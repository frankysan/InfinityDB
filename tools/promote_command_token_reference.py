"""Stage and optionally promote the N5.3 Command Tokens reference release pair.

Default: read-only on tracked outputs. --promote stages two deterministic v9
exports, checks every previously published record, retains restrictions and
unrelated deployed-object publication fields, then atomically replaces both
tracked release outputs using the existing guarded rollback helper.
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
from tools.release_rules_export import export_release_rules
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
IDENTITY = "rule:command-tokens"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _all_ids(path: Path) -> set[str]:
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        return {row[0] for row in db.execute("SELECT DISTINCT id FROM records")}


def _check_record(record: dict[str, Any]) -> None:
    if (
        record["name"] != "Command Tokens"
        or record["kind"] != "rule"
        or record["facts"]["category"] != "command-token-use"
        or record.get("scope") != {"game": "N5", "seasons": ["current"]}
        or {(c["sourceId"], c["page"]) for c in record["citations"]} != {
            ("n5-core-v5.3-pdf", 128), ("n5-core-v5.3-pdf", 129)
        }
    ):
        raise ValueError("N5.3 Command Token identity, scope or citations drift")
    clauses = " ".join(
        [record["summary"]]
        + sum(
            (record["facts"].get(kind, []) for kind in (
                "requirements", "effects", "restrictions", "clarifications"
            )),
            [],
        )
    )
    for fragment in (
        "four Command Tokens", "Strategic", "Executive", "Operational",
        "one Procedural", "one Logistical", "more than ten",
        "Hidden Deployment", "two Speedball Tokens", "ten-member limit",
        "Possessed State", "Coordinated Order", "Guts Roll",
        "Irregular Order", "Regular Order", "Retreat!",
        "Doctor", "Cube", "Engineer", "Remote Presence",
        "Fireteam Leader", "Reactive Turn",
    ):
        if fragment.casefold() not in clauses.casefold():
            raise ValueError(f"Missing reviewed N5.3 Command Token fact: {fragment}")


def verify_candidate(root: Path = ROOT, *, promote: bool = False) -> dict[str, Any]:
    root = root.resolve()
    if not (root / "local").is_dir():
        raise ValueError("Ignored local/ staging and recovery directory required")
    if _sha(root / PDF) != SOURCE_SHA256:
        raise ValueError("N5.3 Command Module source PDF hash differs from reviewed bytes")
    active_rules = root / RULES
    existing = RulesDatabase(active_rules)
    existing.validate()
    already_published = IDENTITY in _all_ids(active_rules)
    if already_published and promote:
        raise ValueError("Command Token general rule already published; no second promotion")
    if not already_published:
        for relative in (RULES, OBJECTS):
            unchanged = subprocess.run(
                ["git", "diff", "--quiet", "HEAD", "--", relative.as_posix()],
                cwd=root, capture_output=True, check=False,
            )
            if unchanged.returncode != 0:
                raise ValueError(f"Tracked release artifact differs from HEAD: {relative}")
    previous = load_deployed_object_publication(root / OBJECTS, root / ARMY, active_rules)
    if previous is None:
        raise ValueError("Active rules/deployed-object release pair is not matched")
    documents = load_curated_directory(root / "data/curated/rules")
    matches = [
        row for _, document in documents for row in document["records"]
        if row["id"] == IDENTITY
    ]
    if len(matches) != 1:
        raise ValueError("Canonical Command Token definition is absent or duplicated")
    _check_record(matches[0])
    original_ids = _all_ids(active_rules)
    original_bytes = {relative: (root / relative).read_bytes() for relative in (RULES, OBJECTS)}
    source_digest = _sha(root / CURATED)
    with tempfile.TemporaryDirectory(prefix="command-tokens-v9-stage-", dir=root / "local") as temp:
        location = Path(temp)
        first, second = location / "first.db", location / "second.db"
        export_release_rules(documents, first, baseline=active_rules)
        export_release_rules(documents, second, baseline=active_rules)
        if _sha(first) != _sha(second):
            raise ValueError("Command Token release export is not byte deterministic")
        if already_published and _sha(first) != _sha(active_rules):
            raise ValueError("Published Command Token rules differ from deterministic rebuild")
        staged = RulesDatabase(first)
        staged.validate()
        if _all_ids(first) != (original_ids if already_published else original_ids | {IDENTITY}):
            raise ValueError("Command Token candidate changed existing record identities")
        _check_record(matches[0])
        result = staged.composed_record(IDENTITY)
        if result is None or result["summary"] != matches[0]["summary"]:
            raise ValueError("Command Token reference not published in candidate")
        for identity in sorted(original_ids):
            if existing.composed_record(identity) != staged.composed_record(identity):
                raise ValueError(f"Command Token candidate changes existing reference: {identity}")
        if existing.restrictions_payload() != staged.restrictions_payload():
            raise ValueError("Command Token reference changed source Restrictions")
        projected = build_publication(
            root / ARMY, first, root / CURATED, root / DELIVERY, root / CANDIDATES,
        )
        expected = json.loads(json.dumps(previous))
        expected["sourceSnapshot"]["rulesDatabaseSha256"] = _sha(first)
        expected["sourceSnapshot"]["curatedSourceSha256"] = source_digest
        if projected != expected:
            raise ValueError("Command Token reference changed unrelated deployed objects")
        if any((root / relative).read_bytes() != blob for relative, blob in original_bytes.items()):
            raise ValueError("Release pair changed during staging")
        if _sha(root / CURATED) != source_digest:
            raise ValueError("Curated source changed during staging")
        report = {
            "scope": "v1s-032a-command-tokens-reference",
            "candidateRecords": len(original_ids) + (not already_published),
            "alreadyPublished": already_published,
            "existingRecordsVerifiedUnchanged": len(original_ids),
            "schema": "v9",
            "deterministic": True,
            "matchedPublication": True,
            "sourcePdfSha256": SOURCE_SHA256,
            "candidateRulesSha256": _sha(first),
        }
        if not promote:
            return report

        def post_validate() -> None:
            new = RulesDatabase(root / RULES)
            new.validate()
            if new.composed_record(IDENTITY) != result:
                raise ValueError("Promoted Command Tokens record differs from staged")
            if load_deployed_object_publication(
                root / OBJECTS, root / ARMY, root / RULES,
            ) != projected:
                raise ValueError("Promoted Command Tokens pair is unmatched")

        backup = _replace_with_rollback(
            root,
            {RULES: first.read_bytes(), OBJECTS: publication_bytes(projected)},
            post_validate,
            backup_prefix="command-tokens-v9-recovery-",
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
