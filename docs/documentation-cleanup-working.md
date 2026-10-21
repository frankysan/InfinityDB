# Documentation cleanup working audit (temporary)

**Project domain:** Project infrastructure

**Status:** Temporary working document, not a canonical reference or a release deliverable.
**Initial audit baseline:** `dev/v1.0.0` at `ab028309a68d3755b6e615d455db01b7dac811b6`, 2026-10-20.
**Closeout-pass baseline:** `dev/v1.0.0` at `bced9f73318d5674b5f631821ba617bdfcaa30ce`; Batches 1–5 already committed and working tree clean before the closeout pass.
**Scope:** Documentation structure and selected repository/code/configuration claims. This is *not* the mandatory exhaustive, page-by-page pre-release audit.

This tracked temporary document exists to coordinate bounded edits. The connected workspace
tool cannot create ignored `local/audits/` files; this is a working-tree placeholder,
not a new permanent documentation owner. Before finishing the overall cleanup, transfer
any outstanding tasks to the canonical owners, preserve distinct source evidence, and
remove this document. Do not commit it as permanent public project documentation.

## Guardrails

- The ownership map in `docs/README.md` remains authoritative. Keep architecture,
  data semantics, curated schema, browser design, CI, operations and release contracts
  in their respective owner documents; avoid a second specification here.
- Distinguish **current implementation**, **accepted design direction**, **open work**
  and **frozen historical evidence**. Do not convert old test results or source
  disagreements into current acceptance claims.
- Preserve source identities, PDF pages, exact Wiki revisions, REA/RS/RR IDs and
  meaningful unresolved conflicts. Move unique evidence before retiring an audit.
- `docs/CHANGELOG.md` is parsed by `src/infinity_db/web/release_notes.py` and
  packaged by `pyproject.toml`; preserve its heading/section grammar.
- `docs/rules-interaction-checklist.md` is generated and verified by
  `tools/audit_rules_interactions.py`; never hand-edit or remove it.
- Keep new private evidence in ignored `local/audits/`; old ignored
  `docs/audits/` and `reports/` remain supported for compatibility.
- Make small changes, run the relevant standard checks, review diffs and Git status,
  and leave all edits unstaged/uncommitted.

## Findings, by priority

### P0 — Canonical testing guide contains dated audit history

**File:** `docs/testing.md` (~3,288 lines). The first ~365 lines provide useful
check-runner, pytest, assets, benchmarks and reporting contracts. A large later
portion accumulates dated 1.0 test/Chromium results, individual REA cases, historical
counts and private evidence paths.

**Action:** Keep repeatable command contracts, reusable test slices and the
distinction between hermetic/optional browser acceptance. Condense or retire
run-specific narratives only after ensuring any unique rule/source finding remains
in curated data, rules semantics/research, or the frozen audit. Do not treat an
earlier browser run as ongoing release acceptance.

### P0 — Unreleased changelog is too detailed

**File:** `docs/CHANGELOG.md` (~1,546 lines; Unreleased ~627 lines).
Many related Weapon/Deployable/rules changes are repeated as separate implementation
or test-history entries.

**Action:** Consolidate *outcomes* for players/operators into coherent entries,
retaining explicit compatibility/upgrade consequences and the parser's grammar.
No release-version history rewrite without separate approval.

### P1 — Backlog contains completed implementation diaries

**File:** `docs/TODO.md` (~2,436 lines; ~243 checked and 155 unchecked
items in the audited snapshot).

**Action:** Keep checked prerequisites only while their parent remains open.
When a parent is closed, promote unique decisions to canonical documents, remove
completed standalone task narration, and leave actionable dependencies/acceptance
for open work. Keep 1.0 and post-1.0 scopes distinct.

### P1 — Rules research and reviewed semantics overlap

**Files:** `docs/rules-research.md` (~2,118 lines) and
`docs/rules-semantics.md` (~5,017 lines).

**Observed examples:** `RR-AW-IMM-002` and `RR-AW-IMM-003` already describe
implemented `skill:immunity` cases and refer to `RS-AW-IMM-001`.
`RR-WPN-FAMILY-001` blends source evidence with current runtime/browser
implementation detail.

**Action:** Review each case for promotion, short cross-reference, or historical
retirement. Keep evidence and conflicts, but do not maintain the same current
contract in research and semantics.

### P1 — Frozen rules audit and appendices need eventual closeout

**Files:** `docs/rules-explanation-audit-1.0.md` and its three appendices
(~4,378 lines total). These reference explicit older commits, contain frozen
denominators, detailed provenance and follow-up decisions.

**Action:** Retain until current 1.0 review is reconciled. At closeout, preserve
unique source manifests/conflicts and any stable identifiers needed by other
documents. Remove obsolete audit process diaries through Git history only after
link and provenance review.

### P2 — Agent context duplicates reference contracts

**File:** `docs/AI_CONTEXT.md` (~353 lines).
Retain non-obvious cross-layer invariants and links; replace routine restatement
of data-model, browser, symbols, release and check contracts with owner links.

### P0 — Private evidence location is inconsistent

**Files:** `docs/README.md` and `AGENTS.md` prefer `local/`;
`docs/releasing.md` around line 147 says raw evidence belongs under
`docs/audits/`; `docs/TODO.md` around line 91 offers
`reports/` or `docs/audits/` without the current canonical path.

**Action:** Align new private audit evidence on `local/audits/`, preserving
legacy paths for compatibility. Avoid treating Git ignore rules as access controls.

### P2 — Markdown checks do not enforce reference integrity

**Current:** The `docs` stage invokes Markdownlint. It does not establish
local link/anchor correctness, documentation ownership or current-value parity.

**Action:** Add a small offline integrity check for changed path/anchor references
and selected canonical/version/workflow claims, registered through the existing
check runner. No new network dependency.

## Documents to retain as distinct canonical owners

`docs/README.md`, `docs/architecture.md`, `docs/data-model.md`,
`docs/application-domains.md`, `docs/project-domains.md`,
`docs/web-design-guidelines.md`, `data/README.md`,
`data/curated/README.md`, `docs/ci.md`, `docs/deployment.md`,
`docs/server-migration.md`, and `docs/releasing.md`.
Prefer targeted fixes rather than merging these.

## Execution log

- [x] Inventory docs and inspect representative code/configuration links; identify
  high-value consolidation candidates and existing doc owners.
- [x] **Batch 1:** Normalize private-audit guidance in `docs/releasing.md`
  and `docs/TODO.md`. Consolidate the dated Ammunition, Labels and General
  Rules acceptance subsections of `docs/testing.md` into one reusable
  verification contract, preserving their exact commands, observed coverage
  and historical success results while reducing repeated narrative.
- [x] **Batch 2:** Consolidate the States, Hacking Programs and Traits
  source/API/browser verification sections in `docs/testing.md` into a
  reusable test/verifier index, retaining their distinct source owners and
  old acceptance results explicitly as dated evidence.
- [x] **Batch 3 (first pass):** Consolidate repeated `Unreleased`
  Weapon-review, rules-reference acceptance and player-summary entries;
  preserve player-facing outcomes, source disputes, parser structure and
  all released-version notes. Remaining high-level summary polish is
  part of the final release-note review.
- [x] **Batch 4 (first pass):** Remove the fully completed standalone
  Trait Wiki-link implementation diary after checking canonical documentation
  and regression coverage. Condense completed cross-surface browser acceptance
  details to a dated, scoped evidence summary, preserving the final 1.0 gate
  and all its remaining unchecked requirements.
- [x] **Batch 5 (first pass):** Replace two already-implemented Immunity
  research entries with stable-ID forwarding notes to their semantic owner;
  reduce duplicate agent-context detail; and add an offline local Markdown
  path/heading validator to the standard documentation stage with tests.
  Further research promotion remains part of release closeout.
- [ ] **Release closeout:** Verify complete documentation corpus against current
  code, tests, package, CI and player-facing routes; settle frozen evidence
  retention, and retire this temporary working document.
  - [x] First-pass evidence disposition: retain the frozen 1.0 audit and its
    three appendices while the source-to-browser gate remains open, preserving
    REA IDs, exact source hashes/revisions and unresolved official conflicts.
    Make the main audit's 2026-10-09 findings explicitly historical rather
    than treating resolved cases as current blockers.
  - [x] Reconcile selected current-state statements against release metadata,
    app-domain ownership, docs-stage code/CI, and TODO; correct the REA-020
    acceptance wording and update docs-stage references.
  - [x] Expand offline link validation from the original hand-picked Markdown
    locations to all Git-tracked Markdown, including nested references, while
    retaining coverage of untracked docs drafts and a source-archive fallback.
    This validates links/anchors, **not** the text's current semantic accuracy.
  - [x] Reconcile the scenario publication claims with the current curated
    collection and executable catalog/API contracts: four N5.3 Core missions
    plus the current ITS Season 18 Battleground pilot. Correct outdated
    core-only statements without widening mandatory 1.0 scope.
  - [x] Distinguish published FAQ v0.1 review and API functionality from
    remaining FAQ source/applicability review; separate in-scope N5 reference
    completeness from optional full ITS season/historical publication.
  - [x] Clarify source-only variant inventory baselines, separating
    tracked release rules.db (41 unresolved Skill source IDs) from
    current curated rules rebuilt for review (38 unresolved), with
    the optional raw-archive test and CI limitations stated explicitly.
  - [x] Reconcile pinned source-field occupancy against represented Unit
    options/notes; keep the release-only raw-source gate explicit.
  - [x] Promote the completed non-Skill Army browser study's durable
    source-to-API and page-bootstrap checks from ignored local scripts into
    maintained tests, without claiming client-rendered Chromium coverage.
  - [x] Promote the seven-case non-Skill Army Chromium acceptance procedure
    to an optional maintained verifier; retain historical browser results
    separately and require new evidence on the actual release candidate.
  - [x] Promote source Unit notes and composite Unit options to maintained
    source-to-API parity tests, preserving source contexts and exact
    included-loadout relationships while leaving browser acceptance separate.
  - [x] Add regression coverage for normal-route disclosure of a bounded
    selection of unresolved official source conflicts, preserving the
    adjudication and live-browser gates separately.
  - [x] Add cross-surface Scenario/FAQ scope tests across the four Core missions and the ITS Battleground pilot; correct the published FAQ ruling count.
  - [x] Add a whole-published-graph API destination regression for
    catalog-backed cross-domain rule links.
  - [x] Verify published embedded Glossary hashes and Weapon-hosted
    rule-card fragments against actual published identities.
  - [x] Check same-page rule-card links for seven published Mine-family
    Weapon pages against their hosted rule records, preserving
    final Chromium fragment navigation as separate acceptance.
  - [ ] At actual 1.0 preparation, review the tracked Markdown corpus
    for factual accuracy (not merely valid links/anchors), source/API/browser
    claims, pending REA and exact source dispositions, and the final
    player-facing release summary. Retire this working document only after
    moving any unresolved documentation tasks to `docs/TODO.md` and
    preserving unique sources in their canonical owners.

### Batch validation log

- **Batch 1, 2026-10-20:** `docs/testing.md` condensed three adjacent
  catalog-specific sections into one; `docs/releasing.md` and `docs/TODO.md`
  now prefer `local/audits/` for new private audit evidence. No code, curated
  data, generated checklist, changelog or release-facing behavior changed.
- **Checks:** `tools/run_checks.py --stage docs` — PASS, 32 Markdown files,
  0 issues; `tools/run_checks.py --stage test tests/test_application_rule_references.py`
  — PASS, 15 tests. No Chromium browser acceptance or full suite attempted;
  those are not implied by the old dated pass counts.
- **Batch 2, 2026-10-20:** Collapsed 99 lines of separate State,
  Hacking Program and Trait verification narratives to 49 lines of common
  procedure with domain-specific source/contracts and all three exact
  browser verifier commands. Preserved published population checks (24
  States, 12 Programs, 33 Traits), 2026-10-19 browser results (72/72,
  36/36, 99/99), and the distinction between the separate 33/33 saved-Wiki
  Trait-anchor check and normal Trait catalog navigation. No other source
  evidence or reference document was moved.
- **Focused tests:** `tests/test_state_catalog.py` — 4 passed;
  `tests/test_hacking_program_publication.py` — 1 passed;
  `tests/test_trait_wiki_references.py` — 22 passed. No live browser
  acceptance or full project suite was run.
- **Batch 3, 2026-10-20:** Reduced `docs/CHANGELOG.md` by 90 lines
  (1,546 to 1,456) across three `Unreleased` hunks only. Grouped a
  deployable/Mines/Deactivator-heavy portion of the Player summary into
  five outcome-oriented entries; six incremental shared-Weapon source
  review entries into one; and nine REA implementation/acceptance notes
  into three player-visible rule-reference improvements. Kept the source
  disagreements (Katyusha, Eclipse, AP Thunderbolt, archived Saving
  Rolls, Flash Pulse), remaining non-Allied eligibility question and
  exact variant/parameter boundaries. Removed obsolete intermediate
  remaining-review counts without changing underlying rules evidence.
- **Checks:** `tests/test_release_notes.py` — 18 passed;
  `docs` Markdownlint — 32 files, 0 issues. The `Unreleased`
  heading and all Added/Changed/Fixed headings remain valid; first
  released version is still `0.10.1` dated 2026-10-10. No application
  runtime, player-route or release packaging changes were made.
- **Batch 4, 2026-10-20:** Reduced `docs/TODO.md` from 2,437 to
  2,344 lines (93 lines). Removed one fully completed, standalone
  Trait-to-Wiki mapping implementation diary after verifying the
  permanent contract in `docs/data-model.md`, the exact mapping
  `config/catalogs/trait-wiki-references.json`, and maintained
  `tests/test_trait_wiki_references.py`. The distinct 33/33 saved
  Wiki-anchor and current-development-server browser acceptance remain
  documented with their limits under `docs/testing.md`.
  Condensed the four completed browser acceptance slices and nested
  Weapon-family navigation into bounded historical evidence:
  93/93, 51/51 source paths, 49 Glossary concepts, 42/42 navigation,
  167/167 Fireteams, 805/805 core scenarios, and 469/469
  Visibility Zone/Ammunition/Immunity. Kept the canonical Mines
  route, responsive checks, source limitations and unresolved
  REA-020/Domination dependencies; retained the open final 1.0
  acceptance parent and every unchecked requirement.
- **Checks:** `docs` Markdownlint — PASS, 32 files/0 issues;
  `tests/test_trait_wiki_references.py` — PASS, 22 tests. No
  fresh browser acceptance or full project test suite attempted.
- **Batch 5, 2026-10-20:** Reviewed and condensed implemented Immunity
  research entries `RR-AW-IMM-002/003` into stable-heading forwarding
  notes; `docs/rules-semantics.md` RS-AW-IMM-001 and curated
  `skill:immunity` already own the explicit/derived cases and
  unresolved source conflicts. The research IDs, their original
  source revision identities, and caveats remain discoverable.
  `docs/AI_CONTEXT.md` was reduced from 353 to 328 lines by
  forwarding detailed Immunity and scenario mechanics to their
  canonical owners while retaining non-obvious boundaries.
- **Documentation integrity:** Added `tools/check_doc_links.py`
  (ordinary inline/reference Markdown links, relative files and
  GitHub-style heading anchors, including duplicate headings; no
  network requests or application-route checking), registered
  `tests/test_doc_links.py`, and appended this check to the existing
  `docs` stage after Markdownlint using the check-runner Python.
  Fixed the initial checker bug affecting the two hyphens
  produced by punctuation removal around an em dash; existing
  Immunity anchor links were correct and unchanged.
  `docs/testing.md` now documents the stage's full contract.
- **Checks:** 4 doc-link tests, 33 check-runner tests and 2
  test-registration tests passed (**39 focused tests**).
  Ruff passed for changed Python sources/tests;
  Pyright reported **0 errors/0 warnings**; the `docs`
  stage passed Markdownlint (**32 files, 0 issues**) and
  the offline link scan (**28 maintained files, 0 errors**).
  No full project suite, live browser acceptance, or external
  URL verification was performed.
- **Closeout pass 1, 2026-10-20:** The five earlier cleanup batches were
  committed at the current base `bced9f73318d5674b5f631821ba617bdfcaa30ce`.
  Verified the frozen main rules audit and its inventory, bilingual N5.3
  reconciliation and source manifest retain distinct REA IDs, original
  counts, exact source hashes/revisions and publication conflicts.
  **Decision:** keep all four until the 1.0 source-to-browser release
  review is finished and any durable evidence is migrated; do not treat
  original October 9 findings/remediation priorities as current defects.
  Clarified the main audit's historical scope, preserved its stable
  headings/citations, and expanded the `docs/README.md` ownership note.
- Reconciled `RR-WPN-FAMILY-001` as retained hash-pinned source evidence
  with implemented Weapon/Trait consumers rather than a wholly open
  research task; corrected the REA-020 Fireteam comment in `docs/TODO.md`
  to distinguish resolved scoped rule guidance from the still-open
  full 1.0 acceptance. Updated `AGENTS.md`, `docs/ci.md` and the
  `Unreleased` changelog's documentation-check entry to reflect
  **Markdownlint plus offline local file/heading link checks**.
  Cross-checked current release metadata (`pyproject.toml` 0.10.1),
  public README/milestone, app-domain registry, CI and package-facing
  documentation without changing application/runtime code.
- **Validation:** `docs` — PASS (Markdownlint 32 files, 0 issues;
  offline links 28 files, 0 errors); `tests/test_release_notes.py`
  — 18 passed; `tests/test_doc_links.py` — 4 passed.
  No full project tests or live browser/source publication acceptance.
- **Remaining:** The release-mandated exhaustive whole-repository Markdown
  and browser-copy/source completeness audit is **not complete**.
  A final REA disposition and source-hash migration, further research
  ownership review, current player-summary reconciliation, and disposal
  of this temporary working file remain conditional on final 1.0
  evidence; do not equate this cleanup with a release gate pass.
- **Closeout pass 2, 2026-10-20:** After the separate raw-Army CI
  fixture fix was committed and the user confirmed CI green,
  expanded `tools/check_doc_links.py` to scan all Git-tracked Markdown
  via read-only `git ls-files`, rather than selected directory roots.
  New untracked `docs/*.md` files are included before staging; an
  archive without Git falls back to canonical reference locations.
  Git-ignored `AGENTS.local.md` is no longer a required input.
  Updated the testing contract and added two fixture tests for nested
  tracked docs, ignored local data and the no-Git fallback.
- **Validation:** `tests/test_doc_links.py` — 6 passed; Ruff passed for
  the tool and test module. The `docs` stage passed Markdownlint
  (32 files, 0 issues) and the expanded offline links scan
  (30 files, 0 errors). This still does not verify source-to-browser
  content completeness, resolve remaining 1.0 REA cases, or authorize
  retirement of this temporary checklist.
- **Closeout pass 3, 2026-10-20:** Found a concrete stale publication
  statement in `docs/data-model.md`: its old text claimed only
  `n5-core@5.3` was available and an explicit ITS 18 selection
  returned no missions. Reviewed current curated
  `n5-its-season-18-2026.09.01.json` publication through the
  `ScenarioCatalog`, its API test fixture and actual
  `scenarios.js` collection selector. The modeled current sets
  are **four Core missions** and **one ITS 18: Overheat Battleground**
  at `its-18@2026.09.01`. Battleground supports six Army Points
  sizes, three end-of-game Sectors and official source citations
  on printed ITS pp. 121–123. Explicit collection selection
  never falls back to Core, and the default remains Core-only.
- Updated the current-state sections of `docs/data-model.md`,
  `docs/application-domains.md`, `docs/architecture.md`,
  `docs/AI_CONTEXT.md`, and `README.md`. This is a **factual
  publication correction**, not an expansion of the mandatory 1.0
  scope: other ITS missions, tournament tooling and the scenario
  editor remain outside that gate.
- **Checks:** `tests/test_scenario_catalog.py` — **43 passed**;
  `tests/test_scenario_api.py` — **72 passed**;
  `docs` — Markdownlint **32 files, 0 issues** and offline links
  **30 files, 0 errors**. The complete 1.0 source-to-browser and
  live Chromium release audits remain separate open work.
- **Closeout pass 4, 2026-10-20:** Reconciled two contradictory FAQ
  publication statements against `n5-faq-v0.1.json` (current curated
  FAQ collection, 27 reviewed rulings), `faq_rulings.py`, and
  `RulesDatabase.faq_rulings_for_topic`. `docs/data-model.md` no longer
  labels the entire FAQ layer "not yet published"; it retains the
  limitations of the explicit date/rules-revision context API.
  `docs/TODO.md` now marks registration of the FAQ collection as
  complete, while preserving a separate unchecked source-hash,
  remaining-FAQ coverage and core/ITS applicability audit.
  Corrected the generic "future 1.0 work" statement to explicitly
  exclude a full ITS season/history library from the mandatory 1.0
  gate. Existing separate ITS Battleground publication is unaffected.
- **Validation:** `tests/test_faq_ruling_references.py` — **60 passed**;
  `tests/test_curated.py` — **227 passed**;
  `tests/test_rules_database.py` — **136 passed**;
  `docs` — Markdownlint **32 files, 0 issues** and offline links
  **30 files, 0 errors**. No application code or curated data changed;
  full suite, browser and external source-content audit remain open.
- **Closeout pass 5, 2026-10-20:** Reconciled
  `docs/data-model.md`'s source-parameter inventory with the
  actual `tools/audit_source_variant_inputs.py` and three raw-archive
  test modules. Pinned Army source contains 96 Skill IDs (33,153
  direct relationship rows) and 34 Equipment IDs (5,427 direct
  relationship rows). The **tracked release rules.db** leaves 41
  Skill and 14 Equipment IDs unresolved; a **temporary rules.db
  rebuilt from current curated source** recognizes the reviewed
  Mimetism, Berserk and Dodge extras, leaving 38 Skill IDs
  unresolved. No public cross-Army Unit usage index is implemented.
  Clarified these two inventories and the regeneration prerequisite
  in `docs/data-model.md` and `docs/TODO.md`.
- **CI limitation:** `infinity.raw.db` is Git-ignored, so the
  three source-occurrence suites skip on clean hosted CI; only
  a local run with paired raw/application storage certifies
  the pinned raw signature counts. The existing source-only
  regression contract and its failing-on-malformed-archive
  behavior remain unchanged.
- **Checks:** `tests/test_audit_source_variant_inputs.py`
  — **7 passed**; `tests/test_other_source_variant_provenance.py`
  — **4 passed**; `tests/test_martial_arts_variant_provenance.py`
  — **2 passed**; `docs` — Markdownlint **32 files, 0 issues**
  and offline links **30 files, 0 errors**. No runtime
  database regeneration, code, or curated source edits.
  The remaining source signatures and full 1.0 release
  completeness gate are still open.
- **Closeout pass 6, 2026-10-20:** Compared the current
  `tools/audit_source_presentation.py` policy and
  `tests/test_audit_source_presentation.py` to the pinned
  2026-10-15 private source-presentation report. It covered
  70 source tables, 441 fields, 39 potentially unrepresented
  fields, and **zero observed populated fields** in that
  pinned application/raw export. Seven direct composite-option
  relationship/extras source tables had no rows; Profile and
  Profile-group notes were empty. These are not the separately
  represented 18 composite-option occurrences (seven Units)
  or 30 Unit notes (28 logical Units). The two out-of-scope
  families retain explicit reasons rather than being treated
  as missing reference facts. Clarified those distinctions
  in `docs/data-model.md` and `docs/TODO.md`, and explained
  synthetic-versus-source evidence in `docs/ci.md`.
- **Checks:** `tests/test_audit_source_presentation.py`
  — 11 passed; `tests/test_run_checks.py` — 33 passed;
  Markdownlint — 32 files, 0 issues; offline docs links —
  30 files, 0 errors. The 1.0 release-only occupancy gate
  itself was **not executed** against a freshly regenerated
  release-candidate pair; this bounded documentation audit
  does not certify final source completeness.
- **Closeout pass 7, 2026-10-20:** Promoted permanent checks from the
  ignored `local/audits/verify_non_skill_army_browser.py` study.
  The new `tests/test_non_skill_army_presentation.py`, registered
  in the web test section, uses only tracked `infinity.db` and
  `rules.db`. It verifies **72 distinct Unit/source identity pairs**
  drawn from Army source Skill IDs 254/273/266/258/282/280:
  Gizmokit/MediKit/Bangbomb → Equipment, Regular → Training,
  Infinity Team Ops → source markers, and BTS=3 → Attribute
  overrides. All pairs must remain correctly classified in the
  normal Unit API, not the player-facing Skills bucket.
  Seven representative Unit HTTP routes and their general-profile
  APIs are also checked, including Raoul Spector; known Equipment
  routes must resolve. The initial failed test correctly exposed
  the test's mistaken assumption that `.general-profile` was
  server-rendered; Unit detail DOM content is populated by `unit.js`,
  so the test was corrected to check the served bootstrap and API
  instead. Historical **21/21 Chromium** checks at 1440/390/320 px
  remain separate evidence, not tests run by hosted CI.
- **Validation:** New tracked suite — **8 passed**; section
  registration — **2 passed**; Ruff for new test — PASS; Pyright
  — 0 errors, 0 warnings. Updated `docs/testing.md` and
  `docs/TODO.md` without marking the full 1.0 source-to-browser
  release gate complete.
- **Closeout pass 8, 2026-10-20:** Added the maintained optional
  `tools/verify_non_skill_army_browser.py`, replacing dependence on
  ignored `local/audits/verify_non_skill_army_browser.py` for future
  repeatable Chromium acceptance. The verifier exercises seven published
  Unit cases at 1440/390/320 px against a supplied current development
  server, checks API classification, client-rendered detail rows, valid
  Equipment destinations, missing bogus Skill links, JavaScript errors
  and horizontal overflow. Output is optional and intended for
  `local/audits/`; it is **not** part of routine CI and no new live
  browser run was performed in this pass. Added two hermetic tests
  for manifest/API-fixture parity and general/Army-local bucket
  extraction; maintained API suite is now 10 tests. Updated the
  operator command in `docs/testing.md` and the bounded TODO note.
- **Checks:** `tests/test_non_skill_army_presentation.py` — 10 passed;
  Ruff — passed for both modified Python files; Pyright —
  0 errors, 0 warnings. Final docs check and working-tree review
  recorded separately before handoff.
- **Closeout pass 9, 2026-10-20:** Confirmed the maintained optional
  Chromium verifier's new ignored `current.json` report contains
  **21/21 passing cases** across seven Units and all three widths.
  This is current development-server evidence, not final release-candidate
  certification. Added `tests/test_unit_source_options_notes.py`
  and registered it under the maintained web section. Its two tests
  compare **30 source Unit notes on 28 logical Units** and **18
  composite options on seven logical Units** in tracked `infinity.db`
  against normal Unit detail APIs. They enforce note text/representative
  attribution, source option identity, Points/SWC, miniature counts,
  ordered Order details and exact Army-local included-loadout IDs and
  quantities, rather than treating any presentation as sufficient.
  Updated `docs/testing.md` and `docs/TODO.md`; the ignored raw
  archive, wider 1.0 source-to-browser gate and final Chromium
  candidate run remain separate release obligations.
- **Checks:** `tests/test_unit_source_options_notes.py` —
  **2 passed** (including exact inclusion-set parity);
  `tests/test_non_skill_army_presentation.py` — **10 passed**;
  `tests/test_test_sections.py` — **2 passed**;
  Ruff on the new module — PASS; Pyright — **0 errors, 0 warnings**;
  `docs` — Markdownlint **32 files, 0 issues**, and offline
  Markdown links **30 files, 0 errors**. No full project suite,
  new Chromium run, or final raw-source gate was performed.
- **Closeout pass 10, 2026-10-20:** Added maintained web regression
  `tests/test_source_conflict_publication.py` and registered it
  under the web section. The five tests cover the published
  Armed Turret S1/S2, Dodge ARM+3, Special Dice Spanish reminder
  and Morat Fireteam Level 3 printed-source conflicts: normal
  API/page routes, preserved unresolved source notes, matching
  structured text-token rows, English/Spanish citations, and
  retained client source-note rendering paths. This protects
  the **disclosure of disputes**, not a source-precedence ruling
  or live Chromium acceptance. Flash Pulse and the separately
  mode-scoped Kobra CC dispute already have dedicated weapon
  API regressions; no duplicate rules decision or curated edit.
  Updated `docs/testing.md` and `docs/TODO.md`, leaving
  external REA errata and final 1.0 completeness open.
- **Validation:** `tests/test_source_conflict_publication.py`
  — **5 passed**; `tests/test_test_sections.py` —
  **2 passed**; existing `tests/test_weaponry_catalog_api.py` —
  **185 passed**; Ruff on the new module — PASS; Pyright —
  **0 errors, 0 warnings**; `docs` — Markdownlint
  **32 files, 0 issues**, offline links **30 files, 0 errors**.
  No full-suite or live-browser release-candidate acceptance was run.
- **Closeout pass 11, 2026-10-20:** Added six Scenario/FAQ API scope tests for four Core missions and ITS Battleground. Annihilation's Ancillary FAQ requires explicit matching context; unrelated scenarios receive no overlay. Base scenario definitions and client collection/season context remain separate. Corrected the current FAQ publication count to 28 (9 v0.1-origin, 19 carried forward). Full source adjudication and live browser acceptance remain open.
- **Validation:** Scenario API 78 passed; FAQ 60 passed; Ruff and Pyright passed; docs 32/0 and links 30/0. Full suite and Chromium not run.
- **Closeout pass 12, 2026-10-20:** Added tracked cross-domain rule-link destination tests against current composed rules and the normal detail APIs. Catalog routes are checked without inventing links for source-only variants. Glossary and in-card anchors and full browser acceptance remain separate.
- **Checks:** relation destination test: 1 passed; test registration: 2 passed; Ruff passed; Pyright 0 errors/0 warnings; Markdownlint 32 files/0 issues and local links 30 files/0 errors. Full suite and Chromium were not run.
- **Closeout pass 13, 2026-10-20:** Extended the previously committed
  `tests/test_public_relation_destinations.py` with embedded Glossary
  hash/anchor checks and actual Weapon-family hosted rule fragments.
  The initial hypothesis that published `display_relations` contain
  embedded Glossary links was false: **there are none currently**.
  The regression instead verifies existing embedded Glossary entry
  identities against the client anchor construction. Weapon-family
  fragment destinations resolve to actual hosted rule cards. These
  are published API and served-script checks, not live Chromium.
  Same-page local rule fragments and final release-candidate browser
  navigation remain open.
- **Validation:** `tests/test_public_relation_destinations.py` —
  **3 passed**; Ruff — PASS; Pyright — **0 errors, 0 warnings**;
  `docs` — Markdownlint **32 files, 0 issues**, and local
  Markdown links **30 files, 0 errors**. No full-suite or
  live Chromium release-candidate run performed.
- **Closeout pass 14, 2026-10-20:** Added same-page fragment
  parity coverage for seven published Mine-family Weapon detail
  APIs. Every emitted `#rule-` reference from nested relations
  or maintained-text tokens must point to a rule card included
  on that page; the known `#rule-weapon-mines` target is pinned
  to avoid a vacuous pass. Updated the testing/TODO boundary:
  this is server API and deterministic renderer coverage,
  not client DOM navigation or final whole-catalog acceptance.
- **Validation:** `tests/test_public_relation_destinations.py` —
  **4 passed**; `tests/test_weaponry_catalog_api.py` —
  **185 passed**; Ruff — PASS; Pyright — **0 errors,
  0 warnings**; Markdownlint — **32 files, 0 issues**;
  offline links — **30 files, 0 errors**. Full project suite
  and live Chromium were not run.
- **Closeout pass 15, 2026-10-20:** Expanded the existing
  same-page Weapon rule-fragment regression from seven Mine-family
  examples to every slug in the current published Weapon catalog.
  The test rejects duplicate catalog slugs and hosted card IDs,
  checks local links in every Weapon detail payload, and verifies
  a served page route for each Weapon emitting local fragments.
  The AP Mine / Mines source-known anchor remains a non-vacuity pin.
  This is not browser-rendered DOM navigation or an adjudication
  of missing source relations.
- **Validation:** `tests/test_public_relation_destinations.py` —
  **4 passed** after the expansion (60.33 seconds). Full-suite
  and live Chromium acceptance remain unrun for this change.
- **Closeout pass 16, 2026-10-20:** Added optional
  `tools.verify_rule_fragment_browser` for served Weapon and Glossary
  fragment navigation in Chromium at desktop and mobile widths.
  Checks catalog soft navigation, rendered same-page links, direct
  deep links, actual target visibility, JavaScript errors, and page
  overflow. Candidate identities are discovered from current API
  publication, with AP Mine's Mines link as a non-vacuity pin.
  This verifier has not yet been executed against a running server;
  final release-candidate browser acceptance remains open.
- **Validation:** New hermetic discovery tests **4 passed**,
  section registration **2 passed**, Ruff **PASS**, Pyright
  **0 errors/0 warnings**, Markdownlint **32 files/0 issues**,
  offline links **30 files/0 errors**. Full suite and live
  Chromium were not run.
- **Closeout pass 17, 2026-10-20:** Investigated the first actual
  Weapon fragment Chromium run (**51/57 passed**). All three AP Mine
  failures came from the verifier demanding a rendered clickable
  self-link even though the published source references its hosted
  Mines rule card; all three Glossary-to-AP-Mine deep links passed.
  Cybermine had one transient missing-card observation, while PARA
  Mine timed out at two widths; those causes remain unconfirmed.
  Corrected the verifier to check every API-referenced source card
  without requiring a corresponding visible self-link, wait for
  asynchronously rendered target cards and capture current URL,
  page status, JavaScript errors and API/network failures on errors.
  Browser results remain **unverified** until the updated verifier
  is executed; do not record a 57/57 pass based on these edits.
- **Validation:** Corrected verifier hermetic tests **7 passed**,
  test-section registration **2 passed**; Ruff on both touched Python
  files **PASS**; Pyright **0 errors/0 warnings**; Markdownlint
  **32 files/0 issues** and offline Markdown links **30 files/0 errors**.
  Full suite and new live Chromium execution were not run.
- **Closeout pass 18, 2026-10-20:** The second Chromium execution
  again reported **51/57**, with failures solely in the deep-link
  replay step after successful Weapon catalog navigation and in-page
  rule-fragment checks. The verifier had reused the same page, with
  existing hash/navigation state, for `page.goto()` to the same
  Weapon's hash URL. Changed direct-link checks to use independent
  fresh pages and include a source-backed direct link even when no
  clickable self-link exists. Added explicit phase labels on failed
  Weapon observations; kept actual browser acceptance pending.
- **Validation:** Verifier unit tests **10 passed**, Ruff on verifier
  and test module **PASS**, Pyright **0 errors/0 warnings**. The live
  browser result remains **51/57** until a fresh execution.
- **Closeout pass 19, 2026-10-20:** Fresh-page deep-link isolation
  improved Chromium acceptance to **55/57**. Both remaining failures
  (Cybermine and Kobra Pistol, 320 px) were within rendered
  same-page fragment clicks after successful initial card checks,
  not cold-load deep links. The verifier had a two-step
  visible-card wait followed by a separately timed DOM count; a
  late optional-Unit re-render could replace the article between
  these operations. Consolidated cardinality and visible-state
  checks into one browser evaluation with a bounded wait and
  explicit missing-card diagnostics. The suspected race remains
  unconfirmed until another live run; do not mark browser acceptance
  complete.
- **Validation:** Atomic-card verifier tests **11 passed**; Ruff on
  verifier and its test module **PASS**. The subsequent developer-run
  Chromium report recorded **57/57 passed** on the local development
  app (1440, 390, 320 px; confirmed 2026-10-20). This closes the
  bounded Weapon fragment browser audit, not final release-candidate
  source completeness.
- **Closeout pass 20, 2026-10-20:** Expanded the maintained cross-domain
  rule-relation destination regression beyond detail API existence:
  every currently published catalog-backed relation target must also
  serve an HTML detail page with its actual frontend renderer contract.
  Dedicated Skills and Hacking Programs pages intentionally differ
  from generic `data-catalog` templates. The composed rules
  `display_relations` graph currently emits no explicit `href`
  targets; those are not claimed as covered graph edges. The
  independently published Glossary-to-Weapon family fragments
  remain covered by their existing API and 57/57 Chromium checks.
  This is current route/bootstrap parity, not full source-to-browser
  completeness or live rendering of every rule relation.
- **Validation:** `tests/test_public_relation_destinations.py` —
  **4 passed** after extending the structured route checks
  (60.58 seconds).
- **Closeout pass 21, 2026-10-20:** Added an opt-in
  `--verify-server` release-evidence check to the source baseline
  inventory. It computes the runtime's exact SHA-256-derived combined
  revision from the inventoried Army and rules database bytes, then
  checks the served `/api/version` revision against that same
  identity. Stale or mismatched publication fails before report
  output; successful results record the endpoint and matched
  revision in JSON/Markdown. This is database-pair consistency
  evidence only: source artifact verification, symbols, semantic
  coverage and final-release browser acceptance remain separate.
- **Validation:** `tests/test_report_reference_baseline.py` —
  **11 passed** including exact runtime-revision parity, stale-server
  rejection and CLI evidence outputs; Ruff on tool and test module
  **PASS**. The server check still requires an explicit live run.
- **Closeout pass 22, 2026-10-20:** Extended the opt-in pinned Army
  ZIP verification from whole-file SHA-256 identity to explicit
  publication cardinality, source-version distributions and source
  faction/list ID parity against `infinity.db::army_lists`. The
  59-JSON-document source archive contains 58 faction/list files
  plus one independent `metadata.json`; the published
  `sourceFileCount=58` is therefore expected, not a discrepancy.
  The verifier fails closed on unexpected extra JSON documents,
  missing source versions or source-list identity drift.
  This is source identity coverage only, not field-level data or
  final browser completeness. The actual pinned ZIP still requires
  an explicit verification rerun.
- **Closeout pass 23, 2026-10-21:** Strengthened the optional
  archive-to-publication gate to compare per-source filename, SHA-256,
  version, Army/reinforcement classification and each ordered Unit
  membership from the pinned ZIP with `army_lists` and `army_units`
  in the published database. It rejects altered provenance, missing
  or extra Unit occurrences, changed positions and malformed or
  duplicate source Unit identities. This records bounded
  source-to-storage parity, not source-field completeness, and
  must be rerun using the actual final release inputs.
- **Closeout pass 24, 2026-10-21:** Expanded the optional pinned Army
  archive parity check through all source profile-group identities,
  direct scalar facts, ordered profiles and loadout options. The
  first real-archive test exposed the intentional database split:
  profile groups are published in `infinity.db`, but the source-native
  profiles and loadout tables live in export-paired `infinity.raw.db`.
  The verifier now requires the valid database export pair, compares
  the correct tables and retains mismatch evidence for identities,
  positions, core profile stats and loadout costs. The new regression
  exercises both nonempty synthetic source data and the locally
  available pinned ZIP; no comparison of derived runtime profile
  payloads or nested references is claimed.
- **Validation:** `tests/test_report_reference_baseline.py` —
  **18 passed**, including the real pinned archive and the exact
  export-paired raw database. Ruff on tool and test module **PASS**;
  Pyright **0 errors/0 warnings**; Markdownlint **32 files/0 issues**,
  offline documentation links **30 files/0 errors**. The full suite,
  fresh served-browser checks and final release-candidate acceptance
  remain outstanding.
- **Closeout pass 25, 2026-10-21:** Extended archive-to-publication
  verification through the reusable profile and loadout payload
  Skill/Equipment/Weapon occurrence rows. Every source parent coordinate,
  occurrence position, referenced ID, display order and quantity is
  compared with the published payload occurrence/relationship joins.
  Duplicate, missing, additional and altered occurrences fail, and the
  pinned archive test requires nonempty matching evidence in all six
  categories. Does not verify extras/parameter values, Characteristics,
  Orders, Peripheral/Include relations, API output or browser display.
- **Closeout pass 26, 2026-10-21:** Extended source-to-published
  payload parity to all ordered `extra` references associated with
  profile and loadout Skills, Equipment and Weapons. The verifier
  compares exact source parent coordinates, reference occurrence,
  extra position and extra ID across the reused payload tables,
  rejecting missing/additional rows, duplicates, reordering and ID
  drift. Pinned-archive integration verifies nonempty extra evidence.
  This is an identity/ordering check, not interpretation of extra
  modifiers or certification of malformed values preserved as raw
  source data.
- **Closeout pass 27, 2026-10-21:** Extended the pinned Army ZIP
  source-to-published-payload audit to ordered profile and loadout
  Characteristic IDs plus typed loadout Order properties: type, list
  count and total count. Matched parent source coordinates and positions
  through reusable payload occurrences. Missing/additional/duplicate
  rows, changed identities, ordering and Order counts fail; synthetic
  mutation cases and real pinned-archive integration are maintained.
  The current pinned snapshot has 15,011 profile Characteristics,
  **zero** loadout Characteristics and 15,195 loadout Orders.
  Zero is an observed, checked source/storage absence, not a missing
  verifier category; the synthetic fixture exercises the nonempty case.
  Raw unmodeled Order fields, other nested relations and client
  rendering remain unreviewed.
