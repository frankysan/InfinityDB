# Changelog

All notable user- or operator-relevant changes to InfinityDB are documented here.
Each release with entries begins with a concise **Player summary** containing only changes visible
or useful to players; an empty pending section is omitted from the browser page. The remaining
sections preserve fuller user/operator release detail. Entries describe
meaningful release outcomes rather than detailed implementation history. New or materially revised
entries use the project-domain labels defined in `docs/project-domains.md`; historical release notes
are not retroactively relabeled.

## [1.1.0] - Unreleased

### Player summary

- ITS Season 18 scenario pages offer explicit tournament and optional Extra
  context selection. Event-only Spec-Ops restrictions no longer appear as
  default N5 Skill restrictions.
- Refreshed Army, Unit, Peripheral, Order and Characteristic symbols while
  preserving the existing Seed Soldier image URL.

### Added

- **Project infrastructure + Data processing:** Added explicit PDF-layout
  selection to the Reinforcements evidence auditor, preserving original source
  labels, byte pins and applicability findings. Legacy paths remain the default;
  changing the selected layout does not migrate files or change published rules.
- **Project infrastructure + Acquisition:** Added an explicit local-workspace
  layout for verifying and previewing staged Army, Wiki and raw-symbol snapshot
  pairs. Legacy activation remains the default; neither selection changes
  Syncthing folders or migrates existing sources, PDFs or overrides.
- **Data processing + Web backend:** Added deterministic multi-season ITS
  publication validation and synthetic duplicate-slug acceptance, preserving
  explicit source ownership and independent season/revision selection.
  No additional real season content is included in this release.
- **Data processing + Web backend + Web frontend:** Added source-cited ITS Season 18
  play-context policies with explicit tournament, TEAM-OPS and Reinforcements
  Extra selection. The policy API never applies a context by default; scenario
  pages show only policies chosen by the player and link to their official
  source references.
- **Data processing + Project infrastructure:** Added `database-health --db-dir`
  to inspect a complete runtime directory offline, including SQLite integrity,
  source-matched references and file fingerprints. Missing or mismatched data
  produce an unhealthy report without changing the selected files.
- **Data processing + Project infrastructure:** Added an offline complete-runtime
  build with `build --db-dir`, using a selected local Army archive and maintained
  references. The build records shared input provenance, validates all outputs
  before replacing the selected files, and retains existing outputs when
  generation or validation fails.
- **Data processing + Web backend + Deployment:** Embedded exact reviewed
  Skill/Equipment occurrences in Rules for complete runtime builds, removing
  the variant-usage JSON requirement while preserving group counts, source
  contexts and browser links. Damaged or mismatched embedded data is rejected.

### Changed

- **Acquisition + Data processing:** Symbol acquisition and graphical processing
  now use the external producer. InfinityDB continues to verify and promote its
  handoff; the retired in-tree processor can no longer resume old builds.
- **Data processing + Web frontend:** Published the approved external symbol
  artwork and retained the former Seed Soldier filename as a byte-identical
  compatibility alias. Existing image links continue to work.
- **Web backend + Data processing:** Preserved scenario-specific N5 FAQ
  applicability across seasons: a core mission's ruling cannot follow an
  independently published ITS mission merely because both share an ID.
  General N5 rulings remain available in valid selected seasons.
- **Data processing + Web frontend:** Removed ITS-specific Spec-Ops/TEAM-OPS
  restrictions from the default N5 Spec-Ops and Request SpecBall rules cards,
  retaining their core Skill semantics and bilingual printing caveat.
- **Data processing + Web backend + Deployment:** Retired loose deployed-object
  JSON serving, legacy v8/v9 build modes and image assembly, and v1 variant
  publications. Current builds and images require database-embedded deployed
  objects and v2 variant data; obsolete inputs fail closed. Older releases
  remain recoverable through their matching retained images.

### Fixed

- **Acquisition + Data processing:** Kept snapshot provenance byte-exact across
  standalone producers and the offline consumer. Manifest collisions fail
  without replacing prior evidence, and acquisition rollback preserves a
  competing producer's manifest even when its bytes are identical.
- **Deployment + Web backend:** Added the ITS season-policy API route to the
  bounded metrics-history allowlist, preserving request history for that route
  without accepting arbitrary metric labels.

## [1.0.1] - 2026-11-09

### Player summary

- Added the ability to save scenario maps directly as SVG images through the browser's
  image context menu, retaining the selected Light/Dark theme, Army Points and distance units.
- Completed Battleground map labels and measurements for both Deployment Zones and all
  three Sectors, including the Objective Points available to each player.
- Added clearer spacing between Orders & AROs controls, scenario rules and reference cards.
- Identified upcoming release notes by their target version and marked them as unreleased.

### Added

- **Deployment:** Added a disposable Docker image preview for staged or tracked runtime
  artifacts. It checks packaged data, startup health and reference APIs, then cleans up
  the preview container and image without replacing the deployed service.

### Changed

- **Web backend + Web frontend:** Added version-specific headings for upcoming release notes,
  showing the target version and Unreleased status without a release date.
- **Web backend + Web frontend:** Kept scenario maps as ordinary images that can be
  saved directly. Each standalone SVG embeds the selected theme palette, and the map
  updates when display preferences change.
- **Data processing + Web backend:** Made `build-rules` write current Rules to
  `local/rules-standalone.db` and prepare a complete local runtime for `serve` by default.
  Explicit `--output` selects a standalone Rules-only build; `--legacy-v8` and `--legacy-v9`
  retain older formats. Direct writes to the tracked release Rules database are rejected.

### Fixed

- **Data processing + Web frontend:** Completed ITS Season 18 Battleground maps at every
  supported game size with Deployment Zone A/B labels, the table center line, Sector scoring
  for both players and depth measurements for both Deployment Zones and all three Sectors.
  Measurements follow the selected inches/centimeters preference.
- **Web frontend:** Added vertical spacing between Orders & AROs declaration controls,
  the optional scenario card and the following reference cards.
- **Data processing + Web backend + Deployment:** Restored the
  `build --compact` → `build-rules` → `serve` checkout workflow, using
  up-to-date local Rules, exact-variant data and Weapon citations without
  requiring Docker release publication. Docker uses only verified, matched release
  artifacts. `serve` selects the verified local runtime when present and reports
  incomplete or stale builds with instructions to rebuild. A checkout
  without a local runtime uses the tracked release data; an explicit `--database` bypasses
  automatic selection.
- **Data processing + Deployment:** Promoted the verified v10 Rules database
  and matching variant/Weapon publications together, retaining existing
  rules semantics and the improved Battleground map. Embedded reviewed deployed
  objects in the rules database and preserved independent JSON compatibility
  for legacy release images.
- **Data processing:** Updated shared Rules staging to retain the current database
  format and rebuild its reviewed deployed-object model, preserving Restrictions
  and source pairing after the v10 migration. Updated source audits and staging
  comparisons to read embedded objects without requiring a legacy JSON file.
- **Web frontend:** Fixed keyboard navigation between Army overview cards and
  Back/Forward through their fragment links. Kept the existing page in place so
  focus stays on the linked card instead of racing a page reload.
- **Deployment + Project infrastructure:** Fixed deployment file permissions after saving
  private installer settings. Kept the settings file restricted to its owner without
  applying that restriction to subsequent checkout files, and ensured the metrics-history
  helper remains readable by its service user. Preserved fingerprinted SVG bytes across
  checkouts to avoid line-ending changes invalidating release verification.

### Upgrade notes

- **Deployment:** Changed direct Docker builds to require a prepared runtime bundle under
  `data/runtime/`, created with `python -m tools.prepare_runtime_bundle`; `deploy.sh` handles
  this preparation automatically. Current Rules store deployed objects in the database,
  while legacy images retain their separate JSON file. Deployment requires the matched
  Army/Rules databases and variant/Weapon publications for the selected release.
- **Data processing + Web backend:** Preparing the automatic checkout runtime requires
  `build --compact` before `build-rules` so the paired raw Army data is available for
  exact-variant references.
  An existing stale local runtime requires rebuilding before `serve` can use it.

## [1.0.0] - 2026-11-07

### Player summary

- Expanded the N5.3 reference with linked explanations of the Player Turn, Orders and AROs,
  Command Tokens, movement, combat, Hacking and Fireteams, with citations beside the rules.
- Added searchable Weapon Properties, expandable Ammunition help and separate profiles for
  17 deployed objects. Expanded Equipment and Glossary references and made more source links
  available directly from Unit and Weapon profiles.
- Added 29 dated FAQ clarifications beside the affected rules and scenarios, and explained
  known disagreements between Army, rulebooks, Wiki pages and language editions in context.
- Added scenario-specific Specialist Troops filtering, optional Reinforcements references
  and the ITS Season 18 Battleground pilot with game-size-specific maps and scoring.
- Improved rules charts, core-scenario maps and narrow-screen Unit pages. Added clearer
  keyboard navigation and page announcements, and made the accuracy notice collapsible.

### Added

- **Data processing + Web backend + Web frontend:** Added Game Sequence and Order Pool
  references covering the five phases of the Player Turn, Tactical Phase checks, Combat Group
  Order ownership, hidden and off-table Orders, unused Orders and repeat spending. Explained
  the source disagreement over Lieutenant Order eligibility alongside the supported reading.
- **Data processing + Web backend + Web frontend:** Added an Orders/AROs quick reference
  linking core declarations to their rules, with scenario actions and Request Reinforcements
  separately identified. Added an ARO overview covering eligibility, declaration timing,
  valid targets, one reaction per Order, default Burst and the restriction on splitting Burst.
- **Data processing + Web backend + Web frontend:** Added a Command Tokens reference
  explaining the shared four-token match pool and Strategic, Executive and Operational uses,
  including first-turn restrictions, expenditure timing, eligible actions and repeat-use limits.
- **Data processing + Web backend + Web frontend:** Added Initiative Roll and Combat Group
  references covering Lieutenant WIP, rerolls, turn-order and Deployment choices, the
  ten-member Combat Group limit, Peripheral capacity, group information and transfer exceptions.
  Added separate Army Retreat! and Standard Game references explaining the survivor check,
  Loss of Lieutenant, recovery and evacuation, and the Standard Game's rounds, scoring and
  ending conditions without applying those endings to scenarios.
- **Data processing + Web backend + Web frontend:** Added a Game Modes table with six
  N5.3 game sizes, Army Points, base SWC, recommended table and Deployment Zone dimensions,
  estimated play times and Retreat! thresholds. Kept setup recommendations distinct from
  scenario-specific requirements.
- **Data processing + Web backend + Web frontend:** Added a dedicated General Rules page
  for the N5.3 Restrictions chart, covering six subjects and fourteen prohibitions, including
  mounted Motorcycles, upward movement, ladder use and Lieutenant selection. Linked related
  Skill, Equipment and State restrictions to their source context in Developer Mode.
- **Data processing + Web backend + Web frontend:** Expanded movement and battlefield geometry
  references for Move, Climb, Jump, Line of Fire, Cover, zones, Coherency and replacement
  positioning. Added supporting-surface requirements, vertical-movement and posture exceptions,
  and linked Silhouette explanations, including S0 and SX alongside the existing S1–S8 diagrams.
  Expanded Deployment Phase help with base placement, contact, fit, Prone and pregame measurement
  restrictions.
- **Data processing + Web backend + Web frontend:** Added eighteen suggested terrain
  combinations, including optional difficulty, combined visibility and conditional Zero-G.
  Made Narrow Gate and Wide Gate discoverable through search and the Glossary, linking to
  Access Width.
- **Data processing + Web backend + Web frontend:** Expanded linked combat references for
  the Order Expenditure Sequence, Coordinated Orders, Guts Rolls, Face to Face and Saving Rolls,
  Special Dice and Mixed Weapons. Added BS/CC Attack explanations for shooting into close
  combat, Coup de Grâce and multiple-Trooper attacks, plus distinct Direct and Impact Template
  guidance for targeting, cancellation, Dodge, Criticals and scenery.
- **Data processing + Web backend + Web frontend:** Expanded Hacking Area, Firewall,
  Supportware and Modifiers Explained references with linked targeting, timing, exceptions
  and recovery guidance. Added N5.3 chart citations to Hacking Device references alongside
  their Wiki sources.
- **Data processing + Web backend + Web frontend:** Expanded Weapon references across
  CC Weapons, Pistols, Rifles, Sniper Rifles, heavy and support weapons, Mines and deployed
  objects. Explained mode-specific placement, charges, templates and effects for Weapons
  including D-Charges, Disco Baller, SymbioBomb, Pitcher and Mine Dispenser. Made Breaker
  Marksman Rifle searchable even without current Unit usage.
- **Data processing + Web backend + Web frontend:** Added searchable Weapon Properties with
  linked previews and cited examples, including Plasma, Viral, Breaker, K1, MULTI,
  Monofilament, Silenced, AP combinations and N+E/M. Added expandable Ammunition help on
  Weapon profiles while preserving each mode's Saving Rolls, Traits, Labels and States.
  Added exact N5.3 Weapon Chart citations for reviewed profiles and individual modes.
- **Data processing + Web backend + Web frontend:** Added standalone profiles for 17 reviewed
  deployed objects, with source links, delivery methods and explicitly disputed or unavailable
  attributes. Covered WildParrot's two placement methods, FastPanda's Perimeter deployment
  and Armed Turret profiles, and retained the unresolved Mine Dispenser subtype. Linked
  reviewed delivery sources to their carrying Unit profiles and loadouts where established.
- **Data processing + Web backend + Web frontend:** Added 29 dated FAQ clarifications beside
  the Equipment, Scenarios, Skills, Traits, States, General Rules, Hacking Programs and
  Fireteams they affect. Linked current English/Spanish answers and retained the original
  FAQ version where applicable. Added a General Deployment repositioning reference and
  identified the Ancillary scoring answer's Annihilation-only scope as InfinityDB's reviewed
  interpretation, with the source ambiguity disclosed.
- **Data processing + Web backend + Web frontend:** Added a Specialist Troops reference and
  a Unit Explorer filter with InfinityDB Standard, Domination, Supplies and Firefight choices.
  Results identify candidate Units for the selected context without implying that every
  profile qualifies.
- **Data processing + Web backend + Web frontend:** Added optional Reinforcements Extra,
  Commlink and Request Reinforcements references, with links to Reinforcement Section pools,
  their owning Armies and filtered Unit Explorer views. Marked the procedures as **N4-origin**
  because current N5/ITS references had not established that the historic procedures were
  reissued unchanged. Scoped Commlink (+1)/(+2) Trooper-limit increases to that Extra,
  preserving the normal N5 roster limit.
- **Data processing + Web backend + Web frontend:** Added a separate Request SpecBall
  reference covering eligibility, token drop and collection, Enhanced Profiles and SpecBot
  handling, with links distinguishing it from Request Speedball and ITS TEAM-OPS procedures.
- **Data processing + Web backend + Web frontend:** Added scenario collection and revision
  selection, plus the ITS Season 18 Battleground pilot with size-specific maps, Sectors,
  end-of-game scoring and special rules. Updated shared scenario links to retain the selected
  collection and game size.
- **Web backend + Web frontend:** Added Equipment such as Cubes and TinBots to the Glossary
  with links to their reference pages. Added source citations to embedded Attribute,
  Game-term and Unit Profile definitions and contextual profile-notation help, and exposed
  Label vocabulary sources with their scope clearly identified.
- **Web backend + Web frontend:** Added Developer Mode links from reviewed Skill and
  Equipment variants to their exact source occurrences and Army-specific Unit profiles or
  loadouts. Excluded unreviewed variants and shared options without established assignments.

### Changed

- **Data processing + Web backend + Web frontend:** Improved Martial Arts, Booty and
  MetaChemistry charts by hiding inapplicable modifiers, separating Booty's TAG/other-Troop-Type
  results and MetaChemistry's compound outcomes, and linking related Weapons, Skills and
  Equipment without changing the source results.
- **Data processing + Web frontend:** Expanded Trooper, Unit Profile and Peripheral Glossary
  definitions to explain profile choices, Attributes, Orders, Attacks, Controller activation,
  Army List limits and Cost accounting. Clarified Deployable Equipment and Weapons, valid
  Targets and the distinction between Hostile and Neutral game elements.
- **Data processing + Web frontend:** Expanded Label and Trait definitions with deployment
  limits, attack/Hacking eligibility, close-combat modifiers, fixed results, Null States and
  Private Information conditions. Clarified Deployable targetability, spent Disposable uses,
  Unloaded, Non-Reloadable, Target (Attribute) and Silent's conditional stacking, while retaining
  Assignable's bilingual timing difference and the unresolved Silent/Immunity interaction.
- **Data processing + Web backend + Web frontend:** Expanded Peripheral, Doctor and Engineer
  guidance with treatment and recovery examples, and clarified Immunity with simultaneous
  State effects. Expanded explanations of Stealth, Controlled Jump/Speedball, Intuitive Attack,
  BS Weapon (WIP), Continuous Damage and Negative Feedback lifetimes. Kept ordinary rules,
  conditional exceptions and reviewed examples visibly distinct.
- **Data processing + Web frontend:** Clarified Fireteam formation and ongoing membership,
  Team Leader and shared actions, leaving/rejoining, TinBot sharing, Special Dice and Disposable
  spending. Explained the Level 3 Morat example without granting Level 4 bonuses. Added links
  between Fireteams and relevant State rules, including Suppressive Fire, Retreat!, Isolated
  and the Ancillary-specific Disconnected exception.
- **Data processing + Web frontend:** Added separate ECM: Guided and ECM: Hacker explanation
  cards with their attack scope and citations. Distinguished cited, reference-only Equipment
  combinations from options present in current Army data, without implying that a Unit has
  those combinations or that a family citation verifies every named variant.
- **Data processing + Web backend + Web frontend:** Made known source disagreements visible
  beside the affected rules and retained imported Army values. Explained disputes over
  Weapon profiles and Saving Rolls, Mine/Dazer and Armed Turret Silhouettes, Dodge (ARM+3),
  Fireteam dice/member-count examples and Doctor/Engineer target eligibility. Added contextual
  explanations for unresolved Army qualifiers, FAQ question scope and Engineer's bilingual
  contact wording.
- **Web frontend:** Made desktop navigation more compact and mobile menus scrollable on short
  screens. Moved keyboard focus to newly loaded content and announced navigation to assistive
  technologies while preserving scroll restoration. Made the accuracy/independence notice
  collapsible to an accessible icon for the current browsing session.
- **Web frontend:** Presented FAQ answers and deployed-object profiles in separate cards,
  improved Orders/AROs tables and section spacing, and removed repeated subtitles, date metadata
  and source captions while retaining linked citations. Moved exact source occurrences and
  technical Reinforcement relationships into Developer Mode and reduced repeated processing
  when loading Glossary definitions.

### Fixed

- **Data processing + Web backend + Web frontend:** Corrected reviewed Skill declaration
  categories and conditional ARO explanations. Identified Alert! as an automatic facing
  adjustment, clarified Climbing Plus/Super-Jump declarations, and corrected guidance for
  Guard/Aerial, Combat Instinct/Sixth Sense, Look Out!, Reload/Place Deployable, Discover and
  Hacking Area reaction windows. Distinguished additive Range/Cover/Skill MODs from the
  most-restrictive, non-stacking Visibility Zone MOD.
- **Data processing + Web backend + Web frontend:** Corrected Hackable profile help to
  identify default HI/REM/TAG/VH eligibility, the Hacker exception regardless of Troop Type
  and Program-specific allied/enemy targeting. Explained an unspecified Hacking Program Target
  dash without treating it as no valid target. Corrected Repeater and Supportware source links,
  added primary citations for Hacking Programs and clarified White Noise timing and Zero Pain's
  two-roll defense in either turn. Corrected Pheroware Tactics and PT: Endgame citations to the
  N5.3 Weapon Chart on page 182.
- **Data processing + Web backend + Web frontend:** Corrected Doctor (2W) to remove
  **up to two Wounds**. Clarified an Isolated Lieutenant's next-Active-Turn Loss of Lieutenant
  trigger and the difference between clearing Isolated before that turn and after the
  army-level situation has begun.
- **Data processing + Web frontend:** Clarified Ammunition, Critical and Immunity exceptions,
  including PARA with missing PH, Shock's VITA condition, T2's additional Critical roll and
  Stun/Guts. Separated Smoke/Eclipse opposition, Visor interactions, Dodge, template retention,
  scenery and Critical effects in compact help. Kept Combined Ammunition distinct from
  Combined Saving Rolls.
- **Data processing + Web frontend:** Clarified Mine Trigger Area measurement, Total Cover,
  concealed Markers, revealed objects and exceptional movement. Put Mine-specific profiles
  before shared rules and displayed Cybermine's absent Ammunition as "--". Distinguished
  Deactivator removal and persistent deployed-object effects from Boost contact attacks,
  Armed Turret reactions and allied Disco Ball activation.
- **Data processing + Web frontend:** Corrected Domination Console placement distances to
  use marker centers and table edges, and displayed physical Console/Supply Box diameters
  separately from scoring areas. Disclosed Domination's conflicting English 6 SWC and Spanish
  7 SWC values at 350 points. Corroborated Annihilation's corrected survival bands while
  retaining the four core scenarios' distinct scoring and ending conditions.
- **Web backend + Web frontend:** Respected chart exclusions for Fireteam Wildcards,
  including Invincible Army Forward Fireteams and Next Wave Team Achilles. Preserved original
  member annotations, flagged unverified Unit/FTO references and stopped treating every
  parenthesized term as a counts-as rule. Kept Reinforcement parent-Army limits separate from
  Section members and repaired links to the Fireteam quick reference.
- **Data processing + Web backend + Web frontend:** Put Equipment imported in Army's Skill
  category, Regular Training and loadout Attribute overrides in their proper Unit categories.
  Removed nonexistent Skill links created by source-only markers. Explained how dashed
  Attributes limit declarations and use, and retained SWC's support-weapon meaning.
- **Data processing + Web backend:** Restored fourteen source-scoped Restrictions in the
  shipped rules data and the Restrictions API without changing reviewed deployed-object
  profiles or existing relationships.
- **Web frontend:** Fixed narrow-screen clipping of dense Unit attributes, loadouts,
  composite-option names, Points/SWC, Order symbols and reference breadcrumbs. Kept Glossary
  headings below the navigation bar and prevented detached previews from reopening after
  navigation. Made official Wiki heading links available on all 33 canonical Trait pages.
- **Web backend + Web frontend:** Included nonempty upcoming-release notes on **What's changed**
  and omitted empty development sections. Added Orders and AROs to the home page reference links.
- **Deployment:** Fixed aggregate metrics-history collection for reviewed variant-use requests
  and Orders/AROs routes without retaining query values.

### Upgrade notes

- **Deployment:** This release requires the complete image with matched Army/rules databases,
  deployed-object, variant-usage and Weapon-profile publications, and graphical assets.
  Mixing artifacts from different releases or rebuilding source data on the production
  server remains unsupported.
- **Data processing:** Local installations maintaining generated data require the
  release's curated inputs and guarded v9 rules/publication workflow. Migration requires
  retaining original upstream snapshots and recovery copies.

## [0.10.1] - 2026-10-10

### Player summary

- Browse the four core scenarios: Annihilation, Domination, Supplies and Firefight,
  with game-size-specific setup, objectives, scoring and deployment maps. Maps follow
  your theme and distance preference.
- Ammunition pages now show compact mechanics and linked State effects. Weapon profiles link
  reviewed Ammunition components and separate Traits, Labels and States for easier lookup.
- Rules references explain more of the conditions and exceptions that matter during play,
  including Immunity, Dodge, Reset, State cancellation, Smoke/Eclipse and Critical Saving Rolls.
- Corrected explanations cover IMP-2 Discover modifiers, Stealth against Deployables,
  Deployable Cover, TinBot sharing and Fireteam formation requirements. Special Weapon
  references explain their distinct modes and keep unresolved source disagreements visible.
- Visibility Zones are easier to find through search, the Glossary and linked rules tooltips;
  longer rules cards use clearer sections and separate source notes.

### Added

- **Data processing + Web backend + Web frontend:** Add the four current core scenarios,
  with a default 300-point selection, point-dependent setup/scoring, linked scenario Rules
  and Skills, source notes and deployment maps generated from the maintained geometry.
  Scenario selection is shareable; maps support Light/Dark themes and inches/centimeters.
- **Data processing + Web backend + Web frontend:** Add compact, source-cited mechanics for
  all eleven base Ammunition references, including conditional State effects and Critical
  exceptions. Weapon profiles link base Ammunition and the reviewed AP+DA, AP+Exp,
  AP+Shock and AP+T2 components while retaining imported Saving Rolls.
- **Data processing + Web backend:** Add distinct rules references for Drop Bears,
  Flash Pulse, Kobra Pistol CC Mode, PARA Mine, Mines, Cybermine, Chest Mine, PT: Endgame,
  Sepsitor, Sepsitor Plus and WildParrot. Explain mode-specific behavior and preserve disagreements
  with Army or other cited sources without silently changing imported profiles.
- **Data processing + Web backend:** Identify Combined Saving Rolls on the six Plasma
  Hit/Blast profiles in the Weapon API, including the additional ARM Saving Roll for a
  Critical. Keep these distinct from Combined Ammunition and retain source profile values.
- **Web backend + Web frontend:** Make Visibility Zone and its Low, Poor, Zero and White
  Noise variants discoverable in search and the Glossary, with linked explanation tooltips
  in rules text.

### Changed

- **Data processing:** Reduce database rebuild time, especially on Windows, while preserving
  generated contents, validation and deterministic release artifacts.
- **Data processing + Web frontend:** Present long rules references in topic-based paragraphs
  with separate source notes. Immunity keeps Requirements, Effects and Restrictions in order,
  followed by clarifications, examples and reviewed interactions with conditional outcomes
  and evidence labels. Explain AP+DA protection, the Flash Pulse exception and
  the different AP-only, Shock-only and BTS Immunities against Silenced Pistol without implying
  that unreviewed combinations have been resolved. Critical-Immunity examples
  cover all five reviewed combined Ammunition forms, keeping their original
  effects and target conditions explicit. E/M-only protection against the
  E/M CC Weapon also distinguishes suppressed E/M effects from remaining Normal Wounds.
  Silent's unresolved Attribute-Immunity timing and English/Spanish wording
  difference are explained on its Trait page and linked from the relevant references.
- **Web backend + Web frontend:** Group Weapon properties under Traits, Labels or States,
  linking each to its owning reference. Use reviewed N5 names for legacy Army labels;
  original wording remains available in Developer Mode and unknown properties remain visible.

### Fixed

- **Data processing:** Correct IMP-2 Discover modifiers and Stealth's Deployable exception.
  Discover now explains its Range MODs and the retry limit after a failed attempt against an
  Impersonation Marker. Deployable Cover explains Vitroferro's pre-PS cap,
  eligibility and printed S3, Disposable (2), Indiscriminate and Perimeter properties.
  TinBot retains owner requirements, Fireteam sharing and non-stacking benefits.
  Kobra Pistol links the correct CC Attribute.
- **Data processing + Web frontend:** Identify Fireteam Type counts as formation requirements,
  distinguish ongoing integrity and type persistence, and preserve the existing count data.
- **Data processing:** Clarify Dodge and Reset roll/movement conditions, cumulative State
  penalties and cancellation exceptions; explain Smoke/Eclipse opposition and Visor limits,
  AP/E/M rounding, T2 Critical Wounds and Continuous Damage's extra-roll exception.
- **Data processing:** Correct Counterintelligence's Command Token effects, Protheion's
  Attribute penalty and post-death limits, Controlled Jump timing/cancellation and its Speedball
  exclusion. Clarify Doctor, Engineer, MediKit, GizmoKit, Intuitive Attack, Disposable,
  Double Shot, Non-Lethal and Boost exceptions, and BS Weapon (WIP)'s Skill restrictions.
- **Web frontend:** Display no Saving Rolls for Weapon profiles without a Saving Attribute.
- **Data processing + Web frontend:** Correct Annihilation's 350-point surviving-force scoring
  boundaries and Supplies' edge-to-edge Supply Box placement at every game size. Preserve
  Domination's printed 350-point 6 SWC and explain the unresolved source inconsistency.

### Upgrade notes

- **Deployment:** Deploy the release-matched application and both tracked runtime databases
  together. Older rules databases are incompatible with the new scenario references; local
  installations maintaining their own generated data must rebuild the rules database from
  this release's curated inputs. Tagged production deployment uses the bundled databases
  and must not rebuild them on the server.

## [0.10.0] - 2026-10-07

### Player summary

- You can now choose a Light or Dark theme, or let InfinityDB follow your device's settings.
- Silhouette diagrams in the Glossary and Unit previews show templates at the same scale,
  making their sizes easier to compare.
- The new **What's changed** page collects release notes in one place, and the privacy policy
  explains what InfinityDB stores.
- Rules descriptions and Unit help are clearer, artwork has been corrected, and Unit and Fireteam
  pages are easier to read on small screens.

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

- Shared Unit Explorer links show when their optional-unit choices differ from your Settings,
  without changing your saved preferences.
- Order references are more complete, and Strategos and Multispectral Visor levels are easier
  to compare.
- Army symbols wrap more neatly when a Unit is available to many Armies.

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

- New **Ammunition**, **Labels**, and **General Rules** pages, a **Glossary**, and site-wide search
  make rules easier to find.
- Unit Explorer has more filters and an optional view of profile stats. The Armies page covers
  both current and legacy forces.
- Rules text links to related references, and shared links preserve search, filter, and Army
  selections. Pages are easier to use on small screens.

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

- Hacking Programs use the same action labels and page layout as Skills.
- Fonts are more consistent across the site, and the sidebar shows when Army data last changed.

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

- Hacking Programs have their own reference pages, and Fireteam charts can be browsed by Army,
  with rules, limits, Wildcards, and FTO options.
- Unit pages show linked profiles, Peripherals, Controllers, and selection requirements more
  clearly. Profile artwork and Fireteam layouts have also been improved.

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

- On first use, distances are shown in inches and all optional Unit types are included.
  Troop Type names are clearer, and profiles show **VITA** or **STR** as appropriate.
- Settings can be collapsed on desktop, and text and layouts are easier to read.

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

- Equipment such as MediKit, GizmoKit, and Deactivator uses the same action presentation as Skills.
- Paramedic links correctly to MediKit, and reference pages refresh correctly after an app update.

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

- Skills, Equipment, Traits, and States have fuller rules explanations and more links to related
  rules, including a complete State reference.
- Skill pages include Hacking Program, Martial Arts, Booty, and MetaChemistry tables.
  Cube and Cube 2.0 pages list the Units that use them.
- Unit pages are easier to read on very small screens.

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

- Doctor, Engineer, Cyberplug, and Peripheral references explain which Controllers can use
  each type of Peripheral.
- Unit pages show which profiles and loadouts are linked and explain requirements that affect
  those choices.

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

- Browser links use readable names instead of numbers.
- Unit Explorer shows how many Units match your filters and breaks down their availability.
  Skill, Equipment, and Weapon filters also include related variants more consistently.

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

- Units, Skills, Equipment, and Weapons are shown consistently across Army views.
- Army totals count each Unit once, even when it appears in several related Army Lists.

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

- Unit availability, Army labels, symbols, and Weapon ranges are more accurate and consistent.

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

- Unit lists can be filtered by Skills, Equipment, and Weapons.
- The new **Traits** pages explain their effects and link to the Weapons, Skills, and Equipment
  that use them.

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

- Mercenary and Reinforcement results now follow your optional-unit settings without leaving
  outdated results on screen.

### Fixed

- Apply optional-unit settings consistently to unit availability, including
  mercenary and reinforcement armies, without stale browser results.

## [0.4.1] - 2026-09-13

### Player summary

- Support and feedback links now take you to the project's GitHub page.

### Changed

- Direct support questions, suggestions, and feedback to the project GitHub page.

## [0.4.0] - 2026-09-13

### Player summary

- Unit and reference pages respond faster, and it is clearer when a page is still loading.
- The browser refreshes automatically after an app update or a change to Army data.

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

- Reference lists and detail pages no longer get stuck loading after an app update.

### Fixed

- Prevent cached browser modules from mixing releases and leaving catalog or detail
  pages in a loading state.

## [0.3.2] - 2026-09-13

### Player summary

- Settings let you include mercenaries, Spec-Ops, Team Operations, and Reinforcements,
  and remember your preferences on this device.
- The browser detects app updates more reliably, and optional-unit settings and wiki-link labels
  are consistent across pages.

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

- Settings adapt to different screen sizes, and Army colours make Unit and reference pages
  easier to scan.
- Movement values are displayed correctly, and mobile navigation works more reliably.

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

- A new home page, simpler navigation, and division badges make the site easier to browse.
  Pages also adapt more consistently to smaller screens.

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

- The About page explains what InfinityDB offers, where its data comes from, and that it's
  an independent community project.

### Changed

- Expand the About page with InfinityDB's purpose, local data flow, current reference
  features, future direction, and independent-project disclosures.

## [0.2.0] - 2026-09-11

### Player summary

- Skills, Equipment, and Weapons have searchable pages with links to the Units and loadouts
  that use them.
- Weapon profiles show Ammunition, Traits, ranges, icons, and special rules, and Unit pages show
  more complete profile and loadout details.
- AVA values display correctly, searches handle punctuation, and symbol display is more reliable.

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

- Unit rows open their detail pages, and search ignores differences in case, accents, and
  punctuation. The browser also shows when Army data was downloaded.
- Reinforcements and related profiles are grouped more reliably when their names differ between
  Army Lists.

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

- You can switch between centimetres and inches, look up Skill Modifiers, and choose whether
  to include Reinforcements.
- General profiles show Troop Type and Classification. Equivalent Army Lists are grouped together
  in filters, and profile and loadout tables are easier to read on small screens.

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

- The first release lets you browse Units across Armies and look up their profiles, loadouts,
  Skills, Equipment, Weapons, and availability.
- Unit pages bring shared and Army-specific details together, with symbols and mercenary
  availability.

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
