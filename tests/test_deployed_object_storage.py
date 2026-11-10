"""SQLite deployed-object projection: normalized persistence and source pairing."""
from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest

from infinity_db.deployed_object_builder import build_deployed_objects
from infinity_db.deployed_object_storage import (
    read_deployed_objects,
    stage_deployed_objects,
)


@pytest.fixture(scope="module")
def pinned_inputs() -> tuple[Path, ...]:
    root = Path(__file__).resolve().parents[1]
    paths = (
        root / "data/generated/army.db",
        root / "data/generated/rules_n5.db",
        root / "data/curated/rules/n5-core-v5.3.json",
        root / "config/validation/deployed-object-delivery-reviews.json",
        root / "config/validation/deployed-object-candidate-reviews.json",
    )
    if not all(path.is_file() for path in paths):
        pytest.skip("Pinned source and release files are unavailable")
    return paths


def test_normalized_snapshot_round_trips_exact_reviewed_projection(
    pinned_inputs: tuple[Path, ...],
) -> None:
    publication = build_deployed_objects(pinned_inputs[0], *pinned_inputs[2:])
    with sqlite3.connect(":memory:") as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        stage_deployed_objects(connection, publication)
        rebuilt = read_deployed_objects(connection, pinned_inputs[0])
        assert rebuilt == publication
        assert len(rebuilt["objects"]) == 17
        assert len(rebuilt["unresolvedDeliveries"]) == 1
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []



def test_standalone_rules_build_preserves_deployed_object_source_facts(
    pinned_inputs: tuple[Path, ...], tmp_path: Path,
) -> None:
    from infinity_db.cli import build_parser, cmd_build_rules
    from infinity_db.rules_database import RulesDatabase
    from infinity_db.web import create_app

    army = tmp_path / "army.db"
    rules = tmp_path / "rules_n5.db"
    shutil.copyfile(pinned_inputs[0], army)
    args = build_parser().parse_args([
        "build-rules", "--army-db", str(army), "--output", str(rules),
    ])
    assert cmd_build_rules(args) == 0
    assert not (tmp_path / "deployed-objects.json").exists()

    embedded = RulesDatabase(rules).deployed_objects_payload(army)
    assert embedded is not None
    assert len(embedded["objects"]) == 17
    assert len(embedded["unresolvedDeliveries"]) == 1

    # Standalone v10 remains useful for inspecting source facts, not for
    # launching an incomplete runtime set.
    with pytest.raises(ValueError, match="Embedded Weapon citations require Rules v12"):
        create_app(army, rules)


def test_v10_validator_rejects_missing_embedded_table(tmp_path: Path) -> None:
    from infinity_db.cli import build_parser, cmd_build_rules
    from infinity_db.rules_database import RulesDatabase

    output = tmp_path / "candidate.db"
    args = build_parser().parse_args(["build-rules", "--output", str(output)])
    assert cmd_build_rules(args) == 0
    with sqlite3.connect(output) as connection:
        connection.execute("DROP TABLE deployed_object_unresolved")
    with pytest.raises(ValueError, match="Incomplete normalized deployed-object schema"):
        RulesDatabase(output).validate()


def test_v10_standalone_build_is_deterministic(tmp_path: Path) -> None:
    from infinity_db.cli import build_parser, cmd_build_rules

    outputs = [tmp_path / name for name in ("first.db", "second.db")]
    for output in outputs:
        args = build_parser().parse_args(["build-rules", "--output", str(output)])
        assert cmd_build_rules(args) == 0
    assert outputs[0].read_bytes() == outputs[1].read_bytes()



def test_normalized_snapshot_rejects_mismatched_army_sha(
    pinned_inputs: tuple[Path, ...],
) -> None:
    publication = build_deployed_objects(pinned_inputs[0], *pinned_inputs[2:])
    with sqlite3.connect(":memory:") as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        stage_deployed_objects(connection, publication)
        connection.execute(
            "UPDATE deployed_object_metadata SET value = ? WHERE key = ?",
            ('"not-the-army-sha"', "armyDatabaseSha256"),
        )
        with pytest.raises(ValueError, match="do not match"):
            read_deployed_objects(connection, pinned_inputs[0])


@pytest.fixture(scope="module")
def reviewed_model(pinned_inputs: tuple[Path, ...]) -> dict:
    return build_deployed_objects(pinned_inputs[0], *pinned_inputs[2:])


@pytest.mark.parametrize("mutation,message", (
    ("UPDATE deployed_object_unit_uses SET army_id=1 "
     "WHERE kind='unit-option-include'", "Unit-wide option cannot invent Army"),
    ("UPDATE deployed_object_unit_uses SET profile_id=1 "
     "WHERE kind='loadout'", "profile/loadout usage context"),
    ("UPDATE deployed_object_unit_uses SET target_loadout_payload_id=NULL "
     "WHERE kind='loadout-include'", "Include provenance"),
    ("UPDATE deployed_object_unit_uses SET kind='invented'", "Invalid or unreviewed"),
    ("UPDATE deployed_object_attribute_sources SET source_json='{}'", "missing source provenance"),
    ("UPDATE deployed_object_metadata SET value='\"bad\"' "
     "WHERE key='candidateReviewSha256'", "source provenance"),
))
def test_embedded_reader_rejects_tampered_evidence_and_unit_context(
    reviewed_model: dict, pinned_inputs: tuple[Path, ...], mutation: str, message: str,
) -> None:
    with sqlite3.connect(":memory:") as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        stage_deployed_objects(connection, reviewed_model)
        assert connection.execute(mutation).rowcount > 0
        with pytest.raises(ValueError, match=message):
            read_deployed_objects(connection, pinned_inputs[0])


def test_embedded_reader_rejects_duplicate_army_source_selectors(
    reviewed_model: dict, pinned_inputs: tuple[Path, ...],
) -> None:
    with sqlite3.connect(":memory:") as connection:
        stage_deployed_objects(connection, reviewed_model)
        first, second = connection.execute(
            "SELECT id,source_profile_json FROM deployed_objects "
            "WHERE source_profile_json IS NOT NULL ORDER BY id LIMIT 2"
        ).fetchall()
        connection.execute(
            "UPDATE deployed_objects SET source_profile_json=? WHERE id=?",
            (first[1], second[0]),
        )
        with pytest.raises(ValueError, match="Duplicate deployed-object Army source selector"):
            read_deployed_objects(connection, pinned_inputs[0])
