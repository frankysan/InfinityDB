"""Reviewed deployed-object source parity and embedded-model integrity."""

from __future__ import annotations

import copy
import json
import shutil
import sqlite3
from collections import Counter
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_directory
from infinity_db.deployed_object_builder import build_deployed_objects
from infinity_db.deployed_object_storage import stage_deployed_objects
from infinity_db.rules_database import RulesDatabase, export_rules_database


@pytest.fixture(scope="module")
def source_paths() -> tuple[Path, Path, Path, Path, Path]:
    root = Path(__file__).resolve().parents[1]
    files = (
        root / "data/generated/army.db",
        root / "data/generated/rules_n5.db",
        root / "data/curated/rules/n5-core-v5.3.json",
        root / "config/validation/deployed-object-delivery-reviews.json",
        root / "config/validation/deployed-object-candidate-reviews.json",
    )
    if not all(path.is_file() for path in files):
        pytest.skip("Pinned release source inputs unavailable")
    return files


@pytest.fixture(scope="module")
def legacy_v9_rules(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """An older reference DB must never activate a loose deployed-object publication."""
    root = Path(__file__).resolve().parents[1]
    output = tmp_path_factory.mktemp("deployed-v9-compatibility") / "rules_n5.db"
    export_rules_database(
        load_curated_directory(root / "data/curated/rules"), output,
        restrictions_manifest=json.loads(
            (root / "config/validation/restrictions-source-chart.json").read_text(encoding="utf-8")
        ),
    )
    with sqlite3.connect(output) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 9
    return output


def test_pinned_publication_is_deterministic_and_source_complete(
    source_paths: tuple[Path, Path, Path, Path, Path],
) -> None:
    publication = build_deployed_objects(source_paths[0], *source_paths[2:])
    assert publication == build_deployed_objects(source_paths[0], *source_paths[2:])
    assert len(publication["objects"]) == 17
    assert len(publication["unresolvedDeliveries"]) == 1
    rules = RulesDatabase(source_paths[1])
    rules.validate()
    assert rules.deployed_objects_payload(source_paths[0]) == publication


def test_named_mines_use_only_their_exact_army_source_subtype(
    source_paths: tuple[Path, Path, Path, Path, Path],
) -> None:
    publication = build_deployed_objects(source_paths[0], *source_paths[2:])
    by_name = {obj["name"]: obj for obj in publication["objects"]}
    for name in (
        "AP Mine", "E/M Mine", "Monofilament Mine",
        "PARA Mine", "Shock Mine", "Viral Mine",
    ):
        obj = by_name[name]
        profile = obj["sourceProfile"]
        assert profile is not None and profile["catalog"] == "weapon"
        assert profile["name"] == name and profile["mode"] is None
        slug = obj["originRuleId"] or next(
            edge["recordId"] for edge in obj["deliverySources"]
        )
        assert obj["originRuleId"] is None
        assert {edge["recordId"] for edge in obj["deliverySources"]} == {slug}
        assert {edge["method"] for edge in obj["deliverySources"]} == {
            "Place Deployable Skill",
            "Intuitive Attack WIP Roll for Camouflage Marker exception",
        }
        assert obj["attributes"]["S"]["status"] == "disputed"
        for use in obj["unitUses"]:
            assert use["originRecordId"] == slug
            assert use["sourceItemId"] == profile["sourceId"], (name, use)
    assert publication["unresolvedDeliveries"] == [{
        "originRecordId": "weapon:mine-dispenser",
        "delivery": "successful BS Attack shot",
        "reason": "source-object-not-resolved",
    }]


def test_reviewed_delivery_uses_have_complete_source_context(
    source_paths: tuple[Path, Path, Path, Path, Path],
) -> None:
    publication = build_deployed_objects(source_paths[0], *source_paths[2:])
    for obj in publication["objects"]:
        for use in obj["unitUses"]:
            required_numbers = ("unitId", "sourceItemId", "sourcePosition")
            required_names = ("unitName", "unitSlug", "contextName")
            assert all(type(use.get(key)) is int for key in required_numbers), (
                obj["name"], use
            )
            for key in required_names:
                assert isinstance(use.get(key), str) and use[key], (
                    obj["name"], key, repr(use.get(key)), use["kind"], use["unitId"],
                )


def test_missing_source_unit_names_use_normalized_logical_identity(
    source_paths: tuple[Path, Path, Path, Path, Path],
) -> None:
    publication = build_deployed_objects(source_paths[0], *source_paths[2:])
    found_missing_name = False
    with sqlite3.connect(source_paths[0]) as db:
        for obj in publication["objects"]:
            for use in obj["unitUses"]:
                source = db.execute(
                    "SELECT u.name, lu.name FROM units AS u "
                    "JOIN logical_unit_sources AS lus ON lus.source_unit_id = u.id "
                    "JOIN logical_units AS lu ON lu.id = lus.logical_unit_id "
                    "WHERE u.id = ?",
                    (use["unitId"],),
                ).fetchone()
                assert source is not None
                original_name, logical_name = source
                expected = original_name or logical_name
                assert use["unitName"] == expected, (obj["name"], use["unitId"])
                if not original_name:
                    found_missing_name = True
    assert found_missing_name, "Pinned source has no missing Unit name to verify"


def test_reviewed_delivery_uses_are_exact_army_occurrences_only(
    source_paths: tuple[Path, Path, Path, Path, Path],
) -> None:
    publication = build_deployed_objects(source_paths[0], *source_paths[2:])
    uses_count = 0
    with sqlite3.connect(source_paths[0]) as db:
        for obj in publication["objects"]:
            reviewed = {
                (edge["recordId"], edge["method"])
                for edge in obj["deliverySources"]
            }
            if not reviewed:
                assert obj["unitUses"] == [], obj["name"]
            for use in obj["unitUses"]:
                uses_count += 1
                assert (use["originRecordId"], use["method"]) in reviewed
                assert use["kind"] in {
                    "profile", "loadout", "unit-option",
                    "profile-include", "loadout-include", "unit-option-include",
                }
                assert use["unitSlug"]
                item_catalog = (
                    "weapons" if use["originRecordId"].startswith("weapon:") else "equipment"
                )
                if use["kind"] in {"unit-option", "unit-option-include"}:
                    assert use["armyId"] is None and use["groupId"] is None
                    assert use["armyName"] is None and use["profileId"] is None
                    if use["kind"] == "unit-option-include":
                        matches = db.execute(
                            "SELECT COUNT(*) FROM unit_option_include_targets AS i "
                            f"JOIN loadout_payload_{item_catalog} AS p "
                            "ON p.loadout_payload_id = i.target_loadout_payload_id "
                            "WHERE i.unit_id = ? AND i.option_id = ? "
                            "AND i.position = ? AND i.target_army_id = ? "
                            "AND i.target_loadout_payload_id = ? "
                            "AND p.item_id = ? AND p.position = ?",
                            (use["unitId"], use["optionId"], use["includePosition"],
                             use["targetArmyId"], use["targetLoadoutPayloadId"],
                             use["sourceItemId"], use["sourcePosition"]),
                        ).fetchone()[0]
                    else:
                        matches = db.execute(
                            f"SELECT COUNT(*) FROM unit_option_{item_catalog} "
                            "WHERE unit_id = ? AND option_id = ? "
                            "AND item_id = ? AND position = ?",
                            (use["unitId"], use["optionId"],
                             use["sourceItemId"], use["sourcePosition"]),
                        ).fetchone()[0]
                else:
                    assert use["armyName"]
                    kind = use["kind"].removesuffix("-include")
                    identity = "profileId" if kind == "profile" else "optionId"
                    other = "optionId" if kind == "profile" else "profileId"
                    assert use[identity] is not None and use[other] is None
                    if use["kind"].endswith("-include"):
                        identity_snake = "profile_id" if kind == "profile" else "option_id"
                        matches = db.execute(
                            f"SELECT COUNT(*) FROM {kind}_occurrence_includes AS i "
                            f"JOIN loadout_payload_{item_catalog} AS p "
                            "ON p.loadout_payload_id = i.target_loadout_payload_id "
                            f"WHERE i.army_id = ? AND i.unit_id = ? "
                            "AND i.group_id = ? "
                            f"AND i.{identity_snake} = ? "
                            "AND i.position = ? AND i.target_loadout_payload_id = ? "
                            "AND p.item_id = ? AND p.position = ?",
                            (use["armyId"], use["unitId"], use["groupId"],
                             use[identity], use["includePosition"],
                             use["targetLoadoutPayloadId"],
                             use["sourceItemId"], use["sourcePosition"]),
                        ).fetchone()[0]
                    else:
                        matches = db.execute(
                            f"SELECT COUNT(*) FROM {kind}_payload_occurrences AS o "
                            f"JOIN {kind}_payload_{item_catalog} AS p "
                            f"ON p.{kind}_payload_id = o.{kind}_payload_id "
                            f"WHERE o.army_id = ? AND o.unit_id = ? AND o.group_id = ? "
                            f"AND o.{'profile_id' if kind == 'profile' else 'option_id'} = ? "
                            "AND p.item_id = ? AND p.position = ?",
                            (use["armyId"], use["unitId"], use["groupId"],
                             use[identity], use["sourceItemId"], use["sourcePosition"]),
                        ).fetchone()[0]
                assert matches == 1, use
    assert uses_count > 0
    assert any(
        use["kind"] in {"profile-include", "loadout-include"}
        for obj in publication["objects"] for use in obj["unitUses"]
    )
    assert any(
        use["kind"] == "unit-option-include"
        for obj in publication["objects"] for use in obj["unitUses"]
    )
    # Reviewed source use does not resolve Mine Dispenser subtype or invent
    # ownership for curated objects without a reviewed delivery edge.
    assert publication["unresolvedDeliveries"][0]["originRecordId"] == (
        "weapon:mine-dispenser"
    )


def test_reviewed_direct_uses_cover_every_matching_raw_source_occurrence(
    source_paths: tuple[Path, Path, Path, Path, Path],
) -> None:
    """Check the reverse direction: source rows must not disappear from publication."""
    from infinity_db.database import raw_database_path
    from infinity_db.deployed_object_usage import _source_ids

    raw_path = raw_database_path(source_paths[0])
    if not raw_path.is_file():
        pytest.skip("Ignored raw Army database is unavailable in clean CI")
    publication = build_deployed_objects(source_paths[0], *source_paths[2:])
    observed_kinds: set[str] = set()
    with (
        sqlite3.connect(f"{source_paths[0].resolve().as_uri()}?mode=ro", uri=True) as db,
        sqlite3.connect(f"{raw_path.resolve().as_uri()}?mode=ro", uri=True) as raw,
    ):
        db.row_factory = sqlite3.Row
        raw.row_factory = sqlite3.Row
        for obj in publication["objects"]:
            for edge in obj["deliverySources"]:
                record_id = edge["recordId"]
                method = edge["method"]
                catalog = "weapons" if record_id.startswith("weapon:") else "equipment"
                source_ids = _source_ids(db, record_id)
                placeholders = ",".join("?" for _ in source_ids)
                expected: Counter[tuple] = Counter()
                for kind, table in (
                    ("profile", f"profile_{catalog}"),
                    ("loadout", f"option_{catalog}"),
                    ("unit-option", f"unit_option_{catalog}"),
                ):
                    army = "NULL" if kind == "unit-option" else "o.army_id"
                    group = "NULL" if kind == "unit-option" else "o.group_id"
                    profile = "o.profile_id" if kind == "profile" else "NULL"
                    option = "NULL" if kind == "profile" else "o.option_id"
                    if table == "option_weapons":
                        item_source = "JOIN option_weapon_templates AS t ON t.id = o.template_id"
                        item_id = "t.item_id"
                    else:
                        item_source = ""
                        item_id = "o.item_id"
                    query = (
                        f"SELECT {army} AS army_id, o.unit_id, {group} AS group_id, "
                        f"{profile} AS profile_id, {option} AS option_id, "
                        f"{item_id} AS item_id, o.position FROM {table} AS o "
                        f"{item_source} WHERE {item_id} IN ({placeholders})"
                    )
                    for row in raw.execute(query, source_ids):
                        expected[(
                            kind, row["army_id"], row["unit_id"], row["group_id"],
                            row["profile_id"], row["option_id"], row["item_id"], row["position"],
                        )] += 1
                actual: Counter[tuple] = Counter(
                    (
                        use["kind"], use["armyId"], use["unitId"], use["groupId"],
                        use["profileId"], use["optionId"], use["sourceItemId"],
                        use["sourcePosition"],
                    )
                    for use in obj["unitUses"]
                    if use["originRecordId"] == record_id
                    and use["method"] == method
                    and use["kind"] in {"profile", "loadout", "unit-option"}
                )
                observed_kinds.update(kind for kind, *_ in actual)
                assert actual == expected, (
                    obj["name"], record_id, method,
                    "unexpected", actual - expected, "missing", expected - actual,
                )
    assert {"profile", "loadout"} <= observed_kinds


def test_reviewed_include_uses_cover_matching_raw_target_loadouts(
    source_paths: tuple[Path, Path, Path, Path, Path],
) -> None:
    """Compare every resolved one-level Include with its source target option."""
    from infinity_db.database import raw_database_path
    from infinity_db.deployed_object_usage import _source_ids

    raw_path = raw_database_path(source_paths[0])
    if not raw_path.is_file():
        pytest.skip("Ignored raw Army database is unavailable in clean CI")
    publication = build_deployed_objects(source_paths[0], *source_paths[2:])
    observed_kinds: set[str] = set()
    with (
        sqlite3.connect(f"{source_paths[0].resolve().as_uri()}?mode=ro", uri=True) as db,
        sqlite3.connect(f"{raw_path.resolve().as_uri()}?mode=ro", uri=True) as raw,
    ):
        db.row_factory = sqlite3.Row
        raw.row_factory = sqlite3.Row
        raw.execute("ATTACH DATABASE ? AS published", (
            f"{source_paths[0].resolve().as_uri()}?mode=ro",
        ))
        for obj in publication["objects"]:
            for edge in obj["deliverySources"]:
                record_id = edge["recordId"]
                method = edge["method"]
                catalog = "weapons" if record_id.startswith("weapon:") else "equipment"
                source_ids = _source_ids(db, record_id)
                placeholders = ",".join("?" for _ in source_ids)
                item_table = f"option_{catalog}"
                if catalog == "weapons":
                    template_join = "JOIN option_weapon_templates AS t ON t.id = o.template_id "
                    item_id = "t.item_id"
                else:
                    template_join = ""
                    item_id = "o.item_id"
                expected: Counter[tuple] = Counter()
                for kind, source_table, identity in (
                    ("profile-include", "profile_includes", "profile_id"),
                    ("loadout-include", "option_includes", "option_id"),
                ):
                    query = (
                        f"SELECT i.army_id, i.unit_id, i.group_id, i.{identity} AS identity_id, "
                        "i.position AS include_position, "
                        f"{item_id} AS item_id, o.position AS source_position "
                        f"FROM {source_table} AS i JOIN {item_table} AS o "
                        "ON o.army_id = i.army_id AND o.unit_id = i.unit_id "
                        "AND o.group_id = i.target_group_id "
                        "AND o.option_id = i.target_option_id "
                        f"{template_join}WHERE {item_id} IN ({placeholders})"
                    )
                    for row in raw.execute(query, source_ids):
                        expected[(
                            kind, row["army_id"], row["unit_id"], row["group_id"],
                            row["identity_id"], row["include_position"],
                            None, row["item_id"], row["source_position"],
                        )] += 1
                query = (
                    "SELECT i.unit_id, i.option_id AS identity_id, "
                    "i.position AS include_position, target.target_army_id, "
                    f"{item_id} AS item_id, o.position AS source_position "
                    "FROM published.unit_option_include_targets AS target "
                    "JOIN unit_option_includes AS i "
                    "ON i.unit_id = target.unit_id AND i.option_id = target.option_id "
                    "AND i.position = target.position "
                    f"JOIN {item_table} AS o "
                    "ON o.army_id = target.target_army_id AND o.unit_id = i.unit_id "
                    "AND o.group_id = i.target_group_id "
                    "AND o.option_id = i.target_option_id "
                    f"{template_join}WHERE {item_id} IN ({placeholders})"
                )
                for row in raw.execute(query, source_ids):
                    expected[(
                        "unit-option-include", None, row["unit_id"], None,
                        row["identity_id"], row["include_position"],
                        row["target_army_id"], row["item_id"], row["source_position"],
                    )] += 1
                actual: Counter[tuple] = Counter(
                    (
                        use["kind"], use["armyId"], use["unitId"], use["groupId"],
                        use["profileId"] if use["kind"] == "profile-include" else use["optionId"],
                        use["includePosition"], use.get("targetArmyId"),
                        use["sourceItemId"], use["sourcePosition"],
                    )
                    for use in obj["unitUses"]
                    if use["originRecordId"] == record_id
                    and use["method"] == method
                    and use["kind"] in {
                        "profile-include", "loadout-include", "unit-option-include",
                    }
                )
                observed_kinds.update(kind for kind, *_ in actual)
                assert actual == expected, (
                    obj["name"], record_id, method,
                    "unexpected", actual - expected, "missing", expected - actual,
                )
    # No reviewed delivery source is reached through profile Includes in this snapshot;
    # their source rows are still checked above if a later snapshot adds one.
    assert {"loadout-include", "unit-option-include"} <= observed_kinds


def test_unit_wide_occurrence_preserves_missing_army_context(
    source_paths: tuple[Path, Path, Path, Path, Path], tmp_path: Path,
) -> None:
    from infinity_db.deployed_object_usage import _occurrences, _source_ids

    database_path = tmp_path / "unit-options.db"
    shutil.copyfile(source_paths[0], database_path)
    with sqlite3.connect(database_path) as db:
        db.row_factory = sqlite3.Row
        source_id = _source_ids(db, "weapon:pitcher")[0]
        unit_id = db.execute("SELECT id FROM units ORDER BY id LIMIT 1").fetchone()[0]
        option_id = db.execute(
            "SELECT COALESCE(MAX(option_id), 0) + 1 FROM unit_options WHERE unit_id = ?",
            (unit_id,),
        ).fetchone()[0]
        occurrence_id = db.execute(
            "SELECT COALESCE(MAX(occurrence_id), 0) + 1 FROM unit_option_weapons"
        ).fetchone()[0]
        db.execute(
            "INSERT INTO unit_options (unit_id, option_id, position, name) "
            "VALUES (?, ?, 100, 'Synthetic source-wide option')",
            (unit_id, option_id),
        )
        db.execute(
            "INSERT INTO unit_option_weapons "
            "(occurrence_id, unit_id, option_id, position, item_id) "
            "VALUES (?, ?, ?, 100, ?)",
            (occurrence_id, unit_id, option_id, source_id),
        )
        uses = _occurrences(db, "weapons", (source_id,))
        match = [
            use for use in uses if use["kind"] == "unit-option"
            and use["unitId"] == unit_id and use["optionId"] == option_id
        ]
        assert len(match) == 1
        assert match[0]["armyId"] is None
        assert match[0]["armyName"] is None
        assert match[0]["groupId"] is None
        assert match[0]["sourceItemId"] == source_id


def test_embedded_model_rejects_identity_value_and_delivery_tampering(
    source_paths: tuple[Path, Path, Path, Path, Path],
) -> None:
    original = build_deployed_objects(source_paths[0], *source_paths[2:])

    def rejected(document: dict, message: str) -> None:
        with sqlite3.connect(":memory:") as connection:
            with pytest.raises(ValueError, match=message):
                stage_deployed_objects(connection, document)
            assert connection.execute("SELECT name FROM sqlite_master").fetchall() == []

    changed = copy.deepcopy(original)
    changed["objects"].append(copy.deepcopy(changed["objects"][0]))
    rejected(changed, "duplicate deployed-object identity")

    changed = copy.deepcopy(original)
    changed["objects"][0]["attributes"]["S"] = {
        "status": "unreported", "value": "0", "provenance": [],
    }
    rejected(changed, "cannot invent a value")

    changed = copy.deepcopy(original)
    disputed = next(
        row for row in changed["objects"] if row["attributes"]["S"]["status"] == "disputed"
    )
    disputed["attributes"]["S"]["provenance"] = []
    rejected(changed, "missing source provenance")

    changed = copy.deepcopy(original)
    changed["objects"][0]["deliverySources"] = [{"recordId": "weapon:pitcher"}]
    rejected(changed, "reviewed delivery edge")

    changed = copy.deepcopy(original)
    changed["objects"][0].pop("unitUses")
    rejected(changed, "Missing or invalid deployed-object Unit usage collection")

    changed = copy.deepcopy(original)
    with_uses = next(obj for obj in changed["objects"] if obj["unitUses"])
    with_uses["unitUses"][0]["originRecordId"] = "weapon:mine-dispenser"
    rejected(changed, "unreviewed deployed-object Unit usage")

    changed = copy.deepcopy(original)
    direct = next(
        use for obj in changed["objects"] for use in obj["unitUses"]
        if use["kind"] in {"profile", "loadout"}
    )
    if direct["kind"] == "profile":
        direct["optionId"] = 1
    else:
        direct["profileId"] = 1
    rejected(changed, "profile/loadout usage context")

    changed = copy.deepcopy(original)
    included = next(
        use for obj in changed["objects"] for use in obj["unitUses"]
        if use["kind"].endswith("-include")
    )
    included["targetLoadoutPayloadId"] = None
    rejected(changed, "Include")

    changed = copy.deepcopy(original)
    unit_option = next(
        use for obj in changed["objects"] for use in obj["unitUses"]
        if use["kind"] == "unit-option-include"
    )
    unit_option["armyId"] = unit_option["targetArmyId"]
    rejected(changed, "Unit-wide option cannot invent Army")

    changed = copy.deepcopy(original)
    changed["sourceSnapshot"]["rulesDatabaseSha256"] = "0" * 64
    rejected(changed, "source provenance")


def test_legacy_rules_never_attach_adjacent_deployed_object_json(
    source_paths: tuple[Path, Path, Path, Path, Path],
    legacy_v9_rules: Path, tmp_path: Path,
) -> None:
    from infinity_db.web import create_app

    release = tmp_path / "release"
    release.mkdir()
    army = release / "army.db"
    rules = release / "rules_n5.db"
    shutil.copyfile(source_paths[0], army)
    shutil.copyfile(legacy_v9_rules, rules)
    (release / "deployed-objects.json").write_text("{", encoding="utf-8")
    external_rules = tmp_path / "independent" / "rules_n5.db"
    external_rules.parent.mkdir()
    shutil.copyfile(legacy_v9_rules, external_rules)

    # Legacy v9 lacks the embedded Weapon Chart and deployed-object model.
    # Modern serving rejects it before a stale/invalid adjacent JSON could
    # be interpreted as an independent publication fallback.
    for candidate in (rules, external_rules):
        with pytest.raises(ValueError, match="Embedded Weapon citations"):
            create_app(army, rules_database_path=candidate)


def test_release_pair_still_fails_closed_on_same_directory_rules_drift(
    source_paths: tuple[Path, Path, Path, Path, Path],
    tmp_path: Path,
) -> None:
    from infinity_db.web import create_app

    army = tmp_path / "army.db"
    rules = tmp_path / "rules_n5.db"
    shutil.copyfile(source_paths[0], army)
    shutil.copyfile(source_paths[1], rules)
    (tmp_path / "deployed-objects.json").write_text("{", encoding="utf-8")
    with sqlite3.connect(rules) as db:
        db.execute(
            "UPDATE deployed_object_metadata SET value=? WHERE key='armyDatabaseSha256'",
            (json.dumps("0" * 64),),
        )
    with pytest.raises(ValueError, match="do not match"):
        create_app(army, rules_database_path=rules)

