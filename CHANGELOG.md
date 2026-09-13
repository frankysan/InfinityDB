# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Changed

- Cache snapshot-wide unit relationships and visible logical-unit mappings for
  unit, skill, and catalog queries, avoiding repeated membership, faction,
  search-term, and catalog-pagination assembly per request.

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
- Repeatable Linux deployment using Docker Compose, Gunicorn, and Caddy, with
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
