# Development checks

**Project domain:** Project infrastructure

`tools/run_checks.py` is the canonical local validation entry point. It keeps pytest, Ruff,
Pyright, Army database-build validation, rules-database validation, asset policy, worker selection,
and optional reporting under one command contract.

The type-check stage explicitly passes the runner's interpreter to Pyright for dependency
resolution, so invoking the virtual-environment Python works without first activating that
environment in the shell.

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
python tools\run_checks.py --stage test tests/test_web.py::test_fireteam_chart_page_and_api_use_application_projection
python tools\run_checks.py --stage lint src/infinity_db/web tests/test_web.py
python tools\run_checks.py --stage type
```

Positional targets are passed to pytest/Ruff for their respective stages. Build/rules stages ignore
those targets. The runner accepts its documented options and test paths/node IDs, not arbitrary
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
.venv\Scripts\python.exe tools/audit_1_0_reference_inputs.py --wiki-history "data/wiki/WIKI-en-history 20260928-165727.zip" --wiki-history-es "data/wiki/WIKI-es-history 20261009-215316.zip" --wiki-snapshot "data/wiki/WIKI-en 20260926-200832.zip" --core-pdf "data/pdf/rules/n5-rules-v5-3-en.pdf" --faq-pdf "data/pdf/faq/n5-faqs-v0-1-en.pdf" --json-output local/audits/1.0-source-evidence.json --markdown-output local/audits/1.0-source-evidence.md
```

The English and Spanish history archives each need `_history/index.json`
and their indexed `_history/oldid/*.html` payloads. Historical revisions
are checked by their URL language, page identity and embedded `wgRevisionId`.
The optional `--wiki-snapshot` verifies the declared curated archive filename,
exact SHA-256, member count, every archived citation/vocabulary member, its
rendered heading and matching revision IDs in the English history archive.
Omitting the snapshot or Spanish history input reports that dimension as
**not checked** rather than verified. An English history archive alone does not
verify Spanish `oldid` pins.

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
