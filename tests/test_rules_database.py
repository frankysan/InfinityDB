import sqlite3
from pathlib import Path

from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import (
    RULES_APPLICATION_ID,
    RULES_SCHEMA_VERSION,
    RulesDatabase,
    export_rules_database,
)


def test_export_rules_database_ignores_example_and_preserves_provenance(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    output = tmp_path / "rules.db"

    export_rules_database(documents, output)

    with sqlite3.connect(output) as connection:
        assert connection.execute("PRAGMA application_id").fetchone()[0] == RULES_APPLICATION_ID
        assert connection.execute("PRAGMA user_version").fetchone()[0] == RULES_SCHEMA_VERSION
        assert connection.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 35
        example_count = connection.execute(
            "SELECT COUNT(*) FROM records WHERE id LIKE '%example%'"
        ).fetchone()[0]
        assert example_count == 0
        assert (
            connection.execute(
                "SELECT page FROM vocabulary_sources WHERE vocabulary = 'skillTypes'"
            ).fetchone()[0]
            == 76
        )
        assert (
            connection.execute(
                "SELECT page FROM vocabulary_sources WHERE vocabulary = 'labels'"
            ).fetchone()[0]
            == 174
        )
        assert (
            connection.execute(
                "SELECT related_record_id FROM record_relations "
                "WHERE record_id = 'state:camouflaged' ORDER BY position LIMIT 1"
            ).fetchone()[0]
            == "skill:camouflage"
        )
        assert connection.execute(
            "SELECT source_id, page FROM record_citations "
            "WHERE record_id = 'state:camouflaged' AND path IS NULL "
            "ORDER BY page LIMIT 1"
        ).fetchone() == ("n5-core-v5.3-pdf", 87)


def test_rules_database_returns_current_trait_records(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    output = tmp_path / "rules.db"
    export_rules_database(documents, output)

    database = RulesDatabase(output)
    database.validate()
    traits = {record["id"]: record for record in database.records_by_kind("trait")}

    assert len(traits) == 33
    assert traits["trait:suppressive-fire"]["aliases"] == ["Suppressive Fire"]
    assert traits["trait:disposable-x"]["facts"]["sourceIdentity"]["prefixes"] == [
        "Disposable ("
    ]
    assert traits["trait:continuous-damage"]["citations"][0]["heading"] == (
        "Continuous Damage"
    )
