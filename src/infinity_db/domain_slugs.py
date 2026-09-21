"""Stable domain-local slug primitives for application/public identities."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from infinity_army_data.identifier_refs import (
    normalize_identifier_slug,
    require_identifier_slug,
)

APPLICATION_SLUG_DOMAINS = ("armies", "units", "skills", "equipment", "weapons")
DOMAIN_SLUG_STATUSES = ("resolved", "collision", "unavailable")


@dataclass(frozen=True)
class DomainSlugResolution:
    """One provisional domain-slug resolution result."""

    candidate_slug: str | None
    slug: str | None
    status: str


def normalize_domain_slug(value: object) -> str:
    """Return a deterministic lowercase ASCII slug candidate."""

    return normalize_identifier_slug(value)


def require_domain_slug(value: object, *, context: str) -> str:
    """Validate one already-assigned domain-local slug and return it."""

    try:
        return require_identifier_slug(value, context=context)
    except ValueError as exc:
        # Public route slugs may contain digits, but never consist only of digits.
        raise ValueError(str(exc)) from exc

def resolve_domain_slug_candidates(
    rows: Iterable[tuple[Any, object]],
    *,
    domain: str,
    reject_numeric: bool = False,
) -> dict[Any, DomainSlugResolution]:
    """Resolve provisional candidates without inventing disambiguating suffixes.

    A unique non-empty candidate is ``resolved`` unless the owning domain rejects
    digit-only candidates because they would shadow its numeric compatibility
    namespace. Duplicate candidates remain visible as ``collision`` records, and
    identities with no usable candidate become ``unavailable``. Neither unresolved
    state receives a routable slug.
    """

    candidates: dict[Any, str | None] = {}
    owners: dict[str, list[Any]] = defaultdict(list)
    for key, label in rows:
        if key in candidates:
            raise ValueError(f"{domain} identity {key!r} is listed more than once")
        candidate = normalize_domain_slug(label) or None
        candidates[key] = candidate
        if candidate is not None:
            owners[candidate].append(key)

    result: dict[Any, DomainSlugResolution] = {}
    for key, candidate in candidates.items():
        if candidate is None:
            result[key] = DomainSlugResolution(None, None, "unavailable")
        elif reject_numeric and candidate.isdigit():
            result[key] = DomainSlugResolution(candidate, None, "unavailable")
        elif len(owners[candidate]) > 1:
            result[key] = DomainSlugResolution(candidate, None, "collision")
        else:
            result[key] = DomainSlugResolution(candidate, candidate, "resolved")
    return result


def assign_domain_slugs(
    rows: Iterable[tuple[Any, object]], *, domain: str
) -> dict[Any, str]:
    """Assign slugs only when every candidate is uniquely resolvable."""

    resolutions = resolve_domain_slug_candidates(rows, domain=domain)
    result: dict[Any, str] = {}
    for key, resolution in resolutions.items():
        if resolution.status == "unavailable":
            raise ValueError(f"{domain} identity {key!r} has no usable slug candidate")
        if resolution.status == "collision":
            assert resolution.candidate_slug is not None
            colliding = [
                other_key
                for other_key, other_resolution in resolutions.items()
                if other_resolution.candidate_slug == resolution.candidate_slug
            ]
            raise ValueError(
                f"{domain} slug collision {resolution.candidate_slug!r} between identities "
                f"{colliding!r}; add an explicit reviewed identity instead"
            )
        assert resolution.slug is not None
        result[key] = resolution.slug
    return result


def validate_assigned_domain_slugs(
    rows: Iterable[tuple[Any, object]], *, domain: str
) -> None:
    """Validate assigned slugs and reject duplicates within one resource domain."""

    owners: dict[str, Any] = {}
    for key, raw_slug in rows:
        slug = require_domain_slug(raw_slug, context=f"{domain} identity {key!r} slug")
        previous = owners.get(slug)
        if previous is not None and previous != key:
            raise ValueError(
                f"{domain} slug {slug!r} is assigned to both identities "
                f"{previous!r} and {key!r}"
            )
        owners[slug] = key


def validate_typed_domain_id(value: object, *, expected_domain: str, context: str) -> str:
    """Validate a curated typed identity such as ``skill:doctor``.

    Additional colon-separated qualifiers are supported for domains that need
    them, for example ``skill-declaration-category:automatic:p86``. Every
    segment follows the same domain-slug grammar.
    """

    if not isinstance(value, str):
        raise ValueError(f"{context} must be a typed domain identity")
    parts = value.split(":")
    if len(parts) < 2 or parts[0] != expected_domain:
        raise ValueError(f"{context} must start with {expected_domain!r} followed by ':'")
    for index, part in enumerate(parts):
        require_domain_slug(part, context=f"{context} segment {index}")
    return value


def route_slug_from_typed_domain_id(
    value: object, *, expected_domain: str, context: str
) -> str:
    """Project one simple typed identity onto its domain-local public route slug.

    Route-backed curated identities use exactly ``domain:slug``. Qualified typed
    identities remain valid internal IDs, but cannot be flattened into a public
    route implicitly because that would create a second identity scheme.
    """

    identifier = validate_typed_domain_id(
        value, expected_domain=expected_domain, context=context
    )
    parts = identifier.split(":")
    if len(parts) != 2:
        raise ValueError(
            f"{context} must contain exactly one domain-local route slug after "
            f"{expected_domain!r}"
        )
    return require_domain_slug(parts[1], context=f"{context} route slug")
