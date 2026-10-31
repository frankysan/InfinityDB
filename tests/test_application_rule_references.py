from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Iterable
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
    assert len(general_rule_items) == 28
    assert {item["slug"] for item in general_rule_items} == {
        "access-width",
        "army-retreat",
        "command-token-strategic-use",
        "coordinated-orders",
        "combat-group",
        "deployment-phase",
        "face-to-face-rolls",
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
        "saving-rolls",
        "standard-game",
        "special-lieutenant-order",
        "special-dice",
        "special-terrain",
        "specialist-troops-standard",
        "supportware",
        "tactical-order",
    }
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
    assert len(sources) == 28
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
    # only for weapon entries so their canonical Army host can be resolved.
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
