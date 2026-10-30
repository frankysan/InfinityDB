"""Audit the six N5.3 p. 194 Restrictions Chart rows without granting legality.

The chart supplies negative conditions. Troop Types are source selectors, not
canonical record IDs; a Motorcycle's upward Jump restriction must never
become a prohibition on all Jump actions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/validation/restrictions-source-chart.json"
CURATED = ROOT / "data/curated/rules/n5-core-v5.3.json"
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
SUBJECTS = ("TAG", "Motorcycle", "Aerial", "VH", "REM", "Irregular")
COUNTS = (2, 5, 2, 2, 2, 1)
CLASSIFICATION = {
    "scope": "source-restriction-conditions-not-live-action-legality",
    "subject": "troop-types-remain-source-selectors-without-canonical-identity",
    "action": "negative-prohibition-not-positive-permission",
    "jump": "motorcycle-upward-only-not-all-jumps",
    "lieutenant": "army-selection-eligibility-not-skill-use",
    "ladder": "physical-route-restriction-without-invented-skill",
}
# Each action maps to its existing reference concept, not a proposed
# executable gameplay operation.
ACTION_TARGETS = {
    "enter-prone": "state:prone",
    "declare-cautious-movement": "skill:cautious-movement",
    "declare-climb": "skill:climb",
    "use-ladders": None,
    "upward-jump": "skill:jump",
    "lieutenant-selection": "skill:lieutenant",
}
ACTION_EVIDENCE = {
    "enter-prone": "prone",
    "declare-cautious-movement": "cautious movement",
    "declare-climb": "climb",
    "use-ladders": "ladders",
    "upward-jump": "upwards jump",
    "lieutenant-selection": "lieutenant",
}
SUBJECT_KIND = {
    "TAG": ("troop-type", None, "skill:cautious-movement"),
    "Motorcycle": ("equipment-while-mounted", "equipment:motorcycle", "equipment:motorcycle"),
    "Aerial": ("skill", "skill:aerial", "skill:aerial"),
    "VH": ("troop-type", None, "skill:cautious-movement"),
    "REM": ("troop-type", None, "skill:lieutenant"),
    "Irregular": ("training", "training:irregular", "training:irregular"),
}


def normalize(value: str) -> str:
    return " ".join(value.upper().replace("’", "'").split())


def restrictions_audit(
    manifest: dict[str, Any], records: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Check exact row/relationship boundaries against maintained reference facts."""
    if set(manifest) != {
        "formatVersion", "sourceId", "sourcePage", "sourcePdfSha256",
        "reviewStatus", "classification", "rows",
    } or (
        manifest["formatVersion"] != 1
        or manifest["sourceId"] != "n5-core-v5.3-pdf"
        or manifest["sourcePage"] != 194
        or manifest["reviewStatus"] != "source-reviewed-audit-only"
        or manifest["classification"] != CLASSIFICATION
        or not isinstance(manifest["sourcePdfSha256"], str)
        or re.fullmatch(r"[a-f0-9]{64}", manifest["sourcePdfSha256"]) is None
    ):
        raise ValueError("Restrictions Chart source provenance/scope drift")

    rows = manifest["rows"]
    if not isinstance(rows, list) or len(rows) != 6 or (
        tuple(row.get("subject") for row in rows if isinstance(row, dict)) != SUBJECTS
    ):
        raise ValueError("Restrictions Chart expected six source-ordered rows")

    uncovered: list[dict[str, str]] = []
    nuanced: list[dict[str, str]] = []
    subjects_without_identity: list[str] = []
    for row, expected_count in zip(rows, COUNTS, strict=True):
        subject = row["subject"]
        kind, owner_ref, evidence_ref = SUBJECT_KIND[subject]
        if set(row) != {
            "subject", "subjectKind", "ownerRecordId", "sourceText",
            "restrictions", "ownerEvidence",
        } or (
            row["subjectKind"], row["ownerRecordId"], row["ownerEvidence"]
        ) != (kind, owner_ref, evidence_ref):
            raise ValueError(f"Restrictions Chart source subject mapping drift: {subject}")
        if not isinstance(row["sourceText"], str) or not row["sourceText"].strip():
            raise ValueError(f"Restrictions Chart missing source text: {subject}")
        conditions = row["restrictions"]
        if not isinstance(conditions, list) or len(conditions) != expected_count:
            raise ValueError(f"Restrictions Chart condition count drift: {subject}")
        seen: set[str] = set()
        for condition in conditions:
            if not isinstance(condition, dict) or set(condition) != {
                "action", "targetRecordId", "scope",
            }:
                raise ValueError(f"Restrictions Chart invalid condition schema: {subject}")
            action = condition["action"]
            if not isinstance(action, str) or action not in ACTION_TARGETS:
                raise ValueError(f"Restrictions Chart unknown prohibited action: {subject}")
            if action in seen:
                raise ValueError(f"Restrictions Chart repeated action: {subject} {action}")
            seen.add(action)
            if condition["targetRecordId"] != ACTION_TARGETS[action]:
                raise ValueError(f"Restrictions Chart target identity drift: {subject} {action}")
            if normalize(ACTION_EVIDENCE[action]) not in normalize(row["sourceText"]):
                raise ValueError(
                    f"Restrictions Chart action unsupported by wording: {subject} {action}"
                )
            scope = condition["scope"]
            allowed_scope = (
                "while-mounted-upwards-only" if action == "upward-jump"
                else "while-mounted" if subject == "Motorcycle"
                else "aerial-active" if subject == "Aerial"
                else "army-selection-only" if action == "lieutenant-selection"
                else "all"
            )
            if scope != allowed_scope:
                raise ValueError(f"Restrictions Chart action-scope drift: {subject} {action}")
            target_ref = condition["targetRecordId"]
            if target_ref is not None and target_ref not in records:
                raise ValueError(f"Restrictions Chart unknown action reference: {target_ref}")

        if evidence_ref not in records or records[evidence_ref]["kind"] not in {
            "equipment", "skill", "training",
        }:
            raise ValueError(f"Restrictions Chart missing maintained evidence: {evidence_ref}")
        if owner_ref is None:
            subjects_without_identity.append(subject)
            for condition in conditions:
                uncovered.append({"subject": subject, "action": condition["action"]})
            continue
        owner = records[owner_ref]
        relations = {
            (relation.get("type"), relation.get("recordId"))
            for relation in owner.get("relations", [])
        }
        restrictions_text = normalize(" ".join(owner.get("facts", {}).get("restrictions", [])))
        if subject == "Motorcycle":
            for fragment in ("MOUNTED", "PRONE", "CLIMB", "LADDERS", "UPWARD", "CAUTIOUS"):
                if fragment not in restrictions_text:
                    raise ValueError(f"Motorcycle maintained restriction missing: {fragment}")
        if subject == "Aerial":
            for fragment in ("PRONE", "CAUTIOUS"):
                if fragment not in restrictions_text:
                    raise ValueError(f"Aerial maintained restriction missing: {fragment}")
        if subject == "Irregular":
            if ("restricts-use-of", "skill:lieutenant") not in relations:
                raise ValueError("Irregular source selection restriction missing relation")
            if "IRREGULAR" not in normalize(" ".join(
                records["skill:lieutenant"].get("facts", {}).get("restrictions", [])
            )):
                raise ValueError("Lieutenant selection rule lost Irregular restriction")

        for condition in conditions:
            action = condition["action"]
            target = condition["targetRecordId"]
            expected_relation = (
                "prevents-state-entry" if action == "enter-prone"
                else "restricts-use-of"
            )
            if target is None or (expected_relation, target) not in relations:
                uncovered.append({"subject": subject, "action": action})
            elif action in {"upward-jump", "lieutenant-selection"}:
                nuanced.append({
                    "subject": subject, "action": action,
                    "risk": (
                        "existing-general-jump-relation-needs-upward-qualifier"
                        if action == "upward-jump"
                        else "existing-skill-relation-is-really-selection-eligibility"
                    ),
                })

    if sum(len(row["restrictions"]) for row in rows) != 14:
        raise ValueError("Restrictions Chart unexpected condition coverage")
    return {
        "scope": CLASSIFICATION["scope"],
        "sourcePage": 194, "rowCount": 6, "negativeConditionCount": 14,
        "sourceOnlyTroopTypeSubjects": subjects_without_identity,
        "missingTypedRelations": uncovered,
        "conditionalRelationWarnings": nuanced,
        "automaticLegalityInference": False,
    }


def verify_pinned_pdf(path: Path, manifest: dict[str, Any]) -> str:
    """Verify each complete line inside p. 194 chart bounds, in source order."""
    try:
        import pymupdf  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ValueError("Restrictions Chart PDF check requires PyMuPDF") from exc
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != manifest["sourcePdfSha256"]:
        raise ValueError("Restrictions Chart pinned PDF fingerprint mismatch")
    with pymupdf.open(stream=data, filetype="pdf") as document:
        text = document[193].get_text("text", sort=False)
    if not isinstance(text, str):
        raise ValueError("Restrictions Chart PDF text unavailable")
    normalized = normalize(text)
    if "RESTRICTIONS CHART" not in normalized or (
        "RETREAT! AND LOSS OF LIEUTENANT SUMMARY CHART" not in normalized
    ):
        raise ValueError("Restrictions Chart PDF section boundary missing")
    block = normalized.split("RESTRICTIONS CHART", 1)[1].split(
        "RETREAT! AND LOSS OF LIEUTENANT SUMMARY CHART", 1
    )[0]
    cursor = 0
    for row in manifest["rows"]:
        text_value = normalize(row["sourceText"])
        found = block.find(text_value, cursor)
        if found < 0:
            raise ValueError(f"Restrictions Chart printed line mismatch: {row['subject']}")
        cursor = found + len(text_value)
    return digest




PUBLICATION = ROOT / "src/infinity_db/web/static/restrictions-reference.json"
SOURCE_URL = "https://experience.corvusbelli.com/en/infinity/resources"
ACTION_DISPLAY: dict[str, tuple[str, str | None]] = {
    "enter-prone": ("Cannot enter Prone State", None),
    "declare-cautious-movement": ("Cannot declare Cautious Movement", None),
    "declare-climb": ("Cannot declare Climb", None),
    "use-ladders": ("Cannot use ladders", "Ladders are a separate restriction from Climb."),
    "upward-jump": (
        "Cannot Jump upward",
        "Only upward Jump is prohibited here; horizontal/downward Jump "
        "is not prohibited by this row.",
    ),
    "lieutenant-selection": (
        "Cannot be chosen as Lieutenant",
        "Army selection eligibility, not a ban on using the Lieutenant Skill.",
    ),
}
SUBJECT_DISPLAY: dict[str, tuple[str, str]] = {
    "TAG": ("TAG", "Troop Type"),
    "Motorcycle": ("Mounted Motorcycle", "Equipment, while mounted"),
    "Aerial": ("Aerial", "Special Skill, while active"),
    "VH": ("Vehicle (VH)", "Troop Type"),
    "REM": ("Remote (REM)", "Troop Type"),
    "Irregular": ("Irregular Trooper", "Irregular Training"),
}


def project_public_restrictions(
    manifest: dict[str, Any], records: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Produce negative-only, linked browser facts from the validated source."""
    restrictions_audit(manifest, records)
    rows: list[dict[str, Any]] = []
    for row in manifest["rows"]:
        subject = row["subject"]
        title, kind = SUBJECT_DISPLAY[subject]
        owner_id = row["ownerRecordId"]
        owner_href = None
        if owner_id and (domain := owner_id.split(":", 1)[0]) in {"skill", "equipment"}:
            owner_href = f"/{'skills' if domain == 'skill' else 'equipment'}/" + (
                owner_id.split(":", 1)[1]
            )
        conditions: list[dict[str, Any]] = []
        for entry in row["restrictions"]:
            target = entry["targetRecordId"]
            link = None
            if target:
                domain, slug = target.split(":", 1)
                link = f"/{'states' if domain == 'state' else 'skills'}/{slug}"
            label, note = ACTION_DISPLAY[entry["action"]]
            conditions.append({
                "action": entry["action"], "label": label, "scope": entry["scope"],
                "href": link, "note": note,
            })
        rows.append({
            "id": subject.lower(), "name": title, "category": kind,
            "ownerHref": owner_href, "sourceSubject": subject,
            "conditions": conditions,
        })
    return {
        "formatVersion": 1,
        "scope": "reviewed-negative-conditions-not-action-legality",
        "source": {
            "id": manifest["sourceId"], "page": manifest["sourcePage"],
            "url": SOURCE_URL,
        },
        "rows": rows,
    }


def publication_bytes(data: dict[str, Any]) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def verify_published_restrictions(
    manifest: dict[str, Any], records: dict[str, dict[str, Any]],
    path: Path,
) -> str:
    expected = publication_bytes(project_public_restrictions(manifest, records))
    actual = path.read_bytes()
    if actual != expected:
        raise ValueError("Published Restrictions reference is stale or does not match source")
    return hashlib.sha256(actual).hexdigest()


def audit_source_files(
    manifest_path: Path = MANIFEST,
    curated_path: Path = CURATED,
    pdf_path: Path | None = None,
    publication_path: Path | None = None,
) -> dict[str, Any]:
    manifest_raw = manifest_path.read_bytes()
    curated_raw = curated_path.read_bytes()
    manifest = json.loads(manifest_raw)
    curated = json.loads(curated_raw)
    records = {row["id"]: row for row in curated["records"]}
    result = restrictions_audit(manifest, records)
    return {
        **result,
        "manifestSha256": hashlib.sha256(manifest_raw).hexdigest(),
        "curatedSha256": hashlib.sha256(curated_raw).hexdigest(),
        "verifiedPdfSha256": verify_pinned_pdf(pdf_path, manifest) if pdf_path else None,
        "publishedReferenceSha256": (
            verify_published_restrictions(manifest, records, publication_path)
            if publication_path is not None else None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--curated", type=Path, default=CURATED)
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--check-publication", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.output and args.check_publication:
        parser.error("--output and --check-publication are exclusive")
    if args.output:
        destination = args.output.resolve()
        if not destination.is_relative_to(ROOT / "local") or destination.exists():
            parser.error("--output must name a new file beneath the ignored local/ directory")
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        curated = json.loads(args.curated.read_text(encoding="utf-8"))
        records = {row["id"]: row for row in curated["records"]}
        data = publication_bytes(project_public_restrictions(manifest, records))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    report = audit_source_files(
        args.manifest, args.curated, args.pdf,
        PUBLICATION if args.check_publication else None,
    )
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"N5.3 Restrictions Chart: {report['rowCount']} rows, "
            f"{report['negativeConditionCount']} negative conditions"
        )
        print(f"Unmodeled typed edges: {len(report['missingTypedRelations'])}")
        print(f"Conditional edge warnings: {len(report['conditionalRelationWarnings'])}")
        print("Source-only: no action-legality or Army ownership inferred")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
