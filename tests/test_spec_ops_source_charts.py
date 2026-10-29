"""Pin the source-defined Spec-Ops/Team-Ops choice chart inventory.

These are immutable Army source options, not a player's selected upgrades.
The current application database preserves them with per-source-unit provenance
even though ordinary Unit detail APIs do not yet publish their contents.
"""

from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARMY = ROOT / "data/generated/infinity.db"
SOURCE = ROOT / "data/raw/JSON 20260929-114335.zip"
SPEC_OPS_IDS = {1908, *range(1912, 1926)}
TEAM_OPS_IDS = {1909, *range(1926, 1940)}


def test_spec_ops_charts_are_source_attributed_and_not_flattened() -> None:
    assert len(SPEC_OPS_IDS) == len(TEAM_OPS_IDS) == 15

    with sqlite3.connect(ARMY) as connection:
        rows = connection.execute(
            "SELECT u.id, u.spectables, s.spectables "
            "FROM units AS u "
            "JOIN logical_unit_spectables AS s ON s.source_unit_id = u.id "
            "WHERE u.id BETWEEN 1908 AND 1939 ORDER BY u.id"
        ).fetchall()

    assert {row[0] for row in rows} == SPEC_OPS_IDS | TEAM_OPS_IDS
    saw_compound_option = False
    for source_id, raw_source, raw_projection in rows:
        assert json.loads(raw_source) == json.loads(raw_projection)
        charts = json.loads(raw_projection)
        assert set(charts) == {"table", "specball"}
        assert len(charts["table"]["items"]) == (
            8 if source_id in SPEC_OPS_IDS else 10
        )
        assert len(charts["specball"]["items"]) == 4
        for chart in charts.values():
            for item in chart["items"]:
                attrs = item["attrs"]
                assert isinstance(attrs, list) and attrs
                assert all(attr["type"] in {"stat", "weapon", "equip", "skill"} for attr in attrs)
                saw_compound_option |= len(attrs) > 1
    assert saw_compound_option


@pytest.mark.skipif(not SOURCE.exists(), reason="Pinned Army ZIP unavailable")
def test_pinned_army_spec_ops_charts_match_materialized_source_payloads() -> None:
    """Cross-check the exact September 29 snapshot without altering source data."""
    by_source_id: dict[int, set[str]] = {}
    with zipfile.ZipFile(SOURCE) as archive:
        for name in archive.namelist():
            if name == "metadata.json" or not name.endswith(".json"):
                continue
            document = json.loads(archive.read(name))
            for unit in document["units"]:
                if "spectables" not in unit:
                    continue
                by_source_id.setdefault(unit["id"], set()).add(
                    json.dumps(unit["spectables"], sort_keys=True)
                )

    assert set(by_source_id) == SPEC_OPS_IDS | TEAM_OPS_IDS
    assert all(len(payloads) == 1 for payloads in by_source_id.values())
    with sqlite3.connect(ARMY) as connection:
        current = {
            source_id: json.dumps(json.loads(raw), sort_keys=True)
            for source_id, raw in connection.execute(
                "SELECT id, spectables FROM units "
                "WHERE spectables IS NOT NULL AND spectables != ''"
            )
        }
    assert current == {
        source_id: next(iter(payloads))
        for source_id, payloads in by_source_id.items()
    }
