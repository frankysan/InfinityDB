from __future__ import annotations

import json
from pathlib import Path

from infinity_army_data.merge import make_source, merge_sources
from infinity_army_data.normalize import normalize_master
from infinity_db.curated import load_curated_directory
from infinity_db.database import export_database
from infinity_db.rules_database import export_rules_database
from tools.audit_enrichment_coverage import audit_coverage, main


def _fixture_database(tmp_path: Path) -> Path:
    document = {
        "version": "test",
        "units": [
            {
                "id": 1,
                "name": "Coverage Unit",
                "factions": [101],
                "profileGroups": [
                    {
                        "id": 1,
                        "category": 1,
                        "profiles": [
                            {
                                "id": 1,
                                "name": "Profile",
                                "type": 1,
                                "skills": [{"id": 74}, {"id": 10}, {"id": 999}],
                                "equip": [{"id": 169}],
                                "weapons": [{"id": 226}],
                            }
                        ],
                        "options": [],
                    }
                ],
            }
        ],
        "filters": {
            "category": [{"id": 1, "name": "Infantry"}],
            "type": [{"id": 1, "name": "Trooper"}],
            "skills": [
                {"id": 74, "name": "Super-Jump"},
                {"id": 10, "name": "Camouflage"},
                {"id": 999, "name": "Missing Skill"},
            ],
            "equip": [
                {"id": 169, "name": "TinBot: Firewall"},
                {"id": 188, "name": "TinBot: Neourocinetics"},
                {"id": 193, "name": "TinBot (Albedo)"},
                {"id": 235, "name": "TinBot"},
                {"id": 244, "name": "TinBot: Discover"},
                {"id": 247, "name": "TinBot: ECM Guided"},
                {"id": 248, "name": "Tinbot (Repeater)"},
            ],
            "weapons": [
                {"id": 209, "name": "Armed Turret (Combi R.)"},
                {"id": 215, "name": "Armed Turret (Marksman R.)"},
                {"id": 219, "name": "Armed Turret (AP Rifle)"},
                {"id": 222, "name": "Armed Turret (Rifle)"},
                {"id": 226, "name": "Armed Turret"},
                {"id": 228, "name": "Armed Turret (E/Mitter)"},
            ],
            "extras": [],
        },
    }
    source = make_source("101-coverage.json", json.dumps(document).encode())
    assert source is not None
    normalized = normalize_master(merge_sources([source]))
    normalized["armyMetadata"] = {
        "sourceFile": "metadata.json",
        "sourceSha256": "test-metadata",
        "data": {"factions": []},
    }
    path = tmp_path / "infinity.db"
    export_database(normalized, path)
    return path


def _fixture_rules(tmp_path: Path) -> Path:
    path = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(Path("data/curated")), path)
    return path


def test_enrichment_coverage_reports_review_mapping_and_source_freshness(tmp_path: Path) -> None:
    report = audit_coverage(
        _fixture_database(tmp_path),
        _fixture_rules(tmp_path),
        include_complete=True,
    )

    assert report["summary"]["exposedCount"] == 5
    assert report["summary"]["completeCount"] == 2
    assert report["summary"]["gapCount"] == 3
    assert report["summary"]["gapCounts"] == {
        "missing_rule_definition": 1,
        "stale_citation_source": 1,
        "unreviewed_rule": 1,
    }

    skills = {item["name"]: item for item in report["domains"]["skills"]["items"]}
    assert skills["Super-Jump"]["gapCodes"] == []
    assert skills["Camouflage"]["gapCodes"] == ["unreviewed_rule"]
    assert skills["Missing Skill"]["gapCodes"] == ["missing_rule_definition"]

    tinbot = report["domains"]["equipment"]["items"][0]
    assert tinbot["familyRuleIds"] == ["equipment:tinbot"]
    assert tinbot["exactSourceRuleIds"] == ["equipment:tinbot-firewall"]
    assert tinbot["mapping"]["exactSourceRecordIds"]["169"] == [
        "equipment:tinbot-firewall"
    ]
    assert tinbot["gapCodes"] == []

    turret = report["domains"]["weapons"]["items"][0]
    assert turret["familyRuleIds"] == ["weapon:armed-turret"]
    assert turret["gapCodes"] == ["stale_citation_source"]
    assert report["summary"]["unresolvedRelatedItemLinkCount"] == 0
    assert report["summary"]["supportingRelationTargetCount"] >= 1


def test_enrichment_coverage_default_details_only_list_gaps(tmp_path: Path) -> None:
    report = audit_coverage(_fixture_database(tmp_path), _fixture_rules(tmp_path))

    assert [item["name"] for item in report["domains"]["skills"]["items"]] == [
        "Camouflage",
        "Missing Skill",
    ]
    assert report["domains"]["equipment"]["items"] == []
    assert [item["name"] for item in report["domains"]["weapons"]["items"]] == [
        "Armed Turret"
    ]


def test_enrichment_coverage_cli_writes_report(tmp_path: Path, capsys) -> None:
    database = _fixture_database(tmp_path)
    rules = _fixture_rules(tmp_path)
    output = tmp_path / "coverage.json"

    assert main([str(database), "--rules", str(rules), "--output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["formatVersion"] == 1
    assert "Enrichment coverage audit written" in capsys.readouterr().out
