"""Pinned current-state Army chart parity; not historical change or list legality."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from infinity_db.database import Database
from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[1]
ARMY_ZIP = ROOT / "data/raw/JSON 20260929-114335.zip"
ARMY_DB = ROOT / "data/generated/infinity.db"


@pytest.mark.skipif(not ARMY_ZIP.exists(), reason="Pinned Army ZIP unavailable")
def test_army_01_all_pinned_chart_constraints_reach_public_api() -> None:
    """Compare original archive rows independently of the chart materializer."""
    assert hashlib.sha256(ARMY_ZIP.read_bytes()).hexdigest() == (
        "f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75"
    )
    database = Database(ARMY_DB)
    application = create_app(ARMY_DB, rules_database_path=ROOT / "data/generated/rules.db")
    chart_count = team_count = member_count = 0
    with zipfile.ZipFile(ARMY_ZIP) as archive:
        # Cover raw contexts too: a publication-only inventory would miss dropped
        # sources. Alternate sources must agree with their selected application chart.
        with sqlite3.connect(ARMY_DB.as_uri() + "?mode=ro", uri=True) as connection:
            source_rows = connection.execute(
                "SELECT a.application_army_id, s.source_file, s.source_sha256 "
                "FROM application_army_sources AS a JOIN army_lists AS s "
                "ON s.id = a.source_army_id WHERE a.has_army_list = 1"
            ).fetchall()
        assert {row[1] for row in source_rows} == {
            name for name in archive.namelist()
            if name.endswith(".json") and name != "metadata.json"
        }
        assert len(source_rows) == 58
        for application_id, source_file, source_sha256 in source_rows:
            source_bytes = archive.read(source_file)
            assert hashlib.sha256(source_bytes).hexdigest() == source_sha256
            chart = database.get_fireteam_chart(application_id)
            assert chart is not None, source_file
            assert json.loads(source_bytes)["fireteamChart"] == json.loads(
                archive.read(chart["source"]["file"])
            )["fireteamChart"], source_file
        for army in database.list_armies():
            chart = database.get_fireteam_chart(army["id"])
            if chart is None:
                continue
            chart_count += 1
            status, _, body = wsgi_response(
                application, f"http://test/api/fireteams?army_id={army['slug']}",
            )
            assert status == 200, army
            published = json.loads(body)
            assert published["army"]["id"] == army["id"]
            for key in ("source", "description", "limits", "teams"):
                assert published[key] == chart[key], (army, key)
            source_bytes = archive.read(chart["source"]["file"])
            assert hashlib.sha256(source_bytes).hexdigest() == chart["source"]["sha256"]
            source = json.loads(source_bytes)
            raw = source["fireteamChart"]
            if raw is None:
                assert chart["description"] is None
                assert chart["limits"] == chart["teams"] == []
                continue
            assert chart["description"] == raw.get("desc"), army
            assert [(item["type"], item["max_count"]) for item in chart["limits"]] == (
                list(raw["spec"].items())
            ), army
            assert len(chart["teams"]) == len(raw["teams"]), army
            for position, (team, original) in enumerate(
                zip(chart["teams"], raw["teams"], strict=True), start=1,
            ):
                team_count += 1
                assert team["position"] == team["source_fireteam_id"] == position
                assert team["name"] == original["name"]
                assert team["observation"] == original.get("obs")
                assert team["wildcards_excluded"] is (
                    (army["id"], team["name"]) in {
                        (204, "Forward Fireteams"), (605, "Team Achilles Fireteams"),
                    }
                )
                assert team["types"] == [value.upper() for value in original["type"]]
                assert len(team["members"]) == len(original["units"])
                for member_position, (member, original_member) in enumerate(
                    zip(team["members"], original["units"], strict=True), start=1,
                ):
                    member_count += 1
                    assert member["position"] == member["source_member_id"] == member_position
                    for key in ("name", "slug", "comment"):
                        assert member[key] == original_member.get(key), (army, team, key)
                    assert member["min_count"] == original_member.get("min")
                    assert member["max_count"] == original_member.get("max")
                    assert member["required"] == bool(original_member.get("required"))
    assert (chart_count, team_count, member_count) == (57, 268, 1249)
