# Continuous integration strategy

This document records the InfinityDB continuous-integration and automated
validation contract. Sections explicitly marked design direction remain planned;
the deployment smoke, required Linux source workflow, and local asset-test policy are
current behavior.

The goal is to make a clean checkout independently trustworthy while still
supporting deeper validation against a complete local Corvus Belli graphical
asset set when one is legitimately available.

## Principles

1. **Hermetic validation is the default.** Required push/pull-request checks must
   not depend on Corvus Belli network availability, ignored local graphical
   assets, or developer-machine state.
2. **Full-asset validation remains supported.** Tests that genuinely exercise
   the acquired/published symbol set are valuable, but they form an explicit
   integration mode rather than a prerequisite for ordinary source validation.
3. **Acquisition is not routine CI.** Army, wiki, and symbol network refreshes
   remain explicit operations. Ordinary CI consumes tracked fixtures and other
   repository-owned inputs.
4. **Installed artifacts are tested as installed artifacts.** A source checkout
   can hide packaging/resource-path defects. Wheel and container validation must
   run in clean environments that do not rely on the repository layout.
5. **Platform behavior is part of correctness.** Maintained Python tooling should
   be exercised on Windows, Ubuntu/Linux, and macOS where practical, especially
   filesystem/path-sensitive tooling.
6. **Third-party graphical assets are not CI artifacts.** Public workflows must
   not upload acquired Corvus Belli SVG trees or derived copies merely to make
   testing convenient.

## Validation layers

### Required source CI (current)

The `Source checks` GitHub Actions workflow runs on pull requests, pushes to
`main`, and manual dispatch. It starts from a clean Ubuntu checkout with
third-party graphical assets absent and delegates the validation contract to
`tools/run_checks.py` rather than duplicating the individual test/build commands
in workflow YAML:

```text
python tools/run_checks.py --all --assets off \
  --build-source tests/fixtures/deployment-smoke
```

The tracked synthetic Army fixture supplies the explicit clean-checkout input
for the Army build stage; ordinary source archives intentionally do not contain a
real `data/raw/` snapshot. The workflow currently covers:

- pytest hermetic tests;
- Ruff through the normal runner lint stage;
- `infinity.db` / `infinity.raw.db` construction from the controlled fixture;
- `rules.db` construction from tracked curated rules data.

Snapshot-note validation and broader maintained-tool coverage join this same
runner when their backlog items are implemented. A clean source archive is
expected to be genuinely green; absent ignored graphical assets are not a
known-failing state.

The workflow defines InfinityDB's required source-validation contract, but GitHub
merge blocking is a repository rules/branch-protection setting rather than a YAML
property. Enabling that repository-side enforcement remains an administrative
step when protected-branch policy is desired.

### Cross-platform CI

A hermetic matrix should exercise the maintained source checks on:

- Windows;
- Ubuntu/Linux;
- macOS.

Python 3.11 remains the minimum supported version and should be represented on
all three platforms. Additional current Python versions may be checked on Linux
without unnecessarily multiplying the full operating-system matrix.

The matrix is intended to expose real portability differences such as path
case handling, path separators, line endings, subprocess behavior, and Windows
`spawn` semantics. External-tool tests may remain conditional where the
required executable is intentionally optional.

### Installed-package smoke

A separate clean-environment job should build the project wheel, install that
wheel, and exercise the supported installed-package surface without relying on
repository-relative files that were not packaged deliberately.

At minimum this layer should verify:

- imports required by the deployed application;
- application startup against generated test databases;
- installed CLI commands that InfinityDB intends to support;
- packaged configuration/resources required by those supported commands.

Build-time configuration and runtime query code should remain separated where
runtime behavior does not require the former. If an installed CLI intentionally
supports ingestion/build operations, its maintained configuration must be
packaged through an explicit resource contract rather than found by walking back
into a source checkout.

### Deployment smoke (current)

The existing `Deployment smoke test` remains a distinct Linux/container layer.
It builds synthetic `infinity.db` and tracked `rules.db`, builds the
redistributable image, validates exact runtime database contents, starts the
application under its production restrictions, and exercises representative API
behavior.

Read-only runtime imports are deliberately separated from build-time Army
normalization and weapon-policy configuration. The installed application may
therefore open and validate already-built databases without repository-relative
`config/` files. Installed build/ingestion CLI resource packaging remains a
separate planned contract for the installed-wheel smoke layer.

This layer verifies deployment packaging; it is not a substitute for general
source CI or installed-wheel validation.

### Full-asset integration mode (current local behavior)

`tools/run_checks.py` has an explicit asset policy with three modes:

```text
--assets off
--assets auto
--assets required
```

The implemented local semantics are:

| Mode | Behavior |
| --- | --- |
| `off` | Do not use third-party graphical assets. Run the hermetic suite only. This is the default for required CI. |
| `auto` | Use full-asset tests when a validated complete asset set is available. With no asset set, run hermetically. A detected partial/corrupt asset set is an error rather than a reason to silently downgrade. |
| `required` | Require a validated complete asset set and run full-asset integration tests. Missing, partial, or invalid assets fail the check run. |

A "complete asset set" is established by the current tracked browser
publication/mapping contract, not inferred from the presence of a few SVG files.
The validator requires every mapped army/unit SVG plus every current
order/characteristic symbol endpoint to exist and parse as SVG. The exact
validator may evolve with the symbol publisher, but the caller-visible semantics
above should remain stable.

Asset-dependent pytest coverage is marked `full_assets` and separated from the
hermetic suite. Direct pytest excludes `full_assets` by default. Hermetic web
coverage uses project-owned temporary SVG fixtures for dynamic static serving,
and version-display assertions consume the controlled application display
version rather than relying on incidental `.git` state.

A GitHub Actions full-asset run should be optional/manual rather than a required
public PR check. Acceptable execution models include a suitably configured
self-hosted runner or an explicit authorized acquisition step. The workflow may
publish ordinary logs/test reports, but must not upload the acquired graphical
asset tree as a GitHub Actions artifact.

## Network and scheduled workflows

External-source acquisition checks may be useful as manual or scheduled
workflows, but they must remain informational/explicit unless a future decision
changes that contract. A temporary Corvus Belli outage or source-host behavior
must not make an otherwise valid source commit fail required CI.

The same principle applies to expensive performance/capacity work: scheduled or
manual workflows may establish baselines without turning every commit into a
networked or long-running benchmark.

## Planned implementation order

The deployment-smoke runtime import boundary, local hermetic/full-asset test
split, and clean-checkout Linux source workflow are implemented. Remaining CI
work should proceed in this order:

1. Add installed-wheel/package smoke validation so source-checkout assumptions
   cannot hide missing packaged resources, including configuration intentionally
   required by supported installed build/ingestion CLI commands.
2. Expand the hermetic source checks to Windows and macOS.
3. Add optional/manual full-asset integration validation without redistributing
   third-party graphical assets.
4. Add scheduled/manual acquisition, performance, or other extended workflows
   only where they provide useful independent signals.

Symbol-pipeline feature work can then continue with these validation layers in
place, so later deduplication/conversion/publication changes receive automatic
clean-environment and cross-platform coverage.
