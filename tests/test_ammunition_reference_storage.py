"""P2.4 source-authored Ammunition links in relational Rules v16."""

from __future__ import annotations

import json
import shutil
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest

from infinity_db.ammunition_reference_storage import (
    read_ammunition_references,
    stage_ammunition_references,
    validate_ammunition_reference_snapshot,
)
from infinity_db.catalog_rules import CatalogRules
from infinity_db.combined_saving_roll_storage import stage_combined_saving_rolls
from infinity_db.database.repository import Database
from infinity_db.database_set import validate_database_set
from infinity_db.restriction_chart_storage import stage_restriction_chart
from infinity_db.rules_database import RulesDatabase
from infinity_db.trait_wiki_references import load_trait_wiki_references
from infinity_db.trait_wiki_storage import stage_trait_wiki_links
from infinity_db.variant_usage_storage import stage_variant_usage
from infinity_db.weapon_ammunition_references import (
    WeaponAmmunitionReferences,
    load_ammunition_reference_map,
)
from infinity_db.weapon_combined_saving_rolls import load_combined_saving_roll_map
from infinity_db.weapon_profile_storage import stage_weapon_profile_citations
from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/generated"
ARMY = RELEASE / "infinity.db"
CONFIG = ROOT / "config/catalogs/weapon-ammunition-references.json"


@pytest.fixture(scope="module")
def v16(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("v16-ammunition-references")
    rules = directory / "rules.db"
    shutil.copyfile(RELEASE / "rules.db", rules)
    shutil.copyfile(ARMY, directory / "infinity.db")
    mapping = load_ammunition_reference_map(CONFIG)
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
                connection, json.loads((
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
            stage_ammunition_references(connection, mapping, ARMY)
            connection.execute("PRAGMA user_version=16")
            connection.execute(
                "UPDATE __rules_metadata SET value='16' WHERE key='formatVersion'"
            )
            connection.execute(
                "UPDATE __rules_metadata SET value='18' "
                "WHERE key='databaseCompatibilityVersion'"
            )
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    return rules, mapping


def test_full_reviewed_mapping_round_trip_and_database_health(v16) -> None:
    path, expected = v16
    assert len(expected) == 16
    assert sum("components" in entry for entry in expected.values()) == 5
    RulesDatabase(path).validate()
    assert RulesDatabase(path).ammunition_references_payload(ARMY) == expected
    with sqlite3.connect(path) as connection:
        validate_ammunition_reference_snapshot(connection)
        assert read_ammunition_references(connection, ARMY) == expected
        assert connection.execute(
            "SELECT COUNT(*) FROM weapon_ammunition_links"
        ).fetchone()[0] == 16
        assert connection.execute(
            "SELECT COUNT(*) FROM weapon_ammunition_components"
        ).fetchone()[0] == 10
    report = validate_database_set(path.parent)
    assert report["layout"] == "v16-two-file"
    assert report["ammunitionReferences"] == 16
    assert set(report["sha256"]) == {"infinity.db", "rules.db"}


def test_v16_player_api_parity_without_runtime_json_reads(v16, monkeypatch) -> None:
    import infinity_db.weapon_ammunition_references as adapter

    path, expected = v16
    previous = create_app(ARMY, rules_database_path=RELEASE / "rules.db")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("v16 must not read maintained Ammunition JSON")

    monkeypatch.setattr(adapter, "load_ammunition_reference_map", forbidden)
    current = create_app(ARMY, rules_database_path=path)
    for slug in (
        "feuerbach", "missile-launcher", "uragan-mrl", "ap-t2-cc-weapon",
        "plasma-rifle", "shock-mine",
    ):
        url = f"http://ammunition.test/api/weapons/{slug}"
        status, _, body = wsgi_response(current, url)
        previous_status, _, previous_body = wsgi_response(previous, url)
        assert status == previous_status == 200
        assert json.loads(body) == json.loads(previous_body)
    assert RulesDatabase(path).ammunition_references_payload() == expected


def test_all_16_identity_and_ordered_components_preserved(v16) -> None:
    path, expected = v16
    refs = WeaponAmmunitionReferences(RulesDatabase(path))
    old = WeaponAmmunitionReferences(RulesDatabase(RELEASE / "rules.db"))
    for source_id, entry in expected.items():
        profile = {"ammunition_source_id": source_id, "ammunition": entry["name"]}
        assert refs.for_profile(profile) == old.for_profile(profile)
        assert refs.effects_for_profile(profile) == old.effects_for_profile(profile)
        assert refs.composition_for_profile(profile) == old.composition_for_profile(profile)
        assert refs.for_profile({**profile, "ammunition": "unreviewed"}) is None
    database = Database(ARMY)
    for slug in ("feuerbach", "uragan-mrl", "plasma-rifle"):
        raw = database.get_catalog_item("weapons", slug)
        assert raw is not None
        assert CatalogRules(RulesDatabase(path)).enrich_catalog_item("weapons", raw) == (
            CatalogRules(RulesDatabase(RELEASE / "rules.db")).enrich_catalog_item(
                "weapons", raw,
            )
        )


@pytest.mark.parametrize("mutation", (
    "missing", "extra", "source-name", "combined-order", "unknown-target", "broken-segment",
))
def test_stage_rejects_source_drift(v16, tmp_path: Path, mutation: str) -> None:
    original, reviewed = v16
    path = tmp_path / "rules.db"
    shutil.copyfile(original, path)
    mapping = deepcopy(reviewed)
    if mutation == "missing":
        del mapping[10]
    elif mutation == "extra":
        mapping[9999] = deepcopy(mapping[10])
    elif mutation == "source-name":
        mapping[10]["name"] = "AP/DA"
    elif mutation == "combined-order":
        mapping[10]["components"].reverse()
    elif mutation == "unknown-target":
        mapping[3]["segments"][0]["ruleId"] = "ammunition:missing"
    else:
        mapping[10]["segments"].pop()
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE weapon_ammunition_components")
        connection.execute("DROP TABLE weapon_ammunition_segments")
        connection.execute("DROP TABLE weapon_ammunition_links")
        connection.execute("DROP TABLE weapon_ammunition_reference_metadata")
        connection.execute("PRAGMA user_version=15")
        with pytest.raises(ValueError, match="(?i)ammunition"):
            stage_ammunition_references(connection, mapping, ARMY)


@pytest.mark.parametrize("mutation", (
    "missing-link", "label", "source", "army", "fingerprint", "segment", "component",
))
def test_read_rejects_corrupt_relational_data(v16, tmp_path: Path, mutation: str) -> None:
    original, _ = v16
    path = tmp_path / "rules.db"
    shutil.copyfile(original, path)
    with sqlite3.connect(path) as connection:
        if mutation == "missing-link":
            connection.execute("DELETE FROM weapon_ammunition_links WHERE ammunition_source_id=29")
        elif mutation == "label":
            connection.execute(
                "UPDATE weapon_ammunition_links SET source_name='invented' "
                "WHERE ammunition_source_id=10"
            )
        elif mutation == "source":
            connection.execute(
                "UPDATE weapon_ammunition_reference_metadata SET source_id='n5-other'"
            )
        elif mutation == "army":
            connection.execute(
                "UPDATE weapon_ammunition_reference_metadata SET army_database_sha256=?",
                ("0" * 64,),
            )
        elif mutation == "fingerprint":
            connection.execute(
                "UPDATE weapon_ammunition_reference_metadata SET content_sha256=?",
                ("0" * 64,),
            )
        elif mutation == "segment":
            connection.execute(
                "UPDATE weapon_ammunition_segments SET text='/' "
                "WHERE ammunition_source_id=10 AND position=1"
            )
        else:
            connection.execute(
                "UPDATE weapon_ammunition_components SET rule_id='ammunition:shock' "
                "WHERE ammunition_source_id=10 AND position=1"
            )
        with pytest.raises(ValueError, match="(?i)ammunition"):
            read_ammunition_references(connection, ARMY)
    if mutation != "army":
        with pytest.raises(ValueError):
            RulesDatabase(path).validate()


def test_previous_releases_keep_reviewed_json_adapter(v16) -> None:
    path, expected = v16
    assert RulesDatabase(RELEASE / "rules.db").ammunition_references_payload() is None
    assert RulesDatabase(path).ammunition_references_payload(ARMY) == expected
    assert load_ammunition_reference_map(CONFIG) == expected
