"""Guarded deterministic publication of the N5.3 Game Sequence and Order Pool.

Without --promote: verify a complete matched candidate, with no tracked writes.
With --promote: replace the rules database and ignored deployed-object publication
as one rollback-protected pair. Existing composed references must remain identical.
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
EN = Path("data/pdf/rules/n5-rules-v5-3-en.pdf")
ES = Path("data/pdf/rules/esp-n5-update-5-3.pdf")
SHA_EN = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
SHA_ES = "7f564c864c6f26d6b218a0477c8afeba99da5c56e1a5369bb259f423689bb28f"
IDENTITIES = frozenset({"rule:game-sequence", "rule:order-pool"})
CITATIONS = {
    "rule:game-sequence": {
        ("n5-core-v5.3-pdf", 16), ("n5-core-v5.3-pdf", 17),
    },
    "rule:order-pool": {
        ("n5-core-v5.3-pdf", 11), ("n5-core-v5.3-pdf", 12),
        ("n5-core-v5.3-pdf", 16), ("n5-core-v5.3-pdf", 17),
        ("n5-core-v5.3-es-pdf", 17),
    },
}
CLAUSES = {
    "rule:game-sequence": (
        "two Player Turns", "Tactical Phase", "Impetuous",
        "Orders Phase", "States", "End of the Turn",
        "Executive Use", "Order Count", "Loss of Lieutenant",
        "both players", "do not generate", "carry-over",
    ),
    "rule:order-pool": (
        "Regular Order Pool", "Combat Group", "Order Count",
        "Regular Order contribution", "Irregular Order contribution",
        "Special", "Tactical Order contribution", "not in a Null",
        "SRC-031", "Teniente en estado no Nulo", "repeatedly",
        "Open Information", "Private Information", "unspent",
    ),
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _all_ids(path: Path) -> set[str]:
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        return {row[0] for row in db.execute("SELECT DISTINCT id FROM records")}


def _source_check(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    selected = {row["id"]: row for row in records if row["id"] in IDENTITIES}
    if len(selected) != 2 or len([
        row for row in records if row["id"] in IDENTITIES
    ]) != 2:
        raise ValueError("Game Sequence and Order Pool must have one canonical definition each")
    for identity in sorted(IDENTITIES):
        rec = selected[identity]
        if (
            rec["kind"] != "rule"
            or rec["composition"] != {"role": "definition"}
            or rec["scope"] != {"game": "N5", "seasons": ["current"]}
            or rec["facts"]["category"] != "basic-rule"
            or {(x["sourceId"], x["page"]) for x in rec["citations"]} != CITATIONS[identity]
        ):
            raise ValueError(f"{identity}: source, type, role or citation drift")
        joined = " ".join(
            [rec["summary"]]
            + [
                value
                for key in (
                    "requirements", "effects", "restrictions",
                    "sourceNotes", "clarifications",
                )
                for value in rec["facts"].get(key, [])
            ]
        )
        for term in CLAUSES[identity]:
            if term.casefold() not in joined.casefold():
                raise ValueError(f"{identity}: missing source-backed clause {term!r}")
    if len(selected["rule:game-sequence"]["facts"]["effects"]) != 5:
        raise ValueError("Game Sequence must retain five separately ordered phase effects")
    if "SRC-031" not in selected["rule:order-pool"]["facts"]["sourceNotes"][0]:
        raise ValueError("Publisher source discrepancy disclosure is missing")
    return selected


def verify_candidate(
    root: Path = ROOT, *, promote: bool = False, refresh: bool = False
) -> dict[str, Any]:
    root = root.resolve()
    if not (root / "local").is_dir():
        raise ValueError("Ignored local/ staging and recovery directory required")
    if _sha(root / EN) != SHA_EN or _sha(root / ES) != SHA_ES:
        raise ValueError("Pinned bilingual N5.3 Core source hashes differ")
    active_rules = root / RULES
    existing = RulesDatabase(active_rules)
    existing.validate()
    old_ids = _all_ids(active_rules)
    already = IDENTITIES & old_ids
    if already and already != IDENTITIES:
        raise ValueError("Partial publication of two inseparable phase references")
    if refresh and (not promote or already != IDENTITIES):
        raise ValueError("Refresh requires --promote and both published references")
    if promote and already and not refresh:
        raise ValueError("References already published; use --refresh for bounded corrections")
    if not already:
        completed = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", RULES.as_posix()],
            cwd=root, capture_output=True, check=False,
        )
        if completed.returncode != 0:
            raise ValueError("Tracked rules database differs from HEAD")
    old_publication = load_deployed_object_publication(
        root / OBJECTS, root / ARMY, active_rules
    )
    if old_publication is None:
        raise ValueError("Source rules/deployed-object pair is unmatched")
    docs = load_curated_directory(root / "data/curated/rules")
    selected = _source_check([
        record for _, document in docs for record in document["records"]
    ])
    curated_hash = _sha(root / CURATED)
    old_bytes = {rel: (root / rel).read_bytes() for rel in (RULES, OBJECTS)}
    with tempfile.TemporaryDirectory(prefix="turn-sequence-v9-", dir=root / "local") as tmp:
        first, second = Path(tmp) / "one.db", Path(tmp) / "two.db"
        export_release_rules(docs, first, baseline=active_rules)
        export_release_rules(docs, second, baseline=active_rules)
        if _sha(first) != _sha(second):
            raise ValueError("Game Sequence release export is not deterministic")
        if already and not refresh and _sha(first) != _sha(active_rules):
            raise ValueError("Published rules differ from deterministic rebuild")
        staged = RulesDatabase(first)
        staged.validate()
        if _all_ids(first) != old_ids | IDENTITIES:
            raise ValueError("Candidate changed existing rule identities")
        for identity in sorted(old_ids - (IDENTITIES if refresh else set())):
            if existing.composed_record(identity) != staged.composed_record(identity):
                raise ValueError(f"Candidate changed existing composed reference {identity}")
        for identity, authored in selected.items():
            saved = staged.composed_record(identity)
            if (
                saved is None
                or saved["summary"] != authored["summary"]
                or saved["facts"] != authored["facts"]
            ):
                raise ValueError(f"Candidate did not preserve full {identity} source prose")
        if staged.restrictions_payload() != existing.restrictions_payload():
            raise ValueError("Candidate modified existing typed Restrictions")
        candidate_publication = build_publication(
            root / ARMY, first, root / CURATED, root / DELIVERY, root / CANDIDATES
        )
        expected = json.loads(json.dumps(old_publication))
        expected["sourceSnapshot"]["rulesDatabaseSha256"] = _sha(first)
        expected["sourceSnapshot"]["curatedSourceSha256"] = curated_hash
        if candidate_publication != expected:
            raise ValueError("Candidate changed unrelated deployed-object publication data")
        if any((root / rel).read_bytes() != data for rel, data in old_bytes.items()):
            raise ValueError("Active release pair changed during staging")
        if curated_hash != _sha(root / CURATED):
            raise ValueError("Curated source changed during staging")
        report = {
            "slice": "V1S-032C1",
            "identities": sorted(IDENTITIES),
            "existingRecordsUnchanged": len(old_ids - (IDENTITIES if refresh else set())),
            "refreshedExistingReferences": bool(refresh),
            "candidateRecords": len(old_ids | IDENTITIES),
            "alreadyPublished": bool(already),
            "deterministic": True,
            "matchedPublication": True,
            "sourceEnglishSha256": SHA_EN,
            "sourceSpanishSha256": SHA_ES,
            "candidateRulesSha256": _sha(first),
        }
        if not promote:
            return report

        def post_validate() -> None:
            current = RulesDatabase(root / RULES)
            current.validate()
            for identity, authored in selected.items():
                saved = current.composed_record(identity)
                if saved is None or saved["facts"] != authored["facts"]:
                    raise ValueError(f"Promoted {identity} differs from candidate")
            if load_deployed_object_publication(
                root / OBJECTS, root / ARMY, root / RULES
            ) != candidate_publication:
                raise ValueError("Promoted rules and deployed-object pair is unmatched")

        backup = _replace_with_rollback(
            root, {RULES: first.read_bytes(), OBJECTS: publication_bytes(candidate_publication)},
            post_validate, backup_prefix="turn-sequence-v9-recovery-"
        )
        report["promoted"] = True
        report["recoveryPath"] = str(backup.relative_to(root))
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify_candidate(promote=args.promote, refresh=args.refresh), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
