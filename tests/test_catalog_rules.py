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



def test_catalog_rules_surface_msv_mimetism_interaction(tmp_path: Path) -> None:
    catalog = CatalogRules(_rules_database(tmp_path))
    item = {
        "id": 9001,
        "name": "Multispectral Visor",
        "slug": "multispectral-visor",
        "variants": [],
    }

    result = catalog.enrich_catalog_item("equipment", item)

    rule = next(rule for rule in result["rules"] if rule["id"] == "equipment:multispectral-visor")
    assert (
        "reduces-modifiers-from",
        "outbound",
        "Mimetism",
    ) in {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in rule["display_relations"]
    }

def test_catalog_rules_leave_army_item_raw_without_rules_database() -> None:
    item = {"id": 226, "name": "Armed Turret", "profiles": []}

    assert CatalogRules(None).enrich_catalog_item("weapons", item) == item
    assert "special_profile" not in item


def test_catalog_rules_apply_curated_tinbot_family_and_named_variant_rules(
    tmp_path: Path,
) -> None:
    catalog = CatalogRules(_rules_database(tmp_path))
    item = {
        "id": 235,
        "name": "TinBot",
        "slug": "tinbot",
        "variants": [
            {
                "item_id": 169,
                "item_name": "TinBot: Firewall",
                "extras": [{"id": 1, "name": "-3"}],
                "units": [],
            },
            {
                "item_id": 244,
                "item_name": "TinBot: Discover",
                "extras": [{"id": 2, "name": "+3"}],
                "units": [],
            },
        ],
    }

    result = catalog.enrich_catalog_item("equipment", item)

    assert [rule["id"] for rule in result["rules"]] == ["equipment:tinbot"]
    firewall, discover = result["variants"]
    assert [rule["id"] for rule in firewall["rules"]] == [
        "equipment:tinbot-firewall"
    ]
    assert firewall["source_variant"] == {"kind": "named", "label": "Firewall"}
    assert firewall["rules"][0]["variant_semantics"]["source_variant"] == {
        "kind": "named",
        "label": "Firewall",
    }
    assert firewall["extras"] == [{"id": 1, "name": "-3"}]
    assert [rule["id"] for rule in discover["rules"]] == [
        "equipment:tinbot-discover"
    ]
    assert discover["source_variant"] == {"kind": "named", "label": "Discover"}
    assert discover["rules"][0]["variant_semantics"]["source_variant"] == {
        "kind": "named",
        "label": "Discover",
    }
    assert discover["extras"] == [{"id": 2, "name": "+3"}]


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
                "id": "equipment:testbot",
                "name": "TestBot",
                "armyLinks": [{"entity": "equipment", "id": "testbot"}],
                "variantSemantics": {"inheritance": "family"},
            },
            {
                **common,
                "id": "equipment:testbot-discover",
                "name": "TestBot: Discover",
                "summary": "Discover variant semantics only.",
                "armyLinks": [{"entity": "equipment", "id": 900244}],
                "variantSemantics": {
                    "inheritance": "source",
                    "sourceVariant": {"kind": "named", "label": "test variant"},
                },
                "relations": [
                    {"type": "variant-of", "recordId": "equipment:testbot"}
                ],
            },
        ]
    )
    rules_path = tmp_path / "rules.db"
    export_rules_database([(current_path, document)], rules_path)
    item = {
        "id": 900235,
        "name": "TestBot",
        "slug": "testbot",
        "variants": [
            {
                "item_id": 900244,
                "item_name": "TestBot: Discover",
                "extras": [],
                "units": [],
            }
        ],
    }

    result = CatalogRules(RulesDatabase(rules_path)).enrich_catalog_item(
        "equipment", item
    )

    assert [rule["id"] for rule in result["rules"]] == ["equipment:testbot"]
    assert result["variants"][0]["source_variant"] == {
        "kind": "named",
        "label": "test variant",
    }
    assert [rule["id"] for rule in result["variants"][0]["rules"]] == [
        "equipment:testbot-discover"
    ]


def test_equipment_catalog_adds_curated_declaration_categories(tmp_path: Path) -> None:
    catalog = CatalogRules(_rules_database(tmp_path))
    item = {
        "id": 21,
        "name": "Medikit",
        "slug": "medikit",
        "variants": [],
    }

    result = catalog.enrich_catalog_item("equipment", item)

    assert result["categories"] == [
        {"name": "Short Skill", "source": "N5 Core Rules v5.3", "page": 124}
    ]
    assert [rule["id"] for rule in result["rules"]] == ["equipment:medikit"]
    assert result["rules"][0]["declaration_categories"] == result["categories"]
