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
    document = {
        "format": "InfinityDB symbol publication mapping",
        "formatVersion": 2,
        "summary": {"publishedBytes": len(SVG.encode()) * len(published)},
        "publishedSha256ByPath": {relative: digest for relative in published},
        "factionIdToPublishedPath": {
            "1": relative for relative in browser if relative.startswith("armies/")
        },
        "unitSlugToPublishedPath": {
            "unit": relative for relative in browser if relative.startswith("units/")
        },
        "unitProfileLogoToPublishedPath": {},
        "staticKeyToPublishedPath": {
            "static": relative
            for relative in browser
            if relative.startswith(("orders/", "characteristics/"))
        },
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
