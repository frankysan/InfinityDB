"""Stage and verify a complete v10 runtime data bundle from reviewed sources.

No tracked release artifact is rewritten. The staging output contains exactly
the files an immutable v10 application image should package.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_directory
from infinity_db.database_set import V10_RUNTIME_FILES, validate_database_set
from infinity_db.deployed_object_builder import build_deployed_objects
from infinity_db.rules_database import export_rules_database
from infinity_db.variant_usage import build_variant_usage_projection
from infinity_db.variant_usage_reference import (
    load_variant_usage_publication,
    publication_from_candidate,
)
from infinity_db.weapon_profile_publication import load_weapon_profile_publication
from tools.build_weapon_profile_publication import DEFAULT_REVIEWS
from tools.build_weapon_profile_publication import (
    build_publication as build_weapon_publication,
)
from tools.build_weapon_profile_publication import (
    publication_bytes as weapon_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGE = ROOT / "local" / "v10-candidate"
REQUIRED = V10_RUNTIME_FILES


def _digest(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def _json_bytes(document: dict[str, Any]) -> bytes:
    return (json.dumps(
        document, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False,
    ) + "\n").encode("utf-8")


def _inputs(root: Path) -> tuple[Path, Path, Path, Path, Path, Path]:
    return (
        root / "data/generated/infinity.db",
        root / "data/generated/infinity.raw.db",
        root / "data/curated/rules",
        root / "config/validation/restrictions-source-chart.json",
        root / "config/validation/deployed-object-delivery-reviews.json",
        root / "config/validation/deployed-object-candidate-reviews.json",
    )


def verify_candidate(stage: Path, *, root: Path = ROOT) -> dict[str, Any]:
    """Reject stale/missing/unmatched outputs; compare reviewed generated publications."""
    stage = stage.resolve()
    actual = {entry.name for entry in stage.iterdir()}
    if actual != REQUIRED:
        raise ValueError(f"Incomplete v10 runtime bundle: {sorted(actual ^ REQUIRED)}")
    army, raw, *_ = _inputs(root)
    staged_army = stage / "infinity.db"
    staged_rules = stage / "rules.db"
    if _digest(staged_army) != _digest(army):
        raise ValueError("Staged Army database differs from pinned build input")
    expected_variant = publication_from_candidate(
        build_variant_usage_projection(
            staged_army, raw, staged_rules,
        )
    )
    path = stage / "variant-usage.json"
    if path.read_bytes() != _json_bytes(expected_variant):
        raise ValueError("Staged exact-variant publication differs from reviewed inputs")
    if load_variant_usage_publication(
        path, staged_army, staged_rules,
    ) != expected_variant:
        raise ValueError("Staged variant publication failed runtime validation")
    weapon_path = stage / "weapon-profile-sources.json"
    expected_weapon = build_weapon_publication(staged_army, staged_rules, DEFAULT_REVIEWS)
    if weapon_path.read_bytes() != weapon_bytes(expected_weapon):
        raise ValueError("Staged Weapon-profile publication differs from reviewed inputs")
    if not load_weapon_profile_publication(weapon_path, staged_army, staged_rules):
        raise ValueError("Staged Weapon-profile publication failed runtime validation")
    result = validate_database_set(stage)
    if result["deployedObjects"] != 17 or result["unresolvedDeliveries"] != 1:
        raise ValueError("Staged deployed objects are incomplete")
    return result


def _write_companion_publications(stage: Path, *, root: Path = ROOT) -> None:
    """Produce the matched runtime companions for either development or release staging."""
    stage.joinpath("variant-usage.json").write_bytes(_json_bytes(
        publication_from_candidate(build_variant_usage_projection(
            stage / "infinity.db", root / "data/generated/infinity.raw.db",
            stage / "rules.db",
        ))
    ))
    stage.joinpath("weapon-profile-sources.json").write_bytes(weapon_bytes(
        build_weapon_publication(stage / "infinity.db", stage / "rules.db", DEFAULT_REVIEWS)
    ))


def build_candidate(stage: Path, *, root: Path = ROOT) -> dict[str, Any]:
    """Build into an empty staging directory without changing the tracked release."""
    stage.mkdir(parents=True, exist_ok=True)
    if any(stage.iterdir()):
        raise ValueError("Candidate output directory must be empty")
    army, _raw, rules_inputs, manifest_path, delivery, candidate_review = _inputs(root)
    shutil.copyfile(army, stage / "infinity.db")
    documents = load_curated_directory(rules_inputs)
    core_source = next(
        (path for path, doc in documents
         if doc["collection"]["id"] == "n5-core-v5.3"
         and doc["collection"]["status"] == "current"),
        None,
    )
    if core_source is None:
        raise ValueError("Current N5.3 core collection required")
    objects = build_deployed_objects(stage / "infinity.db", core_source, delivery, candidate_review)
    export_rules_database(
        documents, stage / "rules.db",
        restrictions_manifest=json.loads(manifest_path.read_text(encoding="utf-8")),
        deployed_objects=objects,
    )
    _write_companion_publications(stage, root=root)
    return verify_candidate(stage, root=root)


def publish_checkout_runtime(
    built_rules: Path,
    destination: Path = ROOT / "local" / "checkout-runtime",
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Assemble a complete ignored checkout runtime from the freshly built rules DB.

    Never modify release artifacts. The data is published only after the
    matching v2 variant and reviewed Weapon publications pass verification.
    """
    import tempfile

    source = (root / "data/generated/infinity.db").resolve()
    target = destination.resolve()
    if not target.is_relative_to((root / "local").resolve()):
        raise ValueError("Checkout runtime must reside within ignored local/")
    if not built_rules.is_file():
        raise ValueError("Build the standalone rules database before publishing checkout runtime")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".checkout-runtime-", dir=target.parent))
    try:
        shutil.copyfile(source, temporary / "infinity.db")
        shutil.copyfile(built_rules, temporary / "rules.db")
        _write_companion_publications(temporary, root=root)
        result = verify_candidate(temporary, root=root)
        if target.exists():
            if {child.name for child in target.iterdir()} != REQUIRED:
                raise ValueError("Unexpected contents in existing checkout runtime")
            shutil.rmtree(target)
        temporary.replace(target)
        return result
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--check", action="store_true", help="Validate an existing candidate")
    parser.add_argument(
        "--checkout", action="store_true",
        help="Refresh ignored local/checkout-runtime from the standalone v10 rules DB",
    )
    parser.add_argument(
        "--rules-db", type=Path, default=ROOT / "local/rules-standalone.db",
        help="Source v10 Rules database for --checkout",
    )
    args = parser.parse_args(argv)
    default = ROOT / "local/checkout-runtime" if args.checkout else DEFAULT_STAGE
    destination = (args.output_dir or default).resolve()
    if not destination.is_relative_to((ROOT / "local").resolve()):
        parser.error("Staging must be inside the ignored local/ directory")
    if args.checkout:
        result = (
            verify_candidate(destination) if args.check
            else publish_checkout_runtime(args.rules_db, destination)
        )
        if destination == (ROOT / "local/checkout-runtime").resolve():
            from infinity_db.checkout_runtime import select_checkout_database

            if select_checkout_database() != destination / "infinity.db":
                raise ValueError("Default serve did not select the checkout runtime")
    else:
        result = (
            verify_candidate(destination) if args.check else build_candidate(destination)
        )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
