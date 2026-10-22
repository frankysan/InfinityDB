"""Pinned N5.3 Martial Arts source-variant reconciliation for the future usage index.

This audits existing Army/rules projections; it does not infer levels from names
or implement cross-Army usage aggregation.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from infinity_db.database.repository import Database
from infinity_db.rules_database import RulesDatabase
from infinity_db.skill_catalog import SkillCatalog

pytestmark = pytest.mark.usefixtures("requires_pinned_raw_army_archive")

ROOT = Path(__file__).resolve().parents[1]
ARMY_DB = ROOT / "data/generated/infinity.db"
RAW_DB = ROOT / "data/generated/infinity.raw.db"
RULES_DB = ROOT / "data/generated/rules.db"

# Reviewed source IDs and printed chart values, N5.3 EN p. 100.
SOURCE_LEVELS = {19: 1, 20: 2, 21: 3, 22: 4, 23: 5}
CHART_MODS = {
    1: ("0", "-3", "0"),
    2: ("+3", "-3", "0"),
    3: ("+3", "-3", "+1SD"),
    4: ("+3", "-3", "+1B"),
    5: ("+3", "-3", "+1B, +1SD"),
}


def test_martial_arts_levels_reconcile_army_catalog_with_reviewed_rules() -> None:
    army = Database(ARMY_DB)
    rules = RulesDatabase(RULES_DB)
    source_ids = army.skill_source_ids("martial-arts")
    assert set(source_ids) == set(SOURCE_LEVELS)

    # The five source IDs must resolve to one application family while retaining
    # a distinct exact-source variant for each Level.
    with sqlite3.connect(ARMY_DB) as connection:
        rows = connection.execute(
            "SELECT source_item_id, source_name, application_item_id "
            "FROM application_catalog_sources "
            "WHERE catalog = 'skills' AND source_item_id BETWEEN 19 AND 23 "
            "ORDER BY source_item_id"
        ).fetchall()
    with sqlite3.connect(RAW_DB) as connection:
        source_names = dict(
            connection.execute(
                "SELECT id, name FROM metadata_skills WHERE id BETWEEN 19 AND 23"
            )
        )
    assert len(rows) == len(source_names) == 5, (rows, source_names)
    assert len({row[2] for row in rows}) == 1, rows
    for source_id, source_name, _application_id in rows:
        level = SOURCE_LEVELS[source_id]
        assert source_name == source_names[source_id] == f"Martial Arts L{level}"

    published = rules.catalog_source_variant_semantics("skill")
    for source_id, level in SOURCE_LEVELS.items():
        assert published.get(source_id) == {"kind": "level", "value": level}
        record = rules.composed_record(f"skill:martial-arts-l{level}")
        assert record is not None
        assert record["review"]["status"] == "reviewed"
        assert record["variant_semantics"]["inheritance"] == "source"
        assert record["variant_semantics"]["source_variant"] == {
            "kind": "level", "value": level,
        }
        assert any(
            citation["source_id"] == "n5-core-v5.3-pdf" and citation["page"] == 100
            for citation in record["citations"]
        )

    chart = army.list_martial_arts_levels()
    assert len(chart) == 5
    assert {
        int(row["level"]): (
            row["attack_mod"], row["opponent_mod"], row["burst_mod"]
        )
        for row in chart
    } == CHART_MODS
    assert all(row["ps_mod"] in (None, "", "-") for row in chart)


def test_martial_arts_used_source_ids_keep_exact_level_and_extras() -> None:
    army = Database(ARMY_DB)
    rules = RulesDatabase(RULES_DB)
    detail = SkillCatalog(army, rules).get_skill("martial-arts")
    assert detail is not None
    variants = detail["variants"]
    assert variants, "No actual Army occurrences for Martial Arts"

    used_ids = {int(variant["skill_id"]) for variant in variants}
    assert used_ids <= SOURCE_LEVELS.keys()
    assert all(
        variant.get("source_variant") == {
            "kind": "level", "value": SOURCE_LEVELS[int(variant["skill_id"])]
        }
        for variant in variants
    )

    # Audit every direct owner scope. No extra (distance or other parameter) may
    # be silently interpreted as a different Martial Arts Level.
    with sqlite3.connect(RAW_DB) as connection:
        for prefix in ("profile", "option", "unit_option"):
            rows = connection.execute(
                f"SELECT o.item_id, o.occurrence_id, e.extra_id, x.type, x.name "
                f"FROM {prefix}_skills AS o "
                f"LEFT JOIN {prefix}_skill_extras AS e "
                f"ON e.occurrence_id = o.occurrence_id "
                f"LEFT JOIN extras AS x ON x.id = e.extra_id "
                f"WHERE o.item_id BETWEEN 19 AND 23 "
                f"ORDER BY o.item_id, o.occurrence_id, e.position"
            ).fetchall()
            for source_id, occurrence_id, extra_id, extra_type, extra_name in rows:
                assert source_id in SOURCE_LEVELS
                assert extra_id is None, (
                    prefix, source_id, occurrence_id, extra_id, extra_type, extra_name,
                )
