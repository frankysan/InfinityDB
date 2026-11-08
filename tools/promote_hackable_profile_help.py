"""Guarded, source-pinned v9 publication of the Hackable profile-help correction.

Verification is read-only. --promote replaces the exact matched rules and two
dependent publications with rollback copies under ignored local/.
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

from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import RulesDatabase
from infinity_db.variant_usage import build_variant_usage_projection
from infinity_db.variant_usage_reference import publication_from_candidate
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
from tools.release_rules_export import export_release_rules, load_release_deployed_objects
from tools.restrictions_v9_release import _replace_with_rollback

RAW = Path("data/generated/infinity.raw.db")
USAGE = Path("data/generated/variant-usage.json")
RECORD_ID = "rule:profile-help:hackable"
SOURCE_PINS = {
    "data/pdf/rules/n5-rules-v5.3-en.pdf":
        "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f",
    "data/pdf/rules/n5-rules-v5.3-es.pdf":
        "7f564c864c6f26d6b218a0477c8afeba99da5c56e1a5369bb259f423689bb28f",
}
CITATIONS = [
    {"sourceId": "n5-core-v5.3-pdf", "page": 8, "section": "Trooper Characteristics"},
    {"sourceId": "n5-core-v5.3-es-pdf", "page": 9, "section": "Características de las Tropas"},
]
REQUIRED = (
    "HI, REM, TAG, and VH", "unless otherwise stated",
    "[[skill:hacker:plural|Hackers]]", "regardless of Troop Type",
    "Allied and enemy", "each Program's own target requirements",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identities(path: Path) -> set[str]:
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        return {row[0] for row in connection.execute("SELECT id FROM records")}


def usage_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def verify_candidate(*, root: Path = ROOT, promote: bool = False) -> dict:
    root = root.resolve()
    if not (root / "local").is_dir():
        raise ValueError("Ignored local/ recovery directory required")
    for relative, expected in SOURCE_PINS.items():
        if digest(root / relative) != expected:
            raise ValueError(f"Pinned bilingual source mismatch: {relative}")
    for relative in (RULES, OBJECTS, USAGE):
        result = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", relative.as_posix()],
            cwd=root, capture_output=True, check=False,
        )
        if result.returncode != 0:
            raise ValueError(f"Release artifact is not clean against HEAD: {relative}")

    documents = load_curated_directory(root / "data/curated/rules")
    selected = [
        record for _, document in documents for record in document["records"]
        if record["id"] == RECORD_ID
    ]
    if len(selected) != 1:
        raise ValueError("Hackable profile-help owner must be unique")
    authored = selected[0]
    if (
        authored["kind"] != "rule"
        or authored["composition"] != {"role": "definition"}
        or authored["scope"] != {"game": "N5", "seasons": ["current"]}
        or authored["facts"] != {"category": "unit-profile-help", "key": "hackable", "order": 70}
        or authored["citations"] != CITATIONS
        or authored["review"] != {"status": "reviewed", "reviewedOn": "2026-11-06"}
        or any(clause not in authored["summary"] for clause in REQUIRED)
    ):
        raise ValueError("Hackable reference or source review drift")

    baseline = {path: (root / path).read_bytes() for path in (RULES, OBJECTS, USAGE)}
    original = RulesDatabase(root / RULES)
    original.validate()
    old_ids = identities(root / RULES)
    old_objects = load_release_deployed_objects(root / OBJECTS, root / ARMY, root / RULES)
    if old_objects is None:
        raise ValueError("Existing deployed-object publication is not matched")
    old_usage = json.loads(baseline[USAGE])
    if (
        old_usage["sourceSnapshot"]["rulesDatabaseSha256"] != digest(root / RULES)
        or old_usage["sourceSnapshot"]["deployedObjectPublicationSha256"] != digest(root / OBJECTS)
    ):
        raise ValueError("Existing variant-usage publication is not matched")

    source_hash = digest(root / CURATED)
    with tempfile.TemporaryDirectory(prefix="hackable-profile-v9-", dir=root / "local") as temp:
        stage = Path(temp)
        first, second = stage / "first.db", stage / "second.db"
        export_release_rules(documents, first, baseline=root / RULES)
        export_release_rules(documents, second, baseline=root / RULES)
        if digest(first) != digest(second) or identities(first) != old_ids:
            raise ValueError("Non-deterministic candidate or identity drift")
        candidate = RulesDatabase(first)
        candidate.validate()
        if candidate.restrictions_payload() != original.restrictions_payload():
            raise ValueError("Restrictions changed")
        for identity in sorted(old_ids - {RECORD_ID}):
            if candidate.composed_record(identity) != original.composed_record(identity):
                raise ValueError(f"Unrelated record changed: {identity}")
        before = original.composed_record(RECORD_ID)
        after = candidate.composed_record(RECORD_ID)
        if before is None or after is None or after["summary"] != authored["summary"]:
            raise ValueError("Hackable summary not published")
        for key, value in before.items():
            if key not in {"summary", "citations", "review"} and after.get(key) != value:
                raise ValueError(f"Unrelated Hackable record field changed: {key}")
        if promote and before["summary"] == after["summary"]:
            raise ValueError("Hackable correction already published")

        projected = build_publication(
            root / ARMY, first, root / CURATED, root / DELIVERY, root / CANDIDATES,
        )
        expected_objects = json.loads(json.dumps(old_objects))
        expected_objects["sourceSnapshot"]["rulesDatabaseSha256"] = digest(first)
        expected_objects["sourceSnapshot"]["curatedSourceSha256"] = source_hash
        if projected != expected_objects:
            raise ValueError("Unrelated deployed-object payload changed")
        object_file = stage / "deployed-objects.json"
        object_file.write_bytes(publication_bytes(projected))
        projected_usage = publication_from_candidate(build_variant_usage_projection(
            root / ARMY, root / RAW, first, object_file,
        ))
        expected_usage = json.loads(json.dumps(old_usage))
        expected_usage["sourceSnapshot"]["rulesDatabaseSha256"] = digest(first)
        expected_usage["sourceSnapshot"]["deployedObjectPublicationSha256"] = digest(object_file)
        if projected_usage != expected_usage:
            raise ValueError("Unrelated variant-usage payload changed")
        usage_data = usage_bytes(projected_usage)
        if source_hash != digest(root / CURATED) or any(
            (root / path).read_bytes() != content for path, content in baseline.items()
        ):
            raise ValueError("Inputs changed while preparing the candidate")

        report = {
            "record": RECORD_ID,
            "changedSummary": before["summary"] != after["summary"],
            "unchangedRecords": len(old_ids) - 1,
            "sourcePinsVerified": len(SOURCE_PINS),
            "schemaAndRestrictionsPreserved": True,
            "deterministic": True,
            "matchedPublications": True,
            "rulesSha256": digest(first),
            "deployedObjectsSha256": digest(object_file),
            "variantUsageSha256": hashlib.sha256(usage_data).hexdigest(),
            "promoted": False,
        }
        if not promote:
            return report

        def post_validate() -> None:
            current = RulesDatabase(root / RULES)
            current.validate()
            if current.composed_record(RECORD_ID) != after:
                raise ValueError("Promoted Hackable record mismatch")
            if load_release_deployed_objects(
                root / OBJECTS, root / ARMY, root / RULES,
            ) != projected:
                raise ValueError("Promoted deployed-object publication mismatch")
            if (
                publication_from_candidate(build_variant_usage_projection(
                    root / ARMY, root / RAW, root / RULES, root / OBJECTS,
                )) != projected_usage
                or (root / USAGE).read_bytes() != usage_data
            ):
                raise ValueError("Promoted variant-usage publication mismatch")

        recovery = _replace_with_rollback(
            root,
            {RULES: first.read_bytes(), OBJECTS: object_file.read_bytes(), USAGE: usage_data},
            post_validate,
            backup_prefix="hackable-profile-v9-recovery-",
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
