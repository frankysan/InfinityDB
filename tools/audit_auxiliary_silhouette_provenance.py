"""Pin the seven N5.3 auxiliary Silhouette disagreements across source contexts.

Read-only: compares printed supplementary object profiles, archived Wiki tables,
dedicated equipment pages and Army metadata. It does not adjudicate gameplay.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from tools.audit_weapon_chart_profiles import (
    WeaponChartAuditError,
    _army_options,
    _metadata,
    _profile_attributes,
)

# Printed labels differ across languages; never auto-translate other objects.
TARGETS = (
    ("AP Mine", "AP MINES", 181, "MINA AP", 190),
    ("E/M Mine", "E/M MINES", 181, "MINA E/M", 190),
    ("Monofilament Mine", "MONOFILAMENT MINES", 181, "MINA MONOFILO", 190),
    ("PARA Mine", "PARA MINES", 181, "MINA PARA", 190),
    ("Shock Mine", "SHOCK MINES", 181, "MINA SHOCK", 190),
    ("Viral Mine", "VIRAL MINES", 181, "MINA VIRAL", 191),
    ("Dazer", "DAZER", 186, "DAZER", 195),
)
EN_CHART = "Weapon_Chart"
ES_CHART = "es/Tabla_de_Armas"
EN_DAZER = "Dazer"
ES_DAZER = "es/Dazer"


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _identity(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def pdf_object_s(page: Any, label: str, *, spanish: bool) -> int:
    """Read the S attribute only from a uniquely named printed object row."""
    words = [(float(w[0]), float(w[1]), str(w[4])) for w in page.get_text("words")]
    anchor = "BLI=0" if spanish else "ARM=0"
    candidates = []
    for x, y, word in words:
        if not (105 < x < 175 and word == anchor):
            continue
        labels = [
            (wy, xx, token) for xx, wy, token in words if 10 <= xx < 115 and abs(wy - y) <= 6.1
        ]
        name = " ".join(
            t for _, _, t in sorted(labels, key=lambda item: (round(item[0], 1), item[1]))
        )
        if _identity(name) != _identity(label):
            continue
        values = [
            int(match.group(1))
            for xx, wy, token in words
            if 205 < xx < 270 and abs(wy - y) < 1.5
            if (match := re.fullmatch(r"S=(\d+)", token))
        ]
        if len(values) != 1:
            raise WeaponChartAuditError(f"Ambiguous S value for printed {label!r}: {values}")
        candidates.append(values[0])
    if len(candidates) != 1:
        raise WeaponChartAuditError(
            f"Expected one printed {label!r} object, found {len(candidates)}"
        )
    return candidates[0]


def html_rows(source: str) -> list[list[str]]:
    rows = []
    for raw in re.findall(r"<tr\b[^>]*>.*?</tr>", source, re.I | re.S):
        cells = re.findall(r"<(?:td|th)\b[^>]*>(.*?)</(?:td|th)>", raw, re.I | re.S)
        rows.append(
            [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", c))).strip() for c in cells]
        )
    return rows


def wiki_chart_s(source: str, label: str) -> int:
    values = [
        int(cells[4])
        for cells in html_rows(source)
        if len(cells) == 5
        and _identity(cells[0]) == _identity(label)
        and cells[1:4] == ["0", "0", "1"]
        and cells[4] in {"0", "1"}
    ]
    if len(values) != 1:
        raise WeaponChartAuditError(f"Expected one Wiki chart object for {label}: {values}")
    return values[0]


def wiki_dazer_s(source: str) -> int:
    """Read the dedicated profile, allowing its unlabeled EN attribute row."""
    tables = re.findall(r"<table\b[^>]*>.*?</table>", source, re.I | re.S)
    values = []
    for table in tables:
        rows = html_rows(table)
        if not rows:
            continue
        headings = [_identity(x) for x in rows[0]]
        if headings not in (
            ["arm", "bts", "str", "s"],
            ["posicionable", "bli", "pb", "est", "s"],
        ):
            continue
        for cells in rows[1:]:
            attrs = cells if len(cells) == 4 else cells[1:]
            if len(attrs) == 4 and attrs[:3] == ["0", "0", "1"]:
                if len(cells) == 5 and _identity(cells[0]) != "dazer":
                    continue
                if attrs[3] in {"0", "1"}:
                    values.append(int(attrs[3]))
    if len(values) != 1:
        raise WeaponChartAuditError(f"Expected one dedicated Dazer profile; found {values}")
    return values[0]


def read_member(archive: ZipFile, name: str) -> tuple[str, str]:
    content = archive.read(name)
    return content.decode("utf-8"), _sha256(content)


def audit(pdf_en: Path, pdf_es: Path, wiki_en: Path, wiki_es: Path, army_db: Path) -> dict:
    try:
        import pymupdf
    except ImportError as exc:
        raise WeaponChartAuditError("pymupdf is required") from exc

    metadata, _ = _metadata(army_db)
    with (
        pymupdf.open(pdf_en) as en,
        pymupdf.open(pdf_es) as es,
        ZipFile(wiki_en) as ze,
        ZipFile(wiki_es) as zs,
    ):
        english_chart, en_chart_hash = read_member(ze, EN_CHART)
        spanish_chart, es_chart_hash = read_member(zs, ES_CHART)
        en_dazer, en_dazer_hash = read_member(ze, EN_DAZER)
        es_dazer, es_dazer_hash = read_member(zs, ES_DAZER)
        rows = []
        for army_name, en_name, en_page, es_name, es_page in TARGETS:
            options = [o for o in _army_options(army_name, metadata) if not o.get("mode")]
            if len(options) != 1:
                raise WeaponChartAuditError(f"Unresolved Army object {army_name}: {len(options)}")
            attributes = _profile_attributes(options[0]["profile"])
            if set(attributes) != {"ARM", "BTS", "STR", "S"}:
                raise WeaponChartAuditError(f"Incomplete Army attributes for {army_name}")
            en_s = pdf_object_s(en[en_page - 1], en_name, spanish=False)
            es_s = pdf_object_s(es[es_page - 1], es_name, spanish=True)
            chart_en = wiki_chart_s(english_chart, en_name.replace(" MINES", " MINE"))
            chart_es = wiki_chart_s(spanish_chart, es_name)
            dedicated = (
                {"en": wiki_dazer_s(en_dazer), "es": wiki_dazer_s(es_dazer)}
                if army_name == "Dazer"
                else None
            )
            status = (
                "pdf-and-wiki-chart-agree; army-differs"
                if en_s == es_s == chart_en == chart_es != attributes["S"]
                else "cross-publication-conflict"
            )
            rows.append(
                {
                    "armyName": army_name,
                    "army": attributes["S"],
                    "pdfEn": {"page": en_page, "S": en_s},
                    "pdfEs": {"page": es_page, "S": es_s},
                    "wikiChartEn": chart_en,
                    "wikiChartEs": chart_es,
                    "wikiDedicated": dedicated,
                    "status": status,
                }
            )
    return {
        "format": "InfinityDB N5 auxiliary Silhouette provenance",
        "formatVersion": 1,
        "inputs": {
            "pdfEn": {"sha256": _sha256(pdf_en.read_bytes())},
            "pdfEs": {"sha256": _sha256(pdf_es.read_bytes())},
            "wikiEn": {
                "archiveSha256": _sha256(wiki_en.read_bytes()),
                "chartMember": EN_CHART,
                "chartSha256": en_chart_hash,
                "dazerMember": EN_DAZER,
                "dazerSha256": en_dazer_hash,
            },
            "wikiEs": {
                "archiveSha256": _sha256(wiki_es.read_bytes()),
                "chartMember": ES_CHART,
                "chartSha256": es_chart_hash,
                "dazerMember": ES_DAZER,
                "dazerSha256": es_dazer_hash,
            },
            "armyDb": {"sha256": _sha256(army_db.read_bytes())},
        },
        "profiles": rows,
        "notes": [
            "Values are quoted attributes; no publication precedence is inferred.",
            "Wiki chart and dedicated Dazer page are separate publication contexts.",
            "Army values are imported Weapon metadata, not corrected here.",
        ],
    }


def markdown_report(report: dict) -> str:
    rows = report["profiles"]
    lines = [
        "# N5.3 supplementary object Silhouette provenance",
        "",
        "Read-only audit; all source values remain unchanged. Values are "
        "Silhouette identifiers (S), not dimensions.",
        "",
        "| Object | English PDF | Spanish PDF | EN Wiki chart | ES Wiki chart "
        "| EN/ES dedicated | Army |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        dedicated = row["wikiDedicated"]
        extras = f"S{dedicated['en']}/S{dedicated['es']}" if dedicated else "—"
        lines.append(
            f"| {row['armyName']} | S{row['pdfEn']['S']} "
            f"(p. {row['pdfEn']['page']}) | S{row['pdfEs']['S']} "
            f"(p. {row['pdfEs']['page']}) | S{row['wikiChartEn']} "
            f"| S{row['wikiChartEs']} | {extras} | S{row['army']} |"
        )
    lines.extend(
        [
            "",
            "- The six named Mines agree across both printed PDFs and both Wiki "
            "Weapon Charts (S0), while Army metadata gives S1.",
            "- Dazer's main Wiki Weapon Charts and English PDF specify S1. "
            "The Spanish PDF, English dedicated Wiki page and Army specify S0; "
            "the Spanish dedicated Wiki page specifies S1.",
            "- No corrected active value or precedence is inferred.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf-en", type=Path, required=True)
    parser.add_argument("--pdf-es", type=Path, required=True)
    parser.add_argument("--wiki-en", type=Path, required=True)
    parser.add_argument("--wiki-es", type=Path, required=True)
    parser.add_argument("--army-db", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit(args.pdf_en, args.pdf_es, args.wiki_en, args.wiki_es, args.army_db)
    except (OSError, KeyError, WeaponChartAuditError) as exc:
        parser.error(str(exc))
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    args.markdown_output.write_text(markdown_report(report), encoding="utf-8", newline="\n")
    print(markdown_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
