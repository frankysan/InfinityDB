from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from tools import symbol_publication
from tools.symbol_publication import slugify

SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>'


def _write_snapshot(path: Path) -> None:
    metadata = {
        "factions": [
            {"id": 101, "name": "PanOceania", "slug": "panoceania", "parent": 101},
            {"id": 102, "name": "Sectorial", "slug": "sectorial", "parent": 101},
        ]
    }
    army = {
        "units": [
            {"id": 1, "slug": "mech-engineer", "canonical": 101},
            {"id": 2, "slug": "chung-hee-jeong", "canonical": 101},
            {"id": 3, "slug": "sectorial-remote", "canonical": 102},
        ]
    }
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("metadata.json", json.dumps(metadata))
        archive.writestr("101-panoceania.json", json.dumps(army))


def _manifest(snapshot: Path) -> dict[str, Any]:
    urls = {
        "u1": "https://example.invalid/u1.svg",
        "u2": "https://example.invalid/u2.svg",
        "f1": "https://example.invalid/f1.svg",
        "f2": "https://example.invalid/f2.svg",
        "regular": "https://example.invalid/regular.svg",
        "cube2": "https://example.invalid/cube2.svg",
    }
    assets = [
        {"url": urls["u1"], "archivePath": "units/u1.svg"},
        {"url": urls["u2"], "archivePath": "units/u2.svg"},
        {"url": urls["f1"], "archivePath": "factions/f1.svg"},
        {"url": urls["f2"], "archivePath": "factions/f2.svg"},
        {"url": urls["regular"], "archivePath": "static/orders/regular.svg"},
        {"url": urls["cube2"], "archivePath": "static/characteristics/cube2.svg"},
    ]
    references = [
        {
            "kind": "unit-profile",
            "authoritative": True,
            "sourceDocument": "101-panoceania.json",
            "assetUrl": urls["u1"],
            "armyId": 101,
            "unitId": 1,
            "unitSlug": "mech-engineer",
        },
        {
            "kind": "unit-profile",
            "authoritative": True,
            "sourceDocument": "101-panoceania.json",
            "assetUrl": urls["u2"],
            "armyId": 101,
            "unitId": 2,
            "unitSlug": "chung-hee-jeong",
        },
        {
            "kind": "faction",
            "authoritative": True,
            "sourceDocument": "metadata.json",
            "assetUrl": urls["f1"],
            "factionId": 101,
            "factionSlug": "panoceania",
        },
        {
            "kind": "faction",
            "authoritative": True,
            "sourceDocument": "metadata.json",
            "assetUrl": urls["f2"],
            "factionId": 102,
            "factionSlug": "sectorial",
        },
        {
            "kind": "static",
            "authoritative": True,
            "sourceDocument": "static-symbols.json",
            "assetUrl": urls["regular"],
            "staticKey": "regular",
            "staticCategory": "orders",
        },
        {
            "kind": "static",
            "authoritative": True,
            "sourceDocument": "static-symbols.json",
            "assetUrl": urls["cube2"],
            "staticKey": "cube2",
            "staticCategory": "characteristics",
        },
    ]
    canonical = {
        "units/u1.svg": "units/u1.svg",
        "units/u2.svg": "units/u1.svg",
        "factions/f1.svg": "factions/f1.svg",
        "factions/f2.svg": "factions/f1.svg",
        "static/orders/regular.svg": "static/orders/regular.svg",
        "static/characteristics/cube2.svg": "static/characteristics/cube2.svg",
    }
    return {
        "armyArtifact": {
            "name": snapshot.name,
            "sha256": symbol_publication.sha256_file(snapshot),
        },
        "assets": assets,
        "references": references,
        "canonicalByArchivePath": canonical,
    }


def _write_compressed(root: Path) -> None:
    for relative in (
        "units/u1.svg",
        "factions/f1.svg",
        "static/orders/regular.svg",
        "static/characteristics/cube2.svg",
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(SVG)


def test_slugify_matches_asset_sanitization() -> None:
    assert slugify("Special:Recent Changes?new=1*") == "special-recent-changes-new-1"


def test_semantic_profile_mapping_promotes_cross_unit_majority_override() -> None:
    references = [
        {
            "unit_id": 1,
            "unit_slug": "uhlan",
            "profile_name": "Crabbot Ancillary Remote Unit",
            "published_path": "peripherals/panoceania/crabbot.svg",
        },
        {
            "unit_id": 2,
            "unit_slug": "jotum",
            "profile_name": "CRABBOT Ancillary Remote Unit",
            "published_path": "peripherals/panoceania/crabbot.svg",
        },
        {
            "unit_id": 3,
            "unit_slug": "cutter",
            "profile_name": "Crabbot Ancillary Remote Unit",
            "published_path": "units/panoceania/cutter.svg",
        },
        {
            "unit_id": 3,
            "unit_slug": "cutter",
            "profile_name": "Crabbot Ancillary Remote Unit",
            "published_path": "units/panoceania/cutter.svg",
        },
        {
            "unit_id": 4,
            "unit_slug": "spec-ops",
            "profile_name": "Initial Profile",
            "published_path": "units/ariadna/spec-ops-variant.svg",
        },
        {
            "unit_id": 5,
            "unit_slug": "other-spec-ops",
            "profile_name": "Initial Profile",
            "published_path": "units/ariadna/other-spec-ops.svg",
        },
    ]
    unit_mapping = {
        "uhlan": "units/panoceania/uhlan.svg",
        "jotum": "units/panoceania/jotum.svg",
        "cutter": "units/panoceania/cutter.svg",
        "spec-ops": "units/ariadna/spec-ops.svg",
        "other-spec-ops": "units/ariadna/other-spec-ops.svg",
    }

    assert symbol_publication._semantic_profile_mapping(references, unit_mapping) == {
        "ancillary crabbot remote": "peripherals/panoceania/crabbot.svg"
    }


def test_build_publication_maps_many_references_to_canonical_assets(tmp_path: Path) -> None:
    snapshot = tmp_path / "army.zip"
    _write_snapshot(snapshot)
    manifest = _manifest(snapshot)
    compressed = tmp_path / "compressed"
    _write_compressed(compressed)
    staging = tmp_path / "staging"

    report, summary = symbol_publication.build_publication(
        assets=manifest["assets"],
        references=manifest["references"],
        canonical_by_source=manifest["canonicalByArchivePath"],
        army_artifact=manifest["armyArtifact"],
        unavailable_assets=manifest.get("unavailableAssets", []),
        snapshot_index=symbol_publication.load_snapshot_index(snapshot),
        compressed_root=compressed,
        staging_static=staging,
    )

    assert summary == {
        "sourceAssetCount": 6,
        "canonicalAssetCount": 4,
        "publishedAssetCount": 4,
        "factionMappingCount": 2,
        "unitMappingCount": 2,
        "staticMappingCount": 2,
        "publishedBytes": len(SVG) * 4,
    }
    source_map = report["sourceArchivePathToPublishedPath"]
    assert source_map["units/u2.svg"] == "units/panoceania/1-mech-engineer.svg"
    assert source_map["factions/f2.svg"] == "armies/panoceania/101-panoceania.svg"
    assert report["staticKeyToPublishedPath"]["regular"] == "orders/regular.svg"
    assert report["staticKeyToPublishedPath"]["cube2"] == "characteristics/cube-2.svg"
    assert (staging / "units" / "panoceania" / "1-mech-engineer.svg").is_file()
    assert (staging / "armies" / "panoceania" / "101-panoceania.svg").is_file()
    assert (staging / "characteristics" / "cube-2.svg").is_file()


def test_publication_prefers_standard_unit_identity_over_reinforcement(tmp_path: Path) -> None:
    snapshot = tmp_path / "army.zip"
    metadata = {
        "factions": [
            {"id": 301, "name": "Ariadna", "slug": "ariadna", "parent": 301},
            {
                "id": 399,
                "name": "L'Equipe Argent",
                "slug": "l-equipe-argent",
                "parent": 399,
            },
        ]
    }
    with zipfile.ZipFile(snapshot, "w") as archive:
        archive.writestr("metadata.json", json.dumps(metadata))
        archive.writestr(
            "303-caledonia.json",
            json.dumps(
                {
                    "units": [
                        {
                            "id": 1555,
                            "slug": "wolfgang-amadeus-wolff",
                            "canonical": 301,
                        }
                    ]
                }
            ),
        )
        archive.writestr(
            "399-l-equipe-argent.json",
            json.dumps(
                {
                    "units": [
                        {
                            "id": 1634,
                            "slug": "reinf-wolfgang-amadeus-wolff",
                            "canonical": 399,
                        }
                    ]
                }
            ),
        )

    standard_url = "https://example.invalid/wolfgang.svg"
    reinforcement_url = "https://example.invalid/reinf-wolfgang.svg"
    canonical = "units/wolfgang.svg"
    manifest = {
        "armyArtifact": {
            "name": snapshot.name,
            "sha256": symbol_publication.sha256_file(snapshot),
        },
        "assets": [
            {"url": standard_url, "archivePath": canonical},
            {"url": reinforcement_url, "archivePath": "units/reinf-wolfgang.svg"},
        ],
        "references": [
            {
                "kind": "unit-profile",
                "authoritative": True,
                "sourceDocument": "303-caledonia.json",
                "assetUrl": standard_url,
                "armyId": 303,
                "unitId": 1555,
                "unitSlug": "wolfgang-amadeus-wolff",
            },
            {
                "kind": "unit-profile",
                "authoritative": True,
                "sourceDocument": "399-l-equipe-argent.json",
                "assetUrl": reinforcement_url,
                "armyId": 399,
                "unitId": 1634,
                "unitSlug": "reinf-wolfgang-amadeus-wolff",
            },
        ],
        "canonicalByArchivePath": {
            canonical: canonical,
            "units/reinf-wolfgang.svg": canonical,
        },
    }
    compressed = tmp_path / "compressed"
    (compressed / canonical).parent.mkdir(parents=True, exist_ok=True)
    (compressed / canonical).write_bytes(SVG)
    staging = tmp_path / "staging"

    report, _summary = symbol_publication.build_publication(
        assets=manifest["assets"],
        references=manifest["references"],
        canonical_by_source=manifest["canonicalByArchivePath"],
        army_artifact=manifest["armyArtifact"],
        unavailable_assets=manifest.get("unavailableAssets", []),
        snapshot_index=symbol_publication.load_snapshot_index(snapshot),
        compressed_root=compressed,
        staging_static=staging,
    )

    expected = "units/ariadna/1555-wolfgang-amadeus-wolff--army-303.svg"
    assert report["sourceArchivePathToPublishedPath"][canonical] == expected
    assert report["sourceArchivePathToPublishedPath"]["units/reinf-wolfgang.svg"] == expected
    assert report["unitSlugToPublishedPath"]["wolfgang-amadeus-wolff"] == expected
    assert report["unitSlugToPublishedPath"]["reinf-wolfgang-amadeus-wolff"] == expected
    assert (staging / expected).is_file()


def test_publication_preserves_distinct_unit_profile_symbols(tmp_path: Path) -> None:
    snapshot = tmp_path / "army.zip"
    _write_snapshot(snapshot)
    manifest = _manifest(snapshot)

    duplicate_url = "https://example.invalid/u1-duplicate.svg"
    alternate_url = "https://example.invalid/u1-alternate.svg"
    manifest["references"][0]["jsonPath"] = (
        "$.units[0].profileGroups[0].profiles[0].logo"
    )
    manifest["assets"].extend(
        [
            {"url": duplicate_url, "archivePath": "units/u1-duplicate.svg"},
            {"url": alternate_url, "archivePath": "units/u1-alternate.svg"},
        ]
    )
    manifest["references"].extend(
        [
            {
                "kind": "unit-profile",
                "authoritative": True,
                "sourceDocument": "101-panoceania.json",
                "jsonPath": "$.units[0].profileGroups[0].profiles[1].logo",
                "assetUrl": duplicate_url,
                "armyId": 101,
                "unitId": 1,
                "unitSlug": "mech-engineer",
            },
            {
                "kind": "unit-profile",
                "authoritative": True,
                "sourceDocument": "101-panoceania.json",
                "jsonPath": "$.units[0].profileGroups[1].profiles[0].logo",
                "assetUrl": alternate_url,
                "armyId": 101,
                "unitId": 1,
                "unitSlug": "mech-engineer",
            },
        ]
    )
    canonical = manifest["canonicalByArchivePath"]
    canonical["units/u1-duplicate.svg"] = "units/u1.svg"
    canonical["units/u1-alternate.svg"] = "units/u1-alternate.svg"

    compressed = tmp_path / "compressed"
    _write_compressed(compressed)
    (compressed / "units" / "u1-alternate.svg").write_bytes(SVG)
    staging = tmp_path / "staging"

    report, summary = symbol_publication.build_publication(
        assets=manifest["assets"],
        references=manifest["references"],
        canonical_by_source=manifest["canonicalByArchivePath"],
        army_artifact=manifest["armyArtifact"],
        unavailable_assets=manifest.get("unavailableAssets", []),
        snapshot_index=symbol_publication.load_snapshot_index(snapshot),
        compressed_root=compressed,
        staging_static=staging,
    )

    primary_path = "units/panoceania/1-mech-engineer.svg"
    alternate_path = "units/panoceania/1-mech-engineer--2-1.svg"
    source_map = report["sourceArchivePathToPublishedPath"]
    assert source_map["units/u1.svg"] == primary_path
    assert source_map["units/u1-duplicate.svg"] == primary_path
    assert source_map["units/u1-alternate.svg"] == alternate_path
    assert report["unitSlugToPublishedPath"]["mech-engineer"] == primary_path
    assert summary["publishedAssetCount"] == 5
    assert report["browserUsageSummary"] == {
        "browserReferencedAssetCount": 5,
        "unreferencedPublishedAssetCount": 0,
    }
    assert not (staging / "symbol-inventory.json").exists()
    assert (staging / primary_path).is_file()
    assert (staging / alternate_path).is_file()

    profile_map = report["unitProfileLogoToPublishedPath"]
    assert profile_map[manifest["references"][0]["assetUrl"]] == primary_path
    assert profile_map[manifest["references"][1]["assetUrl"]] == primary_path
    assert profile_map[duplicate_url] == primary_path
    assert profile_map[alternate_url] == alternate_path



def test_publication_names_embedded_peripheral_by_identity(tmp_path: Path) -> None:
    snapshot = tmp_path / "army.zip"
    _write_snapshot(snapshot)
    manifest = _manifest(snapshot)

    crabbot_url = "https://example.invalid/crabbot.svg"
    manifest["references"][0]["jsonPath"] = (
        "$.units[0].profileGroups[0].profiles[0].logo"
    )
    manifest["assets"].append(
        {"url": crabbot_url, "archivePath": "units/crabbot.svg"}
    )
    manifest["references"].append(
        {
            "kind": "unit-profile",
            "authoritative": True,
            "sourceDocument": "101-panoceania.json",
            "jsonPath": "$.units[0].profileGroups[0].profiles[1].logo",
            "assetUrl": crabbot_url,
            "armyId": 101,
            "unitId": 1,
            "unitSlug": "mech-engineer",
            "profileName": "Crabbot Ancillary Remote Unit",
            "peripheralName": "CRABBOT",
        }
    )
    manifest["canonicalByArchivePath"][
        "units/crabbot.svg"
    ] = "units/crabbot.svg"

    compressed = tmp_path / "compressed"
    _write_compressed(compressed)
    (compressed / "units" / "crabbot.svg").write_bytes(SVG)
    staging = tmp_path / "staging"

    report, _summary = symbol_publication.build_publication(
        assets=manifest["assets"],
        references=manifest["references"],
        canonical_by_source=manifest["canonicalByArchivePath"],
        army_artifact=manifest["armyArtifact"],
        unavailable_assets=manifest.get("unavailableAssets", []),
        snapshot_index=symbol_publication.load_snapshot_index(snapshot),
        compressed_root=compressed,
        staging_static=staging,
    )

    peripheral_path = "peripherals/panoceania/crabbot.svg"
    assert report["sourceArchivePathToPublishedPath"]["units/crabbot.svg"] == peripheral_path
    assert report["unitProfileLogoToPublishedPath"][crabbot_url] == peripheral_path
    assert (staging / peripheral_path).is_file()



def test_mixed_role_profile_prefers_normal_unit_owner(tmp_path: Path) -> None:
    snapshot = tmp_path / "army.zip"
    _write_snapshot(snapshot)
    manifest = _manifest(snapshot)

    peripheral_url = "https://example.invalid/chakora-peripheral.svg"
    profile_url = "https://example.invalid/chakora-profile.svg"
    manifest["assets"].extend(
        [
            {"url": peripheral_url, "archivePath": "units/chakora-peripheral.svg"},
            {"url": profile_url, "archivePath": "units/chakora-profile.svg"},
        ]
    )
    manifest["references"].extend(
        [
            {
                "kind": "unit-profile",
                "authoritative": True,
                "sourceDocument": "101-panoceania.json",
                "jsonPath": "$.units[0].profileGroups[1].profiles[0].logo",
                "assetUrl": peripheral_url,
                "armyId": 101,
                "unitId": 1,
                "unitSlug": "mech-engineer",
                "profileName": "CHAKORA SPECBOTS",
                "peripheralName": "CHAKORA SPECBOTS",
            },
            {
                "kind": "unit-profile",
                "authoritative": True,
                "sourceDocument": "101-panoceania.json",
                "jsonPath": "$.units[1].profileGroups[2].profiles[0].logo",
                "assetUrl": profile_url,
                "armyId": 101,
                "unitId": 2,
                "unitSlug": "chung-hee-jeong",
                "profileName": "CHAKORA SPECBOTS",
            },
        ]
    )
    canonical = manifest["canonicalByArchivePath"]
    canonical["units/chakora-peripheral.svg"] = "units/chakora-profile.svg"
    canonical["units/chakora-profile.svg"] = "units/chakora-profile.svg"

    compressed = tmp_path / "compressed"
    _write_compressed(compressed)
    (compressed / "units" / "chakora-profile.svg").write_bytes(SVG)
    staging = tmp_path / "staging"

    report, summary = symbol_publication.build_publication(
        assets=manifest["assets"],
        references=manifest["references"],
        canonical_by_source=manifest["canonicalByArchivePath"],
        army_artifact=manifest["armyArtifact"],
        unavailable_assets=manifest.get("unavailableAssets", []),
        snapshot_index=symbol_publication.load_snapshot_index(snapshot),
        compressed_root=compressed,
        staging_static=staging,
    )

    expected = "units/panoceania/2-chung-hee-jeong--3-1.svg"
    assert report["sourceArchivePathToPublishedPath"][
        "units/chakora-peripheral.svg"
    ] == expected
    assert report["sourceArchivePathToPublishedPath"][
        "units/chakora-profile.svg"
    ] == expected
    assert report["unitProfileLogoToPublishedPath"][peripheral_url] == expected
    assert report["unitProfileLogoToPublishedPath"][profile_url] == expected
    assert (staging / expected).is_file()
    assert not (staging / "peripherals" / "panoceania" / "chakora-specbots.svg").exists()
    assert summary["canonicalAssetCount"] == 5
    assert summary["publishedAssetCount"] == 5


def test_evidenced_mixed_role_name_keeps_variant_art_unit_owned(tmp_path: Path) -> None:
    snapshot = tmp_path / "army.zip"
    _write_snapshot(snapshot)
    manifest = _manifest(snapshot)

    shared_peripheral_url = "https://example.invalid/chakora-shared-peripheral.svg"
    normal_url = "https://example.invalid/chakora-normal.svg"
    variant_peripheral_url = "https://example.invalid/chakora-variant-peripheral.svg"
    manifest["assets"].extend(
        [
            {
                "url": shared_peripheral_url,
                "archivePath": "units/chakora-shared-peripheral.svg",
            },
            {"url": normal_url, "archivePath": "units/chakora-normal.svg"},
            {
                "url": variant_peripheral_url,
                "archivePath": "units/chakora-variant-peripheral.svg",
            },
        ]
    )
    manifest["references"].extend(
        [
            {
                "kind": "unit-profile",
                "authoritative": True,
                "sourceDocument": "101-panoceania.json",
                "jsonPath": "$.units[0].profileGroups[1].profiles[0].logo",
                "assetUrl": shared_peripheral_url,
                "armyId": 101,
                "unitId": 1,
                "unitSlug": "mech-engineer",
                "profileName": "CHAKORA SPECBOTS",
                "peripheralName": "CHAKORA SPECBOTS",
            },
            {
                "kind": "unit-profile",
                "authoritative": True,
                "sourceDocument": "101-panoceania.json",
                "jsonPath": "$.units[1].profileGroups[2].profiles[0].logo",
                "assetUrl": normal_url,
                "armyId": 101,
                "unitId": 2,
                "unitSlug": "chung-hee-jeong",
                "profileName": "CHAKORA SPECBOTS",
            },
            {
                "kind": "unit-profile",
                "authoritative": True,
                "sourceDocument": "101-panoceania.json",
                "jsonPath": "$.units[0].profileGroups[2].profiles[0].logo",
                "assetUrl": variant_peripheral_url,
                "armyId": 101,
                "unitId": 1,
                "unitSlug": "mech-engineer",
                "profileName": "CHAKORA SPECBOTS",
                "peripheralName": "CHAKORA SPECBOTS",
            },
        ]
    )
    canonical = manifest["canonicalByArchivePath"]
    canonical["units/chakora-shared-peripheral.svg"] = "units/chakora-normal.svg"
    canonical["units/chakora-normal.svg"] = "units/chakora-normal.svg"
    canonical["units/chakora-variant-peripheral.svg"] = (
        "units/chakora-variant-peripheral.svg"
    )

    compressed = tmp_path / "compressed"
    _write_compressed(compressed)
    (compressed / "units" / "chakora-normal.svg").write_bytes(SVG)
    (compressed / "units" / "chakora-variant-peripheral.svg").write_bytes(
        b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="1"/></svg>'
    )
    staging = tmp_path / "staging"

    report, summary = symbol_publication.build_publication(
        assets=manifest["assets"],
        references=manifest["references"],
        canonical_by_source=manifest["canonicalByArchivePath"],
        army_artifact=manifest["armyArtifact"],
        unavailable_assets=manifest.get("unavailableAssets", []),
        snapshot_index=symbol_publication.load_snapshot_index(snapshot),
        compressed_root=compressed,
        staging_static=staging,
    )

    shared_path = "units/panoceania/2-chung-hee-jeong--3-1.svg"
    variant_path = "units/panoceania/1-mech-engineer--3-1.svg"
    assert report["sourceArchivePathToPublishedPath"][
        "units/chakora-shared-peripheral.svg"
    ] == shared_path
    assert report["sourceArchivePathToPublishedPath"][
        "units/chakora-normal.svg"
    ] == shared_path
    assert report["sourceArchivePathToPublishedPath"][
        "units/chakora-variant-peripheral.svg"
    ] == variant_path
    assert (staging / shared_path).is_file()
    assert (staging / variant_path).is_file()
    assert not (staging / "peripherals" / "panoceania" / "chakora-specbots.svg").exists()
    assert summary["canonicalAssetCount"] == 6
    assert summary["publishedAssetCount"] == 6



def test_primary_peripheral_unit_publishes_under_main_army(tmp_path: Path) -> None:
    snapshot = tmp_path / "army.zip"
    _write_snapshot(snapshot)
    manifest = _manifest(snapshot)

    palbot_url = "https://example.invalid/palbot.svg"
    manifest["assets"].append(
        {"url": palbot_url, "archivePath": "units/palbot.svg"}
    )
    manifest["references"].append(
        {
            "kind": "unit-profile",
            "authoritative": True,
            "sourceDocument": "101-panoceania.json",
            "jsonPath": "$.units[2].profileGroups[0].profiles[0].logo",
            "assetUrl": palbot_url,
            "armyId": 102,
            "unitId": 3,
            "unitSlug": "sectorial-remote",
            "profileName": "PALBOTS",
            "peripheralName": "PALBOT",
        }
    )
    manifest["canonicalByArchivePath"][
        "units/palbot.svg"
    ] = "units/palbot.svg"

    compressed = tmp_path / "compressed"
    _write_compressed(compressed)
    (compressed / "units" / "palbot.svg").write_bytes(SVG)
    staging = tmp_path / "staging"

    report, _summary = symbol_publication.build_publication(
        assets=manifest["assets"],
        references=manifest["references"],
        canonical_by_source=manifest["canonicalByArchivePath"],
        army_artifact=manifest["armyArtifact"],
        unavailable_assets=manifest.get("unavailableAssets", []),
        snapshot_index=symbol_publication.load_snapshot_index(snapshot),
        compressed_root=compressed,
        staging_static=staging,
    )

    peripheral_path = "peripherals/panoceania/palbot.svg"
    assert report["unitSlugToPublishedPath"]["sectorial-remote"] == peripheral_path
    assert report["sourceArchivePathToPublishedPath"]["units/palbot.svg"] == peripheral_path
    assert (staging / peripheral_path).is_file()



def test_parent_unit_art_is_not_republished_as_peripheral(tmp_path: Path) -> None:
    snapshot = tmp_path / "army.zip"
    _write_snapshot(snapshot)
    manifest = _manifest(snapshot)

    parent = manifest["references"][0]
    parent["jsonPath"] = "$.units[0].profileGroups[0].profiles[0].logo"
    manifest["references"].append(
        {
            "kind": "unit-profile",
            "authoritative": True,
            "sourceDocument": "101-panoceania.json",
            "jsonPath": "$.units[0].profileGroups[0].profiles[1].logo",
            "assetUrl": parent["assetUrl"],
            "armyId": 101,
            "unitId": 1,
            "unitSlug": "mech-engineer",
            "profileName": "Crabbot Ancillary Remote Unit",
            "peripheralName": "CRABBOT",
        }
    )

    compressed = tmp_path / "compressed"
    _write_compressed(compressed)
    staging = tmp_path / "staging"
    report, _summary = symbol_publication.build_publication(
        assets=manifest["assets"],
        references=manifest["references"],
        canonical_by_source=manifest["canonicalByArchivePath"],
        army_artifact=manifest["armyArtifact"],
        unavailable_assets=manifest.get("unavailableAssets", []),
        snapshot_index=symbol_publication.load_snapshot_index(snapshot),
        compressed_root=compressed,
        staging_static=staging,
    )

    parent_path = "units/panoceania/1-mech-engineer.svg"
    assert report["sourceArchivePathToPublishedPath"]["units/u1.svg"] == parent_path
    assert report["unitProfileLogoToPublishedPath"][parent["assetUrl"]] == parent_path
    assert not (staging / "peripherals" / "panoceania" / "crabbot.svg").exists()


@pytest.mark.parametrize(
    ("peripheral_name", "expected_stem"),
    [("REINF: YUDBOTS", "yudbots"), ("REINF. SLAVE DRONES", "slave-drones")],
)
def test_peripheral_public_path_omits_reinforcement_roster_prefix(
    peripheral_name: str, expected_stem: str
) -> None:
    reference = {
        "kind": "unit-profile",
        "authoritative": True,
        "sourceDocument": "799-ank-program.json",
        "jsonPath": "$.units[0].profileGroups[0].profiles[0].logo",
        "assetUrl": "https://example.invalid/peripheral.svg",
        "armyId": 799,
        "unitId": 1732,
        "unitSlug": "reinf-peripheral",
        "profileName": peripheral_name,
        "peripheralName": peripheral_name,
    }
    index = symbol_publication.SnapshotIndex(
        {799: symbol_publication.FactionInfo(799, "ank-program", 799)},
        {("799-ank-program.json", 1732, "reinf-peripheral"): 799},
    )

    assert symbol_publication._peripheral_public_path(reference, index) == (
        f"peripherals/ank-program/{expected_stem}.svg"
    )


def test_reinforcement_peripheral_alias_prefers_normal_name_and_main_army(
    tmp_path: Path,
) -> None:
    snapshot = tmp_path / "army.zip"
    _write_snapshot(snapshot)
    manifest = _manifest(snapshot)

    normal_url = "https://example.invalid/yudbots.svg"
    reinforcement_url = "https://example.invalid/reinf-yudbots.svg"
    manifest["assets"].extend(
        [
            {"url": normal_url, "archivePath": "units/yudbots.svg"},
            {"url": reinforcement_url, "archivePath": "units/reinf-yudbots.svg"},
        ]
    )
    manifest["references"].extend(
        [
            {
                "kind": "unit-profile",
                "authoritative": True,
                "sourceDocument": "701-aleph.json",
                "jsonPath": "$.units[0].profileGroups[0].profiles[0].logo",
                "assetUrl": normal_url,
                "armyId": 701,
                "unitId": 192,
                "unitSlug": "yudbots",
                "profileName": "YUDBOTS",
                "peripheralName": "YUDBOTS",
            },
            {
                "kind": "unit-profile",
                "authoritative": True,
                "sourceDocument": "1001-o-12.json",
                "jsonPath": "$.units[0].profileGroups[0].profiles[0].logo",
                "assetUrl": normal_url,
                "armyId": 1001,
                "unitId": 192,
                "unitSlug": "yudbots",
                "profileName": "YUDBOTS",
                "peripheralName": "YUDBOTS",
            },
            {
                "kind": "unit-profile",
                "authoritative": True,
                "sourceDocument": "799-ank-program.json",
                "jsonPath": "$.units[0].profileGroups[0].profiles[0].logo",
                "assetUrl": reinforcement_url,
                "armyId": 799,
                "unitId": 1732,
                "unitSlug": "reinf-yudbots",
                "profileName": "REINF: YUDBOTS",
                "peripheralName": "REINF: YUDBOTS",
            },
        ]
    )
    canonical = manifest["canonicalByArchivePath"]
    canonical["units/yudbots.svg"] = "units/yudbots.svg"
    canonical["units/reinf-yudbots.svg"] = "units/yudbots.svg"

    compressed = tmp_path / "compressed"
    _write_compressed(compressed)
    (compressed / "units" / "yudbots.svg").write_bytes(SVG)
    staging = tmp_path / "staging"

    base_index = symbol_publication.load_snapshot_index(snapshot)
    factions = dict(base_index.factions)
    factions.update(
        {
            701: symbol_publication.FactionInfo(701, "aleph", 701),
            799: symbol_publication.FactionInfo(799, "ank-program", 799),
            1001: symbol_publication.FactionInfo(1001, "o-12", 1001),
        }
    )
    canonical_factions = dict(base_index.unit_canonical_faction_by_reference)
    canonical_factions.update(
        {
            ("701-aleph.json", 192, "yudbots"): 799,
            ("1001-o-12.json", 192, "yudbots"): 799,
            ("799-ank-program.json", 1732, "reinf-yudbots"): 799,
        }
    )
    index = symbol_publication.SnapshotIndex(factions, canonical_factions)

    report, _summary = symbol_publication.build_publication(
        assets=manifest["assets"],
        references=manifest["references"],
        canonical_by_source=manifest["canonicalByArchivePath"],
        army_artifact=manifest["armyArtifact"],
        unavailable_assets=manifest.get("unavailableAssets", []),
        snapshot_index=index,
        compressed_root=compressed,
        staging_static=staging,
    )

    expected = "peripherals/aleph/yudbots.svg"
    assert report["sourceArchivePathToPublishedPath"]["units/yudbots.svg"] == expected
    assert report["sourceArchivePathToPublishedPath"]["units/reinf-yudbots.svg"] == expected
    assert report["unitSlugToPublishedPath"]["yudbots"] == expected
    assert report["unitSlugToPublishedPath"]["reinf-yudbots"] == expected
    assert (staging / expected).is_file()
    assert not (staging / "peripherals" / "ank-program" / "reinf-yudbots.svg").exists()


def test_distinct_same_name_peripheral_art_keeps_context_variant(tmp_path: Path) -> None:
    snapshot = tmp_path / "army.zip"
    _write_snapshot(snapshot)
    manifest = _manifest(snapshot)

    first_url = "https://example.invalid/staldron-avatar.svg"
    second_url = "https://example.invalid/staldron-juggernaut.svg"
    manifest["references"][0]["jsonPath"] = (
        "$.units[0].profileGroups[0].profiles[0].logo"
    )
    manifest["references"][1]["jsonPath"] = (
        "$.units[1].profileGroups[0].profiles[0].logo"
    )
    manifest["assets"].extend(
        [
            {"url": first_url, "archivePath": "units/staldron-a.svg"},
            {"url": second_url, "archivePath": "units/staldron-b.svg"},
        ]
    )
    manifest["references"].extend(
        [
            {
                "kind": "unit-profile",
                "authoritative": True,
                "sourceDocument": "101-panoceania.json",
                "jsonPath": "$.units[0].profileGroups[0].profiles[1].logo",
                "assetUrl": first_url,
                "armyId": 101,
                "unitId": 1,
                "unitSlug": "mech-engineer",
                "profileName": "STALDRON",
                "peripheralName": "STALDRON",
            },
            {
                "kind": "unit-profile",
                "authoritative": True,
                "sourceDocument": "101-panoceania.json",
                "jsonPath": "$.units[1].profileGroups[0].profiles[1].logo",
                "assetUrl": second_url,
                "armyId": 101,
                "unitId": 2,
                "unitSlug": "chung-hee-jeong",
                "profileName": "STALDRON",
                "peripheralName": "STALDRON",
            },
        ]
    )
    canonical = manifest["canonicalByArchivePath"]
    canonical["units/staldron-a.svg"] = "units/staldron-a.svg"
    canonical["units/staldron-b.svg"] = "units/staldron-b.svg"

    compressed = tmp_path / "compressed"
    _write_compressed(compressed)
    (compressed / "units" / "staldron-a.svg").write_bytes(SVG)
    (compressed / "units" / "staldron-b.svg").write_bytes(SVG)
    staging = tmp_path / "staging"

    report, _summary = symbol_publication.build_publication(
        assets=manifest["assets"],
        references=manifest["references"],
        canonical_by_source=manifest["canonicalByArchivePath"],
        army_artifact=manifest["armyArtifact"],
        unavailable_assets=manifest.get("unavailableAssets", []),
        snapshot_index=symbol_publication.load_snapshot_index(snapshot),
        compressed_root=compressed,
        staging_static=staging,
    )

    first_path = "peripherals/panoceania/staldron.svg"
    second_path = (
        "peripherals/panoceania/staldron--2-chung-hee-jeong-1-2.svg"
    )
    assert report["unitProfileLogoToPublishedPath"][first_url] == first_path
    assert report["unitProfileLogoToPublishedPath"][second_url] == second_path
    assert (staging / first_path).is_file()
    assert (staging / second_path).is_file()



def test_publication_preserves_army_specific_primary_variant(tmp_path: Path) -> None:
    snapshot = tmp_path / "army.zip"
    _write_snapshot(snapshot)
    manifest = _manifest(snapshot)

    primary = manifest["references"][0]
    primary["jsonPath"] = "$.units[0].profileGroups[0].profiles[0].logo"
    variant_url = "https://example.invalid/u1-sectorial.svg"
    manifest["assets"].append(
        {"url": variant_url, "archivePath": "units/u1-sectorial.svg"}
    )
    manifest["references"].append(
        {
            "kind": "unit-profile",
            "authoritative": True,
            "sourceDocument": "101-panoceania.json",
            "jsonPath": "$.units[0].profileGroups[0].profiles[0].logo",
            "assetUrl": variant_url,
            "armyId": 102,
            "unitId": 1,
            "unitSlug": "mech-engineer",
        }
    )
    manifest["canonicalByArchivePath"][
        "units/u1-sectorial.svg"
    ] = "units/u1-sectorial.svg"

    compressed = tmp_path / "compressed"
    _write_compressed(compressed)
    (compressed / "units" / "u1-sectorial.svg").write_bytes(SVG)
    staging = tmp_path / "staging"

    report, _summary = symbol_publication.build_publication(
        assets=manifest["assets"],
        references=manifest["references"],
        canonical_by_source=manifest["canonicalByArchivePath"],
        army_artifact=manifest["armyArtifact"],
        unavailable_assets=manifest.get("unavailableAssets", []),
        snapshot_index=symbol_publication.load_snapshot_index(snapshot),
        compressed_root=compressed,
        staging_static=staging,
    )

    primary_path = "units/panoceania/1-mech-engineer.svg"
    variant_path = "units/panoceania/1-mech-engineer--army-102.svg"
    source_map = report["sourceArchivePathToPublishedPath"]
    assert source_map["units/u1.svg"] == primary_path
    assert source_map["units/u1-sectorial.svg"] == variant_path
    assert report["unitSlugToPublishedPath"]["mech-engineer"] == primary_path
    assert (staging / primary_path).is_file()
    assert (staging / variant_path).is_file()


def test_publication_still_rejects_same_profile_slot_collision(tmp_path: Path) -> None:
    snapshot = tmp_path / "army.zip"
    _write_snapshot(snapshot)
    manifest = _manifest(snapshot)

    conflict_url = "https://example.invalid/u1-conflict.svg"
    manifest["references"][0]["jsonPath"] = (
        "$.units[0].profileGroups[0].profiles[0].logo"
    )
    manifest["assets"].append(
        {"url": conflict_url, "archivePath": "units/u1-conflict.svg"}
    )
    manifest["references"].append(
        {
            "kind": "unit-profile",
            "authoritative": True,
            "sourceDocument": "101-panoceania.json",
            "jsonPath": "$.units[0].profileGroups[0].profiles[0].logo",
            "assetUrl": conflict_url,
            "armyId": 101,
            "unitId": 1,
            "unitSlug": "mech-engineer",
        }
    )
    manifest["canonicalByArchivePath"][
        "units/u1-conflict.svg"
    ] = "units/u1-conflict.svg"

    compressed = tmp_path / "compressed"
    _write_compressed(compressed)
    (compressed / "units" / "u1-conflict.svg").write_bytes(SVG)

    with pytest.raises(
        ValueError, match=r"Published symbol path collision: units/panoceania/1-mech-engineer\.svg"
    ):
        symbol_publication.build_publication(
            assets=manifest["assets"],
            references=manifest["references"],
            canonical_by_source=manifest["canonicalByArchivePath"],
            army_artifact=manifest["armyArtifact"],
            unavailable_assets=manifest.get("unavailableAssets", []),
            snapshot_index=symbol_publication.load_snapshot_index(snapshot),
            compressed_root=compressed,
            staging_static=tmp_path / "staging",
        )


def test_publication_skips_recorded_unavailable_authoritative_reference(tmp_path: Path) -> None:
    snapshot = tmp_path / "army.zip"
    _write_snapshot(snapshot)
    manifest = _manifest(snapshot)
    missing_url = manifest["references"][0]["assetUrl"]
    manifest["assets"] = [row for row in manifest["assets"] if row["url"] != missing_url]
    manifest["unavailableAssets"] = [
        {
            "url": missing_url,
            "sourceFilename": "u1.svg",
            "archivePath": "units/u1.svg",
            "sourceMethod": "network",
            "httpStatus": 404,
        }
    ]
    manifest["canonicalByArchivePath"].pop(
        "units/u1.svg"
    )
    manifest["canonicalByArchivePath"][
        "units/u2.svg"
    ] = "units/u2.svg"
    compressed = tmp_path / "compressed"
    _write_compressed(compressed)
    (compressed / "units" / "u1.svg").unlink()
    (compressed / "units" / "u2.svg").write_bytes(SVG)
    staging = tmp_path / "staging"

    report, summary = symbol_publication.build_publication(
        assets=manifest["assets"],
        references=manifest["references"],
        canonical_by_source=manifest["canonicalByArchivePath"],
        army_artifact=manifest["armyArtifact"],
        unavailable_assets=manifest.get("unavailableAssets", []),
        snapshot_index=symbol_publication.load_snapshot_index(snapshot),
        compressed_root=compressed,
        staging_static=staging,
    )

    assert summary["sourceAssetCount"] == 5
    assert "mech-engineer" not in report["unitSlugToPublishedPath"]
    assert report["unavailableSourceAssets"][0]["url"] == missing_url
