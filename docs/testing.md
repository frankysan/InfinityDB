# Development checks

**Project domain:** Project infrastructure

`tools/run_checks.py` is the canonical local validation entry point. It keeps pytest, Ruff,
Pyright, Army database-build validation, rules-database validation, asset policy, worker selection,
and optional reporting under one command contract.

Use the project virtual-environment interpreter when available:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py --profile code
```

On Linux/macOS use `.venv/bin/python` instead.

## Profiles and stages

The runner exposes five stages:

- `test` — pytest;
- `lint` — Ruff;
- `type` — Pyright;
- `build` — Army data/database build validation;
- `rules` — curated rules validation/database build.

Named profiles are:

```powershell
# pytest + Ruff + Pyright
python tools\run_checks.py --profile code

# Army build + rules build
python tools\run_checks.py --profile data

# all stages
python tools\run_checks.py --all
```

`--profile all` is equivalent to `--all`.

Requested stages continue after a failure by default so one run can report the complete failure set.
Use `--fail-fast` when the first failure is sufficient.

## Targeted checks

For ordinary development, prefer the smallest check that exercises the changed contract before
running broader validation:

```powershell
python tools\run_checks.py --stage test tests/test_availability.py
python tools\run_checks.py --stage test tests/test_web.py -k fireteam
python tools\run_checks.py --stage lint src/infinity_db/web tests/test_web.py
python tools\run_checks.py --stage type
```

Positional targets are passed to pytest/Ruff for their respective stages. Build/rules stages ignore
those targets.

Direct tool commands remain appropriate when debugging the tool itself:

```powershell
python -m pytest tests\test_specific.py -q
python -m ruff check path\to\file.py
python -m pyright
```

Do not report Ruff/Pyright as run when those tools are unavailable in the active environment.

## Theme runtime regression coverage

The web test suite executes the checked-in theme startup and preference modules in a minimal Node.js
runtime harness. This pins pre-paint System/Light/Dark resolution, session-versus-cookie precedence,
explicit switching, normalization, and remembered-setting behavior without introducing a browser or
JavaScript build dependency. The development dependency set already provides Node.js through
`pyright[nodejs]`; the test also accepts a normal `node` executable when one is already available.
Representative server-rendered pages separately verify that the shared pre-paint bootstrap and
semantic theme stylesheet are present in the correct order.

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

Hosted Windows CI intentionally uses serial pytest because automatic xdist scheduling was unstable
for that runner class; this does not change the normal local default. See `docs/ci.md`.

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

Available tools include:

```powershell
python tools\benchmark_runtime.py --help
python tools\compare_runtime_benchmarks.py --help
python tools\benchmark_test_workers.py --help
```

Use runtime benchmarks for repository/query performance and the worker benchmark for deciding whether
a different local pytest worker setting is warranted. Generated benchmark reports belong in ignored
report/audit storage unless a specific result is needed as release evidence.

## CI and release validation

`docs/ci.md` owns the hosted workflow contract. `docs/releasing.md` owns the release gate. Do not
copy required-check names, branch-protection settings, or release acceptance steps into this file
unless they directly affect how local checks are invoked.
