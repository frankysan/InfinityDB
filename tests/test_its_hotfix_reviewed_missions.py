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
        depths = {
            item["target"]: item
            for item in config["annotations"]
            if item["kind"] == "dimension"
        }
        assert set(depths) == {
            "deployment-a-rear", "dead-zone-a", "deployment-b-forward",
            "deployment-a-forward", "dead-zone-b", "deployment-b-rear",
        }
        assert all(item["axis"] == "y" and item["offset"] == 2.2
                   for item in depths.values())
        for target, annotation in depths.items():
            height = elements[target]["y2"] - elements[target]["y1"]
            assert f'id="{annotation["id"]}" class="measurement"' in svg
            assert f'data-distance-inches="{height:g}"' in svg
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
        assert svg.count('class="measurement placement-ruler"') == 3
        rulers = {
            annotation["id"]: annotation for annotation in geometry["annotations"]
            if annotation["kind"] == "ruler"
        }
        assert set(rulers) == {
            "antenna-middle-from-left", "antenna-right-from-right",
            "exclusion-from-center",
        }
        assert rulers["antenna-middle-from-left"]["x2"] == geometry["table"]["width"] / 2
        assert rulers["antenna-right-from-right"]["x1"] == geometry["table"]["width"] * 3 / 4
        elements = {item["id"]: item for item in geometry["elements"]}
        exclusion_bottom = elements["exclusion-zone"]["y2"]
        deployment_start = elements["deployment-b"]["y1"]
        for ruler_id in ("antenna-middle-from-left", "antenna-right-from-right"):
            ruler = rulers[ruler_id]
            assert ruler["y1"] == ruler["y2"] == exclusion_bottom + 2.5
            assert exclusion_bottom < ruler["y1"] < deployment_start
        center_ruler = rulers["exclusion-from-center"]
        center = geometry["table"]["height"] / 2
        assert center_ruler["x1"] == center_ruler["x2"] == geometry["table"]["width"] - 3
        assert center_ruler["y1"] == center
        assert center_ruler["y2"] == exclusion_bottom == center + 4
        assert 'id="exclusion-from-center" class="measurement placement-ruler"' in svg
        assert 'data-distance-inches="4"' in svg
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
        vertical_ruler = rulers["console-center-from-top"]
        assert vertical_ruler["y1"] == 0
        assert vertical_ruler["y2"] == y1
        assert vertical_ruler["x1"] == vertical_ruler["x2"] == x1 - 2
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


def test_cutthroat_lieutenant_objectives_killing_and_deployment_are_source_pinned() -> None:
    record = _records()["scenario:cutthroat"]
    mission, configs = _parts(record)
    assert [(item["sourceId"], item["page"]) for item in record["citations"]] == [
        ("its-season-18-en-pdf", 132),
        ("its-season-18-en-pdf", 133),
        ("its-season-18-en-pdf", 134),
        ("its-season-18-es-pdf", 137),
        ("its-season-18-es-pdf", 138),
        ("its-season-18-es-pdf", 139),
    ]
    objectives = {obj["id"]: obj for obj in mission["objectives"]}
    assert {name: obj["maximumPoints"] for name, obj in objectives.items()} == {
        "kill-more-army-points": 3,
        "kill-same-lieutenants": 2,
        "kill-more-lieutenants": 3,
        "kill-more-with-lieutenants": 4,
    }
    for name, metric in (
        ("kill-more-army-points", "enemy-army-points-killed"),
        ("kill-more-lieutenants", "enemy-lieutenants-killed"),
    ):
        condition = objectives[name]["awards"][0]["condition"]
        assert condition == {
            "kind": "metric-comparison", "metric": metric, "comparison": "greater",
        }
    assert "at least one enemy Lieutenant" in (
        objectives["kill-same-lieutenants"]["awards"][0]["condition"]["text"]
    )
    assert "any of your" in (
        objectives["kill-more-with-lieutenants"]["awards"][0]["condition"]["text"]
    )
    for obj in objectives.values():
        assert obj["timing"] == "end-of-game"
        assert obj["awards"][0]["armyPoints"] == list(SIZES)

    rules = {rule["id"]: " ".join(rule["paragraphs"]) for rule in mission["rules"]}
    for fragment in (
        "Loss of Lieutenant", "Open Information", "Hidden Deployment", "Tactical Phase",
        "Isolated", "without spending an Order",
    ):
        assert fragment in rules["reinforced-tactical-link"]
    assert "at any time" in rules["killing"]
    assert "Retreat!" in rules["no-quarter"]
    assert "Classified Deck" in rules["hvt-and-classified-deck"]
    assert mission["endConditions"] == [{
        "id": "round-limit", "checkAt": "end-of-round",
        "finishAt": "end-of-round", "condition": {"kind": "round-limit", "rounds": 3},
    }]
    issues = {issue["id"]: issue for issue in mission["sourceIssues"]}
    assert set(issues) == {
        "lieutenant-kill-bilingual-definition", "key-ops-without-designation",
    }
    assert "Spanish p. 138" in issues["lieutenant-kill-bilingual-definition"]["description"]
    assert "no Key Ops selection" in issues["key-ops-without-designation"]["description"]
    assert all(issue["armyPoints"] == list(SIZES) for issue in issues.values())

    for config_id, depth in (
        ("150-points", 12), ("200-250-points", 16), ("300-400-points", 16),
    ):
        geometry = configs[config_id]
        elements = {element["id"]: element for element in geometry["elements"]}
        assert elements["deployment-a"]["y2"] == depth
        assert elements["deployment-b"]["y1"] == geometry["table"]["height"] - depth
        assert elements["deployment-a-label"]["y"] == depth / 2 + .55
        assert elements["deployment-b-label"]["y"] == (
            geometry["table"]["height"] - depth / 2 + .55
        )
        assert {item["target"] for item in geometry["annotations"]} == {
            "deployment-a", "deployment-b",
        }
        svg = render_scenario_map_svg(parse_scenario_geometry(geometry))
        assert f'data-distance-inches="{depth}"' in svg


def test_superiority_four_quadrants_four_consoles_and_bilingual_special_rules() -> None:
    record = _records()["scenario:superiority"]
    mission, configs = _parts(record)
    assert [(citation["sourceId"], citation["page"]) for citation in record["citations"]] == [
        *((("its-season-18-en-pdf", page)) for page in range(135, 139)),
        *((("its-season-18-es-pdf", page)) for page in range(140, 144)),
    ]
    objectives = {item["id"]: item for item in mission["objectives"]}
    assert {id: item["maximumPoints"] for id, item in objectives.items()} == {
        "dominate-more-quadrants": 6,
        "hack-consoles": 4,
    }
    quadrants = objectives["dominate-more-quadrants"]
    assert quadrants["timing"] == "end-of-round"
    assert quadrants["aggregation"] == "exclusive"
    assert quadrants["maximumPointsPerRound"] == 2
    assert quadrants["awards"] == [{
        "armyPoints": list(SIZES),
        "objectivePoints": 2,
        "condition": {
            "kind": "dominated-region-comparison",
            "elementIds": ["quadrant-1", "quadrant-2", "quadrant-3", "quadrant-4"],
            "comparison": "greater",
        },
    }]
    consoles = objectives["hack-consoles"]
    assert consoles["timing"] == "end-of-game"
    assert consoles["aggregation"] == "cumulative"
    assert consoles["awards"] == [{
        "armyPoints": list(SIZES),
        "objectivePoints": 1,
        "condition": {
            "kind": "element-status-count",
            "elementIds": ["console-q1", "console-q2", "console-q3", "console-q4"],
            "status": "hacked",
        },
    }]
    rules = {rule["id"]: " ".join(rule["paragraphs"]) for rule in mission["rules"]}
    assert "more than half" in rules["quadrants-zo"]
    assert "Proxies and Peripherals" in rules["quadrants-zo"]
    assert "Shasvastii-Embryo" in rules["shasvastii"]
    assert "20 Victory Points" in rules["baggage"]
    assert "40 mm" in rules["consoles"]
    assert "Both players then count" in rules["hack-consoles"]
    assert "Normal WIP Roll" in rules["hack-consoles"]
    assert "Peripheral (Servant)" in rules["specialist-troops"]
    assert "+3 and +1SD" in rules["operational-learning"]
    assert "resets after success" in rules["operational-learning"]
    assert "Classified Deck" in rules["hvt-and-classified-deck"]
    assert [item["id"] for item in mission["endConditions"]] == ["round-limit", "retreat"]
    assert mission["endConditions"][0]["condition"] == {"kind": "round-limit", "rounds": 3}
    assert "Retreat!" in mission["endConditions"][1]["condition"]["text"]
    assert mission["sourceIssues"] == [{
        "id": "shasvastii-bilingual-zo-status",
        "armyPoints": list(SIZES),
        "objectiveId": "dominate-more-quadrants",
        "status": "needs-verification",
        "description": mission["sourceIssues"][0]["description"],
    }]
    assert "English" in mission["sourceIssues"][0]["description"]
    assert "Spanish" in mission["sourceIssues"][0]["description"]

    for config_id, width, height, depth in (
        ("150-points", 24, 32, 8),
        ("200-250-points", 32, 48, 12),
        ("300-400-points", 48, 48, 12),
    ):
        geometry = configs[config_id]
        assert geometry["table"] == {"width": width, "height": height, "unit": "in"}
        elements = {element["id"]: element for element in geometry["elements"]}
        assert elements["deployment-a"]["y2"] == depth
        assert elements["deployment-b"]["y1"] == {"anchor": "bottom", "offset": -depth}
        assert len([element for element in elements.values()
                    if element["kind"] == "marker"]) == 4
        for index in range(1, 5):
            quadrant = elements[f"quadrant-{index}"]
            console = elements[f"console-q{index}"]
            x1 = 0 if index % 2 else width / 2
            x2 = width / 2 if index % 2 else {"anchor": "right"}
            y1 = depth if index < 3 else height / 2
            y2 = height / 2 if index < 3 else height - depth
            assert (quadrant["x1"], quadrant["x2"], quadrant["y1"], quadrant["y2"]) == (
                x1, x2, y1, y2,
            )
            assert console["markerType"] == "console"
            assert (console["x"], console["y"]) == (
                width / 4 if index % 2 else width * 3 / 4,
                (y1 + y2) / 2,
            )
        assert {a["id"] for a in geometry["annotations"]} == {
            "deployment-a-depth", "deployment-b-depth",
        }
        svg = render_scenario_map_svg(parse_scenario_geometry(geometry))
        assert svg.count('data-reference="center"') == 8
        assert f'data-distance-inches="{depth}"' in svg


def test_superiority_rejects_missing_scoring_quadrant() -> None:
    record = deepcopy(_records()["scenario:superiority"])
    geometry = record["facts"]["configurations"][0]["geometry"]
    geometry["elements"] = [
        element for element in geometry["elements"] if element["id"] != "quadrant-4"
    ]
    with pytest.raises(ScenarioDefinitionError, match="missing or incompatible scoring element"):
        parse_scenario_definition_record(record)


def test_uplink_center_objectives_activation_control_and_40mm_tokens() -> None:
    record = _records()["scenario:uplink-center"]
    mission, configs = _parts(record)
    assert [(c["sourceId"], c["page"]) for c in record["citations"]] == [
        *((("its-season-18-en-pdf", page)) for page in range(139, 143)),
        *((("its-season-18-es-pdf", page)) for page in range(144, 148)),
    ]
    objectives = {item["id"]: item for item in mission["objectives"]}
    assert {name: obj["maximumPoints"] for name, obj in objectives.items()} == {
        "activate-communication-antennas": 4,
        "control-communication-antennas": 2,
        "control-tech-coffin": 3,
        "active-lieutenant": 1,
    }
    for name, expected in (
        ("activate-communication-antennas", ("activated", 2, ["antenna-left", "antenna-right"])),
        ("control-communication-antennas", ("controlled", 1, ["antenna-left", "antenna-right"])),
        ("control-tech-coffin", ("controlled", 3, ["tech-coffin"])),
    ):
        status, points_each, ids = expected
        obj = objectives[name]
        assert obj["aggregation"] == "cumulative"
        assert obj["timing"] == "end-of-game"
        assert obj["awards"] == [{
            "armyPoints": list(SIZES), "objectivePoints": points_each,
            "condition": {"kind": "element-status-count", "elementIds": ids, "status": status},
        }]
    assert objectives["active-lieutenant"]["awards"][0]["condition"]["kind"] == "reviewed-prose"
    assert "Isolated or Immobilized" in (
        objectives["active-lieutenant"]["awards"][0]["condition"]["text"]
    )
    rules = {item["id"]: " ".join(item["paragraphs"]) for item in mission["rules"]}
    assert "Neither player may deploy in Silhouette contact" in rules["deployment-and-objectives"]
    assert "40 mm" in rules["deployment-and-objectives"]
    assert "stops counting as Activated for the previous player" in (
        rules["activate-communication-antenna"]
    )
    assert "Normal WIP Roll" in rules["activate-communication-antenna"]
    for control_id in ("control-communication-antenna", "control-tech-coffin"):
        assert "not a Marker" in rules[control_id]
        assert "Silhouette contact" in rules[control_id]
        assert "Null State" in rules[control_id]
    assert "Peripheral (Servant)" in rules["specialist-troops"]
    assert "+3 and +1SD" in rules["operational-learning"]
    assert "resets after a successful Roll" in rules["operational-learning"]
    assert "Isolated State" in rules["active-lieutenant"]
    assert "Classified Deck" in rules["hvt-and-classified-deck"]
    assert [e["id"] for e in mission["endConditions"]] == ["round-limit", "retreat"]
    assert mission["endConditions"][0]["condition"] == {"kind": "round-limit", "rounds": 3}
    assert "Retreat!" in mission["endConditions"][1]["condition"]["text"]
    assert mission["sourceIssues"] == []

    for config_id, width, height, depth in (
        ("150-points", 24, 32, 12),
        ("200-250-points", 32, 48, 16),
        ("300-400-points", 48, 48, 16),
    ):
        geometry = configs[config_id]
        assert geometry["table"] == {"width": width, "height": height, "unit": "in"}
        elements = {element["id"]: element for element in geometry["elements"]}
        assert elements["deployment-a"]["y2"] == depth
        assert elements["deployment-b"]["y1"] == height - depth
        assert {
            element["id"]: (element["markerType"], element["x"], element["y"])
            for element in elements.values() if element["kind"] == "marker"
        } == {
            "antenna-left": ("antenna", width / 4, height / 2),
            "tech-coffin": ("tech-coffin", width / 2, height / 2),
            "antenna-right": ("antenna", width * 3 / 4, height / 2),
        }
        rulers = {
            annotation["id"]: annotation for annotation in geometry["annotations"]
            if annotation["kind"] == "ruler"
        }
        assert rulers == {
            "tech-coffin-from-left": {
                "id": "tech-coffin-from-left", "kind": "ruler",
                "x1": 0, "y1": height - depth + 2.5,
                "x2": width / 2, "y2": height - depth + 2.5, "offset": 0,
            },
            "antenna-right-from-right": {
                "id": "antenna-right-from-right", "kind": "ruler",
                "x1": width * 3 / 4, "y1": height - depth + 2.5,
                "x2": width, "y2": height - depth + 2.5, "offset": 0,
            },
        }
        svg = render_scenario_map_svg(parse_scenario_geometry(geometry))
        assert 'data-marker-type="tech-coffin" data-diameter-mm="40"' in svg
        assert svg.count('data-marker-type="antenna" data-diameter-mm="40"') == 2
        assert 'id="tech-coffin-from-left" class="measurement placement-ruler"' in svg
        assert f'data-distance-inches="{width / 2:g}"' in svg
        assert f'data-distance-inches="{width / 4:g}"' in svg
        assert '.objective[data-marker-type="tech-coffin"]' in svg
        assert 'svg[data-theme="dark"] .objective[data-marker-type="tech-coffin"]' in (
            render_scenario_map_svg(parse_scenario_geometry(geometry), theme="dark")
        )


@pytest.mark.parametrize("mutation", ["missing-tech-coffin", "activated-tech-coffin"])
def test_uplink_center_rejects_missing_or_incompatible_scoring_markers(
    mutation: str,
) -> None:
    record = deepcopy(_records()["scenario:uplink-center"])
    geometry = record["facts"]["configurations"][0]["geometry"]
    if mutation == "missing-tech-coffin":
        geometry["elements"] = [e for e in geometry["elements"] if e["id"] != "tech-coffin"]
    else:
        record["facts"]["mission"]["objectives"][0]["awards"][0]["condition"]["elementIds"] = [
            "tech-coffin",
        ]
    with pytest.raises(
        ScenarioDefinitionError,
        match="missing or incompatible scoring element|requires an Antenna marker",
    ):
        parse_scenario_definition_record(record)



def test_hardlock_beacon_control_console_activation_and_map_geometry() -> None:
    record = _records()["scenario:hardlock"]
    mission, configs = _parts(record)
    assert [(c["sourceId"], c["page"]) for c in record["citations"]] == [
        *((("its-season-18-en-pdf", p)) for p in range(49, 53)),
        *((("its-season-18-es-pdf", p)) for p in range(127, 131)),
    ]
    assert {o["id"]: o["maximumPoints"] for o in mission["objectives"]} == {
        "control-enemy-beacon": 3,
        "protect-own-beacon": 1,
        "activate-more-consoles": 2,
        "activate-each-console": 3,
        "classified-objective": 1,
    }
    objectives = {o["id"]: o for o in mission["objectives"]}
    rounds = objectives["control-enemy-beacon"]
    assert rounds["timing"] == "end-of-round"
    assert rounds["maximumPointsPerRound"] == 1
    assert rounds["awards"][0]["objectivePoints"] == 1
    assert objectives["activate-more-consoles"]["awards"][0]["condition"] == {
        "kind": "element-status-comparison",
        "elementIds": ["console-left", "console-center", "console-right"],
        "status": "activated",
        "comparison": "greater",
    }
    assert objectives["activate-each-console"]["awards"][0]["condition"] == {
        "kind": "element-status-count",
        "elementIds": ["console-left", "console-center", "console-right"],
        "status": "activated",
    }
    rules = {rule["id"]: " ".join(rule["paragraphs"]) for rule in mission["rules"]}
    assert "Normal State" in rules["pick-up-beacon"]
    assert "Activated Console" in rules["pick-up-beacon"]
    assert "Baggage" in rules["common-rules-of-beacons"]
    assert "previous player's Activated status is removed" in rules["activate-console"]
    assert "Peripheral (Servant)" in rules["specialist-troops"]
    assert "Classified Deck is used" in rules["classified-objective"]
    assert [e["id"] for e in mission["endConditions"]] == ["round-limit", "retreat"]
    assert {issue["id"] for issue in mission["sourceIssues"]} == {
        "connected-vs-activated-console", "allied-beacon-carrier-normal-state",
    }
    assert all("p." in issue["description"] for issue in mission["sourceIssues"])

    for config_id, w, h, depth in (
        ("150-points", 24, 32, 8),
        ("200-250-points", 32, 48, 12),
        ("300-400-points", 48, 48, 12),
    ):
        geo = configs[config_id]
        assert geo["table"] == {"width": w, "height": h, "unit": "in"}
        elements = {e["id"]: e for e in geo["elements"]}
        assert elements["deployment-a"]["y2"] == depth
        assert elements["deployment-b"]["y1"] == h - depth
        assert {
            e["id"]: (e["markerType"], e["x"], e["y"])
            for e in elements.values() if e["kind"] == "marker"
        } == {
            "beacon-a": ("beacon", w / 2, depth),
            "beacon-b": ("beacon", w / 2, h - depth),
            "console-left": ("console", w / 4, h / 2),
            "console-center": ("console", w / 2, h / 2),
            "console-right": ("console", 3 * w / 4, h / 2),
        }
        annotations = {a["id"]: a for a in geo["annotations"]}
        assert annotations["deployment-a-depth"]["target"] == "deployment-a"
        assert annotations["deployment-b-depth"]["target"] == "deployment-b"
        assert annotations["console-center-from-left"]["x2"] == w / 2
        assert annotations["console-right-from-right"]["x1"] == 3 * w / 4
        for theme in ("light", "dark"):
            svg = render_scenario_map_svg(parse_scenario_geometry(geo), theme=theme)
            assert svg.count('data-marker-type="beacon"') == 2
            assert svg.count('data-marker-type="console" data-diameter-mm="40"') == 3
            assert svg.count('data-physical-size="unspecified"') == 2
            assert '.objective#beacon-a' in svg
            assert '.objective#beacon-b' in svg
            assert 'data-distance-inches="' + str(w / 2).removesuffix(".0") + '"' in svg


@pytest.mark.parametrize("mutation", ["missing-console", "beacon-as-activated-console"])
def test_hardlock_rejects_missing_or_incorrect_activated_console(mutation: str) -> None:
    record = deepcopy(_records()["scenario:hardlock"])
    if mutation == "missing-console":
        geometry = record["facts"]["configurations"][0]["geometry"]
        geometry["elements"] = [
            e for e in geometry["elements"] if e["id"] != "console-left"
        ]
    else:
        award = record["facts"]["mission"]["objectives"][3]["awards"][0]
        award["condition"]["elementIds"][0] = "beacon-a"
    with pytest.raises(
        ScenarioDefinitionError,
        match="missing or incompatible scoring element|requires an Antenna marker",
    ):
        parse_scenario_definition_record(record)


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
