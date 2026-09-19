from __future__ import annotations

import copy
from pathlib import Path

import pytest

from infinity_db.display_identities import (
    DisplayIdentityError,
    display_identity_metadata,
    load_display_identity_curated,
    parse_display_identity_curated,
    parse_display_identity_metadata,
)


def test_tracked_display_identity_curated_round_trips_with_hash() -> None:
    curated = load_display_identity_curated()

    assert curated.canonical_faction_display_armies
    metadata = display_identity_metadata(curated)
    reparsed = parse_display_identity_metadata(
        metadata["displayIdentityCurated"],
        metadata["displayIdentityCuratedSha256"],
    )
    assert reparsed.document == curated.document
    assert dict(reparsed.canonical_faction_display_armies) == dict(
        curated.canonical_faction_display_armies
    )


def test_display_identity_curated_rejects_duplicate_source_identity() -> None:
    document = load_display_identity_curated().document
    duplicate = copy.deepcopy(document["mappings"][0])
    document["mappings"].append(duplicate)

    with pytest.raises(DisplayIdentityError, match="duplicate canonical faction id"):
        parse_display_identity_curated(document)


def test_display_identity_metadata_rejects_wrong_hash() -> None:
    curated = load_display_identity_curated()

    with pytest.raises(DisplayIdentityError, match="hash does not match"):
        parse_display_identity_metadata(curated.document, "0" * 64)


def test_normalized_display_identity_is_validated_against_pinned_curated_data() -> None:
    from infinity_army_data.availability import annotate_availability_semantics
    from infinity_army_data.normalize import normalize_master
    from infinity_db.database.importer import validate_input

    curated = load_display_identity_curated()
    canonical_faction_id, display_army_id = next(
        iter(curated.canonical_faction_display_armies.items())
    )
    data = normalize_master(
        {
            "_meta": {"format": "Infinity Army merged JSON", "formatVersion": 1},
            "armyMetadata": {
                "sourceFile": "metadata.json",
                "sourceSha256": "test-metadata",
                "data": {"factions": []},
            },
            "armyLists": {
                str(display_army_id): {
                    "_meta": {"slug": "display-group", "kind": "faction"},
                    "unitIds": [1],
                }
            },
            "units": {
                "1": {
                    "shared": {
                        "id": 1,
                        "name": "Display identity test",
                        "canonical": canonical_faction_id,
                        "factions": [display_army_id],
                    },
                    "byArmy": {str(display_army_id): {}},
                }
            },
        },
        display_army_overrides=curated.canonical_faction_display_armies,
    )
    annotate_availability_semantics(data)
    data.update(display_identity_metadata(curated))

    validate_input(data)
    data["tables"]["units"][0]["display_army_id"] = None
    with pytest.raises(ValueError, match="does not match pinned curated data"):
        validate_input(data)


def test_repository_exposes_curated_display_identity_without_changing_main_identity(
    tmp_path: Path,
) -> None:
    from infinity_army_data.availability import annotate_availability_semantics
    from infinity_army_data.normalize import normalize_master
    from infinity_db.database import Database, export_database

    curated = load_display_identity_curated()
    canonical_faction_id, display_army_id = next(
        iter(curated.canonical_faction_display_armies.items())
    )
    display_name = "Curated display grouping"
    display_slug = "curated-display-grouping"
    data = normalize_master(
        {
            "_meta": {"format": "Infinity Army merged JSON", "formatVersion": 1},
            "armyMetadata": {
                "sourceFile": "metadata.json",
                "sourceSha256": "test-metadata",
                "data": {
                    "factions": [
                        {
                            "id": display_army_id,
                            "name": display_name,
                            "slug": display_slug,
                        }
                    ]
                },
            },
            "armyLists": {
                str(display_army_id): {
                    "_meta": {"slug": display_slug, "kind": "faction"},
                    "unitIds": [1],
                }
            },
            "units": {
                "1": {
                    "shared": {
                        "id": 1,
                        "name": "Curated display identity test",
                        "canonical": canonical_faction_id,
                        "factions": [display_army_id],
                    },
                    "byArmy": {str(display_army_id): {}},
                }
            },
        },
        display_army_overrides=curated.canonical_faction_display_armies,
    )
    annotate_availability_semantics(data)
    data.update(display_identity_metadata(curated))
    path = tmp_path / "display.db"
    export_database(data, path)

    database = Database(path)
    listed = database.list_units(mercs=True)["items"][0]
    detail = database.get_unit(1)
    assert detail is not None
    for unit in (listed, detail):
        assert unit["main_army_id"] is None
        assert unit["display_army_id"] == curated.canonical_faction_display_armies[
            canonical_faction_id
        ]
        assert unit["display_army_name"] == display_name
        assert unit["display_faction"] == {
            "id": display_army_id,
            "name": display_name,
            "slug": display_slug,
        }
