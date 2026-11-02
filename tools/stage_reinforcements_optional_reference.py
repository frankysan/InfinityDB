"""Stage/promote the clearly sourced optional Reinforcements annex reference.

Only the new reviewed annex is authored. The guarded migration updates the
matched rules DB and deployed-object fingerprint, retaining rollback copies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_directory, load_curated_document
from infinity_db.rules_database import RulesDatabase
from tools.audit_reinforcements_applicability import audit_applicability
from tools.build_deployed_object_publication import build_publication, publication_bytes
from tools.release_rules_export import export_release_rules
from tools.stage_hacking_device_chart_citations import STAGED_PATHS, _replace_staged_batch

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / STAGED_PATHS[0]
RULES = ROOT / STAGED_PATHS[1]
OBJECTS = ROOT / STAGED_PATHS[2]
ANNEX = ROOT / "data/curated/rules/reinforcements-extra-n4-reference.json"
MANIFEST = ROOT / "config/validation/reinforcements-n5-applicability-review.json"
ARMY = ROOT / "data/generated/infinity.db"
DELIVERY = ROOT / "config/validation/deployed-object-delivery-reviews.json"
CANDIDATES = ROOT / "config/validation/deployed-object-candidate-reviews.json"
RECORD_IDS = frozenset((
    "rule:reinforcements-extra", "skill:commlink", "skill:request-reinforcements",
))
SCOPE = "optional-n4-origin-reinforcements-reference-v1"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT,
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def verify_source() -> None:
    document = load_curated_document(ANNEX)
    collection = document["collection"]
    if (collection["id"], collection["status"], collection["authority"]) != (
        "reinforcements-extra-n4-reference", "current", "secondary",
    ):
        raise ValueError("Unexpected optional Reinforcements collection authority")
    records = {record["id"]: record for record in document["records"]}
    if set(records) != RECORD_IDS:
        raise ValueError("Only the three reviewed Reinforcements records may be published")
    for record in records.values():
        if "N4" not in record["summary"] or record["scope"] != {
            "game": "N5", "seasons": ["current"],
        } or not any(
            c["sourceId"] == "reinforcements-annex-wiki-n4"
            for c in record["citations"]
        ):
            raise ValueError(f"Lost source boundary: {record['id']}")
    if records["skill:commlink"]["armyLinks"] != [
        {"entity": "skill", "id": "commlink"},
    ] or records["skill:request-reinforcements"]["facts"]["typeIds"] != [
        "tactical-phase-step",
    ]:
        raise ValueError("Reinforcements identity/declaration boundary changed")
    policy = json.loads(MANIFEST.read_text(encoding="utf-8"))["reviewDecision"]
    if (
        policy.get("n4OriginOptionalReferenceAllowed") is not True
        or policy.get("currentN5ProceduresAuthorized") is not False
    ):
        raise ValueError("N4-origin publication requires an explicit non-N5 decision")
    audit = audit_applicability()
    if audit["n5ProceduresAuthorized"] is not False:
        raise ValueError("The current N5 procedure gate unexpectedly changed")


def verify_record_delta(before: Path, after: Path) -> None:
    """Exactly three new rows; every existing source record remains byte-identical."""
    def rows(path: Path) -> dict[tuple[str, str], tuple[Any, ...]]:
        with sqlite3.connect(path) as connection:
            return {
                (row[0], row[1]): tuple(row)
                for row in connection.execute("SELECT * FROM records")
            }
    old, new = rows(before), rows(after)
    if any(new.get(key) != value for key, value in old.items()):
        raise ValueError("Existing rules records changed during optional annex publication")
    added = set(new) - set(old)
    if len(added) != 3 or {key[1] for key in added} != RECORD_IDS:
        raise ValueError(f"Unexpected rules record additions: {sorted(added)}")
    if not all(key[0] == "reinforcements-extra-n4-reference" for key in added):
        raise ValueError("New records escaped the standalone annex collection")
    old_rules, new_rules = RulesDatabase(before), RulesDatabase(after)
    old_rules.validate()
    new_rules.validate()
    for record_id in RECORD_IDS:
        if old_rules.composed_record(record_id) is not None:
            raise ValueError(f"Already published: {record_id}")
        record = new_rules.composed_record(record_id)
        if record is None or "N4" not in record["summary"]:
            raise ValueError(f"Missing N4 source notice: {record_id}")


def publication(path: Path) -> bytes:
    return publication_bytes(build_publication(
        ARMY, path, CORE, DELIVERY, CANDIDATES,
    ))


def _stage_dir(relative: Path, *, must_exist: bool) -> Path:
    output = (ROOT / relative).resolve()
    local = (ROOT / "local").resolve()
    if (not output.is_relative_to(local) or output == local
            or (ROOT / relative).is_symlink()
            or output.exists() != must_exist):
        raise ValueError("Expected an exclusive ignored local/ stage directory")
    return output


def stage(relative: Path) -> dict[str, Any]:
    output = _stage_dir(relative, must_exist=False)
    verify_source()
    old = json.loads(OBJECTS.read_text(encoding="utf-8"))
    if old["sourceSnapshot"]["rulesDatabaseSha256"] != digest(RULES):
        raise ValueError("Existing rules/publication pair is mismatched")
    output.mkdir(parents=True, exist_ok=False)
    candidate = output / "rules.db"
    export_release_rules(load_curated_directory(ROOT / "data/curated/rules"), candidate)
    verify_record_delta(RULES, candidate)
    body = publication(candidate)
    proposed = json.loads(body)
    if (
        len(old["objects"]) != 17 or proposed["objects"] != old["objects"]
        or proposed["sourceSnapshot"]["rulesDatabaseSha256"] != digest(candidate)
    ):
        raise ValueError("Optional annex changed reviewed deployed objects")
    (output / "deployed-objects.json").write_bytes(body)
    report = {
        "scope": SCOPE, "head": git_head(),
        "annexSha256": digest(ANNEX), "manifestSha256": digest(MANIFEST),
        "coreSha256": digest(CORE), "armySha256": digest(ARMY),
        "priorRulesSha256": digest(RULES), "priorObjectsSha256": digest(OBJECTS),
        "newRulesSha256": digest(candidate),
        "newObjectsSha256": digest(output / "deployed-objects.json"),
        "newRecords": sorted(RECORD_IDS), "unchangedDeployedObjects": 17,
    }
    (output / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n",
    )
    return report


def promote(relative: Path) -> Path:
    output = _stage_dir(relative, must_exist=True)
    report = json.loads((output / "report.json").read_text(encoding="utf-8"))
    if (report.get("scope") != SCOPE
            or report.get("head") != git_head()
            or report.get("newRecords") != sorted(RECORD_IDS)
            or report.get("unchangedDeployedObjects") != 17):
        raise ValueError("Staged optional annex report is stale or unexpected")
    for path, key in (
        (ANNEX, "annexSha256"), (MANIFEST, "manifestSha256"),
        (CORE, "coreSha256"), (ARMY, "armySha256"),
        (RULES, "priorRulesSha256"), (OBJECTS, "priorObjectsSha256"),
        (output / "rules.db", "newRulesSha256"),
        (output / "deployed-objects.json", "newObjectsSha256"),
    ):
        if not path.is_file() or path.is_symlink() or digest(path) != report[key]:
            raise ValueError(f"Staged input changed: {path.name}")
    if subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", STAGED_PATHS[1], STAGED_PATHS[2]],
        cwd=ROOT, check=False,
    ).returncode != 0:
        raise ValueError("Existing published artifacts are not clean against HEAD")
    verify_source()
    staged = output / "rules.db"
    verify_record_delta(RULES, staged)
    body = (output / "deployed-objects.json").read_bytes()
    if publication(staged) != body or (
        json.loads(body)["objects"]
        != json.loads(OBJECTS.read_text(encoding="utf-8"))["objects"]
    ):
        raise ValueError("Staged publication has drifted")
    payloads = {
        STAGED_PATHS[0]: CORE.read_bytes(),  # unchanged but guarded by shared batch
        STAGED_PATHS[1]: staged.read_bytes(),
        STAGED_PATHS[2]: body,
    }

    def postcheck() -> None:
        if (
            digest(RULES) != report["newRulesSha256"]
            or digest(OBJECTS) != report["newObjectsSha256"]
            or publication(RULES) != OBJECTS.read_bytes()
        ):
            raise ValueError("Promoted optional annex artifacts are mismatched")
        RulesDatabase(RULES).validate()

    return _replace_staged_batch(ROOT, payloads, postcheck)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--promote-staged", action="store_true")
    args = parser.parse_args()
    if args.promote_staged:
        print(f"Promoted; rollback backup: {promote(args.output_dir)}")
    else:
        print(json.dumps(stage(args.output_dir), indent=2))
        print("Staged only; release artifacts unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
