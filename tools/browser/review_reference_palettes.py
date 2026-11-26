"""Capture a bounded visual review of the shipped faction palettes and rule hierarchy."""
from __future__ import annotations

import argparse
from pathlib import Path

from infinity_db.theme_palette import palette_options
from infinity_db.web import create_app_from_database_set
from tools.browser_wsgi_transport import route_browser_page

ORIGIN = "http://infinitydb-browser.test"
ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "local/validation"):
        raise ValueError("Use a new local/validation output directory")
    output.mkdir(parents=True, exist_ok=False)
    app = create_app_from_database_set(ROOT / "data/generated")
    from playwright.sync_api import sync_playwright

    palettes = [item["value"] for item in palette_options()]
    cases = [
        ("/skills/immunity", '[data-provenance="reviewed-explanation"]', "immunity"),
        ("/fireteams", '[data-provenance="source-discrepancy"]', "fireteams"),
        ("/scenarios/domination?army_points=350", '[data-provenance="source-uncertainty"]',
         "domination"),
        ("/units/401?army_id=503", ".army-profile[open]", "zeros"),
    ]
    with sync_playwright() as driver:
        browser = driver.chromium.launch()
        try:
            for width in (1440, 390):
                page = browser.new_page(viewport={"width": width, "height": 900})
                route_browser_page(page, app, ORIGIN)
                errors: list[str] = []
                page.on("pageerror", lambda error, errors=errors: errors.append(str(error)))
                page.add_init_script(
                    "sessionStorage.setItem('infinitydb-accuracy-notice-collapsed','true');"
                )
                for path, selector, name in cases:
                    page.goto(ORIGIN + path, wait_until="domcontentloaded")
                    target = page.locator(selector).first
                    target.wait_for(state="visible", timeout=30000)
                    for palette in palettes:
                        for mode in ("light", "dark"):
                            page.evaluate(
                                """([palette, mode]) => {
                                  for (const [selector, value] of [
                                    ["#theme-palette-selector", palette],
                                    ["#theme-selector", mode],
                                  ]) {
                                    const select = document.querySelector(selector);
                                    select.value = value;
                                    select.dispatchEvent(new Event("change", {bubbles: true}));
                                  }
                                }""",
                                [palette, mode],
                            )
                            assert page.evaluate(
                                "document.documentElement.scrollWidth <= innerWidth + 1"
                            ), (name, width, palette, mode)
                            if name == "domination":
                                page.wait_for_function(
                                    """([palette, mode]) => {
                                      const image = document.querySelector("img.scenario-map");
                                      if (!image?.complete || !image.naturalWidth) return false;
                                      const params = new URL(image.src).searchParams;
                                      return params.get("theme") === mode
                                        && (params.get("palette") || "infinitydb") === palette;
                                    }""",
                                    arg=[palette, mode],
                                )
                            if name != "immunity" and palette not in {
                                "infinitydb", "panoceania", "yu-jing", "combined-army",
                                "tohaa", "jsa",
                            }:
                                continue
                            page.evaluate("window.scrollTo(0,0)")
                            page.screenshot(
                                path=output / f"{name}-{width}-{palette}-{mode}.jpg",
                                type="jpeg", quality=65, animations="disabled",
                            )
                            if name != "immunity" or palette in {"infinitydb", "tohaa", "jsa"}:
                                target.scroll_into_view_if_needed()
                                page.screenshot(
                                    path=output / f"{name}-{width}-{palette}-{mode}-detail.jpg",
                                    type="jpeg", quality=65, animations="disabled",
                                )
                    print(f"{name}: {width}px, 24 palette/mode combinations PASS", flush=True)
                assert not errors, errors
                page.close()
        finally:
            browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
