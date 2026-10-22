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
                assert use["kind"] in {"profile", "loadout"}
                assert use["unitSlug"] and use["armyName"]
                kind = use["kind"]
                identity = "profileId" if kind == "profile" else "optionId"
                other = "optionId" if kind == "profile" else "profileId"
                assert use[identity] is not None and use[other] is None
                matches = db.execute(
                    f"SELECT COUNT(*) FROM {kind}_payload_occurrences AS o "
                    f"JOIN {kind}_payload_"
                    f"{'weapons' if use['originRecordId'].startswith('weapon:') else 'equipment'} "
                    f"AS p ON p.{kind}_payload_id = o.{kind}_payload_id "
                    f"WHERE o.army_id = ? AND o.unit_id = ? AND o.group_id = ? "
                    f"AND o.{'profile_id' if kind == 'profile' else 'option_id'} = ? "
                    "AND p.item_id = ? AND p.position = ?",
                    (use["armyId"], use["unitId"], use["groupId"],
                     use[identity], use["sourceItemId"], use["sourcePosition"]),
                ).fetchone()[0]
                assert matches == 1, use
    assert uses_count > 0
    # Reviewed source use does not resolve Mine Dispenser subtype or invent
    # ownership for curated objects without a reviewed delivery edge.
    assert publication["unresolvedDeliveries"][0]["originRecordId"] == (
        "weapon:mine-dispenser"
    )


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
    with_uses = next(obj for obj in changed["objects"] if obj["unitUses"])
    with_uses["unitUses"][0]["optionId"] = 1 if (
        with_uses["unitUses"][0]["kind"] == "profile"
    ) else None
    with_uses["unitUses"][0]["profileId"] = 1 if (
        with_uses["unitUses"][0]["kind"] == "loadout"
    ) else None
    rejected(changed, "profile/loadout usage context")


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

