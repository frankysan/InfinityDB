#!/usr/bin/env python3
"""Download, validate, and stage one private full-asset integration bundle."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:
    from tools.asset_validation import (
        PUBLISHED_ASSET_CATEGORIES,
        AssetSetValidation,
        validate_asset_set,
    )
except ModuleNotFoundError:  # Direct execution as tools/stage_full_asset_bundle.py.
    from asset_validation import (  # type: ignore[no-redef]
        PUBLISHED_ASSET_CATEGORIES,
        AssetSetValidation,
        validate_asset_set,
    )

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATIC_ROOT = REPO_ROOT / "src" / "infinity_db" / "web" / "static"
DEFAULT_URL_ENV = "FULL_ASSET_BUNDLE_URL"
DEFAULT_SHA256_ENV = "FULL_ASSET_BUNDLE_SHA256"
DEFAULT_MAX_DOWNLOAD_MIB = 128
DEFAULT_MAX_EXPANDED_MIB = 256
_SHA256 = re.compile(r"[0-9a-fA-F]{64}")


class AssetBundleError(ValueError):
    """Raised when the configured private full-asset bundle is unsafe or invalid."""


def normalize_sha256(value: str) -> str:
    """Return one validated lowercase SHA-256 digest."""
    digest = value.strip()
    if not _SHA256.fullmatch(digest):
        raise AssetBundleError("Full-asset bundle SHA-256 must be exactly 64 hexadecimal digits")
    return digest.lower()


def download_asset_bundle(
    url: str,
    expected_sha256: str,
    destination: Path,
    *,
    max_bytes: int = DEFAULT_MAX_DOWNLOAD_MIB * 1024 * 1024,
) -> Path:
    """Download one HTTPS bundle while enforcing a size limit and pinned digest."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise AssetBundleError("Full-asset bundle URL must use HTTPS")

    digest = normalize_sha256(expected_sha256)
    headers = {
        "Accept": "application/octet-stream",
        "User-Agent": "InfinityDB-full-asset-check",
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    hasher = hashlib.sha256()
    downloaded = 0
    try:
        with urlopen(Request(url, headers=headers), timeout=60) as response:  # noqa: S310
            final_url = response.geturl() if hasattr(response, "geturl") else url
            if urlparse(final_url).scheme != "https":
                raise AssetBundleError("Full-asset bundle redirected to a non-HTTPS URL")
            with destination.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    if downloaded > max_bytes:
                        raise AssetBundleError(
                            f"Full-asset bundle exceeds the {max_bytes // (1024 * 1024)} MiB limit"
                        )
                    hasher.update(chunk)
                    output.write(chunk)
    except AssetBundleError:
        destination.unlink(missing_ok=True)
        raise
    except HTTPError as exc:
        destination.unlink(missing_ok=True)
        raise AssetBundleError(
            f"Could not download full-asset bundle: HTTP {exc.code} {exc.reason}"
        ) from exc
    except URLError as exc:
        destination.unlink(missing_ok=True)
        raise AssetBundleError(
            f"Could not download full-asset bundle: {exc.reason}"
        ) from exc
    except OSError as exc:
        destination.unlink(missing_ok=True)
        raise AssetBundleError(f"Could not store full-asset bundle: {exc}") from exc

    actual = hasher.hexdigest()
    if actual != digest:
        destination.unlink(missing_ok=True)
        raise AssetBundleError("Full-asset bundle SHA-256 does not match configured digest")
    return destination


def _validated_members(
    archive: zipfile.ZipFile,
    *,
    max_expanded_bytes: int,
) -> tuple[tuple[zipfile.ZipInfo, PurePosixPath], ...]:
    categories = set(PUBLISHED_ASSET_CATEGORIES)
    members: list[tuple[zipfile.ZipInfo, PurePosixPath]] = []
    seen: set[str] = set()
    seen_casefold: set[str] = set()
    expanded = 0

    for info in archive.infolist():
        name = info.filename
        if "\\" in name:
            raise AssetBundleError(f"Bundle member uses a backslash path: {name!r}")
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise AssetBundleError(f"Bundle member escapes the asset root: {name!r}")
        if not relative.parts:
            continue
        if relative.parts[0] not in categories:
            raise AssetBundleError(
                f"Bundle member is outside armies/orders/units: {name!r}"
            )
        if info.is_dir():
            continue
        if len(relative.parts) < 2 or relative.suffix.lower() != ".svg":
            raise AssetBundleError(f"Bundle contains a non-SVG asset member: {name!r}")
        if info.flag_bits & 0x1:
            raise AssetBundleError(f"Bundle contains an encrypted member: {name!r}")

        mode = (info.external_attr >> 16) & 0xFFFF
        if mode and stat.S_ISLNK(mode):
            raise AssetBundleError(f"Bundle contains a symbolic link: {name!r}")

        normalized = relative.as_posix()
        folded = normalized.casefold()
        if normalized in seen:
            raise AssetBundleError(f"Bundle contains a duplicate member: {name!r}")
        if folded in seen_casefold:
            raise AssetBundleError(f"Bundle contains a case-colliding member: {name!r}")
        seen.add(normalized)
        seen_casefold.add(folded)

        expanded += info.file_size
        if expanded > max_expanded_bytes:
            raise AssetBundleError(
                "Full-asset bundle exceeds the expanded-size safety limit"
            )
        members.append((info, relative))

    if not members:
        raise AssetBundleError("Full-asset bundle contains no SVG assets")
    return tuple(members)


def _extract_bundle(archive_path: Path, staging_root: Path, *, max_expanded_bytes: int) -> None:
    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = _validated_members(archive, max_expanded_bytes=max_expanded_bytes)
            for info, relative in members:
                destination = staging_root.joinpath(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, destination.open("wb") as output:
                    shutil.copyfileobj(source, output)
    except zipfile.BadZipFile as exc:
        raise AssetBundleError("Full-asset bundle is not a valid ZIP archive") from exc
    except OSError as exc:
        raise AssetBundleError(f"Could not extract full-asset bundle: {exc}") from exc


def _validate_staging(staging_root: Path, static_root: Path) -> AssetSetValidation:
    for mapping_name in ("army-symbols.js", "unit-symbol-map.js"):
        source = static_root / mapping_name
        if not source.is_file():
            raise AssetBundleError(f"Published symbol mapping is missing: {source}")
        shutil.copy2(source, staging_root / mapping_name)

    validation = validate_asset_set(staging_root)
    if not validation.complete:
        detail = validation.state
        if validation.missing:
            detail += f", missing {len(validation.missing)}"
        if validation.invalid:
            detail += f", invalid {len(validation.invalid)}"
        raise AssetBundleError(f"Full-asset bundle does not satisfy published contract ({detail})")
    return validation


def _install_staging(staging_root: Path, static_root: Path, backup_root: Path) -> None:
    moved_existing: list[str] = []
    installed: list[str] = []
    try:
        for category in PUBLISHED_ASSET_CATEGORIES:
            staged = staging_root / category
            target = static_root / category
            backup = backup_root / category
            if target.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                os.replace(target, backup)
                moved_existing.append(category)
            os.replace(staged, target)
            installed.append(category)
    except OSError as exc:
        for category in reversed(installed):
            target = static_root / category
            if target.exists():
                shutil.rmtree(target)
        for category in reversed(moved_existing):
            backup = backup_root / category
            target = static_root / category
            if backup.exists():
                os.replace(backup, target)
        raise AssetBundleError(f"Could not install full-asset bundle: {exc}") from exc


def stage_asset_bundle(
    archive_path: Path,
    static_root: Path = DEFAULT_STATIC_ROOT,
    *,
    max_expanded_bytes: int = DEFAULT_MAX_EXPANDED_MIB * 1024 * 1024,
) -> AssetSetValidation:
    """Validate a ZIP bundle and replace the local published asset categories atomically."""
    static_root = static_root.resolve()
    static_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".full-assets-stage-", dir=static_root.parent) as stage:
        with tempfile.TemporaryDirectory(
            prefix=".full-assets-backup-", dir=static_root.parent
        ) as backup:
            staging_root = Path(stage)
            backup_root = Path(backup)
            _extract_bundle(
                archive_path,
                staging_root,
                max_expanded_bytes=max_expanded_bytes,
            )
            validation = _validate_staging(staging_root, static_root)
            _install_staging(staging_root, static_root, backup_root)
            return validation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--static-root",
        type=Path,
        default=DEFAULT_STATIC_ROOT,
        help="Published browser static root (default: repository web/static directory)",
    )
    parser.add_argument(
        "--url-env",
        default=DEFAULT_URL_ENV,
        help=(
            "Environment variable containing the private HTTPS bundle URL "
            f"(default: {DEFAULT_URL_ENV})"
        ),
    )
    parser.add_argument(
        "--sha256-env",
        default=DEFAULT_SHA256_ENV,
        help=(
            "Environment variable containing the pinned bundle SHA-256 "
            f"(default: {DEFAULT_SHA256_ENV})"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    url = os.environ.get(args.url_env, "").strip()
    digest = os.environ.get(args.sha256_env, "").strip()
    if not url:
        print(f"ERROR: environment variable {args.url_env} is not configured")
        return 2
    if not digest:
        print(f"ERROR: environment variable {args.sha256_env} is not configured")
        return 2

    try:
        with tempfile.TemporaryDirectory(prefix="infinitydb-full-assets-") as temporary:
            archive = Path(temporary) / "full-assets.zip"
            download_asset_bundle(url, digest, archive)
            validation = stage_asset_bundle(archive, args.static_root)
    except AssetBundleError as exc:
        print(f"ERROR: {exc}")
        return 1

    print(
        "Full-asset bundle staged: "
        f"{validation.present_count}/{validation.expected_count} required SVGs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
