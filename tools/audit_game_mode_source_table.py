"""Validate N5.3 p. 6 recommended Game Modes against independent setup tables.

The chart is general guidance: it does not override a scenario's owned
geometry, forces, deployment rules, or special SWC allowances.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tools.audit_standard_game_reference_tables import MANIFEST as SETUP_MANIFEST

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
MANIFEST = ROOT / "config/validation/game-mode-source-table.json"
PINNED = (
    ("Beginner Games", 150, 3, (24, 32), (8, 24), 40),
    ("Raid Games", 200, 4, (32, 48), (8, 32), 50),
    ("Intermediate Games", 250, 5, (32, 48), (8, 32), 60),
    ("Standard Games", 300, 6, (48, 48), (12, 48), 90),
    ("Magnum Games, and Games with Reinforcements", 350, 7, (48, 48), (12, 48), 100),
    ("Large-Scale Games", 400, 8, (48, 48), (12, 48), 120),
)
CLASSIFICATION = {
    "scope": "recommended-game-modes-not-mandatory-scenario-rules",
    "deploymentZone": "two-dimensional-per-player-inches",
    "gameDuration": "recommended-minutes-not-round-count",
    "swc": "base-allowance-excludes-unit-specific-bonuses",
}


def audit_game_mode_source(
    manifest: dict[str, Any], setup: dict[str, Any],
) -> dict[str, Any]:
    """Fail closed on changed chart values or incorrect cross-domain scope."""
    if set(manifest) != {
        "formatVersion", "sourceId", "sourcePage", "reviewStatus",
        "classification", "rows",
    }:
        raise ValueError("Unexpected N5.3 Game Modes manifest fields")
    if (
        type(manifest["formatVersion"]) is not int
        or manifest["formatVersion"] != 1
        or manifest["sourceId"] != "n5-core-v5.3-pdf"
        or manifest["sourcePage"] != 6
        or manifest["reviewStatus"] != "source-reviewed-audit-only"
        or manifest["classification"] != CLASSIFICATION
    ):
        raise ValueError("Game Modes source attribution/scope drift")
    rows = manifest["rows"]
    if not isinstance(rows, list) or len(rows) != len(PINNED):
        raise ValueError("Expected exactly six recommended Game Mode rows")
    if setup.get("sourceId") != manifest["sourceId"] or setup.get("sourcePages") != {
        "retreatThresholds": 146, "recommendedTables": 147,
    }:
        raise ValueError("Independent standard-game table provenance drift")
    setup_rows = setup.get("rows")
    if not isinstance(setup_rows, list) or len(setup_rows) != len(PINNED):
        raise ValueError("Independent standard-game table row count drift")
    for index, (row, expected, common) in enumerate(
        zip(rows, PINNED, setup_rows, strict=True),
    ):
        if not isinstance(row, dict) or set(row) != {
            "name", "armyPoints", "swc", "tableInches",
            "deploymentZoneInches", "durationMinutes",
        }:
            raise ValueError(f"Game Mode row schema drift: {index}")
        name, points, swc, table, zone, minutes = expected
        if (
            row["name"] != name
            or type(row["armyPoints"]) is not int
            or type(row["swc"]) is not int
            or type(row["durationMinutes"]) is not int
            or row["armyPoints"] != points
            or row["swc"] != swc
            or row["tableInches"] != list(table)
            or row["deploymentZoneInches"] != list(zone)
            or row["durationMinutes"] != minutes
            or row["swc"] * 50 != points
        ):
            raise ValueError(f"N5.3 Game Modes chart drift: row {index}")
        if not isinstance(common, dict) or (
            common.get("armyPoints") != points
            or common.get("recommendedTableInches") != list(table)
            or common.get("retreatThresholdVictoryPoints") != (points + 3) // 4
        ):
            raise ValueError(f"Independent table-size / Retreat! cross-check failed: {points}")
    return {
        "scope": CLASSIFICATION["scope"],
        "sourcePage": 6,
        "corroboratingSourcePages": [146, 147],
        "rowCount": len(rows),
        "deploymentZoneScope": CLASSIFICATION["deploymentZone"],
        "durationScope": CLASSIFICATION["gameDuration"],
        "swcScope": CLASSIFICATION["swc"],
        "rows": rows,
    }


def verify_pinned_pdf(path: Path, manifest: dict[str, Any]) -> str:
    """Verify source headings and independent row cells on printed p. 6."""
    try:
        import pymupdf  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ValueError("PDF verification requires PyMuPDF") from exc
    raw = path.read_bytes()
    with pymupdf.open(stream=raw, filetype="pdf") as source:
        if len(source) < 6:
            raise ValueError("N5.3 PDF lacks printed Game Modes source")
        page = source[5]
        words = page.get_text("words")
        extracted = page.get_text("text", sort=False)
        if not isinstance(extracted, str):
            raise ValueError("Could not read Game Modes PDF page text")
        text = " ".join(extracted.upper().split())
    if not all(heading in text for heading in (
        "GAME MODES", "TABLE", "DEPLOYMENT", "ARMY", "SWC", "DURATION",
    )):
        raise ValueError("N5.3 printed Game Modes heading drift")
    for row in manifest["rows"]:
        points = row["armyPoints"]
        swc = row["swc"]
        minutes = row["durationMinutes"]
        # Use row coordinates rather than two-column extraction order.
        points_cells = [word for word in words if word[4] == str(points)]
        swc_cells = [word for word in words if word[4] == str(swc)]
        minute_cells = [word for word in words if word[4] == str(minutes)]
        if not any(
            left[0] < middle[0] < right[0]
            and abs(float(left[1]) - float(middle[1])) < 12
            and abs(float(left[1]) - float(right[1])) < 12
            for left in points_cells
            for middle in swc_cells
            for right in minute_cells
        ):
            raise ValueError(f"N5.3 Game Modes source row mismatch: {points}")
    # Table-size and Deployment Zone dimensions precede Army Points and
    # may be wrapped onto adjacent baselines. Verify local row geometry.
    for row in manifest["rows"]:
        points = str(row["armyPoints"])
        table_w, table_h = map(str, row["tableInches"])
        zone_depth, zone_width = map(str, row["deploymentZoneInches"])
        anchors = [word for word in words if word[4] == points]
        match_found = False
        for anchor in anchors:
            baseline = (float(anchor[1]) + float(anchor[3])) / 2
            nearby = [
                word for word in words
                if word[0] < anchor[0]
                and abs((float(word[1]) + float(word[3])) / 2 - baseline) <= 21
            ]
            table_pairs = [
                (left, right)
                for left in nearby for right in nearby
                if left[4] == table_w and right[4] == table_h
                and 0 < float(right[0]) - float(left[0]) < 46
            ]
            zone_pairs = [
                (left, right)
                for left in nearby for right in nearby
                if left[4] == zone_depth and right[4] == zone_width
                and 0 < float(right[0]) - float(left[0]) < 46
            ]
            if any(
                table_right[0] < zone_left[0] < zone_right[0] < anchor[0]
                for _, table_right in table_pairs
                for zone_left, zone_right in zone_pairs
            ):
                match_found = True
                break
        if not match_found:
            raise ValueError(f"N5.3 Game Modes source dimensions mismatch: {points}")
    for mode in ("BEGINNER GAMES", "RAID GAMES", "INTERMEDIATE", "STANDARD GAMES",
                 "MAGNUM GAMES", "LARGE-SCALE"):
        if mode not in text:
            raise ValueError(f"Missing N5.3 source Game Mode: {mode}")
    return hashlib.sha256(raw).hexdigest()


def audit_source_files(
    manifest_path: Path = MANIFEST,
    setup_path: Path = SETUP_MANIFEST,
    pdf_path: Path | None = None,
) -> dict[str, Any]:
    raw = manifest_path.read_bytes()
    setup_raw = setup_path.read_bytes()
    manifest = json.loads(raw)
    report = audit_game_mode_source(manifest, json.loads(setup_raw))
    return {
        **report,
        "gameModesSha256": hashlib.sha256(raw).hexdigest(),
        "independentSetupSha256": hashlib.sha256(setup_raw).hexdigest(),
        "verifiedPdfSha256": verify_pinned_pdf(pdf_path, manifest) if pdf_path else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--setup", type=Path, default=SETUP_MANIFEST)
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = audit_source_files(args.manifest, args.setup, args.pdf)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Game Modes source rows: {report['rowCount']}")
        for row in report["rows"]:
            print(
                f"  {row['armyPoints']} pts: {row['name']}; "
                f"SWC {row['swc']}; {row['durationMinutes']} minutes"
            )
        print("Reference only: scenario-specific setup and forces take precedence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
