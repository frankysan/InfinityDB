"""Verify embedded Unit history parity and native browser disclosures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from infinity_db.web import create_app_from_database_set
from tools.browser_wsgi_transport import route_browser_page, wsgi_response

ORIGIN = "http://unit-history.test"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-dir", type=Path, required=True)
    parser.add_argument("--compare-projection", type=Path)
    parser.add_argument("--unit", type=int, action="append", default=[])
    args = parser.parse_args()

    app = create_app_from_database_set(args.db_dir)
    with app.database._connect() as db:
        rows = {
            str(unit): json.loads(body)
            for unit, body in db.execute(
                "SELECT unit_id,body FROM unit_history_payloads ORDER BY unit_id"
            )
        }
    if not rows:
        raise ValueError("Missing embedded history")
    if args.compare_projection is not None:
        expected = json.loads(args.compare_projection.read_text(encoding="utf-8"))["units"]
        if rows != expected:
            different = sorted(
                key for key in rows.keys() | expected.keys() if rows.get(key) != expected.get(key)
            )
            raise ValueError(
                f"Embedded history differs for {len(different)} Units: {different[:20]}"
            )
        print(f"Exact preview parity: {len(rows)} Units", flush=True)
    counts = {
        "units": len(rows),
        "generalEntries": sum(len(changes) for row in rows.values()
                              for changes in row["general"].values()),
        "armyEntries": sum(len(changes) for row in rows.values()
                           for changes in row["armies"].values()),
        "unmatchedEntries": sum(len(context["changes"]) for row in rows.values()
                                for context in row["unmatched"]),
    }
    print(json.dumps(counts, indent=2), flush=True)

    from playwright.sync_api import sync_playwright

    units = args.unit or [232, 1903, 1940, 24]
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        try:
            for unit in units:
                status, _, body = wsgi_response(
                    app, f"{ORIGIN}/api/units/{unit}?mercs=1&specops=1&teamops=1&reinforcement=1",
                )
                assert status == 200
                payload = json.loads(body)
                assert str(unit) in rows
                slug = payload["public_slug"]
                for width, theme in ((1280, "light"), (390, "dark")):
                    page = browser.new_page(viewport={"width": width, "height": 900})
                    errors: list[str] = []
                    page.on("pageerror", lambda error, errors=errors: errors.append(str(error)))
                    try:
                        route_browser_page(page, app, ORIGIN)
                        page.goto(f"{ORIGIN}/units/{slug}", wait_until="domcontentloaded")
                        page.locator(".general-profile .unit-history").first.wait_for()
                        page.evaluate(
                            "(theme) => document.documentElement.dataset.theme = theme", theme,
                        )
                        assert page.locator(".unit-history[open]").count() == 0
                        history = page.locator(".unit-history:has(.unit-history-date)").first
                        history.evaluate("""element => {
                            for (let parent = element.parentElement; parent;
                                 parent = parent.parentElement)
                                if (parent.tagName === 'DETAILS') parent.open = true;
                        }""")
                        history.locator(":scope > summary").click()
                        assert history.locator(".unit-history-change").first.is_visible()
                        assert page.evaluate(
                            "document.documentElement.scrollWidth <= innerWidth + 1"
                        )
                        assert not errors, errors
                        print(f"{slug}: {width}px {theme} PASS", flush=True)
                    finally:
                        page.close()
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
