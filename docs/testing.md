# Development checks

**Project domain:** Project infrastructure

`tools/run_checks.py` is the canonical local validation entry point. It keeps pytest, Ruff,
Markdownlint, Pyright, Army database-build validation, rules-database validation, asset policy,
worker selection, and optional reporting under one command contract.

The type-check stage explicitly passes the runner's interpreter to Pyright for dependency
resolution, so invoking the virtual-environment Python works without first activating that
environment in the shell.

Use the project virtual-environment interpreter when available:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py --profile code
```

On Linux/macOS use `.venv/bin/python` instead.

## Profiles and stages

The runner exposes six stages:

- `test` — pytest;
- `lint` — Ruff;
- `docs` — Markdownlint (Markdown);
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

`--profile all` is equivalent to `--all` and includes `docs`. The `code` and `data`
profiles retain their existing Python/data-only stage sets.

The documentation stage uses the exact, lockfile-pinned `markdownlint-cli2` development dependency
with the project's `.markdownlint.json` rules. It scans repository Markdown while excluding ignored
local material, dependencies and reports. Install it **explicitly** before running `docs` or `--all`:

```powershell
npm ci --ignore-scripts --no-audit --no-fund
.\.venv\Scripts\python.exe tools/run_checks.py --stage docs
```

Node.js 22 or newer is required (CI uses Node.js 24). `npm run lint:docs` is an equivalent
direct command. The stage invokes the installed command via `npm run`, not `npx`; checks neither
install dependencies nor fetch packages automatically. Bootstrap downloads happen only with the
separate `npm ci` step. Missing npm or dependencies cause an explicit check failure. No Node.js
build step is part of the application's runtime or packaging.

Requested stages continue after a failure by default so one run can report the complete failure set.
Use `--fail-fast` when the first failure is sufficient.

## Targeted checks

For ordinary development, prefer the smallest check that exercises the changed contract before
running broader validation:

```powershell
python tools\run_checks.py --stage test tests/test_availability.py
python tools\run_checks.py --stage test tests/test_web.py::test_fireteam_chart_page_and_api_use_application_projection
python tools\run_checks.py --stage lint src/infinity_db/web tests/test_web.py
python tools\run_checks.py --stage type
```

Positional targets are passed to pytest/Ruff for their respective stages. The `docs` stage
always checks the configured Markdown set; `docs`, `type`, `build`, and `rules` ignore positional
targets. The runner accepts its documented options and test paths/node IDs, not arbitrary
pytest flags. For keyword selection or other pytest-specific options, invoke pytest directly.

Direct tool commands remain appropriate when debugging the tool itself:

```powershell
python -m pytest tests\test_specific.py -q
python -m pytest tests/test_web.py -k fireteam -q
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

## Scenario detail soft-navigation regression

The scenario API tests also execute `scenario.js` in a small Node.js lifecycle harness.
It verifies that leaving a scenario detail page aborts its pending map/catalog requests,
removes the distance-unit listener, and rejects late map responses. A second Node.js
harness checks that rapidly changing Army Points returns to the loading panel,
ignores superseded results (including stale errors), and displays only the latest
configuration even when an aborted request still resolves. Responsive grid
contracts are also checked in the web suite. Scenario browser visual review was
user-confirmed on 2026-10-08; the separate real-browser keyboard/touch and
loading/empty/error-state interaction checks remain open in the
[1.0 browser acceptance](TODO.md#final-10-acceptance).

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

## 1.0 source evidence baseline

The offline `tools/report_reference_baseline.py` command inventories the published Army
source snapshot identity, rules collections and source citations, and row counts by
canonical family. Generate ignored review artifacts from the repository root:

```powershell
python tools/report_reference_baseline.py --json-output reports/1.0-baseline.json --markdown-output docs/audits/1.0-baseline.md
```

Optionally pass `--army-archive <path>` to verify the exact Army ZIP SHA-256 against
the one embedded in `infinity.db`. Missing ignored PDFs/wiki snapshots are explicitly
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

The separate read-only `tools/audit_1_0_reference_inputs.py` command
cross-checks supplied **source bytes** with the existing enrichment report,
the current curated Wiki citation archive and historical Wiki revisions. These
inputs are explicit and never downloaded automatically. Keep evidence output in
the ignored `local/` workspace:

```powershell
.venv\Scripts\python.exe -m infinity_db build-rules --output local/audits/1.0-rules-current.db
.venv\Scripts\python.exe tools/audit_1_0_reference_inputs.py --rules-db local/audits/1.0-rules-current.db --wiki-history "data/wiki/WIKI-en-history 20260928-165727.zip" --wiki-history-es "data/wiki/WIKI-es-history 20261009-215316.zip" --wiki-snapshot "data/wiki/WIKI-en 20260926-200832.zip" --wiki-snapshot-es "data/wiki/WIKI-es 20261009-211304.zip" --core-pdf "data/pdf/rules/n5-rules-v5-3-en.pdf" --faq-pdf "data/pdf/faq/n5-faqs-v0-1-en.pdf" --json-output local/audits/1.0-source-evidence.json --markdown-output local/audits/1.0-source-evidence.md
```

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
The rules-enrichment audit still finds 83 gap records, including the
outdated Repeater source citation and two unresolved Sepsitor-to-Cube
relation targets; interaction review still has 15 pending supporting
identities. Those findings are **not** cleared by valid citation bytes.

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

## 1.0 Weapon Trait archived-Wiki cross-reference

`tools/audit_weapon_trait_cross_sources.py` is an **offline, read-only**
source-reconciliation tool, not part of normal builds or CI. It requires the
pinned v5.3 PDF and the exact archived Wiki history ZIP in addition to the
shipped generated databases. It fails closed if the nine maintained review
identities or the PDF/Wiki payload hashes no longer match.

```powershell
.\.venv\Scripts\python.exe -m tools.audit_weapon_trait_cross_sources --core-pdf "C:\path\to\n5-rules-v5-3-en.pdf" --wiki-history "C:\path\to\WIKI-en-history.zip" --json-output docs/audits/weapon-trait-cross-source.json --markdown-output docs/audits/weapon-trait-cross-source.md
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
.venv\Scripts\python.exe tools/audit_weapon_chart_profiles.py --core-pdf data/pdf/rules/n5-rules-v5-3-en.pdf --army-db data/generated/infinity.db --json-output local/audits/weapon-chart.json --markdown-output local/audits/weapon-chart.md
```

The output includes the source PDF SHA-256, raw compared fields, range-band
evidence, candidate discrepancies, and any unresolved chart rows. Saving Roll
multipliers are interpreted together with the Saving Attribute: an Army
`savingNum=1` with `saving=-` is non-operative and matches a printed `--`.
The supplied v5.3 PDF yields 171/171 uniquely aligned rows, with 170 five-field
matches and 170 range-band matches. Kobra Pistol CC Mode has a Saving Rolls
source discrepancy candidate (PDF 1, Army 2); Katyusha MRL prints unsigned `3`
where Army has `+3`. The separate Disco Ball object's attributes match.
This remains partial evidence: other auxiliary/equipment profiles, special-weapon
prose semantics, and API/browser projection still need review. The chart report
also records the exact Army database SHA-256 so it can be safely combined with
enrichment evidence from the same snapshot.

To reconcile unresolved Weapon rule enrichment without inventing definitions,
combine the existing enrichment and chart reports in a separate deterministic
source-to-reference triage:

```powershell
.venv\Scripts\python.exe tools/audit_enrichment_coverage.py data/generated/infinity.db --rules data/generated/rules.db --output local/audits/weapon-enrichment.json
.venv\Scripts\python.exe tools/audit_weapon_definition_gaps.py --army-db data/generated/infinity.db --enrichment local/audits/weapon-enrichment.json --chart local/audits/weapon-chart.json --json-output local/audits/weapon-triage.json --markdown-output local/audits/weapon-triage.md
```

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
python tools/audit_weapon_traits_prose.py --core-pdf "C:\path\to\n5-rules-v5-3-en.pdf" --json-output docs/audits/weapon-traits.json --markdown-output docs/audits/weapon-traits.md
```

The supplied N5 v5.3 PDF yields 145 literal Trait-list matches, 15 reviewed
notation equivalents, two manually checked source-cell matches, and nine remaining
membership/classification candidates across all 171 chart rows (zero deferrals).
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
Continuous Damage p. 175 and Immunity p. 95 with Spanish N5.3 Da?o
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
Separate known issue: existing `weapon:mines` references generate
`/weapons/mines`, whose API request `/api/weapons/mines` returns 404
because this curated family has no corresponding Army catalog item.
An explicit 1.0 navigation acceptance task owns the resolution. The
new Stealth example deliberately uses unlinked ordinary Mine prose
and linked Deployable mechanics instead of adding another broken URL.

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
`as_of=2026-09-01` publication context rather than guessing from the
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

The Fireteam type-after-loss FAQ example remains intentionally
unpublished pending English/Spanish example reconciliation. This
batch does not assert complete FAQ v0.0, ITS, or historical
cross-post inventory coverage.

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
Separately, dense normal Unit profile/loadout subrows can still overlap in
320 px layouts (observed on Scylla); that independent readability issue is
tracked for the remaining 1.0 browser gate rather than counted as one of the
39 absent source fields. Evidence, scripts and screenshots are ignored under
`local/audits/gate-1.0/source-fields-browser/`.

This closes the **39-field review for the current pinned source set only**,
not the overall 1.0 release gate. A new Army source version may populate any
candidate and must be reaudited before tagging; the current report's zero
confirmed gap families does not independently prove browser completeness.
