"""Build semantic symbol publications from verified external handoffs."""

from __future__ import annotations

import json
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, NamedTuple

from infinity_db.identities import load_identity_config, normalized_profile_identity
from infinity_db.snapshot_provenance import sha256_file
from tools.path_sanitization import sanitize_filename

PUBLICATION_MAPPING_FORMAT = "InfinityDB symbol publication mapping"
PUBLICATION_MAPPING_VERSION = 2
PUBLICATION_MANIFEST = "symbol-publication.json"
GENERATED_CATEGORIES = (
    "armies",
    "characteristics",
    "orders",
    "peripherals",
    "units",
)
_TEXT_ROOT_TAGS = {"text", "flowRoot"}
_STATIC_PUBLIC_STEMS = {"cube2": "cube-2"}
_REINFORCEMENT_UNIT_SLUG_PREFIX = "reinf-"
_UNIT_PROFILE_JSON_PATH = re.compile(
    r"\.profileGroups\[(\d+)\]\.profiles\[(\d+)\]\.logo$"
)
_REINFORCEMENT_PERIPHERAL_PREFIX = re.compile(
    r"^\s*reinf(?:orcement)?\s*[.:]\s*", re.IGNORECASE
)


class FactionInfo(NamedTuple):
    identifier: int
    slug: str
    parent: int


class SnapshotIndex(NamedTuple):
    factions: dict[int, FactionInfo]
    unit_canonical_faction_by_reference: dict[tuple[str, int, str], int | None]


def slugify(value: str) -> str:
    """Return an ASCII, lowercase, dash-separated filename component."""
    return sanitize_filename(value).removesuffix(".svg")


def portable_svg_member(value: str) -> PurePosixPath:
    """Reject paths that are not portable relative publication members."""
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or path.is_absolute()
        or ".." in path.parts
        or any(part in {"", "."} for part in path.parts)
    ):
        raise ValueError(f"Symbol path is not a portable relative path: {value!r}")
    return path


def load_snapshot_index(path: Path) -> SnapshotIndex:
    """Load faction hierarchy and per-source unit canonical-faction context."""
    factions: dict[int, FactionInfo] = {}
    canonical_factions: dict[tuple[str, int, str], int | None] = {}
    with zipfile.ZipFile(path) as archive:
        try:
            metadata = json.loads(archive.read("metadata.json"))
        except (KeyError, json.JSONDecodeError) as exc:
            raise ValueError(f"Army snapshot has invalid metadata.json: {exc}") from exc
        rows = metadata.get("factions")
        if not isinstance(rows, list):
            raise ValueError("Army snapshot metadata.json factions must be an array")
        for row in rows:
            if not isinstance(row, dict) or type(row.get("id")) is not int:
                continue
            identifier = row["id"]
            raw_slug = row.get("slug") or row.get("name") or str(identifier)
            if not isinstance(raw_slug, str) or not raw_slug.strip():
                raw_slug = str(identifier)
            parent = row.get("parent")
            if type(parent) is not int:
                parent = identifier
            factions[identifier] = FactionInfo(
                identifier=identifier,
                slug=slugify(raw_slug),
                parent=parent,
            )

        for name in sorted(archive.namelist()):
            if name == "metadata.json" or not name.endswith(".json"):
                continue
            try:
                document = json.loads(archive.read(name))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Army snapshot member {name} is invalid JSON: {exc}") from exc
            units = document.get("units")
            if not isinstance(units, list):
                continue
            for unit in units:
                if not isinstance(unit, dict) or type(unit.get("id")) is not int:
                    continue
                raw_slug = unit.get("slug") or unit.get("isc")
                if not isinstance(raw_slug, str) or not raw_slug.strip():
                    continue
                canonical = unit.get("canonical")
                canonical_faction_id = canonical if type(canonical) is int else None
                canonical_factions[(name, unit["id"], slugify(raw_slug))] = canonical_faction_id
    return SnapshotIndex(
        factions=factions,
        unit_canonical_faction_by_reference=canonical_factions,
    )


def _faction_public_path(reference: dict[str, Any], index: SnapshotIndex) -> str:
    faction_id = reference.get("factionId")
    if type(faction_id) is not int:
        raise ValueError("Authoritative faction reference is missing factionId")
    info = index.factions.get(faction_id)
    raw_slug = reference.get("factionSlug")
    if info is None:
        if not isinstance(raw_slug, str) or not raw_slug.strip():
            raise ValueError(f"Faction {faction_id} has no usable publication slug")
        faction_slug = slugify(raw_slug)
    else:
        faction_slug = info.slug
    parent = index.factions.get(info.parent) if info is not None else None
    folder = parent.slug if parent is not None else faction_slug
    return f"armies/{folder}/{faction_id}-{faction_slug}.svg"


def _unit_profile_slot(reference: dict[str, Any]) -> tuple[int, int] | None:
    json_path = reference.get("jsonPath")
    if not isinstance(json_path, str):
        return None
    match = _UNIT_PROFILE_JSON_PATH.search(json_path)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def _unit_reference_canonical_faction(
    reference: dict[str, Any], index: SnapshotIndex
) -> int | None:
    unit_id = reference.get("unitId")
    raw_slug = reference.get("unitSlug")
    source_document = reference.get("sourceDocument")
    if (
        type(unit_id) is not int
        or not isinstance(raw_slug, str)
        or not raw_slug.strip()
        or not isinstance(source_document, str)
    ):
        return None
    return index.unit_canonical_faction_by_reference.get(
        (source_document, unit_id, slugify(raw_slug))
    )


def _unit_public_path(reference: dict[str, Any], index: SnapshotIndex) -> str:
    unit_id = reference.get("unitId")
    raw_slug = reference.get("unitSlug")
    if type(unit_id) is not int or not isinstance(raw_slug, str) or not raw_slug.strip():
        raise ValueError("Authoritative unit reference requires unitId and unitSlug")
    unit_slug = slugify(raw_slug)
    canonical_faction_id = _unit_reference_canonical_faction(reference, index)
    faction_info = (
        index.factions.get(canonical_faction_id)
        if canonical_faction_id is not None
        else None
    )
    folder = faction_info.slug if faction_info is not None else "unassigned"
    stem = f"units/{folder}/{unit_id}-{unit_slug}"

    suffix_parts: list[str] = []
    army_id = reference.get("armyId")
    if (
        type(canonical_faction_id) is int
        and type(army_id) is int
        and army_id != canonical_faction_id
    ):
        suffix_parts.extend(("army", str(army_id)))

    slot = _unit_profile_slot(reference)
    if slot is not None and slot != (0, 0):
        group_index, profile_index = slot
        suffix_parts.extend((str(group_index + 1), str(profile_index + 1)))

    suffix = f"--{'-'.join(suffix_parts)}" if suffix_parts else ""
    return f"{stem}{suffix}.svg"


def _peripheral_reference(reference: dict[str, Any]) -> bool:
    """Return whether Army explicitly identifies one profile as a Peripheral."""
    name = reference.get("peripheralName")
    return isinstance(name, str) and bool(name.strip())


def _profile_name_key(reference: dict[str, Any]) -> str | None:
    raw_name = reference.get("profileName")
    if not isinstance(raw_name, str) or not raw_name.strip():
        return None
    key = slugify(raw_name)
    return key or None


def _mixed_role_profile_names(
    references_by_canonical: dict[str, list[dict[str, Any]]],
) -> set[str]:
    """Return profile names physically evidenced in both Peripheral and normal roles."""
    mixed: set[str] = set()
    for references in references_by_canonical.values():
        roles_by_name: dict[str, set[bool]] = defaultdict(set)
        for reference in references:
            if reference.get("kind") != "unit-profile":
                continue
            name_key = _profile_name_key(reference)
            if name_key is None:
                continue
            roles_by_name[name_key].add(_peripheral_reference(reference))
        mixed.update(
            name for name, roles in roles_by_name.items() if roles == {False, True}
        )
    return mixed


def _peripheral_public_path(reference: dict[str, Any], index: SnapshotIndex) -> str:
    raw_name = reference.get("peripheralName")
    if not isinstance(raw_name, str) or not raw_name.strip():
        raise ValueError("Peripheral profile reference requires peripheralName")

    canonical_faction_id = _unit_reference_canonical_faction(reference, index)
    faction_info = (
        index.factions.get(canonical_faction_id)
        if canonical_faction_id is not None
        else None
    )
    parent = index.factions.get(faction_info.parent) if faction_info is not None else None
    folder = parent.slug if parent is not None else (
        faction_info.slug if faction_info is not None else "unassigned"
    )
    public_name, _is_reinforcement = _base_peripheral_name(raw_name)
    return f"peripherals/{folder}/{slugify(public_name)}.svg"


def _base_peripheral_name(raw_name: str) -> tuple[str, bool]:
    """Return a Peripheral name with an Army reinforcement prefix removed."""
    match = _REINFORCEMENT_PERIPHERAL_PREFIX.match(raw_name)
    if match is None:
        return raw_name.strip(), False
    base_name = raw_name[match.end() :].strip()
    return (base_name or raw_name.strip()), bool(base_name)


def _peripheral_occurrence_family(
    reference: dict[str, Any], index: SnapshotIndex
) -> FactionInfo | None:
    """Return the main-Army family for the Army occurrence of one Peripheral."""
    army_id = reference.get("armyId")
    if type(army_id) is not int:
        return None
    faction_info = index.factions.get(army_id)
    if faction_info is None:
        return None
    return index.factions.get(faction_info.parent) or faction_info


def _prefer_non_reinforcement_peripheral_path(
    selected_reference: dict[str, Any],
    references: list[dict[str, Any]],
    index: SnapshotIndex,
) -> str | None:
    """Resolve a reinforcement alias to its normal Peripheral identity when evidenced.

    Army can expose byte-identical standalone Peripheral assets under both normal
    and ``REINF:``/``REINF.`` Unit identities. A reinforcement-only canonical
    faction can otherwise win normal publication ranking and leak both its prefix
    and reinforcement army folder into the public path. Only repair that case when
    the same physical canonical asset also has a non-reinforcement reference whose
    normalized Peripheral name matches.
    """
    raw_name = selected_reference.get("peripheralName")
    if not isinstance(raw_name, str):
        return None
    base_name, is_reinforcement = _base_peripheral_name(raw_name)
    if not is_reinforcement:
        return None
    base_slug = slugify(base_name)

    matching: list[dict[str, Any]] = []
    for reference in references:
        candidate_name = reference.get("peripheralName")
        if not isinstance(candidate_name, str):
            continue
        candidate_base, candidate_is_reinforcement = _base_peripheral_name(candidate_name)
        if candidate_is_reinforcement or slugify(candidate_base) != base_slug:
            continue
        matching.append(reference)
    if not matching:
        return None

    family_counts: Counter[int] = Counter()
    family_by_id: dict[int, FactionInfo] = {}
    for reference in matching:
        family = _peripheral_occurrence_family(reference, index)
        if family is None:
            continue
        family_counts[family.identifier] += 1
        family_by_id[family.identifier] = family
    if family_counts:
        family_id = min(family_counts, key=lambda key: (-family_counts[key], key))
        return f"peripherals/{family_by_id[family_id].slug}/{base_slug}.svg"

    best_reference = min(matching, key=lambda row: _reference_rank(row, index))
    fallback = _peripheral_public_path(best_reference, index)
    folder = portable_svg_member(fallback).parts[1]
    return f"peripherals/{folder}/{base_slug}.svg"


def _static_public_path(reference: dict[str, Any]) -> str:
    key = reference.get("staticKey")
    category = reference.get("staticCategory")
    if not isinstance(key, str) or not key.strip():
        raise ValueError("Authoritative static reference is missing staticKey")
    if category not in {"orders", "characteristics"}:
        raise ValueError(f"Unsupported static symbol category: {category!r}")
    stem = _STATIC_PUBLIC_STEMS.get(key, slugify(key))
    return f"{category}/{stem}.svg"


def _publication_candidate(
    reference: dict[str, Any],
    index: SnapshotIndex,
    mixed_role_profile_names: set[str] | frozenset[str] = frozenset(),
) -> str:
    kind = reference.get("kind")
    if kind == "faction":
        return _faction_public_path(reference, index)
    if kind == "unit-profile":
        name_key = _profile_name_key(reference)
        if (
            _peripheral_reference(reference)
            and name_key not in mixed_role_profile_names
        ):
            return _peripheral_public_path(reference, index)
        return _unit_public_path(reference, index)
    if kind == "static":
        return _static_public_path(reference)
    raise ValueError(f"Unsupported authoritative symbol reference kind: {kind!r}")


def _publication_rank(
    reference: dict[str, Any],
    index: SnapshotIndex,
    mixed_role_profile_names: set[str],
) -> tuple[Any, ...]:
    name_key = _profile_name_key(reference)
    mixed_peripheral_rank = int(
        reference.get("kind") == "unit-profile"
        and _peripheral_reference(reference)
        and name_key in mixed_role_profile_names
    )
    return (mixed_peripheral_rank, *_reference_rank(reference, index))


def _namespace(path: str) -> str:
    return portable_svg_member(path).parts[0]


def _reference_rank(
    reference: dict[str, Any], index: SnapshotIndex
) -> tuple[int, int, int, int, int, int, int, int, str]:
    kind = reference.get("kind")
    if kind == "faction":
        identifier = reference.get("factionId")
        slug = reference.get("factionSlug")
        return (
            0,
            0,
            0,
            0,
            identifier if type(identifier) is int else 2**31,
            0,
            0,
            0,
            str(slug or ""),
        )
    if kind == "unit-profile":
        identifier = reference.get("unitId")
        slug = reference.get("unitSlug")
        canonical_faction_id = _unit_reference_canonical_faction(reference, index)
        army_id = reference.get("armyId")
        canonical_faction_rank = (
            0
            if type(canonical_faction_id) is not int
            or type(army_id) is not int
            or army_id == canonical_faction_id
            else 1
        )
        # Shared Unit artwork should be named for the ordinary Unit rather than a
        # Reinforcements-only source variant. Peripheral aliases have their own
        # canonicalization rules and must keep their existing evidence ranking.
        reinforcement_rank = (
            1
            if not _peripheral_reference(reference)
            and isinstance(slug, str)
            and slugify(slug).startswith(_REINFORCEMENT_UNIT_SLUG_PREFIX)
            else 0
        )
        slot = _unit_profile_slot(reference)
        group_index, profile_index = slot if slot is not None else (0, 0)
        primary_rank = 0 if slot is None or slot == (0, 0) else 1
        return (
            1,
            reinforcement_rank,
            canonical_faction_rank,
            primary_rank,
            identifier if type(identifier) is int else 2**31,
            group_index,
            profile_index,
            army_id if type(army_id) is int else 2**31,
            str(slug or ""),
        )
    key = reference.get("staticKey")
    return (2, 0, 0, 0, 0, 0, 0, 0, str(key or ""))


def _semantic_profile_mapping(
    references: list[dict[str, Any]], unit_mapping: dict[str, str]
) -> dict[str, str]:
    """Resolve high-confidence cross-unit profile symbols from Army evidence.

    A semantic profile symbol is only promoted when one published path is a
    strict majority across distinct parent Unit symbols for the normalized profile
    identity and is observed as a non-unit override against at least two different
    parent Unit symbols. Repeated Army occurrences of the same Unit count once.
    This repairs repeated source-assignment mistakes (for example Crabbots that
    incorrectly reuse their parent TAG symbol) without turning one contextual
    variant into a global override.
    """

    identity_config = load_identity_config()
    evidence: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    for reference in references:
        profile_name = reference.get("profile_name")
        unit_id = reference.get("unit_id")
        unit_slug = reference.get("unit_slug")
        published_path = reference.get("published_path")
        if (
            not isinstance(profile_name, str)
            or not profile_name.strip()
            or type(unit_id) is not int
            or not isinstance(unit_slug, str)
            or not isinstance(published_path, str)
        ):
            continue
        identity = normalized_profile_identity(profile_name, identity_config)
        unit_path = unit_mapping.get(unit_slug)
        if identity and unit_path is not None:
            evidence[identity].append((unit_id, published_path, unit_path))

    mapping: dict[str, str] = {}
    for identity, rows in sorted(evidence.items()):
        candidates_by_parent: dict[str, set[str]] = defaultdict(set)
        for _unit_id, published_path, unit_path in rows:
            candidates_by_parent[unit_path].add(published_path)

        parent_votes = [
            (unit_path, next(iter(candidates)))
            for unit_path, candidates in candidates_by_parent.items()
            if len(candidates) == 1
        ]
        counts = Counter(published_path for _, published_path in parent_votes)
        if not counts:
            continue
        published_path, count = counts.most_common(1)[0]
        if count * 2 <= len(parent_votes):
            continue
        override_parent_paths = {
            unit_path
            for unit_path, candidate in parent_votes
            if candidate == published_path and candidate != unit_path
        }
        if len(override_parent_paths) < 2:
            continue
        mapping[identity] = published_path
    return mapping


def _peripheral_variant_path(
    base_path: str, reference: dict[str, Any], index: SnapshotIndex
) -> str:
    """Return a deterministic context suffix for a colliding Peripheral asset."""
    unit_id = reference.get("unitId")
    raw_slug = reference.get("unitSlug")
    if type(unit_id) is not int or not isinstance(raw_slug, str) or not raw_slug.strip():
        raise ValueError("Peripheral variant reference requires unitId and unitSlug")

    suffix_parts = [str(unit_id), slugify(raw_slug)]
    canonical_faction_id = _unit_reference_canonical_faction(reference, index)
    army_id = reference.get("armyId")
    if (
        type(canonical_faction_id) is int
        and type(army_id) is int
        and army_id != canonical_faction_id
    ):
        suffix_parts.extend(("army", str(army_id)))
    slot = _unit_profile_slot(reference)
    if slot is not None:
        group_index, profile_index = slot
        suffix_parts.extend((str(group_index + 1), str(profile_index + 1)))
    return f"{base_path.removesuffix('.svg')}--{'-'.join(suffix_parts)}.svg"


def _resolve_peripheral_path_collisions(
    canonical_to_published: dict[str, str],
    references_by_canonical: dict[str, list[dict[str, Any]]],
    index: SnapshotIndex,
) -> None:
    """Preserve distinct Peripheral artwork that shares one semantic filename.

    The most broadly evidenced canonical asset keeps the clean Peripheral name.
    Other physical variants remain published with deterministic source-Unit
    context, so source evidence is never silently discarded.
    """
    by_path: dict[str, list[str]] = defaultdict(list)
    for canonical, published in canonical_to_published.items():
        if _namespace(published) == "peripherals":
            by_path[published.casefold()].append(canonical)

    for canonicals in by_path.values():
        if len(canonicals) < 2:
            continue
        base_path = canonical_to_published[canonicals[0]]
        folded_base_path = base_path.casefold()
        evidence_keys: dict[str, tuple[int, tuple[Any, ...], str]] = {}
        for canonical in canonicals:
            matching = [
                row
                for row in references_by_canonical[canonical]
                if _publication_candidate(row, index).casefold() == folded_base_path
            ]
            unit_ids = {
                row["unitId"]
                for row in matching
                if type(row.get("unitId")) is int
            }
            best_rank = min(_reference_rank(row, index) for row in matching)
            evidence_keys[canonical] = (-len(unit_ids), best_rank, canonical)

        winner = min(canonicals, key=evidence_keys.__getitem__)
        used = {base_path.casefold()}
        for canonical in sorted(canonicals, key=evidence_keys.__getitem__):
            if canonical == winner:
                canonical_to_published[canonical] = base_path
                continue
            matching = sorted(
                (
                    row
                    for row in references_by_canonical[canonical]
                    if _publication_candidate(row, index).casefold() == base_path.casefold()
                ),
                key=lambda row: _reference_rank(row, index),
            )
            if not matching:
                raise ValueError(
                    f"Peripheral collision has no matching source reference: {canonical}"
                )
            variant = _peripheral_variant_path(base_path, matching[0], index)
            folded = variant.casefold()
            if folded in used:
                raise ValueError(f"Peripheral variant path collision: {variant}")
            used.add(folded)
            canonical_to_published[canonical] = variant


def _has_active_text(root: ET.Element) -> bool:
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] not in _TEXT_ROOT_TAGS:
            continue
        if "".join(element.itertext()).strip():
            return True
    return False


def build_publication(
    *,
    assets: list[dict[str, Any]],
    references: list[dict[str, Any]],
    canonical_by_source: dict[str, str],
    army_artifact: dict[str, Any],
    unavailable_assets: list[dict[str, Any]],
    snapshot_index: SnapshotIndex,
    compressed_root: Path,
    staging_static: Path,
) -> tuple[dict[str, Any], dict[str, int]]:
    """Build semantic paths from verified assets and authoritative Army references.

    The external handoff is verified before calling this mapper. This function
    never installs the resulting publication.
    """
    asset_by_url = {row["url"]: row["archivePath"] for row in assets}
    unavailable_urls = {row["url"] for row in unavailable_assets}
    canonical_paths = sorted(set(canonical_by_source.values()))

    actual_compressed = {
        path.relative_to(compressed_root).as_posix()
        for path in compressed_root.rglob("*.svg")
        if path.is_file()
    }
    if actual_compressed != set(canonical_paths):
        raise ValueError(
            "Compressed symbol work tree does not contain exactly the manifest canonical set"
        )

    references_by_canonical: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for reference in references:
        if not reference.get("authoritative"):
            continue
        asset_url = reference["assetUrl"]
        archive_path = asset_by_url.get(asset_url)
        if archive_path is None:
            if asset_url in unavailable_urls:
                continue
            raise ValueError(
                f"Authoritative reference has no acquired/unavailable asset: {asset_url}"
            )
        canonical = canonical_by_source.get(archive_path)
        if not isinstance(canonical, str):
            raise ValueError(f"Source asset has no canonical mapping: {archive_path}")
        references_by_canonical[canonical].append(reference)

    mixed_role_profile_names = _mixed_role_profile_names(references_by_canonical)

    canonical_to_published: dict[str, str] = {}
    for canonical in canonical_paths:
        canonical_references = references_by_canonical.get(canonical, [])
        if not canonical_references:
            raise ValueError(f"Canonical asset has no authoritative references: {canonical}")
        ranked_candidates = sorted(
            (
                (
                    _publication_rank(row, snapshot_index, mixed_role_profile_names),
                    _publication_candidate(
                        row, snapshot_index, mixed_role_profile_names
                    ),
                    row,
                )
                for row in canonical_references
            ),
            key=lambda item: (item[0], item[1]),
        )
        candidates = sorted({candidate for _, candidate, _row in ranked_candidates})
        namespaces = {_namespace(candidate) for candidate in candidates}
        if namespaces == {"units", "peripherals"}:
            # Source Army sometimes assigns the parent Unit artwork to an embedded
            # Peripheral profile. Physical artwork already owned by a Unit stays in
            # the Unit namespace; the Peripheral reference remains provenance only.
            ranked_candidates = [
                row for row in ranked_candidates if _namespace(row[1]) == "units"
            ]
            candidates = sorted({candidate for _, candidate, _row in ranked_candidates})
            namespaces = {"units"}
        elif len(namespaces) != 1:
            raise ValueError(
                f"Canonical asset crosses incompatible publication namespaces {canonical}: "
                + ", ".join(candidates)
            )
        if namespaces & {"orders", "characteristics"} and len(candidates) != 1:
            raise ValueError(
                "Static symbols with different public keys cannot share one physical canonical "
                f"asset: {canonical}: {', '.join(candidates)}"
            )
        selected_candidate = ranked_candidates[0][1]
        selected_reference = ranked_candidates[0][2]
        if _namespace(selected_candidate) == "peripherals":
            preferred = _prefer_non_reinforcement_peripheral_path(
                selected_reference, canonical_references, snapshot_index
            )
            if preferred is not None:
                selected_candidate = preferred
        canonical_to_published[canonical] = selected_candidate

    _resolve_peripheral_path_collisions(
        canonical_to_published, references_by_canonical, snapshot_index
    )

    casefolded: dict[str, str] = {}
    for canonical, published in canonical_to_published.items():
        folded = published.casefold()
        previous = casefolded.get(folded)
        if previous is not None and previous != canonical:
            raise ValueError(f"Published symbol path collision: {published}")
        casefolded[folded] = canonical

    source_to_published = {
        source: canonical_to_published[canonical]
        for source, canonical in sorted(canonical_by_source.items())
    }
    if set(source_to_published) != {row["archivePath"] for row in assets}:
        raise ValueError("Publication mapping does not account for every source asset")

    army_mapping: dict[int, str] = {}
    unit_mapping: dict[str, str] = {}
    unit_mapping_candidates: dict[
        tuple[int, str],
        list[tuple[tuple[int, int, int, int, int, int, int, int, str], str]],
    ] = defaultdict(list)
    unit_profile_references: list[dict[str, Any]] = []
    static_mapping: dict[str, str] = {}
    for reference in references:
        if not reference.get("authoritative"):
            continue
        asset_url = reference["assetUrl"]
        source = asset_by_url.get(asset_url)
        if source is None:
            if asset_url in unavailable_urls:
                continue
            raise ValueError(
                f"Authoritative reference has no acquired/unavailable asset: {asset_url}"
            )
        published = source_to_published[source]
        kind = reference["kind"]
        if kind == "faction":
            faction_id = reference.get("factionId")
            if type(faction_id) is not int:
                raise ValueError("Authoritative faction reference is missing factionId")
            if not published.startswith("armies/"):
                raise ValueError(f"Faction {faction_id} resolved outside armies/: {published}")
            browser_path = published.removeprefix("armies/")
            previous = army_mapping.setdefault(faction_id, browser_path)
            if previous != browser_path:
                raise ValueError(
                    f"Faction {faction_id} resolves to conflicting symbols: "
                    f"{previous} vs {browser_path}"
                )
        elif kind == "unit-profile":
            unit_id = reference.get("unitId")
            raw_slug = reference.get("unitSlug")
            if (
                type(unit_id) is not int
                or not isinstance(raw_slug, str)
                or not raw_slug.strip()
            ):
                raise ValueError("Authoritative unit reference requires unitId and unitSlug")
            key = slugify(raw_slug)
            if not published.endswith(".svg") or _namespace(published) not in {
                "units",
                "peripherals",
            }:
                raise ValueError(
                    f"Unit profile {key!r} resolved outside unit/peripheral symbols: {published}"
                )
            unit_mapping_candidates[(unit_id, key)].append(
                (_reference_rank(reference, snapshot_index), published)
            )
            unit_profile_references.append(
                {
                    "unit_id": unit_id,
                    "unit_slug": key,
                    "profile_name": reference.get("profileName"),
                    "asset_url": asset_url,
                    "published_path": published,
                }
            )
        elif kind == "static":
            key = reference.get("staticKey")
            if not isinstance(key, str) or not key.strip():
                raise ValueError("Authoritative static reference is missing staticKey")
            expected = _static_public_path(reference)
            if published != expected:
                raise ValueError(
                    f"Static symbol {key!r} resolved to {published}, expected {expected}"
                )
            previous = static_mapping.setdefault(key, published)
            if previous != published:
                raise ValueError(f"Static symbol {key!r} resolves to conflicting paths")

    for (_unit_id, key), candidates in sorted(unit_mapping_candidates.items()):
        browser_path = min(candidates)[1]
        previous = unit_mapping.setdefault(key, browser_path)
        if previous != browser_path:
            raise ValueError(
                f"Unit slug {key!r} resolves to conflicting symbols: "
                f"{previous} vs {browser_path}"
            )

    unit_profile_mapping: dict[str, str] = {}
    for reference in unit_profile_references:
        key = reference["unit_slug"]
        asset_url = reference["asset_url"]
        published_path = reference["published_path"]
        if key not in unit_mapping:
            raise ValueError(f"Unit profile {key!r} has no primary browser symbol")
        # Keep every authoritative profile-logo resolution as occurrence evidence.
        # A source Unit's primary logo can still be a distinct General-profile
        # symbol after several source Units collapse into one logical Unit. Runtime
        # profile enrichment decides whether that evidence forms one unambiguous
        # override or should fall back to the logical Unit symbol.
        previous = unit_profile_mapping.setdefault(asset_url, published_path)
        if previous != published_path:
            raise ValueError(
                f"Profile logo {asset_url!r} resolves to conflicting symbols: "
                f"{previous} vs {published_path}"
            )

    semantic_profile_mapping = _semantic_profile_mapping(
        unit_profile_references, unit_mapping
    )

    staging_static.mkdir(parents=True, exist_ok=True)
    for category in GENERATED_CATEGORIES:
        (staging_static / category).mkdir(parents=True, exist_ok=True)
    published_sha256: dict[str, str] = {}
    published_bytes = 0
    for canonical, published in sorted(canonical_to_published.items()):
        source = compressed_root.joinpath(*portable_svg_member(canonical).parts)
        destination = staging_static.joinpath(*portable_svg_member(published).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        try:
            root = ET.parse(destination).getroot()
        except (ET.ParseError, OSError) as exc:
            raise ValueError(f"Published SVG is not parseable for {published}: {exc}") from exc
        if root.tag.rsplit("}", 1)[-1] != "svg":
            raise ValueError(f"Published symbol root is not <svg>: {published}")
        if _has_active_text(root):
            raise ValueError(f"Published symbol unexpectedly contains active text: {published}")
        published_sha256[published] = sha256_file(destination)
        published_bytes += destination.stat().st_size

    browser_referenced_paths = {
        *(f"armies/{value}" for value in army_mapping.values()),
        *unit_mapping.values(),
        *unit_profile_mapping.values(),
        *semantic_profile_mapping.values(),
        *static_mapping.values(),
    }
    unreferenced_published_paths = set(published_sha256) - browser_referenced_paths

    actual_published = {
        path.relative_to(staging_static).as_posix()
        for category in GENERATED_CATEGORIES
        for path in (staging_static / category).rglob("*.svg")
        if path.is_file()
    }
    if actual_published != set(canonical_to_published.values()):
        raise ValueError("Temporary publication tree does not match the canonical publication map")

    summary = {
        "sourceAssetCount": len(assets),
        "canonicalAssetCount": len(canonical_paths),
        "publishedAssetCount": len(actual_published),
        "factionMappingCount": len(army_mapping),
        "unitMappingCount": len(unit_mapping),
        "staticMappingCount": len(static_mapping),
        "publishedBytes": published_bytes,
    }
    report = {
        "format": PUBLICATION_MAPPING_FORMAT,
        "formatVersion": PUBLICATION_MAPPING_VERSION,
        "sourceSnapshot": {
            "armyArtifact": {
                "name": army_artifact["name"],
                "sha256": army_artifact["sha256"],
            }
        },
        "summary": dict(sorted(summary.items())),
        "sourceArchivePathToPublishedPath": source_to_published,
        "canonicalArchivePathToPublishedPath": dict(sorted(canonical_to_published.items())),
        "factionIdToPublishedPath": {
            str(key): f"armies/{value}" for key, value in sorted(army_mapping.items())
        },
        "unitSlugToPublishedPath": dict(sorted(unit_mapping.items())),
        "unitProfileLogoToPublishedPath": dict(sorted(unit_profile_mapping.items())),
        "profileIdentityToPublishedPath": dict(sorted(semantic_profile_mapping.items())),
        "staticKeyToPublishedPath": dict(sorted(static_mapping.items())),
        "publishedSha256ByPath": dict(sorted(published_sha256.items())),
        "browserUsageSummary": {
            "browserReferencedAssetCount": len(browser_referenced_paths),
            "unreferencedPublishedAssetCount": len(unreferenced_published_paths),
        },
        "unavailableSourceAssets": unavailable_assets,
    }
    return report, summary
