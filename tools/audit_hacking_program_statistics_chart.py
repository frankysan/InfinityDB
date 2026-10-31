"""Audit N5.3 p. 58 Hacking Program statistics independently of device access.

Program identity is name-based: the Army metadata and printed PDF have
different row orders. This is read-only; it never changes imported Army facts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
import zipfile
from pathlib import Path
from typing import Any

from infinity_db.database.repository import Database

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config/validation/hacking-program-statistics-source-chart.json"
ARMY_DB = ROOT / "data/generated/infinity.db"
PDF = ROOT / "data/pdf/rules/n5-rules-v5-3-en.pdf"
EXPECTED_NAMES = (
    "Assisted Fire", "Carbonite", "Controlled Jump", "Cybermask",
    "Enhanced Reaction", "Fairy Dust", "Oblivion", "Total Control",
    "Trinity", "Spotlight", "White Noise", "Zero Pain",
)
EXPECTED_CLASSIFICATION = {
    "scope": "individual-hacking-program-profile-statistics-not-device-access",
    "comparison": "source-order-independent-name-match",
    "special": "reviewed-equivalent-clause-fragments-not-verbatim-identity",
    "sourceMinus": "literal-dash-not-zero-or-absent-carrier",
    "target": "source-column-set-not-army-list-ownership",
}
VALUE_FIELDS = ("attackMod", "opponentMod", "ps", "burst")
SOURCE_FIELDS = ("attack", "opponent", "damage", "burst")
DATABASE_FIELDS = ("attack_mod", "opponent_mod", "ps", "burst")


def normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).upper().split())


def program_key(value: str) -> str:
    return normalized(value).lower().replace(" ", "-")


def skill_type(value: str) -> str:
    return {"entire order": "long skill", "short": "short skill"}.get(
        value.casefold(), value.casefold(),
    )


def _indexed(rows: list[dict[str, Any]], *, label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str):
            raise ValueError(f"Invalid {label} row")
        key = program_key(row["name"])
        if key in result:
            raise ValueError(f"Duplicate {label} Program: {key}")
        result[key] = row
    return result


def audit_statistics(
    manifest: dict[str, Any],
    database_rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Cross-check exact printed columns and independently preserved Army facts."""
    if set(manifest) != {
        "formatVersion", "sourceId", "sourcePage", "sourcePdfSha256",
        "armyArchive", "armyArchiveSha256", "armyMember",
        "reviewStatus", "classification", "rows",
    } or (
        manifest["formatVersion"] != 1
        or manifest["sourceId"] != "n5-core-v5.3-pdf"
        or manifest["sourcePage"] != 58
        or manifest["reviewStatus"] != "source-reviewed-audit-only"
        or manifest["classification"] != EXPECTED_CLASSIFICATION
        or manifest["armyArchive"] != "data/raw/JSON 20260929-114335.zip"
        or manifest["armyMember"] != "metadata.json"
        or any(
            not isinstance(manifest.get(field), str)
            or not re.fullmatch(r"[0-9a-f]{64}", manifest[field])
            for field in ("sourcePdfSha256", "armyArchiveSha256")
        )
    ):
        raise ValueError("Unexpected N5.3 Hacking Programs statistics provenance")
    rows = manifest["rows"]
    if not isinstance(rows, list) or len(rows) != 12 or (
        tuple(row.get("name") for row in rows if isinstance(row, dict)) != EXPECTED_NAMES
    ):
        raise ValueError("Printed Hacking Programs chart row count/order drift")
    if len(database_rows) != 12:
        raise ValueError("Expected exactly 12 published Army Hacking Programs")
    pinned = _indexed(rows, label="PDF")
    actual = _indexed(database_rows, label="published")
    if set(actual) != set(pinned):
        raise ValueError("Published Program identities differ from printed N5.3 chart")
    source = _indexed(source_rows, label="Army archive") if source_rows is not None else None
    if source is not None and set(source) != set(pinned):
        raise ValueError("Army archive Program identities differ from printed N5.3 chart")
    mismatches: list[dict[str, str]] = []
    for row in rows:
        key = program_key(row["name"])
        if set(row) != {
            "name", "attackMod", "opponentMod", "ps", "burst",
            "targets", "skillTypes", "specialEvidence",
        }:
            raise ValueError(f"Unexpected statistics source fields: {key}")
        entry = actual[key]
        for printed, db in zip(VALUE_FIELDS, DATABASE_FIELDS, strict=True):
            if not isinstance(row[printed], str):
                raise ValueError(f"Invalid printed scalar for {key}: {printed}")
            if row[printed] != entry[db]:
                mismatches.append({
                    "program": key, "field": printed,
                    "pdf": row[printed], "army": str(entry[db]),
                })
        for key_name, db_name in (("targets", "targets"), ("skillTypes", "skill_types")):
            expected = row[key_name]
            if not isinstance(expected, list) or any(not isinstance(x, str) for x in expected):
                raise ValueError(f"Invalid source {key_name}: {key}")
            conversion = (
                (lambda x: normalized(x))
                if key_name == "targets" else (lambda x: normalized(skill_type(x)))
            )
            printed_values = [normalized(x) for x in expected]
            army_values = [conversion(x) for x in entry[db_name]]
            if len(set(printed_values)) != len(printed_values) or (
                sorted(printed_values) != sorted(army_values)
            ):
                mismatches.append({
                    "program": key, "field": key_name,
                    "pdf": str(expected), "army": str(entry[db_name]),
                })
        evidence = row["specialEvidence"]
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"Missing reviewed Special evidence: {key}")
        for item in evidence:
            if not isinstance(item, dict) or set(item) != {"pdf", "army"} or any(
                not isinstance(item[side], str) or not item[side].strip()
                for side in ("pdf", "army")
            ):
                raise ValueError(f"Malformed Special evidence: {key}")
            if normalized(item["army"]) not in normalized(entry["special"]):
                mismatches.append({
                    "program": key, "field": "special", "pdf": item["pdf"],
                    "army": str(entry["special"]),
                })
        if source is not None:
            assert source_rows is not None
            archived = source[key]
            for db, upstream in zip(DATABASE_FIELDS, SOURCE_FIELDS, strict=True):
                if entry[db] != archived[upstream]:
                    raise ValueError(f"Published Army metadata drift: {key} {db}")
            if normalized(entry["special"]) != normalized(archived["special"]):
                raise ValueError(
                    f"Published Army Special text drift: {key}; "
                    f"db={entry['special']!r} archive={archived['special']!r}"
                )
            if entry["targets"] != archived.get("target", []):
                raise ValueError(f"Published Army targets drift: {key}")
            if entry["skill_types"] != archived["skillType"]:
                raise ValueError(f"Published Army declaration type drift: {key}")
            if entry["position"] != source_rows.index(archived) + 1:
                raise ValueError(f"Published Army Program position drift: {key}")
    return {
        "scope": EXPECTED_CLASSIFICATION["scope"],
        "sourcePage": 58,
        "rowCount": len(rows),
        "sourceOrder": [program_key(row["name"]) for row in rows],
        "armyOrder": [program_key(row["name"]) for row in database_rows],
        "orderDiffers": [program_key(row["name"]) for row in rows] != [
            program_key(row["name"]) for row in database_rows
        ],
        "archiveReconciled": source is not None,
        "statisticsMismatches": mismatches,
        "specialComparison": EXPECTED_CLASSIFICATION["special"],
        "deviceEntitlementsIncluded": False,
    }


def read_archived_programs(path: Path, member: str) -> list[dict[str, Any]]:
    with zipfile.ZipFile(path) as source:
        content = json.loads(source.read(member))
    rows = content["hack"]
    if not isinstance(rows, list):
        raise ValueError("Pinned Army metadata lacks Hacking Program array")
    return rows


def _column_words(words: list[Any], start: float, end: float) -> list[str]:
    selected = sorted(
        (word for word in words if start <= float(word[0]) < end),
        key=lambda word: (round(float(word[1]) / 3), float(word[0])),
    )
    return [normalized(str(word[4])).strip(".,") for word in selected]


def verify_pdf(path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    try:
        import pymupdf  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ValueError("PDF verification requires PyMuPDF") from exc
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["sourcePdfSha256"]:
        raise ValueError("N5.3 PDF fingerprint differs from pinned source")
    with pymupdf.open(path) as doc:
        page = doc[57]
        words = page.get_text("words")
        plain = normalized(str(page.get_text("text", sort=False)))
    if not (
        "HACKING PROGRAMS CHART" in plain
        and "HACKER DEVICE PROGRAMS CHART" in plain
    ):
        raise ValueError("N5.3 PDF chart titles or boundary changed")
    # Words from the first chart are checked with positional row boundaries.
    # Section/chart headings and the following Device matrix are excluded.
    names = [row["name"] for row in manifest["rows"]]
    starts = [normalized(name).split()[0] for name in names]
    anchors = []
    for start in starts:
        candidates = [
            word for word in words
            if normalized(str(word[4])) == start and float(word[0]) < 160
        ]
        if not candidates:
            raise ValueError(f"Missing printed Hacking Program: {start}")
        later = [word for word in candidates if not anchors or word[1] > anchors[-1][1]]
        if not later:
            raise ValueError(f"Printed Hacking Program row order drift: {start}")
        anchors.append(min(later, key=lambda word: word[1]))
    for index, row in enumerate(manifest["rows"]):
        y = float(anchors[index][1])
        y0 = (float(anchors[index - 1][1]) + y) / 2 if index else y - 14
        y1 = (
            (y + float(anchors[index + 1][1])) / 2
            if index + 1 < len(anchors) else y + 35
        )
        row_words = [word for word in words if y0 <= float(word[1]) < y1]

        if " ".join(_column_words(row_words, 20, 110)) != normalized(row["name"]):
            raise ValueError(f"N5.3 printed Program name mismatch: {row['name']}")
        for field, left, right in (
            ("attackMod", 120, 165), ("opponentMod", 165, 219),
            ("ps", 219, 255), ("burst", 255, 285),
        ):
            if _column_words(row_words, left, right) != [row[field]]:
                raise ValueError(f"N5.3 printed {field} cell mismatch: {row['name']}")
        targets = _column_words(row_words, 285, 337)
        if targets == ["-"]:
            targets = []
        if targets != [normalized(target) for target in row["targets"]]:
            raise ValueError(f"N5.3 printed target cell mismatch: {row['name']}")
        declarations = " ".join(_column_words(row_words, 337, 392))
        expected_declarations = " / ".join(normalized(x) for x in row["skillTypes"])
        if declarations != expected_declarations:
            raise ValueError(f"N5.3 printed Skill Type cell mismatch: {row['name']}")
        special = " ".join(_column_words(row_words, 392, 590)).replace("- ", "-")
        for evidence in row["specialEvidence"]:
            if normalized(evidence["pdf"]) not in special:
                raise ValueError(
                    f"N5.3 printed Special clause drift: {row['name']} ({evidence['pdf']})"
                )
    return {"verifiedPdfSha256": manifest["sourcePdfSha256"], "verifiedRows": len(anchors)}


def audit_files(
    *, manifest_path: Path = MANIFEST, db_path: Path = ARMY_DB,
    archive_path: Path | None = None, pdf_path: Path | None = None,
) -> dict[str, Any]:
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    archive_rows = None
    archive_hash = None
    if archive_path is not None:
        archive_hash = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        if archive_hash != manifest["armyArchiveSha256"]:
            raise ValueError("Pinned Army archive SHA-256 mismatch")
        archive_rows = read_archived_programs(archive_path, manifest["armyMember"])
    report = audit_statistics(manifest, Database(db_path).list_hacking_programs(), archive_rows)
    if report["statisticsMismatches"]:
        raise ValueError(
            f"N5.3 Hacking Program statistics differ: {report['statisticsMismatches']}"
        )
    pdf = verify_pdf(pdf_path, manifest) if pdf_path is not None else None
    return {
        **report,
        "manifestSha256": hashlib.sha256(raw).hexdigest(),
        "armyArchiveSha256": archive_hash,
        "verifiedPdfSha256": pdf["verifiedPdfSha256"] if pdf else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--db", type=Path, default=ARMY_DB)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--pdf", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = audit_files(
        manifest_path=args.manifest, db_path=args.db,
        archive_path=args.archive, pdf_path=args.pdf,
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"N5.3 Hacking Program statistics: {result['rowCount']} rows; "
              f"{len(result['statisticsMismatches'])} mismatches")
        print(f"Army/PDF row ordering differs: {result['orderDiffers']}")
        print(f"Archive matched: {result['archiveReconciled']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
