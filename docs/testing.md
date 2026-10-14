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
