# Development checks

**Project domain:** Project infrastructure

This document owns **local check procedures, focused test selection, phased
execution and retained dated validation evidence**. The older 1.0 acceptance
entries below apply to their stated revisions and artifacts; they are not
current TODO items or proof of post-deployment success. Hosted workflow
requirements belong in [CI](ci.md), release approval and production
verification in [releasing](releasing.md).

`tools/run_checks.py` is the canonical local entry point for pytest, Ruff,
Markdownlint, offline link checks, Pyright, database-build verification,
asset policy, worker selection and optional reporting.

The type-check stage explicitly passes the runner's interpreter to Pyright for dependency
resolution, so invoking the virtual-environment Python works without first activating that
environment in the shell.

## 1.0.1 release preparation

**Project domains:** Web frontend, Data processing, Project infrastructure

On 2026-11-08, the complete Linux release gate passed against staged tree
`bd6345314ec196a8e52d609a8f7ae3264446a1e3`, based on `f9be5fe9`.
It used Python 3.14.4, eight workers, four Chromium lanes/slots and the
Scenario FAQ split profile, with required assets, source occupancy and
`INFINITYDB_RELEASE_FAQ_PARITY=1`. The full source suite passed
**5,916 tests, 22 skipped, zero failures** in 665.48 seconds. Ruff,
Markdownlint, tracked-document links, backlog structure, Pyright, the
pinned Army build and rules/source-occupancy stages all passed.

The isolated Git-index preflight also passed (384.97 seconds), including
indexed artifact verification, lint/types, clean-export pytest, wheel
content checks and normal/asset-free installed-runtime smoke. Both installed
CLI entry points reported **1.0.1**. The clean-export run reported
**1,289 skips**, principally absent Playwright (880 cases) and ignored
Army/PDF/research inputs. These do not claim clean-export browser/source
acceptance: the separate full source run covered those available cohorts.
Its 22 skips were 14 separately selected cross-browser cases, seven
historical/legacy/migration-evidence cases and one Windows-only API case.
Two Python 3.14 multithreaded-fork deprecation warnings remained.

The source-matched v10 candidate and its `--check`, variant publication,
Weapon publication and deployment asset checks passed against the unchanged
tracked runtime set: 17 objects, one unresolved delivery, 151 variant groups,
62 reviewed Weapons and all 808 published/browser-referenced SVGs. Source
occupancy found no populated field among the 39 unrepresented fields. The
updated disposable Docker preview built the **1.0.1** wheel and passed
packaged-data, startup-health and reference API checks; its container/image
were removed. Docker ran through Windows' Linux engine because the devbox
account lacked Docker socket access. Neither check deployed an application.

The Orders & AROs spacing regression passed **12/12, zero skips** on Windows
Chrome (11.86 seconds), then passed in the Linux suite. The CSS was committed
in `8ecf035e`; bounding-box assertions were designed/reviewed without execution
in VD-0116. They check controls/core-card separation at 1440/1024/390/320 px
in both themes and controls/scenario/core-card separation at 1440/390 px,
retaining navigation, filters, page-error, request and overflow checks.
This closes VD-0116 and VR-0144.

Shared staging and source-review consumers now preserve the active v10
schema, Restrictions and reviewed embedded deployed objects. Comparisons
read the schema-owned model rather than requiring stale legacy JSON;
nonmutation guards preserve exact file bytes or absence. Legacy format,
rollback, unrelated-drift and unsupported-version rejection remain covered.
The impacted Windows cohort passed **846/846, zero skips** (59.50 seconds);
an additional audit/staging/reference/browser cohort passed **116 tests,
five historical/source skips** (57.97 seconds). Version/release-note/page
checks passed **36/36**. The final Linux full gate covered the repaired
consumers without relying on an existing ignored legacy JSON file.

The Army overview keyboard failure exposed a shared `popstate` bug: native
fragment traversal reloaded the page, racing its hash-target focus.
VD-0117 added lifecycle/main-identity and Back/Forward assertions at
1440/390 px, reviewed without execution. The new assertion failed before
the fix with one unexpected soft-navigation lifecycle event. The initial
Army/accessibility/web cohort passed **327/327**; the final expanded
Army/accessibility/Orders cohort passed **18/18** (21.66 seconds).
It also checks a filter-query update followed by the Skip link, fragment
Back and query Back, keeping native fragments distinct from route/query
changes and retaining cross-page focus/scroll restoration.

Failed/interrupted attempts remain in ignored `local/audits/v1.0.1/` and
are not acceptance: the first complete Windows run had nine legacy-reader
failures (**5,902 passed, 27 skipped**). The next had one Spec-Ops timeout
(**5,910 passed, 27 skipped**) with static-module `ERR_CONNECTION_REFUSED`;
that observation establishes neither a product regression nor a concurrency
root cause. An earlier Linux run had the Army keyboard failure (**5,915
passed, 22 skipped**). Linux source-audit inputs were copied inside the
validation root where required; root-containment checks were not weakened.
The existing interactive and MCP worker checkouts were preserved.

This verified local gate closes **VR-0145, VR-0146 and VR-0147**.
The final documentation-only closeout receives documentation and staged-index
checks before commit. Exact-SHA hosted Source/Wheel/Deployment/Cross-browser
acceptance, release dating, tagging and deployment remain separate release
checklist obligations.

## Focused release validation after a verified baseline

Finalize README, version and changelog metadata **before** the release PR.
For subsequent documentation or independent-test changes, run
`python -m tools.release_metadata`, Ruff and the affected pytest selectors
before considering full validation. The hosted Source workflow independently
requires a green four-workflow baseline; without it, the complete Source
matrix runs. This does not exempt the exact-SHA browser, wheel or deployment
gates. See [the CI policy](ci.md#risk-based-source-validation).

## Agent coordination safety acceptance

These checks validate the optional coordination CLI. They do not enable it or
create ordinary development prerequisites; the
[explicit activation policy](multi-agent-workspaces.md#activation-and-default-workflow)
owns when its workflow applies.

**2026-11-06, Project infrastructure:** proposal
`1ced58c7b57e27b583476c5ab9450463ec710669` passed **58 tests on Windows**
(asynchronous MCP job `2a806d44540045258054d4179ec27e2a`) and **58 on Linux**
in an isolated temporary environment. Both selected
`tests/test_agent_coordination.py`, `tests/test_agent_global_coordination.py`,
`tests/test_agent_workspaces.py` and `tests/test_test_sections.py`.
The Linux transfer archive was verified against SHA-256
`5a26ed259389fe1d7dc2c5007b00bd25efe6e9c5b9cd824c3351173cd5d237a2`;
the existing Linux checkouts were untouched. These immediate Git-integrity
checks cover independent-clone races, stale ownership/revisions, scope drift,
remote unavailability, checkout changes during preflight and interrupted or
ambiguous operations. Ruff, focused Pyright, the complete documentation stage
and staged backlog closeout passed. The guarded real-primary fast-forward
completed with both reservations held and global registry revision 12.

This evidence accepts the bounded cooperative integration guard, including
version-2 refusal by legacy clients. Inspected recovery, real cross-host
operational acceptance and protection against unrestricted Git clients remain
separate limitations in the [workspace protocol](multi-agent-workspaces.md).
The full suite, hosted matrix and frozen-release acceptance are independent;
the earlier accidentally launched full-suite job was cancelled and is not
acceptance. No new deferred test obligation remains for this safety slice.

The merged CI-repair revision `fde845a8d8b0028ac80309f8cf58a56b4313645f`
passed **110 tests, 5 optional skips, zero failures** on Windows (MCP job
`aa95adf4118a4b6b9c10636b99bbf8cf`). It combined the four coordination modules
above with `tests/test_deterministic_io.py` and
`tests/test_report_reference_baseline.py`. Ruff and focused Pyright also passed.
The newline-policy audit and exact bilingual Hackable-locator expectation now
pass; the earlier run at `9a4731b4` failed those checks. The first isolated CI
repair attempt had two setup failures, resolved by installing declared developer
dependencies and building/verifying the ignored deployed-object publication;
the subsequent standalone repair run passed 52 tests with 5 optional skips.

This combined run also executed the exact VR-0119 and VR-0120 planner/pilot
selectors and their baseline regressions without skips, so both entries are
retired on this revision. Their assertions preserve zero semantic/browser
approvals; VR-0118's source/API/browser acceptance remains open. The five optional
skips do not accept absent source/archive coverage. Replacement hosted Source,
wheel and deployment results remain independently required.

Bounded inspected integration recovery at
`2188aaa1ab4b0bd3ac2d45a2764af6c010a1fc8e` passed **79 Windows tests** in MCP
job `75dd86f4848b471786a729c6ec637043`, followed by the final remote-CAS race
test in job `23c1331c16f2443d9baa48386a5a0941` (**1 passed**). The complete
**80-test** selection then passed on isolated Linux; its input archive SHA-256
was `f253133b5c0eb389da0e78d1917d63375cd781b5847c9a754a57ad79b8aab629`.
Both coordinator source files were unchanged between the Windows runs; the
second run adds the competing-write assertion. Recovery cases cover unchanged
and already-integrated/published source, lost pin/completion/recovery responses,
failed local persistence, stale receipts/revisions, dirty files/indexes, missing
idle-job confirmation and competing callers. Every case preserves source Git
state and held ownership until explicit release. Ruff, focused Pyright, docs
and backlog checks passed; the real guarded fast-forward completed at global
registry revision 23. These are immediate Git-integrity checks, with no deferred
regression obligation for this bounded recovery slice. Abandoned-task transfer,
live cross-host operation and this revision's hosted matrix remain separate.

A live Windows/Linux probe at `b6a1632f` used a newly created, isolated Linux
development clone. Both hosts read the same version-2 registry at revision 25;
Linux correctly refused an existing Windows-owned file scope. A non-overlapping
Linux claim could not be published: the metadata push was rejected, with the
underlying access/policy cause unverified. Both hosts confirmed unchanged remote
revision and claims afterward. Temporary Linux local claims were explicitly
released, source HEADs and existing checkouts were preserved, and no permissions
were changed. This is partial operational evidence; bidirectional live claim/
release acceptance remains blocked in [TODO](TODO.md#concurrent-agent-development-safety).

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
.\.venv\Scripts\python.exe -m tools.dev_status
.\.venv\Scripts\python.exe -m tools.dev_status --json
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

The runner exposes seven stages:

- `test` — pytest;
- `lint` — Ruff;
- `docs` — Markdownlint, offline Markdown path/heading checks and static V1S backlog integrity;
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
The final docs-stage command, `tools.check_v1_backlog`, checks only the
tracked V1S register's static structure. It needs no Git history or ignored
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

## V1S backlog checks

The historical V1S check remains part of the regular `docs` stage. With
no active V1S entries, the old register heading need not remain in TODO;
unscoped V1S task declarations still fail validation. If a numbered V1S
task is reopened, restore the `Pre-planned 1.0 execution slices` heading
before adding it. Do not run task selection with a null ID. The selection
check examines every earlier open ID across workstreams and fails
unexplained skips:

```powershell
$taskId = (.\.venv\Scripts\python.exe -m tools.dev_status --offline --json | ConvertFrom-Json).backlog.next_actionable
.\.venv\Scripts\python.exe -m tools.check_v1_backlog --select $taskId
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
.\.venv\Scripts\python.exe -m tools.check_v1_backlog --base HEAD --target-state index
.\.venv\Scripts\python.exe -m tools.check_v1_backlog --base HEAD --target-state worktree
.\.venv\Scripts\python.exe -m tools.check_v1_backlog --base HEAD~1 --enforce-closeout
```

The `HEAD~1` example checks only the most recent first-parent commit; use
a verified earlier base when multiple closeouts are involved. Historical
advisory mode omits `--enforce-closeout`. Merge ancestry errors are not
clean passes, and evidence-pointer detection does not assess semantic
acceptance. Pass `--json` for machine-readable status, diagnostics and
selection metadata with the same exit codes. Git-aware CI has its own
event-specific base-revision contract in [CI policy](ci.md).

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
Explicit browser slot/lane counts also reach isolated pytest, including the
four-lane prerequisite when `--split-scenario-faq` is selected. This does not
enable the host's automatic browser profile for preflight.

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

The Phase 1 V1S backlog checker is a separate offline structural check; it does
not yet perform Git-history closeout or task-selection validation:

```powershell
python -m tools.check_v1_backlog
```

It reads the designated execution-slice section from `docs/TODO.md` without
requiring Git. Use `--todo PATH` to inspect another Markdown backlog file.

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

### P1 migration semantic baseline

The [P1.3 snapshot-pinned baseline](restructuring-plan.md#p13--snapshot-pinned-runtime-and-browser-route-baseline-2026-11-09)
is a focused, offline 41-route comparison for Army/Rules database restructuring.
Use `python -m tools.runtime_semantic_baseline --check --identical-artifacts`
for the current tracked DBs, or specify `--army-db` and `--rules-db`
without `--identical-artifacts` to compare a rebuilt database set.
It protects JSON source/citation semantics and Battleground SVG geometry
but is **not** a visual browser or Docker acceptance test.
Run `tests/test_runtime_semantic_baseline.py` for its guardrail tests.

For a complete embedded candidate, use the shared startup factory through:

```powershell
.venv\Scripts\python.exe -m tools.runtime_semantic_baseline --check --db-dir local/complete-dbs --route-alias "/static/restrictions-reference.json=>/api/restrictions/chart"
```

`--db-dir` requires current complete projections and recorded matched build
provenance before probing routes. It cannot be combined with individual database
paths or initial baseline capture, and never selects a different directory on
failure. The route alias is the reviewed static-to-API Restrictions migration;
the pinned response/geometry assertions still apply. This does not change normal
serving defaults or establish visual-browser, Docker or release acceptance.

### Selected runtime database-set validation

**Project domains:** Data processing, Project infrastructure

`infinity-db database-health --db-dir PATH --json` checks one explicit
supported runtime directory with full SQLite integrity and either
embedded source-paired facts or older matched JSON publications. The
[data lifecycle](../data/README.md) owns the current two-/three-/four-file contract and the limits of this check. The command operates offline,
does not require a raw archive, and reports unhealthy/missing data without
creating files or selecting another runtime directory.

The complete builder and `create_app_from_database_set` call the same validator
with `require_complete=True`. Their additional gate requires Army v31, Rules v17
and recorded matched build provenance. `tests/test_database_set_builder.py`
checks current complete startup, exact selected paths and rejection of partial
schemas/unrecorded provenance, while retaining all unchanged-output and
interrupted-build recovery checks. `tests/test_database_set.py` additionally
checks that complete startup rejects a transitional set and never creates a
missing selected directory. The ordinary health CLI retains the supported-layout
profile until the coordinated default cutover.

Run `tests/test_database_set.py` for selected-directory health, unchanged
input bytes, missing/corrupt artifacts, unsupported schema/application IDs,
stale publications, embedded Army mismatch and incompatible CLI selections.
`tests/test_app_cli.py` retains the individual Army/raw health contract;
`tests/test_deployed_object_storage.py` covers source-built v10 candidates,
checkout publication and Docker-bundle assembly using the shared verifier.
These focused checks do not establish actual Docker, Linux or hosted CI
acceptance or the final SQLite-only cutover.

`tests/test_database_set_builder.py` exercises input identity, source/code
changes, matched/tampered provenance, repeatable selected outputs, preservation
of unrelated files, source overwrite rejection, pre-publication failures,
interrupted mixed-set rejection and rerun recovery. Its orchestration fixtures
stand in for the Army/Rules generation phases using shipped runtime data;
normalization/export semantics remain covered by the existing CLI/curated tests.

**2026-11-09 initial v10 Windows acceptance:** Two real offline complete builds from the
pinned Army ZIP SHA-256
`f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`
produced identical bytes for all four runtime artifacts and matched shared
provenance. The rebuilt set passed all 41 P1.3 semantic baseline paths.
Its 116 source warnings matched the existing anomaly baseline; these were not
newly accepted source changes. This is local current-format build evidence,
not cross-platform byte acceptance, an actual Docker run or hosted approval.

**Rules v11 embedding:** `tests/test_variant_usage_storage.py` round-trips all
151 committed groups and 10,923 exact source rows, including equivalent TAGCom
spellings, ordered extras and source-only shared-option exclusions. It checks
API/ETag parity, missing/corrupt tables, invalid reviewed coordinates, duplicate
source identities, Army mismatch and export failure preservation. The six
`tests/test_verify_embedded_variant_usage_browser.py` cases reuse the existing
Skill/Equipment Developer Mode journey at 1440/390/320 px, retaining API/DOM,
page-error, failed-request, Unit-link and overflow assertions against v11 fixtures
without variant JSON. These are direct browser checks, not visual or source meaning changes.
The full-publication comparison uses the tracked v10 pair as migration evidence;
retire that fixture dependency with the legacy path while preserving the relevant
typed identity, source-parity and fail-closed assertions.

The earlier complete-build acceptance compared repeated three-file v11 outputs,
ran schema-aware health and bundle checks, and reused all 41 semantic baseline
paths. P2.3 now emits two-file v12 outputs, with reviewed Weapon Chart citations
embedded in Rules. `tests/test_weapon_profile_storage.py` verifies all 62 reviewed
Weapons/69 exact profile modes against the existing publication, current PDF
metadata, selected Army profile fingerprints, corrupted rows and absent sidecars.
`tests/test_database_set_builder.py` covers source-binding, two-file publication,
reproducibility and failed/interrupted replacement. Normal tracked v10 release
regressions remain separate. Actual Docker, Linux and exact-SHA hosted acceptance
remain separate and are not inferred from local focused checks.

**2026-11-09 P2.3 Windows local verification (pre-commit):** Weapon storage
10/10, two-file builder and HTTP citation read 16/16, v11 variant storage
13/13, Weapon API 196/196, selected database-set 20/20, Rules database
166/166 and legacy Weapon publication 19/19. Ruff, canonical Pyright,
documentation and `git diff --check` passed. The real source-ZIP export,
independent-platform reproducibility, Docker, Linux and exact-SHA hosted CI
were not established by this batch. The builder regression uses shipped
release-database fixtures, not a fresh Army normalization and source build.

**2026-11-09 P2.3 real source-ZIP acceptance (Windows):** The opt-in
`tools.verify_complete_database_build` diagnostic rebuilt the same immutable
`data/raw/JSON 20260929-114335.zip` twice (archive SHA-256
`f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`).
Both runs performed lossless normalization, all 73 source validation checks
(116 known baseline warnings), full v12 database-set health, matched build
provenance, 62 exact reviewed Weapon identities/69 cited profiles, 151 variant
groups, matched historical v10 citation semantics and live Weapon/variant HTTP
reads. Byte-level hashes were **identical** between independent runs:
`infinity.db` =
`a2607403e924d02a36f72da88a7d65300e8a2de354365044ff46ca2a7c171fa6`;
`rules.db` =
`e06e24c22f1c8b82fe8f4be4c628df8c12b5fe95261349775d84c1b9ac055998`.
Build-set ID:
`f7615d25cd8590b4498c7493cdebf382593d1377861bbd8f48f905fbc63e5af2`.
The two output directories and intermediate raw data were temporary under
ignored `local/`; no tracked release artifacts were replaced. Re-run the
opt-in diagnostic with
`python -m tools.verify_complete_database_build "data/raw/JSON 20260929-114335.zip" --sha256 f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`.
The historical citation builder and new maintained builder produced identical
tracked publication bytes. These are Windows local checks, not cross-platform
byte reproducibility, Docker, browser or hosted CI acceptance.

**2026-11-09 P2.4 first slice, Restrictions chart (Windows local):**
`tests/test_restriction_chart_storage.py` validates all six chart rows and
14 separately normalized constraints, 4 ordered typed qualifiers, current
source metadata, original JSON semantics and HTTP responses, v10 compatibility,
absent/modified chart failure and no packaged-JSON reads for v13. The
`tests/test_game_mode_source_table.py` browser checks exercise the
new chart API at three viewport widths, including a simulated 503.
The pinned `tests/test_runtime_semantic_baseline.py` continues to check
original v10 artifacts and all migration baseline paths; its one authorized
`/static/api.js` marker substitution recognizes the static-JSON to API
fetch transition without weakening source or payload comparisons.

The pinned source archive `JSON 20260929-114335.zip` (SHA-256
`f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`)
was independently built twice using `tools.verify_complete_database_build`
into isolated ignored directories. Both complete v13/compatibility-15
two-file outputs passed 73 Army normalization checks (116 known
baseline warnings), full selected-set health, source/provenance matching,
151 exact variant groups, 62 reviewed Weapons/69 chart citations and
six chart rows. The returned chart API payload exactly matched the maintained historical
chart JSON, and all 41 pinned runtime baseline routes passed in each build.
The final source-collection mismatch rejection also passed its focused
regression. Byte-identical output hashes were `infinity.db` =
`9c53611e0e09898002c705e175e8c2b11f567b77ae15b4b8edb47b48c0a061ef`
and `rules.db` =
`abcf8a8cd21c9f891bcb450471c217791562224ea47844c12950d785bdd2093d`.
Build-set ID:
`4d7d6af4ff9ea95d04dd35eda4def7e5045b8ad63dd41499932dc599063ac921`.
This proves local Windows reproducibility, not independent Linux,
Docker or final default-serving cutover acceptance.

**2026-11-09 P2.4 second slice, Trait Wiki links (Windows local):**
`tests/test_trait_wiki_storage.py` (13/13) exercises the complete
33-link relational publication, exact v10/v14 Trait detail API parity,
absence of packaged JSON loader calls on v14, source ID/name/URL
validation and missing/corrupted row/fingerprint failures.
`tests/test_database_set_builder.py` (16/16) covers repeatable v14
two-file publication and failed/partial destination isolation. The
existing Trait Wiki reference suite passed 22/22, Rules database
regressions 166/166 and v10 selected-set validation 20/20; Ruff,
canonical Pyright (0 errors), documentation checks and `git diff --check`
passed.

The same pinned Army source ZIP and metadata were built twice through
`tools.verify_complete_database_build`. Both opt-in Rules v14
(compatibility 16) sets passed 73 Army normalization checks (116 known
source warnings), full selected database-set validation, 151 variant
groups, 62 reviewed Weapons/69 profile citations, 6 Restrictions chart
rows, and all 33 reviewed Trait Wiki API links. Every one of the
41 pinned P1.3 semantic baseline routes passed in **both** runs.
The two independent complete builds were byte-identical:
`infinity.db` =
`fe8741e831782dd7c13c8ab7b5fbaced27d15eb50862f01947cd8a9a6ad5215a`;
`rules.db` =
`ae4e5888c4407a9dce4243be1f0941cc3bdb9e47e25f97703c2b96b8d5975fb0`.
Build-set ID:
`5ce9b54936df6ee29fb49d6d9e1ad9dce4d789b9112ee640828e479b982c4285`.
No tracked generated database was changed. These runs prove Windows
source-build reproducibility, not Linux, Docker or P2.6 serving cutover.

**2026-11-09 P2.4 third slice, Combined Saving Roll profiles (Windows local):**
`tests/test_combined_saving_roll_storage.py` (18/18) verifies six exact
source-mode signatures on three Plasma Weapons, full Rules v15
relational round trip, source PDF/Army pairing and content fingerprint,
v10/v15 API parity for the Plasma and Feuerbach details, no packaged
JSON read on v15, and rejection of missing, conflicting and malformed
profiles. The standalone maintained JSON loader remains supported
for source review and v10 compatibility. Existing `test_database_set_builder.py`
passed 16/16, `test_database_set.py` 20/20,
`test_rules_database.py` 166/166, the Plasma Critical suite 4/4,
and the focused CatalogRules combined-roll projection 1/1.
Ruff, canonical Pyright (zero errors/warnings), documentation and
Git diff checks passed.

The pinned immutable Army archive
`JSON 20260929-114335.zip` SHA-256
`f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`
was rebuilt independently **twice** with stable source bytes.
Both complete Rules v15/compatibility-17 two-file outputs passed
73 source normalization checks (116 known baseline source warnings),
selected-set integrity and provenance, 151 variant groups, 62 reviewed
Weapons/69 profile citations, six Restrictions chart rows,
33 reviewed Trait Wiki links and six exact Combined Saving Roll modes.
Both passed all 41 pinned P1.3 runtime routes. The byte-identical hashes
were `infinity.db` =
`31d9d3c7f14ed89367f1c94311e54add1af9e3c9761aad7ffb6932e18f185761`,
`rules.db` =
`44bebcbf3bd5f70ec5ccf8b736605f446daec2e6cd96fe52a9948a2474627aad`.
Build-set ID:
`756d6a67d781ccc5565a7312b4988fd8eff87b6e1386c941bd1ddc30af1040d4`.
A prior run whose code inputs were edited between attempts was
correctly rejected by the byte-equality gate; it is not counted as
reproducibility evidence. The stable repeatability run above passed.
No tracked generated files were changed; this establishes local
Windows opt-in acceptance, not Linux/Docker or P2.6 cutover.

**2026-11-09 P2.4 fourth slice, reviewed Ammunition links (Windows local):**
`tests/test_ammunition_reference_storage.py` (17/17) validates all
16 Army Ammunition ID/name pairs, 11 base links, five ordered combined
compositions (10 component relationships), exact v10/v16 HTTP
and resolver parity, v16 serving without JSON loader calls, and
fail-closed missing/malformed/mixed-source relational rows.
`tests/test_database_set_builder.py` passed 16/16 after correcting
the v16 validator's Windows SQLite connection lifetime;
`tests/test_ammunition_publication_parity.py` passed 8/8,
`tests/test_rules_database.py` passed 166/166 and
`tests/test_database_set.py` passed 20/20.
Ruff, canonical Pyright (0 errors, 0 warnings), documentation and
Git diff checks also passed.

Two complete isolated builds of immutable source archive
`JSON 20260929-114335.zip` (SHA-256
`f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`)
each passed 73 Army normalization checks (116 known baseline source
warnings), provenance and database-set health, 151 exact variant
groups, 62 reviewed Weapons/69 profile citations, six Restrictions
chart rows, 33 Trait Wiki links, six Combined Saving Roll profiles
and 16 Ammunition link identities. All 41 pinned runtime baseline
routes passed in both builds. The complete v16/compatibility-18
two-file SQLite outputs were byte-identical:
`infinity.db` =
`2f3eaf2b42271f6b8e824dcdcb9459f0eab84190442af355e713144b25b47a74`;
`rules.db` =
`3f21f9b4650ff37addd2786cb503399b8ef9434719f0373bc2633fa8931a9486`.
Build-set ID:
`d9b7276fd78bde74e32a61621a1139576e8fd12314f2be53f20c0f9f4990a83d`.
The current tracked v10 release artifacts were not modified; these
results establish the opt-in Windows path, not Linux/Docker or
P2.6 serving cutover acceptance.

**2026-11-09 P2.4 fifth slice, reviewed Weapon Properties (Windows local):**
`tests/test_weapon_property_storage.py` (17/17) validates all 12
reviewed property definitions, ordered current-rule origins, exact
nullable mode/source signatures, ordered original Trait strings,
v10/v17 Glossary/search/Weapon HTTP parity with v17 JSON reads disabled,
and fail-closed source/Army/profile/fingerprint corruption. The
existing `tests/test_weapon_properties.py` passed 26/26,
`tests/test_database_set_builder.py` 16/16,
`tests/test_rules_database.py` 166/166, and
`tests/test_database_set.py` 20/20. Ruff, canonical Pyright
(zero errors/warnings), documentation checks and `git diff --check`
passed.

Two independent complete opt-in builds from pinned
`JSON 20260929-114335.zip` (SHA-256
`f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`)
produced Rules v17 (compatibility 19) paired with the selected Army.
Both passed 73 Army source normalization checks (116 known baseline
warnings), selected-set health and provenance, 151 variant groups,
62 reviewed Weapons/69 citations, six Restrictions chart rows,
33 Trait Wiki links, six Combined Saving Roll profiles,
16 Ammunition references and 12 Weapon Properties. All 41 pinned
P1.3 runtime routes passed in both builds. The sets were
byte-identical:
`infinity.db` =
`884219134b942e2ad389f5bab0ad0ebeba0464bcd4f29e3f96ba2125eca21076`,
`rules.db` =
`0feb0994c0d81860f119c6d81eedd5822232ec639da4d2aeba57e3632952e862`.
Build-set ID:
`94a51879eab0aba64e60a349cb1da036fda1f46f40a3289094fe9adcb796c9d1`.
No tracked release databases were modified. This accepts the Windows
opt-in path, not Linux/Docker or P2.6 default serving cutover.

**2026-11-09 P2.4 sixth slice, Equipment presentation encodings (Windows local):**
`tests/test_equipment_presentation_storage.py` (12/12)
covers Cube/Cube 2.0 source characteristic mappings, Army v27
SQLite read-model parity with v26, no maintained JSON read in
v27 EquipmentCatalog, matching v27 Army/raw export generation,
published content checksum and rejection of missing, duplicate,
unrecognized or corrupted sources. The existing
`tests/test_equipment_config.py` passed 2/2,
`tests/test_database_set_builder.py` 16/16,
`tests/test_database_set.py` 20/20, and the focused Cube
HTTP/Unit-characteristic regression 1/1. Ruff, canonical Pyright
(zero errors/warnings), documentation and Git diff checks passed.

Two independent complete opt-in builds of the pinned immutable
`JSON 20260929-114335.zip` source (SHA-256
`f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`)
each passed 73 Army normalization checks (116 known baseline
warnings), the paired Army v27/compatibility-36 and Rules v17
integrity/provenance checks, 151 variant groups, 62 reviewed
Weapons/69 citations, six Restrictions chart rows, 33 Trait
Wiki links, six Combined Saving Roll profiles, 16 Ammunition
references, 12 Weapon Properties and two Equipment presentation
encodings. All 41 pinned P1.3 runtime routes passed in both
builds. The outputs were byte-identical:
`infinity.db` =
`c12a77d5ef9b67aefd16ae4e70ebd1cc4931f99322d5054d60edb74d997c7cd4`,
`rules.db` =
`8406bd463988072150c0f5224aea036ac33717bbffddbfbebd2b85cfb09230ed`.
Build-set ID:
`132848a42efa935fc6f10f919375dd72a169033f177e0117ee3e42621305f8a9`.
No tracked release database files were modified. This accepts
the local Windows opt-in path, not Linux/Docker or the P2.6
serving/name cutover.

**2026-11-09 P2.4 seventh slice, Army Skill source classifications (Windows local):**
`tests/test_skill_classification_storage.py` passed 15/15,
checking six exact reviewed Army source identities, numeric-or-slug
compatibility, composite Skill catalog resolution, JSON-free v28
SkillCatalog and Unit-detail presentation, Army/raw pairing, and
fail-closed missing/duplicate/drifted identity, source and fingerprint
checks. `tests/test_database_set_builder.py` passed 16/16,
`tests/test_database_set.py` passed 20/20, and
`tests/test_skill_config.py` passed 3/3, and
`tests/test_app_cli.py` passed 22/22, including the database-health
unsupported-schema regression. The v28 source identity helper passed canonical Pyright with
zero errors and warnings; Ruff and documentation checks passed.

Two independent, complete opt-in builds of pinned
`JSON 20260929-114335.zip` (SHA-256
`f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`)
produced a paired Army v28/compatibility-37 and Rules v17 set.
Both passed 73 Army normalization checks (116 known source warnings),
selected-set integrity and provenance, 151 variant groups,
62 Weapons/69 citations, six Restrictions rows, 33 Trait Wiki
links, six Combined Saving Roll profiles, 16 Ammunition references,
12 Weapon Properties, two Equipment presentation encodings
and six reviewed Skill source classifications. All 41 pinned
P1.3 runtime routes passed in each build. The two results were
byte-identical: `infinity.db` SHA-256
`5d76383a0ae16039476f335ab093edca523acc7e740cb38c9f2d6aefa5c1a558`,
`rules.db` SHA-256
`3626a0e0e13991444ae438b15c0662c300df2b62c8c12a1d9e4fabee7411a524`.
Build-set ID:
`1462b5b1f9ce4223bbdef7e399728623a71b88c44bb61acd694900a39ad26234`.
The tracked v10 release files were untouched; Linux, Docker
and P2.6 serving cutover remain separate acceptance gates.

**2026-11-09 P2.4 eighth slice, Unit Explorer filter semantics (Windows local):**
`tests/test_unit_filter_storage.py` passed 19/19, covering source-bound
rows/reasons/order, paired health and compatibility, unchanged source facts,
numeric/slug filter equivalence, combined/contextual membership, filter-choice
HTTP parity without maintained JSON, invalid-input isolation and corrupt-data
rejection. The related builder/set,
Equipment/Skill storage, CLI, Skill configuration and existing database/web
filter regressions passed another 95 tests (114 distinct focused tests total).
Canonical Pyright reported zero errors/warnings; Ruff, documentation links/lint
and Git whitespace checks passed.

Two independent complete builds of pinned `JSON 20260929-114335.zip`
(SHA-256 `f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`)
produced Army v29/compatibility 38 with Rules v17. Each passed
73 normalization checks (116 known source warnings), selected-set integrity
and provenance, all existing reviewed projection inventories, the two hidden
characteristics and one ordered classification membership. Both passed all
41 pinned P1.3 routes plus the classification/filter-values HTTP probes.
The outputs were byte-identical: `infinity.db` SHA-256
`5d8266ff043cb0e4efd0b8cf3d9a3ec786c92da6d27a98bfc068d2b97046923a`;
`rules.db` SHA-256
`aa854498cd4f0c4ef4b1f0997af9a740eb1067acf32b64c288efd64666e58ac5`.
Build-set ID:
`68d20bc8669a67a2cdf535b06d166c49fdfb8536aa9d3b6c3e6b6772d2171695`.
Tracked release databases and default serving remain unchanged. This is local
Windows opt-in acceptance; Linux, Docker and P2.6 cutover remain separate.

**2026-11-09 P2.4 ninth slice, Army overview and historical identities (Windows local):**
`tests/test_army_reference_storage.py` passed 26/26 across the focused
storage and runtime-audit runs. These checks cover all 58 summaries, both
historical identities, exact source digests/order, explicit parent identity,
non-playability, API/search parity without authored JSON, invalid-input
isolation, corrupt-row rejection and read-only runtime tracing. Related
builder/set, Unit-filter, CLI, domain-slug and existing Army/API/search
regressions passed another 92 tests. Seven runtime/separation audit tests
also passed after adding probes for the current Skill, Unit-filter and Army
reference readers (125 distinct focused tests total). This repairs the stale
method inventory that failed Source run `42688197310` at `9b0630e5`; it does
not relabel that failed hosted run as successful. Canonical Pyright,
Ruff and documentation checks passed.

Two independent complete builds of pinned `JSON 20260929-114335.zip`
(SHA-256 `f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`)
produced Army v30/compatibility 39 with Rules v17. Each passed all
73 normalization checks (116 known source warnings), selected-set health
and provenance, existing projection inventories, 58 authored Army summaries
and two historical identities. Both passed all 41 pinned P1.3 runtime routes
plus exact Army-summary, historical non-playability and search-link checks.
The two outputs were byte-identical: `infinity.db` SHA-256
`f9aa1bbfd7eea4e3e146a9eafa4ca58cac6dd822249ed9e2ed0f46f9f8e2749f`;
`rules.db` SHA-256
`cbab3ccb272663921434eb24a24c23bfac44ca086885f3c575b5bf202e0af9f4`.
Build-set ID:
`aeeccb45b53710da1e067245682e1e66d77d74a8a3322aae7dd1b6207e10ba1d`.
Tracked release databases and default serving remain unchanged; Linux,
Docker and final cutover require their separate acceptance.

**2026-11-09 P2.4 final slice, symbol mappings and cache identity (Windows local):**
`tests/test_symbol_path_storage.py` passed 18/18 across storage and Chromium
runs: all 2,019 keys/808 asset hashes round-trip exactly, paired health and
source binding remain strict, invalid paths/assets and corrupt rows fail
closed, a fresh subprocess starts v31 with manifest reads forbidden, and
two selected projections keep independent HTML/module cache versions.
The v31 Army overview also loaded in Chrome at 390 and 1280 pixels with
matching version metadata, loaded symbols, no page/request/HTTP errors
and no horizontal overflow. Related builder/set/audit, legacy symbol,
candidate-identity, full web/API, CLI and reference regressions passed
another 495 distinct cases (513 total). Canonical Pyright, Ruff and
documentation checks passed. The preceding `848657a3` Source run
`42690711332`, wheel run `42690711054` and deployment run `42690711307`
all completed successfully; they validate that earlier SHA only.

Two independent complete builds of pinned `JSON 20260929-114335.zip`
(SHA-256 `f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`)
produced Army v31/compatibility 40 and Rules v17. Each passed
73 normalization checks (116 known source warnings), selected-set health,
provenance and all existing reviewed inventories, plus exact embedded symbol
parity and actual hashes for all 808 SVGs. Both passed all 41 pinned P1.3
routes. The resulting SQLite files were byte-identical:
`infinity.db` SHA-256
`385ed6d7c5df165ea8783c16fb9f6fd74b072aa90eee6af5ed6a9881edd47f14`;
`rules.db` SHA-256
`3e026d291a257cb4df202dd40b7baa94c68b4d403a4fb707baaa2b006bd0732c`.
Build-set ID:
`18514ab77a5295223432bb3c3a35aac7bba4fa70bd3deeeba118e23975c4544d`.
P2.4 materialization is accepted at this opt-in Windows boundary. Tracked
release files and default artifact selection were not changed; Linux,
Docker and final serving cutover remain separate acceptance.

**2026-11-09 installed-wheel compatibility correction after P2.4:**
The v31 asset check initially rejected the deliberately asset-free legacy
installation in hosted wheel run `42693677485` at `88d307ec`.
Older manifest-backed Army schemas again permit absent SVGs while rejecting
present but incorrect bytes; embedded v31 publications remain strict about
both missing and corrupt assets. Ten focused asset/isolation tests passed.
A freshly built wheel was installed offline into a disposable Windows
environment outside the checkout; both normal and asset-free runtime modes
passed, including installed CLI/configuration/database and HTTP probes.
Ruff, Pyright and documentation checks passed. The failed hosted run remains
failed; replacement-SHA hosted acceptance is separate.

**2026-11-09 P2.5 first slice, embedded-only serving and image assembly:**
The focused deployed-object/storage/database-set, deployment-script,
two-file bundle, browser, web/API and CLI cohorts passed 432 distinct
hermetic cases. Negative legacy input checks retained the output sentinel;
current embedded-source binding, reviewed attributes/delivery provenance,
all-object API behavior and Chromium navigation remained covered. Historical
image-only assertions were removed; release-note and source-citation failure
checks remain on the supported image path. Ruff and canonical Pyright passed.

The Windows Docker Desktop Linux engine built a disposable image from the
unchanged tracked v10 database set. Image ID:
`sha256:e4ea3d816a82182a6260530b916c930691e9ca355a82894a269167cd3c627051`.
The revised `verify-container-image.sh --published-assets` passed embedded
database-set checks, complete packaged SVG/provenance validation, non-root
read-only production startup and HTTP reference/citation/variant/release-note
probes. The temporary container was removed by the verifier. This validates
the current tracked-set image path, not the future P2.6 names/defaults or an
opt-in v31 image. Shell syntax and documentation checks passed. No deployment
was performed. Legacy build/migration commands and the standalone JSON verifier
remain unfinished P2.5 work.

**2026-11-09 P2.5 second slice, CI/preflight selected-set verification:**
Source CI, cross-browser CI and clean-export preflight now call the read-only
`database-health --db-dir data/generated` check in place of the historical
deployed-object JSON build/check pair. Focused preflight, workflow and database-set
tests passed **174 cases** with **one skipped**. Ruff, canonical Pyright (0
errors), documentation lint/links/backlog and Git whitespace checks passed;
the tracked runtime artifact/provenance verifier passed with SVG checks disabled.
A direct Pyright invocation without the repository's required `--pythonpath`
failed on missing environment imports; the canonical type stage passed.
This is local Windows acceptance only, not hosted CI or an integrated Docker test.
The remaining historical builder/migration interfaces are separate P2.5 work.

**2026-11-09 P2.5 third slice, retired standalone deployed-object CLI:**
The v8/v9 stage, promote and refresh dispatch plus loose JSON build/check CLI
were removed. A direct module invocation now fails with an explicit retirement
message; the programmatic source projection/serializer remains temporarily
reachable for historical tests and unretired one-use tools. The current embedded
source builder and read path were not changed. Focused deployed-object
publication and storage suites passed **22 tests** (13 and 9 respectively),
including the rejection/no-output regression, source identity/provenance and
current v10 candidate/serving checks. Ruff, canonical Pyright (0 errors),
documentation lint/links/backlog and Git whitespace checks passed. The tracked
runtime provenance/artifact check passed with SVG validation disabled.
This is local Windows acceptance; full hosted CI and final Docker/name cutover
are separate integration checks.

**2026-11-09 P2.5 fourth slice, embedded-only variant source builds:**
The maintained variant source projection rejects Rules databases without
source-matched embedded deployed objects even when a legacy JSON sidecar is
present. Complete-set and maintained candidate/variant builders no longer
supply that sidecar argument; a temporarily ignored optional argument keeps
retirement-stage one-use callers importable. The source snapshot no longer
conditionally hashes the legacy publication. Focused variant-usage tests
passed **98 cases** including negative sidecar/output-preservation checks.
The complete database-set builder suite passed **16 cases** on the initial
candidate; after removing an unreachable legacy-only digest expression,
the representative repeatable complete-build case passed again.
The targeted v10 variant-publication storage test also passed.
Ruff, canonical Pyright (0 errors), documentation checks, Git whitespace
checks and tracked runtime provenance verification passed (SVG checks disabled).
No tracked publication, deployment or final filename/default was changed.

**2026-11-09 P2.5 fifth slice, retired historical terrain staging commands:**
The standalone `stage_promoted_terrain_artifacts` and
`verify_staged_release_pair` module entrypoints now fail explicitly instead
of staging/validating legacy Rules/JSON release pairs. Their imported
historical helpers remain temporarily available for the planned atomic
tool/test deletion; no runtime or source-projection path was changed.
Both CLI smoke invocations returned the expected retirement errors.
Focused staging/helper regressions passed **11 tests** across
`test_promoted_terrain_artifacts` (3),
`test_verify_staged_release_pair` (5) and
`test_legacy_staging_schema_guards` (3). Ruff, canonical Pyright (0 errors),
documentation lint/links/backlog and Git whitespace checks passed.
The plan records the five-file removal group, associated test-section
registry updates and independently maintained source/integrity guards.
This is command retirement, **not** physical helper/test file removal;
no Docker or deployment validation was run for this slice.

**2026-11-09 P2.5 sixth slice, physical legacy staging deletion:**
At commit `15a2ed23`, the two superseded terrain staging/verification
tools and their three historical test modules were physically deleted
together with their three `config/testing/test-sections.json` entries.
No active build, CLI, CI or deployment consumer required the removed tools.
The old runnable reproduction instructions were replaced with historical
provenance and a reference to Git history. Current maintained regressions
on the synchronized Windows checkout passed **60 cases**:
test-section discovery (15), Restrictions chart storage/API (15),
selected database-set health (20), deployed-object storage/build/serving (9)
and core Rules export provenance (1). Ruff, canonical Pyright (0 errors),
documentation lint/links/backlog, Git whitespace and tracked runtime
artifact/provenance verification passed (SVG checks disabled). The removal
commit's hosted installed-wheel and deployment-smoke runs passed; Source
checks were still in progress when reviewed. No full suite, direct Docker
run or deployment was performed as part of this slice.

**2026-11-09 P2.5 seventh slice, retired pre-promotion terrain proposal:**
At `4dbbb0d3`, the maintained source audit started requiring both
accepted Special Terrain / Access Width rules and their N5.3 citations;
negative tests prove that removing both rule records or changing the
Access Width source page fails closed. At `7330c310`, the one-use
terrain reference stager, staging-only tests, and superseded proposal JSON
were deleted together with the single test-section registry entry.
The authoritative accepted definitions and exact source examples remain
in curated Rules and its maintained tests, not a second proposal source.
Post-deletion focused validation passed **56 tests**: source/PDF/API
(20), test-section registry (15), selected database-set health (20)
and core Rules export provenance (1). Ruff, canonical Pyright (0
errors), docs lint/links/backlog, Git whitespace and tracked runtime
artifact/provenance checks passed (SVG validation disabled).
No direct Docker or full suite run was performed.

**2026-11-10 P2.5 eighth slice, v9 profile/summary promoters:**
Commit `dab737d1` deleted the completed Hackable and paragraph-layout
v9 promotion modules without touching current curated Rules or release
artifacts. Their retained assertions are independently covered by
the bilingual Hackable PDF pin/source tests, fresh Rules export and
published profile-help API, and curated long-summary paragraph test.
The historical paragraph-only V1S-082 commands were removed from the
maintained testing instructions. No staging-only test modules or
test-section entries were attached to either retired module.
Focused tests on the deletion commit: **5 passed** (Hackable EN/ES PDF
pins, fresh Rules export/API, long-summary paragraphs and profile-help
list). Ruff, canonical Pyright (0 errors), documentation lint/links/backlog,
Git whitespace and tracked runtime provenance passed (SVG checks disabled).
No full suite, direct Docker run or deployment was performed.

**2026-11-10 P2.5 ninth slice, logical SQLite rebuild comparison:**
`same_logical_rules_contents` now belongs to
`infinity_db.sqlite_comparison`, independent of legacy v9 source
promotion or JSON publication. It reads SQLite files in read-only mode,
compares identity/encoding/page-size pragmas, exact schema objects and
the multiset of every table's rows (including optimizer statistics),
and returns false for missing or invalid files without creating them.
`tests/test_rules_rebuild_logical_equality.py` tests the maintained
contract directly, including cross-host header and row-order variance,
schema drift, changed data and missing/invalid files. An older v9-only
Lieutenant comparison case was retired because its useful insertion
order invariant is now covered here. The legacy exporter re-exports
the comparator temporarily for historical callers; it does not own
this validation contract. Focused Windows checks passed **7 tests**:
logical comparison (4), source-variant selection (1), the current
selected-PDF pin/export invariant (1) and repeatable complete database-set
build (1). Ruff, canonical Pyright (0 errors), docs lint/links/backlog and
Git whitespace checks passed. No full suite, direct Docker run or
deployment was performed.

**2026-11-10 P2.5 tenth slice, standalone turn and Immunity staging:**
The Game Sequence/Order Pool source test no longer imports the v9
paired-publication promoter. It now checks bilingual PDF hashes,
exact curated source identity/scope/citations, ordered turn and Order
Pool semantics, SRC-031 disclosure, and current Rules/API/search parity.
The former v9 paired-publication rebuild test was removed.
The Plasma/Immunity staging script is superseded by independently
maintained pinned source, Army Weapon, Rules and API tests for Enhanced
and Critical cases. Focused tests passed **27 cases**: Game Sequence/Order
Pool (5), Plasma Combined Saving Roll (3), Plasma Critical (4) and
test-section registry (15). Ruff, canonical Pyright (0 errors),
docs lint/links/backlog, Git whitespace and tracked runtime artifact
provenance checks passed (SVG excluded). No full suite or direct
Docker run was performed, and no deployment occurred.

**2026-11-10 P2.5 eleventh slice, Cover/terrain-condition promoters:**
The old v9 Rules/loose-object paired-publication and repeated-promotion
tests were removed from `tests/test_cover_publication.py` and
`tests/test_terrain_condition_publication.py`. Both suites now own exact
accepted PDF citation sets, curated rule identities, role and current N5
scope. Their remaining tests enforce reviewed Cover/Climb/Jump/Climbing
Plus and Difficult Terrain/Saturation/Terrain semantics, pinned N5.3
source evidence, composed Rules database parity, and public API, search
and FAQ behavior. These remain current-purpose tests independent of the
deleted migration entrypoints. Deterministic rebuilding and selected
database-set integrity remain covered by the maintained builder/health
suites; no historical loose-JSON interface was retained for its own test.
Focused Windows validation passed **43 tests**: Cover (4), terrain
conditions (3), test-section registry (15), complete selected-set
repeatable build (1), and selected-set health/fail-closed behavior (20).
Ruff, canonical Pyright (0 errors), docs lint/links/backlog, Git
whitespace, and tracked runtime artifact/provenance checks passed
(SVG verification excluded). No full suite, Docker run, or deployment
was performed.

**2026-11-10 P2.5 twelfth slice, ARO/movement/geometry v9 promoters:**
The three accepted source and API suites now own their N5.3 citation
tables and canonical record checks (identity, N5 scope, definition role),
without importing historical v9 promoters. Their staged-pair rebuild and
rollback-only tests were removed; equivalent current-purpose database
set and logical SQLite comparison tests remain maintained separately.
The shared responsive Chromium acceptance fixture now calls
`validate_database_set` for embedded deployed objects before navigating
the ARO/movement/geometry/Cover/Terrain family; no loose
`deployed-objects.json` fallback is needed. Historical code and original
publication evidence remain recoverable through Git history.
Focused Windows validation passed **49 cases**: ARO (4), movement (3),
geometry (4), shared responsive Chromium acceptance across three
viewports (3), selected database-set health (20) and test-section
registry (15). Ruff, canonical Pyright (0 errors), docs lint/links/backlog,
Git whitespace and tracked runtime artifact/provenance checks passed
(SVG validation excluded). The full suite, direct Docker validation and
deployment were not performed.

**2026-11-10 P2.5 thirteenth slice, source-variant v9 reviewers:**
The five one-use Lieutenant, Terrain, Camouflage, Combat Jump and
Infiltration source review/promote wrappers have been retired. Their
`test_*_review_gate_*` cases reran the completed v9
Rules/loose-deployed-object matched-publication rebuild verification,
not independent current data semantics. The maintained
`tests/test_audit_source_variant_inputs.py` continues to verify
individual pinned Army source occurrence signatures, raw owner scope,
approved typed extra effects, unresolved qualifiers (including
Infiltration bare ReRoll and Religious Troop Total), and negative
semantic mutations. No independent source finding was deleted.
`infinity_db.sqlite_comparison` and `infinity_db.database_set`
separately own current rebuild-equivalence and selected-set integrity;
historical tool code is recoverable from Git.
Focused Windows validation passed **138 tests**: the entire maintained
source-variant module (99), read-only logical SQLite rebuild comparison
(4), current selected database-set integrity/fail-closed behavior (20)
and test-section registry (15). Ruff, canonical Pyright (0 errors),
docs lint/links/backlog, Git whitespace and tracked runtime artifact/
provenance verification passed (SVG excluded). No full suite, direct
Docker test or deployment was performed.

**2026-11-10 P2.5 fourteenth slice, Commlink v9 staging retirement:**
The one-use Commlink paired-release stager and its synthetic pre-promotion
rollback/tamper tests were retired. The optional Reinforcements annex
test now uses a fresh current-format Rules export and checks three
annex records plus Commlink's reviewed +1/+2 effects against active
Rules. Maintained source-inventory, N4-origin authority boundaries,
exact Army loadout provenance and curated fail-closed variant grammar
remain independent of v9 promotion machinery. Historical command
examples were converted to dated evidence, not runnable instructions.
Focused validation passed **63 tests**: optional annex (4), Commlink
source/fresh export (2), Reinforcements applicability (16), database-set
health (20), test registry (15), and invalid Commlink variants (6).
Ruff, canonical Pyright (0 errors), docs lint/links/backlog, Git
whitespace and tracked runtime artifact/provenance checks passed
(SVG validation excluded). No full suite, direct Docker test or
deployment was performed.

**2026-11-10 P2.5 fifteenth slice, citation migration stagers:**
The 14 N5.3 source/manifest citations and four Hacking Device p.58
citations are already accepted; their one-use v9 paired-publication
stagers and stage/rollback-only tests were retired. The maintained
14-citation audit now requires 0 pending / 14 migrated, preserving
cross-manifest ownership, exact reviewed pages and pinned English PDF
checks. The independent device/program chart audit now requires all
four accepted p.58 citations and verifies the exact citation rows
in the current Rules database. Restrictions are verified through
relational chart storage and complete selected-set builds rather than
an incomplete isolated Rules export or old v9 promotion gate.
Focused Windows checks passed **51 tests**: 14-citation source audit
(4), Hacking Device source/chart/Rules parity (11), Restrictions
storage (15), selected-set health (20), repeatable complete builder
(1). Ruff, canonical Pyright (0 errors), docs lint/links/backlog,
Git whitespace and tracked runtime artifact/provenance checks passed
(SVG excluded). No full suite, direct Docker run or deployment occurred.

**2026-11-10 P2.5 sixteenth slice, v9 Restrictions transition retirement:**
The completed v9 Restrictions/source-pin/variant metadata migration
checker matrix and synthetic source-delta fixtures were retired along
with the one-use `tools/restrictions_v9_release` stager/promoter.
Maintained source variants now compare independently reviewed Lieutenant,
Terrain, Combat Jump and Camouflage effects using fresh
`export_rules_database` results and the currently selected Rules DB.
The surviving `test_restriction_storage_candidate.py` cases protect
supported v8/v9 reader and explicit CLI compatibility, plus reviewed
PDF pin export. Relational Restrictions and complete database-set tests
own ongoing integrity. Historical publication-rollback tests are no
longer current development obligations; Git retains the old migration
implementation. Focused Windows validation passed **170 tests**:
source-variant semantics (99), Restrictions CLI/reader and PDF pins (17),
relational Restrictions storage (15), selected database-set integrity
(20), SQLite logical rebuild comparison (4), and test-section registry
(15). Ruff, canonical Pyright (0 errors), docs lint/links/backlog,
Git whitespace and tracked runtime artifact/provenance checks passed
(SVG excluded). No full suite, direct Docker run or deployment occurred.

**2026-11-10 P2.5 seventeenth slice, database-backed research boundaries:**
Core-scenario and terrain/scenery audits now read explicitly selected embedded
deployed objects and report Army/Rules file hashes. Their legacy JSON adapters
are retired, and Pheroware citation parity uses canonical Rules export.
Focused Windows validation passed **233 tests, zero skips** across
`test_core_scenario_object_boundary.py`, `test_terrain_scenery_source_gaps.py`
and `test_weaponry_catalog_api.py` (33.15 seconds). This includes independent
database locations/names, CLI selection, malformed adjacent JSON, exact hash
reporting, nonmutation, and rejection of missing files, v8 models, corrupt
Rules, missing embedded tables and mismatched Army bytes. Existing source PDF,
geometry, scoring, terrain-cell, citation and API checks also passed. Ruff,
focused Pyright (0 errors), docs lint/links/backlog and Git whitespace passed.
No full suite, Linux, Docker or hosted acceptance is implied.

**2026-11-10 P2.5 eighteenth slice, completed release diagnostics:**
Removed the one-use v9-to-v10 promotion path and its schema-preserving
export/rebuild diagnostics, plus the physically retained Restrictions v9
transition module whose callers/tests had already been retired. Current
candidate build/check, checkout assembly and complete-set validation remain.
The maintained logical SQLite comparator owns cross-host semantic comparison;
frozen source evidence and hashes remain in the source audit and Git history.
Focused Windows validation passed **223 tests, zero skips**: 109 storage,
candidate/checkout, complete-builder, database-set, Restrictions compatibility,
logical-comparison and deployment-script tests (168.44 seconds), followed by
114 current source-variant and section-registry tests (43.32 seconds). Ruff,
focused Pyright (0 errors), CLI help, docs lint/links/backlog, Git whitespace
and tracked runtime artifact/provenance verification passed (SVG excluded).
Current code/config/workflows have no imports of the retired modules.
No full suite, Linux, Docker or hosted acceptance is implied. This internal
migration-tool retirement needs no release-note entry.

**2026-11-10 P2.5 nineteenth slice, retired deployed-object JSON adapters:**
Removed the standalone JSON loader and publisher adapter after migrating all
source/storage/browser consumers. Source-model, occurrence/reverse-use and
embedded-release parity checks remain; the browser fixture now uses only
matched databases. The shared storage guard retains valid object/source,
attribute/provenance, delivery and Unit/Include context checks at insertion
and read time. It rejects a self-referential Rules hash before staging.
Focused Windows validation passed **96 distinct tests, zero skips**: 60 current
source, storage, Restrictions, database-set and API/browser cases (95.18 seconds),
seven additional embedded-row tampering cases (4.25 seconds), and 29 complete-build,
variant-storage and section-registry cases (35.74 seconds). Chromium retained
navigation, missing-value, request/page-error and overflow checks at
1440/390/320 px. Ruff, focused Pyright (0 errors), docs lint/links/backlog,
Git whitespace and tracked runtime artifact/provenance checks passed
(SVG excluded). No full suite, Linux, Docker or hosted acceptance is implied.
This internal adapter retirement needs no separate release-note entry.

**2026-11-10 P2.5 twentieth slice and transition closeout:**
Retired explicit v8/v9 Rules CLI builds and v1 exact-variant publications.
Current builds preserve reviewed Restrictions/deployed objects, tracked-file
write refusal and checkout assembly; all variant consumers use the v2-only
loader without a deployed-object sidecar argument. Low-level source-semantic
fixtures retain their independent exporter/read-model checks. Wheel smoke
creates its controlled Rules fixture through the installed canonical API,
preserving isolated CLI, configuration, normal and asset-free runtime coverage.
Focused Windows validation passed **287 tests, zero skips**: 161 variant/source,
CLI, Rules, wheel-isolation and variant-browser cases (62.03 seconds), followed
by 94 storage, actual candidate/checkout assembly, database-set, deployment-script
and section-registry cases (81.77 seconds), plus 32 release-note/metadata
regressions (1.10 seconds). Source/browser checks retain every
published group's canonical ownership, stale-pair refusal, Developer mode,
request/page errors and overflow assertions at 1440/390/320 px. Rejection tests
cover v1 and legacy fingerprint inputs without modifying files.
An offline-built wheel (`1.0.1`, SHA-256
`0a146f05b064b6ce1a2fcd92fe3064b6de5768248993f8b53ca59317edf0c20f`)
passed normal and asset-free installed runtime smoke in a disposable environment
outside the checkout. This is development packaging evidence, not publication.
Ruff, focused Pyright (0 errors), docs lint/links/backlog, Git whitespace and
tracked runtime artifact/provenance verification passed (SVG excluded).
The finalized-release metadata command still rejects the pending 1.1.0
heading and package-version difference, with exactly the same two errors as
the starting revision; it is not a passed release gate or a new regression.
This closes the bounded P2.5 transition; P2.6/P2.7/P2.8 retain filename/default
cutover, assembly removal and final local/container integration acceptance.
No full suite, Linux, hosted or release acceptance is implied.

**2026-11-10 P2.6 preparation, shared complete-set startup:**
The complete builder and application factory now share the validator's complete
mode, requiring Army v31/Rules v17 and recorded matched provenance. The parity
tool's `--db-dir` checks the selected set through this factory, rejecting mixed
selectors, transitional/partial schemas, missing directories and unrecorded
provenance without selecting fallback files or creating outputs.
Focused Windows validation passed **49 tests, zero skips** across
`test_database_set.py`, `test_database_set_builder.py` and
`test_runtime_semantic_baseline.py` (101.57 seconds), including actual application
composition, repeatable fixture builds, unchanged-output failure and interrupted
replacement recovery. Ruff, focused Pyright (0 errors), docs lint/links/backlog,
Git whitespace and tracked artifact/provenance checks passed (SVG excluded).
A fresh offline build of pinned `JSON 20260929-114335.zip` (SHA-256
`f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`)
passed 73 normalization checks with the existing 116 source warnings. Its complete
set passed shared validation and all **41 pinned semantic/HTML/SVG probes** through
`--db-dir`, with the reviewed Restrictions static-to-API route alias.
Build-set ID:
`ba3dd0533872b8773a4fdbd209e99a6cce005759d273af18be1d4c7480a48baa`.
The ignored alternate output had `infinity.db` SHA-256
`111c134d8d8760c09157b7ceb713400510c68c6ae07803ad930ccab0d94cad4f`
and `rules.db` SHA-256
`989013625357d6d2762e48ca4b6ee39880997109e7d814fcc345f153da7c4dc7`.
This was one real source build and focused startup/parity acceptance before
the coordinated P2.6 cutover. It is retained as historical preparation evidence;
it is not a cross-platform determinism result.

**2026-11-10 P2.6 filename/default and shared serving cutover:**
The default complete builder, CLI/WSGI directory selection, tracked
`army.db`/`rules_n5.db`, Docker packaging, deployment scripts, CI and
cache identity now use the same validated two-file set without filename
or environment aliases. The source ZIP
`JSON 20260929-114335.zip` (SHA-256
`f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`)
produced **two byte-identical complete builds**, each with 41 pinned API,
HTML and scenario geometry probes and all reviewed inventories intact.
The tracked Army/Rules database hashes match the resulting
`63b090d1e580`/`99650884f196` prefixes exactly. Full deployment-asset
verification passed: **808/808** SVGs and **808/808** browser references,
with embedded runtime data and source checks valid.

**120 focused tests passed** across database-set, builder, CLI, deployment,
release-scope and P1 semantic-baseline modules. Nine optional variant-browser
cases were skipped because their ignored pinned raw archive was unavailable;
they are not browser acceptance evidence. Ruff, Pyright (zero errors),
documentation lint/links/backlog and Git whitespace passed. This completes
the bounded P2.6 data/entrypoint cutover on `dev/v1.1.0`; it is not a full
suite, Linux, hosted, independent local-server or Docker acceptance result.
P2.7 owns residual publication-ceremony cleanup and P2.8 owns the final
local/container integration check.

**2026-11-10 P2.7 first slice, loose publication retirement:**
The variant candidate tool no longer publishes JSON; source inspection requires
an explicit paired `--raw-db`. The Weapon utility is now a read-only checker
of the embedded Rules projection against maintained source reviews. The
deployment validator rejects missing/mismatched embedded variants and Weapon
citations without sidecar fallback. The determinism manifest hashes reviewed
Weapon citation meaning in memory, rather than creating JSON output from
the unrelated tracked release pair. Its normal fixture build and manifest
generation passed; no tracked runtime databases were rebuilt or changed.

Focused Windows validation: **183 passed, 2 skipped** across
`test_variant_usage.py` (100 pass, 2 skip),
`test_weapon_profile_publication.py` (24 pass),
`test_verify_deployment_assets.py` (13 pass),
`test_deployment_scripts.py` (43 pass), and
`test_compare_determinism_manifests.py` (3 pass).
Full deployment-asset verification passed with **808/808** published SVGs
and browser references. Ruff, Pyright (zero errors), documentation
lint/links/backlog and Git whitespace checks passed. This is focused
tool/source/deployment integration evidence, not a full suite,
independent Linux/Docker image, hosted CI or P2.8 acceptance.

**2026-11-10 P2.7 second slice, runtime fallback removal:**
The runtime no longer reads `variant-usage.json` or
`weapon-profile-sources.json`, even for explicit low-level database
fixtures. The selected-set validator rejects former v10/v11 JSON-dependent
layouts, while v12–v16 two-file relational fixtures remain inspectable
outside complete serving. Public runtime startup continues to require the
current v31/v17 pair with shared provenance. API cache identity and
release-candidate/baseline tooling hash the same canonical inventory of the
selected database filenames and bytes. Obsolete file-loader tests have
been removed or replaced with embedded source/corruption checks.

Two independent full source-ZIP builds retained every reviewed inventory,
passed 41 pinned API/geometry probes each, and produced byte-identical
`army.db` and `rules_n5.db` outputs (expected SHA-256:
`e306700aa2ea02729b25a82edb732bba74465daf7fadb09191c10f346d7e7dfe`
and `26b27d6e4b2394d2535817e5b0e153d16dd98b42e864149ce67922164929f8f5`
respectively). The regenerated tracked artifacts match both exact SHA-256
hashes. `tools.verify_deployment_assets` passed with 808/808 SVGs and
browser references, current source-input freshness and embedded citation
matching. The isolated acceptance tool did not publish the results;
`infinity-db build` regenerated the tracked pair. This completes P2.7;
P2.8 remains separate local/Docker acceptance.

Focused Windows results: **220 passed, 2 skipped** across database-set
(18), variant-usage (98 pass/2 skip), variant storage (13), Weapon citation
(14), deployed objects (12), complete builder (17), release-candidate
browser (16), source-reference baseline (1), P1 semantic baseline (10),
and CLI (21). Ruff and Pyright (zero errors) passed. This is not an
independent Linux, deployed Docker, full-suite or hosted acceptance result.

**2026-11-10 P2.8 local checkout and actual Docker hosting acceptance:**
The complete P2.7 pair was built from pinned Army ZIP and was already
byte-matched to the tracked artifacts. `tools.verify_checkout_server`
launched the actual checkout CLI server on loopback (both normal default
selection and explicit `--db-dir data/generated`), checked HTTP health
and exact snapshot identity, and verified **41/41** pinned representative
API/citation/HTML/JS/SVG responses in each mode. Both subprocesses were
stopped after acceptance. Snapshot:
`21e7ef4bb29739c006b7f17942140f9927fa8aeb1ec61b3af6e504a17a2c2925`.

An actual image built with Docker Desktop Linux engine **29.9.2** from the
same checked-out source and tracked pair passed the `tools.preview_runtime_image`
immutable file-set check (exactly `army.db` and `rules_n5.db`), embedded
reference checks (17 deployed objects, 151 variant groups, 69 Weapon
citations), health startup under read-only/container restrictions and
**41/41** pinned HTTP routes, including Battleground map SVG geometry.
The disposable container and image were removed. Source/deployment
verification passed **808/808** SVG assets and browser references.
A leftover ignored `data/generated/deployed-objects.json` is not used
by checkout runtime and is absent from the actual image. Neither hosting
path depends on JSON sidecars.

Repeat the acceptance from the repository root with:

```powershell
.\.venv\Scripts\python.exe -m tools.verify_checkout_server
.\.venv\Scripts\python.exe -m tools.verify_checkout_server --db-dir data/generated
.\.venv\Scripts\python.exe -m tools.preview_runtime_image --source-dir data/generated --tag infinity-db:preview-local
```

**P2 exit accepted** on commit
`52e0a4c5b99cf4c7db3ab2a72252970f124fd64c` (before documentation
closeout). The P2.8 checks are integration/semantic acceptance on Windows
plus its local Docker Linux engine, not a full project suite, independent
Linux-dev worker run, hosted CI, deployment, or manual visual-browser test.

**2026-11-10 P3.2 standalone ITS database — focused pre-commit evidence:**
The independent `tools.build_its_season` builder and
`src/infinity_db/its_season_database.py` produce a schema-v1 ITS 18
SQLite artifact under ignored `data/work/its/`, while the current
`data/generated/` two-file serving contract remains unchanged. The
source and official PDF are SHA-bound, the builder/parser modules are
fingerprinted, and N5 compatibility `5.3` is explicit. The new database
contains Battleground, all three authored geometry configurations and all
three citations. Its canonical content SHA-256 matches the existing
`rules_n5.db` publication. Repeated builds are byte-identical.

The focused `tests/test_its_season_database.py` suite covers schema,
source/compatibility provenance, exact season-revision selection, corrupt
record/geometry refusal, invalid source preserving the prior artifact,
read-only checking, and refusal to publish under `data/generated/`.
The existing Scenario catalog regression remains green (**43 passed**),
with **13/13** new ITS tests passed. Ruff, Pyright and documentation checks
pass. The source-bound Army/Rules pair was regenerated from pinned inputs;
`tools.verify_deployment_assets` now passes, including **808/808** published
SVGs, **808/808** browser references and embedded source/citation checks.
No new ITS DB is authoritative for web serving, and no full-suite/hosted/Docker
P3 acceptance is claimed.

**2026-11-10 P3.3 ITS 18 pilot and source-policy ownership — focused
pre-commit evidence:** `tools.verify_its_pilot_parity` builds `its_18.db`
from the maintained ITS Season 18 source in an ignored temporary directory,
selects `scenario:battleground` under `its-18@2026.09.01`, and compares
the standalone scenario through the shared ScenarioCatalog and
`_enrich_scenario_api_item` against the existing two-file WSGI runtime.
**6/6 full JSON scenario details** and **24/24 exact SVG byte strings**
matched, covering all 150–400 Army Point selections, light/dark themes and
inch/centimetre rendering. A negative test changes source-authored mission
copy and confirms parity fails. Publication digest remains
`2dd4ab5c9f7c83bcdc4f94e156f29c4b6c2d9e34770a03da85e8886f4c0d5b31`.

Three source-cited ITS 18 policy records for Spec-Ops (official tournaments),
TEAM-OPS and optional Reinforcements now occupy dedicated ITS schema-v2
tables rather than the generic N5 Rules catalog. Read-only integrity,
scoped selection, malformed applicability, citation corruption and
absence from core Rules are covered by focused tests. The existing
Rules interaction audit and standalone Rules build pass.

The tracked Army/Rules pair was regenerated from pinned inputs after these
maintained source changes. The complete `tools.verify_deployment_assets`
gate now passes **808/808** published SVGs and **808/808** browser references,
with embedded runtime data and reviewed citations source-matched. Final
focused evidence: **17/17** ITS database tests, **2/2** P3.3 parity tests,
**43/43** existing Scenario catalog tests; Ruff, Pyright, Rules audit/build,
docs and Git whitespace checks passed. P3.4 owns actual cross-DB serving;
this is an independent candidate/publication comparison, **not** a deployed
three-database runtime test or a complete browser/CI release gate.

**2026-11-10 P3.4 first registry slice — validated but not yet served:**
The backend `PublicationRegistry` now validates exact ITS season identity and
core revision against the current N5 scenario publication, checks ITS policy
targets and external mission dependencies against composed N5 records, and
requires typed owner/revision selection without fallback or default policy
application. The existing two-file `ScenarioCatalog` and HTTP paths remain
unchanged; packaging `its_18.db` awaits the coordinated cutover.

Focused checks: **10/10** new registry tests, **43/43** Scenario catalog
tests, **17/17** ITS builder/selection tests and **166/166** Rules database
tests. Ruff, canonical Pyright, documentation/link checks and Git whitespace
checks passed. The updated MCP integrated build regenerated the source-bound
`army.db`/`rules_n5.db` pair (build set
`4117851f06cd81862878d257de912d3a5a489ac2c974f31aa4fc1560a42ce800`);
deployment assets passed **808/808** SVGs and browser references. A real
checkout CLI server passed **41/41** pinned HTTP paths and health using the
regenerated pair; the P3.3 parity verifier still passed **6/6** API JSON and
**24/24** byte-identical SVG comparisons. This is local validation, not a
three-database hosted/Docker/CI acceptance or a full suite.

**2026-11-10 P3.4 explicit HTTP candidate — focused acceptance:** The
`create_app(..., season_databases={...})` fixture registers an independent
ITS 18 database. Its six Battleground JSON responses and 24 SVG variants
match the existing HTTP implementation exactly; the N5 default, explicit
collection selection and fail-closed absent season/revision remain unchanged.
The runtime snapshot/ETag differs when the ITS database is registered.
`ScenarioCatalog` and the new registry remain separately testable.
This does **not** validate the still-pending automatic three-file serving,
Docker image, or release artifacts.

**2026-11-10 P3.4 integrated three-file serving candidate:**
The normal `infinity-db build` generated Army v31, Rules v17 and ITS v2
(build set `f97eb0a1aee25d768736c2feeb213af26dfb02349aac68acd2cbfffd21e649e0`).
The complete validator now requires all three, binds ITS source identity to
the Army/Rules build manifest, checks season/core compatibility and typed
cross-domain references, and hashes the full set for runtime caches. The
ordinary checkout CLI and Docker runtime use the strict three-file factory.
Focused results: database-set **22/22**, builder **18/18**, deployment
scripts **45/45**, publication registry **13/13**, checkout HTTP **41/41**,
Docker preview HTTP **41/41** plus a direct ITS-owned Battleground probe,
and 808/808 SVG and browser-reference asset verification. Pyright, Ruff,
documentation checks and Git whitespace checks passed. The initial Docker
build failed
because `.dockerignore` omitted `its_18.db`; after correction, the clean
disposable image built and passed. No hosted three-file CI acceptance yet.
The first publication required a one-time local `git add`/`git commit`
because the MCP restricted newly tracked binary database files. The complete
set was committed as `1b8d527de61d0751e7387b7b0d9e62013cf86ff0` and
synchronized with GitHub. Hosted wheel and deployment smoke passed; the
Ubuntu 3.11 Source matrix failed on retired CLI/Rules fixture assumptions
and two deployment-asset season fixture stubs. A focused season-stub correction
is included in the following P3.4 cleanup. Overall hosted Source CI remains
unaccepted until the separate full-suite fixture migration is addressed.

**2026-11-10 P3.4 ITS publication ownership retirement (development checkout):**
The normal three-database build completed with build-set
`29ead25e1ab15370d05c976fa2b5b9ad5a5094051f325ff54d5ce006e8c9d23a`.
The N5 Rules exporter now excludes ITS-owned collections and the strict
complete-set validator rejects a shadow ITS collection in Rules. A frozen
pre-cutover digest guards six Battleground API JSON payloads and 24 SVG
byte streams. Registry tests passed **14/14**, scenario catalog **43/43**,
scenario API **95 passed / 4 skipped**, Rules database **166/166**,
strict database set **23/23**, complete-set builder **18/18**,
ITS database **17/17**, standalone ITS parity **2/2** and deployment-asset
fixtures **13/13**; both modified Rules-only historical report assertions
passed. Deployment source and asset verification passed 808/808 SVG assets
and 808/808 browser references. Real checkout CLI and disposable Docker
image parity each passed 41/41 pinned paths; the Docker image was removed.
The complete historical
report module had two unrelated local failures when optional research tests
encountered a stale ignored `data/generated/army.raw.db` sibling; they are
not serving inputs and were not changed. Hosted full Source matrix is still
failing older standalone Rules-v8 and retired CLI fixture expectations; do
not treat this section as a hosted-CI pass.

## Phased development and validation

**Normal workflow:** orient to the task and checkout, implement one coherent
change, run the relevant focused checks, review/deliver the diff, and report
actual results. Tests may be designed, written and executed during the same
implementation pass. Choose checks by actual behavior and risk, not by a
per-edit validation quota. This is the canonical short development lifecycle;
see the [restructuring decision](restructuring-plan.md#p02--proposed-normal-task-lifecycle-2026-11-09).

- **Ordinary changes:** run appropriate new or existing focused regressions
  plus lint/type/docs/data checks when relevant. For documentation-only edits,
  documentation checks suffice unless the change affects executable examples
  or behavior. Fix failed checks before claiming acceptance.
- **Immediate gates:** security, schema/data integrity, source authority and
  publication changes require their relevant correctness checks now. Report a
  blocker when a required check cannot run; do not label it passed.
- **Genuinely deferred checks:** record a concrete VD only if required test
  design is blocked; record VR only for required execution that cannot yet run
  (unavailable host/assets, dependent integration state, etc.). Specify the
  tested contract, owner, revision/inputs and resumption trigger. Do **not**
  create queue items for work fully tested in the current task.
- **Batching:** related changes can share a focused impact test run on a
  compatible revision. Full suites run for independently identified cumulative,
  integration or release risks, not because the queue reached a count.
- **Pending acceptance:** a task with an outstanding *required* check is not
  fully verified. A separately owned hosted CI/release gate remains pending
  without requiring routine development to reproduce the release gate.
  Never claim dispatch, a failed/skipped check or an older SHA as success.

The [deferred-validation queue](validation-queue.md#queue-rules) is the single
register for open VD/VR items and their triggers. It has **no numeric
thresholds, automatic seven-day deadline or mandatory drain-to-zero cycle**.
Review it when a prerequisite becomes available, before relevant
merge/release acceptance, or when scheduling a deliberate compatible batch.
Independent development can proceed while tests run in a different pinned
checkout with no shared mutable inputs; see
[parallel Windows and Linux validation](#parallel-windows-development-and-linux-validation).

**Coherent change batches:** prefer a reviewable group of related changes over
a separate administrative cycle for each edit. Preserve unrelated changes,
address cross-layer consumers, and make a single meaningful validation and
commit where appropriate. Do not use batching to postpone a known critical
correctness check or to hide outstanding acceptance.

### Portable cross-browser critical-journey cohort (v1.0 gate)

**Project domains:** Web frontend, Project infrastructure

Use `python -m tools.run_cross_browser_compatibility --engine chromium` for
an explicitly selected local engine; `firefox`, `webkit` and `msedge` are
also supported. Install `playwright==1.64.1` and that engine using
`python -m playwright install <engine>` first (on Linux CI the matching OS
libraries are installed with `--with-deps`). The helper runs the dedicated
`tests/test_cross_browser_compatibility.py` cohort with one engine, exits
nonzero on failed/missing browser setup and writes JUnit and failure traces
under ignored `local/cross-browser-compatibility/`. The ordinary source
suite does not require Playwright and skips this opt-in module without an
engine. The hosted matrix is [optional for v1.1+, mandatory for v1.0.x](ci.md#cross-browser-release-compatibility-gate).
A successful local cohort cannot replace any selected hosted gate, and the
81-page Unit matrix is not multiplied across browser engines.

### Focused-first VR execution

**Default: focused tests during normal implementation.** For a newly
written test, run it immediately when practical. For deferred VR execution,
run a **small, risk-based impact set first** and fix failures at that scope.
Execute the complete suite only for a separately identified cumulative,
integration or release gate, or when cross-cutting risk cannot be bounded by
focused tests. Record the reason for any full-suite dispatch. The presence
or number of queued VRs does not itself justify a broad run.

Build the impact set from **all modified inputs and their consumers**, not
only the new test files. Check broad contracts affected by each changed
layer. For example, a curated rules summary, citations or `rules.db`
publication must get the applicable tests for:

- Curated schema, text formatting and long-summary layout
  (`tests/test_curated.py`).
- Current/frozen source-locator and record-count expectations
  (`tests/test_report_reference_baseline.py`), especially when citations
  or source metadata changed.
- Stored rules, matched deployed-object/variant publications and API
  parity (existing source/rules/database tests and publication `--check`
  commands).
- The affected normal-browser routes, citations and navigation at required
  widths; existing shared route tests should accompany new selectors.

An unchanged test module can still have a stale assertion after a source
change. Conversely, a browser-only test addition does not require a new
full source corpus review. List precise selectors for each affected layer;
use existing test-section/module discovery when individual names are not
known. Run the union once for compatible VRs, inspect the failures, and
only widen to the **next relevant section** if the focused evidence reveals
a wider problem. Do not launch a full suite in order to find out which
focused tests should have been selected.

**Full-suite dispatch decision:** before starting one, identify the
separately required gate, its affected scope, prior focused green result,
pinned commit/assets and whether an earlier equivalent full run is
reusable. A known focused failure is repaired **before** any new full run
unless the release owner specifically needs an exhaustive failure census.
A full run remains mandatory for the final release gate and independently
specified CI/preflight gates. No policy here waives them.

**2026-11-06 V1S-082 focused-first VR closure:** At clean committed
`f349ddcb656a81a3bbe2a31070e9c2761b32431b`, the pinned Linux
`linux-dev` job `linux-dev:a6e7bce46e664b8da5baeb3864431370`
passed **48/48 selected tests**, zero skips, with **808/808** SVGs.
This single impact set covered VR-0118 Hackable API/browser, VR-0121
development-status and backlog, VR-0122 Isolated rule/API/browser and
summary layout, VR-0123 pilot page identity and current locator counts,
and VR-0124 MOV anchor/TinBot source-169 variant and negative-route
browser cases. On Windows, job `0a8f3dbdccef4a539058b0190e3981ca`
passed **3/3** pinned bilingual PDF/Isolated source cases and job
`c5bb998bb2c744a7b19471568a723afc` passed **24/24** local
provider/status, TinBot source-extras/catalog and variant publication
cases, all with zero skips. Linux matched deployed-object and
variant-usage `--check` both passed; the read-only online status query
resolved workers and exact-SHA GitHub runs. **VR-0118, VR-0121,
VR-0122, VR-0123 and VR-0124 local execution are satisfied** on this
revision. The full-suite V1S-090, exact-SHA hosted Source matrix and
frozen release-candidate gates remain separate; the earlier failed
full suite at `94103ef4` is not claimed green.

### Final maintained-reference and fragment browser acceptance (V1S-086)

**Project domains:** Web backend, Web frontend, Project infrastructure

On the unchanged frozen source/database pair at `3c8b16018f914fc1ee69fe769216a7c9e8eb47c2`,
`tools.run_checks --stage test --assets required --test-workers 2` passed
**77/77 tests with zero skips** across `test_public_relation_destinations`,
`test_application_rule_references` and `test_verify_rule_fragment_browser`.
All **808/808** processed SVGs were required. Published cross-domain API/page
destinations, Glossary references, Weapon local fragments and cited context
were covered without a new source-wide inventory. The previously accepted
[V1S-082 routing census](v1.0-source-coverage-audit.md#v1s-082-maintained-reference-routing-census-2026-11-07)
and [V1S-083 disclosure regressions](#known-source-disclosure-acceptance-v1s-083--vr-0137)
remain applicable to the unchanged published data and browser consumers.

The Weapon fragment verifier gained a `--self-host` mode for the tracked
Army/rules pair, removing the need for a separately running development server.
Its new ephemeral-server regression and existing unit tests passed **12/12**.
A separate real Chromium invocation of
`tools.verify_rule_fragment_browser --self-host` passed **69/69** checks at
1440/390/320 px in 248 seconds, following soft-navigation, source-backed
rule cards, Glossary-to-Weapon fragments and fresh deep links. The full
JSON report is under ignored `local/audits/v1s086-rule-fragments.json`.
Ruff, Pyright (0 errors/warnings) and the complete docs stage passed.
The later output-only progress indicator does not change browser assertions.
No source, database, publication or gameplay behavior was changed.
V1S-087–095, deferred manual gates, cumulative V1S-090, and exact-SHA hosted
CI remain independent. There are no open VD/VR entries.

### Frozen-pair source gates (V1S-085)

**Project domains:** Data processing, Project infrastructure

At `f1047cf4ee984e1b4ea15af79f2c52ac65497273`, the mandatory source
gates passed against the unchanged V1S-084 release pair:

- Source occupancy inspected **70 tables / 441 fields** using the matched
  raw sibling. **0/39** potentially unrepresented fields were populated;
  zero confirmed gap families and two existing scope decisions were retained.
- `tools.report_reference_baseline --army-archive` verified the pinned
  September 29 ZIP hash, all **58** source files, **4,137** Unit membership
  occurrences, **4,748** groups, **5,020** profiles and **12,993** loadout
  options, plus the published references, extras, Includes, Peripherals,
  Characteristics, Orders and global options against their source rows.
- `tools.audit_1_0_reference_inputs` matched the supplied English Core and
  FAQ PDF bytes to their declarations, checked **116/116** exact Wiki
  revisions, and verified **107** English plus **two** Spanish snapshot
  reference headings. Archive acquisition dates remain separate from edits.
- The current citation minimum remained **495/495**, zero metadata gaps;
  the four scoped source-disposition fingerprints validated without granting
  browser or whole-record approvals.
- The strict **1.0** interaction scope matched the actual runtime catalogs:
  **186/186 primary** (98 Skills, 31 Equipment, 33 Traits, 24 States) and
  **221/221 supporting** identities complete, zero pending. The 518 authored
  relations and 111 future interactions retain their existing scope.

Use the **explicit 1.0 scope**, independently of the historical checklist:

```powershell
.venv\Scripts\python.exe -m tools.audit_rules_interactions --catalog-scope data/curated/rules-interactions/catalog-scope-1.0.0.json --database data/generated/infinity.db --rules-database data/generated/rules.db --require-primary-release 1.0.0 --require-release 1.0.0
.venv\Scripts\python.exe -m tools.audit_rules_interactions --check-output docs/rules-interaction-checklist.md
```

The default historical 0.7 scope intentionally has a different denominator
and Commlink deferral. Passing it alone does not certify the 1.0 primary
catalog. Its generated checklist check also passed; no ledger was rewritten.
`tools.run_checks --stage rules --source-occupancy-gate` passed its occupancy,
historical checklist/supporting review and temporary rules-build checks.

The required-assets, two-worker Windows source regression batch passed
**288 tests with zero skips**. Its exact modules were
`test_audit_source_variant_inputs`, `test_other_source_variant_provenance`,
`test_martial_arts_variant_provenance`, `test_audit_source_presentation`,
`test_audit_1_0_reference_inputs`, `test_audit_rules_interactions`,
`test_report_reference_baseline`, `test_rules_rebuild_logical_equality`,
`test_source_coverage_dispositions` and `test_inspect_raw_archive`, all under
`tests/`. It verified full source-only occurrences rather than accepting
clean-CI skips for missing raw data. Required assets were **808/808** complete.

Reproducibility reused V1S-084's two byte-identical Windows builds; its
source and runtime code are unchanged. A further Windows rules rebuild with
SQLite **3.50.4** matched the tracked bytes. An independent pinned Linux
rebuild, job `linux-dev:5a17c2269ea64d46b4cf3021520f670b`, used SQLite
**3.46.1**: all logical rows, table definitions and reported identity/schema
pragmas matched, but **1,594 bytes** differed. Its hash was
`94b5c460d836d84a512118af79acd508c84bf8f1c17244d8aca903166d62c3dd`,
versus tracked
`90d600a5b7b0425ee590ef90891481433e179d4e96f4a7b1dbf26edfde672ca9`.
Both had 336 × 4096-byte pages. This is logical-equivalence evidence under
the [cross-host policy](v1.0-source-coverage-audit.md#cross-host-rules-rebuild-comparison-v1s-032-validation-2026-11-04),
not cross-host byte parity or permission to replace a shipped artifact.

Ignored `local/v1s085-*` reports retain the baseline/input/occupancy evidence,
rules stage, 288-test transcript and Linux comparison. No runtime, source,
artifact or maintained-policy change was needed. V1S-085 is closed; these
inventory/locator checks do not approve every clause or certify browser
completeness. V1S-086 onward, full Linux/local validation, hosted byte-comparison
and final release/human/operational gates remain independent. Nothing is deferred
in VD/VR.

### Release-matched rebuild and publication acceptance (V1S-084)

**Project domains:** Data processing, Web backend, Web frontend, Project infrastructure

At `f1f53563ba6b7358fc8bd514a833a2571abb1437`, two independent Windows
Army builds consumed the pinned `JSON 20260929-114335.zip` archive
(SHA-256 `f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75`).
Both used lossless reconstruction verification and the ordinary
`infinity-db build <archive> --compact --output-dir <local staging directory>`
pipeline. Each merged 58 source files, passed all **73** normalization checks
and matched the maintained **116-warning** source-anomaly baseline.

The rules database was rebuilt twice through the release-aware v9 exporter,
preserving Restrictions and compatibility. Each stage independently rebuilt
deployed objects, exact-variant usage and Weapon-profile citations from its
own Army/raw/rules pair. In **both stages**, all six files were byte-identical
to the active artifacts: `infinity.db`, `infinity.raw.db`, `rules.db`,
`deployed-objects.json`, `variant-usage.json` and `weapon-profile-sources.json`.
Database health required and validated the raw sibling; each staged app loaded
the matched publications. The complete processed symbol set and its source
binding passed against each staged pair: **808/808** published and
browser-referenced SVGs. No active artifact needed replacement, and their
hashes remained unchanged after acceptance. The
[data-model artifact record](data-model.md#restriction-persistence-and-version-aware-api-v9-locally-promoted)
owns the published fingerprints.

With `INFINITYDB_RELEASE_FAQ_PARITY=1`, a two-worker Windows batch using
`tools.run_checks --stage test --assets required` passed **54 tests with zero
skips**. The exact selector union was:

- `tests/test_faq_ruling_references.py::test_tracked_faq_database_matches_current_curated_release_projection`;
- `tests/test_verify_scenario_faq_browser.py::test_release_faq_primary_entry_points_use_tracked_database`;
- `tests/test_verify_scenario_faq_browser.py::test_release_faq_secondary_entry_points_use_tracked_database`;
- `tests/test_verify_scenario_faq_browser.py::test_release_faq_haris_conflict_uses_tracked_database`;
- `tests/test_verify_deployed_object_publication_browser.py`;
- `tests/test_deployed_object_publication.py::test_pinned_publication_is_deterministic_and_source_complete`;
- `tests/test_verify_deployment_assets.py`;
- `tests/test_weapon_profile_publication.py`.

This verifies all **29** current FAQ records and their source/citation facts,
168 topic/context projections, **48** ordinary browser topic associations at
1440/390 px, and the actual Haris source-conflict disclosure on the tracked
pair. Deployed-object checks cover all **17** references and their missing,
unreported and disputed values, delivery navigation and 1440/390/320 px.
The paired publication retains **151** variant groups and **62** reviewed
profile-only Weapon identities with **69** exact modes. Drift, missing-artifact
and mismatched-source cases remain fail-closed.

Ignored evidence is retained in `local/v1s084-rebuild-verification.json`,
the two `local/v1s084-first` / `local/v1s084-second` staging directories and
`local/v1s084-windows-acceptance.txt`. No source acquisition, schema, gameplay,
artifact or asset change was needed. This closes V1S-084 on the pinned pair;
source occupancy/strict/reproducibility gates, final browser matrices,
cumulative Linux/local validation, hosted CI and release/human/operational
acceptance retain their independent owners. No VD/VR work is deferred.

### Known-source disclosure acceptance (V1S-083 / VR-0137)

**Project domains:** Data processing, Web backend, Web frontend, Project infrastructure

At `2736eaba3402e2e99662414f6ad15c17c87efe47`, the focused two-worker
Linux batch passed **255 tests**, with **14 reviewed skips**, using required
assets (**808/808** published and browser-referenced SVGs). Pinned job
`linux-dev:713b014647cd4d2eb876e28cea1d16c8` ran the new disclosure selectors
plus the affected existing source/API, conflict and empty-value regressions.

The new selectors in `tests/test_verify_scenario_faq_browser.py` are
`test_known_source_disclosures_in_release_api` (**10 cases**) and
`test_known_source_disclosures_normal_browser` (**60 cases**). They cover
ten notes across nine canonical references, keyboard catalog-to-detail
navigation, 1440/390/320 px, both themes and Developer Mode off. Assertions
retain citations and interpretation limits, and reject script errors, failed
requests, bad HTTP responses, unresolved markup and horizontal overflow.
The API check also retains Engineer's contact requirement and the distinct
Spanish omission citation, plus both FAQ language sources.

The compatible existing selection included:

- `tests/test_application_rule_references.py` and `tests/test_faq_ruling_references.py`;
- all four `tests/test_verify_deployed_object_publication_browser.py` cases;
- the seven exact-owner/negative-typing selectors for Charontid SR-1,
  Journalist, Religious Troop, Doctor, Engineer, CC Attack and Infiltration
  in `tests/test_audit_source_variant_inputs.py`;
- `test_published_weapon_source_conflicts_preserve_official_profiles` in
  `tests/test_weaponry_catalog_api.py`;
- the pinned-uncertainty and missing-parent-chart cases in
  `tests/test_verify_fireteam_context_browser.py`;
- the existing provenance-label, Domination SWC, Haris FAQ, all-24-setup,
  controlled empty/error and unavailable/archived-source cases in
  `tests/test_verify_scenario_faq_browser.py`, and the missing-publication
  case in `tests/test_verify_weapon_source_cards_browser.py`.

The Linux skips were **11 local PDF cases** and **three opt-in FAQ parity
cases**. A separate two-worker Windows batch on the **same revision** passed
**20 tests with zero skips**, including every skipped case, with
`INFINITYDB_RELEASE_FAQ_PARITY=1`. It also covered the empty Hacking Program
API and `tests/test_hacking_source_followup.py`, including normal browser
source/timing checks at all three widths. These Windows results supplement
Linux coverage; skipped Linux tests are not reported as passed there.

The initial Linux batch at `8cd201dc` had 20 failures, 100 setup errors,
135 passes and 14 skips. Every failure/error rejected an unmatched
variant-usage/deployed-object pair: the first Windows publication fingerprinted
CRLF curated bytes instead of Git's LF blob. The repair changed provenance
only, matched the Linux-built deployed-object bytes exactly, and passed both
dependent publication checks on Linux before the rerun. Reports are retained
under ignored `local/v1s083-linux-focused-initial.txt`,
`local/v1s083-linux-focused-repaired.txt` and
`local/v1s083-windows-source-and-optin.txt` in the development checkout.

The current-citation minimum remained **495/495**, zero metadata gaps.
Curated validation, deterministic v9 staging, preserved Restrictions and Army
values, 490 unchanged unrelated records, dependent-publication checks, focused
Ruff and the documentation stage passed. VD-0111 was designed without test
execution.

Hosted Source then exposed additional record consumers on `2736eaba`:
stale Deployable non-catalog and clause-review evidence, recovery tests
requiring exactly one source note, the Deployable review date and baseline
locator counts. The immediate CI/publication-integrity repair passed **117
tests** in the reviewed Windows worktree based on that SHA. The seven exact
targets were `tests/test_deployed_object_citation_migrations.py`,
`tests/test_deployed_object_non_catalog_queue.py`,
`tests/test_rules_database.py::test_rea038_direct_recovery_contact_does_not_inherit_allied_gate`,
`tests/test_silent_immunity_source_scope.py`,
`tests/test_source_coverage_dispositions.py`,
`tests/test_legacy_staging_schema_guards.py` and
`tests/test_report_reference_baseline.py`. One test deliberately skipped
because its historical migration was already promoted; the other migration
preflight, drift, negative-input and schema guards passed. The full report is
`local/v1s083-consumer-repair-windows.txt`.

The source-review fingerprints were rebound only after confirming that the
original Deployable summary/clauses were unchanged. Their scope explicitly
excludes the new FAQ note and browser approvals remain pending. Non-catalog
evidence separately pins the added note without changing classification.
The baseline now has 832 source sections and 105 pilot source-page identities;
these are inventories, not extra approvals. The rules databases and browser
artifacts were unchanged by this consumer repair, so the pinned Linux/browser
results above remain applicable. Focused Ruff, Pyright with the project
interpreter and docs passed for the repair.
VR-0137 is now closed. This accepts the bounded disclosure gate,
not the cumulative V1S-090 suite, final release pair or replacement-SHA hosted CI.

### Current N5 citation minimum (V1S-082)

The read-only reporter checks whether each maintained **current Core,
Hacking and FAQ** reference record cites **at least one declared,
version-appropriate current source**. It reuses the validated curated
source/record declarations; it does not read source text, resolve cross-source
differences, require multiple citations or approve browser routes.

```powershell
.\.venv\Scripts\python.exe -m tools.report_reference_baseline --audit-current-citation-minimum
```

The standalone check exits nonzero for any missing applicable current
citation, printing the exact collection/record/source IDs. An optional
`--json-output local/...` saves the detail report. The 2026-11-06
read-only smoke returned **495/495** across the three required current
collections, with zero gaps, using declared version/source metadata.
Weapon Property origin projections, optional N4 Reinforcements and
ITS-only collections remain **outside this individual audit**, not
automatically accepted; check them under their owning scope. Source-byte
identity, interpretation and browser acceptance remain independent.
On Windows at `781818bd482c73a650446d94a13b1edc870cac34`, the three
VD-0089 selectors covering source/version selection, live collections
and historical-only gaps passed **9/9 tests**, with no skips. This
completes VR-0125's local execution; it does not establish semantic or
browser acceptance.

### V1S-082 Weapon Property source and browser regression (VR-0126)

The focused Windows run at `6359a67f9c7068b7cb34f7fa6bb2dd1baf9c21df`
passed **43 tests, with no skips**. It used the development `infinity.db`
SHA-256 `8a5840d1ff632e89de26210ee7bcb47e54c6579c15b5c3436e226702e872d7c8`
and `rules.db` SHA-256
`5bc1ef3c70d1d14ad5f043bd1ad6fe159c608e86755d0ec0ac9a8b99f8b052f8`.
The English and Spanish N5.3 PDF SHA-256 values were respectively
`53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f` and
`7f564c864c6f26d6b218a0477c8afeba99da5c56e1a5369bb259f423689bb28f`.

The `pytest -q -ra --infinitydb-skip-summary` selection covered:

- all of `tests/test_weapon_properties.py`;
- `tests/test_weaponry_catalog_api.py`:
  `test_esx04_ap_t2_cc_row_in_bilingual_current_n53_charts`,
  `test_esx04_ap_t2_cc_profile_matches_pinned_weapon_row` and
  `test_reviewed_breaker_and_viral_source_profiles_use_shared_rules`;
- `tests/test_ammunition_publication_parity.py`:
  `test_pinned_combination_source_evidence_is_independent_of_army_map` and
  `test_all_reviewed_ammunition_sources_reach_canonical_and_weapon_publication`;
- `tests/test_verify_weapon_source_cards_browser.py`:
  `test_weapon_property_origins_reach_sources_in_normal_browser` at
  1440/390/320 px and
  `test_unroutable_weapon_property_example_shows_source_section_in_browser`;
- `tests/test_verify_scenario_faq_browser.py::test_esx04_ap_t2_cc_weapon_property_is_visible_in_browser`
  and `tests/test_catalog_rules.py::test_catalog_rules_leave_army_item_raw_without_rules_database`.

This closes VR-0126 for the reviewed Property change; it does not close
V1S-082, the cumulative release gate or hosted CI.

### V1S-082 Equipment Glossary navigation regression (VR-0127)

The focused Windows run at `519e307891995f8763797674a5d6971f19bde32f`
passed **42 tests** and failed the six new Equipment browser cases: the
test expected title case while the existing badge displays uppercase through
CSS. After correcting that assertion, all **6 browser cases passed** at
`8fc03cb24cde2323b50c2566991b4d2da45df0b4`, with no skips. Only the test
assertion and queue note changed between these revisions, so the first run's
other results remain applicable. Both runs used the same development
Army/rules SHA-256 pair recorded under VR-0126.

The `pytest -q -ra --infinitydb-skip-summary` selection covered:

- `tests/test_application_rule_references.py`:
  `test_equipment_glossary_source_cited_routes_cover_current_concepts`,
  `test_validated_public_reference_filters_stale_equipment_links`,
  `test_equipment_glossary_omits_stale_routes_but_keeps_encoded_equipment`,
  `test_weapon_glossary_uses_opt_in_army_links_for_routable_definitions`
  and `test_numeric_army_skill_links_resolve_to_public_slugs`;
- `tests/test_web.py`:
  `test_glossary_projects_canonical_rules_and_embedded_attributes`,
  `test_curated_weapon_families_are_discoverable_in_glossary` and
  `test_cube_profile_characteristic_resolves_to_canonical_equipment`;
- all of `tests/test_weapon_properties.py`;
- `tests/test_verify_weapon_source_cards_browser.py`:
  `test_equipment_glossary_reaches_cited_detail_with_keyboard` for Cube
  and TinBot at 1440/390/320 px,
  `test_weapon_property_origins_reach_sources_in_normal_browser` and
  `test_unroutable_weapon_property_example_shows_source_section_in_browser`;
- `tests/test_verify_scenario_faq_browser.py::test_unpublished_tinbot_source_variant_is_not_a_fake_public_route`.

This closes VR-0127 for the Equipment Glossary change; V1S-082 and the
independent hosted and final-candidate gates remain open.

### V1S-082 Label vocabulary source visibility (VR-0128)

The focused Windows run at `d87681c8b948b23a4b6fc4568ada6f0e1c82e03a`
passed **76 tests with no skips**. The first run at
`819ec5a4b2bb0e8571f32014db9e81ef7b34b495` stopped after two passes
and a failing synthetic fixture: its Label-only collection still contained
scenario components. The corrected fixture and the entire focused set passed
on the later revision. The dedicated MCP Linux worker was unavailable in this
session, so this is Windows evidence, not a Linux result.

The 17 exact pytest selectors are preserved in the VR-0128 queue entry at
the tested revision. The selected source/API, database and shared-renderer tests covered the pinned
Wiki `Labels` member and revision, all 24 published Label details, v8/v9
database compatibility, collection-scoped duplicate and unavailable sources,
broken source references, and existing Label/Glossary behavior. Chrome covered
normal keyboard navigation, source links, vocabulary-scope disclosure and
missing-source feedback at 1440/390/320 px in light and dark themes, plus
the existing Label browser regressions. The run used development `infinity.db`
SHA-256 `8a5840d1ff632e89de26210ee7bcb47e54c6579c15b5c3436e226702e872d7c8`
and `rules.db` SHA-256
`5bc1ef3c70d1d14ad5f043bd1ad6fe159c608e86755d0ec0ac9a8b99f8b052f8`.
The pinned Wiki archive and N5.3 English/Spanish and N5.2 English PDFs were
present and their required source checks passed. This closes VR-0128, not
V1S-082, hosted CI or the frozen-candidate release gates.

### V1S-082 embedded Glossary source visibility (VR-0129)

The complete focused Windows run at `c247b4bad4ca1713dc40434121736c4dada77752`
passed **50 tests with no skips**. An earlier run at
`904893f0be384f33ee69e149e3597850d15b791a` passed 49 and failed one existing
Glossary assertion because it did not include the new citation field. The
corrected exact-shape assertions and the complete selection passed at the
later revision. The dedicated MCP Linux worker was unavailable, so this is
Windows evidence, not a Linux result.

The 23 exact pytest selectors are preserved in the VR-0129 queue entry at
the tested revision. The source/API checks compared ordered authored and
exported citations for all 13 Attributes, 23 Game terms and 12 Unit Profile
help definitions, including contextual API parity, empty sources, supplement
scope and cache isolation. Chromium covered keyboard/source-link visibility
at 1440/390/320 px in light and dark themes, unavailable and archived sources,
and existing Label, Weapon Property and shared rules-card behavior. The run
used development `infinity.db` SHA-256
`8a5840d1ff632e89de26210ee7bcb47e54c6579c15b5c3436e226702e872d7c8`
and `rules.db` SHA-256
`5bc1ef3c70d1d14ad5f043bd1ad6fe159c608e86755d0ec0ac9a8b99f8b052f8`.
This closes VR-0129, not V1S-082, hosted CI or frozen-candidate acceptance.

### V1S-082 reference-only Equipment variants (VR-0130)

The complete focused Windows run at `0be12102b2b2c1459fb40591ac3969771f6eedd0`
passed **33 tests with no skips**, using Chrome 156 and the full set of
**808/808** published, browser-referenced SVGs. The first run at `b074f672`
passed 31 and failed two test-harness assertions: a mock intercepted
constructor lookups, and a filter assertion overlooked intentionally
filter-independent exact usage. Both tests were corrected and the whole
selection passed at the later revision. The dedicated MCP Linux worker was
unavailable; this is Windows evidence, not Linux acceptance.

The 20 exact pytest selectors are preserved in the VR-0130 queue entry at
the tested revision. Backend/API checks covered maintained relation ownership,
ordering, duplicate suppression, partial and absent Army variants, source and
token parity, explicit missing-record errors, and the absence of fabricated
usage or standalone routes. Chromium verified keyboard navigation, both cited
reference-only cards and related links, the Army-availability disclaimer,
actual Firewall usage, and optional-filter behavior at 1440/390/320 px in light
and dark themes. Existing exact-usage and Equipment route regressions also ran.
The development `infinity.db` SHA-256 was
`8a5840d1ff632e89de26210ee7bcb47e54c6579c15b5c3436e226702e872d7c8`
and `rules.db` SHA-256 was
`5bc1ef3c70d1d14ad5f043bd1ad6fe159c608e86755d0ec0ac9a8b99f8b052f8`.
The matched deployed-object publication SHA-256 was
`8424278c5538c136f0bae7aaa98a363a28363d0877d0dc19d05f9546a9caf428`
and the exact-usage publication SHA-256 was
`5393b6ddfd9b3feb43f7977a8d50f2e4a601351ee89f944f0af3c3ad67a4120f`.
This closes VR-0130, not V1S-082, hosted CI or frozen-candidate acceptance.

### V1S-082 Pheroware citation regression (VR-0131)

The complete focused Windows run at `6b63200fcf7c807d3cc87aa40a203876383ad3da`
passed **28 tests with no skips**, using Chromium `156.0.8078.81` and the
pinned English N5.3 PDF. Full deployment verification passed for **808/808**
published and browser-referenced SVGs. Both the deployed-object and
exact-variant publication rebuild checks also passed. The dedicated MCP
Linux worker was unavailable; this is Windows evidence, not Linux acceptance.

The 12 exact pytest selectors are preserved in the VR-0131 queue entry at
the tested revision. They checked the chart heading on p. 182, citation
parity between curated, fresh-export and published rules, Endgame's
source-variant ownership, API behavior and the frozen inventory. Chromium
checked normal catalog keyboard navigation and cited family and Endgame
cards at 1440/390/320 px in light and dark themes. The first nine-selector
run passed 25 tests; three later inventory selectors exposed a stale
pending-source-section count after removal of the invalid locator. The
baseline was corrected from 830 to 829 and the complete selection passed at
the revision above.

The development `infinity.db` SHA-256 was
`8a5840d1ff632e89de26210ee7bcb47e54c6579c15b5c3436e226702e872d7c8`
and `rules.db` SHA-256 was
`0fcf537fcca2b148541d9ad136003d939f0c0ecbe1e79136fca1bb6fd622714b`.
The matched deployed-object publication SHA-256 was
`ac0b7997dc46523294aa23c24e1d8b121dea432af6e86316379b7ff9cf1208b9`
and the exact-variant usage publication SHA-256 was
`d14dbb8dbf337d0a14c00646cf82a42f0af453f01b370c45ddf6bd64d6342c41`.
This closes VR-0131, not V1S-082, hosted CI or frozen-candidate acceptance.

### V1S-082 Weapon Chart early-row regression (VR-0133)

At `04cde57d9a21861fdb075843f63b0daed0ec4fd2`, the focused Windows
run passed **61 tests, zero skips**:

```powershell
.\.venv\Scripts\python.exe -m pytest -q `
  tests\test_audit_weapon_chart_profiles.py `
  tests\test_audit_weapon_traits_prose.py `
  tests\test_audit_weapon_definition_gaps.py `
  tests\test_audit_wiki_weapon_chart_names.py
```

The pinned English N5.3 PDF SHA-256 was
`53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f`,
the Army database SHA-256 was
`8a5840d1ff632e89de26210ee7bcb47e54c6579c15b5c3436e226702e872d7c8`,
and the rules database SHA-256 was
`0fcf537fcca2b148541d9ad136003d939f0c0ecbe1e79136fca1bb6fd622714b`.
The source-pinned audit confirmed 173 detected profile and Trait rows,
including both early page-188 rows and separately matched Uragan modes;
its differences remain disclosed in the
[coverage audit](v1.0-source-coverage-audit.md#v1s-082-weapon-chart-early-row-correction-2026-11-07).
Ruff, targeted Pyright and documentation checks passed. The dedicated MCP
Linux worker was unavailable; Windows evidence does not establish Linux,
hosted CI or final-candidate acceptance.

### V1S-082 Weapon-profile citation regression (VR-0134)

At clean revision `244b43b6695fe2b20bb73e2d138556ae5b030fa2`, the complete
focused Windows batch passed **169 tests, zero skips**. Its exact source,
API, cache, deployment and browser selectors are recorded in the VR-0134
entry at that revision; `tests/test_test_sections.py` was also included.
The first collection found the new test module unregistered; after its
registration, the initial batch exposed eight outdated deployment-smoke
fixtures. Those were corrected, including negative current/rollback image
probe cases, before the complete batch was rerun on the revision above.

The local pinned English N5.3 PDF SHA-256 was
`53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f`;
its extraction matched all **69** published profile/mode/page tuples for
**62** reviewed Weapons. The known Katyusha printed `3` versus Army `+3`
range difference remains disclosed, not interpreted as a gameplay ruling.
The Army and rules database SHA-256 values were respectively
`8a5840d1ff632e89de26210ee7bcb47e54c6579c15b5c3436e226702e872d7c8`
and `0fcf537fcca2b148541d9ad136003d939f0c0ecbe1e79136fca1bb6fd622714b`;
the exact Weapon-profile publication SHA-256 was
`4dd30a8c6f7ccd823a3de378ccde57c0a84dc63f8d6989a761e86165d33d1395`.
Its deterministic rebuild check and deployment-asset check passed; the
latter's initial run skipped SVG verification. A subsequent full deployment
check passed **808/808** published and browser-referenced SVGs. The Windows
determinism-manifest builder reproduced the publication hash above; its
cross-platform comparison remains a hosted check.

The complete affected Weapon API and web modules also passed **527 tests**
without skips, across the normal and full-asset selections.

Chrome `156.0.8078.81` exercised **22** real-browser cases, including all
1440/390/320 px light/dark citation combinations, mode separation,
keyboard source navigation, and explicit unavailable behavior. The
dedicated MCP Linux worker was unavailable, so these results do not claim
Linux, actual Docker-image, hosted CI or final-candidate acceptance.
VR-0134 is closed locally; V1S-082 retains its remaining bounded checks.

### V1S-082 reference-only Equipment source scope (VR-0135)

At clean revision `9189d41805751e7f486475cc1cd08f849332cbbe`, the focused
Windows batch passed **19 tests, zero skips**. Its exact source/API, catalog,
filter and browser selectors are in the VR-0135 entry at that revision; two
existing Weapon-source browser cases were also run to check shared citation
rendering. Chrome `156.0.8078.81` exercised **15** real-browser cases. These
included reference-only family citation sections and scope disclosure, keyboard
and source links, unchanged parent citations, non-availability and filter
behavior, and no overflow or page errors at 1440/390/320 px in light and dark
themes.

The Army and rules database SHA-256 values were respectively
`8a5840d1ff632e89de26210ee7bcb47e54c6579c15b5c3436e226702e872d7c8`
and `0fcf537fcca2b148541d9ad136003d939f0c0ecbe1e79136fca1bb6fd622714b`.
The deployed-object, exact-variant usage and Weapon-profile publications
were respectively
`ac0b7997dc46523294aa23c24e1d8b121dea432af6e86316379b7ff9cf1208b9`,
`d14dbb8dbf337d0a14c00646cf82a42f0af453f01b370c45ddf6bd64d6342c41`
and `4dd30a8c6f7ccd823a3de378ccde57c0a84dc63f8d6989a761e86165d33d1395`.
The dedicated MCP Linux worker was unavailable; this closes VR-0135 locally,
not V1S-082, hosted CI or final-candidate acceptance.

### V1S-082 runtime snapshot identity repair (VR-0136)

At clean revision `1d1ec4a1aea3e0987e9f54e0ff65780b780da421`, the focused
Windows batch passed **28 tests, zero skips**. Its exact selectors are in
the VR-0136 queue entry at that revision. The batch checked the independently
calculated runtime identity for attached, absent and independently located
Weapon-profile publications; changed publication bytes; malformed and stale
attached publications; missing rules; baseline reporting; API cache validators;
and preflight/postflight rejection before release-browser acceptance. Chrome
`156.0.8078.81` also exercised the real local release-candidate browser gate.

The Army and rules database SHA-256 values were respectively
`8a5840d1ff632e89de26210ee7bcb47e54c6579c15b5c3436e226702e872d7c8`
and `0fcf537fcca2b148541d9ad136003d939f0c0ecbe1e79136fca1bb6fd622714b`;
the Weapon-profile publication SHA-256 was
`4dd30a8c6f7ccd823a3de378ccde57c0a84dc63f8d6989a761e86165d33d1395`.
Both originally failing release-identity selectors passed in this batch.
The dedicated MCP Linux worker was unavailable; this closes VR-0136 locally,
not hosted CI or final-candidate acceptance.

### Validation batch planning

When several checks genuinely remain deferred, group compatible work instead
of launching a separate job for every queue entry:

1. Identify the outstanding selectors, missing prerequisites, owning changes
   and intended revisions/asset state. Do not silently accept blockers.
2. Group by compatible *pinned* commit, test inputs, runner/browser options and
   host. Reuse the smallest sufficient cross-layer focused test set.
3. Execute one compatible batch, inspect failures/skips and expand only when a
   separately justified cumulative or release gate requires it.
4. Associate the terminal results with each affected obligation. Close only
   those checks proven green for their intended revision. Record unresolved
   work and its concrete next trigger; no threshold-driven recount or full
   drain is required.

Long logs and timings belong under ignored `local/` when useful. CI and
release acceptance have separate owners. Independent work may continue in
another checkout while an isolated job runs; never mutate the test checkout
or inputs being tested.

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

### Parallel Windows development and Linux validation

**2026-11-06 full-assets glossary/provenance recovery acceptance:**
The independent `linux-dev` worker tested exact revision
`cbf0cde4ee93bec0dfc0b08ab482e9c27ee78857` in job
`linux-dev:7dfbbc8091db4a12a63eeaf54a85b611`, using eight xdist
workers, four persistent Chromium lanes, the split scenario FAQ suite and
**808/808** required published/browser-referenced SVGs.
**5,378 passed, 29 skipped, 0 failed, 2 Python 3.14 fork deprecation
warnings** in 610.24 s pytest time (610.92 s runner).
The prior full run at `fc353b8b` had 10 failed provenance validations;
their corrected `summaryEvidence` review anchors passed independently
on `7712190e` (10 passed, 2 skips), and the complete suite now passes on
the subsequent exact Git revision. Skips include opt-in migration checks,
local-only missing sources and Windows-only checks; they are **not**
independent hosted/frozen-candidate acceptance. See the
[source-coverage audit](v1.0-source-coverage-audit.md#v1s-082-bounded-source-review-remaining-p-173-glossary-terms-2026-11-06)
for the evidence change and publication hashes.

**2026-11-05 full-assets post-checker regression:**
The independent `linux-dev` worker tested
`702536feecc3d2dddfd854ecd8e51e38509509e1` with the complete
published assets (808/808 SVGs), eight xdist workers and four Chromium
lanes: **5,349 passed, 29 skipped, two fork deprecation warnings,
zero failures in 508.78 s**. The companion hosted Source checks
[rerun](https://github.com/frankysan/InfinityDB/actions/runs/42096775320)
eventually passed all four operating-system/Python legs and the
cross-platform deterministic-output comparison after a reproducible
first-attempt Windows Node lifecycle harness timeout. The exact-main-SHA
release gate is still separate.

**2026-11-05 Windows scenario lifecycle harness stability (VR-0109):**
`tests/scenario_lifecycle_harness.cjs` now exits deterministically after
all lifecycle assertions and a synchronous success marker. Its existing
`tests/test_scenario_api.py::test_scenario_browser_aborts_map_and_unit_listener_on_soft_navigation`
selector passed at committed `342826160e49ebef71c82d1e58d09aa850cdbcf7`
on Windows (0.06 s call) and Linux (0.22 s call), without weakening the
assertions. Hosted validation of that later revision is distinct.

**2026-11-05 V1S-096 Phase 4 local integration (VR-0107/0108):**
The docs stage now runs static V1S backlog checking after Markdownlint
and local links. The explicit CI retirement helper checks GitHub event
ranges without silently accepting diverged/insufficient history.
At pinned Linux revision `bf0821afec7f3cb70268589a9c56032e8e494ee4`,
the focused regressions passed: `tests/test_check_v1_backlog.py`
**41/41**, `tests/test_check_v1_backlog_ci.py` **6/6**,
`tests/test_run_checks.py` **110/110**, and
`tests/test_test_sections.py` **15/15** (all zero skips).
An initially unregistered CI test module was added to the test-section
registry; the corrected commit is the acceptance target. Windows Ruff,
Pyright and the full docs stage passed, including **20 V1S declarations
with no static warnings**. This closes local VR-0107/0108; **hosted Source
workflow, cross-platform deterministic outputs, full candidate checks and
the final candidate's full Source matrix acceptance remain separate**
under [CI policy](ci.md) and [release scope](releasing.md).
V1S-096's checker-specific hosted acceptance is recorded under CI policy.

**2026-11-05 V1S-096 checker acceptance (VR-0104/0105/0106):**
Linux worker `linux-dev` pinned to
`0bac336999d102fe94a3bcadbeec83eca1ae7788` ran
`tests/test_check_v1_backlog.py`: **39 passed, zero skipped/failures**
in 0.86 seconds of pytest execution. The separate
`tools.check_v1_backlog` static CLI passed with 20 declarations and
zero warnings. Explicit `--select V1S-096` with its exact documented
`--priority-reason` passed, reporting all **19** earlier open IDs,
including the earliest (V1S-041), and one warning for the intentional
user-priority override; no older task was retired. Windows Ruff, Pyright,
Markdownlint, link checks and `git diff --check` passed before commit.
This closes the **local** Phase 2/3 deferred-execution entries; Phase 4
integration, hosted CI and final release acceptance remain independent.

### Glossary load and Unit relationship visibility (2026-11-07)

**Project domains:** Web backend, Web frontend

The release owner reported slow Glossary loading on development preview
`2df92f9`. The immutable Glossary API now shares one maintained-text
resolver across entries and caches the resolved payload across requests.
It preserves citations, link tokens, search and URL fragment semantics.
This removes repeated reference lookups. After restarting the preview on
`f4a47167fa5b257dd94f10fc738f1f91009ea8ff`, the release owner
reported **noticeably faster initial Glossary loading and subsequent
refreshes** (2026-11-07). This is qualitative manual confirmation, not a
controlled before/after benchmark or hosted performance acceptance.

On Unit details, Reinforcement relationships now require Developer Mode.
The ordinary view retains Army availability and roster navigation.
Targeted source/DOM regressions check the Glossary response, existing
deep links at 1440/390/320 px, and both Developer Mode visibility
states. This is separate from formal version-matched release acceptance.

### Focused UI regression drain VR-0138-0141 (2026-11-07)

**Project domains:** Web frontend, Web backend, Project infrastructure

On Windows Chromium with the tracked frozen Army/rules database pair and
application implementation at
`87a0db1e6f4ab621b97b41436e0bff90207c31c6`, **51/51 unique
focused pytest cases passed, zero skips**. The test-only corrections below
were applied in the working tree before the successful runs and committed
with this evidence. No runtime/database/source-publication change was
required during validation.

- **VR-0138 — 9/9:** `test_skill_faq_card_padding_and_developer_occurrence_geometry`
  **6/6** (`9592a22e9a054e50a150e2932776b375`, 7.10 s) and
  `test_variant_usage_browser_links_exact_contexts_and_unit_profile_groups`
  **3/3** (`ac0ba8c6f486450b9bb2a04eb93d4308`, 8.76 s).
  Three widths, two themes, FAQ inset and spacing, hidden/visible/hidden
  developer-only source occurrences, keyboard disclosures and exact Unit links.
- **VR-0139 — 3/3:** `test_restrictions_chart_normal_chromium_at_three_widths`
  **1/1** (`eeb1c39721d245e98b364b778642c30e`, 12.05 s), and
  `test_published_restrictions_reference_is_exact_source_projection` and
  `test_restrictions_reference_has_standalone_rules_page` **2/2**.
  Exact six-row/fourteen-condition publication, responsive/themes,
  legacy fragments, Back/Forward, contextual Developer Mode links
  and controlled source failure.
- **VR-0140 — 37/37:** Deployed object card/attributes/navigation **1/1**;
  Orders & AROs full-width/table/filter/overflow **4/4**; FAQ single-source
  card geometry **12/12**; Fireteam source-conflict disclosure **2/2**;
  ordinary browser additional/primary FAQ topic associations **6/6**
  and **8/8**; movement/dated FAQ browser **3/3**; selected source
  and date-retaining FAQ API contract **1/1**.
- **VR-0141 — 14/14, with 12 shared VR-0140 cases:** Node rules-card
  renderer and static frontend contract **2/2**; shared FAQ
  single-source/disclosure-separation browser cohort **12/12**.
  Cited cards no longer duplicate the version/scope caption, but
  uncited cards retain applicability. The `Sources:` citation link
  remains, and FAQ cards have clearance before Unit-use disclosures.

The first regression runs failed on **test assumptions**, corrected
before all-green runs: source label trailing whitespace, narrow-screen
Settings overlay intercepting an attempted disclosure click, a
paragraph's internal padding being mistaken for border-box position,
and asynchronous Back navigation tested before DOM detachment.
No confirmed application defect or gameplay/source change resulted.
No broad test suite was run: V1S-090 remains an independent cumulative
release gate. This evidence closes **VD-0115** (test design) and
**VR-0138, VR-0139, VR-0140, VR-0141** (test execution), not the
manual, hosted or version-matched v1.0 acceptance gates.

### V1S-080 frozen-pair automated notice acceptance

**Project domains:** Web frontend, Project infrastructure

On unchanged tracked Army/rules release inputs at
`174bf8b20bb5e27c12f79586a25ffa8509a57ea4`, the focused
`tests/test_verify_page_footer_browser.py` module passed **10/10 with
zero skips** in 11.33 seconds (Windows async job
`72dea735e96e422d97f6e96fedd164ae`). It verified the native floating
notice at 1440/390/320 px, light/dark, fixed position and bounds,
touch and Enter/Space disclosure, session-storage persistence, normal About
navigation and soft-navigation state continuity. No source, database or
runtime edits were necessary; the existing browser contract provides
the selected frozen-pair checks.

**Manual acceptance checklist (accepted below):** a release owner must inspect the
actual release-matched candidate at approximately 320/390 px in both themes
and activate the notice with **real touch** (expanded and collapsed states),
verify its legibility/bounds, check that the icon-only collapsed control
remains reachable, then use keyboard and navigation to reopen it, including
Back/Forward. Check no horizontal overflow or visual occlusion. Record
device/browser, candidate SHA and the outcome. Browser-emulated touch is
valuable regression evidence but is not a human/real-device sign-off.
The earlier V1S-079 NVDA walkthrough is a separate acceptance.

**2026-11-07 development-preview walkthrough:** The release owner reported
**5/5 manual notice checks passed** at
`2df92f95faaebd435b9f9a943929cffb1d8f7c5e`: both themes at
320/390 px, mouse/keyboard collapse and reopen, operable collapsed
control, Back/Forward state continuity, and **actual-device touch**.
The preview started and the checkout SHA was confirmed (2/2 preparation
checks); specific device/browser version was not provided in the result.
These are accepted as observations of that development revision, **not**
final exact-version v1.0 candidate sign-off. The later
[candidate manual acceptance](#final-candidate-manual-notice-and-silhouette-acceptance-2026-11-07)
closes V1S-080.

**2026-11-05 V1S-079 human assistive-technology acceptance:**
The release owner reported **7/7 manual screen-reader checks passed** using the
NVDA/Chrome walkthrough: initial page semantics; expanded notice and its
accessible name; Enter/Space disclosure operation; spoken soft-navigation
announcements and main focus; persistent sidebar navigation; browser Back/Forward
history, focus and scroll restoration; and keyboard navigation and notice state
continuity. This is human spoken-output acceptance, distinct from the earlier
Chromium accessibility regressions and separate final-candidate touch/theme/
responsive acceptance (V1S-080). The tested Git SHA and software versions were
not supplied in the report, so this evidence must not be cited as exact-SHA
frozen-release acceptance; repeat affected manual checks if the navigation or
notice implementation changes.

**2026-11-05 v1.0 publication and accessibility regression (VR-0102/0103):**
The first pinned Linux run at `a1f78bcd` exposed two over-strict
accessibility URL assertions, an incomplete deployment fixture, stale
documentation anchors, and a raw SQLite byte-hash difference between
otherwise matching Army export pairs. The corrected tracked
`data/generated/variant-usage.json` excludes that machine-specific diagnostic
hash but preserves the validated export-pair and runtime release-artifact
digests. Windows passed **97 variant-unit**, **9 real-browser publication**,
**12 deployment**, and **2 accessibility** focused tests, plus publication
regeneration/preflight, documentation, Ruff and Pyright checks. The separate
`linux-dev` worker, pinned to `e957c43e1e09646012e95d53009c340402c3d95f`,
reconfirmed `tools.build_variant_usage --check-publication` (151 groups,
10,923 reviewed rows), then passed the **full-assets pytest suite:
5,306 passed, 29 skipped, 2 fork deprecation warnings, zero failures in
508.16 seconds** (8 xdist workers, four browser lanes, 808/808 SVGs).
This validates only the pinned revision, not subsequent V1S-096 edits.
Manual assistive-technology sign-off and final release candidate gates remain
separate. Hosted wheel and deployment smoke for the same revision passed.
Three Source matrix legs (Windows 3.11, macOS 3.11, Ubuntu 3.14) passed,
but Ubuntu 3.11 was cancelled, leaving cross-platform deterministic-output
comparison skipped. Those hosted gaps remain mandatory under
[CI policy](ci.md) and final release acceptance; they do not extend VR-0103
after its local checks passed.

**2026-11-05 hosted integration repair:** Source run `42049878323` at
`d4ffce43004e53b030af6f02184a7325e1878191` failed all four matrix legs:
the two- and experimental three/four-lane Chromium registries omitted the
variant-usage and contextual State/Fireteam modules, and metrics history
rejected the runtime's fixed `/api/variant-usage` label. The repair registers
both modules in every lane layout and reviews that one bounded route;
query/path-specific labels remain refused. As an immediate CI-correctness
and metrics-privacy gate, Windows ran `tools/run_checks.py --stage test
--stage lint tests/test_browser_test_capacity.py tests/test_metrics_history.py
tools/browser_test_capacity.py tools/metrics_history.py --assets required`:
**48 passed, zero skips/failures**, Ruff passed, and all **808/808** published
and browser-referenced SVGs were available. Tests cover accepted aggregate
variant-usage counters and refusal of query values and path suffixes.
No deferred local test obligation remains for this bounded repair; hosted
Source matrix/deterministic, wheel and deployment acceptance require the
replacement commit's own runs. This focused result does not accept the
final v1.0 candidate or the wider browser suite.

Subsequent Windows Source jobs in runs `42060534503` and `42060899666`
failed only the scenario navigation lifecycle harness: Python timed out in
`subprocess._communicate` while joining a pipe-reader thread. The test now
captures combined output in a temporary file and retains the same 15-second
process deadline, exit-code check, success marker and every JavaScript lifecycle
assertion. Windows `tests/test_scenario_api.py` passed **97/97** with full assets
and Ruff after this transport change. Hosted confirmation remains required;
local success does not prove the hosted timeout's underlying cause. This is an
internal test-infrastructure change and needs no release-note entry.

**Isolated Linux validation may run alongside independent Windows work.**
Focused, browser-subset, partial and full-suite tests can all run against a
pinned, separate `linux-dev` checkout while unrelated Windows development
continues. This is safe only when test inputs and generated artifacts are not
shared or mutated; it does **not** allow moving the worker's HEAD during a
running job. A test result validates only the exact revision and inputs
actually tested, not newer Windows work. Dispatch is never acceptance.
Reserve full suites for explicit cumulative/release gates rather than using
them merely to permit parallel development.

The Windows MCP `local` checkout, the interactive `devbox` checkout, and the
`mcpworker` checkout at `/srv/mcp-worker/workspaces/InfinityDB` are **three
separate working trees**. `worker="linux-dev"` selects only the last one.
Reading/editing through ordinary MCP workspace tools still targets Windows;
remote test/script jobs do not provide a remote file editor. Check the chosen
worker's actual Git HEAD and test inputs before dispatch, preferably with
`expected_commit` for Linux. Record the commit, host, command, asset policy,
source snapshot/database identity where relevant, and final pass/fail/skip
counts. A Linux result validates only the state it tested, never newer
Windows changes or a different Linux checkout.

For truly deferred execution, select the intended revision and relevant
assets, run compatible focused selectors together, inspect failures and close
only satisfied obligations. Run a full suite only for an independently
required cumulative/release gate. Never modify the testing checkout or
shared inputs while any job is running.

**Autonomous commits and due-validation Git handoff are agent-initiated,
not automatic background mirroring.** After required immediate safety
and static checks pass, inspect the working diff, stage only task-related
files, create a coherent conventional Git commit, and fast-forward push
the intended development branch through separate bounded operations.
Record the SHA and any genuinely deferred VD/VR checks. Independent work may
continue if the test checkout and inputs are isolated; do not manufacture
tasks merely to keep the process running. These actions are authorized
by the user's standing InfinityDB development workflow, but they do
not authorize force/reset/rebase, destructive checkout changes,
releases, deployment, or publication of new acquired content.

When a test is assigned to the Linux worker, inspect the committed Windows
revision and dedicated MCP worker checkout; use separate, bounded
Git operations to fetch and fast-forward the worker's matching branch
to the intended revision. Never silently fetch/checkout a different
task's revision, change the interactive `devbox` checkout, force,
reset, rebase or discard local changes. If a Windows commit is not
yet published or a remote differs, verify the configured origin and
ancestry before a safe separately executed push. Do not move a Linux
worker checkout while its pinned jobs are running. Earlier Linux
results never validate subsequent Windows commits.
`expected_commit` must still **refuse** a mismatched revision rather
than silently repair it inside the test launcher. Syncthing transfers
only designated ignored source folders, not Git or curated/generated
databases; these inputs must be activated and pinned before use.
Missing Linux-only dependencies or source material remain coverage
gaps/skips, not passing results.

Prefer the idle Linux worker for longer validation workloads while Windows
continues coding; reserve Windows execution for Windows-specific behavior,
small immediate regressions, or independent confirmation when required.
Do not compare concurrent multi-host run times as controlled performance
benchmarks without accounting for contention and host differences. Hosted CI,
required preflight, and release acceptance remain independent requirements.
After pushing a development revision, record its SHA and available
hosted runs under the separate
[non-blocking agent CI monitoring and repair protocol](ci.md#agent-ci-monitoring-and-repair).
Continue Windows development while CI runs, and revisit outstanding
statuses after meaningful task or Linux full-suite checkpoints.
A full local test run does not itself trigger GitHub Actions;
post-push monitoring is independent of queued local VD/VR checks.
Only a mandatory release/merge acceptance gate requires waiting
for terminal CI results.

**Deferred Linux execution (only when needed):**

1. Identify a real pending check, its revision, selectors and required assets.
   The queue has no count-based execution trigger; a prerequisite becoming
   available or a relevant integration/release gate is sufficient reason.
2. Prepare the dedicated `linux-dev` MCP worker checkout using separate,
   non-destructive fetch/fast-forward operations, then verify exact HEAD and
   relevant dependencies/source inputs. Never silently move the interactive
   `devbox` checkout, reset/rebase, or change a checkout with active jobs.
   A missing required source artifact or unsafe Git handoff is a blocker.
3. Verify schema-specific matched runtime artifacts where the test depends
   on them (including embedded deployed objects in v10 Rules, matched
   variant/Weapon-profile publications, source identities and browser assets).
   Do not mistake a matching Git SHA for evidence that ignored data is present.
4. Dispatch with `start_test_job` or `start_script_job` using
   `worker="linux-dev"`, `expected_commit=<full SHA>` and the smallest
   relevant selectors. Record the job ID and intended coverage. Independent
   Windows work may continue during a **focused or full** run when it cannot
   mutate this worker's checkout or shared inputs. A dispatch is not a pass.
5. Verify terminal status, actual SHA, failures, skips and source/asset coverage.
   Retire satisfied queued work; keep failed, blocked or unrun verification
   open with a concrete next trigger. Hosted CI and release acceptance remain
   independent. Poll existing jobs after reconnecting rather than launching
   duplicates.

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

**2026-11-04 attack, Template, Hacking and Ammunition queue acceptance:**
The pinned `linux-dev` code-profile job
`linux-dev:92c4757c631b4bfe90b0adcf71392a13` at
`1d0d5c196b87983737981b8b8244321b552527a4` passed **5,123 tests,
29 skipped, zero failures**, plus Ruff and Pyright (**zero errors/warnings**).
Command: `tools/run_checks.py --profile code --assets required --test-workers 8 --browser-slot-count 4 --report`.
Pytest took **451.84 s** (452.51 s runner); Ruff took 0.08 s and Pyright
73.13 s. All **808/808** published/browser-referenced SVGs were present.
The ignored deployed-object publication had been rebuilt for the current
Army/rules pair and independently checked at the tested revision before dispatch.
Army SHA-256: `8a5840d1ff632e89de26210ee7bcb47e54c6579c15b5c3436e226702e872d7c8`;
rules SHA-256: `121480b02d2ec81223d167ea1b1c00a556ddd256a42c418b9622059667493349`.

VR-0077, VR-0078, VR-0080, VR-0081 and VR-0082 were individually reconciled
against this cumulative result. All fifteen new attack/Template/Hacking source,
API and real Chromium cases passed, including ordinary navigation and semantic
links at 1440/390/320 px. The three Ammunition publication/opposition/browser
modules ran without skips, covering all eleven base identities and five ordered
combined forms. The static backlog checker also passed its Linux CLI at
`1c780010` (job `linux-dev:670df4e39b4a4002a7faa8f8fe721e21`, 53 declarations,
zero warnings); its complete regression coverage passed in the corrected code profile.

The preceding cumulative `1c780010` job returned 5,099 passed / 24 failed /
29 skipped. The failures exposed missing interaction-review coverage for the new
Template rule, two unclassified object-discovery mentions, browser-lane registration
and stale citation/current-inventory assertions. The focused repair passed
**261/261**, zero skips, on Windows before the corrected cumulative run above.
No source uncertainty, historical D304/S63 classification, or negative guard was waived.
The 29 remaining skips cover opt-in rebuilt-publication gates, unavailable ignored
historical PDFs/local migration evidence, already-promoted staging checks and a
Windows-kernel-only check. None belongs to the required new reference or Ammunition
selectors. Two existing Python 3.14 multithreaded `fork()` warnings remain.
This closes the five local VR obligations; hosted CI, final candidate/source-wide
acceptance and unresolved source authority remain independently owned.

**2026-11-04 cumulative Linux validation of V1S-032 and source-audit repairs:**
The pinned full-assets job `linux-dev:267d0d526f3242e3baef5efaec5b0116`
at `df7191fcbf9821b7b914afbf19e6123b0bc47508` passed **5,056 tests,
29 skipped, zero failures** in **423.66 s pytest / 424.34 s runner**.
All **808/808** published SVGs were present, and the ignored deployed-object
publication was built and checked before dispatch. Eight workers used four
Chromium lanes with one worker per lane; resource waiting totalled 41.71
summed worker-seconds. Two existing Python 3.14 multithreaded `fork()`
warnings remained. Skips include opt-in publication work, absent ignored
historical PDFs and a local migration report; they are not source acceptance.
This verifies the Linux obligations for VR-0052 through VR-0058 at that
revision. The separate hosted Source acceptance for the cleaned-up
historical-evidence export remains open under the
[transferred V1S-093 release gate](releasing.md#development-freeze-and-release-only-handoff); this result does
not cover subsequent movement-reference or clean-export evidence changes.

The later pinned movement/geometry batch at
`a9f564650ff0f42d28fca29f5a1daf87f8642edb`, job
`linux-dev:c4d857d310ab47949ccd94feb06f7f56`, passed **5,074 tests,
29 skipped, zero failures** in **431.85 s pytest / 432.51 s runner**.
All 808 published SVGs and the rebuilt/checked ignored deployed-object
publication were present. Existing source/history/opt-in skips and two
Python 3.14 multithreaded `fork()` warnings remain. This verifies the
Linux obligations through VR-0061 on that revision, including the repaired
interaction totals; it does not cover subsequent Cover changes. Source CI
passed its Linux and Windows jobs but could not acquire a macOS runner,
so macOS and the dependent byte-comparison gate remain unverified.

**2026-11-04 corrected terrain/Cover cumulative Linux verification:**
The first pinned `4e4aa664` full-suite job
`linux-dev:1f7a136e18d44c06a846b7f045426bdf` failed with
**126 failed, 728 errors, 4,235 passed, 29 skipped** because its
Git-ignored deployed-object publication had not been regenerated for
the newly tracked rules database. This is an input preparation failure,
not evidence of 854 independent gameplay regressions. After explicitly
fast-forwarding `linux-dev` to
`c612e54674caa3a33dc20c5df5b201ab0a98dc90` and **building and
checking** the matching ignored deployed-object publication, the
pinned full-assets job `linux-dev:b91f8ef9c6944352a248e1114db987bd`
passed **5,089 tests, 29 skipped, zero failures** in **438.20 s
pytest / 438.89 s runner**, with all **808/808** published SVG assets.
This verifies the remaining Linux obligations for VR-0062 (Cover and
Climb/Jump) and VR-0063 (Difficult Terrain and Saturation), alongside
the previously accepted local execution for VR-0052–0061. No newly
edited, uncommitted V1S-033E browser test was part of this run.
The reviewed, locally complete queue entries are retired under the
strict drain policy; **hosted Source checks, macOS, cross-platform
byte determinism, Installed wheel, Deployment smoke, and final
source/browser release acceptance remain open** under the
[transferred V1S-093 release gate](releasing.md#development-freeze-and-release-only-handoff)
and the mandatory `docs/ci.md`/`docs/releasing.md` checks.

**2026-11-04 V1S-033E browser closeout:** The previously uncommitted
combined browser test was reviewed in VD-0007 (no tests during design),
correcting its legacy search-URL expectation to `?s=v1.s.*`. The first
VR execution revealed Playwright passes a string to URL predicates;
correcting that test matcher yielded the passing runs below.
Windows passed **3/3** combined acceptance cases and **15/15**
complete movement browser tests in **102.05 s**, covering
1440/390/320 px keyboard navigation, citations, search and responsive
layout. On the committed `c4cbffe95388d71c599312f80540c251a6c3d580`,
Linux verified the unchanged matched ignored deployed-object publication
and passed the identical browser module **15/15** in **84.61 s**
(job `linux-dev:9bb988ab8480415fbbda62eddab9f11f`). Changed-test
Ruff and documentation checks also passed. VR-0064 is retired; no
application, database or generated publication was changed. The earlier
`c612e546` **5,089-pass full Linux suite** remains the baseline for
unchanged application code/data; a new full-suite run was not made for
this test-only commit. Hosted CI and final release gates remain open.

**2026-11-04 pinned source-variant queue closeout (VD-0015–0019 / VR-0072–0076):**
The five exact-source regressions were authored and statically reviewed
during a VD-only drain with **no tests executed**; targeted Ruff,
Markdownlint and local Markdown-link checks all passed.
The new tests pin BS Attack source 201 (1,531 occurrences), CC Attack
240 (625), Peripheral 243 (439), Transmutation 246 (295), and the
cross-family fail-closed source/extra collision boundaries, including
profile-owner identities, both Cyberplug modes, raw trailing whitespace,
and unreviewed `+1 Dam` (SRC-032). Windows committed
`b381756d317685c3acc1f0e57366cb1da73f25ef`; Linux `linux-dev`
was explicitly fetched and fast-forwarded from `c4cbffe9` to this
revision, retaining its independent checkout.

The initial pinned Linux source-variant module
`linux-dev:79d5ad2ab9f54e40bafcaeedd0edf897` produced
**100 passed / 5 failed**, all five failures in *existing* paired-publication
review gates because the ignored `data/generated/deployed-objects.json`
still referenced an older Army/rules fingerprint; **all five new
tests passed**. The tracked `tools.build_deployed_object_publication`
was then run on Linux without any tracked-file edits, and a separate
`--check` verified the regenerated artifact matched the current
Army/rules pair. The repeated complete source-variant module
`linux-dev:876cd4527b5d4dfe85239e56a6eb59a8` passed
**105/105, zero skipped, zero failed** at `b381756d` in
**104.76 s pytest / 105.13 s runner**. Each VR selector
0072–0076 was covered by that same verified module run and retired
individually. The initial input-preparation failure does not
indicate five new gameplay defects; neither run is a full-suite gate.
No runtime code, tracked Army/rules database, or source profile
was changed. Source-unknown effects remain unpromoted; complete
cross-Army usage indexing (V1S-062–066), publisher clarifications,
hosted CI and final 1.0 acceptance remain open.

The frozen declaration-owner audit now reads a hash-pinned extraction of
the original 17 retired records from
`config/validation/frozen-declaration-source-v1.json`. It retains the exact
historical commit, source path, full historical-file digest and original
record contents. This lets the indexed preflight export exercise the audit
without `.git`; it does not replace current curated rules or approve historical
identity transitions. A separate optional replay compares every extracted
record with the original Git object when that history is available. Changed
snapshot bytes fail closed, and other explicitly requested historical commits
still require Git evidence.

**2026-11-02 pinned Linux queue execution and prerequisite recovery:**
The async `linux-dev` full-suite job
`linux-dev:9360ac9d03034bff9a7a9384e54cf917` used
`a2769e110d17dc415c715e05f154b941c81204e9` and all 808
published SVG assets, completing in 537.31 s with **4,850 passed,
22 failed, 27 skipped**. Sixteen failed tests required the Git-ignored
`data/generated/deployed-objects.json` that a matching checkout
does not supply. Running the tracked
`tools.build_deployed_object_publication` on `linux-dev` and its
`--check` verified the publication without touching tracked files;
three affected modules then passed 3/3, 4/4 and 3/3 on Linux.
The six remaining failures are stale rule-category/count and PDF
source-count expectations plus two missing report newline arguments;
see the 1.0 TODO fix and open VR-0027/0028. This cumulative run is
**not accepted** despite all targeted source-variant checks passing.

**2026-11-02 corrected Linux cumulative acceptance (VR-0027/28/29):**
After the worker's `origin` was corrected to official GitHub,
the agent safely fetched/fast-forwarded `dev/v1.0.0` from
`a2769e11` to `16f0d4cf5299ae29d0d3b308a4200ca39d6aa4db`,
rebuilt and checked the ignored deployed-object publication, then
dispatched `linux-dev:77cabfbc8f944158aad8c2cc8ca8d683`.
With all **808/808** published SVGs, the 16-worker Linux full suite
finished **4,871 passed, 28 skipped, zero failed** in 552.06 s;
two warnings concern `fork()` in multithreaded web-metrics tests.
The pinned Linux source-variant module independently passed
**60/60**, job `linux-dev:41ca2800f4284c738ad647771c218658`,
with no raw-source skips. This resolves the prior missing-publication
and six stale-test regressions and accepts VR-0027/28/29. The 28
full-suite skips match the known Windows skip-count baseline;
their per-reason cross-host comparison remains separate under
VR-0023. A new Windows-only Religious Troop source regression
written *after* dispatch is not covered by this run (VR-0030).

**2026-11-02 Confessor source anomaly Linux acceptance (VR-0030 retired):**
With Linux and Windows committed at
`d16338ed7676615431d260f766c261f7236428fc`, the
`linux-dev:70e28c0dc41d460b9cde79fff596f684` cumulative
suite passed **4,872 tests, 28 skipped, zero failed** in
555.30 s (808/808 SVGs available; two known multiprocessing
`fork()` warnings). The separate exact Army raw-snapshot
`tests/test_audit_source_variant_inputs.py::test_religious_troop_total_source_83_is_unresolved_and_owner_pinned`
regression passed **1/1**, job
`linux-dev:4cee49adbe684ae797afeb8bf5c7daa6`.
This retires VR-0030 without changing the upstream Confessor
Religious Troop/Terrain qualifier. The later Windows Camouflage
and Infiltration source regressions were **not** in the tested
`d16338ed` snapshot and remain deferred under VR-0031/32.
Per-reason skip parity and full-load Chromium performance acceptance
remain independently queued under VR-0023/24.

**2026-11-02 Camouflage/Infiltration cumulative Linux acceptance
(VR-0031/32):** The agent pushed the already committed
`eec7f940d435e74bd918367298abb8e2356b8302` Windows
revision, safely fetched/fast-forwarded the dedicated
`linux-dev` checkout and rebuilt/verified the ignored
deployed-object publication. Pinned full-suite job
`linux-dev:086caa465f334f6a9cc3a30ba85ec578`
passed **4,874 tests, 28 skipped, zero failed** in
542.38 s pytest time (543.00 s runner duration); all **808/808**
SVG assets present. Warnings were limited to the two known
multithreaded `fork()` deprecations. The runner measured
**5,714.64 summed worker-seconds** of setup resource waiting
across 31 events, with Chromium slot waits as long as
472.30 s, confirming the separate contention benchmark
remains open under VR-0023/24. The 28 skips match the
historical Windows count, but skip-reason parity still needs
independent reconciliation. The pinned source-variant module independently passed
**63/63**, `linux-dev:03429aa6ae764130967fc05c5a9261cc`,
using the raw Army archive with no skips; VR-0031/32
are therefore retired. Engineer and Doctor source
regressions committed after `eec7f940` are not
covered by this run.

**2026-11-02 Engineer/Doctor pinned Linux acceptance
(VR-0033/34 retired):** The agent
safely published the committed Windows revision
`60511fec335ac370f6664bb0b22edd0ee6681764`,
fast-forwarded the dedicated `linux-dev` checkout, and rebuilt
and verified the ignored deployed-object publication before
starting `linux-dev:5ab409f05073456bb1e550134cd23030`.
With **808/808** published SVGs, the full suite passed
**4,876 tests, 28 skipped, 0 failed** in **556.60 s** pytest
time. The two known multiprocessing `fork()` warnings remain.
Measured Chromium resource waits totaled **5,730.67 summed
worker-seconds** in 34 setup events; the browser-concurrency
investigations remain open (VR-0023/24). Independent `tests/test_audit_source_variant_inputs.py`
validation passed **65/65** with the pinned raw Army archive
and zero skips, job
`linux-dev:c452dd4d53bb4e7dbfa69a0d9096202f`.
This retires VR-0033/34 without implying a ruling on
Doctor/Engineer `ReRoll -3` (SRC-029).
The subsequent Windows Lieutenant and Commlink regression
commit `5776779da247c12b186d028cc9328450963be1c7`
is not covered by these earlier tests.

**2026-11-02 Lieutenant/Commlink pinned Linux source verification
(VR-0035/36 source gate):** After ordinary, validated Windows
commits `5776779da247c12b186d028cc9328450963be1c7`
and `f4e58294e52f6da0be19008135de16df374b4518`
were pushed, the dedicated `linux-dev` worker fetched and
fast-forwarded the same branch to `f4e58294`. Pinned source job
`linux-dev:a11eff7e5372408caf51b73ebfaba5c4`
passed **67/67** with the raw Army archive; there were no
source-data skips. The prior `60511fec` cumulative Linux suite
did not contain the Lieutenant and Commlink regressions.
The later `fd38485f` full Linux suite passed, retiring
VR-0035/36; typed Commlink publication is tracked
separately under VR-0037.

**2026-11-02 Commlink typed source-only implementation (VR-0037):**
The scoped N4-origin annex now has a closed, exact typed mapping
for the **34** `298/TEXT:+1` and **8** `299/TEXT:+2`
Commlink occurrences. Fresh in-memory/exported rules include
`max-trooper-count-increase`, restricted to the optional
Reinforcements Extra's Army List maximum, not a core N5
Attribute bonus or legality calculation. Six fail-closed
mutations rejected incorrect IDs, effect scope, count type,
omission, reordering and invented `+3`. Windows
`tests/test_curated.py` **670/670**, source-variant module **68/68**
(after updating 12 aggregate status assertions to compare
against the actual release revision), rules-database module
**166/166**, temporary rules/data builds, Ruff and Pyright
passed.
A separate v9 migration-delta regression passed **7/7**
on Windows (and the full release-storage candidate module
passed **530/530**), verifying a single Commlink variant
append and refusing changes to unrelated records, schema, missing
records, unchanged variants and mismatched baselines.
The active tracked v9 rules/publication pair is
**not yet updated**; its guarded migration and matched
deployed-object publication must be accepted independently
before marking the runtime mapping published.

The committed source revision `5fcd01b102d5f7e580994c4891c79489bd5a088e`
was validated on Linux via
`linux-dev:ac67b012dd014a8f9bf2d4f76f66f3fb`:
**4,884 passed, 28 skipped, one failed** in 542.46 s pytest.
The sole failure was the old exact `Commlink` variant-dict
assertion in
`tests/test_reinforcements_optional_reference.py`,
which did not allow the newly reviewed occurrence parameters.
A corrected exact N4-origin assertion was committed as
`fd38485fc5867ba6abe7c945cbf5786221cc15cc`;
focused tests passed **2/2** on Windows and Linux
(`linux-dev:a1993f8ea16347e6ac794f81694269ff`).
After rebuilding and verifying 808/808 ignored SVG-dependent
publication assets, replacement full Linux job
`linux-dev:538f30517bf5477c8dc77881c7a985d7` at
`fd38485fc5867ba6abe7c945cbf5786221cc15cc` passed
**4,892 tests, 28 skipped, zero failed** in 560.68 s pytest
(561.20 s runner), with two known multithreaded `fork()`
deprecation warnings. This accepts source-only VR-0035/36,
without publishing the new typed Commlink effects.
Chromium resource wait was 6221.58 summed worker-seconds
across 25 setup events, including 491.75 s on the longest
single Chromium acquisition: evidence for outstanding
VR-0023/24, not an additional suite failure.
The separate guarded release-pair promotion remains VR-0037.
A subsequent non-destructive Windows pair preflight
`tests/test_reinforcements_optional_reference.py` passed
**2/2**: temporary v9 rules export differs only in
`skill:commlink` metadata (or not at all once promoted),
while a freshly built proposed deployed-object publication
preserves all **17** records, their Unit uses and all source
provenance except the new rules-db SHA-256. The normal
`load_deployed_object_publication` validator accepted
the staged temporary pair. Existing deployed-object
publication tests passed **12/12**; migration-guard cases
passed **7/7**. Pyright now passes after explicitly typing
the migration test's dictionary keys as
`dict[tuple[str, str], str]`. Neither tracked release artifact
was modified. This acceptance is deliberately compatible
with a future already-promoted release; actual promotion,
rollback verification and normal UI acceptance remain open.
A subsequent **read-only v9 release-export preflight** in
`test_annex_read_model_is_discoverable_and_separate_from_core_matrix`
compared every staged `records` row against the active tracked
`rules.db`: **only `skill:commlink` differs**. The existing
`_check_variant_semantics_delta` guard accepted the exact
canonically serialized variant append across the full database;
the Annex module passed **2/2** on Windows. This is not a
release-pair promotion; matched deployed-object publication
and normal-mode acceptance are still required.

**2026-11-03 Commlink v9 staging and subsequent promotion (VR-0037):**
The historical `tools.stage_commlink_v9_candidate` accepted a new
ignored `local/` destination and staged a matching v9 Rules and loose
deployed-object JSON pair without modifying the release. The one-use
script was retired in P2.5; the original command remains in Git
history, **not as a runnable development instruction**.
The procedure refused destinations outside the
ignored `local/` directory, preexisting destinations, dirty
tracked release artifacts, mismatched source/publication pairs,
unreviewed source records, unexpected database changes or
unrelated publication drift. It exports a fresh matched v9
`rules.db` and `deployed-objects.json` plus `manifest.json`,
verifies the exact `skill:commlink` variant append and retained
Restrictions, checks 17 identical deployed-object records,
and asserts the active pair remains byte-unchanged.
A real candidate was staged at
`local/commlink-v9-candidate-20261103/`.
Manifest baseline hashes: rules
`bc5df34bf752339c41156d5fe84ca35cc74feb0c890cb5407dd97f6d09f3a35d`,
publication
`88e5b42537f600a016aef62a48d47aa17ab38fdb871f75af9c604485ab34973f`.
Candidate hashes: rules
`5a12887c255e8ccbd5dd2f880b4471e2c8dbd46b9fc4c2dc9469f2e740722f9d`,
publication
`bd7f2b49c6983012f34d195a1b4e77ad32e3f4ffcc9bca39a596cd7bb2851262`.
The originally staged candidate was **not** a release or deployment;
its input hashes were subsequently rechecked before authorized promotion.
The pre-promotion Annex module passed **3/3**, with Ruff and Pyright green.

**Guarded Commlink pair promotion, 2026-11-03:** The separate
`--promote-staged` mode requires the original manifest and both candidate
binaries to match their SHA-256 pins, matches the untouched HEAD baseline,
rebuilds the same candidate from current curated inputs, and requires the
reconstructed bytes to match exactly before writing. It reuses the
paired rollback helper with atomic per-file writes and verifies the
published v9 database, exact +1/+2 effects, matched 17-object
publication and application loader after replacement. An earlier
Windows regression exposed an SQLite handle held by the staging
exporter; explicit connection closure fixed that before promotion.
The disposable promotion, tamper-rejection and injected-failure
rollback suite passed **6/6**; the separate release-storage module
passed **530/530**. Under explicit authorization, that now-retired
command promoted tracked `data/generated/rules.db` and refreshed its matched,
Git-ignored `data/generated/deployed-objects.json`. Verified recovery
copies are retained under ignored `local/commlink-v9-recovery-tscycrly/`.
Before SHA-256:
`rules.db` `bc5df34bf752339c41156d5fe84ca35cc74feb0c890cb5407dd97f6d09f3a35d`,
`deployed-objects.json` `88e5b42537f600a016aef62a48d47aa17ab38fdb871f75af9c604485ab34973f`.
Promoted SHA-256:
`rules.db` `5a12887c255e8ccbd5dd2f880b4471e2c8dbd46b9fc4c2dc9469f2e740722f9d`,
`deployed-objects.json` `bd7f2b49c6983012f34d195a1b4e77ad32e3f4ffcc9bca39a596cd7bb2851262`.
The before/after artifact hashes and both recovery copies matched;
publication
`--check`, Rules validation, post-promotion Annex **6/6**, deployed
objects **12/12** and normal-mode Windows Chromium **3/3** passed.
The optional N4-origin scope and uncalculated roster legality are
unchanged. The source-variant audit's three obsolete pre-promotion assertions
were reconciled against the reviewed published parameter; its
**68/68** tests passed. A disposable synthetic prior-v9 fixture
keeps the actual staged-pair, tamper and injected-rollback tests
exercised after promotion (Annex **6/6**). Cumulative Linux/full-suite
and manual Army-context acceptance remain separate.

**2026-11-03 optional annex normal-mode Chromium navigation (VR-0038):**
The separate `tests/test_verify_reinforcements_optional_browser.py`
now covers the published Rule → Commlink → Request Reinforcements
navigation in normal mode at 1440/390/320 px. Windows real Chromium
passed **3/3**, including the N4-origin notices, source citations,
keyboard link activation, and non-leakage of both optional Skills
into the 57-row N5 Orders/AROs matrix. At `f21ad5ac`, the
separately synchronized Linux worker passed the same **3/3 real
Chromium cases** in 7.59 s (job
`linux-dev:77099baf333c4e5a98372b9f5b31e0ef`), with no skip.
Test-section registration passed **15/15** and targeted Ruff passed
on Windows. The active v9 publication pair was not modified.
Cumulative validation, remaining Army context and manual browser
acceptance are separate;
this does not verify N5-native annex authority or promote typed (+X).

**2026-11-03 Linux promoted-pair cumulative validation (VR-0037/38):**
After explicit worker Git fetch/fast-forward to `561e1269`, the Linux
worker built and verified its Git-ignored matched deployed-object
publication. The 808/808 SVG assets were available. Pinned full-suite
job `linux-dev:a4541b2a28fd4f1e8ea5222c455b60c0` finished
**4,938 passed / 28 skipped / 1 failed** in 575.79 seconds. The
only failure was `tests/test_browser_test_capacity.py::`\
`test_two_browser_lanes_cover_all_real_chromium_modules`: the new
`test_verify_reinforcements_optional_browser` module was present in
the test-section registry but missing from both default/experimental
Chromium lane registries. Both code and source assertions otherwise
passed, but **the cumulative suite was not accepted**. The module was
added to each lane mapping; its direct Windows capacity regression
passed **24/24** and the expanded optional Annex Chromium module
passed **3/3**. The two existing Linux multiprocessing-fork warnings were unchanged.

**Accepted corrected cumulative Linux validation, 2026-11-03:** At
`8e2b2de727afa9695dcd3bc48b7f8b62cf319426` (committed and pushed
on `dev/v1.0.0`), worker `linux-dev` verified the matched
deployed-object publication and 808/808 published SVGs, then ran
`pytest -n auto --dist worksteal --infinitydb-skip-summary` across the
full asset-enabled suite. Job
`linux-dev:013c20ae82b247c29cc9793dab15d12e` finished
**4,939 passed / 28 skipped / 0 failed**, in **574.46 s**
(575.10 s runner duration). The 28 skips were grouped into 12
known reasons: 16 explicit rebuild-only opt-ins and 12 promoted,
local-migration/source-evidence or local-PDF cases. The two existing
Python 3.14 `fork()` deprecation warnings remain. Chromium resource
waiting totaled **6,008.59 worker-seconds** across 34 setup events;
this is summed wait time, not additional wall-clock time.
These results retire **VR-0037, VR-0038 and VR-0039**. They verify the
promoted scoped Commlink (+X) pair, optional Annex browser behavior and
parent/pool links; they do **not** establish N5-native annex authority,
Army List legality, manual assistive-technology acceptance or controlled
2-/4-slot performance equivalence (VR-0023/24).

**2026-11-03 optional annex Section/parent navigation (VR-0039):**
The normal-mode optional Rule detail now derives a current, playable
Reinforcement Section list from `/api/armies`, linking each Section to its
Army overview card and its own Unit Explorer pool, with explicit links to
all available parent Armies. Source availability is not combined Army List
legality or N5-native procedural adoption. The existing browser regression
checks the exact API-derived Section/parent links and Unit Explorer
share-state paths at **1440/390/320 px**, plus live desktop navigation
through both the overview card and the Section-filtered Unit Explorer.
The explicit `reinforcement=1` share-state parameter preserves Section
visibility when optional-unit preferences are disabled. Windows real
Chromium **3/3**, Army overview Chromium **4/4**, and the source-derived
Army-context API test **1/1** passed; targeted Ruff, full Pyright,
docs and data/rules checks passed. After committing the lane correction
at `8e2b2de7`, Linux focused Chromium **3/3**, capacity **24/24**
and the full suite passed, retiring VR-0039.

**2026-11-03 Reinforcements source-profile/variant navigation (VR-0040):**
A pinned Army-database cohort selects one logical Unit with profiles in
an ordinary parent Army and its explicit Reinforcement Section.
`tests/test_verify_reinforcements_optional_browser.py` checks exact
`profile_payload_occurrences` names against the API for both contexts,
the `reinforcement=0` filter and explicitly requested Section override,
and General-profile identity consistency. At 1440/390 px, real Chromium
opens only the chosen Army's profile disclosure and retains its source
profile names. A separate pinned query follows actual Army Skill 260
loadout extras `298/TEXT:+1` and `299/TEXT:+2`: real Chromium at
1440/390 px shows `Commlink (+1)` and `Commlink (+2)` in their
source Army loadouts and links to the scoped N4-origin Skill card.
Windows essential regressions passed **1/1 source/API, 2/2 context
Chromium, 2/2 Commlink Chromium**; targeted Ruff passed. This checks a
bounded real-source cohort rather than all profiles, event roster
legality or N5-native rule authority. Linux at `b8b02491` passed
the complete normal Chromium module **8/8**, including these cases,
while the prior cumulative suite at `8e2b2de7` predates them.
Cumulative cross-platform acceptance passed at `06ae1c48`; VR-0040 retired.

**2026-11-03 complete Reinforcement Section source parity (VR-0041):**
`tests/test_reinforcements_optional_reference.py::test_every_published_reinforcement_profile_and_loadout_keeps_source_army`
independently assembles all source profile and loadout rows from the
tracked Army database using `logical_unit_sources`,
`application_army_sources`, the exact source profile/loadout
occurrences and `role = reinforcement`. For every affected logical
Unit, it compares the runtime repository's Section-scoped
`(group_id, name)` profiles and
`(group_id, option_id, name, points, swc)` loadouts with those
independently joined source rows, including the absence of extra
cross-Section entries. Windows focused regression **1/1 passed**
(1.77 s pytest), targeted Ruff passed. This establishes **published
source-identity parity**, not publisher rules adoption, every possible
Army-list legality constraint or manual browser/AT acceptance.
Linux pinned `b8b0249127e7782331c6b23e1be375d2a9d8ab51`
focused **1/1** passed (job
`linux-dev:66cfc3c91f6b402da58c48e6f90145dc`);
the matching Annex normal Chromium module passed **8/8**
(job `linux-dev:7b225640da724276bc271f2ccea40979`).
The matched ignored deployed-object publication was verified before
these runs. Cumulative acceptance passed at `06ae1c48`; VR-0041 retired.

**2026-11-03 source-wide Commlink occurrence/loadout parity (VR-0042):**
`tests/test_reinforcements_optional_reference.py::test_commlink_source_extras_remain_on_their_exact_army_loadouts`
joins the published Army's Skill 260 loadout occurrences, exact extra
occurrence positions, logical Unit provenance and source Army mapping.
It independently compares each (logical Unit, Army, group, option)
signature set to the runtime Unit API's underlying read-model,
requiring the three observed states: no extra, `298/+1`, and
`299/+2`. No source variant may disappear or leak to an
unrelated Army loadout after Unit canonicalization. Windows targeted
pytest **1/1 passed** and Ruff passed. This checks all materialized
source identities and variant rendering inputs; it does **not** certify
an N5-native procedural rewrite or calculate the actual roster limit.
Linux targeted **1/1** and cumulative validation passed at `06ae1c48`;
VR-0042 retired.

**2026-11-03 accepted Reinforcements source/Army context (VR-0040–0042):**
The full published Reinforcement profile/loadout source parity, exact
Commlink unqualified/+1/+2 loadout signatures and normal-mode
Army/Section browser navigation passed their focused tests on Windows
and Linux. Linux Chromium acceptance was **8/8** at `b8b02491`
(job `linux-dev:7b225640da724276bc271f2ccea40979`);
source/Section and Commlink occurrence selectors each passed **1/1**
on Linux. Windows complete Annex source and browser modules both
passed **8/8**, with Ruff, Pyright (zero errors), data/rules and
documentation checks green.

A full Linux suite pinned to `5d6a30d8` passed **4,946 / 28 skips /
0 failures** (job `linux-dev:09fd3c43e0ee4ae484e2be6032210098`).
After the Pyright-only tuple typing correction and SRC-030 documentation,
the full suite was rerun at exact commit
`06ae1c4856d3213a3f03c88f7f6f219b23366ee7`:
**4,946 passed, 28 skipped, 0 failures**, 808/808 published SVGs,
597.98 s pytest / 598.61 s runner (job
`linux-dev:b3a1901e213c4aaaa4f5c1f0706d4831`). The 28 skips
belong to 12 known categories; the two Python 3.14 `fork()`
deprecation warnings remain. Chromium resource waiting summed
6,367.99 worker-seconds across 32 setup events, not additional wall
time. A subsequent commit `646dee42` changed documentation and
agent instructions only (verified GitHub compare), without modifying
tested application code, data or tests.

**VR-0040/41/42 retired.** This is reference/source parity acceptance,
not roster-legality implementation, confirmation of N5 adoption of
N4-origin procedures, controlled Chromium-capacity benchmarking
(VR-0023/24), or final hosted/manual release acceptance.

**2026-11-03 legacy staging freshness gate (VR-0043 retired):**
The Windows implementation added a read-only
`tools.verify_staged_release_pair` check for exact baseline and candidate
hashes, curated-source freshness, v8/v9 schema preservation, reviewed
Restrictions and deployed-object pair integrity; it does not promote
ignored staged artifacts. Windows focused tests passed **5/5** new
verifier, **3/3** legacy exporters, and **3/3** promoted terrain; Ruff,
Pyright, documentation links/lint, rules stage and whitespace checks
passed. The change was committed and pushed as
`ad3314dc3da02ec3a9087b5361dcbdc1b374cabf`.

After explicit Linux fetch and fast-forward to that exact SHA, the
Git-ignored deployed-object publication was rebuilt and separately
verified with `tools.build_deployed_object_publication --check`.
Pinned `linux-dev` full-suite job
`linux-dev:d6afcceb7045465e844ff91bf65c81b5` finished with
**4,952 passed, 29 skipped, 0 failed** in 578.23 s pytest /
578.92 s runner. All **808/808** published SVG assets were present;
29 skips were grouped into 13 reasons, including optional rebuilt
release inputs, unavailable local PDF/report fixtures, Windows-only
cases and already-promoted staging. Two existing Python 3.14
multithreaded `fork()` deprecation warnings remain. The run measured
6,240.96 summed worker-seconds of Chromium/resource waiting across
30 setup events, already included in setup timings rather than extra
wall time. This retires VR-0043; VR-0023/24 remain open for controlled
capacity and skip-reason comparisons. Hosted CI and release sign-off
remain separate gates.

**2026-11-03 Lieutenant source-119 resource review (VR-0044 retired):**
The pinned N5.3 English p. 99 describes two different Lieutenant
loadout qualifiers: `245/TEXT:+1 Command Token` (30 option rows,
+1 Command Token for the match) and `246/TEXT:+1 Order` (53 option
rows, a second Special Lieutenant Order per Turn). Of 438 direct
source-119 rows, 355 carry neither qualifier. Neither typed effect
is a generic Attribute modifier or a Regular Order Pool addition.
`tools.review_lieutenant_variant` verified all exact source signatures,
option ownership, the PDF fingerprint, a deterministic v9 candidate
with unchanged Restrictions and unrelated deployed-object rows, then
promoted the matched pair using the audited rollback-capable release
path. The ignored paired deployed-object publication passed `--check`.
The generated audit now reports 21 reviewed-extra and 13 unresolved
Skill source IDs; no Unit usage index or roster validator is published.

Immediate Windows checks: `tests/test_audit_source_variant_inputs.py`
**74/74 passed** on the final promoted pair, including the published
pair verifier and four malformed/changed-qualifier rejection cases.
The candidate regression passed both before and after promotion.
Ruff, Pyright (0 errors), data/build, rules, documentation lint/links
and Git diff whitespace checks passed. The initial pinned Linux full
suite at `14590055` found two regression-test defects: a Windows/Linux
SQLite byte-layout assumption and an exact reviewed-extra set that
omitted Lieutenant. Both were corrected by `bda102e6`. The two exact
Linux failure selectors then passed **1/1** each; its full suite passed
**4,959 / 29 expected skips / 0 failures** in **572.58 s**.
No unrelated gameplay semantics or curated source facts changed.

**2026-11-03 final paired source/tooling validation
(VR-0044/45/46 retired):** The Linux worker was explicitly fast-forwarded
to `60bd855932f663bf6bec0de5dc29f3439006e6ed`; the ignored
`deployed-objects.json` matched the tracked release pair on
`tools.build_deployed_object_publication --check`. The newly added
read-only raw-inspection module passed **11/11** pinned Linux tests
(including exact source rows, zero-row table reporting, and refusal of
unpaired archives); directory and ZIP database-size build fixtures passed
**2/2**. The pinned cumulative async job
`linux-dev:0f5828bdc96a4172bb46c5fcce1e991e` passed **4,970 tests,
29 expected skips, 0 failures** in **594.79 s pytest / 595.42 s
runner**, with **808/808** published SVGs. The 29 skips were grouped
into 13 expected reasons. Two existing Python 3.14 multithreaded
`fork()` deprecation warnings remain; 6,589.71 worker-seconds of
Chromium/resource waiting across 33 setup events are *included* in
pytest setup timings, not additional wall time. All three GitHub
workflows (Source Checks, Installed Wheel Smoke, Deployment Smoke)
passed at this same commit. This retires VR-0044, VR-0045 and VR-0046;
VR-0023/24 controlled performance comparisons and final release
sign-off remain independent.

**2026-11-03 Terrain source-58 type review (VR-0047 retired):**
N5.3 English p. 116 and the pinned September 29 Army archive support
seven exact type qualifiers: `Total` (extra 33, 918 direct rows),
`Zero-G` (34, 164), `Aquatic` (35, 65), `Desert` (36, 29),
`Jungle` (37, 30), `Mountain` (38, 19), and `Aquatic/Jungle`
(50, 10). One of 1,236 direct Terrain occurrences is unqualified.
The reviewed typed effect scopes the **existing** Terrain Skill
to a single fixed Type, a player-selected one of two Types when
placed on the table, or all five Types with `Total`—not multiple
stacking MOV bonuses or dynamic terrain resolution. The separate
`Religious Troop (Total)` occurrence remains unreviewed under SRC-028.

The read-only `tools.review_terrain_variant` guard verified source
signatures and owners, pinned N5.3 PDF bytes, the exact
schema-v9 Terrain-only candidate delta, and unrelated
deployed-object invariance. The rollback-capable
`--promote` path refreshed the tracked rules DB and matched ignored
publication, whose independent `--check` passed. Windows direct
and malformed-variant tests passed, then the source-variant module
passed **82/82** on the promoted pair. Both `rules` and `data`
stages passed; Ruff and whitespace checks passed. The inventory is
now **22 reviewed-extra / 12 unresolved** Skill source IDs, without
a published cross-Army Unit-use index. On the pinned Linux checkout
`333a091cb4336cb5cce0d9b0c2eae9b27c7abaa0`, the source-variant
module passed **82/82** (job
`linux-dev:e4b0c232a25c499b8ff18941da38edad`); the cumulative suite
passed **4,977/29 skipped/0 failed** in **593.76 s pytest / 594.37 s
runner** (job `linux-dev:bbfa0a7fd0f64ab79e67e19041c371f3`),
with **808/808** published SVGs. All three hosted workflows passed.
The Linux suite recorded **6,301.22 summed worker-seconds** of Chromium
setup resource waiting over 31 events, included in pytest setup, and
two existing Python 3.14 multithreaded `fork()` warnings. This retires
VR-0047; benchmarking VR-0023/24 and independent final release sign-off
remain open.

**2026-11-03 Camouflage source-29 FAQ one-use review (VR-0048 retired):**
The pinned Army archive reports 597 direct Camouflage occurrences,
including **223** exact `43/TEXT:1 Use` source annotations and **374**
without that extra. The published N5 FAQ v0.0 English and v0.1
English/Spanish sources (printed p. 2) agree: deploying as a Model
preserves the use; attempting Marker deployment with a failed
Infiltration Roll consumes it. One reviewed `camouflaged-state-one-use`
effect now encodes that boundary, without changing the base Skill or
the published FAQ answer. Three pinned FAQ PDF hashes verified on Windows.
The guarded read-only candidate checked the exact v9 single-record
delta, all 223 raw owners and unchanged unrelated deployed-object data.
The variant was promoted using the rollback-capable matched-v9 path;
`tools.review_camouflage_variant` verified the published pair at the time
(the one-use reviewer has since been retired under P2.5).
Five negative mutation cases reject widened use counts, changed
consumption conditions and invented extras. Windows source-variant
module **89/89**, curated collection module **670/670**, and rules
DB module **166/166** passed. Build/data, rules, Ruff, Pyright, docs
lint/links and whitespace checks passed. The inventory is now **23
reviewed-extra / 11 unresolved** Skill source IDs. At pinned
`5ac294165a8be49a13125ba9324281b17b406264`, the Linux source
module passed **89/89** and the cumulative suite passed **4,984 tests,
29 expected skips, 0 failures** in **596.40 s pytest / 597.07 s
runner** (`linux-dev:ec597818137143ffa8cb26c741a8fd87`). All
**808/808** published SVGs were available. Two pre-existing Python
3.14 multithreaded `fork()` warnings and 6,597.21 summed Chromium
worker-seconds of resource waiting (already included in setup time)
were recorded. GitHub Installed Wheel Smoke and Deployment Smoke
passed. Source Checks initially reported failure because macOS was
cancelled before any step; the unsuccessful jobs were retried on
the same SHA, after which all matrix jobs and the cross-platform
deterministic-output check passed. VR-0048 is retired. This remains
metadata, not a game-state usage-tracking engine.

**2026-11-03 Combat Jump source-35 landing/Explosion candidate (VR-0050):**
The pinned N5.3 English rules p. 89 and September Army archive
support six exact `TEXT` qualifier signatures across 211 direct
Combat Jump occurrences: `+3` (extra 1, 3 owners), `PH=11`
(27, 102), `PH=13` (52, 2), `PH=14` (244, 4), `PH=12`
(250, 5) and `Explosion` (255, 5). All 121 qualified occurrences
retain exact Army source/owner positions; the other 90 have no
qualifier. These are three different effect shapes: a modifier
to the landing PH Roll, a fixed PH value **for that landing Roll
only**, and a single-use, self-exempt PS 8 Normal circular Direct
Template Attack **after final placement**. None changes the
printed Unit PH or implements an in-game combat evaluator.
The reviewed typed effect metadata is closed to exactly the six
source signatures; six negative mutation tests reject invented
modifiers, PH values, Explosion-use/attack changes and extras.

The historical read-only `tools.review_combat_jump_variant` verified the
pinned source PDF, 211 direct occurrences, all qualified raw
owners, exact single-record schema-v9 delta, and matched
deployed-object publication invariance. The rollback-capable
`--promote` path refreshed the tracked rules DB and ignored
paired publication. Read-only recheck reports
`combat-jump-v9-verified-published` with identical active/candidate
rules SHA-256. Windows source-variant **97/97**, curated **670/670**,
rules-database **166/166**, data/build, Ruff, Pyright, docs and
rules stages passed. The rules-database inventory assertion was
updated for the new reviewed family. At pinned commit
`c1d8adc6cd547063ee5b8a85e831aa73cd4d4195`, Linux's
source-variant module passed **97/97** after the ignored deployed-object
publication was explicitly rebuilt to match the newly fetched tracked
rules database; the separate `--check` then passed. The complete
Linux suite passed **5,011 tests / 29 expected skips / zero failures**
in **417.86 s pytest / 418.50 s runner**
(`linux-dev:858b769b73294503b857031c802abf74`), with **808/808**
SVGs, correct one-worker-per-lane assignment and **56.00 summed
worker-seconds** of Chromium admission waiting. Two known Python 3.14
multithreaded `fork()` warnings remained. All three hosted workflows,
including Source Checks and deterministic outputs, subsequently passed
at that same SHA; VR-0050 is retired. The inventory at that commit was
**24 reviewed-extra / 10 unresolved** Skill source IDs. The cross-Army
usage index remains unimplemented.

**2026-11-03 General rules and game-table source/browser review (V1S-023 retired):**
At Windows `73ab29a3b9d5bbbabe682879e69cf2298020bc12`,
the pinned English N5.3 PDF and
`tools.audit_standard_game_reference_tables --pdf data/pdf/rules/n5-rules-v5.3-en.pdf`
reverified the six exact Retreat! thresholds (150–400 Army Points),
25% session-state basis and non-mandatory table sizes from printed
pp. 146–147. Focused table/source tests passed **4/4**.
Normal API/search/reverse-link tests for Initiative Roll, Combat Group,
Army Retreat!, Standard Game and Game Modes passed **4/4**;
ordinary Chromium navigation passed **14/14** across the applicable
1440/390/320 px cases: Initiative **2**, Combat Group **3**,
Retreat/Standard Game **6**, and Game Modes **3**. Checked printed
source bindings include Initiative p. 15, Combat Group p. 10 and
Game Modes pp. 6/146/147. No verified storage, API or browser gap
required a change; the existing current curated/rules pair was
preserved. This closes this bounded reference-review slice, not
whole-source or frozen-release-candidate acceptance. No additional
VD/VR obligation was created by the read-only review.

**2026-11-03 Infiltration fixed-PH source review (VR-0051 retired):**
N5.3 p. 97 permits bracketed PH=X to replace only the PH used for the
normal PH-3 Infiltration Roll. The pinned Skill source-47 inventory has
216 direct occurrences: 17 carry five exact fixed-PH signatures,
five carry bare `ReRoll` without the explicit PH=X required by the
printed reroll rule, and 194 carry neither. Only the five fixed-PH
signatures are typed. The original source-47 owner/ID assertion,
negative combination/type tests and the then-current read-only reviewer
`python -m tools.review_infiltration_ph_variant` protected those bounds.
The original reviewer has been retired; current source and type checks
retain this contract.
Its guarded `--promote` updated the tracked v9 rules database and
matched ignored deployed-object publication with a local rollback;
Windows read-only regeneration exactly matches the promoted rules SHA-256
`c016006b7eae19e80969f432a590b802bf989b5831bd6cfd1c1f26765bb3800c`.
The Linux export can have a different binary SHA due to SQLite layout or
ANALYZE statistics; the cross-platform review gate instead compares all
application-owned tables, schema and database identity. Windows
source-variant **100/100**, rules, data/build, docs, Ruff and canonical
Pyright passed. At committed `dd071c4df04d6c90cddc1a84a6974952506a097d`,
Linux source-variant **100/100** passed
(`linux-dev:530576cbc3424eef8af7f85e7c2ff9af`), and the full
four-lane/full-assets suite passed **5,014 tests / 29 expected skips /
zero failures** in **432.87 s pytest / 433.53 s runner**
(`linux-dev:fe88bdfebfcd479db587062a2028296b`), with
**808/808** published SVGs. GitHub Source Checks, Installed Wheel
Smoke and Deployment Smoke all completed successfully for the same
SHA (runs `41691029120`, `41691029210`, `41691029257`).
VR-0051 is retired; these results do not accept later edits or the
final 1.0 release candidate. No cross-Army usage index was added.

**2026-11-02 Syncthing staging worker verification (VR-0026 retired):**
After the `mcpworker` staging ACL/environment and explicit tracked
checkout preparation, Linux asynchronous jobs at
`a2769e110d17dc415c715e05f154b941c81204e9` listed
the expected `JSON`, `WIKI`, `HUMAN-SPHERE` and `SYMBOLS`
staging directories, verified three pinned snapshot SHA-256 values
and successfully planned a read-only N5.3 PDF activation without
writing it. Staging access was sufficient for subsequent explicit
activation; no automatic Git operation or staging write was needed.
The completed execution entry is retired, with historical detail in Git.

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

For a concise source-coverage audit, the runner groups **actual pytest
skip reports** by reason and count, rather than printing hundreds of
individual `-rs` entries; the total must reconcile with pytest's
skipped count. Starting with the 2026-11-03 diagnostic update, this
report defaults **on when the unfiltered full test stage is selected**,
including `--all` and the asynchronous MCP test-job interface.
An accompanying preflight in `--all` receives the same report.
Explicit `--skip-summary` still opts in for filtered test sections,
selected test nodes and standalone preflight.
`--no-skip-summary` suppresses the full-suite default. No collection, execution, worker grouping,
slot capacity or skip decision is changed.
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

**2026-11-03 Glossary full-load timeout instrumentation (VR-0023/24):**
The existing three-width
`test_visibility_zone_terms_normal_browser` acceptance now
captures `/api/glossary` response status and, **only on the
unchanged 15-second visibility timeout**, reports page
`readyState`, loading/error/list panel state, rendered entry
count, error text, JavaScript page errors and any matching API
responses. This will distinguish a pending API response from
client rendering or a visible error state on a future
full-suite failure without weakening the acceptance gate.
Targeted Windows Chromium execution passed **3/3** in
23.68 s (390px case 6.43 s), with Ruff, Pyright, docs
and diff checks green. After safe Git handoff of the committed
diagnostic revision `ce6d6d8b268438260e4831f372b34884c2c8ae09`,
the separate `linux-dev` MCP worker passed the **same 3/3
real-Chromium cases in 19.09 s** (390px case 5.15 s), job
`linux-dev:c827d624021a438a87a72f1c5fdf9ba0`.
This cross-platform isolated pass does **not** reproduce or explain the
earlier full-load failure and does not justify promoting
four Chromium slots as the default.

**2026-11-03 bounded CPU/RAM sampling for Chromium benchmarks (VR-0024):**
A new `tools.sample_test_host_resources` module runs **alongside**,
but never launches or modifies, independently scheduled test jobs.
It records one JSONL metadata header, timestamped host CPU-busy
and physical-memory-usage samples, and a final summary in a new
ignored `local/benchmarks/*.jsonl` file. Linux reads aggregate
`/proc/stat` and `/proc/meminfo`; Windows uses
`GetSystemTimes` and `GlobalMemoryStatusEx` from the
operating system. CPU busy is a delta of host-wide cumulative
counters, not per-process utilization; the first sample has
no CPU delta. This intentionally reports total host contention
from other workloads as well as the test run. Use a unique filename
and start the sampler just before a comparable test job:

```powershell
.\.venv\Scripts\python.exe -m tools.sample_test_host_resources --output local/benchmarks/host-load-windows-2slot.jsonl --duration-seconds 780 --interval-seconds 5
```

On Linux, use
`./.venv/bin/python -m tools.sample_test_host_resources --output local/benchmarks/host-load-linux-2slot.jsonl --duration-seconds 780 --interval-seconds 5`.
The module refuses absolute/escaping paths, overwrites and
unbounded sampling configurations; the source/test schema is
portable, while native measurements support Windows and Linux.
The two files must be sampled on their respective hosts and
aligned with separately pinned revision, start time, test flags
and asset coverage. A missing or prematurely stopped sampler
is incomplete evidence, **not** zero host load.
At committed source `74d00e7ecfc8518b2443bbda721a932eb7510aa3`,
the focused sampler suite passed **21/21 on both Windows
and Linux**, with maintained test-section checks **15/15**
on Windows. Native two-second smoke probes each recorded
three samples: Windows averaged **9.84% host CPU busy**
and **71.18% physical memory used**; Linux averaged
**0.06% host CPU busy** and **9.32% physical memory used**.
Linux jobs:
`linux-dev:5d014bac434e4a4f8b07d132bf96e74c` (pytest),
`linux-dev:3dd2c55769f64836879d980cc7e837b0` (native probe).
These short independent samples do **not** compare host
performance or prove Chromium stability; synchronized
full-load measurements remain pending. Ruff, Pyright, docs
and diff checks passed before the commit, and no browser
slot defaults or scheduling were changed.

**2026-11-03 same-revision full-suite skip parity and host-load evidence
(VR-0023/24, unsuccessful common source gate):**
Windows and Linux both ran full, 808/808-asset suites at
`ea438555d62fe441d7c428ed49ffb6704dc664f2`,
with default `-n auto --dist worksteal` and newly automatic grouped
skip-reason reporting. Windows job
`4a9ab9d4bd284f7db2c6546e2567d71d` finished
**4,921 passed, 28 skipped, one failed** in **517.04 s**
(pytest; 517.69 s runner). Linux job
`linux-dev:04d3dacf1efc42d1974cf1e2a3592d8a`
finished the same **4,921/28/one failed** in **570.68 s**
(pytest; 571.28 s runner), plus two established multithreaded
`fork()` warnings. **Both failed the identical deterministic
I/O assertion**, because
`tools/stage_commlink_v9_candidate.py` wrote its manifest with
`Path.write_text` without an explicit `newline` argument.
There was no reported Chromium test failure. The newline
policy was corrected to `newline="\\n"`; Windows focused
`tests/test_deterministic_io.py` **4/4** and
`tests/test_reinforcements_optional_reference.py` **3/3**
passed, with Ruff and Pyright green. These failed full
suites do not constitute cumulative acceptance of the fix.

**Skip totals match but reasons do not.** Exactly **22**
skips share their grouped reasons: 16 opted-out release-matched
DB tests, two already-promoted citations and four singletons
for earlier promoted/staging states. Windows has six
additional host-specific skips (two Gunicorn fork checks and
four symlink-privilege/host-policy checks). Linux has six
source-evidence skips instead: four referencing missing local
FAQ PDFs, one local migration staging report and one required
N5.2/N5.3 PDF set. This is a genuine **coverage mismatch**
despite both totals being 28; neither host's skipped checks
have been silently counted as passing. Pinned input coverage
and platform-dependent skip rationales require separate review.

New host resource samplers ran simultaneously, each using
5-second intervals for **780 seconds / 157 samples** in
ignored `local/benchmarks/`:
`host-load-full-windows-20261103-0831.jsonl` and
`host-load-full-linux-20261103-0831.jsonl`.
The **whole sampling-window** averages/peaks were Windows
CPU **60.31%/100.00%**, RAM **78.16%/83.75%**;
Linux CPU **30.07%/99.96%**, RAM **18.66%/25.86%**.
The measurement windows extend well after the 517/571-second
test stages, so these means are **not aligned test-only
averages**. Windows measured 1,560.39 summed Chromium
waiting worker-seconds across 15 setup events and Linux
6,171.14 across 32 events. These `-n auto` workloads
are not an equal-worker, controlled slot-capacity benchmark;
the observed differences do not prove Linux/browser slots
are slower or that four-slot capacity is unsafe.

**2026-11-03 corrected cross-host full-suite acceptance at
`5e1cdbf6` (VR-0023/24):**
After the explicit newline-policy correction was committed
and pushed as `5e1cdbf6a91b15ad2c0f67596179b1108e9d7830`,
the matched 808/808-asset, default `-n auto` full suites
passed cleanly:

- Windows `f8b502de14e84b5386d21d1f6c8a38af`:
  **4,922 passed, 28 skipped, 0 failed** in **537.68 s**
  pytest / **538.37 s** runner; **1,584.13 worker-s**
  of measured Chromium admission waits across 16 events.
- Linux `linux-dev:e60ec281afcd46daa893b8f8f1f55b88`:
  **4,922 passed, 28 skipped, 0 failed** in **566.85 s**
  pytest / **567.52 s** runner; **6,075.50 worker-s**
  of measured Chromium waits across 32 events and two
  existing multithreaded `fork()` warnings.

The six unmatched skip reasons on either host persisted:
Windows lacks symlink privileges and skips two Linux-specific
Gunicorn cases; Linux lacks selected ignored FAQ/rules PDFs
and historical migration staging evidence. Equal skip totals
are **not** equal source coverage. The default worker count
was eight on Windows, 16 on Linux; these runs verify
functional stability, not fair 2/4 Chromium slot performance.

Both new 660-second CPU/RAM captures finished successfully
(133 samples per host):
`local/benchmarks/host-load-full-windows-20261103-fixed.jsonl`
and `local/benchmarks/host-load-full-linux-20261103-fixed.jsonl`.
The complete capture's means/peaks were Windows
CPU **73.59%/100%**, RAM **69.06%/72.41%**;
Linux CPU **35.58%/100%**, RAM **21.07%/25.66%**.
Whole-capture means still include post-test time.

To align captures with the real test duration, the new read-only
`tools.analyze_test_host_resources` calculates overlap-weighted
CPU/RAM percentages using sample intervals and refuses incomplete
or malformed captures. For example on Windows:

```powershell
.\.venv\Scripts\python.exe -m tools.analyze_test_host_resources --input local/benchmarks/host-load-full-windows-20261103-fixed.jsonl --test-start 2026-11-03T08:55:33+01:00 --duration-seconds 538.37
```

Windows test-window coverage was **100%** across 109 intervals;
CPU mean/peak **86.05%/100%**, RAM mean/peak
**70.45%/72.41%**. Linux `linux-dev:eeac1d98f593419a9b273be7247edcec`
ran the same committed analyzer at `f9206e06` against the
fixed-run capture with **100%** coverage across 115 intervals:
CPU mean/peak **41.22%/100%**, RAM mean/peak
**23.24%/25.66%**. Linux analyzer regression
`linux-dev:e1710ae2f90b48958ec1c5a2b9aaafab`
passed **11/11** at that revision. Windows analyzer tests
**11/11** and test-section inventory **15/15** passed,
with Ruff, Pyright and Git diff checks green.
These are host-wide utilization measurements, not per-test
process attribution or a fair equal-worker Chromium benchmark.
The original four-slot Glossary timeout still needs
repeat controlled-capacity validation before any default change.

**Controlled browser concurrency pair, 2026-11-03 (preliminary VR-0023/24
evidence):** All runs use the same pinned commit
`5ac294165a8be49a13125ba9324281b17b406264`, complete published
assets (808/808), eight xdist workers, four isolated Chromium lanes,
Scenario FAQ A/D split, and the same 616-case browser test selection
(600 passed, 16 expected skips). Each host runs a serial two-slot then
four-slot pair with an independently started native CPU/RAM sampler.
No browser timeout or other failure occurred in either Windows run.
The historical four-slot Glossary timeout has not been reproduced,
which does **not** establish its cause.

On **Windows**, two slots took **481.83 s pytest / 482.46 s runner**,
and four slots took **402.56 s pytest / 403.26 s runner**: 79.27 s
(**16.5%**) less pytest wall time. Lane A/B/C/D teardown changed from
+360.61/+171.29/+185.67/+480.86 s to
+274.92/+235.66/+260.22/+401.57 s. Both capacities passed the
one-worker-per-lane guard. Namespace-aware timestamped traces measured
**328.55 / 0.01 summed worker-seconds** waiting (two/four slots),
**829.32 / 1,127.28 worker-seconds** of slot holding, and
**354.34 / 208.47 s** at full slot occupancy; no same-slot overlap
warning. Raw metrics:
`local/benchmarks/chromium-20261103-161832-19556/` and
`local/benchmarks/chromium-20261103-163030-34840/`.
Both native test-window captures achieved **100% coverage**.
CPU mean/peak increased from **66.87% / 94.80%** (two slots)
to **79.48% / 100.00%** (four slots), and RAM mean/peak from
**76.61% / 77.88%** to **78.89% / 85.27%**. Captures:
`local/benchmarks/chromium-v1-5ac29416-2slots-cpu.jsonl` and
`local/benchmarks/chromium-v1-5ac29416-4slots-cpu.jsonl`.
The speedup trades for greater host CPU/RAM use and higher total
Chromium slot-held worker time.

On **Linux**, the two-slot run passed **600 / 16 skipped** in
**636.13 s pytest / 636.57 s runner**, with A/B/C/D final teardowns
at +306.32/+181.02/+301.02/+632.04 s; lane ownership was correct.
The timeline measured **442.24 summed worker-seconds** of waiting
and **909.10 worker-seconds** held, with **291.08 s** at full
capacity and no same-slot overlap warning. Its native test-window
capture covered **100% of 636.13 s**, with CPU mean/peak
**22.89% / 51.07%** and RAM mean/peak **18.21% / 19.75%**.
Raw artifacts: `local/benchmarks/chromium-20261103-162532-817731/`
and `local/benchmarks/chromium-v1-5ac29416-linux-2slots-cpu.jsonl`.
The **Linux four-slot** run also passed **600 / 16 skipped** in
**396.22 s pytest / 396.69 s runner**, a **239.91 s (37.7%)**
reduction from two slots. A/B/C/D finished at
+242.55/+183.92/+237.39/+392.49 s, with correct worker ownership.
Its separate lock-namespace trace found **0.00 worker-seconds**
of admission waiting, **987.47 worker-seconds** of holding,
**156.03 s** at full capacity, and no same-slot overlap warning;
raw metrics: `local/benchmarks/chromium-20261103-163737-856283/`.
Its native four-slot test-window capture had **100% coverage**
across **396.22 s**: CPU mean/peak **38.09% / 70.28%**, RAM
mean/peak **16.40% / 19.72%**
(`local/benchmarks/chromium-v1-5ac29416-linux-4slots-cpu.jsonl`).
Compared with Linux's two-slot window, average CPU increased from
**22.89%** while mean measured RAM decreased from **18.21%**;
host-wide measurements do not isolate the benchmark's processes.
All four host/capacity runs passed the 616-case selection; the
prior isolated four-slot Glossary timeout did not recur.
The first pair alone did not establish repeatability. In a subsequent
reverse-order **four-slot** repetition at `48d0cd84`, Linux again
passed **600 / 16 skipped / 0 failures** in **395.29 s** (previously
396.22 s), whereas Windows completed **599 / 16 skipped / one failure**
in **434.84 s** (the Spec-Ops source-chart visibility wait timed out at
12 s; no gameplay assertion changed). This is evidence of an unreliable
four-slot Windows acceptance configuration under shared-host load,
but it does not prove the application or Chromium is defective.
The failing test was
`tests/test_verify_unit_skill_presentation_browser.py::test_live_chromium_spec_ops_source_charts`:
the `.source-choice-charts` visibility assertion exceeded its
existing 12 s threshold. A failure-only diagnostic now records
the active Unit slug/source ID and viewport, response statuses
for Unit/profile-help API calls, failed requests, JavaScript
exceptions, and Unit/rendered-chart state. It retains the same
timeout and test selection and does not change the production
renderer. The previous Glossary diagnostic remains separate.
The existing two-slot Windows limit remains appropriate.

**Host-specific capacity decision (2026-11-03):** The dedicated Linux
MCP worker may opt into the *validated* four-slot, four-lane, eight-worker
Scenario FAQ A/D split profile, while Windows retains two slots.
`tools.browser_test_host_profile` stores a strict, ignored
`local/browser-test-profile.json` marker on the Linux worker only.
The maintained `tools.run_checks --stage test` adopts that profile
when no worker, distribution, slot, lane, split or browser-reuse
override is explicitly supplied. Any explicit scheduling/capacity
option retains the pre-existing manual selection behavior. The
profile does **not** change clean CI, Windows, standalone direct
`pytest`, or isolated preflight defaults; it is reversible without
a Git change. Enable/check/disable on Linux with:

```bash
python -m tools.browser_test_host_profile enable
python -m tools.browser_test_host_profile status
python -m tools.browser_test_host_profile disable
```

**Host-profile acceptance (VR-0049 retired):** At pinned
`47122aa519b6d81c0b471797e9aa93ec77f4588a`, Linux's ignored
profile was enabled explicitly and its runner command verified
`-n 8 --dist loadgroup --browser-lanes --split-scenario-faq
--browser-slot-count 4 --browser-lane-count 4`. Linux focused
profile tests passed **17/17**, ops section **365/one skipped**,
and the complete suite passed **5,001/29 skipped/zero failures**
in **422.07 s pytest / 422.72 s runner** (async job
`linux-dev:33798d90fffe42caa22b2b2c697994c6`). All four
browser lanes remained on individual workers; Chromium setup
waiting totaled **54.42 worker-seconds** across one event, with
**808/808** published SVGs. Two pre-existing Python 3.14
`fork()` deprecation warnings remain. On Windows the unchanged
`-n auto --dist worksteal` command passed **361/five skipped** ops
tests, and its standard two-slot configuration was confirmed.
GitHub Source Checks (including cross-platform deterministic outputs),
Installed Wheel Smoke and Deployment Smoke all passed at that SHA.
The host-local change does not rewrite application data or CI defaults.

**Chromium instrumentation closeout (VR-0024 retired):**
The timestamped slot-wait/hold metrics, lock-namespace filtering,
overlap uncertainty, native CPU/RAM sampler, and test-window
analyzer have now passed repeated focused and real-load
verification on Windows and Linux. At `6177a8dc`, the operational
regressions passed **361 / five skipped** on Windows and
**365 / one skipped** on Linux; all hosted workflows on the
previous application commit `47122aa5` passed. The four
same-revision browser experiments at `5ac29416` passed with
complete CPU/RAM coverage and no slot ownership errors, and
Linux repeated four-slot acceptance successfully at `48d0cd84`.
VR-0024 is therefore retired as a *metrics* validation gate.
The user-approved host-specific capacities remain unchanged.

**Cross-host skip diagnostics closeout (VR-0023 retired):**
At `955c55a02bf4aa74023313506105b29a6620c862`, the maintained
test runner's optional `--skip-details` prints the exact skipped
pytest node IDs and reasons, independently of the existing grouped
`--skip-summary`; neither changes test selection or failure status.
On the same revision, the **model** section passed Windows
**3,055 / six skipped** and Linux **3,049 / twelve skipped**.
Six shared skips concern already-promoted or opt-in source staging.
The six extra Linux skips were identified exactly: two FAQ PDF
identity cases, two Silent Immunity FAQ-source identity cases,
one N5.2/N5.3 pinned-source comparison, and one missing local
migration-staging report. The files are ignored local evidence,
not tracked publication artifacts.

The **ops** section passed Windows **363 / five skipped** (all
symlink-privilege dependent) and Linux **367 / one skipped**
(a Windows-native API-only test). The separate web-metrics tests
passed **two / two skipped** on Windows (two Linux-only Gunicorn
fork cases) and **four / zero skipped** on Linux. All these
comparisons had **zero failures**. Focused capacity tests passed
**25/25**, runner tests **108/one expected skip**, Ruff and
Pyright passed. The prior Linux host-profile full suite at
`47122aa5` passed **5,001 / 29 skipped / zero failures**.
The different skip inventories are understood, explicitly
labeled and do not imply identical optional source-byte coverage.

**The remaining research is explicitly deferred until after v1.0:**
intermittent Windows Glossary/Spec-Ops full-load visibility
timeouts, the Scenario FAQ browser lifecycle/long tail,
pooled-versus-fresh browser comparisons, and optional source
PDF/staging parity. They are tracked in
[the active backlog](TODO.md#performance-storage-and-build-tooling),
not as an open VR-0023 acceptance gate. The validated Linux
four-slot and Windows two-slot limits remain unchanged; no
production browser or CI configuration changes.

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
Neither run replaces [final candidate acceptance](releasing.md#development-freeze-and-release-only-handoff).

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
The completed one-use migration staged and promoted a matched v9
`rules.db`/deployed-object publication pair, rechecked source hashes
and retained rollback copies. All 17 reviewed objects remained unchanged;
the source inventory then reported **20 unresolved Skill IDs**.
The retired script remains recoverable in Git history. This metadata
publication did not establish a Unit-usage index, attack resolution,
full browser signoff or release acceptance.

**Discover (+3/+6/ReRoll) source promotion (2026-11-02):**
Pinned source `131` has 43 direct occurrences, exclusively
`1/TEXT:+3` (24), `2/TEXT:+6` (13), or `277/TEXT:ReRoll` (six).
N5.3 pp. 68, 77 supplies scope and terminology. The source
regression pins every owner occurrence ID, owner class, signature
and exact raw string. Database tests compare both the tracked and
fresh rules export; 13 mutation cases reject unknown signatures,
wrong WIP scope, unreviewed ReRoll behavior and numeric type drift.
The completed one-use Discover migration staged and promoted a guarded
v9 rules/deployed-object pair, verified pinned SHA-256 inputs, preserved
reviewed-object content and retained rollback copies. The audit then
reported **15** unresolved Skill source IDs. Git history retains the
retired script; final release-candidate acceptance and the independent
Unit-usage projection remain separate.

**Parachutist (Dep. Zone) source promotion (2026-11-02):**
Pinned Army Skill source `33` has 305 direct occurrences and exactly
17 matching `48/TEXT:Dep. Zone` extras (12 profile, five option).
The `reviewed-extra` effect strictly permits entry from the table
edge inside the **enemy** Deployment Zone for the matching occurrence,
while the base restriction and N5.3 p. 105 explanation remain intact.
`tests/test_audit_source_variant_inputs.py` verifies source-owner IDs,
full signatures, the published and fresh rules exports; the curated
mutation tests reject incorrect IDs, raw strings, effect scope and
non-Boolean permissions. The completed one-use Parachutist migration
staged and promoted the paired v9 rules/publication output, verified
hashes, preserved all 17 reviewed objects and retained rollback copies.
Git history retains the retired script. The audit then reported **16**
unresolved Skill IDs. Browser verification, cross-Army usage projection
and final release candidate acceptance remain separate.

**Minelayer (2) source-quantity promotion (2026-11-01):**
The source audit verifies Skill source `56` has 546 direct
occurrences, including exactly 15 `267/TEXT:2` extras (14
option-level and one profile-level), with no other reviewed
signatures. The `reviewed-extra` effect is strictly an item
count scoped to deployment; it does not modify Disposable uses.
The focused `test_minelayer_two_deployment_count_matches_pinned_source`
pins all 15 Army contexts and the promoted rules database.
The completed one-use guarded migration staged and promoted a matched
rules/publication pair, checked source hashes and retained rollback copies
under ignored `local/`. All 17 deployed objects remained unchanged; the
variant audit then reported **19 unresolved Skill IDs**. The retired
script remains in Git history. The older generic v9 refresh was
incompatible with the newer schema. Focused regression, database,
publication, rules-build, mutation and cumulative test validation
were completed in November 2026.

**Chain of Command Non Specialist publication (2026-11-01):**
The source audit identifies exactly 11 source-26 `375/TEXT:Non Specialist`
occurrences, all option-level, across Joan of Arc/Joan of Arc v2
and William Wallace; 151 Chain of Command occurrences in total.
The `reviewed-extra` effect excludes only Chain of
Command-derived Specialist Troop qualification. The targeted
source-inventory regression pins all 11 occurrences and the typed
rules database; `test_specialist_candidates_ignore_non_specialist_chain_but_keep_other_skills`
protects the existing independent-qualifier behavior.
The completed one-use guarded promotion staged a matched
rules/publication pair, verified input hashes and retained rollback
copies. No deployed-object record changed (17 unchanged).
Focused source, rules-map, Specialist filter, publication and rules-build
tests passed; the audit then reported **18 unresolved Skill IDs**.
Mutation/edge-case and cumulative checks also passed in November 2026.
The retired script remains recoverable from Git history.

**Forward Observer (+1SD) source promotion (2026-11-01):**
The pinned raw Army audit confirms two profile-level
`308/TEXT:+1SD` occurrences of source `59` on TARKSHYA
Operator in ALEPH and Operations Subsection, among 609 direct
Forward Observer occurrences. The curated exact effect is one
`special-die` scoped to `forward-observer-wip-attack-roll`,
not additional Burst or Disposable uses; newly added N5.3
citations on pp. 75 and 92 establish its rule scope.
The source-variant regression and rules-database mapping
test pass. The completed one-use guarded promotion staged and verified a matched
rules/publication pair, retained rollback backups under ignored
`local/`, and left all 17 reviewed deployed objects unchanged.
The audit then reported **17 unresolved Skill IDs**. Additional
rejection/derived-index tests and cumulative full-suite verification
passed on 2026-11-01; the fulfilled VD/VR entries were retired.
The migration script remains recoverable from Git history.

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

For the frozen local candidate, serve the tracked database pair in an ephemeral
WSGI app and run the full-width and mobile-width Chromium check:

```powershell
.\.venv\Scripts\python.exe -m tools.verify_rule_fragment_browser --self-host --output local/audits/weapon-rule-fragments-browser.json
```

For an existing development or deployed server, use `--base-url URL`
without `--self-host`. The self-hosted mode shuts down its server after the run.

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

### Versioned source-clause dispositions (V1S-082 P1)

The read-only validator checks the tracked
`config/validation/source-coverage-dispositions-v1.json` contract against
current Core/Hacking curated records and declared source fingerprints:

```powershell
.\.venv\Scripts\python.exe -m tools.source_coverage_dispositions
```

Each review has one stable clause key, exact source identity/page/member and
SHA-256, explicit record owners (or `source-first` origin), a narrowly described
claim, dependencies, and **independent** semantic/browser statuses. Accepted
scoped decisions require reviewer/date/evidence and matching full-record
fingerprints; browser acceptance additionally requires a recorded Git SHA,
matched database hashes, test selectors and unchanged source/test contract
files. Missing/stale keys, duplicate clauses, bogus statuses, unaddressable
sources and dependency cycles fail closed. A clean run validates **evidence
shape and current pins only**, not reviewer correctness, source-wide omission
detection, test execution or whole-record acceptance. Only independently
reviewed, versioned and pinned clauses belong in the manifest; the first
two Trait identities have four source-language scoped dispositions, with
no browser approvals. Never import pilot/benchmark triage as approval.
The phased validation queue
remains authoritative for missing or deferred regressions.

### Paragraph-only rules-summary refresh

The v9 one-use `tools.refresh_reference_summary_layout` command was
retired during P2.5 (commit `dab737d1`). Its 2026-11-06 V1S-082
migration checked a paragraph-only change to `rule:loss-of-lieutenant`
while preserving the other 498 composed records and storing recovery
copies under ignored `local/`. That procedure and its three-file JSON
publication contract are historical evidence, recoverable from Git
history, not supported build instructions.

For a new reviewed summary-layout correction, edit the owning curated
Rules source and use the current complete database-set build and
`infinity-db database-health --db-dir` validation. Review the diff for
semantic changes; use focused curated text, Rules export, API, and
browser tests as applicable. Existing paragraph-length checks protect
readability. Neither a rebuild nor whitespace equivalence constitutes
approval of new source-derived wording.

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
`--verify-declaration-pdf data/pdf/rules/n5-rules-v5.3-en.pdf`.
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
.venv\Scripts\python.exe -m tools.report_reference_baseline --reconcile-explanation-inventory --reconcile-declarations --verify-declaration-pdf data/pdf/rules/n5-rules-v5.3-en.pdf --json-output local/audits/v1-declaration-migration-reviewed.json --markdown-output local/audits/v1-declaration-migration-reviewed.md
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
.venv\Scripts\python.exe -m tools.report_reference_baseline --reconcile-explanation-inventory --audit-conditional-declarations --verify-conditional-pdf data/pdf/rules/n5-rules-v5.3-en.pdf --json-output local/audits/v1-conditional-declaration-evidence.json --markdown-output local/audits/v1-conditional-declaration-evidence.md
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

**Historical TinBot: Neurocinetics publication boundary (2026-11-02;
reference presentation superseded 2026-11-07):**
The originally assumed `/equipment/tinbot-neurocinetics` inbound
route is absent by design: reviewed source ID 188 is not among the
four published TinBot source variants (169, 244, 247, 248). The
curated record retains its `uses-effects-of` relation to
`skill:neurocinetics`, but source-specific records without a
published Army application identity do not receive standalone
Equipment routes. At that revision, a browser regression
`test_unpublished_tinbot_source_variant_is_not_a_fake_public_route`
at 1440/390/320 px checks normal catalog-to-parent navigation,
absence of the invented variant card/link, keyboard access to the
independent Skill route, no JS errors and horizontal fit. API
and source-provenance tests enforce non-routability and exact
source membership. The later
[reference-only variant contract](data-model.md#declaration-categories-and-exact-source-variants)
preserves that Army boundary while allowing cited definitions on the family
page without claiming Unit availability. Initial test iterations corrected assumptions
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
rules database bytes and applicable Weapon-profile publication inventoried
from this checkout, add
`--verify-server http://127.0.0.1:8000` (substitute the actual server origin).
The check queries the served `/api/version` response and requires its
`snapshot_revision` to equal the SHA-256 of
`"<Army database SHA-256>:<rules database SHA-256>:<Weapon-profile publication SHA-256 or none>"`,
the runtime's snapshot identity. The baseline validates a co-located
publication against the database pair before fingerprinting it; a missing
or independently located publication contributes `none`. On mismatch it
exits nonzero **before writing
baseline outputs**; a successful run records `servedSnapshot` in JSON.
The server option is opt-in and never starts, deploys, or modifies a server.
It checks runtime identity, not static assets, processed symbols, PDF/Wiki
bytes, browser correctness or full source completeness; these require
independent checks. Rerun against the final candidate and deployment, not
only a local development server.

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

### Frozen-pair scenario and FAQ rerun (V1S-088)

**Project domains:** Data processing, Web backend, Web frontend

At the unchanged frozen pair and app code revision
`a5846dc95c5c0a36561a6a1372b05eed68a50314`, the focused two-worker
Windows run of `tests/test_scenario_catalog.py`, `tests/test_scenario_api.py`,
and `test_verify_scenario_faq_browser.py` selectors for
`test_all_24_core_scenario_setups_render_source_backed_browser_contract`,
`test_every_published_faq_has_a_normal_browser_entry_point` and
`test_faq_browser_routes_cover_every_published_topic_association` passed
**157/157**, **zero skips**, in 34.80 seconds (35.49 seconds runner time).
This covers all **24** Core game-size configurations via catalog/API and
**48** live browser selections (four scenarios × six sizes × two widths),
plus every published **29-ruling** FAQ primary topic entry at 1440/390 px
and the authored topic association inventory. The independent
`tests/test_faq_ruling_references.py` run passed **79** with **one skipped**
release-opt-in parity test in 29.21 seconds. That skipped test is **not**
claimed to have passed in this run.

The omitted opt-in is covered by the earlier **54/54 zero-skip**
[V1S-084 release-pair acceptance](#release-matched-rebuild-and-publication-acceptance-v1s-084),
which explicitly enabled `INFINITYDB_RELEASE_FAQ_PARITY=1` and tested the
tracked rules database, all primary/secondary FAQ browser routes and Haris
source-conflict disclosure. The database/publication/browser consumers remain
unchanged; that separately pinned acceptance is **reused**, not presented as
a rerun. V1S-085 already accepted the cited current source inputs.
No new source scan, rules adjudication, schema, gameplay or runtime change
was required. V1S-088 is closed for this frozen candidate. V1S-041/045/080,
local cumulative V1S-090, human sign-off and hosted/deployed exact-version
gates remain independent. VD/VR is empty.

### Frozen-pair four-scenario interactions (V1S-045)

**Project domains:** Web frontend, Web backend

The release-paired Army and rules databases accepted under V1S-084/085
remained unchanged. On Windows at
`ebcc4651df5f27611dfd7b5b90662ada13bd3005`,
four targeted Chromium selectors from
`tests/test_verify_scenario_faq_browser.py` passed **36/36, zero skips**
in independent asynchronous jobs, without a full-suite rerun:

- `test_final_frozen_scenario_browser_navigation_theme_and_size`:
  **24/24** in 25.87 s (job `c2c6eb7bfd1a4f51ac7bf916932e96d4`).
  Four Core scenarios × light/dark × 1440/390/320 px; keyboard or touch
  entry, size changes, theme, map/source citations, Back/Forward and overflow.
- `test_final_frozen_scenario_catalog_empty_and_error`:
  **4/4** in 5.95 s (job `7556a3a88d7e42f2b022a36ecd615a50`);
  desktop and 320 px controlled catalog empty/error states.
- `test_final_frozen_scenario_rapid_selection_and_reload`:
  **4/4** in 7.86 s (job `6b938caaabb14b728f893ca77a8aab17`);
  all four scenarios, overlapping Army Points changes, final SVG/selection
  and reload persistence.
- `test_final_frozen_scenario_detail_error_recovers`:
  **4/4** in 6.21 s (job `08b88151064e4a1dbff40bccf0eb878e`);
  all four scenarios recover from a controlled HTTP 503 after a valid
  alternative size is chosen.

The earlier [V1S-088](#frozen-pair-scenario-and-faq-rerun-v1s-088)
already accepted the 24 Core sizes and 48 rendered selections.
These added browser checks use the **tracked release pair**, not the
fresh curated rules export used by several development-input regressions.
No gameplay/source/runtime changes or new deferred VD/VR obligations
were needed for this mandatory acceptance gate. Hosted candidate,
manual visual/touch and eventual release SHA checks stay independent.

### Frozen-pair 81-page Unit matrix (V1S-087, local portion)

**Project domains:** Web frontend, Project infrastructure

On the unchanged frozen candidate checkout
`a5846dc95c5c0a36561a6a1372b05eed68a50314`, the targeted local
`tests/test_verify_unit_skill_presentation_browser.py::test_live_chromium_unit_detail_matrix_when_available`
passed **5/5** parametrized groups, **zero skips**, in **66.75 s**
(67.40 s check duration). The test's five groups constitute **81 browser
page configurations**, covering default and rich Unit profiles, optional
flag combinations, source-backed Spec-Ops/Reinforcement presentation and
inches/centimeters at 1440/768/390/320 px where applicable. The test
served the tracked paired databases locally in a temporary WSGI app and
used real Chrome, without requiring a separate deployment. No code, data,
publication or static assets were modified by this acceptance.

This satisfies the **local matrix only**. It does not establish that a
hosted 1.0.0 release candidate exists or matches the frozen pair. The
exact-version hosted representative gate remains open under V1S-087 until
a suitable candidate is actually served; see the next section. Cumulative
V1S-090 and the exact-SHA hosted CI/release gates are separate. VD/VR is empty.

### Pre-candidate frozen-artifact readiness (2026-11-07)

**Project domains:** Web backend, Web frontend, Deployment

Read-only preparation at `25871751a73c437ed9067a67e40d396c33ab4bc9`
(`dev/v1.0.0`, clean) confirms the tracked Army/rules pair and
published browser assets are suitable for a **development preview**:

- `tools.verify_deployment_assets`: PASS, **808/808** published SVGs
  and browser references; both runtime databases and source-bound
  reference publications validated.
- `tools.build_deployed_object_publication --check`,
  `tools.build_variant_usage --check-publication`, and
  `tools.build_weapon_profile_publication --check`: all PASS.
  No release artifacts were rebuilt or overwritten.
- `tests/test_verify_release_candidate_browser.py::test_release_gate_runs_real_local_chromium_when_available`:
  **1/1** PASS with real Chrome and a temporary local WSGI server,
  checking the exact artifact/static/version preflight, representative
  Unit DOM and postflight. This is **local integration**, not hosted
  V1S-087 acceptance.

From the same clean Windows checkout, open a local inspection preview
with the existing CLI (do **not** point the inspector at the older
public 0.10.1 deployment):

```powershell
.\.venv\Scripts\python.exe -m infinity_db serve --host 127.0.0.1 --port 8000
```

Inspect `http://127.0.0.1:8000/`,
`http://127.0.0.1:8000/glossary#attribute-s`, and a Unit detail
showing a Silhouette preview (for example `/units/dragoes`).
Use browser responsive mode for desktop/320/390 px preliminary checks;
**real-device touch sign-off** still requires an operator-controlled
trusted-LAN preview and records the device/browser, exact SHA and result.
Never expose the development server to an untrusted interface by default.
Stop the local preview with Ctrl+C.

**Historical pre-candidate boundary:** on the recorded `25871751`
development preview, package and API versions were still `0.10.1`.
The `INFINITY_DB_DISPLAY_VERSION` presentation override cannot replace
an exact-version `/api/version` check. The untagged 1.0.0 candidate
metadata step below resolves this sequencing dependency without promoting
the public release.

### Untagged 1.0.0 candidate version checkpoint (2026-11-07)

**Project domains:** Project infrastructure, Web backend, Web frontend

On the validated development implementation after `2be87f69`, release
preparation sets **both** `pyproject.toml` and
`src/infinity_army_data/__init__.py` to `1.0.0`. In a source checkout,
the footer may display `1.0.0+dev`; the real `/api/version` endpoint
and wheel metadata instead use **exactly `1.0.0`**, not a presentation
override. All changes remain **untagged** on `dev/v1.0.0`, with the public
release and `docs/CHANGELOG.md` still at **0.10.1** and **Unreleased**.

Focused local release-preparation checks passed:

- `tests/test_version.py`: **6/6**, zero skips, consistent Python and
  package metadata (job `04a2dac565a748b3bd5a342c516a3e4c`).
- `tests/test_verify_release_candidate_browser.py::test_release_gate_runs_real_local_chromium_when_available`:
  **1/1**, real Chrome against a temporary local WSGI application, with
  before/after version, runtime snapshot and static revision checks
  (job `0ac21a8c183a49d1b73a0b547e8fd20a`).
- `tests/test_web.py::test_browser_version_check_uses_an_uncached_server_version`:
  **1/1** (job `b58f04f617934e61b4f52dddc53fe829`).
- `tests/test_release_notes.py::test_checked_in_changelog_parses_current_and_historical_releases`:
  **1/1** (job `282836b03bdf427082a479fbf34f301a`).
- The exact-candidate verifier rejects a mismatched version or static
  fingerprint before browser execution (**2/2**, job
  `962e136716db4ea581dd8590bc0edb0f`); runtime snapshot identity
  remains consistent for attached, absent or independent Weapon-profile
  publication layouts (**3/3**, job
  `d8ca9b287e4944eb9634f853d43aab13`).
- Read-only `tools.verify_deployment_assets`: **808/808** processed
  SVGs and runtime/reference publications source-matched; tracked
  `tools.build_variant_usage --check-publication` and
  `tools.build_weapon_profile_publication --check`: both PASS.
  Tracked databases and published data were **not rebuilt or modified**.

This is **local preparation evidence**, not hosted V1S-087 or human
V1S-080/089 acceptance. To inspect the real candidate, restart the
development server after this checkpoint and request
`http://127.0.0.1:8000/api/version`; verify `version: "1.0.0"` and
the current snapshot/static values. The release owner still needs to
serve a candidate on an accessible, controlled origin and run the
independent exact-version `tools.verify_release_candidate_browser` gate,
with local browser and human sign-off recorded below. Final
changelog promotion, V1S-090 cumulative testing, merge/tagging and
deployment remain gated independently.

### Final candidate manual notice and Silhouette acceptance (2026-11-07)

**Project domains:** Web frontend, Project infrastructure

The release owner reported **all manual checks passed** on the untagged
`1.0.0` candidate `73e807b3887bfec4e4ec9cba7791b1e5cda0012f`,
using **Windows Firefox and iOS Safari**. This accepts the notice/navigation
checklist under V1S-080 and the Silhouette visual/hover/keyboard/touch
checklist under V1S-089, including 320/390 px and light/dark presentation.
Browser and OS version numbers were not supplied; the result is
release-owner-reported human evidence, not an agent-observed device session.
V1S-080 and V1S-089 are complete on this candidate. Repeat affected checks
if their implementation, source pair or browser assets change.

The local inspection preview's `/api/version` was verified before and after
the report: version `1.0.0`, static revision `c135d9dba2cf9b77`, runtime
snapshot `5e79f6ac1d6cfa74d1f5dee71f2f2730e4b6f6fea45572469ae65652ab10c0ef`.
The existing `tools.verify_release_candidate_browser` command also passed
**21/21** real Chrome Unit cases at 1440/390/320 px against that preview,
with matching version/runtime/static preflight and postflight. This is
local candidate evidence; it does not close the independently hosted
V1S-087 gate or approve final cumulative testing, merge, tagging or deployment.

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

### Isolated Linux served-candidate acceptance (V1S-087)

**Project domains:** Project infrastructure, Web backend, Web frontend

With explicit release-owner approval, a clean Git export of
`d758e128a554f7cae6402599c30f898814df3888` was packaged as the
`1.0.0` wheel and served from a separate Linux staging directory using
Python **3.14.4** and Gunicorn **23.0.0**. Installation used only the
verified bundled wheels. The service binds to loopback; Windows Chrome
reached it through an SSH tunnel. Existing development checkouts and the
public **0.10.1** service were not changed.

`tools.verify_release_candidate_browser` passed **21/21** Unit cases
(seven Units at 1440/390/320 px), with exact preflight and postflight:
version `1.0.0`, static revision `4ae85967ab930786`, runtime snapshot
`5e79f6ac1d6cfa74d1f5dee71f2f2730e4b6f6fea45572469ae65652ab10c0ef`.
The clean export passed artifact verification for **808/808** SVGs,
the paired databases and reference publications. All **1,032** compared
wheel source members matched the clean exported files byte for byte.

The first verifier attempt correctly rejected the Windows working-copy
static fingerprint `c135d9dba2cf9b77`. Inspection proved that three
fingerprinted files differed only by CRLF/LF line endings. Acceptance
then used the retained **build-matched clean source**, including its
`src` import path, rather than the editable Windows installation. No
expected fingerprint or verifier assertion was overridden. When checking
a packaged deployment, import the verifier's application modules from
that same retained source or installed wheel; a working copy with different
asset bytes is not a valid fingerprint baseline. Private JSON and byte
comparison evidence remain under ignored `local/candidates/`.

This closes V1S-087 together with the previously accepted local 81-page
Unit matrix. Final cumulative V1S-090, exact-SHA hosted CI, release metadata,
merge/tag and production/post-deployment acceptance remain separate.

### Cumulative candidate acceptance (V1S-090 / VR-0142)

**Project domains:** Project infrastructure, Data processing, Web backend, Web frontend

The frozen candidate passed the following complementary checks. None is
production deployment or final exact-main-SHA/tag acceptance.

- **Full source and browser suite:** `linux-dev` job
  `ca6eb9cd07d244cd8d316a5d1c551867` on
  `e5700703d8d9656360c9cf9e1ef8be2a0e177001` passed **5,847 tests,
  38 skipped, zero failures**, with two existing Python 3.14 fork deprecation
  warnings in **700.79 s**. The eight-worker/four-slot/four-lane run required
  **808/808** SVGs and used the activated pinned rule/FAQ/ITS PDFs. There were
  no missing-source or missing-browser skips. Lint, type, Army/rules builds
  and the source-occupancy gate also passed: zero of 39 potential unrepresented
  fields populated. The 38 skips were 17 release-FAQ opt-ins, 14 independent
  cross-browser cases, six prior/optional migration checks and one Windows-only case.
- **Release-pair FAQ:** the unchanged runtime pair passed the separate Windows
  **17/17** opt-in source/primary/secondary/conflict batch. Human Windows Firefox
  and iOS Safari acceptance and the served-candidate Unit matrix retain their
  separately recorded evidence above.
- **Isolated index/package gate:** after the preflight-only argument-forwarding
  repair, `linux-dev` on `3b73a100d5c3da868900ddb1d50244e6f2f91c67`
  passed **152/152** focused runner/capacity/section tests and complete indexed
  preflight, including artifact/lint/type, wheel contents and installed-wheel
  normal/asset-free runtime. Job `1576d58f53434dfa93821f3bb0f87bfa` passed;
  job `53aaab9af66d4345875c5c5898d9bdad` repeated it with an explicit skip
  summary for retirement review. Both clean-export suites reported **4,604
  passing and 1,283 skipped cases** across all 5,887 indexed tests. The 71 skip
  reasons reflect excluded private sources/archives, optional Playwright,
  opt-in cohorts, historical Git/migration evidence and Windows-only coverage;
  these are not additional source/browser passes. The full-source suite and
  separate opt-in/hosted cohorts supply that coverage.
- **Documentation and final state:** the complete Windows docs stage passed
  (44 linted files, 43 path/heading-checked files), with Ruff/Pyright clean.
  Post-execution Linux inspection confirmed the intended branch/SHA, no tracked
  changes, and **808/808** source-matched graphical/runtime/reference artifacts.
  [Source CI](https://github.com/frankysan/InfinityDB/actions/runs/42392307798)
  passed every OS/Python job and cross-platform deterministic outputs on `3b73a100`;
  wheel, deployment smoke and all four cross-browser jobs also passed.

The repaired failures were stale scenario/FAQ and Developer Mode browser
expectations, plus omitted explicit browser capacity in isolated pytest.
The main source-suite command, application, curated data and release artifacts
did not change after the full-source pass. Focused runner regressions and full
isolated execution verify the later orchestration change. Failed full reports
and the final complete reports remain under ignored `local/candidates/`; Git
history retains the intermediate repairs. No transient tool was added to the
tracked tree or retained as a build/release dependency.

This completes V1S-090 and VR-0142, with **VD 0 / VR 0**. Release-metadata
edits must receive their affected validation before merge/tag preparation.

### Prepared 1.0.0 release metadata (V1S-092)

**Project domains:** Project infrastructure, Web frontend

After cumulative acceptance, release preparation consolidates the prior
Unreleased material into the dated **1.0.0 / 2026-11-07** section, with
five player-summary bullets, user/operator detail and upgrade instructions.
The bare Unreleased heading remains for future work and is omitted from
What's changed. Historical sections from 0.10.1 onward are preserved exactly.
README identifies the prepared version and the previously published release
without asserting that the candidate is already published. Package/API
versions remain consistently `1.0.0`; no release data or static assets changed.

Immediate release-publication integrity checks passed **25/25** existing
release-note, version and HTTP-history tests. A real Chrome check of the
served preparation passed **6/6** cases at 1440/390/320 px in both themes,
including version/date, summary and historical entries, keyboard expansion,
all four detail categories, no horizontal overflow and no JavaScript,
failed-request or HTTP errors. Screenshots and JSON are retained privately.
The complete Git-index/package gate passed on
`a47a573d2afd6376dcc46abe9539e04177c6ca98`, `linux-dev` job
`f267609976f24b6ab9673399744c7669`, in **335.22 s**. The clean export
passed **4,604 tests with 1,283 skips** across all 5,887 indexed cases,
with required **808/808** assets, indexed artifact verification, lint/type,
wheel-content checks and normal/asset-free installed-wheel runtime. Both
installed CLI entry points reported `1.0.0`. The 71 skip reasons match the
previous isolated gate: private source/archive exclusions, optional browser
dependencies, opt-in cohorts, historical migration/Git evidence and one
Windows-only case. The cumulative full-source suite and independent cohorts
above retain that coverage; skipped cases are not counted as passes.

Complete Windows documentation checks passed (44 linted files, 43 link-checked
files), with Ruff/Pyright clean. Post-execution inspection confirmed the pinned
Linux SHA and a clean tracked tree. The full report, skip review and browser
evidence remain under ignored `local/candidates/`. This completes V1S-092
and VR-0143, with **VD 0 / VR 0**. Merge approval, exact-main-SHA hosted CI,
tagging and deployment remain independent release gates.

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
.venv\Scripts\python.exe tools/audit_1_0_reference_inputs.py --rules-db local/audits/1.0-rules-current.db --wiki-history "data/wiki/WIKI-en-history 20260928-165727.zip" --wiki-history-es "data/wiki/WIKI-es-history 20261009-215316.zip" --wiki-snapshot "data/wiki/WIKI-en 20260926-200832.zip" --wiki-snapshot-es "data/wiki/WIKI-es 20261009-211304.zip" --core-pdf "data/pdf/rules/n5-rules-v5.3-en.pdf" --faq-pdf "data/pdf/faq/n5-faq-v0.1-en.pdf" --json-output local/audits/1.0-source-evidence.json --markdown-output local/audits/1.0-source-evidence.md
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
.\.venv\Scripts\python.exe -m tools.audit_weapon_trait_cross_sources --core-pdf "C:\path\to\n5-rules-v5.3-en.pdf" --wiki-history "C:\path\to\WIKI-en-history.zip" --json-output docs/audits/weapon-trait-cross-source.json --markdown-output docs/audits/weapon-trait-cross-source.md
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
.venv\Scripts\python.exe tools/audit_weapon_chart_profiles.py --core-pdf data/pdf/rules/n5-rules-v5.3-en.pdf --army-db data/generated/infinity.db --json-output local/audits/weapon-chart.json --markdown-output local/audits/weapon-chart.md
```

The output includes the source PDF SHA-256, raw compared fields, range-band
evidence, candidate discrepancies, and any unresolved chart rows. Saving Roll
multipliers are interpreted together with the Saving Attribute: an Army
`savingNum=1` with `saving=-` is non-operative and matches a printed `--`.
The corrected extractor aligns 173 detected rows, with 171 five-field
matches and 172 range-band matches. Kobra Pistol CC Mode has a Saving Rolls
source discrepancy candidate (PDF 1, Army 2); the generic Suppressive Fire
Mode Weapon has a printed `*` versus Army `0` Ammunition sentinel; and
Katyusha MRL prints unsigned `3` where Army has `+3`. The separate Disco Ball
object's attributes match. The
[early-row regression](#v1s-082-weapon-chart-early-row-regression-vr-0133)
records the tested revision and source pins.
The [V1S-070 source review](v1.0-source-coverage-audit.md#weapon-profile-and-multimode-chart-review-v1s-070-2026-11-05)
records the existing source dispositions for Kobra and Katyusha; the Kobra
correction request remains open under SRC-021. This is still partial evidence:
the V1S-072 acceptance now covers the full published profile storage/API/browser
projection (see the [acceptance evidence](v1.0-source-coverage-audit.md#v1s-072-full-profile-storageapibrowser-acceptance-2026-11-05)),
while remaining auxiliary/equipment discovery and special-weapon prose semantics
stay under their separate 1.0 tasks. The chart report also records the exact Army
database SHA-256 so it can be safely combined with enrichment evidence from the
same snapshot.

For the seven supplementary object Silhouette conflicts, cross-check both
N5.3 language PDFs and both archived Wiki Weapon Charts as **distinct
publications**. The read-only provenance audit additionally distinguishes
each Dazer-specific Wiki equipment page from its language's chart and pins
all input hashes. It requires the locally retained source archives, PyMuPDF,
and the generated Army database (none are added to Git):

```powershell
.venv\Scripts\python.exe -m tools.audit_auxiliary_silhouette_provenance --pdf-en data/pdf/rules/n5-rules-v5.3-en.pdf --pdf-es data/pdf/rules/n5-rules-v5.3-es.pdf --wiki-en "data/wiki/WIKI-en 20260926-200832.zip" --wiki-es "data/wiki/WIKI-es 20261009-211304.zip" --army-db data/generated/infinity.db --json-output local/audits/auxiliary-silhouette-provenance.json --markdown-output local/audits/auxiliary-silhouette-provenance.md
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

`config/validation/deployed-object-delivery-reviews.json` pins **28
audit-only delivery paths** across the 17 reviewed object identities. They
distinguish Pitcher-fired and Place Deployable delivery of the same
Deployable Repeater source profile; Disco Baller versus its Disco Ball
mode/object; Drop Bears' thrown versus deployed mode; and Mine Dispenser's
loadout-dependent Mine subtype.
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

The review also classifies seven summary-keyword cases:
**WildParrot** (N5.3 p. 74), **Dazer** (pp. 121/186), and **FastPanda**
(pp. 82/186) have exact Army-source object profiles; Dazer's S0/S1
disagreement stays explicit. **Mines** (p. 72) is a shared rules family, not
one generic object or Mine subtype. **D-Charges** (p. 70) resolve during
the same Order and have no persistent four-stat object profile. **Cube**
(p. 121) is automatic equipment; **TinBot** (p. 127) uses a non-targetable
State Token rather than an independently targetable Deployable. The current
19 reviewed delivery-origin records count as covered candidates, not
unreviewed objects.

The current curated-summary scan finds 24 matching definitions; the 12
candidate decisions and 19 delivery-origin records (which overlap) account
for all 24, leaving no unreviewed candidate. A second read-only audit also
searches structured **Requirements, Effects,
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
scan** across all **106 curated Weapon/Equipment definitions**. Unlike the
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

The 106-record census is limited to maintained Weapon/Equipment
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
manifest pins **61 source-reviewed definitions** in this bounded keyword scan,
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

The current 61-record set also covers ten broader clauses: Game Sequence
and Order Pool resources, Command Tokens, General Movement, Line of Fire,
Zones and Contact, Cover, Climb, CC Attack, and the Template
Weapons/Equipment procedure (N5.3 pp. 11–21, 29–33, 41–44, 51, and
128–129). These distinguish resources, existing Troopers and
representations, movement/attack procedures, and scenery conditions; they
add no deployed Weapon/Equipment identity or delivery edge.

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
detailed source fields. All 61 keyword-matching definitions are classified,
but the scan covers neither unmentioned terms nor other source domains and
is **not** a complete N5.3 object inventory.
`tests/test_deployed_object_non_catalog_queue.py` checks these boundaries.

### Expanded non-catalog battlefield-element discovery

The current 61-definition queue excludes other relevant wording, including
Consoles, Supply Boxes, Disco Balls, and Marker/decoy representations. Run a
separate, read-only pass over Skill/Rule/Trait/Term/State definitions:

```powershell
.venv\Scripts\python.exe -m tools.audit_deployed_object_expanded_queue
.venv\Scripts\python.exe -m tools.audit_deployed_object_expanded_queue --json
```

The expanded audit excludes all 61 candidates from the original scan rather
than recounting them. It identifies **28 additional definitions, all
classified** in `config/validation/deployed-object-expanded-reviews.json`,
with no PDF-only decisions or missing maintained N5.3 citations. N5.3 pp. 151
and 153 establish that Domination's four Consoles and Supplies' three Supply
Boxes are *scenario-specific objectives*,
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

Three additional source-reviewed cases cover **Automatic Reaction Order**
(pp. 13–14), **Moving and Measuring** (pp. 27–28), and **Replacing Game
Elements** (p. 22). They describe an existing Trooper Marker/ARO, movement
route representations, and replacement of an existing game element,
respectively—not another deployed Weapon/Equipment identity.

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
.venv\Scripts\python.exe -m tools.audit_hacking_device_program_source_chart --pdf data/pdf/rules/n5-rules-v5.3-en.pdf --json
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

This was a one-time staging and promotion procedure. The old command
and `tests/test_hacking_device_chart_citation_staging.py` were retired
during P2.5; they can be recovered from Git history, **not run as a
current build or release workflow**. The original stage refused an
existing directory and wrote `staging-report.json` with the original
source and Army SHA-256, verified PDF SHA-256, four migrated IDs, and
three artifact hashes. It did not change the tracked checkout.
The retired staging-only test module built and validated the three
artifacts in a temporary directory, compared 17 object records
byte-for-byte and checked the tracked inputs remained unchanged.

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
.venv\Scripts\python.exe -m tools.audit_hacking_program_statistics_chart --archive "data/raw/JSON 20260929-114335.zip" --pdf data/pdf/rules/n5-rules-v5.3-en.pdf --json
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
.venv\Scripts\python.exe -m tools.audit_restrictions_source_chart --pdf data/pdf/rules/n5-rules-v5.3-en.pdf --json
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
`src/infinity_db/web/static/restrictions-reference.json`; the standalone
General Rules chart page loads this read model at `/rules/restrictions`.
The `/rules` catalog links to it, and older `/rules#restriction-*`
bookmarks redirect to the corresponding chart anchor.
The display groups six source conditions and 14 linked, condition-scoped
negative facts. Troop Type selectors without canonical references remain
plain text. The JSON must match the deterministic source projection
byte-for-byte:

```powershell
.venv\Scripts\python.exe -m tools.audit_restrictions_source_chart --check-publication --pdf data/pdf/rules/n5-rules-v5.3-en.pdf --json
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

**2026-11-07 standalone-page relocation:** The original catalog-attached
chart was moved to `/rules/restrictions`, with its own shell and padded
reference surface. The `/rules` directory now links to the chart instead
of fetching/rendering it below the listing. Contextual reverse links go
directly to the dedicated page; old `/rules#restriction-*` fragment URLs
are retained through a browser redirect. The source manifest, six
subjects, fourteen conditions, and typed qualifications were not changed.
At the implementation revision based on `9add9ae`, focused Windows
checks `test_restrictions_reference_has_standalone_rules_page` and
`test_restrictions_chart_normal_chromium_at_three_widths` both passed
(**2/2, zero skips**). The Chromium test covers 1440/390/320 px,
source rows, navigation from the catalog, linked seven-page context,
original bookmarks, card inset and no horizontal overflow.
Light/dark, soft-navigation and controlled failure-mode visual
regressions remain deferred to VD-0113 / VR-0139.

**2026-11-07 developer detail visibility:** Contextual Restrictions sections
on Skill, Equipment and State details now require Developer Mode. The
full `/rules/restrictions` reference remains public from the General Rules
directory, and original source conditions and chart anchors are retained.
`tests/test_game_mode_source_table.py::test_restrictions_chart_normal_chromium_at_three_widths`
now checks both default-hidden and Developer Mode-visible contexts before
following source links. Likewise, the shared `exactVariantUsageSection`
renderer on Skill and Equipment pages is Developer Mode-only;
`tests/test_web.py::test_variant_usage_browser_links_exact_contexts_and_unit_profile_groups`
checks visibility toggling and source-link continuity. These selectors
were updated but **not executed during the implementation pass**;
their linked obligations remain in VD-0112/0113 and VR-0138/0139.
Ordinary rules, descriptions, variants and their citations remain visible.

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
.venv\Scripts\python.exe -m tools.audit_silhouette_template_source_table --pdf data/pdf/rules/n5-rules-v5.3-en.pdf --json
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

### V1S-089 Silhouette manual visual acceptance preflight

**Project domains:** Web frontend, Project infrastructure

On the unchanged tracked source/database pair at
`2f4f4686625e11dc5d760a02096237029d37e660`,
`tests/test_silhouette_template_source_table.py` passed **4/4,
zero skips** in 1.67 seconds (Windows job
`cadfeb8a2f4a4fc4a1a05cbf94338553`).
The source/geometry fixture verifies the pinned English N5.3 printed
Silhouette table, the S1–S8 proportional SVG inputs and the S0/SX
text-only exceptions. It **does not** constitute rendered visual approval.

**Release-owner manual walkthrough (accepted below):**

1. On the release-matched candidate, open the Glossary's Silhouette
   Attribute (`S`) reference. Verify that S1–S8 templates and captions
   are legible, correctly proportioned at one scale, and that S0/SX
   remain explicitly described without substituted diagrams.
2. On a Unit detail page displaying a numeric `S` attribute, hover
   its Silhouette preview, then focus its trigger using Tab. Confirm
   that the popover appears for mouse/keyboard, is readable, stays
   within the viewport, and closes when focus leaves it.
3. On a touch-capable device, tap that trigger to open the preview
   and tap it again to close it. Verify the comparison with S2
   and that no text, trigger or preview becomes inaccessible.
4. Repeat the presentation at approximately **320 and 390 px** in
   **light and dark** themes. Confirm visual scaling, contrast,
   absence of clipping/horizontal page overflow and usable
   focus/touch targets. Record candidate SHA, device/browser,
   results and any screenshot-backed defect.

**2026-11-07 development-preview walkthrough:** The release owner reported
**6/6 manual Silhouette checks passed** at
`2df92f95faaebd435b9f9a943929cffb1d8f7c5e`: proportional
S1–S8 and readable captions, no invented S0/SX diagrams, mouse
hover and keyboard focus open/close, **actual-device touch** open/close,
and both themes at 320/390 px without clipping or horizontal overflow.
The specific device/browser version was not supplied in the result.
This is human evidence for the development preview, **not** final
version-matched v1.0 candidate acceptance. The later
[candidate manual acceptance](#final-candidate-manual-notice-and-silhouette-acceptance-2026-11-07)
closes V1S-089.

The older public release and the source preflight do not establish candidate
visual acceptance; use the later human sign-off linked above. The cumulative
full suite under V1S-090 retains its separate hosted-candidate prerequisite.

### N5.3 Game Modes versus general setup/reference tables

The **Game Modes chart** (printed English N5.3 p. 6) is a separate
recommended-play reference, not an authoritative scenario forces/setup
contract. Its six named modes provide Army Points, baseline SWC,
recommended table size, Deployment Zone dimensions, and nominal duration.
The independent N5.3 Retreat! and advisory table-size sources remain on
pp. 146–147. Audit the same Army Points keys across both source tables:

```powershell
.venv\Scripts\python.exe -m tools.audit_game_mode_source_table
.venv\Scripts\python.exe -m tools.audit_game_mode_source_table --pdf data/pdf/rules/n5-rules-v5.3-en.pdf --json
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
.venv\Scripts\python.exe -m tools.audit_standard_game_reference_tables --pdf data/pdf/rules/n5-rules-v5.3-en.pdf --json
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
.venv\Scripts\python.exe -m tools.audit_terrain_scenery_source_gaps --pdf data/pdf/rules/n5-rules-v5.3-en.pdf --json
```

The audit pins **five Terrain Types** (Aquatic, Desert, Mountain, Jungle,
Zero-G), **18 printed suggestion/example labels** (retaining the source's
`Artic Plains` spelling), and **two Scenery Access Width Tokens** (`Narrow
Gate` / `Wide Gate`). The `skill:terrain` reference exists;
standalone Special Terrain and Access Width reference definitions are
now **promoted** as N5.3 general rules. The subsequent maintained-text
review and coordinated binary refresh are complete (see below).
Gate Token labels do not have separate canonical definitions.
The audit requires both accepted rules and rejects missing or unsupported
definitions. Its optional `--pdf` mode verifies source headings, names and
Narrow Gate eligibility against the local English N5.3 source. Without
the ignored PDF, it still checks maintained and published domain boundaries;
it does not claim to have re-extracted the PDF.

The terrain/scenery and core-scenario boundary audits read deployed objects
directly from validated Rules SQLite, bound to the selected Army bytes. Use
`--army-database PATH --rules-database PATH` to select alternate files;
their locations and names are independent. Both default to the tracked
database pair. Reports include `armyDatabaseSha256` and
`rulesDatabaseSha256`, replacing hashes of a synthesized JSON publication.
The retired `--publication` option and loose JSON recovery path are gone.
Missing, incompatible or mismatched embedded models fail closed without
creating or modifying inputs; adjacent `deployed-objects.json` is ignored.

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
The original one-time staging and three-file promotion are complete.
The pre-promotion staging script, its tests and proposal JSON were retired
in P2.5 at `7330c310`: their exact historical content is available in
Git history, not as current instructions. The maintained terrain source
audit now rejects the original fully unmodelled state and missing source
citation pages. The accepted curated Rules definitions are authoritative.

The first post-promotion rules check revealed two missing interaction-review entries
and reviewed maintained-text aliases. Those reviews are now recorded:
the interaction checklist has **200/200 supporting identities**, Prone
State references use canonical links, and the ordinary Terrain noun is
pinned separately from the `skill:terrain` identity with exact
passage hashes. The rules build now passes.

The final historical two-binary refresh **was completed and verified**
to match the promoted terrain/scenery source corrections with `rules.db`
and `deployed-objects.json`. The archived staging report, source hash,
release baseline, schema, Restrictions and deployed-object pair
fingerprints were checked at the time. No deployment was performed by
that migration procedure.

**Historical procedure retired in P2.5:** the standalone terrain
stager, staged-pair freshness verifier and their staging-only tests
were deleted in commit `15a2ed23`. Their old commands and assertions
remain available through Git history, not as live instructions.
Do not reuse ignored historical staging directories: their source
or release baseline may differ. The current path builds the selected
database set and validates it with `infinity-db database-health --db-dir`.
The maintained source, schema, embedded Restrictions and provenance
checks are described in the current P2.5 acceptance record above.

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

Alternate database selection and input hashes follow the
[terrain/scenery audit contract](#terrain-and-scenery-structures-source-gaps).

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
.venv\Scripts\python.exe -m tools.audit_deployed_object_citation_migrations --json --pdf data/pdf/rules/n5-rules-v5.3-en.pdf
```

The read-only preflight verifies all three manifests and all 14 exact
`sourceId: n5-core-v5.3-pdf` citations. It reports **0 pending / 14
migrated** and rejects partial, duplicate, or stale migrations. `--pdf`
also verifies source excerpts against the local English N5.3 PDF and
reports its SHA-256; this requires PyMuPDF. Normal CI validation does
not require the ignored PDF. The curated citations specify verified
pages without adding unverified section labels.

The migration was originally built in an isolated staging directory
from the pre-migration checkout, requiring all 14 citations to be
pending. Its one-use `tools.stage_deployed_object_citation_migration`
command was retired during P2.5 and remains available in Git history,
**not as a current build instruction**.

The original exclusive staging directory contained a citation-only edit
to the maintained N5.3 curated JSON, three reviewed manifests with only
temporary `citationStatus` and `pdfExcerpt` fields removed, and a freshly built
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

The read-only inventory is for source review; web requests use the embedded
Rules model. The standalone deployed-object JSON builder, reader and legacy
publication fixtures are retired. Validate a selected complete database set with:

```powershell
infinity-db database-health --db-dir data/generated
```

`infinity_db.deployed_object_builder` owns the deterministic reviewed model;
Rules SQLite stores it with the selected Army fingerprint and source/review
evidence. `tests/test_deployed_object_publication.py` checks deterministic
source reconstruction against the actual embedded release, exact subtypes,
reviewed delivery edges and direct/Include occurrence identity. Its negative
model cases reject malformed evidence before storage creates any tables.
`tests/test_deployed_object_storage.py` checks exact relational round trips,
Army pairing and rejection of tampered evidence/source selectors and Unit
ownership after reading stored rows. When
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
real API and Chromium at 1440/390/320 px with an isolated, matched database
pair and no deployed-object JSON. There are 17 reviewed entries, not the entire game-object corpus;
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

Image assembly and deployment-smoke CI validate the selected database set and
its embedded model rather than generating or packaging deployed-object JSON.
Current v10 images still require matched variant and Weapon-profile JSON;
the opt-in complete build embeds those projections as documented in the
[data lifecycle](../data/README.md). Browser success alone does not establish
hosted, container or final-release acceptance.

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
.venv\Scripts\python.exe tools/audit_enrichment_coverage.py data/generated/army.db --rules data/generated/rules_n5.db --output local/audits/weapon-enrichment.json
.venv\Scripts\python.exe tools/audit_weapon_definition_gaps.py --army-db data/generated/army.db --enrichment local/audits/weapon-enrichment.json --chart local/audits/weapon-chart.json --json-output local/audits/weapon-triage.json --markdown-output local/audits/weapon-triage.md
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
baseline failure, reproduction and resolution remain documented in
[V1-A05](v1.0-source-coverage-audit.md#v1-a05--weapon-gap-triage-aborts-on-completed-definitions).

The reviewed Weapon-profile citations are embedded in `rules_n5.db`.
Verify that its source-paired rows still match the authored decisions without
reading the PDF, generating loose JSON or acquiring sources:

```powershell
.\.venv\Scripts\python.exe -m tools.build_weapon_profile_publication
```

The read-only check requires exact embedded citation identities, current PDF
metadata and profile/mode fingerprints. `tools.verify_deployment_assets`
reuses the check before packaging. Source and browser regressions remain
separate evidence.

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
python tools/audit_weapon_traits_prose.py --core-pdf "C:\path\to\n5-rules-v5.3-en.pdf" --json-output docs/audits/weapon-traits.json --markdown-output docs/audits/weapon-traits.md
```

The corrected N5 v5.3 audit yields 147 literal Trait-list matches, 16 reviewed
notation equivalents, two manually checked source-cell matches, and eight
remaining membership/classification candidates across 173 detected rows
(zero deferrals). The
[early-row regression](#v1s-082-weapon-chart-early-row-regression-vr-0133)
records the tested revision.
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
no horizontal overflow. The original rollback-aware
Plasma/Immunity staging step retained all 17 reviewed deployed objects;
its one-use command is retired under P2.5. Current
source and API checks live in
`tests/test_immunity_combined_saving_roll_example.py`
and `tests/test_immunity_plasma_critical.py`.
This is not an attack evaluator or a universal
Weapon Trait ruling.

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
source label, semantic links and no overflow. The
historical rollback-aware staging procedure
promoted a synchronized database/publication pair;
all 17 reviewed deployed objects remained unchanged.
The one-use staging script is retired; current source,
curated and API tests remain authoritative.

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
horizontal overflow. The completed one-off promotion synchronized `rules.db`
and deployed-object publication with recovery backups, keeping all 17 reviewed
deployed objects unchanged and Army Weapon profiles intact. The migration
script is retired; Git history retains it.

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
The completed one-off rules DB/deployed-object publication retained all
17 reviewed objects with recovery backups. The migration script is retired;
Git history retains it.

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
pass real Chromium at 1440/390/320 px. The completed one-off coordinated rules database/publication promotion
retained 17 deployed objects and recovery backups. The migration script is
retired; Git history retains it. This is not a Comms/immunity evaluator
or an Armed Turret adjudication.

**BTS Immunity / E/M CC Weapon, 2026-10-30:**
`tests/test_immunity_bts_em_cc.py` verifies the pinned N5.3
pp. 64, 67, 95–96 and 177 excerpts, exact Army E/M CC Weapon
source identity and BTS/2 × 2 profile, fourth source-scoped Immunity
case, API publication and preservation of Weapon profile fields.
Curated mutations reject unrelated weapons, Comms Attack scope,
source/component changes and unsupported roll results. The completed one-off coordinated promotion checked the exact record and
preserved all 17 deployed objects with a rollback backup. The migration
script is retired; Git history retains it.
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
Both the 29 primary and 19 secondary browser topic associations
originally asserted selected English source, version and source-date labels.
**2026-11-07 presentation revision:** The FAQ section no longer repeats
its date-anchor disclaimer above the cards. Each card instead uses the
shared `rulesCitationList` `Sources:` line with the selected English FAQ
version, link and printed page. Source/selection/original-publication dates
remain available through the API, and conflict rationales/alternative PDF
citations remain in their disclosures. Existing browser and Node test
assertions were updated; new responsive/source-card geometry and layout
coverage is queued for execution under VR-0140 (design VD-0114 completed). No tests from this new UI batch
were executed during the implementation/design phase.
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

Run this gate against the tracked release artifact, and repeat it against
the final frozen release candidate. It never rebuilds the artifact. The
normal `build-rules` export now produces a v10 candidate at ignored
`local/rules-standalone.db`; the obsolete `--legacy-v8`/`--legacy-v9` CLI modes
are retired. Low-level semantic fixtures are not release build modes.
All CLI builds reject direct writes to
the tracked rules database. The prepared 1.0.1 tracked release uses v10;
its schema-specific publication contract is in
[the data-model contract](data-model.md#restriction-persistence-and-version-aware-api-v9-locally-promoted).
Normal development checks skip this release-only gate:

```powershell
$env:INFINITYDB_RELEASE_FAQ_PARITY = "1"
try {
    .venv\Scripts\python.exe -m pytest tests/test_faq_ruling_references.py::test_tracked_faq_database_matches_current_curated_release_projection -q
} finally {
    Remove-Item Env:INFINITYDB_RELEASE_FAQ_PARITY -ErrorAction SilentlyContinue
}
```

**Verify dependent publications before testing the release pair.**
Current v10 Rules embed deployed objects. Verify the matched four-file
runtime set with `tools.build_v10_runtime_candidate --check` and
`tools.verify_deployment_assets`, following the
[release checklist](releasing.md#4-run-local-release-validation).
Historical v8/v9 releases used a separate deployed-object JSON fingerprint;
their builder/reader and promotion commands are retired. Use their retained
release artifacts for historical inspection. Current startup never enables
an object catalog from adjacent legacy JSON.

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
