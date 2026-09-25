#!/usr/bin/env python3
"""Audit Fireteam chart semantics preserved in the normalized InfinityDB database."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPORT_FORMAT = "InfinityDB Fireteam semantics audit"
REPORT_FORMAT_VERSION = 1

REQUIRED_COLUMNS: dict[str, tuple[str, ...]] = {
    "army_lists": (
        "id",
        "name",
        "kind",
        "fireteam_description",
        "fireteam_spec",
    ),
    "fireteams": ("army_id", "fireteam_id", "position", "name", "observation"),
    "fireteam_types": ("army_id", "fireteam_id", "position", "fireteam_type"),
    "fireteam_members": (
        "army_id",
        "fireteam_id",
        "member_id",
        "position",
        "slug",
        "name",
        "comment",
        "min_count",
        "max_count",
        "required",
        "resolved_unit_id",
        "resolution",
    ),
    "army_units": ("army_id", "unit_id"),
    "units": ("id", "name", "slug"),
    "loadout_options": ("army_id", "unit_id", "group_id", "option_id", "name"),
    "application_armies": ("id", "name", "role", "playable"),
    "application_army_sources": ("application_army_id", "source_army_id"),
    "application_army_reinforcement_parents": (
        "reinforcement_army_id",
        "parent_army_id",
    ),
    "__infinity_metadata": ("key", "value"),
}

_FTO_RE = re.compile(r"\bFTO(?:[-\s]?(\d+))?\b", re.IGNORECASE)
_BRACKET_RE = re.compile(r"\(([^()]*)\)")


class FireteamSemanticsAuditError(ValueError):
    """Raised when the selected database cannot be audited safely."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_schema(connection: sqlite3.Connection) -> None:
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    missing_tables = sorted(set(REQUIRED_COLUMNS) - tables)
    if missing_tables:
        raise FireteamSemanticsAuditError(
            f"Database is missing required tables: {', '.join(missing_tables)}"
        )
    for table, required in REQUIRED_COLUMNS.items():
        columns = {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}
        missing = sorted(set(required) - columns)
        if missing:
            raise FireteamSemanticsAuditError(
                f"Table {table!r} is missing required columns: {', '.join(missing)}"
            )


def _snapshot_metadata(connection: sqlite3.Connection) -> dict[str, Any]:
    row = connection.execute(
        "SELECT value FROM __infinity_metadata WHERE key = '_meta'"
    ).fetchone()
    if row is None:
        raise FireteamSemanticsAuditError("Database metadata row '_meta' is missing")
    try:
        metadata = json.loads(row[0])
    except (TypeError, json.JSONDecodeError) as exc:
        raise FireteamSemanticsAuditError("Database metadata row '_meta' is invalid JSON") from exc
    if not isinstance(metadata, dict):
        raise FireteamSemanticsAuditError("Database metadata row '_meta' must be an object")
    return metadata


def _decode_spec(value: Any, army_id: int) -> dict[str, int]:
    if value in (None, ""):
        return {}
    try:
        spec = json.loads(value) if isinstance(value, str) else value
    except json.JSONDecodeError as exc:
        raise FireteamSemanticsAuditError(
            f"Army {army_id} has invalid fireteam_spec JSON"
        ) from exc
    if not isinstance(spec, dict):
        raise FireteamSemanticsAuditError(
            f"Army {army_id} fireteam_spec must decode to an object"
        )
    result: dict[str, int] = {}
    for key, raw in spec.items():
        if not isinstance(key, str) or type(raw) is not int or raw < 0:
            raise FireteamSemanticsAuditError(
                f"Army {army_id} has invalid Fireteam limit {key!r}={raw!r}"
            )
        result[key.upper()] = raw
    return result


def _ascii_upper(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    plain = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return plain.upper()


def _fto_marker(value: str | None) -> str | None:
    match = _FTO_RE.search(_ascii_upper(value))
    if match is None:
        return None
    return match.group(1) or "generic"


def _member_fto_marker(name: str | None, comment: str | None) -> str | None:
    matches = _FTO_RE.findall(f"{_ascii_upper(name)} {_ascii_upper(comment)}")
    if not matches:
        return None
    numbered = [match for match in matches if match]
    return numbered[0] if numbered else "generic"


def _identity_tokens(value: str | None) -> tuple[str, ...]:
    text = _ascii_upper(value)
    text = _FTO_RE.sub(" ", text)
    # Army currently uses both REINF. and REF. around Reinforcement FTO labels.
    text = re.sub(r"\b(?:REINF|REF)\b", " ", text)
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    tokens: list[str] = []
    for token in text.split():
        if token == "THE":
            continue
        if token == "KNIGHTS":
            token = "KNIGHT"
        tokens.append(token)
    return tuple(tokens)


def _fto_option_matches(member_name: str | None, marker: str, option_name: str | None) -> bool:
    option_marker = _fto_marker(option_name)
    if option_marker is None:
        return False
    if marker != "generic" and option_marker != marker:
        return False
    member_tokens = set(_identity_tokens(member_name))
    option_tokens = set(_identity_tokens(option_name))
    if not member_tokens or not option_tokens:
        return False
    return member_tokens <= option_tokens or option_tokens <= member_tokens


def _chart_shape(connection: sqlite3.Connection) -> dict[str, Any]:
    counts = {}
    for table in ("army_lists", "fireteams", "fireteam_types", "fireteam_members"):
        counts[table] = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    type_counts = {
        row[0]: row[1]
        for row in connection.execute(
            "SELECT fireteam_type, COUNT(*) FROM fireteam_types "
            "GROUP BY fireteam_type ORDER BY fireteam_type"
        )
    }
    return {
        "sourceArmyCount": counts["army_lists"],
        "teamCount": counts["fireteams"],
        "typeMembershipCount": counts["fireteam_types"],
        "memberCount": counts["fireteam_members"],
        "typeMembershipCounts": type_counts,
        "policy": (
            "Fireteam Charts are Army-local configuration/relationship data. Team names, "
            "type membership, member wording, cardinality, and notes remain attached to the "
            "source Army context rather than becoming logical-Unit facts."
        ),
    }


def _type_limits(connection: sqlite3.Connection) -> dict[str, Any]:
    value_counts: dict[str, Counter[int]] = defaultdict(Counter)
    unknown_values: list[dict[str, Any]] = []
    reinforcement_zero_type_memberships: list[dict[str, Any]] = []

    army_rows = connection.execute(
        "SELECT id, kind, fireteam_spec FROM army_lists ORDER BY id"
    ).fetchall()
    specs: dict[int, dict[str, int]] = {}
    kinds: dict[int, str | None] = {}
    for row in army_rows:
        army_id = row["id"]
        spec = _decode_spec(row["fireteam_spec"], army_id)
        specs[army_id] = spec
        kinds[army_id] = row["kind"]
        for fireteam_type, limit in sorted(spec.items()):
            value_counts[fireteam_type][limit] += 1
            if limit not in (0, 256) and limit < 1:
                unknown_values.append(
                    {"armyId": army_id, "fireteamType": fireteam_type, "value": limit}
                )

    source_types: dict[int, set[str]] = defaultdict(set)
    for row in connection.execute(
        "SELECT DISTINCT army_id, fireteam_type FROM fireteam_types "
        "ORDER BY army_id, fireteam_type"
    ):
        source_types[row["army_id"]].add(row["fireteam_type"].upper())

    for army_id, fireteam_types in sorted(source_types.items()):
        if kinds.get(army_id) != "reinforcement":
            continue
        spec = specs.get(army_id, {})
        for fireteam_type in sorted(fireteam_types):
            if spec.get(fireteam_type) == 0:
                reinforcement_zero_type_memberships.append(
                    {"sourceArmyId": army_id, "fireteamType": fireteam_type}
                )

    return {
        "rawValueCounts": {
            fireteam_type: {str(value): count for value, count in sorted(counts.items())}
            for fireteam_type, counts in sorted(value_counts.items())
        },
        "interpretation": {
            "0": "unavailable in the selected parent Army context",
            "256": "unlimited",
            "positiveOther": "finite maximum count",
        },
        "unknownValueCount": len(unknown_values),
        "unknownValues": unknown_values,
        "reinforcementSectionTypeRowsWhoseOwnSpecIsZeroCount": len(
            reinforcement_zero_type_memberships
        ),
        "reinforcementSectionTypeRowsWhoseOwnSpecIsZero": reinforcement_zero_type_memberships,
        "policy": (
            "Preserve the raw chart spec. Reinforcement-section charts can contain Fireteam "
            "types while their own spec says zero, so their own spec is not a standalone "
            "legality rule; selected parent-Army limits remain separate context."
        ),
    }


def _member_resolution(connection: sqlite3.Connection) -> dict[str, Any]:
    counts = {
        row["resolution"]: row["count"]
        for row in connection.execute(
            "SELECT resolution, COUNT(*) AS count FROM fireteam_members "
            "GROUP BY resolution ORDER BY resolution"
        )
    }
    details = [
        dict(row)
        for row in connection.execute(
            "SELECT fm.army_id AS armyId, fm.fireteam_id AS fireteamId, "
            "f.name AS fireteamName, fm.member_id AS memberId, fm.slug, fm.name, "
            "fm.comment, fm.resolved_unit_id AS resolvedUnitId, fm.resolution "
            "FROM fireteam_members AS fm "
            "JOIN fireteams AS f USING (army_id, fireteam_id) "
            "WHERE fm.resolution <> 'army' "
            "ORDER BY fm.army_id, fm.fireteam_id, fm.member_id"
        )
    ]
    return {
        "resolutionCounts": counts,
        "nonArmyResolutionCount": len(details),
        "nonArmyResolutions": details,
        "policy": (
            "A normalized Unit-level match is useful provenance but is not sufficient to "
            "establish Fireteam option/subprofile eligibility. Non-local or unresolved source "
            "wording remains explicit rather than being guessed."
        ),
    }


def _required_choice_evidence(connection: sqlite3.Connection) -> dict[str, Any]:
    required_rows = connection.execute(
        "SELECT COUNT(*) FROM fireteam_members WHERE required = 1"
    ).fetchone()[0]
    team_rows = connection.execute(
        "SELECT army_id, fireteam_id, "
        "SUM(CASE WHEN required = 1 THEN 1 ELSE 0 END) AS required_count "
        "FROM fireteam_members GROUP BY army_id, fireteam_id "
        "HAVING required_count > 0 ORDER BY army_id, fireteam_id"
    ).fetchall()
    distribution = Counter(row["required_count"] for row in team_rows)
    positive_min = connection.execute(
        "SELECT COUNT(*) FROM fireteam_members "
        "WHERE required = 1 AND COALESCE(min_count, 0) > 0"
    ).fetchone()[0]
    return {
        "requiredMemberRowCount": required_rows,
        "teamCount": len(team_rows),
        "requiredRowsPerTeamDistribution": {
            str(size): count for size, count in sorted(distribution.items())
        },
        "requiredRowsWithPositiveMinCount": positive_min,
        "policy": (
            "Treat required=true as participation in the chart's required-choice pool. "
            "Preserve min/max independently; do not infer that every required row must be "
            "present simultaneously."
        ),
    }


def _wildcard_evidence(connection: sqlite3.Connection) -> dict[str, Any]:
    team_count, army_count = connection.execute(
        "SELECT COUNT(*), COUNT(DISTINCT army_id) FROM fireteams "
        "WHERE UPPER(name) LIKE '%WILDCARD%'"
    ).fetchone()
    typed = connection.execute(
        "SELECT COUNT(*) FROM fireteam_types AS ft "
        "JOIN fireteams AS f USING (army_id, fireteam_id) "
        "WHERE UPPER(f.name) LIKE '%WILDCARD%'"
    ).fetchone()[0]
    return {
        "teamCount": team_count,
        "sourceArmyCount": army_count,
        "typeMembershipCount": typed,
        "policy": (
            "Wildcard rows are Army-local cross-team eligibility relationships, not a "
            "Fireteam type and not an intrinsic logical-Unit property."
        ),
    }


def _level_equivalence_evidence(connection: sqlite3.Connection) -> dict[str, Any]:
    row_count = 0
    labels: list[str] = []
    for row in connection.execute(
        "SELECT comment FROM fireteam_members WHERE COALESCE(comment, '') <> ''"
    ):
        matches = _BRACKET_RE.findall(row["comment"])
        if not matches:
            continue
        row_count += 1
        for match in matches:
            labels.extend(part.strip() for part in match.split(",") if part.strip())
    return {
        "memberRowCount": row_count,
        "labelReferenceCount": len(labels),
        "distinctLabelCount": len(set(labels)),
        "policy": (
            "Bracketed terms are preserved as Fireteam-Level equivalence wording. They must "
            "not feed logical-Unit identity or generic Unit aliasing."
        ),
    }


def _rule_bearing_notes(connection: sqlite3.Connection) -> dict[str, Any]:
    army_notes = [
        dict(row)
        for row in connection.execute(
            "SELECT id AS sourceArmyId, name AS armyName, "
            "fireteam_description AS description FROM army_lists "
            "WHERE COALESCE(fireteam_description, '') <> '' ORDER BY id"
        )
    ]
    team_notes = [
        dict(row)
        for row in connection.execute(
            "SELECT army_id AS sourceArmyId, fireteam_id AS fireteamId, name AS fireteamName, "
            "observation FROM fireteams WHERE COALESCE(observation, '') <> '' "
            "ORDER BY army_id, fireteam_id"
        )
    ]
    return {
        "armyDescriptionCount": len(army_notes),
        "teamObservationCount": len(team_notes),
        "armyDescriptions": army_notes,
        "teamObservations": team_notes,
        "policy": (
            "Preserve Fireteam chart descriptions and observations verbatim because chart "
            "notes can specialize or override general Fireteam rules."
        ),
    }


def _fto_evidence(connection: sqlite3.Connection) -> dict[str, Any]:
    rows = connection.execute(
        "SELECT fm.*, f.name AS fireteam_name FROM fireteam_members AS fm "
        "JOIN fireteams AS f USING (army_id, fireteam_id) "
        "ORDER BY fm.army_id, fm.fireteam_id, fm.member_id"
    ).fetchall()
    loadouts: dict[tuple[int, int], list[sqlite3.Row]] = defaultdict(list)
    for row in connection.execute(
        "SELECT army_id, unit_id, group_id, option_id, name FROM loadout_options "
        "ORDER BY army_id, unit_id, group_id, option_id"
    ):
        loadouts[(row["army_id"], row["unit_id"])].append(row)

    status_counts: Counter[str] = Counter()
    details: list[dict[str, Any]] = []
    eligible_option_count = 0
    for row in rows:
        marker = _member_fto_marker(row["name"], row["comment"])
        if marker is None:
            continue
        base = {
            "sourceArmyId": row["army_id"],
            "fireteamId": row["fireteam_id"],
            "fireteamName": row["fireteam_name"],
            "memberId": row["member_id"],
            "memberName": row["name"],
            "comment": row["comment"],
            "marker": "FTO" if marker == "generic" else f"FTO-{marker}",
            "resolvedUnitId": row["resolved_unit_id"],
        }
        if row["resolution"] != "army" or row["resolved_unit_id"] is None:
            status = "source-unit-context-mismatch"
            status_counts[status] += 1
            details.append({**base, "status": status, "resolution": row["resolution"]})
            continue

        matches = [
            option
            for option in loadouts[(row["army_id"], row["resolved_unit_id"])]
            if _fto_option_matches(row["name"], marker, option["name"])
        ]
        if not matches:
            status = "no-matching-fto-option"
            status_counts[status] += 1
            details.append({**base, "status": status})
            continue

        status = "resolved"
        status_counts[status] += 1
        eligible_option_count += len(matches)
        details.append(
            {
                **base,
                "status": status,
                "eligibleOptions": [
                    {
                        "groupId": option["group_id"],
                        "optionId": option["option_id"],
                        "name": option["name"],
                    }
                    for option in matches
                ],
            }
        )

    unresolved = [detail for detail in details if detail["status"] != "resolved"]
    return {
        "memberRowCount": len(details),
        "statusCounts": dict(sorted(status_counts.items())),
        "eligibleOptionOccurrenceCount": eligible_option_count,
        "unresolvedCount": len(unresolved),
        "unresolved": unresolved,
        "policy": (
            "Resolve FTO against Army-local loadout-option identity. Generic FTO accepts "
            "matching FTO variants; numbered FTO-N requires that variant. Preserve any "
            "source-context or option mismatch instead of inferring eligibility from Unit "
            "identity alone."
        ),
    }


def _unit_granularity_evidence(connection: sqlite3.Connection) -> dict[str, Any]:
    details = [
        dict(row)
        for row in connection.execute(
            "SELECT army_id AS sourceArmyId, fireteam_id AS fireteamId, "
            "resolved_unit_id AS resolvedUnitId, COUNT(*) AS memberCount, "
            "GROUP_CONCAT(name, ' | ') AS memberNames FROM fireteam_members "
            "WHERE resolution = 'army' AND resolved_unit_id IS NOT NULL "
            "GROUP BY army_id, fireteam_id, resolved_unit_id HAVING COUNT(*) > 1 "
            "ORDER BY army_id, fireteam_id, resolved_unit_id"
        )
    ]
    return {
        "sameSourceUnitMultipleMemberCaseCount": len(details),
        "cases": details,
        "policy": (
            "A Fireteam member can identify a subgroup/profile/loadout within one source Unit. "
            "Do not collapse member identity to resolved_unit_id when multiple chart rows point "
            "at the same Unit."
        ),
    }


def _reinforcement_context(connection: sqlite3.Connection) -> dict[str, Any]:
    application_armies = {
        row["id"]: dict(row)
        for row in connection.execute(
            "SELECT id, name, role, playable FROM application_armies ORDER BY id"
        )
    }
    source_to_application = {
        row["source_army_id"]: row["application_army_id"]
        for row in connection.execute(
            "SELECT application_army_id, source_army_id FROM application_army_sources"
        )
    }
    application_sources: dict[int, list[int]] = defaultdict(list)
    for source_id, application_id in source_to_application.items():
        application_sources[application_id].append(source_id)

    source_specs: dict[int, dict[str, int]] = {}
    source_kinds: dict[int, str | None] = {}
    for row in connection.execute(
        "SELECT id, kind, fireteam_spec FROM army_lists ORDER BY id"
    ):
        source_specs[row["id"]] = _decode_spec(row["fireteam_spec"], row["id"])
        source_kinds[row["id"]] = row["kind"]

    source_types: dict[int, set[str]] = defaultdict(set)
    for row in connection.execute(
        "SELECT DISTINCT army_id, fireteam_type FROM fireteam_types"
    ):
        source_types[row["army_id"]].add(row["fireteam_type"].upper())

    reinforcement_types: dict[int, set[str]] = defaultdict(set)
    reinforcement_source_ids: set[int] = set()
    for source_id, kind in source_kinds.items():
        if kind != "reinforcement":
            continue
        reinforcement_source_ids.add(source_id)
        application_id = source_to_application.get(source_id)
        if application_id is not None:
            reinforcement_types[application_id].update(source_types.get(source_id, set()))

    parent_edges = [
        dict(row)
        for row in connection.execute(
            "SELECT reinforcement_army_id, parent_army_id "
            "FROM application_army_reinforcement_parents "
            "ORDER BY reinforcement_army_id, parent_army_id"
        )
    ]
    checked_contexts = 0
    blocked: list[dict[str, Any]] = []
    for edge in parent_edges:
        reinforcement_id = edge["reinforcement_army_id"]
        parent_id = edge["parent_army_id"]
        parent = application_armies.get(parent_id)
        if parent is None or not parent["playable"]:
            continue
        parent_source_ids = application_sources.get(parent_id, [])
        for fireteam_type in sorted(reinforcement_types.get(reinforcement_id, set())):
            checked_contexts += 1
            source_limits = [
                {
                    "sourceArmyId": source_id,
                    "limit": source_specs.get(source_id, {}).get(fireteam_type),
                }
                for source_id in parent_source_ids
            ]
            allowed = any(
                item["limit"] is not None and item["limit"] != 0 for item in source_limits
            )
            if not allowed:
                blocked.append(
                    {
                        "reinforcementArmyId": reinforcement_id,
                        "parentArmyId": parent_id,
                        "parentArmyName": parent["name"],
                        "fireteamType": fireteam_type,
                        "parentSourceLimits": source_limits,
                    }
                )

    return {
        "sourceReinforcementSectionCount": len(reinforcement_source_ids),
        "applicationReinforcementSectionCount": len(reinforcement_types),
        "parentEdgeCount": len(parent_edges),
        "playableParentTypeContextCount": checked_contexts,
        "blockedByParentTypeLimitCount": len(blocked),
        "blockedByParentTypeLimit": blocked,
        "policy": (
            "Retain Reinforcement-section member eligibility separately from the selected "
            "ordinary parent Army's permitted Fireteam types/counts. Do not combine Main- and "
            "Reinforcement-section member pools merely because they share an application Army."
        ),
    }


def audit_database(path: Path) -> dict[str, Any]:
    """Return deterministic Fireteam semantic evidence for a normalized database."""
    path = path.resolve()
    if not path.is_file():
        raise FireteamSemanticsAuditError(f"Database does not exist: {path}")

    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only = ON")
        _validate_schema(connection)
        metadata = _snapshot_metadata(connection)
        return {
            "format": REPORT_FORMAT,
            "formatVersion": REPORT_FORMAT_VERSION,
            "database": {
                "sha256": _sha256_file(path),
                "schemaVersion": connection.execute("PRAGMA user_version").fetchone()[0],
                "snapshotArchiveSha256": metadata.get("snapshotArchiveSha256"),
                "snapshotDownloadedOn": metadata.get("snapshotDownloadedOn"),
            },
            "chartShape": _chart_shape(connection),
            "typeLimits": _type_limits(connection),
            "memberResolution": _member_resolution(connection),
            "requiredChoiceSets": _required_choice_evidence(connection),
            "wildcards": _wildcard_evidence(connection),
            "levelEquivalence": _level_equivalence_evidence(connection),
            "ruleBearingNotes": _rule_bearing_notes(connection),
            "ftoEligibility": _fto_evidence(connection),
            "memberIdentityGranularity": _unit_granularity_evidence(connection),
            "reinforcementContext": _reinforcement_context(connection),
        }
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path, help="Frontend infinity.db to audit")
    parser.add_argument("--output", type=Path, help="Optional deterministic JSON report path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = audit_database(args.database)
    except (OSError, sqlite3.Error, FireteamSemanticsAuditError) as exc:
        print(f"ERROR: {exc}")
        return 1

    chart = report["chartShape"]
    members = report["memberResolution"]
    fto = report["ftoEligibility"]
    reinforcement = report["reinforcementContext"]
    print("InfinityDB Fireteam semantics audit")
    print(
        f"Charts: {chart['sourceArmyCount']} source armies | {chart['teamCount']} teams | "
        f"{chart['memberCount']} member rows"
    )
    print(
        "Member resolution: "
        f"{members['resolutionCounts'].get('army', 0)} Army-local | "
        f"{members['nonArmyResolutionCount']} non-local/unresolved"
    )
    print(
        "FTO: "
        f"{fto['statusCounts'].get('resolved', 0)}/{fto['memberRowCount']} rows resolved to "
        f"Army-local loadout options | {fto['unresolvedCount']} source anomalies"
    )
    print(
        "Reinforcement context: "
        f"{reinforcement['parentEdgeCount']} parent links | "
        f"{reinforcement['blockedByParentTypeLimitCount']} parent/type combinations blocked"
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
