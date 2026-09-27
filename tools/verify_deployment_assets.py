#!/usr/bin/env python3
"""Verify that deployment symbols match one completed promoted symbol build."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from infinity_db.deployment_provenance import (
    DeploymentProvenanceError,
    validate_database_symbol_provenance,
)
from infinity_db.snapshot_provenance import sha256_file
from infinity_db.symbol_manifest import (
    SYMBOL_BUILD_VERSION,
    SymbolManifestError,
    load_symbol_manifest,
)

try:
    from tools.asset_validation import AssetSetValidation, AssetValidationError, validate_asset_set
except ImportError:  # pragma: no cover - direct script execution fallback
    from asset_validation import AssetSetValidation, AssetValidationError, validate_asset_set

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "manifests" / "army-symbol-build.json"
DEFAULT_STATIC_ROOT = PROJECT_ROOT / "src" / "infinity_db" / "web" / "static"
DEFAULT_DATABASE = PROJECT_ROOT / "data" / "generated" / "infinity.db"
DEFAULT_PUBLICATION_MANIFEST = PROJECT_ROOT / "data" / "manifests" / "symbol-publication.json"


class DeploymentAssetError(ValueError):
    """Raised when local deployment symbols are not one complete promoted publication."""


def _portable_project_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise DeploymentAssetError(
            f"Deployment asset path is outside the project root: {path}"
        ) from exc


def _require_bound_artifact(
    publication: dict[str, Any],
    field: str,
    expected: Path,
    *,
    project_root: Path,
) -> None:
    record = publication.get(field)
    if not isinstance(record, dict):
        raise DeploymentAssetError(f"Published symbol manifest is missing {field}")

    expected_relative = _portable_project_path(expected, project_root)
    if record.get("path") != expected_relative:
        raise DeploymentAssetError(
            f"Published symbol manifest {field} path is {record.get('path')!r}; "
            f"expected {expected_relative!r}"
        )
    if record.get("name") != expected.name:
        raise DeploymentAssetError(
            f"Published symbol manifest {field} name is {record.get('name')!r}; "
            f"expected {expected.name!r}"
        )
    if not expected.is_file():
        raise DeploymentAssetError(f"Published symbol artifact is missing: {expected}")

    actual_digest = sha256_file(expected)
    if record.get("sha256") != actual_digest:
        raise DeploymentAssetError(
            f"Published symbol manifest {field} SHA-256 does not match {expected_relative}"
        )



def verify_deployment_assets(
    manifest_path: Path = DEFAULT_MANIFEST,
    static_root: Path = DEFAULT_STATIC_ROOT,
    *,
    project_root: Path = PROJECT_ROOT,
    database_path: Path | None = None,
    publication_manifest_path: Path | None = None,
) -> AssetSetValidation:
    """Validate local symbols against the terminal v8 build manifest and publication inventory."""

    try:
        manifest = load_symbol_manifest(manifest_path)
    except (OSError, SymbolManifestError) as exc:
        raise DeploymentAssetError(
            f"Could not load promoted symbol manifest {manifest_path}: {exc}"
        ) from exc

    if manifest.get("formatVersion") != SYMBOL_BUILD_VERSION:
        raise DeploymentAssetError(
            "Deployment requires a terminal published symbol manifest "
            f"(version {SYMBOL_BUILD_VERSION})"
        )

    processing = manifest.get("processing")
    publication = processing.get("publication") if isinstance(processing, dict) else None
    if not isinstance(publication, dict) or publication.get("status") != "passed":
        raise DeploymentAssetError("Deployment requires a passed symbol publication stage")

    publication_manifest_path = (
        publication_manifest_path
        or project_root / "data" / "manifests" / "symbol-publication.json"
    )
    _require_bound_artifact(
        publication,
        "publicationManifest",
        publication_manifest_path,
        project_root=project_root,
    )

    validation = validate_asset_set(
        static_root, publication_manifest=publication_manifest_path
    )
    if not validation.complete:
        details: list[str] = [validation.state]
        if validation.missing:
            details.append(f"missing {len(validation.missing)}")
        if validation.browser_missing:
            details.append(f"browser-missing {len(validation.browser_missing)}")
        if validation.unexpected:
            details.append(f"unexpected {len(validation.unexpected)}")
        if validation.invalid:
            details.append(f"invalid {len(validation.invalid)}")
        raise DeploymentAssetError(
            "Published symbol set does not satisfy its inventory/browser contract ("
            + ", ".join(details)
            + ")"
        )

    validate_database_symbol_provenance(
        database_path or project_root / "data" / "generated" / "infinity.db", manifest
    )

    return validation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Terminal symbol build manifest (default: data/manifests/army-symbol-build.json)",
    )
    parser.add_argument(
        "--static-root",
        type=Path,
        default=DEFAULT_STATIC_ROOT,
        help="Published browser static root (default: repository web/static directory)",
    )
    parser.add_argument(
        "--database", type=Path, default=DEFAULT_DATABASE, help="Runtime infinity.db to bind"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        validation = verify_deployment_assets(
            args.manifest, args.static_root, database_path=args.database
        )
    except (DeploymentAssetError, DeploymentProvenanceError, AssetValidationError) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(
        "Deployment symbols verified: "
        f"{validation.present_count}/{validation.expected_count} published SVGs; "
        f"{validation.browser_present_count}/{validation.browser_expected_count} "
        "browser-referenced; manifest-bound publication v8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
