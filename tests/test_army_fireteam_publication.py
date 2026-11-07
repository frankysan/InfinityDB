"""Pinned current-state Army chart parity; not historical change or list legality."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import zipfile
from collections import Counter
from pathlib import Path

import pytest

from infinity_db.database import Database
from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[1]
ARMY_ZIP = ROOT / "data/raw/JSON 20260929-114335.zip"
ARMY_DB = ROOT / "data/generated/infinity.db"


@pytest.mark.skipif(not ARMY_ZIP.exists(), reason="Pinned Army ZIP unavailable")
def test_named_chart_annotations_preserve_exact_local_profile_context() -> None:
    """Parentheses are source syntax, not a universal counts-as/eligibility rule."""
    assert hashlib.sha256(ARMY_ZIP.read_bytes()).hexdigest() == (
        "f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75"
    )
    cases = (
        (105, "105-varuna-immediate-reaction-division.json", "7.26246.158",
         {(1, 4), (2, 1), (2, 4)}),
        (1102, "1102-shindenbutai.json", "7.26246.159", {(3, 5)}),
        (801, "801-tohaa.json", "7.26246.159",
         {(1, member) for member in (*range(1, 13), 15, 17)}),
        (899, "899-deras-kaar.json", "7.26246.159",
         {(1, member) for member in range(1, 5)} | {(3, 1)}),
    )
    application = create_app(ARMY_DB, rules_database_path=ROOT / "data/generated/rules.db")
    database = Database(ARMY_DB)
    reviewed_rows = 0
    with zipfile.ZipFile(ARMY_ZIP) as archive:
        metadata = json.loads(archive.read("metadata.json"))
        assert next(item["name"] for item in metadata["skills"] if item["id"] == 251) == (
            "Strategic\u00a0Deployment"
        )
        for army_id, member, version, row_keys in cases:
            raw = archive.read(member)
            source = json.loads(raw)
            assert source["version"] == version
            chart = database.get_fireteam_chart(army_id)
            assert chart is not None
            assert chart["source"]["file"] == member
            assert chart["source"]["sha256"] == hashlib.sha256(raw).hexdigest()
            status, _, body = wsgi_response(
                application, f"http://test/api/fireteams?army_id={chart['army']['slug']}",
            )
            assert status == 200
            published = json.loads(body)
            source_units = {unit["id"]: unit for unit in source["units"]}
            for team_id, row_id in sorted(row_keys):
                original = source["fireteamChart"]["teams"][team_id - 1]["units"][row_id - 1]
                actual = published["teams"][team_id - 1]["members"][row_id - 1]
                assert (actual["name"], actual["comment"], actual["slug"]) == (
                    original["name"], original["comment"], original["slug"],
                )
                # None of these notes is an explicit FTO marker; no FTO
                # loadouts are inferred from a Skill, division or group label.
                assert actual["fto_marker"] is None and actual["loadouts"] == []
                if actual["source_unit_id"] is not None:
                    assert source_units[actual["source_unit_id"]]["slug"] == original["slug"]
                else:
                    assert (army_id, team_id, row_id) == (899, 1, 4)
                    assert actual["unit"] is None and actual["reference_issues"]
                reviewed_rows += 1

            # Independently compare the named source selectors with native Unit
            # option occurrences; this is descriptive concordance, not legality.
            for source_id, expected_option_ids, name in (
                ((5, (13, 14, 15, 16, 17, 18, 23), "ORC Varuna Div."),
                 (15, (3, 19, 20), "MACHINIST Varuna Div")) if army_id == 105 else
                ((1822, (1, 2, 3), None),) if army_id == 1102 else ()
            ):
                original_unit = source_units[source_id]
                options = [option for group in original_unit["profileGroups"]
                           for option in group["options"]]
                assert tuple(option["id"] for option in options) == expected_option_ids
                if name:
                    assert all(option["name"] == name for option in options)
                status, _, body = wsgi_response(
                    application, f"http://test/api/units/{original_unit['slug']}",
                )
                assert status == 200
                unit = json.loads(body)
                local = next(army for army in unit["armies"] if army["id"] == army_id)
                assert [(option["option_id"], option["name"])
                        for option in local["loadouts"]] == [
                    (option["id"], option["name"]) for option in options
                ]
                if army_id == 1102:
                    assert [option["id"] for option in options
                            if any(skill["id"] == 251 for skill in option["skills"])] == [3]
                    assert [option["option_id"] for option in local["loadouts"]
                            if any(skill["id"] == 251 for skill in option["skills"])] == [3]
                    assert [option["name"] for option in options[:2]] == ["SHIZOKU FTO"] * 2
    assert reviewed_rows == 23


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


@pytest.mark.skipif(not ARMY_ZIP.exists(), reason="Pinned Army ZIP unavailable")
def test_pinned_member_reference_gaps_are_disclosed_without_replacement() -> None:
    database = Database(ARMY_DB)
    with zipfile.ZipFile(ARMY_ZIP) as archive:
        documents = {
            name: json.loads(archive.read(name)) for name in archive.namelist()
            if name.endswith(".json") and name != "metadata.json"
        }
    all_slugs = {unit["slug"] for source in documents.values() for unit in source["units"]}
    codes: Counter[str] = Counter()
    affected = unresolved = 0
    for army in database.list_fireteam_armies():
        chart = database.get_fireteam_chart(army["id"])
        assert chart is not None
        for team in chart["teams"]:
            for member in team["members"]:
                issues = member["reference_issues"]
                codes.update(issue["code"] for issue in issues)
                affected += bool(issues)
                if member["resolution"] == "unresolved":
                    unresolved += 1
                    assert member["slug"] not in all_slugs
                    assert member["unit"] is None
                elif member["resolution"] == "global":
                    assert army["id"] == 799
                    assert member["unit"]["id"] == 1178
                    assert member["slug"] not in {
                        unit["slug"] for unit in documents[chart["source"]["file"]]["units"]
                    }
                    assert member["loadouts"] == []
                elif member["fto_marker"] and not member["loadouts"]:
                    assert army["id"] == 499
                    assert member["source_unit_id"] == 1656
                    source = documents[chart["source"]["file"]]
                    korsan = next(unit for unit in source["units"] if unit["id"] == 1656)
                    options = [option for group in korsan["profileGroups"]
                               for option in group["options"]]
                    assert len(options) == 3
                    assert all("FTO" not in option["name"] for option in options)
    assert (affected, unresolved) == (13, 11)
    assert codes == {
        "unit-reference-unresolved": 11, "unit-not-in-army": 1,
        "fto-unit-context-mismatch": 1, "fto-option-unresolved": 1,
    }


def test_reinforcement_parent_chart_limits_remain_independent() -> None:
    database = Database(ARMY_DB)
    app = create_app(ARMY_DB, rules_database_path=ROOT / "data/generated/rules.db")
    sections = edges = unavailable_core = blocked_section_core = selectable = 0
    selectable_ids = {army["id"] for army in database.list_fireteam_armies()}
    for army in database.list_fireteam_armies():
        chart = database.get_fireteam_chart(army["id"])
        assert chart is not None
        if army["role"] != "reinforcement":
            assert chart["parent_charts"] == []
            continue
        sections += 1
        status, _, body = wsgi_response(app, f"http://test/api/fireteams?army_id={army['slug']}")
        assert status == 200
        published = json.loads(body)
        assert {parent["army"]["id"] for parent in published["parent_charts"]} == set(
            army["parent_army_ids"]
        )
        for parent in published["parent_charts"]:
            edges += 1
            parent_chart = database.get_fireteam_chart(parent["army"]["id"])
            assert parent_chart is not None
            assert parent["source"] == parent_chart["source"]
            assert parent["limits"] == parent_chart["limits"]
            assert parent["army"]["public_slug"]
            assert parent["selectable"] == (parent["army"]["id"] in selectable_ids)
            selectable += parent["selectable"]
            core_unavailable = any(limit["type"] == "CORE" and limit["max_count"] == 0
                                   for limit in parent["limits"])
            unavailable_core += core_unavailable
            blocked_section_core += core_unavailable and any(
                "CORE" in team["types"] for team in chart["teams"]
            )
    assert (sections, edges, unavailable_core, blocked_section_core) == (11, 46, 10, 9)
    assert selectable == 45
