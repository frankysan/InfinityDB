import copy
import sqlite3
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_directory
from infinity_db.database import Database
from infinity_db.rules_database import (
    RULES_APPLICATION_ID,
    RULES_SCHEMA_VERSION,
    RulesDatabase,
    export_rules_database,
)
from infinity_db.skill_catalog import SkillCatalog


def test_export_rules_database_ignores_example_and_preserves_provenance(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    output = tmp_path / "rules.db"

    export_rules_database(documents, output)

    with sqlite3.connect(output) as connection:
        assert connection.execute("PRAGMA application_id").fetchone()[0] == RULES_APPLICATION_ID
        assert connection.execute("PRAGMA user_version").fetchone()[0] == RULES_SCHEMA_VERSION
        assert connection.execute("SELECT COUNT(*) FROM collections").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 138
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
        assert connection.execute(
            "SELECT relation_type, related_record_id FROM record_relations "
            "WHERE record_id = 'skill:camouflage' ORDER BY position LIMIT 1"
        ).fetchone() == ("enters-state", "state:camouflaged")
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
    assert traits["trait:continuous-damage"]["collection"] == {
        "id": "n5-core-v5.3",
        "title": "N5 Core Rules v5.3",
        "domain": "core-rules",
        "status": "current",
        "effective_from": "2026-08-10",
        "authority": "primary",
    }
    camouflaged = database.records_by_kind("state")[0]
    archived = next(
        citation
        for citation in camouflaged["citations"]
        if citation["source_id"] == "wiki-en-20260918-130233"
    )
    assert archived["member"] == "Camouflaged_State"
    assert archived["source_url"] == "https://infinitythewiki.com/"


def test_training_classifies_normal_order_types_without_conflating_tactical_orders(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[1]
    output = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), output)
    database = RulesDatabase(output)
    training = database.training_by_order_type()
    assert set(training) == {"regular", "irregular"}
    assert {item["id"] for item in training.values()} == {
        "training:regular",
        "training:irregular",
    }
    assert all(item["kind"] == "training" for item in training.values())
    assert all(item["citations"][0]["page"] == 11 for item in training.values())
    assert all(item["collection"]["status"] == "current" for item in training.values())

    with sqlite3.connect(output) as connection:
        connection.execute("UPDATE collections SET status = 'superseded'")
    assert database.training_by_order_type() == {}


def test_training_enrichment_preserves_all_other_orders(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    output = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), output)
    catalog = SkillCatalog(Database(tmp_path / "unused.db"), RulesDatabase(output))
    unit = {
        "armies": [
            {
                "loadouts": [
                    {
                        "orders": [
                            {"type": "regular", "list": 1},
                            {"type": "irregular", "list": 1},
                            {"type": "tactical", "list": 1},
                            {"type": "lieutenant", "list": 1},
                        ]
                    }
                ]
            }
        ]
    }
    enriched = catalog.enrich_unit(unit)
    orders = enriched["armies"][0]["loadouts"][0]["orders"]
    assert [order.get("training_reference", {}).get("id") for order in orders] == [
        "training:regular", "training:irregular", None, None
    ]
    assert all(
        "training_reference" not in order
        for order in unit["armies"][0]["loadouts"][0]["orders"]
    )


def test_rules_database_returns_armed_turret_special_profile(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    output = tmp_path / "rules.db"
    export_rules_database(documents, output)

    database = RulesDatabase(output)
    records = database.records_for_army_link("weapon", "armed-turret")

    assert [record["id"] for record in records] == ["weapon:armed-turret"]
    assert records[0]["variant_semantics"] == {"inheritance": "family"}
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


def test_rules_database_returns_reviewed_source_variant_semantics(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    output = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), output)

    variants = RulesDatabase(output).catalog_source_variant_semantics("skill")

    assert variants[19] == {"kind": "level", "value": 1}
    assert variants[23] == {"kind": "level", "value": 5}
    assert variants[69] == {"kind": "level", "value": 1}
    assert variants[70] == {"kind": "level", "value": 2}
    assert variants[278] == {
        "kind": "attribute-replacement",
        "attribute": "BS",
        "value": 12,
    }
    assert variants[279] == {
        "kind": "attribute-replacement",
        "attribute": "BS",
        "value": 11,
    }
    assert variants[274] == {
        "kind": "attribute-replacement",
        "attribute": "CC",
        "value": 21,
    }

    equipment_variants = RulesDatabase(output).catalog_source_variant_semantics(
        "equipment"
    )
    assert equipment_variants[169] == {"kind": "named", "label": "Firewall"}
    assert equipment_variants[188] == {"kind": "named", "label": "Neurocinetics"}
    assert equipment_variants[193] == {"kind": "named", "label": "Albedo"}
    assert equipment_variants[244] == {"kind": "named", "label": "Discover"}
    assert equipment_variants[247] == {"kind": "named", "label": "ECM Guided"}
    assert equipment_variants[248] == {"kind": "named", "label": "Repeater"}


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
            "order": 50,
            "source_title": "N5 Core Rules",
            "source_version": "5.3",
            "page": 111,
        },
    ]



def test_rules_database_returns_equipment_declaration_categories(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    output = tmp_path / "rules.db"
    export_rules_database(documents, output)

    categories = RulesDatabase(output).declaration_categories("equipment")

    assert [
        {
            "army_ref": category["army_ref"],
            "type_id": category["type_id"],
            "name": category["name"],
            "order": category["order"],
            "page": category["page"],
        }
        for category in categories
    ] == [
        {
            "army_ref": "deactivator",
            "type_id": "short-skill",
            "name": "Short Skill",
            "order": 40,
            "page": 121,
        },
        {
            "army_ref": "gizmokit",
            "type_id": "short-skill",
            "name": "Short Skill",
            "order": 40,
            "page": 123,
        },
        {
            "army_ref": "medikit",
            "type_id": "short-skill",
            "name": "Short Skill",
            "order": 40,
            "page": 124,
        },
    ]

    with pytest.raises(ValueError, match="skill or equipment"):
        RulesDatabase(output).declaration_categories("weapon")


def test_current_declaration_categories_match_reviewed_n5_3_semantics(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[1]
    output = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), output)
    database = RulesDatabase(output)

    skill_categories: dict[object, list[str]] = {}
    for category in database.declaration_categories("skill"):
        skill_categories.setdefault(category["army_ref"], []).append(category["name"])

    assert skill_categories["bs-attack"] == ["Short Skill", "ARO"]
    assert skill_categories["cc-attack"] == ["Short Skill", "ARO"]
    assert skill_categories["dodge"] == ["Short Skill", "ARO"]
    assert skill_categories["forward-observer"] == ["Short Skill", "ARO"]
    assert skill_categories["doctor"] == ["Short Skill"]
    assert skill_categories["engineer"] == ["Short Skill"]
    assert skill_categories["cyberplug"] == ["Automatic"]
    assert skill_categories["paramedic"] == ["Automatic"]
    assert skill_categories["parachutist"] == ["Long Skill"]
    assert skill_categories["triangulated-fire"] == ["Long Skill"]
    assert skill_categories["berserk"] == ["Long Skill"]


def test_army_link_records_use_current_collections_by_default(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    current_path, current = load_curated_directory(root / "data" / "curated")[0]
    superseded = copy.deepcopy(current)
    superseded["collection"] = {
        **superseded["collection"],
        "id": "n5-core-v5.2",
        "title": "N5 Core Rules v5.2",
        "status": "superseded",
        "effectiveFrom": "2026-01-01",
    }
    output = tmp_path / "rules.db"
    export_rules_database(
        [(current_path, current), (root / "n5-core-v5.2.json", superseded)],
        output,
    )

    database = RulesDatabase(output)
    current_records = database.records_for_army_link("skill", "camouflage")
    all_records = database.records_for_army_link(
        "skill", "camouflage", current_only=False
    )

    assert current_records
    assert {record["collection"]["status"] for record in current_records} == {"current"}
    assert len(all_records) == len(current_records) * 2
    assert {record["collection"]["status"] for record in all_records} == {
        "current",
        "superseded",
    }


def test_composed_records_attach_current_supplements_without_field_merging(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[1]
    current_path, current = load_curated_directory(root / "data" / "curated")[0]
    supplement = copy.deepcopy(current)
    supplement["collection"] = {
        **supplement["collection"],
        "id": "n5-faq-v0.1",
        "title": "N5 FAQ v0.1",
        "domain": "faq",
        "effectiveFrom": "2026-09-01",
    }
    supplement["records"] = [
        {
            "id": "skill:camouflage",
            "kind": "skill",
            "name": "Camouflage",
            "summary": "A scoped FAQ clarification for Camouflage.",
            "composition": {"role": "supplement"},
            "scope": {"game": "N5", "seasons": ["current"]},
            "citations": [{"sourceId": "n5-core-v5.3-pdf", "page": 87}],
            "review": {"status": "reviewed", "reviewedOn": "2026-09-23"},
        }
    ]
    output = tmp_path / "rules.db"
    export_rules_database(
        [(current_path, current), (root / "n5-faq-v0.1.json", supplement)], output
    )

    raw = RulesDatabase(output).records_for_army_link("skill", "camouflage")
    composed = RulesDatabase(output).composed_records_for_army_link(
        "skill", "camouflage"
    )

    raw_camouflage = [record for record in raw if record["id"] == "skill:camouflage"]
    composed_camouflage = next(
        record for record in composed if record["id"] == "skill:camouflage"
    )
    assert len(raw_camouflage) == 1
    assert composed_camouflage["summary"] == next(
        record["summary"]
        for record in current["records"]
        if record["id"] == "skill:camouflage"
    )
    assert [item["summary"] for item in composed_camouflage["supplements"]] == [
        "A scoped FAQ clarification for Camouflage."
    ]
    assert composed_camouflage["supplements"][0]["collection"]["id"] == "n5-faq-v0.1"


def test_export_rejects_ambiguous_current_definitions(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    current_path, current = load_curated_directory(root / "data" / "curated")[0]
    duplicate = copy.deepcopy(current)
    duplicate["collection"] = {
        **duplicate["collection"],
        "id": "n5-annex-current",
        "title": "N5 Annex",
        "domain": "annex",
    }
    duplicate["records"] = [
        next(record for record in duplicate["records"] if record["id"] == "skill:camouflage")
    ]

    with pytest.raises(ValueError, match="exactly one definition contribution"):
        export_rules_database(
            [(current_path, current), (root / "annex.json", duplicate)],
            tmp_path / "rules.db",
        )


def test_rules_database_exposes_reverse_typed_relations(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    output = tmp_path / "rules.db"
    export_rules_database(documents, output)

    database = RulesDatabase(output)
    relations = database.relations_for_record("state:camouflaged")

    assert {
        (item["type"], item["direction"], item["record_id"])
        for item in relations
    } == {
        ("enters-state", "inbound", "skill:camouflage"),
        ("reveals-state", "inbound", "skill:discover"),
    }

    camouflage = next(
        record
        for record in database.composed_records_for_army_link("skill", "camouflage")
        if record["id"] == "skill:camouflage"
    )
    assert camouflage["display_relations"] == [
        {
            "type": "enters-state",
            "record_id": "state:camouflaged",
            "collection_id": "n5-core-v5.3",
            "direction": "outbound",
            "record": {
                "id": "state:camouflaged",
                "kind": "state",
                "name": "Camouflaged State",
                "army_links": [],
            },
        }
    ]

    camouflaged = next(
        record
        for record in database.composed_records_by_kind("state")
        if record["id"] == "state:camouflaged"
    )
    assert {
        (
            relation["type"],
            relation["direction"],
            relation["record"]["name"],
            tuple(
                (link["entity"], link.get("id"))
                for link in relation["record"]["army_links"]
            ),
        )
        for relation in camouflaged["display_relations"]
    } == {
        ("enters-state", "inbound", "Camouflage", (("skill", "camouflage"),)),
        ("reveals-state", "inbound", "Discover", (("skill", "discover"),)),
    }



def test_msv_mimetism_interaction_is_bidirectional(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    output = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), output)
    database = RulesDatabase(output)

    msv = next(
        record
        for record in database.composed_records_for_army_link(
            "equipment", "multispectral-visor"
        )
        if record["id"] == "equipment:multispectral-visor"
    )
    mimetism = next(
        record
        for record in database.composed_records_for_army_link("skill", "mimetism")
        if record["id"] == "skill:mimetism"
    )

    assert msv["display_relations"] == [
        {
            "type": "reduces-modifiers-from",
            "record_id": "skill:mimetism",
            "collection_id": "n5-core-v5.3",
            "direction": "outbound",
            "record": {
                "id": "skill:mimetism",
                "kind": "skill",
                "name": "Mimetism",
                "army_links": [{"entity": "skill", "id": "mimetism"}],
            },
        }
    ]
    assert mimetism["display_relations"] == [
        {
            "type": "reduces-modifiers-from",
            "record_id": "equipment:multispectral-visor",
            "collection_id": "n5-core-v5.3",
            "direction": "inbound",
            "record": {
                "id": "equipment:multispectral-visor",
                "kind": "equipment",
                "name": "Multispectral Visor",
                "army_links": [
                    {"entity": "equipment", "id": "multispectral-visor"}
                ],
            },
        }
    ]


def test_stealth_counter_interactions_are_bidirectional(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    output = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), output)
    database = RulesDatabase(output)

    def skill_rule(slug: str, record_id: str) -> dict:
        return next(
            record
            for record in database.composed_records_for_army_link("skill", slug)
            if record["id"] == record_id
        )

    combat_instinct = skill_rule("combat-instinct", "skill:combat-instinct")
    sixth_sense = skill_rule("sixth-sense", "skill:sixth-sense")
    stealth = skill_rule("stealth", "skill:stealth")
    surprise_attack = skill_rule("surprise-attack", "skill:surprise-attack")

    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in combat_instinct["display_relations"]
    } == {
        ("ignores-modifiers-from", "outbound", "Surprise Attack"),
        ("negates-effects-of", "outbound", "Stealth"),
    }
    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in sixth_sense["display_relations"]
    } == {("negates-effects-of", "outbound", "Stealth")}
    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in stealth["display_relations"]
    } == {
        ("negates-effects-of", "inbound", "Combat Instinct"),
        ("negates-effects-of", "inbound", "Sixth Sense"),
    }
    assert {
        (relation["type"], relation["direction"], relation["record"]["name"])
        for relation in surprise_attack["display_relations"]
    } == {("ignores-modifiers-from", "inbound", "Combat Instinct")}


def test_rules_database_preserves_variant_inheritance_and_variant_links(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[1]
    current_path, current = load_curated_directory(root / "data" / "curated")[0]
    document = copy.deepcopy(current)
    common = {
        "kind": "skill",
        "summary": "Variant contract test.",
        "scope": {"game": "N5", "seasons": ["current"]},
        "facts": {"category": "special-skill", "typeId": "automatic"},
        "labelIds": [],
        "citations": [{"sourceId": "n5-core-v5.3-pdf", "page": 76}],
        "composition": {"role": "definition"},
        "review": {"status": "reviewed", "reviewedOn": "2026-09-23"},
    }
    document["records"].extend(
        [
            {
                **common,
                "id": "skill:variant-family-test",
                "name": "Variant Family Test",
                "armyLinks": [{"entity": "skill", "id": "variant-family-test"}],
                "variantSemantics": {"inheritance": "family"},
            },
            {
                **common,
                "id": "skill:variant-family-test-l2",
                "name": "Variant Family Test L2",
                "armyLinks": [{"entity": "skill", "id": 92020}],
                "variantSemantics": {
                    "inheritance": "source",
                    "sourceVariant": {"kind": "named", "label": "test variant"},
                },
                "relations": [
                    {"type": "variant-of", "recordId": "skill:variant-family-test"}
                ],
            },
        ]
    )
    output = tmp_path / "rules.db"
    export_rules_database([(current_path, document)], output)

    database = RulesDatabase(output)
    family = database.composed_records_for_army_link("skill", "variant-family-test")
    exact = database.composed_records_for_army_link("skill", 92020)

    assert family[0]["variant_semantics"] == {"inheritance": "family"}
    assert exact[0]["variant_semantics"] == {
        "inheritance": "source",
        "source_variant": {"kind": "named", "label": "test variant"},
    }
    assert exact[0]["relations"] == [
        {
            "type": "variant-of",
            "record_id": "skill:variant-family-test",
            "collection_id": "n5-core-v5.3",
        }
    ]
    assert {
        (relation["type"], relation["direction"], relation["record_id"])
        for relation in database.relations_for_record("skill:variant-family-test")
        if relation["type"] == "variant-of"
    } == {("variant-of", "inbound", "skill:variant-family-test-l2")}


def test_export_rejects_source_specific_variant_without_family_relation(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[1]
    current_path, current = load_curated_directory(root / "data" / "curated")[0]
    document = copy.deepcopy(current)
    document["records"].append(
        {
            "id": "skill:orphan-variant-test",
            "kind": "skill",
            "name": "Orphan Variant Test",
            "summary": "Invalid source-specific variant.",
            "scope": {"game": "N5", "seasons": ["current"]},
            "facts": {"category": "special-skill", "typeId": "automatic"},
            "labelIds": [],
            "citations": [{"sourceId": "n5-core-v5.3-pdf", "page": 76}],
            "composition": {"role": "definition"},
            "review": {"status": "reviewed", "reviewedOn": "2026-09-23"},
            "armyLinks": [{"entity": "skill", "id": 20}],
            "variantSemantics": {
                "inheritance": "source",
                "sourceVariant": {"kind": "named", "label": "test variant"},
            },
        }
    )

    with pytest.raises(ValueError, match="requires exactly one 'variant-of' relation"):
        export_rules_database([(current_path, document)], tmp_path / "rules.db")
