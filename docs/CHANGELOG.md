# Changelog

All notable changes to this project are documented in this file.

## Unreleased

### Changed

- Synchronize reference documentation with the completed manifest-backed symbol
  pipeline and add a dedicated server-migration guide that distinguishes exact
  runtime transfer from rebuild/source-provenance requirements.
- Define symbol manifest stage transitions as forward-only. Failed-stage retry is
  explicit; passed later states cannot be silently demoted by invoking an earlier
  processing helper.
- Reduce `tools/build_symbols.py` console noise to compact stage-level output
  with a single updating progress line for the active interactive stage, while
  retaining the complete verbose transcript in timestamped `data/logs/symbols/`
  logs and supporting an explicit `--log` destination.
- Add a separate normalized `display_army_id` derived from pinned curated
  display-identity data. Canonical mercenary source identity remains distinct
  from Non-Aligned ownership/playability, while the UI can use the curated
  grouping identity for representative symbols and faction styling.
- Bump the Army database schema to 11 and compatibility revision to 16; rebuild
  generated databases after updating.

### Fixed

- Stream orchestrated compression progress through the pipeline console/logging
  layer so the compression stage shows a monotonic running status indicator and
  its full per-file transcript is retained in the symbol-build log.
- Validate the complete published symbol inventory rather than treating only the
  currently browser-referenced subset as the full asset set. New publications
  SHA-bind `symbol-inventory.json`, while browser-only variants remain required
  future-use assets.
- Publish characteristic icons under `static/characteristics/` instead of the
  legacy `static/orders/` location, with browser routes, packaging, asset checks,
  and rollback handling using the same maintained classification.
- Harden version-5 duplicate summary invariants and the v5-to-v8 promotion
  boundaries so impossible counts, downstream manifest rollback, and terminal
  republishing are rejected.
- Preserve distinct unit profile-slot symbol artwork during publication by keeping
  the first profile at the stable unit path and assigning deterministic
  `--<group>-<profile>` suffixes to later distinct profile symbols and
  `--army-<army-id>` namespacing to distinct non-owner-army variants, while
  exact duplicates continue to share one canonical file.

- Treat source-declared symbol URLs that return HTTP 404 as explicit unavailable
  upstream assets instead of aborting the complete symbol acquisition. The
  versioned build manifest retains their URL/reference provenance, downstream
  processing operates on the acquired subset, publication omits unavailable
  mappings, and non-404 network failures remain fatal.

- Make `tools/svg_processor.py` clean under the project Ruff/Pylance expectations:
  optional symbol dependencies are loaded without static unresolved-import noise,
  classification results have explicit types, and remaining lint diagnostics are
  corrected. Extend the default Ruff target set to the maintained symbol
  toolchain so future symbol-processor regressions fail local/CI code checks.

- Bring reference documentation and backlog status in line with the implemented
  CI, snapshot-provenance, and asset-redistribution contracts. Remove stale
  future-only wording for acquisition/provenance and clarify that remaining CI
  hardening no longer blocks symbol-pipeline work.

- Decouple read-only database/web runtime imports from the database exporter and
  Army normalization policy. Installed runtime validation can now open generated
  `infinity.db` and `rules.db` without repository-relative weapon configuration,
  restoring the deployment-smoke package boundary.

- Add the installed-font stage of the symbol pipeline. Infinity-specific legacy
  font aliases now live in validated `config/symbols/font-aliases.json`; the
  orchestrator resolves effective fonts and unused declarations against the local
  font environment, writes a SHA-bound `font-audit.json`, and promotes successful
  structural-preflight state from symbol manifest version 3 to version 4.

- Add verified post-acquisition symbol materialization and structural SVG preflight.
  `build_symbols.py` now revalidates the immutable symbol archive/provenance and
  every member hash before replacing a derived `data/work/symbols/` tree, writes
  a deterministic parse/text/font-declaration report under `data/reports/symbols/`,
  and promotes acquisition-only symbol build state from version 2 to version 3.
  Version-2 manifests remain valid cache inputs.

### Added

- Bind every balanced compression output SVG by SHA-256 in the version-7
  compression report and verify those exact bytes before version-8 publication.
  Publication also reconciles the incoming/previous asset inventories and
  transactionally preserves removed prior SVGs under `data/backups/symbols/`.
- Generate `symbol-inventory.json` as the authoritative complete publication
  contract, distinct from the smaller subset currently referenced by browser
  mappings/endpoints.
- Add explicit symbol-pipeline checkpoints and SHA-bound resume support to
  `tools/build_symbols.py`. Live acceptance can now stop after snapshot,
  acquisition, materialization, preflight, font audit, deduplication, text
  conversion, compression, or publication, then continue without reacquiring
  immutable inputs. Resume verifies existing raw work instead of replacing a
  later-stage work tree.

- Integrate final non-destructive symbol publication into `build_symbols.py`.
  Passed version-7 compression state now advances to version 8 after a temporary
  publication tree, generated browser mappings, and the complete
  source/canonical-to-published mapping validate. The publisher transactionally
  replaces only generated `armies/`, `characteristics/`, `orders/`, `units/`,
  `army-symbols.js`, and `unit-symbol-map.js` outputs, restores prior publication
  on failure, and removes the legacy first-symbol-wins mapping behavior. Before
  replacement it records added/removed/changed symbol differences against the
  previous generated tree and preserves removed prior SVGs in timestamped local
  backups under `data/backups/symbols/`.

- Integrate display-aware canonical symbol compression into `build_symbols.py`.
  Passed version-6 text-conversion state now advances to version 7 using the
  reusable `svg_compress.py` engine with the balanced production profile and
  SHA-bound compression reports; validated output atomically replaces the derived
  compressed work tree while failures preserve the prior state/tree.

- Integrate canonical text-to-path conversion into `build_symbols.py`. Version-5
  duplicate state now advances to version 6 with SHA-bound conversion reports,
  converter identity/settings, and a canonical work tree that converts only
  active-text representatives while carrying no-text representatives forward
  unchanged. Persistent `inkscape --shell` workers are the production default;
  conversion failure records failed state without replacing existing canonical
  output.

- Expand the normal code-check contract with Pyright type checking, full `tools/`
  Ruff coverage, and synthetic integration tests against the real symbol Python
  dependency stack. Required source CI now installs `.[dev,symbols]` on every
  platform/interpreter leg.

- Integrate exact-first visual symbol deduplication into `build_symbols.py`.
  Successful font-audited builds now produce version-5 symbol state with
  duplicate reports, renderer settings, conservative render-error handling, a
  complete portable raw-asset-to-canonical mapping, and total source/canonical
  loose-SVG size accounting while retaining every original source reference.

- Add a dispatch-only `Full-asset checks` GitHub Actions workflow. The job is
  restricted to `main`, stages a checksum-pinned private SVG bundle supplied
  through the dedicated `full-assets` environment, and runs the normal project
  checks with `--assets required` without uploading third-party graphical assets
  as workflow artifacts.

- Expand `Source checks` into a hermetic operating-system matrix covering Windows,
  Ubuntu/Linux, and macOS at Python 3.11, with an additional Linux Python 3.14
  compatibility leg.

- Add an `Installed wheel smoke` GitHub Actions workflow. Wheels now package the
  maintained identity, weapon-catalog, and source-anomaly build configuration
  under `share/infinity-db/config/`; the smoke job installs the wheel into a
  fresh virtual environment and validates both installed build CLIs plus runtime
  startup against generated fixture databases outside the source checkout.

- Add a clean-checkout Linux `Source checks` GitHub Actions workflow that runs
  the normal hermetic test/lint/build/rules contract on Python 3.11 using the
  tracked synthetic Army fixture rather than live data or third-party assets.

- Add explicit hermetic/full-asset test modes. `run_checks.py --assets
  off|auto|required` validates the complete current published symbol set before
  enabling `full_assets` pytest coverage; direct pytest is hermetic by default,
  partial/corrupt local asset trees fail strict modes, and project-owned SVG
  fixtures retain dynamic static-serving coverage without third-party artwork.
- Make web version-display assertions independent of incidental Git-checkout
  state by testing against the application's controlled display version.

- Add `tools/build_symbols.py` as the explicit symbol-refresh orchestration
  entrypoint. It pins one verified Army snapshot through raw symbol discovery
  and acquisition, supports offline `--snapshot` and explicit online
  `--fetch-snapshot` modes, and exposes reusable Army/symbol acquisition
  results for later processing stages.
- Add a validated source-anomaly regression baseline for the exact 2026-09-18
  Army snapshot. InfinityDB application builds allow reviewed warning counts to
  decrease but reject new warning categories or growth above the recorded
  ceiling before database export.
- Support an optional Git-ignored root `AGENTS.local.md` for user-specific agent
  workflow and communication preferences while keeping tracked project
  instructions authoritative.
- Add a Docker deployment smoke workflow that builds `infinity.db` from a
  synthetic Army fixture plus the tracked `rules.db`, validates the image's
  runtime-data contract, rejects third-party symbol trees in redistributable
  builds, and exercises healthy non-root/read-only Gunicorn startup.
- Add project-level markdownlint configuration that keeps `MD024` duplicate-heading checks within sibling headings, allowing standard changelog headings such as `Added`, `Changed`, and `Fixed` to repeat under different releases.
- Add `tools/run_checks.py` as the standard development-check orchestrator for
  pytest, Ruff, Army build validation, and curated rules-database build
  validation, with selectable stages/profiles,
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
- Add reduced raw Army-shaped mercenary regression fixtures based on the observed
  Miranda Ashcroft, Yuan Yuan, and Valerya Gromoz source patterns. The fixtures
  exercise merge-to-normalization classification, fail-closed contract drift,
  mercenary-to-standard matching, and same-army standard/optional overlap.
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
- Add versioned snapshot-provenance and snapshot-note contracts. Army, wiki,
  and symbol acquisition now writes deterministic SHA-256-addressed provenance
  under `data/manifests/snapshots/`, while human annotations remain separate
  under `data/curated/snapshot-notes/`.

### Changed

- Update the official checkout and Python setup actions used by GitHub workflows
  to their current Node-24-compatible major versions.

- Resolve raw Army symbols through Git-ignored local overrides, a validated
  prior immutable symbol snapshot/cache, then upstream network access. Add
  `--image-overrides` and `--refresh-symbols`, report unused overrides and
  filename collisions, validate cached archive/member hashes before reuse, and
  record `override`, `cache`, or `network` as each asset's source method.
- Migrate curated rules provenance to format v3. PDF sources now retain both the
  reviewed local file and official Corvus Belli Resources URL; archived wiki
  sources bind to exact timestamped ZIP/hash/acquisition provenance and use
  archive-member citations, while pinned `oldid=` wiki revisions remain
  URL-backed sources. Bump the independent rules database schema and compatibility revision to preserve
  the richer provenance.
- Make wiki snapshot acquisition fail closed for required content. Required
  crawl failures publish neither the immutable `WIKI-<language> ...zip` archive
  nor snapshot provenance and preserve partial work under `data/work/wiki/`.
  Optional `/favicon.ico` and `Infinity:` MediaWiki project-namespace targets
  are classified as ignored site chrome/project links rather than content
  failures.
- Scope wiki acquisition by language. English is now the default, Spanish can be
  selected explicitly, cross-language page crawling is suppressed while directly
  referenced assets remain eligible, localized special-page namespaces are skipped,
  and both archive names and snapshot provenance record the selected language.
- Make Army JSON acquisition coherence explicit: the downloader now verifies a
  second complete metadata/list pass byte-for-byte before publishing a snapshot,
  reports changed endpoints on instability, and prints accepted source-revision
  counts without requiring one global Corvus Belli revision.
- Clarify current asset-distribution language: Corvus Belli graphical symbols
  may be published into a local installation but are not bundled with InfinityDB
  source code or redistributable releases by default.
- Replace first-logo-per-unit symbol acquisition with complete source-semantic
  Army discovery. `download_army_symbols.py` now preserves every profile/faction
  reference, includes maintained static symbols, audits `resume` and unknown SVG
  source locations, downloads each authoritative URL once, and no longer
  generates browser symbol mappings.
- Upgrade the acquisition-only `army-symbol-build.json` generated state to
  version 2. It now persists the verified Army source URL, language, acquisition
  timestamp/document count, and observed source revisions alongside the Army
  artifact identity, so later symbol stages consume the pin from build state
  instead of CLI memory or filenames.
- Move reinforcement-label prefixes (`REINF` / `REFUERZOS`) into the validated
  identity policy and derive profile `display_name` values in the backend. The
  browser now consumes `display_name` and `profile_identity` instead of carrying
  a duplicate reinforcement-prefix regex. Because existing generated databases
  pin an older identity-config contract, bump the identity-config schema to 2
  and Army database compatibility revision to 15 while keeping SQLite schema 10.
- Make skill-extra distance detection authoritative to imported Army
  `extras.type` metadata instead of numeric-text heuristics. Numeric text such as
  `+5 CC` no longer needs an application exception. Move the remaining
  Super-Jump and Forward Deployment sign-display conventions into cited curated
  skill parameter semantics consumed through `SkillCatalog`, removing duplicate
  skill-name branches from backend and browser code.
- Derive weapon range-table columns from imported profile distance endpoints
  instead of maintaining a fixed global range-band list. Inch labels use the
  existing 2.5 cm conversion and remain aligned across all profiles for a weapon.
- Move Armed Turret non-display metadata-profile suppression out of the runtime
  repository and into validated weapon source-correction configuration applied
  during normalization.
- Move maintained weapon-family taxonomy, regex classification policy, manual
  category decisions, and Army-source weapon metadata corrections out of Python
  into validated `config/catalogs/` configuration. Classification mechanics
  remain code and game-rule facts stay outside source-correction configuration.
- Move the Armed Turret special profile out of Python into a cited curated
  `weapon` rules record linked to Army weapon ID 226. Weapon API responses now
  compose that profile from `rules.db`, while the Army repository remains
  source-data-only and degrades cleanly when curated rules are unavailable.
- Move N5 skill declaration categories out of `skill_categories.py` into cited
  curated `skill-declaration-category` records linked to Army skill IDs. Skill
  list/detail APIs now compose declaration categories and ordinary skill rules
  through `SkillCatalog`; the Army repository no longer embeds rule-derived
  declaration knowledge.
- Reconcile reference documentation with the completed logical-unit and army-role
  refactors: source-unit identity is now distinguished from materialized
  application identity, repository-time identity discovery is no longer described
  as current behavior, and completed refactor backlog history is removed.
- Remove the obsolete repository-side logical-unit identity discovery path now
  that frontend databases materialize complete identity. Legacy duplicate
  compatibility behavior remains build-time only, with its regression coverage
  moved to the logical-unit resolver/audit tests.
- Materialize application logical-unit identity during frontend database
  creation. The exporter resolves configured aliases plus persisted generic,
  mercenary, and reinforcement evidence into frontend-only `logical_units` and
  `logical_unit_sources` tables while retaining all source rows and occurrence
  provenance. Repository reads now consume that materialized mapping; schema
  version is 10.
- Audit unambiguous reinforcement-only source-unit identity during database
  creation and persist `reinforcementUnitMatches` alongside the pinned identity
  policy. The audit now feeds materialized logical-unit identity instead of
  repository-time name/ISC matching; an empty audit remains authoritative.
- Persist generic standard-unit duplicate matches as `genericUnitMatches` during
  normalization. The database builder consumes that audit when materializing
  logical-unit identity; an explicitly empty audit disables arithmetic
  rediscovery, while older normalized inputs without the metadata retain the
  legacy build-time fallback.
- Derive normalized unit `main_army_id` from imported Army metadata faction
  parents instead of the `xx01` Army-ID convention for current InfinityDB
  builds. Explicit maintained canonical-faction overrides still take
  precedence; the arithmetic rule remains only as a standalone/legacy fallback
  when metadata cannot resolve the canonical faction.
- Derive army role/playability from authoritative imported relationships
  instead of Army-ID ranges. `/api/armies` now exposes explicit roles,
  playability, grouping metadata, and reinforcement parents for main armies,
  sectorials, Non-Aligned forces, reinforcement lists, and grouping
  identities. Non-Aligned grouping identity `901` is surfaced as non-playable,
  direct unit filtering by it is rejected, and the browser army selector
  consumes the backend role contract.
- Remove the runtime `901` Non-Aligned grouping special case. Role derivation is
  now structural: self-parented imported parents remain main armies, while
  ordinary imported parents that are not self-parented (and referenced
  metadata-only parents) become grouping nodes. Current source list `901` has
  metadata parent `900`, parents the NA2 child lists, retains its real source
  roster, and is still exposed as non-playable without any numeric-ID special case.
- Document the observed `901` roster shape separately from playability: one
  standard Rumbler Spec-Ops source entry plus the complete 49-variant optional-
  mercenary pool in the analyzed snapshot. Keep that non-playable roster as
  preserved source provenance without adding a dedicated application roster
  query; unit availability is consumed through the playable child NA2 lists.
  Record a future design direction to canonicalize invariant logical-unit data
  while preserving explicit army, loadout, availability, and raw-source deltas.
- Remove the legacy canonical-faction `1` -> `901` identity override now that
  mercenary logical pairing and army-occurrence availability are explicit.
  Canonical source ID `1` remains mercenary source/origin provenance with no
  application `main_army_id`; `901` remains the separate Non-Aligned Armies
  grouping identity. That change bumped the Army database compatibility
  revision to 12 and required existing generated databases to be rebuilt.
- Make repository mercenary filtering consume explicit
  `army_units.availability_kind` provenance. Current normalized snapshots no
  longer use canonical faction `1` plus faction membership to decide whether an
  army occurrence requires the `mercs` filter; that inference remains only as a
  fallback for legacy rows without availability provenance.
- Make `units.source_role` and `army_units.availability_kind` explicit frontend
  SQLite schema fields instead of incidental dynamic columns. Existing generated
  Army databases must be rebuilt when the cumulative schema/compatibility
  revision changes.
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
- Implement the accepted snapshot-metadata design as generated provenance under
  `data/manifests/snapshots/` plus separate human annotations under
  `data/curated/snapshot-notes/`. Generated manifests are SHA-256-bound,
  validated, deterministic, ignored by Git, excluded from Docker packaging, and
  never overwrite curated notes.
- Scope rules-database ingestion to `data/curated/rules/`; `infinity-db
  build-rules` now defaults to that subtree so other curated data categories are
  not implicitly treated as rules collections.
- Clarify documentation status throughout the corpus so current behavior,
  accepted design direction, and planned/unimplemented work are not presented as
  equivalent. Legacy wiki provenance remains documented as legacy until the
  downloader/packager and curated provenance contract are migrated together.
- Document the source-data finding that canonical-faction ID `1` represents a
  mercenary source/origin concept distinct from Non-Aligned Armies grouping ID
  `901`; the former ownership override has since been removed in Unreleased.
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
- Move trait canonical identities, aliases/misspellings, parameterized source
  matching, concise summaries, and citations into curated `trait` records in
  `rules.db`. Army storage now preserves raw trait labels/usage only, while the
  application composes curated references at read time and falls back to raw
  labels when the rules database is unavailable.
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
