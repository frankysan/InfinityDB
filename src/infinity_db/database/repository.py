"""Read-only application queries over the versioned normalized database."""

from __future__ import annotations

import json
import re
import sqlite3
import threading
import unicodedata
import weakref
from collections import OrderedDict
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping
from contextlib import contextmanager
from datetime import date
from functools import wraps
from pathlib import Path
from typing import Any, Protocol

from infinity_army_data.availability import (
    MERCENARY_AVAILABILITY,
    STANDARD_AVAILABILITY,
)
from infinity_army_data.normalized_format import FORMAT_NAME, FORMAT_VERSION
from infinity_db.domain_slugs import (
    APPLICATION_SLUG_DOMAINS,
    assign_domain_slugs,
    require_domain_slug,
)
from infinity_db.identities import (
    IDENTITY_CONFIG_METADATA_KEY,
    IDENTITY_CONFIG_SHA256_METADATA_KEY,
    IdentityConfig,
    IdentityConfigError,
    normalized_profile_identity,
    parse_identity_metadata,
    strip_reinforcement_prefix,
)

from .application_armies import (
    ARMY_ROLE_REINFORCEMENT,
    validate_application_armies,
    validate_application_army_integrity,
)
from .application_catalogs import validate_application_catalogs
from .application_domain_slugs import validate_application_domain_slugs
from .fireteam_relationships import (
    validate_application_fireteam_integrity,
    validate_application_fireteams,
)
from .include_relationships import validate_include_relationships
from .logical_unit_payloads import ALIAS_FIELDS, MATERIALIZED_LOGICAL_UNIT_FIELDS
from .peripheral_relationships import validate_peripheral_relationships
from .publication import PUBLISHED_CONTENT_SHA256_KEY, published_content_sha256
from .relation_constraints import validate_relation_constraints
from .relation_group_dependencies import validate_relation_group_dependencies
from .schema import (
    APPLICATION_ID,
    DATABASE_COMPATIBILITY_KEY,
    DATABASE_COMPATIBILITY_VERSION,
    DATABASE_TABLES,
    METADATA_TABLE,
    PUBLISHED_DATABASE_TABLES,
    SCHEMA_VERSION,
    quote,
)

SQLITE_INTEGER_MIN = -(2**63)
SQLITE_INTEGER_MAX = 2**63 - 1
SOURCE_UNIT_NAMES_CTE = (
    "source_unit_names AS ("
    "SELECT lus.source_unit_id AS unit_id, "
    "COALESCE(a.value, COALESCE(NULLIF(lu.name, ''), 'Unit ' || lu.id)) AS unit_name "
    "FROM logical_unit_sources AS lus "
    "JOIN logical_units AS lu ON lu.id = lus.logical_unit_id "
    "LEFT JOIN logical_unit_aliases AS a "
    "ON a.logical_unit_id = lus.logical_unit_id "
    "AND a.source_unit_id = lus.source_unit_id AND a.field = 'name'"
    ")"
)
AVAILABILITY_FLAGS = ("mercs", "specops", "teamops", "reinforcement")


class ArmySelectionError(ValueError):
    """Raised when an army identity exists but is not a selectable force."""


class RowLike(Protocol):
    """Minimal row interface shared by sqlite3.Row and test dictionaries."""

    def __getitem__(self, key: str, /) -> Any: ...

    def keys(self) -> Iterable[str]: ...


def _validate_logical_unit_payloads(connection: sqlite3.Connection) -> None:
    representative_mismatch = connection.execute(
        "SELECT 1 FROM logical_units AS lu "
        "JOIN units AS r ON r.id = lu.representative_unit_id "
        "WHERE "
        + " OR ".join(
            f"NOT (lu.{field} IS r.{field})"
            for field in MATERIALIZED_LOGICAL_UNIT_FIELDS
        )
        + " LIMIT 1"
    ).fetchone()

    alias_cases = " + ".join(
        (
            "CASE WHEN lus.source_unit_id != lu.representative_unit_id "
            "AND NOT (COALESCE(NULLIF(u.name, ''), 'Unit ' || u.id) IS "
            "COALESCE(NULLIF(r.name, ''), 'Unit ' || r.id)) THEN 1 ELSE 0 END"
            if field == "name"
            else "CASE WHEN lus.source_unit_id != lu.representative_unit_id "
            f"AND u.{field} IS NOT NULL AND u.{field} != '' "
            f"AND NOT (u.{field} IS r.{field}) THEN 1 ELSE 0 END"
        )
        for field in ALIAS_FIELDS
    )
    expected_alias_count = connection.execute(
        "SELECT COALESCE(SUM("
        + alias_cases
        + "), 0) FROM logical_units AS lu "
        "JOIN units AS r ON r.id = lu.representative_unit_id "
        "JOIN logical_unit_sources AS lus ON lus.logical_unit_id = lu.id "
        "JOIN units AS u ON u.id = lus.source_unit_id"
    ).fetchone()[0]
    alias_count = connection.execute("SELECT COUNT(*) FROM logical_unit_aliases").fetchone()[0]

    alias_valid_cases = " OR ".join(
        (
            "(a.field = 'name' AND a.value IS "
            "COALESCE(NULLIF(u.name, ''), 'Unit ' || u.id) "
            "AND NOT (COALESCE(NULLIF(u.name, ''), 'Unit ' || u.id) IS "
            "COALESCE(NULLIF(r.name, ''), 'Unit ' || r.id)))"
            if field == "name"
            else f"(a.field = '{field}' AND a.value IS u.{field} "
            f"AND u.{field} IS NOT NULL AND u.{field} != '' "
            f"AND NOT (u.{field} IS r.{field}))"
        )
        for field in ALIAS_FIELDS
    )
    invalid_alias = connection.execute(
        "SELECT 1 FROM logical_unit_aliases AS a "
        "JOIN logical_units AS lu ON lu.id = a.logical_unit_id "
        "LEFT JOIN logical_unit_sources AS lus "
        "ON lus.logical_unit_id = a.logical_unit_id "
        "AND lus.source_unit_id = a.source_unit_id "
        "JOIN units AS u ON u.id = a.source_unit_id "
        "JOIN units AS r ON r.id = lu.representative_unit_id "
        "WHERE lus.source_unit_id IS NULL "
        "OR a.source_unit_id = lu.representative_unit_id "
        "OR NOT ("
        + alias_valid_cases
        + ") LIMIT 1"
    ).fetchone()

    expected_note_count = connection.execute(
        "SELECT COUNT(*) FROM units "
        "WHERE source_defined = 1 AND notes IS NOT NULL AND notes != ''"
    ).fetchone()[0]
    note_count = connection.execute("SELECT COUNT(*) FROM logical_unit_notes").fetchone()[0]
    invalid_note = connection.execute(
        "SELECT 1 FROM logical_unit_notes AS n "
        "LEFT JOIN logical_unit_sources AS lus "
        "ON lus.logical_unit_id = n.logical_unit_id "
        "AND lus.source_unit_id = n.source_unit_id "
        "JOIN units AS u ON u.id = n.source_unit_id "
        "WHERE lus.source_unit_id IS NULL OR u.notes IS NULL OR u.notes = '' "
        "OR NOT (n.note IS u.notes) LIMIT 1"
    ).fetchone()

    expected_spectables_count = connection.execute(
        "SELECT COUNT(*) FROM units "
        "WHERE source_defined = 1 AND spectables IS NOT NULL AND spectables != ''"
    ).fetchone()[0]
    spectables_count = connection.execute(
        "SELECT COUNT(*) FROM logical_unit_spectables"
    ).fetchone()[0]
    invalid_spectables = connection.execute(
        "SELECT 1 FROM logical_unit_spectables AS s "
        "LEFT JOIN logical_unit_sources AS lus "
        "ON lus.logical_unit_id = s.logical_unit_id "
        "AND lus.source_unit_id = s.source_unit_id "
        "JOIN units AS u ON u.id = s.source_unit_id "
        "WHERE lus.source_unit_id IS NULL "
        "OR u.spectables IS NULL OR u.spectables = '' "
        "OR NOT (s.spectables IS u.spectables) LIMIT 1"
    ).fetchone()

    if (
        representative_mismatch is not None
        or alias_count != expected_alias_count
        or invalid_alias is not None
        or note_count != expected_note_count
        or invalid_note is not None
        or spectables_count != expected_spectables_count
        or invalid_spectables is not None
    ):
        raise ValueError(
            "Database has invalid materialized canonical logical-unit payloads; "
            "rebuild the database"
        )


def instance_lru_cache(maxsize: int) -> Callable:
    """Cache immutable database-query results without retaining Database instances."""

    caches: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
    lock = threading.RLock()

    def decorator(function: Callable) -> Callable:
        @wraps(function)
        def cached(self, *args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            with lock:
                cache = caches.setdefault(self, OrderedDict())
                if key in cache:
                    cache.move_to_end(key)
                    return cache[key]
            value = function(self, *args, **kwargs)
            with lock:
                cache = caches.setdefault(self, OrderedDict())
                cache[key] = value
                cache.move_to_end(key)
                if len(cache) > maxsize:
                    cache.popitem(last=False)
            return value

        return cached

    return decorator


def identity_config_from_connection(connection: sqlite3.Connection) -> IdentityConfig:
    """Load and validate the identity policy pinned into a database snapshot."""
    rows = connection.execute(
        f"SELECT key, value FROM {quote(METADATA_TABLE)} WHERE key IN (?, ?)",
        (IDENTITY_CONFIG_METADATA_KEY, IDENTITY_CONFIG_SHA256_METADATA_KEY),
    ).fetchall()
    values = {row["key"]: row["value"] for row in rows}
    try:
        document = json.loads(values[IDENTITY_CONFIG_METADATA_KEY])
        content_sha256 = json.loads(values[IDENTITY_CONFIG_SHA256_METADATA_KEY])
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(
            "Database has invalid identity configuration metadata; rebuild the database"
        ) from exc
    try:
        return parse_identity_metadata(document, content_sha256)
    except IdentityConfigError as exc:
        raise ValueError(
            "Database has invalid identity configuration metadata; rebuild the database"
        ) from exc

def skill_merge_key(name: object) -> str | None:
    """Identify skill labels that differ only by a numeric level or value."""
    text = str(name or "").strip()
    if not re.search(r"\d", text):
        return None
    return re.sub(r"\s+", " ", re.sub(r"\d+", "", text)).casefold()

def merged_skill_name(name: object) -> str:
    """Turn a numeric skill variant label into its shared display label."""
    text = re.sub(r"\s+", " ", re.sub(r"\d+", "", str(name or "")).strip())
    text = re.sub(r"\s+L$", "", text, flags=re.IGNORECASE)
    return text.rstrip(" =:-()").strip()

def catalog_merge_key(name: object) -> str | None:
    """Identify catalog labels that differ only by a numeric level or value."""
    text = str(name or "").strip()
    if ":" in text:
        return text.split(":", 1)[0].strip().casefold() or None
    return skill_merge_key(text)

def merged_catalog_name(name: object) -> str:
    """Turn a numeric catalog variant label into its shared display label."""
    text = str(name or "").strip()
    if ":" in text:
        return text.split(":", 1)[0].strip()
    return merged_skill_name(text)

def source_trait_name(value: object) -> str:
    """Return a visible Army trait label, excluding bracketed profile annotations."""
    name = str(value or "").strip()
    return "" if name.startswith("[") else name

def unit_sort_key(value: object) -> str:
    """Return a case-insensitive, punctuation-free key for unit-name ordering."""
    decomposed = unicodedata.normalize("NFKD", str(value or "")).casefold()
    return "".join(character for character in decomposed if character.isalnum())

def accent_insensitive_key(value: object) -> str:
    """Return text suitable for case-, accent-, and punctuation-insensitive matching."""
    decomposed = unicodedata.normalize("NFKD", str(value or "")).casefold()
    return "".join(character for character in decomposed if character.isalnum())

def append_unique_item(items: list[dict[str, Any]], item: dict[str, Any]) -> None:
    """Add an item unless a merged source already contributed the same one."""
    if item not in items:
        items.append(item)

def _canonical_usage_select(
    payload_kind: str,
    catalog: str,
    *,
    where: str = "",
) -> str:
    """Return one canonical profile/loadout catalog-usage SELECT fragment."""
    if payload_kind == "profile":
        occurrence_table = "profile_payload_occurrences"
        occurrence_alias = "ppo"
        payload_id = "profile_payload_id"
        parent_id = "profile_id"
        source_label = "profile"
    elif payload_kind == "loadout":
        occurrence_table = "loadout_payload_occurrences"
        occurrence_alias = "lpo"
        payload_id = "loadout_payload_id"
        parent_id = "option_id"
        source_label = "option"
    else:
        raise ValueError(f"Unknown payload kind: {payload_kind}")
    extra_stem = {"skills": "skill", "equipment": "equipment", "weapons": "weapon"}[
        catalog
    ]
    payload_table = f"{payload_kind}_payload_{catalog}"
    extras_table = f"{payload_kind}_payload_{extra_stem}_extras"
    return (
        f"SELECT '{source_label}' AS source, o.item_id, {occurrence_alias}.unit_id, "
        f"printf('%d:%d:%d:%d:%d', {occurrence_alias}.army_id, "
        f"{occurrence_alias}.unit_id, {occurrence_alias}.group_id, "
        f"{occurrence_alias}.{parent_id}, o.position) AS occurrence_key, "
        "e.position AS extra_position, e.extra_id "
        f"FROM {occurrence_table} AS {occurrence_alias} "
        f"JOIN {payload_table} AS o "
        f"ON o.{payload_id} = {occurrence_alias}.{payload_id} "
        f"LEFT JOIN {extras_table} AS e "
        f"ON e.{payload_id} = o.{payload_id} "
        "AND e.occurrence_position = o.position "
        + where
    )


def _canonical_filter_query(catalog: str, item_count: int) -> str:
    """Return source-unit matches for one application catalog identity."""
    if item_count < 1:
        raise ValueError("item_count must be positive")
    placeholders = ", ".join("?" for _ in range(item_count))
    return (
        "SELECT ppo.unit_id FROM profile_payload_occurrences AS ppo "
        f"JOIN profile_payload_{catalog} AS po "
        "ON po.profile_payload_id = ppo.profile_payload_id "
        f"WHERE po.item_id IN ({placeholders}) "
        "UNION SELECT lpo.unit_id FROM loadout_payload_occurrences AS lpo "
        f"JOIN loadout_payload_{catalog} AS lo "
        "ON lo.loadout_payload_id = lpo.loadout_payload_id "
        f"WHERE lo.item_id IN ({placeholders}) "
        f"UNION SELECT unit_id FROM unit_option_{catalog} "
        f"WHERE item_id IN ({placeholders})"
    )


def logical_source_profile_merge_key(
    army_occurrence_key: tuple[int, tuple[str, ...]], profile: RowLike
) -> tuple[Any, ...]:
    """Return the context key used to merge one profile across logical-unit sources.

    Canonical payload identity is intentionally not used here.  Two source
    occurrences can represent the same visible profile while one contributes
    nested relationships that another omits.  Their scalar profile facts,
    source-local profile coordinates, effective army occurrence, and
    classification must still agree before the occurrences may collapse.
    """
    return (
        army_occurrence_key,
        profile["group_id"],
        profile["profile_id"],
        profile["name"],
        profile["move_1"],
        profile["move_2"],
        profile["cc"],
        profile["bs"],
        profile["ph"],
        profile["wip"],
        profile["arm"],
        profile["bts"],
        profile["vitality"],
        profile["silhouette"],
        profile["type"],
        profile["classification"],
    )


def logical_source_loadout_merge_key(
    army_occurrence_key: tuple[int, tuple[str, ...]], loadout: RowLike
) -> tuple[Any, ...]:
    """Return the context key used to merge one loadout across logical-unit sources.

    Canonical payload identity is intentionally not used as occurrence identity.
    Distinct source-local options may reuse the same payload, while overlapping
    source records may still need to collapse when their effective Army
    occurrence, local option coordinates, costs, and visible scalar facts agree.
    """
    return (
        army_occurrence_key,
        loadout["group_id"],
        loadout["option_id"],
        loadout["name"],
        loadout["points"],
        loadout["swc"],
        loadout["minis"],
        loadout["disabled"],
    )


def merge_profile_availability(profile: dict[str, Any], duplicate: Mapping[str, Any]) -> None:
    """Merge only source-occurrence AVA after logical-source profile matching."""
    # Duplicate source records can disagree on AVA.  The lower non-negative
    # value is the restrictive availability and avoids advertising an option
    # that is not present in every source record for the same profile.
    ava = duplicate.get("ava")
    if ava is not None and (
        profile.get("ava") is None
        or (
            isinstance(ava, (int, float))
            and ava >= 0
            and isinstance(profile["ava"], (int, float))
            and profile["ava"] >= 0
            and ava < profile["ava"]
        )
    ):
        profile["ava"] = ava

def army_name(row: RowLike) -> str:
    if row["name"]:
        return row["name"]
    if row["slug"] == "reinf":
        return f"Reinforcements ({row['id']})"
    if row["slug"]:
        derived_name = re.sub(r"[_-]+", " ", row["slug"]).strip().title()
        if derived_name:
            return derived_name
    return f"Army {row['id']}"

def unit_optional_modes(group: Mapping[str, Any]) -> set[str]:
    """Return optional modes encoded in a dedicated unit's name or slug."""
    labels = [*group["names"], group.get("slug") or ""]
    normalized = " ".join(
        re.sub(r"[^a-z0-9]+", "-", label.casefold()).strip("-") for label in labels
    )
    modes = set()
    if "spec-ops" in normalized or "specops" in normalized:
        modes.add("specops")
    if "team-ops" in normalized or "teamops" in normalized:
        modes.add("teamops")
    return modes

def army_is_available(
    army: Mapping[str, Any], group: Mapping[str, Any], selected_flags: set[str]
) -> bool:
    """Return whether an army occurrence needs only enabled optional modes."""
    return army_required_flags(army, group) <= selected_flags

def army_required_flags(
    army: Mapping[str, Any],
    group: Mapping[str, Any],
    canonical_faction_id: int | None = None,
    declared_faction_ids: Collection[int] | None = None,
) -> set[str]:
    """Return the optional availability categories required by an occurrence."""
    required = unit_optional_modes(group)
    availability_kind = army.get("availability_kind")
    if availability_kind == MERCENARY_AVAILABILITY:
        required.add("mercs")
    elif availability_kind == STANDARD_AVAILABILITY:
        pass
    elif availability_kind is None:
        # Legacy database rows created before normalized availability provenance
        # was persisted still need the previous canonical/declaration inference.
        faction_id = (
            group["canonical_faction_id"]
            if canonical_faction_id is None
            else canonical_faction_id
        )
        declared_factions = (
            group["declared_faction_ids"]
            if declared_faction_ids is None
            else declared_faction_ids
        )
        if faction_id == 1 and army["id"] not in declared_factions:
            required.add("mercs")
    else:
        raise ValueError(f"Unknown army availability kind: {availability_kind!r}")
    if (
        army.get("role") == ARMY_ROLE_REINFORCEMENT
        or army.get("kind") == "reinforcement"
    ):
        required.add("reinforcement")
    filters = army.get("filters")
    if isinstance(filters, dict):
        required.update(flag for flag in AVAILABILITY_FLAGS if filters.get(flag))
    return required


def minimal_availability_requirements(
    group: Mapping[str, Any],
    canonical_factions: Mapping[int, int | None],
    declared_faction_ids_by_unit: Mapping[int, Collection[int]],
    army_id: int | None = None,
) -> tuple[frozenset[str], ...]:
    """Return non-redundant optional-mode requirements for one logical unit.

    Requirements are scoped to one application Army when ``army_id`` is supplied.
    If one path is a strict superset of another, the superset cannot affect
    visibility and is omitted from the summary.
    """
    requirements: set[frozenset[str]] = set()
    for occurrence in group["army_occurrences"]:
        if army_id is not None and occurrence["id"] != army_id:
            continue
        source_id = occurrence["source_id"]
        requirements.add(
            frozenset(
                army_required_flags(
                    occurrence,
                    group,
                    canonical_factions[source_id],
                    declared_faction_ids_by_unit[source_id],
                )
            )
        )

    if not requirements and army_id is None and not group["armies"]:
        requirements.add(frozenset())

    minimal = [
        required
        for required in requirements
        if not any(other < required for other in requirements)
    ]
    return tuple(sorted(minimal, key=lambda required: (len(required), sorted(required))))


def availability_summary(
    requirements_by_group: Iterable[tuple[frozenset[str], ...]],
    selected_flags: set[str],
) -> dict[str, Any]:
    """Summarize current and potential logical-unit visibility."""
    categories = {
        "standard": {"shown": 0, "filtered": 0},
        **{flag: {"shown": 0, "filtered": 0} for flag in AVAILABILITY_FLAGS},
    }
    shown = 0
    available = 0

    for requirements in requirements_by_group:
        if not requirements:
            continue
        available += 1
        satisfied = [required for required in requirements if required <= selected_flags]
        is_shown = bool(satisfied)
        if is_shown:
            shown += 1
            if any(not required for required in satisfied):
                categories["standard"]["shown"] += 1
            for flag in AVAILABILITY_FLAGS:
                if any(flag in required for required in satisfied):
                    categories[flag]["shown"] += 1
        else:
            for flag in AVAILABILITY_FLAGS:
                if any(flag in required for required in requirements):
                    categories[flag]["filtered"] += 1

    return {
        "shown": shown,
        "available": available,
        "filtered": available - shown,
        "categories": categories,
    }


def visible_armies_for_group(
    group: Mapping[str, Any],
    selected_flags: set[str],
    canonical_factions: Mapping[int, int | None],
    declared_faction_ids_by_unit: Mapping[int, Collection[int]],
) -> dict[int, dict[str, Any]]:
    """Collect armies that have at least one visible source occurrence.

    A logical unit can combine a normal source record with a generic mercenary
    or reinforcement record.  Availability must be evaluated before those
    occurrences are collapsed into one army symbol.
    """
    visible: dict[int, dict[str, Any]] = {}
    for occurrence in group["army_occurrences"]:
        source_id = occurrence["source_id"]
        flags = army_required_flags(
            occurrence,
            group,
            canonical_factions[source_id],
            declared_faction_ids_by_unit[source_id],
        )
        if flags <= selected_flags:
            visible.setdefault(occurrence["id"], occurrence)
    return visible


class Database:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        if not self.path.is_file():
            raise ValueError(f"Database does not exist: {self.path}. Build it before serving.")
        connection = sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.create_function("casefold", 1, lambda value: (value or "").casefold())
        connection.create_function("unit_sort_key", 1, unit_sort_key)
        try:
            connection.execute("BEGIN")
            yield connection
        finally:
            connection.close()

    @instance_lru_cache(maxsize=1)
    def _identity_config(self) -> IdentityConfig:
        with self._connect() as connection:
            return identity_config_from_connection(connection)

    @instance_lru_cache(maxsize=1)
    def _application_army_graph(self) -> dict[str, Any]:
        """Return the materialized application Army model and source mappings."""
        with self._connect() as connection:
            army_rows = [
                dict(row)
                for row in connection.execute(
                    "SELECT id, name, slug, role, playable, group_id, preferred_source_id "
                    "FROM application_armies ORDER BY id"
                )
            ]
            source_rows = [
                dict(row)
                for row in connection.execute(
                    "SELECT application_army_id, source_army_id, has_army_list, "
                    "has_metadata FROM application_army_sources ORDER BY source_army_id"
                )
            ]
            reinforcement_rows = [
                dict(row)
                for row in connection.execute(
                    "SELECT reinforcement_army_id, parent_army_id "
                    "FROM application_army_reinforcement_parents "
                    "ORDER BY reinforcement_army_id, parent_army_id"
                )
            ]
            source_kinds = {
                row["id"]: row["kind"]
                for row in connection.execute("SELECT id, kind FROM army_lists ORDER BY id")
            }

        armies = {row["id"]: row for row in army_rows}
        identities = {
            army_id: {"id": army_id, "name": row["name"], "slug": row["slug"]}
            for army_id, row in armies.items()
        }
        source_to_application = {
            row["source_army_id"]: row["application_army_id"] for row in source_rows
        }
        list_sources_by_application: dict[int, list[int]] = {}
        for row in source_rows:
            if row["has_army_list"]:
                list_sources_by_application.setdefault(row["application_army_id"], []).append(
                    row["source_army_id"]
                )

        reinforcement_parents: dict[int, list[int]] = {}
        for row in reinforcement_rows:
            reinforcement_parents.setdefault(row["reinforcement_army_id"], []).append(
                row["parent_army_id"]
            )

        def faction_id_for(army_id: int) -> int | None:
            army = armies.get(army_id)
            if army is None:
                return None
            group_id = army.get("group_id")
            if isinstance(group_id, int) and group_id in armies:
                return group_id
            if army.get("role") == ARMY_ROLE_REINFORCEMENT:
                roots = {
                    parent["group_id"] if isinstance(parent.get("group_id"), int) else parent_id
                    for parent_id in reinforcement_parents.get(army_id, [])
                    if (parent := armies.get(parent_id)) is not None
                }
                roots = {root for root in roots if root in armies}
                return next(iter(roots)) if len(roots) == 1 else None
            return army_id

        faction_identities = {
            army_id: identities.get(faction_id)
            for army_id in armies
            if (faction_id := faction_id_for(army_id)) is not None
        }
        source_list_ids: dict[int, int] = {}
        for application_id, source_ids in list_sources_by_application.items():
            source_list_ids[application_id] = (
                application_id if application_id in source_ids else min(source_ids)
            )

        return {
            "armies": armies,
            "identities": identities,
            "faction_identities": faction_identities,
            "source_to_application": source_to_application,
            "source_list_ids": source_list_ids,
            "source_kinds": source_kinds,
            "reinforcement_parents": reinforcement_parents,
        }

    @instance_lru_cache(maxsize=4)
    def _application_catalog_graph(self, catalog: str) -> dict[str, Any]:
        """Return one materialized application catalog and its source mappings."""
        if catalog not in {"skills", "equipment", "weapons"}:
            raise ValueError(f"Unknown catalog: {catalog}")
        with self._connect() as connection:
            item_rows = [
                dict(row)
                for row in connection.execute(
                    "SELECT catalog, id, name, wiki, category, preferred_source_id "
                    "FROM application_catalog_items WHERE catalog = ? ORDER BY id",
                    (catalog,),
                )
            ]
            source_rows = [
                dict(row)
                for row in connection.execute(
                    "SELECT catalog, application_item_id, source_item_id, source_name, has_metadata "
                    "FROM application_catalog_sources WHERE catalog = ? "
                    "ORDER BY application_item_id, source_item_id",
                    (catalog,),
                )
            ]
            weapon_metadata_rows = []
            if catalog == "weapons":
                weapon_metadata_rows = [
                    dict(row)
                    for row in connection.execute(
                        "SELECT s.application_item_id AS id, "
                        "GROUP_CONCAT(DISTINCT NULLIF(m.type, '')) AS type, "
                        "GROUP_CONCAT(DISTINCT NULLIF(m.ammunition, '')) AS ammunition, "
                        "GROUP_CONCAT(DISTINCT NULLIF(m.properties, '')) AS properties "
                        "FROM application_catalog_sources AS s "
                        "LEFT JOIN metadata_weapons AS m ON m.id = s.source_item_id "
                        "WHERE s.catalog = 'weapons' GROUP BY s.application_item_id"
                    )
                ]
        items = {row["id"]: row for row in item_rows}
        if catalog == "weapons":
            for row in weapon_metadata_rows:
                item = items.get(row["id"])
                if item is not None:
                    item.update(
                        {
                            "type": row["type"],
                            "ammunition": row["ammunition"],
                            "properties": row["properties"],
                        }
                    )
        source_ids_by_item: dict[int, tuple[int, ...]] = {}
        source_names_by_item: dict[int, dict[int, str]] = {}
        source_to_item: dict[int, int] = {}
        for item_id in items:
            source_ids = tuple(
                row["source_item_id"]
                for row in source_rows
                if row["application_item_id"] == item_id
            )
            source_ids_by_item[item_id] = source_ids
            source_names_by_item[item_id] = {
                row["source_item_id"]: row["source_name"]
                for row in source_rows
                if row["application_item_id"] == item_id
            }
            for source_id in source_ids:
                source_to_item[source_id] = item_id
        return {
            "items": items,
            "ordered_items": [items[row["id"]] for row in item_rows],
            "source_ids_by_item": source_ids_by_item,
            "source_names_by_item": source_names_by_item,
            "source_to_item": source_to_item,
        }

    @instance_lru_cache(maxsize=1)
    def _faction_groups(self) -> dict[int, dict[str, Any]]:
        """Return application faction/group identities keyed by source or application Army ID."""
        graph = self._application_army_graph()
        groups = dict(graph["faction_identities"])
        for source_id, application_id in graph["source_to_application"].items():
            faction = graph["faction_identities"].get(application_id)
            if faction is not None:
                groups[source_id] = faction
        return groups

    @instance_lru_cache(maxsize=1)
    def _faction_identities(self) -> dict[int, dict[str, Any]]:
        """Return exact application Army identities keyed by source or application Army ID."""
        graph = self._application_army_graph()
        identities = dict(graph["identities"])
        for source_id, application_id in graph["source_to_application"].items():
            identity = graph["identities"].get(application_id)
            if identity is not None:
                identities[source_id] = identity
        return identities

    def validate(self, *, source_consistency: bool = False) -> None:
        """Reject missing, unrelated, unsupported, incomplete, or corrupt databases.

        Normal runtime validation uses only the self-contained published application
        schema. Export staging additionally enables ``source_consistency`` so every
        canonical/materialized layer is cross-checked against the full normalized
        relational source before publication.
        """
        with self._connect() as connection:
            application_id = connection.execute("PRAGMA application_id").fetchone()[0]
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if application_id != APPLICATION_ID or version != SCHEMA_VERSION:
                raise ValueError("Unsupported InfinityDB database; rebuild it from normalized JSON")
            required_tables = (
                DATABASE_TABLES if source_consistency else PUBLISHED_DATABASE_TABLES
            )
            for name, definition in required_tables.items():
                columns = {
                    row["name"] for row in connection.execute(f"PRAGMA table_info({quote(name)})")
                }
                if not {*definition.key, *definition.fields} <= columns:
                    raise ValueError(f"Incomplete database schema: {name}; rebuild the database")
            row = connection.execute(
                f"SELECT value FROM {quote(METADATA_TABLE)} WHERE key = ?", ("_meta",)
            ).fetchone()
            try:
                meta = json.loads(row["value"]) if row else None
            except (json.JSONDecodeError, TypeError) as exc:
                raise ValueError("Database has invalid import metadata") from exc
            if (
                not isinstance(meta, dict)
                or meta.get("format") != FORMAT_NAME
                or meta.get("formatVersion") != FORMAT_VERSION
            ):
                raise ValueError("Database has invalid normalized format metadata")
            compatibility = connection.execute(
                f"SELECT value FROM {quote(METADATA_TABLE)} WHERE key = ?",
                (DATABASE_COMPATIBILITY_KEY,),
            ).fetchone()
            try:
                compatibility_version = (
                    json.loads(compatibility["value"]) if compatibility else None
                )
            except (json.JSONDecodeError, TypeError) as exc:
                raise ValueError("Database has invalid compatibility metadata") from exc
            if compatibility_version != DATABASE_COMPATIBILITY_VERSION:
                raise ValueError(
                    "Database compatibility revision does not match this application; "
                    "rebuild the database"
                )
            identity_config = identity_config_from_connection(connection)
            validate_application_army_integrity(connection)
            validate_application_fireteam_integrity(connection)
            if source_consistency:
                validate_application_armies(connection, identity_config)
                validate_application_fireteams(connection)
            validate_application_catalogs(connection, identity_config)
            validate_application_domain_slugs(connection)
            source_unit_count = connection.execute(
                "SELECT COUNT(*) FROM units WHERE source_defined = 1"
            ).fetchone()[0]
            mapped_source_count = connection.execute(
                "SELECT COUNT(*) FROM logical_unit_sources"
            ).fetchone()[0]
            invalid_mapping = connection.execute(
                "SELECT 1 FROM logical_unit_sources AS lus "
                "JOIN units AS u ON u.id = lus.source_unit_id "
                "WHERE u.source_defined != 1 LIMIT 1"
            ).fetchone()
            invalid_representative = connection.execute(
                "SELECT 1 FROM logical_units AS lu "
                "LEFT JOIN logical_unit_sources AS lus "
                "ON lus.source_unit_id = lu.representative_unit_id "
                "AND lus.logical_unit_id = lu.id "
                "WHERE lu.id != lu.representative_unit_id "
                "OR lus.source_unit_id IS NULL LIMIT 1"
            ).fetchone()
            empty_logical_unit = connection.execute(
                "SELECT 1 FROM logical_units AS lu "
                "LEFT JOIN logical_unit_sources AS lus ON lus.logical_unit_id = lu.id "
                "WHERE lus.source_unit_id IS NULL LIMIT 1"
            ).fetchone()
            if (
                source_unit_count != mapped_source_count
                or invalid_mapping is not None
                or invalid_representative is not None
                or empty_logical_unit is not None
            ):
                raise ValueError(
                    "Database has invalid materialized logical-unit identity; rebuild the database"
                )
            _validate_logical_unit_payloads(connection)

            profile_occurrence_count = connection.execute(
                "SELECT COUNT(*) FROM profile_payload_occurrences"
            ).fetchone()[0]
            unsupported_payload = connection.execute(
                "SELECT 1 FROM profile_payloads AS pp "
                "LEFT JOIN profile_payload_occurrences AS ppo "
                "ON ppo.profile_payload_id = pp.id "
                "WHERE ppo.profile_payload_id IS NULL "
                "OR pp.payload_sha256 IS NULL "
                "OR length(pp.payload_sha256) != 64 LIMIT 1"
            ).fetchone()
            invalid_profile_logical_unit = connection.execute(
                "SELECT 1 FROM profile_payload_occurrences AS ppo "
                "JOIN profile_payloads AS pp ON pp.id = ppo.profile_payload_id "
                "JOIN logical_unit_sources AS lus ON lus.source_unit_id = ppo.unit_id "
                "WHERE pp.logical_unit_id != lus.logical_unit_id LIMIT 1"
            ).fetchone()
            invalid_profile_source = None
            if source_consistency:
                source_profile_count = connection.execute(
                    "SELECT COUNT(*) FROM profiles"
                ).fetchone()[0]
                invalid_profile_context = connection.execute(
                    "SELECT 1 FROM profile_payload_occurrences AS ppo "
                    "JOIN profiles AS p "
                    "ON p.army_id = ppo.army_id "
                    "AND p.unit_id = ppo.unit_id "
                    "AND p.group_id = ppo.group_id "
                    "AND p.profile_id = ppo.profile_id "
                    "WHERE NOT (ppo.position IS p.position) "
                    "OR NOT (ppo.ava IS p.ava) "
                    "OR NOT (ppo.logo IS p.logo) LIMIT 1"
                ).fetchone()
                if source_profile_count != profile_occurrence_count:
                    invalid_profile_source = True
            else:
                invalid_profile_context = None
            if (
                unsupported_payload is not None
                or invalid_profile_logical_unit is not None
                or invalid_profile_context is not None
                or invalid_profile_source is not None
            ):
                raise ValueError(
                    "Database has invalid materialized canonical profile payloads; "
                    "rebuild the database"
                )

            loadout_occurrence_count = connection.execute(
                "SELECT COUNT(*) FROM loadout_payload_occurrences"
            ).fetchone()[0]
            unsupported_loadout_payload = connection.execute(
                "SELECT 1 FROM loadout_payloads AS lp "
                "LEFT JOIN loadout_payload_occurrences AS lpo "
                "ON lpo.loadout_payload_id = lp.id "
                "WHERE lpo.loadout_payload_id IS NULL "
                "OR lp.payload_sha256 IS NULL "
                "OR length(lp.payload_sha256) != 64 LIMIT 1"
            ).fetchone()
            invalid_loadout_logical_unit = connection.execute(
                "SELECT 1 FROM loadout_payload_occurrences AS lpo "
                "JOIN loadout_payloads AS lp ON lp.id = lpo.loadout_payload_id "
                "JOIN logical_unit_sources AS lus ON lus.source_unit_id = lpo.unit_id "
                "WHERE lp.logical_unit_id != lus.logical_unit_id LIMIT 1"
            ).fetchone()
            invalid_loadout_source = None
            if source_consistency:
                source_loadout_count = connection.execute(
                    "SELECT COUNT(*) FROM loadout_options"
                ).fetchone()[0]
                invalid_loadout_context = connection.execute(
                    "SELECT 1 FROM loadout_payload_occurrences AS lpo "
                    "JOIN loadout_options AS o "
                    "ON o.army_id = lpo.army_id "
                    "AND o.unit_id = lpo.unit_id "
                    "AND o.group_id = lpo.group_id "
                    "AND o.option_id = lpo.option_id "
                    "WHERE NOT (lpo.position IS o.position) "
                    "OR NOT (lpo.points IS o.points) "
                    "OR NOT (lpo.swc IS o.swc) LIMIT 1"
                ).fetchone()
                if source_loadout_count != loadout_occurrence_count:
                    invalid_loadout_source = True
            else:
                invalid_loadout_context = None
            if (
                unsupported_loadout_payload is not None
                or invalid_loadout_logical_unit is not None
                or invalid_loadout_context is not None
                or invalid_loadout_source is not None
            ):
                raise ValueError(
                    "Database has invalid materialized canonical loadout payloads; "
                    "rebuild the database"
                )

            if source_consistency:
                validate_include_relationships(connection)
                validate_peripheral_relationships(connection)
                validate_relation_constraints(connection)
                validate_relation_group_dependencies(connection)

            checksum_row = connection.execute(
                f"SELECT value FROM {quote(METADATA_TABLE)} WHERE key = ?",
                (PUBLISHED_CONTENT_SHA256_KEY,),
            ).fetchone()
            try:
                expected_checksum = json.loads(checksum_row["value"]) if checksum_row else None
            except (json.JSONDecodeError, TypeError) as exc:
                raise ValueError(
                    "Database has invalid published content checksum metadata"
                ) from exc
            if (
                not isinstance(expected_checksum, str)
                or len(expected_checksum) != 64
                or published_content_sha256(connection) != expected_checksum
            ):
                raise ValueError(
                    "Database published application content does not match its validated checksum; "
                    "rebuild the database"
                )

            if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Database integrity check failed")
            if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise ValueError("Database contains broken foreign keys")

    def snapshot_downloaded_on(self) -> date | None:
        """Return the raw snapshot's download date, when recorded by the build."""
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT value FROM {quote(METADATA_TABLE)} WHERE key = ?", ("_meta",)
            ).fetchone()
        try:
            value = json.loads(row["value"]).get("snapshotDownloadedOn") if row else None
            return date.fromisoformat(value) if isinstance(value, str) else None
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    @instance_lru_cache(maxsize=1)
    def _unit_graph(self) -> dict[str, Any]:
        """Load canonical logical-unit fields plus source-specific relationships."""
        application_armies = self._application_army_graph()
        with self._connect() as connection:
            source_rows = connection.execute(
                "SELECT lus.source_unit_id AS id, lus.logical_unit_id, u.canonical_faction_id "
                "FROM logical_unit_sources AS lus "
                "JOIN units AS u ON u.id = lus.source_unit_id "
                "ORDER BY lus.source_unit_id"
            ).fetchall()
            source_to_logical = {
                row["id"]: row["logical_unit_id"] for row in source_rows
            }
            logical_rows = connection.execute(
                "SELECT lu.id AS logical_unit_id, lu.representative_unit_id, "
                "COALESCE(NULLIF(lu.name, ''), 'Unit ' || lu.id) AS name, "
                "lu.isc, lu.isc_abbr, lu.slug, lu.canonical_faction_id, "
                "lu.main_army_id, lu.display_army_id, n.note AS notes "
                "FROM logical_units AS lu "
                "LEFT JOIN logical_unit_notes AS n "
                "ON n.logical_unit_id = lu.id "
                "AND n.source_unit_id = lu.representative_unit_id "
                "ORDER BY lu.id"
            ).fetchall()
            sources_by_logical: dict[int, list[int]] = {
                row["logical_unit_id"]: [] for row in logical_rows
            }
            for row in source_rows:
                sources_by_logical[row["logical_unit_id"]].append(row["id"])

            search_terms_by_logical = {
                row["logical_unit_id"]: {
                    row["name"],
                    row["isc"],
                    row["isc_abbr"],
                    row["slug"],
                }
                for row in logical_rows
            }
            names_by_logical = {
                row["logical_unit_id"]: [row["name"]] for row in logical_rows
            }
            for alias in connection.execute(
                "SELECT logical_unit_id, field, value FROM logical_unit_aliases "
                "ORDER BY logical_unit_id, source_unit_id, field"
            ):
                search_terms_by_logical[alias["logical_unit_id"]].add(alias["value"])
                if alias["field"] == "name":
                    names = names_by_logical[alias["logical_unit_id"]]
                    if alias["value"] not in names:
                        names.append(alias["value"])

            for query in (
                "SELECT ppo.unit_id, pp.name "
                "FROM profile_payload_occurrences AS ppo "
                "JOIN profile_payloads AS pp ON pp.id = ppo.profile_payload_id",
                "SELECT lpo.unit_id, lp.name "
                "FROM loadout_payload_occurrences AS lpo "
                "JOIN loadout_payloads AS lp ON lp.id = lpo.loadout_payload_id",
                "SELECT unit_id, name FROM unit_options",
            ):
                for row in connection.execute(query):
                    logical_id = source_to_logical.get(row["unit_id"])
                    if logical_id is not None:
                        search_terms_by_logical[logical_id].add(row["name"])

            memberships: dict[int, list[dict[str, Any]]] = {
                row["id"]: [] for row in source_rows
            }
            army_names = {
                army_id: row["name"]
                for army_id, row in application_armies["armies"].items()
            }
            for source_id, application_id in application_armies[
                "source_to_application"
            ].items():
                identity = application_armies["armies"].get(application_id)
                if identity is not None:
                    army_names[source_id] = identity["name"]
            for army in connection.execute(
                "SELECT au.unit_id, au.army_id AS source_army_id, au.filters, "
                "au.availability_kind, aa.id, aa.name, aa.role "
                "FROM army_units AS au "
                "JOIN application_army_sources AS aas "
                "ON aas.source_army_id = au.army_id AND aas.has_army_list = 1 "
                "JOIN application_armies AS aa ON aa.id = aas.application_army_id "
                "ORDER BY aa.id, au.army_id"
            ):
                if army["unit_id"] not in memberships:
                    continue
                try:
                    filters = json.loads(army["filters"]) if army["filters"] else {}
                except (TypeError, json.JSONDecodeError):
                    filters = {}
                memberships[army["unit_id"]].append(
                    {
                        "id": army["id"],
                        "source_army_id": army["source_army_id"],
                        "name": army["name"],
                        "role": army["role"],
                        "kind": application_armies["source_kinds"].get(
                            army["source_army_id"]
                        ),
                        "filters": filters,
                        "availability_kind": army["availability_kind"],
                    }
                )
            declared_faction_ids_by_unit: dict[int, set[int]] = {
                row["id"]: set() for row in source_rows
            }
            for faction in connection.execute("SELECT unit_id, faction_id FROM unit_factions"):
                if faction["unit_id"] in declared_faction_ids_by_unit:
                    declared_faction_ids_by_unit[faction["unit_id"]].add(
                        faction["faction_id"]
                    )

        groups: list[dict[str, Any]] = []
        for logical in logical_rows:
            logical_id = logical["logical_unit_id"]
            source_ids = sources_by_logical[logical_id]
            group: dict[str, Any] = {
                "id": logical_id,
                "name": logical["name"],
                "isc": logical["isc"],
                "isc_abbr": logical["isc_abbr"],
                "slug": logical["slug"],
                "notes": logical["notes"],
                "canonical_faction_id": logical["canonical_faction_id"],
                "main_army_id": logical["main_army_id"],
                "display_army_id": logical["display_army_id"],
                "source_ids": source_ids,
                "names": names_by_logical[logical_id],
                "armies": {},
                "army_occurrences": [],
            }
            for source_id in source_ids:
                for army in memberships[source_id]:
                    source_army_id = army["source_army_id"]
                    application_army_id = army["id"]
                    if (
                        application_army_id not in group["armies"]
                        or source_army_id == application_army_id
                    ):
                        group["armies"][application_army_id] = army
                    group["army_occurrences"].append(
                        {
                            **army,
                            "source_id": source_id,
                        }
                    )
            group["declared_faction_ids"] = set().union(
                *(declared_faction_ids_by_unit[source_id] for source_id in source_ids)
            )
            group["search_terms"] = search_terms_by_logical[logical_id]
            groups.append(group)

        groups_by_source = {
            source_id: group for group in groups for source_id in group["source_ids"]
        }
        return {
            "rows": source_rows,
            "army_names": army_names,
            "declared_faction_ids_by_unit": declared_faction_ids_by_unit,
            "groups": groups,
            "groups_by_source": groups_by_source,
        }

    @instance_lru_cache(maxsize=16)
    def _visible_unit_items_by_source(
        self, selected_flags: frozenset[str]
    ) -> dict[int, dict[str, Any]]:
        """Map every visible source unit to its logical-unit list item."""
        graph = self._unit_graph()
        faction_groups = self._faction_groups()
        faction_identities = self._faction_identities()
        canonical_factions = {row["id"]: row["canonical_faction_id"] for row in graph["rows"]}
        declared_faction_ids_by_unit = graph["declared_faction_ids_by_unit"]
        items_by_source: dict[int, dict[str, Any]] = {}
        for group in graph["groups"]:
            visible_armies = visible_armies_for_group(
                group,
                set(selected_flags),
                canonical_factions,
                declared_faction_ids_by_unit,
            )
            if group["armies"] and not visible_armies:
                continue
            item = {
                "id": group["id"],
                "name": group["name"],
                "isc": group["isc"],
                "slug": group["slug"],
                "main_army_id": group["main_army_id"],
                "main_army_name": graph["army_names"].get(group["main_army_id"]),
                "main_faction": faction_groups.get(group["main_army_id"]),
                "display_army_id": group["display_army_id"],
                "display_army_name": (
                    faction_identities.get(group["display_army_id"], {}).get("name")
                    or graph["army_names"].get(group["display_army_id"])
                ),
                "display_faction": faction_identities.get(group["display_army_id"]),
                "source_ids": group["source_ids"],
                "army_ids": list(visible_armies),
                "armies": [
                    {"id": army["id"], "name": army["name"]} for army in visible_armies.values()
                ],
            }
            for source_id in group["source_ids"]:
                items_by_source[source_id] = item
        return items_by_source

    @instance_lru_cache(maxsize=512)
    def application_id_for_slug(self, domain: str, slug: str) -> int | None:
        """Resolve one domain-local slug to the current application numeric key."""

        if domain not in APPLICATION_SLUG_DOMAINS:
            raise ValueError(f"Unknown slug domain: {domain}")
        slug = require_domain_slug(slug, context=f"{domain} slug")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT application_id FROM application_domain_slugs "
                "WHERE domain = ? AND status = 'resolved' "
                "AND slug = ? COLLATE NOCASE",
                (domain, slug),
            ).fetchone()
        return None if row is None else int(row["application_id"])

    @instance_lru_cache(maxsize=1024)
    def application_domain_id(self, domain: str, item_ref: int | str) -> int | None:
        """Resolve one source/application numeric ID or public slug to application identity."""

        if domain not in APPLICATION_SLUG_DOMAINS:
            raise ValueError(f"Unknown slug domain: {domain}")
        context = {
            "armies": "army_id",
            "units": "unit_id",
            "skills": "skill_id",
            "equipment": "equipment_id",
            "weapons": "weapon_id",
        }[domain]
        if isinstance(item_ref, str):
            slug = require_domain_slug(item_ref, context=context)
            if slug.isdigit():
                raise ValueError(
                    f"{context} numeric references must be integers, not strings"
                )
            return self.application_id_for_slug(domain, slug)
        if type(item_ref) is not int:
            raise ValueError(f"{context} must be an integer or domain-local slug")

        if domain == "armies":
            if not SQLITE_INTEGER_MIN <= item_ref <= SQLITE_INTEGER_MAX:
                raise ValueError(
                    "army_id must be an integer within SQLite's signed 64-bit range"
                )
            graph = self._application_army_graph()
            application_id = graph["source_to_application"].get(item_ref, item_ref)
            return application_id if application_id in graph["armies"] else None

        if not 0 <= item_ref <= SQLITE_INTEGER_MAX:
            raise ValueError(
                f"{domain} identifier must be a nonnegative SQLite signed 64-bit integer"
            )
        if domain == "units":
            graph = self._unit_graph()
            group = graph["groups_by_source"].get(item_ref)
            if group is not None:
                return int(group["id"])
            return next(
                (int(group["id"]) for group in graph["groups"] if group["id"] == item_ref),
                None,
            )

        graph = self._application_catalog_graph(domain)
        return item_ref if item_ref in graph["items"] else graph["source_to_item"].get(item_ref)

    @instance_lru_cache(maxsize=512)
    def application_army_id(self, army_ref: int | str) -> int | None:
        """Resolve a source/application Army ID or public slug to application identity."""

        return self.application_domain_id("armies", army_ref)

    @instance_lru_cache(maxsize=512)
    def application_unit_id(self, unit_ref: int | str) -> int | None:
        """Resolve a source/application Unit ID or public slug to application identity."""

        return self.application_domain_id("units", unit_ref)

    @instance_lru_cache(maxsize=512)
    def application_catalog_id(self, catalog: str, item_ref: int | str) -> int | None:
        """Resolve a source/application catalog ID or public slug to application identity."""

        if catalog not in {"skills", "equipment", "weapons"}:
            raise ValueError(f"Unknown catalog: {catalog}")
        return self.application_domain_id(catalog, item_ref)

    @instance_lru_cache(maxsize=512)
    def application_slug(self, domain: str, application_id: int) -> str | None:
        """Return the current domain-local slug for one application identity."""

        if domain not in APPLICATION_SLUG_DOMAINS:
            raise ValueError(f"Unknown slug domain: {domain}")
        if type(application_id) is not int or not 0 <= application_id <= SQLITE_INTEGER_MAX:
            raise ValueError(
                "application_id must be an integer within SQLite's signed 64-bit range"
            )
        with self._connect() as connection:
            row = connection.execute(
                "SELECT slug FROM application_domain_slugs "
                "WHERE domain = ? AND application_id = ? AND status = 'resolved'",
                (domain, application_id),
            ).fetchone()
        return None if row is None or row["slug"] is None else str(row["slug"])

    @instance_lru_cache(maxsize=1)
    def list_hacking_programs(self) -> list[dict[str, Any]]:
        """Return structured Army Hacking Program reference rows."""

        with self._connect() as connection:
            programs = [
                dict(row)
                for row in connection.execute(
                    "SELECT position, name, attack_mod, opponent_mod, ps, burst, special "
                    "FROM application_hacking_programs "
                    "ORDER BY position"
                )
            ]
            device_rows = [
                dict(row)
                for row in connection.execute(
                    "SELECT program_position, position, source_equipment_id, "
                    "source_equipment_name FROM application_hacking_program_devices "
                    "ORDER BY program_position, position"
                )
            ]
            target_rows = [
                dict(row)
                for row in connection.execute(
                    "SELECT program_position, position, target "
                    "FROM application_hacking_program_targets "
                    "ORDER BY program_position, position"
                )
            ]
            skill_type_rows = [
                dict(row)
                for row in connection.execute(
                    "SELECT program_position, position, skill_type "
                    "FROM application_hacking_program_skill_types "
                    "ORDER BY program_position, position"
                )
            ]

        devices_by_program: dict[int, list[dict[str, Any]]] = {}
        equipment_graph = self._application_catalog_graph("equipment")
        for row in device_rows:
            source_id = int(row["source_equipment_id"])
            application_id = equipment_graph["source_to_item"].get(source_id)
            name = row.get("source_equipment_name")
            slug = None
            if application_id is not None:
                application_item = equipment_graph["items"].get(application_id)
                if application_item is not None:
                    name = application_item["name"]
                slug = self.application_slug("equipment", int(application_id))
            devices_by_program.setdefault(int(row["program_position"]), []).append(
                {
                    "source_id": source_id,
                    "id": application_id,
                    "slug": slug,
                    "name": name or f"Equipment #{source_id}",
                }
            )

        targets_by_program: dict[int, list[str]] = {}
        for row in target_rows:
            targets_by_program.setdefault(int(row["program_position"]), []).append(
                str(row["target"])
            )
        skill_types_by_program: dict[int, list[str]] = {}
        for row in skill_type_rows:
            skill_types_by_program.setdefault(int(row["program_position"]), []).append(
                str(row["skill_type"])
            )

        for program in programs:
            position = int(program["position"])
            program["devices"] = devices_by_program.get(position, [])
            program["targets"] = targets_by_program.get(position, [])
            program["skill_types"] = skill_types_by_program.get(position, [])
        return programs

    @instance_lru_cache(maxsize=1)
    def list_martial_arts_levels(self) -> list[dict[str, Any]]:
        """Return the structured Army Martial Arts level chart."""

        with self._connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    "SELECT position, level, attack_mod, opponent_mod, ps_mod, burst_mod "
                    "FROM application_martial_arts_levels ORDER BY position"
                )
            ]

    def _list_random_reference_results(self, table_name: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    f'SELECT id, roll, result FROM "{table_name}" ORDER BY id'
                )
            ]

    @instance_lru_cache(maxsize=1)
    def list_metachemistry_results(self) -> list[dict[str, Any]]:
        """Return the structured Army MetaChemistry roll chart."""

        return self._list_random_reference_results("application_metachemistry_results")

    @instance_lru_cache(maxsize=1)
    def list_booty_results(self) -> list[dict[str, Any]]:
        """Return the structured Army Booty roll chart."""

        return self._list_random_reference_results("application_booty_results")

    @instance_lru_cache(maxsize=1)
    def list_armies(self) -> list[dict[str, Any]]:
        """Return canonical application Armies with current logical-unit counts."""
        graph = self._application_army_graph()
        logical_unit_ids: dict[int, set[int]] = {
            army_id: set() for army_id in graph["armies"]
        }
        with self._connect() as connection:
            for row in connection.execute(
                "SELECT aas.application_army_id, lus.logical_unit_id "
                "FROM army_units AS au "
                "JOIN application_army_sources AS aas "
                "ON aas.source_army_id = au.army_id AND aas.has_army_list = 1 "
                "JOIN logical_unit_sources AS lus ON lus.source_unit_id = au.unit_id "
                "ORDER BY aas.application_army_id, lus.logical_unit_id"
            ):
                logical_unit_ids.setdefault(row["application_army_id"], set()).add(
                    row["logical_unit_id"]
                )

        items = []
        for army_id, army in sorted(graph["armies"].items()):
            group = graph["identities"].get(army["group_id"])
            source_list_id = graph["source_list_ids"].get(army_id)
            kind = (
                graph["source_kinds"].get(source_list_id)
                if source_list_id is not None
                else "grouping"
            )
            items.append(
                {
                    "id": army_id,
                    "name": army["name"],
                    "slug": army["slug"],
                    "kind": kind,
                    "role": army["role"],
                    "playable": bool(army["playable"]),
                    "group_id": army["group_id"],
                    "group_name": group.get("name") if group is not None else None,
                    "group_slug": group.get("slug") if group is not None else None,
                    "parent_army_ids": list(graph["reinforcement_parents"].get(army_id, [])),
                    "unit_count": len(logical_unit_ids.get(army_id, set())),
                }
            )
        return items

    @instance_lru_cache(maxsize=1)
    def list_fireteam_armies(self) -> list[dict[str, Any]]:
        """Return playable Armies that have player-facing Fireteam chart content."""

        armies = {item["id"]: item for item in self.list_armies()}
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT c.application_army_id, COUNT(DISTINCT f.fireteam_id) AS fireteam_count, "
                "MAX(CASE WHEN l.raw_limit > 0 THEN 1 ELSE 0 END) AS has_positive_limit, "
                "CASE WHEN COALESCE(c.description, '') != '' THEN 1 ELSE 0 END "
                "AS has_description "
                "FROM application_fireteam_charts AS c "
                "LEFT JOIN application_fireteams AS f "
                "ON f.application_army_id = c.application_army_id "
                "LEFT JOIN application_fireteam_chart_limits AS l "
                "ON l.application_army_id = c.application_army_id "
                "GROUP BY c.application_army_id, c.description "
                "ORDER BY c.application_army_id"
            ).fetchall()

        result: list[dict[str, Any]] = []
        for row in rows:
            army = armies.get(int(row["application_army_id"]))
            if army is None or not army["playable"]:
                continue
            if not (
                int(row["fireteam_count"])
                or bool(row["has_positive_limit"])
                or bool(row["has_description"])
            ):
                continue
            item = dict(army)
            item["fireteam_count"] = int(row["fireteam_count"])
            result.append(item)
        return result

    @instance_lru_cache(maxsize=256)
    def get_fireteam_chart(self, army_ref: int | str) -> dict[str, Any] | None:
        """Return one authoritative Army-scoped Fireteam chart projection."""

        army_id = self.application_army_id(army_ref)
        if army_id is None:
            return None
        army = next((item for item in self.list_armies() if item["id"] == army_id), None)
        if army is None:
            return None

        with self._connect() as connection:
            chart = connection.execute(
                "SELECT application_army_id, source_army_id, source_kind, source_file, "
                "source_sha256, description FROM application_fireteam_charts "
                "WHERE application_army_id = ?",
                (army_id,),
            ).fetchone()
            if chart is None:
                return None
            limits = [
                dict(row)
                for row in connection.execute(
                    "SELECT fireteam_type, position, raw_limit "
                    "FROM application_fireteam_chart_limits "
                    "WHERE application_army_id = ? ORDER BY position, fireteam_type",
                    (army_id,),
                )
            ]
            team_rows = [
                dict(row)
                for row in connection.execute(
                    "SELECT fireteam_id, position, name, observation, source_army_id, "
                    "source_fireteam_id, is_wildcard FROM application_fireteams "
                    "WHERE application_army_id = ? ORDER BY position, fireteam_id",
                    (army_id,),
                )
            ]
            type_rows = [
                dict(row)
                for row in connection.execute(
                    "SELECT fireteam_id, position, fireteam_type "
                    "FROM application_fireteam_types WHERE application_army_id = ? "
                    "ORDER BY fireteam_id, position",
                    (army_id,),
                )
            ]
            member_rows = [
                dict(row)
                for row in connection.execute(
                    "SELECT m.fireteam_id, m.member_id, m.position, m.source_member_id, "
                    "m.slug, m.name, m.comment, m.min_count, m.max_count, m.required, "
                    "m.source_unit_id, m.logical_unit_id, m.resolution, m.fto_marker, "
                    "lu.name AS logical_unit_name, uds.slug AS logical_unit_slug "
                    "FROM application_fireteam_members AS m "
                    "LEFT JOIN logical_units AS lu ON lu.id = m.logical_unit_id "
                    "LEFT JOIN application_domain_slugs AS uds "
                    "ON uds.domain = 'units' AND uds.application_id = m.logical_unit_id "
                    "AND uds.status = 'resolved' "
                    "WHERE m.application_army_id = ? "
                    "ORDER BY m.fireteam_id, m.position, m.member_id",
                    (army_id,),
                )
            ]
            loadout_rows = [
                dict(row)
                for row in connection.execute(
                    "SELECT fireteam_id, member_id, position, loadout_payload_id, option_name, "
                    "fto_marker FROM application_fireteam_member_loadouts "
                    "WHERE application_army_id = ? "
                    "ORDER BY fireteam_id, member_id, position",
                    (army_id,),
                )
            ]
            equivalence_rows = [
                dict(row)
                for row in connection.execute(
                    "SELECT fireteam_id, member_id, position, label "
                    "FROM application_fireteam_member_equivalence_labels "
                    "WHERE application_army_id = ? "
                    "ORDER BY fireteam_id, member_id, position",
                    (army_id,),
                )
            ]

        types_by_team: dict[int, list[str]] = {}
        for row in type_rows:
            types_by_team.setdefault(int(row["fireteam_id"]), []).append(
                str(row["fireteam_type"])
            )
        loadouts_by_member: dict[tuple[int, int], list[dict[str, Any]]] = {}
        for row in loadout_rows:
            loadouts_by_member.setdefault(
                (int(row["fireteam_id"]), int(row["member_id"])), []
            ).append(
                {
                    "position": int(row["position"]),
                    "loadout_payload_id": int(row["loadout_payload_id"]),
                    "name": row["option_name"],
                    "fto_marker": row["fto_marker"],
                }
            )
        equivalence_by_member: dict[tuple[int, int], list[str]] = {}
        for row in equivalence_rows:
            equivalence_by_member.setdefault(
                (int(row["fireteam_id"]), int(row["member_id"])), []
            ).append(str(row["label"]))
        members_by_team: dict[int, list[dict[str, Any]]] = {}
        for row in member_rows:
            fireteam_id = int(row["fireteam_id"])
            member_id = int(row["member_id"])
            logical_unit_id = row["logical_unit_id"]
            unit = None
            if type(logical_unit_id) is int:
                unit = {
                    "id": logical_unit_id,
                    "slug": row["logical_unit_slug"],
                    "name": row["logical_unit_name"],
                }
            members_by_team.setdefault(fireteam_id, []).append(
                {
                    "id": member_id,
                    "position": int(row["position"]),
                    "source_member_id": int(row["source_member_id"]),
                    "slug": row["slug"],
                    "name": row["name"],
                    "comment": row["comment"],
                    "min_count": row["min_count"],
                    "max_count": row["max_count"],
                    "required": bool(row["required"]),
                    "resolution": row["resolution"],
                    "fto_marker": row["fto_marker"],
                    "source_unit_id": row["source_unit_id"],
                    "unit": unit,
                    "loadouts": loadouts_by_member.get((fireteam_id, member_id), []),
                    "equivalence_labels": equivalence_by_member.get(
                        (fireteam_id, member_id), []
                    ),
                }
            )

        teams = []
        for row in team_rows:
            fireteam_id = int(row["fireteam_id"])
            teams.append(
                {
                    "id": fireteam_id,
                    "position": int(row["position"]),
                    "name": row["name"],
                    "observation": row["observation"],
                    "source_army_id": int(row["source_army_id"]),
                    "source_fireteam_id": int(row["source_fireteam_id"]),
                    "is_wildcard": bool(row["is_wildcard"]),
                    "types": types_by_team.get(fireteam_id, []),
                    "members": members_by_team.get(fireteam_id, []),
                }
            )

        return {
            "army": dict(army),
            "source": {
                "army_id": int(chart["source_army_id"]),
                "kind": chart["source_kind"],
                "file": chart["source_file"],
                "sha256": chart["source_sha256"],
            },
            "description": chart["description"],
            "limits": [
                {
                    "type": row["fireteam_type"],
                    "position": int(row["position"]),
                    "max_count": int(row["raw_limit"]),
                }
                for row in limits
            ],
            "teams": teams,
        }

    @instance_lru_cache(maxsize=1)
    def list_skill_extras(self) -> list[dict[str, Any]]:
        """Return candidate distance-related skill and extra pairings."""
        with self._connect() as connection:
            profile_usage = _canonical_usage_select("profile", "skills")
            loadout_usage = _canonical_usage_select("loadout", "skills")
            rows = connection.execute(
                "WITH "
                + SOURCE_UNIT_NAMES_CTE
                + ", combinations AS ("
                + profile_usage
                + " UNION "
                + loadout_usage
                + " UNION SELECT 'unit_option' AS source, uos.item_id, uos.unit_id, "
                "CAST(uos.occurrence_id AS TEXT) AS occurrence_key, "
                "uose.position AS extra_position, uose.extra_id "
                "FROM unit_option_skills AS uos "
                "JOIN unit_option_skill_extras AS uose "
                "ON uose.occurrence_id = uos.occurrence_id) "
                "SELECT combinations.item_id AS skill_id, COALESCE(NULLIF(s.name, ''), "
                "'Skill #' || combinations.item_id) AS skill_name, combinations.extra_id, "
                "COALESCE(NULLIF(e.name, ''), 'Extra #' || combinations.extra_id) AS extra_name, "
                "e.type AS extra_type, u.unit_id, u.unit_name "
                "FROM combinations "
                "LEFT JOIN skills AS s ON s.id = combinations.item_id "
                "LEFT JOIN extras AS e ON e.id = combinations.extra_id "
                "JOIN source_unit_names AS u ON u.unit_id = combinations.unit_id "
                "WHERE combinations.extra_id IS NOT NULL "
                "ORDER BY casefold(skill_name), casefold(extra_name), combinations.item_id, "
                "combinations.extra_id, unit_sort_key(unit_name), u.unit_id"
            ).fetchall()
            combinations: dict[tuple[Any, Any], dict[str, Any]] = {}
            for row in rows:
                if row["extra_type"] != "DISTANCE":
                    continue
                key = (row["skill_id"], row["extra_name"])
                item = combinations.setdefault(
                    key,
                    {
                        "skill_id": row["skill_id"],
                        "skill_name": row["skill_name"],
                        "extra_id": row["extra_id"],
                        "extra_name": row["extra_name"],
                        "is_distance": True,
                        "units": [],
                    },
                )
                unit = {"id": row["unit_id"], "name": row["unit_name"]}
                if unit not in item["units"]:
                    item["units"].append(unit)
            return list(combinations.values())

    @instance_lru_cache(maxsize=8)
    def list_catalog_items(self, catalog: str) -> list[dict[str, Any]]:
        """Return the named records in one of the public rules reference catalogs."""
        if catalog not in {"skills", "equipment", "weapons"}:
            raise ValueError(f"Unknown catalog: {catalog}")
        graph = self._application_catalog_graph(catalog)
        suffix = {"skills": "skill", "equipment": "equipment", "weapons": "weapon"}[catalog]
        profile_usage = _canonical_usage_select("profile", catalog)
        loadout_usage = _canonical_usage_select("loadout", catalog)
        with self._connect() as connection:
            usage_rows = connection.execute(
                "WITH uses AS ("
                + profile_usage
                + " UNION ALL "
                + loadout_usage
                + f" UNION ALL SELECT 'unit_option' AS source, o.item_id, o.unit_id, "
                "CAST(o.occurrence_id AS TEXT) AS occurrence_key, "
                f"e.position AS extra_position, e.extra_id FROM unit_option_{catalog} AS o "
                f"LEFT JOIN unit_option_{suffix}_extras AS e "
                "ON e.occurrence_id = o.occurrence_id) "
                "SELECT uses.source, uses.item_id, uses.occurrence_key, uses.unit_id, uses.extra_id "
                "FROM uses "
                "ORDER BY uses.source, uses.occurrence_key, uses.extra_position"
            ).fetchall()
        occurrences: dict[tuple[str, str], dict[str, Any]] = {}
        for row in usage_rows:
            application_id = graph["source_to_item"].get(row["item_id"])
            if application_id is None:
                continue
            occurrence = occurrences.setdefault(
                (row["source"], row["occurrence_key"]),
                {"item_id": application_id, "unit_id": row["unit_id"], "extras": []},
            )
            if row["extra_id"] is not None:
                occurrence["extras"].append(row["extra_id"])
        displayed_unit_ids = {
            source_id: unit["id"]
            for source_id, unit in self._visible_unit_items_by_source(
                frozenset({"specops"})
            ).items()
        }
        use_keys: dict[int, set[tuple[int, tuple[int, ...]]]] = {}
        for occurrence in occurrences.values():
            unit_id = displayed_unit_ids.get(occurrence["unit_id"])
            if unit_id is not None:
                use_keys.setdefault(occurrence["item_id"], set()).add(
                    (unit_id, tuple(occurrence["extras"]))
                )
        merged: list[dict[str, Any]] = []
        for item in graph["ordered_items"]:
            if catalog == "weapons":
                public = {
                    "id": item["id"],
                    "name": item["name"],
                    "category": item["category"],
                    "type": item.get("type"),
                    "ammunition": item.get("ammunition"),
                    "properties": item.get("properties"),
                }
            else:
                public = {
                    "id": item["id"],
                    "name": item["name"],
                    "wiki": item.get("wiki"),
                }
            public["source_ids"] = list(graph["source_ids_by_item"].get(item["id"], ()))
            public["use_count"] = len(use_keys.get(item["id"], set()))
            merged.append(public)
        return sorted(merged, key=lambda item: (unit_sort_key(item["name"]), item["id"]))

    @instance_lru_cache(maxsize=32)
    def logical_unit_ids_for_characteristic(self, characteristic_name: str) -> frozenset[int]:
        """Return logical Units carrying one profile/loadout characteristic."""

        if not isinstance(characteristic_name, str) or not characteristic_name.strip():
            raise ValueError("characteristic_name must be a non-empty string")
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT p.logical_unit_id AS logical_unit_id "
                "FROM profile_payloads AS p "
                "JOIN profile_payload_characteristics AS pc ON pc.profile_payload_id = p.id "
                "JOIN characteristics AS c ON c.id = pc.characteristic_id "
                "WHERE c.name = ? COLLATE NOCASE "
                "UNION "
                "SELECT DISTINCT l.logical_unit_id AS logical_unit_id "
                "FROM loadout_payloads AS l "
                "JOIN loadout_payload_characteristics AS lc ON lc.loadout_payload_id = l.id "
                "JOIN characteristics AS c ON c.id = lc.characteristic_id "
                "WHERE c.name = ? COLLATE NOCASE",
                (characteristic_name.strip(), characteristic_name.strip()),
            ).fetchall()
        return frozenset(int(row["logical_unit_id"]) for row in rows)

    @instance_lru_cache(maxsize=1)
    def trait_usage_index(self) -> dict[str, tuple[tuple[str, int], ...]]:
        """Return raw Army profile properties mapped to the catalog items carrying them."""
        with self._connect() as connection:
            source_rows = connection.execute(
                "SELECT catalog, source_item_id, application_item_id "
                "FROM application_catalog_sources"
            ).fetchall()
            rows = connection.execute(
                "SELECT DISTINCT m.id AS item_id, m.type, m.properties "
                "FROM metadata_weapons AS m"
            ).fetchall()
        source_maps: dict[str, dict[int, int]] = {
            "skills": {},
            "equipment": {},
            "weapons": {},
        }
        for row in source_rows:
            source_maps[row["catalog"]][row["source_item_id"]] = row["application_item_id"]
        items_by_trait: dict[str, set[tuple[str, int]]] = {}
        for row in rows:
            try:
                traits = json.loads(row["properties"] or "[]")
            except json.JSONDecodeError:
                traits = []
            if not isinstance(traits, list):
                traits = [traits]
            catalog = {"EQUIPMENT": "equipment", "SKILL": "skills"}.get(
                row["type"], "weapons"
            )
            application_item_id = source_maps[catalog].get(row["item_id"])
            if application_item_id is None:
                continue
            for trait in traits:
                trait_name = source_trait_name(trait)
                if trait_name:
                    items_by_trait.setdefault(trait_name, set()).add(
                        (catalog, application_item_id)
                    )
        return {
            name: tuple(sorted(items))
            for name, items in sorted(items_by_trait.items(), key=lambda item: unit_sort_key(item[0]))
        }

    @instance_lru_cache(maxsize=1)
    def list_traits(self) -> list[dict[str, Any]]:
        """Return distinct raw Army profile properties from the source trait bucket."""
        traits = []
        usage = self.trait_usage_index()
        slugs = assign_domain_slugs(
            ((name, name) for name in usage),
            domain="traits",
        )
        for name, items in usage.items():
            traits.append({
                "id": slugs[name],
                "slug": slugs[name],
                "name": name,
                "use_count": len(items),
                "description": None,
            })
        return traits

    @instance_lru_cache(maxsize=128)
    def get_trait(self, item_slug: str) -> dict[str, Any] | None:
        """Return one raw Army profile property with matching visible unit usage."""
        trait = next((item for item in self.list_traits() if item["id"] == item_slug), None)
        if trait is None:
            return None
        variants = []
        for catalog, item_id in self.trait_usage_index().get(trait["name"], ()):
            item = (
                self.get_skill(item_id)
                if catalog == "skills"
                else self.get_catalog_item(catalog, item_id)
            )
            if item is None:
                continue
            units = {
                unit["id"]: unit
                for variant in item["variants"]
                for unit in variant["units"]
            }
            if units:
                variants.append(
                    {
                        "catalog": catalog,
                        "item_id": item["id"],
                        "item_name": item["name"],
                        "extras": [],
                        "units": sorted(
                            units.values(),
                            key=lambda unit: (unit_sort_key(unit["name"]), unit["id"]),
                        ),
                    }
                )
        return {**trait, "variants": variants}

    @instance_lru_cache(maxsize=128)
    def get_catalog_item(self, catalog: str, item_ref: int | str) -> dict[str, Any] | None:
        """Return an equipment or weapon item and its extra-specific unit usage."""
        tables = {
            "equipment": ("equipment", "equipment"),
            "weapons": ("weapons", "weapon"),
        }
        if catalog not in tables:
            raise ValueError(f"Unknown catalog: {catalog}")
        graph = self._application_catalog_graph(catalog)
        application_item_id = self.application_catalog_id(catalog, item_ref)
        if application_item_id is None:
            return None
        item = graph["items"].get(application_item_id)
        if item is None:
            return None
        source_ids = graph["source_ids_by_item"].get(application_item_id, ())
        if not source_ids:
            return None
        suffix = tables[catalog][1]
        placeholders = ", ".join("?" for _ in source_ids)
        profile_usage = _canonical_usage_select(
            "profile", catalog, where=f"WHERE o.item_id IN ({placeholders}) "
        )
        loadout_usage = _canonical_usage_select(
            "loadout", catalog, where=f"WHERE o.item_id IN ({placeholders}) "
        )
        with self._connect() as connection:
            rows = connection.execute(
                "WITH "
                + SOURCE_UNIT_NAMES_CTE
                + ", uses AS ("
                + profile_usage
                + " UNION ALL "
                + loadout_usage
                + f" UNION ALL SELECT 'unit_option' AS source, o.item_id, o.unit_id, "
                "CAST(o.occurrence_id AS TEXT) AS occurrence_key, "
                f"e.position AS extra_position, e.extra_id FROM unit_option_{catalog} AS o "
                f"LEFT JOIN unit_option_{suffix}_extras AS e "
                "ON e.occurrence_id = o.occurrence_id "
                f"WHERE o.item_id IN ({placeholders})) "
                "SELECT uses.source, uses.item_id, uses.occurrence_key, uses.unit_id, "
                "u.unit_name, uses.extra_position, e.id AS extra_id, e.name AS extra_name "
                "FROM uses JOIN source_unit_names AS u ON u.unit_id = uses.unit_id "
                "LEFT JOIN extras AS e ON e.id = uses.extra_id "
                "ORDER BY uses.source, uses.occurrence_key, uses.extra_position, "
                "unit_sort_key(u.unit_name), u.unit_id",
                source_ids * 3,
            ).fetchall()
            if catalog == "weapons":
                profile_filter = (
                    f"m.id IN ({placeholders}) AND (m.type IS NULL OR m.type != 'EQUIPMENT')"
                )
                profile_parameters: tuple[Any, ...] = source_ids
            else:
                profile_filter = f"m.id IN ({placeholders}) AND m.type = 'EQUIPMENT'"
                profile_parameters = source_ids
            profile_rows = connection.execute(
                "SELECT m.position, m.id, m.type, m.name, m.ammunition, m.burst, m.damage, "
                "m.saving, m.savingNum, m.properties, m.distance, m.mode, m.profile, "
                "a.name AS ammunition_name "
                "FROM metadata_weapons AS m "
                "LEFT JOIN metadata_ammunitions AS a ON a.id = m.ammunition "
                f"WHERE {profile_filter} ORDER BY m.position",
                profile_parameters,
            ).fetchall()

        occurrences: dict[tuple[str, Any], dict[str, Any]] = {}
        for row in rows:
            occurrence = occurrences.setdefault(
                (row["source"], row["occurrence_key"]),
                {
                    "item_id": row["item_id"],
                    "unit": {"id": row["unit_id"], "name": row["unit_name"]},
                    "extras": [],
                },
            )
            if row["extra_id"] is not None:
                occurrence["extras"].append({"id": row["extra_id"], "name": row["extra_name"]})
        units_by_source = self._visible_unit_items_by_source(frozenset(AVAILABILITY_FLAGS))
        item_names = graph["source_names_by_item"][application_item_id]
        variants: dict[tuple[Any, tuple[tuple[Any, Any], ...]], dict[str, Any]] = {}
        for occurrence in occurrences.values():
            extras = occurrence["extras"]
            key = (
                occurrence["item_id"],
                tuple((extra["id"], extra["name"]) for extra in extras),
            )
            variant = variants.setdefault(
                key,
                {
                    "item_id": occurrence["item_id"],
                    "item_name": item_names[occurrence["item_id"]],
                    "extras": extras,
                    "units": [],
                },
            )
            unit = units_by_source.get(occurrence["unit"]["id"])
            if unit is not None and unit not in variant["units"]:
                variant["units"].append(unit)
        for variant in variants.values():
            variant["units"].sort(key=lambda unit: (unit_sort_key(unit["name"]), unit["id"]))

        result = {
            "id": application_item_id,
            "name": item["name"],
            "wiki": item.get("wiki"),
            "variants": [variant for variant in variants.values() if variant["units"]],
        }
        if catalog == "weapons":
            result["category"] = item.get("category")

        def decoded(value: Any, default: Any) -> Any:
            if value is None:
                return default
            if not isinstance(value, str):
                return value
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value

        profiles = []
        for profile in profile_rows:
            traits = decoded(profile["properties"], [])
            profile_item = {
                "id": profile["id"],
                "name": profile["name"],
                "mode": profile["mode"],
                "type": profile["type"],
                "ammunition": profile["ammunition_name"] or profile["ammunition"],
                "burst": profile["burst"],
                "damage": profile["damage"],
                "saving": profile["saving"],
                "saving_num": profile["savingNum"],
                "profile": profile["profile"],
                "traits": traits,
                "ranges": decoded(profile["distance"], {}),
            }
            profiles.append(profile_item)
        result["profiles"] = profiles
        if catalog == "weapons":
            profiles_by_id: dict[int, list[dict[str, Any]]] = {}
            for profile in profiles:
                profiles_by_id.setdefault(profile["id"], []).append(profile)
            result["weapon_variants"] = [
                {
                    "id": source_id,
                    "name": item_names[source_id],
                    "profiles": profiles_by_id[source_id],
                }
                for source_id in sorted(
                    profiles_by_id,
                    key=lambda value: (unit_sort_key(item_names[value]), value),
                )
            ]
        return result

    @instance_lru_cache(maxsize=128)
    def skill_source_ids(self, skill_ref: int | str) -> tuple[int, ...]:
        """Return source skill IDs represented by one application Skill reference."""
        graph = self._application_catalog_graph("skills")
        application_skill_id = self.application_catalog_id("skills", skill_ref)
        if application_skill_id is None:
            return ()
        return graph["source_ids_by_item"].get(application_skill_id, ())

    @instance_lru_cache(maxsize=128)
    def get_skill(self, skill_ref: int | str) -> dict[str, Any] | None:
        """Return one Skill reference together with the units that use it."""
        graph = self._application_catalog_graph("skills")
        application_skill_id = self.application_catalog_id("skills", skill_ref)
        if application_skill_id is None:
            return None
        skill = graph["items"].get(application_skill_id)
        if skill is None:
            return None
        source_ids = graph["source_ids_by_item"].get(application_skill_id, ())
        if not source_ids:
            return None
        placeholders = ", ".join("?" for _ in source_ids)
        profile_usage = _canonical_usage_select(
            "profile", "skills", where=f"WHERE o.item_id IN ({placeholders}) "
        )
        loadout_usage = _canonical_usage_select(
            "loadout", "skills", where=f"WHERE o.item_id IN ({placeholders}) "
        )
        with self._connect() as connection:
            rows = connection.execute(
                "WITH "
                + SOURCE_UNIT_NAMES_CTE
                + ", uses AS ("
                + profile_usage
                + " UNION ALL "
                + loadout_usage
                + " UNION ALL SELECT 'unit_option' AS source, o.item_id, o.unit_id, "
                "CAST(o.occurrence_id AS TEXT) AS occurrence_key, "
                "e.position AS extra_position, e.extra_id FROM unit_option_skills AS o "
                "LEFT JOIN unit_option_skill_extras AS e "
                "ON e.occurrence_id = o.occurrence_id "
                f"WHERE o.item_id IN ({placeholders})) "
                "SELECT uses.source, uses.item_id AS skill_id, uses.occurrence_key, "
                "uses.unit_id, u.unit_name, uses.extra_position, "
                "e.id AS extra_id, e.name AS extra_name, e.type AS extra_type "
                "FROM uses JOIN source_unit_names AS u ON u.unit_id = uses.unit_id "
                "LEFT JOIN extras AS e ON e.id = uses.extra_id "
                "ORDER BY uses.item_id, uses.source, uses.occurrence_key, "
                "uses.extra_position, unit_sort_key(u.unit_name), u.unit_id",
                source_ids * 3,
            ).fetchall()
        occurrences: dict[tuple[str, Any], dict[str, Any]] = {}
        for row in rows:
            key = (row["source"], row["occurrence_key"])
            occurrence = occurrences.setdefault(
                key,
                {
                    "skill_id": row["skill_id"],
                    "unit": {"id": row["unit_id"], "name": row["unit_name"]},
                    "extras": [],
                },
            )
            if row["extra_id"] is not None:
                extra = {"id": row["extra_id"], "name": row["extra_name"]}
                if row["extra_type"] == "DISTANCE":
                    extra["is_distance"] = True
                occurrence["extras"].append(extra)
        variants: dict[tuple[Any, tuple[tuple[Any, Any], ...]], dict[str, Any]] = {}
        skill_names = graph["source_names_by_item"][application_skill_id]
        for occurrence in occurrences.values():
            extras = occurrence["extras"]
            key = (
                occurrence["skill_id"],
                tuple((extra["id"], extra["name"]) for extra in extras),
            )
            variant = variants.setdefault(
                key,
                {
                    "skill_id": occurrence["skill_id"],
                    "skill_name": skill_names[occurrence["skill_id"]],
                    "extras": extras,
                    "units": [],
                },
            )
            if occurrence["unit"] not in variant["units"]:
                variant["units"].append(occurrence["unit"])
        unit_items_by_source = self._visible_unit_items_by_source(frozenset(AVAILABILITY_FLAGS))
        for variant in variants.values():
            items = {
                item["id"]: item
                for unit in variant["units"]
                if (item := unit_items_by_source.get(unit["id"])) is not None
            }
            variant["units"] = sorted(
                items.values(), key=lambda item: (unit_sort_key(item["name"]), item["id"])
            )
        return {
            "id": application_skill_id,
            "name": skill["name"],
            "wiki": skill.get("wiki"),
            "variants": [variant for variant in variants.values() if variant["units"]],
        }

    @instance_lru_cache(maxsize=128)
    def list_units(
        self,
        army_id: int | str | None = None,
        search: str = "",
        skill_id: int | str | None = None,
        equipment_id: int | str | None = None,
        weapon_id: int | str | None = None,
        limit: int = 50,
        offset: int = 0,
        mercs: bool = False,
        specops: bool = False,
        teamops: bool = False,
        reinforcement: bool = False,
        descending: bool = False,
        _unbounded: bool = False,
        _logical_unit_ids: frozenset[int] | None = None,
    ) -> dict[str, Any]:
        unresolved_army_filter = False
        if army_id is not None:
            resolved_army_id = self.application_army_id(army_id)
            unresolved_army_filter = resolved_army_id is None
            army_id = resolved_army_id
            if army_id is not None:
                army = self._application_army_graph()["armies"].get(army_id)
                if army is not None and not army["playable"]:
                    raise ArmySelectionError(
                        f"army_id {army_id} is a grouping-only identity, not a selectable army"
                    )
        rule_filters: dict[str, int | None] = {}
        for catalog, item_ref in {
            "skills": skill_id,
            "equipment": equipment_id,
            "weapons": weapon_id,
        }.items():
            if item_ref is not None:
                rule_filters[catalog] = self.application_catalog_id(catalog, item_ref)
        if not isinstance(search, str):
            raise ValueError("search must be a string")
        if type(_unbounded) is not bool:
            raise ValueError("_unbounded must be a boolean")
        if _logical_unit_ids is not None and (
            not isinstance(_logical_unit_ids, frozenset)
            or any(type(unit_id) is not int for unit_id in _logical_unit_ids)
        ):
            raise ValueError("_logical_unit_ids must be a frozenset of integer Unit ids")
        max_limit = 10_000 if _unbounded else 500
        if type(limit) is not int or not 1 <= limit <= max_limit:
            raise ValueError("limit must be an integer between 1 and 500")
        if type(offset) is not int or not 0 <= offset <= SQLITE_INTEGER_MAX:
            raise ValueError("offset must be a nonnegative integer at most 9223372036854775807")
        if type(descending) is not bool:
            raise ValueError("descending must be a boolean")
        selected_flags = {
            flag
            for flag, enabled in {
                "mercs": mercs,
                "specops": specops,
                "teamops": teamops,
                "reinforcement": reinforcement,
            }.items()
            if enabled
        }
        matching_sources_by_rule: dict[str, set[int]] = {}
        if rule_filters:
            with self._connect() as connection:
                for catalog, application_id in rule_filters.items():
                    graph = self._application_catalog_graph(catalog)
                    source_ids = (
                        ()
                        if application_id is None
                        else graph["source_ids_by_item"].get(application_id, ())
                    )
                    if not source_ids:
                        matching_sources_by_rule[catalog] = set()
                        continue
                    query = _canonical_filter_query(catalog, len(source_ids))
                    parameters = source_ids * 3
                    matching_sources_by_rule[catalog] = {
                        row["unit_id"]
                        for row in connection.execute(query, parameters)
                    }
        graph = self._unit_graph()
        faction_groups = self._faction_groups()
        faction_identities = self._faction_identities()
        army_names = graph["army_names"]
        groups = graph["groups"]
        canonical_factions = {
            row["id"]: row["canonical_faction_id"] for row in graph["rows"]
        }
        declared_faction_ids_by_unit = graph["declared_faction_ids_by_unit"]
        search_key = accent_insensitive_key(search)
        grouped = []
        matching_requirements: list[tuple[frozenset[str], ...]] = []
        for group in groups:
            if unresolved_army_filter:
                continue
            if _logical_unit_ids is not None and group["id"] not in _logical_unit_ids:
                continue
            if any(
                not set(group["source_ids"]).intersection(source_ids)
                for source_ids in matching_sources_by_rule.values()
            ):
                continue
            if search:
                if search_key:
                    matches_search = any(
                        search_key in accent_insensitive_key(name)
                        for name in group["search_terms"]
                        if name
                    )
                else:
                    matches_search = any(
                        search.casefold() in str(name).casefold()
                        for name in group["search_terms"]
                        if name
                    )
                if not matches_search:
                    continue

            requirements = minimal_availability_requirements(
                group,
                canonical_factions,
                declared_faction_ids_by_unit,
                army_id,
            )
            if not requirements:
                continue
            matching_requirements.append(requirements)
            if not any(required <= selected_flags for required in requirements):
                continue

            visible_armies = visible_armies_for_group(
                group,
                selected_flags,
                canonical_factions,
                declared_faction_ids_by_unit,
            )
            grouped.append({**group, "armies": visible_armies})
        grouped.sort(
            key=lambda group: (unit_sort_key(group["name"]), group["id"]),
            reverse=descending,
        )
        total = len(grouped)
        items = [
            {
                "id": group["id"],
                "name": group["name"],
                "isc": group["isc"],
                "slug": group["slug"],
                "main_army_id": group["main_army_id"],
                "main_army_name": army_names.get(group["main_army_id"]),
                "main_faction": faction_groups.get(group["main_army_id"]),
                "display_army_id": group["display_army_id"],
                "display_army_name": (
                    faction_identities.get(group["display_army_id"], {}).get("name")
                    or army_names.get(group["display_army_id"])
                ),
                "display_faction": faction_identities.get(group["display_army_id"]),
                "source_ids": group["source_ids"],
                "army_ids": list(group["armies"]),
                "armies": [
                    {"id": army["id"], "name": army["name"]}
                    for army in group["armies"].values()
                ],
            }
            for group in grouped[offset : offset + limit]
        ]
        summary = availability_summary(matching_requirements, selected_flags)
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "availability": summary,
        }

    @instance_lru_cache(maxsize=32)
    def visible_unit_ids(
        self,
        mercs: bool = False,
        specops: bool = False,
        teamops: bool = False,
        reinforcement: bool = False,
    ) -> list[int]:
        """Return the IDs of units visible under the selected optional-unit filters."""
        page = self.list_units(
            limit=10_000,
            mercs=mercs,
            specops=specops,
            teamops=teamops,
            reinforcement=reinforcement,
            _unbounded=True,
        )
        return [item["id"] for item in page["items"]]

    @instance_lru_cache(maxsize=128)
    def get_unit(self, unit_ref: int | str) -> dict[str, Any] | None:
        """Return one Unit reference with its army-specific profiles and loadouts."""
        application_unit_id = self.application_unit_id(unit_ref)
        if application_unit_id is None:
            return None
        graph = self._unit_graph()
        group = next(
            (item for item in graph["groups"] if item["id"] == application_unit_id),
            None,
        )
        if group is None:
            return None
        identity_config = self._identity_config()
        with self._connect() as connection:
            faction_groups = self._faction_groups()
            faction_identities = self._faction_identities()
            army_names = graph["army_names"]
            source_ids = group["source_ids"]
            declared_faction_ids = graph["declared_faction_ids_by_unit"]
            canonical_factions = {
                row["id"]: row["canonical_faction_id"] for row in graph["rows"]
            }
            placeholders = ", ".join("?" for _ in source_ids)
            armies_by_occurrence: dict[tuple[int, tuple[str, ...]], dict[str, Any]] = {}
            by_source_army: dict[tuple[int, int], dict[str, Any]] = {}
            for occurrence in group["army_occurrences"]:
                source_id = occurrence["source_id"]
                flags = tuple(
                    sorted(
                        army_required_flags(
                            occurrence,
                            group,
                            canonical_factions[source_id],
                            declared_faction_ids[source_id],
                        )
                    )
                )
                occurrence_key = (occurrence["id"], flags)
                army = armies_by_occurrence.setdefault(
                    occurrence_key,
                    {
                        "id": occurrence["id"],
                        "name": occurrence["name"],
                        "faction": faction_groups.get(occurrence["id"]),
                        "availability_flags": list(flags),
                        "profiles": [],
                        "loadouts": [],
                        "_occurrence_key": occurrence_key,
                    },
                )
                by_source_army[(source_id, occurrence["source_army_id"])] = army
            armies = list(armies_by_occurrence.values())
            profile_rows = connection.execute(
                "SELECT ppo.unit_id, ppo.army_id, ppo.group_id, ppo.profile_id, "
                "ppo.logo, pp.name, "
                "t.name AS type, c.name AS classification, pp.move_1, pp.move_2, "
                "pp.cc, pp.bs, pp.ph, pp.wip, pp.arm, pp.bts, pp.vitality, pp.silhouette, "
                "pp.is_structure, ppo.ava "
                "FROM profile_payload_occurrences AS ppo "
                "JOIN profile_payloads AS pp ON pp.id = ppo.profile_payload_id "
                "LEFT JOIN troop_types AS t ON t.id = pp.type_id "
                "JOIN profile_groups AS pg ON pg.army_id = ppo.army_id "
                "AND pg.unit_id = ppo.unit_id AND pg.group_id = ppo.group_id "
                "LEFT JOIN categories AS c ON c.id = pg.category_id "
                f"WHERE ppo.unit_id IN ({placeholders}) "
                "ORDER BY ppo.army_id, ppo.group_id, ppo.position, ppo.profile_id, "
                "ppo.unit_id",
                source_ids,
            )
            merged_profiles: dict[tuple[Any, ...], dict[str, Any]] = {}
            profile_merge_keys_by_source: dict[
                tuple[int, int, int, int], tuple[Any, ...]
            ] = {}
            for profile in profile_rows:
                army = by_source_army.get((profile["unit_id"], profile["army_id"]))
                if army is None:
                    continue
                profile_item = {
                    key: profile[key]
                    for key in profile.keys()
                    if key
                    not in {
                        "army_id",
                        "unit_id",
                        "logo",
                    }
                }
                profile_logo = profile["logo"]
                profile_item["logo_urls"] = [profile_logo] if profile_logo else []
                profile_item["display_name"] = strip_reinforcement_prefix(
                    profile["name"], identity_config
                )
                profile_item["profile_identity"] = normalized_profile_identity(
                    profile["name"], identity_config
                )
                profile_item["skills"] = []
                profile_item["equipment"] = []
                profile_item["weapons"] = []
                profile_item["characteristics"] = []
                profile_key = logical_source_profile_merge_key(
                    army["_occurrence_key"], profile
                )
                profile_merge_keys_by_source[
                    (
                        profile["unit_id"],
                        profile["army_id"],
                        profile["group_id"],
                        profile["profile_id"],
                    )
                ] = profile_key
                existing = merged_profiles.get(profile_key)
                if existing is None:
                    army["profiles"].append(profile_item)
                    merged_profiles[profile_key] = profile_item
                else:
                    merge_profile_availability(existing, profile_item)
                    for profile_logo in profile_item["logo_urls"]:
                        if profile_logo not in existing["logo_urls"]:
                            existing["logo_urls"].append(profile_logo)
            for occurrence_table, catalog_table, property_name, extras_table in (
                (
                    "profile_payload_skills",
                    "skills",
                    "skills",
                    "profile_payload_skill_extras",
                ),
                (
                    "profile_payload_equipment",
                    "equipment",
                    "equipment",
                    "profile_payload_equipment_extras",
                ),
                (
                    "profile_payload_weapons",
                    "weapons",
                    "weapons",
                    "profile_payload_weapon_extras",
                ),
            ):
                extras_by_occurrence: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
                extra_rows = connection.execute(
                    "SELECT ppo.unit_id, ppo.army_id, ppo.group_id, ppo.profile_id, "
                    "o.position AS occurrence_position, e.extra_id, x.name, "
                    "x.type AS extra_type "
                    "FROM profile_payload_occurrences AS ppo "
                    f"JOIN {occurrence_table} AS o "
                    "ON o.profile_payload_id = ppo.profile_payload_id "
                    f"JOIN {extras_table} AS e "
                    "ON e.profile_payload_id = o.profile_payload_id "
                    "AND e.occurrence_position = o.position "
                    "LEFT JOIN extras AS x ON x.id = e.extra_id "
                    f"WHERE ppo.unit_id IN ({placeholders}) "
                    "ORDER BY ppo.army_id, ppo.group_id, ppo.profile_id, o.position, "
                    "ppo.unit_id, e.position",
                    source_ids,
                )
                for extra in extra_rows:
                    extra_item = {"id": extra["extra_id"], "name": extra["name"]}
                    if property_name == "skills" and extra["extra_type"] == "DISTANCE":
                        extra_item["is_distance"] = True
                    occurrence_key = (
                        extra["unit_id"],
                        extra["army_id"],
                        extra["group_id"],
                        extra["profile_id"],
                        extra["occurrence_position"],
                    )
                    extras_by_occurrence.setdefault(occurrence_key, []).append(extra_item)
                occurrence_rows = connection.execute(
                    "SELECT ppo.unit_id, ppo.army_id, ppo.group_id, ppo.profile_id, "
                    "o.item_id, o.quantity, o.position, c.name "
                    "FROM profile_payload_occurrences AS ppo "
                    f"JOIN {occurrence_table} AS o "
                    "ON o.profile_payload_id = ppo.profile_payload_id "
                    f"LEFT JOIN {catalog_table} AS c ON c.id = o.item_id "
                    f"WHERE ppo.unit_id IN ({placeholders}) "
                    "ORDER BY ppo.army_id, ppo.group_id, ppo.profile_id, o.position, "
                    "ppo.unit_id",
                    source_ids,
                )
                for occurrence in occurrence_rows:
                    profile_key = profile_merge_keys_by_source.get(
                        (
                            occurrence["unit_id"],
                            occurrence["army_id"],
                            occurrence["group_id"],
                            occurrence["profile_id"],
                        )
                    )
                    profile_item = (
                        merged_profiles.get(profile_key) if profile_key is not None else None
                    )
                    if profile_item is not None:
                        occurrence_key = (
                            occurrence["unit_id"],
                            occurrence["army_id"],
                            occurrence["group_id"],
                            occurrence["profile_id"],
                            occurrence["position"],
                        )
                        append_unique_item(
                            profile_item[property_name],
                            {
                                "id": occurrence["item_id"],
                                "name": occurrence["name"],
                                "quantity": occurrence["quantity"],
                                "extras": extras_by_occurrence.get(occurrence_key, []),
                            },
                        )
            characteristic_rows = connection.execute(
                "SELECT ppo.unit_id, ppo.army_id, ppo.group_id, ppo.profile_id, c.name "
                "FROM profile_payload_occurrences AS ppo "
                "JOIN profile_payload_characteristics AS o "
                "ON o.profile_payload_id = ppo.profile_payload_id "
                "JOIN characteristics AS c ON c.id = o.characteristic_id "
                f"WHERE ppo.unit_id IN ({placeholders}) "
                "ORDER BY ppo.army_id, ppo.group_id, ppo.profile_id, o.position, "
                "ppo.unit_id",
                source_ids,
            )
            for characteristic in characteristic_rows:
                profile_key = profile_merge_keys_by_source.get(
                    (
                        characteristic["unit_id"],
                        characteristic["army_id"],
                        characteristic["group_id"],
                        characteristic["profile_id"],
                    )
                )
                profile_item = merged_profiles.get(profile_key) if profile_key is not None else None
                if profile_item is not None:
                    profile_item["characteristics"].append({"name": characteristic["name"]})
            profile_peripheral_rows = connection.execute(
                "SELECT p.unit_id, p.army_id, p.group_id, p.profile_id, "
                "a.entity_id, e.name, e.type_id, p.quantity "
                "FROM profile_peripherals AS p "
                "JOIN application_peripheral_sources AS a "
                "ON a.army_id = p.army_id AND a.peripheral_id = p.item_id "
                "JOIN application_peripheral_entities AS e ON e.id = a.entity_id "
                f"WHERE p.unit_id IN ({placeholders}) "
                "ORDER BY p.army_id, p.group_id, p.profile_id, p.position, p.unit_id",
                source_ids,
            )
            for peripheral in profile_peripheral_rows:
                profile_key = profile_merge_keys_by_source.get(
                    (
                        peripheral["unit_id"],
                        peripheral["army_id"],
                        peripheral["group_id"],
                        peripheral["profile_id"],
                    )
                )
                profile_item = (
                    merged_profiles.get(profile_key) if profile_key is not None else None
                )
                if profile_item is not None:
                    append_unique_item(
                        profile_item.setdefault("peripherals", []),
                        {
                            "id": peripheral["entity_id"],
                            "name": peripheral["name"],
                            "type_id": peripheral["type_id"],
                            "quantity": peripheral["quantity"],
                        },
                    )

            loadout_rows = connection.execute(
                "SELECT lpo.unit_id, lpo.army_id, lpo.group_id, lpo.option_id, lp.name, "
                "lpo.points, lpo.swc, lp.minis, lp.disabled "
                "FROM loadout_payload_occurrences AS lpo "
                "JOIN loadout_payloads AS lp ON lp.id = lpo.loadout_payload_id "
                f"WHERE lpo.unit_id IN ({placeholders}) "
                "ORDER BY lpo.army_id, lpo.group_id, lpo.position, lpo.option_id, lpo.unit_id",
                source_ids,
            )
            loadout_items: dict[tuple[Any, ...], dict[str, Any]] = {}
            loadout_keys_by_source: dict[tuple[int, int, int, int], tuple[Any, ...]] = {}
            for loadout in loadout_rows:
                army = by_source_army.get((loadout["unit_id"], loadout["army_id"]))
                if army is None:
                    continue
                loadout_item = {
                    key: loadout[key]
                    for key in loadout.keys()
                    if key not in {"army_id", "unit_id"}
                }
                loadout_item["skills"] = []
                loadout_item["equipment"] = []
                loadout_item["weapons"] = []
                loadout_item["orders"] = []
                loadout_key = logical_source_loadout_merge_key(
                    army["_occurrence_key"], loadout
                )
                loadout_keys_by_source[
                    (
                        loadout["unit_id"],
                        loadout["army_id"],
                        loadout["group_id"],
                        loadout["option_id"],
                    )
                ] = loadout_key
                if loadout_key not in loadout_items:
                    army["loadouts"].append(loadout_item)
                    loadout_items[loadout_key] = loadout_item
            order_rows = connection.execute(
                "SELECT lpo.unit_id, lpo.army_id, lpo.group_id, lpo.option_id, o.order_type, "
                "o.list_count, o.total_count "
                "FROM loadout_payload_occurrences AS lpo "
                "JOIN loadout_payload_orders AS o "
                "ON o.loadout_payload_id = lpo.loadout_payload_id "
                f"WHERE lpo.unit_id IN ({placeholders}) "
                "ORDER BY lpo.army_id, lpo.group_id, lpo.option_id, o.position, lpo.unit_id",
                source_ids,
            )
            for order in order_rows:
                loadout_key = loadout_keys_by_source.get(
                    (
                        order["unit_id"],
                        order["army_id"],
                        order["group_id"],
                        order["option_id"],
                    )
                )
                loadout_item = (
                    loadout_items.get(loadout_key) if loadout_key is not None else None
                )
                if loadout_item is not None:
                    order_type = order["order_type"]
                    loadout_item["orders"].append(
                        {
                            "type": order_type.lower()
                            if isinstance(order_type, str)
                            else order_type,
                            "list": order["list_count"],
                            "total": order["total_count"],
                        }
                    )
            for occurrence_table, catalog_table, property_name, extras_table in (
                (
                    "loadout_payload_skills",
                    "skills",
                    "skills",
                    "loadout_payload_skill_extras",
                ),
                (
                    "loadout_payload_equipment",
                    "equipment",
                    "equipment",
                    "loadout_payload_equipment_extras",
                ),
                (
                    "loadout_payload_weapons",
                    "weapons",
                    "weapons",
                    "loadout_payload_weapon_extras",
                ),
            ):
                extras_by_occurrence: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
                extra_rows = connection.execute(
                    "SELECT lpo.unit_id, lpo.army_id, lpo.group_id, lpo.option_id, "
                    "o.position AS occurrence_position, e.extra_id, x.name, "
                    "x.type AS extra_type "
                    "FROM loadout_payload_occurrences AS lpo "
                    f"JOIN {occurrence_table} AS o "
                    "ON o.loadout_payload_id = lpo.loadout_payload_id "
                    f"JOIN {extras_table} AS e "
                    "ON e.loadout_payload_id = o.loadout_payload_id "
                    "AND e.occurrence_position = o.position "
                    "LEFT JOIN extras AS x ON x.id = e.extra_id "
                    f"WHERE lpo.unit_id IN ({placeholders}) "
                    "ORDER BY lpo.army_id, lpo.group_id, lpo.option_id, o.position, "
                    "lpo.unit_id, e.position",
                    source_ids,
                )
                for extra in extra_rows:
                    extra_item = {"id": extra["extra_id"], "name": extra["name"]}
                    if property_name == "skills" and extra["extra_type"] == "DISTANCE":
                        extra_item["is_distance"] = True
                    occurrence_key = (
                        extra["unit_id"],
                        extra["army_id"],
                        extra["group_id"],
                        extra["option_id"],
                        extra["occurrence_position"],
                    )
                    extras_by_occurrence.setdefault(occurrence_key, []).append(extra_item)
                occurrence_rows = connection.execute(
                    "SELECT lpo.unit_id, lpo.army_id, lpo.group_id, lpo.option_id, "
                    "o.item_id, o.quantity, o.position, c.name "
                    "FROM loadout_payload_occurrences AS lpo "
                    f"JOIN {occurrence_table} AS o "
                    "ON o.loadout_payload_id = lpo.loadout_payload_id "
                    f"LEFT JOIN {catalog_table} AS c ON c.id = o.item_id "
                    f"WHERE lpo.unit_id IN ({placeholders}) "
                    "ORDER BY lpo.army_id, lpo.group_id, lpo.option_id, o.position, "
                    "lpo.unit_id",
                    source_ids,
                )
                for occurrence in occurrence_rows:
                    loadout_key = loadout_keys_by_source.get(
                        (
                            occurrence["unit_id"],
                            occurrence["army_id"],
                            occurrence["group_id"],
                            occurrence["option_id"],
                        )
                    )
                    loadout_item = (
                        loadout_items.get(loadout_key) if loadout_key is not None else None
                    )
                    if loadout_item is not None:
                        occurrence_key = (
                            occurrence["unit_id"],
                            occurrence["army_id"],
                            occurrence["group_id"],
                            occurrence["option_id"],
                            occurrence["position"],
                        )
                        append_unique_item(
                            loadout_item[property_name],
                            {
                                "id": occurrence["item_id"],
                                "name": occurrence["name"],
                                "quantity": occurrence["quantity"],
                                "extras": extras_by_occurrence.get(occurrence_key, []),
                            },
                        )
            loadout_peripheral_rows = connection.execute(
                "SELECT p.unit_id, p.army_id, p.group_id, p.option_id, "
                "a.entity_id, e.name, e.type_id, p.quantity "
                "FROM option_peripherals AS p "
                "JOIN application_peripheral_sources AS a "
                "ON a.army_id = p.army_id AND a.peripheral_id = p.item_id "
                "JOIN application_peripheral_entities AS e ON e.id = a.entity_id "
                f"WHERE p.unit_id IN ({placeholders}) "
                "ORDER BY p.army_id, p.group_id, p.option_id, p.position, p.unit_id",
                source_ids,
            )
            for peripheral in loadout_peripheral_rows:
                loadout_key = loadout_keys_by_source.get(
                    (
                        peripheral["unit_id"],
                        peripheral["army_id"],
                        peripheral["group_id"],
                        peripheral["option_id"],
                    )
                )
                loadout_item = (
                    loadout_items.get(loadout_key) if loadout_key is not None else None
                )
                if loadout_item is not None:
                    append_unique_item(
                        loadout_item.setdefault("peripherals", []),
                        {
                            "id": peripheral["entity_id"],
                            "name": peripheral["name"],
                            "type_id": peripheral["type_id"],
                            "quantity": peripheral["quantity"],
                        },
                    )

            access_rows = connection.execute(
                "SELECT a.id, a.controller_kind, a.army_id, a.unit_id, a.group_id, "
                "a.parent_id, a.type_id, a.relationship, t.target_logical_unit_id, "
                "lu.name AS target_name, ds.slug AS target_slug "
                "FROM application_peripheral_controller_access AS a "
                "JOIN application_peripheral_controller_targets AS t ON t.access_id = a.id "
                "JOIN logical_units AS lu ON lu.id = t.target_logical_unit_id "
                "LEFT JOIN application_domain_slugs AS ds "
                "ON ds.domain = 'units' AND ds.application_id = t.target_logical_unit_id "
                f"WHERE a.unit_id IN ({placeholders}) "
                "ORDER BY a.army_id, a.unit_id, a.group_id, a.parent_id, "
                "a.id, t.target_logical_unit_id",
                source_ids,
            )
            access_items: dict[str, dict[str, Any]] = {}
            for access in access_rows:
                access_item = access_items.get(access["id"])
                if access_item is None:
                    access_item = {
                        "id": access["id"],
                        "type_id": access["type_id"],
                        "relationship": access["relationship"],
                        "targets": [],
                    }
                    access_items[access["id"]] = access_item
                    source_key = (
                        access["unit_id"],
                        access["army_id"],
                        access["group_id"],
                        access["parent_id"],
                    )
                    if access["controller_kind"] == "profile":
                        merge_key = profile_merge_keys_by_source.get(source_key)
                        parent_item = (
                            merged_profiles.get(merge_key) if merge_key is not None else None
                        )
                    else:
                        merge_key = loadout_keys_by_source.get(source_key)
                        parent_item = (
                            loadout_items.get(merge_key) if merge_key is not None else None
                        )
                    if parent_item is not None:
                        parent_item.setdefault("peripheral_access", []).append(access_item)
                access_item["targets"].append(
                    {
                        "id": access["target_logical_unit_id"],
                        "slug": access["target_slug"],
                        "name": access["target_name"],
                    }
                )

            controller_rows = connection.execute(
                "SELECT a.id, a.controller_kind, a.army_id, "
                "a.type_id, a.relationship, lus.logical_unit_id AS controller_unit_id, "
                "lu.name AS controller_name, ds.slug AS controller_slug, "
                "CASE a.controller_kind WHEN 'profile' THEN pp.name ELSE lp.name END "
                "AS controller_option_name "
                "FROM application_peripheral_controller_targets AS t "
                "JOIN application_peripheral_controller_access AS a ON a.id = t.access_id "
                "JOIN logical_unit_sources AS lus ON lus.source_unit_id = a.unit_id "
                "JOIN logical_units AS lu ON lu.id = lus.logical_unit_id "
                "LEFT JOIN application_domain_slugs AS ds "
                "ON ds.domain = 'units' AND ds.application_id = lus.logical_unit_id "
                "LEFT JOIN profile_payload_occurrences AS ppo ON a.controller_kind = 'profile' "
                "AND ppo.army_id = a.army_id AND ppo.unit_id = a.unit_id "
                "AND ppo.group_id = a.group_id AND ppo.profile_id = a.parent_id "
                "LEFT JOIN profile_payloads AS pp ON pp.id = ppo.profile_payload_id "
                "LEFT JOIN loadout_payload_occurrences AS lpo ON a.controller_kind = 'loadout' "
                "AND lpo.army_id = a.army_id AND lpo.unit_id = a.unit_id "
                "AND lpo.group_id = a.group_id AND lpo.option_id = a.parent_id "
                "LEFT JOIN loadout_payloads AS lp ON lp.id = lpo.loadout_payload_id "
                "WHERE t.target_logical_unit_id = ? "
                "ORDER BY a.army_id, lu.name, a.controller_kind, a.group_id, a.parent_id, a.id",
                (group["id"],),
            ).fetchall()
            peripheral_controllers = []
            for row in controller_rows:
                army_identity = faction_identities.get(row["army_id"])
                peripheral_controllers.append(
                    {
                        "id": row["id"],
                        "type_id": row["type_id"],
                        "relationship": row["relationship"],
                        "controller_kind": row["controller_kind"],
                        "controller_option_name": row["controller_option_name"],
                        "army": {
                            "id": army_identity["id"] if army_identity else row["army_id"],
                            "name": army_identity["name"] if army_identity else None,
                        },
                        "controller": {
                            "id": row["controller_unit_id"],
                            "slug": row["controller_slug"],
                            "name": row["controller_name"],
                        },
                    }
                )

            peripheral_type_ids = [
                row[0]
                for row in connection.execute(
                    "SELECT DISTINCT type_id FROM application_peripheral_unit_sources "
                    "WHERE logical_unit_id = ? ORDER BY type_id",
                    (group["id"],),
                )
            ]

            constraint_rows = connection.execute(
                "SELECT c.army_id, c.relation_id, c.family, c.min_count, c.max_count, "
                "c.is_group, m.relation_unit_id, m.source_unit_id, m.logical_unit_id, "
                "lu.name, ds.slug "
                "FROM application_unit_constraints AS c "
                "JOIN application_unit_constraint_members AS m "
                "ON m.army_id = c.army_id AND m.relation_id = c.relation_id "
                "JOIN logical_units AS lu ON lu.id = m.logical_unit_id "
                "LEFT JOIN application_domain_slugs AS ds "
                "ON ds.domain = 'units' AND ds.application_id = m.logical_unit_id "
                "WHERE EXISTS ("
                "SELECT 1 FROM application_unit_constraint_members AS own "
                "WHERE own.army_id = c.army_id AND own.relation_id = c.relation_id "
                "AND own.logical_unit_id = ?) "
                "ORDER BY c.army_id, c.relation_id, m.position, m.relation_unit_id",
                (group["id"],),
            ).fetchall()
            selection_constraints: list[dict[str, Any]] = []
            constraints_by_key: dict[tuple[int, int], dict[str, Any]] = {}
            for row in constraint_rows:
                key = (row["army_id"], row["relation_id"])
                constraint = constraints_by_key.get(key)
                if constraint is None:
                    constraint = {
                        "army_id": row["army_id"],
                        "relation_id": row["relation_id"],
                        "family": row["family"],
                        "min_count": row["min_count"],
                        "max_count": row["max_count"],
                        "is_group": bool(row["is_group"]),
                        "members": [],
                    }
                    constraints_by_key[key] = constraint
                    selection_constraints.append(constraint)
                constraint["members"].append(
                    {
                        "source_unit_id": row["source_unit_id"],
                        "logical_unit_id": row["logical_unit_id"],
                        "slug": row["slug"],
                        "name": row["name"],
                    }
                )

            dependency_rows = connection.execute(
                "SELECT c.army_id, c.relation_id, c.min_count, c.max_count, c.is_group, "
                "m.relation_unit_id, m.source_unit_id, m.logical_unit_id, "
                "m.group_id AS member_group_id, m.per_parent, "
                "t.dependency_id, t.source_unit_id AS dependency_source_unit_id, "
                "t.logical_unit_id AS dependency_logical_unit_id, "
                "t.group_id AS dependency_group_id, t.source_group_selector, "
                "t.min_count AS dependency_min_count, "
                "t.min_dependant AS dependency_min_dependant, t.options "
                "FROM application_unit_group_dependency_constraints AS c "
                "JOIN application_unit_group_dependency_members AS m "
                "ON m.army_id = c.army_id AND m.relation_id = c.relation_id "
                "JOIN application_unit_group_dependency_targets AS t "
                "ON t.army_id = m.army_id AND t.relation_id = m.relation_id "
                "AND t.relation_unit_id = m.relation_unit_id "
                "WHERE m.logical_unit_id = ? OR t.logical_unit_id = ? "
                "ORDER BY c.army_id, c.relation_id, m.position, m.relation_unit_id, "
                "t.position, t.dependency_id",
                (group["id"], group["id"]),
            ).fetchall()
            group_dependencies: list[dict[str, Any]] = []
            dependencies_by_relation: dict[tuple[int, int], dict[str, Any]] = {}
            members_by_key: dict[tuple[int, int, int], dict[str, Any]] = {}
            for row in dependency_rows:
                relation_key = (row["army_id"], row["relation_id"])
                relation = dependencies_by_relation.get(relation_key)
                if relation is None:
                    relation = {
                        "army_id": row["army_id"],
                        "relation_id": row["relation_id"],
                        "min_count": row["min_count"],
                        "max_count": row["max_count"],
                        "is_group": bool(row["is_group"]),
                        "members": [],
                    }
                    dependencies_by_relation[relation_key] = relation
                    group_dependencies.append(relation)
                member_key = (
                    row["army_id"],
                    row["relation_id"],
                    row["relation_unit_id"],
                )
                member = members_by_key.get(member_key)
                if member is None:
                    member = {
                        "source_unit_id": row["source_unit_id"],
                        "logical_unit_id": row["logical_unit_id"],
                        "group_id": row["member_group_id"],
                        "per_parent": row["per_parent"],
                        "dependencies": [],
                    }
                    members_by_key[member_key] = member
                    relation["members"].append(member)
                target = {
                    "source_unit_id": row["dependency_source_unit_id"],
                    "logical_unit_id": row["dependency_logical_unit_id"],
                    "group_id": row["dependency_group_id"],
                    "source_group_selector": row["source_group_selector"],
                    "min_count": row["dependency_min_count"],
                    "min_dependant": row["dependency_min_dependant"],
                    "options": json.loads(row["options"]) if row["options"] else None,
                }
                member["dependencies"].append(target)

            main_faction = faction_groups.get(group["main_army_id"])
            display_faction = faction_identities.get(group["display_army_id"])
            for army in armies:
                del army["_occurrence_key"]
        result = {
            "id": group["id"],
            "name": group["name"],
            "isc": group["isc"],
            "slug": group["slug"],
            "isc_abbr": group["isc_abbr"],
            "notes": group["notes"],
            "main_army_id": group["main_army_id"],
            "main_army_name": army_names.get(group["main_army_id"]),
            "main_faction": main_faction,
            "display_army_id": group["display_army_id"],
            "display_army_name": (
                display_faction.get("name")
                if display_faction
                else army_names.get(group["display_army_id"])
            ),
            "display_faction": display_faction,
            "source_ids": source_ids,
            "armies": armies,
        }
        if peripheral_type_ids:
            result["peripheral_type_ids"] = peripheral_type_ids
        if peripheral_controllers:
            result["peripheral_controllers"] = peripheral_controllers
        if selection_constraints:
            result["selection_constraints"] = selection_constraints
        if group_dependencies:
            result["group_dependencies"] = group_dependencies
        return result

