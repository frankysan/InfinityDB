"""Measure Rules publication exports against the selected complete runtime pair.

Only disposable scratch databases are written. Exact variant facts are read
from the selected published pair, not regenerated from the historical source.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from time import perf_counter
from typing import Any
from unittest.mock import patch

from infinity_db import rules_database as storage
from infinity_db.build_provenance import BUILD_PROVENANCE_KEY, file_sha256
from infinity_db.curated import load_curated_directory
from infinity_db.trait_wiki_references import load_trait_wiki_references
from infinity_db.weapon_ammunition_references import load_ammunition_reference_map
from infinity_db.weapon_combined_saving_rolls import load_combined_saving_roll_map
from infinity_db.weapon_profile_builder import build_publication
from infinity_db.weapon_properties import load_weapon_properties

ROOT = Path(__file__).resolve().parents[2]


def run(directory: Path) -> dict[str, Any]:
    army = directory / "army.db"
    selected = storage.RulesDatabase(directory / "rules_n5.db")
    objects = selected.deployed_objects_payload(army)
    variants = selected.variant_usage_payload(army)
    if objects is None or variants is None:
        raise ValueError("Select a complete published Army/Rules pair")
    with closing(sqlite3.connect(selected.path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        provenance = json.loads(db.execute(
            "SELECT value FROM __rules_metadata WHERE key=?", (BUILD_PROVENANCE_KEY,),
        ).fetchone()[0])
    options = {
        "restrictions_manifest": json.loads(
            (ROOT / "config/validation/restrictions-source-chart.json").read_text(encoding="utf-8")
        ),
        "deployed_objects": objects,
        "build_provenance": provenance,
    }
    started = perf_counter()
    documents = load_curated_directory(ROOT / "data/curated/rules")
    load_seconds = perf_counter() - started
    stages: dict[str, dict[str, float]] = {}

    def measure(name: str, target: Path, **kwargs: Any) -> None:
        times: dict[str, float] = {}
        validate = storage._validate_documents
        insert = storage._insert_document
        vacuum = storage.vacuum_deterministic_sqlite

        def timed_validate(*args: Any, **kw: Any) -> Any:
            start = perf_counter()
            result = validate(*args, **kw)
            times["documentValidation"] = perf_counter() - start
            return result

        def timed_insert(*args: Any, **kw: Any) -> Any:
            start = perf_counter()
            result = insert(*args, **kw)
            times["documentInsertion"] = times.get("documentInsertion", 0) + perf_counter() - start
            return result

        def timed_vacuum(*args: Any, **kw: Any) -> Any:
            start = perf_counter()
            result = vacuum(*args, **kw)
            times["vacuum"] = perf_counter() - start
            return result

        with (
            patch.object(storage, "_validate_documents", timed_validate),
            patch.object(storage, "_insert_document", timed_insert),
            patch.object(storage, "vacuum_deterministic_sqlite", timed_vacuum),
        ):
            start = perf_counter()
            storage.export_rules_database(documents, target, **kwargs)
            times["total"] = perf_counter() - start
        stages[name] = times
        print(f"{name}: {times}", file=sys.stderr, flush=True)

    scratch = ROOT / "local/work/build"
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rules-profile-", dir=scratch) as tmp:
        target = Path(tmp) / "rules_n5.db"
        measure("generalProfilesCore", target, finalize=False)
        measure("deployedObjects", target, **options)
        measure("variantUsage", target, variant_usage=variants, **options)
        start = perf_counter()
        weapons = build_publication(
            army, target, ROOT / "data/curated/weapon-shared-effect-reviews.json",
        )
        weapon_seconds = perf_counter() - start
        measure(
            "finalRules", target, variant_usage=variants, weapon_citations=weapons,
            restriction_chart=json.loads(
                (ROOT / "src/infinity_db/web/static/restrictions-reference.json").read_text(
                    encoding="utf-8",
                )
            ),
            trait_wiki_links=load_trait_wiki_references(
                ROOT / "config/catalogs/trait-wiki-references.json",
            ),
            combined_saving_rolls=load_combined_saving_roll_map(
                ROOT / "config/catalogs/weapon-combined-saving-rolls.json",
            ),
            ammunition_references=load_ammunition_reference_map(
                ROOT / "config/catalogs/weapon-ammunition-references.json",
            ),
            weapon_properties=load_weapon_properties(
                ROOT / "config/catalogs/weapon-properties.json",
            ),
            army_database=army, materialize_composed_records=True, **options,
        )
        storage.RulesDatabase(target).validate()
    return {
        "python": sys.version.split()[0], "sqlite": sqlite3.sqlite_version,
        "armySha256": file_sha256(army), "rulesSha256": file_sha256(selected.path),
        "curatedLoadSeconds": load_seconds, "weaponReviewSeconds": weapon_seconds,
        "stages": stages,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-dir", type=Path, default=ROOT / "data/generated")
    args = parser.parse_args()
    print(json.dumps(run(args.db_dir), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
