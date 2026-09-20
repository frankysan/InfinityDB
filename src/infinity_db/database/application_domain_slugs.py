"""Materialize application-owned domain-local slug candidates."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from infinity_db.domain_slugs import (
    APPLICATION_SLUG_DOMAINS,
    DOMAIN_SLUG_STATUSES,
    resolve_domain_slug_candidates,
)


@dataclass(frozen=True)
class ApplicationDomainSlugModel:
    """Provisional domain-local slug rows for current application identities."""

    rows: tuple[dict[str, Any], ...]


def _rows(connection: sqlite3.Connection, statement: str, *parameters: Any) -> list[dict[str, Any]]:
    cursor = connection.execute(statement, parameters)
    columns = tuple(column[0] for column in cursor.description or ())
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _domain_seeds(connection: sqlite3.Connection, domain: str) -> list[tuple[int, object]]:
    if domain == "armies":
        rows = _rows(
            connection,
            "SELECT id, COALESCE(NULLIF(slug, ''), name) AS seed "
            "FROM application_armies ORDER BY id",
        )
    elif domain == "units":
        rows = _rows(
            connection,
            "SELECT id, COALESCE(NULLIF(slug, ''), NULLIF(isc, ''), name) AS seed "
            "FROM logical_units ORDER BY id",
        )
    elif domain in {"skills", "equipment", "weapons"}:
        rows = _rows(
            connection,
            "SELECT id, name AS seed FROM application_catalog_items "
            "WHERE catalog = ? ORDER BY id",
            domain,
        )
    else:
        raise ValueError(f"Unknown slug domain: {domain}")
    return [(int(row["id"]), row["seed"]) for row in rows]


def derive_application_domain_slugs(
    connection: sqlite3.Connection,
) -> ApplicationDomainSlugModel:
    """Derive provisional slug state for supported application domains."""

    result: list[dict[str, Any]] = []
    for domain in APPLICATION_SLUG_DOMAINS:
        seeds = _domain_seeds(connection, domain)
        resolutions = resolve_domain_slug_candidates(seeds, domain=domain)
        result.extend(
            {
                "domain": domain,
                "application_id": application_id,
                "candidate_slug": resolutions[application_id].candidate_slug,
                "slug": resolutions[application_id].slug,
                "status": resolutions[application_id].status,
            }
            for application_id, _ in seeds
        )
    return ApplicationDomainSlugModel(
        rows=tuple(sorted(result, key=lambda row: (row["domain"], row["application_id"])))
    )


def materialize_application_domain_slugs(
    connection: sqlite3.Connection,
) -> ApplicationDomainSlugModel:
    """Populate the application domain-slug registry."""

    model = derive_application_domain_slugs(connection)
    connection.executemany(
        "INSERT INTO application_domain_slugs "
        "(domain, application_id, candidate_slug, slug, status) "
        "VALUES (:domain, :application_id, :candidate_slug, :slug, :status)",
        model.rows,
    )
    return model


def validate_application_domain_slugs(connection: sqlite3.Connection) -> None:
    """Verify the persisted registry matches current application identities."""

    expected = derive_application_domain_slugs(connection).rows
    actual = tuple(
        _rows(
            connection,
            "SELECT domain, application_id, candidate_slug, slug, status "
            "FROM application_domain_slugs ORDER BY domain, application_id",
        )
    )
    if actual != expected:
        raise ValueError("Database has invalid application domain slugs; rebuild the database")

    invalid = [row for row in actual if row["status"] not in DOMAIN_SLUG_STATUSES]
    if invalid:
        raise ValueError("Database has unknown application domain-slug status")
