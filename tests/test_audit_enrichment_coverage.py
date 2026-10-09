from __future__ import annotations

import json
from pathlib import Path

import pytest

from infinity_army_data.merge import make_source, merge_sources
from infinity_army_data.normalize import normalize_master
from infinity_db.curated import load_curated_directory
from infinity_db.database import export_database
from infinity_db.rules_database import export_rules_database
from tools.audit_enrichment_coverage import (
    DEFAULT_CLASSIFICATION_PATH,
    EnrichmentCoverageAuditError,
    _record_gap_codes,
    audit_coverage,
    main,
)


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
                {"id": 201, "name": "BS Attack"},
                {"id": 278, "name": "BS=12"},
                {"id": 279, "name": "BS=11"},
                {"id": 3011, "name": "Discover"},
                {"id": 3012, "name": "Stealth"},
                {"id": 3013, "name": "Forward Observer"},
                {"id": 3014, "name": "Reset"},
                {"id": 3015, "name": "Cautious Movement"},
                {"id": 3016, "name": "Surprise Attack"},
                {"id": 3017, "name": "Dodge"},
                {"id": 3018, "name": "Mimetism"},
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


def _fixture_classification_policy(tmp_path: Path) -> Path:
    document = json.loads(DEFAULT_CLASSIFICATION_PATH.read_text(encoding="utf-8"))
    document["catalogGapCodes"] = {}
    document["overrides"] = []
    path = tmp_path / "fixture-classifications.json"
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("source_version", "expected_gaps"),
    [
        ("0.1", []),  # FAQ version, not an N5 rulebook version.
        ("v0.1", []),
        ("5.3", []),
        ("N5.3 / oldid 3987", []),
        ("5.2", ["stale_citation_source"]),
        ("N5.2 / oldid 3677", ["stale_citation_source"]),
        ("N4.2", ["stale_citation_source"]),
    ],
)
def test_enrichment_coverage_distinguishes_source_revisions_from_rules_editions(
    source_version: str, expected_gaps: list[str]
) -> None:
    record = {
        "reviewContributions": [{"review": {"status": "reviewed"}}],
        "citations": [{"collection_version": "5.3", "source_version": source_version}],
    }
    assert _record_gap_codes(record) == expected_gaps


def test_enrichment_coverage_reports_review_mapping_and_source_freshness(tmp_path: Path) -> None:
    report = audit_coverage(
        _fixture_database(tmp_path),
        _fixture_rules(tmp_path),
        include_complete=True,
        classification_path=_fixture_classification_policy(tmp_path),
    )

    assert report["summary"]["exposedCount"] == 154
    assert report["summary"]["completeCount"] == 153
    assert report["summary"]["gapCount"] == 1
    assert report["summary"]["gapCounts"] == {
        "missing_rule_definition": 1,
        "unresolved_related_item_link": 8,
    }
    assert report["summary"]["classifiedGapCount"] == 9
    assert report["summary"]["classificationCounts"] == {"release-blocker": 9}
    assert report["summary"]["releaseBlockerCount"] == 9

    skills = {item["name"]: item for item in report["domains"]["skills"]["items"]}
    assert skills["Super-Jump"]["gapCodes"] == []
    assert skills["Camouflage"]["gapCodes"] == []
    assert skills["CC Attack"]["gapCodes"] == []
    assert skills["Missing Skill"]["gapCodes"] == ["missing_rule_definition"]
    assert skills["Request Speedball"]["gapCodes"] == []
    assert skills["Missing Skill"]["gapClassifications"][0]["classification"] == (
        "release-blocker"
    )

    tinbot = report["domains"]["equipment"]["items"][0]
    assert tinbot["familyRuleIds"] == ["equipment:tinbot"]
    assert tinbot["exactSourceRuleIds"] == ["equipment:tinbot-firewall"]
    assert tinbot["mapping"]["exactSourceRecordIds"]["169"] == [
        "equipment:tinbot-firewall"
    ]
    assert tinbot["gapCodes"] == []

    turret = next(
        item
        for item in report["domains"]["weapons"]["items"]
        if item["name"] == "Armed Turret"
    )
    assert turret["familyRuleIds"] == ["weapon:armed-turret"]
    assert turret["gapCodes"] == []
    states = {item["name"]: item for item in report["domains"]["states"]["items"]}
    assert len(states) == 24
    assert states["Camouflaged State"]["gapCodes"] == []
    assert states["Unconscious State"]["gapCodes"] == []
    assert states["Targeted State"]["gapCodes"] == []

    assert report["summary"]["unresolvedRelatedItemLinkCount"] == 8
    assert report["summary"]["supportingRelationTargetCount"] == 10
    assert {
        item["targetRecordId"] for item in report["relationCoverage"]["unresolved"]
    } == {
        "equipment:gizmokit",
        "equipment:hacking-device",
        "equipment:medikit",
        "equipment:multispectral-visor",
        "equipment:360o-visor",
    }
    assert {
        item["recordId"] for item in report["relationCoverage"]["supporting"]
    } == {
        "rule:peripheral-type:ancillary",
        "rule:peripheral-type:control",
        "rule:peripheral-type:cyberplug",
        "rule:peripheral-type:servant",
        "rule:peripheral-type:synchronized",
        "rule:command-token-strategic-use",
        "rule:loss-of-lieutenant",
        "rule:special-lieutenant-order",
        "rule:tactical-order",
        "training:regular",
    }


def test_enrichment_coverage_default_details_only_list_gaps(tmp_path: Path) -> None:
    report = audit_coverage(
        _fixture_database(tmp_path),
        _fixture_rules(tmp_path),
        classification_path=_fixture_classification_policy(tmp_path),
    )

    assert [item["name"] for item in report["domains"]["skills"]["items"]] == [
        "Missing Skill"
    ]
    assert report["domains"]["equipment"]["items"] == []
    assert report["domains"]["states"]["items"] == []
    assert report["domains"]["weapons"]["items"] == []


def test_enrichment_coverage_cli_writes_report(tmp_path: Path, capsys) -> None:
    database = _fixture_database(tmp_path)
    rules = _fixture_rules(tmp_path)
    output = tmp_path / "coverage.json"

    classifications = _fixture_classification_policy(tmp_path)
    assert main(
        [
            str(database),
            "--rules",
            str(rules),
            "--classifications",
            str(classifications),
            "--output",
            str(output),
        ]
    ) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["formatVersion"] == 3
    assert payload["classificationPolicy"]["sha256"]
    assert "Enrichment coverage audit written" in capsys.readouterr().out


def _classification_policy_with_override(
    tmp_path: Path, override: dict[str, object]
) -> Path:
    document = json.loads(DEFAULT_CLASSIFICATION_PATH.read_text(encoding="utf-8"))
    document["catalogGapCodes"] = {}
    document["overrides"] = [override]
    path = tmp_path / "classifications.json"
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


def _classification_policy_with_catalog_gap(
    tmp_path: Path,
    *,
    catalog: str,
    gap_code: str,
    classification: str,
    reason: str,
) -> Path:
    document = json.loads(DEFAULT_CLASSIFICATION_PATH.read_text(encoding="utf-8"))
    document["catalogGapCodes"] = {
        catalog: {
            gap_code: {
                "classification": classification,
                "reason": reason,
            }
        }
    }
    document["overrides"] = []
    path = tmp_path / "catalog-classifications.json"
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


def test_enrichment_coverage_allows_catalog_gap_classification(tmp_path: Path) -> None:
    classifications = _classification_policy_with_catalog_gap(
        tmp_path,
        catalog="skills",
        gap_code="missing_rule_definition",
        classification="later-product-work",
        reason="Synthetic catalog-scope decision.",
    )

    report = audit_coverage(
        _fixture_database(tmp_path),
        _fixture_rules(tmp_path),
        classification_path=classifications,
    )

    missing = next(
        item
        for item in report["domains"]["skills"]["items"]
        if item["name"] == "Missing Skill"
    )
    assert missing["gapClassifications"] == [
        {
            "code": "missing_rule_definition",
            "classification": "later-product-work",
            "reason": "Synthetic catalog-scope decision.",
            "source": "catalog-gap-code",
        }
    ]
    assert report["summary"]["classificationCounts"] == {
        "later-product-work": 1,
        "release-blocker": 8,
    }
    assert report["summary"]["releaseBlockerCount"] == 8


def test_enrichment_coverage_allows_explicit_gap_override(tmp_path: Path) -> None:
    classifications = _classification_policy_with_override(
        tmp_path,
        {
            "scope": "catalog",
            "catalog": "skills",
            "itemId": 999,
            "gapCode": "missing_rule_definition",
            "classification": "later-product-work",
            "reason": "Synthetic fixture decision.",
        },
    )

    report = audit_coverage(
        _fixture_database(tmp_path),
        _fixture_rules(tmp_path),
        classification_path=classifications,
    )

    missing = next(
        item
        for item in report["domains"]["skills"]["items"]
        if item["name"] == "Missing Skill"
    )
    assert missing["gapClassifications"] == [
        {
            "code": "missing_rule_definition",
            "classification": "later-product-work",
            "reason": "Synthetic fixture decision.",
            "source": "override",
        }
    ]
    assert report["summary"]["classificationCounts"] == {
        "later-product-work": 1,
        "release-blocker": 8,
    }
    assert report["summary"]["releaseBlockerCount"] == 8


def test_enrichment_coverage_rejects_stale_classification_override(tmp_path: Path) -> None:
    classifications = _classification_policy_with_override(
        tmp_path,
        {
            "scope": "catalog",
            "catalog": "skills",
            "itemId": 123456,
            "gapCode": "missing_rule_definition",
            "classification": "intentional-omission",
            "reason": "Must not silently outlive the gap it classified.",
        },
    )

    with pytest.raises(
        EnrichmentCoverageAuditError,
        match="overrides that do not match current gaps",
    ):
        audit_coverage(
            _fixture_database(tmp_path),
            _fixture_rules(tmp_path),
            classification_path=classifications,
        )
