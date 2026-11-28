"""Measure bounded reference page and map materialization against current composers."""
from __future__ import annotations

import argparse
import json
import sqlite3
import tempfile
import zlib
from contextlib import closing
from pathlib import Path
from statistics import median
from time import perf_counter

from infinity_db.glossary_catalog import GlossaryCatalog
from infinity_db.maintained_text_references import maintained_text_tokens_batch
from infinity_db.scenario_geometry import parse_scenario_geometry
from infinity_db.scenario_map_svg import render_scenario_map_svg
from infinity_db.web.app import create_app_from_database_set
from tools.browser_wsgi_transport import wsgi_response


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-dir", type=Path, default=Path("data/generated"))
    args = parser.parse_args()
    app = create_app_from_database_set(args.db_dir)
    routes = ["/api/glossary", "/api/unit-profile-help", "/api/orders-aros"]
    catalog = app.scenario_catalog
    collections = catalog.list_collections()
    core = next(item for item in collections if item["id"] == "n5-core")
    routes.extend(
        f"/api/orders-aros?scenario={item['slug']}"
        for item in catalog.list_scenarios(collection=core["id"], revision=core["revision"])
    )

    def request(route: str) -> bytes:
        status, _, body = wsgi_response(app, "http://localhost" + route)
        assert status == 200, (status, route)
        return body

    glossary = GlossaryCatalog(app.database, app.rules_database)
    start = perf_counter()
    entries = glossary.entries()
    composition = perf_counter() - start
    raw = json.dumps(entries, ensure_ascii=False, separators=(",", ":")).encode()
    start = perf_counter()
    decoded = json.loads(raw)
    for entry, tokens in zip(decoded, maintained_text_tokens_batch(
        app.database, app.rules_database, (entry["description"] for entry in decoded),
    ), strict=True):
        entry["description_tokens"] = tokens
    elapsed = perf_counter() - start
    print(
        f"glossary raw={len(raw):,} bytes; compose={composition*1000:.2f} ms; "
        f"decode and resolve={elapsed*1000:.2f} ms",
        flush=True,
    )

    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "pages.db"
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE pages (route TEXT PRIMARY KEY, body BLOB)")
            for route in routes:
                start = perf_counter()
                body = request(route)
                cold = perf_counter() - start
                times = []
                for _ in range(5):
                    start = perf_counter()
                    assert request(route) == body
                    times.append(perf_counter() - start)
                db.execute("INSERT INTO pages VALUES (?,?)", (route, body))
                start = perf_counter()
                decoded = json.loads(db.execute(
                    "SELECT body FROM pages WHERE route=?", (route,)
                ).fetchone()[0])
                elapsed = perf_counter() - start
                assert decoded == json.loads(body)
                print(
                    f"{route}: {len(body):,} bytes; cold {cold*1000:.2f} ms; "
                    f"repeat {median(times)*1000:.2f} ms; projected {elapsed*1000:.2f} ms",
                    flush=True,
                )
        print(f"page pilot size={path.stat().st_size:,}", flush=True)

        # Render each distinct geometry/configuration in all four supported presentations.
        # Time whole map requests separately to distinguish composition from SVG rendering.
        geometries = {}
        samples = []
        for collection in collections:
            for summary in catalog.list_scenarios(
                collection=collection["id"], revision=collection["revision"],
            ):
                for points in summary["supported_army_points"]:
                    scenario = catalog.get_scenario(
                        summary["slug"], army_points=points,
                        collection=collection["id"], revision=collection["revision"],
                    )
                    assert scenario is not None
                    geometry = scenario["placement"]["geometry"]
                    key = json.dumps(geometry, sort_keys=True, ensure_ascii=False)
                    if key not in geometries:
                        geometries[key] = geometry
                        samples.append(
                            f"/api/scenarios/{summary['slug']}/map.svg?"
                            f"army_points={points}&collection={collection['id']}"
                            f"&revision={collection['revision']}"
                        )
        svg_bytes = compressed_bytes = 0
        render_times, request_times = [], []
        for geometry in geometries.values():
            for unit in ("in", "cm"):
                for theme in ("light", "dark"):
                    start = perf_counter()
                    svg = render_scenario_map_svg(
                        parse_scenario_geometry(geometry), distance_unit=unit, theme=theme,
                    ).encode("utf-8")
                    render_times.append(perf_counter() - start)
                    svg_bytes += len(svg)
                    compressed_bytes += len(zlib.compress(svg))
        for route in samples:
            start = perf_counter()
            request(route)
            request_times.append(perf_counter() - start)
        print(
            f"maps: {len(geometries)} distinct geometries, {len(render_times)} SVGs; "
            f"raw={svg_bytes:,}; compressed={compressed_bytes:,}; "
            f"render median={median(render_times)*1000:.2f} ms; "
            f"request median={median(request_times)*1000:.2f} ms",
            flush=True,
        )


if __name__ == "__main__":
    main()
