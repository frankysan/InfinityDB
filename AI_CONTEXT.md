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
- Nested data remains JSON in the queryable frontend database. Each row's exact
  normalized representation, including absent versus null fields, belongs in
  the sibling raw archive; do not remove that fidelity merely to simplify a
  query.
- Increment `DATABASE_COMPATIBILITY_VERSION` whenever a code change requires a
  rebuilt database, even when the SQLite schema is unchanged. Incompatible
  databases must fail with a rebuild instruction rather than serving stale
  results.

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
  focused behavior coverage.
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
