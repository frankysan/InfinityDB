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
PERIPHERAL_IDENTITY_FORMAT_VERSION = 3
PERIPHERAL_IDENTITY_METADATA_KEY = "peripheralIdentityCurated"
PERIPHERAL_IDENTITY_SHA256_METADATA_KEY = "peripheralIdentityCuratedSha256"
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
    unit_mapping_count: int
    controller_access_count: int

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
    allowed = {
        "format",
        "formatVersion",
        "sources",
        "entities",
        "profiles",
        "mappings",
        "unitMappings",
        "controllerAccess",
    }
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
    unit_mappings = _require_list(
        document.get("unitMappings"), "Peripheral identity data.unitMappings"
    )
    controller_access = _require_list(
        document.get("controllerAccess"), "Peripheral identity data.controllerAccess"
    )

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
        if "typeId" in entity and entity.get("typeId") not in PERIPHERAL_TYPE_IDS:
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

    unit_mapping_ids: set[str] = set()
    unit_source_keys: set[tuple[str, int]] = set()
    unit_mapping_types_by_logical_id: dict[int, set[str]] = {}
    for index, mapping in enumerate(unit_mappings):
        context = f"Peripheral identity data.unitMappings[{index}]"
        if not isinstance(mapping, dict):
            raise PeripheralIdentityError(f"{context} must be an object")
        allowed_mapping = {
            "id",
            "sourceId",
            "unitId",
            "sourceName",
            "logicalUnitId",
            "typeId",
            "review",
        }
        unknown_mapping = set(mapping) - allowed_mapping
        if unknown_mapping:
            raise PeripheralIdentityError(
                f"{context} has unknown field(s): {', '.join(sorted(unknown_mapping))}"
            )
        mapping_id = _typed_id(
            mapping.get("id"),
            domain="peripheral-unit-mapping",
            context=f"{context}.id",
        )
        if mapping_id in unit_mapping_ids:
            raise PeripheralIdentityError(
                f"{context}: duplicate Unit-backed mapping id {mapping_id!r}"
            )
        unit_mapping_ids.add(mapping_id)
        source_id = mapping.get("sourceId")
        if not isinstance(source_id, str) or source_id not in source_ids:
            raise PeripheralIdentityError(f"{context}.sourceId must reference a declared source")
        unit_id = _require_positive_int(mapping.get("unitId"), f"{context}.unitId")
        source_key = (source_id, unit_id)
        if source_key in unit_source_keys:
            raise PeripheralIdentityError(
                f"{context}: duplicate source Unit-backed Peripheral identity {source_key!r}"
            )
        unit_source_keys.add(source_key)
        _require_string(mapping.get("sourceName"), f"{context}.sourceName")
        logical_unit_id = _require_positive_int(
            mapping.get("logicalUnitId"), f"{context}.logicalUnitId"
        )
        type_id = mapping.get("typeId")
        if type_id not in PERIPHERAL_TYPE_IDS:
            raise PeripheralIdentityError(
                f"{context}.typeId must reference a core Peripheral type"
            )
        unit_mapping_types_by_logical_id.setdefault(logical_unit_id, set()).add(str(type_id))
        _validate_review(mapping.get("review"), f"{context}.review", reason_required=True)

    controller_access_ids: set[str] = set()
    controller_access_keys: set[tuple[str, str, int, int, int, int, str]] = set()
    for index, access in enumerate(controller_access):
        context = f"Peripheral identity data.controllerAccess[{index}]"
        if not isinstance(access, dict):
            raise PeripheralIdentityError(f"{context} must be an object")
        allowed_access = {
            "id",
            "sourceId",
            "controllerKind",
            "armyId",
            "unitId",
            "groupId",
            "parentId",
            "sourceName",
            "typeId",
            "targetLogicalUnitIds",
            "relationship",
            "review",
        }
        unknown_access = set(access) - allowed_access
        if unknown_access:
            raise PeripheralIdentityError(
                f"{context} has unknown field(s): {', '.join(sorted(unknown_access))}"
            )
        access_id = _typed_id(
            access.get("id"),
            domain="peripheral-controller-access",
            context=f"{context}.id",
        )
        if access_id in controller_access_ids:
            raise PeripheralIdentityError(
                f"{context}: duplicate Controller access id {access_id!r}"
            )
        controller_access_ids.add(access_id)
        source_id = access.get("sourceId")
        if not isinstance(source_id, str) or source_id not in source_ids:
            raise PeripheralIdentityError(f"{context}.sourceId must reference a declared source")
        controller_kind = access.get("controllerKind")
        if controller_kind not in {"profile", "loadout"}:
            raise PeripheralIdentityError(
                f"{context}.controllerKind must be 'profile' or 'loadout'"
            )
        army_id = _require_positive_int(access.get("armyId"), f"{context}.armyId")
        unit_id = _require_positive_int(access.get("unitId"), f"{context}.unitId")
        group_id = _require_positive_int(access.get("groupId"), f"{context}.groupId")
        parent_id = _require_positive_int(access.get("parentId"), f"{context}.parentId")
        type_id = access.get("typeId")
        if type_id not in PERIPHERAL_TYPE_IDS:
            raise PeripheralIdentityError(
                f"{context}.typeId must reference a core Peripheral type"
            )
        source_key = (
            source_id,
            controller_kind,
            army_id,
            unit_id,
            group_id,
            parent_id,
            str(type_id),
        )
        if source_key in controller_access_keys:
            raise PeripheralIdentityError(
                f"{context}: duplicate source Controller access identity {source_key!r}"
            )
        controller_access_keys.add(source_key)
        _require_string(access.get("sourceName"), f"{context}.sourceName")
        if access.get("relationship") != "access-pool":
            raise PeripheralIdentityError(
                f"{context}.relationship must be 'access-pool'"
            )
        target_ids = _require_list(
            access.get("targetLogicalUnitIds"), f"{context}.targetLogicalUnitIds"
        )
        if not target_ids:
            raise PeripheralIdentityError(
                f"{context}.targetLogicalUnitIds must contain at least one logical Unit"
            )
        normalized_target_ids = [
            _require_positive_int(value, f"{context}.targetLogicalUnitIds[{target_index}]")
            for target_index, value in enumerate(target_ids)
        ]
        if len(set(normalized_target_ids)) != len(normalized_target_ids):
            raise PeripheralIdentityError(
                f"{context}.targetLogicalUnitIds must not contain duplicates"
            )
        for target_id in normalized_target_ids:
            if str(type_id) not in unit_mapping_types_by_logical_id.get(target_id, set()):
                raise PeripheralIdentityError(
                    f"{context}.targetLogicalUnitIds references logical Unit {target_id} "
                    f"without a reviewed Unit-backed mapping for type {type_id!r}"
                )
        _validate_review(access.get("review"), f"{context}.review", reason_required=True)

    document_json = _canonical_json(document)
    return PeripheralIdentityCurated(
        document_json=document_json,
        content_sha256=hashlib.sha256(document_json.encode("utf-8")).hexdigest(),
        entity_count=len(entities),
        profile_count=len(profiles),
        mapping_count=len(mappings),
        unit_mapping_count=len(unit_mappings),
        controller_access_count=len(controller_access),
    )


def parse_peripheral_identity_metadata(
    document: Any, content_sha256: Any
) -> PeripheralIdentityCurated:
    """Validate curated Peripheral identities loaded from database metadata."""
    if not isinstance(content_sha256, str):
        raise PeripheralIdentityError("Peripheral identity metadata hash must be a string")
    curated = parse_peripheral_identity_curated(document)
    if curated.content_sha256 != content_sha256:
        raise PeripheralIdentityError(
            "Peripheral identity metadata hash does not match its document"
        )
    return curated


def peripheral_identity_metadata(curated: PeripheralIdentityCurated) -> dict[str, Any]:
    """Return reviewed Peripheral provenance persisted with an application database."""
    return {
        PERIPHERAL_IDENTITY_METADATA_KEY: curated.document,
        PERIPHERAL_IDENTITY_SHA256_METADATA_KEY: curated.content_sha256,
    }


def peripheral_identity_source_for_snapshot(
    curated: PeripheralIdentityCurated, snapshot_sha256: object
) -> str | None:
    """Return the unique curated source ID matching one Army snapshot digest."""
    if not isinstance(snapshot_sha256, str) or not snapshot_sha256:
        return None
    matches = [
        source["id"]
        for source in curated.document["sources"]
        if str(source.get("sha256", "")).casefold() == snapshot_sha256.casefold()
    ]
    if len(matches) > 1:
        raise PeripheralIdentityError(
            "Peripheral identity data has multiple sources for the same Army snapshot"
        )
    return matches[0] if matches else None

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
