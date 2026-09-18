# Development checks

InfinityDB provides `tools/run_checks.py` as the standard local entry point for
Python tests, Ruff linting, Army data-build validation, and curated
rules-database validation. The runner only
orchestrates the existing authoritative tools; it does not replace pytest,
Ruff, or `infinity-db build`.

Run it with the project virtual-environment Python:

```powershell
# Code checks: pytest followed by Ruff
python tools/run_checks.py --profile code

# Data/build validation (`infinity.db`, `infinity.raw.db`, and `rules.db`)
python tools/run_checks.py --profile data

# Tests, lint, Army data build, and rules database build
python tools/run_checks.py --all
```

The available stages are `test`, `lint`, `build`, and `rules`. The `build`
stage builds `infinity.db` and `infinity.raw.db`; the `rules` stage builds
`rules.db` from the tracked curated rules collections. The named profiles are
`code` (`test` + `lint`), `data` (`build` + `rules`), and `all`.


## Graphical asset test modes

The test stage has an explicit policy for the ignored Corvus Belli graphical
asset tree:

```powershell
# Hermetic tests only; suitable for clean/public CI
python tools/run_checks.py --stage test --assets off

# Local default: use full-asset tests when a complete valid set exists
python tools/run_checks.py --stage test --assets auto

# Require the complete valid published asset set
python tools/run_checks.py --stage test --assets required
```

`run_checks.py` defaults to `--assets auto`. With no third-party SVG tree,
`auto` falls back to the hermetic suite. If any published third-party SVGs are
present, `auto` requires the set to be complete and valid rather than silently
ignoring a partial/corrupt installation. `required` always requires the complete
set. The report header records the requested/effective asset mode.

Completeness is checked against the current tracked publication contract:
every army SVG referenced by `army-symbols.js`, every unit SVG referenced by
`unit-symbol-map.js`, and every current order/characteristic symbol endpoint must
exist and parse as SVG. Extra local files do not make an otherwise valid set
incomplete.

Asset-dependent tests carry the `full_assets` pytest marker. Direct pytest runs
exclude that marker by default, so a clean checkout is green:

```powershell
python -m pytest -q
```

Use `python -m pytest -m full_assets -q` only when debugging those integration
tests directly. Normal development/handoff runs should prefer `run_checks.py`
because it validates the asset set before enabling them. Hermetic web tests use
project-owned temporary SVG fixtures to retain coverage of dynamic SVG serving
without redistributing third-party artwork.

## Targeted checks

Positional targets are forwarded to pytest and Ruff. They are deliberately not
interpreted as source-file-to-test mappings.

```powershell
python tools/run_checks.py --stage test tests/test_availability.py
python tools/run_checks.py --stage lint src/infinity_army_data/availability.py tests/test_availability.py
```

When no target is supplied, pytest runs the full suite and Ruff uses the
repository defaults defined by the runner. The build and rules stages ignore
positional targets; use `--build-source PATH` to select an Army source directory
or ZIP for the Army build. The rules stage
always uses the normal curated-rules defaults.

```powershell
python tools/run_checks.py --stage build --build-source "data/raw/JSON 20260910-204106.zip"
python tools/run_checks.py --stage rules
```

By default, requested stages continue after a failed stage so one run can show
the complete repository state. Use `--fail-fast` when stopping at the first
failure is more useful.

## Deployment smoke test

Docker deployment validation is intentionally separate from `run_checks.py`
because it requires a Docker daemon. The GitHub Actions `Deployment smoke test`
workflow builds the real application databases from a small synthetic Army
fixture plus the tracked curated rules collection, builds the Docker image, and
uses `scripts/verify-container-image.sh` to validate image contents and healthy
production startup. Redistributable-image validation also rejects locally
acquired Corvus Belli graphical-asset trees.

See [the Linux deployment guide](deployment.md#deployment-smoke-validation) for
the exact container contract and the equivalent manual command.

## Continuous integration

The `Source checks` GitHub Actions workflow runs the normal check runner on
clean Windows, Ubuntu/Linux, and macOS Python 3.11 checkouts on pull requests and
pushes to `main`, plus a Linux Python 3.14 compatibility leg:

```text
python tools/run_checks.py --all --assets off \
  --build-source tests/fixtures/deployment-smoke
```

The synthetic deployment fixture is the explicit Army build input because clean
source checkouts intentionally contain no real raw Army snapshot. This workflow
is hermetic: it does not acquire network data and does not require ignored
Corvus Belli graphical assets.

The separate `Installed wheel smoke` workflow also builds a real wheel, installs
it into a fresh virtual environment, and exercises installed build CLIs plus
runtime startup from outside the source checkout.

`Full-asset checks` is a manual-only workflow for the complete ignored symbol
set. It runs only from `main`, uses the `full-assets` GitHub environment, stages a
private checksum-pinned ZIP whose root contains only `armies/`, `orders/`, and
`units/` SVG trees, and then invokes the same project runner with
`--assets required`. Configure `FULL_ASSET_BUNDLE_URL` and
`FULL_ASSET_BUNDLE_SHA256` as environment secrets. The workflow does not upload
the graphical tree as an artifact. See
[the continuous integration strategy](ci.md) for the security and redistribution
boundary.

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

Direct pytest or Ruff commands remain useful when debugging one tool in
isolation, but normal development and handoff checks should prefer this runner
so the command set and reporting format stay consistent.
