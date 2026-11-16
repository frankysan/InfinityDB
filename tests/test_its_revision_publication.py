"""One season may publish old and hotfix revisions without redirecting either."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from infinity_db.its_season_database import build_its_database
from infinity_db.publication_registry import PublicationReference, PublicationRegistry
from infinity_db.rules_database import RulesDatabase
from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/generated"
HOTFIX_SOURCE = ROOT / "data/curated/its/n5-its-season-18-2026.09.11.json"
ORIGIN = "https://revision-test.example"


@pytest.fixture
def two_revisions(tmp_path: Path):
    hotfix = tmp_path / "its_18_2026.09.11.db"
    build_its_database(HOTFIX_SOURCE, hotfix)
    revisions = {
        "its-18": RELEASE / "its_18.db",
        "its-18@2026.09.11": hotfix,
    }
    rules = RulesDatabase(RELEASE / "rules_n5.db")
    return PublicationRegistry(rules, revisions), create_app(
        RELEASE / "army.db", RELEASE / "rules_n5.db", season_databases=revisions,
    )


def _json(app, path: str) -> tuple[int, dict, dict]:
    status, headers, data = wsgi_response(app, ORIGIN + path)
    return status, dict(headers), json.loads(data)


def test_both_its_revisions_registered_and_no_cross_version_fallback(two_revisions) -> None:
    registry, app = two_revisions
    assert set(registry.season_manifest()) == {"its-18", "its-18@2026.09.11"}
    assert registry.has_season("its-18", "2026.09.01")
    assert registry.has_season("its-18", "2026.09.11")
    assert not registry.has_season("its-18", "2026.09.12")
    assert registry.resolve(PublicationReference(
        "its-18", "scenario:the-dig", "2026.09.01",
    )) is None

    summaries = {}
    for revision, expected_ids in (
        ("2026.09.01", ["battleground"]),
        ("2026.09.11", [
            "crossing-lines", "double-bind", "the-dig", "annihilation",
            "battleground", "cutthroat", "superiority", "uplink-center", "hardlock",
            "b-pong", "akial-interference", "evacuation", "neutralization",
            "provisioning", "area-of-interest",
        ]),
    ):
        status, _, payload = _json(
            app, f"/api/scenarios?collection=its-18&revision={revision}",
        )
        assert status == 200
        summaries[revision] = payload["items"]
        assert [entry["id"] for entry in payload["items"]] == expected_ids
        assert all(item["publication"]["revision"] == revision for item in payload["items"])

    assert len(summaries["2026.09.01"]) == 1
    status, _, payload = _json(app, "/api/scenarios")
    assert status == 200
    collections = {
        (item["id"], item["revision"]): item
        for item in payload["collections"]
    }
    assert collections[("its-18", "2026.09.11")]["scenario_count"] == 15
    assert collections[("its-18", "2026.09.01")]["scenario_count"] == 1
    assert _json(app, "/api/scenarios?collection=its-18&revision=2026.09.12")[2]["items"] == []


def test_battleground_and_policies_bind_correct_edition_sources(two_revisions) -> None:
    registry, app = two_revisions
    for revision, pages in (("2026.09.01", [121, 122, 123]), ("2026.09.11", [129, 130, 131])):
        uri = (
            f"/api/scenarios/battleground?army_points=300"
            f"&collection=its-18&revision={revision}"
        )
        status, headers, item = _json(app, uri)
        assert status == 200
        assert item["publication"]["revision"] == revision
        assert [citation["page"] for citation in item["citations"]] == pages
        assert item["publication"]["sources"][0]["version"] == revision
        status, _, policy = _json(
            app, "/api/season-policies?season_id=its-18"
            f"&season_revision={revision}&context=official-tournament",
        )
        assert status == 200
        assert len(policy["items"]) == 1
        assert policy["items"][0]["citations"][0]["sourceVersion"] == revision
        assert wsgi_response(app, ORIGIN + uri.replace(
            "/api/scenarios/battleground?", "/api/scenarios/battleground/map.svg?",
        ))[0] == 200

    status, _, the_dig = _json(
        app, "/api/scenarios/the-dig?army_points=150"
        "&collection=its-18&revision=2026.09.11",
    )
    assert status == 200
    assert the_dig["placement"]["geometry"]["table"]["width"] == 24
    assert (
        the_dig["placement"]["marker_dimensions"][0]["citation"]["source_version"]
        == "2026.09.11"
    )
    status, _, double_bind = _json(
        app, "/api/scenarios/double-bind?army_points=300"
        "&collection=its-18&revision=2026.09.11",
    )
    assert status == 200
    assert len(double_bind["objective_selection"]["sets"]) == 3
    assert double_bind["objective_selection"]["sets"][0]["id"] == "encryption"
    assert all(o["awards"] for o in double_bind["objectives"])

    assert registry.source_citation(
        season_id="its-18", source_id="its-season-18-en-pdf",
        revision="2026.09.11", page=17,
    )["source_version"] == "2026.09.11"


def test_cutthroat_serves_six_game_sizes_only_in_the_hotfix_revision(two_revisions) -> None:
    _registry, app = two_revisions
    for points, deployment_depth in ((150, 12), (200, 16), (300, 16), (400, 16)):
        uri = (
            f"/api/scenarios/cutthroat?army_points={points}"
            "&collection=its-18&revision=2026.09.11"
        )
        status, _, item = _json(app, uri)
        assert status == 200
        assert item["publication"]["revision"] == "2026.09.11"
        assert item["selected_army_points"] == points
        zones = {e["id"]: e for e in item["placement"]["geometry"]["elements"]}
        assert zones["deployment-a"]["y2"] == deployment_depth
        assert len(item["objectives"]) == 4
        assert {issue["id"] for issue in item["source_issues"]} == {
            "lieutenant-kill-bilingual-definition", "key-ops-without-designation",
        }
        map_uri = uri.replace(
            "/api/scenarios/cutthroat?", "/api/scenarios/cutthroat/map.svg?",
        )
        assert wsgi_response(app, ORIGIN + map_uri)[0] == 200

    status, _, _ = _json(
        app, "/api/scenarios/cutthroat?army_points=300"
        "&collection=its-18&revision=2026.09.01",
    )
    assert status == 404


def test_superiority_is_published_only_in_the_hotfix_with_source_matched_maps(
    two_revisions,
) -> None:
    registry, app = two_revisions
    assert registry.resolve(PublicationReference(
        "its-18", "scenario:superiority", "2026.09.01",
    )) is None
    for points, width, depth in (
        (150, 24, 8), (200, 32, 12), (250, 32, 12),
        (300, 48, 12), (350, 48, 12), (400, 48, 12),
    ):
        uri = (
            f"/api/scenarios/superiority?army_points={points}"
            "&collection=its-18&revision=2026.09.11"
        )
        status, _, item = _json(app, uri)
        assert status == 200
        assert item["selected_army_points"] == points
        assert item["publication"]["revision"] == "2026.09.11"
        assert item["placement"]["geometry"]["table"]["width"] == width
        zones = {e["id"]: e for e in item["placement"]["geometry"]["elements"]}
        assert zones["deployment-a"]["y2"] == depth
        assert {name for name in zones if name.startswith("console-q")} == {
            "console-q1", "console-q2", "console-q3", "console-q4",
        }
        assert len(item["objectives"]) == 2
        assert [source["page"] for source in item["citations"]] == [
            135, 136, 137, 138, 140, 141, 142, 143,
        ]
        assert [issue["id"] for issue in item["source_issues"]] == [
            "shasvastii-bilingual-zo-status",
        ]
        map_uri = uri.replace(
            "/api/scenarios/superiority?", "/api/scenarios/superiority/map.svg?",
        )
        assert wsgi_response(app, ORIGIN + map_uri)[0] == 200

    assert _json(
        app, "/api/scenarios/superiority?army_points=300"
        "&collection=its-18&revision=2026.09.01",
    )[0] == 404


def test_uplink_center_activation_control_and_physical_markers_reach_api(
    two_revisions,
) -> None:
    registry, app = two_revisions
    assert registry.resolve(PublicationReference(
        "its-18", "scenario:uplink-center", "2026.09.01",
    )) is None
    for points, width, height, depth in (
        (150, 24, 32, 12), (200, 32, 48, 16), (250, 32, 48, 16),
        (300, 48, 48, 16), (350, 48, 48, 16), (400, 48, 48, 16),
    ):
        uri = (
            f"/api/scenarios/uplink-center?army_points={points}"
            "&collection=its-18&revision=2026.09.11"
        )
        status, _, item = _json(app, uri)
        assert status == 200
        assert item["selected_army_points"] == points
        assert item["publication"]["revision"] == "2026.09.11"
        geometry = item["placement"]["geometry"]
        assert geometry["table"] == {"width": width, "height": height, "unit": "in"}
        elements = {e["id"]: e for e in geometry["elements"]}
        assert elements["deployment-a"]["y2"] == depth
        assert elements["deployment-b"]["y1"] == height - depth
        assert elements["antenna-left"]["x"] == width / 4
        assert elements["tech-coffin"]["x"] == width / 2
        assert elements["antenna-right"]["x"] == width * 3 / 4
        assert all(elements[id]["y"] == height / 2 for id in (
            "antenna-left", "tech-coffin", "antenna-right",
        ))
        assert {obj["id"]: obj["maximumPoints"] for obj in item["objectives"]} == {
            "activate-communication-antennas": 4,
            "control-communication-antennas": 2,
            "control-tech-coffin": 3,
            "active-lieutenant": 1,
        }
        assert {
            marker["marker_type"]: (marker["count"], marker["diameter_mm"])
            for marker in item["placement"]["marker_dimensions"]
        } == {"antenna": (2, 40), "tech-coffin": (1, 40)}
        assert [c["page"] for c in item["citations"]] == [
            139, 140, 141, 142, 144, 145, 146, 147,
        ]
        map_uri = uri.replace(
            "/api/scenarios/uplink-center?", "/api/scenarios/uplink-center/map.svg?",
        )
        assert wsgi_response(app, ORIGIN + map_uri)[0] == 200
    assert _json(
        app, "/api/scenarios/uplink-center?army_points=300"
        "&collection=its-18&revision=2026.09.01",
    )[0] == 404



def test_hardlock_is_only_in_hotfix_with_beacon_and_console_positions(two_revisions) -> None:
    registry, app = two_revisions
    assert registry.resolve(PublicationReference(
        "its-18", "scenario:hardlock", "2026.09.01",
    )) is None
    for points, width, height, depth in (
        (150, 24, 32, 8), (200, 32, 48, 12), (250, 32, 48, 12),
        (300, 48, 48, 12), (350, 48, 48, 12), (400, 48, 48, 12),
    ):
        uri = (
            f"/api/scenarios/hardlock?army_points={points}"
            "&collection=its-18&revision=2026.09.11"
        )
        status, _, item = _json(app, uri)
        assert status == 200
        assert item["publication"]["revision"] == "2026.09.11"
        assert item["selected_army_points"] == points
        assert {o["id"]: o["maximumPoints"] for o in item["objectives"]} == {
            "control-enemy-beacon": 3, "protect-own-beacon": 1,
            "activate-more-consoles": 2, "activate-each-console": 3,
            "classified-objective": 1,
        }
        geometry = item["placement"]["geometry"]
        assert geometry["table"] == {"width": width, "height": height, "unit": "in"}
        elements = {e["id"]: e for e in geometry["elements"]}
        assert elements["deployment-a"]["y2"] == depth
        assert elements["deployment-b"]["y1"] == height - depth
        assert (elements["beacon-a"]["x"], elements["beacon-a"]["y"]) == (
            width / 2, depth,
        )
        assert (elements["beacon-b"]["x"], elements["beacon-b"]["y"]) == (
            width / 2, height - depth,
        )
        assert {
            name: (elements[name]["x"], elements[name]["y"])
            for name in ("console-left", "console-center", "console-right")
        } == {
            "console-left": (width / 4, height / 2),
            "console-center": (width / 2, height / 2),
            "console-right": (3 * width / 4, height / 2),
        }
        assert {
            m["marker_type"]: (m["count"], m["diameter_mm"])
            for m in item["placement"]["marker_dimensions"]
        } == {"beacon": (2, None), "console": (3, 40)}
        assert [c["page"] for c in item["citations"]] == [
            49, 50, 51, 52, 127, 128, 129, 130,
        ]
        assert {issue["id"] for issue in item["source_issues"]} == {
            "connected-vs-activated-console", "allied-beacon-carrier-normal-state",
        }
        svg_uri = uri.replace(
            "/api/scenarios/hardlock?", "/api/scenarios/hardlock/map.svg?",
        )
        svg_status, _, svg = wsgi_response(app, ORIGIN + svg_uri)
        assert svg_status == 200
        assert svg.count(b'data-marker-type="beacon"') == 2
        assert svg.count(b'data-marker-type="console" data-diameter-mm="40"') == 3
        assert b'data-physical-size="unspecified"' in svg

    assert _json(
        app, "/api/scenarios/hardlock?army_points=300"
        "&collection=its-18&revision=2026.09.01",
    )[0] == 404



def test_b_pong_api_all_game_sizes_and_historical_isolation(two_revisions) -> None:
    registry, app = two_revisions
    assert registry.resolve(PublicationReference(
        "its-18", "scenario:b-pong", "2026.09.01",
    )) is None
    for points, width, height, depth, exclusion in (
        (150, 24, 32, 12, 2), (200, 32, 48, 16, 4),
        (250, 32, 48, 16, 4), (300, 48, 48, 16, 4),
        (350, 48, 48, 16, 4), (400, 48, 48, 16, 4),
    ):
        url = (
            f"/api/scenarios/b-pong?army_points={points}"
            "&collection=its-18&revision=2026.09.11"
        )
        status, _, item = _json(app, url)
        assert status == 200
        assert item["selected_army_points"] == points
        assert item["publication"]["revision"] == "2026.09.11"
        assert item["setup"]["game_size"]["swc"] == {
            150: 3, 200: 4, 250: 5, 300: 6, 350: 7, 400: 8,
        }[points]
        elements = {e["id"]: e for e in item["placement"]["geometry"]["elements"]}
        assert elements["deployment-a"]["y2"] == depth
        assert elements["deployment-b"]["y1"] == height - depth
        assert elements["exclusion-zone"]["y1"] == height / 2 - exclusion
        assert elements["exclusion-zone"]["y2"] == height / 2 + exclusion
        assert elements["tracking-beacon"]["x"] == width / 2
        assert elements["tracking-beacon"]["y"] == height / 2
        assert elements["console-left"]["x"] == width / 4
        assert elements["console-right"]["x"] == width * 3 / 4
        markers = {m["marker_type"]: m for m in item["placement"]["marker_dimensions"]}
        assert markers["tracking-beacon"]["diameter_mm"] is None
        assert markers["tracking-beacon"]["size_status"] == "source-conflict"
        assert markers["tracking-beacon"]["citation"] is None
        assert markers["console"]["diameter_mm"] == 40
        assert [c["page"] for c in item["citations"]] == [
            59, 60, 61, 62, 58, 59, 60, 61, 62,
        ]
        assert len(item["source_issues"]) == 5
        assert sum(o["maximumPoints"] for o in item["objectives"]) == 10
        svg_url = url.replace(
            "/api/scenarios/b-pong?", "/api/scenarios/b-pong/map.svg?",
        )
        svg_status, _, svg = wsgi_response(app, ORIGIN + svg_url)
        assert svg_status == 200
        assert b'data-physical-size="conflicting-sources"' in svg
        assert svg.count(b'data-marker-type="console" data-diameter-mm="40"') == 2
        assert b'id="scenario-exclusion-hatch"' in svg

    assert _json(
        app, "/api/scenarios/b-pong?army_points=300"
        "&collection=its-18&revision=2026.09.01",
    )[0] == 404



def test_akial_interference_api_six_sizes_sources_and_historical_isolation(
    two_revisions,
) -> None:
    registry, app = two_revisions
    assert registry.resolve(PublicationReference(
        "its-18", "scenario:akial-interference", "2026.09.01",
    )) is None
    for points, width, height, depth in (
        (150, 24, 32, 8), (200, 32, 48, 12), (250, 32, 48, 12),
        (300, 48, 48, 12), (350, 48, 48, 12), (400, 48, 48, 12),
    ):
        uri = (
            f"/api/scenarios/akial-interference?army_points={points}"
            "&collection=its-18&revision=2026.09.11"
        )
        status, _, item = _json(app, uri)
        assert status == 200
        assert item["selected_army_points"] == points
        assert item["publication"]["revision"] == "2026.09.11"
        assert item["setup"]["game_size"]["swc"] == points / 50
        geometry = item["placement"]["geometry"]
        assert geometry["table"] == {"width": width, "height": height, "unit": "in"}
        elements = {e["id"]: e for e in geometry["elements"]}
        assert elements["deployment-a"]["y2"] == depth
        assert elements["deployment-b"]["y1"] == height - depth
        antenna = elements["akial-antenna"]
        assert (antenna["x"], antenna["y"]) == (width / 2, height / 2)
        assert len(item["placement"]["marker_dimensions"]) == 1
        assert {
            m["marker_type"]: (m["count"], m["diameter_mm"])
            for m in item["placement"]["marker_dimensions"]
        } == {"antenna": (1, 40)}
        assert [c["page"] for c in item["citations"]] == [92, 93, 94, 95, 96] * 2
        assert {o["id"]: o["maximumPoints"] for o in item["objectives"]} == {
            "common-classified": 6, "more-classified": 1,
            "classified-every-round": 1, "private-classified": 2,
        }
        assert [i["id"] for i in item["source_issues"]] == [
            "emit-once-per-round-vs-retries",
        ]
        svg_uri = uri.replace(
            "/api/scenarios/akial-interference?",
            "/api/scenarios/akial-interference/map.svg?",
        )
        svg_status, _, svg = wsgi_response(app, ORIGIN + svg_uri)
        assert svg_status == 200
        assert svg.count(b'data-marker-type="antenna" data-diameter-mm="40"') == 1
        assert b'id="antenna-from-right"' in svg

    assert _json(
        app, "/api/scenarios/akial-interference?army_points=300"
        "&collection=its-18&revision=2026.09.01",
    )[0] == 404



def test_evacuation_six_game_sizes_schematic_civilians_and_revision_isolation(
    two_revisions,
) -> None:
    registry, app = two_revisions
    assert registry.resolve(PublicationReference(
        "its-18", "scenario:evacuation", "2026.09.01",
    )) is None
    for points, width, height, depth, console_offset in (
        (150, 24, 32, 8, 4), (200, 32, 48, 12, 4),
        (250, 32, 48, 12, 4), (300, 48, 48, 12, 8),
        (350, 48, 48, 12, 8), (400, 48, 48, 12, 8),
    ):
        url = (
            f"/api/scenarios/evacuation?army_points={points}"
            "&collection=its-18&revision=2026.09.11"
        )
        status, _, item = _json(app, url)
        assert status == 200
        assert item["selected_army_points"] == points
        assert item["publication"]["revision"] == "2026.09.11"
        assert item["setup"]["game_size"]["swc"] == points // 50
        geometry = item["placement"]["geometry"]
        assert geometry["table"] == {"width": width, "height": height, "unit": "in"}
        elements = {e["id"]: e for e in geometry["elements"]}
        assert elements["deployment-a"]["y2"] == depth
        assert elements["deployment-b"]["y1"] == height - depth
        assert elements["console-left"]["x"] == width / 2 - console_offset
        assert elements["console-right"]["x"] == width / 2 + console_offset
        assert elements["civilian-left-top"]["x"] == 6
        assert elements["civilian-left-top"]["y"] == depth + 4
        assert elements["civilian-right-bottom"]["x"] == width - 6
        assert elements["civilian-right-bottom"]["y"] == height - depth - 4
        markers = {m["marker_type"]: m for m in item["placement"]["marker_dimensions"]}
        assert markers["civilian"]["count"] == 4
        assert markers["civilian"]["diameter_mm"] is None
        assert markers["civilian"]["citation"] is None
        assert markers["console"]["count"] == 2
        assert markers["console"]["diameter_mm"] == 40
        assert [c["page"] for c in item["citations"]] == [88, 89, 90, 91] * 2
        assert {o["id"]: o["maximumPoints"] for o in item["objectives"]} == {
            "extracted-civilians": 4,
            "extracted-enemy-hvts": 2,
            "classified-objectives": 4,
        }
        assert len(item["source_issues"]) == 3
        svg_url = url.replace("/api/scenarios/evacuation?",
                              "/api/scenarios/evacuation/map.svg?")
        svg_status, _, svg = wsgi_response(app, ORIGIN + svg_url)
        assert svg_status == 200
        assert svg.count(b'data-marker-type="civilian" data-physical-size="unspecified"') == 4
        assert svg.count(b'data-physical-size="unspecified"') == 4
        assert svg.count(b'data-marker-type="console" data-diameter-mm="40"') == 2

    assert _json(
        app, "/api/scenarios/evacuation?army_points=300"
        "&collection=its-18&revision=2026.09.01",
    )[0] == 404



def test_neutralization_six_sizes_controlled_antennas_and_revision_isolation(
    two_revisions,
) -> None:
    registry, app = two_revisions
    assert registry.resolve(PublicationReference(
        "its-18", "scenario:neutralization", "2026.09.01",
    )) is None
    for points, width, height, depth, box_x in (
        (150, 24, 32, 8, 8), (200, 32, 48, 12, 12),
        (250, 32, 48, 12, 12), (300, 48, 48, 12, 20),
        (350, 48, 48, 12, 20), (400, 48, 48, 12, 20),
    ):
        uri = (
            f"/api/scenarios/neutralization?army_points={points}"
            "&collection=its-18&revision=2026.09.11"
        )
        status, _, item = _json(app, uri)
        assert status == 200
        assert item["selected_army_points"] == points
        assert item["publication"]["revision"] == "2026.09.11"
        assert item["setup"]["game_size"]["swc"] == points // 50
        geometry = item["placement"]["geometry"]
        assert geometry["table"] == {"width": width, "height": height, "unit": "in"}
        elements = {e["id"]: e for e in geometry["elements"]}
        assert elements["deployment-a"]["y2"] == depth
        assert elements["deployment-b"]["y1"] == height - depth
        assert elements["exclusion-zone"]["y1"] == height / 2 - 4
        assert elements["exclusion-zone"]["y2"] == height / 2 + 4
        assert elements["tech-box-left"]["x"] == box_x
        assert elements["tech-box-right"]["x"] == width - box_x
        assert {e["id"] for e in elements.values() if e["kind"] == "circle"} == {
            "neutralization-area-a-left", "neutralization-area-a-right",
            "neutralization-area-b-left", "neutralization-area-b-right",
        }
        assert all(e["radius"] == 2.5 for e in elements.values() if e["kind"] == "circle")
        markers = {m["marker_type"]: m for m in item["placement"]["marker_dimensions"]}
        assert {key: (m["count"], m["diameter_mm"]) for key, m in markers.items()} == {
            "antenna": (4, 40), "tech-coffin": (2, 40),
        }
        assert [c["page"] for c in item["citations"]] == [105, 106, 107, 108, 109] * 2
        assert {o["id"]: o["maximumPoints"] for o in item["objectives"]} == {
            "neutralize-hyperthermal-techs": 4,
            "neutralize-more-techs": 1,
            "control-more-antennas": 3,
            "classified-objective": 2,
        }
        assert item["objectives"][2]["awards"][0]["condition"]["kind"] == (
            "element-status-comparison"
        )
        assert len(item["source_issues"]) == 2
        svg_uri = uri.replace(
            "/api/scenarios/neutralization?", "/api/scenarios/neutralization/map.svg?",
        )
        svg_status, _, svg = wsgi_response(app, ORIGIN + svg_uri)
        assert svg_status == 200
        assert svg.count(b'data-marker-type="antenna" data-diameter-mm="40"') == 4
        assert svg.count(b'data-marker-type="tech-coffin" data-diameter-mm="40"') == 2
        assert b'id="scenario-exclusion-hatch"' in svg

    assert _json(
        app, "/api/scenarios/neutralization?army_points=300"
        "&collection=its-18&revision=2026.09.01",
    )[0] == 404



def test_provisioning_six_sizes_safe_areas_and_revision_isolation(two_revisions) -> None:
    registry, app = two_revisions
    assert registry.resolve(PublicationReference(
        "its-18", "scenario:provisioning", "2026.09.01",
    )) is None
    for points, width, height, radius, spacing in (
        (150, 24, 32, 12, 8),
        (200, 32, 48, 20, 12),
        (250, 32, 48, 20, 12),
        (300, 48, 48, 24, 16),
        (350, 48, 48, 24, 16),
        (400, 48, 48, 24, 16),
    ):
        uri = (
            f"/api/scenarios/provisioning?army_points={points}"
            "&collection=its-18&revision=2026.09.11"
        )
        status, _, item = _json(app, uri)
        assert status == 200
        assert item["selected_army_points"] == points
        assert item["publication"]["revision"] == "2026.09.11"
        assert item["setup"]["game_size"]["swc"] == points // 50
        geometry = item["placement"]["geometry"]
        assert geometry["table"] == {"width": width, "height": height, "unit": "in"}
        elements = {e["id"]: e for e in geometry["elements"]}
        assert {elements[id]["radius"] for id in ("deployment-a", "deployment-b")} == {
            radius
        }
        assert {e["id"] for e in elements.values() if e["kind"] == "marker"} == {
            "coffin-upper", "coffin-center", "coffin-lower",
        }
        assert not any(e["kind"] == "circle" for e in elements.values())
        assert {m["marker_type"]: (m["count"], m["diameter_mm"])
                for m in item["placement"]["marker_dimensions"]} == {
            "tech-coffin": (3, 40),
        }
        ruler = next(a for a in geometry["annotations"]
                     if a["id"] == "coffin-center-to-lower")
        assert ruler["x1"] == width / 2
        assert ruler["y1"] == height / 2
        assert [c["page"] for c in item["citations"]] == [
            110, 111, 112, 113, 114, 110, 111, 112, 113, 114, 115,
        ]
        assert {o["id"]: o["maximumPoints"] for o in item["objectives"]} == {
            "control-supply-boxes": 4, "safe-area-comparison": 3,
            "opponent-empty-safe-area": 2, "classified-objective": 1,
        }
        assert len(item["source_issues"]) == 5
        svg_uri = uri.replace(
            "/api/scenarios/provisioning?", "/api/scenarios/provisioning/map.svg?",
        )
        svg_status, _, svg = wsgi_response(app, ORIGIN + svg_uri)
        assert svg_status == 200
        assert svg.count(b'data-marker-type="tech-coffin" data-diameter-mm="40"') == 3
        assert f'data-distance-inches="{spacing}"'.encode() in svg

    assert _json(
        app, "/api/scenarios/provisioning?army_points=300"
        "&collection=its-18&revision=2026.09.01",
    )[0] == 404


def test_area_of_interest_six_sizes_center_antenna_and_revision_isolation(
    two_revisions,
) -> None:
    registry, app = two_revisions
    assert registry.resolve(PublicationReference(
        "its-18", "scenario:area-of-interest", "2026.09.01",
    )) is None
    for points, width, height, radius in (
        (150, 24, 32, 12),
        (200, 32, 48, 20),
        (250, 32, 48, 20),
        (300, 48, 48, 24),
        (350, 48, 48, 24),
        (400, 48, 48, 24),
    ):
        uri = (
            f"/api/scenarios/area-of-interest?army_points={points}"
            "&collection=its-18&revision=2026.09.11"
        )
        status, _, item = _json(app, uri)
        assert status == 200
        assert item["selected_army_points"] == points
        assert item["publication"]["revision"] == "2026.09.11"
        assert item["setup"]["game_size"]["swc"] == points // 50
        geometry = item["placement"]["geometry"]
        assert geometry["table"] == {"width": width, "height": height, "unit": "in"}
        elements = {e["id"]: e for e in geometry["elements"]}
        assert {elements[id]["radius"] for id in (
            "deployment-a", "deployment-b",
        )} == {radius}
        assert {e["id"] for e in elements.values() if e["kind"] == "marker"} == {
            "communication-antenna",
        }
        assert not any(e["kind"] == "circle" for e in elements.values())
        assert {m["marker_type"]: (m["count"], m["diameter_mm"])
                for m in item["placement"]["marker_dimensions"]} == {
            "antenna": (1, 40),
        }
        assert [c["page"] for c in item["citations"]] == [
            *range(121, 125), *range(122, 127),
        ]
        assert {o["id"]: o["maximumPoints"] for o in item["objectives"]} == {
            "dominate-areas": 3, "dominate-special-area": 3,
            "activate-antenna": 3, "classified-objective": 1,
        }
        assert len(item["source_issues"]) == 3
        svg_uri = uri.replace(
            "/api/scenarios/area-of-interest?", "/api/scenarios/area-of-interest/map.svg?",
        )
        svg_status, _, svg = wsgi_response(app, ORIGIN + svg_uri)
        assert svg_status == 200
        assert svg.count(b'data-marker-type="antenna" data-diameter-mm="40"') == 1
        assert f'data-distance-inches="{radius}"'.encode() in svg
        assert f'data-distance-inches="{height / 2:g}"'.encode() in svg

    assert _json(
        app, "/api/scenarios/area-of-interest?army_points=300"
        "&collection=its-18&revision=2026.09.01",
    )[0] == 404

def test_mislabeled_revision_and_duplicate_registration_fail_closed(tmp_path: Path) -> None:
    hotfix = tmp_path / "hotfix.db"
    build_its_database(HOTFIX_SOURCE, hotfix)
    rules = RulesDatabase(RELEASE / "rules_n5.db")
    with pytest.raises(ValueError, match="registration does not match"):
        PublicationRegistry(rules, {"its-18@2026.09.01": hotfix})
    with pytest.raises(ValueError, match="Duplicate registered ITS season/revision"):
        PublicationRegistry(rules, {
            "its-18": hotfix,
            "its-18@2026.09.11": hotfix,
        })
