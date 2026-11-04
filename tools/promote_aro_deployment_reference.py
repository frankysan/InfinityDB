"""Guarded v9 promotion of the core ARO and Deployment Phase reference.

The default mode stages and validates a deterministic candidate without writes.
--promote atomically replaces the tracked rules database and ignored, matching
deployed-object publication with a retained local rollback pair.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_directory
from infinity_db.deployed_object_publication import load_deployed_object_publication
from infinity_db.rules_database import RulesDatabase
from tools.build_deployed_object_publication import build_publication, publication_bytes
from tools.release_rules_export import (
    export_release_rules,
    same_logical_rules_contents,
)
from tools.restrictions_v9_release import _replace_with_rollback

ROOT = Path(__file__).resolve().parents[1]
RULES = Path("data/generated/rules.db")
OBJECTS = Path("data/generated/deployed-objects.json")
ARMY = Path("data/generated/infinity.db")
CURATED = Path("data/curated/rules/n5-core-v5.3.json")
DELIVERY = Path("config/validation/deployed-object-delivery-reviews.json")
CANDIDATES = Path("config/validation/deployed-object-candidate-reviews.json")
PDF = Path("data/pdf/rules/n5-rules-v5-3-en.pdf")
SOURCE_SHA256 = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
NEW_ID = "rule:automatic-reaction-order"
CHANGED_ID = "rule:deployment-phase"
CITATIONS = {
    NEW_ID: {("n5-core-v5.3-pdf", 13), ("n5-core-v5.3-pdf", 14)},
    CHANGED_ID: {("n5-core-v5.3-pdf", 15), ("n5-core-v5.3-pdf", 16)},
}
CLAUSES = {
    NEW_ID: (
        "Line of Fire", "Zone of Control", "Hacking Area", "Template Weapon",
        "Comms Attack", "single", "activated by the Order", "Burst B1",
        "cannot split", "simultaneous", "forfeit", "without LoF or ZoC",
        "second Check", "authorized Skills only", "cannot react to another",
    ),
    CHANGED_ID: (
        "Initiative Roll", "reserves", "entire base", "totally inside",
        "enemy or Neutral", "mission objective", "not be deployed in contact",
        "Prone", "whole base", "central line", "Exclusion Zone",
        "Forward Deployment",
    ),
}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ids(path: Path) -> set[str]:
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        return {row[0] for row in db.execute("SELECT id FROM records")}


def _check_source(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    selected = {
        key: [item for item in records if item["id"] == key]
        for key in (NEW_ID, CHANGED_ID)
    }
    if any(len(rows) != 1 for rows in selected.values()):
        raise ValueError("ARO and Deployment owners must each have exactly one definition")
    result = {key: rows[0] for key, rows in selected.items()}
    for identity, record in result.items():
        if (
            record["kind"] != "rule"
            or record["composition"] != {"role": "definition"}
            or record["scope"] != {"game": "N5", "seasons": ["current"]}
            or record["facts"]["category"] != "basic-rule"
            or {(c["sourceId"], c["page"]) for c in record["citations"]} != CITATIONS[identity]
        ):
            raise ValueError(f"{identity}: kind, scope or N5.3 citation drift")
        text = " ".join(
            [record["summary"]]
            + [
                clause
                for field in ("requirements", "effects", "restrictions", "clarifications")
                for clause in record["facts"].get(field, [])
            ]
        )
        for required in CLAUSES[identity]:
            if required.casefold() not in text.casefold():
                raise ValueError(f"{identity}: missing reviewed source clause {required!r}")
    if len(result[NEW_ID]["facts"]["requirements"]) != 4:
        raise ValueError("The four source-native ARO eligibility families must be separate")
    if len(result[CHANGED_ID]["facts"]["effects"]) < 4:
        raise ValueError("The p.15 sequence and p.16 Deployment conditions must coexist")
    return result


def verify_candidate(root: Path = ROOT, *, promote: bool = False) -> dict[str, Any]:
    root = root.resolve()
    if not (root / "local").is_dir():
        raise ValueError("Ignored local/ recovery directory is required")
    if _digest(root / PDF) != SOURCE_SHA256:
        raise ValueError("Reviewed N5.3 source PDF hash differs")
    active_path = root / RULES
    existing = RulesDatabase(active_path)
    existing.validate()
    old_ids = _ids(active_path)
    published = NEW_ID in old_ids
    if published and promote:
        raise ValueError("Already published; repeated C2 promotion is forbidden")
    if not published:
        unchanged = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", RULES.as_posix()],
            cwd=root, capture_output=True, check=False,
        )
        if unchanged.returncode != 0:
            raise ValueError("Tracked rules database differs from HEAD")
    previous = load_deployed_object_publication(root / OBJECTS, root / ARMY, active_path)
    if previous is None:
        raise ValueError("Active rules/deployed-object publication does not match")
    docs = load_curated_directory(root / "data/curated/rules")
    selected = _check_source([
        record for _, document in docs for record in document["records"]
    ])
    source_hash = _digest(root / CURATED)
    original = {name: (root / name).read_bytes() for name in (RULES, OBJECTS)}

    with tempfile.TemporaryDirectory(prefix="aro-deployment-v9-", dir=root / "local") as tmp:
        first, second = Path(tmp) / "first.db", Path(tmp) / "second.db"
        export_release_rules(docs, first, baseline=active_path)
        export_release_rules(docs, second, baseline=active_path)
        if _digest(first) != _digest(second):
            raise ValueError("Non-deterministic rules export")
        byte_identical = _digest(first) == _digest(active_path)
        logical_match = (
            byte_identical or same_logical_rules_contents(active_path, first)
        ) if published else None
        if published and not logical_match:
            raise ValueError("Published rules differ logically from reviewed rebuild")
        staged = RulesDatabase(first)
        staged.validate()
        if _ids(first) != old_ids | {NEW_ID}:
            raise ValueError("Candidate changed prior record identities")
        unchanged_ids = old_ids - {CHANGED_ID}
        for identity in sorted(unchanged_ids):
            if existing.composed_record(identity) != staged.composed_record(identity):
                raise ValueError(f"Unrelated rule changed: {identity}")
        for identity, curated in selected.items():
            result = staged.composed_record(identity)
            if (
                result is None
                or result["summary"] != curated["summary"]
                or result["facts"] != curated["facts"]
            ):
                raise ValueError(f"Source facts did not publish for {identity}")
        if existing.restrictions_payload() != staged.restrictions_payload():
            raise ValueError("Unrelated typed Restrictions changed")
        projection = build_publication(
            root / ARMY, first, root / CURATED, root / DELIVERY, root / CANDIDATES
        )
        expected = json.loads(json.dumps(previous))
        expected["sourceSnapshot"]["rulesDatabaseSha256"] = _digest(first)
        expected["sourceSnapshot"]["curatedSourceSha256"] = source_hash
        if projection != expected:
            raise ValueError("Unrelated deployed objects changed")
        if source_hash != _digest(root / CURATED) or any(
            (root / name).read_bytes() != data for name, data in original.items()
        ):
            raise ValueError("Source or publication changed during staging")
        report = {
            "scope": "v1s-032c2-aro-deployment",
            "existingRecordsVerifiedUnchanged": len(unchanged_ids),
            "candidateRecords": len(old_ids | {NEW_ID}),
            "alreadyPublished": published,
            "deterministic": True,
            "matchedPublication": True,
            "sourceSha256": SOURCE_SHA256,
            "candidateRulesSha256": _digest(first),
            "publishedRulesSha256": _digest(active_path) if published else None,
            "byteIdenticalWithPublished": byte_identical if published else None,
            "logicallyEquivalentWithPublished": logical_match,
        }
        if not promote:
            return report

        def post_validate() -> None:
            promoted = RulesDatabase(root / RULES)
            promoted.validate()
            for identity in selected:
                if promoted.composed_record(identity) != staged.composed_record(identity):
                    raise ValueError(f"Post-promotion {identity} mismatch")
            if load_deployed_object_publication(
                root / OBJECTS, root / ARMY, root / RULES,
            ) != projection:
                raise ValueError("Post-promotion matched release pair is invalid")

        backup = _replace_with_rollback(
            root,
            {RULES: first.read_bytes(), OBJECTS: publication_bytes(projection)},
            post_validate,
            backup_prefix="aro-deployment-v9-recovery-",
        )
        report["promoted"] = True
        report["recoveryPath"] = str(backup.relative_to(root))
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify_candidate(promote=args.promote), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
