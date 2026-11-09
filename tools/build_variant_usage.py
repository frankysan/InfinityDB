"""Build a source-verified, read-only candidate Rule/Variant Unit-usage projection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from infinity_db.variant_usage import (
    build_variant_usage_projection,
    validate_variant_usage_candidate,
)
from infinity_db.variant_usage_reference import publication_from_candidate

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
    destinations.add_argument(
        "--publish", action="store_true",
        help="write the generated read-only exact-variant API publication",
    )
    destinations.add_argument(
        "--check-publication", action="store_true",
        help="verify the generated exact-variant API publication without writing",
    )
    args = parser.parse_args()
    result = build_variant_usage_projection(
        ROOT / "data/generated/infinity.db",
        ROOT / "data/generated/infinity.raw.db",
        ROOT / "data/generated/rules.db",
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
    if args.publish or args.check_publication:
        destination = ROOT / "data/generated/variant-usage.json"
        expected = (
            json.dumps(
                publication_from_candidate(result),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            ) + "\n"
        ).encode("utf-8")
        if args.check_publication:
            if not destination.is_file() or destination.read_bytes() != expected:
                raise SystemExit("Variant usage publication missing or stale; rebuild it")
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(".json.tmp")
            temporary.write_bytes(expected)
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
        "publication": "data/generated/variant-usage.json"
        if args.publish or args.check_publication else None,
    }, indent=2))


if __name__ == "__main__":
    main()
