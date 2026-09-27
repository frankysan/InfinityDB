from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from tools.asset_validation import validate_asset_set
from tools.stage_full_asset_bundle import (
    AssetBundleError,
    download_asset_bundle,
    stage_asset_bundle,
)

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>'
BROWSER_PATHS = [
    "armies/panoceania/101-panoceania.svg",
    "units/panoceania/1-fusiliers.svg",
    "orders/regular.svg",
    "orders/irregular.svg",
    "orders/impetuous.svg",
    "orders/tactical.svg",
    "orders/lieutenant.svg",
    "characteristics/peripheral.svg",
    "characteristics/hackable.svg",
    "characteristics/cube.svg",
    "characteristics/cube-2.svg",
]


def _static_root(tmp_path: Path) -> Path:
    static = tmp_path / "static"
    static.mkdir()
    return static


def _publication_manifest(
    path: Path, published_paths: list[str], browser_paths: list[str]
) -> Path:
    digest = hashlib.sha256(SVG.encode()).hexdigest()
    armies = {
        str(index): relative
        for index, relative in enumerate(browser_paths, start=1)
        if relative.startswith("armies/")
    }
    units = {
        f"unit-{index}": relative
        for index, relative in enumerate(browser_paths, start=1)
        if relative.startswith("units/")
    }
    static = {
        f"static-{index}": relative
        for index, relative in enumerate(browser_paths, start=1)
        if relative.startswith(("orders/", "characteristics/"))
    }
    document = {
        "format": "InfinityDB symbol publication mapping",
        "formatVersion": 2,
        "summary": {"publishedBytes": len(SVG.encode()) * len(published_paths)},
        "publishedSha256ByPath": {relative: digest for relative in published_paths},
        "factionIdToPublishedPath": armies,
        "unitSlugToPublishedPath": units,
        "unitProfileLogoToPublishedPath": {},
        "staticKeyToPublishedPath": static,
        "browserUsageSummary": {
            "browserReferencedAssetCount": len(set(browser_paths)),
            "unreferencedPublishedAssetCount": len(set(published_paths) - set(browser_paths)),
        },
    }
    path.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _bundle(path: Path, members: list[str]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for member in members:
            archive.writestr(member, SVG)
    return path


def test_stage_asset_bundle_installs_complete_published_set(tmp_path: Path) -> None:
    static = _static_root(tmp_path)
    browser_expected = BROWSER_PATHS
    published_expected = [*browser_expected, "units/panoceania/2-future-variant.svg"]
    archive = _bundle(tmp_path / "assets.zip", published_expected)

    manifest = _publication_manifest(
        tmp_path / "symbol-publication.json", published_expected, browser_expected
    )
    validation = stage_asset_bundle(
        archive, static, publication_manifest=manifest
    )

    assert validation.complete
    assert validation.present_count == validation.expected_count == len(published_expected)
    assert validation.browser_expected_count == len(browser_expected)
    assert validation.unreferenced_published_count == 1
    assert validate_asset_set(static, publication_manifest=manifest).complete
    for relative in published_expected:
        assert (static / relative).is_file()


def test_stage_asset_bundle_failure_preserves_existing_assets(tmp_path: Path) -> None:
    static = _static_root(tmp_path)
    existing = static / "armies" / "legacy.svg"
    existing.parent.mkdir()
    existing.write_text(SVG, encoding="utf-8")
    browser_expected = BROWSER_PATHS
    archive = _bundle(tmp_path / "partial.zip", browser_expected[:-1])
    manifest = _publication_manifest(
        tmp_path / "symbol-publication.json", browser_expected, browser_expected
    )

    with pytest.raises(AssetBundleError, match="does not satisfy published contract"):
        stage_asset_bundle(archive, static, publication_manifest=manifest)

    assert existing.is_file()
    assert not (static / browser_expected[0]).exists()


def test_stage_asset_bundle_ignores_legacy_publication_inventory(tmp_path: Path) -> None:
    static = _static_root(tmp_path)
    archive = _bundle(
        tmp_path / "legacy.zip",
        [*BROWSER_PATHS, "symbol-inventory.json"],
    )
    manifest = _publication_manifest(
        tmp_path / "symbol-publication.json", BROWSER_PATHS, BROWSER_PATHS
    )

    validation = stage_asset_bundle(archive, static, publication_manifest=manifest)

    assert validation.complete
    assert not (static / "symbol-inventory.json").exists()


def test_stage_asset_bundle_rejects_other_root_metadata(tmp_path: Path) -> None:
    static = _static_root(tmp_path)
    archive = _bundle(tmp_path / "metadata.zip", [*BROWSER_PATHS, "metadata.json"])
    manifest = _publication_manifest(
        tmp_path / "symbol-publication.json", BROWSER_PATHS, BROWSER_PATHS
    )

    with pytest.raises(AssetBundleError, match="outside published asset categories"):
        stage_asset_bundle(archive, static, publication_manifest=manifest)


def test_stage_asset_bundle_rejects_path_escape(tmp_path: Path) -> None:
    static = _static_root(tmp_path)
    archive = _bundle(tmp_path / "unsafe.zip", ["../escape.svg"])

    with pytest.raises(AssetBundleError, match="escapes the asset root"):
        stage_asset_bundle(archive, static)

    assert not (tmp_path / "escape.svg").exists()


def test_download_asset_bundle_requires_pinned_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = b"private asset bundle"

    def fake_urlopen(*args: object, **kwargs: object) -> io.BytesIO:
        return io.BytesIO(payload)

    monkeypatch.setattr("tools.stage_full_asset_bundle.urlopen", fake_urlopen)
    destination = tmp_path / "assets.zip"
    digest = hashlib.sha256(payload).hexdigest()

    download_asset_bundle("https://example.invalid/assets.zip", digest, destination)
    assert destination.read_bytes() == payload

    with pytest.raises(AssetBundleError, match="SHA-256 does not match"):
        download_asset_bundle("https://example.invalid/assets.zip", "0" * 64, destination)
    assert not destination.exists()


def test_download_asset_bundle_rejects_non_https_redirect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class RedirectedResponse(io.BytesIO):
        def geturl(self) -> str:
            return "http://example.invalid/assets.zip"

    monkeypatch.setattr(
        "tools.stage_full_asset_bundle.urlopen",
        lambda *args, **kwargs: RedirectedResponse(b"bundle"),
    )

    destination = tmp_path / "assets.zip"
    digest = hashlib.sha256(b"bundle").hexdigest()
    with pytest.raises(AssetBundleError, match="redirected to a non-HTTPS URL"):
        download_asset_bundle("https://example.invalid/assets.zip", digest, destination)
    assert not destination.exists()
