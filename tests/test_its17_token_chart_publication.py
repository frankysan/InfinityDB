"""ITS 17 V0.2 global token-size chart takes precedence over mission-page omission."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from infinity_db.curated import load_curated_document
from infinity_db.its_season_database import build_its_database, inspect_its_database
from tests.its17_inventory_expectations import EXPECTED_ITS17_SCENARIO_IDS

ROOT = Path(__file__).resolve().parents[1]
SEASON = ROOT / "data/curated/its/n5-its-season-17.json"
SHARED = ROOT / "data/curated/its/shared/its17-scenarios-v1.json"
CURRENT = ROOT / "data/curated/its/n5-its-season-18.json"
EN = "its-season-17-v0.2-en-pdf"
ES = "its-season-17-v0.2-es-pdf"
PINS = [(EN, 13), (ES, 14)]
AFFECTED: dict[str, dict[str, tuple[str, ...]]] = {
    "evacuation": {"civilians": ("25 mm",), "extraction-consoles": ("40 mm",)},
    "hardlock": {"deployment-and-objectives": ("40 mm", "25 mm")},
    "uplink-center": {"deployment-and-objectives": ("40 mm",)},
    "superiority": {"consoles": ("40 mm",)},
    "provisioning": {"deployment-and-tech-coffins": ("40 mm",)},
    "area-of-interest": {"communication-antenna": ("40 mm", "25 mm")},
    "last-launch": {"id-scanners": ("40 mm",), "id-checker": ("40 mm",)},
    "b-pong": {"tracking-beacon-representation": ("25 mm",)},
    "crossing-lines": {"activate-antenna": ("40 mm",)},
    "corporate-appropriation": {"panoplies": ("40 mm",)},
    "critical-intervention": {
        "data-console": ("40 mm",), "inhibitor-antenna": ("40 mm",),
    },
    "akial-interference": {"akial-antenna": ("40 mm",)},
}


def test_chart_pins_every_affected_its17_scenario_and_preserves_other_members() -> None:
    source = json.loads(SEASON.read_text(encoding="utf-8"))
    library = json.loads(SHARED.read_text(encoding="utf-8"))
    assert source["sharedScenarioLibrary"]["sha256"] == hashlib.sha256(
        SHARED.read_bytes()
    ).hexdigest()
    assert [m["scenarioId"] for m in source["scenarioCollection"]["members"]] == list(
        EXPECTED_ITS17_SCENARIO_IDS
    )
    assert [item["id"] for item in library["definitions"]] == list(EXPECTED_ITS17_SCENARIO_IDS)
    members = {
        m["scenarioId"].removeprefix("scenario:"): m
        for m in source["scenarioCollection"]["members"]
    }
    assert AFFECTED.keys() <= members.keys()
    assert len(AFFECTED) == 12
    for slug in AFFECTED:
        pins = members[slug]["sharedDefinition"]["citations"][-2:]
        assert [(row["sourceId"], row["page"]) for row in pins] == PINS
        assert [row["section"] for row in pins] == [
            "Diameter of ITS Tokens", "Diámetro de los Tokens ITS",
        ]
        original = next(d for d in library["definitions"]
                        if d["id"] == f"scenario:{slug}")
        assert original["record"]["citations"][-2:] == pins
        assert original["origin"]["seasonId"] == "its-17"


def test_chart_values_are_explicit_and_disputes_remain_separate() -> None:
    source = load_curated_document(SEASON, shared_scenario_library=SHARED)
    records = {r["id"].removeprefix("scenario:"): r for r in source["records"]
               if r["kind"] == "scenario"}
    assert {f"scenario:{slug}" for slug in records} == set(EXPECTED_ITS17_SCENARIO_IDS)
    for slug, rule_expectations in AFFECTED.items():
        rules = {
            rule["id"]: rule
            for rule in records[slug]["facts"]["mission"]["rules"]
        }
        for rule_id, diameters in rule_expectations.items():
            text = json.dumps(rules[rule_id], ensure_ascii=False)
            assert "EN p. 13 / ES p. 14" in text, (slug, rule_id)
            for diameter in diameters:
                assert diameter in text, (slug, rule_id, diameter)

    crossing = records["crossing-lines"]["facts"]["mission"]
    rule = next(rule for rule in crossing["rules"] if rule["id"] == "activate-antenna")
    paragraphs = " ".join(rule["paragraphs"])
    assert "Transmission Antenna Token" in paragraphs
    assert "Console A Token" in paragraphs
    assert "40 mm" in paragraphs
    assert any(issue["status"] == "needs-verification"
               and "Console A Token" in issue["description"]
               for issue in crossing["sourceIssues"])

    evacuation = records["evacuation"]["facts"]["mission"]
    civilians = next(rule for rule in evacuation["rules"] if rule["id"] == "civilians")
    assert "does not prescribe Civilian Model base sizes" in " ".join(
        civilians["paragraphs"]
    )
    assert "25 mm" in json.dumps(civilians)


def test_its17_token_chart_builds_standalone_without_touching_its18(
    tmp_path: Path,
) -> None:
    output = tmp_path / "its_17.db"
    report = build_its_database(SEASON, output, shared_library=SHARED)
    assert [item["id"] for item in report["scenarios"]] == list(EXPECTED_ITS17_SCENARIO_IDS)
    assert {row["id"] for row in report["skills"]} == {
        "skill:casevac", "skill:civevac",
    }
    assert {row["id"] for row in report["states"]} == {"state:casevac"}
    assert inspect_its_database(
        output, source=SEASON, shared_library=SHARED, require_current_builder=True,
    ) == report

    current = load_curated_document(CURRENT)
    assert current["scenarioCollection"]["id"] == "its-18"
    assert "sharedScenarioLibrary" not in current
    assert all(r["scope"]["seasons"] == ["its-18"] for r in current["records"]
               if r["kind"] == "scenario")
