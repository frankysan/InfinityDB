"""Source-backed Unit Explorer matching scopes and prospective counts."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from infinity_db.database import Database
from infinity_db.database.unit_filter_matching import MatchContext, evaluate


def context(
    unit: int, army: int, group: int, option: int, profile: int | None,
    *skills: int,
) -> MatchContext:
    return MatchContext(
        unit, unit, army, group, option, profile,
        frozenset(("skills", value) for value in skills),
    )


def matches(contexts: list[MatchContext], selected: tuple[int, ...], scope: str):
    chosen = {"skills": tuple(frozenset({("skills", value)}) for value in selected)}
    return evaluate(contexts, chosen, frozenset({"skills"}), scope)


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        ("one-profile", (True, True, True)),
        ("alternative-profiles", (False, True, True)),
        ("mutually-exclusive-loadouts", (False, False, True)),
        ("main-and-included-peripheral", (False, True, True)),
        ("controller-target-only", (False, False, False)),
        ("multiple-included-peripherals", (False, True, True)),
        ("transmutation-states", (False, True, True)),
        ("ambiguous-edge", (False, False, False)),
        ("different-logical-units", (False, False, False)),
    ],
)
def test_scope_fixture_matrix(fixture: str, expected: tuple[bool, bool, bool]) -> None:
    profile: list[MatchContext] = []
    loadout: list[MatchContext] = []
    unit: list[MatchContext] = []
    if fixture == "one-profile":
        profile = [context(1, 10, 1, 100, 1, 1, 2)]
        loadout = [context(1, 10, 1, 100, None, 1, 2)]
        unit = loadout
    elif fixture in {"alternative-profiles", "transmutation-states"}:
        profile = [context(1, 10, 1, 100, 1, 1), context(1, 10, 1, 100, 2, 2)]
        loadout = [context(1, 10, 1, 100, None, 1, 2)]
        unit = loadout
    elif fixture == "mutually-exclusive-loadouts":
        profile = [context(1, 10, 1, 100, 1, 1), context(1, 10, 1, 101, 1, 2)]
        loadout = [context(1, 10, 1, 100, None, 1), context(1, 10, 1, 101, None, 2)]
        unit = loadout
    elif fixture in {"main-and-included-peripheral", "multiple-included-peripherals"}:
        profile = [context(1, 10, 1, 100, 1, 1)]
        extra = (3,) if fixture.endswith("peripherals") else ()
        loadout = [context(1, 10, 1, 100, None, 1, 2, *extra)]
        unit = loadout
    elif fixture == "different-logical-units":
        profile = [context(1, 10, 1, 100, 1, 1), context(2, 10, 1, 100, 1, 2)]
        loadout = profile
        unit = profile
    else:
        # A merely available Controller target or ambiguous Include never
        # acquires the target's properties.
        profile = [context(1, 10, 1, 100, 1, 1)]
        loadout = profile
        unit = profile
    for scope, candidates, outcome in zip(
        ("profile", "loadout", "unit"), (profile, loadout, unit), expected,
        strict=True,
    ):
        found, _counts = matches(candidates, (1, 2), scope)
        assert bool(found.get(1)) is outcome


def test_anywhere_unit_merges_reviewed_source_representations_but_not_other_units() -> None:
    representations = [
        context(1, 101, 1, 100, None, 1),
        context(1, 201, 1, 100, None, 2),
        context(2, 101, 1, 100, None, 1),
    ]
    assert set(matches(representations, (1, 2), "unit")[0]) == {1}
    assert matches(representations, (1, 2), "loadout")[0] == {}


def test_prospective_counts_match_reselection_and_deduplicate() -> None:
    candidates = [
        context(1, 101, 1, 100, None, 1, 2),
        context(1, 201, 1, 100, None, 1, 2),
        context(2, 101, 1, 100, None, 1),
        context(3, 101, 1, 100, None, 2),
    ]
    for scope in ("profile", "loadout", "unit"):
        for and_modes in (frozenset({"skills"}), frozenset()):
            selected = {"skills": (frozenset({("skills", 1)}),)}
            current, counts = evaluate(candidates, selected, and_modes, scope)
            added, _ = evaluate(
                candidates,
                {"skills": selected["skills"] + (frozenset({("skills", 2)}),)},
                and_modes, scope,
            )
            expected = counts["skills"].get("2", 0)
            expected += counts["skills"].get("__or_base__", 0)
            assert expected == len(added)
            assert len(current) == 2


def test_materialized_profile_loadout_include_and_peripheral_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "scoped-occurrences.db"
    with sqlite3.connect(path) as connection:
        connection.executescript("""
            CREATE TABLE __infinity_metadata (key TEXT, value TEXT);
            CREATE TABLE logical_unit_sources (source_unit_id INTEGER, logical_unit_id INTEGER);
            CREATE TABLE application_catalog_sources (
                catalog TEXT, source_item_id INTEGER, application_item_id INTEGER
            );
            CREATE TABLE profile_payload_occurrences (
                army_id INTEGER, unit_id INTEGER, group_id INTEGER, profile_id INTEGER,
                profile_payload_id INTEGER, ava INTEGER
            );
            CREATE TABLE loadout_payload_occurrences (
                army_id INTEGER, unit_id INTEGER, group_id INTEGER, option_id INTEGER,
                loadout_payload_id INTEGER, points INTEGER, swc TEXT
            );
            CREATE TABLE profile_payloads (id INTEGER, type_id INTEGER);
            CREATE TABLE profile_groups (
                army_id INTEGER, unit_id INTEGER, group_id INTEGER, category_id INTEGER
            );
            CREATE TABLE profile_payload_skills (
                profile_payload_id INTEGER, item_id INTEGER
            );
            CREATE TABLE loadout_payload_skills (
                loadout_payload_id INTEGER, item_id INTEGER
            );
            CREATE TABLE profile_payload_equipment (
                profile_payload_id INTEGER, item_id INTEGER
            );
            CREATE TABLE loadout_payload_equipment (
                loadout_payload_id INTEGER, item_id INTEGER
            );
            CREATE TABLE profile_payload_weapons (
                profile_payload_id INTEGER, item_id INTEGER
            );
            CREATE TABLE loadout_payload_weapons (
                loadout_payload_id INTEGER, item_id INTEGER
            );
            CREATE TABLE profile_payload_characteristics (
                profile_payload_id INTEGER, characteristic_id INTEGER
            );
            CREATE TABLE loadout_payload_characteristics (
                loadout_payload_id INTEGER, characteristic_id INTEGER
            );
            CREATE TABLE profile_occurrence_includes (
                army_id INTEGER, unit_id INTEGER, group_id INTEGER, profile_id INTEGER,
                target_loadout_payload_id INTEGER
            );
            CREATE TABLE loadout_occurrence_includes (
                army_id INTEGER, unit_id INTEGER, group_id INTEGER, option_id INTEGER,
                target_loadout_payload_id INTEGER
            );
            CREATE TABLE unit_option_include_targets (
                unit_id INTEGER, option_id INTEGER, target_army_id INTEGER,
                target_loadout_payload_id INTEGER
            );
            CREATE TABLE unit_option_skills (unit_id INTEGER, item_id INTEGER);
            CREATE TABLE unit_option_equipment (unit_id INTEGER, item_id INTEGER);
            CREATE TABLE unit_option_weapons (unit_id INTEGER, item_id INTEGER);
            CREATE TABLE application_peripheral_controller_targets (
                access_id INTEGER, target_logical_unit_id INTEGER
            );
            INSERT INTO logical_unit_sources VALUES (1,1),(2,2),(3,1);
            INSERT INTO application_peripheral_controller_targets VALUES (1,2);
            INSERT INTO profile_groups VALUES
                (101,1,1,9),(101,1,2,9),(101,1,3,9),(101,2,1,9),
                (201,3,1,9);
            INSERT INTO profile_payloads VALUES
                (10,7),(20,7),(30,7),(40,7),(50,7),(60,7);
            INSERT INTO profile_payload_occurrences VALUES
                (101,1,1,1,10,1),(101,1,1,2,20,1),
                (101,1,2,3,30,1),(101,1,3,4,40,1),
                (101,2,1,5,50,1),(201,3,1,6,60,1);
            INSERT INTO profile_payload_skills VALUES
                (10,11),(20,12),(30,14),(40,15),(50,17),(60,18);
            INSERT INTO loadout_payload_occurrences VALUES
                (101,1,1,100,100,10,'0'),(101,1,1,101,101,20,'0'),
                (101,1,2,200,200,10,'0'),(101,1,3,300,300,10,'0'),
                (101,2,1,500,500,10,'0'),(201,3,1,600,600,10,'0');
            INSERT INTO loadout_payload_skills VALUES (100,13),(101,19);
            INSERT INTO profile_occurrence_includes VALUES (101,1,1,1,300);
            INSERT INTO loadout_occurrence_includes VALUES (101,1,1,100,200);
            INSERT INTO unit_option_skills VALUES (1,16);
            INSERT INTO unit_option_include_targets VALUES (1,99,101,300);
        """)
        connection.executemany(
            "INSERT INTO application_catalog_sources VALUES ('skills', ?, ?)",
            [(item, item) for item in range(11, 20)],
        )

    # The curated Controller target pool is present but is NOT an attachment.
    def scoped_index() -> dict[str, tuple[MatchContext, ...]]:
        database = Database(path)
        monkeypatch.setattr(
            database, "list_unit_filter_values",
            lambda: {"classifications": [{"id": 9, "slug": "regular"}]},
        )
        monkeypatch.setattr(
            database, "_classification_filter_source_ids",
            lambda _ref: (9,),
        )
        return database._scoped_unit_filter_contexts()

    index = scoped_index()
    profile = [
        candidate for candidate in index["profile"]
        if candidate.source_unit_id == 1 and candidate.group_id == 1
        and candidate.option_id == 100
    ]
    assert len(profile) == 2
    assert not any(
        {("skills", 11), ("skills", 12)} <= candidate.properties
        for candidate in profile
    )
    loadout = next(
        candidate for candidate in index["loadout"]
        if candidate.source_unit_id == 1 and candidate.group_id == 1
        and candidate.option_id == 100
    )
    assert {("skills", value) for value in (11, 12, 13, 14, 15)} <= loadout.properties
    assert ("skills", 19) not in loadout.properties
    assert ("skills", 16) not in loadout.properties

    unit_contexts = [
        candidate for candidate in index["unit"] if candidate.logical_id == 1
    ]
    logical_skills = frozenset().union(
        *(candidate.properties for candidate in unit_contexts)
    )
    assert {("skills", value) for value in (11, 13, 14, 15, 16, 18, 19)} <= logical_skills
    assert ("skills", 17) not in logical_skills

    for scope, skill_pair, expected in (
        ("profile", (11, 12), False),
        ("loadout", (11, 12), True),
        ("loadout", (13, 19), False),
        ("unit", (13, 19), True),
        ("profile", (11, 14), False),
        ("loadout", (11, 14), True),
        ("unit", (11, 18), True),
        ("unit", (11, 17), False),
    ):
        result, _ = matches(list(index[scope]), skill_pair, scope)
        assert bool(result.get(1)) is expected, (scope, skill_pair)

    # Reused target payloads with two possible same-source occurrences are
    # ambiguous and must not silently pull the target's Skills into the parent.
    with sqlite3.connect(path) as connection:
        connection.execute("INSERT INTO profile_groups VALUES (101,1,4,9)")
        connection.execute(
            "INSERT INTO profile_payload_occurrences VALUES (101,1,4,7,10,1)"
        )
        connection.execute(
            "INSERT INTO loadout_payload_occurrences VALUES (101,1,4,400,200,10,'0')"
        )
    ambiguous = scoped_index()
    parent = next(
        candidate for candidate in ambiguous["loadout"]
        if candidate.source_unit_id == 1 and candidate.group_id == 1
        and candidate.option_id == 100
    )
    assert ("skills", 14) not in parent.properties
    assert ("skills", 15) in parent.properties


def test_scope_without_categorical_selections_preserves_unit_population() -> None:
    database = Database(Path("data/generated/army.db"))
    baseline = database.list_units(limit=1)["total"]
    for scope in ("profile", "loadout", "unit"):
        assert database.list_units(
            matching_scope=scope, limit=1,
        )["total"] == baseline


def test_scoped_api_counts_berserk_engineer_reproduction() -> None:
    database = Database(Path("data/generated/army.db"))
    for scope in ("profile", "loadout", "unit"):
        params = {
            "skill_id": "berserk",
            "and_filters": ("skill",),
            "matching_scope": scope,
        }
        result = database.list_units(**params, include_usage_counts=True)
        assert "prospective_counts" in result
        engineer_id = database.application_catalog_id("skills", "engineer")
        assert engineer_id is not None
        predicted = result["prospective_counts"]["skills"][str(engineer_id)]
        actual = database.list_units(
            **{**params, "skill_id": ("berserk", "engineer")},
        )["total"]
        assert predicted == actual
        berserk_id = database.application_catalog_id("skills", "berserk")
        assert result["prospective_counts"]["skills"][str(berserk_id)] == result["total"]


def test_new_scope_validated_and_legacy_remains_optional() -> None:
    from infinity_db.web.api_handler import _unit_query

    assert _unit_query("skill_id=berserk")["matching_scope"] is None
    assert _unit_query("matching_scope=profile")["matching_scope"] == "profile"
    assert _unit_query("matching_scope=loadout")["matching_scope"] == "loadout"
    assert _unit_query("matching_scope=unit")["matching_scope"] == "unit"
    with pytest.raises(ValueError, match="scope"):
        _unit_query("matching_scope=invalid")
    with pytest.raises(ValueError, match="scope"):
        Database(Path("data/generated/army.db")).list_units(matching_scope="invalid")


def test_scoped_results_name_only_supported_matching_configurations() -> None:
    database = Database(Path("data/generated/army.db"))
    for scope in ("profile", "loadout"):
        result = database.list_units(
            skill_id="berserk", matching_scope=scope, limit=25,
        )
        assert result["items"]
        named = [item["matching_contexts"] for item in result["items"]
                 if "matching_contexts" in item]
        assert named
        for evidence in named:
            assert evidence["total"] >= len(evidence["examples"]) >= 1
            assert len(evidence["examples"]) <= 5
            for label in evidence["examples"]:
                assert label["army_name"]
                if scope == "profile":
                    assert label["profile_name"]
                else:
                    assert label["loadout_name"]
    for scope in ("unit", None):
        result = database.list_units(skill_id="berserk", matching_scope=scope, limit=5)
        assert all("matching_contexts" not in item for item in result["items"])
    without_filters = database.list_units(matching_scope="profile", limit=5)
    assert all("matching_contexts" not in item for item in without_filters["items"])
