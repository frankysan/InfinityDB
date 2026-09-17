"""Download the primary unit symbols referenced by an Army snapshot into a timestamped ZIP."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
import zipfile
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from infinity_db.snapshot_provenance import write_snapshot_manifest

try:
    from tools.path_sanitization import sanitize_filename
    from tools.snapshot_archive import create_timestamped_archive
except ImportError:  # pragma: no cover - direct script execution fallback
    from path_sanitization import sanitize_filename
    from snapshot_archive import create_timestamped_archive

ASSET_HOST = "assets.corvusbelli.net"
ASSET_PATH = "/army/img/logo/units/"
ASSET_BASE_URL = f"https://{ASSET_HOST}{ASSET_PATH}"
SVG_NAME = re.compile(r"[a-z0-9-]+\.svg$")


def primary_logos(armies: Iterable[dict]) -> set[str]:
    """Return one deterministic profile-logo URL for every referenced unit ID."""
    by_unit: dict[int, str] = {}
    for army in armies:
        for unit in army.get("units", []):
            unit_id = unit.get("id")
            if not isinstance(unit_id, int) or unit_id in by_unit:
                continue
            logo = next(
                (
                    profile["logo"]
                    for group in unit.get("profileGroups", [])
                    for profile in group.get("profiles", [])
                    if isinstance(profile.get("logo"), str)
                ),
                None,
            )
            if logo is not None:
                by_unit[unit_id] = logo
    return set(by_unit.values())


def primary_symbol_slugs(armies: Iterable[dict]) -> dict[str, str]:
    """Map each source unit slug to its primary profile-logo filename stem."""
    by_unit: dict[int, tuple[str, str]] = {}
    for army in armies:
        for unit in army.get("units", []):
            unit_id = unit.get("id")
            slug = unit.get("slug")
            if not isinstance(unit_id, int) or not isinstance(slug, str) or unit_id in by_unit:
                continue
            logo = next(
                (
                    profile["logo"]
                    for group in unit.get("profileGroups", [])
                    for profile in group.get("profiles", [])
                    if isinstance(profile.get("logo"), str)
                ),
                None,
            )
            if logo is not None:
                by_unit[unit_id] = (slug, destination_name(logo).removesuffix(".svg"))
    return dict(sorted({slug: symbol for slug, symbol in by_unit.values()}.items()))


def write_manifest(armies: Iterable[dict], path: Path) -> None:
    """Write a browser module mapping database slugs to canonical icon slugs."""
    mappings = primary_symbol_slugs(armies)
    entries = ",\n".join(
        f"  [{json.dumps(slug)}, {json.dumps(symbol)}]" for slug, symbol in mappings.items()
    )
    path.write_text(
        "const unitSymbolSlugs = new Map([\n" + entries + "\n]);\n\n"
        "export function unitSymbolSlug(unitSlug) {\n"
        "  return unitSymbolSlugs.get(unitSlug);\n"
        "}\n",
        encoding="utf-8",
        newline="\n",
    )


def destination_name(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != ASSET_HOST:
        raise ValueError(f"Unsupported symbol host: {url}")
    if not parsed.path.startswith(ASSET_PATH):
        raise ValueError(f"Unsupported symbol path: {url}")

    tail = url.removeprefix(f"https://{ASSET_HOST}{ASSET_PATH}")
    tail = tail.split("#", 1)[0]
    if ".svg" in tail.lower():
        stem = tail[: tail.lower().rfind(".svg")]
        name = f"{stem}.svg"
    else:
        name = Path(parsed.path).name

    if not SVG_NAME.fullmatch(name):
        name = sanitize_filename(name)
    return name


def load_armies(path: Path) -> list[dict]:
    """Load Army documents from either a legacy master list or a raw API ZIP."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            armies = []
            for name in sorted(archive.namelist()):
                if not name.lower().endswith(".json"):
                    continue
                data = json.loads(archive.read(name))
                if isinstance(data, dict) and isinstance(data.get("units"), list):
                    armies.append(data)
            return armies
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("master list must be an object keyed by Army source filename")
    return [army for army in data.values() if isinstance(army, dict)]


def _write_bytes(path: Path, body: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(body)
    temporary.replace(path)


def archive_symbols(
    files: list[Path],
    destination: Path,
    *,
    root: Path,
    now: datetime | None = None,
) -> Path:
    """Store exactly one symbol download as a timestamped ZIP snapshot."""
    return create_timestamped_archive(
        files,
        destination,
        prefix="SYMBOLS",
        root=root,
        now=now,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Raw Army ZIP or legacy master-list JSON")
    parser.add_argument(
        "destination",
        nargs="?",
        type=Path,
        default=Path("data/raw/symbols"),
        help="Directory used to store timestamped symbol ZIP snapshots",
    )
    parser.add_argument("--manifest", type=Path, help="Write a browser symbol-slug map")
    parser.add_argument(
        "--manifest-dir",
        type=Path,
        default=Path("data/manifests/snapshots"),
        help="Generated snapshot manifest directory (default: data/manifests/snapshots)",
    )
    parser.add_argument(
        "--delay", type=float, default=0.2, help="Seconds to wait between downloads (default: 0.2)"
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.delay < 0:
        raise ValueError("--delay must not be negative")
    armies = load_armies(args.source)
    if args.manifest:
        write_manifest(armies, args.manifest)
    urls = sorted(primary_logos(armies))
    print(f"Primary symbols: {len(urls)}")
    if args.dry_run:
        print(f"Would download: {len(urls)}")
        return 0

    args.destination.mkdir(parents=True, exist_ok=True)
    archive: Path | None = None
    snapshot_manifest: Path | None = None
    try:
        with tempfile.TemporaryDirectory(
            prefix="infinity-symbols-", dir=args.destination
        ) as staging:
            staging_path = Path(staging)
            files: list[Path] = []
            for index, url in enumerate(urls, start=1):
                name = destination_name(url)
                with urlopen(url, timeout=30) as response:
                    body = response.read()
                if b"<svg" not in body[:1024]:
                    raise ValueError(f"Expected an SVG response: {url}")
                path = staging_path / name
                _write_bytes(path, body)
                files.append(path)
                print(f"[{index}/{len(urls)}] {name}")
                if index < len(urls) and args.delay:
                    time.sleep(args.delay)
            acquired_at = datetime.now().astimezone()
            archive = archive_symbols(
                files, args.destination, root=staging_path, now=acquired_at
            )
            snapshot_manifest = write_snapshot_manifest(
                archive,
                args.manifest_dir,
                snapshot_type="symbols",
                acquired_at=acquired_at,
                source_url=ASSET_BASE_URL,
                document_count=len(files),
                project_root=Path.cwd(),
                input_artifact=args.source,
            )
    except (OSError, ValueError) as exc:
        if snapshot_manifest is not None:
            snapshot_manifest.unlink(missing_ok=True)
        if archive is not None:
            archive.unlink(missing_ok=True)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Downloaded {len(files)} symbols -> {archive}")
    print(f"Snapshot provenance -> {snapshot_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
