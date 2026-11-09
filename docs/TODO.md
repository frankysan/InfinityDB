# InfinityDB backlog

This file tracks unfinished development work, including maintenance, research
and product expansion. Merge, exact-main-SHA CI, tagging, deployment and
post-deployment verification belong to the [release checklist](releasing.md),
not to the development backlog.

This file does not define current application behavior. Current behavior belongs in
the relevant reference documentation; lasting design direction belongs in
`docs/architecture.md` or `docs/data-model.md`; durable release acceptance criteria
belong in `docs/releasing.md`.

Follow [backlog completion and retirement](README.md#backlog-completion-and-retirement).
A checkmark means the entire task subtree, required validation and documentation
handoff are complete. Remove finished entries; retain only brief linked context
for an open parent. Reopen affected tasks and checked ancestors before adding
work. Deferred test design/execution belongs in the [validation queue](validation-queue.md);
required pending acceptance keeps its owning task open.
New or materially revised work items use the canonical project-domain labels
defined in `docs/project-domains.md`; section-level domain declarations may be used
when all contained work shares the same owner.

## Active development

### Major simplification and restructuring

**Project domains:** Project infrastructure, Data processing, Acquisition, Web backend, Web frontend, Deployment

- [ ] Execute P2–P6 of the [phased restructuring plan](restructuring-plan.md).
  P0 workflow simplification and P1 dependency/tool discovery are complete;
  current-format shared validation and opt-in offline complete builds with
  input provenance are available in the [data lifecycle](../data/README.md).
  Complete builds embed exact variant usage, reviewed Weapon-profile
  citations, the Restrictions chart, Trait Wiki links, Combined Saving
  Roll annotations, Ammunition links and 12 reviewed Weapon Properties
  in Rules v17, plus two Cube characteristic encodings in Army v27.
  The opt-in two-file set has local source-build and API parity checks;
  migrate P2.4's remaining four maintained Army JSON datasets and
  symbol path mappings.
  Final default/serving integration and platform acceptance remain under
  P2.6–P2.8. Keep current serving
  functional until the deliberate cutover. The plan owns ordering, decisions and exit criteria;
  do not copy its complete roadmap into a second task ledger.

### External source clarifications

**Project domain:** Data processing

- [ ] Prepare and submit consolidated publisher questions from the
  [SRC register](official-source-clarifications.md), including
  SRC-002 and SRC-030; record dated official responses under their
  stable IDs and open implementation tasks only when needed.
  Preserve unresolved uncertainty in player-facing material until
  authoritative clarification is available.
- [ ] **Optional comprehensive source reconciliation:** Expand the historical
  source-family planner and clause-disposition evidence when useful. Inventory
  additional official PDF/Wiki/Army source concepts and language/revision
  discrepancies, review uncataloged clauses and decide whether any discovered
  facts should enter the maintained reference. Retain reproducible source
  evidence without treating every unreviewed page or unresolved SRC issue as
  an implementation requirement.

### Source notation and rule references

- [ ] **Data processing + Web frontend:** Give Weapon Chart footnote markers
  (such as `[*]`, `[**]`, `[***]`) contextual, clickable rule references instead
  of treating them as ordinary Traits. Use the published chart legend to identify
  the section category (Weaponry, Ammunition, or Skills and Equipment), then
  resolve the actual target by source publication, chart row/mode, and owning
  rule section (e.g. Mines or Sepsitor), preserving any mismatched
  notation from Army and the PDF. Consider tooltips or short explanations and
  a direct Glossary/rules link; retain raw provenance and explicit unresolved
  mappings.

### Per-reference change history

- [ ] **Data processing + Web backend + Web frontend:** Add optional
  **historical FAQ edition replay and source-date/season selection**,
  separate from the current-reference API. Independently curate
  v0.0-selected historical ruling contributions and evidence for
  compatibility with the appropriate historical N5 revision(s);
  validate historical topic/Scenario identities, effective windows,
  supersession, source authority and unresolved ITS boundaries.
  Preserve stable FAQ identities and original citations without
  replacing current v0.1 selection, backdating it, or interpreting
  announcement/PDF creation dates as verified publication days.
  Add browser controls only after a trustworthy historical read
  model exists; ambiguous dates must remain visibly qualified.
  See the [current FAQ contract](data-model.md#dated-faqerrata-layer-published-reviewed-subset).

- [ ] **Data processing + Web backend + Web frontend:** Show a change-history
  marker/notice on each updated Rule, Skill, Weapon, Unit/profile, and other
  applicable reference entity, linking to a player-readable explanation of
  **when** it changed, **what** changed (before/after), and **why** where an
  authoritative source documents the reason. Resolve changes by stable entity
  identity and publication/version; include an effective date only when known.
  - [ ] Derive reviewed change events by comparing versioned N5 Army snapshots,
    rules/FAQ PDFs, exact Wiki revisions, and official Corvus Belli update posts.
    Keep precise source citations and distinguish changed gameplay semantics from
    editorial wording, source-format changes, and unresolved source conflicts.
  - [ ] Present concise change badges on affected detail pages, with accessible
    explanations and links to evidence/history; do not mark unchanged records or
    claim an inferred motivation as an official reason. Explicitly indicate when
    the reason or effective date is unknown.
  Preserve multiple successive changes and supersession without overwriting
  earlier events or conflating history with current canonical facts.

### List and session configuration

- [ ] **Data processing + Web backend + Web frontend:** Model Spec-Ops/Team-Ops
  `spectables` as structured configurable list/session data, preserving the distinction
  between a Unit's base reference profile, a player's selected upgrades, and later
  in-game profile transitions. Do not attach selected choices to the replaceable Army
  snapshot or present the complete chart as immutable Unit detail.
  **Source boundary:** Infinity Spec-Ops and Request SpecBall are already
  defined in N5.3 core rules p. 98 and represented by the current reference.
  ITS Season 18 p. 26 prohibits ordinary Spec-Ops in official tournaments;
  its separate TEAM-OPS Extra is on p. 28. This deferred customization task
  does not make the published core Skills ITS-only or require a configurator
  for core reference publication. Review source-chart exclusions against
  the maintained source evidence.

- [ ] **Data processing + Web backend + Web frontend:** Revisit loadout `disabled` and
  `minis` only when a reviewed source contract or roster-builder use establishes their
  player-facing meaning. Until then retain the source values without inferring either
  current availability or a miniature-count rule.

### Unit Explorer discovery

- [ ] **Web backend + Web frontend:** Add contextual usage counts to the
  Skills, Equipment, and Weapons filter dropdowns. Count distinct logical
  Units in the complete currently filtered population, retaining every active
  filter, including the selection in the counted dropdown, Army context, and
  optional availability. Preserve the existing
  [profile/loadout matching semantics](data-model.md#context-coherent-filtering).
  Counts describe usage within that population, not hypothetical totals obtained
  by replacing or removing a filter, and are independent of pagination, sorting,
  and extended view. Compute counts in batches, keep them synchronized with
  displayed results, and validate accessible presentation, loading/cancellation
  behavior, semantic correctness, and representative performance.
  Multi-selection and per-filter AND/OR/NOT remain separate proposed
  extensions. Server-response/count caching is a measured implementation option,
  not a prerequisite or an accepted infrastructure commitment.

### Routing and long-term compatibility

- [ ] **Web frontend + Project infrastructure:** Design a **stateless, self-contained v2
  sharing format**, replacing the earlier server-side short-link registry proposal.
  **No `/s/<id>` lookup service, server-stored share-token strings, or user-authored
  content database.** Preserve decoding of existing v1 `s=` and legacy explicit links.
  - [ ] Define a versioned, scope-bound canonical typed payload and deterministic
    encoding/decoding, including normalization, meaningful ordering, default elision,
    ruleset/source revision, integrity checking, and error/migration behavior.
  - [ ] Benchmark complete URL length for realistic Unit Explorer, catalog, search,
    scenario presets and **large user-defined scenarios** against v1. Evaluate a
    compact binary codec and measured optional compression, without a server registry.
  - [ ] Prefer URL fragment payloads for authored content to avoid sending it in
    ordinary HTTP requests; test coexistence with existing `#rule-*`/other anchors,
    browser history, browser navigation, clipboard sharing, and soft navigation.
    Document remaining privacy exposure: fragments are not secret or encrypted.
  - [ ] Handle payloads too long for practical URLs with an explicit versioned
    import/export file; a short deterministic hash may verify or identify locally
    available content but **cannot replace the encoded payload** for arbitrary
    user-authored content.
  - [ ] Validate untrusted inputs with resource limits and safe text rendering;
    test compatibility, corrupt payloads, missing rule revisions, and round-trip
    behavior on a completely offline local installation.

- [ ] Before retiring or redirecting numeric routes, define and implement a
  per-domain slug-freezing, reviewed-override, alias/redirect, and canonical-URL
  compatibility policy. Until then, preserve the current contract: canonical generated
  links prefer stable domain slugs while numeric routes remain accepted compatibility forms.

### Concurrent-agent development safety

**Project domain:** Project infrastructure

- [ ] **Optional; explicit user request only:** Complete tool-independent
  multi-agent workspace coordination. The
  [checkout and claim protocol](multi-agent-workspaces.md#activation-and-default-workflow)
  is disabled by default.
  Deferred: further coordination infrastructure work is outside ordinary
  autonomous development; authority: user; revisit: only when the user explicitly
  requests that work. Existing tools and acceptance evidence do not activate it.
  Worktrees, local/global claims, dual-registry pinned fast-forward integration
  and MCP named-checkout pytest/non-test checks are implemented. The real
  coordination ref is initialized; its version-2 transition preserves existing
  claims and requires each older client to update explicitly. See
  [focused safety acceptance](testing.md#agent-coordination-safety-acceptance).
  [Inspected integration recovery](multi-agent-workspaces.md#inspected-integration-recovery)
  now settles interrupted metadata while retaining claims and reservations.
  - [ ] After explicitly updating its coordination client, exercise a
    non-destructive real claim/status round trip from an owned Linux development
    checkout. Preserve the independent interactive checkout and pinned test
    checkout; disposable-clone race tests do not satisfy this operational gate.
    Blocked: the live Linux probe read version 2 and rejected a Windows-owned
    scope, but its metadata push was rejected; authority: integration owner;
    retry: after authorized remote write access/policy verification. The remote
    registry and existing claims stayed unchanged.
  - [ ] Implement inspected abandoned-task recovery and ownership-transfer
    tooling, including disconnected owners, task reassignment and cross-machine
    handoff. Preserve the documented inspection/idle-job requirements; never
    expire claims or assume an unresponsive owner's checkout can be overwritten.
  - [ ] Complete MCP named-checkout Git operations and the remote worker
    allowlist without broadening validation-checkout write privileges.
  - [ ] Add read-only workspace/claim/integration status to the monitor and
    verify race/refusal behavior on actual Linux before unattended use.

### Performance, storage, and build tooling

- [ ] **Finish v10 rules-data release acceptance:** The matched
  v10 artifact set was promoted to tracked `data/generated/` in development
  on 2026-11-08. It contains 17 normalized deployed objects (one unresolved
  delivery), 151 exact-variant groups (v2), reviewed citations for 62 Weapons,
  and the unchanged pinned Army database. The read-only v9→v10 common-table
  parity audit passed: only schema metadata and Battleground map annotations/
  labels changed among existing records; seven normalized deployed-object
  tables were added. Checkout hosting and release image packaging are
  independently supported. The *previous tagged production release* remains
  v9; there has been no deployment or new release tag.
  - [ ] Obtain terminal hosted Source, Deployment, Wheel and Cross-browser
    acceptance for the exact promoted-artifact SHA; confirm the release image
    against the tracked four-file set. Local tracked-image build, startup,
    provenance, deployed-object, variant and Weapon API smoke passed
    2026-11-08, and the disposable image/container were removed.
  - [ ] After hosted acceptance, audit and retire superseded v9 promotion
    helpers (preserving any remaining v8/v9 compatibility consumers). Keep
    the immutable-image release model simple: no live replacement locks,
    in-container regeneration or multi-file runtime transaction machinery.

- [ ] **Browser test infrastructure research — deferred:** Continue the
  [Chromium lifecycle and concurrency investigation](testing.md#controlled-chromium-concurrency-and-browser-reuse-benchmark).
  The historical instrumentation
  gates (VR-0023/24) are complete; Linux uses its validated four-slot profile, Windows retains
  two slots, and clean CI is unchanged. Raw captures stay in ignored
  `local/benchmarks/`.
  - [ ] Diagnose intermittent full-load Windows Glossary and Spec-Ops
    chart visibility timeouts using the existing failure-only API/DOM
    diagnostics; passing isolated runs do not establish their cause.
  - [ ] Profile the Scenario FAQ long tail, fresh browser contexts
    versus pooled-browser reuse, and CPU/RAM behavior under sustained
    parallel load; revisit alternate capacities only with repeated
    stable evidence on a dedicated host.
  - [ ] Revisit exact cross-host optional source-PDF/staging coverage
    if equivalent source-byte audit coverage becomes a requirement;
    platform-only and missing ignored-source skips must remain labeled,
    not silently treated as equal test coverage.
  - [ ] Consider a pinned Playwright container only after verifying a
    Linux test container engine, separate from production Compose.
    Escalate findings separately if they expose current correctness or reliability defects.

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

### Army snapshot and symbol-pipeline maintenance

Remaining pipeline work covers maintenance, selective refactoring, richer diagnostics/performance
work, and external-tool portability. The implemented pipeline and artifact lifecycle
are described in [data guidance](../data/README.md).

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
  - [ ] Add one compact machine-readable build-summary artifact with per-stage and total runtime so
    repeated builds can be compared without scraping the verbose log or individual reports.
  - [ ] Add separate discovery/unknown-reference CSV outputs only if future audit tooling needs
    row-oriented data beyond the build manifest and current JSON/CSV stage reports.

- [ ] Extend the remaining regression and portability coverage for the integrated Army/symbol
  pipeline.
  - [ ] Add explicit fixtures for empty-text cleanup and a small set of troublesome real-world SVG
    conversion cases that should remain stable across tool upgrades.
  - [ ] **Acquisition:** Extend native external-tool integration coverage across Windows, Ubuntu/Linux, and macOS,
    especially executable discovery (`.exe`/`.cmd`), subprocess arguments, and real
    Inkscape/`resvg`/SVGO invocation. Hermetic source/pipeline coverage already runs across all three
    operating systems in required CI; external-tool tests may remain conditional when those
    executables are unavailable.

### ITS, scenarios, and game tools

- [ ] Build a versioned ITS reference library from material under
  `data/pdf/its/` and `data/pdf/legacy/`, keeping the current season distinct
  from archived seasons.
  - [ ] Keep season content isolated by season and effective date. A user choosing
    a prior event must see its matching scenario, objectives, extras, and FAQ
    rulings rather than a mixture of seasons. Retain a curated, human-reviewed
    change log/diff rather than relying on raw PDF text diffing.
  - [ ] Reconcile the official September 24 ITS 18 hotfix in the pinned
    English/Spanish 2026.09.11 PDFs against English 2026.09.01: verify all
    changes to The Dig, Double Bind and Crossing Lines (including objective
    selection, token ownership, 150-point spacing and Engineer/GizmoKit);
    select effective-date/version identities, migrate affected citations and
    audit the published Battleground pilot without silently rewriting historical
    2026.09.01 play. The initial [bilingual PDF delta
    intake](n5-source-history.md#pdf-revision-difference-intake-2026-11-06)
    is evidence triage, not semantic acceptance.
  The official Army app/site remains authoritative for list legality;
  InfinityDB labels its snapshot/date and does not claim tournament validation.
  - [ ] Publish ITS-only FAQ clarifications after verifying each exact
    season/scenario identity, version and bilingual source citation. Model
    seasonal action identities such as `Activate Communication Antenna`,
    `Oppose Activation`, and `Emit Akial Interference` only in their reviewed
    mission context. Confirm none leak into core or other seasons; avoid
    universalizing tournament-specific outcomes.

- [ ] Extend the existing core-scenario foundation with remaining ITS scenario
  list/detail coverage backed by versioned seasonal data; retain the already
  published Season 18 Battleground pilot.
  - [ ] Curate the remaining Season 18 mission identities and complete
    source-backed definitions under the reviewed selected 2026.09.11 hotfix
    identity once its source promotion is accepted; retain
    `its-18@2026.09.01` for historically scoped results. Extend typed
    geometry, scoring and card/classified choices only where each mission
    needs them. Unpublished missions must fail closed.
  - [ ] **Later seasons (after Season 18):** Add ITS Season 17 (the first full
    season launched under N5) and ITS Season 16 Part II (the N5-compatible
    revision), at minimum their scenario definitions and maps. Keep original
    Season 16 N4-era content distinct from Part II; preserve exact season,
    revision and source provenance. Consider season-specific rules and FAQ
    coverage after the scenario baseline, without delaying Season 18.
  - [ ] Capture structured, cited scenario facts: objectives and scoring, game
    rounds/end conditions, force/point/SWC/table/deployment configuration,
    deployment map or geometry, exclusion zones, token types/diameters,
    classified-objective setup, reinforcement suitability, tactical-support
    options, and scenario-specific rules/elements.
  - [ ] Scenario pages should expose the selected season prominently and link
    season-specific terms to the relevant rules/state references.

- [ ] **Data processing + Web frontend:** Extend the existing core-scenario SVG renderer for ITS
  geometry after the seasonal scenario data is curated. Reuse the same versioned geometry model and
  rendering engine rather than creating an ITS-only map format.
  - [ ] Add ITS-required geometry only when supported by curated scenario evidence, including
    repeated/mirrored placements, circular/radius regions, Exclusion/Hazard/Scoring areas,
    asymmetric roles, access/opening lines, scenario-specific markers/icons, and genuine
    per-table-size overrides rather than blind scaling.
  - [ ] Preserve season/scenario source provenance and add compatibility fixtures from current and
    archived ITS material before promoting new geometry features into the schema contract.
  A future geometry editor/preview must reuse the scenario creator below and
  the shared schema/renderer, not introduce an ITS-only browser format.

- [ ] **Data processing + Web frontend:** Build a **scenario creator/editor**
  using the canonical scenario component model and map renderer, with no server-side
  user-content storage (see `docs/data-model.md`).
  - [ ] Start from a blank scenario or copy/modify a published scenario without
    changing its authoritative identity, provenance, or rules; label edited copies as
    player-defined variants.
  - [ ] Select preset Deployment Zone/table geometry, complete rule sets or individual
    Rules/Skills; combine them with custom scenario elements, local Skills/rules,
    objectives, scoring methods, setup, roles, and end conditions.
  - [ ] Define a safe, extensible **typed custom-rule** vocabulary with explicit
    applicability, targets, timing, conditions, modifiers, units, and outcomes.
    Permit prose-only rules when semantics are not representable; do not imply
    InfinityDB can validate or execute unknown game mechanics.
  - [ ] Reuse schema validation, renderer and reference resolvers; test composition,
    conflicting overlays, source-version compatibility, untrusted text, and offline
    round trips with self-contained URLs and portable file import/export.
  Player-authored scenarios must not alter authoritative published scenarios or their acceptance.

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
  Temporary scenario-granted skills, designated Troopers, classified
  cards, tactical support and private information belong to per-game/session
  state, never to the replaceable Army snapshot.

- [ ] Provide an optional ITS organizer/event companion using portable, local
  event data rather than requiring server-side user-authored storage.
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
  If accepted, share canonical data/rules artifacts and semantics with the
  web client; revisit the domain taxonomy only for a permanent native frontend.

### User-owned tools and portable data

**Project domains:** Web frontend, Project infrastructure

Future personal-content tools use transient editing, privacy-aware
self-contained URLs and portable import/export, without mandatory accounts,
server-side saves or share-token registries. Optional device-local
persistence needs a separate privacy decision; the official Army app
remains authoritative for list legality.

- [ ] Build a curated unit-model image repository; do not assume open uploads.
- [ ] Evaluate an offline/portable model-collection tracker without accounts.
- [ ] Support portable army lists, favourites and notes with export/import,
  independent of replaceable Army snapshots.
- [ ] Add Unit comparison across profiles, loadouts, weapons, Skills and Equipment.
- [ ] Build army-list export/integration with game-mode and mission-aware
  capability guidance, without claiming tournament legality or disclosing
  hidden information; coordinate with the ITS guidance above.
- [ ] Add Developer-mode data-review screens for normalization warnings,
  unresolved placeholders and raw-archive record provenance.
- [ ] Optionally browse archived imported versions when snapshot history
  becomes player-useful; existing ZIPs already provide recovery.
- [ ] Add a two-snapshot JSON comparison screen for added, removed and
  updated records, with optional changes highlighted elsewhere in the UI.
