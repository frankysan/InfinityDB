from __future__ import annotations

import json
from pathlib import Path

from infinity_db.symbol_catalog import SymbolCatalog


def _manifest(path: Path) -> Path:
    document = {
        "format": "InfinityDB symbol publication mapping",
        "formatVersion": 2,
        "factionIdToPublishedPath": {
            "101": "armies/panoceania/101-panoceania.svg",
        },
        "unitSlugToPublishedPath": {
            "alpha-ranger": "units/panoceania/1-alpha-ranger.svg",
        },
        "unitProfileLogoToPublishedPath": {
            "https://example.test/profile.svg": "units/panoceania/1-alpha-ranger--2-1.svg",
        },
    }
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_symbol_catalog_enriches_unit_armies_and_profiles(tmp_path: Path) -> None:
    catalog = SymbolCatalog(_manifest(tmp_path / "symbol-publication.json"))
    unit = {
        "slug": "alpha-ranger",
        "display_army_id": 101,
        "armies": [
            {
                "id": 101,
                "profiles": [
                    {"logo_urls": []},
                    {"logo_urls": ["https://example.test/profile.svg"]},
                ],
            }
        ],
    }

    catalog.enrich_unit(unit)

    assert unit["symbol_path"] == "units/panoceania/1-alpha-ranger.svg"
    assert unit["display_army_symbol_path"] == "armies/panoceania/101-panoceania.svg"
    army = unit["armies"][0]
    assert army["symbol_path"] == "armies/panoceania/101-panoceania.svg"
    assert army["profiles"][0]["symbol_paths"] == [
        "units/panoceania/1-alpha-ranger.svg"
    ]
    assert army["profiles"][1]["symbol_paths"] == [
        "units/panoceania/1-alpha-ranger--2-1.svg"
    ]


def test_nested_unit_enrichment_is_detached(tmp_path: Path) -> None:
    catalog = SymbolCatalog(_manifest(tmp_path / "symbol-publication.json"))
    payload = {
        "variants": [
            {
                "units": [
                    {
                        "slug": "alpha-ranger",
                        "display_army_id": 101,
                        "armies": [{"id": 101}],
                    }
                ]
            }
        ]
    }

    enriched = catalog.enrich_nested_units(payload)

    unit = enriched["variants"][0]["units"][0]
    assert unit["symbol_path"] == "units/panoceania/1-alpha-ranger.svg"
    assert unit["armies"][0]["symbol_path"] == "armies/panoceania/101-panoceania.svg"
    assert "symbol_path" not in payload["variants"][0]["units"][0]
