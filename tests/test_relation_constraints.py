from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from infinity_army_data.normalize import normalize_master
from infinity_db.database import Database, export_database
from infinity_db.identities import load_identity_config, parse_identity_config


def _normalized_relations() -> dict:
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
                    "unitIds": [1, 2, 3],
                    "relations": [
                        {"min": 1, "max": 1, "units": [{"unit": 1}, {"unit": 2}]},
                        {"min": 1, "max": 1, "units": [{"unit": 1}, {"unit": 3}]},
                        {"min": 2, "max": 3, "group": True, "units": [{"unit": 3}]},
                        {
                            "min": 1,
                            "max": 1,
                            "units": [{"unit": 1, "profile": 1}, {"unit": 3}],
                        },
                    ],
                }
            },
            "units": {
                "1": {
                    "shared": {"id": 1, "name": "Alpha", "factions": []},
                    "byArmy": {"101": {}},
                },
                "2": {
                    "shared": {"id": 2, "name": "Alpha Reinforcement", "factions": []},
                    "byArmy": {"101": {}},
                },
                "3": {
                    "shared": {"id": 3, "name": "Beta", "factions": []},
                    "byArmy": {"101": {}},
                },
            },
        }
    )


def _identity_config():
    document = load_identity_config().document
    document["units"]["groups"].append(
        {
            "canonical_id": 1,
            "source_ids": [1, 2],
            "reason": "Test-only same-logical relation coverage",
        }
    )
    return parse_identity_config(document)


def test_export_materializes_only_selector_free_relation_constraints(tmp_path: Path) -> None:
    path = tmp_path / "infinity.db"
    export_database(_normalized_relations(), path, identity_config=_identity_config())

    Database(path).validate()
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT army_id, relation_id, family, min_count, max_count, is_group "
            "FROM application_unit_constraints ORDER BY relation_id"
        ).fetchall() == [
            (101, 1, "same-logical-cross-context-exclusive", 1, 1, None),
            (101, 2, "cross-logical-shared-cardinality", 1, 1, None),
            (101, 3, "single-logical-cardinality", 2, 3, 1),
        ]
        assert connection.execute(
            "SELECT relation_id, relation_unit_id, source_unit_id, logical_unit_id "
            "FROM application_unit_constraint_members "
            "ORDER BY relation_id, relation_unit_id"
        ).fetchall() == [
            (1, 1, 1, 1),
            (1, 2, 2, 1),
            (2, 1, 1, 1),
            (2, 2, 3, 3),
            (3, 1, 3, 3),
        ]


def test_unit_detail_exposes_canonical_selection_constraints(tmp_path: Path) -> None:
    path = tmp_path / "infinity.db"
    export_database(_normalized_relations(), path, identity_config=_identity_config())

    alpha = Database(path).get_unit(1)
    beta = Database(path).get_unit(3)
    assert alpha is not None
    assert beta is not None

    assert [item["relation_id"] for item in alpha["selection_constraints"]] == [1, 2]
    same_logical = alpha["selection_constraints"][0]
    assert same_logical["family"] == "same-logical-cross-context-exclusive"
    assert [
        (item["source_unit_id"], item["logical_unit_id"])
        for item in same_logical["members"]
    ] == [(1, 1), (2, 1)]

    assert [item["relation_id"] for item in beta["selection_constraints"]] == [2, 3]
    assert beta["selection_constraints"][1]["family"] == "single-logical-cardinality"
    assert beta["selection_constraints"][1]["min_count"] == 2
    assert beta["selection_constraints"][1]["max_count"] == 3


def test_database_validation_rejects_tampered_relation_constraint(tmp_path: Path) -> None:
    path = tmp_path / "infinity.db"
    export_database(_normalized_relations(), path, identity_config=_identity_config())

    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE application_unit_constraints SET min_count = 9 "
            "WHERE army_id = 101 AND relation_id = 2"
        )
        connection.commit()

    with pytest.raises(ValueError, match="materialized Unit selection constraints"):
        Database(path).validate()


def _normalized_selection_equivalent_profile_relation() -> dict:
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
                    "unitIds": [1, 3],
                    "relations": [
                        {
                            "min": 1,
                            "max": 1,
                            "units": [
                                {"unit": 1, "profile": 1},
                                {"unit": 3, "profile": 1},
                            ],
                        }
                    ],
                }
            },
            "units": {
                "1": {
                    "shared": {"id": 1, "name": "Alpha", "factions": []},
                    "byArmy": {
                        "101": {
                            "profileGroups": [
                                {
                                    "id": 1,
                                    "profiles": [
                                        {"id": 1, "name": "Alpha", "ava": 1},
                                        {"id": 2, "name": "Alpha inactive", "ava": -1},
                                    ],
                                    "options": [{"id": 1, "name": "Alpha"}],
                                }
                            ]
                        }
                    },
                },
                "3": {
                    "shared": {"id": 3, "name": "Beta", "factions": []},
                    "byArmy": {
                        "101": {
                            "profileGroups": [
                                {
                                    "id": 1,
                                    "profiles": [
                                        {"id": 1, "name": "Beta", "ava": 1},
                                        {"id": 2, "name": "Beta inactive", "ava": -1},
                                    ],
                                    "options": [{"id": 1, "name": "Beta"}],
                                }
                            ]
                        }
                    },
                },
            },
        }
    )


def test_export_materializes_selection_equivalent_profile_selector_constraint(
    tmp_path: Path,
) -> None:
    path = tmp_path / "infinity.db"
    export_database(_normalized_selection_equivalent_profile_relation(), path)

    Database(path).validate()
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT relation_id, family, min_count, max_count "
            "FROM application_unit_constraints"
        ).fetchall() == [(1, "cross-logical-shared-cardinality", 1, 1)]
        assert connection.execute(
            "SELECT relation_unit_id, source_unit_id, logical_unit_id "
            "FROM application_unit_constraint_members ORDER BY relation_unit_id"
        ).fetchall() == [(1, 1, 1), (2, 3, 3)]


def test_profile_selector_constraint_requires_selection_equivalence(tmp_path: Path) -> None:
    normalized = _normalized_selection_equivalent_profile_relation()
    normalized["tables"]["profiles"][0]["ava"] = -1
    path = tmp_path / "infinity.db"
    export_database(normalized, path)

    Database(path).validate()
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT count(*) FROM application_unit_constraints"
        ).fetchone() == (0,)
