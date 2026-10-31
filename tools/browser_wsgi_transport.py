"""Serve Playwright browser requests through the WSGI application during tests."""

from __future__ import annotations

from collections.abc import Callable
from io import BytesIO
from typing import Any
from urllib.parse import unquote, urlsplit
from wsgiref.util import setup_testing_defaults


def wsgi_response(
    app: Callable[..., Any],
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
) -> tuple[int, list[tuple[str, str]], bytes]:
    parts = urlsplit(url)
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ["REQUEST_METHOD"] = method
    environ["PATH_INFO"] = unquote(parts.path) or "/"
    environ["QUERY_STRING"] = parts.query
    environ["SERVER_NAME"] = parts.hostname or "localhost"
    environ["SERVER_PORT"] = str(parts.port or 80)
    environ["wsgi.url_scheme"] = parts.scheme
    environ["wsgi.input"] = BytesIO()
    for key, value in (headers or {}).items():
        name = key.upper().replace("-", "_")
        environ[name if name in {"CONTENT_TYPE", "CONTENT_LENGTH"} else f"HTTP_{name}"] = value
    output: dict[str, Any] = {}

    def start_response(
        status: str, response_headers: list[tuple[str, str]], exc_info: Any = None,
    ) -> None:
        output["status"] = int(status.split()[0])
        output["headers"] = response_headers

    return_body = app(environ, start_response)
    try:
        body = b"".join(return_body)
    finally:
        if hasattr(return_body, "close"):
            return_body.close()
    return output["status"], output["headers"], body


def route_browser_page(page: Any, app: Callable[..., Any], origin: str) -> None:
    host = urlsplit(origin).netloc

    def respond(route: Any) -> None:
        request = route.request
        if urlsplit(request.url).netloc != host:
            route.continue_()
            return
        status, headers, body = wsgi_response(app, request.url, request.method, request.headers)
        route.fulfill(status=status, headers=dict(headers), body=body)

    page.route("**/*", respond)
