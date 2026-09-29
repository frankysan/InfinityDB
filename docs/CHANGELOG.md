# Changelog

All notable user- or operator-relevant changes to InfinityDB are documented here.
Entries describe meaningful release outcomes rather than detailed implementation history.
New or materially revised entries use the project-domain labels defined in
`docs/project-domains.md`; historical release notes are not retroactively relabeled.

## Unreleased

### Changed

- **Data processing + Web frontend:** Make the **Armies** overview more useful for choosing a
  force. Each current and legacy Army now has a short gameplay-focused summary, and the page
  explains how broad main/Generic Army Lists differ from focused Sectorials, including the current
  pattern of richer Sectorial Fireteam charts.
- **Web frontend:** Polish pre-release navigation and Army presentation. Rules cards now place Labels
  before Skill/declaration categories, the desktop sidebar compresses vertical spacing on shorter
  displays, `/armies` uses larger consistently aligned symbols/headings, and Unit Explorer remembers
  whether Advanced filters are open.
- **Web frontend:** Make Unit Explorer Army-availability symbols open the selected Unit with that
  Army profile expanded, including optional Army contexts supplied by a shared Unit Explorer view.
- **Web frontend:** Make Unit Explorer optional-availability filtering reproducible in shared links.
  Mercenaries, Spec-Ops, Team Operations, and Reinforcements now have page-local controls whose
  effective values are written explicitly to the Unit Explorer URL. Browser Settings seed a view
  when no availability state is supplied, while shared URL state takes precedence without changing
  the recipient's saved preferences; contextual copy explains when those states differ.
- **Web frontend:** Make text search on all searchable reference catalog landing pages shareable
  through `?q=` URL state. Opening a catalog search link restores the same narrowed result set, and
  clearing the search returns to the canonical unscoped catalog URL.

### Added

- **Data processing + Web backend + Web frontend:** Publish **General Rules** as the explicit
  fallback rules domain. The initial catalog exposes reviewed basic rules, special Order types,
  Command Token Strategic Use, and Peripheral-type definitions through `/rules`, global search,
  Glossary, semantic relation links, and the shared reference-detail presentation. Fireteam rules,
  Unit-profile help, Attributes, and scoped Game terms keep their existing clearer owners instead
  of being duplicated into the fallback catalog.
- **Data processing + Web backend + Web frontend:** Add canonical **Attributes** and scoped
  **Game terms** as embedded rules vocabularies plus a federated **Glossary** across current
  reference domains. Attribute and terminology concepts participate in global search without gaining
  separate catalog/detail hierarchies; Unit-profile Attributes retain contextual tooltips, browsable
  Glossary concepts continue to open their owning detail pages, and same-name concepts such as
  Marker or Hostile remain distinct by semantic kind rather than being merged by display text.
- **Data processing + Web backend + Web frontend:** Add an **Armies** overview with current Army
  symbols, concise structural descriptions, catalog-status labels, and direct links into Unit
  Explorer with the selected Army already applied. Source `discontinued` metadata now identifies
  playable armies that are **Out of catalog**, Reinforcements inherit that display status from
  their main overview group, and curated Spiral Corps / Foreign Company cards preserve legacy
  identities that are no longer playable in N5.
- **Data processing + Web backend + Web frontend:** Add first-class **Ammunition** and **Labels**
  reference domains. The browser now exposes the eleven N5.3 base Ammunition types and the canonical
  current Label vocabulary through searchable catalog/detail surfaces, while a shared application-
  domain registry establishes presentation capabilities for the broader domain skeleton without
  requiring every typed concept to have its own page.
- **Data processing + Web backend + Web frontend:** Add a rules-backed **Profile notation**
  help layer to Unit details. Reviewed N5 profile concepts explain Attributes, Training/Orders,
  Troop Type, Classification, ISC, Hackable, Peripheral, Equipment/Weapon domains, and
  profile/loadout structure; relevant profile labels and Order/Characteristic symbols link into
  the collapsed help panel without making the profile tables denser.
- **Web backend + Web frontend:** Add global search across Armies, Units, Skills, Equipment,
  Weapons, Ammunition, Traits, Labels, States, Hacking Programs, and Fireteam charts. Results
  identify their domain and open the corresponding player-facing surface; compact navigation keeps
  search available as
  an expandable button on narrow screens.
- **Data processing + Web backend + Web frontend:** Add semantic links and preference-aware
  distance tokens to maintained rules text. Canonical Skill, Equipment, Weapon, Trait, State,
  and Hacking Program references can show viewport-bounded summary previews and navigate to
  their detail pages; touch interaction previews before following, and typed distances follow the
  user's cm/in preference. Reviewed State, Hacking Program, Equipment, Trait, and Skill references now use
  semantic links, while validation prevents new unresolved references or literal gameplay-distance
  debt from being introduced. Generic Trait-name collisions that are confirmed to be ordinary rules
  text are fingerprinted to their exact reviewed passage contexts, so later prose changes reopen
  review instead of being silently exempted while identical derived/test clones remain valid.
  Ambiguous reviewed passages can now carry explicit `review-needed`
  markers with machine-readable reasons; the audit lists them separately and the browser highlights
  them instead of allowing uncertainty to disappear from the migration inventory.
- **Web backend + Web frontend:** Expand the Unit Explorer with Troop Type, Classification,
  Characteristics, AVA, Points, and SWC filters plus an optional extended result mode. Exact
  numeric values and inclusive ranges coexist with the existing Skill, Equipment, and Weapon
  filters; AVA preserves **Total**, SWC preserves source display forms such as bonuses and `-`,
  and range controls expose active/reset state while showing endpoint values only when useful.
  Extended results show profile statlines and Army-specific AVA, keep multi-profile Units visibly
  grouped, and the complete expanded filter/presentation state is bookmarkable through the URL.
- **Web backend + Web frontend:** Present source-specific Unit notes and top-level composite Unit
  options with their applicable Army/source context. Composite options expose costs, miniature
  count, Orders, and linked constituent loadouts without collapsing source variants that differ.

### Changed

- **Data processing:** Complete maintained-text semantic-link candidate migration and the final
  manual source/context review. State aliases are fully reviewed, ordinary State-name collisions are
  passage-fingerprinted, Weapon/Ammunition/Attribute namespaces have explicit zero-residual review
  coverage, and the temporary legacy candidate baseline is retired in favor of direct build-time
  completeness validation. All 30 formerly explicit review markers are resolved: source-backed
  references are typed links, while Direct Template attack-rule uses and Infiltration's descriptive
  `forward deployment` wording remain explicitly reviewed plain text.
- **Web backend + Web frontend:** Make **Labels** bidirectional reference concepts: Label badges
  now preview their canonical definitions, and Label detail pages list the current catalog items
  that use each Label with direct links back to those Skills, Equipment items, States, and other
  supported rules domains. Label detail cards also use the normal reference-surface spacing.
- **Web backend + Web frontend:** Normalize **Fireteams** around the shared domain landing/scoped
  interaction: `/fireteams` now shows the Army selector with the general Fireteam rules summary,
  while selecting an Army replaces that summary with the shareable Army-scoped chart and clearing
  the selection returns to the domain landing state.
- **Web frontend:** Standardize responsive visual behavior across Unit Explorer, catalog,
  reference, Unit-detail, Hacking Program, Weapon, and Fireteam surfaces. Shared surfaces,
  titlebars, Settings controls, and semantic table-column roles now keep compact data compact,
  give primary labels available width, preserve technical columns through scoped horizontal
  scrolling in Developer mode, and provide consistent generated-table accessibility semantics.
- **Web frontend:** Tighten Fireteam and Hacking Program presentation. The current-Army summary
  follows the Fireteam card width, Hacking Program Skill-type badges live in the titlebar,
  Targets lead the Program profile table, and baseline Hacking Devices sit inside the Program
  card immediately before Related rules.
- **Web backend + Web frontend:** Complete structured **Related rules** cross-linking across
  Skills, Equipment, Weapons, Traits, States, and Hacking Programs. Current application
  identities resolve to their canonical detail routes; stale source-only variants remain plain
  text instead of producing dead links.
- **Data processing + Web frontend:** Keep unresolved list/session concepts out of immutable Unit
  semantics: Spec-Ops/Team-Ops option charts remain future list/session configuration, and raw
  loadout `disabled` / `minis` values remain preserved without inventing availability or
  miniature-count meaning. Unit detail keeps selection-relationship diagnostics in Developer
  mode and marks General-profile attributes when Army profiles differ.

### Fixed

- **Web backend + Web frontend:** Restore links from structured Peripheral subtype relationships to
  their General Rules pages, so entries such as **Can control: Peripheral (Cyberplug)** are directly
  navigable.
- **Data processing:** Scope reviewed-plain maintained-text fingerprints to exact passage occurrences
  rather than corpus-wide word counts. Synthetic or derived records may now clone an unchanged
  reviewed passage without invalidating the Trait-review gate, while new or changed wording still
  reopens review.
- **Data processing + Web backend + Web frontend:** Restore canonical Labels on Hacking Program
  details. Supportware, No Roll, Comms Attack, and Negative Feedback (NFB) reuse the current core
  Label vocabulary; Non-Lethal remains correctly modeled as a Trait.
- **Web backend:** Keep compound Unit filters semantically coherent when AVA, Points, or SWC is
  involved: profile/loadout-sensitive criteria must be satisfiable within one compatible
  Army/profile-group/loadout context rather than being assembled from unrelated options on the
  same logical Unit.
- **Web backend:** Merge Skill-detail variants whose distance extras differ only by source
  spelling, such as `7.5` versus `+7.5`, so converted values such as Super-Jump `3"` appear once
  with the combined Unit set while raw source extras remain preserved.
- **Web frontend:** Correct existing narrow/soft-navigation regressions: sidebar active-state
  highlighting updates immediately during client-side navigation, the Unit Explorer introduction
  wraps naturally at tablet widths, and ordinary Fireteam member tables fit narrow screens while
  Developer mode retains scrollable technical columns.

### Upgrade notes

- 0.9.0 requires the release-matched tracked runtime databases. Compatibility revision 34 adds
  the source Order rows used by composite Unit options, and the tracked `rules.db` includes the
  new reviewed reference content. Release preparation must rebuild and commit either runtime
  database whenever its Army or curated-rules inputs changed.
- Normal server upgrades from 0.8.1 onward do **not** rebuild databases in production. Deploy the
  exact `data/generated/infinity.db` and `data/generated/rules.db` shipped by the tagged release;
  raw Army/wiki/PDF inputs remain development/release inputs only.

## [0.8.1] - 2026-09-27

### Changed

- **Web backend + Web frontend:** Present Hacking Program profiles with the same
  declaration-category language and detail-card structure used by Skills. Army's legacy
  `entire order` source value remains preserved in the application data but renders canonically
  as **Long Skill**; the Army profile,
  declaration badges, and curated rules semantics now form one unified Skill-style reference card.
- **Web frontend + Project infrastructure:** Adopt a redistributable bundled browser type
  system: Audiowide for the InfinityDB wordmark, Oxanium for display headings, IBM Plex Sans
  for running/interface text, IBM Plex Sans Condensed for dense tables, and IBM Plex Mono for
  identifiers/diagnostics. Canonical WOFF2 assets and OFL notices are tracked with a reproducible
  TTF-to-WOFF2 preparation helper, while the full upstream TTF download set remains a build input.
- **Web frontend:** Standardize browser typography on a canonical shared font-size scale with one
  browser-relative root size and `rem`-based tiers, so the interface can scale coherently without
  page-local font sizes. Restore introductory text below page titles to the normal body tier and
  make Fireteam rules, headers, and the Level-bonuses table wrap within narrow screens.
- **Acquisition + Data processing + Web backend + Web frontend:** Advance snapshot provenance to
  format version 3 for new acquisitions. Army manifests now record the latest date encoded across
  all contained Army source versions; the sidebar presents that player-useful **Army data last
  changed** date while the later snapshot acquisition time is retained as Developer-mode
  provenance. Version-1 and version-2 snapshot manifests remain readable.
- **Deployment + Project infrastructure:** Make release tags self-contained for runtime
  deployment by tracking deterministic `data/generated/infinity.db` and `rules.db`, retiring
  the transferred-artifact/server-rebuild split, and deploying those exact databases from the
  checked-out release. `army-symbol-build.json` is no longer a production dependency; the
  tracked `symbol-publication.json` now carries the compact Army source snapshot identity used
  to bind the runtime database and processed symbol publication.

### Added

- **Data processing + Deployment:** Add a one-time provenance migration helper for an existing
  published symbol set. It copies the Army archive identity from local terminal symbol-build
  state into the tracked publication manifest without rebuilding SVGs and refreshes the ignored
  local binding for future symbol-pipeline work.

### Upgrade notes

- No Army or rules database rebuild is required solely for 0.8.1. The release starts tracking
  the existing deterministic `infinity.db` and `rules.db` runtime artifacts directly.
- The 0.8.0 installer must not be used directly for the first 0.8.1 server upgrade: it predates
  tracked runtime databases and can continue its old database-rebuild behavior after checking out
  the new tag. Bootstrap `v0.8.1`'s installer with the one-time command in `docs/deployment.md`;
  from 0.8.1 onward the installer hands off to the target release's own installer before checkout.
  Raw Army/wiki/PDF/source-symbol archives and `army-symbol-build.json` remain unnecessary on
  production servers.
- The snapshot-provenance v3 change affects newly acquired Army snapshots. Version-1 and
  version-2 snapshot manifests remain readable, and existing compatible runtime databases can
  derive the Army-data change date from their preserved source-version metadata.
- Browser WOFF2 files and their OFL notices are tracked release content. The upstream TTF
  downloads are regeneration inputs only and do not need to be present on deployed servers.

## [0.8.0] - 2026-09-26

### Changed

- **Data processing + Web backend + Deployment:** Consolidate published symbol identity,
  lookup mappings, and SHA-256 completeness into the tracked
  `data/manifests/symbol-publication.json`. Browser code now receives symbol paths through
  API payloads instead of generated static lookup files, while build, full-asset, cache,
  package, and deployment verification consume the same canonical publication contract.
- **Web frontend:** Keep Unit-detail Army relationship structure behind Developer mode;
  the source-declared faction and Reinforcement parentage links remain available for data
  inspection without adding player-facing detail that experienced players already know.
- **Web frontend:** Rebalance the Fireteam Level bonuses table so the Level column is
  compact and Requirement/Bonuses share the remaining width evenly.
- **Web backend + Web frontend:** Align the shared shell and About page with the connected-reference
  scope, classify rules catalog list/detail pages consistently, preserve active navigation on
  detail routes, synchronize page descriptions, and dispose transient page listeners/requests
  when soft navigation replaces the main content.
- **Acquisition + Web backend + Web frontend:** Move Unit artwork from the detail-page
  title into the General profile header row and preserve source profile-logo provenance through
  the Unit API. Extend generated Unit symbol mappings with profile-specific overrides so secondary
  and Army-contextual artwork resolves to the General profile it belongs to; the current
  processed publication is now fully browser-addressable at 806/806 SVGs.
- **Web frontend:** Keep ordinary Fireteam cards compact in non-Developer mode while
  retaining the full-width chart layout when Developer-only columns are visible.
- **Web frontend:** Refine the Fireteam chart browser: mirror the Unit Explorer Army hierarchy
  in the selector, present the Army source sentinel `256` as an unlimited Fireteam type
  allowance, and move unavailable type limits plus FTO-profile/Notes columns behind Developer
  mode so the ordinary member table stays focused and more compact.
- **Web frontend:** Add a persistent **Fireteams include Wildcards** setting, enabled by
  default. When a chart has one Wildcard set, hide its standalone entry and append those members
  to the bottom of every ordinary Fireteam table with a Wildcard indicator; disabling the setting
  restores the source-style standalone table. Preserve multiple context-specific Wildcard sets as
  separate entries rather than merging distinct source contexts.

### Added

- **Data processing + Web backend + Web frontend:** Promote Hacking Programs to a first-class
  rules/reference surface. Program statlines, targets, declaration types, and baseline Hacking
  Device associations remain generated from structured Army metadata; reviewed N5.3 semantic
  records add effects and typed Skill/State relationships. Program pages cross-link baseline
  Devices, Hacker's structured table links to Program details, and Hacking Device pages expose
  the reverse baseline-Program matrix while Upgrade/source-specific availability remains distinct.
- **Web backend + Web frontend:** Expose Reinforcement Section parent/child Army relationships and
  broader source-declared faction membership on Unit details. Reinforcement links navigate through
  existing Army filters, while declared membership has its own cross-Unit filter so faction IDs
  without a current Army List remain discoverable without being treated as concrete availability.
- **Web backend + Web frontend:** Present reviewed Unit selection constraints and same-Unit
  profile-group dependencies on Unit details. Whole-Unit constraints link their affected Units;
  dependency edges link directly to the relevant profile groups and constrained loadouts while
  preserving still-opaque Army selector parameters without pretending to validate complete lists.
- **Web backend + Web frontend:** Present Profile, Loadout, and shared Unit-option include
  relationships on Unit detail surfaces. Included canonical Loadouts retain quantity and Army
  context and link to their rendered Loadout rows, while shared Unit options expose only their
  include relationship pending the broader composite-option review.
- **Web backend + Web frontend:** Present canonical Peripheral attachments and Controller access
  pools on Unit profile/loadout surfaces. Controller access targets now link directly to their Unit
  details, while Unit-backed Peripheral targets expose the reverse Controller occurrences with Army
  and profile/loadout context without implying fixed ownership.
- **Data processing + Web backend + Web frontend:** Add curated N5 Fireteam general rules and
  cumulative Fireteam Level bonuses to `rules.db`, expose them as an optional reference payload
  alongside the canonical Army chart, and generate the `/fireteams` quick reference from those
  facts. Historical `Linkable` and community `pure Fireteam` terminology remains discoverable
  with explicit provenance instead of being presented as current N5 terminology.
- **Web backend + Web frontend:** Add first-class Army-scoped Fireteam browsing on
  `/fireteams` and `/api/fireteams`, backed only by the canonical schema-25 Fireteam projection.
  The browser presents authoritative chart limits, membership requirements, FTO-eligible
  loadouts, Wildcards, equivalence labels, notes, source provenance, and links to resolved Units
  without reading the raw normalized Fireteam tables at runtime.
- **Data processing:** Materialize the first-class Fireteam application projection for
  0.8.0: select one provenance-bound source chart per application Army, preserve chart
  limits/types/members/notes, resolve members to logical Units, link FTO rows to canonical
  Army-local loadouts, retain Wildcard/equivalence context, and keep Reinforcement parent
  limits separate through the existing application Army graph. This advances the Army
  application database to schema 25 / compatibility revision 33, so generated databases
  from 0.7.x must be rebuilt before running or deploying 0.8.0.
- **Deployment:** Add a narrow, loopback-by-default Caddy metrics listener that can be bound to a
  specific trusted LAN interface without publishing the application port or `/internal/*`; persist
  the bind/port in deployment configuration and add a dependency-free workstation CLI that turns
  the aggregate Prometheus metrics into a compact operator report.

### Upgrade notes

- Rebuild the generated Army databases before deploying 0.8.0. Schema 25 /
  compatibility revision 33 adds the canonical Fireteam projection required by the
  0.8 browser/API.
- Rebuild `rules.db` from the tracked curated collections so the deployment includes
  the reviewed Fireteam and Hacking Program reference data used by the new surfaces.
- Deploy the application and tracked processed SVG publication from the same release
  revision. The 0.8 Unit-symbol mapping includes profile-specific overrides and the
  complete tracked publication is browser-addressable.
- The new Caddy metrics listener is optional and loopback-only by default. Configure
  its trusted bind address/port only when the workstation reporting workflow is needed.

## [0.7.2] - 2026-09-26

### Changed

- **Data processing + Project infrastructure:** Reduce repeated SQLite physical-file
  finalization in export-heavy semantic tests while keeping release/CLI exports canonical
  by default. On the primary Windows development machine, the 182-test database/rules
  xdist comparison improved from 19.45 seconds to 17.56 seconds wall time (9.7%), with
  all tests passing in both modes.
- **Deployment + Web backend:** Replace routine Gunicorn access logging with shared,
  privacy-preserving aggregate request metrics. Production workers expose bounded normalized
  route/status counters, latency and response-size histograms, active-request counts, and build
  identity on a Docker-internal metrics endpoint; Caddy blocks the internal surface publicly,
  while Gunicorn error logging remains available for operational diagnostics.
- **Web backend + Web frontend:** Improve 0.7.2 presentation defaults and consistency:
  Settings is collapsible on the
  desktop sidebar, first-use preferences default to inches and all optional Unit types,
  Unit troop-type abbreviations expand to their rules-facing names, Unit health attributes
  use `VITA` or `STR` from canonical profile semantics, detail metadata is Developer-mode
  only, and small labels/table/detail text use a more legible, less fragmented type scale.
- **Web backend + Web frontend:** Improve catalog and rules presentation with wider
  Equipment/Weapon/Trait name columns,
  aligned linked characteristic symbols, and deterministic semantic relation ordering.
- **Web backend + Web frontend:** Harden the browser page shell so executable scripts
  remain same-origin external
  modules under an explicit Content Security Policy, without permitting inline scripts.

### Upgrade notes

- Redeploy the application image for 0.7.2. The production Gunicorn command, internal
  health/metrics endpoints, and Caddy internal-route blocking are part of the release and
  must move together. Routine Gunicorn access logging is intentionally disabled.
- No Army or rules database schema/compatibility rebuild is required solely for 0.7.2;
  existing 0.7.1-compatible generated databases remain usable. Rebuilding with 0.7.2 is
  still valid and preserves the canonical deterministic SQLite export contract.

## [0.7.1] - 2026-09-25

### Changed

- Make generated build/report/archive outputs portable at the byte level across supported
  operating systems: canonical text uses UTF-8/LF, validation ordering is stable, work
  archives normalize Git-managed text bytes, and CI compares representative artifact
  SHA-256 identities across Windows, Linux, and macOS.
- Canonicalize generated SQLite artifacts after build so database page layout and
  transaction-history header fields do not vary between supported host platforms.
- Present declaration-bearing Equipment such as MediKit, GizmoKit, and Deactivator with the
  same action-card/declaration-category language used for Skills while preserving their
  canonical Equipment identity.

### Fixed

- Preserve the checksum-bound symbol inventory and browser-map files byte-for-byte in Git
  so Windows line-ending conversion cannot invalidate a promoted publication manifest.
- Model Paramedic as explicitly equipping its user with MediKit rather than generically
  reusing MediKit effects, and keep MediKit/GizmoKit relation targets routed to Equipment.
- Fingerprint immutable frontend assets by their static content as well as the application
  version, preventing a late frontend rebuild under the same semantic version from leaving
  browsers on an obsolete cached module graph.

### Upgrade notes

- Rebuild `rules.db` from the tracked curated rules before deployment. Curated rules format
  v21 adds the `equips-with` relation used for Paramedic → MediKit; the `rules.db` schema
  remains version 7 / compatibility revision 8.
- No Army database schema or compatibility rebuild is required solely for 0.7.1. Existing
  runtime Army data remains compatible, while newly generated artifacts use the canonical
  cross-platform output rules.

## [0.7.0] - 2026-09-25

### Added

- Complete the 0.7.0 rules/context enrichment gate across the public Skill, Equipment,
  Trait, State, and supporting rules catalogs. The maintained interaction review now
  covers all 182 primary release identities plus supporting identities, while genuinely
  unresolved cross-domain or runtime-scoped interactions remain explicit future work.
- Add the complete current State reference, including the deliberate IMP-1/IMP-2 split,
  and expose reviewed typed relationships for State entry, cancellation, recovery,
  restrictions, modifiers, and effect reuse with derived reverse navigation.
- Expand the rules-backed Skill and Equipment reference with reviewed N5.3 Common/Special
  Skills and Equipment semantics, including recovery, deployment, mobility, morale,
  survivability, reaction/combat, Peripheral, and exact-variant interactions.
- Surface Infinity Army's structured Hacking Program, Martial Arts, Booty, and
  MetaChemistry reference data on Skill detail pages while preserving applicability,
  declaration categories, profile fields, conditional/random outcomes, and provenance.
- Normalize Cube and Cube 2.0 profile-symbol occurrences into canonical Equipment
  identities without inventing textual Army rows, so their usage is available through
  Equipment browsing, filtering, Unit references, and symbol navigation.
- Add deterministic enrichment/presentation audits and the long-lived interaction ledger
  so release-target coverage, source freshness, unresolved targets, supporting identities,
  and explicitly deferred relationships fail closed or remain visibly classified.

### Changed

- Make rules presentation semantics backend-owned: curated summaries, labels, declaration
  categories, exact-source variants, and direction-aware related-rule metadata now flow
  through the maintained rules/application contracts instead of parallel browser logic.
- Improve catalog readability with multi-category Skill types, explicit Requirements /
  Effects / Restrictions, clearer related-rule grouping, exact variant labels, and stable
  links from rules-only relation targets to their detail pages.
- Present Army weapon-profile `damage` as N5 Possibility of Survival (`PS`) while preserving
  the upstream field name in stored/application data for compatibility and provenance.
- Rewrite the landing/About framing around InfinityDB's current rules-enriched scope and
  roadmap, including prominent open-source/non-commercial/non-affiliation wording and the
  explicit Corvus Belli graphical-asset permission.
- Track the validated processed Corvus Belli SVG publication and `symbol-inventory.json` as
  release content. Required source/package/container validation now checks the tracked
  publication directly; transferred-artifact deployment sends only generated databases plus
  the terminal symbol manifest while the matching Git revision supplies tracked symbols. Raw
  Army/wiki/PDF/source-symbol archives remain local provenance inputs, and the checksum-pinned
  external-bundle workflow remains supplementary.
- Complete the post-vetting presentation consistency pass: normalize maintained rules
  terminology, keep occurrence-only Army extras on their source rows, preserve source and
  applicability context, and improve narrow-layout catalog/detail presentation.

### Fixed

- Keep very narrow Unit details readable: long titles may wrap within the viewport and
  General-profile labels stack above their value areas at 400 px and below instead of
  compressing the Attribute statline into overlapping columns.

### Upgrade notes

- Rebuild the generated Army databases before deploying 0.7.0. Schema 24 / compatibility
  revision 32 adds the structured Hacking Program, Martial Arts, Booty, and MetaChemistry
  application projections used by the enriched Skill surfaces.
- Rebuild `rules.db` from the tracked curated rules collections so the deployed reference
  includes the complete 0.7.0 Skill, Equipment, Trait, State, and interaction enrichment.
- The processed Corvus Belli SVG publication and `symbol-inventory.json` are now tracked
  release content. Raw Army/wiki/PDF/source-symbol archives remain local build/provenance
  inputs; guarded production deployment still requires the local terminal symbol-build
  manifest to bind the runtime Army database to the tracked publication.

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
