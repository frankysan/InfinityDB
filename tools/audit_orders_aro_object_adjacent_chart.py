"""Audit selected N5.3 p. 191 Orders/AROs chart entries adjacent to object use.

This source-table audit is intentionally narrower than the planned generated
declaration matrix. Printed Equipment actions, Skills and Programs are
different owning domains; neither a chart row nor an ARO category grants
an additional deployed-object identity or Unit ownership.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/validation/orders-aro-object-adjacent-source-review.json"
CORE = ROOT / "data/curated/rules/n5-core-v5.3.json"
HACKING = ROOT / "data/curated/rules/n5-hacking-programs-v5.3.json"
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
EXPECTED_COUNT = 15
SECTIONS = {"long", "short", "aro"}
SOURCE_TYPES = {"COMMON", "SPECIAL", "EQUIPMENT", "HACKING"}
EXPECTED_SCOPE = "selected-object-adjacent-declaration-rows-not-full-orders-aro-chart"


def check_rows(manifest: dict[str, Any], records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Check a bounded source transcription and independently owned record identities."""
    if (
        manifest.get("formatVersion") != 1
        or manifest.get("scope") != EXPECTED_SCOPE
        or manifest.get("sourceId") != "n5-core-v5.3-pdf"
        or manifest.get("sourcePage") != 191
        or manifest.get("reviewStatus") != "source-reviewed-audit-only"
        or manifest.get("sourceChartIsObjectInventory") is not False
        or not re.fullmatch(r"[0-9a-f]{64}", str(manifest.get("sourcePdfSha256", "")))
    ):
        raise ValueError("Invalid p. 191 audit-only source provenance")
    rows = manifest.get("rows")
    if not isinstance(rows, list) or len(rows) != EXPECTED_COUNT:
        raise ValueError("Selected p. 191 declaration row-count drift")
    seen: set[tuple[str, str]] = set()
    represented: dict[str, list[str]] = {}
    untyped: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "section", "name", "sourceType", "sourcePage", "recordId"
        }:
            raise ValueError("Malformed p. 191 declaration row")
        section, name = row["section"], row["name"]
        source_type, source_page, record_id = (
            row["sourceType"], row["sourcePage"], row["recordId"]
        )
        if (
            section not in SECTIONS or source_type not in SOURCE_TYPES
            or not isinstance(name, str) or not name
            or type(source_page) is not int or not 1 <= source_page < 191
            or not isinstance(record_id, str)
        ):
            raise ValueError(f"Invalid p. 191 declaration values: {row}")
        key = (section, name.casefold())
        if key in seen:
            raise ValueError(f"Duplicate p. 191 declaration: {key}")
        seen.add(key)
        record = records.get(record_id)
        if record is None or record.get("name", "").casefold() != name.casefold() or (
            record.get("composition") or {}
        ).get("role") != "definition" or record.get("scope") != {
            "game": "N5", "seasons": ["current"]
        }:
            raise ValueError(f"Missing current canonical declaration owner: {record_id}")
        kind = record.get("kind")
        if source_type == "HACKING" and kind != "hacking-program":
            raise ValueError(f"Hacking Program owner drift: {record_id}")
        if source_type in {"COMMON", "SPECIAL"} and kind != "skill":
            raise ValueError(f"Skill owner drift: {record_id}")
        if source_type == "EQUIPMENT" and kind != (
            "skill" if name == "Activate Disco Ball" else "equipment"
        ):
            raise ValueError(f"Action-like Equipment owner drift: {record_id}")
        if kind in {"skill", "hacking-program"}:
            # A core Skill can have maintained categories; Hacking declarations
            # instead live in Army metadata and require the later full projection.
            types = (record.get("facts") or {}).get("typeIds", [])
            requested = {
                "long": "long-skill", "short": "short-skill", "aro": "aro"
            }[section]
            if kind == "skill":
                if requested not in types:
                    untyped.append(f"{record_id}:{section}")
            else:
                untyped.append(f"{record_id}:{section}")
        represented.setdefault(section, []).append(record_id)
    if {key[0] for key in seen} != SECTIONS:
        raise ValueError("Missing a selected p. 191 declaration section")
    if not all(
        (section, name) in seen for section, name in (
            ("short", "place deployable"), ("aro", "place deployable"),
            ("short", "reload"), ("aro", "reload"),
            ("short", "activate disco ball"), ("short", "deactivator")
        )
    ):
        raise ValueError("Required object-adjacent declarations missing")
    return {
        "scope": EXPECTED_SCOPE,
        "sourcePage": 191,
        "selectedRows": len(rows),
        "distinctOwners": len({row["recordId"] for row in rows}),
        "rowsByDeclaration": {key: len(value) for key, value in represented.items()},
        "missingCuratedSkillTypesOrSeparatelyOwnedProgramTypes": untyped,
        "fullChartCertified": False,
        "publishedObjectIdentityChanges": 0,
        "newDeliveryEdges": 0,
    }


def verify_pdf(source: Path, manifest: dict[str, Any]) -> str:
    """Match selected cells on the printed source page by geometric row."""
    try:
        import pymupdf  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ValueError("PDF verification requires PyMuPDF") from exc
    source_bytes = source.read_bytes()
    digest = hashlib.sha256(source_bytes).hexdigest()
    if digest != manifest["sourcePdfSha256"]:
        raise ValueError("Pinned N5.3 PDF SHA-256 differs")
    with pymupdf.open(stream=source_bytes, filetype="pdf") as document:
        page = document[190]
        words = page.get_text("words")
        # The right chart starts before the physical page midpoint; some
        # multiword names extend left of that midpoint.
        middle = page.rect.width * 0.43
        aro_headings = [
            rect for rect in page.search_for("AROS")
            if rect.x0 > middle and rect.y0 > page.rect.height * 0.2
        ]
        if len(aro_headings) != 1:
            raise ValueError("Cannot locate p. 191 ARO section boundary")
        lower_start = aro_headings[0].y0
        for row in manifest["rows"]:
            section = row["section"]
            right = section in {"long", "aro"}
            expected_lower = section in {"short", "aro"}
            matches = [
                rect for rect in page.search_for(row["name"])
                if (rect.x0 >= middle) == right
                and (rect.y0 >= lower_start) == expected_lower
            ]
            if len(matches) != 1:
                raise ValueError(
                    f"Missing or ambiguous printed p. 191 declaration: "
                    f"{section} {row['name']} ({len(matches)} matches)"
                )
            name_rect = matches[0]
            x_end = page.rect.width if right else middle
            line = [
                str(word[4]).upper().strip(".,")
                for word in words
                if name_rect.x1 - 2 < float(word[0]) < x_end
                and abs((float(word[1]) + float(word[3])) / 2
                        - (name_rect.y0 + name_rect.y1) / 2) < 5
            ]
            if row["sourceType"] not in line or str(row["sourcePage"]) not in line:
                raise ValueError(
                    f"Printed p. 191 Type/page mismatch for {section} "
                    f"{row['name']}: {line}"
                )
    return digest


def audit(
    manifest_path: Path = MANIFEST,
    core_path: Path = CORE,
    hacking_path: Path = HACKING,
    pdf_path: Path | None = None,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (core_path, hacking_path)
    ]
    records = {
        record["id"]: record for doc in sources
        for record in doc["records"]
    }
    report = check_rows(manifest, records)
    return {
        **report,
        "sourcePdfSha256": manifest["sourcePdfSha256"],
        "verifiedPdfSha256": verify_pdf(pdf_path, manifest) if pdf_path else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, help="Verify against pinned English N5.3 PDF")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = audit(pdf_path=args.pdf)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Selected p. 191 rows: {report['selectedRows']}")
        print(f"Distinct canonical owners: {report['distinctOwners']}")
        print(f"Declaration categories: {report['rowsByDeclaration']}")
        print(f"Skill/Program types needing separate reconciliation: "
              f"{len(report['missingCuratedSkillTypesOrSeparatelyOwnedProgramTypes'])}")
        print(f"Direct PDF verification: {report['verifiedPdfSha256'] is not None}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
