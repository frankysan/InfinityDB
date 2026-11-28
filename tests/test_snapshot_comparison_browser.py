"""Local snapshot report review through the packaged browser shell."""
from __future__ import annotations

import json
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from infinity_db.web import create_app
from tests.test_army_snapshot_diff import documents, snapshot
from tools.browser_wsgi_transport import route_browser_page
from tools.data.compare_army_snapshots import compare_snapshots
from tools.testing.browser_test_metrics import launch_timed_chromium

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://infinitydb-snapshot-review.test"


@pytest.fixture(scope="module")
def app() -> Any:
    return create_app(
        ROOT / "data/generated/army.db",
        rules_database_path=ROOT / "data/generated/rules_n5.db",
    )


@pytest.fixture(scope="module")
def chrome() -> Iterator[Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as driver:
        try:
            browser = launch_timed_chromium(driver, "snapshot-review")
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or "not found" in str(exc):
                pytest.skip(f"Chrome unavailable: {exc}")
            raise
        try:
            yield browser
        finally:
            browser.close()


@pytest.fixture
def report(tmp_path: Path) -> dict:
    before = documents()
    after = deepcopy(before)
    unit = after["101-panoceania.json"]["units"][0]
    group = unit["profileGroups"][0]
    group["profiles"][0]["skills"] = []
    group["options"][0]["skills"] = [{"id": 1}]
    group["profiles"][0]["bs"] = 13
    group["profiles"][0]["notes"] = None
    group["options"][0]["name"] = "<img src=x onerror=alert(1)>"
    for index in range(40):
        unit[f"testField{index}"] = index
    before["102-removed.json"] = deepcopy(before["101-panoceania.json"])
    after["103-added.json"] = deepcopy(after["101-panoceania.json"])
    a, am = snapshot(tmp_path / "before", "before.zip", before)
    b, bm = snapshot(tmp_path / "after", "after.zip", after)
    return compare_snapshots(a, am, b, bm)


@pytest.mark.parametrize("width", [1440, 390])
def test_review_local_report(
    app: Any, chrome: Any, report: dict, width: int,
) -> None:
    page = chrome.new_page(viewport={"width": width, "height": 900})
    route_browser_page(page, app, ORIGIN)
    errors: list[str] = []
    requests: list[tuple[str, str]] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: requests.append((request.method, request.url)))
    try:
        page.goto(f"{ORIGIN}/snapshot-compare", wait_until="domcontentloaded")
        assert page.locator("#snapshot-review").is_hidden()
        assert page.locator('a[href="/snapshot-compare"]').get_attribute("aria-current") == "page"
        assert page.locator('a[href="/snapshot-compare"]').is_hidden()
        page.locator("#snapshot-report").set_input_files({
            "name": "report.json", "mimeType": "application/json",
            "buffer": json.dumps(report).encode(),
        })
        page.locator("#snapshot-review").wait_for(state="visible")
        assert "before.zip" in page.locator("#snapshot-endpoints").inner_text()
        assert "after.zip" in page.locator("#snapshot-endpoints").inner_text()
        assert page.locator(".snapshot-change").count() == 30
        page.locator("#snapshot-next").click()
        assert page.locator("#snapshot-count").inner_text().startswith("31–")
        page.locator("#snapshot-kind").select_option("added")
        assert page.locator(".snapshot-change").count() == 1
        assert "103-added.json" in page.locator("#snapshot-results").inner_text()
        page.locator("#snapshot-kind").select_option("removed")
        assert "102-removed.json" in page.locator("#snapshot-results").inner_text()
        page.locator("#snapshot-kind").select_option("updated")
        page.locator("#snapshot-search").fill("notes")
        page.locator(".snapshot-change > summary").click()
        page.locator(".snapshot-change pre").first.wait_for(state="visible")
        assert "Not present" in page.locator(".snapshot-change").inner_text()
        assert page.locator(".snapshot-change pre").first.inner_text() == "null"
        page.locator("#snapshot-search").fill("options / 1 / name")
        page.locator(".snapshot-change > summary").click()
        page.locator(".snapshot-change pre").first.wait_for(state="visible")
        assert "<img src=x onerror=alert(1)>" in page.locator(".snapshot-change").inner_text()
        assert page.locator(".snapshot-change img").count() == 0
        page.locator("#snapshot-search").fill("")
        page.locator("#snapshot-kind").select_option("effective")
        assert page.locator(".snapshot-change").count() > 0
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        assert not [url for method, url in requests if method != "GET"]
        assert not [url for _, url in requests if "report.json" in url]
        page.locator("#snapshot-report").set_input_files({
            "name": "invalid.json", "mimeType": "application/json", "buffer": b"{}",
        })
        page.wait_for_function("document.querySelector('#snapshot-status').textContent.includes('Invalid')")
        assert page.locator("#snapshot-review").is_hidden()
        assert page.locator(".snapshot-change").count() == 0
        assert not errors, errors
    finally:
        page.close()
