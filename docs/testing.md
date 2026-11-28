# Development checks

**Project domain:** Project infrastructure

This guide owns local test selection, runner invocation, host selection and
validation workflow. Use the focused guides for layer-specific work:

- [Data and source validation](testing-data.md) — runtime sets, source-backed
  tests, semantic and publication audits, release FAQ parity.
- [Browser acceptance](testing-browser.md) — Chromium, cross-browser cohorts,
  manual checks, served-candidate verification and visual diagnostics.
- [Performance and test capacity](testing-performance.md) — test scheduling
  diagnostics, reproducible benchmarks and decision-relevant measurements.

[CI](ci.md) owns hosted workflow requirements; [releasing](releasing.md)
owns release gates; [deployment](deployment.md) owns production operations.
[Historical validation evidence](#historical-validation-evidence) is not
current acceptance.

## Phased development and validation

Orient to the task and checkout, implement one coherent change, run relevant
focused checks, inspect the diff, and report actual results.

- Test design and execution may occur in the same implementation pass. Select
  affected consumers as well as new tests; widen only for demonstrated
  cross-cutting risk, cumulative integration or an independent release gate.
- Documentation-only work normally requires the docs stage; review changed
  executable examples against their actual CLI. Security, schema, source
  authority and publication integrity require applicable immediate checks.
- A failure, missing input, skipped assertion or dispatch is not acceptance.
  Report the tested SHA, host, coverage, failures and meaningful skips.
- Use the [validation queue](validation-queue.md#queue-rules) only for
  genuinely deferred required work. Batch compatible outstanding checks on
  the same pinned revision; no numeric threshold or mandatory drain applies.
- Final release acceptance remains a separate mandatory full-suite and
  running Docker gate; see [the release checklist](releasing.md).

## Validation host selection

Use the dedicated Linux development worker (`linux-dev`) by default for
complete local test suites, including mandatory release acceptance. Use the
validated eight-worker, four-slot, four-lane Chromium profile with the
Scenario FAQ split on that host. Keep Windows for development, focused
regression checks and Windows-specific compatibility tests. Prefer moving
a broad validation run to Linux over repeatedly tuning Windows browser
fixtures or rerunning full suites after host transport/resource failures.
Run a full Windows suite only when Windows-specific integration risk
justifies it or Linux is unavailable.

Synchronize the Linux checkout explicitly, pin the candidate SHA, and
verify required assets and source inputs before testing. If required
source-only checks cannot run on Linux, execute those checks separately
on an exact-SHA host with verified inputs and account for their coverage
in the release evidence; do not count missing-source skips as passes.
Hosted CI and isolated Docker release acceptance remain independent gates.
See [parallel validation](#parallel-windows-development-and-linux-validation)
and [release validation](releasing.md#4-run-local-release-validation).

## Local invocation

Use the project virtual-environment interpreter when available:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py --profile code
```

On Linux/macOS use `.venv/bin/python` instead.

## Read-only development status

When useful, inspect development status with the optional read-only
repository-local command instead of repeating unrelated inventory queries:

```powershell
.\.venv\Scripts\python.exe -m tools.dev.dev_status
.\.venv\Scripts\python.exe -m tools.dev.dev_status --json
```

On Linux/macOS use `.venv/bin/python`. `--offline` skips both network/monitor
lookups, returning local Git, V1S and VD/VR data only. This command **never
writes Git state, selects or retires work, starts tests, synchronizes checkouts,
or dispatches CI**. It reads current `docs/TODO.md` through the maintained
V1S parser and reads active deferred checks from
`docs/validation-queue.md`. The reported next actionable V1S is only
advisory; no active agent assignment is stored. Queue counts and oldest-item
ages are informational: they do not create validation deadlines or initiate
test execution.

When online, the command checks the existing Windows MCP monitor's loopback
`/api/status` endpoint (default port 8766; override with `--monitor-port`).
It shows active jobs for the primary InfinityDB checkout and distinct named
agent worktrees, along with their workers and reported revisions. The monitor
must be enabled in the gateway; an unreachable or stale provider is not proof
that no tests are running. CI uses GitHub Actions run listings filtered to the
**exact local HEAD**, for the repository identified by the GitHub origin.
For restricted repositories, `GH_TOKEN` or `GITHUB_TOKEN` may authorize the
read-only request. CI results are **run-level observations only**; a successful
run does not replace inspection of required jobs, matrix legs, asset coverage
or frozen-candidate acceptance. Absent/inaccessible workflows are explicitly
unverified, not passed. No token value is printed.

## Profiles and stages

The canonical entry point is [tools/run_checks.py](../tools/run_checks.py).
Use the project's virtual environment. The seven stages are:

- `test` — pytest.
- `lint` — Ruff.
- `docs` — Markdownlint, offline Markdown links and backlog integrity.
- `type` — Pyright, using the runner's interpreter for dependency resolution.
- `build` — Army source/database build validation.
- `rules` — interaction-review coverage and generated checklist validation,
  curated rules validation and database build.
- `preflight` — isolated Git-index and installed-wheel validation.

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
dependencies and reports. It then runs `tools.ci.check_doc_links` with the
same Python interpreter as the check runner to validate relative Markdown
paths and heading anchors across **all Git-tracked Markdown files**, including
nested references, plus new `docs/*.md` drafts before staging. Without Git
metadata it falls back to the main root, `docs/`, and `data/` references.
The link checker excludes ignored private files, does not access external
URLs, validate application routes or substitute for browser acceptance;
it checks ordinary inline links and reference definitions, not arbitrary
embedded HTML. Its file count can differ from Markdownlint's glob selection.
The final docs-stage command, `tools.ci.check_v1_backlog`, checks only the
active backlog's static structure. It needs no Git history or ignored
inputs, and it does **not** automatically choose a task or approve closeout.
Install the Markdownlint dependency **explicitly** before `docs` or `--all`:

```powershell
npm ci --ignore-scripts --no-audit --no-fund
.\.venv\Scripts\python.exe tools/run_checks.py --stage docs
```

Node.js 22 or newer is required (CI uses Node.js 24). `npm run lint:docs`
runs **Markdownlint only**; use `--stage docs` for the complete documentation
checks or invoke the individual Python checkers directly.
The stage invokes the pinned installed tool via `npm run`, not `npx`;
checks neither install dependencies nor fetch packages automatically.
Bootstrap downloads happen only with the separate `npm ci` step.
Missing npm or dependencies cause an explicit check failure. No Node.js
build step is part of the application's runtime or packaging.

## Targeted checks

```powershell
.\.venv\Scripts\python.exe tools/run_checks.py --stage test tests/test_availability.py
.\.venv\Scripts\python.exe tools/run_checks.py --stage test tests/test_web.py::test_fireteam_chart_page_and_api_use_application_projection
.\.venv\Scripts\python.exe tools/run_checks.py --stage lint src/infinity_db/web tests/test_web.py
.\.venv\Scripts\python.exe tools/run_checks.py --stage type
```

Positional targets narrow pytest or Ruff, not other stages. Invoke pytest
directly for `-k`, `-q` and other pytest-specific arguments. Use
`--source-occupancy-gate` with the rules stage when the applicable source
presentation gate is required. Do not report Ruff or Pyright as run when
the tool was unavailable.

## Maintained pytest sections

[config/testing/test-sections.json](../config/testing/test-sections.json)
owns the test module inventory. The six sections are:

- `model` — data/model/repository semantics.
- `web` — HTTP/API and web presentation.
- `browser` — browser verification and Chromium journeys.
- `build` — acquisition/build/export/tooling.
- `ops` — deployment/packaging/operations.
- `assets` — graphical publication processing/validation.

```powershell
.\.venv\Scripts\python.exe tools/run_checks.py --stage test --test-section model
.\.venv\Scripts\python.exe tools/run_checks.py --stage test --test-section web --test-section browser
```

A complete suite includes all sections. Do not hard-code evolving test counts.

## Pytest workers

Ordinary defaults are `--test-workers auto --test-dist worksteal` and two
Chromium slots. Use a fixed positive count or `0` for serial diagnosis.
The explicitly enabled Linux host profile is described in
[performance and test capacity](testing-performance.md#chromium-concurrency-under-pytest-xdist).
Worker selection is execution policy, not a correctness difference.
Keep independent test scratch directories; pytest uses its platform-default
per-session temporary directory. CI scheduling is owned by [CI](ci.md).

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

Required CI uses a controlled fixture rather than network acquisition or a developer's `local/data/raw/army/`
contents. Normal checks must not fetch upstream data implicitly.

## Reports and exit status

Use `--report` for a transcript under
`local/reports/checks/CHECKS YYYYMMDD-HHMMSS.txt`, or specify a fresh path:

```powershell
.\.venv\Scripts\python.exe tools/run_checks.py --stage test tests/test_web.py --report
.\.venv\Scripts\python.exe tools/run_checks.py --stage docs --report=local/reports/checks/RUN_ID/docs.txt
```

Prefer selectors before a bare `--report`, or `--report=PATH` for an explicit
destination. Existing files, symlinks and tracked/source destinations are
refused; reports use exclusive creation. An interrupted new receipt may be
partial. Never overwrite earlier evidence.

Full unfiltered test stages default to grouped skip reasons
(`--skip-summary`); use `--skip-details` for exact skipped nodes and
`--no-skip-summary` to suppress the grouped report. Skips are not passes.
Record unavailable private source evidence separately from expected platform
or opt-in skips.

Exit codes: 0 success, 1 stage failure, 2 runner/configuration error.
Later stages continue by default; use `--fail-fast` to stop. Preflight is
skipped after an earlier failed stage, with the overall failure retained.

## V1S backlog checks

The historical V1S check remains part of the regular `docs` stage. With
no active V1S entries, the old register heading need not remain in TODO;
unscoped V1S task declarations still fail validation. If a numbered V1S
task is reopened, restore the `Pre-planned 1.0 execution slices` heading
before adding it. Do not run task selection with a null ID. The selection
check examines every earlier open ID across workstreams and fails
unexplained skips:

```powershell
$taskId = (.\.venv\Scripts\python.exe -m tools.dev.dev_status --offline --json | ConvertFrom-Json).backlog.next_actionable
.\.venv\Scripts\python.exe -m tools.ci.check_v1_backlog --select $taskId
```

A user-directed priority exception is permitted **only** when the selected
task already includes an exact `Priority: <reason>; authority: <owner>;
revisit: <trigger>` annotation in `docs/TODO.md`, and the CLI supplies
the same reason using `--priority-reason`. No standing priority override
is needed after the V1S-096 checker implementation was accepted.

Earlier `Blocked:` or `Deferred:` annotations must name a concrete reason,
owner/authority and `retry:` or `revisit:` trigger, respectively. Incomplete
annotations are warned about and **do not** excuse earlier IDs. Neither a
selection pass nor a priority override retires any task.

Before **removing** a numbered task from TODO, inspect the proposed index
(or worktree) without altering it, then include each retired ID and canonical
acceptance evidence in the eventual commit. After committing, audit the
introducing history from a deliberately chosen ancestor revision:

```powershell
.\.venv\Scripts\python.exe -m tools.ci.check_v1_backlog --base HEAD --target-state index
.\.venv\Scripts\python.exe -m tools.ci.check_v1_backlog --base HEAD --target-state worktree
.\.venv\Scripts\python.exe -m tools.ci.check_v1_backlog --base HEAD~1 --enforce-closeout
```

The `HEAD~1` example checks only the most recent first-parent commit; use
a verified earlier base when multiple closeouts are involved. Historical
advisory mode omits `--enforce-closeout`. Merge ancestry errors are not
clean passes, and evidence-pointer detection does not assess semantic
acceptance. Pass `--json` for machine-readable status, diagnostics and
selection metadata with the same exit codes. Git-aware CI has its own
event-specific base-revision contract in [CI policy](ci.md).

## CI preflight (clean checkout and wheel contents)

Use the isolated preflight when packaging, dependency or clean-index
coverage is relevant, and at the applicable release gate. Stage the intended
inputs first:

```powershell
.\.venv\Scripts\python.exe tools/run_checks.py --stage preflight
```

[tools/ci/ci_preflight.py](../tools/ci/ci_preflight.py) exports the Git index,
including staged additions/content, not unstaged edits. It rejects untracked
non-ignored files by default (`--allow-untracked` warns), unresolved merges
and unsupported modes. Symlink export requires platform permissions.

The standard runner invokes isolated mode: install declared development and
symbol dependencies into a fresh environment, verify indexed runtime artifacts
and source bindings, run Ruff/pytest/Pyright, build a wheel, audit indexed
package resources and run installed-wheel smoke outside the checkout.
The indexed asset check uses the resolved `--assets` mode.
The preflight checks the full indexed suite regardless of ordinary stage
selectors. The runner forwards applicable worker/distribution, slot/lane
and asset options, but not the automatically selected local host profile.

For a quick packaging/untracked check:

```powershell
.\.venv\Scripts\python.exe -m tools.ci.ci_preflight --skip-pytest
```

Direct `--skip-wheel` omits the wheel audit and smoke. Both skip options
together check only index export/untracked-file integrity.
`--isolated` cannot be combined with `--skip-pytest`.
Package installation/build isolation may access package indexes, never
upstream game sources. Indexed preflight does not lint Markdown; run
the ordinary docs stage. A passing wheel audit proves member presence,
not byte equivalence or comprehensive consumer coverage. An index pass
does not validate unstaged files, other platforms or actual Docker startup.
See [CI](ci.md#git-index-preflight-and-wheel-content-audit).

## Parallel Windows development and Linux validation

Use the dedicated `linux-dev` worker, not the independent interactive
Linux checkout. Keep validation and development inputs isolated.

1. Identify the intended revision, relevant selectors and required sources/assets.
2. Inspect the local and remote branch and working tree. Use explicit,
   safe Git synchronization and verify the full expected SHA; do not
   move a running job's checkout or silently discard unrelated changes.
3. Verify the selected runtime set and required ignored source evidence.
   [Syncthing staging](syncthing-assets.md) does not synchronize Git or
   generated databases. For source-only prerequisites see
   [data validation](testing-data.md#full-army-source-archive-provenance-tests).
4. Dispatch the relevant tests. Through the connected MCP workspace use
   asynchronous `start_test_job` (pytest/unittest selectors) or
   `start_script_job` (tracked custom runners including
   `tools.run_checks`), with the intended worker and `expected_commit`.
   Synchronous MCP check/tool calls do not execute test-bearing profiles.
5. Poll the existing job to terminal status, recovering its ID and output
   offsets after disconnection. Review actual exit code, revision, tests,
   failures, skips and asset coverage before reporting acceptance.

Independent Windows development may continue during focused or full Linux
runs, but never mutate the test checkout or shared mutable inputs. Do not
interpret independent concurrent workloads as controlled benchmarks.
See the [MCP workspace skill](../.agents/skills/infinity-mcp-workspace/SKILL.md)
for tool discovery and the [CI monitoring contract](ci.md#agent-ci-monitoring-and-repair)
for independent hosted follow-through.

## Agent coordination safety acceptance

These tests apply only when working on the optional coordination implementation;
they do not activate coordinated development. Run
`tests/test_agent_coordination.py`, `tests/test_agent_global_coordination.py`,
`tests/test_agent_workspaces.py` and `tests/test_test_sections.py` as applicable.
The [coordination protocol](multi-agent-workspaces.md#activation-and-default-workflow)
owns scope and operational limitations.
The [historical acceptance](https://github.com/frankysan/InfinityDB/blob/4774abde079a0e91ea87c9ee417c4ca1e2429403/docs/testing.md#agent-coordination-safety-acceptance)
includes 80-test Linux recovery coverage and the blocked real Linux registry
claim round trip; it does not establish current branch support.

## Historical validation evidence

Dated implementation milestones, release-candidate logs, historical source
reconciliation, retired tool invocations and earlier benchmark trials are
preserved in the [immutable pre-split testing document](https://github.com/frankysan/InfinityDB/blob/4774abde079a0e91ea87c9ee417c4ca1e2429403/docs/testing.md#development-checks)
at `4774abde`. They apply only to the recorded revisions and inputs.
Use Git history for old counts, receipts, investigations and exact historical
procedures; use the focused guides above for current commands. Keep new
run logs privately under `local/` and retain concise tracked results only
when they justify an active design decision or are needed for unresolved
acceptance. Do not recreate a chronological testing diary.
