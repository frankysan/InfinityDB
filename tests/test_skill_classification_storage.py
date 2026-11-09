"""P2.4 Army v28 authored Skill source classifications, not N5 Skills."""

from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from infinity_db.database.publication import validate_database_pair
from infinity_db.database.repository import Database
from infinity_db.equipment_presentation_storage import publish_equipment_encodings
from infinity_db.rules_database import RulesDatabase
from infinity_db.skill_catalog import SkillCatalog
from infinity_db.skill_classification_storage import (
    ARMY_COMPATIBILITY_VERSION,
    ARMY_SCHEMA_VERSION,
    publish_skill_classifications,
    read_skill_classifications,
)
from infinity_db.skill_config import load_skill_source_config
from infinity_db.unit_presentation import enrich_unit_presentation

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/generated"
EQUIPMENT_CONFIG = ROOT / "config/catalogs/equipment-presentation-encodings.json"
SKILL_CONFIG = ROOT / "config/catalogs/skill-source-classifications.json"


@pytest.fixture
def v28(tmp_path: Path) -> tuple[Path, Path]:
    army, raw = tmp_path / "infinity.db", tmp_path / "infinity.raw.db"
    shutil.copyfile(RELEASE / "infinity.db", army)
    shutil.copyfile(RELEASE / "infinity.db", raw)
    publish_equipment_encodings(army, raw, EQUIPMENT_CONFIG)
    publish_skill_classifications(army, raw, SKILL_CONFIG)
    return army, raw


def test_v28_roundtrip_and_paired_generation(v28) -> None:
    army, raw = v28
    expected = load_skill_source_config(SKILL_CONFIG)
    assert len(expected) == 6
    assert [(item.skill_ref, item.classification) for item in expected] == [
        ("bangbomb", "equipment"), ("bts-3", "attribute-override"),
        ("gizmokit", "equipment"), ("infinity-team-ops", "source-marker"),
        ("medikit", "equipment"), ("regular", "training"),
    ]
    Database(army).validate()
    assert validate_database_pair(army, raw_path=raw) is not None
    assert Database(army).skill_source_classifications() == expected
    assert Database(RELEASE / "infinity.db").skill_source_classifications() is None
    with sqlite3.connect(army) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == ARMY_SCHEMA_VERSION
        assert json.loads(connection.execute(
            "SELECT value FROM __infinity_metadata WHERE key='database_compatibility_version'"
        ).fetchone()[0]) == ARMY_COMPATIBILITY_VERSION
        assert read_skill_classifications(connection) == expected
        assert connection.execute(
            "SELECT COUNT(*) FROM skill_source_classifications"
        ).fetchone()[0] == 6
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_skills_catalog_v28_parity_and_zero_json_reads(v28, monkeypatch) -> None:
    import infinity_db.skill_catalog as adapter

    army, _ = v28
    rules = RulesDatabase(RELEASE / "rules.db")
    legacy = SkillCatalog(Database(RELEASE / "infinity.db"), rules)
    old_ids = legacy._rules_catalog_excluded_source_ids()
    assert len(old_ids) == 6

    def forbidden(*_args, **_kwargs):
        raise AssertionError("v28 Skill catalog must not load source classification JSON")

    monkeypatch.setattr(adapter, "load_skill_source_config", forbidden)
    current = SkillCatalog(Database(army), rules)
    assert current._rules_catalog_excluded_source_ids() == old_ids


def test_unit_presentation_accepts_explicit_v28_projection(v28, monkeypatch) -> None:
    import infinity_db.unit_presentation as presenter

    army, _ = v28
    units = Database(army).list_units(limit=1)["items"]
    assert units
    unit = Database(army).get_unit(units[0]["id"])
    assert unit is not None
    expected = enrich_unit_presentation(json.loads(json.dumps(unit)))

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Unit presentation must use provided v28 projection")

    monkeypatch.setattr(presenter, "load_skill_source_config", forbidden)
    actual = enrich_unit_presentation(
        json.loads(json.dumps(unit)),
        source_skill_classifications=Database(army).skill_source_classifications(),
    )
    assert actual == expected


@pytest.mark.parametrize("mutation", (
    "missing", "duplicate", "invalid-classification", "unknown-ref",
    "repeat-identity",
))
def test_build_rejects_unreviewed_source_changes(tmp_path: Path, mutation: str) -> None:
    army, raw = tmp_path / "infinity.db", tmp_path / "infinity.raw.db"
    shutil.copyfile(RELEASE / "infinity.db", army)
    shutil.copyfile(RELEASE / "infinity.db", raw)
    publish_equipment_encodings(army, raw, EQUIPMENT_CONFIG)
    document = json.loads(SKILL_CONFIG.read_text(encoding="utf-8"))
    if mutation == "missing":
        document["classifications"].pop()
    elif mutation == "duplicate":
        document["classifications"].append(document["classifications"][0].copy())
    elif mutation == "invalid-classification":
        document["classifications"][0]["classification"] = "official-skill"
    elif mutation == "unknown-ref":
        document["classifications"][0]["skill_id"] = "unreviewed-n5-skill"
    else:
        document["classifications"][1]["skill_id"] = "bangbomb"
    source = tmp_path / "unreviewed.json"
    source.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError):
        publish_skill_classifications(army, raw, source)
    Database(army).validate()
    assert Database(army).skill_source_classifications() is None


@pytest.mark.parametrize("mutation", (
    "missing", "reason", "classification", "identity", "source", "fingerprint",
))
def test_read_rejects_corrupt_source_rows(v28, mutation: str) -> None:
    army, _ = v28
    with sqlite3.connect(army) as connection:
        if mutation == "missing":
            connection.execute(
                "DELETE FROM skill_source_classifications WHERE source_ref='bangbomb'"
            )
        elif mutation == "reason":
            connection.execute(
                "UPDATE skill_source_classifications SET reason='unreviewed' "
                "WHERE source_ref='bangbomb'"
            )
        elif mutation == "classification":
            connection.execute(
                "UPDATE skill_source_classifications SET classification='training' "
                "WHERE source_ref='bangbomb'"
            )
        elif mutation == "identity":
            connection.execute(
                "UPDATE skill_source_classifications SET application_skill_id=999999 "
                "WHERE source_ref='bangbomb'"
            )
        elif mutation == "source":
            connection.execute(
                "UPDATE skill_source_classification_metadata SET export_pair_sha256=?",
                ("0" * 64,),
            )
        else:
            connection.execute(
                "UPDATE skill_source_classification_metadata SET content_sha256=?",
                ("0" * 64,),
            )
        with pytest.raises(ValueError):
            read_skill_classifications(connection)
    with pytest.raises(ValueError):
        Database(army).validate()


def test_numeric_source_identity_retained_without_slug_inference(tmp_path: Path) -> None:
    army, raw = tmp_path / "infinity.db", tmp_path / "infinity.raw.db"
    shutil.copyfile(RELEASE / "infinity.db", army)
    shutil.copyfile(RELEASE / "infinity.db", raw)
    publish_equipment_encodings(army, raw, EQUIPMENT_CONFIG)
    source = json.loads(SKILL_CONFIG.read_text(encoding="utf-8"))
    skill_id = Database(army).application_catalog_id("skills", "bangbomb")
    assert type(skill_id) is int
    source["classifications"][0]["skill_id"] = skill_id
    config = tmp_path / "numeric-skill.json"
    config.write_text(json.dumps(source), encoding="utf-8")
    publish_skill_classifications(army, raw, config)
    mapped = Database(army).skill_source_classifications()
    assert mapped is not None and mapped[0].skill_ref == skill_id
    assert mapped[0].classification == "equipment"
    Database(army).validate()
