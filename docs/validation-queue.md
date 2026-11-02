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
  the due pass is addressed. A critical gate or an overdue item takes priority.
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
  mirror of Windows. When ready, batch compatible VR selectors into a
  pinned asynchronous `linux-dev` job with `expected_commit`; while it runs,
  Windows implementation may continue independently. A mismatch in the
  worker's Git revision, dependencies or source assets is an explicit
  dispatch blocker, not permission to sync Git or count skips as passing.
  Only a separate requested Git operation changes the Linux checkout.
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

Only open VR obligations belong here. **Current count: 5 distinct
changes** (VR-0023/0024/0026/0027/0028); the execution threshold is
reached. The next validation pass must address runnable work and its
prerequisites before another ordinary implementation pass. The oldest
recorded date is 2026-11-02. Windows and Linux checkouts are independent;
**no Linux Git update has been requested or performed** for the new
Discover/Parachutist changes.

- [ ] **VR-0027** (2026-11-02; ready-to-run; Linux checkout preparation
  pending): Cumulative/cross-platform verification of the reviewed
  Parachutist (Dep. Zone) source-33 parameter and guarded publication.
  Work: [source-variant reconciliation](TODO.md#100--current-reference-completeness-gate);
  implementation included in Windows `dev/v1.0.0` baseline
  `11c6562ed4a3c7960ae3e6e81838799ce9ba0230`.
  Immediate Windows: all 17 source signatures and owners verified in
  `tests/test_audit_source_variant_inputs.py` (**58 passed** at promotion);
  `tests/test_curated.py` (**651 passed**);
  `tests/test_rules_database.py` (**166 passed**), guarded
  staged/promoted v9 rules/deployed-object publication, 17 unchanged
  objects, data/rules build, Ruff, docs and diff checks passed.
  Design: none currently identified.
  Deferred: one cumulative Linux full-suite run on the **explicitly
  selected exact revision**, with verified browser dependencies and
  source/asset skip explanations; compare any platform-specific findings
  with Windows and execute any remaining release-required Windows check.
  Linux `worker="linux-dev"` requires a separately authorized Git
  checkout selection/sync and exact `expected_commit`. The pinned raw
  Army archive was checked on Windows; absent raw inputs on Linux must
  remain disclosed, not counted as independently source-verified.
  Retire after terminal results and evidence are recorded.

- [ ] **VR-0028** (2026-11-02; ready-to-run; Linux checkout preparation
  pending): Cumulative/cross-platform verification of the three exact
  Discover source-131 extras and guarded publication.
  Work: [source-variant reconciliation](TODO.md#100--current-reference-completeness-gate);
  Windows `dev/v1.0.0` combined baseline
  `11c6562ed4a3c7960ae3e6e81838799ce9ba0230`.
  Immediate Windows: source owners and fresh/published export
  `tests/test_audit_source_variant_inputs.py` (**60 passed**);
  `tests/test_curated.py` (**664 passed**);
  `tests/test_rules_database.py` (**166 passed**);
  13 Discover mutation cases, exact SHA-256 guarded rules/publication
  promotion with 17 deployed objects unchanged, data/rules builds,
  Ruff, docs and diff checks passed. Design: none currently identified.
  Deferred: the **same compatible pinned Linux full-suite job** as
  VR-0027 (do not duplicate the run), with explicit skip/source
  coverage and Windows-only checks where needed. Linux Git preparation
  is a separate explicitly authorized operation, not a side effect
  of test dispatch. Retire only for verified terminal acceptance.

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
  repeated clean comparisons and CPU/RAM monitoring. Retire only after
  the remaining evidence is recorded.

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
  Deferred: investigate this full-load failure, repeat alternating fully
  passing comparisons with CPU/RAM sampling, and reconcile cross-host
  source coverage. Retire only after the remaining acceptance evidence.

- [ ] **VR-0026** (2026-11-02; ready-to-run): Verify read-only
  Syncthing staging access through the separate `mcpworker` account.
  Work: [Syncthing staging](syncthing-assets.md#mcp-worker-policy);
  change: `tools/activate_synced_assets.py`, its focused tests and
  worker-specific environment configuration; risk: medium (host permissions
  and pinned private source data). Immediate: Windows activation tests
  **13 passed, 3 platform skips**; Ruff, docs and diff checks passed.
  Design: none. Deferred: apply `mcpworker` read-only ACLs and systemd
  staging-root environment on `devbox`; synchronize the updated tracked
  activation module to the worker checkout deliberately; verify `list`,
  one pinned snapshot hash and a dry-run activation through an asynchronous
  `linux-dev` job with zero unexpected filesystem changes. Do not grant
  staging writes or trigger activation automatically.

A VR entry records its ID/date/status (`awaiting-design`,
`ready-to-run` or `blocked`), the implementation revision/artifact,
immediate focused checks and results, any required VD dependencies,
deferred test selectors/gates, and the final execution outcome.
Retire it once required checks pass on the intended state and the outcome
is recorded. Failed or incomplete verification remains open.

## Next unused IDs

- Design: `VD-0007` (through `VD-0006` retired).
- Execution: `VR-0029` (`VR-0023`, `VR-0024`, `VR-0026`,
  `VR-0027` and `VR-0028` open; earlier entries retired).

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
