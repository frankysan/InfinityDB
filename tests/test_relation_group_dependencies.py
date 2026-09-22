from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from infinity_army_data.normalize import normalize_master
from infinity_db.database import Database, export_database


def _normalized_group_dependency() -> dict:
    return normalize_master(
        {
            "_meta": {"format": "Infinity Army merged JSON", "formatVersion": 1},
            "armyMetadata": {
                "sourceFile": "metadata.json",
                "sourceSha256": "test-metadata",
                "data": {"factions": []},
            },
            "armyLists": {
                "101": {
                    "_meta": {"slug": "first", "kind": "faction"},
                    "unitIds": [1],
                    "relations": [
                        {
                            "min": 0,
                            "group": True,
                            "units": [
                                {
                                    "unit": 1,
                                    "profile": 2,
                                    "perParent": 1,
                                    "depends": [
                                        {
                                            "unit": 1,
                                            "profile": 1,
                                            "group": 7,
                                            "min": 2,
                                            "minDependant": 5,
                                            "options": [7, 8],
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            },
            "units": {
                "1": {
                    "shared": {"id": 1, "name": "Alpha Team", "factions": []},
                    "byArmy": {
                        "101": {
                            "profileGroups": [
                                {
                                    "id": 1,
                                    "profiles": [{"id": 1, "name": "Parent"}],
                                    "options": [
                                        {"id": 7, "name": "Parent A"},
                                        {"id": 8, "name": "Parent B"},
                                    ],
                                },
                                {
                                    "id": 2,
                                    "profiles": [{"id": 1, "name": "Child"}],
                                    "options": [{"id": 1, "name": "Child"}],
                                },
                            ]
                        }
                    },
                }
            },
        }
    )


def test_export_materializes_same_logical_profile_group_dependency(tmp_path: Path) -> None:
    path = tmp_path / "infinity.db"
    export_database(_normalized_group_dependency(), path)

    Database(path).validate()
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT army_id, relation_id, min_count, max_count, is_group "
            "FROM application_unit_group_dependency_constraints"
        ).fetchall() == [(101, 1, 0, None, 1)]
        assert connection.execute(
            "SELECT source_unit_id, logical_unit_id, group_id, per_parent "
            "FROM application_unit_group_dependency_members"
        ).fetchall() == [(1, 1, 2, 1)]
        assert connection.execute(
            "SELECT source_unit_id, logical_unit_id, group_id, source_group_selector, "
            "min_count, min_dependant, options "
            "FROM application_unit_group_dependency_targets"
        ).fetchall() == [(1, 1, 1, 7, 2, 5, "[7,8]")]
        assert connection.execute(
            "SELECT count(*) FROM application_unit_constraints"
        ).fetchone() == (0,)


def test_unit_detail_exposes_profile_group_dependency(tmp_path: Path) -> None:
    path = tmp_path / "infinity.db"
    export_database(_normalized_group_dependency(), path)

    unit = Database(path).get_unit(1)
    assert unit is not None
    assert unit["group_dependencies"] == [
        {
            "army_id": 101,
            "relation_id": 1,
            "min_count": 0,
            "max_count": None,
            "is_group": True,
            "members": [
                {
                    "source_unit_id": 1,
                    "logical_unit_id": 1,
                    "group_id": 2,
                    "per_parent": 1,
                    "dependencies": [
                        {
                            "source_unit_id": 1,
                            "logical_unit_id": 1,
                            "group_id": 1,
                            "source_group_selector": 7,
                            "min_count": 2,
                            "min_dependant": 5,
                            "options": [7, 8],
                        }
                    ],
                }
            ],
        }
    ]


def test_group_dependency_requires_profile_group_coordinates(tmp_path: Path) -> None:
    normalized = _normalized_group_dependency()
    dependency = normalized["tables"]["relation_dependencies"][0]
    dependency["profile_id"] = 99
    path = tmp_path / "infinity.db"
    export_database(normalized, path)

    Database(path).validate()
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT count(*) FROM application_unit_group_dependency_constraints"
        ).fetchone() == (0,)


def test_database_validation_rejects_tampered_group_dependency(tmp_path: Path) -> None:
    path = tmp_path / "infinity.db"
    export_database(_normalized_group_dependency(), path)

    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE application_unit_group_dependency_members SET group_id = 9"
        )
        connection.commit()

    with pytest.raises(ValueError, match="materialized Unit profile-group dependencies"):
        Database(path).validate()
