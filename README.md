# InfinityDB

InfinityDB builds a local SQLite database from Corvus Belli Infinity Army data
and provides a browser for exploring it. It retains the existing merge and
normalization pipeline, validates the imported data, and adds a read-only web
interface and API on top of the resulting database.

## Current features

- Imports Army JSON snapshots and optional API metadata into a validated SQLite
  database.
- Provides merge, normalize, build, export, and local-server commands.
- Preserves source records and reports normalization anomalies without replacing
  a working database when an import fails.
- Browses units by army, name search, and paginated results.
- Shows a unit's general profile plus faction- and army-specific profiles,
  loadouts, availability, skills, equipment, and weapons.
- Bundles army and unit SVG symbols for the browser.
- Includes standalone scripts for downloading Army JSON snapshots and unit
  symbols; normal build commands do not make network requests.

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

```powershell
python tools/download_army_json.py data/raw
infinity-db build --compact
infinity-db serve
```

Open <http://127.0.0.1:8000> and stop the server with `Ctrl+C`.

When no input source is supplied, `infinity-db build` imports the newest ZIP in
`data/raw/`; provide a source path to choose a different snapshot. If
`metadata.json` sits next to the source directory or ZIP, it is imported too:
it supplies official faction names and the ammunition, weapon, skill,
equipment, and rules catalogs. Army-list JSON remains authoritative for unit
availability. Use `--no-metadata` to omit metadata or `--metadata PATH` to
choose another metadata snapshot.

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
```

`infinity-army` and `python -m infinity_army_data` remain available for the
JSON-only pipeline. `infinity-db` (also available as `python -m infinity_db`)
adds the SQLite export and web-server commands.

Each build checks lossless source reconstruction, normalized keys and
relationships, and SQLite import integrity. It writes the following ignored,
generated artifacts:

```text
data/generated/master.json
data/generated/normalized.json
data/generated/normalized-validation.json
data/generated/infinity.db
```

The database is replaced only after the new import passes integrity checks. A
failed import leaves the prior database available. Rebuilding replaces imported
data, so keep future user-authored data separately. On Windows, stop the server
before rebuilding if active readers prevent database replacement.

The bundled server is for local development. For other hosting arrangements,
use the WSGI application factory `infinity_db.web.create_app(Path(...))`.

## Project layout

```text
src/
  infinity_army_data/       # Merge, normalization, metadata, and validation tools
  infinity_db/
    cli.py                  # Application commands and pipeline orchestration
    database/               # Versioned schema, atomic importer, read-only queries
    web/                    # WSGI app, local server, browser assets, and SVG symbols
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
validation, unit details, and profile data. VS Code includes build, serve, test,
and lint tasks, plus build and web-server debug configurations.

## LLM code disclosure

This project has used large language model (LLM) assistance during development.
LLM-generated suggestions and code are reviewed, tested, and remain the
responsibility of the project maintainers. The data, game terms, and artwork
assets originate from their respective sources; LLM assistance does not imply
ownership of those materials.

## License

InfinityDB is released under the [MIT License](LICENSE).
