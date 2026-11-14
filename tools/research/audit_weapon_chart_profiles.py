#!/usr/bin/env python3
"""Compare identifiable N5 v5.3 PDF Weapon Chart rows with shipped Army metadata.

Reassemble wrapped weapon names, and select explicit mode names only on an
unambiguous match. Unresolved printed identities and cells remain deferred.
Nothing in this tool modifies game data or treats a profile as a rule definition.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

if __package__:
    from .report_output import require_new_audit_outputs, write_audit_text_or_exit
    from .weapon_chart_source import (
        PDF_PAGES,
        WeaponChartAuditError,
        _chart_burst_anchors,
        rows_from_words,
    )
    from .weapon_source_common import (
        printed_name_and_mode as _printed_name_and_mode,
    )
    from .weapon_source_common import (
        source_file_sha256 as _sha256,
    )
    from .weapon_source_common import (
        weapon_identity as _identity,
    )
    from .weapon_source_common import (
        weapon_mode_identity as _mode_identity,
    )
    from .weapon_source_metadata import (
        _army_options,
        _metadata,
        _profile_attributes,
    )
    from .weapon_source_metadata import (
        _source_range_bands as _source_range_bands,
    )
else:  # Support direct execution from tools/research/.
    from report_output import require_new_audit_outputs, write_audit_text_or_exit
    from weapon_chart_source import (
        PDF_PAGES,
        WeaponChartAuditError,
        _chart_burst_anchors,
        rows_from_words,
    )
    from weapon_source_common import (
        printed_name_and_mode as _printed_name_and_mode,
    )
    from weapon_source_common import (
        source_file_sha256 as _sha256,
    )
    from weapon_source_common import (
        weapon_identity as _identity,
    )
    from weapon_source_common import (
        weapon_mode_identity as _mode_identity,
    )
    from weapon_source_metadata import (
        _army_options,
        _metadata,
        _profile_attributes,
    )
    from weapon_source_metadata import (
        _source_range_bands as _source_range_bands,
    )

FORMAT = "InfinityDB N5 Weapon Chart profile evidence"
FORMAT_VERSION = 3
_RANGE_EDGES_X = (87.736, 113.663, 139.303, 164.268, 190.195, 216.122, 241.066, 266.993)
_FIELDS = ("ps", "burst", "ammunition", "savingAttribute", "savingRolls")


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


def _printed_auxiliary_profiles(
    words: list[tuple[float, float, str]], page: int
) -> list[dict[str, str | int]]:
    """Record supplementary game-element profiles with no Burst/chart anchor."""
    baselines = sorted({round(y, 1) for x, y, word in words
                        if 95 <= x < 260 and re.fullmatch(r"ARM=\d+", word)})
    rows: list[dict[str, str | int]] = []
    for y in baselines:
        # The printed name can wrap above/below the profile baseline.
        # 6.1 pt captures both lines without crossing adjacent chart rows.
        # Deduplicate overlapping PDF text runs by position and word.
        names = {(round(x, 1), round(wy, 1), word) for x, wy, word in words
                 if 12 <= x < 90 and abs(wy - y) <= 6.1}
        profile_words = {(round(x, 1), word) for x, wy, word in words
                         if 95 <= x < 267 and abs(wy - y) < 1}
        name = " ".join(word for _, _, word in sorted(
            names, key=lambda entry: (entry[1], entry[0])
        ))
        fields = " ".join(word for _, word in sorted(profile_words))
        if all(f"{key}=" in fields for key in ("ARM", "BTS", "STR", "S")):
            rows.append({"page": page, "name": name, "profile": fields})
    return rows


def compare_auxiliary_profiles(
    rows: list[dict[str, str | int]], metadata: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    """Compare object attributes independently of ordinary Weapon attack rows.

    A printed Mine plural resolves to its Army singular identity. Named
    modes such as Disco Ball resolve under the parent Weapon. Ambiguous and
    unmatched rows remain reported instead of being silently discarded.
    """
    result: list[dict[str, Any]] = []
    for row in rows:
        name = str(row["name"])
        printed = _profile_attributes(str(row["profile"]))
        parent, mode = _printed_name_and_mode(name)
        options = [
            item for item in _army_options(parent, metadata)
            if _mode_identity(str(item.get("mode") or "")) == _mode_identity(mode)
        ]
        if not options and not mode:
            options = [
                item for group in metadata.values() for item in group
                if item.get("mode")
                and _mode_identity(str(item["mode"])) == _mode_identity(name)
            ]
        army: dict[str, int] = {}
        differences: list[dict[str, int | str]] = []
        if len(options) == 1 and len(printed) == 4:
            army = _profile_attributes(str(options[0].get("profile", "")))
            if len(army) == 4:
                differences = [
                    {"field": field, "pdf": printed[field], "army": army[field]}
                    for field in ("ARM", "BTS", "STR", "S")
                    if printed[field] != army[field]
                ]
                status = "candidate-discrepancy" if differences else "fields-match"
            else:
                status = "unresolved-auxiliary-profile"
        else:
            status = "unresolved-auxiliary-identity" if len(options) != 1 else (
                "unresolved-auxiliary-profile"
            )
        result.append({
            **row, "printedAttributes": printed, "armyAttributes": army,
            "status": status, "differences": differences,
            "armyName": options[0]["name"] if len(options) == 1 else None,
            "armyMode": options[0].get("mode") if len(options) == 1 else None,
        })
    return result



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
            anchors = [y for y, _ in _chart_burst_anchors(words)]
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
        "armyDatabaseSha256": _sha256(army_db),
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
        "# 1.0 N5 v5.3 Weapon Chart — partial row alignment and range evidence",
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
    auxiliary = report.get("auxiliaryProfiles", [])
    matched = sum(r["status"] in {"fields-match", "candidate-discrepancy"}
                  for r in auxiliary)
    mismatches = sum(r["status"] == "candidate-discrepancy"
                     for r in auxiliary)
    lines.extend([
        "", "## Supplementary object profiles", "",
        f"- Printed object profiles: **{len(auxiliary)}**; matched Army identities: "
        f"**{matched}**; attribute discrepancies: **{mismatches}**; "
        f"unresolved identities/profiles: **{len(auxiliary) - matched}**.", "",
    ])
    for row in auxiliary:
        identity = row.get("armyName") or "unresolved Army identity"
        if row.get("armyMode"):
            identity += f" ({row['armyMode']})"
        detail = "; ".join(
            f"{d['field']}: PDF {d['pdf']} vs Army {d['army']}"
            for d in row.get("differences", [])
        )
        lines.append(
            f"- p. {row['page']}: **{row['name']}** -> {identity}: "
            f"**{row['status']}**"
            + (f" ({detail})" if detail else "") + "."
        )
    lines.extend([
        "", "## Important limitations", "",
        "- A compared row is not proof of complete Weapon facts or a rule definition.",
        "- The chart extractor groups wrapped names around each printed Burst baseline.",
        "- Colored PDF vector bars provide exact slot boundaries; printed numbers,",
        "  not colors, determine range MODs. Bare signed/unsigned distinctions are retained.",
        "- Ancillary object profiles and the Discover Skill are not standalone weapons.",
        "- Only object profiles with four printed attributes are reconciled here;",
        "  other equipment/object rules require a separate clause-level review.",
        "- A PDF/Army mismatch is a source difference, not a correction to either profile.",
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
    parser.add_argument("--army-db", type=Path, default=Path("data/generated/army.db"))
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    require_new_audit_outputs(parser, args.json_output, args.markdown_output)
    try:
        report = audit_chart(args.core_pdf, args.army_db)
    except (OSError, WeaponChartAuditError, sqlite3.Error) as exc:
        parser.error(str(exc))
    output = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.json_output:
        write_audit_text_or_exit(parser, args.json_output, output)
    else:
        print(output, end="")
    if args.markdown_output:
        write_audit_text_or_exit(parser, args.markdown_output, markdown_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
