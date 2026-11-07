"""Verify and project reviewed Weapon Chart citations without reading curation."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from infinity_db.database.repository import Database

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


def load_weapon_profile_publication(
    path: Path, army_database: Path, rules_database: Path | None,
) -> ProfileCitations | None:
    """Load an exact release-pair publication, or None for a legacy installation."""
    if not path.is_file():
        return None
    if rules_database is None:
        raise ValueError("Weapon profile publication requires a rules database")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid Weapon profile publication JSON") from exc
    if (
        not isinstance(document, dict)
        or type(document.get("formatVersion")) is not int
        or document["formatVersion"] != 1
        or document.get("scope") != PROFILE_CITATION_SCOPE
        or not isinstance(document.get("weapons"), list)
    ):
        raise ValueError("Unsupported Weapon profile publication")

    snapshot = document.get("sourceSnapshot")
    if not isinstance(snapshot, dict) or (
        snapshot.get("armyDatabaseSha256") != file_sha256(army_database)
        or snapshot.get("rulesDatabaseSha256") != file_sha256(rules_database)
    ):
        raise ValueError("Weapon profile publication does not match release databases")
    review_sha = snapshot.get("reviewsSha256")
    if not isinstance(review_sha, str) or re.fullmatch(r"[0-9a-f]{64}", review_sha) is None:
        raise ValueError("Weapon profile publication lacks review provenance")

    source = document.get("source")
    if (
        not isinstance(source, dict)
        or not isinstance(source.get("collectionId"), str)
        or not isinstance(source.get("id"), str)
        or source != current_pdf_source(
            rules_database, source["collectionId"], source["id"],
        )
    ):
        raise ValueError("Weapon profile publication source does not match current rules")
    page_range = document.get("chartPageRange")
    if (
        not isinstance(page_range, list)
        or len(page_range) != 2
        or any(type(page) is not int for page in page_range)
        or not 1 <= page_range[0] <= page_range[1] <= source["pageCount"]
    ):
        raise ValueError("Invalid Weapon Chart page range")

    database = Database(army_database)
    citations: ProfileCitations = {}
    seen_weapons: set[int] = set()
    for weapon in document["weapons"]:
        if not isinstance(weapon, dict):
            raise ValueError("Invalid reviewed Weapon identity")
        weapon_id, slug, name = weapon.get("id"), weapon.get("slug"), weapon.get("name")
        digest, profiles = weapon.get("profileSha256"), weapon.get("profiles")
        if (
            type(weapon_id) is not int or weapon_id <= 0 or weapon_id in seen_weapons
            or not isinstance(slug, str) or not slug
            or not isinstance(name, str) or not name
            or not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None
            or not isinstance(profiles, list) or not profiles
        ):
            raise ValueError("Invalid or duplicate reviewed Weapon identity")
        seen_weapons.add(weapon_id)
        details = database.get_catalog_item("weapons", weapon_id)
        if (
            details is None
            or details["name"] != name
            or database.application_slug("weapons", weapon_id) != slug
            or profile_sha256(details["profiles"]) != digest
        ):
            raise ValueError(f"Reviewed Weapon profile identity changed: {slug}")
        expected = {(profile["id"], profile.get("mode")) for profile in details["profiles"]}
        if len(expected) != len(details["profiles"]):
            raise ValueError(f"Ambiguous Weapon profile identities: {slug}")
        actual: set[tuple[int, str | None]] = set()
        for profile in profiles:
            if not isinstance(profile, dict):
                raise ValueError(f"Invalid reviewed Weapon profile: {slug}")
            profile_id, mode, page = (
                profile.get("sourceId"), profile.get("mode"), profile.get("page"),
            )
            if (
                type(profile_id) is not int or profile_id <= 0
                or (mode is not None and (not isinstance(mode, str) or not mode))
                or type(page) is not int or not page_range[0] <= page <= page_range[1]
                or (profile_id, mode) in actual
            ):
                raise ValueError(f"Invalid or duplicate reviewed Weapon mode: {slug}")
            actual.add((profile_id, mode))
            citations[(weapon_id, profile_id, mode)] = {
                "source_id": source["id"],
                "source_title": source["title"],
                "source_version": source["version"],
                "source_url": source["url"],
                "source_sha256": source["sha256"],
                "source_collection_id": source["collectionId"],
                "page": page,
            }
        if actual != expected:
            raise ValueError(f"Reviewed Weapon modes do not match the database: {slug}")
    return citations


def load_runtime_weapon_profile_publication(
    army_database: Path, rules_database: Path | None,
) -> tuple[ProfileCitations | None, str | None]:
    """Load and fingerprint only the publication attached to this runtime pair."""
    if (
        rules_database is not None
        and rules_database.resolve().parent != army_database.resolve().parent
    ):
        return None, None
    path = army_database.with_name("weapon-profile-sources.json")
    citations = load_weapon_profile_publication(path, army_database, rules_database)
    return citations, file_sha256(path) if citations is not None else None


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
