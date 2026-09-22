"""Validated reviewed identity mappings for Army-local Peripheral definitions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from infinity_army_data.project_resources import maintained_curated_path

from .domain_slugs import validate_typed_domain_id

PERIPHERAL_IDENTITY_FORMAT = "InfinityDB curated Peripheral identities"
PERIPHERAL_IDENTITY_FORMAT_VERSION = 1
DEFAULT_PERIPHERAL_IDENTITY_CURATED = maintained_curated_path(
    "peripherals", "army-identities.json"
)
PERIPHERAL_TYPE_IDS = frozenset(
    {
        "rule:peripheral-type:servant",
        "rule:peripheral-type:synchronized",
        "rule:peripheral-type:control",
        "rule:peripheral-type:ancillary",
        "rule:peripheral-type:cyberplug",
    }
)
PERIPHERAL_PROFILE_MODES = frozenset({"connected", "autonomous"})


class PeripheralIdentityError(ValueError):
    """Raised when reviewed Peripheral identity data is invalid."""


@dataclass(frozen=True)
class PeripheralIdentityCurated:
    """Validated reviewed Peripheral identities and Army-source mappings."""

    document_json: str
    content_sha256: str
    entity_count: int
    profile_count: int
    mapping_count: int

    @property
    def document(self) -> dict[str, Any]:
        """Return a detached JSON-compatible copy of the validated document."""
        return json.loads(self.document_json)


def _canonical_json(document: dict[str, Any]) -> str:
    return json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _require_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PeripheralIdentityError(f"{context} must be a non-empty string")
    return value


def _require_positive_int(value: Any, context: str) -> int:
    if type(value) is not int or value < 1:
        raise PeripheralIdentityError(f"{context} must be a positive integer")
    return value


def _require_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise PeripheralIdentityError(f"{context} must be an array")
    return value


def _typed_id(value: Any, *, domain: str, context: str) -> str:
    try:
        return validate_typed_domain_id(value, expected_domain=domain, context=context)
    except ValueError as exc:
        raise PeripheralIdentityError(str(exc)) from exc


def _validate_review(review: Any, context: str, *, reason_required: bool) -> None:
    if not isinstance(review, dict):
        raise PeripheralIdentityError(f"{context} must be an object")
    allowed = {"status", "reviewedOn", "reason"} if reason_required else {"status", "reviewedOn"}
    unknown = set(review) - allowed
    if unknown:
        raise PeripheralIdentityError(
            f"{context} has unknown field(s): {', '.join(sorted(unknown))}"
        )
    if review.get("status") != "reviewed":
        raise PeripheralIdentityError(f"{context}.status must be 'reviewed'")
    _require_string(review.get("reviewedOn"), f"{context}.reviewedOn")
    if reason_required:
        _require_string(review.get("reason"), f"{context}.reason")


def _validate_sources(sources: Any) -> set[str]:
    if not isinstance(sources, list) or not sources:
        raise PeripheralIdentityError("Peripheral identity data.sources must be non-empty")
    source_ids: set[str] = set()
    for index, source in enumerate(sources):
        context = f"Peripheral identity data.sources[{index}]"
        if not isinstance(source, dict):
            raise PeripheralIdentityError(f"{context} must be an object")
        allowed = {"id", "kind", "artifact", "sha256", "acquiredAt", "authority"}
        unknown = set(source) - allowed
        if unknown:
            raise PeripheralIdentityError(
                f"{context} has unknown field(s): {', '.join(sorted(unknown))}"
            )
        source_id = _require_string(source.get("id"), f"{context}.id")
        if source_id in source_ids:
            raise PeripheralIdentityError(f"{context}: duplicate source id {source_id!r}")
        source_ids.add(source_id)
        if source.get("kind") != "army-snapshot":
            raise PeripheralIdentityError(f"{context}.kind must be 'army-snapshot'")
        for field in ("artifact", "acquiredAt", "authority"):
            _require_string(source.get(field), f"{context}.{field}")
        digest = source.get("sha256")
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(char not in "0123456789abcdefABCDEF" for char in digest)
        ):
            raise PeripheralIdentityError(
                f"{context}.sha256 must be a 64-character hexadecimal digest"
            )
    return source_ids


def parse_peripheral_identity_curated(document: Any) -> PeripheralIdentityCurated:
    """Validate the reviewed Army-Peripheral identity/mapping contract."""
    if not isinstance(document, dict):
        raise PeripheralIdentityError("Peripheral identity data must be an object")
    allowed = {"format", "formatVersion", "sources", "entities", "profiles", "mappings"}
    unknown = set(document) - allowed
    if unknown:
        raise PeripheralIdentityError(
            "Peripheral identity data has unknown field(s): " + ", ".join(sorted(unknown))
        )
    if document.get("format") != PERIPHERAL_IDENTITY_FORMAT:
        raise PeripheralIdentityError(
            f"Peripheral identity data must declare format {PERIPHERAL_IDENTITY_FORMAT!r}"
        )
    if document.get("formatVersion") != PERIPHERAL_IDENTITY_FORMAT_VERSION:
        raise PeripheralIdentityError(
            "Peripheral identity data formatVersion must be "
            f"{PERIPHERAL_IDENTITY_FORMAT_VERSION}"
        )

    source_ids = _validate_sources(document.get("sources"))
    entities = _require_list(document.get("entities"), "Peripheral identity data.entities")
    profiles = _require_list(document.get("profiles"), "Peripheral identity data.profiles")
    mappings = _require_list(document.get("mappings"), "Peripheral identity data.mappings")

    entity_ids: set[str] = set()
    for index, entity in enumerate(entities):
        context = f"Peripheral identity data.entities[{index}]"
        if not isinstance(entity, dict):
            raise PeripheralIdentityError(f"{context} must be an object")
        allowed_entity = {"id", "name", "typeId", "review"}
        unknown_entity = set(entity) - allowed_entity
        if unknown_entity:
            raise PeripheralIdentityError(
                f"{context} has unknown field(s): {', '.join(sorted(unknown_entity))}"
            )
        entity_id = _typed_id(entity.get("id"), domain="peripheral", context=f"{context}.id")
        if entity_id in entity_ids:
            raise PeripheralIdentityError(f"{context}: duplicate entity id {entity_id!r}")
        entity_ids.add(entity_id)
        _require_string(entity.get("name"), f"{context}.name")
        if entity.get("typeId") not in PERIPHERAL_TYPE_IDS:
            raise PeripheralIdentityError(f"{context}.typeId must reference a core Peripheral type")
        _validate_review(entity.get("review"), f"{context}.review", reason_required=False)

    profile_entities: dict[str, str] = {}
    for index, profile in enumerate(profiles):
        context = f"Peripheral identity data.profiles[{index}]"
        if not isinstance(profile, dict):
            raise PeripheralIdentityError(f"{context} must be an object")
        allowed_profile = {"id", "entityId", "name", "mode", "review"}
        unknown_profile = set(profile) - allowed_profile
        if unknown_profile:
            raise PeripheralIdentityError(
                f"{context} has unknown field(s): {', '.join(sorted(unknown_profile))}"
            )
        profile_id = _typed_id(
            profile.get("id"), domain="peripheral-profile", context=f"{context}.id"
        )
        if profile_id in profile_entities:
            raise PeripheralIdentityError(f"{context}: duplicate profile id {profile_id!r}")
        entity_id = _typed_id(
            profile.get("entityId"), domain="peripheral", context=f"{context}.entityId"
        )
        if entity_id not in entity_ids:
            raise PeripheralIdentityError(f"{context}.entityId references unknown entity")
        profile_entities[profile_id] = entity_id
        _require_string(profile.get("name"), f"{context}.name")
        if "mode" in profile and profile["mode"] not in PERIPHERAL_PROFILE_MODES:
            raise PeripheralIdentityError(
                f"{context}.mode must be 'connected' or 'autonomous'"
            )
        _validate_review(profile.get("review"), f"{context}.review", reason_required=False)

    mapping_ids: set[str] = set()
    source_keys: set[tuple[str, int, int]] = set()
    for index, mapping in enumerate(mappings):
        context = f"Peripheral identity data.mappings[{index}]"
        if not isinstance(mapping, dict):
            raise PeripheralIdentityError(f"{context} must be an object")
        allowed_mapping = {
            "id",
            "sourceId",
            "armyId",
            "peripheralId",
            "sourceName",
            "entityId",
            "profileId",
            "review",
        }
        unknown_mapping = set(mapping) - allowed_mapping
        if unknown_mapping:
            raise PeripheralIdentityError(
                f"{context} has unknown field(s): {', '.join(sorted(unknown_mapping))}"
            )
        mapping_id = _typed_id(
            mapping.get("id"), domain="peripheral-mapping", context=f"{context}.id"
        )
        if mapping_id in mapping_ids:
            raise PeripheralIdentityError(f"{context}: duplicate mapping id {mapping_id!r}")
        mapping_ids.add(mapping_id)
        source_id = mapping.get("sourceId")
        if not isinstance(source_id, str) or source_id not in source_ids:
            raise PeripheralIdentityError(f"{context}.sourceId must reference a declared source")
        army_id = _require_positive_int(mapping.get("armyId"), f"{context}.armyId")
        peripheral_id = _require_positive_int(
            mapping.get("peripheralId"), f"{context}.peripheralId"
        )
        source_key = (source_id, army_id, peripheral_id)
        if source_key in source_keys:
            raise PeripheralIdentityError(
                f"{context}: duplicate source Peripheral identity {source_key!r}"
            )
        source_keys.add(source_key)
        _require_string(mapping.get("sourceName"), f"{context}.sourceName")
        entity_id = _typed_id(
            mapping.get("entityId"), domain="peripheral", context=f"{context}.entityId"
        )
        if entity_id not in entity_ids:
            raise PeripheralIdentityError(f"{context}.entityId references unknown entity")
        if "profileId" in mapping:
            profile_id = _typed_id(
                mapping.get("profileId"),
                domain="peripheral-profile",
                context=f"{context}.profileId",
            )
            if profile_entities.get(profile_id) != entity_id:
                raise PeripheralIdentityError(
                    f"{context}.profileId must reference a profile belonging to entityId"
                )
        _validate_review(mapping.get("review"), f"{context}.review", reason_required=True)

    document_json = _canonical_json(document)
    return PeripheralIdentityCurated(
        document_json=document_json,
        content_sha256=hashlib.sha256(document_json.encode("utf-8")).hexdigest(),
        entity_count=len(entities),
        profile_count=len(profiles),
        mapping_count=len(mappings),
    )


def load_peripheral_identity_curated(
    path: Path = DEFAULT_PERIPHERAL_IDENTITY_CURATED,
) -> PeripheralIdentityCurated:
    """Load and validate reviewed Peripheral identities/mappings."""
    path = Path(path)
    try:
        with path.open(encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise PeripheralIdentityError(
            f"Could not read Peripheral identity curated data {path}: {exc}"
        ) from exc
    return parse_peripheral_identity_curated(document)
