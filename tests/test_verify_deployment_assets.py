from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import tools.verify_deployment_assets as deployment_assets
from infinity_db.cli import main as infinity_db_main
from infinity_db.deployment_provenance import (
    DeploymentProvenanceError,
    validate_database_symbol_provenance,
)
from tools.verify_deployment_assets import (
    DeploymentAssetError,
    upgrade_legacy_publication_binding,
    verify_deployment_assets,
)

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>'


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_publication(
    project_root: Path, *, army_sha256: str = "a" * 64
) -> tuple[Path, Path, dict]:
    static = project_root / "src" / "infinity_db" / "web" / "static"
    static.mkdir(parents=True)
    expected = (
        "armies/panoceania/101-test.svg",
        "units/panoceania/1-test-unit.svg",
        "orders/regular.svg",
        "orders/irregular.svg",
        "orders/impetuous.svg",
        "orders/tactical.svg",
        "orders/lieutenant.svg",
        "characteristics/peripheral.svg",
        "characteristics/hackable.svg",
        "characteristics/cube.svg",
        "characteristics/cube-2.svg",
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
                "summary": {
                    "publishedAssetCount": len(expected),
                    "publishedBytes": len(SVG.encode()) * len(expected),
                },
                "factionIdToPublishedPath": {"101": expected[0]},
                "unitSlugToPublishedPath": {"test-unit": expected[1]},
                "unitProfileLogoToPublishedPath": {},
                "staticKeyToPublishedPath": {
                    relative.rsplit("/", 1)[-1].removesuffix(".svg"): relative
                    for relative in expected[2:]
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

    def artifact(path: Path) -> dict[str, str]:
        return {
            "name": path.name,
            "path": path.relative_to(project_root).as_posix(),
            "sha256": _sha256(path),
        }

    manifest = {
        "formatVersion": 8,
        "snapshot": {"armyArtifact": {"sha256": army_sha256}},
        "processing": {
            "publication": {
                "status": "passed",
                "summary": {
                    "publishedAssetCount": len(expected),
                    "publishedBytes": len(SVG.encode()) * len(expected),
                },
                "publicationManifest": artifact(publication_manifest),
            }
        },
    }
    manifest_path = project_root / "data" / "manifests" / "army-symbol-build.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("{}\n", encoding="utf-8")
    return manifest_path, static, manifest


def _legacy_publication(manifest: dict) -> dict:
    publication = manifest["processing"]["publication"]
    publication.pop("publicationManifest", None)
    for field in ("inventory", "armyMap", "unitMap"):
        publication[field] = {
            "name": f"{field}.legacy",
            "path": f"legacy/{field}",
            "sha256": "0" * 64,
        }
    return manifest


def test_upgrade_legacy_publication_binding_writes_rebound_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path, static, manifest = _write_publication(tmp_path)
    _legacy_publication(manifest)
    monkeypatch.setattr(deployment_assets, "load_symbol_manifest", lambda path: manifest)

    rebound = json.loads(json.dumps(manifest))
    rebound["processing"]["publication"]["publicationManifest"] = {"sha256": "1" * 64}
    monkeypatch.setattr(
        deployment_assets,
        "add_publication_manifest_binding",
        lambda *args, **kwargs: rebound,
    )
    written: dict[str, object] = {}

    def capture_write(document: dict, path: Path) -> Path:
        written["document"] = document
        written["path"] = path
        return path

    monkeypatch.setattr(deployment_assets, "write_symbol_manifest", capture_write)

    assert upgrade_legacy_publication_binding(
        manifest_path, static, project_root=tmp_path
    )
    assert written == {"document": rebound, "path": manifest_path}


def test_upgrade_legacy_publication_binding_leaves_current_binding_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path, static, manifest = _write_publication(tmp_path)
    monkeypatch.setattr(deployment_assets, "load_symbol_manifest", lambda path: manifest)
    monkeypatch.setattr(
        deployment_assets,
        "write_symbol_manifest",
        lambda *_args, **_kwargs: pytest.fail("current binding must not be rewritten"),
    )

    assert not upgrade_legacy_publication_binding(
        manifest_path, static, project_root=tmp_path
    )


def test_upgrade_legacy_publication_binding_rejects_summary_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path, static, manifest = _write_publication(tmp_path)
    _legacy_publication(manifest)
    manifest["processing"]["publication"]["summary"]["publishedBytes"] += 1
    monkeypatch.setattr(deployment_assets, "load_symbol_manifest", lambda path: manifest)

    with pytest.raises(DeploymentAssetError, match="publishedBytes does not match"):
        upgrade_legacy_publication_binding(
            manifest_path, static, project_root=tmp_path
        )


def test_deployment_assets_require_manifest_bound_complete_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path, static, manifest = _write_publication(tmp_path)
    monkeypatch.setattr(deployment_assets, "load_symbol_manifest", lambda path: manifest)
    monkeypatch.setattr(deployment_assets, "validate_database_symbol_provenance", lambda *_: None)

    validation = verify_deployment_assets(
        manifest_path,
        static,
        project_root=tmp_path,
    )

    assert validation.complete
    assert validation.present_count == validation.expected_count


def test_deployment_assets_reject_nonterminal_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path, static, manifest = _write_publication(tmp_path)
    manifest["formatVersion"] = 7
    monkeypatch.setattr(deployment_assets, "load_symbol_manifest", lambda path: manifest)
    monkeypatch.setattr(deployment_assets, "validate_database_symbol_provenance", lambda *_: None)

    with pytest.raises(DeploymentAssetError, match="terminal published"):
        verify_deployment_assets(manifest_path, static, project_root=tmp_path)


def test_deployment_assets_reject_tampered_publication_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path, static, manifest = _write_publication(tmp_path)
    monkeypatch.setattr(deployment_assets, "load_symbol_manifest", lambda path: manifest)
    monkeypatch.setattr(deployment_assets, "validate_database_symbol_provenance", lambda *_: None)
    publication_manifest = tmp_path / "data" / "manifests" / "symbol-publication.json"
    publication_manifest.write_text("{}\n", encoding="utf-8")

    with pytest.raises(DeploymentAssetError, match="publicationManifest SHA-256"):
        verify_deployment_assets(manifest_path, static, project_root=tmp_path)


def test_deployment_assets_reject_missing_published_svg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path, static, manifest = _write_publication(tmp_path)
    monkeypatch.setattr(deployment_assets, "load_symbol_manifest", lambda path: manifest)
    (static / "units" / "panoceania" / "1-test-unit.svg").unlink()

    with pytest.raises(DeploymentAssetError, match="does not satisfy"):
        verify_deployment_assets(manifest_path, static, project_root=tmp_path)


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


def test_deployment_rejects_valid_smoke_database_for_production_symbols(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    smoke_database, _ = _build_fixture_database(tmp_path, "smoke")
    _, production_sha256 = _build_fixture_database(tmp_path, "production")
    manifest_path, static, manifest = _write_publication(tmp_path, army_sha256=production_sha256)
    monkeypatch.setattr(deployment_assets, "load_symbol_manifest", lambda path: manifest)

    with pytest.raises(DeploymentProvenanceError, match="does not match promoted symbol"):
        verify_deployment_assets(
            manifest_path, static, project_root=tmp_path, database_path=smoke_database
        )


def test_deployment_accepts_matching_database_and_symbol_provenance(tmp_path: Path) -> None:
    database, archive_sha256 = _build_fixture_database(tmp_path, "production")

    assert validate_database_symbol_provenance(
        database, {"snapshot": {"armyArtifact": {"sha256": archive_sha256}}}
    ) == archive_sha256
