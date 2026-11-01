"""Guarded stage/promote for N5.3 Forward Observer (+1SD) extra-die metadata.

Staging writes only ignored local/ outputs; promotion synchronizes curated JSON,
rules.db and the deployed-object publication with retained rollback artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_directory, load_curated_document
from infinity_db.rules_database import RulesDatabase
from tools.audit_source_variant_inputs import inventory_source_variants, select_source_variants
from tools.build_deployed_object_publication import build_publication, publication_bytes
from tools.stage_hacking_device_chart_citations import (
    STAGED_PATHS,
    _replace_staged_batch,
    export_release_rules,
)

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / STAGED_PATHS[0]
RULES = ROOT / STAGED_PATHS[1]
OBJECTS = ROOT / STAGED_PATHS[2]
ARMY = ROOT / "data/generated/infinity.db"
RAW = ROOT / "data/generated/infinity.raw.db"
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
PDF_MANIFEST = ROOT / "config/validation/weaponry-family-clauses.json"
DELIVERY = ROOT / "config/validation/deployed-object-delivery-reviews.json"
CANDIDATES = ROOT / "config/validation/deployed-object-candidate-reviews.json"
RECORD = "skill:forward-observer"
EXPECTED = {
    "source": "army-extra",
    "kind": "reviewed-extra",
    "extra_values": [{
        "extra_id": 308,
        "extra_type": "TEXT",
        "raw_value": "+1SD",
        "effect": {
            "kind": "special-die",
            "applies_to": "forward-observer-wip-attack-roll",
            "count": 1,
        },
    }],
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _head_curated() -> dict[str, Any]:
    old = subprocess.run(
        ["git", "show", f"HEAD:{STAGED_PATHS[0]}"],
        cwd=ROOT, capture_output=True, check=True,
    )
    return json.loads(old.stdout)


def verify_source() -> None:
    """Require exactly one additive curated parameter, unchanged other source facts."""
    old = _head_curated()
    current = load_curated_document(CURATED)
    old_records = {item["id"]: item for item in old["records"]}
    now_records = {item["id"]: item for item in current["records"]}
    if set(now_records) != set(old_records):
        raise ValueError("Curated record identities changed")
    before = old_records[RECORD]
    after = now_records[RECORD]
    variant = after["variantSemantics"]
    if before["variantSemantics"] != {"inheritance": "family"}:
        raise ValueError("Unexpected HEAD Forward Observer variant baseline")
    if variant.get("inheritance") != "family" or len(
        variant.get("occurrenceParameters", [])
    ) != 1:
        raise ValueError("Unexpected Forward Observer variant scope")
    original_param = variant["occurrenceParameters"][0]
    if original_param != {
        "source": "army-extra", "kind": "reviewed-extra",
        "extraValues": [{
            "extraId": 308, "extraType": "TEXT", "rawValue": "+1SD",
            "effect": {
                "kind": "special-die",
                "appliesTo": "forward-observer-wip-attack-roll",
                "count": 1,
            },
        }],
    }:
        raise ValueError("Forward Observer effect differs from exact reviewed scope")
    restored = json.loads(json.dumps(current))
    restored_records = {item["id"]: item for item in restored["records"]}
    restored_records[RECORD]["variantSemantics"] = before["variantSemantics"]
    additional_citations = [
        {"sourceId": "n5-core-v5.3-pdf", "page": 75,
         "section": "Modifiers Explained"},
        {"sourceId": "n5-core-v5.3-pdf", "page": 92,
         "section": "Forward Observer"},
    ]
    if after["citations"] != before["citations"] + additional_citations:
        raise ValueError("Forward Observer citations differ from reviewed additions")
    restored_records[RECORD]["citations"] = before["citations"]
    if restored != old:
        raise ValueError("Other curated source content changed")
    if digest(PDF) != json.loads(PDF_MANIFEST.read_text(encoding="utf8"))[
        "corePdfSha256"
    ]:
        raise ValueError("N5.3 PDF does not match pinned source fingerprint")


def check_source_occurrences(path: Path) -> None:
    report = inventory_source_variants(ARMY, RAW, path)
    [item] = select_source_variants(report, "skills", [59])["items"]
    if (
        item["occurrences"] != 609 or item["status"] != "reviewed-extra-parameter"
        or item["rawValues"] or item["reviewedExtra"] != EXPECTED
        or item["extraSignatures"] != [{
            "extras": [[308, "TEXT", "+1SD"]], "reviewed": True, "count": 2,
        }]
        or report["catalogs"]["skills"]["summary"]["statuses"].get(
            "unresolved-occurrence-parameter"
        ) != 17
    ):
        raise ValueError("Source-59 inventory diverged from pinned reviewed signatures")


def publication(path: Path) -> bytes:
    return publication_bytes(build_publication(
        ARMY, path, CURATED, DELIVERY, CANDIDATES,
    ))


def stage(relative: Path) -> dict[str, Any]:
    output = (ROOT / relative).resolve()
    if not output.is_relative_to((ROOT / "local").resolve()):
        raise ValueError("Stage must be under ignored local/")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite staging output: {relative}")
    verify_source()
    baseline = json.loads(OBJECTS.read_text(encoding="utf8"))
    if baseline["sourceSnapshot"]["rulesDatabaseSha256"] != digest(RULES):
        raise ValueError("Current deployed-object publication is out of sync")
    output.mkdir(parents=True)
    staged = output / "rules.db"
    export_release_rules(load_curated_directory(ROOT / "data/curated/rules"), staged)
    check_source_occurrences(staged)
    if RulesDatabase(staged).skill_reviewed_extra_semantics().get("forward-observer") != EXPECTED:
        raise ValueError("Missing typed Forward Observer parameter in staged export")
    body = publication(staged)
    proposed = json.loads(body)
    if (
        len(proposed["objects"]) != 17
        or proposed["objects"] != baseline["objects"]
        or proposed["sourceSnapshot"]["rulesDatabaseSha256"] != digest(staged)
    ):
        raise ValueError("Staging changed reviewed deployed objects or rules fingerprint")
    (output / "deployed-objects.json").write_bytes(body)
    report = {
        "scope": "n53-forward-observer-special-die-staged",
        "head": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, check=True, text=True,
        ).stdout.strip(),
        "sourceSha256": digest(CURATED),
        "priorRulesSha256": digest(RULES),
        "priorObjectsSha256": digest(OBJECTS),
        "armySha256": digest(ARMY),
        "rawSha256": digest(RAW),
        "pdfSha256": digest(PDF),
        "stagedRulesSha256": digest(staged),
        "stagedObjectsSha256": digest(output / "deployed-objects.json"),
        "reviewedObjects": 17,
    }
    (output / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return report


def promote(relative: Path) -> Path:
    output = (ROOT / relative).resolve()
    if not output.is_relative_to((ROOT / "local").resolve()) or output.is_symlink():
        raise ValueError("Promotion requires ignored local/ stage")
    report = json.loads((output / "report.json").read_text(encoding="utf8"))
    if report.get("scope") != "n53-forward-observer-special-die-staged" or (
        report.get("reviewedObjects") != 17
    ):
        raise ValueError("Unexpected Forward Observer staging report")
    actual_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, check=True, text=True,
    ).stdout.strip()
    if actual_head != report["head"]:
        raise ValueError("HEAD changed after staging")
    git = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", STAGED_PATHS[1], STAGED_PATHS[2]],
        cwd=ROOT, check=False,
    )
    if git.returncode != 0:
        raise ValueError("Published database/artifacts have unstaged changes")
    for path, key in (
        (CURATED, "sourceSha256"), (RULES, "priorRulesSha256"),
        (OBJECTS, "priorObjectsSha256"), (ARMY, "armySha256"),
        (RAW, "rawSha256"), (PDF, "pdfSha256"),
        (output / "rules.db", "stagedRulesSha256"),
        (output / "deployed-objects.json", "stagedObjectsSha256"),
    ):
        if not path.is_file() or path.is_symlink() or digest(path) != report[key]:
            raise ValueError(f"Staging input changed: {path.name}")
    verify_source()
    check_source_occurrences(output / "rules.db")
    baseline = json.loads(OBJECTS.read_text(encoding="utf8"))
    body = (output / "deployed-objects.json").read_bytes()
    if publication(output / "rules.db") != body or (
        json.loads(body)["objects"] != baseline["objects"]
    ):
        raise ValueError("Staged publication not reproducible or modified objects")
    payloads = {
        STAGED_PATHS[0]: CURATED.read_bytes(),
        STAGED_PATHS[1]: (output / "rules.db").read_bytes(),
        STAGED_PATHS[2]: body,
    }

    def postcheck() -> None:
        check_source_occurrences(RULES)
        if publication(RULES) != OBJECTS.read_bytes():
            raise ValueError("Promoted publication out of sync")
        if digest(RULES) != report["stagedRulesSha256"] or (
            digest(OBJECTS) != report["stagedObjectsSha256"]
        ):
            raise ValueError("Promoted hashes differ from staging")
        if json.loads(OBJECTS.read_text(encoding="utf8"))["objects"] != (
            baseline["objects"]
        ):
            raise ValueError("Published objects changed")

    return _replace_staged_batch(ROOT, payloads, postcheck)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--promote-staged", action="store_true")
    args = parser.parse_args()
    if args.promote_staged:
        print(f"Promoted with retained recovery backup: {promote(args.output_dir)}")
    else:
        print(json.dumps(stage(args.output_dir), indent=2))
        print("Staged only; no tracked artifact changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
