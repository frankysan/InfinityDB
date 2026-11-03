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

Only open VR obligations belong here. **Current count: 1 distinct
change** (VR-0023); no deferred test-design requirement is open.
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

Terrain source-58 review **VR-0047** retired at pinned
`333a091cb4336cb5cce0d9b0c2eae9b27c7abaa0`: source-variant
module **82/82** on Linux (`linux-dev:e4b0c232a25c499b8ff18941da38edad`),
and full Linux suite **4,977 passed / 29 skipped / 0 failed**
in **593.76 s** (`linux-dev:bbfa0a7fd0f64ab79e67e19041c371f3`),
with **808/808** published SVGs. Two existing Python 3.14
`fork()` warnings remain. All three GitHub workflows passed.
Chromium setup included **6,301.22 summed worker-seconds** of resource
waiting across 31 events; this is included in pytest wall time.
The unresolved `Religious Troop (Total)` source anomaly is unchanged.

Camouflage source-29 review **VR-0048** retired at pinned
`5ac294165a8be49a13125ba9324281b17b406264`: the matched
publication and Linux source-variant module passed **89/89**; the full
Linux suite passed **4,984 / 29 skipped / 0 failed** in **596.40 s**
(pytest; `linux-dev:ec597818137143ffa8cb26c741a8fd87`), with
**808/808** published SVGs. Existing Python 3.14 `fork()` warnings
persist. All GitHub workflows passed, including Source Checks after
rerunning its initially cancelled macOS job and final deterministic-
output comparison. No source-data or FAQ semantics changed during
the retry; the reviewed annotation remains metadata, not a match-state
tracker.

Linux host-only Chromium profile **VR-0049** retired at
`47122aa519b6d81c0b471797e9aa93ec77f4588a`.
On Linux the ignored `local/browser-test-profile.json` was enabled
explicitly and the maintained runner's generated command verified
**eight xdist workers, four slots, four lanes and Scenario FAQ A/D
split**. Focused profile tests passed **17/17**, operational section
**365/one skip**, and the pinned full suite
`linux-dev:33798d90fffe42caa22b2b2c697994c6` passed
**5,001/29 skipped/zero failures** in **422.07 s pytest / 422.72 s
runner**, with **808/808** SVGs, correct one-worker-per-lane assignments,
**54.42 summed worker-seconds** of Chromium admission waiting, and
two existing Python 3.14 fork warnings. Windows retained standard
`-n auto --dist worksteal` and the two-slot cap; its operational
section passed **361/five skips**. All three GitHub workflows passed,
including the cross-platform deterministic-output matrix. The
profile is host-local and reversible; the separate metrics gate
VR-0024 is retired below, while VR-0023 remains open.

Chromium metrics and timeline instrumentation **VR-0024** retired
at pinned `6177a8dc0befd544971913db010168254bf431fb`.
The maintained operations section passed **361 / 5 skipped** on
Windows (`708666f4030c45549c0737c36c90c95b`) and
**365 / 1 skipped** on Linux
(`linux-dev:36888a30c0b545d5b0e1d21e552a68ec`).
Independent two-/four-slot parallel browser runs at `5ac29416`
passed **600/16 skipped/zero failed** on both platforms, with
one-worker-per-lane guards passing; namespace-partitioned slot
timelines found **no confirmed same-slot overlap**. Full-duration
native CPU/RAM sampling covered **100% of each four host/capacity
test windows**, and the analyzer's overlap-weighted summaries and
per-worker slot wait/hold data were verified. Linux's repeated
four-slot run at `48d0cd84` also passed **600/16 skipped**;
its host-specific four-slot full suite at `47122aa5` passed
**5,001/29 skipped/zero failed** in **422.07 s**. All hosted
checks at `47122aa5` passed. This closes the metrics
implementation/verification obligation, **not** the Windows four-slot
timeout or cross-host source/skip parity, which remain with VR-0023.
Linux keeps its opt-in four-slot profile; Windows and CI remain
unchanged.

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
  regressions. Six host-specific skip reasons on each side remain.
  New same-revision eight-worker/four-lane browser comparisons at
  `5ac29416` passed **600 / 16 skipped / 0 failed** at both capacities
  on each host (Windows **481.83/402.56 s**, Linux
  **636.13/396.22 s**, two/four slots). The Glossary timeout did not
  recur; see `testing.md`. Retire only after alternating repeatability
  and the remaining host-specific source/skip differences are reconciled.
  At documentation revision `48d0cd84`, Linux four-slot repetition
  again passed **600 / 16 skipped** in **395.29 s**, while Windows
  four-slot repetition had **599 / 16 skipped / one Spec-Ops chart
  visibility timeout** in **434.84 s**. The user authorized a
  Linux-only four-slot default while retaining two slots on Windows;
  this is implemented as an ignored, opt-in host-local runner profile
  (VR-0049, retired), not a global or CI default change. The 12 s
  Spec-Ops chart acceptance timeout is unchanged; failure-only
  diagnostics now capture the active Unit/viewport, API results,
  browser errors and DOM state for a possible next recurrence.
  No Windows four-slot default increase is planned.

A VR entry records its ID/date/status (`awaiting-design`,
`ready-to-run` or `blocked`), the implementation revision/artifact,
immediate focused checks and results, any required VD dependencies,
deferred test selectors/gates, and the final execution outcome.
Retire it once required checks pass on the intended state and the outcome
is recorded. Failed or incomplete verification remains open.

## Next unused IDs

- Design: `VD-0007` (through `VD-0006` retired).
- Execution: `VR-0050` (`VR-0023` open; `VR-0024` and
  `VR-0044`–`VR-0049` and earlier entries retired).

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
