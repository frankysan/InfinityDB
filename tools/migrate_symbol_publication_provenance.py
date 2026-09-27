#!/usr/bin/env python3
"""Promote Army snapshot identity from local symbol build state into the tracked publication."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from infinity_db.snapshot_provenance import sha256_file
from infinity_db.symbol_manifest import (
    SYMBOL_BUILD_VERSION,
    SymbolManifestError,
    artifact_record,
    load_symbol_manifest,
    validate_symbol_manifest,
    write_symbol_manifest,
)

try:
    from tools.asset_validation import AssetValidationError, publication_manifest_summary
except ImportError:  # pragma: no cover - direct script execution fallback
    from asset_validation import (  # type: ignore[no-redef]
        AssetValidationError,
        publication_manifest_summary,
    )

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUILD_MANIFEST = PROJECT_ROOT / "data" / "manifests" / "army-symbol-build.json"
DEFAULT_PUBLICATION_MANIFEST = PROJECT_ROOT / "data" / "manifests" / "symbol-publication.json"
_SHA256_RE = re.compile(r"[0-9a-f]{64}")


class PublicationMigrationError(ValueError):
    """Raised when legacy publication provenance cannot be promoted safely."""


def _source_record(build_manifest: dict) -> dict[str, str]:
    snapshot = build_manifest.get("snapshot")
    artifact = snapshot.get("armyArtifact") if isinstance(snapshot, dict) else None
    name = artifact.get("name") if isinstance(artifact, dict) else None
    digest = artifact.get("sha256") if isinstance(artifact, dict) else None
    if not isinstance(name, str) or not name:
        raise PublicationMigrationError("Symbol build manifest has no Army artifact name")
    if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
        raise PublicationMigrationError("Symbol build manifest has no valid Army artifact SHA-256")
    return {"name": name, "sha256": digest}


def _load_publication(path: Path) -> dict:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicationMigrationError(
            f"Could not read tracked symbol publication {path}: {exc}"
        ) from exc
    if not isinstance(document, dict):
        raise PublicationMigrationError("Tracked symbol publication must be a JSON object")
    return document


def migrate_publication_provenance(
    build_manifest_path: Path = DEFAULT_BUILD_MANIFEST,
    publication_manifest_path: Path = DEFAULT_PUBLICATION_MANIFEST,
    *,
    project_root: Path = PROJECT_ROOT,
) -> bool:
    """Add compact Army provenance to a tracked publication and refresh local build binding."""

    try:
        build_manifest = load_symbol_manifest(build_manifest_path)
    except (OSError, SymbolManifestError) as exc:
        raise PublicationMigrationError(
            f"Could not load terminal symbol build manifest {build_manifest_path}: {exc}"
        ) from exc
    if build_manifest.get("formatVersion") != SYMBOL_BUILD_VERSION:
        raise PublicationMigrationError(
            f"Migration requires terminal symbol build version {SYMBOL_BUILD_VERSION}"
        )

    processing = build_manifest.get("processing")
    publication = processing.get("publication") if isinstance(processing, dict) else None
    if not isinstance(publication, dict) or publication.get("status") != "passed":
        raise PublicationMigrationError("Migration requires a passed symbol publication stage")

    try:
        canonical_summary = publication_manifest_summary(publication_manifest_path)
    except AssetValidationError as exc:
        raise PublicationMigrationError(str(exc)) from exc
    build_summary = publication.get("summary")
    if not isinstance(build_summary, dict):
        raise PublicationMigrationError("Symbol build manifest has no publication summary")
    for field in ("publishedAssetCount", "publishedBytes"):
        if build_summary.get(field) != canonical_summary[field]:
            raise PublicationMigrationError(
                f"Symbol build publication summary.{field} does not match tracked publication"
            )

    bound = publication.get("publicationManifest")
    if isinstance(bound, dict):
        if bound.get("sha256") != sha256_file(publication_manifest_path):
            raise PublicationMigrationError(
                "Terminal symbol build manifest does not bind the current tracked publication"
            )

    source = _source_record(build_manifest)
    document = _load_publication(publication_manifest_path)
    existing = document.get("sourceSnapshot")
    if existing is not None:
        if existing == {"armyArtifact": source}:
            return False
        raise PublicationMigrationError(
            "Tracked symbol publication already contains different source snapshot provenance"
        )

    updated = dict(document)
    updated["sourceSnapshot"] = {"armyArtifact": source}
    payload = json.dumps(updated, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    temporary = publication_manifest_path.with_suffix(publication_manifest_path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8", newline="\n")
    temporary.replace(publication_manifest_path)

    # Keep ignored local build state internally consistent after the tracked file changes.
    rebound = json.loads(json.dumps(build_manifest))
    rebound["processing"]["publication"]["publicationManifest"] = artifact_record(
        publication_manifest_path, project_root=project_root
    )
    validate_symbol_manifest(rebound)
    write_symbol_manifest(rebound, build_manifest_path)
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--build-manifest", type=Path, default=DEFAULT_BUILD_MANIFEST
    )
    parser.add_argument(
        "--publication-manifest", type=Path, default=DEFAULT_PUBLICATION_MANIFEST
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        changed = migrate_publication_provenance(
            args.build_manifest,
            args.publication_manifest,
            project_root=PROJECT_ROOT,
        )
    except PublicationMigrationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        "Tracked symbol publication provenance "
        + ("updated." if changed else "already current.")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
