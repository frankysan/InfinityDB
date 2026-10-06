# Changelog

All notable user- or operator-relevant changes to InfinityDB are documented here.
Each release begins with a concise **Player summary** containing only changes visible or useful to
players; the remaining sections preserve fuller user/operator release detail. Entries describe
meaningful release outcomes rather than detailed implementation history. New or materially revised
entries use the project-domain labels defined in `docs/project-domains.md`; historical release notes
are not retroactively relabeled.

## Unreleased

### Player summary

- Choose System, Light, or Dark themes, with improved contrast and readability across the interface.
- Use the new **What's changed** page and expanded privacy information to see visible updates and
  understand what InfinityDB stores.
- Unit, Army, Fireteam, Skill-reference, and symbol presentation received navigation, filtering,
  glossary-help, artwork, and small-screen fixes.

### Added

- **Data processing + Web frontend:** Add **FTO (Fireteam Option)** to the Glossary, explaining that
  FTO is an option-name identifier rather than a standalone rule and that Fireteam charts can
  require FTO or a specific FTO variant such as FTO-2.

- **Deployment + Project infrastructure:** Add operator-side retained metrics history reporting and
  comparison by week/version/snapshot, including request/status/error summaries, normalized-route
  activity, cumulative latency/response-size histograms, bounded percentile estimates, and JSON output
  without introducing another network endpoint or request-level persistence.

- **Deployment + Project infrastructure:** Run retained aggregate metrics in a dedicated
  immutable-root `metrics-history` container with one bounded writable SQLite volume, bracket
  application updates with non-blocking closing/opening scrapes, preserve isolated history across
  normal local-test restarts, and provide an explicit local `--purge` clean-slate path.

- **Deployment + Project infrastructure:** Add a bounded, version-aware metrics-history collector
  engine that converts volatile request counters into generation-safe weekly SQLite summaries,
  retains only one rolling scrape state, and automatically enforces age and database-size limits
  without storing user/request identity data.

- **Deployment + Project infrastructure:** Expose live metrics-generation start and latest completed-request timestamps, and show the generation observation span in the operator metrics report so restarts and counter lifetimes are explicit before retained history is introduced.

- **Deployment + Project infrastructure:** Add a privacy-preserving operational alert evaluator for sustained CPU, memory/OOM/restart pressure, filesystem space/inodes, 5xx response deltas, and health failures, with configurable thresholds and monitoring-friendly exit codes.

- **Web frontend + Project infrastructure:** Publish a user-facing privacy policy in the README and
  About page explaining InfinityDB's no-profile/no-visitor-tracking stance, aggregate-only
  operational metrics, session-only browser settings by default, opt-in preference cookies, and
  shareable URL state. The cookie-consent dialog links directly to the policy.
- **Deployment + Project infrastructure:** Add bounded sanitized deployment diagnostics for the
  existing Caddy/Gunicorn Docker log streams, retaining warning/error-class summaries and grouped
  samples while redacting request targets and identity-like values instead of archiving raw logs.
- **Deployment + Project infrastructure:** Add privacy-preserving Linux host/container resource
  capture for deployment capacity evidence, including CPU, memory/swap, filesystem space/inodes,
  available disk-I/O, network rates, per-container Docker utilization, and restart/OOM events over
  the same interval as an optionally wrapped capacity-test command.
- **Deployment + Project infrastructure:** Add a repeatable HTTP capacity-test scenario for deployed
  InfinityDB stacks, covering representative Unit browsing, search, detail, and API traffic with
  warm-cache steady and burst phases plus retained p50/p95/p99, throughput, error, and response-size
  evidence tied to the target version and snapshot.
- **Deployment + Project infrastructure:** Add `infinity-db database-health` for operational
  validation of published Army databases, reporting schema/compatibility revisions and validation
  timing with optional application/raw export-pair verification and machine-readable JSON output.
- **Web frontend:** Add a project favicon derived from the InfinityDB logo, simplified for clear
  recognition at small browser-tab sizes and high contrast in both light and dark browser chrome,
  with SVG as the scalable primary icon plus a 32 px PNG fallback and Apple touch icon.
- **Web frontend:** Add System, Light, and Dark theme selection in Settings. System follows the
  operating-system color preference by default, explicit choices can be remembered with existing
  Settings persistence, and the selected theme is applied before first paint.
- **Web frontend + Project infrastructure:** Add a What's changed page that leads with player-facing
  summaries and keeps the complete Added/Changed/Fixed/Upgrade notes in expandable detail, all
  published directly from the project's canonical changelog.
- **Acquisition:** Add Human Sphere as an English-only wiki research source using the existing
  deterministic snapshot/history pipeline. Human Sphere acquisitions use their own archive
  identity, normalize bare/`www` host aliases, enumerate MediaWiki content pages before rendered
  link discovery to include orphaned main-namespace pages, store rendered pages with a
  collision-safe `.html` suffix, pace requests conservatively, and reuse already-downloaded assets
  when resuming incomplete work. Snapshot completeness is anchored to the API-enumerated
  main-namespace inventory: failed enumerated pages remain fatal, while Talk/service URLs and stale
  link-discovered HTTP 404s are retained as ignored diagnostics instead of blocking publication.

### Changed

- **Web frontend:** Rewrite the Armies overview framing around playable forces and roster status,
  removing dataset-oriented wording from the player view.
- **Web frontend:** Remove remaining source-review qualifiers and imported-table wording from
  Hacking Program and Fireteam copy, including Hacking Program access labels and empty Fireteam
  member states, keeping the player view focused on rules content and gameplay meaning.
- **Web frontend:** Rename Unit-detail **Source notes** to **Unit notes**, keeping the
  Army-specific applicability visible while removing source-processing terminology from the player
  view.
- **Web frontend:** Present unresolved maintained rules text as **Needs verification** with an
  **uncertain** marker and player-readable reasons, while keeping the underlying review marker
  available to the curation workflow.
- **Web frontend:** Rewrite Equipment, Weapons, and Fireteams introductions around the rules
  information players can browse, removing Army snapshot and source-authority framing from normal
  page copy.
- **Web backend + Web frontend:** Rewrite empty, loading, and error states, including Army, Unit,
  and rules-reference API failures, to describe the player-visible situation directly instead of
  exposing database, snapshot, source-data, or catalog terminology.
- **Web frontend:** Rewrite the About page and Home/About introductory framing around what InfinityDB
  helps players explore, how related rules information is connected, and how uncertainty is
  presented, replacing data-pipeline, generic data framing, and internal release-planning language
  with player-relevant reference language and project goals.
- **Web frontend:** Rewrite Labels, General Rules, and Glossary framing around the rules information
  players can look up, removing internal taxonomy and data-model terminology from those surfaces.
- **Web frontend:** Replace database/domain/indexing/catalog-oriented page framing with InfinityDB
  and player-reference language across navigation breadcrumbs and sidebar framing, the landing page,
  Unit Explorer and Unit details, global Search, rules-reference lists, rules-reference accessibility
  captions, and the What's changed release-history framing.
- **Data processing:** Bind each generated Army application/raw database pair to one deterministic
  full-export fingerprint and make application-database replacement the publication commit point.
  Interrupted paired publication now fails closed for raw-dependent audits and recovers by rerunning
  the export without putting normal serving onto an unvalidated application database.
- **Web backend + Web frontend:** Normalize Army Fireteam limit sentinels into explicit application
  semantics before they reach the browser, and include curated legacy Armies in global search with
  links to the Armies overview.
- **Data processing + Web backend + Web frontend:** Rework symbol publication around semantic
  ownership instead of Army source naming. Peripheral-only artwork now publishes under a dedicated
  main-Army namespace, mixed-role profile names remain Unit-owned, distinct contextual variants are
  preserved, and byte-identical artwork prefers ordinary Unit/Peripheral identities over
  Reinforcement-only aliases for canonical public naming.
- **Data processing + Web frontend:** Refresh the tracked processed SVG corpus with maintained
  reconstructions and cleanup across affected faction, Order, Characteristic, Peripheral, and Unit
  artwork, including corrected gradients/geometry and removal of hidden or redundant source
  structure where appropriate.

### Fixed

- **Web frontend:** Make Unit Profile row headers follow the same reference behavior as Attribute labels: profile concepts now show maintained tooltips and open their Glossary entries, with separate Skills, Equipment, and Weapons concepts, and the redundant Profile notation introduction is removed.
- **Web frontend:** Tune Light and Dark semantic theme colors against an executable contrast audit
  for compact/muted text, links, focus cues, status and range values, tables, dialogs, menus, and
  related badges while keeping faction accents supplementary to textual identity.
- **Web frontend:** Keep Fireteam Member/Requirements columns aligned with a compact, stable split
  across viewport widths, and reserve more room for cm-mode MOV values so profile statlines do not
  crowd adjacent attributes.
- **Web frontend:** Army results that open the Armies overview now target, scroll to, and highlight the matching Army card instead of dropping users at the top of the page.
- **Web backend + Web frontend:** Clarify Unit pages when optional-unit Settings hide every profile,
  remove redundant one-Unit source Characteristics from the Unit Explorer picker, and treat Army's
  combined Headquarters/Mechanized classification as matching both component filters.
- **Deployment:** Include the published Peripheral SVG namespace in wheel/container package data,
  and pin package-data coverage against the tracked symbol-publication manifest so a complete source
  tree cannot produce an incomplete release image.
- **Web backend:** Reject unknown or duplicate semantic query parameters on Fireteam and Unit-detail
  APIs instead of silently ignoring malformed requests, while retaining the Developer-mode cache-bust
  parameter.
- **Web frontend:** Display stationary MOV profiles with an em dash (`—`) instead of treating
  Army's `-1/-1` sentinel as a negative distance, while keeping Army/rules distance conversion
  consistent across Unit profiles, Skill parameters, maintained rules text, and Weapon ranges.
- **Data processing:** Revalidate Armed Turret against the current N5 v5.3 core rules and
  replace its stale N5.2 citation with the current primary source while preserving the documented
  source conflict in its deployable-profile Silhouette.
- **Acquisition:** Apply a local symbol override to every same-category Army asset that is
  byte-identical upstream, so correcting one duplicated Army symbol no longer leaves equivalent
  Unit/profile occurrences on the original artwork. Conflicting overrides for the same upstream
  symbol now fail explicitly instead of producing ambiguous output.
- **Data processing + Web backend + Web frontend:** Resolve Unit and General-profile symbols as
  semantic assignments instead of blindly following each Army profile-logo occurrence. General
  profiles now have one effective symbol with Unit fallback, source-primary artwork remains
  available when it belongs to a distinct General profile after Unit identity consolidation, and
  high-confidence cross-Unit consensus repairs repeated upstream assignments such as Crabbots on
  Cutters and Dragões without discarding the original Army logo URLs used as provenance.

## [0.9.1] - 2026-09-30

### Player summary

- Shared Unit Explorer links now show clearly when optional-unit choices differ from your saved
  Settings without overwriting those Settings.
- Order references, Strategos, Multispectral Visor, and dense Army-availability displays are clearer
  and more complete.

### Changed

- **Web frontend:** Replace the Unit Explorer's duplicate optional-unit controls with a compact
  status showing whether the URL-owned view matches Settings and, when it does not, which optional
  unit categories differ. Clearing filters returns the view to the current Settings baseline, while
  shared views remain reproducible without overwriting the recipient's saved Settings.

### Fixed

- **Data processing + Web backend + Web frontend:** Publish Regular Order and Irregular Order as
  General Rules alongside Special Lieutenant Order and Tactical Order, so all four Order types
  cross-link through the `order-type` category. Impetuous remains a Skill and is surfaced as a
  related reference rather than being misclassified as an Order.
- **Data processing + Web frontend:** Publish the concrete Strategos L1/L2 effects from the core
  rules and surface gameplay-bearing source variants before collapsed Unit-usage sections while
  keeping identity-only variants out of the player-facing rule view.
- **Data processing + Web frontend:** Present level-based reference data such as Multispectral
  Visor in a compact level-effects table between the family rules and Unit-usage sections.
- **Web frontend:** Keep Army-availability symbols bounded and horizontally wrapping in both the
  Unit Explorer and reverse Unit-usage tables, preventing dense Army sets from clipping or
  collapsing into one-symbol-wide columns.

### Upgrade notes

- Deploy the release-matched tracked `data/generated/rules.db` shipped with 0.9.1; it contains the
  new Order references and reviewed Strategos/Multispectral Visor level content.
- No Army database rebuild is required solely for 0.9.1.

## [0.9.0] - 2026-09-29

### Player summary

- Browse new **Ammunition**, **Labels**, and **General Rules** references, use the federated
  **Glossary**, and search across the whole player-facing reference.
- Filter Units by more profile characteristics, inspect extended profile data, and browse a new
  Armies overview with current and legacy forces.
- Rules text, Fireteams, Army context, and shareable browser state are more deeply linked and more
  consistent across desktop and narrow screens.

### Added

- **Data processing + Web backend + Web frontend:** Expand the rules/reference surface with
  first-class **Ammunition**, **Labels**, and **General Rules** catalogs. General Rules is the
  fallback home for reviewed concepts without a clearer domain owner, while Fireteam rules,
  profile help, Attributes, and scoped terminology stay with their more specific surfaces.
- **Data processing + Web backend + Web frontend:** Add canonical **Attributes** and scoped
  **Game terms** as embedded vocabularies plus a federated **Glossary** across the reference
  domains. Same-name concepts remain distinct by semantic kind, and browsable entries link back
  to their owning detail surfaces instead of creating duplicate catalogs.
- **Web backend + Web frontend:** Add global search across the player-facing reference, including
  Armies, Units, rules catalogs, Hacking Programs, and Fireteam charts, with results routed to the
  corresponding application surface.
- **Data processing + Web backend + Web frontend:** Add rules-backed **Profile notation** help to
  Unit details for Attributes, Orders, Troop Type, Classification, ISC, Hackable, Peripheral,
  Equipment/Weapon domains, and profile/loadout structure without making the profile tables denser.
- **Web backend + Web frontend:** Expand Unit Explorer with Troop Type, Classification,
  Characteristics, AVA, Points, and SWC filters plus an optional extended result mode showing
  profile statlines and Army-specific AVA. The complete filter and presentation state is shareable.
- **Data processing + Web backend + Web frontend:** Add an **Armies** overview for current and
  legacy forces with symbols, catalog status, gameplay-focused summaries, and direct Unit Explorer
  links. The page also explains the practical distinction between Generic Army Lists and
  Sectorials and identifies playable forces that are out of catalog.
- **Web backend + Web frontend:** Present source-specific Unit notes and composite Unit options with
  their applicable Army/source context, including costs, miniature count, Orders, and linked
  constituent loadouts where that structure is available.

### Changed

- **Data processing + Web backend + Web frontend:** Make maintained rules prose navigable through
  semantic references. Reviewed Skill, Equipment, Weapon, Trait, State, and Hacking Program links
  can preview definitions and open canonical detail pages, Label badges and Related rules links
  open their canonical references, and typed gameplay distances follow the user's cm/in preference.
  The maintained corpus is now fully reviewed with no unresolved semantic-link migration debt.
- **Web backend + Web frontend:** Make shared browser state compact and reproducible across Unit
  Explorer, Unit Army targeting, Fireteams, catalog search, global search, and Glossary search.
  Optional Unit availability is carried with shared Unit views without overwriting the recipient's
  saved Settings, Army-availability symbols open Units in the selected Army context, and existing
  explicit-parameter links remain compatible.
- **Web backend + Web frontend:** Normalize Fireteams around the shared landing/scoped interaction:
  the unscoped page shows the Army selector and general rules, while selecting an Army switches to
  the shareable Army chart. Wildcard handling and ordinary-player layouts stay compact while
  Developer mode retains the additional source detail.
- **Web frontend:** Standardize responsive behavior across Unit Explorer, catalogs, reference
  details, Hacking Programs, Weapons, Fireteams, navigation, and Settings. Army symbols/headings,
  rules-card badge ordering, narrow-screen tables, short-viewport sidebar spacing, and Advanced
  filter disclosure state now follow the shared presentation rules.

### Fixed

- **Web backend:** Keep compound Unit filters coherent when AVA, Points, or SWC is involved, so
  profile/loadout-sensitive criteria must be satisfied within one compatible context rather than
  assembled from unrelated options on the same Unit.
- **Data processing + Web backend + Web frontend:** Restore missing canonical rule links and labels,
  including Peripheral subtype links into General Rules and Supportware, No Roll, Comms Attack,
  and Negative Feedback (NFB) on Hacking Programs.
- **Web backend:** Merge Skill-detail variants whose distance extras differ only by source spelling,
  preventing duplicate converted values while preserving the original source forms.
- **Web frontend:** Correct narrow-screen and soft-navigation regressions affecting active
  navigation, Unit Explorer introductory wrapping, and Fireteam member tables.

### Upgrade notes

- Deploy the release-matched tracked `data/generated/infinity.db` and
  `data/generated/rules.db` shipped with 0.9.0. They include the additional Unit-option source
  data and reviewed rules/reference content required by the release.
- Normal server upgrades from 0.8.1 onward do **not** rebuild databases in production. Raw
  Army/wiki/PDF inputs remain development and release-preparation inputs only.

## [0.8.1] - 2026-09-27

### Player summary

- Hacking Programs now use the same declaration language and detail-card style as Skills.
- Typography is more consistent across the site, and the sidebar now shows when the contained Army
  data last changed rather than the snapshot download time.

### Changed

- **Web backend + Web frontend:** Present Hacking Programs with the same declaration language and
  detail-card structure as Skills, including canonical **Long Skill** presentation for Army's
  legacy `entire order` source value.
- **Web frontend + Project infrastructure:** Adopt bundled redistributable browser fonts and a
  shared typography scale so headings, body text, compact tables, and diagnostic text remain
  consistent and responsive across the application.
- **Acquisition + Data processing + Web backend + Web frontend:** Distinguish when the contained
  Army data last changed from when a snapshot was downloaded. The player-facing sidebar now shows
  the Army-data change date while acquisition time remains Developer-mode provenance, and older
  snapshot manifests remain readable.
- **Deployment + Project infrastructure:** Make release tags self-contained for deployment by
  tracking the exact runtime Army/rules databases and the publication metadata that binds them to
  the processed symbol set. Production no longer needs raw source archives or symbol-build state.

### Upgrade notes

- No Army or rules database rebuild is required solely for 0.8.1; deploy the tracked runtime
  databases shipped with the release.
- The first upgrade from 0.8.0 must bootstrap the 0.8.1 installer as documented in
  `docs/deployment.md`. From 0.8.1 onward, updates hand off to the target release's installer before
  checkout-side effects occur.
- Snapshot manifest versions 1 and 2 remain supported, and production servers do not need the raw
  Army/wiki/PDF/source-symbol archives used during release preparation.

## [0.8.0] - 2026-09-26

### Player summary

- Browse first-class **Hacking Programs** and Army-scoped **Fireteams** with rules, limits,
  Wildcards, FTO options, and Unit links.
- Unit details expose more useful relationships and selection context, while profile artwork and
  Fireteam presentation are more accurate and compact.

### Added

- **Data processing + Web backend + Web frontend:** Promote Hacking Programs to a first-class
  reference surface with program statlines, targets, declaration types, effects, related rules,
  baseline Hacking Device associations, and reverse links from Hacking Devices.
- **Data processing + Web backend + Web frontend:** Add first-class Army-scoped Fireteam browsing
  with current chart limits, membership requirements, FTO-eligible loadouts, Wildcards,
  equivalence labels, notes, Unit links, and reviewed general Fireteam rules/Level bonuses.
- **Web backend + Web frontend:** Expand Unit details with Reinforcement relationships,
  source-declared faction membership, reviewed selection constraints, profile/loadout includes,
  same-Unit dependencies, and canonical Peripheral/Controller relationships while keeping
  source-oriented diagnostics in Developer mode where appropriate.
- **Deployment:** Add an optional trusted-LAN listener and workstation reporting path for the
  aggregate request metrics introduced in 0.7.2, without exposing the application's internal
  metrics endpoint publicly.

### Changed

- **Acquisition + Web backend + Web frontend:** Improve Unit artwork placement and profile-specific
  symbol resolution so General profiles show the correct Army/contextual artwork and the complete
  processed symbol publication is addressable by the browser.
- **Web backend + Web frontend:** Refine the shared shell, reference navigation, and Fireteam
  presentation, including compact ordinary-player cards, a Unit-Explorer-style Army hierarchy,
  clearer unlimited type allowances, and a persistent setting that folds a single Wildcard set
  into each ordinary Fireteam table.
- **Data processing + Web backend + Deployment:** Use one tracked symbol-publication contract for
  browser lookup, completeness validation, packaging, and deployment instead of separate generated
  lookup inventories.

### Upgrade notes

- Rebuild the generated Army database and `rules.db` before deploying 0.8.0 so the Fireteam and
  Hacking Program application/reference data is present.
- Deploy the application, rebuilt databases, and processed SVG publication from the same release
  revision.
- The trusted-LAN metrics listener is optional; configure its bind address only when remote
  workstation reporting is needed.

## [0.7.2] - 2026-09-26

### Player summary

- Settings and reference pages are clearer by default: inches and all optional Unit types are
  enabled initially, troop types use rules-facing names, and Unit health is shown as **VITA** or
  **STR**.
- Desktop Settings can collapse and the shared typography/layout has been refined for easier
  reading.

### Changed

- **Deployment + Web backend:** Replace routine per-request production access logging with bounded,
  privacy-preserving aggregate request metrics while retaining Gunicorn error logging for
  diagnostics.
- **Web backend + Web frontend:** Improve presentation defaults and readability: Settings can
  collapse in the desktop sidebar, first-use preferences use inches and include all optional Unit
  types, troop types use rules-facing names, Unit health shows `VITA` or `STR` from profile
  semantics, detail metadata is Developer-mode only, and catalog/rules layouts use a clearer
  shared type scale.
- **Web backend + Web frontend:** Apply an explicit same-origin Content Security Policy so browser
  scripts remain external modules without permitting inline executable code.

### Upgrade notes

- Redeploy the application image for 0.7.2 so the production web/metrics configuration moves as one
  release.
- No Army or rules database rebuild is required solely for 0.7.2; 0.7.1-compatible generated
  databases remain usable.

## [0.7.1] - 2026-09-25

### Player summary

- Equipment that declares actions, such as MediKit, GizmoKit, and Deactivator, is now presented with
  the same action-card language as Skills.
- Paramedic correctly links to MediKit, and rebuilt browser assets no longer risk leaving stale
  reference content behind.

### Changed

- Make generated archives, reports, symbol metadata, and SQLite databases reproducible at the byte
  level across supported operating systems.
- Present declaration-bearing Equipment such as MediKit, GizmoKit, and Deactivator with the same
  action-card and declaration-category language used for Skills.

### Fixed

- Model Paramedic as equipping its user with MediKit and keep MediKit/GizmoKit relationships routed
  to the Equipment reference.
- Prevent immutable frontend assets from remaining stale when browser resources are rebuilt under
  the same application version.
- Prevent platform line-ending conversion from invalidating checksum-bound symbol publication
  metadata.

### Upgrade notes

- Rebuild `rules.db` before deployment so the Paramedic → MediKit equipment relationship is
  available.
- No Army database rebuild is required solely for 0.7.1.

## [0.7.0] - 2026-09-25

### Player summary

- Skills, Equipment, Traits, and States now have a substantially richer rules-backed reference,
  including the complete current State catalog.
- Skill details expose structured Hacking Program, Martial Arts, Booty, and MetaChemistry data, and
  Cube/Cube 2.0 usage is linked through Equipment.
- Very narrow Unit-detail layouts are easier to read.

### Added

- Complete the rules-backed Skill, Equipment, Trait, and State reference for the 0.7 milestone,
  including reviewed N5.3 relationships for requirements, effects, restrictions, recovery,
  deployment, mobility, morale, combat, and Peripheral interactions.
- Add the complete current State reference, including distinct IMP-1 and IMP-2 concepts with
  reviewed entry, cancellation, recovery, restriction, modifier, and reverse relationships.
- Surface Army's structured Hacking Program, Martial Arts, Booty, and MetaChemistry data on Skill
  details, and make Cube/Cube 2.0 profile-symbol usage available through the canonical Equipment
  reference.

### Changed

- Make rules presentation come from the maintained application/rules data rather than parallel
  browser assumptions, with clearer Skill categories, Requirements/Effects/Restrictions, related
  rules, exact variants, and source/applicability context.
- Present Army weapon-profile `damage` as N5 Possibility of Survival (`PS`) while preserving the
  upstream field in stored data.
- Update the landing/About presentation for the rules-enriched scope, roadmap, open-source and
  non-commercial status, non-affiliation, and Corvus Belli graphical-asset permission.
- Track the validated processed Corvus Belli SVG publication as release content while keeping raw
  Army/wiki/PDF/source-symbol archives as local provenance inputs.

### Fixed

- Keep very narrow Unit details readable by allowing long titles to wrap and stacking General
  profile labels above their values instead of compressing the Attribute statline.

### Upgrade notes

- Rebuild the generated Army database before deploying 0.7.0 so the structured Hacking Program,
  Martial Arts, Booty, and MetaChemistry data is available.
- Rebuild `rules.db` so the complete 0.7 Skill, Equipment, Trait, State, and interaction reference
  is deployed.
- Deploy the tracked processed SVG publication with the matching release revision; raw source
  archives remain local build/provenance inputs.

## [0.6.3] - 2026-09-22

### Player summary

- Doctor, Engineer, Cyberplug, Peripheral, and Controller relationships are represented more
  explicitly in the reference.
- Unit/Profile/Loadout dependencies and reviewed selection constraints are more complete, improving
  how related options are explained.

### Added

- Add reviewed N5.3 Doctor, Engineer, Cyberplug, Peripheral, and Peripheral-type reference data,
  including Controller eligibility and Connected/Autonomous profile-mode semantics.
- Add canonical Peripheral attachments, Controller access pools, Unit/Profile/Loadout include
  relationships, reviewed Unit selection constraints, and same-Unit profile-group dependencies
  without guessing unresolved Army selector semantics.

### Changed

- Split generated Army storage into a self-contained runtime `infinity.db` and a separate
  `infinity.raw.db` containing the complete normalized source representation. The deployed
  application database becomes substantially smaller while source/audit detail remains available
  to development tooling.

### Upgrade notes

- Rebuild generated Army databases before deploying 0.6.3; there is no in-place migration from the
  earlier combined storage layout.

## [0.6.2] - 2026-09-21

### Player summary

- Browser links now use readable names instead of numeric IDs wherever a stable public name exists.
- Unit Explorer shows visible-versus-total Unit counts with an availability breakdown, and grouped
  Skill/Equipment/Weapon filters behave more consistently.

### Added

- Add deterministic readable public slugs for Armies, Units, Skills, Equipment, and Weapons while
  continuing to accept numeric identifiers for compatibility and provenance.

### Changed

- Use readable slugs throughout browser links, catalog/detail APIs, Unit Explorer filters, and
  canonical cross-domain references where a stable application identity exists.
- Show the Unit Explorer's visible unique-Unit count alongside the total available under the same
  filters, with an expandable availability breakdown.

### Fixed

- Resolve grouped Skill, Equipment, and Weapon filters across all source variants and canonicalize
  accepted legacy numeric references to readable slugs when available.
- Keep session-only Settings, Team Operations-only Skill usage, merged Skill identities, and
  reviewed catalog naming consistent across browser and API surfaces.

### Upgrade notes

- Rebuild generated Army databases before deploying 0.6.2; older generated `infinity.db` files are
  not compatible with this release.

## [0.6.1] - 2026-09-20

### Player summary

- Unit, Army, Skill, Equipment, and Weapon browsing now uses more consistent canonical identities
  across different Army views.
- Army totals count actual logical Units instead of duplicate source representations.

### Changed

- Move Unit, Army, profile/loadout, Skill, Equipment, and Weapon browsing onto canonical
  application data while preserving source-specific context and improving Army-oriented query
  performance.
- Preserve richer source projections behind canonical identities so cross-Army relationships and
  profile metadata remain available without treating one Army view as the complete game model.

### Fixed

- Count Army totals by logical Units rather than duplicate source representations.
- Protect deployment artifacts from synthetic development/test data and reject deployments whose
  runtime database and processed graphical assets come from different Army snapshots.

### Upgrade notes

- Rebuild generated Army databases before deploying 0.6.1; there is no in-place migration from the
  previous application-data layout.

## [0.6.0] - 2026-09-19

### Player summary

- Unit availability, faction presentation, symbols, and weapon-range information are more
  consistent and better grounded in authoritative source relationships.

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

### Player summary

- No player-facing changes.

### Added

- Add the foundation for cited curated rules data and archived wiki sources.
- Clarify licensing boundaries for InfinityDB code, external game data, and graphical
  assets.

### Changed

- Stop distributing third-party graphical symbols in the source tree by default.
- Improve cross-platform handling of wiki-mirror paths and local asset URLs.

## [0.5.1] - 2026-09-14

### Player summary

- No player-facing changes.

### Fixed

- Mark the deployment, install/update, and application-image pruning scripts executable so the
  documented server maintenance commands work directly from a release checkout.

## [0.5.0] - 2026-09-14

### Player summary

- Filter the Unit catalog by Skills, Equipment, and Weapons.
- Browse a new **Traits** catalog with concise summaries and links to where each trait is used.

### Added

- Add advanced unit-catalog filters for skills, equipment, and weapons.
- Add a Traits catalog and detail pages covering traits used by weapons, Skills, and Equipment,
  with concise summaries and usage grouped by catalog type.
- Add server deployment, install/update, and application-image pruning scripts with documented
  image-retention behavior.
- Add a Developer-mode control for bypassing cached API responses while reviewing a local
  deployment.

### Changed

- Document the release deployment workflow and refresh immutable static-asset URLs so linked
  browser modules load their matching release versions after deployment.

### Fixed

- Remove incompatible browser theme metadata from static pages.

## [0.4.2] - 2026-09-14

### Player summary

- Optional-unit settings now apply consistently to mercenary and reinforcement availability without
  stale browser results.

### Fixed

- Apply optional-unit settings consistently to unit availability, including
  mercenary and reinforcement armies, without stale browser results.

## [0.4.1] - 2026-09-13

### Player summary

- Support questions, suggestions, and feedback now point to the project's GitHub page.

### Changed

- Direct support questions, suggestions, and feedback to the project GitHub page.

## [0.4.0] - 2026-09-13

### Player summary

- High-volume Unit and catalog browsing is more responsive, with clearer navigation feedback while
  pages load.
- The browser now refreshes automatically when the deployed release or source data changes.

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

### Player summary

- Catalog and detail pages no longer risk getting stuck in a loading state after an application
  update.

### Fixed

- Prevent cached browser modules from mixing releases and leaving catalog or detail
  pages in a loading state.

## [0.3.2] - 2026-09-13

### Player summary

- Use global controls to include mercenaries, Spec-Ops, Team Operations, and reinforcements, and
  optionally remember browsing preferences on the current device.
- Browser updates are handled more reliably, and optional-unit settings and external wiki labels are
  applied more consistently.

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

### Player summary

- Settings became a reusable responsive menu, while Unit search and catalog presentation gained
  clearer Army-color accents.
- Movement values and mobile navigation were corrected.

### Added

- Add a reusable responsive Settings menu.

### Changed

- Improve unit search and catalog presentation, including army-color accents.
- Make the browser footer accurately identify unreleased checkouts.
- Use the newest available local source archive for default builds and debugging.

### Fixed

- Correct movement-value presentation and mobile navigation behavior.

## [0.3.0] - 2026-09-12

### Player summary

- The browser gained a landing page, compact navigation, division badges, and a more consistent
  responsive visual system.

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

### Player summary

- The About page now explains InfinityDB's purpose, data flow, current reference features, future
  direction, and independent-project status in more detail.

### Changed

- Expand the About page with InfinityDB's purpose, local data flow, current reference
  features, future direction, and independent-project disclosures.

## [0.2.0] - 2026-09-11

### Player summary

- Browse searchable **Skills**, **Equipment**, and **Weapons** catalogs with detail pages linked
  back to the Unit profiles and loadouts that use them.
- Weapon profiles now include ammunition, traits, ranges, special data, and relevant icons, while
  Unit-detail presentation is more complete.
- Displayed AVA, literal punctuation searches, missing assets, and packaged symbols were corrected.

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

### Player summary

- Unit rows are clickable, search ignores case/accents/punctuation, and the browser shows the Army
  snapshot download date.
- Reinforcement matching and profile grouping are more reliable despite source naming variations.

### Added

- Add an About page, snapshot download dates in the browser, and clickable unit
  catalog rows.

### Changed

- Make unit search insensitive to case, accents, and punctuation.
- Improve reinforcement matching and profile grouping despite source naming variants.

### Upgrade notes

- Rebuild existing databases before deploying 0.1.2.

## [0.1.1] - 2026-09-11

### Player summary

- Choose centimetres or inches, browse Skill Modifiers, and control reinforcement visibility and
  availability.
- General profiles show type/classification, equivalent Army lists group more cleanly, and
  narrow-screen profile/loadout rows are more usable.

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

### Player summary

- InfinityDB's first release provides a local browser for Units, Armies, profiles, loadouts, Skills,
  Equipment, Weapons, AVA, and optional-unit availability.
- Army/faction labels, mercenary availability, symbols, and shared versus Army-specific Unit details
  already receive validation and presentation fixes in the initial release.

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
