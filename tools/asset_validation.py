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
PUBLICATION_MANIFEST_FORMAT = "InfinityDB symbol publication mapping"
PUBLICATION_MANIFEST_VERSION = 2
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


def browser_asset_paths(publication_manifest: Path) -> tuple[PurePosixPath, ...]:
    """Return every SVG referenced by the canonical browser/API symbol contract."""

    _inventory, _summary, paths = _publication_manifest(publication_manifest)
    return paths


def publication_manifest_summary(publication_manifest: Path) -> dict[str, int]:
    """Return validated summary values from the canonical publication manifest."""

    _inventory, summary, _paths = _publication_manifest(publication_manifest)
    return dict(summary)


def _publication_manifest(
    path: Path,
) -> tuple[dict[str, str], dict[str, int], tuple[PurePosixPath, ...]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AssetValidationError(f"Published symbol manifest is missing: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise AssetValidationError(
            f"Could not read published symbol manifest {path}: {exc}"
        ) from exc

    if not isinstance(document, dict):
        raise AssetValidationError("Published symbol manifest must be a JSON object")
    if document.get("format") != PUBLICATION_MANIFEST_FORMAT:
        raise AssetValidationError("Published symbol manifest has an unexpected format")
    if document.get("formatVersion") != PUBLICATION_MANIFEST_VERSION:
        raise AssetValidationError("Published symbol manifest has an unsupported formatVersion")

    raw = document.get("publishedSha256ByPath")
    usage = document.get("browserUsageSummary")
    if not isinstance(raw, dict) or not raw:
        raise AssetValidationError("Published symbol manifest must contain publishedSha256ByPath")
    if not isinstance(usage, dict):
        raise AssetValidationError("Published symbol manifest must contain browserUsageSummary")

    inventory: dict[str, str] = {}
    for relative, digest in raw.items():
        if not isinstance(relative, str) or not isinstance(digest, str):
            raise AssetValidationError("Published symbol manifest paths and hashes must be strings")
        path_value = PurePosixPath(relative)
        if (
            path_value.is_absolute()
            or ".." in path_value.parts
            or len(path_value.parts) < 2
            or path_value.parts[0] not in PUBLISHED_ASSET_CATEGORIES
            or path_value.suffix != ".svg"
        ):
            raise AssetValidationError(f"Invalid published symbol manifest path: {relative!r}")
        if _SHA256.fullmatch(digest) is None:
            raise AssetValidationError(
                f"Invalid published symbol manifest SHA-256 for {relative!r}"
            )
        inventory[relative] = digest

    browser_paths: set[str] = set()
    for field in (
        "factionIdToPublishedPath",
        "unitSlugToPublishedPath",
        "unitProfileLogoToPublishedPath",
        "staticKeyToPublishedPath",
    ):
        mapping = document.get(field)
        if not isinstance(mapping, dict):
            raise AssetValidationError(f"Published symbol manifest must contain {field}")
        for relative in mapping.values():
            if not isinstance(relative, str):
                raise AssetValidationError(
                    f"Published symbol manifest {field} values must be strings"
                )
            browser_paths.add(relative)

    browser_count = usage.get("browserReferencedAssetCount")
    unreferenced_count = usage.get("unreferencedPublishedAssetCount")
    if browser_count != len(browser_paths):
        raise AssetValidationError(
            "Published symbol manifest browserReferencedAssetCount does not match its mappings"
        )
    if unreferenced_count != len(set(inventory) - browser_paths):
        raise AssetValidationError(
            "Published symbol manifest unreferencedPublishedAssetCount does not match its mappings"
        )
    summary = document.get("summary")
    if not isinstance(summary, dict):
        raise AssetValidationError("Published symbol manifest must contain summary")
    published_bytes = summary.get("publishedBytes")
    if type(published_bytes) is not int or published_bytes < 0:
        raise AssetValidationError(
            "Published symbol manifest summary.publishedBytes must be non-negative"
        )
    return (
        inventory,
        {
            "publishedAssetCount": len(inventory),
            "browserReferencedAssetCount": len(browser_paths),
            "unreferencedPublishedAssetCount": len(set(inventory) - browser_paths),
            "publishedBytes": published_bytes,
        },
        tuple(PurePosixPath(value) for value in sorted(browser_paths)),
    )


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


def validate_asset_set(
    static_root: Path, *, publication_manifest: Path
) -> AssetSetValidation:
    """Validate the complete published set and the current browser-referenced subset."""

    present_files = _published_svg_files(static_root)
    if not present_files and not publication_manifest.exists():
        return AssetSetValidation(state="absent", expected_count=0, present_count=0)

    try:
        inventory, inventory_summary, browser_expected = _publication_manifest(
            publication_manifest
        )
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
            "publication browserReferencedAssetCount does not match current mappings"
        )
    if inventory_summary["unreferencedPublishedAssetCount"] != unreferenced_count:
        invalid.append(
            "publication unreferencedPublishedAssetCount does not match current mappings"
        )
    if not missing:
        published_bytes = sum(
            present_by_relative[path].stat().st_size for path in expected_paths
        )
        if inventory_summary["publishedBytes"] != published_bytes:
            invalid.append(
                "publication publishedBytes does not match the published SVG files"
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
            f"browser references outside publication manifest {len(validation.browser_missing)}: "
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


def select_asset_mode(
    mode: str,
    static_root: Path,
    *,
    publication_manifest: Path,
) -> AssetModeSelection:
    """Resolve off/auto/required into hermetic or full-asset pytest behavior."""

    if mode not in ASSET_MODES:
        raise AssetValidationError(f"Unknown asset mode: {mode!r}")
    if mode == "off":
        return AssetModeSelection(requested=mode, effective="off", validation=None)

    validation = validate_asset_set(
        static_root, publication_manifest=publication_manifest
    )
    if validation.complete:
        return AssetModeSelection(requested=mode, effective="full", validation=validation)
    if mode == "auto" and validation.state == "absent":
        return AssetModeSelection(requested=mode, effective="off", validation=validation)
    raise _validation_error(mode, validation)
