# InfinityDB backlog

This is the working implementation backlog. Every unchecked item belongs to exactly
one release bucket: **0.10.1**, **1.0.0**, or **post-1.0**.
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

**Project domain:** Project infrastructure

Version **0.10.0** is released and deployed. The immediate milestone is **0.10.1 —
interim reference consistency**, followed by **1.0.0 — current-reference completeness**.
The 0.10.1 candidate includes completed core Scenarios, Ammunition and rules-reference
improvements developed since 0.10.0, plus the verified stabilization corrections.
Broader 1.0 development is temporarily paused until this interim release is published;
the 1.0 acceptance definition and remaining commitments are unchanged.

General performance/storage experiments, major pipeline refactors,
persistent-user-data features, ITS season/tournament tooling, and native applications are explicitly
post-1.0 unless they become necessary to correct a release-blocking defect. Core-rules scenarios are
part of the 1.0 completeness target; their accepted architecture guides the 1.0 implementation.

The public roadmap summary lives in `README.md`; the durable 1.0 acceptance
definition lives in `docs/releasing.md`. The sections below contain the remaining implementation
and release work for 0.10.1, 1.0 and later milestones. Completed substeps are retained only under an
open parent item.

## 0.10.1 — interim reference consistency

**Project domains:** Data processing, Web frontend, Project infrastructure

Implementation stabilization is complete at `7f2923a`. The six corrected areas are
IMP-2 Discover, Stealth/Deployables, Deployable Cover, TinBot, Fireteam formation
requirements and Kobra's CC Attribute link; their durable outcomes are recorded in
`CHANGELOG.md`. This release also publishes the completed improvements since 0.10.0;
it does not claim 1.0 completeness or require unfinished 1.0 features.

**Candidate status:** Metadata and release notes are prepared for **0.10.1** dated
2026-10-10. Full local checks, required tracked assets, byte-identical runtime
database rebuilds and isolated installed-wheel smoke have passed. Real-browser
acceptance and exact-commit hosted validation remain open; it is not published or
certified release-ready. Follow the complete
[release checklist](releasing.md), including the project-wide documentation audit.

- [ ] **Web frontend + Project infrastructure:** Complete real-browser acceptance.
  The prior offline harness passed 52/52 focused tests and rendered seven affected
  views at 320, 390, 768 and 1440 pixels without JavaScript exceptions or overflow;
  that evidence does not verify real navigation or interaction. In a real browser:
  - inspect IMP-2, Stealth, Deployable Cover, TinBot and Kobra CC reference cards on
    desktop and narrow screens; follow their rule/Attribute links and source citations;
  - select an Army on Fireteams, verify formation labels and ongoing-integrity help,
    change the Wildcard setting, and check navigation back to Unit/reference pages;
  - browse all four Scenarios, change Army Points quickly, follow scoped rules links,
    navigate away/back, and check maps in both themes and distance units with
    keyboard and touch; verify loading/empty/error handling where practical;
  - open Visibility Zone tooltips and Ammunition/Immunity cross-links by pointer,
    keyboard and touch; confirm readable sections and no horizontal clipping.
- [ ] **Project infrastructure:** Land the candidate through the protected-main PR
  workflow after acceptance/local validation; require successful Source checks
  (including cross-platform determinism), Installed wheel smoke and Deployment
  smoke test for the exact final SHA. The checksum-pinned external Full-asset
  checks workflow is optional unless that bundle is selected as release evidence.
  Collect hosted evidence, create an annotated `v0.10.1` tag and publish only with
  explicit authorization. Deployment and post-release verification follow separately.

**Deferred intentionally to 1.0:** the remainder of REA-016/020 and the
broader Peripheral (REA-017), Hacking/Supportware (REA-018/019), Special Dice
(REA-021), General Rules (REA-026), weapon-composition/metadata (REA-025/044),
Spec-Ops (REA-040), full source reconciliation and completeness inventory.
Explicitly unresolved source disagreements (including Kobra Anti-materiel),
source-normalization baselines and optional enhancements are not new 0.10.1
regressions. The 1.0 plan below remains the owning backlog for those tasks.

## 1.0.0 — current-reference completeness gate

1.0.0 is the final completeness release for the supported current reference data. It
should resolve remaining material source/rules gaps, certify completeness of the published
core-scenario reference surface, and validate the whole application without expanding into
broader ITS/tournament tooling.

### Development sequence

**Project domains:** Data processing, Web backend, Web frontend, Project infrastructure

This is a proposed implementation sequence within the existing release scope, not a new
completeness definition. Use [the release gate](releasing.md#version-10-data-completeness-gate)
to decide whether a gap blocks 1.0. Do not wait until release preparation to discover missing
information or browser surfaces.

| Stage | Reviewable output | Dependencies |
| --- | --- | --- |
| 1. Inventory and scope | Pinned inputs, source-to-browser coverage inventory, prioritized gap batches | Existing Army/rules databases and audit tools |
| 2. Shared semantics | Scoped identity/clarification contracts, typed Ammunition and annex facts, scenario validation/export pilot | Inventory; reuse current contribution and relation contracts |
| 3. Complete vertical slices | Reviewed catalog batches, FAQ presentation, all four core scenarios | Relevant Stage 2 contract; each slice includes storage, API, and usable browser access |
| 4. Derived references | Declaration matrix, enriched lookup rows, variant usage, Restrictions, weapons and Deployables | Reviewed owning facts and exact variant/scope semantics |
| 5. Closeout | Reconciled completeness evidence and final release acceptance | Every in-scope gap resolved; canonical release checklist |

Stages may overlap where dependencies are satisfied. In particular, ordinary catalog curation can
continue alongside remaining shared-semantic work, and projections need only their owning facts to
be ready. Keep model/export, curation, backend, and browser substeps visible under each open parent;
a populated JSON collection alone does not complete a player-facing task.

For each implementation slice, record the source/version being covered, remaining decisions,
affected canonical documents, and evidence needed to close it. Extend existing validators and
audit tools before introducing another coverage system. Keep generated evidence in ignored
`reports/` or `docs/audits/`; keep maintained semantic decisions in validated curated data or
configuration. Use [the standard checks](testing.md) for the affected contracts, and add manual
browser acceptance for new visual/interaction surfaces. Promote durable contracts to their
canonical owners as implementation lands; keep remaining design extensions explicitly labelled
as unimplemented and distinguish them from the published core-scenario foundation.

### Source inventory and gap batches

- [ ] **Data processing + Project infrastructure:** Establish the 1.0 completeness baseline
  before expanding curation.
  - [x] Extract read-only publication/source evidence from the two shipped databases
    with `tools/report_reference_baseline.py`. Its initial report is deliberately unverified:
    local research inputs, source-by-section coverage, relationships, and ordinary
    browser paths remain to be checked before any completeness claim.
  - [x] Preserve each URL-pinned Wiki `oldid` as a distinct review identity in that
    baseline, separate from the shared local Wiki snapshot; report local source-file
    hash comparisons only when exact bytes are available and distinguish missing and
    unpinned artifacts from verified ones.
  - [x] Reconcile all 103 currently published Wiki `oldid` identities with exact
    historical page payloads in the separately supplied 2026-09-28 history archive.
    `tools/audit_1_0_reference_inputs.py` checks each page title and embedded revision
    ID, including historical Protheion 3908. This establishes source **availability**,
    not curation completeness or equivalence to the pinned 2026-09-18 Wiki snapshot.
  - [ ] Pin the intended Army snapshot, rules/FAQ/annex PDF versions, and supported wiki evidence.
    Record archive/content hashes as appropriate, publication dates separately from acquisition
    dates, and the generated database/publication identities. A later source refresh reopens the
    affected coverage review; normal checks must not acquire newer inputs implicitly.
    Include relevant dated official Corvus Belli rules-update posts as supplementary
    release-change evidence (not replacements for the versioned primary sources).
  - [x] Establish an initial N5 official update-post index and cross-source research
    procedure in `docs/n5-source-history.md`; identify the community Army backup
    as unofficial, versioned historical evidence rather than a new authority.
  - [ ] Reconcile each N5 update-post changelog item with its applicable versioned
    Army snapshot, rules/FAQ PDF, exact Wiki revision, and available historical N5
    versions. Record unmatched announcement claims and unknown release/snapshot
    boundaries as open review work, not confirmed database defects.
  - [ ] Inventory player-relevant information by source section/category, including the four core
    scenarios. For each category record its canonical identity/model, maintained input, generated
    storage, API/read path, ordinary browser entry point, rules context, and outstanding gap or
    justified exclusion. Distinguish missing facts, missing relationships, and missing presentation.
  - [ ] Reuse `audit_source_presentation.py`, `audit_enrichment_coverage.py`, and
    `audit_rules_interactions.py` as baseline evidence. Their existing Army/catalog coverage does
    not establish PDF, FAQ, or scenario completeness or prove browser usability; add the missing
    source review and presentation checks explicitly.
    - [x] Cross-check the existing 132 definition gaps against supplied source evidence:
      131 are Weapon identities and one is the annex-scoped Commlink Skill. The offline
      report records candidate Weapon Chart name occurrences (125/131 on the inspected
      Wiki chart) separately from profile-fact coverage; neither source text nor an
      Army weapon entry proves a complete curated rule definition.
    - [x] Establish a conservative five-field PDF/Army profile comparison via
      `tools/audit_weapon_chart_profiles.py`. On the supplied N5 v5.3 PDF, the first
      pass aligns 74 single-line, single-mode rows from 171 located chart rows;
      all 74 match when interpreting Saving Roll multipliers together with their
      Saving Attributes. Mine Dispenser's `savingNum=1` is non-operative because
      `saving=-`, matching the printed `--`. This is not full Weapon Chart coverage.
    - [x] Expand conservative PDF/Army alignment to wrapped names and explicit
      multi-mode profiles. The supplied N5 v5.3 PDF now aligns 163 of 171 chart
      rows across five profile fields: 162 match and Kobra Pistol (CC Mode) has
      a Saving Rolls discrepancy (printed 1, Army 2). Six Plasma-mode rows have
      multiline saving cells; two Disco Baller rows need identity/mode review.
      This is partial profile evidence, not full Weapon Chart completeness.
    - [x] Verify Kobra Pistol (CC Mode) effective Saving Rolls: the N5.3 DA
      Ammunition rule (p. 64) requires two rolls per hit and the dated N5.3
      update explicitly assigns DA to CC Mode. The Weapon Chart still prints
      one roll (pp. 68, 182), while Army and the current archived Wiki print
      two. Retain the inconsistent printed cell as source evidence.
    - [x] Publish a mode-scoped Kobra Pistol CC reference for the confirmed DA two-roll behavior, explicitly flagging the still-unresolved Anti-materiel source conflict without adding or removing any imported Trait.
    - [ ] Independently adjudicate Kobra Pistol CC Mode's `Anti-materiel` Trait:
      current Army/Wiki include it, the N5.3 PDF omits it, and DA Ammunition
      alone does not imply it. Do not conflate this with the explained roll count.
      BS and CC Mode share Army source ID `221`; do not attach CC-only
      interpretations to the source-wide Weapon variant or BS profile.
    - [x] Add a validated mode-qualified curated identity, matching numeric Weapon
      source ID plus exact profile `mode`, with isolated API/browser presentation.
      The synthetic Kobra fixture proves CC-only rules cannot leak to BS Mode.
      This is infrastructure only; no disputed Kobra rule has been published.
    - [x] Resolve the six Plasma multiline Saving Roll cells and the two
      Disco Baller/Discover chart-row ambiguities. All 171 Burst-anchored rows
      now align uniquely: 170 match across the five core fields and the Kobra
      Pistol CC Mode Saving Rolls candidate remains open. The separate Disco
      Ball object profile agrees with its named Army mode.
    - [x] Compare the chart's vector-drawn range breaks and printed MODs with
      Army range-band metadata. All 171 profiles are aligned: 170 match and
      Katyusha MRL (p. 187) prints unsigned `3` where Army records `+3`.
      This is a raw PDF notation difference, not a curated-data change.
    - [x] Resolve Katyusha MRL's unsigned `3` in the N5 v5.3 chart (p. 187):
      only `0` may be an unsigned integer range MOD. The bare `3` is invalid
      chart notation and is a **confirmed omitted plus sign**; Army and N5.3
      English/Spanish Wiki agree on `+3` at 20–60 cm. Preserve the PDF's
      literal `3` as source evidence and Army's correct `+3`; do not silently
      normalize other chart errors. See
      `config/validation/weapon-range-source-review.json` and RR-SRC-N53-003.
    - [x] Establish a read-only Weapon Traits and special-prose section inventory with
      `tools/audit_weapon_traits_prose.py` against the N5 v5.3 PDF. The 171
      Burst-anchored chart rows yield 145 literal Trait-list matches, 24 review
      candidates (including shorthand and source spelling differences), and two
      PDF-layout deferrals; all 12 indexed prose sections on pp. 68–74 are present.
      This is not evidence of rule-definition, relationship, or browser completeness.
    - [x] Reconcile the 24 initial Weapon Trait candidates against reviewed notation:
      15 are equivalent under explicitly maintained source spelling/State/footnote
      aliases, and the two positional deferrals (Chest Mine CC Mode, Deactivator)
      match visually checked cells pinned to the exact core PDF SHA-256. No
      source rows remain deferred; 9 Trait membership/classification candidates
      remain open, and no upstream gameplay data is modified.
    - [x] Cross-check the nine unresolved Trait identities against exact archived
      Wiki `Weapon_Chart` revision 4083 and official N5 change notices. The Wiki
      agrees with PDF Traits for 7 rows and Army for 2 (Cybermine, Kobra Pistol
      CC Mode). Pheroware's `BS Weapon (WIP)` replaces `Technical Weapon` in the
      April 2025 announcement, but current Army still uses the old classification.
      Kobra's current Wiki/Army show 2 Saving Rolls and `Anti-materiel` while the
      v5.3 PDF shows 1 and lacks that Trait. These are raw comparison results,
      now supplemented by the reviewed semantic outcomes below; do not infer
      that source-text differences automatically represent gameplay differences.
    - [x] Classify all nine cross-source Weapon Trait cases against the N5.3
      printed Weapon Chart and prose: five explained interpretations and four
      partially explained. Cybermine's `Comms Attack` is in the PDF (pp. 72,
      181); the earlier audit extractor truncated the cell, now corrected below.
      `Throwing Weapon` and `Technical
      Weapon` are absent from the N5.3 PDF and persist as Army legacy terms.
      N4 v1.1 p. 43 confirms both names and their original PH/WIP semantics;
      WildParrot explicitly has `Non-Lethal`; Mines and Sepsitor footnote
      references require their own semantic links. N4 p. 171 and N5.3 p. 176
      explicitly define `[*]` as Weaponry, `[**]` as Ammunition, and `[***]`
      as Skills and Equipment. See the version-pinned
      `config/validation/weapon-trait-wiki-review.json` findings; all original
      three-way comparison values remain intact.
    - [x] Correct the seven-line Cybermine PDF Trait-cell extraction without
      erasing the previously reviewed cross-source identity. The new audit checks
      171 rows: 145 literal matches, 16 notation equivalents (including Cybermine),
      2 reviewed cells, 8 unresolved Trait candidates, and 0 deferrals. The
      archived Wiki agrees with both current sources for Cybermine.
    - [x] Publish a WildParrot-specific curated weapon reference: Perimeter
      deployment followed by E/M Mine behavior with a visible Token/Model, not
      Boost movement. Link E/M and applicable State/Non-Lethal rules without
      synthesizing the missing Army Non-Lethal property. N5 v5.3 p. 74; the
      Army-versus-PDF Trait disagreement remains unresolved.
    - [x] Publish source-specific PT: Endgame Double Shot rules under grouped `/weapons/pt`,
      without granting those effects to Eraser or Mirrorball. The N5.3 chart and
      April 2025 update agree; Army still omits Double Shot and uses the old
      Technical Weapon label. Preserve the conflict instead of rewriting Army.
    - [x] Publish source-aware Drop Bears guidance for its two N5.3 modes,
      the shared Disposable (3) uses, visible Mine Token placement, and the
      legacy Army Throwing Weapon label, without changing source Traits or
      granting ordinary Mine Camouflage placement. Preserve PDF pp. 71/181
      provenance and cover both modes through the Weapon API.
    - [x] Review legacy Army `Technical Weapon` terminology in Pheroware and
      present the reviewed N5 `BS Weapon (WIP)` Trait as the primary Weapon-page
      link, retaining the original Army label alongside it. Exact curated aliases
      are source-aware, but parameterized Traits retain their source parameters;
      Drop Bears' duplicate `BS Weapon (PH)` / `Throwing Weapon` resolves to one
      visible canonical link without modifying imported Army properties.
    - [x] Inventory exact-name source/curation links for all 12 N5 v5.3 Weaponry
      prose headings (pp. 68–74). Eight headings match at least one Army weapon
      profile; Armed Turret alone has an exact-name curated Weapon record with
      a section citation, eight relations, and an Army link. This does not prove
      that generic/family sections or the other eleven headings lack a proper
      reference representation: names, mode identities, citations, and rules
      semantics are distinct evidence layers.
    - [x] Publish a PARA Mine-specific reference, with both the shared Mines
      rules and PARA ammunition/Immobilized-A linked. Show the PDF/Wiki `[*]`
      (Weaponry) versus Army `[**]` (Ammunition) discrepancy without modifying
      source data. This establishes both rule owners, not why Army chose `[**]`.
    - [x] Publish separate, cited Sepsitor and Sepsitor Plus references for the
      shared p. 73 attack rules, distinct PS and Disposable profiles,
      Sepsitorized State and Cube 2.0 Saving Roll interaction. Both Weapon pages
      link directly to their own rules; no Army Trait is synthesized.
    - [ ] Continue review of PARA Mine's intended Army footnote marker, Sepsitor
      Plus's missing Army `[*]`, and WildParrot's printed `Non-Lethal` against
      its E/M ammunition effect; Endgame's missing Army `Double Shot` is already
      shown with provenance. Both Sepsitor variants now link to the p. 73 rules,
      but the cause of the missing Army footnote remains unverified.
    - [x] Start a PDF-hash-pinned clause-to-reference review for the **Mines** and
      **Perimeter Weapons** families (N5.3 pp. 69, 72). The read-only
      `tools/audit_weaponry_family_clauses.py` checks 21 selected clauses,
      10 explicitly selected Army weapon names, and related curated concept
      identities. All names and concept records resolve, but neither family
      has a same-named curated record. This is not semantic or UI completeness.
    - [x] First adjudication identified **8 represented**, **9 generic-component-only**,
      and **4 not represented** clauses (subsequently resolved by the Mines family
      definitions below). Complete the `trait:boost` summary with triggering, detonation, blocked
      paths, Marker exclusions, Dodge, and Deployable-chain restrictions; pin
      its N5 p. 69 citation and preserve reviewed-text link provenance.
    - [x] Add a separate **Mines** family reference with complete selected
      trigger/placement/allied-safety mechanics, Cybermine Reset/State exceptions,
      and Chest Mine BS/CC mode exceptions without applying shared Mines placement/trigger rules
      to Chest Mines. The pinned 21-clause review now reports 21 represented;
      weapon catalog enrichment is regression-tested against all eight associated
      Army Weapon slugs (seven named Mine variants and Chest Mine).
    - [x] Reconcile seven named Mine Army profiles with printed N5.3 chart
      values and identify the distinct ammunition/trait/state effect owners.
      Evidence: `config/validation/mine-variant-effects.json` and
      `docs/rules-research.md` RR-WPN-MINE-002; PARA footnote remains unresolved.
    - [ ] Complete an individual-variant review for AP, E/M, Monofilament, PARA,
      Shock, Viral, and Cybermines against the N5 Weapon Chart, ammunition and
      State rules, and Army profiles. Shared placement/trigger rules must not be
      mistaken for identical weapon effects or complete per-variant semantics.
    - [x] Publish individually reviewed Mine effect/reference links from the
      curated family definition to the Weapon profile, including ammunition
      and applicable State/Skill links; do not infer effects for unreviewed weapons.
    - [ ] Manually verify Mines/Cybermine/Chest Mine browser detail cards, rule
      links, citation rendering, and both Chest Mine modes; then reconcile any
      resulting navigation/presentation defects. Source-backed API enrichment
      alone does not establish browser acceptance.
    - [ ] Reconcile auxiliary/equipment object profiles and special-weapon
      prose clause by clause; identify missing facts, relationships, and browser
      coverage separately from raw source notation differences.
    - [ ] Review the six unmatched chart-text names as aliases, multi-mode entries,
      or source-specific rules (including Chest Mine and SymbioBomb). Reconcile all
      Weapon Chart rows and special-weapon text against N5 v5.3 pp. 68–74 and 176–188,
      published Weapon identities and their API/browser profiles; classify each gap
      as missing facts, relationships, or merely missing a standalone definition.
    - [ ] Register the supplied FAQ v0.1 as its own pinned source publication and
      reconcile core versus ITS-season applicability before curating rulings. Its
      content hash and the core PDF/history ZIP hashes are available in the local
      source-evidence report; the separately versioned Reinforcements Extra remains
      unavailable and must not be inferred from the related Wiki page.
  - [ ] Reconcile `data/curated/rules-interactions/reviews.json` and `catalog-scope.json` with the
    pinned input set. Historical review/defer release labels are evidence, not the active roadmap:
    reassess pending items against the 1.0 gate and record explicit scope decisions rather than
    treating every deferred candidate as either automatically required or automatically excluded.
  - [ ] Turn confirmed gaps into bounded batches under the owning tasks below. Each batch names
    the concepts/source sections, dependency, missing contract or content, and completion evidence;
    material source conflicts need a reviewed decision before dependent presentation is closed.
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
    as well as the authored text, and keep source conflicts visible.
    - [ ] Review and implement accepted batches from the
      [1.0 explanation audit](rules-explanation-audit-1.0.md#prioritized-remediation-plan).
      The confirmed recovery/Intuitive Attack explanations (REA-001/002/003/009/022)
      have been revised in curated data and need player-facing review. Adjudicate
      direct Doctor/Engineer target allegiance (REA-038) before closing eligibility;
      Counterintelligence's actor correction (REA-043) is implemented in curated
      data; verify its player-facing wording in the browser. The Continuous Damage
      Critical exception (REA-004) and BS Weapon (WIP) Skill restrictions (REA-005)
      are now documented in curated Trait summaries; verify their player-facing
      wording and keep deferred typed-variant edges separate. Controlled Jump
      (REA-006) now explains immediate declaration, optional table-wide ARO,
      opposing-Program cancellation, and preservation of separate scenario MODs;
      verify the player-facing Program page. Request Speedball's FAQ exclusion
      (REA-007) is now explained in both curated records; verify the player-facing
      Skill and Program cards. Protheion (REA-008) now states the FAQ overkill limit,
      profile-listed enemy Attribute MOD, and recovery order; verify its player-facing
      Skill card (player-verified). The general Immunity (ARM/BTS) Trait
      protection and printed Monofilament exception (REA-010) are now explained
      alongside the existing Flash Pulse example; verify both in the browser.
      The five structured reviewed Immunity interactions (REA-011) now have a
      dedicated player-facing section with applicability and explicit/derived
      labels; verify keyboard, mobile and browser layout before accepting the UI.
      No new Plasma/Enhanced case was added to the reviewed arrays.
      Smoke/Eclipse (REA-012) now distinguishes ordinary rolled LoF opposition,
      MSV/Reflective exceptions, unopposed placement, Dodge, and Criticals in
      curated Clarifications and examples; verify the browser pages.
      AP/E/M and T2 (REA-013) now clarify rounding up halved defenses and
      marking the original-hit versus extra-Critical T2 die before rolling;
      verify their player-facing Ammunition pages. Typed values are unchanged.
      Dodge/Reset (REA-014) now explain per-Attack evasion, movement after
      qualifying Dodge, Engaged exit position, cumulative Reset State MODs,
      and the Sixth Sense exception; verify the Dodge, Reset, Engaged and
      Bangbomb browser cards. REA-015 now has source-cited State-specific cancellation explanations, pending browser review; REA-026 remains separate.
      Targeted MSV1/Sixth Sense FAQ questions (REA-019) stay separate.
      Common Supportware rules (REA-018) remain separate work.
      Separately decide source conflicts and FAQ applicability before dependent curation.
      Use the [source manifest](rules-explanation-audit-1.0-sources.md) and
      [N5.3 reconciliation](rules-explanation-audit-1.0-n5.3-reconciliation.md).
      Complete the [coverage gate](rules-explanation-audit-1.0-inventory.md#audit-completion-gate):
      304 selected clause reviews and 63 screening-only records are not 367 full
      approvals. Track TinBot sharing/SpecBall (REA-039/040), official Spanish PDF
      source contradictions (REA-034/037/041), and Spanish Wiki-versus-PDF
      discrepancies (REA-027/042). Preserve the S17/S21 provenance and seek
      scoped errata rather than silently normalizing conflicting publications.
      Also track targeted current metadata-only Weapon publication
      (REA-044) without promoting optional exhaustive research into a release blocker.
      The report remains an assessment, not accepted replacement semantics.
      Include the five new Visibility Zone Game terms in the final record acceptance
      review; they postdate the frozen 367-record explanation-audit inventory.
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
    - [ ] Define projection rows and declaration/scope columns from the existing canonical
      declaration metadata; expose the owning rule links and cited exceptions. Choose a normal
      reference entry point rather than leaving the matrix as an audit-only output.
    - [ ] Validate the pinned core chart against the generated projection. Cover action-like
      Equipment and Hacking Programs, missing/contradictory categories, scenario-only actions,
      and phase-scoped exclusions without interpreting absence as permission or prohibition.
  - [ ] Deepen the existing first-class Ammunition model with explicit typed
    relationships. Preserve the eleven published base Ammunition identities, distinguish
    source-defined combined forms, preserve component relationships for Combined
    Ammunition, and keep Ammunition composition separate from Combined Saving Roll
    notation. Link State, Attribute, and Saving-Roll effects explicitly instead of
    deriving them from display names.
    - [x] Add a bounded source-identity navigation pilot for the 11 published base Ammunition
      references and source-defined `AP+DA`, using exact Army metadata IDs and names.
      Keep unreviewed forms unlinked and Saving Roll notation independent; this does
      not complete typed Ammunition effects or the quick-reference view.
    - [x] Represent the four reviewed combined Army Ammunition source forms
      (`AP+DA`, `AP+Exp`, `AP+Shock`, `AP+T2`) with exact, ordered canonical
      component identities and project those identities into Weapon API profiles.
      Validate against source ID/name and source display notation; keep alternate
      ammunition choices and Saving Roll expressions out of composition semantics.
      This is a source-to-API pilot, not a replacement for curated effect facts.
    - [x] Establish an initial typed, non-executable Ammunition effect contract on canonical
      records (AP defense halving, DA roll multiplicity, E/M conditional State effects),
      with a source-to-rules-API pilot for AP+DA and a negative Combined Saving Roll case.
      Preserve independent Army profile values and source-cited fact ownership.
    - [x] Extend typed facts to EXP, PARA, and T2, explicitly modeling EXP's three rolls,
      PARA's PH-6/no-PH exception and Immobilized-A on failure, and T2's different
      Wound outcomes for a hit versus an additional Critical Saving Roll.
      Preserve those distinct conditions without evaluating combined ammunition.
    - [x] Add source-backed facts for Normal, Shock, Stun, Smoke and Eclipse;
      isolate Smoke/Eclipse visibility zones from Saving Roll facts and preserve
      Shock's VITA-1 restriction and Stun's Courage/Guts exception.
    - [x] Connect the five reviewed conditional State outcomes from E/M, PARA,
      Shock and Stun to canonical State pages with bidirectional rules relations.
      Check the authored targets against typed State facts without losing failure,
      target-type or VITA restrictions; the full interaction audit stays open.
    - [x] Record the single additional Critical Saving Roll on all nine
      roll-bearing base Ammunition facts, preserving T2's one-Wound Critical
      exception and excluding Smoke/Eclipse. Do not sum the Critical extra roll
      per component or infer totals from the four combined source mappings.
    - [x] Publish a bounded, exact-source Combined Saving Roll Critical reference
      for the six Plasma Weapon Hit/Blast profiles: one ARM plus one BTS Saving
      Roll, with one additional ARM roll on a Critical. Keep the reviewed source
      signatures separate from Ammunition composition and leave unreviewed
      profiles unchanged; this remains descriptive, not a roll evaluator.
    - [x] Pin the reviewed Immunity boundary on its owning Skill reference:
      covered Ammunition uses Normal effects, Immunity (Critical) removes the
      otherwise remaining extra Critical roll, and Comms Attack/Non-Lethal/
      Stunned exceptions are explicit. This is *not* a combined-effect evaluator.
    - [x] Review two conditional Combined Ammunition/Immunity (ARM) intersections:
      AP+DA and AP+Exp when the attack uses ARM and is not a Comms Attack.
      Preserve source identity, ordinary/Critical roll counts and the distinction
      between rule-derived examples and printed examples; keep them non-executable.
    - [x] Pin the explicit N5.3 Vulnerability (Viral) versus Immunity (Enhanced)
      example: the Immunity is unavailable against a weapon named Viral, regardless
      of any inference about Ammunition composition. Cite Wiki Vulnerability
      revision 3156; leave it non-executable.
    - [x] Review Immunity (AP) against AP+DA as a condition-scoped, rule-derived
      case: the AP component is treated as Normal, leaving DA's two full-ARM
      Saving Rolls (three on Critical). Keep the original AP+DA source identity.
    - [x] Pin the N5.3 printed Immunity (BTS) versus Flash Pulse example:
      Stun Ammunition becomes Normal, while Non-Lethal and Stunned-on-failed-save
      remain in effect. Keep the exception weapon-scoped and non-executable.
    - [ ] Review other component-level Immunities, BTS-based variants and
      weapon-specific exceptions. Do not generalize from the reviewed examples
      or the name-scoped Viral Vulnerability case.
    - [x] Present the existing eleven base Ammunition typed facts in the shared
      rules-card renderer, with explicit failed-Saving-Roll conditions, Critical
      exceptions and separate Smoke/Eclipse visibility behavior. Reuse curated
      State links and preserve the full cited summaries; do not calculate rolls.
    - [ ] Review the remaining fact/relation completeness, including combined-effect
      precedence, full Critical interactions, affected Attributes, visibility Face
      to Face outcomes, conditional State cross-links, and comparison-view
      consumption. Do not infer executable mechanics from reviewed reference facts.
    - [ ] Validate every published base identity and reviewed combined form against the pinned
      source; prove that weapon links, Ammunition detail, and later comparison views consume the
      same facts without conflating composition with roll notation.
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
    - [ ] Reuse current scoped definitions/supplements, then identify any missing applicability
      validation or presentation contract using one concept shared by core and scenario material.
      Prove that scope is visible and unrelated scenario/season overlays do not leak into core help.
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
    - [ ] Deliver the annex as a bounded slice: validated collection/citations, typed parameter
      and declaration support, generated rules facts, and linked annex/Skill help from the existing
      Reinforcement Army context. Reuse reviewed Army parent/pool relationships.
    - [ ] Test ordinary versus Reinforcement context, exact `Commlink (+X)` variants, and explicit
      phase classification; do not infer roster legality or mutate the core declaration chart.
  - **Completion:** each covered batch builds into `rules.db`, passes maintained-text and
    interaction review, and is navigable with citations in normal mode. Use semantic maintained-text
    tokens; preserve genuine ambiguity with `review-needed` rather than weakening plain-text review.

- [ ] **Data processing + Web backend + Web frontend:** Complete source reconciliation
  and 1.0 acceptance for the already-published core-scenario domain. All four scenarios,
  shared definition v2, scoped Rules/Skills, relational publication indexes, list/detail
  APIs, browser selection and deterministic theme/distance-aware maps are implemented
  and included in 0.10.1. The current contract belongs in
  [the data model](data-model.md#planned-scenario-model-10).
  - [ ] Reconcile scenario facts, scoring, scoped concepts and source issues with the
    final 1.0 source inventory for all six supported Army Points values. This is
    source-completeness review, not a request to reimplement the published domain.
  - [ ] Verify **Domination's 350-point SWC row** against authoritative clarification.
    N5.3 page 151 prints 6 SWC, unlike Annihilation's 7 at the same Army Points.
    Retain the printed value and visible uncertainty until clarified; this existing
    source disagreement does not block 0.10.1.
  - [ ] Confirm the current model remains source/scope-aware against the reviewed ITS
    variation during final completeness review. ITS content, ITS-only geometry,
    tournament tooling and an interactive scenario editor remain post-1.0.
  - [ ] Incorporate the real-browser keyboard/touch, rapid selection, theme/distance,
    direct/soft navigation and loading/empty/error acceptance from the
    [0.10.1 checklist](#0101--interim-reference-consistency) into 1.0 closeout.
    The 2026-10-08 user-confirmed visual review and automated lifecycle/responsive
    coverage do not replace interaction acceptance.
  - **Completion:** the final source inventory accounts for every in-scope fact and
    scoped concept, and all four scenarios remain understandable and navigable in
    every supported configuration. No mutable match state or live scoring engine is required.

- [ ] **Data processing + Web backend + Web frontend:** Add a dated FAQ/errata layer to the
  existing rules-reference system from current material under `data/pdf/faq/`.
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
    - [ ] Reuse the current definition/supplement boundary. Define the additional ruling identity,
      applicability, supersession, and source-selection fields needed by FAQ data before authoring
      batches; publication recency alone must not imply universal applicability. Record accepted
      semantics in the canonical data model and curated contract.
  - [ ] Deliver one core clarification and one scenario/season-scoped ruling through validation,
    export, repository/API composition, and browser presentation before curating the remaining
    inventory. Show linked questions/answers with dates and affected concepts alongside the base
    rule; choose a discoverable reference entry point without requiring a new top-level FAQ domain.
  - **Completion:** cover carried-forward/cross-posted rulings, supersession, conflicting sources,
    missing targets, and out-of-scope seasons. Every in-scope ruling is discoverable from its topic
    or scenario, and the reader can distinguish base rules from applicable clarifications.

- [ ] **Data processing + Web backend + Web frontend:** Extend generated rules-reference
  projections that build on the enriched canonical data rather than duplicating its facts.
  - [ ] Add richer typed/cross-linked projections for the existing structured Martial Arts,
    Booty, and MetaChemistry reference rows. Keep random outcomes
    as deployment/session overlays, preserve conditional branches (for example TAG
    versus other Troop Types), and cross-link resolvable outcomes to canonical Skills,
    Equipment, Weapons, and Attributes without rewriting Unit profiles.
    - [ ] Validate every published lookup row/range and conditional outcome against its cited
      source. Extend typed outcome support first, then render canonical links from the same rows;
      no random-result selection or persistent session overlay is required for 1.0.
  - [ ] Add a generated cross-army rule-variant usage index once exact variant
    semantics are reconciled: canonical Skill/Equipment -> Level/MOD/typed parameter
    variant -> Unit/profile/loadout occurrences. Derive it from canonical rules and
    Army occurrence relationships rather than maintaining a second classification.
    - [ ] Define the occurrence key and counting policy before aggregation so shared payloads,
      duplicate source Unit representations, and Army-specific variants do not inflate totals or
      lose context. Link results to the applicable Unit/profile/loadout and exact rule variant.
  - [ ] Model the finite V5.3 Restrictions Chart as explicit cross-domain
    relationships (Troop Type/Training/Equipment/Skill -> restricted action or
    Lieutenant eligibility) and expose it as contextual help/generated reference.
    Do not generalize this into a full live-game action-legality engine.
    - [ ] Reconcile every chart row and footnote with its owning fact/typed relationship, then
      test conditional restrictions, positive/negative cases, and scope. Present the condition and
      source; an absent restriction edge must not be presented as an affirmative legality result.
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

- [ ] **Data processing + Web backend + Web frontend:** Add a weapon-and-ammunition quick-reference
  view built from existing weapon profiles plus curated rules data.
  - [ ] Normalize display of multi-mode/multi-ammunition profiles, link ammunition
    names and traits to their effects, and provide a unit-neutral
    comparison/filter view. Preserve the field-specific meaning of `+`: Ammunition
    composition and Combined Saving Rolls are separate rules operations. Validate
    the view against Army metadata; do not copy source charts wholesale into the
    application.
    - [ ] Define a unit-neutral read model and minimal comparison/filter controls using existing
      weapon identities/profiles and the enriched Ammunition model. Keep mode/profile identity,
      conditional values, range bands, damage/saving notation, Traits, and unavailable values
      explicit. Browser code renders these semantics rather than parsing display strings.
    - [ ] Reconcile representative single/multi-mode, combined-ammunition, Combined Saving Roll,
      and conditional/sentinel profiles through storage, API, and browser output. Verify the
      complete published profile set against the inventory, not only representative examples.
  - [ ] Add a generated Deployables profile reference from Weapon/Equipment
    metadata plus curated corrections: ARM/BTS/STR/S for the deployed object,
    originating item/rule, and reverse Unit/loadout uses. Keep deployed-object
    identity separate from the carrier and from catalog domain. Track the V5.3
    Armed Turret S2 detailed-profile versus S1 quick-reference conflict explicitly
    and do not silently choose the summary value without reviewed precedence.
    - [ ] Inventory deployed objects independently of their carriers. Reuse existing
      `facts.specialProfile` support where it fits; extend validated metadata/corrections only for
      confirmed gaps. Resolve or visibly retain the Armed Turret discrepancy with both citations.
    - [ ] Expose deployed-object profiles and reverse uses through a usable reference entry point.
      Test objects supplied through Weapons and Equipment, shared objects/multiple carriers,
      missing/not-applicable values, and carrier-to-object navigation without inventing Unit identity.
  - **Completion:** players can compare weapon profiles and reach Ammunition/Traits and deployed
    object statistics without selecting a carrier first; reverse uses preserve Army/loadout context.

- [ ] **Data processing + Web backend + Web frontend:** Add a curated Infinity Wiki URL mapping
  for traits when authoritative links are available.
  - [ ] Inventory Traits with missing or ambiguous official targets and author validated maintained
    mappings, reusing existing source-link resolution where applicable. Keep renamed/alias labels
    separate from destination identity; do not generate URLs from display names or invent a page
    when only a heading exists.
  - **Completion:** mapped links reach the reviewed official page/heading from normal Trait help;
    unavailable mappings remain deliberate. Source-link checking is explicit research activity,
    while automated mapping/resolution tests remain offline.

### Final 1.0 acceptance

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
  - [ ] Close the 1.0 interaction-review target in the maintained ledger, regenerate the checklist,
    and require the following check to pass. Never edit the generated checklist manually:

    ```text
    python tools/audit_rules_interactions.py --check-output docs/rules-interaction-checklist.md --require-release 1.0.0
    ```

  - [ ] Reconcile cross-source conflicts and empty/unavailable/not-applicable values; retain cited
    uncertainty where appropriate and fix every defect that materially misrepresents in-scope data.
    Record evidence by category and source identity in ignored reports/audits rather than keeping
    completed release narrative in this backlog.
  - [ ] Run [the complete release checklist](releasing.md), including the mandatory whole-corpus
    documentation audit, rebuilt release-matched artifacts where needed, local/hosted checks for
    the final candidate, annotated-tag evidence, and deployed smoke/rollback acceptance where
    applicable. Capture new scenario/reference browser acceptance in `docs/testing.md` as those
    surfaces are implemented.

## Post-1.0 — maintenance and product expansion

These items are intentionally outside the 1.0 completeness gate. They may move earlier
only when required to fix correctness, reproducibility, or release reliability.

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

- [ ] Extend the 1.0 scenario domain with ITS scenario list/detail coverage backed by
  curated seasonal data, rather than creating a separate ITS-only model or using PDF excerpts.
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
