"""Compare resident memory and serving latency with catalog query caches bypassed."""

from __future__ import annotations

import argparse
import ctypes
import gc
import hashlib
import json
import platform
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any, cast

from infinity_db.web.app import create_app_from_database_set
from tools.browser_wsgi_transport import wsgi_response


def resident_bytes() -> int | None:
    """Sample this single serving process, not host memory or aggregate worker RSS."""
    gc.collect()
    if platform.system() == "Linux":
        for line in Path("/proc/self/status").read_text(encoding="ascii").splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
        raise ValueError("Missing VmRSS")
    if platform.system() == "Windows":
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD), ("page_faults", wintypes.DWORD),
                ("peak_working_set", ctypes.c_size_t),
                ("working_set", ctypes.c_size_t),
                ("peak_paged_pool", ctypes.c_size_t), ("paged_pool", ctypes.c_size_t),
                ("peak_nonpaged_pool", ctypes.c_size_t), ("nonpaged_pool", ctypes.c_size_t),
                ("pagefile", ctypes.c_size_t), ("peak_pagefile", ctypes.c_size_t),
            ]

        windows = cast(Any, ctypes)
        current_process = windows.WinDLL("kernel32").GetCurrentProcess
        current_process.restype = wintypes.HANDLE
        get_memory = windows.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
        get_memory.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        get_memory.restype = wintypes.BOOL
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        if not get_memory(current_process(), ctypes.byref(counters), counters.cb):
            raise OSError(windows.get_last_error(), "GetProcessMemoryInfo failed")
        return counters.working_set
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-dir", type=Path, default=Path("data/generated"))
    parser.add_argument("--without-cache", action="store_true")
    args = parser.parse_args()

    started = perf_counter()
    app = create_app_from_database_set(args.db_dir)
    startup = perf_counter() - started
    database = app.database
    if database.catalog_projection is None:
        raise ValueError("This benchmark requires the published catalog projection")
    if args.without_cache:
        # Bypass only these instance LRU wrappers, retaining projection selection,
        # identity resolution, reference enrichment and every other runtime cache.
        for name in ("list_catalog_items", "list_catalog_filter_items",
                     "get_skill", "get_catalog_item"):
            method = getattr(type(database), name).__wrapped__
            setattr(database, name, method.__get__(database))

    def request(route: str) -> bytes:
        status, _, body = wsgi_response(app, "http://localhost" + route)
        if status != 200:
            raise ValueError(f"{route}: HTTP {status}")
        return body

    memory = {"startup": resident_bytes()}
    digest = hashlib.sha256()
    for route in ("/api/units?limit=50&matching_scope=profile&extended=1",
                  "/api/units/minutemen", "/api/glossary", "/api/search?q=mimetism"):
        digest.update(request(route))
    memory["initial_workload"] = resident_bytes()

    cold = []
    count = 0
    for catalog in ("skills", "equipment", "weapons"):
        items = database.list_catalog_items(catalog)
        database.list_catalog_filter_items(catalog)
        for item in items:
            started = perf_counter()
            detail = (database.get_skill(item["id"]) if catalog == "skills"
                      else database.get_catalog_item(catalog, item["id"]))
            cold.append(perf_counter() - started)
            digest.update(json.dumps(detail, sort_keys=True, ensure_ascii=False).encode())
            count += 1
        del items, detail
    memory["catalog_scan"] = resident_bytes()

    timings = {}
    for route in ("/api/skills", "/api/equipment", "/api/weapons",
                  "/api/skills/mimetism", "/api/equipment/medikit", "/api/weapons/combi-rifle"):
        expected = request(route)
        digest.update(expected)
        samples = []
        for _ in range(10):
            started = perf_counter()
            actual = request(route)
            samples.append(perf_counter() - started)
            if actual != expected:
                raise ValueError(f"Repeated response changed: {route}")
        timings[route] = round(median(samples) * 1000, 2)
        del expected, actual
    memory["repeated_requests"] = resident_bytes()

    print(json.dumps({
        "platform": platform.platform(), "python": platform.python_version(),
        "snapshot": app.snapshot_revision, "without_cache": args.without_cache,
        "startup_ms": round(startup * 1000, 2),
        "catalog_details": count, "scan_median_ms": round(median(cold) * 1000, 2),
        "resident_bytes": memory, "repeat_wsgi_median_ms": timings,
        "response_digest": digest.hexdigest(),
    }, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
