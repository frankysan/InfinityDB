# InfinityDB backlog

This is the working implementation backlog. Every unchecked item belongs to exactly
one release bucket: **0.8.0**, **0.9.0**, **1.0.0**, or **post-1.0**. The buckets are
planning commitments, not a promise that a minor release cannot move a low-risk item
earlier or defer a non-gating item when evidence changes.

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

The current milestone is **0.8.0 — connected game relationships**. It builds on the
stable 0.7.x rules/context model by making already-modeled structural relationships
directly useful to players: Fireteams, Peripheral/Controller structure, profile/loadout
includes, selection/dependency relationships, Reinforcement parentage, and useful
cross-army navigation.

General performance/storage experiments, major pipeline refactors,
persistent-user-data features, ITS tooling, and native applications are explicitly
post-1.0 unless they become necessary to correct a release-blocking defect.

## Release roadmap through 1.0

- **0.8.x — Connect the game structure.** Finish Fireteams and expose the structural
  relationships already present in the canonical application data.
- **0.9.x — Complete, audit, and polish.** Close remaining player-facing application
  gaps, run the end-to-end consistency audit, improve search/navigation/filtering,
  finish the intended frontend/theme architecture, and harden CI/operations.
- **1.0.0 — Player data-complete.** Close the remaining current rules/reference gaps
  and pass the final source-to-storage-to-browser completeness gate. A full ITS
  scenario library, list builder, and other broader product tooling are not part of
  the 1.0 gate.
- **Post-1.0 — Expand and optimize.** Pursue optional product features, persistent
  user data, ITS/scenario tooling, native apps, historical-data features, pipeline
  refactors, and performance/storage experiments.

The concise public framing remains: **0.6 built the foundation → 0.7 adds context →
0.8 connects the data → 0.9 closes the gaps → 1.0 completes the reference.**

## 0.8.0 — connected game relationships

The completed connected-data domain audit is maintained in
`docs/080-connected-domain-audit.md`. 0.8.0 should make those modeled relationships
directly useful without becoming an Army-list legality engine or live game-state model.

### Fireteams and connected application data

No open implementation items remain in the 0.8.0 connected-data milestone. The maintained
source-presentation and interaction audits have been rerun; their remaining player-facing gaps
are explicitly assigned to later release buckets below.

## 0.9.0 — completeness, consistency, and polish

0.9.0 is the release-hardening pass: close remaining application presentation gaps,
audit semantic consistency end to end, improve navigation and discoverability, and
finish the web/operations work that should be stable before the 1.0 completeness gate.

### Player-facing completeness and navigation

- [ ] Add a global search field spanning **every database domain**. Each result must
  show its domain explicitly and link to the correct domain-specific detail surface,
  so identical or similar names across domains remain unambiguous.

- [ ] Add a simple wiki-like internal-link syntax for **all maintained text fields**.
  A text value should be able to reference another semantic identity inline,
  for example: `Apply the [[skill:speculative-attack]] -6 MOD and Range MODs; other
  negative MODs such as [[skill:mimetism]], [[rule:partial-cover]], and
  [[rule:visibility-zone:plural]] are not applied.` Display-form modifiers such as
  `:plural` should be supported where useful. The exact namespace vocabulary still
  needs design—the example `rule:` namespace is only a placeholder, not an accepted
  ontology decision. Render resolved links with subtle visual emphasis and a
  small summary tooltip/popover so users can inspect the target without leaving the
  current context. Define escaping, unresolved-link validation, plural/display-text
  behavior, accessibility/keyboard interaction, and which semantic identity resolver
  owns each namespace before implementation.
  - Treat dynamic distances as typed inline tokens handled by the same maintained-text
    rendering layer, for example: `a successful Dodge may also move the user up to
    [[distance:2:inch]].` Every distance embedded in a maintained text field must be marked
    structurally rather than stored only as display text so it can render according to the
    user's current cm/in toggle. Reuse the application's canonical distance-conversion and
    formatting policy rather than introducing parser-local conversion rules. The eventual
    migration should inventory existing text fields, convert literal distances to typed
    tokens, and add validation that prevents newly maintained text from silently
    reintroducing unmarked distance literals where they can be detected reliably.

- [ ] Present source-attributed Unit notes, including meaningful variant-specific notes
  that do not belong only to the representative source Unit.

- [ ] Resolve and present the semantics of the 18 current top-level composite
  `unit_options` rather than using their names only for search/catalog support.

- [ ] Review opaque `spectables` and loadout `disabled` / `minis` semantics, then either
  present the in-scope information or document why it is deliberately outside 1.0.

- [ ] Add a rules glossary and profile-notation help layer to unit details.
  - [ ] Explain the existing profile fields and symbols in context: training/order,
    troop type, classification, ISC, Hackable, Peripheral, equipment versus
    BS weapons, melee weapons, and profile/loadout separators. Use tooltips or a
    linked glossary rather than making every profile row denser.
  - [ ] Make terminology such as Trooper, Peripheral, Marker, Token, Deployable,
    Null State, Ally/Enemy/Hostile, and Victory Points discoverable wherever it
    changes how profile data should be read.

- [ ] Improve General profile versus Army-profile stat-difference signposting.
  - [ ] Keep the existing indicator on an Army-profile stat when it differs from
    the General profile.
  - [ ] Also mark the General profile stat with a small superscript `*` and a
    descriptive tooltip whenever one or more Army profiles differ from it.

- [ ] Rich unit filtering: troop type, classification, availability, points,
  SWC, weapons, equipment, skills, and characteristics.

- [ ] Deep-linkable, shareable search and filter state for catalog and unit
  views.

- [ ] Rules-reference cross-links from profiles, loadouts, skills, equipment,
  and traits to their catalog detail pages.

### End-to-end application consistency

- [ ] Perform a systematic end-to-end consistency audit after the canonical-model
  groundwork above is sufficiently established. This remains an audit and bounded
  correctness-fix effort rather than a visual redesign or broad frontend
  restructuring project.
  - [ ] Establish one pinned production audit baseline before inspecting behavior:
    the Git commit, Army snapshot/provenance, generated `infinity.db` and
    `rules.db`, local terminal symbol manifest, and the tracked release-matched
    symbol publication/inventory. Verify that the runtime database and symbol publication derive from the
    same Army snapshot. Record the evidence and audit results in a durable audit
    document (for example, `docs/audits/web-consistency-YYYY-MM.md`); do not mix
    production observations with synthetic test fixtures.
  - [ ] Create and maintain an explicit audit matrix for each concept, recording
    its semantic-provenance category, source meaning/evidence, storage
    representation, derivation or canonical/application interpretation, API
    representation, browser consumers, canonical documentation location, existing
    coverage, and audit result. Cover logical/source unit identity; army hierarchy, role,
    and playability; faction/display identity; optional availability;
    names/slugs; profiles and loadouts; catalog/rules enrichment; distance/range
    semantics; symbols; source/wiki/rules provenance;
    filtering/search/sorting/counts; and deep-link identifiers.
  - [ ] Begin with the army/unit identity and availability vertical slice. Trace
    `main_army_id` and `display_army_id`, faction grouping, role/playability,
    mercenary and reinforcement availability, logical identity, and their unit
    explorer/detail consumers from storage through the API to the browser.
  - [ ] Audit the backend and API contracts before browser presentation. Trace
    generated database rows through the canonical/application model, repository
    queries, and application-level composition (including `SkillCatalog`,
    `TraitCatalog`, and `CatalogRules`) to the JSON API. Add focused contract
    coverage wherever intentional behavior is not sufficiently pinned.
  - [ ] Audit browser semantic ownership. Inventory domain interpretation in
    browser modules, beginning with `unit.js`, the army selector, catalog detail
    modules, symbol lookup, rules links, and optional-unit filtering. Keep display
    formatting in JavaScript, but expose game/data semantics through the backend
    API when duplicate interpretation could disagree. Route JSON API access
    through `api.js` to match the documented boundary; static/HTML fetches are not
    part of that API-transport requirement.
  - [ ] Perform route-by-route parity checks for the Unit explorer and details;
    Fireteams; Skill Modifiers; Skills, Equipment, Weapons, and Traits list/detail pages;
    shared navigation/settings; and version refresh. Compare API output with
    rendered behavior, including filtering, result counts, ordering, labels,
    deep-link state, cross-links, optional-unit behavior, source/rules links,
    catalog-item unit usage, and symbol identity. Use a deliberate manual browser
    pass unless lightweight browser automation is added for a concrete audit need.
  - [x] Verify Fireteam source retention through the canonical application projection
    and first-class repository/API/browser chart surface. Keep the broader consistency
    audit responsible for route/API/render parity rather than reopening Fireteam domain
    modeling that is already tracked in the 0.8 connected-data workstream.
  - [ ] Exercise degraded states deliberately: rules database available versus
    unavailable; asset validation disabled versus required; complete tracked published
    assets versus an intentionally asset-free specialized package/test layout; unknown
    unit/catalog/trait IDs; empty search
    or filter results; invalid query parameters; missing catalog enrichment;
    stale version/snapshot detection; and database/symbol snapshot mismatch.
  - [ ] Verify the supported validation/runtime contexts independently: a normal
    source checkout with the tracked processed publication, a specialized package/test
    layout where the third-party SVG tree is deliberately absent and asset checks are
    disabled or allowed to fall back, local development with explicitly supplied
    generated runtime artifacts, and production deployment that fails closed for
    incomplete or mismatched databases/assets. Passing one context does not establish
    the others.
  - [ ] Fix discovered inconsistencies incrementally and add focused regression
    coverage where practical. Record intentional deferrals in the audit document
    and TODO rather than silently leaving them unresolved. Keep CI hardening,
    unrelated storage experiments, the Changes page, visual theming, and broader
    UI restructuring outside this audit unless required for a minimal correctness
    or 1.0-completeness fix.
  - [ ] Close with a second source-to-storage-to-browser matrix pass, complete
    normal project checks, and full-asset validation against the pinned production
    publication when it is available. Update canonical documentation, `TODO.md`,
    and `CHANGELOG.md` for material findings before starting the later
    visual-design, frontend-architecture, or theming work.

### Frontend architecture and theming

- [ ] Refactor the web layer toward the documented backend/frontend responsibility
  boundary without changing the current same-origin deployment model.
  - [ ] Split API handling, shared page-shell/static delivery, and top-level request
    dispatch into visibly separate Python concerns while preserving existing URLs.
  - [ ] Organize browser code around explicit API transport, preferences/theme
    state, reusable view/components, and page modules; keep JSON API access routed
    through `api.js`.
  - [ ] Add focused contract/regression coverage as responsibilities move so domain
    interpretation cannot silently migrate back into browser code.

- [ ] Implement first-class Light and Dark themes using the semantic theme contract
  documented in `docs/architecture.md`.
  - [ ] Separate semantic theme tokens from theme-neutral layout/component rules
    and remove remaining hard-coded light-theme assumptions.
  - [ ] Decide and document the default startup behavior (for example, operating-
    system preference versus a fixed project default); an explicit user choice wins.
  - [ ] Add the theme selector to Settings, resolve the selected theme before first
    meaningful paint, and keep persistence on the existing preference contract.
  - [ ] Audit contrast and distinguishability for status/range colors, links, focus,
    muted text, tables, dialogs, menus, and faction accents in both themes.
  - [ ] Add regression coverage for initialization, switching, persistence, and
    representative core pages in both themes.

- [ ] Add a project favicon derived from `infinitydb-logo.svg` and keep it legible
  in light and dark browser chrome where practical.

- [ ] Refactor the frontend design-system structure after the theme contract is
  implemented: separate foundational tokens, theme values, shared components/layout,
  and page-specific exceptions where that improves ownership without adding a CSS
  build step. Promote recurring patterns to shared primitives and preserve the
  established shared shell, navigation, detail, table-density, badge, and Settings
  behavior during the migration.

- [ ] Before retiring or redirecting numeric routes, define and implement the
  per-domain slug-freezing, reviewed-override, alias/redirect, and canonical-URL
  compatibility policy documented as future work in `docs/architecture.md`.

### Release hardening, CI, and operations

- [ ] Define a paired-export replacement policy. The frontend and raw archive
  are currently built as temporary siblings; document and test recovery when a
  process stops between replacing either output.

- [ ] Integrate curated snapshot-note validation into routine project checks so
  every checked-in file under `data/curated/snapshot-notes/` is validated even
  when no downloader or comparison workflow happens to load it.

- [ ] Retain release evidence for the configured hosted workflows. Before
  claiming a release has passed hosted CI, record successful `Source checks`,
  `Installed wheel smoke`, and `Deployment smoke test` runs for the release
  commit or tag.

- [ ] Complete optional/manual full-asset CI administration by adding authorized
  `FULL_ASSET_BUNDLE_URL` and `FULL_ASSET_BUNDLE_SHA256` secrets to the existing
  `full-assets` environment, then record one successful manual run.

- [ ] Establish privacy-preserving production monitoring and a repeatable capacity test
  for the Docker deployment.
  - [ ] Record host and container CPU, memory, swap, disk-space/inode, disk-I/O,
    and network utilization; retain Docker restart/OOM events and sanitized Caddy/Gunicorn
    error diagnostics. Alert on sustained CPU saturation, memory pressure or OOM kills,
    low disk space, elevated 5xx responses, and failed health checks.
  - [x] Publish aggregate request counters/histograms using normalized bounded route
    labels: request rate, status class, latency, response size, and active requests. Static
    assets and `/api/` requests remain separately identifiable for future dashboards.
  - [x] Do not collect IP/geolocation, user-agent/fingerprint, referrer, cookie/session/
    preference values, query/search terms, persistent visitor IDs, unique/returning-user
    analytics, or per-user navigation histories. Raw URLs and unbounded request values are
    excluded from metric labels.
  - [x] Disable the routine Gunicorn access-log stream while retaining stderr error logs.
    If raw request logging is temporarily required for a concrete incident, minimize/sanitize
    its fields, restrict access, and define short retention before enabling it.
  - [ ] Define a representative load-test scenario: browse the unit list, search,
    open unit/catalog details, and fetch API endpoints using a current
    production-like SQLite snapshot. Include a warm-cache steady-state run and
    a short burst run; do not benchmark only the health endpoint.
  - [ ] Establish a baseline at 2 Gunicorn workers x 4 threads, then test 4 x 4
    only with a matching 4-vCPU/4-GiB container allocation. Record p50/p95/p99
    latency, request/error rate, CPU, memory, and SQLite/disk behavior at each
    concurrency level.
  - [ ] Set an explicit scale trigger (for example, a sustained p95 latency or
    error-rate SLO breach while CPU is not otherwise constrained). Prefer
    multiple immutable app replicas behind Caddy over unbounded worker growth;
    re-run the test before changing worker counts or deployment resources.

- [ ] Add a benchmark/health-check command that validates the frontend database,
  confirms its expected raw archive when requested, and reports schema and
  compatibility revisions.

- [ ] Split the growing pytest stage into marker-based local sections (for example
  data/model, web/API, build/ingestion, operations/tooling, and assets) so
  developers can run the relevant slice during iteration. Keep the complete suite
  as the authoritative final gate. Parallel pytest execution now defaults to
  `--test-workers auto` after the primary Windows benchmark reduced the 687-test
  stage from 59.67 s serially to 14.13 s; the shared web fixture also no longer
  rebuilds its database per test. Retain marker-based slices as the complementary
  fast-iteration path for focused development.

## 1.0.0 — current-reference completeness gate

1.0.0 is the final completeness release for the supported current reference data. It
should resolve remaining material source/rules gaps and validate the whole application;
it should not introduce a large new product surface.

### Rules and reference completeness

- [ ] **Data processing + Web backend + Web frontend:** Close the remaining versioned
  curated rules-reference gaps for N5 v5.3 using
  `data/pdf/rules/n5-rules-v5-3-en.pdf` (dated 2026-08-10) and other explicitly scoped
  current reference sources.
  - [ ] Expand remaining canonical rule identities across Skills, Equipment,
    Ammunition, Traits, States, Fireteam concepts, glossary terms, and other useful
    rule domains, retaining rulebook version and printed-page citation. Do not
    recreate Hacking Program facts already promoted by the 0.8 connected-data work.
  - [ ] Generate an Orders/AROs declaration matrix from the reconciled cross-domain
    relationships and use it as a completeness check for missing, invalid, or
    contradictory declaration categories rather than maintaining a second hard-coded
    chart. Make the projection source/scope-aware so scenario-only Skills/AROs can be
    represented without appearing in the core N5 matrix or being flagged as missing
    core categories.
  - [ ] Model Ammunition rules as first-class cited identities and relationships.
    Distinguish the eleven base Ammunition types from source-defined combined
    forms, preserve component relationships for combined Ammunition, and keep
    Ammunition composition separate from Combined Saving Roll notation. Link
    state/Attribute/Saving-Roll effects explicitly instead of deriving them from
    Ammunition display names.
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
    load-order semantics. This catalog coverage is in scope for 1.0; a complete
    scenario library and scenario list/detail pages are not.
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
  - [ ] Add richer typed/cross-linked projections for the structured Martial Arts,
    Booty, and MetaChemistry reference rows now served in 0.7.0. Keep random outcomes
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
  fixed development host. A 2026-09-14 generated-snapshot smoke export measured
  8.45 seconds, 13.4 MB for the frontend DB, and 37.7 MB for the raw archive;
  treat those numbers as provisional until repeated in a controlled environment.

- [ ] Remove redundant whole-document work in the combined build/export path.
  Export validation serializes the complete normalized object to reject invalid
  JSON, while the raw archive serializes every row again and normalization has
  already run `validate_normalized`. Consider a hash-attested validation report
  or an in-memory hand-off that skips only the duplicate build-path pass; the
  standalone `export` command must retain full untrusted-input validation.

- [ ] Evaluate artifact-level deduplication for development builds. The raw
  archive contains 24.9 MB of row JSON, nearly the 25.2 MB normalized input,
  so retaining `normalized.json` and `infinity.raw.db` duplicates the same
  lossless data. Decide whether post-export development workflows need both,
  or document one as a regenerable/transient artifact.

- [ ] Provide a small development CLI for `infinity.raw.db`: inspect a raw row,
  list raw rows by normalized table, and verify that an archive matches its
  frontend sibling's metadata.

- [ ] Add database-size reporting to `infinity-db build` so snapshot growth is
  visible in build output and CI.

### Army snapshot and symbol-pipeline maintenance

Milestone 1 acceptance for the integrated pipeline is complete. The remaining work is
maintenance, refactoring, richer diagnostics, incremental performance, and broader
portability coverage rather than a prerequisite for the 1.0 application-data gate.

- [ ] Let future snapshot-comparison tooling write structured generated diff
  data/reports under manifest/report paths while curated snapshot notes remain
  the human interpretation of those results.

- [ ] Refactor stage scripts into thin CLIs over reusable Python functions and a
  small shared symbol-pipeline utility layer.
  - [ ] Make the symbol-downloader input contract match its CLI and tests. Prefer
    the immutable raw Army ZIP as the authoritative input; either fully support
    directory/current merged-master inputs end to end or stop advertising them.
    In particular, do not claim legacy/current `master.json` compatibility unless
    discovery can consume that schema without treating ordinary embedded SVG
    references as unknown fields.
  - [ ] `svg_processor.py`: keep font audit, alias normalization, complete-set
    duplicate detection, deterministic representative ranking, persistent
    Inkscape conversion, and reports. Duplicate/canonical and text-conversion
    state are integrated into the build manifest; multi-category processing
    beyond the current canonical flow remains.
  - [ ] `path_sanitization.py`: remain shared infrastructure for external/mirror
    naming; pipeline-generated asset names should use one host-independent
    policy.
  - [ ] Longer-term reusable modules may be split into `snapshot`, `discovery`,
    `manifest`, `downloader`, `audit`, `deduplicate`, `convert`, `compress`, and
    `publish` helpers when that reduces duplication rather than adding ceremony.

- [ ] Make every integrated symbol stage idempotent and traceable before adding
  sophisticated incremental caching.
  - [ ] Changes to an override SHA-256 invalidate downstream processing for that
    asset. Removing an override falls back to validated symbol archives/cache or
    network by the normal resolution rules.
  - [ ] After the integrated build is stable, consider cache keys based on snapshot
    SHA-256, source SVG SHA-256, processor/tool versions, font-alias config,
    duplicate renderer/settings, conversion backend/settings, and compression
    profile/settings.

- [ ] Standardize symbol-pipeline reports around detailed machine/human outputs
  plus one concise build summary.
  - [ ] Preserve/report discovery counts, unknown SVG references, font audit,
    missing fonts, unused font declarations, SVG parse errors, duplicate groups,
    duplicate-render errors/separation/summary, text-to-path results/summary,
    compression report/candidates/run metadata, overrides used/unused, raw-cache
    hits, network downloads, manual static assets, canonical counts, published
    asset counts, application-mapping counts, and per-stage/total runtime.
  - [ ] Existing report filenames from the plan may be retained where useful:
    `symbol-discovery.csv`, `unknown-svg-references.csv`, `svg-font-report.csv`,
    `missing-fonts.csv`, `unused-font-declarations.csv`, `svg-parse-errors.csv`,
    `duplicate-groups.csv`, `duplicate-render-errors.csv`,
    `duplicate-separation.csv`, `duplicate-summary.csv`,
    `svg-text-to-path-report.csv`, `text-conversion-summary.csv`,
    `compression-report.csv`, `compression-candidates.csv`, and
    `compression-run.json`.

- [ ] Add focused end-to-end and cross-platform regression coverage for the
  integrated Army/symbol pipeline.
  - [ ] Snapshot/discovery tests: metadata/faction validation, complete archive,
    snapshot identity/hash, all profile/faction logos, multiple logos for one
    unit, one logo shared by units, duplicate URLs, static declarations,
    override suppression of network, override over cache, invalid/unused
    overrides, filename collisions, unexpected SVG fields, and proof that
    `resume` is not required for complete discovery.
  - [ ] SVG fixtures: exact duplicate, XML-different visual duplicate, no-text,
    normal text, alias-font, missing-font, empty-text cleanup, and troublesome
    real-world conversion cases.
  - [ ] Run core portability coverage on Windows, Ubuntu/Linux, and macOS when CI
    permits: project-relative path generation, path sanitization, executable
    discovery including `.exe`/`.cmd`, subprocess argument construction without
    shell quoting, temp files, case-only collisions, snapshot ZIP handling,
    override lookup, static-symbol manifest loading, atomic replacement, and
    Windows `spawn` compatibility. External-tool integration tests may be
    conditional when Inkscape, `resvg`, or SVGO are unavailable.
  - [ ] Add a shared utility layer for executable discovery, native/project-relative
    path conversion, atomic writes, subprocess invocation, and platform-neutral
    generated filenames before orchestration otherwise duplicates those rules.

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

- [ ] Add ITS scenario list and detail pages backed by a curated seasonal data
  model, rather than PDF excerpts.
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
