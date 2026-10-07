"""Canonical application-domain capabilities and public presentation contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DomainLevel = Literal["top-level", "embedded"]
DomainPresentation = Literal["catalog", "overview", "explorer", "scoped", "embedded"]


@dataclass(frozen=True, slots=True)
class ApplicationDomain:
    """Describe semantic ownership separately from player-facing presentation."""

    slug: str
    singular_name: str
    plural_name: str
    level: DomainLevel
    presentation: DomainPresentation
    record_kinds: tuple[str, ...] = ()
    record_categories: tuple[str, ...] = ()
    navigation: bool = False
    search: bool = False
    glossary: bool = False
    landing: bool = False
    catalog: bool = False
    detail: bool = False
    scoped: bool = False
    published: bool = False

    @property
    def route(self) -> str | None:
        """Return the canonical landing route when this domain has one."""

        return f"/{self.slug}" if self.landing and self.published else None


APPLICATION_DOMAINS: tuple[ApplicationDomain, ...] = (
    ApplicationDomain(
        "armies",
        "Army",
        "Armies",
        "top-level",
        "overview",
        navigation=True,
        search=True,
        landing=True,
        published=True,
    ),
    ApplicationDomain(
        "units",
        "Unit",
        "Units",
        "top-level",
        "explorer",
        navigation=True,
        search=True,
        landing=True,
        detail=True,
        published=True,
    ),
    ApplicationDomain(
        "skills",
        "Skill",
        "Skills",
        "top-level",
        "catalog",
        record_kinds=("skill",),
        navigation=True,
        search=True,
        glossary=True,
        landing=True,
        catalog=True,
        detail=True,
        published=True,
    ),
    ApplicationDomain(
        "equipment",
        "Equipment",
        "Equipment",
        "top-level",
        "catalog",
        record_kinds=("equipment",),
        navigation=True,
        search=True,
        glossary=True,
        landing=True,
        catalog=True,
        detail=True,
        published=True,
    ),
    ApplicationDomain(
        "weapons",
        "Weapon",
        "Weapons",
        "top-level",
        "catalog",
        record_kinds=("weapon",),
        navigation=True,
        search=True,
        glossary=True,
        landing=True,
        catalog=True,
        detail=True,
        published=True,
    ),
    ApplicationDomain(
        "ammunition",
        "Ammunition type",
        "Ammunition",
        "top-level",
        "catalog",
        record_kinds=("ammunition",),
        navigation=True,
        search=True,
        glossary=True,
        landing=True,
        catalog=True,
        detail=True,
        published=True,
    ),
    ApplicationDomain(
        "traits",
        "Trait",
        "Traits",
        "top-level",
        "catalog",
        record_kinds=("trait",),
        navigation=True,
        search=True,
        glossary=True,
        landing=True,
        catalog=True,
        detail=True,
        published=True,
    ),
    ApplicationDomain(
        "states",
        "State",
        "States",
        "top-level",
        "catalog",
        record_kinds=("state",),
        navigation=True,
        search=True,
        glossary=True,
        landing=True,
        catalog=True,
        detail=True,
        published=True,
    ),
    ApplicationDomain(
        "hacking-programs",
        "Hacking Program",
        "Hacking Programs",
        "top-level",
        "catalog",
        record_kinds=("hacking-program",),
        navigation=True,
        search=True,
        glossary=True,
        landing=True,
        catalog=True,
        detail=True,
        published=True,
    ),
    ApplicationDomain(
        "fireteams",
        "Fireteam reference",
        "Fireteams",
        "top-level",
        "scoped",
        navigation=True,
        search=True,
        glossary=True,
        landing=True,
        scoped=True,
        published=True,
    ),
    ApplicationDomain(
        "labels",
        "Label",
        "Labels",
        "top-level",
        "catalog",
        navigation=True,
        search=True,
        glossary=True,
        landing=True,
        catalog=True,
        detail=True,
        published=True,
    ),
    ApplicationDomain(
        "scenarios",
        "Scenario",
        "Scenarios",
        "top-level",
        "catalog",
        record_kinds=("scenario",),
        navigation=True,
        landing=True,
        catalog=True,
        detail=True,
        published=True,
    ),
    ApplicationDomain(
        "rules",
        "General rule",
        "General Rules",
        "top-level",
        "catalog",
        record_kinds=("rule",),
        record_categories=(
            "basic-rule",
            "command-token-use",
            "order-type",
            "peripheral-type",
        ),
        navigation=True,
        search=True,
        glossary=True,
        landing=True,
        catalog=True,
        detail=True,
        published=True,
    ),
    ApplicationDomain(
        "attributes",
        "Attribute",
        "Attributes",
        "embedded",
        "embedded",
        record_kinds=("attribute",),
        search=True,
        glossary=True,
        published=True,
    ),
    ApplicationDomain(
        "terms",
        "Game term",
        "Game terms",
        "embedded",
        "embedded",
        record_kinds=("term",),
        search=True,
        glossary=True,
        published=True,
    ),
)

_APPLICATION_DOMAINS_BY_SLUG = {domain.slug: domain for domain in APPLICATION_DOMAINS}
_RULE_RECORD_DOMAINS = {
    kind: domain
    for domain in APPLICATION_DOMAINS
    if domain.published and domain.detail and not domain.record_categories
    for kind in domain.record_kinds
}
_SEMANTIC_RECORD_DOMAINS = {
    kind: domain
    for domain in APPLICATION_DOMAINS
    if domain.published and not domain.record_categories
    for kind in domain.record_kinds
}


def application_domain(slug: str) -> ApplicationDomain:
    """Return one canonical application-domain definition."""

    try:
        return _APPLICATION_DOMAINS_BY_SLUG[slug]
    except KeyError as exc:
        raise ValueError(f"Unknown application domain {slug!r}") from exc


def public_rule_domain(kind: str) -> ApplicationDomain | None:
    """Return the published detail domain owning one unambiguous rules kind."""

    return _RULE_RECORD_DOMAINS.get(kind)


def semantic_record_domain(kind: str) -> ApplicationDomain | None:
    """Return the published semantic owner of one rules-record kind.

    Unlike :func:`public_rule_domain`, embedded vocabularies are included even
    when they intentionally have no detail route of their own.
    """

    return _SEMANTIC_RECORD_DOMAINS.get(kind)


def record_matches_domain(domain: ApplicationDomain, record: dict[str, object]) -> bool:
    """Return whether one semantic rules record belongs to an application domain.

    Most domains own a complete record kind. General Rules is intentionally the
    fallback exception: only reviewed ``rule`` categories without a clearer
    application owner are published there.
    """

    kind = record.get("kind")
    if kind not in domain.record_kinds:
        return False
    if not domain.record_categories:
        return True
    facts = record.get("facts")
    if not isinstance(facts, dict):
        return False
    category = facts.get("category")
    return isinstance(category, str) and category in domain.record_categories


def public_rule_record_domain(record: dict[str, object]) -> ApplicationDomain | None:
    """Return the published detail domain owning one concrete rules record.

    This record-aware resolver handles category-scoped domains such as General
    Rules while :func:`public_rule_domain` remains reserved for kinds that map
    unambiguously to one public catalog.
    """

    for domain in APPLICATION_DOMAINS:
        if not domain.published or not domain.detail:
            continue
        if record_matches_domain(domain, record):
            return domain
    return None
