#!/usr/bin/env python3
"""Compare unambiguous N5 v5.3 PDF Weapon Chart rows with shipped Army metadata.

The PDF's wrapped names and multi-mode layouts require a separate review. This
report checks only exact single-line name matches and explicitly names its limits.
Nothing in this tool modifies game data or treats a profile as a rule definition.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

FORMAT = "InfinityDB N5 Weapon Chart profile evidence"
FORMAT_VERSION = 1
PDF_PAGES = range(176, 189)
_FIELDS = ("ps", "burst", "ammunition", "savingAttribute", "savingRolls")


class WeaponChartAuditError(ValueError):
    """Chart structure or input prevents a reproducible comparison."""


def _identity(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^a-z0-9]+", "", text)


def _value(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = re.sub(r"\s+", "", text).upper().replace("−", "-").replace("–", "-")
    return "" if text in {"", "-", "--"} else text


def _fields_equal(pdf: dict[str, str], army: dict[str, str], field: str) -> bool:
    """Compare the printed Saving Rolls count with its Army source expression.

    A source multiplier (``savingNum``) is non-operative when both sources have
    no Saving Attribute and the chart explicitly displays no Saving Rolls.
    Preserve the raw source values in reports rather than changing the metadata.
    """
    if (
        field == "savingRolls"
        and not _value(pdf["savingAttribute"])
        and not _value(army["savingAttribute"])
        and not _value(pdf["savingRolls"])
    ):
        return True
    return _value(pdf[field]) == _value(army[field])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cell(words: list[tuple[float, float, str]], y: float, left: float,
          right: float) -> str:
    return " ".join(
        word for x, wy, word in sorted(words, key=lambda item: item[0])
        if left <= x < right and abs(wy - y) < 3.2
    ).strip()


def rows_from_words(words: list[tuple[float, float, str]], page_number: int
                    ) -> list[dict[str, Any]]:
    """Extract only rows whose name shares the printed Burst value's baseline.

    These coordinates describe the *specific* N5 v5.3 core Weapon Chart. If the
    PDF layout changes, this audit must be reviewed rather than silently reused.
    """
    result: list[dict[str, Any]] = []
    for x, y, word in words:
        if not (294 <= x <= 310 and 175 < y < 800):
            continue
        if re.fullmatch(r"(?:[1-9]|10|--)", word) is None:
            continue
        name = _cell(words, y, 13, 90)
        row = {
            "page": page_number,
            "name": name,
            "ps": _cell(words, y, 263, 293),
            "burst": _cell(words, y, 293, 314),
            "ammunition": _cell(words, y, 315, 367),
            "savingAttribute": _cell(words, y, 367, 418),
            "savingRolls": _cell(words, y, 418, 462),
        }
        result.append(row)
    return result


def _metadata(db: Path) -> tuple[dict[str, list[dict[str, str]]], int]:
    with sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True) as conn:
        ammunition = dict(conn.execute("SELECT id, name FROM metadata_ammunitions"))
        rows = conn.execute(
            "SELECT name, mode, ammunition, burst, damage, saving, savingNum "
            "FROM metadata_weapons"
        ).fetchall()
    indexed: dict[str, list[dict[str, str]]] = {}
    for name, mode, ammo_id, burst, damage, saving, rolls in rows:
        if not isinstance(name, str):
            raise WeaponChartAuditError("Weapon metadata contains an invalid name")
        item = {
            "name": name,
            "mode": str(mode or ""),
            "ps": str(damage or ""),
            "burst": str(burst or ""),
            "ammunition": str(ammunition.get(ammo_id, "")),
            "savingAttribute": str(saving or ""),
            "savingRolls": str(rolls or ""),
        }
        indexed.setdefault(_identity(name), []).append(item)
    return indexed, len(rows)


def compare_rows(chart_rows: list[dict[str, Any]], metadata: dict[str, list[dict[str, str]]]
                 ) -> dict[str, Any]:
    """Count a row as comparable only when exactly one mode/identity matches."""
    compared: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    for row in chart_rows:
        key = _identity(row["name"])
        options = metadata.get(key, []) if key else []
        if len(options) != 1:
            deferred.append({
                "page": row["page"], "extractedName": row["name"],
                "reason": "no-exact-single-line-name" if not options
                else "multiple-army-modes",
            })
            continue
        army = options[0]
        differences = [
            {"field": field, "pdf": row[field], "army": army[field]}
            for field in _FIELDS if not _fields_equal(row, army, field)
        ]
        compared.append({
            "page": row["page"], "name": army["name"],
            "pdf": {field: row[field] for field in _FIELDS},
            "army": {field: army[field] for field in _FIELDS},
            "differences": differences,
            "status": "candidate-discrepancy" if differences else "fields-match",
        })
    return {
        "chartRowsLocated": len(chart_rows),
        "unambiguousRowsCompared": len(compared),
        "matchingRows": sum(r["status"] == "fields-match" for r in compared),
        "candidateDiscrepancies": sum(r["status"] == "candidate-discrepancy" for r in compared),
        "deferredRows": len(deferred),
        "deferredReasons": dict(sorted(Counter(r["reason"] for r in deferred).items())),
        "compared": compared,
        "deferred": deferred,
    }


def audit_chart(pdf: Path, army_db: Path) -> dict[str, Any]:
    """Audit PDF fields without requiring an extra PDF dependency in normal checks."""
    try:
        import fitz  # type: ignore[import-untyped]  # Optional PyMuPDF audit dependency.
    except ImportError as exc:
        raise WeaponChartAuditError(
            "PDF comparison requires PyMuPDF (python -m pip install pymupdf)"
        ) from exc
    with fitz.open(pdf) as doc:
        if len(doc) < max(PDF_PAGES):
            raise WeaponChartAuditError("Core PDF is too short for N5 v5.3 Weapon Chart")
        chart_rows = []
        for page in PDF_PAGES:
            words = [
                (float(w[0]), float(w[1]), str(w[4]))
                for w in doc[page - 1].get_text("words")
            ]
            chart_rows.extend(rows_from_words(words, page))
    # A different PDF export may move columns without changing its page count.
    # Fail closed rather than reporting misleading matches from another layout.
    anchors = {_identity(row["name"]) for row in chart_rows}
    if len(chart_rows) < 100 or not {
        "tacticalbow", "combirifle", "minedispenser"
    }.issubset(anchors):
        raise WeaponChartAuditError("Unrecognized N5 v5.3 Weapon Chart layout")
    metadata, count = _metadata(army_db)
    result = compare_rows(chart_rows, metadata)
    return {
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
        "status": "partial-pdf-profile-evidence-not-completeness",
        "corePdfSha256": _sha256(pdf),
        "armyMetadataProfiles": count,
        "comparison": result,
        "notCompared": [
            "wrapped-name and multimode Weapon Chart rows",
            "range band breakpoints and modifiers",
            "Traits, mode variants, and special-weapon prose on pages 68-74",
            "profile-to-API/browser projection and standalone rule-definition coverage",
        ],
    }


def markdown_report(report: dict[str, Any]) -> str:
    result = report["comparison"]
    lines = [
        "# 1.0 N5 v5.3 Weapon Chart — first structured comparison",
        "",
        "**Partial evidence, not a completeness verdict.** Uses the official PDF pp. 176–188.",
        "No upstream source, Army metadata, or curated gameplay facts are modified.",
        "",
        f"- Core PDF SHA-256: `{report['corePdfSha256']}`",
        f"- Published Army metadata profile rows: **{report['armyMetadataProfiles']}**.",
        f"- PDF chart rows located: **{result['chartRowsLocated']}**.",
        ("- Exact, single-line, unique-mode rows compared: "
         f"**{result['unambiguousRowsCompared']}**."),
        f"- Rows with all five compared fields matching: **{result['matchingRows']}**.",
        f"- Candidate discrepancies: **{result['candidateDiscrepancies']}**.",
        f"- Deferred rows: **{result['deferredRows']}**.",
        "",
        "## Candidate discrepancies (requires source review)",
        "",
    ]
    for row in result["compared"]:
        for issue in row["differences"]:
            lines.append(
                f"- **{row['name']}** (p. {row['page']}), {issue['field']}: "
                f"PDF `{issue['pdf']}` vs Army `{issue['army']}`."
            )
    if not result["candidateDiscrepancies"]:
        lines.append("- None in the conservative comparison subset.")
    lines.extend([
        "", "## Important limitations", "",
        "- A compared row is not proof of complete Weapon facts or a rule definition.",
        "- The chart extractor accepts only names on the same text baseline as Burst.",
        "- It does not guess across wrapped names or silently select one of several modes.",
        "- Blank, `-` and `--` represent the same absent value for this comparison.",
        "- A Saving Roll multiplier is non-operative without a Saving Attribute;",
        "  an Army `savingNum=1` with `saving=-` matches the chart's `--`.",
        "- The remaining rows and the categories below require dedicated audit work:",
    ])
    lines.extend(f"  - {entry}" for entry in report["notCompared"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-pdf", type=Path, required=True)
    parser.add_argument("--army-db", type=Path, default=Path("data/generated/infinity.db"))
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    try:
        report = audit_chart(args.core_pdf, args.army_db)
    except (OSError, WeaponChartAuditError, sqlite3.Error) as exc:
        parser.error(str(exc))
    output = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(output, encoding="utf-8", newline="\n")
    else:
        print(output, end="")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(
            markdown_report(report), encoding="utf-8", newline="\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
