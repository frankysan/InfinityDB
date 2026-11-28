"""Resolve official N5 Army Unit routes from source-native memberships."""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from typing import Any, TypeGuard

_BASE_URL = "https://infinityuniverse.com/army/infinity"
_SLUG = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]*\Z")


def _safe_slug(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and _SLUG.fullmatch(value) is not None


def _resume_index(raw: str | None) -> dict[str, tuple[int, str] | None] | None:
    """Index exact upstream route keys; ambiguous keys cannot select a Unit."""
    if raw is None:
        return None
    try:
        rows = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(rows, list):
        return None
    result: dict[str, tuple[int, str] | None] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        slug, identifier = row.get("slug"), row.get("id")
        if not _safe_slug(slug):
            continue
        if slug in result or type(identifier) is not int or identifier <= 0:
            result[slug] = None
        else:
            name = row.get("name")
            result[slug] = (identifier, name if isinstance(name, str) and name.strip() else slug)
    return result


def official_army_links(
    connection: sqlite3.Connection, factions: dict[int, dict[str, Any]],
) -> dict[tuple[int, int], list[dict[str, str]]]:
    """Return links keyed by exact (source Army, source Unit), never logical slugs.

    The official workspace selects a metadata faction slug and then a Unit slug
    from its resume or reinforcement resume. A reinforcement section is reached
    through each actual parent Army, not through the section's own source ID.
    """
    lists = {
        identifier: (kind, reinforcement, _resume_index(resume))
        for identifier, kind, reinforcement, resume in connection.execute(
            "SELECT id,kind,reinforcement_id,resume FROM army_lists ORDER BY id"
        )
    }
    memberships = {
        (row[0], row[1]) for row in connection.execute("SELECT army_id,unit_id FROM army_units")
    }
    metadata_slug_counts = Counter(
        faction.get("slug") for faction in factions.values()
        if _safe_slug(faction.get("slug"))
    )
    sections = {reinforcement for _, reinforcement, _ in lists.values()
                if type(reinforcement) is int}
    result: dict[tuple[int, int], list[dict[str, str]]] = defaultdict(list)
    for army_id, (kind, reinforcement_id, resume) in lists.items():
        faction = factions.get(army_id, {})
        army_slug = faction.get("slug")
        name = faction.get("name")
        if (
            kind == "reinforcement" or army_id in sections
            or not _safe_slug(army_slug) or metadata_slug_counts[army_slug] != 1
            or not isinstance(name, str) or not name or resume is None
        ):
            continue
        reinforcement_resume = (
            lists.get(reinforcement_id, (None, None, None))[2]
            if reinforcement_id is not None else {}
        )
        # Without the paired resume we cannot rule out a conflicting route.
        if reinforcement_resume is None:
            continue
        for source_id, index, other in (
            (army_id, resume, reinforcement_resume),
            (reinforcement_id, reinforcement_resume, resume),
        ):
            if source_id is None:
                continue
            for slug, entry in index.items():
                if entry is None or slug in other:
                    continue
                unit_id, unit_name = entry
                if (source_id, unit_id) not in memberships:
                    continue
                link = {
                    "army_name": name, "unit_name": unit_name,
                    "href": f"{_BASE_URL}/{army_slug}/{slug}",
                }
                links = result[(source_id, unit_id)]
                if link not in links:
                    links.append(link)
    return dict(result)
