"""Stage or promote the reviewed V1S-033B geometry reference as a matched v9 pair.

Default mode is read-only. --promote retains verified recovery bytes and rolls
back both release artifacts if replacement or post-validation fails.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import RulesDatabase
from tools.build_deployed_object_publication import build_publication, publication_bytes
from tools.promote_aro_deployment_reference import (
    ARMY,
    CANDIDATES,
    CURATED,
    DELIVERY,
    OBJECTS,
    PDF,
    ROOT,
    RULES,
    SOURCE_SHA256,
    _digest,
    _ids,
)
from tools.release_rules_export import (
    export_release_rules,
    load_release_deployed_objects,
    same_logical_rules_contents,
)
from tools.restrictions_v9_release import _replace_with_rollback

NEW_IDS = {
    "rule:line-of-fire", "rule:zone-of-control", "rule:zones-and-contact",
    "rule:coherency", "rule:distances-and-measurements", "rule:replacing-game-elements",
}
CHANGED_IDS = {"attribute:s", "rule:general-movement"}
CITATIONS = {
    "rule:line-of-fire": {18, 19},
    "rule:zone-of-control": {20},
    "rule:zones-and-contact": {20, 21},
    "rule:coherency": {21},
    "rule:distances-and-measurements": {21, 22},
    "rule:replacing-game-elements": {22},
    "attribute:s": {9, 18},
    "rule:general-movement": {29, 30},
}

def verify_candidate(root: Path = ROOT, *, promote: bool = False) -> dict[str, Any]:
    root = root.resolve()
    if not (root / "local").is_dir() or _digest(root / PDF) != SOURCE_SHA256:
        raise ValueError("Pinned N5.3 PDF and ignored recovery directory are required")
    active = root / RULES
    existing = RulesDatabase(active)
    existing.validate()
    old_ids = _ids(active)
    present = old_ids & NEW_IDS
    if present and present != NEW_IDS:
        raise ValueError("Partial geometry publication is not a supported baseline")
    published = present == NEW_IDS
    if published and promote:
        raise ValueError("Already published; repeated geometry promotion is forbidden")
    if not published and subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", RULES.as_posix()],
        cwd=root, capture_output=True, check=False,
    ).returncode != 0:
        raise ValueError("Tracked rules database differs from HEAD")
    previous = load_release_deployed_objects(root / OBJECTS, root / ARMY, active)
    if previous is None:
        raise ValueError("Active rules/deployed-object publication does not match")
    documents = load_curated_directory(root / "data/curated/rules")
    selected = {
        record["id"]: record for _, doc in documents for record in doc["records"]
        if record["id"] in CITATIONS
    }
    if set(selected) != set(CITATIONS):
        raise ValueError("Geometry reference owners are missing")
    for identity, record in selected.items():
        if (
            record["kind"] != identity.partition(":")[0]
            or record["scope"] != {"game": "N5", "seasons": ["current"]}
            or record["composition"] != {"role": "definition"}
            or {c["page"] for c in record["citations"]
                if c["sourceId"] == "n5-core-v5.3-pdf"} != CITATIONS[identity]
        ):
            raise ValueError(f"Geometry identity, scope or citation drift: {identity}")
    original = {
        name: (root / name).read_bytes() if (root / name).is_file() else None
        for name in (RULES, OBJECTS)
    }
    source_hash = _digest(root / CURATED)
    with tempfile.TemporaryDirectory(prefix="geometry-v9-", dir=root / "local") as tmp:
        first, second = Path(tmp) / "first.db", Path(tmp) / "second.db"
        export_release_rules(documents, first, baseline=active)
        export_release_rules(documents, second, baseline=active)
        if _digest(first) != _digest(second):
            raise ValueError("Non-deterministic geometry rules export")
        staged = RulesDatabase(first)
        staged.validate()
        if _ids(first) != old_ids | NEW_IDS:
            raise ValueError("Candidate changed prior record identities")
        unchanged_ids = old_ids - CHANGED_IDS
        for identity in sorted(unchanged_ids):
            if existing.composed_record(identity) != staged.composed_record(identity):
                raise ValueError(f"Unrelated rule changed: {identity}")
        for identity, curated in selected.items():
            result = staged.composed_record(identity)
            if result is None or any(
                result[key] != curated[key] for key in ("summary", "facts")
            ):
                raise ValueError(f"Geometry source facts did not publish: {identity}")
        byte_match = _digest(first) == _digest(active)
        logical_match = byte_match or same_logical_rules_contents(active, first)
        if published and not logical_match:
            raise ValueError("Published geometry rules differ from reviewed rebuild")
        projection = build_publication(
            root / ARMY, first, root / CURATED, root / DELIVERY, root / CANDIDATES,
        )
        expected = json.loads(json.dumps(previous))
        expected["sourceSnapshot"]["rulesDatabaseSha256"] = _digest(first)
        expected["sourceSnapshot"]["curatedSourceSha256"] = source_hash
        if projection != expected:
            raise ValueError("Unrelated deployed-object publication changed")
        if source_hash != _digest(root / CURATED) or any(
            ((root / name).read_bytes() if (root / name).is_file() else None) != content
            for name, content in original.items()
        ):
            raise ValueError("Geometry source or publication changed during staging")
        report = {
            "scope": "v1s-033b-geometry", "alreadyPublished": published,
            "deterministic": True, "matchedPublication": True,
            "existingRecordsVerifiedUnchanged": len(unchanged_ids),
            "candidateRecords": len(old_ids | NEW_IDS),
            "candidateRulesSha256": _digest(first),
            "publishedRulesSha256": _digest(active) if published else None,
            "logicallyEquivalentWithPublished": logical_match if published else None,
        }
        if not promote:
            return report

        def post_validate() -> None:
            current = RulesDatabase(active)
            current.validate()
            if any(current.composed_record(i) != staged.composed_record(i) for i in selected):
                raise ValueError("Promoted geometry records do not match staged source")
            if load_release_deployed_objects(
                root / OBJECTS, root / ARMY, active,
            ) != projection:
                raise ValueError("Promoted geometry publication pair does not match")

        backup = _replace_with_rollback(
            root, {RULES: first.read_bytes(), OBJECTS: publication_bytes(projection)},
            post_validate, backup_prefix="geometry-v9-recovery-",
        )
        report.update(promoted=True, recoveryPath=str(backup.relative_to(root)))
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify_candidate(promote=args.promote), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
