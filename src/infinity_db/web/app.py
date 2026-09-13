"""Small WSGI application serving the unit API and bundled browser assets."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from datetime import date
from html import escape
from http import HTTPStatus
from importlib.resources import files
from pathlib import Path
from urllib.parse import parse_qs

from infinity_db import __display_version__, __version__
from infinity_db.database import Database

LOGGER = logging.getLogger(__name__)
ASSETS = {
    "/static/version-check.js": ("version-check.js", "text/javascript; charset=utf-8"),
    "/static/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/static/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/static/api.js": ("api.js", "text/javascript; charset=utf-8"),
    "/static/army-symbols.js": ("army-symbols.js", "text/javascript; charset=utf-8"),
    "/static/unit-symbols.js": ("unit-symbols.js", "text/javascript; charset=utf-8"),
    "/static/unit-symbol-map.js": ("unit-symbol-map.js", "text/javascript; charset=utf-8"),
    "/static/unit.js": ("unit.js", "text/javascript; charset=utf-8"),
    "/static/preferences.js": ("preferences.js", "text/javascript; charset=utf-8"),
    "/static/navigation.js": ("navigation.js", "text/javascript; charset=utf-8"),
    "/static/themed-logo.js": ("themed-logo.js", "text/javascript; charset=utf-8"),
    "/static/about.js": ("about.js", "text/javascript; charset=utf-8"),
    "/static/skill-extras.js": ("skill-extras.js", "text/javascript; charset=utf-8"),
    "/static/catalog-list.js": ("catalog-list.js", "text/javascript; charset=utf-8"),
    "/static/skill.js": ("skill.js", "text/javascript; charset=utf-8"),
    "/static/unit-list.js": ("unit-list.js", "text/javascript; charset=utf-8"),
    "/static/catalog-detail.js": ("catalog-detail.js", "text/javascript; charset=utf-8"),
    "/static/infinitydb-logo.svg": ("infinitydb-logo.svg", "image/svg+xml"),
}
ARMY_SYMBOL_PATH = re.compile(r"/static/armies/[a-z0-9-]+/[a-z0-9-]+\.svg")
UNIT_SYMBOL_PATH = re.compile(r"/static/units/[a-z0-9-]+/[a-z0-9-]+\.svg")
ORDER_SYMBOL_PATH = re.compile(
    r"/static/orders/(regular|irregular|peripheral|impetuous|tactical|lieutenant|hackable|cube|cube-2)\.svg"
)
STATIC_URL = re.compile(r'\b(?:src|href)=(?P<quote>["\'])(?P<path>/static/[^"\']+)(?P=quote)')


def _version_static_urls(document: str) -> str:
    """Give page assets a new URL for each application release."""

    return STATIC_URL.sub(
        lambda match: f'{match.group(0)[:-1]}?v={__version__}{match.group("quote")}', document
    )


def _page(
    filename: str,
    *,
    active_page: str | None = None,
    snapshot_downloaded_on: date | None = None,
    breadcrumbs: tuple[tuple[str, str | None], ...],
    catalog_tag: str,
) -> bytes:
    """Render a page with the project-wide navigation and page shell."""
    static = files("infinity_db.web").joinpath("static")
    navigation = static.joinpath("navigation.html").read_text(encoding="utf-8")
    navigation = (
        navigation.replace(
            "{{UNIT_EXPLORER_CURRENT}}",
            ' aria-current="page"' if active_page == "units" else "",
        )
        .replace(
            "{{SKILLS_CURRENT}}",
            ' aria-current="page"' if active_page == "skills" else "",
        )
        .replace(
            "{{EQUIPMENT_CURRENT}}",
            ' aria-current="page"' if active_page == "equipment" else "",
        )
        .replace(
            "{{WEAPONS_CURRENT}}",
            ' aria-current="page"' if active_page == "weapons" else "",
        )
        .replace(
            "{{SKILL_EXTRAS_CURRENT}}",
            ' aria-current="page"' if active_page == "skill-extras" else "",
        )
        .replace(
            "{{ABOUT_CURRENT}}",
            ' aria-current="page"' if active_page == "about" else "",
        )
        .replace(
            "{{SNAPSHOT_DOWNLOAD_DATE}}",
            (
                '<p class="snapshot-date">Army snapshot downloaded '
                f'<time datetime="{snapshot_downloaded_on.isoformat()}">'
                f"{snapshot_downloaded_on:%B} {snapshot_downloaded_on.day}, "
                f"{snapshot_downloaded_on:%Y}"
                "</time></p>"
            )
            if snapshot_downloaded_on
            else "",
        )
    )
    breadcrumb_markup = "".join(
        (
            f'<a href="{escape(href, quote=True)}">{escape(label)}</a>'
            if href
            else f"<strong>{escape(label)}</strong>"
        )
        + ('<span aria-hidden="true">/</span>' if index < len(breadcrumbs) - 1 else "")
        for index, (label, href) in enumerate(breadcrumbs)
    )
    page_header = (
        static.joinpath("page-header.html")
        .read_text(encoding="utf-8")
        .replace("{{BREADCRUMBS}}", breadcrumb_markup)
        .replace("{{CATALOG_TAG}}", escape(catalog_tag))
    )
    page_footer = (
        static.joinpath("page-footer.html")
        .read_text(encoding="utf-8")
        .replace("{{VERSION}}", escape(__display_version__))
    )
    document = static.joinpath(filename).read_text(encoding="utf-8")
    return _version_static_urls(
        document.replace('<html lang="en">', f'<html lang="en" data-app-version="{__version__}">')
        .replace(
            "</head>", '<script type="module" src="/static/version-check.js"></script></head>'
        )
        .replace("<!-- navigation -->", navigation)
        .replace("<!-- page-header -->", page_header)
        .replace("<!-- page-footer -->", page_footer)
    ).encode("utf-8")


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


def _flag(params: dict, key: str) -> bool:
    if key not in params:
        return False
    if params[key][0] not in {"0", "1"}:
        raise ValueError(f"{key} must be 0 or 1")
    return params[key][0] == "1"


def _unit_query(query: str) -> dict:
    params = parse_qs(query, keep_blank_values=True, max_num_fields=10)
    for key, values in params.items():
        if key not in {
            "army_id",
            "search",
            "limit",
            "offset",
            "mercs",
            "specops",
            "teamops",
            "reinforcement",
            "order",
        }:
            raise ValueError(f"Unknown query parameter: {key}")
        if len(values) != 1:
            raise ValueError(f"Provide {key} only once")
    search = params.get("search", [""])[0].strip()
    if len(search) > 200:
        raise ValueError("search must be at most 200 characters")
    order = params.get("order", ["asc"])[0]
    if order not in {"asc", "desc"}:
        raise ValueError("order must be asc or desc")
    return {
        "army_id": _integer(params, "army_id", None, 0, 2**63 - 1),
        "search": search,
        "limit": _integer(params, "limit", 50, 1, 200),
        "offset": _integer(params, "offset", 0, 0, 2**63 - 1),
        "mercs": _flag(params, "mercs"),
        "specops": _flag(params, "specops"),
        "teamops": _flag(params, "teamops"),
        "reinforcement": _flag(params, "reinforcement"),
        "descending": order == "desc",
    }


class Application:
    def __init__(self, database_path: Path) -> None:
        self.database = Database(database_path)
        self.database.validate()
        self.snapshot_downloaded_on = self.database.snapshot_downloaded_on()

    def __call__(self, environ: dict, start_response):
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")
        extra_headers = []
        status = HTTPStatus.OK
        content_type = "application/json; charset=utf-8"
        cache_control = "no-cache"
        payload = None
        body = b""

        if method not in {"GET", "HEAD"}:
            status = HTTPStatus.METHOD_NOT_ALLOWED
            payload = {"error": "Use GET or HEAD for this resource"}
            extra_headers.append(("Allow", "GET, HEAD"))
        elif path == "/":
            content_type = "text/html; charset=utf-8"
            body = _page(
                "index.html",
                snapshot_downloaded_on=self.snapshot_downloaded_on,
                breadcrumbs=(("InfinityDB", None), ("Home", None)),
                catalog_tag="Player reference",
            )
        elif path == "/units":
            content_type = "text/html; charset=utf-8"
            body = _page(
                "units.html",
                active_page="units",
                snapshot_downloaded_on=self.snapshot_downloaded_on,
                breadcrumbs=(("Database", "/"), ("Units", None)),
                catalog_tag="Unit catalog",
            )
        elif path in ASSETS:
            filename, content_type = ASSETS[path]
            body = files("infinity_db.web").joinpath("static", filename).read_bytes()
        elif ARMY_SYMBOL_PATH.fullmatch(path):
            filename = path.removeprefix("/static/armies/")
            asset = files("infinity_db.web").joinpath("static", "armies", filename)
            if asset.is_file():
                body = asset.read_bytes()
                content_type = "image/svg+xml"
            else:
                status = HTTPStatus.NOT_FOUND
                payload = {"error": "Resource not found"}
        elif match := ORDER_SYMBOL_PATH.fullmatch(path):
            asset = files("infinity_db.web").joinpath("static", "orders", f"{match.group(1)}.svg")
            if asset.is_file():
                body = asset.read_bytes()
                content_type = "image/svg+xml"
            else:
                status = HTTPStatus.NOT_FOUND
                payload = {"error": "Resource not found"}
        elif UNIT_SYMBOL_PATH.fullmatch(path):
            filename = path.removeprefix("/static/units/")
            asset = files("infinity_db.web").joinpath("static", "units", filename)
            if asset.is_file():
                body = asset.read_bytes()
                content_type = "image/svg+xml"
            else:
                status = HTTPStatus.NOT_FOUND
                payload = {"error": "Resource not found"}
        elif re.fullmatch(r"/units/[0-9]+", path):
            content_type = "text/html; charset=utf-8"
            body = _page(
                "unit.html",
                active_page="units",
                snapshot_downloaded_on=self.snapshot_downloaded_on,
                breadcrumbs=(("Database", "/"), ("Units", "/units"), ("Details", None)),
                catalog_tag="Unit catalog",
            )
        elif path == "/skill-extras":
            content_type = "text/html; charset=utf-8"
            body = _page(
                "skill-extras.html",
                active_page="skill-extras",
                snapshot_downloaded_on=self.snapshot_downloaded_on,
                breadcrumbs=(("Database", "/"), ("Skill modifiers", None)),
                catalog_tag="Reference data",
            )
        elif path in {"/skills", "/equipment", "/weapons"}:
            content_type = "text/html; charset=utf-8"
            catalog = path.removeprefix("/")
            body = _page(
                f"{catalog}.html",
                active_page=catalog,
                snapshot_downloaded_on=self.snapshot_downloaded_on,
                breadcrumbs=(("Database", "/"), (catalog.capitalize(), None)),
                catalog_tag="Reference data",
            )
        elif re.fullmatch(r"/skills/[0-9]+", path):
            content_type = "text/html; charset=utf-8"
            body = _page(
                "skill.html",
                active_page="skills",
                snapshot_downloaded_on=self.snapshot_downloaded_on,
                breadcrumbs=(("Database", "/"), ("Skills", "/skills"), ("Details", None)),
                catalog_tag="Reference data",
            )
        elif match := re.fullmatch(r"/(equipment|weapons)/[0-9]+", path):
            content_type = "text/html; charset=utf-8"
            body = _page(
                f"{match.group(1)}-detail.html",
                active_page=match.group(1),
                snapshot_downloaded_on=self.snapshot_downloaded_on,
                breadcrumbs=(
                    ("Database", "/"),
                    (match.group(1).capitalize(), f"/{match.group(1)}"),
                    ("Details", None),
                ),
                catalog_tag="Reference data",
            )
        elif path == "/about":
            content_type = "text/html; charset=utf-8"
            body = _page(
                "about.html",
                active_page="about",
                snapshot_downloaded_on=self.snapshot_downloaded_on,
                breadcrumbs=(("InfinityDB", "/"), ("About", None)),
                catalog_tag="Player reference",
            )
        elif path == "/api/version":
            payload = {"version": __version__}
            cache_control = "no-store"
        elif path == "/api/skill-extras":
            try:
                payload = {"items": self.database.list_skill_extras()}
            except (OSError, ValueError, sqlite3.Error):
                LOGGER.exception("Could not read skill modifiers")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The skill modifiers are unavailable. Please try again."}
        elif path in {"/api/skills", "/api/equipment", "/api/weapons"}:
            try:
                payload = {"items": self.database.list_catalog_items(path.removeprefix("/api/"))}
            except (OSError, ValueError, sqlite3.Error):
                LOGGER.exception("Could not read catalog")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The catalog is unavailable. Please try again."}
        elif match := re.fullmatch(r"/api/skills/([0-9]+)", path):
            try:
                skill_id = int(match.group(1))
                payload = self.database.get_skill(skill_id)
                if payload is None:
                    status = HTTPStatus.NOT_FOUND
                    payload = {"error": "Skill not found"}
            except ValueError as exc:
                status = HTTPStatus.BAD_REQUEST
                payload = {"error": str(exc)}
            except (OSError, sqlite3.Error):
                LOGGER.exception("Could not read skill")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The skill is unavailable. Please try again."}
        elif match := re.fullmatch(r"/api/(equipment|weapons)/([0-9]+)", path):
            try:
                payload = self.database.get_catalog_item(match.group(1), int(match.group(2)))
                if payload is None:
                    status = HTTPStatus.NOT_FOUND
                    payload = {"error": "Reference item not found"}
            except ValueError as exc:
                status = HTTPStatus.BAD_REQUEST
                payload = {"error": str(exc)}
            except (OSError, sqlite3.Error):
                LOGGER.exception("Could not read reference item")
                status = HTTPStatus.SERVICE_UNAVAILABLE
                payload = {"error": "The reference item is unavailable. Please try again."}
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
            ("Cache-Control", cache_control),
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
