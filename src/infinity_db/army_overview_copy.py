"""Validated maintained gameplay summaries for the Army overview."""

from __future__ import annotations

import json
from pathlib import Path

from infinity_army_data.identifier_refs import require_identifier_slug
from infinity_army_data.project_resources import maintained_curated_path

ARMY_OVERVIEW_COPY_FORMAT = "InfinityDB curated Army overview copy"
ARMY_OVERVIEW_COPY_FORMAT_VERSION = 1
DEFAULT_ARMY_OVERVIEW_COPY = maintained_curated_path("identities", "army-overview.json")
_MAX_SUMMARY_LENGTH = 240


class ArmyOverviewCopyError(ValueError):
    """Raised when maintained Army-overview copy is invalid."""


def parse_army_overview_copy(document: object) -> dict[str, str]:
    """Validate maintained Army summaries and return them keyed by public slug."""

    if not isinstance(document, dict):
        raise ArmyOverviewCopyError("Army overview copy must be an object")
    if set(document) != {"format", "formatVersion", "armies"}:
        raise ArmyOverviewCopyError(
            "Army overview copy must contain format, formatVersion, and armies"
        )
    if document.get("format") != ARMY_OVERVIEW_COPY_FORMAT:
        raise ArmyOverviewCopyError(
            f"Army overview copy must declare format {ARMY_OVERVIEW_COPY_FORMAT!r}"
        )
    if document.get("formatVersion") != ARMY_OVERVIEW_COPY_FORMAT_VERSION:
        raise ArmyOverviewCopyError(
            "Army overview copy formatVersion must be "
            f"{ARMY_OVERVIEW_COPY_FORMAT_VERSION}"
        )

    rows = document.get("armies")
    if not isinstance(rows, list):
        raise ArmyOverviewCopyError("Army overview copy.armies must be an array")

    summaries: dict[str, str] = {}
    for index, row in enumerate(rows):
        context = f"Army overview copy.armies[{index}]"
        if not isinstance(row, dict) or set(row) != {"slug", "summary"}:
            raise ArmyOverviewCopyError(
                f"{context} must contain exactly slug and summary"
            )
        try:
            slug = require_identifier_slug(row.get("slug"), context=f"{context}.slug")
        except ValueError as exc:
            raise ArmyOverviewCopyError(str(exc)) from exc
        if slug in summaries:
            raise ArmyOverviewCopyError(f"{context}.slug is duplicated: {slug!r}")

        summary = row.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise ArmyOverviewCopyError(f"{context}.summary must be a non-empty string")
        summary = summary.strip()
        if "\n" in summary or "\r" in summary:
            raise ArmyOverviewCopyError(f"{context}.summary must be one paragraph")
        if len(summary) > _MAX_SUMMARY_LENGTH:
            raise ArmyOverviewCopyError(
                f"{context}.summary must be at most {_MAX_SUMMARY_LENGTH} characters"
            )
        summaries[slug] = summary
    return summaries


def load_army_overview_copy(path: Path = DEFAULT_ARMY_OVERVIEW_COPY) -> dict[str, str]:
    """Load the maintained Army-overview copy file."""

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArmyOverviewCopyError(f"Could not load Army overview copy {path}: {exc}") from exc
    return parse_army_overview_copy(document)
