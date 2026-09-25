"""Validated presentation classifications for Army's skill-like source bucket."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from infinity_army_data.identifier_refs import IdentifierRef, parse_identifier_ref
from infinity_army_data.project_resources import maintained_config_path

SKILL_SOURCE_CONFIG_FORMAT = "InfinityDB skill source classifications"
SKILL_SOURCE_CONFIG_VERSION = 1
DEFAULT_SKILL_SOURCE_CONFIG = maintained_config_path(
    "catalogs", "skill-source-classifications.json"
)
_CLASSIFICATIONS = frozenset(
    {"equipment", "training", "attribute-override", "source-marker"}
)


class SkillConfigError(ValueError):
    """Raised when maintained Skill source classification is invalid."""


@dataclass(frozen=True)
class SkillSourceClassification:
    """One Army skill-like identity that is not a rules-domain Skill."""

    skill_ref: IdentifierRef
    classification: str
    reason: str


def _non_empty_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SkillConfigError(f"{context} must be a non-empty string")
    return value.strip()


def parse_skill_source_config(document: Any) -> tuple[SkillSourceClassification, ...]:
    """Validate the maintained Army skill-like classification overlay."""

    if not isinstance(document, dict):
        raise SkillConfigError("skill source config must be an object")
    expected = {"format", "formatVersion", "classifications"}
    if set(document) != expected:
        raise SkillConfigError(
            f"skill source config must contain exactly {sorted(expected)}"
        )
    if document.get("format") != SKILL_SOURCE_CONFIG_FORMAT:
        raise SkillConfigError(
            f"skill source config format must be {SKILL_SOURCE_CONFIG_FORMAT!r}"
        )
    if document.get("formatVersion") != SKILL_SOURCE_CONFIG_VERSION:
        raise SkillConfigError(
            f"skill source config formatVersion must be {SKILL_SOURCE_CONFIG_VERSION}"
        )
    raw_items = document.get("classifications")
    if not isinstance(raw_items, list):
        raise SkillConfigError("skill source config.classifications must be an array")

    result: list[SkillSourceClassification] = []
    seen: set[IdentifierRef] = set()
    for index, raw in enumerate(raw_items):
        context = f"skill source config.classifications[{index}]"
        if not isinstance(raw, dict):
            raise SkillConfigError(f"{context} must be an object")
        expected_fields = {"skill_id", "classification", "reason"}
        if set(raw) != expected_fields:
            raise SkillConfigError(
                f"{context} must contain exactly {sorted(expected_fields)}"
            )
        try:
            skill_ref = parse_identifier_ref(raw.get("skill_id"), context=f"{context}.skill_id")
        except ValueError as exc:
            raise SkillConfigError(str(exc)) from exc
        classification = _non_empty_string(
            raw.get("classification"), f"{context}.classification"
        )
        if classification not in _CLASSIFICATIONS:
            raise SkillConfigError(
                f"{context}.classification must be one of {sorted(_CLASSIFICATIONS)}"
            )
        reason = _non_empty_string(raw.get("reason"), f"{context}.reason")
        if skill_ref in seen:
            raise SkillConfigError(f"duplicate Skill source reference {skill_ref!r}")
        seen.add(skill_ref)
        result.append(
            SkillSourceClassification(
                skill_ref=skill_ref,
                classification=classification,
                reason=reason,
            )
        )
    return tuple(result)


def load_skill_source_config(
    path: Path = DEFAULT_SKILL_SOURCE_CONFIG,
) -> tuple[SkillSourceClassification, ...]:
    """Load and validate maintained Skill source classifications."""

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SkillConfigError(f"Cannot read skill source config {path}: {exc}") from exc
    return parse_skill_source_config(document)
