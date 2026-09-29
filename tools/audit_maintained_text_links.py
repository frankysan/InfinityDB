"""Audit maintained rules prose for semantic-link and manual-review coverage."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from infinity_db.curated import load_curated_directory
from infinity_db.maintained_text_policy import (
    REVIEW_POLICY_FILENAME,
    collect_review_needed_markers,
    collect_reviewed_batch_residuals,
    collect_unlinked_reference_candidates,
    validate_maintained_text_link_coverage,
)

DEFAULT_RULES = Path("data/curated/rules")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rules", nargs="?", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--review-policy", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    documents = load_curated_directory(args.rules)
    review_policy_path = (
        args.review_policy or args.rules.parent / REVIEW_POLICY_FILENAME
    )
    reviewed_residuals = collect_reviewed_batch_residuals(
        documents, review_policy_path
    )
    candidates = collect_unlinked_reference_candidates(
        documents, review_policy_path=review_policy_path
    )
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

    reviewed_residual_count = sum(
        sum(values.values()) for values in reviewed_residuals.values()
    )
    print(
        f"Reviewed-batch residuals: {reviewed_residual_count} occurrence(s) "
        f"across {len(reviewed_residuals)} owner(s)"
    )
    for owner, values in sorted(reviewed_residuals.items()):
        ordered = sorted(
            values.items(),
            key=lambda item: (item[0][0], item[0][1], item[0][2]),
        )
        for (batch_id, field, text, targets), count in ordered:
            suffix = f" x{count}" if count != 1 else ""
            print(
                f"  {owner} {field}: {text!r} -> {'/'.join(targets)} "
                f"[{batch_id}]{suffix}"
            )

    review_needed = collect_review_needed_markers(documents)
    review_count = sum(sum(values.values()) for values in review_needed.values())
    print(
        f"Explicit review-needed markers: {review_count} occurrence(s) "
        f"across {len(review_needed)} owner(s)"
    )
    for owner, values in sorted(review_needed.items()):
        ordered = sorted(
            values.items(),
            key=lambda item: (item[0][0], item[0][1], item[0][2] or ""),
        )
        for (field, reason, text), count in ordered:
            display = repr(text) if text is not None else "<standalone marker>"
            suffix = f" x{count}" if count != 1 else ""
            print(f"  {owner} {field}: {display} [{reason}]{suffix}")

    validate_maintained_text_link_coverage(documents, review_policy_path)
    print(f"Maintained-text coverage complete: {review_policy_path}")
    return 0

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
