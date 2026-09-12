from __future__ import annotations

import hashlib
import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from infinity_army_data.metadata import MetadataError, decode_metadata
from infinity_army_data.normalize import normalize_master, validate_normalized
from infinity_db.cli import main
from infinity_db.database import Database, export_database


def metadata_source() -> dict:
    return {
        "factions": [
            {"id": 101, "parent": 101, "name": "Official First", "slug": "official-first"},
            {"id": 999, "parent": 998, "name": "Metadata only", "discontinued": True},
        ],
        "ammunitions": [{"id": 1, "name": "Ammo", "wiki": "https://example.test/ammo"}],
        "weapons": [
            {"id": 7, "name": "Mode one"},
            {"id": 7, "name": "Mode two"},
        ],
        "skills": [{"id": 2, "name": "Skill"}],
        "equips": [{"id": 3, "name": "Equipment"}],
        "hack": [{"name": "Hack", "devices": [3]}],
        "martialArts": [{"name": "1", "attack": "+3"}],
        "metachemistry": [{"id": 4, "name": "1-3", "value": "+3 PH"}],
        "booty": [{"id": 5, "name": "1-2", "value": "+1 ARM"}],
        "future_collection": [{"kept": True}],
    }


def master(envelope: dict) -> dict:
    return {
        "_meta": {"format": "Infinity Army merged JSON", "formatVersion": 1},
        "armyMetadata": envelope,
        "armyLists": {
            "101": {"_meta": {"slug": "source-slug", "kind": "army"}, "unitIds": [1]},
        },
        "units": {
            "1": {"shared": {"id": 1, "name": "Unit", "factions": [101]}, "byArmy": {"101": {}}},
        },
    }


def test_metadata_preserves_api_records_and_enriches_only_matching_armies() -> None:
    raw = json.dumps(metadata_source()).encode()
    envelope = decode_metadata(raw, "metadata.json")
    data = normalize_master(master(envelope))
    validate_normalized(data)
    assert data["armyMetadata"] == envelope
    assert envelope["sourceSha256"] == hashlib.sha256(raw).hexdigest()
    assert data["tables"]["army_lists"][0]["name"] == "Official First"
    assert data["tables"]["army_lists"][0]["slug"] == "source-slug"
    assert [row["name"] for row in data["tables"]["metadata_weapons"]] == ["Mode one", "Mode two"]
    assert [row["position"] for row in data["tables"]["metadata_weapons"]] == [1, 2]
    assert data["tables"]["metadata_hacking_programs"][0]["position"] == 1
    assert data["armyMetadata"]["data"]["future_collection"] == [{"kept": True}]


def test_missing_mine_profile_is_supplied_during_normalization() -> None:
    envelope = decode_metadata(json.dumps(metadata_source()).encode(), "metadata.json")
    envelope["data"]["weapons"].append({"id": 199, "name": "AP Mine"})

    data = normalize_master(master(envelope))

    mine = next(row for row in data["tables"]["metadata_weapons"] if row["id"] == 199)
    assert mine["profile"] == "ARM=0, BTS=0, STR=1, S=1"


def test_multi_spitfire_name_is_corrected_in_catalog_and_profiles() -> None:
    source = metadata_source()
    source["weapons"] = [{"id": 217, "name": "Spitfire MULTI", "mode": "AP Mode"}]
    document = master(decode_metadata(json.dumps(source).encode(), "metadata.json"))
    document["armyLists"]["101"]["filters"] = {
        "weapons": [{"id": 217, "name": "Spitfire MULTI", "type": "BS"}],
    }

    normalized = normalize_master(document)

    assert normalized["tables"]["weapons"] == [
        {
            "id": 217,
            "name": "MULTI Spitfire",
            "type": "BS",
            "category": "Spitfires",
            "source_defined": True,
        }
    ]
    assert normalized["tables"]["metadata_weapons"][0]["name"] == "MULTI Spitfire"


def test_deployable_repeater_profile_is_shown_with_its_equipment(tmp_path: Path) -> None:
    source = metadata_source()
    source["weapons"] = [
        {"id": 111, "name": "Deployable Repeater", "type": "EQUIPMENT"},
        {"id": 111, "name": "Plasma Carbine", "type": "WEAPON", "mode": "Hit Mode"},
    ]
    document = master(decode_metadata(json.dumps(source).encode(), "metadata.json"))
    document["armyLists"]["101"]["filters"] = {
        "weapons": [{"id": 111, "name": "Plasma Carbine"}],
        "equip": [{"id": 111, "name": "Deployable Repeater"}],
    }

    normalized = normalize_master(document)
    path = tmp_path / "infinity.db"
    export_database(normalized, path)

    database = Database(path)
    plasma = database.get_catalog_item("weapons", 111)
    repeater = database.get_catalog_item("equipment", 111)

    assert plasma is not None
    assert [(profile["name"], profile["mode"]) for profile in plasma["profiles"]] == [
        ("Plasma Carbine", "Hit Mode")
    ]
    assert repeater is not None
    assert repeater["name"] == "Deployable Repeater"
    assert [(profile["name"], profile["mode"]) for profile in repeater["profiles"]] == [
        ("Deployable Repeater", None)
    ]


def test_metadata_rows_are_stored_but_do_not_create_armies(tmp_path: Path) -> None:
    envelope = decode_metadata(json.dumps(metadata_source()).encode(), "metadata.json")
    normalized = normalize_master(master(envelope))
    path = tmp_path / "infinity.db"
    export_database(normalized, path)
    assert Database(path).list_armies() == [
        {
            "id": 101,
            "name": "Official First",
            "slug": "source-slug",
            "kind": "army",
            "unit_count": 1,
        }
    ]
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM metadata_factions").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM metadata_weapons").fetchone()[0] == 2


@pytest.mark.parametrize(
    "source",
    [
        {"factions": [{"id": 1, "name": "One"}], "skills": [{"id": 1}, {"id": 1}]},
        {"factions": [{"id": 1, "name": ""}]},
        {"factions": "not a list"},
    ],
)
def test_invalid_metadata_is_rejected(source: dict) -> None:
    with pytest.raises(MetadataError):
        decode_metadata(json.dumps(source).encode(), "metadata.json")


def test_build_discovers_sidecar_metadata_and_can_disable_it(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "101-first.json").write_text(
        json.dumps({"version": "test", "units": [{"id": 1, "name": "Unit"}]}), encoding="utf-8"
    )
    (source / "metadata.json").write_text(json.dumps(metadata_source()), encoding="utf-8")
    output = tmp_path / "with-metadata"
    assert main(["build", str(source), "--output-dir", str(output)]) == 0
    with sqlite3.connect(output / "infinity.db") as connection:
        assert connection.execute("SELECT name FROM army_lists").fetchone()[0] == "Official First"
        assert connection.execute("SELECT COUNT(*) FROM metadata_factions").fetchone()[0] == 2

    without = tmp_path / "without-metadata"
    assert main(["build", str(source), "--output-dir", str(without), "--no-metadata"]) == 0
    with sqlite3.connect(without / "infinity.db") as connection:
        assert connection.execute("SELECT name FROM army_lists").fetchone()[0] is None
        assert connection.execute("SELECT COUNT(*) FROM metadata_factions").fetchone()[0] == 0


def test_build_discovers_unique_metadata_inside_zip(tmp_path: Path) -> None:
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("army/101-first.json", json.dumps({"version": "test", "units": []}))
        output.writestr("army/metadata.json", json.dumps(metadata_source()))
    output_dir = tmp_path / "generated"
    assert main(["build", str(archive), "--output-dir", str(output_dir)]) == 0
    normalized = json.loads((output_dir / "normalized.json").read_text(encoding="utf-8"))
    assert normalized["armyMetadata"]["sourceFile"] == "metadata.json"
