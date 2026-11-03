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

Version **0.10.1** was released and deployed on 2026-10-10. The current
development milestone is **1.0.0 — current-reference completeness**.
Completed Scenarios, Ammunition, rules-reference and stabilization changes
belong to the [0.10.1 changelog](CHANGELOG.md#0101---2026-10-10), not a
pending release checklist.

Release history belongs in [the changelog](CHANGELOG.md#0101---2026-10-10).
Earlier offline and bounded development-browser checks do not establish final
1.0 acceptance. Current test/verifier procedures belong in [testing](testing.md);
the [release checklist](releasing.md) requires fresh evidence for the final candidate.

General performance/storage experiments, major pipeline refactors,
persistent-user-data features, ITS content/season/tournament tooling and native
applications remain post-1.0 unless needed to fix release-critical defects.
Previously implemented ITS content is retained but is not a 1.0 requirement or
release blocker. The four N5 core-rules scenarios remain in 1.0 scope.

The public roadmap lives in README.md; the durable 1.0 release gate
lives in docs/releasing.md. All unchecked tasks below belong to 1.0
or post-1.0.

## 1.0.0 — current-reference completeness gate

1.0.0 is the final completeness release for the supported current reference data. It
should resolve remaining material source/rules gaps, certify completeness of the published
core-scenario reference surface, and validate the whole application without expanding into
broader ITS/tournament tooling.

### Implemented foundations and remaining scope

**Project domains:** Data processing, Web backend, Web frontend, Project infrastructure

These foundations are implemented; final source-to-browser acceptance remains separate:

- Four Core scenarios and the optional ITS Season 18 Battleground pilot, shared
  scenario components, scoped Rules/Skills and deterministic maps:
  [current scenario contract](data-model.md#scenario-model-implemented-core-and-future-extensions).
- Eleven base Ammunition references, reviewed combined forms, Weapon Properties,
  shared/specific Weapon definitions and disclosed source discrepancies:
  [data model](data-model.md#pipeline-and-persistent-artifacts).
- Twenty-nine dated FAQ rulings, twenty carried from v0.0, with validated
  applicability, supersession, explicit-context API and topic/scenario cards:
  [published FAQ contract](data-model.md#dated-faqerrata-layer-published-reviewed-subset).
- Martial Arts, Booty and MetaChemistry typed, linked charts with reviewed PDF,
  Wiki-history and FAQ evidence:
  [structured charts](data-model.md#structured-skill-reference-charts) and
  [source provenance](n5-source-history.md#reviewed-10-structured-skill-chart-provenance).
- Reviewed exact source variants, including Mimetism, Berserk and Dodge mappings;
  the cross-army usage index remains unimplemented:
  [variant contract](data-model.md#rule-variant-usage-index--accepted-design-direction-not-implemented).
- Published deployed-object profiles, delivery paths and typed reverse uses:
  [current contract](data-model.md#deployed-object-read-model-and-artifact-gated-browser-reference).
- The optional Reinforcements reference and typed Commlink (+1)/(+2) Army extras
  are published in the guarded v9 rules pair. N5-native annex authority and final
  release/browser acceptance remain separate:
  [scoped contract](rules-semantics.md#rs-rf-scope-001--reinforcements-is-a-separately-scoped-annex-not-core-n5-rules-data).
- The interaction-review ledger passes its current supporting-identity slice with
  zero pending entries. Its default primary scope is historical; strict 1.0 primary
  acceptance remains separate, as does full clause/source review:
  [generated checklist](rules-interaction-checklist.md).
- Source archive/storage/API parity checks, optional Chromium verifiers and an
  exact-runtime hosted candidate verifier exist:
  [validation procedures](testing.md#10-source-evidence-baseline).
  Local development-browser passes do not accept a future release or deployment.

### Development sequence

**Project domains:** Data processing, Web backend, Web frontend, Project infrastructure

This sequence organizes the remaining work around the implemented foundations above;
it is not a new completeness definition or a claim that those foundations are absent. Use [the release gate](releasing.md#version-10-data-completeness-gate)
to decide whether a gap blocks 1.0. Do not wait until release preparation to discover missing
information or browser surfaces.

| Stage | Reviewable output | Dependencies |
| --- | --- | --- |
| 1. Inventory and scope | Pinned inputs, source-to-browser coverage inventory, prioritized gap batches | Existing Army/rules databases and audit tools |
| 2. Remaining semantics | Unresolved exact variants, combined-effect boundaries and supported Reinforcements annex facts | Inventory; reuse current scoped identity, FAQ, Ammunition and scenario contracts |
| 3. Complete vertical slices | Remaining catalog/FAQ coverage and final four-Core-scenario reconciliation | Relevant Stage 2 contract; each slice includes storage, API and usable browser access |
| 4. Derived references | Variant usage index; remaining Restrictions and Deployables gaps/acceptance | Reviewed owning facts and exact variant/scope semantics; declaration matrix and linked charts are published; comparison controls are optional |
| 5. Closeout | Reconciled completeness evidence and final release acceptance | Every in-scope gap resolved; canonical release checklist |

Stages may overlap where dependencies are satisfied. In particular, ordinary catalog curation can
continue alongside remaining shared-semantic work, and projections need only their owning facts to
be ready. Keep model/export, curation, backend, and browser substeps visible under each open parent;
a populated JSON collection alone does not complete a player-facing task.

For each implementation slice, record the source/version being covered, remaining decisions,
affected canonical documents, and evidence needed to close it. Extend existing validators and
audit tools before introducing another coverage system. Keep new private evidence under
ignored `local/audits/` (legacy ignored `reports/` and `docs/audits/` remain supported);
keep maintained semantic decisions in validated curated data or configuration.
Use [the standard checks](testing.md) for the affected contracts, and add manual
browser acceptance for new visual/interaction surfaces. Promote durable contracts to their
canonical owners as implementation lands; keep remaining design extensions explicitly labelled
as unimplemented and distinguish them from the published core-scenario foundation.

### Pre-planned 1.0 execution slices

**Planning baseline:** dev/v1.0.0 at dd071c4d (2026-11-03). This is the
actionable slice register for the nine open 1.0 parent outcomes below, not a
second release gate or a new interpretation of historical audit counts.
Each numbered slice maps to the named parent section; the existing parent and
nested acceptance conditions still govern closure. For a new implementation
pass, select a ready slice here rather than inventing another ad hoc subdivision.
Remove completed slices as part of the normal backlog retirement rule; Git
history retains the original estimate and result.

**Sizing:** S = one bounded source decision/check or focused change (1 unit);
M = a small, independently reviewable multi-step source/data/browser slice
(2 units); L = a larger bounded multi-family or end-to-end gate (4 units).
Units are relative planning weights, **not days, hours or commitments**.
A review may close as source-verified no-change; a conditional slice produces
code only when the reviewed source confirms a gap. Source uncertainties,
newer inputs and previously undiscovered 1.0 omissions can expand the plan.
Labels: **review** = evaluate evidence, **design** = settle a contract,
**build** = implement, **gate** = verify/accept, **decision** = settle
a supported boundary, **conditional** = only for confirmed additions,
**external** = independent authorization/dependency.

**Shared completion rule:** Every implementation slice must specify its
pinned source/variant, affected maintained model/export, API and ordinary
browser entry point (or a justified no-change), essential regressions,
deferred validation-queue obligations and documentation handoff. No slice
alone replaces final source-wide or release-candidate acceptance. Work on
independent slices can overlap Linux validation of an earlier committed
revision, following the established dispatch-and-continue protocol.

#### Source baseline, reconciliation, and gap discovery

**Parent:** [Source inventory and gap batches](#source-inventory-and-gap-batches).
**Project domains:** Acquisition, Data processing, Project infrastructure, Web backend, Web frontend

- [ ] **V1S-014 (M, review):** Audit Unit option Includes, Peripheral/controller ownership and resolved
  profile/loadout identities across the current Army input.
- [ ] **V1S-015 (M, review):** Audit Fireteam availability, Reinforcement parent/pool context and ordinary
  Unit/Army/Section browser reachability.
- [ ] **V1S-016 (L, review):** Give Core/Hacking PDF sections and current curated families a
  source-to-storage-to-browser disposition, not citation-only approval.
- [ ] **V1S-017 (M, review):** Review Wiki-backed Skills, Equipment, Terms, Traits and special source wording
  for missing facts, relationships and normal links.
- [ ] **V1S-018 (M, review):** Account for four core scenarios, FAQ, symbols and other source categories in
  the category-level coverage ledger.
- [ ] **V1S-019 (M, review):** Triage further Weapon Properties, exceptions, non-four-attribute entries and
  remaining Weaponry clauses; separate prose from missing facts.
- [ ] **V1S-020 (M, review):** Verify final FAQ v0.1 source hashes and applicability and classify optional
  Reinforcements N4 PDFs correctly.
- [ ] **V1S-021 (M, gate):** Reconcile interaction review and catalog scope with current release identities;
  run the strict 1.0 primary guard without rewriting history.
- [ ] **V1S-022 (M, gate):** Produce ranked confirmed-gap batches with source/version, owner, normal browser
  entry point and required checks; explicitly exclude conjecture.

#### Rules and contextual reference completion

**Parent:** [Rules and reference completeness](#rules-and-reference-completeness).
**Project domains:** Data processing, Web backend, Web frontend

- [ ] **V1S-024 (M, review):** Review remaining Skills by semantic family for missing definitions, typed facts
  and source-backed browser links.
- [ ] **V1S-025 (M, review):** Review Equipment and exceptional Army gear wording, including nonstandard
  attributes and source-scoped semantics.
- [ ] **V1S-026 (M, review):** Review other canonical Rules, game terms, training, scenario terminology and
  glossary coverage without duplicating Hacking Programs.
- [ ] **V1S-027 (M, review):** Review remaining States, Traits, Attributes and reference links; keep in-game
  States separate from static profiles.
- [ ] **V1S-028 (M, review):** Reconcile player-facing cross-source conflicts, FAQ applicability and explicit
  uncertainty before publishing dependent summaries.
- [ ] **V1S-029 (L, review):** Join the 367 frozen explanation-audit records to the current Core/Hacking set
  and later reviewed evidence; preserve original counts.
- [ ] **V1S-030 (M, review):** Review conditional declaration, ARO and reactive eligibility clauses outside
  the already accepted exception examples.
- [ ] **V1S-031 (S, gate):** Give the five newer Visibility Zone terms independent whole-corpus and
  source/browser dispositions.
- [ ] **V1S-032 (M, review):** Review unaccepted Orders, game phases, command and activation rule clauses with
  player-facing conditions and exceptions.
- [ ] **V1S-033 (M, review):** Review movement, visibility, geometry, positioning and terrain clauses for
  missing operative conditions.
- [ ] **V1S-034 (M, review):** Review remaining attacks, Weaponry, mode, ammunition and state interaction
  clauses against exact source text.
- [ ] **V1S-035 (M, review):** Review unaccepted Hacking, firewall, Supportware and scoped interaction
  clauses, without recreating existing program facts.
- [ ] **V1S-036 (M, review):** Review remaining component Immunity and combined-effect precedence cases with
  exact target, source and non-executable semantics.
- [ ] **V1S-037 (M, review):** Review BTS/non-Comms Weapon exceptions, Criticals, affected attributes and
  conditional State relationships separately.
- [ ] **V1S-038 (M, gate):** Reconcile every published base and combined Ammunition fact against pinned Weapon
  data and validate stored/API/browser semantics.
- [ ] **V1S-039 (M, review):** Review shared core/scenario concepts and collection supplements for scoped
  applicability, leakage and browser explanation.
- [ ] **V1S-040 (M, decision):** Document N5-native Reinforcements authority if available, or preserve
  disclosed optional legacy reference and SRC-030 follow-up.
- [ ] **V1S-041 (M, gate):** Accept Reinforcement Section, profile and exact Commlink variants in ordinary
  browser/release context, without asserting roster legality.

#### Four core scenarios

**Parent:** [Core-scenario reference completion](#rules-and-reference-completeness).
**Project domains:** Data processing, Web backend, Web frontend

- [ ] **V1S-042 (M, review):** Reconcile objective, setup, scoring and ending facts for the four core
  scenarios against their pinned source sections.
- [ ] **V1S-043 (M, gate):** Verify source geometry, markers, 24 points/distance configurations and
  deterministic map publication.
- [ ] **V1S-044 (M, gate):** Verify scoped Skills, Specialist roles, scenario overlays and FAQ links without
  ITS-season or core-rule leakage.
- [ ] **V1S-045 (M, gate):** Run normal browser accessibility/navigation, desktop/mobile/theme/rapid-selection
  and empty/error acceptance on final inputs.

#### FAQ and errata

**Parent:** [Dated FAQ/errata acceptance](#rules-and-reference-completeness).
**Project domains:** Data processing, Web backend, Web frontend

- [ ] **V1S-046 (M, review):** Reconcile all 29 published rulings, original citations and 48 topic
  associations to the final pinned FAQ/core sources.
- [ ] **V1S-047 (M, review):** Review carried-forward versus newly added FAQ identities, supersession and
  effective source/season boundaries.
- [ ] **V1S-048 (M, gate):** Verify source precedence, disputed interpretations, excluded ITS-only answers and
  explicit uncertainty in public API output.
- [ ] **V1S-049 (M, gate):** Recheck discoverability, topic/scenario reverse links and base-rule versus
  clarification presentation in ordinary browser.

#### Rule-variant usage index and Restrictions

**Parent:** [Generated rules-reference projections](#rules-and-reference-completeness).
**Project domains:** Data processing, Web backend, Web frontend, Deployment

- [ ] **V1S-050 (S, review):** Resolve Infiltration's five bare ReRoll occurrences only with explicit source
  authority; preserve the five reviewed fixed-PH values.
- [ ] **V1S-051 (S, review):** Review exact Engineer occurrence parameters and operational exceptions; no
  unsupported generic modifiers.
- [ ] **V1S-052 (S, review):** Review exact Doctor occurrence parameters independently of Engineer and
  preserve source-defined differences.
- [ ] **V1S-053 (S, review):** Investigate the Religious Troop/Total anomaly (SRC-028) against raw Terrain and
  profile sources; do not invent a correction.
- [ ] **V1S-054 (M, review):** Review Immunity source-162 occurrence signatures, especially combined/base
  component boundaries.
- [ ] **V1S-055 (M, review):** Review BS Attack source-201 variants and modifiers, preserving ordered raw
  signatures.
- [ ] **V1S-056 (M, review):** Review CC Attack source-240 variants and distinct attribute/attack conditions.
- [ ] **V1S-057 (M, review):** Review Peripheral source-243 modifiers and separate controller/attached option
  contexts.
- [ ] **V1S-058 (M, review):** Review Transmutation source-246 exact profile transition and qualifier
  semantics.
- [ ] **V1S-059 (S, review):** Review Journalist source-272 qualifiers and establish whether a typed rule
  variant is justified.
- [ ] **V1S-060 (M, review):** Review Hacking Device Plus source-101 compound/Upgrade Programs signatures
  without inferring extra Program access.
- [ ] **V1S-061 (M, review):** Run cross-family TEXT/DISTANCE, named MOD and unusual variant consistency
  sweep; classify remaining unknowns fail closed.
- [ ] **V1S-062 (M, design):** Finalize occurrence identity, ordering, duplicate-handling and
  Unit/profile/loadout/Army ownership contract for the usage index.
- [ ] **V1S-063 (L, build):** Generate and validate exact-variant occurrence projections from matched
  Army/rules data, including Includes and Peripherals.
- [ ] **V1S-064 (M, build):** Expose source-scoped variant usage through a stable API/read model with negative
  and duplicate-source cases.
- [ ] **V1S-065 (M, build):** Add discoverable ordinary reference links from canonical Skill/Equipment
  variants to Unit/profile/loadout occurrences.
- [ ] **V1S-066 (M, gate):** Validate full cross-Army publication parity, unknown exclusion, browser coverage
  and source-pair freshness for the new index.
- [ ] **V1S-067 (M, external):** With separate authorization, rehearse Restrictions v8/v9 real-host
  rollback/forward; CI simulation is not host acceptance.

#### Game States context

**Parent:** [Contextual Game States](#rules-and-reference-completeness).
**Project domains:** Data processing, Web backend, Web frontend

- [ ] **V1S-068 (M, review):** Inventory new state references from Fireteam, Hacking, ammunition, scenarios
  and FAQ; classify entry/cancellation/override.
- [ ] **V1S-069 (M, gate):** Curate only source-backed missing links and verify two-way Rule/State browser
  navigation, conditions and scope.

#### Weapons, Ammunition and deployed objects

**Parent:** [Weapon, Ammunition and Deployable presentation](#rules-and-reference-completeness).
**Project domains:** Data processing, Web backend, Web frontend

- [ ] **V1S-070 (M, review):** Audit single/multimode, multi-ammunition and Combined Saving Roll
  source/profile presentation in the existing catalog.
- [ ] **V1S-071 (M, design):** Specify any missing structured mode/profile/conditional/sentinel fields before
  frontend changes; do not parse display strings.
- [ ] **V1S-072 (L, gate):** Reconcile the full published Weapon profile set through storage, API and browser,
  including range, damage and Traits.
- [ ] **V1S-073 (M, review):** Extend deployed-object discovery across independent N5 tables, unusual
  Weapon/Equipment entries and alternate wording.
- [ ] **V1S-074 (M, review):** Review scenery, Gate glossary terms, terrain combinations and scenario
  elements; classify devices versus non-devices.
- [ ] **V1S-075 (M, review):** Rerun source snapshot and full-depth Include audits; preserve exact Army,
  Unit-option and profile ownership.
- [ ] **V1S-076 (M, review):** Audit reverse-use delivery, carrier and source-position edges; avoid inferred
  uses from prose.
- [ ] **V1S-077 (L, conditional):** For each confirmed new object or edge, extend curated inventory,
  deterministic publication and API with targeted regressions.
- [ ] **V1S-078 (M, gate):** Accept deployed-object API/browser navigation, incomplete attributes, variants
  and documented Mine/Dazer/Turret conflicts.

#### Accessibility and navigation

**Parent:** [Player-facing navigation and reference clarity](#player-facing-navigation-and-reference-clarity).
**Project domains:** Web frontend, Project infrastructure

- [ ] **V1S-079 (M, gate):** Perform assistive-technology review of floating accuracy notice and navigation:
  roles, focus, announcement, keyboard.
- [ ] **V1S-080 (M, gate):** Verify touch, theme, narrow viewport and notice collapse/expand behavior; fix
  only reproducible 1.0 regressions.

#### Final frozen-candidate acceptance and release

**Parent:** [Final 1.0 acceptance](#final-10-acceptance).
**Project domains:** Data processing, Web backend, Web frontend, Project infrastructure, Deployment

- [ ] **V1S-081 (M, gate):** Freeze intended source inputs, tracked databases and derived asset identities;
  rerun complete category/source disposition.
- [ ] **V1S-082 (L, gate):** Close all confirmed source-to-storage-to-normal-browser gaps and review every
  explicit exclusion against the 1.0 definition.
- [ ] **V1S-083 (M, gate):** Reconcile cross-source uncertainty, empty/unavailable/not-applicable semantics
  and player-facing source claims.
- [ ] **V1S-084 (M, gate):** Rebuild/verify the release-matched Army/rules pair, FAQ parity, deployed-object
  publication and processed symbols.
- [ ] **V1S-085 (M, gate):** Run source occupancy, source/archive, strict primary interaction, reference
  baseline and output reproducibility checks.
- [ ] **V1S-086 (M, gate):** Run rule fragment and wider source-to-browser checks on the exact candidate;
  document uncovered normal entry points.
- [ ] **V1S-087 (L, gate):** Run the 81-page local Unit matrix and hosted exact-version representative checks
  with pinned assets/databases.
- [ ] **V1S-088 (M, gate):** Rerun scenario 24-configuration and FAQ browser/source gates against the
  candidate; include applicable other surfaces.
- [ ] **V1S-089 (M, gate):** Obtain manual Silhouette hover/keyboard/touch/theme/narrow-width sign-off plus
  required human visual review.
- [ ] **V1S-090 (L, gate):** Drain validation queue and run all relevant complete local/Linux full-asset,
  docs, source and preflight suites.
- [ ] **V1S-091 (L, gate):** Audit the entire tracked Markdown corpus, stale version/command references,
  canonical contracts and browser copy.
- [ ] **V1S-092 (M, gate):** Finalize coherent Unreleased notes, release metadata and version only after the
  completeness review.
- [ ] **V1S-093 (L, gate):** Merge the approved candidate and obtain exact-main-SHA hosted workflows, optional
  full-assets, evidence and annotated tag.
- [ ] **V1S-094 (L, external):** With explicit operational approval, validate retained rollback/forward
  procedure and deploy the approved tagged artifact.
- [ ] **V1S-095 (M, gate):** Verify deployed exact source/runtime pair, release version, static assets and
  representative browser paths after deployment.

**Initial sizing at this baseline:** 95 planned slices (9 S,
75 M, 11 L), **203 relative work units**.
This is an upper-level capacity indicator, not an elapsed-time forecast:
review/no-change slices may be short; full-source discovery can add new work;
separately authorized host/human checks may be schedule dependencies.
The pre-existing validation queue is not counted as new implementation.
Recalculate open counts from unchecked V1S entries as slices retire.
The initial mix is 56 review, 30 gate, two design, three build,
one boundary decision, one conditional implementation and two external
operations. These are not 95 code changes.

**Dependency order (not a serial schedule):** Source/version pinning
V1S-001–003 and the bounded current-state audits can start alongside existing
source-backed variant review V1S-050–061, published-reference verification
V1S-023, and Weapon/deployed-object discovery V1S-070–076. Source review
V1S-004–022 qualifies any new omissions; the relevant owning rules/reference
slice then addresses confirmed gaps. The variant index V1S-062–066 follows
reviewed occurrence semantics, not the other way around. V1S-081–095 are
frozen-candidate/release gates and must not be marked complete from earlier
development checks. V1S-040 can close by accurate legacy-annex disclosure
without a publisher response; V1S-067 and V1S-094 need separate operational
authorization. After a new source acquisition, revisit affected review and
downstream acceptance rather than accepting a previous baseline silently.

### Source inventory and gap batches

The [2026-10-31 source-coverage assessment](v1.0-source-coverage-audit.md)
records four confirmed core-reference/presentation gaps, two reproducible audit/test
defects and four quantified existing dependencies against `9d820602`. Its findings
are dated evidence; the unchecked tasks here own their resolution. In particular,
the enrichment report's missing standalone Weapon definitions are not 62 confirmed
missing explanations: the existing shared-effects approvals must be reconciled.

- [ ] **Data processing + Project infrastructure:** Establish the 1.0 completeness baseline
  against the final intended input set; existing bounded reviews are prerequisites.
  Weapon triage, supporting-target expectations and opt-in 1.0 enrichment
  assessment are repaired; use the [source-evidence procedures](testing.md#10-source-evidence-baseline)
  when refreshing the frozen-pair baseline, without inferring whole-source or
  browser acceptance from the historical shared-effect approvals.
  - [x] Review change-sensitive historical Wiki comparisons: the September 26
    citation replacement is verified, but the missing September 18 original
    cannot establish a before/after content delta. The bounded dispositions
    are recorded in the [source evidence](rules-explanation-audit-1.0-sources.md#historical-wiki-comparison-boundary-v1s-004-2026-11-03);
    source-wide semantic and frozen-release gates remain open.
  - [x] Select and pin the intended Army, rules/FAQ/annex and Wiki review inputs,
    including source/derived-publication identities in the
    [N5 source history](n5-source-history.md#selected-army-input-for-10-v1s-001-2026-11-03).
    Publication dates are separate from acquisition dates. A later source refresh reopens
    affected coverage; normal checks must not acquire newer inputs implicitly.
    Official update posts are supplementary change evidence, not replacements
    for versioned primary sources. Final candidate freeze is still due below.
    - [ ] Refresh the release-candidate baseline and source occupancy gate once
      the Army/rules database pair is frozen for 1.0. Do not reuse the
      pre-Peripheral-projection publication SHA or paired runtime revision.
  - [ ] Reconcile each N5 update-post changelog item with its applicable versioned
    Army snapshot, rules/FAQ PDF, exact Wiki revision, and available historical N5
    versions. Record unmatched announcement claims and unknown release/snapshot
    boundaries as open review work, not confirmed database defects.
    - [ ] **Data processing:** Before 1.0, explicitly review Corvus Belli's
      **N5.3 update blog post** and trace each published change against the pinned
      N5.3 rules, FAQ, Wiki revision and Army snapshot as applicable. Record
      affected maintained identities, confirmed mismatches, no-change results
      and unresolved source/version boundaries; update player-facing data only
      for source-confirmed discrepancies. This is a named N5.3 review within
      the wider update-post reconciliation task, not a substitute for it.
      - [ ] Close the current N5.3 reconciliation inventory against
        the final 1.0 source and browser evidence. See the
        [current disposition](rules-explanation-audit-1.0-n5.3-reconciliation.md#current-reconciliation-inventory-2026-10-29).
        Review four additional Spanish-only subjects, all 20 Army update
        subjects and the nine added FAQ rulings in their own source/scope
        boundaries. Current-rule ESX-01..04 checks have local acceptance;
        continue Army current-state coverage while preserving disclosed
        publisher conflicts and the ITS-only Ancillary ruling boundary.
        Finish release-matched database, derived-publication and browser
        acceptance without replacing the original audit's historical counts.
      - [ ] **ARMY-01 remaining semantics and release gates:** Retain the
        unresolved current N5 Reinforcements authority boundary;
        review further profile-specific annotations if the source
        inventory identifies them. The reviewed
        [Fireteam annotation contract](data-model.md#fireteams)
        does not establish a general-purpose selector or legality model.
        ARMY-02–20 native profile/loadout publication parity is recorded in
        the linked reconciliation inventory; this does not validate roster legality or
        profile-transition/upgrade semantics. Do not infer
        a historical before/after delta without an earlier
        pinned Army snapshot. Final release-matched database,
        browser and CI acceptance remain separate gates.
  - [ ] Inventory player-relevant information by source section/category, including the four core
    scenarios. For each category record its canonical identity/model, maintained input, generated
    storage, API/read path, ordinary browser entry point, rules context, and outstanding gap or
    justified exclusion. Distinguish missing facts, missing relationships, and missing presentation.
  - [ ] Reuse `audit_source_presentation.py`, `audit_enrichment_coverage.py`, and
    `audit_rules_interactions.py` as baseline evidence. Their existing Army/catalog coverage does
    not establish PDF, FAQ, or scenario completeness or prove browser usability; add the missing
    source review and presentation checks explicitly.
    - [ ] Cross-check the **derived Army relationships** that source-field occupancy alone
      cannot certify: canonical Unit/profile/loadout identities, shared Unit-option Includes,
      Peripheral/controller targets, Reinforcement parent/pool membership and Army-local
      Fireteam availability. Distinguish an existing working projection from an uncovered
      source relationship or inaccessible player-facing context; add only confirmed
      deficiencies to the owning vertical slice.
      - [ ] Reconcile normal Unit/Army/Fireteam browser reachability and applicability
        for these relationships (including Reinforcement pool context); classify any
        missing, misleading or deliberately deferred behavior with source evidence.
    - [ ] Obtain independent human visual acceptance if required for the 1.0
      release; agent-reviewed screenshots and automated browser assertions
      are evidence, not a human sign-off.
    - [ ] Continue extending the reviewed Weapon Properties inventory beyond
      Plasma, Viral, Breaker, K1, MULTI, Monofilament, Silenced, four
      AP-based combinations and the reviewed N+E/M form. Review further
      name/Traits exceptions and
      consolidate repeated weapon prose where source/mode-specific information
      remains intact. Initial Viral CC/Sniper, Plasma Sniper, Silenced Pistol
      and the printed Monofilament Immunity example now link their relevant
      Properties directly in maintained-text prose; the E/M CC Weapon
      now links its printed N+E/M combination. Other candidates still
      need source-by-source review.
    - [ ] Continue the broader auxiliary/equipment-object and special-weapon
      prose review, including entries without four printed Attributes.
      Identify missing facts, relationships and browser coverage separately
      from source notation differences.
    - [ ] Continue auditing remaining Weaponry source clauses,
      unreviewed exceptions, exact profile semantics and
      API/browser relationships. The 90 selected clauses and seventeen
      typed edges are not an exhaustive N5.3 pp. 68-74 inventory.
    - [ ] Complete the remaining FAQ v0.1 source-hash/coverage and
      applicability review against the final pinned inputs. Distinguish
      core-relevant answers from ITS-season-only scope before adding
      further rulings; keep locally available FAQ/core PDF/history ZIP
      hash evidence separately versioned. Locally available Reinforcements
      PDFs are N4 publications; verify a supported N5 annex rather than inferring
      current rules from those older files or the related Wiki page.
      Do not make full ITS-season publication a 1.0 requirement.
  - [ ] Reconcile `data/curated/rules-interactions/reviews.json` and
    `catalog-scope.json` with the pinned 1.0 input set. Historical release labels
    and the passing supporting-identity slice do not certify the primary catalog.
    Use the separate 1.0 primary assessment, strict release guard and scope-drift
    report from the [source-evidence procedures](testing.md#10-source-evidence-baseline).
    Account for later published identities, including Activate Disco Ball,
    Request SpecBall, Firewall and optional Commlink, without rewriting historical
    approvals or attributing N5-native authority to the N4-origin annex.
  - [ ] Turn confirmed gaps into bounded batches under the owning tasks below. Each batch names
    the concepts/source sections, dependency, missing contract or content, and completion evidence;
    material source conflicts need reviewed applicability and clear user-visible disclosure
    before dependent presentation is closed; a missing official ruling is not a release blocker.
    Rank populated, player-relevant missing data or misleading rules ahead of optional
    comparisons and presentation enhancements. For every batch, retain the explicit
    blocker/dependency, source/version, expected browser entry point and validation gate;
    do not turn unresolved source chronology into a presumed application defect.
  - **Completion:** every supported source/category has an explicit coverage disposition and every
    material in-scope gap has an owning open task. This establishes the baseline, not final acceptance.

### Rules and reference completeness

- [ ] **Data processing + Web backend + Web frontend:** Close the remaining versioned
  curated rules-reference gaps for N5 v5.3 using
  `data/pdf/rules/n5-rules-v5-3-en.pdf` (dated 2026-08-10) and other explicitly scoped
  current reference sources.
  - [ ] Plan curation batches from the inventory by missing semantic family or source section.
    Separate already-reviewed content from absent definitions, unresolved variants, missing typed
    relations, and facts that exist but cannot yet be reached in the normal browser experience.
    Reuse the current [curated contract](../data/curated/README.md#curated-rules-reference-data);
    extend closed fact/relation vocabularies with validation and presentation support before use.
  - [ ] Review player-facing explanations of material rules interactions during
    remaining curation batches against the
    [explanation standard](../data/curated/README.md#explaining-rules-interactions).
    Verify conditions, the general rule, modifiers, explicit exceptions, the
    resulting game effect, and source certainty; do not generalize a printed
    example into an undocumented rules engine. Sample the normal browser view
    as well as the authored text, and keep source conflicts visible. Track
    the [1.0 explanation audit](rules-explanation-audit-1.0.md#prioritized-remediation-plan)
    through the individual checks below; published cards still require the
    stated browser/source acceptance before their findings can be closed.
    - [ ] **Cross-source applicability and disclosure:** Review material source
      disagreements and FAQ scope before dependent curation. Users must be able
      to identify the conflicting sources/versions, what differs, the published
      value or interpretation and its uncertainty. Use the
      [source manifest](rules-explanation-audit-1.0-sources.md) and
      [N5.3 reconciliation](rules-explanation-audit-1.0-n5.3-reconciliation.md).
      Preserve S17/S21 provenance; do not present an audit interpretation as an
      official ruling. External corrections are tracked under
      [non-blocking follow-up](#external-source-clarifications).
    - [ ] **Clause-review coverage gate:** Complete the
      [inventory gate](rules-explanation-audit-1.0-inventory.md#audit-completion-gate).
      The 304 selected clause reviews and 63 screening-only records
      do not constitute 367 full approvals.
      - [ ] Reconcile the frozen inventory with the current Core/Hacking record
        set and later source/browser evidence
        ([V1-A08](v1.0-source-coverage-audit.md#v1-a08--the-frozen-inventory-does-not-cover-the-current-record-set)).
        Preserve historical counts, independently verify metadata migrations and
        later source-reviewed additions, and give every current in-scope source
        section a clause/presentation disposition. Same-page citations alone do
        not certify the procedures on that page.
        - [ ] **Clause and browser dispositions:** Reconcile each current source
          section and record with later documented source/FAQ decisions,
          reviewed conditional effects, and normal-player browser evidence.
          Prior A01–04 and the selected Equipment/MOD/Weapon mode
          browser tests cover specific routes, not the entire current catalog.
          Prioritize added Skills, the five Visibility Zone terms, source-scoped
          Rules, and Weapon family/mode cases; retain unresolved source conflicts.
        - [ ] **Final completeness gate:** Sign off all relevant current
          categories and source sections under the release checklist, without
          converting historical D/S, current citations, or interaction-review
          flags into whole-record approval.
      - [ ] Verify other **conditional declaration permissions** beyond
        the source-backed exception slices already accepted. The whole
        1.0 corpus and reactive eligibility/activation conditions still
        require their own clause and normal-browser dispositions.
    - [ ] **Visibility Zone inventory additions:** Include the five newer
      Visibility Zone Game terms explicitly in final whole-corpus acceptance.
      Their [bounded source/browser checks](testing.md#10-five-visibility-zone-game-terms-browser-acceptance)
      do not expand the frozen 367-record explanation-audit denominator.
  - [ ] Expand remaining canonical rule identities across Skills, Equipment,
    Ammunition, Traits, States, Fireteam concepts, glossary terms, and other useful
    rule domains, retaining rulebook version and printed-page citation. Do not
    duplicate Hacking Program facts already owned by the current Hacking Program
    domain.
  - [ ] Complete the remaining typed Ammunition facts and relationships.
    The eleven base identities and reviewed combined forms are published;
    preserve the distinction between composition and Combined Saving Rolls.
    Reviewed cases belong in [rules semantics](rules-semantics.md), with bounded
    [source/browser acceptance](testing.md#10-reviewed-immunity-interactions-browser-acceptance-rea-011).
    - [ ] Review remaining component-level Immunities, exact BTS-based non-Comms
      Weapon exceptions, combined-effect precedence, Critical interactions,
      affected Attributes and conditional State links. Do not generalize the
      printed examples or name-scoped Viral Vulnerability into a resolver.
    - [ ] Revalidate all published base identities and reviewed combined forms
      against the final pinned source and shared Weapon/Ammunition facts.
      Keep any future comparison-view consumer separate; no comparison UI or
      executable attack adjudication is required for 1.0.
  - [ ] Include scenario-defined catalog concepts needed for the core-rules
    scenario reference, including core-scenario Skills, contextual roles such as
    Specialist Troop, and the scenario elements those concepts act on. Preserve
    scenario scope and keep temporary effects out of static Unit/Profile facts.
    Keep semantic identity, source publication provenance, and applicability
    separate so one canonical concept can be cited or overlaid by core scenarios
    and FAQ material without duplication or collection-load-order semantics.
    ITS-only actions and season-specific rules remain post-1.0.
    - [ ] Reuse current scoped definitions/supplements, then identify any missing applicability
      validation or presentation contract using one concept shared by core and scenario material.
      Prove that scope is visible and unrelated scenario/season overlays do not leak into core help.
      - [ ] Review remaining shared scenario concepts, collection-specific
        supplements and normal browser presentation for the complete 1.0 scope.
  - [ ] Complete final source-to-browser acceptance for the optional
    **Reinforcements Extra**, separately scoped from `n5-core-rules`.
    The N4-origin procedures, Section/parent navigation and exact typed
    Commlink (+1)/(+2) variants are published; see the
    [scoped reference contract](rules-semantics.md#rs-rf-scope-001--reinforcements-is-a-separately-scoped-annex-not-core-n5-rules-data).
    - [ ] **N5-native source clarification:** Resolve
      [SRC-030](official-source-clarifications.md#src-030--which-reinforcements-annex-procedures-govern-optional-n5-games)
      by identifying an authoritative N5-specific Annex revision or official
      adoption ruling. Pin its edition/date and reconcile differences before
      labelling the procedures N5-native. This does not block the clearly
      disclosed optional legacy reference.
    - [ ] Finish manual browser and release-matched Section/profile/Commlink
      acceptance. Source-wide profile/loadout and complete Commlink signature
      parity, selected-Army ownership and desktop/mobile navigation already have
      bounded checks; use the [acceptance evidence](testing.md#parallel-windows-development-and-linux-validation)
      and [validation queue](validation-queue.md) for remaining execution.
      These checks do not establish roster legality or publisher authority.
  - **Completion:** each covered batch builds into `rules.db`, passes maintained-text and
    interaction review, and is navigable with citations in normal mode. Use semantic maintained-text
    tokens; preserve genuine ambiguity with `review-needed` rather than weakening plain-text review.

- [ ] **Data processing + Web backend + Web frontend:** Complete source reconciliation
  and 1.0 acceptance for the already-published core-scenario domain. All four scenarios,
  shared definition v2, scoped Rules/Skills, relational publication indexes, list/detail
  APIs, browser selection and deterministic theme/distance-aware maps are implemented
  and included in 0.10.1. The current contract belongs in
  [the data model](data-model.md#scenario-model-implemented-core-and-future-extensions).
  - **Browser acceptance:** The separate
    [1.0 core-scenario browser checklist](#final-10-acceptance) owns
    keyboard/touch, rapid selection, theme/distance, direct/soft navigation,
    and loading/empty/error states. The tracked
    `test_verify_scenario_faq_browser.py` now repeats source-chart-to-browser
    checks for all 24 configurations at 1440/390 px, plus keyboard catalog
    and scoped Skill navigation, soft navigation/back, rapid selections,
    empty/error and recovery cases (320 px catalog coverage included).
    See [the repeatable acceptance procedure](testing.md#10-four-core-scenario-browser-acceptance).
    Rerun against the final candidate, including broader visual/touch,
    full-source and hosted gates; this does not itself certify 1.0 completeness.
  - **Completion:** the final source inventory accounts for every in-scope fact and
    scoped concept, and all four scenarios remain understandable and navigable in
    every supported configuration. No mutable match state or live scoring engine is required.

- [ ] **Data processing + Web backend + Web frontend:** Complete source coverage and
  applicability review of the published dated FAQ/errata layer from `data/pdf/faq/`.
  The authoring contract, source-precedence policy, export validation, runtime selector,
  explicit-context API and 29 reviewed current-source rulings are implemented; see the
  [current contract](data-model.md#dated-faqerrata-layer-published-reviewed-subset).
  - [ ] Revalidate this bounded 29-ruling/48-topic FAQ acceptance against
    the **final 1.0 release candidate** and release-matched rules database,
    including browser evidence and final source/disclaimer review. This is
    a release acceptance task, not a requirement for historical replay,
    official resolution of the Haris conflict or the eight ITS-only Q&As.
  - **Completion:** cover carried-forward/cross-posted rulings, supersession, conflicting sources,
    missing targets, and out-of-scope seasons. Every in-scope ruling is discoverable from its topic
    or scenario, and the reader can distinguish base rules from applicable clarifications.

- [ ] **Data processing + Web backend + Web frontend:** Extend generated rules-reference
  projections that build on the enriched canonical data rather than duplicating its facts.
  - [ ] Add the generated cross-army rule-variant usage index:
    canonical Skill/Equipment -> exact Level/MOD/typed variant ->
    Unit/profile/loadout occurrences. Reuse the
    [accepted index design](data-model.md#rule-variant-usage-index--accepted-design-direction-not-implemented).
    - [ ] Reconcile remaining unresolved Skill/Equipment occurrence parameters,
      mixed TEXT/DISTANCE sources and named variants with extra MODs.
      Reuse `python -m tools.audit_source_variant_inputs --catalog skills
      --unresolved-only --brief` (or `--catalog equipment`) and
      `tests/test_audit_source_variant_inputs.py`; revalidate the release-matched
      pair with the ignored raw Army archive. Preserve complete ordered source
      signatures, exclude unreviewed combinations, fail closed on unknowns,
      and promote metadata only through guarded matched-v9 publication.
      The 2026-11-03 Lieutenant source-119 review adds typed, distinct
      `+1 Command Token` (30 options) and `+1 Order` (53 options) effects
      under N5.3 p. 99; it does not treat either as a generic MOD or
      publish the cross-Army usage index. The same day's Terrain source-58
      review adds seven exact typed Terrain applicability selectors (1,235
      qualified direct rows, one unqualified), distinguishing Total/all
      Types, single fixed Types and Aquatic/Jungle/choose-one on placement.
      SRC-028's Religious Troop anomaly remains unreviewed. The
      Camouflage source-29 `1 Use` review certifies 223 one-use Army
      qualifiers using N5 FAQ v0.0/v0.1, without inventing a match-state
      tracker or changing the existing FAQ. The Combat Jump source-35
      review adds six exact landing-roll/Explosion parameters across 121
      direct qualified Army occurrences under N5.3 p. 89; the one-use
      template attack remains separate from the PH landing Roll and is
      not a general attack resolver. The Infiltration source-47 review
      adds five exact bracketed PH values for 17 Army occurrences under
      N5.3 p. 97, applying only to the PH-3 Infiltration Roll; five bare
      `ReRoll` extras remain unresolved because the printed reroll
      requires an explicit PH=X value. These do not yet publish the
      cross-Army usage index. Other unresolved source families remain.
    - [ ] Materialize public context links and verify duplicate sources, reused
      payloads, cross-Army and profile/loadout scope, Includes/Peripherals and
      ambiguous variants before publication. An audited source signature alone
      does not publish a Unit-usage index.
  - [ ] Complete remaining Restrictions migration safety and operational
    acceptance. The six-subject, 14-condition chart, typed v9 API, scoped
    reverse links and qualified legacy labels are published; see the
    [current contract](data-model.md#reviewed-restrictions-chart-projection).
    Negative conditions do not establish affirmative action legality.
    - The three legacy staging-only exporters now preserve the active v8/v9
      release schema and reviewed Restrictions. Their focused regressions and
      `tools.verify_staged_release_pair` reject stale release baselines,
      modified candidate binaries and source drift before reviewed manual
      promotion. Historical ignored staging directories without baseline
      fingerprints remain evidence only; they must be rebuilt before reuse.
      These tools do not promote artifacts automatically.
    - [ ] **Deployment:** Validate real host rollback/forward with the retained
      original v8 database/publication pair. The passing CI image rehearsal is
      not a hosted deployment. Obtain explicit operational authorization and
      a reviewed rollback plan before changing the host.
  - **Completion:** each projection has a normal browser entry point, source reconciliation, and
    regression coverage for its exceptional rows. Exact variant reconciliation gates the usage
    index; it need not block independently ready lookup or Restrictions views.

- [ ] **Data processing + Web backend + Web frontend:** Extend the completed Game States reference
  catalog with any remaining contextual state links needed by later Fireteam, Hacking,
  weapon/ammunition, and scenario guidance;
  do not infer a Unit's current in-game State from its static Army profile.
  - [ ] Drive additions from the coverage inventory and new typed Ammunition/scenario/FAQ facts.
    Author each relation once and verify derived navigation in both directions; distinguish entry,
    cancellation, immunity/override, and objective completion from the resulting State.
  - **Completion:** relevant context is linked from the owning rule and State help with applicable
    conditions/scope; no duplicate definitions or static assertions of a Trooper's live State.

- [ ] **Data processing + Web backend + Web frontend:** Complete remaining Weapon,
  Ammunition and Deployable reference presentation against the source inventory.
  The unit-neutral `/weapons` catalog/detail and `/ammunition` pages already expose
  profiles, modes, ranges, linked effects and Traits. Additional comparison/filter
  controls are an enhancement; the [1.0 gate](releasing.md#version-10-data-completeness-gate)
  requires usable access to in-scope information, not a final comparison UI.
  - [ ] Verify remaining multi-mode/multi-ammunition presentation gaps against those
    existing surfaces before designing another quick-reference view.
    Preserve the field-specific meaning of `+`: Ammunition
    composition and Combined Saving Rolls are separate rules operations. Validate
    the view against Army metadata; do not copy source charts wholesale into the
    application.
    - [ ] Define any additional read model needed for missing information using existing
      weapon identities/profiles and the enriched Ammunition model. Keep mode/profile identity,
      conditional values, range bands, damage/saving notation, Traits, and unavailable values
      explicit. Browser code renders these semantics rather than parsing display strings.
    - [ ] Reconcile representative single/multi-mode, combined-ammunition, Combined Saving Roll,
      and conditional/sentinel profiles through storage, API, and browser output. Verify the
      complete published profile set against the inventory, not only representative examples.
  - [ ] Complete deployed-object inventory and final reference acceptance.
    Seventeen reviewed profiles, delivery paths, API/browser entry points and
    typed reverse uses are published; see the
    [current contract](data-model.md#deployed-object-read-model-and-artifact-gated-browser-reference).
    Keep carrier, delivery mode, deployed-object identity and Unit ownership
    separate, with known/unreported/disputed attributes individually represented.
    - [ ] Expand discovery beyond the 14 four-attribute chart entries, maintained
      definitions and both bounded lexical scans. Check independent source tables,
      scenarios, alternate wording, Weapon/Equipment variants and nonstandard
      Scenery Elements against exact N5.3 clauses and the pinned Army source.
      Terrain, core scenarios, Game Modes, Retreat!, Silhouette Templates, Hacking
      Devices, the Weapon Chart and p. 74 have bounded reviews; none certifies
      total game-element coverage. Classify confirmed identities/delivery edges
      in the reviewed inventory before extending storage or reverse uses.
    - [ ] Decide whether Narrow/Wide Gate glossary terms or typed terrain
      combinations are needed for player discoverability. Their existing
      [terrain/scenery semantics](rules-semantics.md#terrain-and-scenery-structures)
      do not make them persistent deployed Weapon/Equipment devices.
    - [ ] Review unrepresented reverse-use contexts against exact source
      occurrences. Direct profile/loadout/Unit-option uses and one-level Includes
      are already typed; Unit options retain null Army context and Include
      targets use only their resolved Army. Rerun the full-depth Include and raw
      source-schema audits after snapshot changes, preserving source positions
      and ownership. Do not infer uses from prose or catalog membership.
    - [ ] Validate final API/browser navigation, shared carriers, variant and
      missing/not-applicable data against the release-matched publication.
      Retain conflicting Mine/Dazer/Armed Turret Silhouettes and the unresolved
      Mine Dispenser subtype unless reviewed source evidence resolves them.
  - **Completion:** players can inspect Weapon profiles and reach Ammunition/Traits and
    deployed-object statistics without selecting a carrier first; reverse uses preserve
    Army/loadout context. Missing in-scope facts must be exposed; dedicated comparison
    controls are not a separate release blocker.

### Player-facing navigation and reference clarity

**Project domains:** Data processing, Web backend, Web frontend

The shared navigation, contextual Specialist Troops reference/filter,
provenance labels and collapsible accuracy/independence notice are published;
their contracts belong in the [web design guidelines](web-design-guidelines.md).

- [ ] Complete dedicated assistive-technology acceptance of the floating notice
  and affected navigation against the final candidate. Automated browser checks
  do not provide that sign-off; keep keyboard, touch, theme and narrow-screen
  acceptance under the [final gate](#final-10-acceptance).

### Final 1.0 acceptance

**Project domains:** Data processing, Web backend, Web frontend, Project infrastructure

Development-browser results are dated, bounded evidence. The procedures in
[testing](testing.md) cover catalog navigation, source-conflict disclosure,
Weapon/Glossary fragments, Fireteams, all 24 Core scenario selections,
Visibility Zone previews, structured charts and representative Unit layouts/settings.
Rerun affected checks against the final pinned candidate; local results alone
do not establish exhaustive source coverage or hosted acceptance.

- [ ] **Data processing + Web backend + Web frontend + Project infrastructure:**
  Execute the final 1.0 source-to-storage-to-browser completeness gate defined by
  `docs/releasing.md` against pinned current Army, rules, wiki, database, and symbol
  inputs. Resolve every material in-scope gap or document an explicit exclusion with
  rationale, then complete normal project checks, hosted release checks, and
  full-asset validation before tagging 1.0.0.
  - [ ] Re-run the baseline inventory against the final pinned input set. Follow every in-scope
    category from source citation through maintained representation and generated storage to a
    usable normal browser surface; schema coverage, passing validators, and an API route alone
    are insufficient evidence. Re-review exclusions against the canonical completeness definition.
  - [ ] Run `tools.report_reference_baseline --verify-server <origin>` against
    the final candidate/deployment and retained Army/rules database pair,
    alongside separate source/archive, symbol and source-to-browser gates.
  - [ ] Run `tools.verify_rule_fragment_browser` on the final candidate and
    expand source-to-browser completeness beyond the bounded reference samples.
  - [ ] Re-run the full local 81-page Unit Chromium matrix and the separate
    exact-version hosted representative check using the final candidate databases
    and static assets. Retain successful evidence with the target revision.
    The hosted command defaults to 21 pages; it does not run the full local matrix.
  - [ ] Complete [Silhouette manual browser acceptance](testing.md#silhouette-manual-browser-acceptance)
    with hover, keyboard, touch, both themes and narrow widths. Automated DOM or
    screenshot checks do not supply the required interaction sign-off.
  - [ ] Review the final tracked Markdown corpus against the candidate, including
    current behavior, source and REA dispositions, command contracts and complete
    Unreleased notes. Revisit this development audit after later implementation
    or release-metadata changes.
  - [ ] Reconcile cross-source conflicts and empty/unavailable/not-applicable values; retain cited
    uncertainty where appropriate and fix every defect that materially misrepresents in-scope data.
    Record evidence by category and source identity in ignored reports/audits rather than keeping
    completed release narrative in this backlog.
  - [ ] Run [the complete release checklist](releasing.md), including the mandatory whole-corpus
    documentation audit, rebuilt release-matched artifacts where needed, local/hosted checks for
    the final candidate, annotated-tag evidence, and deployed smoke/rollback acceptance where
    applicable. Keep repeatable procedures in `docs/testing.md` and dated execution
    reports in ignored `local/audits/`, rather than adding another acceptance diary.

## Post-1.0 — maintenance and product expansion

These items are intentionally outside the 1.0 completeness gate. They may move earlier
only when required to fix correctness, reproducibility, or release reliability.

### External source clarifications

**Project domain:** Data processing

These external corrections and rulings do **not** block 1.0 while
the affected player references disclose the unresolved source scope.
The canonical [official-source-clarifications.md](official-source-clarifications.md)
register owns the evidence, question wording, stable SRC IDs and publisher
response status. This TODO section tracks only the remaining request/
follow-up action. Retain source-native values until official resolution.

- [ ] Prepare and submit a consolidated set of official source clarification
  requests from the [canonical register](official-source-clarifications.md).
  Record each publisher response against its stable SRC ID, then add only
  implementation follow-ups that a verified ruling actually requires.
  This external work is non-blocking for 1.0 while the published
  reference accurately discloses uncertainty.

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
  - [ ] Preserve multiple successive changes and supersession without overwriting
    previous revisions. Keep historical events distinct from current canonical
    facts and do not turn this feature into a 1.0 completeness blocker.

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

- [x] Provide a read-only development CLI for paired `infinity.raw.db`:
  `tools.inspect_raw_archive` verifies the shared export metadata, lists
  imported normalized tables (including zero-row tables), and retrieves
  individual or bounded paged lossless source rows. Unknown tables, unpaired
  siblings and invalid row selectors fail closed; see [data guidance](../data/README.md).

- [x] Report the application `infinity.db` and paired `infinity.raw.db`
  byte sizes after a successful `infinity-db build`, in ordinary build and
  CI output. A focused regression checks the reported sizes against the
  actual generated files.

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
  - [ ] Treat the official Army app/site as the authority for army-list legality.
    InfinityDB may provide read-only explanation and planning support, but must
    label its snapshot/date and avoid claiming tournament validation.
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
    source-backed definitions under `its-18@2026.09.01`; extend typed
    geometry, scoring and card/classified choices only where the mission
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
  - [ ] Build a web-based editor/preview UI over the same schema and rendering engine rather than
    creating a separate browser-only map format; coordinate this with the scenario creator below.

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
  - [ ] Keep the editor a post-1.0 feature, not a core-scenario release blocker.

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
  - [ ] If a native-client direction is accepted, keep the canonical data/rules artifacts and
    semantics shared with the web application rather than creating a second interpretation layer;
    revisit the project-domain taxonomy if a permanent native-frontend domain becomes warranted.

### User-owned tools and portable data

- [ ] **Web frontend + Project infrastructure:** For future authored-content tools,
  provide transient editing, privacy-preserving URL sharing where practical, and
  deliberate local file import/export. Do **not** introduce server-side user-content
  storage, account-backed saves, or share-token registries as prerequisites.
  Evaluate optional device-local saves only as an explicit, separate privacy
  decision; the baseline works without persistent browser storage.

- [ ] When an army-list builder/export tool is introduced, use the rules reference
  to add game-mode and list-review guidance—not hidden-information disclosure.
  Keep share/export privacy-aware and treat the Army app/data as authoritative
  for list legality. Use portable state rather than a server-side saved-list store.

- [ ] Create a curated unit-model image repository; do not assume open user uploads.

- [ ] Evaluate a device-local/portable model-collection tracker without accounts
  or server-hosted collections.

- [ ] Support portable army lists, favourites and personal notes, with explicit
  export/import instead of server persistence or coupling to imported snapshots.

- [ ] Unit comparison view for profiles, loadouts, weapons, skills, and
  equipment across selected units or armies.

- [ ] Army-list builder/export integration using the same portable-data contract.

- [ ] Data-review screens in Developer mode: normalization warnings, source
  record links through `infinity.raw.db`, and unresolved placeholder records.

- [ ] Low priority: provide access to prior imported-data versions when JSON
  source files change. Existing archived JSON ZIP files and Army snapshots are
  sufficient for recovery until this is needed.

- [ ] Low priority: add a JSON-snapshot comparison page showing added, removed,
  and updated data between two snapshots.

- [ ] Low priority: optionally highlight added, removed, and updated data
  elsewhere in the application when comparing snapshots.
