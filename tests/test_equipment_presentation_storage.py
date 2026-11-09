"""P2.4 opt-in Army v27 Equipment presentation encodings."""

from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from infinity_db.database.publication import validate_database_pair
from infinity_db.database.repository import Database
from infinity_db.equipment_catalog import EquipmentCatalog
from infinity_db.equipment_config import (
    EquipmentConfigError,
    load_equipment_presentation_config,
)
from infinity_db.equipment_presentation_storage import (
    ARMY_COMPATIBILITY_VERSION,
    ARMY_SCHEMA_VERSION,
    publish_equipment_encodings,
    read_equipment_encodings,
)
from infinity_db.rules_database import RulesDatabase

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/generated"
CONFIG = ROOT / "config/catalogs/equipment-presentation-encodings.json"


@pytest.fixture
def v27(tmp_path: Path) -> tuple[Path, Path]:
    army = tmp_path / "infinity.db"
    raw = tmp_path / "infinity.raw.db"
    shutil.copyfile(RELEASE / "infinity.db", army)
    shutil.copyfile(RELEASE / "infinity.db", raw)
    publish_equipment_encodings(army, raw, CONFIG)
    return army, raw


def test_v27_source_rows_pair_checksum_and_legacy_compatibility(v27) -> None:
    army, raw = v27
    expected = load_equipment_presentation_config(CONFIG)
    assert [(row.equipment_id, row.characteristic) for row in expected] == [
        ("cube", "Cube"), ("cube-2", "Cube 2.0"),
    ]
    Database(army).validate()
    assert validate_database_pair(army, raw_path=raw) is not None
    assert Database(army).equipment_presentation_encodings() == expected
    assert Database(RELEASE / "infinity.db").equipment_presentation_encodings() is None
    with sqlite3.connect(army) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == ARMY_SCHEMA_VERSION
        assert json.loads(connection.execute(
            "SELECT value FROM __infinity_metadata WHERE key='database_compatibility_version'"
        ).fetchone()[0]) == ARMY_COMPATIBILITY_VERSION
        assert read_equipment_encodings(connection) == expected
        assert connection.execute(
            "SELECT COUNT(*) FROM equipment_presentation_encodings"
        ).fetchone()[0] == 2
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_v27_equipment_projection_parity_without_runtime_json(v27, monkeypatch) -> None:
    import infinity_db.equipment_catalog as adapter

    army, _ = v27
    rules = RulesDatabase(RELEASE / "rules.db")
    previous = EquipmentCatalog(Database(RELEASE / "infinity.db"), rules)
    baseline = (
        previous.list_equipment(),
        previous.get_equipment("cube"),
        previous.get_equipment("cube-2"),
        previous.logical_unit_ids_for_filter("cube"),
        previous.logical_unit_ids_for_filter("cube-2"),
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("v27 EquipmentCatalog must not read maintained JSON")

    monkeypatch.setattr(adapter, "load_equipment_presentation_config", forbidden)
    current = EquipmentCatalog(Database(army), rules)
    assert (
        current.list_equipment(),
        current.get_equipment("cube"),
        current.get_equipment("cube-2"),
        current.logical_unit_ids_for_filter("cube"),
        current.logical_unit_ids_for_filter("cube-2"),
    ) == baseline


@pytest.mark.parametrize("mutation", (
    "missing", "unknown-characteristic", "duplicate-equipment", "duplicate-characteristic",
))
def test_publication_rejects_source_drift(
    tmp_path: Path, mutation: str,
) -> None:
    army = tmp_path / "infinity.db"
    raw = tmp_path / "infinity.raw.db"
    shutil.copyfile(RELEASE / "infinity.db", army)
    shutil.copyfile(RELEASE / "infinity.db", raw)
    document = json.loads(CONFIG.read_text(encoding="utf-8"))
    if mutation == "missing":
        document["encodings"].pop()
    elif mutation == "unknown-characteristic":
        document["encodings"][0]["characteristic"] = "Unavailable Characteristic"
    elif mutation == "duplicate-equipment":
        document["encodings"][1]["equipment_id"] = "cube"
    else:
        document["encodings"][1]["characteristic"] = "cube"
    source = tmp_path / "invalid.json"
    source.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises((ValueError, EquipmentConfigError)):
        publish_equipment_encodings(army, raw, source)
    Database(army).validate()
    assert Database(army).equipment_presentation_encodings() is None


@pytest.mark.parametrize("mutation", (
    "missing", "name", "reason", "identity", "source", "fingerprint",
))
def test_read_rejects_corrupt_publication(v27, mutation: str) -> None:
    army, _raw = v27
    with sqlite3.connect(army) as connection:
        if mutation == "missing":
            connection.execute(
                "DELETE FROM equipment_presentation_encodings WHERE equipment_id='cube'"
            )
        elif mutation == "name":
            connection.execute(
                "UPDATE equipment_presentation_encodings SET characteristic='Cube 4.0' "
                "WHERE equipment_id='cube'"
            )
        elif mutation == "reason":
            connection.execute(
                "UPDATE equipment_presentation_encodings SET reason='unreviewed' "
                "WHERE equipment_id='cube'"
            )
        elif mutation == "identity":
            connection.execute(
                "UPDATE equipment_presentation_encodings SET characteristic_id=999999 "
                "WHERE equipment_id='cube'"
            )
        elif mutation == "source":
            connection.execute(
                "UPDATE equipment_presentation_metadata SET export_pair_sha256=?",
                ("0" * 64,),
            )
        else:
            connection.execute(
                "UPDATE equipment_presentation_metadata SET content_sha256=?",
                ("0" * 64,),
            )
        with pytest.raises(ValueError):
            read_equipment_encodings(connection)
    with pytest.raises(ValueError):
        Database(army).validate()
