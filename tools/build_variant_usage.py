"""Build a source-verified, read-only candidate Rule/Variant Unit-usage projection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from infinity_db.variant_usage import (
    build_variant_usage_from_normalized,
    build_variant_usage_projection,
    validate_variant_usage_candidate,
)

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    destinations = parser.add_mutually_exclusive_group()
    destinations.add_argument(
        "--output", type=Path,
        help="optional ignored local/*.json candidate; no tracked release publication",
    )
    destinations.add_argument(
        "--check", type=Path,
        help="verify an existing candidate against the exact current inputs without writing",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--raw-db", type=Path,
        help="Explicit validated, paired Army raw archive for source-only inspection",
    )
    source.add_argument(
        "--normalized", type=Path,
        help="Explicit normalized.json bound to the selected Army export generation",
    )
    parser.add_argument(
        "--army-db", type=Path, default=ROOT / "data/generated/army.db",
    )
    parser.add_argument(
        "--rules-db", type=Path, default=ROOT / "data/generated/rules_n5.db",
    )
    args = parser.parse_args()
    result = (
        build_variant_usage_from_normalized(
            args.army_db, args.normalized, args.rules_db,
        )
        if args.normalized is not None
        else build_variant_usage_projection(args.army_db, args.raw_db, args.rules_db)
    )
    if args.check is not None:
        validate_variant_usage_candidate(ROOT / args.check, result)
    if args.output is not None:
        destination = (ROOT / args.output).resolve()
        local_root = (ROOT / "local").resolve()
        if (
            destination.parent != local_root
            or destination.suffix != ".json"
            or not destination.name.startswith("variant-usage-")
        ):
            parser.error("--output must be local/variant-usage-*.json")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(destination)
    print(json.dumps({
        "scope": result["scope"],
        "variantGroups": len(result["variants"]),
        "reviewedSourceRows": sum(
            entry["sourceRelationshipRows"] for entry in result["variants"]
        ),
        "familyOnlyRules": len(result["familyOnlyUniqueUnitCounts"]),
        "unresolvedRows": len(result["unresolvedSourceRows"]),
        "unresolvedCounts": result["diagnosticCounts"],
        "includeEdges": len(result["relationships"]["includes"]),
        "includePaths": len(result["relationships"]["includePaths"]),
        "peripheralAttachments": len(result["relationships"]["peripheralAttachments"]),
        "peripheralControllerEdges": len(
            result["relationships"]["peripheralControllerEdges"]
        ),
        "sourceSnapshot": result["sourceSnapshot"],
        "output": str(args.output) if args.output is not None else None,
    }, indent=2))


if __name__ == "__main__":
    main()
