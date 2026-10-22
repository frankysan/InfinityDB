#!/usr/bin/env python3
"""Optional browser acceptance for every curated Ammunition catalog identity.

Run against the current InfinityDB development server. Source/WSGI parity has
a separate hermetic test; this checks actual player navigation and rendering.
"""

from __future__ import annotations

import argparse
import importlib
import json
from functools import partial
from pathlib import Path
from typing import Any

from infinity_db.curated import load_curated_directory

ROOT = Path(__file__).resolve().parents[1]
WIDTHS = (1440, 390, 320)


def source_names(root: Path = ROOT) -> dict[str, str]:
    """Identify the complete source-owned Ammunition set without URL guesses."""
    return {
        record["id"].removeprefix("ammunition:"): record["name"]
        for _, document in load_curated_directory(root / "data/curated")
        for record in document["records"]
        if record["kind"] == "ammunition"
    }


def _record_page_error(errors: list[str], error: Any) -> None:
    errors.append(str(error))


def verify(
    base_url: str,
    *,
    headed: bool = False,
    catalog: str = "ammunition",
    expected_names: dict[str, str] | None = None,
    expected_record_ids: dict[str, str] | None = None,
    expected_wiki_urls: dict[str, str] | None = None,
    allowed_raw_trait_slugs: set[str] | None = None,
) -> dict[str, Any]:
    """Check all catalog links and their player-visible detail content."""
    if catalog not in {"ammunition", "labels", "rules", "states", "traits"}:
        raise ValueError(f"Unsupported reference catalog: {catalog}")
    expected = source_names() if expected_names is None else expected_names
    required = {"ammunition": 11, "labels": 24, "rules": 21, "states": 24, "traits": 33}[catalog]
    if len(expected) != required:
        raise ValueError(f"Expected {required} reviewed {catalog} entries; found {len(expected)}")
    if catalog == "rules" and (
        expected_record_ids is None or set(expected_record_ids) != set(expected)
    ):
        raise ValueError("General Rules require a complete slug-to-record-ID mapping")
    if catalog == "traits" and (
        expected_wiki_urls is None or set(expected_wiki_urls) != set(expected)
    ):
        raise ValueError("Traits require a complete reviewed Wiki destination mapping")
    try:
        playwright = importlib.import_module("playwright.sync_api")
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is required; install it with 'python -m pip install playwright' "
            "and 'python -m playwright install chromium'"
        ) from exc

    base = base_url.rstrip("/")
    observations: list[dict[str, Any]] = []
    with playwright.sync_playwright() as driver:
        browser = driver.chromium.launch(headless=not headed)
        try:
            for width in WIDTHS:
                context = browser.new_context(viewport={"width": width, "height": 844})
                try:
                    response = context.request.get(f"{base}/{catalog}", timeout=15000)
                    if response.status != 200 or f'data-catalog="{catalog}"' not in response.text():
                        raise RuntimeError(
                            f"{base}/{catalog} is not served by the current InfinityDB app "
                            f"(HTTP {response.status}); check --base-url and restart the app"
                        )
                    page = context.new_page()
                    errors: list[str] = []
                    page.on("pageerror", partial(_record_page_error, errors))
                    page.goto(f"{base}/{catalog}", wait_until="domcontentloaded")
                    page.locator("#catalog-list a").first.wait_for(state="visible")
                    hrefs = set(page.locator("#catalog-list a").evaluate_all(
                        "(anchors) => anchors.map((anchor) => anchor.getAttribute('href'))"
                    ))
                    expected_hrefs = {f"/{catalog}/{slug}" for slug in expected}
                    extra_hrefs = hrefs - expected_hrefs
                    allowed_hrefs = (
                        {f"/traits/{slug}" for slug in (allowed_raw_trait_slugs or set())}
                        if catalog == "traits" else set()
                    )
                    if expected_hrefs - hrefs or extra_hrefs - allowed_hrefs:
                        raise AssertionError(
                            f"Catalog links differ: missing={sorted(expected_hrefs - hrefs)} "
                            f"unexpected={sorted(extra_hrefs - allowed_hrefs)}"
                        )
                    for slug, name in sorted(expected.items()):
                        observation: dict[str, Any] = {
                            "width": width, "slug": slug, "expectedName": name
                        }
                        try:
                            link = page.locator(f'#catalog-list a[href="/{catalog}/{slug}"]')
                            link.click()
                            if catalog in {"ammunition", "states", "traits"}:
                                rule_kind = {
                                    "ammunition": "ammunition",
                                    "states": "state",
                                    "traits": "trait",
                                }[catalog]
                                selector = f"#rule-{rule_kind}-{slug}"
                            elif catalog == "rules":
                                assert expected_record_ids is not None
                                record_id = expected_record_ids[slug]
                                selector = f"#rule-{record_id.replace(':', '-')}"
                            else:
                                selector = "#item-content .reference-detail-section .detail-copy"
                            page.locator(selector).wait_for(state="visible")
                            actual_name = page.locator("#item-name").evaluate(
                                "(element) => element.firstChild.textContent"
                            )
                            if actual_name != name:
                                raise AssertionError(
                                    f"Heading mismatch: {actual_name!r} != {name!r}"
                                )
                            if catalog in {"ammunition", "rules", "states", "traits"}:
                                citations = page.locator("#item-content .detail-source")
                                if not citations.first.is_visible():
                                    raise AssertionError("Source citations are not visible")
                                if catalog == "traits":
                                    assert expected_wiki_urls is not None
                                    source_link = page.locator("#trait-wiki-link")
                                    if not source_link.is_visible():
                                        raise AssertionError("Official Wiki link is not visible")
                                    href = source_link.get_attribute("href")
                                    if href != expected_wiki_urls[slug]:
                                        raise AssertionError("Unexpected Wiki destination")
                                    if source_link.get_attribute("rel") != "noopener noreferrer":
                                        raise AssertionError("Wiki link lacks noopener noreferrer")
                            elif not page.locator(selector).inner_text().strip():
                                raise AssertionError("Label definition is empty")
                            if page.locator("#item-status").is_visible():
                                raise AssertionError("Loading/error panel is still visible")
                            overflow = page.evaluate(
                                "() => document.documentElement.scrollWidth > window.innerWidth + 1"
                            )
                            if overflow:
                                raise AssertionError("Page-level horizontal overflow")
                            if errors:
                                raise AssertionError(f"JavaScript errors: {errors}")
                            observation["status"] = "passed"
                        except Exception as exc:
                            observation.update(status="failed", error=str(exc))
                        observations.append(observation)
                        # Re-open the same public catalog to keep the navigation
                        # context deterministic even after an assertion failure.
                        page.goto(f"{base}/{catalog}", wait_until="domcontentloaded")
                        page.locator("#catalog-list a").first.wait_for(state="visible")
                finally:
                    context.close()
        finally:
            browser.close()
    return {
        "format": f"InfinityDB {catalog.title()} browser acceptance",
        "baseUrl": base,
        "sourceRecordCount": len(expected),
        "widths": list(WIDTHS),
        "total": len(observations),
        "passed": sum(item["status"] == "passed" for item in observations),
        "results": observations,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args(argv)
    report = verify(args.base_url, headed=args.headed)
    if args.output is not None:
        args.output.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(f"Ammunition browser navigation: {report['passed']}/{report['total']} passed")
    for item in report["results"]:
        if item["status"] == "failed":
            print(f"  {item['width']}px {item['slug']}: {item['error']}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
