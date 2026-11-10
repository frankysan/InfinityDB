"""Rules v15 reviewed Combined Saving Roll annotations, exact-profile source parity."""

from __future__ import annotations

import json
import shutil
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest
from storage_fixture_support import copy_base_rules, variant_publication, weapon_publication

from infinity_db.catalog_rules import CatalogRules
from infinity_db.combined_saving_roll_storage import (
    read_combined_saving_rolls,
    stage_combined_saving_rolls,
    validate_combined_saving_roll_snapshot,
)
from infinity_db.database.repository import Database
from infinity_db.database_set import validate_database_set
from infinity_db.restriction_chart_storage import stage_restriction_chart
from infinity_db.rules_database import RulesDatabase
from infinity_db.trait_wiki_references import load_trait_wiki_references
from infinity_db.trait_wiki_storage import stage_trait_wiki_links
from infinity_db.variant_usage_storage import stage_variant_usage
from infinity_db.weapon_combined_saving_rolls import (
    WeaponCombinedSavingRolls,
    load_combined_saving_roll_map,
)
from infinity_db.weapon_profile_storage import stage_weapon_profile_citations
from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/generated"
ARMY = RELEASE / "army.db"
CONFIG = ROOT / "config/catalogs/weapon-combined-saving-rolls.json"


@pytest.fixture(scope="module")
def v15(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("v15-saving-roll-profiles")
    rules = directory / "rules_n5.db"
    copy_base_rules(rules)
    shutil.copyfile(ARMY, directory / "army.db")
    mapping = load_combined_saving_roll_map(CONFIG)
    with sqlite3.connect(rules) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        with connection:
            stage_variant_usage(
                connection,
                variant_publication(),
            )
            stage_weapon_profile_citations(
                connection,
                weapon_publication(),
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
            stage_combined_saving_rolls(connection, mapping, ARMY)
            connection.execute("PRAGMA user_version=15")
            connection.execute(
                "UPDATE __rules_metadata SET value='15' WHERE key='formatVersion'"
            )
            connection.execute(
                "UPDATE __rules_metadata SET value='17' "
                "WHERE key='databaseCompatibilityVersion'"
            )
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    return rules, mapping


def test_six_modes_are_relational_and_source_matched(v15) -> None:
    path, expected = v15
    RulesDatabase(path).validate()
    assert RulesDatabase(path).combined_saving_rolls_payload(ARMY) == expected
    with sqlite3.connect(path) as connection:
        validate_combined_saving_roll_snapshot(connection)
        assert read_combined_saving_rolls(connection, ARMY) == expected
        assert connection.execute(
            "SELECT COUNT(*) FROM weapon_combined_saving_roll_profiles"
        ).fetchone()[0] == 6
    report = validate_database_set(path.parent)
    assert report["layout"] == "v15-two-file"
    assert report["combinedSavingRollProfiles"] == 6
    assert set(report["sha256"]) == {"army.db", "rules_n5.db"}


def test_exact_plasma_profile_and_api_parity_without_json_reads(v15, monkeypatch) -> None:
    import infinity_db.weapon_combined_saving_rolls as adapter

    rules, _mapping = v15
    previous = create_app(ARMY, rules_database_path=RELEASE / "rules_n5.db")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("v15 runtime must not read combined saving roll JSON")

    monkeypatch.setattr(adapter, "load_combined_saving_roll_map", forbidden)
    current = create_app(ARMY, rules_database_path=rules)
    for slug in ("plasma-rifle", "plasma-carbine", "plasma-sniper-rifle", "feuerbach"):
        url = f"http://saving.test/api/weapons/{slug}"
        status, _, body = wsgi_response(current, url)
        legacy_status, _, legacy_body = wsgi_response(previous, url)
        assert status == legacy_status == 200
        assert json.loads(body) == json.loads(legacy_body)
        if slug != "feuerbach":
            for profile in json.loads(body)["profiles"]:
                assert profile["combined_saving_roll"]["critical"] == {
                    "additionalRolls": 1, "attribute": "ARM",
                }


@pytest.mark.parametrize("mutation", (
    "missing-mode", "mode", "identity", "source", "saving", "ammunition",
    "duplicate", "source-identity",
))
def test_staging_rejects_changed_or_ambiguous_review(
    v15, tmp_path: Path, mutation: str,
) -> None:
    old, original = v15
    path = tmp_path / "rules_n5.db"
    shutil.copyfile(old, path)
    mapping = deepcopy(original)
    key = (40, "Blast Mode")
    if mutation == "missing-mode":
        mapping.pop(key)
    elif mutation == "mode":
        mapping[key]["modes"] = ["Blast Mode"]
    elif mutation == "identity":
        mapping[key]["weaponName"] = "Other"
    elif mutation == "source":
        mapping[key]["source"]["page"] = 66
    elif mutation == "saving":
        mapping[key]["savingNum"] = "2"
    elif mutation == "ammunition":
        mapping[key]["ammunitionSourceId"] = 10
    elif mutation == "duplicate":
        mapping[(40, "Another Mode")] = deepcopy(mapping[key])
    else:
        mapping[key]["source"]["sourceId"] = "unknown"
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE weapon_combined_saving_roll_profiles")
        connection.execute("DROP TABLE combined_saving_roll_metadata")
        connection.execute("PRAGMA user_version=14")
        with pytest.raises(ValueError, match="Combined Saving Roll"):
            stage_combined_saving_rolls(connection, mapping, ARMY)


@pytest.mark.parametrize("mutation", (
    "name", "mode", "source", "army", "fingerprint", "count", "position",
))
def test_embedded_corruption_is_rejected(v15, tmp_path: Path, mutation: str) -> None:
    original, _ = v15
    path = tmp_path / "rules_n5.db"
    shutil.copyfile(original, path)
    with sqlite3.connect(path) as connection:
        if mutation == "name":
            connection.execute(
                "UPDATE weapon_combined_saving_roll_profiles SET weapon_name='Other' "
                "WHERE weapon_id=40"
            )
        elif mutation == "mode":
            connection.execute(
                "UPDATE weapon_combined_saving_roll_profiles SET mode='Other' "
                "WHERE weapon_id=40 AND mode='Hit Mode'"
            )
        elif mutation == "source":
            connection.execute(
                "UPDATE combined_saving_roll_metadata SET source_page=66"
            )
        elif mutation == "army":
            connection.execute(
                "UPDATE combined_saving_roll_metadata SET army_database_sha256=?",
                ("0" * 64,),
            )
        elif mutation == "fingerprint":
            connection.execute(
                "UPDATE combined_saving_roll_metadata SET content_sha256=?",
                ("0" * 64,),
            )
        elif mutation == "count":
            connection.execute(
                "DELETE FROM weapon_combined_saving_roll_profiles "
                "WHERE weapon_id=40 AND mode='Hit Mode'"
            )
        else:
            connection.execute(
                "UPDATE weapon_combined_saving_roll_profiles SET position=100 "
                "WHERE weapon_id=40 AND mode='Hit Mode'"
            )
        with pytest.raises(ValueError, match="Combined Saving Roll"):
            read_combined_saving_rolls(connection, ARMY)
    if mutation != "army":
        with pytest.raises(ValueError):
            RulesDatabase(path).validate()


def test_current_release_embeds_reviewed_saving_rolls(v15) -> None:
    path, mapping = v15
    assert RulesDatabase(RELEASE / "rules_n5.db").combined_saving_rolls_payload(ARMY) == mapping
    assert WeaponCombinedSavingRolls()._mapping == mapping
    assert WeaponCombinedSavingRolls(RulesDatabase(path))._mapping == mapping
    raw = Database(ARMY).get_catalog_item("weapons", "plasma-rifle")
    assert raw is not None
    old = CatalogRules(RulesDatabase(RELEASE / "rules_n5.db")).enrich_catalog_item(
        "weapons", raw,
    )
    new = CatalogRules(RulesDatabase(path)).enrich_catalog_item("weapons", raw)
    assert new == old
