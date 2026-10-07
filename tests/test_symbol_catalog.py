from __future__ import annotations

import json
import sqlite3
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
        "profileIdentityToPublishedPath": {},
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
    assert army["profiles"][0]["symbol_path"] == "units/panoceania/1-alpha-ranger.svg"
    assert army["profiles"][1]["symbol_paths"] == [
        "units/panoceania/1-alpha-ranger--2-1.svg"
    ]
    assert army["profiles"][1]["symbol_path"] == (
        "units/panoceania/1-alpha-ranger--2-1.svg"
    )


def test_symbol_catalog_accepts_peripheral_path_as_unit_symbol(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path / "symbol-publication.json")
    document = json.loads(manifest.read_text(encoding="utf-8"))
    peripheral_path = "peripherals/panoceania/palbot.svg"
    document["unitSlugToPublishedPath"]["alpha-ranger"] = peripheral_path
    manifest.write_text(json.dumps(document), encoding="utf-8")

    catalog = SymbolCatalog(manifest)

    assert catalog.unit_path("alpha-ranger") == peripheral_path



def test_symbol_catalog_accepts_dedicated_peripheral_profile_path(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path / "symbol-publication.json")
    document = json.loads(manifest.read_text(encoding="utf-8"))
    peripheral_path = "peripherals/panoceania/crabbot.svg"
    document["unitProfileLogoToPublishedPath"] = {
        "https://example.test/profile.svg": peripheral_path,
    }
    manifest.write_text(json.dumps(document), encoding="utf-8")
    catalog = SymbolCatalog(manifest)

    assert catalog.profile_path(
        None, "https://example.test/profile.svg", "alpha-ranger"
    ) == peripheral_path



def test_symbol_catalog_repairs_profile_logo_from_semantic_identity(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path / "symbol-publication.json")
    document = json.loads(manifest.read_text(encoding="utf-8"))
    crabbot = "units/panoceania/1-alpha-ranger--2-1.svg"
    document["profileIdentityToPublishedPath"] = {
        "ancillary crabbot remote": crabbot,
    }
    manifest.write_text(json.dumps(document), encoding="utf-8")
    catalog = SymbolCatalog(manifest)
    unit = {
        "slug": "alpha-ranger",
        "armies": [
            {
                "id": 101,
                "profiles": [
                    {
                        "profile_identity": "ancillary crabbot remote",
                        "logo_urls": ["https://example.test/bad-parent-symbol.svg"],
                    }
                ],
            }
        ],
    }

    catalog.enrich_unit(unit)

    profile = unit["armies"][0]["profiles"][0]
    assert profile["symbol_path"] == crabbot
    assert profile["symbol_paths"] == [crabbot]


def test_symbol_catalog_source_primary_logo_can_be_general_profile_override(
    tmp_path: Path,
) -> None:
    manifest = _manifest(tmp_path / "symbol-publication.json")
    document = json.loads(manifest.read_text(encoding="utf-8"))
    alternate = "units/panoceania/2-alpha-ranger-variant.svg"
    document["unitProfileLogoToPublishedPath"] = {
        "https://example.test/source-primary.svg": alternate,
    }
    manifest.write_text(json.dumps(document), encoding="utf-8")
    catalog = SymbolCatalog(manifest)
    unit = {
        "slug": "alpha-ranger",
        "armies": [
            {
                "id": 101,
                "profiles": [
                    {
                        "profile_identity": "variant profile",
                        "logo_urls": ["https://example.test/source-primary.svg"],
                    }
                ],
            }
        ],
    }

    catalog.enrich_unit(unit)

    assert unit["symbol_path"] == "units/panoceania/1-alpha-ranger.svg"
    profile = unit["armies"][0]["profiles"][0]
    assert profile["symbol_path"] == alternate
    assert profile["symbol_paths"] == [alternate]


def test_symbol_catalog_ambiguous_contextual_profile_symbols_inherit_unit(
    tmp_path: Path,
) -> None:
    catalog = SymbolCatalog(_manifest(tmp_path / "symbol-publication.json"))
    unit = {
        "slug": "alpha-ranger",
        "armies": [
            {
                "id": 101,
                "profiles": [
                    {
                        "profile_identity": "initial profile",
                        "logo_urls": [],
                    },
                    {
                        "profile_identity": "initial profile",
                        "logo_urls": ["https://example.test/profile.svg"],
                    },
                ],
            }
        ],
    }

    catalog.enrich_unit(unit)

    profiles = unit["armies"][0]["profiles"]
    assert {profile["symbol_path"] for profile in profiles} == {
        "units/panoceania/1-alpha-ranger.svg"
    }


def test_tracked_symbols_repair_cutter_crabbot_assignment() -> None:
    catalog = SymbolCatalog()
    unit = {
        "slug": "cutters-varuna-naval-chasseurs",
        "armies": [
            {
                "id": 101,
                "profiles": [
                    {
                        "profile_identity": "ancillary crabbot remote",
                        "logo_urls": [
                            "https://assets.corvusbelli.net/army/img/logo/units/"
                            "cutters-varuna-naval-chasseurs-2-1.svg"
                        ],
                    }
                ],
            }
        ],
    }

    catalog.enrich_unit(unit)

    assert unit["symbol_path"] == (
        "units/panoceania/12-cutters-varuna-naval-chasseurs.svg"
    )
    assert unit["armies"][0]["profiles"][0]["symbol_path"] == (
        "peripherals/panoceania/crabbot.svg"
    )


def test_symbol_catalog_leaves_unpublished_fixture_unit_unenriched(tmp_path: Path) -> None:
    catalog = SymbolCatalog(_manifest(tmp_path / "symbol-publication.json"))
    unit = {
        "slug": "synthetic-fixture-unit",
        "display_army_id": 101,
        "armies": [{"id": 101, "profiles": [{"logo_urls": []}]}],
    }

    catalog.enrich_unit(unit)

    assert "symbol_path" not in unit
    assert unit["display_army_symbol_path"] == "armies/panoceania/101-panoceania.svg"
    assert unit["armies"][0]["symbol_path"] == "armies/panoceania/101-panoceania.svg"
    assert "symbol_path" not in unit["armies"][0]["profiles"][0]


def test_tracked_publication_covers_every_runtime_logical_unit() -> None:
    database = Path(__file__).parents[1] / "data" / "generated" / "infinity.db"
    catalog = SymbolCatalog()
    with sqlite3.connect(database) as connection:
        slugs = [
            row[0]
            for row in connection.execute(
                "SELECT slug FROM logical_units ORDER BY id"
            )
        ]

    missing = [slug for slug in slugs if catalog.unit_path(slug) is None]
    assert slugs
    assert missing == []


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
