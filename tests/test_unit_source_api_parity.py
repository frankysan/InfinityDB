"""Bounded published-payload to Unit API parity without assuming logical merge cardinality.

The pinned application database is the evidence source here; the separate
Army ZIP audit proves that its reusable payload rows match pinned source.
Only individually identifiable profile/loadout occurrences are compared.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]
ARMY_DB = ROOT / "data/generated/infinity.db"
RULES_DB = ROOT / "data/generated/rules.db"

REFERENCE_FIELDS = (
    ("skills", "skill_extras"),
    ("equipment", "equipment_extras"),
    ("weapons", "weapon_extras"),
)


def _api_unit(app: Any, slug: str) -> dict[str, Any]:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=f"/api/units/{slug}", REQUEST_METHOD="GET")
    statuses: list[int] = []

    def start_response(
        status: str, headers: list[tuple[str, str]], exc_info: Any = None,
    ) -> None:
        statuses.append(int(status.split()[0]))

    response = app(environ, start_response)
    try:
        body = b"".join(response)
    finally:
        close = getattr(response, "close", None)
        if close is not None:
            close()
    assert statuses == [200], (slug, statuses)
    return json.loads(body)


def _source_payload_items(
    db: sqlite3.Connection, kind: str, payload_id: int,
    field: str, extra_suffix: str,
) -> list[tuple[Any, ...]]:
    result: list[tuple[Any, ...]] = []
    for position, item_id, quantity in db.execute(
        f"SELECT position, item_id, quantity FROM {kind}_payload_{field} "
        f"WHERE {kind}_payload_id = ? ORDER BY position",
        (payload_id,),
    ):
        extras = tuple(row[0] for row in db.execute(
            f"SELECT extra_id FROM {kind}_payload_{extra_suffix} "
            f"WHERE {kind}_payload_id = ? AND occurrence_position = ? "
            "ORDER BY position",
            (payload_id, position),
        ))
        result.append((item_id, quantity, extras))
    return result


def _api_payload_items(context: dict[str, Any], field: str) -> list[tuple[Any, ...]]:
    return [
        (
            item["id"], item["quantity"],
            tuple(extra["id"] for extra in item["extras"]),
        )
        for item in context[field]
    ]


def test_source_unique_profile_loadout_references_reach_unit_api() -> None:
    """Compare exact ordered references where logical-source merging is unambiguous."""
    assert ARMY_DB.is_file() and RULES_DB.is_file()
    app = create_app(ARMY_DB, rules_database_path=RULES_DB)
    checked: Counter[str] = Counter()
    checked_extras = 0
    compared_contexts = 0
    ambiguous_contexts = 0
    with sqlite3.connect(f"{ARMY_DB.resolve().as_uri()}?mode=ro", uri=True) as db:
        candidates = db.execute(
            "SELECT DISTINCT lu.slug, lus.source_unit_id, au.army_id, "
            "aas.application_army_id "
            "FROM logical_unit_sources AS lus "
            "JOIN logical_units AS lu ON lu.id = lus.logical_unit_id "
            "JOIN army_units AS au ON au.unit_id = lus.source_unit_id "
            "JOIN application_army_sources AS aas ON aas.source_army_id = au.army_id "
            "WHERE lu.slug IS NOT NULL "
            "AND (SELECT COUNT(*) FROM logical_unit_sources AS s "
            "     WHERE s.logical_unit_id = lus.logical_unit_id) = 1 "
            "AND (SELECT COUNT(*) FROM army_units AS a "
            "     WHERE a.unit_id = lus.source_unit_id) = 1 "
            "AND (SELECT COUNT(*) FROM application_army_sources AS s "
            "     WHERE s.source_army_id = au.army_id) = 1 "
            "AND EXISTS (SELECT 1 FROM profile_payload_occurrences AS p "
            "            WHERE p.unit_id = lus.source_unit_id AND p.army_id = au.army_id) "
            "AND EXISTS (SELECT 1 FROM loadout_payload_occurrences AS l "
            "            WHERE l.unit_id = lus.source_unit_id AND l.army_id = au.army_id) "
            "ORDER BY lu.slug"
        ).fetchall()
        assert len(candidates) >= 12, len(candidates)
        checked_units = 0
        for slug, source_unit, source_army, app_army in candidates:
            unit = _api_unit(app, str(slug))
            armies = [a for a in unit["armies"] if a["id"] == app_army]
            if len(armies) != 1:
                ambiguous_contexts += 1
                continue
            army = armies[0]
            checked_units += 1
            for kind, parent_id, payload_id_col in (
                ("profile", "profile_id", "profile_payload_id"),
                ("loadout", "option_id", "loadout_payload_id"),
            ):
                rows = db.execute(
                    f"SELECT group_id, {parent_id}, {payload_id_col} "
                    f"FROM {kind}_payload_occurrences "
                    "WHERE army_id = ? AND unit_id = ? ORDER BY group_id, position",
                    (source_army, source_unit),
                ).fetchall()
                for group_id, parent_value, payload_id in rows:
                    contexts = [
                        p for p in army[f"{kind}s"]
                        if p["group_id"] == group_id and p[parent_id] == parent_value
                    ]
                    if len(contexts) != 1:
                        ambiguous_contexts += 1
                        continue
                    context = contexts[0]
                    compared_contexts += 1
                    for field, extra_suffix in REFERENCE_FIELDS:
                        expected = _source_payload_items(
                            db, kind, payload_id, field, extra_suffix,
                        )
                        actual = _api_payload_items(context, field)
                        # The player-facing model can collapse duplicate items.
                        # Compare exact order only when individual item tuples are unique.
                        if len(set(expected)) != len(expected):
                            ambiguous_contexts += 1
                            continue
                        assert actual == expected, (
                            slug, source_army, source_unit, kind,
                            group_id, parent_value, field, expected, actual,
                        )
                        checked[f"{kind}.{field}"] += len(expected)
                        checked_extras += sum(len(extras) for _, _, extras in expected)
            if checked_units >= 24 and checked_extras > 0 and all(
                checked[f"{kind}.{field}"] for kind in ("profile", "loadout")
                for field, _ in REFERENCE_FIELDS
            ):
                break

    assert checked_units >= 12, checked_units
    assert compared_contexts >= 24, (compared_contexts, ambiguous_contexts)
    assert checked_extras > 0, checked
    assert all(
        checked[f"{kind}.{field}"] > 0
        for kind in ("profile", "loadout")
        for field, _ in REFERENCE_FIELDS
    ), checked
