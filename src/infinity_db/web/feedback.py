"""Anonymous, explicitly submitted feedback delivered by configured SMTP."""

from __future__ import annotations

import json
import logging
import os
import smtplib
import ssl
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from email.errors import MessageError
from email.headerregistry import Address
from email.message import EmailMessage
from http import HTTPStatus
from threading import Lock
from time import monotonic
from typing import Any
from urllib.parse import urlsplit

from infinity_db import __display_version__
from infinity_db.web.response import WebResponse
from infinity_db.web.routes import metric_route

LOGGER = logging.getLogger(__name__)
MAX_BODY = 16384
MAX_MESSAGE = 2000
MAX_REPORTS_PER_MINUTE = 6
CATEGORIES = frozenset({"data", "rules", "website", "other"})


def _error(message: str, status: HTTPStatus, **kwargs: Any) -> WebResponse:
    return WebResponse.json({"error": message}, status=status, cache_control="no-store", **kwargs)


def _valid_page(path: Any) -> bool:
    if not isinstance(path, str) or len(path) > 240:
        return False
    if path == "":
        return True
    route = metric_route(path, ())
    return route != "/other" and not route.startswith(("/api/", "/static/", "/internal/"))


def _same_origin(environ: dict[str, Any]) -> bool:
    if environ.get("HTTP_SEC_FETCH_SITE", "same-origin") != "same-origin":
        return False
    try:
        origin = urlsplit(environ.get("HTTP_ORIGIN", ""))
    except ValueError:
        return False
    # Caddy may terminate HTTP behind another HTTPS proxy. Compare the
    # browser Origin authority with the forwarded request Host, not the
    # upstream WSGI scheme; Fetch Metadata also rejects cross-scheme requests.
    return (
        origin.scheme in {"http", "https"}
        and bool(origin.netloc)
        and origin.netloc.lower() == environ.get("HTTP_HOST", "").lower()
        and not (origin.path or origin.query or origin.fragment or origin.username)
    )


@dataclass(frozen=True)
class MailDelivery:
    host: str
    port: int
    security: str
    sender: str
    recipient: str
    username: str = ""
    password: str = field(default="", repr=False)

    @classmethod
    def from_environment(cls) -> MailDelivery | None:
        prefix = "INFINITYDB_FEEDBACK_SMTP_"
        host = os.environ.get(prefix + "HOST", "").strip()
        if not host:
            return None
        try:
            security = os.environ.get(prefix + "SECURITY", "starttls").strip().lower()
            if security not in {"starttls", "ssl"}:
                raise ValueError("Invalid SMTP security")
            port = int(os.environ.get(prefix + "PORT") or ("465" if security == "ssl" else "587"))
            if not 1 <= port <= 65535:
                raise ValueError("Invalid SMTP port")
            sender = str(Address(addr_spec=os.environ.get(prefix + "FROM", "")))
            recipient = str(Address(addr_spec=os.environ.get(prefix + "TO", "")))
            if not all("@" in address for address in (sender, recipient)):
                raise ValueError("Invalid SMTP address")
            username = os.environ.get(prefix + "USERNAME", "")
            password = os.environ.get(prefix + "PASSWORD", "")
            if bool(username) != bool(password):
                raise ValueError("Incomplete SMTP credentials")
            return cls(host, port, security, sender, recipient, username, password)
        except (ValueError, TypeError, IndexError, MessageError):
            LOGGER.warning("Feedback email configuration is invalid; reporting disabled")
            return None

    def __call__(self, report: dict[str, str]) -> None:
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = self.recipient
        message["Subject"] = "InfinityDB error report"
        message.set_content(
            f"Category: {report['category']}\n"
            f"Page: {report['page'] or '(not included)'}\n"
            f"Version: {report['version']}\n\n"
            + report["message"]
        )
        context = ssl.create_default_context()
        connection = (
            smtplib.SMTP_SSL(self.host, self.port, timeout=5, context=context)
            if self.security == "ssl"
            else smtplib.SMTP(self.host, self.port, timeout=5)
        )
        try:
            if self.security == "starttls":
                connection.starttls(context=context)
            if self.username:
                connection.login(self.username, self.password)
            connection.send_message(message, from_addr=self.sender, to_addrs=[self.recipient])
        finally:
            # A disconnect after DATA acceptance must not turn success into
            # an apparent failure and invite duplicate submissions.
            connection.close()


class FeedbackHandler:
    """Bound submissions without retaining visitor identifiers or opening a database."""

    def __init__(self, delivery: Callable[[dict[str, str]], None] | None = None) -> None:
        self._delivery = delivery
        self._accepted: deque[float] = deque()
        self._lock = Lock()
        self._sending = Lock()

    def handle(self, environ: dict[str, Any]) -> WebResponse:
        method = environ.get("REQUEST_METHOD")
        if method in {"GET", "HEAD"}:
            return WebResponse.json(
                {"enabled": self._delivery is not None}, cache_control="no-store",
            )
        if method != "POST":
            return _error(
                "Use GET or POST", HTTPStatus.METHOD_NOT_ALLOWED,
                headers=[("Allow", "GET, HEAD, POST")],
            )
        if not _same_origin(environ):
            return _error("Submit from InfinityDB", HTTPStatus.FORBIDDEN)
        if environ.get("QUERY_STRING"):
            return _error("Unexpected query parameters", HTTPStatus.BAD_REQUEST)
        if environ.get("CONTENT_TYPE", "").split(";")[0].strip().lower() != "application/json":
            return _error("Use JSON", HTTPStatus.UNSUPPORTED_MEDIA_TYPE)
        try:
            length = int(environ.get("CONTENT_LENGTH", ""))
        except (TypeError, ValueError):
            return _error("Content length required", HTTPStatus.LENGTH_REQUIRED)
        if length < 1 or length > MAX_BODY:
            return _error("Report too large or empty", HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        try:
            raw = environ["wsgi.input"].read(length)
            if len(raw) != length:
                raise ValueError("Incomplete body")
            payload = json.loads(raw)
        except (KeyError, OSError, UnicodeError, ValueError, RecursionError):
            return _error("Invalid report", HTTPStatus.BAD_REQUEST)
        if not isinstance(payload, dict) or set(payload) != {
            "category", "message", "page", "website",
        }:
            return _error("Invalid report fields", HTTPStatus.BAD_REQUEST)
        category = payload["category"]
        message = payload["message"]
        page = payload["page"]
        if (
            not isinstance(category, str) or category not in CATEGORIES
            or not isinstance(message, str) or not 1 <= len(message.strip()) <= MAX_MESSAGE
            or len(message.encode("utf-16-le", errors="surrogatepass")) // 2 > MAX_MESSAGE
            or not _valid_page(page)
            or payload["website"] != ""
        ):
            return _error("Check the report fields", HTTPStatus.BAD_REQUEST)
        try:
            message.encode("utf-8")
        except UnicodeError:
            return _error("Invalid report text", HTTPStatus.BAD_REQUEST)
        if self._delivery is None:
            return _error("Reporting is unavailable", HTTPStatus.SERVICE_UNAVAILABLE)
        with self._lock:
            now = monotonic()
            while self._accepted and now - self._accepted[0] >= 60:
                self._accepted.popleft()
            if len(self._accepted) >= MAX_REPORTS_PER_MINUTE:
                return _error(
                    "Too many reports. Try again in a minute.", HTTPStatus.TOO_MANY_REQUESTS,
                    headers=[("Retry-After", "60")],
                )
            if not self._sending.acquire(blocking=False):
                return _error(
                    "Another report is being sent. Try again shortly.",
                    HTTPStatus.TOO_MANY_REQUESTS, headers=[("Retry-After", "5")],
                )
            self._accepted.append(now)
        try:
            self._delivery({
                "category": category, "message": message.strip(), "page": page,
                "version": __display_version__,
            })
        except (OSError, smtplib.SMTPException, ValueError):
            # SMTP exceptions may contain credentials, addresses or message
            # content. Log only the fact of failure.
            LOGGER.warning("Feedback email delivery failed")
            return _error("Could not send report", HTTPStatus.SERVICE_UNAVAILABLE)
        finally:
            self._sending.release()
        return WebResponse.json(
            {"accepted": True}, status=HTTPStatus.ACCEPTED, cache_control="no-store",
        )
