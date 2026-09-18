from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from tools import reorganize_symbols
from tools.reorganize_symbols import publish_symbols, slugify

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
        "formatVersion": 7,
        "snapshot": {
            "armyArtifact": {
                "name": snapshot.name,
                "sha256": reorganize_symbols.sha256_file(snapshot),
            },
            "symbolArtifact": {"name": "SYMBOLS test.zip", "sha256": "a" * 64},
        },
        "assets": assets,
        "references": references,
        "processing": {
            "duplicateDetection": {"canonicalByArchivePath": canonical},
            "compression": {"status": "passed"},
        },
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


def test_build_publication_maps_many_references_to_canonical_assets(tmp_path: Path) -> None:
    snapshot = tmp_path / "army.zip"
    _write_snapshot(snapshot)
    manifest = _manifest(snapshot)
    compressed = tmp_path / "compressed"
    _write_compressed(compressed)
    staging = tmp_path / "staging"

    report, summary = reorganize_symbols._build_publication(
        manifest=manifest,
        snapshot_index=reorganize_symbols._load_snapshot_index(snapshot),
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
    assert report["staticKeyToPublishedPath"]["cube2"] == "orders/cube-2.svg"
    assert (staging / "units" / "panoceania" / "1-mech-engineer.svg").is_file()
    assert (staging / "armies" / "panoceania" / "101-panoceania.svg").is_file()
    assert (staging / "orders" / "cube-2.svg").is_file()

    army_map = (staging / "army-symbols.js").read_text(encoding="utf-8")
    assert '[101, "panoceania/101-panoceania.svg"]' in army_map
    assert '[102, "panoceania/101-panoceania.svg"]' in army_map
    unit_map = (staging / "unit-symbol-map.js").read_text(encoding="utf-8")
    assert '["mech-engineer", "panoceania/1-mech-engineer"]' in unit_map
    assert '["chung-hee-jeong", "panoceania/1-mech-engineer"]' in unit_map



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
    canonical = manifest["processing"]["duplicateDetection"]["canonicalByArchivePath"]
    canonical["units/u1-duplicate.svg"] = "units/u1.svg"
    canonical["units/u1-alternate.svg"] = "units/u1-alternate.svg"

    compressed = tmp_path / "compressed"
    _write_compressed(compressed)
    (compressed / "units" / "u1-alternate.svg").write_bytes(SVG)
    staging = tmp_path / "staging"

    report, summary = reorganize_symbols._build_publication(
        manifest=manifest,
        snapshot_index=reorganize_symbols._load_snapshot_index(snapshot),
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
    assert (staging / primary_path).is_file()
    assert (staging / alternate_path).is_file()

    unit_map = (staging / "unit-symbol-map.js").read_text(encoding="utf-8")
    assert '["mech-engineer", "panoceania/1-mech-engineer"]' in unit_map
    assert "mech-engineer--2-1" not in unit_map


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
    manifest["processing"]["duplicateDetection"]["canonicalByArchivePath"][
        "units/u1-sectorial.svg"
    ] = "units/u1-sectorial.svg"

    compressed = tmp_path / "compressed"
    _write_compressed(compressed)
    (compressed / "units" / "u1-sectorial.svg").write_bytes(SVG)
    staging = tmp_path / "staging"

    report, _summary = reorganize_symbols._build_publication(
        manifest=manifest,
        snapshot_index=reorganize_symbols._load_snapshot_index(snapshot),
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
    manifest["processing"]["duplicateDetection"]["canonicalByArchivePath"][
        "units/u1-conflict.svg"
    ] = "units/u1-conflict.svg"

    compressed = tmp_path / "compressed"
    _write_compressed(compressed)
    (compressed / "units" / "u1-conflict.svg").write_bytes(SVG)

    with pytest.raises(
        ValueError, match=r"Published symbol path collision: units/panoceania/1-mech-engineer\.svg"
    ):
        reorganize_symbols._build_publication(
            manifest=manifest,
            snapshot_index=reorganize_symbols._load_snapshot_index(snapshot),
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
    manifest["processing"]["duplicateDetection"]["canonicalByArchivePath"].pop(
        "units/u1.svg"
    )
    manifest["processing"]["duplicateDetection"]["canonicalByArchivePath"][
        "units/u2.svg"
    ] = "units/u2.svg"
    compressed = tmp_path / "compressed"
    _write_compressed(compressed)
    (compressed / "units" / "u1.svg").unlink()
    (compressed / "units" / "u2.svg").write_bytes(SVG)
    staging = tmp_path / "staging"

    report, summary = reorganize_symbols._build_publication(
        manifest=manifest,
        snapshot_index=reorganize_symbols._load_snapshot_index(snapshot),
        compressed_root=compressed,
        staging_static=staging,
    )

    assert summary["sourceAssetCount"] == 5
    assert "mech-engineer" not in report["unitSlugToPublishedPath"]
    assert report["unavailableSourceAssets"][0]["url"] == missing_url

def test_publication_failure_restores_previous_generated_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot = tmp_path / "army.zip"
    _write_snapshot(snapshot)
    manifest = _manifest(snapshot)
    compressed = tmp_path / "work" / "compressed"
    _write_compressed(compressed)

    static = tmp_path / "static"
    old_army = static / "armies" / "old.svg"
    old_army.parent.mkdir(parents=True)
    old_army.write_bytes(b"old army")
    old_orders = static / "orders" / "old.svg"
    old_orders.parent.mkdir(parents=True)
    old_orders.write_bytes(b"old order")
    old_units = static / "units" / "old.svg"
    old_units.parent.mkdir(parents=True)
    old_units.write_bytes(b"old unit")
    (static / "army-symbols.js").write_text("old army map\n", encoding="utf-8")
    (static / "unit-symbol-map.js").write_text("old unit map\n", encoding="utf-8")

    report = tmp_path / "reports" / "SYMBOLS test--aaaaaaaaaaaa" / "publication-map.json"
    report.parent.mkdir(parents=True)
    report.write_text("old report\n", encoding="utf-8")

    monkeypatch.setattr(reorganize_symbols, "load_symbol_manifest", lambda _path: manifest)
    monkeypatch.setattr(
        reorganize_symbols,
        "add_publication",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("manifest failure")),
    )

    with pytest.raises(ValueError, match="manifest failure"):
        publish_symbols(
            army_snapshot=snapshot,
            build_manifest_path=tmp_path / "manifest.json",
            work_root=tmp_path / "work",
            reports_base=tmp_path / "reports",
            static_root=static,
            project_root=tmp_path,
        )

    assert old_army.read_bytes() == b"old army"
    assert old_orders.read_bytes() == b"old order"
    assert old_units.read_bytes() == b"old unit"
    assert (static / "army-symbols.js").read_text(encoding="utf-8") == "old army map\n"
    assert (static / "unit-symbol-map.js").read_text(encoding="utf-8") == "old unit map\n"
    assert report.read_text(encoding="utf-8") == "old report\n"


def test_publication_backup_failure_restores_already_moved_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    snapshot = tmp_path / "army.zip"
    _write_snapshot(snapshot)
    manifest = _manifest(snapshot)
    compressed = tmp_path / "work" / "compressed"
    _write_compressed(compressed)

    static = tmp_path / "static"
    for category in ("armies", "orders", "units"):
        path = static / category / "old.svg"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"old {category}".encode())
    (static / "army-symbols.js").write_text("old army map\n", encoding="utf-8")
    (static / "unit-symbol-map.js").write_text("old unit map\n", encoding="utf-8")

    monkeypatch.setattr(reorganize_symbols, "load_symbol_manifest", lambda _path: manifest)
    original_replace = Path.replace
    failing_path = static / "orders"

    def flaky_replace(self: Path, target: Path) -> Path:
        if self == failing_path:
            raise OSError("backup failure")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", flaky_replace)

    with pytest.raises(OSError, match="backup failure"):
        publish_symbols(
            army_snapshot=snapshot,
            build_manifest_path=tmp_path / "manifest.json",
            work_root=tmp_path / "work",
            reports_base=tmp_path / "reports",
            static_root=static,
            project_root=tmp_path,
        )

    assert (static / "armies" / "old.svg").read_bytes() == b"old armies"
    assert (static / "orders" / "old.svg").read_bytes() == b"old orders"
    assert (static / "units" / "old.svg").read_bytes() == b"old units"
    assert (static / "army-symbols.js").read_text(encoding="utf-8") == "old army map\n"
    assert (static / "unit-symbol-map.js").read_text(encoding="utf-8") == "old unit map\n"
