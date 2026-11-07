"""Safely refresh an existing v9 rules summary after paragraph-only curation.

This reusable maintenance gate refuses semantic edits, changed reference records,
unmatched release inputs, and changes to dependent publication contents.
Default verification never mutates tracked artifacts; --promote uses rollback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_directory
from infinity_db.deployed_object_publication import load_deployed_object_publication
from infinity_db.rules_database import RulesDatabase
from infinity_db.variant_usage import build_variant_usage_projection
from infinity_db.variant_usage_reference import publication_from_candidate
from tools.build_deployed_object_publication import build_publication, publication_bytes
from tools.promote_hackable_profile_help import (
    ARMY,
    CANDIDATES,
    CURATED,
    DELIVERY,
    OBJECTS,
    RAW,
    ROOT,
    RULES,
    USAGE,
    digest,
    identities,
    usage_bytes,
)
from tools.release_rules_export import export_release_rules
from tools.restrictions_v9_release import _replace_with_rollback


def normalized_summary(value: str) -> str:
    """Compare semantic text while permitting whitespace-only paragraph layout."""
    return " ".join(value.split())


def verify_candidate(
    record_id: str, *, root: Path = ROOT, promote: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    if not record_id.startswith(("rule:", "skill:", "trait:", "equipment:")):
        raise ValueError("Only curated rules-domain records support summary-layout refresh")
    if not (root / "local").is_dir():
        raise ValueError("Ignored local/ recovery directory is required")
    for relative in (RULES, USAGE):
        if subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", relative.as_posix()],
            cwd=root, capture_output=True, check=False,
        ).returncode != 0:
            raise ValueError(f"Release artifact is not clean against HEAD: {relative}")

    documents = load_curated_directory(root / "data/curated/rules")
    authored = [
        record for _, document in documents for record in document["records"]
        if record["id"] == record_id
    ]
    if len(authored) != 1:
        raise ValueError("Record must have exactly one current curated owner")
    authored_summary = authored[0].get("summary")
    if not isinstance(authored_summary, str) or "\n\n" not in authored_summary:
        raise ValueError("Authored summary must contain a real paragraph break")

    baseline = {p: (root / p).read_bytes() for p in (RULES, OBJECTS, USAGE)}
    old_db = RulesDatabase(root / RULES)
    old_db.validate()
    old_ids = identities(root / RULES)
    previous_objects = load_deployed_object_publication(
        root / OBJECTS, root / ARMY, root / RULES,
    )
    if previous_objects is None:
        raise ValueError("Current deployed-object publication is not release-matched")
    previous_usage = json.loads(baseline[USAGE])
    if (
        previous_usage["sourceSnapshot"]["rulesDatabaseSha256"] != digest(root / RULES)
        or previous_usage["sourceSnapshot"]["deployedObjectPublicationSha256"]
        != digest(root / OBJECTS)
    ):
        raise ValueError("Current variant-usage publication is not release-matched")
    source_hash = digest(root / CURATED)
    before = old_db.composed_record(record_id)
    if before is None:
        raise ValueError("Target record absent from current database")
    if before["summary"] == authored_summary:
        raise ValueError("Summary layout is already published")
    if normalized_summary(before["summary"]) != normalized_summary(authored_summary):
        raise ValueError("Summary contains semantic text changes, not just whitespace")

    with tempfile.TemporaryDirectory(prefix="rules-layout-v9-", dir=root / "local") as tmp:
        stage = Path(tmp)
        first, second = stage / "rules-a.db", stage / "rules-b.db"
        export_release_rules(documents, first, baseline=root / RULES)
        export_release_rules(documents, second, baseline=root / RULES)
        if digest(first) != digest(second) or identities(first) != old_ids:
            raise ValueError("Non-deterministic export or changed record identities")
        next_db = RulesDatabase(first)
        next_db.validate()
        for identity in sorted(old_ids - {record_id}):
            if old_db.composed_record(identity) != next_db.composed_record(identity):
                raise ValueError(f"Unrelated composed record drift: {identity}")
        after = next_db.composed_record(record_id)
        if after is None or after["summary"] != authored_summary:
            raise ValueError("New summary not reflected in exported rules database")
        for key, value in before.items():
            if key != "summary" and after.get(key) != value:
                raise ValueError(f"Unrelated field changed on target record: {key}")

        objects = build_publication(
            root / ARMY, first, root / CURATED, root / DELIVERY, root / CANDIDATES,
        )
        expected_objects = json.loads(json.dumps(previous_objects))
        expected_objects["sourceSnapshot"]["rulesDatabaseSha256"] = digest(first)
        expected_objects["sourceSnapshot"]["curatedSourceSha256"] = source_hash
        if objects != expected_objects:
            raise ValueError("Deployed-object content changed beyond source fingerprints")
        staged_objects = stage / "deployed-objects.json"
        staged_objects.write_bytes(publication_bytes(objects))
        usage = publication_from_candidate(build_variant_usage_projection(
            root / ARMY, root / RAW, first, staged_objects,
        ))
        expected_usage = json.loads(json.dumps(previous_usage))
        expected_usage["sourceSnapshot"]["rulesDatabaseSha256"] = digest(first)
        expected_usage["sourceSnapshot"]["deployedObjectPublicationSha256"] = digest(
            staged_objects
        )
        if usage != expected_usage:
            raise ValueError("Variant-usage content changed beyond source fingerprints")
        usage_data = usage_bytes(usage)
        if source_hash != digest(root / CURATED) or any(
            (root / path).read_bytes() != original for path, original in baseline.items()
        ):
            raise ValueError("Release inputs changed during staging")

        report = {
            "record": record_id,
            "scope": "summary-whitespace-only",
            "unchangedRecords": len(old_ids) - 1,
            "deterministic": True,
            "rulesSha256": digest(first),
            "deployedObjectsSha256": digest(staged_objects),
            "variantUsageSha256": hashlib.sha256(usage_data).hexdigest(),
            "promoted": False,
        }
        if not promote:
            return report

        def post_validate() -> None:
            actual = RulesDatabase(root / RULES)
            actual.validate()
            if actual.composed_record(record_id) != after:
                raise ValueError("Promoted summary differs from staged candidate")
            if load_deployed_object_publication(
                root / OBJECTS, root / ARMY, root / RULES,
            ) != objects:
                raise ValueError("Promoted deployed-object publication is not matched")
            if (
                (root / USAGE).read_bytes() != usage_data
                or publication_from_candidate(build_variant_usage_projection(
                    root / ARMY, root / RAW, root / RULES, root / OBJECTS,
                )) != usage
            ):
                raise ValueError("Promoted variant-usage publication is not matched")

        backup = _replace_with_rollback(
            root,
            {RULES: first.read_bytes(), OBJECTS: staged_objects.read_bytes(), USAGE: usage_data},
            post_validate,
            backup_prefix="rules-layout-v9-recovery-",
        )
        report.update(promoted=True, recoveryPath=str(backup.relative_to(root)))
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record_id", help="one exact current curated record identity")
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify_candidate(args.record_id, promote=args.promote), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
