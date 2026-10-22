#!/usr/bin/env python3
"""Chromium acceptance for Army-sourced Hacking Programs and their reviewed rules."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any

from infinity_db.database.repository import Database
from infinity_db.domain_slugs import assign_domain_slugs

ROOT = Path(__file__).resolve().parents[1]
ARMY_DB = ROOT / "data/generated/infinity.db"
WIDTHS = (1440, 390, 320)


def source_programs(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    """Derive program identities and structured fields from the published Army DB."""
    rows = Database(root / "data/generated/infinity.db").list_hacking_programs()
    slugs = assign_domain_slugs(
        ((int(row["position"]), row["name"]) for row in rows),
        domain="hacking-programs",
    )
    return {slugs[int(row["position"])]: row for row in rows}


def _display(value: object) -> str:
    return "—" if value is None or value == "" else str(value)


def verify(base_url: str, *, headed: bool = False) -> dict[str, Any]:
    expected = source_programs()
    if len(expected) != 12:
        raise ValueError(f"Expected 12 published Hacking Programs; found {len(expected)}")
    try:
        playwright = importlib.import_module("playwright.sync_api")
    except ImportError as exc:
        raise RuntimeError(
            "Playwright/Chromium are required; install playwright and its chromium browser"
        ) from exc

    base = base_url.rstrip("/")
    observations: list[dict[str, Any]] = []
    with playwright.sync_playwright() as driver:
        browser = driver.chromium.launch(headless=not headed)
        try:
            for width in WIDTHS:
                context = browser.new_context(viewport={"width": width, "height": 844})
                try:
                    response = context.request.get(f"{base}/hacking-programs", timeout=15000)
                    if (
                        response.status != 200
                        or 'data-catalog="hacking-programs"' not in response.text()
                    ):
                        raise RuntimeError(
                            f"{base}/hacking-programs is not the current InfinityDB catalog "
                            f"(HTTP {response.status}); check server and --base-url"
                        )
                    page = context.new_page()
                    errors: list[str] = []
                    page.on("pageerror", lambda exc, sink=errors: sink.append(str(exc)))
                    page.goto(f"{base}/hacking-programs", wait_until="domcontentloaded")
                    page.locator("#catalog-list a").first.wait_for(state="visible")
                    found = set(page.locator("#catalog-list a").evaluate_all(
                        "(anchors) => anchors.map((a) => a.getAttribute('href'))"
                    ))
                    wanted = {f"/hacking-programs/{slug}" for slug in expected}
                    if found != wanted:
                        raise AssertionError(
                            f"Catalog mismatch: missing={sorted(wanted - found)} "
                            f"unexpected={sorted(found - wanted)}"
                        )

                    for slug, row in sorted(expected.items()):
                        observation: dict[str, Any] = {
                            "width": width, "slug": slug, "name": row["name"]
                        }
                        try:
                            errors.clear()
                            page.locator(
                                f'#catalog-list a[href="/hacking-programs/{slug}"]'
                            ).click()
                            page.locator(
                                f"#rule-hacking-program-{slug}"
                            ).wait_for(state="visible")
                            name = page.locator("#item-name").evaluate(
                                "(element) => element.firstChild.textContent"
                            )
                            if name != row["name"]:
                                raise AssertionError(f"Wrong heading: {name!r}")
                            cells = page.locator(
                                "#item-content .hacking-program-profile-table table tbody td"
                            )
                            displayed = cells.all_text_contents()
                            values = [
                                ", ".join(row["targets"]) if row["targets"] else "—",
                                _display(row["attack_mod"]),
                                _display(row["opponent_mod"]),
                                _display(row["ps"]),
                                _display(row["burst"]),
                            ]
                            if displayed != values:
                                raise AssertionError(
                                    f"Program profile mismatch: {displayed!r} != {values!r}"
                                )
                            if not page.locator(
                                "#item-content .hacking-program-devices"
                            ).is_visible():
                                raise AssertionError("Baseline Devices are not visible")
                            if not page.locator(
                                "#item-content .detail-source"
                            ).first.is_visible():
                                raise AssertionError("Rules source citations are not visible")
                            if page.locator("#item-status").is_visible():
                                raise AssertionError("Loading/error message remains visible")
                            if page.evaluate(
                                "() => document.documentElement.scrollWidth > window.innerWidth + 1"
                            ):
                                raise AssertionError("Page-level horizontal overflow")
                            if errors:
                                raise AssertionError(f"JavaScript errors: {errors}")
                            observation["status"] = "passed"
                        except Exception as exc:
                            observation.update(status="failed", error=str(exc))
                        observations.append(observation)
                        page.goto(f"{base}/hacking-programs", wait_until="domcontentloaded")
                        page.locator("#catalog-list a").first.wait_for(state="visible")
                finally:
                    context.close()
        finally:
            browser.close()
    return {
        "format": "InfinityDB Hacking Programs browser acceptance",
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
    print(f"Hacking Programs browser navigation: {report['passed']}/{report['total']} passed")
    for item in report["results"]:
        if item["status"] == "failed":
            print(f"  {item['width']}px {item['slug']}: {item['error']}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
