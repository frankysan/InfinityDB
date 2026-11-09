"""Prepare a minimal, verified runtime-data directory for immutable Docker images.

Deployment packages already-built artifacts; it never regenerates rules or Army
data inside the image. The legacy v9 image includes deployed-objects.json, while
a v10 image gets exactly four files and no deployed-object JSON.
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

from infinity_db.database.repository import Database
from infinity_db.database_set import validate_database_set
from infinity_db.deployed_object_publication import load_deployed_object_publication
from infinity_db.rules_database import RulesDatabase
from infinity_db.variant_usage_reference import load_variant_usage_publication
from infinity_db.weapon_profile_publication import load_weapon_profile_publication

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data/generated"
DEFAULT_OUTPUT = ROOT / "data/runtime"
COMMON = {"infinity.db", "rules.db"}
REVIEWED = {"variant-usage.json", "weapon-profile-sources.json"}
LEGACY = {"deployed-objects.json"}


def expected_files(source: Path) -> set[str]:
    """Validate the exact source pair and select schema-specific files."""
    army, rules_path = source / "infinity.db", source / "rules.db"
    # Read the header without creating a missing database. Legacy formats keep
    # their old packaging contract until the deliberate P2.5 retirement.
    if not rules_path.is_file():
        raise ValueError(f"Rules database does not exist: {rules_path}")
    with closing(sqlite3.connect(
        rules_path.resolve().as_uri() + "?mode=ro", uri=True,
    )) as connection:
        schema = connection.execute("PRAGMA user_version").fetchone()[0]
    if schema in {10, 11}:
        result = validate_database_set(source)
        if result["deployedObjects"] != 17 or result["unresolvedDeliveries"] != 1:
            raise ValueError("Incomplete reviewed deployed objects")
        return set(result["sha256"])

    Database(army).validate()
    rules = RulesDatabase(rules_path)
    rules.validate()
    if schema not in {8, 9}:
        raise ValueError("Unsupported runtime rules schema")
    files = set(COMMON)
    files.update(LEGACY)
    objects = load_deployed_object_publication(
        source / "deployed-objects.json", army, rules_path,
    )
    if objects is None:
        raise ValueError("Legacy rules require deployed-objects.json")
    if len(objects["objects"]) != 17 or len(objects["unresolvedDeliveries"]) != 1:
        raise ValueError("Incomplete reviewed deployed objects")

    if schema >= 9:
        files.update(REVIEWED)
        variants = load_variant_usage_publication(
            source / "variant-usage.json", army, rules_path,
            source / "deployed-objects.json",
        )
        if (variants is None or not variants["variants"]
            or variants["formatVersion"] != 1):
            raise ValueError("Invalid schema-matched variant usage publication")
        if not load_weapon_profile_publication(
            source / "weapon-profile-sources.json", army, rules_path,
        ):
            raise ValueError("Missing source-matched Weapon citations")
    return files


def prepare_bundle(source: Path, output: Path) -> set[str]:
    """Create only the verified runtime files; do not alter source artifacts."""
    source, output = source.resolve(), output.resolve()
    if source == output or source.is_relative_to(output) or output.is_relative_to(source):
        raise ValueError("Runtime source and output directories must be independent")
    names = expected_files(source)
    output.mkdir(parents=True, exist_ok=True)
    for entry in output.iterdir():
        if not entry.is_file():
            raise ValueError("Runtime bundle contains an unexpected subdirectory")
        entry.unlink()
    for name in sorted(names):
        shutil.copyfile(source / name, output / name)
    if {p.name for p in output.iterdir()} != names:
        raise ValueError("Incomplete runtime bundle")
    if expected_files(output) != names:
        raise ValueError("Runtime bundle failed after copying")
    return names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    if args.output_dir.resolve() != DEFAULT_OUTPUT.resolve():
        parser.error("Docker runtime data must be staged under data/runtime/")
    names = prepare_bundle(args.source_dir, args.output_dir)
    print(f"Prepared immutable image data: {', '.join(sorted(names))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
