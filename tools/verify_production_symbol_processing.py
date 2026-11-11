"""Verify the pinned P5 production compression handoff and inspect legacy paths.

Read-only, local evidence; does not publish assets.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.compare_symbol_canonical_paths import compare_paths
from tools.verify_processed_symbol_handoff import verify_processed_symbol_handoff


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--effective-stem", default="EFFECTIVE-SYMBOLS 20261111-204139")
    parser.add_argument(
        "--legacy-root",
        default="data/work/symbols/SYMBOLS 20261004-184813--cda970bafe15/compressed",
    )
    args = parser.parse_args(argv)
    stem = args.effective_stem
    if not stem.startswith("EFFECTIVE-SYMBOLS ") or any(
        value in stem for value in ("/", "\\", "..")
    ):
        parser.error("Expected a safe EFFECTIVE-SYMBOLS timestamp stem")
    sibling = Path.cwd().parent / "InfinityDB-symbol-tools"
    processed = sibling / "local/p5-production-processed" / stem
    reports = sibling / "local/p5-production-reports" / stem
    inputs = [
        processed / "CANONICAL.zip",
        processed / "text-conversion-state.json",
        processed / "COMPRESSED.zip",
        processed / "compression-state.json",
        processed / "compression-report.csv",
        processed / "compression-candidates.csv",
        processed / "compression-run.json",
    ]
    try:
        verified = verify_processed_symbol_handoff(*inputs)
        paths = compare_paths(Path(args.legacy_root), reports / "duplicate-state.json")
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(json.dumps({"verified": verified, "paths": paths}, indent=2))
    return 0 if not paths["externalOnly"] and not paths["legacyOnly"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
