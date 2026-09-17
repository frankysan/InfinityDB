# InfinityDB: AI context

Use this document to orient substantial changes. It records durable non-obvious
project decisions, implementation constraints, and historical choices that help
agents work consistently without duplicating the canonical architecture or data
model.

## Documentation hierarchy and status

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
- `docs/TODO.md` is the maintained backlog of unimplemented work.
- `docs/CHANGELOG.md` records released and unreleased changes.

Before changing a boundary or persistence behavior, read
`docs/architecture.md` and `docs/data-model.md`. Do not maintain a competing
copy of their principles here.

Status must remain explicit. Unqualified descriptions in this document should
refer to current constraints/behavior. Accepted but unimplemented choices are
marked **Design direction**. The decision log may record an accepted decision
before implementation, but the current sections and `TODO.md` remain
responsible for implementation status.

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
  List presence, grouping, list kind, canonical ownership, optional availability
  category, and playability are separate semantics.
- The identity configuration no longer maps canonical-faction source ID `1` to
  `901`. Normalization preserves ID `1` as mercenary source/origin provenance
  and explicitly leaves `main_army_id` unset for canonical-1 units; 901 remains
  the distinct Non-Aligned Armies grouping identity.
- Source investigation shows ID `1` and ID `901` represent different concepts.
  ID `1` behaves as a mercenary source/origin identity with no army list and no
  ordinary faction membership role; 901 is the Non-Aligned Armies grouping
  identity for distinct child army lists. They must not be conflated.
- Ordinary unit records declare normal faction availability in `factions`.
  Dedicated optional-mercenary source variants consistently use
  `canonical: 1`, an empty `factions` list, a `merc-...` slug, and army-specific
  occurrences that add optional availability. Many use a 10,000-offset-style
  source ID, but numeric offset is diagnostic evidence only, not the semantic
  rule.
- Current normalized snapshots persist generic standard duplicate-unit matches,
  mercenary-to-standard source-unit matches, and explicit
  `army_units.availability_kind`. Repository logical grouping consumes the
  persisted generic and mercenary mappings, while mercenary filtering uses
  explicit availability provenance. The 10,000-ID generic grouping rule remains
  only as a compatibility fallback for older databases without
  `genericUnitMatches`.
- 901 (Non-Aligned Armies) is a grouping identity for its child 9xx armies, not
  an independently playable army. Do not infer playability from ID patterns or
  the existence of an `army_lists` record.
- The merger's current `army_lists.kind` is derived from source shape: ordinary
  documents containing `reinforcements` become `army`, while reinforcement
  documents without it become `reinforcement`. It is not a source-provided
  main-army/sectorial taxonomy.
- Army metadata parent relationships carry useful grouping semantics: standard
  main armies are self-parented, sectorials point to their main army, and NA2
  forces point to grouping identity 901. Ordinary list documents explicitly
  reference their reinforcement list through `reinforcements`.
- Current InfinityDB normalization also uses that metadata parent relationship
  to derive unit `main_army_id`. Explicit maintained canonical-faction overrides
  take precedence; the old `xx01` calculation is retained only for standalone or
  legacy normalization inputs without a usable metadata row for that canonical
  faction.
- The backend/API exposes explicit army role/playability semantics derived from
  metadata parent relationships and ordinary-list `reinforcements` links.
  `/api/armies` distinguishes main armies, sectorials, Non-Aligned forces,
  reinforcement lists, and grouping-only identities; the browser selector
  consumes that contract rather than Army-ID ranges. Grouping identity `901` is
  non-playable.
- Mercenary variants are classified during normalization, their source markers
  are validated, audited mercenary-to-standard mappings are persisted, and
  repository queries consume explicit availability provenance. Generic standard
  duplicate matching is also audited and persisted during normalization.
  Database creation additionally persists unambiguous reinforcement-to-standard
  matches using the pinned name-normalization policy. Current repositories do not
  rediscover generic or reinforcement identity at query time when those metadata
  contracts are present. Frontend database creation resolves configured aliases
  plus persisted generic, mercenary, and reinforcement evidence into explicit
  `logical_units` / `logical_unit_sources` relations. Source rows remain
  unchanged; every source unit maps to exactly one logical unit, and repository
  reads consume that materialized mapping rather than rebuilding identity
  dynamically. Legacy rediscovery remains only as a database-build compatibility
  path for older normalized inputs.
- SQLite Army imports replace a complete snapshot. Future user-authored data
  must remain separate from that replaceable imported state.
- Nested queryable values may remain JSON in the frontend DB; exact normalized
  rows, including absent-versus-null distinctions, are preserved in the sibling
  raw archive.
- Increment `DATABASE_COMPATIBILITY_VERSION` whenever existing generated Army
  databases must be rebuilt, even if the SQLite schema version is unchanged.

## Snapshot acquisition and provenance

### Current

- Army, wiki, and symbol downloaders stage loose files temporarily and persist
  complete timestamped `JSON`, `WIKI`, or `SYMBOLS` ZIP snapshots. Same-second
  name collisions receive `-2`, `-3`, and so on rather than overwriting.
- Raw snapshot archives are immutable after successful acquisition.
- Current downloaders do not write InfinityDB-owned snapshot provenance under
  `data/manifests/`, and there is no populated/consumed curated snapshot-note
  contract yet.
- Corvus Belli's Army `metadata.json` remains source data, not project-generated
  snapshot metadata.

### Design direction

- Downloader-generated snapshot provenance will live under
  `data/manifests/snapshots/` and bind to an archive by SHA-256.
- Human-authored snapshot descriptions, comparison targets, and notable-change
  notes will live separately under `data/curated/snapshot-notes/`, also keyed to
  the snapshot SHA-256.
- Generated tooling must never overwrite curated snapshot notes; editing notes
  must never mutate the raw archive or generated provenance.
- Persistence/version-control/package policy for generated manifests is not yet
  implemented and should be finalized together with the first manifest writer.
- Persistent generated project paths should use portable project-relative forms;
  treat filenames as case-sensitive internally and detect case-only collisions
  before publishing.

Current curated wiki provenance predates the timestamped ZIP lifecycle. Do not
invent exact archive/hash associations for legacy wiki references. Migrate them
when the wiki downloader/packager and curated provenance contract are rewritten
together.

External executable discovery should use explicit configuration/shared discovery
helpers/`shutil.which()` rather than fixed installation paths. Subprocess-heavy
tools use argument lists, not shell command strings, and process-based
concurrency must remain safe under the Windows `spawn` model.

## Symbol pipeline

### Current

Downloaded Corvus Belli graphical assets remain outside the public repository
unless redistribution permission clearly allows inclusion. Local corrected
image overrides likewise remain ignored unless redistribution status changes.

Current acquisition can create timestamped symbol archives, and the repository
contains standalone processing/reorganization tooling plus bundled browser
assets. The complete manifest-backed build described below is not yet the
current integrated workflow.

### Design direction

A symbol build associated with an Army snapshot will use the same exact pinned
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

Source resolution follows the accepted policy:

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
limitation; persistent workers are the intended mitigation. Do not restart
startup profiling without new evidence.

## Curated rules-reference constraints

### Current

Raw PDF and wiki research material is not an application input. Human-reviewed
rules collections live under `data/curated/rules/`; `infinity-db build-rules`
defaults to that subtree and does not ingest sibling curated categories.

Current local reference families include N5 core rules revisions, N5 FAQs, ITS
season/historical material, and wiki research. Keep core rules, FAQ/errata
rulings, ITS seasons, historical sources, and wiki-derived material explicitly
scoped so a view cannot silently combine incompatible versions.

PDF record citations retain document version/date plus printed-page citations.
Wiki record citations currently retain snapshot-local paths and `snapshotDate`.
The checked-in wiki source still references the legacy unpacked mirror identity;
that is current provenance, not a timestamped-archive guarantee.

The current curated-v2 rules contract includes collection/source metadata,
maintained `skillTypes` and `labels` vocabularies with `vocabularySources`, typed
records, Army links, related-record links, review state, and citations. The
current `vocabularySources` validator requires the mixed legacy locator fields
`sourceId`, `path`, `snapshotDate`, `heading`, and positive `page`. Version 1
curated-rule files must be migrated before ingestion. The reserved
`rules/example.json` template is excluded from directory ingestion.

The rules database has its own schema/versioning and replacement lifecycle. It
must not import Army JSON data, and Army database construction must not import
rules data. Application/service code may combine the two only through stable
application-level identities.

### Design direction

When the wiki downloader/packager is rewritten, migrate legacy wiki source
identity to exact recorded timestamped archive/hash provenance and replace the
mixed `vocabularySources` locator with source-appropriate provenance. This is
tracked as future work and should not be papered over by documentation-only
changes.

## API and UI constraints

- API routes are same-origin and read-only. Validate request input at the HTTP
  boundary and do not expose internal exceptions.
- Prefer additive response changes; do not silently repurpose existing fields.
- Army filtering uses actual `army_units` occurrences, not canonical faction
  references.
- **Design direction:** Army selectors should use explicit backend-provided
  role/playability semantics rather than treating every imported list identity
  as selectable.
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
- 2026-09-16: The `1` -> `901` canonical-faction ownership override was moved
  into validated identity configuration. Subsequent source investigation on
  2026-09-17 found that the two IDs represent different domain concepts.
- 2026-09-17: After mercenary logical pairing and availability provenance moved
  to explicit normalized metadata, the legacy `1` -> `901` override was removed.
  Canonical source ID `1` now remains mercenary provenance with no application
  `main_army_id`; 901 remains the distinct NA2 grouping identity. Army database
  compatibility revision 12 requires rebuilding existing generated snapshots.
- 2026-09-16: Army-linked symbol discovery is reference/URL based, uses one
  exact pinned Army snapshot, audits unknown SVG locations, and leaves final
  canonical application paths/mappings to the publisher. This records design
  direction; the integrated manifest-backed pipeline is not yet implemented.
- 2026-09-16: Army JSON, wiki, and symbol acquisition use complete timestamped
  ZIP snapshots rather than long-lived unpacked download directories.
- 2026-09-16: Snapshot metadata follows the existing data-path model instead of
  introducing editable sidecars beside raw archives. The accepted design puts
  generated acquisition provenance under `data/manifests/snapshots/` and human
  notes under `data/curated/snapshot-notes/`; the writers/contracts are not yet
  implemented.
- 2026-09-16: Rules ingestion is scoped to `data/curated/rules/`. Other curated
  categories may have separate future semantics but are not implicitly rules
  database inputs.
- 2026-09-16: Documentation distinguishes current implementation, accepted
  design direction, and planned/unimplemented backlog so future architecture is
  not presented as existing behavior.
- 2026-09-17: Generic standard-unit duplicate matching moved from repository-time
  10,000-ID arithmetic into a normalization audit persisted as
  `genericUnitMatches`. Current repositories treat the persisted audit as
  authoritative, including an empty result; older databases without the key
  retain the arithmetic fallback. No SQLite schema or compatibility revision
  change was required because the metadata contract is backward-compatible.
- 2026-09-17: Unit `main_army_id` derivation moved from the ordinary `xx01`
  Army-ID convention to imported metadata faction parents for current
  InfinityDB builds. Explicit maintained overrides still win; `xx01` remains
  only as a legacy/standalone fallback when metadata cannot resolve the
  canonical faction. Database compatibility revision 13 requires rebuilding
  existing generated Army databases.
- 2026-09-17: Army role/playability moved to an explicit source-derived
  backend/API contract. Metadata parents classify main, sectorial, and
  Non-Aligned forces; explicit ordinary-list `reinforcements` links classify
  reinforcement relationships. Grouping identity 901 is exposed as
  non-playable and browser selectors no longer infer roles from Army-ID ranges.
- 2026-09-17: Mercenary source identity and Non-Aligned Army grouping are
  separate. ID `1` is retained as mercenary source provenance; 901 groups NA2
  army lists. Dedicated mercenary variants are identified by source semantics,
  not numeric ID arithmetic. Classification, persisted mercenary-to-standard
  matching, and explicit availability provenance are now normalized before
  repository use.
- 2026-09-17: Logical-unit identity is materialized during frontend database
  creation. Configured aliases and persisted generic, mercenary, and
  reinforcement matches are build-time identity evidence; the exporter resolves
  their transitive components into `logical_units` and `logical_unit_sources`.
  Source/profile/loadout/occurrence rows remain keyed to original source units
  for provenance, and repository reads consume the materialized relation. Legacy
  identity discovery is retained only behind the builder for older normalized
  inputs.
