"""Build-reviewed Weapon Chart locators from current Army/Rules source facts.

This is a maintained build-time validator, not an enrichment-coverage audit.
Source decisions remain curated; no rule meaning is inferred from chart rows.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .catalog_rules import CatalogRules
from .catalog_slugs import attach_public_catalog_slug
from .database.repository import Database
from .rules_database import RulesDatabase
from .weapon_profile_publication import (
    PROFILE_CITATION_SCOPE,
    current_pdf_source,
    file_sha256,
    profile_sha256,
)

_REVIEW_FORMAT = "InfinityDB Weapon shared-effects source reviews"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _reviewed_policy(path: Path) -> dict[str, Any]:
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Cannot read reviewed Weapon source policy") from exc
    if not isinstance(policy, dict):
        raise ValueError("Reviewed Weapon source policy must be an object")
    if (
        policy.get("format") != _REVIEW_FORMAT
        or policy.get("version") != 1
        or policy.get("sourceCollectionId") != "n5-core-v5.3"
        or policy.get("sourceId") != "n5-core-v5.3-pdf"
        or not isinstance(policy.get("sourceSha256"), str)
        or _SHA256.fullmatch(policy["sourceSha256"]) is None
        or not isinstance(policy.get("reviews"), list)
    ):
        raise ValueError("Unsupported reviewed Weapon source policy")
    pages = policy.get("chartPageRange")
    if (
        not isinstance(pages, list) or len(pages) != 2
        or any(type(page) is not int for page in pages)
        or pages[0] <= 0 or pages[1] < pages[0]
    ):
        raise ValueError("Reviewed Weapon source policy lacks its PDF and chart-page pins")
    return policy


def _reviewed_candidates(
    database: Database, rules: RulesDatabase,
) -> tuple[dict[int, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Select missing family definitions using the same public catalog composition.

    Exact source/mode rules do not substitute for a family definition. The
    separate coverage audit still owns other gap classifications.
    """
    catalog = CatalogRules(rules)
    pending: dict[int, dict[str, Any]] = {}
    indexed: dict[str, dict[str, Any]] = {}
    for source in database.list_catalog_items("weapons"):
        weapon_id = int(source["id"])
        item = database.get_catalog_item("weapons", weapon_id)
        if item is None:
            raise ValueError(f"Weapon catalog identity cannot be resolved: {weapon_id}")
        attach_public_catalog_slug(database, "weapons", item)
        slug = database.application_slug("weapons", weapon_id)
        if not isinstance(slug, str) or not slug:
            raise ValueError(f"Weapon has no canonical slug: {weapon_id}")
        if slug in indexed:
            raise ValueError(f"Duplicate canonical Weapon slug: {slug}")
        indexed[slug] = item
        detail = catalog.enrich_catalog_item("weapons", item)
        if not detail.get("rules"):
            # Exact source-only definitions are not family definitions. A source
            # variant with a disputed/review-incomplete rule is outside this
            # profile-only publication, rather than silently accepted.
            exact = [
                record for variant in detail.get("variants", [])
                for record in variant.get("rules", [])
            ]
            if all(
                (record.get("review") or {}).get("status") == "reviewed"
                and record.get("citations")
                for record in exact
            ):
                pending[weapon_id] = item
    return pending, indexed


def build_publication(
    army_path: Path, rules_path: Path, reviews_path: Path,
) -> dict[str, Any]:
    """Compile exact reviewed chart locators, rejecting incomplete source policy."""
    policy = _reviewed_policy(reviews_path)
    pages = policy["chartPageRange"]
    source = current_pdf_source(
        rules_path, policy["sourceCollectionId"], policy["sourceId"],
    )
    if (
        source["sha256"] != policy["sourceSha256"]
        or not 1 <= pages[0] <= pages[1] <= source["pageCount"]
    ):
        raise ValueError("Reviewed Weapon Chart policy does not match the current PDF")

    database = Database(army_path)
    database.validate()
    rules = RulesDatabase(rules_path)
    rules.validate()
    pending, all_weapons = _reviewed_candidates(database, rules)
    accepted: dict[int, dict[str, Any]] = {}
    seen_slugs: set[str] = set()
    for review in policy["reviews"]:
        if not isinstance(review, dict):
            raise ValueError("Reviewed Weapon entry must be an object")
        slug, name, digest, page, reason = (
            review.get("slug"), review.get("name"), review.get("profileSha256"),
            review.get("chartPage"), review.get("reason"),
        )
        if (
            not isinstance(slug, str) or not slug
            or not isinstance(name, str) or not name
            or not isinstance(digest, str) or _SHA256.fullmatch(digest) is None
            or type(page) is not int or not pages[0] <= page <= pages[1]
            or not isinstance(reason, str) or not reason.strip()
        ):
            raise ValueError(f"Incomplete reviewed Weapon entry: {name!r}")
        if slug in seen_slugs:
            raise ValueError(f"Duplicate reviewed Weapon: {slug}")
        seen_slugs.add(slug)
        item = all_weapons.get(slug)
        if item is None or item["name"] != name:
            raise ValueError(f"Reviewed Weapon identity changed: {name}")
        weapon_id = int(item["id"])
        if profile_sha256(item["profiles"]) != digest:
            raise ValueError(f"Reviewed Weapon profile changed: {name}")
        if weapon_id not in pending:
            # A historical review may remain when a reviewed family rule was
            # subsequently published. It must identify that same Weapon.
            if not any(
                record["id"] == f"weapon:{slug}"
                and record["kind"] == "weapon"
                and (record.get("variant_semantics") or {}).get("inheritance") != "source"
                for record in rules.composed_records_for_army_link("weapon", slug)
            ):
                raise ValueError(f"Reviewed Weapon has no verified definition: {name}")
        accepted[weapon_id] = review
    if pending.keys() - accepted.keys():
        raise ValueError("Profile-only Weapons lack reviewed chart citations")

    weapons = [
        {
            "id": weapon_id,
            "slug": database.application_slug("weapons", weapon_id),
            "name": item["name"],
            "profileSha256": accepted[weapon_id]["profileSha256"],
            "profiles": [
                {
                    "sourceId": profile["id"],
                    "mode": profile.get("mode"),
                    "page": accepted[weapon_id]["chartPage"],
                }
                for profile in item["profiles"]
            ],
        }
        for weapon_id, item in pending.items()
    ]
    weapons.sort(key=lambda weapon: (weapon["slug"], weapon["id"]))
    return {
        "formatVersion": 1,
        "scope": PROFILE_CITATION_SCOPE,
        "sourceSnapshot": {
            "armyDatabaseSha256": file_sha256(army_path),
            "rulesDatabaseSha256": file_sha256(rules_path),
            "reviewsSha256": file_sha256(reviews_path),
        },
        "source": source,
        "chartPageRange": pages,
        "weapons": weapons,
    }
