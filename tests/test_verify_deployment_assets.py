from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import tools.verify_deployment_assets as deployment_assets
from infinity_db.cli import main as infinity_db_main
from infinity_db.deployment_provenance import (
    DeploymentProvenanceError,
    publication_snapshot_sha256,
    validate_database_symbol_provenance,
)
from tools.verify_deployment_assets import DeploymentAssetError, verify_deployment_assets

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>'


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_publication(
    project_root: Path, *, army_sha256: str = "a" * 64
) -> tuple[Path, Path]:
    static = project_root / "src" / "infinity_db" / "web" / "static"
    static.mkdir(parents=True)
    expected = (
        "armies/panoceania/101-test.svg",
        "units/panoceania/1-test-unit.svg",
        "orders/regular.svg",
        "characteristics/cube.svg",
    )
    digest = hashlib.sha256(SVG.encode()).hexdigest()
    for relative in expected:
        path = static / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(SVG, encoding="utf-8")

    publication_manifest = project_root / "data" / "manifests" / "symbol-publication.json"
    publication_manifest.parent.mkdir(parents=True, exist_ok=True)
    publication_manifest.write_text(
        json.dumps(
            {
                "format": "InfinityDB symbol publication mapping",
                "formatVersion": 2,
                "sourceSnapshot": {
                    "armyArtifact": {
                        "name": "army.zip",
                        "sha256": army_sha256,
                    }
                },
                "summary": {
                    "publishedAssetCount": len(expected),
                    "publishedBytes": len(SVG.encode()) * len(expected),
                },
                "factionIdToPublishedPath": {"101": expected[0]},
                "unitSlugToPublishedPath": {"test-unit": expected[1]},
                "unitProfileLogoToPublishedPath": {},
                "staticKeyToPublishedPath": {
                    "regular": expected[2],
                    "cube": expected[3],
                },
                "publishedSha256ByPath": {relative: digest for relative in expected},
                "browserUsageSummary": {
                    "browserReferencedAssetCount": len(expected),
                    "unreferencedPublishedAssetCount": 0,
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return publication_manifest, static


def _build_fixture_database(tmp_path: Path, name: str) -> tuple[Path, str]:
    source = Path(__file__).resolve().parent / "fixtures" / "deployment-smoke"
    archive = tmp_path / f"{name}.zip"
    import zipfile

    with zipfile.ZipFile(archive, "w") as output:
        for path in source.iterdir():
            output.write(path, path.name)
        output.comment = name.encode("ascii")
    output_dir = tmp_path / name
    assert (
        infinity_db_main(["build", str(archive), "--output-dir", str(output_dir), "--compact"])
        == 0
    )
    return output_dir / "infinity.db", _sha256(archive)


def test_deployment_assets_require_complete_tracked_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    publication_manifest, static = _write_publication(tmp_path)
    monkeypatch.setattr(deployment_assets, "validate_database_symbol_provenance", lambda *_: None)

    class FakeRulesDatabase:
        def __init__(self, path: Path) -> None:
            self.path = path

        def validate(self) -> None:
            pass

    monkeypatch.setattr(deployment_assets, "RulesDatabase", FakeRulesDatabase)
    validation = verify_deployment_assets(
        static,
        database_path=tmp_path / "infinity.db",
        rules_database_path=tmp_path / "rules.db",
        publication_manifest_path=publication_manifest,
    )

    assert validation.complete
    assert validation.present_count == validation.expected_count


def test_deployment_assets_reject_missing_published_svg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    publication_manifest, static = _write_publication(tmp_path)
    (static / "units" / "panoceania" / "1-test-unit.svg").unlink()
    monkeypatch.setattr(deployment_assets, "validate_database_symbol_provenance", lambda *_: None)

    with pytest.raises(DeploymentAssetError, match="does not satisfy"):
        verify_deployment_assets(
            static,
            database_path=tmp_path / "infinity.db",
            rules_database_path=tmp_path / "rules.db",
            publication_manifest_path=publication_manifest,
        )


def test_deployment_assets_validate_rules_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    publication_manifest, static = _write_publication(tmp_path)
    monkeypatch.setattr(deployment_assets, "validate_database_symbol_provenance", lambda *_: None)

    with pytest.raises(ValueError, match="Rules database does not exist"):
        verify_deployment_assets(
            static,
            database_path=tmp_path / "infinity.db",
            rules_database_path=tmp_path / "missing-rules.db",
            publication_manifest_path=publication_manifest,
        )


def test_deployment_rejects_database_for_different_publication_snapshot(tmp_path: Path) -> None:
    smoke_database, _ = _build_fixture_database(tmp_path, "smoke")
    _, production_sha256 = _build_fixture_database(tmp_path, "production")
    publication_manifest, _ = _write_publication(tmp_path, army_sha256=production_sha256)

    with pytest.raises(DeploymentProvenanceError, match="does not match tracked symbol"):
        validate_database_symbol_provenance(smoke_database, publication_manifest)


def test_deployment_accepts_matching_database_and_publication_provenance(tmp_path: Path) -> None:
    database, archive_sha256 = _build_fixture_database(tmp_path, "production")
    publication_manifest, _ = _write_publication(tmp_path, army_sha256=archive_sha256)

    assert validate_database_symbol_provenance(database, publication_manifest) == archive_sha256
    assert publication_snapshot_sha256(publication_manifest) == archive_sha256


def test_deployment_rejects_publication_without_snapshot_provenance(tmp_path: Path) -> None:
    publication_manifest, _ = _write_publication(tmp_path)
    document = json.loads(publication_manifest.read_text(encoding="utf-8"))
    document.pop("sourceSnapshot")
    publication_manifest.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(DeploymentProvenanceError, match="sourceSnapshot.armyArtifact.sha256"):
        publication_snapshot_sha256(publication_manifest)
