"""Audit or checkpoint maintained rules prose that still needs semantic links."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from infinity_db.curated import load_curated_directory
from infinity_db.maintained_text_policy import (
    BASELINE_FILENAME,
    build_maintained_text_link_baseline,
    collect_unlinked_reference_candidates,
    validate_maintained_text_link_baseline,
)

DEFAULT_RULES = Path("data/curated/rules")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rules", nargs="?", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Rewrite the legacy migration baseline after a reviewed link-migration batch.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    documents = load_curated_directory(args.rules)
    baseline_path = args.baseline or args.rules.parent / BASELINE_FILENAME
    candidates = collect_unlinked_reference_candidates(documents)
    by_namespace: Counter[str] = Counter()
    for values in candidates.values():
        for (_, _, targets), count in values.items():
            namespaces = {target.partition(":")[0] for target in targets}
            for namespace in namespaces:
                by_namespace[namespace] += count

    occurrence_count = sum(sum(values.values()) for values in candidates.values())
    print(
        f"Unlinked maintained-text candidates: {occurrence_count} occurrence(s) "
        f"across {len(candidates)} owner(s)"
    )
    if by_namespace:
        print(
            "Candidate target namespaces: "
            + ", ".join(f"{key}={value}" for key, value in sorted(by_namespace.items()))
        )

    if args.write_baseline:
        baseline = build_maintained_text_link_baseline(documents)
        baseline_path.write_text(
            json.dumps(baseline, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"Wrote reviewed legacy baseline: {baseline_path}")
        return 0

    validate_maintained_text_link_baseline(documents, baseline_path)
    print(f"Legacy baseline matches: {baseline_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
