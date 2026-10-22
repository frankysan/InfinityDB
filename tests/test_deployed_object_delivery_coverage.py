"""Audit the gap between reviewed object identities and delivery origins."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

import tools.audit_deployed_object_delivery_coverage as audit


def test_same_source_alias_is_only_a_review_lead(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "army.db"
    with sqlite3.connect(database) as db:
        db.executescript(
            """
            CREATE TABLE application_domain_slugs(
                domain TEXT, application_id INTEGER, slug TEXT
            );
            CREATE TABLE application_catalog_sources(
                catalog TEXT, application_item_id INTEGER, source_item_id INTEGER
            );
            INSERT INTO application_domain_slugs VALUES
                ('weapons', 5, 'example-device'),
                ('weapons', 6, 'similarly-named-device'),
                ('equipment', 7, 'unreviewed-equipment');
            INSERT INTO application_catalog_sources VALUES
                ('weapons', 5, 42), ('weapons', 6, 99), ('equipment', 7, 13);
            """
        )
    monkeypatch.setattr(
        audit, "audit_inventory",
        lambda *_args: {"armyDatabaseSha256": "a" * 64, "curatedSourceSha256": "b" * 64},
    )
    monkeypatch.setattr(
        audit, "project_deployed_references",
        lambda _report: {
            "objects": [
                {"id": "x", "name": "Example", "sourceProfile": {
                    "catalog": "weapon", "sourceId": 42, "mode": None,
                }, "originRuleId": None, "deliverySources": []},
                {"id": "y", "name": "Reviewed other", "sourceProfile": None,
                 "originRuleId": "weapon:armed-turret", "deliverySources": [
                     {"recordId": "weapon:armed-turret", "method": "place"},
                 ]},
            ],
            "unresolvedDeliveries": [],
        },
    )
    result = audit.audit_delivery_coverage(database, database, database, database)
    assert result["withReviewedDelivery"] == 1
    assert [row["objectId"] for row in result["withoutReviewedDelivery"]] == ["x"]
    assert result["objects"][0]["sameSourceCatalogCandidates"] == [
        {"recordId": "weapon:example-device", "applicationId": 5},
    ]
    assert result["objects"][0]["reviewedDeliverySources"] == []
    assert result["objects"][1]["sameSourceCatalogCandidates"] == []


def test_pinned_delivery_review_gap_is_explicit() -> None:
    root = Path(__file__).resolve().parents[1]
    paths = (
        root / "data/generated/infinity.db",
        root / "data/curated/rules/n5-core-v5.3.json",
        root / "config/validation/deployed-object-delivery-reviews.json",
        root / "config/validation/deployed-object-candidate-reviews.json",
    )
    if not all(path.is_file() for path in paths):
        pytest.skip("Pinned N5.3 source inputs unavailable")
    report = audit.audit_delivery_coverage(*paths)
    assert report["scope"] == "delivery-review-queue-not-inferred-object-ownership"
    assert report["reviewedObjectCount"] == 17
    assert report["withReviewedDelivery"] + len(report["withoutReviewedDelivery"]) == 17
    assert len(report["withoutReviewedDelivery"]) == 9
    assert {row["name"] for row in report["objects"] if row["reviewedDeliverySources"]} == {
        "Deployable Repeater", "Disco Ball", "Drop Bears",
        "WildParrot", "FastPanda", "Armed Turret", "Crazykoala", "Madtraps",
    }
    assert report["unresolvedDeliveryOrigins"] == [{
        "originRecordId": "weapon:mine-dispenser",
        "delivery": "successful BS Attack shot",
        "reason": "source-object-not-resolved",
    }]
    assert all(
        row["sourceProfile"] is not None or row["originRuleId"] is not None
        for row in report["withoutReviewedDelivery"]
    )
    assert all(
        candidate["recordId"] not in {
            edge["recordId"] for edge in row["reviewedDeliverySources"]
        }
        for row in report["withoutReviewedDelivery"]
        for candidate in row["sameSourceCatalogCandidates"]
    )


def test_cli_reports_queue_without_assigning_object_ownership(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    root = Path(__file__).resolve().parents[1]
    if not (root / "data/generated/infinity.db").is_file():
        pytest.skip("Pinned Army database unavailable")
    monkeypatch.setattr(sys, "argv", ["audit_deployed_object_delivery_coverage"])
    assert audit.main() == 0
    output = capsys.readouterr().out
    assert "Reviewed objects: 17" in output
    assert "without:" in output
    assert "Unresolved reviewed delivery origins: 1" in output
