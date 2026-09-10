#!/usr/bin/env python3
"""Normalize a lossless Infinity Army ``master.json`` into relational-style JSON.

This script consumes the output of ``merge_infinity_army.py`` and produces a
single JSON document whose ``tables`` member contains arrays of records.  The
records are deliberately database-independent: they can later be written to
SQLite, PostgreSQL, CSV/JSONL, etc. without teaching the database adapter how to
interpret Corvus Belli's nested source format.

Design principles
-----------------
* ``unit.id`` is the global unit identity.
* Army/sectorial occurrences remain army-specific.  Profile groups, profiles,
  loadout options, AVA, points, SWC, skills, equipment, etc. are therefore keyed
  by ``(army_id, unit_id, ...)`` rather than flattened into global profiles.
* Global lookup IDs (skills, weapons, equipment, ammunition, characteristics,
  troop types, categories and extras) are deduplicated by ID.  Army-specific
  flags/presence are retained in separate link tables.
* Peripheral IDs are *army-local*, so their primary key is ``(army_id, id)``.
* Faction references are a superset of actual source files.  Placeholder rows
  are created for referenced faction/category IDs that have no definition in
  the supplied master file, keeping foreign keys valid without inventing names.
* Rare/uncertain structures (Spec-Ops tables, resume/teamops and search-filter
  UI data) are preserved as JSON-valued fields instead of being over-normalized.
* Every generated foreign-key relationship is validated before output is
  written.  Source anomalies are reported as warnings rather than silently
  discarded.

Uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .metadata import METADATA_TABLES, MetadataError, normalize_metadata, validate_metadata_envelope


FORMAT_NAME = "Infinity Army normalized JSON"
FORMAT_VERSION = 1
EXPECTED_MASTER_FORMAT = "Infinity Army merged JSON"
EXPECTED_MASTER_VERSION = 1

GLOBAL_CATALOGS = {
    "category": ("categories", "army_categories"),
    "chars": ("characteristics", "army_characteristics"),
    "type": ("troop_types", "army_troop_types"),
    "equip": ("equipment", "army_equipment"),
    "skills": ("skills", "army_skills"),
    "weapons": ("weapons", "army_weapons"),
    "ammunition": ("ammunition", "army_ammunition"),
    "extras": ("extras", "army_extras"),
}
CONTEXT_FLAGS = ("mercs", "specops", "teamops")


class NormalizationError(ValueError):
    pass


class Builder:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.warnings: list[dict[str, Any]] = []
        self.stats: Counter[str] = Counter()
        self._occurrence_id = 0

    def add(self, table: str, **row: Any) -> dict[str, Any]:
        self.tables[table].append(row)
        return row

    def warn(self, code: str, message: str, **context: Any) -> None:
        item = {"code": code, "message": message}
        if context:
            item["context"] = context
        self.warnings.append(item)
        self.stats[f"warning:{code}"] += 1

    def next_occurrence_id(self) -> int:
        self._occurrence_id += 1
        return self._occurrence_id


def load_master(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise NormalizationError(f"Could not read {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise NormalizationError("master.json top-level value must be an object")
    meta = data.get("_meta")
    if not isinstance(meta, dict):
        raise NormalizationError("master.json has no valid _meta object")
    if meta.get("format") != EXPECTED_MASTER_FORMAT:
        raise NormalizationError(
            f"Expected master format {EXPECTED_MASTER_FORMAT!r}, "
            f"got {meta.get('format')!r}"
        )
    if meta.get("formatVersion") != EXPECTED_MASTER_VERSION:
        raise NormalizationError(
            f"Expected master formatVersion {EXPECTED_MASTER_VERSION}, "
            f"got {meta.get('formatVersion')!r}"
        )
    if not isinstance(data.get("armyLists"), dict) or not isinstance(data.get("units"), dict):
        raise NormalizationError("master.json must contain armyLists and units objects")
    return data


def _stable_base(item: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in item.items() if k not in CONTEXT_FLAGS}


def _merge_catalog_identity(
    identities: dict[Any, dict[str, Any]],
    catalog_name: str,
    item: dict[str, Any],
) -> None:
    if "id" not in item:
        raise NormalizationError(f"{catalog_name} lookup item has no id: {item!r}")
    item_id = item["id"]
    base = _stable_base(item)
    previous = identities.get(item_id)
    if previous is None:
        identities[item_id] = base
    elif previous != base:
        raise NormalizationError(
            f"Global lookup conflict in {catalog_name} for id {item_id}: "
            f"{previous!r} != {base!r}"
        )


def collect_faction_ids(master: dict[str, Any]) -> tuple[set[int], Counter[int], Counter[int]]:
    ids = {int(x) for x in master["armyLists"]}
    canonical_refs: Counter[int] = Counter()
    membership_refs: Counter[int] = Counter()

    for army_key, army in master["armyLists"].items():
        reinf = army.get("reinforcements")
        if isinstance(reinf, int):
            ids.add(reinf)

    for unit_record in master["units"].values():
        shared = unit_record["shared"]
        canonical = shared.get("canonical")
        if isinstance(canonical, int):
            ids.add(canonical)
            canonical_refs[canonical] += 1
        for faction_id in shared.get("factions", []):
            if isinstance(faction_id, int):
                ids.add(faction_id)
                membership_refs[faction_id] += 1

    return ids, canonical_refs, membership_refs


def main_army_id(canonical_faction_id: Any, faction_ids: set[int]) -> int | None:
    """Resolve canonical ownership to its whole-army group ID (``xx01``)."""
    if not isinstance(canonical_faction_id, int):
        return None
    # Canonical 1 is the legacy mercenary designation, which corresponds to
    # Non-Aligned Armies rather than PanOceania.  Other canonical IDs use the
    # current hundred-based army namespace.
    candidate = (
        901 if canonical_faction_id == 1
        else canonical_faction_id - canonical_faction_id % 100 + 1
    )
    return candidate if candidate in faction_ids and candidate % 100 == 1 else None


def build_catalogs(master: dict[str, Any], b: Builder) -> dict[str, set[Any]]:
    identities: dict[str, dict[Any, dict[str, Any]]] = {
        source_name: {} for source_name in GLOBAL_CATALOGS
    }

    # First pass: collect/validate global identities.
    for army_key, army in master["armyLists"].items():
        filters = army.get("filters") or {}
        for source_name in GLOBAL_CATALOGS:
            for item in filters.get(source_name, []):
                if not isinstance(item, dict):
                    raise NormalizationError(
                        f"Army {army_key} filters.{source_name} contains non-object {item!r}"
                    )
                _merge_catalog_identity(identities[source_name], source_name, item)

    # Profile-group category 0 is referenced in the source but is not present in
    # filters.category.  More generally, add source-undefined placeholders for
    # any catalog IDs referenced by normalized records later.
    def emit_global_table(source_name: str) -> None:
        global_table, _ = GLOBAL_CATALOGS[source_name]
        for item_id in sorted(identities[source_name], key=lambda x: (str(type(x)), str(x))):
            item = identities[source_name][item_id]
            row = dict(item)
            row["source_defined"] = True
            b.tables[global_table].append(row)

    for source_name in GLOBAL_CATALOGS:
        emit_global_table(source_name)

    # Second pass: preserve army-specific catalog presence/order/context flags.
    for army_key, army in master["armyLists"].items():
        army_id = int(army_key)
        filters = army.get("filters") or {}
        for source_name, (_, link_table) in GLOBAL_CATALOGS.items():
            for position, item in enumerate(filters.get(source_name, []), start=1):
                b.add(
                    link_table,
                    army_id=army_id,
                    item_id=item["id"],
                    position=position,
                    mercs=item.get("mercs"),
                    specops=item.get("specops"),
                    teamops=item.get("teamops"),
                )

        # Peripherals are explicitly army-local.
        seen_peripheral: set[Any] = set()
        for position, item in enumerate(filters.get("peripheral", []), start=1):
            item_id = item.get("id")
            if item_id in seen_peripheral:
                raise NormalizationError(
                    f"Army {army_id} has duplicate peripheral id {item_id}"
                )
            seen_peripheral.add(item_id)
            b.add(
                "peripherals",
                army_id=army_id,
                id=item_id,
                position=position,
                name=item.get("name"),
                mercs=item.get("mercs"),
            )

    return {name: set(items) for name, items in identities.items()}


def ensure_catalog_placeholder(
    b: Builder,
    catalog_ids: dict[str, set[Any]],
    source_name: str,
    item_id: Any,
    reason: str,
) -> None:
    if item_id is None or item_id in catalog_ids[source_name]:
        return
    global_table, _ = GLOBAL_CATALOGS[source_name]
    catalog_ids[source_name].add(item_id)
    b.add(global_table, id=item_id, name=None, source_defined=False)
    b.warn(
        "catalog_placeholder",
        f"Referenced {source_name} id {item_id!r} has no lookup definition; placeholder created",
        catalog=source_name,
        item_id=item_id,
        reason=reason,
    )


def normalize_reference_occurrences(
    b: Builder,
    catalog_ids: dict[str, set[Any]],
    *,
    source_name: str,
    table: str,
    extras_table: str | None,
    parent: dict[str, Any],
    values: Iterable[Any],
    context: str,
    army_id: int | None = None,
    peripheral_ids: set[tuple[int, Any]] | None = None,
) -> None:
    """Normalize objects shaped like {id, order, q, extra}.

    For peripherals, source_name must be ``peripheral`` and army_id/peripheral_ids
    are used instead of a global catalog.
    """
    known = {"id", "order", "q", "extra"}
    for position, value in enumerate(values, start=1):
        occurrence_id = b.next_occurrence_id()
        if not isinstance(value, dict):
            b.warn(
                "non_object_reference",
                f"{context} contains non-object reference; preserved as raw",
                value=value,
            )
            b.add(
                table,
                occurrence_id=occurrence_id,
                **parent,
                position=position,
                item_id=None,
                display_order=None,
                quantity=None,
                raw=value,
            )
            continue

        item_id = value.get("id")
        if source_name == "peripheral":
            assert army_id is not None and peripheral_ids is not None
            if item_id is not None and (army_id, item_id) not in peripheral_ids:
                b.warn(
                    "missing_peripheral",
                    f"Peripheral id {item_id!r} is not defined for army {army_id}",
                    context=context,
                )
        else:
            ensure_catalog_placeholder(b, catalog_ids, source_name, item_id, context)

        unknown = {k: v for k, v in value.items() if k not in known}
        raw: Any = None
        if item_id is None or unknown:
            raw = value
            if item_id is None:
                b.warn(
                    "anonymous_reference",
                    f"{context} contains a reference object without an id; row preserved",
                    value=value,
                )
            if unknown:
                b.warn(
                    "unmodeled_reference_fields",
                    f"{context} contains unmodeled fields; row preserved with raw data",
                    fields=sorted(unknown),
                )

        b.add(
            table,
            occurrence_id=occurrence_id,
            **parent,
            position=position,
            item_id=item_id,
            display_order=value.get("order"),
            quantity=value.get("q"),
            raw=raw,
        )

        if extras_table is not None:
            extras = value.get("extra")
            if extras is None:
                continue
            if not isinstance(extras, list):
                b.warn(
                    "invalid_extra_list",
                    f"{context} extra field is not an array; preserved in parent raw data",
                    value=extras,
                )
                continue
            for extra_position, extra_id in enumerate(extras, start=1):
                ensure_catalog_placeholder(b, catalog_ids, "extras", extra_id, context)
                b.add(
                    extras_table,
                    occurrence_id=occurrence_id,
                    position=extra_position,
                    extra_id=extra_id,
                )


def normalize_includes(
    b: Builder,
    table: str,
    parent: dict[str, Any],
    values: Iterable[Any],
    context: str,
) -> None:
    for position, value in enumerate(values, start=1):
        if not isinstance(value, dict):
            b.warn("invalid_include", f"{context} include is not an object", value=value)
            b.add(
                table,
                **parent,
                position=position,
                target_group_id=None,
                target_option_id=None,
                quantity=None,
                raw=value,
            )
            continue
        known = {"group", "option", "q"}
        unknown = {k: v for k, v in value.items() if k not in known}
        b.add(
            table,
            **parent,
            position=position,
            target_group_id=value.get("group"),
            target_option_id=value.get("option"),
            quantity=value.get("q"),
            raw=value if unknown else None,
        )
        if unknown:
            b.warn(
                "unmodeled_include_fields",
                f"{context} include contains unmodeled fields",
                fields=sorted(unknown),
            )


def normalize_orders(
    b: Builder,
    table: str,
    parent: dict[str, Any],
    values: Iterable[Any],
    context: str,
) -> None:
    for position, value in enumerate(values, start=1):
        if not isinstance(value, dict):
            b.warn("invalid_order", f"{context} order is not an object", value=value)
            b.add(table, **parent, position=position, order_type=None, list_count=None, total_count=None, raw=value)
            continue
        known = {"type", "list", "total"}
        unknown = {k: v for k, v in value.items() if k not in known}
        b.add(
            table,
            **parent,
            position=position,
            order_type=value.get("type"),
            list_count=value.get("list"),
            total_count=value.get("total"),
            raw=value if unknown else None,
        )
        if unknown:
            b.warn(
                "unmodeled_order_fields",
                f"{context} order contains unmodeled fields",
                fields=sorted(unknown),
            )


def normalize_characteristics(
    b: Builder,
    catalog_ids: dict[str, set[Any]],
    table: str,
    parent: dict[str, Any],
    values: Iterable[Any],
    context: str,
) -> None:
    for position, char_id in enumerate(values, start=1):
        ensure_catalog_placeholder(b, catalog_ids, "chars", char_id, context)
        b.add(table, **parent, position=position, characteristic_id=char_id)


def normalize_option_nested(
    b: Builder,
    catalog_ids: dict[str, set[Any]],
    peripheral_ids: set[tuple[int, Any]],
    *,
    prefix: str,
    army_id: int | None,
    parent: dict[str, Any],
    option: dict[str, Any],
    context: str,
) -> None:
    # Global unit options do not currently contain these item arrays, but we
    # normalize them anyway so future source versions are handled consistently.
    normalize_reference_occurrences(
        b,
        catalog_ids,
        source_name="skills",
        table=f"{prefix}_skills",
        extras_table=f"{prefix}_skill_extras",
        parent=parent,
        values=option.get("skills", []),
        context=f"{context}.skills",
    )
    normalize_reference_occurrences(
        b,
        catalog_ids,
        source_name="equip",
        table=f"{prefix}_equipment",
        extras_table=f"{prefix}_equipment_extras",
        parent=parent,
        values=option.get("equip", []),
        context=f"{context}.equip",
    )
    normalize_reference_occurrences(
        b,
        catalog_ids,
        source_name="weapons",
        table=f"{prefix}_weapons",
        extras_table=f"{prefix}_weapon_extras",
        parent=parent,
        values=option.get("weapons", []),
        context=f"{context}.weapons",
    )
    if army_id is not None:
        normalize_reference_occurrences(
            b,
            catalog_ids,
            source_name="peripheral",
            table=f"{prefix}_peripherals",
            extras_table=None,
            parent=parent,
            values=option.get("peripheral", []),
            context=f"{context}.peripheral",
            army_id=army_id,
            peripheral_ids=peripheral_ids,
        )
    elif option.get("peripheral"):
        # Global unit options have no unambiguous army-local peripheral namespace.
        for value in option.get("peripheral", []):
            b.warn(
                "global_option_peripheral",
                "Global unit option contains an army-local peripheral reference; preserved in raw option",
                context=context,
                value=value,
            )

    normalize_characteristics(
        b,
        catalog_ids,
        f"{prefix}_characteristics",
        parent,
        option.get("chars", []),
        f"{context}.chars",
    )
    normalize_includes(
        b,
        f"{prefix}_includes",
        parent,
        option.get("includes", []),
        f"{context}.includes",
    )
    normalize_orders(
        b,
        f"{prefix}_orders",
        parent,
        option.get("orders", []),
        f"{context}.orders",
    )


def normalize_master(master: dict[str, Any]) -> dict[str, Any]:
    b = Builder()
    army_lists = master["armyLists"]
    units = master["units"]

    metadata = master.get("armyMetadata")
    metadata_rows: dict[str, list[dict[str, Any]]] = {}
    metadata_faction_names: dict[int, str] = {}
    if metadata is not None:
        try:
            validate_metadata_envelope(metadata)
            metadata_rows = normalize_metadata(metadata)
        except MetadataError as exc:
            raise NormalizationError(f"Invalid Army metadata: {exc}") from exc
        for row in metadata_rows["metadata_factions"]:
            metadata_faction_names[row["id"]] = row["name"]
    for table_name, _ in METADATA_TABLES.values():
        metadata_rows.setdefault(table_name, [])

    # Relations occasionally point at legitimate Army unit IDs that are not
    # present as ordinary unit records in the supplied source files.  Collect
    # them up front so they can be represented by explicit placeholder units.
    relation_unit_refs: Counter[int] = Counter()
    for army in army_lists.values():
        for relation in army.get("relations", []):
            for rel_unit in relation.get("units", []):
                ref = rel_unit.get("unit")
                if isinstance(ref, int):
                    relation_unit_refs[ref] += 1
                for dep in rel_unit.get("depends", []):
                    ref = dep.get("unit")
                    if isinstance(ref, int):
                        relation_unit_refs[ref] += 1

    # Faction reference namespace: includes source files and dangling references
    # present in canonical/factions fields.
    faction_ids, canonical_refs, membership_refs = collect_faction_ids(master)
    actual_army_ids = {int(x) for x in army_lists}
    for faction_id in sorted(faction_ids):
        b.add(
            "factions",
            id=faction_id,
            has_army_list=faction_id in actual_army_ids,
            canonical_reference_count=canonical_refs[faction_id],
            unit_membership_reference_count=membership_refs[faction_id],
        )

    catalog_ids = build_catalogs(master, b)

    # Army-list records and army-local peripherals/catalog context.
    for army_key, army in sorted(army_lists.items(), key=lambda kv: int(kv[0])):
        army_id = int(army_key)
        meta = army.get("_meta") or {}
        filters = army.get("filters") or {}
        chart = army.get("fireteamChart") or {}
        spec = chart.get("spec") or {}
        b.add(
            "army_lists",
            id=army_id,
            name=metadata_faction_names.get(army_id),
            slug=meta.get("slug"),
            kind=meta.get("kind"),
            version=army.get("version"),
            reinforcement_id=army.get("reinforcements"),
            source_file=meta.get("sourceFile"),
            source_sha256=meta.get("sourceSha256"),
            resume=army.get("resume"),
            teamops=army.get("teamops"),
            legacy_fireteams=army.get("fireteams"),
            filter_attrs=filters.get("attrs"),
            filter_points=filters.get("points"),
            filter_swc=filters.get("swc"),
            fireteam_description=chart.get("desc"),
            fireteam_spec=spec,
        )

    peripheral_ids = {
        (row["army_id"], row["id"]) for row in b.tables.get("peripherals", [])
    }

    # Global units and their declared faction memberships.
    for unit_key, unit_record in sorted(units.items(), key=lambda kv: int(kv[0])):
        unit_id = int(unit_key)
        shared = unit_record.get("shared") or {}
        if shared.get("id") != unit_id:
            raise NormalizationError(
                f"Unit dictionary key {unit_id} disagrees with shared.id={shared.get('id')!r}"
            )
        b.add(
            "units",
            id=unit_id,
            id_army=shared.get("idArmy"),
            canonical_faction_id=shared.get("canonical"),
            main_army_id=main_army_id(shared.get("canonical"), faction_ids),
            isc=shared.get("isc"),
            isc_abbr=shared.get("iscAbbr"),
            name=shared.get("name"),
            slug=shared.get("slug"),
            notes=shared.get("notes"),
            spectables=shared.get("spectables"),
            source_defined=True,
            relation_reference_count=relation_unit_refs[unit_id],
        )
        for position, faction_id in enumerate(shared.get("factions", []), start=1):
            b.add(
                "unit_factions",
                unit_id=unit_id,
                faction_id=faction_id,
                position=position,
            )

        # Top-level unit options are global to the unit identity in master.json.
        for position, option in enumerate(shared.get("options", []), start=1):
            option_id = option.get("id")
            parent = {"unit_id": unit_id, "option_id": option_id}
            known = {
                "id", "name", "points", "swc", "minis", "disabled", "compatible",
                "habilities", "skills", "equip", "weapons", "peripheral", "chars",
                "includes", "orders",
            }
            unknown = {k: v for k, v in option.items() if k not in known}
            b.add(
                "unit_options",
                unit_id=unit_id,
                option_id=option_id,
                position=position,
                name=option.get("name"),
                points=option.get("points"),
                swc=option.get("swc"),
                minis=option.get("minis"),
                disabled=option.get("disabled"),
                compatible=option.get("compatible"),
                habilities=option.get("habilities"),
                raw=option if unknown else None,
            )
            if unknown:
                b.warn(
                    "unmodeled_unit_option_fields",
                    "Global unit option contains unmodeled fields",
                    unit_id=unit_id,
                    option_id=option_id,
                    fields=sorted(unknown),
                )
            normalize_option_nested(
                b,
                catalog_ids,
                peripheral_ids,
                prefix="unit_option",
                army_id=None,
                parent=parent,
                option=option,
                context=f"unit {unit_id} option {option_id}",
            )

    for unit_id in sorted(set(relation_unit_refs) - {int(x) for x in units}):
        b.add(
            "units",
            id=unit_id,
            id_army=None,
            canonical_faction_id=None,
            main_army_id=None,
            isc=None,
            isc_abbr=None,
            name=None,
            slug=None,
            notes=None,
            spectables=None,
            source_defined=False,
            relation_reference_count=relation_unit_refs[unit_id],
        )
        b.warn(
            "unit_placeholder",
            f"Relation references unit id {unit_id}, which has no ordinary unit record; placeholder created",
            unit_id=unit_id,
            reference_count=relation_unit_refs[unit_id],
        )

    # Army-unit occurrences, profile groups, profiles and army-specific options.
    for army_key, army in sorted(army_lists.items(), key=lambda kv: int(kv[0])):
        army_id = int(army_key)
        seen_units: set[int] = set()
        for unit_position, unit_id in enumerate(army.get("unitIds", []), start=1):
            if unit_id in seen_units:
                raise NormalizationError(f"Army {army_id} unitIds contains duplicate {unit_id}")
            seen_units.add(unit_id)
            unit_record = units.get(str(unit_id))
            if unit_record is None:
                raise NormalizationError(f"Army {army_id} references unknown unit id {unit_id}")
            variant = (unit_record.get("byArmy") or {}).get(str(army_id))
            if variant is None:
                raise NormalizationError(
                    f"Army {army_id} lists unit {unit_id}, but unit has no byArmy variant"
                )

            b.add(
                "army_units",
                army_id=army_id,
                unit_id=unit_id,
                position=unit_position,
                filters=variant.get("filters"),
            )

            group_option_ids: dict[int, set[int]] = {}
            for group_position, group in enumerate(variant.get("profileGroups", []), start=1):
                group_id = group.get("id")
                category_id = group.get("category")
                ensure_catalog_placeholder(
                    b,
                    catalog_ids,
                    "category",
                    category_id,
                    f"army {army_id} unit {unit_id} group {group_id}",
                )
                option_ids = {o.get("id") for o in group.get("options", [])}
                if len(option_ids) != len(group.get("options", [])):
                    raise NormalizationError(
                        f"Army {army_id} unit {unit_id} group {group_id} has duplicate option IDs"
                    )
                group_option_ids[group_id] = option_ids

                b.add(
                    "profile_groups",
                    army_id=army_id,
                    unit_id=unit_id,
                    group_id=group_id,
                    position=group_position,
                    category_id=category_id,
                    isc=group.get("isc"),
                    notes=group.get("notes"),
                )

                seen_profiles: set[Any] = set()
                for profile_position, profile in enumerate(group.get("profiles", []), start=1):
                    profile_id = profile.get("id")
                    if profile_id in seen_profiles:
                        raise NormalizationError(
                            f"Army {army_id} unit {unit_id} group {group_id} has duplicate profile id {profile_id}"
                        )
                    seen_profiles.add(profile_id)
                    type_id = profile.get("type")
                    ensure_catalog_placeholder(
                        b,
                        catalog_ids,
                        "type",
                        type_id,
                        f"army {army_id} unit {unit_id} group {group_id} profile {profile_id}",
                    )
                    move = profile.get("move") or []
                    if len(move) != 2:
                        b.warn(
                            "unexpected_move_shape",
                            "Profile move does not contain exactly two values",
                            army_id=army_id,
                            unit_id=unit_id,
                            group_id=group_id,
                            profile_id=profile_id,
                            move=move,
                        )
                    parent = {
                        "army_id": army_id,
                        "unit_id": unit_id,
                        "group_id": group_id,
                        "profile_id": profile_id,
                    }
                    b.add(
                        "profiles",
                        **parent,
                        position=profile_position,
                        name=profile.get("name"),
                        logo=profile.get("logo"),
                        type_id=type_id,
                        move_1=move[0] if len(move) > 0 else None,
                        move_2=move[1] if len(move) > 1 else None,
                        cc=profile.get("cc"),
                        bs=profile.get("bs"),
                        ph=profile.get("ph"),
                        wip=profile.get("wip"),
                        arm=profile.get("arm"),
                        bts=profile.get("bts"),
                        vitality=profile.get("w"),
                        silhouette=profile.get("s"),
                        ava=profile.get("ava"),
                        is_structure=profile.get("str"),
                        notes=profile.get("notes"),
                    )
                    normalize_characteristics(
                        b,
                        catalog_ids,
                        "profile_characteristics",
                        parent,
                        profile.get("chars", []),
                        f"army {army_id} unit {unit_id} group {group_id} profile {profile_id}.chars",
                    )
                    normalize_reference_occurrences(
                        b,
                        catalog_ids,
                        source_name="skills",
                        table="profile_skills",
                        extras_table="profile_skill_extras",
                        parent=parent,
                        values=profile.get("skills", []),
                        context=f"army {army_id} unit {unit_id} group {group_id} profile {profile_id}.skills",
                    )
                    normalize_reference_occurrences(
                        b,
                        catalog_ids,
                        source_name="equip",
                        table="profile_equipment",
                        extras_table="profile_equipment_extras",
                        parent=parent,
                        values=profile.get("equip", []),
                        context=f"army {army_id} unit {unit_id} group {group_id} profile {profile_id}.equip",
                    )
                    normalize_reference_occurrences(
                        b,
                        catalog_ids,
                        source_name="weapons",
                        table="profile_weapons",
                        extras_table="profile_weapon_extras",
                        parent=parent,
                        values=profile.get("weapons", []),
                        context=f"army {army_id} unit {unit_id} group {group_id} profile {profile_id}.weapons",
                    )
                    normalize_reference_occurrences(
                        b,
                        catalog_ids,
                        source_name="peripheral",
                        table="profile_peripherals",
                        extras_table=None,
                        parent=parent,
                        values=profile.get("peripheral", []),
                        context=f"army {army_id} unit {unit_id} group {group_id} profile {profile_id}.peripheral",
                        army_id=army_id,
                        peripheral_ids=peripheral_ids,
                    )
                    normalize_includes(
                        b,
                        "profile_includes",
                        parent,
                        profile.get("includes", []),
                        f"army {army_id} unit {unit_id} group {group_id} profile {profile_id}.includes",
                    )

                for option_position, option in enumerate(group.get("options", []), start=1):
                    option_id = option.get("id")
                    parent = {
                        "army_id": army_id,
                        "unit_id": unit_id,
                        "group_id": group_id,
                        "option_id": option_id,
                    }
                    b.add(
                        "loadout_options",
                        **parent,
                        position=option_position,
                        name=option.get("name"),
                        points=option.get("points"),
                        swc=option.get("swc"),
                        minis=option.get("minis"),
                        disabled=option.get("disabled"),
                    )
                    normalize_option_nested(
                        b,
                        catalog_ids,
                        peripheral_ids,
                        prefix="option",
                        army_id=army_id,
                        parent=parent,
                        option=option,
                        context=f"army {army_id} unit {unit_id} group {group_id} option {option_id}",
                    )

            # Verify includes after every group/option key has been collected.
            valid_options = {
                (group_id, option_id)
                for group_id, option_ids in group_option_ids.items()
                for option_id in option_ids
            }
            for table in ("profile_includes", "option_includes"):
                for row in b.tables.get(table, []):
                    if row.get("army_id") != army_id or row.get("unit_id") != unit_id:
                        continue
                    target = (row.get("target_group_id"), row.get("target_option_id"))
                    if target not in valid_options:
                        raise NormalizationError(
                            f"Invalid include target {target} in army {army_id} unit {unit_id}"
                        )

            # Global unit-option includes must be valid in every army occurrence.
            shared = unit_record["shared"]
            for option in shared.get("options", []):
                for include in option.get("includes", []):
                    target = (include.get("group"), include.get("option"))
                    if target not in valid_options:
                        raise NormalizationError(
                            f"Unit {unit_id} global option {option.get('id')} target {target} "
                            f"is invalid in army {army_id}"
                        )

    # Fireteam chart.
    slug_to_units: dict[str, set[int]] = defaultdict(set)
    for row in b.tables["units"]:
        if row.get("slug"):
            slug_to_units[row["slug"]].add(row["id"])
    army_unit_sets: dict[int, set[int]] = defaultdict(set)
    for row in b.tables["army_units"]:
        army_unit_sets[row["army_id"]].add(row["unit_id"])

    for army_key, army in sorted(army_lists.items(), key=lambda kv: int(kv[0])):
        army_id = int(army_key)
        chart = army.get("fireteamChart") or {}
        for fireteam_id, team in enumerate(chart.get("teams", []), start=1):
            b.add(
                "fireteams",
                army_id=army_id,
                fireteam_id=fireteam_id,
                position=fireteam_id,
                name=team.get("name"),
                observation=team.get("obs"),
            )
            for type_position, fireteam_type in enumerate(team.get("type", []), start=1):
                b.add(
                    "fireteam_types",
                    army_id=army_id,
                    fireteam_id=fireteam_id,
                    position=type_position,
                    fireteam_type=fireteam_type,
                )
            for member_id, member in enumerate(team.get("units", []), start=1):
                slug = member.get("slug")
                candidates = slug_to_units.get(slug, set())
                local_candidates = candidates & army_unit_sets[army_id]
                if len(local_candidates) == 1:
                    resolved_unit_id = next(iter(local_candidates))
                    resolution = "army"
                elif len(candidates) == 1:
                    resolved_unit_id = next(iter(candidates))
                    resolution = "global"
                    b.warn(
                        "fireteam_unit_not_in_army",
                        "Fireteam slug resolves globally but not to a unit listed in this army",
                        army_id=army_id,
                        fireteam_id=fireteam_id,
                        slug=slug,
                        unit_id=resolved_unit_id,
                    )
                elif len(candidates) > 1:
                    resolved_unit_id = None
                    resolution = "ambiguous"
                    b.warn(
                        "ambiguous_fireteam_slug",
                        "Fireteam slug maps to multiple unit IDs",
                        army_id=army_id,
                        fireteam_id=fireteam_id,
                        slug=slug,
                        candidates=sorted(candidates),
                    )
                else:
                    resolved_unit_id = None
                    resolution = "unresolved"
                    b.warn(
                        "unresolved_fireteam_slug",
                        "Fireteam slug does not map to a normalized unit",
                        army_id=army_id,
                        fireteam_id=fireteam_id,
                        slug=slug,
                        name=member.get("name"),
                    )
                b.add(
                    "fireteam_members",
                    army_id=army_id,
                    fireteam_id=fireteam_id,
                    member_id=member_id,
                    position=member_id,
                    slug=slug,
                    name=member.get("name"),
                    comment=member.get("comment"),
                    min_count=member.get("min"),
                    max_count=member.get("max"),
                    required=member.get("required"),
                    resolved_unit_id=resolved_unit_id,
                    resolution=resolution,
                )

    # Relations.  profile/group/options values here are preserved as Army's raw
    # local selectors; they are not promoted to profile FKs because the source
    # does not always provide enough key components to identify a unique row.
    for army_key, army in sorted(army_lists.items(), key=lambda kv: int(kv[0])):
        army_id = int(army_key)
        for relation_id, relation in enumerate(army.get("relations", []), start=1):
            b.add(
                "relations",
                army_id=army_id,
                relation_id=relation_id,
                position=relation_id,
                min_count=relation.get("min"),
                max_count=relation.get("max"),
                is_group=relation.get("group"),
            )
            for relation_unit_id, rel_unit in enumerate(relation.get("units", []), start=1):
                unit_id = rel_unit.get("unit")
                b.add(
                    "relation_units",
                    army_id=army_id,
                    relation_id=relation_id,
                    relation_unit_id=relation_unit_id,
                    position=relation_unit_id,
                    unit_id=unit_id,
                    profile_id=rel_unit.get("profile"),
                    per_parent=rel_unit.get("perParent"),
                )
                known = {"unit", "profile", "perParent", "depends"}
                unknown = {k: v for k, v in rel_unit.items() if k not in known}
                if unknown:
                    b.warn(
                        "unmodeled_relation_unit_fields",
                        "Relation unit contains unmodeled fields",
                        army_id=army_id,
                        relation_id=relation_id,
                        fields=sorted(unknown),
                    )
                for dependency_id, dep in enumerate(rel_unit.get("depends", []), start=1):
                    dep_unit = dep.get("unit")
                    known_dep = {
                        "unit", "profile", "group", "min", "minDependant", "options"
                    }
                    unknown_dep = {k: v for k, v in dep.items() if k not in known_dep}
                    b.add(
                        "relation_dependencies",
                        army_id=army_id,
                        relation_id=relation_id,
                        relation_unit_id=relation_unit_id,
                        dependency_id=dependency_id,
                        position=dependency_id,
                        unit_id=dep_unit,
                        profile_id=dep.get("profile"),
                        group_id=dep.get("group"),
                        min_count=dep.get("min"),
                        min_dependant=dep.get("minDependant"),
                        options=dep.get("options"),
                        raw=dep if unknown_dep else None,
                    )
                    if unknown_dep:
                        b.warn(
                            "unmodeled_relation_dependency_fields",
                            "Relation dependency contains unmodeled fields",
                            army_id=army_id,
                            relation_id=relation_id,
                            fields=sorted(unknown_dep),
                        )

    tables = dict(sorted(b.tables.items()))
    tables.update(metadata_rows)
    tables = dict(sorted(tables.items()))
    result = {
        "_meta": {
            "format": FORMAT_NAME,
            "formatVersion": FORMAT_VERSION,
            "sourceFormat": master["_meta"].get("format"),
            "sourceFormatVersion": master["_meta"].get("formatVersion"),
            "sourceFileCount": master["_meta"].get("sourceFileCount"),
            "sourceVersions": master["_meta"].get("sourceVersions"),
            "tableCounts": {name: len(rows) for name, rows in tables.items()},
            "warningCount": len(b.warnings),
            "warningCounts": dict(sorted((k.removeprefix("warning:"), v) for k, v in b.stats.items() if k.startswith("warning:"))),
        },
        "tables": tables,
        "warnings": b.warnings,
    }
    if metadata is not None:
        result["armyMetadata"] = metadata
    return result


def _unique(rows: list[dict[str, Any]], fields: tuple[str, ...], table: str) -> set[tuple[Any, ...]]:
    seen: set[tuple[Any, ...]] = set()
    for row in rows:
        key = tuple(row.get(field) for field in fields)
        if key in seen:
            raise NormalizationError(f"Duplicate key in {table} {fields}: {key}")
        seen.add(key)
    return seen


def validate_normalized(data: dict[str, Any]) -> dict[str, Any]:
    """Validate primary-key uniqueness and generated foreign-key relationships."""
    t = data["tables"]
    if "armyMetadata" in data:
        try:
            validate_metadata_envelope(data["armyMetadata"])
        except MetadataError as exc:
            raise NormalizationError(f"Invalid Army metadata: {exc}") from exc
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(ok), "detail": detail})
        if not ok:
            raise NormalizationError(f"Validation failed: {name}: {detail}")

    faction_ids = _unique(t.get("factions", []), ("id",), "factions")
    faction_ids_scalar = {x[0] for x in faction_ids}
    army_ids = _unique(t.get("army_lists", []), ("id",), "army_lists")
    army_ids_scalar = {x[0] for x in army_ids}
    unit_ids = _unique(t.get("units", []), ("id",), "units")
    unit_ids_scalar = {x[0] for x in unit_ids}
    army_unit_keys = _unique(t.get("army_units", []), ("army_id", "unit_id"), "army_units")
    profile_group_keys = _unique(t.get("profile_groups", []), ("army_id", "unit_id", "group_id"), "profile_groups")
    profile_keys = _unique(t.get("profiles", []), ("army_id", "unit_id", "group_id", "profile_id"), "profiles")
    option_keys = _unique(t.get("loadout_options", []), ("army_id", "unit_id", "group_id", "option_id"), "loadout_options")
    unit_option_keys = _unique(t.get("unit_options", []), ("unit_id", "option_id"), "unit_options")
    peripheral_keys = _unique(t.get("peripherals", []), ("army_id", "id"), "peripherals")
    fireteam_keys = _unique(t.get("fireteams", []), ("army_id", "fireteam_id"), "fireteams")
    relation_keys = _unique(t.get("relations", []), ("army_id", "relation_id"), "relations")
    relation_unit_keys = _unique(t.get("relation_units", []), ("army_id", "relation_id", "relation_unit_id"), "relation_units")
    _unique(t.get("unit_factions", []), ("unit_id", "faction_id"), "unit_factions")
    _unique(t.get("peripherals", []), ("army_id", "id"), "peripherals")
    _unique(t.get("fireteam_types", []), ("army_id", "fireteam_id", "position"), "fireteam_types")
    _unique(t.get("fireteam_members", []), ("army_id", "fireteam_id", "member_id"), "fireteam_members")

    # Global lookup keys.
    catalog_table_ids: dict[str, set[Any]] = {}
    for source_name, (global_table, _) in GLOBAL_CATALOGS.items():
        keys = _unique(t.get(global_table, []), ("id",), global_table)
        catalog_table_ids[source_name] = {x[0] for x in keys}

    check("army_list -> faction", all((row["id"],) in faction_ids for row in t.get("army_lists", [])), "all army-list IDs exist as faction references")
    check("army_list reinforcement -> faction", all(row.get("reinforcement_id") is None or row["reinforcement_id"] in faction_ids_scalar for row in t.get("army_lists", [])), "all reinforcement IDs exist in faction references")
    check("unit canonical -> faction", all(row.get("canonical_faction_id") is None or row["canonical_faction_id"] in faction_ids_scalar for row in t.get("units", [])), "all canonical faction references resolve")
    check("unit main army -> whole army group", all(
        row.get("main_army_id") is None
        or row["main_army_id"] in faction_ids_scalar and row["main_army_id"] % 100 == 1
        for row in t.get("units", [])
    ), "all main-army references resolve to whole-army group IDs")
    check("unit_factions -> unit/faction", all(row["unit_id"] in unit_ids_scalar and row["faction_id"] in faction_ids_scalar for row in t.get("unit_factions", [])), "all unit faction memberships resolve")
    check("army_units -> army/unit", all(row["army_id"] in army_ids_scalar and row["unit_id"] in unit_ids_scalar for row in t.get("army_units", [])), "all army-unit rows resolve")
    check("profile_groups -> army_unit", all((row["army_id"], row["unit_id"]) in army_unit_keys for row in t.get("profile_groups", [])), "all profile groups have an army-unit parent")
    check("profiles -> profile_group", all((row["army_id"], row["unit_id"], row["group_id"]) in profile_group_keys for row in t.get("profiles", [])), "all profiles have a profile-group parent")
    check("options -> profile_group", all((row["army_id"], row["unit_id"], row["group_id"]) in profile_group_keys for row in t.get("loadout_options", [])), "all loadout options have a profile-group parent")
    check("unit_options -> unit", all(row["unit_id"] in unit_ids_scalar for row in t.get("unit_options", [])), "all global unit options have a unit parent")
    check("peripherals -> army", all(row["army_id"] in army_ids_scalar for row in t.get("peripherals", [])), "all army-local peripherals have an army parent")
    check("profile_groups category -> categories", all(row.get("category_id") is None or row["category_id"] in catalog_table_ids["category"] for row in t.get("profile_groups", [])), "all non-null profile-group categories resolve")
    check("profiles type -> troop_types", all(row.get("type_id") is None or row["type_id"] in catalog_table_ids["type"] for row in t.get("profiles", [])), "all non-null profile troop types resolve")

    # Catalog link tables.
    for source_name, (global_table, link_table) in GLOBAL_CATALOGS.items():
        valid = catalog_table_ids[source_name]
        check(
            f"{link_table} -> army/{global_table}",
            all(row["army_id"] in army_ids_scalar and row["item_id"] in valid for row in t.get(link_table, [])),
            f"all {link_table} rows resolve",
        )

    # Parent FK helpers for nested tables.
    profile_parent_tables = {
        "profile_characteristics", "profile_skills", "profile_equipment", "profile_weapons",
        "profile_peripherals", "profile_includes",
    }
    for table in profile_parent_tables:
        check(
            f"{table} -> profile",
            all((r["army_id"], r["unit_id"], r["group_id"], r["profile_id"]) in profile_keys for r in t.get(table, [])),
            f"all {table} rows have a profile parent",
        )

    option_parent_tables = {
        "option_characteristics", "option_skills", "option_equipment", "option_weapons",
        "option_peripherals", "option_includes", "option_orders",
    }
    for table in option_parent_tables:
        check(
            f"{table} -> option",
            all((r["army_id"], r["unit_id"], r["group_id"], r["option_id"]) in option_keys for r in t.get(table, [])),
            f"all {table} rows have a loadout-option parent",
        )

    unit_option_parent_tables = {
        "unit_option_characteristics", "unit_option_skills", "unit_option_equipment", "unit_option_weapons",
        "unit_option_includes", "unit_option_orders",
    }
    for table in unit_option_parent_tables:
        check(
            f"{table} -> unit_option",
            all((r["unit_id"], r["option_id"]) in unit_option_keys for r in t.get(table, [])),
            f"all {table} rows have a unit-option parent",
        )

    # Item refs (null is allowed only for source anomalies intentionally preserved).
    item_tables = {
        "profile_skills": "skills",
        "profile_equipment": "equip",
        "profile_weapons": "weapons",
        "option_skills": "skills",
        "option_equipment": "equip",
        "option_weapons": "weapons",
        "unit_option_skills": "skills",
        "unit_option_equipment": "equip",
        "unit_option_weapons": "weapons",
    }
    for table, source_name in item_tables.items():
        valid = catalog_table_ids[source_name]
        check(
            f"{table} -> catalog",
            all(r.get("item_id") is None or r["item_id"] in valid for r in t.get(table, [])),
            f"all non-null {table} item IDs resolve",
        )

    char_tables = ["profile_characteristics", "option_characteristics", "unit_option_characteristics"]
    for table in char_tables:
        valid = catalog_table_ids["chars"]
        check(
            f"{table} -> characteristics",
            all(r.get("characteristic_id") in valid for r in t.get(table, [])),
            f"all {table} characteristic IDs resolve",
        )

    periph_tables = ["profile_peripherals", "option_peripherals"]
    for table in periph_tables:
        check(
            f"{table} -> peripherals",
            all(r.get("item_id") is None or (r["army_id"], r["item_id"]) in peripheral_keys for r in t.get(table, [])),
            f"all non-null {table} peripheral IDs resolve",
        )

    # Extras reference occurrence rows and the global extras catalog.
    occurrence_ids_by_table = {
        table: {r["occurrence_id"] for r in t.get(table, [])}
        for table in [
            "profile_skills", "profile_equipment", "profile_weapons",
            "option_skills", "option_equipment", "option_weapons",
            "unit_option_skills", "unit_option_equipment", "unit_option_weapons",
        ]
    }
    extras_pairs = [
        ("profile_skill_extras", "profile_skills"),
        ("profile_equipment_extras", "profile_equipment"),
        ("profile_weapon_extras", "profile_weapons"),
        ("option_skill_extras", "option_skills"),
        ("option_equipment_extras", "option_equipment"),
        ("option_weapon_extras", "option_weapons"),
        ("unit_option_skill_extras", "unit_option_skills"),
        ("unit_option_equipment_extras", "unit_option_equipment"),
        ("unit_option_weapon_extras", "unit_option_weapons"),
    ]
    for extra_table, parent_table in extras_pairs:
        check(
            f"{extra_table} -> occurrence/extras",
            all(r["occurrence_id"] in occurrence_ids_by_table[parent_table] and r["extra_id"] in catalog_table_ids["extras"] for r in t.get(extra_table, [])),
            f"all {extra_table} rows resolve",
        )

    # Includes target another option within the same army/unit.
    for table in ["profile_includes", "option_includes"]:
        check(
            f"{table} target -> option",
            all((r["army_id"], r["unit_id"], r["target_group_id"], r["target_option_id"]) in option_keys for r in t.get(table, [])),
            f"all {table} targets resolve",
        )

    # Unit-option include is global; it must resolve in at least one army occurrence.
    # The normalizer already proves it resolves in every occurrence while building.
    check(
        "unit_option_includes target -> option",
        all(any(ok[1] == r["unit_id"] and ok[2] == r["target_group_id"] and ok[3] == r["target_option_id"] for ok in option_keys) for r in t.get("unit_option_includes", [])),
        "all global unit-option include targets resolve",
    )

    check("fireteam_types -> fireteam", all((r["army_id"], r["fireteam_id"]) in fireteam_keys for r in t.get("fireteam_types", [])), "all fireteam types have a fireteam parent")
    check("fireteam_members -> fireteam", all((r["army_id"], r["fireteam_id"]) in fireteam_keys for r in t.get("fireteam_members", [])), "all fireteam members have a fireteam parent")
    check("resolved fireteam unit -> unit", all(r.get("resolved_unit_id") is None or r["resolved_unit_id"] in unit_ids_scalar for r in t.get("fireteam_members", [])), "all resolved fireteam units exist")

    check("relation_units -> relation/unit", all((r["army_id"], r["relation_id"]) in relation_keys and (r.get("unit_id") is None or r["unit_id"] in unit_ids_scalar) for r in t.get("relation_units", [])), "all relation units resolve")
    check("relation_dependencies -> relation_unit/unit", all((r["army_id"], r["relation_id"], r["relation_unit_id"]) in relation_unit_keys and (r.get("unit_id") is None or r["unit_id"] in unit_ids_scalar) for r in t.get("relation_dependencies", [])), "all relation dependencies resolve")

    return {
        "passed": True,
        "checkCount": len(checks),
        "checks": checks,
        "warningCount": data["_meta"].get("warningCount", 0),
        "warningCounts": data["_meta"].get("warningCounts", {}),
    }


def write_json(path: Path, data: Any, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        if compact:
            json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    tmp.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Normalize Infinity Army master.json into relational-style JSON tables"
    )
    parser.add_argument("input", type=Path, help="master.json produced by merge_infinity_army.py")
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=Path("normalized.json"),
        help="Normalized output file (default: ./normalized.json)",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Validation report path (default: <output-stem>-validation.json)",
    )
    parser.add_argument("--compact", action="store_true", help="Write minified normalized JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report_path = args.report or args.output.with_name(args.output.stem + "-validation.json")
    try:
        master = load_master(args.input)
        normalized = normalize_master(master)
        validation = validate_normalized(normalized)
        normalized["_meta"]["validationPassed"] = True
        normalized["_meta"]["validationCheckCount"] = validation["checkCount"]
        write_json(args.output, normalized, compact=args.compact)
        write_json(report_path, validation, compact=False)
    except (OSError, NormalizationError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    meta = normalized["_meta"]
    print(f"Normalized {args.input} -> {args.output}")
    print(f"Tables: {len(meta['tableCounts'])}; validation checks: {validation['checkCount']} passed")
    print(f"Warnings: {meta['warningCount']}")
    for name, count in sorted(meta.get("warningCounts", {}).items()):
        print(f"  {name}: {count}")
    print(f"Validation report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
