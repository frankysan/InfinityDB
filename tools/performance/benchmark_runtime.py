#!/usr/bin/env python3
"""Benchmark representative InfinityDB repository read paths against one database."""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import statistics
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from infinity_db.database import Database

FORMAT = "InfinityDB runtime benchmark"
FORMAT_VERSION = 1


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    action: Callable[[Database], object]
    setup: Callable[[Database], object] | None = None


def _percentile(values: Sequence[float], fraction: float) -> float:
    if not values:
        raise ValueError("cannot calculate a percentile of an empty sample")
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1))
    return ordered[index]


def _summary(samples: Sequence[float]) -> dict[str, float]:
    milliseconds = [sample * 1000 for sample in samples]
    return {
        "medianMs": statistics.median(milliseconds),
        "p95Ms": _percentile(milliseconds, 0.95),
        "meanMs": statistics.fmean(milliseconds),
        "minMs": min(milliseconds),
        "maxMs": max(milliseconds),
    }


def _time(action: Callable[[], object]) -> float:
    started = time.perf_counter()
    action()
    return time.perf_counter() - started


def _cold_sample(case: BenchmarkCase, path: Path) -> float:
    if case.setup is None:
        return _time(lambda: case.action(Database(path)))
    database = Database(path)
    case.setup(database)
    return _time(lambda: case.action(database))


def _catalog_detail_action(catalog: str, item_id: int) -> Callable[[Database], object]:
    if catalog == "skills":
        return lambda database: database.get_skill(item_id)
    return lambda database: database.get_catalog_item(catalog, item_id)


def discover_cases(database: Database) -> list[BenchmarkCase]:
    """Build representative cases from identities present in the supplied snapshot."""
    armies = [army for army in database.list_armies() if army.get("playable")]
    units = database.list_units(limit=1).get("items", [])
    unit = units[0] if units else None

    cases = [
        BenchmarkCase("armies", lambda db: db.list_armies()),
        BenchmarkCase("units", lambda db: db.list_units(limit=50)),
        BenchmarkCase(
            "units-counts", lambda db: db.list_units(limit=50, include_usage_counts=True)
        ),
        BenchmarkCase(
            "units-counts-numeric",
            lambda db: db.list_units(
                points_min=10, points_max=35, limit=50, include_usage_counts=True,
            ),
        ),
        BenchmarkCase("traits", lambda db: db.list_traits()),
        BenchmarkCase(
            "units-scoped-initial-full",
            lambda db: db.list_units(
                matching_scope="profile", limit=50, include_usage_counts=True,
            ),
        ),
        BenchmarkCase(
            "units-scoped-initial-prospective",
            lambda db: db.list_units(
                matching_scope="profile", limit=50, include_usage_counts=True,
                include_raw_usage_counts=False,
            ),
        ),
    ]
    if armies:
        army_id = armies[0]["id"]
        cases.append(
            BenchmarkCase(
                "units-by-army",
                lambda db, value=army_id: db.list_units(army_id=value, limit=50),
            )
        )
        cases.append(
            BenchmarkCase(
                "units-counts-by-army",
                lambda db, value=army_id: db.list_units(
                    army_id=value, limit=50, include_usage_counts=True,
                ),
            )
        )
    if unit is not None:
        unit_id = unit["id"]
        unit_name = str(unit.get("name") or "")
        cases.append(BenchmarkCase("unit-detail", lambda db, value=unit_id: db.get_unit(value)))
        if unit_name:
            search = unit_name[: max(1, min(6, len(unit_name)))]
            cases.append(
                BenchmarkCase(
                    "unit-search",
                    lambda db, value=search: db.list_units(search=value, limit=50),
                )
            )

    for catalog in ("skills", "equipment", "weapons"):
        items = database.list_catalog_items(catalog)
        cases.append(
            BenchmarkCase(
                f"{catalog}-catalog",
                lambda db, value=catalog: db.list_catalog_items(value),
            )
        )
        if catalog == "skills" and len(items) >= 2:
            ids = tuple(
                item["id"] for item in sorted(
                    items, key=lambda item: item.get("use_count", 0), reverse=True,
                )[:2]
            )
            cases.append(
                BenchmarkCase(
                    "units-counts-multiselect",
                    lambda db, value=ids: db.list_units(
                        skill_id=value, limit=50, include_usage_counts=True,
                    ),
                )
            )
            # Exercise the explicitly scoped AND/count paths, not just the legacy
            # multi-selection endpoint. Prefer a realistic cross-skill query.
            by_slug = {str(item.get("slug")): item["id"] for item in items}
            scoped_ids = (
                (by_slug["berserk"], by_slug["engineer"])
                if {"berserk", "engineer"} <= by_slug.keys()
                else ids
            )
            for scope in ("profile", "loadout", "unit"):
                cases.append(
                    BenchmarkCase(
                        f"units-scoped-{scope}-counts",
                        lambda db, values=scoped_ids, mode=scope: db.list_units(
                            skill_id=values, and_filters=("skill",),
                            matching_scope=mode, limit=50, include_usage_counts=True,
                        ),
                    )
                )
            cases.append(
                BenchmarkCase(
                    "units-scoped-loadout-numeric-counts",
                    lambda db, values=scoped_ids: db.list_units(
                        skill_id=values, and_filters=("skill",),
                        matching_scope="loadout", points_min=10, points_max=35,
                        limit=50, include_usage_counts=True,
                    ),
                )
            )
            for scope in ("profile", "loadout", "unit"):
                cases.append(
                    BenchmarkCase(
                        f"units-scoped-{scope}-after-index",
                        lambda db, values=scoped_ids, mode=scope: db.list_units(
                            skill_id=values, and_filters=("skill",),
                            matching_scope=mode, limit=50, include_usage_counts=True,
                        ),
                        setup=lambda db, value=scoped_ids[0], mode=scope: db.list_units(
                            skill_id=value, matching_scope=mode,
                            limit=50, include_usage_counts=True,
                        ),
                    )
                )
            for scope in ("profile", "loadout", "unit"):
                cases.append(
                    BenchmarkCase(
                        f"units-prospective-{scope}-after-index",
                        lambda db, values=scoped_ids, mode=scope: db.list_units(
                            skill_id=values, and_filters=("skill",),
                            matching_scope=mode, limit=50, include_usage_counts=True,
                            include_raw_usage_counts=False,
                        ),
                        setup=lambda db, value=scoped_ids[0], mode=scope: db.list_units(
                            skill_id=value, matching_scope=mode, limit=50,
                            include_usage_counts=True, include_raw_usage_counts=False,
                        ),
                    )
                )
        if items:
            item_id = items[0]["id"]
            cases.append(
                BenchmarkCase(
                    f"{catalog}-detail",
                    _catalog_detail_action(catalog, item_id),
                )
            )

    traits = database.list_traits()
    if traits:
        trait_id = traits[0]["id"]
        cases.append(BenchmarkCase("trait-detail", lambda db, value=trait_id: db.get_trait(value)))
    return cases


def benchmark_database(
    path: Path,
    *,
    cold_iterations: int,
    warm_iterations: int,
    case_names: Sequence[str] = (),
) -> dict[str, Any]:
    database = Database(path)
    database.validate()
    cases = discover_cases(database)
    if case_names:
        unknown = set(case_names) - {case.name for case in cases}
        if unknown:
            raise ValueError(f"Unknown benchmark cases: {', '.join(sorted(unknown))}")
        cases = [case for case in cases if case.name in case_names]
    results = []
    for case in cases:
        cold_samples = [_cold_sample(case, path) for _ in range(cold_iterations)]
        warm_database = Database(path)
        if case.setup is not None:
            case.setup(warm_database)
        case.action(warm_database)
        warm_samples = [
            _time(lambda action=case.action, db=warm_database: action(db))
            for _ in range(warm_iterations)
        ]
        results.append(
            {
                "name": case.name,
                "cold": _summary(cold_samples),
                "warm": _summary(warm_samples),
            }
        )
    return {
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
        "database": str(path),
        "databaseBytes": path.stat().st_size,
        "coldIterations": cold_iterations,
        "warmIterations": warm_iterations,
        "cases": results,
    }


def benchmark_unit_explorer(
    path: Path, iterations: int, *, profile: bool = False,
    pages: bool = False, page_names: Sequence[str] = (),
) -> None:
    """Measure loopback HTTP and completed DOM updates on a fresh app per sample."""
    import cProfile
    import pstats
    from socketserver import ThreadingMixIn
    from threading import Thread
    from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

    from playwright.sync_api import sync_playwright  # pyright: ignore[reportMissingImports]

    from infinity_db.web import create_app

    class Server(ThreadingMixIn, WSGIServer):
        daemon_threads = True

    class QuietHandler(WSGIRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

    samples: dict[str, list[float]] = {}
    page_cases = {
        "/units/minutemen": "#unit-content",
        "/units/dragoes": "#unit-content",
        "/skills/mimetism": "#skill-content",
        "/equipment/medikit": "#item-content",
        "/weapons/combi-rifle": "#item-content",
        "/skills": "#catalog-table-container",
        "/equipment": "#catalog-table-container",
        "/weapons": "#catalog-table-container",
        "/armies": "#army-overview-groups",
    }

    if page_names:
        page_names = tuple("/" + name.lstrip("/") for name in page_names)
        unknown = set(page_names) - page_cases.keys()
        if unknown:
            raise ValueError(f"Unknown page benchmark cases: {', '.join(sorted(unknown))}")
        page_cases = {route: page_cases[route] for route in page_names}

    def run_sample(browser: Any, selected_route: str = "") -> None:
        app = create_app(path, rules_database_path=path.with_name("rules_n5.db"))
        def serve(environ, start_response):
            if (
                profile and (
                    (pages and environ.get("PATH_INFO") in {
                        "/api" + selected_route, "/api/variant-usage", "/api/visible-unit-ids",
                    })
                    or (not pages and (
                        environ.get("PATH_INFO") == "/api/unit-filters"
                        or (environ.get("PATH_INFO") == "/api/units"
                            and "extended=1" in environ.get("QUERY_STRING", ""))
                    ))
                )
            ):
                profiler = cProfile.Profile()
                result = profiler.runcall(app, environ, start_response)
                print("API profile:", environ["PATH_INFO"], environ["QUERY_STRING"], flush=True)
                pstats.Stats(profiler).strip_dirs().sort_stats("cumulative").print_stats(25)
                return result
            return app(environ, start_response)

        server = make_server(
            "127.0.0.1", 0, serve, server_class=Server, handler_class=QuietHandler,
        )
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            def measure(name: str, action: Callable[[], object]) -> None:
                started = time.perf_counter()
                with page.expect_response(
                    lambda response: "/api/units?" in response.url
                    and response.request.method == "GET",
                    timeout=60_000,
                ) as response_info:
                    action()
                response = response_info.value
                if not response.ok:
                    raise ValueError(f"Unit Explorer returned HTTP {response.status}")
                page.wait_for_function(
                    """() => document.querySelector('#unit-count')
                    ?.getAttribute('aria-busy') === 'false'
                    && !document.querySelector('#table-container').hidden""",
                    timeout=60_000,
                )
                samples.setdefault(name, []).append(time.perf_counter() - started)
                timing = response.request.timing
                if timing["responseEnd"] < 0:
                    raise ValueError("API resource timing unavailable")
                samples.setdefault(name + " API", []).append(timing["responseEnd"] / 1000)

            origin = f"http://127.0.0.1:{server.server_port}"
            if pages:
                ready = page_cases[selected_route]
                detail = ready in {"#skill-content", "#item-content"}
                if detail:
                    page.add_init_script("""(() => {
                        window.detailRenderTimes = [];
                        const observer = new MutationObserver(records => {
                            if (records.some(record =>
                                record.target.id === 'skill-content'
                                || record.target.id === 'item-content')) {
                                window.detailRenderTimes.push(performance.now());
                            }
                        });
                        observer.observe(document, {subtree: true, childList: true});
                    })()""")
                for phase in ("cold", "repeat"):
                    started = time.perf_counter()
                    page.goto(origin + selected_route, wait_until="domcontentloaded")
                    page.locator(ready).wait_for(state="visible", timeout=15_000)
                    elapsed = time.perf_counter() - started
                    samples.setdefault(f"{selected_route} {phase}", []).append(elapsed)
                    if detail:
                        # Wait for follow-up requests, but report observed render
                        # timestamps rather than networkidle's fixed quiet interval.
                        page.wait_for_load_state("networkidle", timeout=15_000)
                        times = page.evaluate("window.detailRenderTimes")
                        if not times:
                            raise ValueError("No detail render observed")
                        samples.setdefault(f"{selected_route} {phase} first DOM", []).append(
                            times[0] / 1000,
                        )
                        samples.setdefault(f"{selected_route} {phase} final DOM", []).append(
                            times[-1] / 1000,
                        )
                        print(f"{selected_route} {phase} renders: {times}", flush=True)
                    resources = page.evaluate("""() => performance.getEntriesByType('resource')
                        .filter(e => new URL(e.name).pathname.startsWith('/api/'))
                        .map(e => ({
                            path: new URL(e.name).pathname,
                            start: Math.round(e.startTime), end: Math.round(e.responseEnd),
                            bytes: e.decodedBodySize,
                        }))""")
                    print(
                        f"{selected_route} {phase}: {elapsed*1000:.1f} ms {resources}",
                        flush=True,
                    )
                if errors:
                    raise ValueError(f"Browser errors: {errors}")
                return
            measure("initial", lambda: page.goto(
                origin + "/units", wait_until="domcontentloaded",
            ))
            resources = page.evaluate("""() => performance.getEntriesByType('resource')
                .filter(entry => new URL(entry.name).pathname.startsWith('/api/'))
                .map(entry => ({
                    path: new URL(entry.name).pathname,
                    start: Math.round(entry.startTime),
                    end: Math.round(entry.responseEnd),
                    bytes: entry.decodedBodySize,
                }))""")
            print(f"Initial API resources: {resources}", flush=True)
            measure("next page", lambda: page.locator("#next-page-top").click())
            measure("previous page", lambda: page.locator("#previous-page-top").click())
            measure("Extended", lambda: page.locator("#extended-results").check())
            page.locator(".unit-extended-profile").first.wait_for(state="visible")
            measure("Extended next", lambda: page.locator("#next-page-top").click())
            measure("Extended previous", lambda: page.locator("#previous-page-top").click())
            measure("compact", lambda: page.locator("#extended-results").uncheck())
            measure("search", lambda: page.locator("#unit-search").fill("fusiliers"))
            if errors:
                raise ValueError(f"Browser errors: {errors}")
            print("Completed browser sample", flush=True)
        finally:
            context.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    with sync_playwright() as driver:
        browser = driver.chromium.launch(channel="chrome")
        try:
            for _ in range(iterations):
                if pages:
                    for route in page_cases:
                        run_sample(browser, route)
                else:
                    run_sample(browser)
        finally:
            browser.close()

    for name, values in samples.items():
        summary = _summary(values)
        print(f"{name:<24} p50 {summary['medianMs']:8.1f} ms  p95 {summary['p95Ms']:8.1f} ms")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path, help="Path to a built army.db snapshot.")
    parser.add_argument("--cold-iterations", type=int, default=20)
    parser.add_argument("--warm-iterations", type=int, default=200)
    parser.add_argument("--case", action="append", default=[], help="Run only this named case.")
    parser.add_argument("--profile", action="store_true", help="Profile each selected case.")
    parser.add_argument("--browser", action="store_true", help="Benchmark Unit Explorer in Chrome.")
    parser.add_argument("--pages", action="store_true", help="Benchmark detail and catalog pages.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cold_iterations < 1 or args.warm_iterations < 1:
        raise SystemExit("iteration counts must be positive")
    try:
        if args.browser or args.pages:
            if args.json or (args.browser and (args.case or args.pages)):
                raise ValueError("--browser cannot be combined with --case, --pages or --json")
            benchmark_unit_explorer(
                args.database, args.cold_iterations, profile=args.profile,
                pages=args.pages, page_names=args.case,
            )
            return 0
        if args.profile:
            import cProfile
            import pstats

            if not args.case or args.json:
                raise ValueError("--profile requires --case and cannot be combined with --json")
            cases = {case.name: case for case in discover_cases(Database(args.database))}
            for name in args.case:
                if name not in cases:
                    raise ValueError(f"Unknown benchmark case: {name}")
                print(f"Profile: {name}", flush=True)
                profiler = cProfile.Profile()
                database = Database(args.database)
                setup = cases[name].setup
                if setup is not None:
                    setup(database)
                profiler.runcall(cases[name].action, database)
                pstats.Stats(profiler).strip_dirs().sort_stats("cumulative").print_stats(25)
            return 0
        report = benchmark_database(
            args.database,
            cold_iterations=args.cold_iterations,
            warm_iterations=args.warm_iterations,
            case_names=args.case,
        )
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    print(f"Runtime benchmark: {report['database']}")
    print(f"Database size: {report['databaseBytes']:,} bytes")
    print(
        f"Samples: {report['coldIterations']} cold / "
        f"{report['warmIterations']} warm per case"
    )
    for case in report["cases"]:
        cold = case["cold"]
        warm = case["warm"]
        print(
            f"{case['name']:<20} "
            f"cold p50 {cold['medianMs']:8.3f} ms  p95 {cold['p95Ms']:8.3f} ms | "
            f"warm p50 {warm['medianMs']:8.3f} ms  p95 {warm['p95Ms']:8.3f} ms"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
