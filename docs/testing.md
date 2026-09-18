# Development checks

InfinityDB provides `tools/run_checks.py` as the standard local entry point for
Python tests, Ruff linting, and Army data-build validation. The runner only
orchestrates the existing authoritative tools; it does not replace pytest,
Ruff, or `infinity-db build`.

Run it with the project virtual-environment Python:

```powershell
# Code checks: pytest followed by Ruff
python tools/run_checks.py --profile code

# Data/build validation
python tools/run_checks.py --profile data

# Tests, lint, and data build
python tools/run_checks.py --all
```

The available stages are `test`, `lint`, and `build`. The named profiles are
`code` (`test` + `lint`), `data` (`build`), and `all`.

## Targeted checks

Positional targets are forwarded to pytest and Ruff. They are deliberately not
interpreted as source-file-to-test mappings.

```powershell
python tools/run_checks.py --stage test tests/test_availability.py
python tools/run_checks.py --stage lint src/infinity_army_data/availability.py tests/test_availability.py
```

When no target is supplied, pytest runs the full suite and Ruff uses the
repository defaults defined by the runner. The build stage ignores positional
targets; use `--build-source PATH` to select an Army source directory or ZIP.

```powershell
python tools/run_checks.py --stage build --build-source "data/raw/JSON 20260910-204106.zip"
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
