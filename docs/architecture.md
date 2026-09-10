# Architecture and direction

## Project goals

1. **Database backend:** maintain validated, queryable Infinity data, including
   army-specific variants and the source metadata needed to trace it.
2. **Extensible web UI:** begin with a unit list filterable by army, then add
   functionality through focused API endpoints and views.

Data tools are a subsystem of InfinityDB. They remain usable independently for
inspection, validation, and rebuilding snapshots.

## Data flow

```text
Army directory / ZIP
    + optional metadata.json
    -> merge + lossless verification
    -> master.json
    -> normalize + relationship validation
    -> normalized.json + validation report
    -> SQLite importer
    -> infinity.db
    -> repository -> HTTP API -> browser UI
```

## Module boundaries

| Layer | Responsibility | Extension point |
| --- | --- | --- |
| `infinity_army_data` | Interpret and validate source data | Source-format changes and additional normalization |
| `infinity_db.database.schema` | Table definitions, composite keys, references, schema version | New normalized entities and future migration policy |
| `infinity_db.database.importer` | Validate and store a complete snapshot | Alternative storage adapters, such as PostgreSQL |
| `infinity_db.database.repository` | Read-only application queries | Unit details, profile comparisons, catalog queries |
| `infinity_db.web.app` | Validate HTTP input and serialize query results | Additional routes and API resources |
| `infinity_db.web.static` | UI, URL state, loading and error handling | New screens and filters |

Only the importer consumes normalized JSON. HTTP routes query the repository;
browser code calls the API. Neither web layer parses raw Army files. Browser
requests live in `api.js`; page state and rendering live in `app.js`. The current
UI uses native modules and requires no JavaScript build step.

The optional API `metadata.json` is a supplemental snapshot. Its records are
preserved separately and enrich display names for matching army IDs. It never
creates an army list or changes unit membership, which continue to come solely
from the army JSON files.

SQLite is the initial backend because it runs locally without a separate service.
Schema definitions are separate from ingestion code. The current schema has a
version and rejects incompatible databases with a rebuild instruction. Migration
of persistent user-authored data is future work; database rebuilds currently
replace a complete imported snapshot.

## Initial HTTP API

All routes are same-origin and read-only. `GET` returns JSON or a static asset;
`HEAD` returns the corresponding headers without a body.

### `GET /api/armies`

Returns `{ "items": [...] }`. Each item has `id`, `name`, `slug`, `kind`, and
`unit_count`. Only actual imported army lists appear; referenced faction
placeholders do not become selectable armies. Unit counts use source-defined
units in `army_units`.

### `GET /api/units?army_id=101&search=fusilier&limit=50&offset=0`

Returns `{ "items": [...], "total": 0, "limit": 50, "offset": 0 }`, where each item
has `id`, `name`, `main_army_id`, `army_ids`, and `armies` (`id` and `name` per membership).
The zero total above illustrates the response shape.

- Omit `army_id` to browse all source-defined units, deduplicated by global ID.
- Army membership comes from `army_units`, not canonical faction or declared
  faction references.
- `main_army_id` is derived from canonical ownership and always references a
  whole-army faction group (`xx01`); it is null when that mapping is unavailable.
- Search matches literal, case-insensitive name substrings, including Unicode.
- Results sort by display name after case-folding, removing diacritics, and ignoring
  punctuation and other non-alphanumeric characters; unit ID breaks ties for stable
  pagination.
- Source records that share a 10,000-ID family and ISC identity are presented as one
  logical unit. Reinforcement-only variants join their matching standard unit; its
  list entry and details page combine all army-specific data.
- `limit` defaults to 50 and must be between 1 and 200; `offset` defaults to 0 and
  must be a nonnegative SQLite integer.
- `search` is limited to 200 characters. Invalid or repeated unit query parameters
  return HTTP 400 with `{ "error": "..." }`. Unknown army IDs return an empty list.
- Unknown resources return 404; unsupported methods return 405; database read
  failures return 503 without exposing internal exception details.

## Next increments

1. Add unit detail routes and views showing profiles and loadouts in a selected
   army context, retaining army-specific points, AVA, and rules.
2. Add equipment, weapon, and skill reference pages using existing normalized
   catalog and occurrence tables.
3. Expose fireteams and relationships while showing unresolved source references
   explicitly.
4. Add migrations, deployment, and another database adapter when their requirements
   are known. Keep user-owned data separate from replaceable imported snapshots.
