# InfinityDB backlog

This is the working implementation backlog. Every unchecked item belongs to exactly
one release bucket: **1.0.0** or **post-1.0**.
The buckets are planning commitments, not a promise that a minor release cannot move a
low-risk item earlier or defer a non-gating item when evidence changes.

This file does not define current application behavior. Current behavior belongs in
the relevant reference documentation; lasting design direction belongs in
`docs/architecture.md` or `docs/data-model.md`; durable release acceptance criteria
belong in `docs/releasing.md`.

Keep completed prerequisites only when they clarify an open dependency. Summarize
implemented foundations with links to their canonical owners; remove completed run
diaries after their durable outcomes are recorded. Git history retains implementation
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
- Twenty-eight dated FAQ rulings, nineteen carried from v0.0, with validated
  applicability, supersession, explicit-context API and topic/scenario cards:
  [published FAQ contract](data-model.md#dated-faqerrata-layer-published-reviewed-subset).
- Martial Arts, Booty and MetaChemistry typed, linked charts with reviewed PDF,
  Wiki-history and FAQ evidence:
  [structured charts](data-model.md#structured-skill-reference-charts) and
  [source provenance](n5-source-history.md#reviewed-10-structured-skill-chart-provenance).
- Reviewed exact source variants, including Mimetism, Berserk and Dodge mappings;
  the cross-army usage index remains unimplemented:
  [variant contract](data-model.md#rule-variant-usage-index--accepted-design-direction-not-implemented).
- The 1.0 interaction-review ledger passes for 191 supporting identities with
  zero pending entries. This is a separate gate from full clause/source review:
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
| 4. Derived references | Declaration matrix, variant usage, Restrictions, Weapon comparison and Deployables | Reviewed owning facts and exact variant/scope semantics; existing linked charts are complete |
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

### Source inventory and gap batches

- [ ] **Data processing + Project infrastructure:** Establish the 1.0 completeness baseline
  against the final intended input set; existing bounded reviews are prerequisites.
  - [ ] Review any change-sensitive curated interpretations that cannot be
    established from the available September 26 capture; the missing original
    cannot be used to prove earlier content equivalence.
  - [ ] Pin the intended Army snapshot, rules/FAQ/annex PDF versions, and supported wiki evidence.
    Record archive/content hashes as appropriate, publication dates separately from acquisition
    dates, and the generated database/publication identities. A later source refresh reopens the
    affected coverage review; normal checks must not acquire newer inputs implicitly.
    Include relevant dated official Corvus Belli rules-update posts as supplementary
    release-change evidence (not replacements for the versioned primary sources).
    - [x] Archive the **pre-Peripheral-projection Army/rules database-pair baseline**
      from the exact September 29 pinned Army ZIP. The ignored
      `local/audits/gate-1.0/reference-baseline-current-20261021.{json,md}`
      records 58 matched Army documents, 23 published categories and 122
      source groups; Army SHA-256
      `ec77c5d1fd742bcefb3975dd223550fe3a51053d39fbdb34ce814e3ddd62e6c9`,
      rules SHA-256
      `3ab86945aaadf09c4104e3e08801531987957ffa866124f87c602609938cd3e3`,
      paired runtime revision
      `3079979bca345289fbc20f1ef3272ec0e706659f20718435b237867f847ef2fe`.
      The earlier `reference-baseline.{json,md}` is retained as historical
      evidence; neither report certifies gameplay or browser completeness.
      The Army database was subsequently rebuilt for the source-only
      Peripheral publication (schema 26, compatibility 35; SHA-256
      `8a5840d1ff632e89de26210ee7bcb47e54c6579c15b5c3436e226702e872d7c8`).
      That earlier baseline remains historical, not current candidate evidence.
    - [ ] Refresh the release-candidate baseline and source occupancy gate once
      the Army/rules database pair is frozen for 1.0. Do not reuse the
      pre-Peripheral-projection publication SHA or paired runtime revision.
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
    - [x] Check **statically unrepresented Army source-field occupancy** against the
      paired raw/application database. The September 29 Army snapshot
      (reexported SHA-256 `8a5840d1ff632e89de26210ee7bcb47e54c6579c15b5c3436e226702e872d7c8`)
      has **0 populated fields out of 39 unrepresented candidates** across 70 source
      tables/441 fields. This includes global Unit-option Skill/Equipment/Weapon references,
      Extras and Characteristics, and profile/group notes; no currently occupied missing
      UI fields were found. `test_pinned_published_army_has_no_occupied_unrepresented_source_fields`
      guards the actual pair when the ignored raw database is available; clean CI skips
      that local-only proof, so the release `--source-occupancy-gate` remains required.
      A changed Army snapshot or export pair reopens this check. This does **not** certify
      derived relationships or browser parity.
    - [ ] Cross-check the **derived Army relationships** that source-field occupancy alone
      cannot certify: canonical Unit/profile/loadout identities, shared Unit-option Includes,
      Peripheral/controller targets, Reinforcement parent/pool membership and Army-local
      Fireteam availability. Distinguish an existing working projection from an uncovered
      source relationship or inaccessible player-facing context; add only confirmed
      deficiencies to the owning vertical slice.
      - [x] Validate current published relationship integrity using independent logical-Unit,
        faction/Army and Fireteam semantic audits, Peripheral materialization validation,
        all three Army-scoped Include target tables, Fireteam FTO loadout source identities,
        and Reinforcement parent references. The nonempty published graph passes
        `test_pinned_army_derived_relationships_have_live_published_targets`.
        This is a source/storage invariant, not proof of all player-facing contexts.
      - [ ] Reconcile normal Unit/Army/Fireteam browser reachability and applicability
        for these relationships (including Reinforcement pool context); classify any
        missing, misleading or deliberately deferred behavior with source evidence.
        - [x] Extend normal Unit Chromium acceptance to Army-scoped profile/loadout
          and composite-option Includes. Four distinct source-backed Units at 1440
          and 390 px passed **8/8 pages**, verifying **232 Include links** against
          the same Army's actual loadout anchors, plus correct row placement.
          Empty and malformed link/quantity/Controller-access cases are checked
          separately in hermetic regressions. This is bounded browser parity,
          not all-Unit or gameplay-list validation.
        - [x] **Publish source-only Peripheral attachment labels** without
          inferring identity, type or Controller assignment. Deterministically
          project attached Army-local `peripherals` names into the new
          `application_peripheral_source_labels` runtime table; the raw
          definition table remains excluded. The existing reviewed mappings
          take precedence when present; unmapped profile/loadout attachments
          retain their name, quantity and explicit source-local identity in
          API and normal Unit rows (no placeholder Peripheral type). Missing
          or drifted source definitions fail validation. Rebuilt the pinned
          September 29 snapshot at compatibility version 35, Army SHA-256
          `8a5840d1ff632e89de26210ee7bcb47e54c6579c15b5c3436e226702e872d7c8`.
          The source contains 818 `option_peripherals` occurrences; its
          reviewed Peripheral entity/Controller tables remain empty.
          Importer, API and real browser regressions cover the source-only
          projection. This resolves *attachment display*, not the separate
          source-by-source review of Peripheral rules and Controller semantics.
        - [x] Expose source-backed **Reinforcement Section/parent links** in
          ordinary Unit details. Link to each selected Army's Unit Explorer
          view; restrict player-visible relationships to Army contexts that
          pass the optional-unit presentation filter. Broader declared-faction
          memberships and source IDs remain developer-only rather than
          implying legal Army-list membership. A pinned-source Chromium case
          verifies named parent links and share-state routes at 1440/390 px.
          This is a read-only reference, not roster legality validation.
        - [x] Expose **verified Army-local Fireteam FTO profiles** in normal
          member rows without treating FTO as a generic Unit-wide entitlement.
          The player-facing label requires a source Army member resolution,
          source Unit and Unit link, an explicit FTO marker and matching
          published loadout occurrences. The existing FTO Profiles and Notes
          diagnostic columns remain developer-only; context mismatches and
          no-matching-option cases do not gain inferred eligibility.
          Injected Wildcard rows do not repeat the FTO summary, since
          general Wildcard eligibility is a separate chart relationship.
          The pinned `audit_fireteam_semantics.py` regression verifies
          resolved/unresolved categories; a normal Chromium Fireteam chart
          asserts API-to-visible-FTO parity, Unit links, no Wildcard
          promotion and no viewport overflow at 1440/390 px.
          Player-facing FTO labels do not validate complete roster legality.
        - [x] Validate normal **Army overview** Reinforcement parent/section
          links against the published Army API in Chromium at 1440/390 px.
          `test_verify_army_overview_browser.py` covers all published visible
          Army cards and their source-backed links in both directions, shared
          sections, keyboard-triggered fragments/focus, and horizontal overflow;
          injected API cases cover missing, non-playable and legacy references.
          The overview exposes navigation, not Army List composition legality.
          This bounded acceptance does not close the broader source-to-browser
          relationship review.
    - [ ] Obtain independent human visual acceptance if required for the 1.0
      release; agent-reviewed screenshots and automated browser assertions
      are evidence, not a human sign-off.
    - [x] Browser-review D-Charges and Disco Baller source cards at 1440/390 px.
      `test_verify_weapon_source_cards_browser.py` verifies both imported
      Weapon modes/profile values against the published API, rendered linked
      references and N5.3 citations, normal rule-card navigation, and page
      overflow without JavaScript errors. This is bounded automated Chromium
      acceptance, not independent human visual sign-off or exhaustive Weaponry
      source coverage.
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
  - [ ] Reconcile `data/curated/rules-interactions/reviews.json` and `catalog-scope.json` with the
    pinned input set. Historical review/defer release labels are evidence, not the active roadmap:
    the current 1.0 ledger has no pending identities. Reassess deferred candidates and changed
    inputs against the 1.0 gate rather than treating every candidate as automatically required
    or automatically excluded.
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
      - [ ] Verify other conditional declaration permissions and
        remaining numerical Army replacement variants. Selected
        checks do not certify the full 1.0 corpus.
    - [ ] **Visibility Zone inventory additions:** Include the five
      newer Visibility Zone Game terms in final record acceptance;
      they postdate the frozen 367-record explanation-audit inventory.
      - [ ] Include these five post-inventory records explicitly in
        final 1.0 whole-corpus acceptance; do not silently expand
        the frozen 367-record explanation-audit denominator.
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
    - [ ] Review other component-level Immunities, BTS-based variants and
      weapon-specific exceptions. Do not generalize from the reviewed examples
      or the name-scoped Viral Vulnerability case.
    - [ ] Review the remaining fact/relation completeness, including combined-effect
      precedence, full Critical interactions, affected Attributes, visibility Face
      to Face outcomes, conditional State cross-links, and comparison-view
      consumption. Do not infer executable mechanics from reviewed reference facts.
    - [ ] Validate every published base identity and reviewed combined form against the pinned
      source; prove that weapon links, Ammunition detail, and later comparison views consume the
      same facts without conflating composition with roll notation.
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
  - [ ] Verify Domination's 350-point SWC disclosure on the final candidate:
    the published English-source 6 and conflicting official Spanish 7 must be
    clearly sourced and explained. An official clarification is not required
    for release; preserve the uncertainty and reviewed publication baseline.
  - **Browser acceptance:** The separate
    [1.0 core-scenario browser checklist](#final-10-acceptance) owns
    keyboard/touch, rapid selection, theme/distance, direct/soft navigation,
    and loading/empty/error states. Bounded Chromium acceptance subsequently
    covered all 24 selections; rerun on the final candidate. The earlier
    user-confirmed visual review and lifecycle tests alone do not establish it.
  - **Completion:** the final source inventory accounts for every in-scope fact and
    scoped concept, and all four scenarios remain understandable and navigable in
    every supported configuration. No mutable match state or live scoring engine is required.

- [ ] **Data processing + Web backend + Web frontend:** Complete source coverage and
  applicability review of the published dated FAQ/errata layer from `data/pdf/faq/`.
  The authoring contract, source-precedence policy, export validation, runtime selector,
  explicit-context API and 28 browser-published rulings are implemented; see the
  [current contract](data-model.md#dated-faqerrata-layer-published-reviewed-subset).
  - [ ] Reconcile every remaining in-scope ruling against the pinned FAQ and
    source inventory. Reuse the existing question/answer, topic, version/date,
    citation and applicability fields; preserve original provenance on carry-forwards.
  - [ ] Prioritize links to features already represented by the app: deployment
    and private-information handling; BS Attack/MOD and template behavior;
    hacking Firewall; Marker, Camouflage, Peripheral, and State interactions;
    Coordinated Orders; and Fireteam creation/bonuses/integrity. Defer
    ITS-only FAQ rulings and season-specific scenarios to post-1.0; do not
    present their outcomes as universal core rules.
  - [ ] Verify remaining source selections, conflicts and effective-date scopes
    against the implemented applicability-first precedence policy. Every selected
    answer must show its date/version and remain separate from the base definition.
    Assess historical replay and user-selectable applicability against the current
    reference gate; full ITS history is post-1.0.
  - **Completion:** cover carried-forward/cross-posted rulings, supersession, conflicting sources,
    missing targets, and out-of-scope seasons. Every in-scope ruling is discoverable from its topic
    or scenario, and the reader can distinguish base rules from applicable clarifications.

- [ ] **Data processing + Web backend + Web frontend:** Extend generated rules-reference
  projections that build on the enriched canonical data rather than duplicating its facts.
  - [ ] Add a generated cross-army rule-variant usage index once exact variant
    semantics are reconciled: canonical Skill/Equipment -> Level/MOD/typed parameter
    variant -> Unit/profile/loadout occurrences. Derive it from canonical rules and
    Army occurrence relationships rather than maintaining a second classification.
    - [ ] Reconcile the remaining **38 Skill** source IDs with unresolved
      occurrence parameters and 14 Equipment source IDs. The tracked
      rules.db now includes the reviewed Mimetism/Berserk/Dodge mappings;
      `tests/test_audit_source_variant_inputs.py` pins this baseline
      and independently checks a fresh curated rules export. Revalidate
      the release-matched source pair before final certification.
      Source-only occurrence verification requires the ignored raw
      Army archive and is skipped in clean CI.
      Review other mixed TEXT/DISTANCE sources and named Equipment
      variants with extra MODs; preserve raw signatures and exclude
      unreviewed specific combinations from index counts. Fail closed
      rather than parsing numeric-looking display strings.
    - [ ] Materialize the read-only index and public context links, then test
      duplicate-source, reused-payload, cross-Army, profile/loadout-specific,
      included/Peripheral, and ambiguous-variant cases before publication.
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
      - [x] In normal Chromium at 390 px, discover every **multi-profile Weapon**
        from the published catalog API and compare all rendered mode titles,
        Ammunition text/component links, B, PS, Saving notation, range bands
        and optional object-profile text against the same API. The dynamic
        `test_all_published_multi_profile_weapon_statlines_render_on_mobile`
        also checks catalog/detail profile cardinality, JavaScript errors
        and page overflow.
      - [x] Extend the pinned published-Weapon audit across all catalog details:
        `test_published_weapon_profiles_preserve_source_metadata` compares
        every published profile to `metadata_weapons` fields, source Traits
        and raw range bands without overwriting curated supplements.
        The three-shard `test_all_published_single_profile_weapon_cards_at_mobile_width`
        compares every single-profile card's title, stats, Ammunition links,
        range bands and optional deployed-object profile at 390 px. The
        profile-less SymbioBomb has a reviewed rule card without a standalone
        Weapon Chart statline; browser acceptance verifies this separately.
        This proves current published storage/API/mobile-browser parity only:
        independent N5.3 PDF/source-chart comparison, excluded raw metadata
        rows and broader desktop/theme/visual acceptance remain open.
      - [x] Re-run a **local-only pinned N5.3 PDF source comparison** against
        the current Army database in
        `test_pinned_n53_pdf_chart_source_differences`: 171/171 main chart
        rows aligned; Kobra Pistol (CC Mode) printed one Saving Roll versus
        Army two; Katyusha MRL printed unsigned `3` versus reviewed `+3`;
        14 auxiliary profiles include the seven already documented Mine/Dazer
        Silhouette conflicts. The test preserves both source values and skips
        where the ignored official PDF or optional PyMuPDF is unavailable.
      - [x] Verify player-visible **source-conflict presentation** in Chromium:
        Kobra's CC-only two-roll explanation and unresolved Anti-materiel
        disclosure at 1440/390 px, Katyusha's reviewed `+3` range values,
        and S0/S1 disclosure for all six named Mine objects at 390 px in
        `test_verify_weapon_source_cards_browser.py`. Do not infer a
        correction to the disputed S0/S1 object profiles.
        These checks do not resolve the remaining Weapon/prose inventory or
        independently review every printed Trait and object definition.
  - [ ] Add a generated Deployables profile reference from Weapon/Equipment
    metadata plus curated corrections: ARM/BTS/STR/S for the deployed object,
    originating item/rule, and reverse Unit/loadout uses. Keep deployed-object
    identity separate from the carrier and from catalog domain. Track the V5.3
    Armed Turret S2 detailed-profile versus S1 quick-reference conflict explicitly
    and do not silently choose the summary value without reviewed precedence.
    - [ ] Inventory deployed objects independently of their carriers. Reuse existing
      `facts.specialProfile` support where it fits; extend validated metadata/corrections only for
      confirmed gaps. Resolve or visibly retain the Armed Turret discrepancy with both citations.
      - [x] Reconcile the **14 auxiliary object profiles** already extracted
        from the N5.3 Weapon Chart with normal Chromium pages at 1440/390 px:
        11 Weapon-domain profiles plus three Equipment-domain profiles (Dazer,
        Deployable Repeater and FastPanda). Verify the Army-sourced
        ARM/BTS/STR/S values and mode identity against the published catalog
        API, without assigning chart S0/S1 precedence. Separately verify the
        curated Armed Turret Trooper profile, its S2/S1 source note and other
        printed-source caveat. The two browser cases in
        `test_verify_weapon_source_cards_browser.py` cover these existing
        reference surfaces, **not** distinct deployed-object identities.
      - [ ] Enumerate additional deployed objects beyond the 14 four-attribute
        chart entries, including Equipment and objects lacking a standard
        profile. Classify carried item, delivery mode and deployed object
        separately; identify source-backed object identities, provenance,
        unavailable values and unresolved conflicts before defining any
        canonical object/profile projection or reverse-use links.
        - [x] Add the reproducible, read-only
          `tools/audit_deployed_object_inventory.py` source inventory and
          `tests/test_audit_deployed_object_inventory.py` regression. It
          distinguishes the 14 printed profile identities by Army catalog
          and exact mode, exposes further populated source-profile rows,
          and retains cited curated examples: Armed Turret (distinct curated
          profile), Deployable Cover (nonstandard scenery) and Pitcher
          (delivery item, not the deployed Repeater). Candidate mentions
          are explicitly **not** inferred object identities; no source
          values or runtime relations are changed. The command and
          limitations are documented in `docs/testing.md`.
        - [ ] Review remaining source-only profiles and curated-text
          candidates against the exact N5.3 clauses and Army snapshot;
          record confirmed object identities, separate carriers/delivery
          paths, shared objects, nonstandard/missing attributes, and
          provenance in an accepted inventory before adding canonical
          object storage, browser entry points or reverse-use links.
          - [x] Pin the **single additional populated Army source profile**:
            Madtraps (Weapon source ID 150, ARM 0/BTS 0/STR 1/S 1).
            The N5.3 main chart (p. 187) and Perimeter/Boost rules (p. 69)
            are distinct from the 14 auxiliary object rows. Preserve its
            Weapon identity and Boost/PARA mechanics; do not infer a generic
            Mine/Perimeter equivalence.
          - [x] Add the audit-only reviewed delivery contract
            `config/validation/deployed-object-delivery-reviews.json`.
            Six pinned source paths distinguish Pitcher and Place Deployable
            routes to the shared Deployable Repeater profile; Disco Baller
            from its Disco Ball mode/object; two Drop Bears deployment
            modes; and Mine Dispenser's unresolved loadout-specific Mine
            subtype. The inventory now validates exact mode selectors,
            rule-text evidence, published N5.3 citation pages and rules
            owners without creating canonical object IDs or Unit carriers.
          - [ ] Classify remaining curated-text candidates, including
            nonstandard Scenery Elements and objects without Army profiles,
            with exact source evidence; then design and validate object
            identity, missing-data semantics and reverse-use presentation.
    - [ ] Expose deployed-object profiles and reverse uses through a usable reference entry point.
      Test objects supplied through Weapons and Equipment, shared objects/multiple carriers,
      missing/not-applicable values, and carrier-to-object navigation without inventing Unit identity.
  - **Completion:** players can inspect Weapon profiles and reach Ammunition/Traits and
    deployed-object statistics without selecting a carrier first; reverse uses preserve
    Army/loadout context. Missing in-scope facts must be exposed; dedicated comparison
    controls are not a separate release blocker.

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

These external corrections and rulings do **not** block 1.0 when the sources
and nature of each disagreement are clear to users. The 1.0 acceptance task
owns disclosure and accurate scope; this section owns later authoritative
resolution. Preserve reviewed source values and uncertainty while waiting.
An external correction can be incorporated earlier when available without
making its arrival a release prerequisite.

- [ ] Continue review of PARA Mine's intended Army footnote marker, Sepsitor
  Plus's missing Army `[*]`, and WildParrot's printed `Non-Lethal` against
  its E/M ammunition effect; Endgame's missing Army `Double Shot` is already
  shown with provenance. Both Sepsitor variants now link to the p. 73 rules,
  but the cause of the missing Army footnote remains unverified.

- [ ] **REA-045 — Official Armed Turret E/Mitter ruling:** Seek an
  applicable Corvus Belli erratum/FAQ or scoped confirmation of
  whether the Turret profile's one Saving Roll is intentional or
  the two-roll canonical E/Mitter applies. Do not infer a unique
  turret E/M rule or overwrite Army source data in the meantime.

- [ ] Seek authoritative publication corrections for AP Thunderbolt
  (both Wiki languages), AP+EXP CC Weapon (Spanish Wiki) and Stun Pistol
  (Spanish Wiki). Their current player-facing source notes retain
  the discrepancies; closing source-coverage review does not imply
  that Corvus Belli has resolved the underlying publication conflicts.

- [ ] Establish official precedence or corrections for the six Mine
  S0-versus-Army-S1 discrepancies and Dazer's cross-publication
  S0/S1 conflict before modifying profiles or publishing a definitive
  active-object geometry ruling. S0 itself remains a valid N5.3
  template (25 mm base, 3 mm high; general rules p. 18), also
  present in N5.1/N5.2.

- [ ] **REA-027 — Spanish Flash Pulse chart correction:** Seek an authoritative
  correction for Spanish Wiki Weapon Chart revisions 3987/3988, which list two
  PB rolls without State: Stunned. Both N5.3 PDF languages, pinned Army Weapon 72
  and the published reference retain one roll, Non-Lethal and Stunned.
  Keep the source disagreement visible; revision chronology alone is not a ruling.

- [ ] **REA-028 — Kobra Pistol CC Anti-materiel ruling:** Seek official
  clarification on the bilingual printed chart versus Army/current Wiki.
  Keep the disputed Trait separate from DA's supported two Saving Rolls
  (three on a Critical). BS and CC share Army source ID 221, so preserve exact
  mode scope. Wiki revisions 4021/4077/4082 retain historical evidence, not
  automatic precedence; do not infer Anti-materiel from DA.

- [ ] **REA-030 — Core versus ITS FAQ scope:** Seek clarification on whether
  the ITS scenario-element Marker-State answer and undeployed Ancillary Killed
  exception also apply to the four core N5.3 scenarios. Preserve the currently
  reviewed applicability, including the bounded Annihilation ruling; do not
  universalize ITS-only answers or change core missions while awaiting a ruling.
  Remaining in-scope FAQ coverage stays under the 1.0 FAQ task.

- [ ] **REA-034 — Official example correction:** Seek an official
  correction for the Level 3 Morat example granting Level 4's +1
  BS/CD in both printed languages. Do not infer that the example
  overrides the Fireteam Level table in the meantime.

- [ ] **REA-037 — Official Armed Turret Silhouette ruling:**
  Seek a scoped Corvus Belli correction or approved precedence
  decision for S2 detailed profiles versus S1 summary tables.
  Do not change the existing S2 value solely from the summary or
  treat its use as an authoritative resolution.

- [ ] **REA-038 — Non-Allied direct-target ruling:** Obtain a scoped
  current N5 ruling or explicit project decision on the *derived*
  interpretation for non-Allied Unconscious/Immobilized, Neutral,
  Hostile, and scenario-specific targets. Absence of an Allied gate
  in direct Skill text alone is not a verified universal permission.
  Do not change gameplay eligibility beyond confirmed clauses until
  this source decision is made.

- [ ] **REA-041 — Official Fireteam dice clarification:** Obtain an
  authoritative erratum or scoped ruling for Spanish N5.3 p. 140
  versus p. 75 and English pp. 75/136. Keep the contradiction
  explicit meanwhile; this external dependency does not block the
  locally reviewed 1.0 reference explanation.

- [ ] **REA-042 — Official Dodge modifier clarification:** Seek an
  authoritative correction for the PDF-versus-Wiki failed-PH
  condition. The unresolved external source disagreement is visible
  to players and is not a remaining 1.0 implementation blocker.

- [ ] Seek authoritative clarification of **Domination's 350-point SWC cross-language source conflict**.
  English N5.3 p. 151, English N5.2 p. 150
  and pinned English Wiki revision 3264 print 6 SWC; official Spanish N5.3
  p. 155 prints **7 CAP/SWC** for the same scenario and Army Points.
  Retain the published English-source 6 with a visible `needs-verification`
  issue until clarification; do not silently override one official edition.
  This specific discrepancy does not itself require changing the scenario
  model or reopening the completed 1.0 interaction-review ledger.

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
