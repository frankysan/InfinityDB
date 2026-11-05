"""Build a source-verified, read-only candidate Rule/Variant Unit-usage projection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from infinity_db.variant_usage import build_variant_usage_projection

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path,
        help="optional ignored local/*.json candidate; no tracked release publication",
    )
    args = parser.parse_args()
    result = build_variant_usage_projection(
        ROOT / "data/generated/infinity.db",
        ROOT / "data/generated/infinity.raw.db",
        ROOT / "data/generated/rules.db",
        ROOT / "data/generated/deployed-objects.json",
    )
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
        "peripheralControllerEdges": len(
            result["relationships"]["peripheralControllerEdges"]
        ),
        "sourceSnapshot": result["sourceSnapshot"],
        "output": str(args.output) if args.output is not None else None,
    }, indent=2))


if __name__ == "__main__":
    main()
