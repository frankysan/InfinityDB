"""Offline construction and validated replacement of one complete runtime set."""

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

from .army_reference_storage import publish_army_reference_data
from .army_snapshot_source import verify_pinned_army_build_source
from .build_provenance import (
    FAMILIES,
    MANIFEST_FORMAT,
    build_input_fingerprints,
    build_record,
    build_set_id,
    canonical_bytes,
    file_sha256,
)
from .curated import load_curated_directory
from .database.normalized_source import verified_normalized_generation
from .database_set import (
    COMPLETE_RUNTIME_FILES,
    SEASON_DATABASE_SOURCES,
    season_shared_library_source,
    validate_database_set,
)
from .deployed_object_builder import build_deployed_objects
from .equipment_presentation_storage import publish_equipment_encodings
from .its_season_database import build_its_database
from .rules_database import export_rules_database
from .search_index_storage import publish_search_index
from .skill_classification_storage import publish_skill_classifications
from .symbol_path_storage import publish_symbol_paths
from .trait_wiki_references import load_trait_wiki_references
from .unit_filter_storage import publish_unit_filter_semantics
from .unit_history_storage import history_input_identity, history_inputs, publish_unit_history
from .unit_input_storage import publish_filter_contexts
from .variant_usage import build_variant_usage_from_normalized
from .variant_usage_reference import publication_from_candidate
from .weapon_ammunition_references import load_ammunition_reference_map
from .weapon_combined_saving_rolls import load_combined_saving_roll_map
from .weapon_profile_builder import build_publication
from .weapon_properties import load_weapon_properties

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def collect_build_manifest(
    root: Path, source: Path, metadata: Path | None, *,
    snapshot_manifest: Path | None = None, history_root: Path | None = None,
) -> dict[str, Any]:
    """Declare a conservative maintained-input envelope, never absolute host paths."""
    if not source.is_file() or not zipfile.is_zipfile(source):
        raise ValueError("Complete runtime builds require an immutable local Army ZIP")
    if not (root / "pyproject.toml").is_file():
        raise ValueError("Complete runtime builds require the project source checkout")
    if snapshot_manifest is not None:
        if metadata is not None:
            raise ValueError("--snapshot-manifest cannot combine with --metadata")
        verify_pinned_army_build_source(source, snapshot_manifest)
    envelope = discover_metadata(source, metadata, required=True)
    assert envelope is not None
    inputs = build_input_fingerprints(root, unit_history=history_root is not None)
    code_digests = {name: digest for name, digest in inputs.items()
                    if name.startswith("src/") and name.endswith(".py")}
    manifest = {
        "format": MANIFEST_FORMAT, "formatVersion": 1, "families": list(FAMILIES),
        "builderRevision": hashlib.sha256(canonical_bytes(code_digests)).hexdigest(),
        "source": {
            "archiveName": source.name, "archiveSha256": file_sha256(source),
            "metadataName": envelope["sourceFile"],
            "metadataSha256": envelope["sourceSha256"],
        },
        "inputs": inputs,
    }
    if history_root is not None:
        manifest["history"] = history_input_identity(history_root)
    build_set_id(manifest)
    return manifest


def _build_general_profiles(stage: Path, root: Path) -> None:
    """Compose against core Rules before later publications bind the final Army bytes."""
    from .general_profile_storage import publish_general_profiles

    rules = stage / "general-profile-rules.db"
    export_rules_database(load_curated_directory(root / "data/curated/rules"), rules,
                          finalize=False)
    publish_general_profiles(stage / "army.db", rules)
    rules.unlink()


def _build_rules_and_publications(stage: Path, root: Path, manifest: dict[str, Any]) -> None:
    army, rules = stage / "army.db", stage / "rules_n5.db"
    generation = verified_normalized_generation(army, stage / "normalized.json")
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
    variants = publication_from_candidate(build_variant_usage_from_normalized(
        army, stage / "normalized.json", rules,
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
    trait_links = load_trait_wiki_references(
        root / "config/catalogs/trait-wiki-references.json"
    )
    saving_rolls = load_combined_saving_roll_map(
        root / "config/catalogs/weapon-combined-saving-rolls.json"
    )
    ammunition = load_ammunition_reference_map(
        root / "config/catalogs/weapon-ammunition-references.json"
    )
    properties = load_weapon_properties(
        root / "config/catalogs/weapon-properties.json"
    )
    export_rules_database(
        documents, rules, variant_usage=variants, weapon_citations=weapons,
        restriction_chart=chart, trait_wiki_links=trait_links,
        combined_saving_rolls=saving_rolls, ammunition_references=ammunition,
        weapon_properties=properties, materialize_composed_records=True,
        army_database=army, **export_options,
    )


def _build_registered_seasons(stage: Path, root: Path, core_revision: str) -> None:
    """Materialize every explicitly registered ITS season and its pinned library."""
    for season, (filename, season_source) in SEASON_DATABASE_SOURCES.items():
        relative_library = season_shared_library_source(season)
        build_its_database(
            root / season_source, stage / filename, core_revision=core_revision,
            shared_library=(root / relative_library if relative_library is not None else None),
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
    for season in SEASON_DATABASE_SOURCES:
        season_shared_library_source(season)
    selected_manifest: Path | None = getattr(args, "snapshot_manifest", None)
    if selected_manifest is not None and args.source is None:
        raise ValueError("--snapshot-manifest requires an explicit Army ZIP source")
    if selected_manifest is not None and args.metadata is not None:
        raise ValueError("--snapshot-manifest cannot combine with --metadata")
    implicit_source = args.source is None
    source = (args.source if args.source is not None else latest_snapshot()).resolve()
    if implicit_source and args.metadata is None:
        selected_manifest = root / "local/data/manifests/snapshots" / f"{source.stem}.json"
        if not selected_manifest.is_file():
            raise ValueError(
                f"Default Army source needs matching snapshot provenance: {selected_manifest}"
            )
    selected_manifest = selected_manifest.resolve() if selected_manifest is not None else None
    target = args.db_dir.resolve()
    history_root = (root / "local/data/history" if getattr(args, "with_unit_history", True)
                    else None)
    manifest = collect_build_manifest(
        root, source, args.metadata, snapshot_manifest=selected_manifest,
        history_root=history_root,
    )
    selected_manifest_sha256 = (
        file_sha256(selected_manifest) if selected_manifest is not None else None
    )
    if target.exists() and not target.is_dir():
        raise ValueError("Runtime output must be a directory")
    protected = {source, *(root / name for name in manifest["inputs"])}
    if args.metadata is not None:
        protected.add(args.metadata.resolve())
    if selected_manifest is not None:
        protected.add(selected_manifest)
    if history_root is not None:
        protected.update(path.resolve() for path in history_inputs(history_root))
    for name in COMPLETE_RUNTIME_FILES:
        output = target / name
        if output.resolve() in protected or (output.exists() and not output.is_file()):
            raise ValueError(f"Runtime output would replace an input or non-file: {name}")

    work = root / "local/work/build"
    work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="runtime-", dir=work) as directory:
        stage = Path(directory)
        army_args = argparse.Namespace(**vars(args))
        army_args.source, army_args.output_dir = source, stage
        if build_army(army_args, build_record(manifest, "army")) != 0:
            raise ValueError("Army build failed before runtime publication")
        # Only the verified normalized model is needed by these overlays.
        # The legacy raw-pair publisher APIs remain available for standalone use.
        normalized = stage / "normalized.json"
        publish_equipment_encodings(
            stage / "army.db", None,
            root / "config/catalogs/equipment-presentation-encodings.json",
            normalized=normalized,
        )
        publish_skill_classifications(
            stage / "army.db", None,
            root / "config/catalogs/skill-source-classifications.json",
            normalized=normalized,
        )
        publish_unit_filter_semantics(
            stage / "army.db", None,
            root / "config/catalogs/unit-filter-semantics.json",
            normalized=normalized,
        )
        publish_army_reference_data(
            stage / "army.db", None,
            root / "data/curated/identities/army-overview.json",
            root / "data/curated/identities/legacy-armies.json",
            normalized=normalized,
        )
        publish_symbol_paths(
            stage / "army.db", None,
            root / "data/manifests/symbol-publication.json",
            root / "src/infinity_db/web/static",
            normalized=normalized,
        )
        _build_general_profiles(stage, root)
        publish_filter_contexts(stage / "army.db")
        if history_root is not None:
            publish_unit_history(stage / "army.db", history_root)
        _build_rules_and_publications(stage, root, manifest)
        from .rules_database import RulesDatabase

        core_revision = RulesDatabase(stage / "rules_n5.db").current_core_scenario_revision()
        _build_registered_seasons(stage, root, core_revision)
        publish_search_index(
            stage / "army.db", stage / "rules_n5.db",
            {season: stage / filename for season, (filename, _) in SEASON_DATABASE_SOURCES.items()},
        )
        result = validate_database_set(stage, require_complete=True)
        if result["buildProvenance"].get("buildSetId") != build_set_id(manifest):
            raise ValueError("Built runtime set does not match the selected build inputs")
        if (
            collect_build_manifest(
                root, source, args.metadata, snapshot_manifest=selected_manifest,
                history_root=history_root,
            ) != manifest
            or (
                selected_manifest is not None
                and file_sha256(selected_manifest) != selected_manifest_sha256
            )
        ):
            raise ValueError(
                "Build inputs changed during generation; selected outputs were retained"
            )
        target.mkdir(parents=True, exist_ok=True)
        # Stop serving this directory before rebuilding. Individual replacements
        # are atomic; interruption leaves an invalid mixed set, recovered by rerun.
        for name in sorted(COMPLETE_RUNTIME_FILES):
            os.replace(stage / name, target / name)
        for name in ("variant-usage.json", "weapon-profile-sources.json",
                     "its_18_2026.09.11.db"):
            obsolete = target / name
            if obsolete.is_file() or obsolete.is_symlink():
                obsolete.unlink()
        return result
