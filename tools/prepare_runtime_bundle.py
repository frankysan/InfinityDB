"""Prepare a minimal, verified runtime-data directory for immutable Docker images.

Deployment packages already-built artifacts; it never regenerates rules or Army
data inside the image. Only current database sets with embedded deployed
objects are supported; loose legacy deployed-object JSON is never packaged.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from infinity_db.database_set import validate_database_set

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data/generated"
DEFAULT_OUTPUT = ROOT / "data/runtime"


def expected_files(source: Path) -> set[str]:
    """Validate the exact source pair and select schema-specific files."""
    result = validate_database_set(source)
    if result["deployedObjects"] != 17 or result["unresolvedDeliveries"] != 1:
        raise ValueError("Incomplete reviewed deployed objects")
    return set(result["sha256"])


def prepare_bundle(source: Path, output: Path) -> set[str]:
    """Create only the verified runtime files; do not alter source artifacts."""
    source, output = source.resolve(), output.resolve()
    if source == output or source.is_relative_to(output) or output.is_relative_to(source):
        raise ValueError("Runtime source and output directories must be independent")
    names = expected_files(source)
    output.mkdir(parents=True, exist_ok=True)
    for entry in output.iterdir():
        if not entry.is_file():
            raise ValueError("Runtime bundle contains an unexpected subdirectory")
        entry.unlink()
    for name in sorted(names):
        shutil.copyfile(source / name, output / name)
    if {p.name for p in output.iterdir()} != names:
        raise ValueError("Incomplete runtime bundle")
    if expected_files(output) != names:
        raise ValueError("Runtime bundle failed after copying")
    return names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    if args.output_dir.resolve() != DEFAULT_OUTPUT.resolve():
        parser.error("Docker runtime data must be staged under data/runtime/")
    names = prepare_bundle(args.source_dir, args.output_dir)
    print(f"Prepared immutable image data: {', '.join(sorted(names))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
