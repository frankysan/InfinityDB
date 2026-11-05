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

- [ ] VD-0053 (2026-11-05; needs-design): Verify per-commit Git-aware V1S retirement attribution, including valid closeout, missing ID mention, multiple IDs in one commit, and reopen/no-op or reordered tasks that must not count as removals.
  Work: [V1S-096](TODO.md#final-10-acceptance); change: `tools/check_v1_backlog.py` Git-aware audit on Windows after a1f78bcd; risk: medium.
  Existing coverage: `tests/test_check_v1_backlog.py` checks static parsing only; linked execution: VR-0104.
  Outcome: pending design; no tests executed.

- [ ] VD-0054 (2026-11-05; needs-design): Verify advisory/enforced closeout severity, acceptance-pointer warnings, bad or diverged revisions, non-first-parent range, missing files, and CLI error reporting.
  Work: [V1S-096](TODO.md#final-10-acceptance); change: `tools/check_v1_backlog.py`; risk: medium.
  Existing coverage: no Git-history CLI fixtures; linked execution: VR-0104.
  Outcome: pending design; no tests executed.

VD-0050/0051/0052 were previously retired after static test-design review;
their still-unrun selectors remain under VR-0103.

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

- [ ] VR-0102 (2026-11-05; ready-to-run): Shared soft-navigation focus handoff and polite page-change announcement, plus existing floating-notice touch/keyboard acceptance.
  Work: [V1S-079/080](TODO.md#accessibility-and-navigation); revision: this implementation/design batch (use its introducing Git commit as the exact test target); risk: medium.
  Immediate: Ruff on both modified/new test modules and `git diff --check` passed; no tests executed.
  Design: VD-0047/0048/0049 retired after static review (no test execution).
  Deferred: `tests/test_verify_accessible_navigation_browser.py` (soft link, persistent-shell link, back/scroll, focus/status at 1440/390px); `tests/test_verify_page_footer_browser.py` (native disclosure semantics and touch at 390/320px in light/dark), existing `tests/test_verify_sidebar_density_browser.py`, and applicable normal broader checks at next due drain.
  Outcome: unrun; actual screen-reader sign-off and frozen-candidate visual acceptance remain separately required under V1S-079/080.

- [ ] VR-0103 (2026-11-05; ready-to-run): Track and require the byte-exact v1.0 variant-usage release publication throughout source CI, deployment packaging, preflight/image smoke and v8 compatibility checks.
  Work: [variant usage projection](TODO.md#rules-and-reference-completeness); revision: current changes from d1f315a1, pin the resulting commit for execution; risk: high.
  Immediate: `tools.build_variant_usage --check-publication` PASS (151 groups, 10,923 reviewed rows); `tools.verify_deployment_assets --skip-svg` PASS against current source-matched artifacts; no pytest executed.
  Design: VD-0050/0051/0052 retired after static review; tests authored but not run.
  Deferred: `tests/test_deployment_scripts.py` (tracked/image/v8 guards), `tests/test_verify_deployment_assets.py` (missing/empty/stale and matched preflight), `tests/test_variant_usage.py` and relevant `tests/test_web.py` selectors; normal source/CI smoke and actual container build at release candidate gate.
  Outcome: unrun; runtime and hosted exact-release acceptance not yet claimed.

- [ ] VR-0104 (2026-11-05; awaiting-design): Git-aware V1S backlog closeout auditor, initial committed-history mode.
  Work: [V1S-096](TODO.md#final-10-acceptance); revision: pending commit from Windows implementation after a1f78bcd; risk: medium.
  Immediate: Ruff and Pyright passed; no implementation regression tests executed.
  Design: VD-0053/0054.
  Deferred: `tests/test_check_v1_backlog.py` with synthetic temporary Git repositories, CLI baselines/enforcement, and applicable normal checks on the committed revision.
  Outcome: unrun; phase 2 worktree/index mode and phase 3/4 integration remain outside this batch.

## Next unused IDs

- Design: `VD-0055`; active obligations are listed above.
- Execution: `VR-0105`; active obligations are listed above.

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
