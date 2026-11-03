"""Stage, but never promote, the reviewed Commlink v9 rules/publication pair.

Only the exact optional Reinforcements Extra Commlink (+1)/(+2) source
metadata may differ from the currently tracked release pair. Output
stays under ignored local/ and needs a separate promotion decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_directory
from infinity_db.deployed_object_publication import load_deployed_object_publication
from infinity_db.rules_database import RulesDatabase
from tools.build_deployed_object_publication import build_publication, publication_bytes
from tools.release_rules_export import export_release_rules
from tools.restrictions_v9_release import _check_variant_semantics_delta

ROOT = Path(__file__).resolve().parents[1]
COMMLINK = ("reinforcements-extra-n4-reference", "skill:commlink")


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def stage_commlink_candidate(destination: Path, *, root: Path = ROOT) -> dict[str, Any]:
    """Build a validated pair in a new directory; never modify the active pair."""
    root = root.resolve()
    destination = destination.resolve()
    if destination.exists():
        raise ValueError("Commlink staging destination already exists")
    if not destination.parent.is_dir():
        raise ValueError("Commlink staging destination parent must exist")
    generated = root / "data/generated"
    current_rules = generated / "rules.db"
    current_publication = generated / "deployed-objects.json"
    army = generated / "infinity.db"
    for relative in ("data/generated/rules.db", "data/generated/deployed-objects.json"):
        check = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", relative],
            cwd=root, capture_output=True, check=False,
        )
        if check.returncode != 0:
            raise ValueError(f"Tracked release artifact differs from HEAD: {relative}")
    previous = load_deployed_object_publication(current_publication, army, current_rules)
    if previous is None:
        raise ValueError("Existing matched release publication is missing")
    documents = load_curated_directory(root / "data/curated/rules")
    matches = [
        row for _, document in documents for row in document["records"]
        if (document["collection"]["id"], row["id"]) == COMMLINK
    ]
    if len(matches) != 1:
        raise ValueError("Exactly one reviewed Commlink source record is required")
    variant = matches[0]["variantSemantics"]
    if (
        matches[0]["review"]["status"] != "reviewed"
        or matches[0]["armyLinks"] != [{"entity": "skill", "id": "commlink"}]
        or set(variant) != {"inheritance", "occurrenceParameters"}
        or variant["inheritance"] != "family"
    ):
        raise ValueError("Commlink source review contract changed")
    requested: dict[tuple[str, str], str] = {
        COMMLINK: json.dumps(variant, ensure_ascii=False, separators=(",", ":")),
    }
    before_hashes = {
        "rules.db": _sha256(current_rules),
        "deployed-objects.json": _sha256(current_publication),
    }
    working = Path(tempfile.mkdtemp(prefix="commlink-v9-stage-", dir=destination.parent))
    try:
        next_rules = working / "rules.db"
        export_release_rules(documents, next_rules, baseline=current_rules)
        _check_variant_semantics_delta(current_rules, next_rules, requested)
        current = RulesDatabase(current_rules)
        staged = RulesDatabase(next_rules)
        staged.validate()
        if staged.restrictions_payload() != current.restrictions_payload():
            raise ValueError("Staged Commlink changes reviewed Restrictions")
        source_paths = (
            root / "data/curated/rules/n5-core-v5.3.json",
            root / "config/validation/deployed-object-delivery-reviews.json",
            root / "config/validation/deployed-object-candidate-reviews.json",
        )
        proposed = build_publication(army, next_rules, *source_paths)
        expected = json.loads(json.dumps(previous))
        expected["sourceSnapshot"]["rulesDatabaseSha256"] = _sha256(next_rules)
        if proposed != expected:
            raise ValueError("Commlink staging changed unrelated deployed-object content")
        if len(proposed["objects"]) != 17:
            raise ValueError("Commlink staging changed deployed-object count")
        output_publication = working / "deployed-objects.json"
        output_publication.write_bytes(publication_bytes(proposed))
        if load_deployed_object_publication(output_publication, army, next_rules) != proposed:
            raise ValueError("Staged Commlink publication failed matched-pair validation")
        if before_hashes != {
            "rules.db": _sha256(current_rules),
            "deployed-objects.json": _sha256(current_publication),
        }:
            raise ValueError("Tracked release artifacts changed during staging")
        manifest: dict[str, Any] = {
            "kind": "staged-commlink-v9-pair-not-promoted",
            "record": "skill:commlink",
            "sourceCollection": "reinforcements-extra-n4-reference",
            "previousSha256": before_hashes,
            "candidateSha256": {
                "rules.db": _sha256(next_rules),
                "deployed-objects.json": _sha256(output_publication),
            },
            "deployedObjectCount": 17,
        }
        (working / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )
        if destination.exists():
            raise ValueError("Commlink staging destination was created concurrently")
        working.rename(destination)
        return manifest
    finally:
        if working.exists():
            shutil.rmtree(working)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination", type=Path, required=True,
        help="New ignored local/ directory for an unpromoted candidate pair",
    )
    args = parser.parse_args()
    destination = (ROOT / args.destination).resolve()
    local = (ROOT / "local").resolve()
    if not destination.is_relative_to(local) or destination == local:
        parser.error("--destination must be inside the ignored local/ directory")
    manifest = stage_commlink_candidate(destination)
    print(f"Staged Commlink v9 candidate: {destination}")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
