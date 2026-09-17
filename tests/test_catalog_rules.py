from pathlib import Path

from infinity_db.catalog_rules import CatalogRules
from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import RulesDatabase, export_rules_database


def _rules_database(tmp_path: Path) -> RulesDatabase:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    output = tmp_path / "rules.db"
    export_rules_database(documents, output)
    return RulesDatabase(output)


def test_armed_turret_profile_comes_from_curated_rules(tmp_path: Path) -> None:
    catalog = CatalogRules(_rules_database(tmp_path))

    item = catalog.enrich_catalog_item(
        "weapons",
        {"id": 226, "name": "Armed Turret", "profiles": []},
    )

    assert item["special_profile"] == {
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
        "cc_weapon": "PARA CC Weapon (-3)",
    }
    assert [rule["id"] for rule in item["rules"]] == ["weapon:armed-turret"]


def test_catalog_rules_leave_army_item_raw_without_rules_database() -> None:
    item = {"id": 226, "name": "Armed Turret", "profiles": []}

    assert CatalogRules(None).enrich_catalog_item("weapons", item) == item
    assert "special_profile" not in item
