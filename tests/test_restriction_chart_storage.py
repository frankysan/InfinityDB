"""Restrictions source chart v13 relational publication and HTTP parity."""

from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest
from storage_fixture_support import copy_base_rules, variant_publication, weapon_publication

from infinity_db.restriction_chart_storage import (
    read_restriction_chart,
    stage_restriction_chart,
    validate_restriction_chart_snapshot,
)
from infinity_db.rules_database import RulesDatabase
from infinity_db.variant_usage_storage import stage_variant_usage
from infinity_db.weapon_profile_storage import stage_weapon_profile_citations
from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/generated"
ARMY = RELEASE / "army.db"
CHART = ROOT / "src/infinity_db/web/static/restrictions-reference.json"


@pytest.fixture
def published(tmp_path: Path) -> tuple[Path, dict]:
    rules = tmp_path / "rules_n5.db"
    copy_base_rules(rules)
    chart = json.loads(CHART.read_text(encoding="utf-8"))
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
            stage_restriction_chart(connection, chart)
            connection.execute("PRAGMA user_version=13")
            connection.execute(
                "UPDATE __rules_metadata SET value='13' WHERE key='formatVersion'"
            )
            connection.execute(
                "UPDATE __rules_metadata SET value='15' "
                "WHERE key='databaseCompatibilityVersion'"
            )
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    return rules, chart


def test_chart_round_trips_all_six_rows_and_14_conditions(published) -> None:
    rules, chart = published
    RulesDatabase(rules).validate()
    assert RulesDatabase(rules).restriction_chart_payload() == chart
    with sqlite3.connect(rules) as connection:
        validate_restriction_chart_snapshot(connection)
        assert connection.execute("SELECT COUNT(*) FROM restriction_chart_rows").fetchone()[0] == 6
        assert connection.execute(
            "SELECT COUNT(*) FROM restriction_chart_conditions"
        ).fetchone()[0] == 14
        assert connection.execute(
            "SELECT COUNT(*) FROM restriction_chart_qualifiers"
        ).fetchone()[0] == 4
        assert connection.execute(
            "SELECT COUNT(*) FROM restriction_constraints"
        ).fetchone()[0] == 14


def test_v13_api_ignores_old_static_json_path(published, monkeypatch) -> None:
    import infinity_db.web.api_handler as api_handler

    rules, chart = published

    def never_read_packaged_json(*_args, **_kwargs):
        raise AssertionError("v13 API must not consult the packaged chart JSON")

    monkeypatch.setattr(api_handler, "files", never_read_packaged_json)
    app = create_app(ARMY, rules_database_path=rules)
    status, headers, body = wsgi_response(app, "http://chart.test/api/restrictions/chart")
    assert status == 200
    assert dict(headers)["Content-Type"].startswith("application/json")
    assert json.loads(body) == chart
    status, _, body = wsgi_response(app, "http://chart.test/api/restrictions/chart?other=x")
    assert status == 400
    assert "error" in json.loads(body)


def test_tracked_chart_api_retains_original_payload() -> None:
    app = create_app(ARMY, rules_database_path=RELEASE / "rules_n5.db")
    status, _, body = wsgi_response(app, "http://chart.test/api/restrictions/chart")
    assert status == 200
    assert json.loads(body) == json.loads(CHART.read_text(encoding="utf-8"))
    assert RulesDatabase(RELEASE / "rules_n5.db").restriction_chart_payload() == json.loads(
        CHART.read_text(encoding="utf-8"),
    )


@pytest.mark.parametrize("mutation", ("source", "row", "action", "scope", "qualifier", "missing"))
def test_chart_staging_rejects_unreviewed_drift(
    tmp_path: Path, mutation: str,
) -> None:
    rules = tmp_path / "rules_n5.db"
    copy_base_rules(rules)
    chart = json.loads(CHART.read_text(encoding="utf-8"))
    if mutation == "source":
        chart["source"]["page"] = 195
    elif mutation == "row":
        chart["rows"][0]["sourceSubject"] = "Unknown"
    elif mutation == "action":
        chart["rows"][0]["conditions"][0]["action"] = "jump"
    elif mutation == "scope":
        chart["rows"][1]["conditions"][4]["scope"] = "all"
    elif mutation == "qualifier":
        chart["rows"][1]["conditions"][4]["operation"]["qualifier"]["direction"] = "downward"
    elif mutation == "missing":
        chart["rows"][1]["conditions"].pop()
    with sqlite3.connect(rules) as connection:
        connection.execute("PRAGMA user_version=12")
        with pytest.raises(ValueError, match="Restrictions chart"):
            stage_restriction_chart(connection, chart)


@pytest.mark.parametrize(
    "mutation", ("label", "content-hash", "source", "source-collection", "missing-row"),
)
def test_chart_reader_rejects_corrupt_embedded_data(published, mutation: str) -> None:
    rules, _ = published
    with sqlite3.connect(rules) as connection:
        if mutation == "label":
            connection.execute(
                "UPDATE restriction_chart_conditions SET label='invented' "
                "WHERE row_id='tag' AND position=0"
            )
        elif mutation == "content-hash":
            connection.execute(
                "UPDATE restriction_chart_metadata SET content_sha256=?",
                ("0" * 64,),
            )
        elif mutation == "source":
            connection.execute(
                "UPDATE restriction_chart_metadata SET source_page=193"
            )
        elif mutation == "source-collection":
            connection.execute(
                "UPDATE restriction_chart_metadata SET source_collection_id=?",
                ("n5-hacking-programs-v5.3",),
            )
        else:
            connection.execute(
                "DELETE FROM restriction_chart_conditions "
                "WHERE row_id='motorcycle' AND position=4"
            )
        with pytest.raises(ValueError, match="Restrictions chart"):
            read_restriction_chart(connection)
    with pytest.raises(ValueError):
        RulesDatabase(rules).validate()


def test_provenance_keeps_upward_jump_and_lieutenant_context(published) -> None:
    _rules, chart = published
    motorcycle = next(row for row in chart["rows"] if row["id"] == "motorcycle")
    jump = next(c for c in motorcycle["conditions"] if c["action"] == "upward-jump")
    assert jump["scope"] == "while-mounted-upwards-only"
    assert jump["operation"]["qualifier"] == {"direction": "upward"}
    assert next(
        row for row in chart["rows"] if row["id"] == "rem"
    )["conditions"][1]["scope"] == "army-selection-only"
    clone = deepcopy(chart)
    assert clone == chart
