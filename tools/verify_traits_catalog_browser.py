#!/usr/bin/env python3
"""Optional Chromium catalog-to-detail acceptance for 33 canonical Traits."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from infinity_db.curated import load_curated_directory
from infinity_db.database.repository import Database
from infinity_db.trait_wiki_references import load_trait_wiki_references
from tools.verify_ammunition_browser import ROOT, verify


def source_traits(root: Path = ROOT) -> dict[str, str]:
    """Select reviewed canonical Trait identities independently of Army labels."""
    traits: dict[str, str] = {}
    for _, document in load_curated_directory(root / "data/curated"):
        if document["collection"]["status"] != "current":
            continue
        for record in document["records"]:
            if record["kind"] != "trait":
                continue
            identity = record["id"]
            if not identity.startswith("trait:") or identity.count(":") != 1:
                raise ValueError(f"Invalid canonical Trait identity: {identity}")
            slug = identity.removeprefix("trait:")
            if slug in traits:
                raise ValueError(f"Duplicate canonical Trait identity: {identity}")
            traits[slug] = record["name"]
    return traits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args(argv)
    traits = source_traits()
    wiki = load_trait_wiki_references()
    urls = {identity.removeprefix("trait:"): ref["url"] for identity, ref in wiki.items()}
    if set(traits) != set(urls):
        raise ValueError("Canonical Traits and curated Wiki destinations differ")
    raw = Database(ROOT / "data/generated/infinity.db").list_traits()
    report = verify(
        args.base_url,
        headed=args.headed,
        catalog="traits",
        expected_names=traits,
        expected_wiki_urls=urls,
        allowed_raw_trait_slugs={row["slug"] for row in raw},
    )
    if args.output is not None:
        args.output.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(f"Traits catalog browser navigation: {report['passed']}/{report['total']} passed")
    for item in report["results"]:
        if item["status"] == "failed":
            print(f"  {item['width']}px {item['slug']}: {item['error']}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
