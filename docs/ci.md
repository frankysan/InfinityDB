# Continuous integration strategy

This document records the InfinityDB continuous-integration and automated
validation contract. Sections explicitly marked design direction remain planned;
the deployment smoke, required cross-platform source workflow, installed-wheel
smoke, local asset-test policy, and dispatch-only full-asset workflow are current
behavior.

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
`main`, and manual dispatch. Its matrix covers clean Windows, Ubuntu/Linux, and
macOS runners at Python 3.11, plus Linux at Python 3.14. Third-party graphical
assets are absent, and each leg delegates the validation contract to
`tools/run_checks.py` rather than duplicating the individual test/build commands
in workflow YAML:

```text
python tools/run_checks.py --all --assets off \
  --build-source tests/fixtures/deployment-smoke
```

The tracked synthetic Army fixture supplies the explicit clean-checkout input
for the Army build stage; ordinary source archives intentionally do not contain a
real `data/raw/` snapshot. Every matrix leg installs `.[dev,symbols]` and covers:

- pytest hermetic tests, including synthetic integration against the real
  fontTools, tinycss2/cssselect2, and Pillow Python dependencies;
- Ruff across the maintained `src/`, `tests/`, and complete `tools/` trees;
- Pyright type checking across maintained `src/` and `tools/` code;
- `infinity.db` / `infinity.raw.db` construction from the controlled fixture;
- `rules.db` construction from tracked curated rules data.

Snapshot-note validation and focused regression coverage for the remaining
standalone tools join this same runner when their backlog items are implemented.
A clean source archive is expected to be genuinely green; absent ignored
graphical assets are not a
known-failing state.

The workflow defines InfinityDB's required source-validation contract, but GitHub
merge blocking is a repository rules/branch-protection setting rather than a YAML
property. Enabling that repository-side enforcement remains an administrative
step when protected-branch policy is desired.

### Cross-platform CI (current)

The hermetic source-check matrix exercises the maintained source checks on:

- Windows at Python 3.11;
- Ubuntu/Linux at Python 3.11 and Python 3.14;
- macOS at Python 3.11.

Python 3.11 remains the minimum supported version and is represented on all three
platforms. The additional Linux Python 3.14 leg adds newer-interpreter coverage
without multiplying the full operating-system matrix.

The matrix is intended to expose real portability differences such as path
case handling, path separators, line endings, subprocess behavior, and Windows
`spawn` semantics. External-tool tests may remain conditional where the
required executable is intentionally optional.

### Installed-package smoke (current)

The `Installed wheel smoke` GitHub Actions workflow builds the project wheel,
installs it into a fresh virtual environment, stages only controlled Army/rules
fixtures outside the checkout, and exercises the supported installed-package
surface from that clean working directory.

The job verifies:

- installed `infinity-db` and `infinity-army` console entry points;
- `infinity-db build` and standalone `infinity-army build`;
- curated-rules validation and `rules.db` construction;
- runtime `Database`, `RulesDatabase`, and application startup against the
  generated test databases;
- installed maintained identity, weapon-catalog, and source-anomaly
  configuration.

The tracked authored configuration remains under repository `config/`. Wheel
packaging installs the build/ingestion subset under
`<sys.prefix>/share/infinity-db/config/`; loaders prefer the tracked source
layout when present and otherwise resolve that installed shared-data contract.
This avoids duplicating authored configuration inside Python packages while
keeping installed build commands independent of a source checkout.

Build-time configuration and runtime query code remain separated: opening an
already-built database does not load Army normalization policy, while installed
build/ingestion commands intentionally consume the packaged maintained data.

### Deployment smoke (current)

The existing `Deployment smoke test` remains a distinct Linux/container layer.
It builds synthetic `infinity.db` and tracked `rules.db`, builds the
redistributable image, validates exact runtime database contents, starts the
application under its production restrictions, and exercises representative API
behavior.

Read-only runtime imports are deliberately separated from build-time Army
normalization and weapon-policy configuration. The installed application may
therefore open and validate already-built databases without repository-relative
`config/` files. Installed build/ingestion CLI resource packaging is validated
separately by the installed-wheel smoke layer.

This layer verifies deployment packaging; it is not a substitute for general
source CI or installed-wheel validation.

### Full-asset integration mode (current local and manual CI behavior)

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

A "complete asset set" is established by the generated publication inventory,
not by the smaller set currently referenced by the browser and not by the mere
presence of SVG files. Final symbol publication writes `symbol-inventory.json`
with every published SVG path and SHA-256. The validator requires that complete
inventory to be present, parseable, hash-correct, and free of unexpected SVGs.
It then independently derives the browser-referenced subset from
`army-symbols.js`, `unit-symbol-map.js`, and the current order/characteristic
endpoints and verifies that subset is contained in the publication. Published
variants that are not yet browser-referenced remain valid and required parts of
the full asset set.

Asset-dependent pytest coverage is marked `full_assets` and separated from the
hermetic suite. Direct pytest excludes `full_assets` by default. Hermetic web
coverage uses project-owned temporary SVG fixtures for dynamic static serving,
and version-display assertions consume the controlled application display
version rather than relying on incidental `.git` state.

The dispatch-only `Full-asset checks` workflow implements the optional GitHub
layer on a GitHub-hosted Ubuntu/Python 3.11 runner. It is restricted to the
`main` ref and uses the `full-assets` GitHub environment so access to the private
bundle can be controlled independently from ordinary source CI. That environment
provides `FULL_ASSET_BUNDLE_URL` and `FULL_ASSET_BUNDLE_SHA256` secrets. The
URL must resolve over HTTPS, and the configured digest pins the exact bundle used
by the run.

`tools/stage_full_asset_bundle.py` downloads the bundle without printing its
URL, enforces download/expanded-size limits, rejects path traversal, symlinks,
encrypted members, case-colliding names, and files outside the
`armies/`, `characteristics/`, `orders/`, and `units/` SVG trees plus the exact
root `symbol-inventory.json`, then validates the complete publication inventory
and the browser-referenced subset before replacing the ignored local asset
directories/inventory. The private bundle therefore carries the same generated
publication inventory as the local published tree. The workflow then runs:

```text
python tools/run_checks.py --all --assets required \
  --build-source tests/fixtures/deployment-smoke
```

The bundle is deliberately supplied privately rather than reconstructed by CI.
InfinityDB now has an authoritative publisher, but required/manual full-asset CI
still avoids rerunning the network/external-tool-sensitive symbol acquisition and
processing pipeline; it validates the already-published contract instead. The
workflow has no push or pull-request trigger and does not upload the bundle or
staged graphical tree as a GitHub Actions artifact. The environment secrets
therefore remain an explicit repository-administration prerequisite before a
manual run can succeed.

## Network and scheduled workflows

External-source acquisition checks may be useful as manual or scheduled
workflows, but they must remain informational/explicit unless a future decision
changes that contract. A temporary Corvus Belli outage or source-host behavior
must not make an otherwise valid source commit fail required CI.

The same principle applies to expensive performance/capacity work: scheduled or
manual workflows may establish baselines without turning every commit into a
networked or long-running benchmark.

## Remaining follow-up work

The deployment-smoke runtime import boundary, local hermetic/full-asset test
split, cross-platform source workflow, installed-wheel smoke, and dispatch-only
full-asset workflow are implemented. These core validation layers are sufficient
for symbol-pipeline feature work to continue with automatic clean-environment and
cross-platform coverage.

Non-blocking CI follow-up remains in the backlog: add focused regression coverage
for still-under-tested standalone tools, validate checked-in snapshot notes routinely, configure
repository rules/branch protection if required, and configure the `full-assets`
environment with an authorized checksum-pinned bundle plus one successful manual
run. Scheduled/manual acquisition, performance, or other extended workflows
should be added only where they provide a useful independent signal.
