"""Stage and explicitly promote a reviewed Commlink v9 rules/publication pair.

Only the exact optional Reinforcements Extra Commlink (+1)/(+2) source
metadata may differ from the current tracked release pair. Promotion requires
an unchanged candidate, a reproducible rebuild and rollback copies in local/.
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
from tools.restrictions_v9_release import (
    _check_variant_semantics_delta,
    _replace_with_rollback,
)

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

def promote_commlink_candidate(destination: Path, *, root: Path = ROOT) -> Path:
    """Promote the exact verified candidate pair with retained rollback copies."""
    root = root.resolve()
    local = root / "local"
    if destination.is_symlink():
        raise ValueError("Commlink candidate directory must not be a symlink")
    stage = destination.resolve()
    if not stage.is_relative_to(local) or not stage.is_dir():
        raise ValueError("Commlink candidate must be a directory inside ignored local/")
    if {path.name for path in stage.iterdir()} != {
        "rules.db", "deployed-objects.json", "manifest.json",
    }:
        raise ValueError("Commlink candidate directory has unexpected contents")
    manifest_path = stage / "manifest.json"
    if manifest_path.is_symlink():
        raise ValueError("Commlink manifest must not be a symlink")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        set(manifest) != {
            "kind", "record", "sourceCollection", "previousSha256",
            "candidateSha256", "deployedObjectCount",
        }
        or manifest["kind"] != "staged-commlink-v9-pair-not-promoted"
        or manifest["record"] != COMMLINK[1]
        or manifest["sourceCollection"] != COMMLINK[0]
        or manifest["deployedObjectCount"] != 17
        or set(manifest["previousSha256"]) != {"rules.db", "deployed-objects.json"}
        or set(manifest["candidateSha256"]) != {"rules.db", "deployed-objects.json"}
    ):
        raise ValueError("Unexpected Commlink promotion manifest")
    generated = root / "data/generated"
    tracked = {
        "rules.db": generated / "rules.db",
        "deployed-objects.json": generated / "deployed-objects.json",
    }
    payloads: dict[Path, bytes] = {}
    for name, target in tracked.items():
        check = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", target.relative_to(root).as_posix()],
            cwd=root, capture_output=True, check=False,
        )
        if check.returncode != 0:
            raise ValueError(f"Tracked Commlink release target differs from HEAD: {name}")
        if _sha256(target) != manifest["previousSha256"][name]:
            raise ValueError(f"Commlink baseline changed since staging: {name}")
        source = stage / name
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"Staged Commlink artifact missing or unsafe: {name}")
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != manifest["candidateSha256"][name]:
            raise ValueError(f"Staged Commlink artifact changed: {name}")
        payloads[target.relative_to(root)] = data

    # Independently reconstruct the staged pair from CURRENT maintained inputs.
    # A stale but internally consistent manifest must not authorize publication.
    with tempfile.TemporaryDirectory(prefix="commlink-v9-verify-", dir=local) as temporary:
        fresh = Path(temporary) / "candidate"
        regenerated = stage_commlink_candidate(fresh, root=root)
        if regenerated != manifest:
            raise ValueError("Commlink curated source or release inputs changed since staging")
        for name in tracked:
            if (fresh / name).read_bytes() != payloads[tracked[name].relative_to(root)]:
                raise ValueError(f"Staged Commlink pair is not reproducible: {name}")

    army = generated / "infinity.db"
    expected = load_deployed_object_publication(
        stage / "deployed-objects.json", army, stage / "rules.db",
    )
    if expected is None or len(expected["objects"]) != 17:
        raise ValueError("Staged Commlink release pair is not loadable")

    def post_validate() -> None:
        for name, target in tracked.items():
            if _sha256(target) != manifest["candidateSha256"][name]:
                raise ValueError(f"Promoted Commlink artifact fingerprint changed: {name}")
        published = RulesDatabase(tracked["rules.db"])
        published.validate()
        semantics = published.skill_reviewed_extra_semantics().get("commlink")
        if semantics is None or [
            (entry["extra_id"], entry["effect"]["count"])
            for entry in semantics["extra_values"]
        ] != [(298, 1), (299, 2)]:
            raise ValueError("Promoted Commlink typed parameters are unavailable")
        if load_deployed_object_publication(
            tracked["deployed-objects.json"], army, tracked["rules.db"],
        ) != expected:
            raise ValueError("Promoted Commlink deployed-object publication mismatches staging")
        from infinity_db.web import create_app

        app = create_app(army, rules_database_path=tracked["rules.db"])
        if app.deployed_objects is None or len(app.deployed_objects["objects"]) != 17:
            raise ValueError("Promoted Commlink application did not load the matched pair")

    return _replace_with_rollback(
        root, payloads, post_validate, backup_prefix="commlink-v9-recovery-",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination", type=Path, required=True,
        help="Ignored local/ destination (new for staging, existing for promotion)",
    )
    parser.add_argument(
        "--promote-staged", action="store_true",
        help="Promote this exact verified candidate with retained rollback copies",
    )
    args = parser.parse_args()
    destination = ROOT / args.destination
    local = (ROOT / "local").resolve()
    if not destination.resolve().is_relative_to(local) or destination.resolve() == local:
        parser.error("--destination must be inside the ignored local/ directory")
    if args.promote_staged:
        backup = promote_commlink_candidate(destination)
        print(f"Promoted reviewed Commlink v9 pair; rollback copies: {backup}")
    else:
        manifest = stage_commlink_candidate(destination)
        print(f"Staged Commlink v9 candidate: {destination}")
        print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
