# Changelog

All notable user- or operator-relevant changes to InfinityDB are documented here.
Entries describe meaningful release outcomes rather than detailed implementation history.

## Unreleased

### Added

- Add a derived domain-local application slug registry for Armies, logical Units,
  Skills, Equipment, and Weapons. The registry records deterministic candidates and
  explicit resolved/collision/unavailable states without changing existing public
  numeric routes or inventing order-dependent collision suffixes.
- Separate server-rebuild and transferred-artifact deployment paths so a validated
  database/symbol set cannot be accidentally replaced during deployment, and add an
  isolated loopback-only test deployment with an explicit teardown command that cannot
  expose its Caddy port to the LAN, target production, or prune production rollback images.

### Changed

- Continue the public slug migration across Skills, Equipment, Weapons, and logical
  Units: catalog/unit links and detail APIs use readable domain-local slugs when
  available while existing numeric URLs remain valid for compatibility. Unit payloads
  keep source/context `slug` separate and expose the application route as `public_slug`.
  Catalog identity alias groups may also be
  authored with readable source-label slugs or numeric source IDs; unknown or ambiguous
  slugs fail validation instead of being guessed.
- Validate curated typed record IDs against the shared domain-slug grammar, and make
  Trait slug collisions fail closed instead of producing positional `-2`/`-3` IDs.
- Make the Unit explorer's matching-unit statistic show the currently visible unique
  units alongside the total available under the same Army/search/catalog filters, with
  an expandable availability breakdown for standard and optional unit categories.

### Upgrade notes

- Rebuild generated Army databases after this change. The development schema is now
  17 / compatibility revision 25; older generated `infinity.db` files are rejected.

### Fixed

- Keep settings for the current browser session when persistent settings are
  disabled, show Team Operations-only units on Skill detail pages when that
  optional-unit category is enabled, and use public Skill slugs for source variants
  merged into curated application identities instead of falling back to numeric IDs.
- Preserve the `+dev` browser display version in containerized development/test
  deployments without embedding Git metadata in the image. The API/package release
  version remains unchanged.

## [0.6.1] - 2026-09-20

### Changed

- Improve unit browsing and Army-oriented query performance while moving profile,
  loadout, logical-unit, Army, Skill, Equipment, and Weapon reads onto canonical
  application data without losing source-specific context. In the same-host,
  same-snapshot 0.6.0-to-0.6.1 benchmark, the geometric mean of cold
  medians improved by 2.33%, including 43.94% faster Army listing and 11.68% faster
  Army-filtered unit listing; aggregate cold p95 remained effectively flat
  (+0.52%).
- Preserve richer source projections and weapon/equipment profile metadata behind
  the canonical application identities so cross-Army relationships remain
  available without treating one Army view as the complete game model.

### Upgrade notes

- Rebuild existing generated Army databases before deploying 0.6.1. Schema 16 /
  compatibility revision 24 is intentionally incompatible with older generated
  Army databases; there is no in-place database migration.
- The audited production-like `infinity.db` grew from 13,557,760 to 18,108,416
  bytes (+33.56%) because the new materialized application layers coexist with
  retained source/context representations. Physical source-only separation into
  `infinity.raw.db` remains later work.

### Fixed

- Keep generated deployment artifacts safe when development, CI, and deployment
  checks use synthetic fixture data.
- Reject deployments whose database and published graphical assets do not originate
  from the same verified Army snapshot before they can be activated.
- Count Army unit totals by logical units rather than duplicate source
  representations.
- Avoid redundant catalog-graph reads when resolving Traits through the
  materialized application catalogs.

## [0.6.0] - 2026-09-19

### Added

- Add a separately versioned rules database for cited N5 rules knowledge, including
  skill declaration categories, parameter semantics, trait summaries, and exceptional
  weapon profiles.
- Add reliable logical-unit identities and explicit availability for standard,
  mercenary, and reinforcement units.
- Add verifiable, reproducible source snapshots for Army, wiki, and symbol data.
- Add a resumable symbol build and publication workflow that produces complete local
  graphical assets with source provenance.
- Add a unified validation workflow for local development and CI, including data,
  code, package, deployment, and full-asset checks.
- Add deployment checks and tooling for safely publishing validated local graphical
  assets.

### Changed

- Use authoritative imported relationships and reviewed policy to determine army
  roles, faction presentation, unit identity, and optional-unit availability.
- Move maintained game knowledge into validated configuration and cited rules data,
  rather than duplicating it in application code.
- Treat third-party graphical symbols as locally generated deployment artifacts rather
  than source-distributed assets.
- Require production deployments to include validated Army and rules databases.
- Derive browser-facing faction, profile, army-role, and weapon-range information
  from backend data contracts.

### Upgrade notes

- Rebuild existing generated databases before deploying 0.6.0.

### Fixed

- Preserve distinct graphical-symbol variants and their provenance through publication,
  including explicitly unavailable upstream assets.
- Make symbol publication recoverable and reproducible after interrupted or failed
  builds.
- Keep installed-package validation and symbol processing reliable across the supported
  development workflow.

## [0.5.1a] - 2026-09-15

### Added

- Add the foundation for cited curated rules data and archived wiki sources.
- Clarify licensing boundaries for InfinityDB code, external game data, and graphical
  assets.

### Changed

- Stop distributing third-party graphical symbols in the source tree by default.
- Improve cross-platform handling of wiki-mirror paths and local asset URLs.

## [0.5.1] - 2026-09-14

### Added

- Add advanced unit-catalog filters for skills, equipment, and weapons.
- Add Traits catalog and detail pages with concise summaries and usage links.
- Add deployment maintenance tools and a Developer-mode cache bypass for local review.

### Changed

- Improve deployment guidance and ensure browsers load matching release assets after
  an update.

### Fixed

- Remove incompatible browser theme metadata from static pages.

## [0.4.2] - 2026-09-14

### Fixed

- Apply optional-unit settings consistently to unit availability, including
  mercenary and reinforcement armies, without stale browser results.

## [0.4.1] - 2026-09-13

### Changed

- Direct support questions, suggestions, and feedback to the project GitHub page.

## [0.4.0] - 2026-09-13

### Added

- Add a raw database archive for development and data review alongside the lean
  deployed database.
- Add snapshot-aware API caching and automatic browser refresh when release or source
  data changes.
- Add a maintained backlog for future performance, pipeline, operational, and product
  work.

### Changed

- Improve responsiveness of high-volume unit and catalog queries.
- Improve browser navigation feedback while page data is loading.
- Clarify InfinityDB's data-driven reference scope and future direction.

## [0.3.3] - 2026-09-13

### Fixed

- Prevent cached browser modules from mixing releases and leaving catalog or detail
  pages in a loading state.

## [0.3.2] - 2026-09-13

### Added

- Add global controls for including mercenaries, Spec-Ops, Team Operations, and
  reinforcements across relevant unit lists.
- Add an opt-in cookie consent flow for saving display and browsing preferences on the
  current device.
- Add release-aware browser updates and clear startup guidance when a server port is
  already in use.

### Changed

- Improve responsiveness of the web reference and update project release metadata.

### Fixed

- Apply global optional-unit settings and external wiki-link labels consistently on
  catalog detail pages.

## [0.3.1] - 2026-09-13

### Added

- Add a reusable responsive Settings menu.

### Changed

- Improve unit search and catalog presentation, including army-color accents.
- Make the browser footer accurately identify unreleased checkouts.
- Use the newest available local source archive for default builds and debugging.

### Fixed

- Correct movement-value presentation and mobile navigation behavior.

## [0.3.0] - 2026-09-12

### Added

- Add an opt-in Developer mode for database IDs and data-review columns.
- Add a landing page, compact navigation, and division badges for applicable unit
  profiles.

### Changed

- Establish a consistent responsive visual system and shared page shell across browser
  routes.
- Require validated Army metadata when building a database.

### Upgrade notes

- Rebuild existing databases before deploying 0.3.0.

## [0.2.1] - 2026-09-12

### Changed

- Expand the About page with InfinityDB's purpose, local data flow, current reference
  features, future direction, and independent-project disclosures.

## [0.2.0] - 2026-09-11

### Added

- Add searchable Skills, Equipment, and Weapons catalogs with detail pages that link
  rule items to the unit profiles and loadouts that use them.
- Add weapon profiles, ammunition, traits, range modifiers, special-weapon details,
  and relevant order and characteristic icons to unit references.
- Add maintenance support for organizing Army symbol assets.

### Changed

- Improve unit-detail presentation of shared, army-specific, profile, and loadout
  information.
- Preserve catalog-item usage and associated details throughout database and browser
  views.
- Use stable static paths for graphical symbols.

### Upgrade notes

- Rebuild existing databases before deploying 0.2.0.

### Fixed

- Correct displayed AVA, literal punctuation searches, missing-asset responses, and
  packaged symbol availability.

## [0.1.2] - 2026-09-11

### Added

- Add an About page, snapshot download dates in the browser, and clickable unit
  catalog rows.

### Changed

- Make unit search insensitive to case, accents, and punctuation.
- Improve reinforcement matching and profile grouping despite source naming variants.

### Upgrade notes

- Rebuild existing databases before deploying 0.1.2.

## [0.1.1] - 2026-09-11

### Added

- Add a persistent centimetre/inch preference, Skill Modifiers reference, and
  reinforcement filtering and availability in unit views.
- Add profile type and classification to general unit profiles.

### Changed

- Present equivalent army lists as one filterable army and improve profile and
  loadout grouping.

### Fixed

- Correct distance-modifier display and keep profile and loadout rows usable on
  narrow screens.

## [0.1.0] - 2026-09-10

### Added

- Add a validated SQLite-backed Infinity data pipeline, command-line workflows, and
  local browser and JSON API.
- Add unit catalog and detail views for armies, profiles, loadouts, skills,
  equipment, weapons, AVA, and optional-unit availability.
- Add imported faction and catalog metadata, graphical symbols, source-acquisition
  tools, developer documentation, automated coverage, and repeatable Linux
  deployment.

### Changed

- Validate source reconstruction, normalized relationships, and database integrity
  before replacing an existing database.
- Improve army labels, faction grouping, mercenary availability, and presentation of
  shared and army-specific unit details.

### Fixed

- Correct mercenary main-army designations, source-symbol resolution, and profile and
  loadout rendering.
