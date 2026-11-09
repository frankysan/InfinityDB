"""Offline orchestration of the current runtime set before the P2 filename cutover."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from infinity_army_data.cli import discover_metadata, latest_snapshot

from .build_provenance import (
    FAMILIES,
    MANIFEST_FORMAT,
    build_record,
    build_set_id,
    canonical_bytes,
    file_sha256,
)
from .curated import load_curated_directory
from .database.publication import validate_database_pair
from .database_set import EMBEDDED_WEAPON_RUNTIME_FILES, validate_database_set
from .deployed_object_builder import build_deployed_objects
from .rules_database import export_rules_database
from .variant_usage import build_variant_usage_projection
from .variant_usage_reference import publication_from_candidate
from .weapon_profile_builder import build_publication

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def collect_build_manifest(root: Path, source: Path, metadata: Path | None) -> dict[str, Any]:
    """Declare a conservative maintained-input envelope, never absolute host paths."""
    if not source.is_file() or not zipfile.is_zipfile(source):
        raise ValueError("Complete runtime builds require an immutable local Army ZIP")
    if not (root / "pyproject.toml").is_file():
        raise ValueError("Complete runtime builds require the project source checkout")
    envelope = discover_metadata(source, metadata, required=True)
    assert envelope is not None
    code = sorted((root / "src").rglob("*.py"))
    maintained = [
        path for directory in (
            "config/catalogs", "config/identity", "config/validation", "config/symbols",
            "data/curated",
        ) for path in (root / directory).rglob("*.json") if path.name != "example.json"
    ]
    maintained.extend([
        root / "pyproject.toml", root / "data/manifests/symbol-publication.json",
        root / "src/infinity_db/web/static/restrictions-reference.json",
    ])
    # Match the repository's LF source-text policy even in an older Windows
    # worktree containing CRLF. Upstream archive/API metadata stay byte-exact.
    code_digests = {
        path.relative_to(root).as_posix(): hashlib.sha256(
            path.read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        for path in code
    }
    inputs = {path.relative_to(root).as_posix(): file_sha256(path) for path in maintained}
    manifest = {
        "format": MANIFEST_FORMAT, "formatVersion": 1, "families": list(FAMILIES),
        "builderRevision": hashlib.sha256(canonical_bytes(code_digests)).hexdigest(),
        "source": {
            "archiveName": source.name, "archiveSha256": file_sha256(source),
            "metadataName": envelope["sourceFile"],
            "metadataSha256": envelope["sourceSha256"],
        },
        "inputs": dict(sorted({**inputs, **code_digests}.items())),
    }
    build_set_id(manifest)
    return manifest


def _build_rules_and_publications(stage: Path, root: Path, manifest: dict[str, Any]) -> None:
    army, rules = stage / "infinity.db", stage / "rules.db"
    generation = validate_database_pair(army)
    if generation is None:
        raise ValueError("Complete builds require an Army export generation fingerprint")
    documents = load_curated_directory(root / "data/curated/rules")
    core = next(
        (path for path, doc in documents
         if doc["collection"]["id"] == "n5-core-v5.3"
         and doc["collection"]["status"] == "current"), None,
    )
    if core is None:
        raise ValueError("Current N5.3 core source required for deployed objects")
    objects = build_deployed_objects(
        army, core, root / "config/validation/deployed-object-delivery-reviews.json",
        root / "config/validation/deployed-object-candidate-reviews.json",
    )
    export_options = dict(
        restrictions_manifest=json.loads(
            (root / "config/validation/restrictions-source-chart.json").read_text(encoding="utf-8")
        ),
        deployed_objects=objects,
        build_provenance=build_record(manifest, "rules-n5", army_generation=generation),
    )
    # The source projection uses the temporary v10 Rules model. The final export
    # embeds its resolved facts without storing its own completed byte hash.
    export_rules_database(documents, rules, **export_options)
    variants = publication_from_candidate(build_variant_usage_projection(
        army, stage / "infinity.raw.db", rules, stage / "deployed-objects.json",
    ))
    export_rules_database(documents, rules, variant_usage=variants, **export_options)
    weapons = build_publication(
        army, rules, root / "data/curated/weapon-shared-effect-reviews.json",
    )
    chart = json.loads(
        (root / "src/infinity_db/web/static/restrictions-reference.json").read_text(
            encoding="utf-8"
        )
    )
    export_rules_database(
        documents, rules, variant_usage=variants, weapon_citations=weapons,
        restriction_chart=chart, army_database=army, **export_options,
    )


def build_database_set(
    args: argparse.Namespace,
    build_army: Callable[[argparse.Namespace, dict[str, Any]], int],
    *,
    root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Build/validate in disposable work files, then replace only selected outputs."""
    if args.no_verify:
        raise ValueError("Complete runtime builds cannot use --no-verify")
    root = root.resolve()
    source = (args.source if args.source is not None else latest_snapshot()).resolve()
    target = args.db_dir.resolve()
    manifest = collect_build_manifest(root, source, args.metadata)
    if target.exists() and not target.is_dir():
        raise ValueError("Runtime output must be a directory")
    protected = {source, *(root / name for name in manifest["inputs"])}
    if args.metadata is not None:
        protected.add(args.metadata.resolve())
    for name in EMBEDDED_WEAPON_RUNTIME_FILES:
        output = target / name
        if output.resolve() in protected or (output.exists() and not output.is_file()):
            raise ValueError(f"Runtime output would replace an input or non-file: {name}")

    work = root / "data/work/build"
    work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="runtime-", dir=work) as directory:
        stage = Path(directory)
        army_args = argparse.Namespace(**vars(args))
        army_args.source, army_args.output_dir = source, stage
        if build_army(army_args, build_record(manifest, "army")) != 0:
            raise ValueError("Army build failed before runtime publication")
        _build_rules_and_publications(stage, root, manifest)
        result = validate_database_set(stage)
        if result["buildProvenance"].get("buildSetId") != build_set_id(manifest):
            raise ValueError("Built runtime set does not match the selected build inputs")
        if collect_build_manifest(root, source, args.metadata) != manifest:
            raise ValueError(
                "Build inputs changed during generation; selected outputs were retained"
            )
        target.mkdir(parents=True, exist_ok=True)
        # Stop serving this directory before rebuilding. Individual replacements
        # are atomic; interruption leaves an invalid mixed set, recovered by rerun.
        for name in sorted(EMBEDDED_WEAPON_RUNTIME_FILES):
            os.replace(stage / name, target / name)
        for name in ("variant-usage.json", "weapon-profile-sources.json"):
            obsolete = target / name
            if obsolete.is_file() or obsolete.is_symlink():
                obsolete.unlink()
        return result
