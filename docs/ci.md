# Continuous integration strategy

This document records the InfinityDB continuous-integration and automated
validation contract. Sections explicitly marked design direction remain planned;
the deployment smoke, required cross-platform source workflow, installed-wheel
smoke, tracked published-asset policy, and dispatch-only external-bundle full-asset
workflow are current behavior.

The goal is to make a clean checkout independently trustworthy while still
supporting deeper validation against a complete Corvus Belli graphical
publication. Redistribution of that processed publication is explicitly permitted
for InfinityDB's non-commercial scope; CI independence is an engineering choice,
not a licensing requirement.

## Principles

1. **Hermetic validation is the default.** Required push/pull-request checks must
   not depend on Corvus Belli network availability, raw acquisition inputs, or
   developer-machine state.
2. **Published-asset validation is required.** The approved processed SVG publication
   is tracked release content, so ordinary source validation verifies it directly. The
   manual external-bundle workflow remains a supplementary independent validation path.
3. **Acquisition is not routine CI.** Army, wiki, and symbol network refreshes
   remain explicit operations. Ordinary CI consumes tracked fixtures and other
   repository-owned inputs.
4. **Installed artifacts are tested as installed artifacts.** A source checkout
   can hide packaging/resource-path defects. Wheel and container validation must
   run in clean environments that do not rely on the repository layout.
5. **Platform behavior is part of correctness.** Maintained Python tooling should
   be exercised on Windows, Ubuntu/Linux, and macOS where practical, especially
   filesystem/path-sensitive tooling.
6. **Raw third-party acquisition inputs are not routine CI artifacts.** Public
   workflows must not upload Army/wiki/PDF/source-symbol archives merely to make
   testing convenient. Corvus Belli has permitted redistribution of InfinityDB's
   processed graphical publication, which is tracked release content; raw acquisition
   archives remain excluded.

## Validation layers

### Required source CI (configured)

The `Source checks` GitHub Actions workflow is configured to run on pull requests, pushes to
`main`, and manual dispatch. Its matrix covers clean Windows, Ubuntu/Linux, and
macOS runners at Python 3.11, plus Linux at Python 3.14. The tracked processed
graphical publication is present, and every leg delegates validation to
`tools/run_checks.py` with `--assets required`.

The Ubuntu/Python 3.11 leg is the primary source gate and runs `--all`: pytest,
Ruff, Pyright, Army database construction, and curated rules database
construction. The Windows/Python 3.11, macOS/Python 3.11, and Ubuntu/Python 3.14
compatibility legs run pytest plus the Army and rules build stages. This keeps
platform/interpreter-sensitive behavior covered without redundantly repeating
platform-independent lint and type checks four times.

Hosted Windows Actions explicitly passes `--test-workers 0`; parallel pytest
remains the normal local default. Automatic xdist worker selection caused a
severe slowdown on the hosted Windows runner, whereas the serial hosted run was
stable. Linux and macOS CI use automatic worker selection.

The tracked synthetic Army fixture supplies the explicit clean-checkout input
for the Army build stage; ordinary source archives intentionally do not contain a
real `data/raw/` snapshot. Every matrix leg installs `.[dev,symbols]`, so the
pytest coverage also exercises the real fontTools, tinycss2/cssselect2,
and Pillow Python dependencies.

Focused regression coverage for the maintained standalone tools is included in
the source suite. Routine validation of checked-in snapshot notes remains a
follow-up item. A clean source archive is expected to contain and validate the
complete tracked processed SVG publication.

The workflow defines InfinityDB's required source-validation contract, while
merge blocking remains a repository setting rather than a workflow-YAML property.
The repository currently has an active `Protect main` branch ruleset targeting
`main`. It requires pull requests with resolved review threads and an up-to-date
set of required checks: the four `Source checks` matrix jobs, `deployment-smoke`,
and `installed-wheel`. The 0.7.1 deterministic-output job is additionally mandatory
for release acceptance; after its first hosted run establishes the check context, it
must also be added to the `Protect main` required checks. The ruleset blocks branch
deletion and non-fast-forward updates and has no bypass actors. These settings live
on GitHub and therefore cannot be completed by workflow YAML alone.

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

The three Python 3.11 platform legs additionally produce a deterministic-output SHA-256
manifest from the same synthetic inputs. The workflow compares those manifests after
the matrix completes and fails if any representative database, JSON/report artifact,
snapshot/work archive, or checksum-bound publication metadata differs byte-for-byte.
This comparison is a required portability check, not diagnostic-only evidence.

### Installed-package smoke (configured)

The `Installed wheel smoke` GitHub Actions workflow is configured to build the project wheel,
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

### Deployment smoke (configured)

The configured `Deployment smoke test` is a distinct Linux/container layer.
It builds synthetic `infinity.db` and tracked `rules.db`, builds the application
image with the tracked processed SVG publication, validates exact runtime database
contents and packaged assets, starts the
application under its production restrictions, and exercises representative API
behavior.

Read-only runtime imports are deliberately separated from build-time Army
normalization and weapon-policy configuration. The installed application may
therefore open and validate already-built databases without repository-relative
`config/` files. Installed build/ingestion CLI resource packaging is validated
separately by the installed-wheel smoke layer.

This layer verifies deployment packaging; it is not a substitute for general
source CI or installed-wheel validation.

### Tracked published-asset integration and external-bundle validation

`tools/run_checks.py` retains the explicit asset policy with three modes:

```text
--assets off
--assets auto
--assets required
```

The implemented local semantics are:

- `off`: skip publication validation and `full_assets` pytest coverage.
- `auto`: use full-asset coverage when a validated complete asset set is available;
  a detected partial/corrupt set is an error rather than a silent downgrade.
- `required`: require a validated complete asset set and include `full_assets`
  integration coverage.

The complete processed SVG publication and `symbol-inventory.json` are tracked release
content, so required source CI now uses `--assets required` directly from a clean
checkout. A complete asset set is established by the generated publication inventory,
not merely by the presence of SVG files. The validator checks every published path and
SHA-256, rejects unexpected SVGs, and independently verifies that the browser-referenced
subset is contained in the publication. Published variants that are not yet
browser-referenced remain valid and required parts of the complete publication.

Asset-dependent pytest coverage remains marked `full_assets`; direct pytest excludes it
by default, while the project runner includes it in `required` mode. Network/external-tool
symbol acquisition remains outside required CI: CI validates the approved processed
publication rather than reconstructing it from raw source inputs.

The dispatch-only `Full-asset checks` workflow is retained as a supplementary,
independent validation path. It is restricted to `main` and uses the `full-assets`
GitHub environment. `FULL_ASSET_BUNDLE_URL` and `FULL_ASSET_BUNDLE_SHA256` identify a
checksum-pinned HTTPS ZIP. `tools/stage_full_asset_bundle.py` downloads that bundle
without printing its URL, enforces download/expanded-size limits, rejects path traversal,
symlinks, encrypted members, case-colliding names, and files outside the four published
SVG namespaces plus the root `symbol-inventory.json`, then validates and stages that
publication before running:

```text
python tools/run_checks.py --all --assets required \
  --build-source tests/fixtures/deployment-smoke
```

The manual workflow no longer exists to supply assets that required source CI lacks; its
purpose is to validate a separately supplied pinned publication bundle against the same
contract. It has no push or pull-request trigger and does not upload the staged graphical
tree as a GitHub Actions artifact. The environment secrets therefore remain an explicit
repository-administration prerequisite only for this optional independent check.

## Network and scheduled workflows

External-source acquisition checks may be useful as manual or scheduled
workflows, but they must remain informational/explicit unless a future decision
changes that contract. A temporary Corvus Belli outage or source-host behavior
must not make an otherwise valid source commit fail required CI.

The same principle applies to expensive performance/capacity work: scheduled or
manual workflows may establish baselines without turning every commit into a
networked or long-running benchmark.

## Remaining follow-up work

The deployment-smoke runtime import boundary, tracked published-asset validation,
cross-platform source workflow, installed-wheel smoke, dispatch-only external-bundle
full-asset workflow, protected-`main` ruleset, and focused standalone-tool regression
coverage are implemented or configured. Hosted workflow results and the optional
external-bundle environment configuration remain release-evidence/repository-
administration work; see the backlog. These layers remain the baseline for the
Milestone 2 consistency audit.

Non-blocking CI follow-up remains in the backlog: validate checked-in snapshot notes
routinely, configure the `full-assets` environment secrets with an authorized
checksum-pinned bundle and record one successful manual run, and retain release evidence
for required hosted workflows. Scheduled/manual acquisition, performance, or other
extended workflows should be added only where they provide a useful independent signal.
