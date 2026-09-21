"""Validated curated display-identity relationships for Army-derived data."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from infinity_army_data.identifier_refs import (
    IdentifierRef,
    normalize_identifier_slug,
    parse_identifier_ref,
)
from infinity_army_data.project_resources import maintained_curated_path

DISPLAY_IDENTITY_FORMAT = "InfinityDB curated display identities"
DISPLAY_IDENTITY_FORMAT_VERSION = 2
DEFAULT_DISPLAY_IDENTITY_CURATED = maintained_curated_path("identities", "army-display.json")
DISPLAY_IDENTITY_METADATA_KEY = "displayIdentityCurated"
DISPLAY_IDENTITY_SHA256_METADATA_KEY = "displayIdentityCuratedSha256"


class DisplayIdentityError(ValueError):
    """Raised when curated display-identity data is invalid."""


@dataclass(frozen=True)
class DisplayIdentityCurated:
    """Immutable display-identity relationships compiled from curated data."""

    document_json: str
    content_sha256: str
    canonical_faction_display_armies: Mapping[IdentifierRef, IdentifierRef]

    @property
    def document(self) -> dict[str, Any]:
        """Return a detached JSON-compatible copy of the validated document."""
        return json.loads(self.document_json)

    def resolve_factions(
        self,
        factions: Iterable[Mapping[str, Any]],
        *,
        active_canonical_ids: set[int] | None = None,
    ) -> Mapping[int, int]:
        """Resolve authored faction references against source faction identities."""

        by_id: dict[int, Mapping[str, Any]] = {}
        slug_owners: dict[str, set[int]] = defaultdict(set)
        for row in factions:
            faction_id = row.get("id")
            if type(faction_id) is not int or faction_id <= 0:
                continue
            existing = by_id.get(faction_id)
            if existing is None:
                by_id[faction_id] = row
            for raw_slug in (row.get("slug"), normalize_identifier_slug(row.get("name"))):
                if isinstance(raw_slug, str) and raw_slug:
                    slug_owners[raw_slug].add(faction_id)

        def resolve(reference: IdentifierRef, context: str) -> int:
            if isinstance(reference, int):
                return reference
            owners = sorted(slug_owners.get(reference, ()))
            if not owners:
                raise DisplayIdentityError(
                    f"{context} references unknown source faction slug {reference!r}"
                )
            if len(owners) > 1:
                raise DisplayIdentityError(
                    f"{context} source faction slug {reference!r} is ambiguous across IDs "
                    f"{owners!r}"
                )
            return owners[0]

        resolved: dict[int, int] = {}
        for canonical_ref, display_ref in self.canonical_faction_display_armies.items():
            canonical_id = resolve(canonical_ref, "canonicalFactionId")
            if active_canonical_ids is not None and canonical_id not in active_canonical_ids:
                continue
            display_id = resolve(display_ref, "displayArmyId")
            if canonical_id in resolved:
                raise DisplayIdentityError(
                    f"multiple curated mappings resolve to canonical faction ID {canonical_id}"
                )
            resolved[canonical_id] = display_id
        return MappingProxyType(resolved)

    def resolve_master(self, master: Mapping[str, Any]) -> Mapping[int, int]:
        """Resolve display mappings against the source identities available in one master."""

        rows_by_id: dict[int, dict[str, Any]] = {}
        metadata = master.get("armyMetadata")
        if isinstance(metadata, Mapping):
            data = metadata.get("data")
            if isinstance(data, Mapping):
                for row in data.get("factions", ()) or ():
                    if isinstance(row, Mapping) and type(row.get("id")) is int:
                        rows_by_id[row["id"]] = dict(row)
        for raw_id, army in (master.get("armyLists") or {}).items():
            try:
                army_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            if not isinstance(army, Mapping):
                continue
            meta = army.get("_meta")
            if not isinstance(meta, Mapping):
                continue
            row = rows_by_id.setdefault(army_id, {"id": army_id})
            if not row.get("slug") and isinstance(meta.get("slug"), str):
                row["slug"] = meta["slug"]
            if not row.get("name") and isinstance(meta.get("name"), str):
                row["name"] = meta["name"]

        active_canonical_ids: set[int] = set()
        for unit in (master.get("units") or {}).values():
            if not isinstance(unit, Mapping):
                continue
            shared = unit.get("shared")
            if isinstance(shared, Mapping) and type(shared.get("canonical")) is int:
                active_canonical_ids.add(shared["canonical"])
        return self.resolve_factions(
            rows_by_id.values(), active_canonical_ids=active_canonical_ids
        )


def _canonical_json(document: Mapping[str, Any]) -> str:
    return json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _identifier_ref(value: Any, context: str) -> IdentifierRef:
    try:
        return parse_identifier_ref(value, context=context)
    except ValueError as exc:
        raise DisplayIdentityError(str(exc)) from exc


def parse_display_identity_curated(document: Any) -> DisplayIdentityCurated:
    """Validate and compile the curated army display-identity document."""
    if not isinstance(document, dict):
        raise DisplayIdentityError("display identity curated data must be an object")
    allowed = {"format", "formatVersion", "sources", "mappings"}
    unknown = set(document) - allowed
    if unknown:
        raise DisplayIdentityError(
            "display identity curated data has unknown field(s): "
            + ", ".join(sorted(unknown))
        )
    if document.get("format") != DISPLAY_IDENTITY_FORMAT:
        raise DisplayIdentityError(
            f"display identity curated data must declare format {DISPLAY_IDENTITY_FORMAT!r}"
        )
    if document.get("formatVersion") != DISPLAY_IDENTITY_FORMAT_VERSION:
        raise DisplayIdentityError(
            "display identity curated data formatVersion must be "
            f"{DISPLAY_IDENTITY_FORMAT_VERSION}"
        )

    sources = document.get("sources")
    if not isinstance(sources, list) or not sources:
        raise DisplayIdentityError("display identity curated data.sources must be non-empty")
    source_ids: set[str] = set()
    for index, source in enumerate(sources):
        context = f"display identity curated data.sources[{index}]"
        if not isinstance(source, dict):
            raise DisplayIdentityError(f"{context} must be an object")
        allowed_source = {"id", "kind", "artifact", "sha256", "acquiredAt", "authority"}
        unknown_source = set(source) - allowed_source
        if unknown_source:
            raise DisplayIdentityError(
                f"{context} has unknown field(s): {', '.join(sorted(unknown_source))}"
            )
        for field in ("id", "artifact", "acquiredAt", "authority"):
            value = source.get(field)
            if not isinstance(value, str) or not value.strip():
                raise DisplayIdentityError(f"{context}.{field} must be a non-empty string")
        if source.get("kind") != "army-snapshot":
            raise DisplayIdentityError(f"{context}.kind must be 'army-snapshot'")
        digest = source.get("sha256")
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(char not in "0123456789abcdefABCDEF" for char in digest)
        ):
            raise DisplayIdentityError(
                f"{context}.sha256 must be a 64-character hexadecimal digest"
            )
        if source["id"] in source_ids:
            raise DisplayIdentityError(f"{context}: duplicate source id {source['id']!r}")
        source_ids.add(source["id"])

    mappings = document.get("mappings")
    if not isinstance(mappings, list) or not mappings:
        raise DisplayIdentityError("display identity curated data.mappings must be non-empty")

    compiled: dict[IdentifierRef, IdentifierRef] = {}
    for index, mapping in enumerate(mappings):
        context = f"display identity curated data.mappings[{index}]"
        if not isinstance(mapping, dict):
            raise DisplayIdentityError(f"{context} must be an object")
        allowed_mapping = {"canonicalFactionId", "displayArmyId", "sourceId", "reason"}
        unknown_mapping = set(mapping) - allowed_mapping
        if unknown_mapping:
            raise DisplayIdentityError(
                f"{context} has unknown field(s): {', '.join(sorted(unknown_mapping))}"
            )
        canonical_faction_ref = _identifier_ref(
            mapping.get("canonicalFactionId"), f"{context}.canonicalFactionId"
        )
        display_army_ref = _identifier_ref(
            mapping.get("displayArmyId"), f"{context}.displayArmyId"
        )
        source_id = mapping.get("sourceId")
        if not isinstance(source_id, str) or source_id not in source_ids:
            raise DisplayIdentityError(f"{context}.sourceId must reference a declared source")
        reason = mapping.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise DisplayIdentityError(f"{context}.reason must be a non-empty string")
        if canonical_faction_ref in compiled:
            raise DisplayIdentityError(
                f"{context}: duplicate canonical faction reference {canonical_faction_ref!r}"
            )
        compiled[canonical_faction_ref] = display_army_ref

    document_json = _canonical_json(document)
    return DisplayIdentityCurated(
        document_json=document_json,
        content_sha256=hashlib.sha256(document_json.encode("utf-8")).hexdigest(),
        canonical_faction_display_armies=MappingProxyType(compiled),
    )


def parse_display_identity_metadata(document: Any, content_sha256: Any) -> DisplayIdentityCurated:
    """Validate curated display identity loaded from snapshot metadata."""
    if not isinstance(content_sha256, str):
        raise DisplayIdentityError("display identity metadata hash must be a string")
    curated = parse_display_identity_curated(document)
    if curated.content_sha256 != content_sha256:
        raise DisplayIdentityError("display identity metadata hash does not match its document")
    return curated


def load_display_identity_curated(
    path: Path = DEFAULT_DISPLAY_IDENTITY_CURATED,
) -> DisplayIdentityCurated:
    """Load and validate authored curated display-identity relationships."""
    path = Path(path)
    try:
        with path.open(encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise DisplayIdentityError(
            f"Could not read display identity curated data {path}: {exc}"
        ) from exc
    return parse_display_identity_curated(document)


def display_identity_metadata(curated: DisplayIdentityCurated) -> dict[str, Any]:
    """Return curated display-identity provenance persisted with a normalized snapshot."""
    return {
        DISPLAY_IDENTITY_METADATA_KEY: curated.document,
        DISPLAY_IDENTITY_SHA256_METADATA_KEY: curated.content_sha256,
    }
