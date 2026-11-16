"""Army overview and historical identities remain distinct and self-contained in v30."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest
from storage_fixture_support import copy_base_army

from infinity_db.army_overview_copy import load_army_overview_copy
from infinity_db.army_reference_storage import (
    ARMY_COMPATIBILITY_VERSION,
    ARMY_SCHEMA_VERSION,
    publish_army_reference_data,
    read_army_reference_data,
)
from infinity_db.database.health import database_health_report
from infinity_db.database.publication import validate_database_pair
from infinity_db.database.repository import Database
from infinity_db.equipment_presentation_storage import publish_equipment_encodings
from infinity_db.legacy_armies import load_legacy_armies
from infinity_db.skill_classification_storage import publish_skill_classifications
from infinity_db.unit_filter_storage import publish_unit_filter_semantics
from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/generated"
OVERVIEW = ROOT / "data/curated/identities/army-overview.json"
LEGACY = ROOT / "data/curated/identities/legacy-armies.json"


@pytest.fixture
def v29(tmp_path: Path) -> tuple[Path, Path]:
    army, raw = tmp_path / "army.db", tmp_path / "army.raw.db"
    copy_base_army(army)
    copy_base_army(raw)
    publish_equipment_encodings(
        army, raw, ROOT / "config/catalogs/equipment-presentation-encodings.json",
    )
    publish_skill_classifications(
        army, raw, ROOT / "config/catalogs/skill-source-classifications.json",
    )
    publish_unit_filter_semantics(army, raw, ROOT / "config/catalogs/unit-filter-semantics.json")
    return army, raw


@pytest.fixture
def v30(v29) -> tuple[Path, Path]:
    army, raw = v29
    publish_army_reference_data(army, raw, OVERVIEW, LEGACY)
    return army, raw


def test_exact_source_roundtrip_and_identity_boundaries(v30) -> None:
    army, raw = v30
    expected = load_army_overview_copy(OVERVIEW), load_legacy_armies(LEGACY)
    assert len(expected[0]) == 58 and len(expected[1]) == 2
    assert Database(army).army_reference_data() == expected
    assert validate_database_pair(army, raw_path=raw) is not None
    health = database_health_report(army, require_raw=True)
    assert health["status"] == "healthy"
    assert health["application"]["schemaRevision"] == ARMY_SCHEMA_VERSION
    assert health["application"]["compatibilityRevision"] == ARMY_COMPATIBILITY_VERSION
    with sqlite3.connect(army) as connection:
        assert read_army_reference_data(connection) == expected
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute(
            "SELECT overview_sha256,legacy_sha256 FROM army_reference_metadata"
        ).fetchone() == (
            hashlib.sha256(OVERVIEW.read_bytes()).hexdigest(),
            hashlib.sha256(LEGACY.read_bytes()).hexdigest(),
        )
        assert connection.execute(
            "SELECT slug FROM army_overview_text ORDER BY position"
        ).fetchall() == [(slug,) for slug in expected[0]]
        assert connection.execute(
            "SELECT slug,application_army_id,legacy_context,legacy_army_id "
            "FROM army_overview_text WHERE legacy_army_id IS NOT NULL ORDER BY position"
        ).fetchall() == [("spiral-corps", None, 1, 906), ("foreign-company", None, 1, 907)]
    assert Database(army).application_army_id("spiral-corps") is None
    assert Database(army).application_army_id(906) is None
    assert Database(army).list_armies() == Database(RELEASE / "army.db").list_armies()


def test_http_and_search_parity_without_authored_json(v30, monkeypatch) -> None:
    import infinity_db.army_overview_copy as copy_adapter
    import infinity_db.legacy_armies as legacy_adapter

    previous = create_app(RELEASE / "army.db")
    paths = ("/api/armies", "/api/search?q=spiral", "/api/search?q=foreign")

    def payload(app, path):
        status, _headers, body = wsgi_response(app, "http://army.test" + path)
        assert status == 200
        return json.loads(body)

    expected = [payload(previous, path) for path in paths]

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Army v30 serving must not open overview or legacy JSON")

    monkeypatch.setattr(copy_adapter, "load_army_overview_copy", forbidden)
    monkeypatch.setattr(legacy_adapter, "load_legacy_armies", forbidden)
    current = create_app(v30[0])
    assert [payload(current, path) for path in paths] == expected


@pytest.mark.parametrize("mutation", (
    "missing-summary", "unknown-slug", "duplicate-summary", "overlong-summary",
    "legacy-id-collision", "legacy-slug-collision", "unknown-parent", "different-parent-slug",
    "different-parent-name", "duplicate-legacy", "missing-legacy",
))
def test_build_rejects_inconsistent_inputs_before_writes(
    v29, tmp_path: Path, mutation: str,
) -> None:
    army, raw = v29
    before = army.read_bytes(), raw.read_bytes()
    overview = json.loads(OVERVIEW.read_text(encoding="utf-8"))
    legacy = json.loads(LEGACY.read_text(encoding="utf-8"))
    if mutation == "missing-summary":
        overview["armies"].pop()
    elif mutation == "unknown-slug":
        overview["armies"][0]["slug"] = "unknown-army"
    elif mutation == "duplicate-summary":
        overview["armies"].append(overview["armies"][0])
    elif mutation == "overlong-summary":
        overview["armies"][0]["summary"] = "x" * 241
    elif mutation == "legacy-id-collision":
        legacy["armies"][0]["id"] = 101
    elif mutation == "legacy-slug-collision":
        legacy["armies"][0]["slug"] = "panoceania"
    elif mutation == "unknown-parent":
        legacy["armies"][0]["groupId"] = 999999
    elif mutation == "different-parent-slug":
        legacy["armies"][0]["groupSlug"] = "panoceania"
    elif mutation == "different-parent-name":
        legacy["armies"][0]["groupName"] = "Unreviewed parent"
    elif mutation == "duplicate-legacy":
        legacy["armies"].append(legacy["armies"][0])
    else:
        legacy["armies"].pop()
    overview_path, legacy_path = tmp_path / "overview.json", tmp_path / "legacy.json"
    overview_path.write_text(json.dumps(overview), encoding="utf-8")
    legacy_path.write_text(json.dumps(legacy), encoding="utf-8")
    with pytest.raises(ValueError):
        publish_army_reference_data(army, raw, overview_path, legacy_path)
    assert (army.read_bytes(), raw.read_bytes()) == before


@pytest.mark.parametrize("sql", (
    "DELETE FROM army_overview_text WHERE position=0",
    "DELETE FROM legacy_army_identities WHERE id=906",
    "UPDATE army_overview_text SET text='Unreviewed content' WHERE position=0",
    "UPDATE army_overview_text SET application_army_id=201 WHERE position=0",
    "UPDATE army_overview_text SET legacy_army_id=907 WHERE slug='spiral-corps'",
    "UPDATE army_overview_text SET position=99 WHERE position=0",
    "UPDATE legacy_army_identities SET group_id=101 WHERE id=906",
    "UPDATE legacy_army_identities SET reason='Unreviewed reason' WHERE id=906",
    "UPDATE legacy_army_identities SET source_context=9 WHERE id=906",
    "UPDATE army_reference_metadata SET export_pair_sha256=printf('%064d',0)",
    "UPDATE army_reference_metadata SET content_sha256=printf('%064d',0)",
))
def test_corrupt_rows_fail_closed_without_json_fallback(v30, monkeypatch, sql: str) -> None:
    import infinity_db.army_overview_copy as copy_adapter
    import infinity_db.legacy_armies as legacy_adapter

    army, _raw = v30
    with sqlite3.connect(army) as connection:
        connection.execute(sql)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Corrupt Army reference must not recover from authored JSON")

    monkeypatch.setattr(copy_adapter, "load_army_overview_copy", forbidden)
    monkeypatch.setattr(legacy_adapter, "load_legacy_armies", forbidden)
    with pytest.raises(ValueError):
        Database(army).army_reference_data()
    with pytest.raises(ValueError):
        Database(army).validate()


def test_pre_v30_retains_authored_adapters(v29) -> None:
    assert Database(v29[0]).army_reference_data() == (
        load_army_overview_copy(OVERVIEW), load_legacy_armies(LEGACY),
    )


def test_runtime_audit_traces_embedded_army_data(v30) -> None:
    from tools.data.audit_runtime_database_surface import audit_database

    army, _raw = v30
    before = hashlib.sha256(army.read_bytes()).hexdigest()
    report = audit_database(army, project_root=ROOT)
    tables = {row["table"] for row in report["inventory"]}
    assert {
        "army_overview_text", "legacy_army_identities", "army_reference_metadata",
        "skill_source_classifications", "unit_filter_metadata", "hidden_unit_characteristics",
        "source_classification_memberships", "source_classification_matches",
    } <= tables
    assert hashlib.sha256(army.read_bytes()).hexdigest() == before
