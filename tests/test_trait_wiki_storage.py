"""P2.4 reviewed Trait Wiki links embedded in Rules v14 with v10 API parity."""

from __future__ import annotations

import json
import shutil
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest
from storage_fixture_support import copy_base_rules, variant_publication, weapon_publication

from infinity_db.restriction_chart_storage import stage_restriction_chart
from infinity_db.rules_database import RulesDatabase
from infinity_db.trait_wiki_references import load_trait_wiki_references
from infinity_db.trait_wiki_storage import (
    read_trait_wiki_links,
    stage_trait_wiki_links,
    validate_trait_wiki_snapshot,
)
from infinity_db.variant_usage_storage import stage_variant_usage
from infinity_db.weapon_profile_storage import stage_weapon_profile_citations
from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/generated"
ARMY = RELEASE / "army.db"
CONFIG = ROOT / "config/catalogs/trait-wiki-references.json"


@pytest.fixture(scope="module")
def v14(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    directory = tmp_path_factory.mktemp("rules-v14-trait-links")
    rules = directory / "rules_n5.db"
    copy_base_rules(rules)
    shutil.copyfile(ARMY, directory / "army.db")
    mapping = load_trait_wiki_references(CONFIG)
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
            stage_trait_wiki_links(connection, mapping)
            connection.execute("PRAGMA user_version=14")
            connection.execute(
                "UPDATE __rules_metadata SET value='14' WHERE key='formatVersion'"
            )
            connection.execute(
                "UPDATE __rules_metadata SET value='16' "
                "WHERE key='databaseCompatibilityVersion'"
            )
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    return rules, mapping


def test_v14_round_trip_matches_all_33_source_reviewed_links(v14) -> None:
    from infinity_db.database_set import validate_database_set

    path, expected = v14
    RulesDatabase(path).validate()
    assert RulesDatabase(path).trait_wiki_links_payload() == expected
    assert len(expected) == 33
    with sqlite3.connect(path) as connection:
        validate_trait_wiki_snapshot(connection)
        assert read_trait_wiki_links(connection) == expected
    report = validate_database_set(path.parent)
    assert report["layout"] == "v14-two-file"
    assert report["traitWikiLinks"] == 33
    assert set(report["sha256"]) == {"army.db", "rules_n5.db"}


def test_v14_public_api_matches_v10_without_legacy_config_reads(
    v14, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import infinity_db.trait_wiki_references as legacy

    path, expected = v14
    previous = create_app(ARMY, rules_database_path=RELEASE / "rules_n5.db")

    def no_runtime_json(*_args, **_kwargs):
        raise AssertionError("Rules v14 must not read packaged Trait Wiki JSON")

    monkeypatch.setattr(legacy, "load_trait_wiki_references", no_runtime_json)
    current = create_app(ARMY, rules_database_path=path)
    for identity, link in expected.items():
        route = f"http://trait.test/api/traits/{identity.removeprefix('trait:')}"
        status, _, body = wsgi_response(current, route)
        old_status, _, old_body = wsgi_response(previous, route)
        assert status == old_status == 200
        assert json.loads(body) == json.loads(old_body)
        assert json.loads(body)["wiki"] == link["url"]


@pytest.mark.parametrize("mutation", ("missing", "unknown", "name", "http", "fragment"))
def test_staging_rejects_unreviewed_trait_links(
    v14, tmp_path: Path, mutation: str,
) -> None:
    source, expected = v14
    path = tmp_path / "rules_n5.db"
    shutil.copyfile(source, path)
    entries = deepcopy(expected)
    if mutation == "missing":
        entries.pop("trait:arm-0")
    elif mutation == "unknown":
        entries["trait:invented"] = {"name": "Invented", "url": "https://infinitythewiki.com/Traits#Invented"}
    elif mutation == "name":
        entries["trait:arm-0"]["name"] = "Invented Name"
    elif mutation == "http":
        entries["trait:arm-0"]["url"] = "http://infinitythewiki.com/Traits#ARM_.3D_0"
    else:
        entries["trait:arm-0"]["url"] = "https://infinitythewiki.com/Traits"

    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE trait_source_links")
        connection.execute("DROP TABLE trait_wiki_metadata")
        connection.execute("PRAGMA user_version=13")
        with pytest.raises(ValueError, match="Trait Wiki"):
            stage_trait_wiki_links(connection, entries)


@pytest.mark.parametrize("mutation", ("name", "url", "missing", "fingerprint", "position"))
def test_corrupt_relational_trait_links_fail_closed(v14, tmp_path: Path, mutation: str) -> None:
    source, _ = v14
    path = tmp_path / "rules_n5.db"
    shutil.copyfile(source, path)
    with sqlite3.connect(path) as connection:
        if mutation == "name":
            connection.execute(
                "UPDATE trait_source_links SET name='Wrong' "
                "WHERE trait_record_id='trait:non-lethal'"
            )
        elif mutation == "url":
            connection.execute(
                "UPDATE trait_source_links SET url='http://bad.example' "
                "WHERE trait_record_id='trait:non-lethal'"
            )
        elif mutation == "missing":
            connection.execute(
                "DELETE FROM trait_source_links WHERE trait_record_id='trait:non-lethal'"
            )
        elif mutation == "fingerprint":
            connection.execute(
                "UPDATE trait_wiki_metadata SET content_sha256=?",
                ("0" * 64,),
            )
        else:
            connection.execute(
                "UPDATE trait_source_links SET position=100 "
                "WHERE trait_record_id='trait:non-lethal'"
            )
        with pytest.raises(ValueError, match="Trait Wiki"):
            read_trait_wiki_links(connection)
    with pytest.raises(ValueError):
        RulesDatabase(path).validate()


def test_tracked_rules_preserve_reviewed_wiki_links(v14) -> None:
    source, expected = v14
    assert RulesDatabase(source).trait_wiki_links_payload() == expected
    assert RulesDatabase(RELEASE / "rules_n5.db").trait_wiki_links_payload() == expected
    app = create_app(ARMY, rules_database_path=RELEASE / "rules_n5.db")
    status, _, body = wsgi_response(app, "http://trait.test/api/traits/non-lethal")
    assert status == 200
    assert json.loads(body)["wiki"] == expected["trait:non-lethal"]["url"]
