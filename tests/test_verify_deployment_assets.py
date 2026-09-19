from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import tools.verify_deployment_assets as deployment_assets
from tools.asset_validation import PUBLICATION_INVENTORY_FORMAT, PUBLICATION_INVENTORY_VERSION
from tools.verify_deployment_assets import DeploymentAssetError, verify_deployment_assets

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>'


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_publication(project_root: Path) -> tuple[Path, Path, dict]:
    static = project_root / "src" / "infinity_db" / "web" / "static"
    static.mkdir(parents=True)
    army_map = static / "army-symbols.js"
    unit_map = static / "unit-symbol-map.js"
    army_map.write_text(
        'const armySymbols = new Map([[101, "panoceania/101-test.svg"]]);\n',
        encoding="utf-8",
    )
    unit_map.write_text(
        'const unitSymbolSlugs = new Map([["test-unit", "panoceania/1-test-unit"]]);\n',
        encoding="utf-8",
    )

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

    inventory = static / "symbol-inventory.json"
    inventory.write_text(
        json.dumps(
            {
                "format": PUBLICATION_INVENTORY_FORMAT,
                "formatVersion": PUBLICATION_INVENTORY_VERSION,
                "summary": {
                    "publishedAssetCount": len(expected),
                    "browserReferencedAssetCount": len(expected),
                    "unreferencedPublishedAssetCount": 0,
                    "publishedBytes": len(SVG.encode()) * len(expected),
                },
                "publishedSha256ByPath": {relative: digest for relative in expected},
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
        "processing": {
            "publication": {
                "status": "passed",
                "summary": {
                    "publishedAssetCount": len(expected),
                    "publishedBytes": len(SVG.encode()) * len(expected),
                },
                "inventory": artifact(inventory),
                "armyMap": artifact(army_map),
                "unitMap": artifact(unit_map),
            }
        },
    }
    manifest_path = project_root / "data" / "manifests" / "army-symbol-build.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text("{}\n", encoding="utf-8")
    return manifest_path, static, manifest


def test_deployment_assets_require_manifest_bound_complete_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path, static, manifest = _write_publication(tmp_path)
    monkeypatch.setattr(deployment_assets, "load_symbol_manifest", lambda path: manifest)

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

    with pytest.raises(DeploymentAssetError, match="terminal published"):
        verify_deployment_assets(manifest_path, static, project_root=tmp_path)


def test_deployment_assets_reject_tampered_manifest_bound_map(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path, static, manifest = _write_publication(tmp_path)
    monkeypatch.setattr(deployment_assets, "load_symbol_manifest", lambda path: manifest)
    (static / "army-symbols.js").write_text("tampered\n", encoding="utf-8")

    with pytest.raises(DeploymentAssetError, match="armyMap SHA-256"):
        verify_deployment_assets(manifest_path, static, project_root=tmp_path)


def test_deployment_assets_reject_missing_published_svg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path, static, manifest = _write_publication(tmp_path)
    monkeypatch.setattr(deployment_assets, "load_symbol_manifest", lambda path: manifest)
    (static / "units" / "panoceania" / "1-test-unit.svg").unlink()

    with pytest.raises(DeploymentAssetError, match="does not satisfy"):
        verify_deployment_assets(manifest_path, static, project_root=tmp_path)
