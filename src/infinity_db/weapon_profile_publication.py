"""Verify and project reviewed Weapon Chart citations without reading curation."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

PROFILE_CITATION_SCOPE = "reviewed-weapon-profile-chart"
ProfileKey = tuple[int, int, str | None]
ProfileCitations = dict[ProfileKey, dict[str, Any]]


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def profile_sha256(profiles: list[dict[str, Any]]) -> str:
    data = json.dumps(
        profiles, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def current_pdf_source(
    rules_database: Path, collection_id: str, source_id: str,
) -> dict[str, Any]:
    """Read the selected current PDF identity from the published rules database."""
    uri = Path(rules_database).resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT s.id, s.title, s.version, s.url, s.sha256, s.page_count "
            "FROM sources AS s JOIN collections AS c ON c.id = s.collection_id "
            "WHERE s.collection_id = ? AND s.id = ? "
            "AND c.status = 'current' AND s.kind = 'pdf' AND s.authority = 'primary'",
            (collection_id, source_id),
        ).fetchone()
    if row is None:
        raise ValueError("Reviewed Weapon Chart source is not a current primary PDF")
    source = {
        "collectionId": collection_id,
        "id": row["id"],
        "title": row["title"],
        "version": row["version"],
        "url": row["url"],
        "sha256": row["sha256"],
        "pageCount": row["page_count"],
    }
    if (
        any(not isinstance(source[key], str) or not source[key]
            for key in ("collectionId", "id", "title", "version", "url"))
        or not isinstance(source["sha256"], str)
        or re.fullmatch(r"[0-9a-f]{64}", source["sha256"]) is None
        or type(source["pageCount"]) is not int
        or source["pageCount"] <= 0
    ):
        raise ValueError("Reviewed Weapon Chart source has incomplete provenance")
    return source


def load_runtime_weapon_profile_publication(
    army_database: Path, rules_database: Path | None,
) -> tuple[ProfileCitations | None, str | None]:
    """Read only embedded Rules citations; never load loose JSON sidecars."""
    if rules_database is None:
        return None, None
    from .rules_database import RulesDatabase

    citations = RulesDatabase(rules_database).weapon_profile_citations_payload(army_database)
    return citations, file_sha256(rules_database) if citations is not None else None


def attach_weapon_profile_citations(
    item: dict[str, Any], citations: ProfileCitations | None,
) -> None:
    """Attach citations to exact profile identities in both API projections."""
    item["profile_citations_available"] = citations is not None
    groups = [item.get("profiles", [])]
    groups.extend(variant.get("profiles", []) for variant in item.get("weapon_variants", []))
    for profiles in groups:
        for profile in profiles:
            key = (item["id"], profile["id"], profile.get("mode"))
            citation = citations.get(key) if citations is not None else None
            profile["profile_citations"] = [dict(citation)] if citation is not None else []
