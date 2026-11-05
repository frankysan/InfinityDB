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

No open test-design obligations.

A VD entry records its ID/date/status (`needs-design` or `blocked`),
owning TODO work and revision, concrete missing assertion/edge case,
existing coverage, risk, linked VR ID, and resulting test selector and
static design-review outcome. Do not record a test result in VD. Retire
the entry when its design review is complete; retain the unrun test
selector and other dependencies in its VR item.

## Pending deferred execution

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

- [ ] VR-0089 (2026-11-05; ready-to-run): V1S-090 disposable Commlink
  baseline/strict staging repair; base: 63e9e4ba; design: VD-0031 statically
  reviewed without execution. Added selector:
  test_commlink_candidate_rejects_unrelated_curated_drift verifies full-record
  rejection, no destination and byte-preservation of both baseline artifacts.
  Deferred: tests/test_reinforcements_optional_reference.py, then complete
  code/full-assets and Git-index preflight on linux-dev. Due now: hosted CI failure.
  Execution: full job `linux-dev:3a1ca0d3752b48ddb2423d407c713492` at
  `8391ba6cc389a16d141fc6bfabb0f38b43f9b0fc` failed eleven publication
  guards (5,219 passed / 29 skipped), plus missing Linux Markdownlint setup;
  preflight did not run. Rerun full code/data/preflight after VR-0092's paired
  correction. Docs run on Windows and hosted CI until Linux npm setup is available.
  Corrected execution: job `linux-dev:bae1f465c5bf414fb9050086fe012fdd` at
  `0cbcf65aaec0d6a8e9644142c9b57ec360cc252b` is running full
  test/lint/type/build/rules/preflight stages with required assets and the
  controlled build fixture. No accepted result yet.
- [ ] VR-0090 (2026-11-05; ready-to-run): V1S-090 exact Doctor evidence
  manifest refresh; base: 63e9e4ba; no missing design (existing mutation coverage).
  Deferred: tests/test_deployed_object_non_catalog_queue.py,
  tests/test_deployed_object_citation_migrations.py and
  tests/test_legacy_staging_schema_guards.py, then cumulative linux-dev checks.
  Due now: hosted CI failure; preserve source/provenance guards.
  Execution: same failed pinned full job as VR-0089; corrected-pair rerun pending.
- [ ] VR-0091 (2026-11-05; ready-to-run): V1S-090 frozen reference-section
  expectation refresh after the reviewed Doctor citation addition; base: 63e9e4ba.
  No missing design; existing tests/test_report_reference_baseline.py covers
  frozen/current identity/evidence joins. Deferred: that module and complete
  code/full-assets checks on linux-dev. Due now: hosted CI failure.
  Execution: same failed pinned full job as VR-0089; corrected-pair rerun pending.
- [ ] VR-0092 (2026-11-05; ready-to-run): V1S-084 prerequisite: synchronize
  the two previously reviewed Doctor/Ancillary records and Doctor citations
  with the tracked v9 rules/deployed-object pair. Base: 8391ba6c.
  Existing source, runtime and guarded publication regressions cover the change;
  no missing test design. Immediate artifact-safety gate: full schema/table
  multiset comparison permits only those two records, their Doctor citations
  and affected citation statistics; preserve all 17 deployed-object payloads
  and unrelated fingerprints; retain recovery copies and post-validate both files.
  Deferred: all eleven failed publication/source selectors from the pinned
  Linux --all run, full assets/code and isolated preflight; linux-dev.
  The previous run failed 11 provenance tests and Linux Markdownlint setup;
  passing lint/type/build/rules stages do not accept the pair.
- [ ] VR-0093 (2026-11-05; ready-to-run): V1S-090 normal-mode scenario FAQ
  scope disclosure. Base: 0cbcf65a; design: VD-0032 statically reviewed without
  execution. Existing API assertions now cover the backend note and its absence
  on general FAQs; the browser selector adds 320 px, the normal non-discrepancy
  note, Hacking FAQ exclusion, Firefight exclusion, overflow and failed requests.
  Deferred: tests/test_faq_ruling_references.py and
  test_supplies_faq_is_visible_and_does_not_leak_to_other_scenarios in
  tests/test_verify_scenario_faq_browser.py, plus exact-pair browser checks.
  Due now: materially misleading omission of the reviewed applicability limit;
  intended execution host: linux-dev, with Windows corroboration.

## Next unused IDs

- Design: `VD-0033`; active obligations are listed above.
- Execution: `VR-0094`; active obligations are listed above.

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
