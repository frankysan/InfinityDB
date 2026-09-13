# InfinityDB

InfinityDB builds a local SQLite database from Corvus Belli Infinity Army data
and provides a browser for exploring it. It retains the existing merge and
normalization pipeline, validates the imported data, and adds a read-only web
interface and API on top of the resulting database.

Current release: **0.4.0** (2026-09-13).

## Current features

- Imports Army JSON snapshots together with required API metadata into a
  validated SQLite database.
- Exports a lean, queryable `infinity.db` for the browser and a sibling
  `infinity.raw.db` development archive that preserves exact normalized rows.
- Provides merge, normalize, build, export, and local-server commands.
- Preserves source records and reports normalization anomalies without replacing
  a working database when an import fails.
- Browses units by army, accent- and punctuation-insensitive name search, and
  paginated results. Clicking a catalog row opens that unit's details.
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
  and ID table columns during data review.
- Uses a shared page shell on every route: the navigation, breadcrumb header,
  catalog label, and versioned footer are rendered centrally. Core visual
  values are defined as CSS design tokens, so new screens can reuse the same
  surfaces, controls, spacing, typography, focus treatment, and responsive
  behavior.
- Accents unit-list and general-profile surfaces with the unit's main-army
  colors while retaining the shared design-system contrast and spacing rules.
- Includes a Skill Modifiers page for browsing distance-related skill extras
  and the units that use them.
- Includes searchable Skills, Equipment, and Weapons reference catalogs. Their
  detail pages show the matching unit profiles and loadouts; weapon pages also
  show available profiles, traits, range bands, and special weapon data.
- Includes an About page that explains the local reference, its validated data
  pipeline, its current capabilities and direction, plus maintainer contact
  details, the GitHub repository, and an LLM code-use disclosure.
- Bundles army, unit, order, and characteristic SVG symbols for the browser.
  Army and unit assets use stable ID-and-slug paths, so the browser can serve
  an exact asset without scanning a symbol directory.
- Includes standalone scripts for downloading Army JSON snapshots and unit
  symbols; normal build commands do not make network requests.
- Uses snapshot-aware API validators and release-fingerprinted static modules,
  so browsers refresh safely when either deployed application or data changes.

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

Alternatively, download a fresh raw snapshot first. The downloader saves Army
API metadata and each faction listed in it, writes a timestamped
`JSON YYYYMMDD-HHMMSS.zip` archive, and removes its temporary loose files.
When that archive is built, InfinityDB records its download date and shows it
in the browser sidebar.

```powershell
python tools/download_army_json.py data/raw
infinity-db build --compact
infinity-db serve
```

The development server listens on all local network interfaces. Open
<http://127.0.0.1:8000> on the development machine, or use its LAN address
(for example, `http://192.168.1.25:8000`) from another device. Allow Python
through the Windows firewall if prompted. Stop the server with `Ctrl+C`.

When no input source is supplied, `infinity-db build` imports the newest ZIP in
`data/raw/`; provide a source path to choose a different snapshot. Every
database build requires `metadata.json`: keep it beside the source directory or
ZIP, include one copy in the ZIP, or supply `--metadata PATH`. It supplies
official faction names and the ammunition, weapon, skill, equipment, and rules
catalogs. Army-list JSON remains authoritative for unit availability.

The army selector includes main-army, sectorial, and reinforcement lists.
Display names are derived from source slugs when a name is unavailable, and
reinforcement lists that share the `reinf` slug include their list ID so they
remain distinguishable.

## Commands

```powershell
# Run individual data stages
infinity-db merge "data/raw/JSON 20260909.zip" data/generated/master.json --compact
infinity-db normalize data/generated/master.json data/generated/normalized.json --compact
infinity-db export data/generated/normalized.json data/generated/infinity.db

# Use an alternate output directory or database/server port
infinity-db build --output-dir other-output --compact
infinity-db serve --database other-output/infinity.db --port 8001
# Bind only to this machine when LAN access is not wanted
infinity-db serve --host 127.0.0.1
```

`infinity-army` and `python -m infinity_army_data` remain available for the
JSON-only pipeline. `infinity-db` (also available as `python -m infinity_db`)
adds the SQLite export and web-server commands.

Each build checks that required metadata is present, lossless source
reconstruction, normalized keys and relationships, and SQLite import
integrity. It writes the following ignored, generated artifacts:

```text
data/generated/master.json
data/generated/normalized.json
data/generated/normalized-validation.json
data/generated/infinity.db
data/generated/infinity.raw.db
```

The database is replaced only after the new import passes integrity checks. A
failed import leaves the prior database available. Rebuilding replaces imported
data, so keep future user-authored data separately. On Windows, stop the server
before rebuilding if active readers prevent database replacement.

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
validated SQLite snapshot in an immutable image. Caddy listens on HTTP and
reverse-proxies to the application; place it behind an external TLS reverse
proxy for public HTTPS. Build the database before building the image:

```sh
infinity-db build --compact
DOMAIN=infinity.example.com IMAGE_TAG=0.4.0 docker compose up -d --build
```

Replace the hostname with the public domain configured at the external TLS
reverse proxy.
See the [Linux deployment guide](docs/deployment.md) for prerequisites,
updates, rollback behavior, and operational commands.

## Project layout

```text
src/
  infinity_army_data/       # Merge, normalization, metadata, and validation tools
  infinity_db/
    cli.py                  # Application commands and pipeline orchestration
    database/               # Versioned schema, atomic importer, read-only queries
    web/                    # WSGI app, shared browser shell, assets, and SVG symbols
tests/                      # Pipeline, database, API, and browser tests
tools/                      # Manual source and symbol download scripts
docs/                       # Architecture and data-model documentation
data/raw/                   # Ignored source snapshots
data/generated/             # Ignored database, JSON, and validation artifacts
```

See [architecture and development direction](docs/architecture.md) and the
[data model](docs/data-model.md) for boundaries and extension points.

## Development checks

```powershell
python -m pytest -q
python -m ruff check src/infinity_db src/infinity_army_data/cli.py tests
```

Tests cover the ingestion and import pipeline, preservation of normalized
records, safe database replacement, army membership, pagination, search, API
validation, reference catalogs, unit details, profile data, and static-symbol
delivery. VS Code includes build, serve, test, and lint tasks, plus build and
web-server debug configurations.

## LLM code disclosure

This project has used large language model (LLM) assistance during development.
LLM-generated suggestions and code are reviewed, tested, and remain the
responsibility of the project maintainers. The data, game terms, and artwork
assets originate from their respective sources; LLM assistance does not imply
ownership of those materials.

## License

InfinityDB is released under the [MIT License](LICENSE).
