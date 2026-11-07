#!/usr/bin/env python3
"""Check reviewed Trait Wiki fragments against saved official page HTML.

This is an explicit external-source audit. It never downloads pages during
ordinary builds or tests; feed it a locally saved HTML response from /Traits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from infinity_db.trait_wiki_references import load_trait_wiki_references

_VOID_ELEMENTS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
})


class _Headings(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: dict[str, str] = {}
        self._anchor: str | None = None
        self._depth = 0
        self._skip_depth = 0
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = (values.get("class") or "").split()
        if self._anchor is not None:
            if tag not in _VOID_ELEMENTS:
                self._depth += 1
                if self._skip_depth:
                    self._skip_depth += 1
                elif "mw-editsection" in classes:
                    self._skip_depth = 1
            return
        if (
            values.get("id")
            and (
                (tag == "span" and "mw-headline" in classes)
                or tag in {"h2", "h3", "h4"}
            )
        ):
            self._anchor = values["id"]
            self._depth = 1
            self._skip_depth = 0
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._anchor is not None and not self._skip_depth:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._anchor is None or tag in _VOID_ELEMENTS:
            return
        if self._skip_depth:
            self._skip_depth -= 1
        self._depth -= 1
        if self._depth == 0:
            name = " ".join("".join(self._text).split())
            self.anchors[self._anchor] = name
            self._anchor = None
            self._text = []


def audit_html(
    html: str,
    references: dict[str, dict[str, str]],
    canonical_traits: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Require the exact fragment to identify the intended heading."""
    parser = _Headings()
    parser.feed(html)
    matches: list[dict[str, str]] = []
    failures: list[dict[str, str | None]] = []
    for trait_id, entry in sorted(references.items()):
        fragment = unquote(urlsplit(entry["url"]).fragment)
        heading = parser.anchors.get(fragment)
        if heading is not None and heading == entry["name"]:
            matches.append({"traitId": trait_id, "heading": heading, "fragment": fragment})
        else:
            failures.append({
                "traitId": trait_id,
                "expectedHeading": entry["name"],
                "fragment": fragment,
                "actualHeading": heading,
                "status": "missing-fragment" if heading is None else "wrong-heading",
            })
    unmapped: list[dict[str, Any]] = []
    if canonical_traits is not None:
        for trait_id, name in sorted(canonical_traits.items()):
            if trait_id in references:
                continue
            fragments = sorted(
                anchor for anchor, heading in parser.anchors.items() if heading == name
            )
            unmapped.append({
                "traitId": trait_id,
                "name": name,
                "headingIds": fragments,
                "status": (
                    "review-candidate" if len(fragments) == 1
                    else "ambiguous-heading" if fragments else "missing-heading"
                ),
            })
    return {
        "format": "InfinityDB Trait Wiki anchor audit",
        "mappingCount": len(references),
        "matchedCount": len(matches),
        "headingCount": len(parser.anchors),
        "matches": matches,
        "failures": failures,
        "unmappedReview": unmapped,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path, help="Saved HTML of the official /Traits page")
    parser.add_argument("--output", type=Path, help="Optional JSON evidence output")
    parser.add_argument(
        "--inventory-unmapped",
        action="store_true",
        help="List exact source heading IDs for unmapped canonical Traits; never add URLs.",
    )
    args = parser.parse_args(argv)
    canonical_traits = None
    if args.inventory_unmapped:
        from infinity_db.curated import load_curated_directory

        root = Path(__file__).resolve().parents[1]
        canonical_traits = {
            record["id"]: record["name"]
            for _, document in load_curated_directory(root / "data" / "curated")
            for record in document["records"]
            if record["kind"] == "trait"
        }
    raw = args.html.read_bytes()
    report = audit_html(
        raw.decode("utf-8-sig"), load_trait_wiki_references(), canonical_traits
    )
    report["sourceSha256"] = hashlib.sha256(raw).hexdigest()
    if args.output:
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
    print(
        f"Trait Wiki anchors: {report['matchedCount']}/{report['mappingCount']} "
        f"matched ({report['headingCount']} headings parsed)"
    )
    for failure in report["failures"]:
        print(
            f"  {failure['traitId']}: {failure['status']} "
            f"{failure['fragment']!r} (actual: {failure['actualHeading']!r})"
        )
    for candidate in report["unmappedReview"]:
        print(
            f"  {candidate['traitId']}: {candidate['status']} "
            f"{candidate['headingIds']!r}"
        )
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
