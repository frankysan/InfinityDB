# InfinityDB backlog

This is the working implementation backlog. Every unchecked item belongs to exactly
one release bucket: **1.0.0** or **post-1.0**.
The buckets are planning commitments, not a promise that a minor release cannot move a
low-risk item earlier or defer a non-gating item when evidence changes.

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

## Current milestone

**Project domain:** Project infrastructure

Released version: **0.10.1**; current development: **1.0.0**.
The [changelog](CHANGELOG.md) owns release history,
[testing](testing.md) owns verification procedures and
[releasing](releasing.md) owns the final acceptance definition.
Bounded development checks do not approve the frozen candidate.
Core N5 scenarios remain in scope; optional ITS, user-data,
performance experiments and native clients are post-1.0.

## 1.0.0 — current-reference completeness gate

Close material source-to-browser reference gaps and verify the complete
current-data release against the [1.0 definition](releasing.md#version-10-data-completeness-gate).

### Implemented foundations and remaining scope

**Project domains:** Data processing, Web backend, Web frontend, Project infrastructure

The canonical [data model](data-model.md), [source-coverage audit](v1.0-source-coverage-audit.md)
and [test procedures](testing.md) own implemented facts, bounded acceptance
and source identities. Published foundations include the core scenarios,
dated FAQ, structured skill charts, Weapon/Ammunition and deployed-object
references, scoped Reinforcements and exact-variant usage API/browser paths.
The usage publication is still conditional on a verified matched artifact;
an ignored development candidate is not a release artifact.

### Development sequence

Review and close the earliest actionable numbered V1S slice below after
checking the [VD/VR queue](validation-queue.md). Source/inventory
reconciliation precedes its dependent curation or projection; final
release-input checks remain V1S-081–095. The
[1.0 release definition](releasing.md#version-10-data-completeness-gate)
determines scope. Do not make optional ITS tooling or publisher answers
release blockers.

### Pre-planned 1.0 execution slices

The numbered V1S register is the actionable decomposition of the
1.0 parent outcomes below, not a second release definition.
The original 2026-11-03 sizing and retired ID history remain in Git.
S/M/L are relative bounded/small multi-step/larger acceptance slices,
not time estimates. A source-reviewed no-change is a valid closeout;
conditional implementation requires a confirmed gap.

#### V1S work selection and handoff

After the [VD/VR checkpoint](validation-queue.md#queue-rules), before
each autonomous "proceed" pass:

1. Inventory **all unchecked V1S IDs**, prerequisites, owners and
   available evidence; do not resume from the latest edited section
   or assume missing IDs have passed.
2. Select the **earliest actionable** ID. For earlier IDs, record
   a concrete `Blocked:` dependency/owner/retry trigger or
   `Deferred:` priority/revisit trigger in their existing entries.
   Source uncertainty alone is not a blocker when further review is
   possible. Bypass actionable earlier work only for explicit user
   priority or a documented critical dependency.
3. At each boundary reconcile the selected ID, its parent, source
   evidence, changed contracts and VD/VR obligations. Retire it only
   with completed acceptance and documentation; otherwise rewrite
   the remaining action. Preserve every retired V1S ID in the
   closeout commit per [the retirement contract](README.md#backlog-completion-and-retirement).
4. Report the selected/previous ID disposition, reasons for passing
   over earlier IDs, and current VD/VR counts. Do not equate a
   focused test pass or Git commit with final release acceptance.

An implementation slice needs source/variant provenance, affected
model/export, API and ordinary browser route (or justified no-change),
regressions and documentation handoff. Final candidate and CI gates
remain separate. Only an actively running **full Linux suite** allows
independent Windows work while validation drains; see the
[queue rules](validation-queue.md#queue-rules).

#### Rules and contextual reference completion

**Parent:** [Rules and reference completeness](#rules-and-reference-completeness).
**Project domains:** Data processing, Web backend, Web frontend

Previous source reviews and exact browser acceptance are retained in
[the coverage audit](v1.0-source-coverage-audit.md). The remaining external
Silent/Immunity question is [SRC-002](official-source-clarifications.md#src-002--silent-versus-attribute-immunity-bilingual-qualifier),
not a 1.0 gate.

- [ ] **V1S-041 (M, gate):** Accept the optional Reinforcements
  Section, profiles and exact Commlink (+1)/(+2) variants in the
  ordinary browser on the frozen, release-matched source pair.
  Preserve N4-origin disclosure; do not assert roster legality or
  N5-native authority.
  Deferred: Final release-paired acceptance depends on V1S-081/084/088;
  authority: release owner; revisit: after those frozen-input gates pass.

#### Four core scenarios

**Parent:** [Core-scenario reference completion](#rules-and-reference-completeness).
**Project domains:** Data processing, Web backend, Web frontend

- [ ] **V1S-045 (M, gate):** Run final-input four-scenario
  keyboard/touch/theme/responsive, rapid-selection, empty/error
  and navigation/race-recovery acceptance alongside V1S-088.
  Existing [bounded source/browser checks](v1.0-source-coverage-audit.md#core-scenario-scoped-skills-specialists-overlays-and-faq-v1s-044-2026-11-05)
  do not certify the frozen candidate.
  Deferred: Final-input acceptance requires V1S-081/084 and runs with V1S-088;
  authority: release owner; revisit: after the frozen candidate is ready.

#### FAQ and errata

**Parent:** [Rules and reference completeness](#rules-and-reference-completeness).
**Project domains:** Data processing, Web backend, Web frontend

No independently open FAQ slice precedes the final V1S-084/088
release-matched acceptance.

#### Rule-variant usage index and Restrictions

**Parent:** [Rules and reference completeness](#rules-and-reference-completeness).
**Project domains:** Data processing, Web backend, Web frontend, Deployment

The [variant usage source-pair and browser gate](v1.0-source-coverage-audit.md#full-exact-variant-usage-source-pair-acceptance-2026-11-05)
is accepted on development inputs; final artifact/hosted checks are
still required. Restrictions migration has staged-pair and CI image
rehearsal; the former V1S-067 live-host rehearsal is out of scope.

#### Game States context

**Parent:** [Rules and reference completeness](#rules-and-reference-completeness).
**Project domains:** Data processing, Web backend, Web frontend

The [State/Fireteam review](v1.0-source-coverage-audit.md#contextual-state-fireteam-browser-acceptance-2026-11-05)
records reviewed source-backed reciprocal links. Final source-input
acceptance remains under V1S-081–088.

#### Weapons, Ammunition and deployed objects

**Parent:** [Rules and reference completeness](#rules-and-reference-completeness).
**Project domains:** Data processing, Web backend, Web frontend

The [deployed-object acceptance](v1.0-source-coverage-audit.md#deployed-object-api-and-ordinary-browser-acceptance-v1s-078-2026-11-05)
is bounded to the development pair; final-input checks remain.

#### Accessibility and navigation

**Parent:** [Player-facing navigation and reference clarity](#player-facing-navigation-and-reference-clarity).
**Project domains:** Web frontend, Project infrastructure

- [ ] **V1S-080 (M, gate):** Complete final-candidate touch, theme,
  320/390px viewport and notice expand/collapse verification; fix
  reproducible 1.0 defects. Development touch regressions passed;
  release-candidate manual/browser acceptance remains open.
  Deferred: Final-candidate checks depend on frozen inputs and V1S-088 paired
  acceptance; authority: release owner; revisit: after V1S-081/084/088 produce
  the candidate.

#### Final frozen-candidate acceptance and release

**Parent:** [Final 1.0 acceptance](#final-10-acceptance).
**Project domains:** Data processing, Web backend, Web frontend, Project infrastructure, Deployment

The current input baseline is pinned and artifact-validated; its source inventory
and remaining source/browser dispositions are recorded in the
[coverage audit](v1.0-source-coverage-audit.md). V1S-082 owns the remaining
source-to-browser gap review; final release acceptance remains open.

- [ ] **V1S-082 (L, gate):** Resolve confirmed source-to-normal-browser
  gaps and review all explicit omissions under the 1.0 definition.
  The [coverage audit](v1.0-source-coverage-audit.md) records accepted bounded
  glossary/Label corrections and the remaining source inventory. The
  [Trait definition review](v1.0-source-coverage-audit.md#v1s-082-bounded-source-review-trait-definition-conditions-2026-11-06)
  and [Attribute definition review](v1.0-source-coverage-audit.md#v1s-082-bounded-source-review-attribute-definitions-and-dash-prerequisites-2026-11-06)
  passed their bounded source/API/browser and cumulative checks under retired
  VR-0115/0117. Continue the wider source inventory; these results do not approve
  the frozen release candidate. The [Hackable profile-help review](v1.0-source-coverage-audit.md#v1s-082-bounded-source-review-hackable-profile-help-2026-11-06)
  now publishes default Troop Type/Hacker conditions and per-Program target
  scope; its source/API/browser execution remains under VR-0118.
  The [coverage optimization plan](v1.0-coverage-workflow-plan.md) introduces a
  read-only, source-family batch planner built on the existing identity/locator
  inventory (currently 466 records / 830 source locators). Its output is triage
  only; it does not retire any source or browser acceptance obligation.
  A fixed [35-record pilot](v1.0-coverage-workflow-plan.md#p1--tracked-disposition-and-source-evidence-contract)
  spans 10 cohorts and three source-first probes; its read-only work packet reports
  129 citation occurrences, 125 exact source/page/heading locators and 97
  `(sourceId, page)` buckets. The 97 buckets are not distinct pages: 9
  page-less Wiki locators carry explicit archive `member` identities, giving
  104 known source pages. The planner preserves those members and reports 25
  citation-occurrence page-reuse candidates; it suppresses page totals and the
  reuse estimate if any identity is missing or ambiguous. Neither locator
  count nor candidate reuse is measured review time, actual source opens or
  saved work. Including the three source-first probes yields a 26/132 (19.7%)
  citation-occurrence ceiling under one-open-per-citation assumptions, still
  not a measured effort reduction.
  The source-only pilot has now screened **35/35 distinct identities** at
  selected-clause scope across 39 record-cohort screen events, with **0/35
  whole-record or current-revision browser approvals**. The Trait cohort
  repeated four identities from the initial seven; the earlier 22/35 figure
  after the State cohort counted those repeats as new identities and is
  corrected in the audit to 18/35 distinct identities across 22 screen events.
  The three source-first control-page probes were screened separately; their
  scoped prose review found zero newly confirmed unowned concepts, not whole-
  page acceptance.
  The Doctor/Engineer batch records the unresolved bilingual contact-condition
  discrepancy **SRC-034**. The weapon-profile batch rechecked existing
  **SRC-020** and **SRC-021** without resolving either conflict. The Trait
  cohort reuses unchanged records and prior bounded source/API/browser evidence;
  **SRC-002** remains unresolved. The
  [State cohort review](v1.0-source-coverage-audit.md#v1s-082-fixed-pilot-state-cohort-2026-11-06)
  identified a missing Isolated/Loss-of-Lieutenant clause against agreeing
  English/Spanish N5.3 sources. The three owning curated records now jointly
  encode the bilingual timing distinction and typed Lieutenant-to-rule link;
  a guarded v9 promotion changed exactly those records and verified matched
  publications.
  VR-0122 has focused source/API/browser passes, but its first cumulative
  run identified a summary-layout failure and brittle browser assertions.
  The guarded paragraph-only repair is published; the corrected full
  cumulative rerun remains pending. No whole-record acceptance follows. The
  [Terms, Attribute and Equipment screen](v1.0-source-coverage-audit.md#v1s-082-fixed-pilot-terms-attribute-and-equipment-2026-11-06)
  confirms the bilingual Firewall/TinBot and MOV clauses. Direct normal-browser
  assertions for the MOV glossary anchor and TinBot source-169 Firewall variant
  usage passed all six focused Chromium cases under VR-0124; matched
  cumulative acceptance and individual VR closeout remain pending. The
  [remaining Core, Conditional Skills and Declaration Metadata screen](v1.0-source-coverage-audit.md#v1s-082-fixed-pilot-remaining-core-conditional-skills-and-declaration-metadata-2026-11-06)
  retains existing source scopes and leaves the Dodge PDF/Wiki modifier
  discrepancy **SRC-006** unresolved. These results remain screening evidence,
  not completed semantic or browser acceptance; reviewer time was not measured
  for that fixed screen. A separate [40-record mixed-screen benchmark](v1.0-source-coverage-audit.md#v1s-082-mixed-screen-benchmark-2026-11-06)
  logged page-access events and wall time, but did not measure active effort or
  establish full-review savings. Its six unresolved scoped decisions and four
  browser observations are not whole-record or browser approvals.
  Next: rerun the cumulative Linux gate on the repaired matched artifacts
  and reconcile all five due VR entries individually. The earlier failed
  5,365-pass Linux run, exact repair and focused outcomes are
  [recorded](v1.0-source-coverage-audit.md#v1s-082-vr-drain-movtinbot-browser-checks-and-isolated-repair-2026-11-06).
  Then reconcile **SRC-002**, **SRC-006**, **SRC-020**, **SRC-021** and
  **SRC-034** without inventing rules. The P1 tracked
  disposition schema and read-only fingerprint validator now have four
  source-specific scoped approvals across two Trait identities
  ([evidence](v1.0-source-coverage-audit.md#v1s-082-p1-source-clause-evidence-deployable-and-target-attribute-2026-11-06)).
  Browser and whole-record acceptance remain open; extend evidence from
  independent clause reviews, then benchmark equal-scope active repeated
  effort with independent quality controls.
- [ ] **V1S-083 (M, gate):** Verify disclosure of source conflicts
  and empty/unavailable/not-applicable semantics.
- [ ] **V1S-084 (M, gate):** Rebuild and verify the release-matched
  Army/rules pair, FAQ parity, deployed objects and processed symbols.
- [ ] **V1S-085 (M, gate):** Run source occupancy, archive,
  strict interaction, baseline and reproducibility gates; distinguish
  [physical SQLite byte differences](v1.0-source-coverage-audit.md#cross-host-rules-rebuild-comparison-v1s-032-validation-2026-11-04)
  from logical equivalence.
- [ ] **V1S-086 (M, gate):** Run final-candidate rule-fragment
  and broader source-to-browser checks; identify uncovered routes.
- [ ] **V1S-087 (L, gate):** Run the 81-page local Unit matrix
  and exact-version hosted representative checks.
- [ ] **V1S-088 (M, gate):** Repeat all 24 core-scenario
  configurations and FAQ source/browser acceptance.
- [ ] **V1S-089 (M, gate):** Obtain manual Silhouette
  hover/keyboard/touch/theme/narrow-width and human visual sign-off.
- [ ] **V1S-090 (L, gate):** Drain due VD/VR work and run the full
  local/Linux, source, docs, preflight and applicable full-asset checks.
- [ ] **V1S-091 (L, gate):** Audit the complete tracked Markdown
  corpus, links, commands, contracts and browser copy.
- [ ] **V1S-092 (M, gate):** Finalize Unreleased notes,
  release metadata and version after completeness acceptance.
- [ ] **V1S-093 (L, gate):** Merge the approved candidate, obtain
  exact-main-SHA hosted Source, wheel and deployment smoke evidence,
  optional full-assets and annotated tag.
- [ ] **V1S-094 (L, external):** With explicit operator approval,
  deploy the tagged artifact and verify recovery assets exist.
  A live-host rollback rehearsal is not required.
- [ ] **V1S-095 (M, gate):** Verify the deployed exact source/runtime
  pair, release version, static assets and representative browser paths.

### Source inventory and gap batches

**Project domains:** Data processing, Project infrastructure

The [source-coverage audit](v1.0-source-coverage-audit.md) owns reviewed
dispositions, source identities and confirmed omissions. These tasks own the
remaining work; the final-input freeze and complete release check remain
V1S-081–085 rather than independent acceptance ledgers.

- [ ] Reconcile the final pinned Army, N5.3 Rules, Wiki, FAQ, annex, scenario and
  symbol inputs against the complete source-section-to-storage-to-browser
  inventory. Identify every material omitted fact, relationship or ordinary
  browser route; distinguish a confirmed defect from a source conflict,
  unreviewed clause or deliberate exclusion. Re-run the
  [source-evidence tools](testing.md#10-source-evidence-baseline) and strict
  interaction-catalog scope check on the frozen pair.
  Review the newly available [PDF revisions](n5-source-history.md#local-pdf-revision-inventory-2026-11-06),
  including ITS 18 version 2026.09.11 in both languages, before selecting the
  final ITS input; compare content and migrate affected citations explicitly.
  Current citations remain pinned to 2026.09.01.
- [ ] Finish official N5 change-post reconciliation, explicitly including the
  N5.3 post, Spanish-only cases, all 20 Army-update subjects and nine added
  FAQ rulings. Compare announcements with pinned primary sources; close the
  [reconciliation inventory](rules-explanation-audit-1.0-n5.3-reconciliation.md#current-reconciliation-inventory-2026-10-29)
  without inventing historical deltas. Unanswered publisher questions, such as
  optional Reinforcements authority, remain in the [SRC register](official-source-clarifications.md).
- [ ] Reconcile the final `data/curated/rules-interactions/reviews.json` and
  `catalog-scope.json` with all current in-scope identities and cited
  exceptions, retaining historical review decisions without treating them
  as whole-record approval. Final source-clause and browser acceptance belong
  to the [completeness gate](releasing.md#version-10-data-completeness-gate).

The [bounded source/relationship findings](n5-source-history.md) and
[ranked gap batches](v1.0-source-coverage-audit.md#ranked-confirmed-gaps-and-evidence-batches-v1s-022-2026-11-03)
remain evidence, not extra TODO entries. Final human visual sign-off is owned
by V1S-045/089 and the [release checklist](releasing.md).

### Rules and reference completeness

**Project domains:** Data processing, Web backend, Web frontend

The [rules explanation audit](rules-explanation-audit-1.0.md) and
[source-coverage audit](v1.0-source-coverage-audit.md) own detailed
findings and historical test results. Existing Skill, Equipment,
General Rule, State, Trait, Attribute, FAQ, scenario and Weapon
definitions are the foundation; the tasks below cover outstanding
source clauses, semantics and release publication, not a rebuild
of already-reviewed catalogs.

- [ ] Close the remaining versioned N5.3 rules-reference and explanation
  gaps by source section and semantic family. Reconcile the frozen
  [367-record clause inventory](rules-explanation-audit-1.0-inventory.md#audit-completion-gate)
  with the current Core/Hacking catalog and later source/browser evidence;
  historical D/S labels, cited pages and selected browser tests do not imply
  full-record acceptance.
  - [ ] Review remaining source clauses and material conditional declaration,
    ARO and reactive-eligibility cases beyond the bounded
    [V1S-030 sample](v1.0-source-coverage-audit.md#conditional-declaration-and-reactive-eligibility-follow-up-v1s-030-2026-11-04).
    For each material interaction, verify conditions, baseline, modifiers,
    exceptions, effect and uncertainty against
    [the explanation standard](../data/curated/README.md#explaining-rules-interactions)
    and its ordinary browser presentation. Do not infer a general legality
    or combat-resolution engine.
  - [ ] Curate confirmed missing facts, links or explanations across Skills,
    Equipment, Weaponry, Ammunition, Traits, States, Fireteams and glossary
    terms. Preserve versioned source provenance and scoped application
    identities, and extend the validated fact vocabulary where required.
    Do not duplicate Hacking Program facts or create a separate
    scenario-only identity for a shared rule.
  - [ ] Verify remaining Weapon Properties, special weapons, auxiliary
    equipment/objects, mode-specific prose and unreviewed N5.3 Weaponry
    clauses. Keep combined-effect relationships distinct from raw Traits
    and source-specific discrepancies; selected examples are not a
    whole-Weaponry audit.
- [ ] Reconcile reviewed base and combined Ammunition, Attribute Immunity,
  critical and State interactions against the final pinned Weapon/Rules
  publication. Preserve composition versus Combined Saving Rolls, conditional
  exceptions and cited uncertainty; unanswered
  [SRC-002](official-source-clarifications.md#src-002--silent-versus-attribute-immunity-bilingual-qualifier)
  does not require a publisher response before 1.0.
- [ ] Accept the published, separately scoped optional Reinforcements
  Section/profile/Commlink reference on release-matched inputs and ordinary
  desktop/mobile browser routes under **V1S-041**. Disclose its N4-origin
  procedures without asserting N5-native adoption or roster legality;
  [SRC-030](official-source-clarifications.md) is non-blocking.

- [ ] **Core scenarios:** Finish the four published scenarios' final
  source-to-storage-to-browser reconciliation and keyboard/touch/theme/
  narrow-width acceptance. Keep scenario-only concepts, spatial geometry,
  derived SVG, scoped FAQ and ordinary rules links consistent; use
  **V1S-045/088** for frozen-candidate checks and
  [the scenario contract](data-model.md#scenario-model-implemented-core-and-future-extensions).
  A live scoring or match-state engine is not required.

- [ ] **FAQ/errata:** Repeat the reviewed 29-ruling/48-topic source,
  supersession, exclusion, applicability and normal-browser acceptance
  on the final paired rules database under **V1S-084/088**. Maintain
  core-versus-ITS scope, provenance and conservative disputed-source
  disclosure; historical season replay and external rulings are not
  1.0 prerequisites. See the
  [FAQ contract](data-model.md#dated-faqerrata-layer-published-reviewed-subset).

- [ ] **Rule-variant usage projection:** Accept the byte-exact tracked
  `variant-usage.json` artifact, its deployment/image guards and Skill/Equipment
  API/browser links against the **frozen** release source/runtime pair. The
  [development source-pair/API/browser acceptance](v1.0-source-coverage-audit.md#full-exact-variant-usage-source-pair-acceptance-2026-11-05)
  is complete; final candidate, exact-SHA hosted and deployed checks remain.
  - [ ] Reconcile any newly reviewed exact occurrence parameters,
    reused payloads, shared Unit options, Include/Peripheral paths and
    incompatible/unknown signatures against final input revisions. Fail
    closed when Army/profile membership or a typed variant cannot be
    established; do not attribute source-only rows as direct uses.
    Use the [variant contract](data-model.md#current-read-only-variant-candidate).
  The reviewed Restrictions chart/projection and staging safety are
  implemented. Real-host v8/v9 rollback rehearsal is not required for 1.0.

- [ ] **Game States:** Add any genuinely missing contextual links revealed
  by final Fireteam, Hacking, Ammunition, FAQ and scenario review.
  Distinguish entry, cancellation, immunity and objective effects;
  check reciprocal navigation and do not infer a Unit's live game State.

- [ ] **Weapons and deployed objects:** Resolve any final-input
  Weapon-profile, Ammunition/Trait relationship and deployed-object
  source/publication omission. Repeat normal browser reachability and
  source-context checks for shared carriers, delivery modes, Include
  edges, variants and known/unreported/disputed attributes under
  **V1S-081–088**. The
  [Weapon profile](data-model.md#weapon-profile-row-and-api-contract) and
  [deployed-object](data-model.md#deployed-object-read-model-and-artifact-gated-browser-reference)
  contracts own implemented behavior; comparison controls are post-1.0.
  Keep unresolved Mine/Dazer/Armed Turret differences disclosed.

### Player-facing navigation and reference clarity

**Project domains:** Web frontend, Project infrastructure

- [ ] Complete final-candidate touch, 320/390px responsive and theme
  acceptance of the floating accuracy notice and navigation under
  **V1S-080**. The 7/7 human screen-reader walkthrough passed under
  retired V1S-079; its reported result and the earlier automated focus,
  announcement and notice regressions are recorded in
  [testing](testing.md#parallel-windows-development-and-linux-validation).
  The [web design guidelines](web-design-guidelines.md) own the UI contract.

### Final 1.0 acceptance

**Project domains:** Data processing, Web backend, Web frontend,
Project infrastructure, Deployment

- [ ] Complete **V1S-081–095** against the exact frozen source,
  database, generated-publication, static-asset and release-candidate
  revisions. This includes full source/semantic/browser disposition,
  81-page Unit matrix, core scenario and FAQ gates, manual Silhouette
  and visual acceptance, all due VD/VR checks, full local/Linux checks,
  documentation audit, exact-SHA hosted CI, annotated tag, authorized
  deployment and post-deploy smoke. Use the
  [canonical release checklist](releasing.md); keep detailed commands,
  logs and intermediate acceptance counts in their maintained owners
  rather than a second checklist here.
  Preserve unresolved but accurately disclosed publisher issues as
  non-blocking; verify recovery assets without requiring a live-host
  rollback rehearsal.

## Post-1.0 — maintenance and product expansion

These items are intentionally outside the 1.0 completeness gate. They may move earlier
only when required to fix correctness, reproducibility, or release reliability.

### External source clarifications

**Project domain:** Data processing

- [ ] Prepare and submit consolidated publisher questions from the
  [SRC register](official-source-clarifications.md), including
  SRC-002 and SRC-030; record dated official responses under their
  stable IDs and open implementation tasks only when needed.
  Unanswered questions do not block 1.0 when the player-facing
  uncertainty is accurately disclosed.

### Source notation and rule references

- [ ] **Data processing + Web frontend:** Give Weapon Chart footnote markers
  (such as `[*]`, `[**]`, `[***]`) contextual, clickable rule references instead
  of treating them as ordinary Traits. Use the published chart legend to identify
  the section category (Weaponry, Ammunition, or Skills and Equipment), then
  resolve the actual target by source publication, chart row/mode, and owning
  rule section (e.g. Mines or Sepsitor), preserving any mismatched
  notation from Army and the PDF. Consider tooltips or short explanations and
  a direct Glossary/rules link; retain raw provenance and explicit unresolved
  mappings. Do not require this richer display for 1.0 completeness.

### Per-reference change history

- [ ] **Data processing + Web backend + Web frontend:** Add optional
  **historical FAQ edition replay and source-date/season selection**,
  separate from the 1.0 current-reference API. Independently curate
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
  for 1.0. Review any source-chart exclusions through the existing 1.0 inventory.

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
  **Strictly post-1.0:** this accepted feature does not expand the 1.0 release
  gate. Multi-selection and per-filter AND/OR/NOT remain separate proposed
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
  is disabled by default and is **not a v1.0 completeness gate**.
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

- [ ] **Post-1.0 infrastructure research — deferred:** Continue the
  [Chromium lifecycle and concurrency investigation](testing.md#controlled-chromium-concurrency-and-browser-reuse-benchmark)
  after v1.0 ships. The v1.0 instrumentation gates (VR-0023/24) are
  complete; Linux uses its validated four-slot profile, Windows retains
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
    None of these investigations blocks the v1.0 release unless new
    evidence reveals a release-critical defect.

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
work, and external-tool portability. It is outside the 1.0 application-data gate. The implemented
pipeline and artifact lifecycle are described in [data guidance](../data/README.md).

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
    is evidence triage, not semantic acceptance. This is **post-1.0**, not
    a core-rule release blocker.
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
  published Season 18 Battleground pilot without treating it as a 1.0 gate.
  - [ ] Curate the remaining Season 18 mission identities and complete
    source-backed definitions under the reviewed selected 2026.09.11 hotfix
    identity once its source promotion is accepted; retain
    `its-18@2026.09.01` for historically scoped results. Extend typed
    geometry, scoring and card/classified choices only where each mission
    needs them. Unpublished missions must fail closed.
  - [ ] Capture structured, cited scenario facts: objectives and scoring, game
    rounds/end conditions, force/point/SWC/table/deployment configuration,
    deployment map or geometry, exclusion zones, token types/diameters,
    classified-objective setup, reinforcement suitability, tactical-support
    options, and scenario-specific rules/elements.
  - [ ] Scenario pages should expose the selected season prominently and link
    season-specific terms to the relevant rules/state references.

- [ ] **Data processing + Web frontend:** Extend the 1.0 core-scenario SVG renderer for ITS
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

- [ ] **Data processing + Web frontend:** Build a **post-1.0 scenario creator/editor**
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
  The editor remains post-1.0, independent of core-scenario release acceptance.

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
