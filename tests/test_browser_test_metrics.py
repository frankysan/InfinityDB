"""Worker-scoped Chromium reuse keeps one real launch and one admission lease."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools.browser_test_capacity import browser_slot
from tools.browser_test_metrics import (
    POOLED_BROWSER_MODULES,
    ChromiumLanePool,
    TimedBrowser,
    launch_timed_chromium,
)
from tools.performance import probe_docker_test_host


class _FakeBrowser:
    def __init__(self) -> None:
        self.pages = 0
        self.closes = 0

    def new_page(self, **kwargs: Any) -> object:
        self.pages += 1
        return object()

    def close(self) -> None:
        self.closes += 1


class _FakeDriver:
    def __init__(self) -> None:
        self.launches = 0
        self.browser = _FakeBrowser()
        self.chromium = self

    def launch(self, *, channel: str) -> _FakeBrowser:
        assert channel == "chrome"
        self.launches += 1
        return self.browser


def test_docker_probe_does_not_invoke_missing_cli(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(probe_docker_test_host.shutil, "which", lambda name: None)
    assert probe_docker_test_host.main() == 0
    assert "unavailable on MCP server process PATH" in capsys.readouterr().out


def test_launch_and_context_metrics_are_opt_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("INFINITYDB_BROWSER_METRICS_DIRECTORY", raising=False)
    driver = _FakeDriver()
    browser = launch_timed_chromium(driver, "baseline")
    assert isinstance(browser, TimedBrowser)
    browser.new_page(viewport={"width": 390})
    browser.close()
    assert driver.launches == 1
    assert driver.browser.pages == 1
    assert driver.browser.closes == 1
    assert not list(tmp_path.iterdir())

    directory = tmp_path / "metrics"
    monkeypatch.setenv("INFINITYDB_BROWSER_METRICS_DIRECTORY", str(directory))
    browser = launch_timed_chromium(driver, "measured")
    browser.new_page(viewport={"width": 1440})
    browser.close()
    rows = [
        json.loads(line)
        for line in next(directory.glob("browser-*.jsonl")).read_text().splitlines()
    ]
    assert [row["event"] for row in rows] == ["launch", "new_page", "close"]
    assert all(row["label"] == "measured" and row["seconds"] >= 0 for row in rows)


def test_lane_pool_reuses_one_browser_and_releases_its_slot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    driver = _FakeDriver()

    class _DriverContext:
        def __enter__(self) -> _FakeDriver:
            return driver

        def __exit__(self, *_args: object) -> None:
            pass

    monkeypatch.setattr(sync_api, "sync_playwright", _DriverContext)
    pool = ChromiumLanePool(tmp_path, slots=1)
    with pytest.raises(ValueError, match="Unexpected pooled"):
        pool.finished_module("some_other_module")
    first = pool.get()
    second = pool.get()
    assert first is second
    assert driver.launches == 1
    # The slot is kept while the Chromium process remains reusable.
    with pytest.raises(TimeoutError):
        with browser_slot(tmp_path, slots=1, timeout_seconds=0):
            pass
    for module in sorted(POOLED_BROWSER_MODULES):
        pool.finished_module(module)
    assert driver.browser.closes == 1
    # Closing the final module releases the slot without waiting for worker exit.
    with browser_slot(tmp_path, slots=1, timeout_seconds=0):
        pass
    pool.close()
    assert driver.browser.closes == 1
