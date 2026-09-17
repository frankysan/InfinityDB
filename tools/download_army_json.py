#!/usr/bin/env python3
"""Manually download one raw Infinity Army JSON snapshot from Corvus Belli's API.

This is deliberately a standalone script. It is not registered with
``infinity-db`` or imported by the build pipeline, so network requests occur
only when this script is explicitly run.
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from infinity_army_data.merge import decode_document
from infinity_army_data.metadata import decode_metadata

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


def download_snapshot(
    destination: Path,
    *,
    language: str = "en",
    api_base_url: str = API_BASE_URL,
    opener: Callable[..., Any] = urlopen,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[Path]:
    """Save metadata, then one raw unit-list JSON file for every metadata faction."""
    if not re.fullmatch(r"[a-z]{2}(?:-[A-Z]{2})?", language):
        raise ApiDownloadError("language must be an API language code such as 'en'")

    destination.mkdir(parents=True, exist_ok=True)
    metadata_url = f"{api_base_url.rstrip('/')}/infinity/{language}/metadata"
    metadata_bytes = _get_bytes(metadata_url, opener=opener, timeout=timeout)
    try:
        metadata = decode_metadata(metadata_bytes, "metadata.json")["data"]
    except ValueError as exc:
        raise ApiDownloadError(f"Invalid metadata response: {exc}") from exc
    _write_bytes(destination / "metadata.json", metadata_bytes)

    files = [destination / "metadata.json"]
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
        path = destination / filename
        _write_bytes(path, units_bytes)
        files.append(path)
    return files


def archive_snapshot(
    files: list[Path],
    destination: Path,
    *,
    now: datetime | None = None,
) -> Path:
    """Store exactly one downloaded Army snapshot in a timestamped ZIP file."""
    return create_timestamped_archive(files, destination, prefix="JSON", now=now)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", nargs="?", type=Path, default=Path("data/raw"))
    parser.add_argument("--language", default="en", help="Army API language code (default: en)")
    args = parser.parse_args(argv)
    try:
        args.destination.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="infinity-army-", dir=args.destination) as staging:
            files = download_snapshot(Path(staging), language=args.language)
            archive = archive_snapshot(files, args.destination)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Downloaded {len(files) - 1} army lists and metadata -> {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
