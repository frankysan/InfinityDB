# InfinityDB backlog

This is the working implementation backlog. Every unchecked item belongs to exactly
one release bucket: **0.10.0**, **1.0.0**, or **post-1.0**.
The buckets are planning commitments, not a promise that a minor release cannot move a
low-risk item earlier or defer a non-gating item when evidence changes.

This file does not define current application behavior. Current behavior belongs in
the relevant reference documentation; lasting design direction belongs in
`docs/architecture.md` or `docs/data-model.md`; durable release acceptance criteria
belong in `docs/releasing.md`.

Keep completed substeps while their parent task is still open because they clarify
progress and remaining scope. Once a standalone or parent task is complete, remove it
after any durable outcome is recorded in `CHANGELOG.md`, architecture/data-model
documentation, or another appropriate reference. Git history retains implementation
detail. New or materially revised work items use the canonical project-domain labels
defined in `docs/project-domains.md`; section-level domain declarations may be used
when all contained work shares the same owner.

## Current milestone

The current milestone is **0.10.0 — consistency, presentation, and release hardening**.
It follows the completed 0.9.0 application-completeness/discoverability milestone by auditing the
finished application model end to end, establishing the scenario architecture, completing the
frontend/theme architecture, and hardening release and operations workflows before the 1.0
data-completeness gate.

General performance/storage experiments, major pipeline refactors,
persistent-user-data features, ITS season/tournament tooling, and native applications are explicitly
post-1.0 unless they become necessary to correct a release-blocking defect. Core-rules scenarios are
part of the 1.0 completeness target; their architecture is now established for later 1.0
implementation without adding the full scenario surface to 0.10.0.

The public roadmap summary lives in `README.md`; the durable 1.0 acceptance
definition lives in `docs/releasing.md`. The sections below record the candidate's completed
version-specific gates and implementation work that remains open for later releases.

## 0.10.0 — consistency, presentation, and release hardening

**Project domains:** Web frontend, Deployment, Project infrastructure

Implementation and version-specific manual acceptance are complete. Merge, exact-release-commit
hosted validation, tagging, and publication follow [the release checklist](releasing.md).

- [x] Complete the application consistency, scenario architecture, frontend/theme, and
  release/operations hardening work recorded in the 0.10.0 changelog.
- [x] Complete the full-assets candidate gate: `Full-asset checks` passed for
  `7f58d1387f2478aad6650e0311729083c7739800` on 2026-10-07
  ([run 37579009400](https://github.com/frankysan/InfinityDB/actions/runs/37579009400)).
  This closes environment/bundle administration and pre-merge acceptance; a different final release
  SHA still needs its own run when collecting optional full-assets release evidence.
- [x] Complete capacity/load testing, the matched 2x4 versus 4x4 experiment, and the production
  scale-review policy. The retained results, resource boundaries, commands, and scale trigger remain
  in [deployment guidance](deployment.md#repeatable-http-capacity-scenario) and
  [testing guidance](testing.md#benchmark-tooling); production still defaults to 2x4.
- [x] Complete Silhouette manual browser acceptance. The maintainer confirmed on 2026-10-07 that
  the [manual checks](testing.md#silhouette-manual-browser-acceptance) were performed and passed.

## 1.0.0 — current-reference completeness gate

1.0.0 is the final completeness release for the supported current reference data. It
should resolve remaining material source/rules gaps, add the bounded core-scenario reference
surface, and validate the whole application without expanding into broader ITS/tournament tooling.

### Rules and reference completeness

- [ ] **Data processing + Web backend + Web frontend:** Close the remaining versioned
  curated rules-reference gaps for N5 v5.3 using
  `data/pdf/rules/n5-rules-v5-3-en.pdf` (dated 2026-08-10) and other explicitly scoped
  current reference sources.
  - [ ] Expand remaining canonical rule identities across Skills, Equipment,
    Ammunition, Traits, States, Fireteam concepts, glossary terms, and other useful
    rule domains, retaining rulebook version and printed-page citation. Do not
    duplicate Hacking Program facts already owned by the current Hacking Program
    domain.
  - [ ] Generate an Orders/AROs declaration matrix from the reconciled cross-domain
    relationships and use it as a completeness check for missing, invalid, or
    contradictory declaration categories rather than maintaining a second hard-coded
    chart. Make the projection source/scope-aware so scenario-only Skills/AROs can be
    represented without appearing in the core N5 matrix or being flagged as missing
    core categories.
  - [ ] Deepen the existing first-class Ammunition model with explicit typed
    relationships. Preserve the eleven published base Ammunition identities, distinguish
    source-defined combined forms, preserve component relationships for Combined
    Ammunition, and keep Ammunition composition separate from Combined Saving Roll
    notation. Link State, Attribute, and Saving-Roll effects explicitly instead of
    deriving them from display names.
  - [ ] Include scenario-defined catalog concepts needed for the general rules
    reference, including scenario-only Skills, Equipment when present, contextual
    roles such as Specialist Troop, and the scenario elements those concepts act
    on. Preserve scenario/season scope and keep temporary effects out of static
    Unit/Profile facts. Include the scoped action identities surfaced by the
    current ITS FAQ where their owning scenarios classify them as Skills/AROs,
    including `Activate Communication Antenna`, `Oppose Activation`, and `Emit
    Akial Interference`. Keep semantic identity, source publication provenance, and
    applicability separate so the same canonical concept can be cited or overlaid
    by core, scenario, FAQ, or season material without duplication or collection-
    load-order semantics. This catalog coverage is in scope for 1.0 and should share
    identities/scope with the core-scenario model rather than becoming a parallel representation.
  - [ ] Add the official Reinforcements Extra as a separately versioned/scoped
    annex source rather than folding it into `n5-core-rules`. Curate `Commlink`
    and `Request Reinforcements`, link the capability they create to the annex
    scope, and retain the ordinary-Army -> Reinforcement Section/pool context.
    - [ ] Encode `Commlink (+X)` as a typed maximum-Trooper-count parameter, not a
      Skill Level or Attribute MOD.
    - [ ] Extend declaration-category validation so phase-scoped actions such as
      `Request Reinforcements` can be explicitly classified outside Basic Short/
      Short/Long/ARO instead of being treated as incomplete or assigned a false
      category.

- [ ] **Data processing + Web backend + Web frontend:** Add the current core-rules
  scenarios as a first-class, browsable scenario domain for 1.0, using the model derived
  from the 0.10.0 core/ITS comparison.
  - [ ] Maintain structured, cited scenario data sufficient to understand setup, objectives,
    scoring, deployment, special rules/elements, and end conditions without relying on an
    unstructured PDF excerpt as the application model.
  - [ ] Keep the model source/scope-aware and extensible to versioned ITS seasons, but do
    not make ITS scenario content, tournament/event tooling, or a deployment-map editor a
    1.0 requirement.
  - [ ] Provide usable scenario list/detail presentation and links to existing canonical
    rule/catalog entities where identities overlap.

- [ ] Add a dated FAQ/errata layer to the existing rules-reference system from
  current material under `data/pdf/faq/`.
  - [ ] Model each ruling as a question, concise answer, rule/topic links,
    applicable scope, document version/date, and source-page citation; do not
    flatten it into the base-rule summary. This preserves the distinction
    between a rule and a later clarification, and permits an answer to be
    superseded cleanly.
    - [ ] Give each ruling a canonical identity independent of wiki page
      placement. Store the original FAQ publication version/date separately from
      current rules/ITS-season/scenario applicability so cross-posted or
      carried-forward rulings are linked rather than duplicated.
  - [ ] Prioritize links to features already represented by the app: deployment
    and private-information handling; BS Attack/MOD and template behavior;
    hacking Firewall; Marker, Camouflage, Peripheral, and State interactions;
    Coordinated Orders; and Fireteam creation/bonuses/integrity. The FAQ also
    contains scenario-specific rulings, so scope them to the relevant ITS
    season and mission rather than presenting them as universal core rules.
  - [ ] Define an explicit source-precedence and effective-date policy. An on-screen
    answer must show its source date/version and never silently blend conflicting
    documents.

- [ ] **Data processing + Web backend + Web frontend:** Extend generated rules-reference
  projections that build on the enriched canonical data rather than duplicating its facts.
  - [ ] Add richer typed/cross-linked projections for the existing structured Martial Arts,
    Booty, and MetaChemistry reference rows. Keep random outcomes
    as deployment/session overlays, preserve conditional branches (for example TAG
    versus other Troop Types), and cross-link resolvable outcomes to canonical Skills,
    Equipment, Weapons, and Attributes without rewriting Unit profiles.
  - [ ] Add a generated cross-army rule-variant usage index once exact variant
    semantics are reconciled: canonical Skill/Equipment -> Level/MOD/typed parameter
    variant -> Unit/profile/loadout occurrences. Derive it from canonical rules and
    Army occurrence relationships rather than maintaining a second classification.
  - [ ] Model the finite V5.3 Restrictions Chart as explicit cross-domain
    relationships (Troop Type/Training/Equipment/Skill -> restricted action or
    Lieutenant eligibility) and expose it as contextual help/generated reference.
    Do not generalize this into a full live-game action-legality engine.

- [ ] Extend the completed Game States reference catalog with any remaining contextual
  state links needed by later Fireteam, Hacking, weapon/ammunition, and scenario guidance;
  do not infer a Unit's current in-game State from its static Army profile.

- [ ] Add a weapon-and-ammunition quick-reference view built from existing
  weapon profiles plus curated rules data.
  - [ ] Normalize display of multi-mode/multi-ammunition profiles, link ammunition
    names and traits to their effects, and provide a unit-neutral
    comparison/filter view. Preserve the field-specific meaning of `+`: Ammunition
    composition and Combined Saving Rolls are separate rules operations. Validate
    the view against Army metadata; do not copy source charts wholesale into the
    application.
  - [ ] Add a generated Deployables profile reference from Weapon/Equipment
    metadata plus curated corrections: ARM/BTS/STR/S for the deployed object,
    originating item/rule, and reverse Unit/loadout uses. Keep deployed-object
    identity separate from the carrier and from catalog domain. Track the V5.3
    Armed Turret S2 detailed-profile versus S1 quick-reference conflict explicitly
    and do not silently choose the summary value without reviewed precedence.

- [ ] Add a curated Infinity Wiki URL mapping for traits when authoritative
  links are available.

### Final 1.0 acceptance

- [ ] **Data processing + Web backend + Web frontend + Project infrastructure:**
  Execute the final 1.0 source-to-storage-to-browser completeness gate defined by
  `docs/releasing.md` against pinned current Army, rules, wiki, database, and symbol
  inputs. Resolve every material in-scope gap or document an explicit exclusion with
  rationale, then complete normal project checks, hosted release checks, and
  full-asset validation before tagging 1.0.0.

## Post-1.0 — maintenance and product expansion

These items are intentionally outside the 1.0 completeness gate. They may move earlier
only when required to fix correctness, reproducibility, or release reliability.

### List and session configuration

- [ ] **Data processing + Web backend + Web frontend:** Model Spec-Ops/Team-Ops
  `spectables` as structured configurable list/session data, preserving the distinction
  between a Unit's base reference profile, a player's selected upgrades, and later
  in-game profile transitions. Do not attach selected choices to the replaceable Army
  snapshot or present the complete chart as immutable Unit detail.

- [ ] **Data processing + Web backend + Web frontend:** Revisit loadout `disabled` and
  `minis` only when a reviewed source contract or roster-builder use establishes their
  player-facing meaning. Until then retain the source values without inferring either
  current availability or a miniature-count rule.

### Routing and long-term compatibility

- [ ] Before retiring or redirecting numeric routes, define and implement a
  per-domain slug-freezing, reviewed-override, alias/redirect, and canonical-URL
  compatibility policy. Until then, preserve the current contract: canonical generated
  links prefer stable domain slugs while numeric routes remain accepted compatibility forms.

### Performance, storage, and build tooling

- [ ] Benchmark cold and warm requests per worker for unit lists, unit details,
  skills, equipment, and weapons. Record median and p95 timings against a
  representative snapshot before and after each performance change.

- [ ] Evaluate SQLite `immutable=1` for deployed snapshots. Enable it only when
  the process never observes an in-place database replacement.

- [ ] Compare otherwise equivalent deployment variants backed by SQLite and by
  `normalized.json`, with both variants exposing the same API and representative
  load scenario. Define the JSON variant's startup parsing, indexing, and caching
  semantics before interpreting performance results so the comparison measures
  runtime data models rather than repeated JSON parsing. Evaluate both request
  performance and deployment portability/multi-platform suitability before
  deciding whether a storage/query abstraction is justified.

- [ ] Establish a reproducible build/export performance baseline on CI or a
  fixed development host. Record the exact source snapshot, toolchain, generated artifact
  sizes, and timing methodology with each result instead of carrying provisional benchmark
  numbers in the backlog.

- [ ] Remove redundant whole-document work in the combined build/export path.
  Export validation serializes the complete normalized object to reject invalid
  JSON, while the raw archive serializes every row again and normalization has
  already run `validate_normalized`. Consider a hash-attested validation report
  or an in-memory hand-off that skips only the duplicate build-path pass; the
  standalone `export` command must retain full untrusted-input validation.

- [ ] Evaluate artifact-level deduplication for development builds. `normalized.json` and
  `infinity.raw.db` intentionally retain overlapping lossless source structure today; measure
  the duplication on a controlled build, then decide whether post-export workflows need both
  or whether one should be documented as a regenerable/transient artifact.

- [ ] Provide a small development CLI for `infinity.raw.db`: inspect a raw row,
  list raw rows by normalized table, and verify that an archive matches its
  application sibling's metadata.

- [ ] Add database-size reporting to `infinity-db build` so snapshot growth is
  visible in build output and CI.

### Army snapshot and symbol-pipeline maintenance

Milestone 1 acceptance for the integrated pipeline is complete. Immutable-input acquisition,
verified resumable checkpoints, deterministic canonical processing, transaction-safe publication,
and release-bound symbol provenance are established. Remaining work is maintenance, selective
refactoring, richer diagnostics/performance work, and broader portability coverage rather than a
prerequisite for the 1.0 application-data gate.

- [ ] Let future snapshot-comparison tooling write structured generated diff
  data/reports under manifest/report paths while curated snapshot notes remain
  the human interpretation of those results.

- [ ] Refactor legacy/standalone stage CLIs around the integrated pipeline only where doing so
  removes duplicated contracts or platform handling.
  - [ ] Resolve the standalone symbol-downloader input mismatch. The maintained integrated build
    requires an immutable raw Army ZIP, while the downloader help still advertises discovery-only
    directory/master inputs that are not supported consistently end to end. Either implement that
    discovery-only contract deliberately or remove it from the CLI/documentation.
  - [ ] Consolidate shared executable discovery, native/project-relative path conversion, atomic
    writes, and subprocess invocation where conversion/compression/orchestration still duplicate
    those rules.
  - [ ] Split additional `snapshot`, `discovery`, `manifest`, `downloader`, `audit`, `deduplicate`,
    `convert`, `compress`, or `publish` helpers only when the split reduces duplication rather than
    adding ceremony.

- [ ] Evaluate content-addressed incremental reuse only after measuring the current full rebuild.
  If worthwhile, derive cache keys from the pinned snapshot/source SVG hashes plus processor/tool
  versions, font-alias configuration, duplicate-render settings, conversion settings, and
  compression profile/settings. Do not weaken the current manifest/hash validation or immutable
  raw-symbol snapshot boundary to gain incremental speed.

- [ ] Finish symbol-pipeline reporting for machine-to-machine comparison.
  - [x] Persist the detailed acquisition/source counts, SVG preflight, font audit, duplicate
    detection, text-conversion, compression, publication mapping/change data, override usage, and
    cache/network provenance while keeping the interactive console concise and the verbose build
    log complete.
  - [ ] Add one compact machine-readable build-summary artifact with per-stage and total runtime so
    repeated builds can be compared without scraping the verbose log or individual reports.
  - [ ] Add separate discovery/unknown-reference CSV outputs only if future audit tooling needs
    row-oriented data beyond the build manifest and current JSON/CSV stage reports.

- [ ] Extend the remaining regression and portability coverage for the integrated Army/symbol
  pipeline.
  - [x] Cover pinned snapshot/provenance validation, complete Unit/profile/faction discovery,
    multiple/shared/duplicate URLs, static declarations, category-safe filename collisions,
    override precedence and upstream-equivalent propagation, conflicting/invalid/unused overrides,
    validated cache reuse, refresh behavior, and unavailable-source handling.
  - [x] Cover verified materialization/resume behavior, persisted failed audits, exact-first visual
    deduplication and deterministic representative ranking, text-conversion failure preservation,
    compression/report binding, publication collision detection, removed-symbol backups, and
    transactional publication rollback.
  - [x] Cover semantic publication cases for Unit/Profile fallback, distinct General-profile
    artwork, Reinforcement aliases, Peripheral-only and mixed-role identities, contextual
    Peripheral variants, parent-Unit artwork reuse, and cross-Unit profile-symbol consensus.
  - [ ] Add explicit fixtures for empty-text cleanup and a small set of troublesome real-world SVG
    conversion cases that should remain stable across tool upgrades.
  - [ ] Run core portability coverage on Windows, Ubuntu/Linux, and macOS when CI permits,
    especially executable discovery (`.exe`/`.cmd`), subprocess argument construction, temp files,
    case-only collisions, snapshot ZIP handling, atomic replacement, and Windows `spawn` behavior.
    External-tool integration tests may remain conditional when Inkscape, `resvg`, or SVGO are
    unavailable.

### ITS, scenarios, and game tools

- [ ] Build a versioned ITS reference library from material under
  `data/pdf/its/` and `data/pdf/legacy/`, keeping the current season distinct
  from archived seasons.
  - [ ] Keep season content isolated by season and effective date. A user choosing
    a prior event must see its matching scenario, objectives, extras, and FAQ
    rulings rather than a mixture of seasons. Retain a curated, human-reviewed
    change log/diff rather than relying on raw PDF text diffing.
  - [ ] Treat the official Army app/site as the authority for army-list legality.
    InfinityDB may provide read-only explanation and planning support, but must
    label its snapshot/date and avoid claiming tournament validation.

- [ ] Extend the 1.0 scenario domain with ITS scenario list/detail coverage backed by
  curated seasonal data, rather than creating a separate ITS-only model or using PDF excerpts.
  - [ ] Capture structured, cited scenario facts: objectives and scoring, game
    rounds/end conditions, force/point/SWC/table/deployment configuration,
    deployment map or geometry, exclusion zones, token types/diameters,
    classified-objective setup, reinforcement suitability, tactical-support
    options, and scenario-specific rules/elements.
  - [ ] Scenario pages should expose the selected season prominently and link
    season-specific terms to the relevant rules/state references.

- [ ] **Data processing + Web frontend:** Add a deployment-map SVG
  generator for scenario maps. The first iteration should accept a validated JSON map
  definition and generate deterministic SVGs for the three officially supported table-size
  presets: **24×32 in, 32×48 in, and 48×48 in**. Treat inches as the canonical geometry unit
  in the schema rather than rounding dimensions to nominal feet. Keep the renderer itself
  dimension-agnostic so historical, future, and scenario-specific formats do not require
  renderer changes.
  - [ ] Define a flexible coordinate/geometry model with absolute and relative anchors to
    table edges, center lines, other objects, and repeated/mirrored placements; allow
    per-table-size overrides where geometry genuinely differs rather than scaling blindly.
  - [ ] Support layered map primitives for Deployment Zones, Exclusion/Hazard/Scoring areas,
    center or dividing lines, rectangular and circular regions, access/opening lines, objective
    markers and scenery elements, labels, measurements, player-side/Attacker/Defender context,
    legends, and scenario-specific icons. Styling should support fills, opacity, strokes, hatching,
    symbols, and reusable semantic styles without baking one ITS season's artwork into the schema.
  - [ ] Research current and archived ITS scenario maps before freezing the schema. Cover examples
    with changing Deployment Zone depths, central Exclusion Zones, hazardous areas such as
    Biotechvore regions, exact Console/Server placements, asymmetric roles, and maps containing
    special access lines or scenario-specific objective markers. Preserve season/scenario source
    provenance for any definitions derived from official material.
  - [ ] Validate generated geometry and metadata deterministically: table bounds, dimensions,
    required references/anchors, stable element order/IDs, reproducible SVG bytes where practical,
    and readable output at print and screen sizes. Keep the JSON schema versioned so map
    definitions can evolve without silently changing old output.
  - [ ] Later, build a web-based editor/preview UI over the same schema and rendering engine rather
    than creating a separate browser-only map format.

- [ ] **Web backend + Web frontend:** Add an interactive Fireteam builder within a
  selected Army context. Build compositions from the canonical Fireteam projection and general
  Fireteam-rule facts rather than duplicating chart logic in the client.
  - [ ] Enforce Fireteam-local requirements and limits while composing a team: chart type,
    minimum/maximum counts, required choices, FTO eligibility, Wildcards, equivalence/alias
    semantics, and any other reviewed Army-local constraints represented by the canonical model.
  - [ ] Resolve the resulting Fireteam type and Level, then show the applicable bonuses from the
    same canonical Fireteam Level data used by the reference UI. Explain incomplete or invalid
    compositions in terms of the specific local requirement that is not satisfied.
  - [ ] Keep the tool narrower than a full Army-list legality engine. Unit availability and
    Fireteam composition must come from InfinityDB's maintained snapshot, while the official Army
    app/site remains authoritative for complete list legality.

- [ ] Add mission-aware list capability guidance once saved-list support exists.
  - [ ] Derive a transparent checklist from the selected ITS scenario and the
    imported profile data: ITS Specialist Troops, relevant equipment/skills,
    Reinforcement or Team-Ops constraints, and scenario interactions. Explain
    missing capabilities without declaring a list illegal or strategically
    inadequate.
  - [ ] Keep temporary scenario-granted skills, designated Troopers, classified
    cards, tactical support, and private information out of static unit
    profiles. They belong to a per-game/session layer, which is not yet part of
    InfinityDB's replaceable imported snapshot.

- [ ] Provide an optional ITS organizer/event companion only after
  user-authored persistent storage and migrations are established.
  - [ ] Support season-aware event setup: published scenarios, allowed extras,
    player count/round guidance, pairings, byes, score entry, and a printable
    control-sheet checklist. Do not infer an official ranking submission or
    replace the Online Tournament Manager.
  - [ ] Include setup aids from ITS documents while keeping organizer choices and
    local participant data clearly separate from official records.

- [ ] Add optional play-aid pages for core procedures, distinct from the unit
  database: order expenditure/ARO sequence, modifiers, movement/combat
  resolution, command tokens, and Fireteam quick reference. Use concise cited
  checklists rather than source excerpts.

### Native applications

- [ ] **Project infrastructure + Web frontend:** Evaluate adapting InfinityDB into
  native stand-alone Android and iOS applications. Compare BeeWare/Toga, Kivy, and other suitable
  Python-capable or cross-platform frameworks before committing to an implementation.
  - [ ] Evaluate candidates against InfinityDB-specific requirements: reuse of Python domain/data
    logic, local/offline SQLite snapshots and rules data, UI/navigation reuse versus rewrite,
    performance and startup cost, accessibility, platform-native integration, persistent storage,
    snapshot/update delivery, package size, signing/store distribution, and CI/release burden.
  - [ ] Build a small read-only proof of concept for at least one representative workflow (for
    example Unit or Fireteam browsing) before choosing a framework, and record which existing web
    assumptions would need to be separated into shared application services.
  - [ ] If a native-client direction is accepted, keep the canonical data/rules artifacts and
    semantics shared with the web application rather than creating a second interpretation layer;
    revisit the project-domain taxonomy if a permanent native-frontend domain becomes warranted.

### Persistent user data and broader product features

- [ ] Establish a migration policy for future persistent user-authored data;
  imported snapshots are intentionally replaced wholesale today.

- [ ] When a saved army-list builder is introduced, use the rules reference to
  add game-mode and list-review guidance—not hidden-information disclosure.
  Keep any share/export view privacy-aware and treat the Army app/data as
  authoritative for list legality.

- [ ] Create a unit-model image repository.

- [ ] Add a per-user model-collection tracker.

- [ ] Saved army lists, favourites, and personal notes stored separately from
  the replaceable imported snapshot.

- [ ] Unit comparison view for profiles, loadouts, weapons, skills, and
  equipment across selected units or armies.

- [ ] Army-list builder/export integration once user-authored data storage and
  migrations are established.

- [ ] Data-review screens in Developer mode: normalization warnings, source
  record links through `infinity.raw.db`, and unresolved placeholder records.

- [ ] Low priority: provide access to prior imported-data versions when JSON
  source files change. Existing archived JSON ZIP files and Army snapshots are
  sufficient for recovery until this is needed.

- [ ] Low priority: add a JSON-snapshot comparison page showing added, removed,
  and updated data between two snapshots.

- [ ] Low priority: optionally highlight added, removed, and updated data
  elsewhere in the application when comparing snapshots.
