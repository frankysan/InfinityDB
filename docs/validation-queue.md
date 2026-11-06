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

- [ ] VD-0082 (2026-11-06; needs-design): Read-only development-status local
  parsing and V1S recommendation. Work: user-requested Project infrastructure
  dev-status CLI; change: `tools/dev_status.py`; risk: incorrect task/queue
  prioritization. Existing coverage: maintained V1S backlog parser tests;
  linked execution: VR-0121. Design: add offline cases for valid/invalid
  backlog, documented pauses, VD threshold exclusions for blocked items, VR
  aging and malformed/duplicate active queue entries. No tests run during VD.
- [ ] VD-0083 (2026-11-06; needs-design): Read-only MCP and exact-SHA GitHub
  status reporting. Work: user-requested Project infrastructure dev-status
  CLI; change: `tools/dev_status.py`; risk: stale/misleading CI or job state.
  Existing coverage: MCP monitor contract and GitHub CI policy;
  linked execution: VR-0121. Design: mock local monitor and GitHub responses
  (including unavailable, stale/unverified, missing, skipped, failed, queued,
  superseded and cross-checkout jobs), and verify SHA filtering, token
  non-disclosure, timeouts and read-only behavior. No live CI dispatch or
  tests during VD.

A VD entry records its ID/date/status (`needs-design` or `blocked`),
owning TODO work and revision, concrete missing assertion/edge case,
existing coverage, risk, linked VR ID, and resulting test selector and
static design-review outcome. Do not record a test result in VD. Retire
the entry when its design review is complete; retain the unrun test
selector and other dependencies in its VR item.

## Pending deferred execution

- [ ] VR-0121 (2026-11-06; awaiting-design): Read-only development-status
  CLI reporting Git/V1S, VD/VR, MCP jobs and GitHub exact-SHA workflows.
  Work: user-requested Project infrastructure status command; revision:
  commit introducing `tools/dev_status.py` (pin exact SHA for VR execution);
  risk: misleading acceptance or stale status.
  Immediate: read-only local/online CLI smoke, Ruff, Pyright, docs and Git
  diff checks; these are not deferred regression tests.
  Design: VD-0082 and VD-0083. Deferred: `tests/test_dev_status.py`
  local parser and mocked provider cases, plus selected existing V1S/parser
  regressions on a pinned Windows and Linux revision. No running tests count
  as accepted until the designed cases are executed and reconciled.
- [ ] VR-0118 (2026-11-06; ready-to-run): N5.3 Hackable Unit Profile
  help correction. Work: V1S-082; revision: implementation commit containing
  the guarded v9 publication; risk: source and browser reference accuracy.
  Design: VD-0077 (bilingual PDF clauses), VD-0078 (curated/stored/API and
  typed link), VD-0079 (ordinary keyboard/browser 1440/390/320 px), all
  statically reviewed and retired **without running tests**.
  Immediate: exact English p. 8 / Spanish p. 9 PDF hashes, deterministic
  double v9 export, 498 unrelated identities unchanged, schema/Restrictions
  parity, matched deployed-object/variant-usage publications and guarded
  rollback-safe promotion; both publication verifiers and semantic-link
  audit passed. See the
  [bounded review](v1.0-source-coverage-audit.md#v1s-082-bounded-source-review-hackable-profile-help-2026-11-06).
  Deferred: `tests/test_application_rule_references.py::test_hackable_profile_help_pinned_source`
  (2 source cases), `tests/test_application_rule_references.py::test_hackable_profile_help_export_and_api`,
  `tests/test_verify_scenario_faq_browser.py::test_hackable_profile_help_normal_browser`
  (3 Chromium cases), cumulative application source/reference regressions.
  Intended hosts: Windows for both verified PDF files; explicitly pinned
  `linux-dev` for API/browser/cumulative acceptance with required assets.
  No skip on the intended host counts as evidence. Hosted matrix and
  frozen-candidate release gates remain independently required.

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

- Design: `VD-0084`; active obligations are listed above.
- Execution: `VR-0122`; active obligations are listed above.

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
