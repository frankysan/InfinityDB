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
- **Disposition:** deferred; tracked by [cross-season ITS reuse](TODO.md#its-scenarios-and-game-tools).

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
- **Disposition:** proposed, outside the current implementation scope.
