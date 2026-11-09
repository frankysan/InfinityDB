"""Build a release-paired publication of reviewed Weapon Chart citations."""

from __future__ import annotations

import argparse
import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from infinity_db.weapon_profile_builder import build_publication
from infinity_db.weapon_profile_publication import load_weapon_profile_publication

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARMY = ROOT / "data" / "generated" / "infinity.db"
DEFAULT_RULES = ROOT / "data" / "generated" / "rules.db"
DEFAULT_REVIEWS = ROOT / "data" / "curated" / "weapon-shared-effect-reviews.json"
DEFAULT_OUTPUT = ROOT / "data" / "generated" / "weapon-profile-sources.json"


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
