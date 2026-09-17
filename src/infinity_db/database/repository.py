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
from decimal import Decimal, InvalidOperation
from functools import wraps
from pathlib import Path
from typing import Any, Protocol

from infinity_army_data.availability import (
    MERCENARY_AVAILABILITY,
    STANDARD_AVAILABILITY,
)
from infinity_army_data.normalize import FORMAT_NAME, FORMAT_VERSION
from infinity_db.identities import (
    IDENTITY_CONFIG_METADATA_KEY,
    IDENTITY_CONFIG_SHA256_METADATA_KEY,
    IdentityConfig,
    IdentityConfigError,
    load_identity_config,
    normalized_profile_identity,
    parse_identity_metadata,
)

from .schema import (
    APPLICATION_ID,
    DATABASE_COMPATIBILITY_KEY,
    DATABASE_COMPATIBILITY_VERSION,
    DATABASE_TABLES,
    METADATA_TABLE,
    SCHEMA_VERSION,
    quote,
)

SQLITE_INTEGER_MIN = -(2**63)
SQLITE_INTEGER_MAX = 2**63 - 1
UNIT_NAME_SQL = "COALESCE(NULLIF(u.name, ''), 'Unit ' || u.id)"
AVAILABILITY_FLAGS = ("mercs", "specops", "teamops", "reinforcement")
NON_ALIGNED_GROUP_ID = 901
ARMY_ROLE_MAIN = "main"
ARMY_ROLE_SECTORIAL = "sectorial"
ARMY_ROLE_NON_ALIGNED = "non_aligned"
ARMY_ROLE_REINFORCEMENT = "reinforcement"
ARMY_ROLE_GROUPING = "grouping"
ARMY_ROLE_UNKNOWN = "unknown"


class ArmySelectionError(ValueError):
    """Raised when an army identity exists but is not a selectable force."""


class RowLike(Protocol):
    """Minimal row interface shared by sqlite3.Row and test dictionaries."""

    def __getitem__(self, key: str) -> Any: ...

    def keys(self) -> Iterable[str]: ...

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


NUMBER_PATTERN = re.compile(r"[+-]?\d+(?:\.\d+)?")
DISTANCE_DIVISOR = Decimal("2.5")
NON_DISTANCE_EXTRAS = frozenset({"+5 CC"})

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

def canonical_skill_id(
    skill_id: int, identity_config: IdentityConfig | None = None
) -> int:
    """Return the configured representative ID for an explicit skill identity group."""
    config = identity_config or load_identity_config()
    return config.canonical_catalog_id("skills", skill_id) or skill_id

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

def configured_catalog_group(
    identity_config: IdentityConfig,
    catalog: str,
    item_id: int,
    available_ids: Collection[int],
) -> tuple[int, tuple[int, ...]] | None:
    """Return an explicit manifest group restricted to IDs present in this snapshot."""
    source_ids = tuple(
        source_id
        for source_id in identity_config.catalog_source_ids(catalog, item_id)
        if source_id in available_ids
    )
    if not source_ids:
        return None
    canonical_id = identity_config.canonical_catalog_id(catalog, item_id)
    if canonical_id not in source_ids:
        canonical_id = min(source_ids)
    return canonical_id, source_ids

def trait_slug(name: object) -> str:
    """Return a URL-safe identity for one raw Army trait label."""
    return re.sub(r"[^a-z0-9]+", "-", str(name or "").casefold()).strip("-")

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

def contains_distance_multiple(value: object) -> bool:
    """Whether text has no assignment and contains a number divisible by 2.5."""
    text = str(value or "")
    if "=" in text or text.upper() in NON_DISTANCE_EXTRAS:
        return False
    for number in NUMBER_PATTERN.findall(text):
        try:
            if Decimal(number) % DISTANCE_DIVISOR == 0:
                return True
        except InvalidOperation:
            continue
    return False

def canonical_skill_extra_name(skill_name: object, extra_name: object) -> str:
    """Normalize sign conventions that are specific to a distance skill."""
    skill = str(skill_name or "")
    extra = str(extra_name or "")
    if skill == "Super-Jump":
        return extra.removeprefix("+")
    if skill == "Forward Deployment" and not extra.startswith("+"):
        try:
            if NUMBER_PATTERN.fullmatch(extra) and Decimal(extra) > 0:
                return f"+{extra}"
        except InvalidOperation:
            pass
    return extra

def append_unique_item(items: list[dict[str, Any]], item: dict[str, Any]) -> None:
    """Add an item unless a merged source already contributed the same one."""
    if item not in items:
        items.append(item)

def merge_profile(profile: dict[str, Any], duplicate: dict[str, Any]) -> None:
    """Combine complementary metadata from duplicate source profiles."""
    for key, value in duplicate.items():
        if key in {"skills", "equipment", "weapons", "ava"}:
            continue
        if profile.get(key) in (None, "") and value not in (None, ""):
            profile[key] = value
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
    normal_army_ids: Collection[int] | None = None,
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
        # was persisted still need the previous canonical/faction inference.
        faction_id = (
            group["canonical_faction_id"]
            if canonical_faction_id is None
            else canonical_faction_id
        )
        normal_armies = group["normal_army_ids"] if normal_army_ids is None else normal_army_ids
        if faction_id == 1 and army["id"] not in normal_armies:
            required.add("mercs")
    else:
        raise ValueError(f"Unknown army availability kind: {availability_kind!r}")
    if army.get("kind") == "reinforcement":
        required.add("reinforcement")
    filters = army.get("filters")
    if isinstance(filters, dict):
        required.update(flag for flag in AVAILABILITY_FLAGS if filters.get(flag))
    return required

def visible_armies_for_group(
    group: Mapping[str, Any],
    selected_flags: set[str],
    canonical_factions: Mapping[int, int | None],
    normal_armies_by_unit: Mapping[int, Collection[int]],
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
            normal_armies_by_unit[source_id],
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
    def _faction_groups(self) -> dict[int, dict[str, Any]]:
        """Return Army metadata faction groups keyed by source army ID."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT child.id AS army_id, "
                "COALESCE(child.parent, child.id) AS faction_id, "
                "parent.name AS faction_name, parent.slug AS faction_slug "
                "FROM metadata_factions AS child "
                "LEFT JOIN metadata_factions AS parent "
                "ON parent.id = COALESCE(child.parent, child.id)"
            ).fetchall()
        groups = {
            row["army_id"]: {
                "id": row["faction_id"],
                "name": row["faction_name"],
                "slug": row["faction_slug"],
            }
            for row in rows
        }
        for source_id, canonical_id in self._identity_config().army_aliases.items():
            if canonical_id not in groups and source_id in groups:
                groups[canonical_id] = groups[source_id]
        return groups

    def validate(self) -> None:
        """Reject missing, unrelated, unsupported, incomplete, or corrupt databases."""
        with self._connect() as connection:
            application_id = connection.execute("PRAGMA application_id").fetchone()[0]
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if application_id != APPLICATION_ID or version != SCHEMA_VERSION:
                raise ValueError("Unsupported InfinityDB database; rebuild it from normalized JSON")
            for name, definition in DATABASE_TABLES.items():
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
            identity_config_from_connection(connection)
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
        """Load materialized logical identity plus source-specific unit relationships."""
        identity_config = self._identity_config()
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT u.id, {UNIT_NAME_SQL} AS name, u.isc, u.isc_abbr, u.slug, u.notes, "
                "u.main_army_id, u.canonical_faction_id, u.source_role "
                "FROM units AS u WHERE u.source_defined = 1 ORDER BY u.id"
            ).fetchall()
            rows_by_id = {row["id"]: row for row in rows}
            logical_rows = connection.execute(
                "SELECT lu.id AS logical_unit_id, lu.representative_unit_id, "
                "lus.source_unit_id "
                "FROM logical_units AS lu "
                "JOIN logical_unit_sources AS lus ON lus.logical_unit_id = lu.id "
                "ORDER BY lu.id, lus.source_unit_id"
            ).fetchall()
            memberships: dict[int, list[dict[str, Any]]] = {row["id"]: [] for row in rows}
            army_names = {
                row["id"]: army_name(row)
                for row in connection.execute("SELECT id, name, slug FROM army_lists")
            }
            for army in connection.execute(
                "SELECT au.unit_id, au.filters, au.availability_kind, "
                "a.id, a.name, a.slug, a.kind "
                "FROM army_units AS au "
                "JOIN army_lists AS a ON a.id = au.army_id ORDER BY a.id"
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
                        "name": army_name(army),
                        "kind": army["kind"],
                        "filters": filters,
                        "availability_kind": army["availability_kind"],
                    }
                )
            normal_armies_by_unit: dict[int, set[int]] = {row["id"]: set() for row in rows}
            for faction in connection.execute("SELECT unit_id, faction_id FROM unit_factions"):
                if faction["unit_id"] in normal_armies_by_unit:
                    normal_armies_by_unit[faction["unit_id"]].add(faction["faction_id"])
            search_terms_by_source = {
                row["id"]: {row["name"], row["isc"], row["isc_abbr"], row["slug"]} for row in rows
            }
            for table in ("profiles", "loadout_options", "unit_options"):
                for row in connection.execute(f"SELECT unit_id, name FROM {table}"):
                    if row["unit_id"] in search_terms_by_source:
                        search_terms_by_source[row["unit_id"]].add(row["name"])

        sources_by_logical: dict[int, list[int]] = {}
        representatives: dict[int, int] = {}
        for row in logical_rows:
            logical_id = row["logical_unit_id"]
            representatives[logical_id] = row["representative_unit_id"]
            sources_by_logical.setdefault(logical_id, []).append(row["source_unit_id"])

        groups: list[dict[str, Any]] = []
        for logical_id, source_ids in sources_by_logical.items():
            representative = rows_by_id[representatives[logical_id]]
            group: dict[str, Any] = {
                "id": logical_id,
                "name": representative["name"],
                "isc": representative["isc"],
                "slug": representative["slug"],
                "canonical_faction_id": representative["canonical_faction_id"],
                "main_army_id": representative["main_army_id"],
                "source_ids": source_ids,
                "names": [rows_by_id[source_id]["name"] for source_id in source_ids],
                "armies": {},
                "army_occurrences": [],
            }
            for source_id in source_ids:
                for army in memberships[source_id]:
                    source_army_id = army["id"]
                    preferred_army_id = identity_config.canonical_army_id(source_army_id)
                    preferred_army = {**army, "id": preferred_army_id}
                    if (
                        preferred_army_id not in group["armies"]
                        or source_army_id == preferred_army_id
                    ):
                        group["armies"][preferred_army_id] = preferred_army
                    group["army_occurrences"].append(
                        {
                            **preferred_army,
                            "source_id": source_id,
                            "source_army_id": source_army_id,
                        }
                    )
            group["normal_army_ids"] = set().union(
                *(normal_armies_by_unit[source_id] for source_id in source_ids)
            )
            group["search_terms"] = set().union(
                *(search_terms_by_source[source_id] for source_id in source_ids)
            )
            groups.append(group)

        groups_by_source = {
            source_id: group for group in groups for source_id in group["source_ids"]
        }
        return {
            "rows": rows,
            "army_names": army_names,
            "normal_armies_by_unit": normal_armies_by_unit,
            "search_terms_by_source": search_terms_by_source,
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
        canonical_factions = {row["id"]: row["canonical_faction_id"] for row in graph["rows"]}
        normal_armies_by_unit = graph["normal_armies_by_unit"]
        items_by_source: dict[int, dict[str, Any]] = {}
        for group in graph["groups"]:
            visible_armies = visible_armies_for_group(
                group, set(selected_flags), canonical_factions, normal_armies_by_unit
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
                "source_ids": group["source_ids"],
                "army_ids": list(visible_armies),
                "armies": [
                    {"id": army["id"], "name": army["name"]} for army in visible_armies.values()
                ],
            }
            for source_id in group["source_ids"]:
                items_by_source[source_id] = item
        return items_by_source

    @instance_lru_cache(maxsize=1)
    def list_armies(self) -> list[dict[str, Any]]:
        """Return imported force lists with explicit source-derived role semantics."""
        identity_config = self._identity_config()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT a.id, a.name, a.slug, a.kind, a.reinforcement_id, u.id AS unit_id "
                "FROM army_lists AS a "
                "LEFT JOIN army_units AS au ON au.army_id = a.id "
                "LEFT JOIN units AS u ON u.id = au.unit_id AND u.source_defined = 1 "
                "ORDER BY a.id"
            ).fetchall()
            metadata = {
                row["id"]: dict(row)
                for row in connection.execute(
                    "SELECT id, parent, name, slug FROM metadata_factions ORDER BY id"
                )
            }

            reinforcement_parents: dict[int, set[int]] = {}
            for row in connection.execute(
                "SELECT id, reinforcement_id FROM army_lists "
                "WHERE reinforcement_id IS NOT NULL ORDER BY id"
            ):
                reinforcement_id = identity_config.canonical_army_id(row["reinforcement_id"])
                parent_id = identity_config.canonical_army_id(row["id"])
                reinforcement_parents.setdefault(reinforcement_id, set()).add(parent_id)

            armies: dict[int, dict[str, Any]] = {}
            for row in rows:
                source_army_id = row["id"]
                preferred_army_id = identity_config.canonical_army_id(source_army_id)
                if preferred_army_id not in armies or source_army_id == preferred_army_id:
                    armies[preferred_army_id] = {
                        "id": preferred_army_id,
                        "source_army_id": source_army_id,
                        "name": army_name(row),
                        "slug": row["slug"],
                        "kind": row["kind"],
                        "unit_ids": armies.get(preferred_army_id, {}).get("unit_ids", set()),
                    }
                if row["unit_id"] is not None:
                    armies[preferred_army_id]["unit_ids"].add(row["unit_id"])

            for army in armies.values():
                army_id = army["id"]
                source_army_id = army["source_army_id"]
                metadata_row = metadata.get(source_army_id) or metadata.get(army_id)
                parent_id = metadata_row.get("parent") if metadata_row is not None else None
                canonical_parent_id = (
                    identity_config.canonical_army_id(parent_id)
                    if isinstance(parent_id, int)
                    else None
                )
                parent_army_ids = sorted(reinforcement_parents.get(army_id, ()))

                if army_id == NON_ALIGNED_GROUP_ID:
                    role = ARMY_ROLE_GROUPING
                    playable = False
                    group_id = None
                elif parent_army_ids:
                    role = ARMY_ROLE_REINFORCEMENT
                    playable = True
                    group_id = None
                elif canonical_parent_id == army_id:
                    role = ARMY_ROLE_MAIN
                    playable = True
                    group_id = None
                elif canonical_parent_id == NON_ALIGNED_GROUP_ID:
                    role = ARMY_ROLE_NON_ALIGNED
                    playable = True
                    group_id = NON_ALIGNED_GROUP_ID
                elif canonical_parent_id is not None:
                    role = ARMY_ROLE_SECTORIAL
                    playable = True
                    group_id = canonical_parent_id
                else:
                    role = ARMY_ROLE_UNKNOWN
                    playable = True
                    group_id = None

                group = (
                    (metadata.get(parent_id) or metadata.get(group_id))
                    if group_id is not None
                    else None
                )
                army.update(
                    role=role,
                    playable=playable,
                    group_id=group_id,
                    group_name=group.get("name") if group is not None else None,
                    group_slug=group.get("slug") if group is not None else None,
                    parent_army_ids=parent_army_ids,
                )

            if (
                NON_ALIGNED_GROUP_ID not in armies
                and any(
                    army["group_id"] == NON_ALIGNED_GROUP_ID
                    for army in armies.values()
                )
            ):
                group = metadata.get(NON_ALIGNED_GROUP_ID)
                if group is not None:
                    armies[NON_ALIGNED_GROUP_ID] = {
                        "id": NON_ALIGNED_GROUP_ID,
                        "source_army_id": NON_ALIGNED_GROUP_ID,
                        "name": group.get("name") or f"Army {NON_ALIGNED_GROUP_ID}",
                        "slug": group.get("slug"),
                        "kind": "grouping",
                        "unit_ids": set(),
                        "role": ARMY_ROLE_GROUPING,
                        "playable": False,
                        "group_id": None,
                        "group_name": None,
                        "group_slug": None,
                        "parent_army_ids": [],
                    }

            return [
                {
                    "id": army["id"],
                    "name": army["name"],
                    "slug": army["slug"],
                    "kind": army["kind"],
                    "role": army["role"],
                    "playable": army["playable"],
                    "group_id": army["group_id"],
                    "group_name": army["group_name"],
                    "group_slug": army["group_slug"],
                    "parent_army_ids": army["parent_army_ids"],
                    "unit_count": len(army["unit_ids"]),
                }
                for army in sorted(armies.values(), key=lambda army: army["id"])
            ]

    @instance_lru_cache(maxsize=1)
    def list_skill_extras(self) -> list[dict[str, Any]]:
        """Return candidate distance-related skill and extra pairings."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT combinations.skill_id, COALESCE(NULLIF(s.name, ''), "
                "'Skill #' || combinations.skill_id) AS skill_name, combinations.extra_id, "
                "COALESCE(NULLIF(e.name, ''), 'Extra #' || combinations.extra_id) AS extra_name, "
                f"u.id AS unit_id, {UNIT_NAME_SQL} AS unit_name "
                "FROM ("
                "SELECT ps.item_id AS skill_id, pse.extra_id, ps.unit_id FROM profile_skills AS ps "
                "JOIN profile_skill_extras AS pse ON pse.occurrence_id = ps.occurrence_id "
                "UNION "
                "SELECT os.item_id AS skill_id, ose.extra_id, os.unit_id FROM option_skills AS os "
                "JOIN option_skill_extras AS ose ON ose.occurrence_id = os.occurrence_id "
                "UNION "
                "SELECT uos.item_id AS skill_id, uose.extra_id, uos.unit_id FROM unit_option_skills AS uos "
                "JOIN unit_option_skill_extras AS uose ON uose.occurrence_id = uos.occurrence_id"
                ") AS combinations "
                "LEFT JOIN skills AS s ON s.id = combinations.skill_id "
                "LEFT JOIN extras AS e ON e.id = combinations.extra_id "
                "JOIN units AS u ON u.id = combinations.unit_id AND u.source_defined = 1 "
                "ORDER BY casefold(skill_name), casefold(extra_name), combinations.skill_id, "
                "combinations.extra_id, unit_sort_key(unit_name), u.id"
            ).fetchall()
            combinations: dict[tuple[Any, Any], dict[str, Any]] = {}
            for row in rows:
                if not contains_distance_multiple(row["extra_name"]):
                    continue
                display_extra_name = canonical_skill_extra_name(
                    row["skill_name"], row["extra_name"]
                )
                key = (row["skill_id"], display_extra_name)
                item = combinations.setdefault(
                    key,
                    {
                        "skill_id": row["skill_id"],
                        "skill_name": row["skill_name"],
                        "extra_id": row["extra_id"],
                        "extra_name": display_extra_name,
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
        metadata_tables = {
            "skills": "metadata_skills",
            "equipment": "metadata_equipment",
            "weapons": "metadata_weapons",
        }
        try:
            metadata_table = metadata_tables[catalog]
        except KeyError as exc:
            raise ValueError(f"Unknown catalog: {catalog}") from exc
        identity_config = self._identity_config()

        with self._connect() as connection:
            if catalog == "weapons":
                rows = connection.execute(
                    "SELECT c.id, COALESCE(NULLIF(c.name, ''), MIN(NULLIF(m.name, '')), "
                    "'Weapon #' || c.id) AS name, "
                    "c.category, "
                    "GROUP_CONCAT(DISTINCT NULLIF(m.type, '')) AS type, "
                    "GROUP_CONCAT(DISTINCT NULLIF(m.ammunition, '')) AS ammunition, "
                    "GROUP_CONCAT(DISTINCT NULLIF(m.properties, '')) AS properties "
                    "FROM weapons AS c LEFT JOIN metadata_weapons AS m ON m.id = c.id "
                    "GROUP BY c.id, c.name "
                    "ORDER BY casefold(c.name), c.id"
                ).fetchall()
            else:
                rows = connection.execute(
                    f"SELECT c.id, COALESCE(NULLIF(c.name, ''), NULLIF(m.name, ''), "
                    f"'{catalog[:-1].title()} #' || c.id) AS name, m.wiki "
                    f"FROM {catalog} AS c LEFT JOIN {metadata_table} AS m ON m.id = c.id "
                    "ORDER BY casefold(c.name), c.id"
                ).fetchall()
            items = [dict(row) for row in rows]
            suffix = {"skills": "skill", "equipment": "equipment", "weapons": "weapon"}[catalog]
            option_usage = (
                "SELECT 'option' AS source, t.item_id, o.occurrence_id, o.unit_id, "
                "e.position AS extra_position, e.extra_id "
                "FROM option_weapons AS o JOIN option_weapon_templates AS t "
                "ON t.id = o.template_id "
                "LEFT JOIN option_weapon_extras AS e ON e.occurrence_id = o.occurrence_id"
                if catalog == "weapons"
                else f"SELECT 'option' AS source, o.item_id, o.occurrence_id, o.unit_id, "
                f"e.position AS extra_position, e.extra_id FROM option_{catalog} AS o "
                f"LEFT JOIN option_{suffix}_extras AS e ON e.occurrence_id = o.occurrence_id"
            )
            usage_rows = connection.execute(
                "SELECT uses.source, uses.item_id, uses.occurrence_id, uses.unit_id, uses.extra_id "
                "FROM units AS u JOIN ("
                f"SELECT 'profile' AS source, o.item_id, o.occurrence_id, o.unit_id, "
                f"e.position AS extra_position, e.extra_id FROM profile_{catalog} AS o "
                f"LEFT JOIN profile_{suffix}_extras AS e ON e.occurrence_id = o.occurrence_id "
                f"UNION ALL {option_usage} "
                f"UNION ALL SELECT 'unit_option' AS source, o.item_id, o.occurrence_id, o.unit_id, "
                f"e.position AS extra_position, e.extra_id FROM unit_option_{catalog} AS o "
                f"LEFT JOIN unit_option_{suffix}_extras AS e ON e.occurrence_id = o.occurrence_id"
                ") AS uses ON uses.unit_id = u.id "
                "WHERE u.source_defined = 1 "
                "ORDER BY uses.source, uses.occurrence_id, uses.extra_position"
            ).fetchall()
            occurrences: dict[tuple[str, int], dict[str, Any]] = {}
            for row in usage_rows:
                occurrence = occurrences.setdefault(
                    (row["source"], row["occurrence_id"]),
                    {"item_id": row["item_id"], "unit_id": row["unit_id"], "extras": []},
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
            for item in items:
                item["use_count"] = len(use_keys.get(item["id"], set()))
            groups: dict[str, list[dict[str, Any]]] = {}
            for item in items:
                canonical_id = identity_config.canonical_catalog_id(catalog, item["id"])
                merge_key = (
                    skill_merge_key(item["name"])
                    if catalog == "skills"
                    else catalog_merge_key(item["name"])
                )
                key = f"alias:{canonical_id}" if canonical_id is not None else merge_key
                groups.setdefault(key or f"id:{item['id']}", []).append(item)
            merged = []
            for group in groups.values():
                canonical_id = next(
                    (
                        configured
                        for item in group
                        if (configured := identity_config.canonical_catalog_id(catalog, item["id"]))
                        is not None
                    ),
                    None,
                )
                representative = next(
                    (item for item in group if item["id"] == canonical_id),
                    min(group, key=lambda item: item["id"]),
                )
                if len(group) > 1:
                    representative = {
                        **representative,
                        "name": merged_catalog_name(representative["name"]),
                    }
                representative["use_count"] = sum(item["use_count"] for item in group)
                merged.append(representative)
            return sorted(merged, key=lambda item: (unit_sort_key(item["name"]), item["id"]))

    @instance_lru_cache(maxsize=1)
    def trait_usage_index(self) -> dict[str, tuple[tuple[str, int], ...]]:
        """Return raw Army trait labels mapped to the catalog items that carry them."""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT w.id AS item_id, m.type, m.properties "
                "FROM weapons AS w JOIN metadata_weapons AS m ON m.id = w.id "
            ).fetchall()
        items_by_trait: dict[str, set[tuple[str, int]]] = {}
        for row in rows:
            try:
                traits = json.loads(row["properties"] or "[]")
            except json.JSONDecodeError:
                traits = []
            if not isinstance(traits, list):
                traits = [traits]
            for trait in traits:
                trait_name = source_trait_name(trait)
                if trait_name:
                    catalog = {"EQUIPMENT": "equipment", "SKILL": "skills"}.get(
                        row["type"], "weapons"
                    )
                    items_by_trait.setdefault(trait_name, set()).add((catalog, row["item_id"]))
        return {
            name: tuple(sorted(items))
            for name, items in sorted(items_by_trait.items(), key=lambda item: unit_sort_key(item[0]))
        }

    @instance_lru_cache(maxsize=1)
    def list_traits(self) -> list[dict[str, Any]]:
        """Return distinct raw Army trait labels carried by catalogued profiles."""
        traits = []
        slug_counts: dict[str, int] = {}
        for name, items in self.trait_usage_index().items():
            base_slug = trait_slug(name) or "trait"
            slug_counts[base_slug] = slug_counts.get(base_slug, 0) + 1
            slug = base_slug if slug_counts[base_slug] == 1 else f"{base_slug}-{slug_counts[base_slug]}"
            traits.append({
                "id": slug,
                "name": name,
                "use_count": len(items),
                "description": None,
            })
        return traits

    @instance_lru_cache(maxsize=128)
    def get_trait(self, item_slug: str) -> dict[str, Any] | None:
        """Return one raw Army trait label with matching visible unit usage."""
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
    def get_catalog_item(self, catalog: str, item_id: int) -> dict[str, Any] | None:
        """Return an equipment or weapon item and its extra-specific unit usage."""
        tables = {
            "equipment": ("equipment", "metadata_equipment", "equipment"),
            "weapons": ("weapons", "metadata_weapons", "weapon"),
        }
        if catalog not in tables:
            raise ValueError(f"Unknown catalog: {catalog}")
        if type(item_id) is not int or not 0 <= item_id <= SQLITE_INTEGER_MAX:
            raise ValueError("item_id must be an integer within SQLite's signed 64-bit range")
        identity_config = self._identity_config()
        item_table, metadata_table, suffix = tables[catalog]
        with self._connect() as connection:
            catalog_items = connection.execute(
                f"SELECT id, COALESCE(NULLIF(name, ''), '{catalog[:-1].title()} #' || id) AS name "
                f"FROM {item_table}"
            ).fetchall()
            selected = next((row for row in catalog_items if row["id"] == item_id), None)
            if selected is None:
                return None
            configured_group = configured_catalog_group(
                identity_config,
                catalog,
                item_id,
                {row["id"] for row in catalog_items},
            )
            if configured_group is not None:
                canonical_id, source_ids = configured_group
            else:
                merge_key = catalog_merge_key(selected["name"])
                source_ids = tuple(
                    row["id"]
                    for row in catalog_items
                    if merge_key is not None and catalog_merge_key(row["name"]) == merge_key
                ) or (item_id,)
                canonical_id = min(source_ids)
            placeholders = ", ".join("?" for _ in source_ids)
            wiki_field = "m.wiki AS wiki" if catalog == "equipment" else "NULL AS wiki"
            item = connection.execute(
                f"SELECT c.id, COALESCE(NULLIF(c.name, ''), NULLIF(m.name, ''), "
                f"'{catalog[:-1].title()} #' || c.id) AS name, {wiki_field} "
                f"FROM {item_table} AS c LEFT JOIN {metadata_table} AS m ON m.id = c.id "
                "WHERE c.id = ?",
                (canonical_id,),
            ).fetchone()
            option_usage = (
                "SELECT 'option' AS source, t.item_id, o.occurrence_id, o.unit_id, "
                "e.position AS extra_position, e.extra_id "
                "FROM option_weapons AS o JOIN option_weapon_templates AS t "
                "ON t.id = o.template_id "
                "LEFT JOIN option_weapon_extras AS e ON e.occurrence_id = o.occurrence_id "
                f"WHERE t.item_id IN ({placeholders}) "
                if catalog == "weapons"
                else f"SELECT 'option' AS source, o.item_id, o.occurrence_id, o.unit_id, "
                f"e.position AS extra_position, e.extra_id FROM option_{catalog} AS o "
                f"LEFT JOIN option_{suffix}_extras AS e ON e.occurrence_id = o.occurrence_id "
                f"WHERE o.item_id IN ({placeholders}) "
            )
            rows = connection.execute(
                "SELECT uses.source, uses.item_id, uses.occurrence_id, uses.unit_id, "
                + UNIT_NAME_SQL
                + " AS unit_name, uses.extra_position, e.id AS extra_id, e.name AS extra_name "
                "FROM units AS u JOIN ("
                f"SELECT 'profile' AS source, o.item_id, o.occurrence_id, o.unit_id, "
                f"e.position AS extra_position, e.extra_id FROM profile_{catalog} AS o "
                f"LEFT JOIN profile_{suffix}_extras AS e ON e.occurrence_id = o.occurrence_id "
                f"WHERE o.item_id IN ({placeholders}) "
                f"UNION ALL {option_usage}"
                f"UNION ALL SELECT 'unit_option' AS source, o.item_id, o.occurrence_id, o.unit_id, "
                f"e.position AS extra_position, e.extra_id FROM unit_option_{catalog} AS o "
                f"LEFT JOIN unit_option_{suffix}_extras AS e ON e.occurrence_id = o.occurrence_id "
                f"WHERE o.item_id IN ({placeholders})"
                ") AS uses ON uses.unit_id = u.id "
                "LEFT JOIN extras AS e ON e.id = uses.extra_id "
                "WHERE u.source_defined = 1 "
                "ORDER BY uses.source, uses.occurrence_id, uses.extra_position, "
                "unit_sort_key(unit_name), u.id",
                source_ids * 3,
            ).fetchall()
            occurrences: dict[tuple[str, Any], dict[str, Any]] = {}
            for row in rows:
                occurrence = occurrences.setdefault(
                    (row["source"], row["occurrence_id"]),
                    {
                        "item_id": row["item_id"],
                        "unit": {"id": row["unit_id"], "name": row["unit_name"]},
                        "extras": [],
                    },
                )
                if row["extra_id"] is not None:
                    occurrence["extras"].append(
                        {"id": row["extra_id"], "name": row["extra_name"]}
                    )
            units_by_source = self._visible_unit_items_by_source(frozenset({"specops"}))
            item_names = {row["id"]: row["name"] for row in catalog_items}
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
                variant["units"].sort(
                    key=lambda unit: (unit_sort_key(unit["name"]), unit["id"])
                )
            result = {
                **dict(item),
                "id": canonical_id,
                "name": (
                    merged_catalog_name(item["name"])
                    if len(source_ids) > 1
                    else item["name"]
                ),
                "variants": [variant for variant in variants.values() if variant["units"]],
            }
            if catalog in {"equipment", "weapons"}:
                if catalog == "weapons":
                    profile_filter = (
                        f"m.id IN ({placeholders}) AND (m.type IS NULL OR m.type != 'EQUIPMENT')"
                    )
                    profile_parameters: tuple[Any, ...] = source_ids
                else:
                    profile_filter = "m.id = ? AND m.type = 'EQUIPMENT' AND m.name = ?"
                    profile_parameters = (canonical_id, item["name"])
                profile_rows = connection.execute(
                    "SELECT m.position, m.id, m.type, m.name, m.ammunition, m.burst, m.damage, "
                    "m.saving, m.savingNum, m.properties, m.distance, m.mode, m.profile, "
                    "a.name AS ammunition_name "
                    "FROM metadata_weapons AS m "
                    "LEFT JOIN metadata_ammunitions AS a ON a.id = m.ammunition "
                    f"WHERE {profile_filter} ORDER BY m.position",
                    profile_parameters,
                ).fetchall()

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
    def skill_source_ids(self, skill_id: int) -> tuple[int, ...]:
        """Return source skill IDs represented by one application skill identity."""
        if type(skill_id) is not int or not 0 <= skill_id <= SQLITE_INTEGER_MAX:
            raise ValueError("skill_id must be an integer within SQLite's signed 64-bit range")
        identity_config = self._identity_config()
        with self._connect() as connection:
            skills = connection.execute(
                "SELECT s.id, COALESCE(NULLIF(s.name, ''), NULLIF(m.name, ''), "
                "'Skill #' || s.id) AS name "
                "FROM skills AS s LEFT JOIN metadata_skills AS m ON m.id = s.id"
            ).fetchall()
        skill = next((row for row in skills if row["id"] == skill_id), None)
        if skill is None:
            return ()
        configured_group = configured_catalog_group(
            identity_config,
            "skills",
            skill_id,
            {row["id"] for row in skills},
        )
        if configured_group is not None:
            return configured_group[1]
        merge_key = skill_merge_key(skill["name"])
        return tuple(
            row["id"]
            for row in skills
            if merge_key is not None and skill_merge_key(row["name"]) == merge_key
        ) or (skill_id,)

    @instance_lru_cache(maxsize=128)
    def get_skill(self, skill_id: int) -> dict[str, Any] | None:
        """Return one skill together with the units that use it."""
        if type(skill_id) is not int or not 0 <= skill_id <= SQLITE_INTEGER_MAX:
            raise ValueError("skill_id must be an integer within SQLite's signed 64-bit range")
        identity_config = self._identity_config()
        with self._connect() as connection:
            skills = connection.execute(
                "SELECT s.id, COALESCE(NULLIF(s.name, ''), NULLIF(m.name, ''), "
                "'Skill #' || s.id) AS name, m.wiki "
                "FROM skills AS s LEFT JOIN metadata_skills AS m ON m.id = s.id"
            ).fetchall()
            skill = next((row for row in skills if row["id"] == skill_id), None)
            if skill is None:
                return None
            configured_group = configured_catalog_group(
                identity_config,
                "skills",
                skill_id,
                {row["id"] for row in skills},
            )
            if configured_group is not None:
                canonical_id, source_ids = configured_group
            else:
                merge_key = skill_merge_key(skill["name"])
                source_ids = tuple(
                    row["id"]
                    for row in skills
                    if merge_key is not None and skill_merge_key(row["name"]) == merge_key
                ) or (skill_id,)
                canonical_id = min(source_ids)
            representative = next(row for row in skills if row["id"] == canonical_id)
            placeholders = ", ".join("?" for _ in source_ids)
            rows = connection.execute(
                "SELECT uses.source, uses.skill_id, uses.occurrence_id, uses.unit_id, "
                + UNIT_NAME_SQL
                + " AS unit_name, uses.extra_position, "
                "e.id AS extra_id, e.name AS extra_name "
                "FROM units AS u JOIN ("
                f"SELECT 'profile' AS source, o.item_id AS skill_id, o.occurrence_id, o.unit_id, "
                "e.position AS extra_position, e.extra_id FROM profile_skills AS o "
                "LEFT JOIN profile_skill_extras AS e ON e.occurrence_id = o.occurrence_id "
                f"WHERE o.item_id IN ({placeholders}) "
                "UNION ALL SELECT 'option' AS source, o.item_id AS skill_id, o.occurrence_id, "
                "o.unit_id, e.position AS extra_position, e.extra_id FROM option_skills AS o "
                "LEFT JOIN option_skill_extras AS e ON e.occurrence_id = o.occurrence_id "
                f"WHERE o.item_id IN ({placeholders}) "
                "UNION ALL SELECT 'unit_option' AS source, o.item_id AS skill_id, "
                "o.occurrence_id, o.unit_id, e.position AS extra_position, e.extra_id "
                "FROM unit_option_skills AS o "
                "LEFT JOIN unit_option_skill_extras AS e ON e.occurrence_id = o.occurrence_id "
                f"WHERE o.item_id IN ({placeholders})"
                ") AS uses ON uses.unit_id = u.id "
                "LEFT JOIN extras AS e ON e.id = uses.extra_id "
                "WHERE u.source_defined = 1 "
                "ORDER BY uses.skill_id, uses.source, uses.occurrence_id, uses.extra_position, "
                "unit_sort_key(unit_name), u.id",
                source_ids * 3,
            ).fetchall()
            occurrences: dict[tuple[str, Any], dict[str, Any]] = {}
            for row in rows:
                key = (row["source"], row["occurrence_id"])
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
                    if contains_distance_multiple(row["extra_name"]):
                        extra["is_distance"] = True
                    occurrence["extras"].append(extra)
            variants: dict[tuple[Any, tuple[tuple[Any, Any], ...]], dict[str, Any]] = {}
            skill_names = {row["id"]: row["name"] for row in skills}
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
            unit_items_by_source = self._visible_unit_items_by_source(frozenset({"specops"}))
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
                **dict(representative),
                "id": canonical_id,
                "name": (
                    merged_skill_name(representative["name"])
                    if len(source_ids) > 1
                    else representative["name"]
                ),
                "variants": [variant for variant in variants.values() if variant["units"]],
            }

    @instance_lru_cache(maxsize=128)
    def list_units(
        self,
        army_id: int | None = None,
        search: str = "",
        skill_id: int | None = None,
        equipment_id: int | None = None,
        weapon_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
        mercs: bool = False,
        specops: bool = False,
        teamops: bool = False,
        reinforcement: bool = False,
        descending: bool = False,
        _unbounded: bool = False,
    ) -> dict[str, Any]:
        if army_id is not None and (
            type(army_id) is not int or not SQLITE_INTEGER_MIN <= army_id <= SQLITE_INTEGER_MAX
        ):
            raise ValueError("army_id must be an integer within SQLite's signed 64-bit range")
        if army_id is not None:
            army_id = self._identity_config().canonical_army_id(army_id)
            army = next((item for item in self.list_armies() if item["id"] == army_id), None)
            if army is not None and not army["playable"]:
                raise ArmySelectionError(
                    f"army_id {army_id} is a grouping-only identity, not a selectable army"
                )
        rule_filters = {
            "skills": skill_id,
            "equipment": equipment_id,
            "weapons": weapon_id,
        }
        for name, item_id in rule_filters.items():
            if item_id is not None and (
                type(item_id) is not int or not 0 <= item_id <= SQLITE_INTEGER_MAX
            ):
                parameter = {
                    "skills": "skill",
                    "equipment": "equipment",
                    "weapons": "weapon",
                }[name]
                raise ValueError(
                    f"{parameter}_id must be an integer within SQLite's signed 64-bit range"
                )
        if not isinstance(search, str):
            raise ValueError("search must be a string")
        if type(_unbounded) is not bool:
            raise ValueError("_unbounded must be a boolean")
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
        if any(item_id is not None for item_id in rule_filters.values()):
            with self._connect() as connection:
                for catalog, item_id in rule_filters.items():
                    if item_id is None:
                        continue
                    if catalog == "weapons":
                        query = (
                            "SELECT unit_id FROM profile_weapons WHERE item_id = ? "
                            "UNION SELECT o.unit_id FROM option_weapons AS o "
                            "JOIN option_weapon_templates AS t ON t.id = o.template_id "
                            "WHERE t.item_id = ? "
                            "UNION SELECT unit_id FROM unit_option_weapons WHERE item_id = ?"
                        )
                    else:
                        query = (
                            f"SELECT unit_id FROM profile_{catalog} WHERE item_id = ? "
                            f"UNION SELECT unit_id FROM option_{catalog} WHERE item_id = ? "
                            f"UNION SELECT unit_id FROM unit_option_{catalog} WHERE item_id = ?"
                        )
                    matching_sources_by_rule[catalog] = {
                        row["unit_id"]
                        for row in connection.execute(query, (item_id, item_id, item_id))
                    }
        graph = self._unit_graph()
        faction_groups = self._faction_groups()
        army_names = graph["army_names"]
        groups = graph["groups"]
        canonical_factions = {
            row["id"]: row["canonical_faction_id"] for row in graph["rows"]
        }
        normal_armies_by_unit = graph["normal_armies_by_unit"]
        search_key = accent_insensitive_key(search)
        grouped = []
        for group in groups:
            if any(
                not set(group["source_ids"]).intersection(source_ids)
                for source_ids in matching_sources_by_rule.values()
            ):
                continue
            visible_armies = visible_armies_for_group(
                group, selected_flags, canonical_factions, normal_armies_by_unit
            )
            if group["armies"] and not visible_armies:
                continue
            if army_id is not None and army_id not in visible_armies:
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
                "source_ids": group["source_ids"],
                "army_ids": list(group["armies"]),
                "armies": [
                    {"id": army["id"], "name": army["name"]}
                    for army in group["armies"].values()
                ],
            }
            for group in grouped[offset : offset + limit]
        ]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

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
    def get_unit(self, unit_id: int) -> dict[str, Any] | None:
        """Return a browsable unit and its army-specific profiles and loadouts."""
        if type(unit_id) is not int or not 0 <= unit_id <= SQLITE_INTEGER_MAX:
            raise ValueError("unit_id must be a nonnegative SQLite signed 64-bit integer")
        identity_config = self._identity_config()
        with self._connect() as connection:
            selected = connection.execute(
                f"SELECT u.id, {UNIT_NAME_SQL} AS name, u.isc, u.isc_abbr, u.slug, u.notes, "
                "u.main_army_id "
                "FROM units AS u WHERE u.id = ? AND u.source_defined = 1",
                (unit_id,),
            ).fetchone()
            if selected is None:
                return None
            graph = self._unit_graph()
            faction_groups = self._faction_groups()
            siblings = graph["rows"]
            army_names = graph["army_names"]
            group = graph["groups_by_source"][selected["id"]]
            source_ids = group["source_ids"]
            unit = next(sibling for sibling in siblings if sibling["id"] == group["id"])
            normal_army_ids = graph["normal_armies_by_unit"]
            canonical_factions = {
                row["id"]: row["canonical_faction_id"] for row in siblings
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
                            normal_army_ids[source_id],
                        )
                    )
                )
                occurrence_key = (occurrence["id"], flags)
                army = armies_by_occurrence.setdefault(
                    occurrence_key,
                    {
                        "id": occurrence["id"],
                        "name": occurrence["name"],
                        "faction": faction_groups.get(occurrence["source_army_id"]),
                        "availability_flags": list(flags),
                        "profiles": [],
                        "loadouts": [],
                        "_occurrence_key": occurrence_key,
                    },
                )
                by_source_army[(source_id, occurrence["source_army_id"])] = army
            armies = list(armies_by_occurrence.values())
            profile_rows = connection.execute(
                "SELECT p.unit_id, p.army_id, p.group_id, p.profile_id, p.name, "
                "t.name AS type, c.name AS classification, p.move_1, p.move_2, "
                "p.cc, p.bs, p.ph, p.wip, p.arm, p.bts, p.vitality, p.silhouette, p.ava "
                "FROM profiles AS p "
                "LEFT JOIN troop_types AS t ON t.id = p.type_id "
                "JOIN profile_groups AS pg ON pg.army_id = p.army_id "
                "AND pg.unit_id = p.unit_id AND pg.group_id = p.group_id "
                "LEFT JOIN categories AS c ON c.id = pg.category_id "
                f"WHERE p.unit_id IN ({placeholders}) "
                "ORDER BY p.army_id, p.group_id, p.position, p.profile_id",
                source_ids,
            )
            profile_items: dict[tuple[Any, ...], dict[str, Any]] = {}
            profile_keys_by_source: dict[tuple[int, int, int, int], tuple[Any, ...]] = {}
            for profile in profile_rows:
                army = by_source_army.get((profile["unit_id"], profile["army_id"]))
                if army is None:
                    continue
                profile_item = {
                    key: profile[key]
                    for key in profile.keys()
                    if key not in {"army_id", "unit_id"}
                }
                profile_item["profile_identity"] = normalized_profile_identity(
                    profile["name"], identity_config
                )
                profile_item["skills"] = []
                profile_item["equipment"] = []
                profile_item["weapons"] = []
                profile_item["characteristics"] = []
                profile_key = (
                    army["_occurrence_key"],
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
                profile_keys_by_source[
                    (
                        profile["unit_id"],
                        profile["army_id"],
                        profile["group_id"],
                        profile["profile_id"],
                    )
                ] = profile_key
                existing = profile_items.get(profile_key)
                if existing is None:
                    army["profiles"].append(profile_item)
                    profile_items[profile_key] = profile_item
                else:
                    merge_profile(existing, profile_item)
            for occurrence_table, catalog_table, property_name, extras_table in (
                ("profile_skills", "skills", "skills", "profile_skill_extras"),
                ("profile_equipment", "equipment", "equipment", "profile_equipment_extras"),
                ("profile_weapons", "weapons", "weapons", "profile_weapon_extras"),
            ):
                extras_by_occurrence: dict[Any, list[dict[str, Any]]] = {}
                extra_rows = connection.execute(
                    "SELECT e.occurrence_id, e.extra_id, x.name "
                    f"FROM {extras_table} AS e "
                    f"JOIN {occurrence_table} AS o ON o.occurrence_id = e.occurrence_id "
                    "LEFT JOIN extras AS x ON x.id = e.extra_id "
                    f"WHERE o.unit_id IN ({placeholders}) "
                    "ORDER BY e.occurrence_id, e.position",
                    source_ids,
                )
                for extra in extra_rows:
                    extra_item = {"id": extra["extra_id"], "name": extra["name"]}
                    if property_name == "skills" and contains_distance_multiple(extra["name"]):
                        extra_item["is_distance"] = True
                    extras_by_occurrence.setdefault(extra["occurrence_id"], []).append(extra_item)
                occurrence_rows = connection.execute(
                    "SELECT o.occurrence_id, o.unit_id, o.army_id, o.group_id, o.profile_id, "
                    "o.item_id, o.quantity, o.position, c.name "
                    f"FROM {occurrence_table} AS o "
                    f"LEFT JOIN {catalog_table} AS c ON c.id = o.item_id "
                    f"WHERE o.unit_id IN ({placeholders}) "
                    "ORDER BY o.army_id, o.group_id, o.profile_id, o.position, o.occurrence_id",
                    source_ids,
                )
                for occurrence in occurrence_rows:
                    profile_key = profile_keys_by_source.get(
                        (
                            occurrence["unit_id"],
                            occurrence["army_id"],
                            occurrence["group_id"],
                            occurrence["profile_id"],
                        )
                    )
                    profile_item = (
                        profile_items.get(profile_key) if profile_key is not None else None
                    )
                    if profile_item is not None:
                        append_unique_item(
                            profile_item[property_name],
                            {
                                "id": occurrence["item_id"],
                                "name": occurrence["name"],
                                "quantity": occurrence["quantity"],
                                "extras": extras_by_occurrence.get(occurrence["occurrence_id"], []),
                            },
                        )
            characteristic_rows = connection.execute(
                "SELECT o.unit_id, o.army_id, o.group_id, o.profile_id, c.name "
                "FROM profile_characteristics AS o "
                "JOIN characteristics AS c ON c.id = o.characteristic_id "
                f"WHERE o.unit_id IN ({placeholders}) "
                "ORDER BY o.army_id, o.group_id, o.profile_id, o.position",
                source_ids,
            )
            for characteristic in characteristic_rows:
                profile_key = profile_keys_by_source.get(
                    (
                        characteristic["unit_id"],
                        characteristic["army_id"],
                        characteristic["group_id"],
                        characteristic["profile_id"],
                    )
                )
                profile_item = profile_items.get(profile_key) if profile_key is not None else None
                if profile_item is not None:
                    profile_item["characteristics"].append({"name": characteristic["name"]})
            loadout_rows = connection.execute(
                "SELECT o.unit_id, o.army_id, o.group_id, o.option_id, o.name, o.points, o.swc, "
                "o.minis, o.disabled "
                f"FROM loadout_options AS o WHERE o.unit_id IN ({placeholders}) "
                "ORDER BY o.army_id, o.group_id, o.position, o.option_id",
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
                loadout_key = (
                    army["_occurrence_key"],
                    loadout["group_id"],
                    loadout["option_id"],
                    loadout["name"],
                    loadout["points"],
                    loadout["swc"],
                    loadout["minis"],
                    loadout["disabled"],
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
                "SELECT o.unit_id, o.army_id, o.group_id, o.option_id, o.order_type, "
                "o.list_count, o.total_count "
                f"FROM option_orders AS o WHERE o.unit_id IN ({placeholders}) "
                "ORDER BY o.army_id, o.group_id, o.option_id, o.position",
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
                ("option_skills", "skills", "skills", "option_skill_extras"),
                ("option_equipment", "equipment", "equipment", "option_equipment_extras"),
                ("option_weapons", "weapons", "weapons", "option_weapon_extras"),
            ):
                extras_by_occurrence = {}
                extra_rows = connection.execute(
                    "SELECT e.occurrence_id, e.extra_id, x.name "
                    f"FROM {extras_table} AS e "
                    f"JOIN {occurrence_table} AS o ON o.occurrence_id = e.occurrence_id "
                    "LEFT JOIN extras AS x ON x.id = e.extra_id "
                    f"WHERE o.unit_id IN ({placeholders}) "
                    "ORDER BY e.occurrence_id, e.position",
                    source_ids,
                )
                for extra in extra_rows:
                    extra_item = {"id": extra["extra_id"], "name": extra["name"]}
                    if property_name == "skills" and contains_distance_multiple(extra["name"]):
                        extra_item["is_distance"] = True
                    extras_by_occurrence.setdefault(extra["occurrence_id"], []).append(extra_item)
                item_column = "o.item_id"
                quantity_column = "o.quantity"
                occurrence_source = f"FROM {occurrence_table} AS o"
                if occurrence_table == "option_weapons":
                    item_column = "t.item_id"
                    quantity_column = "t.quantity"
                    occurrence_source += (
                        " JOIN option_weapon_templates AS t ON t.id = o.template_id"
                    )
                occurrence_rows = connection.execute(
                    "SELECT o.occurrence_id, o.unit_id, o.army_id, o.group_id, o.option_id, "
                    f"{item_column} AS item_id, {quantity_column} AS quantity, o.position, c.name "
                    f"{occurrence_source} "
                    f"LEFT JOIN {catalog_table} AS c ON c.id = {item_column} "
                    f"WHERE o.unit_id IN ({placeholders}) "
                    "ORDER BY o.army_id, o.group_id, o.option_id, o.position, o.occurrence_id",
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
                        append_unique_item(
                            loadout_item[property_name],
                            {
                                "id": occurrence["item_id"],
                                "name": occurrence["name"],
                                "quantity": occurrence["quantity"],
                                "extras": extras_by_occurrence.get(occurrence["occurrence_id"], []),
                            },
                        )
            main_faction = faction_groups.get(group["main_army_id"])
            for army in armies:
                del army["_occurrence_key"]
        return {
            "id": unit["id"],
            "name": unit["name"],
            "isc": unit["isc"],
            "slug": unit["slug"],
            "isc_abbr": unit["isc_abbr"],
            "notes": unit["notes"],
            "main_army_id": group["main_army_id"],
            "main_army_name": army_names.get(group["main_army_id"]),
            "main_faction": main_faction,
            "source_ids": source_ids,
            "armies": armies,
        }

