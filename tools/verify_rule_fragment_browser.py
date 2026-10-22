#!/usr/bin/env python3
"""Optional Chromium acceptance for published Weapon rule fragment links.

Uses the served Weapon and Glossary APIs for discovery, then follows real
rendered links at desktop and narrow widths. No upstream network access.
"""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

WIDTHS = (1440, 390, 320)


def local_fragments(value: Any) -> set[str]:
    """Find local rule references in a nested published detail payload."""
    if isinstance(value, dict):
        reference = value.get("public_reference")
        current = (
            {reference["href"]}
            if isinstance(reference, dict)
            and isinstance(reference.get("href"), str)
            and reference["href"].startswith("#rule-")
            else set()
        )
        for child in value.values():
            current.update(local_fragments(child))
        return current
    if isinstance(value, list):
        found: set[str] = set()
        for child in value:
            found.update(local_fragments(child))
        return found
    return set()


def _get_json(request: Any, url: str) -> dict[str, Any]:
    response = request.get(url, timeout=20000)
    if response.status != 200:
        raise RuntimeError(f"GET {url}: HTTP {response.status}")
    payload: dict[str, Any] = response.json()
    return payload


def weapon_candidates(request: Any, base: str) -> dict[str, set[str]]:
    """Discover pages with potentially rendered local links from served APIs."""
    items = _get_json(request, f"{base}/api/weapons")["items"]
    slugs = {item["slug"] for item in items}
    if len(slugs) != len(items) or len(slugs) < 50:
        raise AssertionError("Unexpected or duplicate Weapon catalog slugs")
    candidates: dict[str, set[str]] = {}
    for slug in sorted(slugs):
        path = quote(slug, safe="")
        fragments = local_fragments(_get_json(request, f"{base}/api/weapons/{path}"))
        if fragments:
            candidates[slug] = fragments
    if "#rule-weapon-mines" not in candidates.get("ap-mine", set()):
        raise AssertionError("Known AP Mine fragment missing from served source")
    return candidates


def glossary_links(request: Any, base: str) -> list[str]:
    entries = _get_json(request, f"{base}/api/glossary")["items"]
    links = {
        item["href"]
        for item in entries
        if isinstance(item.get("href"), str)
        and item["href"].startswith("/weapons/")
        and urlsplit(item["href"]).fragment.startswith("rule-")
    }
    if not links:
        raise AssertionError("No published Glossary-to-Weapon fragment links")
    return sorted(links)


def _ready(page: Any, errors: list[str], network_errors: list[str]) -> None:
    try:
        page.locator("#item-content:not([hidden])").wait_for(
            state="visible", timeout=15000
        )
    except Exception as exc:
        state = page.evaluate(
            """() => ({
              heading: document.querySelector("#item-name")?.textContent || null,
              status: document.querySelector("#item-status")?.textContent || null,
              contentHidden: document.querySelector("#item-content")?.hidden ?? null,
            })"""
        )
        raise AssertionError(
            f"Weapon detail did not render: url={page.url!r}, "
            f"state={state!r}, JS errors={errors!r}, "
            f"network errors={network_errors!r}"
        ) from exc
    if page.locator("#item-status").is_visible():
        raise AssertionError("Weapon detail still reports loading/error")


def _assert_hosted(page: Any, href: str) -> None:
    fragment = urlsplit(href).fragment
    if not fragment.startswith("rule-"):
        raise AssertionError(f"Not a rule-card target: {href}")
    # A late optional-Unit response can replace every card after the initial
    # render. Observe cardinality and visibility in ONE browser evaluation,
    # rather than waiting for one DOM node and counting a later replacement.
    try:
        observed = page.wait_for_function(
            """(id) => {
              const cards = [...document.querySelectorAll("#item-content article[id]")]
                .filter((card) => card.id === id);
              if (!cards.length) return false;
              if (cards.length > 1) return { count: cards.length };
              return cards[0].getClientRects().length ? { count: 1 } : false;
            }""",
            arg=fragment,
            timeout=10000,
        ).json_value()
    except Exception as exc:
        state = page.evaluate(
            """(id) => ({
              count: [...document.querySelectorAll("#item-content article[id]")]
                .filter((card) => card.id === id).length,
              contentHidden: document.querySelector("#item-content")?.hidden ?? null,
              status: document.querySelector("#item-status")?.textContent || null,
            })""",
            fragment,
        )
        raise AssertionError(f"{href}: rendered rule card unavailable: {state!r}") from exc
    if observed["count"] != 1:
        raise AssertionError(
            f"{href}: expected one rendered rule card, got {observed['count']}"
        )


def _assert_target(page: Any, href: str) -> None:
    fragment = urlsplit(href).fragment
    page.wait_for_function(
        "(hash) => window.location.hash === hash",
        arg=f"#{fragment}",
        timeout=10000,
    )
    _assert_hosted(page, href)
    page.wait_for_function(
        """(id) => {
          const card = document.getElementById(id);
          if (!card || !card.getClientRects().length) return false;
          const heading = card.querySelector("header") || card;
          const rect = heading.getBoundingClientRect();
          return rect.width > 0 && rect.height > 0
            && rect.bottom > 0 && rect.top < window.innerHeight;
        }""",
        arg=fragment,
        timeout=10000,
    )


def _check_errors(page: Any, errors: list[str], network_errors: list[str]) -> None:
    if errors or network_errors:
        raise AssertionError(
            f"JavaScript errors: {errors}; network errors: {network_errors}"
        )
    if page.evaluate("() => document.documentElement.scrollWidth > innerWidth + 1"):
        raise AssertionError("Page-level horizontal overflow")


def _record_api_response(response: Any, errors: list[str]) -> None:
    if response.status >= 400 and "/api/" in response.url:
        errors.append(f"HTTP {response.status}: {response.url}")


def _record_failed_request(request: Any, errors: list[str]) -> None:
    failure = str(request.failure)
    # Optional Unit filters can legitimately be aborted during page navigation.
    if "/api/" in request.url and "ERR_ABORTED" not in failure:
        errors.append(f"{request.method} {request.url}: {failure}")


def _record_failure(
    item: dict[str, Any], page: Any, exc: Exception,
    errors: list[str], network_errors: list[str],
) -> None:
    item.update(
        status="failed", error=str(exc), url=page.url,
        jsErrors=list(errors), networkErrors=list(network_errors),
    )


def _watch_page(page: Any, errors: list[str], network_errors: list[str]) -> None:
    page.on("pageerror", lambda exc, sink=errors: sink.append(str(exc)))
    page.on(
        "response",
        lambda response, sink=network_errors: _record_api_response(response, sink),
    )
    page.on(
        "requestfailed",
        lambda request, sink=network_errors: _record_failed_request(request, sink),
    )


def _direct_fragment(source_targets: set[str], rendered_links: list[str]) -> str:
    """Test a visible link if possible, otherwise a source-backed deep link."""
    return rendered_links[0] if rendered_links else min(source_targets)


def _check_fresh_deep_link(
    context: Any, url: str, fragment: str,
    errors: list[str], network_errors: list[str],
) -> None:
    """Load a URL in a new document, independent of the in-page hash clicks."""
    fresh_page = context.new_page()
    _watch_page(fresh_page, errors, network_errors)
    try:
        response = fresh_page.goto(url, wait_until="domcontentloaded")
        if response is None or response.status != 200:
            raise AssertionError(
                f"Direct deep link returned HTTP {getattr(response, 'status', None)}: {url}"
            )
        _ready(fresh_page, errors, network_errors)
        _assert_target(fresh_page, fragment)
        _check_errors(fresh_page, errors, network_errors)
    finally:
        fresh_page.close()


def verify(base_url: str, *, headed: bool = False) -> dict[str, Any]:
    """Exercise soft navigation, native local hashes, and direct deep links."""
    try:
        playwright = importlib.import_module("playwright.sync_api")
    except ImportError as exc:
        raise RuntimeError(
            "Playwright/Chromium required: install playwright and its Chromium browser"
        ) from exc

    base = base_url.rstrip("/")
    results: list[dict[str, Any]] = []
    with playwright.sync_playwright() as driver:
        browser = driver.chromium.launch(headless=not headed)
        try:
            for width in WIDTHS:
                context = browser.new_context(viewport={"width": width, "height": 844})
                try:
                    catalog = context.request.get(f"{base}/weapons", timeout=15000)
                    if catalog.status != 200 or 'data-catalog="weapons"' not in catalog.text():
                        raise RuntimeError(f"{base}/weapons is not the expected app")
                    candidates = weapon_candidates(context.request, base)
                    links = glossary_links(context.request, base)
                    page = context.new_page()
                    errors: list[str] = []
                    network_errors: list[str] = []
                    _watch_page(page, errors, network_errors)

                    for slug, source_targets in candidates.items():
                        entry: dict[str, Any] = {
                            "width": width, "source": "weapon", "slug": slug,
                            "sourceFragments": len(source_targets),
                        }
                        try:
                            errors.clear()
                            network_errors.clear()
                            page.goto(f"{base}/weapons", wait_until="domcontentloaded")
                            page.locator("#catalog-list a").first.wait_for(state="visible")
                            entry["phase"] = "catalog-soft-navigation"
                            page.evaluate("() => { window.__fragmentTestDocument = document; }")
                            path = quote(slug, safe="")
                            page.locator(
                                f'#catalog-list a[href="/weapons/{path}"]'
                            ).click()
                            _ready(page, errors, network_errors)
                            if urlsplit(page.url).path != f"/weapons/{path}":
                                raise AssertionError("Catalog click did not navigate to detail")
                            if not page.evaluate(
                                "() => window.__fragmentTestDocument === document"
                            ):
                                raise AssertionError("Catalog click lost soft-navigation document")
                            hrefs: list[str] = page.locator(
                                '#item-content a[href^="#rule-"]'
                            ).evaluate_all(
                                "(nodes) => [...new Set("
                                "nodes.map((a) => a.getAttribute('href'))"
                                ")].sort()"
                            )
                            # Source references include hosted identities that
                            # deliberately are not rendered as clickable links.
                            # Verify their cards, then click the links that exist.
                            entry["phase"] = "hosted-source-cards"
                            for href in sorted(source_targets):
                                _assert_hosted(page, href)
                            entry["phase"] = "in-page-fragment-clicks"
                            for href in hrefs:
                                page.locator(
                                    f'#item-content a[href="{href}"]'
                                ).first.click()
                                _assert_target(page, href)
                            _check_errors(page, errors, network_errors)
                            direct = _direct_fragment(source_targets, hrefs)
                            entry["phase"] = "fresh-deep-link"
                            _check_fresh_deep_link(
                                context, f"{base}/weapons/{path}{direct}", direct,
                                errors, network_errors,
                            )
                            entry.update(
                                status="passed",
                                hostedSourceFragments=len(source_targets),
                                renderedFragments=len(hrefs),
                                directFragment=direct,
                            )
                            entry.pop("phase", None)
                        except Exception as exc:
                            _record_failure(entry, page, exc, errors, network_errors)
                        results.append(entry)

                    for href in links:
                        entry = {"width": width, "source": "glossary", "href": href}
                        try:
                            errors.clear()
                            network_errors.clear()
                            page.goto(f"{base}/glossary", wait_until="domcontentloaded")
                            page.locator("#glossary-list .glossary-entry").first.wait_for(
                                state="visible"
                            )
                            page.locator(
                                f'#glossary-list a[href="{href}"]'
                            ).first.click()
                            _ready(page, errors, network_errors)
                            if urlsplit(page.url).path != urlsplit(href).path:
                                raise AssertionError("Glossary link reached wrong Weapon page")
                            _assert_target(page, href)
                            _check_errors(page, errors, network_errors)
                            entry["status"] = "passed"
                        except Exception as exc:
                            _record_failure(entry, page, exc, errors, network_errors)
                        results.append(entry)
                finally:
                    context.close()
        finally:
            browser.close()

    return {
        "format": "InfinityDB Weapon rule-fragment browser acceptance",
        "baseUrl": base,
        "widths": list(WIDTHS),
        "total": len(results),
        "passed": sum(item["status"] == "passed" for item in results),
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
            encoding="utf-8",
            newline="\n",
        )
    print(f"Weapon fragment browser navigation: {report['passed']}/{report['total']} passed")
    for item in report["results"]:
        if item["status"] == "failed":
            print(f"  {item['width']}px {item.get('slug', item.get('href'))}: {item['error']}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
