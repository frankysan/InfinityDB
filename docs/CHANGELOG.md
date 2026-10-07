# Changelog

All notable user- or operator-relevant changes to InfinityDB are documented here.
Each release begins with a concise **Player summary** containing only changes visible or useful to
players; the remaining sections preserve fuller user/operator release detail. Entries describe
meaningful release outcomes rather than detailed implementation history. New or materially revised
entries use the project-domain labels defined in `docs/project-domains.md`; historical release notes
are not retroactively relabeled.

## [0.10.0] - 2026-10-07

### Player summary

- Choose System, Light, or Dark themes, with improved contrast and readability.
- Compare S1–S8 Silhouette templates in the Glossary and Unit previews at a shared scale.
- Read the new **What's changed** page and privacy information.
- Browse clearer rules descriptions and Unit help, with improved navigation, filtering,
  artwork, and small-screen layouts.

### Added

- **Web frontend:** Add System, Light, and Dark theme selection in Settings. System follows the
  operating-system preference; explicit choices use existing Settings persistence and apply before
  first paint. Add a project favicon that stays legible in light and dark browser chrome.
- **Web frontend:** Add scale-preserving S1–S8 Silhouette diagrams to the Glossary and Unit
  statline previews. Other supported Silhouettes include a faded S2 reference at the same scale;
  S2 appears alone and the normal statline stays compact.
- **Web frontend + Project infrastructure:** Add a **What's changed** page with concise player
  summaries and expandable release details, plus a public privacy policy linked from cookie
  consent. Explain aggregate-only monitoring, session settings, opt-in preference cookies, and
  shareable URL state.
- **Data processing + Web frontend:** Add **FTO (Fireteam Option)** to the Glossary, explaining
  option-name identifiers and chart requirements for specific variants such as FTO-2.
- **Deployment:** Add bounded aggregate metrics history and operator reports by week, version,
  and snapshot. A separate private collector retains request/status/error summaries and latency
  estimates without visitor identities. Updates capture outgoing and incoming generations without
  blocking a healthy application; history survives restarts and rollback, and format upgrades are
  transactional with older collectors refusing newer stores.
- **Deployment:** Add privacy-preserving resource capture, sanitized warning/error diagnostics,
  and configurable operational alerts for CPU, memory, storage, errors, and health failures.
- **Deployment:** Add repeatable HTTP capacity testing and controlled worker/resource comparisons.
  The matched 2x4 versus 4x4 experiment establishes 4x4 as the first bounded scale step, with an
  explicit latency/error/resource trigger for review. Production continues to default to 2x4;
  measured results and comparison commands are retained in deployment guidance.
- **Deployment:** Add `infinity-db database-health` to validate Army databases and optionally
  verify their application/raw export pair, with revision, timing, and JSON output.
- **Acquisition:** Add English-only Human Sphere wiki research snapshots, including orphaned
  content pages, deterministic archive identities, and resumable downloads. Missing required pages
  block publication; unrelated Talk/service pages and stale discovered 404s remain diagnostics.

### Changed

- **Web frontend:** Use clearer game/reference language throughout navigation, page introductions,
  Unit notes, profile notation, rules help, and empty/error/loading states. Unresolved reference
  information appears as **Needs verification** with an **uncertain** marker and readable reasons.
- **Data processing:** Publish validated application/raw exports as one matching generation.
  Interrupted publication preserves the previous serving database, rejects mismatched raw-dependent
  audits, and recovers by rerunning the export.
- **Web backend + Web frontend:** Interpret Fireteam limit sentinels explicitly and include legacy
  Armies in global search, linking to their entries on the Armies overview.
- **Data processing + Web frontend:** Refresh processed faction, Order, Characteristic, Peripheral,
  and Unit artwork. Preserve distinct contextual variants, publish Peripheral-only artwork in its
  own namespace, and keep mixed-role artwork with its Unit identity.
- **Project infrastructure:** Retain exact-commit hosted validation evidence in annotated release
  tags. Release candidates can complete the optional full-assets check before merge using a
  reproducible checksum-pinned publication bundle; final release evidence remains tied to the
  resulting release commit.

### Fixed

- **Web frontend:** Give Unit Profile row headers maintained help and Glossary links, keep
  Fireteam columns and cm-mode statlines readable at narrow widths, and improve text, status,
  link, and focus contrast in both themes. Army links now scroll to and highlight the matching card.
- **Web backend + Web frontend:** Explain when optional-unit Settings hide all Unit profiles,
  remove redundant one-Unit Characteristics from filter choices, and match the combined
  Headquarters/Mechanized classification through either component filter.
- **Web backend:** Reject unknown or duplicate semantic parameters on Fireteam and Unit-detail
  APIs while preserving the Developer-mode cache-bust parameter.
- **Web frontend:** Display stationary MOV as an em dash rather than a negative distance, and
  keep cm/in conversion consistent across profiles, rules help, and Weapon ranges.
- **Data processing:** Update Armed Turret to current N5 v5.3 citations while preserving the
  documented conflict between sources for its deployable-profile Silhouette.
- **Acquisition:** Apply symbol overrides to all same-category upstream-identical artwork;
  conflicting overrides fail explicitly rather than producing ambiguous results.
- **Data processing + Web backend + Web frontend:** Correct Unit and General-profile symbol
  assignments, preserve genuine profile-specific artwork, and repair repeated upstream
  misassignments such as Crabbots on Cutters and Dragões while retaining source provenance.
- **Deployment:** Include published Peripheral artwork in installed packages and release images.

### Upgrade notes

- **Deployment:** Deploy the release-matched tracked Army database, rules database, and complete
  processed SVG publication together. Normal server upgrades consume these artifacts without
  rebuilding databases in production.
- **Deployment:** Preserve the metrics-history volume during updates and rollback. Older
  collectors refuse newer history formats; rollback must not downgrade or delete retained history.

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
