"""Source-bound variant usage projection regression and fail-closed contracts."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from infinity_db import variant_usage
from infinity_db.variant_usage import (
    _assert_complete_owner_rows,
    _include_peripheral_provenance,
    _published_extras_match,
    _resolve_effect,
    build_variant_usage_projection,
)

ROOT = Path(__file__).resolve().parents[1]


def _extra(extra_id: int, raw: str, *, position: int = 1) -> dict[str, object]:
    return {"position": position, "extraId": extra_id,
            "extraType": "TEXT", "rawValue": raw}


def test_variant_usage_never_promotes_partial_or_unknown_extras() -> None:
    family = {
        "inheritance": "family",
        "occurrence_parameters": [{
            "source": "army-extra", "kind": "reviewed-extra",
            "extra_values": [{
                "extra_id": 250, "extra_type": "TEXT", "raw_value": "PH=12",
                "effect": {"kind": "infiltration-roll-ph-value",
                           "applies_to": "infiltration-ph-minus-three-roll",
                           "value": 12},
            }],
        }],
    }
    assert _resolve_effect(family, []) == ("family", None)
    state, typed = _resolve_effect(family, [_extra(250, "PH=12")])
    assert state == "exact" and typed is not None
    assert typed["parameter"]["effect"]["value"] == 12
    assert _resolve_effect(family, [_extra(277, "ReRoll")]) == ("unresolved", None)
    assert _resolve_effect(
        family, [_extra(250, "PH=12"), _extra(277, "ReRoll", position=2)]
    ) == ("unresolved", None)
    assert _resolve_effect(family, [_extra(250, "PH=13")]) == ("unresolved", None)


def test_variant_usage_exact_multi_extra_order_and_distinct_mods() -> None:
    variant = {
        "inheritance": "source",
        "source_variant": {"kind": "named", "value": "Example"},
        "occurrence_combinations": [{
            "extras": [
                {"extra_id": 6, "extra_type": "TEXT", "raw_value": "-3"},
                {"extra_id": 8, "extra_type": "TEXT", "raw_value": "+1B"},
            ],
            "effects": [
                {"kind": "target-roll-mod", "modifier": -3},
                {"kind": "burst-mod", "modifier": 1},
            ],
        }],
    }
    a, effect = _resolve_effect(
        variant, [_extra(6, "-3"), _extra(8, "+1B", position=2)]
    )
    assert a == "exact" and effect is not None
    assert len(effect["combinationEffects"]) == 2
    assert _resolve_effect(
        variant, [_extra(8, "+1B"), _extra(6, "-3", position=2)]
    ) == ("unresolved", None)
    assert _resolve_effect(variant, [_extra(6, "-3")]) == ("unresolved", None)


def test_variant_usage_published_extras_reject_drift_and_reordered_source() -> None:
    with sqlite3.connect(":memory:") as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("CREATE TABLE extras (id INTEGER, type TEXT, name TEXT)")
        connection.execute(
            "CREATE TABLE profile_payload_skill_extras "
            "(profile_payload_id INTEGER, occurrence_position INTEGER, "
            "position INTEGER, extra_id INTEGER)"
        )
        connection.executemany(
            "INSERT INTO extras VALUES (?, ?, ?)",
            [(6, "TEXT", "-3"), (8, "TEXT", "+1B")],
        )
        connection.executemany(
            "INSERT INTO profile_payload_skill_extras VALUES (1, 3, ?, ?)",
            [(1, 6), (2, 8)],
        )
        row = {
            "catalog": "skills", "position": 3,
            "extras": [_extra(6, "-3"), _extra(8, "+1B", position=2)],
        }
        assert _published_extras_match(connection, row, "profile", 1)
        assert not _published_extras_match(
            connection, {**row, "extras": list(reversed(row["extras"]))},
            "profile", 1,
        )
        connection.execute("UPDATE extras SET name = '+1 SD' WHERE id = 8")
        assert not _published_extras_match(connection, row, "profile", 1)


def test_variant_usage_include_and_peripheral_edges_are_context_only() -> None:
    with sqlite3.connect(":memory:") as connection:
        connection.row_factory = sqlite3.Row
        for table in (
            "profile_occurrence_includes", "loadout_occurrence_includes",
            "unit_option_include_targets",
        ):
            connection.execute(
                f"CREATE TABLE {table} "
                "(position INTEGER, target_loadout_payload_id INTEGER, "
                "quantity INTEGER)"
            )
        connection.execute(
            "INSERT INTO profile_occurrence_includes VALUES (1, 17, 2)"
        )
        connection.execute(
            "INSERT INTO loadout_occurrence_includes VALUES (2, 19, 1)"
        )
        connection.execute(
            "CREATE TABLE application_peripheral_controller_access "
            "(id INTEGER, source_id TEXT, controller_kind TEXT, "
            "army_id INTEGER, unit_id INTEGER, group_id INTEGER, parent_id INTEGER)"
        )
        connection.execute(
            "CREATE TABLE application_peripheral_controller_targets "
            "(access_id INTEGER, target_logical_unit_id INTEGER)"
        )
        connection.execute(
            "INSERT INTO application_peripheral_controller_access "
            "VALUES (7, 'pinned', 'profile', 701, 185, 1, 1)"
        )
        connection.execute(
            "INSERT INTO application_peripheral_controller_targets VALUES (7, 42)"
        )
        result = _include_peripheral_provenance(connection)
        assert [item["kind"] for item in result["includes"]] == [
            "loadout_occurrence_includes", "profile_occurrence_includes"
        ]
        assert result["peripheralControllerEdges"] == [{
            "access_id": 7, "source_id": "pinned",
            "controller_kind": "profile", "army_id": 701,
            "unit_id": 185, "group_id": 1, "parent_id": 1,
            "target_logical_unit_id": 42,
        }]
        assert "never counted as direct" in result["policy"]


def test_variant_usage_truncated_raw_relationships_fail_closed() -> None:
    with sqlite3.connect(":memory:") as connection:
        connection.execute("CREATE TABLE unit_option_skills (occurrence_id INTEGER)")
        connection.executemany(
            "INSERT INTO unit_option_skills VALUES (?)", [(1,), (2,)]
        )
        _assert_complete_owner_rows(connection, "skills", "unit_option", 2)
        with pytest.raises(ValueError, match="relationship count differs"):
            _assert_complete_owner_rows(connection, "skills", "unit_option", 1)


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_variant_usage_mismatched_raw_snapshot_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = iter(("a" * 64, "b" * 64))
    monkeypatch.setattr(variant_usage, "_snapshot", lambda _db: next(values))
    with pytest.raises(ValueError, match="raw archive does not match"):
        build_variant_usage_projection(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db",
            ROOT / "data/generated/rules.db",
            ROOT / "data/generated/deployed-objects.json",
        )


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_variant_usage_pinned_pair_has_source_ownership_not_inferred_includes() -> None:
    projection = build_variant_usage_projection(
        ROOT / "data/generated/infinity.db",
        ROOT / "data/generated/infinity.raw.db",
        ROOT / "data/generated/rules.db",
        ROOT / "data/generated/deployed-objects.json",
    )
    assert projection["scope"] == "read-only-candidate-not-published"
    assert projection["formatVersion"] == 1
    assert len(projection["sourceSnapshot"]["armyArchiveSha256"]) == 64
    assert projection["relationships"]["policy"].startswith("context-only")
    assert projection["relationships"]["includes"]
    assert isinstance(projection["relationships"]["peripheralControllerEdges"], list)
    assert projection["variants"]
    assert {f"skill:martial-arts-l{level}" for level in range(1, 6)} <= {
        group["variant"]["recordId"] for group in projection["variants"]
    }
    assert all(
        group["uniqueUnits"] <= group["uniqueArmyUnits"]
        <= group["sourceRelationshipRows"]
        and group["sourceRows"]
        for group in projection["variants"]
    )
    for group in projection["variants"]:
        contexts = [
            row["context"] for row in group["sourceRows"]
            if row["context"]["applicationArmyId"] is not None
        ]
        assert group["uniqueUnits"] == len({
            context["logicalUnitId"] for context in contexts
        })
        assert group["uniqueArmyUnits"] == len({
            (context["applicationArmyId"], context["logicalUnitId"])
            for context in contexts
        })
    # Five bare Infiltration ReRolls and Doctor 2W are source-native
    # unresolved occurrence annotations, never fabricated typed effects.
    raw_unresolved = {
        (item["catalog"], item["sourceId"], item["occurrenceId"])
        for item in projection["unresolvedSourceRows"]
    }
    assert {("skills", 47, number) for number in
            (44546, 74177, 61511, 65105, 67248)} <= raw_unresolved
    assert {("skills", 53, number) for number in
            (33478, 34014, 34181, 35960)} <= raw_unresolved
    assert projection["diagnosticCounts"]["unreviewed-signature"] >= 9
    # No include or controller relationship can fabricate a direct owner.
    for group in projection["variants"]:
        for owner in group["sourceRows"]:
            assert owner["ownerKind"] in {"profile", "option", "unit_option"}
            assert owner["occurrenceId"] is not None
            assert not any(k in owner for k in ("includePosition", "peripheralId"))
    # Stable canonical output independent of incidental dict iteration.
    assert json.loads(json.dumps(projection, sort_keys=True)) == projection
