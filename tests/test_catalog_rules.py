import copy
import json
import sqlite3
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.catalog_rules import CatalogRules
from infinity_db.curated import load_curated_directory, load_curated_document
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
    assert "[[term:visibility-zone|Visibility Zones]] to 0" in levels[1]["effects"][0]
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


def test_reviewed_combined_ammunition_critical_is_not_per_component(
    tmp_path: Path,
) -> None:
    """Components retain independent facts; the shared extra roll is not summed."""
    root = Path(__file__).parents[1]
    records = {
        record["id"]: record
        for record in load_curated_document(
            root / "data/curated/rules/n5-core-v5.3.json"
        )["records"]
    }
    refs = WeaponAmmunitionReferences(_rules_database(tmp_path))
    expected = {
        (10, "AP+DA"): ("ap", "da", 2),
        (13, "AP+Exp"): ("ap", "exp", 3),
        (30, "AP+Shock"): ("ap", "shock", 1),
        (40, "AP+T2"): ("ap", "t2", None),
    }
    for (source_id, name), (first, second, rolls) in expected.items():
        composition = refs.composition_for_profile(
            {"ammunition_source_id": source_id, "ammunition": name}
        )
        assert composition is not None
        assert composition["kind"] == "combined"
        assert [part["record_id"] for part in composition["components"]] == [
            f"ammunition:{first}", f"ammunition:{second}"
        ]
        # A Critical is one extra Saving Roll for the *whole* combination.
        # The mapping exposes components but does not calculate Saving Rolls.
        assert "criticalAdditionalSavingRolls" not in composition
        for slug in (first, second):
            assert records[f"ammunition:{slug}"]["facts"]["ammunitionResolution"][
                "criticalAdditionalSavingRolls"
            ] == 1
        if rolls is not None:
            assert records[f"ammunition:{second}"]["facts"]["ammunitionResolution"][
                "rollsPerHit"
            ] == rolls
    assert refs.composition_for_profile(
        {"ammunition_source_id": 10, "ammunition": "ARM+BTS"}
    ) is None


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
        "criticalAdditionalSavingRolls": 1,
        "defenseModifier": {"operation": "halve", "attributes": ["ARM", "BTS"]},
    }
    assert da["facts"]["ammunitionResolution"] == {
        "criticalAdditionalSavingRolls": 1,
        "rollsPerHit": 2,
    }
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
    assert exp["facts"]["ammunitionResolution"] == {
        "criticalAdditionalSavingRolls": 1,
        "rollsPerHit": 3,
    }
    assert para["facts"]["ammunitionResolution"] == {
        "criticalAdditionalSavingRolls": 1,
        "savingRoll": {"attribute": "PH", "modifier": -6, "missingAttribute": "no-effect"},
        "rollsPerHit": 1,
        "stateEffects": [{
            "stateId": "state:immobilized-a", "condition": "failed-saving-roll"
        }],
    }
    assert t2["facts"]["ammunitionResolution"] == {
        "criticalAdditionalSavingRolls": 1,
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


@pytest.mark.parametrize("slug", (
    "normal", "shock", "stun", "smoke", "eclipse",
))
def test_remaining_base_ammunition_facts_are_source_cited_and_published(
    tmp_path: Path, slug: str,
) -> None:
    rules_db = _rules_database(tmp_path)
    record = rules_db.composed_record(f"ammunition:{slug}")
    assert record is not None
    assert record["citations"]
    facts = record["facts"]
    assert ("visibilityZone" in facts) != ("ammunitionResolution" in facts)

    root = Path(__file__).parents[1]
    app = create_app(root / "data/generated/infinity.db", rules_database_path=rules_db.path)
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ["REQUEST_METHOD"] = "GET"
    environ["PATH_INFO"] = f"/api/ammunition/{slug}"
    statuses: list[str] = []
    body = b"".join(app(environ, lambda status, headers, exc_info=None: statuses.append(status)))
    assert statuses == ["200 OK"]
    payload = json.loads(body)
    assert payload["rules"][0]["facts"] == facts

    if slug == "normal":
        assert facts["ammunitionResolution"]["woundsPerFailedSave"] == {
            "hit": 1, "criticalAdditionalRoll": 1,
        }
    elif slug == "shock":
        dead = facts["ammunitionResolution"]["stateEffects"][0]
        assert dead["stateId"] == "state:dead"
        assert dead["targetAttribute"] == {"name": "VITA", "equals": 1}
        assert dead["application"] == "bypass-unconscious"
        assert rules_db.composed_record(dead["stateId"]) is not None
    elif slug == "stun":
        resolution = facts["ammunitionResolution"]
        assert resolution["stateEffects"] == [{
            "stateId": "state:stunned", "condition": "failed-saving-roll",
        }]
        assert resolution["gutsEffect"]["exception"] == "courage-or-equivalent"
        assert rules_db.composed_record("state:stunned") is not None
    else:
        zone = facts["visibilityZone"]
        assert zone["visibility"] == "zero"
        assert zone["multispectralVisor"] == (
            "blocked" if slug == "eclipse" else "can-draw-lof"
        )
        assert "ammunitionResolution" not in facts


def test_combined_saving_roll_review_covers_exact_six_plasma_modes() -> None:
    """The N5.3 Critical ARM rule is independent of Ammunition composition."""
    from infinity_db.database.repository import Database
    from infinity_db.weapon_combined_saving_rolls import (
        WeaponCombinedSavingRolls,
        load_combined_saving_roll_map,
    )

    root = Path(__file__).parents[1]
    database = Database(root / "data/generated/infinity.db")
    resolver = WeaponCombinedSavingRolls()
    mapping = load_combined_saving_roll_map()
    assert set(mapping) == {
        (weapon_id, mode)
        for weapon_id in (40, 111, 113)
        for mode in ("Blast Mode", "Hit Mode")
    }
    for slug in ("plasma-rifle", "plasma-carbine", "plasma-sniper-rifle"):
        weapon = database.get_catalog_item("weapons", slug)
        assert weapon is not None
        assert {profile["mode"] for profile in weapon["profiles"]} == {
            "Blast Mode", "Hit Mode"
        }
        for profile in weapon["profiles"]:
            assert resolver.for_profile(profile) == {
                "kind": "combined-saving-roll",
                "rolls": [
                    {"attribute": "ARM", "count": 1},
                    {"attribute": "BTS", "count": 1},
                ],
                "critical": {"additionalRolls": 1, "attribute": "ARM"},
                "source": {"sourceId": "n5-core-v5.3", "page": 67},
            }
            assert profile["ammunition"] == "N"
    feuerbach = database.get_catalog_item("weapons", "feuerbach")
    assert feuerbach is not None
    assert all(resolver.for_profile(p) is None for p in feuerbach["profiles"])
    plasma = database.get_catalog_item("weapons", "plasma-carbine")
    assert plasma is not None
    changed = plasma["profiles"][0].copy()
    for field, value in (
        ("id", 999), ("name", "Other"), ("mode", "Unknown"),
        ("ammunition", "AP+DA"), ("ammunition_source_id", 10),
        ("saving", "ARM"), ("saving_num", "2"),
    ):
        candidate = changed.copy()
        candidate[field] = value
        assert resolver.for_profile(candidate) is None, field


def test_combined_saving_roll_review_is_published_without_ammunition_composition() -> None:
    from infinity_db.database.repository import Database

    root = Path(__file__).parents[1]
    database = Database(root / "data/generated/infinity.db")
    rules = CatalogRules(RulesDatabase(root / "data/generated/rules.db"))
    plasma = database.get_catalog_item("weapons", "plasma-carbine")
    assert plasma is not None
    enriched = rules.enrich_catalog_item("weapons", plasma)
    for profile in enriched["profiles"]:
        assert profile["combined_saving_roll"]["critical"] == {
            "additionalRolls": 1, "attribute": "ARM"
        }
        assert (profile["saving"], profile["saving_num"]) == (
            "ARM and BTS", "1 and 1"
        )
        assert "ammunition_composition" not in profile
    for variant in enriched["weapon_variants"]:
        for profile in variant.get("profiles", []):
            assert profile["combined_saving_roll"]["kind"] == "combined-saving-roll"
    feuerbach = database.get_catalog_item("weapons", "feuerbach")
    assert feuerbach is not None
    enriched_feuerbach = rules.enrich_catalog_item("weapons", feuerbach)
    assert all("combined_saving_roll" not in p for p in enriched_feuerbach["profiles"])
    assert any("ammunition_composition" in p for p in enriched_feuerbach["profiles"])


@pytest.mark.parametrize("mutation", (
    lambda d: d["critical"].update({"attribute": "BTS"}),
    lambda d: d["critical"].update({"additionalRolls": 2}),
    lambda d: d["critical"].update({"additionalRolls": True}),
    lambda d: d["source"].update({"page": 66}),
    lambda d: d["profiles"][0]["modes"].append("Hit Mode"),
    lambda d: d["profiles"].append(copy.deepcopy(d["profiles"][0])),
    lambda d: d["profiles"][0].update({"saving": "ARM+BTS"}),
    lambda d: d["profiles"][0].update({"weaponId": True}),
))
def test_combined_saving_roll_map_rejects_unsupported_or_ambiguous_inputs(
    tmp_path: Path, mutation: Any,
) -> None:
    from infinity_db.weapon_combined_saving_rolls import load_combined_saving_roll_map

    source = Path(__file__).parents[1] / "config/catalogs/weapon-combined-saving-rolls.json"
    document = json.loads(source.read_text(encoding="utf-8"))
    mutation(document)
    target = tmp_path / "invalid-combined-saving-rolls.json"
    target.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="Combined Saving Roll"):
        load_combined_saving_roll_map(target)


def test_plasma_combined_saving_roll_critical_reaches_weapon_api() -> None:
    root = Path(__file__).parents[1]
    app = create_app(
        root / "data/generated/infinity.db",
        rules_database_path=root / "data/generated/rules.db",
    )

    def detail(slug: str) -> dict[str, Any]:
        environ: dict[str, Any] = {}
        setup_testing_defaults(environ)
        environ["REQUEST_METHOD"] = "GET"
        environ["PATH_INFO"] = f"/api/weapons/{slug}"
        statuses: list[str] = []
        body = b"".join(
            app(environ, lambda status, headers, exc_info=None: statuses.append(status))
        )
        assert statuses == ["200 OK"]
        return json.loads(body)

    for slug in ("plasma-carbine", "plasma-rifle", "plasma-sniper-rifle"):
        result = detail(slug)
        for profile in result["profiles"]:
            assert profile["combined_saving_roll"]["critical"] == {
                "additionalRolls": 1, "attribute": "ARM"
            }
            assert profile["combined_saving_roll"]["source"] == {
                "sourceId": "n5-core-v5.3", "page": 67
            }
            assert (profile["saving"], profile["saving_num"]) == (
                "ARM and BTS", "1 and 1"
            )
            assert "ammunition_composition" not in profile
        for variant in result["weapon_variants"]:
            for profile in variant.get("profiles", []):
                assert profile["combined_saving_roll"]["kind"] == "combined-saving-roll"
    feuerbach = detail("feuerbach")
    for profile in feuerbach["profiles"]:
        assert "combined_saving_roll" not in profile
    burst = next(p for p in feuerbach["profiles"] if p["mode"] == "Burst Mode")
    assert burst["ammunition_composition"]["kind"] == "combined"


def test_immunity_ammunition_boundaries_reach_rules_database(tmp_path: Path) -> None:
    rules_db = _rules_database(tmp_path)
    immunity = rules_db.composed_record("skill:immunity")
    assert immunity is not None
    assert immunity["citations"]
    interaction = immunity["facts"]["immunityInteraction"]
    assert interaction["coveredAmmunition"] == {
        "treatAs": "ammunition:normal",
        "ignore": [
            "special-effects", "saving-roll-attribute-modifiers",
            "saving-roll-count-modifiers",
        ],
    }
    assert interaction["criticalAgainstCoveredAmmunition"] == {
        "additionalSavingRolls": 1,
        "unless": "immunity-critical",
        "rollEffects": "normal-ammunition",
    }
    assert interaction["exceptions"] == {
        "commsAttacks": "immunity-state-only",
        "notNegatedByImmunity": ["trait:non-lethal", "state:stunned"],
    }
    for record_id in ("ammunition:ap", "ammunition:da", "ammunition:exp",
                      "ammunition:shock", "ammunition:t2"):
        record = rules_db.composed_record(record_id)
        assert record is not None
        assert "immunityInteraction" not in record["facts"]

    mapping = load_ammunition_reference_map()
    for name in ("AP+DA", "AP+Exp", "AP+Shock", "AP+T2"):
        source_entry = next(entry for entry in mapping.values() if entry["name"] == name)
        assert "immunityInteraction" not in source_entry
        assert len(source_entry["components"]) == 2


def test_reviewed_combined_immunity_cases_are_explicit_and_source_scoped(
    tmp_path: Path,
) -> None:
    """ARM removes combined effects; AP removes only the reviewed AP component."""
    rules_db = _rules_database(tmp_path)
    immunity = rules_db.composed_record("skill:immunity")
    assert immunity is not None
    source_map = load_ammunition_reference_map()
    facts = immunity["facts"]["immunityInteraction"]
    cases = facts["reviewedCombinedCases"]
    assert [(case["sourceAmmunitionId"], case["when"]["immunity"])
            for case in cases] == [(10, "ARM"), (13, "ARM"), (10, "AP")]
    for case, normal, critical in zip(cases[:2], (2, 3), (3, 4), strict=True):
        source = source_map[case["sourceAmmunitionId"]]
        assert case["sourceAmmunitionName"] == source["name"]
        assert case["components"] == source["components"]
        assert case["when"] == {
            "immunity": "ARM", "savingAttribute": "ARM", "attackClass": "non-comms"
        }
        assert case["withoutImmunity"] == {
            "hitRolls": normal, "criticalRolls": critical
        }
        assert case["withImmunity"] == {
            "hitRolls": 1, "criticalRolls": 2, "treatedAs": "ammunition:normal"
        }
        assert case["evidence"] == "derived-from-pinned-general-rules"
    ap_case = cases[2]
    assert ap_case["sourceAmmunitionName"] == source_map[10]["name"]
    assert ap_case["components"] == source_map[10]["components"]
    assert ap_case["when"] == {
        "immunity": "AP", "savingAttribute": "ARM", "attackClass": "non-comms"
    }
    assert ap_case["withoutImmunity"] == {"hitRolls": 2, "criticalRolls": 3}
    assert ap_case["withImmunity"] == {
        "hitRolls": 2,
        "criticalRolls": 3,
        "treatedAs": "ammunition:da",
        "ignoredComponents": ["ammunition:ap"],
        "remainingComponents": ["ammunition:da"],
    }
    assert ap_case["evidence"] == "derived-from-pinned-general-rules"
    assert {citation["source_version"] for citation in immunity["citations"]} == {
        "5.3", "N5.3 / oldid 3643", "N5.3 / oldid 3000",
        "N5.3 / oldid 3156",
    }
    # The source-owned mapping remains descriptive: no target Immunity is inferred.
    for source_id in (10, 13, 30, 40):
        assert "withImmunity" not in source_map[source_id]


def test_ap_em_rounding_and_t2_critical_die_identification_reach_api(
    tmp_path: Path,
) -> None:
    """Player instructions and pinned sources survive curated publication."""
    rules_db = _rules_database(tmp_path)
    app = create_app(
        Path(__file__).resolve().parents[1] / "data/generated/infinity.db",
        rules_database_path=rules_db.path,
    )
    expected = {
        "ap": {
            "sourcePages": (63, 66),
            "fragments": (
                "round up", "ARM 5 becomes ARM 3", "cannot be reduced below 1"
            ),
        },
        "em": {
            "sourcePages": (64, 64),
            "fragments": (
                "Both Saving Rolls", "rounded up", "BTS 5 becomes BTS 3"
            ),
        },
        "t2": {
            "sourcePages": (67, 67),
            "fragments": (
                "before rolling", "hit roll inflicts 2 Wounds",
                "extra Critical roll inflicts only 1 Wound",
            ),
        },
    }
    for slug, case in expected.items():
        record = rules_db.composed_record(f"ammunition:{slug}")
        assert record is not None
        assert len(record["facts"]["clarifications"]) == 1
        text = record["facts"]["clarifications"][0]
        for fragment in case["fragments"]:
            assert fragment in text
        en_page, es_page = case["sourcePages"]
        assert {
            (source["source_id"], source.get("page"))
            for source in record["citations"]
        } >= {
            ("n5-core-v5.3-pdf", en_page),
            ("n5-core-v5.3-es-pdf", es_page),
        }

        environ: dict[str, Any] = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO=f"/api/ammunition/{slug}", REQUEST_METHOD="GET")
        statuses: list[str] = []
        response = app(
            environ,
            lambda status, headers, exc_info=None, _statuses=statuses: _statuses.append(
                status
            ),
        )
        assert statuses == ["200 OK"]
        payload = json.loads(b"".join(response))
        rule = payload["rules"][0]
        assert rule["facts"]["clarifications"] == record["facts"]["clarifications"]
        assert len(rule["fact_tokens"]["clarifications"]) == 1
        assert rule["facts"]["ammunitionResolution"] == record["facts"][
            "ammunitionResolution"
        ]

    # Keep T2's separate hit/Critical Wound outcomes and AP/E/M modifiers typed.
    t2 = rules_db.composed_record("ammunition:t2")
    assert t2 is not None
    assert t2["facts"]["ammunitionResolution"]["woundsPerFailedSave"] == {
        "hit": 2,
        "criticalAdditionalRoll": 1,
    }
    for slug, attrs in (("ap", ["ARM", "BTS"]), ("em", ["BTS"])):
        ammunition = rules_db.composed_record(f"ammunition:{slug}")
        assert ammunition is not None
        modifier = ammunition["facts"]["ammunitionResolution"]["defenseModifier"]
        assert modifier == {"operation": "halve", "attributes": attrs}


def test_smoke_eclipse_opposition_and_msv_exception_reach_api(
    tmp_path: Path,
) -> None:
    rules_db = _rules_database(tmp_path)
    app = create_app(
        Path(__file__).resolve().parents[1] / "data/generated/infinity.db",
        rules_database_path=rules_db.path,
    )

    for slug, expected_msv in (("smoke", "can-draw-lof"), ("eclipse", "blocked")):
        record = rules_db.composed_record(f"ammunition:{slug}")
        assert record is not None
        clarifications = " ".join(record["facts"]["clarifications"])
        assert "Face to Face" in clarifications
        assert "unopposed Roll" in clarifications
        assert "[[equipment:multispectral-visor|Multispectral Visor]]" in clarifications
        assert "[[skill:dodge|Dodge]]" in clarifications
        assert record["facts"]["visibilityZone"]["multispectralVisor"] == expected_msv
        assert "ammunitionResolution" not in record["facts"]
        assert {
            (citation["source_id"], citation.get("page"))
            for citation in record["citations"]
            if citation["source_id"].endswith("-pdf")
        } >= {
            ("n5-core-v5.3-pdf", 66 if slug == "smoke" else 64),
            ("n5-core-v5.3-es-pdf", 65 if slug == "smoke" else 64),
        }

        environ: dict[str, Any] = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO=f"/api/ammunition/{slug}", REQUEST_METHOD="GET")
        statuses: list[str] = []
        response = app(
            environ,
            lambda status, headers, exc_info=None, _statuses=statuses: _statuses.append(status),
        )
        assert statuses == ["200 OK"]
        payload = json.loads(b"".join(response))
        rule = payload["rules"][0]
        assert len(rule["facts"]["clarifications"]) == 3
        assert len(rule["fact_tokens"]["clarifications"]) == 3
        assert any(
            token["target"] == "equipment:multispectral-visor"
            for tokens in rule["fact_tokens"]["clarifications"]
            for token in tokens
            if token["type"] == "reference"
        )

    smoke = rules_db.composed_record("ammunition:smoke")
    eclipse = rules_db.composed_record("ammunition:eclipse")
    assert smoke is not None and eclipse is not None
    smoke_text = " ".join(smoke["facts"]["clarifications"])
    eclipse_text = " ".join(eclipse["facts"]["clarifications"])
    assert "must win every applicable Face to Face Roll" in smoke_text
    assert "Critical has no additional effect" in smoke_text
    assert "not opposed by the Smoke placement Roll" in smoke_text
    assert "Unlike ordinary [[ammunition:smoke|Smoke]]" in eclipse_text
    assert "Once established" in eclipse_text
    assert "[[term:poor-visibility-zone|Poor Visibility]] MOD" in eclipse_text
    assert "[[trait:reflective|Reflective]]" in eclipse_text


def test_immunity_arm_bts_trait_protection_and_printed_example_reach_api(
    tmp_path: Path,
) -> None:
    rules_db = _rules_database(tmp_path)
    immunity = rules_db.composed_record("skill:immunity")
    assert immunity is not None
    effects = "\n".join(immunity["facts"]["effects"])
    assert "covered non-Comms Attack" in effects
    assert "Immunity (ARM) or (BTS) also ignores" in effects
    assert "cause [[trait:state|States]], inflict Wounds" in effects
    assert (
        "separate from treating Ammunition as [[ammunition:normal|Normal]]" in effects
    )
    assert "ordinary Saving Roll still happens" in effects
    assert "Printed Example 2" not in effects
    assert "The printed [[weapon:flash-pulse|Flash Pulse]] example" not in effects
    assert "For the reviewed [[ammunition:ap|AP]]" not in effects
    clarifications = "\n".join(immunity["facts"]["clarifications"])
    assert "Printed Example 2" in clarifications
    assert "[[trait:arm-0|ARM = 0]]" in clarifications
    assert "[[trait:state|State: Dead]]" in clarifications
    assert "[[state:dead|Dead]]" in clarifications
    assert "using full ARM" in clarifications
    assert "Despite the ordinary protection against State-causing Traits" in clarifications
    assert "[[trait:non-lethal|Non-Lethal]]" in clarifications
    assert "[[state:stunned|Stunned]] only on a failed BTS roll" in clarifications
    assert {
        citation["page"]
        for citation in immunity["citations"]
        if citation["source_id"] == "n5-core-v5.3-pdf"
    } == {95, 96}
    assert {
        citation["page"]
        for citation in immunity["citations"]
        if citation["source_id"] == "n5-core-v5.3-es-pdf"
    } == {99}

    root = Path(__file__).resolve().parents[1]
    app = create_app(
        root / "data/generated/infinity.db", rules_database_path=rules_db.path
    )
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO="/api/skills/immunity", REQUEST_METHOD="GET")
    statuses: list[str] = []
    response = app(
        environ, lambda status, headers, exc_info=None: statuses.append(status)
    )
    payload = json.loads(b"".join(response))
    assert statuses == ["200 OK"]
    assert payload["rules"][0]["id"] == "skill:immunity"
    assert "ordinary Saving Roll still happens" in " ".join(
        payload["rules"][0]["facts"]["effects"]
    )
    assert "Printed Example 2" in " ".join(
        payload["rules"][0]["facts"]["clarifications"]
    )
    clarifications_tokens = payload["rules"][0]["fact_tokens"]["clarifications"]
    assert len(clarifications_tokens) == 3
    assert any(
        token["target"] == "trait:arm-0"
        for token in clarifications_tokens[0]
        if token["type"] == "reference"
    )


def test_flash_pulse_immunity_example_reaches_rules_and_weapon_api(
    tmp_path: Path,
) -> None:
    rules_db = _rules_database(tmp_path)
    immunity = rules_db.composed_record("skill:immunity")
    flash = rules_db.composed_record("weapon:flash-pulse")
    assert immunity is not None and flash is not None
    assert immunity["facts"]["immunityInteraction"]["reviewedWeaponCases"] == [
        {
            "when": {
                "weaponId": "weapon:flash-pulse",
                "immunity": "BTS",
                "savingAttribute": "BTS",
                "attackClass": "non-comms",
            },
            "ammunitionTreatedAs": "ammunition:normal",
            "survivingTraits": ["trait:non-lethal", "trait:state"],
            "stateEffect": {
                "stateId": "state:stunned", "condition": "failed-saving-roll"
            },
            "evidence": "explicit-pinned-wiki-example",
        }
    ]
    assert {relation["record_id"] for relation in flash["relations"]} == {
        "ammunition:stun", "trait:bs-weapon-wip", "trait:non-lethal",
        "trait:state", "state:stunned",
    }
    assert {citation["source_version"] for citation in flash["citations"]} == {
        "5.3", "N5.3 / oldid 4083", "N5.3 / oldid 3643",
        "N5.2 / oldid 3677 (es)", "N5.3 / oldid 3987 (es)",
    }
    assert "Saving Roll remains BTS, not ARM" in flash["summary"]
    assert "explicitly exempts these two Traits" in flash["summary"]
    assert "only if the BTS Saving Roll fails" in flash["summary"]
    assert "two PB/BTS Saving Rolls" in flash["facts"]["sourceNotes"][0]
    assert "Spanish N5.3 PDF Weapon Chart (p. 196) confirms one" in (
        flash["facts"]["sourceNotes"][0]
    )
    assert "Saving Roll stays BTS, not ARM" in " ".join(
        immunity["facts"]["clarifications"]
    )
    assert "explicitly exempts" in immunity["facts"]["restrictions"][1]

    root = Path(__file__).resolve().parents[1]
    app = create_app(root / "data/generated/infinity.db", rules_database_path=rules_db.path)

    def request(path: str) -> tuple[str, bytes]:
        environ: dict[str, Any] = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
        statuses: list[str] = []
        response = app(
            environ, lambda status, headers, exc_info=None: statuses.append(status)
        )
        try:
            body = b"".join(response)
        finally:
            close = getattr(response, "close", None)
            if close is not None:
                close()
        return statuses[0], body

    status, body = request("/api/weapons/flash-pulse")
    assert status == "200 OK"
    item = json.loads(body)
    assert item["slug"] == "flash-pulse"
    assert [rule["id"] for rule in item["rules"]] == ["weapon:flash-pulse"]
    assert any(
        citation["source_version"] == "N5.3 / oldid 4083"
        for citation in item["rules"][0]["citations"]
    )
    assert item["rules"][0]["summary_tokens"]
    assert "Saving Roll remains BTS, not ARM" in item["rules"][0]["summary"]
    assert "two PB/BTS Saving Rolls" in item["rules"][0]["facts"]["sourceNotes"][0]

    status, body = request("/api/skills/immunity")
    assert status == "200 OK"
    payload = json.loads(body)
    assert payload["rules"][0]["facts"]["immunityInteraction"][
        "reviewedWeaponCases"
    ][0]["when"]["weaponId"] == "weapon:flash-pulse"

    status, body = request("/weapons/flash-pulse")
    assert status == "200 OK"
    assert b"InfinityDB" in body


def test_vulnerability_example_is_explicit_and_not_a_component_rule(
    tmp_path: Path,
) -> None:
    rules_db = _rules_database(tmp_path)
    immunity = rules_db.composed_record("skill:immunity")
    vulnerability = rules_db.composed_record("skill:vulnerability")
    assert immunity is not None
    assert vulnerability is not None
    examples = immunity["facts"]["immunityInteraction"]["reviewedVulnerabilityCases"]
    assert examples == [
        {
            "when": {
                "immunity": "Enhanced",
                "vulnerability": "Viral",
                "weaponNameContains": "Viral",
            },
            "result": "cannot-apply-immunity",
            "evidence": "explicit-pinned-wiki-example",
        }
    ]
    assert any(
        citation["source_version"] == "N5.3 / oldid 3156"
        for citation in immunity["citations"]
    )
    assert "Vulnerability (Viral)" in " ".join(vulnerability["facts"]["effects"])
    for source_id in (10, 13, 30, 40):
        # Explicit name-scoped Vulnerability is not an Ammunition-ID lookup.
        assert "reviewedVulnerabilityCases" not in load_ammunition_reference_map()[source_id]


def test_immunity_interaction_is_cited_on_skill_api(tmp_path: Path) -> None:
    rules_db = _rules_database(tmp_path)
    root = Path(__file__).resolve().parents[1]
    app = create_app(root / "data/generated/infinity.db", rules_database_path=rules_db.path)
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ["PATH_INFO"] = "/api/skills/immunity"
    environ["REQUEST_METHOD"] = "GET"
    statuses: list[str] = []
    body = b"".join(
        app(environ, lambda status, headers, exc_info=None: statuses.append(status))
    )
    assert statuses == ["200 OK"]
    rules = json.loads(body)["rules"]
    assert [rule["id"] for rule in rules] == ["skill:immunity"]
    assert rules[0]["facts"]["immunityInteraction"]["criticalAgainstCoveredAmmunition"] == {
        "additionalSavingRolls": 1,
        "unless": "immunity-critical",
        "rollEffects": "normal-ammunition",
    }
    assert any(
        citation["source_version"] == "N5.3 / oldid 3643"
        for citation in rules[0]["citations"]
    )
    assert [case["sourceAmmunitionId"] for case in rules[0]["facts"][
        "immunityInteraction"
    ]["reviewedCombinedCases"]] == [10, 13, 10]
