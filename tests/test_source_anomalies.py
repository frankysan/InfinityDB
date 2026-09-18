from __future__ import annotations

import json
from pathlib import Path

import pytest

from infinity_db.source_anomalies import (
    SourceAnomalyBaseline,
    SourceAnomalyBaselineError,
    load_source_anomaly_baseline,
    source_anomaly_baseline_applies,
    validate_normalized_source_anomalies,
    validate_source_anomaly_counts,
)


def baseline(**warning_counts: int) -> SourceAnomalyBaseline:
    return SourceAnomalyBaseline(
        snapshot_downloaded_on="2026-09-18",
        snapshot_archive_sha256="a" * 64,
        source_versions={"7.26246.158": 36, "7.26246.159": 22},
        warning_counts=warning_counts,
    )


def test_tracked_baseline_matches_verified_snapshot() -> None:
    tracked = load_source_anomaly_baseline()

    assert tracked.snapshot_downloaded_on == "2026-09-18"
    assert (
        tracked.snapshot_archive_sha256
        == "041d625bf45ecbd161ddc3a6723e106bd9d5c1a9d9aa088d94b10166fb8c9815"
    )
    assert dict(tracked.source_versions) == {
        "7.26246.158": 36,
        "7.26246.159": 22,
    }
    assert dict(tracked.warning_counts) == {
        "anonymous_reference": 95,
        "catalog_placeholder": 1,
        "fireteam_unit_not_in_army": 1,
        "unit_placeholder": 5,
        "unresolved_fireteam_slug": 14,
    }
    assert tracked.warning_count == 116


def test_baseline_applies_only_to_current_or_later_downloader_snapshots() -> None:
    tracked = baseline(known=1)

    assert source_anomaly_baseline_applies(
        {"_meta": {"snapshotDownloadedOn": "2026-09-18"}}, tracked
    )
    assert source_anomaly_baseline_applies(
        {"_meta": {"snapshotDownloadedOn": "2026-09-19"}}, tracked
    )
    assert not source_anomaly_baseline_applies(
        {"_meta": {"snapshotDownloadedOn": "2026-09-17"}}, tracked
    )
    assert not source_anomaly_baseline_applies({"_meta": {}}, tracked)


def test_warning_decreases_are_allowed() -> None:
    audit = validate_source_anomaly_counts(
        {"anonymous_reference": 80, "unit_placeholder": 0},
        baseline(anonymous_reference=95, unit_placeholder=5),
    )

    assert audit.warning_count == 80
    assert dict(audit.warning_counts) == {"anonymous_reference": 80}
    assert audit.baseline_warning_count == 100


def test_new_warning_category_is_rejected() -> None:
    with pytest.raises(SourceAnomalyBaselineError, match=r"new categories: new_shape=1"):
        validate_source_anomaly_counts(
            {"anonymous_reference": 95, "new_shape": 1},
            baseline(anonymous_reference=95),
        )


def test_warning_count_growth_is_rejected() -> None:
    with pytest.raises(
        SourceAnomalyBaselineError,
        match=r"count growth: anonymous_reference=96 > 95",
    ):
        validate_source_anomaly_counts(
            {"anonymous_reference": 96},
            baseline(anonymous_reference=95),
        )


def test_normalized_document_requires_warning_counts() -> None:
    with pytest.raises(
        SourceAnomalyBaselineError,
        match=r"normalized\._meta\.warningCounts must be an object",
    ):
        validate_normalized_source_anomalies({"_meta": {}}, baseline(known=1))


def test_loader_rejects_invalid_snapshot_hash(tmp_path: Path) -> None:
    path = tmp_path / "baseline.json"
    path.write_text(
        json.dumps(
            {
                "format": "InfinityDB source anomaly baseline",
                "formatVersion": 1,
                "baseline": {
                    "snapshotDownloadedOn": "2026-09-18",
                    "snapshotArchiveSha256": "not-a-hash",
                    "sourceVersions": {"test": 1},
                    "warningCounts": {"known": 1},
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SourceAnomalyBaselineError, match="lowercase SHA-256"):
        load_source_anomaly_baseline(path)
