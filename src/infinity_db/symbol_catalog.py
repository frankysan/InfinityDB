"""Resolve published symbol paths from the canonical publication manifest."""

from __future__ import annotations

import json
import re
import unicodedata
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any

from infinity_army_data.project_resources import maintained_manifest_path

PUBLICATION_FORMAT = "InfinityDB symbol publication mapping"
PUBLICATION_VERSION = 2
_PUBLISHED_CATEGORIES = frozenset({"armies", "characteristics", "orders", "units"})


class SymbolCatalogError(ValueError):
    """Raised when the published symbol manifest is invalid."""


def _slugify(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = text.lower().replace("&", " and ")
    return re.sub(r"(^-+|-+$)", "", re.sub(r"[^a-z0-9]+", "-", text))


def _published_path(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or ".." in path.parts
        or len(path.parts) < 2
        or path.parts[0] not in _PUBLISHED_CATEGORIES
        or path.suffix != ".svg"
    ):
        raise SymbolCatalogError(f"Invalid published symbol path: {value!r}")
    return value


class SymbolCatalog:
    """Read-only symbol lookup backed by ``symbol-publication.json``."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or maintained_manifest_path("symbol-publication.json")
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SymbolCatalogError(
                f"Could not read symbol publication manifest {self.path}: {exc}"
            ) from exc
        if not isinstance(document, dict):
            raise SymbolCatalogError("Symbol publication manifest must be a JSON object")
        if document.get("format") != PUBLICATION_FORMAT:
            raise SymbolCatalogError("Symbol publication manifest has an unexpected format")
        if document.get("formatVersion") != PUBLICATION_VERSION:
            raise SymbolCatalogError("Symbol publication manifest has an unsupported formatVersion")

        self.armies = self._mapping(document, "factionIdToPublishedPath")
        self.units = self._mapping(document, "unitSlugToPublishedPath")
        self.profile_logos = self._mapping(document, "unitProfileLogoToPublishedPath")

    @staticmethod
    def _mapping(document: dict[str, Any], field: str) -> dict[str, str]:
        raw = document.get(field)
        if not isinstance(raw, dict):
            raise SymbolCatalogError(f"Symbol publication manifest must contain {field}")
        result: dict[str, str] = {}
        for key, value in raw.items():
            if not isinstance(key, str):
                raise SymbolCatalogError(
                    f"Symbol publication manifest {field} keys must be strings"
                )
            path = _published_path(value)
            if path is None:
                raise SymbolCatalogError(
                    f"Symbol publication manifest {field} values must be paths"
                )
            result[key] = path
        return result

    def army_path(self, army_id: object) -> str | None:
        if type(army_id) is not int:
            return None
        return self.armies.get(str(army_id))

    def unit_path(self, unit_name: object) -> str | None:
        slug = _slugify(unit_name)
        return self.units.get(slug) if slug else None

    def profile_path(self, profile_logo: object, unit_name: object) -> str | None:
        if isinstance(profile_logo, str):
            override = self.profile_logos.get(profile_logo)
            if override is not None:
                return override
        return self.unit_path(unit_name)

    def enrich_army(self, army: dict[str, Any], *, unit_name: object = None) -> None:
        symbol_path = self.army_path(army.get("id"))
        if symbol_path is not None:
            army["symbol_path"] = symbol_path

        unit_path = self.unit_path(unit_name)
        profiles = army.get("profiles")
        if not isinstance(profiles, list):
            return
        for profile in profiles:
            if not isinstance(profile, dict):
                continue
            logo_urls = profile.get("logo_urls")
            logos = logo_urls if isinstance(logo_urls, list) and logo_urls else [None]
            symbol_paths: list[str] = []
            for logo in logos:
                path = self.profile_path(logo, unit_name)
                if path is not None and path not in symbol_paths:
                    symbol_paths.append(path)
            if not symbol_paths and unit_path is not None:
                symbol_paths.append(unit_path)
            if symbol_paths:
                profile["symbol_paths"] = symbol_paths

    def enrich_unit(self, unit: dict[str, Any]) -> None:
        unit_name = unit.get("slug") or unit.get("isc") or unit.get("name")
        symbol_path = self.unit_path(unit_name)
        if symbol_path is not None:
            unit["symbol_path"] = symbol_path

        display_path = self.army_path(unit.get("display_army_id"))
        if display_path is not None:
            unit["display_army_symbol_path"] = display_path

        armies = unit.get("armies")
        if isinstance(armies, list):
            for army in armies:
                if isinstance(army, dict):
                    self.enrich_army(army, unit_name=unit_name)

    def enrich_armies(self, armies: list[dict[str, Any]]) -> None:
        for army in armies:
            self.enrich_army(army)

    def enrich_units(self, units: list[dict[str, Any]]) -> None:
        for unit in units:
            self.enrich_unit(unit)

    def enrich_nested_units(self, value: dict[str, Any]) -> dict[str, Any]:
        """Return a detached payload with nested ``units`` collections enriched."""

        result = deepcopy(value)

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                for key, child in node.items():
                    if key == "units" and isinstance(child, list):
                        for item in child:
                            if isinstance(item, dict):
                                self.enrich_unit(item)
                    walk(child)
            elif isinstance(node, list):
                for child in node:
                    walk(child)

        walk(result)
        return result
