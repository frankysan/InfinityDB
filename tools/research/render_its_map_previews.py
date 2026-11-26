"""Render local ITS scenario-map PNG previews for source-diagram visual comparison.

Only writes ignored local/work/its/map-previews; does not alter a publication.
"""
from __future__ import annotations

import argparse
import importlib
import re
from pathlib import Path
from xml.etree import ElementTree

import pymupdf

from infinity_db.curated import load_curated_document
from infinity_db.scenario_geometry import parse_scenario_geometry
from infinity_db.scenario_map_svg import render_scenario_map_svg
from infinity_db.web import create_app_from_database_set
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/curated/its/n5-its-season-18.json"
OUTPUT = ROOT / "local/work/its/map-previews"
TOKEN_RE = re.compile(r"var\((--color-scenario-map-[a-z-]+),\s*(#[0-9a-fA-F]{6})\)")
COLOR_RE = re.compile(r"(--color-scenario-map-[a-z-]+):\s*(#[0-9a-fA-F]{6});")


def _raster_friendly_svg(svg: str, colors: dict[str, str], *, theme: str, width: float) -> bytes:
    """MuPDF ignores SVG class styles; materialize their browser-equivalent roles."""
    xml = TOKEN_RE.sub(lambda m: colors.get(m.group(1), m.group(2)), svg)
    root = ElementTree.fromstring(xml)
    text_scale = 1.0 + max(0.0, min(24.0, width - 24.0)) / 48.0
    palette: dict[str, dict[str, str]] = {
        "table": {"fill": colors["--color-scenario-map-table"],
                  "stroke": colors["--color-scenario-map-outline"], "stroke-width": ".12"},
        "deployment-a": {"fill": colors["--color-scenario-map-deployment-a"],
                         "stroke": colors["--color-scenario-map-deployment-a-edge"],
                         "stroke-width": ".09"},
        "deployment-b": {"fill": colors["--color-scenario-map-deployment-b"],
                         "stroke": colors["--color-scenario-map-deployment-b-edge"],
                         "stroke-width": ".09"},
        "scoring": {"fill": colors["--color-scenario-map-scoring"],
                    "fill-opacity": ".65", "stroke": colors["--color-scenario-map-scoring-edge"]},
        "no-deploy": {"fill": "#744647" if theme == "dark" else "#f0c6c6",
                      "fill-opacity": ".72",
                      "stroke": "#d5a7a7" if theme == "dark" else "#aa7777",
                      "stroke-width": ".09"},
        # MuPDF does not implement SVG patterns; show the underlying red zone.
        # The browser renders the source-backed diagonal hatch in the SVG itself.
        "exclusion": {"fill": colors["--color-scenario-map-deployment-b"],
                      "stroke": colors["--color-scenario-map-deployment-b-edge"],
                      "stroke-width": ".09"},
        "influence": {"fill": "#51476b" if theme == "dark" else "#d4c7f1",
                      "fill-opacity": ".8",
                      "stroke": "#c0adf0" if theme == "dark" else "#7463a8",
                      "stroke-width": ".10"},
        "sector": {"fill": "#4b5b3e" if theme == "dark" else "#b9c995",
                   "stroke": "#a6c083" if theme == "dark" else "#667e47",
                   "stroke-width": ".08"},
        "sector-center": {"fill": "#6c6444" if theme == "dark" else "#eee7b7",
                          "stroke": "#d2c88b" if theme == "dark" else "#9e9855",
                          "stroke-width": ".08"},
        "objective": {"fill": colors["--color-scenario-map-marker"],
                      "stroke": colors["--color-scenario-map-outline"], "stroke-width": ".1"},
        "guide": {"fill": "none", "stroke": colors["--color-scenario-map-guide"],
                  "stroke-width": ".06", "stroke-dasharray": ".35 .25"},
        "measurement": {"fill": "none", "stroke": colors["--color-scenario-map-measurement"],
                        "stroke-width": ".09"},
        "dimension-label": {"fill": colors["--color-scenario-map-text"],
                            "font-family": "sans-serif", "font-size": str(1.1 * text_scale)},
        "area-size": {"fill": colors["--color-scenario-map-text"],
                      "font-family": "sans-serif", "font-size": str(1.1 * text_scale)},
        "label": {"fill": colors["--color-scenario-map-text"],
                  "font-family": "sans-serif", "font-weight": "600",
                  "font-size": str(1.4 * text_scale)},
    }
    markers = [element for element in root.iter() if element.get("data-marker-type")]
    has_civilians = any(element.get("data-marker-type") == "civilian" for element in markers)
    has_beacons = any(element.get("data-marker-type") == "beacon"
                      for element in markers)
    has_tracking_beacon = any(element.get("data-marker-type") == "tracking-beacon"
                              for element in markers)
    has_akial_antenna = any(
        element.get("id") in {"akial-antenna", "inhibitor-antenna"}
        for element in markers
    )
    has_tech_coffin = any(element.get("data-marker-type") == "tech-coffin"
                          for element in markers)
    for element in root.iter():
        for klass in element.get("class", "").split():
            element.attrib.update(palette.get(klass, {}))
        if element.get("data-marker-type") in {"prototype", "panoply"}:
            prototype = element.get("data-marker-type") == "prototype"
            element.attrib.update({
                "fill": ("#a85988" if prototype else "#468b99") if theme == "dark"
                        else ("#da79a6" if prototype else "#64b7c0"),
                "stroke": ("#f2adce" if prototype else "#b0e5ed") if theme == "dark"
                          else ("#a33e70" if prototype else "#25757c"),
            })
        if element.get("data-marker-type") == "defensive-turret":
            element.attrib.update({
                "fill": "#64748b" if theme == "dark" else "#718096",
                "stroke": "#cbd5e1" if theme == "dark" else "#334155",
            })
        if has_civilians and element.get("data-marker-type") == "civilian":
            element.attrib.update({
                "fill": "#83d5eb" if theme == "dark" else "#74c9e6",
                "stroke": "#b5efff" if theme == "dark" else "#237ca7",
            })
        if has_tracking_beacon and element.get("data-marker-type") == "tracking-beacon":
            element.attrib.update({
                "fill": "#75b9ec" if theme == "dark" else "#5f8ecc",
                "stroke": "#c6e9ff" if theme == "dark" else "#24568f",
            })
        if (has_beacons or has_tracking_beacon or has_civilians) and element.get(
            "data-marker-type"
        ) == "console":
            element.attrib.update({
                "fill": "#6aa968" if theme == "dark" else "#84ca7a",
                "stroke": "#b7ebb0" if theme == "dark" else "#377735",
            })
        if has_beacons and element.get("data-marker-type") == "beacon":
            is_a = element.get("id") == "beacon-a"
            element.attrib.update({
                "fill": ("#ed8388" if is_a else "#77c4ef") if theme == "dark"
                        else ("#cf4047" if is_a else "#278ec4"),
                "stroke": ("#f5b6b9" if is_a else "#c4eafd") if theme == "dark"
                          else ("#8f1520" if is_a else "#15577c"),
            })
        if (has_tech_coffin or has_akial_antenna) and element.get("data-marker-type") in {
            "antenna", "tech-coffin",
        }:
            role = element.get("data-marker-type")
            if role == "antenna":
                element.attrib.update({
                    "fill": "#97741e" if theme == "dark" else "#f7c86a",
                    "stroke": "#efd18d" if theme == "dark" else "#b97b09",
                })
            else:
                element.attrib.update({
                    "fill": "#725991" if theme == "dark" else "#a99ac5",
                    "stroke": "#dec9f1" if theme == "dark" else "#6d4d91",
                })
    for element in list(root):
        if element.tag.endswith("}style"):
            root.remove(element)
    root.attrib.pop("style", None)
    return ElementTree.tostring(root, encoding="utf-8")


def _render_standalone_preview(
    svg: str, output: Path, *, width: int, height: int, browser_name: str,
) -> None:
    """Open the exact generated file in a browser, without rewriting its styles."""
    playwright = importlib.import_module("playwright.sync_api")

    svg_path = output.with_suffix(".svg")
    svg_path.write_bytes(svg.encode("utf-8"))
    with playwright.sync_playwright() as driver:
        browser = getattr(driver, browser_name).launch()
        try:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(svg_path.resolve().as_uri())
            page.locator("svg").wait_for()
            page.screenshot(path=output)
        finally:
            browser.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--missions",
        help="Comma-separated exact mission slugs (standalone mode uses current missions).",
    )
    parser.add_argument("--config", default="300-400-points")
    parser.add_argument("--theme", choices=("light", "dark"), default="light")
    parser.add_argument("--distance-unit", choices=("in", "cm"), default="in")
    parser.add_argument("--width-px", type=int, default=630)
    parser.add_argument(
        "--standalone", action="store_true",
        help="Save the original SVG and render it directly in a browser.",
    )
    parser.add_argument(
        "--browser", choices=("chromium", "firefox", "webkit"), default="chromium",
        help="Browser engine for standalone previews.",
    )
    args = parser.parse_args(argv)
    if args.width_px < 300 or args.width_px > 1200:
        parser.error("--width-px must be 300..1200")
    records = {
        record["id"].removeprefix("scenario:"): record
        for record in load_curated_document(SOURCE)["records"]
    }
    default_missions = (
        "crossing-lines,double-bind,the-dig,critical-intervention"
        if args.standalone else "crossing-lines,double-bind,the-dig,battleground"
    )
    selected = (args.missions or default_missions).split(",")
    if not selected or any(slug not in records for slug in selected):
        parser.error("Unknown scenario slug")
    palette = (ROOT / "src/infinity_db/web/static/themes" / f"{args.theme}.css")
    colors = dict(COLOR_RE.findall(palette.read_text(encoding="utf-8")))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    app = create_app_from_database_set(ROOT / "data/generated") if args.standalone else None

    for slug in selected:
        record = records[slug]
        configurations = record["facts"]["configurations"]
        selected_config = next(
            (c for c in configurations if c["id"] == args.config), None,
        )
        if selected_config is None:
            parser.error(f"Unknown configuration for {slug}: {args.config}")
        geometry = parse_scenario_geometry(selected_config["geometry"])
        svg = render_scenario_map_svg(
            geometry, theme=args.theme, distance_unit=args.distance_unit,
        )
        if app is not None:
            points = int(args.config.split("-", 1)[0])
            status, headers, body = wsgi_response(
                app, f"http://localhost/api/scenarios/{slug}/map.svg"
                f"?army_points={points}&collection=its-18"
                f"&theme={args.theme}&distance_unit={args.distance_unit}",
            )
            content_type = {key.lower(): value for key, value in headers}.get("content-type", "")
            if status != 200 or not content_type.startswith("image/svg+xml"):
                raise ValueError(f"{slug}: expected a published SVG, received {status}")
            if body != svg.encode("utf-8"):
                raise ValueError(f"{slug}: curated preview differs from the published SVG")
            output = OUTPUT / (
                f"{slug}-{args.config}-{args.theme}-{args.distance_unit}"
                f"-standalone-{args.width_px}-{args.browser}.png"
            )
            _render_standalone_preview(
                svg, output, width=args.width_px,
                height=round(args.width_px * geometry.table.height / geometry.table.width),
                browser_name=args.browser,
            )
            print(output.relative_to(ROOT))
            continue
        # MuPDF's SVG importer does not universally implement CSS custom properties.
        # Resolve the already-pinned palette for faithful standalone preview rasterization.
        preview_svg = _raster_friendly_svg(svg, colors, theme=args.theme,
                                           width=geometry.table.width)
        with pymupdf.open(stream=preview_svg, filetype="svg") as document:
            scale = args.width_px / geometry.table.width
            suffix = "" if args.distance_unit == "in" else f"-{args.distance_unit}"
            output = OUTPUT / f"{slug}-{args.config}-{args.theme}{suffix}.png"
            document[0].get_pixmap(
                matrix=pymupdf.Matrix(scale, scale), alpha=False,
            ).save(output)
            print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
