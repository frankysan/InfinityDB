"""Optional Chromium timing and a worker-local, capacity-owned browser pool.

Only the explicitly grouped four-lane benchmark may enable the pool.
An acquired OS slot stays held until the browser is closed, so other
workers cannot launch an uncounted browser while the pooled one is idle.
"""

from __future__ import annotations

import json
import os
import time
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from tools.browser_test_capacity import browser_slot

# Exactly these modules are grouped on chromium-b in four-lane mode.
POOLED_BROWSER_MODULES = frozenset({
    "test_verify_ammunition_publication_browser",
    "test_verify_sidebar_density_browser",
    "test_verify_weapon_source_cards_browser",
})


def record_browser_duration(event: str, label: str, elapsed_seconds: float) -> None:
    """Write an opt-in event to the same ignored directory as slot timings."""
    directory = os.environ.get("INFINITYDB_BROWSER_METRICS_DIRECTORY")
    if not directory:
        return
    output_dir = Path(directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "event": event,
        "label": label,
        "pid": os.getpid(),
        "seconds": elapsed_seconds,
    }
    with (output_dir / f"browser-{os.getpid()}.jsonl").open(
        "a", encoding="utf-8",
    ) as output:
        output.write(json.dumps(record, sort_keys=True) + "\n")


class TimedBrowser:
    """Proxy the browser API, measuring per-test context/page construction."""

    def __init__(self, browser: Any, label: str):
        self._browser = browser
        self._label = label

    def new_page(self, **kwargs: Any) -> Any:
        started = time.monotonic()
        try:
            return self._browser.new_page(**kwargs)
        finally:
            record_browser_duration(
                "new_page", self._label, time.monotonic() - started,
            )

    def close(self) -> None:
        started = time.monotonic()
        try:
            self._browser.close()
        finally:
            record_browser_duration(
                "close", self._label, time.monotonic() - started,
            )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._browser, name)


def launch_timed_chromium(driver: Any, label: str) -> TimedBrowser:
    """Launch real Chrome, preserving its original launch errors."""
    started = time.monotonic()
    try:
        browser = driver.chromium.launch(channel="chrome")
    except BaseException:
        record_browser_duration("launch_error", label, time.monotonic() - started)
        raise
    record_browser_duration("launch", label, time.monotonic() - started)
    return TimedBrowser(browser, label)


class ChromiumLanePool:
    """Reuse one Chrome process across lane B modules, never across workers."""

    def __init__(self, lock_directory: Path, *, slots: int):
        self._lock_directory = lock_directory
        self._slots = slots
        self._stack = ExitStack()
        self._browser: TimedBrowser | None = None
        self._finished: set[str] = set()

    def get(self) -> TimedBrowser:
        if self._browser is None:
            from playwright.sync_api import sync_playwright

            try:
                self._stack.enter_context(browser_slot(
                    self._lock_directory,
                    slots=self._slots,
                    label="pooled-chromium-b",
                ))
                driver = self._stack.enter_context(sync_playwright())
                browser = launch_timed_chromium(driver, "pooled-chromium-b")
                self._stack.callback(browser.close)
                self._browser = browser
            except BaseException:
                self.close()
                raise
        return self._browser

    def finished_module(self, module: str) -> None:
        if module not in POOLED_BROWSER_MODULES:
            raise ValueError(f"Unexpected pooled browser module: {module}")
        self._finished.add(module)
        if self._finished == POOLED_BROWSER_MODULES:
            self.close()

    def close(self) -> None:
        self._stack.close()
        self._browser = None
