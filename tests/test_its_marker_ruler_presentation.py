"""Regression coverage for source-sized ITS tokens and marker-adjacent placement rulers."""

from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree

import pytest

from infinity_db.scenario_geometry import marker_diameter_mm, parse_scenario_geometry
from infinity_db.scenario_map_svg import render_scenario_map_svg

ROOT = Path(__file__).resolve().parents[1]
ITS18 = ROOT / "data/curated/its/n5-its-season-18.json"
ITS17_SHARED = ROOT / "data/curated/its/shared/its17-scenarios-v1.json"
SVG_NS = "{http://www.w3.org/2000/svg}"

# These are marker-placement guides, not Deployment Zone, region-radius or
# scenario-rule distance measurements. Their endpoints describe the actual
# measured positions; only the offset locates the visible line on the map.
MARKER_PLACEMENT_RULERS = frozenset({
    "antenna-middle-from-left",
    "antenna-right-from-right",
    "tech-coffin-from-left",
    "console-center-from-left",
    "console-right-from-right",
    "beacon-from-left",
    "right-console-from-right",
    "antenna-from-right",
    "tech-box-left-from-left",
    "coffin-center-from-left",
    "coffin-right-from-edge",
    "id-checker-center-from-left",
    "scanner-right-from-edge",
    "prototype-left-from-edge",
    "prototype-right-from-edge",
    "alpha-center-from-left",
    "room-center-from-left",
    "console-left-from-left",
    "civilian-right-from-right",
})


def test_its_token_chart_has_canonical_size_for_each_fixed_footprint() -> None:
    # ITS 17 V0.2 EN p.13 / ITS 18 2026.09.11 EN p.18.
    for marker, size_mm in {
        "antenna": 40,
        "tech-coffin": 40,
        "console": 40,
        "objective": 40,
        "supply-box": 25,
        "beacon": 25,
        "player-a-b": 25,
        "data-pack": 25,
        "defensive-turret": 25,
        "civevac": 25,
        "civilian": 25,
        "hyperthermal-tech": 25,
    }.items():
        assert marker_diameter_mm(marker) == size_mm

    # B-Pong Tracking Beacon has a documented EN/ES size disagreement.
    assert marker_diameter_mm("tracking-beacon") is None


@pytest.mark.parametrize(
    ("source", "expected_count"),
    [(ITS18, 63), (ITS17_SHARED, 45)],
    ids=["its-18", "its-17"],
)
def test_marker_placement_rulers_measure_markers_but_draw_below_them(
    source: Path, expected_count: int,
) -> None:
    document = json.loads(source.read_text(encoding="utf-8"))
    records = (
        document["records"] if source == ITS18
        else [entry["record"] for entry in document["definitions"]]
    )
    examined = 0
    for record in records:
        if record["kind"] != "scenario":
            continue
        for configuration in record["facts"]["configurations"]:
            geometry = configuration["geometry"]
            markers = [e for e in geometry["elements"] if e["kind"] == "marker"]
            for marker in markers:
                diameter = marker_diameter_mm(marker["markerType"])
                if marker["markerType"] == "tracking-beacon":
                    assert diameter is None
                else:
                    assert diameter is not None, (
                        record["name"], configuration["id"], marker["markerType"]
                    )
            placement = [
                a for a in geometry.get("annotations", [])
                if a["kind"] == "ruler" and a["id"] in MARKER_PLACEMENT_RULERS
            ]
            if not placement:
                continue
            root = ElementTree.fromstring(
                render_scenario_map_svg(parse_scenario_geometry(geometry))
            )
            by_id = {node.get("id"): node for node in root.iter() if node.get("id")}
            for ruler in placement:
                assert ruler["y1"] == ruler["y2"], (record["name"], ruler["id"])
                assert ruler["offset"] == 2.5, (record["name"], ruler["id"])
                assert any(
                    marker["x"] in (ruler["x1"], ruler["x2"])
                    and marker["y"] == ruler["y1"]
                    for marker in markers
                ), (record["name"], configuration["id"], ruler["id"])

                group = by_id[ruler["id"]]
                line = group.find(f"{SVG_NS}line")
                assert line is not None
                for coordinate, expected in (
                    ("y1", ruler["y1"] + 2.5),
                    ("y2", ruler["y2"] + 2.5),
                    ("x1", ruler["x1"]),
                    ("x2", ruler["x2"]),
                ):
                    resolved = line.get(coordinate)
                    assert resolved is not None
                    assert float(resolved) == pytest.approx(expected)
                examined += 1

            if record["name"] in {"Double Bind", "B-Pong"}:
                verticals = {
                    a["id"]: a for a in geometry["annotations"]
                    if a["kind"] == "ruler" and a["x1"] == a["x2"]
                }
                if record["name"] == "Double Bind":
                    guide = verticals["exclusion-from-center"]
                    assert guide["x1"] == geometry["table"]["width"] * 5 / 8
                else:
                    for name in ("exclusion-a-radius", "exclusion-b-radius"):
                        assert verticals[name]["x1"] == geometry["table"]["width"] / 2 + 2

    assert examined == expected_count
