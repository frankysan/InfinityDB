# Continuous integration strategy

This document records the accepted design direction for InfinityDB continuous
integration and automated validation. Unless a section is explicitly marked
current, the workflows and command-line options described here are planned and
must not be treated as implemented behavior.

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

### Required source CI

The normal push/pull-request workflow should run from a clean checkout with
third-party graphical assets absent. Its authoritative command surface should be
`tools/run_checks.py`, extended as needed rather than duplicating project-check
logic in workflow YAML.

The required source layer should cover:

- pytest hermetic tests;
- Ruff over all maintained Python packages and tools;
- `infinity.db` / `infinity.raw.db` construction from controlled fixture or
  pinned test input;
- `rules.db` construction from tracked curated rules data;
- curated snapshot-note/schema validation once integrated into the normal check
  runner;
- maintained standalone-tool regression coverage that does not require external
  proprietary assets or live network acquisition.

A clean source archive should be genuinely green. Missing ignored graphical
assets must not be represented as a known-failing normal test state.

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
It should continue to build synthetic `infinity.db` and tracked `rules.db`, build
the redistributable image, validate exact runtime database contents, start the
application under its production restrictions, and exercise representative API
behavior.

This layer verifies deployment packaging; it is not a substitute for general
source CI or installed-wheel validation.

### Full-asset integration mode

`tools/run_checks.py` should gain an explicit asset policy with three modes:

```text
--assets off
--assets auto
--assets required
```

The intended semantics are:

| Mode | Behavior |
| --- | --- |
| `off` | Do not use third-party graphical assets. Run the hermetic suite only. This is the default for required CI. |
| `auto` | Use full-asset tests when a validated complete asset set is available. With no asset set, run hermetically. A detected partial/corrupt asset set is an error rather than a reason to silently downgrade. |
| `required` | Require a validated complete asset set and run full-asset integration tests. Missing, partial, or invalid assets fail the check run. |

A "complete asset set" must be established by the current symbol
publication/mapping contract, not inferred from the presence of a few SVG files.
The exact validator may evolve with the symbol pipeline, but the caller-visible
semantics above should remain stable.

Asset-dependent pytest coverage should be explicitly marked (for example,
`full_assets`) and separated from hermetic tests. Hermetic tests should use
project-owned fixtures or injected temporary static roots to cover missing and
present-asset behavior without requiring Corvus Belli artwork.

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

1. Repair the current deployment-smoke packaging/runtime failure so the existing
   workflow returns to a trustworthy baseline.
2. Make asset-dependent tests hermetic and introduce explicit `off` / `auto` /
   `required` asset modes in `run_checks.py`.
3. Add required Linux source CI around the normal check runner.
4. Add installed-wheel/package smoke validation so source-checkout assumptions
   cannot hide missing packaged resources.
5. Expand the hermetic source checks to Windows and macOS.
6. Add optional/manual full-asset integration validation without redistributing
   third-party graphical assets.
7. Add scheduled/manual acquisition, performance, or other extended workflows
   only where they provide useful independent signals.

Symbol-pipeline feature work can then continue with these validation layers in
place, so later deduplication/conversion/publication changes receive automatic
clean-environment and cross-platform coverage.
