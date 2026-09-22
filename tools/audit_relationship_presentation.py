#!/usr/bin/env python3
"""Audit confirmed player-relevant relationships that are not yet presented on the web."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

REPORT_FORMAT = "InfinityDB relationship presentation gap audit"
REPORT_FORMAT_VERSION = 1

REQUIRED_TABLES = {
    "__infinity_metadata",
    "profile_occurrence_includes",
    "loadout_occurrence_includes",
    "unit_option_includes",
    "unit_option_include_targets",
    "application_unit_constraints",
    "application_unit_constraint_members",
    "application_unit_group_dependency_constraints",
    "application_unit_group_dependency_members",
    "application_unit_group_dependency_targets",
    "profile_peripherals",
    "option_peripherals",
    "application_peripheral_sources",
    "application_peripheral_unit_sources",
    "application_peripheral_controller_access",
    "application_peripheral_controller_targets",
    "fireteams",
    "fireteam_types",
    "fireteam_members",
    "application_army_reinforcement_parents",
}


class RelationshipPresentationAuditError(ValueError):
    """Raised when the maintained presentation-gap audit cannot be evaluated."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metadata(connection: sqlite3.Connection) -> dict[str, Any]:
    row = connection.execute(
        "SELECT value FROM __infinity_metadata WHERE key = '_meta'"
    ).fetchone()
    if row is None:
        raise RelationshipPresentationAuditError("Database metadata row '_meta' is missing")
    try:
        value = json.loads(row[0])
    except (TypeError, json.JSONDecodeError) as exc:
        raise RelationshipPresentationAuditError(
            "Database metadata row '_meta' is invalid JSON"
        ) from exc
    if not isinstance(value, dict):
        raise RelationshipPresentationAuditError("Database metadata row '_meta' must be an object")
    return value


def _validate_schema(connection: sqlite3.Connection) -> None:
    tables = {
        str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    missing = sorted(REQUIRED_TABLES - tables)
    if missing:
        raise RelationshipPresentationAuditError(
            "Database is missing required table(s): " + ", ".join(missing)
        )


def _count(connection: sqlite3.Connection, table: str) -> int:
    return int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])


def _source_surface(project_root: Path) -> dict[str, str]:
    repository_path = project_root / "src/infinity_db/database/repository.py"
    static_root = project_root / "src/infinity_db/web/static"
    if not repository_path.is_file():
        raise RelationshipPresentationAuditError(
            "Repository source is missing: src/infinity_db/database/repository.py"
        )
    if not static_root.is_dir():
        raise RelationshipPresentationAuditError(
            "Web static source is missing: src/infinity_db/web/static"
        )
    web_sources = []
    for path in sorted(static_root.glob("*.js")):
        web_sources.append(path.read_text(encoding="utf-8"))
    return {
        "repository": repository_path.read_text(encoding="utf-8"),
        "web": "\n".join(web_sources),
    }


def _has_any(source: str, markers: tuple[str, ...]) -> bool:
    return any(marker in source for marker in markers)


def _presentation_status(
    sources: dict[str, str],
    *,
    repository_markers: tuple[str, ...],
    web_markers: tuple[str, ...],
) -> dict[str, Any]:
    repository_exposed = _has_any(sources["repository"], repository_markers)
    web_presented = _has_any(sources["web"], web_markers)
    if web_presented:
        status = "web_presented"
    elif repository_exposed:
        status = "repository_or_api_only"
    else:
        status = "database_only"
    return {
        "status": status,
        "repositoryExposed": repository_exposed,
        "webPresented": web_presented,
    }


def _include_relationships(
    connection: sqlite3.Connection, sources: dict[str, str]
) -> dict[str, Any]:
    return {
        "classification": "confirmed_1_0_presentation_gap",
        **_presentation_status(
            sources,
            repository_markers=(
                "profile_occurrence_includes",
                "loadout_occurrence_includes",
                "unit_option_include_targets",
            ),
            web_markers=(
                "profile_occurrence_includes",
                "loadout_occurrence_includes",
                "unit_option_include_targets",
            ),
        ),
        "profileOccurrenceCount": _count(connection, "profile_occurrence_includes"),
        "loadoutOccurrenceCount": _count(connection, "loadout_occurrence_includes"),
        "unitOptionDefinitionCount": _count(connection, "unit_option_includes"),
        "unitOptionTargetContextCount": _count(connection, "unit_option_include_targets"),
        "reason": (
            "Includes are occurrence-scoped player relationships. Canonical target resolution "
            "exists in the application database, but normal Unit-detail serving does not expose it."
        ),
    }


def _selection_relationships(
    connection: sqlite3.Connection, sources: dict[str, str]
) -> dict[str, Any]:
    return {
        "classification": "confirmed_1_0_presentation_gap",
        **_presentation_status(
            sources,
            repository_markers=("selection_constraints", "group_dependencies"),
            web_markers=("selection_constraints", "group_dependencies"),
        ),
        "constraintCount": _count(connection, "application_unit_constraints"),
        "constraintMemberCount": _count(connection, "application_unit_constraint_members"),
        "groupDependencyConstraintCount": _count(
            connection, "application_unit_group_dependency_constraints"
        ),
        "groupDependencyMemberCount": _count(
            connection, "application_unit_group_dependency_members"
        ),
        "groupDependencyTargetCount": _count(
            connection, "application_unit_group_dependency_targets"
        ),
        "reason": (
            "Canonical Army selection constraints and profile-group dependencies are returned "
            "by Unit detail, but the browser does not render them."
        ),
    }


def _peripheral_relationships(
    connection: sqlite3.Connection, sources: dict[str, str]
) -> dict[str, Any]:
    unit_backed_count = int(
        connection.execute(
            "SELECT COUNT(DISTINCT logical_unit_id) FROM application_peripheral_unit_sources"
        ).fetchone()[0]
    )
    return {
        "classification": "confirmed_1_0_presentation_gap",
        **_presentation_status(
            sources,
            repository_markers=("peripheral_access", "peripheral_type_ids", '"peripherals"'),
            web_markers=("peripheral_access", "peripheral_type_ids", ".peripherals"),
        ),
        "profileAttachmentCount": _count(connection, "profile_peripherals"),
        "loadoutAttachmentCount": _count(connection, "option_peripherals"),
        "canonicalSourceMappingCount": _count(connection, "application_peripheral_sources"),
        "unitBackedLogicalUnitCount": unit_backed_count,
        "controllerAccessCount": _count(connection, "application_peripheral_controller_access"),
        "controllerTargetCount": _count(connection, "application_peripheral_controller_targets"),
        "reason": (
            "Canonical Peripheral attachments, Unit-backed Peripheral type identity, and "
            "Controller access pools are available to Unit detail but are not rendered."
        ),
    }


def _fireteam_relationships(
    connection: sqlite3.Connection, sources: dict[str, str]
) -> dict[str, Any]:
    non_local = int(
        connection.execute(
            "SELECT COUNT(*) FROM fireteam_members "
            "WHERE COALESCE(resolution, '') != 'army'"
        ).fetchone()[0]
    )
    return {
        "classification": "confirmed_1_0_presentation_gap",
        **_presentation_status(
            sources,
            repository_markers=("fireteam_members", "fireteam_types", "fireteams"),
            web_markers=("fireteam_members", "fireteam_types", "fireteams"),
        ),
        "teamCount": _count(connection, "fireteams"),
        "typeMembershipCount": _count(connection, "fireteam_types"),
        "memberCount": _count(connection, "fireteam_members"),
        "nonArmyResolutionCount": non_local,
        "reason": (
            "Fireteam chart membership, type eligibility, cardinality, required-choice context, "
            "and chart notes are player-facing relationships with no repository/browser surface."
        ),
    }


def _reinforcement_parent_relationships(
    connection: sqlite3.Connection, sources: dict[str, str]
) -> dict[str, Any]:
    row = connection.execute(
        "SELECT COUNT(*), COUNT(DISTINCT reinforcement_army_id), "
        "COUNT(DISTINCT parent_army_id) FROM application_army_reinforcement_parents"
    ).fetchone()
    return {
        "classification": "confirmed_1_0_presentation_gap",
        **_presentation_status(
            sources,
            repository_markers=("parent_army_ids",),
            web_markers=("parent_army_ids",),
        ),
        "parentEdgeCount": int(row[0]),
        "reinforcementSectionCount": int(row[1]),
        "parentArmyCount": int(row[2]),
        "reason": (
            "Reinforcement Section parentage is exposed by the Army repository/API, but the "
            "browser does not present which parent Armies a Section belongs to."
        ),
    }


def audit_database(path: Path, *, project_root: Path) -> dict[str, Any]:
    """Return deterministic evidence for confirmed relationship presentation gaps."""
    path = path.resolve()
    project_root = project_root.resolve()
    if not path.is_file():
        raise RelationshipPresentationAuditError(f"Database does not exist: {path}")

    sources = _source_surface(project_root)
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only = ON")
        _validate_schema(connection)
        metadata = _metadata(connection)
        gaps = {
            "includeRelationships": _include_relationships(connection, sources),
            "selectionRelationships": _selection_relationships(connection, sources),
            "peripheralRelationships": _peripheral_relationships(connection, sources),
            "fireteamRelationships": _fireteam_relationships(connection, sources),
            "reinforcementParentRelationships": _reinforcement_parent_relationships(
                connection, sources
            ),
        }
        return {
            "format": REPORT_FORMAT,
            "formatVersion": REPORT_FORMAT_VERSION,
            "database": {
                "sha256": _sha256_file(path),
                "schemaVersion": connection.execute("PRAGMA user_version").fetchone()[0],
                "snapshotArchiveSha256": metadata.get("snapshotArchiveSha256"),
                "snapshotDownloadedOn": metadata.get("snapshotDownloadedOn"),
            },
            "gapFamilyCount": len(gaps),
            "gaps": gaps,
            "excludedFromConfirmedGapCount": {
                "unitFactions": (
                    "Source unit_factions remains a meaningful source relationship, but its "
                    "additional source grouping semantics have not yet been established as a "
                    "distinct web presentation requirement beyond canonical Army availability."
                ),
                "nonRelationshipPayloads": (
                    "Source notes, spectables, and top-level unit_options are completeness "
                    "candidates, but they are payload/context rather than relationship families "
                    "and belong to the broader source-to-presentation inventory."
                ),
            },
        }
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path, help="Frontend infinity.db to audit")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root used to inspect repository/web presentation surfaces",
    )
    parser.add_argument("--output", type=Path, help="Optional deterministic JSON report path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = audit_database(args.database, project_root=args.project_root)
    except (OSError, sqlite3.Error, RelationshipPresentationAuditError) as exc:
        print(f"ERROR: {exc}")
        return 1

    gaps = report["gaps"]
    print(REPORT_FORMAT)
    print(f"Confirmed gap families: {report['gapFamilyCount']}")
    for name, gap in gaps.items():
        print(f"- {name}: {gap['status']}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
