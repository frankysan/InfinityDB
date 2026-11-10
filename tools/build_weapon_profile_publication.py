"""Verify embedded Weapon Chart citations against reviewed source inputs.

This is a read-only diagnostic, not a JSON publication or promotion command.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from infinity_db.rules_database import RulesDatabase
from infinity_db.weapon_profile_builder import build_publication

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARMY = ROOT / "data" / "generated" / "army.db"
DEFAULT_RULES = ROOT / "data" / "generated" / "rules_n5.db"
DEFAULT_REVIEWS = ROOT / "data" / "curated" / "weapon-shared-effect-reviews.json"


def check_embedded_profiles(
    army_path: Path, rules_path: Path, reviews_path: Path,
) -> int:
    """Require exact source-derived citations in the selected Rules database."""
    embedded = RulesDatabase(rules_path).weapon_profile_citations_payload(army_path)
    if not embedded:
        raise ValueError("Complete embedded Weapon profile citations are missing")
    publication = build_publication(army_path, rules_path, reviews_path)
    source = publication["source"]
    expected = {
        (weapon["id"], profile["sourceId"], profile["mode"]): {
            "source_id": source["id"], "source_title": source["title"],
            "source_version": source["version"], "source_url": source["url"],
            "source_sha256": source["sha256"], "source_collection_id": source["collectionId"],
            "page": profile["page"],
        }
        for weapon in publication["weapons"] for profile in weapon["profiles"]
    }
    if embedded != expected:
        raise ValueError("Embedded Weapon citations differ from reviewed source inputs")
    return len(embedded)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--army-db", type=Path, default=DEFAULT_ARMY)
    parser.add_argument("--rules-db", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--reviews", type=Path, default=DEFAULT_REVIEWS)
    args = parser.parse_args(argv)
    try:
        count = check_embedded_profiles(args.army_db, args.rules_db, args.reviews)
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Embedded Weapon profile citations: PASS ({count} profiles)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
