"""End-to-end published deployed-object API and page acceptance."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable, Iterator
from pathlib import Path
from socketserver import ThreadingMixIn
from threading import Thread
from typing import Any
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.web import create_app
from tools.browser_wsgi_transport import route_browser_page
from tools.build_deployed_object_publication import build_publication, publication_bytes


class _ThreadedServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class _QuietHandler(WSGIRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def published_app(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[Callable, str]]:
    root = Path(__file__).resolve().parents[1]
    tmp = tmp_path_factory.mktemp("deployed-pub")
    inputs = (
        root / "data/generated/infinity.db",
        root / "data/generated/rules.db",
        root / "data/curated/rules/n5-core-v5.3.json",
        root / "config/validation/deployed-object-delivery-reviews.json",
        root / "config/validation/deployed-object-candidate-reviews.json",
    )
    if not all(path.is_file() for path in inputs):
        pytest.skip("Pinned source databases unavailable")
    army = tmp / "infinity.db"
    rules = tmp / "rules.db"
    shutil.copyfile(inputs[0], army)
    shutil.copyfile(inputs[1], rules)
    publication = build_publication(*inputs)
    (tmp / "deployed-objects.json").write_bytes(publication_bytes(publication))
    app = create_app(army, rules_database_path=rules)
    server = make_server(
        "127.0.0.1", 0, app, server_class=_ThreadedServer, handler_class=_QuietHandler
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield app, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _request(app: Callable, path: str) -> tuple[int, bytes]:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ["PATH_INFO"] = path
    results: dict[str, Any] = {}

    def start_response(status: str, headers: list, exc_info=None) -> None:
        results["status"] = int(status.split()[0])

    body = b"".join(app(environ, start_response))
    return results["status"], body


def test_deployed_reference_api_has_reviewed_objects_and_no_invented_units(
    published_app: tuple[Callable, str],
) -> None:
    app, _ = published_app
    code, content = _request(app, "/api/deployed-objects")
    assert code == 200
    result = json.loads(content)
    assert len(result["items"]) == 17
    assert len(result["unresolved_deliveries"]) == 1
    objects = {obj["name"]: obj for obj in result["items"]}
    assert objects["Deployable Cover"]["attributes"]["ARM"]["status"] == "unreported"
    assert objects["Dazer"]["attributes"]["S"]["status"] == "disputed"
    assert objects["Deployable Cover"]["sourceProfile"] is None
    for name, expected in (
        ("Dazer", {
            ("equipment:dazer", "Place Deployable Skill"),
        }),
        ("Deployable Cover", {
            ("equipment:deployable-cover", "Place Deployable Skill with Perimeter positioning"),
        }),
        ("Cybermine", {
            ("weapon:cybermine", "Place Deployable Skill"),
            ("weapon:cybermine", "Intuitive Attack WIP Roll for Camouflage Marker exception"),
        }),
    ):
        obj = objects[name]
        assert {(edge["recordId"], edge["method"]) for edge in obj["deliverySources"]} == expected
        assert all(
            use["originRecordId"] in {edge[0] for edge in expected}
            for use in obj["unitUses"]
        )
    assert objects["Cybermine"]["unitUses"]

    repeater = objects["Deployable Repeater"]
    assert {row["recordId"] for row in repeater["deliverySources"]} == {
        "weapon:pitcher", "equipment:deployable-repeater",
    }
    assert "units" not in repeater and "carriers" not in repeater
    assert {
        edge["method"] for edge in objects["WildParrot"]["deliverySources"]
    } == {
        "Place Deployable Skill with Perimeter positioning",
        "Intuitive Attack WIP Roll with Perimeter positioning",
    }
    assert objects["FastPanda"]["deliverySources"][0]["recordId"] == (
        "equipment:fastpanda"
    )
    for name, record_id in (
        ("Crazykoala", "weapon:crazykoala"),
        ("Madtraps", "weapon:madtraps"),
    ):
        obj = objects[name]
        assert obj["sourceProfile"]["catalog"] == "weapon"
        assert [(edge["recordId"], edge["method"]) for edge in obj["deliverySources"]] == [
            (record_id, "Place Deployable Skill with Perimeter positioning"),
        ]
        assert all(use["originRecordId"] == record_id for use in obj["unitUses"])
        assert obj["unitUses"], name
    assert objects["Armed Turret"]["sourceProfile"] is None
    assert objects["Armed Turret"]["attributes"]["S"]["status"] == "disputed"
    assert objects["Armed Turret"]["deliverySources"][0]["recordId"] == (
        "weapon:armed-turret"
    )
    assert all(
        (use["originRecordId"], use["method"]) in {
            (edge["recordId"], edge["method"]) for edge in obj["deliverySources"]
        }
        for obj in result["items"] for use in obj["unitUses"]
    )
    assert any(obj["unitUses"] for obj in result["items"])
    first_use = next(
        use for obj in result["items"] for use in obj["unitUses"]
    )
    unit_status, _ = _request(app, f"/units/{first_use['unitSlug']}")
    assert unit_status == 200, first_use

    # Every source link is a real Army-backed catalog entry, not a guessed slug.
    for obj in result["items"]:
        source = obj["sourceProfile"]
        if source is not None:
            catalog = "weapons" if source["catalog"] == "weapon" else "equipment"
            status, _ = _request(app, f"/api/{catalog}/{source['sourceId']}")
            assert status == 200, (obj["id"], catalog, source["sourceId"])
        for edge in obj["deliverySources"]:
            domain, slug = edge["recordId"].split(":", 1)
            catalog = "weapons" if domain == "weapon" else "equipment"
            status, _ = _request(app, f"/api/{catalog}/{slug}")
            assert status == 200, (obj["id"], edge["recordId"])

    status, detail = _request(app, f"/api/deployed-objects/{repeater['id']}")
    assert status == 200
    assert json.loads(detail) == repeater

    status, _ = _request(app, "/api/deployed-objects/unknown")
    assert status == 404


def test_published_reference_is_discoverable_in_normal_browser_pages(
    published_app: tuple[Callable, str],
) -> None:
    app, _ = published_app
    for page in ("/weapons", "/equipment", "/deployed-objects"):
        status, html = _request(app, page)
        assert status == 200
        assert b"/deployed-objects" in html
    status, script = _request(app, "/static/deployed-objects.js")
    assert status == 200
    assert b"deployed-object-entry" in script


def test_chromium_reviewed_attributes_delivery_navigation_and_missing_values(
    published_app: tuple[Callable, str],
) -> None:
    app, origin = published_app
    status, body = _request(app, "/api/deployed-objects")
    assert status == 200
    include_object = next(
        obj for obj in json.loads(body)["items"]
        if any(use["kind"] == "unit-option-include" for use in obj["unitUses"])
    )
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(channel="chrome")
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or "not found" in str(exc):
                pytest.skip(f"Chrome unavailable: {exc}")
            raise
        try:
            for width in (1440, 390):
                page = browser.new_page(viewport={"width": width, "height": 900})
                route_browser_page(page, app, origin)
                errors: list[str] = []
                page.on("pageerror", lambda error, failures=errors: failures.append(str(error)))
                try:
                    page.goto(f"{origin}/deployed-objects", wait_until="domcontentloaded")
                    page.locator("#deployed-list").wait_for(state="visible", timeout=60000)
                    assert page.locator(".deployed-object-entry").count() == 17
                    assert "17 reviewed" in page.locator("#deployed-count").inner_text()

                    cover = page.locator(".deployed-object-entry").filter(
                        has=page.get_by_role("heading", name="Deployable Cover", exact=True)
                    )
                    assert cover.count() == 1
                    assert "Not reported" in cover.inner_text()
                    assert "3" in cover.inner_text()
                    dazer = page.locator(".deployed-object-entry").filter(
                        has=page.get_by_role("heading", name="Dazer", exact=True)
                    )
                    assert "sources disagree" in dazer.inner_text()
                    assert "N5.3 PDF" in dazer.inner_text()
                    assert dazer.locator('a[href^="/equipment/"]').count() == 2
                    assert dazer.locator('a[href="/equipment/dazer"]').count() == 1
                    assert cover.locator(
                        'a[href="/equipment/deployable-cover"]'
                    ).count() == 2

                    repeater = page.locator(".deployed-object-entry").filter(
                        has=page.get_by_role(
                            "heading", name="Deployable Repeater", exact=True
                        )
                    )
                    assert repeater.locator("a[href='/weapons/pitcher']").count() == 1
                    assert repeater.locator(
                        "a[href='/equipment/deployable-repeater']"
                    ).count() == 1
                    for name, slug in (
                        ("Crazykoala", "crazykoala"),
                        ("Madtraps", "madtraps"),
                    ):
                        device = page.locator(".deployed-object-entry").filter(
                            has=page.get_by_role("heading", name=name, exact=True)
                        )
                        assert device.count() == 1
                        assert device.locator(f'a[href="/weapons/{slug}"]').count() >= 1
                        assert "Place Deployable Skill with Perimeter positioning" in (
                            device.inner_text()
                        )
                        assert device.locator(".deployed-object-unit-uses").count() == 1
                    for name, slug in (
                        ("AP Mine", "ap-mine"),
                        ("E/M Mine", "e-m-mine"),
                        ("Monofilament Mine", "monofilament-mine"),
                        ("PARA Mine", "para-mine"),
                        ("Shock Mine", "shock-mine"),
                        ("Viral Mine", "viral-mine"),
                    ):
                        mine = page.locator(".deployed-object-entry").filter(
                            has=page.get_by_role("heading", name=name, exact=True)
                        )
                        assert mine.count() == 1
                        assert "sources disagree" in mine.inner_text()
                        assert "Place Deployable Skill" in mine.inner_text()
                        assert "Intuitive Attack WIP Roll" in mine.inner_text()
                        assert mine.locator(f'a[href="/weapons/{slug}"]').count() == 2
                    assert "Mine Dispenser" in page.locator("#deployed-unresolved").inner_text()
                    usage = page.locator(".deployed-object-unit-uses")
                    assert usage.count() > 0
                    first = usage.first
                    first.locator("summary").click()
                    first.locator("li").first.wait_for(state="visible", timeout=10000)
                    assert first.locator("li").count() > 0
                    assert first.locator('a[href^="/units/"]').count() > 0
                    included = page.locator(
                        f'.deployed-object-entry[id="{include_object["id"]}"]'
                    ).locator(".deployed-object-unit-uses")
                    if not included.evaluate("(node) => node.open"):
                        included.locator("summary").click()
                    included.locator("li").first.wait_for(state="visible", timeout=10000)
                    assert "includes" in included.inner_text()
                    assert "no Army assignment" in included.inner_text()
                    assert not errors, errors
                    assert page.evaluate(
                        "() => document.documentElement.scrollWidth <= window.innerWidth + 1"
                    ), width

                    anchor = repeater.locator("h3 a")
                    href = anchor.get_attribute("href")
                    assert href and href.startswith("#army-")
                    anchor.focus()
                    page.keyboard.press("Enter")
                    page.wait_for_function(
                        "(id) => document.activeElement?.id === id",
                        arg=href[1:],
                    )
                    assert page.evaluate("location.hash") == href
                finally:
                    page.close()
        finally:
            browser.close()


def test_unpublished_legacy_database_does_not_infer_object_catalog(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    army = tmp_path / "infinity.db"
    rules = tmp_path / "rules.db"
    shutil.copyfile(root / "data/generated/infinity.db", army)
    shutil.copyfile(root / "data/generated/rules.db", rules)
    app = create_app(army, rules_database_path=rules)
    for path in ("/api/deployed-objects", "/api/deployed-objects/army-weapon-199"):
        status, content = _request(app, path)
        assert status == 503
        assert b"not published" in content
    status, _ = _request(app, "/deployed-objects")
    assert status == 200

