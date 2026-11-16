"""Source-pinned hotfix mission and shared map-geometry acceptance.

The reviewed September revision remains isolated until selected runtime integration.
"""
import math
from copy import deepcopy
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.its_season_database import (
    build_its_database,
    select_its_scenario,
)
from infinity_db.scenario_definition import (
    ScenarioDefinitionError,
    parse_scenario_definition_record,
)
from infinity_db.scenario_geometry import (
    CircleRegionElement,
    MarkerElement,
    QuarterCircleElement,
    ScenarioGeometryError,
    parse_scenario_geometry,
    resolve_coordinate,
)
from infinity_db.scenario_map_svg import render_scenario_map_svg

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/curated/its/n5-its-season-18-2026.09.11.json"
SIZES = (150, 200, 250, 300, 350, 400)


def _records() -> dict[str, dict]:
    return {
        record["id"]: record
        for record in load_curated_document(SOURCE)["records"]
    }


def _parts(record: dict) -> tuple[dict, dict[str, dict]]:
    mission = record["facts"]["mission"]
    configs = {entry["id"]: entry["geometry"] for entry in record["facts"]["configurations"]}
    assert [size["armyPoints"] for size in mission["gameSizes"]] == list(SIZES)
    assert len(configs) == 3
    for geometry in configs.values():
        parsed = parse_scenario_geometry(geometry)
        for theme in ("light", "dark"):
            svg = render_scenario_map_svg(parsed, theme=theme)
            assert f"<title id=\"map-title\">{record['name']}</title>" in svg
        for unit in ("in", "cm"):
            assert f'data-distance-unit="{unit}"' in render_scenario_map_svg(
                parsed, distance_unit=unit
            )
    return mission, configs


def test_crossing_lines_split_deployment_and_hvt_hotfix() -> None:
    record = _records()["scenario:crossing-lines"]
    mission, configs = _parts(record)
    assert len(mission["objectives"]) == 4
    assert sum(item["maximumPoints"] for item in mission["objectives"]) == 10
    assert [c["page"] for c in record["citations"]] == [63, 64, 65, 66] * 2
    assert "HVT" in " ".join(mission["rules"][-1]["paragraphs"])
    assert "Classified Deck" in " ".join(mission["rules"][-1]["paragraphs"])
    for size in mission["gameSizes"]:
        for deployment in size["deployments"]:
            assert len(deployment["elementIds"]) == 2
    for config in configs.values():
        elements = {item["id"]: item for item in config["elements"]}
        assert len([x for x in elements.values() if x.get("markerType") == "antenna"]) == 2
        assert {x["id"] for x in elements.values() if x["style"] == "exclusion"} == {
            "dead-zone-a", "dead-zone-b",
        }
        for label_id, team in (
            ("deployment-a-rear-label", "A"),
            ("deployment-b-rear-label", "B"),
            ("deployment-a-forward-label", "A"),
            ("deployment-b-forward-label", "B"),
        ):
            label = elements[label_id]
            assert label["x"] == config["table"]["width"] / 2
            assert label["text"] == f"Deployment Zone {team}"
        svg = render_scenario_map_svg(parse_scenario_geometry(config))
        assert svg.count('fill:url(#scenario-exclusion-hatch)') == 1
        assert 'id="scenario-exclusion-hatch"' in svg
        assert {x["id"] for x in elements.values() if x["style"] == "deployment-a"} == {
            "deployment-a-rear", "deployment-a-forward",
        }
        assert {x["id"] for x in elements.values() if x["style"] == "deployment-b"} == {
            "deployment-b-rear", "deployment-b-forward",
        }
        w, h = config["table"]["width"], config["table"]["height"]
        assert elements["antenna-left"]["x"] == w / 4
        assert elements["antenna-right"]["x"] == 3 * w / 4
        assert elements["antenna-left"]["y"] == h / 2
    assert configs["150-points"]["elements"][0]["y1"] == 8
    assert configs["200-250-points"]["elements"][0]["y1"] == 12


def test_double_bind_selected_main_objective_hotfix_and_antenna_areas() -> None:
    record = _records()["scenario:double-bind"]
    mission, configs = _parts(record)
    assert [c["page"] for c in record["citations"]] == list(range(72, 78)) * 2
    selection = mission["objectiveSelection"]
    assert selection["firstChooser"] == "player-who-chose-deployment"
    assert selection["selectionTiming"] == "when-deployment-is-chosen"
    assert selection["distinctSetsRequired"] is True
    assert {entry["id"]: entry["objectiveIds"] for entry in selection["sets"]} == {
        "encryption": ["encryption-one", "encryption-two"],
        "sabotage": ["sabotage"],
        "secure-vector": ["secure-vector-one", "secure-vector-two"],
    }
    objectives = {item["id"]: item for item in mission["objectives"]}
    assert sum(objectives[id]["maximumPoints"] for id in ("encryption-one", "encryption-two")) == 6
    assert objectives["sabotage"]["maximumPoints"] == 6
    assert sum(objectives[id]["maximumPoints"] for id in (
        "secure-vector-one", "secure-vector-two",
    )) == 6
    assert objectives["kill-more"]["maximumPoints"] == 2
    assert objectives["classified"]["maximumPoints"] == 2
    text = " ".join(" ".join(item["paragraphs"]) for item in mission["rules"])
    for phrase in (
        "same moment", "remaining sets", "one Antenna can be destroyed per Player Turn",
        "damage to any other Antenna", "GizmoKit", "WIP-3",
    ):
        assert phrase in text
    for geometry in configs.values():
        parsed = parse_scenario_geometry(geometry)
        regions = [
            element for element in parsed.elements
            if isinstance(element, CircleRegionElement)
        ]
        assert len(regions) == 3
        assert {region.radius for region in regions} == {2.5}
        assert {region.style for region in regions} == {"influence"}
        assert {
            el.marker_type for el in parsed.elements if isinstance(el, MarkerElement)
        } == {"antenna"}
        svg = render_scenario_map_svg(parsed)
        assert svg.count('data-region-shape="circle"') == 3
        assert 'class="exclusion"' in svg
        assert 'class="influence"' in svg
        assert svg.count('class="measurement placement-ruler"') == 2
        rulers = {
            annotation["id"]: annotation for annotation in geometry["annotations"]
            if annotation["kind"] == "ruler"
        }
        assert set(rulers) == {"antenna-middle-from-left", "antenna-right-from-right"}
        assert rulers["antenna-middle-from-left"]["x2"] == geometry["table"]["width"] / 2
        assert rulers["antenna-right-from-right"]["x1"] == geometry["table"]["width"] * 3 / 4
        assert (
            f'data-distance-inches="{geometry["table"]["width"] / 2:g}"' in svg
        )
    assert objectives["sabotage"]["awards"][0]["condition"]["status"] == "destroyed"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("unknown-objective", "unknown"),
        ("overlapping-sets", "reuses an objective"),
        ("wrong-selection-timing", "one of"),
    ],
)
def test_double_bind_objective_selection_rejects_incompatible_data(
    mutation: str, message: str,
) -> None:
    record = deepcopy(_records()["scenario:double-bind"])
    selection = record["facts"]["mission"]["objectiveSelection"]
    if mutation == "unknown-objective":
        selection["sets"][0]["objectiveIds"] = ["missing"]
    elif mutation == "overlapping-sets":
        selection["sets"][1]["objectiveIds"] = ["encryption-one"]
    else:
        selection["selectionTiming"] = "after-deployment"
    with pytest.raises(ScenarioDefinitionError, match=message):
        parse_scenario_definition_record(record)


def test_the_dig_150_point_spacing_analysis_token_ownership_and_corner_geometry() -> None:
    record = _records()["scenario:the-dig"]
    mission, configs = _parts(record)
    assert [c["page"] for c in record["citations"]] == list(range(78, 83)) * 2
    assert {item["id"]: item["maximumPoints"] for item in mission["objectives"]} == {
        "neutralize-hyperthermal": 6,
        "neutralize-each-round": 1,
        "control-console-tokens": 1,
        "classified-objectives": 2,
    }
    rules = {item["id"]: " ".join(item["paragraphs"]) for item in mission["rules"]}
    assert "[[distance:4:inch]]" in rules["place-hyperthermal-techs"]
    assert "[[distance:8:inch]]" in rules["place-hyperthermal-techs"]
    assert "opponent Token" in rules["analyze-hyperthermal-tech"]
    assert "own Player Token" in rules["neutralize-hyperthermal-tech"]
    assert "WIP Roll" in rules["analyze-hyperthermal-tech"]
    for config_id, expected_radius, spacing in (
        ("150-points", 12, 8), ("200-250-points", 20, 12),
        ("300-400-points", 24, 16),
    ):
        parsed = parse_scenario_geometry(configs[config_id])
        zones = [el for el in parsed.elements if isinstance(el, QuarterCircleElement)]
        assert {(el.id, el.corner, el.radius) for el in zones} == {
            ("deployment-a", "top-right", expected_radius),
            ("deployment-b", "bottom-left", expected_radius),
        }
        consoles = sorted(
            (
                el for el in parsed.elements
                if isinstance(el, MarkerElement) and el.marker_type == "console"
            ),
            key=lambda el: resolve_coordinate(el.x, axis="x", table=parsed.table),
        )
        assert len(consoles) == 3
        x0 = resolve_coordinate(consoles[0].x, axis="x", table=parsed.table)
        y0 = resolve_coordinate(consoles[0].y, axis="y", table=parsed.table)
        x1 = resolve_coordinate(consoles[1].x, axis="x", table=parsed.table)
        y1 = resolve_coordinate(consoles[1].y, axis="y", table=parsed.table)
        assert x1 == parsed.table.width / 2
        assert y1 == parsed.table.height / 2
        assert math.isclose(math.hypot(x1 - x0, y1 - y0), spacing, abs_tol=0.00001)
        svg = render_scenario_map_svg(parsed)
        assert svg.count('data-region-shape="quarter-circle"') == 2
        assert svg.count('data-marker-type="console"') == 3
        assert svg.count('class="measurement placement-ruler"') == 3
        rulers = {
            a["id"]: a for a in configs[config_id]["annotations"] if a["kind"] == "ruler"
        }
        assert set(rulers) == {
            "console-to-console", "deployment-corner-radius", "console-center-from-top",
        }
        assert rulers["deployment-corner-radius"]["x2"] == expected_radius
        assert rulers["console-center-from-top"]["y2"] == parsed.table.height / 2
        assert math.isclose(
            math.hypot(
                rulers["console-to-console"]["x2"] - rulers["console-to-console"]["x1"],
                rulers["console-to-console"]["y2"] - rulers["console-to-console"]["y1"],
            ), spacing, abs_tol=0.00001,
        )


def test_battleground_hotfix_sectors_are_distinguishable_from_generic_scoring() -> None:
    record = _records()["scenario:battleground"]
    for entry in record["facts"]["configurations"]:
        geometry = entry["geometry"]
        sectors = {
            element["id"]: element["style"]
            for element in geometry["elements"]
            if element["id"].startswith("sector-") and element["kind"] == "rectangle"
        }
        assert sectors == {
            "sector-near-a": "sector",
            "sector-center": "sector-center",
            "sector-near-b": "sector",
        }
        svg = render_scenario_map_svg(parse_scenario_geometry(geometry), theme="dark")
        assert 'class="sector"' in svg
        assert 'class="sector-center"' in svg
        assert 'svg[data-theme="dark"] .sector' in svg


def test_new_shapes_fail_closed_and_old_revision_remains_unpublished(tmp_path: Path) -> None:
    doc = _records()["scenario:double-bind"]
    original = doc["facts"]["configurations"][0]["geometry"]
    mutated = dict(original)
    mutated["elements"] = [dict(e) for e in original["elements"]]
    circle = next(e for e in mutated["elements"] if e["kind"] == "circle")
    circle["radius"] = 100
    with pytest.raises(ScenarioGeometryError, match="outside table"):
        parse_scenario_geometry(mutated)

    output = tmp_path / "hotfix.db"
    build_its_database(SOURCE, output)
    for scenario_id in ("scenario:crossing-lines", "scenario:double-bind", "scenario:the-dig"):
        assert select_its_scenario(
            output, season_id="its-18", revision="2026.09.11",
            scenario_id=scenario_id,
        )
        assert select_its_scenario(
            output, season_id="its-18", revision="2026.09.01",
            scenario_id=scenario_id,
        ) is None
