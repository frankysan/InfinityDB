# Architecture

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
3. **Code defines behavior; configuration defines maintained knowledge.**
   Domain-specific aliases, mappings, filters, overrides, exceptions, and other
   independently maintained project knowledge should live in validated
   configuration when they can change independently of implementation behavior.
   Generated manifests record provenance/build state rather than maintained
   policy.
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

## Documentation status

This document records both implemented architecture and accepted architectural
direction, but those are not interchangeable:

- **Current** describes implemented repository/application behavior.
- **Design direction** describes an accepted boundary or target shape that is
  not fully implemented yet.
- Concrete implementation work belongs in `docs/TODO.md`; this document should
  not maintain a second backlog.

Unless a paragraph is explicitly marked as design direction or future work,
architectural statements describe the current implementation.

## Configuration, curated data, manifests, and generated state

### Current

InfinityDB currently separates executable behavior, maintained project
knowledge, immutable source material, human-reviewed rules data, and reproducible
build output:

```text
code                  = behavior
config/               = maintained project/domain knowledge
raw source data       = immutable external input
data/curated/rules/   = source-controlled human-reviewed rules data
data/generated/       = reproducible database/JSON build output
```

Aliases, mappings, filters, manual overrides, compatibility exceptions, static
asset declarations, and similar maintained domain knowledge belong in
validated, versioned configuration when they can change independently of the
code that interprets them.

`data/curated/rules/` is different from configuration: it contains
human-reviewed information derived from identified external sources and retains
source provenance. It is the only curated subtree currently consumed by the
rules-database build.

This is not a requirement to make every constant configurable. Values that
define implementation behavior remain in code. Configuration is for maintained
domain knowledge and policy; curated rules data is for human-reviewed
source-derived facts.

`config/identity/source-identities.json` is the first repository-wide example
of the code/config split. It owns maintained logical-identity exceptions for
source unit, army-list, skill, equipment, and weapon IDs plus identity-name
aliases. Generic matching and duplicate-detection algorithms remain code. The
ordinary whole-army `xx01` derivation also remains code; exceptional
interpretation policy lives in configuration and is supplied explicitly to the
generic normalizer.

Source canonical-faction ID `1` and Non-Aligned Armies grouping ID `901` are
now kept distinct in normalization. ID `1` remains mercenary source/origin
provenance with no application `main_army_id`; the generic whole-army `xx01`
derivation is explicitly suppressed for that source identity. ID `901` remains
the metadata grouping identity for Non-Aligned armies. The former legacy
`1` -> `901` identity-config override has been removed.

The authored identity configuration is a build input, not a deployed runtime
file. InfinityDB normalization validates it, supplies normalization-time
exceptions, and writes the exact document and its deterministic SHA-256 into
`normalized.json`. Database export revalidates that pinned provenance, rejects
incomplete or conflicting identity metadata, and propagates the same policy to
the frontend and raw database metadata. Repository queries revalidate and
consume the policy pinned into that immutable database snapshot. Unit-detail
queries also derive each profile's `profile_identity` from that pinned policy;
browser grouping consumes the backend-derived identity and keeps only display
formatting, so browser assets do not duplicate profile alias or ignored-word
rules. This keeps deployments self-contained and prevents later working-tree
configuration changes from silently changing the meaning of an existing
normalized or SQLite snapshot.

Army presentation and classification currently combine imported relationships
with merger-derived fields. Faction grouping, display names, and slugs come from
`metadata_factions.parent`, `name`, and `slug`; repository responses expose this
as `main_faction` for unit summaries/details and `faction` for each army
occurrence. The merger sets `army_lists.kind` to `army` for source documents
that contain a top-level `reinforcements` field and to `reinforcement` for those
that do not. That field therefore captures the current ordinary-list versus
reinforcement-file shape, but it is not an upstream main-army/sectorial
classification. Browser code consumes these backend fields and must not infer
faction or reinforcement semantics from Army ID prefixes or suffixes.

Mercenary units and Non-Aligned Armies are also separate source concepts.
Ordinary unit records declare their normal faction availability through
`factions`. The source additionally contains dedicated mercenary variants that
consistently use canonical faction `1`, an empty `factions` list, a `merc-...`
slug, and army-specific occurrences that supply optional mercenary
availability. Many also use 10,000-offset-style unit IDs, but that numeric
pattern is supporting evidence only. Normalization records mercenary source roles, army-occurrence availability
provenance, and audited mercenary-to-standard source-unit matches. Repository
queries consume the persisted match metadata for mercenary logical grouping and
`army_units.availability_kind` for current-snapshot mercenary filtering; the old
canonical/faction inference remains only as a legacy-row fallback.

### Design direction

Two additional data roles are accepted but are not yet implemented as produced
artifacts:

```text
data/manifests/              = generated provenance and build state
data/curated/snapshot-notes/ = human-reviewed snapshot annotations
```

Generated manifests are not maintained project knowledge. Snapshot-acquisition
provenance will live under `data/manifests/snapshots/`; build-specific state such
as the planned Army-symbol build manifest may live under `data/manifests/` as
well. Human-written snapshot descriptions and notable-change notes will live
under `data/curated/snapshot-notes/` and remain separate from generated state.

No current downloader writes `data/manifests/snapshots/`, and no current runtime
or build consumes `data/curated/snapshot-notes/`. Version-control, ignore, and
packaging policy for generated manifests therefore remains an implementation
decision to finalize when the manifest writer is introduced; the current
`.gitignore`/`.dockerignore` behavior is not evidence of a completed manifest
lifecycle.

Important configuration, curated-data, and generated-manifest contracts should
define a schema or schema version, validate on load, serialize deterministically
where generated, and have focused regression tests. Persistent project paths
stored in future manifests should use portable project-relative
representations rather than machine-specific absolute paths.

Army role/playability is derived in the backend from source relationships
rather than numeric ID patterns. Metadata self-parent/child relationships
identify main armies and sectorials, metadata parent `901` groups the distinct
Non-Aligned army lists, and ordinary source documents identify their
reinforcement list through the explicit `reinforcements` field. `/api/armies`
exposes those roles, playability, grouping metadata, and reinforcement parents;
the browser selector consumes that contract directly. Grouping-only identity
`901` is exposed as non-playable and cannot be used as a selectable
`army_id`.

Mercenary source variants are classified during normalization from their
source-semantic contract (`canonical == 1`, empty declared `factions`,
`merc-...` slug), with schema drift reported instead of guessed. Audited
mercenary-to-standard source-unit matches and explicit army-occurrence
availability provenance are persisted and consumed by repository queries. The
10,000-ID offset is supporting matching evidence only, not the semantic rule.

The legacy `1` -> `901` canonical-faction override has now been removed. ID `1`
remains source provenance for mercenary identity and does not receive an
application `main_army_id`; 901 remains a separate Non-Aligned Army grouping
identity. Remaining logical-unit work concerns the broader generic duplicate,
configured-alias, and reinforcement identity layer rather than mercenary
availability inference.

## Snapshot acquisition and provenance

### Current

Standalone Army, wiki, and symbol acquisition uses a common immutable snapshot
model. Downloaders stage loose files temporarily and persist complete timestamped
archives named `JSON YYYYMMDD-HHMMSS.zip`, `WIKI YYYYMMDD-HHMMSS.zip`, or
`SYMBOLS YYYYMMDD-HHMMSS.zip`. A same-second collision receives `-2`, `-3`, and
so on rather than overwriting an existing archive.

The archive is the durable acquisition artifact. Corvus Belli's Army
`metadata.json` remains source data contained in or supplied alongside Army
snapshots; it is not InfinityDB-owned snapshot metadata.

Current curated-v2 wiki citations identify wiki material with a snapshot-local
path and `snapshotDate`. The checked-in rules collection still contains legacy
provenance from the earlier unpacked wiki mirror. That is current historical
source identity and must not be silently rewritten to a timestamped ZIP that was
not actually recorded at curation time.

### Design direction

Downloader-known snapshot provenance will be generated outside the immutable
archive in a versioned record under `data/manifests/snapshots/` and will bind to
the archive by SHA-256. Appropriate generated fields include archive
identity/path, snapshot type, acquisition timestamp, source/base URL, language,
source-document count, and downloader-known source facts.

Human interpretation has a different lifecycle. Descriptions, comparison
targets, and notable-change notes will live under
`data/curated/snapshot-notes/` and also bind to the immutable snapshot by
SHA-256. Generated tooling must not overwrite human-written notes, and editing
those notes must never mutate the raw archive or generated provenance.
Automated comparison output may later be recorded in generated manifests or
reports while curated notes remain the human interpretation.

Exact timestamped archive identity/hash for wiki-derived curated rules is also a
design direction, not a current guarantee. Migrate the legacy wiki provenance
when the wiki downloader/packager and curated provenance contract are rewritten
together; do not fabricate that association in documentation alone.

## Data flow

The current application data flows are:

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

PDF / wiki research sources
    -> human-reviewed cited collections in data/curated/rules/
    -> `infinity-db build-rules`
    -> separate rules.db
    -> rules repository -> HTTP API -> browser UI
```

The two database flows are deliberately independent. `build-rules` consumes
only validated JSON collections under `data/curated/rules/` and skips the
reserved `example.json` template; it never reads PDFs, wiki snapshots, or other
curated subtrees directly. A rules-document update must not rebuild an Army
snapshot, and an Army import must not modify rules data. Where a screen needs
both, the application/service layer joins stable application-level identities
and returns a combined representation; the databases do not import from or
attach to one another.

Asset acquisition and processing is likewise a separate build concern. Current
tooling preserves raw downloaded assets independently from working/published
outputs and bundles processed assets for the browser.

**Design direction:** an integrated symbol build tied to an Army snapshot will
use that exact pinned snapshot throughout discovery and publication. Discovery
will preserve every source reference/URL independently of later deduplication;
canonical processing may collapse equivalent assets, but it must not discard
their source references. Only the publisher will assign final application paths
and generated browser mappings because only that stage knows the final
canonical asset. Discovery, source resolution, validation, deduplication,
conversion, compression, and publishing remain distinct intended stages with
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
A normal build can consume explicit local snapshots. Network refreshes are
separate, intentional operations.

## Portability and filesystem policy

Python tooling should support Windows, Linux, and macOS unless a component is
explicitly documented otherwise.

Core pipeline logic should use portable filesystem/process APIs rather than
shell-specific command strings or machine-specific paths. External executable
discovery should be centralized and allow explicit configuration before
platform-specific fallbacks.

Generated asset names and persistent generated-state paths should be
host-independent. Treat filenames as case-sensitive internally and detect
case-only collisions before publishing.

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

## Required Army API metadata

The required API `metadata.json` is a supplemental source snapshot. Its records
are preserved separately and enrich display names for matching army IDs.
Faction records also provide explicit parent relationships, names, and slugs
used for unit presentation and grouping. Metadata never creates an army list or
changes unit membership, which continue to come solely from the army JSON
files. Database builds fail when no metadata snapshot is provided beside,
inside, or explicitly alongside the Army source.

Corvus Belli's `metadata.json` is source data. It is conceptually distinct from
the planned InfinityDB-generated snapshot-provenance records under
`data/manifests/snapshots/`, which are not implemented yet.

## SQLite persistence

SQLite is the initial backend because it runs locally without a separate
service. Schema definitions are separate from ingestion code. The current
schema has a schema version of 9 and database compatibility revision of 12; it
rejects incompatible databases with a rebuild instruction. The importer builds
a lean frontend database and a lossless sibling raw archive, creates read-path
indexes after loading, and persists SQLite planner statistics. Migration of
persistent user-authored data is future work; database rebuilds currently
replace a complete imported snapshot.

Rules-reference data uses a distinct SQLite database with its own schema,
compatibility/versioning, importer, and atomic replacement policy. This database
is not an extension of `infinity.db` or `infinity.raw.db`.

The source-controlled `data/curated/rules/` JSON layer is the only
application-facing representation of facts researched from PDFs or the wiki.
`data/pdf/` and `data/wiki/` remain local reference material and are not opened
by application code; `infinity_db.curated.load_curated_document` validates the
rules intermediary contract before the rules importer consumes it.

The current curated-v2 rules contract stores collection scope, source metadata,
typed records, maintained vocabularies, Army catalog links, related-rule links,
review state, and citations. PDF record citations require printed page numbers.
Wiki record citations currently require a snapshot-local path and snapshot date.
The current `vocabularySources` shape is older and requires a mixed locator set
including `path`, `snapshotDate`, `heading`, and a positive `page`; it should not
be mistaken for the desired long-term source-specific citation model.

The checked-in wiki source record still points to the earlier unpacked local
mirror identity. **Design direction:** when the wiki downloader/packager and
curated provenance contract are rewritten, migrate wiki source/vocabulary
provenance to exact timestamped archive identity/hash and source-appropriate
locators. Until then, preserve the recorded legacy provenance rather than
claiming an exact archive association that has not been established.

No collection may silently combine current, historical, FAQ, and season rules.
Version 1 curated-rule files must be migrated before ingestion.

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

Returns `{ "items": [...] }`. Each item exposes `id`, `name`, `slug`,
legacy source-shape `kind`, explicit `role`, `playable`, `group_id`,
`group_name`, `group_slug`, `parent_army_ids`, and `unit_count`. Roles are
derived from imported source relationships rather than Army-ID ranges:
self-parented metadata factions are `main`, metadata children are `sectorial`,
children of metadata identity `901` are `non_aligned`, and lists referenced by
ordinary source `reinforcements` links are `reinforcement`. When imported
Non-Aligned children exist, metadata identity `901` is also surfaced as a
`grouping` item with `playable: false`; it is never a selectable army. Unit
counts use source-defined units in `army_units`.

### `GET /api/units?army_id=101&search=fusilier&limit=50&offset=0`

Returns `{ "items": [...], "total": 0, "limit": 50, "offset": 0 }`, where each
item has `id`, `name`, `main_army_id`, `main_faction`, `army_ids`, and `armies`
(`id` and `name` per membership). `main_faction` is either null or an object
with `id`, `name`, and `slug`, derived from imported Army metadata. The zero
total above illustrates the response shape.

- Omit `army_id` to browse all source-defined units, deduplicated by global ID.
- Army membership comes from `army_units`, not canonical faction or declared
  faction references.
- `main_army_id` currently represents canonical whole-army/group ownership.
  Ordinary ownership uses the `xx01` derivation and exceptional mappings come
  from the pinned identity policy. Canonical source ID `1` is explicitly excluded
  from application main-army ownership and remains mercenary source provenance;
  Non-Aligned grouping uses the separate metadata identity `901`.
- `main_faction` is derived from the matching metadata-faction parent record;
  browser code consumes it directly instead of deriving a faction from Army IDs.
- Search matches accent- and punctuation-insensitive, case-folded name
  substrings, including Unicode.
- Results sort by display name after case-folding, removing diacritics, and
  ignoring punctuation and other non-alphanumeric characters; unit ID breaks
  ties for stable pagination.
- Source records that share a 10,000-ID family and ISC identity are currently
  presented as one logical unit. Reinforcement-only variants join their matching
  standard unit; mercenary source occurrences are evaluated separately before
  visible army memberships are collapsed. This is runtime deduplication, not yet
  the intended normalized logical-unit model.
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
where it occurs. The response includes the same `main_faction` object used by
unit summaries; each army occurrence also includes its derived `faction` object
or null. Profile records include a backend-derived `profile_identity` used by
the browser to group equivalent labels under the identity policy pinned into
the database. A reinforcement-only source variant is folded into a uniquely
matching standard unit. Current mercenary availability is evaluated from explicit normalized
`availability_kind` source-occurrence provenance at repository-query time. Unknown unit IDs return 404.

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
Metadata weapon/equipment profiles retain the raw `traits` value and also expose
`trait_references`. Each reference contains the raw `label`, canonical `name`
(or null), and trait-catalog `slug` (or null). Browser rendering consumes these
backend-derived references for trait links and does not canonicalize trait text
or generate trait slugs independently.

`GET /api/traits` returns the derived shared-traits catalog.
`GET /api/traits/{slug}` returns a trait's concise rules summary, when
available, and its use grouped across skills, equipment, and weapons.

Future implementation work is tracked in `docs/TODO.md`; this document records
current architecture and clearly labeled lasting design direction rather than
maintaining a second backlog.
