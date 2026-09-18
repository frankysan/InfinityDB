#!/usr/bin/env python3
"""Manually download one raw Infinity Army JSON snapshot from Corvus Belli's API.

This is deliberately a standalone script. It is not registered with
``infinity-db`` or imported by the build pipeline, so network requests occur
only when this script is explicitly run.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import tempfile
import zipfile
from collections import Counter
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, NamedTuple
from urllib.request import Request, urlopen

from infinity_army_data.merge import decode_document
from infinity_army_data.metadata import decode_metadata
from infinity_db.snapshot_provenance import write_snapshot_manifest

try:
    from tools.snapshot_archive import create_timestamped_archive
except ImportError:  # pragma: no cover - direct script execution fallback
    from snapshot_archive import create_timestamped_archive

API_BASE_URL = "https://api.corvusbelli.com/army"
API_ORIGIN = "https://infinityuniverse.com"
DEFAULT_TIMEOUT = 30
API_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:155.0) "
    "Gecko/20100101 Firefox/155.0"
)
_SLUG_PART = re.compile(r"[^a-z0-9]+")


class ApiDownloadError(ValueError):
    """The Army API returned data that cannot be saved as an input snapshot."""


class ArmySnapshotResult(NamedTuple):
    """Identity and observed source revisions for one published Army snapshot."""

    archive: Path
    manifest: Path
    acquired_at: datetime
    language: str
    source_url: str
    document_count: int
    source_revisions: dict[str, int]


def _request(url: str) -> Request:
    return Request(
        url,
        headers={
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "DNT": "1",
            "Origin": API_ORIGIN,
            "Referer": f"{API_ORIGIN}/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "Sec-GPC": "1",
            "TE": "trailers",
            "User-Agent": API_USER_AGENT,
        },
    )


def _get_bytes(
    url: str,
    *,
    opener: Callable[..., Any] = urlopen,
    timeout: int = DEFAULT_TIMEOUT,
) -> bytes:
    try:
        with opener(_request(url), timeout=timeout) as response:
            return response.read()
    except OSError as exc:
        raise ApiDownloadError(f"Could not download {url}: {exc}") from exc


def _write_bytes(path: Path, body: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(body)
    temporary.replace(path)


def _filename(faction: dict[str, Any]) -> str:
    faction_id = faction.get("id")
    if type(faction_id) is not int:
        raise ApiDownloadError("metadata.factions entries need integer IDs")
    slug = faction.get("slug") or faction.get("name") or "army"
    if not isinstance(slug, str):
        raise ApiDownloadError(f"metadata faction {faction_id} has an invalid slug")
    normalized_slug = _SLUG_PART.sub("-", slug.casefold()).strip("-") or "army"
    return f"{faction_id}-{normalized_slug}.json"


def _sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _verify_stable_downloads(
    downloads: list[tuple[Path, str, bytes]],
    *,
    opener: Callable[..., Any],
    timeout: int,
) -> None:
    changed: list[str] = []
    for path, url, first_body in downloads:
        second_body = _get_bytes(url, opener=opener, timeout=timeout)
        if second_body == first_body:
            continue
        changed.append(f"{path.name} ({_sha256(first_body)} -> {_sha256(second_body)})")

    if changed:
        raise ApiDownloadError(
            "Army API responses changed during acquisition; refusing to create a torn "
            "snapshot. Changed endpoint(s): " + "; ".join(changed)
        )


def _source_revision_counts(files: list[Path]) -> dict[str, int]:
    revisions: Counter[str] = Counter()
    for path in files:
        if path.name == "metadata.json":
            continue
        document = decode_document(path.read_bytes(), path.name)
        revisions[str(document.get("version"))] += 1
    return dict(sorted(revisions.items()))


def snapshot_source_revision_counts(archive: Path) -> dict[str, int]:
    """Read per-document Army source revision counts from one immutable ZIP snapshot."""
    if not archive.is_file() or not zipfile.is_zipfile(archive):
        raise ApiDownloadError(f"Army snapshot must be a ZIP archive: {archive}")
    revisions: Counter[str] = Counter()
    with zipfile.ZipFile(archive) as source:
        names = [
            name
            for name in source.namelist()
            if not name.endswith("/") and name.lower().endswith(".json")
        ]
        if "metadata.json" not in names:
            raise ApiDownloadError("Army snapshot is missing metadata.json")
        for name in sorted(names):
            if name == "metadata.json":
                continue
            try:
                document = decode_document(source.read(name), name)
            except ValueError as exc:
                raise ApiDownloadError(f"Invalid Army source document {name}: {exc}") from exc
            revisions[str(document.get("version"))] += 1
    return dict(sorted(revisions.items()))


def download_snapshot(
    destination: Path,
    *,
    language: str = "en",
    api_base_url: str = API_BASE_URL,
    opener: Callable[..., Any] = urlopen,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[Path]:
    """Download one stable metadata + Army-list snapshot using two API passes."""
    if not re.fullmatch(r"[a-z]{2}(?:-[A-Z]{2})?", language):
        raise ApiDownloadError("language must be an API language code such as 'en'")

    destination.mkdir(parents=True, exist_ok=True)
    metadata_url = f"{api_base_url.rstrip('/')}/infinity/{language}/metadata"
    metadata_bytes = _get_bytes(metadata_url, opener=opener, timeout=timeout)
    try:
        metadata = decode_metadata(metadata_bytes, "metadata.json")["data"]
    except ValueError as exc:
        raise ApiDownloadError(f"Invalid metadata response: {exc}") from exc

    downloads: list[tuple[Path, str, bytes]] = [
        (destination / "metadata.json", metadata_url, metadata_bytes)
    ]
    seen_ids: set[int] = set()
    for faction in metadata["factions"]:
        if not isinstance(faction, dict):
            raise ApiDownloadError("metadata.factions entries must be objects")
        faction_id = faction.get("id")
        if type(faction_id) is not int:
            raise ApiDownloadError("metadata.factions entries need integer IDs")
        if faction_id in seen_ids:
            raise ApiDownloadError(f"metadata.factions has duplicate ID {faction_id}")
        seen_ids.add(faction_id)

        filename = _filename(faction)
        units_url = f"{api_base_url.rstrip('/')}/units/{language}/{faction_id}"
        units_bytes = _get_bytes(units_url, opener=opener, timeout=timeout)
        try:
            decode_document(units_bytes, filename)
        except ValueError as exc:
            raise ApiDownloadError(
                f"Invalid unit-list response for faction {faction_id}: {exc}"
            ) from exc
        downloads.append((destination / filename, units_url, units_bytes))

    _verify_stable_downloads(downloads, opener=opener, timeout=timeout)

    for path, _, body in downloads:
        _write_bytes(path, body)
    return [path for path, _, _ in downloads]


def archive_snapshot(
    files: list[Path],
    destination: Path,
    *,
    now: datetime | None = None,
) -> Path:
    """Store exactly one downloaded Army snapshot in a timestamped ZIP file."""
    return create_timestamped_archive(files, destination, prefix="JSON", now=now)


def acquire_army_snapshot(
    destination: Path,
    manifest_directory: Path,
    *,
    language: str = "en",
    api_base_url: str = API_BASE_URL,
    project_root: Path | None = None,
    opener: Callable[..., Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    acquired_at: datetime | None = None,
) -> ArmySnapshotResult:
    """Download, verify, archive, and describe one immutable Army snapshot."""
    project_root = project_root or Path.cwd()
    opener = opener or urlopen
    destination.mkdir(parents=True, exist_ok=True)
    archive: Path | None = None
    manifest: Path | None = None
    try:
        with tempfile.TemporaryDirectory(prefix="infinity-army-", dir=destination) as staging:
            files = download_snapshot(
                Path(staging),
                language=language,
                api_base_url=api_base_url,
                opener=opener,
                timeout=timeout,
            )
            revisions = _source_revision_counts(files)
            timestamp = acquired_at or datetime.now().astimezone()
            archive = archive_snapshot(files, destination, now=timestamp)
            manifest = write_snapshot_manifest(
                archive,
                manifest_directory,
                snapshot_type="army",
                acquired_at=timestamp,
                source_url=api_base_url,
                document_count=len(files),
                project_root=project_root,
                language=language,
            )
    except Exception:
        if manifest is not None:
            manifest.unlink(missing_ok=True)
        if archive is not None:
            archive.unlink(missing_ok=True)
        raise

    return ArmySnapshotResult(
        archive=archive,
        manifest=manifest,
        acquired_at=timestamp,
        language=language,
        source_url=api_base_url,
        document_count=len(files),
        source_revisions=revisions,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", nargs="?", type=Path, default=Path("data/raw"))
    parser.add_argument("--language", default="en", help="Army API language code (default: en)")
    parser.add_argument(
        "--manifest-dir",
        type=Path,
        default=Path("data/manifests/snapshots"),
        help="Generated snapshot manifest directory (default: data/manifests/snapshots)",
    )
    args = parser.parse_args(argv)
    try:
        result = acquire_army_snapshot(
            args.destination,
            args.manifest_dir,
            language=args.language,
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        f"Downloaded {result.document_count - 1} army lists and metadata -> "
        f"{result.archive}"
    )
    print(
        "Army source revisions -> "
        + ", ".join(
            f"{version}: {count}" for version, count in result.source_revisions.items()
        )
    )
    print(f"Snapshot provenance -> {result.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
