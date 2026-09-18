# InfinityDB

InfinityDB builds a local SQLite database from Corvus Belli Infinity Army data
and provides a browser for exploring it. It retains the existing merge and
normalization pipeline, validates the imported data, and adds a read-only web
interface and API on top of the resulting database.

Current release: **0.5.1** (2026-09-14).

## Guiding principles

- **Accuracy:** InfinityDB uses official data sources and strives to represent
  them as accurately as possible, preserving uncertainty where the source is
  incomplete or ambiguous.
- **Flexibility:** InfinityDB expands the ways users can browse its data while
  keeping the experience simple, fast, and customizable.
- **Transparency:** InfinityDB is open source under the [MIT License](LICENSE).
  Outside data, quoted text, and image assets remain the property of their
  respective owners.

## Current features

- Imports Army JSON snapshots together with required API metadata into a
  validated SQLite database.
- Exports a lean, queryable `infinity.db` for the browser and a sibling
  `infinity.raw.db` development archive that preserves exact normalized rows.
- Provides merge, normalize, build, export, and local-server commands.
- Preserves source records and reports normalization anomalies without replacing
  a working database when an import fails.
- Browses units by army, accent- and punctuation-insensitive name search, and
  paginated results. Advanced filters narrow results by skill, equipment, or
  weapon. Clicking a catalog row opens that unit's details.
- Filters optional availability categories, including mercenaries, Spec-Ops,
  Team Operations, and reinforcements.
- Shows a unit's general profile plus faction- and army-specific profiles,
  loadouts, availability (including reinforcement profiles), skills, equipment,
  and weapons. Army-specific tables are collapsible, with the first standard
  army open initially.
- Matches reinforcement-only records to their corresponding standard unit when
  their source labels use equivalent wording, accents, or spelling variants.
- Provides a Settings menu with a persistent centimetre/inch display preference
  for movement and distance-based skill modifiers, and displays the download
  date recorded for a downloader-created Army snapshot in the sidebar.
- Provides a default-off Developer mode in Settings for showing database IDs
  and ID table columns during data review, with an optional cache bypass for
  reviewing local changes.
- Uses a shared page shell on every route: the navigation, breadcrumb header,
  catalog label, and versioned footer are rendered centrally. Core visual
  values are defined as CSS design tokens, so new screens can reuse the same
  surfaces, controls, spacing, typography, focus treatment, and responsive
  behavior.
- Accents unit-list and general-profile surfaces with the unit's main-army
  colors while retaining the shared design-system contrast and spacing rules.
- Includes a Skill Modifiers page for browsing distance-related skill extras
  and the units that use them.
- Includes searchable Skills, Equipment, Weapons, and Traits reference
  catalogs. Skills, Equipment, and Weapons detail pages show the matching unit
  profiles and loadouts; weapon pages also show available profiles, traits,
  range bands, and special weapon data. Traits pages provide concise summaries
  and group their uses across rule catalogs.
- Includes an About page that explains the local reference, its validated data
  pipeline, its current capabilities and direction, plus maintainer contact
  details, the GitHub repository, and an LLM code-use disclosure.
- Supports locally published army, unit, order, and characteristic SVG symbols
  for the browser. Corvus Belli graphical assets are acquired separately and are
  not bundled with InfinityDB source code or redistributable releases by
  default. Army and unit assets use stable ID-and-slug paths, so the browser can
  serve an exact local asset without scanning a symbol directory.
- Includes standalone scripts for downloading Army JSON snapshots, wiki mirror
  snapshots, and the current unit-symbol set. All three stage loose files
  temporarily and persist complete timestamped ZIP snapshots; normal build
  commands do not make network requests.
- Includes dedicated regression tests for each standalone tool script so the
  wiki mirror, symbol download, symbol reorganizer, Army JSON downloader, and
  shared sanitization logic stay cross-platform and safe to run.
- Uses snapshot-aware API validators and release-fingerprinted static modules,
  so browsers refresh safely when either deployed application or data changes.
- Includes server deployment, update, and image-pruning scripts; see the
  [Linux deployment guide](docs/deployment.md) for the supported workflow.

## Design direction

Accepted architectural direction is documented separately from current
features. Generated snapshot provenance under `data/manifests/snapshots/` and
the separate human-authored snapshot-note contract are now implemented. Major
remaining directions include exact migration of legacy wiki provenance and the
complete manifest-backed symbol pipeline; see
[architecture](docs/architecture.md) and [the backlog](docs/TODO.md).

The current curated rules schema records wiki pages by snapshot-local path and
snapshot date, and the checked-in v5.3 collection still contains legacy
provenance from the earlier unpacked wiki mirror. Exact timestamped wiki archive
identity/hash is intentionally deferred until the wiki downloader/packager and
curated provenance contract are rewritten together.

## Requirements and setup

Requires Python 3.11 or newer. The application uses only the Python standard
library at runtime; SQLite is included with Python.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Select `.venv` as the Python interpreter in VS Code.

## Build and browse

Place downloaded Army JSON files or a ZIP archive in `data/raw/`, then build
the database and start the local server:

```powershell
infinity-db build --compact
infinity-db serve
```

Alternatively, download a fresh raw snapshot first. The downloader fetches Army
API metadata and each faction listed in it, then repeats the complete endpoint
set and requires byte-identical responses before writing the timestamped
`JSON YYYYMMDD-HHMMSS.zip` archive. If any endpoint changes between passes, the
run aborts without publishing a snapshot and reports the changed endpoint(s).
Successful runs also report the observed per-document Army source revisions.
When the archive is built, InfinityDB records its download date and shows it in
the browser sidebar.

```powershell
python tools/download_army_json.py data/raw
infinity-db build --compact
infinity-db serve
```

The standalone wiki and Army-symbol downloaders follow the same durable-output
convention. Wiki acquisition defaults to English and creates language-labeled
`WIKI-<language> YYYYMMDD-HHMMSS.zip` archives under `data/wiki/`; Spanish is
available explicitly with `--language es`. Symbol acquisition creates
`SYMBOLS YYYYMMDD-HHMMSS.zip` archives under `data/raw/symbols/`. Successful
wiki runs remove their local work directory; incomplete wiki runs publish no
archive or provenance and preserve downloaded work under `data/work/wiki/` for
inspection. All three downloaders also write deterministic snapshot provenance bound to each
archive SHA-256 under `data/manifests/snapshots/`; these generated records are
ignored by Git. Army-symbol acquisition additionally writes the current
`data/manifests/army-symbol-build.json`, preserving raw asset identities and
every Army/static reference for later processing stages.

```powershell
python tools/download_wiki_snapshot.py
# Optional Spanish snapshot:
python tools/download_wiki_snapshot.py --language es
python tools/download_army_symbols.py "data/raw/JSON 20260910-204106.zip"
```

The development server listens on all local network interfaces. Open
<http://127.0.0.1:8000> on the development machine, or use its LAN address
(for example, `http://192.168.1.25:8000`) from another device. Allow Python
through the Windows firewall if prompted. Stop the server with `Ctrl+C`.

When no input source is supplied, `infinity-db build` imports the newest ZIP in
`data/raw/`; provide a source path to choose a different snapshot. Every
database build requires `metadata.json`: keep it beside the source directory or
ZIP, include one copy in the ZIP, or supply `--metadata PATH`. It supplies
official faction names, faction-parent relationships, and the ammunition,
weapon, skill, equipment, and rules catalogs. Current builds use those parent
relationships to derive unit `main_army_id`; Army-list JSON remains
authoritative for unit availability.

Reference PDFs and local wiki snapshots are developer and agent research inputs
only. They are never read by the application or the Army build. Curate concise,
human-reviewed rules facts under `data/curated/rules/`; PDF record citations
retain printed-page provenance, while current wiki record citations retain a
snapshot-local path and snapshot date. Validate those intermediary files before
a rules-data import:

```powershell
infinity-db validate-curated data/curated/rules/example.json
```

The army selector consumes backend-derived role and playability semantics.
Metadata parent relationships distinguish main armies, sectorials, and
Non-Aligned forces; explicit source reinforcement links identify reinforcement
lists. Non-Aligned identity `901` is exposed by the API as a non-playable grouping
node and is not selectable. Its real imported source roster is preserved for
provenance, but InfinityDB does not expose a separate roster-query surface for
`901`; unit availability is consumed through the playable child NA2 lists.
Display names are derived from source slugs when a name is unavailable, and
reinforcement lists that share the `reinf` slug include their list ID so they
remain distinguishable.

## Commands

```powershell
# Run individual data stages
infinity-db merge "data/raw/JSON 20260910-204106.zip" data/generated/master.json --compact
infinity-db normalize data/generated/master.json data/generated/normalized.json --compact
infinity-db export data/generated/normalized.json data/generated/infinity.db

# Use an alternate output directory or database/server port
infinity-db build --output-dir other-output --compact
infinity-db serve --database other-output/infinity.db --port 8001
# Bind only to this machine when LAN access is not wanted
infinity-db serve --host 127.0.0.1

# Build the independent rules-reference database from curated rules JSON
infinity-db build-rules --output data/generated/rules.db
```

`build-rules` defaults to `data/curated/rules/`. Other curated subtrees are not
rules-database inputs.

`infinity-army` and `python -m infinity_army_data` remain available for the
JSON-only pipeline. `infinity-db` (also available as `python -m infinity_db`)
adds the SQLite export and web-server commands.

Each build checks that required metadata is present, lossless source
reconstruction, normalized keys and relationships, tracked source-anomaly
ceilings for downloader-dated snapshots, and SQLite import integrity. The
source-anomaly baseline allows warning counts to decrease but rejects new
warning categories or growth above the reviewed baseline before database
export. Ad-hoc inputs without downloader snapshot provenance are not compared
against that production-source baseline. The build writes the following
ignored, generated artifacts:

```text
data/generated/master.json
data/generated/normalized.json
data/generated/normalized-validation.json
data/generated/infinity.db
data/generated/infinity.raw.db
```

The independent curated-rules build writes `data/generated/rules.db`; it is not
part of the Army JSON build and can be rebuilt separately with `build-rules`.

The database is replaced only after the new import passes integrity checks. A
failed import leaves the prior database available. Rebuilding replaces imported
data, so keep future user-authored data separately. On Windows, stop the server
before rebuilding if active readers prevent database replacement.

Rules-reference material curated from supplied PDFs and wiki research is stored
in the separate `rules.db`. It retains the provenance required by the current
curated schema and can be updated independently of the Army JSON-derived
`infinity.db` and `infinity.raw.db` snapshots.

The application also records a database compatibility revision in every build
and verifies it at startup. This is independent of the release version: bump
`DATABASE_COMPATIBILITY_VERSION` whenever a code change requires rebuilding the
database, even if the SQLite schema did not change. An incompatible database
causes startup to fail with a rebuild instruction rather than serving stale data.

The bundled server is for local development. For other hosting arrangements,
use the WSGI application factory `infinity_db.web.create_app(Path(...))`. A
repeatable Docker Compose deployment with Gunicorn and Caddy is provided in the
[Linux deployment guide](docs/deployment.md).

## Linux deployment

The supplied Docker Compose configuration packages the application and its
validated Army and curated-rules SQLite snapshots in an immutable image. Caddy
listens on HTTP and reverse-proxies to the application; place it behind an external TLS reverse
proxy for public HTTPS. Build both runtime databases before building the image:

```sh
infinity-db build --compact
infinity-db build-rules
DOMAIN=infinity.example.com IMAGE_TAG=0.5.1 docker compose up -d --build
```

Replace the hostname with the public domain configured at the external TLS
reverse proxy. See the [Linux deployment guide](docs/deployment.md) for
prerequisites, updates, rollback behavior, and operational commands.

## Project layout

```text
docs/                       # Architecture, data model, deployment, testing, and project docs
src/
  infinity_army_data/       # Army JSON merge, normalization, metadata, and validation
  infinity_db/
    cli.py                  # Build, export, rules, and local-server commands
    database/               # Schema, importer, and read-only repository queries
    skill_catalog.py        # Compose Army skills with curated rules/declarations
    trait_catalog.py        # Compose raw Army trait usage with curated rule identities
    web/
      app.py                # WSGI application and API routes
      server.py             # Local development server
      wsgi.py               # WSGI entry point for deployment
      static/               # Tracked UI assets; third-party symbols are local/ignored
tests/                      # Pipeline, database, API, web, and tool-script tests
tools/                      # Manual acquisition/processing utilities and check runner
scripts/                    # Linux deployment, update, and image-maintenance scripts
data/
  raw/                      # Ignored immutable Army/source snapshots
    symbols/                # Ignored immutable symbol snapshots
  wiki/                     # Ignored wiki research snapshots
  pdf/                      # Ignored rules and FAQ research documents
  curated/
    rules/                  # Current source-controlled rules-reference collections
    snapshot-notes/         # Source-controlled human snapshot annotations
  manifests/                # Ignored generated provenance/build-state records
  generated/                # Ignored database, JSON, and validation artifacts
reports/                    # Ignored timestamped local development-check reports
.vscode/                    # Shared build, serve, test, lint, and debug tasks
Dockerfile                  # Immutable application image for deployment
compose.yaml                # Gunicorn, Caddy, and application Compose deployment
Caddyfile                    # Reverse-proxy configuration for the Compose deployment
```

See [architecture](docs/architecture.md), the [data model](docs/data-model.md),
and [the backlog](docs/TODO.md) for current boundaries, accepted design
direction, and unimplemented work respectively.

## Development checks

Use `tools/run_checks.py` as the standard development entry point. It
orchestrates pytest, Ruff, Army data-build validation, and curated rules-database
validation while preserving the underlying tools as the authoritative checks.

```powershell
# Full code checks: pytest, then Ruff
python tools/run_checks.py --profile code

# Data/build validation (`infinity.db`, `infinity.raw.db`, and `rules.db`)
python tools/run_checks.py --profile data

# All stages
python tools/run_checks.py --all

# Targeted checks
python tools/run_checks.py --stage test tests/test_availability.py
python tools/run_checks.py --stage lint src/infinity_army_data/availability.py tests/test_availability.py
```

Requested stages continue after a failure by default so one run can report the
complete state; add `--fail-fast` to stop at the first failure. Positional
targets are forwarded to pytest/Ruff only. Use `--build-source PATH` to choose a
specific Army source for the build stage.

Add `--report` to tee the complete live console transcript to an ignored local
report. Without an explicit path the runner writes
`reports/CHECKS YYYYMMDD-HHMMSS.txt`, using the same run-start timestamp that is
recorded in the report header. Supplying a path preserves it instead:

```powershell
python tools/run_checks.py --profile code --report
python tools/run_checks.py --profile code --report reports/custom-check.txt
```

See [development checks](docs/testing.md) for stage/profile definitions,
reporting behavior, and exit codes. Tests cover the ingestion and import
pipeline, preservation of normalized records, safe database replacement, army
membership, pagination, search, API validation, reference catalogs, unit
details, profile data, static-symbol delivery, and the standalone tool scripts
used for local Army and wiki data fetches. VS Code includes build, serve, test,
and lint tasks, plus build and web-server debug configurations.

## LLM code disclosure

This project has used large language model (LLM) assistance during development.
LLM-generated suggestions and code are reviewed, tested, and remain the
responsibility of the project maintainers. The data, game terms, and artwork
assets originate from their respective sources; LLM assistance does not imply
ownership of those materials.

## License

InfinityDB's original source code and documentation are released under the
[MIT License](LICENSE). Downloaded Army data, symbols, wiki content, rules
documents, and deployment dependencies retain their own rights and licenses;
see [third-party notices](THIRD_PARTY_NOTICES.md) before redistributing a
build that includes them.
