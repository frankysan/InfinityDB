"""Historical staged-pair verifier retained only for old source-review tests.

The standalone command has been retired. Maintained builds use the selected
database-set health check; legacy helper removal follows the P2.5 test cleanup.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from infinity_db.deployed_object_publication import load_deployed_object_publication
from infinity_db.rules_database import RulesDatabase
from tools.release_rules_export import RELEASE_RULES, release_deployed_object_bytes

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_PUBLICATION = ROOT / "data/generated/deployed-objects.json"
ARMY_DB = ROOT / "data/generated/infinity.db"
CURATED = ROOT / "data/curated/rules/n5-core-v5.3.json"
REPORT_NAMES = ("migration-report.json", "staging-report.json")
ACCEPTED_SCOPES = {
    "staged-artifacts-only-not-applied-or-committed",
    "staged-only-no-checkout-modification",
    "post-promotion-binary-rebuild-not-applied",
}
GENERATED_PATHS = {
    "rulesDatabase": "data/generated/rules.db",
    "deployedObjects": "data/generated/deployed-objects.json",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_staged_release_pair(
    directory: Path,
    *,
    active_rules: Path = RELEASE_RULES,
    active_publication: Path = ACTIVE_PUBLICATION,
    army_db: Path = ARMY_DB,
    curated_path: Path = CURATED,
) -> dict[str, Any]:
    """Fail closed on a stale baseline, mutated candidate or mismatched schema pair."""
    if directory.is_symlink():
        raise ValueError("Staging directory may not be a symlink")
    stage = directory.resolve(strict=True)
    reports = [stage / name for name in REPORT_NAMES if (stage / name).is_file()]
    if len(reports) != 1 or any(path.is_symlink() for path in reports):
        raise ValueError("Exactly one safe staging report is required")
    report = json.loads(reports[0].read_text(encoding="utf-8"))
    if report.get("scope") not in ACCEPTED_SCOPES:
        raise ValueError("Unexpected staging report scope")
    baseline = report.get("releaseBaselineSha256")
    candidates = report.get("stagedSha256")
    if (
        not isinstance(baseline, dict) or set(baseline) != set(GENERATED_PATHS)
        or not isinstance(candidates, dict)
        or not set(GENERATED_PATHS).issubset(candidates)
        or not isinstance(report.get("stagedPaths"), list)
        or any(relative not in report["stagedPaths"] for relative in GENERATED_PATHS.values())
    ):
        raise ValueError("Staging report lacks current-pair provenance; rebuild the stage")
    for key, source in (
        ("rulesDatabase", active_rules),
        ("deployedObjects", active_publication),
    ):
        digest = (
            hashlib.sha256(release_deployed_object_bytes(source)).hexdigest()
            if key == "deployedObjects" else sha256(source)
        )
        if digest != baseline[key]:
            raise ValueError(f"Release baseline changed since staging: {key}")
    source_digest = report.get("curatedSourceSha256", report.get("sourceSha256"))
    if not isinstance(source_digest, str) or sha256(curated_path) != source_digest:
        raise ValueError("Curated source changed since staging")
    staged: dict[str, Path] = {}
    for key, relative in GENERATED_PATHS.items():
        path = stage / relative
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(stage):
            raise ValueError(f"Unsafe or missing staged artifact: {relative}")
        if sha256(path) != candidates[key]:
            raise ValueError(f"Staged artifact digest changed: {relative}")
        staged[key] = path
    current = RulesDatabase(active_rules)
    proposed = RulesDatabase(staged["rulesDatabase"])
    current.validate()
    proposed.validate()
    with closing(sqlite3.connect(active_rules)) as conn:
        current_version = conn.execute("PRAGMA user_version").fetchone()[0]
    with closing(sqlite3.connect(staged["rulesDatabase"])) as conn:
        staged_version = conn.execute("PRAGMA user_version").fetchone()[0]
    if (
        current_version not in (8, 9, 10)
        or staged_version != current_version
        or proposed.restrictions_payload() != current.restrictions_payload()
    ):
        raise ValueError("Staged rules changed release schema or reviewed Restrictions")
    payload = load_deployed_object_publication(
        staged["deployedObjects"], army_db, staged["rulesDatabase"],
    )
    if payload is None or len(payload["objects"]) != report.get("reviewedObjects"):
        raise ValueError("Staged deployed-object publication does not match its source pair")
    return {
        "schemaVersion": staged_version,
        "reviewedObjects": len(payload["objects"]),
        "releaseBaselineSha256": baseline,
        "stagedSha256": {key: candidates[key] for key in GENERATED_PATHS},
    }


def main() -> int:
    """Disable the superseded loose-JSON staging gate."""
    raise SystemExit(
        "Historical staged Rules/JSON pair verification is retired. "
        "Use 'infinity-db database-health --db-dir <selected-directory>' "
        "for supported embedded runtime sets."
    )


if __name__ == "__main__":
    raise SystemExit(main())
