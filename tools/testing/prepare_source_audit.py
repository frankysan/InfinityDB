"""Prepare local source-audit artifacts matching the tracked runtime publication."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from infinity_db.army_reference_storage import publish_army_reference_data
from infinity_db.build_provenance import build_record, build_set_id, validate_set_provenance
from infinity_db.cli import _build_army, _export
from infinity_db.database.publication import validate_database_pair
from infinity_db.database_set_builder import collect_build_manifest
from infinity_db.equipment_presentation_storage import publish_equipment_encodings
from infinity_db.skill_classification_storage import publish_skill_classifications
from infinity_db.symbol_path_storage import publish_symbol_paths
from infinity_db.unit_filter_storage import publish_unit_filter_semantics

ROOT = Path(__file__).resolve().parents[2]


def prepare(root: Path = ROOT) -> str:
    """Reproduce the legacy paired export; verify before replacing local outputs."""
    root = root.resolve()
    release = root / "data/generated"
    symbols = root / "data/manifests/symbol-publication.json"
    source_name = json.loads(symbols.read_text(encoding="utf-8"))[
        "sourceSnapshot"
    ]["armyArtifact"]["name"]
    source = root / "local/data/raw/army" / source_name
    snapshot_manifest = root / "local/data/manifests/snapshots" / f"{source.stem}.json"
    provenance = validate_set_provenance(release / "army.db", release / "rules_n5.db")
    manifest = collect_build_manifest(root, source, None, snapshot_manifest=snapshot_manifest)
    if build_set_id(manifest) != provenance.get("buildSetId"):
        raise ValueError("Source or checkout inputs do not match the tracked runtime build")
    work = root / "local/work/build"
    work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="source-audit-", dir=work) as directory:
        stage = Path(directory)
        args = argparse.Namespace(
            source=source, output_dir=stage, metadata=None, no_verify=False,
            compact=True, require_metadata_for_build=True,
        )
        if _build_army(args, build_record(manifest, "army")) != 0:
            raise ValueError("Army source build failed")
        army, raw = stage / "army.db", stage / "army.raw.db"
        _export(stage / "normalized.json", army, include_raw=True)
        publish_equipment_encodings(
            army, raw, root / "config/catalogs/equipment-presentation-encodings.json",
        )
        publish_skill_classifications(
            army, raw, root / "config/catalogs/skill-source-classifications.json",
        )
        publish_unit_filter_semantics(
            army, raw, root / "config/catalogs/unit-filter-semantics.json",
        )
        publish_army_reference_data(
            army, raw, root / "data/curated/identities/army-overview.json",
            root / "data/curated/identities/legacy-armies.json",
        )
        publish_symbol_paths(army, raw, symbols, root / "src/infinity_db/web/static")
        generation = validate_database_pair(release / "army.db", raw_path=raw)
        if generation != provenance.get("armyExportPairSha256") or generation is None:
            raise ValueError("Raw export does not match the published Army generation")
        destination = work / "army"
        destination.mkdir(exist_ok=True)
        for name in ("master.json", "normalized.json", "normalized-validation.json",
                     "army.db", "army.raw.db"):
            os.replace(stage / name, destination / name)
    return generation


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    generation = prepare()
    print(f"Matched source-audit archive ready: {generation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
