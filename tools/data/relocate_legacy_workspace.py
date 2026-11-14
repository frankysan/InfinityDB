"""Relocate obsolete in-tree processing artifacts into ignored local/archive.

One-time cleanup helper. Preview by default; --apply renames files/directories
in place without copying, overwriting, or deleting their contents.
"""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Original histories are retained individually, not merged into active work.
RELOCATIONS = (
    ("data/work/symbols", "local/archive/symbols/work"),
    ("data/reports/symbols", "local/archive/symbols/reports"),
    ("data/logs/symbols", "local/archive/symbols/logs"),
    ("data/backups/symbols", "local/archive/symbols/backups"),
    ("data/manifests/army-symbol-build.json", "local/archive/symbols/army-symbol-build.json"),
    ("data/work/its/its_18.db", "local/archive/its/its_18-legacy-output.db"),
    ("data/runtime", "local/archive/runtime/pre-direct-database-set"),
)


def relocate(root: Path, *, apply: bool) -> tuple[int, int]:
    pending: list[tuple[Path, Path]] = []
    existing = 0
    for source_name, target_name in RELOCATIONS:
        source, target = root / source_name, root / target_name
        if source.is_symlink() or target.is_symlink():
            raise ValueError(f"Link refused: {source_name}")
        if source.exists():
            if target.exists():
                raise ValueError(f"Destination occupied: {target_name}")
            if source.is_dir() and not any(source.iterdir()):
                print(f"Empty source, unchanged: {source_name}")
                continue
            pending.append((source, target))
        elif target.exists():
            existing += 1
            print(f"Already relocated: {source_name}")
        else:
            print(f"Not present: {source_name}")
    for source, target in pending:
        action = "Moving" if apply else "Would move"
        print(f"{action}: {source.relative_to(root)} -> {target.relative_to(root)}")
        if apply:
            target.parent.mkdir(parents=True, exist_ok=True)
            source.rename(target)
    status = "moved" if apply else "pending"
    print(f"Historical artifacts: {len(pending)} {status}, {existing} already local")
    return len(pending), existing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        relocate(ROOT, apply=args.apply)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Legacy relocation stopped: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
