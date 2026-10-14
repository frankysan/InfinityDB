"""Weapon Properties retain source-profile identity and canonical rules ownership."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.catalog_rules import CatalogRules
from infinity_db.database.repository import Database
from infinity_db.glossary_catalog import GlossaryCatalog
from infinity_db.rules_database import RulesDatabase
from infinity_db.weapon_properties import WeaponProperties, load_weapon_properties
from infinity_db.web.app import create_app

ROOT = Path(__file__).resolve().parents[1]
ARMY_PATH = ROOT / "data/generated/infinity.db"
RULES_PATH = ROOT / "data/generated/rules.db"


def _services():
    database = Database(ARMY_PATH)
    rules = RulesDatabase(RULES_PATH)
    return database, rules, WeaponProperties(rules)


def test_weapon_properties_have_distinct_explicit_rules_origins() -> None:
    database, rules, properties = _services()
    del database
    assert len(properties.entries()) == 12
    entries = {item["id"]: item for item in properties.entries()}
    viral = entries["weapon-property:viral"]
    assert any(origin["recordId"] == "trait:bioweapon" for origin in viral["origins"])
    assert any(origin["recordId"] == "ammunition:normal" for origin in viral["origins"])
    assert any(origin["role"] == "name-dependent-exception" for origin in viral["origins"])
    mono = entries["weapon-property:monofilament"]
    assert any(o.get("recordId") == "state:dead" for o in mono["origins"])
    assert any(o.get("recordId") == "skill:immunity" for o in mono["origins"])
    silent = entries["weapon-property:silenced"]
    assert any(o.get("recordId") == "trait:silent-x" for o in silent["origins"])
    plasma = entries["weapon-property:plasma"]
    assert any("Combined Saving Roll" in origin.get("sourceSection", "")
               for origin in plasma["origins"])
    assert any(origin.get("recordId") == "rule:saving-rolls" for origin in plasma["origins"])
    for entry in entries.values():
        for origin in entry["origins"]:
            if "recordId" in origin:
                assert rules.composed_record(origin["recordId"]) is not None
    glossary = GlossaryCatalog(Database(ARMY_PATH), rules).embedded_entries()
    assert {entry["id"] for entry in glossary if entry["kind"] == "weapon-property"} == set(entries)


def test_weapon_property_profiles_are_exact_and_mode_scoped() -> None:
    database, rules, properties = _services()
    catalog = CatalogRules(rules)

    def profiles(slug):
        item = database.get_catalog_item("weapons", slug)
        assert item is not None
        return catalog.enrich_catalog_item("weapons", item)["profiles"]

    assert all(
        [p["id"] for p in properties.for_profile(profile)] == ["weapon-property:plasma"]
        for profile in profiles("plasma-carbine")
    )
    assert [p["id"] for p in properties.for_profile(profiles("viral-rifle")[0])] == [
        "weapon-property:viral"
    ]
    viral_mine = profiles("viral-mine")[0]
    assert (
        viral_mine["ammunition"], viral_mine["saving"], viral_mine["saving_num"]
    ) == ("N", "BTS", "1")
    assert [p["id"] for p in viral_mine["weapon_properties"]] == [
        "weapon-property:viral"
    ]
    assert "ammunition_composition" not in viral_mine
    assert [p["id"] for p in properties.for_profile(viral_mine)] == [
        "weapon-property:viral"
    ]
    assert [p["id"] for p in properties.for_profile(profiles("breaker-pistol")[0])] == [
        "weapon-property:breaker"
    ]
    assert [p["id"] for p in properties.for_profile(profiles("k1-sniper-rifle")[0])] == [
        "weapon-property:k1"
    ]
    for profile in profiles("multi-rifle"):
        assert [p["id"] for p in profile["weapon_properties"]] == ["weapon-property:multi"]
    feuerbach = {p["mode"]: p for p in profiles("feuerbach")}
    assert [p["id"] for p in feuerbach["Burst Mode"]["weapon_properties"]] == [
        "weapon-property:ap-da"
    ]
    assert "weapon_properties" not in feuerbach["Explosive Mode"]
    assert [p["id"] for p in profiles("silenced-pistol")[0]["weapon_properties"]] == [
        "weapon-property:ap-shock", "weapon-property:silenced"
    ]
    for slug in ("monofilament-cc-weapon", "monofilament-mine"):
        profile = profiles(slug)[0]
        assert [p["id"] for p in profile["weapon_properties"]] == [
            "weapon-property:monofilament"
        ]
        assert (profile["ammunition"], profile["saving"], profile["saving_num"]) == (
            "N", "ARM=0", "1"
        )
    source_item = database.get_catalog_item("weapons", "viral-rifle")
    assert source_item is not None
    original = source_item["profiles"][0]
    for field, value in (("id", 999), ("mode", "CC Mode"),
                         ("saving", "ARM"), ("traits", [])):
        modified = copy.deepcopy(original)
        modified[field] = value
        assert properties.for_profile(modified) == []


@pytest.mark.parametrize("mutate", (
    lambda d: d["properties"][0].update({"unexpected": 1}),
    lambda d: d["properties"][0]["origins"][0].update({"role": ""}),
    lambda d: d["properties"][0]["origins"][0].update({"domain": "Weapon Traits"}),
    lambda d: d["properties"][1]["profiles"][0].update({"weaponId": True}),
    lambda d: d["properties"][0]["profiles"].append(
        copy.deepcopy(d["properties"][0]["profiles"][0])
    ),
    lambda d: d["properties"].append(copy.deepcopy(d["properties"][0])),
))
def test_weapon_properties_reject_invalid_curated_contract(tmp_path: Path, mutate) -> None:
    path = ROOT / "config/catalogs/weapon-properties.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    mutate(document)
    candidate = tmp_path / "weapon-properties.json"
    candidate.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="Weapon Propert"):
        load_weapon_properties(candidate)


def test_weapon_properties_are_searchable_and_linked_from_weapon_api() -> None:
    app = create_app(ARMY_PATH, rules_database_path=RULES_PATH)

    def request(path: str, query: str = ""):
        environ = {}
        setup_testing_defaults(environ)
        environ["REQUEST_METHOD"] = "GET"
        environ["PATH_INFO"] = path
        environ["QUERY_STRING"] = query
        statuses = []
        body = b"".join(
            app(environ, lambda status, headers, exc_info=None: statuses.append(status))
        )
        assert statuses == ["200 OK"]
        return json.loads(body)

    glossary = request("/api/glossary")["items"]
    plasma = next(item for item in glossary if item["id"] == "weapon-property:plasma")
    assert plasma["href"] == "/glossary#weapon-property-plasma"
    assert any(origin["domain"] == "Ammunition" for origin in plasma["origins"])
    matches = request("/api/search", "q=Plasma")["items"]
    assert any(item["domain"] == "Weapon Property" and
               item["href"] == "/glossary#weapon-property-plasma" for item in matches)
    viral = request("/api/weapons/viral-rifle")
    assert viral["profiles"][0]["weapon_properties"][0]["id"] == "weapon-property:viral"
    assert viral["profiles"][0]["ammunition"] == "N"
    assert "ammunition_composition" not in viral["profiles"][0]
    plasma_weapon = request("/api/weapons/plasma-carbine")
    assert all("ammunition_composition" not in p for p in plasma_weapon["profiles"])
    assert all(p["weapon_properties"][0]["id"] == "weapon-property:plasma"
               for p in plasma_weapon["profiles"])


def test_every_reviewed_property_source_profile_still_matches_army() -> None:
    """Review must reopen when pinned Weapon identity, mode or Traits drift."""
    import sqlite3

    source = load_weapon_properties()
    connection = sqlite3.connect(ARMY_PATH)
    connection.row_factory = sqlite3.Row
    profiles = {
        (r["id"], r["mode"]): r
        for r in connection.execute("SELECT * FROM metadata_weapons")
    }
    for entry in source:
        for signature in entry["profiles"]:
            key = signature["weaponId"], signature["mode"]
            assert key in profiles, (entry["id"], key)
            profile = profiles[key]
            assert profile["name"] == signature["weaponName"]
            assert profile["ammunition"] == signature["ammunitionSourceId"]
            assert profile["saving"] == signature["saving"]
            assert profile["savingNum"] == signature["savingNum"]
            assert json.loads(profile["properties"]) == signature["traits"]
    connection.close()


def test_curated_weapon_property_links_resolve_with_previews() -> None:
    from infinity_db.maintained_text import parse_maintained_text
    from infinity_db.maintained_text_references import maintained_text_tokens

    database, rules, _ = _services()
    for slug in ("monofilament", "silenced", "viral", "plasma"):
        target = f"weapon-property:{slug}"
        assert parse_maintained_text(f"[[{target}]]")[0]["target"] == target
        tokens = maintained_text_tokens(database, rules, f"[[{target}]]")
        assert tokens is not None
        assert tokens[0]["public_reference"] == {
            "href": f"/glossary#weapon-property-{slug}"
        }
        assert tokens[0]["preview_tokens"][0]["text"]
    with pytest.raises(ValueError, match="not current"):
        maintained_text_tokens(database, rules, "[[weapon-property:unknown]]")


def test_published_weapon_rules_link_to_shared_properties() -> None:
    from infinity_db.maintained_text_references import maintained_text_tokens

    database, rules, _ = _services()
    for record_id, expected in (
        ("weapon:viral-cc-weapon", "viral"),
        ("weapon:viral-sniper-rifle", "viral"),
        ("weapon:plasma-sniper-rifle", "plasma"),
        ("weapon:silenced-pistol", "silenced"),
    ):
        record = rules.composed_record(record_id)
        assert record is not None
        tokens = maintained_text_tokens(database, rules, record["summary"])
        assert tokens is not None
        assert any(
            token["type"] == "reference"
            and token["target"] == f"weapon-property:{expected}"
            for token in tokens
        ), record_id
    immunity = rules.composed_record("skill:immunity")
    assert immunity is not None
    assert "weapon-property:monofilament" in json.dumps(immunity["facts"])


def test_rules_build_rejects_unknown_weapon_property_reference(tmp_path: Path) -> None:
    from infinity_db.curated import load_curated_directory
    from infinity_db.rules_database import export_rules_database

    documents = load_curated_directory(ROOT / "data/curated")
    path, document = documents[0]
    replacement = copy.deepcopy(document)
    replacement["records"][0]["summary"] += " [[weapon-property:unknown]]"
    documents[0] = path, replacement
    with pytest.raises(ValueError, match="does not resolve to a current semantic record"):
        export_rules_database(documents, tmp_path / "invalid-rules.db", finalize=False)


def test_n_em_property_reuses_both_rules_without_inferred_rolls() -> None:
    """The N5.3 printed combination is not a separate E/M Ammunition type."""
    from infinity_db.weapon_ammunition_references import load_ammunition_reference_map

    mapping = load_ammunition_reference_map()
    assert mapping[5] == {
        "name": "N+E/M",
        "segments": [
            {"text": "N", "ruleId": "ammunition:normal"},
            {"text": "+"},
            {"text": "E/M", "ruleId": "ammunition:em"},
        ],
        "components": ["ammunition:normal", "ammunition:em"],
    }
    database, rules, registry = _services()
    property_entry = next(
        entry for entry in registry.entries() if entry["id"] == "weapon-property:n-em"
    )
    assert [origin["recordId"] for origin in property_entry["origins"]
            if "recordId" in origin] == [
        "ammunition:normal", "ammunition:em", "rule:saving-rolls"
    ]
    assert any("p. 67" in origin.get("sourceSection", "")
               for origin in property_entry["origins"])
    assert "Wounds" in property_entry["summary"]
    assert "Critical adds one" in property_entry["summary"]

    weapon = database.get_catalog_item("weapons", "e-m-cc-weapon")
    assert weapon is not None
    profile = CatalogRules(rules).enrich_catalog_item("weapons", weapon)["profiles"][0]
    assert (profile["ammunition"], profile["saving"], profile["saving_num"]) == (
        "N+E/M", "BTS/2", "2"
    )
    assert profile["traits"] == ["CC", "[**]"]
    assert [part["record_id"] for part in profile["ammunition_composition"]["components"]] == [
        "ammunition:normal", "ammunition:em"
    ]
    assert [part["record_id"] for part in profile["ammunition_effects"]] == [
        "ammunition:normal", "ammunition:em"
    ]
    assert [entry["id"] for entry in profile["weapon_properties"]] == [
        "weapon-property:n-em"
    ]
    assert "ammunitionResolution" not in profile
    assert "combined_saving_roll" not in profile
    for field, alternate in (("ammunition", "E/M"), ("ammunition_source_id", 14),
                             ("saving_num", "1"), ("mode", "E/Mitter")):
        changed = profile.copy()
        changed[field] = alternate
        assert registry.for_profile(changed) == []

    curated = rules.composed_record("weapon:e-m-cc-weapon")
    assert curated is not None
    assert "weapon-property:n-em" in curated["summary"]
    assert {citation["page"] for citation in curated["citations"]} >= {67, 177}
    assert all(citation["source_id"] == "n5-core-v5.3-pdf"
               for citation in curated["citations"])


def test_e_m_source_exceptions_are_not_implicitly_composed() -> None:
    import sqlite3

    database, rules, registry = _services()
    emitter = database.get_catalog_item("weapons", "e-mitter")
    assert emitter is not None
    profile = CatalogRules(rules).enrich_catalog_item("weapons", emitter)["profiles"][0]
    assert (profile["ammunition"], profile["saving"], profile["saving_num"]) == (
        "E/M", "BTS/2", "2"
    )
    assert all(item["id"] != "weapon-property:n-em"
               for item in profile.get("weapon_properties", []))
    assert "ammunition_composition" not in profile

    with sqlite3.connect(ARMY_PATH) as source:
        special = source.execute(
            "SELECT name, mode, ammunition, saving, savingNum FROM metadata_weapons "
            "WHERE id = 226 AND mode = 'E/Mitter'"
        ).fetchone()
    # Imported Army mode differs from the usual E/M ammunition roll count.
    assert special == ("Armed Turret", "E/Mitter", 14, "BTS/2", "1")
    assert not any(
        item["id"] == "weapon-property:em" for item in registry.entries()
    )


def test_armed_turret_emitter_source_discrepancy_remains_visible() -> None:
    """Do not turn an Army/PDF disagreement into an E/M ammunition exception."""
    import sqlite3

    with sqlite3.connect(ARMY_PATH) as db:
        turret = db.execute(
            "SELECT ammunition, saving, savingNum FROM metadata_weapons "
            "WHERE id = 226 AND mode = 'E/Mitter'"
        ).fetchone()
        emitter = db.execute(
            "SELECT ammunition, saving, savingNum FROM metadata_weapons "
            "WHERE id = 25 AND mode IS NULL"
        ).fetchone()
    assert turret == (14, "BTS/2", "1")
    assert emitter == (14, "BTS/2", "2")

    rules = RulesDatabase(RULES_PATH)
    record = rules.composed_record("weapon:armed-turret")
    assert record is not None
    assert "Unresolved source conflict" in record["summary"]
    assert "one BTS/2 Saving Roll" in record["summary"]
    assert "two" in record["summary"]
    assert "[[weapon:e-mitter|E/Mitter]]" in record["summary"]
    assert "[[ammunition:em|E/M Ammunition]]" in record["summary"]
    assert [(citation["source_id"], citation["page"]) for citation in record["citations"]] == [
        ("n5-core-v5.3-pdf", 70),
        ("n5-core-v5.3-pdf", 186),
        ("n5-core-v5.3-es-pdf", 195),
    ]
    assert record["facts"]["specialProfile"]["stats"][-1] == ["S", "2"]


def test_breaker_marksman_metadata_only_weapon_is_public_without_unit_usage() -> None:
    """REA-044: Army source 225 has no usage row but has a reviewed public identity."""
    import sqlite3

    database, rules, properties = _services()
    with sqlite3.connect(ARMY_PATH) as source:
        assert source.execute("SELECT COUNT(*) FROM weapons WHERE id=225").fetchone()[0] == 0
        assert source.execute(
            "SELECT name FROM metadata_weapons WHERE id=225"
        ).fetchone()[0] == "Breaker Marksman Rifle"

    assert database.application_catalog_id("weapons", 225) == 225
    assert database.application_catalog_id("weapons", "breaker-marksman-rifle") == 225
    assert database.application_slug("weapons", 225) == "breaker-marksman-rifle"
    entries = [entry for entry in database.list_catalog_items("weapons")
               if entry["id"] == 225]
    assert len(entries) == 1
    assert (entries[0]["name"], entries[0]["category"],
            entries[0]["source_ids"], entries[0]["use_count"]) == (
        "Breaker Marksman Rifle", "Marksman Rifles", [225], 0
    )
    item = database.get_catalog_item("weapons", "breaker-marksman-rifle")
    assert item is not None
    assert item == database.get_catalog_item("weapons", 225)
    assert item["variants"] == []
    assert len(item["profiles"]) == 1
    profile = item["profiles"][0]
    assert (profile["id"], profile["name"], profile["ammunition"],
            profile["ammunition_source_id"], profile["burst"], profile["damage"],
            profile["saving"], profile["saving_num"], profile["traits"]) == (
        225, "Breaker Marksman Rifle", "AP", 3, "3", "7",
        "BTS/2", "1", ["Suppressive Fire"]
    )
    assert profile["ranges"]["short"] == {"max": 20, "mod": "-3"}
    assert profile["ranges"]["med"] == {"max": 60, "mod": "+3"}
    assert profile["ranges"]["long"] == {"max": 100, "mod": "-3"}
    assert profile["ranges"]["max"] == {"max": 120, "mod": "-6"}
    assert [prop["id"] for prop in properties.for_profile(profile)] == [
        "weapon-property:breaker"
    ]
    enriched = CatalogRules(rules).enrich_catalog_item("weapons", item)
    assert enriched["profiles"][0]["ammunition_effects"][0]["record_id"] == "ammunition:ap"
    assert "weapon-property:breaker" in [
        prop["id"] for prop in enriched["profiles"][0]["weapon_properties"]
    ]
    curated = rules.composed_record("weapon:breaker-marksman-rifle")
    assert curated is not None
    assert "weapon-property:breaker" in curated["summary"]
    assert "Sniper Rifle" in str(curated["facts"]["sourceNotes"])
    assert any(citation["page"] == 180 for citation in curated["citations"])
    assert database.get_catalog_item("weapons", "breaker-sniper-rifle") is None


def test_reviewed_metadata_only_weapon_publication_requires_source_signature() -> None:
    """A changed source or missing record cannot silently become a new Weapon."""
    import sqlite3

    from infinity_db.database.application_catalogs import (
        _reviewed_metadata_only_weapons,
    )

    with sqlite3.connect(":memory:") as connection:
        connection.execute("ATTACH DATABASE ? AS army", (str(ARMY_PATH),))
        connection.execute(
            "CREATE TABLE metadata_weapons AS "
            "SELECT * FROM army.metadata_weapons WHERE id=225"
        )
        connection.execute("CREATE TABLE weapons (id INTEGER)")
        entries = _reviewed_metadata_only_weapons(connection)
        assert [(entry["id"], entry["category"]) for entry in entries] == [
            (225, "Marksman Rifles")
        ]
        connection.execute("UPDATE metadata_weapons SET savingNum='2' WHERE id=225")
        with pytest.raises(ValueError, match="source profile drift"):
            _reviewed_metadata_only_weapons(connection)
        connection.execute("UPDATE metadata_weapons SET savingNum='1' WHERE id=225")
        connection.execute("INSERT INTO weapons (id) VALUES (225)")
        assert _reviewed_metadata_only_weapons(connection) == []
        connection.execute("DELETE FROM weapons")
        connection.execute("DELETE FROM metadata_weapons")
        assert _reviewed_metadata_only_weapons(connection) == []


def test_reviewed_metadata_only_weapon_config_rejects_unexpected_fields(
    tmp_path: Path,
) -> None:
    from infinity_db.database.application_catalogs import (
        DEFAULT_METADATA_ONLY_WEAPONS,
        _reviewed_metadata_only_weapons,
    )

    document = json.loads(DEFAULT_METADATA_ONLY_WEAPONS.read_text(encoding="utf-8"))
    document["weapons"][0]["unreviewed"] = True
    invalid = tmp_path / "invalid.json"
    invalid.write_text(json.dumps(document), encoding="utf-8")
    import sqlite3

    with sqlite3.connect(":memory:") as connection:
        with pytest.raises(ValueError, match="metadata-only Weapon publication"):
            _reviewed_metadata_only_weapons(connection, invalid)
