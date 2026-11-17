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

Use these links to jump directly to a workstream:

- **Reference and UI:** [Sources](#external-source-clarifications), [Rule references](#source-notation-and-rule-references), [History](#per-reference-change-history), [Lists](#list-and-session-configuration), [Sharing](#routing-and-long-term-compatibility).
- **Engineering:** [Backlog policy](README.md#backlog-completion-and-retirement), [Agent coordination](#concurrent-agent-development-safety), [Performance/build](#performance-storage-and-build-tooling), [Army snapshots](#army-snapshot-maintenance).
- **Expansion:** [ITS/scenarios](#its-scenarios-and-game-tools), [Native applications](#native-applications), [Portable tools](#user-owned-tools-and-portable-data).

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

- [ ] **Acquisition + Data processing:** Retire the September/October 2026
  Wiki ZIPs and their snapshot manifests once this migration is accepted.
  - Completed: Repinned 109 current-page citations (unchanged MediaWiki revision
    IDs and headings) and verified 116 curated `oldid` references. Migrated
    active research readers, pinned tests and current documentation; rebuilt
    the runtime database set. Retirement comparison found **zero missing**
    older current-page/historical revision IDs or history page-name conflicts
    in either language; the November 16 archives are revision-level supersets.
  - Remaining: Final focused validation and a deliberate local cleanup of the
    four old ZIPs, corresponding old manifests, and the superseded English
    extracted history mirror. Preserve dated reports
    as historical evidence; never silently delete or re-label their source
    provenance. Future captures use the parameterized migration and retirement
    comparison tools without introducing new hard-coded source-version logic.

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

### Release and deployment robustness

**Project domain:** Project infrastructure

- [ ] **Prevent recurrence of v1.1.0 release-process failures** without adding
  another release-management system or routine full-suite gates. The 2026-11-16
  release passed application/data/CI validation, but exposed late checklist
  corrections, release-evidence/CI drift, noncritical image-pruning failure
  and an incorrect production `1.1.0+dev` footer.
  - [ ] **Make production version identity deterministic.** For a verified
    release-tag checkout, derive and bake the version from the tag/package
    identity rather than server worktree status; retain `+dev` for real
    development builds. [PR #31](https://github.com/frankysan/InfinityDB/pull/31)
    proposes changing source-checkout Git status handling, but that module
    participates in the tracked runtime-database input fingerprint. Do not
    merge that source-level change alone: it needs a matching database rebuild
    during release preparation. The production build instead now pins display
    identity to the exact tag/package version in `scripts/deploy.sh`.
    Assert that the built image/footer and deployed public footer agree with
    the release tag and `/api/version`, alongside snapshot/static revisions.
  - [ ] **Make image retention cleanup non-fatal.** The v1.1.0 deploy tried
    to remove an old `app-test-*` metrics-history image still referenced by
    a test container. Skip and report tags used by *any* container (including
    stopped or isolated-test containers); do not force-remove them, disturb
    production/test stacks or fail an otherwise healthy deployment because
    pruning could not complete. Keep the supported test-stack stop command
    in the release procedure.
  - [ ] **Prevent CI/evidence contract drift.** The release-evidence collector
    rejected the green Source run because its expected matrix omitted both
    pinned-determinism jobs; the immediate fix was [PR #30](https://github.com/frankysan/InfinityDB/pull/30).
    Add a focused contract test against the maintained workflow job definitions,
    including required successful build/reuse steps. Exercise candidate release
    evidence after its hosted checks pass but *before* merge; still recollect
    evidence on the exact final `main` SHA before tagging.
  - [ ] **Consolidate isolated Docker acceptance probes.** Earlier
    `releasing.md` commands used the wrong Caddy host and health port;
    corrected to `localhost:8080/api/version` and the loopback metrics
    listener `127.0.0.1:8081/health`. Reuse one small executable smoke
    check for version, health, metrics and representative routes instead of
    copying commands between documents.
  - [ ] **Freeze release-facing content before costly acceptance.** Complete
    changelog/README, version metadata, deployment instructions and release
    tooling, then run cheap metadata/docs/tooling checks before the mandatory
    full local suite and isolated Docker test. Preserve exact-SHA post-merge
    CI and any selected cross-browser jobs; the additional browser dispatch
    on the merge SHA is expected, not a failure. Avoid redundant reruns unless
    the changed content invalidates the relevant evidence.
  - [ ] Validate these focused improvements with release-evidence, version
    and deployment-script regression tests, Ruff and appropriate hosted CI.
    The implementation on `dev/v1.2.0` includes tag-derived display identity,
    nonfatal/reference-aware pruning, pre-merge evidence checking, a shared
    deployment HTTP probe, and updated release instructions. Focused Windows
    tests and static checks passed; Linux pruning behavior, the tagged Docker
    image path and hosted CI remain to be verified before closeout.
    Keep detailed acceptance procedures in `docs/releasing.md` and
    `docs/deployment.md`, not duplicated in this backlog.

### Performance, storage, and build tooling

- [ ] **Retire superseded v9 rules-data promotion helpers** after the tracked
  v10 Rules set receives the applicable release-candidate acceptance.
  The current set includes 17 normalized deployed objects (one unresolved
  delivery), 151 exact-variant groups and 62 reviewed Weapon citations.
  [Releasing](releasing.md) owns exact-SHA Source, Wheel, Deployment and
  matched four-file image evidence; [cross-browser checks](ci.md#cross-browser-release-compatibility-gate)
  are opt-in for v1.1+ when browser risk warrants them.
  Preserve independent v8/v9 compatibility consumers, and keep immutable
  images free of live replacement locks or in-container regeneration.

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

### Army snapshot maintenance

The implemented artifact lifecycle is described in [data guidance](../data/README.md).

- [ ] Let future snapshot-comparison tooling write structured generated diff
  data/reports under manifest/report paths while curated snapshot notes remain
  the human interpretation of those results.

### ITS, scenarios, and game tools

**v1.2.0 priority:** Expand source-cited ITS Season 18 coverage, especially
reconciling the current hotfix and publishing additional reviewed missions,
scenario maps and their relevant context. Preserve the existing Battleground
pilot and historical revision identities. Season 17 and Season 16 Part II
remain later scope; do not claim complete Season 18 coverage before it is verified.

**Published 2026.09.11 hotfix coverage (2026-11-17):** All twenty
reviewed missions now have source-cited scoring, rules and game-size maps; the original
2026.09.01 Battleground remains independently selectable. The browser exposes
exact-revision selection, typed objectives, and Double Bind's alternative Main
Objective sets. Map zoning and placement rulers have been reviewed in both
source languages. All twenty hotfix missions are present, with unresolved source
issues identified explicitly. In-browser visual acceptance at relevant
breakpoints is still open. See the
[ITS season database](its-season-database.md#published-20260911-hotfix-curation).

- [ ] **Data processing: consolidate source-family curation.** Implement the
  [accepted version-tagged fact model](data-model.md#accepted-authoring-direction-one-source-family-version-tagged-facts)
  and migrate the two ITS Season 18 curated JSON files into one maintained
  season-family file. Declare the current revision explicitly (currently
  2026.09.11), and project only its reviewed facts, including
  mission facts, maps, event policies, source descriptors and citations; reject
  missing, conflicting or implicitly inherited facts. Update builders, source
  registration and build provenance together. Prove the current publication
  preserves existing hotfix behavior before retiring the split inputs.
  Make the browser select a season rather than an exact revision; do not show
  older ITS 18 facts or require an older-revision runtime database. Retain
  historical curation/provenance for a possible later replay feature, without
  implementing that feature as part of this migration. Handle existing
  explicit-revision links without silently presenting outdated facts.

- [ ] Build a versioned ITS reference library from material under
  `local/data/pdf/its/` and `local/data/pdf/legacy/`, keeping the current season distinct
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
  - [x] Curate the remaining Season 18 mission identities and complete
    source-backed definitions under the reviewed selected 2026.09.11 hotfix
    identity once its source promotion is accepted; retain
    `its-18@2026.09.01` for historically scoped results. Extend typed
    geometry, scoring and card/classified choices only where each mission
    needs them. Unpublished missions must fail closed.
    All twenty reviewed hotfix missions now have definitions and six-size maps.
    Unresolved bilingual discrepancies remain explicit source issues;
    visual browser acceptance is tracked separately.
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
