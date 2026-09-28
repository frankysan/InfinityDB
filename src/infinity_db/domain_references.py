"""Helpers for additive public identifiers on application-domain references."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

from infinity_db.application_domains import public_rule_domain

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


def rule_record_public_reference(
    database: Database,
    record: dict[str, Any],
) -> dict[str, str] | None:
    """Return a routable catalog reference for one rules-relation endpoint."""

    kind = record.get("kind")
    if not isinstance(kind, str):
        return None
    domain = public_rule_domain(kind)
    if domain is None:
        return None
    catalog = domain.slug
    typed_prefix = kind

    if kind in {"skill", "equipment", "weapon"}:
        entity = kind
        has_army_link = False
        for link in record.get("army_links", []):
            if link.get("entity") != entity:
                continue
            has_army_link = True
            raw_ref = link.get("id")
            if not isinstance(raw_ref, str) or not raw_ref:
                continue
            if raw_ref.isdigit():
                slug = public_slug_for_reference(database, catalog, int(raw_ref))
                if slug is None:
                    continue
                return {"catalog": catalog, "id": slug}
            return {"catalog": catalog, "id": raw_ref}

        if has_army_link or kind != "skill":
            return None

    record_id = record.get("id")
    prefix = f"{typed_prefix}:"
    if isinstance(record_id, str) and record_id.startswith(prefix):
        route_id = record_id[len(prefix):]
        if route_id:
            return {"catalog": catalog, "id": route_id}
    return None


def enrich_rule_relation_references(
    database: Database,
    value: dict[str, Any],
) -> dict[str, Any]:
    """Attach browser-routable references to structured rules relations.

    Numeric Army source IDs are projected through the current application catalog
    before publication so stale source-only variants do not become dead browser links.
    Rules-owned Trait, State, Hacking Program, and rules-only Skill identities retain
    their typed semantic ID as the route source.
    """

    result = deepcopy(value)

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            relations = node.get("display_relations")
            if isinstance(relations, list):
                for relation in relations:
                    if not isinstance(relation, dict):
                        continue
                    record = relation.get("record")
                    if not isinstance(record, dict):
                        continue
                    reference = rule_record_public_reference(database, record)
                    if reference is not None:
                        record["public_reference"] = reference
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(result)
    return result
