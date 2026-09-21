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
        assert connection.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 103
        example_count = connection.execute(
            "SELECT COUNT(*) FROM records WHERE id LIKE '%example%'"
        ).fetchone()[0]
        assert example_count == 0
        assert connection.execute(
            "SELECT member, page FROM vocabulary_sources WHERE vocabulary = 'skillTypes'"
        ).fetchone() == ("Skills_and_Equipment_Module", None)
        assert connection.execute(
            "SELECT member, page FROM vocabulary_sources WHERE vocabulary = 'labels'"
        ).fetchone() == ("Labels", None)
        assert connection.execute(
            "SELECT local_path, sha256, acquired_at, language, document_count, url "
            "FROM sources WHERE id = 'wiki-en-20260918-130233'"
        ).fetchone() == (
            "data/wiki/WIKI-en 20260918-130233.zip",
            "aa407f1959fbaafce98058acf507640cc94bfc2690d4a7519a547caf1492f23a",
            "2026-09-18T13:02:33+02:00",
            "en",
            812,
            "https://infinitythewiki.com/",
        )
        assert connection.execute(
            "SELECT url FROM sources WHERE id = 'n5-core-v5.3-pdf'"
        ).fetchone()[0] == "https://experience.corvusbelli.com/en/infinity/resources"
        assert (
            connection.execute(
                "SELECT related_record_id FROM record_relations "
                "WHERE record_id = 'state:camouflaged' ORDER BY position LIMIT 1"
            ).fetchone()[0]
            == "skill:camouflage"
        )
        assert connection.execute(
            "SELECT source_id, page FROM record_citations "
            "WHERE record_id = 'state:camouflaged' AND page IS NOT NULL "
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
    assert traits["trait:continuous-damage"]["citations"][0]["source_url"] == (
        "https://infinitythewiki.com/index.php?title=Traits&oldid=4110"
    )
    camouflaged = database.records_by_kind("state")[0]
    archived = next(
        citation
        for citation in camouflaged["citations"]
        if citation["source_id"] == "wiki-en-20260918-130233"
    )
    assert archived["member"] == "Camouflaged_State"
    assert archived["source_url"] == "https://infinitythewiki.com/"


def test_rules_database_returns_armed_turret_special_profile(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    output = tmp_path / "rules.db"
    export_rules_database(documents, output)

    database = RulesDatabase(output)
    records = database.records_for_army_link("weapon", "armed-turret")

    assert [record["id"] for record in records] == ["weapon:armed-turret"]
    assert records[0]["facts"]["specialProfile"] == {
        "stats": [
            ["MOV", "--"],
            ["CC", "5"],
            ["BS", "10"],
            ["PH", "--"],
            ["WIP", "--"],
            ["ARM", "2"],
            ["BTS", "3"],
            ["STR", "1"],
            ["S", "2"],
        ],
        "equipment": ["360º Visor"],
        "skills": ["Total Reaction"],
        "ccWeapon": "PARA CC Weapon (-3)",
    }
    assert records[0]["citations"][0]["heading"] == "Armed Turret Profile"


def test_rules_database_returns_skill_parameter_semantics(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    output = tmp_path / "rules.db"
    export_rules_database(documents, output)

    assert RulesDatabase(output).skill_parameter_semantics() == {
        "super-jump": {"kind": "distance", "positive_sign": "omit"},
        "forward-deployment": {"kind": "distance", "positive_sign": "force"},
    }

def test_rules_database_returns_skill_declaration_categories(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    output = tmp_path / "rules.db"
    export_rules_database(documents, output)

    database = RulesDatabase(output)
    categories = [
        category
        for category in database.skill_declaration_categories()
        if category["skill_ref"] == "sapper"
    ]

    assert categories == [
        {
            "skill_ref": "sapper",
            "name": "Deployment",
            "order": 20,
            "source_title": "N5 Core Rules",
            "source_version": "5.3",
            "page": 111,
        },
        {
            "skill_ref": "sapper",
            "name": "Long Skill",
            "order": 40,
            "source_title": "N5 Core Rules",
            "source_version": "5.3",
            "page": 111,
        },
    ]
