"""Protect optional N4-origin Reinforcements references in the N5-era player catalog.

These assertions cover the source boundary, not verified N5 adoption of N4 procedures.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from infinity_db.curated import load_curated_directory, load_curated_document
from infinity_db.database.repository import Database
from infinity_db.reference_catalog import RulesRecordCatalog
from infinity_db.rules_database import RulesDatabase, export_rules_database
from infinity_db.skill_catalog import SkillCatalog

ROOT = Path(__file__).resolve().parents[1]
ANNEX = ROOT / "data/curated/rules/reinforcements-extra-n4-reference.json"


def test_annex_current_optional_reference_discloses_n4_source_boundary() -> None:
    document = load_curated_document(ANNEX)
    assert document["collection"]["id"] == "reinforcements-extra-n4-reference"
    assert document["collection"]["authority"] == "secondary"
    assert document["collection"]["status"] == "current"
    sources = {source["id"]: source for source in document["sources"]}
    assert sources["reinforcements-annex-wiki-n4"]["version"].startswith("N4 Annex")
    assert sources["reinforcements-its-season-18"]["version"] == "2026.09.01"
    assert sources["reinforcements-n5-core"]["version"] == "5.3"

    records = {record["id"]: record for record in document["records"]}
    assert set(records) == {
        "rule:reinforcements-extra", "skill:commlink", "skill:request-reinforcements",
    }
    for record in records.values():
        assert record["scope"] == {"game": "N5", "seasons": ["current"]}
        assert record["review"]["status"] == "reviewed"
        assert "N4" in record["summary"]
        assert record["facts"]["sourceNotes"]
        assert any(
            citation["sourceId"] == "reinforcements-annex-wiki-n4"
            for citation in record["citations"]
        )
    assert records["rule:reinforcements-extra"]["facts"]["category"] == "optional-extra"
    assert records["skill:commlink"]["armyLinks"] == [
        {"entity": "skill", "id": "commlink"},
    ]
    variant = records["skill:commlink"]["variantSemantics"]
    assert variant["inheritance"] == "family"
    assert variant["occurrenceParameters"] == [{
        "source": "army-extra", "kind": "reviewed-extra",
        "extraValues": [
            {
                "extraId": extra_id, "extraType": "TEXT", "rawValue": f"+{count}",
                "effect": {
                    "kind": "max-trooper-count-increase",
                    "appliesTo": "optional-reinforcements-extra-army-list",
                    "count": count,
                },
            }
            for extra_id, count in ((298, 1), (299, 2))
        ],
    }]
    assert records["skill:request-reinforcements"]["facts"]["typeIds"] == [
        "tactical-phase-step",
    ]
    assert not records["skill:request-reinforcements"].get("armyLinks")
    assert all(
        record["id"] not in {"rule:reinforcements-extra", "skill:commlink",
                             "skill:request-reinforcements"}
        for _path, core in load_curated_directory(ROOT / "data/curated/rules")
        if core["collection"]["id"] == "n5-core-v5.3"
        for record in core["records"]
    )


def test_annex_read_model_is_discoverable_and_separate_from_core_matrix(tmp_path: Path) -> None:
    documents = load_curated_directory(ROOT / "data/curated/rules")
    output = tmp_path / "rules.db"
    export_rules_database(documents, output)
    rules = RulesDatabase(output)
    rules.validate()

    # The optional annex must survive a fresh current-format Rules export,
    # not only a historical v9 paired-publication promotion.
    published = RulesDatabase(ROOT / "data/generated/rules.db")
    assert rules.skill_reviewed_extra_semantics()["commlink"] == (
        published.skill_reviewed_extra_semantics()["commlink"]
    )
    for identity in ("rule:reinforcements-extra", "skill:commlink",
                     "skill:request-reinforcements"):
        fresh_record = rules.composed_record(identity)
        active_record = published.composed_record(identity)
        assert fresh_record is not None and active_record is not None
        assert fresh_record["summary"] == active_record["summary"]
        assert fresh_record["facts"] == active_record["facts"]

    army = Database(ROOT / "data/generated/infinity.db")

    general = RulesRecordCatalog(rules, "rules")
    assert any(item["slug"] == "reinforcements-extra" for item in general.list_items())
    entry = general.get_item("reinforcements-extra")
    assert entry is not None
    assert entry["rules"][0]["facts"]["category"] == "optional-extra"
    assert "N4" in entry["description"]

    skills = SkillCatalog(army, rules)
    for name in ("commlink", "request-reinforcements"):
        entry = skills.get_skill(name)
        assert entry is not None
        assert entry["rules"][0]["id"] == f"skill:{name}"
        assert "N4" in entry["rules"][0]["summary"]
    assert any(item["slug"] == "request-reinforcements" for item in skills.list_skills())
    request = rules.composed_record("skill:request-reinforcements")
    assert request is not None
    assert request["skill_types"][0]["id"] == "tactical-phase-step"
    # The core 57-row Orders/AROs projection is intentionally unchanged.
    from infinity_db.declaration_matrix import core_declaration_matrix

    matrix = core_declaration_matrix(army, rules)
    items = [item for section in matrix["sections"] for item in section["items"]]
    assert len(items) == 57
    assert not any(item["name"] == "Request Reinforcements" for item in items)


def test_every_published_reinforcement_profile_and_loadout_keeps_source_army() -> None:
    """Canonical Units must retain each Section's exact source profile/loadout rows."""
    from collections import defaultdict

    path = ROOT / "data/generated/infinity.db"
    profiles: dict[int, dict[int, set[tuple[int, str]]]] = defaultdict(
        lambda: defaultdict(set)
    )
    loadouts: dict[int, dict[int, set[tuple[object, ...]]]] = defaultdict(
        lambda: defaultdict(set)
    )
    with sqlite3.connect(path) as connection:
        for logical_id, army_id, group_id, name in connection.execute(
            "SELECT lus.logical_unit_id, aas.application_army_id, "
            "ppo.group_id, pp.name "
            "FROM profile_payload_occurrences AS ppo "
            "JOIN logical_unit_sources AS lus ON lus.source_unit_id = ppo.unit_id "
            "JOIN application_army_sources AS aas ON aas.source_army_id = ppo.army_id "
            "JOIN application_armies AS a ON a.id = aas.application_army_id "
            "AND a.role = 'reinforcement' "
            "JOIN profile_payloads AS pp ON pp.id = ppo.profile_payload_id"
        ):
            profiles[logical_id][army_id].add((group_id, name))
        for logical_id, army_id, group_id, option_id, name, points, swc in connection.execute(
            "SELECT lus.logical_unit_id, aas.application_army_id, "
            "lpo.group_id, lpo.option_id, lp.name, lpo.points, lpo.swc "
            "FROM loadout_payload_occurrences AS lpo "
            "JOIN logical_unit_sources AS lus ON lus.source_unit_id = lpo.unit_id "
            "JOIN application_army_sources AS aas ON aas.source_army_id = lpo.army_id "
            "JOIN application_armies AS a ON a.id = aas.application_army_id "
            "AND a.role = 'reinforcement' "
            "JOIN loadout_payloads AS lp ON lp.id = lpo.loadout_payload_id"
        ):
            loadouts[logical_id][army_id].add(
                (group_id, option_id, name, points, swc)
            )

    logical_ids = set(profiles) | set(loadouts)
    assert len(profiles) > 20, "No substantive published Reinforcement profile corpus"
    assert len(loadouts) > 20, "No substantive published Reinforcement loadout corpus"
    database = Database(path)
    compared_sections = 0
    for logical_id in sorted(logical_ids):
        unit = database.get_unit(logical_id)
        assert unit is not None, logical_id
        actual_profiles: dict[int, set[tuple[int, str]]] = defaultdict(set)
        actual_loadouts: dict[int, set[tuple[object, ...]]] = defaultdict(set)
        for army in unit["armies"]:
            if army["role"] != "reinforcement":
                continue
            if army["profiles"]:
                actual_profiles[army["id"]].update(
                    (item["group_id"], item["name"]) for item in army["profiles"]
                )
            if army["loadouts"]:
                actual_loadouts[army["id"]].update(
                    (item["group_id"], item["option_id"], item["name"],
                     item["points"], item["swc"])
                    for item in army["loadouts"]
                )
        expected_profiles = dict(profiles.get(logical_id, {}))
        expected_loadouts = dict(loadouts.get(logical_id, {}))
        assert dict(actual_profiles) == expected_profiles, (
            logical_id, unit["name"], actual_profiles, expected_profiles,
        )
        assert dict(actual_loadouts) == expected_loadouts, (
            logical_id, unit["name"], actual_loadouts, expected_loadouts,
        )
        compared_sections += len(set(expected_profiles) | set(expected_loadouts))
    assert compared_sections > 20


def test_commlink_source_extras_remain_on_their_exact_army_loadouts() -> None:
    """Source Commlink (+X) signatures must not leak across canonical Unit/Army rows."""
    from collections import Counter, defaultdict

    path = ROOT / "data/generated/infinity.db"
    # Include unqualified Commlink and preserve all extras belonging to each
    # source Skill occurrence. Source IDs are not inferred from display names.
    occurrences: dict[tuple[int, int, int, int, int], list[tuple[int, str]]] = defaultdict(
        list
    )
    with sqlite3.connect(path) as connection:
        for logical_id, army_id, group_id, option_id, position, extra_id, extra_name in (
            connection.execute(
                "SELECT lus.logical_unit_id, aas.application_army_id, "
                "lpo.group_id, lpo.option_id, s.position, e.extra_id, x.name "
                "FROM loadout_payload_occurrences AS lpo "
                "JOIN logical_unit_sources AS lus ON lus.source_unit_id = lpo.unit_id "
                "JOIN application_army_sources AS aas ON aas.source_army_id = lpo.army_id "
                "JOIN loadout_payload_skills AS s "
                "ON s.loadout_payload_id = lpo.loadout_payload_id AND s.item_id = 260 "
                "LEFT JOIN loadout_payload_skill_extras AS e "
                "ON e.loadout_payload_id = s.loadout_payload_id "
                "AND e.occurrence_position = s.position "
                "LEFT JOIN extras AS x ON x.id = e.extra_id "
                "ORDER BY lus.logical_unit_id, aas.application_army_id, "
                "lpo.group_id, lpo.option_id, s.position, e.position"
            )
        ):
            key = (logical_id, army_id, group_id, option_id, position)
            occurrences.setdefault(key, [])
            if extra_id is not None:
                occurrences[key].append((extra_id, extra_name))

    assert occurrences, "No source-backed Commlink occurrences"
    expected: dict[tuple[int, int, int, int], set[tuple[tuple[int, str], ...]]] = (
        defaultdict(set)
    )
    signatures: Counter[tuple[tuple[int, str], ...]] = Counter()
    for (logical_id, army_id, group_id, option_id, _position), extras in occurrences.items():
        signature = tuple(extras)
        expected[(logical_id, army_id, group_id, option_id)].add(signature)
        signatures[signature] += 1
    assert signatures[((298, "+1"),)] > 0
    assert signatures[((299, "+2"),)] > 0
    assert signatures[()] > 0
    assert set(signatures) == {(), ((298, "+1"),), ((299, "+2"),)}

    actual: dict[tuple[int, int, int, int], set[tuple[tuple[int, str], ...]]] = (
        defaultdict(set)
    )
    database = Database(path)
    for logical_id in sorted({key[0] for key in expected}):
        unit = database.get_unit(logical_id)
        assert unit is not None
        for army in unit["armies"]:
            for loadout in army["loadouts"]:
                key = (logical_id, army["id"], loadout["group_id"], loadout["option_id"])
                for skill in loadout["skills"]:
                    if skill["id"] != 260:
                        continue
                    actual[key].add(tuple(
                        (extra["id"], extra["name"]) for extra in skill.get("extras", [])
                    ))
    assert dict(actual) == dict(expected), (
        "Commlink source variant leak or missing exact loadout",
        [
            (key, actual.get(key), expected.get(key))
            for key in sorted(set(actual) | set(expected))
            if actual.get(key) != expected.get(key)
        ][:20],
    )
