# InfinityDB

InfinityDB is the database project for Corvus Belli's Infinity. It brings together
data ingestion, a database backend, and a web interface. The existing merge and
normalization tools are part of this project: they supply the database with
validated data.

The initial web interface is a unit catalog with an army filter, unit-name search,
and pagination. Shared units appear once, with their available armies. Separate
ingestion, storage, API, and browser modules provide room for unit details,
profiles, equipment, skills, and fireteams later.

## Setup

Requires Python 3.11 or newer. The application has no runtime dependencies beyond
Python's standard library; SQLite is included with Python.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Select `.venv` as the Python interpreter in VS Code.

## Build the database and start the UI

Place the downloaded Army JSON files or ZIP archive in `data/raw/`, then run:

```powershell
infinity-db build "data/raw/JSON 20260909.zip" --compact
infinity-db serve
```

Open **http://127.0.0.1:8000**. Stop the local server with `Ctrl+C`.
The army selector includes source army/sectorial and reinforcement lists. Display
names are derived from source slugs when the dataset has no army name.
Reinforcement lists with the shared source slug `reinf` include their list ID in
the label so each remains identifiable.

The build writes these ignored, generated artifacts:

```text
data/generated/master.json
data/generated/normalized.json
data/generated/normalized-validation.json
data/generated/infinity.db
```

Each build verifies lossless source reconstruction, validates normalized keys and
relationships, and imports every normalized table into SQLite. Source anomalies
remain in the validation report and database metadata. The database is replaced
only after the new import passes integrity checks; a failed import leaves the
previous database available. Rebuilding replaces imported data, so keep any future
user-authored data in separate storage.

If `metadata.json` is beside the source directory or ZIP archive, the build also
imports the Army API metadata. This supplies official faction names for the UI and
stores its ammunition, weapon, skill, equipment, and rules catalogs separately.
Army-list JSON remains authoritative for unit availability. Pass `--no-metadata`
to omit it or `--metadata PATH` to choose another snapshot.

Use `--output-dir PATH` to choose a build directory and
`serve --database PATH --port 8001` to serve another database. Stop the server
before rebuilding on Windows if active database readers prevent replacement.

The bundled server is intended for local development. The WSGI application factory
`infinity_db.web.create_app(Path(...))` can also be hosted by a WSGI server when
deployment becomes part of the project.

## Use the data tools individually

```powershell
infinity-db merge "data/raw/JSON 20260909.zip" data/generated/master.json --compact
infinity-db normalize data/generated/master.json data/generated/normalized.json --compact
infinity-db export data/generated/normalized.json data/generated/infinity.db
```

The original `infinity-army` entry point and `python -m infinity_army_data` remain
available for the JSON-only pipeline. Its `build` command continues to produce
JSON files. `infinity-db build` adds the database stage. The application can also
be run as `python -m infinity_db` with the same commands.

## Project layout

```text
src/
  infinity_army_data/       # Existing merge, normalization, and validation tools
  infinity_db/
    cli.py                 # Application commands and pipeline orchestration
    database/
      schema.py            # Versioned relational schema and key definitions
      importer.py          # Validated, atomic SQLite import
      repository.py        # Read-only application queries
    web/
      app.py               # WSGI routes, API validation, and static assets
      server.py            # Local server
      static/              # HTML, CSS, and browser JavaScript modules
tests/
docs/
data/raw/                  # Ignored source snapshots
data/generated/            # Ignored databases, JSON, and validation reports
```

See [architecture and development direction](docs/architecture.md) and
[data model](docs/data-model.md) for boundaries and extension points.

## Development checks

```powershell
python -m pytest -q
python -m ruff check src/infinity_db src/infinity_army_data/cli.py tests
```

Tests cover the import pipeline, preservation of normalized records, database
replacement on failure, army membership, pagination, search, and API behavior.
The original `merge.py` and `normalize.py` have existing lint findings; the scoped
command above checks the application, shared CLI, and tests.

VS Code includes build, serve, test, and lint tasks, plus build and web-server
debug configurations.
