# Development checks

**Project domain:** Project infrastructure

`tools/run_checks.py` is the canonical local validation entry point. It keeps pytest, Ruff,
Markdownlint, offline documentation link checks, Pyright, Army database-build validation,
rules-database validation, asset policy,
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
- `docs` — Markdownlint plus offline local Markdown path/heading checks;
- `type` — Pyright;
- `build` — Army data/database build validation;
- `rules` - interaction-review coverage and generated-checklist validation, followed by
  curated rules validation/database build.

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

The documentation stage first runs the lockfile-pinned `markdownlint-cli2` dependency
with the project's `.markdownlint.json` rules, excluding local material,
dependencies and reports. It then runs `tools.check_doc_links` with the
same Python interpreter as the check runner to validate relative Markdown
paths and heading anchors across **all Git-tracked Markdown files**, including
nested references, plus new `docs/*.md` drafts before staging. Without Git
metadata it falls back to the main root, `docs/`, and `data/` references.
The link checker excludes ignored private files, does not access external
URLs, validate application routes or substitute for browser acceptance;
it checks ordinary inline links and reference definitions, not arbitrary
embedded HTML. Its file count can differ from Markdownlint's glob selection.
Install the Markdownlint dependency **explicitly** before `docs` or `--all`:

```powershell
npm ci --ignore-scripts --no-audit --no-fund
.\.venv\Scripts\python.exe tools/run_checks.py --stage docs
```

Node.js 22 or newer is required (CI uses Node.js 24). `npm run lint:docs`
runs **Markdownlint only**; use `--stage docs` for both checks or invoke
`python -m tools.check_doc_links` directly for the offline link audit.
The stage invokes the pinned installed tool via `npm run`, not `npx`;
checks neither install dependencies nor fetch packages automatically.
Bootstrap downloads happen only with the separate `npm ci` step.
Missing npm or dependencies cause an explicit check failure. No Node.js
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
user-confirmed on 2026-10-08; later bounded Chromium interaction acceptance is
documented under [four-core-scenario acceptance](#10-four-core-scenario-browser-acceptance).
Neither run replaces [final candidate acceptance](TODO.md#final-10-acceptance).

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

## Full Army source-archive provenance tests

`tests/test_audit_source_variant_inputs.py`,
`tests/test_other_source_variant_provenance.py` and
`tests/test_martial_arts_variant_provenance.py` pin direct Skill/Equipment
occurrences, their source-extra signatures and exact Army source IDs. They
require the ignored development archive `data/generated/infinity.raw.db`
alongside the tracked published application/rules databases. The shared
pytest prerequisite skips only these raw-dependent modules when that
archive is absent in a clean CI checkout; an existing but malformed
archive fails its schema check rather than being silently accepted.
A local full-source audit must use a paired, current Army database export
from the pinned Army snapshot (or validate an existing pair with
`infinity-db database-health data/generated/infinity.db --require-raw`),
then run these modules explicitly.
A clean CI pass does **not** claim to have verified the full source-only
occurrence counts.

## Non-Skill Army source classification and Unit presentation

`tests/test_non_skill_army_presentation.py` is a maintained, hermetic
source-to-API regression against the tracked published `infinity.db`
and `rules.db`. It checks **all 72 distinct Unit/source pairs** in the
pinned snapshot for six Army Skill-source identities deliberately presented
outside the player-facing Skill category: Gizmokit, MediKit and Bangbomb
are Equipment; Regular is Training; Infinity Team Ops is a source marker;
and BTS=3 is an Attribute override. Each occurrence must reach its
correct canonical `shared_items` or contextual `specific_items` bucket;
none may be falsely presented as a Skill.

Seven representative Unit details additionally check the normal HTTP
bootstrap, their general-profile API data and Equipment route
availability. Unit details are **client-rendered**: the initial HTML only
contains `unit-content` and the `unit.js` bootstrap; a rendered
`general-profile` appears only after JavaScript executes. The separate
ignored `local/audits/non-skill-army-browser/results.json` recorded
**21/21 Chromium checks** across 1440/390/320 px for those seven
Units. A second report, `local/audits/non-skill-army-browser/current.json`,
records **21/21 passing cases on 2026-10-20** using the maintained
verifier; the user confirmed that run. Both reports are bounded
checkout-specific browser evidence, not CI browser tests or proof of
whole-catalog source-to-browser completeness.

The maintained optional verifier `tools.verify_non_skill_army_browser`
repeats the seven real-browser cases at those three widths. It checks
the client-rendered general profile, published API buckets, the correct
Equipment/Training/Attribute-override table rows, valid Equipment
destinations, the absence of mistaken Skill links, JavaScript errors,
and document-level overflow. The published Unit API inventory test remains
the separate 72-pair source-to-API gate. With the development server
running for the **same checkout and databases**, run from the repository
root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m tools.verify_non_skill_army_browser --base-url http://127.0.0.1:8000 --output local/audits/non-skill-army-browser/current.json
```

The optional verifier requires Playwright with Chromium installed and
is not part of routine source checks. The 2026-10-20 pass verifies its
development checkout but does **not** carry a release-candidate source
hash or certify a future build. Rerun it against the actual candidate
before final 1.0 browser acceptance.

## Unresolved N5.3 source-conflict publication

`tests/test_source_conflict_publication.py` protects the **published
player-facing disclosure boundary** for four reviewed but still
externally unresolved N5.3 disputes: Armed Turret Silhouette S1/S2,
Dodge (ARM+3) PDF versus Wiki wording, the Special Dice/Fireteam
Spanish reminder, and the separate printed Morat Fireteam Level 3
example. The regression checks normal API and page routes for
Armed Turret, Dodge, Special Dice and Fireteams, retaining the
reviewed source notes, structured text tokens and both official
N5.3 language-edition citations. It also checks the maintained
browser scripts still consume source notes through the normal
player-facing renderer.

This is **tracked-publication/API and served-script validation**,
not fresh Chromium DOM acceptance or an official correction.
Kobra Pistol's distinct CC-mode Anti-materiel dispute and Flash
Pulse's Spanish Wiki conflict have existing mode-scoped/weapon
API regressions under `tests/test_weaponry_catalog_api.py`.
These tests must not replace the source reconciliation tasks:
the open REA dependencies remain listed in `docs/TODO.md`.

## Published cross-domain rule relation destinations

`tests/test_public_relation_destinations.py` traverses the maintained
current rules database across Ammunition, Equipment, Hacking Programs,
General Rules, Skills, States, Traits and Weapons. It applies the same
relation-link enrichment as the web backend, then checks every distinct
**catalog-backed** destination against both its normal public detail API
and the matching served HTML detail-page contract. Skills and Hacking
Programs have dedicated detail scripts; other catalogs use the normal
`data-catalog` template marker. The test records owning rule IDs on
failures rather than assuming a structurally valid relation reaches a
usable page. This verifies route/template reachability, not client-side
rendering or source completeness.

Additional checks in the same test module verify that published
**embedded Glossary** entries target their deterministic client-created
article IDs and that Glossary links to **Weapon-family rule fragments**
resolve to actual rule cards in their host Weapon detail API. The first
check is of published embedded entries; the current published
`display_relations` graph contains no embedded Glossary link targets,
so it would be incorrect to claim such graph edges were exercised.
That composed `display_relations` graph also currently emits no
explicit `href` references; Weapon-family/Glossary fragment targets
are checked separately below. The renderer and page-script contracts
are checked, but actual client-rendered DOM navigation is not.

A further check enumerates every published Weapon slug from
`/api/weapons` and inspects each complete detail API payload.
Every same-page `#rule-…` reference from relations or
maintained-text tokens must resolve to a rule card included in that
Weapon's `rules` array. Duplicate public slugs and duplicate hosted
rule-card anchors fail. Pages with local fragments must also serve
their normal Weapon detail route. The known
`#rule-weapon-mines` reference and its AP Mine page are pinned
against a vacuous pass. The shared renderer derives those article IDs
from the same rule identities.

Intentionally unlinked source variants remain unlinked. This
does not adjudicate rules, establish every *expected* relation,
inspect live DOM anchors, or replace final release-candidate
Chromium fragment navigation at 1.0 acceptance.

### Weapon fragment Chromium verifier

With the development app running, execute this optional full-width and
mobile-width browser check from the repository root:

```powershell
.\.venv\Scripts\python.exe -m tools.verify_rule_fragment_browser --base-url http://127.0.0.1:8000 --output local/audits/weapon-rule-fragments-browser.json
```

The verifier discovers candidate Weapon pages with local rule references
from the *served* Weapon catalog/details APIs and discovers Weapon rule
fragment links from the served Glossary API. At 1440, 390 and 320 px, it
follows catalog links through the soft-navigation path, checks every
API-referenced local rule target as a rendered card even when its
reference is not displayed as a link, follows every actually rendered
same-page rule fragment link, opens a direct deep link in a **fresh
browser page** (including pages without a clickable self-link), and
follows Glossary-to-Weapon hash links. This isolates cold-load behavior
from the preceding in-page hash/navigation state. Card uniqueness
and visibility are checked atomically within a single browser
evaluation to tolerate DOM replacement during optional Unit updates,
without allowing missing or duplicate cards. It reports page
JavaScript/API/network errors and horizontal overflow; loading
failures include the last visible page state. The AP Mine/Mines source target must be hosted,
but is not required to appear as a self-link on the Weapon page.
Its JSON report belongs under ignored `local/audits`; the command
exits nonzero on failures. The current development-browser run on
2026-10-20 passed **57/57** across 1440, 390 and 320 px. This is
bounded development-server evidence, not final-release verification.

This is client-side link and anchor acceptance for the current served
app, not proof that every intended source relation exists or that
the final pinned release inputs are complete. The verifier must be
re-run against the eventual 1.0 release candidate.

## Scenario-specific FAQ publication scope

A maintained Scenario API regression checks the Annihilation-only FAQ against Core and ITS missions. The base Scenario response stays separate from dated FAQ rulings, and the served client supplies explicit scenario and season context. This does not replace rules-source adjudication or live browser acceptance.

## Source Unit notes and composite-option publication

`tests/test_unit_source_options_notes.py` compares **all** source-attributed
Unit notes and composite options in the tracked published `infinity.db`
against normal Unit detail API responses. The pinned release baseline has
**30 source Unit notes on 28 logical Units** and **18 composite Unit options
on seven logical Units**. Every source note must preserve its source
Unit ID, text, representative identity and attributed Army metadata.
Every source composite option must appear under its logical Unit,
preserving source option identity, name, Points/SWC, miniature count,
ordered Order contributions, and *exact* Army-scoped included-loadout
payload IDs and quantities. The check fails on missing or extra
inclusions rather than treating any displayed composite bundle as
sufficient.

This is **tracked-database-to-API parity**, not direct reinspection of
the ignored raw Army archive and not a live Chromium acceptance run.
The original responsive/browser investigation remains dated evidence;
the final 1.0 gate still requires validation against the final source
pair, served revision and normal player-visible pages.

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

## 1.0 reference-catalog parity and browser verification

`tests/test_application_rule_references.py` checks curated definitions,
generated rules storage, public list/detail API responses, and normally
served player templates. The covered catalog contracts differ:

- **Ammunition:** the 11-record reviewed baseline matches canonical IDs,
  names/summaries, typed facts, source citations and visible rules cards.
- **Labels:** the 24-record reviewed baseline is derived from curated
  `labels` arrays, not `records`. It preserves descriptions, maintained-text
  links and deduplicated `used_by` entries; the UI shows a Definition section
  rather than an Ammunition card or per-Label citations.
- **General Rules:** the 21-record reviewed baseline uses `rule` records
  filtered by reviewed General Rules categories, not all rules. It validates
  unique public slugs (including qualified Peripheral IDs), generated identities,
  source facts/citations and their exact rule-card IDs.

These are **source-to-storage/API/template parity** checks, not independent
rules correctness or rendered-browser acceptance. Rerun optional Chromium
navigation checks against the **current checkout's development server**, not a
stale Docker/Caddy listener. Each verifier checks its whole catalog at
1440, 390 and 320 px for correct visible details, load completion, console
errors and document-level horizontal overflow.

Start the local server in one PowerShell window:

```powershell
.\.venv\Scripts\python.exe -m infinity_db serve --host 127.0.0.1 --port 8000
```

Run the needed verifier from a second repository-root PowerShell window:

```powershell
.\.venv\Scripts\python.exe -m tools.verify_ammunition_browser --base-url http://127.0.0.1:8000 --output local/audits/ammunition-browser.json
.\.venv\Scripts\python.exe -m tools.verify_labels_browser --base-url http://127.0.0.1:8000 --output local/audits/labels-browser.json
.\.venv\Scripts\python.exe -m tools.verify_general_rules_browser --base-url http://127.0.0.1:8000 --output local/audits/general-rules-browser.json
```

**Historical acceptance, 2026-10-19:** Ammunition 33/33, Labels 72/72,
and General Rules 63/63 browser checks passed against that day's development
server. These results are evidence for those specific runs, **not** continuing
release acceptance. The complete 1.0 cross-source and browser-completeness gates
remain open; retain future browser reports in ignored `local/audits/`.

## 1.0 State, Hacking Program and Trait publication verification

The focused hermetic suites validate exact source identities, generated
storage, public list/detail API contracts and normally served templates:

- **States:** `tests/test_state_catalog.py` covers all 24 separate
  `state`-kind records, canonical names/facts, citations, published
  `rules.db` entries and catalog/detail delivery.
- **Hacking Programs:** `tests/test_hacking_program_publication.py`
  covers 12 published entries. Army owns profile values, targets,
  declaration categories, baseline Hacking Devices, Upgrade extras,
  modifiers, PS and Burst; reviewed curated records own rule semantics,
  citations and interactions. The tests reconcile both sources with
  unique public slugs, generated rule records, API values and templates.
  Neither source alone defines the complete player page.
- **Traits:** `tests/test_trait_wiki_references.py` covers all 33 canonical
  reviewed Traits, including typed facts, citations, use counts, current
  `rules.db`, published catalog/detail identities and exact reviewed
  Wiki destinations. Raw Army properties are a separate source-derived
  bucket: extra catalog slugs must be backed by that bucket and must
  never replace the canonical Trait entries.

Optional Chromium verifiers follow actual catalog-to-detail navigation
at 1440, 390 and 320 px. They check matching headings, canonical rule
cards, visible citations, JavaScript errors, incomplete loading and
document-level horizontal overflow. Hacking Programs also check profile
fields and baseline Devices; Traits check their official Wiki links and
exclude raw-property substitutes. The separate Trait Wiki-anchor test
against saved official HTML (33/33) is **not** a substitute for catalog
navigation and does not establish live Wiki availability.

With the current checkout's development server running on
`http://127.0.0.1:8000` (startup command above), run the needed
verifier from the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m tools.verify_states_browser --base-url http://127.0.0.1:8000 --output local/audits/states-browser.json
.\.venv\Scripts\python.exe -m tools.verify_hacking_programs_browser --base-url http://127.0.0.1:8000 --output local/audits/hacking-programs-browser.json
.\.venv\Scripts\python.exe -m tools.verify_traits_catalog_browser --base-url http://127.0.0.1:8000 --output local/audits/traits-catalog-browser.json
```

**Historical browser acceptance, 2026-10-19:** States 72/72,
Hacking Programs 36/36 and canonical Trait catalog entries 99/99
passed on the then-current development server. These are bounded
results for those runs, not independent rules-semantic review or
continuing 1.0 completeness acceptance. Store new evidence under
ignored `local/audits/`; rerun against the actual target checkout.

## 1.0 Martial Arts, Booty and MetaChemistry structured-chart parity

`tests/test_structured_skill_charts_publication.py` reconciles every generated
Army chart row, repository getter and Skill API `structured_reference` value.
It checks Martial Arts Levels 1–5 and exact D20 coverage of Booty and
MetaChemistry without gaps or overlaps. Typed conditional branches/components
and reviewed public links have negative cases for missing or ambiguous identities.
The tests belong to the `model` section.

The optional Chromium verifier enters all three pages through the Skills catalog
at 1440/390/320 px, compares every rendered chart cell with the served API and
local Army database, follows reviewed destinations and rejects JavaScript errors,
incomplete loading and horizontal overflow. With the matching development server running:

```powershell
.\.venv\Scripts\python.exe -m tools.verify_structured_skill_charts_browser --base-url http://127.0.0.1:8000 --output local/audits/structured-skill-charts-browser.json
```

**Historical acceptance:** successive 9/9 runs on 2026-10-19/20 covered the
presentation corrections, typed branches/components and final family/alias links.
Rerun the current verifier against the final candidate; earlier renderer passes
do not accept later code. The [data model](data-model.md#structured-skill-reference-charts)
owns current publication behavior, and the
[source-history review](n5-source-history.md#reviewed-10-structured-skill-chart-provenance)
owns PDF pages, exact Wiki revisions/hashes and FAQ comparison.

## 1.0 MetaChemistry combined outcomes — typed publication

The hermetic chart suite checks all five compound outcomes (16–20), preserving
the source `result` and exact two-component values/parameters. It rejects unknown
combinations and verifies six Skill-link occurrences to five canonical families,
including parameter-preserving Immunity links. MOV and Attribute modifiers stay
typed text. The same three-page Chromium command above checks components, links
and unchanged source values; the 2026-10-20 9/9 result is dated development evidence.

## 1.0 Booty Weapon outcomes — exact public-reference audit

The chart suite checks all ten Weapon labels. Nine resolve by exact unique
catalog name; HMG resolves through the separately reviewed Heavy Machine Gun
alias below. Source strings and TAG/other-Troop-Type branches remain intact.
The original exact-name-only 9/9 browser run preceded the alias/family revision;
use the current verifier for the complete published links.

### Booty alias and variant family references

The current API/browser supports all **16 Booty link occurrences**: nine
exact-name Weapons, HMG, and six parameterized Skill/Equipment outcomes.
HMG resolves only to the normal Heavy Machine Gun; Multispectral Visor L1,
Mimetism (-6), BS Attack (Shock)/(+1B), and TAG-only Immunity (AP)/(ARM)
retain their printed parameters while linking to canonical families.
Hermetic tests require unique reviewed destinations and preserve `outcome_variant`
or HMG's `reference_name`. A later 2026-10-20 **9/9** Chromium run covered all
16 occurrences and destinations; this revision is no longer browser-pending.
Final release verification remains separate.

## 1.0 independent N5.3 Wiki chart-value reconciliation

The chart regression independently pins all **16 Booty rows, 12 MetaChemistry
rows and 5 Martial Arts levels** against the reviewed N5.3 Wiki charts, retaining
Army source spelling such as `+1SD` versus `+1 SD`. It also requires a reviewed
canonical Skill and nonempty citations on each served page. This is distinct
from generated-storage/API parity; neither test reopens the external Wiki.
The completed PDF and history comparison is retained in
[source history](n5-source-history.md#reviewed-10-structured-skill-chart-provenance).

## 1.0 structured chart ownership and deployment FAQ provenance

The maintained regression pins Booty p. 86, Martial Arts p. 100 and
MetaChemistry p. 101 to the English N5.3 PDF source identity. It selects the
separate `faq-ruling:deployment-phase-reposition-after-measurement` only for
the reviewed N5.3/effective-date context, preserves v0.0 origin and v0.1 selected
citations, and rejects preceding contexts. The current test checks citation
identity/page, not the ignored PDF bytes.

The later direct PDF inspection and archived Wiki/FAQ reconciliation are
completed within the bounded chart scope in
[source history](n5-source-history.md#reviewed-10-structured-skill-chart-provenance).
The earlier failed attempt to reopen an external PDF is superseded by that
inspection; it is not a remaining chart-source blocker. These checks do not
certify the complete rules corpus, select random outcomes or persist game state.

## 1.0 source evidence baseline

The offline `tools/report_reference_baseline.py` command inventories the published Army
source snapshot identity, rules collections and source citations, and row counts by
canonical family. Scenario membership evidence is separated by source collection,
revision and publication identity: the current published rules database has
four N5 core scenarios and a distinct ITS Season 18 Battleground pilot.
The aggregate five memberships must **not** be described as five core missions
or counted as evidence of 1.0 scenario browser completeness.

Each category now also includes an optional `routeHint` (browser/API discovery
surfaces and presentation mode) derived from the published application-domain
registry. For example, profile/loadout rows point to nested Unit detail routes,
while Attributes use the embedded Glossary. These are *candidate starting
points*, not mappings of every source record or verified player-facing evidence;
`apiReadPath`, `browserEntryPoint`, and all fact/relationship/presentation
review fields remain pending. Where domain ownership or publication is ambiguous,
the route hint is null rather than a guessed destination.
Generate ignored review artifacts from the repository root:

```powershell
python tools/report_reference_baseline.py --json-output reports/1.0-baseline.json --markdown-output docs/audits/1.0-baseline.md
```

To ensure the **running development/release server** uses the exact Army and
rules database bytes inventoried from this checkout, add
`--verify-server http://127.0.0.1:8000` (substitute the actual server origin).
The check queries the served `/api/version` response and requires its
`snapshot_revision` to equal the SHA-256 of
`"<Army database SHA-256>:<rules database SHA-256>"`, the runtime's
existing snapshot identity. On mismatch it exits nonzero **before writing
baseline outputs**; a successful run records `servedSnapshot` in JSON.
The server option is opt-in and never starts, deploys, or modifies a server.
It checks database-pair identity only: static assets, processed symbols,
PDFs, Wiki revisions, browser correctness and full source completeness
require their independent checks. Rerun against the final candidate
and deployment, not only a local development server.

Optionally pass `--army-archive <path>` to verify the exact Army ZIP SHA-256 against
the one embedded in `infinity.db`. With the pinned source ZIP available, the
baseline checks each source faction/list ID, filename, source-file SHA-256,
version and Army/reinforcement kind against the published `army_lists` rows.
It also checks every source Unit occurrence and its original list position
against `infinity.db::army_units`, matches the source-version counts,
and rejects unexpected JSON documents, duplicate Unit IDs or source-file
count mismatches. The September 29 archive has **59 JSON documents**:
58 Army-list source files plus one `metadata.json` document; these counts
must not be conflated. The optional check records `sourceIdentityEvidence`
including the source-provenance and Unit-occurrence counts. It fails closed
on source identity, provenance or Unit-membership mismatches. It also
requires the validated application/raw database export pair and verifies
all source profile-group identities, positions, categories and text fields
against published `infinity.db::profile_groups`. Every nested source
profile's identity, position and core attribute fields, and each loadout's
identity, position, name, Points, SWC, miniature count and disabled flag,
are compared with `infinity.raw.db::profiles` and
`infinity.raw.db::loadout_options` respectively. These two tables
are intentionally **not** in the published application database.
The optional audit also compares every source profile/loadout Skill,
Equipment and Weapon occurrence against the corresponding reusable
`profile_payload_*` and `loadout_payload_*` rows in the published app
database. It checks parent source coordinates, occurrence positions, source
item IDs, display order and quantity; missing, duplicated and altered
occurrences fail closed. The audit also checks each ordered `extra`
ID against the matching published `*_payload_*_extras` row, keyed by
source parent, reference occurrence, and extra position. Missing,
duplicate, reordered, and changed extras fail closed. Non-array
source `extra` values are intentionally preserved in parent raw data
rather than normalized into extras rows; this check does not certify
that raw preservation or the meaning of any extra. The pinned
archive is also compared with published `profile_payload_characteristics`,
`loadout_payload_characteristics`, and `loadout_payload_orders` through
their source-to-payload occurrence joins. Ordered Characteristic IDs and
the modeled Order type, list count and total count must match exactly;
missing, duplicated and changed positions or facts fail closed.
For the September 29 pinned archive the verified counts are **15,011
profile Characteristics**, **0 loadout Characteristics**, and **15,195
loadout Orders**. The zero count is an explicitly checked source/storage
absence, not skipped coverage; synthetic nonempty loadout Characteristics
exercise detection of discrepancies. Unknown Order fields and non-object
Order entries may be preserved as raw data and are not fully certified
by this typed check. The optional audit also verifies contextual
profile/loadout Peripheral occurrences against published
`profile_peripherals` and `option_peripherals` source rows, preserving
army-local source IDs, positions, display order and quantities. For
profile/loadout Includes it resolves the source group/option coordinates
through `loadout_payload_occurrences` and verifies the canonical target
payload, occurrence position and quantity against the published
`profile_occurrence_includes` and `loadout_occurrence_includes`.
The audit also reconstructs the source-shared global Unit options
from all pinned Army lists, rejecting cross-army changes to shared fields.
It checks each global option's source ID, position, name, Points, SWC,
miniature count, and disabled flag against published `unit_options`.
Each source Unit-option Include is expanded across every matching
army-specific `loadout_payload_occurrences` target and compared with
`unit_option_include_targets` (source position, target Army and
canonical payload, quantity). The report distinguishes original
Includes from their expanded published target count. Missing or
duplicate targets and altered fields fail closed.
This does **not** certify global-option Skill/Equipment/Weapon arrays,
Characteristics, Orders, compatibility flags, raw Peripheral
references (no unambiguous army-local namespace), derived Peripheral
entity identities, unknown raw fields, API serialization, normal-browser
display or rules semantics.

A separate maintained `tests/test_unit_source_api_parity.py` checks
**published payload-to-Unit-API parity** for an intentionally bounded
cohort of logical Units with a single source Unit and Army membership.
It reads the tracked application database, requests normal
`/api/units/<slug>` responses, matches individually identifiable
profile/loadout occurrences by source group and profile/option ID, and
compares ordered Skill/Equipment/Weapon IDs, quantities and ordered Extra IDs
against the six published reusable payload relationships. The regression
requires at least 12 candidate Units, 24 matched contexts, nonempty
coverage in all six categories and actual Extra evidence. Ambiguous
contexts and item duplicates intentionally coalesced by the logical
presentation layer are excluded from strict cardinality comparison.
The same module also verifies the cross-Army General Profile merge
projection for logical Units with **multiple distinct source Unit IDs**.
It independently checks the contributing visible Army Profile count,
representative MOV/attribute statistics, BS/ARM/VITA difference labels,
shared Weapons and loadout-specific Weapon deltas. Shared source
Equipment must survive the Skill-to-Equipment reclassification overlay,
and nonshared Equipment must remain in each army-specific presentation.
For this merged cohort, the regression also independently reconstructs
source shared Skills (including the sole-loadout rule) and source-specific
Skills before presentation classification. It verifies that normal Unit
JSON retains the original Skill IDs, quantities and Extras in the reviewed
`skills`, `equipment`, `training`, `attribute_overrides` and
`source_markers` buckets. A native Equipment row takes precedence
when a projected Skill has the same display identity and variants.
Nonempty synthetic cases cover all four non-Skill classifications and
fail on missing categories, altered quantities or Extra IDs.
The current pinned archive has no eligible case where distinct source Unit
IDs collapse into a single army-local profile/loadout; this test does
not claim to exercise that scenario. The regression requires a
nonempty multi-Army sample with differing stats and shared/specific
item evidence. It is not full-catalog Skill classification coverage,
all combined-source variants, or browser acceptance. The existing
`test_unit_source_options_notes.py` already checks source-to-API
parity for global Unit options, Orders and expanded Includes.

The normal Unit detail **browser acceptance** is available through
`tools.verify_unit_skill_presentation_browser`. It compares each rendered
General Profile and each army-local profile/loadout section with the normal
`/api/units/<slug>` response: exact row category, item name, linked
Skill/Equipment/Weapon destination, quantity and rendered Extras.
It checks absent/extra rows as well as missing items, keeps Training
and attribute overrides unlinked, and ensures API-only source markers
never gain Skill links. It also rejects missing sections, JavaScript
errors and document-level horizontal overflow. Distance Extras are
independently checked against the configured 2.5 cm/in conversion and
Skill positive-sign policy, including literal inches/centimeters.
The default matrix covers seven pinned representative Units at 1440,
390 and 320 px (**21 pages**). Three further source-backed, distinct
Units are selected deterministically by richness of their profile
payloads, loadouts and Army memberships (at least 2 profiles, 4
loadouts and 2 Armies) and verified at 1440/768/390/320 px
(**12 more pages**). Additional isolated session-preference scenarios
exercise Team-Ops off (**3 pages**), Mercenaries off (**3 pages**),
Mercenaries and Team-Ops off together (**6 pages**), and all four
optional categories off (**6 pages**). Their DOM comparisons use
identically filtered API queries, and each scenario must change
visible Armies or General Profiles. Spec-Ops and Reinforcement cases
are also selected separately through published source Unit identities
and Army-list membership, then confirmed by the normal API to have
visible, flag-specific availability. An unfiltered baseline (**6 pages**),
each flag individually disabled (**3 + 3 pages**), and both flags
disabled together (**6 pages**) must preserve exact DOM/API parity
and remove at least one visible Army for each selected Unit.
Two source-backed Units with visible distance Extras are tested
in inches and centimeters at three widths (**12 pages**).
The pinned local server passed **81/81 page checks** on 2026-10-21.
The full matrix is assembled by the pytest integration, not by the default CLI:

```powershell
.\.venv\Scripts\python.exe tools/run_checks.py --stage test tests/test_verify_unit_skill_presentation_browser.py::test_live_chromium_unit_detail_matrix_when_available --test-workers 0 --assets off
```

It starts a temporary local server and runs when Chrome and Playwright are
available; otherwise the browser test explicitly skips. A skip is not acceptance.
The separate CLI defaults to seven Units × three widths (**21 pages**).
To check an already running candidate server and save ignored evidence:

```powershell
.\.venv\Scripts\python.exe -m tools.verify_unit_skill_presentation_browser --base-url http://127.0.0.1:8000 --channel chrome --output local/audits/1.0-unit-skill-browser.json
```

Use `--exclude-optional teamops` (repeat for multiple flags),
`--distance-unit cm`, and `--width 768` (repeat for multiple widths)
to check variants against a running server.
This remains bounded representative **browser** acceptance, not
full-catalog completeness, all optional-flag combinations, all
parameterized Skill semantics, or every visual layout variant.

For **deployed release-candidate acceptance**, use the separate
`tools.verify_release_candidate_browser` entrypoint from the exact
candidate checkout (whose tracked generated databases and static assets
must match the deployment). It first validates the served
`/api/version` fields against the supplied release version, the
SHA-256 revision of the local Army/rules database pair, and the local
static asset fingerprint. Only then does it run the representative
Unit-detail Chromium matrix (seven pinned Units at 1440/390/320 px by
default). It repeats the served identity checks after the browser run,
and writes JSON evidence only after all stages pass. Example **for the
future tagged 1.0.0 deployment**. The README still documents
0.10.1 as the latest release; this command must not be used to claim
that the hosted service already serves 1.0.0:

```powershell
.\.venv\Scripts\python.exe -m tools.verify_release_candidate_browser --base-url https://infinitydb.tsudao.com --expected-version 1.0.0 --channel chrome --json-output local/audits/1.0-hosted-unit-browser.json
```

Optional `--army-db`, `--rules-db`, repeated `--slug` and repeated
`--width` arguments select a specific retained candidate and smaller
browser cohort. This release gate must **not** be considered passed
against an earlier deployed version or different database/static-asset
build. Local-server/real-Chromium integration and rejection tests
are not evidence of hosted release acceptance. The full local 81-page
matrix remains a separate requirement; deployed representative checks
do not imply full-catalog acceptance.

An optional integration regression exercises the exact pinned ZIP
when it exists locally and skips when it is absent. Example for
the present input:

```powershell
.\.venv\Scripts\python.exe tools/report_reference_baseline.py --army-archive "data/raw/JSON 20260929-114335.zip" --verify-server http://127.0.0.1:8000 --json-output local/audits/1.0-baseline-pair.json --markdown-output local/audits/1.0-baseline-pair.md
```

Missing ignored PDFs/wiki snapshots are explicitly
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
The former 83-gap/15-pending result is superseded: Repeater/Cube links
were reconciled and the maintained interaction ledger now has zero pending
supporting identities. Re-run enrichment and interaction audits for the target
database pair. Enrichment's historical release classifications and a missing
standalone Weapon definition are not, by themselves, current 1.0 defect
verdicts; reconcile the source-pinned shared-effect reviews and final coverage
inventory. Valid citation bytes alone never establish semantic completeness.

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

## Reading the dated source and browser checks

The sections below retain source-specific reproduction procedures and bounded
historical results. Counts and descriptions of then-open work apply to their
stated run, not automatically to the current checkout. Current behavior belongs
to the data/semantic owners; [TODO](TODO.md) owns remaining work. Rerun affected
procedures against the exact candidate and retain new execution logs privately.

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

For the seven supplementary object Silhouette conflicts, cross-check both
N5.3 language PDFs and both archived Wiki Weapon Charts as **distinct
publications**. The read-only provenance audit additionally distinguishes
each Dazer-specific Wiki equipment page from its language's chart and pins
all input hashes. It requires the locally retained source archives, PyMuPDF,
and the generated Army database (none are added to Git):

```powershell
.venv\Scripts\python.exe -m tools.audit_auxiliary_silhouette_provenance --pdf-en data/pdf/rules/n5-rules-v5-3-en.pdf --pdf-es data/pdf/rules/esp-n5-update-5-3.pdf --wiki-en "data/wiki/WIKI-en 20260926-200832.zip" --wiki-es "data/wiki/WIKI-es 20261009-211304.zip" --army-db data/generated/infinity.db --json-output local/audits/auxiliary-silhouette-provenance.json --markdown-output local/audits/auxiliary-silhouette-provenance.md
```

The output reports source values, **not** a gameplay ruling or permission to
overwrite imported Army data. The regression module exercises parsers using
synthetic inputs and conditionally validates the pinned source matrix when
those local source files are available.

Before creating a distinct deployed-object/reverse-use model, generate the
read-only source/profile and curated-rule *candidate* inventory:

```powershell
.venv\Scripts\python.exe -m tools.audit_deployed_object_inventory --army-db data/generated/infinity.db --curated-source data/curated/rules/n5-core-v5.3.json --json-output local/audits/deployed-object-inventory.json
```

The report matches the 14 pinned supplementary Weapon Chart profiles using
source name, catalog and exact mode. On the pinned Army database, the sole
additional populated profile is **Madtraps** (Weapon source ID 150, mode-less;
ARM 0, BTS 0, STR 1, S 1). N5.3 p. 69 names MadTraps among Perimeter Weapons
and p. 187 lists its attack profile, but it is not one of the 14 separate
four-attribute auxiliary chart entries. Do not discard it or treat that
exclusion as a missing source value.

`config/validation/deployed-object-delivery-reviews.json` now pins an
**audit-only first batch** of six reviewed delivery paths. They distinguish
Pitcher-fired and Place Deployable delivery of the same Deployable Repeater
source profile; Disco Baller versus its Disco Ball mode/object; Drop Bears'
thrown versus deployed mode; and Mine Dispenser's loadout-dependent Mine subtype.
The audit resolves exact catalog names/modes and validates cited N5.3 pages
and maintained rules text. It does **not** publish new object IDs, infer Unit
carriers, grant any mode to another item, or resolve the Mine Dispenser subtype.

A second audit-only review batch,
`config/validation/deployed-object-candidate-reviews.json`, now classifies
four nonstandard or non-object cases against maintained source evidence and
exact English N5.3 citations:

- **Deployable Cover** (p. 122): placed Scenery Element with verified **S3**
  and Cutting Foam/Vitroferro variants, but no reviewed conventional
  ARM/BTS/STR object profile. Missing attributes are retained as unreported.
- **Armed Turret** (pp. 70, 74, 195): deployed object with an independently
  curated Trooper-style profile, ARM 2/BTS 3/STR 1/S2. Its documented S1
  quick-reference conflict is not silently resolved.
- **Deactivator** (p. 121): a user-held tool/Skill that targets deployed
  objects, not itself a deployed object.
- **SymbioBomb** (p. 74): assignable single-use Weapon, not a separately
  profiled deployed battlefield object.

The validator rejects mismatched profile shapes, lost source clauses/citations
and invented missing-attribute values. Reviewed candidate decisions and
remaining candidate mentions are reported separately. The existing Pitcher
delivery case remains distinct. Other curated Weapon/Equipment summaries
containing deployment-related words form an **unreviewed manual queue**, not
confirmed objects. Army profile text stays source-native even when four
conventional attributes can be parsed; incomplete/nonstandard values stay
unparsed. The audit requires no third-party PDFs at runtime; disputed
Silhouettes retain their original provenance, without assigning precedence
or introducing Unit/carrier identities.

For the older Wiki Weapon Chart name inventory, use the read-only
explicit-alias audit. It preserves repeated alternative tables and reports
unresolved identities independently from source-profile value differences.
The pinned Wiki and Army files are private, not committed:

```powershell
.venv\Scripts\python.exe -m tools.audit_wiki_weapon_chart_names --wiki-en "data/wiki/WIKI-en 20260926-200832.zip" --army-db data/generated/infinity.db --curated-rules data/curated/rules/n5-core-v5.3.json --json-output local/audits/wiki-weapon-names.json --markdown-output local/audits/wiki-weapon-names.md
```

A name alias is not a new Weapon rule or corrected Weapon Chart profile.
Different-valued alternative rows remain separately reviewable.

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
At this point the Mines family route was flagged for investigation,
so the new Stealth example used ordinary Mine prose and linked
Deployable mechanics. The subsequent Weapon-family routing audit
(below) confirmed that the generated `weapon:mines` destination was
already `/weapons/ap-mine#rule-weapon-mines`, not the invalid
`/weapons/mines` guess. The actual Glossary discovery defect was
corrected and browser-verified separately.

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

At that batch's date the Fireteam Type example was unpublished. It has
since been published using the consistent English HARIS example with a
separate Spanish-count discrepancy, as described in the
[current FAQ contract](data-model.md#dated-faqerrata-layer-published-reviewed-subset).
The batch alone does not establish complete FAQ/ITS historical coverage.

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

## 1.0 five Visibility Zone Game terms browser acceptance

**Verified 2026-10-16 on `dev/v1.0.0`.** A freshly rebuilt rules database
was used with the current application and Army snapshot. The five
post-inventory N5.3 p. 144 Game terms (Visibility, Low, Poor, Zero and
White Noise Zones) were checked at 1440, 390 and 320 px, including
direct Glossary hash URLs, term descriptions, global-search result
links, pointer and keyboard reference previews, accessible tooltip
descriptions, actual keyboard navigation and focused hash targets.
An isolated touch-enabled 390 px context checked first-tap preview
and second-tap navigation from the shared term to all four variants.

The first full browser pass reported **314/314 passing interaction,
navigation and overflow checks**. During manual inspection of the
320 px White Noise screenshot, a sticky-navigation overlap was
identified: the heading was partly obscured. A separate browser
measurement confirmed the defect at both narrow widths. A responsive
Glossary scroll offset now clears the sticky navigation; the
post-correction narrow-screen pass reported **229/229 checks passed**,
including explicit unobstructed-heading assertions for every term
at 390 and 320 px. The corrected 320 px White Noise screenshot was
inspected and its heading is visible.

The same browser work also reproduced JavaScript errors when
a detached maintained-reference tooltip was reopened during
navigation. The shared preview code now ignores disconnected
elements, with a Node-based regression for a connected-to-detached
reference lifecycle. The accepted browser passes have no page errors
or horizontal document overflow. This closes the bounded five-term
browser interaction requirement, not the frozen 367-record source
review or the final 1.0 whole-corpus release gate. Private scripts,
screenshots, a rebuilt rules DB and check results remain under
ignored `local/audits/visibility-five-terms-browser/`.

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
A separate dense Unit profile/loadout subrow overlap was also observed
at 320 px on Scylla during this review. That presentation defect was
subsequently corrected: normal profile Attributes, Skills, Equipment
and Includes stack at very narrow widths, and loadout names wrap above
Points/SWC. Follow-up served-browser inspection covered 320, 390, 400,
600 and 768 px. The layout correction is independent of the 39 absent
source fields and does not close the overall 1.0 browser gate.
Evidence, scripts and screenshots remain ignored under
`local/audits/gate-1.0/source-fields-browser/`.

This closes the **39-field review for the current pinned source set only**,
not the overall 1.0 release gate. A new Army source version may populate any
candidate and must be reaudited before tagging; the current report's zero
confirmed gap families does not independently prove browser completeness.

For subsequent Army snapshot reviews, the source-presentation audit has an opt-in
fail-closed occupancy gate:

```powershell
.\.venv\Scripts\python.exe tools/audit_source_presentation.py data/generated/infinity.db --require-no-occupied-gaps --output local/audits/source-presentation.json
```

This gate passes only when a checksum-matched raw source database is available
and none of the statically unrepresented fields has a populated value. It fails
if the raw pair is missing or any candidate becomes populated; inspect
`rawEvidence.potentialGapBatches` in the JSON report before deciding whether
the newly populated source semantics require application, API or browser work.

The normal check runner has an opt-in 1.0 release mode:
`python tools/run_checks.py --all --source-occupancy-gate`. It checks the
tracked release Army database and its raw sibling **before** the rules
interaction-review/build stage, failing that stage if the occupancy audit
fails. For focused rehearsal, use `--stage rules --source-occupancy-gate`.
This flag requires the rules stage and does not change the normal `--all`
workflow or hosted CI. Rebuild the published Army pair from the final pinned
snapshot before using this release gate. It does **not** replace the complete
1.0 source-to-storage-to-browser audit.

## 1.0 selected declaration-category source and browser reconciliation

**Verified 2026-10-16 on dev/v1.0.0.** BS Attack (p. 39), CC Attack
(p. 51), Discover (p. 77), Dodge (p. 79), Forward Observer (p. 92)
and Morpho-Scan (p. 103) were checked against their exact declaration
headings in the pinned N5.3 English rulebook. The first three have
corrected page-scoped declaration IDs and full Skill citations;
Morpho-Scan now has only a Short Skill mapping and the primary PDF
citation. Existing BS=11, BS=12 and CC=21 action-heading citations
were corrected without claiming validation of their numeric source
variants. The source-to-metadata tests verify the six actual headings
and prevent restoration of the eight retired ARO/Basic IDs.

A privately rebuilt current rules DB backed headless Chrome checks
of the four changed Skill pages at 1440, 390 and 320 px. **12/12
browser checks passed**, including the exact visible category badges
(BS/CC Short Skill + ARO, Discover Basic Short Skill + ARO and
Morpho-Scan Short Skill only), no JavaScript errors and no page-level
overflow. The Morpho-Scan 320 px screenshot was inspected for
readability. Private verifier, results and screenshot are ignored
under local/audits/declaration-source-browser/.

The frozen 367-record explanation audit was not renumbered. This is
selected declaration source/projection/browser verification, not
acceptance of every declaration option or any numerical replacement
variant, and not final whole-corpus acceptance.

## 1.0 Deployment and Long Skill source/browser reconciliation

**Verified 2026-10-16 on the current 1.0 development branch.**
Deployment and Long Skill declaration metadata was compared with
the exact headings in the pinned English N5.3 PDF (pp. 32, 34, 86,
89, 92, 95-97, 102, 105, 111 and 118). Three stale Deployment pages
were corrected and the shared Jump/Climb and Combat Jump/Parachutist
mappings split. The unchanged classifications of the other selected
source headings were checked in the same pass. Seven affected Skill
definitions now link to their relevant primary-source headings.

The resulting curated data exports 61 declaration-category records.
Focused tests verify page-scoped mappings, Skill type membership,
the pinned source headings and the new total of 461 published rules
database records. Headless Chromium checked eight Skill detail pages
(Infiltration, Impersonation, Hidden Deployment, Climb, Jump,
Combat Jump, Parachutist and Sapper) at 1440/390/320 px:
**24/24 checks passed** for visible declaration badges, absent
inapplicable ARO/Basic badges, HTTP responses, console errors and
document overflow. The private verifier, database, reports and
screenshots are under ignored local/audits/declaration-source-2/.

These are selected metadata and presentation acceptance results,
not a validation of the 367-record frozen explanation inventory,
conditional Climbing Plus/Super-Jump use, remaining declaration
families or whole-corpus release readiness.

## 1.0 Deployment-only Skills wrongly labeled Automatic

**Verified 2026-10-16 against the pinned N5.3 English PDF.** Booty
(p. 86), Decoy (p. 90), MetaChemistry (p. 101), Remdriver (p. 110)
and Strategic Deployment (p. 112) each use an explicit Deployment
Skill heading, not an Automatic heading. Their five independent
curated declaration mappings now point to the correct source
pages, while the owning Skills retain their existing mechanics and
prior Wiki revisions. Regression checks enforce the exact category
and page and pin the source PDF checksum.

A freshly built rules DB was checked in headless Chrome at 1440,
390 and 320 px. All five Skill pages displayed exactly one
Deployment category badge. **15/15 page checks passed** with no
JavaScript exceptions or document-level horizontal overflow.
Private evidence and the verifier are under ignored
local/audits/declaration-automatic-reconciliation/.

The current declaration catalog has 65 records and the rules
database has 465 total records. The frozen 367-record explanation
inventory was not modified; this is selected metadata/browser
acceptance only. Other Automatic category page mismatches and
training-vs-Skill attribution remain unreviewed.

## 1.0 Automatic Skill heading and Regular ownership audit

**Verified 2026-10-16 against the pinned N5.3 English PDF.**
Fourteen Automatic declarations were reconciled to source headings
on pp. 54, 87, 93, 95, 99, 103-104, 109-111, 113-114 and 116.
Regression tests pin the owning headings, the exact curated
page mappings and related Skill source citations. The unrelated
Regular/Automatic link was removed; canonical Training ownership
and the existing Order rules are preserved.

The catalog now has 28 Automatic groups and 63 total declaration
records; the exported rules database has 463 records. A freshly
rebuilt rules DB was used to verify fourteen public Skill pages
in headless Chrome at 1440, 390 and 320 px: **42/42 checks passed**,
with the expected Automatic badges and no page errors or horizontal
overflow. Private verifier, output and screenshots are stored under
ignored local/audits/automatic-page-reconciliation/.

This bounded acceptance does not sign off exceptional Automatic
activation, remaining Short Skill or named replacement-profile
semantics. The 367-record explanation-audit snapshot remains frozen.

## 1.0 Short Skill headings and Army replacement variants

**Verified 2026-10-16 against pinned N5.3 and the 2026-09-29 Army
snapshot.** Eleven current Short Skill declarations were screened
against the rulebook's exact headings. Sensor now cites p. 111
rather than p. 112 in both its declaration and full Skill definition.
The source-pinned test checks all eleven pages, while an unconditionally
runnable curated regression enforces the mapping.

BS=11 (Skill ID 279), BS=12 (278) and CC=21 (274) were checked
against the original ignored Army archive,
JSON 20260929-114335.zip, SHA-256
f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75.
The source has 59 JSON files and 2/9/6 loadout occurrences for those
identities respectively. Occurrences can repeat across factions;
the source-defined values are not independently named N5 core rules.
The core action references remain BS Attack p. 39 / CC Attack p. 51,
with general MOD/value notation context at p. 75. A dedicated
regression test checks dictionary IDs/names, unit-option occurrences,
and pinned archive digest; **that test skips if the gitignored source
archive is unavailable**, while the curated identity/parent tests
still run.

With a freshly rebuilt rules DB, the Sensor Skill page was tested
in headless Chrome at 1440, 390 and 320 px: **3/3 checks passed**,
including the Short Skill badge, no page errors and no horizontal
overflow. The private verifier, database, results and screenshot
remain under ignored local/audits/short-skill-numeric-provenance/.
The frozen 367-record audit is unchanged; the 1.0 whole-corpus
signoff and conditional permissions are still open.

## 1.0 conditional movement browser checks

**Verified 2026-10-16 against the pinned N5.3 PDF.**
Climbing Plus (p. 88) and Super-Jump (p. 113) retain
Automatic types; Climb and Jump retain Long Skill types.
Pinned source tests verify conditional Basic Short declaration,
trajectory, 360-degree LoF, Impetuous and Jet Propulsion.
The curated tests verify source references and restrictions.

The public Skill pages passed 6/6 headless Chrome cases at
1440, 390 and 320 px with no console errors or overflow.
Private evidence is in ignored local/audits/conditional-mobility-browser/.
This does not complete the frozen 367-record audit or whole-corpus 1.0 gate.

## 1.0 reactive combat Automatic Skill provenance

**Verified 2026-10-16 against the pinned N5.3 English PDF.**
Guard (p. 95, Optional), Neurocinetics (p. 104, Obligatory),
and Total Reaction (p. 116, Optional) have distinct trigger and
action restrictions. Pinned-source tests assert their original
headings and key restrictions; curated tests assert the source
pages, category labels and retained Wiki provenance.

Guard and Neurocinetics gained direct PDF citations. Neither
the underlying Skill mechanics nor the original 367-record
explanation-audit inventory changed. The rules database was
rebuilt and three published Skill pages were checked in headless
Chrome at 1440, 390 and 320 px: **9/9 cases passed**, showing
Automatic category badges without page errors or horizontal
overflow. Private evidence remains under ignored
local/audits/reactive-combat-browser/.

This is a selected provenance and browser check. It does not
cover combined Burst effects, every ARO eligibility condition,
or the final 1.0 whole-corpus acceptance gate.

## 1.0 Guard versus Aerial conditional eligibility

**Verified 2026-10-16 against the pinned N5.3 English PDF.**
Aerial p. 86 prohibits Guard against a non-Unconscious Aerial
target, independently of the Silhouette-contact exception in
Guard p. 95. Unconscious p. 172 disables Automatic Skills.
Against an Unconscious Aerial target, Guard's LoF and ZoC
requirements still apply.

A pinned-PDF test checks all three clauses. The curated
regression verifies the page citations, category types,
Aerial-owned restriction relation and conditional explanations.
A rebuilt rules DB powered headless Chrome checks of Aerial
and Guard at 1440, 390 and 320 px: **6/6 browser cases passed**,
with no JavaScript exceptions or page-level overflow.
Private evidence is under ignored local/audits/guard-aerial-browser/.

This closes the bounded Guard/Aerial exception review, not the
original frozen 367-record audit or full 1.0 acceptance gate.

## 1.0 Combat Instinct, Sixth Sense and Stealth ARO scope

**Verified 2026-10-16 against pinned English N5.3 pp. 20, 88
and 111-112.** A curated regression preserves optional Automatic
categories and the existing directed Stealth-counter relations,
with Combat Instinct's independent Surprise Attack modifier
exception. A SHA-256-pinned PDF regression checks Combat
Instinct's two clauses, Sixth Sense's attack-only outside-LoF
permission, Stealth's counter exceptions, and ordinary ZoC
reaction eligibility. Historical Wiki/FAQ citations remain
intact; Combat Instinct acquired a primary PDF citation.

A freshly built rules database was used in headless Chrome to
verify the Combat Instinct, Sixth Sense and Stealth Skill pages
at 1440, 390 and 320 px. **9/9 checks passed** for visible
Automatic badges, the newly authored scoped explanations,
source-counter names, HTTP response, no JavaScript page
errors, and no horizontal document overflow. The verifier,
result JSON, rebuilt DB and screenshot are private under
ignored local/audits/stealth-counter-aros/.

This is bounded source-to-page acceptance, not an engine-level
general ARO permission or 367-record corpus signoff. The
original inventory remains frozen; conditional ARO and
numerical Army variant work remains open.

## 1.0 Look Out! exceptional allied Dodge ARO

**Verified 2026-10-16 against pinned N5.3 English p. 81.**
A curated regression checks Look Out!'s ARO-only and No
Roll type, original reviewed restriction, Dodge relationship,
primary PDF citation, and allied selection, special ARO,
unopposed/Face to Face, and no-prior-ARO conditions.
A SHA-256-pinned source test checks all relevant clauses
and the outside-LoF/ZoC example.

The rebuilt rules database powered headless Chrome checks
of the Look Out! Skill page at 1440, 390 and 320 px.
**3/3 checks passed** for ARO badge, visible explanation,
no JavaScript page errors and no horizontal overflow.
Private verifier, rebuilt DB and screenshots are under
ignored local/audits/look-out-aro-browser/.

This is bounded ARO procedure acceptance. The original
367-record inventory is unchanged, and other conditional
AROs and the whole-corpus gate remain open.

## 1.0 Reload and Place Deployable ARO timing

**Verified 2026-10-16 against pinned English N5.3 pp. 82-83
and 120.** Curated tests assert the Short Skill/ARO identity
of Reload and Place Deployable, their retained historical
citations, Baggage eligibility and separate States Phase
recovery, reactive LoF, the Perimeter placement exception,
Conclusion timing and the unchanged occupied-spot FAQ ruling.
A SHA-256-pinned PDF regression validates the actual headings
and these eligibility and activation clauses.

A freshly rebuilt rules database was used to verify Reload
and Place Deployable in headless Chrome at 1440, 390 and
320 px. **6/6 browser cases passed**, including visible
Short Skill and ARO badges, new explanation text, no JavaScript
page errors and no horizontal overflow. Private verifier,
database, screenshot and results are stored under ignored
local/audits/reload-deployable-aros/.

The frozen 367-record inventory is unchanged. This closes a
bounded source/metadata review, not other exceptional ARO
permissions, other numerical variants, or whole-corpus 1.0.

## 1.0 Discover marker retry and ARO reveal procedure

**Verified 2026-10-16 against pinned N5.3 English p. 77.**
Curated regression coverage checks mandatory LoF, the one
attempt per target per Order restriction, failed same-Marker
lockout until next Player Turn, separate attempts by other
Troopers, reset of Marker identity following revelation and
re-entry, and the Discover + Attack ARO reveal exception.
A SHA-256-pinned PDF test checks the original source wording.
Discover retains its Basic Short Skill/ARO type, existing
source citations, and reveal relationships.

With a newly rebuilt rules database, the Discover Skill page
was tested in headless Chrome at 1440, 390 and 320 px:
**3/3 checks passed** for visible categories and new rule
explanations, no JavaScript errors, and no document overflow.
Private verifier, database, results and screenshot are under
ignored local/audits/discover-aro-review/.

This is selected rule correction and browser acceptance,
not completion of all ARO exceptions, numerical Army variants,
or the frozen 367-record audit inventory.

## 1.0 Cautious Movement ARO-suppression conditions

**Verified 2026-10-16 against SHA-256-pinned English N5.3
pp. 32 and 112.** A curated regression tests the Long Skill
classification, existing movement restrictions, new primary
PDF references, ordinary LoF/ZoC endpoint checks, the Hackable
Model and non-Hackable Hacking Area distinction, Stealth
exceptions, Hidden Deployment exclusion and unchanged
Stealth-to-Cautious Movement relation. A pinned-PDF test
checks the exact source heading and relevant clauses.

A newly rebuilt rules database was used in headless Chrome
at 1440, 390 and 320 px: **3/3 Cautious Movement page checks
passed** for the visible Long Skill category, the new source
explanations, no JavaScript exceptions and no document overflow.
The private verifier, result JSON, database and screenshot
are under ignored local/audits/cautious-movement-aro/.

This is bounded source-to-page acceptance. The frozen
367-record inventory and remaining conditional ARO and
Army-variant acceptance tasks remain open.

## 1.0 Alert! automatic Conclusion

**Verified 2026-10-16 against the SHA-256-pinned English
N5.3 PDF p. 77.** The curated regression checks Optional,
No Roll and Automatic classification, the Order/ARO
activation exclusion, allied Attack/ZoC requirement,
after-Saving-Rolls Conclusion timing and absence of
additional reactions. The original reviewed text and
historical Wiki reference remain, alongside the new
primary-source citation. A separate pinned-PDF test
checks the heading and all associated conditions.

A newly built rules DB passed **3/3 headless Chrome
Skill-page checks** at 1440, 390 and 320 px for the
Automatic badge, visible eligibility and timing text,
no JavaScript exceptions and no document overflow.
The verifier, results, database and screenshot are
private under ignored local/audits/alert-conclusion-audit/.

The original 367-record audit remains frozen; other
conditional ARO permissions and the whole-corpus gate
remain open.

## 1.0 Cyberplug Controller ARO split

**Verified 2026-10-16 against the SHA-256-pinned N5.3 English
PDF pp. 107-108.** The curated regression asserts the existing
Automatic Peripheral Skill, Cyberplug Connected/Autonomous
profiles, common-Order activation, separate reactive eligibility
and Controller-as-Idle behavior. A PDF-pinned regression checks
the official active and reactive examples.

With a freshly rebuilt rules DB, the published Cyberplug
subtype reference passed **3/3 headless Chrome checks** at
1440, 390 and 320 px. The new explanations were visible,
with no JavaScript errors or horizontal overflow. Private
verifier, screenshot, results and rules database remain under
ignored local/audits/cyberplug-aro-browser/ and
local/audits/cyberplug-aro-audit.db.

The original REA-017 foundation and frozen 367-record audit
are unchanged. This is selected ARO clarification, not a new
rules engine or whole-corpus 1.0 acceptance.

## 1.0 Speculative Attack Circular Template ARO order

**Verified 2026-10-16 against SHA-256-pinned English N5.3
p. 48.** Two regressions verify Long Skill classification,
primary and historical Wiki citations, unchanged modifiers,
the Main Target and legal impact point, the check for affected
Troopers before AROs and distance measurement, and the
behind-cover Dodge (-3) Face to Face example.

A fresh rules database powered browser checks of the
published Speculative Attack Skill page at 1440, 390
and 320 px. **3/3 headless Chrome checks passed** for
the Long Skill badge, new explanatory text, no JavaScript
errors, and no horizontal overflow. Private verifier,
results, screenshot and rebuilt DB remain in ignored
local/audits/speculative-aro-browser/ and
local/audits/speculative-aro-rules.db.

The selected ARO procedure is source-reviewed; neither
the frozen 367-record inventory nor remaining whole-corpus
1.0 acceptance tasks are marked complete.

## 1.0 Suppressive Fire G: Jumper ARO boundary

**Verified 2026-10-16 against SHA-256-pinned N5.3 English
pp. 85 and 171.** A curated test checks the Long Skill
classification, historical Wiki and primary PDF citations,
G: Jumper exception and the existing State's B3 BS Attack
ARO limit and cancellation rule. A source-pinned regression
checks the explicit Proxy exception and reactive Burst
conditions.

With a newly rebuilt rules database, the published
Suppressive Fire Skill and State pages passed **6/6
headless Chrome checks** at 1440, 390 and 320 px, including
the new explanation, existing State restrictions, no
JavaScript page errors and no horizontal overflow.
Private verifier/results/screenshot/database are under
ignored local/audits/suppressive-fire-aro/.

The frozen 367-record audit is unchanged. This is a
selected conditional activation review, not whole-corpus
1.0 acceptance.

## 1.0 Hacking Area reactive windows

**Verified 2026-10-16 against SHA-256-pinned English N5.3
pp. 55-57.** Curated regression coverage pins the owning
Hacking Area rule to the correct p. 55 source heading,
preserves its archived Wiki citation, and checks separate
ARO opportunities for an enemy Hacker and a later targeted
Trooper, plus delayed ARO restrictions for Camouflaged Markers.
A pinned-PDF test verifies both worked source examples.

The published Hacking Area page was tested from a fresh
rules database in headless Chrome at 1440, 390 and 320 px.
The first attempt displayed incomplete content at 390 px
despite HTTP 200; diagnostic reruns were all successful:
**three complete repeats, 9/9 checks passed** for rule
content, links, no JavaScript errors and no horizontal
overflow. The intermittent initial failure is recorded
but not confirmed as a reproducible UI regression.
Private verifier, evidence and rebuilt database are under
ignored local/audits/hacking-area-aro/.

This is bounded source-to-page verification, not acceptance
of all conditional ARO rules or the frozen 367-record corpus.

## 1.0 Army BTS attribute override presentation

**Verified 2026-10-16 against current built Army data and
maintained source classification policy.** A focused synthetic
regression checks that configured `attribute-override`
occurrences, including BTS=3, separate from actual Skills
in the loadout-specific presentation without changing the
original source items. Existing catalog tests continue to
ensure non-Skills such as BTS=3 do not appear as independent
rules-backed Skills.

Headless Chrome tested the actual Corregidor Alguaciles
Unit page at 1440, 390 and 320 px. **3/3 checks passed**:
the three Gatta BTS=3 occurrences appeared under Attribute
overrides, no `/skills/bts-3` links were generated, and
there were no JavaScript errors or horizontal overflow.
The private verifier, screenshots and results are under
ignored `local/audits/bts-override/`.

The frozen 367-record audit and remaining numerical
variant/source acceptance are separate open tasks.

## 1.0 non-Skill Army Unit presentation

**Focused regression, 2026-10-16.** Known Army source classifications
are projected into Unit Equipment, Training, and Attribute overrides.
The source-only Infinity Team-Ops marker is not presented as a Skill.
Native Bangbomb Equipment takes precedence over its duplicate source
occurrence, while raw Army items remain intact. Source classification
is maintained in config/catalogs/skill-source-classifications.json.
Synthetic regression passed; whole-corpus browser acceptance is open.

## 1.0 Trait Wiki heading-fragment acceptance harness

**Source and bounded browser acceptance completed 2026-10-19.** The local saved
official Wiki HTML audit first reported **22/22 existing links matched**
across 35 parsed headings and one unambiguous heading ID for each of the
11 previously unmapped canonical Traits. After those exact fragments were
added to the maintained map, a follow-up local audit reported **33/33
matched (35 headings parsed)**. This completes source-heading verification
for that HTML snapshot, but does not demonstrate that the links on the
public Trait detail pages scroll correctly in a browser. Legacy MediaWiki
encoding matters: Suppressive Fire (SF) uses `.28SF.29`, not a
display-name-derived fragment.

`tools/audit_trait_wiki_anchors.py` reads a saved HTML response from the
official `https://infinitythewiki.com/Traits` page. It checks every mapped
fragment against the page's actual heading `id` and its rendered text,
reporting missing fragments and wrong-heading matches separately. The
audit runs **offline**, writes optional JSON evidence (including the exact
HTML file SHA-256), and returns a nonzero exit status for any mismatch.
`--inventory-unmapped` separately lists heading IDs exactly as they appear
in the supplied HTML for canonical Traits without a maintained URL; unique
matches are **review candidates**, never automatically published destinations.
Missing or duplicate headings are flagged for manual investigation. The parser
excludes MediaWiki edit controls and handles void markup within headings.
Its hermetic regression tests cover legacy `mw-headline` spans, headings
with direct IDs, nested markup, candidate reporting and failure handling;
they are not evidence that the live Wiki accepts the links.

To run the source check explicitly from the repository root in PowerShell:

```powershell
Invoke-WebRequest -Uri "https://infinitythewiki.com/Traits" -OutFile "local/audits/traits-current.html"
.\.venv\Scripts\python.exe tools/audit_trait_wiki_anchors.py local/audits/traits-current.html --inventory-unmapped --output local/audits/trait-wiki-anchors.json
```

Keep the HTML and report under ignored `local/audits`, with a capture
date, source revision, and SHA-256 recorded in the associated review.
The 22/22 inventory and subsequent 33/33 result were supplied from the
local audit outputs; the underlying saved HTML and SHA-256 were not
available through the repository probe. The source audit is complete
for the tested snapshot. A separate local Chromium run subsequently passed
all 33 Trait page navigation checks against that saved Wiki HTML snapshot.

### Player-facing Trait link browser acceptance

The source audit does not exercise the browser. Inspection found that the
previous Trait Wiki link was placed exclusively in the developer-only
`#item-meta` element, and so ordinary users could not see it.
`traits-detail.html` now provides a separate, initially hidden
`#trait-wiki-link` in player-facing content. `catalog-detail.js`
sets its reviewed URL and reveals it when `wiki` is available; the
developer-only source metadata on other catalog pages is unchanged.

`tools/verify_trait_wiki_browser.py` is an optional browser acceptance
check. With a running local InfinityDB application and an existing official
Traits HTML snapshot, it visits all 33 `/traits/{slug}` routes in a clean
Chromium context with Developer Mode off; each page must render the visible
source link, open a new tab with the exact curated fragment, and scroll to
the corresponding heading. The official Wiki is fulfilled from the saved
HTML and other external traffic is blocked. Its source audit must first
match all maintained links. This check does not prove live third-party
reachability or the behavior of a later Wiki revision.

Run against the current checkout, not an older isolated Docker/Caddy
test stack. In a separate PowerShell window at the repository root start
the development server (its default port is 8000):

```powershell
.\.venv\Scripts\python.exe -m infinity_db serve --host 127.0.0.1 --port 8000
```

Then run the verifier from the repository root in another PowerShell window.
The browser dependency is optional and is not part of the canonical project
test suite:

```powershell
.\.venv\Scripts\python.exe -m pip install playwright
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m tools.verify_trait_wiki_browser --base-url http://127.0.0.1:8000 --wiki-html local/audits/traits-current.html --output local/audits/trait-wiki-browser.json
```

If all routes report HTTP 404, the verifier is reaching the wrong/stale
service rather than exposing a problem with the Wiki heading fragments.
The preflight now verifies `/traits/boost` returns HTTP 200 with the
current `#trait-wiki-link` template before testing any of the 33 links.
The repository's presentation handler separately serves all 33 routes
in regression tests. An existing listener at port 8080 is not assumed
to reflect the current working tree.

**Accepted 2026-10-19:** The local Chromium verifier passed **33/33**
Trait page navigation checks against the current development server with
the saved official Wiki HTML substituted for external requests. This
verifies that the player-facing links open the exact configured anchors
and scroll to the expected headings in the isolated browser environment.
It does not establish live external Wiki availability or later revisions.

Keep the HTML, browser report, snapshot hash, and browser-run date under
ignored `local/audits`. The hermetic regression tests separately validate
the link's HTML/JS contract and the browser fixture; the 33/33 acceptance
result was reported from the local Chromium run.
