"""Tracked regression baseline for tolerated Infinity Army source anomalies."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import MappingProxyType
from typing import Any

from infinity_army_data.project_resources import maintained_config_path

FORMAT_NAME = "InfinityDB source anomaly baseline"
FORMAT_VERSION = 1
DEFAULT_SOURCE_ANOMALY_BASELINE = maintained_config_path(
    "validation", "source-anomalies.json"
)


class SourceAnomalyBaselineError(ValueError):
    """Raised when the baseline is invalid or a source-anomaly regression is found."""


@dataclass(frozen=True)
class SourceAnomalyBaseline:
    """Validated warning counts observed for one known Army snapshot."""

    snapshot_downloaded_on: str
    snapshot_archive_sha256: str
    source_versions: Mapping[str, int]
    warning_counts: Mapping[str, int]

    @property
    def warning_count(self) -> int:
        return sum(self.warning_counts.values())


@dataclass(frozen=True)
class SourceAnomalyAudit:
    """Result of comparing current normalization warnings with the tracked baseline."""

    warning_count: int
    warning_counts: Mapping[str, int]
    baseline_warning_count: int
    baseline_snapshot_downloaded_on: str


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SourceAnomalyBaselineError(f"{context} must be an object")
    return value


def _only_keys(value: Mapping[str, Any], allowed: set[str], context: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        names = ", ".join(sorted(unknown))
        raise SourceAnomalyBaselineError(f"{context} has unknown field(s): {names}")


def _count_map(value: Any, context: str, *, positive: bool) -> Mapping[str, int]:
    source = _object(value, context)
    result: dict[str, int] = {}
    for key, count in source.items():
        if not isinstance(key, str) or not key:
            raise SourceAnomalyBaselineError(f"{context} keys must be non-empty strings")
        minimum = 1 if positive else 0
        if type(count) is not int or count < minimum:
            qualifier = "positive" if positive else "non-negative"
            raise SourceAnomalyBaselineError(
                f"{context}.{key} must be a {qualifier} integer"
            )
        result[key] = count
    return MappingProxyType(dict(sorted(result.items())))


def load_source_anomaly_baseline(
    path: Path = DEFAULT_SOURCE_ANOMALY_BASELINE,
) -> SourceAnomalyBaseline:
    """Load and validate the tracked source-anomaly baseline."""

    try:
        root = _object(json.loads(path.read_text(encoding="utf-8")), str(path))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceAnomalyBaselineError(f"Could not read {path}: {exc}") from exc

    _only_keys(root, {"format", "formatVersion", "baseline"}, str(path))
    if root.get("format") != FORMAT_NAME:
        raise SourceAnomalyBaselineError(
            f"{path} format must be {FORMAT_NAME!r}"
        )
    if root.get("formatVersion") != FORMAT_VERSION:
        raise SourceAnomalyBaselineError(
            f"{path} formatVersion must be {FORMAT_VERSION}"
        )

    baseline = _object(root.get("baseline"), f"{path}.baseline")
    _only_keys(
        baseline,
        {
            "snapshotDownloadedOn",
            "snapshotArchiveSha256",
            "sourceVersions",
            "warningCounts",
        },
        f"{path}.baseline",
    )

    snapshot_date = baseline.get("snapshotDownloadedOn")
    if not isinstance(snapshot_date, str):
        raise SourceAnomalyBaselineError(
            f"{path}.baseline.snapshotDownloadedOn must be an ISO date"
        )
    try:
        date.fromisoformat(snapshot_date)
    except ValueError as exc:
        raise SourceAnomalyBaselineError(
            f"{path}.baseline.snapshotDownloadedOn must be an ISO date"
        ) from exc

    archive_sha256 = baseline.get("snapshotArchiveSha256")
    if not isinstance(archive_sha256, str) or re.fullmatch(
        r"[0-9a-f]{64}", archive_sha256
    ) is None:
        raise SourceAnomalyBaselineError(
            f"{path}.baseline.snapshotArchiveSha256 must be a lowercase SHA-256"
        )

    source_versions = _count_map(
        baseline.get("sourceVersions"),
        f"{path}.baseline.sourceVersions",
        positive=True,
    )
    warning_counts = _count_map(
        baseline.get("warningCounts"),
        f"{path}.baseline.warningCounts",
        positive=True,
    )
    if not warning_counts:
        raise SourceAnomalyBaselineError(
            f"{path}.baseline.warningCounts must not be empty"
        )

    return SourceAnomalyBaseline(
        snapshot_downloaded_on=snapshot_date,
        snapshot_archive_sha256=archive_sha256,
        source_versions=source_versions,
        warning_counts=warning_counts,
    )


def source_anomaly_baseline_applies(
    normalized: Mapping[str, Any],
    baseline: SourceAnomalyBaseline,
) -> bool:
    """Return whether a normalized downloader snapshot is new enough for the baseline."""

    meta = _object(normalized.get("_meta"), "normalized._meta")
    snapshot_date = meta.get("snapshotDownloadedOn")
    if snapshot_date is None:
        return False
    if not isinstance(snapshot_date, str):
        raise SourceAnomalyBaselineError(
            "normalized._meta.snapshotDownloadedOn must be an ISO date or null"
        )
    try:
        current = date.fromisoformat(snapshot_date)
    except ValueError as exc:
        raise SourceAnomalyBaselineError(
            "normalized._meta.snapshotDownloadedOn must be an ISO date or null"
        ) from exc
    return current >= date.fromisoformat(baseline.snapshot_downloaded_on)


def validate_source_anomaly_counts(
    warning_counts: Mapping[str, Any],
    baseline: SourceAnomalyBaseline,
) -> SourceAnomalyAudit:
    """Reject new warning categories or growth above the recorded baseline."""

    current = _count_map(warning_counts, "normalized warningCounts", positive=False)
    current = MappingProxyType({key: value for key, value in current.items() if value})

    new_categories = {
        key: count
        for key, count in current.items()
        if key not in baseline.warning_counts
    }
    growth = {
        key: (count, baseline.warning_counts[key])
        for key, count in current.items()
        if key in baseline.warning_counts and count > baseline.warning_counts[key]
    }

    if new_categories or growth:
        details: list[str] = []
        if new_categories:
            values = ", ".join(
                f"{key}={count}" for key, count in sorted(new_categories.items())
            )
            details.append(f"new categories: {values}")
        if growth:
            values = ", ".join(
                f"{key}={count} > {maximum}"
                for key, (count, maximum) in sorted(growth.items())
            )
            details.append(f"count growth: {values}")
        raise SourceAnomalyBaselineError(
            "Source anomaly regression against "
            f"{baseline.snapshot_downloaded_on} baseline: "
            + "; ".join(details)
        )

    return SourceAnomalyAudit(
        warning_count=sum(current.values()),
        warning_counts=current,
        baseline_warning_count=baseline.warning_count,
        baseline_snapshot_downloaded_on=baseline.snapshot_downloaded_on,
    )


def validate_normalized_source_anomalies(
    normalized: Mapping[str, Any],
    baseline: SourceAnomalyBaseline,
) -> SourceAnomalyAudit:
    """Validate the warning summary in a normalized Army document."""

    meta = _object(normalized.get("_meta"), "normalized._meta")
    warning_counts = meta.get("warningCounts")
    if not isinstance(warning_counts, Mapping):
        raise SourceAnomalyBaselineError(
            "normalized._meta.warningCounts must be an object"
        )
    return validate_source_anomaly_counts(warning_counts, baseline)
