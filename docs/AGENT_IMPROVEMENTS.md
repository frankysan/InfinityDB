# Agent improvement log

**Project domain:** Project infrastructure

Record actionable opportunities noticed during implementation, investigation,
validation, documentation review, or handoff. [TODO.md](TODO.md) tracks accepted
work. Recording a suggestion leaves the current task scope in place.

1. Check for an existing entry and update it if applicable. For a new entry,
   assign the next unused `AI-####` ID and keep the ID stable.
2. Record the affected files or instructions, the observation and available
   evidence, the proposed change, why it matters, and its disposition. Mark
   uncertainty explicitly and keep private evidence out of tracked files.
3. Use `proposed`, `deferred`, `accepted`, `implemented`, `declined`, or
   `superseded`. Update the disposition when it changes and link the relevant
   TODO item, commit, or decision. Retain earlier entries for reference.
4. Mention relevant new entries in the handoff. If the checkout is read-only,
   include the proposed entry in the handoff for a later authorized edit.

## Entries

Use one heading per entry with its ID and a short title. Include the date,
affected area, observation and evidence, proposed change, and disposition.

## AI-0001 — Normalize ITS scenario Skill facts

- **Date:** 2026-11-17
- **Area:** `data/curated/its/n5-its-season-18.json`, scenario/Skill read models.
- **Observation:** Twenty-six current ITS Short Skills were initially rendered
  as prose-only mission cards. The original paragraphs remain in the mission data
  for compatibility and provenance.
- **Implemented:** All 26 now have curated Requirements and Effects, with
  Restrictions, Clarifications, and Source context where applicable. Three
  actions have exact page pins supported by the existing reviewed source text;
  other actions retain clearly identified mission-range citations rather than
  invented action-specific pages. Rendering reuses the standard Skill card.
- **Why:** Player-facing rules become scannable without losing original clauses
  or obscuring known bilingual source differences.
- **Disposition:** implemented for structured facts. Exact pins for additional
  actions require further source-page verification; do not infer a page.

## AI-0002 — Check Core scenario Skill publication parity

- **Date:** 2026-11-17
- **Area:** Core curated rules and `rules_n5.db` generation.
- **Confirmed cause:** `RulesDatabase._compose_records()` intentionally
  filters scenario-scoped definitions when no scenario ID is supplied. The
  ordinary Skill catalog used that unscoped query and therefore omitted
  `skill:hack-consoles` and `skill:pick-up-supply-boxes`. This was not
  missing source data or a stale Rules database.
- **Implemented:** The scenario-aware catalog now includes those definitions
  from their existing Core scenario reference, retaining exact N5.3 citations,
  scoping, and the existing fail-closed unscoped Rules lookup.
- **Why:** Core scenario Skills now appear under Scenario-specific Skills and
  have working detail and Search routes without changing the Rules database.
- **Disposition:** implemented.

## AI-0003 — Integrate library-backed seasons into the complete build registry

- **Date:** 2026-11-17
- **Area:** `src/infinity_db/database_set.py`, integrated build tooling and ITS authoring.
- **Observation:** The opt-in ITS builder and standalone developer command
  accept a pinned shared scenario library, but the complete build registry
  still has only the unchanged ITS 18 source path. Registering a real
  library-backed season requires wiring its declared library input and hash
  through the complete-set build and provenance checks.
- **Proposed:** Extend season registration with an optional library input
  when a reviewed ITS 17/18 authoring migration actually needs it; keep
  present ITS 18 builds unchanged until then.
- **Why:** Prevent synthetic reuse capability from being mistaken for a
  deployed, integrated multi-season publication pipeline.
- **Disposition:** implemented as opt-in complete-set registration, matched
  provenance and deployment freshness checks. Validated using synthetic
  ITS 17 source and library; actual ITS 17 publication remains separate.

## AI-0004 — Reconcile stale publication-registry regression expectations

- **Date:** 2026-11-17
- **Area:** `tests/test_publication_registry.py` and scenario Skill/marker provenance.
- **Observation:** Two checks failed in the extended registry suite: deleting the
  ITS English source now triggers `Missing ITS Skill source` before the older
  expected marker-diameter error, and the frozen Battleground API/SVG checksum
  no longer matches. Neither path uses the new opt-in shared scenario library;
  the source-freeze expectation likely predates recent scenario Skill output.
  A clean-base comparison was attempted, but its isolated worktree lacked the
  project virtual environment, so baseline status is not independently proven.
- **Proposed:** In a separate focused task, verify the current pre-change
  baseline and update error-order assertions or freeze evidence only when the
  changed output is established as expected. Never overwrite golden hashes
  without comparing the actual response differences.
- **Why:** Keep regression tests meaningful without folding unrelated output
  changes into cross-season reuse development.
- **Disposition:** partially addressed. The registered ITS 18 golden digest
  now reflects the current reviewed scenario action-card output: independent
  parity passes for six JSON variants and 24 SVG variants. The previously
  observed marker-source error-order issue did not reproduce in hosted CI;
  retain the strict source rejection checks.

## AI-0005 — Project shared records after source-family revision selection

- **Date:** 2026-11-17
- **Area:** `its_source_family.py`, `curated.py`, and shared ITS build registration.
- **Observation:** Current ITS source-family projection requires exact
  `factRevisions.records` coverage of the record array. Shared scenario
  definitions are materialized before this check, so a future library-backed
  source-family migration must define how imported membership records receive
  applicable revision tags without losing archived source-local facts.
- **Proposed:** Integrate version-pinned memberships with the source-family
  projector, separating revision-specific publication bindings from shared
  authoring definitions while retaining source hashes and historical overrides.
  Test a current plus archived revision before migrating real ITS 17 data.
- **Why:** The synthetic standalone reuse proof does not establish the
  one-source-family revision-history contract for future season migrations.
- **Disposition:** partially addressed: synthetic current and archived source
  projections preserve exact revision tags and references when one scenario
  is imported. Optional complete-set library registration and its
  matched provenance checks are implemented; real ITS 17 curation remains
  [pending](TODO.md#its-scenarios-and-game-tools).

## AI-0006 — Reconcile the runtime semantic snapshot with current ITS publication

- **Date:** 2026-11-17
- **Area:** `tests/fixtures/runtime-semantic-baseline-v1.2-current.json`
  and `tools/runtime_semantic_baseline.py`.
- **Observation:** After a validated source-fresh rebuild, the default semantic
  baseline requests archived `its-18@2026.09.01` Battleground and receives
  the intentionally fail-closed 404. The separately named v1.2-current
  baseline reports five differences in Skills and Scenario API responses;
  their exact cause has not been established. The current database-set and
  deployment-asset checks pass.
- **Proposed:** Compare the stored payloads with the current reviewed API
  responses and the last known accepted revision, then refresh the canonical
  baseline only for confirmed intentional publication changes.
- **Why:** Historical and stale baseline snapshots should not create ambiguous
  failures or motivate unreviewed changes to serving behavior.
- **Disposition:** addressed for the current ITS 18 publication. A fresh
  41-path capture was compared field-for-field to the previous snapshot:
  exactly five Skill/Scenario API digests changed, while 36 paths (including
  the SVG response) remained unchanged. The current v1.2 fixture was
  refreshed with those five reviewed digests and exact selected database
  identities. Historical v1 and v1.2 source-baseline fixtures were not altered.

## AI-0007 — Publish ITS season-wide Skills without fabricated scenario bindings

- **Date:** 2026-11-17
- **Area:** ITS curated season source, shared Skill bindings, Skill catalog and Search.
- **Observation:** The official ITS 18 2026.09.11 publication defines four
  season-wide Skills outside specific scenario action lists: CivEvac
  (Common Skill, pp. 22-23), Casevac (Common Skill, p. 25),
  Team-Ops (Special Skill, p. 30), and Request a Tacball
  (Short Skill, pp. 30-31). Casevac State (pp. 25-26) is a separate
  state. Team-Ops additionally names the optional tournament Extra
  (p. 29), which governs applicability of the Team-Ops Skill and
  Request a Tacball. The current shared Skill binder requires nonempty
  scenario IDs, so none of these can be represented correctly by
  attaching it to an arbitrary scenario. The ITS 18 curated source
  currently mentions several mechanics without publishing their
  standalone definitions.
- **Proposed:** Support exact season/revision Skill memberships independent
  of scenarios, with optional Extra applicability, versioned source
  citations and full Requirements/Effects/Restrictions. Publish one
  canonical card per Skill in catalog/Search; connect only genuine
  scenario usages. Preserve Casevac State as a separately linked state.
  Evaluate cross-ITS reuse against actual older documents rather
  than assuming names imply identical mechanics.
- **Why:** A season-wide source definition should not be duplicated
  across missions, hidden because it lacks scenario membership, or
  presented as an unconditional Skill outside an optional tournament Extra.
- **Disposition:** implemented for four current ITS 18 standalone Skills
  with revision-specific source citations, catalog/Search publication,
  optional-Extra applicability and synthetically validated cross-season
  `sharedSeasonSkillBindings`. Casevac State has now also been published
  independently with exact page pins and reciprocal Skill links; see
  [ITS season database](its-season-database.md).

## AI-0008 — Resolve maintained-text references across selected publications

- **Date:** 2026-11-17
- **Area:** State/Skill catalog and maintained-text reference resolution.
- **Observation:** Maintained-text references previously looked up every Skill
  and State in the N5 Rules database, so a valid ITS-owned
  `[[state:casevac]]` or `[[skill:casevac]]` link would fail during API
  enrichment even when the selected ITS database published that record.
- **Implemented:** The maintained-text resolver now accepts an explicit map of
  registered ITS rule records on relevant Skill/State detail surfaces.
  It preserves the core resolver's normal behavior and fails closed for
  missing references. Casevac and Casevac State link bidirectionally.
- **Potential follow-up:** If additional non-core publications use maintained
  semantic links in more catalog surfaces, centralize publication-aware
  resolution with strict owner/revision disambiguation rather than extending
  each route independently. No extra abstraction is needed for the current
  one-season use case.

## AI-0009 — Model historical ITS Skill declarations without implicit equivalence

- **Date:** 2026-11-18
- **Area:** ITS source curation, season Skill type vocabulary and cross-season Skill catalog.
- **Observation:** Official ITS 17 V0.2 labels CivEvac and Casevac as
  Short Movement Skills, but ITS 18 2026.09.11 labels them Basic Short
  Skill and Short Skill respectively. The current ITS type validator
  supports the latter classifications, not the historical label. ITS 17
  Outbreak also changes objectives/point values relative to ITS 18.
- **Proposed:** Before real ITS 17 publication, represent the original
  Skill category faithfully, resolve distinct-version public Skill
  identities without treating common names as semantic equivalence, and
  select reusable scenario components by verified facts rather than name.
  Do not collapse the differently scored Outbreak objective lists.
- **Why:** Importing ITS 17 through the ITS 18 type vocabulary would
  silently change the older source; reusing its newer Skill version would
  misstate published movement/action semantics.
- **Disposition:** partially implemented: historical `short-movement-skill`
  validates and displays through the ITS-only season Skill path without
  modifying the N5 core matrix. Synthetic cross-season type-variant
  consolidation rejection and current ITS 18 CivEvac scenario exceptions
  have regression coverage. Resolving distinct-version public routes and
  full source-reviewed ITS 17 curation remain open under
  [ITS scenarios and game tools](TODO.md#its-scenarios-and-game-tools).
