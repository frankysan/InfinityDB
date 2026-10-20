"""Verify exact N5.3 source variants before cross-Army usage aggregation.

Checks published catalog identity, reviewed rule provenance and source-only
occurrence extras. Does not infer variants from labels or synthesize roll state.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from infinity_db.catalog_rules import CatalogRules
from infinity_db.database.repository import Database
from infinity_db.rules_database import RulesDatabase
from infinity_db.skill_catalog import SkillCatalog

ROOT = Path(__file__).resolve().parents[1]
ARMY_DB = ROOT / "data/generated/infinity.db"
RAW_DB = ROOT / "data/generated/infinity.raw.db"
RULES_DB = ROOT / "data/generated/rules.db"

SKILL_VARIANTS: dict[str, dict[int, tuple[str, dict[str, Any], int]]] = {
    "strategos": {
        69: ("skill:strategos-l1", {"kind": "level", "value": 1}, 113),
        70: ("skill:strategos-l2", {"kind": "level", "value": 2}, 113),
    },
    "bs-attack": {
        278: (
            "skill:bs-12",
            {"kind": "attribute-replacement", "attribute": "BS", "value": 12},
            39,
        ),
        279: (
            "skill:bs-11",
            {"kind": "attribute-replacement", "attribute": "BS", "value": 11},
            39,
        ),
    },
    "cc-attack": {
        274: (
            "skill:cc-21",
            {"kind": "attribute-replacement", "attribute": "CC", "value": 21},
            51,
        ),
    },
}

# A reviewed definition does not imply the current Army snapshot uses it.
PUBLISHED_TINBOT_IDS = {169, 244, 247, 248}

TINBOT_VARIANTS: dict[int, tuple[str, str]] = {
    169: ("equipment:tinbot-firewall", "Firewall"),
    188: ("equipment:tinbot-neurocinetics", "Neurocinetics"),
    193: ("equipment:tinbot-albedo", "Albedo"),
    244: ("equipment:tinbot-discover", "Discover"),
    247: ("equipment:tinbot-ecm-guided", "ECM Guided"),
    248: ("equipment:tinbot-repeater", "Repeater"),
}


def _source_members(catalog: str, source_ids: set[int]) -> list[tuple[int, int]]:
    with sqlite3.connect(ARMY_DB) as connection:
        return [
            (int(source_id), int(application_id))
            for source_id, application_id in connection.execute(
                "SELECT source_item_id, application_item_id "
                "FROM application_catalog_sources WHERE catalog = ? "
                "ORDER BY source_item_id",
                (catalog,),
            )
            if source_id in source_ids
        ]


def _source_extras(
    catalog: str, ids: set[int]
) -> dict[tuple[str, int, int], tuple[tuple[int, str, str], ...]]:
    """Retrieve direct source relationships, not reusable payload identities."""
    result: dict[tuple[str, int, int], tuple[tuple[int, str, str], ...]] = {}
    extra_suffix = "skill" if catalog == "skills" else catalog
    with sqlite3.connect(RAW_DB) as connection:
        for prefix in ("profile", "option", "unit_option"):
            rows = connection.execute(
                f"SELECT o.item_id, o.occurrence_id, e.extra_id, x.type, x.name "
                f"FROM {prefix}_{catalog} AS o "
                f"LEFT JOIN {prefix}_{extra_suffix}_extras AS e "
                f"ON e.occurrence_id = o.occurrence_id "
                f"LEFT JOIN extras AS x ON x.id = e.extra_id "
                f"ORDER BY o.item_id, o.occurrence_id, e.position"
            ).fetchall()
            for item_id, occurrence_id, extra_id, extra_type, extra_name in rows:
                if item_id not in ids:
                    continue
                key = (prefix, int(item_id), int(occurrence_id))
                values = list(result.get(key, ()))
                if extra_id is not None:
                    values.append((int(extra_id), str(extra_type), str(extra_name)))
                result[key] = tuple(values)
    return result


@pytest.mark.parametrize("family", sorted(SKILL_VARIANTS))
def test_other_skill_source_variants_have_exact_reviewed_identity(family: str) -> None:
    expected = SKILL_VARIANTS[family]
    army = Database(ARMY_DB)
    rules = RulesDatabase(RULES_DB)
    actual_members = _source_members("skills", set(expected))
    assert {source_id for source_id, _ in actual_members} == set(expected)
    assert len({application_id for _, application_id in actual_members}) == 1
    assert set(expected) <= set(army.skill_source_ids(family))
    source_variants = rules.catalog_source_variant_semantics("skill")
    detail = SkillCatalog(army, rules).get_skill(family)
    assert detail is not None
    visible = {
        int(variant["skill_id"]): variant
        for variant in detail["variants"]
        if int(variant["skill_id"]) in expected
    }
    assert visible, (family, "No direct published source use")
    for source_id, (record_id, variant_value, page) in expected.items():
        assert source_variants[source_id] == variant_value
        record = rules.composed_record(record_id)
        assert record is not None
        assert record["review"]["status"] == "reviewed"
        assert record["variant_semantics"]["inheritance"] == "source"
        assert record["variant_semantics"]["source_variant"] == variant_value
        assert any(
            citation["source_id"] == "n5-core-v5.3-pdf" and citation["page"] == page
            for citation in record["citations"]
        )
        if source_id in visible:
            assert visible[source_id]["source_variant"] == variant_value
            assert record_id in {
                rule["id"] for rule in visible[source_id].get("rules", [])
            }
    # A typed Level/Attribute replacement belongs to the source identity;
    # the pinned snapshot must not carry unknown occurrence extras on it.
    occurrences = _source_extras("skills", set(expected))
    assert occurrences, family
    assert all(not extras for extras in occurrences.values()), (family, occurrences)


def test_tinbot_named_variants_keep_source_extras_and_reviewed_identity() -> None:
    army = Database(ARMY_DB)
    rules = RulesDatabase(RULES_DB)
    actual_members = _source_members("equipment", set(TINBOT_VARIANTS))
    assert {source_id for source_id, _ in actual_members} == PUBLISHED_TINBOT_IDS
    assert len({application_id for _, application_id in actual_members}) == 1
    source_variants = rules.catalog_source_variant_semantics("equipment")

    detail = army.get_catalog_item("equipment", "tinbot")
    assert detail is not None
    enriched = CatalogRules(rules).enrich_catalog_item("equipment", detail)
    visible = [v for v in enriched["variants"] if v["item_id"] in TINBOT_VARIANTS]
    assert visible, "No direct published TinBot source use"
    for source_id, (record_id, label) in TINBOT_VARIANTS.items():
        variant_value = {"kind": "named", "label": label}
        assert source_variants[source_id] == variant_value
        record = rules.composed_record(record_id)
        assert record is not None
        assert record["review"]["status"] == "reviewed"
        assert record["variant_semantics"]["inheritance"] == "source"
        assert record["variant_semantics"]["source_variant"] == variant_value
        assert any(
            citation["source_id"] == "n5-core-v5.3-pdf" and citation["page"] == 127
            for citation in record["citations"]
        )
    occurrences = _source_extras("equipment", set(TINBOT_VARIANTS))
    assert occurrences, "No source-level TinBot relationship provenance"
    assert any(extras for extras in occurrences.values()), "TinBot source MOD extras missing"
    assert {item_id for _, item_id, _ in occurrences} <= PUBLISHED_TINBOT_IDS
    for variant in visible:
        source_id = int(variant["item_id"])
        record_id, label = TINBOT_VARIANTS[source_id]
        assert variant["source_variant"] == {"kind": "named", "label": label}
        assert record_id in {rule["id"] for rule in variant.get("rules", [])}
        # Distinct parameter extras must remain attached to exact source
        # occurrence variants. They are *not* inferred from the TinBot name.
        listed_extras = tuple(
            (int(item["id"]), str(item["name"])) for item in variant["extras"]
        )
        assert listed_extras in {
            tuple((extra_id, extra_name) for extra_id, _type, extra_name in extras)
            for (scope, item_id, _occurrence), extras in occurrences.items()
            if item_id == source_id
        }, (source_id, listed_extras)
