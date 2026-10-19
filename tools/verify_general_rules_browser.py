#!/usr/bin/env python3
"""Optional Chromium catalog-to-detail acceptance for all current General Rules."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from infinity_db.application_domains import application_domain, record_matches_domain
from infinity_db.curated import load_curated_directory
from infinity_db.domain_slugs import route_slug_from_qualified_typed_domain_id
from tools.verify_ammunition_browser import ROOT, verify


def source_rules(root: Path = ROOT) -> dict[str, tuple[str, str]]:
    """Select category-scoped General Rules and retain qualified record IDs."""
    domain = application_domain("rules")
    rules: dict[str, tuple[str, str]] = {}
    for _, document in load_curated_directory(root / "data/curated"):
        if document["collection"]["status"] != "current":
            continue
        for record in document["records"]:
            if not record_matches_domain(domain, record):
                continue
            record_id = record["id"]
            slug = route_slug_from_qualified_typed_domain_id(
                record_id, expected_domain="rule", context="General Rule browser identity"
            )
            if slug in rules:
                raise ValueError(f"Duplicate General Rule route slug: {slug}")
            rules[slug] = (record_id, record["name"])
    return rules


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args(argv)
    rules = source_rules()
    report = verify(
        args.base_url,
        headed=args.headed,
        catalog="rules",
        expected_names={slug: name for slug, (_, name) in rules.items()},
        expected_record_ids={slug: record_id for slug, (record_id, _) in rules.items()},
    )
    if args.output is not None:
        args.output.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(f"General Rules browser navigation: {report['passed']}/{report['total']} passed")
    for item in report["results"]:
        if item["status"] == "failed":
            print(f"  {item['width']}px {item['slug']}: {item['error']}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
