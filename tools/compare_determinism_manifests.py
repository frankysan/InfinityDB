#!/usr/bin/env python3
"""Compare cross-platform determinism manifests and fail on any byte drift."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EXPECTED_FORMAT = "InfinityDB cross-platform determinism manifest"
SUPPORTED_FORMAT_VERSIONS = frozenset({1, 2})


def _load(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("format") != EXPECTED_FORMAT:
        raise ValueError(f"Unexpected determinism manifest format: {path}")
    version = document.get("formatVersion")
    if type(version) is not int or version not in SUPPORTED_FORMAT_VERSIONS:
        raise ValueError(f"Unexpected determinism manifest version: {path}")
    artifacts = document.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise ValueError(f"Determinism manifest has no artifacts: {path}")
    return document


def compare(paths: list[Path]) -> list[str]:
    if len(paths) < 2:
        raise ValueError("At least two determinism manifests are required")
    documents = [(path, _load(path)) for path in paths]
    baseline_path, baseline = documents[0]
    version = baseline["formatVersion"]
    for path, document in documents[1:]:
        if document["formatVersion"] != version:
            raise ValueError(
                f"Cannot compare determinism manifest v{version} ({baseline_path}) "
                f"with v{document['formatVersion']} ({path}); "
                "regenerate using the same format version on both systems"
            )
    baseline_artifacts = baseline["artifacts"]
    errors: list[str] = []
    for path, document in documents[1:]:
        artifacts = document["artifacts"]
        names = sorted(set(baseline_artifacts) | set(artifacts))
        for name in names:
            expected = baseline_artifacts.get(name)
            actual = artifacts.get(name)
            if expected != actual:
                errors.append(
                    f"{name}: {baseline_path}={expected!r}; {path}={actual!r}"
                )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths", type=Path, nargs="+",
        help="Two or more manifest JSON files, or one directory of determinism-manifest.json files",
    )
    args = parser.parse_args(argv)

    paths = (
        sorted(args.paths[0].rglob("determinism-manifest.json"))
        if len(args.paths) == 1 and args.paths[0].is_dir()
        else args.paths
    )
    try:
        errors = compare(paths)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1
    if errors:
        print("Cross-platform deterministic output mismatch:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Cross-platform deterministic outputs verified across {len(paths)} manifests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
