# Development checks

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

Completeness is checked against the generated `symbol-inventory.json` written
by final symbol publication. Every inventoried SVG must exist, parse as SVG, and
match its published SHA-256, and unlisted SVGs inside the generated asset
categories are rejected. The validator separately derives the currently
browser-referenced subset from `army-symbols.js`, `unit-symbol-map.js`, and the
order/characteristic endpoints. This distinction is intentional: published
profile/army variants that the browser does not yet consume remain part of the
complete asset set. Check output therefore reports both the full published count
and the browser-referenced count.

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
for every test stage. Benchmarking on the primary Windows development machine
reduced the complete 687-test run from 59.67 seconds serially to 14.13 seconds
with `auto`; four fixed workers took 19.41 seconds.

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

Docker deployment validation is intentionally separate from `run_checks.py`
because it requires a Docker daemon. The configured GitHub Actions `Deployment smoke test`
workflow builds the real application databases from a small synthetic Army
fixture plus the tracked curated rules collection, builds the Docker image, and
uses `scripts/verify-container-image.sh` to validate image contents and healthy
production startup. The smoke workflow uses `--packaged-assets` to verify that the tracked processed
SVG publication survives Docker/package installation with exact inventory hashes and
working live symbol routes. Local production deployment uses `--published-assets`,
which performs the same package checks after `tools/verify_deployment_assets.py` has
bound the host publication to terminal symbol-build manifest state and additionally
revalidates that database/publication provenance before Compose activation.
The workflow stages its fixture databases and Docker context under the runner
temporary directory; it never writes fixture data into checkout deployment paths.

See [the Linux deployment guide](deployment.md#deployment-smoke-validation) for
the exact container contract and the equivalent manual command.

## Continuous integration

The `Source checks` GitHub Actions workflow runs the check runner on clean
Windows, Ubuntu/Linux, and macOS Python 3.11 checkouts on pull requests, pushes
to `main`, and manual dispatch, plus a Linux Python 3.14 compatibility leg. The
Ubuntu/Python 3.11 leg owns the complete source gate (`--all`); the compatibility
legs run pytest plus both database-build stages. This avoids repeating Ruff and
Pyright on every operating system while preserving cross-platform runtime/build
coverage.

Hosted Windows Actions explicitly uses `--test-workers 0`. Parallel pytest is
still the local default, but `auto` regressed severely on the hosted Windows
runner while the serial suite remained stable. Linux and macOS CI continue to
use automatic xdist worker selection.

Each source-check leg installs both the development and symbol Python dependency
sets. This keeps the real fontTools/tinycss2/cssselect2/Pillow integration
fixtures in required CI without requiring external renderers or third-party
artwork. Ruff and Pyright run on the primary Ubuntu/Python 3.11 leg.

The synthetic deployment fixture is the explicit Army build input because clean
source checkouts intentionally contain no real raw Army snapshot. This workflow
is network-hermetic: it does not acquire live data and validates the tracked processed
Corvus Belli graphical publication directly from the checkout.

For Python 3.11, each operating-system leg also builds a deterministic-output manifest.
The manifest hashes representative Army and rules databases, normalized JSON/report
outputs, a metadata-normalized snapshot archive, the work-archive export, and the
checksum-bound publication metadata. A final Ubuntu job downloads the Windows/Linux/
macOS manifests and fails if any artifact SHA-256 differs. This is the maintained
byte-level portability gate; ordinary semantic equality is not sufficient.

The separate configured `Installed wheel smoke` workflow builds a real wheel, installs
it into a fresh virtual environment, and exercises installed build CLIs plus
runtime startup from outside the source checkout.

The processed SVG publication is tracked in the repository, so normal source CI now
runs with `--assets required`. This validates the publication inventory and includes
the `full_assets` pytest coverage directly from a clean checkout. The dispatch-only
`Full-asset checks` workflow remains available as an independent validation of a
checksum-pinned external publication bundle. It is restricted to `main`, uses the
`full-assets` GitHub environment, stages the configured bundle through
`tools/stage_full_asset_bundle.py`, and then runs the same required-asset project gate.
Configure `FULL_ASSET_BUNDLE_URL` and `FULL_ASSET_BUNDLE_SHA256` before using that
supplementary workflow.

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
