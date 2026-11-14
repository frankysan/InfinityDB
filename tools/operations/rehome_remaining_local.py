"""One-time relocation of completed staging and one PDF research pin inventory.

No source bytes are modified. Do not reuse this script after the cleanup.
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MOVES = (
    ("local/changelog-v1-review",
     "local/archive/legacy-root/v1-release/changelog-v1-review"),
    ("local/citation-migration-n53",
     "local/archive/legacy-root/rules-research/citation-migration-n53"),
    ("local/hacking-device-citations-n53",
     "local/archive/legacy-root/rules-research/hacking-device-citations-n53"),
    ("local/reviewed-reference-pair",
     "local/archive/legacy-root/reference-review/reviewed-reference-pair"),
    ("local/rules-standalone.db",
     "local/archive/legacy-root/legacy-builds/rules-standalone.db"),
    ("local/pdf-revision-inventory.json",
     "local/research/pdf/revision-inventory.json"),
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    pending: list[tuple[Path, Path]] = []
    complete = 0
    for before, after in MOVES:
        source, destination = ROOT / before, ROOT / after
        if source.is_symlink() or destination.is_symlink():
            parser.error(f"Refusing link: {before}")
        if source.exists() and not destination.exists():
            pending.append((source, destination))
        elif not source.exists() and destination.exists():
            complete += 1
        else:
            parser.error(f"Expected exactly one source or destination: {before}")
    for source, destination in pending:
        print(f"{'Moving' if args.apply else 'Would move'}: "
              f"{source.relative_to(ROOT)} -> {destination.relative_to(ROOT)}")
        if args.apply:
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.rename(destination)
    print(f"{len(pending)} {'moved' if args.apply else 'pending'}, "
          f"{complete} already relocated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
