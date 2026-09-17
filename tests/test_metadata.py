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


def test_configured_non_display_weapon_metadata_profiles_are_suppressed() -> None:
    source = metadata_source()
    source["weapons"] = [
        {"id": 226, "name": "Armed Turret", "burst": "-", "damage": "-"},
        {
            "id": 226,
            "name": "Armed Turret",
            "mode": "Combi Rifle",
            "burst": "3",
            "damage": "7",
        },
        {
            "id": 226,
            "name": "Armed Turret",
            "mode": "PARA CC Weapon",
            "burst": "1",
            "damage": "-",
        },
    ]

    normalized = normalize_master(
        master(decode_metadata(json.dumps(source).encode(), "metadata.json"))
    )

    assert [
        (row["name"], row.get("mode"))
        for row in normalized["tables"]["metadata_weapons"]
    ] == [("Armed Turret", "Combi Rifle")]
    assert len(normalized["armyMetadata"]["data"]["weapons"]) == 3


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


def test_normalization_uses_metadata_parent_for_main_army_identity() -> None:
    source = metadata_source()
    source["factions"][0]["parent"] = 777
    source["factions"].append(
        {"id": 777, "parent": 777, "name": "Source-defined parent", "slug": "parent"}
    )
    document = master(decode_metadata(json.dumps(source).encode(), "metadata.json"))
    document["armyLists"]["777"] = {
        "_meta": {"slug": "parent", "kind": "army"},
        "unitIds": [],
    }
    document["units"]["1"]["shared"]["canonical"] = 101

    normalized = normalize_master(document)
    validate_normalized(normalized)

    assert normalized["tables"]["units"][0]["main_army_id"] == 777


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
            "role": "main",
            "playable": True,
            "group_id": None,
            "group_name": None,
            "group_slug": None,
            "parent_army_ids": [],
            "unit_count": 1,
        }
    ]
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM metadata_factions").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM metadata_weapons").fetchone()[0] == 2


def test_army_roles_use_metadata_hierarchy_and_reinforcement_links(tmp_path: Path) -> None:
    source = metadata_source()
    source["factions"].extend(
        [
            {
                "id": 102,
                "parent": 101,
                "name": "Official Sectorial",
                "slug": "official-sectorial",
            },
            {
                "id": 198,
                "parent": 101,
                "name": "First Reinforcements",
                "slug": "first-reinforcements",
            },
            {
                "id": 901,
                "parent": 901,
                "name": "Non-Aligned Armies",
                "slug": "non-aligned-armies",
            },
            {
                "id": 902,
                "parent": 901,
                "name": "Independent Company",
                "slug": "independent-company",
            },
        ]
    )
    document = master(decode_metadata(json.dumps(source).encode(), "metadata.json"))
    document["armyLists"]["101"]["reinforcements"] = 198
    document["armyLists"]["102"] = {
        "_meta": {"slug": "source-sectorial", "kind": "army"},
        "unitIds": [1],
    }
    document["armyLists"]["198"] = {
        "_meta": {"slug": "source-reinforcements", "kind": "reinforcement"},
        "unitIds": [1],
    }
    document["armyLists"]["902"] = {
        "_meta": {"slug": "source-na2", "kind": "army"},
        "unitIds": [1],
    }
    document["units"]["1"]["byArmy"].update({"102": {}, "198": {}, "902": {}})

    normalized = normalize_master(document)
    path = tmp_path / "infinity.db"
    export_database(normalized, path)
    armies = {army["id"]: army for army in Database(path).list_armies()}

    assert armies[101]["role"] == "main"
    assert armies[101]["playable"] is True
    assert armies[102]["role"] == "sectorial"
    assert armies[102]["group_id"] == 101
    assert armies[102]["group_name"] == "Official First"
    assert armies[198]["role"] == "reinforcement"
    assert armies[198]["parent_army_ids"] == [101]
    assert armies[902]["role"] == "non_aligned"
    assert armies[902]["group_id"] == 901
    assert armies[902]["group_name"] == "Non-Aligned Armies"
    assert armies[901] == {
        "id": 901,
        "name": "Non-Aligned Armies",
        "slug": "non-aligned-armies",
        "kind": "grouping",
        "role": "grouping",
        "playable": False,
        "group_id": None,
        "group_name": None,
        "group_slug": None,
        "parent_army_ids": [],
        "unit_count": 0,
    }
    with pytest.raises(ValueError, match="grouping-only identity"):
        Database(path).list_units(army_id=901)


def test_unit_details_use_metadata_parent_for_faction_group(tmp_path: Path) -> None:
    source = metadata_source()
    source["factions"].append(
        {
            "id": 777,
            "parent": 101,
            "name": "Official Sectorial",
            "slug": "official-sectorial",
        }
    )
    document = master(decode_metadata(json.dumps(source).encode(), "metadata.json"))
    document["units"]["1"]["shared"]["canonical"] = 101
    document["armyLists"]["777"] = {
        "_meta": {"slug": "source-sectorial", "kind": "sectorial"},
        "unitIds": [1],
    }
    document["units"]["1"]["byArmy"]["777"] = {}

    normalized = normalize_master(document)
    path = tmp_path / "infinity.db"
    export_database(normalized, path)

    details = Database(path).get_unit(1)

    assert details is not None
    faction = {
        "id": 101,
        "name": "Official First",
        "slug": "official-first",
    }
    assert details["main_faction"] == faction
    armies = {army["id"]: army for army in details["armies"]}
    assert armies[101]["faction"] == faction
    assert armies[777]["faction"] == faction


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


def test_build_discovers_required_sidecar_metadata(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "101-first.json").write_text(
        json.dumps({"version": "test", "units": [{"id": 1, "name": "Unit"}]}), encoding="utf-8"
    )
    (source / "metadata.json").write_text(json.dumps(metadata_source()), encoding="utf-8")
    output = tmp_path / "generated"
    assert main(["build", str(source), "--output-dir", str(output)]) == 0
    assert "Skipped non-Army JSON files: metadata.json" not in capsys.readouterr().err
    with sqlite3.connect(output / "infinity.db") as connection:
        assert connection.execute("SELECT name FROM army_lists").fetchone()[0] == "Official First"
        assert connection.execute("SELECT COUNT(*) FROM metadata_factions").fetchone()[0] == 2


def test_build_rejects_a_source_without_metadata(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "101-first.json").write_text(
        json.dumps({"version": "test", "units": [{"id": 1, "name": "Unit"}]}), encoding="utf-8"
    )

    output = tmp_path / "generated"
    assert main(["build", str(source), "--output-dir", str(output)]) == 1
    assert not (output / "infinity.db").exists()


def test_database_import_rejects_normalized_data_without_metadata(
    tmp_path: Path,
) -> None:
    data = normalize_master(
        {
            "_meta": {"format": "Infinity Army merged JSON", "formatVersion": 1},
            "armyLists": {},
            "units": {},
        }
    )
    with pytest.raises(ValueError, match="required Army metadata"):
        export_database(data, tmp_path / "infinity.db")


def test_build_discovers_unique_metadata_inside_zip(tmp_path: Path) -> None:
    archive = tmp_path / "source.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("army/101-first.json", json.dumps({"version": "test", "units": []}))
        output.writestr("army/metadata.json", json.dumps(metadata_source()))
    output_dir = tmp_path / "generated"
    assert main(["build", str(archive), "--output-dir", str(output_dir)]) == 0
    normalized = json.loads((output_dir / "normalized.json").read_text(encoding="utf-8"))
    assert normalized["armyMetadata"]["sourceFile"] == "metadata.json"
