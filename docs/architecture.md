# Architecture and direction

## Project goals

1. **Database backend:** maintain validated, queryable Infinity data, including
   army-specific variants and the source metadata needed to trace it.
2. **Extensible web UI:** provide a unit explorer and rules-reference catalogs
   through focused API endpoints and views.

Data tools are a subsystem of InfinityDB. They remain usable independently for
inspection, validation, and rebuilding snapshots.

## Data flow

```text
Army directory / ZIP
    + required metadata.json
    -> merge + lossless verification
    -> master.json
    -> normalize + relationship validation
    -> normalized.json + validation report
    -> SQLite importer
    -> infinity.db + infinity.raw.db
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
| `infinity_db.web.static` | UI, shared page-shell components, URL state, loading and error handling | New screens, filters, and catalogs |

Only the importer consumes normalized JSON. HTTP routes query the repository;
browser code calls the API. Neither web layer parses raw Army files. Browser
requests live in `api.js`; shared unit-row rendering lives in `unit-list.js`;
page-specific state and rendering live in the corresponding module (for
example, `app.js` or `catalog-detail.js`). The current UI uses native modules
and requires no JavaScript build step. Bundled army and unit symbols are
addressed by stable ID-and-slug paths, while JavaScript maps source identities
to those paths.

## Browser design system

The WSGI page renderer composes every browser route from a page-specific
document, the shared navigation, and shared header/footer fragments. The page
header receives structured breadcrumb and catalog-tag data from the route; the
footer receives the application version. New pages should use the
`<!-- navigation -->`, `<!-- page-header -->`, and `<!-- page-footer -->`
markers so their shell stays synchronized with existing pages.

`static/styles.css` is the browser design-system entry point. Its root tokens
define shared color roles, surfaces, borders, spacing, radii, control height,
focus treatment, and shadows. Reuse these tokens and established components
such as `.main`, `.topbar`, `.explorer`, `.button`, and `.page-footer` rather
than introducing page-local visual values. Detail pages use `.main-detail` to
retain the common layout and responsive behavior. Detail renderers also reuse
`.detail-group`, `.detail-section-title`, `.data-surface-header`, `.data-label`,
and `.badge`; use their modifiers for semantic variants instead of duplicating
detail-table geometry or type treatments.

Surface hierarchy uses `.surface` with default, `--subtle`, or `--highlighted`
variants. Tables use the comfortable default or `.data-table--compact` for
detail and usage data; retain those variants instead of adding page-specific
cell padding or header type rules.

Unit-list and general-profile surfaces may use the unit's named main-army
colors as accents. Keep those accents within the shared token and gradient
system so catalog-specific styling remains legible and consistent.

Browser preferences are stored locally. The Settings sidebar section provides
distance units and a default-off Developer mode; on compact screens it becomes
a top-bar menu beside Navigation. New sidebar or top-bar menus should use this
same inline-sidebar and compact-dropdown pattern. Developer mode sets
`data-developer-mode` on the document root; use `.developer-only` for inline
technical details and `.id-column` for table columns so they remain hidden in
the player-facing view by default.

The required API `metadata.json` is a supplemental snapshot. Its records are
preserved separately and enrich display names for matching army IDs. It never
creates an army list or changes unit membership, which continue to come solely
from the army JSON files. Database builds fail when no metadata snapshot is
provided beside, inside, or explicitly alongside the Army source.

SQLite is the initial backend because it runs locally without a separate service.
Schema definitions are separate from ingestion code. The current schema has a
schema version of 8 and database compatibility revision of 9; it rejects
incompatible databases with a rebuild instruction. The importer builds a lean
frontend database and a lossless sibling raw archive, creates read-path indexes
after loading, and persists SQLite planner statistics. Migration
of persistent user-authored data is future work; database rebuilds currently
replace a complete imported snapshot.

## HTTP API

All routes are same-origin and read-only. `GET` returns JSON or a static asset;
`HEAD` returns the corresponding headers without a body.

HTML is revalidated on each request. API representations have snapshot-specific
ETags and short shared-cache lifetimes; fingerprinted static assets are immutable
for a release. Pages compare both the application version and snapshot revision
with the version endpoint, then reload through a fresh URL after a deployment or
data refresh.

### `GET /api/version`

Returns `{ "version": "0.4.1", "snapshot_revision": "..." }`. The browser
uses it to detect application or imported-snapshot changes.

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
- Search matches accent- and punctuation-insensitive, case-folded name
  substrings, including Unicode.
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

### `GET /api/units/{unit_id}`

Returns one logical unit, including its general data and the profiles,
loadouts, availability, skills, equipment, and weapons that apply to each army
where it occurs. A reinforcement-only source variant is folded into a uniquely
matching standard unit. Unknown unit IDs return 404.

### `GET /api/skill-extras`

Returns `{ "items": [...] }` of distinct skill/extra combinations whose extra
contains a distance value, together with the units using each combination.
The Skill Modifiers browser page consumes this endpoint.

### Rules-reference endpoints

`GET /api/skills`, `GET /api/equipment`, and `GET /api/weapons` return
`{ "items": [...] }` for their searchable catalogs. Catalog records combine
equivalent source labels where appropriate and include an ID, display name, and
reference link when the metadata snapshot provides one.

`GET /api/skills/{id}`, `GET /api/equipment/{id}`, and
`GET /api/weapons/{id}` return one catalog item and its distinct usage variants.
Each variant includes the relevant extras and logical units that use it. Weapon
details additionally include metadata weapon profiles, such as ammunition,
traits, and range data, when present in the supplied metadata snapshot.

## Next increments

1. Expose fireteams and relationships while showing unresolved source references
   explicitly.
2. Add migrations and another database adapter when their requirements are
   known, while keeping user-owned data separate from replaceable imported
   snapshots.
3. Extend the browser only where it can make source relationships and rules
   context clearer for players.
