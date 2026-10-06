# InfinityDB

InfinityDB builds a local database and browser from Corvus Belli Infinity Army
data. While Infinity Army presents one army at a time, InfinityDB brings those
views together into a game-wide reference for exploring units, profiles,
equipment, skills, weapons, and relationships across armies.

Current release: **0.9.1** (2026-09-30).

## Guiding principles

- **Accuracy:** use official data sources and preserve uncertainty when the
  source is incomplete or ambiguous.
- **Flexibility:** make Infinity data easier to browse and understand while
  keeping the application simple, fast, and customizable.
- **Transparency:** keep InfinityDB open source and clearly distinguish project
  code from third-party data, quoted text, and graphical assets.
- **Privacy:** collect only the aggregate operational information needed to run
  and improve the service; do not build visitor profiles or persistent tracking.

## Privacy policy

InfinityDB is designed to be useful without an account and without visitor-level
tracking. The application does not build user profiles, assign persistent visitor
identifiers, or use advertising trackers, fingerprinting, or per-user analytics.

- **Operational monitoring is aggregate-only.** InfinityDB records bounded route,
  status-class, latency, response-size, active-request, and build/snapshot metrics.
  IP addresses/geolocation, user agents or fingerprints, referrers, cookie/session/
  preference values, query or search terms, unique/returning-user identifiers, and
  per-user navigation histories are excluded from those metrics.
- **Temporary settings stay in the browser session.** Theme, distance, optional-unit,
  Fireteam Wildcard, developer-mode, and related display preferences use browser
  `sessionStorage` by default. InfinityDB does not use `localStorage`.
- **Persistent cookies are opt-in.** Enabling **Remember settings** and accepting the
  confirmation stores first-party preference cookies for up to one year. They contain
  settings values only, not a visitor identifier. Turning **Remember settings** off
  deletes those InfinityDB cookies; current-session values can remain until that
  browser tab/session ends.
- **Shareable state can appear in the URL.** Search/filter state that needs to be
  bookmarkable or shareable may be encoded in the URL, so it can also appear in your
  browser history or in a link you choose to share. InfinityDB does not retain those
  query/search values in its aggregate metrics.

This policy describes InfinityDB's application-level collection and retention. Hosting
and network infrastructure necessarily processes connection metadata to deliver HTTP
traffic, and external links are governed by the destination site's own privacy policy;
InfinityDB does not use that connection metadata for visitor analytics or store it in
its application metrics.

## Current features

- Imports validated Infinity Army snapshots into a local SQLite database and
  serves a read-only browser and HTTP API.
- Browses units across armies with name search, pagination, and filters for
  skills, equipment, weapons, and optional availability. Unit Explorer filter state is shareable;
  optional-unit Settings seed a new view but the effective availability choices are recorded in the
  URL without overwriting another user's saved preferences.
- Shows a consolidated **General profile** alongside faction- and army-specific
  profiles, loadouts, availability, skills, equipment, and weapons.
- Groups equivalent standard, reinforcement, and optional-mercenary source
  records into coherent unit views while preserving their distinct availability
  and army contexts.
- Includes an Army overview with symbols, concise role/context summaries, catalog-status labels,
  legacy Army references, and direct links into pre-filtered Unit Explorer rosters.
- Includes a Skill Modifiers view and searchable Skills, Equipment, Weapons,
  Ammunition, Traits, Labels, States, Hacking Programs, and General Rules reference
  catalogs, with reverse Unit usage links where that relationship applies. Search and filter state
  uses compact self-contained share links while legacy explicit query parameters remain readable.
- Includes global search and a federated Glossary across player-facing reference domains, with
  embedded Attributes and scoped Game terms routed back to their canonical owning surfaces.
- Supports System, Light, and Dark themes from Settings; System follows the operating-system
  preference, while an explicit choice can be remembered with the other browser settings.
- Uses `/fireteams` as a general Fireteam-rules landing page and switches to Army-scoped charts when
  an Army is selected, with limits, member requirements, Wildcards, FTO loadouts, equivalence
  labels, and N5 rules/bonus context.
- Presents connected Unit relationships for Peripherals/Controllers, Includes,
  selection/dependency constraints, Reinforcement parentage, and broader
  source-declared faction membership.
- Displays curated rules-reference information where available, including
  summaries, classifications, special weapon data, and source citations.
- Supports centimetre/inch display preferences and a Developer mode for
  inspecting database IDs and other review information.
- Supports published army, unit, order, and characteristic SVG symbols. Corvus
  Belli has explicitly permitted InfinityDB to use and redistribute the graphical
  assets used by this non-commercial community project, including processed SVGs
  in public repositories and build packages. Those assets remain Corvus Belli
  property and are not covered by InfinityDB's MIT License.
- Uses reproducible source snapshots for Army, wiki, and symbol acquisition.
  Normal database builds do not make network requests.
- Includes local development, validation, deployment, update, rollback, and
  server-migration workflows.

For the technical meaning of imported and InfinityDB-derived concepts, see the
[data model](docs/data-model.md). Architectural boundaries and design decisions
are documented in [architecture](docs/architecture.md).

## Project domains

Engineering work is classified into six project domains so ownership stays clear
across planning, architecture, release notes, and implementation:

- **Acquisition:** download/source-snapshot and asset/archive tooling.
- **Data processing:** curation, validation, normalization, and generated databases.
- **Deployment:** hosted packaging, server operation, migration, and monitoring.
- **Web backend:** server-side application, queries, routes, and API behavior.
- **Web frontend:** browser UI, interaction, accessibility, and visual presentation.
- **Project infrastructure:** CI, shared checks, packaging/release tooling, developer
  workflow, and documentation conventions.

See [project domains](docs/project-domains.md) for the canonical boundaries and the
documentation-label convention.

## Roadmap to 1.0

The current direction is deliberately incremental:

- **0.7.x — Rules & context:** enriched existing catalog/application data with concise
  rules summaries, official references, classifications, and reviewed semantic
  relationships.
- **0.8.x — Connected game structure:** exposed first-class relationships such as Fireteams,
  Peripherals/Controllers, linked profiles/includes, selection/dependency constraints,
  Reinforcement parentage, and useful cross-army navigation.
- **0.9.x — Complete & discover:** closed the remaining application-data presentation
  gaps and made the result searchable, navigable, and understandable.
- **0.10.x — Stabilize & harden:** audit the completed application model end to end,
  finish the frontend/theme architecture, and harden release and operations workflows.
- **1.0.0 — Player data-complete:** every useful in-scope game datum collected by
  InfinityDB has a maintained representation and a meaningful, usable place in the
  web reference, including the current core-rules scenarios. ITS season/tournament
  content remains a later extension of the same scenario model.

In short: **0.6 built the foundation → 0.7 added context → 0.8 connected the data →
0.9 closed application gaps → 0.10 hardens and polishes → 1.0 completes the reference.**
Exact minor-release scope may move as audits discover dependencies; the durable 1.0 gate is
defined in [release process](docs/releasing.md).

## Requirements and setup

Requires Python 3.11 or newer. The application uses only the Python standard
library at runtime; SQLite is included with Python.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,symbols]"
```

Select `.venv` as the Python interpreter in VS Code.

## Quick start

If an Army snapshot already exists under `data/raw/`, build the database and
start the local server:

```powershell
infinity-db build --compact
infinity-db serve
```

Open <http://127.0.0.1:8000> on the development machine. The development server
listens on local network interfaces by default; use the machine's LAN address
from another device, or bind only to localhost with:

```powershell
infinity-db serve --host 127.0.0.1
```

Stop the server with `Ctrl+C`.

### Download a fresh Army snapshot

Acquisition is explicit and separate from normal builds:

```powershell
python tools/download_army_json.py data/raw
infinity-db build --compact
infinity-db serve
```

The downloader publishes an immutable timestamped ZIP only after validating a
coherent source acquisition. Generated snapshot provenance is kept separately
from the source archive. See [data storage and provenance](data/README.md) for
the detailed snapshot contract.

### Build the rules reference

Curated rules data is built independently from Army data:

```powershell
infinity-db build-rules
```

Reference PDFs and wiki snapshots are research inputs rather than direct runtime
inputs. Human-reviewed rules collections live under `data/curated/rules/`.

### Acquire and publish graphical symbols

Graphical assets are optional for source development but required for a complete
local graphical deployment. Use the symbol orchestrator with an existing pinned
Army snapshot (replace the timestamp with the immutable local snapshot you intend
to use):

```powershell
python tools/build_symbols.py --snapshot "data/raw/JSON YYYYMMDD-HHMMSS.zip"
```

Or intentionally fetch a fresh Army snapshot first:

```powershell
python tools/build_symbols.py --fetch-snapshot
```

Symbol processing requires the `symbols` Python extras. Compression additionally
requires SVGO v4+ and `resvg`; text conversion normally requires Inkscape.

The symbol pipeline is resumable and records detailed local logs, reports,
provenance, and publication state. Corvus Belli has granted explicit permission
for InfinityDB to redistribute the processed graphical publication used by the
project, provided the project remains non-commercial and the assets stay clearly
separate from the MIT-licensed code. Raw Army, wiki, PDF, and source-symbol
archives remain separate local/provenance inputs by project policy and are not
committed merely because the processed graphical output may be distributed. See
[third-party notices](THIRD_PARTY_NOTICES.md), [architecture](docs/architecture.md),
and [data storage and provenance](data/README.md) for the full contract.

The wiki snapshot downloader is also available independently:

```powershell
python tools/download_wiki_snapshot.py
python tools/download_wiki_snapshot.py --language es
python tools/download_wiki_snapshot.py --site human-sphere
python tools/download_wiki_snapshot.py --site human-sphere --include-history
```

The default site remains the official Infinity Wiki. Human Sphere acquisition is English-only,
uses a distinct `HUMAN-SPHERE ...zip` archive identity, and enumerates MediaWiki content pages
before following rendered links so unlinked main-namespace pages are not silently omitted. That
enumerated main-namespace inventory defines required Human Sphere content; stale discovered 404s,
Talk pages, and site-service endpoints are recorded as ignored rather than making a healthy mirror
unpublishable. Both sources keep incomplete work for inspection and publish only complete snapshots.

## Common commands

The snapshot filename below is a pattern; replace the timestamp with the local
immutable Army ZIP you intend to process.

```powershell
# Run individual Army-data stages
infinity-db merge "data/raw/JSON YYYYMMDD-HHMMSS.zip" data/generated/master.json --compact
infinity-db normalize data/generated/master.json data/generated/normalized.json --compact
infinity-db export data/generated/normalized.json data/generated/infinity.db

# Use an alternate output directory or database/server port
infinity-db build --output-dir other-output --compact
infinity-db serve --database other-output/infinity.db --port 8001

# Validate a published Army database and its development raw sibling
infinity-db database-health data/generated/infinity.db --require-raw

# Validate a curated rules file
infinity-db validate-curated data/curated/rules/example.json

# Build the independent rules-reference database
infinity-db build-rules --output data/generated/rules.db
```

`build-rules` defaults to `data/curated/rules/`.

`infinity-army` and `python -m infinity_army_data` remain available for the
JSON-only pipeline. `infinity-db` (also available as `python -m infinity_db`)
adds SQLite export and web-server commands.

A normal Army build writes generated artifacts under `data/generated/`,
including the application database `infinity.db`, the lossless development
archive `infinity.raw.db`, and intermediate normalized JSON.

Database replacement is fail-safe: a failed import leaves the previous database
available. On Windows, stop the server before rebuilding if an active reader
prevents replacement.

## Linux deployment

The supported Docker Compose deployment packages the application, the tracked runtime
databases, and the tracked processed symbol publication from one release tag into an immutable
application image. Retained aggregate metrics run separately in an immutable-root
`metrics-history` service with one bounded writable SQLite volume; no writable metrics state is
mounted into the web-facing application container. Raw Army/wiki/PDF/source-symbol archives are
not required on the server.

```sh
sh ./scripts/install-or-update.sh
```

The installer fetches release tags, hands off to the installer shipped by the target release,
checks out that release, validates the tracked `infinity.db`, `rules.db`, and
`symbol-publication.json` contract, then builds and verifies the exact image that will be
activated. Database generation remains a development/release workflow rather than a deployment
step. Upgrading an existing 0.8.0 server to 0.8.1 requires the one-time bootstrap documented in
[Linux deployment](docs/deployment.md); do not invoke the 0.8.0 installer directly for that
transition.

For a deployment test on the server that must not be reachable from the LAN, use
`sh ./scripts/deploy-local-test.sh`. It runs as a separate Compose project on
`127.0.0.1:8080` by default, including an isolated metrics-history volume, and does not prune
production rollback images. `sh ./scripts/stop-local-test.sh` preserves that test history; add
`--purge` for a deliberate clean-slate local stack.

Retained aggregate history can be inspected from the collector SQLite store with
`tools/metrics_history.py periods`, `report`, and `compare`. Reports can select or aggregate by ISO
week, InfinityDB version, and snapshot revision and expose only the bounded status/route/histogram
dimensions already collected; no historical HTTP endpoint or request-level log is added. See the
[Linux deployment guide](docs/deployment.md) for command examples and percentile semantics.

Place the supplied production Caddy service behind a public TLS reverse proxy.
Deployment validation fails if required databases or graphical assets are missing or
inconsistent.

See the [Linux deployment guide](docs/deployment.md) for prerequisites, updates,
rollback, and operational commands. Use the
[server migration guide](docs/server-migration.md) when transferring an existing
installation to another host.

## Project layout

```text
docs/                       # Tracked project docs; docs/audits/ is local audit evidence
src/
  infinity_army_data/       # Army merge, normalization, metadata, and validation
  infinity_db/              # SQLite storage, application services, API, and browser
tests/                      # Pipeline, database, API, web, and tool regression tests
tools/                      # Acquisition, processing, auditing, and check utilities
scripts/                    # Linux deployment and maintenance scripts
data/
  raw/                      # Immutable Army/source snapshots, ignored by Git
  wiki/                     # Wiki research snapshots, ignored by Git
  pdf/                      # Local rules/FAQ/ITS research documents, ignored by Git
  curated/                  # Source-controlled reviewed rules, identities, and annotations
  manifests/                # Tracked symbol publication plus ignored build provenance
  work/                     # Rebuildable processing work, ignored by Git
  reports/                  # Generated processing reports, ignored by Git
  logs/                     # Verbose pipeline logs, ignored by Git
  backups/                  # Local retained processing/publication history, ignored by Git
  generated/                # Tracked runtime DBs plus ignored intermediate build artifacts
image_overrides/            # Local authoritative symbol overrides, ignored by Git
```

## Development checks

Use `tools/run_checks.py` as the standard development entry point:

```powershell
# Full code checks: pytest, Ruff, then Pyright
python tools/run_checks.py --profile code

# Data/build validation
python tools/run_checks.py --profile data

# All stages
python tools/run_checks.py --all

# Targeted checks
python tools/run_checks.py --stage test tests/test_availability.py
python tools/run_checks.py --stage lint src/infinity_army_data/availability.py tests/test_availability.py

# Maintained local test slices
python tools/run_checks.py --stage test --test-section model
python tools/run_checks.py --stage test --test-section web

# Keep a timestamped local report
python tools/run_checks.py --profile code --report
```

Test stages use `pytest-xdist` automatic worker selection by default. Use a
fixed worker count when needed, or force serial execution for debugging:

```powershell
python tools/run_checks.py --stage test --test-workers 4
python tools/run_checks.py --stage test --test-workers 0
```

See [development checks](docs/testing.md) for worker-selection guidance and the
current test-runner contract.

Requested stages continue after a failure by default; add `--fail-fast` to stop
at the first failure. See [development checks](docs/testing.md) for stage and
profile definitions, asset modes, reports, and exit codes.

## Technical documentation

Start with the [documentation map](docs/README.md), which identifies the canonical owner for each
kind of project information. The main current-state references are:

- [Architecture](docs/architecture.md) — system boundaries, engineering principles, and durable
  cross-layer contracts.
- [Data model](docs/data-model.md) — source/application semantics, identities, persistence, and
  query invariants.
- [Application domains](docs/application-domains.md) — player-facing domain ownership and
  publication capabilities.
- [Web design guidelines](docs/web-design-guidelines.md) — browser surfaces, tables, controls,
  responsive behavior, accessibility, typography, and theming.
- [Project domains](docs/project-domains.md) — engineering ownership labels.
- [Data storage and provenance](data/README.md) and
  [curated data contracts](data/curated/README.md).
- [Rules semantics](docs/rules-semantics.md), [rules research](docs/rules-research.md), and the
  generated [rules interaction checklist](docs/rules-interaction-checklist.md).
- [Development checks](docs/testing.md) and [continuous integration](docs/ci.md).
- [Release process](docs/releasing.md), [Linux deployment](docs/deployment.md), and
  [server migration](docs/server-migration.md).
- [Backlog](docs/TODO.md) and [changelog](docs/CHANGELOG.md).

Completed audit/closeout narratives are retained by Git history rather than kept as parallel
current-state references unless they contain unique rationale that still guides active work.

## LLM code disclosure

This project has used large language model (LLM) assistance during development.
LLM-generated suggestions and code are reviewed, tested, and remain the
responsibility of the project maintainers. The data, game terms, and artwork
assets originate from their respective sources; LLM assistance does not imply
ownership of those materials.

## License

InfinityDB's original source code and documentation are released under the
[MIT License](LICENSE). All Infinity artwork, logos, symbols, and game data are
the property of Corvus Belli S.L. and are used with permission for this
non-commercial community project. Corvus Belli graphical assets are distributed
separately from the MIT License. Army data, wiki content, rules documents, fonts,
and deployment dependencies retain their own rights and licenses; see
[third-party notices](THIRD_PARTY_NOTICES.md).
