"""Materialize InfinityDB's canonical catalog identities and source provenance."""

from __future__ import annotations

import re
import sqlite3
from collections import defaultdict
from collections.abc import Collection
from dataclasses import dataclass
from typing import Any

from infinity_db.identities import IdentityConfig

CATALOGS = ("skills", "equipment", "weapons")


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


def _configured_catalog_group(
    identity_config: IdentityConfig,
    catalog: str,
    item_id: int,
    available_ids: Collection[int],
) -> tuple[int, tuple[int, ...]] | None:
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


def _source_catalog_rows(connection: sqlite3.Connection, catalog: str) -> list[dict[str, Any]]:
    if catalog == "weapons":
        return _dict_rows(
            connection,
            "SELECT c.id, COALESCE(NULLIF(c.name, ''), MIN(NULLIF(m.name, '')), "
            "'Weapon #' || c.id) AS name, NULL AS wiki, c.category, "
            "CAST(CASE WHEN COUNT(m.position) > 0 THEN 1 ELSE 0 END AS INTEGER) AS has_metadata "
            "FROM weapons AS c LEFT JOIN metadata_weapons AS m ON m.id = c.id "
            "GROUP BY c.id, c.name, c.category ORDER BY c.id",
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


def derive_application_catalogs(
    connection: sqlite3.Connection,
    identity_config: IdentityConfig,
) -> ApplicationCatalogModel:
    items: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for catalog in CATALOGS:
        rows = _source_catalog_rows(connection, catalog)
        rows_by_id = {row["id"]: row for row in rows}
        available_ids = set(rows_by_id)
        groups: dict[tuple[str, Any], list[dict[str, Any]]] = defaultdict(list)
        explicit_groups: dict[tuple[str, Any], tuple[int, tuple[int, ...]]] = {}
        merge_key_for = _skill_merge_key if catalog == "skills" else _catalog_merge_key
        merged_name_for = _merged_skill_name if catalog == "skills" else _merged_catalog_name
        for row in rows:
            configured = _configured_catalog_group(
                identity_config, catalog, row["id"], available_ids
            )
            if configured is not None:
                key = ("alias", configured[0])
                explicit_groups[key] = configured
            else:
                merge_key = merge_key_for(row["name"])
                key = ("merge", merge_key) if merge_key is not None else ("id", row["id"])
            groups[key].append(row)
        for key in sorted(groups, key=lambda item: (item[0], str(item[1]))):
            group = sorted(groups[key], key=lambda row: row["id"])
            configured = explicit_groups.get(key)
            canonical_id = (
                configured[0]
                if configured is not None
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
