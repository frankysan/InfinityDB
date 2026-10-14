"""Materialize InfinityDB's canonical catalog identities and source provenance."""

from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from infinity_army_data.project_resources import maintained_config_path
from infinity_db.identities import IdentityConfig

CATALOGS = ("skills", "equipment", "weapons")
DEFAULT_METADATA_ONLY_WEAPONS = maintained_config_path(
    "catalogs", "metadata-only-weapons.json"
)


@dataclass(frozen=True)
class ApplicationCatalogModel:
    items: tuple[dict[str, Any], ...]
    sources: tuple[dict[str, Any], ...]


def _dict_rows(
    connection: sqlite3.Connection, statement: str, parameters: Collection[Any] = ()
) -> list[dict[str, Any]]:
    cursor = connection.execute(statement, tuple(parameters))
    columns = tuple(column[0] for column in cursor.description or ())
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _skill_merge_key(name: object) -> str | None:
    text = str(name or "").strip()
    if not re.search(r"\d", text):
        return None
    return re.sub(r"\s+", " ", re.sub(r"\d+", "", text)).casefold()


def _merged_skill_name(name: object) -> str:
    text = re.sub(r"\s+", " ", re.sub(r"\d+", "", str(name or "")).strip())
    text = re.sub(r"\s+L$", "", text, flags=re.IGNORECASE)
    return text.rstrip(" =:-()").strip()


def _catalog_merge_key(name: object) -> str | None:
    text = str(name or "").strip()
    if ":" in text:
        return text.split(":", 1)[0].strip().casefold() or None
    return _skill_merge_key(text)


def _merged_catalog_name(name: object) -> str:
    text = str(name or "").strip()
    if ":" in text:
        return text.split(":", 1)[0].strip()
    return _merged_skill_name(text)


_PUBLICATION_PROFILE_KEYS = {
    "mode", "type", "ammunition", "burst", "damage", "saving",
    "savingNum", "traits", "distance",
}


def _reviewed_metadata_only_weapons(
    connection: sqlite3.Connection,
    path: Path = DEFAULT_METADATA_ONLY_WEAPONS,
) -> list[dict[str, Any]]:
    """Publish only explicitly reviewed, exact-match unused Army Weapon profiles."""
    document = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict)
        or set(document) != {"format", "version", "weapons"}
        or document["format"] != "InfinityDB reviewed metadata-only weapon publication"
        or type(document["version"]) is not int
        or document["version"] != 1
        or not isinstance(document["weapons"], list)
    ):
        raise ValueError("Invalid metadata-only Weapon publication configuration")

    result: list[dict[str, Any]] = []
    seen: set[int] = set()
    for entry in document["weapons"]:
        if (
            not isinstance(entry, dict)
            or set(entry) != {"id", "name", "category", "profile", "source"}
            or type(entry["id"]) is not int
            or entry["id"] <= 0
            or entry["id"] in seen
            or any(not isinstance(entry[k], str) or not entry[k].strip()
                   for k in ("name", "category", "source"))
            or not isinstance(entry["profile"], dict)
            or set(entry["profile"]) != _PUBLICATION_PROFILE_KEYS
        ):
            raise ValueError("Invalid or duplicate metadata-only Weapon publication")
        seen.add(entry["id"])
        expected = entry["profile"]
        if (
            expected["mode"] is not None
            or expected["type"] != "WEAPON"
            or type(expected["ammunition"]) is not int
            or expected["ammunition"] <= 0
            or any(not isinstance(expected[k], str) or not expected[k]
                   for k in ("burst", "damage", "saving", "savingNum"))
            or not isinstance(expected["traits"], list)
            or any(not isinstance(trait, str) or not trait for trait in expected["traits"])
            or not isinstance(expected["distance"], dict)
        ):
            raise ValueError(f"Invalid metadata-only Weapon profile for {entry['id']}")
        rows = _dict_rows(
            connection,
            "SELECT id, name, mode, type, ammunition, burst, damage, "
            "saving, savingNum, properties, distance "
            "FROM metadata_weapons WHERE id = ?",
            (entry["id"],),
        )
        # An older source snapshot or a minimal fixture may not contain the
        # reviewed weapon. Do not synthesize an upstream profile in that case.
        if not rows:
            continue
        if len(rows) != 1:
            raise ValueError(f"Reviewed Weapon {entry['id']} has multiple source profiles")
        row = rows[0]
        actual = {k: row[k] for k in _PUBLICATION_PROFILE_KEYS
                  if k not in {"traits", "distance"}}
        actual["traits"] = json.loads(row["properties"] or "[]")
        actual["distance"] = json.loads(row["distance"] or "null")
        if row["name"] != entry["name"] or actual != expected:
            raise ValueError(f"Reviewed metadata-only Weapon {entry['id']} source profile drift")
        existing = connection.execute(
            "SELECT 1 FROM weapons WHERE id = ?", (entry["id"],)
        ).fetchone()
        if existing is None:
            result.append({
                "id": entry["id"],
                "name": entry["name"],
                "wiki": None,
                "category": entry["category"],
                "has_metadata": 1,
            })
    return result


def _source_catalog_rows(connection: sqlite3.Connection, catalog: str) -> list[dict[str, Any]]:
    if catalog == "weapons":
        rows = _dict_rows(
            connection,
            "SELECT c.id, COALESCE(NULLIF(c.name, ''), MIN(NULLIF(m.name, '')), "
            "'Weapon #' || c.id) AS name, NULL AS wiki, c.category, "
            "CAST(CASE WHEN COUNT(m.position) > 0 THEN 1 ELSE 0 END AS INTEGER) AS has_metadata "
            "FROM weapons AS c LEFT JOIN metadata_weapons AS m ON m.id = c.id "
            "GROUP BY c.id, c.name, c.category ORDER BY c.id",
        )
        return sorted(
            [*rows, *_reviewed_metadata_only_weapons(connection)],
            key=lambda row: row["id"],
        )
    metadata_table = {"skills": "metadata_skills", "equipment": "metadata_equipment"}[catalog]
    fallback = "Skill" if catalog == "skills" else "Equipment"
    return _dict_rows(
        connection,
        f"SELECT c.id, COALESCE(NULLIF(c.name, ''), NULLIF(m.name, ''), "
        f"'{fallback} #' || c.id) AS name, m.wiki, NULL AS category, "
        f"CAST(CASE WHEN m.id IS NOT NULL THEN 1 ELSE 0 END AS INTEGER) AS has_metadata "
        f"FROM {catalog} AS c LEFT JOIN {metadata_table} AS m ON m.id = c.id ORDER BY c.id",
    )


def _catalog_reference_labels(
    connection: sqlite3.Connection,
    catalog: str,
    used_rows: list[dict[str, Any]],
) -> dict[int, str]:
    """Return the complete source catalog labels available for identity resolution."""

    if catalog == "weapons":
        metadata_rows = _dict_rows(
            connection,
            "SELECT id, MIN(NULLIF(name, '')) AS name "
            "FROM metadata_weapons GROUP BY id ORDER BY id",
        )
    else:
        metadata_table = {"skills": "metadata_skills", "equipment": "metadata_equipment"}[
            catalog
        ]
        metadata_rows = _dict_rows(
            connection,
            f"SELECT id, name FROM {metadata_table} ORDER BY id",
        )
    labels = {
        int(row["id"]): str(row["name"])
        for row in metadata_rows
        if row.get("name") not in (None, "")
    }
    for row in used_rows:
        labels.setdefault(int(row["id"]), str(row["name"]))
    return labels


def derive_application_catalogs(
    connection: sqlite3.Connection,
    identity_config: IdentityConfig,
) -> ApplicationCatalogModel:
    items: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for catalog in CATALOGS:
        rows = _source_catalog_rows(connection, catalog)
        resolved_aliases = identity_config.resolve_catalog_aliases(
            catalog, _catalog_reference_labels(connection, catalog, rows)
        )
        groups: dict[tuple[str, Any], list[dict[str, Any]]] = defaultdict(list)
        merge_key_for = _skill_merge_key if catalog == "skills" else _catalog_merge_key
        merged_name_for = _merged_skill_name if catalog == "skills" else _merged_catalog_name
        for row in rows:
            configured_canonical = resolved_aliases.get(row["id"])
            if configured_canonical is not None:
                key = ("alias", configured_canonical)
            else:
                merge_key = merge_key_for(row["name"])
                key = ("merge", merge_key) if merge_key is not None else ("id", row["id"])
            groups[key].append(row)
        for key in sorted(groups, key=lambda item: (item[0], str(item[1]))):
            group = sorted(groups[key], key=lambda row: row["id"])
            canonical_id = (
                int(key[1])
                if key[0] == "alias"
                else min(row["id"] for row in group)
            )
            representative = next((row for row in group if row["id"] == canonical_id), group[0])
            name = (
                merged_name_for(representative["name"])
                if len(group) > 1
                else representative["name"]
            )
            items.append(
                {
                    "catalog": catalog,
                    "id": canonical_id,
                    "name": name,
                    "wiki": representative.get("wiki"),
                    "category": representative.get("category"),
                    "preferred_source_id": representative["id"],
                }
            )
            for row in group:
                sources.append(
                    {
                        "catalog": catalog,
                        "application_item_id": canonical_id,
                        "source_item_id": row["id"],
                        "source_name": row["name"],
                        "has_metadata": row["has_metadata"],
                    }
                )
    return ApplicationCatalogModel(
        items=tuple(
            sorted(items, key=lambda row: (row["catalog"], row["id"]))
        ),
        sources=tuple(
            sorted(
                sources,
                key=lambda row: (row["catalog"], row["application_item_id"], row["source_item_id"]),
            )
        ),
    )


def materialize_application_catalogs(
    connection: sqlite3.Connection,
    identity_config: IdentityConfig,
) -> ApplicationCatalogModel:
    model = derive_application_catalogs(connection, identity_config)
    connection.executemany(
        "INSERT INTO application_catalog_items "
        "(catalog, id, name, wiki, category, preferred_source_id) "
        "VALUES (:catalog, :id, :name, :wiki, :category, :preferred_source_id)",
        model.items,
    )
    connection.executemany(
        "INSERT INTO application_catalog_sources "
        "(catalog, application_item_id, source_item_id, source_name, has_metadata) "
        "VALUES (:catalog, :application_item_id, :source_item_id, :source_name, :has_metadata)",
        model.sources,
    )
    return model


def validate_application_catalogs(
    connection: sqlite3.Connection,
    identity_config: IdentityConfig,
) -> None:
    del identity_config
    source_count = 0
    mapped_count = 0
    for catalog in CATALOGS:
        source_count += connection.execute(f"SELECT COUNT(*) FROM {catalog}").fetchone()[0]
        mapped_count += connection.execute(
            "SELECT COUNT(*) FROM application_catalog_sources WHERE catalog = ?",
            (catalog,),
        ).fetchone()[0]
    # Reviewed metadata-only publications add one mapped source identity
    # without inventing a row in the upstream usage-derived weapons table.
    source_count += len(_reviewed_metadata_only_weapons(connection))
    empty_item = connection.execute(
        "SELECT 1 FROM application_catalog_items AS aci "
        "LEFT JOIN application_catalog_sources AS acs "
        "ON acs.catalog = aci.catalog AND acs.application_item_id = aci.id "
        "WHERE acs.source_item_id IS NULL LIMIT 1"
    ).fetchone()
    invalid_preferred = connection.execute(
        "SELECT 1 FROM application_catalog_items AS aci "
        "LEFT JOIN application_catalog_sources AS acs "
        "ON acs.catalog = aci.catalog AND acs.application_item_id = aci.id "
        "AND acs.source_item_id = aci.preferred_source_id "
        "WHERE acs.source_item_id IS NULL LIMIT 1"
    ).fetchone()
    if source_count != mapped_count or empty_item is not None or invalid_preferred is not None:
        raise ValueError(
            "Database has invalid materialized application catalog identity; rebuild the database"
        )
