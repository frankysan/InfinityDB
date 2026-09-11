# Changelog

All notable changes to this project are documented in this file.

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
