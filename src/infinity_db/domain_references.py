"""Helpers for additive public identifiers on application-domain references."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from infinity_db.database.repository import Database


def public_slug_for_reference(
    database: Database,
    domain: str,
    item_ref: int | str,
) -> str | None:
    """Return a routable public slug for one application-domain reference."""

    application_id = database.application_domain_id(domain, item_ref)
    if application_id is None:
        return None
    return database.application_slug(domain, application_id)
