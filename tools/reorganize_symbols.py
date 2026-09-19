"""Publish verified canonical symbols into the web application's static tree.

This is the final, non-destructive symbol-pipeline stage. It consumes a pinned
Army snapshot, a version-7 compressed symbol build, and the complete compressed
canonical work tree. It builds and validates a temporary publication tree,
generates browser mappings from authoritative manifest references, and only
then transactionally replaces the generated static symbol directories and maps.
Raw snapshots and processing work trees are never moved or deleted.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, NamedTuple

from infinity_db.snapshot_provenance import sha256_file
from infinity_db.symbol_manifest import (
    SYMBOL_BUILD_COMPRESSION_VERSION,
    add_publication,
    load_symbol_manifest,
    write_symbol_manifest,
)

try:
    from tools.path_sanitization import sanitize_filename
except ImportError:  # pragma: no cover - direct script execution fallback
    from path_sanitization import sanitize_filename

SYMBOL_MAP = "unit-symbol-map.js"
ARMY_MAP = "army-symbols.js"
PUBLICATION_MAPPING_FORMAT = "InfinityDB symbol publication mapping"
PUBLICATION_MAPPING_VERSION = 2
REMOVED_SYMBOL_BACKUP_FORMAT = "InfinityDB removed symbol backup"
REMOVED_SYMBOL_BACKUP_VERSION = 1
GENERATED_CATEGORIES = ("armies", "characteristics", "orders", "units")
_TEXT_ROOT_TAGS = {"text", "flowRoot"}
_STATIC_PUBLIC_STEMS = {"cube2": "cube-2"}
_UNIT_PROFILE_JSON_PATH = re.compile(
    r"\.profileGroups\[(\d+)\]\.profiles\[(\d+)\]\.logo$"
)


class FactionInfo(NamedTuple):
    identifier: int
    slug: str
    parent: int


class SnapshotIndex(NamedTuple):
    factions: dict[int, FactionInfo]
    unit_owner_by_reference: dict[tuple[str, int, str], int | None]


class PublicationResult(NamedTuple):
    static_root: Path
    mapping_report: Path
    army_map: Path
    unit_map: Path
    summary: dict[str, int]
    changes: dict[str, int]
    removed_backup: Path | None
    status: str


def slugify(value: str) -> str:
    """Return an ASCII, lowercase, dash-separated filename component."""
    return sanitize_filename(value).removesuffix(".svg")


def _portable_member(value: str) -> PurePosixPath:
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


def _load_snapshot_index(path: Path) -> SnapshotIndex:
    """Load faction hierarchy and per-source unit canonical ownership."""
    factions: dict[int, FactionInfo] = {}
    owners: dict[tuple[str, int, str], int | None] = {}
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
                owner = canonical if type(canonical) is int else None
                owners[(name, unit["id"], slugify(raw_slug))] = owner
    return SnapshotIndex(factions=factions, unit_owner_by_reference=owners)


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


def _unit_reference_owner(
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
    return index.unit_owner_by_reference.get(
        (source_document, unit_id, slugify(raw_slug))
    )


def _unit_public_path(reference: dict[str, Any], index: SnapshotIndex) -> str:
    unit_id = reference.get("unitId")
    raw_slug = reference.get("unitSlug")
    if type(unit_id) is not int or not isinstance(raw_slug, str) or not raw_slug.strip():
        raise ValueError("Authoritative unit reference requires unitId and unitSlug")
    unit_slug = slugify(raw_slug)
    owner = _unit_reference_owner(reference, index)
    owner_info = index.factions.get(owner) if owner is not None else None
    folder = owner_info.slug if owner_info is not None else "unassigned"
    stem = f"units/{folder}/{unit_id}-{unit_slug}"

    suffix_parts: list[str] = []
    army_id = reference.get("armyId")
    if type(owner) is int and type(army_id) is int and army_id != owner:
        suffix_parts.extend(("army", str(army_id)))

    slot = _unit_profile_slot(reference)
    if slot is not None and slot != (0, 0):
        group_index, profile_index = slot
        suffix_parts.extend((str(group_index + 1), str(profile_index + 1)))

    suffix = f"--{'-'.join(suffix_parts)}" if suffix_parts else ""
    return f"{stem}{suffix}.svg"


def _static_public_path(reference: dict[str, Any]) -> str:
    key = reference.get("staticKey")
    category = reference.get("staticCategory")
    if not isinstance(key, str) or not key.strip():
        raise ValueError("Authoritative static reference is missing staticKey")
    if category not in {"orders", "characteristics"}:
        raise ValueError(f"Unsupported static symbol category: {category!r}")
    stem = _STATIC_PUBLIC_STEMS.get(key, slugify(key))
    return f"{category}/{stem}.svg"


def _publication_candidate(reference: dict[str, Any], index: SnapshotIndex) -> str:
    kind = reference.get("kind")
    if kind == "faction":
        return _faction_public_path(reference, index)
    if kind == "unit-profile":
        return _unit_public_path(reference, index)
    if kind == "static":
        return _static_public_path(reference)
    raise ValueError(f"Unsupported authoritative symbol reference kind: {kind!r}")


def _namespace(path: str) -> str:
    return _portable_member(path).parts[0]


def _reference_rank(
    reference: dict[str, Any], index: SnapshotIndex
) -> tuple[int, int, int, int, int, int, int, str]:
    kind = reference.get("kind")
    if kind == "faction":
        identifier = reference.get("factionId")
        slug = reference.get("factionSlug")
        return (
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
        owner = _unit_reference_owner(reference, index)
        army_id = reference.get("armyId")
        owner_rank = (
            0
            if type(owner) is not int or type(army_id) is not int or army_id == owner
            else 1
        )
        slot = _unit_profile_slot(reference)
        group_index, profile_index = slot if slot is not None else (0, 0)
        primary_rank = 0 if slot is None or slot == (0, 0) else 1
        return (
            1,
            owner_rank,
            primary_rank,
            identifier if type(identifier) is int else 2**31,
            group_index,
            profile_index,
            army_id if type(army_id) is int else 2**31,
            str(slug or ""),
        )
    key = reference.get("staticKey")
    return (2, 0, 0, 0, 0, 0, 0, str(key or ""))


def _render_army_map(mapping: dict[int, str]) -> str:
    lines = ["const armySymbols = new Map(["]
    lines.extend(f'  [{key}, {json.dumps(value)}],' for key, value in sorted(mapping.items()))
    lines.extend(
        [
            "]);",
            "",
            "export function armySymbolPath(armyId) {",
            "  const symbol = armySymbols.get(armyId);",
            "  const version = document.documentElement.dataset.appVersion;",
            (
                "  return symbol && `/static/armies/${encodeURI(symbol)}?v="
                "${encodeURIComponent(version)}`;"
            ),
            "}",
            "",
        ]
    )
    return "\n".join(lines)


def _render_unit_map(mapping: dict[str, str]) -> str:
    lines = ["const unitSymbolSlugs = new Map(["]
    lines.extend(
        f"  [{json.dumps(key)}, {json.dumps(value)}],"
        for key, value in sorted(mapping.items())
    )
    lines.extend(
        [
            "]);",
            "",
            "export function unitSymbolSlug(unitSlug) {",
            "  return unitSymbolSlugs.get(unitSlug);",
            "}",
            "",
        ]
    )
    return "\n".join(lines)


def _has_active_text(root: ET.Element) -> bool:
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] not in _TEXT_ROOT_TAGS:
            continue
        if "".join(element.itertext()).strip():
            return True
    return False


def _build_publication(
    *,
    manifest: dict[str, Any],
    snapshot_index: SnapshotIndex,
    compressed_root: Path,
    staging_static: Path,
) -> tuple[dict[str, Any], dict[str, int]]:
    assets = manifest["assets"]
    asset_by_url = {row["url"]: row["archivePath"] for row in assets}
    unavailable_urls = {row["url"] for row in manifest.get("unavailableAssets", [])}
    duplicate = manifest["processing"]["duplicateDetection"]
    canonical_by_source = duplicate["canonicalByArchivePath"]
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
    for reference in manifest["references"]:
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

    canonical_to_published: dict[str, str] = {}
    for canonical in canonical_paths:
        references = references_by_canonical.get(canonical, [])
        if not references:
            raise ValueError(f"Canonical asset has no authoritative references: {canonical}")
        ranked_candidates = sorted(
            (_reference_rank(row, snapshot_index), _publication_candidate(row, snapshot_index))
            for row in references
        )
        candidates = sorted({candidate for _, candidate in ranked_candidates})
        namespaces = {_namespace(candidate) for candidate in candidates}
        if len(namespaces) != 1:
            raise ValueError(
                f"Canonical asset crosses incompatible publication namespaces {canonical}: "
                + ", ".join(candidates)
            )
        if namespaces & {"orders", "characteristics"} and len(candidates) != 1:
            raise ValueError(
                "Static symbols with different public keys cannot share one physical canonical "
                f"asset: {canonical}: {', '.join(candidates)}"
            )
        canonical_to_published[canonical] = ranked_candidates[0][1]

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
        list[tuple[tuple[int, int, int, int, int, int, int, str], str]],
    ] = defaultdict(list)
    static_mapping: dict[str, str] = {}
    for reference in manifest["references"]:
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
            if not published.startswith("units/") or not published.endswith(".svg"):
                raise ValueError(f"Unit {key!r} resolved outside units/: {published}")
            browser_path = published.removeprefix("units/").removesuffix(".svg")
            unit_mapping_candidates[(unit_id, key)].append(
                (_reference_rank(reference, snapshot_index), browser_path)
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

    staging_static.mkdir(parents=True, exist_ok=True)
    for category in GENERATED_CATEGORIES:
        (staging_static / category).mkdir(parents=True, exist_ok=True)
    published_sha256: dict[str, str] = {}
    published_bytes = 0
    for canonical, published in sorted(canonical_to_published.items()):
        source = compressed_root.joinpath(*_portable_member(canonical).parts)
        destination = staging_static.joinpath(*_portable_member(published).parts)
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

    army_map = staging_static / ARMY_MAP
    unit_map = staging_static / SYMBOL_MAP
    army_map.write_text(_render_army_map(army_mapping), encoding="utf-8", newline="\n")
    unit_map.write_text(_render_unit_map(unit_mapping), encoding="utf-8", newline="\n")

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
        "summary": dict(sorted(summary.items())),
        "sourceArchivePathToPublishedPath": source_to_published,
        "canonicalArchivePathToPublishedPath": dict(sorted(canonical_to_published.items())),
        "factionIdToPublishedPath": {
            str(key): f"armies/{value}" for key, value in sorted(army_mapping.items())
        },
        "unitSlugToPublishedPath": {
            key: f"units/{value}.svg" for key, value in sorted(unit_mapping.items())
        },
        "staticKeyToPublishedPath": dict(sorted(static_mapping.items())),
        "publishedSha256ByPath": dict(sorted(published_sha256.items())),
        "unavailableSourceAssets": manifest.get("unavailableAssets", []),
    }
    return report, summary


def _published_symbol_inventory(static_root: Path) -> dict[str, str]:
    inventory: dict[str, str] = {}
    for category in GENERATED_CATEGORIES:
        category_root = static_root / category
        if not category_root.is_dir():
            continue
        for path in sorted(category_root.rglob("*.svg")):
            if not path.is_file():
                continue
            relative = path.relative_to(static_root).as_posix()
            inventory[relative] = sha256_file(path)
    return inventory


def _publication_changes(
    existing: dict[str, str], incoming: dict[str, str]
) -> tuple[dict[str, Any], dict[str, int]]:
    added = [
        {"path": path, "sha256": incoming[path]}
        for path in sorted(set(incoming) - set(existing))
    ]
    removed = [
        {"path": path, "sha256": existing[path]}
        for path in sorted(set(existing) - set(incoming))
    ]
    changed = [
        {
            "path": path,
            "previousSha256": existing[path],
            "incomingSha256": incoming[path],
        }
        for path in sorted(set(existing) & set(incoming))
        if existing[path] != incoming[path]
    ]
    unchanged_count = sum(
        1
        for path in set(existing) & set(incoming)
        if existing[path] == incoming[path]
    )
    summary = {
        "addedAssetCount": len(added),
        "removedAssetCount": len(removed),
        "changedAssetCount": len(changed),
        "unchangedAssetCount": unchanged_count,
    }
    return {
        "summary": summary,
        "added": added,
        "removed": removed,
        "changed": changed,
    }, summary


def _backup_destination(backup_base: Path, *, symbol_sha256: str, created_at: datetime) -> Path:
    stem = f"{created_at.strftime('%Y%m%d-%H%M%S')}--{symbol_sha256[:12]}"
    candidate = backup_base / stem
    suffix = 1
    while candidate.exists():
        candidate = backup_base / f"{stem}-{suffix:02d}"
        suffix += 1
    return candidate


def _stage_removed_symbol_backup(
    *,
    static_root: Path,
    staging_root: Path,
    removed: list[dict[str, str]],
    symbol_artifact: dict[str, Any],
    created_at: datetime,
) -> Path:
    staged_backup = staging_root / "removed-symbol-backup"
    removed_root = staged_backup / "removed"
    for row in removed:
        relative = row["path"]
        source = static_root.joinpath(*_portable_member(relative).parts)
        if not source.is_file():
            raise ValueError(f"Published symbol disappeared before backup: {relative}")
        if sha256_file(source) != row["sha256"]:
            raise ValueError(f"Published symbol changed before backup: {relative}")
        destination = removed_root.joinpath(*_portable_member(relative).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    manifest = {
        "format": REMOVED_SYMBOL_BACKUP_FORMAT,
        "formatVersion": REMOVED_SYMBOL_BACKUP_VERSION,
        "createdAt": created_at.isoformat(timespec="seconds"),
        "incomingSymbolArtifact": {
            "name": symbol_artifact["name"],
            "sha256": symbol_artifact["sha256"],
        },
        "summary": {"removedAssetCount": len(removed)},
        "removed": removed,
    }
    staged_backup.mkdir(parents=True, exist_ok=True)
    (staged_backup / "backup-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return staged_backup


def _remove_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _resolve_compression_report(
    record: dict[str, Any],
    *,
    project_root: Path,
    report_root: Path,
) -> Path:
    candidates: list[Path] = []
    portable = record.get("path")
    if isinstance(portable, str):
        candidates.append(project_root / Path(portable))
    name = record.get("name")
    if isinstance(name, str):
        candidates.append(report_root / name)
    for candidate in candidates:
        if candidate.is_file() and sha256_file(candidate) == record.get("sha256"):
            return candidate
    raise ValueError("Could not resolve SHA-bound compression report")


def _verify_compressed_work_tree(
    manifest: dict[str, Any],
    *,
    compressed_root: Path,
    compression_report: Path,
) -> None:
    canonical_map = manifest["processing"]["duplicateDetection"]["canonicalByArchivePath"]
    canonical_paths = set(canonical_map.values())
    actual = {
        path.relative_to(compressed_root).as_posix()
        for path in compressed_root.rglob("*.svg")
        if path.is_file()
    }
    if actual != canonical_paths:
        raise ValueError(
            "Compressed symbol work tree does not contain exactly the manifest canonical set"
        )

    try:
        with compression_report.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except OSError as exc:
        raise ValueError(
            f"Could not load compression report {compression_report}: {exc}"
        ) from exc
    expected_hashes: dict[str, str] = {}
    for row in rows:
        if row.get("profile") != "balanced":
            continue
        relative = row.get("file")
        digest = row.get("output_sha256")
        if not isinstance(relative, str) or relative not in canonical_paths:
            raise ValueError(f"Compression report contains unexpected balanced asset: {relative}")
        if relative in expected_hashes:
            raise ValueError(f"Compression report repeats balanced asset: {relative}")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError(f"Compression report has invalid output SHA-256 for {relative}")
        expected_hashes[relative] = digest
    if set(expected_hashes) != canonical_paths:
        raise ValueError("Compression report hashes do not cover exactly the canonical asset set")

    for relative, expected in expected_hashes.items():
        path = compressed_root.joinpath(*_portable_member(relative).parts)
        actual_sha = sha256_file(path)
        if actual_sha != expected:
            raise ValueError(
                f"Compressed SVG SHA-256 does not match version-7 report for {relative}"
            )


def publish_symbols(
    *,
    army_snapshot: Path,
    build_manifest_path: Path,
    work_root: Path,
    reports_base: Path,
    static_root: Path,
    project_root: Path,
    backup_base: Path | None = None,
) -> PublicationResult:
    """Publish one verified version-7 compressed build transactionally."""
    manifest = load_symbol_manifest(build_manifest_path)
    if manifest.get("formatVersion") != SYMBOL_BUILD_COMPRESSION_VERSION:
        raise ValueError(
            "Publication requires passed "
            f"version-{SYMBOL_BUILD_COMPRESSION_VERSION} compression state"
        )
    processing = manifest.get("processing", {})
    if processing.get("compression", {}).get("status") != "passed":
        raise ValueError("Publication requires passed compression state")

    army_artifact = manifest["snapshot"]["armyArtifact"]
    if army_snapshot.name != army_artifact["name"]:
        raise ValueError(
            "Pinned Army snapshot name does not match symbol manifest: "
            f"{army_snapshot.name} != {army_artifact['name']}"
        )
    if sha256_file(army_snapshot) != army_artifact["sha256"]:
        raise ValueError("Pinned Army snapshot SHA-256 does not match symbol manifest")

    compressed_root = work_root / "compressed"
    if not compressed_root.is_dir():
        raise ValueError(f"Compressed symbol work tree is missing: {compressed_root}")
    snapshot_index = _load_snapshot_index(army_snapshot)

    symbol_artifact = manifest["snapshot"]["symbolArtifact"]
    report_root = reports_base / (
        f"{Path(symbol_artifact['name']).stem}--{symbol_artifact['sha256'][:12]}"
    )
    report_destination = report_root / "publication-map.json"
    compression_record = processing["compression"].get("report")
    if not isinstance(compression_record, dict):
        raise ValueError("Compression state is missing its report identity")
    compression_report = _resolve_compression_report(
        compression_record,
        project_root=project_root,
        report_root=report_root,
    )
    _verify_compressed_work_tree(
        manifest,
        compressed_root=compressed_root,
        compression_report=compression_report,
    )

    static_root.parent.mkdir(parents=True, exist_ok=True)
    static_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".symbol-publication-", dir=static_root.parent))
    staging_static = staging / "static"
    backup_root = staging / "backup"
    backup_root.mkdir()
    try:
        report_document, summary = _build_publication(
            manifest=manifest,
            snapshot_index=snapshot_index,
            compressed_root=compressed_root,
            staging_static=staging_static,
        )
        previous_inventory = _published_symbol_inventory(static_root)
        incoming_inventory = _published_symbol_inventory(staging_static)
        changes, change_summary = _publication_changes(previous_inventory, incoming_inventory)
        report_document["previousPublicationComparison"] = changes

        created_at = datetime.now(UTC)
        removed_backup: Path | None = None
        staged_removed_backup: Path | None = None
        removed = changes["removed"]
        if removed:
            if backup_base is None:
                backup_base = reports_base / "removed-backups"
            removed_backup = _backup_destination(
                backup_base,
                symbol_sha256=symbol_artifact["sha256"],
                created_at=created_at,
            )
            staged_removed_backup = _stage_removed_symbol_backup(
                static_root=static_root,
                staging_root=staging,
                removed=removed,
                symbol_artifact=symbol_artifact,
                created_at=created_at,
            )
            try:
                backup_path = removed_backup.relative_to(project_root).as_posix()
            except ValueError:
                backup_path = str(removed_backup)
            report_document["previousPublicationComparison"]["removedBackup"] = {
                "path": backup_path,
                "manifest": "backup-manifest.json",
            }

        staged_report = staging / "publication-map.json"
        staged_report.write_text(
            json.dumps(report_document, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        destinations = [
            *(static_root / category for category in GENERATED_CATEGORIES),
            static_root / ARMY_MAP,
            static_root / SYMBOL_MAP,
        ]
        staged_paths = [
            *(staging_static / category for category in GENERATED_CATEGORIES),
            staging_static / ARMY_MAP,
            staging_static / SYMBOL_MAP,
        ]
        report_root.mkdir(parents=True, exist_ok=True)
        destinations.append(report_destination)
        staged_paths.append(staged_report)
        if removed_backup is not None and staged_removed_backup is not None:
            destinations.append(removed_backup)
            staged_paths.append(staged_removed_backup)

        backups = {
            destination: backup_root / str(index)
            for index, destination in enumerate(destinations)
        }
        backed_up: list[Path] = []
        installed: list[Path] = []
        try:
            for destination in destinations:
                if destination.exists():
                    destination.replace(backups[destination])
                    backed_up.append(destination)

            for destination, source in zip(destinations, staged_paths, strict=True):
                destination.parent.mkdir(parents=True, exist_ok=True)
                source.replace(destination)
                installed.append(destination)

            updated = add_publication(
                manifest,
                summary=summary,
                mapping_report=report_destination,
                army_map=static_root / ARMY_MAP,
                unit_map=static_root / SYMBOL_MAP,
                project_root=project_root,
            )
            write_symbol_manifest(updated, build_manifest_path)
        except Exception:
            for destination in reversed(installed):
                _remove_path(destination)
            for destination in reversed(backed_up):
                backup = backups[destination]
                if backup.exists():
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    backup.replace(destination)
            raise

        return PublicationResult(
            static_root=static_root,
            mapping_report=report_destination,
            army_map=static_root / ARMY_MAP,
            unit_map=static_root / SYMBOL_MAP,
            summary=summary,
            changes=change_summary,
            removed_backup=removed_backup,
            status="passed",
        )
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="Pinned raw Army snapshot ZIP")
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument(
        "--build-manifest",
        type=Path,
        help="Generated symbol build manifest (default: data/manifests/army-symbol-build.json)",
    )
    parser.add_argument(
        "--static",
        type=Path,
        default=Path("src/infinity_db/web/static"),
        help="Application static root",
    )
    args = parser.parse_args(argv)

    build_manifest = args.build_manifest or (
        args.data_root / "manifests" / "army-symbol-build.json"
    )
    try:
        manifest = load_symbol_manifest(build_manifest)
        symbol_artifact = manifest["snapshot"]["symbolArtifact"]
        work_root = args.data_root / "work" / "symbols" / (
            f"{Path(symbol_artifact['name']).stem}--{symbol_artifact['sha256'][:12]}"
        )
        result = publish_symbols(
            army_snapshot=args.snapshot,
            build_manifest_path=build_manifest,
            work_root=work_root,
            reports_base=args.data_root / "reports" / "symbols",
            static_root=args.static,
            project_root=Path.cwd(),
            backup_base=args.data_root / "backups" / "symbols",
        )
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(
        "Published symbols -> "
        f"{result.summary['publishedAssetCount']} canonical SVGs | "
        f"{result.summary['unitMappingCount']} unit mappings | "
        f"{result.summary['factionMappingCount']} faction mappings | "
        f"{result.summary['staticMappingCount']} static mappings"
    )
    print(
        "Publication changes -> "
        f"+{result.changes['addedAssetCount']} added | "
        f"~{result.changes['changedAssetCount']} changed | "
        f"-{result.changes['removedAssetCount']} removed"
    )
    if result.removed_backup is not None:
        print(f"Removed symbol backup -> {result.removed_backup}")
    print(f"Publication root -> {result.static_root}")
    print(f"Publication mapping -> {result.mapping_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
