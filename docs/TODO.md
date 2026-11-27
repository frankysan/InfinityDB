# InfinityDB backlog

This file tracks unfinished development work, including maintenance, research
and product expansion. Merge, final-main CI evidence, tagging, deployment and
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

Use these links to jump directly to a workstream:

- **Reference and UI:** [Sources](#external-source-clarifications), [Rule references](#source-notation-and-rule-references), [Source updates](#source-family-revision-updates), [History](#per-reference-change-history), [Presentation and feedback](#reference-presentation-and-feedback), [Lists](#list-and-session-configuration), [Sharing](#routing-and-long-term-compatibility).
- **Engineering:** [Backlog policy](README.md#backlog-completion-and-retirement), [Agent coordination](#concurrent-agent-development-safety), [Performance/build](#performance-storage-and-build-tooling), [Army snapshots](../data/README.md#army-snapshot-diff-reports).
- **Expansion:** [ITS/scenarios](#its-scenarios-and-game-tools), [Native applications](#native-applications), [Portable tools](#user-owned-tools-and-portable-data).

## v1.3.0 release plan

**Release focus:** Historical reference, performance and personalization.

This is the accepted scope and remaining development work. Detailed tasks live
in the linked workstreams; retire this milestone summary when the release closes.

### Committed scope and remaining work

- **Project infrastructure:** Identical-tree CI reuse, authoritative PR metadata,
  direct Caddy Host-header probing and release-tooling regression coverage are
  implemented. Retain normal [release verification](releasing.md).
- **Data processing + Web backend:** Materialized profiles, Rules, search, catalog
  usage, scoped filter inputs and reference projections, plus pre-fork
  initialization, are implemented. The [development capacity investigation](deployment.md#full-stack-v130-development-capacity-2026-11-27)
  is complete.
- **Data processing + Web backend + Web frontend:** Initial N5 Unit history is
  embedded in the normal build and includes the latest available direct snapshot.
  Initial history disclosures are implemented; retain coverage limits and
  [extend history](#per-reference-change-history) when new source states are available.
- **Web frontend + Web backend:** Faction palettes and the initial rules-content
  hierarchy and official Army deep links are implemented; representative
  [visual acceptance](testing.md#faction-palette-and-rules-content-visual-acceptance) passed.

Implemented outcomes are recorded in the [changelog](CHANGELOG.md); final
candidate acceptance remains in the release checklist.

Complete the selected development work before the existing
[release checklist](releasing.md); no new release gates are introduced.

### Optional additions (not release-blocking)

- **Web frontend + Web backend:** [ITS season-wide rules](#its-scenarios-and-game-tools)
  and [Unit comparison](#user-owned-tools-and-portable-data), both high
  priority when capacity permits. Reuse materialized profiles and historical
  comparison components where appropriate.
- **Web frontend + Web backend + Deployment:** Shared
  [bug/error reporting form](#reference-presentation-and-feedback).

### Deferred beyond the committed scope

Historical FAQ replay and comprehensive Rules history; ITS 16 Part II;
scenario creator/editor; interactive Fireteam builder; stateless v2 sharing;
native applications; portable Army lists and collection management;
comprehensive multi-agent coordination; alternative JSON runtime storage.
These remain in their owning backlog sections.

Miniature image integration and printable model identification sheets remain
dependency-bound to sufficient curated miniature and image coverage.
Reconsider inclusion only if those inputs mature during development; do not
make v1.3.0 depend on them.

## Active development

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
  The verified English/Spanish Wiki snapshots and histories from 2026-11-16
  are available for explicit edition/revision comparison; their portable
  member names were migrated into curated N5.3 after exact URL, heading,
  and source revision identity verification.

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

  Implemented subset: markers are separated from Traits without changing
  Army data, including combined labels. Reviewed mappings cover seven named
  Mines and Chest Mine CC Mode (p. 181); E/M Carbine (p. 176); E/M CC Weapon
  (p. 177, combined N+E/M); Blitzen and Smoke/E/M/Eclipse Grenades (p. 178);
  Smoke/E/M Grenade Launchers (p. 179); Deactivator Equipment (p. 186);
  and Sepsitor Plus (p. 187). Exact mode/catalog scope is preserved,
  including Chest Mine BS Mode's unresolved Army marker. SRC-013/014
  differences remain visible. Chromium acceptance covers reviewed pages
  at 1440/390/320 px, light/dark, keyboard and touch. Remaining: other
  chart rows/modes and publisher clarification of unresolved mismatches.

### Source-family revision updates

- [ ] **Acquisition + Data processing:** Implement a repeatable, reviewable
  **Rules / FAQ / ITS revision intake and reconciliation workflow**, building
  on the current ITS Season 18 source-family and per-fact revision model.
  - [ ] Preserve each new official release as immutable source evidence with
    exact revision identity, original bytes, hashes, language, citation
    locations and trustworthy publication/effective-date provenance. Do not
    infer publication dates from filenames or PDF metadata alone.
  - [ ] Compare successive releases by stable fact identity; classify added,
    modified, removed, unchanged, editorial-only and ambiguous/conflicting
    facts. Generate deterministic, cited before/after reports for human review,
    reusing unchanged facts rather than re-curating whole publications.
  - [ ] Promote only reviewed changes, retaining superseded values, per-fact
    revision applicability, citations and historical source provenance.
    Validate current and historical projections, citation integrity, and
    fail-closed handling of unresolved changes before publishing only the
    latest applicable facts to players.
  - [ ] Extend Rules and FAQ incrementally and exercise the same workflow on
    future ITS revisions; share tooling where actual source-family needs
    overlap. Historical browsing remains a separate, optional feature.

### Per-reference change history

- [ ] **Data processing + Web backend + Web frontend:** Extend the published N5
  Unit history beyond the initial accepted corpus.
  The v35 projection, enabled by default, is documented in the
  [history data model](data-model.md#private-army-history-research-database)
  and [presentation contract](web-design-guidelines.md#unit-history-presentation).
  - [ ] Extend the accepted corpus for new source states, material contextual
    metadata, or a newly selected current Army archive not already accepted as
    a direct endpoint, before publishing its history.
    Validate identity, revision dates, comparison scope, provenance and contextual
    General/Army attribution. The [intake review](n5-source-history.md#direct-snapshot-intake-review)
    found no additional source states among currently available manifest-backed archives.
  - [ ] Improve coverage where independently supported: unresolved loadout
    replacement/modification groups, changed labels, missing definitions,
    unresolved reference shapes, ambiguous same-day alternatives, complex
    lifecycle/attachment changes, multi-target and group-owned loadout changes,
    other classified items and asynchronous or incomplete observations.
    Keep ambiguous cases as review/coverage evidence; never weaken continuity
    criteria merely to increase the displayed count.
  - [ ] Later: extend to N4/CodeOne only with edition-specific validation,
    provisional identities and independently supported source provenance.
  Final Docker and release acceptance of the initial N5 publication belongs
  to the [release checklist](releasing.md).

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

- [ ] **Data processing + Web backend + Web frontend:** Extend per-reference
  change indicators beyond the initial Unit histories to applicable Rules,
  Skills, Weapons and other entities. Show when and what changed, and why only
  when documented by an authoritative source.
  - [ ] Derive reviewed events from versioned N5 Army snapshots, rules/FAQ PDFs,
    exact Wiki revisions and official Corvus Belli update posts. Distinguish
    gameplay changes, editorial wording, source-format changes and unresolved
    conflicts; preserve stable identities, citations and successive revisions.
  - [ ] Add concise accessible detail-page indicators and links to evidence;
    do not mark unchanged records or invent reasons or effective dates.
    Keep unknown reasons/dates explicit and historical facts separate from
    the current reference.

### Reference presentation and feedback

- [ ] **Web frontend + Web backend:** Consider independent sectorial palettes
  only with representative sectorial visual references; do not infer them
  solely from their parent faction.
- [ ] **Web frontend + Web backend + Deployment:** Add a shared, minimal
  bug/error reporting form with lightweight spam/bot protection. Include
  the current page and relevant entity context by default, let the reporter
  inspect the submitted context, and omit personal details and private
  URL/query/share data. Require no account, name or email. Choose a simple
  report-delivery mechanism and retention policy before implementation;
  avoid a separate issue-management system or personal-content store.
  Keep the component consistent wherever displayed.

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

- [ ] **Optional; explicit user request only:** Complete remaining
  multi-agent coordination; the [checkout/claim protocol](multi-agent-workspaces.md#activation-and-default-workflow)
  stays disabled by default. Implemented worktrees, claims, integration and
  recovery are documented there; see [focused acceptance](testing.md#agent-coordination-safety-acceptance).
  - [ ] Verify an owned Linux checkout's real claim/status round trip after
    authorized remote metadata-push access is restored. Keep interactive
    and pinned test checkouts independent; the earlier registry push was
    rejected without changing the existing remote claims.
  - [ ] Add inspected abandoned-task recovery, ownership transfer and
    cross-machine handoff; never auto-expire claims or overwrite an owner.
  - [ ] Complete named-checkout MCP Git operations and the remote worker
    allowlist without adding write access to validation checkouts.
  - [ ] Surface read-only workspace/claim/integration status in the monitor
    and verify real Linux refusal/race behavior before unattended use.

### Performance, storage, and build tooling

- [ ] **Deferred browser test-performance investigation:** Use the existing
  [Chromium benchmarks](testing.md#controlled-chromium-concurrency-and-browser-reuse-benchmark)
  and failure-only API/DOM diagnostics. Linux four-slot and Windows two-slot
  settings remain unchanged unless repeated evidence supports a change.
  - [ ] Reproduce intermittent full-load Windows Glossary/Spec-Ops
    chart-visibility timeouts; isolated passing tests do not explain them.
  - [ ] Measure Scenario FAQ tail latency, fresh versus pooled contexts,
    and CPU/RAM under sustained parallel load before adjusting capacity.
  - [ ] Review cross-host optional PDF/staging source-byte coverage only if
    needed; label host-only and missing-source skips explicitly.
  - [ ] Consider a pinned Playwright test container only after verifying a
    suitable Linux test container engine, separate from production Compose.

- [ ] Evaluate SQLite `immutable=1` for deployed snapshots. Enable it only when
  the process never observes an in-place database replacement.

- [ ] Compare otherwise equivalent deployment variants backed by SQLite and by
  `normalized.json`, with both variants exposing the same API and representative
  load scenario. Define the JSON variant's startup parsing, indexing, and caching
  semantics before interpreting performance results so the comparison measures
  runtime data models rather than repeated JSON parsing. Evaluate both request
  performance and deployment portability/multi-platform suitability before
  deciding whether a storage/query abstraction is justified.

- [ ] **Retire the remaining explicit raw-SQLite interfaces** once independent
  research and source-audit consumers no longer need them. Complete runtime
  builds and default standalone exports already omit `army.raw.db`; verified
  normalized input replaces the legacy sibling for maintained source audits.
  Rawless v2 determinism and the independent native-platform checks are
  documented in [CI](ci.md#cross-platform-deterministic-outputs) and the
  [data lifecycle](../data/README.md).
  - [ ] Review the remaining opt-in paired-export, pair-health, source-row
    inspection and programmatic `include_raw=True` contracts. Retire only
    those without independent consumers, preserving source-only row fidelity,
    absent-versus-null values, exact occurrence/Extra relationships and
    fail-closed provenance. Keep useful compatibility/parity paths until
    focused replacement tests and complete-set build checks pass.
  - [ ] Decide whether any legacy ignored `data/generated/army.raw.db`
    contains unique evidence worth retaining. It is not a current matched
    runtime pair and must not be silently deleted; a separately reviewed
    disposition suffices without reopening the completed workspace cleanup.

### ITS, scenarios, and game tools

ITS Seasons 17 (V0.2) and 18 (2026.09.11) have completed source audit,
diagram and focused browser acceptance. All 36 season-mission definitions
(216 setups) have been reviewed; known source discrepancies remain disclosed.
See [release browser acceptance](its-season-database.md#release-browser-acceptance).
Final-candidate acceptance is governed by [the release checklist](releasing.md).
Season 16 Part II remains later scope.

- [ ] Extend the versioned ITS reference library to remaining archived seasons
  and historical revision browsing as appropriate. ITS 17 V0.2 and ITS 18
  2026.09.11 are already published with independent selected revisions and
  source-family evidence. Preserve season/date isolation, curated differences,
  historical facts and the official Army app's authority for list legality.
  - [ ] Publish additional ITS-only FAQ clarifications after verifying exact
    season/scenario identity, version and bilingual citation; keep seasonal
    actions and rulings scoped to their reviewed context.
- [ ] **Data processing + Web backend:** Extend the shared scenario/Skill
  authoring model only where real reuse requires reviewed typed overrides.
  ITS 17/18 scenario coverage and canonical Skill consolidation are published;
  see [ITS database documentation](its-season-database.md).
  - [ ] Add narrow typed field overrides for remaining scenario components
    when needed, rejecting incompatible facts and preserving citations.
  - [ ] Review remaining ITS 17 V0.0/V0.1 historical differences, V0.2
    bilingual discrepancies, optional Extras and reusable components as
    justified by further publication or historical replay. All six original
    PDFs are pinned; do not infer cross-revision or cross-season equivalence.
  - [ ] Add ITS Season 16 Part II (N5-compatible revision), keeping original
    N4-era Season 16 distinct. Curate cited scoring, objectives, setup,
    geometry, token sizes, classified and tactical support options, scenario
    rules and applicable season references. Reuse the existing component
    and renderer contracts; consider season-wide rules and FAQ coverage
    after the scenario baseline.

- [ ] **Data processing + Web frontend + Web backend:** Complete the reviewed
  Season Rules coverage for ITS 17 and ITS 18. The
  [collapsed Season Rules disclosure](season-publication-ownership.md#season-rules-on-scenario-pages)
  already presents published season-scoped Rules, Skills, States and policies.
  Review and curate missing gameplay-relevant common rules (including Civilians,
  Designated Targets, Classified Objectives/HVTs and tournament Army List
  selection), and applicable optional Extras (including ITS 18 Resilience
  Operations). Review exact bilingual season sources; distinguish event-only
  rules from normal mission rules and avoid duplicating existing mission-specific
  facts or core definitions.

- [ ] **Data processing + Web frontend:** Extend the shared scenario geometry
  model and SVG renderer only when later seasonal content or the scenario
  editor requires unsupported, source-backed geometry. Preserve source
  provenance and compatibility fixtures; do not introduce an ITS-only format.

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
  - [ ] **Data processing + Web frontend:** **Dependency-bound:** Automatically generate printable model
    identification sheets for all current factions and Armies/sectorials from
    the published `miniatures.db`. Begin once the curated database and
    representative image coverage are sufficient for useful, accurate sheets;
    retain the goal of complete current-faction coverage. Include Unit names,
    representative images, and explicit missing-image handling; consider
    optional older sculpts/alternatives. Provide print-friendly layouts and PDF
    export, with regeneration after Army or miniature database updates.
    Respect asset publication permissions and preserve canonical identities.
- [ ] Evaluate an offline/portable model-collection tracker without accounts.
- [ ] Support portable army lists, favourites and notes with export/import,
  independent of replaceable Army snapshots.
- [ ] Add Unit comparison across profiles, loadouts, weapons, Skills and Equipment.
- [ ] Build army-list export/integration with game-mode and mission-aware
  capability guidance, without claiming tournament legality or disclosing
  hidden information; coordinate with the ITS guidance above.
- [ ] Add Developer-mode data-review screens for normalization warnings,
  unresolved placeholders and raw-archive record provenance.
- [ ] Extend archived snapshot browsing beyond the initial N5 Unit history
  where it becomes player-useful; existing ZIPs provide recovery.
- [ ] Add a two-snapshot JSON comparison screen for added, removed and
  updated records, reusing structured snapshot diff tooling where possible.
