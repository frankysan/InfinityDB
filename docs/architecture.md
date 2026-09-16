# Architecture and direction

## Project goals

1. **Database backend:** maintain validated, queryable Infinity data, including
   army-specific variants and the source metadata needed to trace it.
2. **Extensible web UI:** provide a unit explorer and rules-reference catalogs
   through focused API endpoints and views.

## Guiding principles

1. **Accuracy:** use official data sources and strive to represent those
   sources as accurately as possible. When source data is incomplete or
   ambiguous, preserve that uncertainty rather than presenting an unsupported
   conclusion as fact.
2. **Flexibility:** expand the ways users can browse and understand the data
   while keeping the experience simple, fast, and customizable.
3. **Transparency:** keep the project open source under the MIT License and
   clearly distinguish InfinityDB's work from outside data, quoted text, and
   image assets, which remain the property of their respective owners.

## Engineering principles

1. **Preserve the source.** Raw upstream data and assets are immutable inputs;
   transformations happen in separate stages.
2. **Never lose information silently.** Merging, normalization, deduplication,
   filtering, and cleanup must preserve provenance and report anything
   discarded, unresolved, or ambiguous.
3. **Code defines behavior; manifests define knowledge.** Domain-specific
   aliases, mappings, filters, overrides, exceptions, and other independently
   maintained project knowledge should live in validated configuration when
   they can change independently of implementation behavior.
4. **One source of truth per build.** Every stage of a build must use the same
   pinned inputs and explicit configuration so the result is reproducible.
5. **Prefer explicit relationships over assumptions.** Model what the source
   actually represents, including many-to-many and source-specific
   relationships, rather than flattening data for implementation convenience.
6. **Build conservatively.** When validation or interpretation is uncertain,
   preserve source or existing valid data rather than guessing or
   destructively correcting it.
7. **Separate stages and responsibilities.** Acquisition, validation,
   normalization, processing, publishing, and deployment should remain
   independently understandable and testable.
8. **Be deterministic and portable.** Given the same inputs and configuration,
   the project should produce the same logical result on Windows, Linux, and
   macOS.

These principles are the canonical engineering decision criteria for the
project. `AGENTS.md` contains immediate operational instructions, while
`docs/AI_CONTEXT.md` records durable invariants and non-obvious decisions.

Data tools are a subsystem of InfinityDB. They remain usable independently for
inspection, validation, and rebuilding snapshots. The standalone scripts in
`tools/` keep their own dedicated regression coverage under `tests/` so their
filesystem safety, URL handling, and cross-platform naming remain validated
independently from the core database and web pipeline.

## Configuration and generated state

InfinityDB separates executable behavior from maintained project knowledge and
from build output:

```text
code        = behavior
config      = maintained project/domain knowledge
raw data    = immutable external input
generated   = reproducible build output
```

Aliases, mappings, filters, manual overrides, compatibility exceptions, static
asset declarations, and similar domain knowledge should use validated,
versioned manifests or configuration when they can change independently of the
code that interprets them.

This is not a requirement to make every constant configurable. Values that
define implementation behavior remain in code. Manifests are for domain
knowledge, policy, source declarations, mappings, and independently maintained
exceptions.

Important manifest/configuration contracts should define a schema or schema
version, validate on load, serialize deterministically when generated, and have
focused regression tests. Generated build manifests record provenance and
state; hand-authored configuration remains distinct from generated output.

Persistent project paths stored in manifests use portable project-relative
representations rather than machine-specific absolute paths.

`config/identity/source-identities.json` is the first repository-wide example
of this split. It owns maintained logical-identity exceptions for source unit,
army-list, skill, equipment, and weapon IDs plus identity-name aliases. Generic
matching and duplicate-detection algorithms remain code. The ordinary
whole-army `xx01` derivation also remains code; exceptional interpretation
policy, such as the legacy mercenary canonical-faction mapping, lives in the
manifest and is supplied explicitly to the generic normalizer.

The authored identity manifest is a build input, not a deployed runtime file.
InfinityDB normalization validates it, supplies normalization-time exceptions,
and writes the exact document and its deterministic SHA-256 into
`normalized.json`. Database export revalidates that pinned provenance, rejects
incomplete or conflicting identity metadata, and propagates the same policy to
the frontend and raw database metadata. Repository queries revalidate and
consume the policy pinned into that immutable database snapshot. This keeps
deployments self-contained and prevents later working-tree configuration
changes from silently changing the meaning of an existing normalized or SQLite
snapshot.

## Data flow

```text
Army directory / ZIP
    + required metadata.json
    -> merge + lossless verification
    -> master.json
       + validated identity configuration
    -> normalize + relationship validation
    -> normalized.json + validation report
       + pinned identity document / SHA-256
    -> SQLite importer
       + revalidated pinned identity provenance
    -> infinity.db + infinity.raw.db
    -> repository -> HTTP API -> browser UI

PDF rules documents
    -> curated, cited rules facts
  -> `infinity-db build-rules`
  -> separate `rules.db`
    -> rules repository -> HTTP API -> browser UI
```

The two flows are deliberately independent. `build-rules` consumes only
validated JSON collections under `data/curated/` and skips the reserved
`example.json` template; it never reads PDFs or wiki snapshots directly. A
rules-document update must not rebuild an Army snapshot, and an Army import must
not modify rules data. Where a screen needs both, the application/service layer
joins stable application-level identities and returns a combined
representation; the databases do not import from or attach to one another.

Asset acquisition and processing is likewise a separate build concern. Raw
downloaded assets are preserved independently from working and published
outputs. Asset discovery, source resolution, validation, deduplication,
conversion, compression, and publishing should remain distinct stages, with
provenance recorded rather than inferred from final filenames.

## Module boundaries

| Layer | Responsibility | Extension point |
| --- | --- | --- |
| `infinity_army_data` | Interpret and validate source data | Source-format changes and additional normalization |
| `infinity_db.database.schema` | Table definitions, composite keys, references, schema version | New normalized entities and future migration policy |
| `infinity_db.database.importer` | Validate and store a complete snapshot | Alternative storage adapters, such as PostgreSQL |
| `infinity_db.database.repository` | Read-only application queries | Unit details, profile comparisons, catalog queries |
| `infinity_db.web.app` | Validate HTTP input and serialize query results | Additional routes and API resources |
| `infinity_db.web.static` | UI, shared page-shell components, URL state, loading and error handling | New screens, filters, and catalogs |
| standalone `tools/` | Explicit acquisition, validation, and asset-processing workflows | New independent build/input tools |
| deployment scripts | Package and deploy validated application output | Additional deployment targets |

Only the importer consumes normalized JSON. HTTP routes query the repository;
browser code calls the API. Neither web layer parses raw Army files. Browser
requests live in `api.js`; shared unit-row rendering lives in `unit-list.js`;
page-specific state and rendering live in the corresponding module (for
example, `app.js` or `catalog-detail.js`). The current UI uses native modules
and requires no JavaScript build step. Bundled army and unit symbols are
addressed by stable ID-and-slug paths, while JavaScript maps source identities
to those paths.

Acquisition tools must not become hidden network dependencies of normal builds.
A normal build should be able to consume explicit local snapshots. Network
refreshes are separate, intentional operations.

## Portability and filesystem policy

Python tooling should support Windows, Linux, and macOS unless a component is
explicitly documented otherwise.

Core pipeline logic should use portable filesystem/process APIs rather than
shell-specific command strings or machine-specific paths. External executable
discovery should be centralized and allow explicit configuration before
platform-specific fallbacks.

Generated asset names and persistent manifest paths must be host-independent.
Treat filenames as case-sensitive internally and detect case-only collisions
before publishing.

Raw inputs are immutable. Persistent generated files should be built and
validated separately and atomically replace prior output where practical.
Failure should leave the previous valid output usable.

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
distance units, a default-off Developer mode, and a developer-only cache-bypass
control; on compact screens it becomes a top-bar menu beside Navigation. New
sidebar or top-bar menus should use this same inline-sidebar and
compact-dropdown pattern. Developer mode sets `data-developer-mode` on the
document root; use `.developer-only` for inline technical details and
`.id-column` for table columns so they remain hidden in the player-facing view
by default.

The required API `metadata.json` is a supplemental snapshot. Its records are
preserved separately and enrich display names for matching army IDs. It never
creates an army list or changes unit membership, which continue to come solely
from the army JSON files. Database builds fail when no metadata snapshot is
provided beside, inside, or explicitly alongside the Army source.

SQLite is the initial backend because it runs locally without a separate
service. Schema definitions are separate from ingestion code. The current
schema has a schema version of 8 and database compatibility revision of 10; it
rejects incompatible databases with a rebuild instruction. The importer builds
a lean frontend database and a lossless sibling raw archive, creates read-path
indexes after loading, and persists SQLite planner statistics. Migration of
persistent user-authored data is future work; database rebuilds currently
replace a complete imported snapshot.

When PDF-derived rules references are introduced, they use a distinct SQLite
database with its own schema, compatibility/versioning, importer, and atomic
replacement policy. Each curated fact records its document edition/date and
printed-page citation. This database is not an extension of `infinity.db` or
`infinity.raw.db`.

The first boundary is the source-controlled `data/curated/` JSON layer. It is
the only application-facing representation of facts researched from PDFs or
the wiki. `data/pdf/` and `data/wiki/` remain local reference material and are
not opened by application code; `infinity_db.curated.load_curated_document`
validates the intermediary contract before a future rules importer consumes it.

The current corpus is intentionally split into N5 core rules, N5 FAQ/errata,
ITS season, historical, and wiki collections. Curated v2 stores collection
scope, source metadata, typed records, Army catalog links, related-rule links,
review state, and citations. Printed page numbers are required for PDF sources;
wiki records require a snapshot-local path and date. No collection may
silently combine current, historical, FAQ, and season rules. Version 1 curated
files must be migrated before ingestion.

## HTTP API

All routes are same-origin and read-only. `GET` returns JSON or a static asset;
`HEAD` returns the corresponding headers without a body.

HTML is revalidated on each request. API representations have
snapshot-specific ETags and short shared-cache lifetimes; fingerprinted static
assets are immutable for a release. Pages compare both the application version
and snapshot revision with the version endpoint, then reload through a fresh URL
after a deployment or data refresh.

### `GET /api/version`

Returns `{ "version": "0.5.1", "snapshot_revision": "..." }`. The browser uses
it to detect application or imported-snapshot changes.

### `GET /api/armies`

Returns `{ "items": [...] }`. Each item has `id`, `name`, `slug`, `kind`, and
`unit_count`. Only actual imported army lists appear; referenced faction
placeholders do not become selectable armies. Unit counts use source-defined
units in `army_units`.

### `GET /api/units?army_id=101&search=fusilier&limit=50&offset=0`

Returns `{ "items": [...], "total": 0, "limit": 50, "offset": 0 }`, where each
item has `id`, `name`, `main_army_id`, `army_ids`, and `armies` (`id` and
`name` per membership). The zero total above illustrates the response shape.

- Omit `army_id` to browse all source-defined units, deduplicated by global ID.
- Army membership comes from `army_units`, not canonical faction or declared
  faction references.
- `main_army_id` is derived from canonical ownership and always references a
  whole-army faction group (`xx01`); it is null when that mapping is unavailable.
- Search matches accent- and punctuation-insensitive, case-folded name
  substrings, including Unicode.
- Results sort by display name after case-folding, removing diacritics, and
  ignoring punctuation and other non-alphanumeric characters; unit ID breaks
  ties for stable pagination.
- Source records that share a 10,000-ID family and ISC identity are presented
  as one logical unit. Reinforcement-only variants join their matching standard
  unit; its list entry and details page combine all army-specific data.
- `limit` defaults to 50 and must be between 1 and 200; `offset` defaults to 0
  and must be a nonnegative SQLite integer.
- `search` is limited to 200 characters. Invalid or repeated unit query
  parameters return HTTP 400 with `{ "error": "..." }`. Unknown army IDs return
  an empty list.
- Optional `skill_id`, `equipment_id`, and `weapon_id` parameters narrow
  results to units with matching catalog items in a profile, loadout, or unit
  option.
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

`GET /api/traits` returns the derived shared-traits catalog.
`GET /api/traits/{slug}` returns a trait's concise rules summary, when
available, and its use grouped across skills, equipment, and weapons.

## Next increments

1. Expose fireteams and relationships while showing unresolved source references
   explicitly.
2. Add migrations and another database adapter when their requirements are
   known, while keeping user-owned data separate from replaceable imported
   snapshots.
3. Extend the browser only where it can make source relationships and rules
   context clearer for players.
