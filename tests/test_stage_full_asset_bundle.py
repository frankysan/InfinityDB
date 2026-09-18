from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import pytest

from tools.asset_validation import expected_asset_paths, validate_asset_set
from tools.stage_full_asset_bundle import (
    AssetBundleError,
    download_asset_bundle,
    stage_asset_bundle,
)

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>'


def _static_root(tmp_path: Path) -> Path:
    static = tmp_path / "static"
    static.mkdir()
    (static / "army-symbols.js").write_text(
        'const armySymbols = new Map([[101, "panoceania/101-panoceania.svg"]]);\n',
        encoding="utf-8",
    )
    (static / "unit-symbol-map.js").write_text(
        'const unitSymbolSlugs = new Map([["fusiliers", "panoceania/1-fusiliers"]]);\n',
        encoding="utf-8",
    )
    return static


def _bundle(path: Path, members: list[str]) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for member in members:
            archive.writestr(member, SVG)
    return path


def test_stage_asset_bundle_installs_complete_published_set(tmp_path: Path) -> None:
    static = _static_root(tmp_path)
    expected = [path.as_posix() for path in expected_asset_paths(static)]
    archive = _bundle(tmp_path / "assets.zip", expected)

    validation = stage_asset_bundle(archive, static)

    assert validation.complete
    assert validation.present_count == validation.expected_count == len(expected)
    assert validate_asset_set(static).complete
    for relative in expected:
        assert (static / relative).is_file()


def test_stage_asset_bundle_failure_preserves_existing_assets(tmp_path: Path) -> None:
    static = _static_root(tmp_path)
    existing = static / "armies" / "legacy.svg"
    existing.parent.mkdir()
    existing.write_text(SVG, encoding="utf-8")
    expected = [path.as_posix() for path in expected_asset_paths(static)]
    archive = _bundle(tmp_path / "partial.zip", expected[:-1])

    with pytest.raises(AssetBundleError, match="does not satisfy published contract"):
        stage_asset_bundle(archive, static)

    assert existing.is_file()
    assert not (static / expected[0]).exists()


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
