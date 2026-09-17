"""Validated project configuration for weapon catalog policy and source corrections."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

WEAPON_CATEGORY_CONFIG_FORMAT = "InfinityDB weapon category config"
WEAPON_CATEGORY_CONFIG_VERSION = 1
WEAPON_OVERRIDE_CONFIG_FORMAT = "InfinityDB weapon source corrections"
WEAPON_OVERRIDE_CONFIG_VERSION = 1
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WEAPON_CATEGORY_CONFIG = PROJECT_ROOT / "config" / "catalogs" / "weapon-categories.json"
DEFAULT_WEAPON_OVERRIDE_CONFIG = PROJECT_ROOT / "config" / "catalogs" / "weapon-overrides.json"


class WeaponConfigError(ValueError):
    """Raised when maintained weapon configuration is invalid."""


@dataclass(frozen=True)
class WeaponCategoryRule:
    """One ordered weapon-family classifier rule."""

    name: str
    patterns: tuple[str, ...]


@dataclass(frozen=True)
class WeaponCategoryConfig:
    """Validated weapon-family classification policy."""

    categories: tuple[str, ...]
    rules: tuple[WeaponCategoryRule, ...]
    fallback_category: str
    overrides: Mapping[int, str]


@dataclass(frozen=True)
class WeaponMetadataProfileSuppression:
    """One exact Army metadata weapon row that should not become a display profile."""

    name: str
    mode: str | None


@dataclass(frozen=True)
class WeaponOverrideConfig:
    """Validated corrections for incomplete or inconsistent Army weapon metadata."""

    profile_overrides: Mapping[int, str]
    name_overrides: Mapping[int, str]
    metadata_profile_suppressions: Mapping[int, tuple[WeaponMetadataProfileSuppression, ...]]


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WeaponConfigError(f"{context} must be an object")
    return value


def _only_keys(value: Mapping[str, Any], allowed: set[str], context: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise WeaponConfigError(f"{context} has unknown field(s): {', '.join(sorted(unknown))}")


def _positive_int(value: Any, context: str) -> int:
    if type(value) is not int or value <= 0:
        raise WeaponConfigError(f"{context} must be a positive integer")
    return value


def _non_empty_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WeaponConfigError(f"{context} must be a non-empty string")
    return value


def parse_weapon_category_config(document: Any) -> WeaponCategoryConfig:
    """Validate and compile the authored weapon-category configuration."""

    root = _object(document, "weapon category config")
    _only_keys(
        root,
        {"format", "formatVersion", "fallbackCategory", "categories", "overrides"},
        "weapon category config",
    )
    if root.get("format") != WEAPON_CATEGORY_CONFIG_FORMAT:
        raise WeaponConfigError(
            f"weapon category config format must be {WEAPON_CATEGORY_CONFIG_FORMAT!r}"
        )
    if root.get("formatVersion") != WEAPON_CATEGORY_CONFIG_VERSION:
        raise WeaponConfigError(
            f"weapon category config formatVersion must be {WEAPON_CATEGORY_CONFIG_VERSION}"
        )

    raw_categories = root.get("categories")
    if not isinstance(raw_categories, list) or not raw_categories:
        raise WeaponConfigError("weapon category config.categories must be a non-empty array")

    rules: list[WeaponCategoryRule] = []
    category_names: list[str] = []
    seen_categories: set[str] = set()
    for index, raw_category in enumerate(raw_categories):
        context = f"weapon category config.categories[{index}]"
        category = _object(raw_category, context)
        _only_keys(category, {"name", "patterns"}, context)
        name = _non_empty_string(category.get("name"), f"{context}.name")
        if name in seen_categories:
            raise WeaponConfigError(f"weapon category config has duplicate category {name!r}")
        seen_categories.add(name)

        raw_patterns = category.get("patterns")
        if not isinstance(raw_patterns, list):
            raise WeaponConfigError(f"{context}.patterns must be an array")
        patterns: list[str] = []
        for pattern_index, raw_pattern in enumerate(raw_patterns):
            pattern_context = f"{context}.patterns[{pattern_index}]"
            pattern = _non_empty_string(raw_pattern, pattern_context)
            try:
                re.compile(pattern, re.IGNORECASE)
            except re.error as exc:
                raise WeaponConfigError(f"{pattern_context} is not a valid regex: {exc}") from exc
            patterns.append(pattern)

        category_names.append(name)
        rules.append(WeaponCategoryRule(name=name, patterns=tuple(patterns)))

    fallback = _non_empty_string(root.get("fallbackCategory"), "fallbackCategory")
    if fallback not in seen_categories:
        raise WeaponConfigError("fallbackCategory must name a declared category")
    fallback_rule = rules[category_names.index(fallback)]
    if fallback_rule.patterns:
        raise WeaponConfigError("fallback category must not define regex patterns")
    if category_names[-1] != fallback:
        raise WeaponConfigError("fallback category must be the final category")

    raw_overrides = root.get("overrides")
    if not isinstance(raw_overrides, list):
        raise WeaponConfigError("weapon category config.overrides must be an array")
    overrides: dict[int, str] = {}
    for index, raw_override in enumerate(raw_overrides):
        context = f"weapon category config.overrides[{index}]"
        override = _object(raw_override, context)
        _only_keys(override, {"weapon_id", "category", "reason"}, context)
        weapon_id = _positive_int(override.get("weapon_id"), f"{context}.weapon_id")
        category = _non_empty_string(override.get("category"), f"{context}.category")
        if category not in seen_categories:
            raise WeaponConfigError(f"{context}.category must name a declared category")
        reason = override.get("reason")
        if reason is not None:
            _non_empty_string(reason, f"{context}.reason")
        if weapon_id in overrides:
            raise WeaponConfigError(f"weapon category config has duplicate weapon ID {weapon_id}")
        overrides[weapon_id] = category

    return WeaponCategoryConfig(
        categories=tuple(category_names),
        rules=tuple(rules),
        fallback_category=fallback,
        overrides=MappingProxyType(overrides),
    )


def parse_weapon_override_config(document: Any) -> WeaponOverrideConfig:
    """Validate maintained corrections for Army weapon metadata."""

    root = _object(document, "weapon override config")
    _only_keys(root, {"format", "formatVersion", "corrections"}, "weapon override config")
    if root.get("format") != WEAPON_OVERRIDE_CONFIG_FORMAT:
        raise WeaponConfigError(
            f"weapon override config format must be {WEAPON_OVERRIDE_CONFIG_FORMAT!r}"
        )
    if root.get("formatVersion") != WEAPON_OVERRIDE_CONFIG_VERSION:
        raise WeaponConfigError(
            f"weapon override config formatVersion must be {WEAPON_OVERRIDE_CONFIG_VERSION}"
        )

    corrections = root.get("corrections")
    if not isinstance(corrections, list):
        raise WeaponConfigError("weapon override config.corrections must be an array")

    profile_overrides: dict[int, str] = {}
    name_overrides: dict[int, str] = {}
    metadata_profile_suppressions: dict[int, tuple[WeaponMetadataProfileSuppression, ...]] = {}
    seen_ids: set[int] = set()
    for index, raw_correction in enumerate(corrections):
        context = f"weapon override config.corrections[{index}]"
        correction = _object(raw_correction, context)
        _only_keys(
            correction,
            {"weapon_id", "name", "profile", "suppress_metadata_profiles", "reason"},
            context,
        )
        weapon_id = _positive_int(correction.get("weapon_id"), f"{context}.weapon_id")
        if weapon_id in seen_ids:
            raise WeaponConfigError(f"weapon override config has duplicate weapon ID {weapon_id}")
        seen_ids.add(weapon_id)

        name = correction.get("name")
        profile = correction.get("profile")
        raw_suppressions = correction.get("suppress_metadata_profiles")
        if name is None and profile is None and raw_suppressions is None:
            raise WeaponConfigError(
                f"{context} must define name, profile, and/or suppress_metadata_profiles"
            )
        if name is not None:
            name_overrides[weapon_id] = _non_empty_string(name, f"{context}.name")
        if profile is not None:
            profile_overrides[weapon_id] = _non_empty_string(profile, f"{context}.profile")
        if raw_suppressions is not None:
            if not isinstance(raw_suppressions, list) or not raw_suppressions:
                raise WeaponConfigError(
                    f"{context}.suppress_metadata_profiles must be a non-empty array"
                )
            suppressions: list[WeaponMetadataProfileSuppression] = []
            seen_suppressions: set[tuple[str, str | None]] = set()
            for suppression_index, raw_suppression in enumerate(raw_suppressions):
                suppression_context = (
                    f"{context}.suppress_metadata_profiles[{suppression_index}]"
                )
                suppression = _object(raw_suppression, suppression_context)
                _only_keys(suppression, {"name", "mode"}, suppression_context)
                suppression_name = _non_empty_string(
                    suppression.get("name"), f"{suppression_context}.name"
                )
                suppression_mode = suppression.get("mode")
                if suppression_mode is not None:
                    suppression_mode = _non_empty_string(
                        suppression_mode, f"{suppression_context}.mode"
                    )
                suppression_key = (suppression_name, suppression_mode)
                if suppression_key in seen_suppressions:
                    raise WeaponConfigError(
                        f"{context}.suppress_metadata_profiles has duplicate matcher "
                        f"{suppression_key!r}"
                    )
                seen_suppressions.add(suppression_key)
                suppressions.append(
                    WeaponMetadataProfileSuppression(
                        name=suppression_name,
                        mode=suppression_mode,
                    )
                )
            metadata_profile_suppressions[weapon_id] = tuple(suppressions)
        reason = correction.get("reason")
        if reason is not None:
            _non_empty_string(reason, f"{context}.reason")

    return WeaponOverrideConfig(
        profile_overrides=MappingProxyType(profile_overrides),
        name_overrides=MappingProxyType(name_overrides),
        metadata_profile_suppressions=MappingProxyType(metadata_profile_suppressions),
    )


def _load_json(path: Path, label: str) -> Any:
    try:
        with Path(path).open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise WeaponConfigError(f"Could not read {label} {path}: {exc}") from exc


def load_weapon_category_config(
    path: Path = DEFAULT_WEAPON_CATEGORY_CONFIG,
) -> WeaponCategoryConfig:
    """Load the authored weapon-family classification policy."""

    return parse_weapon_category_config(_load_json(path, "weapon category config"))


def load_weapon_override_config(
    path: Path = DEFAULT_WEAPON_OVERRIDE_CONFIG,
) -> WeaponOverrideConfig:
    """Load the authored Army weapon source corrections."""

    return parse_weapon_override_config(_load_json(path, "weapon override config"))
