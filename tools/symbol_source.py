"""Discover authoritative symbol sources and exportable lookup identities."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import urlparse

from infinity_db.legacy_armies import DEFAULT_LEGACY_ARMIES, LegacyArmy, load_legacy_armies
from infinity_db.snapshot_provenance import portable_project_path
from tools.path_sanitization import sanitize_filename

ASSET_HOST = "assets.corvusbelli.net"
ASSET_ROOT_PATH = "/army/img/"
DEFAULT_STATIC_CONFIG = Path("config/symbols/static-symbols.json")
SVG_NAME = re.compile(r"[a-z0-9-]+\.svg$")
ARMY_FILE = re.compile(r"^(?P<id>\d+)-(?P<slug>.+)\.json$", re.IGNORECASE)
STATIC_IDENTIFIER = re.compile(r"[a-z0-9-]+")


class SourceDocument(NamedTuple):
    name: str
    data: dict[str, Any]


class Discovery(NamedTuple):
    references: list[dict[str, Any]]
    authoritative_urls: set[str]
    audit: dict[str, int]
    source_document_count: int


class ResolutionPlan(NamedTuple):
    """Stable producer override lookup paths and their collisions."""

    override_paths: dict[str, str]
    collisions: dict[str, list[str]]


def _normalized_label(value: object) -> str:
    """Return one source-label comparison form without inventing semantic aliases."""
    return _slugify_label(str(value or "")).replace("-", " ")


def _slugify_label(value: str) -> str:
    """Return the same readable ASCII slug shape used by published symbol names."""
    return sanitize_filename(value).removesuffix(".svg")


def _peripheral_skill_ids(documents: list[SourceDocument]) -> set[int]:
    """Return source Skill IDs explicitly named Peripheral by metadata."""
    result: set[int] = set()
    for document in documents:
        if document.name != "metadata.json":
            continue
        skills = document.data.get("skills")
        if not isinstance(skills, list):
            continue
        for skill in skills:
            if (
                isinstance(skill, dict)
                and type(skill.get("id")) is int
                and isinstance(skill.get("name"), str)
                and skill["name"].strip().casefold() == "peripheral"
            ):
                result.add(skill["id"])
    return result


def _profile_is_peripheral(profile: dict[str, Any], peripheral_skill_ids: set[int]) -> bool:
    skills = profile.get("skills")
    if not isinstance(skills, list):
        return False
    for skill in skills:
        if not isinstance(skill, dict):
            continue
        if type(skill.get("id")) is int and skill["id"] in peripheral_skill_ids:
            return True
        name = skill.get("name")
        if isinstance(name, str) and name.strip().casefold() == "peripheral":
            return True
    return False


def _army_peripheral_names(document: dict[str, Any]) -> list[str]:
    filters = document.get("filters")
    if not isinstance(filters, dict):
        return []
    rows = filters.get("peripheral")
    if not isinstance(rows, list):
        return []
    names: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        if isinstance(name, str) and name.strip():
            names.append(name.strip())
    return names


def _peripheral_name(profile_name: str, source_names: list[str]) -> str:
    """Prefer the Army-local Peripheral name embedded in one profile label.

    Exact and prefix matches are intentionally preferred over generic substring
    matches.  This keeps labels such as ``BÂTARD, Merc Antipode`` attached to
    BÂTARD rather than the more generic ANTIPODE definition.  When Army does not
    expose a matching filter label, the profile name remains the source-backed
    fallback instead of guessing a maintained identity.
    """
    normalized_profile = _normalized_label(profile_name)
    if not normalized_profile:
        return profile_name.strip()

    candidates = [
        (name, _normalized_label(name))
        for name in source_names
        if _normalized_label(name)
    ]
    exact = [name for name, normalized in candidates if normalized == normalized_profile]
    if len(exact) == 1:
        return exact[0]

    prefix = [
        (name, normalized)
        for name, normalized in candidates
        if normalized_profile.startswith(normalized + " ")
    ]
    if prefix:
        longest = max(len(normalized) for _name, normalized in prefix)
        winners = [name for name, normalized in prefix if len(normalized) == longest]
        if len(winners) == 1:
            return winners[0]

    padded_profile = f" {normalized_profile} "
    contained = [
        (name, normalized)
        for name, normalized in candidates
        if f" {normalized} " in padded_profile
    ]
    if contained:
        longest = max(len(normalized) for _name, normalized in contained)
        winners = [name for name, normalized in contained if len(normalized) == longest]
        if len(winners) == 1:
            return winners[0]
    return profile_name.strip()


def destination_name(url: str) -> str:
    """Return one deterministic, Windows-safe SVG filename for an asset URL."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != ASSET_HOST:
        raise ValueError(f"Unsupported symbol host: {url}")
    if not parsed.path.startswith(ASSET_ROOT_PATH):
        raise ValueError(f"Unsupported symbol path: {url}")

    tail = url.removeprefix(f"https://{ASSET_HOST}{ASSET_ROOT_PATH}")
    tail = tail.rsplit("/", 1)[-1].split("#", 1)[0]
    if ".svg" in tail.lower():
        stem = tail[: tail.lower().rfind(".svg")]
        name = f"{stem}.svg"
    else:
        name = Path(parsed.path).name

    if not SVG_NAME.fullmatch(name):
        name = sanitize_filename(name)
    return name


def load_source_documents(path: Path) -> list[SourceDocument]:
    """Load raw Army JSON documents from a ZIP/directory or a legacy master JSON."""
    documents: list[SourceDocument] = []
    if path.is_file() and zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for name in sorted(archive.namelist()):
                if name.endswith("/") or not name.lower().endswith(".json"):
                    continue
                data = json.loads(archive.read(name))
                if isinstance(data, dict):
                    documents.append(SourceDocument(Path(name).name, data))
    elif path.is_dir():
        for file in sorted(path.glob("*.json")):
            data = json.loads(file.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                documents.append(SourceDocument(file.name, data))
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("master list must be an object keyed by Army source filename")
        for name, value in sorted(data.items()):
            if isinstance(value, dict):
                filename = name if str(name).lower().endswith(".json") else f"{name}.json"
                documents.append(SourceDocument(Path(filename).name, value))
    if not documents:
        raise ValueError("No JSON source documents were found")
    return documents


def load_static_symbols(path: Path) -> list[dict[str, str]]:
    """Load and validate the maintained static-symbol declaration file."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not load static symbols {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError("static symbols must be a JSON object")
    if set(document) != {"schema_version", "base_url", "assets"}:
        raise ValueError("static symbols must contain schema_version, base_url, and assets")
    if document["schema_version"] != 2:
        raise ValueError("static symbols schema_version must be 2")
    base_url = document["base_url"]
    if not isinstance(base_url, str) or not base_url.startswith("https://"):
        raise ValueError("static symbols base_url must be an HTTPS URL")
    assets = document["assets"]
    if not isinstance(assets, list):
        raise ValueError("static symbols assets must be an array")

    result: list[dict[str, str]] = []
    keys: set[str] = set()
    declarations: set[tuple[str, str]] = set()
    for index, asset in enumerate(assets):
        context = f"static symbols assets[{index}]"
        if not isinstance(asset, dict) or set(asset) != {"key", "category", "filename", "label"}:
            raise ValueError(f"{context} must contain key, category, filename, and label")
        row: dict[str, str] = {}
        for field in ("key", "category", "filename", "label"):
            value = asset[field]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{context}.{field} must be a non-empty string")
            row[field] = value
        for field in ("key", "category"):
            if not STATIC_IDENTIFIER.fullmatch(row[field]):
                raise ValueError(f"{context}.{field} must use lowercase slug syntax")
        if row["key"] in keys:
            raise ValueError(f"{context}.key is duplicated: {row['key']}")
        keys.add(row["key"])
        declaration = (row["category"], row["filename"])
        if declaration in declarations:
            raise ValueError(f"{context} duplicates {row['category']}/{row['filename']}")
        declarations.add(declaration)
        if (
            Path(row["filename"]).name != row["filename"]
            or not row["filename"].lower().endswith(".svg")
        ):
            raise ValueError(f"{context}.filename must be one SVG filename")
        row["url"] = base_url.rstrip("/") + "/" + row["filename"]
        destination_name(row["url"])
        result.append(row)
    return result


def discover_symbols(
    documents: list[SourceDocument],
    *,
    static_symbols: list[dict[str, str]],
    static_source: str,
    legacy_armies: tuple[LegacyArmy, ...] = (),
    legacy_source: str = "data/curated/identities/legacy-armies.json",
) -> Discovery:
    """Discover authoritative Army/static symbols and audit all raw SVG references."""
    semantic: list[dict[str, Any]] = []
    resume: list[dict[str, Any]] = []
    known_locations: set[tuple[str, str]] = set()
    peripheral_skill_ids = _peripheral_skill_ids(documents)

    for document in documents:
        if document.name == "metadata.json":
            factions = document.data.get("factions", [])
            if not isinstance(factions, list):
                raise ValueError("metadata.json factions must be an array")
            for index, faction in enumerate(factions):
                if not isinstance(faction, dict):
                    continue
                logo = faction.get("logo")
                if not isinstance(logo, str):
                    continue
                path = f"$.factions[{index}].logo"
                reference: dict[str, Any] = {
                    "kind": "faction",
                    "authoritative": True,
                    "sourceDocument": document.name,
                    "jsonPath": path,
                    "assetUrl": logo,
                }
                if type(faction.get("id")) is int:
                    reference["factionId"] = faction["id"]
                if isinstance(faction.get("slug"), str) and faction["slug"].strip():
                    reference["factionSlug"] = faction["slug"]
                semantic.append(reference)
                known_locations.add((document.name, path))
            continue

        units = document.data.get("units")
        if not isinstance(units, list):
            continue
        army_match = ARMY_FILE.match(document.name)
        army_id = int(army_match.group("id")) if army_match else None
        army_slug = army_match.group("slug") if army_match else None
        peripheral_names = _army_peripheral_names(document.data)
        for unit_index, unit in enumerate(units):
            if not isinstance(unit, dict):
                continue
            unit_id = unit.get("id") if type(unit.get("id")) is int else None
            unit_slug = unit.get("slug") if isinstance(unit.get("slug"), str) else None
            groups = unit.get("profileGroups", [])
            if isinstance(groups, list):
                for group_index, group in enumerate(groups):
                    if not isinstance(group, dict):
                        continue
                    profiles = group.get("profiles", [])
                    if not isinstance(profiles, list):
                        continue
                    for profile_index, profile in enumerate(profiles):
                        if not isinstance(profile, dict):
                            continue
                        logo = profile.get("logo")
                        if not isinstance(logo, str):
                            continue
                        path = (
                            f"$.units[{unit_index}].profileGroups[{group_index}]"
                            f".profiles[{profile_index}].logo"
                        )
                        reference = {
                            "kind": "unit-profile",
                            "authoritative": True,
                            "sourceDocument": document.name,
                            "jsonPath": path,
                            "assetUrl": logo,
                        }
                        if army_id is not None:
                            reference["armyId"] = army_id
                        if army_slug:
                            reference["armySlug"] = army_slug
                        if unit_id is not None:
                            reference["unitId"] = unit_id
                        if unit_slug:
                            reference["unitSlug"] = unit_slug
                        profile_name = profile.get("name") or profile.get("isc")
                        if isinstance(profile_name, str) and profile_name.strip():
                            reference["profileName"] = profile_name
                            if _profile_is_peripheral(profile, peripheral_skill_ids):
                                reference["peripheralName"] = _peripheral_name(
                                    profile_name,
                                    peripheral_names,
                                )
                        semantic.append(reference)
                        known_locations.add((document.name, path))

        resume_rows = document.data.get("resume", [])
        if isinstance(resume_rows, list):
            for resume_index, row in enumerate(resume_rows):
                if not isinstance(row, dict) or not isinstance(row.get("logo"), str):
                    continue
                path = f"$.resume[{resume_index}].logo"
                reference = {
                    "kind": "resume-audit",
                    "authoritative": False,
                    "sourceDocument": document.name,
                    "jsonPath": path,
                    "assetUrl": row["logo"],
                }
                if army_id is not None:
                    reference["armyId"] = army_id
                if army_slug:
                    reference["armySlug"] = army_slug
                if type(row.get("id")) is int:
                    reference["unitId"] = row["id"]
                if isinstance(row.get("slug"), str) and row["slug"].strip():
                    reference["unitSlug"] = row["slug"]
                resume.append(reference)
                known_locations.add((document.name, path))

    for index, army in enumerate(legacy_armies):
        reference = {
            "kind": "faction",
            "authoritative": True,
            "sourceDocument": legacy_source,
            "jsonPath": f"$.armies[{index}].logo",
            "assetUrl": army.logo,
            "factionId": army.id,
            "factionSlug": army.slug,
        }
        semantic.append(reference)

    recursive: list[tuple[str, str, str]] = []
    for document in documents:
        recursive.extend(
            (document.name, json_path, value)
            for json_path, value in _string_values(document.data)
            if ".svg" in value.casefold()
        )
    unknown = [
        item for item in recursive if (item[0], item[1]) not in known_locations
    ]
    if unknown:
        details = "\n".join(f"  {name} {path}: {url}" for name, path, url in unknown[:20])
        extra = "" if len(unknown) <= 20 else f"\n  ... and {len(unknown) - 20} more"
        raise ValueError(
            "Unknown SVG-bearing Army source fields were found:\n" + details + extra
        )

    static_refs: list[dict[str, Any]] = []
    for index, asset in enumerate(static_symbols):
        static_refs.append(
            {
                "kind": "static",
                "authoritative": True,
                "sourceDocument": static_source,
                "jsonPath": f"$.assets[{index}]",
                "assetUrl": asset["url"],
                "staticKey": asset["key"],
                "staticCategory": asset["category"],
                "label": asset["label"],
            }
        )

    for reference in [*semantic, *resume, *static_refs]:
        destination_name(reference["assetUrl"])

    authoritative_urls = {
        reference["assetUrl"] for reference in [*semantic, *static_refs]
    }
    unit_refs = [row for row in semantic if row["kind"] == "unit-profile"]
    faction_refs = [row for row in semantic if row["kind"] == "faction"]
    semantic_urls = {reference["assetUrl"] for reference in semantic}
    audit = {
        "unitProfileReferenceCount": len(unit_refs),
        "uniqueUnitUrlCount": len({row["assetUrl"] for row in unit_refs}),
        "factionReferenceCount": len(faction_refs),
        "uniqueFactionUrlCount": len({row["assetUrl"] for row in faction_refs}),
        "semanticReferenceCount": len(semantic),
        "uniqueSemanticUrlCount": len(semantic_urls),
        "resumeReferenceCount": len(resume),
        "uniqueResumeUrlCount": len({row["assetUrl"] for row in resume}),
        "staticReferenceCount": len(static_refs),
        "recursiveReferenceCount": len(recursive),
        "uniqueRecursiveUrlCount": len({url for _, _, url in recursive}),
        "uniqueDownloadedUrlCount": len(authoritative_urls),
        "unknownReferenceCount": 0,
    }
    return Discovery(
        references=[*semantic, *resume, *static_refs],
        authoritative_urls=authoritative_urls,
        audit=audit,
        source_document_count=len(documents),
    )


def _string_values(value: Any, path: str = "$"):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _string_values(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _string_values(child, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value


def archive_paths(discovery: Discovery) -> dict[str, str]:
    """Assign deterministic raw-archive paths without conflating consumer references."""
    categories: dict[str, set[str]] = {url: set() for url in discovery.authoritative_urls}
    for reference in discovery.references:
        url = reference["assetUrl"]
        if url not in categories or not reference["authoritative"]:
            continue
        kind = reference["kind"]
        if kind == "unit-profile":
            categories[url].add("units")
        elif kind == "faction":
            categories[url].add("factions")
        elif kind == "static":
            categories[url].add(f"static/{reference['staticCategory']}")

    candidates: dict[str, str] = {}
    for url in sorted(discovery.authoritative_urls):
        category = sorted(categories[url])[0] if categories[url] else "unclassified"
        candidates[url] = f"{category}/{destination_name(url)}"

    by_candidate: dict[str, list[str]] = {}
    for url, candidate in candidates.items():
        by_candidate.setdefault(candidate.casefold(), []).append(url)
    for urls in by_candidate.values():
        if len(urls) < 2:
            continue
        for url in urls:
            path = Path(candidates[url])
            suffix = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
            candidates[url] = (path.parent / f"{path.stem}--{suffix}{path.suffix}").as_posix()
    return candidates


def override_resolution_plan(discovery: Discovery) -> ResolutionPlan:
    """Return stable URL-derived override paths and any filename collisions."""
    categories: dict[str, set[str]] = {url: set() for url in discovery.authoritative_urls}
    for reference in discovery.references:
        url = reference["assetUrl"]
        if url not in categories or not reference["authoritative"]:
            continue
        kind = reference["kind"]
        if kind == "unit-profile":
            categories[url].add("units")
        elif kind == "faction":
            categories[url].add("factions")
        elif kind == "static":
            categories[url].add(reference["staticCategory"])

    candidates: dict[str, str] = {}
    for url in sorted(discovery.authoritative_urls):
        category = sorted(categories[url])[0] if categories[url] else "unclassified"
        candidates[url] = f"{category}/{destination_name(url)}"

    collisions: dict[str, list[str]] = {}
    by_candidate: dict[str, list[str]] = {}
    for url, candidate in candidates.items():
        by_candidate.setdefault(candidate.casefold(), []).append(url)
    for key, urls in sorted(by_candidate.items()):
        if len(urls) < 2:
            continue
        collisions[key] = sorted(urls)
        for url in urls:
            path = Path(candidates[url])
            suffix = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
            candidates[url] = (path.parent / f"{path.stem}--{suffix}{path.suffix}").as_posix()
    return ResolutionPlan(candidates, collisions)


def discover_symbol_source(
    source: Path,
    *,
    static_symbols_path: Path = DEFAULT_STATIC_CONFIG,
    legacy_armies_path: Path | None = DEFAULT_LEGACY_ARMIES,
    project_root: Path | None = None,
) -> Discovery:
    """Discover every authoritative symbol for one explicit Army source artifact."""
    if not source.is_file():
        raise ValueError("source must be an immutable Army ZIP or JSON file")
    project_root = project_root or Path.cwd()
    documents = load_source_documents(source)
    static_symbols = load_static_symbols(static_symbols_path)
    static_source = (
        portable_project_path(static_symbols_path, project_root=project_root)
        or static_symbols_path.name
    )
    if legacy_armies_path is None:
        legacy_armies = ()
        legacy_source = "data/curated/identities/legacy-armies.json"
    else:
        legacy_armies = load_legacy_armies(legacy_armies_path)
        legacy_source = (
            portable_project_path(legacy_armies_path, project_root=project_root)
            or legacy_armies_path.name
        )
    return discover_symbols(
        documents,
        static_symbols=static_symbols,
        static_source=static_source,
        legacy_armies=legacy_armies,
        legacy_source=legacy_source,
    )
