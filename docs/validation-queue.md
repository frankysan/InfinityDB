# Phased validation queue

**Project domain:** Project infrastructure

This file is the single active register for validation work deferred under the
[phased development workflow](testing.md#phased-development-and-validation).
It tracks **test design and execution obligations**, not implementation features,
release scope, or source ambiguities. `docs/TODO.md` owns implementation work
and defects; `docs/releasing.md` owns mandatory release acceptance. Keep stable
IDs here and link the owning task instead of duplicating its description.

## Queue rules

- Separate **implementation**, **test design (VD)** and **test execution
  (VR)**. Implementation normally records concrete missing tests as VD
  instead of writing and executing a regression suite immediately. VD
  work creates or edits tests and links their execution to VR; **no tests
  run during a VD pass**, including new-test sanity runs. VR is the only
  deferred test-execution phase. Exceptionally urgent correctness,
  security, migration or artifact-safety checks remain immediate and
  must be named explicitly. See
  [testing.md](testing.md#phased-development-and-validation).
- Before ending an implementation pass, record **all concrete missing test
  designs** as VD, including new focused regression tests unless an immediate
  safety exception requires them, and each change's **deferred execution** as
  VR. A VR may await one or more VD items; existing tests requiring reruns
  need only VR. Record exact immediate exception selectors/results separately.
  Never call an unrun check passed or defer a required safety, migration or
  publication gate.
- Design items are `VD-0001`, `VD-0002`, etc. Each ID is one independently
  actionable test requirement, not one test function or a speculative idea.
  Count open `needs-design` IDs toward the **3-requirement design threshold**.
- Execution items are `VR-0001`, `VR-0002`, etc. Each item represents one
  distinct implementation change awaiting deferred verification, including
  changes whose required test design is unfinished. Count distinct open
  implementation changes, not files, tests, commits, or repeated runs, toward
  the **5-change execution threshold**. Combine multiple checks for the same
  change under one VR item. Link any blocking VD IDs.
- **Strict drain loop (check at every work boundary):**
  1. If **VD >= 3**, process **all open VD entries to zero**, one at a
     time. Otherwise, process any VD due by age or a mandatory gate.
     Write/revise the tests and link them to VR, but **run no tests**.
  2. If **VR >= 5** or any VR is due by age or a mandatory gate, first
     complete **all open VD prerequisites** of those due VR entries,
     even when VD is below 3. A blocked VD leaves its dependent VR
     blocked; never bypass the prerequisite.
  3. If **VR >= 5**, execute and reconcile **all open VR entries to zero**,
     one at a time. Otherwise, process VR entries due by age or gate.
     Shared full-suite results may satisfy several entries, but review
     and retire each independently. **Dispatch is not completion**.
  4. Recount both queues and check overdue/gated entries. If VD >= 3 or
     VR >= 5, restart at step 1; otherwise resume ordinary implementation
     only after all individually due work is handled.
  Reaching a numeric threshold triggers a drain to **zero**, not a pause
  when the count falls below its threshold. Never start ordinary
  implementation while due queue work is idle or running focused VR tests.
  **Exception:** while an actual full test suite is running asynchronously on
  a pinned, independent `linux-dev` checkout, unrelated Windows development
  may continue. Its new VD/VR obligations still enter the queue, and the
  outstanding VR entries remain open; resume the drain when the full run
  completes. This exception does not apply to focused or partial Linux jobs,
  nor to merely scheduling a future run. Failed and blocked entries remain
  open and must be triaged individually; if no safe action can clear them,
  report the blockers and leave the queue explicitly undrained rather than
  claiming success or looping indefinitely.
  A critical gate or an overdue item takes priority.
- **Hosted CI has its own owner:** `docs/ci.md` specifies CI execution,
  failures and matrix results; `docs/releasing.md` owns final acceptance.
  **Do not hold a locally verified VR item open solely for a hosted CI run**.
  Preserve its still-mandatory CI acceptance in those owners and the active
  source-coverage evidence; never describe VR retirement as hosted approval.
  A VR with no remaining local execution work but a pending hosted check
  should be migrated to its CI/release owner, not retained indefinitely
  as a completed local task. This separation does **not** waive hosted
  platform, wheel, deployment or deterministic-byte requirements.
- **Maximum age:** process any open deferrable item within 7 calendar days of
  its recorded date, even below threshold. Also process it before the relevant
  release, merge, deployment, or other mandatory acceptance gate. Reassess the
  counts and oldest dates at the beginning and end of every agent pass.
- Never queue work that is required immediately for correctness or risk control.
  [Immediate checks and exceptions](testing.md#phased-development-and-validation)
  still apply, and required hosted CI remains unchanged.
- When design discovers a product defect, add/link the implementation fix in
  `docs/TODO.md` and mark the affected entry `blocked`; do not fix unrelated
  behavior during a dedicated design/execution pass. Failed executions stay
  open until the relevant checks pass on a corrected state.
- Include sufficient version/commit or artifact identity for results to be
  reproducible. A green result from an older state cannot verify a later edit.
  Store bulky reports under ignored `local/`; retain concise durable acceptance
  evidence in its canonical document when required.
- **Linux is the preferred deferred-execution worker**, not an automatic
  mirror of Windows. When execution is due, the agent prepares the
  *committed* target revision using separately invoked safe Git
  fetch/fast-forward operations on `linux-dev`, as already authorized
  for the validation handoff. Never force, reset, rebase or disturb a
  divergent/dirty checkout; report an unsafe or unavailable revision
  as a blocker. Batch compatible selectors into one pinned asynchronous
  `linux-dev` job with `expected_commit`. **Only while the entire
  full-suite run is actually executing on Linux** may independent Windows
  development continue; a focused/partial job does not suspend VR
  draining. Check the full-suite result at meaningful boundaries,
  resume processing open VR entries after it finishes, and respond
  to actionable failures. A Linux run cannot verify later Windows
  edits. Git synchronization remains explicit, bounded and
  validation-triggered, never a background mirror.
  Follow the [dispatch/retirement protocol](testing.md#parallel-windows-development-and-linux-validation).
  A successful job applies only to its verified revision and coverage.
  At each pass boundary, report queue counts, due/blocked items and what
  was actually dispatched; do not equate green immediate tests with an
  empty deferred-execution queue.
- **Retire completed entries immediately after processing:** remove each VD
  item once the test code/selector has been inspected for design completeness,
  and carry the selector to an open VR item **without executing it**. Remove
  each VR only after its required execution and evidence have passed for the
  exact intended state. Keep failed, blocked or unrun work open; separately
  owned hosted CI and release gates are not implicitly accepted.
- This is an **active queue, not a completion log**. Git history retains
  retired detail; do not copy finished items into another running diary.
  Advance the next-unused-ID counters on creation and never reuse an ID.

## Pending test design

No pending design obligations.

VD-0072/0073/0074 were retired after static review of three pinned-source cases,
five curated/export/API cases and fifteen ordinary-browser cases, without
executing tests. VR-0115 retains their selectors and existing-regression reruns.

VD-0069/0070/0071 were retired after static review of the source/vocabulary,
API and 36-case ordinary-browser designs without executing tests. Their
execution was subsequently accepted under VR-0114, as recorded below.

VD-0066/0067/0068 were retired following static design review without
execution; their three selector groups were subsequently accepted on the
pinned Linux revision under VR-0113 (see below).

VD-0062 was retired after static review without execution; its curated-export,
Glossary API, and responsive browser selectors were executed and accepted under
VR-0110, as recorded in the
[coverage audit](v1.0-source-coverage-audit.md#v1s-082-bounded-source-review-trooper-glossary-2026-11-05).

VD-0059/0060/0061 were retired after
static review without execution; their docs-stage, JSON, synthetic Git
ancestry and CI regressions passed under VR-0107/0108 on pinned Linux
`bf0821af`. Earlier VD-0053–VD-0058 passed on `0bac3369`, and
VD-0050–VD-0052 on `e957c43e`. VR-0109's existing Node harness selector
passed on committed Windows/Linux `34282616` and was retired. Hosted
CI/release acceptance remains independent.

A VD entry records its ID/date/status (`needs-design` or `blocked`),
owning TODO work and revision, concrete missing assertion/edge case,
existing coverage, risk, linked VR ID, and resulting test selector and
static design-review outcome. Do not record a test result in VD. Retire
the entry when its design review is complete; retain the unrun test
selector and other dependencies in its VR item.

## Pending deferred execution

- [ ] VR-0116 (2026-11-06; ready-to-run): Renamed local PDF references and
  expanded revision inventory. Work: operator-requested source maintenance;
  revision: implementation commit containing this entry; risk: provenance.
  Design: existing source/hash, rules-export and publication coverage; no new
  behavior or missing assertion identified. Immediate: verify all selected
  PDF paths/pages/hashes; deterministic double v9 export; complete SQLite
  schema/table comparison allowing only declared source-path substitutions;
  unchanged deployed-object and variant-usage payloads apart from dependent
  fingerprints; rollback-protected matched publication and docs checks.
  Outcome: all 14 declarations matched paths/pages/hashes; both v9 exports
  were byte-identical and all 16 tables matched apart from 14 locator cells.
  Both dependent publications matched; documentation stage and diff checks passed.
  Deferred: `tests/test_curated.py`, `tests/test_audit_1_0_reference_inputs.py`,
  `tests/test_report_reference_baseline.py`,
  `tests/test_audit_reinforcements_applicability.py`,
  `tests/test_silent_immunity_source_scope.py`,
  `tests/test_restriction_storage_candidate.py`, and cumulative source/API
  regressions for mechanically updated PDF locators.
  Intended host: pinned `linux-dev`, after explicitly activating renamed PDFs
  from Syncthing staging; present source bytes must pass their hash checks.
  Additional historical revisions are inventoried, not semantically accepted.

- [ ] VR-0115 (2026-11-06; ready-to-run): Five N5.3 Trait definition
  corrections. Work: V1S-082; revision: implementation commit containing this
  entry; risk: source/reference parity. Design: VD-0072/0073/0074 completed
  without execution. Immediate publication-integrity gates passed: pinned
  source hashes, unchanged v9 schema/Restrictions and other rule fields,
  deterministic double export,
  semantic-link coverage and rollback-protected matched release publications.
  Deferred: `tests/test_silent_immunity_source_scope.py` (includes
  `test_v1s082_trait_glossary_source_clauses` and
  `test_v1s082_trait_definitions_export_and_api`),
  `tests/test_verify_scenario_faq_browser.py::test_v1s082_traits_normal_browser`,
  `tests/test_rules_database.py::test_rea023_deployable_placement_geometry_and_exception_owners`,
  `tests/test_deployable_trigger_cross_rules.py`, and publication-pair checks.
  These retain the existing Silent/Immunity, Disposable and Deployable
  conditions. Intended host: pinned `linux-dev` with required assets;
  historical source checks may require Windows where N5.2 is available.
  Record actual hosts and no uncovered source/browser skips.

VR-0114 was accepted at `8c2600de350195ab7f69782a07e9bbb92ab52db7`: 51/51
Linux API/export/browser checks and 3/3 Windows pinned-source checks passed,
with required 808/808 assets. The Windows run covers the historical N5.2 PDF
missing on Linux. Exact selectors, jobs and earlier failure dispositions are
recorded in the [Label review](v1.0-source-coverage-audit.md#v1s-082-bounded-source-review-label-definitions-2026-11-06).

VR-0113 was accepted on 2026-11-06 against `af806f6016e9c1ae38bf567dc0db6aba5380f28c`
using Linux job `linux-dev:299fff7559554529b55ac0f80d3b0dc7`:
**21 passed, zero skipped/failed** with 808/808 published/browser SVGs.
Five curated/source assertions, one Glossary API assertion and fifteen
Chromium cases (five entries at 1440/390/320 px) passed; source/asset
and release-pair publication gates are recorded in the
[coverage audit](v1.0-source-coverage-audit.md#v1s-082-bounded-source-review-remaining-p-173-glossary-terms-2026-11-06).
The independently required full suite, hosted CI and frozen-candidate
release gates remain separate.

The most recent pinned Linux full-assets acceptance, including the 2026-11-04
queue drain, is recorded in
[testing.md](testing.md#parallel-windows-development-and-linux-validation).
The active queue does not duplicate completed evidence: Git history retains
the retired VD/VR entries. Hosted Source checks (including macOS and
cross-platform deterministic outputs), Installed wheel, Deployment smoke
and final release acceptance are still independently required under
[CI policy](ci.md) and [V1S-093](TODO.md#final-10-acceptance);
**an empty VR queue does not certify those gates**.

A VR entry records its ID/date/status (`awaiting-design`,
`ready-to-run` or `blocked`), the implementation revision/artifact,
immediate focused checks and results, any required VD dependencies,
deferred test selectors/gates, and the final execution outcome.
Retire it once required checks pass on the intended state and the outcome
is recorded. Failed or incomplete verification remains open.

The five-item November 4 drain was verified at
`1d0d5c196b87983737981b8b8244321b552527a4`; see the linked testing
summary above. Hosted CI and final release gates retain separate owners.

## Next unused IDs

- Design: `VD-0075`; active obligations are listed above.
- Execution: `VR-0117`; active obligations are listed above.

Increment the relevant next-unused ID when adding a task, even if that
task is later removed. Previous completed records remain in Git history.
The 2026-11-02 cumulative local suite evidence is summarized in
[testing.md](testing.md#controlled-chromium-concurrency-and-browser-reuse-benchmark);
mandatory CI and final release acceptance remain separate.

## Recording template

Copy only the applicable entry to the corresponding active section and
replace the sample ID with the next unused ID shown above. Do not create
entries for work fully verified during implementation.

```text
- [ ] VD-NNNN (YYYY-MM-DD; needs-design): <required assertion/edge case>.
  Work: <TODO anchor>; change: <revision/files>; risk: <level>.
  Existing coverage: <selector or none>; linked execution: VR-NNNN.
  Outcome: <authored test selectors and static design review; no tests run>.

- [ ] VR-NNNN (YYYY-MM-DD; awaiting-design): <one implementation change>.
  Work: <TODO anchor>; revision: <commit/artifact>; risk: <level>.
  Immediate: <essential regression selector/result and required validators>.
  Design: VD-NNNN or none.
  Deferred: <existing module/full-suite/integration/manual checks>.
  Outcome: <tested revision, command, counts and evidence, when run>.
```
