"""Build a release-paired publication of reviewed Weapon Chart citations."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from infinity_db.database.repository import Database
from infinity_db.rules_database import RulesDatabase
from infinity_db.weapon_profile_publication import (
    PROFILE_CITATION_SCOPE,
    current_pdf_source,
    file_sha256,
    load_weapon_profile_publication,
)

try:
    from tools.audit_enrichment_coverage import audit_coverage
    from tools.audit_weapon_definition_gaps import load_shared_reviews
except ModuleNotFoundError as exc:  # pragma: no cover - direct script execution
    if exc.name not in {
        "tools", "tools.audit_enrichment_coverage", "tools.audit_weapon_definition_gaps",
    }:
        raise
    from audit_enrichment_coverage import audit_coverage
    from audit_weapon_definition_gaps import load_shared_reviews

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARMY = ROOT / "data" / "generated" / "infinity.db"
DEFAULT_RULES = ROOT / "data" / "generated" / "rules.db"
DEFAULT_REVIEWS = ROOT / "data" / "curated" / "weapon-shared-effect-reviews.json"
DEFAULT_OUTPUT = ROOT / "data" / "generated" / "weapon-profile-sources.json"


def build_publication(
    army_path: Path, rules_path: Path, reviews_path: Path,
) -> dict[str, Any]:
    """Compile reviewed identities and modes after validating their source pair."""
    try:
        policy = json.loads(reviews_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Cannot read reviewed Weapon source policy") from exc
    if not isinstance(policy, dict):
        raise ValueError("Reviewed Weapon source policy must be an object")
    collection_id, source_id, source_sha = (
        policy.get("sourceCollectionId"), policy.get("sourceId"), policy.get("sourceSha256"),
    )
    page_range = policy.get("chartPageRange")
    if (
        not isinstance(collection_id, str) or not collection_id
        or not isinstance(source_id, str) or not source_id
        or not isinstance(source_sha, str) or re.fullmatch(r"[0-9a-f]{64}", source_sha) is None
        or not isinstance(page_range, list) or len(page_range) != 2
        or any(type(page) is not int for page in page_range)
    ):
        raise ValueError("Reviewed Weapon source policy lacks its PDF and chart-page pins")
    source = current_pdf_source(rules_path, collection_id, source_id)
    if (
        source["sha256"] != source_sha
        or not 1 <= page_range[0] <= page_range[1] <= source["pageCount"]
    ):
        raise ValueError("Reviewed Weapon Chart policy does not match the current PDF")

    database = Database(army_path)
    rules = RulesDatabase(rules_path)
    enrichment = audit_coverage(army_path, rules_path)
    reviewed = load_shared_reviews(database, enrichment, reviews_path, rules=rules)
    pending = {
        row["id"] for row in enrichment["domains"]["weapons"]["items"]
        if row["gapCodes"] == ["missing_rule_definition"]
    }
    if pending - reviewed.keys():
        raise ValueError("Profile-only Weapons lack reviewed chart citations")
    raw_reviews = {review["slug"]: review for review in policy["reviews"]}
    weapons: list[dict[str, Any]] = []
    for weapon_id in pending:
        item = database.get_catalog_item("weapons", weapon_id)
        if item is None:
            raise ValueError(f"Reviewed Weapon cannot be resolved: {weapon_id}")
        slug = database.application_slug("weapons", weapon_id)
        review = raw_reviews[slug]
        page = reviewed[weapon_id]["chartPage"]
        if type(page) is not int or not page_range[0] <= page <= page_range[1]:
            raise ValueError(f"Reviewed Weapon chart page is out of range: {slug}")
        weapons.append({
            "id": weapon_id,
            "slug": slug,
            "name": item["name"],
            "profileSha256": review["profileSha256"],
            "profiles": [
                {"sourceId": profile["id"], "mode": profile.get("mode"), "page": page}
                for profile in item["profiles"]
            ],
        })
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
        "chartPageRange": page_range,
        "weapons": weapons,
    }


def publication_bytes(publication: dict[str, Any]) -> bytes:
    return (json.dumps(
        publication, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ) + "\n").encode("utf-8")


def check_publication(
    army_path: Path, rules_path: Path, reviews_path: Path, output_path: Path,
) -> None:
    expected = publication_bytes(build_publication(army_path, rules_path, reviews_path))
    if not output_path.is_file() or output_path.read_bytes() != expected:
        raise ValueError("Weapon profile publication is missing or differs from reviewed inputs")
    if load_weapon_profile_publication(output_path, army_path, rules_path) is None:
        raise ValueError("Weapon profile publication is missing")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--army-db", type=Path, default=DEFAULT_ARMY)
    parser.add_argument("--rules-db", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--reviews", type=Path, default=DEFAULT_REVIEWS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check", action="store_true", help="Verify existing bytes without writing",
    )
    args = parser.parse_args(argv)
    try:
        if args.check:
            check_publication(args.army_db, args.rules_db, args.reviews, args.output)
        else:
            publication = build_publication(args.army_db, args.rules_db, args.reviews)
            temporary: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb", dir=args.output.parent, prefix=".weapon-profile-", delete=False,
                ) as stream:
                    temporary = Path(stream.name)
                    stream.write(publication_bytes(publication))
                load_weapon_profile_publication(temporary, args.army_db, args.rules_db)
                temporary.replace(args.output)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    action = "verified" if args.check else "built"
    print(f"Reviewed Weapon profile publication {action}: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
