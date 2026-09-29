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
        "rules",
        "General rule",
        "General Rules",
        "top-level",
        "catalog",
        navigation=False,
        search=True,
        glossary=True,
        landing=True,
        catalog=True,
        detail=True,
        published=False,
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
)

_APPLICATION_DOMAINS_BY_SLUG = {domain.slug: domain for domain in APPLICATION_DOMAINS}
_RULE_RECORD_DOMAINS = {
    kind: domain
    for domain in APPLICATION_DOMAINS
    if domain.published and domain.detail
    for kind in domain.record_kinds
}
_SEMANTIC_RECORD_DOMAINS = {
    kind: domain
    for domain in APPLICATION_DOMAINS
    if domain.published
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
