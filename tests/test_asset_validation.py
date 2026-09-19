from __future__ import annotations

from pathlib import Path, PurePosixPath

import pytest

from tools.asset_validation import (
    AssetValidationError,
    expected_asset_paths,
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
    return tuple(path.as_posix() for path in expected_asset_paths(static))


def _write_svg(static: Path, relative: str, body: str = SVG) -> None:
    path = static / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_tracked_symbol_mappings_define_a_nonempty_asset_contract() -> None:
    static = Path("src/infinity_db/web/static")

    expected = expected_asset_paths(static)

    assert any(path.parts[0] == "armies" for path in expected)
    assert any(path.parts[0] == "units" for path in expected)
    assert any(path.parts[0] == "orders" for path in expected)
    assert any(path.parts[0] == "characteristics" for path in expected)
    assert PurePosixPath("orders/regular.svg") in expected
    assert PurePosixPath("characteristics/cube.svg") in expected
    assert PurePosixPath("orders/cube.svg") not in expected


def test_asset_validation_distinguishes_absent_partial_complete_and_invalid(tmp_path: Path) -> None:
    static = tmp_path / "static"
    expected = _write_contract(static)

    assert validate_asset_set(static).state == "absent"

    _write_svg(static, expected[0])
    partial = validate_asset_set(static)
    assert partial.state == "partial"
    assert partial.missing

    for relative in expected:
        _write_svg(static, relative)
    complete = validate_asset_set(static)
    assert complete.state == "complete"
    assert complete.present_count == complete.expected_count == len(expected)

    _write_svg(static, expected[-1], "not svg")
    invalid = validate_asset_set(static)
    assert invalid.state == "invalid"
    assert invalid.invalid


def test_auto_mode_falls_back_only_when_assets_are_completely_absent(tmp_path: Path) -> None:
    static = tmp_path / "static"
    expected = _write_contract(static)

    selection = select_asset_mode("auto", static)
    assert selection.effective == "off"
    assert not selection.include_full_assets

    _write_svg(static, expected[0])
    with pytest.raises(AssetValidationError, match="partial"):
        select_asset_mode("auto", static)


def test_required_mode_requires_a_complete_valid_asset_set(tmp_path: Path) -> None:
    static = tmp_path / "static"
    expected = _write_contract(static)

    with pytest.raises(AssetValidationError, match="no published"):
        select_asset_mode("required", static)

    for relative in expected:
        _write_svg(static, relative)
    selection = select_asset_mode("required", static)

    assert selection.effective == "full"
    assert selection.include_full_assets
    assert selection.validation is not None
    assert selection.validation.complete
