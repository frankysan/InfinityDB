"""Compare the pinned legacy compressed symbol paths to external canonical mapping."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def compare_paths(legacy_root: Path, duplicate_receipt: Path) -> dict:
    receipt = json.loads(duplicate_receipt.read_text(encoding="utf-8"))
    if receipt.get("stage") != "duplicateDetection" or receipt.get("status") != "passed":
        raise ValueError("Expected passed duplicate detection receipt")
    mapping = receipt["canonicalByArchivePath"]
    canonical = set(mapping.values())
    legacy = {
        path.relative_to(legacy_root).as_posix()
        for path in legacy_root.rglob("*.svg")
    }
    return {
        "externalCanonicalCount": len(canonical),
        "legacyCanonicalCount": len(legacy),
        "externalOnly": sorted(canonical - legacy),
        "legacyOnly": sorted(legacy - canonical),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-root", type=Path, required=True)
    parser.add_argument("--duplicate-receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = compare_paths(args.legacy_root, args.duplicate_receipt)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0 if not result["externalOnly"] and not result["legacyOnly"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
