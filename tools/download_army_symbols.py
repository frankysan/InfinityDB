"""Discover and resolve every authoritative symbol referenced by one Army snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
import time
import zipfile
from collections.abc import Callable
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import urlparse
from urllib.request import urlopen
from xml.etree import ElementTree

from infinity_db.snapshot_provenance import (
    load_snapshot_manifest,
    portable_project_path,
    sha256_file,
    write_snapshot_manifest,
)
from infinity_db.symbol_manifest import (
    build_symbol_manifest,
    load_symbol_manifest,
    write_symbol_manifest,
)

try:
    from tools.download_army_json import ArmySnapshotResult, resolve_army_snapshot
    from tools.path_sanitization import sanitize_filename
    from tools.snapshot_archive import create_timestamped_archive
except ImportError:  # pragma: no cover - direct script execution fallback
    from download_army_json import ArmySnapshotResult, resolve_army_snapshot
    from path_sanitization import sanitize_filename
    from snapshot_archive import create_timestamped_archive

ASSET_HOST = "assets.corvusbelli.net"
ASSET_ROOT_PATH = "/army/img/"
ASSET_ROOT_URL = f"https://{ASSET_HOST}{ASSET_ROOT_PATH}"
DEFAULT_STATIC_CONFIG = Path("config/symbols/static-symbols.json")
DEFAULT_BUILD_MANIFEST = Path("data/manifests/army-symbol-build.json")
DEFAULT_OVERRIDE_ROOT = Path("image_overrides")
SVG_NAME = re.compile(r"[a-z0-9-]+\.svg$")
ARMY_FILE = re.compile(r"^(?P<id>\d+)-(?P<slug>.+)\.json$", re.IGNORECASE)
STATIC_IDENTIFIER = re.compile(r"[a-z0-9-]+")


class SourceDocument(NamedTuple):
    name: str
    data: dict[str, Any]


class Discovery(NamedTuple):
    references: list[dict[str, Any]]
    authoritative_urls: set[str]
    audit: dict[str, int]
    source_document_count: int


class SymbolSnapshotResult(NamedTuple):
    """Identity and discovery state for one published raw symbol snapshot."""

    archive: Path
    snapshot_manifest: Path
    build_manifest: Path
    asset_count: int
    discovery: Discovery


class SymbolCache(NamedTuple):
    """Validated prior immutable symbol snapshot used as an acquisition cache."""

    archive: Path
    assets: dict[str, dict[str, Any]]


class ResolutionPlan(NamedTuple):
    """Stable local override keys plus diagnostics for one discovery set."""

    override_paths: dict[str, str]
    collisions: dict[str, list[str]]


def destination_name(url: str) -> str:
    """Return one deterministic, Windows-safe SVG filename for an asset URL."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != ASSET_HOST:
        raise ValueError(f"Unsupported symbol host: {url}")
    if not parsed.path.startswith(ASSET_ROOT_PATH):
        raise ValueError(f"Unsupported symbol path: {url}")

    tail = url.removeprefix(f"https://{ASSET_HOST}{ASSET_ROOT_PATH}")
    tail = tail.rsplit("/", 1)[-1].split("#", 1)[0]
    if ".svg" in tail.lower():
        stem = tail[: tail.lower().rfind(".svg")]
        name = f"{stem}.svg"
    else:
        name = Path(parsed.path).name

    if not SVG_NAME.fullmatch(name):
        name = sanitize_filename(name)
    return name


def load_source_documents(path: Path) -> list[SourceDocument]:
    """Load raw Army JSON documents from a ZIP/directory or a legacy master JSON."""
    documents: list[SourceDocument] = []
    if path.is_file() and zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for name in sorted(archive.namelist()):
                if name.endswith("/") or not name.lower().endswith(".json"):
                    continue
                data = json.loads(archive.read(name))
                if isinstance(data, dict):
                    documents.append(SourceDocument(Path(name).name, data))
    elif path.is_dir():
        for file in sorted(path.glob("*.json")):
            data = json.loads(file.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                documents.append(SourceDocument(file.name, data))
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("master list must be an object keyed by Army source filename")
        for name, value in sorted(data.items()):
            if isinstance(value, dict):
                filename = name if str(name).lower().endswith(".json") else f"{name}.json"
                documents.append(SourceDocument(Path(filename).name, value))
    if not documents:
        raise ValueError("No JSON source documents were found")
    return documents


def load_static_symbols(path: Path) -> list[dict[str, str]]:
    """Load and validate the maintained static-symbol declaration file."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not load static symbols {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError("static symbols must be a JSON object")
    if set(document) != {"schema_version", "base_url", "assets"}:
        raise ValueError("static symbols must contain schema_version, base_url, and assets")
    if document["schema_version"] != 2:
        raise ValueError("static symbols schema_version must be 2")
    base_url = document["base_url"]
    if not isinstance(base_url, str) or not base_url.startswith("https://"):
        raise ValueError("static symbols base_url must be an HTTPS URL")
    assets = document["assets"]
    if not isinstance(assets, list):
        raise ValueError("static symbols assets must be an array")

    result: list[dict[str, str]] = []
    keys: set[str] = set()
    declarations: set[tuple[str, str]] = set()
    for index, asset in enumerate(assets):
        context = f"static symbols assets[{index}]"
        if not isinstance(asset, dict) or set(asset) != {"key", "category", "filename", "label"}:
            raise ValueError(f"{context} must contain key, category, filename, and label")
        row: dict[str, str] = {}
        for field in ("key", "category", "filename", "label"):
            value = asset[field]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{context}.{field} must be a non-empty string")
            row[field] = value
        for field in ("key", "category"):
            if not STATIC_IDENTIFIER.fullmatch(row[field]):
                raise ValueError(f"{context}.{field} must use lowercase slug syntax")
        if row["key"] in keys:
            raise ValueError(f"{context}.key is duplicated: {row['key']}")
        keys.add(row["key"])
        declaration = (row["category"], row["filename"])
        if declaration in declarations:
            raise ValueError(f"{context} duplicates {row['category']}/{row['filename']}")
        declarations.add(declaration)
        if (
            Path(row["filename"]).name != row["filename"]
            or not row["filename"].lower().endswith(".svg")
        ):
            raise ValueError(f"{context}.filename must be one SVG filename")
        row["url"] = base_url.rstrip("/") + "/" + row["filename"]
        destination_name(row["url"])
        result.append(row)
    return result


def discover_symbols(
    documents: list[SourceDocument],
    *,
    static_symbols: list[dict[str, str]],
    static_source: str,
) -> Discovery:
    """Discover authoritative Army/static symbols and audit all raw SVG references."""
    semantic: list[dict[str, Any]] = []
    resume: list[dict[str, Any]] = []
    known_locations: set[tuple[str, str]] = set()

    for document in documents:
        if document.name == "metadata.json":
            factions = document.data.get("factions", [])
            if not isinstance(factions, list):
                raise ValueError("metadata.json factions must be an array")
            for index, faction in enumerate(factions):
                if not isinstance(faction, dict):
                    continue
                logo = faction.get("logo")
                if not isinstance(logo, str):
                    continue
                path = f"$.factions[{index}].logo"
                reference: dict[str, Any] = {
                    "kind": "faction",
                    "authoritative": True,
                    "sourceDocument": document.name,
                    "jsonPath": path,
                    "assetUrl": logo,
                }
                if type(faction.get("id")) is int:
                    reference["factionId"] = faction["id"]
                if isinstance(faction.get("slug"), str) and faction["slug"].strip():
                    reference["factionSlug"] = faction["slug"]
                semantic.append(reference)
                known_locations.add((document.name, path))
            continue

        units = document.data.get("units")
        if not isinstance(units, list):
            continue
        army_match = ARMY_FILE.match(document.name)
        army_id = int(army_match.group("id")) if army_match else None
        army_slug = army_match.group("slug") if army_match else None
        for unit_index, unit in enumerate(units):
            if not isinstance(unit, dict):
                continue
            unit_id = unit.get("id") if type(unit.get("id")) is int else None
            unit_slug = unit.get("slug") if isinstance(unit.get("slug"), str) else None
            groups = unit.get("profileGroups", [])
            if isinstance(groups, list):
                for group_index, group in enumerate(groups):
                    if not isinstance(group, dict):
                        continue
                    profiles = group.get("profiles", [])
                    if not isinstance(profiles, list):
                        continue
                    for profile_index, profile in enumerate(profiles):
                        if not isinstance(profile, dict):
                            continue
                        logo = profile.get("logo")
                        if not isinstance(logo, str):
                            continue
                        path = (
                            f"$.units[{unit_index}].profileGroups[{group_index}]"
                            f".profiles[{profile_index}].logo"
                        )
                        reference = {
                            "kind": "unit-profile",
                            "authoritative": True,
                            "sourceDocument": document.name,
                            "jsonPath": path,
                            "assetUrl": logo,
                        }
                        if army_id is not None:
                            reference["armyId"] = army_id
                        if army_slug:
                            reference["armySlug"] = army_slug
                        if unit_id is not None:
                            reference["unitId"] = unit_id
                        if unit_slug:
                            reference["unitSlug"] = unit_slug
                        profile_name = profile.get("name") or profile.get("isc")
                        if isinstance(profile_name, str) and profile_name.strip():
                            reference["profileName"] = profile_name
                        semantic.append(reference)
                        known_locations.add((document.name, path))

        resume_rows = document.data.get("resume", [])
        if isinstance(resume_rows, list):
            for resume_index, row in enumerate(resume_rows):
                if not isinstance(row, dict) or not isinstance(row.get("logo"), str):
                    continue
                path = f"$.resume[{resume_index}].logo"
                reference = {
                    "kind": "resume-audit",
                    "authoritative": False,
                    "sourceDocument": document.name,
                    "jsonPath": path,
                    "assetUrl": row["logo"],
                }
                if army_id is not None:
                    reference["armyId"] = army_id
                if army_slug:
                    reference["armySlug"] = army_slug
                if type(row.get("id")) is int:
                    reference["unitId"] = row["id"]
                if isinstance(row.get("slug"), str) and row["slug"].strip():
                    reference["unitSlug"] = row["slug"]
                resume.append(reference)
                known_locations.add((document.name, path))

    recursive: list[tuple[str, str, str]] = []
    for document in documents:
        recursive.extend(
            (document.name, json_path, value)
            for json_path, value in _string_values(document.data)
            if ".svg" in value.casefold()
        )
    unknown = [
        item for item in recursive if (item[0], item[1]) not in known_locations
    ]
    if unknown:
        details = "\n".join(f"  {name} {path}: {url}" for name, path, url in unknown[:20])
        extra = "" if len(unknown) <= 20 else f"\n  ... and {len(unknown) - 20} more"
        raise ValueError(
            "Unknown SVG-bearing Army source fields were found:\n" + details + extra
        )

    static_refs: list[dict[str, Any]] = []
    for index, asset in enumerate(static_symbols):
        static_refs.append(
            {
                "kind": "static",
                "authoritative": True,
                "sourceDocument": static_source,
                "jsonPath": f"$.assets[{index}]",
                "assetUrl": asset["url"],
                "staticKey": asset["key"],
                "staticCategory": asset["category"],
                "label": asset["label"],
            }
        )

    for reference in [*semantic, *resume, *static_refs]:
        destination_name(reference["assetUrl"])

    authoritative_urls = {
        reference["assetUrl"] for reference in [*semantic, *static_refs]
    }
    unit_refs = [row for row in semantic if row["kind"] == "unit-profile"]
    faction_refs = [row for row in semantic if row["kind"] == "faction"]
    semantic_urls = {reference["assetUrl"] for reference in semantic}
    audit = {
        "unitProfileReferenceCount": len(unit_refs),
        "uniqueUnitUrlCount": len({row["assetUrl"] for row in unit_refs}),
        "factionReferenceCount": len(faction_refs),
        "uniqueFactionUrlCount": len({row["assetUrl"] for row in faction_refs}),
        "semanticReferenceCount": len(semantic),
        "uniqueSemanticUrlCount": len(semantic_urls),
        "resumeReferenceCount": len(resume),
        "uniqueResumeUrlCount": len({row["assetUrl"] for row in resume}),
        "staticReferenceCount": len(static_refs),
        "recursiveReferenceCount": len(recursive),
        "uniqueRecursiveUrlCount": len({url for _, _, url in recursive}),
        "uniqueDownloadedUrlCount": len(authoritative_urls),
        "unknownReferenceCount": 0,
    }
    return Discovery(
        references=[*semantic, *resume, *static_refs],
        authoritative_urls=authoritative_urls,
        audit=audit,
        source_document_count=len(documents),
    )


def _string_values(value: Any, path: str = "$"):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _string_values(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _string_values(child, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value


def archive_paths(discovery: Discovery) -> dict[str, str]:
    """Assign deterministic raw-archive paths without conflating consumer references."""
    categories: dict[str, set[str]] = {url: set() for url in discovery.authoritative_urls}
    for reference in discovery.references:
        url = reference["assetUrl"]
        if url not in categories or not reference["authoritative"]:
            continue
        kind = reference["kind"]
        if kind == "unit-profile":
            categories[url].add("units")
        elif kind == "faction":
            categories[url].add("factions")
        elif kind == "static":
            categories[url].add(f"static/{reference['staticCategory']}")

    candidates: dict[str, str] = {}
    for url in sorted(discovery.authoritative_urls):
        category = sorted(categories[url])[0] if categories[url] else "unclassified"
        candidates[url] = f"{category}/{destination_name(url)}"

    by_candidate: dict[str, list[str]] = {}
    for url, candidate in candidates.items():
        by_candidate.setdefault(candidate.casefold(), []).append(url)
    for urls in by_candidate.values():
        if len(urls) < 2:
            continue
        for url in urls:
            path = Path(candidates[url])
            suffix = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
            candidates[url] = (path.parent / f"{path.stem}--{suffix}{path.suffix}").as_posix()
    return candidates


def override_resolution_plan(discovery: Discovery) -> ResolutionPlan:
    """Return stable URL-derived override paths and any filename collisions."""
    categories: dict[str, set[str]] = {url: set() for url in discovery.authoritative_urls}
    for reference in discovery.references:
        url = reference["assetUrl"]
        if url not in categories or not reference["authoritative"]:
            continue
        kind = reference["kind"]
        if kind == "unit-profile":
            categories[url].add("units")
        elif kind == "faction":
            categories[url].add("factions")
        elif kind == "static":
            categories[url].add(reference["staticCategory"])

    candidates: dict[str, str] = {}
    for url in sorted(discovery.authoritative_urls):
        category = sorted(categories[url])[0] if categories[url] else "unclassified"
        candidates[url] = f"{category}/{destination_name(url)}"

    collisions: dict[str, list[str]] = {}
    by_candidate: dict[str, list[str]] = {}
    for url, candidate in candidates.items():
        by_candidate.setdefault(candidate.casefold(), []).append(url)
    for key, urls in sorted(by_candidate.items()):
        if len(urls) < 2:
            continue
        collisions[key] = sorted(urls)
        for url in urls:
            path = Path(candidates[url])
            suffix = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
            candidates[url] = (path.parent / f"{path.stem}--{suffix}{path.suffix}").as_posix()
    return ResolutionPlan(candidates, collisions)


def _svg_bytes(body: bytes, *, context: str) -> bytes:
    """Validate raw bytes as one SVG document and return them unchanged."""
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError as exc:
        raise ValueError(f"Invalid SVG from {context}: {exc}") from exc
    if root.tag.rsplit("}", 1)[-1].casefold() != "svg":
        raise ValueError(f"Invalid SVG from {context}: root element is not <svg>")
    return body


def _override_files(root: Path) -> dict[str, Path]:
    """Index local SVG overrides by case-insensitive portable relative path."""
    if not root.exists():
        return {}
    if not root.is_dir():
        raise ValueError(f"Image override root is not a directory: {root}")

    result: dict[str, Path] = {}
    for path in sorted(
        (candidate for candidate in root.rglob("*") if candidate.is_file()),
        key=lambda candidate: candidate.relative_to(root).as_posix().casefold(),
    ):
        if path.suffix.casefold() != ".svg":
            continue
        relative = path.relative_to(root).as_posix()
        key = relative.casefold()
        if key in result:
            first = result[key].relative_to(root).as_posix()
            raise ValueError(
                "Case-insensitive image override collision: "
                f"{first} and {relative}"
            )
        result[key] = path
    return result


def _cache_archive_path(
    artifact: dict[str, Any],
    *,
    destination: Path,
    project_root: Path,
) -> Path | None:
    if isinstance(artifact.get("path"), str):
        candidate = project_root / Path(artifact["path"])
        if candidate.is_file():
            return candidate
    candidate = destination / artifact["name"]
    if candidate.is_file():
        return candidate
    return None


def load_symbol_cache(
    build_manifest_path: Path,
    *,
    destination: Path,
    manifest_directory: Path,
    project_root: Path,
) -> SymbolCache | None:
    """Load the prior symbol snapshot as a validated exact-URL cache when available."""
    if not build_manifest_path.is_file():
        return None

    manifest = load_symbol_manifest(build_manifest_path)
    artifact = manifest["snapshot"]["symbolArtifact"]
    archive = _cache_archive_path(
        artifact,
        destination=destination,
        project_root=project_root,
    )
    if archive is None:
        return None
    if archive.name != artifact["name"]:
        raise ValueError(
            "Cached symbol artifact name does not match its resolved archive: "
            f"{artifact['name']} != {archive.name}"
        )
    actual = sha256_file(archive)
    if actual != artifact["sha256"]:
        raise ValueError(
            "Cached symbol archive SHA-256 mismatch: "
            f"expected {artifact['sha256']}, got {actual}"
        )

    provenance_path = manifest_directory / f"{archive.stem}.json"
    if not provenance_path.is_file():
        raise ValueError(f"Cached symbol snapshot provenance is missing: {provenance_path}")
    provenance = load_snapshot_manifest(provenance_path, archive=archive)
    if provenance["snapshot"]["type"] != "symbols":
        raise ValueError(f"Cached snapshot provenance is not a symbol snapshot: {provenance_path}")

    assets = {row["url"]: row for row in manifest["assets"]}
    if provenance["snapshot"]["archive"]["name"] != archive.name:
        raise ValueError(
            "Cached symbol snapshot provenance names a different archive: "
            f"{provenance['snapshot']['archive']['name']} != {archive.name}"
        )
    if provenance["snapshot"]["documentCount"] != len(assets):
        raise ValueError(
            "Cached symbol snapshot document count does not match its build manifest: "
            f"{provenance['snapshot']['documentCount']} != {len(assets)}"
        )
    return SymbolCache(archive=archive, assets=assets)


def _cached_svg(cache: SymbolCache, archive: zipfile.ZipFile, url: str) -> bytes | None:
    asset = cache.assets.get(url)
    if asset is None:
        return None
    archive_path = asset["archivePath"]
    try:
        body = archive.read(archive_path)
    except KeyError as exc:
        raise ValueError(
            f"Cached symbol archive is missing manifest member {archive_path!r}: {cache.archive}"
        ) from exc
    actual = hashlib.sha256(body).hexdigest()
    if actual != asset["sha256"]:
        raise ValueError(
            "Cached symbol member SHA-256 mismatch for "
            f"{url}: expected {asset['sha256']}, got {actual}"
        )
    return _svg_bytes(body, context=f"cache {cache.archive.name}#{archive_path}")


def _write_bytes(path: Path, body: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_bytes(body)
    temporary.replace(path)


def archive_symbols(
    files: list[Path],
    destination: Path,
    *,
    root: Path,
    now: datetime | None = None,
) -> Path:
    """Store exactly one complete symbol acquisition as a timestamped ZIP snapshot."""
    return create_timestamped_archive(
        files,
        destination,
        prefix="SYMBOLS",
        root=root,
        now=now,
    )


def discover_symbol_source(
    source: Path,
    *,
    static_symbols_path: Path = DEFAULT_STATIC_CONFIG,
    project_root: Path | None = None,
) -> Discovery:
    """Discover every authoritative symbol for one explicit Army source artifact."""
    if not source.is_file():
        raise ValueError("source must be an immutable Army ZIP or JSON file")
    project_root = project_root or Path.cwd()
    documents = load_source_documents(source)
    static_symbols = load_static_symbols(static_symbols_path)
    static_source = (
        portable_project_path(static_symbols_path, project_root=project_root)
        or static_symbols_path.name
    )
    return discover_symbols(
        documents,
        static_symbols=static_symbols,
        static_source=static_source,
    )


def acquire_symbol_snapshot(
    source: Path,
    destination: Path,
    manifest_directory: Path,
    build_manifest_path: Path,
    *,
    static_symbols_path: Path = DEFAULT_STATIC_CONFIG,
    delay: float = 0.2,
    project_root: Path | None = None,
    discovery: Discovery | None = None,
    opener: Callable[..., Any] | None = None,
    sleeper: Callable[[float], Any] | None = None,
    acquired_at: datetime | None = None,
    progress: Callable[[str], Any] | None = None,
    army_snapshot: ArmySnapshotResult | None = None,
    army_snapshot_manifest: Path | None = None,
    override_root: Path = DEFAULT_OVERRIDE_ROOT,
    refresh_symbols: bool = False,
) -> SymbolSnapshotResult:
    """Resolve and publish one complete raw symbol snapshot for a pinned Army source."""
    if delay < 0:
        raise ValueError("delay must not be negative")
    project_root = project_root or Path.cwd()
    discovery = discovery or discover_symbol_source(
        source,
        static_symbols_path=static_symbols_path,
        project_root=project_root,
    )
    opener = opener or urlopen
    sleeper = sleeper or time.sleep
    progress = progress or (lambda _message: None)
    army_snapshot = army_snapshot or resolve_army_snapshot(
        source,
        manifest_directory=manifest_directory,
        manifest=army_snapshot_manifest,
    )
    if army_snapshot.archive.resolve() != source.resolve():
        raise ValueError(
            "Resolved Army snapshot does not match the symbol acquisition source: "
            f"{army_snapshot.archive} != {source}"
        )
    if discovery.source_document_count != army_snapshot.document_count:
        raise ValueError(
            "Symbol discovery source-document count does not match Army provenance: "
            f"{discovery.source_document_count} != {army_snapshot.document_count}"
        )

    resolution_plan = override_resolution_plan(discovery)
    overrides = _override_files(override_root)
    for candidate, urls in resolution_plan.collisions.items():
        progress(
            "Override filename collision: "
            f"{candidate} represents {len(urls)} URLs; use URL-specific names:"
        )
        for url in urls:
            progress(f"  {url} -> {resolution_plan.override_paths[url]}")

    cache = None
    if not refresh_symbols:
        cache = load_symbol_cache(
            build_manifest_path,
            destination=destination,
            manifest_directory=manifest_directory,
            project_root=project_root,
        )

    destination.mkdir(parents=True, exist_ok=True)
    archive: Path | None = None
    snapshot_manifest: Path | None = None
    try:
        paths = archive_paths(discovery)
        cache_context = zipfile.ZipFile(cache.archive) if cache is not None else nullcontext(None)
        with cache_context as cache_archive, tempfile.TemporaryDirectory(
            prefix="infinity-symbols-", dir=destination
        ) as staging:
            staging_path = Path(staging)
            files: list[Path] = []
            assets: list[dict[str, str]] = []
            used_overrides: set[str] = set()
            source_counts = {"override": 0, "cache": 0, "network": 0}
            urls = sorted(discovery.authoritative_urls)
            for index, url in enumerate(urls, start=1):
                relative = paths[url]
                override_relative = resolution_plan.override_paths[url]
                override_key = override_relative.casefold()
                override = overrides.get(override_key)
                if override is not None:
                    body = _svg_bytes(
                        override.read_bytes(),
                        context=f"override {override}",
                    )
                    source_method = "override"
                    used_overrides.add(override_key)
                else:
                    cached = None
                    if cache is not None:
                        assert isinstance(cache_archive, zipfile.ZipFile)
                        cached = _cached_svg(cache, cache_archive, url)
                    if cached is not None:
                        body = cached
                        source_method = "cache"
                    else:
                        with opener(url, timeout=30) as response:
                            body = response.read()
                        body = _svg_bytes(body, context=f"network {url}")
                        source_method = "network"
                        if index < len(urls) and delay:
                            sleeper(delay)

                path = staging_path / Path(relative)
                _write_bytes(path, body)
                files.append(path)
                source_counts[source_method] += 1
                assets.append(
                    {
                        "url": url,
                        "sourceFilename": Path(urlparse(url).path).name
                        or destination_name(url),
                        "archivePath": relative,
                        "sha256": hashlib.sha256(body).hexdigest(),
                        "sourceMethod": source_method,
                    }
                )
                progress(f"[{index}/{len(urls)}] {relative} [{source_method}]")

            unused_overrides = sorted(
                path.relative_to(override_root).as_posix()
                for key, path in overrides.items()
                if key not in used_overrides
            )
            progress(
                "Symbol sources: "
                f"override {source_counts['override']} | "
                f"cache {source_counts['cache']} | "
                f"network {source_counts['network']}"
            )
            if unused_overrides:
                progress(f"Unused image overrides ({len(unused_overrides)}):")
                for relative in unused_overrides:
                    progress(f"  {relative}")

            timestamp = acquired_at or datetime.now().astimezone()
            archive = archive_symbols(
                files, destination, root=staging_path, now=timestamp
            )
            snapshot_manifest = write_snapshot_manifest(
                archive,
                manifest_directory,
                snapshot_type="symbols",
                acquired_at=timestamp,
                source_url=ASSET_ROOT_URL,
                document_count=len(files),
                project_root=project_root,
                input_artifact=source,
            )
            build_manifest = build_symbol_manifest(
                army_artifact=source,
                symbol_artifact=archive,
                acquired_at=timestamp,
                army_acquired_at=army_snapshot.acquired_at,
                army_language=army_snapshot.language,
                army_source_url=army_snapshot.source_url,
                source_document_count=army_snapshot.document_count,
                source_revisions=army_snapshot.source_revisions,
                assets=assets,
                references=discovery.references,
                audit=discovery.audit,
                project_root=project_root,
            )
            write_symbol_manifest(build_manifest, build_manifest_path)
    except Exception:
        if snapshot_manifest is not None:
            snapshot_manifest.unlink(missing_ok=True)
        if archive is not None:
            archive.unlink(missing_ok=True)
        raise

    return SymbolSnapshotResult(
        archive=archive,
        snapshot_manifest=snapshot_manifest,
        build_manifest=build_manifest_path,
        asset_count=len(files),
        discovery=discovery,
    )


def print_discovery_summary(discovery: Discovery) -> None:
    """Print concise source-discovery counts for one symbol acquisition."""
    print(
        "Unit/profile logos: "
        f"{discovery.audit['unitProfileReferenceCount']} references / "
        f"{discovery.audit['uniqueUnitUrlCount']} unique URLs"
    )
    print(
        "Faction logos: "
        f"{discovery.audit['factionReferenceCount']} references / "
        f"{discovery.audit['uniqueFactionUrlCount']} unique URLs"
    )
    print(
        "Resume audit: "
        f"{discovery.audit['resumeReferenceCount']} references / "
        f"{discovery.audit['uniqueResumeUrlCount']} unique URLs"
    )
    print(
        "Recursive SVG audit: "
        f"{discovery.audit['recursiveReferenceCount']} references / "
        f"{discovery.audit['uniqueRecursiveUrlCount']} unique URLs / "
        f"{discovery.audit['unknownReferenceCount']} unknown locations"
    )
    print(f"Static declarations: {discovery.audit['staticReferenceCount']}")
    print(f"Unique assets to download: {len(discovery.authoritative_urls)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        type=Path,
        help="Raw Army ZIP; directory/master inputs are discovery-only with --dry-run",
    )
    parser.add_argument(
        "destination",
        nargs="?",
        type=Path,
        default=Path("data/raw/symbols"),
        help="Directory used to store timestamped symbol ZIP snapshots",
    )
    parser.add_argument(
        "--static-symbols",
        type=Path,
        default=DEFAULT_STATIC_CONFIG,
        help="Maintained static-symbol declarations",
    )
    parser.add_argument(
        "--build-manifest",
        type=Path,
        default=DEFAULT_BUILD_MANIFEST,
        help="Generated acquisition/build manifest",
    )
    parser.add_argument(
        "--image-overrides",
        type=Path,
        default=DEFAULT_OVERRIDE_ROOT,
        help="Local SVG override root (default: image_overrides)",
    )
    parser.add_argument(
        "--refresh-symbols",
        action="store_true",
        help="Bypass the prior immutable symbol cache; local overrides still take precedence",
    )
    parser.add_argument(
        "--manifest-dir",
        type=Path,
        default=Path("data/manifests/snapshots"),
        help="Generated snapshot manifest directory (default: data/manifests/snapshots)",
    )
    parser.add_argument(
        "--snapshot-manifest",
        type=Path,
        help="Army snapshot provenance manifest (defaults to <manifest-dir>/<source>.json)",
    )
    parser.add_argument(
        "--delay", type=float, default=0.2, help="Seconds to wait between downloads (default: 0.2)"
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.delay < 0:
        raise ValueError("--delay must not be negative")
    try:
        discovery = discover_symbol_source(
            args.source,
            static_symbols_path=args.static_symbols,
        )
        print_discovery_summary(discovery)
        if args.dry_run:
            return 0

        result = acquire_symbol_snapshot(
            args.source,
            args.destination,
            args.manifest_dir,
            args.build_manifest,
            static_symbols_path=args.static_symbols,
            delay=args.delay,
            discovery=discovery,
            progress=print,
            army_snapshot_manifest=args.snapshot_manifest,
            override_root=args.image_overrides,
            refresh_symbols=args.refresh_symbols,
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Resolved {result.asset_count} symbols -> {result.archive}")
    print(f"Snapshot provenance -> {result.snapshot_manifest}")
    print(f"Symbol build manifest -> {result.build_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
