"""Small WSGI application composing API, browser presentation, and HTTP dispatch."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Mapping
from hashlib import file_digest, sha256
from http import HTTPStatus
from pathlib import Path
from time import perf_counter
from typing import Any

from infinity_db import __display_version__, __version__
from infinity_db.database import Database
from infinity_db.publication_registry import PublicationRegistry
from infinity_db.rules_database import RulesDatabase
from infinity_db.snapshot_revision import database_set_snapshot_revision
from infinity_db.symbol_catalog import SymbolCatalog
from infinity_db.variant_usage_reference import load_runtime_variant_usage
from infinity_db.weapon_profile_publication import load_runtime_weapon_profile_publication
from infinity_db.web.api_handler import ApiHandler
from infinity_db.web.metrics import RequestMetrics
from infinity_db.web.presentation import ASSETS, PresentationHandler, static_asset_revision
from infinity_db.web.response import WebResponse
from infinity_db.web.routes import metric_route

LOGGER = logging.getLogger(__name__)
_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; object-src 'none'; "
    "base-uri 'none'; frame-ancestors 'none'"
)


def _snapshot_revision(path: Path) -> str:
    """Return a stable identifier for an immutable runtime artifact."""

    with path.open("rb") as database:
        return file_digest(database, "sha256").hexdigest()


def _etag_matches(header: str | None, etag: str) -> bool:
    """Use HTTP's weak comparison rules for an If-None-Match request header."""

    if not header:
        return False
    for candidate in header.split(","):
        candidate = candidate.strip()
        if candidate == "*":
            return True
        if candidate.startswith(("W/", "w/")):
            candidate = candidate[2:].lstrip()
        if candidate == etag:
            return True
    return False


class Application:
    """Top-level WSGI dispatch and observability around focused route handlers."""

    def __init__(
        self, database_path: Path, rules_database_path: Path | None = None,
        *, runtime_fingerprints: dict[str, str] | None = None,
        season_databases: Mapping[str, Path] | None = None,
    ) -> None:
        self.database = Database(database_path)
        self.database.validate()
        self.rules_database: RulesDatabase | None = None
        candidate_rules_path = rules_database_path or Path(database_path).with_name("rules_n5.db")
        if rules_database_path is not None:
            rules_database = RulesDatabase(candidate_rules_path)
            rules_database.validate()
            self.rules_database = rules_database
        elif candidate_rules_path.is_file():
            try:
                rules_database = RulesDatabase(candidate_rules_path)
                rules_database.validate()
                self.rules_database = rules_database
            except (OSError, ValueError, sqlite3.Error):
                LOGGER.warning("Ignoring invalid rules database: %s", candidate_rules_path)

        if season_databases and self.rules_database is None:
            raise ValueError("ITS season registration requires a validated N5 Rules database")
        self.publication_registry = (
            PublicationRegistry(self.rules_database, season_databases)
            if season_databases and self.rules_database is not None else None
        )

        self.source_data_changed_on = self.database.source_data_changed_on()
        self.snapshot_downloaded_on = self.database.snapshot_downloaded_on()
        rules_revision = (
            _snapshot_revision(self.rules_database.path)
            if self.rules_database is not None
            else None
        )
        self.variant_usage: dict[str, Any] | None = None
        self.variant_usage_revision: str | None = None
        rules_path = self.rules_database.path if self.rules_database is not None else None
        self.deployed_objects = (
            self.rules_database.deployed_objects_payload(self.database.path)
            if self.rules_database is not None else None
        )
        self.variant_usage, self.variant_usage_revision = load_runtime_variant_usage(
            self.database.path, rules_path,
        )
        self.weapon_profile_citations, _ = (
            load_runtime_weapon_profile_publication(self.database.path, rules_path)
        )
        fingerprints = {self.database.path.name: _snapshot_revision(self.database.path)}
        if rules_revision is not None:
            fingerprints[candidate_rules_path.name] = rules_revision
        if self.publication_registry is not None:
            for season_id, manifest in self.publication_registry.season_manifest().items():
                filename = f"{season_id.replace('-', '_')}.db"
                if filename in fingerprints:
                    raise ValueError(f"Duplicate runtime database filename: {filename}")
                fingerprints[filename] = manifest["sha256"]
        if runtime_fingerprints is not None and self.publication_registry is not None:
            if fingerprints != runtime_fingerprints:
                raise ValueError("Registered ITS database fingerprints differ from selected set")
        self.snapshot_revision = database_set_snapshot_revision(
            runtime_fingerprints if runtime_fingerprints is not None else fingerprints
        )
        symbols = SymbolCatalog(publication=self.database.symbol_publication())
        static_revision = static_asset_revision(symbols)
        self.presentation = PresentationHandler(
            source_data_changed_on=self.source_data_changed_on,
            snapshot_downloaded_on=self.snapshot_downloaded_on,
            snapshot_revision=self.snapshot_revision,
            static_revision=static_revision,
        )
        self.api = ApiHandler(
            self.database,
            self.rules_database,
            static_revision=static_revision,
            symbol_catalog=symbols,
            snapshot_revision=self.snapshot_revision,
            deployed_objects=self.deployed_objects,
            variant_usage=self.variant_usage,
            variant_usage_revision=self.variant_usage_revision,
            weapon_profile_citations=self.weapon_profile_citations,
            publication_registry=self.publication_registry,
        )
        # Preserve the existing Application service attributes while request ownership moves
        # behind the API handler. They remain internal compatibility aliases, not dispatch logic.
        self.trait_catalog = self.api.trait_catalog
        self.state_catalog = self.api.state_catalog
        self.skill_catalog = self.api.skill_catalog
        self.equipment_catalog = self.api.equipment_catalog
        self.hacking_program_catalog = self.api.hacking_program_catalog
        self.search_catalog = self.api.search_catalog
        self.catalog_rules = self.api.catalog_rules
        self.scenario_catalog = self.api.scenario_catalog
        self.symbol_catalog = self.api.symbol_catalog
        self.fireteam_rules_reference = self.api.fireteam_rules_reference
        self.request_metrics = RequestMetrics()

    def _snapshot_etag(self, path: str, query: str) -> str:
        """Return a snapshot validator scoped to one requested representation."""

        representation = sha256(f"{path}?{query}".encode()).hexdigest()[:16]
        return f'"{__version__}-{self.snapshot_revision}-{representation}"'

    def __call__(self, environ: dict, start_response):
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")

        internal_response = self._internal_response(path, method)
        if internal_response is not None:
            return self._send_internal_response(internal_response, method, start_response)

        route = metric_route(path, ASSETS)
        started = perf_counter()
        response_status = HTTPStatus.INTERNAL_SERVER_ERROR.value
        response_size = 0
        worker_slot = self.request_metrics.start_request()

        def instrumented_start_response(status: str, headers, exc_info=None):
            nonlocal response_status, response_size
            response_status = int(status.split()[0])
            if method != "HEAD":
                for name, value in headers:
                    if name.lower() == "content-length":
                        response_size = int(value)
                        break
            return start_response(status, headers, exc_info)

        try:
            result = self._serve_request(environ, instrumented_start_response)
        except BaseException:
            self.request_metrics.finish_request(
                worker_slot,
                route,
                HTTPStatus.INTERNAL_SERVER_ERROR.value,
                perf_counter() - started,
                0,
            )
            raise
        self.request_metrics.finish_request(
            worker_slot, route, response_status, perf_counter() - started, response_size
        )
        return result

    def _internal_response(self, path: str, method: str) -> WebResponse | None:
        if path not in {"/internal/metrics", "/internal/health"}:
            return None
        if method not in {"GET", "HEAD"}:
            return WebResponse(
                status=HTTPStatus.METHOD_NOT_ALLOWED,
                body=b"method not allowed\n",
                content_type="text/plain; charset=utf-8",
                cache_control="no-store",
                headers=[("Allow", "GET, HEAD")],
            )
        if path == "/internal/metrics":
            return WebResponse(
                body=self.request_metrics.render_prometheus(
                    version=__display_version__, snapshot_revision=self.snapshot_revision
                ),
                content_type="text/plain; version=0.0.4; charset=utf-8",
                cache_control="no-store",
            )
        try:
            self.api.validate_health()
        except (OSError, ValueError, sqlite3.Error):
            return WebResponse(
                status=HTTPStatus.SERVICE_UNAVAILABLE,
                body=b"unavailable\n",
                content_type="text/plain; charset=utf-8",
                cache_control="no-store",
            )
        return WebResponse(
            body=b"ok\n",
            content_type="text/plain; charset=utf-8",
            cache_control="no-store",
        )

    @staticmethod
    def _send_internal_response(response: WebResponse, method: str, start_response):
        headers = [
            ("Content-Type", response.content_type),
            ("Content-Length", str(len(response.body))),
            ("Cache-Control", response.cache_control),
            ("X-Content-Type-Options", "nosniff"),
            *response.headers,
        ]
        start_response(f"{response.status.value} {response.status.phrase}", headers)
        return [] if method == "HEAD" else [response.body]

    def _dispatch(self, method: str, path: str, query: str) -> WebResponse:
        if method not in {"GET", "HEAD"}:
            return WebResponse.json(
                {"error": "Use GET or HEAD for this resource"},
                status=HTTPStatus.METHOD_NOT_ALLOWED,
                headers=[("Allow", "GET, HEAD")],
            )

        response = self.presentation.handle(path, query)
        if response is not None:
            return response
        response = self.api.handle(path, query)
        if response is not None:
            return response
        return WebResponse.json({"error": "Resource not found"}, status=HTTPStatus.NOT_FOUND)

    def _serve_request(self, environ: dict, start_response):
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")
        query = environ.get("QUERY_STRING", "")
        response = self._dispatch(method, path, query)

        etag = (
            self._snapshot_etag(path, query)
            if path.startswith("/api/") and response.status == HTTPStatus.OK
            else None
        )
        if etag and path == "/api/variant-usage" and self.api.variant_usage_revision:
            representation = sha256(f"{path}?{query}".encode()).hexdigest()[:16]
            etag = (
                f'"{__version__}-{self.snapshot_revision}-'
                f'{self.api.variant_usage_revision}-{representation}"'
            )
        status = response.status
        body = response.body
        if etag and _etag_matches(environ.get("HTTP_IF_NONE_MATCH"), etag):
            status = HTTPStatus.NOT_MODIFIED
            body = b""

        headers = [
            ("Cache-Control", response.cache_control),
            ("X-Content-Type-Options", "nosniff"),
            ("Content-Security-Policy", _CONTENT_SECURITY_POLICY),
            *([("ETag", etag)] if etag else []),
            *response.headers,
        ]
        if status != HTTPStatus.NOT_MODIFIED:
            headers[:0] = [
                ("Content-Type", response.content_type),
                ("Content-Length", str(len(body))),
            ]
        start_response(f"{status.value} {status.phrase}", headers)
        return [] if method == "HEAD" else [body]


def create_app(
    database_path: Path, rules_database_path: Path | None = None,
    *, season_databases: Mapping[str, Path] | None = None,
) -> Application:
    """Create the app with optionally registered, explicitly selected ITS files."""

    return Application(
        database_path, rules_database_path, season_databases=season_databases,
    )


def create_app_from_database_set(directory: Path) -> Application:
    """Open exactly one complete embedded set after shared, read-only validation."""
    from infinity_db.database_set import (
        ARMY_DATABASE_FILENAME,
        RULES_DATABASE_FILENAME,
        SEASON_DATABASE_SOURCES,
        validate_database_set,
    )

    selected = Path(directory).resolve()
    report = validate_database_set(selected, require_complete=True)
    return Application(
        selected / ARMY_DATABASE_FILENAME, selected / RULES_DATABASE_FILENAME,
        runtime_fingerprints=report["sha256"],
        season_databases={
            season: selected / filename
            for season, (filename, _source) in SEASON_DATABASE_SOURCES.items()
        },
    )
