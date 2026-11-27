"""Feedback submission validation, privacy boundaries and shared browser form."""

from __future__ import annotations

import json
import smtplib
from io import BytesIO
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from infinity_db.web import create_app_from_database_set
from infinity_db.web.feedback import MAX_BODY, MAX_REPORTS_PER_MINUTE, FeedbackHandler, MailDelivery
from tools.browser_wsgi_transport import route_browser_page

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://infinitydb-feedback.test"
VALID = {"category": "data", "message": "Wrong value\nExpected a different value.",
         "page": "/units/401", "website": ""}


def environment(payload: Any = VALID, **overrides: Any) -> dict[str, Any]:
    raw = json.dumps(payload).encode("utf-8")
    return {
        "REQUEST_METHOD": "POST", "HTTP_ORIGIN": ORIGIN,
        "HTTP_HOST": "infinitydb-feedback.test", "HTTP_SEC_FETCH_SITE": "same-origin",
        "CONTENT_TYPE": "application/json", "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": BytesIO(raw), "HTTP_COOKIE": "private-cookie",
        "HTTP_REFERER": ORIGIN + "/?s=private-share",
        "HTTP_USER_AGENT": "private-agent", "REMOTE_ADDR": "private-address",
        **overrides,
    }


def test_valid_report_delivers_only_explicit_fields(caplog: pytest.LogCaptureFixture) -> None:
    delivered: list[dict[str, str]] = []
    handler = FeedbackHandler(delivered.append)
    response = handler.handle(environment())
    assert response.status == 202
    assert response.cache_control == "no-store"
    assert not caplog.records
    assert len(delivered) == 1
    data = delivered[0]
    assert set(data) == {"category", "message", "page", "version"}
    assert data["message"] == VALID["message"]
    assert data["page"] == VALID["page"]
    assert "private-" not in json.dumps(data)


@pytest.mark.parametrize("security,port", [("starttls", 587), ("ssl", 465)])
def test_smtp_transport(security: str, port: int, monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    smtp = MagicMock(return_value=client)
    ssl_smtp = MagicMock(return_value=client)
    monkeypatch.setattr("infinity_db.web.feedback.smtplib.SMTP", smtp)
    monkeypatch.setattr("infinity_db.web.feedback.smtplib.SMTP_SSL", ssl_smtp)
    delivery = MailDelivery("relay.test", port, security, "sender@example.test",
                            "maintainer@example.test", "user", "secret")
    report = {"category": "rules", "message": "Incorrect rule\nBcc: injected@example.test",
              "page": "/skills/11", "version": "test"}
    delivery(report)
    constructor = smtp if security == "starttls" else ssl_smtp
    assert constructor.call_args.args == ("relay.test", port)
    assert constructor.call_args.kwargs["timeout"] == 5
    if security == "starttls":
        client.starttls.assert_called_once()
        assert client.method_calls[0][0] == "starttls"
    else:
        client.starttls.assert_not_called()
        assert "context" in constructor.call_args.kwargs
    client.login.assert_called_once_with("user", "secret")
    message = client.send_message.call_args.args[0]
    assert message["To"] == "maintainer@example.test"
    assert message["Bcc"] is None
    assert report["message"] in message.get_content()
    assert client.send_message.call_args.kwargs["to_addrs"] == ["maintainer@example.test"]
    client.close.assert_called_once()


def test_disabled_or_failed_delivery(caplog: pytest.LogCaptureFixture) -> None:
    handler = FeedbackHandler()
    assert json.loads(handler.handle({"REQUEST_METHOD": "GET"}).body) == {"enabled": False}
    assert handler.handle(environment()).status == 503

    def fail(report: dict[str, str]) -> None:
        raise smtplib.SMTPException(report["message"])

    handler = FeedbackHandler(fail)
    assert json.loads(handler.handle({"REQUEST_METHOD": "GET"}).body) == {"enabled": True}
    assert handler.handle(environment()).status == 503
    assert VALID["message"] not in caplog.text
    assert "Feedback email delivery failed" in caplog.text


def test_mail_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    prefix = "INFINITYDB_FEEDBACK_SMTP_"
    for name in ("HOST", "PORT", "SECURITY", "FROM", "TO", "USERNAME", "PASSWORD"):
        monkeypatch.delenv(prefix + name, raising=False)
    assert MailDelivery.from_environment() is None
    monkeypatch.setenv(prefix + "HOST", "relay.test")
    assert MailDelivery.from_environment() is None
    monkeypatch.setenv(prefix + "FROM", "sender@example.test")
    monkeypatch.setenv(prefix + "TO", "maintainer@example.test")
    delivery = MailDelivery.from_environment()
    assert delivery is not None and delivery.port == 587
    monkeypatch.setenv(prefix + "SECURITY", "ssl")
    delivery = MailDelivery.from_environment()
    assert delivery is not None and delivery.port == 465
    monkeypatch.setenv(prefix + "SECURITY", "plain")
    assert MailDelivery.from_environment() is None
    monkeypatch.setenv(prefix + "SECURITY", "starttls")
    monkeypatch.setenv(prefix + "TO", "a@example.test,b@example.test")
    assert MailDelivery.from_environment() is None


@pytest.mark.parametrize(("overrides", "expected"), [
    ({"REQUEST_METHOD": "PUT"}, 405),
    ({"HTTP_ORIGIN": "https://other.test"}, 403),
    ({"HTTP_ORIGIN": ""}, 403),
    ({"HTTP_ORIGIN": "null"}, 403),
    ({"HTTP_SEC_FETCH_SITE": "cross-site"}, 403),
    ({"CONTENT_TYPE": "text/plain"}, 415),
    ({"CONTENT_LENGTH": ""}, 411),
    ({"CONTENT_LENGTH": str(MAX_BODY + 1)}, 413),
    ({"CONTENT_LENGTH": "50", "wsgi.input": BytesIO(b"{}")}, 400),
    ({"QUERY_STRING": "s=private"}, 400),
])
def test_request_boundaries(overrides: dict[str, Any], expected: int,
                            caplog: pytest.LogCaptureFixture) -> None:
    response = FeedbackHandler().handle(environment(**overrides))
    assert response.status == expected
    assert not caplog.records


@pytest.mark.parametrize("patch", [
    {"website": "bot"}, {"message": " "}, {"message": "x" * 2001},
    {"message": "😀" * 1001},
    {"message": []}, {"category": []}, {"category": "unknown"},
    {"page": "/units/401?s=private"}, {"page": "/units/401#private"},
    {"page": "https://example.com"}, {"page": "/api/version"},
    {"page": "/not-a-page"}, {"email": "private"},
])
def test_rejected_payload(patch: dict[str, Any], caplog: pytest.LogCaptureFixture) -> None:
    assert FeedbackHandler().handle(environment({**VALID, **patch})).status == 400
    assert not caplog.records


def test_rate_limit_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    handler = FeedbackHandler(lambda report: None)
    monkeypatch.setattr("infinity_db.web.feedback.monotonic", lambda: 100.0)
    for _ in range(MAX_REPORTS_PER_MINUTE):
        assert handler.handle(environment({**VALID, "page": ""})).status == 202
    response = handler.handle(environment())
    assert response.status == 429
    assert ("Retry-After", "60") in response.headers
    monkeypatch.setattr("infinity_db.web.feedback.monotonic", lambda: 160.0)
    assert handler.handle(environment()).status == 202


def test_feedback_browser(caplog: pytest.LogCaptureFixture) -> None:
    api = pytest.importorskip("playwright.sync_api")
    app = create_app_from_database_set(ROOT / "data/generated")
    delivered: list[dict[str, str]] = []
    app.feedback = FeedbackHandler(delivered.append)
    with api.sync_playwright() as driver:
        try:
            browser = driver.chromium.launch()
        except Exception as exc:
            if "Executable doesn't exist" in str(exc):
                pytest.skip(f"Chromium unavailable: {exc}")
            raise
        try:
            for width, theme in ((1440, "light"), (390, "dark")):
                page = browser.new_page(viewport={"width": width, "height": 800},
                                        color_scheme=theme)
                route_browser_page(page, app, ORIGIN)
                errors: list[str] = []
                page.on("pageerror", lambda error, errors=errors: errors.append(str(error)))
                page.goto(f"{ORIGIN}/units/401?private=not-submitted#private-fragment")
                page.locator(".page-footer-notice .feedback-open").click()
                dialog = page.locator(".feedback-dialog")
                assert dialog.is_visible()
                context = page.locator("#feedback-context")
                assert "/units/401" in context.inner_text()
                assert "private" not in context.inner_text()
                page.locator("#feedback-include-page").uncheck()
                assert "Page not included" in context.inner_text()
                if width == 1440:
                    page.locator("#feedback-include-page").check()
                page.locator("#feedback-message").fill("Incorrect value")
                page.locator("#feedback-submit").click()
                page.get_by_text("Report received. Thank you.").wait_for(timeout=15000)
                data = delivered[-1]
                assert data["page"] == ("/units/401" if width == 1440 else "")
                assert data["message"] == "Incorrect value"
                assert "private" not in json.dumps(data)
                assert "Incorrect value" not in caplog.text
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                page.locator("#feedback-close").click()
                page.evaluate("() => window.infinityNavigate('/about')")
                page.wait_for_url(f"{ORIGIN}/about")
                page.locator(".page-footer-notice .feedback-open").click()
                assert "/about" in context.inner_text()
                page.keyboard.press("Escape")
                assert not dialog.is_visible()
                assert not errors, errors
                page.close()
        finally:
            browser.close()
