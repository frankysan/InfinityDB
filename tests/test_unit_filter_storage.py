"""Unit Explorer overlays preserve source facts and public results in Army v29."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from infinity_db.database.health import database_health_report
from infinity_db.database.publication import validate_database_pair
from infinity_db.database.repository import Database
from infinity_db.equipment_presentation_storage import publish_equipment_encodings
from infinity_db.skill_classification_storage import publish_skill_classifications
from infinity_db.unit_filter_config import load_unit_filter_config
from infinity_db.unit_filter_storage import (
    ARMY_COMPATIBILITY_VERSION,
    ARMY_SCHEMA_VERSION,
    publish_unit_filter_semantics,
    read_unit_filter_semantics,
)
from infinity_db.unit_presentation import enrich_unit_filter_presentation
from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/generated"
CONFIG = ROOT / "config/catalogs/unit-filter-semantics.json"


@pytest.fixture
def v28(tmp_path: Path) -> tuple[Path, Path]:
    army, raw = tmp_path / "infinity.db", tmp_path / "infinity.raw.db"
    shutil.copyfile(RELEASE / "infinity.db", army)
    shutil.copyfile(RELEASE / "infinity.db", raw)
    publish_equipment_encodings(
        army, raw, ROOT / "config/catalogs/equipment-presentation-encodings.json",
    )
    publish_skill_classifications(
        army, raw, ROOT / "config/catalogs/skill-source-classifications.json",
    )
    return army, raw


@pytest.fixture
def v29(v28) -> tuple[Path, Path]:
    army, raw = v28
    publish_unit_filter_semantics(army, raw, CONFIG)
    return v28


def test_source_bound_roundtrip_and_paired_health(v29) -> None:
    army, raw = v29
    expected = load_unit_filter_config(CONFIG)
    database = Database(army)
    database.validate()
    assert database.unit_filter_semantics() == expected
    assert validate_database_pair(army, raw_path=raw) is not None
    health = database_health_report(army, require_raw=True)
    assert health["status"] == "healthy"
    assert health["application"]["schemaRevision"] == ARMY_SCHEMA_VERSION
    assert health["application"]["compatibilityRevision"] == ARMY_COMPATIBILITY_VERSION
    with sqlite3.connect(army) as connection:
        assert read_unit_filter_semantics(connection) == expected
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        digest = connection.execute("SELECT source_sha256 FROM unit_filter_metadata").fetchone()[0]
        assert digest == hashlib.sha256(CONFIG.read_bytes()).hexdigest()
        rows = connection.execute(
            "SELECT slug,reason FROM hidden_unit_characteristics ORDER BY position"
        ).fetchall()
        document = json.loads(CONFIG.read_text(encoding="utf-8"))
        assert rows == [
            (item["characteristic"], item["reason"]) for item in document["hiddenCharacteristics"]
        ]
    previous = Database(RELEASE / "infinity.db")
    assert database.list_unit_filter_values() == previous.list_unit_filter_values()


def test_public_filter_choices_and_results_match_without_json(v29, monkeypatch) -> None:
    import infinity_db.database.repository as repository
    import infinity_db.unit_presentation as presentation

    previous = Database(RELEASE / "infinity.db")
    raw = previous.list_unit_filter_values()
    expected_filters = enrich_unit_filter_presentation(raw)
    classifications = [
        item["slug"] for item in expected_filters["classifications"]
    ] + ["headquarters-troops-mechanized-troops"]
    choices = [
        {"classification": slug, "limit": 500} for slug in classifications
    ] + [
        {"classification": slug, "points": 86, "limit": 500}
        for slug in ("headquarters-troops", "mechanized-troops")
    ] + [
        {"characteristic": slug, "limit": 500}
        for slug in ("mechanical-transmutation", "shasvastii")
    ]
    expected_units = [previous.list_units(**choice) for choice in choices]

    def forbidden(*_args, **_kwargs):
        raise AssertionError("v29 filtering/presentation must not read maintained JSON")

    monkeypatch.setattr(repository, "load_unit_filter_config", forbidden)
    monkeypatch.setattr(presentation, "load_unit_filter_config", forbidden)
    current = Database(v29[0])
    assert enrich_unit_filter_presentation(
        current.list_unit_filter_values(), filter_semantics=current.unit_filter_semantics(),
    ) == expected_filters
    assert [current.list_units(**choice) for choice in choices] == expected_units
    for slug in ("headquarters-troops", "mechanized-troops"):
        value = next(item for item in raw["classifications"] if item["slug"] == slug)
        assert current.list_units(classification=value["id"]) == current.list_units(
            classification=slug,
        )
    app = create_app(v29[0])
    status, _headers, body = wsgi_response(app, "http://filter.test/api/unit-filters")
    assert status == 200
    assert json.loads(body) == expected_filters
    for slug in ("headquarters-troops", "mechanized-troops"):
        status, _headers, body = wsgi_response(
            app, f"http://filter.test/api/units?classification={slug}&search=MARUTS&limit=200",
        )
        assert status == 200
        assert [item["name"] for item in json.loads(body)["items"]] == ["MARUTS"]


@pytest.mark.parametrize("mutation", (
    "unknown-characteristic", "unknown-source", "unknown-match", "duplicate", "recursive",
))
def test_build_rejects_invalid_policy_before_writes(v28, tmp_path: Path, mutation: str) -> None:
    army, raw = v28
    before = (army.read_bytes(), raw.read_bytes())
    document = json.loads(CONFIG.read_text(encoding="utf-8"))
    if mutation == "unknown-characteristic":
        document["hiddenCharacteristics"][0]["characteristic"] = "unreviewed-characteristic"
    elif mutation == "unknown-source":
        document["classificationMemberships"][0]["sourceClassification"] = "unknown-source"
    elif mutation == "unknown-match":
        document["classificationMemberships"][0]["matches"][0] = "unknown-match"
    elif mutation == "duplicate":
        document["hiddenCharacteristics"].append(document["hiddenCharacteristics"][0])
    else:
        membership = document["classificationMemberships"][0]
        membership["matches"][0] = membership["sourceClassification"]
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError):
        publish_unit_filter_semantics(army, raw, path)
    assert (army.read_bytes(), raw.read_bytes()) == before


@pytest.mark.parametrize("sql", (
    "DELETE FROM hidden_unit_characteristics WHERE position=0",
    "DELETE FROM source_classification_matches WHERE position=0",
    "UPDATE hidden_unit_characteristics SET reason='unreviewed' WHERE position=0",
    "UPDATE source_classification_memberships SET reason='unreviewed'",
    "UPDATE source_classification_matches SET category_id=999999 WHERE position=0",
    "UPDATE hidden_unit_characteristics SET characteristic_id=999999 WHERE position=0",
    "UPDATE hidden_unit_characteristics SET position=9 WHERE position=0",
    "UPDATE source_classification_matches SET position=9 WHERE position=0",
    "UPDATE unit_filter_metadata SET export_pair_sha256=printf('%064d',0)",
    "UPDATE unit_filter_metadata SET content_sha256=printf('%064d',0)",
    "UPDATE unit_filter_metadata SET source_sha256=printf('%064d',9)",
))
def test_corrupt_projection_never_falls_back(v29, monkeypatch, sql: str) -> None:
    import infinity_db.database.repository as repository

    army, _raw = v29
    with sqlite3.connect(army) as connection:
        connection.execute(sql)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Corrupt v29 data must not fall back to JSON")

    monkeypatch.setattr(repository, "load_unit_filter_config", forbidden)
    with pytest.raises(ValueError):
        Database(army).validate()


def test_pre_v29_retains_source_adapter(v28) -> None:
    assert Database(v28[0]).unit_filter_semantics() == load_unit_filter_config(CONFIG)
