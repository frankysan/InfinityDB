#!/usr/bin/env python3
"""Optional Chromium acceptance of all current State catalog/detail pages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from infinity_db.curated import load_curated_directory
from tools.verify_ammunition_browser import ROOT, verify


def source_states(root: Path = ROOT) -> dict[str, str]:
    """Return current source-authored States, preserving exact route identities."""
    result: dict[str, str] = {}
    for _, document in load_curated_directory(root / "data/curated"):
        if document["collection"]["status"] != "current":
            continue
        for record in document["records"]:
            if record["kind"] != "state":
                continue
            record_id = record["id"]
            if not record_id.startswith("state:") or record_id.count(":") != 1:
                raise ValueError(f"Invalid State route identity: {record_id}")
            slug = record_id.removeprefix("state:")
            if slug in result:
                raise ValueError(f"Duplicate State source identity: {record_id}")
            result[slug] = record["name"]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args(argv)
    report = verify(
        args.base_url,
        headed=args.headed,
        catalog="states",
        expected_names=source_states(),
    )
    if args.output is not None:
        args.output.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(f"States browser navigation: {report['passed']}/{report['total']} passed")
    for item in report["results"]:
        if item["status"] == "failed":
            print(f"  {item['width']}px {item['slug']}: {item['error']}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
