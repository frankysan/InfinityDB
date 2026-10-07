#!/usr/bin/env python3
"""Build a deterministic checksum-pinned bundle for the manual full-asset CI workflow."""

from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path

try:
    from tools.asset_validation import PUBLISHED_ASSET_CATEGORIES, validate_asset_set
    from tools.snapshot_archive import _archive_info
except ModuleNotFoundError:  # Direct execution as tools/build_full_asset_bundle.py.
    from asset_validation import (  # type: ignore[no-redef]
        PUBLISHED_ASSET_CATEGORIES,
        validate_asset_set,
    )
    from snapshot_archive import _archive_info  # type: ignore[no-redef]

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATIC_ROOT = REPO_ROOT / "src" / "infinity_db" / "web" / "static"
DEFAULT_PUBLICATION_MANIFEST = REPO_ROOT / "data" / "manifests" / "symbol-publication.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports" / "full-assets.zip"
_COMPRESSION = zipfile.ZIP_DEFLATED
_COMPRESSLEVEL = 6


class FullAssetBundleBuildError(ValueError):
    """Raised when the tracked publication cannot produce a valid external bundle."""


def _published_files(static_root: Path) -> list[Path]:
    files: list[Path] = []
    for category in PUBLISHED_ASSET_CATEGORIES:
        root = static_root / category
        if root.is_dir():
            files.extend(path for path in root.rglob("*.svg") if path.is_file())
    return sorted(files, key=lambda path: path.relative_to(static_root).as_posix())


def build_full_asset_bundle(
    destination: Path,
    *,
    static_root: Path = DEFAULT_STATIC_ROOT,
    publication_manifest: Path = DEFAULT_PUBLICATION_MANIFEST,
) -> tuple[Path, str, int]:
    """Build the exact validated publication as a deterministic ZIP and return its digest."""
    static_root = static_root.resolve()
    publication_manifest = publication_manifest.resolve()
    validation = validate_asset_set(static_root, publication_manifest=publication_manifest)
    if not validation.complete:
        detail = validation.state
        if validation.missing:
            detail += f", missing {len(validation.missing)}"
        if validation.unexpected:
            detail += f", unexpected {len(validation.unexpected)}"
        if validation.invalid:
            detail += f", invalid {len(validation.invalid)}"
        raise FullAssetBundleBuildError(
            f"Published asset set is not complete and valid ({detail})"
        )

    files = _published_files(static_root)
    if len(files) != validation.expected_count:
        raise FullAssetBundleBuildError(
            "Validated publication count does not match files selected for bundling"
        )

    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.unlink(missing_ok=True)
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=_COMPRESSION,
            compresslevel=_COMPRESSLEVEL,
        ) as archive:
            for path in files:
                relative = path.relative_to(static_root).as_posix()
                archive.writestr(
                    _archive_info(relative),
                    path.read_bytes(),
                    compress_type=_COMPRESSION,
                    compresslevel=_COMPRESSLEVEL,
                )
        temporary.replace(destination)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise FullAssetBundleBuildError(f"Could not build full-asset bundle: {exc}") from exc

    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    return destination, digest, len(files)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output ZIP path (default: reports/full-assets.zip)",
    )
    parser.add_argument(
        "--static-root",
        type=Path,
        default=DEFAULT_STATIC_ROOT,
        help="Published browser static root",
    )
    parser.add_argument(
        "--publication-manifest",
        type=Path,
        default=DEFAULT_PUBLICATION_MANIFEST,
        help="Tracked symbol publication manifest",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        archive, digest, count = build_full_asset_bundle(
            args.output,
            static_root=args.static_root,
            publication_manifest=args.publication_manifest,
        )
    except FullAssetBundleBuildError as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Full-asset bundle: {archive}")
    print(f"Published SVGs: {count}")
    print(f"SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
