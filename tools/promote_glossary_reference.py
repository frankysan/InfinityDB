"""Guarded v9 publication of the five N5.3 glossary source corrections.

Default mode verifies a deterministic candidate without changing release assets.
--promote replaces the rules DB and both dependent publications as a checked batch,
retaining byte-for-byte recovery copies under ignored local/.
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
from infinity_db.variant_usage import build_variant_usage_projection
from infinity_db.variant_usage_reference import publication_from_candidate
from tools.audit_deployed_object_non_catalog_queue import audit_non_catalog_candidates
from tools.build_deployed_object_publication import build_publication, publication_bytes
from tools.promote_aro_deployment_reference import (
    ARMY,
    CANDIDATES,
    CURATED,
    DELIVERY,
    OBJECTS,
    ROOT,
    RULES,
)
from tools.release_rules_export import export_release_rules
from tools.restrictions_v9_release import _replace_with_rollback

RAW = Path("data/generated/infinity.raw.db")
USAGE = Path("data/generated/variant-usage.json")
PDFS = {
    Path("data/pdf/rules/n5-rules-v5-3-en.pdf"):
        "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f",
    Path("data/pdf/rules/esp-n5-update-5-3.pdf"):
        "7f564c864c6f26d6b218a0477c8afeba99da5c56e1a5369bb259f423689bb28f",
}
REQUIRED = {
    "term:deployable-equipment": ("Special Skill or Trait", "receive Attacks"),
    "term:deployable-weapon": ("may belong", "perform and receive Attacks"),
    "term:target": ("capable of being chosen", "Skills or Equipment"),
    "term:hostile": ("own Attributes", "Enemy by all players"),
    "term:neutral": ("has Attributes", "no player's Army List"),
}
EXPECTED_SECTION = {
    "term:deployable-equipment": "Terminology — Deployable Equipment",
    "term:deployable-weapon": "Terminology — Deployable Weapon",
    "term:target": "Terminology — Target",
    "term:hostile": "Alignment — Hostile",
    "term:neutral": "Alignment — Neutral",
}


def _sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _identities(path: Path) -> set[str]:
    with closing(sqlite3.connect(path)) as connection:
        return {row[0] for row in connection.execute("SELECT id FROM records")}


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def verify_candidate(root: Path = ROOT, *, promote: bool = False) -> dict[str, Any]:
    root = root.resolve()
    if not (root / "local").is_dir():
        raise ValueError("An ignored local/ recovery directory is required")
    for path, digest in PDFS.items():
        if _sha(root / path) != digest:
            raise ValueError(f"Pinned N5.3 source differs: {path}")
    for target in (RULES, USAGE):
        clean = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", target.as_posix()],
            cwd=root, capture_output=True, check=False,
        )
        if clean.returncode != 0:
            raise ValueError(f"Tracked release artifact is already modified: {target}")

    existing = RulesDatabase(root / RULES)
    existing.validate()
    old_ids = _identities(root / RULES)
    old_objects = load_deployed_object_publication(root / OBJECTS, root / ARMY, root / RULES)
    if old_objects is None:
        raise ValueError("Matched deployed-object baseline is required")
    original_usage = json.loads((root / USAGE).read_text(encoding="utf-8"))
    old_snapshot = original_usage["sourceSnapshot"]
    if (
        old_snapshot["rulesDatabaseSha256"] != _sha(root / RULES)
        or old_snapshot["deployedObjectPublicationSha256"] != _sha(root / OBJECTS)
    ):
        raise ValueError("Existing variant-usage publication is not release-matched")

    documents = load_curated_directory(root / "data/curated/rules")
    selected = [
        record for _, document in documents for record in document["records"]
        if record["id"] in REQUIRED
    ]
    if len(selected) != len(REQUIRED) or {r["id"] for r in selected} != set(REQUIRED):
        raise ValueError("Missing or duplicate glossary owners")
    for record in selected:
        identity = record["id"]
        if (
            record["kind"] != "term"
            or record["composition"] != {"role": "definition"}
            or record["scope"] != {"game": "N5", "seasons": ["current"]}
            or record["review"] != {"status": "reviewed", "reviewedOn": "2026-11-06"}
            or record["citations"] != [{
                "sourceId": "n5-core-v5.3-pdf",
                "page": 173,
                "section": EXPECTED_SECTION[identity],
            }]
            or any(clause not in record["summary"] for clause in REQUIRED[identity])
        ):
            raise ValueError(f"Unreviewed glossary owner drift: {identity}")

    provenance = audit_non_catalog_candidates(
        root / CURATED,
        root / "config/validation/deployed-object-non-catalog-reviews.json",
    )
    if provenance["unreviewed"]:
        raise ValueError("Unreviewed deployed-object classification after glossary edit")
    baseline = {key: (root / key).read_bytes() for key in (RULES, OBJECTS, USAGE)}
    curated_digest = _sha(root / CURATED)
    with tempfile.TemporaryDirectory(prefix="glossary-v9-", dir=root / "local") as tmp:
        stage = Path(tmp)
        first, second = stage / "first.db", stage / "second.db"
        export_release_rules(documents, first, baseline=root / RULES)
        export_release_rules(documents, second, baseline=root / RULES)
        if _sha(first) != _sha(second) or _identities(first) != old_ids:
            raise ValueError("Non-deterministic rebuild or changed record identities")
        staged = RulesDatabase(first)
        staged.validate()
        if staged.restrictions_payload() != existing.restrictions_payload():
            raise ValueError("Typed Restrictions changed")
        for identity in sorted(old_ids - set(REQUIRED)):
            if staged.composed_record(identity) != existing.composed_record(identity):
                raise ValueError(f"Unrelated composed rule changed: {identity}")
        changed = []
        for record in selected:
            candidate = staged.composed_record(record["id"])
            if candidate is None or any(
                candidate[key] != record[key] for key in ("summary", "facts")
            ):
                raise ValueError(f"Reviewed glossary did not publish: {record['id']}")
            baseline_record = existing.composed_record(record["id"])
            if baseline_record is None:
                raise ValueError(f"Missing previous glossary record: {record['id']}")
            changed.append(baseline_record["summary"] != candidate["summary"])
        if any(changed) and not all(changed):
            raise ValueError("Partially published glossary changes")
        already_published = not any(changed)
        if already_published:
            if promote:
                raise ValueError("Glossary corrections are already published")
            if _sha(first) != _sha(root / RULES):
                raise ValueError("Published rules DB differs from deterministic candidate")

        candidate_objects = build_publication(
            root / ARMY, first, root / CURATED, root / DELIVERY, root / CANDIDATES
        )
        expected_objects = json.loads(json.dumps(old_objects))
        expected_objects["sourceSnapshot"]["rulesDatabaseSha256"] = _sha(first)
        expected_objects["sourceSnapshot"]["curatedSourceSha256"] = curated_digest
        if candidate_objects != expected_objects:
            raise ValueError("Unrelated deployed-object content changed")
        object_file = stage / "objects.json"
        object_file.write_bytes(publication_bytes(candidate_objects))
        candidate_usage = publication_from_candidate(build_variant_usage_projection(
            root / ARMY, root / RAW, first, object_file,
        ))
        expected_usage = json.loads(json.dumps(original_usage))
        expected_usage["sourceSnapshot"]["rulesDatabaseSha256"] = _sha(first)
        expected_usage["sourceSnapshot"]["deployedObjectPublicationSha256"] = _sha(object_file)
        if candidate_usage != expected_usage:
            raise ValueError("Unrelated variant-usage content changed")
        usage_bytes = _json_bytes(candidate_usage)
        if _sha(root / CURATED) != curated_digest or any(
            (root / key).read_bytes() != data for key, data in baseline.items()
        ):
            raise ValueError("Source or release inputs changed during staging")
        report: dict[str, Any] = {
            "scope": "v1s-082-glossary",
            "changedRecords": [] if already_published else sorted(REQUIRED),
            "alreadyPublished": already_published,
            "unchangedRecordsVerified": len(old_ids - set(REQUIRED)),
            "candidateRulesSha256": _sha(first),
            "candidateObjectsSha256": _sha(object_file),
            "candidateUsageSha256": hashlib.sha256(usage_bytes).hexdigest(),
            "matchedPair": True,
            "deterministic": True,
            "promoted": False,
        }
        if not promote:
            return report

        def post_validate() -> None:
            RulesDatabase(root / RULES).validate()
            checked_objects = load_deployed_object_publication(
                root / OBJECTS, root / ARMY, root / RULES,
            )
            if checked_objects != candidate_objects:
                raise ValueError("Promoted deployed-object publication mismatch")
            check_usage = publication_from_candidate(build_variant_usage_projection(
                root / ARMY, root / RAW, root / RULES, root / OBJECTS,
            ))
            if check_usage != candidate_usage or (root / USAGE).read_bytes() != usage_bytes:
                raise ValueError("Promoted variant-usage publication mismatch")

        recovery = _replace_with_rollback(
            root,
            {RULES: first.read_bytes(), OBJECTS: object_file.read_bytes(), USAGE: usage_bytes},
            post_validate,
            backup_prefix="glossary-v9-recovery-",
        )
        report.update(promoted=True, recoveryPath=str(recovery.relative_to(root)))
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify_candidate(promote=args.promote), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
