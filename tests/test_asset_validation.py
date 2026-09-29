from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

import pytest

from tools.asset_validation import (
    AssetValidationError,
    browser_asset_paths,
    select_asset_mode,
    validate_asset_set,
)

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>'
BROWSER_PATHS = (
    "armies/panoceania/101-test.svg",
    "units/panoceania/1-test-unit.svg",
    "orders/regular.svg",
    "characteristics/cube.svg",
)


def _write_svg(static: Path, relative: str, body: str = SVG) -> None:
    path = static / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _write_manifest(
    path: Path,
    expected: tuple[str, ...] | list[str],
    *,
    browser_paths: tuple[str, ...] | list[str] | None = None,
) -> Path:
    if browser_paths is None:
        browser_paths = expected
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
        "summary": {"publishedBytes": len(SVG.encode()) * len(expected)},
        "publishedSha256ByPath": {relative: digest for relative in expected},
        "factionIdToPublishedPath": armies,
        "unitSlugToPublishedPath": units,
        "unitProfileLogoToPublishedPath": {},
        "staticKeyToPublishedPath": static,
        "browserUsageSummary": {
            "browserReferencedAssetCount": len(set(browser_paths)),
            "unreferencedPublishedAssetCount": len(set(expected) - set(browser_paths)),
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_tracked_symbol_manifest_defines_a_nonempty_browser_asset_contract() -> None:
    publication_manifest = Path("data/manifests/symbol-publication.json")

    expected = browser_asset_paths(publication_manifest)

    assert any(path.parts[0] == "armies" for path in expected)
    assert any(path.parts[0] == "units" for path in expected)
    assert any(path.parts[0] == "orders" for path in expected)
    assert any(path.parts[0] == "characteristics" for path in expected)
    assert PurePosixPath("orders/regular.svg") in expected
    assert PurePosixPath("characteristics/cube.svg") in expected
    assert PurePosixPath("orders/cube.svg") not in expected


def test_asset_validation_distinguishes_absent_partial_complete_and_invalid(
    tmp_path: Path,
) -> None:
    static = tmp_path / "static"
    static.mkdir()
    publication_manifest = tmp_path / "symbol-publication.json"
    published_expected = (*BROWSER_PATHS, "units/panoceania/2-future-variant.svg")

    assert (
        validate_asset_set(static, publication_manifest=publication_manifest).state
        == "absent"
    )

    _write_manifest(
        publication_manifest,
        published_expected,
        browser_paths=BROWSER_PATHS,
    )
    _write_svg(static, published_expected[0])
    partial = validate_asset_set(static, publication_manifest=publication_manifest)
    assert partial.state == "partial"
    assert partial.missing
    assert partial.expected_count == len(published_expected)
    assert partial.browser_expected_count == len(BROWSER_PATHS)

    for relative in published_expected:
        _write_svg(static, relative)
    complete = validate_asset_set(static, publication_manifest=publication_manifest)
    assert complete.state == "complete"
    assert complete.present_count == complete.expected_count == len(published_expected)
    assert (
        complete.browser_present_count
        == complete.browser_expected_count
        == len(BROWSER_PATHS)
    )
    assert complete.unreferenced_published_count == 1

    _write_svg(static, published_expected[-1], "not svg")
    invalid = validate_asset_set(static, publication_manifest=publication_manifest)
    assert invalid.state == "invalid"
    assert invalid.invalid


def test_asset_validation_requires_publication_manifest_when_assets_exist(
    tmp_path: Path,
) -> None:
    static = tmp_path / "static"
    static.mkdir()
    _write_svg(static, BROWSER_PATHS[0])
    publication_manifest = tmp_path / "missing-symbol-publication.json"

    validation = validate_asset_set(static, publication_manifest=publication_manifest)

    assert validation.state == "invalid"
    assert validation.invalid
    assert "manifest is missing" in validation.invalid[0]


def test_asset_validation_rejects_unexpected_and_hash_mismatched_assets(
    tmp_path: Path,
) -> None:
    static = tmp_path / "static"
    static.mkdir()
    publication_manifest = _write_manifest(
        tmp_path / "symbol-publication.json", BROWSER_PATHS
    )
    for relative in BROWSER_PATHS:
        _write_svg(static, relative)

    extra = "units/panoceania/unlisted.svg"
    _write_svg(static, extra)
    unexpected = validate_asset_set(static, publication_manifest=publication_manifest)
    assert unexpected.state == "invalid"
    assert unexpected.unexpected == (extra,)

    (static / extra).unlink()
    _write_svg(
        static,
        BROWSER_PATHS[0],
        '<svg xmlns="http://www.w3.org/2000/svg"><path/></svg>',
    )
    mismatch = validate_asset_set(static, publication_manifest=publication_manifest)
    assert mismatch.state == "invalid"
    assert any("SHA-256 mismatch" in row for row in mismatch.invalid)


def test_auto_mode_falls_back_only_when_assets_and_manifest_are_absent(
    tmp_path: Path,
) -> None:
    static = tmp_path / "static"
    static.mkdir()
    publication_manifest = tmp_path / "symbol-publication.json"

    selection = select_asset_mode(
        "auto",
        static,
        publication_manifest=publication_manifest,
    )
    assert selection.effective == "off"
    assert not selection.include_full_assets

    _write_manifest(publication_manifest, BROWSER_PATHS)
    _write_svg(static, BROWSER_PATHS[0])
    with pytest.raises(AssetValidationError, match="partial"):
        select_asset_mode(
            "auto",
            static,
            publication_manifest=publication_manifest,
        )


def test_required_mode_requires_complete_published_and_browser_sets(
    tmp_path: Path,
) -> None:
    static = tmp_path / "static"
    static.mkdir()
    publication_manifest = tmp_path / "symbol-publication.json"
    published_expected = (*BROWSER_PATHS, "units/panoceania/2-future-variant.svg")

    with pytest.raises(AssetValidationError, match="no published"):
        select_asset_mode(
            "required",
            static,
            publication_manifest=publication_manifest,
        )

    _write_manifest(
        publication_manifest,
        published_expected,
        browser_paths=BROWSER_PATHS,
    )
    for relative in published_expected:
        _write_svg(static, relative)
    selection = select_asset_mode(
        "required",
        static,
        publication_manifest=publication_manifest,
    )

    assert selection.effective == "full"
    assert selection.include_full_assets
    assert selection.validation is not None
    assert selection.validation.complete
    assert "published SVGs" in selection.description()
    assert "browser-referenced" in selection.description()
    assert "1 published not yet browser-referenced" in selection.description()


def test_tracked_symbol_publication_is_fully_browser_addressable() -> None:
    static = Path("src/infinity_db/web/static")
    publication_manifest = Path("data/manifests/symbol-publication.json")

    validation = validate_asset_set(
        static, publication_manifest=publication_manifest
    )

    assert validation.complete
    assert validation.browser_expected_count == validation.expected_count
    assert validation.expected_count > 0
    assert validation.unreferenced_published_count == 0
