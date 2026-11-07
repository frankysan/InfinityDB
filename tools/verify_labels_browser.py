#!/usr/bin/env python3
"""Optional Chromium catalog-to-definition acceptance for all current Labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from infinity_db.curated import load_curated_directory
from tools.verify_ammunition_browser import ROOT, verify


def source_names(root: Path = ROOT) -> dict[str, str]:
    """Select current curated Label identities; reject conflicting definitions."""
    names: dict[str, str] = {}
    for _, document in load_curated_directory(root / "data/curated"):
        if document["collection"]["status"] != "current":
            continue
        for label in document["labels"]:
            slug, name = label["id"], label["name"]
            if slug in names and names[slug] != name:
                raise ValueError(f"Conflicting current Label name: {slug}")
            names[slug] = name
    return names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args(argv)
    report = verify(
        args.base_url,
        headed=args.headed,
        catalog="labels",
        expected_names=source_names(),
    )
    if args.output is not None:
        args.output.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(f"Labels browser navigation: {report['passed']}/{report['total']} passed")
    for item in report["results"]:
        if item["status"] == "failed":
            print(f"  {item['width']}px {item['slug']}: {item['error']}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
