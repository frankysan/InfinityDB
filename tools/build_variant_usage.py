"""Build a source-verified, read-only candidate Rule/Variant Unit-usage projection."""

from __future__ import annotations

import argparse
import json
import os
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
    destination: Path | None = None
    if args.output is not None:
        candidate = (ROOT / args.output).resolve()
        local_root = (ROOT / "local").resolve()
        if (
            candidate.parent != local_root
            or candidate.suffix != ".json"
            or not candidate.name.startswith("variant-usage-")
        ):
            parser.error("--output must be local/variant-usage-*.json")
        if (ROOT / args.output).is_symlink() or candidate.exists() or candidate.is_symlink():
            parser.exit(1, f"Variant usage candidate already exists: {args.output}\n")
        destination = candidate
    result = (
        build_variant_usage_from_normalized(
            args.army_db, args.normalized, args.rules_db,
        )
        if args.normalized is not None
        else build_variant_usage_projection(args.army_db, args.raw_db, args.rules_db)
    )
    if args.check is not None:
        validate_variant_usage_candidate(ROOT / args.check, result)
    if destination is not None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".json.tmp")
        created = False
        try:
            with temporary.open("x", encoding="utf-8", newline="\n") as output:
                created = True
                output.write(
                    json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
                )
            # Preserve the staged, complete candidate without an overwriting rename.
            os.link(temporary, destination)
        except FileExistsError as exc:
            parser.exit(1, f"Variant usage candidate already exists: {exc}\n")
        finally:
            if created:
                temporary.unlink(missing_ok=True)
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
