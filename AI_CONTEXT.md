# InfinityDB: AI context

Use this document to orient changes. It records durable project decisions and
constraints; the README is the user-facing setup and operations guide. For
deeper detail, read `docs/architecture.md` and `docs/data-model.md` before
changing a boundary or persistence behavior.

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

Keep source-format logic, database storage choices, HTTP behavior, and browser
state in their respective layers. Do not add a JavaScript build step unless a
clear requirement justifies it.

## Guiding principles

- **Accuracy:** Use official data sources and strive to represent them as
  accurately as possible. Preserve uncertainty when a source is incomplete or
  ambiguous rather than presenting an unsupported conclusion as fact.
- **Flexibility:** Expand the ways users can browse and understand the data
  while keeping the experience simple, fast, and customizable.
- **Transparency:** Keep the project open source under the MIT License and
  distinguish InfinityDB's work from outside data, quoted text, and image
  assets, which remain the property of their respective owners.

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
- Army-list data is authoritative for selectable army lists and unit membership.
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
  dedicated regression tests so filesystem-safety and download logic remain
  covered independently of the main pipeline.
- Run `python -m pytest -q` and
  `python -m ruff check src/infinity_db src/infinity_army_data/cli.py tests`
  for substantive changes.
- Update the README for user-visible behavior, and architecture/data-model docs
  when changing a documented boundary, invariant, or storage decision. Add a
  dated note below when a non-obvious, lasting tradeoff is introduced.
- Update `TODO.md` whenever the user or any agent identifies a potential
  improvement, optimization, or new feature. Keep it actionable, place it in
  the appropriate section, and mark work complete only after implementation,
  verification, and documentation are finished.
- Record new work under `Unreleased` in `CHANGELOG.md`. Do not increment or
  otherwise alter the release version unless explicitly requested.
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
