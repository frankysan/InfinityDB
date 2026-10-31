"""Cross-check N5.3 p.74 Deployable Profiles with reviewed object references.

The p.74 quick-reference table is independent of pp. 176–188 Weapon Chart
extraction and contains repeated names. Neither aliases nor a plural family
are new object identities. This is read-only provenance, not publication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from infinity_db.deployed_object_reference import project_deployed_references
from tools.audit_deployed_object_inventory import audit_inventory

PAGE = 74
PRINTED_ROWS = (
    "ARMED TURRET",
    "CRAZYKOALA",
    "CYBERMINE",
    "DAZER",
    "DEPLOYABLE REPEATER",
    "DISCO BALLER",
    "DROP BEARS (DEPLOYABLE MODE)",
    "FAST PANDA",
    "MADTRAPS",
    "MINES",
    "WILDPARROT",
    "FASTPANDA",
    "MADTRAPS",
)
# These are selectors into *already reviewed* identities. They do not
# imply equivalent effects, delivery or Army/Unit ownership.
SOURCE_SELECTORS: dict[str, tuple[str, str, str | None]] = {
    "CRAZYKOALA": ("weapon", "Crazykoala", None),
    "CYBERMINE": ("weapon", "Cybermine", None),
    "DAZER": ("equipment", "Dazer", None),
    "DEPLOYABLE REPEATER": ("equipment", "Deployable Repeater", None),
    "DISCO BALLER": ("weapon", "Disco Baller", "Disco Ball"),
    "DROP BEARS (DEPLOYABLE MODE)": ("weapon", "Drop Bears", "Deployable Mode"),
    "FAST PANDA": ("equipment", "FastPanda", None),
    "FASTPANDA": ("equipment", "FastPanda", None),
    "MADTRAPS": ("weapon", "Madtraps", None),
    "WILDPARROT": ("weapon", "WildParrot", None),
}
NAME_PATTERN = "|".join(
    re.escape(name) for name in sorted(set(PRINTED_ROWS), key=len, reverse=True)
)
PROFILE_LINE = re.compile(
    rf"(?<![\w])(?P<name>{NAME_PATTERN})"
    r"[ \t]+(?P<arm>[0-9])[ \t]+(?P<bts>[0-9])"
    r"[ \t]+(?P<str>[0-9])[ \t]+(?P<s>[0-9])(?=\s|$)",
    re.IGNORECASE,
)
KEYS = ("ARM", "BTS", "STR", "S")


def parse_quick_profiles(text: str) -> list[dict[str, Any]]:
    """Extract printed values verbatim; fail on missing/reordered table rows."""
    if "DEPLOYABLE PROFILES" not in text:
        raise ValueError("N5.3 p.74 Deployable Profiles header missing")
    chunk = text.split("DEPLOYABLE PROFILES", 1)[1]
    rows = []
    for match in PROFILE_LINE.finditer(chunk):
        rows.append({
            "printedName": match.group("name").upper(),
            "printedAttributes": {
                key: int(match.group(group))
                for key, group in zip(KEYS, ("arm", "bts", "str", "s"), strict=True)
            },
            "pdfPage": PAGE,
        })
    if [row["printedName"] for row in rows] != list(PRINTED_ROWS):
        raise ValueError(
            "N5.3 p.74 quick-reference rows changed or were not extracted: "
            f"{[row['printedName'] for row in rows]}"
        )
    return rows


def compare_quick_profiles(
    printed: list[dict[str, Any]],
    references: dict[str, Any],
) -> dict[str, Any]:
    """Preserve duplicate spellings, Mine family scope and source conflicts."""
    if references.get("scope") != "reviewed-projection-not-complete-unit-usage":
        raise ValueError("Expected a reviewed object reference, not an Army ownership map")
    objects = references["objects"]
    result = []
    for row in printed:
        name = row["printedName"]
        if name == "MINES":
            # p.74 has a plural family row, not a generic Mine object.
            result.append({
                **row, "disposition": "family-not-single-object",
                "referenceId": None, "differences": [],
            })
            continue
        if name == "ARMED TURRET":
            matching = [o for o in objects if o["originRuleId"] == "weapon:armed-turret"]
        else:
            selector = SOURCE_SELECTORS[name]
            matching = [
                obj for obj in objects
                if obj["sourceProfile"] is not None
                and (
                    obj["sourceProfile"]["catalog"],
                    obj["sourceProfile"]["name"],
                    obj["sourceProfile"]["mode"],
                ) == selector
            ]
        if len(matching) != 1:
            raise ValueError(f"Missing or ambiguous reviewed p.74 identity: {name}")
        obj = matching[0]
        differences = []
        known_source_disputes = []
        for field in KEYS:
            attribute = obj["attributes"][field]
            if attribute["status"] == "disputed":
                known_source_disputes.append({
                    "field": field,
                    "printed": row["printedAttributes"][field],
                    "alternatives": attribute["provenance"],
                })
            if attribute["status"] == "unreported":
                differences.append({
                    "field": field, "printed": row["printedAttributes"][field],
                    "reviewed": None, "status": "unreported",
                })
            elif int(attribute["value"]) != row["printedAttributes"][field]:
                if attribute["status"] != "disputed" or not any(
                    int(item["value"]) == row["printedAttributes"][field]
                    for item in attribute["provenance"]
                ):
                    raise ValueError(f"Unreviewed p.74 profile disagreement: {name}.{field}")
                differences.append({
                    "field": field,
                    "printed": row["printedAttributes"][field],
                    "reviewed": int(attribute["value"]),
                    "status": "known-source-conflict",
                })
        result.append({
            **row, "referenceId": obj["id"], "differences": differences,
            "knownSourceDisputes": known_source_disputes,
            "disposition": "documented-conflict" if differences else "matched-reviewed",
        })
    duplicates = {
        name: count for name, count in sorted(Counter(
            row["referenceId"] for row in result if row["referenceId"] is not None
        ).items()) if count > 1
    }
    return {
        "scope": "p74-source-table-cross-check-not-complete-object-inventory",
        "printedRows": len(result),
        "distinctReferenceObjects": len({
            row["referenceId"] for row in result if row["referenceId"] is not None
        }),
        "familyRows": sum(r["disposition"] == "family-not-single-object" for r in result),
        "duplicateReferenceRows": duplicates,
        "conflictingRows": [
            row for row in result if row["disposition"] == "documented-conflict"
        ],
        "rowsWithKnownSourceDisputes": [
            row for row in result if row.get("knownSourceDisputes")
        ],
        "rows": result,
    }


def audit_p74(
    pdf: Path, army_db: Path, curated: Path,
    delivery_reviews: Path, candidate_reviews: Path,
) -> dict[str, Any]:
    try:
        import fitz  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ValueError("Install PyMuPDF for pinned p.74 source extraction") from exc
    with fitz.open(pdf) as document:
        if len(document) < PAGE:
            raise ValueError("Pinned PDF lacks p.74")
        page_text = document[PAGE - 1].get_text("text", sort=True)
        if not isinstance(page_text, str):
            raise ValueError("Pinned PDF page text extraction returned an invalid type")
        printed = parse_quick_profiles(page_text)
    reference = project_deployed_references(
        audit_inventory(army_db, curated, delivery_reviews, candidate_reviews)
    )
    return {
        **compare_quick_profiles(printed, reference),
        "pdfSha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        "sourceSnapshot": reference["sourceSnapshot"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=Path("data/pdf/rules/n5-rules-v5-3-en.pdf"))
    parser.add_argument("--army-db", type=Path, default=Path("data/generated/infinity.db"))
    parser.add_argument(
        "--curated", type=Path,
        default=Path("data/curated/rules/n5-core-v5.3.json"),
    )
    parser.add_argument(
        "--delivery-reviews", type=Path,
        default=Path("config/validation/deployed-object-delivery-reviews.json"),
    )
    parser.add_argument(
        "--candidate-reviews", type=Path,
        default=Path("config/validation/deployed-object-candidate-reviews.json"),
    )
    args = parser.parse_args()
    print(json.dumps(
        audit_p74(
            args.pdf, args.army_db, args.curated,
            args.delivery_reviews, args.candidate_reviews,
        ), indent=2, ensure_ascii=False,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
