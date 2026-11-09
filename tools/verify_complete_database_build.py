"""Opt-in repeatable source-ZIP acceptance for the complete SQLite runtime set.

This is a maintained development/release diagnostic. Outputs are isolated under
ignored local/ and discarded; tracked release files are never modified.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from infinity_db.build_provenance import file_sha256
from infinity_db.cli import _build_army, build_parser
from infinity_db.database_set import validate_database_set
from infinity_db.database_set_builder import build_database_set
from infinity_db.rules_database import RulesDatabase
from infinity_db.weapon_profile_publication import load_weapon_profile_publication
from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response
from tools.runtime_semantic_baseline import DEFAULT_BASELINE, capture, check

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://database-set-acceptance.test"


def _api(app: Callable[..., Any], route: str) -> dict:
    status, _headers, body = wsgi_response(app, ORIGIN + route)
    if status != 200:
        raise ValueError(f"Source-build HTTP acceptance failed: {route} ({status})")
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError(f"Source-build HTTP response is not an object: {route}")
    return payload


def verify(source: Path, expected_sha256: str) -> dict:
    """Rebuild twice, verify byte determinism and public citation semantics."""
    source = source.resolve()
    if not source.is_file() or file_sha256(source) != expected_sha256:
        raise ValueError("Selected source ZIP does not match its expected SHA-256")
    expected = load_weapon_profile_publication(
        ROOT / "data/generated/weapon-profile-sources.json",
        ROOT / "data/generated/infinity.db",
        ROOT / "data/generated/rules.db",
    )
    if expected is None:
        raise ValueError("Tracked release lacks reviewed Weapon citation baseline")

    scratch = ROOT / "local"
    scratch.mkdir(exist_ok=True)
    reports = []
    with tempfile.TemporaryDirectory(prefix="complete-build-acceptance-", dir=scratch) as temp:
        for attempt in (1, 2):
            destination = Path(temp) / f"attempt-{attempt}"
            args = build_parser().parse_args(
                ["build", str(source), "--db-dir", str(destination), "--compact"]
            )
            result = build_database_set(args, _build_army)
            report = validate_database_set(destination)
            if report != result or report["layout"] != "v17-two-file":
                raise ValueError("Complete-build database health disagrees with publication")
            if set(report["sha256"]) != {"infinity.db", "rules.db"}:
                raise ValueError("Complete build produced an unexpected runtime file set")
            inventory = (
                report["variantGroups"], report["reviewedWeapons"], report["restrictionChartRows"],
            )
            if (
                inventory != (151, 62, 6) or report["traitWikiLinks"] != 33
                or report["combinedSavingRollProfiles"] != 6
                or report["ammunitionReferences"] != 16
                or report["weaponProperties"] != 12
                or report["equipmentPresentationEncodings"] != 2
                or report["skillSourceClassifications"] != 6
                or report["hiddenUnitCharacteristics"] != 2
                or report["sourceClassificationMemberships"] != 1
                or report["armyOverviewSummaries"] != 58
                or report["legacyArmyIdentities"] != 2
                or report["publishedSymbolMappings"] != 2019
                or report["publishedSymbolAssets"] != 808
            ):
                raise ValueError("Complete build changed the reviewed source inventory")

            citations = RulesDatabase(
                destination / "rules.db"
            ).weapon_profile_citations_payload(destination / "infinity.db")
            if citations != expected:
                raise ValueError("Complete build changed reviewed Weapon citation semantics")
            app = create_app(
                destination / "infinity.db", rules_database_path=destination / "rules.db",
            )
            weapon = _api(app, "/api/weapons/uragan-mrl")
            if not weapon["profile_citations_available"] or not all(
                profile["profile_citations"] for profile in weapon["profiles"]
            ):
                raise ValueError("Reviewed Weapon chart locators are absent from the HTTP API")
            variant = _api(app, "/api/variant-usage?record_id=skill:tagcom")
            if not variant.get("items"):
                raise ValueError("Embedded exact variant usage is absent from the HTTP API")
            chart = _api(app, "/api/restrictions/chart")
            expected_chart = json.loads(
                (ROOT / "src/infinity_db/web/static/restrictions-reference.json").read_text(
                    encoding="utf-8"
                )
            )
            if chart != expected_chart:
                raise ValueError("Embedded Restrictions chart differs from source publication")
            links = RulesDatabase(destination / "rules.db").trait_wiki_links_payload()
            from infinity_db.trait_wiki_references import load_trait_wiki_references

            expected_links = load_trait_wiki_references(
                ROOT / "config/catalogs/trait-wiki-references.json"
            )
            if links != expected_links:
                raise ValueError("Embedded Trait Wiki links differ from reviewed curation")
            for identity, entry in expected_links.items():
                trait = _api(app, f"/api/traits/{identity.removeprefix('trait:')}")
                if trait.get("wiki") != entry["url"]:
                    raise ValueError(f"Missing embedded Wiki link for {identity}")
            from infinity_db.weapon_combined_saving_rolls import load_combined_saving_roll_map

            saving_rolls = RulesDatabase(
                destination / "rules.db"
            ).combined_saving_rolls_payload(destination / "infinity.db")
            if saving_rolls != load_combined_saving_roll_map(
                ROOT / "config/catalogs/weapon-combined-saving-rolls.json"
            ):
                raise ValueError("Embedded Combined Saving Rolls differ from source review")
            for slug in ("plasma-rifle", "plasma-carbine", "plasma-sniper-rifle"):
                detail = _api(app, f"/api/weapons/{slug}")
                if any("combined_saving_roll" not in p for p in detail["profiles"]):
                    raise ValueError(f"Missing Combined Saving Roll profile: {slug}")
            from infinity_db.weapon_ammunition_references import (
                load_ammunition_reference_map,
            )

            ammunition = RulesDatabase(destination / "rules.db").ammunition_references_payload(
                destination / "infinity.db"
            )
            if ammunition != load_ammunition_reference_map(
                ROOT / "config/catalogs/weapon-ammunition-references.json"
            ):
                raise ValueError("Embedded Ammunition mapping differs from reviewed source")
            for slug in ("feuerbach", "missile-launcher", "uragan-mrl", "ap-t2-cc-weapon"):
                weapon = _api(app, f"/api/weapons/{slug}")
                if not any(
                    profile.get("ammunition_parts")
                    for profile in weapon.get("profiles", [])
                ):
                    raise ValueError(f"Reviewed Ammunition links are missing for {slug}")
            from infinity_db.weapon_properties import load_weapon_properties

            properties = RulesDatabase(
                destination / "rules.db"
            ).weapon_properties_payload(destination / "infinity.db")
            if properties != load_weapon_properties(
                ROOT / "config/catalogs/weapon-properties.json"
            ):
                raise ValueError("Embedded Weapon Properties differ from reviewed source")
            for slug, property_id in (
                ("plasma-rifle", "plasma"), ("viral-rifle", "viral"),
                ("feuerbach", "ap-da"), ("silenced-pistol", "silenced"),
            ):
                weapon = _api(app, f"/api/weapons/{slug}")
                profiles = weapon.get("profiles", [])
                if not any(
                    any(item["id"] == f"weapon-property:{property_id}"
                        for item in profile.get("weapon_properties", []))
                    for profile in profiles
                ):
                    raise ValueError(f"Missing reviewed Weapon Property for {slug}")
            from infinity_db.database.repository import Database
            from infinity_db.equipment_config import load_equipment_presentation_config

            encodings = Database(
                destination / "infinity.db"
            ).equipment_presentation_encodings()
            if encodings != load_equipment_presentation_config(
                ROOT / "config/catalogs/equipment-presentation-encodings.json"
            ):
                raise ValueError("Embedded Equipment encodings differ from reviewed source")
            for slug in ("cube", "cube-2"):
                detail = _api(app, f"/api/equipment/{slug}")
                if detail.get("slug") != slug:
                    raise ValueError(f"Missing presentation Equipment {slug}")
            from infinity_db.skill_config import load_skill_source_config

            classifications = Database(
                destination / "infinity.db"
            ).skill_source_classifications()
            if classifications != load_skill_source_config(
                ROOT / "config/catalogs/skill-source-classifications.json"
            ):
                raise ValueError("Embedded Skill source classifications differ from review")
            from infinity_db.unit_filter_config import load_unit_filter_config

            semantics = Database(destination / "infinity.db").unit_filter_semantics()
            if semantics != load_unit_filter_config(
                ROOT / "config/catalogs/unit-filter-semantics.json",
            ):
                raise ValueError("Embedded Unit filter semantics differ from review")
            filters = _api(app, "/api/unit-filters")
            if semantics.hidden_characteristics.intersection(
                item["slug"] for item in filters["characteristics"]
            ):
                raise ValueError("Hidden source characteristics leaked into filter choices")
            for membership in semantics.classification_memberships:
                for slug in membership.matches:
                    units = _api(app, f"/api/units?classification={slug}&search=MARUTS&limit=200")
                    if "MARUTS" not in {unit["name"] for unit in units["items"]}:
                        raise ValueError("Combined classification lost its Unit filter membership")
            from infinity_db.army_overview_copy import load_army_overview_copy
            from infinity_db.legacy_armies import load_legacy_armies

            army_copy, legacy_armies = Database(destination / "infinity.db").army_reference_data()
            if (army_copy, legacy_armies) != (
                load_army_overview_copy(ROOT / "data/curated/identities/army-overview.json"),
                load_legacy_armies(ROOT / "data/curated/identities/legacy-armies.json"),
            ):
                raise ValueError("Embedded Army reference differs from authored inputs")
            armies = _api(app, "/api/armies")["items"]
            by_slug = {item.get("public_slug") or item["slug"]: item for item in armies}
            if any(
                by_slug[slug]["overview_description"] != text for slug, text in army_copy.items()
            ):
                raise ValueError("Army API changed authored overview summaries")
            for legacy_army in legacy_armies:
                item = by_slug[legacy_army.slug]
                if not item.get("legacy") or item["playable"]:
                    raise ValueError("Historical Army became playable in the overview")
                query = legacy_army.slug.split("-")[0]
                results = _api(app, f"/api/search?q={query}")["items"]
                if not any(
                    result["domain"] == "Army" and result["name"] == legacy_army.name
                    and result["href"] == f"/armies#army-{legacy_army.slug}"
                    for result in results
                ):
                    raise ValueError("Historical Army search navigation changed")
            from infinity_db.symbol_catalog import SymbolCatalog

            embedded = SymbolCatalog(
                publication=Database(destination / "infinity.db").symbol_publication(),
            )
            authored = SymbolCatalog(ROOT / "data/manifests/symbol-publication.json")
            if embedded.revision != authored.revision:
                raise ValueError("Embedded symbol maps differ from the selected publication")
            version = _api(app, "/api/version")
            if version["static_revision"] != app.presentation.static_revision:
                raise ValueError("Server and presentation disagree on selected asset revision")
            baseline = json.loads(DEFAULT_BASELINE.read_text(encoding="utf-8"))
            observed = capture(
                app, paths=tuple(item["path"] for item in baseline["probes"]),
            )
            if check(baseline, observed) != len(baseline["probes"]):
                raise ValueError("Runtime semantic baseline is incomplete")
            reports.append(report)
            print(
                f"Complete build {attempt}: v17 healthy, 62 Weapons, "
                f"69 citations, 6 chart rows, 33 Trait links, "
                f"6 saving-roll modes, 16 Ammunition references, "
                f"12 Weapon Properties, 2 Equipment encodings, "
                f"6 Skill classifications, 2 hidden characteristics, "
                f"1 classification membership, 58 Army summaries, "
                f"2 historical Army identities, 2019 symbol mappings, "
                f"808 verified SVGs, 41 baseline routes; "
                f"hashes {json.dumps(report['sha256'], sort_keys=True)}",
                flush=True,
            )
        if reports[0]["sha256"] != reports[1]["sha256"]:
            raise ValueError("Repeated complete builds differ at the SQLite byte level")
        if reports[0]["buildProvenance"] != reports[1]["buildProvenance"]:
            raise ValueError("Repeated complete builds differ in source provenance")

    return {
        "status": "pass",
        "sourceSha256": expected_sha256,
        "buildSetId": reports[0]["buildProvenance"]["buildSetId"],
        "layout": reports[0]["layout"],
        "sha256": reports[0]["sha256"],
        "reviewedWeapons": reports[0]["reviewedWeapons"],
        "variantGroups": reports[0]["variantGroups"],
        "restrictionChartRows": reports[0]["restrictionChartRows"],
        "traitWikiLinks": reports[0]["traitWikiLinks"],
        "combinedSavingRollProfiles": reports[0]["combinedSavingRollProfiles"],
        "ammunitionReferences": reports[0]["ammunitionReferences"],
        "weaponProperties": reports[0]["weaponProperties"],
        "equipmentPresentationEncodings": reports[0]["equipmentPresentationEncodings"],
        "skillSourceClassifications": reports[0]["skillSourceClassifications"],
        "hiddenUnitCharacteristics": reports[0]["hiddenUnitCharacteristics"],
        "sourceClassificationMemberships": reports[0]["sourceClassificationMemberships"],
        "armyOverviewSummaries": reports[0]["armyOverviewSummaries"],
        "legacyArmyIdentities": reports[0]["legacyArmyIdentities"],
        "publishedSymbolMappings": reports[0]["publishedSymbolMappings"],
        "publishedSymbolAssets": reports[0]["publishedSymbolAssets"],
        "rebuilds": 2,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Pinned local immutable Army ZIP")
    parser.add_argument(
        "--sha256", required=True, help="Expected exact source archive SHA-256",
    )
    args = parser.parse_args(argv)
    if len(args.sha256) != 64 or any(char not in "0123456789abcdef" for char in args.sha256):
        parser.error("--sha256 must be 64 lowercase hexadecimal characters")
    try:
        print(json.dumps(verify(args.source, args.sha256), sort_keys=True, indent=2))
    except (OSError, ValueError) as exc:
        print(f"Complete-build acceptance: FAIL: {exc}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
