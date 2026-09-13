# Data model notes

## Pipeline

```text
raw Army JSON
    -> lossless merged master.json
    -> normalized relational-style JSON
    -> validated SQLite database
    -> read-only repository / HTTP API / web UI
```

## Identities

- `unit.id` is treated as the global unit identity.
- Unit `profileGroups` and unit-level `filters` are army-list-specific variants.
- Profile group, profile and loadout option IDs are local to their army/unit hierarchy and use composite keys in normalized data.
- Skills, weapons, equipment, ammunition, characteristics, troop types, categories and extras use stable global lookup IDs.
- Skill, equipment, and weapon occurrences retain their owning profile,
  loadout, or unit option, display order, quantity, and linked extras. This
  supports both unit details and reverse lookup from the rules-reference
  catalogs.
- Peripheral IDs are army-local.
- Referenced but undefined factions/units/categories are retained as explicit placeholder records rather than discarded.

## Principle

The merged master layer is lossless and source-oriented. The normalized layer is query-oriented. Database-specific choices should live in exporters/adapters rather than in source parsing.

## SQLite storage

`infinity_db.database` imports every normalized table with its original field names,
declared primary keys, and foreign keys. Nested arrays and objects use JSON text.
Every row also has a `__row_json` field retaining the exact normalized record,
including absent versus null fields. `__infinity_metadata` retains import metadata
and warnings. The schema defines empty tables as well, so API queries do not depend
on a particular snapshot containing every kind of record.

`PRAGMA application_id` identifies an InfinityDB file and `PRAGMA user_version`
records its schema version. The current schema version is 6 and the application
compatibility revision is 7. Imports build a temporary sibling file, check
database integrity, then replace the destination. Incompatible schemas or
compatibility revisions require a rebuild from normalized JSON for now.
Release 0.3.2 does not change either database version.

The unit browser queries `units`, `army_units`, and `army_lists`. It excludes
source-undefined placeholder units and uses actual army occurrences for filtering,
preserving the distinction between list membership and canonical identity.

The rules-reference browsers query the global `skills`, `equipment`, and
`weapons` catalogs together with their `profile_*`, `option_*`, and
`unit_option_*` occurrence tables. Equivalent source labels can be merged for
display, but the underlying source IDs and individual occurrences remain
available for validation and detail rendering.

## Required Army API metadata

`metadata.json` is a required supplementary API snapshot for database builds.
When it is beside an Army directory or ZIP archive, `infinity-db build`
discovers it automatically; otherwise use `--metadata PATH`. It is copied
losslessly into `master.json` and `normalized.json`, and its nine collections
are available as `metadata_*` SQLite tables. Database export also rejects
normalized data that does not contain valid Army metadata.

Faction names enrich matching `army_lists` by numeric ID. Army list files remain
the authority for which armies and units are selectable: metadata-only factions
never create army lists or unit memberships. Metadata weapon IDs can repeat for
different modes, so their table uses source position as its key.
