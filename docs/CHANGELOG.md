# Changelog

All notable user- or operator-relevant changes to InfinityDB are documented here.
Entries describe meaningful release outcomes rather than detailed implementation history.

## Unreleased

### Fixed

- Prevent check, CI, and deployment-smoke fixture builds from writing to
  `data/generated/`, so synthetic test data cannot replace deployment artifacts.
- Bind production `infinity.db` to the terminal symbol publication's exact Army
  ZIP SHA-256 and reject mismatched or missing provenance during deployment,
  transfer, and published-image validation without requiring raw archives on the server.

## [0.6.0] - 2026-09-19

### Added

- Add a separately versioned curated-rules pipeline and `rules.db` runtime database.
  Cited N5 rules data now supplies skill declaration categories and parameter
  semantics, trait identities and summaries, and exceptional weapon profiles while
  Army-derived storage remains source-data-only.
- Add validated source-identity and display-identity configuration. Normalization
  pins the exact identity policy, records explicit standard/mercenary availability,
  and persists generic, mercenary, and reinforcement matching evidence so frontend
  databases can materialize stable logical-unit identities.
- Add deterministic acquisition provenance for Army, wiki, and symbol snapshots.
  Timestamped immutable archives are SHA-256-bound under `data/manifests/`, human
  snapshot notes remain separate curated data, Army downloads are coherence-checked,
  and reviewed source anomalies are enforced as a regression baseline.
- Add the complete resumable symbol-build pipeline. A pinned Army snapshot now flows
  through source discovery/acquisition, verified materialization, SVG preflight,
  installed-font audit, exact-first visual deduplication, text-to-path conversion,
  balanced compression, and transactional publication with SHA-bound reports,
  checkpoints, backups, generated browser maps, and `symbol-inventory.json`.
- Add a unified development/CI validation contract through `tools/run_checks.py`,
  including deterministic reports, Ruff and Pyright coverage, hermetic and
  full-asset modes, cross-platform source checks, installed-wheel smoke testing,
  Docker deployment smoke testing, and a manually dispatched private full-asset
  workflow.
- Add deployment safeguards for locally published graphical assets. Deployment now
  verifies the manifest-bound host publication before building, validates the exact
  installed image and representative symbol routes before activation, and provides a
  commit-bound one-SSH-session helper for transferring only ignored deployment
  artifacts to a matching server checkout.

### Changed

- Release metadata now identifies this version as 0.6.0. Documentation
  distinguishes locally validated and configured CI behavior from hosted workflow
  executions, which remain release evidence tracked in the backlog.

- Rework unit and army identity around authoritative imported relationships and
  pinned policy rather than runtime heuristics. Army roles, playability, grouping,
  reinforcement parents, faction presentation, main-army identity, profile identity,
  and optional-mercenary semantics are now derived or materialized explicitly;
  Non-Aligned grouping identity `901` remains non-playable and distinct from
  canonical mercenary source identity `1`.
- Move maintained game/domain knowledge out of browser and repository code into
  validated configuration or curated rules data. This includes reinforcement label
  policy, weapon taxonomy and source corrections, skill declaration categories and
  distance semantics, trait canonicalization, special weapon profiles, and curated
  display-army identity.
- Standardize Army, wiki, and symbol acquisition on timestamped ZIP snapshots with
  generated provenance. Wiki acquisition is language-scoped and fail-closed for
  required content, while symbol acquisition resolves each authoritative reference
  through explicit local overrides, validated immutable cache, then network access.
- Treat Corvus Belli graphical symbols as local generated deployment artifacts rather
  than redistributable source assets. Complete published assets are inventory-bound
  and may be materialized for a local installation, but are not bundled in source or
  redistributable release images by default.
- Make `tools/build_symbols.py` the maintained symbol orchestration entrypoint with
  forward-only manifest transitions, explicit failed-stage retry, resumable
  checkpoints, compact interactive stage progress, and complete timestamped logs.
- Require production deployments to include both validated `infinity.db` and
  `rules.db`, and package the maintained build configuration needed by installed
  build/runtime tools. Read-only runtime imports are independent of exporter-only
  normalization policy.
- Derive browser-facing data from backend/source contracts instead of duplicated UI
  assumptions, including profile display names/identity, faction metadata, army
  roles, and weapon range columns.
- Bump the Army frontend database to schema version 11 and compatibility revision 16,
  the identity configuration to schema version 2, and the rules database to schema
  and compatibility version 2. Existing generated databases must be rebuilt.
- Complete Milestone 1 ingestion acceptance: the pinned Army/wiki/symbol path has
  exact provenance through runtime artifacts, the live version-2-through-version-8
  symbol pipeline passed rollback and repeated-build reproducibility acceptance, and
  deployment acceptance proved missing assets are rejected before activation.

### Fixed

- Preserve complete symbol semantics through publication: distinct profile-slot and
  non-owner-army artwork receive deterministic published variants, characteristic
  icons use their own namespace, unavailable upstream HTTP 404 assets remain explicit
  provenance instead of aborting acquisition, and validation covers the complete
  publication rather than only browser-referenced assets.
- Harden symbol manifest and publication transactions so invalid duplicate summaries,
  backward stage transitions, stale compressed inputs, terminal republishing, and
  publication failures cannot silently corrupt or demote accepted state; removed prior
  assets are preserved in timestamped backups.
- Remove unresolved local raster references from temporary conversion copies before
  Inkscape so randomized `svg-font-pipeline-*` paths cannot leak into canonical or
  published SVG bytes. Repeated same-snapshot builds now produce zero publication
  delta.
- Restore installed-package/runtime validation by separating read-only database
  imports from repository-relative build configuration and by packaging the validated
  configuration required by installed build tools.
- Make the symbol-processing toolchain clean under the maintained Ruff/Pyright
  contract and stream compression progress through the shared console/logging layer
  without losing the full per-file transcript.

## [0.5.1a] - 2026-09-15

### Added

- Add the initial curated-rules data structure and supporting documentation for
  separating PDF/wiki-derived rules knowledge from Army JSON-derived data.
- Add a wiki snapshot downloader plus focused regression coverage for the standalone
  tools and project-local pytest temp/cache configuration for reliable Windows runs.
- Add third-party notices and clarify the licensing boundary between InfinityDB's
  original code, external game data/assets, and deployment dependencies.

### Changed

- Remove Corvus Belli graphical SVGs from the tracked source tree and ignore generated
  army, order, and unit symbol directories so third-party graphical assets are no
  longer redistributed with the repository by default.
- Harden cross-platform path sanitization and wiki-mirror file handling while
  preserving compatible local URLs and asset naming.

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
