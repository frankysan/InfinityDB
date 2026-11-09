"""Rules v17: exact reviewed Weapon Property vocabulary and Army source profiles."""

from __future__ import annotations

import json
import shutil
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest

from infinity_db.ammunition_reference_storage import stage_ammunition_references
from infinity_db.combined_saving_roll_storage import stage_combined_saving_rolls
from infinity_db.database.repository import Database
from infinity_db.database_set import validate_database_set
from infinity_db.restriction_chart_storage import stage_restriction_chart
from infinity_db.rules_database import RulesDatabase
from infinity_db.trait_wiki_references import load_trait_wiki_references
from infinity_db.trait_wiki_storage import stage_trait_wiki_links
from infinity_db.variant_usage_storage import stage_variant_usage
from infinity_db.weapon_ammunition_references import load_ammunition_reference_map
from infinity_db.weapon_combined_saving_rolls import load_combined_saving_roll_map
from infinity_db.weapon_profile_storage import stage_weapon_profile_citations
from infinity_db.weapon_properties import WeaponProperties, load_weapon_properties
from infinity_db.weapon_property_storage import (
    read_weapon_properties,
    stage_weapon_properties,
    validate_weapon_property_snapshot,
)
from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/generated"
ARMY = RELEASE / "infinity.db"
CONFIG = ROOT / "config/catalogs/weapon-properties.json"


@pytest.fixture(scope="module")
def v17(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[dict]]:
    directory = tmp_path_factory.mktemp("v17-property-reference")
    rules = directory / "rules.db"
    shutil.copyfile(RELEASE / "rules.db", rules)
    shutil.copyfile(ARMY, directory / "infinity.db")
    entries = load_weapon_properties(CONFIG)
    with sqlite3.connect(rules) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        with connection:
            stage_variant_usage(
                connection,
                json.loads((RELEASE / "variant-usage.json").read_text(encoding="utf-8")),
            )
            stage_weapon_profile_citations(
                connection,
                json.loads(
                    (RELEASE / "weapon-profile-sources.json").read_text(encoding="utf-8")
                ),
                ARMY,
            )
            connection.execute("PRAGMA user_version=12")
            stage_restriction_chart(
                connection,
                json.loads((
                    ROOT / "src/infinity_db/web/static/restrictions-reference.json"
                ).read_text(encoding="utf-8")),
            )
            connection.execute("PRAGMA user_version=13")
            stage_trait_wiki_links(
                connection,
                load_trait_wiki_references(
                    ROOT / "config/catalogs/trait-wiki-references.json"
                ),
            )
            connection.execute("PRAGMA user_version=14")
            stage_combined_saving_rolls(
                connection,
                load_combined_saving_roll_map(
                    ROOT / "config/catalogs/weapon-combined-saving-rolls.json"
                ),
                ARMY,
            )
            connection.execute("PRAGMA user_version=15")
            stage_ammunition_references(
                connection,
                load_ammunition_reference_map(
                    ROOT / "config/catalogs/weapon-ammunition-references.json"
                ),
                ARMY,
            )
            connection.execute("PRAGMA user_version=16")
            stage_weapon_properties(connection, entries, ARMY)
            connection.execute("PRAGMA user_version=17")
            connection.execute(
                "UPDATE __rules_metadata SET value='17' WHERE key='formatVersion'"
            )
            connection.execute(
                "UPDATE __rules_metadata SET value='19' "
                "WHERE key='databaseCompatibilityVersion'"
            )
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    return rules, entries


def test_source_order_and_relational_round_trip(v17) -> None:
    path, source = v17
    rules = RulesDatabase(path)
    rules.validate()
    assert len(source) == 12
    assert rules.weapon_properties_payload(ARMY) == source
    with sqlite3.connect(path) as connection:
        validate_weapon_property_snapshot(connection)
        assert read_weapon_properties(connection, ARMY) == source
        assert connection.execute(
            "SELECT COUNT(*) FROM weapon_properties"
        ).fetchone()[0] == 12
        assert connection.execute(
            "SELECT COUNT(*) FROM weapon_property_origins"
        ).fetchone()[0] == sum(len(item["origins"]) for item in source)
        assert connection.execute(
            "SELECT COUNT(*) FROM weapon_property_profiles"
        ).fetchone()[0] == sum(len(item["profiles"]) for item in source)
        assert connection.execute(
            "SELECT COUNT(*) FROM weapon_property_profile_traits"
        ).fetchone()[0] == sum(
            len(profile["traits"]) for item in source for profile in item["profiles"]
        )
    report = validate_database_set(path.parent)
    assert report["layout"] == "v17-two-file"
    assert report["weaponProperties"] == 12
    assert set(report["sha256"]) == {"infinity.db", "rules.db"}


def test_v17_glossary_search_and_weapon_api_parity_without_json_reads(
    v17, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import infinity_db.weapon_properties as source_module

    path, source = v17
    previous = create_app(ARMY, rules_database_path=RELEASE / "rules.db")
    routes = (
        "/api/glossary", "/api/search?q=plasma", "/api/search?q=viral",
        "/api/weapons/plasma-rifle", "/api/weapons/viral-rifle",
        "/api/weapons/silenced-pistol", "/api/weapons/feuerbach",
        "/api/weapons/ap-t2-cc-weapon", "/api/weapons/monofilament-mine",
    )
    baseline = {
        route: wsgi_response(previous, f"http://properties.test{route}")
        for route in routes
    }

    def forbidden(*_args, **_kwargs):
        raise AssertionError("v17 runtime must not read Weapon Property JSON")

    monkeypatch.setattr(source_module, "load_weapon_properties", forbidden)
    current = create_app(ARMY, rules_database_path=path)
    for route in routes:
        status, _, body = wsgi_response(current, f"http://properties.test{route}")
        previous_status, _, previous_body = baseline[route]
        assert (status, json.loads(body)) == (previous_status, json.loads(previous_body))
        assert status == 200
    assert RulesDatabase(path).weapon_properties_payload(ARMY) == source


def test_v17_source_profile_matching_is_still_exact(v17) -> None:
    path, source = v17
    properties = WeaponProperties(RulesDatabase(path), database=Database(ARMY))
    assert len(properties.entries()) == 12
    weapon = Database(ARMY).get_catalog_item("weapons", "silenced-pistol")
    assert weapon is not None
    reviewed = weapon["profiles"][0]
    assert [item["id"] for item in properties.for_profile(reviewed)] == [
        "weapon-property:ap-shock", "weapon-property:silenced",
    ]
    for field, alternate in (("id", 999), ("mode", "Blast Mode"),
                             ("saving", "BTS"), ("traits", [])):
        changed = deepcopy(reviewed)
        changed[field] = alternate
        assert properties.for_profile(changed) == []
    assert RulesDatabase(RELEASE / "rules.db").weapon_properties_payload() is None
    assert source == load_weapon_properties(CONFIG)


@pytest.mark.parametrize("mutation", (
    "missing", "duplicate", "origin", "profile-name", "profile-traits",
    "profile-ammo", "empty-summary",
))
def test_stage_rejects_maintained_source_drift(v17, tmp_path: Path, mutation: str) -> None:
    original, source = v17
    path = tmp_path / "rules.db"
    shutil.copyfile(original, path)
    entries = deepcopy(source)
    if mutation == "missing":
        entries.pop()
    elif mutation == "duplicate":
        entries.append(deepcopy(entries[0]))
    elif mutation == "origin":
        entries[0]["origins"][0]["recordId"] = "ammunition:unknown"
    elif mutation == "profile-name":
        entries[0]["profiles"][0]["weaponName"] = "Other"
    elif mutation == "profile-traits":
        entries[0]["profiles"][0]["traits"] = ["Changed"]
    elif mutation == "profile-ammo":
        entries[0]["profiles"][0]["ammunitionSourceId"] = 999
    else:
        entries[0]["summary"] = ""
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version=16")
        with pytest.raises(ValueError, match="(?i)weapon propert"):
            stage_weapon_properties(connection, entries, ARMY)


@pytest.mark.parametrize("mutation", (
    "summary", "origin", "missing-profile", "trait", "fingerprint",
    "source", "army-sha",
))
def test_reader_rejects_corrupted_relational_mapping(v17, tmp_path: Path, mutation: str) -> None:
    original, _ = v17
    path = tmp_path / "rules.db"
    shutil.copyfile(original, path)
    with sqlite3.connect(path) as connection:
        if mutation == "summary":
            connection.execute(
                "UPDATE weapon_properties SET summary='unreviewed' WHERE id='plasma'"
            )
        elif mutation == "origin":
            connection.execute(
                "UPDATE weapon_property_origins SET rule_collection_id='other' "
                "WHERE property_id='plasma' AND record_id IS NOT NULL"
            )
        elif mutation == "missing-profile":
            connection.execute(
                "DELETE FROM weapon_property_profiles "
                "WHERE property_id='plasma' AND position=0"
            )
        elif mutation == "trait":
            connection.execute(
                "UPDATE weapon_property_profile_traits SET text='unreviewed' "
                "WHERE property_id='plasma' AND profile_position=0 AND position=0"
            )
        elif mutation == "fingerprint":
            connection.execute(
                "UPDATE weapon_property_metadata SET content_sha256=?",
                ("0" * 64,),
            )
        elif mutation == "source":
            connection.execute(
                "UPDATE weapon_property_metadata SET source_id='other'"
            )
        else:
            connection.execute(
                "UPDATE weapon_property_metadata SET army_database_sha256=?",
                ("0" * 64,),
            )
        with pytest.raises(ValueError, match="(?i)weapon propert"):
            read_weapon_properties(connection, ARMY)
    if mutation != "army-sha":
        with pytest.raises(ValueError):
            RulesDatabase(path).validate()
