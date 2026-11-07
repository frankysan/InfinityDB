"""Bounded published-payload to Unit API parity without assuming logical merge cardinality.

The pinned application database is the evidence source here; the separate
Army ZIP audit proves that its reusable payload rows match pinned source.
Only individually identifiable profile/loadout occurrences are compared.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.skill_config import load_skill_source_config
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


def _presentation_item_key(item: dict[str, Any]) -> tuple[Any, ...]:
    """Use the visible presentation identity, including canonical quantity."""
    quantity = item.get("quantity")
    if quantity is None or quantity == 1:
        quantity = None
    extras = tuple(sorted(
        (extra["id"] for extra in item.get("extras", ())),
        key=str,
    ))
    return (item["id"], quantity, extras)


def _common_presentation_items(
    contexts: list[dict[str, Any]], field: str,
) -> list[tuple[Any, ...]]:
    if not contexts:
        return []
    first = [_presentation_item_key(item) for item in contexts[0][field]]
    return list(dict.fromkeys(
        identity for identity in first
        if all(
            any(_presentation_item_key(item) == identity for item in other[field])
            for other in contexts[1:]
        )
    ))


def _modal_stat(profiles: list[dict[str, Any]], field: str) -> Any:
    values = [p[field] for p in profiles if p.get(field) not in (None, "")]
    return Counter(values).most_common(1)[0][0] if values else None


def test_presentation_shared_identity_preserves_quantities_and_extra_variants() -> None:
    def item(quantity: int | None, extras: list[int]) -> dict[str, Any]:
        return {
            "id": 31, "quantity": quantity,
            "extras": [{"id": value} for value in extras],
        }

    first = {"weapons": [item(1, [43, 42]), item(2, [42]), item(1, [43, 42])]}
    second = {"weapons": [item(None, [42, 43]), item(3, [42])]}
    assert _common_presentation_items([first, second], "weapons") == [
        (31, None, (42, 43))
    ]
    assert _presentation_item_key(item(2, [42])) == (31, 2, (42,))
    assert _common_presentation_items([], "weapons") == []


def _source_general_skills(
    profiles: list[dict[str, Any]], loadouts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Reconstruct source Skill sharing before the presentation classification."""
    shared = _common_presentation_items(profiles, "skills")
    raw = [
        next(item for item in profiles[0]["skills"] if _presentation_item_key(item) == key)
        for key in shared
    ]
    if len(loadouts) == 1:
        for skill in loadouts[0]["skills"]:
            identity = _presentation_item_key(skill)
            if identity not in shared:
                shared.append(identity)
                raw.append(skill)
    return raw


def _assert_skill_buckets_preserve_source(
    source_skills: list[dict[str, Any]],
    presented: dict[str, Any],
    classifications: dict[str, str],
    observed: Counter[str],
    context: tuple[Any, ...],
) -> None:
    """Check the classified API projection without calling the classifier itself."""
    categories = {
        "equipment": "equipment",
        "training": "training",
        "source-marker": "source_markers",
        "attribute-override": "attribute_overrides",
    }
    expected: dict[str, list[tuple[Any, ...]]] = {
        bucket: [] for bucket in ("skills", *categories.values())
    }
    native_equipment = {
        (
            " ".join(str(item.get("slug") or item.get("name") or "").casefold().split()),
            _presentation_item_key(item)[1:],
        )
        for item in presented["equipment"]
        if item.get("source_classification") != "equipment"
    }
    projected_seen = set(native_equipment)
    for skill in source_skills:
        category = classifications.get(str(skill.get("slug") or ""))
        bucket = categories.get(category or "", "skills")
        key = _presentation_item_key(skill)
        if bucket == "equipment":
            display_key = (
                " ".join(str(skill.get("slug") or skill.get("name") or "").casefold().split()),
                key[1:],
            )
            if display_key in projected_seen:
                continue
            projected_seen.add(display_key)
        expected[bucket].append(key)
        observed[f"source.{category or 'skill'}"] += 1
    for bucket, expected_items in expected.items():
        presented_items = presented.get(bucket, [])
        if bucket == "equipment":
            presented_items = [
                item for item in presented_items
                if item.get("source_classification") == "equipment"
            ]
        actual = [_presentation_item_key(item) for item in presented_items]
        assert actual == expected_items, (
            context, bucket, expected_items, actual
        )
        observed[f"matched.{bucket}"] += len(actual)


def test_skill_bucket_projection_preserves_variants_and_rejects_loss() -> None:
    """Exercise every reviewed non-Skill category, including native Equipment dedup."""
    classifications = {
        str(item.skill_ref): item.classification
        for item in load_skill_source_config()
    }

    def skill(
        skill_id: int, slug: str, *, quantity: int | None = None,
        extras: tuple[int, ...] = (),
    ) -> dict[str, Any]:
        return {
            "id": skill_id, "slug": slug, "name": slug,
            "quantity": quantity,
            "extras": [{"id": extra} for extra in extras],
        }

    gizmo_two = skill(254, "gizmokit", quantity=2, extras=(41,))
    gizmo_one = skill(254, "gizmokit", quantity=1, extras=(41,))
    bangbomb = skill(266, "bangbomb", extras=(42,))
    training = skill(258, "regular")
    marker = skill(282, "infinity-team-ops")
    override = skill(280, "bts-3")
    ordinary = skill(99, "stealth")
    native_bangbomb = {
        **skill(246, "bangbomb", extras=(42,)),
    }
    projected = {
        "skills": [ordinary],
        "equipment": [
            native_bangbomb,
            {**gizmo_two, "source_classification": "equipment"},
            {**gizmo_one, "source_classification": "equipment"},
        ],
        "training": [training],
        "source_markers": [marker],
        "attribute_overrides": [override],
    }
    raw = [
        gizmo_two, gizmo_one, bangbomb, training, marker, override, ordinary,
    ]
    coverage: Counter[str] = Counter()
    _assert_skill_buckets_preserve_source(
        raw, projected, classifications, coverage, ("synthetic",),
    )
    assert coverage["matched.equipment"] == 2
    assert coverage["matched.training"] == 1
    assert coverage["matched.source_markers"] == 1
    assert coverage["matched.attribute_overrides"] == 1
    assert coverage["matched.skills"] == 1

    for bucket in ("training", "source_markers", "attribute_overrides"):
        malformed = deepcopy(projected)
        malformed[bucket] = []
        with pytest.raises(AssertionError):
            _assert_skill_buckets_preserve_source(
                raw, malformed, classifications, Counter(), ("deleted", bucket),
            )
    changed_quantity = deepcopy(projected)
    changed_quantity["equipment"][1]["quantity"] = 3
    with pytest.raises(AssertionError):
        _assert_skill_buckets_preserve_source(
            raw, changed_quantity, classifications, Counter(), ("quantity",),
        )
    changed_extra = deepcopy(projected)
    changed_extra["equipment"][1]["extras"][0]["id"] = 88
    with pytest.raises(AssertionError):
        _assert_skill_buckets_preserve_source(
            raw, changed_extra, classifications, Counter(), ("extra",),
        )


def test_general_skill_source_selection_respects_single_loadout() -> None:
    common = {
        "skills": [
            {"id": 2, "quantity": None, "extras": []},
        ]
    }
    another = {
        "skills": [
            {"id": 2, "quantity": None, "extras": []},
            {"id": 3, "quantity": 2, "extras": [{"id": 40}]},
        ]
    }
    loadout = {
        "skills": [
            {"id": 2, "quantity": None, "extras": []},
            {"id": 4, "quantity": 1, "extras": []},
        ]
    }
    assert [
        _presentation_item_key(item)
        for item in _source_general_skills([common, another], [loadout])
    ] == [(2, None, ()), (4, None, ())]
    assert [
        _presentation_item_key(item)
        for item in _source_general_skills([common, another], [loadout, loadout])
    ] == [(2, None, ())]


def test_multi_source_general_profiles_preserve_army_differences() -> None:
    """Verify cross-Army shared/delta projection for multi-source logical Units."""
    assert ARMY_DB.is_file() and RULES_DB.is_file()
    app = create_app(ARMY_DB, rules_database_path=RULES_DB)
    checked_units = 0
    checked_general = 0
    checked_shared_weapons = 0
    checked_specific_weapons = 0
    checked_shared_equipment = 0
    checked_specific_equipment = 0
    checked_varied_statlines = 0
    classified = Counter()
    classifications = {
        str(record.skill_ref): record.classification
        for record in load_skill_source_config()
    }
    with sqlite3.connect(f"{ARMY_DB.resolve().as_uri()}?mode=ro", uri=True) as db:
        candidates = db.execute(
            "SELECT lu.slug FROM logical_units AS lu "
            "JOIN logical_unit_sources AS lus ON lus.logical_unit_id = lu.id "
            "WHERE lu.slug IS NOT NULL "
            "GROUP BY lu.id, lu.slug HAVING COUNT(DISTINCT lus.source_unit_id) > 1 "
            "ORDER BY lu.slug"
        ).fetchall()
        assert candidates, "No multi-source logical Units in pinned publication"
        for (slug,) in candidates:
            unit = _api_unit(app, str(slug))
            visible_armies = [
                army for army in unit["armies"] if army["presentation_visible"]
            ]
            if len({army["id"] for army in visible_armies}) < 2:
                continue
            matched_for_unit = False
            shared_by_group: dict[tuple[int, int], set[tuple[Any, ...]]] = {}
            for general in unit["general_profiles"]:
                identity = general["profile_identity"]
                contributors = [
                    (army, profile)
                    for army in visible_armies
                    for profile in army["profiles"]
                    if profile["profile_identity"] == identity
                ]
                if len({army["id"] for army, _ in contributors}) < 2:
                    continue
                matched_for_unit = True
                checked_general += 1
                profiles = [profile for _, profile in contributors]
                assert general["occurrence_count"] == len(profiles), (
                    slug, identity, general["occurrence_count"], len(profiles)
                )
                for stat in (
                    "move_1", "move_2", "cc", "bs", "ph", "wip",
                    "arm", "bts", "vitality", "silhouette", "is_structure",
                ):
                    assert general["stats"][stat] == _modal_stat(profiles, stat), (
                        slug, identity, stat, general["stats"][stat],
                    )
                for label, stat in (("BS", "bs"), ("ARM", "arm"), ("VITA", "vitality")):
                    if any(p[stat] != profiles[0][stat] for p in profiles[1:]):
                        assert label in general["different_stat_labels"], (
                            slug, identity, label, general["different_stat_labels"]
                        )
                        checked_varied_statlines += 1
                common_equipment = set(
                    _common_presentation_items(profiles, "equipment")
                )
                displayed_equipment = {
                    _presentation_item_key(item)
                    for item in general["shared_items"]["equipment"]
                }
                # Reviewed Skill-to-Equipment reclassification may add
                # equipment presentation items, but must not remove actual
                # source Equipment shared across these profiles.
                assert common_equipment <= displayed_equipment, (slug, identity)
                checked_shared_equipment += len(common_equipment)
                for _, profile in contributors:
                    specific_equipment = {
                        _presentation_item_key(item)
                        for item in profile["specific_items"]["equipment"]
                    }
                    for item in profile["equipment"]:
                        item_key = _presentation_item_key(item)
                        if item_key not in displayed_equipment:
                            assert item_key in specific_equipment, (
                                slug, identity, item_key
                            )
                            checked_specific_equipment += 1
                contexts = {
                    (army["id"], profile["group_id"])
                    for army, profile in contributors
                }
                matching_loadouts = [
                    loadout for army in visible_armies
                    for loadout in army["loadouts"]
                    if (army["id"], loadout["group_id"]) in contexts
                ]
                raw_general_skills = _source_general_skills(
                    profiles, matching_loadouts,
                )
                _assert_skill_buckets_preserve_source(
                    raw_general_skills, general["shared_items"],
                    classifications, classified, (slug, identity, "general"),
                )
                shared_ids = {
                    _presentation_item_key(item) for item in raw_general_skills
                }
                for army, profile in contributors:
                    shared_by_group.setdefault(
                        (army["id"], profile["group_id"]), set()
                    ).update(shared_ids)
                    source_specific = [
                        item for item in profile["skills"]
                        if _presentation_item_key(item) not in shared_ids
                    ]
                    _assert_skill_buckets_preserve_source(
                        source_specific, profile["specific_items"],
                        classifications, classified,
                        (slug, army["id"], profile["group_id"], "profile"),
                    )
                expected = _common_presentation_items(matching_loadouts, "weapons")
                actual = [
                    _presentation_item_key(item)
                    for item in general["shared_items"]["weapons"]
                ]
                assert actual == expected, (slug, identity, expected, actual)
                checked_shared_weapons += len(expected)
                shared = set(expected)
                for loadout in matching_loadouts:
                    expected_specific = [
                        _presentation_item_key(item) for item in loadout["weapons"]
                        if _presentation_item_key(item) not in shared
                    ]
                    actual_specific = [
                        _presentation_item_key(item)
                        for item in loadout["specific_items"]["weapons"]
                    ]
                    assert actual_specific == expected_specific, (
                        slug, identity, loadout["name"],
                        expected_specific, actual_specific,
                    )
                    checked_specific_weapons += len(expected_specific)
            for army in visible_armies:
                for loadout in army["loadouts"]:
                    key = (army["id"], loadout["group_id"])
                    if key not in shared_by_group:
                        continue
                    source_specific = [
                        item for item in loadout["skills"]
                        if _presentation_item_key(item) not in shared_by_group[key]
                    ]
                    _assert_skill_buckets_preserve_source(
                        source_specific, loadout["specific_items"],
                        classifications, classified,
                        (slug, army["id"], loadout["group_id"], "loadout"),
                    )
            if matched_for_unit:
                checked_units += 1
            if (
                checked_units >= 12 and checked_general >= 18
                and checked_shared_weapons > 0
                and checked_specific_weapons > 0
                and checked_shared_equipment > 0
                and checked_specific_equipment > 0
                and checked_varied_statlines > 0
            ):
                break
    assert checked_units >= 12, checked_units
    assert checked_general >= 18, checked_general
    assert checked_shared_weapons > 0, checked_shared_weapons
    assert checked_specific_weapons > 0, checked_specific_weapons
    assert checked_shared_equipment > 0, checked_shared_equipment
    assert checked_specific_equipment > 0, checked_specific_equipment
    assert checked_varied_statlines > 0, checked_varied_statlines
    assert classified["matched.skills"] > 0, classified
    assert classified["matched.equipment"] > 0, classified
