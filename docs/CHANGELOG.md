# Changelog

All notable user- or operator-relevant changes to InfinityDB are documented here.
Entries describe meaningful release outcomes rather than detailed implementation history.

## Unreleased

### Added

- Link Concealed bidirectionally to Camouflaged State, making its reuse of that State's
  effects discoverable without incorrectly representing it as State entry.
- Link Stealth bidirectionally to Cautious Movement using the existing `enables-use-of`
  relationship, exposing the documented ZoC/Hacking Area exception without flattening the
  remaining declaration, LoF, and ARO conditions into the graph edge.
- Add bidirectional restrictive-State self-recovery interactions: Dodge now cancels IMM-A,
  Reset also cancels Isolated, and IMM-A / IMM-B / Isolated expose the State-specific Dodge
  or Reset roll interaction from both endpoints without duplicating the exact MOD values.
- Expand Targeted State into a bidirectional interaction hub: Forward Observer now causes
  Targeted, Reset cancels Targeted/IMM-B, and Targeted exposes which player-facing Skills
  receive its roll modifiers or declaration restrictions. Reverse navigation is derived
  automatically from the one-way curated graph.
- Add a first-class rules-backed States catalog and bidirectional recovery graph: Doctor
  and Engineer now author typed State-cancellation relationships, while affected State
  pages expose derived `Cancelled by` navigation. The enrichment coverage audit now treats
  States as a normal audited player-facing surface.
- Expand the bidirectional gameplay-interaction graph with Sensor as the first multi-edge
  hub: Sensor now links to Mimetism, Discover, Camouflage, Camouflaged State, and Hidden
  Deployment State, while affected pages receive derived reverse relationships. Add
  reviewed Hidden Deployment Skill/State identities so Sensor's hidden-state interaction
  resolves to stable rules concepts.
- Add bidirectional gameplay-interaction enrichment so players can discover rule
  interactions from either endpoint: Multispectral Visor reduces Mimetism MODs; Sixth
  Sense and Combat Instinct negate Stealth; and Combat Instinct ignores Surprise Attack
  MODs. Reverse relationships are derived automatically rather than maintained twice.
- Add a deterministic rules-enrichment coverage audit across the currently exposed
  Skill, Equipment, Weapon, Trait, and State catalogs, reporting missing definitions,
  review/source freshness gaps, ambiguous family/exact-source mappings, and unresolved
  related-item targets against a pinned `infinity.db` + `rules.db` pair. A maintained
  fail-closed classification policy now labels every detected gap as release-blocking or as
  an explicitly reviewed scope exception, while rules-only relation targets remain identified
  as supporting identities without requiring standalone UI.
- Add reviewed exact-source Level semantics for Martial Arts L1-L5 and Strategos L1-L2,
  preserving their shared browsing families while exposing the applicable Level on each
  source variant and Unit occurrence.
- Show the existing curated rules reference on Skill, Trait, Equipment, and Weapon
  detail pages through one shared renderer, including applicability context and linked
  authoritative citations.
- Add typed rules relationships with derived reverse navigation, replacing generic
  related-record lists with explicit semantic edges for state transitions, Peripheral
  subtype/controller relationships, and exact source variants linked to their rule
  family.
- Explain Regular and Irregular Training alongside the corresponding Unit loadout
  Orders, with reviewed rules summaries and cited sources while keeping special
  Order-generation types separate.

### Changed

- Add reviewed No Cover / Limited Cover rules and a bidirectional precedence relationship so players can see immediately that No Cover overrides Limited Cover when both restrictions apply.

- Expand the bidirectional CC interaction graph with Natural Born Warrior as a counter
  hub for Martial Arts and Surprise Attack MODs, deriving reverse navigation on both
  affected Skill pages while preserving the rule's CC-only activation conditions.

- Expanded the 0.7.0 bidirectional interaction graph with reviewed
  Marksmanship/Multispectral Visor counter relationships from Albedo and Reflective.

- Surface reviewed rules relationships with resolved endpoint metadata and
  direction-aware player-facing labels, preserving one-way curated authorship while
  using derived reverse navigation.
- Improve rules-reference readability for players by labeling Requirements,
  Effects, and Restrictions explicitly and presenting Requirements before rule
  effects rather than rendering semantically different facts as anonymous lists.
- Expose reviewed exact-source semantics directly on Equipment/Weapon usage variants,
  allowing detail pages to label named variants such as TinBot Firewall/Discover from
  structured rules data while keeping occurrence modifiers separate.
- Present the Army weapon-profile `damage` value using the N5 Possibility of Survival
  (`PS`) label across ranged and melee/Equipment profile details while preserving the
  upstream field name in application data for compatibility and provenance.
- Strengthen the structured rules contract with deterministic multi-publication
  composition, typed related-item links, explicit family-versus-source variant
  inheritance, and cross-domain declaration categories. N5.3 action classifications are
  reconciled for the audited Skill mismatches and for Deactivator, GizmoKit, and MediKit
  as Equipment actions; non-current collections remain excluded from normal enrichment.

## [0.6.3] - 2026-09-22

### Added

- Add reviewed N5.3 rules records for Doctor, Engineer, Cyberplug, Peripheral, and
  all five Peripheral types, including validated controller-eligibility and
  Connected/Autonomous profile-mode facts.
- Add canonical Peripheral identity and relationship data across both embedded and
  ordinary Unit-backed source mechanisms. InfinityDB now preserves reviewed subtype
  identity, canonical attachments, standalone Unit-backed Peripheral identity, and
  Cyberplug Controller access pools without inventing unsupported ownership links.
- Materialize occurrence-scoped Profile, Loadout, and top-level Unit-option include
  relationships, plus 96 selection-safe Unit constraints and 14 deterministic
  same-Unit profile-group dependency relationships. Selector-ambiguous source rows
  remain explicit source/context data rather than being guessed into canonical rules.
- Add deterministic semantic audits for relationships, Fireteams, normalization-only
  link storage, application/raw database separation, and source-to-presentation
  completeness. The maintained Army completeness inventory covers all 70 normalized
  source tables / 441 fields and fails closed when a new source construct has not been
  classified.

### Changed

- Physically separate generated Army storage: `infinity.db` now publishes only the
  self-contained application schema, while `infinity.raw.db` owns the complete
  queryable normalized source schema plus exact lossless row JSON. Full
  source-to-canonical checks run against a temporary relational staging database
  before publication, and runtime validation no longer depends on raw-only tables.
  On the reviewed production snapshot the application database decreased from
  18,108,416 bytes (17.27 MiB) to 8,138,752 bytes (7.76 MiB), a 55.06% reduction.
- Speed up development validation by reusing a template web-test database and running
  pytest through `pytest-xdist` by default. The primary local Windows benchmark dropped
  the complete 687-test stage from 59.67 seconds serially to 14.13 seconds with
  automatic worker selection.
- Tune hosted source CI independently from the local default: Ubuntu/Python 3.11 remains
  the full tests/lint/type/build/rules gate, compatibility matrix legs retain runtime/
  data checks, and hosted Windows runs pytest serially. The measured workflow recovered
  from 11:36 to 1:25 after this change.
- Consolidate completed one-off design/audit documents into maintained architecture,
  data-model, rules-semantics, rules-research, backlog, and changelog references, and
  define the public roadmap direction through 1.0.

### Upgrade notes

- Rebuild generated Army databases before deploying 0.6.3. Schema 23 / compatibility
  revision 31 introduces the physical application/raw database split while retaining
  materialized include/Peripheral relationships, selection-safe Unit constraints, and
  reviewed profile-group dependencies; there is no in-place database migration.

## [0.6.2] - 2026-09-21

### Added

- Add deterministic domain-local public slugs for Armies, logical Units, Skills,
  Equipment, and Weapons. Numeric identifiers remain accepted for compatibility and
  provenance, while ambiguous or colliding readable identifiers fail closed.
- Add a loopback-only local deployment test path and explicitly separate server-rebuild
  deployments from transferred, prevalidated database/asset deployments.

### Changed

- Use readable public slugs throughout browser links, catalog/detail APIs, Unit explorer
  filters, maintained catalog identity configuration, and curated Army links where a
  deterministic application identity exists. Stable curated Trait identities and
  source/provenance-only numeric identifiers are unchanged.
- Expose readable slug companions on canonical cross-domain API references while
  retaining the existing numeric fields for compatibility.
- Show the Unit explorer's currently visible unique-unit count alongside the total
  available under the same filters, with an expandable availability breakdown.

### Upgrade notes

- Rebuild generated Army databases before deploying 0.6.2. Schema 17 / compatibility
  revision 25 is intentionally incompatible with older generated `infinity.db` files;
  there is no in-place database migration.

### Fixed

- Resolve grouped Skill, Equipment, and Weapon filters across all source variants,
  including legacy numeric filter URLs, and canonicalize accepted references to their
  readable public slug when available.
- Preserve current-tab settings when persistent settings are disabled, include
  Team Operations-only units on Skill detail pages when that optional category is
  enabled, and keep merged Skill source variants on their application public slug.
- Resolve maintained catalog identity slugs against the complete source metadata
  catalog, including represented-but-currently-unused source entries, and preserve the
  reviewed TinBot Neurocinetics spelling while retaining the upstream typo only as raw
  provenance.
- Preserve the `+dev` browser display version in containerized development/test
  deployments without embedding Git metadata in the image.

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
