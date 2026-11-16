"""Build InfinityDB's complete runtime set from one selected Army ZIP/manifest pair.

This is a thin, MCP-invocable entry point to the existing offline CLI. It adds
no build rules and does not fetch or select sources implicitly.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from infinity_db.cli import main as infinity_db_main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Immutable Army ZIP")
    parser.add_argument("--manifest", type=Path, required=True, help="Matching v3 provenance")
    parser.add_argument(
        "--db-dir", type=Path, default=Path("data/generated"),
        help="Complete runtime set destination (default: data/generated)",
    )
    args = parser.parse_args(argv)
    return infinity_db_main([
        "build", str(args.source),
        "--snapshot-manifest", str(args.manifest),
        "--db-dir", str(args.db_dir),
        "--compact",
    ])


if __name__ == "__main__":
    raise SystemExit(main())
