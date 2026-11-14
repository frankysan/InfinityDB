#!/usr/bin/env python3
"""Report 1.0 source/publication evidence without declaring reference completeness.

This is a read-only cross-source inventory, not a new coverage classification
policy. Source-to-API/browser decisions must be reviewed against the pinned inputs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from collections import Counter
from collections.abc import Sequence
from contextlib import ExitStack, closing
from pathlib import Path, PureWindowsPath
from typing import Any
from urllib.parse import parse_qs, urlsplit

from infinity_army_data.merge import SourceDocument, load_sources, merge_sources
from infinity_db.application_domains import application_domain, semantic_record_domain
from infinity_db.database.paths import raw_database_path
from infinity_db.database.publication import validate_database_pair
from infinity_db.snapshot_revision import database_set_snapshot_revision
from infinity_db.variant_usage_source import normalized_source_connection
from infinity_db.weapon_profile_publication import load_runtime_weapon_profile_publication

if __package__:
    from .research.source_paths import SourcePathError, pinned_pdf_path
    from .served_runtime import ServedRuntimeError, verify_served_runtime
else:
    from research.source_paths import SourcePathError, pinned_pdf_path
    from served_runtime import ServedRuntimeError, verify_served_runtime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_FORMAT = "InfinityDB 1.0 reference evidence baseline"
REPORT_VERSION = 2


class ReferenceBaselineError(ValueError):
    """The supplied published data cannot provide a trustworthy baseline."""


def _require_new_report_outputs(*paths: Path | None) -> None:
    """Preflight every selected report before costly source/audit work."""
    seen: set[Path] = set()
    for path in paths:
        if path is None:
            continue
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"Reference baseline output already exists: {path}")
        resolved = path.resolve()
        if resolved in seen:
            raise ReferenceBaselineError(
                "Reference baseline report outputs must be different files"
            )
        seen.add(resolved)


def _write_new_report(path: Path, content: str) -> None:
    """Write UTF-8/LF evidence without replacing a previous accepted report."""
    _require_new_report_outputs(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def _write_report_or_exit(
    parser: argparse.ArgumentParser, path: Path, content: str,
) -> None:
    try:
        _write_new_report(path, content)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Reference baseline output: {exc}\n")


def _connect(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ReferenceBaselineError(f"Published database is unavailable: {path}")
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _metadata(connection: sqlite3.Connection, table: str) -> dict[str, Any]:
    try:
        rows = connection.execute(f'SELECT key, value FROM "{table}"').fetchall()
    except sqlite3.DatabaseError as exc:
        raise ReferenceBaselineError(f"Missing or unreadable {table}: {exc}") from exc
    try:
        return {row["key"]: json.loads(row["value"]) for row in rows}
    except (json.JSONDecodeError, TypeError) as exc:
        raise ReferenceBaselineError(f"Invalid JSON in {table}: {exc}") from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_location(root: Path, relative: str | None) -> str:
    if relative is None:
        return "url-backed/no-local-artifact"
    candidate = Path(relative)
    if (
        candidate.is_absolute()
        or bool(PureWindowsPath(relative).drive)
        or ".." in candidate.parts
        or ".." in PureWindowsPath(relative).parts
        or not (root / candidate).resolve().is_relative_to(root.resolve())
    ):
        return "unsafe-declared-path"
    return "available" if (root / candidate).is_file() else "missing-local-artifact"


_NESTED_SOURCE_FIELDS = {
    "profile_groups": (
        ("army_id", "unit_id", "group_id"),
        ("position", "category_id", "isc", "notes"),
    ),
    "profiles": (
        ("army_id", "unit_id", "group_id", "profile_id"),
        (
            "position", "name", "logo", "type_id", "move_1", "move_2",
            "cc", "bs", "ph", "wip", "arm", "bts", "vitality",
            "silhouette", "ava", "is_structure", "notes",
        ),
    ),
    "loadout_options": (
        ("army_id", "unit_id", "group_id", "option_id"),
        ("position", "name", "points", "swc", "minis", "disabled"),
    ),
}


def _verify_nested_source_rows(
    army: sqlite3.Connection, table: str, expected: list[tuple[Any, ...]]
) -> int:
    """Verify source-native keys, positions and scalar facts without reconstruction."""
    identity_columns, value_columns = _NESTED_SOURCE_FIELDS[table]
    columns = (*identity_columns, *value_columns)
    actual: dict[tuple[Any, ...], tuple[Any, ...]] = {}
    for row in army.execute(f"SELECT {', '.join(columns)} FROM {table}"):
        key = tuple(row[:len(identity_columns)])
        if key in actual:
            raise ReferenceBaselineError(f"{table}: duplicate published identity {key!r}")
        actual[key] = tuple(row[len(identity_columns):])

    original: dict[tuple[Any, ...], tuple[Any, ...]] = {}
    for row in expected:
        key = row[:len(identity_columns)]
        if key in original:
            raise ReferenceBaselineError(f"{table}: duplicate source identity {key!r}")
        original[key] = row[len(identity_columns):]

    missing = sorted(original.keys() - actual.keys())
    extra = sorted(actual.keys() - original.keys())
    if missing or extra:
        raise ReferenceBaselineError(
            f"{table} source identities differ from published storage: "
            f"missing={missing[:10]!r}, extra={extra[:10]!r}"
        )
    for key in sorted(original):
        if original[key] != actual[key]:
            columns_changed = [
                name for name, expected_value, actual_value
                in zip(value_columns, original[key], actual[key], strict=True)
                if expected_value != actual_value
            ]
            raise ReferenceBaselineError(
                f"{table} source facts differ at {key!r}: "
                f"fields={columns_changed!r}, expected={original[key]!r}, "
                f"actual={actual[key]!r}"
            )
    return len(original)


def _collect_source_profile_references(
    expected: dict[tuple[str, str], list[tuple[Any, ...]]],
    kind: str, parent: tuple[int, int, int, int], source: dict[str, Any],
) -> None:
    for field, source_field in (
        ("skills", "skills"), ("equipment", "equip"), ("weapons", "weapons"),
    ):
        for position, reference in enumerate(source.get(source_field) or [], start=1):
            if not isinstance(reference, dict):
                raise ReferenceBaselineError(
                    f"{kind}.{field} has non-object source occurrence at "
                    f"{parent!r}, position {position}"
                )
            expected[(kind, field)].append((
                *parent, position, reference.get("id"),
                reference.get("order"), reference.get("q"),
            ))


def _verify_published_profile_references(
    army: sqlite3.Connection,
    sources: list[SourceDocument],
) -> dict[str, int]:
    """Check source reference occurrences against the actual reusable payload views."""
    expected: dict[tuple[str, str], list[tuple[Any, ...]]] = {
        (kind, field): []
        for kind in ("profile", "loadout")
        for field in ("skills", "equipment", "weapons")
    }
    for source in sources:
        for unit in source.data["units"]:
            for group in unit.get("profileGroups") or []:
                parent = (source.faction_id, unit["id"], group["id"])
                for profile in group.get("profiles") or []:
                    _collect_source_profile_references(
                        expected, "profile", (*parent, profile["id"]), profile,
                    )
                for loadout in group.get("options") or []:
                    _collect_source_profile_references(
                        expected, "loadout", (*parent, loadout["id"]), loadout,
                    )
    result: dict[str, int] = {}
    for (kind, field), rows in sorted(expected.items()):
        payload_type = "profile" if kind == "profile" else "loadout"
        identity = "profile_id" if kind == "profile" else "option_id"
        occurrence_table = f"{payload_type}_payload_occurrences"
        reference_table = f"{payload_type}_payload_{field}"
        query = (
            f"SELECT o.army_id, o.unit_id, o.group_id, o.{identity}, "
            "r.position, r.item_id, r.display_order, r.quantity "
            f"FROM {occurrence_table} o JOIN {reference_table} r "
            f"ON r.{payload_type}_payload_id = o.{payload_type}_payload_id"
        )
        actual = [tuple(row) for row in army.execute(query)]
        source_by_key = {row[:5]: row[5:] for row in rows}
        published_by_key = {row[:5]: row[5:] for row in actual}
        if len(source_by_key) != len(rows) or len(published_by_key) != len(actual):
            raise ReferenceBaselineError(
                f"{kind}.{field}: duplicate source or published occurrence position"
            )
        missing = sorted(source_by_key.keys() - published_by_key.keys())
        extra = sorted(published_by_key.keys() - source_by_key.keys())
        if missing or extra:
            raise ReferenceBaselineError(
                f"{kind}.{field}: source/published reference identities differ: "
                f"missing={missing[:10]!r}, extra={extra[:10]!r}"
            )
        for key in sorted(source_by_key):
            if source_by_key[key] != published_by_key[key]:
                raise ReferenceBaselineError(
                    f"{kind}.{field}: published reference differs at {key!r}: "
                    f"source={source_by_key[key]!r}, published={published_by_key[key]!r}"
                )
        result[f"{kind}.{field}"] = len(rows)
    return result


def _verify_published_profile_extras(
    army: sqlite3.Connection,
    sources: list[SourceDocument],
) -> dict[str, int]:
    """Match ordered extra IDs through published reusable payload relationships."""
    expected: dict[tuple[str, str], list[tuple[int, ...]]] = {
        (kind, field): []
        for kind in ("profile", "loadout")
        for field in ("skills", "equipment", "weapons")
    }
    for source in sources:
        for unit in source.data["units"]:
            for group in unit.get("profileGroups") or []:
                parent = (source.faction_id, unit["id"], group["id"])
                for kind, rows in (
                    ("profile", group.get("profiles") or []),
                    ("loadout", group.get("options") or []),
                ):
                    for record in rows:
                        identity = (*parent, record["id"])
                        for field, source_field in (
                            ("skills", "skills"),
                            ("equipment", "equip"),
                            ("weapons", "weapons"),
                        ):
                            for occurrence_position, reference in enumerate(
                                record.get(source_field) or [], start=1
                            ):
                                extras = reference.get("extra")
                                # Non-array extra values are preserved as raw
                                # parent data by the normalizer, not emitted as rows.
                                if not isinstance(extras, list):
                                    continue
                                for extra_position, extra_id in enumerate(extras, start=1):
                                    expected[(kind, field)].append((
                                        *identity, occurrence_position,
                                        extra_position, extra_id,
                                    ))

    result: dict[str, int] = {}
    suffixes = {
        "skills": "skill_extras",
        "equipment": "equipment_extras",
        "weapons": "weapon_extras",
    }
    for (kind, field), rows in sorted(expected.items()):
        occurrence_table = f"{kind}_payload_occurrences"
        extras_table = f"{kind}_payload_{suffixes[field]}"
        identity_col = "profile_id" if kind == "profile" else "option_id"
        query = (
            f"SELECT o.army_id, o.unit_id, o.group_id, o.{identity_col}, "
            "e.occurrence_position, e.position, e.extra_id "
            f"FROM {occurrence_table} o JOIN {extras_table} e "
            f"ON e.{kind}_payload_id = o.{kind}_payload_id"
        )
        actual = [tuple(row) for row in army.execute(query)]
        key_length = 6
        source_by_key = {row[:key_length]: row[key_length:] for row in rows}
        actual_by_key = {row[:key_length]: row[key_length:] for row in actual}
        if len(source_by_key) != len(rows) or len(actual_by_key) != len(actual):
            raise ReferenceBaselineError(
                f"{kind}.{field}.extras: duplicate source or published extra position"
            )
        missing = sorted(source_by_key.keys() - actual_by_key.keys())
        extra = sorted(actual_by_key.keys() - source_by_key.keys())
        if missing or extra:
            raise ReferenceBaselineError(
                f"{kind}.{field}.extras: source/published extra positions differ: "
                f"missing={missing[:10]!r}, extra={extra[:10]!r}"
            )
        for key in sorted(source_by_key):
            if source_by_key[key] != actual_by_key[key]:
                raise ReferenceBaselineError(
                    f"{kind}.{field}.extras: published extra differs at {key!r}: "
                    f"source={source_by_key[key]!r}, published={actual_by_key[key]!r}"
                )
        result[f"{kind}.{field}"] = len(rows)
    return result


def _verify_published_characteristics_orders(
    army: sqlite3.Connection,
    sources: list[SourceDocument],
) -> dict[str, int]:
    """Check ordered Characteristics and modeled Order facts after payload reuse."""
    expected: dict[str, list[tuple[Any, ...]]] = {
        "profile.characteristics": [],
        "loadout.characteristics": [],
        "loadout.orders": [],
    }
    for source in sources:
        for unit in source.data["units"]:
            for group in unit.get("profileGroups") or []:
                parent = (source.faction_id, unit["id"], group["id"])
                for kind, rows in (
                    ("profile", group.get("profiles") or []),
                    ("loadout", group.get("options") or []),
                ):
                    for record in rows:
                        key = (*parent, record["id"])
                        for position, char_id in enumerate(
                            record.get("chars") or [], start=1
                        ):
                            expected[f"{kind}.characteristics"].append(
                                (*key, position, char_id)
                            )
                        if kind == "loadout":
                            for position, value in enumerate(
                                record.get("orders") or [], start=1
                            ):
                                order = value if isinstance(value, dict) else {}
                                expected["loadout.orders"].append((
                                    *key, position, order.get("type"),
                                    order.get("list"), order.get("total"),
                                ))

    result: dict[str, int] = {}
    for category, rows in expected.items():
        kind, field = category.split(".")
        identity = "profile_id" if kind == "profile" else "option_id"
        selected = (
            "r.characteristic_id"
            if field == "characteristics"
            else "r.order_type, r.list_count, r.total_count"
        )
        sql = (
            f"SELECT o.army_id, o.unit_id, o.group_id, o.{identity}, "
            f"r.position, {selected} "
            f"FROM {kind}_payload_occurrences o "
            f"JOIN {kind}_payload_{field} r "
            f"ON r.{kind}_payload_id = o.{kind}_payload_id"
        )
        published = [tuple(row) for row in army.execute(sql)]
        source_values = {row[:5]: row[5:] for row in rows}
        published_values = {row[:5]: row[5:] for row in published}
        if len(source_values) != len(rows) or len(published_values) != len(published):
            raise ReferenceBaselineError(
                f"{category}: duplicate source/published occurrence positions"
            )
        missing = sorted(source_values.keys() - published_values.keys())
        extra = sorted(published_values.keys() - source_values.keys())
        if missing or extra:
            raise ReferenceBaselineError(
                f"{category}: source/published occurrence positions differ: "
                f"missing={missing[:10]!r}, extra={extra[:10]!r}"
            )
        for key in sorted(source_values):
            if source_values[key] != published_values[key]:
                raise ReferenceBaselineError(
                    f"{category}: source/published facts differ at {key!r}: "
                    f"source={source_values[key]!r}, "
                    f"published={published_values[key]!r}"
                )
        result[category] = len(rows)
    return result


def _verify_published_peripherals_includes(
    army: sqlite3.Connection,
    sources: list[SourceDocument],
) -> dict[str, int]:
    """Verify contextual Peripheral occurrences and resolved Include targets.

    Peripheral IDs remain army-local source IDs. Include targets are the
    canonical payload IDs of the referenced (army, unit, group, option).
    This does not certify raw unknown fields or application-level identities.
    """
    expected: dict[str, list[tuple[Any, ...]]] = {
        "profile.peripherals": [],
        "loadout.peripherals": [],
        "profile.includes": [],
        "loadout.includes": [],
    }
    target_payloads = {
        tuple(row[:4]): row[4]
        for row in army.execute(
            "SELECT army_id, unit_id, group_id, option_id, loadout_payload_id "
            "FROM loadout_payload_occurrences"
        )
    }
    for source in sources:
        for unit in source.data["units"]:
            for group in unit.get("profileGroups") or []:
                prefix = (source.faction_id, unit["id"], group["id"])
                for kind, members in (
                    ("profile", group.get("profiles") or []),
                    ("loadout", group.get("options") or []),
                ):
                    for member in members:
                        parent = (*prefix, member["id"])
                        for position, item in enumerate(
                            member.get("peripheral") or [], start=1
                        ):
                            fields = item if isinstance(item, dict) else {}
                            expected[f"{kind}.peripherals"].append((
                                *parent, position, fields.get("id"),
                                fields.get("order"), fields.get("q"),
                            ))
                        for position, item in enumerate(
                            member.get("includes") or [], start=1
                        ):
                            fields = item if isinstance(item, dict) else {}
                            target = (*prefix[:2], fields.get("group"), fields.get("option"))
                            if target not in target_payloads:
                                raise ReferenceBaselineError(
                                    f"{kind}.includes: no published target for {target!r} "
                                    f"from {parent!r} position {position}"
                                )
                            expected[f"{kind}.includes"].append((
                                *parent, position, target_payloads[target],
                                fields.get("q"),
                            ))

    query_specs = {
        "profile.peripherals": (
            "SELECT army_id, unit_id, group_id, profile_id, position, "
            "item_id, display_order, quantity FROM profile_peripherals"
        ),
        "loadout.peripherals": (
            "SELECT army_id, unit_id, group_id, option_id, position, "
            "item_id, display_order, quantity FROM option_peripherals"
        ),
        "profile.includes": (
            "SELECT army_id, unit_id, group_id, profile_id, position, "
            "target_loadout_payload_id, quantity FROM profile_occurrence_includes"
        ),
        "loadout.includes": (
            "SELECT army_id, unit_id, group_id, option_id, position, "
            "target_loadout_payload_id, quantity FROM loadout_occurrence_includes"
        ),
    }
    counts: dict[str, int] = {}
    for kind, sql in query_specs.items():
        source_rows = expected[kind]
        stored_rows = [tuple(row) for row in army.execute(sql)]
        source_map = {row[:5]: row[5:] for row in source_rows}
        stored_map = {row[:5]: row[5:] for row in stored_rows}
        if len(source_map) != len(source_rows) or len(stored_map) != len(stored_rows):
            raise ReferenceBaselineError(f"{kind}: duplicate occurrence positions")
        missing = sorted(source_map.keys() - stored_map.keys())
        extra = sorted(stored_map.keys() - source_map.keys())
        if missing or extra:
            raise ReferenceBaselineError(
                f"{kind}: source/published occurrence positions differ: "
                f"missing={missing[:10]!r}, extra={extra[:10]!r}"
            )
        for key in sorted(source_map):
            if source_map[key] != stored_map[key]:
                raise ReferenceBaselineError(
                    f"{kind}: source/published relationship differs at {key!r}: "
                    f"source={source_map[key]!r}, published={stored_map[key]!r}"
                )
        counts[kind] = len(source_rows)
    return counts


def _verify_published_unit_options(
    army: sqlite3.Connection,
    sources: list[SourceDocument],
) -> dict[str, int]:
    """Match global Unit options and each army-expanded Include target."""
    try:
        master = merge_sources(sources)
    except ValueError as exc:
        raise ReferenceBaselineError(f"Global Unit source identity drift: {exc}") from exc
    expected_options: dict[tuple[int, ...], tuple[Any, ...]] = {}
    expected_includes: dict[tuple[int, ...], tuple[Any, ...]] = {}
    target_armies: dict[tuple[int, int, int], list[tuple[int, int]]] = {}
    for row in army.execute(
        "SELECT army_id, unit_id, group_id, option_id, loadout_payload_id "
        "FROM loadout_payload_occurrences"
    ):
        target_armies.setdefault((row[1], row[2], row[3]), []).append(
            (row[0], row[4])
        )
    for targets in target_armies.values():
        targets.sort()

    source_include_count = 0
    for unit in master["units"].values():
        shared = unit["shared"]
        unit_id = shared["id"]
        for position, option in enumerate(shared.get("options") or [], start=1):
            option_id = option["id"]
            key = (unit_id, option_id)
            if key in expected_options:
                raise ReferenceBaselineError(f"Duplicate global Unit option: {key!r}")
            expected_options[key] = (
                position, option.get("name"), option.get("points"),
                option.get("swc"), option.get("minis"), option.get("disabled"),
            )
            for include_position, value in enumerate(
                option.get("includes") or [], start=1
            ):
                source_include_count += 1
                include = value if isinstance(value, dict) else {}
                group_id = include.get("group")
                included_option = include.get("option")
                if type(group_id) is not int or type(included_option) is not int:
                    raise ReferenceBaselineError(
                        f"Global Unit option {key!r} include {include_position} "
                        "has invalid source target coordinates"
                    )
                target_key = (unit_id, group_id, included_option)
                targets = target_armies.get(target_key)
                if not targets:
                    raise ReferenceBaselineError(
                        f"Global Unit option {key!r} include {include_position} "
                        f"has no published loadout targets for {target_key!r}"
                    )
                for target_army, payload_id in targets:
                    include_key = (*key, include_position, target_army)
                    expected_includes[include_key] = (
                        payload_id, include.get("q")
                    )

    actual_options = [
        tuple(row) for row in army.execute(
            "SELECT unit_id, option_id, position, name, points, swc, minis, disabled "
            "FROM unit_options"
        )
    ]
    actual_includes = [
        tuple(row) for row in army.execute(
            "SELECT unit_id, option_id, position, target_army_id, "
            "target_loadout_payload_id, quantity FROM unit_option_include_targets"
        )
    ]
    for label, expected, observed, key_size in (
        ("unit_options", expected_options, actual_options, 2),
        ("unit_option_include_targets", expected_includes, actual_includes, 4),
    ):
        actual_map = {row[:key_size]: row[key_size:] for row in observed}
        if len(actual_map) != len(observed):
            raise ReferenceBaselineError(f"{label}: duplicate published identities")
        missing = sorted(expected.keys() - actual_map.keys())
        extra = sorted(actual_map.keys() - expected.keys())
        if missing or extra:
            raise ReferenceBaselineError(
                f"{label}: source/published identities differ: "
                f"missing={missing[:10]!r}, extra={extra[:10]!r}"
            )
        for key in sorted(expected):
            if expected[key] != actual_map[key]:
                raise ReferenceBaselineError(
                    f"{label}: source/published facts differ at {key!r}: "
                    f"source={expected[key]!r}, published={actual_map[key]!r}"
                )
    return {
        "globalOptions": len(expected_options),
        "sourceIncludeOccurrences": source_include_count,
        "publishedExpandedIncludeTargets": len(expected_includes),
    }


def _verify_army_archive_sources(
    archive: Path, metadata: dict[str, Any], army: sqlite3.Connection,
    raw_army: sqlite3.Connection | None = None,
    *,
    source_storage: str = "paired-army.raw.db",
) -> dict[str, Any]:
    """Match individual raw Army source identities to the published list rows.

    The enclosing caller verifies the archive SHA-256 first. This check only
    certifies IDs, source version counts and document cardinality, not the
    contents of every source field.
    """
    try:
        sources, skipped = load_sources(archive)
    except (OSError, ValueError) as exc:
        raise ReferenceBaselineError(f"Army archive cannot be parsed: {exc}") from exc

    if sorted(skipped) != ["metadata.json"]:
        raise ReferenceBaselineError(
            f"Army archive expected one metadata.json document, got {sorted(skipped)!r}"
        )
    declared_count = metadata.get("sourceFileCount")
    if type(declared_count) is not int or len(sources) != declared_count:
        raise ReferenceBaselineError(
            f"Army source count differs from published metadata: "
            f"{len(sources)} != {declared_count!r}"
        )
    versions = dict(sorted(Counter(str(s.data.get("version")) for s in sources).items()))
    if any(s.data.get("version") is None for s in sources):
        raise ReferenceBaselineError("Army source archive contains a missing version")
    if versions != metadata.get("sourceVersions"):
        raise ReferenceBaselineError(
            f"Army source versions differ from published metadata: "
            f"{versions!r} != {metadata.get('sourceVersions')!r}"
        )
    source_ids = {s.faction_id for s in sources}
    stored = {
        int(row[0]): {
            "version": row[1], "kind": row[2],
            "source_file": row[3], "source_sha256": row[4],
        }
        for row in army.execute(
            "SELECT id, version, kind, source_file, source_sha256 FROM army_lists"
        )
    }
    stored_ids = set(stored)
    if source_ids != stored_ids:
        raise ReferenceBaselineError(
            f"Published Army list identities differ from the source archive: "
            f"missing={sorted(source_ids - stored_ids)!r}, "
            f"extra={sorted(stored_ids - source_ids)!r}"
        )
    expected_memberships: list[tuple[int, int, int]] = []
    expected_nested: dict[str, list[tuple[Any, ...]]] = {
        table: [] for table in _NESTED_SOURCE_FIELDS
    }
    for source in sources:
        fields = {
            "version": source.data["version"],
            "kind": "army" if "reinforcements" in source.data else "reinforcement",
            "source_file": source.filename,
            "source_sha256": source.sha256,
        }
        if stored[source.faction_id] != fields:
            raise ReferenceBaselineError(
                f"Army {source.faction_id} published source provenance differs "
                f"from the archived source: expected {fields!r}, "
                f"actual {stored[source.faction_id]!r}"
            )
        unit_ids: set[int] = set()
        for position, unit in enumerate(source.data["units"], start=1):
            unit_id = unit.get("id") if isinstance(unit, dict) else None
            if type(unit_id) is not int or unit_id in unit_ids:
                raise ReferenceBaselineError(
                    f"Army {source.faction_id} has invalid or duplicate "
                    f"source Unit ID at position {position}: {unit_id!r}"
                )
            unit_ids.add(unit_id)
            expected_memberships.append((source.faction_id, unit_id, position))
            for group_position, group in enumerate(
                unit.get("profileGroups") or [], start=1
            ):
                group_id = group.get("id")
                if type(group_id) is not int:
                    raise ReferenceBaselineError(
                        f"Army {source.faction_id} Unit {unit_id} has "
                        f"invalid profile group identity {group_id!r}"
                    )
                parent = (source.faction_id, unit_id, group_id)
                expected_nested["profile_groups"].append((
                    *parent, group_position, group.get("category"),
                    group.get("isc"), group.get("notes"),
                ))
                for profile_position, profile in enumerate(
                    group.get("profiles") or [], start=1
                ):
                    profile_id = profile.get("id")
                    if type(profile_id) is not int:
                        raise ReferenceBaselineError(
                            f"Army {source.faction_id} Unit {unit_id} group {group_id} "
                            f"has invalid profile identity {profile_id!r}"
                        )
                    move = profile.get("move") or []
                    expected_nested["profiles"].append((
                        *parent, profile_id, profile_position,
                        profile.get("name"), profile.get("logo"), profile.get("type"),
                        move[0] if len(move) > 0 else None,
                        move[1] if len(move) > 1 else None,
                        profile.get("cc"), profile.get("bs"), profile.get("ph"),
                        profile.get("wip"), profile.get("arm"), profile.get("bts"),
                        profile.get("w"), profile.get("s"), profile.get("ava"),
                        profile.get("str"), profile.get("notes"),
                    ))
                for option_position, option in enumerate(
                    group.get("options") or [], start=1
                ):
                    option_id = option.get("id")
                    if type(option_id) is not int:
                        raise ReferenceBaselineError(
                            f"Army {source.faction_id} Unit {unit_id} group {group_id} "
                            f"has invalid loadout identity {option_id!r}"
                        )
                    expected_nested["loadout_options"].append((
                        *parent, option_id, option_position,
                        option.get("name"), option.get("points"), option.get("swc"),
                        option.get("minis"), option.get("disabled"),
                    ))
    published_memberships = [
        (int(row[0]), int(row[1]), int(row[2]))
        for row in army.execute(
            "SELECT army_id, unit_id, position FROM army_units "
            "ORDER BY army_id, position, unit_id"
        )
    ]
    expected_memberships.sort()
    published_memberships.sort()
    if expected_memberships != published_memberships:
        expected_set = set(expected_memberships)
        published_set = set(published_memberships)
        raise ReferenceBaselineError(
            "Published Army Unit memberships/positions differ from raw source: "
            f"missing={sorted(expected_set - published_set)[:10]!r}, "
            f"extra={sorted(published_set - expected_set)[:10]!r}"
        )
    nested_counts = {
        table: _verify_nested_source_rows(
            army if table == "profile_groups" else (raw_army or army),
            table, rows,
        )
        for table, rows in expected_nested.items()
    }
    return {
        "status": "source-identities-match-published-army-lists",
        "archiveJsonDocuments": len(sources) + len(skipped),
        "sourceFileCount": len(sources),
        "sourceVersions": versions,
        "matchedArmyListIds": len(source_ids),
        "matchedSourceProvenanceRows": len(sources),
        "matchedUnitMembershipOccurrences": len(expected_memberships),
        "matchedNestedSourceRows": nested_counts,
        "nestedStorage": {
            "profile_groups": "published-army.db",
            "profiles": source_storage,
            "loadout_options": source_storage,
        },
    }


def _revision_oldid(url: str | None) -> str | None:
    """Identify an exact Wiki oldid pin without accessing the network."""
    if not url:
        return None
    values = parse_qs(urlsplit(url).query).get("oldid", [])
    if len(values) == 1 and values[0].isascii() and values[0].isdigit():
        return values[0]
    return None


def _artifact_evidence(
    root: Path, local_path: str | None, url: str | None, hashes: set[str],
    *, source_layout: str = "legacy",
) -> dict[str, Any]:
    """Verify an explicitly selected PDF layout without changing its source identity."""
    location = _source_location(root, local_path)
    selected = root / local_path if local_path is not None else None
    if source_layout == "local" and local_path is not None and local_path.startswith("data/pdf/"):
        if len(hashes) != 1:
            raise ReferenceBaselineError(
                f"Local PDF source requires one declared SHA-256: {local_path}"
            )
        try:
            selected = pinned_pdf_path(
                root, local_path, next(iter(hashes)), layout=source_layout, missing_ok=True,
            )
        except SourcePathError as exc:
            raise ReferenceBaselineError(str(exc)) from exc
        location = "available" if selected is not None else "missing-local-artifact"
    actual_sha: str | None = None
    matches: bool | None = None
    oldid = _revision_oldid(url) if local_path is None else None
    if location == "available" and selected is not None:
        actual_sha = _sha256(selected)
        if (
            source_layout == "local" and local_path is not None
            and local_path.startswith("data/pdf/")
        ):
            if actual_sha not in hashes:
                raise ReferenceBaselineError(f"Source hash mismatch: {local_path}")
        if len(hashes) > 1:
            status = "conflicting-source-hashes"
        elif hashes:
            matches = actual_sha in hashes
            status = "hash-matched" if matches else "hash-mismatch-needs-review"
        else:
            status = "local-file-no-hash-pin"
    elif location == "url-backed/no-local-artifact":
        status = "revision-url-pinned" if oldid else "url-without-revision-pin"
    else:
        status = location
    return {
        "localStatus": location,
        "verificationStatus": status,
        "artifactSha256": actual_sha,
        "declaredHashMatches": matches,
        "revisionOldid": oldid,
    }


def _route_hint(key: str) -> dict[str, str] | None:
    """Locate an existing discovery surface, without asserting per-row coverage."""

    if key in {"army:profiles", "army:loadouts"}:
        return {
            "mode": "nested-unit",
            "browser": "/units/:id",
            "api": "/api/units/:id",
        }

    if key.startswith("army:catalog:"):
        domain_slug = key.removeprefix("army:catalog:")
    elif key in {"army:armies", "army:units", "army:fireteams"}:
        domain_slug = key.removeprefix("army:")
    elif key.startswith("rules:"):
        domain = semantic_record_domain(key.removeprefix("rules:"))
        if domain is None:
            return None
        domain_slug = domain.slug
    else:
        return None

    try:
        domain = application_domain(domain_slug)
    except ValueError:
        return None
    if not domain.published:
        return None
    if domain.route is None:
        if domain.glossary:
            return {"mode": "embedded-glossary", "browser": "/glossary", "api": "/api/glossary"}
        return None
    mode = "nested-scoped" if domain.scoped else domain.presentation
    return {
        "mode": mode,
        "browser": domain.route,
        "api": f"/api/{domain.slug}",
    }


def _row(
    key: str,
    source: str,
    canonical: str,
    maintained: str,
    database: str,
    count: int,
    *,
    citations: int | None = None,
) -> dict[str, Any]:
    return {
        "id": key,
        "source": source,
        "canonicalIdentity": canonical,
        "maintainedInput": maintained,
        "generatedStorage": database,
        "publishedRows": count,
        "rowsWithCitations": citations,
        "routeHint": _route_hint(key),
        "apiReadPath": None,
        "browserEntryPoint": None,
        "rulesContext": None,
        "factCoverage": "not-reviewed-against-source",
        "relationshipCoverage": "not-reviewed",
        "presentationCoverage": "not-reviewed",
        "scopeDecision": "pending",
    }


def build_baseline(
    army_database: Path,
    rules_database: Path,
    *,
    root: Path = PROJECT_ROOT,
    army_archive: Path | None = None,
    normalized: Path | None = None,
    source_layout: str = "legacy",
) -> dict[str, Any]:
    """Inventory published identities; intentionally make no completeness claims."""
    if source_layout not in {"legacy", "local"}:
        raise ReferenceBaselineError(f"Unknown source layout: {source_layout}")
    if normalized is not None and army_archive is None:
        raise ReferenceBaselineError(
            "Verified normalized source requires --army-archive for source parity"
        )
    with (
        closing(_connect(army_database)) as army,
        closing(_connect(rules_database)) as rules,
    ):
        army_meta = _metadata(army, "__infinity_metadata")
        rules_meta = _metadata(rules, "__rules_metadata")
        raw_army = army_meta.get("_meta")
        if not isinstance(raw_army, dict):
            raise ReferenceBaselineError("Army publication lacks normalized source metadata")
        archive_sha = raw_army.get("snapshotArchiveSha256")
        if not isinstance(archive_sha, str) or len(archive_sha) != 64:
            raise ReferenceBaselineError("Army publication lacks a pinned archive SHA-256")
        archive_evidence: dict[str, Any] | None = None
        if army_archive is None:
            archive_status = "not-supplied"
        else:
            if not army_archive.is_file():
                raise ReferenceBaselineError(f"Army archive is unavailable: {army_archive}")
            if _sha256(army_archive) != archive_sha:
                raise ReferenceBaselineError("Army archive SHA-256 differs from published metadata")
            with ExitStack() as source_stack:
                if normalized is None:
                    raw_path = raw_database_path(army_database)
                    try:
                        validate_database_pair(army_database, raw_path=raw_path)
                    except ValueError as exc:
                        raise ReferenceBaselineError(
                            f"Published Army/raw source database pair is invalid: {exc}"
                        ) from exc
                    source = source_stack.enter_context(closing(_connect(raw_path)))
                    source_storage = "paired-army.raw.db"
                else:
                    try:
                        source, _generation = source_stack.enter_context(
                            normalized_source_connection(army_database, normalized)
                        )
                    except (OSError, ValueError, sqlite3.Error) as exc:
                        raise ReferenceBaselineError(
                            f"Verified normalized Army source is invalid: {exc}"
                        ) from exc
                    source_storage = "verified-normalized.json"
                archive_evidence = _verify_army_archive_sources(
                    army_archive, raw_army, army, source,
                    source_storage=source_storage,
                )
                sources, _ = load_sources(army_archive)
                archive_evidence["matchedPublishedReferences"] = (
                    _verify_published_profile_references(army, sources)
                )
                archive_evidence["matchedPublishedExtras"] = (
                    _verify_published_profile_extras(army, sources)
                )
                archive_evidence["matchedPublishedCharacteristicsOrders"] = (
                    _verify_published_characteristics_orders(army, sources)
                )
                archive_evidence["matchedPublishedPeripheralsIncludes"] = (
                    _verify_published_peripherals_includes(army, sources)
                )
                archive_evidence["matchedPublishedGlobalUnitOptions"] = (
                    _verify_published_unit_options(army, sources)
                )
            archive_status = "hash-verified-source-identities"

        # Each URL revision is a separate source identity. Only a genuinely shared
        # local archive should be aggregated across curated collections.
        source_groups: dict[tuple[str, str, str], dict[str, Any]] = {}
        try:
            source_records = rules.execute(
                "SELECT collection_id, id, kind, title, version, published_date, "
                "retrieved_date, acquired_at, local_path, url, sha256 "
                "FROM sources ORDER BY kind, version, local_path, collection_id, id"
            ).fetchall()
            collections = [dict(x) for x in rules.execute(
                "SELECT id, title, domain, status, effective_from "
                "FROM collections ORDER BY id"
            )]
        except sqlite3.DatabaseError as exc:
            raise ReferenceBaselineError(f"Rules source catalog is unreadable: {exc}") from exc
        for record in source_records:
            locator_type = "file" if record["local_path"] else "url"
            locator = record["local_path"] or record["url"] or record["id"]
            group_key = (record["kind"], locator_type, locator)
            if group_key not in source_groups:
                source_groups[group_key] = {
                    "kind": record["kind"],
                    "versions": set(),
                    "localPath": record["local_path"],
                    "url": record["url"] if locator_type == "url" else None,
                    "localStatus": _source_location(root, record["local_path"]),
                    "sourceRows": 0,
                    "sourceIds": set(),
                    "titles": set(),
                    "collections": set(),
                    "publishedDates": set(),
                    "retrievedDates": set(),
                    "acquiredAt": set(),
                    "declaredSha256": set(),
                }
            group = source_groups[group_key]
            group["sourceRows"] += 1
            group["versions"].add(record["version"])
            group["sourceIds"].add(record["id"])
            group["titles"].add(record["title"])
            group["collections"].add(record["collection_id"])
            for field, column in (
                ("publishedDates", "published_date"),
                ("retrievedDates", "retrieved_date"),
                ("acquiredAt", "acquired_at"),
            ):
                if record[column]:
                    group[field].add(record[column])
            if record["sha256"]:
                group["declaredSha256"].add(record["sha256"])

        source_inventory = [dict(row) for row in source_records]
        sources = []
        for group in source_groups.values():
            hashes = group["declaredSha256"]
            sources.append({
                **{k: v for k, v in group.items() if k not in
                   {"sourceIds", "titles", "collections", "declaredSha256", "versions",
                    "publishedDates", "retrievedDates", "acquiredAt"}},
                "uniqueSourceIds": len(group["sourceIds"]),
                "titles": sorted(group["titles"]),
                "versions": sorted(group["versions"]),
                "collections": sorted(group["collections"]),
                "publishedDates": sorted(group["publishedDates"]),
                "retrievedDates": sorted(group["retrievedDates"]),
                "acquiredAt": sorted(group["acquiredAt"]),
                "declaredSha256": sorted(hashes),
                **_artifact_evidence(
                    root, group["localPath"], group["url"], hashes,
                    source_layout=source_layout,
                ),
            })
        verification_counts: dict[str, int] = {}
        for source in sources:
            status = source["verificationStatus"]
            verification_counts[status] = verification_counts.get(status, 0) + 1

        evidence_rows: list[dict[str, Any]] = []
        army_families = (
            ("armies", "army_lists"),
            ("units", "logical_units"),
            ("profiles", "profile_payloads"),
            ("loadouts", "loadout_payloads"),
            ("fireteams", "application_fireteams"),
            ("peripherals", "application_peripheral_entities"),
        )
        try:
            for category, table in army_families:
                count = army.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                evidence_rows.append(_row(
                    f"army:{category}", "Infinity Army snapshot", table,
                    "pinned Army snapshot + reviewed identity configuration",
                    f"army.db::{table}", count,
                ))
            catalogs = army.execute(
                "SELECT catalog, COUNT(*) AS count FROM application_catalog_items "
                "GROUP BY catalog ORDER BY catalog"
            ).fetchall()
            for catalog in catalogs:
                evidence_rows.append(_row(
                    f"army:catalog:{catalog['catalog']}", "Infinity Army snapshot",
                    f"application catalog {catalog['catalog']}",
                    "pinned Army snapshot + reviewed catalog configuration",
                    "army.db::application_catalog_items", catalog["count"],
                ))
            records = rules.execute(
                "SELECT r.kind AS kind, COUNT(*) AS count, "
                "SUM(CASE WHEN EXISTS (SELECT 1 FROM record_citations AS c "
                "WHERE c.collection_id = r.collection_id "
                "AND c.record_id = r.id) THEN 1 ELSE 0 END) AS cited "
                "FROM records AS r GROUP BY r.kind ORDER BY r.kind"
            ).fetchall()
            for item in records:
                evidence_rows.append(_row(
                    f"rules:{item['kind']}", "Curated N5 rules and wiki evidence",
                    f"rules record kind {item['kind']}", "data/curated/rules/",
                    "rules_n5.db::records", item["count"], citations=item["cited"],
                ))
            scenario_memberships = [
                {
                    "collectionId": row["collection_id"],
                    "collectionRevision": row["collection_revision"],
                    "position": row["position"],
                    "scenarioId": row["scenario_id"],
                    "publicationCollectionId": row["publication_collection_id"],
                }
                for row in rules.execute(
                    "SELECT collection_id, collection_revision, position, "
                    "scenario_id, publication_collection_id "
                    "FROM scenario_memberships "
                    "ORDER BY collection_id, collection_revision, position"
                )
            ]
        except sqlite3.DatabaseError as exc:
            raise ReferenceBaselineError(f"Published catalog is unreadable: {exc}") from exc

    army_sha = _sha256(army_database)
    rules_sha = _sha256(rules_database)
    try:
        _, weapon_profile_sha = load_runtime_weapon_profile_publication(
            army_database, rules_database,
        )
    except (OSError, sqlite3.Error, ValueError) as exc:
        raise ReferenceBaselineError(
            f"Cannot verify embedded Weapon citations: {exc}"
        ) from exc
    runtime_revision = database_set_snapshot_revision({
        army_database.name: army_sha, rules_database.name: rules_sha,
    })
    return {
        "format": REPORT_FORMAT,
        "formatVersion": REPORT_VERSION,
        "status": "initial-evidence-only-not-a-completeness-verdict",
        "runtimeSnapshotRevision": runtime_revision,
        "weaponProfilePublicationSha256": weapon_profile_sha,
        "armySnapshot": {
            "archiveSha256": archive_sha,
            "publishedDatabaseSha256": army_sha,
            "archiveVerification": archive_status,
            "sourceIdentityEvidence": archive_evidence,
            "sourceFileCount": raw_army.get("sourceFileCount"),
            "sourceVersions": raw_army.get("sourceVersions"),
            "sourceDataChangedOn": raw_army.get("sourceDataChangedOn"),
            "snapshotDownloadedOn": raw_army.get("snapshotDownloadedOn"),
        },
        "rulesPublication": {
            "publishedDatabaseSha256": rules_sha,
            "metadata": rules_meta, "collections": collections,
        },
        "sourceGroups": sources,
        "sourceVerificationCounts": dict(sorted(verification_counts.items())),
        "sourceInventory": source_inventory,
        "scenarioMembershipCount": len(scenario_memberships),
        "scenarioMemberships": scenario_memberships,
        "inventory": evidence_rows,
        "remainingEvidence": [
            "Confirm source archive hashes, publication identities, and PDF/wiki local inputs",
            "Review official PDF/FAQ/annex sections and wiki material against record families",
            "Reconcile source semantics and rule relationships, not just record counts",
            "Check normal API/browser paths and rules context for each inventory row",
            "Reconcile existing Army source-presentation, enrichment, "
            "and interaction audits",
            "Classify every concrete gap with a scope decision and owning 1.0 task",
        ],
    }


def verify_served_revision(report: dict[str, Any], base_url: str) -> dict[str, str]:
    """Require the inventoried database pair and applicable Weapon publication.

    This does not verify external source artifacts, rules semantics, or browser
    rendering.
    """
    try:
        observed = verify_served_runtime(
            report["runtimeSnapshotRevision"], base_url,
        )
    except ServedRuntimeError as exc:
        raise ReferenceBaselineError(str(exc)) from exc
    return {**observed, "status": "exact-database-pair-match-not-source-completeness"}


def render_markdown(report: dict[str, Any]) -> str:
    snapshot = report["armySnapshot"]
    lines = [
        "# 1.0 current-reference baseline (initial evidence)",
        "",
        "**Status: not a completeness verdict.** Counts prove only published rows; "
        "citations prove only citation presence. Source facts, relations, scope, and "
        "normal browser access still require review.",
        "",
        "## Published source identities",
        "",
        f"- Army: {snapshot['sourceFileCount']} source documents; "
        f"versions `{json.dumps(snapshot['sourceVersions'], sort_keys=True)}`; "
        f"archive SHA-256 `{snapshot['archiveSha256']}` "
        f"({snapshot['archiveVerification']}).",
        *(
            [f"- Verified Army source identities: "
             f"{snapshot['sourceIdentityEvidence']['archiveJsonDocuments']} archive JSON documents "
             f"(including metadata.json), "
             f"{snapshot['sourceIdentityEvidence']['matchedArmyListIds']} matched "
             "published Army-list IDs with matching version counts, "
             f"{snapshot['sourceIdentityEvidence']['matchedSourceProvenanceRows']} "
             "matched per-file provenance records and "
             f"{snapshot['sourceIdentityEvidence']['matchedUnitMembershipOccurrences']} "
             "ordered Unit membership occurrences."]
            if snapshot.get("sourceIdentityEvidence") else []
        ),
        *(
            [f"- Nested Army source row parity: "
             f"{snapshot['sourceIdentityEvidence']['matchedNestedSourceRows']['profile_groups']} "
             "profile groups in published army.db; "
             f"{snapshot['sourceIdentityEvidence']['matchedNestedSourceRows']['profiles']} "
             "profiles and "
             f"{snapshot['sourceIdentityEvidence']['matchedNestedSourceRows']['loadout_options']} "
             + (
                 "loadouts in verified normalized.json. "
                 if snapshot['sourceIdentityEvidence'].get('nestedStorage', {}).get(
                     'profiles'
                 ) == "verified-normalized.json"
                 else "loadouts in export-paired army.raw.db. "
              )
             + "Derived runtime payloads and browser presentation remain unverified."]
            if (snapshot.get("sourceIdentityEvidence") or {}).get("matchedNestedSourceRows")
            else []
        ),
        *(
            ["- Published profile/loadout Skill, Equipment and Weapon occurrences: "
             + ", ".join(
                 f"{name}={count}"
                 for name, count in sorted(
                     snapshot["sourceIdentityEvidence"]["matchedPublishedReferences"].items()
                 )
             )
             + " (source ID, position, display order and quantity; "
             "not nested extras or browser rendering)."]
            if (snapshot.get("sourceIdentityEvidence") or {}).get("matchedPublishedReferences")
            else []
        ),
        *(
            ["- Published profile/loadout reference extras: "
             + ", ".join(
                 f"{name}={count}"
                 for name, count in sorted(
                     snapshot["sourceIdentityEvidence"]["matchedPublishedExtras"].items()
                 )
             )
             + " (exact source occurrence, extra position and extra ID; "
             "not a parameter-semantics or browser verification)."]
            if (snapshot.get("sourceIdentityEvidence") or {}).get("matchedPublishedExtras")
            else []
        ),
        *(
            ["- Published profile/loadout Characteristics and Orders: "
             + ", ".join(
                 f"{name}={count}"
                 for name, count in sorted(
                     snapshot["sourceIdentityEvidence"][
                         "matchedPublishedCharacteristicsOrders"
                     ].items()
                 )
             )
             + " (ordered characteristic IDs; modeled Order type/list/total; "
             "raw fields and browser representation unreviewed)."]
            if (snapshot.get("sourceIdentityEvidence") or {}).get(
                "matchedPublishedCharacteristicsOrders"
            )
            else []
        ),
        *(
            ["- Published contextual Peripherals and Includes: "
             + ", ".join(
                 f"{name}={count}"
                 for name, count in sorted(
                     snapshot["sourceIdentityEvidence"][
                         "matchedPublishedPeripheralsIncludes"
                     ].items()
                 )
             )
             + " (army-local peripheral IDs and canonical include target payloads; "
             "raw fields and browser output unreviewed)."]
            if (snapshot.get("sourceIdentityEvidence") or {}).get(
                "matchedPublishedPeripheralsIncludes"
            )
            else []
        ),
        *(
            [(
                "- Global Unit-option parity: {globalOptions} options, "
                "{sourceIncludeOccurrences} source Includes, "
                "{publishedExpandedIncludeTargets} army-expanded published targets "
                "(not global-option nested item arrays or browser rendering)."
             ).format_map(
                 snapshot["sourceIdentityEvidence"]["matchedPublishedGlobalUnitOptions"]
             )]
            if (snapshot.get("sourceIdentityEvidence") or {}).get(
                "matchedPublishedGlobalUnitOptions"
            )
            else []
        ),
        f"- Published Army database SHA-256: `{snapshot['publishedDatabaseSha256']}`.",
        f"- Published rules database SHA-256: "
        f"`{report['rulesPublication']['publishedDatabaseSha256']}`.",
        f"- Applicable Weapon-profile publication SHA-256: "
        f"`{report['weaponProfilePublicationSha256'] or 'unavailable'}`.",
        f"- Combined runtime snapshot revision: `{report['runtimeSnapshotRevision']}` "
        "(database pair and applicable Weapon-profile publication; not source completeness).",
        *(
            [f"- Served runtime: {report['servedSnapshot']['status']} "
             f"at `{report['servedSnapshot']['versionUrl']}`."]
            if report.get("servedSnapshot") else []
        ),
        f"- Army source data changed: {snapshot['sourceDataChangedOn']}; "
        f"snapshot acquired: {snapshot['snapshotDownloadedOn']} "
        "(separate from publication dates).",
        "- Rules collections: " + ", ".join(
            f"`{item['id']}` ({item['status']})"
            for item in report["rulesPublication"]["collections"]
        ) + ".",
        f"- N5 Rules scenario memberships: {report['scenarioMembershipCount']} "
        "(this is not an inventory of separate ITS season databases).",
        "- Source evidence statuses: " + ", ".join(
            f"{count} {status}"
            for status, count in report["sourceVerificationCounts"].items()
        ) + ".",
        "",
        "## Published scenario memberships by collection",
        "",
        "These are source-scoped memberships in the selected N5 Rules database, "
        "not a browser-completeness verdict. ITS publications are stored separately "
        "in season databases and are not included in this Rules-only report.",
        "",
        "| Collection | Revision | Position | Scenario ID | Source collection |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for membership in report["scenarioMemberships"]:
        lines.append(
            f"| `{membership['collectionId']}` | "
            f"`{membership['collectionRevision']}` | "
            f"{membership['position']} | `{membership['scenarioId']}` | "
            f"`{membership['publicationCollectionId']}` |"
        )
    lines.extend([
        "",
        "## Source artifacts referenced by rules publication",
        "",
        "| Kind | Version | Curated rows | Source identity | Evidence |",
        "| --- | --- | ---: | --- | --- |",
    ])
    for source in report["sourceGroups"]:
        versions = source["versions"]
        version_label = versions[0] if len(versions) == 1 else f"{len(versions)} versions"
        if source["localPath"] is not None:
            locator = f"`{source['localPath']}`"
        else:
            title = source["titles"][0]
            locator = f"[{title}]({source['url']})" if source["url"] else title
            if source["revisionOldid"]:
                locator += f" (`oldid={source['revisionOldid']}`)"
        escaped_locator = locator.replace("|", "\\|")
        lines.append(
            f"| {source['kind']} | {version_label} | {source['sourceRows']} | "
            f"{escaped_locator} | {source['verificationStatus']} |"
        )
    lines.extend([
        "",
        "The complete source inventory JSON retains individual collection/source IDs, "
        "publication and acquisition dates, declared SHA-256 values, and URLs. "
        "The report does not fetch URLs or reinterpret acquisition dates as publication dates.",
        "",
        "The current source table is not an exhaustive publication inventory: "
        "FAQ/errata and annex scope must be reconciled separately.",
        "",
        "A local hash match checks exact file bytes against the declared SHA-256, "
        "but does not verify the source contents. A mismatch may mean a logical "
        "rather than byte-level hash pin and requires review. URL `oldid=` pins "
        "identify revisions, not offline content verification. A local PDF without "
        "a declared SHA-256 cannot be hash-verified.",
        "",
        "## Published category inventory (verification pending)",
        "",
        "Route hints identify possible *starting surfaces* from the current "
        "application-domain registry. They are not source-to-API parity or "
        "browser-acceptance evidence: nested Unit data, embedded Glossary "
        "vocabularies, scoped references and curated Weapons may not have "
        "one direct page per source row.",
        "",
        "| Source/category | Canonical identity | Maintained input | Storage | Rows | "
        "Cited | Candidate browser / API | Review |",
        "| --- | --- | --- | --- | ---: | ---: | --- | --- |",
    ])
    for item in report["inventory"]:
        cited = item["rowsWithCitations"]
        hint = item["routeHint"]
        candidate = (
            f"`{hint['browser']}` / `{hint['api']}` ({hint['mode']}; unverified)"
            if hint else "not identified"
        )
        lines.append(
            f"| `{item['id']}` | `{item['canonicalIdentity']}` | "
            f"{item['maintainedInput']} | `{item['generatedStorage']}` | "
            f"{item['publishedRows']} | {cited if cited is not None else '—'} | "
            f"{candidate} | pending source/API/browser review |"
        )
    lines.extend(["", "## Outstanding 1.0 evidence", ""])
    lines.extend(f"- [ ] {item}." for item in report["remainingEvidence"])
    lines.extend([
        "",
        "This baseline is a starting inventory; it does not replace "
        "`audit_source_presentation.py`, `audit_enrichment_coverage.py`, "
        "or `audit_rules_interactions.py`. Missing sources and unreviewed browser "
        "paths must not be interpreted as either completeness or confirmed defects.",
        "",
    ])
    return "\n".join(lines)


FROZEN_EXPLANATION_INVENTORY = (
    PROJECT_ROOT / "docs/rules-explanation-audit-1.0-inventory.md"
)
FROZEN_DECLARATION_COMMIT = "c5400ab1b950990fdacc509be91c110fe85431fb"
FROZEN_DECLARATION_SOURCE = (
    PROJECT_ROOT / "config/validation/frozen-declaration-source-v1.json"
)
FROZEN_DECLARATION_SOURCE_SHA256 = (
    "9fed4f072387882f80d18f1e0dfb6c4db4827ab8233001f5ad21c96e809fa10f"
)
DECLARATION_REVIEW = PROJECT_ROOT / "config/validation/declaration-inventory-migration-v1.json"
# The declaration review is bound to the original 2026-10-31 frozen file.
# A later documentation-only TODO anchor correction did not modify its
# 367 record rows, but did change the current Markdown file bytes.
HISTORICAL_EXPLANATION_INVENTORY_SHA256 = (
    "3f6b21bc6ba7e508e63cfaa74b1bdb3fdefe3ab3968418d813be18a36275675e"
)
FROZEN_EXPLANATION_INVENTORY_SHA256 = (
    "624e0406c1159a9131a876128e70639a2ee9374981a640b11e9dc11dfc69fc00"
)
SELECTED_EXPLANATION_BROWSER_TESTS = {
    "rule:initiative-roll": "test_initiative_roll_normal_reference_navigation",
    "rule:combat-group": "test_combat_group_normal_reference_navigation",
    "rule:army-retreat": "test_army_retreat_standard_game_normal_reference_navigation",
    "rule:standard-game": "test_army_retreat_standard_game_normal_reference_navigation",
    "rule:game-modes": "test_game_modes_source_table_normal_reference_navigation",
    "rule:modifiers-explained": "test_modifiers_explained_normal_reference_navigation",
    "skill:activate-disco-ball": "test_added_source_skills_normal_browser",
    "skill:request-specball": "test_added_source_skills_normal_browser",
    "skill:combat-instinct": "test_stealth_counter_reaction_permissions_normal_browser",
    "skill:sixth-sense": "test_stealth_counter_reaction_permissions_normal_browser",
    "skill:neurocinetics": "test_reactive_burst_skill_permissions_normal_browser",
    "skill:total-reaction": "test_reactive_burst_skill_permissions_normal_browser",
    "weapon:multi-rifle": "test_multi_weapon_modes_stay_separate_in_normal_browser",
    "weapon:multi-heavy-machine-gun": "test_multi_weapon_modes_stay_separate_in_normal_browser",
    "weapon:multi-marksman-rifle": "test_multi_weapon_modes_stay_separate_in_normal_browser",
    "weapon:multi-pistol": "test_multi_weapon_modes_stay_separate_in_normal_browser",
    "weapon:boarding-pistol": "test_blast_and_hit_weapon_modes_keep_effects_separate_in_browser",
    "weapon:missile-launcher": "test_blast_and_hit_weapon_modes_keep_effects_separate_in_browser",
    "weapon:k1-combi-rifle": (
        "test_k1_weapon_profiles_keep_normal_ammunition_and_arm_zero_in_browser"
    ),
    "weapon:k1-sniper-rifle": (
        "test_k1_weapon_profiles_keep_normal_ammunition_and_arm_zero_in_browser"
    ),
    "equipment:firewall": "test_added_equipment_firewall_normal_browser",
    "rule:order-expenditure-sequence": (
        "test_conditional_reaction_source_slices_visible_in_normal_browser"
    ),
    "skill:look-out": "test_conditional_reaction_source_slices_visible_in_normal_browser",
    **{
        identifier: "test_remaining_conditional_crosswalk_cases_normal_browser"
        for identifier in (
            "skill:guard", "rule:hacking-area",
            "rule:peripheral-type:cyberplug", "skill:stealth",
        )
    },
    **{
        identifier: "test_selected_conditional_skills_normal_browser"
        for identifier in (
            "skill:discover", "skill:place-deployable",
            "skill:reload", "skill:alert",
        )
    },
    **{
        identifier: "test_visibility_zone_terms_normal_browser"
        for identifier in (
            "term:visibility-zone", "term:low-visibility-zone",
            "term:poor-visibility-zone", "term:zero-visibility-zone",
            "term:white-noise-zone",
        )
    },
}
CURRENT_EXPLANATION_COLLECTIONS = (
    PROJECT_ROOT / "data/curated/rules/n5-core-v5.3.json",
    PROJECT_ROOT / "data/curated/rules/n5-hacking-programs-v5.3.json",
)
_EXPLANATION_ROW = re.compile(r"^\| \x60([^\x60]+)\x60 \| ([CH]) \| ([DS]) \|")


def parse_frozen_explanation_inventory(markdown: str) -> dict[str, dict[str, str]]:
    """Read only the original record table; never infer approvals from its D/S tier."""
    start = "## Record inventory"
    end = "## Scenario component inventory"
    if markdown.count(start) != 1 or markdown.count(end) != 1:
        raise ReferenceBaselineError("Frozen explanation inventory boundaries changed")
    section = markdown.split(start, 1)[1].split(end, 1)[0]
    results: dict[str, dict[str, str]] = {}
    for line in section.splitlines():
        if not line.startswith("| `"):
            continue
        match = _EXPLANATION_ROW.match(line)
        if match is None:
            raise ReferenceBaselineError(f"Malformed frozen record inventory row: {line[:90]}")
        identifier, collection, tier = match.groups()
        if identifier in results:
            raise ReferenceBaselineError(f"Duplicate frozen identity: {identifier}")
        if ":" not in identifier:
            raise ReferenceBaselineError(f"Invalid frozen identity: {identifier}")
        results[identifier] = {"collection": collection, "historicalTier": tier}
    if not results:
        raise ReferenceBaselineError("Frozen record inventory is empty")
    return results


def reconcile_explanation_inventory(
    inventory_path: Path = FROZEN_EXPLANATION_INVENTORY,
    curated_paths: Sequence[Path] = CURRENT_EXPLANATION_COLLECTIONS,
) -> dict[str, Any]:
    """Bridge frozen 367-record evidence to today's Core/Hacking identities.

    This proves identity coverage and preserves original tiers. Source locators,
    curated review flags, and test names are evidence pointers, not full-record
    acceptance or migration approval.
    """
    from infinity_db.curated import load_curated_document

    if _sha256(inventory_path) != FROZEN_EXPLANATION_INVENTORY_SHA256:
        raise ReferenceBaselineError("Frozen explanation inventory hash changed")
    frozen = parse_frozen_explanation_inventory(
        inventory_path.read_text(encoding="utf-8")
    )
    browser_test_sources = [
        (PROJECT_ROOT / path).read_text(encoding="utf-8")
        for path in (
            "tests/test_verify_scenario_faq_browser.py",
            "tests/test_verify_weapon_source_cards_browser.py",
        )
    ]
    for identifier, test in SELECTED_EXPLANATION_BROWSER_TESTS.items():
        if not any(f"def {test}(" in source for source in browser_test_sources):
            raise ReferenceBaselineError(
                f"Selected browser evidence no longer exists: {identifier}"
            )
    historical_tiers = Counter(row["historicalTier"] for row in frozen.values())
    if len(frozen) != 367 or historical_tiers != {"D": 304, "S": 63}:
        raise ReferenceBaselineError("Historical explanation inventory drift (367/304/63)")
    records: dict[str, tuple[str, dict[str, Any]]] = {}
    curated_hashes: dict[str, str] = {}
    for path, collection_code in zip(curated_paths, ("C", "H"), strict=True):
        document = load_curated_document(path)
        curated_hashes[document["collection"]["id"]] = _sha256(path)
        for record in document["records"]:
            identifier = record["id"]
            if identifier in records:
                raise ReferenceBaselineError(f"Duplicate current identity: {identifier}")
            records[identifier] = (collection_code, record)
    if not records:
        raise ReferenceBaselineError("No current Core/Hacking records")
    before, now = set(frozen), set(records)
    retained = sorted(before & now)
    removed = sorted(before - now)
    added = sorted(now - before)
    retired_rows = []
    for identifier in removed:
        row = frozen[identifier]
        if not identifier.startswith("declaration-category:"):
            raise ReferenceBaselineError(
                f"Non-declaration frozen identity removed; manual migration required: {identifier}"
            )
        # A same-type/new-page candidate is a discovery hint, never proof of rename.
        group = identifier.rsplit(":", 1)[0]
        candidates = [
            candidate for candidate in added
            if candidate.startswith(group + ":")
        ]
        retired_rows.append({
            "id": identifier, **row, "disposition": "retired-declaration-identity",
            "possibleReplacementIds": candidates,
            "replacementVerified": False,
        })
    current_rows: list[dict[str, Any]] = []
    groups: dict[tuple[str, str, str], set[str]] = {}
    for identifier in sorted(now):
        collection, record = records[identifier]
        previous = frozen.get(identifier)
        review = record.get("review") or {}
        citations = record.get("citations") or []
        if not isinstance(citations, list):
            raise ReferenceBaselineError(f"Current citations malformed: {identifier}")
        locations = []
        for citation in citations:
            if not isinstance(citation, dict):
                raise ReferenceBaselineError(f"Invalid citation: {identifier}")
            source = citation.get("sourceId")
            if not isinstance(source, str) or not source:
                raise ReferenceBaselineError(f"Unattributed citation: {identifier}")
            page = str(citation.get("page", "-"))
            section = str(citation.get("section") or citation.get("heading") or
                          citation.get("member") or "unspecified-heading")
            key = (source, page, section)
            groups.setdefault(key, set()).add(identifier)
            locations.append({
                "sourceId": source, "page": citation.get("page"),
                "heading": section,
                "status": "source-locator-not-clause-acceptance",
            })
        if not locations:
            groups.setdefault(("unattributed", "-", "no-citations"), set()).add(identifier)
        current_rows.append({
            "id": identifier, "kind": record["kind"], "collection": collection,
            "lineage": "retained" if previous else "added-after-frozen-inventory",
            "historicalTier": previous["historicalTier"] if previous else None,
            "curatedReviewStatus": review.get("status"),
            "curatedReviewedOn": review.get("reviewedOn"),
            "citations": locations,
            "sourceDisposition": "pending-full-material-clause-reconciliation",
            "sourceSpecificVariant": (
                (record.get("variantSemantics") or {}).get("inheritance") == "source"
            ),
            "browserDisposition": (
                "source-variant-pending-owner-context-presentation-review"
                if (record.get("variantSemantics") or {}).get("inheritance") == "source"
                else "selected-route-smoke-evidence-not-full-acceptance"
                if identifier in SELECTED_EXPLANATION_BROWSER_TESTS
                else "pending-full-normal-mode-acceptance"
            ),
            "selectedBrowserTest": SELECTED_EXPLANATION_BROWSER_TESTS.get(identifier),
            "fullRecordAcceptance": "not-assessed-in-this-audit",
        })
    sections = [
        {
            "sourceId": source, "page": page, "heading": heading,
            "currentRecordIds": sorted(ids), "recordCount": len(ids),
            "disposition": "pending-section-specific-clause-and-browser-review",
        }
        for (source, page, heading), ids in sorted(groups.items())
    ]
    added_kinds = dict(sorted(Counter(records[rid][1]["kind"] for rid in added).items()))
    retained_s = sorted(rid for rid in retained if frozen[rid]["historicalTier"] == "S")
    return {
        "format": "InfinityDB frozen/current explanation inventory reconciliation",
        "formatVersion": 1,
        "status": "identity-bridge-only-pending-clause-and-browser-acceptance",
        "frozenInventorySha256": _sha256(inventory_path),
        "currentCuratedSha256": curated_hashes,
        "frozenCount": len(frozen), "frozenTiers": dict(sorted(historical_tiers.items())),
        "currentCount": len(now), "retainedCount": len(retained),
        "addedCount": len(added), "removedCount": len(removed),
        "addedKinds": added_kinds, "retainedScreeningOnlyIds": retained_s,
        "retiredIdentityRows": retired_rows,
        "addedIds": added,
        "currentRecords": current_rows, "sourceSections": sections,
        "sourceSectionCount": len(sections),
        "fullRecordApprovalsIssuedByThisAudit": 0,
        "remainingWork": [
            "Adjudicate each retired declaration identity and possible metadata replacement "
            "from actual source headings; matching category/page labels are not rename proof",
            "Review current added records against their owning source clauses, later "
            "curation and exception evidence; existing reviewed status is not full approval",
            "Resolve remaining historical screening-only identities and their material "
            "mechanics; numerical source-value evidence is separately scoped",
            "Assign each source section a signed-off clause and normal-browser disposition; "
            "same-page citations are only locator evidence",
        ],
    }


def plan_explanation_review_batches(
    report: dict[str, Any], *, batch_limit: int = 40,
) -> dict[str, Any]:
    """Cluster existing evidence pointers for review; approve no gameplay facts."""
    if not 1 <= batch_limit <= 100:
        raise ReferenceBaselineError("Review batch limit must be between 1 and 100")
    if report.get("status") != "identity-bridge-only-pending-clause-and-browser-acceptance":
        raise ReferenceBaselineError(
            "Review planner requires the current explanation reconciliation"
        )
    records = report["currentRecords"]
    sections = report["sourceSections"]
    by_id = {row["id"]: row for row in records}
    if len(by_id) != len(records) or len(records) != report["currentCount"]:
        raise ReferenceBaselineError("Duplicate or missing current review identities")

    def locator_key(row: dict[str, Any]) -> tuple[str, str, str]:
        page = row["page"] if row["page"] is not None else "-"
        return row["sourceId"], str(page), row["heading"]

    owners: dict[tuple[str, str, str], set[str]] = {}
    for row in records:
        if row["fullRecordAcceptance"] != "not-assessed-in-this-audit":
            raise ReferenceBaselineError("Planner cannot import presumed full-record approvals")
        keys = [locator_key(citation) for citation in row["citations"]]
        if not keys:
            keys = [("unattributed", "-", "no-citations")]
        for key in keys:
            owners.setdefault(key, set()).add(row["id"])

    section_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    for section in sections:
        key = locator_key(section)
        if key in section_map:
            raise ReferenceBaselineError(f"Duplicate source locator: {key!r}")
        section_map[key] = section
        if set(section["currentRecordIds"]) != owners.get(key):
            raise ReferenceBaselineError(f"Source locator owners disagree: {key!r}")
    if set(section_map) != set(owners) or len(sections) != report["sourceSectionCount"]:
        raise ReferenceBaselineError("Source locator coverage differs from the baseline")

    def source_ref(key: tuple[str, str, str]) -> dict[str, str]:
        return {"sourceId": key[0], "page": key[1], "heading": key[2]}

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in records:
        grouped.setdefault((row["collection"], row["kind"]), []).append(row)
    batches: list[dict[str, Any]] = []
    owner_batch: dict[str, str] = {}
    for (collection, kind), family in sorted(grouped.items()):
        def sort_key(row: dict[str, Any]) -> tuple[tuple[str, str, str], str]:
            citations = row["citations"]
            key = min(map(locator_key, citations)) if citations else (
                "unattributed", "-", "no-citations"
            )
            return key, row["id"]

        ordered = sorted(family, key=sort_key)
        for offset in range(0, len(ordered), batch_limit):
            chunk = ordered[offset:offset + batch_limit]
            batch_id = f"{collection.lower()}-{kind}-{offset // batch_limit + 1:02d}"
            keys = sorted({
                key
                for row in chunk
                for key in (
                    [locator_key(citation) for citation in row["citations"]]
                    or [("unattributed", "-", "no-citations")]
                )
            })
            for row in chunk:
                owner_batch[row["id"]] = batch_id
            batches.append({
                "id": batch_id,
                "collection": collection,
                "kind": kind,
                "status": "pending-source-and-normal-browser-review",
                "recordCount": len(chunk),
                "sourceLocatorCount": len(keys),
                "records": [
                    {
                        "id": row["id"],
                        "historicalTier": row["historicalTier"],
                        "lineage": row["lineage"],
                        "sourceSpecificVariant": row["sourceSpecificVariant"],
                        "selectedBrowserTestHint": row["selectedBrowserTest"],
                        "sourceLocators": [
                            source_ref(locator_key(citation))
                            for citation in row["citations"]
                        ],
                        "status": "pending-full-material-review",
                    }
                    for row in chunk
                ],
                "sourceLocators": [source_ref(key) for key in keys],
            })

    if set(owner_batch) != set(by_id):
        raise ReferenceBaselineError("Review batches omit current record identities")
    shared = [
        {
            **source_ref(key),
            "recordIds": sorted(owners[key]),
            "batchIds": sorted({owner_batch[record_id] for record_id in owners[key]}),
            "status": "shared-source-pointer-not-semantic-approval",
        }
        for key in sorted(owners)
        if len(owners[key]) > 1
    ]
    return {
        "format": "InfinityDB V1S-082 review batch plan",
        "formatVersion": 1,
        "status": "triage-only-no-source-or-browser-approvals",
        "inputs": {
            "frozenInventorySha256": report["frozenInventorySha256"],
            "currentCuratedSha256": report["currentCuratedSha256"],
        },
        "summary": {
            "currentRecords": len(records),
            "sourceLocators": len(sections),
            "recordLocatorLinks": sum(len(ids) for ids in owners.values()),
            "sharedSourceLocators": len(shared),
            "historicalScreeningRecords": sum(
                row["historicalTier"] == "S" for row in records
            ),
            "addedAfterFrozenInventory": sum(
                row["lineage"] == "added-after-frozen-inventory" for row in records
            ),
            "sourceSpecificVariantRecords": sum(
                bool(row["sourceSpecificVariant"]) for row in records
            ),
            "selectedBrowserTestHints": sum(
                bool(row["selectedBrowserTest"]) for row in records
            ),
            "batches": len(batches),
            "maxRecordsPerBatch": batch_limit,
            "approvedRecords": 0,
            "approvedSourceLocators": 0,
        },
        "batches": batches,
        "sharedSourceLocators": shared,
    }


V1S082_PILOT_MANIFEST = PROJECT_ROOT / "config/validation/v1s082-review-pilot-v1.json"


def _source_page_identity(
    source_id: str, page: Any, member: str | None = None,
) -> tuple[str, str] | None:
    if type(page) is int and page > 0:
        return source_id, f"page:{page}"
    if (page is None and source_id.startswith("wiki-")
            and re.search(r"-oldid-[0-9]+$", source_id)):
        return source_id, "revision"
    if page is None and source_id.startswith("wiki-") and member and member.strip():
        return source_id, f"member:{member}"
    return None


def _source_page_member(
    curated_record: dict[str, Any], citation: dict[str, Any],
) -> str | None:
    source_id = citation["sourceId"]
    if not source_id.startswith("wiki-"):
        return None
    members = [
        row.get("member")
        for row in curated_record["citations"]
        if row.get("sourceId") == source_id
        and row.get("page") == citation["page"]
        and row.get("heading") == citation["heading"]
    ]
    if (not members
            or any(not isinstance(member, str) or not member.strip() for member in members)
            or len(set(members)) != 1):
        return None
    return members[0]


def build_explanation_review_pilot(
    report: dict[str, Any], *, manifest_path: Path = V1S082_PILOT_MANIFEST,
) -> dict[str, Any]:
    """Prepare pinned, representative work packets; no automatic rule approval."""
    from infinity_db.curated import load_curated_document

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReferenceBaselineError(f"V1S-082 pilot manifest is unreadable: {exc}") from exc
    if (manifest.get("format") != "InfinityDB V1S-082 review pilot sample"
            or manifest.get("formatVersion") != 1
            or manifest.get("status") != "selection-only-no-approved-mechanics"):
        raise ReferenceBaselineError("V1S-082 pilot manifest format/status mismatch")
    selected = manifest.get("records")
    probes = manifest.get("sourceFirstProbes")
    benchmarks = manifest.get("benchmarkFields")
    if (not isinstance(benchmarks, list) or not benchmarks
            or any(not isinstance(field, str) or not field for field in benchmarks)
            or len(set(benchmarks)) != len(benchmarks)):
        raise ReferenceBaselineError("V1S-082 benchmark field contract is invalid")
    if (not isinstance(selected, list) or not 30 <= len(selected) <= 40
            or len(selected) != manifest.get("selectedRecordCount")
            or not isinstance(probes, list) or not probes):
        raise ReferenceBaselineError("V1S-082 pilot must select 30-40 records and source probes")

    indexed = {record["id"]: record for record in report["currentRecords"]}
    if len(indexed) != report["currentCount"]:
        raise ReferenceBaselineError("Pilot baseline has duplicate or missing current identities")
    curated: dict[str, dict[str, Any]] = {}
    for source in CURRENT_EXPLANATION_COLLECTIONS:
        for row in load_curated_document(source)["records"]:
            if row["id"] in curated:
                raise ReferenceBaselineError(f"Duplicate pilot curated identity: {row['id']}")
            curated[row["id"]] = row

    sections: dict[tuple[str, str, str], set[str]] = {}
    for row in report["sourceSections"]:
        key = (row["sourceId"], str(row["page"]), row["heading"])
        if key in sections:
            raise ReferenceBaselineError(f"Duplicate pilot source locator: {key!r}")
        sections[key] = set(row["currentRecordIds"])

    record_ids: set[str] = set()
    cohorts: set[str] = set()
    selected_rows: list[dict[str, Any]] = []
    all_locators: set[tuple[str, str, str, str | None]] = set()
    all_source_pages: set[tuple[str, str]] = set()
    unresolved_source_page_locators: set[tuple[str, str, str]] = set()
    naive_locator_count = 0
    repeated_shared = 0
    for item in selected:
        if not isinstance(item, dict):
            raise ReferenceBaselineError("Pilot record must be an object")
        identifier = item.get("recordId")
        cohort = item.get("cohort")
        question = item.get("reviewQuestion")
        if (not isinstance(identifier, str) or identifier not in indexed
                or identifier in record_ids):
            raise ReferenceBaselineError(f"Missing/duplicate pilot record: {identifier!r}")
        if (not isinstance(cohort, str) or not re.fullmatch(r"[a-z][a-z-]+", cohort)
                or not isinstance(question, str) or not question.strip()):
            raise ReferenceBaselineError(f"Missing pilot cohort/review question: {identifier}")
        record_ids.add(identifier)
        cohorts.add(cohort)
        row = indexed[identifier]
        source_locators = []
        for citation in row["citations"]:
            page = citation["page"] if citation["page"] is not None else "-"
            key = (citation["sourceId"], str(page), citation["heading"])
            if identifier not in sections.get(key, set()):
                raise ReferenceBaselineError(f"Pilot source ownership mismatch: {identifier}")
            member = _source_page_member(curated[identifier], citation)
            source_locator = {
                "sourceId": key[0], "page": key[1], "heading": key[2],
                "otherRecordOwners": sorted(sections[key] - {identifier}),
                "status": "citation-pointer-not-reviewed-clause",
            }
            if member is not None:
                source_locator["member"] = member
            source_locators.append(source_locator)
            repeated_shared += len(sections[key]) > 1
            all_locators.add((*key, member))
            page_identity = _source_page_identity(
                citation["sourceId"], citation["page"], member,
            )
            if page_identity is None:
                unresolved_source_page_locators.add(key)
            else:
                all_source_pages.add(page_identity)
            naive_locator_count += 1
        curated_bytes = json.dumps(
            curated[identifier], sort_keys=True, ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        selected_rows.append({
            "id": identifier,
            "cohort": cohort,
            "reviewQuestion": question,
            "kind": row["kind"],
            "lineage": row["lineage"],
            "historicalTier": row["historicalTier"],
            "selectedBrowserTestHint": row["selectedBrowserTest"],
            "curatedRecordSha256": hashlib.sha256(curated_bytes).hexdigest(),
            "citations": source_locators,
            "sourceDisposition": "pending-semantic-acceptance",
            "normalBrowserDisposition": "pending-browser-acceptance",
            "measurements": {
                field: None for field in manifest["benchmarkFields"]
            },
        })
    if len(cohorts) < 6 or len(selected_rows) != manifest["selectedRecordCount"]:
        raise ReferenceBaselineError("Pilot selection does not cover enough semantic families")
    source_page_identity_complete = not unresolved_source_page_locators
    source_ids = {key[0] for key in sections}
    probe_ids: set[str] = set()
    probe_rows: list[dict[str, Any]] = []
    for probe in probes:
        if (not isinstance(probe, dict)
                or not isinstance(probe.get("id"), str)
                or probe["id"] in probe_ids
                or probe.get("sourceId") not in source_ids
                or type(probe.get("printedPage")) is not int
                or probe["printedPage"] < 1
                or not isinstance(probe.get("question"), str)
                or not probe["question"].strip()):
            raise ReferenceBaselineError(f"Invalid source-first probe: {probe!r}")
        probe_ids.add(probe["id"])
        probe_rows.append({**probe, "status": "pending-independent-source-scan"})
    return {
        "format": "InfinityDB V1S-082 review pilot work packet",
        "formatVersion": 2,
        "status": "planned-not-reviewed-no-source-or-browser-approvals",
        "inputFingerprints": {
            "frozenInventorySha256": report["frozenInventorySha256"],
            "currentCuratedSha256": report["currentCuratedSha256"],
            "selectionManifestSha256": _sha256(manifest_path),
        },
        "summary": {
            "selectedRecords": len(selected_rows),
            "semanticCohorts": len(cohorts),
            "selectedSourceCitationOccurrences": naive_locator_count,
            "uniqueSelectedSourceLocators": len(all_locators),
            "sourcePageIdentityComplete": source_page_identity_complete,
            "knownUniqueSourcePageIdentities": len(all_source_pages),
            "unresolvedSourcePageIdentityLocators": len(unresolved_source_page_locators),
            "unresolvedSourcePageIdentitySources": sorted({
                key[0] for key in unresolved_source_page_locators
            }),
            "uniqueSelectedSourcePages": (
                len(all_source_pages) if source_page_identity_complete else None
            ),
            "duplicateSelectedLocatorOccurrences": naive_locator_count - len(all_locators),
            "sourcePageOpensPotentiallyReusable": (
                naive_locator_count - len(all_source_pages)
                if source_page_identity_complete else None
            ),
            "sharedWithOtherRecordsOccurrences": repeated_shared,
            "sourceFirstProbes": len(probe_rows),
            "sourceApprovals": 0,
            "browserApprovals": 0,
        },
        "records": selected_rows,
        "sourceFirstProbes": probe_rows,
        "benchmarkFields": manifest["benchmarkFields"],
        "caveat": (
            "Locator duplication is only a potential research shortcut, not proof "
            "that two records express the same semantic clause or that any source "
            "fact or browser route has been accepted. Page-open reuse is estimated "
            "only when every source-page identity is known; it is unknown while any "
            "identity is unresolved and is never measured source-open or review-time evidence."
        ),
    }


def reconcile_declaration_owners(
    report: dict[str, Any],
    *,
    repository: Path = PROJECT_ROOT,
    historical_commit: str = FROZEN_DECLARATION_COMMIT,
    historical_snapshot: Path = FROZEN_DECLARATION_SOURCE,
) -> dict[str, Any]:
    """Recover original category ownership; never infer rename from page numbers."""
    if not re.fullmatch(r"[0-9a-f]{40}", historical_commit):
        raise ReferenceBaselineError("Historical commit must be an exact SHA-1")
    historical_file = "data/curated/rules/n5-core-v5.3.json"
    if historical_commit == FROZEN_DECLARATION_COMMIT:
        # Exact historical records, extracted once from Git, must also work in
        # the index-only preflight export where no .git directory exists.
        try:
            raw = historical_snapshot.read_bytes()
        except OSError as exc:
            raise ReferenceBaselineError("Frozen declaration source unavailable") from exc
        if hashlib.sha256(raw).hexdigest() != FROZEN_DECLARATION_SOURCE_SHA256:
            raise ReferenceBaselineError("Frozen declaration source hash changed")
        historical = json.loads(raw)
        if (
            historical.get("formatVersion") != 1
            or historical.get("historicalCommit") != historical_commit
            or historical.get("historicalPath") != historical_file
            or historical.get("historicalFileSha256") != (
                "bb17f2013a1b8bc32961689789e4afff6fcc30f1476248d5d53d4b96587ab9a5"
            )
        ):
            raise ReferenceBaselineError("Frozen declaration source provenance changed")
    else:
        result = subprocess.run(
            ["git", "show", f"{historical_commit}:{historical_file}"],
            cwd=repository, capture_output=True, text=True, check=False,
            encoding="utf-8",
        )
        if result.returncode != 0:
            raise ReferenceBaselineError(
                f"Historical curated snapshot unavailable: {historical_commit} "
                f"({result.stderr.strip()[:180]})"
            )
        try:
            historical = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ReferenceBaselineError("Historical curated snapshot has invalid JSON") from exc
    from infinity_db.curated import load_curated_document

    current = load_curated_document(CURRENT_EXPLANATION_COLLECTIONS[0])
    original = {
        row["id"]: row for row in historical["records"]
        if row["kind"] == "declaration-category"
    }
    modern = {
        row["id"]: row for row in current["records"]
        if row["kind"] == "declaration-category"
    }
    if not modern:
        raise ReferenceBaselineError("Current declaration categories are missing")
    retired_ids = [row["id"] for row in report["retiredIdentityRows"]]
    if not set(retired_ids) <= original.keys():
        raise ReferenceBaselineError("Frozen identity absent from historical curated snapshot")
    owner_index: dict[tuple[str, str], list[str]] = {}
    for identifier, row in modern.items():
        for link in row.get("armyLinks", []):
            key = (str(link["entity"]), str(link["id"]))
            owner_index.setdefault(key, []).append(identifier)

    transitions = []
    for identifier in sorted(retired_ids):
        old = original[identifier]
        owners = old.get("armyLinks") or []
        if not owners:
            raise ReferenceBaselineError(
                f"Retired declaration has no historical owner: {identifier}"
            )
        owner_rows = []
        for link in owners:
            key = (str(link["entity"]), str(link["id"]))
            candidates = [
                {
                    "id": cid,
                    "typeId": modern[cid]["facts"]["typeId"],
                    "page": modern[cid]["citations"][0]["page"],
                }
                for cid in sorted(owner_index.get(key, []))
            ]
            owner_rows.append({
                "entity": key[0], "id": key[1],
                "currentCategories": candidates,
                "disposition": (
                    "source-heading-and-meaning-review-required"
                    if candidates else "unresolved-owner-no-current-category"
                ),
            })
        transitions.append({
            "retiredId": identifier,
            "historicalCategory": old["facts"]["typeId"],
            "historicalPage": old["citations"][0]["page"],
            "ownerTransitions": owner_rows,
            "status": "owner-crosswalk-not-approved-rename",
        })
    current_added = [
        {"id": identifier, "owners": modern[identifier].get("armyLinks", []),
         "typeId": modern[identifier]["facts"]["typeId"],
         "sourceId": modern[identifier]["citations"][0]["sourceId"],
         "page": modern[identifier]["citations"][0]["page"]}
        for identifier in report["addedIds"] if identifier in modern
    ]
    return {
        "historicalCommit": historical_commit,
        "historicalFile": historical_file,
        "retiredCount": len(transitions), "addedCount": len(current_added),
        "transitions": transitions, "addedDeclarations": current_added,
        "status": "owner-crosswalk-requires-source-heading-review",
    }


def verify_declaration_review(
    crosswalk: dict[str, Any],
    *,
    manifest_path: Path = DECLARATION_REVIEW,
    pdf_path: Path | None = None,
) -> dict[str, Any]:
    """Check exact historical owners, 20 current headings and optional PDF bytes."""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReferenceBaselineError(f"Declaration review unavailable: {exc}") from exc
    if manifest.get("formatVersion") != 1 or manifest.get("historicalCommit") != (
        crosswalk["historicalCommit"]
    ) or manifest.get("historicalInventorySha256") != (
        HISTORICAL_EXPLANATION_INVENTORY_SHA256
    ):
        raise ReferenceBaselineError("Declaration review has mismatched historical scope")
    retired = manifest.get("retiredTransitions")
    added = manifest.get("addedHeadings")
    if not isinstance(retired, list) or not isinstance(added, list):
        raise ReferenceBaselineError("Declaration review entries must be arrays")
    if len(retired) != len(crosswalk["transitions"]) or len(added) != (
        len(crosswalk["addedDeclarations"])
    ):
        raise ReferenceBaselineError("Declaration review does not cover full migration")
    review_by_id = {row["oldId"]: row for row in retired}
    if len(review_by_id) != len(retired) or set(review_by_id) != {
        row["retiredId"] for row in crosswalk["transitions"]
    }:
        raise ReferenceBaselineError("Retired declaration review IDs differ")
    changed_kinds = 0
    split_groups = 0
    for row in crosswalk["transitions"]:
        review = review_by_id[row["retiredId"]]
        owners = {
            f"{owner['entity']}:{owner['id']}" for owner in row["ownerTransitions"]
        }
        if len(set(review["historicalOwners"])) != len(review["historicalOwners"]) or (
            set(review["historicalOwners"]) != owners
        ):
            raise ReferenceBaselineError(f"Historical owners differ: {row['retiredId']}")
        targets = review["currentIds"]
        if len(set(targets)) != len(targets) or not targets:
            raise ReferenceBaselineError(f"Invalid current ID list: {row['retiredId']}")
        target_owners: set[str] = set()
        new_kinds: set[str] = set()
        for target in targets:
            matches = [
                owner for owner in row["ownerTransitions"]
                if any(category["id"] == target for category in owner["currentCategories"])
            ]
            if len(matches) != 1:
                raise ReferenceBaselineError(
                    f"Replacement lacks unique historical skill owner: {target}"
                )
            match = matches[0]
            target_owners.add(f"{match['entity']}:{match['id']}")
            category = next(
                c for c in match["currentCategories"] if c["id"] == target
            )
            new_kinds.add(category["typeId"])
        if target_owners != owners or len(new_kinds) != 1:
            raise ReferenceBaselineError(
                f"Retired category has missing or inconsistent owner: {row['retiredId']}"
            )
        old_kind = row["historicalCategory"]
        if review["disposition"] == "corrected-source-page":
            if new_kinds != {old_kind} or len(owners) != 1:
                raise ReferenceBaselineError(f"Invalid page-only correction: {row['retiredId']}")
        elif review["disposition"] == "corrected-classification":
            if old_kind in new_kinds or len(owners) != 1:
                raise ReferenceBaselineError(f"Invalid kind correction: {row['retiredId']}")
            changed_kinds += 1
        elif review["disposition"] == "split-by-skill-owner":
            if new_kinds != {old_kind} or len(owners) <= 1:
                raise ReferenceBaselineError(f"Invalid split correction: {row['retiredId']}")
            split_groups += 1
        else:
            raise ReferenceBaselineError(f"Unrecognized resolution: {row['retiredId']}")
    added_by_id = {row["id"]: row for row in added}
    if len(added_by_id) != len(added) or set(added_by_id) != {
        row["id"] for row in crosswalk["addedDeclarations"]
    }:
        raise ReferenceBaselineError("Added category review identities differ")
    classes = {
        "aro": "SHORT SKILL / ARO",
        "basic-short-skill": "BASIC SHORT SKILL / ARO",
        "short-skill": "SHORT SKILL",
        "long-skill": "LONG SKILL",
        "deployment-skill": "DEPLOYMENT SKILL",
        "automatic": "AUTOMATIC SKILL",
    }
    for actual in crosswalk["addedDeclarations"]:
        review = added_by_id[actual["id"]]
        source_class = classes.get(actual["typeId"])
        if actual["id"] == "declaration-category:aro:p77":
            source_class = "BASIC SHORT SKILL / ARO"
        if actual["typeId"] == "short-skill" and actual["id"] in {
            "declaration-category:short-skill:p39",
            "declaration-category:short-skill:p51",
        }:
            source_class = "SHORT SKILL / ARO"
        if (review["owner"] not in {
            f"{link['entity']}:{link['id']}" for link in actual["owners"]
        } or len(actual["owners"]) != 1 or
                actual["sourceId"] != manifest["currentSourceId"] or
                review["printedClassification"] != source_class or
                not isinstance(review["printedHeading"], str) or
                not review["printedHeading"].strip() or
                not actual["id"].endswith(f":p{actual['page']}")):
            raise ReferenceBaselineError(f"Added source-heading review mismatch: {actual['id']}")
    evidence = "curated-source-and-historical-owner-checked"
    if pdf_path is not None:
        if _sha256(pdf_path) != manifest["currentPdfSha256"]:
            raise ReferenceBaselineError("Pinned declaration PDF SHA-256 mismatch")
        try:
            import pymupdf
        except ImportError as exc:
            raise ReferenceBaselineError("PyMuPDF required for source verification") from exc
        with pymupdf.open(pdf_path) as document:
            for actual in crosswalk["addedDeclarations"]:
                review = added_by_id[actual["id"]]
                heading = re.escape(review["printedHeading"])
                classification = re.escape(review["printedClassification"])
                page = " ".join(document[actual["page"] - 1].get_text().split())
                if not re.search(rf"{heading}\s+{classification}", page, re.I):
                    raise ReferenceBaselineError(
                        f"Printed declaration heading mismatch: {actual['id']}"
                    )
        evidence = "pinned-n5.3-pdf-headings-verified"
    return {
        "status": evidence,
        "retiredReviewed": len(retired),
        "newHeadingsReviewed": len(added),
        "kindCorrections": changed_kinds,
        "multiOwnerSplits": split_groups,
        "retiredCategoryAliasesCreated": 0,
        "fullRecordApprovalsIssued": 0,
    }


def join_explanation_reviewed_evidence(
    report: dict[str, Any],
    *,
    declaration_manifest: Path = DECLARATION_REVIEW,
) -> dict[str, Any]:
    """Join each frozen record to current identities and bounded later evidence.

    This is a provenance crosswalk, never an additional approval tier.
    Retired declaration IDs map by reviewed historical owner, not by name/page.
    """
    required = {"declarationMigrations", "conditionalDeclarations", "visibilityZones"}
    if not required <= report.keys():
        raise ReferenceBaselineError(
            "Reviewed explanation join requires declaration, conditional and visibility audits"
        )
    if _sha256(FROZEN_EXPLANATION_INVENTORY) != FROZEN_EXPLANATION_INVENTORY_SHA256:
        raise ReferenceBaselineError("Frozen explanation inventory hash changed")
    frozen = parse_frozen_explanation_inventory(
        FROZEN_EXPLANATION_INVENTORY.read_text(encoding="utf-8")
    )
    current = {item["id"]: item for item in report["currentRecords"]}
    if len(current) != report["currentCount"] or len(frozen) != report["frozenCount"]:
        raise ReferenceBaselineError("Frozen/current explanation join identity count drift")
    retained = set(frozen) & set(current)
    removed = set(frozen) - set(current)
    if (len(retained), len(removed), len(set(current) - set(frozen))) != (
        report["retainedCount"], report["removedCount"], report["addedCount"]
    ):
        raise ReferenceBaselineError("Frozen/current explanation join lineage drift")

    migration = report["declarationMigrations"]
    verified = verify_declaration_review(migration, manifest_path=declaration_manifest)
    if migration.get("review") != verified:
        # A caller's source-PDF-enhanced verification may have a stronger status.
        if not (migration.get("review", {}).get("status") ==
                "pinned-n5.3-pdf-headings-verified"
                and {k: v for k, v in migration["review"].items() if k != "status"} ==
                {k: v for k, v in verified.items() if k != "status"}):
            raise ReferenceBaselineError("Retired declaration review evidence drift")
    manifest = json.loads(declaration_manifest.read_text(encoding="utf-8"))
    transitions = {entry["oldId"]: entry for entry in manifest["retiredTransitions"]}
    added_headings = {entry["id"]: entry for entry in manifest["addedHeadings"]}
    if (set(transitions) != removed or
            set(added_headings) != {
                row["id"] for row in migration["addedDeclarations"]
            } or len(added_headings) != 20):
        raise ReferenceBaselineError("Historical declaration transition coverage drift")

    conditional = report["conditionalDeclarations"]["cases"]
    visibility = report["visibilityZones"]["records"]
    conditional_by_id: dict[str, list[dict[str, Any]]] = {}
    for entry in conditional:
        conditional_by_id.setdefault(entry["recordId"], []).append(entry)
    visibility_by_id = {row["id"]: row for row in visibility}
    if (len(conditional) != 10 or len(visibility_by_id) != 5
            or len(set(conditional_by_id) - set(current)) != 0
            or len(set(visibility_by_id) - set(current)) != 0
            or not set(added_headings) <= set(current)):
        raise ReferenceBaselineError("Later selected evidence target or count drift")

    current_rows = []
    selected_browser = 0
    evidenced_ids: set[str] = set()
    for identity in sorted(current):
        row = current[identity]
        evidence: list[dict[str, Any]] = []
        if row["selectedBrowserTest"]:
            selected_browser += 1
            evidence.append({
                "kind": "selected-browser-test-anchor",
                "test": row["selectedBrowserTest"],
                "disposition": "maintained-test-exists-not-executed-by-join",
            })
        for case in conditional_by_id.get(identity, []):
            evidence.append({
                "kind": "selected-conditional-clause",
                "key": case["key"], "page": case["sourcePage"],
                "test": case["supportingTest"],
                "disposition": case["disposition"],
            })
        if identity in visibility_by_id:
            source = visibility_by_id[identity]
            evidence.append({
                "kind": "selected-visibility-term",
                "href": source["href"],
                "disposition": source["fullRecordAcceptance"],
                "verifiedPdfLanguages": report["visibilityZones"]["verifiedPdfLanguages"],
            })
        if identity in added_headings:
            heading = added_headings[identity]
            evidence.append({
                "kind": "reviewed-declaration-heading",
                "owner": heading["owner"],
                "printedClassification": heading["printedClassification"],
                "disposition": "owner-and-heading-reviewed-not-full-record-acceptance",
            })
        if evidence:
            evidenced_ids.add(identity)
        current_rows.append({
            "id": identity,
            "lineage": row["lineage"],
            "historicalTier": row["historicalTier"],
            "curatedReviewStatus": row["curatedReviewStatus"],
            "curatedReviewedOn": row["curatedReviewedOn"],
            "sourceSpecificVariant": row["sourceSpecificVariant"],
            "sourceLocatorCount": len(row["citations"]),
            "sourceDisposition": row["sourceDisposition"],
            "browserDisposition": row["browserDisposition"],
            "laterEvidence": evidence,
            "fullRecordAcceptance": row["fullRecordAcceptance"],
        })

    current_evidence = {
        row["id"]: [entry["kind"] for entry in row["laterEvidence"]]
        for row in current_rows if row["laterEvidence"]
    }
    historical_rows = []
    for identity in sorted(frozen):
        entry = frozen[identity]
        if identity in current:
            modern_ids = [identity]
            disposition = "retained-identity-with-source-and-browser-gates-open"
            transition = None
        else:
            transition = transitions[identity]
            modern_ids = transition["currentIds"]
            if not modern_ids or not set(modern_ids) <= set(current):
                raise ReferenceBaselineError(
                    f"Retired declaration lacks validated current owner: {identity}"
                )
            disposition = "owner-and-heading-reviewed-no-alias-or-full-record-approval"
        later_links = [
            {"currentRecordId": linked, "evidenceKinds": current_evidence[linked]}
            for linked in modern_ids if linked in current_evidence
        ]
        historical_rows.append({
            "id": identity,
            "originalCollection": entry["collection"],
            "historicalTier": entry["historicalTier"],
            "lineage": "retained" if identity in current else "retired-declaration",
            "currentRecordIds": modern_ids,
            "laterEvidence": later_links,
            "migrationDisposition": transition["disposition"] if transition else None,
            "disposition": disposition,
            "fullRecordAcceptance": "not-approved-by-identity-or-evidence-join",
        })
    if (len(historical_rows) != 367 or
            sum(row["historicalTier"] == "S" for row in historical_rows) != 63):
        raise ReferenceBaselineError("Historical D/S denominator changed during join")
    return {
        "format": "InfinityDB frozen/current selected evidence join",
        "formatVersion": 1,
        "status": "reviewed-evidence-joined-no-full-record-acceptance",
        "frozenInventorySha256": report["frozenInventorySha256"],
        "currentCuratedSha256": report["currentCuratedSha256"],
        "historicalRecords": historical_rows,
        "currentRecords": current_rows,
        "summary": {
            "frozen": 367, "historicalD": 304, "historicalS": 63,
            "retained": len(retained), "retiredDeclarations": len(removed),
            "added": report["addedCount"], "current": len(current),
            "retainedHistoricalS": sum(
                row["historicalTier"] == "S" and row["lineage"] == "retained"
                for row in historical_rows
            ),
            "historicalIdentitiesWithLaterEvidence": sum(
                bool(row["laterEvidence"]) for row in historical_rows
            ),
            "reviewedDeclarationTransitions": len(transitions),
            "reviewedNewDeclarationHeadings": len(added_headings),
            "selectedConditionalCases": len(conditional),
            "selectedVisibilityTerms": len(visibility_by_id),
            "selectedBrowserTestAnchors": selected_browser,
            "currentIdentitiesWithLaterEvidence": len(evidenced_ids),
            "wholeRecordApprovals": 0,
            "pendingSourceSections": report["sourceSectionCount"],
        },
    }


NUMERIC_ARMY_VARIANTS = {
    279: ("skill:bs-11", "BS=11", "BS", 11, "skill:bs-attack", 39),
    278: ("skill:bs-12", "BS=12", "BS", 12, "skill:bs-attack", 39),
    274: ("skill:cc-21", "CC=21", "CC", 21, "skill:cc-attack", 51),
}
NUMERIC_ARMY_SNAPSHOT_SHA256 = (
    "f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75"
)


def audit_numeric_army_replacement_variants(
    archive_path: Path, curated_path: Path = CURRENT_EXPLANATION_COLLECTIONS[0],
) -> dict[str, Any]:
    """Read-only exact Army source occurrence audit; no profile stat rewriting."""
    import zipfile

    from infinity_db.curated import load_curated_document

    if _sha256(archive_path) != NUMERIC_ARMY_SNAPSHOT_SHA256:
        raise ReferenceBaselineError("Pinned Army ZIP does not match numeric-variant source")
    document = load_curated_document(curated_path)
    records = {record["id"]: record for record in document["records"]}
    expected_counts = {279: 2, 278: 9, 274: 6}
    dictionaries: dict[int, set[str]] = {sid: set() for sid in NUMERIC_ARMY_VARIANTS}
    occurrences: dict[int, list[dict[str, Any]]] = {
        sid: [] for sid in NUMERIC_ARMY_VARIANTS
    }
    with zipfile.ZipFile(archive_path) as archive:
        members = sorted(
            name for name in archive.namelist() if name.endswith(".json")
        )
        if len(members) != 59:
            raise ReferenceBaselineError("Pinned Army ZIP document count changed")
        for member in members:
            data = json.loads(archive.read(member))
            for item in data.get("filters", {}).get("skills", []):
                sid = item.get("id")
                if sid in NUMERIC_ARMY_VARIANTS:
                    dictionaries[sid].add(str(item.get("name")))
            for unit in data.get("units", []):
                for group in unit.get("profileGroups", []):
                    profiles = group.get("profiles", [])
                    for option in group.get("options", []):
                        for occurrence in option.get("skills", []):
                            sid = occurrence.get("id")
                            if sid not in NUMERIC_ARMY_VARIANTS:
                                continue
                            if occurrence.get("q") != 1:
                                raise ReferenceBaselineError(
                                    f"Unexpected replacement multiplicity {sid} in {member}"
                                )
                            if not profiles:
                                raise ReferenceBaselineError(
                                    f"Replacement lacks parent profile in {member}"
                                )
                            attribute = NUMERIC_ARMY_VARIANTS[sid][2].lower()
                            base_values = sorted({
                                profile.get(attribute) for profile in profiles
                            })
                            if any(type(v) is not int for v in base_values):
                                raise ReferenceBaselineError(
                                    f"Non-numeric base {attribute} in {member}"
                                )
                            occurrences[sid].append({
                                "sourceFile": member,
                                "unitId": unit["id"],
                                "unitName": unit["name"],
                                "profileGroupId": group["id"],
                                "optionId": option["id"],
                                "optionName": option["name"],
                                "profileBaseValues": base_values,
                                "replacementAttribute": attribute.upper(),
                                "sourceVariantQuantity": occurrence["q"],
                            })
    result = []
    for sid, (rid, name, attribute, value, parent, page) in (
        NUMERIC_ARMY_VARIANTS.items()
    ):
        record = records[rid]
        if (
            dictionaries[sid] != {name}
            or record["name"] != name
            or record.get("armyLinks") != [{"entity": "skill", "id": sid}]
            or record.get("variantSemantics") != {
                "inheritance": "source",
                "sourceVariant": {
                    "kind": "attribute-replacement", "attribute": attribute,
                    "value": value,
                },
            }
            or record.get("relations") != [
                {"type": "variant-of", "recordId": parent}
            ]
            or record.get("facts", {}).get("typeIds") != ["short-skill", "aro"]
            or (record["citations"][0].get("sourceId"),
                record["citations"][0].get("page")) != ("n5-core-v5.3-pdf", page)
            or (record["citations"][1].get("sourceId"),
                record["citations"][1].get("page")) != ("n5-core-v5.3-pdf", 75)
        ):
            raise ReferenceBaselineError(f"Source variant classification drift: {rid}")
        if len(occurrences[sid]) != expected_counts[sid]:
            raise ReferenceBaselineError(
                f"Army replacement occurrences drift: {rid}="
                f"{len(occurrences[sid])}, expected {expected_counts[sid]}"
            )
        result.append({
            "id": rid, "armySourceId": sid, "name": name,
            "baseAttribute": attribute, "replacementValue": value,
            "sourceActionRule": parent, "rulesPages": [page, 75],
            "factionFileOccurrences": len(occurrences[sid]),
            "occurrences": occurrences[sid],
            "sourceScope": "army-option-skill-not-permanent-profile-stat",
            "scopeDisposition": "verified-source-variant-and-occurrence-not-broad-mechanics",
        })
    return {
        "status": "pinned-army-numerical-variants-verified",
        "armyArchiveSha256": NUMERIC_ARMY_SNAPSHOT_SHA256,
        "variantCount": len(result),
        "factionFileOccurrenceCount": sum(len(x["occurrences"]) for x in result),
        "records": result,
        "fullRecordApprovalsIssued": 0,
    }


CONDITIONAL_DECLARATION_EVIDENCE = (
    PROJECT_ROOT / "config/validation/conditional-declaration-evidence-v1.json"
)


def audit_conditional_declaration_evidence(
    manifest_path: Path = CONDITIONAL_DECLARATION_EVIDENCE,
    *,
    pdf_path: Path | None = None,
    root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Verify selected clause locators, player facts and test anchors, not global AROs."""
    from infinity_db.curated import load_curated_document

    config = json.loads(manifest_path.read_text(encoding="utf-8"))
    if config.get("formatVersion") != 1 or config.get("format") != (
        "InfinityDB V1-A08 conditional declaration evidence crosswalk"
    ) or config.get("sourceId") != "n5-core-v5.3-pdf" or (
        config.get("disposition") != (
            "selected-clause-source-prose-and-test-anchor-not-full-record-approval"
        )
    ):
        raise ReferenceBaselineError("Unexpected conditional declaration audit scope")
    rows = config.get("entries")
    if not isinstance(rows, list) or len(rows) != 10:
        raise ReferenceBaselineError("Expected 10 selected conditional evidence cases")
    curated = load_curated_document(root / "data/curated/rules/n5-core-v5.3.json")
    records = {row["id"]: row for row in curated["records"]}
    seen: set[str] = set()
    verified = []
    document = None
    if pdf_path is not None:
        if _sha256(pdf_path) != config.get("sourceSha256"):
            raise ReferenceBaselineError("Conditional declaration PDF fingerprint mismatch")
        try:
            import pymupdf
        except ImportError as exc:
            raise ReferenceBaselineError("PyMuPDF required for PDF clause checks") from exc
        document = pymupdf.open(pdf_path)
    try:
        for entry in rows:
            key = entry.get("key")
            if not isinstance(key, str) or key in seen:
                raise ReferenceBaselineError(f"Duplicate/invalid conditional case: {key}")
            seen.add(key)
            record_id = entry["recordId"]
            page = entry["page"]
            field = entry["field"]
            needle = entry["factNeedle"]
            test_file = entry["testFile"]
            test_name = entry["testName"]
            record = records.get(record_id)
            if (record is None or record.get("review", {}).get("status") != "reviewed"
                    or not isinstance(page, int) or type(page) is not int
                    or field not in ("requirements", "effects", "restrictions",
                                     "clarifications")
                    or not isinstance(needle, str) or len(needle) < 15):
                raise ReferenceBaselineError(f"Invalid reviewed clause: {key}")
            facts = record.get("facts", {}).get(field, [])
            if not isinstance(facts, list) or not any(
                isinstance(clause, str) and needle in clause for clause in facts
            ):
                raise ReferenceBaselineError(f"Conditional fact clause drift: {key}")
            if not any(
                citation.get("sourceId") == config["sourceId"]
                and citation.get("page") == page
                for citation in record.get("citations", [])
            ):
                raise ReferenceBaselineError(f"Conditional citation drift: {key}")
            if not re.fullmatch(r"tests/test_[a-z0-9_]+\.py", test_file):
                raise ReferenceBaselineError(f"Unsafe conditional test path: {key}")
            if not re.fullmatch(r"test_[a-z0-9_]+", test_name):
                raise ReferenceBaselineError(f"Unsafe conditional test name: {key}")
            source = (root / test_file).read_text(encoding="utf-8")
            if not re.search(rf"^def {test_name}\(", source, re.M):
                raise ReferenceBaselineError(f"Missing conditional test anchor: {key}")
            if document is not None:
                if page < 1 or page > len(document):
                    raise ReferenceBaselineError(f"Invalid conditional source page: {key}")
                page_text = document[page - 1].get_text()
                if not isinstance(page_text, str):
                    raise ReferenceBaselineError(f"Invalid conditional PDF text: {key}")
                source_text = " ".join(page_text.split())
                raw_needle = entry.get("pdfNeedle")
                if not isinstance(raw_needle, str) or not raw_needle.strip():
                    raise ReferenceBaselineError(f"Invalid conditional PDF clause: {key}")
                pdf_needle = " ".join(raw_needle.split())
                if pdf_needle.casefold() not in source_text.casefold():
                    raise ReferenceBaselineError(f"Conditional PDF clause missing: {key}")
            verified.append({
                "key": key, "recordId": record_id, "sourcePage": page,
                "sourceField": field, "supportingTest": f"{test_file}::{test_name}",
                "scope": entry["scope"],
                "disposition": "selected-evidence-only-pending-full-record-review",
            })
    finally:
        if document is not None:
            document.close()
    return {
        "status": (
            "pinned-source-clause-and-curated-evidence-verified" if pdf_path
            else "curated-clause-citation-and-test-anchor-verified"
        ),
        "selectedCaseCount": len(verified),
        "cases": verified,
        "globalAroEligibilityReviewed": False,
        "fullRecordApprovalsIssued": 0,
    }


VISIBILITY_ZONE_REVIEW = (
    PROJECT_ROOT / "config/validation/visibility-zone-terms-v1.json"
)
VISIBILITY_ZONE_IDS = frozenset({
    "term:visibility-zone", "term:low-visibility-zone",
    "term:poor-visibility-zone", "term:zero-visibility-zone",
    "term:white-noise-zone",
})


def audit_visibility_zone_evidence(
    manifest_path: Path = VISIBILITY_ZONE_REVIEW,
    *,
    root: Path = PROJECT_ROOT,
    verify_pdfs: bool = False,
    source_layout: str = "legacy",
) -> dict[str, Any]:
    """Selected bilingual source/term/browser evidence, without whole-record approval."""
    from infinity_db.curated import load_curated_document

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("formatVersion") != 1
            or manifest.get("format") != (
                "InfinityDB V1-A08 five Visibility Zone term source and presentation evidence"
            )
            or manifest.get("scope") != (
                "five-post-inventory-terms-selected-clause-and-normal-browser-evidence-"
                "not-whole-corpus-acceptance"
            )
            or manifest.get("frozenInventoryCount") != 367
            or manifest.get("sourcePages") != {"english": 144, "spanish": 148}):
        raise ReferenceBaselineError("Unexpected Visibility Zone evidence scope")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or len(entries) != 5:
        raise ReferenceBaselineError("Visibility evidence must contain five terms")
    ids = [row.get("id") for row in entries if isinstance(row, dict)]
    if len(ids) != 5 or set(ids) != VISIBILITY_ZONE_IDS:
        raise ReferenceBaselineError("Visibility evidence identity drift")
    records = {
        record["id"]: record
        for record in load_curated_document(
            root / "data/curated/rules/n5-core-v5.3.json"
        )["records"]
    }
    required_tests = (
        "tests/test_web.py::test_visibility_zones_are_discoverable_in_glossary_and_global_search",
        "tests/test_web.py::test_visibility_zone_five_term_explanations_match_pinned_n5_3_source",
    )
    source_code = (root / "tests/test_web.py").read_text(encoding="utf-8")
    for test in required_tests:
        if f"def {test.split('::')[1]}(" not in source_code:
            raise ReferenceBaselineError(f"Visibility source test missing: {test}")
    verified_pages: list[str] = []
    pages: dict[str, str] = {}
    if verify_pdfs:
        import pymupdf

        expected_pins = {
            "data/pdf/rules/n5-rules-v5.3-en.pdf":
                "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f",
            "data/pdf/rules/n5-rules-v5.3-es.pdf":
                "7f564c864c6f26d6b218a0477c8afeba99da5c56e1a5369bb259f423689bb28f",
        }
        if manifest.get("sourcePins") != expected_pins:
            raise ReferenceBaselineError("Visibility source pin definitions changed")
        for language, (relative, pin) in zip(
            ("english", "spanish"), expected_pins.items(), strict=True
        ):
            try:
                path = pinned_pdf_path(root, relative, pin, layout=source_layout)
            except SourcePathError as exc:
                raise ReferenceBaselineError(
                    f"Visibility {language} PDF verification failed: {exc}"
                ) from exc
            if path is None:
                raise ReferenceBaselineError(f"Visibility {language} PDF unavailable")
            with pymupdf.open(path) as pdf:
                value = pdf[manifest["sourcePages"][language] - 1].get_text()
                if not isinstance(value, str):
                    raise ReferenceBaselineError(f"Visibility PDF text missing: {language}")
                pages[language] = " ".join(value.split()).casefold()
            verified_pages.append(language)
    verified_rows = []
    for entry in entries:
        identifier = entry["id"]
        record = records[identifier]
        if (
            record["kind"] != "term"
            or record["name"] != entry["name"]
            or record.get("review", {}).get("status") != "reviewed"
            or record.get("facts", {}).get("scope") != "visibility-condition"
            or entry["scope"] != "visibility-condition"
            or entry["sourceCitation"] != "n5-core-v5.3-pdf"
            or entry["sourcePage"] != 144
            or not any(
                c.get("sourceId") == "n5-core-v5.3-pdf" and c.get("page") == 144
                for c in record["citations"]
            )
            or entry["href"] != f"/glossary#{identifier.replace(':', '-')}"
            or not isinstance(entry["summaryClause"], str)
            or entry["summaryClause"] not in record["summary"]
            or entry["existingTests"] != list(required_tests)
        ):
            raise ReferenceBaselineError(f"Visibility term review drift: {identifier}")
        if verify_pdfs:
            for language in ("english", "spanish"):
                clause = entry[language + "Clause"]
                if not isinstance(clause, str) or (
                    " ".join(clause.split()).casefold() not in pages[language]
                ):
                    raise ReferenceBaselineError(
                        f"Visibility {language} source clause drift: {identifier}"
                    )
        verified_rows.append({
            "id": identifier, "name": record["name"], "href": entry["href"],
            "curatedReviewStatus": record["review"]["status"],
            "sourcePages": manifest["sourcePages"],
            "sourceDisposition": "selected-bilingual-clauses-reviewed",
            "browserDisposition": "selected-glossary-route-and-hash-test-evidence",
            "fullRecordAcceptance": "pending-whole-corpus-acceptance",
        })
    return {
        "status": "five-visibility-zone-terms-source-and-route-reconciled",
        "reviewedTermCount": len(verified_rows),
        "verifiedPdfLanguages": verified_pages,
        "records": verified_rows,
        "historicalInventoryExtended": False,
        "fullRecordApprovalsIssued": 0,
    }


def render_explanation_reconciliation(report: dict[str, Any]) -> str:
    """Compact work queue for reviewers, retaining exact IDs in the JSON."""
    lines = [
        "# Current explanation inventory reconciliation",
        "",
        "Historical D/S tiers remain frozen; this is **not a v1.0 release gate pass**.",
        "",
        f"- Frozen: {report['frozenCount']} (D {report['frozenTiers']['D']}; "
        f"S {report['frozenTiers']['S']})",
        f"- Current Core + Hacking: {report['currentCount']}; "
        f"{report['retainedCount']} retained, {report['addedCount']} added, "
        f"{report['removedCount']} retired",
        f"- Retained historical S: {len(report['retainedScreeningOnlyIds'])}",
        "- Added kinds: " + ", ".join(
            f"{key} {value}" for key, value in report["addedKinds"].items()
        ),
        f"- Source locators requiring clause/browser dispositions: "
        f"{report['sourceSectionCount']}",
        "",
        "## Retired declaration metadata (replacement not inferred)",
        "",
    ]
    for item in report["retiredIdentityRows"]:
        candidates = ", ".join(item["possibleReplacementIds"]) or "none"
        lines.append(f"- `{item['id']}` → possible new type peers: {candidates}; **not approved**")
    lines.extend(["", "## Added current identities by kind", ""])
    for kind in report["addedKinds"]:
        ids = [
            item["id"] for item in report["currentRecords"]
            if item["lineage"] == "added-after-frozen-inventory" and item["kind"] == kind
        ]
        lines.append(f"### {kind} ({len(ids)})")
        lines.extend(
            f"- `{identifier}` — source and browser acceptance pending"
            for identifier in ids
        )
        lines.append("")
    if "declarationMigrations" in report:
        crosswalk = report["declarationMigrations"]
        lines.extend([
            "## Historical declaration owner crosswalk",
            "",
            f"Historical source commit: `{crosswalk['historicalCommit']}`",
            "",
            "Old category IDs are historical grouped page markers, not stable "
            "gameplay identities. Common owner labels identify candidates only.",
            "",
        ])
        if "review" in crosswalk:
            review = crosswalk["review"]
            lines.extend([
                f"Verified: {review['retiredReviewed']} historical retirements and "
                f"{review['newHeadingsReviewed']} current source headings; "
                f"{review['kindCorrections']} kind corrections and "
                f"{review['multiOwnerSplits']} grouped-owner splits.",
                f"Evidence: `{review['status']}`. No historical aliases or "
                "whole-record approvals were created.",
                "",
            ])
        for item in crosswalk["transitions"]:
            lines.append(
                f"### `{item['retiredId']}` "
                f"({item['historicalCategory']}, p. {item['historicalPage']})"
            )
            for owner in item["ownerTransitions"]:
                targets = ", ".join(
                    f"`{entry['id']}` ({entry['typeId']}, p. {entry['page']})"
                    for entry in owner["currentCategories"]
                ) or "**no current declaration category**"
                lines.append(f"- {owner['entity']} `{owner['id']}` → {targets}")
            lines.append("")
        lines.extend(["## New declaration-category records", ""])
        for item in crosswalk["addedDeclarations"]:
            owners = ", ".join(
                f"{link['entity']}:{link['id']}" for link in item["owners"]
            )
            lines.append(
                f"- `{item['id']}` ({item['typeId']}, p. {item['page']}) "
                f"— {owners}"
            )
        lines.append("")
    if "reviewedEvidenceJoin" in report:
        summary = report["reviewedEvidenceJoin"]["summary"]
        lines.extend([
            "## Frozen-to-current reviewed evidence join",
            "",
            "**Provenance bridge, not full-source or browser acceptance.**",
            f"- Historical: {summary['frozen']} (D {summary['historicalD']}, "
            f"S {summary['historicalS']}); {summary['retained']} retained, "
            f"{summary['retiredDeclarations']} reviewed declaration retirements.",
            f"- Current: {summary['current']} records, including "
            f"{summary['added']} post-inventory additions.",
            f"- Retained historical S: {summary['retainedHistoricalS']}; "
            "all historical tiers and original denominators unchanged.",
            f"- Frozen identities pointing to later selected evidence: "
            f"{summary['historicalIdentitiesWithLaterEvidence']} of "
            f"{summary['frozen']} (not whole-record approvals).",
            f"- Selected evidence: {summary['reviewedDeclarationTransitions']} "
            "retired declaration ownership transitions; "
            f"{summary['reviewedNewDeclarationHeadings']} current declaration "
            "headings; "
            f"{summary['selectedConditionalCases']} conditional clause cases; "
            f"{summary['selectedVisibilityTerms']} Visibility Zone terms; "
            f"{summary['selectedBrowserTestAnchors']} browser test anchors.",
            f"- Distinct current identities with some later evidence: "
            f"{summary['currentIdentitiesWithLaterEvidence']}. "
            "This is not a whole-record approval count.",
            f"- Pending source section/locator dispositions: "
            f"{summary['pendingSourceSections']}; "
            f"whole-record approvals: {summary['wholeRecordApprovals']}.",
            "",
            "The JSON report records all 367 original identities, each reviewed "
            "declaration owner mapping, all current curated identities and the "
            "specific limited later evidence links. A retired category is not "
            "a rename or a new public alias; a test anchor is not test execution.",
            "",
        ])
    if "numericArmyVariants" in report:
        evidence = report["numericArmyVariants"]
        lines.extend([
            "## Pinned Army numerical Skill variants",
            "",
            f"Source: `{evidence['armyArchiveSha256']}`",
            f"Verified: {evidence['variantCount']} Skill source variants, "
            f"{evidence['factionFileOccurrenceCount']} faction-file occurrences.",
            "All are loadout-specific Skills. Base Unit attributes remain unchanged.",
            "",
        ])
        for entry in evidence["records"]:
            bases = sorted({
                value for item in entry["occurrences"]
                for value in item["profileBaseValues"]
            })
            lines.append(
                f"- `{entry['id']}`: {entry['baseAttribute']} = "
                f"{entry['replacementValue']}, "
                f"{entry['factionFileOccurrences']} source occurrences "
                f"(parent profile values {bases}); source "
                f"`{entry['sourceActionRule']}`"
            )
        lines.extend([
            "",
            "This is source-identity/occurrence verification, **not** a "
            "runtime combat calculator or whole-record signoff.",
            "",
        ])
    if "conditionalDeclarations" in report:
        evidence = report["conditionalDeclarations"]
        lines.extend([
            "## Selected declaration and reaction exception evidence",
            "",
            f"Verified {evidence['selectedCaseCount']} source-scoped clauses: "
            f"`{evidence['status']}`.",
            "This does not verify general ARO eligibility or certify all records.",
            "",
        ])
        for entry in evidence["cases"]:
            lines.append(
                f"- `{entry['recordId']}` (p. {entry['sourcePage']}): "
                f"{entry['scope']} — {entry['supportingTest']}"
            )
        lines.append("")
    if "visibilityZones" in report:
        evidence = report["visibilityZones"]
        lines.extend([
            "## Five post-inventory Visibility Zone Game terms",
            "",
            f"Reviewed: {evidence['reviewedTermCount']} source-specific term definitions.",
            f"Bilingual PDF clauses verified: "
            f"{', '.join(evidence['verifiedPdfLanguages']) or 'not requested'}.",
            "Previously reviewed browser routes are selected evidence, "
            "**not full-record approval**.",
            "",
        ])
        for entry in evidence["records"]:
            lines.append(
                f"- `{entry['id']}` — `{entry['href']}`; "
                f"{entry['sourceDisposition']}; "
                f"{entry['browserDisposition']}; full gate pending"
            )
        lines.append("")
    remaining = report["remainingWork"]
    if "reviewedEvidenceJoin" in report:
        remaining = [
            "Carry the 17 owner-verified declaration retirements and their "
            "20 current heading owners through clause and normal-browser "
            "acceptance; never publish old page/category IDs as aliases",
            *remaining[1:],
        ]
    lines.extend([
        "## Remaining acceptance",
        "",
        *[f"- [ ] {item}" for item in remaining],
        "",
        "The JSON report contains every current identity, source locator, historical tier "
        "and explicit pending disposition. Do not convert a reviewed curation flag, "
        "a citation or a successful selected browser test into whole-record sign-off.",
        "",
    ])
    return "\n".join(lines)


CURRENT_CITATION_COLLECTIONS = (
    "n5-core-v5.3",
    "n5-hacking-programs-v5.3",
    "n5-faq-v0.1",
)


def _is_current_rule_citation_source(
    source: dict[str, Any], *, collection_id: str,
) -> bool:
    """Classify declared current N5 source *identity*, not semantic correctness."""
    identifier = source.get("id")
    version = source.get("version")
    if not isinstance(identifier, str) or not isinstance(version, str):
        return False
    has_reference = bool(source.get("url")) or bool(
        source.get("localPath") and source.get("sha256")
    )
    if not has_reference:
        return False
    if collection_id == "n5-faq-v0.1":
        return identifier in {"n5-faq-v0.1-en-pdf", "n5-faq-v0.1-es-pdf"} and (
            version == "0.1"
        )
    if identifier in {"n5-core-v5.3-pdf", "n5-core-v5.3-es-pdf"}:
        return version == "5.3"
    if identifier in {"n5-faq-v0.1-en-pdf", "n5-faq-v0.1-es-pdf"}:
        return version == "0.1"
    if identifier == "its-season-18-en-pdf":
        return version == "2026.09.01"
    if source.get("kind") == "wiki":
        if identifier in {
            "wiki-en-20260926-200832", "wiki-es-20261009-211304",
        }:
            return bool(source.get("sha256")) and version.startswith("2026")
        return version.startswith("N5.3")
    return False


def audit_current_rule_citation_minimum(
    *,
    root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Report current-source citation coverage for maintained N5 reference owners.

    The authoritative curated loader already checks nonempty citations,
    known source IDs, and locator shape. This additional read-only release
    audit identifies records whose citations reference only noncurrent sources.
    It does not inspect source text, adjudicate versions, or verify browser routes.
    """
    from infinity_db.curated import load_curated_document

    by_collection = []
    gaps = []
    for collection_id in CURRENT_CITATION_COLLECTIONS:
        path = root / "data/curated/rules" / f"{collection_id}.json"
        document = load_curated_document(path)
        collection = document["collection"]
        if collection["id"] != collection_id or collection["status"] != "current":
            raise ReferenceBaselineError(
                f"Current citation collection changed: {collection_id}"
            )
        eligible = {
            source["id"] for source in document["sources"]
            if _is_current_rule_citation_source(
                source, collection_id=collection_id,
            )
        }
        if not eligible:
            raise ReferenceBaselineError(
                f"No declared current source identities: {collection_id}"
            )
        checked = 0
        covered = 0
        for record in document["records"]:
            checked += 1
            cited = {citation["sourceId"] for citation in record["citations"]}
            if cited & eligible:
                covered += 1
            else:
                gaps.append({
                    "collection": collection_id,
                    "recordId": record["id"],
                    "citedSourceIds": sorted(cited),
                })
        by_collection.append({
            "collection": collection_id,
            "records": checked,
            "withCurrentCitation": covered,
            "withoutCurrentCitation": checked - covered,
            "currentSourceIds": sorted(eligible),
        })
    return {
        "format": "InfinityDB current citation minimum",
        "formatVersion": 1,
        "scope": "current-core-hacking-faq-records",
        "evidence": "declared-version-and-locator-only-not-source-semantics-or-browser",
        "totalRecords": sum(row["records"] for row in by_collection),
        "withCurrentCitation": sum(row["withCurrentCitation"] for row in by_collection),
        "withoutCurrentCitation": len(gaps),
        "collections": by_collection,
        "gaps": gaps,
        "excludedScope": [
            "optional-n4-origin-reinforcements",
            "its-season-18-only",
            "weapon-property-origin-projection",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=REPORT_FORMAT)
    parser.add_argument("--army-db", type=Path, default=PROJECT_ROOT / "data/generated/army.db")
    parser.add_argument(
        "--rules-db", type=Path, default=PROJECT_ROOT / "data/generated/rules_n5.db",
    )
    parser.add_argument("--army-archive", type=Path, help="Verify exact ZIP bytes against Army pin")
    parser.add_argument(
        "--source-layout", choices=("legacy", "local"), default="local",
        help="Select physical PDF evidence under data/pdf or local/data/pdf; labels stay unchanged",
    )
    parser.add_argument(
        "--normalized", type=Path,
        help="Attested normalized.json for --army-archive, without a raw sibling",
    )
    parser.add_argument(
        "--verify-server", metavar="BASE_URL",
        help="Check that the server uses this exact Army/rules database pair",
    )
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument(
        "--audit-current-citation-minimum", action="store_true",
        help="Check current Core/Hacking/FAQ records for at least one current source",
    )
    parser.add_argument(
        "--review-batches-output", type=Path,
        help="Write a triage-only review batch plan under ignored local/",
    )
    parser.add_argument(
        "--review-pilot-output", type=Path,
        help="Write the fixed 35-record source-review pilot to ignored local/",
    )
    parser.add_argument(
        "--reconcile-explanation-inventory", action="store_true",
        help="Compare frozen 367-record explanation inventory to current Core/Hacking",
    )
    parser.add_argument(
        "--reconcile-declarations", action="store_true",
        help="Include historical Git ownership crosswalk for retired declarations",
    )
    parser.add_argument(
        "--verify-declaration-pdf", type=Path,
        help="Verify the 20 added printed declaration headings against exact N5.3 PDF bytes",
    )
    parser.add_argument(
        "--verify-numeric-army-archive", type=Path,
        help="Audit three source-native numerical replacement Skills in a pinned Army ZIP",
    )
    parser.add_argument(
        "--audit-conditional-declarations", action="store_true",
        help="Cross-check selected ARO and declaration exceptions without global acceptance",
    )
    parser.add_argument(
        "--verify-conditional-pdf", type=Path,
        help="Check selected conditional clauses against pinned N5.3 PDF",
    )
    parser.add_argument(
        "--audit-visibility-zones", action="store_true",
        help="Reconcile five post-inventory visibility terms and selected evidence",
    )
    parser.add_argument(
        "--join-reviewed-evidence", action="store_true",
        help="Join 367 frozen identities to current records and later bounded evidence",
    )
    parser.add_argument(
        "--verify-visibility-pdfs", action="store_true",
        help="Verify exact pinned English and Spanish Visibility Zone clauses",
    )
    args = parser.parse_args(argv)
    try:
        _require_new_report_outputs(
            args.json_output, args.markdown_output,
            args.review_batches_output, args.review_pilot_output,
        )
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Reference baseline output: {exc}\n")
    if args.audit_current_citation_minimum:
        if (
            args.reconcile_explanation_inventory
            or args.review_batches_output is not None
            or args.review_pilot_output is not None
            or args.join_reviewed_evidence
            or args.reconcile_declarations
            or args.verify_declaration_pdf is not None
            or args.verify_numeric_army_archive is not None
            or args.audit_conditional_declarations
            or args.verify_conditional_pdf is not None
            or args.audit_visibility_zones
            or args.verify_visibility_pdfs
            or args.markdown_output is not None
            or args.army_archive is not None
            or args.verify_server is not None
        ):
            parser.error("Current citation minimum is a standalone read-only audit")
        minimum = audit_current_rule_citation_minimum()
        if args.json_output is not None:
            _write_report_or_exit(
                parser, args.json_output,
                json.dumps(minimum, indent=2, sort_keys=True) + "\n",
            )
        print(
            f"Current N5 citation minimum: {minimum['withCurrentCitation']}/"
            f"{minimum['totalRecords']} records have a declared current source; "
            f"{minimum['withoutCurrentCitation']} missing"
        )
        for gap in minimum["gaps"]:
            print(f"  {gap['collection']} / {gap['recordId']}: "
                  f"{', '.join(gap['citedSourceIds'])}")
        return 1 if minimum["gaps"] else 0
    if args.reconcile_explanation_inventory:
        if args.verify_declaration_pdf is not None and not args.reconcile_declarations:
            parser.error("--verify-declaration-pdf requires --reconcile-declarations")
        if args.verify_conditional_pdf is not None and not args.audit_conditional_declarations:
            parser.error("--verify-conditional-pdf requires --audit-conditional-declarations")
        if args.verify_visibility_pdfs and not args.audit_visibility_zones:
            parser.error("--verify-visibility-pdfs requires --audit-visibility-zones")
        if args.join_reviewed_evidence and not (
            args.reconcile_declarations and args.audit_conditional_declarations
            and args.audit_visibility_zones
        ):
            parser.error(
                "--join-reviewed-evidence requires --reconcile-declarations, "
                "--audit-conditional-declarations and --audit-visibility-zones"
            )
        report = reconcile_explanation_inventory()
        if args.review_pilot_output is not None:
            target = args.review_pilot_output
            if not target.resolve().is_relative_to((PROJECT_ROOT / "local").resolve()):
                parser.error("--review-pilot-output must be under ignored local/")
            pilot = build_explanation_review_pilot(report)
            _write_report_or_exit(
                parser, target, json.dumps(pilot, indent=2, ensure_ascii=False) + "\n",
            )
            summary = pilot["summary"]
            if summary["sourcePageIdentityComplete"]:
                page_summary = (
                    f"{summary['uniqueSelectedSourcePages']} source pages / "
                    f"{summary['sourcePageOpensPotentiallyReusable']} potentially "
                    "reusable page opens"
                )
            else:
                page_summary = (
                    f"{summary['knownUniqueSourcePageIdentities']} known source-page "
                    f"identities / {summary['unresolvedSourcePageIdentityLocators']} "
                    "unresolved page-identity locators; page-open reuse unknown"
                )
            print(
                f"Review pilot: {summary['selectedRecords']} records / "
                f"{summary['semanticCohorts']} cohorts / "
                f"{summary['selectedSourceCitationOccurrences']} citation occurrences / "
                f"{summary['uniqueSelectedSourceLocators']} unique locators / "
                f"{page_summary} / "
                f"{summary['sourceFirstProbes']} source-first probes; zero approvals"
            )
        if args.review_batches_output is not None:
            target = args.review_batches_output
            if not target.resolve().is_relative_to((PROJECT_ROOT / "local").resolve()):
                parser.error("--review-batches-output must be under ignored local/")
            plan = plan_explanation_review_batches(report)
            _write_report_or_exit(
                parser, target, json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
            )
            summary = plan["summary"]
            print(
                f"Review batches: {summary['batches']} batches / "
                f"{summary['currentRecords']} records / "
                f"{summary['sourceLocators']} source locators / "
                f"{summary['sharedSourceLocators']} shared locators; "
                "zero approvals issued"
            )
        if args.audit_visibility_zones:
            evidence = audit_visibility_zone_evidence(
                verify_pdfs=args.verify_visibility_pdfs, source_layout=args.source_layout,
            )
            ids = {record["id"] for record in evidence["records"]}
            added = set(report["addedIds"])
            if ids != VISIBILITY_ZONE_IDS or not ids <= added:
                raise ReferenceBaselineError("Visibility identities are not post-inventory")
            report["visibilityZones"] = evidence
        if args.audit_conditional_declarations:
            report["conditionalDeclarations"] = audit_conditional_declaration_evidence(
                pdf_path=args.verify_conditional_pdf,
            )
        if args.verify_numeric_army_archive is not None:
            report["numericArmyVariants"] = audit_numeric_army_replacement_variants(
                args.verify_numeric_army_archive,
            )
        if args.reconcile_declarations:
            crosswalk = reconcile_declaration_owners(report)
            crosswalk["review"] = verify_declaration_review(
                crosswalk, pdf_path=args.verify_declaration_pdf,
            )
            report["declarationMigrations"] = crosswalk
        if args.join_reviewed_evidence:
            report["reviewedEvidenceJoin"] = join_explanation_reviewed_evidence(report)
        for path, content in (
            (args.json_output, json.dumps(report, indent=2, ensure_ascii=False) + "\n"),
            (args.markdown_output, render_explanation_reconciliation(report)),
        ):
            if path is not None:
                _write_report_or_exit(parser, path, content)
        print(
            f"Explanation inventory: {report['frozenCount']} frozen, "
            f"{report['currentCount']} current, {report['retainedCount']} retained, "
            f"{report['addedCount']} added, {report['removedCount']} retired; "
            f"{report['sourceSectionCount']} source locators pending clause review"
        )
        return 0
    if (args.review_batches_output is not None or args.review_pilot_output is not None
            or args.reconcile_declarations
            or args.verify_declaration_pdf is not None
            or args.verify_numeric_army_archive is not None
            or args.audit_conditional_declarations or args.verify_conditional_pdf is not None
            or args.audit_visibility_zones or args.verify_visibility_pdfs
            or args.join_reviewed_evidence):
        parser.error("reconciliation flags require --reconcile-explanation-inventory")
    if args.normalized is not None and args.army_archive is None:
        parser.error("--normalized requires --army-archive")
    report = build_baseline(
        args.army_db, args.rules_db, army_archive=args.army_archive,
        normalized=args.normalized, source_layout=args.source_layout,
    )
    if args.verify_server:
        try:
            report["servedSnapshot"] = verify_served_revision(report, args.verify_server)
        except ReferenceBaselineError as exc:
            print(f"Release snapshot mismatch: {exc}", file=sys.stderr)
            return 1
    for path, content in (
        (args.json_output, json.dumps(report, indent=2, sort_keys=True) + "\n"),
        (args.markdown_output, render_markdown(report)),
    ):
        if path is not None:
            _write_report_or_exit(parser, path, content)
    print(f"{REPORT_FORMAT}: {len(report['inventory'])} category rows, "
          f"{len(report['sourceGroups'])} source groups; all require review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
