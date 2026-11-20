"""Regression coverage for source-sized ITS tokens and marker-adjacent placement rulers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal
from xml.etree import ElementTree

import pytest

from infinity_db.scenario_geometry import (
    marker_diameter_mm,
    marker_radius_inches,
    parse_scenario_geometry,
)
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
    "antenna-left-from-left",
    "antenna-right-from-right",
    "console-right-from-right",
    "right-console-from-right",
    "tech-box-left-from-left",
    "coffin-right-from-edge",
    "scanner-right-from-edge",
    "prototype-left-from-edge",
    "console-left-from-left",
    "civilian-right-from-right",
})


@pytest.mark.parametrize("source", [ITS18, ITS17_SHARED], ids=["its-18", "its-17"])
def test_placement_helpers_skip_obvious_centers_and_mirrored_duplicates(
    source: Path,
) -> None:
    document = json.loads(source.read_text(encoding="utf-8"))
    records = (
        document["records"] if source == ITS18
        else [entry["record"] for entry in document["definitions"]]
    )
    for record in records:
        if record["kind"] != "scenario":
            continue
        for configuration in record["facts"]["configurations"]:
            geometry = configuration["geometry"]
            width, height = geometry["table"]["width"], geometry["table"]["height"]
            markers = [e for e in geometry["elements"] if e["kind"] == "marker"]
            rulers = {
                a["id"]: a for a in geometry["annotations"] if a["kind"] == "ruler"
            }
            for ruler in rulers.values():
                endpoints = ((ruler["x1"], ruler["y1"]), (ruler["x2"], ruler["y2"]))
                # A line from any table edge to an exactly central marker
                # only restates its visually obvious position.
                for marker in markers:
                    if (marker["x"], marker["y"]) != (width / 2, height / 2):
                        continue
                    if (width / 2, height / 2) not in endpoints:
                        continue
                    other = (
                        endpoints[0] if endpoints[1] == (width / 2, height / 2)
                        else endpoints[1]
                    )
                    assert not (
                        other[0] in (0, width) or other[1] in (0, height)
                    ), (record["name"], configuration["id"], ruler["id"])

            if record["id"] == "scenario:corporate-appropriation":
                by_id = {m["id"]: m for m in markers}
                assert by_id["prototype-left"]["x"] + by_id["prototype-right"]["x"] == width
                assert by_id["prototype-left"]["y"] == by_id["prototype-right"]["y"]
                assert "prototype-left-from-edge" in rulers
                assert "prototype-right-from-edge" not in rulers
            if record["id"] == "scenario:b-pong":
                by_id = {e["id"]: e for e in geometry["elements"]}
                assert (
                    by_id["exclusion-zone"]["y1"] + by_id["exclusion-zone"]["y2"]
                ) == height
                assert "exclusion-a-radius" in rulers
                assert "exclusion-b-radius" not in rulers


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


@pytest.mark.parametrize("source", [ITS18, ITS17_SHARED], ids=["its-18", "its-17"])
@pytest.mark.parametrize("distance_unit", ["in", "cm"])
def test_critical_intervention_antenna_is_tangent_to_server_room_lower_left(
    source: Path, distance_unit: Literal["in", "cm"],
) -> None:
    document = json.loads(source.read_text(encoding="utf-8"))
    records = (
        document["records"] if source == ITS18
        else [entry["record"] for entry in document["definitions"]]
    )
    record = next(r for r in records if r["id"] == "scenario:critical-intervention")
    radius = marker_radius_inches("antenna")
    assert marker_diameter_mm("antenna") == 40
    assert radius is not None
    assert len(record["facts"]["configurations"]) == 3

    for configuration in record["facts"]["configurations"]:
        geometry = configuration["geometry"]
        elements = {element["id"]: element for element in geometry["elements"]}
        room = elements["server-room"]
        antenna = elements["inhibitor-antenna"]
        assert antenna["markerType"] == "antenna"

        # The Antenna center is inset by one physical token radius from
        # the room's left edge and offset one radius below its bottom edge.
        assert antenna["x"] - radius == pytest.approx(room["x1"], abs=1e-6)
        assert antenna["y"] - radius == pytest.approx(room["y2"], abs=1e-6)
        assert antenna["x"] + radius < room["x2"]
        assert antenna["y"] + radius < geometry["table"]["height"]

        svg = ElementTree.fromstring(render_scenario_map_svg(
            parse_scenario_geometry(geometry), distance_unit=distance_unit,
        ))
        circle = next(node for node in svg.iter() if node.get("id") == "inhibitor-antenna")
        assert circle.get("data-diameter-mm") == "40"
        cx = float(circle.get("cx", "nan"))
        cy = float(circle.get("cy", "nan"))
        r = float(circle.get("r", "nan"))
        assert cx - r == pytest.approx(room["x1"], abs=1e-6)
        assert cy - r == pytest.approx(room["y2"], abs=1e-6)


@pytest.mark.parametrize("source", [ITS18, ITS17_SHARED], ids=["its-18", "its-17"])
@pytest.mark.parametrize("distance_unit", ["in", "cm"])
def test_crossing_lines_antenna_edge_ruler_is_mirrored_and_clear(
    source: Path, distance_unit: Literal["in", "cm"],
) -> None:
    document = json.loads(source.read_text(encoding="utf-8"))
    records = (
        document["records"] if source == ITS18
        else [entry["record"] for entry in document["definitions"]]
    )
    record = next(r for r in records if r["id"] == "scenario:crossing-lines")
    for configuration, expected_inches in zip(
        record["facts"]["configurations"], (6, 8, 12), strict=True,
    ):
        geometry = configuration["geometry"]
        width = geometry["table"]["width"]
        center_y = geometry["table"]["height"] / 2
        markers = {e["id"]: e for e in geometry["elements"] if e["kind"] == "marker"}
        assert markers["antenna-left"]["x"] == expected_inches
        assert markers["antenna-right"]["x"] == width - expected_inches
        assert markers["antenna-left"]["y"] == markers["antenna-right"]["y"] == center_y

        rulers = {a["id"]: a for a in geometry["annotations"] if a["kind"] == "ruler"}
        assert set(rulers) == {"antenna-left-from-left"}
        assert rulers["antenna-left-from-left"] == {
            "id": "antenna-left-from-left",
            "kind": "ruler",
            "x1": 0,
            "y1": center_y,
            "x2": expected_inches,
            "y2": center_y,
            "offset": 2.5,
        }

        root = ElementTree.fromstring(render_scenario_map_svg(
            parse_scenario_geometry(geometry), distance_unit=distance_unit,
        ))
        ruler = next(e for e in root.iter() if e.get("id") == "antenna-left-from-left")
        line = ruler.find(f"{SVG_NS}line")
        caption = ruler.find(f"{SVG_NS}text")
        assert line is not None and caption is not None
        assert ruler.get("data-distance-inches") == str(expected_inches)
        assert (
            float(line.get("x1", "nan")), float(line.get("x2", "nan")),
            float(line.get("y1", "nan")), float(line.get("y2", "nan")),
        ) == (0, expected_inches, center_y + 2.5, center_y + 2.5)
        expected_caption = (
            f"{expected_inches}″" if distance_unit == "in"
            else f"{expected_inches * 2.5:g} cm"
        )
        assert caption.text == expected_caption
        # Both markers remain above the ruler; the caption is below its line.
        assert float(caption.get("y", "nan")) > center_y + 2.5
        # Avoid adding a mirrored right ruler across the dense depth labels.
        assert not any(e.get("id") == "antenna-right-from-right" for e in root.iter())


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


@pytest.mark.parametrize("distance_unit", ["in", "cm"])
def test_double_bind_exclusion_label_stays_visible(
    distance_unit: Literal["in", "cm"],
) -> None:
    document = json.loads(ITS18.read_text(encoding="utf-8"))
    record = next(r for r in document["records"] if r["id"] == "scenario:double-bind")
    for configuration in record["facts"]["configurations"]:
        geometry = configuration["geometry"]
        width = geometry["table"]["width"]
        text_scale = 1 + max(0, min(24, width - 24)) / 48
        svg = ElementTree.fromstring(render_scenario_map_svg(
            parse_scenario_geometry(geometry), distance_unit=distance_unit,
        ))
        guide = next(node for node in svg.iter() if node.get("id") == "exclusion-from-center")
        caption = guide.find(f"{SVG_NS}text")
        assert caption is not None and caption.text is not None
        x = float(caption.get("x", "nan"))
        y = float(caption.get("y", "nan"))
        # The longer '10 cm' label must not be clipped at the right table edge.
        half_width = len(caption.text) * 0.6 * 1.1 * text_scale / 2
        assert x - half_width > 0
        assert x + half_width < width - 0.1

        # Nor should the exclusion guide label return to an Antenna template.
        bbox = (x - half_width, y - 1.1 * text_scale,
                x + half_width, y + 0.2 * text_scale)
        for circle in (e for e in geometry["elements"] if e["kind"] == "circle"):
            nearest_x = max(bbox[0], min(circle["x"], bbox[2]))
            nearest_y = max(bbox[1], min(circle["y"], bbox[3]))
            separation = ((nearest_x - circle["x"]) ** 2
                          + (nearest_y - circle["y"]) ** 2) ** 0.5
            assert separation > circle["radius"], (configuration["id"], circle["id"])


@pytest.mark.parametrize("source", [ITS18, ITS17_SHARED], ids=["its-18", "its-17"])
def test_exclusion_and_forward_zone_labels_have_separate_tracks(source: Path) -> None:
    document = json.loads(source.read_text(encoding="utf-8"))
    records = (
        document["records"] if source == ITS18
        else [entry["record"] for entry in document["definitions"]]
    )
    for record in records:
        if record["id"] not in {"scenario:b-pong", "scenario:crossing-lines"}:
            continue
        for configuration in record["facts"]["configurations"]:
            geometry = configuration["geometry"]
            annotations = {a["id"]: a for a in geometry["annotations"]}
            width = geometry["table"]["width"]
            if record["id"] == "scenario:b-pong":
                center = geometry["table"]["height"] / 2
                assert "beacon-from-left" not in annotations
                assert "exclusion-b-radius" not in annotations
                ruler = annotations["right-console-from-right"]
                assert ruler["y1"] == center
                assert ruler["offset"] == 4.5
                assert ruler["y1"] + ruler["offset"] > center + 4
            elif width == 48:
                near = annotations["deployment-b-forward-depth"]
                far = annotations["deployment-a-forward-depth"]
                assert (near["offset"], far["offset"]) == (4.7, 2.2)
                # The rendered 10 cm captions are on distinct vertical lanes.
                assert near["offset"] - far["offset"] > 1.1 * 1.5


@pytest.mark.parametrize(
    ("source", "expected_count"),
    [(ITS18, 36), (ITS17_SHARED, 24)],
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
                    -3.0 if record["id"] == "scenario:neutralization"
                    and ruler["id"] == "antenna-right-from-right"
                    else 4.5 if record["id"] in {"scenario:double-bind", "scenario:b-pong"}
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

                # Ruler text sits beyond its line, away from the measured markers
                # and (for Double Bind) outside the Circular Template footprints.
                caption = group.find(f"{SVG_NS}text")
                assert caption is not None
                baseline = float(caption.get("y", "nan"))
                rendered_y = ruler["y1"] + expected_offset
                text_scale = 1 + max(0, min(24, geometry["table"]["width"] - 24)) / 48
                if expected_offset > 0:
                    assert baseline > rendered_y
                    assert baseline - 1.1 * text_scale > ruler["y1"] + 0.8
                else:
                    assert baseline < rendered_y
                    assert baseline < ruler["y1"] - 2.5
                examined += 1

            if record["name"] in {"Double Bind", "B-Pong"}:
                verticals = {
                    a["id"]: a for a in geometry["annotations"]
                    if a["kind"] == "ruler" and a["x1"] == a["x2"]
                }
                if record["name"] == "Double Bind":
                    guide = verticals["exclusion-from-center"]
                    assert guide["x1"] == {24: 21, 32: 28, 48: 43}[geometry["table"]["width"]]
                    assert guide["x2"] == guide["x1"]
                else:
                    assert set(verticals) == {"exclusion-a-radius"}
                    assert verticals["exclusion-a-radius"]["x1"] == (
                        geometry["table"]["width"] / 2 + 2
                    )

    assert examined == expected_count
