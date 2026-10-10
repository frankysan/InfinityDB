#!/usr/bin/env python3
"""Compare identifiable N5 v5.3 PDF Weapon Chart rows with shipped Army metadata.

Reassemble wrapped weapon names, and select explicit mode names only on an
unambiguous match. Unresolved printed identities and cells remain deferred.
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
FORMAT_VERSION = 3
_RANGE_EDGES_CM = (20, 40, 60, 80, 100, 120, 240)
_RANGE_EDGES_X = (87.736, 113.663, 139.303, 164.268, 190.195, 216.122, 241.066, 266.993)
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


def _cell(
    words: list[tuple[float, float, str]], y: float, left: float,
    right: float, *, wrapped: bool = False,
) -> str:
    """Read a chart cell, including the two baselines of combined saves."""
    tolerance = 5.2 if wrapped else 3.2
    relevant = [
        (x, wy, word) for x, wy, word in words
        if left <= x < right and abs(wy - y) < tolerance
    ]
    return " ".join(
        word for x, wy, word in sorted(relevant, key=lambda item: (round(item[1] / 3), item[0]))
    ).strip()


def rows_from_words(words: list[tuple[float, float, str]], page_number: int
                    ) -> list[dict[str, Any]]:
    """Reassemble rows of the *specific* N5 v5.3 Weapon Chart layout.

    Burst values anchor table rows. Name text may span up to four baselines;
    midpoints between Burst anchors stop adjacent names from merging. Limit
    the name window to the printed name column and 14.9 vertical points.
    Unreadable cells are left blank, never reconstructed by guessing.
    """
    anchors = [
        (y, word) for x, y, word in words
        if 294 <= x <= 310 and 175 < y < 800
        and re.fullmatch(r"(?:[1-9]|10|--)", word)
    ]
    anchors.sort()
    result: list[dict[str, Any]] = []
    for index, (y, _) in enumerate(anchors):
        low = max(y - 14.9, (anchors[index - 1][0] + y) / 2) if index else y - 14.9
        high = (
            min(y + 14.9, (anchors[index + 1][0] + y) / 2)
            if index + 1 < len(anchors) else y + 14.9
        )
        name_words = [
            (wy, x, word) for x, wy, word in words
            if 12 <= x < 90 and low < wy < high and word != "NAME"
        ]
        name = " ".join(
            word for _, _, word in sorted(
                name_words, key=lambda entry: (round(entry[0] / 4.8), entry[1])
            )
        )
        result.append({
            "page": page_number,
            "name": name,
            "ps": _cell(words, y, 263, 293),
            "burst": _cell(words, y, 293, 314),
            "ammunition": _cell(words, y, 315, 367),
            "savingAttribute": _cell(words, y, 367, 418, wrapped=True),
            "savingRolls": _cell(words, y, 418, 462),
        })
    return result



def _printed_range_bands(
    words: list[tuple[float, float, str]], y: float,
    fills: list[tuple[tuple[float, float, float, float], tuple[float, float, float]]],
) -> list[str | None] | None:
    """Derive printed range MODs from the N5 chart's vector bar boundaries.

    Colored rectangles locate groups; printed text supplies the MOD values.
    Neutral table backgrounds and black out-of-range cells are not bands.
    Return None if a colored group cannot be resolved without guessing.
    """
    colors: list[tuple[float, float, float] | None] = []
    for left, right in zip(_RANGE_EDGES_X[:-1], _RANGE_EDGES_X[1:], strict=True):
        x = (left + right) / 2
        hits = [
            color for (x0, y0, x1, y1), color in fills
            if x0 <= x <= x1 and y0 <= y + 4 <= y1
        ]
        color = hits[-1] if hits else None
        # All four active range colors are chromatic; the alternating table
        # backgrounds and black beyond maximum range are neutral.
        if color is not None and max(color) - min(color) <= 0.15:
            color = None
        colors.append(color)
    labels = [
        (x, word) for x, wy, word in words
        if _RANGE_EDGES_X[0] <= x < _RANGE_EDGES_X[-1]
        and abs(wy - y) < 3.2 and re.fullmatch(r"[+-]?\d+", word)
    ]
    result: list[str | None] = [None] * 7
    if not any(color is not None for color in colors):
        return result if not labels else None
    index = 0
    while index < len(colors):
        color = colors[index]
        end = index + 1
        while end < len(colors) and colors[end] == color:
            end += 1
        if color is not None:
            matches = [
                (x, word) for x, word in labels
                if _RANGE_EDGES_X[index] <= x < _RANGE_EDGES_X[end]
            ]
            if len(matches) == 1:
                result[index:end] = [matches[0][1]] * (end - index)
            elif len(matches) == end - index and all(
                _RANGE_EDGES_X[i] <= x < _RANGE_EDGES_X[i + 1]
                for i, (x, _) in zip(range(index, end), matches, strict=True)
            ):
                result[index:end] = [word for _, word in matches]
            else:
                return None
        index = end
    return result


def _source_range_bands(distance: str) -> list[str | None] | None:
    """Expand canonical Army breakpoints (2.5 cm per inch) into chart cells."""
    result: list[str | None] = [None] * 7
    if not distance:
        return result
    parsed = json.loads(distance)
    boundaries = sorted(
        (int(value["max"]), str(value["mod"]))
        for value in parsed.values() if isinstance(value, dict)
    )
    previous = 0
    for maximum, modifier in boundaries:
        if maximum not in _RANGE_EDGES_CM or maximum <= previous:
            return None
        for index, edge in enumerate(_RANGE_EDGES_CM):
            if previous < edge <= maximum:
                result[index] = modifier
        previous = maximum
    return result


def _printed_auxiliary_profiles(
    words: list[tuple[float, float, str]], page: int
) -> list[dict[str, str | int]]:
    """Record supplementary game-element profiles with no Burst/chart anchor."""
    baselines = sorted({round(y, 1) for x, y, word in words
                        if 95 <= x < 260 and re.fullmatch(r"ARM=\d+", word)})
    rows: list[dict[str, str | int]] = []
    for y in baselines:
        # Overlapping PDF text runs can duplicate exactly the same word.
        names = {(round(x, 1), word) for x, wy, word in words
                 if 12 <= x < 90 and abs(wy - y) < 1}
        profile_words = {(round(x, 1), word) for x, wy, word in words
                         if 95 <= x < 267 and abs(wy - y) < 1}
        name = " ".join(word for _, word in sorted(names))
        fields = " ".join(word for _, word in sorted(profile_words))
        if all(f"{key}=" in fields for key in ("ARM", "BTS", "STR", "S")):
            rows.append({"page": page, "name": name, "profile": fields})
    return rows


def _profile_attributes(value: str) -> dict[str, int]:
    return {key: int(number) for key, number in re.findall(
        r"\b(ARM|BTS|STR|S)\s*=\s*(\d+)\b", value
    )}


def compare_auxiliary_profiles(
    rows: list[dict[str, str | int]], metadata: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    """Check extra chart object profiles independently of the five-field rows."""
    result = []
    for row in rows:
        name = str(row["name"])
        # Only independently named *modes* are in this focused pass. Other
        # object/equipment profile rows require their own domain audit.
        options = [
            item for group in metadata.values() for item in group
            if item.get("mode") and _identity(item["mode"]) == _identity(name)
        ]
        if not options:
            continue
        printed = _profile_attributes(str(row["profile"]))
        if len(options) == 1 and len(printed) == 4:
            army = _profile_attributes(options[0].get("profile", ""))
            status = "fields-match" if printed == army else "candidate-discrepancy"
        else:
            army = {}
            status = "unresolved-auxiliary-profile"
        result.append({**row, "printedAttributes": printed,
                       "armyAttributes": army, "status": status})
    return result


def _printed_name_and_mode(name: str) -> tuple[str, str]:
    """Keep the printed identity separate from an explicit parenthesized mode."""
    match = re.fullmatch(r"(.+?)\s*\(([^()]*)\s+Mode\)", name, re.IGNORECASE)
    if match is None:
        return name, ""
    return match.group(1).strip(), match.group(2).strip() + " Mode"


def _mode_identity(mode: str) -> str:
    # N5's Anti-Materiel and Army's Anti-Material/Antimaterial spellings
    # designate the same named mode; do not collapse unrelated mode names.
    return _identity(mode).replace("antimaterial", "antimateriel")


def _army_options(
    name: str, metadata: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    key = _identity(name)
    options = metadata.get(key, []) if key else []
    # The chart labels tokenized Mines in the plural; Army models the type
    # as a singular weapon. Limit this alias to a trailing "Mines" word.
    if not options and key.endswith("mines"):
        options = metadata.get(key[:-1], [])
    return options


def _metadata(db: Path) -> tuple[dict[str, list[dict[str, Any]]], int]:
    with sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True) as conn:
        ammunition = dict(conn.execute("SELECT id, name FROM metadata_ammunitions"))
        rows = conn.execute(
            "SELECT name, mode, ammunition, burst, damage, saving, savingNum, "
            "distance, profile FROM metadata_weapons"
        ).fetchall()
    indexed: dict[str, list[dict[str, Any]]] = {}
    for name, mode, ammo_id, burst, damage, saving, rolls, distance, profile in rows:
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
            "rangeBands": _source_range_bands(str(distance or "")),
            "profile": str(profile or ""),
        }
        indexed.setdefault(_identity(name), []).append(item)
    return indexed, len(rows)


def compare_rows(chart_rows: list[dict[str, Any]], metadata: dict[str, list[dict[str, Any]]]
                 ) -> dict[str, Any]:
    """Compare only exact, uniquely resolved printed identity/mode pairs."""
    compared: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    for row in chart_rows:
        printed_name, printed_mode = _printed_name_and_mode(row["name"])
        options = _army_options(printed_name, metadata)
        reason = ""
        if not options:
            reason = "no-matching-army-identity"
        elif printed_mode:
            options = [
                option for option in options
                if _mode_identity(option["mode"]) == _mode_identity(printed_mode)
            ]
            if len(options) != 1:
                reason = "unresolved-army-mode"
        elif len(options) != 1:
            # A bare printed name identifies the default (mode-less) profile,
            # when exactly one exists alongside named special modes.
            default = [option for option in options if not option["mode"]]
            if len(default) == 1:
                options = default
            else:
                reason = "missing-mode-disambiguation"
        elif options[0]["mode"]:
            reason = "missing-printed-mode"
        # A blank extracted cell is not the chart's explicit `--` notation.
        # It can indicate wrapped columns, e.g. the combined Plasma save;
        # such rows require a separate structured extraction review.
        if not reason and any(not row[field].strip() for field in _FIELDS):
            reason = "incomplete-pdf-cells"
        if reason:
            deferred.append({
                "page": row["page"], "extractedName": row["name"],
                "reason": reason,
            })
            continue
        army = options[0]
        differences = [
            {"field": field, "pdf": row[field], "army": army[field]}
            for field in _FIELDS if not _fields_equal(row, army, field)
        ]
        compared.append({
            "page": row["page"], "name": army["name"],
            "mode": army["mode"], "printedName": row["name"],
            "pdf": {field: row[field] for field in _FIELDS},
            "army": {field: army[field] for field in _FIELDS},
            "differences": differences,
            "status": "candidate-discrepancy" if differences else "fields-match",
            **({"rangeComparison": {
                "pdf": row["rangeBands"],
                "army": army.get("rangeBands"),
                "status": (
                    "deferred" if row["rangeBands"] is None
                    or army.get("rangeBands") is None else
                    "bands-match" if row["rangeBands"] == army["rangeBands"] else
                    "candidate-discrepancy"
                ),
            }} if "rangeBands" in row and "rangeBands" in army else {}),
        })
    return {
        "chartRowsLocated": len(chart_rows),
        "unambiguousRowsCompared": len(compared),
        "matchingRows": sum(r["status"] == "fields-match" for r in compared),
        "candidateDiscrepancies": sum(r["status"] == "candidate-discrepancy" for r in compared),
        "deferredRows": len(deferred),
        "rangeRowsCompared": sum(
            "rangeComparison" in r and r["rangeComparison"]["status"] != "deferred"
            for r in compared
        ),
        "rangeMatches": sum(
            "rangeComparison" in r and r["rangeComparison"]["status"] == "bands-match"
            for r in compared
        ),
        "rangeCandidates": sum(
            "rangeComparison" in r
            and r["rangeComparison"]["status"] == "candidate-discrepancy"
            for r in compared
        ),
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
        supplementary_rows: list[dict[str, str | int]] = []
        for page in PDF_PAGES:
            words = [
                (float(w[0]), float(w[1]), str(w[4]))
                for w in doc[page - 1].get_text("words")
            ]
            page_rows = rows_from_words(words, page)
            anchors = sorted(
                y for x, y, word in words
                if 294 <= x <= 310 and 175 < y < 800
                and re.fullmatch(r"(?:[1-9]|10|--)", word)
            )
            if len(anchors) != len(page_rows):
                raise WeaponChartAuditError("Weapon Chart row anchors are inconsistent")
            fills = [
                ((float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)),
                 (float(drawing["fill"][0]), float(drawing["fill"][1]),
                  float(drawing["fill"][2])))
                for drawing in doc[page - 1].get_drawings()
                if drawing["fill"] is not None
                for item in drawing["items"]
                if item[0] == "re"
                for rect in [item[1]]
                if rect.x1 > _RANGE_EDGES_X[0]
                and rect.x0 < _RANGE_EDGES_X[-1]
            ]
            for row, y in zip(page_rows, anchors, strict=True):
                row["rangeBands"] = _printed_range_bands(words, y, fills)
            chart_rows.extend(page_rows)
            supplementary_rows.extend(_printed_auxiliary_profiles(words, page))
    # A different PDF export may move columns without changing its page count.
    # Fail closed rather than reporting misleading matches from another layout.
    anchors = {_identity(row["name"]) for row in chart_rows}
    if len(chart_rows) < 100 or not {
        "tacticalbow", "combirifle", "minedispenser"
    }.issubset(anchors):
        raise WeaponChartAuditError("Unrecognized N5 v5.3 Weapon Chart layout")
    metadata, count = _metadata(army_db)
    result = compare_rows(chart_rows, metadata)
    extra = compare_auxiliary_profiles(supplementary_rows, metadata)
    return {
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
        "status": "partial-pdf-profile-evidence-not-completeness",
        "corePdfSha256": _sha256(pdf),
        "armyMetadataProfiles": count,
        "comparison": result,
        "auxiliaryProfiles": extra,
        "notCompared": [
            "Traits and special-weapon prose on pages 68-74",
            "manual review of candidate Saving Roll and range notation discrepancies",
            "profile-to-API/browser projection and standalone rule-definition coverage",
        ],
    }


def markdown_report(report: dict[str, Any]) -> str:
    result = report["comparison"]
    lines = [
        "# 1.0 N5 v5.3 Weapon Chart — complete row alignment and range evidence",
        "",
        "**Partial evidence, not a completeness verdict.** Uses the official PDF pp. 176–188.",
        "No upstream source, Army metadata, or curated gameplay facts are modified.",
        "",
        f"- Core PDF SHA-256: `{report['corePdfSha256']}`",
        f"- Published Army metadata profile rows: **{report['armyMetadataProfiles']}**.",
        f"- PDF chart rows located: **{result['chartRowsLocated']}**.",
        ("- Unique printed identity/mode rows compared: "
         f"**{result['unambiguousRowsCompared']}**."),
        f"- Rows with all five compared fields matching: **{result['matchingRows']}**.",
        f"- Candidate discrepancies: **{result['candidateDiscrepancies']}**.",
        f"- Deferred rows: **{result['deferredRows']}**.",
        (f"- Range comparisons: **{result['rangeRowsCompared']}**, "
         f"matches **{result['rangeMatches']}**, "
         f"candidates **{result['rangeCandidates']}**."),
        (f"- Supplementary object profiles: **{len(report.get('auxiliaryProfiles', []))}** "
         "(not included in the anchored chart-row count)."),
        "",
        "## Candidate discrepancies (requires source review)",
        "",
    ]
    for row in result["compared"]:
        for issue in row["differences"]:
            lines.append(
                f"- **{row['name']}** ({row['mode'] or 'standard'}, "
                f"p. {row['page']}), {issue['field']}: "
                f"PDF `{issue['pdf']}` vs Army `{issue['army']}`."
            )
    if not result["candidateDiscrepancies"]:
        lines.append("- None in the conservative comparison subset.")
    lines.extend(["", "## Range-band candidates (requires source review)", ""])
    for row in result["compared"]:
        range_check = row.get("rangeComparison")
        if range_check and range_check["status"] == "candidate-discrepancy":
            lines.append(
                f"- **{row['name']}** ({row['mode'] or 'standard'}, "
                f"p. {row['page']}): printed {range_check['pdf']} vs "
                f"Army {range_check['army']}."
            )
    if not result["rangeCandidates"]:
        lines.append("- None in the range subset.")
    lines.extend(["", "## Supplementary object profiles", ""])
    for row in report.get("auxiliaryProfiles", []):
        lines.append(
            f"- p. {row['page']}: **{row['name']}**: {row['status']} "
            f"(printed {row['printedAttributes']}, Army {row['armyAttributes']})."
        )
    lines.extend([
        "", "## Important limitations", "",
        "- A compared row is not proof of complete Weapon facts or a rule definition.",
        "- The chart extractor groups wrapped names around each printed Burst baseline.",
        "- Colored PDF vector bars provide exact slot boundaries; printed numbers,",
        "  not colors, determine range MODs. Bare signed/unsigned distinctions are retained.",
        "- Ancillary object profiles and the Discover Skill are not standalone weapons.",
        "- Modes are selected by an explicit printed name or a unique mode-less",
        "  default; unresolved identities remain deferred.",
        "- Combined Plasma saving cells are read from both printed baselines.",
        "- Blank, `-` and `--` represent the same absent value for this comparison.",
        "- A Saving Roll multiplier is non-operative without a Saving Attribute;",
        "  an Army `savingNum=1` with `saving=-` matches the chart's `--`.",
        "- The remaining rows and the categories below require dedicated audit work:",
    ])
    lines.extend(f"  - {entry}" for entry in report["notCompared"])
    lines.extend(["", "## Deferred source rows", ""])
    for row in result["deferred"]:
        lines.append(
            f"- p. {row['page']}: `{row['extractedName']}` — {row['reason']}."
        )
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
