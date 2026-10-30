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
- The 1.0 interaction-review ledger passes for 198 supporting identities with
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
    - [x] Reconcile the currently pinned source artifacts without fetching
      anything. The 2026-10-28 source-evidence run matched all **113/113**
      archived Wiki revisions, **88/88** English Wiki references across 74
      pages, and **2/2** Spanish references; both language snapshots matched
      their declared hashes. The pinned Army ZIP matched the current
      application database source identity. At that review, the N5.3 PDF had no
      maintained byte-hash pin; FAQ v0.1 still needs publication-scope review,
      and the available Reinforcements PDFs are N4 rather than a verified N5
      annex. This is source-identity evidence only, not gameplay or browser
      completeness. Full local report:
      `local/audits/gate-1.0/current-20261028/source-evidence.md`.
    - [x] **Data processing + Project infrastructure:** Pin the supplied
      English N5.3 PDF in both Core and Hacking source declarations.
      The 196-page input matches the reviewed Restrictions SHA-256;
      JSON/Markdown evidence now reports `declared-hash-match`.
      A guarded refresh synchronized the tracked v9 rules/publication
      pair, allowing only the two source-hash cells and corresponding
      publication provenance fingerprints to change. Rule rows,
      Restrictions and reviewed objects are unchanged. See
      [source identity](n5-source-history.md#reviewed-english-n53-core-pdf-identity)
      and [validation](testing.md#10-source-evidence-baseline).
    - [x] **Data processing + Project infrastructure:** Pin the remaining
      selected Spanish core, FAQ and duplicated ITS PDF declarations.
      All 12 declarations for six reviewed documents now have byte hashes;
      the paired v9 refresh changed only nine missing source hashes and
      corresponding publication fingerprints. The source-evidence report
      identifies supplied FAQ bytes by exact reviewed source ID, including
      historical v0.0. Publication-date/applicability review and the final
      input freeze remain separate gates. See
      [source identities](n5-source-history.md#remaining-reviewed-pdf-identities).
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
        It distinguishes
        **12 focused rechecks/clarifications**, **9 previously verified
        selected clauses**, **2 represented rules with local
        source-to-browser checks complete** (N53-02/05),
        **2 disclosed source conflicts** (N53-07/09) and
        **1 editorial item** (N53-01) across the 26 English bullets.
        Review four additional Spanish-only subjects, all 20 Army update
        subjects and the nine added FAQ rulings in their own source/scope
        boundaries. Current-rule ESX-01..04 checks have local acceptance;
        continue Army current-state coverage while preserving disclosed
        publisher conflicts and the ITS-only Ancillary ruling boundary.
        Finish release-matched database, derived-publication and browser
        acceptance without replacing the original audit's historical counts.
      - [x] **ARMY-02–04 source-pair chart publication:** Rechecked
        Indigo (1912/1926, PanOceania), Confessor (1913/1927,
        Military Orders) and Gui Feng/Yu Jing (1914/1928) against the
        exact `JSON 20260929-114335.zip` faction members, database
        and Unit API. For each source Unit the public reference preserves
        source name, ID, archive file/version, separate Spec-Ops
        (8 choices) or TEAM-OPS (10 choices) selection chart, four
        SpecBall choices, original option order and compound attributes.
        Chromium confirms all six Unit pages at 1440/390/320 px, with
        links, expected rows and no horizontal overflow. This is
        **selected current chart/identity coverage**, not a complete
        profile, availability, Fireteam or customization acceptance,
        nor evidence of a historical before/after Army change. The
        remaining full profiles and roster options for these three
        pairs are still included in the wider Army coverage gate.
      - [x] **ARMY-05–08 source-pair chart publication:** Rechecked
        Intel/Ariadna TEAM-OPS (1915/1929), Husam/Haqqislam TEAM-OPS
        (1916/1930), Vortex/Nomads TEAM-OPS (1917/1931), and
        Nexus-7/Combined Army TEAM-OPS (1918/1932) against the
        respective faction members of `JSON 20260929-114335.zip`,
        application database and public Unit API. All eight source
        identities, names, version/file provenance and ordered
        grouped attributes match. Each Spec-Ops entry has eight
        selection options and four SpecBall options; each TEAM-OPS
        entry has ten selection options and four SpecBall options.
        The shared Chromium test now passes 14 Unit pages across
        1440/390/320 px (42 page/viewport checks), including all
        seven previously and newly reviewed pairs. Intel's source
        includes separate Full Power/Battle Ravaged Enhanced
        Profiles; these source profile differences are **not**
        inferred to be configurable chart choices or accepted as
        completed roster/profile semantics.
      - [x] **ARMY-09–12 source-pair chart publication:** Rechecked
        Treitak/Morat TEAM-OPS (1919/1933), Shasvastii Corax/
        Shasvastii TEAM-OPS (1920/1934), Blur/Next Wave TEAM-OPS
        (1921/1935), and Chandra/ALEPH TEAM-OPS (1922/1936) against
        the pinned September 29 ZIP, current Army database and Unit
        API. All eight records preserve source names and IDs,
        grouped ordered choices (8 Spec-Ops or 10 TEAM-OPS entries),
        four SpecBall choices and exact file/version provenance.
        Treitak Spec-Ops occurs in both Combined Army and Morat
        source files, while Morat TEAM-OPS occurs only in Morat;
        the duplicate Treitak choice payload is identical and
        published under one logical identity. Chandra Spec-Ops
        and ALEPH TEAM-OPS both occur in ALEPH, Steel Phalanx and
        Operations members, all version `7.26246.159`, with
        identical choice payloads; do not attribute them only to
        the ALEPH main Army file or to the `.158` revision.
        Chromium now passes all 22 reviewed Unit pages at
        1440/390/320 px (66 page/viewport combinations).
        This is **current chart/publication coverage only**, not
        full roster, profiles, AVA, Fireteams, historical deltas
        or final hosted release acceptance.
      - [x] **ARMY-13–16 source-pair chart publication:** Rechecked
        Ŝtormo/O-12 TEAM-OPS (1923/1937), Kaizoku/JSA TEAM-OPS
        (1924/1938), Hatail/Tohaa TEAM-OPS (1908/1909), and
        Rumbler/NA2 TEAM-OPS (1925/1939) against the pinned
        September 29 source members, database and public Unit API.
        The final eight source identities preserve separate ordered
        selection charts (8 Spec-Ops, 10 TEAM-OPS entries), four
        SpecBall options, grouped attributes and version/file
        provenance. All source members use revision `7.26246.159`.
        Ŝtormo appears in O-12/Starmada/Torchlight Brigade, and
        Kaizoku in JSA/Shindenbutai/Ōban. Rumbler Spec-Ops is
        present in six NA2 source members (Non-Aligned Armies,
        Druze, Ikari, StarCo, Dahshat, White Company), but NA2
        TEAM-OPS is absent from the Non-Aligned Armies umbrella
        member and present in the other five. The duplicate
        chart payloads agree. Hatail's separate active/inactive
        Symbiont Armor profiles remain profile-level data,
        **not** chart choices. Chromium passes all 30 chart-bearing
        Unit pages at 1440/390/320 px (90 page/viewport checks).
        This completes **selected current chart/identity publication
        for ARMY-02–16**, not roster/profile/AVA/Fireteam acceptance
        or a pre/post Army change comparison.
      - [x] **ARMY-17–20 selected current-state publication:** The
        September 29 Army snapshot, application database and public
        pages agree on four distinct source cases:
        - **ARMY-17 / Ioann Bann #1940:** The O-12 and Starmada
          `7.26246.159` members preserve Dogface (AVA 1) and
          Dog-Warrior (transition profile AVA -1) forms. Both
          Fireteam charts permit a maximum-one, optional
          Varangian-labeled member in a Duo. Public Fireteam API
          and Chromium chart pages at 1440/390/320 px show the
          scoped membership. This is not approval of the entire
          sectorial chart or a pre-update membership delta.
        - **ARMY-18 / Najjarun #314:** Haqqislam, Hassassin
          Bahram and Qapu Khalqi `7.26246.158` source profiles
          each contain shared Equipment 238 (Deactivator). The
          three distinct native loadouts in each context are
          published with the shared Equipment reference linked
          on the ordinary Unit page; the separate option weapon
          ID 222 is not a substitute for Equipment 238.
        - **ARMY-19 / Sāchā #1874:** Selected Torchlight Brigade
          (`7.26246.159`), Kestrel Colonial Force, Invincible
          Army and USAriadna (`7.26246.158`) sources all have
          profile AVA 1. The four corresponding public Unit API
          contexts retain AVA 1; the ordinary Unit page loads
          responsively. A separate numeric-AVA Chromium check
          now verifies AVA 1 inside each of these four Army
          profile sections, keyboard expansion and Army-specific
          links at 1440/390/320 px (15 page/viewport checks).
          AVA remains contextual rather than appearing in the
          General profile.
        - **ARMY-20 / Racerbot #1905:** PanOceania and Haqqislam
          `7.26246.158` source profiles contain both native
          Equipment 246 and legacy Skill 266 (Bangbomb, extra
          310). The maintained public projection deduplicates
          these into one Equipment entry, not a duplicate
          Equipment/Skill listing. The ordinary Unit page links
          `/equipment/bangbomb` without a Skill duplicate.
        Source/API regressions and Chromium checks at 1440/390/
        320 px passed for all four selected Unit pages; the
        Ioann Fireteam pages also passed in O-12 and Starmada.
        These checks establish **selected present-state behavior**,
        not historical Army changes or final hosted acceptance.
      - [x] **Data processing + Web backend — ARMY-01 current
        source/chart parity:** Check all 58 pinned Army source
        contexts against the selected application charts and public
        API: 57 chart contexts (one empty grouping chart), 268 teams
        and 1,249 member rows preserve ordered types, limits,
        bounds, required choices, annotations and source hashes.
        Contracted Back-up sources 998/999 have identical charts
        and map to one application Army; this is not a missing chart.
        A local source-separated Chromium audit covers all 56
        playable charts at 1440/390/320 px (168 page/viewport
        cases), including visible limits, types, member bounds,
        required choices, equivalence labels and chart/team notes.
        Private evidence: `local/audits/army01-browser-20261029/`.
      - [x] **Web backend + Web frontend — explicit Wildcard
        exclusions:** The combined view now respects the reviewed
        `No Wildcards` observations on Invincible Army's Forward
        Fireteams and Next Wave's Team Achilles. Chromium checks
        both charts, the real Settings toggle and an all-excluded
        fallback at 1440/390/320 px; source-separated rows remain
        available. This does not validate general roster legality.
      - [x] **Web backend + Web frontend — ARMY-01 reference
        uncertainty and context:** The 11 unresolved rows have no
        exact Unit-slug definition in the pinned archive; ARJUNA's
        match exists only outside its Reinforcement Section, and
        KORSAN's three local loadouts have no FTO name. All 13
        affected rows now expose verification notices without
        inventing targets or options. Original member annotations
        are visible, including the three `--` / Spec-Ops rows.
        All 11 Reinforcement charts expose 46 parent contexts with
        independent limits; 45 lead to selectable charts, while the
        non-playable NA2 grouping stays unlinked. Nine contexts
        show a Section CORE type alongside parent CORE 0; this
        discrepancy remains explicit rather than merging pools.
        Source/API and Chromium tests cover the notices, real
        Wildcard toggle, parent navigation/back and empty/missing
        chart distinctions at 1440/390/320 px in light/dark themes.
      - [x] **Data processing + Web backend + Web frontend — ARMY-02–20
        native profile/loadout parity:** All 34 reviewed source
        Units now have pinned-source-to-API coverage for
        115 Army/Unit contexts, 323 ordered profiles and 961 ordered
        loadouts. Archive/member hashes and exact `.158`/`.159`
        revisions are verified; source Attributes, AVA, items/Extras,
        Orders, costs and disabled options remain contextual.
        Chromium checks all 34 ordinary Unit pages at 1440/390/320 px
        in light/dark themes (204 pages), including profile names/
        values, AVA, costs, linked items, keyboard expansion and
        overflow. Per-batch counts and exceptional source contexts
        (including Hatail's separate Symbiont profiles and the
        Rumbler/NA2 grouping distinction) are retained in
        [validation](testing.md#army-update-profile-acceptance).
        This completes native publication parity only; upgrade/
        profile-transition rules, roster/Fireteam legality, historical
        deltas and final hosted acceptance remain separate.
      - [x] **Data processing + Web frontend — ARMY-01 named annotation review:**
        Check 23 Triad/Triada, Varuna Div and Strategic Deployment
        source rows across Varuna, Shindenbutai, Tohaa and Deras Kaar.
        Varuna names match seven ORC and three Machinist local options;
        Shizoku's Skill-251 option is distinct from its two FTO options.
        Replace the blanket counts-as caption with neutral chart terms,
        retaining source text and the legacy API/storage fields.
        Source/API and 24 Chromium cases cover both Wildcard views,
        1440/390/320 px and both themes. This establishes source
        concordance and presentation, not automatic eligibility or
        current N5 Reinforcements authority. See
        [validation](testing.md#fireteam-annotation-applicability).
      - [ ] **ARMY-01 remaining semantics and release gates:** Retain the
        unresolved current N5 Reinforcements authority boundary;
        review further profile-specific annotations if the source
        inventory identifies them. The named annotation review above
        does not establish a general-purpose selector or legality model.
        ARMY-02–20 native profile/loadout publication parity is
        covered above; this does not validate roster legality or
        profile-transition/upgrade semantics. Do not infer
        a historical before/after delta without an earlier
        pinned Army snapshot. Final release-matched database,
        browser and CI acceptance remain separate gates.
      - [x] Recheck **Infinity Spec-Ops / Request SpecBall (N53-02)**
        against N5.3 p. 98 and the already recorded REA-040
        acceptance. The core request Skill, drop, selection, pickup,
        state/profile transition, timing, once-per-game and
        SpecBot procedures are already published, cross-linked
        to Combat Jump and separate from Speedball/Tacball. Source
        notes preserve the English misprint and ITS Season 18
        tournament boundary. A new public API/route regression
        confirms both Skills remain accessible; the historical
        2026-10-14 responsive browser run passed 24/24 checks.
        No gameplay-data edit was necessary.
      - [x] **N53-02 source-chart inventory:** The pinned September 29
        Army snapshot has source-defined `spectables` on 30 distinct
        Units: 15 Spec-Ops (source IDs 1908, 1912-1925) and 15
        TEAM-OPS (1909, 1926-1939). Each has a `table` choice list
        (8 Spec-Ops or 10 TEAM-OPS entries) and a separate four-entry
        `specball` list; an entry can group multiple `stat`,
        `skill`, `weapon`, or `equip` attributes. The same source
        payloads are preserved verbatim per Unit in
        `logical_unit_spectables`, as checked against
        `JSON 20260929-114335.zip` and the built Army database by
        `test_spec_ops_source_charts.py`. These are available source
        choices, **not** player-selected upgrades; duplicate faction
        occurrences do not create extra canonical Unit identities.
      - [x] **N53-02 read-only choice publication (1.0):** The Unit
        API now projects each exact `source_unit_id` separately from
        `logical_unit_spectables`; the ordinary Unit page publishes
        ordered Spec-Ops/TEAM-OPS and SpecBall options without
        flattening combined attributes. Catalog names and canonical
        routes are resolved from the current Army database, and
        unresolved extras retain their source IDs. Attribute `q`
        values and MOV components are shown explicitly as raw
        source notation, not guessed modifiers or final statistics.
        Each source record includes the source Unit ID and Army
        source-version/file provenance; the page links the core
        Spec-Ops and Request SpecBall Skills while distinguishing
        ITS TEAM-OPS applicability. API tests and focused Chromium
        checks at 1440/390 px cover the source options, links, and
        responsive overflow. Final release-matched hosted browser
        acceptance remains open, as does the post-1.0 interactive
        list/session configurator and any future review of the
        numeric option semantics.
      - [x] **N53-05 Guts Roll attack-position geometry:** Rechecked
        official N5.3 p. 38 against `rule:guts-roll`, including the
        positions from which attackers actually attacked and the
        Prone fallback when already outside relevant LoF/areas.
        The fresh curated export and tracked `rules.db` both publish
        the rule through `/api/rules/guts-roll`. Focused Chromium
        acceptance passes at 1440, 390 and 320 px for the ordinary
        `/rules/guts-roll` page, including clarification, Prone
        cross-link, p. 38 citation, and zero horizontal overflow.
        No gameplay-data change was required; this closes the
        bounded local source-to-browser review, **not** hosted
        release-candidate acceptance or the broader Guts interaction
        completeness gate.
      - [x] Recheck the **Impetuous/Prone update (N53-13)** against N5.3
        p. 97. Preserve the Impetuous-Phase Move/Jump/Climb movement-end rule
        separately from the additional end-of-Order Prone restriction, and cite
        the printed page on `skill:impetuous`. A focused curated-data regression
        guards both clauses. This closes one reviewed changelog item, not the
        remaining N5.3 rules/Army review; rebuild release-matched rules data
        before final browser acceptance.
      - [x] Reconcile the **Null Label enumeration (N53-24)** against
        N5.3 p. 174. The maintained `term:null-state` summary links
        the five source-named States: Dead, Disconnected, Possessed,
        Sepsitorized and Unconscious. A fresh rules export and Glossary
        projection regression verify the list and source citation. Only the
        two generic-word reviewed-text fingerprints affected by the summary
        extension were refreshed. The tracked rules database must be rebuilt
        before final player-facing browser acceptance.
      - [x] Reconcile the player-facing **Berserk/Prone exception (N53-03)**
        against General Movement Rules, N5.3 p. 29. Both `state:prone`
        and `skill:berserk` now explain that Berserk's Movement Label does
        not permit voluntary Prone entry/exit at the start or end of movement.
        This does not impose an unsupported general ban on Berserk while
        Prone. A focused curated regression guards the source citation and
        the two owner cards. The shorter Prone summary at N5.3 p. 169
        still omits Berserk; retain this source-internal discrepancy as
        documented. Release-matched rules data and browser acceptance
        remain separate requirements.
      - [x] Recheck **Protheion (N53-16)** against N5.3 p. 109 and FAQ
        v0.1 p. 2: `skill:protheion` already specifies that a printed
        negative MOD affects the enemy in a Face to Face Roll and that
        additional failed Saving Rolls after Dead State grant no benefit.
        Existing `test_protheion_overkill_and_opponent_mod_are_published`
        covers both; no rules-data edit required.
      - [x] Recheck **Minelayer (N53-14)** against N5.3 p. 102:
        `skill:minelayer` already includes Deployable Weapons **or
        Equipment**, the enemy/Marker exclusion in the Trigger Area,
        and the entire ZoC for Perimeter items. Existing REA-023
        tests cover these; no rules-data edit required.
      - [x] Recheck **Firewall (N53-06)** against N5.3 p. 55 and FAQ
        v0.1 p. 1: `equipment:firewall` is already represented as
        Automatic Equipment with its Device-enabled restriction and
        appropriate provenance; no rules-data edit required.
      - [x] Clarify the **PARA CC Weapon modifier (N53-10)** using
        N5.3 p. 75 and PARA Ammunition p. 65. The common
        `rule:modifiers-explained` and `weapon:para-cc-weapon`
        now distinguish the opponent's profile-listed negative MOD
        during Face to Face Rolls from the separate PH-6 Saving Roll
        after a hit. A focused rules-export regression guards both
        citations and mechanics; this does not change the Ammunition
        resolution or weapon-profile source values. Release-matched
        browser acceptance remains pending.
      - [x] Recheck **Cyberplug profiles (N53-15)** against N5.3
        p. 107 and its p. 108 examples: the maintained
        `rule:peripheral-type:cyberplug` already specifies profile
        choice at each Order/ARO start, no more than one Connected
        Cyberplug, Controller-owned Doctor/Engineer Rolls on one allied
        target per Order, and Autonomous fallback rather than Disconnected.
        Strengthen the existing curated regression; no gameplay-data
        edit was required.
      - [x] Clarify **Peripheral/Fireteam Integrity (N53-21)** against
        N5.3 pp. 107 and 134. `rule:fireteam-general` now links the
        narrow `rule:peripheral-type:ancillary` exception: its Controller
        may remain in a Fireteam while Ancillary is undeployed,
        Disconnected, or Null; placement or recovery ends the exception.
        Distinguish a departing non-Leader from a departing Leader,
        which cancels the entire team. The Ancillary card links back
        and explicitly excludes Cyberplug Controllers. This does not
        expand Ancillary-specific scenario rulings beyond their source
        scope. A fresh rules export and scoped regressions pass; final
        release-matched browser acceptance remains open.
      - [x] Reconcile **Deployable Cover (N53-19)** against N5.3
        p. 122. The maintained `equipment:deployable-cover` already
        lists Disposable (2), Indiscriminate, Perimeter, S3, placement
        wholly within ZoC, both variants, and the Vitroferro
        ARM/BTS-plus-MOD cap of 12 before PS; the earlier audit's
        missing-property finding is stale. Added the omitted
        Deactivator-removal and taller-than-S3 movement exceptions
        to the owner card, with a focused regression. No unsupported
        ARM/BTS/STR values were inferred for the Scenery Element.
        Release-matched browser acceptance remains pending.
      - [x] Reconcile **Camouflaged ARO declarations (N53-22)** against
        N5.3 pp. 157-158. The four permitted Skills (Discover, Dodge,
        Look Out!, Reset), delayed response and whole-Order revelation
        were already covered in `state:camouflaged` clarifications.
        The declaration-only restriction is now explicit in the State's
        operative restrictions, with a separate explanation of the
        delayed-ARO window and its lost-reaction condition. Existing
        reviewed text remains intact; the catalog regression verifies
        the permitted list and subsequent reveal. Final release-matched
        browser acceptance remains open.
      - [x] **Spanish-only ESX-01 / Stealth alignment:** Current
        English N5.3 p. 112 and Spanish N5.3 p. 114 agree on
        Cautious Movement/Idle/Basic Short Movement ARO scope, the
        Combat Instinct, Sixth Sense and Deployable exclusions, and
        the restricted Silhouette-contact reaction choices. Existing
        `skill:stealth` and counter-Skill references already cover
        the broader effects and FAQ v0.1 mixed activation; explicitly
        list CC Attack, Dodge, Reset and Engaged-usable Skills in
        the owner card for discoverability, without granting a new
        ARO during protected movement. Current PDF and curated
        regressions plus Chromium at 1440/390/320 px verify the
        scoped change. **Historical Spanish N5.2 comparison remains
        unprovable** without that exact earlier PDF; this closes
        current-rule publication, not the historical delta or final
        hosted release acceptance.
      - [x] **Spanish-only ESX-02 / Jet Propulsion wording:** English
        N5.2 p. 112 allowed direction and heading changes before
        landing; English N5.3 p. 113 expressly permits repeating
        them freely during the airborne trajectory. Current Spanish
        N5.3 pp. 116-117 retains less explicit before-landing
        wording, but its illustrated example describes changing the
        path freely in the air. The `skill:super-jump` reference now
        states the repeated-direction privilege **only for the named
        Jet Propulsion variant**, while preserving exact-trajectory
        declaration, ordinary Jump distance, the Short Skill
        bracket-distance condition and one-Basic-Short-Jump-per-Order
        restriction. A bilingual source-context note and citation
        disclose the difference. Pinned English N5.2/N5.3 and
        current Spanish PDF regressions, curated tests and Chromium
        at 1440/390/320 px passed. Historical **Spanish** N5.2
        before/after verification remains unavailable without its
        exact PDF; hosted release acceptance remains open.
      - [x] **Spanish-only ESX-03 / Multispectral Visor L3:** Current
        English N5.3 p. 125 and Spanish N5.3 p. 131 agree that only
        in the user's Active Turn may L3 make a BS Attack against a
        Camouflaged Marker in LoF without previous Discover, while
        applying the Marker's Mimetism. English p. 125 retains normal
        Camouflaged State cancellation; Spanish p. 131 additionally
        says that performing the attack does not reveal the target
        to the rest of the army. The maintained
        `equipment:multispectral-visor` now separates the user's
        targeting permission from automatic global revelation and
        the cancellation triggers (notably a required Saving Roll),
        referencing Camouflaged State pp. 158/163. This does **not**
        permit Reactive-Turn attacks against unrevealed Markers or
        immunity from cancellation when its conditions apply.
        Pinned bilingual source checks, curated regression and
        Chromium at 1440/390/320 px passed. Historical Spanish
        N5.2 before/after evidence and final hosted release
        acceptance remain open.
      - [x] **Spanish-only ESX-04 / AP+T2 CC Anti-materiel:** The
        English N5.3 p. 177 and Spanish N5.3 p. 184 CC Weapon
        charts both print PS 8, B1, AP+T2, one ARM/2 Saving
        Roll and the Anti-materiel and CC Traits. The public
        `ap-t2-cc-weapon` profile and `weapon-property:ap-t2`
        already preserve those values and link both component
        Ammunition rules; no additional saving roll or separate
        attack mode is implied. Pinned bilingual PDF and public
        API regressions passed, as did ordinary Chromium weapon
        presentation at 1440/390/320 px, including Anti-materiel
        and the AP/T2 links. No production-data change was
        necessary. The exact earlier Spanish N5.2 PDF is still
        missing, so historical Spanish before/after evidence
        and final hosted release acceptance remain open.
      - [x] Verify **N5.3 new weapon profiles (N53-25)** against the
        English Weapon Chart p. 180 and Army metadata. Source ID 225,
        Breaker Marksman Rifle, is already published through the
        reviewed metadata-only Weapon mechanism in the current
        application database: public numeric ID and slug resolve to
        the same one-mode weapon with the printed BTS/2, PS 7,
        Burst 3, range and Breaker property. Its source signature
        is pinned and checked before publication; the new API
        regression additionally rejects an invented Breaker Sniper
        Rifle alias. AP Red Fury (229) and AP Thunderbolt (230)
        remain source-verified from the prior reconciliation.
        No production-data change was needed on this checkout.
        Browser acceptance against the final release build remains
        a separate requirement.
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
      - [x] Inventory the FAQ v0.1 **ITS-section applicability boundary**
        against the maintained 29-ruling collection. Of ten source
        questions in the printed ITS section, two are now published with
        scoped applicability: undeployed Ancillary/Killed objectives for
        Annihilation, and the scenario-element/Marker-State restriction
        for core Supplies (corroborated by N5.3 p. 153). Eight ITS-only
        questions remain without standalone curated FAQ rulings and are
        deferred from the four core-scenario baseline. The existing
        Ancillary ruling was compared with the Core N5.3 Killing
        clauses (Annihilation p. 150 and Firefight p. 155). Both share
        the same Killing wording, but FAQ v0.1 EN/ES p. 4 places the
        exception under ITS without naming either Core mission.
        Retain the existing Annihilation-only InfinityDB selection; the
        FAQ does not explicitly assign that answer to a Core mission.
        The follow-up review also checked the generic Peripheral rules
        (N5.3 pp. 106–108), which do not establish a Firefight scoring
        exception. **Do not extend to Firefight** on shared Killing text
        alone; reopen only with scenario-specific supporting evidence
        and a reviewed applicability change. The cross-scenario runtime
        regression prevents implicit inheritance through the shared
        Killing Rule.
        See [FAQ v0.1 applicability inventory](faq-v0.1-scope-inventory.md).
        This does not certify full FAQ or browser coverage; keep scenario
        applicability explicit before further curation.
      - [x] Pin and independently verify the available FAQ source PDFs.
        The audit-only inventory records SHA-256, source identity, version,
        file-page count and local path for English v0.0 and English/Spanish
        v0.1. All **3/3** local bytes matched on 2026-10-28, and the
        focused pytest cases passed. Clean CI skips missing ignored PDF
        bytes rather than treating the declared hashes as verification.
        This does not establish exact original PDF publication dates,
        final 1.0 input freezing, or broader ITS applicability.
      - [x] Correct the Supplies carrier FAQ's original source to English
        v0.0 printed p. 2. It was incorrectly recorded as v0.1-origin;
        English/Spanish v0.1 p. 3 remains the selected current citation.
        The 29 published rulings now comprise 20 v0.0-origin and nine
        v0.1-origin entries. Its Supplies-only effective scope is unchanged.
      - [x] Reconcile the **28 English FAQ v0.0 question identities**
        against the current v0.1 inventory, pinning the original
        printed page of every carried-forward ruling and all eight
        deferred ITS questions. Twenty reviewed published questions
        originate in v0.0 (ten on p. 1, ten on p. 2), alongside eight
        ITS-only deferred questions (two on p. 2, six on p. 3).
        The nine remaining v0.1 questions are new. The independent
        inventory and FAQ regression now prevent unreviewed historical
        source/page reclassification. This closes question provenance,
        not gameplay applicability, exact publication dates or complete
        browser reachability.
      - [x] Validate **ordinary browser FAQ selection** for the new
        Supplies ruling at 1440px and 390px using
        `tests/test_verify_scenario_faq_browser.py`. The Chromium
        acceptance checks source-linked Supplies clarification,
        Annihilation's existing Ancillary clarification, and no
        FAQ section in Domination or Firefight. It reuses the same
        page across navigations to catch stale FAQ leakage.
        `test_scenario_api.py` also pins the Supplies selection.
        This is bounded scenario-page delivery, not a claim of full
        FAQ browser or final release completeness.
  - [ ] Reconcile `data/curated/rules-interactions/reviews.json` and `catalog-scope.json` with the
    pinned input set. Historical review/defer release labels are evidence, not the active roadmap.
    A preliminary audit of the current tracked database pair found that the maintained primary
    scope still targets 0.7.0 and omits the published `activate-disco-ball`, `request-specball`,
    and `firewall` identities, whose reviews target 1.0.0. The independent 1.0.0 supporting-
    identity slice passes 111/111, but does not expand or certify that primary catalog: the
    maintained primary denominator remains 182 items at 0.7.0. A refresh against the current
    database pair exposes the three omitted primary identities and cannot be treated as a
    release check until its target and review coverage are reconciled. Commlink remains under a
    post-0.7.0 scope exception in that historical ledger. Current evidence identifies its
    Reinforcements Wiki source as N4-only. N5.3 p. 6 mentions games with Reinforcements;
    ITS Season 18 (version 2026.09.01, p. 27) explicitly permits the Reinforcements
    Extra in tournaments and refers players to the Reinforcements Annex. This confirms
    current optional-mode applicability, but does not identify an N5 edition of the Annex
    or certify unchanged N4 procedures. Keep Commlink unresolved for 1.0 rather than
    importing N4 rules or treating the old exception as a current scope decision.
    Reconcile the 1.0 primary review baseline and Commlink against pinned inputs,
    preserving historical review dates and labels as provenance.
    - [x] Add a distinct `--require-primary-release` audit guard. The existing
      `--require-release 1.0.0` validates the 1.0 supporting slice while the
      primary denominator still targets 0.7.0. The new strict guard fails
      rather than misreporting that historical scope as a completed 1.0
      primary review; it also fails on pending primary items. It is not
      added to CI's currently passing 1.0 supporting gate until the
      maintained primary catalog and Commlink scope are reconciled.
    - [x] Add non-mutating `--report-catalog-scope-drift` to the existing
      rules-interaction auditor, using the paired Army/rules databases.
      A pinned regression finds only `skill:activate-disco-ball`,
      `skill:request-specball`, and `equipment:firewall` added versus
      the 0.7.0 primary scope; there are no removed or renamed entries.
      All three have reviewed N5.3 definitions and 1.0 review records
      dated October 13–14. The report preserves the old Commlink exception
      without endorsing it as a current N5 scope decision. Inspect with:
      `python -m tools.audit_rules_interactions --report-catalog-scope-drift --database data/generated/infinity.db --rules-database data/generated/rules.db`.
      This identifies the bounded delta; it does not close the 1.0
      primary baseline or settle the missing verified N5 annex for Commlink.
    - [x] Establish a **separate, non-release-ready 1.0 primary catalog
      candidate** in `data/curated/rules-interactions/catalog-scope-1.0.0.json`.
      The candidate matches the pinned public Skill/Equipment/Trait/State
      catalogs (97/31/33/24 entries), includes the three reviewed new
      identities, and retains existing historical review dates and target
      labels rather than rewriting them as 1.0 reviews. It does not carry
      forward the old Commlink release exception. The bounded candidate
      audit reports **184/185 primary identities complete, Commlink pending**,
      and **195 supporting identities**. The strict candidate gate
      `python -m tools.audit_rules_interactions --catalog-scope data/curated/rules-interactions/catalog-scope-1.0.0.json --require-primary-release 1.0.0`
      fails and names Commlink as intended. The unchanged 0.7.0 scope and
      generated historical checklist remain the default CI baseline.
      This candidate is review-tracking evidence, **not** proof that earlier
      curated meanings remain accurate for the final 1.0 source set.
      Verify an N5-applicable Reinforcements annex or explicitly decide the
      1.0 applicability boundary before making this candidate the active
      release gate.
    - [x] Verify **current Reinforcements Extra applicability** without
      inferring N5 mechanics. The local official ITS Season 18 PDF
      (`data/pdf/its/Its-rules-season-18-en.pdf`, version 2026.09.01,
      p. 27) explicitly offers Reinforcements and refers to the Annex.
      The pinned N4 annex and archived N4-labeled Wiki remain historical
      procedure evidence only. Subsequent official N5-era Army updates
      (March 18, October 2 and October 15, 2025) confirm maintained
      Reinforcement profiles, **not** their annex procedure or Commlink
      effects. See `docs/n5-source-history.md` and `docs/rules-semantics.md`.
      **Still open:** identify an official
      N5-applicable Annex revision or explicit adoption ruling before
      curating Commlink/Request Reinforcements as N5 and activating the
      strict 1.0 primary release gate.
    - [x] **Data processing + Project infrastructure:** Correct historical
      Reinforcements source availability in the existing evidence auditor.
      A maintained inventory verifies the two reviewed N4 PDF fingerprints;
      missing files stay unverified and changed bytes fail closed. The
      version-3 JSON/Markdown report separates historical availability from
      unresolved N5 authority. Both local hashes match; this does not close
      Commlink, Request Reinforcements or the strict 1.0 primary gate.
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
  - [x] Generate a current-core **Orders/AROs declaration matrix** from
    composed Skill rules and Army-backed Hacking Program declarations, published
    at `/orders-aros` and `/api/orders-aros`. Its 57 category occurrences
    match the independently reviewed N5.3 p. 191 chart exactly, across 42
    existing canonical action owners. The page links to owning Skills, Equipment
    or Hacking Programs and explicitly excludes live action-legality evaluation.
    - [x] Reuse current Skill, Equipment and normalized Hacking Program
      declaration categories; keep source-only BS/CC replacement variants,
      Automatic and Deployment Skills, scenario-only and phase-scoped actions
      outside the unscoped core projection. The p. 191 Equipment-labelled
      Activate Disco Ball remains a canonical Skill with its distinct source
      Type.
    - [x] Validate the full pinned chart against generated runtime rows, including
      declaration category, source Type, owning identity and public route. Do not
      infer that an absent action is prohibited or allow a source table row to
      create a new Weapon/Equipment or Army carrier.
    - [x] Run real local Chromium acceptance at 1440, 1024, 390 and 320 px:
      verify all 57 rows and per-category counts, Equipment/Hacking search
      behavior, empty states, three public detail destinations, JS errors and
      page-level overflow. Keep the 17-destination desktop/mobile sidebar
      contract synchronized. Tests:
      `tests/test_verify_orders_aros_browser.py` and
      `tests/test_verify_sidebar_density_browser.py`.
    - [x] Replace the three source-reviewed Equipment Short Skill exceptions
      (Deactivator, GizmoKit, MediKit) with first-class
      `facts.typeIds: ["short-skill"]` in their current N5.3 definitions
      and direct p. 191 citations. Validate optional Equipment typeIds
      (no implicit classification), rebuild and promote the paired
      `data/generated/rules.db` and `deployed-objects.json` fingerprints
      with recovery backups. Confirm that 57/57 source rows, browser
      behavior, and all 17 deployed-object identities/deliveries remain
      unchanged. The matrix now discovers Equipment declaration types
      from rules.db rather than three hard-coded IDs. Retain the
      independent PDF chart audit as the drift gate.
    - [x] Add a separate, opt-in **current core-scenario action** panel to
      `/orders-aros`, selected by `?scenario=<core-slug>`. Derive Skills
      from `RulesDatabase.scenario_reference()` and verified current
      `n5-core` publication membership, never from Unit profiles or an
      extra maintained declaration table. Domination supplies **Hack Consoles**
      (Short Skill, N5.3 p. 151); Supplies supplies **Pick Up Supply Boxes**
      (Short Skill, p. 153). Annihilation and Firefight have no additional
      declared Skills. Render separate source-cited cards/links into each
      scenario's real Skill reference, with URL persistence, browser acceptance
      and error recovery; the unscoped **57/57** matrix stays identical.
      Unsupported and ITS-only scenario selections fail closed.
    - [ ] Add explicitly **phase-scoped** annex actions (not normal
      Short/Long/ARO categories), notably Request Reinforcements, when the
      separately versioned Reinforcements source and typed annex records
      exist. ITS/season-only actions remain outside the 1.0 core selection
      and should require explicit season/revision context in later work.
  - [ ] Deepen the existing first-class Ammunition model with explicit typed
    relationships. Preserve the eleven published base Ammunition identities, distinguish
    source-defined combined forms, preserve component relationships for Combined
    Ammunition, and keep Ammunition composition separate from Combined Saving Roll
    notation. Link State, Attribute, and Saving-Roll effects explicitly instead of
    deriving them from display names.
    - [ ] Review other component-level Immunities, BTS-based variants and
      weapon-specific exceptions. Do not generalize from the reviewed examples
      or the name-scoped Viral Vulnerability case.
      - [x] Promote N5.3 p. 96 **printed Example 3** as a distinct typed
        `reviewedSavingRollCases` record: Immunity (Enhanced) against the
        Plasma Rifle does not remove its separate ARM and BTS Saving Rolls.
        Validate the exact pinned PDF, Normal Ammunition, published Army
        Combined Saving Roll profile and Immunity API; render the sixth
        source-labelled interaction without adding an attack evaluator.
        Rebuild/promote `rules.db` with synchronized deployed-object
        publication and recovery backups; all 17 objects stay unchanged.
        Chromium acceptance at 1440/390/320 px confirms the sixth
        source-labelled case, links and layout.
      - [x] Review the exact N5.3 **E/M CC Weapon** instance of BTS-based
        Combined Ammunition. The printed N+E/M example (p. 67), Immunity
        (BTS) and Comms limitation (pp. 95–96), and CC Weapon Chart (p. 177)
        support a *rule-derived*, non-Comms-only case: two BTS/2 rolls
        (three on Critical) become one unmodified BTS roll (two on
        Critical unless Immunity (Critical) also applies). Require the
        exact Weapon/source Ammunition ID, preserve the two Army Saving
        Rolls and component identity, and never project an Immunity
        result into the Weapon API. Validate the closed schema, pinned
        source and browser at 1440/390/320 px. Publish the synchronized
        rules DB/deployed-object pair with rollback backup.
      - [x] Add the **standalone E/Mitter** case under source weapon
        ID 25 and E/M source ID 14 (N5.3 pp. 64, 95–96, 186).
        Its non-Comms two BTS/2 rolls (three on Critical) become
        one unmodified BTS Saving Roll (two on Critical without
        Immunity (Critical)); **Non-Lethal survives** and E/M State
        effects do not apply. Keep the Armed Turret E/Mitter
        discrepancy (source weapon 226, one imported roll) explicitly
        excluded and unchanged. Verify source, Army and API,
        fail-closed validation mutations, eight-card renderer and
        1440/390/320 px browser acceptance; promote the coordinated
        rules/publication pair with a recovery backup.
      - [x] Review **Silenced Pistol** as a source-bounded partial
        component-Immunity case: source Ammunition ID 30 `AP+Shock`,
        one BTS/2 Saving Roll and the separate Silent (-6) Trait
        (N5.3 pp. 63, 65, 67, 95–96, 175, 182).
        With Immunity (AP), only AP is ignored: one full-BTS roll
        remains (two for a Critical), Shock retains its conditional
        VITA=1 failed-save direct-Dead effect, and Silent remains
        independently conditional. Restrict the rule-derived
        result to `weapon:silenced-pistol`; do not rewrite Army
        source values or infer a general component evaluator.
        Promote rules/publication together with a recovery backup
        and preserve all 17 reviewed deployed objects.
      - [x] Add exact **AP+T2 CC Weapon** partial-component
        Immunity (AP) reference (Army Ammunition source ID 40).
        The pinned N5.3 pp. 63, 67, 95–96 and 177 establish
        one ARM/2 roll for the hit (two on a Critical), becoming
        one full-ARM roll (two on a Critical) when only AP is
        ignored. Preserve T2's distinct failed-roll outcomes:
        **2 Wounds** from the hit roll versus **1 Wound** from
        the extra Critical roll; identify each die before
        rolling. Anti-materiel remains a separate Weapon Trait.
        Restrict applicability to the non-Comms CC Weapon;
        do not rewrite source profiles or infer target outcomes.
        Gate the case with exact schema, source/Army/API tests,
        1440/390/320 Chromium and coordinated rules/publication
        promotion with recovery backups.
      - [ ] Review other BTS-component Immunity outcomes using exact
        non-Comms Weapon/combined-Ammunition evidence. The four
        reviewed BTS-based examples do not authorize generic E/M,
        Comms Attack or arbitrary combined-effect adjudication.
    - [ ] Review the remaining fact/relation completeness, including combined-effect
      precedence, full Critical interactions, affected Attributes, visibility Face
      to Face outcomes, conditional State cross-links, and comparison-view
      consumption. Do not infer executable mechanics from reviewed reference facts.
    - [ ] Validate every published base identity and reviewed combined form against the pinned
      source; prove that weapon links, Ammunition detail, and later comparison views consume the
      same facts without conflating composition with roll notation.
      - [x] Add full cross-domain publication parity for all 11 canonical base
        identities and 16 exact Army source Ammunition ID/name pairs (11 base,
        five combined). The regression verifies the current metadata lookup,
        canonical rules facts and citations, at least one real imported/public
        Weapon profile per source identity, ordered component routes and
        shared-rule summaries, and preservation of source Saving Roll fields.
        Exercise all five combined forms through the public Weapon API and
        independently pin N5.3 p. 67's printed AP+DA, AP+Exp and N+E/M
        examples (including the distinct Combined Saving Roll discussion).
        Source-defined AP+Shock and AP+T2 remain grounded in exact Army
        metadata, not misattributed to the p. 67 examples.
      - [ ] Review any remaining component-level precedence, exceptions, and
        future comparison-view consumers independently. Identity/transport
        parity is not an executable attack or Critical resolution model.
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
    - [x] Independently verify current **source references** without promoting
      historical procedures: N5.3 p. 6 mentions Reinforcements as a game mode;
      ITS Season 18 v2026.09.01 p. 27 identifies a current optional Extra
      and points to an unversioned Reinforcements Annex. Both official
      current PDFs and the English/Spanish **N4 annex** PDFs are byte-pinned,
      with Commlink (Automatic Skill) and Request Reinforcements (Tactical
      Phase step) checked as **N4-only** evidence. The source gate in
      `config/validation/reinforcements-n5-applicability-review.json`
      rejects changes that turn historical text into current N5 authority.
      Current `rules.db` and the 57-row N5 Orders/AROs matrix retain
      neither unverified annex action.
    - [ ] **Source blocker:** Identify an authoritative N5-specific
      Reinforcements Annex revision or an explicit official adoption
      ruling establishing which historical N4 procedures remain applicable.
      Archive/pin the exact approved source, effective version/date and
      publication scope before authoring current N5 Commlink or Request
      Reinforcements. A reference to an unversioned Annex alone does not
      authorize silently reusing N4 rules.
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
  - [x] Verify Domination's 350-point SWC disclosure on the final candidate.
    Pinned official English N5.3 p. 151 and N5.2 p. 150 show **6 SWC**;
    pinned official Spanish N5.3 p. 155 shows **7 CAP/SWC**. Retain 6 as
    the English-source publication value and keep `needs-verification`
    rather than asserting either source is an erratum. The normal setup
    SWC row now links to the full, sourced cross-language discrepancy
    note. Browser acceptance at 1440/390px verifies the 350-point value,
    direct keyboard-accessible note link, and non-leakage to other game
    sizes and core scenarios. Seeking an authoritative clarification
    remains an independent future task below, not a 1.0 blocker.
  - [x] **Data processing + Web frontend:** Correct **Domination
    center-placement measurements** before 1.0. Keep all four source-defined
    scoring Quadrants intact, but replace their on-map area-size captions
    with dashed rulers from each Console **center** to its nearest horizontal
    and vertical table edges. Derived nearest-edge distances from the pinned
    N5.3 map (p. 152) are 6/12 in (150 points), 8/18 in (200–250),
    and 12/18 in (300–400), following the normal in/cm conversion.
    Render the same measured coordinates in standalone and embedded SVG
    and explain that shaded Quadrants are scoring regions, not Console
    marker footprints. The projection activates only for the verified
    four-Quadrant/four-Console layout; no curated geometry or rules
    database rebuild is needed. SVG, API and desktop/mobile Chromium
    acceptance cover all three table configurations and both units.
    See [the map projection contract](data-model.md#current-scenario-foundation).
  - [x] **Data processing + Web frontend:** Show **physical scenario
    marker diameters** alongside the normal setup map. The read-only
    `placement.marker_dimensions` projection derives type and count from
    each selected geometry, using the existing canonical 40 mm Console
    and 25 mm Supply Box footprints. The cited source is the official,
    pinned ITS Season 18 v2026.09.01 token-diameter chart (p. 17);
    N5.3 core pp. 151 and 153 establish the marker types/placement.
    This uses an ITS physical-token source, **not** ITS scenario rules.
    The browser explicitly distinguishes mm footprint from scoring
    areas, map drawing scale and inch/cm game distances.
    All six supported Army Points settings, all four Core scenarios,
    standalone SVGs in both units, and desktop/mobile Chromium display
    are covered; Annihilation and Firefight correctly omit marker rows.
    See [the marker projection contract](data-model.md#current-scenario-foundation).
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
  - [x] Pin the **FAQ v0.1 question-level source inventory**: 29 reviewed
    rulings (27 general-section, two ITS-section with separately verified
    Core scenario scope) and eight deferred ITS-only questions. The
    [source triage](faq-v0.1-scope-inventory.md) remains the narrative
    disposition; the machine-readable audit manifest and regression
    verify printed page/identity, provenance, selected citation, date and
    rules-revision gates, and scenario selection against a fresh rules
    database. This is the v0.1 question inventory only, **not** full
    historical FAQ/errata completeness or ITS applicability certification.
  - [x] Reconcile all **29 in-scope current FAQ v0.1 rulings** against the
    pinned English and Spanish FAQ PDFs and question-level source inventory.
    Retain question/answer meaning, 20 carried-forward v0.0 source origins,
    nine new v0.1 origins, source-specific pages, topic references and
    applicability. The eight remaining ITS-only Q&As are explicitly
    inventoried and deferred, not promoted to generic core rules.
    - [x] Repair **five corrupted possessives in four reviewed FAQ
      questions/answers** and the stray replacement `?` in the English
      historical v0.0 source title. Verified against the pinned English
      FAQ source pages; a regression now checks all 29 current FAQ
      question/answer strings for replacement question marks and pins
      the five restored phrases. No meaning, source selection, topic
      identity, citation or applicability changed. This is a bounded
      text-fidelity correction, not the remaining full wording audit.
    - [x] Correct adjacent N5.3 **core-rule copy encoding** discovered in
      the FAQ review: two possessives in `trait:continuous-damage`
      Immunity clarifications and one in `skill:request-speedball`'s
      Controlled Jump exclusion example, plus the Spanish *Daño
      Continuo* title in testing evidence. Targeted curated/composed
      rules tests protect the restored text. No source authority,
      rule behavior, links or effective-date scopes changed.
    - [x] Compare the **20 published v0.0-origin answers** against pinned
      English FAQ v0.0 and v0.1 PDFs, checking their meaning and exceptions
      did not change across those source versions. Pin independent
      answer-semantic anchors in the audit-only question inventory and
      assert each carried-forward current answer retains them, alongside
      original and selected printed-page references. Focused test passed
      on 2026-10-29. This does not grant historical runtime selection,
      independently date either PDF, or certify the eight deferred
      ITS-only rulings or all Spanish translations.
    - [x] Reconcile the **nine v0.1-origin current FAQ answers** with
      pinned English and Spanish v0.1 PDFs. An independent audit-only
      manifest pins answer conditions and each language's printed
      page; the focused test checks those nine answers, selected
      English source, bilingual citations, provenance and scoped
      applicability. Preserve the real Haris numerical contradiction
      while recording the non-contradictory Spanish FT Master omission
      and broader Deployable-placement question. No answer, published
      scope or effective-date selection changed. The 20 carried-forward
      Spanish source answers are reviewed separately below; deferred
      ITS-only applicability is not claimed complete.
    - [x] Cross-check the **20 current, v0.0-origin answers** against
      Spanish FAQ v0.1. Pin each Spanish printed citation page
      (8/8/4 across pp. 1–3) and assert all original/current citations,
      date/version gates, non-conflicting answers and Supplies-only
      scenario scope. The Spanish Stealth/ARO question specifies
      *outside ZoC or Hacking Area*, unlike the broader English
      question; both conditional Idle answers agree. Source rationale
      records the narrower Spanish question without inventing
      permission inside those areas or changing gameplay. The
      regression and source audit distinguish this bounded bilingual
      review from historical replay and deferred ITS-only questions.
  - [x] Verify source-to-ordinary-browser reachability of **all 29 published
    reviewed FAQ rulings** against a fresh rules export. The tracked
    `test_every_published_faq_has_a_normal_browser_entry_point` drives
    25 normal Skill, Equipment, Trait, State, Hacking Program, General Rule,
    Fireteams and Core Scenario entry points in Chromium at 1440/390 px.
    All 8 grouped browser checks passed on 2026-10-29, matching every
    selected FAQ question, answer, source citation and authored topic
    against its owning page. Separate scenario tests reject ITS-only
    applicability leakage. This is bounded published-question delivery,
    not exhaustive FAQ source semantics or final 1.0 acceptance.
  - [x] Reconcile all **48 authored FAQ topic edges** (42 distinct topics
    for 29 current rulings) with the current rules selector. A focused
    source-derived regression verifies exact membership, selected source,
    original v0.0/v0.1 provenance and reviewed applicability for every
    topic in unscoped, Annihilation, Supplies and Firefight contexts.
    Historical 2025-10-15, pre-effective 2026-08-31 and wrong-revision
    5.2 queries select no current FAQ, including the two narrowly
    scoped Core scenario overlaps. Passed on 2026-10-29. This is a
    selector/reference coverage gate, **not** historical FAQ replay,
    source-wording certification or adoption of deferred ITS rulings.
  - [x] Prioritize links to features already represented by the app:
    deployment/private information, BS Attack/MODs/templates, Firewall,
    Marker/Camouflage/Peripheral/State interactions, Coordinated Orders,
    Fireteam creation/bonuses/integrity, and the two reviewed Core
    scenario overlaps. The maintained **48 FAQ topic associations over
    42 topics** now have an exact source-to-normal-browser coverage
    assertion, including 19 secondary associations beyond the first
    entry point for each of the 29 rulings. Chromium verifies those
    additional Skills, Traits, Equipment, States, General Rules and
    shared Fireteams/Core Scenario pages at 1440/390 px. Embedded
    scenario/Fireteam rule topics reuse their normal owning page,
    not duplicate rule cards. ITS-only rulings and season-specific
    scenarios remain post-1.0 and do not acquire universal core scope.
    This is current-source navigation coverage, not final release
    visual/touch acceptance or a historical FAQ browser.
  - [x] Verify all 29 current source selections, conflicting citations,
    effective-date scopes and source/version display against the
    applicability-first policy. English FAQ v0.1 is selected in each case;
    exactly one real numerical source conflict is retained (Fireteam Type:
    English three-to-two vs Spanish two-to-two Haris example). The Spanish
    FT Master omission is not a contradictory answer, so it generates no
    false warning. Chromium at 1440/390 px verifies visible selected English
    citation, date/version anchor, expandable Haris discrepancy explanation
    and Spanish alternative citation, with the base rules kept separate.
    Historical replay and browser date/season selection remain post-1.0.
    - [x] Assess historical v0.0 replay against the **current N5.3
      1.0 reference gate**: the 20 v0.0-origin citations are provenance,
      not v0.0-selected rulings or proof of N5.2 gameplay applicability.
      Retain the explicit-context API as a current-source filter, not
      a complete historical rules reconstruction. A regression checks
      all 29 current rulings against each of the four independent date
      gates, original versus selected provenance, previous-day and
      N5.2 exclusions, and valid scenario context. Preserve the
      2026-09-01 announcement-era anchor without claiming an exact
      PDF publication day. Record historical edition replay and
      browser date/season controls under post-1.0. Final
      release-candidate FAQ acceptance remains open.
    - [x] Correct the **FAQ source-date label** without altering the selected
      source or historical API field contract. The curated 2026-09-01
      `publishedDate` is an announcement-era reference/applicability anchor,
      not independent evidence of the PDF's publication day. The player
      section and citation cards now distinguish that provenance explicitly;
      Chromium/JavaScript regressions pin the wording. No source precedence
      or scenario scope changed. Exact PDF dates and full historical
      applicability remain open.
    - [x] Recheck the **Fireteam required-member FAQ bilingual qualifier**.
      English v0.1 p. 3 preserves the bracketed FT Master exception;
      Spanish v0.1 p. 3 omits it while agreeing on chart minimums.
      Source curation now records this omission without inventing a
      contradictory Spanish ruling; the actual Haris member-count
      contradiction remains explicitly flagged. N5.3 Fireteam
      Integrity p. 134 and reviewed `skill:ft-master` confirm the
      distinction. A source/API regression verifies both dispositions.
      No rules, selected citation, effective date or scope changed.
    - [x] Verify the **player-visible source-selection distinction** on
      Fireteams at desktop/mobile widths. The only current FAQ numerical
      contradiction exposes both English-selected and Spanish-alternative
      citations via an expandable disclosure. FT Master remains
      non-contradictory, not a warning; all ordinary FAQ entry points
      retain the explicit source version/date anchor and English citation.
      No rendering or source-selection bug required a gameplay change.
  - [ ] Revalidate this bounded 29-ruling/48-topic FAQ acceptance against
    the **final 1.0 release candidate** and release-matched rules database,
    including browser evidence and final source/disclaimer review. This is
    a release acceptance task, not a requirement for historical replay,
    official resolution of the Haris conflict or the eight ITS-only Q&As.
    - [x] Introduce an opt-in **tracked release rules.db FAQ parity gate**:
      compare all 29 stored rulings and their source/citation facts against
      a fresh curated export, then compare all 42 topics across four
      scenario contexts (168 selections, 48 authored edges), including
      pre-effective-date and N5.2 exclusions. Fail closed on stale
      release artifacts without writing or silently replacing the DB.
    - [x] **Regenerate and verify tracked rules.db**: after the local
      rebuild on 2026-10-29, the independent opt-in FAQ parity function
      passed against the tracked binary (29 records, 48 topic edges,
      168 scenario/topic selections and closed pre-date/N5.2 contexts).
      This fixes the earlier 28 record-field and 134 projection
      differences detected at `f1dbf187`; no curated rule changed.
    - [x] Rebuild and verify the paired **deployed-objects.json**
      publication after the current rules export. The tracked-pair
      FAQ parity and primary/secondary/conflict Chromium gates pass
      at 1440/390 px with `INFINITYDB_RELEASE_FAQ_PARITY=1`.
      This is local database-pair acceptance; repeat it against
      the final frozen release candidate.
  - **Completion:** cover carried-forward/cross-posted rulings, supersession, conflicting sources,
    missing targets, and out-of-scope seasons. Every in-scope ruling is discoverable from its topic
    or scenario, and the reader can distinguish base rules from applicable clarifications.

- [ ] **Data processing + Web backend + Web frontend:** Extend generated rules-reference
  projections that build on the enriched canonical data rather than duplicating its facts.
  - [ ] Add a generated cross-army rule-variant usage index once exact variant
    semantics are reconciled: canonical Skill/Equipment -> Level/MOD/typed parameter
    variant -> Unit/profile/loadout occurrences. Derive it from canonical rules and
    Army occurrence relationships rather than maintaining a second classification.
    - [ ] Reconcile the remaining **37 Skill** source IDs with unresolved
      occurrence parameters and 14 Equipment source IDs. The tracked
      rules.db now includes the reviewed Mimetism/Berserk/Dodge/Surprise Attack mappings;
      `tests/test_audit_source_variant_inputs.py` pins this baseline
      and independently checks a fresh curated rules export. Revalidate
      the release-matched source pair before final certification.
      Source-only occurrence verification requires the ignored raw
      Army archive and is skipped in clean CI.
      Review other mixed TEXT/DISTANCE sources and named Equipment
      variants with extra MODs; preserve raw signatures and exclude
      unreviewed specific combinations from index counts. Fail closed
      rather than parsing numeric-looking display strings.
      - [x] **Data processing:** Reconcile Surprise Attack source Skill 191
        against English N5.3 p. 114, Spanish p. 88 and archived Wiki
        revision 3943. Its 767 direct rows have only exact extras 6/7
        (`TEXT: -3/-6`, 762/5 rows). The typed map targets the attacked
        opponent's Face to Face ARO Roll; activation requirements,
        Attribute-specific exceptions and the separate-attacker FAQ remain
        unchanged. The guarded matched-v9 refresh changes only the owning
        record's variant metadata and publication fingerprints. Source-only
        regressions cover both tracked and fresh rules exports; this is
        parameter reconciliation, not a published Unit-use index. See
        [source review](n5-source-history.md#reviewed-surprise-attack-occurrence-modifiers).
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
      - [x] Pin the six N5.3 **Restrictions Chart** rows (p. 194), containing
        **14 prohibitions**, in a read-only source manifest and cross-domain
        audit. Optional PDF verification checks all six ordered source
        clauses against the pinned English document. The audit preserves
        source-only TAG/VH/REM Troop Type selectors without inventing
        canonical IDs or Unit ownership, and compares maintained
        Equipment/Skill/Training facts where available. It separately flags
        Motorcycle's **upward-only** Jump restriction and Irregular's
        **Lieutenant selection** restriction, whose existing generic
        `restricts-use-of` relations are not sufficiently scoped for
        automatic legality decisions. This is source reconciliation, not
        a published player-facing Restrictions reference.
      - [x] Publish the **six-subject, 14-condition** N5.3 Restrictions
        chart as a deterministic read-only projection of the reviewed
        source manifest under the normal `/rules#restrictions` reference.
        Keep source-only TAG/VH/REM selectors unlinked, and link exact
        Motorcycle/Aerial/Prone/Cautious Movement/Climb/Jump/Lieutenant
        records without inventing new Troop Type identities. Make
        mounted-only upward Jump, distinct ladders and Lieutenant
        **selection** qualifications explicit. The browser reference
        preserves negative-only semantics; it is not a legality engine.
        The byte-exact static publication check and Chromium tests
        (1440/390/320 px) protect the source-to-browser contract.
      - [x] Add **contextual reverse links** from the seven existing
        Equipment, Skill and State reference destinations to individual
        Restrictions chart conditions. The deterministic publication now
        carries exact `ownerRecordId` and `targetRecordId` identity
        alongside public links. Profile pages list only matching negative
        conditions, including the mounted upward-only Jump and
        Lieutenant **selection** qualifiers. The normal browser follows
        deep links to the corresponding row. Chromium tests cover seven
        destinations across 1440/390/320 px plus an unaffected Skill.
        These are source-backed contextual references, not new
        canonical `restricts-use-of` edges or legality predictions.
      - [x] Introduce a **source-scoped typed negative-constraint model**
        (`src/infinity_db/restriction_conditions.py`) covering all
        **14** N5.3 restrictions with five distinct operation kinds:
        State entry, Skill declaration, terrain traversal, directional
        Skill movement and Army role selection. Validate explicit source
        selectors, actor/target identities, condition scopes, upward-only
        direction, ladder terrain and Lieutenant selection; fail closed
        on missing or broadened evidence. The deterministic public
        chart now includes typed `operation.kind` and `qualifier`.
        Preserve the original generic `rules.db` relations for backwards
        compatibility; this model does **not** assert action legality.
      - [x] Prototype and validate an **additive v9 SQLite/API contract**
        for the finite restrictions using a disposable copy of the
        current v8 `rules.db`. The candidate table preserves all
        14 typed negative conditions with source fingerprint, nullable
        source-only endpoints and distinct operation qualifiers. Legacy
        relation rows/composed API responses remain unchanged at
        v8; simulated v9/compatibility-11 is correctly rejected by the
        old validator, demonstrating the required version-aware
        application rollout. No HTTP endpoint, exporter, tracked
        database or live version has been changed. See
        `docs/data-model.md` for the staged read contract.
      - [x] Implement the **version-aware read path**, explicit
        deterministic v9/compatibility-11 exporter and additive
        `GET /api/restrictions`. Existing v8/compatibility-10
        snapshots remain valid; the API explicitly reports
        `available: false` with no inferred conditions on v8.
        Valid v9 snapshots must contain all fourteen exact typed
        source conditions. The opt-in build remains separate from
        normal v8 export and refuses the default tracked
        `rules.db` destination. Tests verify stable v9 bytes,
        both version paths, HTTP query validation and unchanged
        legacy Skill/Equipment API responses. The browser still
        consumes its independently published static chart.
      - [x] **Promote the synchronized v9 release pair locally** after
        reviewed N5.3 PDF/source hashes and 14 constraints were
        verified. The tracked `rules.db` now uses v9/compatibility-11,
        and the ignored `deployed-objects.json` was regenerated
        with its matching rules SHA-256; 17 reviewed objects and
        all other publication fields are unchanged. A guarded
        coordinated promotion retained the complete v8 release
        pair under ignored `local/` and validated the promoted
        application startup. The legacy generic relation graph
        is unchanged. See `docs/data-model.md` for fingerprints
        and recovery location.
      - [x] **Validate and package the promoted v9 release pair** in
        the GitHub Actions Source checks, Installed wheel smoke and
        Deployment smoke test workflows (all green at `b7230761`,
        2026-10-30). The release image accepts v9 with its generated
        publication; separate v8 and v9 read-path/HTTP tests pass.
        These checks validate the CI image, **not** a hosted deployment
        or image-level rollback on the live host.
      - [x] **Audit and qualify both over-broad legacy display
        relations** without changing the canonical graph or the raw
        `relations`/`reverse_relations` API contract. N5.3 p. 194
        supports Motorcycle → Jump only for upward movement while
        mounted and Irregular → Lieutenant only for Army role selection.
        The player-facing labels now convey those scopes in both
        directions; all other relation labels remain generic.
        Source-specific typed restrictions and static chart links
        remain the authoritative explanation. Tests exercise v8/v9
        projections and untouched structural edges.
      - [x] **Add a CI rollback-image rehearsal** to the deployment
        smoke workflow. Generate an independent v8/compatibility-10
        database and matching publication under ignored `local/`,
        compare them with the tracked v9 pair (all reviewed objects
        and legacy relations identical; only the rules database SHA
        differs), and build a disposable v8 overlay image from the
        same already-validated v9 application. Require v8 schema,
        unavailable typed Restrictions, full container startup/HTTP
        checks, then recheck the original v9 image. Hermetic
        release-pair parity and workflow contract tests pass locally.
        The Docker rehearsal passed hosted Deployment smoke at
        `663a345` (2026-10-30).
      - [x] **Confirm the v8 rollback-image CI gate passes** for
        commit `663a345` (Deployment smoke test, 2026-10-30).
        The disposable source-equivalent v8 rules/publication pair
        passed provenance, container-startup and HTTP checks, followed
        by another successful v9 image check. This proves application
        compatibility, not exact historical v8-byte identity.
      - [ ] **Validate the real host-level rollback/forward process**
        using the retained original v8 database/publication pair.
        The CI rehearsal did not replace live containers or perform
        a hosted deployment. Require explicit operational authorization
        and a separately reviewed rollback plan before changing the host.
      - [x] **Audit the seven absent conventional legacy edges and
        their actual consumers.** Six represent TAG/VH/REM source-only
        Troop Type selectors (no canonical owner record), and the
        seventh is Motorcycle ladder traversal (no Skill target).
        All seven are already source-ordered in the reviewed v9
        `restriction_constraints` API and static browser publication;
        browser reverse links use the exact target concept where
        available. A regression pins the seven subject/action pairs,
        source scope and operation, v9 API projection, and absence
        of fabricated owners/ladder Skills. No current player-facing
        consumer needs a generic edge. Retain the legacy graph
        unchanged; do not mistake its missing edges for missing
        Restrictions coverage or infer permission from absence.
      - [x] **Verify Irregular Training occurrence ownership**
        against the tracked Army database: normalized
        `loadout_payload_orders` carry source Order types at specific
        loadout occurrences; `SkillCatalog.enrich_unit()` already maps
        Irregular Order entries to `training:irregular`. The real-snapshot
        regression verifies the source-to-Unit-detail mapping and
        confirms no Training reference is promoted to a profile or
        Unit-wide property. Earlier samples of Skill/Training item
        arrays were not the authoritative Order source.
        The chart and Lieutenant detail already link the selection
        prohibition; **do not add a Unit-level reverse link** absent
        an explicitly option-scoped use case and provenance model.
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
    - [x] **Audit Isolated State ↔ Fireteams/Coordinated Orders source ownership.**
      The reviewed Isolated definition forbids Fireteam membership and Coordinated
      Order participation; the Fireteam General Rules already link back to
      `state:isolated` and distinguish Leader-triggered cancellation
      from ordinary member departure. Coordinated Orders' same-Training
      requirement does not override isolation. A source/database regression
      pins these contextual facts without inventing automatic State transitions.
    - [x] **Publish scoped Isolated State navigation** to Fireteam General
      Rules and Coordinated Orders. Two distinct source-authored edges,
      `prevents-membership-in` and `prevents-participation-in`, carry
      the affected-Trooper scope and generate reverse composed links.
      The State's maintained restrictions now link both owning rule
      topics and distinguish Leader cancellation from ordinary member
      departure. The Fireteams-specific landing at `/fireteams`
      preserves its existing State links; the Coordinated Orders
      detail has the reciprocal typed relationship. HTTP and normal
      Chromium tests at 1440/390 px cover both publication paths.
      Regenerated the tracked v9 rules.db
      and paired ignored deployed-object publication with guarded
      checks and retained v9 recovery copies. No Unit live-State,
      Team-wide restriction, or legality inference was introduced.
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
        - [x] Extend the read-only Weapon/Equipment inventory beyond
          summary-only keywords. The 104-definition source-domain scan
          now inspects detailed clauses and reports 10 additional
          evidence-preserving leads, marking SymbioBomb as already
          reviewed rather than a new gap. The scan changes no object
          identities, source values, or delivery relationships.
        - [x] Review all nine additional source-domain clause leads
          against pinned N5.3: Chest Mine, Sepsitor Plus, Flammenspeer,
          Chain Rifle, Multispectral Visor, Baggage, Escape System,
          Holomask and Holoprojector. Explicit source-backed decisions
          separate carried attacks, temporary Templates, chart footnote
          markers, reloads and Trooper representations from persistent
          deployed objects. The read-only manifest
          `config/validation/deployed-object-source-domain-clause-reviews.json`
          is validated against exact curated evidence; all **10/10**
          clause leads are accounted for (including previously reviewed
          SymbioBomb). No new source profile, delivery edge or Unit
          carrier is inferred.
        - [x] Migrate all **14 N5.3 citations** into maintained rules:
          Escape System (p. 117), Holomask and Holoprojector (p. 124),
          plus the eleven reviewed non-catalog/expanded definitions.
          The six-file coordinated promotion replaced the three
          review manifests, curated JSON, `rules.db` and its matching
          `deployed-objects.json`. Preflight confirms **0 pending /
          14 migrated**; the published reference remains 17 objects
          with 28 reviewed delivery paths.
          - [x] Add a single **read-only migration preflight**
            (`tools.audit_deployed_object_citation_migrations`) that
            reconciles all 14 pending records and their exact page
            proposals across three review manifests. The optional
            `--pdf` check verifies all excerpts against the pinned
            English N5.3 PDF and records its SHA-256. Missing,
            stale or prematurely published citations fail closed;
            there is no source/database mutation.
          - [x] Implement and test an **isolated, coordinated migration
            staging build**. `tools.stage_deployed_object_citation_migration`
            preserves existing curated/manifest formatting, stages
            exactly 14 maintained citations and removes the 14
            temporary PDF-only manifest fields, then builds a matching
            `rules.db` and fingerprinted `deployed-objects.json`.
            Review validators and the preflight now accept either the
            complete pre- or post-migration state, but reject partial
            migration and mismatched evidence. Focused staging tests
            verify generated data without altering tracked inputs.
          - [x] Promote all six staged files together, following
            `docs/testing.md`. The local post-promotion preflight,
            focused audit and publication tests, temporary rules
            rebuild and lint/docs/type checks pass. A targeted
            regression additionally matches all six promoted files
            byte-for-byte against the staging report and validates
            the binary SHA-256 fingerprints. Full suite and CI
            remain the release gates; nothing deployed.
        - [ ] Expand object discovery beyond maintained definitions
          and the current lexical scans, especially source tables,
          scenarios and unmodeled Weapon/Equipment variants. Closed
          queues are not an exhaustive game-object inventory.
          - [x] Cross-check the independent **N5.3 p. 74 Deployable
            Profiles quick-reference table** against the existing
            reviewed object reference using pinned PDF extraction.
            Its 13 printed rows resolve to ten distinct reviewed
            objects, one generic Mines family row, and repeated
            FastPanda/Madtraps entries. Preserve Armed Turret's
            S1/S2 contradiction and Dazer's S0/S1 dispute instead
            of deduplicating source observations or inventing object
            identities. The read-only audit and regression are in
            `tools/audit_deployed_object_quick_profiles.py` and
            `tests/test_deployed_object_quick_profiles.py`.
          - [ ] Audit other independent source tables and scenario
            elements not covered by the main Weapon Chart or p. 74.
            Reconcile their game-element categories independently
            of Unit/loadout ownership and current lexical scans.
            - [x] Reconcile the **complete N5.3 p. 191 Orders/AROs
              source chart**: 57 printed declaration rows (3 Basic
              Short, 15 Long, 23 Short, 16 ARO), resolving to
              **42 existing canonical owners** across Skills, Equipment
              and Hacking Programs. Verify each printed row's name,
              source Type and page using geometric PDF extraction and
              the pinned PDF hash. All curated Skill category memberships
              agree; all **19 Hacking Program declaration occurrences**
              match separate Army-backed metadata (including the
              normalized Long Skill convention). The Equipment-labeled
              Activate Disco Ball remains a Skill, and printed Look Out!
              links to the canonical Look Out Skill. This is **source
              validation only**: it neither adds deployed objects,
              delivery edges or Unit carriers nor implements the
              separately planned generated player-facing matrix.
              The established audit-only manifest and tests now guard
              full printed-row coverage, owner and declaration drift:
              `config/validation/orders-aro-object-adjacent-source-review.json`.
            - [x] Independently reconcile **N5.3 core scenario
              objectives** (pp. 149–156): Annihilation and Firefight
              contain no scenario-object Markers; Domination has
              exactly four Consoles (p. 151) and Supplies has three
              Supply Boxes (p. 153) in each of three map
              configurations. The read-only boundary audit verifies
              placement/source citations, scenario-only interaction
              Skills, scoring-status references, physical Marker IDs,
              and exclusion from the 17 published Weapon/Equipment
              deployed-object identities. No Army carrier or new
              delivery relationship is inferred.
            - [x] Review the independent **Special Terrain Suggestions
              and Examples** table and Scenery Structures access
              markings (N5.3 pp. 143–145). The pinned PDF confirms
              five terrain Types, **18 suggested example rows**,
              and two Access Width Tokens (Narrow Gate, Wide Gate).
              These are optional game-table characteristics/examples
              and scenery access labels, not new Weapon/Equipment
              deployments or 18 extra canonical terrain Types.
              The read-only audit pins printed spellings and records
              missing maintained Special Terrain/Access Width rules
              and gate-marker reference terms. Existing `skill:terrain`
              remains available. No source/profile/carrier publication
              change was made.
            - [x] Publish the reviewed **Special Terrain** and
              **Access Width** reference definitions independently of
              current map/session instances. Preserve the five
              terrain-type parameters, Difficult/Saturation/Visibility
              composition, and Narrow Gate Silhouette/Prone
              restrictions; do not create deployable object identities
              from terrain suggestions or label Tokens.
              - [x] Pin two N5.3-cited `basic-rule` proposals in
                `config/validation/terrain-scenery-reference-additions.json`
                (pp. 143 and 145). Validate the source format and
                canonical refs, and stage the curated JSON, rebuilt
                `rules.db`, and fingerprinted
                `deployed-objects.json` together using
                `tools.stage_terrain_scenery_references`. The
                isolated staging regression passes and preserves
                all tracked files.
              - [x] Complete the **post-promotion binary refresh**.
                Both maintained rules are present, their interaction
                reviews and canonical text links are updated, and
                the supporting review gate passes **200/200**. The
                two refreshed tracked binaries match the local
                `terrain-scenery-refresh-n53` staging report and
                files byte-for-byte; the report's source SHA-256
                matches the curated JSON. The publication retains
                **17 reviewed objects**, with its rules-database
                fingerprint verified in a focused regression.
                Source, rules, publication and static checks pass.
                Full project/CI checks remain release gates;
                nothing deployed.
              - [ ] Consider separate glossary/source terms for
                Narrow and Wide Gate labels and typed
                terrain-characteristic combinations if player
                discoverability requires them; do not conflate
                their labels with persistent deployed devices.
            - [x] Independently reconcile the N5.3 **Retreat! threshold
              table** (p. 146) and generic **recommended table-size**
              guidance (p. 147). Six printed Army Points rows
              (150/200/250/300/350/400) have Retreat! thresholds
              (38/50/63/75/88/100 VP) and advisory dimensions
              (24×32 / 32×48 / 48×48 inches by game-size group).
              The new read-only source manifest and audit preserve
              upward rounding at 150/250/350, army/session Victory
              Points versus Trooper Retreat! State, and optional
              table-layout advice versus scenario-owned dimensions.
              The pinned PDF check verifies the source rows using
              page coordinates; no Unit attributes, scenario
              overrides or deployed-object identities were added.
            - [x] Reconcile N5.3 **Game Modes** (p. 6) against
              independent Retreat!/table recommendations (pp. 146–147).
              All six source rows now have pinned mode names, Army Points,
              SWC allowances (3/4/5/6/7/8), table dimensions,
              deployment-zone dimensions, and recommended durations
              (40/50/60/90/100/120 minutes). The new read-only
              cross-table audit checks row order, exact PDF cell
              positions and consistency with the separate source
              manifests. Game Modes are recommendations, not
              mandatory scenario or Unit Profile rules.
            - [x] Decide the immediate general-reference boundary:
              retain **source-reviewed manifest-only data** for Game
              Modes, Retreat! thresholds and generic table guidance
              until a unified general-reference presentation contract
              is designed. Do not duplicate these rows into a
              scenario, Unit, Army, or deployed-object identity, or
              treat advisory setup dimensions as scenario rules.
            - [ ] Design a general game-setup reference presentation
              if required by the 1.0 player-useful-data inventory;
              model the source rows once, identify authority/overrides,
              and keep session/Retreat! computation outside static data.
            - [x] Reconcile the **N5.3 Silhouette Templates** table
              (p. 18) against the existing browser diagram geometry.
              The PDF pins **ten source rows** (SX, S0–S8); all eight
              rendered S1–S8 dimensions match their source base widths
              and heights. S0 is a fixed 25 mm base/3 mm height, while
              SX is the 3 mm high Prone representation whose base width
              follows the Trooper's original Silhouette Attribute.
              There are deliberately no S0/SX SVG diagrams; the UI
              already provides contextual text instead. A fail-closed
              source manifest and audit verify maintained attribute
              references, displayed dimensions, distinct Prone
              semantics, all eight SVG assets, and the English PDF.
              No Unit characteristic or deployed-object profile changed.
            - [x] Audit the independent **N5.3 Hacking Device
              Programs Chart** (p. 58) against the four maintained
              Equipment definitions and the canonical Hacking Programs
              domain. The four device sets grant 4/6/2/4 Programs
              (Hacking Device / Plus / Killer / EVO), with **11
              distinct Programs** across them. The source matrix is
              device access, distinct from the Hacking Programs
              statistics chart on the same page and unrelated to
              Unit carriers or deployed Weapons/Equipment. The
              read-only audit pins printed row assignments and
              verifies all Program references; no runtime relation
              or identity was created.
              - [x] Promote the **four verified p. 58 citations**
                into the maintained Hacking Device definitions
                together with `rules.db` and the dependent
                deployed-object publication fingerprint. The four
                direct PDF citations are now maintained alongside
                the existing wiki sources; Program access is unchanged.
                - [x] Implement the staging-only citation migration
                  in `tools/stage_hacking_device_chart_citations.py`.
                  The source audit now rejects partial/wrong-page
                  migrations while allowing exactly the fully pending
                  or fully migrated state. Focused tests verify that
                  only four source citations are appended, wiki
                  citations remain, the generated rules database
                  and fingerprint are aligned, all 17 deployed-object
                  records are identical, and tracked inputs remain
                  unchanged. The p. 58 PDF source is verified.
                - [x] Stage and inspect the three outputs on
                  2026-10-30 from HEAD `5e4647c`. The report at
                  `local/hacking-device-citations-n53/staging-report.json`
                  matches all three independently read SHA-256 hashes,
                  the unchanged source/Army inputs and the verified
                  N5.3 PDF. Exactly four p. 58 citations are added;
                  the existing wiki citations and 4/6/2/4 Program
                  assignments remain intact. The staged publication
                  passes `--check` with the matching rules fingerprint
                  and identical 17 reviewed objects/delivery paths.
                  Focused staging/chart tests: 8 passed, 1 skipped.
                - [x] Promote the curated JSON, `rules.db` and
                  `deployed-objects.json` as a guarded, rollback-capable
                  batch through tracked MCP `run_script` on 2026-10-30.
                  The promoted SHA-256 values match all three staged
                  outputs; the source audit has zero missing citations,
                  publication `--check` passes, and the 17 reviewed
                  objects/delivery paths are unchanged. Focused tests,
                  rules, lint, docs and type checks pass. The full
                  project test suite and CI remain release-level gates.
            - [ ] Continue source-table discovery beyond the terrain,
              scenario, Game Modes, Retreat!, Silhouette Templates,
              Hacking Device charts, Weapon Chart and p. 74 reviews;
              verify additional game-element categories against direct
              rules before expanding a canonical inventory.
              - [x] Independently verify the **12-row N5.3 Hacking Programs
                statistics chart** (p. 58) against the pinned September 29
                Army `metadata.json`, generated database and existing API
                parity checks. An audit-only source manifest pins all 12
                printed identities, Attack/Opponent MOD, PS, Burst, Target,
                Skill Type and reviewed Special clauses. The optional pinned
                PDF check validates row/column geometry independently of
                Army row order, with **zero statistical mismatches**.
                Source order places Total Control and Trinity before
                Spotlight, while Army orders Spotlight first; this is a
                harmless order difference, not a profile discrepancy.
                No Program facts, Device grants, Unit carrier, runtime
                identity or generated database was changed. The separately
                checked Discover range (p. 77/main Weapon Chart) and
                Fireteam charts (pp. 133–136) already have maintained
                references; avoid duplicate definitions.
              - [x] Reconcile the **N5.3 Hacking Program chart Target dash**
                against the p. 57 chart key and individual Program clauses
                (pp. 59–61). Spotlight's dash does not prevent targeting
                non-Hackable Troopers; Cybermask is self-directed, while
                White Noise creates a zone. Preserve the original Army
                `targets` arrays and rendered dash, and add conditional
                player-facing guidance to consult the maintained rules
                instead of implying there are no valid targets.
              - [x] Independently pin the **N5.3 p. 194 Restrictions Chart**:
                six source conditions and 14 prohibitions in an audit-only
                cross-domain manifest. TAG/VH/REM remain source Troop Type
                selectors, not manufactured canonical entity records;
                motorcycle upward Jump and Lieutenant selection remain
                scoped operations. See the separate generated Restrictions
                reference TODO for the outstanding player-facing work.
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
            - [x] Add a second audit-only reviewed classification manifest,
              `config/validation/deployed-object-candidate-reviews.json`,
              pinned to exact English N5.3 citations and curated facts:
              Deployable Cover is an S3 Scenery Element with ARM/BTS/STR
              unreported; Armed Turret retains its curated ARM 2/BTS 3/STR
              1/S2 profile and unresolved S1 summary conflict; Deactivator
              is a tool acting on deployed objects, not a deployed object;
              SymbioBomb is an assignable single-use Weapon, not a
              standalone deployed-object profile. Validator regression
              rejects classification/shape changes, lost citations and
              unsupported values. Other candidates were reviewed separately
              in the subsequent bounded keyword-queue closeout.
            - [x] Close the bounded **curated-summary keyword queue**:
              all 15 matching definitions are covered by reviewed
              classifications or the five reviewed delivery origins.
              WildParrot, Dazer, and FastPanda retain exact Army source
              profiles; Mines is a family rather than one generic object;
              D-Charges resolve immediately; Cube is automatic Equipment;
              TinBot has a non-targetable State Token. The manifest pins
              source pages and evidence, rejects profile drift, and
              retains the Dazer S0/S1 disagreement.
            - [x] Close the additional **detailed-rule keyword queue**
              across Weapon/Equipment definition Requirements, Effects,
              Restrictions, Clarifications and source notes. Cube 2.0
              (Command Token recovery reroll, N5.3 p. 121) was the one
              previously unreviewed detail-only candidate; its automatic
              Equipment/non-deployed-object status is now pinned. The
              repeatable audit fails on future uncovered detailed mentions.
              Neither bounded scan proves full N5.3 object, delivery,
              Unit or loadout completeness.
            - [x] Start a separate **non-catalog game-element queue** across
              Skill/rule/Trait/term/State definitions. The read-only
              `tools.audit_deployed_object_non_catalog_queue` records
              keyword evidence and source citations without generating object
              identities. Three source-backed Skill decisions are pinned:
              Place Deployable is a delivery action (p. 82), Minelayer a
              deployment method (p. 102), and Request Speedball creates
              support State Tokens that Deactivators cannot target, rather
              than standard four-attribute deployed objects (p. 84). Preserve other
              matches as an open manual queue and review further candidate
              identities before expanding the 17-object reference.
              - [x] Review ten additional non-catalog source candidates in
                a bounded N5.3 batch. The pinned keyword queue contains
                48 definitions: **13 reviewed, 35 still open**. Glossary
                Token/State Token/Deployable/Scenery terms (p. 173) describe
                categories, not universal object instances. SpecBall (p. 98)
                is a distinct non-targetable support State Token; RemDriver
                (p. 110) marks a Remote's MODs. Ancillary Peripherals
                (pp. 107-108) are placeable Troopers requiring separate
                Unit/Profile interpretation, and Supplies' Box plus Pick Up
                Skill (p. 153) are scenario-specific objective mechanics.
                No additional four-stat profile, Army carrier or reviewed
                delivery edge follows from these rules. Next: review
                remaining keyword hits including Boost/Perimeter and
                scenario/peripheral markers, plus source wording absent
                from the keyword query.
              - [x] Review 12 further N5.3 non-catalog definitions:
                the Deployable/Perimeter/Boost Traits, Intuitive Attack,
                Dodge, Stealth, Cautious Movement, Guts Roll, Control/
                Cyberplug Peripheral role Tokens, Camouflaged and HoloMask
                States. This bounded scan now has **25 reviewed of 48**,
                leaving **23 open**. The reviewed cases are object-class,
                placement/trigger interactions, or representations of
                existing Troopers/items—not new object profiles or
                inferred Army ownership. Source citations and summary/
                detailed clauses are pinned, including a drift guard when
                summary-only Trait definitions gain detailed text.
                Next: remaining deployment-state, scenario, and command-
                token candidates, then broader wording/source discovery.
              - [x] Review the remaining 17 **directly N5.3-cited**
                non-catalog candidates: failed deployment handling for
                Combat Jump/Impersonation/Infiltration; Impetuous, NWI,
                Protheion, G: Jumper and Retreat! status Tokens; Doctor,
                Engineer, Remote Presence, Strategos L2 and reroll/
                Command Token references; Coordinated Orders' Spearhead,
                Deployment Phase, Domination scoring and Hacking Area.
                These change neither the underlying object identity nor
                reverse Unit use. The bounded keyword queue is now
                **42 reviewed of 48**, with **six unresolved**.
              - [x] Classify the final six keyword matches with
                independently checked English N5.3 PDF evidence:
                Frenzy (p. 93), Possessed (p. 169), Command Token
                Strategic Use (p. 128), Counterintelligence (p. 90),
                Inspiring Leadership (p. 99) and Transmutation
                (p. 117). The bounded non-catalog keyword queue
                is now **48/48 reviewed**, without any new deployed
                Weapon/Equipment identity or inferred carrier.
                The audit manifest pins PDF excerpts separately because
                these six maintained records still only cite Wiki
                revisions; PDF-only reviews are not runtime citations.
              - [x] Migrate the six verified PDF citations into
                maintained rule records, alongside the other eight
                verified citations; rebuild `rules.db` and refresh the
                deployed-object publication fingerprints together.
                The non-catalog audit now reports **zero** missing
                maintained N5.3 citations.
              - [x] Classify `rule:access-width` against the existing
                reviewed N5.3 p. 145 Access Width definition. Narrow
                and Wide Gate Tokens label agreed scenery openings;
                they are not deployed Weapon/Equipment profiles or
                reverse Unit uses. The Prone/Silhouette X exception and
                Movement priority remain rule-level constraints. The
                non-catalog keyword queue now has **49/49 reviewed**
                classifications; this does not establish complete N5.3
                game-element coverage beyond the bounded keyword scan.
              - [ ] Extend object discovery beyond the bounded
                non-catalog keyword/definition-fields scan, checking
                alternate wording and other N5.3 source domains.
                Reconcile any source-backed object identities and
                delivery edges independently, without extrapolating
                from names, rule methods or generic Traits.
                - [x] Start a **separate expanded lexical queue** using
                  Console, Supply Box, Disco Ball and Marker/decoy terms.
                  The read-only audit finds 25 additional definitions;
                  six now have pinned review decisions. Core N5.3
                  Consoles (p. 151) and Supply Boxes (p. 153) are
                  scenario objects, not Weapon/Equipment inventory;
                  their Hack/control rules create no new identities.
                  Activate Disco Ball (p. 71) acts on the already
                  reviewed Disco Baller source-mode object; a generic
                  Marker (p. 173) is a representation, not an item.
                  None adds an Army carrier or a publication edge.
                - [x] Review eight additional N5.3-cited expanded
                  definitions: Decoy Skill, Holoecho, Hidden Deployment,
                  Impersonation-1/-2, Discover, Surprise Attack and Sensor.
                  Holoecho replicas can provoke AROs and trigger deployed
                  devices despite not having independent Weapon/Equipment
                  identities. The expanded queue is **14/25 reviewed**.
                - [x] Classify the final **11 expanded candidates**:
                  Indiscriminate, Look Out!, Chain of Command, Morpho-Scan,
                  Killing, Reinforced Tactical Link, Decoy State,
                  Concealed, Mnemonica, Tactical Awareness and Explode.
                  All have been manually checked against N5.3 pages;
                  the expanded bounded lexical queue is now **25/25
                  reviewed**, without a new deployed-object identity.
                  Decoy replicas may affect LoF and be targeted, while
                  Concealed applies an S2 Camouflage representation to
                  an existing Weapon/Equipment item.
                - [x] Migrate the five expanded-review citations
                  (Decoy State p. 159, Concealed p. 175, Mnemonica
                  p. 103, Tactical Awareness p. 115, Explode p. 92)
                  alongside the other nine citations, with a
                  coordinated rules database and publication refresh.
                  The expanded audit now reports **zero** missing
                  maintained N5.3 citations.
                - [ ] Expand discovery beyond both lexical scans and
                  their definition/field boundaries, including
                  source tables and other N5.3 game-element domains.
                  No total object-completeness claim is established.
            - [x] **Reconcile delivery paths for all 17 currently published
              reviewed deployed objects.** The pinned review now covers
              17 of 17 objects with 28 approved delivery paths and zero
              uncovered objects in this bounded inventory. Newly reviewed:
              WildParrot's ordinary
              Place Deployable and WIP-based Intuitive Attack paths,
              FastPanda's Perimeter placement and Armed Turret's
              reviewed-only curated profile placement. The last retains
              its disputed S1/S2 Silhouette and has no manufactured
              Army four-stat profile. `tools.audit_deployed_object_delivery_coverage`
              lists the outstanding objects and exact source-catalog aliases
              for further N5.3 review, without promoting aliases into
              methods or Army/Unit carriers. Keep Mine Dispenser's
              unresolved subtype explicit.
              - [x] Add source-cited Crazykoala/Madtraps N5.3 definitions
                and reviewed Place Deployable/Perimeter delivery paths.
                N5.3 p. 69 and chart pp. 186-187 distinguish their shared
                Boost placement/trigger behavior from Crazykoala Shock and
                Madtraps PARA/Non-Lethal. The publication API and 1440/390 px
                Chromium acceptance now verify their source links and exact
                Army-backed reverse uses; this does not certify remaining
                unreviewed object deliveries or roster legality.
              - [x] Review Dazer's ordinary Silhouette-contact Place
                Deployable origin (N5.3 pp. 82, 121), with its separate
                ZoC terrain effect and unresolved S0/S1 source conflict.
                Review Deployable Cover's Place Deployable/Perimeter origin,
                S3-only scenery profile, and Unit Profile-dependent
                Cutting Foam/Vitroferro selection (p. 122); ARM/BTS/STR
                remain unreported.
              - [x] Review Cybermine's Place Deployable and exceptional
                Intuitive Attack delivery paths (N5.3 pp. 49, 72, 82,
                181). A failed Intuitive Attack consumes a use without
                placing a Mine. The resulting deployed Cybermine is
                distinct from its Comms Attack/Reset-only trigger effects.
                Exact reverse Unit/loadout uses now fall back from a
                missing imported Unit name to the existing logical-unit
                name, without fabricating Army or profile ownership.
              - [x] Review AP, E/M, Monofilament, PARA, Shock and Viral
                Mines as six separate Army source subtypes. Each has two
                evidence-backed deliveries (ordinary Place Deployable
                and conditional Intuitive Attack), N5.3 pp. 49, 72,
                82 and 181. Five new narrowly scoped curated definitions
                complement the existing PARA Mine definition and shared
                Mines rules. All retain the printed S0 versus imported S1
                discrepancy; no subtype inherits another's ammunition.
                Publication regression tests require reverse Unit uses to
                match each exact Army source ID. This closes the bounded
                17-object delivery-origin gap, not exhaustive N5.3
                coverage, roster legality or the unresolved Mine Dispenser
                Unit/loadout-specific subtype.
            - [ ] Implement the minimal **deployed-object reference
              contract** after source review. Separate stable object/
              variant identity from the carrier's Weapon/Equipment
              catalog record, exact Army source selector (ID and mode),
              delivery method, and Unit/loadout ownership. Represent
              ARM/BTS/STR/S individually as known, unreported, or
              disputed with source provenance; do not coerce missing
              values to 0 or assume all objects have four attributes.
              Explicitly reviewed item/mode-to-object delivery edges
              may have multiple origins; derive reverse usage only
              from proven edges and actual Unit/loadout associations.
              Preserve unresolved Mine subtype and S0/S1 disputes.
              Validate API, browser navigation and missing/variant/shared
              cases before closing the player-facing requirement.
              - [x] Implement and test the **pure source-backed read
                projection** in `deployed_object_reference.py`:
                17 distinct reviewed entries (15 Army profile identities,
                Armed Turret and Deployable Cover), source-snapshot hashes,
                exact Army ID/mode ownership, attribute-level known/
                unreported/disputed provenance, and grouped reviewed
                delivery origins. The six Mine/Silhouette, Dazer and Armed
                Turret disputes retain alternatives; Cover lacks only
                unreported ARM/BTS/STR. Mine Dispenser remains unresolved.
                Tests assert shared-object delivery and no invented Units.
                The pure projection is separate from artifact-gated publication.
              - [x] Add the **artifact-gated read-only API and normal browser
                entry point** for the 17 reviewed objects:
                `/api/deployed-objects`, exact `/api/deployed-objects/{id}`,
                and `/deployed-objects` linked from Weapons and Equipment.
                The isolated Chromium acceptance covers both 1440/390 px,
                unresolved Mine Dispenser, known/unreported/disputed
                attributes, source reference links, shared delivery paths
                and keyboard fragment navigation. Missing publications
                return 503; invalid or database-mismatched publications
                fail closed. Unit uses require independently reviewed
                delivery origins and exact Army source occurrences.
              - [x] **Validate hosted delivery** of the deterministic
                `data/generated/deployed-objects.json` release publication
                for the pinned `infinity.db`/`rules.db` pair. Deployment
                and CI generate/check the artifact from reviewed sources,
                Docker packages it, and the image smoke validates hashes,
                17 objects, unresolved delivery, API and browser entry.
                Deployment smoke, source checks and installed-wheel smoke
                passed on commit `9c9a09f` (2026-10-22). Revalidate on the
                final tagged candidate as part of final 1.0 acceptance.
              - [x] Refresh the local rules/deployed-object publication pair
                from current maintained inputs and pass the publication
                `--check` and deployment-asset validation. Final frozen
                candidate and hosted acceptance remain separate gates.
              - [ ] Complete **reverse Unit/loadout uses** from exact Army
                occurrences and reviewed object/delivery edges.
                Direct Army profile/loadout and source-wide Unit-option
                occurrences are now separately typed, as are one-level
                Includes from profiles, loadouts and Unit options.
                Unit options retain null Army/group context; their Include
                targets retain the resolved target Army only, not a
                fabricated parent Army assignment. Source positions,
                parent IDs, included payload IDs and reviewed delivery
                methods remain available. A pinned, full-depth audit of all
                contextual Include roots against reviewed delivery-source
                IDs found **no additional transitive uses**, ambiguous
                intermediate targets or cycles (2026-10-22). The audit is
                regression-tested for deeper matches, shared targets and
                cycles; rerun on any new Army/review snapshot. Review other
                unrepresented source contexts before closing. Preserve
                unavailable attributes, conflicting Silhouettes and the
                unresolved Mine Dispenser subtype; do not infer ownership
                from rule prose.
                - [x] Independently reconcile reviewed Weapon/Equipment
                  reverse-use rows with all matching raw Army direct
                  profile/loadout/Unit-option occurrences and resolved
                  one-level Include targets. The 2026-10-29 pinned-pair
                  local tests pass without missing or extra uses; reviewed
                  profile-include origins have no matches in this snapshot.
                  This requires the ignored `infinity.raw.db`, so clean CI
                  skips the raw-pair comparison. It does not establish
                  unreviewed delivery, variant or object completeness.
                - [x] Classify current source-schema Weapon/Equipment
                  references: Army-level catalog membership, Unit-bearing
                  profile/loadout/Unit-option occurrences, reusable Weapon
                  option templates and the three Include contexts. The
                  schema regression flags new source catalog foreign keys
                  or changed Include selectors for explicit review, even
                  without the ignored raw database. This is structural
                  coverage, not evidence of all N5 object/delivery semantics.
    - [ ] Expose deployed-object profiles and reverse uses through a usable reference entry point.
      Test objects supplied through Weapons and Equipment, shared objects/multiple carriers,
      missing/not-applicable values, and carrier-to-object navigation without inventing Unit identity.
  - **Completion:** players can inspect Weapon profiles and reach Ammunition/Traits and
    deployed-object statistics without selecting a carrier first; reverse uses preserve
    Army/loadout context. Missing in-scope facts must be exposed; dedicated comparison
    controls are not a separate release blocker.

### Player-facing navigation and reference clarity

**Project domains:** Data processing, Web backend, Web frontend

These are 1.0-scoped usability and reference-interpretation follow-ups.
Reuse the published data model and existing browser components; treat
enhancements as release-blocking only when their omission
would materially impair required reference access, clarity or source disclosure.

- [x] **Web frontend:** Reduce the **sidebar menu's vertical footprint**
  before 1.0 without hiding destinations or introducing another nested
  navigation disclosure. Compact desktop row padding, section spacing
  and decorative footer gaps while retaining readable targets and
  current-route indication. Bound the existing compact popovers to
  the viewport with internal scrolling for short touch screens.
  Chromium checks at 1440px, 1024px, 390px and 320px validate all 16
  destinations, focus/scroll reachability, responsive sticky navigation,
  settings expansion and keyboard/touch operation. See the
  [responsive design contract](web-design-guidelines.md#make-responsiveness-a-content-priority-decision).
- [x] **Data processing + Web backend + Web frontend:** Publish
  **Specialist Troops** as an **InfinityDB general reference Rule**, even
  though the official N5.3 source defines it within individual scenarios.
  The maintained `rule:specialist-troops:standard` carries the unscoped
  qualifier list in General Rules, search and Glossary, while scenario
  inclusions preserve explicit `addSkills`/`removeSkills` precedence and
  citations. Detail pages derive **Used by** links to Domination, Supplies
  and Firefight. Source/publication parity was revalidated after rebuilding
  the tracked rules database and dependent deployed-object artifact
  (`test_application_rule_references.py`: 15 passing).
  This does **not** create an unconditional Specialist Unit attribute.
- [x] **Web backend + Web frontend:** Add a **Specialist Troops filter**
  to the Unit Explorer using the shared published qualifier Rule.
  The selector distinguishes InfinityDB Standard from Domination, Supplies,
  and Firefight; resolves scenario overrides from the reviewed rules database;
  filters candidate Units by profile/loadout/Unit-option Skill occurrences;
  excludes Chain of Command (Non Specialist) through that Skill while
  retaining Units with another qualifying Skill; and intersects with existing
  filters without inventing permanent Unit facts. The browser explains
  candidate-vs-profile scope and links to the General Rule. API tests verify
  context validation and matching counts; Chromium at 1440/390px verifies
  filter combinations, clear/reset, and versioned URL persistence.
  See the [Unit filter semantics](data-model.md#current-scenario-foundation)
  and [web design contract](web-design-guidelines.md#specialist-troops-filtering-is-contextual).
- [x] **Data processing + Web frontend:** Establish a
  **text-first provenance distinction policy** for source-native
  Army/statline material, InfinityDB-maintained rules, explanations,
  reviewed examples, dated FAQ/errata and source conflicts. The shared
  rules renderer identifies maintained text, visibly labels sources
  and source-context notes, and separates reviewed examples. Dated FAQ
  publications have distinct treatment; competing citations display
  an explicit normal-mode discrepancy warning. Colors use existing
  light/dark semantic tokens with textual labels and borders rather
  than color alone. Node regressions cover interpretation/source roles
  and synthetic conflict evidence; Chromium covers the General Rules
  and Supplies FAQ pages at 1440/390px in both light/dark themes.
  No generic "recently updated" tag is inferred without a dated
  authoritative change. This defines the policy and applies it to
  shared Rule/FAQ surfaces; it is **not** a claim that every imported
  statline or historical erratum has been source-reconciled. See
  [visual provenance contract](web-design-guidelines.md#distinguish-rules-provenance-without-implying-new-authority).
- [x] **Web frontend:** Omit redundant rule-card subtitles when a card's
  heading is `Title` and its sole subtitle repeats `Rules for Title`.
  The shared renderer skips only the exact placeholder (optional period)
  without changing curated data, meaningful/linked summaries, facts,
  applicability, citations or source notes. Node DOM regressions cover
  ordinary/shared cards; real Chromium scenario acceptance at 1440px
  and 390px confirms the Supplies rule card has no redundant summary,
  retains facts and citations, and remains navigable. See the
  [web design contract](web-design-guidelines.md#curated-rules-text-hierarchy).
- [x] **Web frontend:** Show the **accuracy/independence disclaimer** in
  a floating section attached to the bottom of the viewport, **expanded by
  default** for each new browsing session. The shared shell uses native
  `details`/`summary` to collapse into an unobtrusive 44px icon-only
  control, with a session-scoped choice that survives reload and soft
  navigation without creating a persistent cookie or consent dependency.
  The non-affiliation and accuracy text still links to About/attribution,
  reserves a future feedback slot without an inactive control, and keeps
  room to scroll page-end content clear of the panel. Shared-shell tests
  cover normal routes; Chromium at 1440px, 390px, and 320px in both themes
  covers default visibility, viewport geometry, keyboard toggle, focus,
  collapsed size, mobile overflow, soft navigation, and reload.
  Native disclosure semantics provide accessible expanded/collapsed state;
  dedicated assistive-technology sign-off remains a final 1.0 task.
  See the [web design contract](web-design-guidelines.md#use-progressive-disclosure-for-secondary-information).

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

- [ ] Seek source corrections or clarification for the pinned Fireteam chart
  references disclosed under ARMY-01: 11 rows referencing eight exact slugs
  without Unit definitions (including three Combined Army Spec-Ops placeholders), ARJUNA's global-only
  match and KORSAN's FTO annotation without an FTO-named local loadout.
  Preserve chart names/annotations and uncertainty; do not create aliases or
  eligible options from similar names. The visible disclosure is locally
  accepted; an external publisher response is not a 1.0 prerequisite.

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
