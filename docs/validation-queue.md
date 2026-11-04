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
changes** (VR-0052/0053/0054; not yet due by the five-change threshold).

- [ ] **VR-0052** (2026-11-03; ready-to-run): Validate the
  Windows CP1252-safe JSON stdout change in
  `tools/audit_army_faction_semantics.py` from V1S-013.
  Work: [source inventory and gap batches](TODO.md#source-inventory-and-gap-batches);
  risk: low (audit CLI only; source data and runtime unchanged).
  Immediate Windows: `tests/test_audit_army_faction_semantics.py`
  **4/4**, direct actual-database CLI exit 0 (previously
  `UnicodeEncodeError`), Ruff on tool/test and full Pyright pass.
  Design: none; limited-encoding regression already added.
  Deferred: pinned committed-revision Linux focused module and
  cumulative full suite when the validation threshold is due,
  plus exact-SHA hosted CI. Retire only after checking those
  outcomes; final frozen-release acceptance remains separate.

- [ ] **VR-0053** (2026-11-03; ready-to-run): Validate
  the paired raw/application Army source-audit adapter and
  explicit current-only historical-review boundary from V1S-014.
  Work: [source inventory and gap batches](TODO.md#source-inventory-and-gap-batches);
  risk: low/medium (read-only audit tooling, no runtime changes).
  Immediate Windows: new `tests/test_paired_audit_connection.py`
  **3/3**, existing relationship **7/7**, Peripheral **6/6**,
  normalization **3/3**, published Unit relationship Chromium
  **1/1**, Controller API **1/1**. Actual source audits all
  pass in their applicable modes, and the five historical
  endpoint IDs remain unresolved under `--current-only`.
  Design: none; paired/mismatch/legacy tests added, with the
  original snapshot-bound guard kept.
  Deferred: pinned committed-revision Linux focused tests,
  cumulative full suite when the threshold is due, and
  exact-SHA hosted CI. A future separately approved
  re-review may rebind historical endpoint evidence; do
  not count this current-only mode as such approval.

- [ ] **VR-0054** (2026-11-04; ready-to-run): Validate the
  V1S-032A source-backed Command Token general reference and matched
  schema-v9 `rules.db` / deployed-object publication.
  Work: [Rules and contextual reference completion](TODO.md#rules-and-contextual-reference-completion);
  artifact: `data/generated/rules.db` SHA-256
  `e3d367cf881833d9a4820c1d659467e51556a249146c63d7d933769e3240e6aa`;
  risk: medium (new public canonical Rule plus tracked matched release pair).
  Immediate: deterministic double export, all 483 prior rule identities unchanged,
  source/API 3/3, Chromium 3/3 at three widths, baseline 49/49,
  rules database 166/166, curated rules 670/670, interactions 15/15,
  deployed-object publication 12/12 and maintained links 38/38;
  strict interaction audit, rules build, Ruff, Pyright and docs pass.
  Design: none; the source, publication, mismatch/rollback guard
  and normal-browser checks are implemented.
  Deferred: pinned Linux focused/full suite and exact-candidate hosted CI,
  including Source checks cross-platform deterministic rules/database
  output comparison. The final release-wide browser/source gate remains
  separately mandatory.

Infiltration fixed-PH source-47 review **VR-0051** retired at pinned
`dd071c4df04d6c90cddc1a84a6974952506a097d` after Linux
source-variant **100/100**, full-assets **5,014 passed / 29 expected
skips / zero failures**, and all three GitHub workflows passed. The
source-boundary and paired-publication details are in
[testing.md](testing.md#parallel-windows-development-and-linux-validation).
Final frozen-candidate release gates remain separate.

Combat Jump source-35 occurrence semantics **VR-0050** retired at
pinned `c1d8adc6cd547063ee5b8a85e831aa73cd4d4195`. The exact
N5.3 p. 89 Army variants cover **121 qualified/90 unqualified**
direct occurrences across six signatures, retaining landing-only
PH modifications and the separate one-use Explosion attack. The
guarded schema-v9 release refresh preserved unrelated records and
the paired deployed-object projection. Windows source-variant
**97/97**, curated **670/670**, rules DB **166/166**, data/build,
rules, Ruff and Pyright passed. The explicitly rebuilt ignored Linux
publication passed its matched-pair `--check`; Linux source-variant
**97/97** passed, and its full suite passed **5,011 / 29 expected
skips / zero failed** in **417.86 s pytest / 418.50 s runner** (job
`linux-dev:858b769b73294503b857031c802abf74`), with
**808/808** published SVGs, correct four-lane worker assignment,
**56.00 summed worker-seconds** of Chromium admission waiting and
two known Python 3.14 `fork()` warnings. GitHub Source Checks
(all four matrix jobs plus cross-platform deterministic outputs),
Installed Wheel Smoke and Deployment Smoke all passed. The
cross-Army variant usage index remains separate and unimplemented.

At pinned Linux commit `06ae1c4856d3213a3f03c88f7f6f219b23366ee7`,
the full suite passed **4,946 tests / 28 expected skips / 0 failures**
with 808/808 SVG assets. This retires VR-0040 (Army/Section and
Commlink browser context), VR-0041 (all published Reinforcement profile/
loadout source parity) and VR-0042 (all source-backed Commlink extras).
The preceding `5d6a30d8` run passed the same suite; a subsequent
fixed-tuple Pyright correction was retested on the final revision.
See [testing.md](testing.md#parallel-windows-development-and-linux-validation)
for the pinned jobs, warnings and residual scope. The independent
Chromium skip-reason and controlled capacity comparisons were tracked
under VR-0023/24, both now retired below. Git updates are explicit,
not background mirroring.

The later pinned Linux suite at `ad3314dc3da02ec3a9087b5361dcbdc1b374cabf`
passed **4,952 tests / 29 expected skips / 0 failures** with 808/808
published SVG assets. It retires VR-0043 (legacy staging freshness guard);
full evidence and the two existing `fork()` warnings are recorded in
[testing.md](testing.md#parallel-windows-development-and-linux-validation).
The independent Chromium diagnostics were tracked as VR-0023/24;
both were subsequently retired below.

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
VR-0024 and VR-0023 are both retired below.

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
timeout or cross-host source/skip parity. VR-0023 now documents
the environment-specific differences, while deeper investigation is
explicitly deferred to after v1.0. Linux keeps its opt-in four-slot
profile; Windows and CI remain unchanged.

Chromium cross-host skip diagnostics **VR-0023** retired at pinned
`955c55a02bf4aa74023313506105b29a6620c862`. The maintained
runner's `--skip-details` opt-in lists each skipped pytest node ID
and reason alongside independently controlled grouped skip counts;
it changes neither selection, admission slots, nor exit status.
Focused Windows capacity tests **25/25**, runner tests **108/one
expected skip**, Ruff and Pyright passed. With `--skip-details`
and full assets, Windows model tests passed **3,055/6 skipped**
(job `30eed8ebb1624bf6bc16d81bdb40167e`), Linux model
**3,049/12 skipped** (job
`linux-dev:07d181f703904818b9de7a07a58a313c`).
Exactly **six additional Linux model skips** come from five absent
ignored FAQ/N5.2–N5.3 PDF checks and one local migration report;
the other six model skips are shared, pre-promotion/opt-in cases.
Windows operations passed **363/five skipped**
(`4e04d81e25d047d7baeb324cc0715d90`); all five skips
are Windows symlink-privilege checks. Linux operations passed
**367/one skipped**
(`linux-dev:beaf812a636044818dc85d7c6026dd1a`), the skip
being a Windows-only native API test. Separately,
`tests/test_web_metrics.py` passed Windows **2/two skipped**
(Linux Gunicorn/fork-only cases) and Linux **4/4**. All compared
sections have zero failures; unequal skip counts are explicitly
environment-labeled, not falsely described as equivalent coverage.
The prior pinned four-slot Linux full suite at `47122aa5`
passed **5,001/29 skipped/zero failed**, and VR-0024 separately
retired the slot/resource instrumentation. The deeper analysis
of Windows full-load Glossary/Spec-Ops timeouts, Scenario FAQ
long tails, browser pooling, and optional identical PDF/staging
coverage is **deferred to the Post-1.0 backlog** in
[TODO.md](TODO.md#performance-storage-and-build-tooling).
The chosen Linux four-slot and Windows two-slot limits remain
unchanged. No new 1.0 validation obligation is created by this
performance investigation.

A VR entry records its ID/date/status (`awaiting-design`,
`ready-to-run` or `blocked`), the implementation revision/artifact,
immediate focused checks and results, any required VD dependencies,
deferred test selectors/gates, and the final execution outcome.
Retire it once required checks pass on the intended state and the outcome
is recorded. Failed or incomplete verification remains open.

## Next unused IDs

- Design: `VD-0007` (through `VD-0006` retired).
- Execution: `VR-0055` (`VR-0052/0053/0054` open; `VR-0051` and earlier entries retired).

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
