"""Prepare local source-audit artifacts matching the tracked runtime publication."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from infinity_db.build_provenance import build_record, build_set_id, validate_set_provenance
from infinity_db.cli import _build_army, _export
from infinity_db.database import Database
from infinity_db.database.normalized_source import verified_normalized_generation
from infinity_db.database.publication import (
    PUBLISHED_CONTENT_SHA256_KEY,
    _database_metadata,
    validate_database_pair,
)
from infinity_db.database.schema import DATABASE_COMPATIBILITY_KEY, METADATA_TABLE
from infinity_db.database_set_builder import collect_build_manifest
from infinity_db.sqlite_determinism import normalize_sqlite_header, vacuum_deterministic_sqlite

ROOT = Path(__file__).resolve().parents[2]


def bind_staged_pair(army: Path, raw: Path, normalized: Path, published: Path) -> str:
    """Bind a newly exported audit pair to the independently verified release."""
    generation = validate_database_pair(army, raw_path=raw)
    Database(published).validate()
    if generation is None or verified_normalized_generation(published, normalized) != generation:
        raise ValueError("Raw export does not match the published Army generation")

    # Post-export overlays change only the application compatibility revision and
    # published relational checksum. The raw archive still contains the same
    # source rows. Never relabel an unrelated source or rewrite an existing archive.
    base = _database_metadata(raw)
    target = _database_metadata(published)
    allowed = {DATABASE_COMPATIBILITY_KEY, PUBLISHED_CONTENT_SHA256_KEY}
    if base.keys() != target.keys() or any(
        base[key] != target[key] for key in base.keys() - allowed
    ):
        raise ValueError("Raw export has unexpected shared metadata differences")
    with closing(sqlite3.connect(published.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        revision = db.execute("PRAGMA user_version").fetchone()[0]
    with closing(sqlite3.connect(raw)) as db:
        with db:
            db.executemany(
                f"UPDATE {METADATA_TABLE} SET value=? WHERE key=?",
                [(target[key], key) for key in sorted(allowed)],
            )
            db.execute(f"PRAGMA user_version={revision}")
        vacuum_deterministic_sqlite(db)
    normalize_sqlite_header(raw)
    shutil.copyfile(published, army)
    if validate_database_pair(army, raw_path=raw) != generation:
        raise ValueError("Audit pair failed final generation validation")
    return generation


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
    manifest = collect_build_manifest(
        root, source, None, snapshot_manifest=snapshot_manifest,
        history_root=root / "local/data/history" if "history" in provenance else None,
    )
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
        generation = bind_staged_pair(
            army, raw, stage / "normalized.json", release / "army.db",
        )
        if generation != provenance.get("armyExportPairSha256"):
            raise ValueError("Raw export does not match the published Army generation")
        destination = work / "army"
        # Preserve existing evidence if its generation cannot be verified against
        # the release. A failed or stale pair is not grounds for deleting it.
        if destination.exists():
            try:
                existing = validate_database_pair(
                    release / "army.db", raw_path=destination / "army.raw.db",
                )
            except (OSError, ValueError, sqlite3.Error):
                existing = None
            if existing != generation:
                retained = Path(tempfile.mkdtemp(prefix="retained-army-audit-", dir=work))
                os.replace(destination, retained / "army")
                print(f"Retained previous audit inputs: {retained / 'army'}", flush=True)
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
