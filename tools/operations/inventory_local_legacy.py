"""One-time inventory of ignored top-level local/ files for workspace cleanup."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / "local"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=140)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)
    entries = sorted(LOCAL.iterdir(), key=lambda p: p.name.casefold())
    if args.summary:
        roots = Counter("directory" if item.is_dir() else item.suffix.lower() or "(no suffix)"
                        for item in entries)
        print(f"Total: {len(entries)}; types: {dict(roots)}")
        groups = Counter()
        for item in entries:
            name = item.name
            if "recovery" in name or "backup" in name:
                key = "recovery-or-backup"
            elif name.startswith(("p24-", "p25-", "p26-", "p27-", "p5-", "p6-")):
                key = "p-series"
            elif name.startswith(("ci-", "CHECKS ", "label-ci-")):
                key = "CI-diagnostics"
            elif name.startswith(("test-", "test_", "verify-", "verify_")):
                key = "test-diagnostics"
            elif name.startswith(("audit-", "audit_", "review-", "review_")):
                key = "audit-or-review"
            else:
                key = "other"
            groups[key] += 1
        print(f"Candidate groups: {dict(groups)}")
    else:
        for index, path in enumerate(entries[args.offset:args.offset + args.limit],
                                     start=args.offset):
            print(f"{index:03d} {'D' if path.is_dir() else 'F'} {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
