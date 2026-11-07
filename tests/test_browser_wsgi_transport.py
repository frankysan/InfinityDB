"""Regression checks for direct WSGI responses in Chromium page routing."""

from __future__ import annotations

from typing import Any

from tools.browser_wsgi_transport import route_browser_page, wsgi_response


def _app(environ: dict[str, Any], start_response: Any) -> list[bytes]:
    path = environ["PATH_INFO"]
    if path == "/missing":
        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"missing"]
    start_response("200 OK", [
        ("Content-Type", "text/plain"),
        ("X-Request-Method", environ["REQUEST_METHOD"]),
    ])
    return [f"{path}?{environ['QUERY_STRING']}".encode()]


def test_wsgi_response_preserves_path_query_method_and_status() -> None:
    status, headers, body = wsgi_response(_app, "http://127.0.0.1:8080/static/site.js?v=3")
    assert status == 200
    assert dict(headers)["Content-Type"] == "text/plain"
    assert body == b"/static/site.js?v=3"
    status, headers, body = wsgi_response(_app, "http://127.0.0.1:8080/missing", "HEAD")
    assert status == 404
    assert body == b"missing"


def test_page_routing_handles_same_origin_and_preserves_external_requests() -> None:
    class Request:
        def __init__(self, url: str) -> None:
            self.url = url
            self.method = "GET"
            self.headers: dict[str, str] = {}

    class Route:
        def __init__(self, url: str) -> None:
            self.request = Request(url)
            self.handled: tuple[int, bytes] | None = None
            self.continued = False

        def fulfill(self, *, status: int, headers: dict[str, str], body: bytes) -> None:
            assert headers["Content-Type"] == "text/plain"
            self.handled = (status, body)

        def continue_(self) -> None:
            self.continued = True

    class Page:
        def route(self, pattern: str, callback: Any) -> None:
            assert pattern == "**/*"
            self.callback = callback

    page = Page()
    route_browser_page(page, _app, "http://127.0.0.1:8080")
    internal = Route("http://127.0.0.1:8080/api/units?limit=1")
    page.callback(internal)
    assert internal.handled == (200, b"/api/units?limit=1")
    external = Route("https://example.org/api/units")
    page.callback(external)
    assert external.continued
    assert external.handled is None
