"""Safely stage/promote N5.3 Equipment declarations with coherent rules publication.

The three reviewed Equipment Short Skill typeIds are already maintained in the
curated source. Staging does not mutate any tracked generated file. Promotion
checks source fingerprints, retains rollback backups, and verifies that the
deployed-object identities and delivery graph remain unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_directory
from infinity_db.database.repository import Database
from infinity_db.declaration_matrix import core_declaration_matrix
from infinity_db.rules_database import RulesDatabase, export_rules_database
from tools.audit_orders_aro_object_adjacent_chart import audit as source_chart_audit
from tools.build_deployed_object_publication import build_publication, publication_bytes
from tools.stage_hacking_device_chart_citations import (
    STAGED_PATHS,
    _replace_staged_batch,
)

ROOT = Path(__file__).resolve().parents[1]
CURATED = ROOT / STAGED_PATHS[0]
PUBLISHED_RULES = ROOT / STAGED_PATHS[1]
PUBLISHED_OBJECTS = ROOT / STAGED_PATHS[2]
ARMY = ROOT / "data/generated/infinity.db"
DELIVERY = ROOT / "config/validation/deployed-object-delivery-reviews.json"
CANDIDATES = ROOT / "config/validation/deployed-object-candidate-reviews.json"
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
EXPECTED = {
    "equipment:deactivator",
    "equipment:gizmokit",
    "equipment:medikit",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_equipment_provenance() -> None:
    """All newly declarable Equipment must have direct source-chart evidence."""
    document = json.loads(CURATED.read_text(encoding="utf-8"))
    records = {row["id"]: row for row in document["records"]}
    present = {
        row["id"] for row in document["records"]
        if row["kind"] == "equipment" and (row.get("facts") or {}).get("typeIds")
    }
    if present != EXPECTED:
        raise ValueError(f"Expected exactly three Equipment declarations, got {present}")
    for identity in EXPECTED:
        record = records[identity]
        if record["facts"]["typeIds"] != ["short-skill"] or not any(
            citation.get("sourceId") == "n5-core-v5.3-pdf" and citation.get("page") == 191
            for citation in record["citations"]
        ):
            raise ValueError(f"Missing N5.3 p. 191 metadata/citation: {identity}")


def validate_matrix(path: Path) -> None:
    """Compare every generated declaration cell to independently reviewed source."""
    expected = json.loads((
        ROOT / "config/validation/orders-aro-object-adjacent-source-review.json"
    ).read_text(encoding="utf-8"))["rows"]
    categories = {
        "basic": "basic-short-skill",
        "long": "long-skill",
        "short": "short-skill",
        "aro": "aro",
    }
    report = core_declaration_matrix(Database(ARMY), RulesDatabase(path))
    rows = {
        (section["id"], row["record_id"]): (row["name"], row["source_type"])
        for section in report["sections"] for row in section["items"]
    }
    source_rows = {
        (categories[row["section"]], row["recordId"]): (
            row["name"].removesuffix("!"), row["sourceType"].title(),
        )
        for row in expected
    }
    if {k: (v[0].removesuffix("!"), v[1]) for k, v in rows.items()} != source_rows:
        raise ValueError("Generated declaration matrix differs from 57-row PDF review")
    for identity in EXPECTED:
        record = RulesDatabase(path).composed_record(identity)
        if record is None or [x["id"] for x in record.get("skill_types", [])] != [
            "short-skill"
        ]:
            raise ValueError(f"Rules DB Equipment type missing: {identity}")


def publication(path: Path) -> bytes:
    return publication_bytes(build_publication(
        ARMY, path, CURATED, DELIVERY, CANDIDATES,
    ))


def stage(output: Path) -> dict[str, Any]:
    stage_dir = (ROOT / output).resolve()
    if not stage_dir.is_relative_to((ROOT / "local").resolve()):
        raise ValueError("Staging output must be within repository local/")
    if stage_dir.exists():
        raise FileExistsError(f"Refusing to reuse existing stage: {stage_dir}")
    current_equipment_provenance()
    pdf_report = source_chart_audit(pdf_path=PDF, army_db_path=ARMY)
    if pdf_report["selectedRows"] != 57 or pdf_report["armyProgramDeclarationsVerified"] != 19:
        raise ValueError("Unverified source chart")
    baseline = json.loads(PUBLISHED_OBJECTS.read_text(encoding="utf-8"))
    if baseline["sourceSnapshot"]["rulesDatabaseSha256"] != digest(PUBLISHED_RULES):
        raise ValueError("Existing deployed publication is out of sync")
    stage_dir.mkdir(parents=True)
    staged_rules = stage_dir / "rules.db"
    export_rules_database(
        load_curated_directory(ROOT / "data/curated/rules"), staged_rules
    )
    validate_matrix(staged_rules)
    deployed = publication(staged_rules)
    updated = json.loads(deployed)
    if updated["objects"] != baseline["objects"]:
        raise ValueError("Unexpected change to published deployed objects")
    if updated["sourceSnapshot"]["rulesDatabaseSha256"] != digest(staged_rules):
        raise ValueError("Deployed publication fingerprint mismatches rules DB")
    (stage_dir / "deployed-objects.json").write_bytes(deployed)
    report = {
        "scope": "n53-equipment-declarations-staged",
        "sourceSha256": digest(CURATED),
        "priorRulesSha256": digest(PUBLISHED_RULES),
        "priorObjectsSha256": digest(PUBLISHED_OBJECTS),
        "armySha256": digest(ARMY),
        "pdfSha256": pdf_report["verifiedPdfSha256"],
        "stagedRulesSha256": digest(staged_rules),
        "stagedObjectsSha256": digest(stage_dir / "deployed-objects.json"),
        "declarations": sorted(EXPECTED),
        "matrixRows": pdf_report["selectedRows"],
        "deployedObjectCount": len(updated["objects"]),
    }
    (stage_dir / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return report


def promote(output: Path) -> Path:
    stage_dir = (ROOT / output).resolve()
    if not stage_dir.is_relative_to((ROOT / "local").resolve()) or stage_dir.is_symlink():
        raise ValueError("Promotion requires staged artifacts within local/")
    report = json.loads((stage_dir / "report.json").read_text(encoding="utf-8"))
    if report.get("scope") != "n53-equipment-declarations-staged" or (
        report.get("declarations") != sorted(EXPECTED)
    ) or report.get("matrixRows") != 57:
        raise ValueError("Invalid or stale staging report")
    for path, key in (
        (CURATED, "sourceSha256"),
        (PUBLISHED_RULES, "priorRulesSha256"),
        (PUBLISHED_OBJECTS, "priorObjectsSha256"),
        (ARMY, "armySha256"),
        (PDF, "pdfSha256"),
        (stage_dir / "rules.db", "stagedRulesSha256"),
        (stage_dir / "deployed-objects.json", "stagedObjectsSha256"),
    ):
        if not path.is_file() or path.is_symlink() or digest(path) != report[key]:
            raise ValueError(f"Changed or unavailable staging input: {path}")
    current_equipment_provenance()
    validate_matrix(stage_dir / "rules.db")
    if publication(stage_dir / "rules.db") != (
        stage_dir / "deployed-objects.json"
    ).read_bytes():
        raise ValueError("Staged publication not reproducible")

    before = json.loads(PUBLISHED_OBJECTS.read_text(encoding="utf-8"))["objects"]
    payloads = {
        STAGED_PATHS[0]: CURATED.read_bytes(),
        STAGED_PATHS[1]: (stage_dir / "rules.db").read_bytes(),
        STAGED_PATHS[2]: (stage_dir / "deployed-objects.json").read_bytes(),
    }

    def verify_promoted() -> None:
        validate_matrix(PUBLISHED_RULES)
        if publication(PUBLISHED_RULES) != PUBLISHED_OBJECTS.read_bytes():
            raise ValueError("Promoted deployed objects publication differs from generated")
        if json.loads(PUBLISHED_OBJECTS.read_text(encoding="utf-8"))["objects"] != before:
            raise ValueError("Deployed-object identities/deliveries changed")
        if digest(PUBLISHED_RULES) != report["stagedRulesSha256"]:
            raise ValueError("Promoted rules DB checksum drift")

    return _replace_staged_batch(ROOT, payloads, verify_promoted)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--promote-staged", action="store_true")
    args = parser.parse_args()
    if args.promote_staged:
        backup = promote(args.output_dir)
        print(f"Promoted Equipment declarations; recovery backup: {backup}")
    else:
        report = stage(args.output_dir)
        print(json.dumps(report, indent=2))
        print("Staged only: no tracked generated files changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
