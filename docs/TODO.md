# InfinityDB backlog

This is the working implementation backlog. Every unchecked item belongs to exactly
one release bucket: **1.0.0** or **post-1.0**.
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

Version **0.10.1** was released and deployed on 2026-10-10. The current
development milestone is **1.0.0 — current-reference completeness**.
Completed Scenarios, Ammunition, rules-reference and stabilization changes
belong to the [0.10.1 changelog](CHANGELOG.md#0101---2026-10-10), not a
pending release checklist.

**0.10.1 release evidence:** [PR #19](https://github.com/frankysan/InfinityDB/pull/19)
merged to main at 0b83a3b2fef7, and the
[GitHub release](https://github.com/frankysan/InfinityDB/releases/tag/v0.10.1)
was published on October 10. For that exact commit, GitHub shows successful
[Source checks](https://github.com/frankysan/InfinityDB/actions/runs/38057014539)
(including cross-platform determinism),
[Installed wheel smoke](https://github.com/frankysan/InfinityDB/actions/runs/38057014543),
and [Deployment smoke](https://github.com/frankysan/InfinityDB/actions/runs/38057014518).
Production deployment is user-confirmed. The v0.10.1 tag exists but is
**lightweight**, rather than annotated as the old checklist requested. Keep
annotated-tag acceptance for 1.0; do not reopen a published minor release.

The old offline 52/52 browser checks and seven-view responsive check did not
establish the full real-browser interaction acceptance specified for 0.10.1.
The later REA-017/026 browser acceptance is narrower as well. Those unverified
cross-surface checks are now individual tasks under
[final 1.0 acceptance](#final-10-acceptance).

General performance/storage experiments, major pipeline refactors,
persistent-user-data features, ITS season/tournament tooling and native
applications remain post-1.0 unless needed to fix release-critical defects.
Core-rules scenarios remain within 1.0 completeness scope.

The public roadmap lives in README.md; the durable 1.0 release gate
lives in docs/releasing.md. All unchecked tasks below belong to 1.0
or post-1.0.

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
  - [x] Reconcile the initial 103 English Wiki `oldid` identities with exact
    historical page payloads in the 2026-09-28 history archive. The maintained
    source audit verifies each page title and embedded revision ID, including
    historical Protheion 3908. This establishes source **availability**,
    not curation completeness or equivalence to the removed September 18 capture.
  - [x] Re-run the 1.0 source-input audit using separate English and Spanish
    Wiki history archives and the September 26 curated Wiki capture. All 110
    currently published `oldid` identities verify against language-matched history
    payloads; the refreshed capture audit now resolves 80 curated
    citation/vocabulary references across 68 pages (including Activate Disco
    Ball) with all 80 headings and page revision IDs
    verified. The audit checks exact
    local archive hashes, but does not establish historical content equivalence,
    rules correctness or browser completeness.
  - [x] Replace the unavailable September 18 English Wiki citation snapshot with
    the validated September 26 capture, correcting three changed member paths.
    All cited headings and September 28 archived page revision IDs were verified;
    retain the missing original as a historical evidence limitation.
  - [ ] Review any change-sensitive curated interpretations that cannot be
    established from the available September 26 capture; the missing original
    cannot be used to prove earlier content equivalence.
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
    - [x] Reconcile the initial 119 unresolved Army Weapon enrichment entries
      against the exact N5 v5.3 PDF chart evidence and retained catalog categories
      using `tools/audit_weapon_definition_gaps.py`. The pinned Army database
      and 171 compared chart rows agree on the source identity. Results:
      115 chart-listed Weapons without standalone reviewed definitions,
      2 existing family-rule mapping ambiguities (Cybermine and PARA Mine),
      1 stale citation source (Flash Pulse), and 1 chart-absent source identity
      (SymbioBomb). This is source/profile availability evidence, **not**
      115 verified missing gameplay facts or completed browser coverage.
      The initial 29 review batches were generated under ignored `local/audits/`;
      subsequent fixes reduced the current total as recorded below.
    - [x] Reconcile the original three existing-reference flags. Cybermine and
      PARA Mine intentionally layer specific effects over `weapon:mines` through
      `uses-effects-of`; the coverage audit now recognizes a unique, acyclic
      specific-to-shared chain while retaining both cards and rejecting unrelated
      overlaps. Flash Pulse retains the reviewed Spanish N5.2 Immunity revision
      as comparative evidence, with a narrow accepted-historical-source policy
      override; the distinct Spanish N5.3 Wiki Weapon Chart conflict (REA-027)
      remains open. Neither rule text nor upstream Army profiles were rewritten.
    - [x] Publish a standalone, cited SymbioBomb Weapon reference from N5.3
      p. 74 and the pinned English Wiki page. Differentiate Unit Profile owner
      from Deployment-assigned user, the three permitted Pheroware Tactics,
      Endgame/Eraser's -3 Face to Face MOD, and end-of-Order removal. The
      catalog entry has no independent Weapon Chart attack profile, so none
      was synthesized; the existing owner/loadout records remain unchanged.
    - [x] Refresh the Weapon triage after these corrections: 115 chart-listed
      definition-review items, 1 explicitly accepted historical citation,
      no ambiguous family mappings and no chart-absent unrepresented entry.
      Source-based batch planning now produces 26 definition-review batches
      plus 1 retained citation-evidence batch; local reports are ignored.
    - [x] Browser-accept SymbioBomb at 1440, 390 and 320 px in headless Chrome,
      with source citations, no horizontal overflow or JS exceptions, desktop
      and keyboard navigation to PT, and preview-first/two-tap mobile links.
      Desktop and 320 px full-page screenshots were visually inspected. No
      independent attack profile is shown; real session assignment remains
      outside this static reference. Evidence stays under ignored local/audits/.
    - [x] Complete the first eight-identity Uncategorized Weapon batch.
      D-Charges (N5.3 pp. 70/186) and Disco Baller (pp. 71/186) retain their
      specific mode, charge, deployment, and activation rules. Nanopulser,
      Pulzar, Chain Rifle, Chain-colt, E/Mitter and Missile Launcher now have
      source-cited summaries and typed ammunition/trait/Skill links matching
      their exact printed chart profiles (pp. 186–187). The template size,
      ARM versus BTS Saving Roll, E/M disabling effects and Hit versus Blast
      Mode are explicit; no Army statistics were rewritten. Updated source
      triage: 107 remaining definition-review Weapons, 1 reviewed historical
      citation, and 25 definition-review batches plus the citation-evidence batch.
    - [ ] Browser-review the new D-Charges and Disco Baller cards (both source
      modes, related reference links, mobile layout and citations); API coverage
      does not substitute for this acceptance.
    - [x] Create source-only `skill:activate-disco-ball` with verified N5.3
      p. 71 and matching English Wiki evidence. Keep its Deactivator, allied
      Ball, LoF/ZoC, WIP +3, range MOD and Eclipse timing requirements
      explicit; add inline and related-rule navigation from Disco Baller.
      It has no fabricated Army Skill profile. Browser acceptance passed
      23/23 scenarios (seven reference pages × three viewport widths,
      desktop click and touch preview-then-navigation).
    - [x] Complete the first eight-identity CC Weapon batch (CC, PARA, DA,
      AP, Shock, E/M, EXP and Viral). All eight have curated N5.3 p. 177
      definitions, unchanged Army profiles, typed effect relationships and
      reviewed interaction entries. Viral's BioWeapon (DA+Shock) VITA-versus-STR
      resolution is explicitly **derived** from the source Trait and printed
      N/BTS/one-save baseline; unresolved Immunity combinations are not certified.
      N+E/M preserves its printed two BTS/2 saves without an invented extra ARM
      Roll. A generic CC Weapon requirement remains distinct from the named
      Army Weapon entry. Browser acceptance passed 26/26 viewport/navigation
      checks, with 320 px EXP/Viral screenshots reviewed; evidence is Git-ignored.
      The refreshed triage has 99 definition-review Weapons in 24 bounded
      batches plus Flash Pulse's accepted historical citation.
    - [x] Complete the eight-identity Pistol batch (Pistol, Heavy, Boarding,
      Breaker, Assault, AP Heavy, Silenced and MULTI). The N5.3 p. 182 profiles
      remain unmodified; the player-facing rules now distinguish Boarding
      Blast/Hit traits, AP against ARM versus BTS, Shock, the conditional
      Silent (-6) Dodge modifier (p. 175), combined AP+Shock (p. 67), and
      MULTI's three non-stacking modes. Related ammunition/trait/Skill links
      and interaction reviews are current. Browser acceptance passed 26/26
      scenarios across three viewport widths and two navigation behaviors;
      320 px Boarding/Silenced/MULTI screenshots were inspected.
      The refreshed triage shows 91 definition-review Weapons in 23 batches,
      plus Flash Pulse's accepted historical citation.
    - [x] Introduce canonical ammunition-summary reuse on Weapon profiles:
      exact source ID/name matches project each published component's summary,
      citations and route as display-only `ammunition_effects`. The UI offers
      expandable shared explanations, without deriving combined Saving Rolls,
      Immunity outcomes or mode effects. AP CC Weapon, AP Heavy Pistol,
      Breaker Pistol and Silenced Pistol now keep only profile-specific prose;
      AP Rifle demonstrates reuse without a standalone curated Weapon rule.
      The initial UI/API pilot passed focused regression and browser checks.
    - [x] Split the Weapon gap triage into **pending review categories** rather
      than implying every absent Weapon paragraph is a missing rule.
      The refreshed source-bound audit (v2) has 92 unresolved entries:
      89 with all canonical ammunition components linked, 2 special objects
      requiring separate effect/source review (Pitcher, Mine Dispenser), and
      Flash Pulse's accepted historical citation. 17 multi-profile Weapons
      require explicit mode-by-mode review. Batching: 22 shared-effects-review
      batches, 2 missing-effect-links batches, and 1 historical-citation batch.
      The previous 91-item report was stale; both the committed and current
      rules databases independently report 92 entries.
    - [x] Review the initial eight Rifle identities against the N5.3 p. 183
      chart. MULTI Rifle and K1 Combi Rifle require dedicated source-cited
      explanations for mode-specific Traits/Saving Rolls and the printed
      N with ARM=0 respectively. Combi Rifle, Rifle, Adhesive Launcher Rifle,
      Breaker Combi Rifle, AP Rifle and T2 Rifle reuse canonical ammunition
      and source Trait links without six duplicated Weapon descriptions.
      Those six decisions are pinned to exact Army profile hashes in
      `data/curated/weapon-shared-effect-reviews.json` and invalidated if a
      source profile changes; the triage keeps reviewed decisions visible.
      The source audit now reports 83 remaining actionable Weapon reviews,
      6 explicitly accepted shared-only identities, and 16 pending
      multi-profile candidates. Browser acceptance passed 26/26 viewport and
      navigation checks, with mobile first-tap preview and three 320 px
      screenshots reviewed. Private evidence is under ignored `local/audits/`.
      The remaining batch order begins with Shotguns.
    - [x] Complete source-specific review of the five N5.3 p. 184 Shotguns
      (Boarding, Light, Vulkan, Heavy, T2 Boarding) without duplicating
      canonical Ammunition explanations. The source lists no Direct Template
      for these profiles. Vulkan's Army spelling `Continous Damage` resolves
      through its reviewed alias to the Continuous Damage Trait; T2 Boarding
      retains Anti-materiel. All five are pinned by source profile hash in
      `data/curated/weapon-shared-effect-reviews.json`, with no new
      standalone Weapon definition required.
    - [x] Review both N5.3 p. 185 Submachine Guns. The standard
      Submachine Gun (N/ARM) and AP Submachine Gun (AP/ARM/2) share
      PS 7, Burst 3, Range MODs and Suppressive Fire. Their existing
      canonical ammunition and Trait references are sufficient; no
      standalone Weapon explanation is required. Both decisions are
      pinned to the exact Army source profiles in
      `data/curated/weapon-shared-effect-reviews.json`.
      Browser acceptance passed 8/8 checks across 1440/390/320 px,
      including desktop Trait and mobile Ammunition navigation.
    - [x] Review the next eight Uncategorized Weapons against N5.3
      chart pp. 186–188. Feuerbach and Hyper-Rapid Magnetic Cannon
      now have distinct, source-cited explanations for mutually exclusive
      modes and their different Burst, Saving Rolls and Traits. E/Marat,
      Mk12, Zapper, Contender, Crazykoala and Madtraps reuse canonical
      Ammunition/Traits without duplicating prose; those six decisions
      are pinned to exact Army profile hashes in the shared-review policy.
      E/Marat/Zapper retain distinct template sizes, while Crazykoala
      and Madtraps inherit Boost movement/contact only through Boost,
      never WildParrot or Mines effects. Browser checks passed 26/26
      across three viewport widths, including desktop and mobile links.
    - [x] Review the three N5.3 p. 179 Heavy Machine Guns without
      duplicating shared rules. Standard HMG (N/ARM) and AP HMG (AP/ARM/2)
      use source-pinned shared Ammunition/Suppressive Fire explanations
      with PS 5, Burst 4 and identical ranges. MULTI HMG has a cited,
      mode-specific reference: EXP/Anti-materiel B1 with three ARM Rolls
      versus AP or Shock B4 with one Roll and Suppressive Fire. The
      review ledger and 11/11 viewport/navigation browser checks are
      current; 320 px screenshots were inspected.
    - [x] Review the four N5.3 p. 178 Disposable Support Weapons.
      Panzerfaust, Blitzen and Akrylat-Kanone reuse source-linked
      Ammunition, Disposable and other Traits; each shared-only decision
      is pinned to its exact Army profile hash. Panzerfaust's AP+EXP
      profile retains three ARM/2 Rolls, Blitzen's [**] source footnote
      refers to E/M effects, and Akrylat-Kanone retains PARA/PH-6
      with the IMM-A source notation. Flammenspeer has a dedicated
      source-cited rules card: its Blast Mode uses N/ARM with an
      Impact Template; Hit Mode uses AP/ARM/2 without a Template.
      Continuous Damage and Disposable (2) apply to both modes.
      Browser acceptance passed 14/14 checks with narrow screenshots
      and desktop/touch navigation reviewed.
    - [x] Review N5.3 p. 185 Spitfires. Standard (N/ARM) and AP
      (AP/ARM/2) Spitfires reuse Normal/AP Ammunition and Suppressive
      Fire with PS 6, Burst 4 and identical ranges. Their shared-only
      source profiles are fingerprinted in
      `data/curated/weapon-shared-effect-reviews.json`. MULTI Spitfire
      now has its own cited explanation: DA Anti-Materiel B1/two ARM
      Saving Rolls versus AP/ARM/2 and Shock/ARM B4/one Saving Roll
      with Suppressive Fire. Army's source mode spelling
      `Anti-Material Mode` is preserved; the official chart uses
      `Anti-Materiel Mode`. Browser checks passed 11/11,
      including desktop Trait and mobile DA preview/navigation.
    - [x] Reconcile the four N5.3 p. 178 Grenades (Smoke,
      standard, E/M and Eclipse). The original single-mode profiles
      retain Speculative Attack, BS Weapon (PH), circular Impact
      Template, their distinct range MODs and Saving Rolls, and
      optional Non-lethal/Targetless/Reflective/[**] Traits.
      Smoke and Eclipse reuse their separately reviewed visibility-
      zone rules; E/M uses two BTS/2 Saving Rolls and standard
      Grenades one ARM Saving Roll. No standalone Weapon text
      is necessary. All four decisions are pinned to exact Army
      source profiles; browser acceptance passed 14/14 checks.
      Also correct reused Ammunition descriptions to render
      maintained-text links rather than raw [[reference]] syntax.
    - [x] Review the remaining four N5.3 p. 185 Sniper Rifles. MULTI
      retains distinct DA/ARM two-roll Anti-Materiel, AP/ARM/2 and Shock/ARM
      modes at Burst 2; K1 has Normal Ammunition with ARM=0; Viral retains
      conditional BioWeapon effects for VITA versus STR; Plasma Blast and Hit
      retain one ARM plus one BTS Saving Roll, with a Critical adding only one
      extra ARM roll. All four have source-cited references and interaction
      reviews, without rewriting the Army profiles. API regression checks
      preserve mode-specific Traits and linked reusable effects.
    - [x] Browser-review the four new Sniper Rifle cards at 1440, 390 and
      320 px, including source citations, shared-effect links and mode-specific
      explanations. Desktop BioWeapon navigation and mobile DA preview/two-tap
      navigation passed (14/14 checks). All four 320 px screenshots were
      inspected; no horizontal overflow or JavaScript errors were observed.
      Private evidence is under `local/audits/sniper-rifles-browser/`.
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
    - [x] **REA-045 ? Armed Turret E/Mitter source disclosure:**
      Verified that all six captured Army Turret E/Mitter modes use one
      BTS/2 Saving Roll versus two for standalone E/Mitter, both N5.3
      Weapon Charts and canonical E/M. Keep the imported source profile
      unchanged; its source-cited conflict is published in secondary
      source notes with links to E/Mitter and E/M Ammunition, separate
      from the REA-037 Silhouette conflict. Focused database, regression
      and browser checks cover the discrepancy and related links.
    - [ ] **REA-045 ? Official Armed Turret E/Mitter ruling:** Seek an
      applicable Corvus Belli erratum/FAQ or scoped confirmation of
      whether the Turret profile's one Saving Roll is intentional or
      the two-roll canonical E/Mitter applies. Do not infer a unique
      turret E/M rule or overwrite Army source data in the meantime.
    - [x] Browser-review all twelve current Weapon Properties and rule-origin
      navigation at 1440, 390 and 320 px, plus global search at 1440 and
      320 px, including touch preview/second-tap navigation, 76 passing
      browser checks, no overflow/JavaScript errors, and inspection of
      representative narrow-screen screenshots. Private
      evidence is in `local/audits/weapon-properties-browser/`.
    - [ ] Continue source-specific Weapon review without duplicating
      canonical Ammunition or Trait rules. The updated triage has
      47 actionable reviews, 33 accepted shared-only identities,
      and 9 pending multi-profile candidates, plus Flash Pulse's
      historical citation. Pitcher and Mine Dispenser still need separate
      missing-effect source reviews; the next shared-effects batches include
      Flamethrowers and Marksman Rifles.
    - [ ] Reconcile auxiliary/equipment object profiles and special-weapon
      prose clause by clause; identify missing facts, relationships, and browser
      coverage separately from raw source notation differences.
    - [ ] Reconcile remaining Wiki Weapon Chart *text-name* mismatches as aliases,
      multi-mode entries, or source-specific rules (including Chest Mine and SymbioBomb).
      This earlier Wiki text-match audit is separate from the complete 171-row N5 PDF
      profile alignment and its single chart-absent catalog identity. Reconcile the
      source prose (pp. 68–74), printed profiles (pp. 176–188), and API/browser
      coverage before classifying genuine missing facts, relationships, or definitions.
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
    as well as the authored text, and keep source conflicts visible. Track
    the [1.0 explanation audit](rules-explanation-audit-1.0.md#prioritized-remediation-plan)
    through the individual checks below; published cards still require the
    stated browser/source acceptance before their findings can be closed.
    - [x] **REA-001 ? Engineer target and recovery:** Reviewed the
      separate STR repair and eligible State-cancellation branches, success
      versus failed WIP outcomes, self-use and Stunned exceptions. Added
      an allied VITA Targeted example that does not require STR, and checked
      the published Engineer/Targeted/Stunned/Doctor references and links.
      Responsive browser acceptance passed 18/18; non-Allied eligibility
      remains independently open under REA-038.
    - [x] **REA-002 ? Doctor recovery:** Reviewed ordinary Unconscious
      VITA/contact recovery, lethal failure, 2W and ReRoll WIP variants,
      and the Command Token reroll distinction. Published source-linked
      examples for conscious wounded targets, Stunned VITA versus STR,
      No Wound Incapacitation self-treatment, and Technorganic STR recovery
      only while Unconscious. Browser acceptance passed 21/21 at 1440,
      390 and 320 px; non-Allied target eligibility remains REA-038.
    - [x] **REA-003 ? Intuitive Attack:** Verified the single unmodified
      WIP Roll as the B1 Attack resolution, eligible Face to Face AROs,
      Main Target-only Critical effect, and special Deployable placement.
      Added three worked examples with English/Spanish N5.3 citations,
      source/database regressions and responsive browser acceptance.
      No additional BS Roll or gameplay rule was introduced.
    - [ ] **REA-004 — Continuous Damage:** Verify the documented Critical
      exception in the Trait card; keep deferred typed-variant edges separate.
    - [ ] **REA-005 — BS Weapon (WIP):** Verify the prohibited Skill
      combinations on the player-facing Trait card without promoting
      deferred typed-variant edges.
    - [ ] **REA-006 — Controlled Jump:** Check the Program card's immediate
      declaration, optional table-wide ARO, opposing-Program cancellation,
      and separate scenario MODs.
    - [ ] **REA-007 — Request Speedball:** Verify the FAQ exclusion in both
      the Skill and Program cards.
    - [x] **REA-008 — Protheion:** The Skill card explains the FAQ overkill
      limit, profile-listed enemy Attribute MOD, and recovery order;
      player-facing wording has been verified.
    - [ ] **REA-009 — Simultaneous recovery:** Review the updated explanation
      for recovery and re-infliction in the same Order.
    - [ ] **REA-010 — General Immunity:** Verify the Immunity (ARM/BTS)
      protection, printed Monofilament exception, and existing Flash Pulse
      example in the browser.
    - [ ] **REA-011 — Reviewed Immunity interactions:** Check the dedicated
      player-facing presentation of five cases for applicability and
      explicit/derived labels, including keyboard, mobile, and browser
      layout. Do not add unreviewed Plasma/Enhanced cases to the arrays.
    - [ ] **REA-012 — Smoke/Eclipse:** Review browser Clarifications and
      examples for rolled LoF opposition, MSV/Reflective exceptions,
      unopposed placement, Dodge, and Criticals.
    - [ ] **REA-013 — AP, E/M, and T2:** Verify the Ammunition pages explain
      rounding up halved defenses and identifying original-hit versus
      extra-Critical T2 dice before rolling; typed values remain unchanged.
    - [ ] **REA-014 — Dodge/Reset:** Verify the Dodge, Reset, Engaged, and
      Bangbomb cards cover per-Attack evasion, post-Dodge movement,
      Engaged exit position, cumulative Reset State MODs, and Sixth Sense.
    - [ ] **REA-015 — State cancellation:** Inspect the source-cited
      State-specific cancellation explanations in the browser; keep this
      distinct from the completed REA-026 baseline.
    - [x] **REA-017 — Peripheral subtypes:** Shared activation, Coherency,
      Roll ownership, Servant/Connected Cyberplug Doctor/Engineer contact,
      Control Spearhead, Ancillary deployment/Fireteam exceptions, and
      Cyberplug Autonomous behavior are published in linked, source-cited
      references. Chrome acceptance on 2026-10-13 passed 24 page/viewport
      cases (1440/390/320 px), six links, keyboard/touch navigation,
      with no JavaScript errors or horizontal clipping; see
      [development checks](testing.md#10-peripheral-rea-017-browser-acceptance).
      Dependent source-specific exceptions remain separately tracked.
    - [x] **REA-018 — Hacking Area, Firewall, Supportware:** The existing
      source-linked cards match N5.3 pp. 55–56 and 60 and FAQ v0.1 p. 1:
      enemy Repeater Hacker-only targeting and Idle, 8-inch ARO measurements,
      a disabled Hacking Device's Firewall, and whole-Program Fairy Dust
      replacement. Browser acceptance passed 18/18 cases at 1440/390/320 px,
      with no errors or overflow. Related program-specific exceptions remain
      under their owning audit findings.
    - [x] **REA-019 — Negative Feedback:** Verified the shared Label's
      same-Trooper cancellation and the distinct Cybermask/White Noise
      lifetimes against N5.3 pp. 59, 61, 76 and 174. Chromium acceptance
      covered three cards and Label-to-Program links at 1440/390/320 px
      (15/15 passed); no JavaScript errors or horizontal overflow.
      Other NFB interactions remain scoped to their owning rules.
    - [x] **REA-020 — Fireteam ownership and integrity:** The published
      shared baseline now distinguishes Active Leader-only actions, common
      Movement/Reset, individual reactive rolls and ARO majority selection,
      ordinary departure versus cancellation, rejoining at the next States
      Phase and formation-only Type minimums. FT Master, Number 2, NCO,
      Tactical Awareness and Peripheral conditions link to their owners.
      Source and browser acceptance passed 33/33 checks at 1440/390/320 px;
      final chart selection/Wildcard/keyboard/touch workflow remains separate.
    - [x] **REA-021 — Special Dice:** Verified +1 SD versus Burst,
      allocation/discard, Disposable charges, ranged Kits, Martial Arts
      Levels 3/5, Berserk's Long Skill exception, Fireteam Levels 2/4,
      and the Discover distinction against N5.3 and FAQ v0.1. The
      Fireteam Level 2 table now links the shared Special Dice rule.
      Browser acceptance passed 39/39 route/navigation checks at
      1440/390/320 px. The separate official Spanish reminder conflict
      remains unresolved under REA-041.
    - [x] **REA-022 — Recovery Kits and Disposable:** Verified same-Order
      multiple MediKit/GizmoKit hits, one-success PH recovery, Remote
      Presence's Unconscious exception, and B versus SD charge use
      against N5.3 pp. 75, 123–124 and 175. The reference cards now
      explain mixed PH results and the two-unspent-charge Double Shot
      prerequisite with focused regression examples.
    - [x] **REA-023 — Deployable placement geometry:** Reviewed the
      Place Deployable Active/Reactive contact, surface, timing and FAQ
      occupied-location rule; Perimeter's passable path; Minelayer's
      Trigger Area/ZoC enemy exclusions; and Deployable lifecycle and
      item-specific placement. All nine published reference pages
      passed browser validation at 1440, 390 and 320 px (39/39).
      Armed Turret's printed Silhouette and E/Mitter conflicts remain
      separate under REA-037 and REA-045.
    - [x] **REA-024 — BioWeapon and Viral Mine:** Linked the VITA-only
      DA+Shock effect and its derived Saving Roll conditions to canonical
      Ammunition, Shock and Immunity references. Viral Mine retains the
      pinned N/BTS/one-roll source profile and reuses the reviewed Viral
      Weapon Property. No new universal Immunity interpretation was made.
      Source/API and browser acceptance verified; a separate pre-existing
      320 px Ammunition header overflow remains in final UI acceptance.
    - [x] **REA-026 — Shared General Rules:** Face to Face Rolls, Saving
      Rolls, Guts Rolls, Order Expenditure Sequence, and Coordinated
      Orders are published, linked, and source-cited. Chrome acceptance
      on 2026-10-13 covered all five at 1440/390/320 px, link
      navigation, keyboard, touch previews, and citations without
      page errors or horizontal overflow. See
      [development checks](testing.md#10-general-rules-rea-026-browser-acceptance).
      Broader source and release acceptance remains under the 1.0 gate.
    - [x] **REA-027 — Flash Pulse source reconciliation:** Verified the
      pinned Army weapon 72 and English/Spanish N5.3 PDF weapon charts
      retain STUN, one BTS/PB Saving Roll, Non-Lethal and State: Stunned.
      The printed Immunity examples independently require a failed
      Saving Roll to cause Stunned. Both Spanish Wiki Weapon Charts
      (revisions 3987/3988) still show two PB rolls without the Trait,
      confirmed by direct live/oldid retrieval on 2026-10-14.
      The conflicting publications, revision identities, source URLs
      and accepted one-roll profile now have regression and browser
      acceptance coverage; no roll or gameplay data were overwritten.
      - [ ] **External publication correction pending:** Seek an
        authoritative Wiki correction or erratum for both Spanish
        charts. The source conflict remains explicitly unresolved;
        do not reinterpret the rules from revision chronology alone.
    - [x] **REA-028 — Kobra Pistol CC source decisions:** Confirmed DA's
      two ARM Saving Rolls (three on a Critical) against both N5.3
      PDF one-roll cells, the pinned Army profile and exact Wiki edits.
      Mode-scoped reference now separately flags the still-disputed
      Anti-materiel Trait. Wiki history 4021/4077/4082 records the
      roll correction before the Trait addition; current Army data and
      the BS Shock mode are unchanged.
      - [ ] **External Anti-materiel ruling pending:** Seek official
        clarification on Kobra CC's Trait in the bilingual printed
        chart versus Army/current Wiki. Do not infer the Trait from DA
        or infer that a later Wiki revision settles the discrepancy.
    - [x] **REA-030 — General versus ITS FAQ applicability:** Reviewed
      English and Spanish N5 FAQ v0.1. Source registration already
      existed in English; Spanish v0.1 is now pinned. Sixth Sense/MSV1
      explains the conditional -6 LoF exception when targeted through
      a Zero Visibility Zone. ITS Spotlight Classified scoring and
      undeployed Ancillary scoring are annotated with their exact scope.
      Core Supplies, Annihilation and Firefight mechanics remain unchanged.
      - [ ] **External scope ruling:** Determine whether the ITS
        scenario-element Marker-State answer and undeployed Ancillary
        Killed exception also apply to the four core N5.3 scenarios.
      - [ ] **Future full FAQ collection:** The selected ruling
        references do not constitute a complete versioned FAQ/ITS
        data collection; do not mix all ITS decisions into core rules.
    - [x] **REA-034 ? Fireteam Level 3 printed example:** Preserve the
      bilingual N5.3 pp. 138/142 Morat CORE Case 2 contradiction and
      explain the correct table-derived Level 3 bonus in the public
      Fireteams reference, without granting Level 4 +1 BS/CD. Source
      notes and citations are distinct from REA-041's dice reminder.
      Focused rules tests and responsive browser acceptance passed 9/9.
    - [ ] **REA-034 ? Official example correction:** Seek an official
      correction for the Level 3 Morat example granting Level 4's +1
      BS/CD in both printed languages. Do not infer that the example
      overrides the Fireteam Level table in the meantime.
    - [x] **REA-035 — Impersonation Discover:** Verified ordinary Discover
      Range/Cover/Mimetism MODs versus IMP-1's additional -3, first/second
      stage, Biometric Visor, one-Order and failed-retry limits against
      the N5.3 sources. Browser acceptance passed at 1440/390/320 px.
    - [x] **REA-036 — Deployable Cover:** Published and verified
      contact/obscuration requirements, variant/non-stacking conditions,
      Vitroferro's cap before PS, and S3/Disposable (2)/Indiscriminate/
      Perimeter source properties. Browser acceptance passed at all three
      widths; broader placement and FAQ scope remain separate tasks.
    - [x] **REA-037 ? Armed Turret Silhouette source presentation:**
      Verified detailed S2 against English/Spanish N5.3 pp. 70/74 and
      both pinned Wiki detailed profiles; confirmed conflicting S1 in
      English summary pp. 74/195 and Spanish p. 203. Retain the existing
      detailed S2 stat and publish the explicit discrepancy, complete
      source references and LoF/clearance consequences. Chromium
      acceptance passed at desktop/390/320 px (3/3).
    - [ ] **REA-037 ? Official Armed Turret Silhouette ruling:**
      Seek a scoped Corvus Belli correction or approved precedence
      decision for S2 detailed profiles versus S1 summary tables.
      Do not change the existing S2 value solely from the summary or
      treat its use as an authoritative resolution.
    - [x] **REA-038 ? Doctor/Engineer direct-use scope:** Reconcile
      direct Skill contact/State requirements against EN N5.3 pp. 90-91,
      close-combat restrictions pp. 51/160, locally scoped Allied gates
      for Kits pp. 123-124 and Servant/Cyberplug pp. 106-107, plus
      English/Spanish captured Wiki Skills. Publish clear source-cited
      direct-versus-delegated eligibility and Engaged conditions without
      introducing an unsupported universal target-allegiance rule.
    - [ ] **REA-038 ? Non-Allied direct-target ruling:** Obtain a scoped
      current N5 ruling or explicit project decision on the *derived*
      interpretation for non-Allied Unconscious/Immobilized, Neutral,
      Hostile, and scenario-specific targets. Absence of an Allied gate
      in direct Skill text alone is not a verified universal permission.
      Do not change gameplay eligibility beyond confirmed clauses until
      this source decision is made.
    - [x] **REA-039 — TinBot sharing:** N5.3 p. 127 operational eligibility,
      Fireteam-wide benefits, same-advantage MOD selection, owner departure,
      nonblocking/untargetable State Token status and Dead State removal
      are linked from the family and Fireteam references. All six named
      options retain source-specific effects. Focused source/API tests and
      responsive browser acceptance passed 12/12 checks at 1440/390/320 px.
    - [x] **REA-040 — Request SpecBall:** Published the core N5.3
      Skill with Game Round/Active Turn/once-per-game eligibility, one
      55 mm Combat Jump/PH 15 Token, different item selection, contact
      pickup, Marker cancellation, end-of-Order Enhanced Profile and
      SpecBot placement. Linked Infinity Spec-Ops and Combat Jump, kept
      Request Speedball and Season 18 TEAM-OPS/Tacball separate, and
      pinned the English printed-name discrepancy against Spanish N5.3.
      Source/database and responsive browser acceptance passed (24/24).
      Complete chart/list configurators remain post-1.0.
    - [x] **REA-041 ? Fireteam dice source review:** English N5.3
      pp. 75/136 and Spanish p. 75 agree that B6 caps Burst, not the
      extra Special Dice rolled and discarded. Spanish p. 140 contradicts
      that rule by imposing a six-dice inclusive reminder; English/Spanish
      evidence and the unsolved discrepancy are now visible as linked
      source notes on Special Dice and Fireteams. Responsive browser
      acceptance passed (15/15). No gameplay cap was changed.
    - [ ] **REA-041 ? Official Fireteam dice clarification:** Obtain an
      authoritative erratum or scoped ruling for Spanish N5.3 p. 140
      versus p. 75 and English pp. 75/136. Keep the contradiction
      explicit meanwhile; this external dependency does not block the
      locally reviewed 1.0 reference explanation.
    - [x] **REA-042 — Dodge (ARM+3) player reference:** Explain the
      profile-listed +3 ARM Saving Roll modifier from English and Spanish
      N5.3 p. 75, never +3 PH or a universal Dodge bonus. Pin the
      contrasting failed-PH condition in both English and Spanish Wiki
      snapshots, including Spanish history revision 4012. Add bilingual
      PDF/Wiki source notes, tests, and responsive browser acceptance
      (12/12); preserve the printed profile without a mechanics rewrite.
    - [ ] **REA-042 — Official Dodge modifier clarification:** Seek an
      authoritative correction for the PDF-versus-Wiki failed-PH
      condition. The unresolved external source disagreement is visible
      to players and is not a remaining 1.0 implementation blocker.
    - [x] **REA-043 — Counterintelligence:** Verified against N5.3
      pp. 90/128 and in the rendered Skill reference at 1440, 390 and
      320 px. Both Strategic Use branches retain their first-Turn
      conditions; the relaxed Command Token limit benefits the Skill
      owner, not the opposing player. Browser acceptance passed 6/6.
    - [x] **REA-044 — Metadata-only Weapons:** Publish the reviewed
      Breaker Marksman Rifle from Army source 225 with exact source-profile
      validation, numeric/slug lookup, standalone weapon rule reference
      and zero Unit usage. Other unused historical metadata remains unpublished;
      a comprehensive metadata inventory is not a 1.0 blocker.
    - [ ] **Cross-source applicability:** Resolve material source
      conflicts and FAQ scope before dependent curation. Use the
      [source manifest](rules-explanation-audit-1.0-sources.md) and
      [N5.3 reconciliation](rules-explanation-audit-1.0-n5.3-reconciliation.md).
      Preserve the S17/S21 provenance and seek scoped errata instead
      of treating the audit's assessment as replacement semantics.
    - [ ] **Clause-review coverage gate:** Complete the
      [inventory gate](rules-explanation-audit-1.0-inventory.md#audit-completion-gate).
      The 304 selected clause reviews and 63 screening-only records
      do not constitute 367 full approvals.
    - [ ] **Visibility Zone inventory additions:** Include the five
      newer Visibility Zone Game terms in final record acceptance;
      they postdate the frozen 367-record explanation-audit inventory.
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
    - [x] Represent the five reviewed combined Army Ammunition source forms
      (`AP+DA`, `AP+Exp`, `AP+Shock`, `AP+T2`, `N+E/M`) with exact,
      ordered canonical
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
      per component or infer totals from the five combined source mappings.
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
  [the data model](data-model.md#scenario-model-implemented-core-and-future-extensions).
  - [ ] Reconcile scenario facts, scoring, scoped concepts and source issues with the
    final 1.0 source inventory for all six supported Army Points values. This is
    source-completeness review, not a request to reimplement the published domain.
  - [ ] Verify **Domination's 350-point SWC row** against authoritative clarification.
    N5.3 page 151 prints 6 SWC, unlike Annihilation's 7 at the same Army Points.
    Retain the printed value and visible uncertainty until clarified; this existing
    source disagreement did not block released 0.10.1; retain it for
    the 1.0 source-completeness review.
  - [ ] Confirm the current model remains source/scope-aware against the reviewed ITS
    variation during final completeness review. ITS content, ITS-only geometry,
    tournament tooling and an interactive scenario editor remain post-1.0.
  - **Browser acceptance:** The separate
    [1.0 core-scenario browser checklist](#final-10-acceptance) owns
    keyboard/touch, rapid selection, theme/distance, direct/soft navigation,
    and loading/empty/error states. The 2026-10-08 user-confirmed visual
    review and automated lifecycle/responsive tests do not replace
    interactive browser acceptance.
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

The 0.10.1 offline checks and later REA-017/026 scoped Chrome reviews do not
prove the four cross-surface browser interactions below. These incomplete
acceptance tasks move forward to 1.0 rather than blocking the published 0.10.1:

- [ ] **Web frontend — reference-card browser acceptance:** Inspect IMP-2,
  Stealth, Deployable Cover, TinBot and Kobra CC on desktop and narrow screens.
  Follow rules, Attribute and source links; confirm readability and navigation.
  The earlier offline 52/52 tests and seven-view responsive check were not
  substitutes for these interactions.
- [ ] **Web frontend — Fireteam browser acceptance:** Select an Army, verify
  Fireteam formation requirements and ongoing-integrity help, change Wildcard
  settings and navigate between Fireteams, Units and references. Test desktop
  and narrow screens; keep remaining REA-020 mechanics separately tracked.
- [ ] **Web frontend — core-scenario browser acceptance:** Browse all four
  Scenarios, change Army Points rapidly, follow scoped rules links, navigate
  away/back, and check maps in both themes and distance units. Exercise
  keyboard and touch, including loading/empty/error states where practical.
  Coordinate this with the existing scenario source-completeness task.
- [ ] **Web frontend — Visibility Zone and Ammunition/Immunity acceptance:**
  Open Visibility Zone tooltips and Ammunition/Immunity cross-links with
  pointer, keyboard and touch. Verify readable content and no horizontal
  clipping across desktop and narrow-screen layouts.
  - [ ] Correct the shared "Rules reference" tag in the narrow breadcrumb:
    at 320 px it overflows by about 6 px on Normal, DA and Shock Ammunition
    detail pages. This predates the BioWeapon curation and belongs to the
    shared reference layout rather than Ammunition semantics.

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
