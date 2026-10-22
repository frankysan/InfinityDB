"""Release-time generation and fail-closed loading of deployed-object references."""

from __future__ import annotations

import copy
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from infinity_db.deployed_object_publication import load_deployed_object_publication
from tools.build_deployed_object_publication import build_publication, publication_bytes


@pytest.fixture(scope="module")
def source_paths() -> tuple[Path, Path, Path, Path, Path]:
    root = Path(__file__).resolve().parents[1]
    files = (
        root / "data/generated/infinity.db",
        root / "data/generated/rules.db",
        root / "data/curated/rules/n5-core-v5.3.json",
        root / "config/validation/deployed-object-delivery-reviews.json",
        root / "config/validation/deployed-object-candidate-reviews.json",
    )
    if not all(path.is_file() for path in files):
        pytest.skip("Pinned release source inputs unavailable")
    return files


def test_pinned_publication_is_deterministic_and_source_complete(
    source_paths: tuple[Path, Path, Path, Path, Path], tmp_path: Path,
) -> None:
    publication = build_publication(*source_paths)
    assert publication_bytes(publication) == publication_bytes(build_publication(*source_paths))
    assert len(publication["objects"]) == 17
    assert len(publication["unresolvedDeliveries"]) == 1
    path = tmp_path / "deployed-objects.json"
    path.write_bytes(publication_bytes(publication))
    assert load_deployed_object_publication(path, source_paths[0], source_paths[1]) == (
        publication
    )


def test_named_mines_use_only_their_exact_army_source_subtype(
    source_paths: tuple[Path, Path, Path, Path, Path],
) -> None:
    publication = build_publication(*source_paths)
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
    publication = build_publication(*source_paths)
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
    publication = build_publication(*source_paths)
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
    publication = build_publication(*source_paths)
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


def test_publication_missing_is_legacy_compatible_but_corrupt_fails_closed(
    source_paths: tuple[Path, Path, Path, Path, Path], tmp_path: Path,
) -> None:
    output = tmp_path / "deployed-objects.json"
    assert load_deployed_object_publication(output, source_paths[0], source_paths[1]) is None
    output.write_text("{", encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="JSON"):
        load_deployed_object_publication(output, source_paths[0], source_paths[1])

    output.write_bytes(publication_bytes(build_publication(*source_paths)))
    with pytest.raises(ValueError, match="requires a rules database"):
        load_deployed_object_publication(output, source_paths[0], None)
    wrong = tmp_path / "wrong.db"
    shutil.copyfile(source_paths[1], wrong)
    wrong.write_bytes(b"wrong")
    with pytest.raises(ValueError, match="does not match"):
        load_deployed_object_publication(output, source_paths[0], wrong)


def test_publication_rejects_identity_value_and_delivery_tampering(
    source_paths: tuple[Path, Path, Path, Path, Path], tmp_path: Path,
) -> None:
    original = build_publication(*source_paths)
    output = tmp_path / "deployed-objects.json"

    def rejected(document: dict, message: str) -> None:
        output.write_text(json.dumps(document), encoding="utf-8", newline="\n")
        with pytest.raises(ValueError, match=message):
            load_deployed_object_publication(output, source_paths[0], source_paths[1])

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


def test_external_rules_database_does_not_inherit_adjacent_release_publication(
    source_paths: tuple[Path, Path, Path, Path, Path], tmp_path: Path,
) -> None:
    from infinity_db.web import create_app

    release = tmp_path / "release"
    release.mkdir()
    army = release / "infinity.db"
    rules = release / "rules.db"
    shutil.copyfile(source_paths[0], army)
    shutil.copyfile(source_paths[1], rules)
    (release / "deployed-objects.json").write_bytes(
        publication_bytes(build_publication(*source_paths))
    )
    external_rules = tmp_path / "independent" / "rules.db"
    external_rules.parent.mkdir()
    shutil.copyfile(source_paths[1], external_rules)

    assert create_app(army, rules_database_path=rules).deployed_objects is not None
    # An independently supplied rules source must never pick up that publication,
    # even when its contents happen to match the release pair byte-for-byte.
    assert create_app(army, rules_database_path=external_rules).deployed_objects is None


def test_release_pair_still_fails_closed_on_same_directory_rules_drift(
    source_paths: tuple[Path, Path, Path, Path, Path], tmp_path: Path,
) -> None:
    from infinity_db.web import create_app

    army = tmp_path / "infinity.db"
    rules = tmp_path / "rules.db"
    shutil.copyfile(source_paths[0], army)
    shutil.copyfile(source_paths[1], rules)
    (tmp_path / "deployed-objects.json").write_bytes(
        publication_bytes(build_publication(*source_paths))
    )
    with sqlite3.connect(rules) as db:
        db.execute(
            "UPDATE sources SET title = title || ' ' "
            "WHERE rowid = (SELECT rowid FROM sources LIMIT 1)"
        )
    with pytest.raises(ValueError, match="does not match release databases"):
        create_app(army, rules_database_path=rules)

