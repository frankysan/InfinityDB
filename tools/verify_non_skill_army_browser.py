#!/usr/bin/env python3
"""Optional Chromium acceptance for Army source entries that are not Skills.

Run against a current InfinityDB development server. The maintained pytest
suite covers source-to-API classifications; this covers actual client rendering.
"""

from __future__ import annotations

import argparse
import importlib
import json
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

WIDTHS = (1440, 390, 320)


@dataclass(frozen=True)
class UnitCase:
    slug: str
    source_slug: str
    category: str
    label: str | None = None
    href: str | None = None
    minimum_rows: int = 1


CASES = (
    UnitCase("dragoes", "gizmokit", "equipment", "Gizmokit", "/equipment/gizmokit"),
    UnitCase("minutemen", "medikit", "equipment", "MediKit", "/equipment/medikit"),
    UnitCase("racerbots", "bangbomb", "equipment", "Bangbomb", "/equipment/bangbomb"),
    UnitCase("miyamoto-mushashi", "regular", "training", "Regular"),
    UnitCase("raoul-spector-mercenary-operative", "regular", "training", "Regular"),
    UnitCase("tohaa-team-ops", "infinity-team-ops", "source_markers"),
    UnitCase("corregidor-alguaciles", "bts-3", "attribute_overrides", "BTS=3",
             minimum_rows=3),
)

HEADINGS = {
    "equipment": "Equipment",
    "training": "Training",
    "attribute_overrides": "Attribute overrides",
}


def projected_buckets(unit: dict[str, Any], source_slug: str) -> set[str]:
    """Collect actual buckets from general and Army-local profile/loadout data."""
    found: set[str] = set()
    for profile in unit["general_profiles"]:
        for category, items in profile["shared_items"].items():
            if any(item.get("slug") == source_slug for item in items):
                found.add(category)
    for army in unit["armies"]:
        for group in ("profiles", "loadouts"):
            for profile in army[group]:
                for category, items in profile.get("specific_items", {}).items():
                    if any(item.get("slug") == source_slug for item in items):
                        found.add(category)
    return found


def _record_page_error(errors: list[str], error: Any) -> None:
    errors.append(str(error))


def verify(base_url: str, *, headed: bool = False) -> dict[str, Any]:
    try:
        playwright = importlib.import_module("playwright.sync_api")
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is required: install the package and Chromium using "
            "'python -m pip install playwright' and "
            "'python -m playwright install chromium'"
        ) from exc

    base = base_url.rstrip("/")
    results: list[dict[str, Any]] = []
    with playwright.sync_playwright() as driver:
        browser = driver.chromium.launch(headless=not headed)
        try:
            for width in WIDTHS:
                context = browser.new_context(viewport={"width": width, "height": 900})
                try:
                    for case in CASES:
                        observation: dict[str, Any] = {
                            "width": width,
                            "unit": case.slug,
                            "source": case.source_slug,
                            "status": "failed",
                        }
                        page = context.new_page()
                        errors: list[str] = []
                        page.on("pageerror", partial(_record_page_error, errors))
                        try:
                            response = page.goto(
                                f"{base}/units/{case.slug}",
                                wait_until="networkidle",
                                timeout=20000,
                            )
                            if response is None or response.status != 200:
                                raise AssertionError("Unit detail HTTP response was not 200")
                            page.locator("#unit-content").wait_for(state="visible")
                            page.locator(".general-profile").first.wait_for(state="attached")
                            page.locator(".army-profile").evaluate_all(
                                "(elements) => elements.forEach(element => element.open = true)"
                            )

                            api = context.request.get(
                                f"{base}/api/units/{case.slug}", timeout=15000
                            )
                            if api.status != 200:
                                raise AssertionError(f"Unit API returned HTTP {api.status}")
                            buckets = projected_buckets(api.json(), case.source_slug)
                            if buckets != {case.category}:
                                raise AssertionError(
                                    f"Source buckets {sorted(buckets)} != {[case.category]}"
                                )
                            if page.locator(
                                f'a[href="/skills/{case.source_slug}"]'
                            ).count():
                                raise AssertionError("Non-Skill source gained a Skill link")

                            if case.label is not None:
                                rows = page.locator(
                                    ".general-profile tr,.profile-details-table tr,"
                                    ".loadout-table tr"
                                ).filter(has_text=case.label)
                                if rows.count() < case.minimum_rows:
                                    raise AssertionError(
                                        f"Missing {case.label} rows: {rows.count()}"
                                    )
                                expected_heading = HEADINGS[case.category]
                                valid = rows.evaluate_all(
                                    "(elements, label) => elements.some(row => "
                                    "row.cells[0]?.textContent?.trim().startsWith(label))",
                                    expected_heading,
                                )
                                if not valid:
                                    raise AssertionError(
                                        f"Source row lacks {expected_heading} heading"
                                    )
                            if case.href is not None:
                                links = page.locator(f'a[href="{case.href}"]')
                                expected_count = 1 if case.source_slug == "bangbomb" else 0
                                if links.count() < 1 or (
                                    expected_count and links.count() != expected_count
                                ):
                                    raise AssertionError("Equipment link count differs")
                                destination = context.request.get(
                                    base + case.href, timeout=15000
                                )
                                if destination.status != 200:
                                    raise AssertionError(
                                        f"Equipment destination HTTP {destination.status}"
                                    )
                            if page.evaluate(
                                "() => document.documentElement.scrollWidth > "
                                "window.innerWidth + 1"
                            ):
                                raise AssertionError("Document-level horizontal overflow")
                            if errors:
                                raise AssertionError(f"Browser JS errors: {errors}")
                            observation["status"] = "passed"
                        except Exception as exc:
                            observation["error"] = str(exc)
                        finally:
                            results.append(observation)
                            page.close()
                finally:
                    context.close()
        finally:
            browser.close()

    return {
        "format": "InfinityDB non-Skill Army browser acceptance",
        "baseUrl": base,
        "passed": sum(item["status"] == "passed" for item in results),
        "total": len(CASES) * len(WIDTHS),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args(argv)

    report = verify(args.base_url, headed=args.headed)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8", newline="\n",
        )
    print(f"Non-Skill Army browser acceptance: {report['passed']}/{report['total']} passed")
    for item in report["results"]:
        if item["status"] != "passed":
            print(f"  {item['width']}px {item['unit']}: {item['error']}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
