"""Helpers for additive public identifiers on application-domain references."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from infinity_db.application_domains import (
    public_rule_record_domain,
    semantic_record_domain,
)
from infinity_db.domain_slugs import (
    route_slug_from_qualified_typed_domain_id,
    route_slug_from_typed_domain_id,
)

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
    database: Database | None,
    record: dict[str, Any],
) -> dict[str, str] | None:
    """Return the player-facing reference for one rules-relation endpoint.

    Route-backed domains use their normal catalog/detail URL contract. Embedded
    vocabularies intentionally have no detail route, so their canonical public
    destination is the corresponding Glossary entry.
    """

    kind = record.get("kind")
    if not isinstance(kind, str):
        return None
    domain = public_rule_record_domain(record)
    if domain is None:
        semantic_domain = semantic_record_domain(kind)
        if (
            semantic_domain is None
            or semantic_domain.level != "embedded"
            or not semantic_domain.glossary
        ):
            return None
        record_id = record.get("id")
        try:
            route_id = route_slug_from_typed_domain_id(
                record_id,
                expected_domain=kind,
                context=f"curated {semantic_domain.singular_name.lower()} id",
            )
        except ValueError:
            return None
        return {"href": f"/glossary#{kind}-{route_id}"}
    catalog = domain.slug
    typed_prefix = kind

    if kind in {"skill", "equipment", "weapon"}:
        entity = kind
        army_links = [
            link
            for link in record.get("army_links", [])
            if link.get("entity") == entity
        ]
        # A family shared by several Army Weapons needs a link to the rule
        # card, not just to the first Weapon's profile table. Until there is
        # a dedicated family route, the first linked Weapon hosts that card.
        shared_weapon_family = (
            kind == "weapon"
            and (record.get("variant_semantics") or {}).get("inheritance") == "family"
            and len({link.get("id") for link in army_links}) > 1
            and isinstance(record.get("id"), str)
        )
        has_army_link = bool(army_links)
        for link in army_links:
            raw_ref = link.get("id")
            if not isinstance(raw_ref, str) or not raw_ref:
                continue
            if raw_ref.isdigit():
                if database is None:
                    continue
                slug = public_slug_for_reference(database, catalog, int(raw_ref))
                if slug is None:
                    continue
            else:
                slug = raw_ref
            if shared_weapon_family:
                fragment = record["id"].replace(":", "-")
                return {"href": f"/{catalog}/{quote(slug, safe='')}#rule-{fragment}"}
            return {"catalog": catalog, "id": slug}

        if has_army_link or kind != "skill":
            return None

    record_id = record.get("id")
    try:
        slugger = (
            route_slug_from_qualified_typed_domain_id
            if domain.record_categories
            else route_slug_from_typed_domain_id
        )
        route_id = slugger(
            record_id,
            expected_domain=typed_prefix,
            context=f"curated {domain.singular_name.lower()} id",
        )
    except ValueError:
        return None
    return {"catalog": catalog, "id": route_id}


def local_rule_public_reference(
    record_id: object, local_rule_ids: frozenset[str]
) -> dict[str, str] | None:
    """Link to an existing rule card in the current detail page, when supplied."""

    if isinstance(record_id, str) and record_id in local_rule_ids:
        return {"href": f"#rule-{record_id.replace(':', '-')}"}
    return None


def enrich_rule_relation_references(
    database: Database,
    value: dict[str, Any],
    *,
    local_rule_ids: frozenset[str] = frozenset(),
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
                    reference = local_rule_public_reference(
                        record.get("id"), local_rule_ids
                    ) or rule_record_public_reference(database, record)
                    if reference is not None:
                        record["public_reference"] = reference
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(result)
    return result
