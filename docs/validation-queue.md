# Phased validation queue

**Project domain:** Project infrastructure

This file is the single active register for validation work deferred under the
[phased development workflow](testing.md#phased-development-and-validation).
It tracks **test design and execution obligations**, not implementation features,
release scope, or source ambiguities. `docs/TODO.md` owns implementation work
and defects; `docs/releasing.md` owns mandatory release acceptance. Keep stable
IDs here and link the owning task instead of duplicating its description.

## Queue rules

- Separate the four activities: **essential test creation** and
  **essential targeted execution** happen within the implementation pass;
  **additional test design** is deferred as VD; **broader test execution**
  is deferred as VR. A design pass may run newly written tests for sanity
  without turning into a general execution pass. See
  [testing.md](testing.md#phased-development-and-validation).
- Before ending an implementation pass, record every concrete missing
  regression **design** as VD and each change's deferred broader **execution**
  as VR, including changes needing only an existing full-suite or browser run.
  Record exact immediate test selectors and results separately. Never call an
  unrun check passed or defer a required safety, migration or publication gate.
- Design items are `VD-0001`, `VD-0002`, etc. Each ID is one independently
  actionable test requirement, not one test function or a speculative idea.
  Count open `needs-design` IDs toward the **5-requirement design threshold**.
- Execution items are `VR-0001`, `VR-0002`, etc. Each item represents one
  distinct implementation change awaiting deferred verification, including
  changes whose required test design is unfinished. Count distinct open
  implementation changes, not files, tests, commits, or repeated runs, toward
  the **5-change execution threshold**. Combine multiple checks for the same
  change under one VR item. Link any blocking VD IDs.
- When design reaches 5, the next pass handles test design only. When execution
  reaches 5, the next pass handles test execution only, after required test
  design is ready. If both thresholds are reached, design goes first wherever
  it blocks execution. Do not start another ordinary implementation pass until
  the due pass is addressed. For asynchronous Linux validation, correctly
  dispatching the due jobs addresses the scheduling checkpoint; return
  immediately to independent Windows work while they run. Failed jobs
  remain open and actionable, not silently accepted or ignored.
  A critical gate or an overdue item takes priority.
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
  `linux-dev` job with `expected_commit`; **after dispatch, resume
  independent Windows development immediately**, not a polling/waiting
  loop. Check status at meaningful Windows task boundaries and respond
  to actionable failures. A Linux run cannot verify later Windows
  edits. Git synchronization remains explicit, bounded and
  validation-triggered, never a background mirror.
  Follow the [dispatch/retirement protocol](testing.md#parallel-windows-development-and-linux-validation).
  A successful job applies only to its verified revision and coverage.
  At each pass boundary, report queue counts, due/blocked items and what
  was actually dispatched; do not equate green immediate tests with an
  empty deferred-execution queue.
- **Retire completed entries immediately after processing:** remove a VD item
  once its tests are designed and the direct sanity checks pass; carry any
  relevant selector/dependency into its open VR item. Remove a VR item when
  its required execution has passed on the intended state and the outcome is
  recorded. Keep failed, blocked, or unrun work open; independent hosted CI
  and release gates are not implicitly accepted.
- This is an **active queue, not a completion log**. Git history retains
  retired detail; do not copy finished items into another running diary.
  Advance the next-unused-ID counters on creation and never reuse an ID.

## Pending test design

Only open VD requirements belong here. **No pending entries.**

A VD entry records its ID/date/status (`needs-design` or `blocked`),
owning TODO work and revision, concrete missing assertion/edge case,
existing coverage, risk, linked VR ID, and test selector/sanity-check
outcome as it is processed. Retire the entry once designed and checked;
retain required dependencies in any still-open VR item.

## Pending deferred execution

Only open VR obligations belong here. **Current count: 3 distinct
changes** (VR-0023/0024/0047); no deferred test-design requirement is open.
Oldest recorded date: 2026-11-02.

At pinned Linux commit `06ae1c4856d3213a3f03c88f7f6f219b23366ee7`,
the full suite passed **4,946 tests / 28 expected skips / 0 failures**
with 808/808 SVG assets. This retires VR-0040 (Army/Section and
Commlink browser context), VR-0041 (all published Reinforcement profile/
loadout source parity) and VR-0042 (all source-backed Commlink extras).
The preceding `5d6a30d8` run passed the same suite; a subsequent
fixed-tuple Pyright correction was retested on the final revision.
See [testing.md](testing.md#parallel-windows-development-and-linux-validation)
for the pinned jobs, warnings and residual scope. The independent
Chromium skip-reason and controlled capacity comparisons remain open
as VR-0023/24. Git updates are explicit, not background mirroring.

The later pinned Linux suite at `ad3314dc3da02ec3a9087b5361dcbdc1b374cabf`
passed **4,952 tests / 29 expected skips / 0 failures** with 808/808
published SVG assets. It retires VR-0043 (legacy staging freshness guard);
full evidence and the two existing `fork()` warnings are recorded in
[testing.md](testing.md#parallel-windows-development-and-linux-validation).
The independent Chromium diagnostics remain open as VR-0023/24.

The 2026-11-03 Lieutenant publication and development tooling batches
retired **VR-0044/45/46** at pinned `60bd855932f663bf6bec0de5dc29f3439006e6ed`.
The initial Lieutenant suite at `14590055` exposed two test defects,
both corrected by `bda102e6`: cross-platform SQLite byte-layout
comparison and an incomplete reviewed-extra identity assertion.
The corrected `bda102e6` Linux suite passed **4,959 / 29 skipped /
0 failed**; its two original failing selectors passed separately on
Linux. On the final revision the raw-inspector module passed **11/11**
and the directory/ZIP database-size fixtures passed **2/2** on Linux.
The final full Linux job `linux-dev:0f5828bdc96a4172bb46c5fcce1e991e`
passed **4,970 / 29 skipped / 0 failed** in **594.79 s**, with **808/808**
published SVGs; all three GitHub workflows passed. The two existing
Python 3.14 fork warnings and independent controlled Chromium
benchmarking are not resolved by these results. See
[testing.md](testing.md#parallel-windows-development-and-linux-validation).

- [ ] **VR-0047** (2026-11-03; ready-to-run): Validate N5.3
  Terrain source-58 profile-type metadata on pinned Linux and across the
  release-matched browser/reference suite. Work: [variant usage projection](TODO.md#rules-and-reference-completeness);
  change: seven exact Terrain `TEXT` extras (`Total`, five single
  Types, `Aquatic/Jungle` choose-one), guarded matched-v9 refresh,
  and pinned source regressions; risk: moderate (curated semantics and
  tracked rules DB, no executable terrain evaluator).
  Immediate Windows: source-variant module **82/82**; five malformed
  type/selection regressions, 1,235 qualified/one unqualified source
  occurrence and SRC-028 separation; read-only pre-promotion delta guard,
  rollback-capable promotion and published pair recheck; data and rules
  stages, Ruff, and diff checks passed. Design: none.
  Deferred: Linux pinned-source module, cumulative browser/source suite,
  hosted CI on the committed release pair. Independent official
  clarification SRC-028 remains open.

- [ ] **VR-0023** (2026-11-02; ready-to-run): Validate grouped skip-reason
  reporting and explicit resource-wait measurements under full Linux and
  Windows xdist runs. Work: [browser concurrency benchmarking](TODO.md#performance-storage-and-build-tooling);
  change: `tools/run_checks.py`, `tools/pytest_startup_profile.py`,
  related focused tests, based on `841acbe0`; risk: low (diagnostic-only).
  Immediate: capacity/profile **15 passed**, runner **94 passed / 1 expected
  skip**, real Windows xdist skip-summary **94 passed / 1 expected skip**,
  12 browser tests passed with measured slot contention; Ruff, Pyright,
  docs and diff checks passed. Design: none.
  Linux first-pair evidence: at `c7901f1`, both eight-worker/four-lane
  runs passed **4,505 / 330 skipped**; two slots took **608.34 s** and
  four slots **420.25 s**, with measured cumulative Chromium waiting
  **2,777.73 s** and **1,072.94 s**, respectively. Grouped skip reasons
  reconcile all 330 cases. See `docs/testing.md` for methodology.
  Correctly grouped Linux full-suite pair at `413a2185`: both slot
  counts passed **4,520 / 330 skipped**; two slots took **503.49 s**
  with **750.74 worker-s** of measured slot waiting; four took
  **380.97 s** with **93.27 worker-s** waiting (24.3% faster in one
  pair). Windows full-suite 2/4-slot pair at `4bda6efb`: both reported
  **28 skips**, but only two slots passed (**4,843/28 in 672.40 s**);
  four slots had **4,842/28 with one Glossary browser visibility timeout**
  in **509.91 s**, despite 83.2% less measured slot waiting. The exact
  failure passed in isolation; see `testing.md`. Deferred: resolve this
  full-load failure, aligned Windows/Linux skip-source parity, alternating
  repeated clean comparisons and CPU/RAM monitoring. A new
  **failure-only Glossary diagnostic** captures the `/api/glossary`
  response and pending/loading/error/list/JS state on the original
  15-second timeout; three isolated normal Chromium widths passed
  **3/3**, including 390px in 6.43 s. Linux acceptance of
  the same committed test (`ce6d6d8b`) passed **3/3** in
  19.09 s (390px in 5.15 s), job
  `linux-dev:c827d624021a438a87a72f1c5fdf9ba0`.
  It changes no timeout, lane scheduling or default capacity,
  and does not yet establish the full-load cause.
  To make same-revision skip parity observable from the
  restricted async test-job interface, the check runner now
  automatically groups skip reasons for unfiltered full test
  suites (also `--all`); targeted and standalone-preflight
  reporting remains opt-in, with an explicit
  `--no-skip-summary` override. Focused runner regression
  passed **106 tests, one expected skip**; Ruff and Pyright
  passed. The grouped counts are now available from
  both same-revision full suites at `ea438555`: both reported
  **4,921 passed, 28 skipped, one shared non-browser
  deterministic-I/O failure**. Only **22** skips share
  grouped reasons. Windows skipped two Gunicorn fork tests
  and four symlink-privilege tests; Linux skipped six tests
  needing local PDFs or migration staging evidence. The
  newline-policy defect was fixed in `5e1cdbf6`, and
  **both** full suites at that revision passed: Windows
  **4,922/28 skipped in 537.68 s**, Linux **4,922/28
  skipped in 566.85 s**, with no failures or browser
  regressions. Six host-specific skip reasons on each side
  remain. Retire only after source coverage and other
  acceptance evidence are reconciled.

- [ ] **VR-0024** (2026-11-02; ready-to-run): Validate opt-in
  timestamped Chromium slot metrics and the timeline analyzer under
  real parallel Linux/Windows browser loads. Work:
  [Chromium concurrency benchmark](TODO.md#performance-storage-and-build-tooling);
  change: `tools/browser_test_capacity.py`,
  `tools/analyze_chromium_timeline.py`, focused regression tests;
  risk: low (metrics only; default admission unchanged).
  Immediate: **18/18** capacity/timeline tests passed in serial and
  two-worker xdist; twelve real Chromium browser tests passed with
  timestamped metrics (two-slot occupancy **11.04/12.40 s** observed).
  Ruff, Pyright, docs, and whitespace checks passed. Design: none.
  Linux evidence: at `f81cfa4a`, four slots passed **4,508 tests /
  330 skipped** in **418.90 s**; timestamped timeline found **284.29 s**
  at full capacity, but Scenario FAQ admissions spanned **seven workers**,
  exposing ineffective xdist lane grouping on Linux.
  The marker is now placed at item-collection time and opt-in lane runs
  report actual worker assignments, failing if any lane spans workers.
  Focused Windows eight-worker loadgroup: **12 passed**, two lanes
  confined to one worker each. Linux at `9f9e7eaa`: restored Scenario
  FAQ **232 passed, 16 skipped**, but lanes A/D still spanned five/seven
  workers, so the test stage failed its safety guard. This matches
  the pytest 9.2 / pytest-xdist 3.8.0 incompatibility: constrain
  pytest <9.2 and fail fast for known-broken loadgroup versions.
  Confirmed Linux recovery at `c39fb659`: `devbox` used pytest
  9.2.0 and pytest-xdist 3.8.0 before downgrading pytest to **9.1.1**.
  The targeted B/D browser-lane run passed **12/12 in 13.58 s**:
  B's six setup events stayed on `gw1`; D's six stayed on `gw0`.
  Linux at `413a2185` with pytest 9.1.1: **250 passed, 16 skipped**
  in **257.41 s**; lanes A/B/C/D each stayed on one worker, with Scenario
  FAQ split across A/D and the assignment guard passing. D remained the
  long tail (+254 s). At `413a2185`, the grouped full Linux
  2/4-slot pair passed **4,520 / 330 skipped** in **503.49/380.97 s**,
  with each of A/B/C/D assigned to one worker in both runs; the
  four-slot D lane still finished last (+377.62 s). Timestamped
  metrics are on `devbox` under `local/benchmarks/` (details in
  `testing.md`). The timeline reconstruction showed **437.69/182.22 s**
  at full capacity (two/four slots), with **0.22/0.09 s** waiting despite
  a free slot. Overlap warnings may include separate lock namespaces
  from capacity self-tests and post-unlock timestamp skew; they do not
  establish a resource-cap breach. New instrumentation records
  lock-directory provenance and pre-/post-unlock bounds, and the
  analyzer isolates the shared xdist lock namespace, distinguishing
  confirmed interval overlap from unlock-window ambiguity. Focused
  Windows tests passed. Linux at `25c0da5b` passed **36/36** targeted
  capacity, Page Footer and Sidebar Density tests (13.86 s); B/D lanes
  remained on individual workers and fresh metrics were written under
  `local/benchmarks/chromium-20261102-160356-356643/` on `devbox`.
  The updated analyzer selected the shared pytest lock namespace,
  excluded **13** independent capacity self-test records, found two
  admissions (peak **2/4** slots), negligible waiting and **no**
  same-slot-overlap warning; summed unlock uncertainty was **0.0001 s**.
  Targeted Linux namespace/overlap diagnostics are verified.
  Separate MCP `linux-dev` worker at `413a2185` initially skipped all
  12 B/D browser tests for missing Playwright, but after environment
  repair **12/12 real Chromium tests passed**. Its four-lane Scenario FAQ
  acceptance passed **250/16 skipped in 255.05 s** and showed **0.00
  worker-s** slot waiting with a +252.44 s lane-D tail. Windows full-suite
  2/4-slot timelines at `4bda6efb` measured **682.70/114.74 worker-s**
  of slot waiting; both lock namespaces were isolated correctly. The
  four-slot run failed one browser visibility timeout, independently
  reproduced as passing in isolation; see `testing.md`.
  An independent bounded host CPU/RAM sampler is implemented,
  recording host-wide CPU counter deltas and physical-memory
  usage as ignored JSONL alongside separate test jobs.
  Windows focused sampler tests **21/21** and a real native
  smoke probe **3/3 samples** passed (9.84% mean host CPU,
  71.18% mean RAM used); this is instrumentation evidence,
  not a browser benchmark. The matching Linux worker
  revision `74d00e7e` passed **21/21** focused sampler
  tests plus a native **3-sample** probe (mean 0.06%
  CPU busy and 9.32% RAM used); Windows and Linux
  instrumentation is now independently verified.
  Same-revision Windows/Linux full-suite samplers completed
  **157 samples each**, measuring 780 seconds while the tests
  lasted 517/571 seconds. Entire-window CPU mean and peak:
  Windows **60.31% / 100%**, Linux **30.07% / 99.96%**.
  Entire-window RAM mean and peak: Windows **78.16% /
  83.75%**, Linux **18.66% / 25.86%**. These durations
  include post-test idle time, **not** test-window-only
  averages. Default `-n auto` Linux observed **6,171.14
  summed Chromium worker-seconds** of setup waiting vs
  **1,560.39** on Windows, but worker counts differ and
  the runs both failed one non-browser I/O guard.
  A new read-only overlap-weighted
  `tools.analyze_test_host_resources` utility selects
  exactly the recorded pytest start/duration from these
  ignored captures and fails closed if the summary or
  99% interval coverage is absent. **11/11** focused
  analyzer tests and **15/15** test-section tests passed.
  The fixed-revision Windows full suite has **100%**
  sampler coverage, and its test-window-only CPU mean/peak
  was **86.05% / 100%** and memory mean/peak
  **70.45% / 72.41%**, not the lower all-window CPU mean.
  Matching Linux analysis is now verified: at `f9206e06`,
  the independent worker's analyzer tests passed **11/11**
  and its fixed-run capture has **100%** coverage across
  115 intervals, CPU mean/peak **41.22% / 100%** and
  memory mean/peak **23.24% / 25.66%** (job
  `linux-dev:eeac1d98f593419a9b273be7247edcec`).
  These unmatched worker-count runs do not establish a
  controlled browser-capacity comparison.
  Remaining: investigate the
  earlier four-slot Glossary failure; repeat alternating
  fully passing equal-worker/slot comparisons with
  concurrent CPU/RAM sampling and reconcile source
  coverage. Do not alter defaults or retire yet.

A VR entry records its ID/date/status (`awaiting-design`,
`ready-to-run` or `blocked`), the implementation revision/artifact,
immediate focused checks and results, any required VD dependencies,
deferred test selectors/gates, and the final execution outcome.
Retire it once required checks pass on the intended state and the outcome
is recorded. Failed or incomplete verification remains open.

## Next unused IDs

- Design: `VD-0007` (through `VD-0006` retired).
- Execution: `VR-0048` (`VR-0023`, `VR-0024` and `VR-0047`
  open; `VR-0044`–`VR-0046` and earlier entries retired).

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
  Outcome: <selector and design-sanity result, when performed>.

- [ ] VR-NNNN (YYYY-MM-DD; awaiting-design): <one implementation change>.
  Work: <TODO anchor>; revision: <commit/artifact>; risk: <level>.
  Immediate: <essential regression selector/result and required validators>.
  Design: VD-NNNN or none.
  Deferred: <existing module/full-suite/integration/manual checks>.
  Outcome: <tested revision, command, counts and evidence, when run>.
```
