"""Read-only application queries over the versioned normalized database."""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from infinity_army_data.normalize import FORMAT_NAME, FORMAT_VERSION
from infinity_army_data.weapon_profiles import special_weapon_detail

from .schema import (
    APPLICATION_ID,
    DATABASE_COMPATIBILITY_KEY,
    DATABASE_COMPATIBILITY_VERSION,
    METADATA_TABLE,
    ROW_JSON,
    SCHEMA_VERSION,
    TABLES,
    quote,
)

SQLITE_INTEGER_MIN = -(2**63)
SQLITE_INTEGER_MAX = 2**63 - 1
UNIT_NAME_SQL = "COALESCE(NULLIF(u.name, ''), 'Unit ' || u.id)"
AVAILABILITY_FLAGS = ("mercs", "specops", "teamops", "reinforcement")
# Source records whose IDs differ without following either of the general
# duplicate patterns.  The value is the preferred representative ID.
UNIT_MERGE_ALIASES = {
    300: 300,
    1690: 300,
    10300: 300,
    1345: 1345,
    1875: 1345,
    11345: 1345,
}
SKILL_MERGE_ALIASES = {
    19: 19,
    20: 19,
    21: 19,
    22: 19,
    23: 19,
    69: 69,
    70: 69,
    201: 201,
    278: 201,
    279: 201,
    240: 240,
    274: 240,
}
SKILL_NAME_EXCEPTION_ALIASES = {
    201: 201,
    278: 201,
    279: 201,
    240: 240,
    274: 240,
}
CATALOG_NAME_EXCEPTION_ALIASES = {
    ("equipment", 169): 235,
    ("equipment", 188): 235,
    ("equipment", 193): 235,
    ("equipment", 235): 235,
    ("equipment", 244): 235,
    ("equipment", 247): 235,
    ("equipment", 248): 235,
    ("weapons", 209): 226,
    ("weapons", 215): 226,
    ("weapons", 219): 226,
    ("weapons", 222): 226,
    ("weapons", 226): 226,
    ("weapons", 228): 226,
}
# These metadata rows describe the deployable rather than a weapon mode.
WEAPON_PROFILE_PLACEHOLDERS = frozenset(
    {
        (226, "Armed Turret", None),
        (226, "Armed Turret", "PARA CC Weapon"),
    }
)
ARMY_MERGE_ALIASES = {998: 999}
REINFORCEMENT_ARMY_SUFFIXES = frozenset({98, 99})
NUMBER_PATTERN = re.compile(r"[+-]?\d+(?:\.\d+)?")
DISTANCE_DIVISOR = Decimal("2.5")
NON_DISTANCE_EXTRAS = frozenset({"+5 CC"})
UNIT_IDENTITY_WORD_ALIASES = {
    "armoured": "armored",
    "reconnaissance": "recon",
    "reconaissance": "recon",
}


def is_reinforcement_army_id(army_id: int) -> bool:
    """Return whether an army ID denotes a reinforcement-only army."""
    return army_id % 100 in REINFORCEMENT_ARMY_SUFFIXES


def canonical_army_id(army_id: int) -> int:
    """Return the preferred ID for army lists that represent one force."""
    return ARMY_MERGE_ALIASES.get(army_id, army_id)


def canonical_skill_id(skill_id: int) -> int:
    """Return the representative ID for synonymous skill variants."""
    return SKILL_MERGE_ALIASES.get(skill_id, skill_id)


def skill_merge_key(name: object) -> str | None:
    """Identify skill labels that differ only by a numeric level or value."""
    text = str(name or "").strip()
    if not re.search(r"\d", text):
        return None
    return re.sub(r"\s+", " ", re.sub(r"\d+", "", text)).casefold()


def merged_skill_name(name: object) -> str:
    """Turn a numeric skill variant label into its shared display label."""
    text = re.sub(r"\s+", " ", re.sub(r"\d+", "", str(name or "")).strip())
    text = re.sub(r"\s+L$", "", text, flags=re.IGNORECASE)
    return text.rstrip(" =:-()").strip()


def catalog_merge_key(name: object) -> str | None:
    """Identify catalog labels that differ only by a numeric level or value."""
    text = str(name or "").strip()
    if ":" in text:
        return text.split(":", 1)[0].strip().casefold() or None
    return skill_merge_key(text)


def merged_catalog_name(name: object) -> str:
    """Turn a numeric catalog variant label into its shared display label."""
    text = str(name or "").strip()
    if ":" in text:
        return text.split(":", 1)[0].strip()
    return merged_skill_name(text)


def unit_sort_key(value: object) -> str:
    """Return a case-insensitive, punctuation-free key for unit-name ordering."""
    decomposed = unicodedata.normalize("NFKD", str(value or "")).casefold()
    return "".join(character for character in decomposed if character.isalnum())


def accent_insensitive_key(value: object) -> str:
    """Return text suitable for case-, accent-, and punctuation-insensitive matching."""
    decomposed = unicodedata.normalize("NFKD", str(value or "")).casefold()
    return "".join(character for character in decomposed if character.isalnum())


def contains_distance_multiple(value: object) -> bool:
    """Whether text has no assignment and contains a number divisible by 2.5."""
    text = str(value or "")
    if "=" in text or text.upper() in NON_DISTANCE_EXTRAS:
        return False
    for number in NUMBER_PATTERN.findall(text):
        try:
            if Decimal(number) % DISTANCE_DIVISOR == 0:
                return True
        except InvalidOperation:
            continue
    return False


def canonical_skill_extra_name(skill_name: object, extra_name: object) -> str:
    """Normalize sign conventions that are specific to a distance skill."""
    skill = str(skill_name or "")
    extra = str(extra_name or "")
    if skill == "Super-Jump":
        return extra.removeprefix("+")
    if skill == "Forward Deployment" and not extra.startswith("+"):
        try:
            if NUMBER_PATTERN.fullmatch(extra) and Decimal(extra) > 0:
                return f"+{extra}"
        except InvalidOperation:
            pass
    return extra


def unit_group_key(row: sqlite3.Row) -> tuple[int, str]:
    """Identify duplicate unit records that belong to one logical unit."""
    unit_id = row["id"]
    if unit_id in UNIT_MERGE_ALIASES:
        return (UNIT_MERGE_ALIASES[unit_id], "")
    return (
        unit_id % 10_000,
        (row["isc"] or row["name"]).casefold(),
    )


def normalized_unit_identity(value: object) -> str:
    """Return an order-insensitive, singularized identity for a unit label."""
    identity = re.sub(r"^reinf(?:\.|:)?\s*", "", str(value or ""), flags=re.IGNORECASE)
    decomposed = unicodedata.normalize("NFKD", identity).casefold()
    words = re.findall(r"[^\W_]+", decomposed)
    normalized_words = [
        UNIT_IDENTITY_WORD_ALIASES.get(
            root := (
                word[:-1]
                if len(word) > 3 and word.endswith("s") and not word.endswith("ss")
                else word
            ),
            root,
        )
        for word in words
    ]
    return " ".join(sorted(normalized_words))


def unit_match_identities(row: sqlite3.Row) -> set[str]:
    """Return normalized ISC and display-name identities for a unit.

    Reinforcement labels are secondary, and the Army data does not always use
    the same wording for the ISC and display name.  These identities are used
    only when joining a reinforcement-only record to a unique standard-unit
    candidate.
    """
    return {
        identity
        for value in (row["isc"], row["name"])
        if (identity := normalized_unit_identity(value))
    }


def unit_base_identity(row: sqlite3.Row) -> str:
    """Return a stable primary identity for a logical unit group."""
    return min(unit_match_identities(row), default="")


def append_unique_item(items: list[dict[str, Any]], item: dict[str, Any]) -> None:
    """Add an item unless a merged source already contributed the same one."""
    if item not in items:
        items.append(item)


def merge_profile(profile: dict[str, Any], duplicate: dict[str, Any]) -> None:
    """Combine complementary metadata from duplicate source profiles."""
    for key, value in duplicate.items():
        if key in {"skills", "equipment", "weapons", "ava"}:
            continue
        if profile.get(key) in (None, "") and value not in (None, ""):
            profile[key] = value
    # Duplicate source records can disagree on AVA.  The lower non-negative
    # value is the restrictive availability and avoids advertising an option
    # that is not present in every source record for the same profile.
    ava = duplicate.get("ava")
    if ava is not None and (
        profile.get("ava") is None
        or (
            isinstance(ava, (int, float))
            and ava >= 0
            and isinstance(profile["ava"], (int, float))
            and profile["ava"] >= 0
            and ava < profile["ava"]
        )
    ):
        profile["ava"] = ava


def logical_unit_groups(
    rows: list[sqlite3.Row], memberships: dict[int, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    """Combine 10,000-ID duplicates and their reinforcement-only variants."""
    groups: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        armies = memberships[row["id"]]
        reinforcement_only = bool(armies) and all(
            is_reinforcement_army_id(army["id"]) for army in armies
        )
        base_identity = unit_base_identity(row)
        key = (
            ("reinforcement", base_identity)
            if reinforcement_only
            else ("standard", *unit_group_key(row))
        )
        group = groups.setdefault(
            key,
            {
                "id": row["id"],
                "name": row["name"],
                "isc": row["isc"],
                "slug": row["slug"] if "slug" in row.keys() else None,
                "canonical_faction_id": (
                    row["canonical_faction_id"] if "canonical_faction_id" in row.keys() else None
                ),
                # The lowest source ID is the logical unit's representative.  This
                # prevents a merged reinforcement/duplicate from replacing the
                # canonical army of the ordinary unit.
                "main_army_id": row["main_army_id"] if "main_army_id" in row.keys() else None,
                "source_ids": [],
                "names": [],
                "armies": {},
                "army_occurrences": [],
                "base_identity": base_identity,
                "match_identities": set(unit_match_identities(row)),
                "reinforcement_only": reinforcement_only,
            },
        )
        group["match_identities"].update(unit_match_identities(row))
        group["source_ids"].append(row["id"])
        group["names"].append(row["name"])
        for army in armies:
            source_army_id = army["id"]
            preferred_army_id = canonical_army_id(source_army_id)
            preferred_army = {**army, "id": preferred_army_id}
            if preferred_army_id not in group["armies"] or source_army_id == preferred_army_id:
                group["armies"][preferred_army_id] = preferred_army
            group["army_occurrences"].append(
                {
                    **preferred_army,
                    "source_id": row["id"],
                    "source_army_id": source_army_id,
                }
            )

    standard_groups: dict[str, list[dict[str, Any]]] = {}
    for group in groups.values():
        if not group["reinforcement_only"]:
            for identity in group["match_identities"]:
                standard_groups.setdefault(identity, []).append(group)
    for key, group in list(groups.items()):
        candidates = {
            id(candidate): candidate
            for identity in group["match_identities"]
            for candidate in standard_groups.get(identity, [])
        }.values()
        if group["reinforcement_only"] and len(candidates) == 1:
            target = next(iter(candidates))
            target["source_ids"].extend(group["source_ids"])
            target["names"].extend(group["names"])
            target["armies"].update(group["armies"])
            target["army_occurrences"].extend(group["army_occurrences"])
            del groups[key]
    return list(groups.values())


def army_name(row: sqlite3.Row) -> str:
    if row["name"]:
        return row["name"]
    if row["slug"] == "reinf":
        return f"Reinforcements ({row['id']})"
    if row["slug"]:
        derived_name = re.sub(r"[_-]+", " ", row["slug"]).strip().title()
        if derived_name:
            return derived_name
    return f"Army {row['id']}"


def unit_optional_modes(group: dict[str, Any]) -> set[str]:
    """Return optional modes encoded in a dedicated unit's name or slug."""
    labels = [*group["names"], group.get("slug") or ""]
    normalized = " ".join(
        re.sub(r"[^a-z0-9]+", "-", label.casefold()).strip("-") for label in labels
    )
    modes = set()
    if "spec-ops" in normalized or "specops" in normalized:
        modes.add("specops")
    if "team-ops" in normalized or "teamops" in normalized:
        modes.add("teamops")
    return modes


def army_is_available(
    army: dict[str, Any], group: dict[str, Any], selected_flags: set[str]
) -> bool:
    """Return whether an army occurrence needs only enabled optional modes."""
    return army_required_flags(army, group) <= selected_flags


def army_required_flags(
    army: dict[str, Any],
    group: dict[str, Any],
    canonical_faction_id: int | None = None,
    normal_army_ids: set[int] | None = None,
) -> set[str]:
    """Return the optional availability categories required by an occurrence."""
    required = unit_optional_modes(group)
    faction_id = (
        group["canonical_faction_id"] if canonical_faction_id is None else canonical_faction_id
    )
    normal_armies = group["normal_army_ids"] if normal_army_ids is None else normal_army_ids
    if faction_id == 1 and army["id"] not in normal_armies:
        required.add("mercs")
    if is_reinforcement_army_id(army["id"]):
        required.add("reinforcement")
    filters = army.get("filters")
    if isinstance(filters, dict):
        required.update(flag for flag in AVAILABILITY_FLAGS if filters.get(flag))
    return required


class Database:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        if not self.path.is_file():
            raise ValueError(f"Database does not exist: {self.path}. Build it before serving.")
        connection = sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.create_function("casefold", 1, lambda value: (value or "").casefold())
        connection.create_function("unit_sort_key", 1, unit_sort_key)
        try:
            connection.execute("BEGIN")
            yield connection
        finally:
            connection.close()

    def validate(self) -> None:
        """Reject missing, unrelated, unsupported, incomplete, or corrupt databases."""
        with self._connect() as connection:
            application_id = connection.execute("PRAGMA application_id").fetchone()[0]
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if application_id != APPLICATION_ID or version != SCHEMA_VERSION:
                raise ValueError("Unsupported InfinityDB database; rebuild it from normalized JSON")
            for name, definition in TABLES.items():
                columns = {
                    row["name"] for row in connection.execute(f"PRAGMA table_info({quote(name)})")
                }
                if not {*definition.key, *definition.fields, ROW_JSON} <= columns:
                    raise ValueError(f"Incomplete database schema: {name}; rebuild the database")
            row = connection.execute(
                f"SELECT value FROM {quote(METADATA_TABLE)} WHERE key = ?", ("_meta",)
            ).fetchone()
            try:
                meta = json.loads(row["value"]) if row else None
            except (json.JSONDecodeError, TypeError) as exc:
                raise ValueError("Database has invalid import metadata") from exc
            if (
                not isinstance(meta, dict)
                or meta.get("format") != FORMAT_NAME
                or meta.get("formatVersion") != FORMAT_VERSION
            ):
                raise ValueError("Database has invalid normalized format metadata")
            compatibility = connection.execute(
                f"SELECT value FROM {quote(METADATA_TABLE)} WHERE key = ?",
                (DATABASE_COMPATIBILITY_KEY,),
            ).fetchone()
            try:
                compatibility_version = (
                    json.loads(compatibility["value"]) if compatibility else None
                )
            except (json.JSONDecodeError, TypeError) as exc:
                raise ValueError("Database has invalid compatibility metadata") from exc
            if compatibility_version != DATABASE_COMPATIBILITY_VERSION:
                raise ValueError(
                    "Database compatibility revision does not match this application; "
                    "rebuild the database"
                )
            if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Database integrity check failed")
            if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise ValueError("Database contains broken foreign keys")

    def snapshot_downloaded_on(self) -> date | None:
        """Return the raw snapshot's download date, when recorded by the build."""
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT value FROM {quote(METADATA_TABLE)} WHERE key = ?", ("_meta",)
            ).fetchone()
        try:
            value = json.loads(row["value"]).get("snapshotDownloadedOn") if row else None
            return date.fromisoformat(value) if isinstance(value, str) else None
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    def list_armies(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT a.id, a.name, a.slug, a.kind, u.id AS unit_id "
                "FROM army_lists AS a "
                "LEFT JOIN army_units AS au ON au.army_id = a.id "
                "LEFT JOIN units AS u ON u.id = au.unit_id AND u.source_defined = 1 "
                "ORDER BY a.id"
            ).fetchall()
            armies: dict[int, dict[str, Any]] = {}
            for row in rows:
                source_army_id = row["id"]
                preferred_army_id = canonical_army_id(source_army_id)
                if preferred_army_id not in armies or source_army_id == preferred_army_id:
                    armies[preferred_army_id] = {
                        "id": preferred_army_id,
                        "name": army_name(row),
                        "slug": row["slug"],
                        "kind": row["kind"],
                        "unit_ids": armies.get(preferred_army_id, {}).get("unit_ids", set()),
                    }
                if row["unit_id"] is not None:
                    armies[preferred_army_id]["unit_ids"].add(row["unit_id"])
            return [
                {
                    "id": army["id"],
                    "name": army["name"],
                    "slug": army["slug"],
                    "kind": army["kind"],
                    "unit_count": len(army["unit_ids"]),
                }
                for army in sorted(armies.values(), key=lambda army: army["id"])
            ]

    def list_skill_extras(self) -> list[dict[str, Any]]:
        """Return candidate distance-related skill and extra pairings."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT combinations.skill_id, COALESCE(NULLIF(s.name, ''), "
                "'Skill #' || combinations.skill_id) AS skill_name, combinations.extra_id, "
                "COALESCE(NULLIF(e.name, ''), 'Extra #' || combinations.extra_id) AS extra_name, "
                f"u.id AS unit_id, {UNIT_NAME_SQL} AS unit_name "
                "FROM ("
                "SELECT ps.item_id AS skill_id, pse.extra_id, ps.unit_id FROM profile_skills AS ps "
                "JOIN profile_skill_extras AS pse ON pse.occurrence_id = ps.occurrence_id "
                "UNION "
                "SELECT os.item_id AS skill_id, ose.extra_id, os.unit_id FROM option_skills AS os "
                "JOIN option_skill_extras AS ose ON ose.occurrence_id = os.occurrence_id "
                "UNION "
                "SELECT uos.item_id AS skill_id, uose.extra_id, uos.unit_id FROM unit_option_skills AS uos "
                "JOIN unit_option_skill_extras AS uose ON uose.occurrence_id = uos.occurrence_id"
                ") AS combinations "
                "LEFT JOIN skills AS s ON s.id = combinations.skill_id "
                "LEFT JOIN extras AS e ON e.id = combinations.extra_id "
                "JOIN units AS u ON u.id = combinations.unit_id AND u.source_defined = 1 "
                "ORDER BY casefold(skill_name), casefold(extra_name), combinations.skill_id, "
                "combinations.extra_id, unit_sort_key(unit_name), u.id"
            ).fetchall()
            combinations: dict[tuple[Any, Any], dict[str, Any]] = {}
            for row in rows:
                if not contains_distance_multiple(row["extra_name"]):
                    continue
                display_extra_name = canonical_skill_extra_name(
                    row["skill_name"], row["extra_name"]
                )
                # The normalized display text is the semantic pair identity.
                # This retains ordinary sign differences while applying the
                # known Super-Jump and Forward Deployment conventions.
                key = (row["skill_id"], display_extra_name)
                item = combinations.setdefault(
                    key,
                    {
                        "skill_id": row["skill_id"],
                        "skill_name": row["skill_name"],
                        "extra_id": row["extra_id"],
                        "extra_name": display_extra_name,
                        "is_distance": True,
                        "units": [],
                    },
                )
                unit = {"id": row["unit_id"], "name": row["unit_name"]}
                if unit not in item["units"]:
                    item["units"].append(unit)
            return list(combinations.values())

    def list_catalog_items(self, catalog: str) -> list[dict[str, Any]]:
        """Return the named records in one of the public rules reference catalogs."""
        metadata_tables = {
            "skills": "metadata_skills",
            "equipment": "metadata_equipment",
            "weapons": "metadata_weapons",
        }
        try:
            metadata_table = metadata_tables[catalog]
        except KeyError as exc:
            raise ValueError(f"Unknown catalog: {catalog}") from exc

        with self._connect() as connection:
            if catalog == "weapons":
                rows = connection.execute(
                    "SELECT c.id, COALESCE(NULLIF(c.name, ''), MIN(NULLIF(m.name, '')), "
                    "'Weapon #' || c.id) AS name, "
                    "c.category, "
                    "GROUP_CONCAT(DISTINCT NULLIF(m.type, '')) AS type, "
                    "GROUP_CONCAT(DISTINCT NULLIF(m.ammunition, '')) AS ammunition, "
                    "GROUP_CONCAT(DISTINCT NULLIF(m.properties, '')) AS properties "
                    "FROM weapons AS c LEFT JOIN metadata_weapons AS m ON m.id = c.id "
                    "GROUP BY c.id, c.name "
                    "ORDER BY casefold(c.name), c.id"
                ).fetchall()
            else:
                rows = connection.execute(
                    f"SELECT c.id, COALESCE(NULLIF(c.name, ''), NULLIF(m.name, ''), "
                    f"'{catalog[:-1].title()} #' || c.id) AS name, m.wiki "
                    f"FROM {catalog} AS c LEFT JOIN {metadata_table} AS m ON m.id = c.id "
                    "ORDER BY casefold(c.name), c.id"
                ).fetchall()
            items = [dict(row) for row in rows]
            suffix = {"skills": "skill", "equipment": "equipment", "weapons": "weapon"}[catalog]
            option_usage = (
                "SELECT 'option', t.item_id, o.occurrence_id, o.unit_id "
                "FROM option_weapons AS o JOIN option_weapon_templates AS t "
                "ON t.id = o.template_id"
                if catalog == "weapons"
                else f"SELECT 'option', item_id, occurrence_id, unit_id FROM option_{catalog}"
            )
            usage_rows = connection.execute(
                "SELECT uses.source, uses.item_id, uses.occurrence_id, uses.unit_id, links.extra_id "
                "FROM units AS u JOIN ("
                f"SELECT 'profile' AS source, item_id, occurrence_id, unit_id FROM profile_{catalog} "
                f"UNION ALL {option_usage} "
                f"UNION ALL SELECT 'unit_option', item_id, occurrence_id, unit_id FROM unit_option_{catalog}"
                ") AS uses ON uses.unit_id = u.id LEFT JOIN ("
                f"SELECT 'profile' AS source, occurrence_id, position, extra_id FROM profile_{suffix}_extras "
                f"UNION ALL SELECT 'option', occurrence_id, position, extra_id FROM option_{suffix}_extras "
                f"UNION ALL SELECT 'unit_option', occurrence_id, position, extra_id FROM unit_option_{suffix}_extras"
                ") AS links ON links.source = uses.source AND links.occurrence_id = uses.occurrence_id "
                "WHERE u.source_defined = 1 "
                "ORDER BY uses.source, uses.occurrence_id, links.position"
            ).fetchall()
            occurrences: dict[tuple[str, int], dict[str, Any]] = {}
            for row in usage_rows:
                occurrence = occurrences.setdefault(
                    (row["source"], row["occurrence_id"]),
                    {"item_id": row["item_id"], "unit_id": row["unit_id"], "extras": []},
                )
                if row["extra_id"] is not None:
                    occurrence["extras"].append(row["extra_id"])
            units = []
            offset = 0
            while True:
                page = self.list_units(limit=500, offset=offset, specops=True)
                units.extend(page["items"])
                offset += len(page["items"])
                if offset >= page["total"]:
                    break
            displayed_unit_ids = {
                source_id: unit["id"] for unit in units for source_id in unit["source_ids"]
            }
            use_keys: dict[int, set[tuple[int, tuple[int, ...]]]] = {}
            for occurrence in occurrences.values():
                unit_id = displayed_unit_ids.get(occurrence["unit_id"])
                if unit_id is not None:
                    use_keys.setdefault(occurrence["item_id"], set()).add(
                        (unit_id, tuple(occurrence["extras"]))
                    )
            for item in items:
                item["use_count"] = len(use_keys.get(item["id"], set()))
            if catalog not in {"skills", "equipment", "weapons"}:
                return items
            groups: dict[str, list[dict[str, Any]]] = {}
            for item in items:
                if catalog == "skills":
                    canonical_id = SKILL_NAME_EXCEPTION_ALIASES.get(item["id"])
                    merge_key = skill_merge_key(item["name"])
                else:
                    canonical_id = CATALOG_NAME_EXCEPTION_ALIASES.get((catalog, item["id"]))
                    merge_key = catalog_merge_key(item["name"])
                key = f"alias:{canonical_id}" if canonical_id is not None else merge_key
                groups.setdefault(key or f"id:{item['id']}", []).append(item)
            merged = []
            for group in groups.values():
                canonical_id = next(
                    (
                        CATALOG_NAME_EXCEPTION_ALIASES.get((catalog, item["id"]))
                        for item in group
                        if CATALOG_NAME_EXCEPTION_ALIASES.get((catalog, item["id"])) is not None
                    ),
                    None,
                )
                representative = next(
                    (item for item in group if item["id"] == canonical_id),
                    min(group, key=lambda item: item["id"]),
                )
                if len(group) > 1:
                    representative = {
                        **representative,
                        "name": merged_catalog_name(representative["name"]),
                    }
                representative["use_count"] = sum(item["use_count"] for item in group)
                merged.append(representative)
            return sorted(merged, key=lambda item: (unit_sort_key(item["name"]), item["id"]))

    def get_catalog_item(self, catalog: str, item_id: int) -> dict[str, Any] | None:
        """Return an equipment or weapon item and its extra-specific unit usage."""
        tables = {
            "equipment": ("equipment", "metadata_equipment", "equipment"),
            "weapons": ("weapons", "metadata_weapons", "weapon"),
        }
        if catalog not in tables:
            raise ValueError(f"Unknown catalog: {catalog}")
        if type(item_id) is not int or not 0 <= item_id <= SQLITE_INTEGER_MAX:
            raise ValueError("item_id must be an integer within SQLite's signed 64-bit range")
        item_table, metadata_table, suffix = tables[catalog]
        with self._connect() as connection:
            catalog_items = connection.execute(
                f"SELECT id, COALESCE(NULLIF(name, ''), '{catalog[:-1].title()} #' || id) AS name "
                f"FROM {item_table}"
            ).fetchall()
            selected = next((row for row in catalog_items if row["id"] == item_id), None)
            if selected is None:
                return None
            canonical_id = CATALOG_NAME_EXCEPTION_ALIASES.get((catalog, item_id))
            if canonical_id is not None:
                source_ids = tuple(
                    row["id"]
                    for row in catalog_items
                    if CATALOG_NAME_EXCEPTION_ALIASES.get((catalog, row["id"])) == canonical_id
                )
                if canonical_id not in source_ids:
                    canonical_id = min(source_ids)
            else:
                merge_key = catalog_merge_key(selected["name"])
                source_ids = tuple(
                    row["id"]
                    for row in catalog_items
                    if merge_key is not None and catalog_merge_key(row["name"]) == merge_key
                ) or (item_id,)
                canonical_id = min(source_ids)
            placeholders = ", ".join("?" for _ in source_ids)
            item = connection.execute(
                f"SELECT c.id, COALESCE(NULLIF(c.name, ''), NULLIF(m.name, ''), "
                f"'{catalog[:-1].title()} #' || c.id) AS name "
                f"FROM {item_table} AS c LEFT JOIN {metadata_table} AS m ON m.id = c.id "
                "WHERE c.id = ?",
                (canonical_id,),
            ).fetchone()
            option_usage = (
                "SELECT 'option', t.item_id, o.occurrence_id, o.unit_id "
                "FROM option_weapons AS o JOIN option_weapon_templates AS t "
                "ON t.id = o.template_id "
                f"WHERE t.item_id IN ({placeholders}) "
                if catalog == "weapons"
                else f"SELECT 'option', item_id, occurrence_id, unit_id FROM option_{catalog} "
                f"WHERE item_id IN ({placeholders}) "
            )
            rows = connection.execute(
                "SELECT uses.source, uses.item_id, uses.occurrence_id, uses.unit_id, "
                + UNIT_NAME_SQL
                + " AS unit_name, links.position AS extra_position, e.id AS extra_id, e.name AS extra_name "
                "FROM units AS u JOIN ("
                f"SELECT 'profile' AS source, item_id, occurrence_id, unit_id FROM profile_{catalog} WHERE item_id IN ({placeholders}) "
                f"UNION ALL {option_usage}"
                f"UNION ALL SELECT 'unit_option', item_id, occurrence_id, unit_id FROM unit_option_{catalog} WHERE item_id IN ({placeholders})"
                ") AS uses ON uses.unit_id = u.id LEFT JOIN ("
                f"SELECT 'profile' AS source, occurrence_id, position, extra_id FROM profile_{suffix}_extras "
                f"UNION ALL SELECT 'option', occurrence_id, position, extra_id FROM option_{suffix}_extras "
                f"UNION ALL SELECT 'unit_option', occurrence_id, position, extra_id FROM unit_option_{suffix}_extras"
                ") AS links ON links.source = uses.source AND links.occurrence_id = uses.occurrence_id "
                "LEFT JOIN extras AS e ON e.id = links.extra_id WHERE u.source_defined = 1 "
                "ORDER BY uses.source, uses.occurrence_id, links.position, unit_sort_key(unit_name), u.id",
                source_ids * 3,
            ).fetchall()
            occurrences: dict[tuple[str, Any], dict[str, Any]] = {}
            for row in rows:
                occurrence = occurrences.setdefault(
                    (row["source"], row["occurrence_id"]),
                    {
                        "item_id": row["item_id"],
                        "unit": {"id": row["unit_id"], "name": row["unit_name"]},
                        "extras": [],
                    },
                )
                if row["extra_id"] is not None:
                    occurrence["extras"].append({"id": row["extra_id"], "name": row["extra_name"]})
            units = []
            offset = 0
            while True:
                page = self.list_units(limit=500, offset=offset, specops=True)
                units.extend(page["items"])
                offset += len(page["items"])
                if offset >= page["total"]:
                    break
            units_by_source = {
                source_id: unit for unit in units for source_id in unit["source_ids"]
            }
            item_names = {row["id"]: row["name"] for row in catalog_items}
            variants: dict[tuple[Any, tuple[tuple[Any, Any], ...]], dict[str, Any]] = {}
            for occurrence in occurrences.values():
                extras = occurrence["extras"]
                key = (
                    occurrence["item_id"],
                    tuple((extra["id"], extra["name"]) for extra in extras),
                )
                variant = variants.setdefault(
                    key,
                    {
                        "item_id": occurrence["item_id"],
                        "item_name": item_names[occurrence["item_id"]],
                        "extras": extras,
                        "units": [],
                    },
                )
                unit = units_by_source.get(occurrence["unit"]["id"])
                if unit is not None and unit not in variant["units"]:
                    variant["units"].append(unit)
            for variant in variants.values():
                variant["units"].sort(key=lambda unit: (unit_sort_key(unit["name"]), unit["id"]))
            result = {
                **dict(item),
                "id": canonical_id,
                "name": merged_catalog_name(item["name"]) if len(source_ids) > 1 else item["name"],
                "variants": list(variants.values()),
            }
            if catalog == "weapons":
                profile_rows = connection.execute(
                    "SELECT m.position, m.id, m.type, m.name, m.ammunition, m.burst, m.damage, "
                    "m.saving, m.savingNum, m.properties, m.distance, m.__row_json, "
                    "a.name AS ammunition_name "
                    "FROM metadata_weapons AS m "
                    "LEFT JOIN metadata_ammunitions AS a ON a.id = m.ammunition "
                    f"WHERE m.id IN ({placeholders}) ORDER BY m.position",
                    source_ids,
                ).fetchall()

                def decoded(value: Any, default: Any) -> Any:
                    if value is None:
                        return default
                    if not isinstance(value, str):
                        return value
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value

                profiles = []
                for profile in profile_rows:
                    source = decoded(profile[ROW_JSON], {})
                    item = {
                        "id": profile["id"],
                        "name": profile["name"],
                        "mode": source.get("mode") if isinstance(source, dict) else None,
                        "type": profile["type"],
                        "ammunition": profile["ammunition_name"] or profile["ammunition"],
                        "burst": profile["burst"],
                        "damage": profile["damage"],
                        "saving": profile["saving"],
                        "saving_num": profile["savingNum"],
                        "profile": source.get("profile") if isinstance(source, dict) else None,
                        "traits": decoded(profile["properties"], []),
                        "ranges": decoded(profile["distance"], {}),
                    }
                    if (item["id"], item["name"], item["mode"]) not in WEAPON_PROFILE_PLACEHOLDERS:
                        profiles.append(item)
                result["profiles"] = profiles
                profiles_by_id: dict[int, list[dict[str, Any]]] = {}
                for profile in profiles:
                    profiles_by_id.setdefault(profile["id"], []).append(profile)
                result["weapon_variants"] = [
                    {
                        "id": source_id,
                        "name": item_names[source_id],
                        "profiles": profiles_by_id[source_id],
                    }
                    for source_id in sorted(
                        profiles_by_id, key=lambda value: (unit_sort_key(item_names[value]), value)
                    )
                ]
                result["special_profile"] = special_weapon_detail(canonical_id)
            return result

    def get_skill(self, skill_id: int) -> dict[str, Any] | None:
        """Return one skill together with the units that use it."""
        if type(skill_id) is not int or not 0 <= skill_id <= SQLITE_INTEGER_MAX:
            raise ValueError("skill_id must be an integer within SQLite's signed 64-bit range")
        with self._connect() as connection:
            skills = connection.execute(
                "SELECT s.id, COALESCE(NULLIF(s.name, ''), NULLIF(m.name, ''), "
                "'Skill #' || s.id) AS name, m.wiki "
                "FROM skills AS s LEFT JOIN metadata_skills AS m ON m.id = s.id"
            ).fetchall()
            skill = next((row for row in skills if row["id"] == skill_id), None)
            if skill is None:
                return None
            canonical_id = SKILL_NAME_EXCEPTION_ALIASES.get(skill_id)
            if canonical_id is not None:
                source_ids = tuple(
                    row["id"]
                    for row in skills
                    if SKILL_NAME_EXCEPTION_ALIASES.get(row["id"]) == canonical_id
                )
                if canonical_id not in source_ids:
                    canonical_id = min(source_ids)
            else:
                merge_key = skill_merge_key(skill["name"])
                source_ids = tuple(
                    row["id"]
                    for row in skills
                    if merge_key is not None and skill_merge_key(row["name"]) == merge_key
                ) or (skill_id,)
                canonical_id = min(source_ids)
            representative = next(row for row in skills if row["id"] == canonical_id)
            placeholders = ", ".join("?" for _ in source_ids)
            rows = connection.execute(
                "SELECT uses.source, uses.skill_id, uses.occurrence_id, uses.unit_id, "
                + UNIT_NAME_SQL
                + " AS unit_name, extra_links.position AS extra_position, "
                "e.id AS extra_id, e.name AS extra_name "
                "FROM units AS u JOIN ("
                f"SELECT 'profile' AS source, item_id AS skill_id, occurrence_id, unit_id FROM profile_skills WHERE item_id IN ({placeholders}) "
                f"UNION ALL SELECT 'option', item_id, occurrence_id, unit_id FROM option_skills WHERE item_id IN ({placeholders}) "
                f"UNION ALL SELECT 'unit_option', item_id, occurrence_id, unit_id FROM unit_option_skills WHERE item_id IN ({placeholders})"
                ") AS uses ON uses.unit_id = u.id "
                "LEFT JOIN ("
                "SELECT 'profile' AS source, occurrence_id, position, extra_id FROM profile_skill_extras "
                "UNION ALL SELECT 'option', occurrence_id, position, extra_id FROM option_skill_extras "
                "UNION ALL SELECT 'unit_option', occurrence_id, position, extra_id FROM unit_option_skill_extras"
                ") AS extra_links ON extra_links.source = uses.source "
                "AND extra_links.occurrence_id = uses.occurrence_id "
                "LEFT JOIN extras AS e ON e.id = extra_links.extra_id "
                "WHERE u.source_defined = 1 "
                "ORDER BY uses.skill_id, uses.source, uses.occurrence_id, extra_links.position, "
                "unit_sort_key(unit_name), u.id",
                source_ids * 3,
            ).fetchall()
            occurrences: dict[tuple[str, Any], dict[str, Any]] = {}
            for row in rows:
                key = (row["source"], row["occurrence_id"])
                occurrence = occurrences.setdefault(
                    key,
                    {
                        "skill_id": row["skill_id"],
                        "unit": {
                            "id": row["unit_id"],
                            "name": row["unit_name"],
                        },
                        "extras": [],
                    },
                )
                if row["extra_id"] is not None:
                    extra = {
                        "id": row["extra_id"],
                        "name": row["extra_name"],
                    }
                    if contains_distance_multiple(row["extra_name"]):
                        extra["is_distance"] = True
                    occurrence["extras"].append(extra)
            variants: dict[tuple[Any, tuple[tuple[Any, Any], ...]], dict[str, Any]] = {}
            skill_names = {row["id"]: row["name"] for row in skills}
            for occurrence in occurrences.values():
                extras = occurrence["extras"]
                key = (
                    occurrence["skill_id"],
                    tuple((extra["id"], extra["name"]) for extra in extras),
                )
                variant = variants.setdefault(
                    key,
                    {
                        "skill_id": occurrence["skill_id"],
                        "skill_name": skill_names[occurrence["skill_id"]],
                        "extras": extras,
                        "units": [],
                    },
                )
                if occurrence["unit"] not in variant["units"]:
                    variant["units"].append(occurrence["unit"])
            unit_rows = connection.execute(
                f"SELECT u.id, {UNIT_NAME_SQL} AS name, u.isc, u.slug, u.main_army_id, "
                "u.canonical_faction_id FROM units AS u WHERE u.source_defined = 1 ORDER BY u.id"
            ).fetchall()
            memberships: dict[int, list[dict[str, Any]]] = {row["id"]: [] for row in unit_rows}
            membership_rows = connection.execute(
                "SELECT au.unit_id, au.filters, a.id, a.name, a.slug FROM army_units AS au "
                "JOIN army_lists AS a ON a.id = au.army_id ORDER BY a.id"
            )
            for army in membership_rows:
                if army["unit_id"] not in memberships:
                    continue
                try:
                    filters = json.loads(army["filters"]) if army["filters"] else {}
                except (TypeError, json.JSONDecodeError):
                    filters = {}
                memberships[army["unit_id"]].append(
                    {
                        "id": army["id"],
                        "name": army_name(army),
                        "filters": filters,
                    }
                )
            normal_armies_by_unit: dict[int, set[int]] = {row["id"]: set() for row in unit_rows}
            for faction in connection.execute("SELECT unit_id, faction_id FROM unit_factions"):
                if faction["unit_id"] in normal_armies_by_unit:
                    normal_armies_by_unit[faction["unit_id"]].add(faction["faction_id"])
            unit_items_by_source: dict[int, dict[str, Any]] = {}
            for group in logical_unit_groups(unit_rows, memberships):
                group["normal_army_ids"] = set().union(
                    *(normal_armies_by_unit[source_id] for source_id in group["source_ids"])
                )
                visible_armies = {
                    army_id: army
                    for army_id, army in group["armies"].items()
                    if army_is_available(army, group, {"specops"})
                }
                if group["armies"] and not visible_armies:
                    continue
                item = {
                    "id": group["id"],
                    "name": group["name"],
                    "isc": group["isc"],
                    "slug": group["slug"],
                    "main_army_id": group["main_army_id"],
                    "source_ids": group["source_ids"],
                    "army_ids": list(visible_armies),
                    "armies": [
                        {"id": army["id"], "name": army["name"]} for army in visible_armies.values()
                    ],
                }
                for source_id in group["source_ids"]:
                    unit_items_by_source[source_id] = item
            for variant in variants.values():
                items = {
                    item["id"]: item
                    for unit in variant["units"]
                    if (item := unit_items_by_source.get(unit["id"])) is not None
                }
                variant["units"] = sorted(
                    items.values(), key=lambda item: (unit_sort_key(item["name"]), item["id"])
                )
            return {
                **dict(representative),
                "id": canonical_id,
                "name": (
                    merged_skill_name(representative["name"])
                    if len(source_ids) > 1
                    else representative["name"]
                ),
                "variants": list(variants.values()),
            }

    def list_units(
        self,
        army_id: int | None = None,
        search: str = "",
        limit: int = 50,
        offset: int = 0,
        mercs: bool = False,
        specops: bool = False,
        teamops: bool = False,
        reinforcement: bool = False,
    ) -> dict[str, Any]:
        if army_id is not None and (
            type(army_id) is not int or not SQLITE_INTEGER_MIN <= army_id <= SQLITE_INTEGER_MAX
        ):
            raise ValueError("army_id must be an integer within SQLite's signed 64-bit range")
        if army_id is not None:
            army_id = canonical_army_id(army_id)
        if not isinstance(search, str):
            raise ValueError("search must be a string")
        if type(limit) is not int or not 1 <= limit <= 500:
            raise ValueError("limit must be an integer between 1 and 500")
        if type(offset) is not int or not 0 <= offset <= SQLITE_INTEGER_MAX:
            raise ValueError("offset must be a nonnegative integer at most 9223372036854775807")
        selected_flags = {
            flag
            for flag, enabled in {
                "mercs": mercs,
                "specops": specops,
                "teamops": teamops,
                "reinforcement": reinforcement,
            }.items()
            if enabled
        }
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT u.id, {UNIT_NAME_SQL} AS name, u.isc, u.slug, u.main_army_id, "
                "u.canonical_faction_id "
                "FROM units AS u WHERE u.source_defined = 1 ORDER BY u.id"
            ).fetchall()
            memberships: dict[int, list[dict[str, Any]]] = {row["id"]: [] for row in rows}
            if rows:
                army_rows = connection.execute(
                    "SELECT au.unit_id, au.filters, a.id, a.name, a.slug FROM army_units AS au "
                    "JOIN army_lists AS a ON a.id = au.army_id "
                    "ORDER BY a.id"
                )
                for army in army_rows:
                    if army["unit_id"] in memberships:
                        try:
                            filters = json.loads(army["filters"]) if army["filters"] else {}
                        except (TypeError, json.JSONDecodeError):
                            filters = {}
                        memberships[army["unit_id"]].append(
                            {
                                "id": army["id"],
                                "name": army_name(army),
                                "filters": filters,
                            }
                        )
            normal_armies_by_unit: dict[int, set[int]] = {row["id"]: set() for row in rows}
            faction_rows = connection.execute("SELECT unit_id, faction_id FROM unit_factions")
            for faction in faction_rows:
                if faction["unit_id"] in normal_armies_by_unit:
                    normal_armies_by_unit[faction["unit_id"]].add(faction["faction_id"])
            groups = logical_unit_groups(rows, memberships)
            for group in groups:
                group["normal_army_ids"] = set().union(
                    *(normal_armies_by_unit[source_id] for source_id in group["source_ids"])
                )
            search_key = accent_insensitive_key(search)
            grouped = []
            for group in groups:
                visible_armies = {
                    id: army
                    for id, army in group["armies"].items()
                    if army_is_available(army, group, selected_flags)
                }
                if group["armies"] and not visible_armies:
                    continue
                if army_id is not None and army_id not in visible_armies:
                    continue
                if search:
                    if search_key:
                        matches_search = any(
                            search_key in accent_insensitive_key(name) for name in group["names"]
                        )
                    else:
                        matches_search = any(
                            search.casefold() in str(name).casefold() for name in group["names"]
                        )
                    if not matches_search:
                        continue
                grouped.append({**group, "armies": visible_armies})
            grouped.sort(key=lambda group: (unit_sort_key(group["name"]), group["id"]))
            total = len(grouped)
            items = [
                {
                    "id": group["id"],
                    "name": group["name"],
                    "isc": group["isc"],
                    "slug": group["slug"],
                    "main_army_id": group["main_army_id"],
                    "source_ids": group["source_ids"],
                    "army_ids": list(group["armies"]),
                    "armies": [
                        {"id": army["id"], "name": army["name"]}
                        for army in group["armies"].values()
                    ],
                }
                for group in grouped[offset : offset + limit]
            ]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    def get_unit(self, unit_id: int) -> dict[str, Any] | None:
        """Return a browsable unit and its army-specific profiles and loadouts."""
        if type(unit_id) is not int or not 0 <= unit_id <= SQLITE_INTEGER_MAX:
            raise ValueError("unit_id must be a nonnegative SQLite signed 64-bit integer")
        with self._connect() as connection:
            selected = connection.execute(
                f"SELECT u.id, {UNIT_NAME_SQL} AS name, u.isc, u.isc_abbr, u.slug, u.notes, "
                "u.main_army_id "
                "FROM units AS u WHERE u.id = ? AND u.source_defined = 1",
                (unit_id,),
            ).fetchone()
            if selected is None:
                return None
            siblings = connection.execute(
                f"SELECT u.id, {UNIT_NAME_SQL} AS name, u.isc, u.isc_abbr, u.slug, u.notes, "
                "u.main_army_id, u.canonical_faction_id "
                "FROM units AS u WHERE u.source_defined = 1 ORDER BY u.id"
            ).fetchall()
            memberships: dict[int, list[dict[str, Any]]] = {row["id"]: [] for row in siblings}
            membership_rows = connection.execute(
                "SELECT au.unit_id, au.filters, a.id, a.name, a.slug FROM army_units AS au "
                "JOIN army_lists AS a ON a.id = au.army_id ORDER BY a.id"
            )
            for army in membership_rows:
                if army["unit_id"] in memberships:
                    try:
                        filters = json.loads(army["filters"]) if army["filters"] else {}
                    except (TypeError, json.JSONDecodeError):
                        filters = {}
                    memberships[army["unit_id"]].append(
                        {"id": army["id"], "name": army_name(army), "filters": filters}
                    )
            group = next(
                group
                for group in logical_unit_groups(siblings, memberships)
                if selected["id"] in group["source_ids"]
            )
            source_ids = group["source_ids"]
            unit = next(sibling for sibling in siblings if sibling["id"] == group["id"])
            normal_army_ids: dict[int, set[int]] = {row["id"]: set() for row in siblings}
            for faction in connection.execute("SELECT unit_id, faction_id FROM unit_factions"):
                if faction["unit_id"] in normal_army_ids:
                    normal_army_ids[faction["unit_id"]].add(faction["faction_id"])
            group["normal_army_ids"] = set().union(
                *(normal_army_ids[source_id] for source_id in source_ids)
            )
            canonical_factions = {row["id"]: row["canonical_faction_id"] for row in siblings}
            placeholders = ", ".join("?" for _ in source_ids)
            armies_by_occurrence: dict[tuple[int, tuple[str, ...]], dict[str, Any]] = {}
            by_source_army: dict[tuple[int, int], dict[str, Any]] = {}
            for occurrence in group["army_occurrences"]:
                source_id = occurrence["source_id"]
                flags = tuple(
                    sorted(
                        army_required_flags(
                            occurrence,
                            group,
                            canonical_factions[source_id],
                            normal_army_ids[source_id],
                        )
                    )
                )
                occurrence_key = (occurrence["id"], flags)
                army = armies_by_occurrence.setdefault(
                    occurrence_key,
                    {
                        "id": occurrence["id"],
                        "name": occurrence["name"],
                        "availability_flags": list(flags),
                        "profiles": [],
                        "loadouts": [],
                        "_occurrence_key": occurrence_key,
                    },
                )
                by_source_army[(source_id, occurrence["source_army_id"])] = army
            armies = list(armies_by_occurrence.values())
            profile_rows = connection.execute(
                "SELECT p.unit_id, p.army_id, p.group_id, p.profile_id, p.name, "
                "t.name AS type, c.name AS classification, p.move_1, p.move_2, "
                "p.cc, p.bs, p.ph, p.wip, p.arm, p.bts, p.vitality, p.silhouette, p.ava "
                "FROM profiles AS p "
                "LEFT JOIN troop_types AS t ON t.id = p.type_id "
                "JOIN profile_groups AS pg ON pg.army_id = p.army_id "
                "AND pg.unit_id = p.unit_id AND pg.group_id = p.group_id "
                "LEFT JOIN categories AS c ON c.id = pg.category_id "
                f"WHERE p.unit_id IN ({placeholders}) "
                "ORDER BY p.army_id, p.group_id, p.position, p.profile_id",
                source_ids,
            )
            profile_items: dict[tuple[Any, ...], dict[str, Any]] = {}
            profile_keys_by_source: dict[tuple[int, int, int, int], tuple[Any, ...]] = {}
            for profile in profile_rows:
                army = by_source_army.get((profile["unit_id"], profile["army_id"]))
                if army is None:
                    continue
                item = {
                    key: profile[key] for key in profile.keys() if key not in {"army_id", "unit_id"}
                }
                item["skills"] = []
                item["equipment"] = []
                item["weapons"] = []
                item["characteristics"] = []
                profile_key = (
                    army["_occurrence_key"],
                    profile["group_id"],
                    profile["profile_id"],
                    profile["name"],
                    profile["move_1"],
                    profile["move_2"],
                    profile["cc"],
                    profile["bs"],
                    profile["ph"],
                    profile["wip"],
                    profile["arm"],
                    profile["bts"],
                    profile["vitality"],
                    profile["silhouette"],
                    profile["type"],
                    profile["classification"],
                )
                profile_keys_by_source[
                    (
                        profile["unit_id"],
                        profile["army_id"],
                        profile["group_id"],
                        profile["profile_id"],
                    )
                ] = profile_key
                existing = profile_items.get(profile_key)
                if existing is None:
                    army["profiles"].append(item)
                    profile_items[profile_key] = item
                else:
                    merge_profile(existing, item)
            for occurrence_table, catalog_table, property_name, extras_table in (
                ("profile_skills", "skills", "skills", "profile_skill_extras"),
                ("profile_equipment", "equipment", "equipment", "profile_equipment_extras"),
                ("profile_weapons", "weapons", "weapons", "profile_weapon_extras"),
            ):
                extras_by_occurrence: dict[Any, list[dict[str, Any]]] = {}
                extra_rows = connection.execute(
                    "SELECT e.occurrence_id, e.extra_id, x.name "
                    f"FROM {extras_table} AS e "
                    f"JOIN {occurrence_table} AS o ON o.occurrence_id = e.occurrence_id "
                    "LEFT JOIN extras AS x ON x.id = e.extra_id "
                    f"WHERE o.unit_id IN ({placeholders}) "
                    "ORDER BY e.occurrence_id, e.position",
                    source_ids,
                )
                for extra in extra_rows:
                    item = {
                        "id": extra["extra_id"],
                        "name": extra["name"],
                    }
                    if property_name == "skills" and contains_distance_multiple(extra["name"]):
                        item["is_distance"] = True
                    extras_by_occurrence.setdefault(extra["occurrence_id"], []).append(item)
                occurrence_rows = connection.execute(
                    "SELECT o.occurrence_id, o.unit_id, o.army_id, o.group_id, o.profile_id, o.item_id, "
                    "o.quantity, o.position, c.name "
                    f"FROM {occurrence_table} AS o "
                    f"LEFT JOIN {catalog_table} AS c ON c.id = o.item_id "
                    f"WHERE o.unit_id IN ({placeholders}) "
                    "ORDER BY o.army_id, o.group_id, o.profile_id, o.position, o.occurrence_id",
                    source_ids,
                )
                for occurrence in occurrence_rows:
                    profile_key = profile_keys_by_source.get(
                        (
                            occurrence["unit_id"],
                            occurrence["army_id"],
                            occurrence["group_id"],
                            occurrence["profile_id"],
                        )
                    )
                    profile = profile_items.get(profile_key) if profile_key is not None else None
                    if profile is not None:
                        append_unique_item(
                            profile[property_name],
                            {
                                "id": occurrence["item_id"],
                                "name": occurrence["name"],
                                "quantity": occurrence["quantity"],
                                "extras": extras_by_occurrence.get(occurrence["occurrence_id"], []),
                            },
                        )
            characteristic_rows = connection.execute(
                "SELECT o.unit_id, o.army_id, o.group_id, o.profile_id, c.name "
                "FROM profile_characteristics AS o "
                "JOIN characteristics AS c ON c.id = o.characteristic_id "
                f"WHERE o.unit_id IN ({placeholders}) "
                "ORDER BY o.army_id, o.group_id, o.profile_id, o.position",
                source_ids,
            )
            for characteristic in characteristic_rows:
                profile_key = profile_keys_by_source.get(
                    (
                        characteristic["unit_id"],
                        characteristic["army_id"],
                        characteristic["group_id"],
                        characteristic["profile_id"],
                    )
                )
                profile = profile_items.get(profile_key) if profile_key is not None else None
                if profile is not None:
                    profile["characteristics"].append({"name": characteristic["name"]})
            loadout_rows = connection.execute(
                "SELECT o.unit_id, o.army_id, o.group_id, o.option_id, o.name, o.points, o.swc, "
                "o.minis, o.disabled "
                f"FROM loadout_options AS o WHERE o.unit_id IN ({placeholders}) "
                "ORDER BY o.army_id, o.group_id, o.position, o.option_id",
                source_ids,
            )
            loadout_items: dict[tuple[Any, ...], dict[str, Any]] = {}
            loadout_keys_by_source: dict[tuple[int, int, int, int], tuple[Any, ...]] = {}
            for loadout in loadout_rows:
                army = by_source_army.get((loadout["unit_id"], loadout["army_id"]))
                if army is None:
                    continue
                item = {
                    key: loadout[key] for key in loadout.keys() if key not in {"army_id", "unit_id"}
                }
                item["skills"] = []
                item["equipment"] = []
                item["weapons"] = []
                item["orders"] = []
                loadout_key = (
                    army["_occurrence_key"],
                    loadout["group_id"],
                    loadout["option_id"],
                    loadout["name"],
                    loadout["points"],
                    loadout["swc"],
                    loadout["minis"],
                    loadout["disabled"],
                )
                loadout_keys_by_source[
                    (
                        loadout["unit_id"],
                        loadout["army_id"],
                        loadout["group_id"],
                        loadout["option_id"],
                    )
                ] = loadout_key
                if loadout_key not in loadout_items:
                    army["loadouts"].append(item)
                    loadout_items[loadout_key] = item
            order_rows = connection.execute(
                "SELECT o.unit_id, o.army_id, o.group_id, o.option_id, o.order_type, "
                "o.list_count, o.total_count "
                f"FROM option_orders AS o WHERE o.unit_id IN ({placeholders}) "
                "ORDER BY o.army_id, o.group_id, o.option_id, o.position",
                source_ids,
            )
            for order in order_rows:
                loadout_key = loadout_keys_by_source.get(
                    (
                        order["unit_id"],
                        order["army_id"],
                        order["group_id"],
                        order["option_id"],
                    )
                )
                loadout = loadout_items.get(loadout_key) if loadout_key is not None else None
                if loadout is not None:
                    order_type = order["order_type"]
                    loadout["orders"].append(
                        {
                            "type": order_type.lower()
                            if isinstance(order_type, str)
                            else order_type,
                            "list": order["list_count"],
                            "total": order["total_count"],
                        }
                    )
            for occurrence_table, catalog_table, property_name, extras_table in (
                ("option_skills", "skills", "skills", "option_skill_extras"),
                ("option_equipment", "equipment", "equipment", "option_equipment_extras"),
                ("option_weapons", "weapons", "weapons", "option_weapon_extras"),
            ):
                extras_by_occurrence = {}
                extra_rows = connection.execute(
                    "SELECT e.occurrence_id, e.extra_id, x.name "
                    f"FROM {extras_table} AS e "
                    f"JOIN {occurrence_table} AS o ON o.occurrence_id = e.occurrence_id "
                    "LEFT JOIN extras AS x ON x.id = e.extra_id "
                    f"WHERE o.unit_id IN ({placeholders}) "
                    "ORDER BY e.occurrence_id, e.position",
                    source_ids,
                )
                for extra in extra_rows:
                    item = {
                        "id": extra["extra_id"],
                        "name": extra["name"],
                    }
                    if property_name == "skills" and contains_distance_multiple(extra["name"]):
                        item["is_distance"] = True
                    extras_by_occurrence.setdefault(extra["occurrence_id"], []).append(item)
                item_column = "o.item_id"
                quantity_column = "o.quantity"
                occurrence_source = f"FROM {occurrence_table} AS o"
                if occurrence_table == "option_weapons":
                    item_column = "t.item_id"
                    quantity_column = "t.quantity"
                    occurrence_source += (
                        " JOIN option_weapon_templates AS t ON t.id = o.template_id"
                    )
                occurrence_rows = connection.execute(
                    "SELECT o.occurrence_id, o.unit_id, o.army_id, o.group_id, o.option_id, "
                    f"{item_column} AS item_id, {quantity_column} AS quantity, o.position, c.name "
                    f"{occurrence_source} "
                    f"LEFT JOIN {catalog_table} AS c ON c.id = {item_column} "
                    f"WHERE o.unit_id IN ({placeholders}) "
                    "ORDER BY o.army_id, o.group_id, o.option_id, o.position, o.occurrence_id",
                    source_ids,
                )
                for occurrence in occurrence_rows:
                    loadout_key = loadout_keys_by_source.get(
                        (
                            occurrence["unit_id"],
                            occurrence["army_id"],
                            occurrence["group_id"],
                            occurrence["option_id"],
                        )
                    )
                    loadout = loadout_items.get(loadout_key) if loadout_key is not None else None
                    if loadout is not None:
                        append_unique_item(
                            loadout[property_name],
                            {
                                "id": occurrence["item_id"],
                                "name": occurrence["name"],
                                "quantity": occurrence["quantity"],
                                "extras": extras_by_occurrence.get(occurrence["occurrence_id"], []),
                            },
                        )
            for army in armies:
                del army["_occurrence_key"]
        return {
            "id": unit["id"],
            "name": unit["name"],
            "isc": unit["isc"],
            "slug": unit["slug"],
            "isc_abbr": unit["isc_abbr"],
            "notes": unit["notes"],
            "main_army_id": group["main_army_id"],
            "source_ids": source_ids,
            "armies": armies,
        }
