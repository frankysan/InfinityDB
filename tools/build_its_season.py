"""Build or inspect the isolated ITS 18 SQLite publication (P3.2).

This deliberately does not change data/generated or the current serving set.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from infinity_db.its_season_database import (
    DEFAULT_CORE_REVISION,
    build_its_database,
    inspect_its_database,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data/curated/rules/n5-its-season-18-2026.09.01.json"
DEFAULT_OUTPUT = ROOT / "data/work/its/its_18.db"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--core-revision", default=DEFAULT_CORE_REVISION)
    parser.add_argument(
        "--check", action="store_true",
        help="Inspect an existing ITS artifact without building or changing files",
    )
    args = parser.parse_args(argv)
    reserved = ROOT / "data/generated"
    if args.output.resolve().is_relative_to(reserved.resolve()):
        parser.error("ITS is not a serving artifact before the P3.4 cutover")
    try:
        if args.check:
            result = inspect_its_database(
                args.output, source=args.source, core_revision=args.core_revision,
                require_current_builder=True,
            )
        else:
            result = build_its_database(
                args.source, args.output, core_revision=args.core_revision,
            )
    except (OSError, ValueError) as exc:
        parser.exit(1, f"ITS season database blocked: {exc}\n")
    print(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
