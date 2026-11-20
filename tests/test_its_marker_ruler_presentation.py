"""Regression coverage for source-sized ITS tokens and marker-adjacent placement rulers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal
from xml.etree import ElementTree

import pytest

from infinity_db.scenario_geometry import marker_diameter_mm, parse_scenario_geometry
from infinity_db.scenario_map_svg import render_scenario_map_svg

ROOT = Path(__file__).resolve().parents[1]
ITS18 = ROOT / "data/curated/its/n5-its-season-18.json"
ITS17_SHARED = ROOT / "data/curated/its/shared/its17-scenarios-v1.json"
SVG_NS = "{http://www.w3.org/2000/svg}"

# One canonical diameter for every mission rule that defines an area using
# a Circular Template, including areas placed by players rather than on maps.
CIRCULAR_TEMPLATE_MISSIONS = {
    ITS18: {
        "scenario:double-bind", "scenario:neutralization", "scenario:provisioning",
        "scenario:area-of-interest", "scenario:data-harvest", "scenario:outbreak",
    },
    ITS17_SHARED: {
        "scenario:provisioning", "scenario:area-of-interest", "scenario:outbreak",
    },
}


@pytest.mark.parametrize("source", [ITS18, ITS17_SHARED], ids=["its-18", "its-17"])
def test_all_circular_template_missions_state_12_cm_diameter(source: Path) -> None:
    document = json.loads(source.read_text(encoding="utf-8"))
    records = (
        document["records"] if source == ITS18
        else [entry["record"] for entry in document["definitions"]]
    )
    found: set[str] = set()
    for record in records:
        if record["kind"] != "scenario":
            continue
        paragraphs = [
            paragraph
            for rule in record["facts"]["mission"]["rules"]
            for paragraph in rule["paragraphs"]
        ]
        if any("Circular Template" in paragraph for paragraph in paragraphs):
            found.add(record["id"])
            assert any(
                "[[distance:12:cm]] diameter" in paragraph for paragraph in paragraphs
            ), record["id"]

        for configuration in record["facts"]["configurations"]:
            circles = [
                element for element in configuration["geometry"]["elements"]
                if element["kind"] == "circle"
            ]
            if circles:
                assert record["id"] in CIRCULAR_TEMPLATE_MISSIONS[source]
                assert all(
                    element["style"] == "influence" and element["radius"] == 2.5
                    for element in circles
                ), record["id"]

    assert found == CIRCULAR_TEMPLATE_MISSIONS[source]


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


@pytest.mark.parametrize("distance_unit", ["in", "cm"])
def test_neutralization_ruler_labels_clear_antenna_areas(
    distance_unit: Literal["in", "cm"],
) -> None:
    document = json.loads(ITS18.read_text(encoding="utf-8"))
    record = next(r for r in document["records"] if r["id"] == "scenario:neutralization")
    for configuration in record["facts"]["configurations"]:
        geometry = configuration["geometry"]
        elements = {e["id"]: e for e in geometry["elements"]}
        annotations = {a["id"]: a for a in geometry["annotations"]}
        area = elements["neutralization-area-a-right"]
        left_area = elements["neutralization-area-a-left"]
        ruler = annotations["antenna-right-from-right"]
        depth = annotations["deployment-a-depth"]
        deployment_depth = elements["deployment-a"]["y2"]

        # Measure the actual right-hand Antenna center, but draw entirely above
        # its circular region; move the vertical depth guide to the opposite edge.
        assert (ruler["x1"], ruler["x2"], ruler["y1"], ruler["y2"]) == (
            area["x"], geometry["table"]["width"], area["y"], area["y"],
        )
        assert ruler["offset"] == -3.0
        assert (depth["side"], depth["offset"]) == ("start", 0.8)

        root = ElementTree.fromstring(render_scenario_map_svg(
            parse_scenario_geometry(geometry), distance_unit=distance_unit,
        ))
        by_id = {node.get("id"): node for node in root.iter() if node.get("id")}
        ruler_group = by_id[ruler["id"]]
        ruler_line = ruler_group.find(f"{SVG_NS}line")
        ruler_label = ruler_group.find(f"{SVG_NS}text")
        depth_group = by_id[depth["id"]]
        depth_line = depth_group.find(f"{SVG_NS}line")
        depth_label = depth_group.find(f"{SVG_NS}text")
        assert all(node is not None for node in (
            ruler_line, ruler_label, depth_line, depth_label,
        ))
        assert ruler_line is not None and ruler_label is not None
        assert depth_line is not None and depth_label is not None

        # Both the line and its label are above the drawn template area.
        assert float(ruler_line.get("y1", "nan")) == deployment_depth - 3.0
        assert float(ruler_line.get("y2", "nan")) < area["y"] - area["radius"]
        assert float(ruler_label.get("y", "nan")) < area["y"] - area["radius"]
        # The vertical deployment guide also clears the left template area.
        assert float(depth_line.get("x1", "nan")) == 0.8
        assert float(depth_line.get("x1", "nan")) < left_area["x"] - left_area["radius"]
        assert ruler_group.get("data-distance-inches") == "4"
        expected_ruler = "4″" if distance_unit == "in" else "10 cm"
        expected_depth = (
            f"{deployment_depth}″" if distance_unit == "in"
            else f"{deployment_depth * 2.5:g} cm"
        )
        assert ruler_label.text == expected_ruler
        assert depth_label.text == expected_depth


@pytest.mark.parametrize(
    ("source", "expected_count"),
    [(ITS18, 63), (ITS17_SHARED, 45)],
    ids=["its-18", "its-17"],
)
def test_marker_placement_rulers_measure_markers_without_overlaying_them(
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
                expected_offset = (
                    -3.0
                    if record["id"] == "scenario:neutralization"
                    and ruler["id"] == "antenna-right-from-right"
                    else 2.5
                )
                assert ruler["offset"] == expected_offset, (record["name"], ruler["id"])
                assert any(
                    marker["x"] in (ruler["x1"], ruler["x2"])
                    and marker["y"] == ruler["y1"]
                    for marker in markers
                ), (record["name"], configuration["id"], ruler["id"])

                group = by_id[ruler["id"]]
                line = group.find(f"{SVG_NS}line")
                assert line is not None
                for coordinate, expected in (
                    ("y1", ruler["y1"] + expected_offset),
                    ("y2", ruler["y2"] + expected_offset),
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
