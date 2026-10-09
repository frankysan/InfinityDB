import copy
import json
import sqlite3
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.catalog_rules import CatalogRules
from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import RulesDatabase, export_rules_database
from infinity_db.weapon_ammunition_references import (
    WeaponAmmunitionReferences,
    load_ammunition_reference_map,
)
from infinity_db.web import create_app


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
    levels = rule["facts"]["levels"]
    assert [level["level"] for level in levels] == [1, 2, 3]
    assert "Zero Visibility Zones" in levels[0]["effects"][2]
    assert "Visibility Zones to 0" in levels[1]["effects"][0]
    assert "automatically succeeds" in levels[2]["effects"][3]
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
    documents = load_curated_directory(root / "data" / "curated")
    current = next(
        document
        for _, document in documents
        if document["collection"]["id"] == "n5-core-v5.3"
    )
    hacking_programs = next(
        item
        for item in documents
        if item[1]["collection"]["id"] == "n5-hacking-programs-v5.3"
    )
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
    export_rules_database(
        [(root / "curated.json", document), hacking_programs], rules_path
    )
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


def test_weapon_source_mode_rules_do_not_leak_between_same_id_profiles(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    core_path, core = next(
        (path, document) for path, document in documents
        if document["collection"]["id"] == "n5-core-v5.3"
    )
    test_core = copy.deepcopy(core)
    # Keep this synthetic fixture independent of the now-published Kobra records.
    test_core["records"] = [
        record for record in test_core["records"]
        if record["id"] not in {"weapon:kobra-pistol", "weapon:kobra-pistol-cc"}
    ]
    shared = {
        "kind": "weapon",
        "scope": {"game": "N5", "seasons": ["current"]},
        "citations": [{"sourceId": "n5-core-v5.3-pdf", "page": 182}],
        "composition": {"role": "definition"},
        "review": {"status": "reviewed", "reviewedOn": "2026-10-08"},
    }
    test_core["records"].extend(
        [
        {
            **shared, "id": "weapon:kobra-pistol-test",
            "name": "Kobra test shared", "summary": "Synthetic shared reference.",
            "armyLinks": [{"entity": "weapon", "id": "kobra-pistol"}],
            "variantSemantics": {"inheritance": "family"},
        },
        {
            **shared, "id": "weapon:kobra-pistol-cc-test",
            "name": "Kobra CC test", "summary": "Synthetic CC-only reference.",
            "armyLinks": [{"entity": "weapon", "id": 221}],
            "variantSemantics": {"inheritance": "source", "sourceMode": "CC Mode"},
            "relations": [{"type": "variant-of", "recordId": "weapon:kobra-pistol-test"}],
        },
        ]
    )
    path = tmp_path / "rules.db"
    export_rules_database(
        [(core_path, test_core), *(entry for entry in documents if entry[0] != core_path)],
        path,
    )
    rules = RulesDatabase(path)
    record = rules.composed_records_for_army_link("weapon", 221)
    assert next(rule for rule in record if rule["id"] == "weapon:kobra-pistol-cc-test")[
        "variant_semantics"
    ] == {"inheritance": "source", "source_mode": "CC Mode"}
    # Exact-source variant labels are separate from per-mode rules.
    assert 221 not in rules.catalog_source_variant_semantics("weapon")

    def profiles() -> list[dict]:
        return [
            {"id": 221, "mode": "BS Mode", "ammunition": "Shock"},
            {"id": 221, "mode": "CC Mode", "ammunition": "DA"},
        ]

    item = {
        "id": 221, "name": "Kobra Pistol", "slug": "kobra-pistol",
        "profiles": profiles(),
        "weapon_variants": [{"id": 221, "name": "Kobra Pistol", "profiles": profiles()}],
        "variants": [{"item_id": 221, "item_name": "Kobra Pistol", "units": [], "extras": []}],
    }
    result = CatalogRules(rules).enrich_catalog_item("weapons", item)
    assert [rule["id"] for rule in result["rules"]] == ["weapon:kobra-pistol-test"]
    assert "rules" not in result["variants"][0]
    assert "source_variant" not in result["variants"][0]
    for field in ("profiles", "weapon_variants"):
        rendered = (
            result[field] if field == "profiles" else result[field][0]["profiles"]
        )
        assert "rules" not in rendered[0]
        assert [rule["id"] for rule in rendered[1]["rules"]] == [
            "weapon:kobra-pistol-cc-test"
        ]
    assert item["profiles"][1].get("rules") is None

    # Confirm the HTTP API uses the same exact-mode enrichment without changing
    # the imported Army profiles or contaminating the other mode.
    app = create_app(
        root / "data/generated/infinity.db", rules_database_path=path
    )
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO="/api/weapons/kobra-pistol", REQUEST_METHOD="GET")
    statuses: list[str] = []

    def start_response(
        status: str, headers: list[tuple[str, str]], exc_info: Any = None
    ) -> None:
        statuses.append(status)

    response = app(environ, start_response)
    try:
        payload = json.loads(b"".join(response))
    finally:
        close = getattr(response, "close", None)
        if close:
            close()
    assert statuses == ["200 OK"]
    assert "rules" not in payload["profiles"][0]
    assert [rule["id"] for rule in payload["profiles"][1]["rules"]] == [
        "weapon:kobra-pistol-cc-test"
    ]
    assert "rules" not in payload["weapon_variants"][0]["profiles"][0]
    assert [
        rule["id"] for rule in payload["weapon_variants"][0]["profiles"][1]["rules"]
    ] == ["weapon:kobra-pistol-cc-test"]


def test_reviewed_ammunition_references_preserve_exact_army_identity(tmp_path: Path) -> None:
    mapping = load_ammunition_reference_map()
    assert len(mapping) == 15
    refs = WeaponAmmunitionReferences(_rules_database(tmp_path))
    assert refs.for_profile({"ammunition_source_id": 10, "ammunition": "AP+DA"}) == [
        {"text": "AP", "public_reference": {"catalog": "ammunition", "id": "ap"}},
        {"text": "+"},
        {"text": "DA", "public_reference": {"catalog": "ammunition", "id": "da"}},
    ]
    assert refs.composition_for_profile({"ammunition_source_id": 10, "ammunition": "AP+DA"}) == {
        "kind": "combined",
        "components": [
            {
                "record_id": "ammunition:ap",
                "public_reference": {"catalog": "ammunition", "id": "ap"},
            },
            {
                "record_id": "ammunition:da",
                "public_reference": {"catalog": "ammunition", "id": "da"},
            },
        ],
    }
    fresh = refs.composition_for_profile({"ammunition_source_id": 10, "ammunition": "AP+DA"})
    assert fresh is not None
    fresh["components"][0]["public_reference"]["id"] = "unrelated"
    unchanged = refs.composition_for_profile({"ammunition_source_id": 10, "ammunition": "AP+DA"})
    assert unchanged is not None
    assert unchanged["components"][0]["public_reference"]["id"] == "ap"
    assert refs.composition_for_profile({"ammunition_source_id": 3, "ammunition": "AP"}) is None
    assert refs.for_profile({"ammunition_source_id": 10, "ammunition": "AP/DA"}) is None
    assert refs.composition_for_profile({"ammunition_source_id": 10, "ammunition": "AP/DA"}) is None
    assert refs.for_profile({"ammunition_source_id": 17, "ammunition": "AP/DA"}) is None
    assert refs.for_profile({"ammunition_source_id": 0, "ammunition": "--"}) is None

    # A maintained mapping must exactly reconstruct the source notation.
    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps({
        "format": "InfinityDB weapon ammunition references",
        "version": 2,
        "sourceEntries": {"10": {
            "name": "AP+DA",
            "segments": [{"text": "AP", "ruleId": "ammunition:ap"}],
        }},
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="reproduce source name"):
        load_ammunition_reference_map(invalid)


@pytest.mark.parametrize(
    ("source_name", "components"),
    [
        ("AP+DA", ["ammunition:ap", "ammunition:shock"]),
        ("AP/DA", ["ammunition:ap", "ammunition:da"]),
        ("AP+DA", ["ammunition:ap", "ammunition:ap"]),
    ],
)
def test_combined_ammunition_source_requires_exact_component_order(
    tmp_path: Path, source_name: str, components: list[str]
) -> None:
    config = {
        "format": "InfinityDB weapon ammunition references",
        "version": 2,
        "sourceEntries": {
            "10": {
                "name": source_name,
                "segments": [
                    {"text": "AP", "ruleId": "ammunition:ap"},
                    {"text": "+" if "+" in source_name else "/"},
                    {"text": "DA", "ruleId": "ammunition:da"},
                ],
                "components": components,
            }
        },
    }
    path = tmp_path / "invalid-composition.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="ordered, linked components"):
        load_ammunition_reference_map(path)


def test_combined_ammunition_components_are_not_inferred_from_roll_notation(
    tmp_path: Path,
) -> None:
    references = WeaponAmmunitionReferences(_rules_database(tmp_path))
    source = {
        "ammunition_source_id": 13,
        "ammunition": "AP+Exp",
        "saving": "ARM/2",
        "saving_num": "3",
    }
    composition = references.composition_for_profile(source)
    assert composition is not None
    assert [part["record_id"] for part in composition["components"]] == [
        "ammunition:ap", "ammunition:exp"
    ]
    assert source["saving"] == "ARM/2"
    assert source["saving_num"] == "3"
    assert references.composition_for_profile({**source, "ammunition_source_id": 17}) is None
    assert references.composition_for_profile({**source, "ammunition": "AP/Exp"}) is None


def test_reviewed_ammunition_source_names_match_published_army_snapshot() -> None:
    root = Path(__file__).resolve().parents[1]
    with sqlite3.connect(root / "data/generated/infinity.db") as connection:
        published = dict(connection.execute("SELECT id, name FROM metadata_ammunitions"))
        source_count = connection.execute("SELECT COUNT(*) FROM metadata_weapons").fetchone()[0]
        reviewed_ids = tuple(load_ammunition_reference_map())
        reviewed_count = connection.execute(
            "SELECT COUNT(*) FROM metadata_weapons WHERE ammunition IN ("
            + ", ".join("?" for _ in reviewed_ids) + ")",
            reviewed_ids,
        ).fetchone()[0]
    assert source_count >= reviewed_count
    assert reviewed_count >= len(reviewed_ids)
    for source_id, entry in load_ammunition_reference_map().items():
        assert published[source_id] == entry["name"]


def test_ammunition_resolution_pilot_preserves_separate_source_operations(
    tmp_path: Path,
) -> None:
    """Typed base effects, source composition, and saving syntax stay independent."""
    rules_db = _rules_database(tmp_path)
    ap = rules_db.composed_record("ammunition:ap")
    da = rules_db.composed_record("ammunition:da")
    em = rules_db.composed_record("ammunition:em")
    assert ap is not None and da is not None and em is not None
    assert ap["facts"]["ammunitionResolution"] == {
        "defenseModifier": {"operation": "halve", "attributes": ["ARM", "BTS"]}
    }
    assert da["facts"]["ammunitionResolution"] == {"rollsPerHit": 2}
    assert em["facts"]["ammunitionResolution"]["stateEffects"] == [
        {"stateId": "state:isolated", "condition": "failed-saving-roll"},
        {
            "stateId": "state:immobilized-b",
            "condition": "failed-saving-roll",
            "targetTypes": ["HI", "TAG", "REM", "VH"],
        },
    ]
    for effect in em["facts"]["ammunitionResolution"]["stateEffects"]:
        state = rules_db.composed_record(effect["stateId"])
        assert state is not None and state["kind"] == "state"

    exp = rules_db.composed_record("ammunition:exp")
    para = rules_db.composed_record("ammunition:para")
    t2 = rules_db.composed_record("ammunition:t2")
    assert exp is not None and para is not None and t2 is not None
    assert exp["facts"]["ammunitionResolution"] == {"rollsPerHit": 3}
    assert para["facts"]["ammunitionResolution"] == {
        "savingRoll": {"attribute": "PH", "modifier": -6, "missingAttribute": "no-effect"},
        "rollsPerHit": 1,
        "stateEffects": [{
            "stateId": "state:immobilized-a", "condition": "failed-saving-roll"
        }],
    }
    assert t2["facts"]["ammunitionResolution"] == {
        "woundsPerFailedSave": {"hit": 2, "criticalAdditionalRoll": 1}
    }
    assert rules_db.composed_record("state:immobilized-a") is not None

    root = Path(__file__).parents[1]
    app = create_app(root / "data/generated/infinity.db", rules_database_path=rules_db.path)

    def detail(path: str) -> dict[str, Any]:
        environ: dict[str, Any] = {}
        setup_testing_defaults(environ)
        environ["REQUEST_METHOD"] = "GET"
        environ["PATH_INFO"] = path
        statuses: list[str] = []
        body = b"".join(
            app(environ, lambda status, headers, exc_info=None: statuses.append(status))
        )
        assert statuses == ["200 OK"]
        return json.loads(body)

    for slug, record in (
        ("ap", ap), ("da", da), ("em", em),
        ("exp", exp), ("para", para), ("t2", t2),
    ):
        ammunition_detail = detail(f"/api/ammunition/{slug}")
        assert ammunition_detail["rules"][0]["facts"]["ammunitionResolution"] == (
            record["facts"]["ammunitionResolution"]
        )
        assert ammunition_detail["rules"][0]["citations"]

    para_rules = detail("/api/ammunition/para")["rules"]
    assert para_rules[0]["facts"]["ammunitionResolution"]["stateEffects"][0][
        "condition"
    ] == "failed-saving-roll"
    assert detail("/api/ammunition/t2")["rules"][0]["facts"][
        "ammunitionResolution"
    ]["woundsPerFailedSave"]["criticalAdditionalRoll"] == 1

    feuerbach = detail("/api/weapons/feuerbach")
    burst = next(profile for profile in feuerbach["profiles"] if profile["mode"] == "Burst Mode")
    assert [part["record_id"] for part in burst["ammunition_composition"]["components"]] == [
        "ammunition:ap", "ammunition:da"
    ]
    assert (burst["saving"], burst["saving_num"]) == ("ARM/2", "2")
    assert "ammunitionResolution" not in burst

    plasma = detail("/api/weapons/plasma-carbine")
    assert all(profile["ammunition"] == "N" for profile in plasma["profiles"])
    assert all("ammunition_composition" not in profile for profile in plasma["profiles"])
    assert all(
        (profile["saving"], profile["saving_num"]) == ("ARM and BTS", "1 and 1")
        for profile in plasma["profiles"]
    )
