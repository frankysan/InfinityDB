"""SQLite schema for normalized Infinity Army data, independent of source parsing."""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from dataclasses import dataclass

SCHEMA_VERSION = 10
# Increment this revision whenever a code change requires rebuilding an existing
# database, even if the SQLite schema itself is unchanged.  It deliberately
# does not track the user-facing application release version.
DATABASE_COMPATIBILITY_VERSION = 14
APPLICATION_ID = 0x49444231
ROW_JSON = "__row_json"
RAW_ROWS_TABLE = "__infinity_raw_rows"
METADATA_TABLE = "__infinity_metadata"
DATABASE_COMPATIBILITY_KEY = "database_compatibility_version"


@dataclass(frozen=True)
class Reference:
    fields: tuple[str, ...]
    table: str
    target: tuple[str, ...]


@dataclass(frozen=True)
class Table:
    key: tuple[str, ...]
    fields: tuple[str, ...]
    references: tuple[Reference, ...] = ()


def ref(fields: str, table: str, target: str | None = None) -> Reference:
    return Reference(tuple(fields.split()), table, tuple((target or fields).split()))


def table(key: str, fields: str = "", *references: Reference) -> Table:
    return Table(tuple(key.split()), tuple(fields.split()), references)


TABLES = {
    "factions": table(
        "id", "has_army_list canonical_reference_count unit_membership_reference_count"
    ),
    "army_lists": table(
        "id",
        "name slug kind version reinforcement_id source_file source_sha256 resume teamops "
        "legacy_fireteams filter_attrs filter_points filter_swc fireteam_description fireteam_spec",
        ref("id", "factions"),
        ref("reinforcement_id", "factions", "id"),
    ),
    "units": table(
        "id",
        "id_army canonical_faction_id main_army_id isc isc_abbr name slug notes spectables "
        "source_defined source_role "
        "relation_reference_count",
        ref("canonical_faction_id", "factions", "id"),
        ref("main_army_id", "factions", "id"),
    ),
    "unit_factions": table(
        "unit_id faction_id",
        "position",
        ref("unit_id", "units", "id"),
        ref("faction_id", "factions", "id"),
    ),
    "army_units": table(
        "army_id unit_id",
        "position filters availability_kind",
        ref("army_id", "army_lists", "id"),
        ref("unit_id", "units", "id"),
    ),
    "profile_groups": table(
        "army_id unit_id group_id",
        "position category_id isc notes",
        ref("army_id unit_id", "army_units"),
        ref("category_id", "categories", "id"),
    ),
    "profiles": table(
        "army_id unit_id group_id profile_id",
        "position name logo type_id move_1 move_2 cc bs ph wip arm bts vitality silhouette ava "
        "is_structure notes",
        ref("army_id unit_id group_id", "profile_groups"),
        ref("type_id", "troop_types", "id"),
    ),
    "loadout_options": table(
        "army_id unit_id group_id option_id",
        "position name points swc minis disabled",
        ref("army_id unit_id group_id", "profile_groups"),
    ),
    "unit_options": table(
        "unit_id option_id",
        "position name points swc minis disabled compatible habilities raw",
        ref("unit_id", "units", "id"),
    ),
    "peripherals": table("army_id id", "position name mercs", ref("army_id", "army_lists", "id")),
    "fireteams": table(
        "army_id fireteam_id", "position name observation", ref("army_id", "army_lists", "id")
    ),
    "fireteam_types": table(
        "army_id fireteam_id position", "fireteam_type", ref("army_id fireteam_id", "fireteams")
    ),
    "fireteam_members": table(
        "army_id fireteam_id member_id",
        "position slug name comment min_count max_count required resolved_unit_id resolution",
        ref("army_id fireteam_id", "fireteams"),
        ref("resolved_unit_id", "units", "id"),
    ),
    "relations": table(
        "army_id relation_id",
        "position min_count max_count is_group",
        ref("army_id", "army_lists", "id"),
    ),
    "relation_units": table(
        "army_id relation_id relation_unit_id",
        "position unit_id profile_id per_parent",
        ref("army_id relation_id", "relations"),
        ref("unit_id", "units", "id"),
    ),
    "relation_dependencies": table(
        "army_id relation_id relation_unit_id dependency_id",
        "position unit_id profile_id group_id min_count min_dependant options raw",
        ref("army_id relation_id relation_unit_id", "relation_units"),
        ref("unit_id", "units", "id"),
    ),
}

# Supplementary Army API metadata. These deliberately have no foreign keys: its
# faction hierarchy can reference records omitted by a particular API snapshot,
# and weapon IDs legitimately repeat for alternate modes.
TABLES.update(
    {
        "metadata_factions": table("id", "parent name slug discontinued logo"),
        "metadata_ammunitions": table("id", "name"),
        "metadata_weapons": table(
            "position",
            "id type name mode ammunition burst damage saving savingNum "
            "properties distance profile",
        ),
        "metadata_skills": table("id", "name wiki"),
        "metadata_equipment": table("id", "name wiki"),
        "metadata_hacking_programs": table("position"),
        "metadata_martial_arts": table("position"),
        "metadata_metachemistry": table("id", "name value"),
        "metadata_booty": table("id", "name value"),
    }
)

for catalog in (
    "categories",
    "characteristics",
    "troop_types",
    "equipment",
    "skills",
    "weapons",
    "ammunition",
    "extras",
):
    if catalog == "weapons":
        fields = "name source_defined category"
    elif catalog == "extras":
        fields = "name source_defined type"
    else:
        fields = "name source_defined"
    TABLES[catalog] = table("id", fields)
    TABLES[f"army_{catalog}"] = table(
        "army_id item_id",
        "position mercs specops teamops",
        ref("army_id", "army_lists", "id"),
        ref("item_id", catalog, "id"),
    )

for prefix, parent, parent_key in (
    ("profile", "profiles", "army_id unit_id group_id profile_id"),
    ("option", "loadout_options", "army_id unit_id group_id option_id"),
    ("unit_option", "unit_options", "unit_id option_id"),
):
    parent_ref = ref(parent_key, parent)
    for suffix, catalog, extra_suffix in (
        ("skills", "skills", "skill_extras"),
        ("equipment", "equipment", "equipment_extras"),
        ("weapons", "weapons", "weapon_extras"),
    ):
        occurrence_table = f"{prefix}_{suffix}"
        TABLES[occurrence_table] = table(
            "occurrence_id",
            f"{parent_key} position item_id display_order quantity raw",
            parent_ref,
            ref("item_id", catalog, "id"),
        )
        TABLES[f"{prefix}_{extra_suffix}"] = table(
            "occurrence_id position",
            "extra_id",
            ref("occurrence_id", occurrence_table),
            ref("extra_id", "extras", "id"),
        )
    TABLES[f"{prefix}_characteristics"] = table(
        f"{parent_key} position",
        "characteristic_id",
        parent_ref,
        ref("characteristic_id", "characteristics", "id"),
    )
    include_refs = [parent_ref]
    if prefix != "unit_option":
        include_refs.append(
            ref(
                "army_id unit_id target_group_id target_option_id",
                "loadout_options",
                "army_id unit_id group_id option_id",
            )
        )
        TABLES[f"{prefix}_peripherals"] = table(
            "occurrence_id",
            f"{parent_key} position item_id display_order quantity raw",
            parent_ref,
            ref("army_id item_id", "peripherals", "army_id id"),
        )
    TABLES[f"{prefix}_includes"] = table(
        f"{parent_key} position", "target_group_id target_option_id quantity raw", *include_refs
    )
    if prefix != "profile":
        TABLES[f"{prefix}_orders"] = table(
            f"{parent_key} position", "order_type list_count total_count raw", parent_ref
        )

# Option weapon payloads recur heavily across army-specific loadouts. Keep the
# occurrence (its parent and display position) separate from reusable payload.
TABLES["option_weapon_templates"] = table(
    "id", "item_id display_order quantity raw", ref("item_id", "weapons", "id")
)
TABLES["option_weapons"] = table(
    "occurrence_id",
    "army_id unit_id group_id option_id position template_id",
    ref("army_id unit_id group_id option_id", "loadout_options"),
    ref("template_id", "option_weapon_templates", "id"),
)


DERIVED_TABLES = {
    "logical_units": table(
        "id",
        "representative_unit_id",
        ref("representative_unit_id", "units", "id"),
    ),
    "logical_unit_sources": table(
        "source_unit_id",
        "logical_unit_id",
        ref("source_unit_id", "units", "id"),
        ref("logical_unit_id", "logical_units", "id"),
    ),
}

DATABASE_TABLES = {**TABLES, **DERIVED_TABLES}

# Primary keys preserve the source hierarchy, which normally starts with
# ``army_id``. The public read API also traverses the data by unit and performs
# reverse catalog lookups by item, neither of which can use those key prefixes.
# Keep these indexes deliberately limited to the predicates used by repository
# queries; this is a read-only snapshot, so their small import cost is repaid by
# every cold-cache detail request.
INDEXES = (
    ("profiles_unit", "profiles", "unit_id, army_id, group_id, position, profile_id"),
    (
        "loadout_options_unit",
        "loadout_options",
        "unit_id, army_id, group_id, position, option_id",
    ),
    ("profile_characteristics_unit", "profile_characteristics", "unit_id"),
    ("option_characteristics_unit", "option_characteristics", "unit_id"),
    ("option_orders_unit", "option_orders", "unit_id"),
    ("profile_skills_unit", "profile_skills", "unit_id"),
    ("profile_skills_item", "profile_skills", "item_id"),
    ("profile_equipment_unit", "profile_equipment", "unit_id"),
    ("profile_equipment_item", "profile_equipment", "item_id"),
    ("profile_weapons_unit", "profile_weapons", "unit_id"),
    ("profile_weapons_item", "profile_weapons", "item_id"),
    ("option_skills_unit", "option_skills", "unit_id"),
    ("option_skills_item", "option_skills", "item_id"),
    ("option_equipment_unit", "option_equipment", "unit_id"),
    ("option_equipment_item", "option_equipment", "item_id"),
    ("option_weapons_unit", "option_weapons", "unit_id"),
    ("option_weapons_template", "option_weapons", "template_id"),
    ("option_weapon_templates_item", "option_weapon_templates", "item_id"),
    ("unit_option_skills_item", "unit_option_skills", "item_id"),
    ("unit_option_equipment_item", "unit_option_equipment", "item_id"),
    ("unit_option_weapons_item", "unit_option_weapons", "item_id"),
)


def quote(identifier: str) -> str:
    """Quote identifiers; source field names are data, never executable SQL."""
    if not isinstance(identifier, str) or not identifier or "\x00" in identifier:
        raise ValueError("Table and field names must be nonempty strings without NUL bytes")
    return '"' + identifier.replace('"', '""') + '"'


def columns_for(name: str, rows: list[dict]) -> tuple[str, ...]:
    definition = DATABASE_TABLES[name]
    columns = list(dict.fromkeys((*definition.key, *definition.fields)))
    for row in rows:
        for field in row:
            quote(field)
            if field.casefold() == ROW_JSON:
                raise ValueError(f"{name}.{field} is reserved for database storage")
            if field not in columns:
                if field.casefold() in {column.casefold() for column in columns}:
                    raise ValueError(f"Ambiguous field name in {name}: {field}")
                columns.append(field)
    return tuple(columns)


def create_schema(
    connection: sqlite3.Connection,
    tables: dict[str, list[dict]],
    *,
    table_columns: Mapping[str, tuple[str, ...]] | None = None,
) -> None:
    """Create all tables, including empty ones, with deferred relational constraints.

    Values have no SQLite affinity, avoiding coercion of source strings such as SWC.
    Nested JSON occupies text columns. Lossless source rows are stored in the
    separate development archive, not in the frontend database. Secondary
    indexes are deliberately created after the bulk load by ``create_indexes``.
    """
    connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    connection.execute(
        f"CREATE TABLE {quote(METADATA_TABLE)} (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    for name, definition in DATABASE_TABLES.items():
        columns = (
            table_columns[name]
            if table_columns is not None and name in table_columns
            else columns_for(name, tables.get(name, []))
        )
        parts = [
            quote(field) + (" NOT NULL" if field in definition.key else "") for field in columns
        ]
        parts.append("PRIMARY KEY (" + ", ".join(map(quote, definition.key)) + ")")
        for reference in definition.references:
            parts.append(
                "FOREIGN KEY (" + ", ".join(map(quote, reference.fields)) + ") "
                "REFERENCES "
                + quote(reference.table)
                + " ("
                + ", ".join(map(quote, reference.target))
                + ") "
                "DEFERRABLE INITIALLY DEFERRED"
            )
        connection.execute(f"CREATE TABLE {quote(name)} ({', '.join(parts)})")


def create_indexes(connection: sqlite3.Connection) -> None:
    """Create read-path indexes after data loading completes."""
    connection.execute("CREATE INDEX units_name ON units(name COLLATE NOCASE, id)")
    connection.execute("CREATE INDEX army_units_unit ON army_units(unit_id, army_id)")
    connection.execute(
        "CREATE INDEX logical_unit_sources_logical "
        "ON logical_unit_sources(logical_unit_id, source_unit_id)"
    )
    for index_name, table_name, columns in INDEXES:
        connection.execute(f"CREATE INDEX {quote(index_name)} ON {quote(table_name)} ({columns})")
