"""Audit independent N5.3 Retreat! and advisory game-table reference rows.

Neither the Retreat! situation threshold nor the recommended table dimensions
are permanent Unit attributes or authoritative scenario-specific setup.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_document

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/validation/standard-game-reference-tables.json"
CURATED = ROOT / "data/curated/rules/n5-core-v5.3.json"
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"

# Reviewed directly from N5.3 English printed pp. 146-147.
PINNED = (
    (150, 38, (24, 32)),
    (200, 50, (32, 48)),
    (250, 63, (32, 48)),
    (300, 75, (48, 48)),
    (350, 88, (48, 48)),
    (400, 100, (48, 48)),
)
REQUIRED_SOURCE_RECORDS = {
    "state:retreat": ("state", 170),
    "term:victory-points": ("term", 173),
}
THRESHOLD_RULE = {
    "comparison": "current-victory-points-less-than-or-equal-to-threshold",
    "basis": "army-points-available-for-building-list",
    "percent": 25,
    "checkPhase": "beginning-of-active-turn-tactical-phase",
    "domain": "army-session-not-unit-or-trooper-attribute",
}
TABLE_RULE = {
    "scope": "advisory-not-mandatory",
    "domain": "generic-table-setup-not-scenario-override",
    "units": "inches",
}


def audit_reference_tables(manifest: dict[str, Any], curated: dict[str, Any]) -> dict[str, Any]:
    """Fail closed on source, sizes, scope and unrelated model identities."""
    if set(manifest) != {
        "formatVersion", "sourceId", "sourcePages", "reviewStatus",
        "thresholdRule", "tableSizeRule", "rows",
    }:
        raise ValueError("Unexpected reference table schema")
    if (
        type(manifest["formatVersion"]) is not int
        or manifest["formatVersion"] != 1
        or manifest["sourceId"] != "n5-core-v5.3-pdf"
        or manifest["sourcePages"] != {
            "retreatThresholds": 146, "recommendedTables": 147,
        }
        or manifest["reviewStatus"] != "source-reviewed-audit-only"
        or manifest["thresholdRule"] != THRESHOLD_RULE
        or manifest["tableSizeRule"] != TABLE_RULE
    ):
        raise ValueError("N5.3 source provenance or scope drift")
    rows = manifest["rows"]
    if not isinstance(rows, list) or len(rows) != len(PINNED):
        raise ValueError("Expected six game-size reference rows")
    for index, (row, (points, threshold, dimensions)) in enumerate(
        zip(rows, PINNED, strict=True),
    ):
        if not isinstance(row, dict) or set(row) != {
            "armyPoints", "retreatThresholdVictoryPoints", "recommendedTableInches",
        }:
            raise ValueError(f"Reference table row schema drift: {index}")
        if (
            type(row["armyPoints"]) is not int
            or type(row["retreatThresholdVictoryPoints"]) is not int
            or row["armyPoints"] != points
            or row["retreatThresholdVictoryPoints"] != threshold
            or row["recommendedTableInches"] != list(dimensions)
            or (points + 3) // 4 != threshold
        ):
            raise ValueError(f"Printed N5.3 game-size reference row drift: {points}")
    records = {record["id"]: record for record in curated["records"]}
    if len(records) != len(curated["records"]):
        raise ValueError("Duplicate maintained rule ID")
    for record_id, (kind, page) in REQUIRED_SOURCE_RECORDS.items():
        record = records.get(record_id)
        if (
            record is None
            or record["kind"] != kind
            or not any(
                cite.get("sourceId") == "n5-core-v5.3-pdf"
                and cite.get("page") == page
                for cite in record.get("citations", [])
            )
        ):
            raise ValueError(f"Maintained retreat/victory concept drift: {record_id}")
    if "rule:retreat-threshold" in records or "rule:recommended-table-size" in records:
        raise ValueError("New maintained setup reference needs explicit source review")
    return {
        "scope": "audit-only-army-session-threshold-and-advisory-setup",
        "retreatThresholdSourcePage": 146,
        "tableSizeSourcePage": 147,
        "rowCount": len(rows),
        "thresholdComparison": manifest["thresholdRule"]["comparison"],
        "thresholdDomain": manifest["thresholdRule"]["domain"],
        "tableSizeScope": manifest["tableSizeRule"]["scope"],
        "tableSizeDomain": manifest["tableSizeRule"]["domain"],
        "linkedMaintainedReferences": list(REQUIRED_SOURCE_RECORDS),
        "rows": rows,
    }


def verify_pinned_pdf(path: Path, manifest: dict[str, Any]) -> str:
    """Independently compare all six source rows with printed English N5.3."""
    try:
        import pymupdf  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ValueError("PDF verification requires PyMuPDF") from exc
    raw = path.read_bytes()
    with pymupdf.open(stream=raw, filetype="pdf") as source:
        if len(source) < 147:
            raise ValueError("N5.3 PDF missing printed source pages")
        text: dict[int, str] = {}
        for page in (146, 147):
            extracted = source[page - 1].get_text("text", sort=False)
            if not isinstance(extracted, str):
                raise ValueError(f"Missing PDF source text on page {page}")
            text[page] = " ".join(extracted.upper().split())
        retreat_words = source[145].get_text("words")
    if "RETREAT!" not in text[146] or "25%" not in text[146]:
        raise ValueError("Retreat! source rule missing from printed page")
    if "SETTING UP" not in text[147] or "NOT MANDATORY" not in text[147]:
        raise ValueError("Advisory table setup qualifier missing from PDF")
    for row in manifest["rows"]:
        points = row["armyPoints"]
        threshold = row["retreatThresholdVictoryPoints"]
        point_cells = [word for word in retreat_words if word[4] == str(points)]
        threshold_cells = [word for word in retreat_words if word[4] == str(threshold)]
        if not any(
            right[0] > left[2] and abs(float(right[1]) - float(left[1])) <= 6
            for left in point_cells for right in threshold_cells
        ):
            raise ValueError(f"Retreat! source table row mismatch: {points}")
    # The table-size recommendations group Army Points into three ranges.
    for phrase in (
        'FOR A 150-POINT GAME, USE A 24” X 32” GAME TABLE',
        'FOR A 200 OR 250-POINT GAME, USE A 32” X 48” GAME TABLE',
        'FOR A 300, 350 OR 400-POINT GAME, USE A 48” X 48” GAME TABLE',
    ):
        if phrase not in text[147]:
            raise ValueError(f"Advisory table-size source drift: {phrase}")
    return hashlib.sha256(raw).hexdigest()


def audit_source_files(
    manifest_path: Path = MANIFEST,
    curated_path: Path = CURATED,
    pdf_path: Path | None = None,
) -> dict[str, Any]:
    manifest_raw = manifest_path.read_bytes()
    curated_raw = curated_path.read_bytes()
    manifest = json.loads(manifest_raw)
    report = audit_reference_tables(manifest, load_curated_document(curated_path))
    return {
        **report,
        "manifestSha256": hashlib.sha256(manifest_raw).hexdigest(),
        "curatedSha256": hashlib.sha256(curated_raw).hexdigest(),
        "verifiedPdfSha256": (
            verify_pinned_pdf(pdf_path, manifest) if pdf_path is not None else None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--curated", type=Path, default=CURATED)
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = audit_source_files(args.manifest, args.curated, args.pdf)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Retreat! and table-setup source rows: {result['rowCount']}")
        for row in result["rows"]:
            print(
                f"  {row['armyPoints']} Army Points: Retreat! <= "
                f"{row['retreatThresholdVictoryPoints']} VP; advisory table "
                f"{row['recommendedTableInches'][0]} x {row['recommendedTableInches'][1]} in"
            )
        print("Threshold: army/session game state, not a Unit/Profile attribute")
        print("Table sizes: advisory setup, not scenario overrides")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
