"""Source-pinned, read-only Wiki Weapon Chart identity reconciliation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.audit_weapon_chart_profiles import WeaponChartAuditError
from tools.audit_wiki_weapon_chart_names import (
    audit,
    markdown_report,
    reconcile,
    weapon_rows,
)


def _html_table(header: list[str], *rows: list[str]) -> str:
    def cells(tag: str, fields: list[str]) -> str:
        return "<tr>" + "".join(f"<{tag}>{v}</{tag}>" for v in fields) + "</tr>"

    return "<table>" + cells("th", header) + "".join(cells("td", r) for r in rows) + "</table>"


def test_weapon_rows_exclude_supplementary_objects_and_keep_alt_entries() -> None:
    weapon_head = ["Name"] + [f"field{i}" for i in range(13)]
    data = (
        _html_table(weapon_head, ["AP Mines"] + [""] * 13)
        + _html_table(["Deployable", "ARM", "BTS", "STR", "S"], ["AP MINE", "0", "0", "1", "0"])
        + _html_table(weapon_head, ["AP Mines"] + ["new"] * 13)
    )
    rows = weapon_rows(data)
    assert len(rows) == 2
    assert {r["name"] for r in rows} == {"AP Mines"}
    assert [r["tableIndex"] for r in rows] == [0, 2]
    assert rows[0]["fields"]["field0"] == ""
    assert rows[1]["fields"]["field0"] == "new"


def test_weapon_rows_reject_malformed_or_missing_weapon_tables() -> None:
    with pytest.raises(WeaponChartAuditError, match="Invalid Wiki"):
        weapon_rows(
            _html_table(
                ["Name"] + [f"field{i}" for i in range(13)],
                ["AP Mines", "7"],
            )
        )
    with pytest.raises(WeaponChartAuditError, match="No recognizable"):
        weapon_rows(
            _html_table(
                ["Deployable", "ARM", "BTS", "STR", "S"],
                ["AP MINE", "0", "0", "1", "0"],
            )
        )


def test_reconcile_aliases_and_different_alternative_table_values() -> None:
    rows = [
        {"name": "AP Mines", "tableIndex": 0, "fields": {"ammo": "AP"}},
        {"name": "Feuerbach (Blast Mode)", "tableIndex": 1, "fields": {"ammo": "EXP"}},
        {"name": "Suppressive Fire Mode", "tableIndex": 1, "fields": {"ammo": "*"}},
        {"name": "Trench-Hammer (BS Mode)", "tableIndex": 2, "fields": {"trait": "Disposable (3)"}},
        {"name": "Trench-Hammer (BS Mode)", "tableIndex": 3, "fields": {"trait": "[*]"}},
        {"name": "MISSING UNREVIEWED WEAPON", "tableIndex": 4, "fields": {"ammo": "N"}},
    ]
    metadata = {
        "apmine": [{"name": "AP Mine", "mode": ""}],
        "feuerbach": [
            {"name": "Feuerbach", "mode": "Burst Mode"},
            {"name": "Feuerbach", "mode": "Explosive Mode"},
        ],
        "trenchhammer": [{"name": "Trench-Hammer", "mode": "BS Mode"}],
    }
    report = reconcile(rows, metadata)
    statuses = {r["printedName"]: r["status"] for r in report["identities"]}
    assert statuses == {
        "AP Mines": "explicit-name-alias",
        "Feuerbach (Blast Mode)": "explicit-mode-alias",
        "Suppressive Fire Mode": "editorial-chart-row-not-a-weapon",
        "Trench-Hammer (BS Mode)": "exact",
        "MISSING UNREVIEWED WEAPON": "unresolved",
    }
    assert report["duplicateOccurrences"] == 1
    assert report["duplicates"] == [
        {
            "printedName": "Trench-Hammer (BS Mode)",
            "occurrences": 2,
            "tableIndices": [2, 3],
            "distinctValues": 2,
            "status": "conflicting-alternative-values",
        }
    ]


def test_pinned_english_wiki_identity_inventory_if_sources_available() -> None:
    root = Path(__file__).resolve().parents[1]
    wiki = root / "data/wiki/WIKI-en 20260926-200832.zip"
    army = root / "data/generated/infinity.db"
    curated = root / "data/curated/rules/n5-core-v5.3.json"
    if not all(path.exists() for path in (wiki, army, curated)):
        pytest.skip("Pinned private snapshots not available")
    report = audit(wiki, army, curated)
    assert report["rows"] == 208
    assert report["uniqueNamesAndModes"] == 174
    assert report["statuses"] == {
        "exact": 162,
        "explicit-name-alias": 10,
        "explicit-mode-alias": 1,
        "editorial-chart-row-not-a-weapon": 1,
        "unresolved": 0,
    }
    assert report["duplicateOccurrences"] == 34
    assert {
        row["printedName"]
        for row in report["duplicates"]
        if row["status"] == "conflicting-alternative-values"
    } == {
        "Trench-Hammer (BS Mode)",
        "Trench-Hammer (CC Mode)",
        "Kobra Pistol (BS Mode)",
        "Kobra Pistol (CC Mode)",
    }
    exceptions = {
        row["printedName"]: row for row in report["identities"] if row["status"] != "exact"
    }
    assert exceptions["Feuerbach (Blast Mode)"]["armyMode"] == "Explosive Mode"
    assert exceptions["Chest Mines (BS Mode)"]["armyName"] == "Chest Mine"
    assert exceptions["Chest Mines (CC Mode)"]["armyMode"] == "CC Mode"
    assert exceptions["Suppressive Fire Mode"]["armyName"] is None
    assert report["chartAbsentCuratedReference"] == {
        "name": "SymbioBomb",
        "curatedRule": "weapon:symbiobomb",
        "hasCuratedRule": True,
        "hasArmyProfile": False,
        "hasWikiWeaponChartProfile": False,
        "classification": "standalone-source-prose-without-chart-profile",
    }
    assert all(
        report["sources"][key] for key in ("wikiArchiveSha256", "chartSha256", "armyDbSha256")
    )
    assert "unresolved: **0**" in markdown_report(report)
