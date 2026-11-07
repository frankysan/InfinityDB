#!/usr/bin/env python3
"""Optional Chromium acceptance for every canonical Trait Wiki link.

Requires a running InfinityDB app, Playwright/Chromium, and a saved official
Traits HTML snapshot. The external Wiki response is served from that snapshot,
so the test does not depend on third-party requests or change server data.
"""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from infinity_db.trait_wiki_references import load_trait_wiki_references
from tools.audit_trait_wiki_anchors import audit_html


def _browser_html(source_html: str) -> str:
    """Keep the original headings and allow every target to scroll near the top."""
    spacer = '<div aria-hidden="true" style="height:2000px"></div>'
    before, separator, after = source_html.rpartition("</body>")
    return before + spacer + separator + after if separator else source_html + spacer


def _validate_trait_page_response(status: int, html: str, base: str) -> None:
    """Fail once on a wrong/stale app target instead of reporting 33 unrelated 404s."""
    if status != 200:
        raise RuntimeError(
            f"Browser target {base!r} returned HTTP {status} for /traits/boost. "
            "The current InfinityDB source registers /traits/<slug> routes. "
            "Check which process or container serves --base-url, and use a "
            "running instance built from the current checkout."
        )
    if 'data-catalog="traits"' not in html or 'id="trait-wiki-link"' not in html:
        raise RuntimeError(
            f"Browser target {base!r} does not serve the current Trait detail template. "
            "Restart/rebuild the local app using this checkout and verify --base-url."
        )


def _observe_wiki_heading(popup: Any) -> dict[str, Any]:
    """Read the browser's actual hash target and scroll position."""
    return popup.evaluate(
        """() => {
          const fragment = decodeURIComponent(window.location.hash.slice(1));
          const heading = document.getElementById(fragment);
          const rect = heading?.getBoundingClientRect();
          return {
            fragment,
            exists: Boolean(heading),
            top: rect ? rect.top : null,
            scrollY: window.scrollY
          };
        }"""
    )


def verify(
    base_url: str,
    source_html: str,
    *,
    headed: bool = False,
    timeout_ms: int = 15000,
) -> dict[str, Any]:
    """Visit all 33 public pages as a non-developer user and click the Wiki links."""
    references = load_trait_wiki_references()
    source_audit = audit_html(source_html, references)
    if source_audit["failures"]:
        raise ValueError(
            f"Wiki HTML fails source audit: "
            f"{source_audit['matchedCount']}/{source_audit['mappingCount']} matched"
        )

    try:
        playwright = importlib.import_module("playwright.sync_api")
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is required: install playwright, then run "
            "'python -m playwright install chromium'"
        ) from exc

    base = base_url.rstrip("/")
    wiki_html = _browser_html(source_html)
    outcomes: list[dict[str, Any]] = []
    with playwright.sync_playwright() as driver:
        browser = driver.chromium.launch(headless=not headed)
        try:
            context = browser.new_context(viewport={"width": 390, "height": 844})
            try:
                # Do not contact the live Wiki, third-party CDNs, or analytics.
                def route_request(route: Any) -> None:
                    url = route.request.url
                    parsed = urlsplit(url)
                    if url.startswith(f"{base}/"):
                        route.continue_()
                    elif (
                        parsed.scheme == "https"
                        and parsed.hostname == "infinitythewiki.com"
                        and parsed.path == "/Traits"
                    ):
                        route.fulfill(
                            status=200, content_type="text/html; charset=utf-8", body=wiki_html
                        )
                    else:
                        route.abort()

                context.route("**/*", route_request)
                preflight = context.request.get(f"{base}/traits/boost", timeout=timeout_ms)
                _validate_trait_page_response(preflight.status, preflight.text(), base)
                page = context.new_page()
                page.set_default_timeout(timeout_ms)
                for trait_id, entry in sorted(references.items()):
                    slug = trait_id.removeprefix("trait:")
                    record: dict[str, Any] = {"traitId": trait_id, "name": entry["name"]}
                    popup = None
                    try:
                        response = page.goto(
                            f"{base}/traits/{slug}", wait_until="domcontentloaded"
                        )
                        if response is None or not response.ok:
                            status = response.status if response else "-"
                            raise AssertionError(f"Trait page HTTP {status}")
                        if page.locator("html").get_attribute("data-developer-mode") == "true":
                            raise AssertionError("Developer Mode must be disabled")
                        link = page.locator("#trait-wiki-link")
                        link.wait_for(state="visible")
                        if link.get_attribute("href") != entry["url"]:
                            raise AssertionError("Visible Wiki href differs from curated mapping")
                        if link.get_attribute("target") != "_blank":
                            raise AssertionError("Wiki link does not open in a new tab")
                        rel = set((link.get_attribute("rel") or "").split())
                        if not {"noopener", "noreferrer"} <= rel:
                            raise AssertionError("Wiki link missing safe external-tab attributes")
                        # noopener can make the new tab independent of its opener.
                        with context.expect_page() as opened:
                            link.click()
                        popup = opened.value
                        popup.wait_for_url("https://infinitythewiki.com/Traits*")
                        popup.wait_for_load_state("domcontentloaded")
                        popup.wait_for_timeout(150)
                        expected = unquote(urlsplit(entry["url"]).fragment)
                        observation = _observe_wiki_heading(popup)
                        if observation["fragment"] != expected or not observation["exists"]:
                            raise AssertionError("Popup did not resolve the expected heading")
                        if observation["top"] is None or abs(observation["top"]) > 180:
                            raise AssertionError(
                                f"Popup did not scroll to heading (top={observation['top']})"
                            )
                        record.update({
                            "status": "passed",
                            "fragment": observation["fragment"],
                            "headingTopPx": observation["top"],
                            "popupUrl": popup.url,
                        })
                    except Exception as exc:
                        record.update({"status": "failed", "error": str(exc)})
                    finally:
                        if popup is not None:
                            popup.close()
                    outcomes.append(record)
            finally:
                context.close()
        finally:
            browser.close()
    return {
        "format": "InfinityDB Trait Wiki browser acceptance",
        "baseUrl": base,
        "sourceMatchedCount": source_audit["matchedCount"],
        "total": len(references),
        "passed": sum(record["status"] == "passed" for record in outcomes),
        "results": outcomes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--wiki-html", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args(argv)
    report = verify(
        args.base_url,
        args.wiki_html.read_text(encoding="utf-8-sig"),
        headed=args.headed,
    )
    if args.output:
        args.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(f"Trait Wiki browser navigation: {report['passed']}/{report['total']} passed")
    for result in report["results"]:
        if result["status"] != "passed":
            print(f"  {result['traitId']}: {result['error']}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
