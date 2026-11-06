from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import zipfile
from collections.abc import Callable, Iterable
from contextlib import closing
from copy import deepcopy
from functools import partial
from pathlib import Path
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_army_data.metadata import decode_metadata
from infinity_army_data.normalize import normalize_master, validate_normalized
from infinity_db.application_domains import (
    APPLICATION_DOMAINS,
    application_domain,
    public_rule_domain,
    public_rule_record_domain,
    record_matches_domain,
    semantic_record_domain,
    semantic_record_owner,
)
from infinity_db.curated import load_curated_directory
from infinity_db.database import Database, export_database
from infinity_db.domain_references import (
    enrich_rule_relation_references,
    rule_record_public_reference,
)
from infinity_db.domain_slugs import route_slug_from_qualified_typed_domain_id
from infinity_db.glossary_catalog import GlossaryCatalog
from infinity_db.hacking_program_catalog import HackingProgramCatalog
from infinity_db.reference_catalog import LabelCatalog, RulesRecordCatalog
from infinity_db.rules_database import RulesDatabase, export_rules_database
from infinity_db.skill_catalog import SkillCatalog
from infinity_db.web import create_app
from tools.audit_1_0_reference_inputs import _WikiHeadings
from tools.verify_ammunition_browser import WIDTHS, source_names, verify
from tools.verify_general_rules_browser import source_rules
from tools.verify_labels_browser import source_names as label_source_names


def _reference_database(tmp_path: Path) -> Database:
    skills = [
        {"id": 1000, "name": "Hacker"},
        *[
            {"id": 18 + level, "name": f"Martial Arts L{level}"}
            for level in range(1, 6)
        ],
        {"id": 25, "name": "Booty"},
        {"id": 55, "name": "MetaChemistry"},
    ]
    equipment = [
        {"id": 100, "name": "Hacking Device"},
        {"id": 101, "name": "Hacking Device Plus"},
        {"id": 145, "name": "Killer Hacking Device"},
        {"id": 182, "name": "EVO Hacking Device"},
    ]
    source = {
        "factions": [{"id": 101, "parent": 101, "name": "Army", "slug": "army"}],
        "skills": skills,
        "equips": equipment,
        "hack": [
            {
                "name": "Carbonite",
                "attack": "0",
                "opponent": "0",
                "damage": "7",
                "burst": "2",
                "special": "DA Ammo. State: IMM-B. Non-Lethal.",
                "devices": [100, 101],
                "target": ["TAG", "HI", "REM", "Hacker", "VH"],
                "skillType": ["short", "aro"],
                "extra": 13,
            },
            {
                "name": "Zero Pain",
                "attack": "0",
                "opponent": "-3",
                "damage": "-",
                "burst": "2",
                "special": "Nullifies Comms Attack.",
                "target": [],
                "skillType": ["short", "aro"],
                "extra": 287,
            },
        ],
        "martialArts": [
            {
                "name": str(level),
                "attack": "0" if level == 1 else "+3",
                "opponent": "-3",
                "damage": "-",
                "burst": "+1B" if level >= 4 else "0",
            }
            for level in range(1, 6)
        ],
        "metachemistry": [
            {"id": 1, "name": "1-3", "value": "+3 PH"},
            {"id": 4, "name": "4-5", "value": "Super-Jump"},
        ],
        "booty": [
            {"id": 1, "name": "1-2", "value": "+1 ARM"},
            {"id": 3, "name": "3-4", "value": "Light Flamethrower"},
        ],
    }
    envelope = decode_metadata(json.dumps(source).encode(), "metadata.json")
    master = {
        "_meta": {"format": "Infinity Army merged JSON", "formatVersion": 1},
        "armyMetadata": envelope,
        "armyLists": {
            "101": {
                "_meta": {"slug": "army", "kind": "army"},
                "unitIds": [1],
                "filters": {"skills": skills, "equip": equipment},
            }
        },
        "units": {
            "1": {
                "shared": {"id": 1, "name": "Unit", "factions": [101]},
                "byArmy": {"101": {}},
            }
        },
    }
    normalized = normalize_master(master)
    validate_normalized(normalized)
    path = tmp_path / "infinity.db"
    export_database(normalized, path)
    return Database(path)


def test_application_domain_registry_separates_identity_from_presentation() -> None:
    assert len({domain.slug for domain in APPLICATION_DOMAINS}) == len(APPLICATION_DOMAINS)
    assert {domain.slug for domain in APPLICATION_DOMAINS if domain.level == "top-level"} == {
        "armies",
        "units",
        "skills",
        "equipment",
        "weapons",
        "ammunition",
        "traits",
        "states",
        "hacking-programs",
        "fireteams",
        "labels",
        "scenarios",
        "rules",
    }

    ammunition = application_domain("ammunition")
    assert ammunition.presentation == "catalog"
    assert ammunition.record_kinds == ("ammunition",)
    assert ammunition.navigation is True
    assert ammunition.search is True
    assert ammunition.glossary is True
    assert ammunition.catalog is True
    assert ammunition.detail is True
    assert ammunition.published is True

    labels = application_domain("labels")
    assert labels.presentation == "catalog"
    assert labels.record_kinds == ()
    assert labels.navigation is True
    assert labels.glossary is True
    assert labels.published is True

    armies = application_domain("armies")
    assert armies.presentation == "overview"
    assert armies.navigation is True
    assert armies.landing is True
    assert armies.catalog is False
    assert armies.detail is False
    assert armies.published is True
    assert armies.route == "/armies"

    scenarios = application_domain("scenarios")
    assert scenarios.presentation == "catalog"
    assert scenarios.record_kinds == ("scenario",)
    assert scenarios.landing is True
    assert scenarios.catalog is True
    assert scenarios.detail is True
    assert scenarios.navigation is True
    assert scenarios.search is False
    assert scenarios.glossary is False
    assert scenarios.published is True
    assert scenarios.route == "/scenarios"
    assert semantic_record_domain("scenario") == scenarios

    fireteams = application_domain("fireteams")
    assert fireteams.presentation == "scoped"
    assert fireteams.landing is True
    assert fireteams.scoped is True
    assert fireteams.catalog is False
    assert fireteams.detail is False

    attributes = application_domain("attributes")
    assert attributes.level == "embedded"
    assert attributes.glossary is True
    assert attributes.search is True
    assert attributes.published is True
    assert attributes.route is None
    assert attributes.catalog is False
    assert attributes.detail is False

    terms = application_domain("terms")
    assert terms.level == "embedded"
    assert terms.record_kinds == ("term",)
    assert terms.glossary is True
    assert terms.search is True
    assert terms.published is True
    assert terms.route is None
    assert terms.catalog is False
    assert terms.detail is False

    general_rules = application_domain("rules")
    assert general_rules.published is True
    assert general_rules.navigation is True
    assert general_rules.route == "/rules"
    assert general_rules.record_kinds == ("rule",)
    assert set(general_rules.record_categories) == {
        "basic-rule",
        "command-token-use",
        "order-type",
        "peripheral-type",
        "optional-extra",
    }

    assert public_rule_domain("ammunition") == ammunition
    assert public_rule_domain("attribute") is None
    assert semantic_record_domain("attribute") == attributes
    assert public_rule_domain("term") is None
    assert semantic_record_domain("term") == terms
    assert public_rule_domain("rule") is None
    assert public_rule_domain("scenario") == scenarios
    assert public_rule_record_domain(
        {"kind": "rule", "facts": {"category": "basic-rule"}}
    ) == general_rules
    assert public_rule_record_domain(
        {"kind": "rule", "facts": {"category": "fireteam-general"}}
    ) is None
    for category in ("fireteam-general", "fireteam-level-bonuses"):
        record = {"kind": "rule", "facts": {"category": category}}
        assert semantic_record_owner(record) == fireteams
        assert rule_record_public_reference(None, record) == {"href": "/fireteams"}
    assert semantic_record_owner({"kind": "rule", "facts": {"category": "unknown"}}) is None
    assert rule_record_public_reference(
        None, {"kind": "rule", "facts": {"category": "unknown"}},
    ) is None


def test_attributes_are_current_canonical_embedded_records(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    rules_database = RulesDatabase(rules_path)

    attributes = rules_database.composed_records_by_kind("attribute")
    assert {record["id"] for record in attributes} == {
        "attribute:mov",
        "attribute:cc",
        "attribute:bs",
        "attribute:ph",
        "attribute:wip",
        "attribute:arm",
        "attribute:bts",
        "attribute:vita",
        "attribute:str",
        "attribute:ava",
        "attribute:s",
        "attribute:swc",
        "attribute:c",
    }
    movement = next(record for record in attributes if record["id"] == "attribute:mov")
    assert movement["name"] == "Movement (MOV)"
    assert movement["facts"]["abbreviation"] == "MOV"


@pytest.mark.parametrize("relative,pin,language", [
    ("data/pdf/rules/n5-rules-v5.3-en.pdf",
     "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f", "en"),
    ("data/pdf/rules/n5-rules-v5.3-es.pdf",
     "7f564c864c6f26d6b218a0477c8afeba99da5c56e1a5369bb259f423689bb28f", "es"),
    ("data/pdf/rules/n5-rules-v5.2-en.pdf",
     "643ab0b6d7c3e9e5ffbf668543723161f252367e7788af09ec008be19c17851b", "en"),
])
def test_attribute_dash_and_swc_source_clauses(
    relative: str, pin: str, language: str, require_source_files: Callable[..., None],
) -> None:
    import pymupdf

    path = Path(__file__).parents[1] / relative
    require_source_files(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == pin
    with pymupdf.open(path) as document:
        text = " ".join(str(document[8].get_text("text")).casefold().split())
    if language == "es":
        assert "no podrán declarar ni realizar ninguna habilidad" in text
        assert "que requiera de dicho atributo" in text
        assert "colocar un arma de apoyo a una tropa que pertenezca a esa unidad" in text
    else:
        assert "cannot declare or use any skill that requires that attribute" in text
        assert "adding a support weapon to a trooper of that unit" in text


def test_attribute_dash_and_swc_export_and_api(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data/curated/rules")
    owners = {
        record["id"]: record for _, document in documents for record in document["records"]
        if record["id"] in {"rule:profile-help:attributes", "attribute:swc"}
    }
    assert len(owners) == 2
    fresh = tmp_path / "attributes.db"
    export_rules_database(documents, fresh)
    for database in (RulesDatabase(fresh), RulesDatabase(root / "data/generated/rules.db")):
        for identity, authored in owners.items():
            stored = database.composed_record(identity)
            assert stored is not None
            assert stored["summary"] == authored["summary"]
            assert stored.get("facts") == authored.get("facts")
            assert authored["review"] == {"status": "reviewed", "reviewedOn": "2026-11-06"}
            assert authored["citations"][0]["page"] == 9
            assert authored["citations"][0]["sourceId"] == "n5-core-v5.3-pdf"
    app = create_app(root / "data/generated/infinity.db", rules_database_path=fresh)
    status, body = _published_get(app, "/api/glossary")
    assert status == "200 OK"
    entries = {item["id"]: item for item in json.loads(body)["items"]}
    for identity, authored in owners.items():
        entry = entries[identity]
        assert entry["description"] == authored["summary"]
        assert entry["href"] == "/glossary#" + identity.replace(":", "-")
        assert entry["embedded"] is True
    help_entry = entries["rule:profile-help:attributes"]
    assert "cannot declare or use a Skill that requires it" in help_entry["description"]
    assert {token["target"] for token in help_entry["description_tokens"]
            if token["type"] == "reference"} == {
        "attribute:vita", "attribute:str", "attribute:mov",
    }
    assert "adding a Support Weapon to a Trooper of that Unit" in (
        entries["attribute:swc"]["description"]
    )
    status, body = _published_get(app, "/api/unit-profile-help")
    assert status == "200 OK"
    contextual = next(item for item in json.loads(body)["items"] if item["key"] == "attributes")
    assert contextual["summary"] == owners["rule:profile-help:attributes"]["summary"]


@pytest.mark.parametrize("relative,pin,page,clauses", [
    (
        "data/pdf/rules/n5-rules-v5.3-en.pdf",
        "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f",
        8,
        ("both allies and enemies", "hi, rem, tag, and vh troopers are",
         "hackable unless otherwise stated", "hackers, regardless of troop type"),
    ),
    (
        "data/pdf/rules/n5-rules-v5.3-es.pdf",
        "7f564c864c6f26d6b218a0477c8afeba99da5c56e1a5369bb259f423689bb28f",
        9,
        ("tanto aliados como enemigos", "salvo que se indique",
         "tropas tipo ip, rem, tag y vh son hackeables",
         "hackers, sin importar cuál sea su tipo de tropa"),
    ),
])
def test_hackable_profile_help_pinned_source(
    relative: str, pin: str, page: int, clauses: tuple[str, ...],
    require_source_files: Callable[..., None],
) -> None:
    import pymupdf

    source = Path(__file__).parents[1] / relative
    require_source_files(source)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == pin
    with pymupdf.open(source) as pdf:
        text = " ".join(str(pdf[page - 1].get_text("text")).casefold().split())
    assert all(clause in text for clause in clauses)


def test_hackable_profile_help_export_and_api(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data/curated/rules")
    records = [
        record for _, document in documents for record in document["records"]
        if record["id"] == "rule:profile-help:hackable"
    ]
    assert len(records) == 1
    authored = records[0]
    assert authored["review"] == {"status": "reviewed", "reviewedOn": "2026-11-06"}
    assert authored["citations"] == [
        {"sourceId": "n5-core-v5.3-pdf", "page": 8,
         "section": "Trooper Characteristics"},
        {"sourceId": "n5-core-v5.3-es-pdf", "page": 9,
         "section": "Características de las Tropas"},
    ]
    fresh = tmp_path / "hackable.db"
    export_rules_database(documents, fresh)
    for database_path in (fresh, root / "data/generated/rules.db"):
        record = RulesDatabase(database_path).composed_record(authored["id"])
        assert record is not None
        assert record["summary"] == authored["summary"]
        assert record["facts"] == authored["facts"]
        assert {(citation["source_id"], citation["page"]) for citation in record["citations"]} == {
            ("n5-core-v5.3-pdf", 8), ("n5-core-v5.3-es-pdf", 9),
        }
    app = create_app(root / "data/generated/infinity.db",
                     rules_database_path=root / "data/generated/rules.db")
    status, body = _published_get(app, "/api/unit-profile-help")
    assert status == "200 OK"
    contextual = next(
        row for row in json.loads(body)["items"] if row["key"] == "hackable"
    )
    assert contextual["summary"] == authored["summary"]
    assert all(phrase in contextual["summary"] for phrase in (
        "HI, REM, TAG, and VH", "unless otherwise stated",
        "regardless of Troop Type", "Allied and enemy",
        "each Program's own target requirements",
    ))
    links = [token for token in contextual["summary_tokens"]
             if token["type"] == "reference"]
    assert {token["target"] for token in links} == {"skill:hacker"}
    assert all(token["public_reference"] for token in links)
    status, body = _published_get(app, "/api/glossary")
    assert status == "200 OK"
    published = next(
        row for row in json.loads(body)["items"] if row["id"] == authored["id"]
    )
    assert published["description"] == authored["summary"]
    assert published["href"] == "/glossary#rule-profile-help-hackable"
    assert published["embedded"] is True


def test_game_terms_are_current_canonical_embedded_records(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    rules_database = RulesDatabase(rules_path)

    terms = rules_database.composed_records_by_kind("term")
    assert {record["id"] for record in terms} == {
        "term:ally",
        "term:deployable-equipment",
        "term:deployable-weapon",
        "term:enemy",
        "term:fto",
        "term:hostile",
        "term:low-visibility-zone",
        "term:marker",
        "term:model",
        "term:neutral",
        "term:null-state",
        "term:peripheral",
        "term:poor-visibility-zone",
        "term:scenery-element",
        "term:state-token",
        "term:target",
        "term:token",
        "term:trooper",
        "term:unit-profile",
        "term:victory-points",
        "term:visibility-zone",
        "term:white-noise-zone",
        "term:zero-visibility-zone",
    }
    assert {record["facts"]["scope"] for record in terms} == {
        "alignment",
        "fireteam-eligibility",
        "game-element",
        "profile",
        "scoring",
        "state-classification",
        "trooper-category",
        "visibility-condition",
    }
    trooper = next(record for record in terms if record["id"] == "term:trooper")
    assert trooper["summary"] == (
        "Troopers are game elements represented by Unit Profiles and belonging to "
        "a player's Army List. They have Attributes, contribute Orders to the Order "
        "Pool, can spend Orders to activate themselves, and can declare and receive "
        "Attacks."
    )
    assert [
        (citation["source_id"], citation["page"]) for citation in trooper["citations"]
    ] == [("n5-core-v5.3-pdf", 173)]
    unit_profile = next(record for record in terms if record["id"] == "term:unit-profile")
    assert unit_profile["summary"] == (
        "A Unit Profile represents the Troopers that form a Unit. It gives each "
        "Trooper's numerical Attribute values and lists their Characteristics, "
        "Special Skills, Equipment, and Armor. It also shows the Unit's Trooper "
        "options, which can differ in Skills, Equipment, and Weapons."
    )
    assert unit_profile["facts"]["scope"] == "profile"
    assert [
        (citation["source_id"], citation["page"], citation["section"])
        for citation in unit_profile["citations"]
    ] == [
        ("n5-core-v5.3-pdf", 173, "Terminology — Unit Profile"),
        ("n5-core-v5.3-pdf", 8, "Unit Profile"),
    ]
    peripheral = next(record for record in terms if record["id"] == "term:peripheral")
    assert peripheral["summary"] == (
        "A [[skill:peripheral|Peripheral]] is a special Trooper category. It cannot "
        "contribute or spend "
        "Orders on its own and does not take a place in the Army List. Normally, it "
        "activates when its Controller spends an Order and copies the Controller's "
        "actions; its type-specific rules may differ.\n\n"
        "Its own Troop Profile lists its Cost, which is also added to the Controller's "
        "Cost. The Special Skill explains the Controller relationship and each type."
    )
    assert [
        (citation["source_id"], citation["page"])
        for citation in peripheral["citations"]
    ] == [("n5-core-v5.3-pdf", 173)]


@pytest.mark.parametrize(
    ("identity", "required"),
    (
        ("term:deployable-equipment", ("Attributes belonging", "receive Attacks")),
        ("term:deployable-weapon", ("may belong", "perform and receive Attacks")),
        ("term:target", ("capable of being chosen", "Skills or Equipment")),
        ("term:hostile", ("own Attributes", "Enemy by all players")),
        ("term:neutral", ("has Attributes", "no player's Army List")),
    ),
)
def test_v1s082_p173_glossary_matches_published_release(
    identity: str, required: tuple[str, str],
) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data/curated/rules")
    source = next(
        record for _, document in documents for record in document["records"]
        if record["id"] == identity
    )
    published = RulesDatabase(root / "data/generated/rules.db").composed_record(identity)
    assert published is not None
    assert published["summary"] == source["summary"]
    assert published["facts"] == source["facts"]
    assert source["review"] == {"status": "reviewed", "reviewedOn": "2026-11-06"}
    assert len(source["citations"]) == 1
    assert source["citations"][0]["sourceId"] == "n5-core-v5.3-pdf"
    assert source["citations"][0]["page"] == 173
    assert [
        (citation["source_id"], citation["page"], citation["section"])
        for citation in published["citations"]
    ] == [(
        "n5-core-v5.3-pdf", 173, source["citations"][0]["section"],
    )]
    assert all(fragment in published["summary"] for fragment in required)
    if identity == "term:deployable-weapon":
        assert "must belong" not in published["summary"]
    if identity == "term:neutral":
        assert "treated as an Enemy" not in published["summary"]


def test_null_state_glossary_lists_the_five_n53_source_states(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    rules = RulesDatabase(rules_path)
    null_state = next(
        term for term in rules.composed_records_by_kind("term")
        if term["id"] == "term:null-state"
    )
    expected = (
        "N5.3 explicitly lists: [[state:dead|Dead]], "
        "[[state:disconnected|Disconnected]], [[state:possessed|Possessed]], "
        "[[state:sepsitorized|Sepsitorized]], and "
        "[[state:unconscious|Unconscious]]."
    )
    assert null_state["summary"].endswith(expected)
    assert [
        (citation["source_id"], citation["page"]) for citation in null_state["citations"]
    ] == [("n5-core-v5.3-pdf", 174)]
    glossary = GlossaryCatalog(_reference_database(tmp_path), rules)
    entry = next(item for item in glossary.entries() if item["id"] == "term:null-state")
    assert entry["description"] == null_state["summary"]
    assert entry["href"] == "/glossary#term-null-state"
    assert entry["embedded"] is True


def test_ammunition_and_label_catalogs_reuse_current_rules_data(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    rules_database = RulesDatabase(rules_path)

    ammunition = RulesRecordCatalog(rules_database, "ammunition")
    ammunition_items = ammunition.list_items()
    assert len(ammunition_items) == 11
    assert {item["slug"] for item in ammunition_items} == {
        "normal",
        "ap",
        "da",
        "eclipse",
        "em",
        "exp",
        "para",
        "shock",
        "smoke",
        "stun",
        "t2",
    }
    shock = ammunition.get_item("shock")
    assert shock is not None
    assert shock["name"] == "Shock Ammunition"
    assert shock["rules"][0]["id"] == "ammunition:shock"

    labels = LabelCatalog(rules_database)
    label_items = labels.list_items()
    assert len(label_items) == 24
    assert {item["slug"] for item in label_items} >= {
        "hackable",
        "negative-feedback",
        "supportware",
    }
    hackable = labels.get_item("hackable")
    assert hackable is not None
    assert hackable["name"] == "Hackable"
    assert "Hacking Programs" in hackable["description"]

    general_rules = RulesRecordCatalog(rules_database, "rules")
    general_rule_items = general_rules.list_items()
    expected_slugs = set(source_rules(root))
    assert len(general_rule_items) == len(expected_slugs)
    assert {item["slug"] for item in general_rule_items} == expected_slugs
    # Keep the reviewed baseline as a floor while accepting source-backed additions.
    assert {
        "access-width",
        "army-retreat",
        "command-token-strategic-use",
        "coordinated-orders",
        "combat-group",
        "deployment-phase",
        "face-to-face-rolls",
        "game-modes",
        "initiative-roll",
        "guts-roll",
        "hacking-area",
        "irregular-order",
        "loss-of-lieutenant",
        "modifiers-explained",
        "order-expenditure-sequence",
        "peripheral-type-ancillary",
        "peripheral-type-control",
        "peripheral-type-cyberplug",
        "peripheral-type-servant",
        "peripheral-type-synchronized",
        "regular-order",
        "reinforcements-extra",
        "saving-rolls",
        "standard-game",
        "special-lieutenant-order",
        "special-dice",
        "special-terrain",
        "specialist-troops-standard",
        "supportware",
        "tactical-order",
        "game-sequence",
        "order-pool",
        "automatic-reaction-order",
        "command-tokens",
    } <= expected_slugs
    specialists = general_rules.get_item("specialist-troops-standard")
    assert specialists is not None
    assert specialists["rules"][0]["id"] == "rule:specialist-troops:standard"
    assert specialists["rules"][0]["facts"]["specialists"]["anyOfSkills"] == [
        "skill:doctor", "skill:engineer", "skill:forward-observer",
        "skill:hacker", "skill:paramedic", "skill:specialist-operative",
        "skill:chain-of-command",
    ]
    assert specialists["used_by"] == [
        {"catalog": "scenarios", "catalog_name": "Scenarios", "name": name,
         "href": f"/scenarios/{slug}"}
        for name, slug in (
            ("Domination", "domination"),
            ("Firefight", "firefight"),
            ("Supplies", "supplies"),
        )
    ]
    assert general_rules.get_item("fireteam-general") is None
    tactical_order = general_rules.get_item("tactical-order")
    assert tactical_order is not None
    assert tactical_order["category"] == "order-type"
    assert tactical_order["category_peers"] == [
        {
            "id": "irregular-order",
            "slug": "irregular-order",
            "name": "Irregular Order",
        },
        {
            "id": "regular-order",
            "slug": "regular-order",
            "name": "Regular Order",
        },
        {
            "id": "special-lieutenant-order",
            "slug": "special-lieutenant-order",
            "name": "Special Lieutenant Order",
        },
    ]
    assert tactical_order["related_category_peers"] == [
        {
            "id": "skill:impetuous",
            "name": "Impetuous",
            "domain": "Skill",
            "public_reference": {"catalog": "skills", "id": "impetuous"},
        }
    ]
    servant = general_rules.get_item("peripheral-type-servant")
    assert servant is not None
    assert servant["rules"][0]["id"] == "rule:peripheral-type:servant"

    assert RulesRecordCatalog(None, "ammunition").list_items() == []
    assert RulesRecordCatalog(None, "rules").list_items() == []
    assert LabelCatalog(None).list_items() == []

def _published_get(
    app: Callable[..., Iterable[bytes]], path: str
) -> tuple[str, bytes]:
    environ: dict = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
    statuses: list[str] = []

    def respond(status: str, _headers: list, _exc_info: object = None) -> None:
        statuses.append(status)

    response = app(environ, respond)
    try:
        body = b"".join(response)
    finally:
        close = getattr(response, "close", None)
        if close is not None:
            close()
    assert len(statuses) == 1, path
    return statuses[0], body


def test_all_published_ammunition_records_reach_normal_browser_routes() -> None:
    """Cross-check every curated Ammunition identity through storage and WSGI."""

    root = Path(__file__).parents[1]
    curated_records = {
        record["id"]: record
        for _, document in load_curated_directory(root / "data/curated")
        for record in document["records"]
        if record["kind"] == "ammunition"
    }
    assert len(curated_records) == 11
    assert source_names(root) == {
        identity.removeprefix("ammunition:"): source["name"]
        for identity, source in curated_records.items()
    }
    assert WIDTHS == (1440, 390, 320)

    rules_path = root / "data/generated/rules.db"
    with sqlite3.connect(rules_path) as connection:
        stored_ids = {
            record_id
            for (record_id,) in connection.execute(
                "SELECT id FROM records WHERE kind = 'ammunition'"
            )
        }
    assert stored_ids == set(curated_records)

    app = create_app(root / "data/generated/infinity.db", rules_database_path=rules_path)

    get = partial(_published_get, app)
    status, body = get("/api/ammunition")
    assert status == "200 OK"
    listed = json.loads(body)["items"]
    assert {f"ammunition:{item['slug']}" for item in listed} == set(curated_records)
    assert len(listed) == len(curated_records)

    status, body = get("/ammunition")
    assert status == "200 OK"
    assert b'data-catalog="ammunition"' in body
    assert b"/static/reference-catalog.js" in body

    for identity, source in sorted(curated_records.items()):
        slug = identity.removeprefix("ammunition:")
        list_item = next(item for item in listed if item["slug"] == slug)
        assert list_item["name"] == source["name"], identity
        assert list_item["description"] == source["summary"], identity

        status, body = get(f"/api/ammunition/{slug}")
        assert status == "200 OK", identity
        detail = json.loads(body)
        assert (detail["slug"], detail["name"], detail["description"]) == (
            slug, source["name"], source["summary"]
        )
        assert len(detail["rules"]) == 1, identity
        rule = detail["rules"][0]
        assert (rule["id"], rule["summary"]) == (identity, source["summary"])
        assert rule.get("facts", {}) == source.get("facts", {}), identity
        assert rule["citations"], identity
        assert {citation["source_id"] for citation in rule["citations"]} >= {
            citation["sourceId"] for citation in source["citations"]
        }, identity

        status, body = get(f"/ammunition/{slug}")
        assert status == "200 OK", identity
        assert b'data-catalog="ammunition"' in body
        assert b"/static/reference-detail.js" in body
        assert b'id="item-content"' in body
        assert b'class="intro-copy developer-only"' in body

    # The real player content is placed in item-content; only metadata uses
    # developer-only styling. A browser interaction check is still required.
    javascript = (root / "src/infinity_db/web/static/reference-detail.js").read_text(
        encoding="utf-8"
    )
    assert "getCatalogItem(catalog, itemId, pageController.signal)" in javascript
    assert "rulesReferenceSection(item.rules)" in javascript
    assert "content.hidden = false;" in javascript


def test_all_published_labels_preserve_curated_vocabulary_and_public_routes() -> None:
    """Verify the current Label vocabulary, not the unrelated rules-record table."""

    root = Path(__file__).parents[1]
    source_rows = {
        (document["collection"]["id"], label["id"], label["name"], label["description"])
        for _, document in load_curated_directory(root / "data/curated")
        if document["collection"]["status"] == "current"
        for label in document["labels"]
    }
    expected: dict[str, tuple[str, str]] = {}
    sources_by_id: dict[str, set[str]] = {}
    for collection_id, label_id, name, description in source_rows:
        if label_id in expected:
            assert expected[label_id] == (name, description), label_id
        expected[label_id] = (name, description)
        sources_by_id.setdefault(label_id, set()).add(collection_id)
    assert len(expected) == 24
    assert label_source_names(root) == {
        label_id: name for label_id, (name, _) in expected.items()
    }
    assert WIDTHS == (1440, 390, 320)
    with pytest.raises(ValueError, match="Unsupported reference catalog"):
        verify("http://127.0.0.1:8000", catalog="invalid")
    with pytest.raises(ValueError, match="Expected 24 reviewed labels entries"):
        verify("http://127.0.0.1:8000", catalog="labels", expected_names={})

    rules_path = root / "data/generated/rules.db"
    with sqlite3.connect(rules_path) as connection:
        stored_rows = set(connection.execute(
            "SELECT l.collection_id, l.id, l.name, l.description FROM labels AS l "
            "JOIN collections AS c ON c.id = l.collection_id "
            "WHERE c.status = 'current'"
        ))
    assert stored_rows == source_rows

    app = create_app(root / "data/generated/infinity.db", rules_database_path=rules_path)
    get = partial(_published_get, app)
    status, body = get("/api/labels")
    assert status == "200 OK"
    items = json.loads(body)["items"]
    assert len(items) == len(expected)
    assert {item["slug"] for item in items} == set(expected)
    assert all(item["id"] == item["slug"] for item in items)

    status, body = get("/labels")
    assert status == "200 OK"
    assert b'data-catalog="labels"' in body
    assert b"/static/reference-catalog.js" in body

    for label_id, (name, description) in sorted(expected.items()):
        listed = next(item for item in items if item["slug"] == label_id)
        assert (listed["name"], listed["description"]) == (name, description), label_id
        status, body = get(f"/api/labels/{label_id}")
        assert status == "200 OK", label_id
        detail = json.loads(body)
        assert (detail["id"], detail["slug"], detail["name"], detail["description"]) == (
            label_id, label_id, name, description
        )
        assert detail["collection"]["id"] in sources_by_id[label_id], label_id
        assert isinstance(detail["description_tokens"], list), label_id
        used_by = detail["used_by"]
        assert len({item["href"] for item in used_by}) == len(used_by), label_id
        assert all(item["href"].startswith("/") for item in used_by), label_id

        status, body = get(f"/labels/{label_id}")
        assert status == "200 OK", label_id
        assert b'data-catalog="labels"' in body
        assert b"/static/reference-detail.js" in body
        assert b'id="item-content"' in body

    script = (root / "src/infinity_db/web/static/reference-detail.js").read_text(
        encoding="utf-8"
    )
    assert "definitionSection(item)" in script
    assert "content.hidden = false;" in script


def test_label_vocabulary_sources_reach_published_details() -> None:
    root = Path(__file__).parents[1]
    document = next(
        doc for _, doc in load_curated_directory(root / "data/curated")
        if doc["collection"]["id"] == "n5-core-v5.3"
    )
    sources = {source["id"]: source for source in document["sources"]}
    expected = []
    for reference in document["vocabularySources"]["labels"]:
        source = sources[reference["sourceId"]]
        expected.append({
            "source_id": source["id"],
            "source_title": source["title"],
            "source_version": source["version"],
            "source_url": source["url"],
            "page": reference.get("page"),
            "member": reference.get("member"),
            "heading": reference["heading"],
            "collection": {
                "id": document["collection"]["id"],
                "title": document["collection"]["title"],
            },
        })
    assert [source["source_id"] for source in expected] == [
        "wiki-en-20260926-200832", "n5-core-v5.3-pdf",
    ]
    assert expected[0]["member"] == "Labels"
    assert expected[1]["page"] == 174

    rules_path = root / "data/generated/rules.db"
    with sqlite3.connect(rules_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (9,)
    rules = RulesDatabase(rules_path)
    labels = rules.current_labels()
    assert len(labels) == len(document["labels"]) == 24
    assert all(label["vocabulary_sources"] == expected for label in labels)

    app = create_app(root / "data/generated/infinity.db", rules_database_path=rules_path)
    for label in labels:
        status, body = _published_get(app, f"/api/labels/{label['id']}")
        assert status == "200 OK", label["id"]
        detail = json.loads(body)
        assert detail["vocabulary_sources"] == expected, label["id"]
        assert "citations" not in detail
    faqs = next(label for label in labels if label["id"] == "faqs")
    assert faqs["description"] == "A label category for FAQ-related rule references."


def test_label_vocabulary_archived_wiki_member_covers_published_headings() -> None:
    root = Path(__file__).parents[1]
    wiki = root / "data/wiki/WIKI-en 20260926-200832.zip"
    if not wiki.is_file():
        pytest.skip("Pinned Label Wiki archive unavailable")
    assert hashlib.sha256(wiki.read_bytes()).hexdigest() == (
        "c0fe18c165473e3f273efd58aa7ecb0ea0d94ee274189de9361aad175b3de987"
    )
    with zipfile.ZipFile(wiki) as archive:
        member = archive.read("Labels")
    assert hashlib.sha256(member).hexdigest() == (
        "3b731a8f3ac150c66b79c4e5f0f57220fe10f257a2b18e7651ef68c2a3840bb9"
    )
    html = member.decode("utf-8")
    assert re.search(r'"wgRevisionId"\s*:\s*4067\b', html)
    headings = _WikiHeadings()
    headings.feed(html)
    document = next(
        doc for _, doc in load_curated_directory(root / "data/curated")
        if doc["collection"]["id"] == "n5-core-v5.3"
    )
    assert {label["name"].casefold() for label in document["labels"]} <= headings.headings


def test_label_vocabulary_sources_keep_collection_scope_and_missing_data(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data/curated")
    core_path, core = next(
        item for item in documents if item[1]["collection"]["id"] == "n5-core-v5.3"
    )
    secondary = deepcopy(core)
    secondary.pop("scenarioCollection", None)
    secondary["collection"] = {
        **secondary["collection"], "id": "test-label-secondary",
        "title": "Secondary Label collection",
    }
    secondary["records"] = []
    secondary["skillTypes"] = []
    secondary["labels"] = [
        deepcopy(next(label for label in core["labels"] if label["id"] == "hackable"))
    ]
    secondary["sources"] = [
        deepcopy(next(source for source in core["sources"] if source["id"] == "n5-core-v5.3-pdf"))
    ]
    secondary["vocabularySources"] = {
        "skillTypes": [],
        "labels": [{"sourceId": "n5-core-v5.3-pdf", "page": 42, "heading": "Test"}],
    }
    unsourced = deepcopy(secondary)
    unsourced["collection"] = {
        **unsourced["collection"], "id": "test-label-unsourced",
        "title": "Unsourced Label collection",
    }
    unsourced["labels"] = [
        {"id": "unsourced-label", "name": "Unsourced Label", "description": "Example."}
    ]
    unsourced["sources"] = []
    unsourced["vocabularySources"]["labels"] = []
    historical = deepcopy(secondary)
    historical["collection"] = {
        **historical["collection"], "id": "test-label-historical",
        "title": "Historical Label collection", "status": "superseded",
    }
    historical["vocabularySources"]["labels"][0]["page"] = 99
    rules_path = tmp_path / "rules-v8.db"
    export_rules_database(
        [
            *documents,
            (core_path.with_name("test-label-secondary.json"), secondary),
            (core_path.with_name("test-label-unsourced.json"), unsourced),
            (core_path.with_name("test-label-historical.json"), historical),
        ],
        rules_path,
        finalize=False,
    )
    rules = RulesDatabase(rules_path)
    rules.validate()
    with sqlite3.connect(rules_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (8,)

    catalog = LabelCatalog(rules)
    detail = catalog.get_item("hackable")
    assert detail is not None
    sources = detail["vocabulary_sources"]
    assert [
        (source["collection"]["id"], source["source_id"], source["page"])
        for source in sources
    ] == [
        ("n5-core-v5.3", "wiki-en-20260926-200832", None),
        ("n5-core-v5.3", "n5-core-v5.3-pdf", 174),
        ("test-label-secondary", "n5-core-v5.3-pdf", 42),
    ]
    assert sources[-1]["collection"]["title"] == "Secondary Label collection"
    other = catalog.get_item("attack")
    assert other is not None and len(other["vocabulary_sources"]) == 2
    unavailable = catalog.get_item("unsourced-label")
    assert unavailable is not None and unavailable["vocabulary_sources"] == []
    sources[0]["source_title"] = "Client mutation"
    fresh = catalog.get_item("hackable")
    assert fresh is not None
    assert fresh["vocabulary_sources"][0]["source_title"] != "Client mutation"

    with sqlite3.connect(rules_path) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            "DELETE FROM sources WHERE collection_id = ? AND id = ?",
            ("test-label-secondary", "n5-core-v5.3-pdf"),
        )
    with pytest.raises(ValueError, match="Unknown Label vocabulary source"):
        RulesDatabase(rules_path).current_labels()


@pytest.mark.parametrize(
    ("filename", "digest", "page", "clause"),
    (
        ("n5-rules-v5.3-en.pdf",
         "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f",
         174, "When deploying its owner during the Deployment Phase"),
        ("n5-rules-v5.3-es.pdf",
         "7f564c864c6f26d6b218a0477c8afeba99da5c56e1a5369bb259f423689bb28f",
         181, "Únicamente durante la Fase de Despliegue"),
        ("n5-rules-v5.2-en.pdf",
         "643ab0b6d7c3e9e5ffbf668543723161f252367e7788af09ec008be19c17851b",
         173, "When deploying its owner during the Deployment Phase"),
    ),
)
def test_v1s082_label_review_pinned_sources(
    filename: str, digest: str, page: int, clause: str,
) -> None:
    """Pin the reviewed versions and preserve the bilingual timing difference."""
    root = Path(__file__).parents[1]
    path = root / "data/pdf/rules" / filename
    if not path.is_file():
        pytest.skip(f"Pinned local PDF unavailable: {filename}")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    pdf = pytest.importorskip("pymupdf")
    with pdf.open(path) as document:
        text = " ".join(document[page - 1].get_text().split())
    assert clause in text
    if filename == "n5-rules-v5.3-es.pdf":
        assert "Los MOD que otorgue son combinables" in text
        assert "Turno Activo y Reactivo" in text
        assert "éste será fijo" in text
    else:
        for phrase in (
            "cannot receive more than one", "Game State Tokens rather than Model",
            "combined with other CC Special Skills", "Active Turn and the Reactive Turn",
            "Partial Cover has no effect", "both allies and enemies",
            "fixed one which will be shown between brackets",
        ):
            assert phrase in text
        labels_text = text.split("LABELS Labels describe", 1)[1].split(
            "TRAITS Traits are", 1,
        )[0]
        headings = re.findall(r"»\s*([^»]+?)\. ", labels_text)
        source_names = {heading.strip() for heading in headings}
        curated = json.loads((root / "data/curated/rules/n5-core-v5.3.json").read_text(
            encoding="utf-8",
        ))
        assert len(source_names) == 23
        assert source_names == {
            label["name"] for label in curated["labels"] if label["id"] != "faqs"
        }
        if filename == "n5-rules-v5.3-en.pdf":
            assert "Dead, Disconnected, Possessed, Sepsitorized, and Unconscious" in text
        else:
            assert "Sepsitorized" not in labels_text


def test_v1s082_label_vocabulary_primary_citation_and_export() -> None:
    root = Path(__file__).parents[1]
    document = next(
        doc for _, doc in load_curated_directory(root / "data/curated")
        if doc["collection"]["id"] == "n5-core-v5.3"
    )
    assert document["vocabularySources"]["labels"] == [
        {"sourceId": "wiki-en-20260926-200832", "heading": "Labels", "member": "Labels"},
        {"sourceId": "n5-core-v5.3-pdf", "page": 174, "heading": "Labels"},
    ]
    with closing(sqlite3.connect(root / "data/generated/rules.db")) as connection:
        assert connection.execute(
            "SELECT source_id, page, heading FROM vocabulary_sources "
            "WHERE collection_id = 'n5-core-v5.3' AND vocabulary = 'labels' "
            "ORDER BY position"
        ).fetchall() == [
            ("wiki-en-20260926-200832", None, "Labels"),
            ("n5-core-v5.3-pdf", 174, "Labels"),
        ]
        assert connection.execute("PRAGMA user_version").fetchone() == (9,)
    assert len(document["labels"]) == 24  # 23 printed Labels plus the Wiki FAQs category.
    assert next(row for row in document["labels"] if row["id"] == "faqs")[
        "description"
    ] == "A label category for FAQ-related rule references."


@pytest.mark.parametrize(
    ("slug", "required", "targets"),
    (
        ("airborne-deployment", ("every Skill carrying this Label",), set()),
        ("assignable-transmutation", (
            "only to a Trooper", "already represented", "at most one",
            "base contact", "State Token", "English rules", "Spanish rules",
        ), {"skill:transmutation", "skill:hidden-deployment", "skill:impersonation",
            "term:state-token"}),
        ("attack", ("cannot be declared against Allies or Neutral", "Models or Markers"),
         set()),
        ("cc-special-skill", ("Silhouette contact", "combine", "Active and Reactive",
                              "unless"), set()),
        ("comms-attack", ("Partial Cover has no effect",), {"skill:reset", "skill:dodge"}),
        ("hackable", ("Characteristic or Label", "either Allies or Enemies",
                      "Each Program"), {"term:peripheral"}),
        ("hostile", ("own Attributes", "Every player", "declare and receive"), set()),
        ("non-reloadable", ("with this Label", "cannot be canceled", "cannot be recovered"),
         {"trait:disposable-x", "state:unloaded"}),
        ("no-roll", ("without a Roll", "If it supplies", "fixed", "brackets"), set()),
        ("null", ("Trooper", "neither an Order nor Victory Points"),
         {"term:null-state", "state:dead", "state:disconnected", "state:possessed",
          "state:sepsitorized", "state:unconscious"}),
        ("private-information", ("possesses a Special Skill or Equipment", "is used",
                                 "game ends"), set()),
        ("superior-deployment", ("outside the Deployment Zone", "every Skill carrying"),
         set()),
    ),
)
def test_v1s082_label_definition_api_qualifications(
    slug: str, required: tuple[str, ...], targets: set[str],
) -> None:
    root = Path(__file__).parents[1]
    app = create_app(root / "data/generated/infinity.db",
                     rules_database_path=root / "data/generated/rules.db")
    status, body = _published_get(app, f"/api/labels/{slug}")
    assert status == "200 OK"
    item = json.loads(body)
    assert item["id"] == item["slug"] == slug
    assert all(phrase in item["description"] for phrase in required), slug
    assert targets <= {
        token["target"] for token in item["description_tokens"]
        if token["type"] == "reference"
    }
    assert all(
        token.get("public_reference")
        for token in item["description_tokens"] if token["type"] == "reference"
    )
    assert len({row["href"] for row in item["used_by"]}) == len(item["used_by"])
    assert all(row["href"].startswith("/") for row in item["used_by"])


def test_all_current_general_rules_preserve_category_scoped_publication() -> None:
    """Audit all published General Rules, including qualified source IDs."""

    root = Path(__file__).parents[1]
    domain = application_domain("rules")
    sources = {
        record["id"]: (document["collection"]["id"], record)
        for _, document in load_curated_directory(root / "data/curated")
        if document["collection"]["status"] == "current"
        for record in document["records"]
        if record_matches_domain(domain, record)
    }
    assert {
        "rule:game-sequence", "rule:order-pool",
        "rule:automatic-reaction-order", "rule:command-tokens",
    } <= set(sources)
    assert sources["rule:reinforcements-extra"][1]["facts"]["category"] == "optional-extra"
    slugs = {
        route_slug_from_qualified_typed_domain_id(
            record_id, expected_domain="rule", context="General Rule source identity"
        ): record_id
        for record_id in sources
    }
    assert len(slugs) == len(sources)
    assert slugs["peripheral-type-servant"] == "rule:peripheral-type:servant"
    assert source_rules(root) == {
        slug: (record_id, sources[record_id][1]["name"])
        for slug, record_id in slugs.items()
    }
    with pytest.raises(ValueError, match="General Rules require a complete"):
        verify(
            "http://127.0.0.1:8000",
            catalog="rules",
            expected_names={
                slug: sources[record_id][1]["name"]
                for slug, record_id in slugs.items()
            },
        )

    rules_path = root / "data/generated/rules.db"
    with sqlite3.connect(rules_path) as connection:
        rows = list(connection.execute(
            "SELECT r.collection_id, r.id, r.name, r.summary, r.facts_json "
            "FROM records AS r JOIN collections AS c ON c.id = r.collection_id "
            "WHERE c.status = 'current' AND r.kind = 'rule'"
        ))
    published = {
        record_id: (collection_id, name, summary, json.loads(facts_json or "{}"))
        for collection_id, record_id, name, summary, facts_json in rows
        if record_matches_domain(
            domain, {"kind": "rule", "facts": json.loads(facts_json or "{}")}
        )
    }
    assert set(published) == set(sources)
    for record_id, (collection_id, record) in sources.items():
        assert published[record_id] == (
            collection_id, record["name"], record["summary"], record.get("facts", {})
        ), record_id

    app = create_app(root / "data/generated/infinity.db", rules_database_path=rules_path)
    get = partial(_published_get, app)
    status, body = get("/api/rules")
    assert status == "200 OK"
    listed = json.loads(body)["items"]
    assert {item["slug"] for item in listed} == set(slugs)
    assert len(listed) == len(slugs)
    status, body = get("/rules")
    assert status == "200 OK"
    assert b'data-catalog="rules"' in body
    assert b"/static/reference-catalog.js" in body

    for slug, record_id in sorted(slugs.items()):
        _, source = sources[record_id]
        item = next(item for item in listed if item["slug"] == slug)
        assert (item["id"], item["name"], item["description"]) == (
            slug, source["name"], source["summary"]
        ), record_id
        status, body = get(f"/api/rules/{slug}")
        assert status == "200 OK", record_id
        detail = json.loads(body)
        assert (detail["slug"], detail["name"], detail["description"]) == (
            slug, source["name"], source["summary"]
        ), record_id
        assert detail["category"] == source["facts"]["category"], record_id
        assert len(detail["rules"]) == 1, record_id
        record = detail["rules"][0]
        assert (record["id"], record["summary"]) == (
            record_id, source["summary"]
        ), record_id
        assert record.get("facts", {}) == source.get("facts", {}), record_id
        assert record["citations"], record_id
        assert {citation["source_id"] for citation in record["citations"]} >= {
            citation["sourceId"] for citation in source["citations"]
        }, record_id
        assert len({peer["slug"] for peer in detail.get("category_peers", [])}) == len(
            detail.get("category_peers", [])
        ), record_id

        status, body = get(f"/rules/{slug}")
        assert status == "200 OK", record_id
        assert b'data-catalog="rules"' in body
        assert b"/static/reference-detail.js" in body
        assert b'id="item-content"' in body

    script = (root / "src/infinity_db/web/static/reference-detail.js").read_text(
        encoding="utf-8"
    )
    assert "rulesReferenceSection(item.rules)" in script
    assert "content.hidden = false;" in script


def test_rules_relation_references_project_source_variants_to_public_routes(
    tmp_path: Path,
) -> None:
    database = _reference_database(tmp_path)
    payload = {
        "rules": [
            {
                "display_relations": [
                    {
                        "record": {
                            "id": "skill:martial-arts-l2",
                            "kind": "skill",
                            "name": "Martial Arts L2",
                            "army_links": [{"entity": "skill", "id": "20"}],
                        }
                    },
                    {
                        "record": {
                            "id": "equipment:hacking-device",
                            "kind": "equipment",
                            "name": "Hacking Device",
                            "army_links": [{"entity": "equipment", "id": "100"}],
                        }
                    },
                    {
                        "record": {
                            "id": "skill:stale-source-variant",
                            "kind": "skill",
                            "name": "Stale source variant",
                            "army_links": [{"entity": "skill", "id": "999"}],
                        }
                    },
                    {
                        "record": {
                            "id": "state:unconscious",
                            "kind": "state",
                            "name": "Unconscious State",
                            "army_links": [],
                        }
                    },
                    {
                        "record": {
                            "id": "ammunition:shock",
                            "kind": "ammunition",
                            "name": "Shock Ammunition",
                            "army_links": [],
                        }
                    },
                    {
                        "record": {
                            "id": "attribute:mov",
                            "kind": "attribute",
                            "name": "Movement (MOV)",
                            "army_links": [],
                        }
                    },
                    {
                        "record": {
                            "id": "term:marker",
                            "kind": "term",
                            "name": "Marker",
                            "army_links": [],
                        }
                    },
                    {
                        "record": {
                            "id": "rule:loss-of-lieutenant",
                            "kind": "rule",
                            "name": "Loss of Lieutenant",
                            "facts": {"category": "basic-rule"},
                            "army_links": [],
                        }
                    },
                ]
            }
        ]
    }

    result = enrich_rule_relation_references(database, payload)
    records = [
        relation["record"]
        for relation in result["rules"][0]["display_relations"]
    ]

    assert records[0]["public_reference"] == {
        "catalog": "skills",
        "id": "martial-arts",
    }
    assert records[1]["public_reference"] == {
        "catalog": "equipment",
        "id": "hacking-device",
    }
    assert "public_reference" not in records[2]
    assert records[3]["public_reference"] == {
        "catalog": "states",
        "id": "unconscious",
    }
    assert records[4]["public_reference"] == {
        "catalog": "ammunition",
        "id": "shock",
    }
    assert records[5]["public_reference"] == {"href": "/glossary#attribute-mov"}
    assert records[6]["public_reference"] == {"href": "/glossary#term-marker"}
    assert records[7]["public_reference"] == {
        "catalog": "rules",
        "id": "loss-of-lieutenant",
    }


def test_peripheral_subtype_relations_resolve_to_general_rules_routes(
    tmp_path: Path,
) -> None:
    database = _reference_database(tmp_path)
    root = Path(__file__).parents[1]
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    rules_database = RulesDatabase(rules_path)

    cyberplug = next(
        record
        for record in rules_database.composed_records_by_kind("skill")
        if record["id"] == "skill:cyberplug"
    )
    result = enrich_rule_relation_references(database, {"rules": [cyberplug]})
    relation = next(
        item
        for item in result["rules"][0]["display_relations"]
        if item["record"]["id"] == "rule:peripheral-type:cyberplug"
    )

    assert relation["presentation"]["label"] == "Can control"
    assert relation["record"]["name"] == "Peripheral (Cyberplug)"
    assert relation["record"]["public_reference"] == {
        "catalog": "rules",
        "id": "peripheral-type-cyberplug",
    }


def test_structured_reference_metadata_is_materialized_without_raw_tables(
    tmp_path: Path,
) -> None:
    database = _reference_database(tmp_path)

    programs = database.list_hacking_programs()
    assert [program["name"] for program in programs] == ["Carbonite", "Zero Pain"]
    assert programs[0]["attack_mod"] == "0"
    assert programs[0]["ps"] == "7"
    assert programs[0]["targets"] == ["TAG", "HI", "REM", "Hacker", "VH"]
    assert programs[0]["skill_types"] == ["short", "aro"]
    assert programs[0]["source_extra_id"] == 13
    assert programs[0]["devices"] == [
        {
            "source_id": 100,
            "id": 100,
            "slug": "hacking-device",
            "name": "Hacking Device",
        },
        {
            "source_id": 101,
            "id": 101,
            "slug": "hacking-device-plus",
            "name": "Hacking Device Plus",
        },
    ]
    assert programs[1]["devices"] == []

    assert database.list_martial_arts_levels()[0] == {
        "position": 1,
        "level": "1",
        "attack_mod": "0",
        "opponent_mod": "-3",
        "ps_mod": "-",
        "burst_mod": "0",
    }
    assert database.list_metachemistry_results() == [
        {"id": 1, "roll": "1-3", "result": "+3 PH"},
        {"id": 4, "roll": "4-5", "result": "Super-Jump"},
    ]
    assert database.list_booty_results() == [
        {"id": 1, "roll": "1-2", "result": "+1 ARM"},
        {"id": 3, "roll": "3-4", "result": "Light Flamethrower"},
    ]

    with sqlite3.connect(database.path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert "metadata_hacking_programs" not in tables
    assert "metadata_martial_arts" not in tables
    assert "metadata_metachemistry" not in tables
    assert "metadata_booty" not in tables
    assert {
        "application_hacking_programs",
        "application_hacking_program_devices",
        "application_hacking_program_targets",
        "application_hacking_program_skill_types",
        "application_martial_arts_levels",
        "application_metachemistry_results",
        "application_booty_results",
    } <= tables


def test_structured_reference_metadata_is_attached_to_existing_skill_details(
    tmp_path: Path,
) -> None:
    database = _reference_database(tmp_path)
    catalog = SkillCatalog(database, None)

    hacker = catalog.get_skill(1000)
    martial_arts = catalog.get_skill(19)
    booty = catalog.get_skill(25)
    metachemistry = catalog.get_skill(55)

    assert hacker is not None
    assert hacker["structured_reference"]["kind"] == "hacking-programs"
    assert hacker["structured_reference"]["rows"][0]["name"] == "Carbonite"

    assert martial_arts is not None
    assert martial_arts["slug"] == "martial-arts"
    assert martial_arts["structured_reference"]["kind"] == "martial-arts"
    assert len(martial_arts["structured_reference"]["rows"]) == 5

    assert booty is not None
    assert booty["structured_reference"] == {
        "kind": "random-chart",
        "title": "Booty chart",
        "rows": [
            {"id": 1, "roll": "1-2", "result": "+1 ARM"},
            {"id": 3, "roll": "3-4", "result": "Light Flamethrower"},
        ],
    }

    assert metachemistry is not None
    assert metachemistry["structured_reference"]["title"] == "MetaChemistry chart"


def test_hacking_program_catalog_composes_army_profiles_with_rules_semantics(
    tmp_path: Path,
) -> None:
    database = _reference_database(tmp_path)
    rules_path = tmp_path / "rules.db"
    root = Path(__file__).parents[1]
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    catalog = HackingProgramCatalog(database, RulesDatabase(rules_path))

    programs = catalog.list_programs()
    assert [program["slug"] for program in programs] == ["carbonite", "zero-pain"]
    carbonite = catalog.get_program("carbonite")
    assert carbonite is not None
    assert carbonite["source_extra_id"] == 13
    assert carbonite["rules"][0]["id"] == "hacking-program:carbonite"
    assert [label["name"] for label in carbonite["rules"][0]["labels"]] == [
        "Comms Attack"
    ]
    assert {
        relation["record"]["id"]
        for relation in carbonite["rules"][0]["display_relations"]
    } == {"state:immobilized-b"}

    zero_pain = catalog.get_program(2)
    assert zero_pain is not None
    assert zero_pain["slug"] == "zero-pain"
    assert zero_pain["devices"] == []
    assert zero_pain["source_extra_id"] == 287

    assert catalog.programs_for_equipment("hacking-device") == [
        {"id": "carbonite", "slug": "carbonite", "name": "Carbonite"}
    ]
    assert catalog.programs_for_equipment("hacking-device-plus") == [
        {"id": "carbonite", "slug": "carbonite", "name": "Carbonite"}
    ]


def test_hacking_program_catalog_remains_available_without_rules_database(
    tmp_path: Path,
) -> None:
    catalog = HackingProgramCatalog(_reference_database(tmp_path), None)
    carbonite = catalog.get_program("carbonite")
    assert carbonite is not None
    assert carbonite["description"] == "DA Ammo. State: IMM-B. Non-Lethal."
    assert "rules" not in carbonite


def test_weapon_glossary_uses_opt_in_army_links_for_routable_definitions(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[1]
    output = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), output)
    rules = RulesDatabase(output)
    database = _reference_database(tmp_path)

    # The bulk query remains lightweight by default. The Glossary opts in
    # for Weapon and Equipment entries to resolve their canonical hosts.
    original = rules.composed_records_by_kind("weapon")
    assert not any(record.get("army_links") for record in original)
    routed = rules.composed_records_by_kind("weapon", include_army_links=True)
    mines = next(record for record in routed if record["id"] == "weapon:mines")
    assert len(mines["army_links"]) == 7
    assert rule_record_public_reference(database, mines) == {
        "href": "/weapons/ap-mine#rule-weapon-mines"
    }

    glossary = GlossaryCatalog(database, rules)
    entries = [entry for entry in glossary.entries() if entry["kind"] == "weapon"]
    # Source-mode-specific definitions are not separate search identities.
    assert len(entries) == sum(
        (record.get("variant_semantics") or {}).get("inheritance") != "source"
        for record in routed
    )
    assert len(entries) == len({entry["id"] for entry in entries})
    by_id = {entry["id"]: entry for entry in entries}
    assert by_id["weapon:mines"]["href"] == "/weapons/ap-mine#rule-weapon-mines"
    assert by_id["weapon:para-mine"]["href"] == "/weapons/para-mine"
    assert by_id["weapon:wildparrot"]["href"] == "/weapons/wildparrot"
    assert "weapon:pt-endgame" not in by_id
    assert all(entry["href"].startswith("/weapons/") for entry in entries)
    assert all(not entry["embedded"] for entry in entries)


def test_equipment_glossary_source_cited_routes_cover_current_concepts() -> None:
    root = Path(__file__).parents[1]
    rules = RulesDatabase(root / "data/generated/rules.db")
    app = create_app(
        root / "data/generated/infinity.db", rules_database_path=rules.path
    )
    records = rules.composed_records_by_kind("equipment", include_army_links=True)
    expected = {
        record["id"]: record
        for record in records
        if (record.get("variant_semantics") or {}).get("inheritance") != "source"
    }
    variants = {record["id"] for record in records} - set(expected)
    assert len(expected) == 31
    status, body = _published_get(app, "/api/glossary")
    assert status == "200 OK"
    items = [item for item in json.loads(body)["items"] if item["kind"] == "equipment"]
    entries = {item["id"]: item for item in items}
    assert len(items) == len(entries)
    assert set(entries) == set(expected)
    assert not variants.intersection(entries)
    assert entries["equipment:cube"]["href"] == "/equipment/cube"
    assert entries["equipment:cube-2"]["href"] == "/equipment/cube-2"
    assert entries["equipment:tinbot"]["href"] == "/equipment/tinbot"
    assert entries["equipment:firewall"]["href"] == "/equipment/firewall"

    fields = ("source_id", "source_version", "page", "member", "section", "heading")
    for identifier, entry in entries.items():
        record = expected[identifier]
        assert entry["description"] == record["summary"]
        assert entry["domain"] == "Equipment"
        assert entry["embedded"] is False
        status, body = _published_get(app, "/api" + entry["href"])
        assert status == "200 OK", identifier
        card = next(row for row in json.loads(body)["rules"] if row["id"] == identifier)
        assert card["summary"] == record["summary"]
        assert card["citations"]
        assert {
            tuple(citation.get(field) for field in fields)
            for citation in card["citations"]
        } == {
            tuple(citation.get(field) for field in fields)
            for citation in record["citations"]
        }, identifier


@pytest.mark.parametrize("valid_ref", ["hacking-device", "100"])
def test_validated_public_reference_filters_stale_equipment_links(
    tmp_path: Path, valid_ref: str,
) -> None:
    database = _reference_database(tmp_path)
    record = {
        "kind": "equipment",
        "id": "equipment:hacking-device",
        "army_links": [
            {"entity": "equipment", "id": "missing-device"},
            {"entity": "equipment", "id": valid_ref},
        ],
    }
    assert rule_record_public_reference(database, record) == {
        "catalog": "equipment", "id": "missing-device"
    }
    assert rule_record_public_reference(database, record, validate_army_links=True) == {
        "catalog": "equipment", "id": "hacking-device"
    }
    record["army_links"].pop()
    assert rule_record_public_reference(database, record, validate_army_links=True) is None

    cube = {
        "kind": "equipment",
        "id": "equipment:cube",
        "army_links": [
            {"entity": "equipment", "id": "missing-device"},
            {"entity": "equipment", "id": "cube"},
        ],
    }
    assert rule_record_public_reference(database, cube, validate_army_links=True) is None
    assert rule_record_public_reference(
        database, cube, validate_army_links=True,
        additional_route_slugs=frozenset({"cube"}),
    ) == {"catalog": "equipment", "id": "cube"}


def test_equipment_glossary_omits_stale_routes_but_keeps_encoded_equipment(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[1]
    database = _reference_database(tmp_path)
    rules_path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(root / "data" / "curated"), rules_path)
    with sqlite3.connect(rules_path) as connection:
        result = connection.execute(
            "UPDATE record_army_links SET external_id = ? "
            "WHERE record_id = ? AND entity = ?",
            ("missing-device", "equipment:hacking-device", "equipment"),
        )
        assert result.rowcount == 1
    rules = RulesDatabase(rules_path)
    entries = {
        item["id"]: item for item in GlossaryCatalog(database, rules).entries()
        if item["kind"] == "equipment"
    }
    assert "equipment:hacking-device" not in entries
    assert entries["equipment:cube"]["href"] == "/equipment/cube"
    assert entries["equipment:cube-2"]["href"] == "/equipment/cube-2"
    assert entries["equipment:firewall"]["href"] == "/equipment/firewall"
    assert "equipment:tinbot-firewall" not in entries

    with sqlite3.connect(rules_path) as connection:
        result = connection.execute(
            "INSERT INTO record_army_links "
            "(collection_id, record_id, position, entity, external_id) "
            "SELECT collection_id, record_id, 1, entity, ? FROM record_army_links "
            "WHERE record_id = ? AND entity = ? AND position = 0",
            ("100", "equipment:hacking-device", "equipment"),
        )
        assert result.rowcount == 1
    entries = {
        item["id"]: item for item in GlossaryCatalog(database, rules).entries()
        if item["kind"] == "equipment"
    }
    assert entries["equipment:hacking-device"]["href"] == "/equipment/hacking-device"


def test_numeric_army_skill_links_resolve_to_public_slugs(tmp_path: Path) -> None:
    database = _reference_database(tmp_path)
    record = {
        "kind": "skill",
        "id": "skill:hacker",
        "army_links": [{"entity": "skill", "id": 1000}],
    }
    expected = {"catalog": "skills", "id": "hacker"}
    assert rule_record_public_reference(database, record) == expected
    assert rule_record_public_reference(None, record) is None
    record["army_links"][0]["id"] = "1000"
    assert rule_record_public_reference(database, record) == expected
    record["army_links"][0]["id"] = "hacker"
    assert rule_record_public_reference(database, record) == expected

    # Common Skills remain accessible as curated definitions in minimal Army
    # snapshots even when their numeric source ID is absent from the catalog.
    missing = {
        "kind": "skill",
        "id": "skill:jump",
        "facts": {"category": "common-skill"},
        "variant_semantics": {"inheritance": "family"},
        "army_links": [{"entity": "skill", "id": 263}],
    }
    assert rule_record_public_reference(database, missing) == {
        "catalog": "skills", "id": "jump",
    }
    missing["variant_semantics"]["inheritance"] = "source"
    assert rule_record_public_reference(database, missing) is None
    missing["variant_semantics"]["inheritance"] = "family"
    missing["facts"]["category"] = "unknown"
    assert rule_record_public_reference(database, missing) is None


def test_shared_weapon_family_reference_targets_its_card() -> None:
    family = {
        "kind": "weapon",
        "id": "weapon:mines",
        "variant_semantics": {"inheritance": "family"},
        "army_links": [
            {"entity": "weapon", "id": "ap-mine"},
            {"entity": "weapon", "id": "e-m-mine"},
        ],
    }
    assert rule_record_public_reference(None, family) == {
        "href": "/weapons/ap-mine#rule-weapon-mines"
    }
    # A weapon-specific rule still links to its Weapon page, not an absent anchor.
    family["army_links"] = [{"entity": "weapon", "id": "cybermine"}]
    assert rule_record_public_reference(None, family) == {
        "catalog": "weapons", "id": "cybermine"
    }
    # Multi-linked source-specific records do not gain an invented rule-card anchor.
    family["variant_semantics"] = {"inheritance": "source"}
    family["army_links"].append({"entity": "weapon", "id": "ap-mine"})
    assert rule_record_public_reference(None, family) == {
        "catalog": "weapons", "id": "cybermine"
    }
