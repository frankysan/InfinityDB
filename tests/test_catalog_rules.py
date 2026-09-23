import copy
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
        {"id": 226, "name": "Armed Turret", "slug": "armed-turret", "profiles": []},
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


def test_catalog_rules_keep_source_specific_rules_on_matching_variant(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[1]
    current_path, current = load_curated_directory(root / "data" / "curated")[0]
    document = copy.deepcopy(current)
    common = {
        "kind": "equipment",
        "summary": "TinBot test semantics.",
        "scope": {"game": "N5", "seasons": ["current"]},
        "citations": [{"sourceId": "n5-core-v5.3-pdf", "page": 123}],
        "composition": {"role": "definition"},
        "review": {"status": "reviewed", "reviewedOn": "2026-09-23"},
    }
    document["records"].extend(
        [
            {
                **common,
                "id": "equipment:tinbot",
                "name": "TinBot",
                "armyLinks": [{"entity": "equipment", "id": "tinbot"}],
                "variantSemantics": {"inheritance": "family"},
            },
            {
                **common,
                "id": "equipment:tinbot-discover",
                "name": "TinBot: Discover",
                "summary": "Discover variant semantics only.",
                "armyLinks": [{"entity": "equipment", "id": 244}],
                "variantSemantics": {"inheritance": "source"},
                "relations": [
                    {"type": "variant-of", "recordId": "equipment:tinbot"}
                ],
            },
        ]
    )
    rules_path = tmp_path / "rules.db"
    export_rules_database([(current_path, document)], rules_path)
    item = {
        "id": 235,
        "name": "TinBot",
        "slug": "tinbot",
        "variants": [
            {"item_id": 244, "item_name": "TinBot: Discover", "extras": [], "units": []}
        ],
    }

    result = CatalogRules(RulesDatabase(rules_path)).enrich_catalog_item(
        "equipment", item
    )

    assert [rule["id"] for rule in result["rules"]] == ["equipment:tinbot"]
    assert [rule["id"] for rule in result["variants"][0]["rules"]] == [
        "equipment:tinbot-discover"
    ]
