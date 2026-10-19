#!/usr/bin/env python3
"""Optional Chromium acceptance for complete Martial Arts, Booty, MetaChemistry charts."""

from __future__ import annotations

import argparse
import importlib
import json
from functools import partial
from pathlib import Path
from typing import Any

from infinity_db.database.repository import Database
from infinity_db.structured_chart_outcomes import project_booty_rows

ROOT = Path(__file__).resolve().parents[1]
WIDTHS = (1440, 390, 320)
CHARTS: dict[str, dict[str, Any]] = {
    "martial-arts": {
        "table": "application_martial_arts_levels",
        "columns": ("position", "level", "attack_mod", "opponent_mod", "ps_mod", "burst_mod"),
        "order": "position",
        "kind": "martial-arts",
        "title": "Martial Arts chart",
        "list_method": "list_martial_arts_levels",
        "visible_columns": ("level", "attack_mod", "opponent_mod", "burst_mod"),
    },
    "booty": {
        "table": "application_booty_results",
        "columns": ("id", "roll", "result"),
        "order": "id",
        "kind": "random-chart",
        "title": "Booty chart",
        "list_method": "list_booty_results",
        "visible_columns": ("roll", "result"),
    },
    "metachemistry": {
        "table": "application_metachemistry_results",
        "columns": ("id", "roll", "result"),
        "order": "id",
        "kind": "random-chart",
        "title": "MetaChemistry chart",
        "list_method": "list_metachemistry_results",
        "visible_columns": ("roll", "result"),
    },
}


def source_charts(database: Database) -> dict[str, dict[str, Any]]:
    """Use normalized Army table getters, not curated outcomes or guessed roll results."""
    return {
        slug: {
            "kind": chart["kind"],
            "title": chart["title"],
            "rows": (
                project_booty_rows(database.list_booty_results())
                if slug == "booty" else getattr(database, chart["list_method"])()
            ),
        }
        for slug, chart in CHARTS.items()
    }


def _page_error(errors: list[str], error: Any) -> None:
    errors.append(str(error))


def verify(base_url: str, *, headed: bool = False) -> dict[str, Any]:
    expected = source_charts(Database(ROOT / "data/generated/infinity.db"))
    if set(expected) != set(CHARTS) or any(not value["rows"] for value in expected.values()):
        raise ValueError("Cannot verify incomplete published structured Skill charts")
    try:
        playwright = importlib.import_module("playwright.sync_api")
    except ImportError as exc:
        raise RuntimeError(
            "Playwright and its Chromium browser are required for browser acceptance"
        ) from exc

    base = base_url.rstrip("/")
    results: list[dict[str, Any]] = []
    with playwright.sync_playwright() as driver:
        browser = driver.chromium.launch(headless=not headed)
        try:
            for width in WIDTHS:
                context = browser.new_context(viewport={"width": width, "height": 844})
                try:
                    landing = context.request.get(f"{base}/skills", timeout=15000)
                    if (
                        landing.status != 200
                        or 'data-catalog="skills"' not in landing.text()
                    ):
                        raise RuntimeError(
                            f"{base}/skills is not the current InfinityDB catalog "
                            f"(HTTP {landing.status})"
                        )
                    page = context.new_page()
                    errors: list[str] = []
                    page.on("pageerror", partial(_page_error, errors))
                    page.goto(f"{base}/skills", wait_until="domcontentloaded")
                    page.locator("#catalog-list a").first.wait_for(state="visible")
                    links = set(page.locator("#catalog-list a").evaluate_all(
                        "(anchors) => anchors.map((a) => a.getAttribute('href'))"
                    ))
                    required = {f"/skills/{slug}" for slug in CHARTS}
                    if not required <= links:
                        raise AssertionError(f"Missing chart Skill links: {required - links}")

                    for slug, definition in CHARTS.items():
                        observation: dict[str, Any] = {"width": width, "slug": slug}
                        try:
                            response = context.request.get(
                                f"{base}/api/skills/{slug}", timeout=15000
                            )
                            if response.status != 200:
                                raise AssertionError(
                                    f"Skill API unavailable: {slug} HTTP {response.status}"
                                )
                            skill = response.json()
                            if skill.get("structured_reference") != expected[slug]:
                                raise AssertionError(
                                    f"Served Skill chart differs from local snapshot: {slug}"
                                )
                            errors.clear()
                            page.locator(
                                f'#catalog-list a[href="/skills/{slug}"]'
                            ).click()
                            chart = page.locator("table.data-table--reference").filter(
                                has=page.locator("caption", has_text=definition["title"])
                            )
                            chart.wait_for(state="visible")
                            heading = page.locator("#skill-name").evaluate(
                                "(element) => element.firstChild.textContent"
                            )
                            if heading != skill["name"]:
                                raise AssertionError(
                                    f"Unexpected Skill heading: {heading!r} != {skill['name']!r}"
                                )
                            headings = chart.locator("thead th").all_text_contents()
                            expected_headers = (
                                ["Level", "Attack MOD", "Opponent MOD", "Burst MOD"]
                                if slug == "martial-arts" else ["Roll", "Result"]
                            )
                            if headings != expected_headers:
                                raise AssertionError(f"Unexpected chart columns: {headings}")
                            actual = chart.locator("tbody tr").evaluate_all(
                                "(rows) => rows.map((row) => Array.from("
                                "row.querySelectorAll('td'), (cell) => cell.textContent))"
                            )
                            rows = expected[slug]["rows"]
                            visible = definition["visible_columns"]
                            expected_rows = [
                                [
                                    (
                                        "\n".join(
                                            f"{branch['label']}: {branch['result']}"
                                            for branch in row["conditional_outcomes"]
                                        )
                                        if slug == "booty" and field == "result"
                                        and row.get("conditional_outcomes")
                                        else str(row[field])
                                    )
                                    if row[field] not in (None, "") else "—"
                                    for field in visible
                                ]
                                for row in rows
                            ]
                            if actual != expected_rows:
                                raise AssertionError(
                                    f"Chart data mismatch: {actual!r} != {expected_rows!r}"
                                )
                            if slug == "booty":
                                branches = chart.locator(".chart-outcome-branches")
                                if branches.count() != 4:
                                    raise AssertionError("Expected four explicit Booty branches")
                                for branch in branches.all():
                                    style = branch.evaluate(
                                        "(element) => getComputedStyle(element).whiteSpace"
                                    )
                                    if style != "pre-line":
                                        raise AssertionError(
                                            "Booty TAG/other Troop Type branches are not separated"
                                        )
                            if page.locator("#skill-status").is_visible():
                                raise AssertionError("Loading/error state remains visible")
                            if page.evaluate(
                                "() => document.documentElement.scrollWidth > window.innerWidth + 1"
                            ):
                                raise AssertionError("Document-level horizontal overflow")
                            if errors:
                                raise AssertionError(f"JavaScript errors: {errors}")
                            observation["rows"] = len(rows)
                            observation["status"] = "passed"
                        except Exception as exc:
                            observation.update(status="failed", error=str(exc))
                        results.append(observation)
                        page.goto(f"{base}/skills", wait_until="domcontentloaded")
                        page.locator("#catalog-list a").first.wait_for(state="visible")
                finally:
                    context.close()
        finally:
            browser.close()
    return {
        "format": "InfinityDB structured Skill chart browser acceptance",
        "baseUrl": base,
        "widths": list(WIDTHS),
        "total": len(results),
        "passed": sum(row["status"] == "passed" for row in results),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args(argv)
    report = verify(args.base_url, headed=args.headed)
    if args.output:
        args.output.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(f"Structured Skill charts browser: {report['passed']}/{report['total']} passed")
    for item in report["results"]:
        if item["status"] == "failed":
            print(f"  {item['width']}px {item['slug']}: {item['error']}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
