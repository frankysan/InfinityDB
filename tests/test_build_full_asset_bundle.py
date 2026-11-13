from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from tools.build_full_asset_bundle import FullAssetBundleBuildError, build_full_asset_bundle
from tools.stage_full_asset_bundle import stage_asset_bundle

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>'


def _manifest(path: Path, published: list[str]) -> Path:
    digest = hashlib.sha256(SVG.encode()).hexdigest()
    browser = published[:1]
    faction_path = next((relative for relative in browser if relative.startswith("armies/")), None)
    unit_path = next((relative for relative in browser if relative.startswith("units/")), None)
    static_path = next(
        (
            relative
            for relative in browser
            if relative.startswith(("orders/", "characteristics/"))
        ),
        None,
    )
    document = {
        "format": "InfinityDB symbol publication mapping",
        "formatVersion": 2,
        "summary": {"publishedBytes": len(SVG.encode()) * len(published)},
        "publishedSha256ByPath": {relative: digest for relative in published},
        "factionIdToPublishedPath": {"1": faction_path} if faction_path else {},
        "unitSlugToPublishedPath": {"unit": unit_path} if unit_path else {},
        "unitProfileLogoToPublishedPath": {},
        "staticKeyToPublishedPath": {"static": static_path} if static_path else {},
        "browserUsageSummary": {
            "browserReferencedAssetCount": len(browser),
            "unreferencedPublishedAssetCount": len(published) - len(browser),
        },
    }
    path.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _publication(tmp_path: Path) -> tuple[Path, Path, list[str]]:
    static = tmp_path / "static"
    published = [
        "armies/panoceania.svg",
        "units/fusiliers.svg",
        "orders/regular.svg",
    ]
    for relative in published:
        target = static / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(SVG, encoding="utf-8")
    manifest = _manifest(tmp_path / "symbol-publication.json", published)
    return static, manifest, published


def test_build_full_asset_bundle_is_exact_and_deterministic(tmp_path: Path) -> None:
    static, manifest, published = _publication(tmp_path)
    first, first_digest, count = build_full_asset_bundle(
        tmp_path / "first.zip",
        static_root=static,
        publication_manifest=manifest,
    )
    second, second_digest, second_count = build_full_asset_bundle(
        tmp_path / "second.zip",
        static_root=static,
        publication_manifest=manifest,
    )

    assert count == second_count == len(published)
    assert first.read_bytes() == second.read_bytes()
    assert first_digest == second_digest == hashlib.sha256(first.read_bytes()).hexdigest()
    with zipfile.ZipFile(first) as archive:
        assert archive.namelist() == sorted(published)
        for info in archive.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.compress_type == zipfile.ZIP_DEFLATED


def test_built_bundle_is_accepted_by_staging_contract(tmp_path: Path) -> None:
    static, manifest, published = _publication(tmp_path)
    archive, _digest, _count = build_full_asset_bundle(
        tmp_path / "assets.zip",
        static_root=static,
        publication_manifest=manifest,
    )
    staged = tmp_path / "staged"

    validation = stage_asset_bundle(
        archive,
        staged,
        publication_manifest=manifest,
    )

    assert validation.complete
    assert sorted(
        path.relative_to(staged).as_posix()
        for path in staged.rglob("*.svg")
    ) == sorted(published)


def test_full_asset_bundle_rebuild_replaces_selected_final_zip_only(
    tmp_path: Path,
) -> None:
    static, manifest, published = _publication(tmp_path)
    destination = tmp_path / "full-assets.zip"
    first, first_digest, _ = build_full_asset_bundle(
        destination, static_root=static, publication_manifest=manifest,
    )
    before = first.read_bytes()
    assert first_digest == hashlib.sha256(before).hexdigest()
    second, second_digest, _ = build_full_asset_bundle(
        destination, static_root=static, publication_manifest=manifest,
    )
    assert second == first
    assert second.read_bytes() == before
    assert second_digest == first_digest
    assert not (tmp_path / ".full-assets.zip.tmp").exists()


def test_full_asset_bundle_preserves_another_builds_staging(
    tmp_path: Path,
) -> None:
    static, manifest, _ = _publication(tmp_path)
    destination = tmp_path / "full-assets.zip"
    staging = tmp_path / ".full-assets.zip.tmp"
    previous = b"another bundle build is already staging"
    staging.write_bytes(previous)
    with pytest.raises(FullAssetBundleBuildError, match="Could not build"):
        build_full_asset_bundle(
            destination, static_root=static, publication_manifest=manifest,
        )
    assert staging.read_bytes() == previous
    assert not destination.exists()


def test_full_asset_bundle_rejects_symlink_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    static, manifest, _ = _publication(tmp_path)
    destination = tmp_path / "full-assets.zip"
    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path, "is_symlink",
        lambda path: path == destination or original_is_symlink(path),
    )
    with pytest.raises(FullAssetBundleBuildError, match="symlink"):
        build_full_asset_bundle(
            destination, static_root=static, publication_manifest=manifest,
        )
    assert not destination.exists()
    assert not (tmp_path / ".full-assets.zip.tmp").exists()


def test_full_asset_bundle_cleans_only_owned_staging_after_write_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    static, manifest, _ = _publication(tmp_path)
    destination = tmp_path / "full-assets.zip"
    before = b"previous selected bundle destination"
    destination.write_bytes(before)
    original_writestr = zipfile.ZipFile.writestr

    def failed_writestr(self, *args, **kwargs):
        raise OSError("simulated staging failure")

    monkeypatch.setattr(zipfile.ZipFile, "writestr", failed_writestr)
    with pytest.raises(FullAssetBundleBuildError, match="simulated staging failure"):
        build_full_asset_bundle(
            destination, static_root=static, publication_manifest=manifest,
        )
    monkeypatch.setattr(zipfile.ZipFile, "writestr", original_writestr)
    assert destination.read_bytes() == before
    assert not (tmp_path / ".full-assets.zip.tmp").exists()


def test_build_full_asset_bundle_rejects_incomplete_publication(tmp_path: Path) -> None:
    static, manifest, published = _publication(tmp_path)
    (static / published[-1]).unlink()
    destination = tmp_path / "assets.zip"

    with pytest.raises(FullAssetBundleBuildError, match="not complete and valid"):
        build_full_asset_bundle(
            destination,
            static_root=static,
            publication_manifest=manifest,
        )

    assert not destination.exists()


def test_build_full_asset_bundle_rejects_unexpected_svg(tmp_path: Path) -> None:
    static, manifest, _published = _publication(tmp_path)
    unexpected = static / "units" / "unexpected.svg"
    unexpected.write_text(SVG, encoding="utf-8")

    with pytest.raises(FullAssetBundleBuildError, match="unexpected 1"):
        build_full_asset_bundle(
            tmp_path / "assets.zip",
            static_root=static,
            publication_manifest=manifest,
        )
