"""Explicit base models and publications for relational storage unit tests."""

from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

from infinity_db.build_provenance import file_sha256
from infinity_db.curated import load_curated_directory
from infinity_db.database.publication import published_content_sha256
from infinity_db.rules_database import RulesDatabase, export_rules_database
from infinity_db.weapon_profile_storage import _read_document

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/generated"


def variant_publication() -> dict:
    result = RulesDatabase(RELEASE / "rules_n5.db").variant_usage_payload(RELEASE / "army.db")
    assert result is not None
    return result


def weapon_publication() -> dict:
    with closing(sqlite3.connect(RELEASE / "rules_n5.db")) as connection:
        document = _read_document(connection)
    document["sourceSnapshot"]["rulesDatabaseSha256"] = file_sha256(RELEASE / "rules_n5.db")
    return document


def rules_build_provenance() -> dict:
    with closing(sqlite3.connect(RELEASE / "rules_n5.db")) as connection:
        return json.loads(connection.execute(
            "SELECT value FROM __rules_metadata WHERE key='database_set_build'"
        ).fetchone()[0])


def copy_base_rules(destination: Path) -> None:
    """Construct the standalone relational base for testing individual projections."""
    export_rules_database(
        load_curated_directory(ROOT / "data/curated/rules"), destination,
        restrictions_manifest=json.loads(
            (ROOT / "config/validation/restrictions-source-chart.json").read_text(encoding="utf-8")
        ),
        deployed_objects=RulesDatabase(RELEASE / "rules_n5.db").deployed_objects_payload(
            RELEASE / "army.db",
        ),
        build_provenance=rules_build_provenance(),
    )


def copy_base_army(destination: Path) -> None:
    """Isolate source/export rows before the five complete-build projections."""
    shutil.copyfile(RELEASE / "army.db", destination)
    with closing(sqlite3.connect(destination)) as connection, connection:
        for table in (
            "equipment_presentation_metadata", "equipment_presentation_encodings",
            "skill_source_classification_metadata", "skill_source_classifications",
            "unit_filter_metadata", "hidden_unit_characteristics",
            "source_classification_memberships", "source_classification_matches",
            "army_reference_metadata", "legacy_army_identities", "army_overview_text",
            "symbol_path_metadata", "published_symbol_assets", "published_symbol_paths",
        ):
            connection.execute(f"DROP TABLE IF EXISTS {table}")
        connection.execute("PRAGMA user_version=26")
        connection.execute(
            "UPDATE __infinity_metadata SET value='35' WHERE key='database_compatibility_version'"
        )
        connection.execute("DELETE FROM __infinity_metadata WHERE key='database_set_build'")
        connection.execute(
            "UPDATE __infinity_metadata SET value=? WHERE key='published_content_sha256'",
            (json.dumps(published_content_sha256(connection)),),
        )
