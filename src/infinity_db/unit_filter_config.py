"""Validated application overlays for Unit Explorer source filter vocabularies."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from infinity_army_data.project_resources import maintained_config_path
from infinity_db.domain_slugs import require_domain_slug

UNIT_FILTER_CONFIG_FORMAT = "InfinityDB Unit filter semantics"
UNIT_FILTER_CONFIG_VERSION = 1
DEFAULT_UNIT_FILTER_CONFIG = maintained_config_path(
    "catalogs", "unit-filter-semantics.json"
)


class UnitFilterConfigError(ValueError):
    """Raised when maintained Unit filter semantics are invalid."""


@dataclass(frozen=True)
class ClassificationMembership:
    """One combined source classification that matches component public filters."""

    source_classification: str
    matches: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class UnitFilterConfig:
    """Maintained Unit Explorer filter presentation/query overlays."""

    hidden_characteristics: frozenset[str]
    classification_memberships: tuple[ClassificationMembership, ...]


def _non_empty_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise UnitFilterConfigError(f"{context} must be a non-empty string")
    return value.strip()


def _slug(value: Any, context: str) -> str:
    try:
        return require_domain_slug(value, context=context)
    except ValueError as exc:
        raise UnitFilterConfigError(str(exc)) from exc


def parse_unit_filter_config(document: Any) -> UnitFilterConfig:
    """Validate maintained Unit Explorer filter overlays."""

    if not isinstance(document, dict):
        raise UnitFilterConfigError("Unit filter config must be an object")
    expected = {
        "format",
        "formatVersion",
        "hiddenCharacteristics",
        "classificationMemberships",
    }
    if set(document) != expected:
        raise UnitFilterConfigError(
            f"Unit filter config must contain exactly {sorted(expected)}"
        )
    if document.get("format") != UNIT_FILTER_CONFIG_FORMAT:
        raise UnitFilterConfigError(
            f"Unit filter config format must be {UNIT_FILTER_CONFIG_FORMAT!r}"
        )
    if document.get("formatVersion") != UNIT_FILTER_CONFIG_VERSION:
        raise UnitFilterConfigError(
            f"Unit filter config formatVersion must be {UNIT_FILTER_CONFIG_VERSION}"
        )

    raw_hidden = document.get("hiddenCharacteristics")
    if not isinstance(raw_hidden, list):
        raise UnitFilterConfigError("Unit filter config.hiddenCharacteristics must be an array")
    hidden: set[str] = set()
    for index, raw in enumerate(raw_hidden):
        context = f"Unit filter config.hiddenCharacteristics[{index}]"
        if not isinstance(raw, dict) or set(raw) != {"characteristic", "reason"}:
            raise UnitFilterConfigError(
                f"{context} must contain exactly ['characteristic', 'reason']"
            )
        characteristic = _slug(raw.get("characteristic"), f"{context}.characteristic")
        _non_empty_string(raw.get("reason"), f"{context}.reason")
        if characteristic in hidden:
            raise UnitFilterConfigError(
                f"duplicate hidden characteristic {characteristic!r}"
            )
        hidden.add(characteristic)

    raw_memberships = document.get("classificationMemberships")
    if not isinstance(raw_memberships, list):
        raise UnitFilterConfigError(
            "Unit filter config.classificationMemberships must be an array"
        )
    memberships: list[ClassificationMembership] = []
    seen_sources: set[str] = set()
    for index, raw in enumerate(raw_memberships):
        context = f"Unit filter config.classificationMemberships[{index}]"
        fields = {"sourceClassification", "matches", "reason"}
        if not isinstance(raw, dict) or set(raw) != fields:
            raise UnitFilterConfigError(
                f"{context} must contain exactly {sorted(fields)}"
            )
        source = _slug(
            raw.get("sourceClassification"), f"{context}.sourceClassification"
        )
        raw_matches = raw.get("matches")
        if not isinstance(raw_matches, list) or not raw_matches:
            raise UnitFilterConfigError(f"{context}.matches must be a non-empty array")
        matches = tuple(
            _slug(value, f"{context}.matches[{match_index}]")
            for match_index, value in enumerate(raw_matches)
        )
        if len(set(matches)) != len(matches):
            raise UnitFilterConfigError(f"{context}.matches contains duplicates")
        if source in matches:
            raise UnitFilterConfigError(
                f"{context}.matches must not include its source classification"
            )
        if source in seen_sources:
            raise UnitFilterConfigError(
                f"duplicate combined classification {source!r}"
            )
        seen_sources.add(source)
        memberships.append(
            ClassificationMembership(
                source_classification=source,
                matches=matches,
                reason=_non_empty_string(raw.get("reason"), f"{context}.reason"),
            )
        )

    return UnitFilterConfig(
        hidden_characteristics=frozenset(hidden),
        classification_memberships=tuple(memberships),
    )


@lru_cache(maxsize=1)
def load_unit_filter_config(
    path: Path = DEFAULT_UNIT_FILTER_CONFIG,
) -> UnitFilterConfig:
    """Load and validate maintained Unit Explorer filter semantics."""

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UnitFilterConfigError(f"Cannot read Unit filter config {path}: {exc}") from exc
    return parse_unit_filter_config(document)
