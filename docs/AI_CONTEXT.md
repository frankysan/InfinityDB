# InfinityDB: AI context

Use this document to orient substantial changes. It records durable non-obvious
project decisions, implementation constraints, and historical choices that help
agents work consistently without duplicating the canonical architecture or data
model.

## Documentation hierarchy

- `AGENTS.md` contains immediate repository-wide instructions for coding agents.
- `docs/architecture.md` is authoritative for architecture, engineering
  principles, subsystem boundaries, data-path roles, and lasting design
  direction.
- `docs/data-model.md` is authoritative for normalized data semantics and
  persistence structure.
- This document records non-obvious constraints and decision history that are
  useful during implementation.
- `README.md` is the user-facing project introduction, setup, and operations
  guide.
- `docs/TODO.md` is the maintained backlog.
- `docs/CHANGELOG.md` records released and unreleased changes.

Before changing a boundary or persistence behavior, read
`docs/architecture.md` and `docs/data-model.md`. Do not maintain a competing
copy of their principles here.

## Purpose and subsystem boundaries

InfinityDB builds validated local reference databases from Infinity source data
and serves a read-only browser and same-origin HTTP API.

- `infinity_army_data` interprets, merges, normalizes, and validates Army source
  data independently of the database/web application.
- `infinity_db.database` owns Army SQLite storage and repository queries.
- The separate rules-reference database is built from validated curated rules
  collections, not from raw PDFs or wiki snapshots.
- `infinity_db.web` validates HTTP input, serializes repository results, and
  contains the native-module browser UI.
- Standalone acquisition and processing tools remain explicitly invoked and
  independently testable. Normal builds and tests must not acquire network data
  unexpectedly.
- Deployment remains separate from acquisition, normalization, database
  construction, rules curation, and asset processing.

## Non-obvious Army data invariants

- Preserve the merged master document losslessly. The normalized layer is
  relational/query-oriented but retains source identities and relationships
  needed for validation and display.
- Unit IDs are global; nested profile, profile-group, and loadout IDs are only
  unique within their army/unit hierarchy. Use the established composite keys.
- Retain source-undefined references as explicit placeholders rather than
  silently discarding them.
- Valid Army API `metadata.json` is required for database creation. It enriches
  catalogs, names, and faction hierarchy but must not create army membership or
  alter source-derived availability.
- Army-list occurrences are authoritative for unit membership and availability.
  List presence, grouping, list kind, canonical ownership, and playability are
  separate semantics.
- Legacy canonical-faction source ID `1` maps to `901` through the validated
  source-identity policy for canonical ownership only.
- 901 (Non-Aligned Armies) is a grouping identity for its child 9xx armies, not
  an independently playable army. Do not infer playability from ID patterns or
  the existence of an `army_lists` record.
- SQLite Army imports replace a complete snapshot. Future user-authored data
  must remain separate from that replaceable imported state.
- Nested queryable values may remain JSON in the frontend DB; exact normalized
  rows, including absent-versus-null distinctions, are preserved in the sibling
  raw archive.
- Increment `DATABASE_COMPATIBILITY_VERSION` whenever existing generated Army
  databases must be rebuilt, even if the SQLite schema version is unchanged.

## Snapshot acquisition and provenance

The canonical path/lifecycle model is defined in `docs/architecture.md`.
Implementation work must preserve these additional constraints:

- Army, wiki, and symbol downloaders stage loose files temporarily and persist
  complete timestamped `JSON`, `WIKI`, or `SYMBOLS` ZIP snapshots. Same-second
  name collisions receive `-2`, `-3`, and so on rather than overwriting.
- Raw snapshot archives are immutable after successful acquisition.
- Downloader-generated snapshot provenance belongs under
  `data/manifests/snapshots/` and binds to an archive by SHA-256. It is not
  Corvus Belli's source `metadata.json` and is not hand-edited project policy.
- Human-authored snapshot descriptions, comparison targets, and notable-change
  notes belong under `data/curated/snapshot-notes/`, also keyed to the snapshot
  SHA-256. They are intentionally separate from generated provenance so either
  lifecycle can change without rewriting the other.
- `data/curated/snapshot-notes/` is not a rules-database input.
- Persistent generated project paths use portable project-relative forms; treat
  filenames as case-sensitive internally and detect case-only collisions before
  publishing.
- External executable discovery should use explicit configuration/shared
  discovery helpers/`shutil.which()` rather than fixed installation paths.
- Subprocess-heavy tools use argument lists, not shell command strings, and
  process-based concurrency must remain safe under the Windows `spawn` model.

## Symbol pipeline constraints

Downloaded Corvus Belli graphical assets remain outside the public repository
unless redistribution permission clearly allows inclusion. Local corrected
image overrides likewise remain ignored unless redistribution status changes.

A symbol build associated with an Army snapshot must use the same exact pinned
Army snapshot throughout discovery and publication. Pin archive identity and
SHA-256 plus source metadata needed for reproducibility; no downstream stage may
select a newer snapshot independently.

Authoritative Army-API symbol discovery comes from every
`units[].profileGroups[].profiles[].logo` reference plus
`metadata.json -> factions[].logo`. `resume[].logo` is only a
consistency/validation source. Recursively scan source strings for additional
SVG references as a schema-drift audit; unknown SVG-bearing fields must be
reported rather than silently ignored.

Symbol discovery/reference identity is URL/reference based rather than unit-ID
based. A unit may reference several source SVGs, and several units/profiles may
reference the same SVG. Exact or visual deduplication may map several source
assets to one canonical asset but must retain every original reference.

Source resolution follows the maintained policy:

```text
local override
    -> validated selected symbol snapshot/cache
    -> upstream network when explicit acquisition permits it
```

An invalid matching override is an error; it must not silently fall back to a
different source.

Only the publisher assigns final application paths and generated
`army-symbols.js` / `unit-symbol-map.js` mappings because only publication knows
the final canonical asset after deduplication/conversion/compression.

The established processing direction is `resvg` for visual duplicate and
compression validation, persistent `inkscape --shell` workers for text-to-path
conversion, and standalone reusable stages wrapped by a thin orchestrator. The
roughly 8-9 second Windows Inkscape startup cost is an accepted external-tool
limitation for now; persistent workers mitigate it. Do not restart startup
profiling without new evidence.

## Curated rules-reference constraints

Raw PDF and wiki research material is not an application input. Human-reviewed
rules collections live under `data/curated/rules/`; `infinity-db build-rules`
defaults to that subtree and must not ingest sibling curated categories such as
`snapshot-notes/`.

Current local reference families include N5 core rules revisions, N5 FAQs, ITS
season/historical material, and timestamped wiki snapshots. Keep core rules,
FAQ/errata rulings, ITS seasons, historical sources, and wiki-derived material
explicitly scoped so a view cannot silently combine incompatible versions.

PDF-derived facts retain document version/date plus printed-page citations. Wiki
facts retain snapshot-local paths and snapshot identity; current curated-v2
citations use `snapshotDate`, while source metadata should also retain the exact
selected timestamped archive identity/SHA-256 when available.

The current curated-v2 rules contract includes collection/source metadata,
maintained `skillTypes` and `labels` vocabularies with `vocabularySources`, typed
records, Army links, related-record links, review state, and citations. Version
1 curated-rule files must be migrated before ingestion. The reserved
`rules/example.json` template is excluded from directory ingestion.

The rules database has its own schema/versioning and replacement lifecycle. It
must not import Army JSON data, and Army database construction must not import
rules data. Application/service code may combine the two only through stable
application-level identities.

## API and UI constraints

- API routes are same-origin and read-only. Validate request input at the HTTP
  boundary and do not expose internal exceptions.
- Prefer additive response changes; do not silently repurpose existing fields.
- Army filtering uses actual `army_units` occurrences, not canonical faction
  references.
- Army selectors must ultimately use explicit backend-provided role/playability
  semantics rather than treating every imported list identity as selectable.
- Search/display ordering is case-, accent-, and punctuation-insensitive.
- Browser requests belong in `api.js`; shared unit rows in `unit-list.js`;
  page-specific rendering/state in the corresponding page module.
- Frontend database data is immutable for a running application instance.
  Snapshot-aware ETags and `/api/version` distinguish new imported data from an
  application release.
- Every browser route uses the shared server-rendered page shell. New static
  page documents retain the navigation/header/footer markers expected by
  `_page()`.
- Shared menus use the inline-sidebar / compact-topbar pattern.
- `styles.css` is the design-system source of truth. Reuse established tokens,
  surfaces, table density, detail-group primitives, and badges rather than
  adding page-local equivalents.
- Developer mode is default-off. Technical inline fields use `.developer-only`
  and ID table columns use `.id-column`.

## Style and change discipline

- Target Python 3.11, four-space indentation, and Ruff rules `E`, `F`, `I`,
  `UP`, `B` with 100-character lines except reviewed SQL strings.
- Prefer explicit small functions and clear transformations over clever
  abstractions. Preserve source field names unless a deliberate mapping is
  documented.
- Update focused tests with behavior changes. Standalone scripts in `tools/`
  require dedicated regression coverage for filesystem/URL/portability logic.
- Run substantive Python tests/lint through the project virtual environment,
  for example `<venv-python> -m pytest -q` and
  `<venv-python> -m ruff check src/infinity_db src/infinity_army_data/cli.py tests`.
- Update `README.md` for user-visible behavior/setup/capabilities, canonical
  architecture/data-model docs for their respective decisions, `TODO.md` for
  concrete future work, and `CHANGELOG.md` under `Unreleased` for meaningful
  changes.
- Keep `__version__` at the released value until an explicit release. While
  unreleased work exists, the browser footer uses `__display_version__` with
  the `+dev` suffix.

## Decision log

- 2026-09-12: Database builds require validated Army API metadata. The importer
  enforces this too, so metadata-free normalized data cannot bypass the build
  command and become a database.
- 2026-09-12: SQLite is a local replaceable imported snapshot, not a home for
  user-authored persistent data. User-owned migrations are deferred until that
  requirement exists.
- 2026-09-12: The browser has no frontend build tool; native modules keep local
  deployment and maintenance simple.
- 2026-09-12: The browser shell is centrally rendered from navigation, header,
  and footer fragments. CSS tokens/shared components are the extension point for
  visual consistency.
- 2026-09-13: Settings uses the shared sidebar/compact-topbar menu pattern. Unit
  catalog accents may draw from named main-army colors only through the shared
  design system.
- 2026-09-14: PDF/wiki-derived rules references use their own SQLite database,
  independently versioned from the replaceable Army JSON snapshot.
- 2026-09-16: Engineering principles are canonical in `docs/architecture.md`.
  Maintained domain knowledge belongs in validated configuration where
  appropriate; generated project paths remain deterministic and portable.
- 2026-09-16: Legacy canonical-faction ID `1` -> `901` is an ownership-policy
  mapping distinct from playability. 901 is grouping-only; explicit
  role/playability semantics remain required for selectors/APIs.
- 2026-09-16: Army-linked symbol discovery is reference/URL based, uses one
  exact pinned Army snapshot, audits unknown SVG locations, and leaves final
  canonical application paths/mappings to the publisher.
- 2026-09-16: Army JSON, wiki, and symbol acquisition use complete timestamped
  ZIP snapshots rather than long-lived unpacked download directories.
- 2026-09-16: Snapshot metadata follows the existing data-path model instead of
  introducing editable sidecars beside raw archives. Generated acquisition
  provenance lives under `data/manifests/snapshots/`; human descriptions and
  notable-change notes live under `data/curated/snapshot-notes/`; both bind to
  immutable raw snapshots by SHA-256.
- 2026-09-16: Rules ingestion is scoped to `data/curated/rules/`. Other curated
  categories are human-reviewed project data but are not implicitly rules
  database inputs.
