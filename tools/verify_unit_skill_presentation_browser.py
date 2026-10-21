#!/usr/bin/env python3
"""Optional Chromium acceptance for Unit detail shared and specific item rows.

The normal Unit API is the expected source. This checks client-rendered DOM
placement and links, not semantic source correctness or every possible Unit.
"""

from __future__ import annotations

import argparse
import importlib
import json
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any
from urllib.parse import quote

from tools.verify_non_skill_army_browser import CASES, WIDTHS

DEFAULT_SLUGS = tuple(case.slug for case in CASES)
BUCKETS = (
    ("skills", "Skills", "skills"),
    ("equipment", "Equipment", "equipment"),
    ("weapons", "Weapons", "weapons"),
    ("training", "Training", None),
    ("attribute_overrides", "Attribute overrides", None),
)


@dataclass(frozen=True)
class ItemExpectation:
    label: str
    name: str
    href: str | None
    quantity: int | None
    extras: tuple[str, ...]


def expected_items(items: dict[str, Any]) -> dict[str, list[ItemExpectation]]:
    """Project API shared/specific items onto rows visible in normal mode."""
    result: dict[str, list[ItemExpectation]] = {}
    for bucket, label, catalog in BUCKETS:
        expected: list[ItemExpectation] = []
        for item in items.get(bucket) or []:
            route_id = item.get("slug") or item.get("id")
            href = f"/{catalog}/{quote(str(route_id), safe='')}" if catalog else None
            expected.append(
                ItemExpectation(
                    label=label,
                    name=str(item.get("name") or bucket.removesuffix("s").title()),
                    href=href,
                    quantity=item.get("quantity"),
                    extras=tuple(
                        str(extra.get("name") or "Extra")
                        for extra in item.get("extras") or []
                        if not extra.get("is_distance")
                    ),
                )
            )
        if expected:
            result[bucket] = expected
    return result


def _matches_row(row: dict[str, Any], item: ItemExpectation) -> bool:
    if not str(row["heading"]).strip().startswith(item.label):
        return False
    if item.href is not None:
        matching = [
            link["text"] for link in row["links"] if link["href"] == item.href
        ]
    else:
        # Classified non-Skills are deliberately unlinked text/spans.
        # Header help anchors may exist, but not Skill catalog links.
        matching = (
            [] if any(
                str(link["href"]).startswith("/skills/") for link in row["links"]
            ) else [row["text"]]
        )
    for text in matching:
        if item.name.casefold() not in str(text).casefold():
            continue
        if item.quantity is not None and int(item.quantity) != 1:
            if f"×{item.quantity}" not in text:
                continue
        if all(extra.casefold() in str(text).casefold() for extra in item.extras):
            return True
    return False


def assert_rendered_items(
    rows: list[dict[str, Any]], items: dict[str, Any], context: str,
) -> int:
    """Require the right row header and rendered item for every visible API entry."""
    matches = 0
    projected = expected_items(items)
    for bucket, label, _ in BUCKETS:
        expected = projected.get(bucket, [])
        if not expected and any(
            str(row["heading"]).strip().startswith(label) for row in rows
        ):
            raise AssertionError(f"{context}: unexpected {bucket} row")
        for item in expected:
            if not any(_matches_row(row, item) for row in rows):
                raise AssertionError(
                    f"{context}: missing {bucket} item {item.name!r} "
                    f"({item.href or 'unlinked'}) in its labeled row"
                )
            matches += 1
    return matches


# Segment by actual profile/loadout summary rows, not document-wide text.
DOM_SNAPSHOT = """() => {
  const rows = (root) => [...root.querySelectorAll('tr')].map((tr) => ({
    heading: tr.cells[0]?.textContent?.trim() || '',
    text: tr.textContent?.trim() || '',
    links: [...tr.querySelectorAll('a[href]')].map((a) => ({
      href: a.getAttribute('href'), text: a.textContent?.trim() || '',
    })),
    summary: tr.classList.contains('profile-summary'),
  }));
  const segments = (root, selector) => {
    const result = [];
    for (const table of root.querySelectorAll(selector)) {
      let active = null;
      for (const row of rows(table)) {
        if (row.summary) {
          active = [];
          result.push(active);
        } else if (active) {
          active.push(row);
        }
      }
    }
    return result;
  };
  return {
    general: [...document.querySelectorAll('.general-profile')].map(rows),
    armies: [...document.querySelectorAll('.army-profile')].map((section) => ({
      name: section.querySelector('summary')?.textContent?.trim() || '',
      profiles: segments(section, '.profile-details-table'),
      loadouts: segments(section, '.loadout-table'),
    })),
    skillHrefs: [...document.querySelectorAll('a[href^="/skills/"]')].map(
      (a) => a.getAttribute('href')
    ),
    overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
  };
}"""


def assert_unit_dom(unit: dict[str, Any], dom: dict[str, Any], slug: str) -> dict[str, int]:
    """Compare visible General and Army-local API projections with scoped DOM rows."""
    general = [
        entry for entry in unit["general_profiles"]
        if entry.get("presentation_visible") is not False
    ]
    if len(dom["general"]) != len(general):
        raise AssertionError(
            f"{slug}: General Profile DOM count {len(dom['general'])} != {len(general)}"
        )
    counts = {"shared": 0, "profiles": 0, "loadouts": 0}
    for index, entry in enumerate(general):
        counts["shared"] += assert_rendered_items(
            dom["general"][index], entry["shared_items"], f"{slug}/general#{index}"
        )
    rendered_armies = dom["armies"]
    consumed: set[int] = set()
    for army in unit["armies"]:
        if not army.get("presentation_visible"):
            continue
        expected_heading = army["name"] + "".join(
            badge["label"] for badge in army.get("availability_badges") or []
        )
        candidates = [
            (i, value) for i, value in enumerate(rendered_armies)
            if i not in consumed and value["name"] == expected_heading
        ]
        if len(candidates) != 1:
            raise AssertionError(
                f"{slug}: cannot uniquely match Army section {army['name']!r}, "
                f"found {len(candidates)}"
            )
        index, rendered = candidates[0]
        consumed.add(index)
        for kind in ("profiles", "loadouts"):
            if len(rendered[kind]) != len(army[kind]):
                raise AssertionError(
                    f"{slug}/{army['name']}: {kind} DOM count "
                    f"{len(rendered[kind])} != API {len(army[kind])}"
                )
            for offset, context in enumerate(army[kind]):
                counts[kind] += assert_rendered_items(
                    rendered[kind][offset],
                    context.get("specific_items") or {},
                    f"{slug}/{army['name']}/{kind}#{offset}",
                )
    if len(consumed) != len(rendered_armies):
        raise AssertionError(f"{slug}: unexpected Army sections in DOM")
    for general_or_army in [
        *(general_item["shared_items"] for general_item in general),
        *(
            context.get("specific_items") or {}
            for army in unit["armies"] if army.get("presentation_visible")
            for kind in ("profiles", "loadouts")
            for context in army[kind]
        ),
    ]:
        for source_marker in general_or_army.get("source_markers") or []:
            marker_slug = source_marker.get("slug") or source_marker.get("id")
            if f"/skills/{quote(str(marker_slug), safe='')}" in dom["skillHrefs"]:
                raise AssertionError(f"{slug}: source marker gained Skill link")
    if dom["overflow"]:
        raise AssertionError(f"{slug}: document horizontal overflow")
    return counts


def _page_error(errors: list[str], error: Any) -> None:
    errors.append(str(error))


def verify(
    base_url: str, *, slugs: tuple[str, ...] = DEFAULT_SLUGS, headed: bool = False,
    channel: str | None = None,
) -> dict[str, Any]:
    try:
        playwright = importlib.import_module("playwright.sync_api")
    except ImportError as exc:
        raise RuntimeError("Install Playwright and Chromium for browser acceptance") from exc
    base = base_url.rstrip("/")
    results: list[dict[str, Any]] = []
    with playwright.sync_playwright() as driver:
        browser = driver.chromium.launch(
            headless=not headed,
            **({"channel": channel} if channel else {}),
        )
        try:
            for width in WIDTHS:
                context = browser.new_context(viewport={"width": width, "height": 900})
                try:
                    for slug in slugs:
                        outcome: dict[str, Any] = {
                            "unit": slug, "width": width, "status": "failed",
                        }
                        page = context.new_page()
                        errors: list[str] = []
                        page.on("pageerror", partial(_page_error, errors))
                        try:
                            response = page.goto(
                                f"{base}/units/{slug}", wait_until="networkidle",
                                timeout=20000,
                            )
                            if response is None or response.status != 200:
                                raise AssertionError("Unit page HTTP response not 200")
                            page.locator("#unit-content").wait_for(state="visible")
                            api = context.request.get(
                                f"{base}/api/units/{slug}", timeout=15000,
                            )
                            if api.status != 200:
                                raise AssertionError(f"Unit API HTTP {api.status}")
                            page.locator(".general-profile").first.wait_for(
                                state="attached", timeout=10000,
                            )
                            page.locator(".army-profile").evaluate_all(
                                "(elements) => elements.forEach(el => el.open = true)"
                            )
                            outcome["counts"] = assert_unit_dom(
                                api.json(), page.evaluate(DOM_SNAPSHOT), slug
                            )
                            if errors:
                                raise AssertionError(f"Browser JS errors: {errors!r}")
                            outcome["status"] = "passed"
                        except Exception as exc:
                            outcome["error"] = str(exc)
                        finally:
                            results.append(outcome)
                            page.close()
                finally:
                    context.close()
        finally:
            browser.close()
    return {
        "format": "InfinityDB Unit Skill presentation browser acceptance",
        "baseUrl": base,
        "passed": sum(r["status"] == "passed" for r in results),
        "total": len(slugs) * len(WIDTHS),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--slug", action="append", dest="slugs")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--channel", help="Installed Chromium channel, e.g. chrome")
    args = parser.parse_args(argv)
    report = verify(
        args.base_url, slugs=tuple(args.slugs) if args.slugs else DEFAULT_SLUGS,
        headed=args.headed, channel=args.channel,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8", newline="\n",
        )
    print(f"Unit Skill browser acceptance: {report['passed']}/{report['total']} passed")
    for entry in report["results"]:
        if entry["status"] != "passed":
            print(f"  {entry['width']}px {entry['unit']}: {entry['error']}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
