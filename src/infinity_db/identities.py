"""Validated project knowledge for source-identity exceptions and aliases."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

IDENTITY_CONFIG_SCHEMA_VERSION = 1
DEFAULT_IDENTITY_CONFIG = Path("config/identity/source-identities.json")
CATALOG_NAMES = ("skills", "equipment", "weapons")


class IdentityConfigError(ValueError):
    """Raised when the source-identity manifest is invalid."""


@dataclass(frozen=True)
class IdentityConfig:
    """Immutable, validated identity policy compiled from the authored manifest."""

    document_json: str
    content_sha256: str
    unit_aliases: Mapping[int, int]
    army_aliases: Mapping[int, int]
    catalog_aliases: Mapping[str, Mapping[int, int]]
    canonical_faction_overrides: Mapping[int, int]
    word_aliases: Mapping[str, str]
    profile_identity_ignored_words: frozenset[str]

    @property
    def document(self) -> dict[str, Any]:
        """Return a detached JSON-compatible copy of the validated manifest."""
        return json.loads(self.document_json)

    def canonical_unit_id(self, source_id: int) -> int:
        return self.unit_aliases.get(source_id, source_id)

    def canonical_army_id(self, source_id: int) -> int:
        return self.army_aliases.get(source_id, source_id)

    def canonical_catalog_id(self, catalog: str, source_id: int) -> int | None:
        aliases = self.catalog_aliases.get(catalog)
        return aliases.get(source_id) if aliases is not None else None


def _canonical_json(document: Mapping[str, Any]) -> str:
    return json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise IdentityConfigError(f"{context} must be an object")
    return value


def _only_keys(value: Mapping[str, Any], allowed: set[str], context: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise IdentityConfigError(f"{context} has unknown field(s): {', '.join(sorted(unknown))}")


def _positive_int(value: Any, context: str) -> int:
    if type(value) is not int or value <= 0:
        raise IdentityConfigError(f"{context} must be a positive integer")
    return value


def _alias_groups(value: Any, context: str) -> Mapping[int, int]:
    section = _object(value, context)
    _only_keys(section, {"groups"}, context)
    groups = section.get("groups")
    if not isinstance(groups, list):
        raise IdentityConfigError(f"{context}.groups must be an array")

    aliases: dict[int, int] = {}
    for index, raw_group in enumerate(groups):
        group_context = f"{context}.groups[{index}]"
        group = _object(raw_group, group_context)
        _only_keys(group, {"canonical_id", "source_ids", "reason"}, group_context)

        canonical_id = _positive_int(group.get("canonical_id"), f"{group_context}.canonical_id")
        source_ids = group.get("source_ids")
        if not isinstance(source_ids, list) or len(source_ids) < 2:
            raise IdentityConfigError(f"{group_context}.source_ids must contain at least two IDs")
        parsed_ids = [
            _positive_int(source_id, f"{group_context}.source_ids[{position}]")
            for position, source_id in enumerate(source_ids)
        ]
        if len(set(parsed_ids)) != len(parsed_ids):
            raise IdentityConfigError(f"{group_context}.source_ids contains duplicate IDs")
        if canonical_id not in parsed_ids:
            raise IdentityConfigError(
                f"{group_context}.canonical_id must also appear in source_ids"
            )

        reason = group.get("reason")
        if reason is not None and (not isinstance(reason, str) or not reason.strip()):
            raise IdentityConfigError(f"{group_context}.reason must be a non-empty string")

        for source_id in parsed_ids:
            if source_id in aliases:
                raise IdentityConfigError(
                    f"{context} source ID {source_id} belongs to more than one alias group"
                )
            aliases[source_id] = canonical_id

    return MappingProxyType(aliases)


def _string_map(value: Any, context: str) -> Mapping[str, str]:
    mapping = _object(value, context)
    result: dict[str, str] = {}
    for source, target in mapping.items():
        if not isinstance(source, str) or not source:
            raise IdentityConfigError(f"{context} keys must be non-empty strings")
        if not isinstance(target, str) or not target:
            raise IdentityConfigError(f"{context}.{source} must be a non-empty string")
        if source != source.casefold() or target != target.casefold():
            raise IdentityConfigError(f"{context} entries must use case-folded strings")
        result[source] = target
    return MappingProxyType(result)


def parse_identity_config(document: Any) -> IdentityConfig:
    """Validate and compile one source-identity manifest document."""

    root = _object(document, "identity config")
    _only_keys(
        root,
        {
            "schema_version",
            "units",
            "armies",
            "catalogs",
            "canonical_faction_overrides",
            "name_normalization",
            "profile_identity",
        },
        "identity config",
    )
    if root.get("schema_version") != IDENTITY_CONFIG_SCHEMA_VERSION:
        raise IdentityConfigError(
            "identity config schema_version must be "
            f"{IDENTITY_CONFIG_SCHEMA_VERSION}"
        )

    unit_aliases = _alias_groups(root.get("units"), "identity config.units")
    army_aliases = _alias_groups(root.get("armies"), "identity config.armies")

    catalogs = _object(root.get("catalogs"), "identity config.catalogs")
    _only_keys(catalogs, set(CATALOG_NAMES), "identity config.catalogs")
    if set(catalogs) != set(CATALOG_NAMES):
        missing = set(CATALOG_NAMES) - set(catalogs)
        raise IdentityConfigError(
            "identity config.catalogs is missing: " + ", ".join(sorted(missing))
        )
    catalog_aliases = MappingProxyType(
        {
            catalog: _alias_groups(catalogs[catalog], f"identity config.catalogs.{catalog}")
            for catalog in CATALOG_NAMES
        }
    )

    raw_faction_overrides = _object(
        root.get("canonical_faction_overrides"),
        "identity config.canonical_faction_overrides",
    )
    faction_overrides: dict[int, int] = {}
    for source_text, target in raw_faction_overrides.items():
        if not isinstance(source_text, str) or not source_text.isdecimal():
            raise IdentityConfigError(
                "identity config.canonical_faction_overrides keys must be positive integer strings"
            )
        source_id = _positive_int(
            int(source_text), f"identity config.canonical_faction_overrides.{source_text}"
        )
        target_id = _positive_int(
            target, f"identity config.canonical_faction_overrides.{source_text}"
        )
        faction_overrides[source_id] = target_id

    name_normalization = _object(
        root.get("name_normalization"), "identity config.name_normalization"
    )
    _only_keys(name_normalization, {"word_aliases"}, "identity config.name_normalization")
    word_aliases = _string_map(
        name_normalization.get("word_aliases"),
        "identity config.name_normalization.word_aliases",
    )

    profile_identity = _object(root.get("profile_identity"), "identity config.profile_identity")
    _only_keys(profile_identity, {"ignored_words"}, "identity config.profile_identity")
    ignored_words = profile_identity.get("ignored_words")
    if not isinstance(ignored_words, list):
        raise IdentityConfigError("identity config.profile_identity.ignored_words must be an array")
    parsed_ignored_words: list[str] = []
    for index, word in enumerate(ignored_words):
        if not isinstance(word, str) or not word:
            raise IdentityConfigError(
                f"identity config.profile_identity.ignored_words[{index}] "
                "must be a non-empty string"
            )
        if word != word.casefold():
            raise IdentityConfigError(
                "identity config.profile_identity.ignored_words entries must be case-folded"
            )
        parsed_ignored_words.append(word)
    if len(set(parsed_ignored_words)) != len(parsed_ignored_words):
        raise IdentityConfigError(
            "identity config.profile_identity.ignored_words contains duplicates"
        )

    document_json = _canonical_json(root)
    return IdentityConfig(
        document_json=document_json,
        content_sha256=hashlib.sha256(document_json.encode("utf-8")).hexdigest(),
        unit_aliases=unit_aliases,
        army_aliases=army_aliases,
        catalog_aliases=catalog_aliases,
        canonical_faction_overrides=MappingProxyType(faction_overrides),
        word_aliases=word_aliases,
        profile_identity_ignored_words=frozenset(parsed_ignored_words),
    )


def load_identity_config(path: Path = DEFAULT_IDENTITY_CONFIG) -> IdentityConfig:
    """Load and validate the authored source-identity manifest."""

    path = Path(path)
    try:
        with path.open(encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise IdentityConfigError(f"Could not read identity config {path}: {exc}") from exc
    return parse_identity_config(document)
