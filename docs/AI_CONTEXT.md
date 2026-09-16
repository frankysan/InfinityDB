# InfinityDB: AI context

Use this document to orient substantial changes. It records durable project
decisions, invariants, and non-obvious development constraints.

## Documentation hierarchy

- `AGENTS.md` contains immediate repository-wide instructions for coding agents.
- `docs/architecture.md` is authoritative for architecture, engineering
  principles, subsystem boundaries, and lasting design direction.
- `docs/data-model.md` is authoritative for normalized data semantics and
  persistence structure.
- This document records durable project context, compatibility invariants, and
  implementation constraints that help agents make changes consistently.
- `README.md` remains the user-facing project introduction, setup, and
  operations guide.
- `docs/TODO.md` is the maintained backlog.
- `docs/CHANGELOG.md` records released and unreleased changes.

Before changing a boundary or persistence behavior, read
`docs/architecture.md` and `docs/data-model.md`.

Follow the guiding and engineering principles defined in
`docs/architecture.md`; do not maintain a separate competing copy here.

## Purpose and boundaries

InfinityDB builds a local, validated SQLite reference database from Corvus
Belli Infinity Army snapshots and serves a read-only browser and same-origin
HTTP API.

- `infinity_army_data` interprets, merges, normalizes, and validates source
  data. It remains useful independently of the database and web application.
- `infinity_db.database` defines and imports the SQLite snapshot, then exposes
  read-only repository queries.
- `infinity_db.web` validates HTTP input, serializes repository results, and
  contains the native-module browser UI.
- Raw Army files are parsed only by the data pipeline. Routes and browser code
  must use the repository and HTTP API respectively.
- Standalone acquisition and processing tools remain independently usable and
  testable rather than becoming hidden side effects of normal application
  builds.
- Deployment is a separate concern from acquisition, normalization, database
  construction, and asset processing.

Keep source-format logic, database storage choices, HTTP behavior, browser
state, asset processing, and deployment behavior in their respective layers.
Do not add a JavaScript build step unless a clear requirement justifies it.

## Configuration and manifests

InfinityDB distinguishes behavior from maintained project knowledge:

```text
code        = behavior
config      = maintained project/domain knowledge
raw data    = immutable external input
generated   = reproducible build output
```

Aliases, mappings, filters, manual overrides, compatibility exceptions, static
asset declarations, and similar domain knowledge should use validated,
versioned configuration when they can change independently of implementation
behavior.

Do not move ordinary implementation constants into configuration merely for
configurability. Use manifests when the content represents maintained domain
knowledge, policy, mappings, source declarations, or independently reviewable
exceptions.

Important configuration contracts should have an explicit schema or schema
version, validation on load, deterministic serialization when generated, and
tests for invalid and edge-case inputs.

Persistent manifests should store portable project-relative paths rather than
machine-specific absolute paths.

## Data and compatibility invariants

- Preserve the merged master document losslessly. The normalized document is
  relational and query-oriented, but should retain source identity and
  relationships needed for validation and display.
- Unit IDs are global; nested profile, profile-group, and loadout IDs are only
  unique within their army/unit hierarchy. Use the established composite keys.
- Retain source-undefined references as explicit placeholders; do not silently
  discard them.
- Database creation requires valid `metadata.json`, discovered beside or inside
  the source or passed with `--metadata`. It enriches display names and
  reference catalogs, but must not create list membership or alter availability.
- Army-list data is authoritative for unit membership and source-derived
  availability, but the existence of an army-list identity does not necessarily
  make it independently playable. Grouping, list kind, and playability are
  separate domain semantics.
- The legacy canonical-faction source ID `1` -> `901` mapping is maintained in
  the validated source-identity manifest and establishes canonical ownership
  only. It does not imply that 901 is independently playable.
- 901 (Non-Aligned Armies) is a grouping identity for its child 9xx armies, not
  a playable army. Playability must not be inferred from numeric ID ranges or
  from the mere presence of an `army_lists` record.
- SQLite imports are complete snapshot replacements. Build and validate temporary
  sibling frontend and raw-archive databases before replacing the working files,
  so a failed build leaves the prior snapshot usable.
- PDF-derived rules material belongs in a separate SQLite database from the
  Army JSON-derived frontend and raw-archive databases. Its import and release
  lifecycle must be independent; combine Army and rules results only in an
  application/service layer, never by treating either source as input to the
  other's pipeline.
- Nested data remains JSON in the queryable frontend database. Each row's exact
  normalized representation, including absent versus null fields, belongs in
  the sibling raw archive; do not remove that fidelity merely to simplify a
  query.
- Increment `DATABASE_COMPATIBILITY_VERSION` whenever a code change requires a
  rebuilt database, even when the SQLite schema is unchanged. Incompatible
  databases must fail with a rebuild instruction rather than serving stale
  results.

## Filesystem, portability, and build invariants

- Target Windows, Linux, and macOS for Python tooling unless a component is
  explicitly documented as platform-specific.
- Use portable filesystem APIs and avoid hard-coded user or system paths.
- Treat raw downloaded inputs as immutable. Transformations write to separate
  working/generated locations.
- Persistent generated state should be validated before replacement and written
  atomically where practical so failed builds leave the prior valid state
  usable.
- Generated project paths and names must be deterministic across supported host
  operating systems.
- Treat filenames as case-sensitive internally and detect case-only collisions
  before publishing.
- External executables should be discovered through explicit configuration,
  shared discovery helpers, or `shutil.which()` rather than fixed installation
  paths.
- Subprocess-heavy tooling should use argument lists rather than shell command
  strings. Do not make core pipeline behavior depend on CMD, PowerShell, Bash,
  or shell-specific quoting.
- Any process-based concurrency must be safe under the Windows `spawn` model.
- Normal builds and tests must not make unexpected network requests. Network
  acquisition belongs in explicit downloader/refresh operations.

## Third-party assets and symbol processing

Downloaded Army data, graphical assets, rules documents, wiki material, and
other third-party content are not automatically covered by InfinityDB's MIT
License. Review `THIRD_PARTY_NOTICES.md` before redistribution.

Corvus Belli graphical assets should remain outside the public repository unless
redistribution permission clearly allows their inclusion.

Local image overrides may contain corrected or technically modified derivatives
of Corvus Belli assets and therefore remain local/ignored unless their
redistribution status changes. Configuration may document an expected override
and its purpose without embedding the asset itself.

The symbol pipeline should preserve provenance and distinguish upstream asset
identity, local source resolution, canonical/deduplicated identity, and final
published paths. Override resolution follows the project policy:

```text
local override
    -> validated raw cache
    -> upstream download
```

An invalid override must fail explicitly rather than silently falling back to a
different source.

A symbol build associated with an Army snapshot must use that one exact pinned
snapshot throughout discovery and publication. Pin the archive identity,
SHA-256, language, acquisition timestamp, and API base URL; no downstream stage
may independently select a newer snapshot.

Authoritative Army-API symbol discovery comes from every
`units[].profileGroups[].profiles[].logo` reference plus
`metadata.json -> factions[].logo`. `resume[].logo` is a consistency/validation
source, not the complete discovery source. Recursively scanning all source
strings for additional SVG references is an audit for source-schema drift; an
unknown SVG-bearing field must be reported rather than silently ignored.

Symbol identity is reference/URL based rather than unit-ID based. A unit may
reference several source SVGs, several units or profiles may reference one SVG,
and visual duplicate detection may collapse several source assets to one
canonical asset. Deduplication must never discard the original references. The
publisher, not the downloader, owns final application paths and generated
`army-symbols.js` / `unit-symbol-map.js` mappings because only the publisher
knows the final canonical asset after processing.

The established production processing direction is `resvg` for visual duplicate
and compression validation, persistent `inkscape --shell` workers for text-to-
path conversion, and standalone stage tools wrapped by a thin orchestrator.
The slow Windows startup cost of Inkscape is treated as an external-tool
limitation; persistent workers are the mitigation unless new evidence warrants
reopening that investigation.

## Local rules-reference documents

The ignored, user-supplied PDFs in `data/` are potential sources for
rules-aware product work and data review; they are not inputs to the Army JSON
merge/normalization/build pipeline:

- `data/pdf/rules/n5-rules-v5-1-en.pdf`, `n5-rules-v5-2-en.pdf`, and
  `n5-rules-v5-3-en.pdf`: N5 core rules revisions.
- `data/pdf/faq/n5-faqs-v0-0-en.pdf` and `n5-faqs-v0-1-en.pdf`: dated FAQ
  clarifications.
- `data/pdf/its/Its-rules-season-18-en.pdf`: current ITS Season 18 rules.
- `data/pdf/legacy/`: historical ITS Seasons 6-17 and N2/N3 rules.
- `data/wiki/20260915/`: a local wiki snapshot with HTML pages, originals,
  and assets.

When using these documents, record the document version/date and printed-page
citation. Keep core rules, FAQ/errata rulings, and ITS season content separate
so a view cannot silently combine editions or seasons. The official Infinity
Army app/data remains authoritative for unit availability and list legality;
live official rules, FAQs, wiki, errata, and event dates may supersede a local
copy. Use concise original summaries and structured facts, not bulk-extracted
or served copyrighted PDF text or artwork. Curate core rules, FAQ/errata, and
ITS records into separate versioned collections; historical sources must not be
silently blended with current rules.

The handoff from research to project data is `data/curated/`. Curated JSON
files use the `InfinityDB curated reference` format and must preserve source
identity plus printed-page provenance for every record. Application ingestion
must use `infinity_db.curated.load_curated_document` (or a validated importer
built on it), never open files under `data/pdf/` or `data/wiki/`.
Army links in curated records may point to existing catalog or unit IDs, but
must not change Army-derived availability, legality, or statistics. The
current v2 citation model supports printed PDF pages and wiki paths with
snapshot dates. Version 1 curated files must be migrated before ingestion.

## API and UI rules

- API routes are same-origin and read-only. Validate request input at the HTTP
  boundary; return useful client errors without exposing internal exceptions.
- Keep response shapes stable. Additive fields are preferable to changing or
  repurposing existing fields.
- Army filtering derives from actual `army_units` occurrences, not canonical
  faction references. Source records may be combined into one logical unit only
  using the repository's established identity rules.
- Army selectors must ultimately use explicit backend-provided playability/role
  semantics rather than treating every imported army-list identity as playable.
- Search and display ordering are case-, accent-, and punctuation-insensitive;
  preserve this behavior for new searchable names.
- Browser requests belong in `api.js`; shared unit rows belong in
  `unit-list.js`; page-specific state and rendering belong in their page module.
- Treat frontend database data as immutable for a running application instance.
  Snapshot-aware ETags and the version endpoint distinguish a new dataset from
  a new application release; keep these validators aligned when adding routes.
  Use native browser modules and stable asset paths rather than directory scans.
- Every browser route uses the server-rendered shared page shell. Add new pages
  through `_page()` with breadcrumb and catalog-tag values, and retain the
  navigation/header/footer markers in their static document.
- Shared menus use the sidebar-section / compact-topbar pattern: render their
  labeled options inline beneath sidebar navigation on wide screens, then use
  the shared compact-menu dropdown behavior beside Navigation in the top bar.
  New sidebar or topbar menus should follow this pattern by default.
- Treat `styles.css` as the design-system source of truth. Reuse its root
  tokens and existing layout/control components; do not add page-local colors,
  spacing scales, radii, or shell variants when a shared token or component can
  express the need. Detail renderers must compose the shared `.detail-group`,
  `.detail-section-title`, `.data-surface-header`, `.data-label`, and `.badge`
  primitives before adding a semantic modifier.
- Use the shared default, subdued, and highlighted `.surface` variants for
  cards and panels. Tables use the comfortable default or
  `.data-table--compact` for detail and usage data; do not introduce local
  table padding or density rules.
- Developer mode is a persistent, default-off browser preference for technical
  details. Mark inline database identifiers with `.developer-only` and ID table
  columns with `.id-column`; both must stay hidden unless Developer mode is on.

## Style and change discipline

- Target Python 3.11, use four-space indentation, and keep Ruff-compatible code
  (`E`, `F`, `I`, `UP`, `B`; 100-character lines except reviewed SQL strings).
- Prefer explicit, small functions and clear data transformations over clever
  abstractions. Preserve existing source field names in normalized/database
  records unless a deliberate mapping is documented.
- Update tests with behavior changes. Pipeline changes need lossless,
  relationship, and import-integrity coverage; repository/API/UI changes need
  focused behavior coverage. Standalone scripts in `tools/` also need their own
  dedicated regression tests so filesystem safety, portability, and download
  logic remain covered independently of the main pipeline.
- Run substantive test and lint commands through the project's virtual
  environment, for example:
  `<venv-python> -m pytest -q` and
  `<venv-python> -m ruff check src/infinity_db src/infinity_army_data/cli.py tests`.
- Update `README.md` for user-visible behavior and the relevant canonical
  documentation when changing a documented boundary, invariant, or storage
  decision.
- Update `docs/TODO.md` whenever the user or an agent identifies a concrete
  future improvement, optimization, cleanup, or feature. Keep it actionable,
  place it in the appropriate section, and mark work complete only after
  implementation, verification, and documentation are finished.
- Record meaningful work under `Unreleased` in `docs/CHANGELOG.md`. Do not
  increment or otherwise alter the release version unless explicitly requested.
- Keep `__version__` at the released value. While `Unreleased` contains work,
  the browser footer must use `__display_version__` with a `+dev` suffix; reset
  it to the release version only as part of an explicitly requested release.

## Decision log

- 2026-09-12: Database builds require validated Army API metadata. The importer
  enforces this too, so a metadata-free normalized document cannot bypass the
  build command and become a database.
- 2026-09-12: SQLite is a local, replaceable imported snapshot, not a home for
  user-authored persistent data. Migrations for user-owned data are deferred
  until that requirement exists.
- 2026-09-12: The browser has no frontend build tool; native modules keep local
  deployment and maintenance simple.
- 2026-09-12: The browser shell is centrally rendered from navigation, header,
  and footer fragments. CSS tokens and shared components are the required
  extension point for consistent visual design across current and future pages.
- 2026-09-13: Settings follows the shared menu pattern across sidebar and
  compact top-bar layouts. Unit catalog accents may draw from named main-army
  colors only through the shared design-system tokens and gradients.
- 2026-09-14: PDF-derived rules references will use their own SQLite database,
  independently versioned and updated from the replaceable Army JSON snapshot.
  This preserves source provenance and prevents a rules-document update from
  requiring an Army import (or vice versa).
- 2026-09-16: Engineering principles are canonical in
  `docs/architecture.md`. Durable project knowledge that can change
  independently of implementation behavior should use validated manifests or
  configuration where appropriate. Tooling and generated project paths should
  remain deterministic and portable across Windows, Linux, and macOS.
- 2026-09-16: Legacy canonical-faction ID `1` -> `901` is an identity-policy
  mapping for Non-Aligned Armies ownership and is distinct from army
  playability. 901 is a grouping identity for its child 9xx armies, not an
  independently playable army; explicit role/playability semantics are still
  required for selectors and APIs.
- 2026-09-16: Army-linked symbol processing uses one exact pinned Army snapshot.
  Source discovery is reference/URL based rather than unit-ID based; profile
  logos and metadata faction logos are authoritative, recursive SVG scanning is
  a schema-drift audit, and only the publisher assigns final canonical asset
  paths and generated application mappings.