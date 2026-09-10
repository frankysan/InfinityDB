"""Small WSGI application serving the unit API and bundled browser assets."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from http import HTTPStatus
from importlib.resources import files
from pathlib import Path
from urllib.parse import parse_qs

from infinity_db.database import Database

LOGGER = logging.getLogger(__name__)
ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/static/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/static/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/static/api.js": ("api.js", "text/javascript; charset=utf-8"),
    "/static/army-symbols.js": ("army-symbols.js", "text/javascript; charset=utf-8"),
    "/static/unit.js": ("unit.js", "text/javascript; charset=utf-8"),
}
ARMY_SYMBOL_PATH = re.compile(
    r"/static/army-symbols/(?:[A-Za-z0-9 ._-]+/)*[A-Za-z0-9 ._-]+\.svg"
)


def _integer(params: dict, key: str, default: int | None, low: int, high: int) -> int | None:
    if key not in params:
        return default
    raw = params[key][0]
    if len(raw) > 19 or not re.fullmatch(r"[0-9]+", raw):
        raise ValueError(f"{key} must be an integer between {low} and {high}")
    value = int(raw)
    if not low <= value <= high:
        raise ValueError(f"{key} must be between {low} and {high}")
    return value


def _unit_query(query: str) -> dict:
    params = parse_qs(query, keep_blank_values=True, max_num_fields=10)
    for key, values in params.items():
        if key not in {"army_id", "search", "limit", "offset"}:
            raise ValueError(f"Unknown query parameter: {key}")
        if len(values) != 1:
            raise ValueError(f"Provide {key} only once")
    search = params.get("search", [""])[0].strip()
    if len(search) > 200:
        raise ValueError("search must be at most 200 characters")
    return {
        "army_id": _integer(params, "army_id", None, 0, 2**63 - 1),
        "search": search,
        "limit": _integer(params, "limit", 50, 1, 200),
        "offset": _integer(params, "offset", 0, 0, 2**63 - 1),
    }


class Application:
    def __init__(self, database_path: Path) -> None:
        self.database = Database(database_path)
        self.database.validate()

    def __call__(self, environ: dict, start_response):
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")
        extra_headers = []
        status = HTTPStatus.OK
        content_type = "application/json; charset=utf-8"
        payload = None
        body = b""

        if method not in {"GET", "HEAD"}:
            status = HTTPStatus.METHOD_NOT_ALLOWED
            payload = {"error": "Use GET or HEAD for this resource"}
            extra_headers.append(("Allow", "GET, HEAD"))
        elif path in ASSETS:
            filename, content_type = ASSETS[path]
            body = files("infinity_db.web").joinpath("static", filename).read_bytes()
        elif ARMY_SYMBOL_PATH.fullmatch(path):
            filename = path.removeprefix("/static/army-symbols/")
            asset = files("infinity_db.web").joinpath("static", "army-symbols", filename)
            body = asset.read_bytes()
            content_type = "image/svg+xml"
        elif re.fullmatch(r"/units/[0-9]+", path):
            content_type = "text/html; charset=utf-8"
            body = files("infinity_db.web").joinpath("static", "unit.html").read_bytes()
        elif path == "/api/armies":
            try:
                payload = {"items": self.database.list_armies()}
            except (OSError, ValueError, sqlite3.Error):
                LOGGER.exception("Could not read armies")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The database is unavailable. Please try again."}
        elif path == "/api/units":
            try:
                query = _unit_query(environ.get("QUERY_STRING", ""))
            except ValueError as exc:
                status = HTTPStatus.BAD_REQUEST
                payload = {"error": str(exc)}
            else:
                try:
                    payload = self.database.list_units(**query)
                except (OSError, ValueError, sqlite3.Error):
                    LOGGER.exception("Could not read units")
                    status = HTTPStatus.SERVICE_UNAVAILABLE
                    payload = {"error": "The database is unavailable. Please try again."}
        elif match := re.fullmatch(r"/api/units/([0-9]+)", path):
            try:
                unit_id = int(match.group(1))
                if unit_id > 2**63 - 1:
                    raise ValueError("unit_id must be between 0 and 9223372036854775807")
                payload = self.database.get_unit(unit_id)
                if payload is None:
                    status = HTTPStatus.NOT_FOUND
                    payload = {"error": "Unit not found"}
            except ValueError as exc:
                status = HTTPStatus.BAD_REQUEST
                payload = {"error": str(exc)}
            except (OSError, sqlite3.Error):
                LOGGER.exception("Could not read unit")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The database is unavailable. Please try again."}
        else:
            status = HTTPStatus.NOT_FOUND
            payload = {"error": "Resource not found"}

        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-cache"),
            ("X-Content-Type-Options", "nosniff"),
            (
                "Content-Security-Policy",
                "default-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
            ),
            *extra_headers,
        ]
        start_response(f"{status.value} {status.phrase}", headers)
        return [] if method == "HEAD" else [body]


def create_app(database_path: Path) -> Application:
    """Create the app after verifying the database, without starting a server."""
    return Application(database_path)
