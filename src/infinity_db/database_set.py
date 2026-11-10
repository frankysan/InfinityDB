"""Shared validation of the built runtime set during the SQLite-only migration.

The tracked v10 set includes two JSON publications; v11 embeds variant usage
and v12 also embeds Weapon citations; v13 embeds the Restrictions chart;
v14 embeds reviewed Trait Wiki references; v15 embeds reviewed Combined
Saving Roll annotations; v16 embeds reviewed Ammunition links; v17 embeds
exact authored Weapon Property definitions and source profiles.
This module never selects a fallback
set, rebuilds inputs, or establishes working-tree curation freshness.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from collections.abc import Mapping
from contextlib import closing
from pathlib import Path
from typing import Any

from .army_reference_storage import ARMY_SCHEMA_VERSION as ARMY_REFERENCE_SCHEMA_VERSION
from .build_provenance import validate_set_provenance
from .database.repository import Database
from .rules_database import RulesDatabase
from .symbol_path_storage import ARMY_SCHEMA_VERSION as COMPLETE_ARMY_SCHEMA_VERSION
from .unit_filter_storage import ARMY_SCHEMA_VERSION as UNIT_FILTER_SCHEMA_VERSION
from .variant_usage_reference import load_runtime_variant_usage
from .weapon_profile_publication import load_weapon_profile_publication
from .weapon_property_storage import SCHEMA_VERSION as COMPLETE_RULES_SCHEMA_VERSION

ARMY_DATABASE_FILENAME = "army.db"
RULES_DATABASE_FILENAME = "rules_n5.db"
DEFAULT_DATABASE_DIRECTORY = Path("data/generated")


def select_database_directory(
    directory: Path | None = None, *, required_environment: bool = False,
    environment: Mapping[str, str] | None = None,
) -> Path:
    """Resolve one operator-selected set without filename or environment aliases."""
    settings = os.environ if environment is None else environment
    retired = ("INFINITY_DB_DATABASE", "INFINITY_DB_RULES_DATABASE")
    if any(settings.get(name) for name in retired):
        raise ValueError(
            "Individual database environment settings are retired; use INFINITY_DB_DB_DIR"
        )
    value = settings.get("INFINITY_DB_DB_DIR")
    if directory is not None:
        return Path(directory).resolve()
    if value:
        return Path(value).resolve()
    if required_environment:
        raise ValueError("INFINITY_DB_DB_DIR must name the complete database directory")
    return DEFAULT_DATABASE_DIRECTORY.resolve()

V10_RUNTIME_FILES = frozenset({
    ARMY_DATABASE_FILENAME, RULES_DATABASE_FILENAME,
    "variant-usage.json", "weapon-profile-sources.json",
})
EMBEDDED_VARIANT_RUNTIME_FILES = V10_RUNTIME_FILES - {"variant-usage.json"}
EMBEDDED_WEAPON_RUNTIME_FILES = frozenset({ARMY_DATABASE_FILENAME, RULES_DATABASE_FILENAME})


def _full_integrity_check(path: Path) -> None:
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
        if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError(f"Database integrity check failed: {path.name}")
        if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise ValueError(f"Database contains broken foreign keys: {path.name}")


def validate_database_set(directory: Path, *, require_complete: bool = False) -> dict[str, Any]:
    """Validate exactly the selected supported runtime artifacts without writing files.

    Other build outputs in the directory are ignored, never selected as data
    or used to recover a missing publication. The raw archive, source curation
    and graphical publication are outside this built-runtime validation scope.
    Complete mode requires all current embedded projections and recorded shared
    build provenance, without consulting transitional JSON publications.
    """
    directory = Path(directory).resolve()
    if not directory.is_dir():
        raise ValueError(f"Database-set directory does not exist: {directory}")
    missing = sorted(
        name for name in EMBEDDED_WEAPON_RUNTIME_FILES if not (directory / name).is_file()
    )
    if missing:
        raise ValueError(f"Incomplete database set; missing: {', '.join(missing)}")

    army_path = directory / ARMY_DATABASE_FILENAME
    rules_path = directory / RULES_DATABASE_FILENAME
    with closing(sqlite3.connect(rules_path.as_uri() + "?mode=ro", uri=True)) as connection:
        schema_version = connection.execute("PRAGMA user_version").fetchone()[0]
    if schema_version not in {10, 11, 12, 13, 14, 15, 16, 17}:
        raise ValueError("Unsupported Rules schema for selected database set")
    if require_complete and schema_version != COMPLETE_RULES_SCHEMA_VERSION:
        raise ValueError(
            f"Complete embedded sets require Rules schema v{COMPLETE_RULES_SCHEMA_VERSION}"
        )
    with closing(sqlite3.connect(army_path.as_uri() + "?mode=ro", uri=True)) as connection:
        army_version = connection.execute("PRAGMA user_version").fetchone()[0]
    if require_complete and army_version != COMPLETE_ARMY_SCHEMA_VERSION:
        raise ValueError(
            f"Complete embedded sets require Army schema v{COMPLETE_ARMY_SCHEMA_VERSION}"
        )
    names = (
        V10_RUNTIME_FILES if schema_version == 10 else
        EMBEDDED_VARIANT_RUNTIME_FILES if schema_version == 11 else
        EMBEDDED_WEAPON_RUNTIME_FILES
    )
    missing = sorted(name for name in names if not (directory / name).is_file())
    if missing:
        raise ValueError(f"Incomplete database set; missing: {', '.join(missing)}")
    army = Database(army_path)
    army.validate()
    encodings = army.equipment_presentation_encodings()
    classifications = army.skill_source_classifications()
    symbols = army.symbol_publication()
    filter_semantics = (
        army.unit_filter_semantics() if army_version >= UNIT_FILTER_SCHEMA_VERSION else None
    )
    army_reference = (
        army.army_reference_data() if army_version >= ARMY_REFERENCE_SCHEMA_VERSION else None
    )
    rules = RulesDatabase(rules_path)
    rules.validate()
    provenance = validate_set_provenance(army_path, rules_path)
    if require_complete and provenance["status"] != "matched":
        raise ValueError("Complete embedded sets require recorded matched build provenance")
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
        if schema_version in {12, 13, 14, 15, 16, 17} else
        load_weapon_profile_publication(
            directory / "weapon-profile-sources.json", army_path, rules_path,
        )
    )
    if not weapons:
        raise ValueError("Database set lacks source-matched Weapon profile citations")
    chart = rules.restriction_chart_payload() if schema_version >= 13 else None
    if schema_version >= 13 and (chart is None or len(chart["rows"]) != 6):
        raise ValueError("Database set lacks a complete embedded Restrictions chart")

    trait_links = rules.trait_wiki_links_payload() if schema_version >= 14 else None
    if schema_version >= 14 and not trait_links:
        raise ValueError("Database set lacks complete embedded Trait Wiki links")

    saving_rolls = (
        rules.combined_saving_rolls_payload(army_path)
        if schema_version >= 15 else None
    )
    if schema_version >= 15 and (saving_rolls is None or len(saving_rolls) != 6):
        raise ValueError("Database set lacks exact reviewed Combined Saving Roll profiles")

    ammunition = rules.ammunition_references_payload(army_path) if schema_version >= 16 else None
    if schema_version >= 16 and (ammunition is None or len(ammunition) != 16):
        raise ValueError("Database set lacks complete reviewed Ammunition links")

    properties = rules.weapon_properties_payload(army_path) if schema_version >= 17 else None
    if schema_version >= 17 and (properties is None or len(properties) != 12):
        raise ValueError("Database set lacks source-matched Weapon Properties")

    fingerprints = {}
    for name in sorted(names):
        with (directory / name).open("rb") as stream:
            fingerprints[name] = hashlib.file_digest(stream, "sha256").hexdigest()
    return {
        "layout": {
            10: "v10-four-file", 11: "v11-three-file",
            12: "v12-two-file", 13: "v13-two-file",
            14: "v14-two-file", 15: "v15-two-file",
            16: "v16-two-file", 17: "v17-two-file",
        }[schema_version],
        "integrityCheck": "full",
        "buildProvenance": provenance,
        "schemaVersion": schema_version,
        "deployedObjects": len(objects["objects"]),
        "unresolvedDeliveries": len(objects["unresolvedDeliveries"]),
        "variantGroups": len(variants["variants"]),
        **({"equipmentPresentationEncodings": len(encodings)} if encodings is not None else {}),
        **({"skillSourceClassifications": len(classifications)}
           if classifications is not None else {}),
        "variantPublicationVersion": variants["formatVersion"],
        "reviewedWeapons": len({key[0] for key in weapons}),
        **({"restrictionChartRows": len(chart["rows"])} if chart is not None else {}),
        **({"traitWikiLinks": len(trait_links)} if trait_links is not None else {}),
        **({"combinedSavingRollProfiles": len(saving_rolls)} if saving_rolls is not None else {}),
        **({"ammunitionReferences": len(ammunition)} if ammunition is not None else {}),
        **({"weaponProperties": len(properties)} if properties is not None else {}),
        "sha256": fingerprints,
        **({
            "publishedSymbolMappings": sum(len(symbols[field]) for field in (
                "factionIdToPublishedPath", "unitSlugToPublishedPath",
                "unitProfileLogoToPublishedPath", "profileIdentityToPublishedPath",
            )),
            "publishedSymbolAssets": len(symbols["publishedSha256ByPath"]),
        } if symbols is not None else {}),
        **({
            "armyOverviewSummaries": len(army_reference[0]),
            "legacyArmyIdentities": len(army_reference[1]),
        } if army_reference is not None else {}),
        **({
            "hiddenUnitCharacteristics": len(filter_semantics.hidden_characteristics),
            "sourceClassificationMemberships": len(filter_semantics.classification_memberships),
        } if filter_semantics is not None else {}),
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
        report.update(validate_database_set(directory, require_complete=True))
    except (OSError, sqlite3.Error, ValueError, KeyError, TypeError) as exc:
        report["error"] = str(exc)
    else:
        report["status"] = "healthy"
    return report
