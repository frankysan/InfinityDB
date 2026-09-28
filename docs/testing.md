# Development checks

**Project domain:** Project infrastructure

InfinityDB provides `tools/run_checks.py` as the standard local entry point for
Python tests, Ruff linting, Pyright type checking, Army data-build validation,
and curated rules-database validation. The runner only
orchestrates the existing authoritative tools; it does not replace pytest,
Ruff, or `infinity-db build`.

Run it with the project virtual-environment Python:

```powershell
# Code checks: pytest, Ruff, then Pyright
python tools/run_checks.py --profile code

# Data/build validation (`infinity.db`, `infinity.raw.db`, and `rules.db`)
python tools/run_checks.py --profile data

# Tests, lint, type checking, Army data build, and rules database build
python tools/run_checks.py --all
```

The available stages are `test`, `lint`, `type`, `build`, and `rules`. The `type`
stage runs Pyright over the maintained `src/`, `tools/`, and `tests/` trees. The
`build` stage builds `infinity.db` and `infinity.raw.db`; the `rules` stage builds
`rules.db` from the tracked curated rules collections. Both use isolated system
temporary output directories: check execution never writes `data/generated/`.
The named profiles are
`code` (`test` + `lint` + `type`), `data` (`build` + `rules`), and `all`.

## Graphical asset test modes

The test stage has an explicit policy for the tracked Corvus Belli graphical
publication. The validated processed publication is release content under Corvus
Belli's explicit non-commercial permission; raw acquisition archives remain excluded
from Git:

```powershell
# Hermetic tests only; explicitly skip asset-dependent integration coverage
python tools/run_checks.py --stage test --assets off

# Local default: use full-asset tests when a complete valid set exists
python tools/run_checks.py --stage test --assets auto

# Require the complete valid published asset set
python tools/run_checks.py --stage test --assets required
```

`run_checks.py` defaults to `--assets auto`. In a normal source checkout the tracked
publication is present, so `auto` resolves to full-asset validation. In a specialized
package/test layout with no third-party SVG tree, `auto` falls back to the hermetic
suite. If any published third-party SVGs are present, `auto` requires the set to be
complete and valid rather than silently ignoring a partial/corrupt installation.
`required` always requires the complete set. The report header records the
requested/effective asset mode.

Completeness is checked against the tracked
`data/manifests/symbol-publication.json` written by final symbol publication.
Every published SVG named by that manifest must exist, parse as SVG, and match
its SHA-256, and unlisted SVGs inside the generated asset categories are
rejected. The same manifest also defines the currently browser-referenced
subset through its Army, Unit/profile, and static mappings. This distinction is
intentional even though the current processed publication is
fully browser-addressable (806/806 SVGs): future preserved variants must remain
part of the complete asset set rather than weakening validation. Check output
therefore reports both the full published count and the browser-referenced count.

Asset-dependent tests carry the `full_assets` pytest marker. Direct pytest runs
exclude that marker by default, so a clean checkout is green:

```powershell
python -m pytest -q
```

Use `python -m pytest -m full_assets -q` only when debugging those integration
tests directly. Normal development/handoff runs should prefer `run_checks.py`
because it validates the asset set before enabling them. Hermetic web tests use
project-owned temporary SVG fixtures to retain coverage of dynamic SVG serving
without depending on the complete processed graphical publication.

## Parallel pytest execution

The check runner uses `pytest-xdist` with automatic worker selection by default
for every test stage. In the recorded parallelization benchmark on the primary Windows development machine,
the then-current 687-test suite fell from 59.67 seconds serially to 14.13 seconds
with `auto`; four fixed workers took 19.41 seconds. These figures are historical
evidence, not the size or expected duration of the current suite.

```powershell
# Default: let pytest-xdist choose from the available physical CPU cores
python tools/run_checks.py --stage test

# Explicit fixed worker count
python tools/run_checks.py --stage test --test-workers 4

# Explicit serial/debugging mode
python tools/run_checks.py --stage test --test-workers 0
```

Parallel runs use xdist's `worksteal` scheduler so the relatively expensive
database tests can be rebalanced instead of pinning an entire large test module
to one worker. `pytest-xdist` is part of the `dev` dependency set. Serial mode
remains available for debugging ordering, isolation, or concurrency-sensitive
failures.

The web tests build one template SQLite database per module, then copy that
template into each test's temporary directory before creating the application.
This preserves mutation isolation while avoiding a full normalize/export cycle
for every web test.

Rules-backed Skill and State catalogs cache their composed current records for the
lifetime of each catalog instance. The underlying runtime rules database is immutable,
so repeated lookups do not need to rerun the same composition queries. Detail surfaces
still copy cached records before returning them, preserving caller mutation isolation.
In the 2026-09-28 serial Linux benchmark, this reduced
`tests/test_audit_enrichment_coverage.py` from 14.57 seconds to 2.54 seconds.
Treat the timing as diagnostic evidence rather than a test threshold.

Read-only rules-database query tests also share one module-scoped build of the unchanged
current curated corpus instead of rebuilding identical SQLite files for every test. Tests
that intentionally mutate or validate export behavior continue to build isolated databases.
In the 2026-09-28 serial Linux benchmark, this reduced `tests/test_rules_database.py`
from 5.14 seconds to 2.27 seconds while retaining all 45 tests. Treat the timing as
diagnostic evidence rather than a test threshold.

### SQLite finalization in semantic tests

The production Army and rules exporters canonicalize generated SQLite artifacts by
default: they repack with `VACUUM` and normalize transaction-history-only header
fields so release artifacts remain byte-deterministic. Export-heavy semantic tests
that inspect database contents rather than final file bytes explicitly use
`finalize=False` to avoid repeating that physical-file work. This optimization is
limited to test callers; the CLI does not expose a non-finalized build mode.

`tests/test_database.py` and `tests/test_rules_database.py` retain a comparison
switch for measuring the finalization cost with the normal xdist scheduler. Set
`INFINITYDB_TEST_FINALIZE_SQLITE=1` to force those fixtures back through canonical
finalization for one run, then compare against the normal test path using the same
machine and worker count:

```powershell
$env:INFINITYDB_TEST_FINALIZE_SQLITE = "1"
python tools/run_checks.py --stage test --test-workers auto tests/test_database.py tests/test_rules_database.py
Remove-Item Env:INFINITYDB_TEST_FINALIZE_SQLITE
python tools/run_checks.py --stage test --test-workers auto tests/test_database.py tests/test_rules_database.py
```

On the primary Windows development machine, the 182-test database/rules comparison
with `--test-workers auto` and xdist `worksteal` measured 19.45 seconds with canonical
finalization forced and 17.56 seconds with the semantic-test fast path: a 1.89-second,
9.7% reduction in check-run wall time. Pytest's own reported duration improved from
19.05 to 17.18 seconds (9.8%). Both runs passed all 182 tests.

Treat these timings as diagnostic evidence, not a pass/fail performance threshold.
Shared CI runners can vary substantially, so future comparisons should record the platform,
worker setting, and both measured durations.

## Targeted checks

Positional targets are forwarded to pytest and Ruff. They are deliberately not
interpreted as source-file-to-test mappings.

```powershell
python tools/run_checks.py --stage test tests/test_availability.py
python tools/run_checks.py --stage lint src/infinity_army_data/availability.py tests/test_availability.py
```

When no target is supplied, pytest runs the full suite and Ruff checks the full
maintained `tools/` tree along with `src/` and `tests/`. The type stage always
uses the project Pyright configuration; positional targets remain specific to
pytest and Ruff. The build and rules stages ignore positional targets; use
`--build-source PATH` to
select an Army source directory
or ZIP for the Army build. The rules stage
always uses the normal curated-rules defaults.

```powershell
python tools/run_checks.py --stage build --build-source "data/raw/JSON 20260918-204434.zip"
python tools/run_checks.py --stage rules
```

By default, requested stages continue after a failed stage so one run can show
the complete repository state. Use `--fail-fast` when stopping at the first
failure is more useful.

## Deployment smoke test

Docker deployment validation is intentionally separate from `run_checks.py` because it
requires a Docker daemon. The configured GitHub Actions `Deployment smoke test` builds the
application image directly from the tracked release `infinity.db`, `rules.db`, processed SVG
publication, and `symbol-publication.json`, then uses `scripts/verify-container-image.sh` in
`--published-assets` mode to validate exact installed assets, database/publication snapshot
provenance, runtime database formats, and healthy production startup. This intentionally tests
the same self-contained artifact model used by tagged production deployment rather than replacing
the committed runtime databases with synthetic fixture outputs.

See [the Linux deployment guide](deployment.md#deployment-smoke-validation) for
the exact container contract and the equivalent manual command.

## Continuous integration

Hosted CI delegates source validation to the same `tools/run_checks.py` runner, but
workflow triggers, platform/interpreter matrices, hosted worker-count exceptions,
installed-wheel/container smoke coverage, required branch checks, and the optional
external full-asset bundle are repository/CI policy rather than local check-runner
semantics. They are maintained canonically in [the CI strategy](ci.md).

When reproducing a hosted failure locally, use the stage, target, worker, and asset
controls documented above. Do not copy hosted workflow policy into this document;
update `docs/ci.md` when the GitHub Actions or branch-protection contract changes.

## Reports

Console output can also be written verbatim to a UTF-8 text report.

```powershell
# Automatically named, repository-local report
python tools/run_checks.py --profile code --report

# Explicit path/name
python tools/run_checks.py --profile code --report reports/custom-check.txt
```

With `--report` and no path, the runner writes to:

```text
reports/CHECKS YYYYMMDD-HHMMSS.txt
```

The filename uses the same local run-start timestamp recorded in the report
header, making the output deterministic for that run. The `reports/` directory
is ignored by Git. Supplying a path explicitly preserves that path instead.

The report header records the run start, current Git branch and commit, selected
stages, and any targets. Each stage records its command, streamed output, result,
and duration, followed by an overall summary.

## Exit codes

- `0`: every requested stage passed.
- `1`: at least one requested check stage failed.
- `2`: runner/configuration error or a stage could not be started.

Direct pytest, Ruff, or Pyright commands remain useful when debugging one tool in
isolation, but normal development and handoff checks should prefer this runner
so the command set and reporting format stay consistent.

## Runtime repository benchmark

The 0.6.1 canonicalization release gate used a local repository-read benchmark
rather than a CI timing threshold. The benchmark remains available for later
before/after work; run it against an already-built production-like Army database:

```powershell
python tools/benchmark_runtime.py data\generated\infinity.db
```

Use `--json` when results need to be archived or compared mechanically. For a
before/after comparison, use the same Army source snapshot, machine, Python
environment, and iteration counts. The command reports cold and warm median/p95
latencies for representative Army, unit, catalog, and Trait read paths plus the
database size. CI does not assert timing because shared-runner variance would make
that evidence misleading.

The **before** benchmark must execute with the pre-change implementation. Do not
open an older-schema database with the current repository merely to obtain a
number: runtime validation intentionally rejects incompatible databases. Build
the same Army snapshot in the pre-change checkout and run the same
`benchmark_runtime.py` script with that checkout's `src` directory first on
`PYTHONPATH`. On PowerShell, one reproducible approach is:

```powershell
$before = (Resolve-Path "..\InfinityDB-before").Path
$env:PYTHONPATH = (Join-Path $before "src")
python .\tools\benchmark_runtime.py (Join-Path $before "data\benchmark-before\infinity.db") --json > .\reports\BENCHMARK-before.json
Remove-Item Env:PYTHONPATH
```

Generate the after report normally from the current checkout, then compare the
two reports:

```powershell
python tools\benchmark_runtime.py data\generated\infinity.db --json > reports\BENCHMARK-after.json
python tools\compare_runtime_benchmarks.py reports\BENCHMARK-before.json reports\BENCHMARK-after.json
python tools\compare_runtime_benchmarks.py reports\BENCHMARK-before.json reports\BENCHMARK-after.json --json > reports\BENCHMARK-comparison.json
```

The comparison requires the same case set and cold/warm iteration counts. It
reports database-size change and per-case median/p95 percentage deltas; negative
timing deltas are faster and positive deltas are slower. It deliberately does
not impose a pass/fail performance threshold: release review should interpret
the measured tradeoffs alongside semantic correctness and losslessness.
