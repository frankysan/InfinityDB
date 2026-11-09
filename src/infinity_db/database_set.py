"""Shared validation of the built runtime set during the SQLite-only migration.

The tracked v10 set includes two JSON publications; v11 embeds variant usage
and v12 also embeds Weapon citations; v13 embeds the Restrictions chart;
v14 embeds reviewed Trait Wiki references.
This module never selects a fallback
set, rebuilds inputs, or establishes working-tree curation freshness.
"""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from .build_provenance import validate_set_provenance
from .database.repository import Database
from .rules_database import RulesDatabase
from .variant_usage_reference import load_runtime_variant_usage
from .weapon_profile_publication import load_weapon_profile_publication

V10_RUNTIME_FILES = frozenset({
    "infinity.db", "rules.db", "variant-usage.json", "weapon-profile-sources.json",
})
EMBEDDED_VARIANT_RUNTIME_FILES = V10_RUNTIME_FILES - {"variant-usage.json"}
EMBEDDED_WEAPON_RUNTIME_FILES = frozenset({"infinity.db", "rules.db"})


def _full_integrity_check(path: Path) -> None:
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
        if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError(f"Database integrity check failed: {path.name}")
        if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise ValueError(f"Database contains broken foreign keys: {path.name}")


def validate_database_set(directory: Path) -> dict[str, Any]:
    """Validate exactly the selected supported runtime artifacts without writing files.

    Other build outputs in the directory are ignored, never selected as data
    or used to recover a missing publication. The raw archive, source curation
    and graphical publication are outside this built-runtime validation scope.
    """
    directory = Path(directory).resolve()
    if not directory.is_dir():
        raise ValueError(f"Database-set directory does not exist: {directory}")
    missing = sorted(
        name for name in EMBEDDED_WEAPON_RUNTIME_FILES if not (directory / name).is_file()
    )
    if missing:
        raise ValueError(f"Incomplete database set; missing: {', '.join(missing)}")

    army_path, rules_path = directory / "infinity.db", directory / "rules.db"
    with closing(sqlite3.connect(rules_path.as_uri() + "?mode=ro", uri=True)) as connection:
        schema_version = connection.execute("PRAGMA user_version").fetchone()[0]
    if schema_version not in {10, 11, 12, 13, 14}:
        raise ValueError("Unsupported Rules schema for selected database set")
    names = (
        V10_RUNTIME_FILES if schema_version == 10 else
        EMBEDDED_VARIANT_RUNTIME_FILES if schema_version == 11 else
        EMBEDDED_WEAPON_RUNTIME_FILES
    )
    missing = sorted(name for name in names if not (directory / name).is_file())
    if missing:
        raise ValueError(f"Incomplete database set; missing: {', '.join(missing)}")
    Database(army_path).validate()
    rules = RulesDatabase(rules_path)
    rules.validate()
    provenance = validate_set_provenance(army_path, rules_path)
    for path in (army_path, rules_path):
        _full_integrity_check(path)

    objects = rules.deployed_objects_payload(army_path)
    if objects is None or not objects["objects"]:
        raise ValueError("Database set lacks source-matched embedded deployed objects")
    variants, _ = load_runtime_variant_usage(army_path, rules_path)
    if variants is None or not variants["variants"] or variants["formatVersion"] != 2:
        raise ValueError("Database set lacks a source-matched v2 variant publication")
    weapons = (
        rules.weapon_profile_citations_payload(army_path)
        if schema_version in {12, 13, 14} else
        load_weapon_profile_publication(
            directory / "weapon-profile-sources.json", army_path, rules_path,
        )
    )
    if not weapons:
        raise ValueError("Database set lacks source-matched Weapon profile citations")
    chart = rules.restriction_chart_payload() if schema_version >= 13 else None
    if schema_version >= 13 and (chart is None or len(chart["rows"]) != 6):
        raise ValueError("Database set lacks a complete embedded Restrictions chart")

    trait_links = rules.trait_wiki_links_payload() if schema_version == 14 else None
    if schema_version == 14 and not trait_links:
        raise ValueError("Database set lacks complete embedded Trait Wiki links")

    fingerprints = {}
    for name in sorted(names):
        with (directory / name).open("rb") as stream:
            fingerprints[name] = hashlib.file_digest(stream, "sha256").hexdigest()
    return {
        "layout": {
            10: "v10-four-file", 11: "v11-three-file",
            12: "v12-two-file", 13: "v13-two-file", 14: "v14-two-file",
        }[schema_version],
        "integrityCheck": "full",
        "buildProvenance": provenance,
        "schemaVersion": schema_version,
        "deployedObjects": len(objects["objects"]),
        "unresolvedDeliveries": len(objects["unresolvedDeliveries"]),
        "variantGroups": len(variants["variants"]),
        "variantPublicationVersion": variants["formatVersion"],
        "reviewedWeapons": len({key[0] for key in weapons}),
        **({"restrictionChartRows": len(chart["rows"])} if chart is not None else {}),
        **({"traitWikiLinks": len(trait_links)} if trait_links is not None else {}),
        "sha256": fingerprints,
    }


def database_set_health_report(directory: Path) -> dict[str, Any]:
    """Report selected-set health, including failures, for the existing health CLI."""
    report: dict[str, Any] = {
        "format": "InfinityDB database-set health",
        "formatVersion": 1,
        "directory": str(Path(directory).resolve()),
        "status": "unhealthy",
        "sourcePolicyFreshness": "not-checked",
        "graphicalAssets": "not-checked",
    }
    try:
        report.update(validate_database_set(directory))
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError) as exc:
        report["error"] = str(exc)
    else:
        report["status"] = "healthy"
    return report
