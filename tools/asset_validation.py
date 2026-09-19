"""Validate the locally published third-party symbol set used by integration tests."""

from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ASSET_MODES = ("off", "auto", "required")
PUBLISHED_ASSET_CATEGORIES = ("armies", "characteristics", "orders", "units")
PUBLICATION_INVENTORY = "symbol-inventory.json"
PUBLICATION_INVENTORY_FORMAT = "InfinityDB published symbol inventory"
PUBLICATION_INVENTORY_VERSION = 1
ORDER_SYMBOL_NAMES = (
    "regular",
    "irregular",
    "impetuous",
    "tactical",
    "lieutenant",
)
CHARACTERISTIC_SYMBOL_NAMES = (
    "peripheral",
    "hackable",
    "cube",
    "cube-2",
)
_ARMY_MAPPING = re.compile(r'\[\s*\d+\s*,\s*"([^"]+\.svg)"\s*\]')
_UNIT_MAPPING = re.compile(r'\[\s*"[^"]+"\s*,\s*"([^"]+)"\s*\]')
_SHA256 = re.compile(r"[0-9a-f]{64}")


class AssetValidationError(ValueError):
    """Raised when an explicit asset-testing policy cannot be satisfied."""


@dataclass(frozen=True)
class AssetSetValidation:
    state: str
    expected_count: int
    present_count: int
    browser_expected_count: int = 0
    browser_present_count: int = 0
    unreferenced_published_count: int = 0
    missing: tuple[str, ...] = ()
    browser_missing: tuple[str, ...] = ()
    unexpected: tuple[str, ...] = ()
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
            validation = self.validation
            return (
                f"{self.requested} -> full "
                f"({validation.present_count}/{validation.expected_count} published SVGs; "
                f"{validation.browser_present_count}/{validation.browser_expected_count} "
                "browser-referenced; "
                f"{validation.unreferenced_published_count} published not yet browser-referenced)"
            )
        return "auto -> off (no third-party graphical asset set detected)"


def _safe_relative_svg(value: str, *, suffix: str = "") -> PurePosixPath:
    path = PurePosixPath(f"{value}{suffix}")
    if path.is_absolute() or ".." in path.parts or path.suffix != ".svg":
        raise AssetValidationError(f"Invalid published symbol path in mapping: {value!r}")
    return path


def browser_asset_paths(static_root: Path) -> tuple[PurePosixPath, ...]:
    """Return every SVG currently referenced by browser mappings/endpoints."""

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
    expected.update(
        PurePosixPath("characteristics") / f"{name}.svg"
        for name in CHARACTERISTIC_SYMBOL_NAMES
    )
    return tuple(sorted(expected, key=str))


# Backward-compatible name for callers that previously treated this subset as the full set.
def expected_asset_paths(static_root: Path) -> tuple[PurePosixPath, ...]:
    return browser_asset_paths(static_root)


def _publication_inventory(static_root: Path) -> tuple[dict[str, str], dict[str, int]]:
    path = static_root / PUBLICATION_INVENTORY
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AssetValidationError(f"Published symbol inventory is missing: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise AssetValidationError(
            f"Could not read published symbol inventory {path}: {exc}"
        ) from exc

    if not isinstance(document, dict):
        raise AssetValidationError("Published symbol inventory must be a JSON object")
    if document.get("format") != PUBLICATION_INVENTORY_FORMAT:
        raise AssetValidationError("Published symbol inventory has an unexpected format")
    if document.get("formatVersion") != PUBLICATION_INVENTORY_VERSION:
        raise AssetValidationError("Published symbol inventory has an unsupported formatVersion")
    raw = document.get("publishedSha256ByPath")
    if not isinstance(raw, dict) or not raw:
        raise AssetValidationError("Published symbol inventory must contain publishedSha256ByPath")
    summary = document.get("summary")
    summary_fields = {
        "publishedAssetCount",
        "browserReferencedAssetCount",
        "unreferencedPublishedAssetCount",
        "publishedBytes",
    }
    if not isinstance(summary, dict) or set(summary) != summary_fields:
        raise AssetValidationError("Published symbol inventory has an invalid summary")
    for field in summary_fields:
        if type(summary[field]) is not int or summary[field] < 0:
            raise AssetValidationError(
                f"Published symbol inventory summary.{field} must be a non-negative integer"
            )

    inventory: dict[str, str] = {}
    categories = set(PUBLISHED_ASSET_CATEGORIES)
    for relative, digest in raw.items():
        if not isinstance(relative, str) or not isinstance(digest, str):
            raise AssetValidationError(
                "Published symbol inventory paths and hashes must be strings"
            )
        path_value = PurePosixPath(relative)
        if (
            path_value.is_absolute()
            or ".." in path_value.parts
            or len(path_value.parts) < 2
            or path_value.parts[0] not in categories
            or path_value.suffix != ".svg"
        ):
            raise AssetValidationError(f"Invalid published symbol inventory path: {relative!r}")
        if _SHA256.fullmatch(digest) is None:
            raise AssetValidationError(
                f"Invalid published symbol inventory SHA-256 for {relative!r}"
            )
        inventory[relative] = digest
    if summary["publishedAssetCount"] != len(inventory):
        raise AssetValidationError(
            "Published symbol inventory summary.publishedAssetCount does not match its paths"
        )
    if (
        summary["browserReferencedAssetCount"]
        + summary["unreferencedPublishedAssetCount"]
        != summary["publishedAssetCount"]
    ):
        raise AssetValidationError(
            "Published symbol inventory browser/unreferenced counts do not cover all assets"
        )
    return inventory, summary


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


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_asset_set(static_root: Path) -> AssetSetValidation:
    """Validate the complete published set and the current browser-referenced subset."""

    present_files = _published_svg_files(static_root)
    inventory_path = static_root / PUBLICATION_INVENTORY
    if not present_files and not inventory_path.exists():
        return AssetSetValidation(state="absent", expected_count=0, present_count=0)

    try:
        inventory, inventory_summary = _publication_inventory(static_root)
        browser_expected = browser_asset_paths(static_root)
    except AssetValidationError as exc:
        return AssetSetValidation(
            state="invalid",
            expected_count=0,
            present_count=len(present_files),
            invalid=(str(exc),),
        )

    present_by_relative = {
        path.relative_to(static_root).as_posix(): path for path in present_files
    }
    expected_paths = set(inventory)
    present_paths = set(present_by_relative)
    missing = sorted(expected_paths - present_paths)
    unexpected = sorted(present_paths - expected_paths)
    invalid: list[str] = []

    for relative in sorted(expected_paths & present_paths):
        path = present_by_relative[relative]
        reason = _invalid_svg_reason(path)
        if reason is not None:
            invalid.append(f"{relative}: {reason}")
            continue
        actual = _sha256_file(path)
        if actual != inventory[relative]:
            invalid.append(
                f"{relative}: SHA-256 mismatch (expected {inventory[relative]}, got {actual})"
            )

    browser_paths = {path.as_posix() for path in browser_expected}
    browser_missing = sorted(browser_paths - expected_paths)
    browser_present_count = len(browser_paths & present_paths & expected_paths)
    unreferenced_count = len(expected_paths - browser_paths)
    if inventory_summary["browserReferencedAssetCount"] != len(browser_paths):
        invalid.append(
            "symbol-inventory.json browserReferencedAssetCount does not match current mappings"
        )
    if inventory_summary["unreferencedPublishedAssetCount"] != unreferenced_count:
        invalid.append(
            "symbol-inventory.json unreferencedPublishedAssetCount does not match current mappings"
        )
    if not missing:
        published_bytes = sum(present_by_relative[path].stat().st_size for path in expected_paths)
        if inventory_summary["publishedBytes"] != published_bytes:
            invalid.append(
                "symbol-inventory.json publishedBytes does not match the published SVG files"
            )

    if invalid or unexpected or browser_missing:
        state = "invalid"
    elif missing:
        state = "partial"
    else:
        state = "complete"

    return AssetSetValidation(
        state=state,
        expected_count=len(expected_paths),
        present_count=len(expected_paths & present_paths),
        browser_expected_count=len(browser_paths),
        browser_present_count=browser_present_count,
        unreferenced_published_count=unreferenced_count,
        missing=tuple(missing),
        browser_missing=tuple(browser_missing),
        unexpected=tuple(unexpected),
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
        details.append(f"missing published {len(validation.missing)}: {sample}{suffix}")
    if validation.browser_missing:
        sample = ", ".join(validation.browser_missing[:5])
        suffix = " ..." if len(validation.browser_missing) > 5 else ""
        details.append(
            f"browser references outside publication inventory {len(validation.browser_missing)}: "
            f"{sample}{suffix}"
        )
    if validation.unexpected:
        sample = ", ".join(validation.unexpected[:5])
        suffix = " ..." if len(validation.unexpected) > 5 else ""
        details.append(f"unexpected published {len(validation.unexpected)}: {sample}{suffix}")
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
