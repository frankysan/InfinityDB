#!/usr/bin/env python3
"""Compare cross-platform determinism manifests and fail on any byte drift."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EXPECTED_FORMAT = "InfinityDB cross-platform determinism manifest"
EXPECTED_FORMAT_VERSION = 1


def _load(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("format") != EXPECTED_FORMAT:
        raise ValueError(f"Unexpected determinism manifest format: {path}")
    if document.get("formatVersion") != EXPECTED_FORMAT_VERSION:
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
    parser.add_argument("root", type=Path, help="Directory containing downloaded manifests")
    args = parser.parse_args(argv)

    paths = sorted(args.root.rglob("determinism-manifest.json"))
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
