from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

import pytest

from tools.asset_validation import (
    PUBLICATION_INVENTORY,
    PUBLICATION_INVENTORY_FORMAT,
    PUBLICATION_INVENTORY_VERSION,
    AssetValidationError,
    browser_asset_paths,
    select_asset_mode,
    validate_asset_set,
)

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>'


def _write_contract(static: Path) -> tuple[str, ...]:
    static.mkdir(parents=True, exist_ok=True)
    (static / "army-symbols.js").write_text(
        'const armySymbols = new Map([[101, "panoceania/101-test.svg"]]);\n',
        encoding="utf-8",
    )
    (static / "unit-symbol-map.js").write_text(
        'const unitSymbolSlugs = new Map([["test-unit", "panoceania/1-test-unit"]]);\n',
        encoding="utf-8",
    )
    return tuple(path.as_posix() for path in browser_asset_paths(static))


def _write_svg(static: Path, relative: str, body: str = SVG) -> None:
    path = static / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _write_inventory(
    static: Path,
    expected: tuple[str, ...] | list[str],
    *,
    browser_count: int | None = None,
) -> None:
    digest = hashlib.sha256(SVG.encode()).hexdigest()
    if browser_count is None:
        browser_count = len(expected)
    document = {
        "format": PUBLICATION_INVENTORY_FORMAT,
        "formatVersion": PUBLICATION_INVENTORY_VERSION,
        "summary": {
            "publishedAssetCount": len(expected),
            "browserReferencedAssetCount": browser_count,
            "unreferencedPublishedAssetCount": len(expected) - browser_count,
            "publishedBytes": len(SVG.encode()) * len(expected),
        },
        "publishedSha256ByPath": {relative: digest for relative in expected},
    }
    (static / PUBLICATION_INVENTORY).write_text(
        json.dumps(document, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_tracked_symbol_mappings_define_a_nonempty_browser_asset_contract() -> None:
    static = Path("src/infinity_db/web/static")

    expected = browser_asset_paths(static)

    assert any(path.parts[0] == "armies" for path in expected)
    assert any(path.parts[0] == "units" for path in expected)
    assert any(path.parts[0] == "orders" for path in expected)
    assert any(path.parts[0] == "characteristics" for path in expected)
    assert PurePosixPath("orders/regular.svg") in expected
    assert PurePosixPath("characteristics/cube.svg") in expected
    assert PurePosixPath("orders/cube.svg") not in expected


def test_asset_validation_distinguishes_absent_partial_complete_and_invalid(tmp_path: Path) -> None:
    static = tmp_path / "static"
    browser_expected = _write_contract(static)
    published_expected = (*browser_expected, "units/panoceania/2-future-variant.svg")

    assert validate_asset_set(static).state == "absent"

    _write_inventory(static, published_expected, browser_count=len(browser_expected))
    _write_svg(static, published_expected[0])
    partial = validate_asset_set(static)
    assert partial.state == "partial"
    assert partial.missing
    assert partial.expected_count == len(published_expected)
    assert partial.browser_expected_count == len(browser_expected)

    for relative in published_expected:
        _write_svg(static, relative)
    complete = validate_asset_set(static)
    assert complete.state == "complete"
    assert complete.present_count == complete.expected_count == len(published_expected)
    assert (
        complete.browser_present_count
        == complete.browser_expected_count
        == len(browser_expected)
    )
    assert complete.unreferenced_published_count == 1

    _write_svg(static, published_expected[-1], "not svg")
    invalid = validate_asset_set(static)
    assert invalid.state == "invalid"
    assert invalid.invalid


def test_asset_validation_requires_publication_inventory_when_assets_exist(tmp_path: Path) -> None:
    static = tmp_path / "static"
    expected = _write_contract(static)
    _write_svg(static, expected[0])

    validation = validate_asset_set(static)

    assert validation.state == "invalid"
    assert validation.invalid
    assert "inventory is missing" in validation.invalid[0]


def test_asset_validation_rejects_unexpected_and_hash_mismatched_assets(tmp_path: Path) -> None:
    static = tmp_path / "static"
    expected = _write_contract(static)
    for relative in expected:
        _write_svg(static, relative)
    _write_inventory(static, expected)

    extra = "units/panoceania/unlisted.svg"
    _write_svg(static, extra)
    unexpected = validate_asset_set(static)
    assert unexpected.state == "invalid"
    assert unexpected.unexpected == (extra,)

    (static / extra).unlink()
    _write_svg(static, expected[0], '<svg xmlns="http://www.w3.org/2000/svg"><path/></svg>')
    mismatch = validate_asset_set(static)
    assert mismatch.state == "invalid"
    assert any("SHA-256 mismatch" in row for row in mismatch.invalid)


def test_auto_mode_falls_back_only_when_assets_are_completely_absent(tmp_path: Path) -> None:
    static = tmp_path / "static"
    expected = _write_contract(static)

    selection = select_asset_mode("auto", static)
    assert selection.effective == "off"
    assert not selection.include_full_assets

    _write_inventory(static, expected)
    _write_svg(static, expected[0])
    with pytest.raises(AssetValidationError, match="partial"):
        select_asset_mode("auto", static)


def test_required_mode_requires_complete_published_and_browser_sets(tmp_path: Path) -> None:
    static = tmp_path / "static"
    browser_expected = _write_contract(static)
    published_expected = (*browser_expected, "units/panoceania/2-future-variant.svg")

    with pytest.raises(AssetValidationError, match="no published"):
        select_asset_mode("required", static)

    _write_inventory(static, published_expected, browser_count=len(browser_expected))
    for relative in published_expected:
        _write_svg(static, relative)
    selection = select_asset_mode("required", static)

    assert selection.effective == "full"
    assert selection.include_full_assets
    assert selection.validation is not None
    assert selection.validation.complete
    assert "published SVGs" in selection.description()
    assert "browser-referenced" in selection.description()
    assert "1 published not yet browser-referenced" in selection.description()


def test_tracked_symbol_publication_is_fully_browser_addressable() -> None:
    static = Path("src/infinity_db/web/static")

    validation = validate_asset_set(static)

    assert validation.complete
    assert validation.browser_expected_count == validation.expected_count == 806
    assert validation.unreferenced_published_count == 0
