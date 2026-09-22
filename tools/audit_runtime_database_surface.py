"""Audit the Army-database fields consumed by normal application runtime paths."""

from __future__ import annotations

import argparse
import ast
import json
import sqlite3
from collections import defaultdict
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from infinity_db.database.repository import Database, unit_sort_key

FORMAT = "InfinityDB runtime database surface audit"
FORMAT_VERSION = 1

CANONICAL = "canonical_application"
CONTEXTUAL = "contextual_application"
SOURCE = "intentional_source_representation"
NO_ISSUE = "none"
REPLACEABLE = "replaceable_duplicate"
OVERLAP = "semantic_overlap"


class RuntimeSurfaceAuditError(ValueError):
    """Raised when runtime coverage or its maintained semantic policy is stale."""


def _policy(
    role: str,
    *,
    issue: str = NO_ISSUE,
    reason: str,
    fields: Mapping[str, tuple[str, str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "role": role,
        "issue": issue,
        "reason": reason,
        "fields": dict(fields or {}),
    }


# This policy describes only tables observed on normal repository/API/web serving
# paths. Validation/build-only tables deliberately do not belong here.
TABLE_POLICY: dict[str, dict[str, Any]] = {}


def _register(
    names: Sequence[str],
    role: str,
    *,
    issue: str = NO_ISSUE,
    reason: str,
) -> None:
    for name in names:
        TABLE_POLICY[name] = _policy(role, issue=issue, reason=reason)


_register(
    ["__infinity_metadata"],
    CANONICAL,
    reason="Build-pinned operational metadata used for snapshot and identity policy.",
)
_register(
    [
        "profile_payloads",
        "profile_payload_characteristics",
        "profile_payload_skills",
        "profile_payload_skill_extras",
        "profile_payload_equipment",
        "profile_payload_equipment_extras",
        "profile_payload_weapons",
        "profile_payload_weapon_extras",
        "loadout_payloads",
        "loadout_payload_orders",
        "loadout_payload_skills",
        "loadout_payload_skill_extras",
        "loadout_payload_equipment",
        "loadout_payload_equipment_extras",
        "loadout_payload_weapons",
        "loadout_payload_weapon_extras",
        "categories",
        "characteristics",
        "troop_types",
        "extras",
    ],
    CANONICAL,
    reason="Current application identity/payload or unambiguous lookup catalog.",
)
_register(
    [
        "application_armies",
        "application_army_reinforcement_parents",
        "application_catalog_items",
        "application_domain_slugs",
    ],
    CANONICAL,
    reason=(
        "Materialized InfinityDB application identity/hierarchy or catalog identity "
        "used by normal serving."
    ),
)
_register(
    ["application_army_sources", "application_catalog_sources"],
    CONTEXTUAL,
    reason=(
        "Reviewed source-to-application Army provenance mapping used to reconcile "
        "source occurrences without erasing source IDs."
    ),
)
_register(
    ["application_peripheral_entities", "application_peripheral_profiles"],
    CANONICAL,
    reason=(
        "Reviewed canonical Peripheral application identity used by normal Unit-detail "
        "serving."
    ),
)
_register(
    [
        "application_peripheral_sources",
        "application_peripheral_unit_sources",
        "application_peripheral_controller_access",
        "application_peripheral_controller_targets",
        "profile_peripherals",
        "option_peripherals",
    ],
    CONTEXTUAL,
    reason=(
        "Reviewed or source-context Peripheral relationships preserve exact Army/profile/"
        "loadout occurrence context while resolving canonical application targets."
    ),
)
_register(
    [
        "application_unit_constraints",
        "application_unit_constraint_members",
    ],
    CONTEXTUAL,
    reason=(
        "Materialized selector-free Army selection constraints preserve exact source member "
        "context while resolving every eligible member to canonical logical-Unit identity."
    ),
)
_register(
    [
        "application_unit_group_dependency_constraints",
        "application_unit_group_dependency_members",
        "application_unit_group_dependency_targets",
    ],
    CONTEXTUAL,
    reason=(
        "Materialized same-logical Army profile-group dependencies preserve exact Army/Unit/"
        "group coordinates while resolving source Unit endpoints to canonical logical identity."
    ),
)
_register(
    ["logical_units"],
    CANONICAL,
    reason="Representative-backed logical-unit application values.",
)
TABLE_POLICY["logical_units"]["fields"].update(
    {
        "canonical_faction_id": (
            CONTEXTUAL,
            NO_ISSUE,
            "Compatibility copy of representative source-origin context; not a game-wide "
            "logical-unit ownership or membership fact.",
        ),
        "main_army_id": (
            CONTEXTUAL,
            NO_ISSUE,
            "Compatibility copy of representative source-derived grouping context; not "
            "logical-unit ownership or availability.",
        ),
        "display_army_id": (
            CONTEXTUAL,
            NO_ISSUE,
            "Compatibility copy of a representative presentation identity with no independent "
            "domain semantics.",
        ),
    }
)

_register(
    [
        "logical_unit_sources",
        "logical_unit_aliases",
        "logical_unit_notes",
        "profile_payload_occurrences",
        "loadout_payload_occurrences",
        "profile_groups",
        "army_units",
        "metadata_ammunitions",
    ],
    CONTEXTUAL,
    reason="Explicit occurrence, relationship, presentation, or metadata context.",
)
_register(
    ["unit_factions"],
    CONTEXTUAL,
    reason=(
        "Source-declared faction memberships are preserved as a broader game-wide "
        "relationship distinct from concrete Army-list availability."
    ),
)

_register(
    [
        "unit_options",
        "unit_option_skills",
        "unit_option_skill_extras",
        "unit_option_equipment",
        "unit_option_equipment_extras",
        "unit_option_weapons",
        "unit_option_weapon_extras",
    ],
    SOURCE,
    reason=(
        "Top-level unit-option data is intentionally source-contextual until its own "
        "semantic audit establishes reusable identity."
    ),
)
_register(
    [
        "profiles",
        "loadout_options",
        "profile_skills",
        "profile_skill_extras",
        "profile_equipment",
        "profile_equipment_extras",
        "profile_weapons",
        "profile_weapon_extras",
        "option_skills",
        "option_skill_extras",
        "option_equipment",
        "option_equipment_extras",
        "option_weapons",
        "option_weapon_templates",
        "option_weapon_extras",
    ],
    SOURCE,
    issue=REPLACEABLE,
    reason=(
        "Runtime still reads a lossless source copy of meaning already materialized in "
        "the canonical profile/loadout layer."
    ),
)
_register(
    ["army_lists"],
    SOURCE,
    reason=(
        "Normal serving retains only the legacy source-list shape needed for the "
        "compatibility `kind` field and reinforcement fallback; canonical Army identity "
        "and hierarchy come from application_armies."
    ),
)
_register(
    ["metadata_factions"],
    CONTEXTUAL,
    issue=OVERLAP,
    reason=(
        "Faction hierarchy metadata overlaps application army/list identity and requires "
        "one explicit semantic boundary."
    ),
)
_register(
    ["skills", "equipment", "weapons"],
    CANONICAL,
    reason=(
        "Source catalog references back the canonical payload occurrences and unit-detail "
        "labels; player-facing catalog identity is materialized separately."
    ),
)
_register(
    ["metadata_skills", "metadata_equipment", "metadata_weapons"],
    CONTEXTUAL,
    reason=(
        "Source metadata enriches or profiles catalog items without defining the materialized "
        "application catalog identity."
    ),
)
TABLE_POLICY["units"] = _policy(
    SOURCE,
    reason="Source-unit identity remains a provenance/context bridge for live relationships.",
    fields={
        "canonical_faction_id": (
            CONTEXTUAL,
            NO_ISSUE,
            "Source-specific faction context used by availability/visibility semantics.",
        ),
        "name": (
            SOURCE,
            REPLACEABLE,
            "Catalog reverse lookup still reads a source name already represented by "
            "logical-unit identity/aliases.",
        ),
    },
)

# Database methods called directly by the web layer or the player-facing catalog
# helpers. validate() is intentionally excluded from the audited serving surface.
EXCLUDED_DIRECT_METHODS = {"validate"}
PROBED_DIRECT_METHODS = {
    "application_catalog_id",
    "application_domain_id",
    "application_slug",
    "snapshot_downloaded_on",
    "list_armies",
    "list_skill_extras",
    "list_catalog_items",
    "get_catalog_item",
    "skill_source_ids",
    "get_skill",
    "trait_usage_index",
    "list_traits",
    "get_trait",
    "list_units",
    "visible_unit_ids",
    "get_unit",
}
RUNTIME_MODULES = (
    "src/infinity_db/web/app.py",
    "src/infinity_db/army_slugs.py",
    "src/infinity_db/catalog_slugs.py",
    "src/infinity_db/domain_references.py",
    "src/infinity_db/unit_slugs.py",
    "src/infinity_db/skill_catalog.py",
    "src/infinity_db/trait_catalog.py",
)


def _database_calls(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    calls: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        owner = node.func.value
        if isinstance(owner, ast.Attribute) and owner.attr == "database":
            calls.add(node.func.attr)
        elif isinstance(owner, ast.Name) and owner.id == "database":
            calls.add(node.func.attr)
    return calls


def discover_runtime_database_methods(project_root: Path) -> set[str]:
    calls: set[str] = set()
    for relative in RUNTIME_MODULES:
        path = project_root / relative
        if not path.is_file():
            raise RuntimeSurfaceAuditError(f"Runtime module is missing: {relative}")
        calls.update(_database_calls(path))
    return calls


class _TracingDatabase(Database):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.reads: set[tuple[str, str]] = set()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        if not self.path.is_file():
            raise ValueError(f"Database does not exist: {self.path}. Build it before serving.")
        connection = sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.create_function("casefold", 1, lambda value: (value or "").casefold())
        connection.create_function("unit_sort_key", 1, unit_sort_key)

        def authorize(
            action: int,
            table: str | None,
            column: str | None,
            _database: str | None,
            _trigger: str | None,
        ) -> int:
            if action == sqlite3.SQLITE_READ and table and column:
                self.reads.add((table, column))
            return sqlite3.SQLITE_OK

        connection.set_authorizer(authorize)
        try:
            connection.execute("BEGIN")
            yield connection
        finally:
            connection.close()


def _run_probe(path: Path, action: Callable[[Database], object]) -> set[tuple[str, str]]:
    database = _TracingDatabase(path)
    action(database)
    return database.reads


def _first(items: Sequence[Mapping[str, Any]], label: str) -> Mapping[str, Any]:
    if not items:
        raise RuntimeSurfaceAuditError(f"Production runtime audit needs at least one {label}")
    return items[0]


def _probe_actions(path: Path) -> list[tuple[str, Callable[[Database], object]]]:
    preparation = Database(path)
    armies = preparation.list_armies()
    skills = preparation.list_catalog_items("skills")
    equipment = preparation.list_catalog_items("equipment")
    weapons = preparation.list_catalog_items("weapons")
    traits = preparation.list_traits()
    visible_ids = preparation.visible_unit_ids(
        mercs=True,
        specops=True,
        teamops=True,
        reinforcement=True,
    )
    playable = next((item for item in armies if item.get("playable")), None)
    if playable is None:
        raise RuntimeSurfaceAuditError("Runtime audit needs at least one playable army")
    skill = _first(skills, "skill")
    skill_slug = preparation.application_slug("skills", int(skill["id"]))
    if skill_slug is None:
        raise RuntimeSurfaceAuditError("Runtime audit needs at least one resolved Skill slug")
    equipment_item = _first(equipment, "equipment item")
    weapon = _first(weapons, "weapon")
    trait = _first(traits, "weapon trait")
    if not visible_ids:
        raise RuntimeSurfaceAuditError("Runtime audit needs at least one visible unit")
    unit_id = visible_ids[0]

    return [
        ("snapshot-metadata", lambda db: db.snapshot_downloaded_on()),
        ("armies", lambda db: db.list_armies()),
        ("unit-application-id", lambda db: db.application_domain_id("units", unit_id)),
        ("skill-extras", lambda db: db.list_skill_extras()),
        ("skills-list", lambda db: db.list_catalog_items("skills")),
        (
            "skill-application-id",
            lambda db: db.application_catalog_id("skills", int(skill["id"])),
        ),
        (
            "skill-slug-for-id",
            lambda db: db.application_slug("skills", int(skill["id"])),
        ),
        (
            "skill-id-for-slug",
            lambda db: db.application_id_for_slug("skills", skill_slug),
        ),
        ("equipment-list", lambda db: db.list_catalog_items("equipment")),
        ("weapons-list", lambda db: db.list_catalog_items("weapons")),
        ("skill-detail", lambda db: db.get_skill(int(skill["id"]))),
        ("skill-source-ids", lambda db: db.skill_source_ids(int(skill["id"]))),
        (
            "equipment-detail",
            lambda db: db.get_catalog_item("equipment", int(equipment_item["id"])),
        ),
        ("weapon-detail", lambda db: db.get_catalog_item("weapons", int(weapon["id"]))),
        ("traits-list", lambda db: db.list_traits()),
        ("trait-detail", lambda db: db.get_trait(str(trait["id"]))),
        ("traits-usage", lambda db: db.trait_usage_index()),
        ("units-list", lambda db: db.list_units(limit=500)),
        ("units-search", lambda db: db.list_units(search="unit", limit=500)),
        ("units-army", lambda db: db.list_units(army_id=int(playable["id"]), limit=500)),
        ("units-mercs", lambda db: db.list_units(mercs=True, limit=500)),
        ("units-specops", lambda db: db.list_units(specops=True, limit=500)),
        ("units-teamops", lambda db: db.list_units(teamops=True, limit=500)),
        (
            "units-reinforcement",
            lambda db: db.list_units(reinforcement=True, limit=500),
        ),
        (
            "units-skill-filter",
            lambda db: db.list_units(skill_id=int(skill["id"]), limit=500),
        ),
        (
            "units-equipment-filter",
            lambda db: db.list_units(equipment_id=int(equipment_item["id"]), limit=500),
        ),
        (
            "units-weapon-filter",
            lambda db: db.list_units(weapon_id=int(weapon["id"]), limit=500),
        ),
        ("unit-detail", lambda db: db.get_unit(unit_id)),
        (
            "visible-unit-ids",
            lambda db: db.visible_unit_ids(
                mercs=True,
                specops=True,
                teamops=True,
                reinforcement=True,
            ),
        ),
    ]


def _row_counts(path: Path, tables: Sequence[str]) -> dict[str, int]:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        return {
            table: int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
            for table in tables
        }
    finally:
        connection.close()


def _field_policy(table: str, field: str) -> tuple[str, str, str]:
    policy = TABLE_POLICY[table]
    override = policy["fields"].get(field)
    if override is not None:
        return override
    return policy["role"], policy["issue"], policy["reason"]


def _classified_inventory(
    aggregate: Mapping[str, set[str]],
    row_counts: Mapping[str, int],
    surfaces_by_table: Mapping[str, set[str]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    unknown = sorted(set(aggregate) - set(TABLE_POLICY))
    if unknown:
        raise RuntimeSurfaceAuditError(
            "Runtime database surface has unclassified table(s): " + ", ".join(unknown)
        )

    summary: defaultdict[str, int] = defaultdict(int)
    inventory: list[dict[str, Any]] = []
    for table in sorted(aggregate):
        fields = []
        table_issues: set[str] = set()
        table_roles: set[str] = set()
        for field in sorted(aggregate[table]):
            role, issue, reason = _field_policy(table, field)
            fields.append({"name": field, "role": role, "issue": issue, "reason": reason})
            table_roles.add(role)
            if issue != NO_ISSUE:
                table_issues.add(issue)
            summary[f"role:{role}:fieldCount"] += 1
            summary[f"issue:{issue}:fieldCount"] += 1
        if table_issues:
            summary["tableWithOpenIssueCount"] += 1
        inventory.append(
            {
                "table": table,
                "rowCount": row_counts[table],
                "surfaces": sorted(surfaces_by_table.get(table, set())),
                "roles": sorted(table_roles),
                "issues": sorted(table_issues),
                "fields": fields,
            }
        )
    return inventory, dict(sorted(summary.items()))


def audit_database(path: Path, *, project_root: Path) -> dict[str, Any]:
    path = path.resolve()
    project_root = project_root.resolve()
    Database(path).validate()

    discovered = discover_runtime_database_methods(project_root)
    unexpected = sorted(discovered - PROBED_DIRECT_METHODS - EXCLUDED_DIRECT_METHODS)
    missing = sorted(PROBED_DIRECT_METHODS - discovered)
    if unexpected or missing:
        details = []
        if unexpected:
            details.append("unprobed direct method(s): " + ", ".join(unexpected))
        if missing:
            details.append("probe method(s) no longer used: " + ", ".join(missing))
        raise RuntimeSurfaceAuditError(
            "Runtime method coverage is stale (" + "; ".join(details) + ")"
        )

    surface_reads: dict[str, set[tuple[str, str]]] = {}
    aggregate: defaultdict[str, set[str]] = defaultdict(set)
    surfaces_by_table: defaultdict[str, set[str]] = defaultdict(set)
    for surface, action in _probe_actions(path):
        reads = _run_probe(path, action)
        surface_reads[surface] = reads
        for table, column in reads:
            aggregate[table].add(column)
            surfaces_by_table[table].add(surface)

    counts = _row_counts(path, sorted(aggregate))
    inventory, classification_summary = _classified_inventory(
        aggregate, counts, surfaces_by_table
    )
    open_tables = [item["table"] for item in inventory if item["issues"]]
    replaceable_tables = [
        item["table"] for item in inventory if REPLACEABLE in item["issues"]
    ]
    overlap_tables = [item["table"] for item in inventory if OVERLAP in item["issues"]]

    surfaces = {
        name: {
            table: sorted(column for read_table, column in reads if read_table == table)
            for table in sorted({read_table for read_table, _column in reads})
        }
        for name, reads in surface_reads.items()
    }
    runtime_field_count = sum(len(columns) for columns in aggregate.values())
    return {
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
        "database": str(path),
        "policy": {
            "validationExcluded": True,
            "excludedDirectMethods": sorted(EXCLUDED_DIRECT_METHODS),
            "discoveredDirectMethods": sorted(discovered),
            "probedDirectMethods": sorted(PROBED_DIRECT_METHODS),
        },
        "summary": {
            "surfaceCount": len(surface_reads),
            "runtimeTableCount": len(aggregate),
            "runtimeFieldCount": runtime_field_count,
            "tableWithOpenIssueCount": len(open_tables),
            "replaceableSourceTableCount": len(replaceable_tables),
            "semanticOverlapTableCount": len(overlap_tables),
            **classification_summary,
        },
        "openIssues": {
            "replaceableSourceTables": sorted(replaceable_tables),
            "semanticOverlapTables": sorted(overlap_tables),
        },
        "surfaces": surfaces,
        "inventory": inventory,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path, help="Built InfinityDB Army database")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root used to verify runtime method coverage",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = audit_database(args.database, project_root=args.project_root)
    except (OSError, sqlite3.Error, RuntimeSurfaceAuditError, ValueError) as exc:
        print(f"Runtime database surface audit failed: {exc}")
        return 1
    document = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(document, encoding="utf-8")
    else:
        print(document, end="")
    summary = report["summary"]
    print(
        "Runtime surface: "
        f"{summary['surfaceCount']} probes | {summary['runtimeTableCount']} tables | "
        f"{summary['runtimeFieldCount']} fields | "
        f"{summary['tableWithOpenIssueCount']} tables need follow-up"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
