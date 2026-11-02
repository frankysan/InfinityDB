# Development checks

**Project domain:** Project infrastructure

`tools/run_checks.py` is the canonical local validation entry point. It keeps pytest, Ruff,
Markdownlint, offline documentation link checks, Pyright, Army database-build validation,
rules-database validation, asset policy,
worker selection, and optional reporting under one command contract.

The type-check stage explicitly passes the runner's interpreter to Pyright for dependency
resolution, so invoking the virtual-environment Python works without first activating that
environment in the shell.

Use the project virtual-environment interpreter when available:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py --profile code
```

On Linux/macOS use `.venv/bin/python` instead.

## Profiles and stages

The runner exposes seven stages:

- `test` — pytest;
- `lint` — Ruff;
- `docs` — Markdownlint plus offline local Markdown path/heading checks;
- `type` — Pyright;
- `build` — Army data/database build validation;
- `rules` - interaction-review coverage and generated-checklist validation, followed by
  curated rules validation/database build;
- `preflight` — isolated CI-parity check: rejects untracked non-ignored files, audits wheel
  contents from the index, installs declared dependencies in a fresh environment, and runs
  indexed Ruff, pytest and Pyright, verifies the release-artifact source binding, and
  smoke-tests the built wheel in another clean environment. It may download Python packages; see
  [CI preflight](#ci-preflight-clean-checkout-and-wheel-contents).

Named profiles are:

```powershell
# pytest + Ruff + Pyright
python tools\run_checks.py --profile code

# Army build + rules build
python tools\run_checks.py --profile data

# all stages
python tools\run_checks.py --all
```

`--profile all` is equivalent to `--all` and includes `docs`. The `code` and `data`
profiles retain their existing Python/data-only stage sets.

The documentation stage first runs the lockfile-pinned `markdownlint-cli2` dependency
with the project's `.markdownlint.json` rules, excluding local material,
dependencies and reports. It then runs `tools.check_doc_links` with the
same Python interpreter as the check runner to validate relative Markdown
paths and heading anchors across **all Git-tracked Markdown files**, including
nested references, plus new `docs/*.md` drafts before staging. Without Git
metadata it falls back to the main root, `docs/`, and `data/` references.
The link checker excludes ignored private files, does not access external
URLs, validate application routes or substitute for browser acceptance;
it checks ordinary inline links and reference definitions, not arbitrary
embedded HTML. Its file count can differ from Markdownlint's glob selection.
Install the Markdownlint dependency **explicitly** before `docs` or `--all`:

```powershell
npm ci --ignore-scripts --no-audit --no-fund
.\.venv\Scripts\python.exe tools/run_checks.py --stage docs
```

Node.js 22 or newer is required (CI uses Node.js 24). `npm run lint:docs`
runs **Markdownlint only**; use `--stage docs` for both checks or invoke
`python -m tools.check_doc_links` directly for the offline link audit.
The stage invokes the pinned installed tool via `npm run`, not `npx`;
checks neither install dependencies nor fetch packages automatically.
Bootstrap downloads happen only with the separate `npm ci` step.
Missing npm or dependencies cause an explicit check failure. No Node.js
build step is part of the application's runtime or packaging.

Requested stages continue after a failure by default so one run can report the complete failure set.
Use `--fail-fast` when the first failure is sufficient.
The final `preflight` stage is skipped if any earlier stage failed or could not start;
the summary reports `preflight SKIP` and retains the original failure status.

## CI preflight (clean checkout and wheel contents)

A local working tree can contain files that a fresh CI checkout never sees. Before
pushing a candidate, run the full Git-index preflight using the project virtual environment:

```powershell
.\.venv\Scripts\python.exe tools/run_checks.py --stage preflight
```

Use `.venv/bin/python` on Linux/macOS. The preflight:

1. Rejects **non-ignored untracked files** (`--allow-untracked` only warns).
   Git-ignored files are deliberately excluded.
2. Exports the **Git index**, including staged additions and staged content, to a
   temporary directory. It does **not** incorporate unstaged modifications to
   already-tracked files. Git executable modes and symlinks are retained; unresolved
   merges or unsupported Git index modes fail rather than being silently flattened.
   Symlink export on Windows requires the permissions needed to create links.
3. Runs pytest inside that index export, using the invoking environment's Python
   and dependencies. Before pytest it generates and checks the ignored deployed-object
   publication, matching the source CI setup. Arguments following `--` are forwarded to pytest.
4. Builds one wheel from the same export and checks that every indexed file under
   `src/` is present, including standalone modules and implicit namespace packages,
   except the explicit `src/infinity_db/web/static/logo/` design-source exemption.
   It also checks every source named by `[tool.setuptools.data-files]` in
   `pyproject.toml` is in the index and has a corresponding `.data/data/` wheel member.
5. In isolated mode, installs that wheel without dependencies or an editable source
   link in a second fresh environment outside the checkout. The shared
   `tools/installed_wheel_smoke.py` helper checks both CLI entry points, Army/rules
   builds, database health, installed configuration lookup, application routes, and
   operation after removing SVG directories from only that disposable installation.

To catch undeclared dependencies and reliance on ignored local evidence before
committing, use the isolated mode after staging the intended candidate:

```powershell
.\.venv\Scripts\python.exe tools/ci_preflight.py --isolated -- -n auto
```

`tools/run_checks.py --all` and `--profile all` include this isolated validation
automatically, after the working-tree checks. Run only that gate with:

```powershell
.\.venv\Scripts\python.exe tools/run_checks.py --stage preflight
```

The runner forwards `--test-workers`, `--test-dist` and its resolved asset selection
to preflight and isolated pytest. `--assets off` omits SVG-file checks while retaining
database schema and database/publication snapshot verification; `required` also checks
the complete indexed SVG publication. Preflight always checks the full indexed suite; positional targets
and `--test-section` narrow only the ordinary working-tree test stage. The ordinary
test stage retains access to local evidence and optional browser tooling, while the
isolated pass checks the environment and files available to a clean CI checkout.

This exports the same index, creates a fresh virtual environment without system-site
packages, installs only `.[dev,symbols]` from that export, prepares the publication,
and invokes the existing deployment-artifact verifier on the actual indexed databases
and publication manifest. It also runs the canonical Ruff stage against the index,
pytest (including full-asset tests when selected), and Pyright in that environment.
It does not inherit `PYTHONPATH`,
`PYTHONHOME`, a disposable Git-index override, or `PYTEST_ADDOPTS` that could mask tests.
Package installation is explicit in this mode and may download dependencies; it
does not acquire game sources. `--isolated` cannot be combined with `--skip-pytest`.
It uses the invoking Python version and local OS, so hosted portability checks remain
necessary. Ordinary preflight reuses installed packages and cannot detect a missing
declaration when a developer already has that package installed.

For a quick packaging/untracked check without repeating pytest or installing dependencies:

```powershell
.\.venv\Scripts\python.exe tools/ci_preflight.py --skip-pytest
```

`--skip-wheel` omits the wheel audit and installed-wheel smoke; combining the skip switches exercises
only index export and untracked-file checks. These are direct `ci_preflight.py`
options; the standard runner's `preflight` stage always uses `--isolated`.

**Limits:** Wheel member auditing checks presence, not byte-level equivalence. The
isolated installed-wheel smoke additionally exercises runtime/resource lookup; it
cannot prove every unexercised consumer's packaging requirements. Source tests, builds
and installed-wheel smoke run on the invoking OS/Python, so multi-platform byte
comparisons and production Docker startup still require their separate CI gates.
Indexed Markdown lint/link checks are not part of preflight; the ordinary `docs`
stage checks the working tree.
The wheel command uses pip's PEP 517 build isolation; it may require network
access for build requirements when those are not cached. It does not acquire
Infinity Army or wiki sources. Run the preflight again after staging intended
changes; a pass against the index does **not** validate unstaged code. The
dedicated regression cases are maintained in `tests/test_run_checks.py`;
see [the hosted CI contract](ci.md).

`.[dev]` includes PyMuPDF for PDF research tools and source-test collection.
Ignored official PDFs remain optional local evidence: only tests that actually read
unavailable source files skip. Curated-data, API and synthetic evidence-gate tests
still run in clean CI. A present PDF must pass its original hash and clause checks;
changed or malformed bytes are failures, not skips. Reinforcements authority/identity
mutation tests use synthetic PDFs in CI and never authorize historical N4 procedures
as current N5 rules.

## Targeted checks

For ordinary development, prefer the smallest check that exercises the changed contract before
running broader validation:

```powershell
python tools\run_checks.py --stage test tests/test_availability.py
python tools\run_checks.py --stage test tests/test_web.py::test_fireteam_chart_page_and_api_use_application_projection
python tools\run_checks.py --stage lint src/infinity_db/web tests/test_web.py
python tools\run_checks.py --stage type
```

Positional targets are passed to pytest/Ruff for their respective stages. The `docs` stage
always checks the configured Markdown set; `docs`, `type`, `build`, `rules`, and `preflight` ignore positional
targets. The runner accepts its documented options and test paths/node IDs, not arbitrary
pytest flags. For keyword selection or other pytest-specific options, invoke pytest directly.

**Check-report safety:** `--report` without a filename writes a timestamped
transcript under `reports/`. Prefer placing test selectors **before**
`--report`, or use `--report=reports/filename.txt` for an explicit
output file. The runner also recognizes a Python test target immediately
following a bare `--report`, preserving it as a test selector instead of
opening it as the destination. Reports cannot overwrite Python/source
files or any Git-tracked file. This protection addresses a 2026-11-02
Linux incident where `--report tests/test_verify_scenario_faq_browser.py`
caused argparse to interpret the test selector as a report filename,
truncating the tracked source and inadvertently selecting the entire
test suite. Restore the original test module with
`git restore --source=HEAD -- tests/test_verify_scenario_faq_browser.py`
on the affected checkout after verifying no intended local edits remain.

**2026-11-02 cross-host report-path regression (VR-0025):** At Linux commit
`413a2185`, `tests/test_run_checks.py` passed **99/99**. At Windows commit
`f90514f3`, it passed **98 with 1 platform skip**. The actual formerly
ambiguous invocation, `--stage test --report tests/test_domain_slugs.py
--assets off`, selected the intended test module and passed **8/8** on each
host, rather than interpreting its path as a report destination. Both
asynchronous jobs reported exit code zero and overall `PASS`. The focused
suite also verifies that source/data and Git-tracked report destinations are
rejected without overwriting files. This retires VR-0025; release and hosted
CI gates remain independent.

Direct tool commands remain appropriate when debugging the tool itself:

```powershell
python -m pytest tests\test_specific.py -q
python -m pytest tests/test_web.py -k fireteam -q
python -m ruff check path\to\file.py
python -m pyright
```

Do not report Ruff/Pyright as run when those tools are unavailable in the active environment.

## Phased development and validation

For ordinary v1.0 development, split work into **implementation**, **test design**,
and **test execution** passes. This minimizes redundant full-suite runs without
weakening targeted checks, required CI, or [release acceptance](releasing.md).
The [validation queue](validation-queue.md) owns pending obligations and their
status; `docs/TODO.md` continues to own features, fixes, and milestone scope.

1. **Implementation pass:** define expected behavior and a minimum acceptance
   check before editing. Implement a bounded change and inspect its diff.
   **Create an essential focused regression now** if existing tests cannot
   demonstrate the changed contract or safely catch its immediate failure.
   **Execute only essential checks now**: selected test node IDs (or the
   smallest suitable module if targeting is impractical), required local
   lint/type/docs/data checks, and any migration, provenance or publication
   integrity guards. A change is not safe merely because its broader tests
   are queued. Avoid automatically running whole neighboring test modules,
   full profiles, or the complete suite just because they are available.
   Record additional desired regression assertions as VD items, and deferred
   execution against this distinct change as a VR item. Include the exact
   immediate test names/results and the checks still missing. Report
   `implemented; broader validation pending` until required verification
   is complete.
2. **Test-design pass:** batch **nonessential additional test design** from
   open VD requirements: add assertions, edge cases, negative cases and
   fixtures without unrelated production changes. Reuse existing tests.
   Execute each newly added or edited test directly as a *design sanity
   check*, not a substitute for a later broader execution pass. Record
   exact selectors/results and unblock linked VR items; fix a defective
   test here, but send newly discovered product defects to `docs/TODO.md`.
   Retire designed VD items after successful sanity checks, carrying any
   needed selectors or dependencies into still-open VR items.
3. **Test-execution pass:** batch **deferred verification** across ready VR
   changes: relevant existing module suites, integration/browser checks and
   cumulative full-suite/profile checks. Prefer a single shared run for
   overlapping requirements; do not re-run equivalent modules separately
   for each task. Record the exact tested revision, commands, pass/fail/skip
   counts and evidence. Close a VR item only when its required checks have
   passed on the relevant state. Retire verified VR entries from the active
   queue after recording their outcome; Git history preserves the record.
   Keep failed or blocked verification open.

**Four kinds of test work:** essential *creation* (write the minimum
regression needed to trust this change now); deferred *design* (queue
additional tests as VD); essential *execution* (run the direct regression
and risk-critical checks now); deferred *execution* (queue broader runs
as VR). Creating a test and running that specific test is permitted during
implementation or test design; it does **not** authorize automatically
running the entire surrounding module. Existing tests to rerun require
VR work, not a VD entry. Avoid speculative VD entries when no concrete
missing behavior or assertion can be described.

**Scheduling:** At **5 open VD requirements**, the next pass must be test
design. At **5 distinct implementation changes with open VR verification**,
the next pass must be test execution (after any blocking design). If both are
due, first design what execution needs. Each open item also becomes due
**7 calendar days after recording**, irrespective of count. Check the queue
before and after each pass and do not start unrelated ordinary implementation
while a mandatory pass is due. The thresholds are batching triggers, not
limits on how many checks a pass may execute.

**Never defer essential checks:** validate the changed contract with a
direct existing or newly written regression and appropriate static/structure
checks. Migrations, schemas, artifact/publication integrity, provenance,
security, compatibility boundaries and correctness-critical player-facing
rules require immediate risk-appropriate coverage and verification.
Run a larger module or suite **immediately only when** narrow checks cannot
reliably establish safety, when diagnosing/fixing a failure, or when a
required integration/acceptance gate is due. Such an exception is explicit:
state what risk requires it and what was run. Conversely, deferring a
broader suite is not a waiver of any relevant immediate regression.
Existing push/pull-request CI runs on its configured triggers; its checks
are not disabled, postponed, or replaced by this local queue. Before merge,
deploy, tagging, or release-candidate acceptance, clear all relevant VD/VR
obligations and run the gates in `docs/ci.md` and `docs/releasing.md`.
Unrelated post-release work must remain classified in TODO.

A bounded implementation with successful **relevant immediate checks** may
be reported as implemented, but not as fully validated if VD/VR obligations
remain. Distinguish precisely between `implemented`, `targeted checks passed`
and `acceptance validated`; never report an unrun test as passed. This
respects local validation requirements without requiring an unconditional
full-module/full-suite run after every ordinary implementation. Keep check
evidence and deferred obligations explicit in agent handoffs. The workflow
does not change `tools/run_checks.py`, its profiles or hosted CI execution.

**Parallel work while a test job runs:** An asynchronous test job does not
require the agent to idle. Continue with read-only audits, source inspection,
planning, issue triage and analysis, and poll the job as needed. Avoid any
write to files, databases, staged publication artifacts or fixtures the
running tests might read or modify; tests operate on the live checkout, not
an automatically frozen snapshot. If parallel mutations are necessary,
isolate the test run in a separate worktree/environment and verify which
revision and artifacts it tested. Never treat a job result as acceptance
for edits made after its tested state. Concurrent CPU/IO-intensive tasks
can also affect test timing and Chromium stability, so limit contention.

**Workspace MCP execution:** The connected MCP server requires test workloads
to use its asynchronous job interface. Use `start_test_job` for ordinary
pytest or unittest selectors and `start_script_job` for a tracked custom
runner such as `tools.run_checks` (including complete validation profiles).
Recover job IDs with `list_script_jobs`; poll incremental output through
`poll_script_job` using its returned byte offset; cancel explicitly through
`cancel_script_job` when necessary. Synchronous `run_checks` test/code/all,
`run_tool` unittest, and recognized test-launching `run_script` modules
refuse test execution with `tests_require_job`. This restriction applies to
the MCP tools, not to the local PowerShell CLI. A dropped MCP request or
client stream does **not** establish a pytest result: require the job's
terminal status, subprocess exit code, and final report. For the recent
Windows suite (~8–10 minutes), allow **1,800 s** for full pytest and
**3,600 s** for a full validation profile (server job maximum: **7,200 s**).

**2026-11-02 schema-preserving staging regression (VD/VR-0006):**
`tests/test_legacy_staging_schema_guards.py` reconstructs pending
deployed-object citation, terrain/scenery, and Hacking Device citation
inputs under disposable pytest directories. All three staging paths
pass: each preserves schema-v9 and the 14 reviewed Restrictions,
produces a matching 17-object publication fingerprint, and leaves
the active checkout unchanged. Focused tests: **3 passed**.
The eight-worker `worksteal` cumulative suite on `dev/v1.0.0`
based on `6cc2f1e`, including the new working-tree tests, passed
**4,701 tests, 25 skipped, 0 failed** in **552.19 s** (async job
`c21786aaa9504047bf74437904e21d5e`; ignored report
`local/validation-vr0006-full-20261102.txt`). Ruff, Pyright,
docs and diff checks also passed. This retires the local VD/VR-0006
obligations, not hosted CI or release-candidate acceptance.

## Source-test tail profiling and browser isolation

The default pytest configuration reports the 20 slowest setup/call/teardown
durations, including local runs (CI already requested those durations). This
identifies slow individual cases but not idle time spent by other workers.

An automatic controller-side `xdist startup and collection timings` summary
reports elapsed time from xdist worker-spawning to first/last worker ready,
first/last worker collection complete, and first dispatched test. The check
runner also passes a monotonic launch timestamp into pytest, allowing the
summary to measure **process launch to xdist worker-spawning** (interpreter
and pytest initialization) and **process launch to first test**. For a direct
`python -m pytest` invocation, the pre-xdist interval is explicitly marked
unavailable. The durations overlap, require no extra report files, and do
not modify test scheduling. Serial runs omit the xdist summary. Retain the
runner's total elapsed time for broader performance comparisons.

On 2026-10-29, running five non-browser test sections with 8 workers took
**94.91 s** (2,669 passed, 3 skipped), and the browser section with two
grouped workers took **143.21 s** (152 passed, 16 skipped). The combined
**238.12 s** did not materially improve over the **239.25 s** unified run.
Neither older report separated worker bootstrap from collection, so the cause
of the observed browser startup delay remains unmeasured until the new
instrumentation is run.

Browser verifier modules have their own maintained `browser` section, separate
from the `web` HTTP/API tests. A complete suite still includes both. For
independent diagnosis or CI job partitioning, use:

```powershell
.\.venv\Scripts\python.exe tools/run_checks.py --stage test --test-section browser --test-workers 2
.\.venv\Scripts\python.exe tools/run_checks.py --stage test --test-section web --test-workers 2
```

The browser section includes the real Chromium scenario FAQ and Weapon card
matrices. They exercise repeated page navigations, desktop/mobile renderings,
and all maintained source-to-DOM cases. Splitting jobs can isolate this work,
but the slot limit also determines concurrency within each job.

On local Windows (2026-10-29), paired two-worker `--dist worksteal` runs
with otherwise identical tests measured **80.7 s (one slot) vs 49.7 s
(two slots)** for the Scenario FAQ browser module (54 passed, 16 skipped),
and **73.1 s vs 52.3 s** for the Weapon cards browser module (23 passed).
These are single-run comparisons, not a full-suite benchmark. The previous
one-slot runs showed lock waits of approximately 76 s and 69 s in setup.
The subsequent full `-n auto` run on 2026-10-29 passed all
2,812 tests (19 skipped) in **246.85 s**, confirming that two browser slots
remain stable under the workstation's normal worker count.

## Chromium concurrency under pytest-xdist

**Linux worker validation, 2026-11-02:** Ubuntu `devbox` (16 vCPUs,
approximately 15 GiB RAM, Python 3.14) passed the complete seven-stage
`tools/run_checks.py --all --build-source tests/fixtures/deployment-smoke
--test-workers 6 --assets required --report` command at commit
`16560d038a611d23128a60e7b29781f6f0077d0c`. The ordinary test stage
reported **4,492 passed, 330 skipped, 2 warnings in 546.85 s**; the
isolated Git-index CI preflight passed in **262.10 s**, including wheel
and deployed-asset verification. Ruff, docs, Pyright, synthetic Army
build and curated rules all passed. The two warnings concern Python 3.14
forking a multithreaded process in web-metrics tests, not assertion
failures. A prior `-n auto` (16-worker) run on the same commit passed
the same **4,492/330** split in **549.94 s**; these single runs do not
show a speedup from increased workers with two Chromium slots.

This Linux checkout lacks some Git-ignored source evidence: its
**330 skipped** tests contrast with a previous Windows full-suite run
of **4,797 passed / 25 skipped** (both totals are 4,822 collected).
Investigate actual skip reasons and reconcile input availability
before treating the hosts as coverage-equivalent; the differing source
states also prevent a controlled cross-host speed comparison. This
Linux run predated the separate resource-wait reporting implementation,
so its multi-minute pytest setup durations are not decomposed into
waiting versus other setup.

For a concise source-coverage audit, the runner now accepts optional
`--skip-summary` on test/preflight stages. It groups **actual pytest
skip reports** by reason and count, rather than printing hundreds of
individual `-rs` entries; the total must reconcile with pytest's
skipped count. This is opt-in and does not alter collection or execution.
Record the reasons from Linux and Windows at the same commit, then
synchronize only the pinned source files needed for parity.

**Linux paired slot-limit experiment, 2026-11-02:** On `devbox` commit
`c7901f1abc8e9d0d128f30283e74cf817bc733f4`, two sequential full test
runs used eight xdist workers, `browserlanes`, four grouped browser lanes,
`--split-scenario-faq`, `--assets required`, `--browser-metrics`, and
`--skip-summary`. Only the Chromium slot count changed:

- **Two slots (default):** **4,505 passed, 330 skipped, 2 warnings** in
  **608.34 s** (runner 608.99 s). Measured Chromium admission waiting
  totaled **2,777.73 worker-seconds** across 17 setup events; the longest
  individual wait was **485.80 s** within **489.59 s** of pytest setup.
  Report: `CHECKS 20261102-131906.txt`.
- **Four slots:** identical **4,505 passed, 330 skipped, 2 warnings** in
  **420.25 s** (runner 420.87 s). Measured admission waiting totaled
  **1,072.94 worker-seconds** across 17 setup events; the longest wait
  was **263.01 s** within **265.28 s** of pytest setup.
  Report: `CHECKS 20261102-132923.txt`.

Increasing from two to four slots shortened the test stage by **188.09 s
(30.9%)** and reduced *summed worker waiting* by **1,704.79 s (61.4%)**.
Worker waiting is concurrent and must not be interpreted as elapsed wall
time. The same two Python 3.14 multithreaded-`fork` deprecation warnings
were reported in both runs. Neither run changed the existing test default.

The grouped skip-reason report reconciled all **330 skips across 50 reason
strings** in each run: **307 missing pinned/local source evidence** (Army
archives/raw DBs and rules/FAQ/historical PDFs), **17 intentional opt-ins
for release-matched rebuilt databases**, **5 pre-promotion checks now
inapplicable because migrations/citations were promoted**, and **1 absent
local migration staging report**. The missing-source grouping is based on
the reported reasons, not a file-by-file inventory; selective source
transfer and a matching Windows skip-reason comparison are still needed.

These are **two single measurements in one order**, not an alternating
repeated benchmark. Four slots substantially help but retain over a
thousand worker-seconds of admission waiting; do not promote four slots
as the default until repeated A/B/A trials, CPU/RAM observations and
cross-platform release stability checks pass.

**Per-worker JSONL analysis (the two archived `chromium-*/` directories):**
The slot files record completed acquisitions and holds, not a continuous
occupancy timeline. The two-slot run recorded **60 admission records**,
**1,004.96 aggregate slot-held worker-seconds**, and **2,777.73
worker-seconds waiting**. Its two operating slots were occupied for
**509.90/608.34 s (83.8%)** and **495.05/608.34 s (81.4%)**. Extra
near-zero records for slots 2/3 belong to admission tests and do not
signify ordinary Chromium capacity beyond the configured two slots.

The four-slot run recorded **74 admission records**, **1,173.90
aggregate held seconds**, and **1,072.95 waiting seconds**. Its slots
held **309.08/420.25 s (73.5%)**, **292.84 s (69.7%)**, **290.17 s
(69.0%)**, and **281.81 s (67.1%)**. These percentages approximate
individual-slot utilization relative to total pytest duration; they do
not establish CPU utilization or the exact overlap pattern. The
aggregate held duration *increased* by about **16.8%** with four slots,
so gains in elapsed time are not proportional to reduced total work.

Scenario FAQ was the largest admission holder in both configurations:
**464.09 held seconds** (46.2% of all held time) over four records
with two slots, versus **529.37 held seconds** (45.1%) over six records
with four. Its longest individual holds were **228.73/224.86 s**
with two slots and **132.39/130.26/129.00/126.17 s** with four.
Other notable four-slot holders were Weapon source cards (**163.63 s**),
Unit Skill presentation (**125.85 s**) and Fireteam context
(**106.00 s**); the latter incurred **526.56 s** of cumulative slot
waiting despite only 106 seconds held. Ammunition publication's
cumulative wait fell from **997.18 s** to **51.33 s**.

The instrumented Chromium lifecycle files contain only **15 launches
totaling 2.29 s** (two-slot run) versus **18 launches totaling 2.81 s**
(four-slot run). Both recorded **120 `new_page` operations** (15.50
versus 17.14 s total). Only explicitly timed browser fixtures are
included; do not mistake these for every browser/context operation
in the suite. Chrome startup cost is negligible compared with admission
waiting.

**Timestamped slot instrumentation (opt-in, after the November 2 archive):**
The Chromium admission JSONL retains `wait_seconds`, `hold_seconds`,
`pid`, `label` and `slot`; it additionally records `worker` (xdist
worker ID or `main`) and monotonic `request_monotonic_seconds`,
`acquired_monotonic_seconds` and `released_monotonic_seconds`.
Acquisition is timed after securing the OS lock; release is measured
after unlocking. Monotonic timestamps are comparable **between processes
on the same host within the same run**, not across hosts or reboots.
This instrumentation does not change slot admission, test isolation or
scheduling and does not require running a permanent monitor.

The tracked offline analyzer `tools.analyze_chromium_timeline` reconstructs
concurrent admission requests and held slots from completed, timestamped
JSONL records. Run it after an instrumented benchmark, e.g. from the
repository root on `devbox`:

```bash
./.venv/bin/python -m tools.analyze_chromium_timeline local/benchmarks/chromium-RUN --slots 4
```

Use the actual `local/benchmarks/chromium-*/` path printed by the runner.
The analyzer prints observation span, aggregate waiting and held time,
peak queued admissions, peak occupied slots, full-capacity time,
time with queued requests despite a nominal free slot, and the
heaviest module holders, with observed worker IDs and distinct PID
counts for each. It excludes records above the configured
slot count, because capacity-fixture self-tests can independently
acquire additional test-only slots. It **refuses older duration-only
JSONL** rather than inventing a concurrency timeline. Completed
admissions are not a lossless event log: interrupted holders or
timeouts may be absent, and similarly numbered slots from test-only
lock directories are not necessarily the same resource. Apparent
free capacity while waiting therefore merits further examination,
not an immediate scheduler conclusion.

A focused Windows real-Chromium xdist smoke run at `ce07106e`
passed **12 tests** in **13.78 s** with four pytest workers and two
slots (`--browser-metrics` directory
`local/benchmarks/chromium-20261102-140301-32228`).
The analyzer reconstructed **12.40 s** of observed admission activity,
**11.04 s** with both slots held, **16.27 worker-seconds** waiting,
and just **0.06 s** with a queued request and nominally free capacity.
Peak admission queue length was three. These numbers describe the
recorded Chromium locks, not whole-suite utilization.

**Linux grouped-lane regression, 2026-11-02:** A subsequent full
four-slot Linux run at `f81cfa4a` passed **4,508/330 skipped** in
**418.90 s**, with **1,075.27 worker-seconds** of slot waiting.
Timestamped metrics reconstructed **378.58 s** of browser-admission
activity, **284.29 s** with all four slots occupied, and just
**0.55 s** of queued admission with nominally free capacity.
However, Scenario FAQ occupied slots on **seven xdist workers** and
Ammunition publication on **eight**. The Linux pytest report lacked
the `@chromium-*` test grouping suffix and browser-lane timing output,
unlike Windows. This invalidates interpreting the run as effective
four-lane scheduling; the 4-slot capacity result remains valid.

An initial hypothesis was hook ordering: the dynamic `xdist_group`
marker was moved from `pytest_collection_modifyitems` to
`pytest_itemcollected`, before the pytest-xdist collection hook.
This was insufficient on Linux. The likely underlying cause is
a known dependency incompatibility: **pytest 9.2.0** introduced
structured internal node IDs; **pytest-xdist 3.8.0** still rewrites
the old internal `_nodeid` field for loadgroup. Group markers remain
visible, but loadgroup silently distributes those tests as ungrouped.
The Linux environment was confirmed to have pytest **9.2.0** and
pytest-xdist **3.8.0**. Until upstream releases a compatible xdist
version, InfinityDB's `.[dev]` dependencies constrain pytest to
**`>=8.0,<9.2`**.
The startup profiler rejects the known-incompatible
pytest/xdist combination on `--dist loadgroup` with an actionable
message, before test collection. This is a safeguard, not a monkeypatch
of pytest internals or a change to normal worksteal scheduling.

The controller-side report prints each `chromium-*` lane's **actual**
worker and setup count; an explicitly grouped run fails if a lane
executes on multiple workers. A focused Windows eight-worker loadgroup
check passed **12/12** with lane B on `gw1` and lane D on `gw0`.

The attempted Linux verification on 2026-11-02 at
`d848609d` **does not constitute a scheduling acceptance run**.
The command placed the test path directly after bare `--report`;
argparse consumed that path as the report destination and overwrote
`tests/test_verify_scenario_faq_browser.py`. Pytest consequently
collected the entire suite, could not import the corrupted module,
and produced nine dependent reference-baseline failures plus a
collection error (**4,268 passed, 314 skipped**). This run
is invalid benchmark evidence. The runner now normalizes the ambiguous
`--report`/test-target combination and refuses to overwrite source
or tracked files.

The restored Linux checkout at `9f9e7eaa` then ran the intended
Scenario FAQ selection: **232 passed, 16 skipped in 135.17 s**, but the
runner correctly reported **FAIL** because lane A's 112 setup events
were distributed over **five workers**, and lane D's 136 events over
**seven workers**. Measured Chromium waiting was **506.61 summed
worker-seconds** across four setup events; this is not proof of
correct lane scheduling. No test assertions failed. The attempted
early-marker fix is therefore not sufficient on that Linux install.

**Confirmed Linux recovery:** At commit `c39fb659`, devbox
downgraded pytest from **9.2.0 to 9.1.1**, retaining pytest-xdist
**3.8.0**. A focused `browserlanes` acceptance run with eight xdist
workers, four configured lanes and four Chromium slots selected only
`test_verify_page_footer_browser.py` and
`test_verify_sidebar_density_browser.py`. All **12 tests passed**
in **13.58 s**, runner duration **14.03 s**. Browser lane B ran six
tests solely on `gw1`, and lane D ran six tests solely on `gw0`;
the lane assignment guard passed. This confirms the incompatibility
resolution for the observed two lanes, but does not yet validate the
Scenario FAQ A/D split or all four lanes together.

**Next Linux acceptance:** At the same compatible dependency
versions, run the Scenario FAQ module with `--split-scenario-faq`
and confirm A/D each stay on one worker. Then execute the full
browser section (or full suite) with all four lane groups and repeat
two-/four-slot benchmarks under the **working** scheduler.
Do not compare the older dispersed-worker full-suite measurements
as if they were grouped-lane baselines. Collect CPU/RAM samples
separately.

### Measured waiting versus pytest setup

Pytest's native `setup` duration includes time blocked acquiring a Chromium
slot. This is **waiting**, not active fixture initialization; the two numbers
must not be added. InfinityDB's `tools.pytest_startup_profile` plugin now
records Chromium-slot acquisition waits during setup and transfers their
durations through pytest's `user_properties` to the xdist controller. For
significant waits (at least 50 ms), the final console report displays:

- **Measured resource waiting**: time blocked before acquiring a Chromium
  slot, summed across worker processes (not wall-clock elapsed time).
- **Remaining setup**: the original pytest setup duration minus the measured
  wait. This is *not* guaranteed active CPU work: other waits remain
  uninstrumented.
- **Original pytest setup**: unchanged, for comparison with historical results.

The displayed largest-wait examples are individual test setup events; a
module-scoped fixture's slot wait is charged to the first test executing that
fixture on each worker, not distributed across all cases in the module. Tests
blocked in a slot admission timeout also report their measured waiting.
The existing `--browser-metrics` JSONL slot records remain optional and
independent of this console report. This profiling change does not increase
Chromium concurrency or alter test assertions, fixture scope, scheduling,
or timeouts. A separate future improvement can expose live queued/waiting/
setup/running/teardown states to the MCP job monitor.

Full local checks retain `-n auto --dist worksteal` by default; the worker
count is not reduced for browser acceptance. The 2026-10-29 full suite varied
from 246.85 s to 305.64 s despite both runs passing. The latter showed
browser module fixture setup waits up to 142 s, suggesting contention and
repeated module setup when worksteal distributes one module among workers.
This is not evidence that fixture teardown or pytest post-processing is slow.

The runner also supports `--test-dist loadgroup`. It assigns all
Chromium-gated browser module cases to the same xdist worker, while other
tests remain individually schedulable. The grouping marker is added in a
`tryfirst` collection hook, before xdist generates grouped test IDs.
A full Windows run on 2026-10-29 passed 2,821 tests (19 skipped) in
**247.43 s**, nearly identical to the best worksteal run of 246.85 s.
The grouped run exposed another issue: mock-only
`test_verify_rule_fragment_browser.py` waited **118.09 s** for a Chromium
slot even though no tests in it launch a browser. That module is now excluded
from slot admission and grouped scheduling, retaining its test coverage.
Three mixed modules, `test_verify_release_candidate_browser.py`,
`test_verify_deployed_object_publication_browser.py`, and
`test_verify_unit_skill_presentation_browser.py`, now acquire slots only
for explicitly identified real-Chromium tests. Unit Skill's pure database
and DOM-contract tests no longer wait for slots. Modules with shared
module-scoped Chromium fixtures retain module-wide slot protection.
The `loadgroup` option remains opt-in. The latest full `worksteal` run
passed 2,826 tests (19 skipped) in **211.53 s**, with the first test starting
4.14 s after process launch. Remaining large setup durations arise from
Chromium-slot contention rather than process startup.

An additional experimental `--test-dist browserlanes` mode uses xdist's
`loadgroup` scheduler but maps all real Chromium browser modules to **two
stable scheduling lanes**. Each lane is owned by one xdist worker; other
tests remain independently schedulable across workers. This prevents idle
pytest workers from waiting on Chromium locks, while retaining the two-slot
lock as a safety limit. Source-backed Unit, Scenario FAQ, and release browser
tests occupy lane A; Weapon cards and the remaining browser modules occupy
lane B. The mock-only verifier module is not assigned to either lane. These
assignments are provisional estimates of execution cost, **not** guaranteed
balanced work. Group order matters: xdist's `loadgroup` scheduler inherits
`loadscope` scheduling, which normally assigns the groups with the greatest
**number of cases** first (not the greatest estimated runtime). The two
Chromium groups are therefore expected to start early, but the default
scheduler does not balance their actual durations. The startup profiler now
prints the first start and last teardown for each browser lane, plus the
first non-lane test start, to verify overlap and diagnose a late-running lane
without creating per-step reports. Compare the same full test command with
the baseline:

```powershell
.\.venv\Scripts\python.exe tools/run_checks.py --stage test --test-dist browserlanes
```

Full Windows benchmarks on 2026-10-29 did **not** validate this mode:
**240.41 s** (one local JavaScript-request failure in release-candidate
Chromium acceptance) and **222.88 s** (one Fireteam page visibility timeout),
versus the passing **211.53 s** worksteal baseline. In the second run, both
lanes started **3.63 s** after xdist spawned and finished at **221.79 s**
and **222.35 s** respectively; non-lane tests also started at 3.63 s.
This rules out late lane scheduling as the explanation. The long, nearly
suite-length lanes limit scheduling flexibility, and the observed browser
failures under full load remain unproven root-cause-wise. Keep
**worksteal as the recommended default**; do not promote this experimental
mode without both a passing full run and reproducible speedup. The Fireteam
browser test now records browser request, HTTP and JavaScript diagnostics on
visibility timeout without weakening its assertions. No new report snapshot
is needed unless recording a release milestone.

The **2026-11-01 v1.0 cumulative verification** adds a passing browser-lane
data point, but does not establish a faster default. With eight workers,
ordinary `loadgroup` completed **4,697 passed, 25 skipped, 1 failed**
in **462.38 s**; the failed Chromium cohort reported a transient local
server `ERR_CONNECTION_REFUSED` and passed in isolation. A subsequent
`browserlanes` full run completed **4,698 passed, 25 skipped** in
**595.85 s**. Its two Chromium lanes avoided this particular failure but
ran **133.47 s longer** than the unsuccessful loadgroup attempt; this is
not a controlled performance comparison or proof of the failure cause.
Continue to treat worksteal as the default and select browserlanes
explicitly when validating contention. The passing asynchronous job
(`e0806dee270e45638f1f348cea85d223`) wrote its detailed report to
ignored `local/validation-queue-vr0001-vr0005-browserlanes-20261101.txt`.
Completed VD/VR entries were retired from the active queue; the final
release candidate still needs its own acceptance evidence.

During an xdist run, `tests/conftest.py` admits **at most two Chromium
slot holders concurrently** across workers using cross-process OS file locks
in the per-run pytest temporary directory. For modules with shared browser
fixtures the slot spans the module; mixed modules acquire it only around
browser-dependent cases. Unrelated tests continue on available workers.
Locks release even if a worker process exits unexpectedly; normal serial tests
and environments without Playwright do not acquire them.
`tests/test_browser_test_capacity.py` covers cross-process exclusion and reuse.
The lane registry also includes Orders/AROs, Ammunition publication, and
Immunity/Plasma browser acceptance; its coverage test requires every real
Chromium module in the maintained browser section to have a lane.

The Unit Skill acceptance matrix is split into independently scheduled
pytest cases for default Units, complex profiles, optional flags, source-backed
optional variants, and distance conversions. Each case reuses one Chromium
instance across its viewports and Unit scenarios, while distinct cases can
occupy the two available browser slots. The browser waits for `domcontentloaded`
and then explicitly for visible Unit content rather than waiting for
`networkidle` on every navigation. The suite's real HTTP server remains
available for independent API requests and source-backed selection; the
browser's same-origin page requests use the WSGI adapter. Standalone verifier
calls continue to create and close their own browser. In a focused Windows
two-worker run, the five cases passed in **37.53 s** and the complete Unit
browser module passed **33 tests in 40.01 s**, compared with an approximately
79-second serial monolithic Unit matrix before these changes. The
subsequent full auto-worker run also passed.

Long-running catalog render checks retain bounded deadlines and report HTTP,
JavaScript, failed-request and page-status evidence on failure; none silently
retry a failed page. The Army overview, Weapon, deployed-object and Fireteam FTO
browser suites intercept same-origin page requests and serve them directly from the application
WSGI callable using `tools/browser_wsgi_transport.py`. This keeps real HTML,
JS module execution, API responses, and browser assertions, but removes
dependence on a transient local TCP listener for browser rendering. Dedicated
HTTP/API tests still exercise the socket/transport boundary. The WSGI adapter
has separate routing/response regression tests. Army overview acceptance also retains
an independent HTTP `/api/armies` request for its expected-data comparison, checks
relationship links and keyboard focus at desktop/mobile widths, and reports page
status, JavaScript, failed-request and HTTP-error evidence on failure.

The cross-domain relation destination gate is divided by its eight **public
route catalogs** (distinct from singular source record kinds). All discovered
destinations are required to belong to a tested catalog, and each still
receives the original API and HTML response checks. This avoids one long
pytest item at the end of an xdist run. On Windows, the isolated gate passed
eight cases in **35.08 s serially** and **25.09 s with two workers**; the
complete relation module passed 11 tests in **34.15 s** with two workers.
This split participates in the normal full-suite checks.

### Controlled Chromium concurrency and browser-reuse benchmark

**Status: single-run comparison complete; repeatability and browser-reuse work pending.**
This is a Project infrastructure experiment, not a change to the current
`worksteal` default or the 1.0 release gate. Test cases currently share
browsers within some modules. The default remains two active Chromium
slot holders; three and four are experimental settings.

1. **Freeze the comparison inputs.** Pin Git HEAD and the complete working
   tree/DB/publication state, Python/pytest/xdist/Playwright versions,
   Chrome/Chromium channel and version, host CPU/RAM, pytest worker count
   (start with eight), asset policy, and background workload. Run on the
   same Windows checkout and record whether Docker Desktop is active.
   Do not edit test inputs while benchmark jobs are running.
2. **Instrument before tuning.** Report elapsed wall time, xdist startup/
   collection, per-slot lock wait and hold time, browser launch/close count
   and duration, browser-context/page creation, per-module execution and
   teardown, and lane start/finish. Collect CPU utilization, peak process-
   tree RAM, and failures (including WSGI/HTTP/JS/request diagnostics).
   Distinguish blocked fixture setup from expensive Chromium launch.
3. **Make admission and grouping configurable (separately).** Add validated
   runner/pytest settings for browser slots (2, 3, 4) and browser lane count
   (2, 3, 4). Keep the existing two-slot/two-lane behavior as the default.
   Derive balanced, deterministic xdist groups from maintained browser
   modules using measured workload rather than case count alone. Include
   the two real-Chromium tests outside the `_browser.py` modules. Preserve
   mock-only and mixed-module exclusions and the cross-process slot lock.
4. **Establish native baselines.** On the unchanged tests, record current
   `worksteal` with two slots and grouped `browserlanes` with two slots/
   two lanes. Then compare `worksteal` at 2/3/4 slots (without reuse) and
   grouped runs at 2/3/4 lanes with matching slot limits (without reuse).
   Keep all non-browser pytest workers enabled. Start with the maintained
   browser section; test each promising configuration against the full
   test stage to expose scheduler starvation and the long-tail effect.
5. **Measure browser reuse independently.** Prototype one lazily started
   Playwright/Chromium process per dedicated browser worker, spanning
   modules but never shared across worker processes. Create a fresh
   context/page per independent test and always close them; preserve
   per-test routing, event capture, viewport/theme/storage isolation,
   and the existing HTTP acceptance checks. Ensure the number of
   *live* pooled browsers, including idle ones, never exceeds the
   configured resource cap: a short-lived slot lease alone does not
   enforce this. Handle crashes, skips and worker exit without leaks.
   Compare reuse on/off at identical lane and slot counts.
6. **Repeat and validate.** Run one unscored warm-up followed by at least
   three scored runs per candidate, alternating their order. Record
   median total and browser-section time, run-to-run variation, p95
   fixture wait/test time, CPU/RAM peaks, pass/skip counts, and all
   timeouts/retries (do not silently retry). Add focused regression tests
   for slot configuration, xdist grouping, isolation, crash/teardown,
   and fallback when Chrome or Playwright is absent.
7. **Evaluate Docker as a second environment, not a shortcut.** Confirm
   `docker version`, `docker info` and `docker compose version` work with
   Linux containers on the Windows development host before use. The
   existing Dockerfile/Compose files package the *application*, not a
   Playwright test runner. If native benchmarks justify further study,
   use a separate pinned Playwright-capable test image, matching Python/
   Playwright/browser versions and the same pinned data. Keep browser
   tests and app data isolated from production containers; set explicit
   CPU/RAM limits, account for Docker Desktop/WSL2 overhead, and record
   host versus container results independently. Do not compare Chrome
   on Windows with a different bundled Chromium build as equivalent.
8. **Decision gate.** Adopt a new default only when all assertions pass
   with unchanged expected skips, no new flaky failures or resource
   leaks, and repeatable median wall-time improvement of at least 10%
   on the full test stage without material p95/peak-RAM regression.
   Otherwise keep the current defaults. Re-run the candidate with
   canonical checks, CI and release acceptance as applicable.

Initial implementation exposes `--browser-slot-count` and
`--browser-lane-count` (2, 3 or 4), plus opt-in `--browser-metrics`
on `tools/run_checks.py --stage test`. Defaults and regular test
command lines are unchanged. `--browser-lane-count` other than 2
requires `--test-dist browserlanes`. The experimental three/four-lane
assignments are provisional until profiled, and the separate real-Chromium
cases outside the browser section still acquire slots independently.

For a controlled Windows browser-section comparison (run **sequentially**):

```powershell
.\.venv\Scripts\python.exe tools/run_checks.py --stage test --test-section browser --test-workers 8 --test-dist browserlanes --browser-slot-count 2 --browser-lane-count 2 --browser-metrics
.\.venv\Scripts\python.exe tools/run_checks.py --stage test --test-section browser --test-workers 8 --test-dist browserlanes --browser-slot-count 3 --browser-lane-count 3 --browser-metrics
.\.venv\Scripts\python.exe tools/run_checks.py --stage test --test-section browser --test-workers 8 --test-dist browserlanes --browser-slot-count 4 --browser-lane-count 4 --browser-metrics
```

Each run prints its ignored `local/benchmarks/chromium-*/` path. The
per-worker `slot-<pid>.jsonl` files contain module/test label, worker,
slot index, wait/hold durations and (in newly recorded runs) monotonic
request/acquisition/release timestamps. The separate optional browser
lifecycle files time only explicitly instrumented Chrome launches and
page creations; they do **not** cover every browser process or include
CPU/RAM usage. A recorded fixture wait is not Chromium startup. See the
[timestamped metrics analysis](#chromium-concurrency-under-pytest-xdist)
and keep Windows/Docker performance sampling as separate work.

**Exploratory Windows results, 2026-11-02:** All four runs used eight xdist
workers, the same `dev/v1.0.0` source state based on `f82bf93d`,
the same local generated DBs and full asset selection, and the complete
maintained browser section (608 cases including expected skips). Each was
run sequentially, with independent per-worker slot metrics:

- 2 slots / 2 grouped lanes: **592 passed, 16 skipped** in **555.67 s**;
  lane A completed at +554.76 s, lane B at +235.47 s.
- 3 slots / 3 grouped lanes: **592 passed, 16 skipped** in **479.18 s**
  (13.8% below the two-lane time); last lane at +478.35 s.
- 4 slots / 4 grouped lanes: **592 passed, 16 skipped** in **445.63 s**
  (19.8% below the two-lane time); last lane at +444.82 s.
- 4 slots / ordinary `worksteal`: **590 passed, 16 skipped, 2 failed**
  in **360.57 s**. Both failures were the real Chromium
  Reinforcement-parentage and release-candidate tests: local static-module
  requests returned `ERR_CONNECTION_REFUSED`, leaving Unit content hidden.
  Fixture setup waits reached **305.73 s**; do not promote or report this
  configuration as a successful speedup.

**Scenario FAQ split experiment, 2026-11-02:** On the clean
`dev/v1.0.0` base `d4c39fe` plus only the benchmark/test-fixture edits,
an opt-in `--split-scenario-faq` mode partitions Scenario FAQ test
node IDs deterministically between lanes A and D in four-lane mode.
Each worker owns an independent module-scoped Chrome/WSGI fixture and
retains the same cross-process Chromium slot limit. The normal grouping,
pytest defaults, and release transport gate are unchanged. Run with:

```powershell
.\.venv\Scripts\python.exe tools/run_checks.py --stage test --test-section browser --test-workers 8 --test-dist browserlanes --browser-slot-count 4 --browser-lane-count 4 --split-scenario-faq --browser-metrics
```

The first complete Windows run passed **592, skipped 16, failed 0**
in **413.60 s**, versus the earlier unsplit four-lane **445.63 s**
(7.2% improvement across single runs). Lanes A/B/C/D finished at
+301.77/+246.20/+292.33/+412.79 s; lock waits remained
about 1 ms or less. The duplicated Scenario FAQ module fixture held
slots on two workers for approximately **287 and 272 s**. Thus, the
split shortens the critical path without reducing total browser
occupancy, and lane D remains the tail. Also, the independently
HTTP-verified Reinforcement parentage test now routes Chromium page
requests through the existing direct WSGI adapter to avoid local
static-asset socket refusal; the hosted release-candidate test still
uses real HTTP, and passed this run. The source of its earlier
`ERR_CONNECTION_REFUSED` failures remains **unconfirmed**.

A subsequent cumulative test run on the same working tree under
the **unchanged default** (`-n auto --dist worksteal`, two Chromium
slots) passed **4,797 tests, 25 skipped, 0 failed** in **564.13 s**
(async job `453e2eba4f534fd5aea5dd9f5494598e`; 2026-11-02).
It fulfills the deferred local VR-0019/0020/0021 cumulative execution
obligations; mandatory hosted CI and final release acceptance remain
independent. The slowest fixture setup took **299.97 s** (an
Immunity/Plasma Chromium case), showing significant contention remains
in the ordinary scheduling path. Ruff, canonical Pyright,
Markdownlint, documentation links and diff checks all passed.

These results remain exploratory, not adoption evidence: repeat the
benchmark, capture CPU/memory and Chrome launch counts, and verify
a final release candidate before changing the recommended default.

The grouped runs' measured Chromium slot waits were generally sub-millisecond;
the main constraint was **uneven lane workload**. The Scenario FAQ module held
one slot for about **373 / 449 / 430 s** in the 2/3/4-lane runs, respectively.
Its execution slowed as more heavy browser modules ran concurrently, which
is consistent with, but does not independently prove, resource contention.
The original 2/3/4-lane results are **single measurements**, not an
A/B/A benchmark. Keep the existing `worksteal` / two-slot default until
repeatability and release reliability are demonstrated. The Scenario FAQ
split and the first cumulative full-suite pass are now documented above.

**Cross-module Chromium reuse pilot, 2026-11-02:** A second opt-in option,
`--reuse-browser`, applies only to the three modules assigned to lane B
in four-lane `browserlanes` mode: Ammunition publication, Sidebar density,
and Weapon source cards. The same worker holds one OS Chromium slot for
the entire pooled browser lifetime, skipping the redundant per-module
slot lease. Its single Playwright process is closed after the last eligible
module (or on worker teardown), and every test still calls
`browser.new_page()` for a fresh, isolated page/context. This is not
enabled by the default pytest command.

The two comparable Windows runs selected the same three modules, eight
workers, four slots, four lanes, and the same tracked and generated data:

- Ordinary per-module Chrome lifecycle: **121 passed in 128.34 s**;
  three launches took **0.919 s total**.
- One pooled Chrome across the three modules: **121 passed in 126.42 s**;
  one launch took **0.216 s**.
- Both modes created **120 independent pages/contexts**, taking
  **13.25 s** and **13.19 s** respectively. Slot waiting was negligible.
  Thus, the 1.92-second (1.5%) total difference is a **single-run
  observation**, not an established speedup.

Reproduce the limited pilot (run sequentially, with no competing tests):

```powershell
.\.venv\Scripts\python.exe tools/run_checks.py --stage test --test-workers 8 --test-dist browserlanes --browser-slot-count 4 --browser-lane-count 4 --browser-metrics tests/test_verify_ammunition_publication_browser.py tests/test_verify_sidebar_density_browser.py tests/test_verify_weapon_source_cards_browser.py
.\.venv\Scripts\python.exe tools/run_checks.py --stage test --test-workers 8 --test-dist browserlanes --browser-slot-count 4 --browser-lane-count 4 --reuse-browser --browser-metrics tests/test_verify_ammunition_publication_browser.py tests/test_verify_sidebar_density_browser.py tests/test_verify_weapon_source_cards_browser.py
```

The opt-in `browser-<pid>.jsonl` files beside slot records capture launch,
close, and new-page durations. Reuse requires `browserlanes` and exactly
four slots/four lanes, so the pool cannot exceed the configured resource
cap. In a further **complete browser-section** four-lane run combining
`--split-scenario-faq --reuse-browser`, **592 passed, 16 skipped** in
**399.68 s** (lanes A/B/C/D finished at +296.05/+241.52/+285.30/+398.97 s).
For comparison, the earlier four-lane split without the pool finished in
**413.60 s**: a 3.4% single-run difference. The pool showed one launch,
120 independent new-page calls, one close, and released its slot before
other lanes finished. This validates coexistence but does not establish
a repeatable improvement.

More complete host CPU/RAM sampling and repeated, alternated runs are
still required before adopting the pool; measured startup cost is too
small to explain the full-suite long-tail delays.

**Cumulative local validation of the reuse pilot, 2026-11-02:** The
default test command (`python -m pytest -n auto --dist worksteal` through
`tools.run_checks`, without reuse or Scenario FAQ split enabled) passed
**4,805 tests, 25 skipped, 0 failed** in **533.47 s** (runner duration
534.09 s, exit 0). Evidence: asynchronous job
`055606fc719249308264da6fbd75565f`, on `dev/v1.0.0` at
`16560d03` with the reuse-pilot working-tree edits. This fulfills the
local cumulative-test obligation `VR-0022`; hosted CI and final
release-candidate verification remain independent. Fixture setup
durations still reached **284.93 s**, reflecting the unresolved
default-scheduler long tail. At documentation closeout the repository
HEAD had advanced to `709ccc7f`; this test result is **not** claimed
as validation of changes introduced after `16560d03`.

**Linux four-lane grouping verification, 2026-11-02:** On Ubuntu `devbox`,
`dev/v1.0.0` at `413a2185dfdd20d7caca5781380d8c1041814d57`,
pytest 9.1.1 and pytest-xdist 3.8.0, the targeted Scenario FAQ,
Sidebar density and Orders/AROs browser modules ran with eight workers,
four Chromium slots, four browser lanes, `--split-scenario-faq`,
`--browser-metrics`, required assets and reporting. The stage passed
**250 tests, 16 skipped, 0 failed in 257.41 s** (runner 257.78 s).
All four observed lanes stayed on exactly one worker: A `gw1` (112 setup
events), B `gw3` (6), C `gw2` (12) and D `gw0` (136); the assignment
guard passed. Scenario FAQ test identifiers were split across A/D.
All lanes began at +1.27 s relative to worker spawn, but final teardown
was +199.08/+14.93/+14.22/+254.08 s for A/B/C/D respectively.
The remaining long tail is workload imbalance, not xdist startup or
cross-worker lane dispersion. Timestamped metrics are stored on `devbox`
at `local/benchmarks/chromium-20261102-150545-273889/`. This targeted
run verifies scheduler correctness, **not** full-suite performance or
cross-host skip parity; repeat equal-revision full-suite two-/four-slot
runs with the same four lanes and FAQ split before changing defaults.

**Controlled Linux grouped full-suite pair, 2026-11-02:** On the
same `devbox` revision `413a2185` with eight xdist workers, four
browser lanes, Scenario FAQ A/D splitting and required/full assets,
both runs passed **4,520 tests, 330 skipped, zero failed** (two
Python multiprocessing `fork()` deprecation warnings each). Each lane
remained on exactly one worker in both runs: A `gw2` (122 setup
events), B `gw3` (121), C `gw1` (137), and D `gw0` (217).

- **Two Chromium slots:** pytest **503.49 s**, runner **504.11 s**;
  measured cumulative slot waiting **750.74 worker-s** across nine
  setup events. Lane final teardowns A/B/C/D at
  +385.43/+182.36/+501.79/+449.84 s. Metrics:
  `local/benchmarks/chromium-20261102-151402-286243/` on `devbox`.
- **Four Chromium slots:** pytest **380.97 s**, runner **381.49 s**;
  measured cumulative slot waiting **93.27 worker-s** in one non-lane
  Chromium setup. Lane final teardowns A/B/C/D at
  +248.01/+182.98/+243.47/+377.62 s. Metrics:
  `local/benchmarks/chromium-20261102-152232-319639/` on `devbox`.

Four slots shortened this paired test stage by **122.52 s (24.3%)**
and reduced summed Chromium waiting by **657.47 worker-s (87.6%)**.
Both runs passed the group-to-worker scheduling guard. With four slots,
lane D remains the long tail, while the ungrouped game-mode Chromium
test still waited 93.27 s for admission. These are sequential
**single-pair observations**, not an alternating/repeated performance
result. No CPU/RAM sampling or cross-host source/skip reconciliation
was supplied. Keep existing defaults; repeat the same pinned
configuration in alternating order, analyze the timestamped slot
metrics and capture CPU/RAM before making an adoption decision.

**Linux Chromium timeline reconstruction, same `413a2185` pair:**
The two-slot trace observed 35 admissions (three records with slot indices
above two excluded), **489.86 s** of observation, **927.81 worker-s** of
holds, **437.69 s** at full capacity, **750.75 worker-s** of waiting,
**0.22 s** with a free slot and a pending request, and a peak queue of
three requests. The four-slot trace observed 38 admissions,
**374.73 s** of observation, **1,042.82 worker-s** of holds,
**182.22 s** at full capacity, **93.27 worker-s** of waiting,
**0.09 s** with a free slot and a pending request, and a peak queue of
two requests. Full-capacity occupancy fell from **89.4%** to **48.6%**
of each trace's observation span. Scenario FAQ held **459.55/507.13
worker-s** (two/four slots); higher parallelism shortened elapsed time
but did not reduce its total hold cost. These observations support
capacity contention rather than excessive idle-slot admission latency.

**Timeline diagnostic caveat:** Both analyzer runs printed
`overlapping holders for the same slot`. The measurement code samples
`released_monotonic_seconds` *after* the OS lock is released and its
handle closed, so recorded hold boundaries can overlap subsequent
owners. In addition, the full suite's capacity self-tests use independent
temporary lock directories while sharing the process-wide metrics
output directory; their 3-/4-slot tests can generate the three slot
indices excluded by a two-slot analysis. The analyzer currently stores
neither lock-directory identity nor a separate unlock timestamp; it
cannot distinguish independent namespaces or identify genuine lock
ownership overlap from these summaries. The approximately **0.26
slot-second** difference between summed holds and uniquely occupied
slots in each trace is small but **not a lock-correctness proof**.
Before using overlap warnings as a validation gate, record/partition
lock namespaces and bound unlock-to-timestamp skew, with focused
analyzer regressions. Keep the raw metrics and do not change resource
limits based on this warning alone.

**Chromium metric namespace/unlock instrumentation follow-up, 2026-11-02:**
New runs record `lock_directory` and
`release_started_monotonic_seconds`, sampled just before attempting to
unlock, alongside the existing post-unlock `released_monotonic_seconds`.
The timeline analyzer prefers the shared xdist
`infinitydb-chromium-slots` namespace when present, excludes other
self-test namespaces before filtering slots, and reports their count.
If automatic selection is ambiguous, specify the exact
`--lock-directory`; mixed legacy and namespace-aware records fail
explicitly. Occupancy now uses the conservative pre-unlock bound while
reported held time retains the post-unlock timestamp. Overlaps limited
to the unlock interval are **indeterminate** rather than proven lock
violations; the summed unlock uncertainty is reported. Existing traces
without namespace/timing fields remain readable but cannot reliably
resolve overlap warnings, so the prior Linux pair remains historical
evidence rather than a corrected occupancy reconstruction.

Focused Windows validation passed: **24/24** capacity/timeline tests
(including Linux- and Windows-style lock-directory identities), **3/3**
browser-metrics tests, and **98 passed / 1 expected skip** in the runner
regressions. Ruff, canonical Pyright (zero errors), Markdownlint, links,
and Git whitespace checks passed. The improvement affects
instrumentation and offline analysis only; it does not change slot
admission, grouping, or Chromium lifecycle. Repeat a fresh Linux run to verify that the warning is
resolved with namespace-aware records, then continue alternating
benchmarks with CPU/RAM sampling. On Linux `devbox` at `25c0da5b`
(2026-11-02 16:03 CET), a four-slot/eight-worker targeted run of
`test_browser_test_capacity.py`, Page Footer, and Sidebar Density
passed **36/36** in **13.86 s** (runner **14.23 s**, no skips or failures).
Lane B remained on `gw1` and D on `gw0` (six setup events each); the
assignment guard passed. Metrics on `devbox`:
`local/benchmarks/chromium-20261102-160356-356643/`. This validates real
Linux test execution and lane assignment with the new instrumentation.
The subsequent offline timeline analysis selected the shared lock
namespace `/tmp/pytest-of-infinitydb/pytest-17/infinitydb-chromium-slots`
and **excluded 13 independent self-test records**. It reconstructed
**2 admissions**, **12.36 s** observation, **20.03 worker-s** held,
**20.03 unique occupied slot-seconds**, **0.00 s** measurable waiting,
**0.00 s** at full capacity, and **2/4** peak occupied slots. No
same-slot-overlap warning remained; summed unlock timestamp uncertainty
was **0.0001 s**. The selected holds were Sidebar Density (`gw1`,
12.36 worker-s) and Page Footer (`gw0`, 7.66 worker-s). The reported
peak queue of two requests is an instantaneous event count, despite
negligible integrated waiting, not evidence of sustained contention.
This confirms the namespace filtering and overlap classification on a
real Linux mixed workload. It is not a full-suite capacity benchmark;
repeat alternating runs with CPU/RAM sampling before changing defaults.

**Separate MCP Linux worker environment, 2026-11-02:** The registered
`linux-dev` worker executes from `/srv/mcp-worker/workspaces/InfinityDB`,
not the earlier interactive `devbox` checkout. At `413a2185`, its initial
four-slot/eight-worker B/D browser-lane run skipped all 12 tests because
Playwright was absent. After restoring that environment dependency, the same
12 real-Chromium tests passed in **14.06 s**, with B on `gw1` and D on `gw0`.
A larger four-lane Scenario FAQ/Sidebar/Orders run passed **250 tests,
16 expected skips in 255.05 s**; each lane used one worker (A/B/C/D:
`gw1`/`gw3`/`gw2`/`gw0`). Final teardowns were +201.12/+15.26/+14.39/
+252.44 s, confirming the D long tail. The associated timestamped trace
(`local/benchmarks/chromium-20261102-172648-362351/` on the worker)
recorded **0.00 worker-s** of slot waiting, **476.29 worker-s** held, and
only **12.66 s** with all four slots occupied. For this selected workload,
Scenario FAQ case execution and uneven distribution, not Chromium admission,
dominate elapsed time. These checks do not verify Syncthing staging access;
that remains a separate obligation. Neither checkout was synchronized.

**Controlled Windows full-suite slot pair, 2026-11-02:** At clean commit
`4bda6efb`, sequential runs used eight xdist workers, four grouped lanes,
Scenario FAQ A/D split, required assets, browser metrics, and grouped skip
reporting, changing only Chromium slots. The two-slot run **passed 4,843,
skipped 28, failed 0 in 672.40 s**, with **682.70 worker-s** of admission
waiting, **445.59 s** at full slot capacity and lane D ending +671.53 s.
The four-slot run took **509.91 s**, passed **4,842**, skipped the same **28**,
but **failed one** Scenario FAQ browser assertion; measured waiting was
**114.74 worker-s**, full-capacity occupancy **315.10 s**, and lane D ended
+509.15 s. Both lane-assignment guards passed. Observed duration fell
**24.2%** and summed waiting **83.2%**, but the faster run is **not an
acceptable configuration result** because of the failure. The failed case,
`test_visibility_zone_terms_normal_browser[390]`, received HTTP 200 for
`/glossary#term-visibility-zone` but timed out at 15 s waiting for the term
to become visible. An isolated rerun on the same revision, eight workers and
four slots **passed in 9.59 s**; the cause under full-suite load remains
unconfirmed. A second focused four-lane run combining all three Glossary
widths, Sidebar Density and Orders/AROs passed **21/21 in 24.22 s**;
its 390px Glossary case took **12.02 s** in the call phase. Both targeted
runs therefore pass, but neither reproduces full-suite load or establishes
the reason for the original timeout. Metrics:
`local/benchmarks/chromium-20261102-172549-31072/` (two slots) and
`local/benchmarks/chromium-20261102-173728-15540/` (four slots), on Windows. No CPU/RAM sampling or aligned cross-host source-parity
check was performed. Keep scheduling defaults unchanged, investigate the
load-sensitive failure, and require repeated fully passing comparisons before
promotion.

**Docker host readiness:** the fixed, read-only
`python -m tools.probe_docker_test_host` probe found the Docker CLI and
Compose **5.6.1** on the Windows MCP host, but both the daemon version
and engine-info queries failed (exit 1, unclassified by the probe).
The Linux container engine is **not yet verified as usable** from the
MCP process. The existing Dockerfile and Compose configuration remain
production-specific and unchanged. No Docker tests have been performed.

Store raw measurements in ignored `local/benchmarks/`; publish only the
selected configuration, methodology and concise outcome here. Do not
turn the active validation queue into a completed benchmark log.

## Theme runtime regression coverage

The web test suite executes the checked-in theme startup and preference modules in a minimal Node.js
runtime harness. This pins pre-paint System/Light/Dark resolution, session-versus-cookie precedence,
explicit switching, normalization, and remembered-setting behavior without introducing a browser or
JavaScript build dependency. The development dependency set already provides Node.js through
`pyright[nodejs]`; the test also accepts a normal `node` executable when one is already available.
Representative server-rendered pages separately verify that the shared pre-paint bootstrap and
semantic theme stylesheet are present in the correct order.

## Scenario detail soft-navigation regression

The scenario API tests also execute `scenario.js` in a small Node.js lifecycle harness.
It verifies that leaving a scenario detail page aborts its pending map/catalog requests,
removes the distance-unit listener, and rejects late map responses. A second Node.js
harness checks that rapidly changing Army Points returns to the loading panel,
ignores superseded results (including stale errors), and displays only the latest
configuration even when an aborted request still resolves. Responsive grid
contracts are also checked in the web suite. Scenario browser visual review was
user-confirmed on 2026-10-08; later bounded Chromium interaction acceptance is
documented under [four-core-scenario acceptance](#10-four-core-scenario-browser-acceptance).
Neither run replaces [final candidate acceptance](TODO.md#final-10-acceptance).

## Silhouette manual browser acceptance

The scale-preserving Silhouette renderer has automated structural coverage, but the release gate
retains a small real-browser review because clipping, touch behavior, and theme rendering are visual
interaction concerns. Use the current generated database and check these representative Unit pages:

- `/units/cadin-firststrike-donn` — S2, shown without a duplicate reference;
- `/units/ajax-the-great-myrmidon-officer` — S5 plus the faded S2 reference;
- `/units/gator-squadron` — S7 plus the faded S2 reference;
- `/units/maghariba-guard` — S8 plus the faded S2 reference.

Also check `/glossary#attribute-s`. In both Light and Dark themes, confirm the Glossary S1–S8 set
keeps one common relative scale, wraps into equal-width rows without horizontal clipping, and does
not widen the normal Glossary content column. On the Unit examples, confirm the `S` value opens the
preview with mouse hover, keyboard focus, and touch/click; the popup must remain on-screen at narrow
widths, preserve the selected-template/S2 relative scale, and close normally when focus/pointer
moves away or the touch/click interaction is dismissed. Record completion in `docs/TODO.md`; do not
replace this acceptance check with screenshot-only or DOM-only evidence.

## Full Army source-archive provenance tests

`tests/test_audit_source_variant_inputs.py`,
`tests/test_other_source_variant_provenance.py` and
`tests/test_martial_arts_variant_provenance.py` pin direct Skill/Equipment
occurrences, their source-extra signatures and exact Army source IDs. They
require the ignored development archive `data/generated/infinity.raw.db`
alongside the tracked published application/rules databases. The shared
pytest prerequisite skips only these raw-dependent modules when that
archive is absent in a clean CI checkout; an existing but malformed
archive fails its schema check rather than being silently accepted.
A local full-source audit must use a paired, current Army database export
from the pinned Army snapshot (or validate an existing pair with
`infinity-db database-health data/generated/infinity.db --require-raw`),
then run these modules explicitly.
A clean CI pass does **not** claim to have verified the full source-only
occurrence counts.

Inspect a specific source family without dumping the entire inventory:

```powershell
python -m tools.audit_source_variant_inputs --catalog skills `
    --source-id 74 --source-id 263 --source-id 271
python -m tools.audit_source_variant_inputs --catalog equipment --source-id 169
```

The first command selects Super-Jump, Jump and Climb; the second selects
TinBot: Firewall. Output preserves the original full-catalog summary
and every selected raw extra ID/type/value; unknown source IDs fail
explicitly. To inspect only the remaining unresolved source IDs without
truncating the console response, use:

```powershell
python -m tools.audit_source_variant_inputs --catalog skills --unresolved-only --brief
```

`--unresolved-only` filters the displayed items without changing the
`fullCatalogSummary` counts. `--brief` retains source IDs, names,
occurrence totals and the number of signatures while omitting verbose
per-signature data; rerun with `--source-id N` to inspect exact raw
values. Selection/combination guard tests work in CI without the
raw database, while pinned occurrence-count regressions require the
local archive.

The reviewed Surprise Attack source gate covers Skill `191`, all 767 direct
rows and the exact single-extra signatures 6/7 (`TEXT: -3/-6`, 762/5 rows).
It checks both the tracked rules artifact and a fresh export, preserving the
opponent-target Face to Face ARO scope separately from Mimetism and the
distance-only display query. The current source inventory has 34 unresolved
Skill IDs and 10 Equipment IDs; these are per-source review flags, not Unit counts.

**Jump/Climb distance review:** Army source IDs 263/271 have 26/6
exact single-extra `DISTANCE: 7.5` (extra ID 372) occurrences. The
fresh and tracked rules exports expose their family distance
semantics keyed by numeric Army ID; no other family receives their
meaning. `tests/test_audit_source_variant_inputs.py` checks source
signatures against the local ignored raw Army database.
`tests/test_restriction_storage_candidate.py` runs the
CI-compatible migration delta tests, including malicious extra
links, wrong IDs, unrelated records and `sqlite_stat1` changes.
The guarded local refresh is
`python -m tools.build_deployed_object_publication --refresh-movement-distance-v9`;
it requires the matching ignored raw source and an unchanged
tracked v9 rules database, retains ignored recovery copies, and
updates `rules.db` with its paired deployed-object publication.
Do not rerun against an already-promoted pair.

**TinBot Firewall Equipment MOD review:** Source Equipment 169
has 147 direct occurrences: 92 exact `TEXT: -3` (extra 6)
and 55 exact `TEXT: -6` (extra 7). The mapped
`enemy-comms-attack-mod` targets only a Comms Attack against
the TinBot's owner (N5.3 p. 127); it is not a generic opponent
MOD. `tests/test_audit_source_variant_inputs.py` checks the
pinned raw source and both rules-export pathways, while
`tests/test_curated.py` and
`tests/test_restriction_storage_candidate.py` fail closed
on altered source IDs, values, applicability, source identity
and unrelated database changes. The exact source-only audit
requires ignored `infinity.raw.db`, unlike the hermetic
mutation and migration tests. The one-time guarded local refresh
is `python -m tools.build_deployed_object_publication
--refresh-tinbot-firewall-v9`; it requires a matching, unchanged
tracked v9 rules artifact, updates the synchronized
deployed-object publication and retains recovery copies under
ignored `local/`. Do not rerun after promotion.

**TinBot Discover and ECM Guided review:** Source Equipment
`244` has two `TEXT: ReRoll` (extra `277`) occurrences;
source `247` has two `TEXT: -6` (extra `7`) and two
`TEXT: -9` (extra `259`) occurrences. The reviewed effects
respectively mean a one-die Discover reroll (N5.3 p. 68)
and a negative enemy Guided Attack MOD against the TinBot
owner (N5.3 p. 127 and the maintained ECM rule). The
`+3 WIP` Discover example is **not** inferred from `ReRoll`.
The typed maps are available via
`RulesDatabase.equipment_reviewed_extra_semantics()`.
`tests/test_audit_source_variant_inputs.py` verifies exact
pinned raw signatures against the tracked rules DB **and a fresh
export**; the raw archive is required for these tests.
The hermetic curated and v9 release migration tests reject
source drift, incorrect scopes, altered named variants and
unrelated database changes. The one-time guarded local refresh
is `python -m tools.build_deployed_object_publication
--refresh-tinbot-other-v9`; it retains ignored recovery copies
and synchronizes the rules database with the deployed-object
publication. Do not rerun after promotion.

**Hacking Device unmodified program-grant review:** Pinned source
Equipment `100`/`101` has 653/126 direct relationships.
The five exact single-extra `hacking-program-grant` mappings
cover 150 Hacking Device and 46 Hacking Device Plus occurrences.
The audited `UPGRADE:` source text is matched by exact
ID/type/value, including nonbreaking spaces, rather than
parsed from display labels. N5.3 pp. 54/58/123 supplies the
program-upgrade and baseline-device distinction; individual
program effects stay owned by their canonical `hacking-program:*`
records. `tests/test_audit_source_variant_inputs.py` compares
the local raw source against tracked and freshly exported
rules metadata and, at that review milestone, asserted that
multi-extra combinations remained unreviewed. The later
explicit exact-combination review supersedes that
classification for precisely three ordered signatures. The hermetic curated validator rejects
wrong device, type, source value and program target; the
guarded v9 source preflight rejects drift before promotion.
The one-time local refresh was
`python -m tools.build_deployed_object_publication
--refresh-hacking-program-grants-v9`; the previous matched
rules/publication pair is preserved in ignored `local/`.
The normalized program-grant effect has a `program` identity
without a synthetic `applies_to` field. Neither Equipment
source ID is fully reconciled: modified programs, Firewall
variants and exact combined upgrades remain unresolved.
Do not rerun the one-time migration on an already-promoted pair.

**Hacking Device B/PS/Special Die upgrade review:** Source
Equipment `100`/`101` now has nine additional exact
`reviewed-extra` mappings (81 single-extra occurrences:
66 `+1B`, eight Carbonite `PS=6`, seven `+1SD`).
At that stage, the pinned-source audit still distinguished
these from unreviewed `SR-1/SR-2`, Firewall strings and
compound signatures; the named-program SR forms were
reviewed separately below. The mappings
retain program identity and separate the `modifier`, `value`
and `count` fields instead of inferring a full modified
Hacking Program profile. The hermetic migration regressions
reject altered scopes, program identities, reordered/removed
grants, schema changes, altered source counts and unauthorized
combinations; the raw-source audit compares tracked
`rules.db` with a fresh curated export when the local
raw archive is available. The one-time guarded refresh is
`python -m tools.build_deployed_object_publication
--refresh-hacking-program-mods-v9`. It synchronizes the
matched publication and retains ignored rollback artifacts.
Do not rerun after promotion.

**Hacking Device named-program SR review:** Source IDs
`100`/`101` have five newly reviewed exact single
extras totaling 55 occurrences. The curated
`program-saving-roll-mod` effect records a `-1` or
`-2` target Saving Roll modifier only for its named
Hacking Program. The source gate requires the pinned
TEXT extra ID, raw spelling, count and previous
reviewed grant/B/PS/SD ordering, and excludes
unqualified `SR-1`, Firewall and multi-extra combinations
at that milestone. The later independent reviews
addressed the exact Firewall and three compound signatures.
The hermetic v9 migration delta tests reject modified
program effects, absent older entries, unrelated table
changes and schema drift; the full raw-source inventory
compares current and freshly exported rules metadata
when the pinned local raw archive is available.
The one-time guarded promotion was
`python -m tools.build_deployed_object_publication
--refresh-hacking-saving-rolls-v9`. It retains the
earlier matched release pair under ignored `local/`.
Do not rerun on the already promoted pair.

**Hacking Device Firewall review:** Source Equipment
`100` has 16 direct single-extra occurrences:
`326`/`Firewall -6` (2),
`334`/`UPGRADE: Firewall (-3)` (13) and
`376`/`UPGRADE: Firewall (-6)` (1).
Each reviewed effect contains a canonical Firewall
reference, the negative attacker WIP MOD and
a **fixed +3 defender Saving Roll MOD** against
Comms Attacks, per N5.3 pp. 55-56.
The pinned-source audit compares the raw Army
snapshot, tracked `rules.db`, and a freshly
exported rules database. Curated mutation tests
reject wrong extra IDs/types, scope, modifier
values, or TinBot substitution. The v9 hermetic
migration suite rejects changes to previous
reviewed grants/B/PS/SD/SR entries, schema,
unrelated rows, and source signatures.
The one-time guarded local promotion is
`python -m tools.build_deployed_object_publication
--refresh-hacking-firewall-v9`; it updates the
matched deployed-object publication and retains
recovery copies under ignored `local/`.
Do not rerun after the pair is promoted.
At this Firewall milestone, unqualified SR and
multiple-extra combinations were unreviewed; the
later exact-combination review below supersedes that
for precisely three source signatures.

**Exact Hacking Device compound source reviews (2026-11-01):**
The curated `occurrenceCombinations` field lists only three
complete, ordered two-extra Army signatures. Device `100`
has Cybermask + Trinity grants (one direct occurrence) and
Total Control `PS=3` + Trinity `PS=5` (two). Device Plus
`101` has Trinity `PS=5` + Zero Pain (two).
`tests/test_curated.py` rejects changed extra IDs,
spellings, order, program identity, effects and additional
unlisted pairs. `tests/test_audit_source_variant_inputs.py`
checks the exact ordered signatures, including comparing
the tracked rules artifact and a fresh curated export
against pinned raw Army occurrences. It also proves that
individual reviewed extras and different permutations
cannot certify an unlisted combination. The dedicated
`RulesDatabase.equipment_reviewed_combination_semantics()`
reader returns the exact reviewed pairs, without adding
their effects to ordinary single-extra semantics.
The bounded `tests/test_restriction_storage_candidate.py`
migration suite rejects unreviewed or missing source
signatures, changed prior reviewed rules, schema changes
and unrelated database edits. The one-time guarded command
is `python -m tools.build_deployed_object_publication
--refresh-hacking-combinations-v9`; the matching previous
rules/publication pair is preserved under ignored `local/`.
Do not rerun on the promoted pair. The source-level
baseline is now **34 unresolved Skill / 10 Equipment IDs**;
Device Plus extra `344` (`UPGRADE: SR-1`, two occurrences)
remains open because it lacks a program target.

**Read-only exact source-owner provenance (2026-11-01):**
`tools.audit_source_variant_inputs` accepts
`--catalog equipment --source-id 101 --owner-extra-id 344`
to inspect only direct raw Army relationship owners. The
`occurrenceOwners` result includes original owner type,
Unit, army/source file, profile or loadout option, raw
occurrence ID, source position, and exact extra ID/type/text.
The pinned Charontid regression in
`tests/test_audit_source_variant_inputs.py` verifies
exactly two `option` owners: Combined Army source
`601`, Unit `498`, option IDs `4`/`9`,
occurrences `51441`/`51461`. Neither has
a source-level program target or additional raw payload.
Invalid catalog/source/extra arguments are rejected
without opening a database. This test requires the
ignored pinned raw Army database. These diagnostic
details are not a published Unit-use index. The
hypothesis that unqualified `SR-1` applies to every
Hacking Program on the Device Plus is plausible but
**not verified**; the two occurrences remain unresolved.

**Bangbomb source-verified Dodge +4 (2026-11-01):**
The exact `equipment:bangbomb` variant is sourced to
N5.3 p. 120, source Equipment ID `246`, extra `310`,
`TEXT: +4`, with **125** standalone occurrences.
The `dodge-roll-mod` modifier is only applicable
against attacks from enemy Troopers in LoF/ZoC
and excludes Template Weapons. The curated validator
rejects wrong IDs, types, values, scopes, numeric
modifiers, and source family changes.
`tests/test_audit_source_variant_inputs.py` checks
the 125 reviewed signatures against tracked and
freshly exported rules databases when the ignored
pinned raw Army archive exists. The one-time guarded
command `python -m tools.build_deployed_object_publication
--refresh-bangbomb-v9` verifies exact source input,
compares the full before/after database to reject
unrelated changes and generic append bypasses, and
updates the matched rules/publication artifacts
with ignored recovery copies in `local/`.
Do not rerun after promotion. The source audit
baseline becomes **34 unresolved Skill / 9 Equipment**
IDs; this does not publish a Unit-use index.

**Source-specific ECM Guided/Hacker (2026-11-01):**
ECM source `239` uses exact `TEXT` extras `6/-3`
(2), `7/-6` (176), `51/-8` (1), `251/-8`
(2); ECM source `241` uses `6/-3` (158) and
`7/-6` (3). Both belong to application Equipment
`239`, so distinct `inheritance: source`
definitions carry exact numeric source links rather
than borrowing a shared generic parameter. The
curated validator rejects altered source IDs, named
variant labels, effect targets, numeric values and
extra identities. The pinned Army-source audit
compares the tracked `rules.db` and a freshly
exported rules database, including raw owner
checks for `-8`: Next Wave Juggernauts (extra
`51`) and ZETA UNIT in O-12 and Starmada
(extra `251`). The dedicated additive v9
migration guard permits only the two exact
source-specific definitions/links/citations/relations;
pre-existing database rows, schema, source snapshot
and publication objects are preserved. Negative
tests reject unrelated additions, changed legacy
rows, source-link drift and missing or malformed
extras. The one-time guarded command
`python -m tools.build_deployed_object_publication
--refresh-ecm-source-variants-v9` synchronizes
the release pair and retains ignored rollback
files; do not rerun after promotion. The source
audit baseline is now **34 Skill / 7 Equipment**
unresolved IDs. These are not cross-Army Unit-use
indices.

**MediKit source-verified ranged Burst (2026-11-01):**
Equipment source ID `106` has 573 direct Army
occurrences; 38 have one extra `8` (`TEXT:+1B`).
N5.3 p. 124 limits its typed
`equipment-burst-mod` effect to the remote
MediKit BS Attack, not its contact Short Skill
or the recipient's PH recovery Rolls.
`tests/test_curated.py` rejects changed source
IDs, raw text, extra type, effect kind, modifier,
or broad/incorrect scope.
`tests/test_audit_source_variant_inputs.py`
verifies all source signatures against both the
tracked and freshly exported rules databases.
Hermetic tests in
`tests/test_restriction_storage_candidate.py`
reject source drift, unrelated database changes
and a generic refresh bypass. The one-time
guarded command
`python -m tools.build_deployed_object_publication
--refresh-medikit-v9` synchronizes the matched
rules/publication pair while preserving ignored
rollback copies under `local/`. Do not rerun
the command after promotion. The unresolved
baseline becomes **34 Skill / 6 Equipment**
source IDs; this is not a Unit-use index.

**EVO Trinity grant plus Saving Roll modifier (2026-11-01):**
Equipment source `182` has 40 direct
Army occurrences; two use exact extra `352`,
`TEXT: UPGRADE: Trinity (SR-2)`. The
`hacking-program-upgrade` mapping preserves
both **Trinity access** and its `-2` target
Saving Roll modifier, alongside EVO's four
unchanged baseline programs (N5.3 p. 58).
Curated mutation tests reject removal of
`grantsProgram: true`, incorrect program,
SR modifier, scope, source ID, or spelling.
The hermetic guarded migration tests reject
generic append bypass, changed earlier
family semantics, missing or modified source
rows, schema changes and unrelated metadata.
The pinned raw-source audit compares tracked
and freshly exported rules databases.
The one-time guarded command
`python -m tools.build_deployed_object_publication
--refresh-evo-trinity-v9` synchronizes
the previous matched release pair and retains
ignored rollback files in `local/`. Do not
rerun it after promotion. The source baseline
is **34 unresolved Skill / 5 Equipment IDs**.

**Hacking Device/Plus Trinity access correction (2026-11-01):**
Eight previously reviewed, exact Upgrade signatures
on Equipment sources `100` and `101` (19 direct
Army occurrences) now retain their B/SD/SR/PS=5
semantics **and** grant Trinity. Standalone extras
`290/378/339/352` on source `100`, extras
`378/339` on `101`, and the two approved
`343` compound signatures are the complete
scope. `tests/test_curated.py` checks that all
eight require `grantsProgram` as an actual
boolean `true`, including rejection of integer
`1`; hermetic
`tests/test_restriction_storage_candidate.py`
tests reject altered prior modifiers, missing
grants, changed compound components, unrelated
rows and generic refresh bypass. The pinned
Army audit in `tests/test_audit_source_variant_inputs.py`
compares tracked and freshly exported Rules DBs
against exact source IDs, counts and full
compound order; the unqualified Charontid extra
remains open. The matched v9 update used
`python -m tools.build_deployed_object_publication
--refresh-hacking-trinity-access-v9`; do not
rerun after promotion. Prior artifacts are
retained under ignored `local/`, with
`--check` verifying publication parity.
Source audit counts remain **34 unresolved
Skill / 5 Equipment**.

**Albedo source occurrence reconciliation (2026-11-01):**
`tests/test_curated.py` rejects changed source
IDs, extra types, spellings, effect targets or
modifier signs for Albedo Equipment `183`.
`tests/test_audit_source_variant_inputs.py`
asserts 142 pinned direct rows: `TEXT:-3`
(extra 6, 55 occurrences) and `TEXT:-6`
(extra 7, 87 occurrences). It compares the
tracked v9 rules database with a fresh export
and rejects unreviewed combinations. The
existing append-only v9 metadata refresh
`--refresh-variant-semantics-v9 equipment:albedo`
was run once, with a retained matched pair
under ignored `local/`. The paired publication
passes `--check`. Current unresolved source
counts are **34 Skill / 4 Equipment**; the
cross-Army usage index remains unimplemented.

**Neurocinetics reactive Burst source variant (2026-11-01):**
`tests/test_audit_source_variant_inputs.py` now verifies the four
option-specific source-109 `8/TEXT:+1B` signatures and their two
Unit identities across four Army contexts, in both the tracked and
fresh rules export. `tests/test_curated.py` rejects unsupported
IDs, kind, source type, value and non-Reactive-Turn scopes.
`tools.stage_neurocinetics_burst --output-dir local/<unique-stage>`
creates an ignored staged v9 `rules.db` and matched deployed-object
publication without mutating tracked artifacts;
`--promote-staged` rechecks input hashes/HEAD and preserves rollback
copies. The published pair retains all 17 reviewed objects, and
the source inventory moves from 21 to **20 unresolved Skill IDs**.
This is metadata publication and does not establish a Unit-usage
index, attack resolution, full browser signoff or release acceptance.

**Minelayer (2) source-quantity promotion (2026-11-01):**
The source audit verifies Skill source `56` has 546 direct
occurrences, including exactly 15 `267/TEXT:2` extras (14
option-level and one profile-level), with no other reviewed
signatures. The `reviewed-extra` effect is strictly an item
count scoped to deployment; it does not modify Disposable uses.
The focused `test_minelayer_two_deployment_count_matches_pinned_source`
pins all 15 Army contexts and the promoted rules database.
The script `tools.stage_minelayer_count --output-dir local/<unique-name>`
stages the matched rules/publication pair under ignored `local/`;
`--promote-staged` revalidates hashes and retains rollback copies.
All 17 published deployed objects remain unchanged, and the
variant audit drops to **19 unresolved Skill IDs**. The older
generic `--refresh-variant-semantics-v9` path requires schema
`user_version=9` and rejects this newer checkout; use the
dedicated guarded migration for this change. Focused regression,
database, publication and rules-build validation were run
immediately. Additional mutation cases and cumulative test-suite
execution are deferred in `docs/validation-queue.md`.

**Chain of Command Non Specialist publication (2026-11-01):**
The source audit identifies exactly 11 source-26 `375/TEXT:Non Specialist`
occurrences, all option-level, across Joan of Arc/Joan of Arc v2
and William Wallace; 151 Chain of Command occurrences in total.
The `reviewed-extra` effect excludes only Chain of
Command-derived Specialist Troop qualification. The targeted
source-inventory regression pins all 11 occurrences and the typed
rules database; `test_specialist_candidates_ignore_non_specialist_chain_but_keep_other_skills`
protects the existing independent-qualifier behavior.
`tools.stage_chain_of_command_non_specialist --output-dir local/<unique-name>`
stages guarded matching rules/publication artifacts;
`--promote-staged` verifies input hashes and retains rollback
copies. No deployed-object record was changed (17 unchanged).
Focused source, rules-map, Specialist filter, publication and
rules-build tests passed; source audit count is **18 unresolved
Skill IDs**. Mutation/edge-case tests and cumulative suite
execution are deferred in `docs/validation-queue.md`.

**Forward Observer (+1SD) source promotion (2026-11-01):**
The pinned raw Army audit confirms two profile-level
`308/TEXT:+1SD` occurrences of source `59` on TARKSHYA
Operator in ALEPH and Operations Subsection, among 609 direct
Forward Observer occurrences. The curated exact effect is one
`special-die` scoped to `forward-observer-wip-attack-roll`,
not additional Burst or Disposable uses; newly added N5.3
citations on pp. 75 and 92 establish its rule scope.
The source-variant regression and rules-database mapping
test pass. `tools.stage_forward_observer_special_die`
stages a fingerprint-verified matched rules/publication
pair beneath ignored `local/`; `--promote-staged` verifies
and retains rollback backups. The reviewed 17 deployed
objects are identical before/after promotion and the
audit now lists **17 unresolved Skill IDs**.
Additional rejection/derived-index tests and cumulative
full-suite verification were subsequently completed on 2026-11-01;
the fulfilled VD/VR entries have been retired from the active queue.

**Phased regression design pass (2026-11-01):**
`tests/test_curated.py` now contains exact-source mutation matrices
for Minelayer (2), Chain of Command (Non Specialist), and Forward
Observer (+1SD); `tests/test_audit_source_variant_inputs.py` checks
unparameterized Minelayer rows (531), Forward Observer tracked/fresh
rules parity (607 ordinary occurrences), and source-specific
non-inference. `tests/test_scenario_api.py` checks all 11 pinned
Chain of Command option annotations against the Specialist candidate
filter in all four reviewed contexts, preserving other Skill qualifiers.

Initial design-sanity runs yielded **30 passed, 2 strict xfailed**,
exposing the boolean-as-integer validation defects (`excluded: 1`
and `count: true`). Both guards were subsequently fixed, the strict
xfail markers removed, and the affected negative-case matrices passed
(**8/8** and **9/9**). All five deferred design requirements were
completed, and the cumulative full-suite run on 2026-11-01 passed
(**4,698 passed, 25 skipped**). These completed queue entries were
retired; final hosted CI/release acceptance remains separate.

## Non-Skill Army source classification and Unit presentation

`tests/test_non_skill_army_presentation.py` is a maintained, hermetic
source-to-API regression against the tracked published `infinity.db`
and `rules.db`. It checks **all 72 distinct Unit/source pairs** in the
pinned snapshot for six Army Skill-source identities deliberately presented
outside the player-facing Skill category: Gizmokit, MediKit and Bangbomb
are Equipment; Regular is Training; Infinity Team Ops is a source marker;
and BTS=3 is an Attribute override. Each occurrence must reach its
correct canonical `shared_items` or contextual `specific_items` bucket;
none may be falsely presented as a Skill.

Seven representative Unit details additionally check the normal HTTP
bootstrap, their general-profile API data and Equipment route
availability. Unit details are **client-rendered**: the initial HTML only
contains `unit-content` and the `unit.js` bootstrap; a rendered
`general-profile` appears only after JavaScript executes. The separate
ignored `local/audits/non-skill-army-browser/results.json` recorded
**21/21 Chromium checks** across 1440/390/320 px for those seven
Units. A second report, `local/audits/non-skill-army-browser/current.json`,
records **21/21 passing cases on 2026-10-20** using the maintained
verifier; the user confirmed that run. Both reports are bounded
checkout-specific browser evidence, not CI browser tests or proof of
whole-catalog source-to-browser completeness.

The maintained optional verifier `tools.verify_non_skill_army_browser`
repeats the seven real-browser cases at those three widths. It checks
the client-rendered general profile, published API buckets, the correct
Equipment/Training/Attribute-override table rows, valid Equipment
destinations, the absence of mistaken Skill links, JavaScript errors,
and document-level overflow. The published Unit API inventory test remains
the separate 72-pair source-to-API gate. With the development server
running for the **same checkout and databases**, run from the repository
root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m tools.verify_non_skill_army_browser --base-url http://127.0.0.1:8000 --output local/audits/non-skill-army-browser/current.json
```

The optional verifier requires Playwright with Chromium installed and
is not part of routine source checks. The 2026-10-20 pass verifies its
development checkout but does **not** carry a release-candidate source
hash or certify a future build. Rerun it against the actual candidate
before final 1.0 browser acceptance.

## Unresolved N5.3 source-conflict publication

`tests/test_source_conflict_publication.py` protects the **published
player-facing disclosure boundary** for four reviewed but still
externally unresolved N5.3 disputes: Armed Turret Silhouette S1/S2,
Dodge (ARM+3) PDF versus Wiki wording, the Special Dice/Fireteam
Spanish reminder, and the separate printed Morat Fireteam Level 3
example. The regression checks normal API and page routes for
Armed Turret, Dodge, Special Dice and Fireteams, retaining the
reviewed source notes, structured text tokens and both official
N5.3 language-edition citations. It also checks the maintained
browser scripts still consume source notes through the normal
player-facing renderer.

This is **tracked-publication/API and served-script validation**,
not fresh Chromium DOM acceptance or an official correction.
Kobra Pistol's distinct CC-mode Anti-materiel dispute and Flash
Pulse's Spanish Wiki conflict have existing mode-scoped/weapon
API regressions under `tests/test_weaponry_catalog_api.py`.
These tests must not replace the source reconciliation tasks:
the open REA dependencies remain listed in `docs/TODO.md`.

## Published cross-domain rule relation destinations

`tests/test_public_relation_destinations.py` traverses the maintained
current rules database across Ammunition, Equipment, Hacking Programs,
General Rules, Skills, States, Traits and Weapons. It applies the same
relation-link enrichment as the web backend, then checks every distinct
**catalog-backed** destination against both its normal public detail API
and the matching served HTML detail-page contract. Skills and Hacking
Programs have dedicated detail scripts; other catalogs use the normal
`data-catalog` template marker. The test records owning rule IDs on
failures rather than assuming a structurally valid relation reaches a
usable page. This verifies route/template reachability, not client-side
rendering or source completeness.

Additional checks in the same test module verify that published
**embedded Glossary** entries target their deterministic client-created
article IDs and that Glossary links to **Weapon-family rule fragments**
resolve to actual rule cards in their host Weapon detail API. The first
check is of published embedded entries; the current published
`display_relations` graph contains no embedded Glossary link targets,
so it would be incorrect to claim such graph edges were exercised.
That composed `display_relations` graph also currently emits no
explicit `href` references; Weapon-family/Glossary fragment targets
are checked separately below. The renderer and page-script contracts
are checked, but actual client-rendered DOM navigation is not.

A further check enumerates every published Weapon slug from
`/api/weapons` and inspects each complete detail API payload.
Every same-page `#rule-…` reference from relations or
maintained-text tokens must resolve to a rule card included in that
Weapon's `rules` array. Duplicate public slugs and duplicate hosted
rule-card anchors fail. Pages with local fragments must also serve
their normal Weapon detail route. The known
`#rule-weapon-mines` reference and its AP Mine page are pinned
against a vacuous pass. The shared renderer derives those article IDs
from the same rule identities.

Intentionally unlinked source variants remain unlinked. This
does not adjudicate rules, establish every *expected* relation,
inspect live DOM anchors, or replace final release-candidate
Chromium fragment navigation at 1.0 acceptance.

### Weapon fragment Chromium verifier

With the development app running, execute this optional full-width and
mobile-width browser check from the repository root:

```powershell
.\.venv\Scripts\python.exe -m tools.verify_rule_fragment_browser --base-url http://127.0.0.1:8000 --output local/audits/weapon-rule-fragments-browser.json
```

The verifier discovers candidate Weapon pages with local rule references
from the *served* Weapon catalog/details APIs and discovers Weapon rule
fragment links from the served Glossary API. At 1440, 390 and 320 px, it
follows catalog links through the soft-navigation path, checks every
API-referenced local rule target as a rendered card even when its
reference is not displayed as a link, follows every actually rendered
same-page rule fragment link, opens a direct deep link in a **fresh
browser page** (including pages without a clickable self-link), and
follows Glossary-to-Weapon hash links. This isolates cold-load behavior
from the preceding in-page hash/navigation state. Card uniqueness
and visibility are checked atomically within a single browser
evaluation to tolerate DOM replacement during optional Unit updates,
without allowing missing or duplicate cards. It reports page
JavaScript/API/network errors and horizontal overflow; loading
failures include the last visible page state. The AP Mine/Mines source target must be hosted,
but is not required to appear as a self-link on the Weapon page.
Its JSON report belongs under ignored `local/audits`; the command
exits nonzero on failures. The current development-browser run on
2026-10-20 passed **57/57** across 1440, 390 and 320 px. This is
bounded development-server evidence, not final-release verification.

This is client-side link and anchor acceptance for the current served
app, not proof that every intended source relation exists or that
the final pinned release inputs are complete. The verifier must be
re-run against the eventual 1.0 release candidate.

## Scenario-specific FAQ publication scope

A maintained Scenario API regression checks the Annihilation-only FAQ against Core and ITS missions. The base Scenario response stays separate from dated FAQ rulings, and the served client supplies explicit scenario and season context. This does not replace rules-source adjudication or live browser acceptance.

## Source Unit notes and composite-option publication

`tests/test_unit_source_options_notes.py` compares **all** source-attributed
Unit notes and composite options in the tracked published `infinity.db`
against normal Unit detail API responses. The pinned release baseline has
**30 source Unit notes on 28 logical Units** and **18 composite Unit options
on seven logical Units**. Every source note must preserve its source
Unit ID, text, representative identity and attributed Army metadata.
Every source composite option must appear under its logical Unit,
preserving source option identity, name, Points/SWC, miniature count,
ordered Order contributions, and *exact* Army-scoped included-loadout
payload IDs and quantities. The check fails on missing or extra
inclusions rather than treating any displayed composite bundle as
sufficient.

This is **tracked-database-to-API parity**, not direct reinspection of
the ignored raw Army archive and not a live Chromium acceptance run.
The original responsive/browser investigation remains dated evidence;
the final 1.0 gate still requires validation against the final source
pair, served revision and normal player-visible pages.

## Maintained snapshot-note validation

The routine pytest suite recursively validates every maintained JSON snapshot note under
`data/curated/snapshot-notes/`, independently of downloader/comparison workflows. The directory
contract permits only `README.md` plus `.json` note files, so an accidentally checked-in stray file
cannot bypass validation by using an unrecognized extension.

## Maintained pytest sections

`config/testing/test-sections.json` defines coarse, maintained slices of the test suite. The current
sections are:

- `model` — data/model/repository semantics;
- `web` — API/browser/web presentation;
- `build` — acquisition/build/export/tooling;
- `ops` — deployment/packaging/operations;
- `assets` — graphical publication processing/validation.

Run one or combine several:

```powershell
python tools\run_checks.py --stage test --test-section model
python tools\run_checks.py --stage test --test-section web --test-section ops
```

The section file is maintained source, not a generated test-count ledger. Tests may move between
sections as ownership changes; documentation should not hard-code current counts.

## Pytest workers

Test stages default to pytest-xdist automatic worker selection:

```powershell
python tools\run_checks.py --stage test --test-workers auto
```

Use a fixed worker count when diagnosing scheduling/resource behavior, or `0` for serial execution:

```powershell
python tools\run_checks.py --stage test --test-workers 4
python tools\run_checks.py --stage test --test-workers 0
```

Worker choice is an execution policy, not a correctness difference. Tests must remain valid under
parallel execution unless they are explicitly serialized by their own fixture/contract.

Hosted Windows CI uses two fixed pytest workers because automatic xdist scheduling was unstable
for that runner class and serial execution exceeded the job budget as coverage grew. This does not
change the normal local default. See `docs/ci.md` for the hosted execution/time-budget policy.

Pytest uses its platform-default, per-session temporary directory rather than a fixed
repository-local `.pytest-tmp` directory. This avoids reuse or cleanup collisions
when local test runs overlap; use `--basetemp=...` explicitly only when needed.

## Graphical asset modes

Asset-dependent coverage is controlled explicitly:

```text
--assets off
--assets auto
--assets required
```

- `off` runs hermetic tests and skips `full_assets` integration coverage.
- `auto` uses the complete tracked/local publication when it validates; a detected partial/corrupt
  publication is an error rather than a silent downgrade.
- `required` fails unless the complete publication validates and includes `full_assets` tests.

Examples:

```powershell
# Hermetic source-focused tests
python tools\run_checks.py --stage test --assets off

# Normal local behavior
python tools\run_checks.py --stage test --assets auto

# Release/full-publication validation
python tools\run_checks.py --stage test --assets required
```

The publication contract comes from `data/manifests/symbol-publication.json`, not from counting SVG
files. Validation checks paths/hashes, rejects unexpected publication members, and verifies the
browser-referenced subset against the same manifest.

## Build source

The Army build stage accepts an explicit source directory/ZIP:

```powershell
python tools\run_checks.py --stage build --build-source tests\fixtures\deployment-smoke
```

Required CI uses a controlled fixture rather than network acquisition or a developer's `data/raw/`
contents. Normal checks must not fetch upstream data implicitly.

## SQLite finalization in tests

Release/default Army and rules exports perform canonical SQLite physical finalization so generated
files are byte-stable. Some semantic tests may explicitly use exporter APIs with physical
finalization disabled to avoid repeatedly paying for `VACUUM`/header canonicalization when the test
only asserts logical database contents.

That optimization skips only physical finalization. It must not bypass source validation, schema
creation, integrity checks, semantic materialization, or atomic destination replacement.
Army export tests also simulate interruption between raw-sibling replacement and the application
commit point: the previous application remains valid, the mismatched pair is rejected, and rerunning
export restores one matching generation. Determinism/release tests continue to exercise the
canonical finalized path.

## Reports

Use `--report` to retain the complete check transcript:

```powershell
# reports/CHECKS YYYYMMDD-HHMMSS.txt
python tools\run_checks.py --profile code --report

# explicit destination
python tools\run_checks.py --all --report reports\release-checks.txt
```

Generated reports are local evidence and are normally ignored by Git.

## Exit status

The runner returns success only when every requested stage succeeds. Configuration/argument errors
also fail the command. With the default continue-on-failure behavior, later requested stages still
run and the final status remains failed if any earlier stage failed.

## Deployment smoke

Local/source validation and production packaging are separate contracts. The container smoke path
builds an image from the tracked runtime artifacts and validates production startup through
`scripts/verify-container-image.sh`. Hosted execution is described in `docs/ci.md`.

For a server-side isolated test deployment use the workflow in `docs/deployment.md`; it is not a
substitute for source tests.

## Benchmark tooling

Benchmarks are diagnostic evidence, not stable documentation constants. Record the exact commit,
source/database snapshot, platform, Python/SQLite versions, worker configuration, and command with
each result instead of copying timing numbers into this file.

The installed application also exposes a lightweight database health/validation timing command:

```powershell
infinity-db database-health data/generated/infinity.db
infinity-db database-health data/generated/infinity.db --require-raw
infinity-db database-health data/generated/infinity.db --require-raw --json
```

It always runs the application-database integrity validation and reports actual/expected SQLite
schema and application compatibility revisions. `--require-raw` additionally requires the expected
`infinity.raw.db` sibling and verifies that both files belong to one export generation. Validation
time and file sizes are included as lightweight operational evidence; use the dedicated benchmark
tools below for representative query-performance comparisons.

Available benchmark and capacity tools include:

```powershell
python tools\benchmark_runtime.py --help
python tools\compare_runtime_benchmarks.py --help
python tools\benchmark_test_workers.py --help
python tools\capacity_test.py --help
python tools\deployment_resources.py --help
python tools\deployment_alerts.py --help
```

Use runtime benchmarks for repository/query performance and the worker benchmark for deciding whether
a different local pytest worker setting is warranted. `capacity_test.py` is deliberately HTTP-level:
it discovers representative public Unit/Skill/Equipment/Weapon identities from the target deployment,
warms the same routes, then runs separate fixed-concurrency steady and burst phases across Unit list,
search, Unit/catalog detail, and matching JSON API requests. It reports aggregate and per-case p50/p95/
p99 successful-request latency, request/error rate, status classes, response sizes, and target
version/snapshot identity. The synthetic search value is redacted from retained report paths. It does
not use `/health` as the workload.

Capacity reports are diagnostic evidence, not stable performance promises. Retain the exact target
release/snapshot, client location, command, and accompanying host/container resource observations with
any baseline. For the isolated Caddy test stack, use `http://localhost:8080`; `127.0.0.1:8080` reaches
the listener but does not match the configured Caddy host. `deployment_resources.py` is Linux-host-only
and can wrap the capacity command while sampling bounded host/Docker resource counters over the same
interval. Its container summaries retain only the capacity-relevant runtime configuration (explicit
Docker CPU/memory limits and detected Gunicorn worker/thread counts), while its JSON intentionally
excludes hostnames, IPs, request URLs, arbitrary container environment/command values, and arbitrary
Docker event payloads. Record resource boundaries outside Docker separately.

The recorded capacity baselines, matched worker-count experiment, Compose overrides, and production
scale-review trigger are maintained in
[deployment guidance](deployment.md#repeatable-http-capacity-scenario). Keep measured results and
operational policy there rather than maintaining a second copy in this test reference.

`deployment_alerts.py` evaluates a fresh resource report together with bounded aggregate metrics and
health samples, producing monitoring-friendly OK/warning/critical/unknown exit codes without retaining
endpoint URLs or user/request identity data. Generated benchmark/capacity/resource/alert reports belong
in ignored report/audit storage unless a specific result is needed as release evidence.

Live-metrics tests pin the generation timing contract before retained history exists: one shared
generation-start timestamp is created with the preloaded request registry, only completed instrumented
requests advance the latest-request timestamp, and reading `/metrics`/`/health` does not change either
value. `report_metrics.py` must also remain tolerant of older deployments without these gauges.

Metrics-history engine tests keep the persistence/privacy contract explicit: deterministic synthetic
scrapes verify first-generation-from-zero accumulation, same-generation deltas, restart/version
boundaries, fail-closed handling of unexplained counter decreases, weekly aggregation keyed by
week/version/snapshot, route-label and histogram-bound allowlisting, age-based pruning, and oldest-completed-week pruning
under the database-size ceiling. The collector state remains one rolling snapshot and must not retain
real visitor data or unbounded request labels. Historical-report tests additionally pin exact/latest
selection, broad week/version/snapshot aggregation, request/status/error summaries, normalized-route
activity, cumulative histogram percentile bounds, machine-readable output, and latest-period
comparison behavior. Deployment tests additionally prove the application container remains read-only, collector state lives
only in its dedicated history volume, and pre-update/post-health transition scrapes do not make
historical storage a prerequisite for app startup. They pin the lifecycle order: build/verify both
images, stop only the continuous collector, one-shot closing scrape, availability-critical app/Caddy
replacement + health, one-shot opening scrape, then continuous collector startup. Collector
scrape/start failures remain observable warnings rather than application rollback triggers. The closing
transition path alone may synthesize a generation boundary for legacy metrics that predate the live
timestamp gauges; continuous collection remains strict. The isolated `infinitydb-test` project gets a
distinct history volume, preserves it on normal stop, and `--purge` removes only test-project volumes.
Persistent-store tests pin the forward schema-migration contract before any history-format increment:
registered one-version upgrades commit schema changes and the `format_version` marker atomically,
failed migrations retain the previous committed format, non-empty unversioned stores are refused, and
an older collector rejects a newer store without modifying retained history. The production rollback
procedure separately preserves the named history volume across a release with no collector.

## 1.0 reference-catalog parity and browser verification

`tests/test_application_rule_references.py` checks curated definitions,
generated rules storage, public list/detail API responses, and normally
served player templates. The covered catalog contracts differ:

- **Ammunition:** the 11-record reviewed baseline matches canonical IDs,
  names/summaries, typed facts, source citations and visible rules cards.
- **Labels:** the 24-record reviewed baseline is derived from curated
  `labels` arrays, not `records`. It preserves descriptions, maintained-text
  links and deduplicated `used_by` entries; the UI shows a Definition section
  rather than an Ammunition card or per-Label citations.
- **General Rules:** the 21-record reviewed baseline uses `rule` records
  filtered by reviewed General Rules categories, not all rules. It validates
  unique public slugs (including qualified Peripheral IDs), generated identities,
  source facts/citations and their exact rule-card IDs.

These are **source-to-storage/API/template parity** checks, not independent
rules correctness or rendered-browser acceptance. Rerun optional Chromium
navigation checks against the **current checkout's development server**, not a
stale Docker/Caddy listener. Each verifier checks its whole catalog at
1440, 390 and 320 px for correct visible details, load completion, console
errors and document-level horizontal overflow.

Start the local server in one PowerShell window:

```powershell
.\.venv\Scripts\python.exe -m infinity_db serve --host 127.0.0.1 --port 8000
```

Run the needed verifier from a second repository-root PowerShell window:

```powershell
.\.venv\Scripts\python.exe -m tools.verify_ammunition_browser --base-url http://127.0.0.1:8000 --output local/audits/ammunition-browser.json
.\.venv\Scripts\python.exe -m tools.verify_labels_browser --base-url http://127.0.0.1:8000 --output local/audits/labels-browser.json
.\.venv\Scripts\python.exe -m tools.verify_general_rules_browser --base-url http://127.0.0.1:8000 --output local/audits/general-rules-browser.json
```

**Historical acceptance, 2026-10-19:** Ammunition 33/33, Labels 72/72,
and General Rules 63/63 browser checks passed against that day's development
server. These results are evidence for those specific runs, **not** continuing
release acceptance. The complete 1.0 cross-source and browser-completeness gates
remain open; retain future browser reports in ignored `local/audits/`.

## 1.0 State, Hacking Program and Trait publication verification

The focused hermetic suites validate exact source identities, generated
storage, public list/detail API contracts and normally served templates:

- **States:** `tests/test_state_catalog.py` covers all 24 separate
  `state`-kind records, canonical names/facts, citations, published
  `rules.db` entries and catalog/detail delivery.
- **Hacking Programs:** `tests/test_hacking_program_publication.py`
  covers 12 published entries. Army owns profile values, targets,
  declaration categories, baseline Hacking Devices, Upgrade extras,
  modifiers, PS and Burst; reviewed curated records own rule semantics,
  citations and interactions. The tests reconcile both sources with
  unique public slugs, generated rule records, API values and templates.
  Neither source alone defines the complete player page.
- **Traits:** `tests/test_trait_wiki_references.py` covers all 33 canonical
  reviewed Traits, including typed facts, citations, use counts, current
  `rules.db`, published catalog/detail identities and exact reviewed
  Wiki destinations. Raw Army properties are a separate source-derived
  bucket: extra catalog slugs must be backed by that bucket and must
  never replace the canonical Trait entries.

Optional Chromium verifiers follow actual catalog-to-detail navigation
at 1440, 390 and 320 px. They check matching headings, canonical rule
cards, visible citations, JavaScript errors, incomplete loading and
document-level horizontal overflow. Hacking Programs also check profile
fields and baseline Devices; Traits check their official Wiki links and
exclude raw-property substitutes. The separate Trait Wiki-anchor test
against saved official HTML (33/33) is **not** a substitute for catalog
navigation and does not establish live Wiki availability.

With the current checkout's development server running on
`http://127.0.0.1:8000` (startup command above), run the needed
verifier from the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m tools.verify_states_browser --base-url http://127.0.0.1:8000 --output local/audits/states-browser.json
.\.venv\Scripts\python.exe -m tools.verify_hacking_programs_browser --base-url http://127.0.0.1:8000 --output local/audits/hacking-programs-browser.json
.\.venv\Scripts\python.exe -m tools.verify_traits_catalog_browser --base-url http://127.0.0.1:8000 --output local/audits/traits-catalog-browser.json
```

**Historical browser acceptance, 2026-10-19:** States 72/72,
Hacking Programs 36/36 and canonical Trait catalog entries 99/99
passed on the then-current development server. These are bounded
results for those runs, not independent rules-semantic review or
continuing 1.0 completeness acceptance. Store new evidence under
ignored `local/audits/`; rerun against the actual target checkout.

## 1.0 Martial Arts, Booty and MetaChemistry structured-chart parity

`tests/test_structured_skill_charts_publication.py` reconciles every generated
Army chart row, repository getter and Skill API `structured_reference` value.
It checks Martial Arts Levels 1–5 and exact D20 coverage of Booty and
MetaChemistry without gaps or overlaps. Typed conditional branches/components
and reviewed public links have negative cases for missing or ambiguous identities.
The tests belong to the `model` section.

The optional Chromium verifier enters all three pages through the Skills catalog
at 1440/390/320 px, compares every rendered chart cell with the served API and
local Army database, follows reviewed destinations and rejects JavaScript errors,
incomplete loading and horizontal overflow. With the matching development server running:

```powershell
.\.venv\Scripts\python.exe -m tools.verify_structured_skill_charts_browser --base-url http://127.0.0.1:8000 --output local/audits/structured-skill-charts-browser.json
```

**Historical acceptance:** successive 9/9 runs on 2026-10-19/20 covered the
presentation corrections, typed branches/components and final family/alias links.
Rerun the current verifier against the final candidate; earlier renderer passes
do not accept later code. The [data model](data-model.md#structured-skill-reference-charts)
owns current publication behavior, and the
[source-history review](n5-source-history.md#reviewed-10-structured-skill-chart-provenance)
owns PDF pages, exact Wiki revisions/hashes and FAQ comparison.

## 1.0 MetaChemistry combined outcomes — typed publication

The hermetic chart suite checks all five compound outcomes (16–20), preserving
the source `result` and exact two-component values/parameters. It rejects unknown
combinations and verifies six Skill-link occurrences to five canonical families,
including parameter-preserving Immunity links. MOV and Attribute modifiers stay
typed text. The same three-page Chromium command above checks components, links
and unchanged source values; the 2026-10-20 9/9 result is dated development evidence.

## 1.0 Booty Weapon outcomes — exact public-reference audit

The chart suite checks all ten Weapon labels. Nine resolve by exact unique
catalog name; HMG resolves through the separately reviewed Heavy Machine Gun
alias below. Source strings and TAG/other-Troop-Type branches remain intact.
The original exact-name-only 9/9 browser run preceded the alias/family revision;
use the current verifier for the complete published links.

### Booty alias and variant family references

The current API/browser supports all **16 Booty link occurrences**: nine
exact-name Weapons, HMG, and six parameterized Skill/Equipment outcomes.
HMG resolves only to the normal Heavy Machine Gun; Multispectral Visor L1,
Mimetism (-6), BS Attack (Shock)/(+1B), and TAG-only Immunity (AP)/(ARM)
retain their printed parameters while linking to canonical families.
Hermetic tests require unique reviewed destinations and preserve `outcome_variant`
or HMG's `reference_name`. A later 2026-10-20 **9/9** Chromium run covered all
16 occurrences and destinations; this revision is no longer browser-pending.
Final release verification remains separate.

## 1.0 independent N5.3 Wiki chart-value reconciliation

The chart regression independently pins all **16 Booty rows, 12 MetaChemistry
rows and 5 Martial Arts levels** against the reviewed N5.3 Wiki charts, retaining
Army source spelling such as `+1SD` versus `+1 SD`. It also requires a reviewed
canonical Skill and nonempty citations on each served page. This is distinct
from generated-storage/API parity; neither test reopens the external Wiki.
The completed PDF and history comparison is retained in
[source history](n5-source-history.md#reviewed-10-structured-skill-chart-provenance).

## 1.0 structured chart ownership and deployment FAQ provenance

The maintained regression pins Booty p. 86, Martial Arts p. 100 and
MetaChemistry p. 101 to the English N5.3 PDF source identity. It selects the
separate `faq-ruling:deployment-phase-reposition-after-measurement` only for
the reviewed N5.3/effective-date context, preserves v0.0 origin and v0.1 selected
citations, and rejects preceding contexts. The current test checks citation
identity/page, not the ignored PDF bytes.

The later direct PDF inspection and archived Wiki/FAQ reconciliation are
completed within the bounded chart scope in
[source history](n5-source-history.md#reviewed-10-structured-skill-chart-provenance).
The earlier failed attempt to reopen an external PDF is superseded by that
inspection; it is not a remaining chart-source blocker. These checks do not
certify the complete rules corpus, select random outcomes or persist game state.

## 1.0 source evidence baseline

### Frozen explanation-inventory reconciliation (V1-A08)

The original October 9 [367-record explanation inventory](rules-explanation-audit-1.0-inventory.md)
remains historical evidence: 304 selected clause comparisons (D) and 63
screening-only rows (S), **neither of which is full-record approval**. To
reconcile its exact identities against the *current* N5 Core/Hacking curated
collections without overwriting the original audit, run:

```powershell
.venv\Scripts\python.exe -m tools.report_reference_baseline --reconcile-explanation-inventory --json-output local/audits/v1-current-explanation-inventory.json --markdown-output local/audits/v1-current-explanation-inventory.md
```

The report pins the frozen appendix's SHA-256, validates current curated
documents, and lists all retained, newly added and retired identities.
At the October 31 current checkout baseline: **448 total; 350 retained,
98 added, 17 retired declaration categories**. The new IDs comprise 20
declaration categories, 53 Weapons, 17 Rules, five Game terms, two
Skills and one Equipment record. **46** historical S rows are still present.
Its 740 source-locator groups are **review queue entries**, not 740
unreviewed mechanics or independently confirmed defects. Identical
source/page references may cover distinct procedures; source locations
need their own clause-level dispositions. Metadata page/type peers are
candidate discoveries, not approved identity renames.

A fresh **2026-11-02** run reports **450 current records** (350 retained,
100 added, 17 retired declaration identities) and **743** source
locators; the earlier 448/740 baseline remains dated evidence.
Three post-inventory Equipment identities are explicitly distinguished:
`equipment:ecm-guided` and `equipment:ecm-hacker` have
`inheritance: source` and require owner-context presentation review, whereas
`equipment:firewall` has a normal public route. The reconciliation
reports the ECM variants as awaiting owner-context presentation review
rather than misreporting missing pages. The pinned English N5.3 PDF
checks exact selected ECM pp. 122/75 and Firewall p. 55 clauses.
Firewall's normal catalog-to-detail navigation, conditions, citation
and horizontal fit pass Chromium at 1440/390/320 px; no program or
attack calculation was introduced. These are **selected source and
browser checks**, not whole-record acceptance or an expansion of the
historical D/S tiers. The bounded 2026-11-02 batch passed **48 focused
tests** (including three real Chromium widths) using two test workers,
plus Ruff, Pyright, documentation and diff checks. The ignored
`local/audits/v1-explanation-current-20261102.{json,md}`
contains the current 450/743 reconciliation. The cumulative
suite subsequently **passed** on `8481d52b`: **4,706 passed,
25 skipped, 0 failed** in **614.25 s** with eight `worksteal`
workers (async job `dea98a36d6994302a5ec2f06123b7b32`,
report `local/validation-vr0007-full-20261102.txt`). VR-0007
was retired; whole-corpus signoff remains open.

**ECM source-only summary presentation (2026-11-02):**
The parent Equipment detail originally rendered source-variant labels
but excluded summary-only variant records from the "Variant rules"
cards. The new Chromium regression first failed at 1440/390/320 px,
then passed at all three widths after enabling source-summary cards
only for Equipment. Both `equipment:ecm-guided` and
`equipment:ecm-hacker` now show their distinct Guided Attack versus
Hacking Program scopes, N5.3 p. 122 citations and maintained ECM
links; the existing Skill/Weapon variant selection is unchanged.
This adds no curated inference and does not constitute whole-record
acceptance. The first cumulative run after this change found one
stale static JavaScript assertion in
`test_catalog_detail_frontend_renders_typed_source_variant_labels`
(**4,708 passed, 25 skipped, 1 failed**); the assertion was
updated to require the Equipment-only variant option, and the
five focused test cases passed. The corrected cumulative run on
`dev/v1.0.0` at `8d24a47` plus the test correction passed
**4,709 tests, 25 skipped, 0 failed** in **594.65 s** with eight
`worksteal` workers (async job
`7c58317028da401fa04054fba22c02c6`, report
`local/validation-vr0008-full-rerun-20261102.txt`).
VR-0008 was retired. Hosted CI and release-candidate acceptance
remain independent.

**Modifiers Explained (MODs), selected source/browser review (2026-11-02):**
`test_modifiers_explained_normal_reference_navigation` in
`tests/test_verify_scenario_faq_browser.py` checks the tracked
release-pair Rules catalog and inbound Trench Hammer link in Chromium
at 1440/390/320 px, including keyboard activation, maintained rule
text (bracketed, Automatic/non-Automatic, ReRoll, Burst/Special Dice,
and PARA separation), N5.3 pp. 68/75 citations, outbound destinations,
horizontal fit and JS errors. Existing API and pinned English
N5.3 p. 75 tests remain unchanged. The current-inventory report
registers this as **selected-route evidence only**; full clause,
Weapon and whole-record acceptance remain open. Six focused tests
passed including the inventory crosswalk; the cumulative regression
completed in the VR-0009–VR-0013 batch described below.

**MULTI Rifle and MULTI Heavy Machine Gun selected modes (2026-11-02):**
`test_multi_weapon_modes_stay_separate_in_normal_browser` in
`tests/test_verify_weapon_source_cards_browser.py` checks normal
catalog-to-detail navigation at 1440/390/320 px, all three source
profiles per Weapon, mode-local Ammunition, Burst, PS, Saving
Rolls and Anti-materiel/Suppressive Fire Traits. It verifies the
reviewed N5.3 pp. 183/179 citations, a keyboard-operated link to
AP Ammunition, JS errors and horizontal fit. Existing API tests
preserve source-mode facts independently. The six Chromium cases and two API cases passed initially (8/8).
The inventory initially failed because selected browser test names
were looked up only in the scenario/FAQ browser module. The auditor
now checks that module and the existing Weapon browser module;
a negative regression confirms missing test names still fail closed.
The expanded focused run **passed 13/13**. The current
reconciliation records only selected browser evidence
for `weapon:multi-rifle` and `weapon:multi-heavy-machine-gun`;
neither the frozen inventory nor whole-Weapon acceptance changes.
Cumulative regression completed in the VR-0009–VR-0013 batch below.

**MULTI Marksman Rifle/Pistol mode extension (2026-11-02):**
The same browser regression now also verifies N5.3 p. 180 MULTI
Marksman Rifle and p. 182 MULTI Pistol at 1440/390/320 px. Army's
first-mode label `Anti-Material Mode` stays unchanged despite
the source-reviewed Anti-materiel spelling. Mode-specific
Ammunition/Burst/PS/Saving and Traits remain independent; the
Pistol AP/Shock alternatives do not acquire Anti-materiel or
Suppressive Fire. All routes, citations, keyboard AP links,
JavaScript and horizontal-fit checks passed. Initial focused
regression: **14 passed** across four MULTI Weapons and two
existing source/API cases. Including inventory reconciliation
and its missing-test fail-closed guard, the final focused set
passed **16/16**. Ruff, Pyright, docs and diff checks passed.
The two new inventory identities receive selected browser
evidence only, without whole-record approval. Broader regression
completed in the VR-0009–VR-0013 batch below.

**Boarding Pistol / Missile Launcher selected mode separation
(2026-11-02):** `test_blast_and_hit_weapon_modes_keep_effects_separate_in_browser`
adds 1440/390/320 px Chromium checks for normal catalog navigation,
mode-specific Ammunition/Burst/Saving Rolls, template and
Intuitive Attack exclusion from Hit Mode, the Boarding Pistol
ranged-versus-template range-table distinction, reviewed N5.3
p. 182/187 citations, keyboard ammunition links, JS errors
and horizontal fit. Missile Launcher Blast preserves three ARM
saves with Circular Impact Template, while Hit preserves three
ARM/2 saves with AP+EXP and no Template; both keep Anti-materiel.
Nine focused browser/API/source-mode tests passed before inventory
registration. The expanded set with inventory reconciliation and its
fail-closed guard passed **11/11**; Ruff, Pyright, Markdownlint,
documentation links and diff checks passed. The current 450-record
inventory records these two Weapons as **selected browser evidence only**;
it does not certify automatic attack resolution or the complete record.
Cumulative regression completed in the VR-0009–VR-0013 batch below.

**K1 Combi Rifle / K1 Sniper Rifle selected browser evidence
(2026-11-02):** `test_k1_weapon_profiles_keep_normal_ammunition_and_arm_zero_in_browser`
verifies normal catalog-to-detail Chromium navigation at 1440/390/320 px,
single-mode source profiles, N Ammunition, PS 7, ARM=0 with one
Saving Roll, and the Combi B3/Suppressive Fire versus Sniper
B2/no Suppressive Fire distinction. Both retain Anti-materiel;
the reviewed N5.3 chart citations are pp. 183/185. The
browser test checks the source-backed distinction from AP's
ARM/2, keyboard navigation to Normal Ammunition, horizontal
fit and JavaScript errors. Six browser cases and two existing
API/source checks passed (8/8); the expanded set including
inventory reconciliation and missing-test guard passed **10/10**.
Ruff, Pyright, documentation and diff checks passed. This is
selected-route evidence, not a derived K1 ammunition mechanic, Immunity
adjudication or whole-record approval. The five-item cumulative
batch VR-0009–VR-0013 completed successfully.

**Cumulative test execution, VR-0009 through VR-0013 (2026-11-02):**
The final change state on `dev/v1.0.0`, based on
`80d1df0dc21418d6ff90c2bc89ebe63636095315`, passed the full
8-worker `worksteal` test suite: **4,737 passed, 25 skipped,
0 failed** in **522.00 s** (overall test stage 522.64 s).
Async job `a220d046688a464db4ebe2f41638be98` exited 0;
ignored report `local/validation-vr0009-vr0013-full-20261102.txt`.
The run covers the selected MODs, MULTI Rifle/HMG,
MULTI Marksman/Pistol, Boarding Pistol/Missile Launcher, and
K1 Combi/Sniper work, satisfying all five deferred obligations.
The queue entries were retired; the historical 367-record review,
current 450-record reconciliation, and selected browser checks do
**not** imply whole-record signoff. Hosted CI and release-candidate
acceptance remain separate.

**Post-inventory Skills, selected source/browser review (2026-11-02):**
`test_added_source_skills_normal_browser` checks the tracked
release-pair Skills catalog and normal detail route for
`skill:activate-disco-ball` (N5.3 p. 71) and
`skill:request-specball` (N5.3 p. 98). Across 1440/390/320 px
it verifies reviewed conditional text, restrictions, citations,
related links, inbound keyboard navigation from Disco Baller
and Infinity Spec-Ops, no JS errors, and horizontal fit.
The Disco Ball activation test checks allied Deactivator/LoF/ZoC,
WIP +3, Conclusion/States timing and enemy restriction.
The SpecBall test checks Round 2/3, one drop/PH 15, once-per-game,
selection/collection timing, printing discrepancy and ITS
TEAM-OPS boundary. Existing API tests cover both, with older
REA-040 browser evidence retained as historic validation.
Eight focused browser/API cases passed before inventory registration;
the expanded set with reconciliation and its missing-test guard
passed **10/10**. Ruff, Pyright, documentation links, Markdownlint
and diff checks passed. Both records are registered as
**selected-route evidence only**. Whole-record and broader
declaration eligibility signoff remain open.
Cumulative regression completed in the VR-0014–VR-0018 batch below.

For the reviewed **declaration-category metadata migration** (V1-A08), add
`--reconcile-declarations` to join retired categories to their actual Skill
owners from historical Git commit `c5400ab1`. This explicitly requires
the historical Git object; a shallow clone without that commit fails closed
rather than inventing a replacement. With the pinned N5.3 source PDF
available, also pass
`--verify-declaration-pdf data/pdf/rules/n5-rules-v5-3-en.pdf`.
The maintained source review lives in
`config/validation/declaration-inventory-migration-v1.json` and checks all
**17 retired** category identities against their historical owners and
current destinations, plus **20 new** headings/classifications against the
source-exact SHA-256 PDF. It distinguishes page-anchor corrections, three
kind corrections (Decoy, Morpho Scan's former Basic Short Skill and ARO
categories), and a shared Climb/Jump group split. No old
`declaration-category:*` ID becomes a route alias. Conditional skill
permissions, individual variants and full normal-browser explanation
acceptance remain separate work. Generate ignored review evidence with:

```powershell
.venv\Scripts\python.exe -m tools.report_reference_baseline --reconcile-explanation-inventory --reconcile-declarations --verify-declaration-pdf data/pdf/rules/n5-rules-v5-3-en.pdf --json-output local/audits/v1-declaration-migration-reviewed.json --markdown-output local/audits/v1-declaration-migration-reviewed.md
```

For the **three numerical Army replacement Skills**, a separate
source-scoped audit verifies the pinned September 29 Army archive
(SHA-256 pinned in the audit), source dictionary Skill IDs 279 / 278 /
274, all 17 faction-file option occurrences and the original BS/CC
values in their containing Unit Profile groups. It also checks the
curated `sourceVariant` attribute/replacement, parent BS/CC action
rules and printed N5.3 pp. 39 / 51 / 75 citations. No replacement
is written into base Unit statistics or inferred from example statlines.
Without the private Army ZIP this optional audit cannot claim source
closure. Produce an ignored report with:

```powershell
.venv\Scripts\python.exe -m tools.report_reference_baseline --reconcile-explanation-inventory --verify-numeric-army-archive "data/raw/JSON 20260929-114335.zip" --json-output local/audits/v1-numeric-attribute-replacements.json --markdown-output local/audits/v1-numeric-attribute-replacements.md
```

The historical source identities occur twice for Polaris Bearpode
Beta (base BS 5 → BS=11), nine times across Strelok, Konduktor and
Stempler Zond options (base BS 10–11 → BS=12), and six times for Swiss
Guard variants (base CC 15 → CC=21); repetitions across faction files
are **not distinct units**. The nine normal-browser cases test the
owning `/skills/bs-attack` and `/skills/cc-attack` pages and
the displayed source replacement labels at 1440/390/320 px. These
are not independently routed `/skills/bs-11` or `/skills/bs-12`
pages, nor full conditional-effect or profile-variant approval.

For the selected **conditional declaration and reactive eligibility**
evidence matrix, the maintained
`config/validation/conditional-declaration-evidence-v1.json` identifies
ten bounded source/record/test anchors. The reference baseline audit
checks each actual curated fact clause, versioned source citation and
existing test name against a closed manifest; with the source PDF
available, it additionally verifies the exact pinned PDF fingerprint
and the selected printed clause text. Reproduce its ignored JSON/Markdown
evidence with:

```powershell
.venv\Scripts\python.exe -m tools.report_reference_baseline --reconcile-explanation-inventory --audit-conditional-declarations --verify-conditional-pdf data/pdf/rules/n5-rules-v5-3-en.pdf --json-output local/audits/v1-conditional-declaration-evidence.json --markdown-output local/audits/v1-conditional-declaration-evidence.md
```

The ten entries cover Order declaration/Resolution timing, Look Out!,
Discover, Place Deployable, Reload, Alert!, Guard versus Aerial,
Hacking Area, Cyberplug Controller and Stealth mixed activations.
The normal `/rules/order-expenditure-sequence` and
`/skills/look-out` pages passed six Chromium cases at
1440/390/320 px. The additional
`test_selected_conditional_skills_normal_browser` regression
checks `/skills/discover`, `/skills/place-deployable`,
`/skills/reload`, and `/skills/alert` at those widths (12 cases).
It verifies selected source-conditional requirements, restrictions,
timing and exceptions, citations, normal catalog navigation, keyboard
links, JavaScript errors and horizontal fit. The three existing pinned
English N5.3 source tests passed alongside these checks (**15/15**).
With inventory reconciliation and the missing-test fail-closed guard,
the expanded focused run passed **17/17**. Ruff, Pyright,
documentation and diff checks passed. The source crosswalk audit
with the exact PDF fingerprint passed.
The first two browser slices covered six of ten crosswalk cases.
The follow-on `test_remaining_conditional_crosswalk_cases_normal_browser`
regression checks Guard/Aerial (N5.3 pp. 86/95), Hacking Area
(pp. 55/57), Peripheral (Cyberplug) (pp. 107/108), and Stealth
(p. 112) at 1440/390/320 px. It checks the distinct ARO window
and conditional exceptions, actual Rules/Skills catalog navigation,
pinned source citations, working keyboard links, JavaScript errors
and horizontal fit. The four associated pinned-PDF source tests
and twelve Chromium cases passed (**16/16**); including inventory
reconciliation and the fail-closed missing-test guard, **18/18**
passed. The closed-source crosswalk audit passed against the pinned
N5.3 PDF; Ruff, Pyright, documentation links, Markdownlint and
diff checks passed. Cumulative execution completed in the
VR-0014–VR-0018 batch below.
All **ten selected crosswalk cases** now have repeatable
normal-browser evidence. This is neither all possible ARO triggers
nor a complete matrix of Skill-specific permissions.

**Beyond the original ten-case crosswalk — Stealth counters
(2026-11-02):** The separately source-reviewed `skill:combat-instinct`
and `skill:sixth-sense` records differ in reactive eligibility:
Combat Instinct removes the Stealth limitation for otherwise eligible
ZoC reactions but does not create LoF or a response to outside-LoF
Attacks; Sixth Sense permits an outside-LoF response only to Attacks
directed at its user, not arbitrary movement. The
`test_stealth_counter_reaction_permissions_normal_browser`
regression checks the actual tracked release-pair Skills catalog
and both detail routes at 1440/390/320 px, the distinct clauses,
N5.3 pp. 20/88/111/112 citations, keyboard navigation to
related Skills, JS errors and horizontal fit. Six browser cases
plus the existing curated source-contract and pinned-English-PDF
tests passed (8/8) before inventory reconciliation.
The expanded focused run, including the inventory crosswalk
and missing-test guard, passed **10/10**. Ruff, Pyright,
Markdownlint, documentation links and diff checks passed.
These two new selected-browser pointers do not extend the closed
ten-entry conditional-declaration manifest or grant full-record
approval. Cumulative regression completed in the VR-0014–VR-0018
batch below. Every record
and source section retains pending whole-record acceptance, including
where reviewed curation or selected browser evidence exists.

**Reactive Burst permissions, Neurocinetics versus Total Reaction
(2026-11-02):** The tracked release-pair Chromium regression
`test_reactive_burst_skill_permissions_normal_browser` checks the
N5.3 pp. 104/116 source-clause distinctions at 1440/390/320 px.
Neurocinetics reduces Active Turn BS Weapon Burst to 1 and applies
full Reactive Turn Burst against a single target; Total Reaction
permits full Burst for a BS Attack ARO against an activated Trooper,
without transferring Neurocinetics' Active Turn restriction. The
test verifies Skills catalog discovery, source citations, keyboard
navigation from the Skills catalog or Armed Turret, JavaScript
errors and horizontal fit. The raw September Army archive and
fresh-versus-published rules database audits confirm the separate
Neurocinetics `+1B` modifier for four exact option occurrences,
not all users or Total Reaction. A tentative TinBot (Neurocinetics)
inbound link was not visible, so that unsupported inbound
assumption was excluded rather than claiming a passing link.
Six browser, two curated/PDF and two Army provenance cases
passed (10/10) before inventory registration. The expanded
focused set, including inventory reconciliation and the
missing-test fail-closed guard, passed **12/12**. Ruff,
Pyright, Markdownlint, documentation links and diff passed.
Selected-route evidence and source-variant review are not
general reaction eligibility, whole-Unit or whole-record signoff.
Cumulative suite validation completed at the five-item
VR-0014–VR-0018 gate.

**Cumulative test execution, VR-0014 through VR-0018
(2026-11-02):** On `dev/v1.0.0`, based on
`c7d7b4fa2f1d33515c19f12183c84013b85ed51b`, the eight-worker
`worksteal` full project suite passed: **4,779 passed,
25 skipped, 0 failed**, **615.25 seconds** (runner stage 615.97 s).
Managed job `bf6f5db144404b28b65699bc19a299bd` exited 0;
ignored report `local/validation-vr0014-vr0018-full-20261102.txt`.
This cumulative run covers added Skills, all ten selected
conditional-declaration crosswalk browser cases, Combat Instinct
and Sixth Sense, and the Neurocinetics/Total Reaction scope.
VR-0014 through VR-0018 were retired. Browser-selected clauses
and reviewed Army extras remain narrower than whole-record
acceptance. Hosted CI and final release-candidate gates are
independent. The slowest reported test fixture setups reached
294.70 s; no local full-suite timeout or test failure occurred.

**TinBot: Neurocinetics publication boundary (2026-11-02):**
The originally assumed `/equipment/tinbot-neurocinetics` inbound
route is absent by design: reviewed source ID 188 is not among the
four published TinBot source variants (169, 244, 247, 248). The
curated record retains its `uses-effects-of` relation to
`skill:neurocinetics`, but source-specific records without a
published Army application identity do not receive standalone
Equipment routes. A new browser regression
`test_unpublished_tinbot_source_variant_is_not_a_fake_public_route`
at 1440/390/320 px checks normal catalog-to-parent navigation,
absence of the invented variant card/link, keyboard access to the
independent Skill route, no JS errors and horizontal fit. API
and source-provenance tests enforce non-routability and exact
source membership. Initial test iterations corrected assumptions
about the composed-record relation schema and the empty Army
database fixture, not product defects. Final focused regression:
**5 passed**. No frontend, rules-data or publication changes.
Cumulative suite work is deferred as VR-0019; neither this check
nor the reviewed source relation grants whole-record acceptance.

The JSON contains the complete current identity crosswalk, D/S provenance
where applicable, source pages/headings, curated review flags and
selected browser-test pointers for recently published references.
Every current record retains an explicit *full acceptance not assessed*
disposition, even when its curated source status is `reviewed` or a
selected browser test exists. The Markdown is an ignored reviewer queue.
Neither the CLI nor the frozen source record inventory is a new release
gate pass. Actual source/material-clause reconciliation, verified
renames/retirements, scenario applicability, and final normal-mode
browser acceptance remain under [the TODO](TODO.md) and
[the 1.0 release gate](releasing.md#version-10-data-completeness-gate).
`tests/test_report_reference_baseline.py` covers identity counts,
malformed/duplicate historical rows, fingerprint drift and report output.

The offline `tools/report_reference_baseline.py` command inventories the published Army
source snapshot identity, rules collections and source citations, and row counts by
canonical family. Scenario membership evidence is separated by source collection,
revision and publication identity: the current published rules database has
four N5 core scenarios and a distinct ITS Season 18 Battleground pilot.
The aggregate five memberships must **not** be described as five core missions
or counted as evidence of 1.0 scenario browser completeness.

Each category now also includes an optional `routeHint` (browser/API discovery
surfaces and presentation mode) derived from the published application-domain
registry. For example, profile/loadout rows point to nested Unit detail routes,
while Attributes use the embedded Glossary. These are *candidate starting
points*, not mappings of every source record or verified player-facing evidence;
`apiReadPath`, `browserEntryPoint`, and all fact/relationship/presentation
review fields remain pending. Where domain ownership or publication is ambiguous,
the route hint is null rather than a guessed destination.
Generate ignored review artifacts from the repository root:

```powershell
python tools/report_reference_baseline.py --json-output reports/1.0-baseline.json --markdown-output docs/audits/1.0-baseline.md
```

To ensure the **running development/release server** uses the exact Army and
rules database bytes inventoried from this checkout, add
`--verify-server http://127.0.0.1:8000` (substitute the actual server origin).
The check queries the served `/api/version` response and requires its
`snapshot_revision` to equal the SHA-256 of
`"<Army database SHA-256>:<rules database SHA-256>"`, the runtime's
existing snapshot identity. On mismatch it exits nonzero **before writing
baseline outputs**; a successful run records `servedSnapshot` in JSON.
The server option is opt-in and never starts, deploys, or modifies a server.
It checks database-pair identity only: static assets, processed symbols,
PDFs, Wiki revisions, browser correctness and full source completeness
require their independent checks. Rerun against the final candidate
and deployment, not only a local development server.

Optionally pass `--army-archive <path>` to verify the exact Army ZIP SHA-256 against
the one embedded in `infinity.db`. With the pinned source ZIP available, the
baseline checks each source faction/list ID, filename, source-file SHA-256,
version and Army/reinforcement kind against the published `army_lists` rows.
It also checks every source Unit occurrence and its original list position
against `infinity.db::army_units`, matches the source-version counts,
and rejects unexpected JSON documents, duplicate Unit IDs or source-file
count mismatches. The September 29 archive has **59 JSON documents**:
58 Army-list source files plus one `metadata.json` document; these counts
must not be conflated. The optional check records `sourceIdentityEvidence`
including the source-provenance and Unit-occurrence counts. It fails closed
on source identity, provenance or Unit-membership mismatches. It also
requires the validated application/raw database export pair and verifies
all source profile-group identities, positions, categories and text fields
against published `infinity.db::profile_groups`. Every nested source
profile's identity, position and core attribute fields, and each loadout's
identity, position, name, Points, SWC, miniature count and disabled flag,
are compared with `infinity.raw.db::profiles` and
`infinity.raw.db::loadout_options` respectively. These two tables
are intentionally **not** in the published application database.
The optional audit also compares every source profile/loadout Skill,
Equipment and Weapon occurrence against the corresponding reusable
`profile_payload_*` and `loadout_payload_*` rows in the published app
database. It checks parent source coordinates, occurrence positions, source
item IDs, display order and quantity; missing, duplicated and altered
occurrences fail closed. The audit also checks each ordered `extra`
ID against the matching published `*_payload_*_extras` row, keyed by
source parent, reference occurrence, and extra position. Missing,
duplicate, reordered, and changed extras fail closed. Non-array
source `extra` values are intentionally preserved in parent raw data
rather than normalized into extras rows; this check does not certify
that raw preservation or the meaning of any extra. The pinned
archive is also compared with published `profile_payload_characteristics`,
`loadout_payload_characteristics`, and `loadout_payload_orders` through
their source-to-payload occurrence joins. Ordered Characteristic IDs and
the modeled Order type, list count and total count must match exactly;
missing, duplicated and changed positions or facts fail closed.
For the September 29 pinned archive the verified counts are **15,011
profile Characteristics**, **0 loadout Characteristics**, and **15,195
loadout Orders**. The zero count is an explicitly checked source/storage
absence, not skipped coverage; synthetic nonempty loadout Characteristics
exercise detection of discrepancies. Unknown Order fields and non-object
Order entries may be preserved as raw data and are not fully certified
by this typed check. The optional audit also verifies contextual
profile/loadout Peripheral occurrences against published
`profile_peripherals` and `option_peripherals` source rows, preserving
army-local source IDs, positions, display order and quantities. For
profile/loadout Includes it resolves the source group/option coordinates
through `loadout_payload_occurrences` and verifies the canonical target
payload, occurrence position and quantity against the published
`profile_occurrence_includes` and `loadout_occurrence_includes`.
The audit also reconstructs the source-shared global Unit options
from all pinned Army lists, rejecting cross-army changes to shared fields.
It checks each global option's source ID, position, name, Points, SWC,
miniature count, and disabled flag against published `unit_options`.
Each source Unit-option Include is expanded across every matching
army-specific `loadout_payload_occurrences` target and compared with
`unit_option_include_targets` (source position, target Army and
canonical payload, quantity). The report distinguishes original
Includes from their expanded published target count. Missing or
duplicate targets and altered fields fail closed.
This does **not** certify global-option Skill/Equipment/Weapon arrays,
Characteristics, Orders, compatibility flags, raw Peripheral
references (no unambiguous army-local namespace), derived Peripheral
entity identities, unknown raw fields, API serialization, normal-browser
display or rules semantics.

A separate maintained `tests/test_unit_source_api_parity.py` checks
**published payload-to-Unit-API parity** for an intentionally bounded
cohort of logical Units with a single source Unit and Army membership.
It reads the tracked application database, requests normal
`/api/units/<slug>` responses, matches individually identifiable
profile/loadout occurrences by source group and profile/option ID, and
compares ordered Skill/Equipment/Weapon IDs, quantities and ordered Extra IDs
against the six published reusable payload relationships. The regression
requires at least 12 candidate Units, 24 matched contexts, nonempty
coverage in all six categories and actual Extra evidence. Ambiguous
contexts and item duplicates intentionally coalesced by the logical
presentation layer are excluded from strict cardinality comparison.
The same module also verifies the cross-Army General Profile merge
projection for logical Units with **multiple distinct source Unit IDs**.
It independently checks the contributing visible Army Profile count,
representative MOV/attribute statistics, BS/ARM/VITA difference labels,
shared Weapons and loadout-specific Weapon deltas. Shared source
Equipment must survive the Skill-to-Equipment reclassification overlay,
and nonshared Equipment must remain in each army-specific presentation.
For this merged cohort, the regression also independently reconstructs
source shared Skills (including the sole-loadout rule) and source-specific
Skills before presentation classification. It verifies that normal Unit
JSON retains the original Skill IDs, quantities and Extras in the reviewed
`skills`, `equipment`, `training`, `attribute_overrides` and
`source_markers` buckets. A native Equipment row takes precedence
when a projected Skill has the same display identity and variants.
Nonempty synthetic cases cover all four non-Skill classifications and
fail on missing categories, altered quantities or Extra IDs.
The current pinned archive has no eligible case where distinct source Unit
IDs collapse into a single army-local profile/loadout; this test does
not claim to exercise that scenario. The regression requires a
nonempty multi-Army sample with differing stats and shared/specific
item evidence. It is not full-catalog Skill classification coverage,
all combined-source variants, or browser acceptance. The existing
`test_unit_source_options_notes.py` already checks source-to-API
parity for global Unit options, Orders and expanded Includes.

The normal Unit detail **browser acceptance** is available through
`tools.verify_unit_skill_presentation_browser`. It compares each rendered
General Profile and each army-local profile/loadout section with the normal
`/api/units/<slug>` response: exact row category, item name, linked
Skill/Equipment/Weapon destination, quantity and rendered Extras.
It checks absent/extra rows as well as missing items, keeps Training
and attribute overrides unlinked, and ensures API-only source markers
never gain Skill links. It also rejects missing sections, JavaScript
errors and document-level horizontal overflow. Distance Extras are
independently checked against the configured 2.5 cm/in conversion and
Skill positive-sign policy, including literal inches/centimeters.
The default matrix covers seven pinned representative Units at 1440,
390 and 320 px (**21 pages**). Three further source-backed, distinct
Units are selected deterministically by richness of their profile
payloads, loadouts and Army memberships (at least 2 profiles, 4
loadouts and 2 Armies) and verified at 1440/768/390/320 px
(**12 more pages**). Additional isolated session-preference scenarios
exercise Team-Ops off (**3 pages**), Mercenaries off (**3 pages**),
Mercenaries and Team-Ops off together (**6 pages**), and all four
optional categories off (**6 pages**). Their DOM comparisons use
identically filtered API queries, and each scenario must change
visible Armies or General Profiles. Spec-Ops and Reinforcement cases
are also selected separately through published source Unit identities
and Army-list membership, then confirmed by the normal API to have
visible, flag-specific availability. An unfiltered baseline (**6 pages**),
each flag individually disabled (**3 + 3 pages**), and both flags
disabled together (**6 pages**) must preserve exact DOM/API parity
and remove at least one visible Army for each selected Unit.
Two source-backed Units with visible distance Extras are tested
in inches and centimeters at three widths (**12 pages**).
The pinned local server passed **81/81 page checks** on 2026-10-21.
The full matrix is assembled by the pytest integration, not by the default CLI:

```powershell
.\.venv\Scripts\python.exe tools/run_checks.py --stage test tests/test_verify_unit_skill_presentation_browser.py::test_live_chromium_unit_detail_matrix_when_available --test-workers 0 --assets off
```

It starts a temporary local server and runs when Chrome and Playwright are
available; otherwise the browser test explicitly skips. A skip is not acceptance.
The separate CLI defaults to seven Units × three widths (**21 pages**).
To check an already running candidate server and save ignored evidence:

```powershell
.\.venv\Scripts\python.exe -m tools.verify_unit_skill_presentation_browser --base-url http://127.0.0.1:8000 --channel chrome --output local/audits/1.0-unit-skill-browser.json
```

Use `--exclude-optional teamops` (repeat for multiple flags),
`--distance-unit cm`, and `--width 768` (repeat for multiple widths)
to check variants against a running server.
This remains bounded representative **browser** acceptance, not
full-catalog completeness, all optional-flag combinations, all
parameterized Skill semantics, or every visual layout variant.

### Army update profile acceptance

**Project domains:** Data processing, Web backend, Web frontend

`tests/test_army_profile_publication.py` independently compares the
pinned September 29 Army ZIP with the public Unit API for ARMY-02–20.
It verifies the archive SHA-256, each member hash and source version,
and each Unit's complete set of source Army contexts. ALEPH, Tohaa,
NA2, O-12 and JSA members use `7.26246.159`; all other reviewed
members use `7.26246.158`.

| Batch | Source Units | Army/Unit contexts | Profiles | Loadouts |
| --- | --- | --- | --- | --- |
| ARMY-02–04 | Indigo (1912/1926), Confessor (1913/1927), Gui Feng/Yu Jing (1914/1928) | 22 | 66 | 220 |
| ARMY-05–08 | Intel (1915/1929), Husam (1916/1930), Vortex (1917/1931), Nexus-7 (1918/1932) | 33 | 111 | 328 |
| ARMY-09–12 | Treitak (1919/1933), Corax (1920/1934), Blur (1921/1935), Chandra (1922/1936) | 13 | 39 | 128 |
| ARMY-13–16 | Ŝtormo (1923/1937), Kaizoku (1924/1938), Hatail (1908/1909), Rumbler (1925/1939) | 25 | 77 | 248 |
| ARMY-17–20 | Ioann Bann (1940), Najjarun (314), Sāchā (1874), Racerbot (1905) | 22 | 30 | 37 |
| Total | 34 source Units | 115 | 323 | 961 |

Profiles and loadouts retain source order. Checks include Attributes, source-specific AVA,
Troop Type/classification, Characteristics, native item IDs,
quantities/ordered Extras, Orders/Training, costs and disabled options.
Null and empty Extra lists both mean no source modifier. Empty
Includes/Peripheral attachments and notes are asserted explicitly;
new populated relationships require review. Missing ignored source
bytes cause an explicit skip, not source acceptance.

The complementary
`test_army_update_native_profiles_costs_and_ava_in_browser` in
`tests/test_verify_scenario_faq_browser.py` serves the tracked database
pair through the existing WSGI Chromium transport. It checks all 34
ordinary Unit pages at 1440/390/320 px in light/dark themes (204 pages:
36 for ARMY-02–04, 48 each for the next three batches and 24 for
ARMY-17–20), using the shared Unit DOM
assertions for linked items and exact Army-local profile names,
numeric profiles, AVA, points and SWC assertions. Keyboard
expansion exposes each Army section; transition-profile AVA remains
a dash rather than an invented independent availability. Indigo's
PanOceania Hacker Order remains Irregular while the other five
source contexts remain Regular. The source/API check guards that
distinction without assigning Unit-wide Training.
Intel's Full Power and Battle Ravaged profiles remain separate, with
their distinct names, Attributes, source AVA and item sets. Nexus-7
Spec-Ops occurs in Combined Army, Onyx and Next Wave; Combined Army
TEAM-OPS occurs only in Combined Army and Onyx. The source/API check
requires those exact Army sets; browser sections must match them.
Treitak Spec-Ops occurs in Combined Army and Morat, while Morat
TEAM-OPS is Morat-only. Both Chandra Units retain three separate Army
contexts (ALEPH, Steel Phalanx and Operations Subsection), including
each source profile/loadout rather than only their shared choice chart.
Ŝtormo and Kaizoku each retain three source Army contexts per Unit.
Hatail keeps its active/inactive Symbiont profiles and Chaksa profiles
separate, preserving exact source names and values without inferring
transition mechanics. Rumbler Spec-Ops has six source contexts,
including the non-playable NA2 grouping; NA2 TEAM-OPS has five
sectorial contexts and no grouping occurrence. The ordinary Unit
reference preserves that source context without making the grouping
an independently playable Army or assigning roster legality.

ARMY-17–20 covers eight Ioann Bann contexts, five Najjarun contexts,
five Sāchā contexts and four Racerbot contexts. Sāchā's USAriadna
source has two loadouts; the other four Armies have one each. Each
Najjarun context retains its own AVA and all three loadouts, including
Ramah and Dahshat. The native API preserves Racerbot's Equipment 246
and legacy Skill 266 (Bangbomb), while the normal browser renders
the reviewed deduplicated Equipment reference. Existing
`test_non_skill_army_presentation.py` assertions separately guard
that classification, Najjarun's shared Deactivator and the selected
O-12/Starmada Ioann Fireteam memberships. These four Units have no
source-choice charts; their full profile checks do not require or
fabricate Spec-Ops charts. The wider Fireteam annotation/legality
review remains separate.

Run both parts with:

```powershell
.\.venv\Scripts\python.exe tools/run_checks.py --stage test tests/test_army_profile_publication.py tests/test_verify_scenario_faq_browser.py::test_army_update_native_profiles_costs_and_ava_in_browser --test-workers 2
```

These checks establish current native publication parity, not
profile-transition/upgrade rules, complete roster/Fireteam legality,
historical Army changes or final hosted acceptance. TEAM-OPS is retained
source data and does not expand the mandatory 1.0 ITS publication scope.

### Fireteam annotation applicability

**Project domains:** Data processing, Web frontend

`test_named_chart_annotations_preserve_exact_local_profile_context` in
`tests/test_army_fireteam_publication.py` pins 23 named source rows against
`JSON 20260929-114335.zip` (SHA-256
`f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`),
their source-member hashes/revisions and public chart API:

- Three Varuna Div rows in the `.158` Varuna member match seven local
  ORC options (13–18, 23) and three Machinist options (3, 19, 20).
- Shindenbutai's `.159` Shizoku row names Strategic Deployment. Source
  Skill 251 belongs to option 3; options 1–2 are SHIZOKU FTO. The native
  Unit API preserves this distinction without inventing FTO applicability
  for the third option.
- Fourteen `.159` Tohaa Triad rows and five `.159` Deras Kaar Triada
  rows retain their exact notes and source-local Unit resolution. The
  unresolved Reinforcement Neema row stays unresolved. These labels do
  not establish current N5 annex authority or a shared Unit Skill.

The parser and materialized `equivalence_labels` field remain byte/shape
compatible. Their name is legacy: parenthetical terms can be grouping
wording or profile qualifications; syntax alone does not prove counts-as
equivalence. The semantic audit preserves its existing report keys while
stating that limit explicitly. No database/publication rebuild is needed.

`test_named_annotations_do_not_invent_counts_as_rules` in
`tests/test_verify_fireteam_context_browser.py` checks all four ordinary
chart pages at 1440/390/320 px in light/dark themes (24 cases). Each case
uses the real Settings checkbox with keyboard activation to exercise both
Wildcard views. Exact original notes, neutral **Chart terms**, absence of
invented FTO summaries/counts-as captions, unresolved references and no
horizontal overflow remain covered. Existing FTO and chart-context suites
retain their broader source/API/browser checks.

This is descriptive source concordance and presentation acceptance, not
an executable profile-selection/legality rule or final hosted acceptance.

### Hosted Unit release-candidate acceptance

For **deployed release-candidate acceptance**, use the separate
`tools.verify_release_candidate_browser` entrypoint from the exact
candidate checkout (whose tracked generated databases and static assets
must match the deployment). It first validates the served
`/api/version` fields against the supplied release version, the
SHA-256 revision of the local Army/rules database pair, and the local
static asset fingerprint. Only then does it run the representative
Unit-detail Chromium matrix (seven pinned Units at 1440/390/320 px by
default). It repeats the served identity checks after the browser run,
and writes JSON evidence only after all stages pass. Example **for the
future tagged 1.0.0 deployment**. The README still documents
0.10.1 as the latest release; this command must not be used to claim
that the hosted service already serves 1.0.0:

```powershell
.\.venv\Scripts\python.exe -m tools.verify_release_candidate_browser --base-url https://infinitydb.tsudao.com --expected-version 1.0.0 --channel chrome --json-output local/audits/1.0-hosted-unit-browser.json
```

Optional `--army-db`, `--rules-db`, repeated `--slug` and repeated
`--width` arguments select a specific retained candidate and smaller
browser cohort. This release gate must **not** be considered passed
against an earlier deployed version or different database/static-asset
build. Local-server/real-Chromium integration and rejection tests
are not evidence of hosted release acceptance. The full local 81-page
matrix remains a separate requirement; deployed representative checks
do not imply full-catalog acceptance.

An optional integration regression exercises the exact pinned ZIP
when it exists locally and skips when it is absent. Example for
the present input:

```powershell
.\.venv\Scripts\python.exe tools/report_reference_baseline.py --army-archive "data/raw/JSON 20260929-114335.zip" --verify-server http://127.0.0.1:8000 --json-output local/audits/1.0-baseline-pair.json --markdown-output local/audits/1.0-baseline-pair.md
```

Missing ignored PDFs/wiki snapshots are explicitly
reported rather than downloaded or assumed present. The report keeps each URL-pinned
Wiki `oldid=` revision separate from the shared local Wiki archive. If a local source
file exists, its actual SHA-256 is included and compared to the curated hash when
one exists. A mismatch must be reviewed because some curated hashes can describe
logical snapshots; neither file presence nor a URL revision pin authenticates source
content. A PDF with no declared content hash remains unverified even when available.
Each source row retains publication and acquisition dates separately.

**This report is not a completeness check.** Citation presence is not source
correctness, and published row counts do not prove semantic, API, or browser
coverage. Each inventory row starts with pending source/relationship/presentation
review. Reconcile the report with the existing source-presentation, enrichment, and
rules-interaction audits before closing the Stage 1 inventory in `TODO.md`.

The FAQ v0.1 audit inventory
(`config/validation/n5-faq-v0.1-question-inventory.json`) additionally
pins the exact English v0.0 and English/Spanish v0.1 PDF hashes, paths,
versions and file-page counts. The three parameterized
`test_pinned_faq_pdf_source_identity_and_available_bytes` cases verify
maintained source declarations in every checkout and compare source
SHA-256 when the ignored local PDFs are present. Missing files produce
explicit skips, not byte-verification passes; **3/3** source hashes
matched in the 2026-10-28 local review. This gate complements, but
does not replace, question coverage, scenario applicability or browser
verification.

The separate read-only `tools/audit_1_0_reference_inputs.py` command
cross-checks supplied **source bytes** with the existing enrichment report,
the current curated Wiki citation archive and historical Wiki revisions. These
inputs are explicit and never downloaded automatically. Keep evidence output in
the ignored `local/` workspace:

```powershell
.venv\Scripts\python.exe -m infinity_db build-rules --output local/audits/1.0-rules-current.db
.venv\Scripts\python.exe tools/audit_1_0_reference_inputs.py --rules-db local/audits/1.0-rules-current.db --wiki-history "data/wiki/WIKI-en-history 20260928-165727.zip" --wiki-history-es "data/wiki/WIKI-es-history 20261009-215316.zip" --wiki-snapshot "data/wiki/WIKI-en 20260926-200832.zip" --wiki-snapshot-es "data/wiki/WIKI-es 20261009-211304.zip" --core-pdf "data/pdf/rules/n5-rules-v5-3-en.pdf" --faq-pdf "data/pdf/faq/n5-faqs-v0-1-en.pdf" --json-output local/audits/1.0-source-evidence.json --markdown-output local/audits/1.0-source-evidence.md
```

All 12 PDF source declarations now carry maintained SHA-256 pins for six
reviewed documents; see [source identities](n5-source-history.md#remaining-reviewed-pdf-identities).
The auditor compares the supplied bytes with consistent source-catalog pins
(hexadecimal case is immaterial) and renders the actual `coreRulesPdfPinStatus`
in both JSON and Markdown. A declared match establishes byte identity only.
`tests/test_curated.py` rejects malformed optional PDF hashes, and
`tests/test_restriction_storage_candidate.py` verifies declaration/export parity
and rejects unrelated changes during a source-pin refresh.

The `tools.build_deployed_object_publication --refresh-pdf-source-pins-v9`
operation stages a matched v9 pair, verifies local bytes for previously unpinned
PDF declarations, compares two independent exports, and permits only those
NULL-to-hash cells to change across the complete stored table set. The complete
schema, including indexes, must also remain identical. The matching publication
may change only its rules-database/curated-source fingerprints. Coordinated
replacement retains recovery copies of both original artifacts and restores them
if post-publication checks fail. It requires an unchanged tracked rules database
and refuses changes to existing pins or other source metadata. It also freezes
the input hashes during staging. The retained `--refresh-core-pdf-pin-v9` form
restricts the operation to the two English core declarations. These are scoped
provenance operations, not general artifact replacement workflows. The normal default rules export
remains v8-compatible. No acquisition runs during these checks.

For reviewed occurrence-parameter additions, use
`python -m tools.build_deployed_object_publication --refresh-variant-semantics-v9 skill:surprise-attack`
with the exact intended record IDs. This shares the matched-v9 pair,
deterministic double export, frozen-input and rollback checks above, but
permits only appended `occurrenceParameters` in those existing reviewed family
records. It rejects changing prior parameters, inheritance, gameplay prose,
citations, source rows, other records or schema objects. The only publication
changes allowed are the paired rules/curated-source fingerprints. This scoped
operation does not replace general versioned migrations or final release checks.

The version-4 report matches a supplied FAQ PDF against the reviewed
`sourceArtifacts` in the question inventory and consistent catalog declarations.
It records `faqPdfPinStatus`, exact `faqPdfMatchedSourceIds` and
`faqPublicationScope: not-verified-by-byte-check` in JSON, with the same identity
and status in Markdown. This identifies historical v0.0 separately from v0.1;
matching bytes do not establish publication dates, historical runtime replay or
gameplay applicability. `--faq-inventory` selects an alternative reviewed
inventory for the same check. Local verification on 2026-10-30 matched all three
reviewed FAQ files to their exact source IDs.

The report's `reinforcementsSourceEvidence` (introduced in version 3) separately checks the
audit-only [historical source inventory](../config/validation/reinforcements-source-inputs.json).
Its two relative research paths resolve within the checkout. Optional
`--reinforcements-inventory` selects another inventory under the same contract;
no files are fetched. Matching bytes establish availability of the reviewed
N4 inputs; absent ignored PDFs are `not-supplied`, and changed bytes fail closed.
The inventory cannot assert an N5 edition, current applicability or an unverified
publication date. Edition identity comes from the cover review tied to its byte
pin; the auditor does not parse the PDF or check live publication authority.
The retained `reinforcementsAnnexPdfSupplied` flag now means at least one pinned
historical PDF was verified; `reinforcementsN5AuthorityVerified` stays false.
It must not be used as an N5 procedure/completeness verdict. Tests cover
zero/one/two available files, altered bytes, invalid source claims, JSON/Markdown
report wiring and optional real-file verification. This corrects the earlier
hard-coded "PDF not supplied" report, without publishing N4 rules as N5.

The English and Spanish history archives each need `_history/index.json`
and their indexed `_history/oldid/*.html` payloads. Historical revisions
are checked by their URL language, page identity and embedded `wgRevisionId`.
With the current rebuilt rules database, `--wiki-snapshot` and
`--wiki-snapshot-es` verify the separately pinned English and Spanish
archive filenames, exact SHA-256 hashes, document counts, cited members,
rendered headings, dated Wiki errata labels, and matching page revisions
against the correct language's history archive. Repeated pins shared across
curated collections must agree. If snapshot verification is requested,
**every locally pinned Wiki language must be supplied**; an absent Spanish
snapshot or its language-matched history fails rather than silently verifying
English alone. Historical `oldid` URLs are verified independently, and an
omitted history archive leaves those revisions unverified.

The 2026-10-15 source-evidence rerun found **113/113** exact
historical Wiki revisions, **82/82** English snapshot references across 70
pages, and **2/2** Spanish snapshot references across two pages. The
shipped Army database's source archive hash was also matched with the
pinned locally available Army ZIP by `tools/report_reference_baseline.py`.
Detailed hashes and inventories remain under ignored `local/audits/`.
The former 83-gap/15-pending result is superseded: Repeater/Cube links
were reconciled and the maintained interaction ledger now has zero pending
supporting identities. Re-run enrichment and interaction audits for the target
database pair. Enrichment's historical release classifications and a missing
standalone Weapon definition are not, by themselves, current 1.0 defect
verdicts; reconcile the source-pinned shared-effect reviews and final coverage
inventory. Valid citation bytes alone never establish semantic completeness.

The report is evidence, **not** a judgment that curated interpretations or
browser presentations are complete. PDF SHA-256 values without maintained pins
remain unverified; a valid Wiki revision ID does not imply semantic correctness.
Weapon-chart name occurrences do not validate complete profiles, and Commlink's
Wiki page cannot replace the separately scoped Reinforcements annex PDF.

## CI and release validation

`docs/ci.md` owns the hosted workflow contract. `docs/releasing.md` owns the release gate. Do not
copy required-check names, branch-protection settings, or release acceptance steps into this file
unless they directly affect how local checks are invoked.

## Shared scenario composition regression coverage

`tests/test_scenario_components.py` covers explicit component identity, scope isolation,
Specialist additions/removals, same-name definitions, cycle/unknown-reference failures, and
self-contained rules-database payloads. A small Node.js harness executes the common Skill-card
renderer with the two scenario Skills and the resolved Specialist list; it reuses the dev Node
dependency and adds no JavaScript build step. Existing scenario tests still validate every game-size
row, score condition, placement, source issue, and SVG output after reference expansion.

## Reading the dated source and browser checks

The sections below retain source-specific reproduction procedures and bounded
historical results. Counts and descriptions of then-open work apply to their
stated run, not automatically to the current checkout. Current behavior belongs
to the data/semantic owners; [TODO](TODO.md) owns remaining work. Rerun affected
procedures against the exact candidate and retain new execution logs privately.

## 1.0 Weapon Trait archived-Wiki cross-reference

`tools/audit_weapon_trait_cross_sources.py` is an **offline, read-only**
source-reconciliation tool, not part of normal builds or CI. It requires the
pinned v5.3 PDF and the exact archived Wiki history ZIP in addition to the
shipped generated databases. It fails closed if the nine maintained review
identities or the PDF/Wiki payload hashes no longer match.

```powershell
.\.venv\Scripts\python.exe -m tools.audit_weapon_trait_cross_sources --core-pdf "C:\path\to\n5-rules-v5-3-en.pdf" --wiki-history "C:\path\to\WIKI-en-history.zip" --json-output docs/audits/weapon-trait-cross-source.json --markdown-output docs/audits/weapon-trait-cross-source.md
```

This compares **Traits**, not all weapon-profile values or rules prose; the
Wiki's superseded `original_border` chart rows are kept separate from current
rows. The exact Wiki member revision and bytes are pinned in
`config/validation/weapon-trait-wiki-review.json`; authoritative adjudication
remains manual and source-specific.

## 1.0 Weapon Chart partial evidence audit

The read-only `tools/audit_weapon_chart_profiles.py` compares the printed N5 v5.3
Weapon Chart to the shipped Army metadata. Its PDF layout reader reconstructs
wrapped names and two-line Plasma saving cells, selects a unique explicit or
mode-less profile, and keeps Disco Ball's auxiliary object profile separate from
the Burst-anchored rows. It compares five profile fields plus range-band slots:
printed MOD text supplies values while the PDF's vector rectangles supply
breakpoint boundaries. Bare `3` is not silently rewritten to `+3`.

The official core PDF is supplied locally and is **not** included in Git. This
offline audit additionally requires PyMuPDF (`python -m pip install pymupdf`);
normal CI and tests do not need that optional dependency. Run from the repository root:

```powershell
.venv\Scripts\python.exe tools/audit_weapon_chart_profiles.py --core-pdf data/pdf/rules/n5-rules-v5-3-en.pdf --army-db data/generated/infinity.db --json-output local/audits/weapon-chart.json --markdown-output local/audits/weapon-chart.md
```

The output includes the source PDF SHA-256, raw compared fields, range-band
evidence, candidate discrepancies, and any unresolved chart rows. Saving Roll
multipliers are interpreted together with the Saving Attribute: an Army
`savingNum=1` with `saving=-` is non-operative and matches a printed `--`.
The supplied v5.3 PDF yields 171/171 uniquely aligned rows, with 170 five-field
matches and 170 range-band matches. Kobra Pistol CC Mode has a Saving Rolls
source discrepancy candidate (PDF 1, Army 2); Katyusha MRL prints unsigned `3`
where Army has `+3`. The separate Disco Ball object's attributes match.
This remains partial evidence: other auxiliary/equipment profiles, special-weapon
prose semantics, and API/browser projection still need review. The chart report
also records the exact Army database SHA-256 so it can be safely combined with
enrichment evidence from the same snapshot.

For the seven supplementary object Silhouette conflicts, cross-check both
N5.3 language PDFs and both archived Wiki Weapon Charts as **distinct
publications**. The read-only provenance audit additionally distinguishes
each Dazer-specific Wiki equipment page from its language's chart and pins
all input hashes. It requires the locally retained source archives, PyMuPDF,
and the generated Army database (none are added to Git):

```powershell
.venv\Scripts\python.exe -m tools.audit_auxiliary_silhouette_provenance --pdf-en data/pdf/rules/n5-rules-v5-3-en.pdf --pdf-es data/pdf/rules/esp-n5-update-5-3.pdf --wiki-en "data/wiki/WIKI-en 20260926-200832.zip" --wiki-es "data/wiki/WIKI-es 20261009-211304.zip" --army-db data/generated/infinity.db --json-output local/audits/auxiliary-silhouette-provenance.json --markdown-output local/audits/auxiliary-silhouette-provenance.md
```

The output reports source values, **not** a gameplay ruling or permission to
overwrite imported Army data. The regression module exercises parsers using
synthetic inputs and conditionally validates the pinned source matrix when
those local source files are available.

Before creating a distinct deployed-object/reverse-use model, generate the
read-only source/profile and curated-rule *candidate* inventory:

```powershell
.venv\Scripts\python.exe -m tools.audit_deployed_object_inventory --army-db data/generated/infinity.db --curated-source data/curated/rules/n5-core-v5.3.json --json-output local/audits/deployed-object-inventory.json
```

The report matches the 14 pinned supplementary Weapon Chart profiles using
source name, catalog and exact mode. On the pinned Army database, the sole
additional populated profile is **Madtraps** (Weapon source ID 150, mode-less;
ARM 0, BTS 0, STR 1, S 1). N5.3 p. 69 names MadTraps among Perimeter Weapons
and p. 187 lists its attack profile, but it is not one of the 14 separate
four-attribute auxiliary chart entries. Do not discard it or treat that
exclusion as a missing source value.

Independently cross-check the **N5.3 p. 74 Deployable Profiles quick-reference
table**, which is outside the pp. 176–188 Weapon Chart extractor:

```powershell
.venv\Scripts\python.exe -m tools.audit_deployed_object_quick_profiles
```

The read-only PDF audit extracts **13 printed rows**, including two FastPanda
spellings (`FAST PANDA` and `FASTPANDA`) and two Madtraps rows. Their
source selectors resolve to **10 distinct reviewed object identities**.
The `MINES` row is a shared family, **not** an eleventh generic Mine
identity or a license to merge its six named subtypes. Duplicate labels
are preserved as repeated printed evidence, not duplicate objects.
The report checks each printed ARM/BTS/STR/S value against the existing
reviewed source/profile reference without adding a carrier or delivery
edge. It visibly retains **Armed Turret's S1 quick-reference versus S2
detailed-profile conflict**, and also exposes Dazer's existing S0/S1
source dispute even though p. 74 agrees with S0. An unmatched row or
unreviewed value fails closed. PyMuPDF and the pinned local English PDF
are required; the synthetic parser tests do not require them.
`tests/test_deployed_object_quick_profiles.py` additionally verifies the
real table when both local PDF and Army database are present.

`config/validation/deployed-object-delivery-reviews.json` now pins an
**audit-only first batch** of six reviewed delivery paths. They distinguish
Pitcher-fired and Place Deployable delivery of the same Deployable Repeater
source profile; Disco Baller versus its Disco Ball mode/object; Drop Bears'
thrown versus deployed mode; and Mine Dispenser's loadout-dependent Mine subtype.
The audit resolves exact catalog names/modes and validates cited N5.3 pages
and maintained rules text. It does **not** publish new object IDs, infer Unit
carriers, grant any mode to another item, or resolve the Mine Dispenser subtype.

A second audit-only review batch,
`config/validation/deployed-object-candidate-reviews.json`, now classifies
four nonstandard or non-object cases against maintained source evidence and
exact English N5.3 citations:

- **Deployable Cover** (p. 122): placed Scenery Element with verified **S3**
  and Cutting Foam/Vitroferro variants, but no reviewed conventional
  ARM/BTS/STR object profile. Missing attributes are retained as unreported.
- **Armed Turret** (pp. 70, 74, 195): deployed object with an independently
  curated Trooper-style profile, ARM 2/BTS 3/STR 1/S2. Its documented S1
  quick-reference conflict is not silently resolved.
- **Deactivator** (p. 121): a user-held tool/Skill that targets deployed
  objects, not itself a deployed object.
- **SymbioBomb** (p. 74): assignable single-use Weapon, not a separately
  profiled deployed battlefield object.

The remaining seven summary-keyword candidates are separately reviewed and pinned:
**WildParrot** (N5.3 p. 74), **Dazer** (pp. 121/186), and **FastPanda**
(pp. 82/186) have exact Army-source object profiles; Dazer's S0/S1
disagreement stays explicit. **Mines** (p. 72) is a shared rules family, not
one generic object or Mine subtype. **D-Charges** (p. 70) resolve during
the same Order and have no persistent four-stat object profile. **Cube**
(p. 121) is automatic equipment; **TinBot** (p. 127) uses a non-targetable
State Token rather than an independently targetable Deployable. The existing
five reviewed delivery origin records count as covered candidates, not
unreviewed objects.

For this pinned curated-summary keyword scan, all 15 matching definitions
are accounted for by reviewed classifications or delivery paths. A second
read-only audit also searches structured **Requirements, Effects,
Restrictions, Clarifications, and source notes** for Deployable/Token/Scenery
Element mentions that may be absent from summaries:

```powershell
.venv\Scripts\python.exe -m tools.audit_deployed_object_detail_queue
.venv\Scripts\python.exe -m tools.audit_deployed_object_detail_queue --json
```

This scan found one previously unreviewed detail-only record, **Cube 2.0**
(N5.3 p. 121). Its Command Token recovery reroll concerns a spent game
resource, not a separate deployed model. The decision is source-pinned in
`config/validation/deployed-object-candidate-reviews.json` as automatic
Equipment, with no manufactured object attributes. The full detailed-rule
keyword queue now has no unreviewed Weapon/Equipment definition; its
regression test fails if a new match lacks a reviewed decision or delivery
origin. Neither scan is **an exhaustive N5.3 game-object inventory**:
different wording, sources outside maintained Weapon/Equipment definitions,
Army/Unit/loadout semantics, and edition changes still need reconciliation.

The same read-only inventory now performs an **additional source-domain clause
scan** across all **104 curated Weapon/Equipment definitions**. Unlike the
original 24 summary mentions, this examines the complete summary plus
structured Requirements, Effects, Restrictions, Clarifications and source notes
for placement, deployment, representation and related language. The report
includes `additionalCuratedClauseLeads` with the exact matching text and
citations, and `unreviewedCuratedClauseLeads` separately from prior decisions.
It finds **10 additional leads** on the pinned source: SymbioBomb was
already classified as an assigned non-deployed Weapon; the other **nine are
now reviewed**, leaving no open candidates in this clause-based queue.
The additional decisions are separately pinned in
`config/validation/deployed-object-source-domain-clause-reviews.json`.
The CLI includes them by default; programmatic callers may pass its path as
the fifth argument to `audit_inventory`. The audit exposes
`reviewedSourceClauseDecisions`, `reviewedSourceClausePdfOnly`,
`unreviewedCuratedClauseLeads` and the manifest SHA-256. Existing
candidate/delivery reviews retain their separate publication boundaries.

The reviewed distinctions are:

- **Chest Mine** (N5.3 p. 72): two carried attack modes, not Mines
  placement or an independent deployed profile.
- **Sepsitor Plus** (pp. 73, 176, 187): the chart's `[*]` is a rules
  cross-reference, not a game Marker or independent object.
- **Flammenspeer** (p. 178) and **Chain Rifle** (p. 186): placed Impact/
  Direct Templates resolve attacks; they are not persistent deployed
  Weapons/Equipment.
- **Multispectral Visor** (p. 125): Level 3 targeting of an existing
  Camouflage Marker is not placement or general revelation.
- **Baggage** (p. 120): recovery of uses does not recover items already
  deployed on the table.
- **Escape System** (p. 117): an Eclipse Template accompanies an
  existing Trooper's profile/Model replacement.
- **Holomask and Holoprojector** (p. 124): disguise and Holoecho
  representations of an existing bearer, with no independent deployed
  Weapon/Equipment profile. Holoecho's gameplay interaction with other
  devices is reviewed separately under its State.

The verified N5.3 PDF citations for Escape System, Holomask and
Holoprojector have been **promoted into maintained rules and rebuilt
`rules.db`**, together with the 11 related citations from other audits.
Their source-only PDF metadata was removed from the review manifest.
The validator now checks each exact maintained source page and continues
to reject unsupported object profiles, delivery claims and citation drift.

The 104-record census is limited to maintained Weapon/Equipment
definitions; closed lexical queues cannot establish overall source-table,
Army/Unit/loadout or gameplay completeness. No new identities, attributes
or delivery links are inferred.

The second remaining inventory question is *delivery coverage for the objects
already identified*, independently of keyword discovery. Run:

```powershell
.venv\Scripts\python.exe -m tools.audit_deployed_object_delivery_coverage
.venv\Scripts\python.exe -m tools.audit_deployed_object_delivery_coverage --json
```

The pinned review has **17 reviewed object identities and 28 approved
delivery paths**, with no uncovered origin for an object in that bounded
publication. This is not a complete N5.3 object inventory. WildParrot has
separate Place Deployable and WIP-based Intuitive Attack methods (N5.3 pp.
49, 74, 82); FastPanda uses Perimeter placement (pp. 82, 186), and Armed
Turret uses a reviewed-only curated Trooper profile rather than an invented
Army four-stat profile (pp. 70, 74). Its S1/S2 conflict remains visible.
The report provides exact source-ID-based catalog aliases only as
**candidates to investigate**: a source alias does not prove delivery mechanics,
mode or Unit/Army roster legality. Mine Dispenser's subtype remains separately
unresolved. `tests/test_deployed_object_delivery_coverage.py` guards these
boundaries and verifies that aliases cannot become inferred delivery edges.

The Weapon/Equipment candidate validator rejects mismatched profile shapes,
exact Army profile selectors/attributes, lost source clauses/citations, and
invented missing-attribute values. Source text and alternative Silhouette
values remain unchanged; no canonical object or carrier IDs are created.

### Non-catalog game-element discovery

Weapon/Equipment definition scans do not examine Skills, generic rules,
Traits, terminology or States. Audit their own definition summaries and
structured detail fields without turning keyword mentions into object IDs:

```powershell
.venv\Scripts\python.exe -m tools.audit_deployed_object_non_catalog_queue
.venv\Scripts\python.exe -m tools.audit_deployed_object_non_catalog_queue --json
```

The separate `config/validation/deployed-object-non-catalog-reviews.json`
manifest pins **51 source-reviewed definitions** in this bounded keyword scan,
with no unreviewed candidates. Access Width gate Tokens label scenery
openings (p. 145); Army Retreat Tokens indicate existing Trooper conditions
(p. 146); Combat Group affiliation identifies the group of an existing
deployed Weapon or Equipment Marker (p. 10). None creates an additional
deployed-object profile or delivery permission.
Six earlier decisions initially had PDF-only evidence recorded in the
audit manifest. Their verified N5.3 citations have since been migrated to
maintained rules records and synchronized with the rules database/publication;
the audit now reports no missing maintained N5.3 citations.
The original three Skill decisions distinguish `skill:place-deployable`
(delivery action, p. 82), `skill:minelayer` (deployment method, p. 102)
and `skill:request-speedball` (support State Tokens, p. 84). Additional
source-reviewed classes distinguish:

- **Five glossary concepts** (p. 173): Token, State Token, Deployable
  Weapon/Equipment and Scenery Element describe types or representations,
  never a single universal object identity, profile or delivery edge.
- **SpecBall** (p. 98): `skill:request-specball` places one support
  State Token, distinct from Speedball's two Tokens. Neither blocks
  enemy Movement or can be Deactivated. A separately selected SpecBot
  requires its own evidence; the drop Token does not establish its profile.
- **RemDriver** (p. 110): the Token shows a MOD assignment to an existing
  Remote and is not an independent deployed device.
- **Peripheral (Ancillary)** (pp. 107–108): the Controller can place an
  Ancillary Trooper with Place Deployable, but this belongs to the Peripheral
  Unit/Profile model, not a generic Weapon/Equipment deployed-object profile.
  Dedicated Peripheral reference coverage is a separate question.
- **Supplies** (p. 153): carrying a Supply Box preserves its scenario
  Token even with a Null carrier; the Pick Up Supply Boxes Skill manipulates
  that scenario objective. These are not Army source Weapon/Equipment items.
- **Deployable, Perimeter and Boost Traits** (pp. 175, 82 and 69):
  these define the object class, placement variation and trigger behavior,
  respectively, not interchangeable device identities. Boost/Mines remain
  distinct; a generic Trait does not authorize a delivery edge.
- **Intuitive Attack** (p. 49) conditionally permits placement of eligible
  Deployable Weapons and consumes a use on a failed Roll where applicable.
  It is a delivery Skill, not a separate deployed profile.
- **Dodge, Guts Roll, Stealth and Cautious Movement** (pp. 79-80, 38,
  112 and 32/112) distinguish exempt post-Roll movement from ordinary
  triggering and ARO restrictions. None adds a carrier or object.
- **Control and Cyberplug Peripherals** (pp. 107-108): Spearhead and
  Autonomous Tokens indicate a Peripheral's role or operating profile,
  not independent Weapon/Equipment objects.
- **Camouflaged and HoloMask States** (pp. 157 and 164): a Marker/imitated
  Model represents an existing identity. HoloMask expressly cannot copy
  Deployable items represented by Models or Tokens.
- **Combat Jump, Impersonation, Infiltration** (pp. 89, 96-97): a failed
  superior deployment removes already placed eligible Deployables. The Skill
  does not establish an unsourced item identity or carrier.
- **Impetuous, NWI, Protheion, G: Jumper, Retreat!** (pp. 97, 104,
  109, 93 and 170): activation, State, VITA and Active Proxy Tokens
  represent the owning Trooper's existing status or role.
- **Doctor, Engineer, Remote Presence, Strategos L2 and MOD rules**
  (pp. 90-91, 110, 113, 68): Command Tokens are expended resources or
  reroll references, not physical deployed objects.
- **Coordinated Orders and Deployment Phase** (pp. 129-130, 15):
  Spearhead Tokens identify a participant; deployment/order exceptions do
  not grant item identity or reverse Unit ownership.
- **Domination and Hacking Area** (pp. 151, 55-57): scenario scoring
  excludes Weapon/Equipment Markers; existing Repeaters extend Hacking
  Area but do not become another item or delivery edge.

The final six decisions were verified against the pinned English N5.3
PDF: `skill:frenzy` (p. 93, indirectly inflicted Deployable wounds do
not qualify); `state:possessed` (p. 169, an existing Trooper changes
control/profile); `rule:command-token-strategic-use` (p. 128,
resource expenditure and Speedball State Tokens);
`skill:counterintelligence` (p. 90, counters strategic resource use);
`skill:inspiring-leadership` (p. 99, modifies Order expenditure);
and `skill:transmutation` (p. 117, changes the same Trooper's
Unit Profile and representation). None establishes a separate
Weapon/Equipment deployed-object identity.

These six definitions now have **maintained N5.3 PDF citations** in the
curated rules and regenerated `rules.db`. Their former
`citationStatus: pdf-verified-manifest-only` and `pdfExcerpt` fields
were retired as part of the coordinated promotion, which also refreshed
the deployed-object publication fingerprint. The audit continues to
verify exact source pages and summary/detail evidence. Its
`reviewedPdfOnly` and `missingMaintainedN5Citation` reports are now empty.

The decisions were manually compared with pinned English N5.3 pages.
The audit validator pins source citations already in maintained definitions
or explicit transitional PDF-only review evidence, plus curated summary
and detail evidence; it does **not** parse the PDF in CI. No new ARM/BTS/STR/S
value, Army carrier, delivery edge or runtime object is inferred.
Summary-only glossary/trait reviews remain valid only while they lack
detailed source fields. All 48 keyword-matching definitions are classified,
but the scan covers neither unmentioned terms nor other source domains and
is **not** a complete N5.3 object inventory.
`tests/test_deployed_object_non_catalog_queue.py` checks these boundaries.

### Expanded non-catalog battlefield-element discovery

The initial 48-definition queue excludes other relevant wording, including
Consoles, Supply Boxes, Disco Balls, and Marker/decoy representations. Run a
separate, read-only pass over Skill/Rule/Trait/Term/State definitions:

```powershell
.venv\Scripts\python.exe -m tools.audit_deployed_object_expanded_queue
.venv\Scripts\python.exe -m tools.audit_deployed_object_expanded_queue --json
```

The expanded audit excludes all 48 candidates from the original scan rather
than recounting them. It identifies **25 additional definitions, all
classified** in `config/validation/deployed-object-expanded-reviews.json`.
Five decisions use audit-only PDF evidence because their maintained
definitions still cite only the Wiki. N5.3 pp. 151 and 153 establish that
Domination's four
Consoles and Supplies' three Supply Boxes are *scenario-specific objectives*,
represented by scenario Markers or scenery; Hack Consoles and controlling
Supply Boxes act on those existing objectives and create no further objects.
N5.3 p. 71 makes Activate Disco Ball an interaction with the previously
reviewed Disco Baller source-mode object, **not another delivery method or
object identity**. The generic Marker terminology on p. 173 likewise
describes a representation rather than a concrete source catalog object.

The second review batch distinguishes **Decoy deployment** (p. 90),
**Holoecho** (pp. 162–163), **Hidden Deployment** (pp. 161–162),
**Impersonation-1/-2** (pp. 166–167), **Discover** (p. 77),
**Surprise Attack** (p. 114) and **Sensor** (p. 111). They operate on
representations or detect/modify existing Troopers, Weapons and Equipment;
none provides another independent deployed-object profile or Army carrier.
Crucially, Holoecho duplicates are **not inert markers**: p. 162 explicitly
treats them as Troopers for ARO, LoF and triggering deployed Weapons/Equipment,
including Mines and CrazyKoalas. Their separate removal rules are reviewed
on p. 163. Likewise, a normal successful Discover against Impersonation-1
reduces it to Impersonation-2, whereas Discover against Impersonation-2
reveals the underlying Model. This does not create two Trooper identities.

The final 11 cases distinguish **Indiscriminate** (p. 175, an existing
item's placement exception), **Look Out!** (p. 81), **Chain of Command**
(p. 87), **Morpho-Scan** (p. 103), **scenario Killing and Reinforced
Tactical Link** (pp. 150/155), **Decoy State** (p. 159), **Concealed**
(p. 175), **Mnemonica** (p. 103), **Tactical Awareness** (p. 115),
and **Explode** (p. 92). These concern target/role eligibility,
existing Model or Marker representations, Orders, or a Trooper-centered
Attack Template, not a new independently deployed Weapon/Equipment.
Decoy replicas are static, but can affect LoF and be targeted under the
State rules. The Concealed Trait describes S2 Camouflage Markers for
existing Weapons/Equipment, not an additional deployed item.

The five previously PDF-only records—`state:decoy`,
`trait:concealed`, `skill:mnemonica`, `skill:tactical-awareness`
and `skill:explode`—now have their verified N5.3 source pages
in the maintained curated definitions and regenerated `rules.db`.
Temporary `pdfExcerpt` and `citationStatus` metadata has been
retired. The expanded audit's `reviewedPdfOnly` and
`missingMaintainedN5Citation` reports are now empty. CI still
validates the curated citations, not the ignored source PDF.

This expanded scan is deliberately bounded to named objectives/devices
and Marker/decoy wording, not all N5.3 prose, source tables, or possible
game elements. The manifest and validator reject unsupported IDs,
lost detail clauses, stale citations or inferred object profiles. No
production database, published object count, Unit ownership or approved
delivery path is changed.
`tests/test_deployed_object_expanded_queue.py` checks the discovery and
fail-closed review boundaries.

### N5.3 Hacking Device Programs source chart

The English N5.3 p. 58 **Hacker Device Programs Chart** lists four
Hacking Device Equipment types and the Programs each one grants. It
is distinct from the **Hacking Programs Chart** on the same page,
which gives individual Program statistics. The review manifest
`config/validation/hacking-device-program-source-chart.json` pins
the four source rows, their printed Program-column order, and the
fact that this is a device access matrix rather than Unit ownership,
a deployed object, or an additional Program identity.

```powershell
.venv\Scripts\python.exe -m tools.audit_hacking_device_program_source_chart
.venv\Scripts\python.exe -m tools.audit_hacking_device_program_source_chart --pdf data/pdf/rules/n5-rules-v5-3-en.pdf --json
```

The four devices grant **4 / 6 / 2 / 4** Programs, respectively
(Hacking Device, Hacking Device Plus, Killer Hacking Device, EVO
Hacking Device), for **11 distinct Program definitions** in the
union. The audit checks exact maintained Equipment access-link
sets and matching canonical Hacking Program records. The optional
`--pdf` mode verifies the printed device table's four Program
assignments separately from the preceding Program statistics table.
Missing, duplicated or incorrectly assigned Programs, changed source
scope, and missing canonical records fail closed. CI does not require
the ignored local PDF.

The four Equipment facts agree with the N5.3 chart. On 2026-10-30,
the four p. 58 citations were staged, verified and **promoted together**
with the matching `rules.db` and deployed-object publication. The checked-out
source now retains both the existing wiki citations and direct N5.3 citations,
without changing its 4/6/2/4 Program assignments. The checkout audit reports
`missingMaintainedN53ChartCitations: []`.
The audit's `missingMaintainedN53ChartCitations` report allows
either all four missing or none missing and fails closed on partial
migration, duplicate N5.3 source citations or incorrect page.
`tests/test_hacking_device_program_source_chart.py` covers these
boundaries and the four source-backed Program sets.

#### Stage and promote the four N5.3 p. 58 Equipment citations

The reviewed migration stages and promotes one
`{"sourceId":"n5-core-v5.3-pdf","page":58}` citation to each of
`equipment:hacking-device`, `equipment:hacking-device-plus`,
`equipment:killer-hacking-device` and
`equipment:evo-hacking-device`. It retains all wiki citations
and existing Equipment facts. Because the tracked rules database
changes, the dependent deployed-object publication was rebuilt and
promoted **in the same batch**.

From the repository root, after committing the staging tool/tests
and with unchanged curated source and Army database:

```powershell
& .\.venv\Scripts\python.exe -m tools.stage_hacking_device_chart_citations --output-dir local/hacking-device-citations-n53 --pdf data/pdf/rules/n5-rules-v5-3-en.pdf
```

The command refuses an existing staging directory and writes
`staging-report.json` with the original source and Army SHA-256,
the verified PDF SHA-256, four migrated IDs, and three artifact
hashes. It **never changes the tracked checkout**. The isolated
regression `tests/test_hacking_device_chart_citation_staging.py`
builds and validates the same three artifacts under a temporary
directory, compares the published 17 object records byte-for-byte
and checks all tracked inputs remain unchanged.

**Staging and promotion verified 2026-10-30, HEAD `5e4647c`.**
Before promotion, the live input hashes matched the staging report: curated source
`264db18e21c6a2cf4e7de98d3532726735b3b9e7309feef9c4e56cb38341f0e8`
and Army database
`8a5840d1ff632e89de26210ee7bcb47e54c6579c15b5c3436e226702e872d7c8`.
The PDF fingerprint is
`53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f`.
Independently inspected **staged and promoted** hashes match the report: curated source
`e40f8bbd6b83fc74dd301d620bc36021d19b68e6551c9afc16d590b86d1e9756`,
`rules.db`
`3cd6653be1e34193477946eb850e90b13baa102be88c23b7bbfdcaba9a760636`,
and `deployed-objects.json`
`262f47cd4e32173919452367dd599f66a66df727d692ac8a6d73bde5e90f5398`.
The staged publication passes `--check`; it embeds the matching rules
database fingerprint and retains all 17 reviewed objects and approved
delivery paths. Pre-promotion focused tests: **8 passed, 1 skipped**.
Post-promotion staging/promotion tests: **5 passed, 2 expected skips**
(including an injected mid-batch copy failure and successful rollback);
chart tests: **5 passed**. The checkout audit now reports zero missing
citations; publication `--check`, rules, Ruff, Markdown lint, documentation
links and canonical Pyright (0 errors/0 warnings) all pass. The full suite
and CI are reserved for the broader release gate.

The tracked staging module now supports guarded promotion through MCP
`run_script`, with `--output-dir local/hacking-device-citations-n53
--promote-staged`. It verifies all source/staging fingerprints, independently
rebuilds the dependent publication, checks the 17 unchanged objects and
copies all three artifacts with rollback on validation failure. Its recovery
backup is retained under ignored `local/hacking-device-citation-backup-*/`.
A three-file replacement is not filesystem-atomic; the backup permits
recovery after interruption.

The following PowerShell procedure was prepared before the tracked
promotion command became available. It is retained as a **historical manual
fallback**, not a step to repeat after this completed promotion. It verifies
source/Army and staged hashes before writing, and attempts rollback on error:

```powershell
$stage = "local/hacking-device-citations-n53"
$report = Get-Content (Join-Path $stage "staging-report.json") -Raw |
    ConvertFrom-Json
$expected = @(
    "data/curated/rules/n5-core-v5.3.json",
    "data/generated/rules.db",
    "data/generated/deployed-objects.json"
)
$ids = @(
    "equipment:hacking-device",
    "equipment:hacking-device-plus",
    "equipment:killer-hacking-device",
    "equipment:evo-hacking-device"
)
if ($report.scope -ne "staged-only-hacking-device-p58-citations-not-applied" -or
    $report.sourcePage -ne 58 -or $report.reviewedObjects -ne 17 -or
    (@(Compare-Object $expected $report.stagedPaths).Count -ne 0) -or
    (@(Compare-Object $ids $report.migratedDeviceIds).Count -ne 0)) {
    throw "Unexpected device citation migration report"
}
if (git status --porcelain -- $expected) {
    throw "The three promotion targets have changed since staging"
}
if ((Get-FileHash "data/curated/rules/n5-core-v5.3.json" -Algorithm SHA256).Hash -ne
    $report.sourceSha256 -or
    (Get-FileHash "data/generated/infinity.db" -Algorithm SHA256).Hash -ne
    $report.armySha256) {
    throw "Current curated source or Army database changed after staging"
}
$hashes = @(
    $report.stagedSha256.curated,
    $report.stagedSha256.rulesDatabase,
    $report.stagedSha256.deployedObjects
)
for ($i = 0; $i -lt $expected.Count; $i++) {
    $file = Join-Path $stage $expected[$i]
    if (-not (Test-Path -LiteralPath $file -PathType Leaf) -or
        (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne $hashes[$i]) {
        throw "Missing or altered staged artifact: $file"
    }
}
$ErrorActionPreference = "Stop"
$backup = Join-Path "local" ("hacking-device-citation-backup-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $backup | Out-Null
$cleanupBackup = $false
try {
    foreach ($path in $expected) {
        $saved = Join-Path $backup $path
        New-Item -ItemType Directory -Path (Split-Path $saved -Parent) -Force | Out-Null
        Copy-Item -LiteralPath $path -Destination $saved
    }
    foreach ($path in $expected) {
        Copy-Item -LiteralPath (Join-Path $stage $path) -Destination $path -Force
    }
    for ($i = 0; $i -lt $expected.Count; $i++) {
        if ((Get-FileHash -LiteralPath $expected[$i] -Algorithm SHA256).Hash -ne $hashes[$i]) {
            throw "Promoted artifact hash mismatch: $($expected[$i])"
        }
    }
    $auditJson = & .\.venv\Scripts\python.exe -m tools.audit_hacking_device_program_source_chart --json
    if ($LASTEXITCODE -ne 0) { throw "Hacking Device source audit failed" }
    $audit = $auditJson | ConvertFrom-Json
    if (@($audit.missingMaintainedN53ChartCitations).Count -ne 0) {
        throw "Hacking Device citation migration remained incomplete"
    }
    & .\.venv\Scripts\python.exe -m tools.build_deployed_object_publication --check
    if ($LASTEXITCODE -ne 0) { throw "Deployed-object publication check failed" }
    $cleanupBackup = $true
} catch {
    $promotionError = $_
    try {
        foreach ($path in $expected) {
            $saved = Join-Path $backup $path
            if (Test-Path -LiteralPath $saved -PathType Leaf) {
                Copy-Item -LiteralPath $saved -Destination $path -Force
            }
        }
        $cleanupBackup = $true
    } catch {
        Write-Warning "Rollback incomplete; preserve backups at $backup"
        throw
    }
    throw $promotionError
} finally {
    if ($cleanupBackup) { Remove-Item -LiteralPath $backup -Recurse -Force }
}
```

Post-promotion checks confirm `missingMaintainedN53ChartCitations: []`,
matching generated artifact fingerprints and identical approved delivery
paths for all 17 reviewed objects. The change affects **citations only**;
Program statistics, Unit carriers and canonical object identities remain
unchanged. The full suite and CI still require release-level execution.

### N5.3 Hacking Programs statistics source chart

The independent **Hacking Programs Chart** on English N5.3 printed p. 58
defines 12 Program profiles. The read-only manifest
`config/validation/hacking-program-statistics-source-chart.json` records all
printed Program names, Attack/Opponent MOD, PS, Burst, Target and Skill Type
cells, plus separately reviewed Special-clause evidence. It is distinct from
the four-device Program entitlement chart and does not authorize additional
Equipment, Unit carrier or deployed-object identities.

```powershell
.venv\Scripts\python.exe -m tools.audit_hacking_program_statistics_chart --json
.venv\Scripts\python.exe -m tools.audit_hacking_program_statistics_chart --archive "data/raw/JSON 20260929-114335.zip" --pdf data/pdf/rules/n5-rules-v5-3-en.pdf --json
```

The offline default checks the exact source rows against the published
`infinity.db` Program profiles without requiring ignored source assets.
Optional `--archive` verifies the pinned September 29 Army ZIP SHA-256 and
its original `metadata.json` Program values, including source order,
declaration types, targets and normalized Special text. Optional `--pdf`
verifies the pinned English PDF fingerprint and every printed row/column,
including the reviewed Special-clause fragments, using page geometry rather
than raw text extraction order.

**Reviewed 2026-10-30:** all 12 Program identities and numerical,
Target/Skill Type and Special-clause evidence agree; zero mismatches.
The PDF lists **Total Control, Trinity, Spotlight**, while Army metadata
lists **Spotlight, Total Control, Trinity**. The audit records this
source-order discrepancy and joins by Program name; it is not a changed
Program profile. The existing `tests/test_hacking_program_publication.py`
continues to cover the Army-to-API/browser-data layer. The adjacent
`tests/test_hacking_device_program_source_chart.py` covers both page 58
source audits, drift detection and optional PDF/archive evidence. No
runtime database or curated Program record was modified.

**Target dash follow-up (N5.3 pp. 57–61):** the `Target` column
identifies specified Troop Types; five Program source rows have no Troop
Type listed, but their detailed effects are distinct (for example,
Spotlight, Cybermask and White Noise). The normal Program detail keeps
Army's source-derived `—` while adding a brief note to consult the
Program's individual requirements/effects rather than interpreting a
missing Troop Type as no valid target. The source regression verifies the
printed chart key and program-specific clauses; the maintained
`tools.verify_hacking_programs_browser` acceptance checks the conditional
note alongside all original Army stat cells at 1440/390/320 px.

For repeatable localhost browser acceptance without an external server:

```powershell
.venv\Scripts\python.exe -m tools.verify_hacking_programs_browser --self-host --output local/hacking-program-target-scope-browser-20261030.json
```

The self-host mode launches a disposable loopback WSGI server using the
current pinned Army/rules databases, then shuts it down. The existing
`--base-url` mode remains available for checking a deployed origin.
**Verified 2026-10-30: 36/36 real Chromium Program pages passed** (12
Programs at 1440/390/320 px). This validates the conditional target-scope
note and original profile/Device/citation rendering, not the full 1.0
browser or release suite.

### N5.3 Restrictions Chart source and browser reference

The English N5.3 **Restrictions Chart** (printed p. 194) lists six source
conditions and 14 prohibited actions/eligibility choices. The read-only
`config/validation/restrictions-source-chart.json` records each source
subject, negative action, reference target and scope without materializing
runtime relationships or assigning invented Troop Type identities.
The audit cross-checks the relevant existing curated records and highlights
missing or insufficiently scoped typed relationships:

```powershell
.venv\Scripts\python.exe -m tools.audit_restrictions_source_chart --json
.venv\Scripts\python.exe -m tools.audit_restrictions_source_chart --pdf data/pdf/rules/n5-rules-v5-3-en.pdf --json
```

The optional PDF check requires PyMuPDF, verifies the pinned source SHA-256
and matches all six ordered printed restrictions between the chart headings.
The default runs offline from the maintained manifest and curated JSON.
Regression tests are in `tests/test_game_mode_source_table.py` with the
other independent N5.3 source-table audits.

**Reviewed 2026-10-30:** all six source lines match, with 14 separately
identified restrictions. TAG, VH and REM are source Troop Type selectors,
not canonical rules identities; Motorcycle's printed restriction concerns
**upward** Jump and its ladder prohibition is distinct from Climb.
Irregular Training's Lieutenant restriction concerns **selection**, not
the act of using a Skill. Existing broad `restricts-use-of` relations
cannot currently express those qualifications. This audit does not assert
positive legality, Unit ownership, or restrictions beyond the finite
source chart.

The reviewed manifest is now projected into packaged
`src/infinity_db/web/static/restrictions-reference.json`; the normal
General Rules catalog loads this read model at `/rules#restrictions`.
The display groups six source conditions and 14 linked, condition-scoped
negative facts. Troop Type selectors without canonical references remain
plain text. The JSON must match the deterministic source projection
byte-for-byte:

```powershell
.venv\Scripts\python.exe -m tools.audit_restrictions_source_chart --check-publication --pdf data/pdf/rules/n5-rules-v5-3-en.pdf --json
.venv\Scripts\python.exe -m tools.audit_restrictions_source_chart --output local/restrictions-reference-staged.json
```

The second command stages replacement bytes under the ignored `local/`
directory for review, without overwriting the live tracked asset.
`tests/test_game_mode_source_table.py` checks publication byte parity,
source drift, WSGI static delivery and three real Chromium viewport
renderings (1440/390/320 px), including conditional scope, references
and page overflow.

The reviewed read model also carries `ownerRecordId` and
`targetRecordId` for **source-backed reverse contextual links**.
The same Chromium test visits seven relevant canonical pages:
Motorcycle Equipment, Aerial, Cautious Movement, Climb, Jump,
Lieutenant and Prone State. It checks exact condition counts and
anchor targets at all three viewports, follows the upward-Jump link
back to its source row, and confirms the unrelated Dodge page does
not show a spurious Restrictions section. The source regression also checks byte-exact publication parity.

**Typed condition contract:** the source compiler in
`src/infinity_db/restriction_conditions.py` covers all 14 negative
constraints using exactly five operation kinds. It preserves source
Troop Type selectors without canonical IDs, requires the existing
owner/target records where appropriate, and fails closed on incorrect
action targets, source scopes or positive-permission interpretation.
The public model adds `subjectKind` and `operation.kind` /
`operation.qualifier` alongside existing chart data. Browser
acceptance checks upward Jump, ladder traversal and Lieutenant
selection carry distinct typed operation kinds at all three widths.
The v9 schema adds a separate table, without changing the
generic `record_relations` graph. Its source audit still reports
seven non-materializable conventional edges: two TAG, two VH,
two REM (all source-only Troop Types with no canonical owner) and
one mounted Motorcycle ladder traversal (with no Skill target).
`test_n53_seven_non_graph_restrictions_keep_source_scoped_api_and_browser_coverage`
pins all seven against the complete 14-item v9 API and published
browser JSON, checks target-based navigation, and verifies that
no fabricated owner or ladder Skill is needed. Missing generic
edges are **not** missing source coverage and cannot imply
positive legality. The two inherently over-broad legacy edges
retain **scoped, bidirectional player-facing presentation labels**
only; their types and endpoints remain unchanged for compatibility.
`tests/test_rule_relations.py` checks v8/v9 views and other
relationship labels. This is contextual help, not a declaration
or Army selection legality resolver.

**Isolated State contextual navigation:** the source regression in
`tests/test_state_catalog.py` checks distinct membership and
participation edges, two-way composed relations, and maintained
text that distinguishes Leader cancellation from member departure.
The tracked v9 rules database was rebuilt alongside its matching
deployed-object publication using the guarded
`tools.build_deployed_object_publication --refresh-isolated-context-v9`
command. This checks exactly two additional legacy relation rows,
unchanged 14 typed Restrictions, unchanged reviewed deployed-object
content, and updated rules/curated-source fingerprints; original
paired v9 artifacts are retained under ignored `local/`.
An API regression checks the real routed destination: Fireteam
General Rules belongs to the specialized `/fireteams` landing
whose reviewed facts already link back to Isolated, whereas
Coordinated Orders has a standard General Rules detail with a
reciprocal typed relationship. The
`test_isolated_navigation_browser_links` Chromium acceptance checks
the State's two destinations, the reciprocal Coordinated Orders link
and the Fireteams existing Isolated link at 1440/390 px.
No live State, whole-team ban, or Army legality is inferred.

Irregular Training has no standalone catalog route. The source
ownership is now verified against the tracked Army database:
`loadout_payload_orders.order_type` contains actual Irregular
occurrences, and `SkillCatalog.enrich_unit()` maps those specific
Order entries to `training:irregular`. The existing Skill/Training
item arrays were not the authoritative Order source. Regression
`tests/test_rules_database.py::test_tracked_army_irregular_order_occurrences_map_to_training_without_unit_inference`
checks the real source-to-Unit-detail projection and prevents an
unreviewed Unit/profile-wide Training claim. The Lieutenant Skill and
source chart already expose the Irregular selection prohibition; no
Unit-level reverse link is published.

**Version-aware SQLite/API migration contract (v9 locally promoted, not deployed):**
`tests/test_restriction_storage_candidate.py` prepares a separate
v8 rollback test database when the tracked release artifact is v9,
then adds the `restriction_constraints` table using
`src/infinity_db/restriction_storage.py`, and verifies the 14
reviewed negative conditions and additive JSON read shape. The test
asserts legacy `record_relations` rows and representative composed
API records remain unchanged, verifies source-order and filters,
rejects positive polarity, duplicate staging, invalid IDs/scopes,
and confirms an empty filter result conveys no permission.
The version-aware reader now accepts exact v8/compatibility-10
and v9/compatibility-11 pairs and rejects incomplete v9 models,
version mismatches and unsupported revisions.

```powershell
.venv\Scripts\python.exe tools/run_checks.py --stage test tests/test_restriction_storage_candidate.py
.venv\Scripts\python.exe tools/run_checks.py --stage test tests/test_game_mode_source_table.py
```

The suite also exports the reviewed v9 snapshot twice and asserts
byte-for-byte determinism, compares the legacy relation graph, and
tests `/api/restrictions` on both versions: v8 reports
`available: false`; v9 returns 14 source-scoped prohibitions
with filters and no positive legality inference. Legacy Skill
and Equipment JSON remains unchanged. The normal standalone
exporter remains v8/compatibility-10; the **tracked release**
`data/generated/rules.db` now uses v9/compatibility-11.
For a separately staged v9 build, use:

```powershell
.venv\Scripts\python.exe -m infinity_db build-rules --restrictions-manifest config/validation/restrictions-source-chart.json --output local/restrictions-rules-v9.db
```

The opt-in path refuses the default `data/generated/rules.db`
destination. A paired promotion instead uses the tracked
`tools.build_deployed_object_publication` module:

```powershell
.venv\Scripts\python.exe -m tools.build_deployed_object_publication --stage-restrictions-v9 local/restrictions-v9-n53-20261030-reviewed
.venv\Scripts\python.exe -m tools.build_deployed_object_publication --promote-restrictions-v9 local/restrictions-v9-n53-20261030-reviewed
```

Staging refuses existing output directories; promotion requires matching
reviewed input hashes, an unchanged tracked v8 database, the exact
staged SHA-256 pair, and the same 17 deployed-object records with no
additional publication changes. Both original v8 artifacts are retained
under ignored `local/`. The historical Hacking Device citation test
now checks source citations and deployed-object content across later
schema versions, not obsolete byte identity.

The deployment-smoke workflow requires 14 typed constraints in the
tracked v9 database and builds its matching deployed-object publication
before the image; `scripts/verify-container-image.sh` checks the actual
HTTP Restrictions conditions after startup and accepts explicit v8
unavailable-data behavior. An additional **CI rollback-image rehearsal**
rebuilds a disposable v8 rules/publication pair, compares its 17 reviewed
objects and legacy graph against v9, overlays both artifacts into a copy
of the tested release image, starts that v8 image with full HTTP checks,
then rechecks the original v9 image. The original retained v8 backup
and production host are not altered by the CI rehearsal. The overlay
Docker gate passed hosted Deployment smoke for commit `663a345`
(2026-10-30); live-host rollback remains untested.

Local regression coverage:
`tests/test_restriction_storage_candidate.py::test_disposable_v8_rollback_pair_preserves_v9_reviewed_objects`
tests actual matched v8/v9 publication payloads, while
`tests/test_deployment_scripts.py::test_deployment_smoke_builds_and_exercises_v8_rollback_image`
pins the sequence and isolation of the CI image gates.
The local promotion and remaining hosted acceptance are recorded in
[the data model](data-model.md#restriction-persistence-and-version-aware-api-v9-locally-promoted).
Normal tests never write to the tracked runtime database.

### N5.3 Silhouette Templates source and browser geometry

The English N5.3 **Silhouette Templates** table (printed p. 18)
defines ten representations: SX, S0 and S1–S8.
`config/validation/silhouette-template-source-table.json` pins
the base width and template height in millimetres for each source row.
An independent read-only audit compares these source rows against the
eight fixed dimensions in the browser's
`src/infinity_db/web/static/silhouette-diagrams.js` and the canonical
`attribute:s`/Prone State references:

```powershell
.venv\Scripts\python.exe -m tools.audit_silhouette_template_source_table
.venv\Scripts\python.exe -m tools.audit_silhouette_template_source_table --pdf data/pdf/rules/n5-rules-v5-3-en.pdf --json
```

**S0** has a fixed 25 mm base and 3 mm height. **SX** is the
3 mm high representation for a Trooper in Prone State; the base
width depends on the Trooper's original Silhouette Attribute and
must not be flattened to a universal 25 mm base or another permanent
Unit value. The existing UI displays S1–S8 at a shared scale with
source-backed SVGs and provides explicit text for S0/SX, which have
no supplied reference SVGs. Neither is an independently deployed
Weapon/Equipment identity.

The source audit rejects changed table dimensions/order, an invented
fixed SX base, missing/changed S1–S8 diagram sizes, absent SVGs,
broken display-mode safeguards or missing maintained attribute
references. Optional `--pdf` checks the exact printed table and
Prone footnote using the local pinned English N5.3 PDF. The audit
does not require the ignored PDF during CI and does not rewrite
the application, publish profile attributes, or modify generated
artifacts. The separate UI regression still verifies the existing
diagram component and SVG delivery.
`tests/test_silhouette_template_source_table.py` pins the source
rows, browser geometry, negative drift cases, and local PDF evidence.

### N5.3 Game Modes versus general setup/reference tables

The **Game Modes chart** (printed English N5.3 p. 6) is a separate
recommended-play reference, not an authoritative scenario forces/setup
contract. Its six named modes provide Army Points, baseline SWC,
recommended table size, Deployment Zone dimensions, and nominal duration.
The independent N5.3 Retreat! and advisory table-size sources remain on
pp. 146–147. Audit the same Army Points keys across both source tables:

```powershell
.venv\Scripts\python.exe -m tools.audit_game_mode_source_table
.venv\Scripts\python.exe -m tools.audit_game_mode_source_table --pdf data/pdf/rules/n5-rules-v5-3-en.pdf --json
```

The read-only manifest
`config/validation/game-mode-source-table.json` pins six exact rows:
Beginner (150 / 3 SWC / 40 min), Raid (200 / 4 / 50),
Intermediate (250 / 5 / 60), Standard (300 / 6 / 90),
Magnum and Games with Reinforcements (350 / 7 / 100),
and Large-Scale (400 / 8 / 120). Table sizes are 24×32,
32×48 or 48×48 inches; Deployment Zones are 8×24, 8×32
or 12×48 inches, respectively. The six table dimensions must
match the independently maintained p. 147 recommendations.
Source-review semantics preserve baseline SWC rather than conflating
profile-specific bonuses, and the indicated game duration is in
minutes, not a limit of Game Rounds.

The audit rejects changed values, schemas, sources, row order,
Army Points/SWC alignment, and divergence from the separate
Retreat!/table-size manifest. Optional local-PDF verification checks
the printed p. 6 headings and source words, uses positional cell
alignment for Army Points/SWC/minutes and the table/Deployment
dimensions, and reports its PDF SHA-256. The ignored PDF is not
required by CI. The reviewed `rule:game-modes` definition now publishes
these six rows at `/rules/game-modes` and `/api/rules/game-modes`, using
`facts.gameSetupTable.rows` as the structured normal-player source.
The audit compares **every published value** to both pinned manifests
and fails closed on changed data, source pages or advisory scope.
The browser uses the shared horizontally scrollable reference-table
primitive. Normal player search reaches the same record. Scenarios,
Army List legality, Unit attributes, and live session state remain
separate. `tests/test_game_mode_source_table.py` includes source,
publication and negative-drift coverage.

### Independent Retreat! and generic game-setup source tables

N5.3 prints a **Retreat! threshold table** on p. 146 and separate
**advisory table-size recommendations** on p. 147. The maintained
Trooper `state:retreat` (p. 170) and `term:victory-points` (p. 173)
do not themselves represent the army-wide threshold or generic table
layout. Review the read-only inventory with:

```powershell
.venv\Scripts\python.exe -m tools.audit_standard_game_reference_tables
.venv\Scripts\python.exe -m tools.audit_standard_game_reference_tables --pdf data/pdf/rules/n5-rules-v5-3-en.pdf --json
```

The audit pins six Army Points rows in
`config/validation/standard-game-reference-tables.json`: 150 → 38 VP,
200 → 50 VP, 250 → 63 VP, 300 → 75 VP, 350 → 88 VP,
400 → 100 VP. These are ceilings of one quarter of the game/list
points, checked against **current surviving Victory Points** at the
beginning of the active turn's Tactical Phase. This is an **army/session
condition**; it is not a static Unit/Profile attribute or a direct
synonym for the Trooper's `state:retreat`.

The adjacent generic table-size recommendations are 24×32 inches at
150 points, 32×48 at 200/250, and 48×48 at 300/350/400.
The source explicitly identifies table setup guidance as advisory, not
mandatory. These dimensions must not override authoritative
scenario-scoped geometry or deployment rules.

The source audit fails closed on changed row values, threshold
rounding, page provenance, scope, missing maintained Retreat!/VP
identities, or newly introduced canonical reference records requiring
review. With `--pdf`, it checks both pages in the locally pinned
English N5.3 PDF, including positional alignment of Army Points and
survivor thresholds across the printed two-column table. Without the
ignored PDF, the manifest and maintained-boundary checks remain
available in CI. It does not publish scenario data, infer surviving
Troopers from an Army loadout, evaluate game state, or add any deployed
object. `tests/test_standard_game_reference_tables.py` covers source
rows, rounding, negative drift and the optional PDF extraction.

### Terrain and Scenery Structures source gaps

The optional N5.3 terrain chapter (pp. 143–145) contains a separate source
table and two physical access labels outside the Weapon Chart and scenario
object inventories. Its suggested combinations are not new canonical terrain
Types or deployed Weapon/Equipment profiles. Audit the source boundary with:

```powershell
.venv\Scripts\python.exe -m tools.audit_terrain_scenery_source_gaps
.venv\Scripts\python.exe -m tools.audit_terrain_scenery_source_gaps --pdf data/pdf/rules/n5-rules-v5-3-en.pdf --json
```

The audit pins **five Terrain Types** (Aquatic, Desert, Mountain, Jungle,
Zero-G), **18 printed suggestion/example labels** (retaining the source's
`Artic Plains` spelling), and **two Scenery Access Width Tokens** (`Narrow
Gate` / `Wide Gate`). The `skill:terrain` reference exists;
standalone Special Terrain and Access Width reference definitions are
now **promoted** as N5.3 general rules. The subsequent maintained-text
review and coordinated binary refresh are complete (see below).
Gate Token labels do not have separate canonical definitions.
The audit accepts both the original two-gap state and the fully
published two-rule state but rejects partial migration or unsupported
definitions. Its optional `--pdf` mode verifies source headings, names and
Narrow Gate eligibility against the local English N5.3 source. Without
the ignored PDF, it still checks maintained and published domain boundaries;
it does not claim to have re-extracted the PDF.

Special Terrain zones are game-table/session configurations, with a Terrain
Type and at least one other characteristic (Difficult Terrain, Saturation
or Visibility Conditions). The table's 18 example rows illustrate possible
combinations, not 18 distinct terrain Types. Access Width is a scenery
restriction; the Narrow/Wide Gate Tokens label access points rather than
deployable devices, and the applicable Silhouette/Prone restrictions cannot
be inferred from an Army loadout. The audit fails on unexpected promotion
of these names into the 17-object Weapon/Equipment publication or new
maintained source identities requiring re-review. The source-gap
audit itself does not add attributes, source carriers or runtime records.
The semantics are already reviewed in `docs/rules-semantics.md` and
`docs/rules-research.md`. `tests/test_terrain_scenery_source_gaps.py`
guards the boundary, including a local-only test of the pinned PDF.

Two source-backed `basic-rule` definitions were promoted together with
their generated artifacts: `rule:special-terrain` (p. 143) and
`rule:access-width` (p. 145). They specify optional table scope, terrain
Types and characteristics, scenery Access Width precedence and the
Silhouette X/Prone restriction, without creating extra object identities.
The original one-time staging and promotion procedure was:

```powershell
.venv\Scripts\python.exe -m tools.stage_terrain_scenery_references --output-dir local/terrain-scenery-references-n53 --pdf data/pdf/rules/n5-rules-v5-3-en.pdf
```

The original staging and three-file promotion are complete. The first
post-promotion rules check revealed two missing interaction-review entries
and reviewed maintained-text aliases. Those reviews are now recorded:
the interaction checklist has **200/200 supporting identities**, Prone
State references use canonical links, and the ordinary Terrain noun is
pinned separately from the `skill:terrain` identity with exact
passage hashes. The rules build now passes.

The final two-binary refresh **was completed and verified** to pair the
post-promotion source corrections with a matching `rules.db` and
`deployed-objects.json` fingerprint. The following is the archived
reproduction procedure; it requires a new, unused output directory
if the original local staging directory still exists:

```powershell
& .\.venv\Scripts\python.exe -m tools.stage_promoted_terrain_artifacts --output-dir local/terrain-scenery-refresh-n53
```

The original `local/terrain-scenery-refresh-n53/staging-report.json`
matched the current curated-source SHA-256, and both promoted binary
files matched the staged SHA-256 fingerprints byte-for-byte. For future
rebuilds, verify the current source hash and both staged binary hashes
before copying them together:

```powershell
$stage = "local/terrain-scenery-refresh-n53"
$report = Get-Content (Join-Path $stage "staging-report.json") -Raw |
    ConvertFrom-Json
if ($report.scope -ne "post-promotion-binary-rebuild-not-applied" -or
    $report.reviewedObjects -ne 17 -or $report.stagedPaths.Count -ne 2) {
    throw "Unexpected terrain refresh report"
}
if ((Get-FileHash data/curated/rules/n5-core-v5.3.json -Algorithm SHA256).Hash -ne
    $report.sourceSha256) {
    throw "Curated source changed after staging"
}
$hashes = @(
    $report.stagedSha256.rulesDatabase,
    $report.stagedSha256.deployedObjects
)
for ($i = 0; $i -lt $report.stagedPaths.Count; $i++) {
    $path = $report.stagedPaths[$i]
    $candidate = Join-Path $stage $path
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf) -or
        (Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash -ne $hashes[$i]) {
        throw "Missing or changed staged binary: $path"
    }
}
foreach ($path in $report.stagedPaths) {
    Copy-Item -LiteralPath (Join-Path $stage $path) -Destination $path -Force
}
& .\.venv\Scripts\python.exe -m tools.build_deployed_object_publication --check
& .\.venv\Scripts\python.exe -m tools.run_checks --stage rules
```

The refreshed binary pair must be committed together with the curated
source and corresponding review policy/checklist changes. No deployment
has occurred. The regression
`tests/test_promoted_terrain_artifacts.py` checks that an isolated rebuild
does not modify tracked inputs and, when the ignored staging report is
present, verifies its source hash and exact binary equality against the
promoted files. The published `rules.db` fingerprint is checked even
without local staging artifacts.

### Core scenario-object source-domain boundary

The deployed Weapon/Equipment inventory must not absorb scenario objectives
simply because they are represented by physical Markers or scenery. The
read-only boundary audit checks the four **N5.3 core scenarios** (printed
pp. 149–156) against maintained scenario geometry, scoped rules and Skills,
scoring references, and the published deployed-object identities:

```powershell
.venv\Scripts\python.exe -m tools.audit_core_scenario_objects
.venv\Scripts\python.exe -m tools.audit_core_scenario_objects --json
```

Annihilation and Firefight have no scenario-object Marker instances.
Domination (pp. 151–152) places exactly **four Consoles** across all three
supported map configurations; the `Hack Consoles` Skill and `hacked`
scoring status are confined to that scenario. Supplies (pp. 153–154) places
**three Supply Boxes** in each configuration; the `Pick Up Supply Boxes`
Skill and `controlled` status are scenario scoped. Each scoring condition
must reference the exact physical Marker IDs present in every configuration.
The audit pins the maintained N5.3 citation pages for the scenario definitions,
placement rules and associated Skills, and rejects mismatched/duplicate
source references or accidental promotion of `Console` / `Supply Box`
to the Weapon/Equipment publication. The printed source pages were reviewed
against the pinned English N5.3 PDF; the audit itself does not read the PDF.
The existing scenario tests separately validate placement coordinates,
individual setup/scoring rules, and the unresolved Domination 350-point SWC
discrepancy. This cross-domain gate is not an exhaustive scenario or ITS
game-object inventory and must not create Army carriers or delivery paths.
`tests/test_core_scenario_object_boundary.py` exercises the fail-closed
publication and provenance boundary.

### N5.3 citation migration verification

The **14 independently verified N5.3 PDF citations** are now present in
maintained rules and the regenerated `rules.db`: six non-catalog, five
expanded, and three Weapon/Equipment source-domain citations. The review
manifests no longer carry temporary PDF-only status/excerpt fields. Verify
their coordinated post-migration state with:

```powershell
.venv\Scripts\python.exe -m tools.audit_deployed_object_citation_migrations
.venv\Scripts\python.exe -m tools.audit_deployed_object_citation_migrations --json --pdf data/pdf/rules/n5-rules-v5-3-en.pdf
```

The read-only preflight verifies all three manifests and all 14 exact
`sourceId: n5-core-v5.3-pdf` citations. It reports **0 pending / 14
migrated** and rejects partial, duplicate, or stale migrations. `--pdf`
also verifies source excerpts against the local English N5.3 PDF and
reports its SHA-256; this requires PyMuPDF. Normal CI validation does
not require the ignored PDF. The curated citations specify verified
pages without adding unverified section labels.

The migration was first built in an isolated staging directory, using
the following command **from the pre-migration checkout**. This command
requires the 14 citations to be pending and is not rerunnable from
the already migrated working tree:

```powershell
.venv\Scripts\python.exe -m tools.stage_deployed_object_citation_migration --output-dir local/citation-migration-n53 --pdf data/pdf/rules/n5-rules-v5-3-en.pdf
```

The exclusive staging directory contains a citation-only edit to the
maintained N5.3 curated JSON, the three reviewed manifests with only temporary
`citationStatus` and `pdfExcerpt` fields removed, a freshly built
`data/generated/rules.db`, the matching fingerprinted
`data/generated/deployed-objects.json`, and `migration-report.json`.
All 14 migrated records are validated through their post-migration
review contracts before staging, and the object publication must retain
17 reviewed identities. The source/manifest changes preserve existing
formatting. The stage command refuses to overwrite an existing directory,
write inside a source/generated input directory, or run on a partially
migrated checkout. It uses the existing pinned Army database but does not
rebuild it. Staging tests compare the original curated files, both tracked
generated artifacts and all three manifests byte-for-byte before/after.

The six staged files were subsequently promoted together. For an
independent replay from a pre-migration checkout, inspect the staging
report and copy all six paths in one review batch:

```powershell
$stage = "local/citation-migration-n53"
$paths = @(
    "data/curated/rules/n5-core-v5.3.json"
    "config/validation/deployed-object-non-catalog-reviews.json"
    "config/validation/deployed-object-expanded-reviews.json"
    "config/validation/deployed-object-source-domain-clause-reviews.json"
    "data/generated/rules.db"
    "data/generated/deployed-objects.json"
)
foreach ($path in $paths) {
    Copy-Item -LiteralPath (Join-Path $stage $path) -Destination $path
}
.venv\Scripts\python.exe -m tools.audit_deployed_object_citation_migrations --json
.venv\Scripts\python.exe -m tools.build_deployed_object_publication --check
```

The promoted `rules.db` and deployed-object publication were checked
against the staging report's exact SHA-256 fingerprints, and the focused
audit and publication regressions passed. The audit exception maps
remain as transition guards, but the maintained citations replace
their PDF-only manifest metadata. Never publish the curated text alone
without its matching `rules.db` and derived publication. The migration
adds no object identities, delivery edges, or Unit carriers.
`tests/test_deployed_object_citation_migrations.py` verifies pending and
migrated states, source drift, optional PDF excerpts, and (when the local
staging report exists) byte-for-byte equality of all six promoted files.

### Deployed-object release publication

The read-only inventory is for review; ordinary web requests must not read
the raw curated source files. In a development/release checkout, after
building both matching databases, compile the reviewed reference payload:

```powershell
.venv\Scripts\python.exe -m tools.build_deployed_object_publication
.venv\Scripts\python.exe -m tools.build_deployed_object_publication --check
```

The builder writes deterministic `data/generated/deployed-objects.json` with
the source and rules review evidence, direct Army profile/loadout occurrences,
source-wide Unit options, and explicit one-level included loadout occurrences
for reviewed delivery sources, along with the **exact** current
`infinity.db`/`rules.db` SHA-256 fingerprints. Changes to either database
require regenerating and revalidating the publication. The corresponding
`tests/test_deployed_object_publication.py` tests prove deterministic bytes
and rejection of corrupt, duplicate, stale or unsupported values. When
`data/generated/infinity.raw.db` is available alongside the published Army
database, two additional local-only tests compare every reviewed origin's
published direct and one-level Include reverse-use rows against independent
raw Weapon/Equipment occurrences and exact Include targets, including
source-wide Unit options without invented Army ownership. These comparisons
skip in clean CI without the ignored raw source database and must be repeated
against the final pinned release input pair. They do not validate unreviewed
delivery origins or objects. The hermetic
`tests/test_deployed_object_source_contexts.py` checks the known schema-level
Weapon/Equipment foreign-key contexts, distinguishes whole-Army catalogs and
reusable Weapon templates from Unit ownership, and guards all three source
Include selector shapes against drift. New source context types must be
reviewed rather than automatically promoted to reverse Unit uses.
`tests/test_verify_deployed_object_publication_browser.py` exercises the
real API and Chromium at 1440/390 px with an isolated, freshly generated
publication. There are 17 reviewed entries, not the entire game-object corpus;
Mine Dispenser's subtype remains unresolved. The reverse-usage projection
includes only exact source occurrences linked to reviewed delivery origins.
Unit-wide options retain an unknown Army context; one-level Include targets
retain their source parent and target payload without inventing membership.
`tests/test_deployed_object_transitive_includes.py` checks every contextual
Include root against current **reviewed** delivery-source IDs, recursively
resolving intermediate payloads only through a unique Army/Unit occurrence.
The pinned 2026-10-22 snapshot has no additional transitive matches, shared
same-context intermediate targets or cycles. The synthetic fixture verifies
that a future two-hop match, different Army/Unit occurrence, ambiguous
same-context payload and cycle are handled explicitly. This is a source-drift
gate, **not** a claim that other unreviewed delivery sources or missing objects
cannot have additional uses.

The release deployment command generates and verifies this ignored publication
from the checked-out pinned database pair before building the Docker image.
The Docker image must contain the publication beside both databases. The image
smoke test verifies the publication against the actual installed database
hashes, its 17 reviewed entries and unresolved delivery, and the HTTP/API
browser entry point. Deployment-smoke CI generates the same deterministic
artifact from the tracked sources before Docker build. Passing the isolated
browser test alone is not proof of hosted availability; final hosted acceptance
and the separate Unit/loadout reverse-usage work remain open.

For the older Wiki Weapon Chart name inventory, use the read-only
explicit-alias audit. It preserves repeated alternative tables and reports
unresolved identities independently from source-profile value differences.
The pinned Wiki and Army files are private, not committed:

```powershell
.venv\Scripts\python.exe -m tools.audit_wiki_weapon_chart_names --wiki-en "data/wiki/WIKI-en 20260926-200832.zip" --army-db data/generated/infinity.db --curated-rules data/curated/rules/n5-core-v5.3.json --json-output local/audits/wiki-weapon-names.json --markdown-output local/audits/wiki-weapon-names.md
```

A name alias is not a new Weapon rule or corrected Weapon Chart profile.
Different-valued alternative rows remain separately reviewable.

To reconcile unresolved Weapon rule enrichment without inventing definitions,
combine the existing enrichment and chart reports in a separate deterministic
source-to-reference triage:

```powershell
.venv\Scripts\python.exe tools/audit_enrichment_coverage.py data/generated/infinity.db --rules data/generated/rules.db --output local/audits/weapon-enrichment.json
.venv\Scripts\python.exe tools/audit_weapon_definition_gaps.py --army-db data/generated/infinity.db --enrichment local/audits/weapon-enrichment.json --chart local/audits/weapon-chart.json --json-output local/audits/weapon-triage.json --markdown-output local/audits/weapon-triage.md
```

**Current-input regression (2026-10-31):** the triage now retains historical
shared-effect approvals for Weapons that subsequently acquired their own published
family definitions. A resolved review still requires its original profile hash,
source identity and canonical Weapon link to match; a missing unresolved row alone
is insufficient. The unfiltered October 31 source reports now reconcile **62**
active shared-effect reviews and **2** superseded approvals (Crazykoala and
Madtraps); Flash Pulse remains a separately accepted historical citation. The
output includes `resolvedSharedReviews` and `resolvedSharedReviewCount` so those
two approvals remain auditable without counting them as missing definitions. This
is triage evidence, not whole-Weapon or v1.0 completeness acceptance. The original
finding and reproduction remain documented in
[V1-A05](v1.0-source-coverage-audit.md#v1-a05--weapon-gap-triage-aborts-on-completed-definitions).

For the opt-in **1.0 enrichment source-triage assessment**, add
`--assess-release 1.0.0` to the triage command. It cross-checks the same pinned
Army/rules fingerprints and current enrichment gap identities with the source-
reviewed Weapon results, preserving the historical policy's blocker count only as
historical context. `releaseAssessment.pending` lists all remaining unreviewed
catalog/link gaps; source-reviewed shared Weapon omissions and explicitly accepted
historical citations do not become missing definitions. For a nonzero exit until
this bounded assessment has no pending gaps, use `--require-release 1.0.0` instead.
The October 31 source pair reports **one pending Skill (Commlink)** despite zero
historical-policy blockers. The strict gate therefore intentionally exits 1. This
assessment does not replace the separate 1.0 primary-interaction gate, annex
source-applicability review, whole-source explanation review, or browser acceptance.

The triage rejects mismatched Army database hashes, incomplete/deferred chart
alignment, and invalid coverage or PDF report identities. It reports separate
cases for chart-listed Weapons without a standalone curated definition, stale
citations, ambiguous mappings, and identities not located on the PDF chart.
Batches use the Army source category and catalog use count and contain at most
eight Weapon identities. Explicitly reviewed historical-comparison citations
are shown separately from unresolved stale citations; this does not decide
any remaining cross-publication rules conflict. Shared and specific Weapon
rules linked through a unique, acyclic `uses-effects-of` hierarchy are
intentional layering, not ambiguous family mappings. Unrelated overlapping
definitions and cycles still fail the mapping audit. A chart identity does
**not** verify rules prose, typed relationships, exact profile modes or usable
browser presentation. SymbioBomb has its own N5.3 Weaponry prose on p. 74,
not an independent chart profile; its curated reference describes use without
inventing one. Generated reports and third-party source inputs remain
local and Git-ignored.

## 1.0 Weapon Traits and special-weapon source inventory

`tools/audit_weapon_traits_prose.py` uses the same optional N5 v5.3 PDF and
generated Army database, plus `rules.db`, to compare positionally reconstructed
Traits against raw Army `metadata_weapons.properties`. The offline check keeps
printed wording, mode identities, source page, and Army properties in each report.
It also indexes 12 named special-weapon prose sections on pp. 68–74 against
named curated Weapon definitions, without treating a missing dedicated Weapon
record as proof that no gameplay rule representation exists.

```powershell
python tools/audit_weapon_traits_prose.py --core-pdf "C:\path\to\n5-rules-v5-3-en.pdf" --json-output docs/audits/weapon-traits.json --markdown-output docs/audits/weapon-traits.md
```

The supplied N5 v5.3 PDF yields 145 literal Trait-list matches, 15 reviewed
notation equivalents, two manually checked source-cell matches, and nine remaining
membership/classification candidates across all 171 chart rows (zero deferrals).
`config/validation/weapon-trait-source-review.json` maintains the narrow spelling,
State-notation, and compound footnote equivalences separately from gameplay data.
The two verified source cells are keyed by printed name/page and can only be reused
with the exact pinned core PDF hash. Review policy changes are recorded in the
reproducible evidence report. These candidates are **not confirmed source-data defects**: spelling and
shorthand differences, omitted/extra printed Traits, and extraction limitations
require separate review. The report does not compare prose clauses, rule
relationships, or player-facing completeness. The PDF remains an optional
offline dependency only; normal tests and CI require no PDF or PyMuPDF.

## 1.0 General Rules (REA-026) browser acceptance

**Verified 2026-10-13:** Windows, headless Chrome 155, branch dev/v1.0.0
at commit 2996fefb46fc. A temporary rules database was freshly rebuilt from
curated sources beside a copy of the tracked Army database; the live Git
working tree and tracked generated databases were not modified.

The five reference pages (Face to Face Rolls, Saving Rolls, Guts Roll, Order
Expenditure Sequence, Coordinated Orders) loaded at **1440, 390 and 320 px**
(15 browser/viewport cases). All rendered source-cited rules and semantic links
with zero horizontal overflow, JavaScript exceptions or browser-console errors.
Full-page 320-pixel Guts Roll and Coordinated Orders screenshots were visually
inspected for readable sections, links and source citations.

Five rule-to-reference navigation clicks passed, along with seven reverse links
from BS Attack, Courage, Move, Doctor, MediKit and Hacker. Enter-key navigation
to Dodge passed. Mobile touch emulation verified two taps: the first reveals
the linked rule preview and the second follows the link.

One combined-harness run intermittently remained on the loading state when
opening a second mobile browser context. Five subsequent fresh mobile touch
contexts each fetched the rule API (HTTP 200) and fully rendered the same page,
without page errors or failed requests. The isolated stall was not reproduced
or attributed to a confirmed application defect; investigate if it recurs.

This certifies **only REA-026's bounded reference/browser scope**. It does not
certify the cross-surface browser acceptance now tracked for 1.0,
exhaustive theme or distance preferences, every interaction exception,
or hosted deployment.
Playwright and locally installed Chrome were used only for this optional
acceptance exercise; normal CI does not require a browser.

## 1.0 SymbioBomb bounded browser acceptance

**Verified 2026-10-13, branch `dev/v1.0.0`, base commit `f9d06ef`.**
Headless browser acceptance used an isolated local application instance with
the current Army and rules database snapshots. It did not connect to the
public deployment or modify tracked source data.

The SymbioBomb Weapon page rendered at **1440, 390 and 320 px** with the
source-backed explanation, Pheroware Tactics links, printed N5.3 p. 74 and
archived English Wiki citations. No horizontal overflow or JavaScript/console
errors were observed. Desktop and 320 px full-page screenshots were visually
inspected for legible paragraphs and working citations. Neither the browser
nor the API added an invented SymbioBomb attack profile.

Desktop mouse click and keyboard Enter followed the Pheroware link to
`/weapons/pt`. Mobile touch emulation retained the current two-tap behavior:
the first tap displayed the reference preview while staying on the SymbioBomb
page, and the second navigated to Pheroware. All evidence and screenshots are
under ignored `local/audits/symbiobomb-browser/`.

This certifies only this bounded page, layout, and navigation behavior. It
does not simulate deployment assignment or grant 1.0-wide browser acceptance.

**D-Charges / Disco Baller render smoke (2026-10-13):** The two new
source-backed Weapon cards loaded at 1440, 390 and 320 px (six cases)
with their N5.3 and archived Wiki citations, expected mode/profile sections
and maintained reference links. No horizontal overflow or browser errors
were observed. The 320 px screenshots were visually reviewed and stored in
ignored `local/audits/weapon-first-batch-browser/`. This verifies the current
rendering and link presence; individual cross-page click/touch routes and
additional modes still require focused browser acceptance.

**First Weapon batch follow-up (2026-10-13):** All six remaining
Uncategorized Weapon references and the source-only Activate Disco Ball Skill
rendered at 1440, 390 and 320 px (21 page/viewport cases), with expected
source citations, rules and Army mode/profile separation, no horizontal
overflow and no JavaScript errors. The Disco Baller inline link to
Activate Disco Ball passed both desktop click and touch preview-then-navigation
(two additional cases). Full-page 320 px Missile Launcher and Activate Disco
Ball screenshots were visually inspected. Evidence remains in ignored
`local/audits/weapon-first-batch-2-browser/`. These checks are bounded
reference/browser acceptance, not a complete release gate.

## 1.0 Grenade shared-effects browser acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** Smoke Grenades,
standard Grenades, E/M Grenades and Eclipse Grenades matched the
N5.3 p. 178 chart at 1440, 390 and 320 px (12 page/viewport
checks), preserving their individual range MODs, PS, Burst,
Saving Rolls and published Traits. Smoke/Eclipse use distinct
visibility-zone Ammunition records with no Saving Rolls;
E/M retains two BTS/2 Saving Rolls and standard Grenades one
ARM Saving Roll. All four use the shared BS Weapon (PH),
Speculative Attack and circular Impact Template rules without
duplicating mechanics in new Weapon records. Source footnotes
`[**]` remain visible as original source notation.

The shared Ammunition renderer was also verified to display
canonical inline references (including Smoke's Zero Visibility
Zone and Eclipse's Reflective/MSV relationships) as real links
rather than raw `[[...]]` tokens. Desktop Eclipse-to-Reflective
navigation and mobile Smoke Ammunition preview-first, second-tap
navigation passed (**14/14 checks**). All four 320 px screenshots
were inspected; no horizontal overflow or JavaScript errors
were observed. Source-profile-pinned reviews remain in
`data/curated/weapon-shared-effect-reviews.json`; private evidence
remains Git-ignored under
`local/audits/grenades-shared-review-browser/`. These checks
validate references and rendering, not simulated attack outcomes.

## 1.0 Spitfire shared-effects browser acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** Spitfire, AP Spitfire
and MULTI Spitfire were checked at 1440, 390 and 320 px (nine page
cases), preserving the N5.3 p. 185 PS, Burst, Ammunition, Saving Roll
Attributes/counts, ranges and Traits. The first two rely on their
canonical Normal/AP ammunition and Suppressive Fire references,
without duplicate Weapon-specific rules text. MULTI Spitfire retains
the Army's `Anti-Material Mode` label and the different DA B1/two
ARM Saving Rolls, AP B4/ARM/2, and Shock B4/ARM modes. Its source-cited
card explicitly reconciles the chart's `Anti-Materiel Mode` spelling
without rewriting Army profile data.

Desktop navigation to Anti-materiel and mobile DA first-tap preview,
second-tap navigation passed (**11/11 checks**). All three full-page
320 px screenshots were inspected; there was no horizontal overflow
or JavaScript error. Source-profile-pinned shared-only reviews remain
in `data/curated/weapon-shared-effect-reviews.json`; private evidence
remains Git-ignored under `local/audits/spitfire-browser/`. These are
bounded reference checks, not an automated attack-resolution ruling.

## 1.0 Sniper Rifle source-specific browser acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** MULTI, K1, VIRAL and Plasma Sniper
Rifles were checked at 1440, 390 and 320 px (12 page cases), preserving
N5.3 p. 185 firing modes, PS/Burst, Ammunition, Saving Rolls, Traits and
range MODs. MULTI retains three separate DA/AP/Shock modes, K1 retains N
Ammunition with ARM=0, and Viral retains the conditional BioWeapon
VITA/STR distinction. Plasma Blast and Hit have separate PS and Template
conditions, one ARM plus one BTS Saving Roll, and the existing
source-pinned additional ARM roll on a Critical (N5.3 p. 67); this is not
combined Ammunition.

Desktop BioWeapon navigation and mobile MULTI DA first-tap preview and
second-tap navigation passed (**14/14 checks**). All four full-page
320 px screenshots were inspected; no horizontal overflow or JavaScript
errors were observed. Private evidence is Git-ignored under
`local/audits/sniper-rifles-browser/`. These checks validate reference
presentation, not automatic attack resolution.

## 1.0 Disposable Support Weapon browser acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** Panzerfaust, Blitzen,
Flammenspeer and Akrylat-Kanone matched the N5.3 p. 178 chart at
1440, 390 and 320 px (12 viewport cases). Panzerfaust retains
AP+EXP/ARM/2 with three Saving Rolls; Blitzen E/M and its [**]
Ammunition footnote, Akrylat-Kanone PARA/PH-6 and IMM-A source
notation. These three use canonical Ammunition and Trait rules
without additional Weapon cards. Flammenspeer has separate Blast
(N, ARM, circular Impact Template) and Hit (AP, ARM/2, no Template)
modes, each with Continuous Damage and Disposable (2).

Desktop Flammenspeer navigation to Impact Template and mobile
Panzerfaust EXP first-tap preview/second-tap navigation passed
(**14/14 browser checks**). The 320 px Flammenspeer and Panzerfaust
screenshots were inspected; no horizontal overflow or JavaScript
errors were observed. Reviewed source-profile fingerprints remain
in `data/curated/weapon-shared-effect-reviews.json`; evidence and
screenshots remain Git-ignored under
`local/audits/disposable-support-browser/`. This is bounded browser
and source-profile acceptance, not automatic combination or
Immunity resolution.

## 1.0 Heavy Machine Gun shared-effects acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** Heavy Machine Gun,
AP Heavy Machine Gun and MULTI Heavy Machine Gun matched the N5.3 p. 179
profiles at 1440, 390 and 320 px (nine cases), including source Ammo,
Saving Roll Attributes/counts, Burst, PS, Range MODs and Traits. The first
two displayed canonical Normal/AP explanations without standalone Weapon
cards. MULTI HMG displayed its three separate mode-specific profiles
and a new source-cited rules card; Anti-materiel EXP stays Burst 1,
three ARM Rolls, while AP and Shock retain Burst 4 and Suppressive Fire.

Desktop navigation to Anti-materiel and mobile EXP link first-tap preview,
second-tap navigation passed (**11/11 browser checks**). The 320 px
screenshots were inspected; no horizontal overflow or JavaScript errors
were observed. Source-profile-pinned shared-only reviews remain in
`data/curated/weapon-shared-effect-reviews.json`. Private evidence is
Git-ignored under `local/audits/hmg-shared-review-browser/`.
This does not claim automatic immunity resolution or 1.0-wide acceptance.

## 1.0 additional Uncategorized Weapon shared-effects acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** Eight N5.3 pp. 186–188 Weapon
references (E/Marat, Mk12, Zapper, Contender, Feuerbach, Crazykoala,
Madtraps, Hyper-Rapid Magnetic Cannon) were checked at 1440, 390 and
320 px (24 page/viewport cases). All source profiles retained their
published modes, ammunition, Saving Rolls and Traits. Feuerbach and
Hyper-Rapid Magnetic Cannon include new, mode-specific curated cards;
the six other identities reuse shared ammunition and Trait definitions.
Crazykoala and Madtraps link to Boost/Perimeter without inheriting
WildParrot or Mines behavior.

Desktop navigation from Crazykoala to Boost and mobile Feuerbach AP+DA
Ammunition preview-first/second-tap navigation both passed (**26/26**).
The 320 px Feuerbach, cannon, Crazykoala and Madtraps screenshots were
inspected; no horizontal overflow or JavaScript errors were observed.
Source-pinned shared-only reviews remain in
`data/curated/weapon-shared-effect-reviews.json`, and private browser
evidence is under ignored `local/audits/uncategorized3-browser/`.
The checks are bounded reference acceptance, not an effects engine
or a claim of release-wide Weapon completeness.

## 1.0 Submachine Gun shared-effects acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** Both N5.3 p. 185 profiles
were tested at 1440, 390 and 320 px (six cases), preserving PS 7,
Burst 3, identical Range MODs and Suppressive Fire while distinguishing
Normal/ARM from AP/ARM/2. Each profile displayed its canonical
Ammunition explanation and citations without adding a duplicate Weapon
rule. Desktop navigation to Suppressive Fire and mobile AP Ammunition
preview-first, second-tap navigation passed (**8/8 checks**). The 320 px
screenshots were inspected; no horizontal overflow or JavaScript errors
were observed. Profile-pinned decisions remain in
`data/curated/weapon-shared-effect-reviews.json`; private browser evidence
is Git-ignored under `local/audits/submachine-shared-review-browser/`.

This is bounded source/profile and browser acceptance, not a claim of
release-wide Weapon completeness or computed combined effects.

## 1.0 Shotgun shared-effects acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** The five N5.3 p. 184 Shotgun
profiles (Boarding, Light, Vulkan, Heavy, T2 Boarding) were checked at 1440,
390, and 320 px (15 viewport cases), preserving the printed ammunition,
Saving Roll Attributes, PS, Burst, range bands, and Traits. Each profile
displayed linked canonical ammunition text and citations; no standalone
Weapon rule or Direct Template was invented. The Vulkan source spelling
`Continous Damage` resolved to the visible canonical Continuous Damage
Trait, while T2 Boarding kept its separate Anti-materiel link.

Desktop navigation from Vulkan to Continuous Damage passed; mobile Boarding
Shotgun's AP link showed the preview on the first tap and navigated on the
second (**17/17 checks**). Full-page Vulkan and T2 Boarding screenshots at
320 px were inspected; no horizontal overflow or JavaScript errors were
observed. Source-profile-pinned reviews are maintained in
`data/curated/weapon-shared-effect-reviews.json`; browser evidence and
screenshots remain Git-ignored under `local/audits/shotgun-shared-review-browser/`.
This is bounded reference acceptance, not a claim that all Weapon behavior
or 1.0 release gates are complete.

## 1.0 Rifle shared-effects acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** Eight N5.3 p. 183 Rifle profiles
were checked at 1440, 390 and 320 px (24 cases). Combi Rifle, Rifle,
Adhesive Launcher Rifle, Breaker Combi Rifle, AP Rifle and T2 Rifle
rendered only the source profile, reviewed shared ammunition text, and
linked Traits; no standalone Weapon rule was invented. MULTI Rifle
retained three separate modes with their different Burst, ammunition,
Saving Rolls and Traits. K1 Combi Rifle retained N with ARM=0 and its
dedicated source-backed explanation. No horizontal overflow or JavaScript
errors were observed.

Desktop navigation from K1 to Anti-materiel passed. Mobile MULTI Rifle
shared DA followed the standard preview-first, second-tap navigation
contract after the shared-effects renderer was changed to use maintained
reference links (**26/26 accepted**). The 320 px MULTI, K1 and Adhesive
Launcher full-page screenshots were inspected. Private evidence is under
ignored `local/audits/rifle-shared-review-browser/`.

This covers these reference profiles and link behaviors, not derived
Immunity rulings, future weapon changes, or 1.0 release-wide acceptance.

## 1.0 reusable Ammunition effects pilot

**Verified 2026-10-14.** Five Weapon references (AP CC Weapon,
AP Heavy Pistol, Breaker Pistol, AP Rifle, and Silenced Pistol) were checked
at 1440 and 320 px, plus AP Rifle navigation to the canonical AP reference
(**11/11 browser checks**). The new expandable profile area reused the same
canonical AP summary/citations in four different Weapon identities, displayed
AP and Shock separately for the combined Silenced Pistol profile, and
preserved distinct ARM/2 and BTS/2 Saving Rolls. The AP Rifle required no
standalone curated Weapon rule. No horizontal overflow or JavaScript errors
were observed. Screenshots, API results and local audit work remain in
ignored `local/audits/shared-ammunition-pilot/`.

This verifies display-only component reuse, not automatic Combined
Ammunition adjudication, immunity handling, or completion of Weapon-specific
mode/exception audits. The v2 Weapon gap report retains all source-review
candidates pending and distinguishes reusable links from special source
relationships.

## 1.0 Pistol Weapon batch browser acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** Eight Pistol-family Weapon pages
rendered at 1440, 390 and 320 px (24 cases), with source-cited N5.3
p. 182 profiles, linked rules and no horizontal overflow or JavaScript/
console errors. Boarding Blast/Hit and MULTI's three modes stayed
distinct; Silenced displayed the printed AP+Shock/BTS/2 profile and the
conditional Silent (-6) Trait.

Desktop navigation from Silenced Pistol to Silent (X) passed. Touch
navigation from MULTI Pistol to DA passed with reference preview on the
first tap and navigation on the second (two more cases: **26/26**).
Full-page 320 px screenshots of Boarding, Silenced and MULTI were
visually inspected. The evidence remains Git-ignored under
`local/audits/pistol-browser/`. No Army statistics or modes were
rewritten. This certifies only these reference pages and interactions,
not the full 1.0 release.

## 1.0 CC Weapon batch browser acceptance

**Verified 2026-10-14, branch `dev/v1.0.0`.** All eight common
CC Weapon reference pages were tested at 1440, 390 and 320 px
(24 viewport cases). The published content included the source-cited
N5.3 p. 177 explanations and the unchanged Army chart profiles. All
cases had no horizontal overflow or observed JavaScript/console errors.

Viral CC Weapon's BioWeapon link navigated to the Trait by mouse;
a mobile first tap of DA opened the reference preview and the second
navigated to its Ammunition page (two additional checks, **26/26**).
Full-page 320 px screenshots of EXP and Viral were visually inspected.
The Viral card keeps the printed N/BTS/one-save baseline separate from
the explicitly derived VITA/STR-dependent BioWeapon interpretation.
No implicit immunity interactions were validated.

Evidence and screenshots are stored under ignored
`local/audits/cc-weapons-browser/`, not committed to public docs.
This is bounded reference/browser acceptance, not a release-wide check.

## 1.0 Peripheral (REA-017) browser acceptance

**Verified 2026-10-13, branch dev/v1.0.0, base commit 5fc94553b992,
Windows, headless Chrome 155.** The browser served the application code
from an isolated Git worktree, the existing Army database, and a temporary
rules database rebuilt from the updated curated content; tracked runtime
artifacts and the active Git checkout were not modified.

Eight pages were exercised at **1440, 390 and 320 px** (24 cases): the
Peripheral Skill, all five Peripheral subtype General Rules, Cyberplug and
Disconnected State. All displayed the reference content, citations and
semantic links without horizontal overflow or JavaScript errors. The
320-pixel Peripheral, Control and Cyberplug screenshots were inspected;
Cyberplug prose was simplified after the first screenshot to avoid repeated
inline links, and the full browser grid was rerun after that revision.

Six navigation paths passed between Doctor, Engineer, Disconnected, the
Peripheral Skill and the related subtype references. Focusing a reference
and pressing Enter opened its destination. On emulated touch, the first
tap revealed the inline preview and the second navigated, as intended.

This is **REA-017's bounded reference/browser acceptance**, not general
release acceptance or certification of every peripheral gameplay scenario.
The N5.3 pp. 106-108 behavior is represented as linked explanations; Army
Peripheral relationships and execution/evaluation logic were not changed.

## 1.0 Hacking baseline REA-018 browser acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** The six published Hacking Area,
Firewall, Supportware, Repeater, Fairy Dust and Enhanced Reaction
references were reviewed against the English N5.3 rules (pp. 55–56, 60)
and FAQ v0.1 (Firewall from a disabled Hacking Device). Chromium
acceptance passed **18/18 route/viewport checks** at 1440, 390 and
320 px, with no horizontal overflow or JavaScript errors.

The rendered cards preserve enemy-Repeater Hacker-only targeting and
Idle on failed Requirements, 8-inch reactive Hacking Area measurements,
a single chosen Firewall with fixed +3 Saving Roll protection, the FAQ's
disabled-Device exception, and complete Fairy Dust cancellation when
Enhanced Reaction is assigned to one protected REM. The 320 px Hacking
Area, Firewall and Supportware screenshots were visually inspected.

Source values and program mechanics were unchanged: this closed an
outdated audit verification task, not an additional rules implementation.
The source-based API regression assertions remain in
`tests/test_rules_database.py`; ignored local browser evidence is
stored under `local/audits/rea018-browser/`. Related cross-source
scope and Program-specific cases remain independent 1.0 audit work.

## 1.0 Negative Feedback REA-019 browser acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** The shared Negative Feedback
Label, Cybermask and White Noise references were checked against official
English N5.3 pp. 59, 61, 76 and 174 for same-Trooper NFB cancellation
and each Program's separate duration. Chromium acceptance passed **15/15
render/navigation checks** at 1440, 390 and 320 px; there were no
JavaScript errors or page-level horizontal overflow.

The Label states that a newly activated NFB effect overrides other active
NFB effects on **the same Trooper** until cancellation/deactivation,
without affecting allies. Cybermask restricts its Hacker while that
Hacker remains in IMP-2; White Noise restricts its creating Hacker
while its Template persists until the start of the States Phase.
The Label's actual Used by links navigate to both Hacking Program pages
at all three tested widths. All three 320 px screenshots were inspected.

Source/curated data and runtime gameplay behavior were unchanged:
REA-019 was already implemented and has now passed browser acceptance.
The existing rules regression plus the extended API Used by contract
are under `tests/test_rules_database.py` and `tests/test_web.py`.
Private screenshots, source extracts and browser results are Git-ignored
under `local/audits/rea019-browser/` and `local/audits/`.
This is bounded reference acceptance, not generalized NFB interaction
simulation.

## 1.0 Special Dice REA-021 browser acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** The public Special Dice General
Rule, Fireteam Level bonus table, Martial Arts, Berserk, BS Attack,
Disposable, MediKit, GizmoKit and Discover references were checked
against English N5.3 pp. 75, 86, 100 and 136 plus FAQ v0.1 p. 3.
Chromium acceptance passed **39/39 route and navigation checks** at
1440, 390 and 320 px, with no JavaScript errors or page-level overflow.

Special Dice add a rolled-and-discarded die, not Burst or a Disposable
charge. The Fireteam Level 2 bonus table directly links its +1 SD
notation to the shared explanation. The examples preserve dice
allocation to one target, Active Player first discard, +1 SD during
both turns, Martial Arts Levels 3/5, Berserk's explicit Long Skill
exception, and Fireteam Level 4's PH/WIP attribute distinction from
Discover. Screenshots of the 320 px Fireteams and Special Dice pages
were inspected.

Private evidence is under `local/audits/rea021-browser/` and
`local/audits/rea021-source-scan-2026-10-14.txt`. The unresolved
Spanish Fireteam maximum-dice wording conflict remains independently
tracked under REA-041. No general dice or Burst evaluator was added.

## 1.0 Recovery Kits and Disposable REA-022 browser acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** Source facts and player-facing
reference cards were checked against official N5.3 pp. 75, 123-124,
175 and 182. The browser suite covers MediKit, GizmoKit, Disposable (X),
Double Shot, Special Dice and Remote Presence at 1440, 390 and 320 px,
including actual links to their shared rule owners. Chromium acceptance
passed **30/30 checks**, with no JavaScript errors or horizontal overflow.
The 320 px MediKit, Disposable and Double Shot screenshots were inspected.

Both recovery Kits use the target's own PH Roll after a successful remote
BS Attack hit (or contact use). In one Order, any successful target PH
Roll among multiple hits gives one ordinary Wound recovery, even if
another PH Roll fails; multiple successes do not restore additional
Wounds. Remote Presence's GizmoKit exception removes enough Wounds to
cancel either level of Unconscious. Disposable B1 with a +1B modifier
spends two charges to fire B2 if available, while +1 SD adds a die to
roll and discard without spending another charge. Double Shot requires
both remaining Disposable (2) uses for its +1B benefit.

The rules regression covers these examples with source page citations
in `tests/test_rules_database.py`. Private browser images, results and
source extracts remain in `local/audits/rea022-browser/` and other
ignored `local/audits/` files. This is a reviewed reference baseline;
it does not add a general dice or recovery outcome evaluator.

## 1.0 REA-023 placement geometry browser acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** Canonical Place Deployable,
Perimeter, Minelayer, Deployable and Indiscriminate rules, plus
FastPanda, Deployable Repeater, WildParrot and Armed Turret, were
cross-checked against the official English N5.3 pp. 70, 74, 82, 102,
175 and FAQ v0.1 pp. 2-3. Chromium accepted **39/39** page and rule-link
checks at 1440, 390 and 320 px, with no horizontal overflow or page errors.
The 320 px Place Deployable, Perimeter and Armed Turret screenshots
were visually inspected.

These references now distinguish normal Active/Reactive placement contact,
Perimeter's passable path within ZoC, Minelayer's separate Trigger Area
and ZoC enemy exclusions, the timing and displacement of placement
at Conclusion, and direct removal/non-triggering of a Deployable.
Armed Turret still retains its independently tracked S1/S2 and
E/Mitter official-source conflicts: placement clarification does not
choose their precedence. The existing Mines and Drop Bears exception
cards remain separate source owners.

Focused tests live in `tests/test_rules_database.py`. Private source
excerpts, rendered screenshots and browser results remain ignored under
`local/audits/` and `local/audits/rea023-browser/`.
No runtime geometry simulation or generic rule evaluator was added.

## 1.0 REA-024 BioWeapon and Viral Mine acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** The BioWeapon Trait, shared
Viral Weapon Property, Mines reference, Viral Mine, Viral CC Weapon and
VIRAL Sniper Rifle were checked against English N5.3 pp. 63-65, 118,
174, 181 and 185, plus the pinned Army weapon profiles. The published
Viral Mine source remains N/BTS/one Saving Roll; the Trait conditionally
adds DA+Shock only against VITA, with the combined two-roll result
clearly identified as derived rather than a rewritten source field.
Shock still needs VITA 1 and a failed Saving Roll to bypass Unconscious.
The independent Vulnerability (Viral) rule remains name-scoped, and
other Immunity combinations are not certified by these examples.

Chromium browser acceptance passed **33/33** render/navigation checks
across eight rule/weapon pages at 1440, 390 and 320 px, including actual
BioWeapon-to-DA/Shock/Viral Property links and no JavaScript errors.
The BioWeapon, Viral Mine and Normal Ammunition 320 px screenshots were
visually inspected.

**Independent existing UI issue:** At exactly 320 px, the shared
"Rules reference" breadcrumb badge extends about 6 px beyond the
viewport on Normal, DA and Shock Ammunition detail pages. Five render
or navigation occurrences were recorded in this acceptance run; it
is not introduced by BioWeapon and is tracked under the final UI
acceptance checklist. Those cases were explicitly allowed only as
known layout exceptions, not asserted to be free of horizontal overflow.
At 390 px the affected page had no overflow. The screenshot and DOM
diagnostic remain under `local/audits/rea024-browser/`.

The regression contracts in `tests/test_rules_database.py` and
`tests/test_weapon_properties.py` protect source page citations, the
VITA/STR condition, the DA/Shock components, and Viral Mine's exact
N/BTS/one-roll property mapping. No general ammunition-combination
or Immunity evaluator was added. Private source extracts and browser
results stay under `local/audits/`.

## 1.0 REA-020 Fireteam ownership and integrity acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** The shared Fireteam quick
reference and related FT Master, Number 2, NCO, Tactical Awareness and
Suppressive Fire cards were compared against official English N5.3
pp. 93, 104-105, 107 and 132-136, including the already published
Ancillary subtype and relevant FAQ evidence.

Chromium accepted **33/33** route and link-navigation checks at 1440,
390 and 320 px, with no JavaScript errors or page-level horizontal
overflow. The 320 px Fireteam quick-reference screenshot was inspected;
its formation badges, action ownership, cancellation/departure distinctions,
rejoining timing and linked exceptions render without clipping.

The rules regression in `tests/test_rules_database.py` distinguishes
Leader-only attacks from Movement/Reset, independent reactive Rolls
versus the team ARO, per-member departure versus full cancellation,
two-or-more-member survival, States Phase rejoining, and NCO/Tactical
Awareness/FT Master/Number 2 exceptions. The canonical rules database
build includes a passage-specific reviewed-plain fingerprint for
**States Phase**: that turn-phase term must not link to the unrelated
weapon Trait named `State`.

Private source extracts, screenshots and browser report are retained
under `local/audits/rea020-browser/` and `local/audits/`.
This is source and reference-card acceptance; the separate Fireteam
Army selection, Wildcard and keyboard/touch workflow remains in
the final 1.0 acceptance checklist.

## 1.0 REA-027 Flash Pulse source-conflict acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** The current published Flash
Pulse reference and its Immunity (BTS), Stun Ammunition, Stunned and
Non-Lethal links were compared against the exact official English
N5.3 PDF (pp. 95-96, 186), Spanish N5.3 PDF (pp. 99, 196) and
the pinned Army snapshot weapon 72. All these current authoritative
weapon profiles agree on STUN, **one BTS/PB Saving Roll** and separate
Non-Lethal and State: Stunned Traits. Against Immunity (BTS/PB),
STUN becomes Normal without switching to ARM, and only a failed
Saving Roll causes Stunned; Non-Lethal prevents Wounds.

Live and exact-revision Spanish Wiki requests made on 2026-10-14
confirmed that Weapon Chart revision 3987 **and** alternative chart
revision 3988 still list two PB rolls without State: Stunned.
Spanish Immunity revision 3677 separately retains the failed-save
Stunned result. The exact historical alternative chart revision
3988 was independently verified in S21's Wiki history archive
(timestamp 2026-08-27T14:21:00Z; SHA-256 recorded in the
[source manifest](rules-explanation-audit-1.0-sources.md)).
This remains an **unresolved external publication conflict**, not
authority to modify the source Army profile.
The weapon's source notes/citations expose the disagreement.

Chromium browser acceptance passed **24/24** page and real
link-navigation checks at 1440, 390 and 320 px with zero JavaScript
errors. The Flash Pulse, Immunity and Stun pages were visually inspected
at 320 px. There were **two recorded occurrences** of the already
tracked narrow "Rules reference" breadcrumb overflow (roughly 6 px)
on the Stun Ammunition page, one direct render and one navigation.
These exceptions are explicit; the weapon and Immunity pages had no
page-level horizontal overflow.

Regression contracts in `tests/test_rules_database.py` and
`tests/test_weaponry_catalog_api.py` preserve the sourced one-roll
profile, failed-save-only Stunned result, exact Wiki citation revisions
and Army weapon identity. Private PDF excerpts, HTTP evidence,
browser images and results are Git-ignored under `local/audits/`
and `local/audits/rea027-browser/`. No game mechanics, imported
weapon profiles, or general Immunity algorithm were changed.

## 1.0 REA-028 Kobra Pistol source-conflict acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** The Kobra Pistol shared
and CC-only references were checked against English N5.3 pp. 64,
68 and 182; Spanish N5.3 pp. 68 and 191; pinned Army weapon 221;
the official N5.3 update notice; N5.2's older Shock/N profiles;
and archived English Wiki Mixed Weapons revisions 4021, 4077,
4082 plus Weapon Chart 4083.

Both N5.3 PDFs list DA/ARM/**one** Saving Roll in Kobra CC Mode,
but the DA rule requires **two**, or three for a Critical. Army and
the reviewed Wiki profile agree with the two-roll interpretation.
Separately, both PDFs **omit Anti-materiel** while Army and the
later Wiki include it. The exact Wiki history places the correction
to two rolls in revision 4077 and Anti-materiel's addition in
revision 4082; edition date or revision chronology does not establish
the authority or reason for the latter change. The imported CC Trait
remains untouched and visibly flagged as unresolved. BS Mode continues
to use Shock with no inherited Anti-materiel or CC-only rule card.

Focused contract tests are in `tests/test_weaponry_catalog_api.py`.
Chrome browser acceptance passed **21/21** route and cross-link checks
at 1440, 390 and 320 px with no JavaScript errors. The 320 px Kobra
screen was visually inspected and the CC Mode reference renders
without horizontal clipping. Two 320 px Ammunition pages triggered the
**already documented approximately 6 px shared breadcrumb overflow**;
they were explicitly allowed as known independent UI exceptions.

The source audit, exact Wiki revision hashes and timestamps are
recorded in [the rules-explanation audit](rules-explanation-audit-1.0.md)
and [source manifest](rules-explanation-audit-1.0-sources.md).
Private PDF/HTML extractions, 320 px screenshots and browser results
remain in `local/audits/` and `local/audits/rea028-browser/`.
No raw source archives, new universal rule evaluator, or guessed
profile correction were added.

## 1.0 REA-030 FAQ scope and selected applicability acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** English and Spanish FAQ
v0.1 (printed pp. 2–4; file pages 3–5) were independently compared
with the original v0.0 English FAQ and the N5.3 core scenario rules.
English FAQ provenance was already registered in the core and Hacking
collections; the verified Spanish PDF source is now registered in the
core curated collection. Its exact SHA-256 and the differing
publication-versus-PDF-creation dates are in the source audit manifest.

The published **Sixth Sense / Multispectral Visor Level 1** clarification
is strictly conditioned on the defender being targeted by a BS Attack
through a Zero Visibility Zone. The FAQ cancels the specified -6 LoF
MOD in that joint case, not all visibility penalties. The FAQ's
Spotlight Classified Objective scoring rule and undeployed Ancillary
Killed exception remain **ITS-scoped**. The core N5.3 Annihilation,
Firefight and Supplies scenario records retain their original
effects/citations, and no undocumented change to Marker-state
transitions or end-game scoring was introduced.

Chromium browser acceptance passed **24/24** page and actual link
navigation checks at 1440, 390 and 320 px across Sixth Sense,
Multispectral Visor, Targeted State, and three core scenario pages,
with no JavaScript errors or horizontal overflow. The 320 px skill,
equipment and state screenshots were visually reviewed. Regression
coverage is in `tests/test_rules_database.py` and explicitly asserts
that the ITS FAQ does not alter the core scenario rules or override
MSV Level 1 in isolation.

This is selected FAQ source-and-scope acceptance, **not** certification
of the entire 37-question FAQ corpus or a standalone versioned FAQ
collection. Wider ITS season integration and whether these ITS
scenario-element/Ancillary answers apply to core missions remain open
for authoritative clarification. Private extracts, screenshots and
results are retained under Git-ignored `local/audits/` and
`local/audits/rea030-browser/`.

## 1.0 TinBot REA-039 browser acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** N5.3 p. 127 and the six
published TinBot options were reviewed against the curated Equipment
family, Firewall and Fireteam rule references. Source/API regression
coverage includes owner eligibility, shared Fireteam benefits, non-stacking,
State Token removal and the source-specific option links. A temporary,
locally rebuilt rules database was used for browser checks rather than
assuming the existing generated release database was current.

Headless Chrome completed **12/12 render/navigation checks** across 1440,
390 and 320 px (TinBot, Firewall and Fireteam), including direct
Fireteam-to-TinBot navigation, with no JavaScript errors or page-level
horizontal overflow. The TinBot option definitions share their family
reference; they are not standalone Equipment URL routes.
Private results, screenshots and the verification script are Git-ignored
under `local/audits/rea039-browser/` and `local/audits/`.
This does not imply a generic MOD combination/Fireteam evaluator.

## 1.0 Request SpecBall REA-040 browser acceptance

**Verified 2026-10-14, `dev/v1.0.0`.** Compared the standalone
Request SpecBall and Infinity Spec-Ops Skill references against N5.3
English p. 98 and Spanish p. 98. Season 18 ITS pp. 26/28 separately
support the official-tournament Spec-Ops restriction and the distinct
TEAM-OPS Extra; Request Tacball does not change the core SpecBall rule.
The printed English "Requesting a Speedball" label is retained as
source-specific discrepancy evidence, not merged with the other Skill.

A rebuilt local rules database was used for headless Chrome browser
acceptance, not the checked-in/generated release database. The test
passed **24/24 render/navigation checks** across 1440, 390 and 320 px
for Request SpecBall, Infinity Spec-Ops, Request Speedball, Combat Jump
and Deactivator, including working links from Infinity Spec-Ops to
Request SpecBall and from the new card to its related procedures.
No JavaScript errors or page-level horizontal overflow were observed.
320 px screenshots and results remain Git-ignored under
`local/audits/rea040-browser/`; the verification script and temporary
rules DB are in `local/audits/`. This is bounded reference/browser
acceptance, not a complete Spec-Ops Chart/list builder or a rule engine.

## 1.0 Fireteam Special Dice discrepancy (REA-041)

**Verified 2026-10-14, `dev/v1.0.0`.** Compared official English N5.3
pp. 75/136 and Spanish N5.3 pp. 75/140. The English text and Spanish
general Modifiers text exclude +1 SD from the maximum B6; the Spanish
Fireteam reminder alone counts extra dice toward a six-dice ceiling.
The September 2026 update notice does not supply a sourced adjudication.

Curated Fireteam Level facts accept optional `sourceNotes`, validated
through the shared maintained-text/source rules. The Fireteams quick
reference displays those secondary notes with the same styling and
semantic links as other rules pages; the shared Special Dice reference
contains the detailed conflict notes and a B6+1 SD example. A rebuilt
local rules database backed a headless Chrome run with **15/15 passed**
render/navigation checks at 1440, 390, and 320 px; pages remained free
of JavaScript errors and horizontal overflow. Curated and composed-rules
regression tests cover both records, four bilingual citations and the
unchanged Fireteam Level 2 bonus. Private browser verifier, 320 px
screenshots, result JSON and temporary rules DB remain under ignored
`local/audits/`. Official erratum remains unresolved; the browser does
not silently apply a new Fireteam rolled-dice cap.

## 1.0 Dodge (ARM+3) source reconciliation (REA-042)

**Verified 2026-10-14, `dev/v1.0.0`.** Official English N5.3 p. 75
and Spanish N5.3 p. 75 grant the profile-listed +3 ARM/BLI modifier on
relevant Saving Rolls after Dodge declaration. The English Wiki snapshot
`20260926-200832` and Spanish Wiki snapshot `20261009-211304` instead
restrict it to a failed PH/FIS Roll. Spanish revision 4012 establishes
historical provenance for the latter. The official September 1, 2026
N5.3 articles describe a Dodge clarification but do not resolve these
different conditions. Both interpretations remain labeled by source;
the current curated card uses the matching two-PDF rule.

Focused curated and published-rules tests verify the non-universal
(ARM+3) bonus, the lack of a PH or BTS modifier, application when a
separate simultaneous Attack requires a Saving Roll, and all four
bilingual PDF/Wiki source citations. A locally rebuilt rules DB and
headless Chrome passed **12/12** render/navigation checks at 1440, 390
and 320 px for Dodge, Saving Rolls, Face to Face Rolls, and the inline
Dodge-to-Saving-Rolls link. No JavaScript page errors or horizontal
overflow were observed. Screenshots, results, private script and
local temporary DB remain under Git-ignored `local/audits/`.
This does not imply a full simultaneous combat resolver or an
unverified official erratum.

## 1.0 Doctor/Engineer direct versus delegated target scope (REA-038)

**Reviewed 2026-10-14, `dev/v1.0.0`.** Checked the N5.3 English
Doctor/Engineer pages 90-91, Engaged and Close Combat pp. 51/160,
Kit-specific Allied requirements pp. 123-124, Peripheral delegations
pp. 106-107, and pinned English/Spanish Wiki Doctor/Engineer pages.
Direct Skill requirements specify contact and applicable State/Attribute
conditions, but not a generic Allied-only gate. The explicit Allied
conditions for Kits and delegated Peripheral use remain local, and
Engaged restrictions remain independently mandatory. Non-Allied direct
use beyond such confirmed conditions has **not** been adopted as a
universal gameplay permission.

Focused source/database regression checks assert the unchanged direct
requirements, Kit/Peripheral Allied boundaries, published clarification,
close-combat source citations and unresolved non-Allied note. Responsive
headless Chrome acceptance against a locally rebuilt rules DB checks
Doctor, Engineer, MediKit and GizmoKit at 1440, 390 and 320 px, plus
cross-links, JS errors and horizontal overflow. Verification script,
screenshots, generated rules DB and results are private and ignored in
`local/audits/`. A future official ruling or explicit project decision
is required to adjudicate non-Allied direct targeting fully.

## 1.0 Armed Turret Silhouette source conflict (REA-037)

**Verified 2026-10-14, `dev/v1.0.0`.** English N5.3 detailed p. 70
and Spanish detailed p. 74 use S2; English deployable summary pp.
74/195 and Spanish p. 203 use S1. Pinned English/Spanish Wiki
Armed Turret detailed pages corroborate S2. English N5.3 p. 18
verifies the same 25 mm base with different S1/S2 heights (25/40 mm).
This is unresolved official source conflict, not a corrected value.

Focused curated and published-rules regressions require the S2 statline,
the secondary player-facing conflict note and all underlying citations.
A rebuilt local rules database was used for headless Chrome
acceptance. **3/3 render checks** passed at 1440, 390, 320 px on the
`/weapons/armed-turret` page, checking the S2 displayed value, S1/S2
conflict note in `.rules-source-note`, absence of JS errors and
horizontal overflow. Screenshots and private verification outputs
remain ignored under `local/audits/`. The separate REA-045 E/Mitter
Saving Roll issue is not altered by this acceptance.

## 1.0 Armed Turret E/Mitter Saving Roll discrepancy (REA-045)

**Verified 2026-10-14, `dev/v1.0.0`.** Six archived Army metadata
captures list weapon 226 / E/Mitter mode as E/M, BTS/2, one Saving
Roll; standalone weapon 25, English N5.3 p. 186, Spanish p. 195 and
the canonical E/M rules list two. Neither the official Turret rule
nor N5 FAQ v0.1 authorizes a scoped exception. The two values are
reported as unresolved provenance, not adjudicated game mechanics.

The Turret summary remains gameplay-focused; a second `facts.sourceNotes`
entry owns the discrepancy (the first is REA-037 Silhouette). Source
and composed-rules regression tests assert the unchanged imported Army
metadata, the standalone E/Mitter, visible secondary note and typed
links. The source test exports a fresh local rules DB to avoid stale
release database assumptions.

Headless Chrome against a rebuilt local rules DB passed **15/15
content/navigation checks** at 1440, 390 and 320 px across Armed Turret,
E/Mitter and E/M Ammunition, including both linked destinations.
The Turret and E/Mitter pages had no horizontal overflow or JS errors.
At 320 px, E/M Ammunition alone retains a 6 px overflow from the
`Rules reference` catalog tag. The exact same overflow reproduces
against the preexisting release rules DB and is already recorded
under REA-024 TODO; not introduced by this change. Screenshots and
diagnostics remain private in Git-ignored `local/audits/`.

## 1.0 Fireteam Level 3 printed-example disagreement (REA-034)

**Verified 2026-10-14, `dev/v1.0.0`.** Both English N5.3 p. 138 and
Spanish N5.3 p. 142 show a five-member Morat CORE with only three
matching members and describe it as Level 3, but include Level 4's
+1 BS/CD Attack bonus. The level tables (English pp. 135?136,
Spanish pp. 139?140) require four matching or equivalent members for
that extra BS MOD. The new `facts.basis` example correctly explains
cumulative bonuses through Level 3; a separate `facts.sourceNotes`
entry preserves the erroneous examples. The existing REA-041 Special
Dice notice remains separate and the Level table remains unchanged.

Focused curated/published rules validation passed **277/277** tests.
Headless Chrome against a locally rebuilt rules DB passed **9/9**
render and navigation checks at 1440, 390 and 320 px, including the
actual Level 3 versus Level 4 table rows, two source notes, and links
from the example to Special Dice and Discover. No JS errors or page
horizontal overflow. Private script, result JSON, and 320 px screenshot
remain Git-ignored under `local/audits/`.
The outstanding official erratum remains an external decision.

## 1.0 Engineer recovery and target eligibility (REA-001)

**Verified 2026-10-14, `dev/v1.0.0`.** Compared English N5.3 Engineer
p. 91 and cancellation conditions for Stunned p. 170 and Targeted
p. 171 with existing direct/delegated scope review REA-038. The
published Engineer record preserves STR Wound repair versus
State-cancellation as different WIP outcomes, self-use restrictions,
Remote Presence and ReRoll WIP/Command Token exceptions. Clarifications
now give a VITA Targeted example and a VITA/STR Stunned counterexample.
An allied example deliberately avoids inventing non-Allied eligibility.

Curated and composed-rules regressions passed **279/279** tests. Headless
Chrome against a newly rebuilt local rules database passed **18/18**
content/navigation checks at 1440, 390 and 320 px on Engineer,
Targeted and Stunned, including Engineer-to-Targeted/Stunned/Doctor
semantic links. No JavaScript errors or horizontal overflow. Private
acceptance script, screenshots and result JSON are Git-ignored under
`local/audits/`. General recovery simulation and an official ruling
on non-Allied direct treatment are outside this acceptance scope.

## 1.0 Doctor recovery and scoped exceptions (REA-002)

**Verified 2026-10-14, `dev/v1.0.0`.** Compared N5.3 English Doctor
p. 90, No Wound Incapacitation p. 104, Technorganic and its STR
recovery example p. 116, and Stunned State cancellation p. 170. The
published Doctor reference retains Unconscious VITA/contact eligibility,
lethal ordinary failure, Doctor (2W), ReRoll WIP=X, and the independent
Command Token reroll. Added four source-linked clarifications covering
ordinary healing versus a conscious wounded target, Stunned treatment,
NWI self-treatment, and Technorganic's Unconscious-only exception.
The pending REA-038 non-Allied direct-target interpretation was not
resolved or changed.

Focused curated/composed rules regressions passed **281/281**. Headless
Chrome against a newly rebuilt local rules DB passed **21/21**
content/navigation checks at 1440, 390 and 320 px for Doctor, NWI,
Technorganic and Stunned, including Doctor-to-exception links, with
no JavaScript page errors or horizontal overflow. Private script,
320 px screenshots and result JSON remain in Git-ignored
`local/audits/`. This is reference acceptance, not a general healing
simulation or complete non-Allied eligibility adjudication.

## 1.0 Intuitive Attack source and browser acceptance (REA-003)

**Reviewed 2026-10-14, `dev/v1.0.0`.** Compared English N5.3 p. 49,
Spanish N5.3 p. 48, and the pinned Wiki Intuitive Attack source. The
existing Skill effects specify the one unmodified WIP Roll for the B1
Attack, eligible Face to Face reactions, Main Target-only Critical and
specific Deployable Trigger Area/Disposable conditions. Three published
examples make the unreacting CAMO, opposing ARO/multiple targets and
Deployable placement cases explicit without changing those mechanics.

Curated source and composed-rules regression tests protect the examples,
canonical Trait link and both printed-page citations. The browser
acceptance script and locally rebuilt rules database are private in
`local/audits/`; tests include desktop and 390/320 px widths and
semantic navigation to the shared roll and placement references.

## 1.0 Continuous Damage Critical and Immunity acceptance (REA-004)

**Verified 2026-10-14, `dev/v1.0.0`.** Compared official English N5.3
Continuous Damage p. 175 and Immunity p. 95 with Spanish N5.3 Daño
Continuo p. 182 and Inmunidad p. 99. Continuous Damage repeats Saving
Rolls after a failed ordinary hit save but explicitly does not apply to
the additional Saving Roll from a Critical. A failed Critical-added roll
may inflict the ordinary effect but does not itself start a chain.
Relevant Immunity variants can suppress the Trait without canceling the
ordinary or Critical-added Saving Roll; only Immunity (Critical) removes
the extra Critical roll itself. No unconditional Dead transition is added.

Two examples in `trait:continuous-damage` `facts.clarifications` are
covered by curated and composed-record tests, including bilingual source
citations, the separate ordinary/Critical outcomes and conditional
Immunity. Focused pytest suite passed **285/285**; headless Chromium
passed **15/15** content/navigation checks at 1440, 390 and 320 px for
Continuous Damage, Immunity and Saving Rolls including both semantic
links. No JS errors or page-level horizontal overflow. Verification
script, screenshots and results remain ignored in `local/audits/`.
This acceptance is not a complete damage or Immunity simulator.

## 1.0 BS Weapon (WIP) named Skill restrictions (REA-005)

**Verified 2026-10-14, `dev/v1.0.0`.** Compared English N5.3 BS Weapon
(WIP) p. 175 and BS Attack (Guided) p. 39 with Spanish N5.3 Guided
p. 39. The original summary already excluded the **BS Attack (Shock)**
and **BS Attack (Guided)** Skills with WIP weapons but not Shock Ammunition
in general. Three linked clarifications now show Flash Pulse as an
ordinary WIP-based BS Attack, the separate Shock Skill-versus-ammunition
scope, and Guided's incompatibility even against a Targeted enemy.

Curated and composed-record tests assert all three cases, source
citations, unchanged `modifies-rolls-for` relation and Flash Pulse
source behavior. Chromium acceptance passed **21/21** render/navigation
checks at 1440, 390 and 320 px for the Trait, Flash Pulse, BS Attack,
Shock Ammunition and Targeted links. No JS errors or horizontal overflow.
Private script, screenshots and result JSON are kept under ignored
`local/audits/`. No exact attack variants, new restriction edges or
gameplay changes were introduced.

## 1.0 Controlled Jump declaration and cancellation (REA-006)

**Verified 2026-10-14, `dev/v1.0.0`.** English N5.3 p. 59 and Spanish
N5.3 p. 61 confirm immediate activation of Controlled Jump upon
its declaration, including an optional table-wide ARO imposing -3 on
the same enemy Combat Jump landing PH Roll. The modifier can affect
non-Hackable Troopers. If both players have Controlled Jump active,
the two Programs cancel only their own effects; Firefight Designated
Landing Area +3 (English p. 155) remains independently applicable.
FAQ v0.1 p. 1 excludes Speedball Tokens from this Trooper-only Program.

The existing effects/restrictions and single `modifies-rolls-for` Combat
Jump relation were retained. Added three `facts.clarifications` and a
Spanish source record in the hacking-programs collection; no new
runtime or timing representation. Curated/published regression checks
cover the same-roll ARO, opposing-program cancellation, independent
scenario bonus and Token exclusion, with cited EN/ES and FAQ sources.
Chromium passed **18/18** render/navigation checks at 1440, 390 and
320 px on Controlled Jump, Combat Jump and Request Speedball, including
links to Combat Jump, Hacker and Request Speedball. No JS errors or
horizontal overflow. Private verifier, screenshots and results remain
under Git-ignored `local/audits/`. REA-007 keeps its separate
Speedball-specific reference acceptance task.

## 1.0 Speedball FAQ exclusion and PH 15 example (REA-007)

**Verified 2026-10-14, `dev/v1.0.0`.** Official English N5.3 Request
Speedball p. 84 calls for two 55 mm Tokens with PH 15 Rolls using Combat
Jump placement. N5 FAQ v0.1, printed p. 1, explicitly excludes
Speedballs from Controlled Jump because that Program affects Troopers
only. Both references already cited this FAQ and linked to the other.
The added Speedball clarification gives the concrete PH 15 versus PH
18/12 example while limiting the exclusion to Controlled Jump +3/-3,
without settling other scenario modifier rules.

Curated and composed rules regressions cover the versioned FAQ citation
on both cards, the PH 15/18/12 example, the Trooper-versus-Token scope,
and unchanged Combat Jump reuse relation. Responsive Chromium acceptance
covers both cards, Combat Jump, reciprocal navigation, JavaScript errors
and 1440/390/320 px overflow. **18/18 Chromium checks passed** with
no JavaScript errors or page-level horizontal overflow. Private verifier,
screenshots, result JSON and rebuilt rules DB stay Git-ignored in
`local/audits/`.

**Source-copy fidelity follow-up, 2026-10-29:** Corrected three
corrupted possessives in two maintained N5.3 core-rule clarifications:
`trait:continuous-damage`'s Immunity explanation (`Trait's`, `target's`)
and `skill:request-speedball`'s Controlled Jump explanation
(`Controlled Jump`'s). The associated English N5.3 Immunity p. 95
and FAQ v0.1 p. 1 remain the reviewed rule evidence. Restored the
Spanish *Daño Continuo* title above. Both curated and composed-rules
regressions now assert the restored phrases, preserving existing
effects, links, citations and applicability. This is text fidelity,
not a new Immunity/Controlled Jump interpretation or general
curated-text certification.

## 1.0 simultaneous recovery and re-infliction (REA-009)

**Reviewed 2026-10-15, `dev/v1.0.0`.** The official English and Spanish
N5.3 PDFs, both p. 15, explicitly place positive effects before
negative effects when a Trooper receives and removes Wounds or States
within one Order. The printed Engineer/Riotstopper example uses Engineer
WIP to cancel the original IMM-A, then a PH-6 PARA Saving Roll. WIP
failure leaves original IMM-A; WIP success plus successful PARA Save
leaves IMM-A canceled; WIP success plus failed PARA Save inflicts new
IMM-A. The newly linked shared Order Expenditure Sequence owns this
worked example; Engineer, Doctor and IMM-A link to it. The PARA
`failed-saving-roll` State effect remains unchanged.

Source and composed-rules regressions cover the three outcomes,
versioned EN/ES p. 15 provenance and semantic links, and unchanged
PARA behavior. Browser acceptance uses a freshly rebuilt local rules
DB at 1440/390/320 px with the Order, Engineer, Doctor, IMM-A and
PARA cards, plus linked navigation, JavaScript errors and overflow.
**33/33 Chromium content/navigation checks passed** with no JavaScript
errors or new overflow. At 320 px, PARA alone has an existing 6 px
`catalog-tag` overflow; it reproduced identically with the preexisting
release rules DB and locally rebuilt rules DB. The Order, Engineer,
Doctor and IMM-A pages had no overflow at any checked width. The
private verifier, screenshots and diagnostics live under ignored
`local/audits/`. No game-state timing engine was introduced.

## 1.0 general Immunity and printed examples (REA-010)

**Reviewed 2026-10-15, `dev/v1.0.0`.** English N5.3 pp. 95-96 and
Spanish N5.3 p. 99 explicitly provide *two independent* protections for
non-Comms ARM/BTS attacks using the matching Saving Roll Attribute:
covered Ammunition becomes Normal, and applicable Weapon/Skill/Equipment
Traits causing States, Wounds or Attribute reduction are ignored.
Neither changes the ordinary Saving Roll or automatically removes an
additional Critical save. The Immunity effects now link to State,
Continuous Damage, ARM=0, and BTS=0 as concrete representative Traits.

Printed Example 2: Monofilament versus Immunity (ARM) ignores ARM=0 and
State: Dead, with one ARM save (two for Critical unless also Immunity
(Critical)). Printed Example 4: Immunity (BTS) versus Flash Pulse keeps
the BTS save and preserves Non-Lethal and State: Stunned on failed save.
The Spanish Wiki Flash Pulse Weapon Chart contradiction remains
separately described in `weapon:flash-pulse` source notes; the published
N5.3 bilingual PDFs agree on one roll and both Traits. No interaction
arrays, evidence labels or gameplay mechanics were changed.

Source and composed-rules regression checks verify these conditions,
provenance and unchanged five reviewed Immunity interactions. Browser
acceptance checks Immunity, Flash Pulse, the linked Trait pages and
semantic navigation at 1440, 390 and 320 px against a freshly rebuilt
local rules DB. **30/30 Chromium content/navigation checks passed** with
no JavaScript errors or page horizontal overflow. The private verifier,
screenshots and results remain in ignored `local/audits/`.

## 1.0 reviewed Immunity interactions browser acceptance (REA-011)

**Verified 2026-10-15, `dev/v1.0.0`.** The shared Immunity-case renderer
already publishes five structured, provenance-qualified interactions:
Flash Pulse/BTS and Enhanced+Viral Vulnerability (two explicit source
cases); ARM/AP+DA, ARM/AP+EXP and AP/AP+DA (three derived general-rule
cases). Conditions include non-Comms scope, Viral in the weapon **name**,
individual before/after hit and Critical Saving Roll counts, AP-only
negation retaining DA, and the Immunity (Critical) caveat. A Plasma /
Enhanced result is not stored and must not be invented.

Chromium acceptance uses a fresh local rules DB and the actual
`/skills/immunity` card at 1440, 390 and 320 px, asserting five
visible cases, all conditions, individual evidence labels, link routes,
no JS errors and no horizontal overflow. Keyboard-only Tab advances
between native case links with the shared focus-visible ring, and
Enter follows the focused reference. Screenshots and diagnostic JSON
remain in ignored `local/audits/`. The tracked Node render harness
now also guards one semantic title/body/evidence block per item,
two explicit and three derived labels, the reviewed non-Comms scope,
and no synthesized Plasma example. Two existing API test assertions were
brought back into sync with prior changes: the REA-010 Immunity
ordinary-roll wording and the fourth Dodge clarification added earlier.
No renderer, source facts or rule mechanics needed changing.

## 1.0 Smoke and Eclipse browser acceptance (REA-012)

**Verified 2026-10-15, `dev/v1.0.0`.** Official English N5.3 p. 66
requires a rolled enemy Attack and crossing LoF to oppose Smoke
placement; the user must win every applicable Face to Face Roll, while
an affected enemy Dodge is Normal and Smoke Critical adds no effect.
English p. 64 makes Eclipse's Reflective exception apply to qualifying
MSV attacks through its zone, without overriding unopposed placement
or the ordinary Smoke rules. MSV Levels (p. 125) remain independent.
The maintained clarifications and visibility-zone fact objects were
already present, with cited EN/ES N5.3 source pages and shared links.

Expanded the published/API regression test to assert the exact
rolled-LoF, multi-opponent, Critical, Dodge, unopposed, MSV/Reflective
and zone-fact branches. Headless Chromium against a newly built rules
DB passed **33/33** render/navigation checks at 1440, 390 and 320 px
covering the Smoke, Eclipse, MSV, Reflective and Dodge references,
including cross-links to the Poor Visibility glossary entry.
No JavaScript errors were observed. A known **6 px** breadcrumb
`catalog-tag` overflow affects Smoke and Eclipse at 320 px; it
reproduced identically in both the existing release and rebuilt rules
DBs. This is already tracked for the shared reference layout, not
claimed to be resolved by REA-012. Private acceptance script,
screenshots and result JSON remain ignored under `local/audits/`.
No game mechanics, source data or frontend renderer were modified.

## 1.0 AP/E/M rounding and T2 Critical die acceptance (REA-013)

**Verified 2026-10-15, `dev/v1.0.0`.** The English N5.3 rules
(pp. 63-64, 67) and Spanish N5.3 rules (pp. 64, 66-67) confirm that
halving ARM/BTS always rounds up: 5 becomes 3 and any positive value
remains at least 1. AP uses the ARM or BTS Saving Roll Attribute set
by its weapon. E/M uses BTS/2 for both required hit Saving Rolls; a
Critical adds one more roll. Each affected State remains conditional
on a failed roll. T2 requires distinguishing its original-hit die
(2 Wounds on failure) from the extra Critical die (1 Wound on failure)
**before** rolling the Saving Rolls.

The pre-existing curated clarifications and typed resolution facts were
already correct and source cited. A published/API regression test was
extended to protect AP/E/M Attribute modifiers, E/M's two hit rolls,
conditional States, and the single additional Critical roll; existing
assertions protect T2's differentiated Wound counts and citations.

Headless Chromium with a freshly built rules DB passed **18/18**
render/API checks on AP, E/M and T2 at 1440, 390 and 320 px; no
JavaScript errors were observed. A **pre-existing 6 px catalog-tag
breadcrumb overflow** occurs on all three pages at 320 px, identically
against the release and rebuilt rules DBs, and remains tracked under
the separate final shared-layout acceptance task. The private browser
verifier, screenshots and result JSON remain in Git-ignored
`local/audits/`. No source data, gameplay mechanics or renderer changed.

## 1.0 Dodge/Reset conditional outcomes and State links (REA-014)

**Verified 2026-10-15, `dev/v1.0.0`.** Reviewed the existing N5.3-cited
Dodge, Reset, Engaged, Isolated, IMM-B, Targeted, Sixth Sense and
Bangbomb references. One Dodge die is evaluated independently for
several Attacks; failure to evade any applicable Attack prevents Dodge
movement, even when another is evaded. Only one -3 PH MOD applies to
the listed special Dodge circumstances. Cancellation of Engaged also
requires a valid new position outside contact with every enemy.

IMM-B (-3), Isolated (-9) and Targeted (-3) Reset WIP penalties combine
up to the general -12 cap. Sixth Sense ignores ordinary penalties
including Targeted but preserves the explicit IMM-B/Isolated exceptions.
The Bangbomb (+4) example distinguishes the eligible Combi Rifle
attack from an E/Marat Template with a different PH Success Value.

Extended the published/API regression to cover the State records,
Sixth Sense exceptions and Bangbomb's conditional outcome; preserved
original State/Skill relationships and citations. Headless Chromium
against a fresh local rules DB passed **48/48** content/navigation
checks at 1440, 390 and 320 px, covering eight reference pages and
cross-links, without JavaScript errors or horizontal overflow.
Screenshot, script, results JSON and generated DB remain in ignored
`local/audits/`. This is rules-reference acceptance, not an executable
multi-target roll evaluator. REA-015/REA-026 are separate tasks.

## 1.0 State-specific cancellation acceptance (REA-015)

**Verified 2026-10-15, `dev/v1.0.0`.** Ten N5.3-cited State cards
retain distinct cancellation conditions: Camouflaged AROs, Hidden
Deployment and independent Marker identity, Holoecho bearer versus
holographic decoy, HoloMask end-of-Order replacement, IMP-1 versus IMP-2
revelation, Prone/Unconscious and Impetuous, Controller/Coherency/Engineer
routes for Disconnected, Retreat! Command Token recovery, and Suppressive
Fire termination. The published/API regression now guards these
conditions in addition to bilingual source citations.

A minor IMP-1 correction changes "an disguised Marker" to "a disguised
Marker". Its reviewed plain `AROs` fingerprint was updated while keeping
the previously reviewed non-Trait meaning. The maintained-text gate
and rules database validate the change. Headless Chromium passed
**66/66** content/navigation checks at 1440, 390 and 320 px, covering
ten State pages and twelve links per viewport, with no JavaScript errors
or horizontal overflow. Scripts, screenshots and result JSON are
Git-ignored under `local/audits/`. REA-026 remains a separate contract.

## 1.0 Stealth, Deployables and mixed activation (REA-016)

**Verified 2026-10-15, `dev/v1.0.0`.** Official English N5.3 p. 112
and Spanish N5.3 p. 114 expressly exclude Deployable Weapons and
Equipment from Stealth; the FAQ v0.1 EN/ES printed p. 2 requires
announcing ARO-limiting Automatic Skills while using a Marker and
permits a reaction generated by another activated Trooper to choose
the Stealth user, becoming Idle when that user does not declare a
Skill that permits the reaction. The example uses a Controller and
Peripheral without implying a universal reaction evaluator.

Added three player-facing examples to the existing Stealth Skill, with
direct source citations. Effects, restrictions, typed relations, Mines,
Boost, Sixth Sense and Combat Instinct source mechanics were retained.
Source and composed-rules tests verify the examples, all four cited
pages, independently triggering Deployables, and the unchanged
Cautious Movement relationship.

Headless Chromium using a freshly rebuilt rules DB passed **39/39**
content/navigation checks at 1440/390/320 px on Stealth, Deployable,
Boost, Sixth Sense, Combat Instinct, Peripheral and Cautious Movement,
with no JavaScript exceptions or horizontal overflow. Browser script,
screenshots and result JSON remain ignored under `local/audits/`.
At this point the Mines family route was flagged for investigation,
so the new Stealth example used ordinary Mine prose and linked
Deployable mechanics. The subsequent Weapon-family routing audit
(below) confirmed that the generated `weapon:mines` destination was
already `/weapons/ap-mine#rule-weapon-mines`, not the invalid
`/weapons/mines` guess. The actual Glossary discovery defect was
corrected and browser-verified separately.

## 1.0 curated Weapon-family and Glossary routing acceptance

**Verified 2026-10-15, `dev/v1.0.0`.** The canonical link for the
curated `weapon:mines` family was already
`/weapons/ap-mine#rule-weapon-mines` (the AP Mine catalog page embeds
the reviewed Mines rule card). `/weapons/mines` is not a published Army
Weapon slug and properly returns 404 if guessed directly; it was not
the generated link. All 51 current curated Weapon definitions were
audited against the pinned Army database: each resolves to a real
catalog page hosting its rule (including exact source-mode variants).

The actual defect was Glossary discoverability. Its bulk rules query
excluded Army links, causing weapon identities to be silently skipped
when calculating destinations. Army links remain opt-in by default;
the Glossary requests them only for Weapon records. The resulting
Glossary publishes 49 non-source-specific Weapon definitions, including
Mines, PARA Mine and WildParrot, without creating duplicate catalog
items or publishing source-mode subrecords independently.

Two regression tests verify the opt-in bulk-query contract and the
published `/api/glossary` weapon destinations. Headless Chromium
passed **42/42** checks at 1440/390/320 px: searching for Mines in
Glossary, clicking through to the exact rule-card anchor hosted on
AP Mine, verifying PARA Mine's local anchor and following WildParrot's
cross-page Mines reference. No JavaScript exceptions or new horizontal
clipping of the Mines card were found. Private browser scripts/results
are ignored under `local/audits/`. Other final cross-surface reference
acceptance items remain open.

## 1.0 five-card cross-surface reference browser acceptance

**Verified 2026-10-15 on `dev/v1.0.0`.** Headless Chromium exercised
IMP-2, Stealth, Deployable Cover, TinBot, and Kobra Pistol (including its
CC-mode rules) on 1440 px desktop and 390/320 px narrow layouts. A fresh
private `rules.db` was built from the current curated sources; the tracked
0.10.1 release database intentionally does not yet contain all current
Stealth/TinBot explanations. No release database was replaced.

**93/93 browser checks passed**: each card rendered its relevant conditions;
rule and Trait links were focusable and activated using Enter; the Kobra CC
Attribute link opened `Glossary#attribute-cc`; and reviewed source citation
links opened the intended URL in a separate tab. External HTTPS responses
were stubbed to test navigation deterministically, **not** third-party
availability or the accuracy of a live remote page. The pinned N5.3 Wiki
revision citations were checked separately from legacy, Army-supplied Wiki
URLs. No JavaScript exceptions, horizontal overflow, or narrow-card clipping
were observed. The 320 px screenshots of the longer Deployable Cover,
TinBot, and Kobra CC cards were inspected for readability.

The private verifier, result JSON, and screenshots remain Git-ignored under
`local/audits/final-reference-cards-browser/`. This completes only the
five-card browser acceptance in `docs/TODO.md`. Fireteam interactions,
scenario selection/maps, and Visibility Zone/Immunity input-method
acceptance remain open; this was not a full release/UI audit.

## 1.0 Fireteam cross-surface browser acceptance

**Verified 2026-10-15 on `dev/v1.0.0`.** Headless Chromium against the
current Army database and a fresh, private curated rules database checked
the Fireteams landing and Army-scoped views at 1440, 390 and 320 px.
The general unscoped quick reference shows DUO/HARIS/CORE formation
limits, Coherency, Team Leader duties, whole-team cancellation,
individual member departure, rejoining, FT Master exceptions and
Fireteam Level bonuses. It links to canonical Skills including FT Master.
The general reference is intentionally hidden while an Army is selected.

**167/167 browser checks passed.** The Shock Army of Acontecimento chart
shows four Wildcard-augmented teams (38 member rows, 20 Wildcard badges)
with the setting enabled. Disabling it restores the five separate team
entries (23 rows); enabling it restores the merged projection without
changing the selected Army URL. Army-specific type limits, minimum/
maximum/exact member requirements, and resolved Unit links were checked.
A member link was activated using the keyboard, the Unit page was opened,
and browser back restored the selected chart. Opening the versioned
share URL directly reproduced the correct Army; changing to Military
Orders, navigating back, and clearing the selection produced the intended
states. No JavaScript errors or page-level horizontal overflow occurred.
At 320 px, the member table's independent horizontal scrolling was
verified and its full-page screenshot reviewed.

The private test script, diagnostics and screenshots remain ignored under
`local/audits/final-fireteam-browser/`. This closes the Fireteam browser
acceptance item in `docs/TODO.md`, not the separate REA-020 Fireteam
mechanics/source review, scenario interaction acceptance or final
source-to-storage-to-browser completeness gate. No frontend or curated
mechanics were changed in this acceptance pass.

## 1.0 scenario-model ITS compatibility acceptance

**Verified 2026-10-15 on `dev/v1.0.0`.** A source comparison of the
locally pinned Season 18 PDF (2026.09.01) with the existing core scenario
model confirms that optional multiple Deployment Zones per Side
(`Crossing Lines`) and asymmetric objective `sideIds` (`Critical
Intervention`) are preserved through validation and scenario-catalog
projection. A synthetic in-memory catalog regression exercises those
boundaries without publishing an ITS mission or adding rules data.

Radius-based Safe Areas (`Provisioning`), selected objective sets
(`Double Bind`), Classified systems and cross-season revision selection
remain out of 1.0 scope and are **not** claimed as implemented. The
private evidence is under `local/audits/its-scenario-model-compatibility-20261015.md`.
Normal rules and scenario tests cover current N5.3 publication behavior.

## 1.0 four-core-scenario browser acceptance

**Verified 2026-10-15 on `dev/v1.0.0`.** Headless Chromium used the
current Army database and a privately rebuilt current curated rules
database. Annihilation, Domination, Supplies and Firefight were browsed
from `/scenarios` on 1440/390/320 px layouts. Each scenario opened at
the published 300-point default. The page was switched through all six
supported sizes (150, 200, 250, 300, 350, 400), and rapid successive
changes were checked to ensure the final selected setup, map identity,
objectives and table facts won rather than stale asynchronous results.

**792/792 main-flow checks passed.** Every game-size map rendered as an
inline canonical SVG and remained within the viewport. Light and dark
themes and inch/centimeter display were switched on each scenario at
all three viewport sizes, checking the live SVG labels, table size,
selection and absence of JavaScript errors or page-level overflow.
Keyboard activation of scoped rules links, browser back to the scenario,
then back to the four-card catalog worked. Screenshots of the 320 px
light/dark inch/cm configurations were visually reviewed for readability.

**13/13 additional controlled checks passed.** The catalog loading,
empty-list and API-error states were verified by intercepting its
requests. Detail API failure displayed an error and recovered after a
subsequent valid Army Points choice; unsupported direct game size
produced an explicit error. A touch-enabled 390 px context verified
catalog navigation, Settings/distance switching, the first-tap
maintained-reference preview, second-tap navigation, browser back and
restoration of the selected size. External requests were not used for
this acceptance. The private verifiers, screenshots and results remain
ignored under `local/audits/final-scenario-browser/`.

**Scope:** Browser acceptance only (805/805 total). This does not close
the separate source-completeness review of every scenario fact and
scenario-specific rule at every supported size, nor resolve the
Domination 350-point SWC conflict or perform the complete 1.0 release
gate. No application code or curated scenario mechanics were changed.

**Follow-up source review, 2026-10-15:** All 24 configurations
(four core scenarios × six Army sizes) have a reviewed English N5.3
Forces/Deployment chart baseline and corresponding composed-database
and API regression checks. Spanish N5.3 confirms Annihilation's existing
reviewed 350-point survival-band correction, but contradicts English
N5.3/N5.2 and the pinned English Wiki on Domination 350-point SWC
(Spanish **7**, English **6**). The public read model retains 6
and an explicit `needs-verification` source issue until authoritative
clarification. Previous browser acceptance covers all 24 selections;
this source-review milestone does not close the project-wide 1.0
source inventory or normal release checklist.

**Repeatable core-scenario browser regression, 2026-10-28:** The tracked
`tests/test_verify_scenario_faq_browser.py` suite now includes a
source-chart-to-ordinary-browser matrix for all four Core scenarios and
six Army Points sizes at 1440/390 px. It checks presented Army Points,
SWC (including Domination's documented 350-point conflict), table sizes,
minimum Victory Points where applicable, Objective and Rule/Skill card
counts, canonical inline map dimensions, N5.3 citations, scoped source
notes, and reload persistence. Additional browser cases cover
keyboard-operated catalog-to-detail/back navigation for all four
scenarios at 1440/390/320 px; scoped Rule/Skill navigation with restored
scenario selection; rapid successive game-size changes; controlled
catalog failure/empty states; and detail API failure recovery.
The companion catalog tests independently pin the 24 curated chart
rows; the browser suite tests their player-facing rendering.

Run this reproducible local regression from the repository root:

```powershell
.venv\Scripts\python.exe -m tools.run_checks --stage test tests/test_verify_scenario_faq_browser.py
.venv\Scripts\python.exe -m tools.run_checks --stage test tests/test_scenario_catalog.py
.venv\Scripts\python.exe -m tools.run_checks --stage test tests/test_scenario_api.py
```

The WSGI-backed browser uses a fresh isolated rules export and the
checkout's Army database. The additional
`test_every_published_faq_has_a_normal_browser_entry_point` tests
all 29 reviewed FAQ question/answer/citation cards at 25 ordinary
reference entry points, grouped into eight Chromium checks at
1440/390 px; all eight passed on 2026-10-29. Its independent
coverage assertion fails on added, removed or unmapped rulings.
The normal browser paths include catalog details, Fireteams and the
two scenario-only selections. This is repeatable **local development
evidence**, not a substitute for broader manual visual/touch review,
source inventory, hosted exact-version deployment or the final 1.0
release gate.
The official cross-language Domination discrepancy remains unresolved.

**Orders/AROs scoped-action browser acceptance, 2026-10-30:** The
`tests/test_verify_orders_aros_browser.py` suite checks the unchanged 57-row
Core reference at 1440/1024/390/320 px, plus opt-in Domination and Supplies
Short Skill rows, selected context/URL persistence, source page display,
deep links to actual scenario Skill cards, empty Annihilation scope, invalid
ITS-only selection rejection, mobile layout and error recovery. The
`tests/test_hacking_program_publication.py` API cases independently verify
each of the four current Core scenario selections, distinct scopes, unchanged
Core payloads and rejection of unsupported/season-only contexts. This is
local Chromium acceptance, not deployed browser verification.

**Typed Smoke/Eclipse opposition reference, 2026-10-31:**
`tests/test_ammunition_visibility_opposition.py` pins N5.3 pp. 64/66
and verifies the exact optional opposition facts, canonical rule relation,
stored/public API parity and compatibility with older zone objects.
Mutations reject omitted Roll/LoF/crossing conditions, universal Visor
opposition, opposed enemy Dodge, win-any retention, additional Critical
Saving Rolls and calculated target outcomes. The shared renderer preserves
State links while linking opposition rows to the canonical Face to Face rule.
Six Chromium checks in `test_verify_ammunition_publication_browser.py`
cover Smoke/Eclipse at 1440/390/320 px, API agreement, exact conditional
rows, keyboard rule navigation/back, request/page errors and overflow.
The module now has 68 cases. The older REA-012 6 px overflow observation
is historical; these current checks require no horizontal overflow.
Rules/publication promotion retains the same 17 deployed objects and
recovery copies. This is reference acceptance, not an attack calculator.

**Weapon-detail reviewed Ammunition browser parity, 2026-10-31:**
`tests/test_verify_ammunition_publication_browser.py` cross-checks
the published Weapon API with the existing UI for all five reviewed
Combined Ammunition identities (source IDs 5, 10, 13, 30 and 40).
At 1440/390/320 px, 15 Chromium cases require ordered canonical
component links, exact displayed canonical summaries (resolving
maintained `[[target|label]]` text), source citation counts and
unchanged Saving Roll cells, with no overflow. Three additional
Plasma Rifle checks confirm a Combined Saving Roll (`ARM and BTS`)
is not turned into Combined Ammunition. No application source,
curated data, Army profile or published database is changed.
The extension covers one real source-backed Weapon profile for each of the
11 base Ammunition identities: 33 Chromium cases at 1440/390/320 px verify
single-component canonical links, shared summaries with resolved maintained-text
display forms (including plural references), citation counts, source Saving Roll
notation, and no horizontal overflow. Eleven more Chromium cases at 390 px
visit the canonical Ammunition detail routes, verify matching titles and cited
rule records. That parity-only batch covered 62 cases; all 11 base and five combined source
identities are represented without inferred attack rules or a database rebuild.
Future Weapon comparison views remain out of scope.

**Silent / Attribute-Immunity source disclosure, 2026-10-31:**
`tests/test_silent_immunity_source_scope.py` pins English and Spanish
N5.3 PDF bytes and selected printed pages (14/95/175 and 14/99/182),
plus the three supplied FAQ input hashes. The source checks separate
opposing Rolls from Saving Rolls, retain the bilingual Face to Face
qualifier difference and bound the FAQ term inventory to those exact inputs.
Source/stored/API assertions verify visible Clarifications, canonical links,
primary citations and the explicit `scope-unclear` marker on Silent, with
links from Immunity and Silenced Pistol. Nine Chromium checks at 1440/390/320
px cover those ordinary pages, visible uncertainty, keyboard-accessible
marker help, page/request errors and overflow. The Immunity browser module
now has 66 cases; its 23 typed interactions remain unchanged. Maintained-text
auditing retains zero unlinked candidates/residuals and one explicit marker.
The synchronized rules/publication pair retains all 17 objects and recovery
copies; this is local disclosure acceptance, not an authoritative ruling.

**BTS partial-component Immunity examples, 2026-10-31:**
`tests/test_immunity_bts_component_exceptions.py` pins N5.3 pp. 63–65,
67, 95–96, 177 and 182, exact Army Weapon identities and Ammunition
IDs 30/5. Source, stored-rule and public API checks distinguish
Immunity (Shock) leaving AP/BTS/2 from Immunity (E/M) leaving Normal/BTS.
Earlier AP-only, full-BTS and Critical cases remain separate; the Weapon
API retains its original profiles. Mutations reject altered scope,
components, source values, outcomes and evidence, including Boolean/float
Saving Roll counts. Six new Chromium checks at 1440/390/320 px verify
the explanations, remaining Wound possibility, unchanged extra Critical
roll, canonical links, API agreement, errors and overflow. The full Immunity
browser module reached 57 cases in that batch, with 23 reviewed interactions.
Coordinated rules/publication promotion retains all 17 deployed objects
and recovery copies; this remains local acceptance.

**Five combined-form Critical-Immunity examples, 2026-10-31:**
`tests/test_immunity_combined_critical_completion.py` independently pins
the N5.3 PDF, exact chart rows and Army profiles for AP+EXP CC Weapon,
Silenced Pistol (AP+Shock) and E/M CC Weapon (N+E/M). It checks authored,
stored and public API cases while preserving source Saving Roll fields
and ordered component references. A corpus assertion requires one exact
example per reviewed combined form (IDs 5/10/13/30/40); it is not a
general Weapon/target completeness verdict. Mutation tests reject altered
Weapon, Comms scope, source ID, components, roll counts, Attribute,
Critical suppression and evidence. Nine additional Chromium checks at
1440/390/320 px verify the three new explanations, conditional Shock/E/M
effects, canonical links, source API parity, request/page errors and overflow.
The shared renderer covers 21 reviewed interactions; the full Immunity
browser module reached 51 cases in that batch. Rules/publication refresh preserves all 17
deployed objects and recovery copies. Final release acceptance stays separate.

**Silenced Pistol / Immunity (BTS), 2026-10-31:**
`tests/test_immunity_bts_silenced_pistol.py` pins English N5.3
pp. 63, 65, 67, 95–96, 175 and 182 and checks the exact Army
AP+Shock/BTS/2 profile against the seventh fixed combined case.
Source/API parity preserves the original Weapon profile and the
AP-only case: BTS Immunity covers both components and retains one
full-BTS Saving Roll, plus the extra Critical roll unless Immunity
(Critical) applies. Shock's special effect is ignored; ordinary failed
Normal rolls can still inflict Wounds; Silent's separate reaction
mechanic is linked without adjudicating its Immunity interaction.
Closed-schema mutations reject altered applicability, components,
source values, outcomes and evidence. The shared renderer and Chromium
at 1440/390/320 px verify the eighteenth interaction, canonical links,
API agreement, request/page errors and overflow. The coordinated
rules/publication refresh retains all 17 reviewed deployed objects
and recovery copies. This is local acceptance, not hosted release approval.

**Oblivion Comms exception / Immunity (State), 2026-10-31:**
`tests/test_immunity_oblivion_comms.py` pins English
N5.3 pp. 57–58/95, checks the curated Oblivion
program's Comms Attack, AP Ammunition, BTS Saving
Roll, Non-Lethal and Isolated effects, and verifies
the exact `reviewedCommsCases` publication on
the Immunity Skill API. It distinguishes ordinary
Immunity (BTS), which does not protect against
Comms Attacks, from Immunity (State: Isolated),
which prevents the State without suppressing the
attack Saving Roll. Burst 2 is checked as attack
dice, not an inferred number of Saving Rolls.
Fail-closed curated mutations reject identity,
Comms scope, sourced effects, Burst, exception
mechanics or evidence drift. Chromium at
1440/390/320 px checks the seventeenth Skill
card, canonical Program/State/Ammo/Trait links,
and layout. Coordinated staged rules DB and
deployed-object publication retain all 17
reviewed objects with a recovery backup.

**E/M Grenade Launcher / Immunity (BTS), 2026-10-31:**
`tests/test_immunity_bts_em_grenade_launcher.py`
pins N5.3 pp. 64, 95–96 and 179 and independently
checks the exact non-Comms, Non-Lethal source
E/M Weapon profile (BTS/2 × 2) and source
Ammunition ID 14. It verifies the fifth fixed
`reviewedWeaponCases` record through curated
data, `rules.db` and the Skill API without
modifying Weapon source Saving Rolls or
interpreting template placement. Fail-closed
schema mutations reject an altered Weapon,
Comms classification, source ID, roll
counts/attribute, independent Traits and
source evidence. Renderer and Chromium checks
at 1440/390/320 px cover the sixteenth reviewed
card, conditional State suppression,
Non-Lethal exemption and semantic links.
Coordinated DB/publication promotion preserves
17 reviewed deployed objects and rollback backup.

**AP+DA CC Weapon / Immunity (Critical), 2026-10-31:**
`tests/test_immunity_ap_da_critical.py` pins N5.3
pp. 67, 95 and 177 and Army source Ammunition
ID 10 AP+DA, ARM/2 × 2 with Anti-materiel and CC
Traits. It independently validates two Saving Rolls
per hit, three on a Critical, and two with Immunity
(Critical), preserving AP halving and the original
Weapon API. The second exact `reviewedCriticalCases`
entry fails closed on modified identity, source
components, roll count, Attribute, evidence or
Comms status. Chromium at 1440/390/320 px checks
the fifteenth card, semantic links and mobile
layout. Coordinated staging/promoting keeps
`rules.db` and deployed-object publication
synchronized, with 17 reviewed deployed objects
unchanged and recovery backup available.

**AP+T2 CC Weapon / Immunity (Critical), 2026-10-31:**
`tests/test_immunity_t2_critical.py` pins N5.3 pp. 63,
67, 95 and 177 and the exact Army `AP+T2`/ARM/2
source profile (Ammunition ID 40). A new fixed
`reviewedCriticalCases` record distinguishes the
original failed T2 hit roll (2 Wounds) from the
suppressed additional Critical roll (potentially
1 Wound) without cancelling AP halving or modifying
the Weapon API. The curated validator fails closed
on unsupported identities, conditions and outcomes.
The Skill renderer and Chromium acceptance at
1440/390/320 px verify the separate fourteenth
case with no overflow. The synchronized `rules.db`
and deployed-object publication retain 17 reviewed
objects and a local rollback backup; this is not an
attack-calculation engine.

**Plasma Combined Saving Roll / Immunity (Critical), 2026-10-31:**
`tests/test_immunity_plasma_critical.py` checks English
N5.3 pp. 67, 95 and 96 against the pinned PDF, the
exact Plasma Rifle Army Combined Saving Roll annotation,
and the new, separately rule-derived Skill API case.
It proves a Critical requires two ARM + one BTS rolls
without Immunity (Critical), but one ARM + one BTS
with the Immunity. It rejects any implied attack
resolution or changes to the Weapon profile.
The curated mutation suite rejects altered rolls,
applicability, result or source classification.
`tests/test_immunity_combined_saving_roll_example.py`
continues to verify the distinct printed Enhanced
example; the renderer and Chromium check the
thirteenth case at 1440/390/320 px. Coordinated
`rules.db`/deployed-object publication staging
retains all 17 reviewed objects with recovery backup.
Full CI and hosted deployment remain separate.

**Immunity printed Example 4 PDF provenance, 2026-10-30:**
`tests/test_immunity_flash_pulse_pdf_example.py` verifies the
pinned N5.3 English pp. 95–96 and 186, the published Flash Pulse
source profile (STUN, one BTS roll, Non-Lethal, State: Stunned)
and the direct Example 4 evidence classification in maintained
curated data, `rules.db` and the Skill API. The Spanish Wiki
two-roll / missing-State discrepancy remains source-noted,
not imported as a Weapon profile mutation. The same test
audits distinct pinned PDF labels for all four printed p. 96
Immunity examples. The maintained-text renderer and Chromium
at 1440/390/320 px check the Example 4 evidence label and
conditional State exception, without changing the twelve-case
count. Coordinated rules/publication promotion retains the
17 reviewed deployed objects and rollback backup.

**Missile Launcher / printed Immunity (ARM) Example 1, 2026-10-30:**
`tests/test_immunity_missile_launcher_example.py` verifies
the pinned N5.3 pp. 95–96/187, differentiates Blast
(EXP/ARM × 3, Circular Impact Template) from Hit
(AP+EXP/ARM/2 × 3) Army modes, confirms the
fourth source-scoped `reviewedWeaponCases` record
in curated rules, `rules.db`, and the Skill API,
and ensures both Weapon profiles retain their
imported source fields. Curated mutation tests
reject changed mode, Immunity category, source
Ammunition, Saving Roll count, Traits, and
derived evidence. The JS and Chromium renderer
at 1440/390/320 px verifies the twelfth case,
mode exclusion, source label and links, with
no horizontal overflow. The existing rollback-
aware `tools/stage_immunity_plasma_saving_roll.py`
rebuilds and promotes the synchronized DB and
deployed-object publication, retaining all 17
reviewed objects. This is not an attack evaluator
or a universal Weapon Trait ruling.

**Monofilament / printed Immunity (ARM) Example 2, 2026-10-30:**
`tests/test_immunity_monofilament_example.py` pins N5.3
pp. 95–96/177, confirms the Normal Ammunition, ARM=0,
one-roll and State: Dead source Weapon profile, and verifies
the third source-scoped `reviewedWeaponCases` entry through
`rules.db` and the Skill API. The source Weapon API does
not inherit a calculated Immunity outcome. Curated mutation
tests fail closed on changed Weapon, category, source Traits,
roll counts and death-State behavior. The JS renderer and
Chromium at 1440/390/320 px verify the eleventh case,
source label, semantic links and no overflow. The existing
rollback-aware `tools/stage_immunity_plasma_saving_roll.py`
promotes the synchronized database/publication pair; all
17 reviewed deployed objects remain unchanged.

**AP+T2 CC Weapon / partial Immunity (AP), 2026-10-30:**
`tests/test_immunity_ap_t2_cc.py` checks the pinned English
N5.3 pp. 63, 67, 95–96 and 177, the exact Army AP+T2
source Ammunition ID 40 and its ARM/2 × 1 source profile,
and the canonical T2 **2-Wound hit versus 1-Wound extra
Critical** distinction. The sixth Combined Immunity case
retains T2 and its two distinct conditional failed-roll
consequences while ignoring AP's halving only. Closed-schema
mutations reject unrelated Weapons, Comms scopes, altered
counts/Attributes, lost T2 components or reversed Wound
assignments. `tests/test_verify_immunity_plasma_browser.py`
covers the tenth Immunity card at 1440/390/320 px,
including conditional wording, semantic links and no
horizontal overflow. `tools/stage_immunity_ap_t2_cc.py`
stages and promotes synchronized `rules.db`/deployed-object
publication with recovery backups, keeping all 17 reviewed
deployed objects unchanged and Army Weapon profiles intact.

**Silenced Pistol / partial Immunity (AP), 2026-10-30:**
`tests/test_immunity_ap_silenced_pistol.py` pins English N5.3
pp. 63, 65, 67, 95–96, 175, 182, exact Army source
Ammunition 30 (`AP+Shock`) and the published Silenced Pistol
BTS/2 × 1 Weapon profile. The fifth typed Combined Ammunition
case retains Shock's VITA=1 failed-save effect and separately
conditional Silent (-6) when AP is ignored. Curated mutations
reject changed Weapon identity, Comms scope, source components,
roll counts, BTS attributes and retained Shock. Public
Immunity API and Chromium at 1440/390/320 px verify
the ninth reviewed case without altering Weapon profile data.
The synchronized rules DB/deployed-object publication uses
`tools/stage_immunity_ap_silenced_pistol.py`, retaining all
17 reviewed objects with recovery backups.

**Standalone E/Mitter / Immunity (BTS), 2026-10-30:**
`tests/test_immunity_bts_emitter.py` pins N5.3 pp. 64, 95–96
and 186, standalone Army weapon 25 / E/M source 14, and the
distinct Armed Turret one-roll discrepancy (weapon 226).
It proves the source-backed one-BTS-roll result with surviving
Non-Lethal under Immunity (BTS) without modifying either
Weapon API profile. The curated validator rejects unsupported
weapon IDs, source Ammunition, Comms scope, altered roll counts,
suppressed Non-Lethal and mislabeled evidence. The eighth
player-facing Immunity card, source/restriction text and links
pass real Chromium at 1440/390/320 px. Coordinated rules
database/publication staging and promotion in
`tools/stage_immunity_bts_emitter.py` retains 17 deployed objects
and recovery backups. This is not a Comms/immunity evaluator
or an Armed Turret adjudication.

**BTS Immunity / E/M CC Weapon, 2026-10-30:**
`tests/test_immunity_bts_em_cc.py` verifies the pinned N5.3
pp. 64, 67, 95–96 and 177 excerpts, exact Army E/M CC Weapon
source identity and BTS/2 × 2 profile, fourth source-scoped Immunity
case, API publication and preservation of Weapon profile fields.
Curated mutations reject unrelated weapons, Comms Attack scope,
source/component changes and unsupported roll results. The
coordinated stage/promotion in `tools/stage_immunity_bts_cc.py`
checks the exact record and preserves all 17 deployed objects
with a rollback backup.
`tests/test_verify_immunity_plasma_browser.py` also covers this
seventh reviewed interaction at 1440/390/320 px, with links,
source-scope labeling and no overflow or JS errors. This is local
acceptance, not a generic Immunity calculator or deployment check.

**Immunity/Plasma Combined Saving Roll example, 2026-10-30:**
`tests/test_immunity_combined_saving_roll_example.py` checks the
pinned English N5.3 p. 96 Example 3, the exact Plasma Rifle Army
Combined Saving Roll profile, canonical Immunity facts and Skill API,
and absence of any invented runtime Weapon immunity evaluation.
`tests/test_curated.py` mutates the reviewed example's conditions,
roll attributes, result, evidence and multiplicity to verify the
closed contract. The six-case maintained-text renderer is tested
with `tests/immunity_cases_render_harness.mjs` through the
focused `test_web.py` regression. A coordinated database/publication
promotion retains all 17 existing deployed objects.
`tests/test_verify_immunity_plasma_browser.py` verifies the sixth case
at 1440, 390 and 320 px with its source label, semantic links,
no invented Critical outcome, and no horizontal overflow or JS errors.

**Ammunition reviewed-source publication parity, 2026-10-30:**
`tests/test_ammunition_publication_parity.py` verifies the 11 published
base Ammunition identities, 16 current reviewed Army source IDs/names,
five ordered combined identities, canonical rules citations/summaries,
all 16 profile-to-rule entry points, and representative HTTP Weapon
details for all five combinations. The test pins N5.3 p. 67's three
printed combination examples independently of the Army config and
confirms the distinct Combined Saving Roll source section. This
does not infer attack roll arithmetic, immunity precedence or comparison
results from composition.

**Reinforcements applicability gate, 2026-10-30:** The tracked
`tests/test_audit_reinforcements_applicability.py` checks exact N5.3
p. 6 and ITS18 v2026.09.01 p. 27 PDF references, pinned historical
N4 English/Spanish PDFs, source-only Commlink/Request classifications
and preservation of the 57-row Core Orders/AROs reference. Mutations
of the source excerpts, versions, IDs, or an attempt to assert current
N5 procedural authority fail validation. This is a source-identity
gate only; the N5-applicable annex revision or explicit adoption
ruling remains unresolved. Neither legacy Skill was published to
`rules.db`.

**Bilingual Fireteam FAQ follow-up, 2026-10-29:** The tracked
`test_fireteam_faq_source_omission_is_not_a_contradictory_ruling`
checks English v0.1 printed p. 3's FT Master exception against the
Spanish omission and the reviewed `skill:ft-master` restriction.
The selected FAQ still carries both language citations, with no
conflicting citation for that omission. The adjacent Haris Type
example retains its real numerical conflicting citation. The source
review changed only the required-member ruling's `selectionReason`;
effective date, selected source, gameplay and scenario scope remain
unchanged.

**FAQ topic/reference applicability matrix, 2026-10-29:** The
`test_published_faq_all_topic_links_preserve_selected_scope_and_history`
regression traverses all 48 authored topic associations for 29 current
reviewed FAQ rulings (42 unique topics) against a fresh curated rules
database. Each topic is queried with no scenario, Annihilation,
Supplies and Firefight; selected answers are compared with source
records and their provenance/citation/scope. All topics are separately
checked at the 2025-10-15 historical source anchor, the 2026-08-31
pre-effective boundary and the non-reviewed 5.2 revision; current
v0.1 rulings must be absent. The focused regression passed. This is
a current-source selector/association gate, not historical v0.0 replay
or a certification of deferred ITS-specific applicability.

**All-topic FAQ browser entry-point regression, 2026-10-29:**
`test_faq_browser_routes_cover_every_published_topic_association`
guards exactly 48 published topic/ruling associations across 42
topics, including the 19 associations outside the existing primary
29-ruling route matrix. The paired
`test_every_additional_faq_topic_link_is_visible_from_its_normal_page`
verifies normal Chromium publication at 1440/390 px from each of
17 additional topic owners, including embedded Fireteams/Scenario
rule topics on their owning pages. Questions, answers and selected
citations must render. The original primary 25 routes remain a
separate 8-check gate. These tests verify bounded discoverability,
not click-path ranking, touch acceptance or historical/ITS editions.

**Player-facing FAQ source selection/conflict gate, 2026-10-29:**
`test_fireteam_faq_discloses_real_source_conflict_not_language_omission`
covers desktop/mobile Fireteams (1440/390 px). The 29-record source
inventory contains exactly one numerical conflict: the Haris member
example. The normal FAQ card shows its selected English v0.1 citation
and source date anchor, and the expandable warning shows the actual
selection rationale with a Spanish alternative PDF citation link.
The FT Master qualifier omission remains visible in the selected
English answer and does not produce a false contradiction warning.
Both the 29 primary and 19 secondary browser topic associations now
also assert selected English source, version and source-date labels.
This is bounded current-publication presentation proof, not final
hosted release acceptance or independently dated historical replay.

**Release-tracked FAQ database parity (opt-in):**
The ordinary source/API/Chromium FAQ tests use a freshly built rules
database, which cannot detect a stale checked-in binary. The opt-in
`test_tracked_faq_database_matches_current_curated_release_projection`
compares the tracked `data/generated/rules.db` with a fresh curated
export: exact 29-rule record facts, source/citation metadata and
168 topic/scenario query projections (42 topics in four contexts),
with independent pre-effective-date and N5.2 exclusions. It never
rewrites the artifact.

Run this gate after rebuilding the tracked rules artifact, and repeat it
against the final frozen release candidate. Normal development checks skip
this release-only gate:

```powershell
.venv\Scripts\python.exe -m infinity_db build-rules --output data/generated/rules.db
$env:INFINITYDB_RELEASE_FAQ_PARITY = "1"
try {
    .venv\Scripts\python.exe -m pytest tests/test_faq_ruling_references.py::test_tracked_faq_database_matches_current_curated_release_projection -q
} finally {
    Remove-Item Env:INFINITYDB_RELEASE_FAQ_PARITY -ErrorAction SilentlyContinue
}
```

**Rebuild dependent publication before testing the release pair.**
The tracked rules DB hash also anchors the ignored
`data/generated/deployed-objects.json`. Regenerate and verify that
publication whenever either runtime database changes; application startup
rejects a mismatched pair. Run:

```powershell
.venv\Scripts\python.exe -m tools.build_deployed_object_publication
.venv\Scripts\python.exe -m tools.build_deployed_object_publication --check
```

Then opt in with `INFINITYDB_RELEASE_FAQ_PARITY=1` for the tracked
FAQ browser cases in `tests/test_verify_scenario_faq_browser.py`:
`test_release_faq_primary_entry_points_use_tracked_database`,
`test_release_faq_secondary_entry_points_use_tracked_database`, and
`test_release_faq_haris_conflict_uses_tracked_database`.
They exercise the same 29 primary/19 secondary association cards
and bilingual conflict disclosure at 1440/390 px, using the
**tracked** Army and rules databases rather than a temporary build.
These are opt-in release-candidate tests; ordinary tests skip them.

Review the tracked binary diff and validate the release-matched
database/Army pair with the normal asset and release gates before
committing. Neither the parity nor local browser checks validate an
actual deployed release or authenticate external source bytes.

**Current-source temporal gate regression, 2026-10-29:**
`test_current_faq_temporal_gates_are_independent_for_all_published_rulings`
asserts all 29 current rulings appear at their N5.3 2026-09-01
reference-date anchor, not the previous day, at the v0.0 origin
anchor, or under N5.2. It shifts each of the four independently
enforced date gates into the future in isolated in-memory copies:
selected source, original source, owning collection and ruling
applicability. Each blocks the earlier query and permits the next
day; scenario-specific cases retain their explicitly reviewed
scenario context. This guards the 1.0 current-reference selector
without backdating records or authorizing historical replay.

**Carried-forward FAQ meaning regression, 2026-10-29:** The
`test_carried_forward_v00_faq_answers_retain_reviewed_v01_semantics`
compares reviewed semantic anchors of all 20 v0.0-origin published
answers against current curated v0.1 text, including the original and
selected English printed-page citations. The anchors were reviewed
against both pinned English FAQs. This is an audit-only source wording
gate: it does not read the ignored PDF bytes in CI, grant historical
publication, or certify Spanish/ITS translation and applicability.

**Bilingual review of 20 carried-forward answers, 2026-10-29:**
`test_carried_forward_v00_faq_bilingual_pages_and_question_scope`
checks all 20 pinned Spanish printed-page positions, v0.0 origin and
selected v0.1 English citation, no conflicting answers, N5.3 date
gates and the Supplies-only scenario exception. English and Spanish
source comparison found the Spanish Stealth/ARO question adds an
outside-ZoC/Hacking-Area qualifier absent from the English question;
the answers remain compatible. The selection rationale and test
document this as a context difference, not a conflicting ruling or
generalization to other positions. This is a current-reference
source review, not automated PDF extraction or historical replay.

**Nine new FAQ v0.1 answers, 2026-10-29:**
`test_new_v01_faq_answers_retain_reviewed_bilingual_source_semantics`
checks all v0.1-origin published answers with independent semantic
anchors and bilingual printed-page pins reviewed against local English
and Spanish PDFs. It retains English selected-source provenance,
current N5.3 reference-date gates, the Annihilation-only Ancillary
scope and the one explicit Haris numerical conflict. The Spanish
FT Master qualification omission and broader Deployable placement
question remain non-contradictory source differences. Tests use
tracked evidence; they do not fetch ignored PDF bytes in CI or
implement historical replay.

**FAQ public-copy encoding regression, 2026-10-29:**
`test_published_faq_copy_has_no_corrupted_question_mark_possessives`
checks the 29 current FAQ question/answer strings for accidental
replacement question marks, anchors the five apostrophes recovered
from the English FAQ sources, and verifies the English v0.0 PDF
title. It guards presentation fidelity only: it does not certify
full historical answer wording or translation equivalence.

## 1.0 FAQ v0.1 pilot acceptance

**Verified 2026-10-15 on `dev/v1.0.0`.** The
`data/curated/rules/n5-faq-v0.1.json` source collection retains a
general Hacking Device Firewall ruling (English and Spanish FAQ p. 1)
and a scenario-scoped undeployed Peripheral (Ancillary) Killed ruling
(English and Spanish FAQ p. 4), both selected from English FAQ v0.1,
with a separate Spanish source citation. The pinned `publishedDate`
is the project's official 2026-09-01 N5.3/FAQ announcement-era
source anchor; it is not evidence of an independently dated FAQ
document publication. The scope is deliberately restricted to the
published Annihilation scenario for the second pilot.

Tests verify all three curated collections export to the current Rules
database, both FAQ identities and provenance survive the public API,
date/revision/scenario restrictions hide nonmatching rulings, and base
rules remain unchanged. Browser acceptance with a fresh WSGI instance
passes **6/6** source cards on Hacking Device and Annihilation at
1440, 390, and 320 px, with no page-level horizontal overflow or
JavaScript errors. Domination does not show the Annihilation-only
pilot. Private checker:
`local/audits/verify_faq_pilot_browser.py`.

The browser deliberately uses explicit FAQ v0.1/N5.3
`as_of=2026-09-01` reference context rather than guessing from the
user's clock. This confirms two published examples, not the
complete FAQ inventory, ITS season-specific verification or historical
edition selection.

## 1.0 FAQ v0.1 general clarification expansion

**Verified 2026-10-15 on `dev/v1.0.0`.** Six additional
source-reviewed records expand the existing FAQ pilot to eight:
Skill declaration / target position (EN/ES p. 1);
fired Deployables on vertical surfaces (EN p. 1 / ES p. 2);
Peripheral actions with a restricted Controller (EN/ES p. 2);
Camouflaged Marker in Total Cover (EN/ES p. 3);
Special Dice and Coordinated Orders (EN p. 2 / ES p. 3);
Fireteam creation minimums after member loss (EN/ES p. 3).
These entries were not present in the available pinned English
FAQ v0.0 PDF. All retain original v0.1 identity, dated source
citations, explicit N5.3 applicability and an independently reviewed
Spanish page even where pagination differs.

Added an API/database parametrized regression for the seven
affected canonical topic IDs, including `rule:special-dice`
as a second route to the same Special Dice ruling. The shared FAQ
presentation is reused by Skill, Trait, State and General Rules
details. The Fireteam ruling belongs to the Fireteams quick
reference/Army chart surface, not a fabricated General Rules URL.

Private headless-browser verifier
`local/audits/verify_faq_expanded_browser.py` tested six real
reference pages across desktop 1440 px and narrow 390/320 px.
**18/18 checks passed:** the expected question, answer, source
version/date/link and one FAQ card per page, with no JavaScript
exceptions or page-level horizontal overflow.

At that batch's date the Fireteam Type example was unpublished. It has
since been published using the consistent English HARIS example with a
separate Spanish-count discrepancy, as described in the
[current FAQ contract](data-model.md#dated-faqerrata-layer-published-reviewed-subset).
The batch alone does not establish complete FAQ/ITS historical coverage.

## 1.0 FAQ v0.0 carry-forward provenance and presentation

**Verified 2026-10-15 on `dev/v1.0.0`.** Eight additional
N5 FAQ entries were compared against English FAQ v0.0,
English FAQ v0.1, and Spanish FAQ v0.1, bringing the authored
current FAQ collection to **16**. The carried-forward records preserve
their original v0.0 printed pages/version separately from the selected
current v0.1 source and independent Spanish v0.1 citations. No canonical
rules, Skills or Army source data are rewritten.

Source boundaries include the separate English v0.0/v0.1 printed
pages for Place Deployable and Surprise Attack (1/2), the
historically associated but not independently confirmed
2025-10-15 v0.0 source date, exact N5.3-only current
applicability, and no automatic ITS season applicability.
Eight parameterized regressions verify source triplets,
original/current versions, applicable dates and revisions;
an additional count test ensures 8 current v0.1-origin and
8 carried v0.0-origin identities without duplicates.

Private headless-browser checker
`local/audits/verify_faq_carried_forward_browser.py` tested
**33/33** topic views (eight primary reference pages plus three
additional multi-topic/cross-link pages, each at 1440/390/320 px),
including the selected v0.1 citation, earlier v0.0 source label, and
two separate rulings on Jump without duplicated identities;
no JavaScript errors or horizontal overflow.

**Limit:** This batch does not complete the original v0.0
inventory, season-scoped ITS rulings, historical FAQ edition
replay, or the unresolved bilingual Fireteam-type example.

## 1.0 remaining general FAQ v0.0 carry-forward acceptance

**Verified 2026-10-15 on `dev/v1.0.0`.** Ten further source-reviewed
general FAQ v0.0 rulings are carried into v0.1 with three citations
per record: English v0.0 origin, selected English v0.1, and Spanish
v0.1 at their own printed pages. Published FAQ count: **26**,
including 18 carried and 8 introduced in v0.1. All new entries
retain explicit N5.3/date applicability; ITS-only material and
general Deployment Phase repositioning remain out of this batch.

Added 10 source/applicability regression cases and cross-topic
identity checks for Minelayer/Decoy/Holoecho, Controlled Jump/
Speedballs, Aerial/Boost, Discover/Fireteam, and
Disconnected/Unconscious. Browser integration now displays the
same dated FAQ component on the Controlled Jump Hacking Program
page and composes Fireteam general/bonus-related rulings without
duplicating their IDs.

Private browser checker `local/audits/verify_faq_remaining_general_browser.py`
passed **36/36** views across 12 reference paths at 1440/390/320 px,
checking selected FAQ version, historical source note, relevant
question/answer, JavaScript errors and horizontal overflow. Canonical
rules and Army profile source data remain unchanged.

## 1.0 exact current scenario publication selection

**Verified 2026-10-15 on `dev/v1.0.0`.** The shared scenario catalog
and list/detail/SVG-map endpoints now support paired exact
`collection` and `revision` selectors. Current N5 Core
`n5-core@5.3` still exposes its four published scenarios, while
`its-18@2026.09.01`, `its-17@2025.09.01`, and uninstalled
`n5-core@5.2` selections produce empty lists or HTTP 404,
never substituted Core data. Missing, malformed, repeated and
unknown selector parameters return HTTP 400. Legacy requests
without selectors remain supported.

`tests/test_scenario_catalog.py` includes an explicitly synthetic
Season 18 publication-metadata fixture, testing exact filtering
without authoring false scenario rules. `tests/test_scenario_api.py`
checks corresponding list/detail/map behavior, provenance and
negative API cases, including a correctly scoped N5.3 map.
No actual ITS mission, FAQ ruling, extra geometry or
historical edition is published by this API milestone.
Browser season choice and season-aware share URLs await the
first source-complete ITS scenario definition.

## 1.0 Deployment Phase owner and ITS applicability audit

**Verified 2026-10-15 on `dev/v1.0.0`.** A new official N5.3
General Rules identity `rule:deployment-phase` uses core PDF
printed p. 15 for the phase sequence. The v0.0-origin FAQ
repositioning clarification (v0.0 EN p. 1; selected v0.1
EN/ES p. 1) attaches to that general rule, not an arbitrary
deployment Skill. FAQ inventory is **27** (19 v0.0 origins
and 8 v0.1 origins). The independent rule review gate is
**180/180** supporting identities complete.

`tests/test_faq_ruling_references.py` verifies N5.3
source identity, original and current FAQ citations, precise
phase versus Minelayer topic selection and negative date/
revision cases. The normal rules export confirms current
target integrity. The private responsive browser verifier
`local/audits/verify_deployment_phase_faq_browser.py` checks
the new `/rules/deployment-phase` card at 1440/390/320 px
and confirms that the general repositioning ruling does not
appear on `/skills/minelayer`.

A separate pinned English FAQ v0.0/v0.1 and ITS Season 18
source audit verified Area of Interest, Crossing Lines and
Akial Interference mission references, but did **not**
publish their ITS-only FAQ answers into the current N5 Core
catalog. The missing season/missions publication is a
real dependency, not grounds for dropping applicability
restrictions. Private evidence is in
`local/audits/faq-its-season18-source-scope-20261015.md`.

## 1.0 Visibility Zone and Ammunition/Immunity browser acceptance

**Verified 2026-10-15 on `dev/v1.0.0`.** Headless Chromium used a freshly
rebuilt rules database from current curated sources and the current Army
snapshot. **469/469 browser checks passed** across 1440, 390 and 320 px,
including Normal, DA, Shock, Smoke, Eclipse, AP, E/M and T2 Ammunition;
Immunity, Sixth Sense, Multispectral Visor and Reflective reference cards.
The test activated Visibility Zone/Zero Visibility Zone/Poor Visibility
references, cross-links from Smoke and Eclipse, and the Immunity links
to Normal, AP and DA. It verified actual Glossary hash targets after
asynchronous loading and canonical rule-page destinations, not only
that anchors existed in response data.

For representative references at each viewport, hovering opened a readable
preview, keyboard focus exposed the same preview and Enter followed the
link. A real touch-enabled 390 px context confirmed first-tap preview,
second-tap navigation on Visibility Zone, Smoke/Eclipse and Immunity
examples. Preview text and on-screen horizontal bounds were checked;
no page-level overflow or JavaScript exceptions occurred.

The existing **6 px overflow** at 320 px was reproduced independently
on Normal, DA, Shock, Smoke and Eclipse Ammunition before the fix;
`.catalog-tag` extended beyond the right edge. The shared narrow
breadcrumb now wraps with reduced spacing while the existing reference
tag remains visible. Post-change checks found zero horizontal overflow
at all tested widths on these pages and other rule-reference surfaces.
A served-CSS regression test protects the narrow layout contract.
The 320 px Smoke screenshot was reviewed for readability.

Private browser scripts, screenshots and check results remain ignored in
`local/audits/visibility-ammunition-browser/`. This closes the specific
browser interaction/layout gate; it does not close the final 1.0 source
completeness gate or change any curated rules interpretations.

## 1.0 five Visibility Zone Game terms browser acceptance

**V1-A08 follow-up (2026-10-31).** The maintained evidence crosswalk at
`config/validation/visibility-zone-terms-v1.json` lists the five current
`term:*` identities, their reviewed N5.3 p. 144 definitions, exact
`/glossary#term-*` routes, source clause excerpts in English p. 144 and
Spanish p. 148, and existing API/source regressions. The frozen
historical 367-record D/S denominator is not changed. Reproduce the
selected bilingual-source and identity audit with:

```powershell
.venv\Scripts\python.exe -m tools.report_reference_baseline --reconcile-explanation-inventory --audit-visibility-zones --verify-visibility-pdfs --json-output local/audits/v1-visibility-zone-reconciliation.json --markdown-output local/audits/v1-visibility-zone-reconciliation.md
```

The audit rejects changed identities, curated clauses, citation pages,
Glossary targets, evidence scope and source hashes. New Chromium tests
exercise all five current normal-mode Glossary URLs at 1440/390/320 px;
the historical acceptance below remains useful independent evidence.
The generated reports reside in ignored `local/audits/`. These checks
do not automatically approve all conditional MOD exceptions, every
related Skill, or the final 448-record source/presentation gate.

**Verified 2026-10-16 on `dev/v1.0.0`.** A freshly rebuilt rules database
was used with the current application and Army snapshot. The five
post-inventory N5.3 p. 144 Game terms (Visibility, Low, Poor, Zero and
White Noise Zones) were checked at 1440, 390 and 320 px, including
direct Glossary hash URLs, term descriptions, global-search result
links, pointer and keyboard reference previews, accessible tooltip
descriptions, actual keyboard navigation and focused hash targets.
An isolated touch-enabled 390 px context checked first-tap preview
and second-tap navigation from the shared term to all four variants.

The first full browser pass reported **314/314 passing interaction,
navigation and overflow checks**. During manual inspection of the
320 px White Noise screenshot, a sticky-navigation overlap was
identified: the heading was partly obscured. A separate browser
measurement confirmed the defect at both narrow widths. A responsive
Glossary scroll offset now clears the sticky navigation; the
post-correction narrow-screen pass reported **229/229 checks passed**,
including explicit unobstructed-heading assertions for every term
at 390 and 320 px. The corrected 320 px White Noise screenshot was
inspected and its heading is visible.

The same browser work also reproduced JavaScript errors when
a detached maintained-reference tooltip was reopened during
navigation. The shared preview code now ignores disconnected
elements, with a Node-based regression for a connected-to-detached
reference lifecycle. The accepted browser passes have no page errors
or horizontal document overflow. This closes the bounded five-term
browser interaction requirement, not the frozen 367-record source
review or the final 1.0 whole-corpus release gate. Private scripts,
screenshots, a rebuilt rules DB and check results remain under
ignored `local/audits/visibility-five-terms-browser/`.

## 1.0 Repeater/Cube source-to-browser enrichment reconciliation

**Verified 2026-10-15 on `dev/v1.0.0`.** The Repeater citation was checked
against the current N5.3 rules PDF (printed pp. 55-56), pinned English Wiki
Repeater and Hacking Area pages, and the archived Hacking Area oldid 3974.
The older revision remains separately preserved as historical source evidence;
Repeater's current reference now cites the Hacking Area page in the verified
English Wiki snapshot alongside the N5.3 rulebook and Repeater page. The
mechanics and imported Army Equipment values were not changed.

The `tools/audit_enrichment_coverage.py` baseline now uses the same
`EquipmentCatalog` as the published `/api/equipment` endpoints, covering Army
Equipment, profile-symbol-encoded Cube/Cube 2.0 and curated-only Firewall.
The rebuilt current-rules/Army enrichment audit reported **0 release blockers**
and **0 unresolved related-item links**. It still reports **81** Weapon
identities without standalone curated definitions plus the independently
classified older Flash Pulse citation; this is **not** overall 1.0 completeness.
A regression test checks public Equipment IDs and real Cube/Sepsitor relations.

Headless Chromium verified `/equipment/repeater`, `/rules/hacking-area`,
`/equipment/cube`, `/equipment/cube-2`, `/weapons/sepsitor`, and
`/weapons/sepsitor-plus` against rebuilt curated rules. **117/117** checks
passed at 1440/390/320 px and touch-enabled 390 px: content rendered,
semantic links showed reference previews, keyboard and touch navigation
reached the public destination, and no page-level horizontal overflow or
JavaScript exceptions occurred. The 320 px Repeater screenshot was reviewed.
Private source-inventory reports, browser results and screenshots remain in
ignored `local/audits/gate-1.0/`.

## 1.0 flagged source-field occupancy and Unit browser acceptance

**Verified 2026-10-15 on `dev/v1.0.0`.** The source-presentation audit was
rerun against the published Army database and its checksum-matched paired
normalized raw database. All **39** fields statically classified as
`unrepresented_player_information` were inspected for occupied source values.
**None was populated.** The original pinned Army ZIP was also checked directly:
its 59 JSON documents contain 4,137 source Unit occurrences, 4,748 profile
groups, 5,020 profiles and 162 top-level composite-option occurrences across
Army contexts; none supplies values for the flagged note or direct
Unit-option Skill/Equipment/Weapon/Characteristic fields. The seven
`unit_option_*` Skills, Weapons, Equipment, extras and Characteristics
relation tables contain zero rows; both
`profile_groups.notes` (4,748 groups) and `profiles.notes` (5,020 profiles)
contain zero nonempty values. The audit retains all 39 candidates rather than
misclassifying them as implemented; its new `rawEvidence.unrepresentedFieldOccupancy`
reports source row counts and occupied values by table/field, and summary
`occupiedUnrepresentedFieldCount` is `0` for this snapshot (or unknown if a
validated raw pair is unavailable). A synthetic populated source fixture
asserts that an occupied candidate is surfaced, including numeric zero.

The independently populated source structures have distinct semantics:
**18** composite Unit-option occurrences belong to **7** logical Unit pages,
and **30** source Unit-note occurrences belong to **28** logical Unit pages.
The current application DB projects included loadout relationships (322
Army-scoped target rows) and composite-option Order contributions (33 source
rows). The published API returns those fields in each owning Army context,
and renders them in normal Unit pages rather than treating absent direct
Unit-option Skill/Equipment/Weapon rows as missing presentations.

**510/510 source/API/browser acceptance checks passed.** Headless Chromium
checked actual option names, source unit/option IDs, points, SWC, resolved
included-loadout anchors, Orders, miniature counts and source notes, at
1440, 390 and 320 px. Every Army detail with composite options was opened
for the mobile table-width check. No JavaScript errors or document-level
horizontal overflow were detected. Visual inspection found that long
composite-option names were clipped inside a narrow card despite fitting at
document level; the mobile table body/name now wraps without truncating the
source label, and a served-CSS regression protects this presentation.
A separate dense Unit profile/loadout subrow overlap was also observed
at 320 px on Scylla during this review. That presentation defect was
subsequently corrected: normal profile Attributes, Skills, Equipment
and Includes stack at very narrow widths, and loadout names wrap above
Points/SWC. Follow-up served-browser inspection covered 320, 390, 400,
600 and 768 px. The layout correction is independent of the 39 absent
source fields and does not close the overall 1.0 browser gate.
Evidence, scripts and screenshots remain ignored under
`local/audits/gate-1.0/source-fields-browser/`.

This closes the **39-field review for the current pinned source set only**,
not the overall 1.0 release gate. A new Army source version may populate any
candidate and must be reaudited before tagging; the current report's zero
confirmed gap families does not independently prove browser completeness.

For subsequent Army snapshot reviews, the source-presentation audit has an opt-in
fail-closed occupancy gate:

```powershell
.\.venv\Scripts\python.exe tools/audit_source_presentation.py data/generated/infinity.db --require-no-occupied-gaps --output local/audits/source-presentation.json
```

This gate passes only when a checksum-matched raw source database is available
and none of the statically unrepresented fields has a populated value. It fails
if the raw pair is missing or any candidate becomes populated; inspect
`rawEvidence.potentialGapBatches` in the JSON report before deciding whether
the newly populated source semantics require application, API or browser work.

The normal check runner has an opt-in 1.0 release mode:
`python tools/run_checks.py --all --source-occupancy-gate`. It checks the
tracked release Army database and its raw sibling **before** the rules
interaction-review/build stage, failing that stage if the occupancy audit
fails. For focused rehearsal, use `--stage rules --source-occupancy-gate`.
This flag requires the rules stage and does not change the normal `--all`
workflow or hosted CI. Rebuild the published Army pair from the final pinned
snapshot before using this release gate. It does **not** replace the complete
1.0 source-to-storage-to-browser audit.

## 1.0 selected declaration-category source and browser reconciliation

**Verified 2026-10-16 on dev/v1.0.0.** BS Attack (p. 39), CC Attack
(p. 51), Discover (p. 77), Dodge (p. 79), Forward Observer (p. 92)
and Morpho-Scan (p. 103) were checked against their exact declaration
headings in the pinned N5.3 English rulebook. The first three have
corrected page-scoped declaration IDs and full Skill citations;
Morpho-Scan now has only a Short Skill mapping and the primary PDF
citation. Existing BS=11, BS=12 and CC=21 action-heading citations
were corrected without claiming validation of their numeric source
variants. The source-to-metadata tests verify the six actual headings
and prevent restoration of the eight retired ARO/Basic IDs.

A privately rebuilt current rules DB backed headless Chrome checks
of the four changed Skill pages at 1440, 390 and 320 px. **12/12
browser checks passed**, including the exact visible category badges
(BS/CC Short Skill + ARO, Discover Basic Short Skill + ARO and
Morpho-Scan Short Skill only), no JavaScript errors and no page-level
overflow. The Morpho-Scan 320 px screenshot was inspected for
readability. Private verifier, results and screenshot are ignored
under local/audits/declaration-source-browser/.

The frozen 367-record explanation audit was not renumbered. This is
selected declaration source/projection/browser verification, not
acceptance of every declaration option or any numerical replacement
variant, and not final whole-corpus acceptance.

## 1.0 Deployment and Long Skill source/browser reconciliation

**Verified 2026-10-16 on the current 1.0 development branch.**
Deployment and Long Skill declaration metadata was compared with
the exact headings in the pinned English N5.3 PDF (pp. 32, 34, 86,
89, 92, 95-97, 102, 105, 111 and 118). Three stale Deployment pages
were corrected and the shared Jump/Climb and Combat Jump/Parachutist
mappings split. The unchanged classifications of the other selected
source headings were checked in the same pass. Seven affected Skill
definitions now link to their relevant primary-source headings.

The resulting curated data exports 61 declaration-category records.
Focused tests verify page-scoped mappings, Skill type membership,
the pinned source headings and the new total of 461 published rules
database records. Headless Chromium checked eight Skill detail pages
(Infiltration, Impersonation, Hidden Deployment, Climb, Jump,
Combat Jump, Parachutist and Sapper) at 1440/390/320 px:
**24/24 checks passed** for visible declaration badges, absent
inapplicable ARO/Basic badges, HTTP responses, console errors and
document overflow. The private verifier, database, reports and
screenshots are under ignored local/audits/declaration-source-2/.

These are selected metadata and presentation acceptance results,
not a validation of the 367-record frozen explanation inventory,
conditional Climbing Plus/Super-Jump use, remaining declaration
families or whole-corpus release readiness.

## 1.0 Deployment-only Skills wrongly labeled Automatic

**Verified 2026-10-16 against the pinned N5.3 English PDF.** Booty
(p. 86), Decoy (p. 90), MetaChemistry (p. 101), Remdriver (p. 110)
and Strategic Deployment (p. 112) each use an explicit Deployment
Skill heading, not an Automatic heading. Their five independent
curated declaration mappings now point to the correct source
pages, while the owning Skills retain their existing mechanics and
prior Wiki revisions. Regression checks enforce the exact category
and page and pin the source PDF checksum.

A freshly built rules DB was checked in headless Chrome at 1440,
390 and 320 px. All five Skill pages displayed exactly one
Deployment category badge. **15/15 page checks passed** with no
JavaScript exceptions or document-level horizontal overflow.
Private evidence and the verifier are under ignored
local/audits/declaration-automatic-reconciliation/.

The current declaration catalog has 65 records and the rules
database has 465 total records. The frozen 367-record explanation
inventory was not modified; this is selected metadata/browser
acceptance only. Other Automatic category page mismatches and
training-vs-Skill attribution remain unreviewed.

## 1.0 Automatic Skill heading and Regular ownership audit

**Verified 2026-10-16 against the pinned N5.3 English PDF.**
Fourteen Automatic declarations were reconciled to source headings
on pp. 54, 87, 93, 95, 99, 103-104, 109-111, 113-114 and 116.
Regression tests pin the owning headings, the exact curated
page mappings and related Skill source citations. The unrelated
Regular/Automatic link was removed; canonical Training ownership
and the existing Order rules are preserved.

The catalog now has 28 Automatic groups and 63 total declaration
records; the exported rules database has 463 records. A freshly
rebuilt rules DB was used to verify fourteen public Skill pages
in headless Chrome at 1440, 390 and 320 px: **42/42 checks passed**,
with the expected Automatic badges and no page errors or horizontal
overflow. Private verifier, output and screenshots are stored under
ignored local/audits/automatic-page-reconciliation/.

This bounded acceptance does not sign off exceptional Automatic
activation, remaining Short Skill or named replacement-profile
semantics. The 367-record explanation-audit snapshot remains frozen.

## 1.0 Short Skill headings and Army replacement variants

**Verified 2026-10-16 against pinned N5.3 and the 2026-09-29 Army
snapshot.** Eleven current Short Skill declarations were screened
against the rulebook's exact headings. Sensor now cites p. 111
rather than p. 112 in both its declaration and full Skill definition.
The source-pinned test checks all eleven pages, while an unconditionally
runnable curated regression enforces the mapping.

BS=11 (Skill ID 279), BS=12 (278) and CC=21 (274) were checked
against the original ignored Army archive,
JSON 20260929-114335.zip, SHA-256
f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75.
The source has 59 JSON files and 2/9/6 loadout occurrences for those
identities respectively. Occurrences can repeat across factions;
the source-defined values are not independently named N5 core rules.
The core action references remain BS Attack p. 39 / CC Attack p. 51,
with general MOD/value notation context at p. 75. A dedicated
regression test checks dictionary IDs/names, unit-option occurrences,
and pinned archive digest; **that test skips if the gitignored source
archive is unavailable**, while the curated identity/parent tests
still run.

With a freshly rebuilt rules DB, the Sensor Skill page was tested
in headless Chrome at 1440, 390 and 320 px: **3/3 checks passed**,
including the Short Skill badge, no page errors and no horizontal
overflow. The private verifier, database, results and screenshot
remain under ignored local/audits/short-skill-numeric-provenance/.
The frozen 367-record audit is unchanged; the 1.0 whole-corpus
signoff and conditional permissions are still open.

## 1.0 conditional movement browser checks

**Verified 2026-10-16 against the pinned N5.3 PDF.**
Climbing Plus (p. 88) and Super-Jump (p. 113) retain
Automatic types; Climb and Jump retain Long Skill types.
Pinned source tests verify conditional Basic Short declaration,
trajectory, 360-degree LoF, Impetuous and Jet Propulsion.
The curated tests verify source references and restrictions.

The public Skill pages passed 6/6 headless Chrome cases at
1440, 390 and 320 px with no console errors or overflow.
Private evidence is in ignored local/audits/conditional-mobility-browser/.
This does not complete the frozen 367-record audit or whole-corpus 1.0 gate.

## 1.0 reactive combat Automatic Skill provenance

**Verified 2026-10-16 against the pinned N5.3 English PDF.**
Guard (p. 95, Optional), Neurocinetics (p. 104, Obligatory),
and Total Reaction (p. 116, Optional) have distinct trigger and
action restrictions. Pinned-source tests assert their original
headings and key restrictions; curated tests assert the source
pages, category labels and retained Wiki provenance.

Guard and Neurocinetics gained direct PDF citations. Neither
the underlying Skill mechanics nor the original 367-record
explanation-audit inventory changed. The rules database was
rebuilt and three published Skill pages were checked in headless
Chrome at 1440, 390 and 320 px: **9/9 cases passed**, showing
Automatic category badges without page errors or horizontal
overflow. Private evidence remains under ignored
local/audits/reactive-combat-browser/.

This is a selected provenance and browser check. It does not
cover combined Burst effects, every ARO eligibility condition,
or the final 1.0 whole-corpus acceptance gate.

## 1.0 Guard versus Aerial conditional eligibility

**Verified 2026-10-16 against the pinned N5.3 English PDF.**
Aerial p. 86 prohibits Guard against a non-Unconscious Aerial
target, independently of the Silhouette-contact exception in
Guard p. 95. Unconscious p. 172 disables Automatic Skills.
Against an Unconscious Aerial target, Guard's LoF and ZoC
requirements still apply.

A pinned-PDF test checks all three clauses. The curated
regression verifies the page citations, category types,
Aerial-owned restriction relation and conditional explanations.
A rebuilt rules DB powered headless Chrome checks of Aerial
and Guard at 1440, 390 and 320 px: **6/6 browser cases passed**,
with no JavaScript exceptions or page-level overflow.
Private evidence is under ignored local/audits/guard-aerial-browser/.

This closes the bounded Guard/Aerial exception review, not the
original frozen 367-record audit or full 1.0 acceptance gate.

## 1.0 Combat Instinct, Sixth Sense and Stealth ARO scope

**Verified 2026-10-16 against pinned English N5.3 pp. 20, 88
and 111-112.** A curated regression preserves optional Automatic
categories and the existing directed Stealth-counter relations,
with Combat Instinct's independent Surprise Attack modifier
exception. A SHA-256-pinned PDF regression checks Combat
Instinct's two clauses, Sixth Sense's attack-only outside-LoF
permission, Stealth's counter exceptions, and ordinary ZoC
reaction eligibility. Historical Wiki/FAQ citations remain
intact; Combat Instinct acquired a primary PDF citation.

A freshly built rules database was used in headless Chrome to
verify the Combat Instinct, Sixth Sense and Stealth Skill pages
at 1440, 390 and 320 px. **9/9 checks passed** for visible
Automatic badges, the newly authored scoped explanations,
source-counter names, HTTP response, no JavaScript page
errors, and no horizontal document overflow. The verifier,
result JSON, rebuilt DB and screenshot are private under
ignored local/audits/stealth-counter-aros/.

This is bounded source-to-page acceptance, not an engine-level
general ARO permission or 367-record corpus signoff. The
original inventory remains frozen; conditional ARO and
numerical Army variant work remains open.

## 1.0 Look Out! exceptional allied Dodge ARO

**Verified 2026-10-16 against pinned N5.3 English p. 81.**
A curated regression checks Look Out!'s ARO-only and No
Roll type, original reviewed restriction, Dodge relationship,
primary PDF citation, and allied selection, special ARO,
unopposed/Face to Face, and no-prior-ARO conditions.
A SHA-256-pinned source test checks all relevant clauses
and the outside-LoF/ZoC example.

The rebuilt rules database powered headless Chrome checks
of the Look Out! Skill page at 1440, 390 and 320 px.
**3/3 checks passed** for ARO badge, visible explanation,
no JavaScript page errors and no horizontal overflow.
Private verifier, rebuilt DB and screenshots are under
ignored local/audits/look-out-aro-browser/.

This is bounded ARO procedure acceptance. The original
367-record inventory is unchanged, and other conditional
AROs and the whole-corpus gate remain open.

## 1.0 Reload and Place Deployable ARO timing

**Verified 2026-10-16 against pinned English N5.3 pp. 82-83
and 120.** Curated tests assert the Short Skill/ARO identity
of Reload and Place Deployable, their retained historical
citations, Baggage eligibility and separate States Phase
recovery, reactive LoF, the Perimeter placement exception,
Conclusion timing and the unchanged occupied-spot FAQ ruling.
A SHA-256-pinned PDF regression validates the actual headings
and these eligibility and activation clauses.

A freshly rebuilt rules database was used to verify Reload
and Place Deployable in headless Chrome at 1440, 390 and
320 px. **6/6 browser cases passed**, including visible
Short Skill and ARO badges, new explanation text, no JavaScript
page errors and no horizontal overflow. Private verifier,
database, screenshot and results are stored under ignored
local/audits/reload-deployable-aros/.

The frozen 367-record inventory is unchanged. This closes a
bounded source/metadata review, not other exceptional ARO
permissions, other numerical variants, or whole-corpus 1.0.

## 1.0 Discover marker retry and ARO reveal procedure

**Verified 2026-10-16 against pinned N5.3 English p. 77.**
Curated regression coverage checks mandatory LoF, the one
attempt per target per Order restriction, failed same-Marker
lockout until next Player Turn, separate attempts by other
Troopers, reset of Marker identity following revelation and
re-entry, and the Discover + Attack ARO reveal exception.
A SHA-256-pinned PDF test checks the original source wording.
Discover retains its Basic Short Skill/ARO type, existing
source citations, and reveal relationships.

With a newly rebuilt rules database, the Discover Skill page
was tested in headless Chrome at 1440, 390 and 320 px:
**3/3 checks passed** for visible categories and new rule
explanations, no JavaScript errors, and no document overflow.
Private verifier, database, results and screenshot are under
ignored local/audits/discover-aro-review/.

This is selected rule correction and browser acceptance,
not completion of all ARO exceptions, numerical Army variants,
or the frozen 367-record audit inventory.

## 1.0 Cautious Movement ARO-suppression conditions

**Verified 2026-10-16 against SHA-256-pinned English N5.3
pp. 32 and 112.** A curated regression tests the Long Skill
classification, existing movement restrictions, new primary
PDF references, ordinary LoF/ZoC endpoint checks, the Hackable
Model and non-Hackable Hacking Area distinction, Stealth
exceptions, Hidden Deployment exclusion and unchanged
Stealth-to-Cautious Movement relation. A pinned-PDF test
checks the exact source heading and relevant clauses.

A newly rebuilt rules database was used in headless Chrome
at 1440, 390 and 320 px: **3/3 Cautious Movement page checks
passed** for the visible Long Skill category, the new source
explanations, no JavaScript exceptions and no document overflow.
The private verifier, result JSON, database and screenshot
are under ignored local/audits/cautious-movement-aro/.

This is bounded source-to-page acceptance. The frozen
367-record inventory and remaining conditional ARO and
Army-variant acceptance tasks remain open.

## 1.0 Alert! automatic Conclusion

**Verified 2026-10-16 against the SHA-256-pinned English
N5.3 PDF p. 77.** The curated regression checks Optional,
No Roll and Automatic classification, the Order/ARO
activation exclusion, allied Attack/ZoC requirement,
after-Saving-Rolls Conclusion timing and absence of
additional reactions. The original reviewed text and
historical Wiki reference remain, alongside the new
primary-source citation. A separate pinned-PDF test
checks the heading and all associated conditions.

A newly built rules DB passed **3/3 headless Chrome
Skill-page checks** at 1440, 390 and 320 px for the
Automatic badge, visible eligibility and timing text,
no JavaScript exceptions and no document overflow.
The verifier, results, database and screenshot are
private under ignored local/audits/alert-conclusion-audit/.

The original 367-record audit remains frozen; other
conditional ARO permissions and the whole-corpus gate
remain open.

## 1.0 Cyberplug Controller ARO split

**Verified 2026-10-16 against the SHA-256-pinned N5.3 English
PDF pp. 107-108.** The curated regression asserts the existing
Automatic Peripheral Skill, Cyberplug Connected/Autonomous
profiles, common-Order activation, separate reactive eligibility
and Controller-as-Idle behavior. A PDF-pinned regression checks
the official active and reactive examples.

With a freshly rebuilt rules DB, the published Cyberplug
subtype reference passed **3/3 headless Chrome checks** at
1440, 390 and 320 px. The new explanations were visible,
with no JavaScript errors or horizontal overflow. Private
verifier, screenshot, results and rules database remain under
ignored local/audits/cyberplug-aro-browser/ and
local/audits/cyberplug-aro-audit.db.

The original REA-017 foundation and frozen 367-record audit
are unchanged. This is selected ARO clarification, not a new
rules engine or whole-corpus 1.0 acceptance.

## 1.0 Speculative Attack Circular Template ARO order

**Verified 2026-10-16 against SHA-256-pinned English N5.3
p. 48.** Two regressions verify Long Skill classification,
primary and historical Wiki citations, unchanged modifiers,
the Main Target and legal impact point, the check for affected
Troopers before AROs and distance measurement, and the
behind-cover Dodge (-3) Face to Face example.

A fresh rules database powered browser checks of the
published Speculative Attack Skill page at 1440, 390
and 320 px. **3/3 headless Chrome checks passed** for
the Long Skill badge, new explanatory text, no JavaScript
errors, and no horizontal overflow. Private verifier,
results, screenshot and rebuilt DB remain in ignored
local/audits/speculative-aro-browser/ and
local/audits/speculative-aro-rules.db.

The selected ARO procedure is source-reviewed; neither
the frozen 367-record inventory nor remaining whole-corpus
1.0 acceptance tasks are marked complete.

## 1.0 Suppressive Fire G: Jumper ARO boundary

**Verified 2026-10-16 against SHA-256-pinned N5.3 English
pp. 85 and 171.** A curated test checks the Long Skill
classification, historical Wiki and primary PDF citations,
G: Jumper exception and the existing State's B3 BS Attack
ARO limit and cancellation rule. A source-pinned regression
checks the explicit Proxy exception and reactive Burst
conditions.

With a newly rebuilt rules database, the published
Suppressive Fire Skill and State pages passed **6/6
headless Chrome checks** at 1440, 390 and 320 px, including
the new explanation, existing State restrictions, no
JavaScript page errors and no horizontal overflow.
Private verifier/results/screenshot/database are under
ignored local/audits/suppressive-fire-aro/.

The frozen 367-record audit is unchanged. This is a
selected conditional activation review, not whole-corpus
1.0 acceptance.

## 1.0 Hacking Area reactive windows

**Verified 2026-10-16 against SHA-256-pinned English N5.3
pp. 55-57.** Curated regression coverage pins the owning
Hacking Area rule to the correct p. 55 source heading,
preserves its archived Wiki citation, and checks separate
ARO opportunities for an enemy Hacker and a later targeted
Trooper, plus delayed ARO restrictions for Camouflaged Markers.
A pinned-PDF test verifies both worked source examples.

The published Hacking Area page was tested from a fresh
rules database in headless Chrome at 1440, 390 and 320 px.
The first attempt displayed incomplete content at 390 px
despite HTTP 200; diagnostic reruns were all successful:
**three complete repeats, 9/9 checks passed** for rule
content, links, no JavaScript errors and no horizontal
overflow. The intermittent initial failure is recorded
but not confirmed as a reproducible UI regression.
Private verifier, evidence and rebuilt database are under
ignored local/audits/hacking-area-aro/.

This is bounded source-to-page verification, not acceptance
of all conditional ARO rules or the frozen 367-record corpus.

## 1.0 Army BTS attribute override presentation

**Verified 2026-10-16 against current built Army data and
maintained source classification policy.** A focused synthetic
regression checks that configured `attribute-override`
occurrences, including BTS=3, separate from actual Skills
in the loadout-specific presentation without changing the
original source items. Existing catalog tests continue to
ensure non-Skills such as BTS=3 do not appear as independent
rules-backed Skills.

Headless Chrome tested the actual Corregidor Alguaciles
Unit page at 1440, 390 and 320 px. **3/3 checks passed**:
the three Gatta BTS=3 occurrences appeared under Attribute
overrides, no `/skills/bts-3` links were generated, and
there were no JavaScript errors or horizontal overflow.
The private verifier, screenshots and results are under
ignored `local/audits/bts-override/`.

The frozen 367-record audit and remaining numerical
variant/source acceptance are separate open tasks.

## 1.0 non-Skill Army Unit presentation

**Focused regression, 2026-10-16.** Known Army source classifications
are projected into Unit Equipment, Training, and Attribute overrides.
The source-only Infinity Team-Ops marker is not presented as a Skill.
Native Bangbomb Equipment takes precedence over its duplicate source
occurrence, while raw Army items remain intact. Source classification
is maintained in config/catalogs/skill-source-classifications.json.
Synthetic regression passed; whole-corpus browser acceptance is open.

## 1.0 Trait Wiki heading-fragment acceptance harness

**Source and bounded browser acceptance completed 2026-10-19.** The local saved
official Wiki HTML audit first reported **22/22 existing links matched**
across 35 parsed headings and one unambiguous heading ID for each of the
11 previously unmapped canonical Traits. After those exact fragments were
added to the maintained map, a follow-up local audit reported **33/33
matched (35 headings parsed)**. This completes source-heading verification
for that HTML snapshot, but does not demonstrate that the links on the
public Trait detail pages scroll correctly in a browser. Legacy MediaWiki
encoding matters: Suppressive Fire (SF) uses `.28SF.29`, not a
display-name-derived fragment.

`tools/audit_trait_wiki_anchors.py` reads a saved HTML response from the
official `https://infinitythewiki.com/Traits` page. It checks every mapped
fragment against the page's actual heading `id` and its rendered text,
reporting missing fragments and wrong-heading matches separately. The
audit runs **offline**, writes optional JSON evidence (including the exact
HTML file SHA-256), and returns a nonzero exit status for any mismatch.
`--inventory-unmapped` separately lists heading IDs exactly as they appear
in the supplied HTML for canonical Traits without a maintained URL; unique
matches are **review candidates**, never automatically published destinations.
Missing or duplicate headings are flagged for manual investigation. The parser
excludes MediaWiki edit controls and handles void markup within headings.
Its hermetic regression tests cover legacy `mw-headline` spans, headings
with direct IDs, nested markup, candidate reporting and failure handling;
they are not evidence that the live Wiki accepts the links.

To run the source check explicitly from the repository root in PowerShell:

```powershell
Invoke-WebRequest -Uri "https://infinitythewiki.com/Traits" -OutFile "local/audits/traits-current.html"
.\.venv\Scripts\python.exe tools/audit_trait_wiki_anchors.py local/audits/traits-current.html --inventory-unmapped --output local/audits/trait-wiki-anchors.json
```

Keep the HTML and report under ignored `local/audits`, with a capture
date, source revision, and SHA-256 recorded in the associated review.
The 22/22 inventory and subsequent 33/33 result were supplied from the
local audit outputs; the underlying saved HTML and SHA-256 were not
available through the repository probe. The source audit is complete
for the tested snapshot. A separate local Chromium run subsequently passed
all 33 Trait page navigation checks against that saved Wiki HTML snapshot.

### Player-facing Trait link browser acceptance

The source audit does not exercise the browser. Inspection found that the
previous Trait Wiki link was placed exclusively in the developer-only
`#item-meta` element, and so ordinary users could not see it.
`traits-detail.html` now provides a separate, initially hidden
`#trait-wiki-link` in player-facing content. `catalog-detail.js`
sets its reviewed URL and reveals it when `wiki` is available; the
developer-only source metadata on other catalog pages is unchanged.

`tools/verify_trait_wiki_browser.py` is an optional browser acceptance
check. With a running local InfinityDB application and an existing official
Traits HTML snapshot, it visits all 33 `/traits/{slug}` routes in a clean
Chromium context with Developer Mode off; each page must render the visible
source link, open a new tab with the exact curated fragment, and scroll to
the corresponding heading. The official Wiki is fulfilled from the saved
HTML and other external traffic is blocked. Its source audit must first
match all maintained links. This check does not prove live third-party
reachability or the behavior of a later Wiki revision.

Run against the current checkout, not an older isolated Docker/Caddy
test stack. In a separate PowerShell window at the repository root start
the development server (its default port is 8000):

```powershell
.\.venv\Scripts\python.exe -m infinity_db serve --host 127.0.0.1 --port 8000
```

Then run the verifier from the repository root in another PowerShell window.
The browser dependency is optional and is not part of the canonical project
test suite:

```powershell
.\.venv\Scripts\python.exe -m pip install playwright
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m tools.verify_trait_wiki_browser --base-url http://127.0.0.1:8000 --wiki-html local/audits/traits-current.html --output local/audits/trait-wiki-browser.json
```

If all routes report HTTP 404, the verifier is reaching the wrong/stale
service rather than exposing a problem with the Wiki heading fragments.
The preflight now verifies `/traits/boost` returns HTTP 200 with the
current `#trait-wiki-link` template before testing any of the 33 links.
The repository's presentation handler separately serves all 33 routes
in regression tests. An existing listener at port 8080 is not assumed
to reflect the current working tree.

**Accepted 2026-10-19:** The local Chromium verifier passed **33/33**
Trait page navigation checks against the current development server with
the saved official Wiki HTML substituted for external requests. This
verifies that the player-facing links open the exact configured anchors
and scroll to the expected headings in the isolated browser environment.
It does not establish live external Wiki availability or later revisions.

Keep the HTML, browser report, snapshot hash, and browser-run date under
ignored `local/audits`. The hermetic regression tests separately validate
the link's HTML/JS contract and the browser fixture; the 33/33 acceptance
result was reported from the local Chromium run.
