"""Validate the locally published third-party symbol set used by integration tests."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ASSET_MODES = ("off", "auto", "required")
PUBLISHED_ASSET_CATEGORIES = ("armies", "orders", "units")
ORDER_SYMBOL_NAMES = (
    "regular",
    "irregular",
    "peripheral",
    "impetuous",
    "tactical",
    "lieutenant",
    "hackable",
    "cube",
    "cube-2",
)
_ARMY_MAPPING = re.compile(r'\[\s*\d+\s*,\s*"([^"]+\.svg)"\s*\]')
_UNIT_MAPPING = re.compile(r'\[\s*"[^"]+"\s*,\s*"([^"]+)"\s*\]')


class AssetValidationError(ValueError):
    """Raised when an explicit asset-testing policy cannot be satisfied."""


@dataclass(frozen=True)
class AssetSetValidation:
    state: str
    expected_count: int
    present_count: int
    missing: tuple[str, ...] = ()
    invalid: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return self.state == "complete"


@dataclass(frozen=True)
class AssetModeSelection:
    requested: str
    effective: str
    validation: AssetSetValidation | None

    @property
    def include_full_assets(self) -> bool:
        return self.effective == "full"

    def description(self) -> str:
        if self.requested == "off":
            return "off (hermetic tests only)"
        assert self.validation is not None
        if self.include_full_assets:
            return (
                f"{self.requested} -> full "
                f"({self.validation.present_count}/{self.validation.expected_count} required SVGs)"
            )
        return "auto -> off (no third-party graphical asset set detected)"


def _safe_relative_svg(value: str, *, suffix: str = "") -> PurePosixPath:
    path = PurePosixPath(f"{value}{suffix}")
    if path.is_absolute() or ".." in path.parts or path.suffix != ".svg":
        raise AssetValidationError(f"Invalid published symbol path in mapping: {value!r}")
    return path


def expected_asset_paths(static_root: Path) -> tuple[PurePosixPath, ...]:
    """Return every SVG required by the current browser publication mappings."""

    army_map = static_root / "army-symbols.js"
    unit_map = static_root / "unit-symbol-map.js"
    try:
        army_source = army_map.read_text(encoding="utf-8")
        unit_source = unit_map.read_text(encoding="utf-8")
    except OSError as exc:
        raise AssetValidationError(f"Could not read published symbol mapping: {exc}") from exc

    army_values = _ARMY_MAPPING.findall(army_source)
    unit_values = _UNIT_MAPPING.findall(unit_source)
    if not army_values:
        raise AssetValidationError(f"No army symbol mappings found in {army_map}")
    if not unit_values:
        raise AssetValidationError(f"No unit symbol mappings found in {unit_map}")

    expected = {
        PurePosixPath("armies") / _safe_relative_svg(value)
        for value in army_values
    }
    expected.update(
        PurePosixPath("units") / _safe_relative_svg(value, suffix=".svg")
        for value in unit_values
    )
    expected.update(PurePosixPath("orders") / f"{name}.svg" for name in ORDER_SYMBOL_NAMES)
    return tuple(sorted(expected, key=str))


def _published_svg_files(static_root: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for category in PUBLISHED_ASSET_CATEGORIES:
        root = static_root / category
        if root.is_dir():
            files.extend(path for path in root.rglob("*.svg") if path.is_file())
    return tuple(files)


def _invalid_svg_reason(path: Path) -> str | None:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        return str(exc)
    if root.tag.rsplit("}", 1)[-1] != "svg":
        return f"root element is {root.tag!r}, not svg"
    return None


def validate_asset_set(static_root: Path) -> AssetSetValidation:
    """Validate the complete local asset set against current browser mappings."""

    present_files = _published_svg_files(static_root)
    if not present_files:
        return AssetSetValidation(state="absent", expected_count=0, present_count=0)

    expected = expected_asset_paths(static_root)
    present_by_relative = {
        path.relative_to(static_root).as_posix(): path for path in present_files
    }
    missing: list[str] = []
    invalid: list[str] = []
    present_count = 0
    for relative in expected:
        relative_text = relative.as_posix()
        path = present_by_relative.get(relative_text)
        if path is None:
            missing.append(relative_text)
            continue
        present_count += 1
        reason = _invalid_svg_reason(path)
        if reason is not None:
            invalid.append(f"{relative_text}: {reason}")

    if invalid:
        state = "invalid"
    elif missing:
        state = "partial"
    else:
        state = "complete"
    return AssetSetValidation(
        state=state,
        expected_count=len(expected),
        present_count=present_count,
        missing=tuple(missing),
        invalid=tuple(invalid),
    )


def _validation_error(mode: str, validation: AssetSetValidation) -> AssetValidationError:
    if validation.state == "absent":
        return AssetValidationError(
            f"Asset mode {mode!r} requires a complete local asset set, but no published "
            "third-party SVG assets were detected."
        )
    details: list[str] = []
    if validation.missing:
        sample = ", ".join(validation.missing[:5])
        suffix = " ..." if len(validation.missing) > 5 else ""
        details.append(f"missing {len(validation.missing)}: {sample}{suffix}")
    if validation.invalid:
        sample = "; ".join(validation.invalid[:3])
        suffix = " ..." if len(validation.invalid) > 3 else ""
        details.append(f"invalid {len(validation.invalid)}: {sample}{suffix}")
    detail_text = "; ".join(details) or validation.state
    return AssetValidationError(
        f"Asset mode {mode!r} detected a {validation.state} local asset set ({detail_text})."
    )


def select_asset_mode(mode: str, static_root: Path) -> AssetModeSelection:
    """Resolve off/auto/required into hermetic or full-asset pytest behavior."""

    if mode not in ASSET_MODES:
        raise AssetValidationError(f"Unknown asset mode: {mode!r}")
    if mode == "off":
        return AssetModeSelection(requested=mode, effective="off", validation=None)

    validation = validate_asset_set(static_root)
    if validation.complete:
        return AssetModeSelection(requested=mode, effective="full", validation=validation)
    if mode == "auto" and validation.state == "absent":
        return AssetModeSelection(requested=mode, effective="off", validation=validation)
    raise _validation_error(mode, validation)
