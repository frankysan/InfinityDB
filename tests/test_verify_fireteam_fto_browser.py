"""Real Chromium acceptance for source-verified, Army-local Fireteam FTO profiles."""

from __future__ import annotations

from socketserver import ThreadingMixIn
from threading import Thread
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

import pytest

from infinity_db.database import Database
from infinity_db.web import create_app


def _verified(member: dict) -> bool:
    return (
        member.get("fto_marker") is not None
        and member.get("resolution") == "army"
        and member.get("source_unit_id") is not None
        and member.get("unit") is not None
        and bool(member.get("loadouts"))
    )


def _summary(member: dict) -> str:
    marker = member["fto_marker"]
    label = "FTO" if marker == "generic" else f"FTO-{marker}"
    names = [item["name"] for item in member["loadouts"] if item.get("name")]
    return f"{label} profile{'' if len(names) == 1 else 's'}: {'; '.join(names)}"


def test_live_fireteam_fto_is_scoped_to_verified_member_options() -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    army_db = root / "data/generated/infinity.db"
    rules_db = root / "data/generated/rules.db"
    database = Database(army_db)

    selection = None
    for army in database.list_fireteam_armies():
        chart = database.get_fireteam_chart(army["id"])
        if chart is None:
            continue
        visible_teams = [team for team in chart["teams"] if not team["is_wildcard"]]
        if not visible_teams:
            continue
        resolved = [
            member for team in visible_teams for member in team["members"]
            if _verified(member)
        ]
        if resolved:
            selection = (army, chart, visible_teams, resolved)
            break
    assert selection is not None, "No pinned Army-local FTO profile available to verify"
    army, chart, visible_teams, resolved = selection
    expected = sorted(_summary(member) for member in resolved)

    class ThreadedServer(ThreadingMixIn, WSGIServer):
        daemon_threads = True

    class QuietHandler(WSGIRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

    app = create_app(army_db, rules_database_path=rules_db)
    server = make_server(
        "127.0.0.1", 0, app, server_class=ThreadedServer,
        handler_class=QuietHandler,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        with sync_api.sync_playwright() as driver:
            try:
                browser = driver.chromium.launch(channel="chrome")
            except Exception as exc:
                if "Executable doesn't exist" in str(exc) or "not found" in str(exc):
                    pytest.skip(f"Chromium unavailable: {exc}")
                raise
            try:
                for width in (1440, 390):
                    page = browser.new_page(viewport={"width": width, "height": 900})
                    page_errors: list[str] = []
                    failed_requests: list[str] = []
                    http_errors: list[str] = []
                    page.on(
                        "pageerror", lambda error, errors=page_errors: errors.append(str(error))
                    )
                    page.on(
                        "requestfailed",
                        lambda request, failures=failed_requests: failures.append(
                            f"{request.url}: {request.failure}"
                        ),
                    )
                    page.on(
                        "response",
                        lambda response, errors=http_errors: errors.append(
                            f"{response.status} {response.url}"
                        ) if response.status >= 400 else None,
                    )
                    try:
                        page.goto(
                            f"{base}/fireteams?army={army['id']}",
                            wait_until="domcontentloaded",
                        )
                        try:
                            page.locator("#fireteam-content").wait_for(
                                state="visible", timeout=60000,
                            )
                        except sync_api.TimeoutError as exc:
                            error_text = page.locator(
                                "#fireteam-error-message"
                            ).all_text_contents()
                            raise AssertionError(
                                f"Fireteam content stayed hidden: army={army['id']}, "
                                f"width={width}, "
                                f"loading={page.locator('#fireteam-loading').is_visible()}, "
                                f"error={error_text!r}, "
                                f"page_errors={page_errors[:8]!r}, "
                                f"failed_requests={failed_requests[:12]!r}, "
                                f"http_errors={http_errors[:12]!r}"
                            ) from exc
                        summaries = page.locator(".fireteam-member-fto-summary")
                        assert summaries.count() == len(expected), (army["name"], width)
                        assert sorted(summaries.all_text_contents()) == expected
                        assert all(
                            not row.locator(
                                "th.table-column--primary .skill-category-badge"
                            ).filter(has_text="Wildcard").count()
                            for row in page.locator(
                                ".fireteam-member-table tr:has(.fireteam-member-fto-summary)"
                            ).all()
                        )
                        assert all(
                            row.locator("th.table-column--primary a[href^='/units/']").count()
                            for row in page.locator(
                                ".fireteam-member-table tr:has(.fireteam-member-fto-summary)"
                            ).all()
                        )
                        assert not page.locator(
                            ".fireteam-member-table .developer-only"
                        ).first.is_visible()
                        assert page.evaluate(
                            "() => document.documentElement.scrollWidth <= innerWidth + 1"
                        )
                    finally:
                        page.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
