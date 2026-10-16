"""Read-only audit of N5 Wiki Weapon Chart names and Army profile identities.

The Wiki chart repeats alternative tables. Profile values are not collapsed
when identical names have different source rows; those differences are flagged.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from tools.audit_weapon_chart_profiles import (
    WeaponChartAuditError,
    _identity,
    _metadata,
    _mode_identity,
    _printed_name_and_mode,
)

CHART_MEMBER = "Weapon_Chart"
# Explicit source spellings, not a blanket singularization rule.
NAME_ALIASES = {
    _identity(name): canonical
    for name, canonical in (
        ("AP Mines", "AP Mine"),
        ("Chest Mines", "Chest Mine"),
        ("Cybermines", "Cybermine"),
        ("E/M Mines", "E/M Mine"),
        ("Monofilament Mines", "Monofilament Mine"),
        ("PARA Mines", "PARA Mine"),
        ("Shock Mines", "Shock Mine"),
        ("Viral Mines", "Viral Mine"),
        ("CrazyKoalas", "Crazykoala"),
    )
}
MODE_ALIASES = {
    (_identity("Feuerbach"), _mode_identity("Blast Mode")): "Explosive Mode",
}
EDITORIAL_ROWS = {"Suppressive Fire Mode"}


def _cells(row: str) -> list[str]:
    cells = re.findall(r"<(?:td|th)\b[^>]*>(.*?)</(?:td|th)>", row, re.I | re.S)
    return [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", c))).strip() for c in cells]


def weapon_rows(html_source: str) -> list[dict[str, Any]]:
    """Read Weapon-profile tables only, keeping repeated alternative rows."""
    result = []
    tables = re.findall(r"<table\b.*?</table>", html_source, re.I | re.S)
    for table_index, table in enumerate(tables):
        source_rows = re.findall(r"<tr\b.*?</tr>", table, re.I | re.S)
        if not source_rows:
            continue
        header = _cells(source_rows[0])
        if len(header) < 10 or header[0].lower() != "name":
            continue  # the supplementary four-Attribute Deployable tables
        for row in source_rows[1:]:
            values = _cells(row)
            if len(values) != len(header) or not values[0]:
                raise WeaponChartAuditError(f"Invalid Wiki Weapon Chart row in table {table_index}")
            result.append(
                {
                    "name": values[0],
                    "tableIndex": table_index,
                    "fields": dict(zip(header[1:], values[1:], strict=True)),
                }
            )
    if not result:
        raise WeaponChartAuditError("No recognizable Weapon profile tables")
    return result


def reconcile(
    rows: list[dict[str, Any]], metadata: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    indexed: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        indexed[_identity(row["name"])].append(row)

    identities = []
    for entries in indexed.values():
        first = entries[0]
        printed_name = first["name"]
        if printed_name in EDITORIAL_ROWS:
            identities.append(
                {
                    "printedName": printed_name,
                    "status": "editorial-chart-row-not-a-weapon",
                    "armyName": None,
                    "armyMode": None,
                    "tableIndices": sorted({r["tableIndex"] for r in entries}),
                }
            )
            continue

        parent, mode = _printed_name_and_mode(printed_name)
        canonical_name = NAME_ALIASES.get(_identity(parent), parent)
        canonical_mode = MODE_ALIASES.get((_identity(canonical_name), _mode_identity(mode)), mode)
        options = [
            item
            for item in metadata.get(_identity(canonical_name), [])
            if _mode_identity(str(item.get("mode") or "")) == _mode_identity(canonical_mode)
        ]
        status = (
            (
                "explicit-mode-alias"
                if canonical_mode != mode
                else "explicit-name-alias"
                if canonical_name != parent
                else "exact"
            )
            if len(options) == 1
            else "unresolved"
        )
        identities.append(
            {
                "printedName": printed_name,
                "status": status,
                "armyName": options[0]["name"] if len(options) == 1 else None,
                "armyMode": options[0]["mode"] if len(options) == 1 else None,
                "candidateCount": len(options),
                "tableIndices": sorted({r["tableIndex"] for r in entries}),
            }
        )

    duplicates = []
    for entries in indexed.values():
        if len(entries) <= 1:
            continue
        variants = {
            json.dumps(row["fields"], sort_keys=True, ensure_ascii=False) for row in entries
        }
        duplicates.append(
            {
                "printedName": entries[0]["name"],
                "occurrences": len(entries),
                "tableIndices": sorted({r["tableIndex"] for r in entries}),
                "distinctValues": len(variants),
                "status": "conflicting-alternative-values"
                if len(variants) > 1
                else "identical-repeat",
            }
        )
    statuses = {
        name: sum(r["status"] == name for r in identities)
        for name in (
            "exact",
            "explicit-name-alias",
            "explicit-mode-alias",
            "editorial-chart-row-not-a-weapon",
            "unresolved",
        )
    }
    return {
        "rows": len(rows),
        "uniqueNamesAndModes": len(identities),
        "statuses": statuses,
        "identities": identities,
        "duplicateOccurrences": len(rows) - len(identities),
        "duplicates": duplicates,
    }


def audit(archive_path: Path, army_db: Path, curated_rules: Path) -> dict[str, Any]:
    with ZipFile(archive_path) as archive:
        data = archive.read(CHART_MEMBER)
    chart_rows = weapon_rows(data.decode("utf-8"))
    metadata, profile_count = _metadata(army_db)
    result = reconcile(chart_rows, metadata)
    if result["statuses"]["unresolved"]:
        names = [
            row["printedName"] for row in result["identities"] if row["status"] == "unresolved"
        ]
        raise WeaponChartAuditError(f"Unresolved Wiki identities: {names}")
    # The profile-less SymbioBomb is not a missing Army chart identity.
    curated = json.loads(curated_rules.read_text(encoding="utf-8"))
    ids = {row["id"] for row in curated["records"]}
    result["chartAbsentCuratedReference"] = {
        "name": "SymbioBomb",
        "curatedRule": "weapon:symbiobomb",
        "hasCuratedRule": "weapon:symbiobomb" in ids,
        "hasArmyProfile": bool(metadata.get(_identity("SymbioBomb"))),
        "hasWikiWeaponChartProfile": any(
            _identity(row["name"]) == _identity("SymbioBomb") for row in chart_rows
        ),
        "classification": "standalone-source-prose-without-chart-profile",
    }
    return {
        "format": "InfinityDB Wiki Weapon Chart identity reconciliation",
        "formatVersion": 1,
        "sources": {
            "wikiArchiveSha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
            "chartMember": CHART_MEMBER,
            "chartSha256": hashlib.sha256(data).hexdigest(),
            "armyDbSha256": hashlib.sha256(army_db.read_bytes()).hexdigest(),
            "curatedRulesSha256": hashlib.sha256(curated_rules.read_bytes()).hexdigest(),
            "armyProfileCount": profile_count,
        },
        **result,
        "limitations": [
            "The row identity/mode audit is not a complete chart value or rules audit.",
            "Repeated names with differing fields remain separate source conflicts.",
            "Editorial Suppressive Fire Mode is not a standalone Weapon profile.",
            "Only explicitly reviewed aliases are recognized; no fuzzy matching.",
        ],
    }


def markdown_report(report: dict[str, Any]) -> str:
    statuses = report["statuses"]
    conflicts = sum(
        row["status"] == "conflicting-alternative-values" for row in report["duplicates"]
    )
    lines = [
        "# Wiki Weapon Chart identity reconciliation",
        "",
        "Read-only review against pinned English Wiki and Army snapshots.",
        "",
        f"- Weapon rows: **{report['rows']}**; unique names/modes: "
        f"**{report['uniqueNamesAndModes']}**.",
        f"- Exact matches: **{statuses['exact']}**; explicit name aliases: "
        f"**{statuses['explicit-name-alias']}**; explicit mode aliases: "
        f"**{statuses['explicit-mode-alias']}**.",
        f"- Editorial-only rows: **{statuses['editorial-chart-row-not-a-weapon']}**; "
        f"unresolved: **{statuses['unresolved']}**.",
        f"- Repeated row occurrences: **{report['duplicateOccurrences']}**; "
        "alternative value conflicts: "
        f"**{conflicts}**.",
        "",
        "## Exceptions",
        "",
    ]
    for row in report["identities"]:
        if row["status"] != "exact":
            target = row["armyName"] or "no standalone Army Weapon"
            if row["armyMode"]:
                target += f" ({row['armyMode']})"
            lines.append(f"- {row['printedName']} -> {target}: {row['status']}.")
    lines.extend(["", "## Different values in repeated table rows", ""])
    for row in report["duplicates"]:
        if row["status"] == "conflicting-alternative-values":
            lines.append(
                f"- {row['printedName']}: {row['occurrences']} rows in tables "
                f"{row['tableIndices']}, {row['distinctValues']} variants."
            )
    lines.extend(
        [
            "",
            "## Chart-absent standalone rule",
            "",
            "- SymbioBomb has curated source-prose rules but no Weapon Chart "
            "or Army attack-profile identity. Its profile is not fabricated.",
            "",
            "No upstream profile, Weapon rule, or chart publication was modified.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki-en", type=Path, required=True)
    parser.add_argument("--army-db", type=Path, required=True)
    parser.add_argument("--curated-rules", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit(args.wiki_en, args.army_db, args.curated_rules)
    except (OSError, KeyError, json.JSONDecodeError, WeaponChartAuditError) as exc:
        parser.error(str(exc))
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    args.markdown_output.write_text(markdown_report(report), encoding="utf-8", newline="\n")
    print(markdown_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
