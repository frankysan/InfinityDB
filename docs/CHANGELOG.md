# Changelog

All notable changes to this project are documented in this file.

## Unreleased

### Added

- Add `tools/run_checks.py` as the standard development-check orchestrator for
  pytest, Ruff, and Army build validation, with selectable stages/profiles,
  targeted pytest/Ruff paths, fail-fast mode, deterministic exit codes, and
  live console output that can be mirrored to a report file.
- Add deterministic timestamped check reports under ignored `reports/` when
  `--report` is used without an explicit path; the filename and report header
  share the same local run-start timestamp, while an explicitly supplied path
  remains authoritative.
- Add normalization-time source semantics for optional mercenaries:
  source-defined units expose `source_role` (`standard` or
  `mercenary_variant`) and army occurrences expose `availability_kind`
  (`standard` or `mercenary`). The classifier validates the observed
  canonical/factions/slug contract and does not use the common 10,000-ID offset
  as its semantic rule.
- Add dedicated regression tests for each standalone tool script in `tools/`,
  covering the Army JSON downloader, wiki mirror downloader, asset symbol
  downloader, symbol reorganizer, and shared file-path sanitizer.
- Add project-local pytest temp/cache configuration so the suite runs reliably
  from the repository `.venv` on Windows and does not depend on the system temp
  directory.
- Add the validated `config/identity/source-identities.json` configuration for
  maintained unit, army, skill, equipment, weapon, and name-normalization
  identity exceptions.
- Pin the exact identity configuration and its deterministic SHA-256 into
  `normalized.json` during InfinityDB normalization and propagate the same
  validated policy into both generated Army database siblings.

### Changed

- Make repository mercenary filtering consume explicit
  `army_units.availability_kind` provenance. Current normalized snapshots no
  longer use canonical faction `1` plus faction membership to decide whether an
  army occurrence requires the `mercs` filter; that inference remains only as a
  fallback for legacy rows without availability provenance.
- Make repository logical-unit grouping consume persisted
  `mercenaryUnitMatches` / `unmatchedMercenaryUnitIds` metadata when present,
  so mercenary pairing no longer depends on the variant's 10,000-ID duplicate
  key. Explicitly unmatched variants stay separate, while older databases
  without this metadata retain the legacy grouping fallback.
- Make `units.source_role` and `army_units.availability_kind` explicit frontend
  SQLite schema fields instead of incidental dynamic columns. The Army database
  schema is now version 9 and the compatibility revision is 11; existing
  generated Army databases must be rebuilt.
- Document `tools/run_checks.py` as the standard local/agent check entry point,
  with its detailed stage, target, reporting, and exit-code contract in
  `docs/testing.md`.
- Standardize tool-script validation around one regression file per script so
  failures are easier to trace and maintain.
- Standardize Army, wiki, and symbol acquisition on one timestamped ZIP snapshot
  convention. Wiki and symbol downloads now stage loose files temporarily and
  persist complete `WIKI YYYYMMDD-HHMMSS.zip` and
  `SYMBOLS YYYYMMDD-HHMMSS.zip` archives instead of long-lived loose download
  trees; Army acquisition continues to emit `JSON YYYYMMDD-HHMMSS.zip`.
- Document the accepted snapshot-metadata design as generated provenance under
  `data/manifests/snapshots/` plus separate human annotations under
  `data/curated/snapshot-notes/`, replacing the earlier adjacent-sidecar design.
  These paths/contracts remain unimplemented until the corresponding writers are
  added.
- Scope rules-database ingestion to `data/curated/rules/`; `infinity-db
  build-rules` now defaults to that subtree so other curated data categories are
  not implicitly treated as rules collections.
- Clarify documentation status throughout the corpus so current behavior,
  accepted design direction, and planned/unimplemented work are not presented as
  equivalent. Legacy wiki provenance remains documented as legacy until the
  downloader/packager and curated provenance contract are migrated together.
- Document the source-data finding that canonical-faction ID `1` represents a
  mercenary source/origin concept distinct from Non-Aligned Armies grouping ID
  `901`. The existing `1` -> `901` ownership override remains current behavior
  for now, but is explicitly a migration target rather than a domain invariant.
- Document the accepted direction to classify optional mercenary source variants
  during normalization, validate their source-semantic markers, and move
  unambiguous logical-unit deduplication into normalization/database creation
  while preserving every source ID, occurrence, and availability provenance.
- Document the decision to keep PDF/wiki-derived rules references in a
  separately versioned SQLite database from Army JSON-derived data.
- Harden the file-path sanitization and wiki mirror logic for cross-platform
  safety while preserving compatible local URLs and asset-file naming.
- Document the MIT licensing boundary for original project material, external
  data and assets, and deployment dependencies in a third-party notices file
  and related user documentation.
- Move explicit logical-unit, army-list, catalog, and exceptional canonical-
  faction identity knowledge out of implementation code and into validated
  source-identity configuration. Generic duplicate, name-normalization, and
  whole-army `xx01` derivation algorithms remain implementation behavior.
- Make database export revalidate identity provenance pinned into normalized
  data, reject incomplete or conflicting policies, and preserve that exact
  policy in the immutable database snapshot used by runtime queries.
- Derive unit profile grouping identities in the backend from the identity
  policy pinned into the database and expose them through unit-detail API
  records, so browser code no longer maintains duplicate profile alias and
  ignored-word tables.
- Derive reinforcement classification from imported army-list `kind` metadata
  and faction grouping, names, and slugs from Army metadata parent relationships,
  exposing the derived faction metadata through unit API records so browser code
  no longer interprets Army ID suffixes or maintains faction lookup tables.
- Expose backend-derived trait references alongside raw metadata trait labels,
  including canonical trait names and catalog slugs, so catalog-detail browser
  code no longer duplicates trait aliases, misspellings, or slug generation.
- Document the distinction between canonical ownership and army playability:
  legacy canonical-faction ID `1` maps to Non-Aligned Armies `901` through the
  identity configuration in the current implementation, while 901 itself is a
  grouping identity whose explicit non-playable role still needs backend/API
  modeling. Later source investigation supersedes the assumption that IDs `1`
  and `901` are semantically equivalent.
- Consolidate the standalone Army/symbol pipeline plan into the maintained
  backlog and durable AI context, preserving its pinned-snapshot, complete SVG
  discovery, reference/asset identity, override/cache/network resolution,
  processing, publishing, cross-platform, failure-policy, and testing decisions.

## [0.5.1] - 2026-09-14

### Added

- Add advanced unit-catalog filters for skills, equipment, and weapons.
- Add a Traits catalog and detail pages covering traits used by weapon, skill,
  and equipment profiles, with concise rules summaries and usage grouped by
  catalog type.
- Add server deployment, install-or-update, and application-image pruning
  scripts, with documented image-retention behavior.
- Add a Developer-mode control for bypassing cached API responses while
  reviewing a local deployment.

### Changed

- Document the release deployment workflow and update release references to
  version 0.5.1.
- Refresh immutable static-asset URLs so linked modules load their matching
  release versions after deployment.

### Fixed

- Remove incompatible browser theme metadata from static pages.

## [0.4.2] - 2026-09-14

### Fixed

- Evaluate each source occurrence before merging a unit's army availability,
  preventing mercenary and reinforcement armies from appearing when their
  optional toggles are disabled.
- Render every army that is visible under the selected optional-unit toggles,
  including reinforcement armies alongside normal armies.
- Bypass browser-cached API responses for optional-unit filtering, and advance
  the static-asset fingerprint so an updated deployment immediately shows the
  corrected availability symbols.

## [0.4.1] - 2026-09-13

### Changed

- Direct About-page support questions, suggestions, and feedback to the
  project's GitHub page instead of publishing an email address.

## [0.4.0] - 2026-09-13

### Added

- Export a sibling `infinity.raw.db` development archive that preserves every
  exact normalized row while keeping the deployed `infinity.db` lean and
  queryable.
- Add targeted read-path indexes, bounded batch insertion, and query-plan
  regression coverage for high-volume unit and catalog-detail queries.
- Add snapshot-aware ETags for successful API responses, expose the snapshot
  revision through `/api/version`, and refresh browser pages when either the
  release or imported data changes.
- Add shared page-navigation loading events so the sidebar retains its active
  state while page data is loading.
- Add `TODO.md` as the maintained backlog for performance, pipeline,
  operational, and potential product work.

### Changed

- Cache snapshot-wide unit relationships and visible logical-unit mappings for
  unit, skill, and catalog queries, avoiding repeated membership, faction,
  search-term, and catalog-pagination assembly per request.
- Join catalog extras inside each profile, option, and unit-option source branch
  so SQLite uses occurrence primary keys instead of materializing extras unions.
- Persist SQLite planner statistics when exporting the immutable frontend snapshot.
- Build indexes after bulk loading and write both generated database files only
  after their integrity checks pass.
- Update project documentation for the split database artifacts, snapshot-aware
  caching, current database compatibility revision, and release 0.4.0.
- Refocus the About page on InfinityDB's data-driven use of official Infinity
  Army snapshots and API metadata, and describe the planned player-facing rules,
  Fireteam, model-image, and personal-collection features.

### Fixed

- Align formatting and linting across the data pipeline, database, web, and
  test code.

## [0.3.3] - 2026-09-13

### Fixed

- Version every JavaScript module dependency with its release URL. This prevents
  browsers with cached 0.3.2 modules from mixing releases and leaving catalog
  or detail pages on their loading states.

## [0.3.2] - 2026-09-13

### Added

- Global Settings controls for including mercenaries, Spec-Ops, Team Operations,
  and reinforcements. The chosen filters apply consistently to the unit catalog
  and unit lists on rules-reference detail pages.
- An opt-in cookie consent flow to remember distance, optional-unit, and
  Developer mode settings on the current device.
- A version endpoint and browser-side release check, plus release-fingerprinted
  static assets and cache headers that safely cache immutable release assets.
- An actionable startup error when the selected web-server port is already in
  use.

### Changed

- Improved web-reference responsiveness by caching immutable database-query
  results and reducing repeated client-side catalog and detail-page work.
- Updated the package, documentation, and About page for version 0.3.2.
- Modernized package license metadata for current setuptools releases.

### Fixed

- Ensured global optional-unit settings affect every related unit list,
  including Skills, Equipment, and Weapons detail pages.
- Corrected optional-unit filter updates and Infinity Wiki link labels on
  catalog detail pages.

## [0.3.1] - 2026-09-13

### Added

- A reusable Settings menu that presents browser preferences in the sidebar on
  wide screens and beside Navigation on compact screens.

### Changed

- Improved unit search and catalog presentation, including army-color accents
  for unit-list and general-profile surfaces.
- Made development-version detection compare the checkout with the current
  release tag, so the browser footer accurately marks unreleased checkouts.
- Updated local build and debug defaults to use the newest source archive in
  `data/raw/` rather than a stale, hard-coded snapshot path.

### Fixed

- Corrected a CSS naming issue and the movement-value display.
- Ensured the reusable navigation menu closes correctly on iOS.

## [0.3.0] - 2026-09-12

### Added

- Default-off Developer mode in the sidebar. It reveals database IDs and ID
  table columns for development and data-review work without exposing them in
  the standard player-facing reference.
- Landing page that introduces InfinityDB and links to the main reference
  catalogs.
- Surface and Deepspace division badges on applicable unit profiles.
- Compact navigation menu for narrow browser widths.

### Changed

- Unified page and detail-card hierarchy around default, subdued, and
  highlighted surface variants, and standardized data tables on comfortable or
  compact density rules.
- Released version 0.3.0 across the package, command-line tools, and browser
  footer.
- `infinity-db build` now requires validated Army API `metadata.json` and the
  database compatibility revision increased to 7; rebuild existing databases
  before starting the application.
- Standardized every browser route on a shared page shell with injected
  navigation, breadcrumb header, catalog tag, and versioned footer. The web UI
  now defines reusable design tokens for its core surfaces, typography,
  borders, spacing, radii, controls, focus treatment, and shadows.
- Consolidated repeated detail-view group, heading, surface-header, data-label,
  and badge styles into shared primitives and added coverage that guards their
  use across detail renderers.

## [0.2.1] - 2026-09-12

### Changed

- Aligned the package and command-line version at 0.2.1.
- Expanded the About page to describe InfinityDB's purpose, local data flow,
  current reference features, and future direction while retaining its
  independent-project and transparency disclosures.
- Refreshed project documentation for the current web reference, data pipeline,
  and database compatibility revision (6).

## [0.2.0] - 2026-09-11

### Added

- Searchable Skills, Equipment, and Weapons reference catalogs with detail
  pages that link each rule item to the unit profiles and loadouts that use it.
- Weapon-reference details for profiles, ammunition, traits, range modifiers,
  and the available special weapon data.
- Order and characteristic icons in unit details, including loadout-specific
  order markers.
- A maintenance tool to reorganize bundled SVG symbols from an Army snapshot.

### Changed

- Reworked unit-detail rendering to group shared and army-specific data more
  clearly and separate successive loadouts visually.
- Normalization and repository queries now preserve and expose catalog-item
  occurrences and their extras across profiles, loadouts, and unit options.
- Bundled army, unit, and order symbols now use stable, ID-addressed static
  paths; asset requests no longer depend on server-side directory scanning.
- Database schema version increased to 6 and compatibility revision increased
  to 5; rebuild existing databases before starting this release.

### Fixed

- Corrected the total AVA displayed in unit details.
- Preserved literal punctuation-only unit searches instead of treating them as
  empty queries.
- Return HTTP 404 for unknown army and order-symbol asset paths.
- Include reorganized army, unit, and order SVG assets in built packages.

## [0.1.2] - 2026-09-11

### Added

- About page with project background, maintainer support contact, GitHub
  repository link, and LLM code-use disclosure.
- Snapshot download-date tracking for downloader-created Army archives, shown
  in the shared browser sidebar when available.
- Clickable unit-catalog rows, while preserving the unit-name link's normal
  browser interactions.

### Changed

- Unit search now ignores case, accents, and punctuation.
- Reinforcement-only records use normalized ISC and display-name identities to
  join a uniquely matching standard unit despite wording and spelling variants.
- Profile grouping normalizes reinforcement prefixes and equivalent profile
  labels more consistently.
- Database compatibility revision increased to 2; rebuild existing databases
  before starting the updated application.

## [0.1.1] - 2026-09-11

### Added

- Persistent centimetre/inch display preference in the shared sidebar, applied
  to movement values and distance-based skill modifiers.
- Skill Modifiers page and API for browsing distance-related skill extras and
  linking directly to the units that use them.
- Reinforcement filter and nested reinforcement-list display in the army
  selector, including reinforcement availability badges on unit details.
- Profile type and classification in general unit profiles.

### Changed

- Army-list aliases are consolidated so equivalent force lists display and
  filter as one army.
- General profiles now group profile names without case sensitivity.
- Army-specific profile and loadout tables are collapsible; only the first
  displayed non-mercenary, non-reinforcement army is expanded initially.

### Fixed

- Normalized distance-modifier signs and conversions for Super-Jump and
  Forward Deployment.
- Kept profile and loadout rows accessible and readable on narrow screens.

## [0.1.0] - 2026-09-10

### Added

- SQLite-backed Infinity database, including a versioned schema, validated
  atomic importer, and read-only repository queries.
- `infinity-db` command-line application with `build`, `merge`, `normalize`,
  `export`, and `serve` workflows, while retaining the JSON-only
  `infinity-army` entry point.
- Local WSGI browser and read-only JSON API for armies and units.
- Unit catalog with army filtering, name search, pagination, and availability
  filters for mercenaries, Spec-Ops, Team Operations, and reinforcements.
- Unit-detail pages that show shared/general profiles and faction- and
  army-specific profiles, loadouts, skills, equipment, weapons, and AVA.
- API metadata import for faction names and ammunition, weapon, skill,
  equipment, and rules catalogs.
- Bundled SVG symbols for armies and units, including fallback resolution for
  source naming variations.
- Manual tools to download Army JSON snapshots and unit symbols.
- Architecture and data-model documentation, VS Code tasks/debug profiles, and
  automated coverage for the pipeline, database, API, and web interface.
- Repeatable Linux deployment using Docker Compose, Gunicorn and Caddy, with
  a production WSGI entry point and an image that embeds a validated SQLite
  snapshot.

### Changed

- Builds now verify lossless source reconstruction, normalized relationships,
  and database integrity before replacing an existing database.
- Army labels now support sectorials and reinforcement lists, with readable
  fallback names and disambiguated shared `reinf` slugs.
- Unit views group armies by faction, distinguish a unit's main army, and
  surface mercenary availability correctly.
- Detail views consolidate common profile data and highlight army-specific
  stat differences, while keeping skills, equipment, and weapons visible at
  the appropriate general, profile, or loadout level.

### Fixed

- Corrected main-army designation for mercenary units.
- Restored missing unit-symbol resolution and added mappings for source naming
  exceptions.
- Improved unit-detail data handling and rendering for profile and loadout
  variations.
