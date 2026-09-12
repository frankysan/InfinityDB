# Changelog

All notable changes to this project are documented in this file.

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
