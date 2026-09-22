# InfinityDB

InfinityDB builds a local database and browser from Corvus Belli Infinity Army
data. While Infinity Army presents one army at a time, InfinityDB brings those
views together into a game-wide reference for exploring units, profiles,
equipment, skills, weapons, and relationships across armies.

Current release: **0.6.2** (2026-09-21).

## Guiding principles

- **Accuracy:** use official data sources and preserve uncertainty when the
  source is incomplete or ambiguous.
- **Flexibility:** make Infinity data easier to browse and understand while
  keeping the application simple, fast, and customizable.
- **Transparency:** keep InfinityDB open source and clearly distinguish project
  code from third-party data, quoted text, and graphical assets.

## Current features

- Imports validated Infinity Army snapshots into a local SQLite database and
  serves a read-only browser and HTTP API.
- Browses units across armies with name search, pagination, and filters for
  skills, equipment, weapons, and optional availability.
- Shows a consolidated **General profile** alongside faction- and army-specific
  profiles, loadouts, availability, skills, equipment, and weapons.
- Groups equivalent standard, reinforcement, and optional-mercenary source
  records into coherent unit views while preserving their distinct availability
  and army contexts.
- Includes a Skill Modifiers view and searchable Skills, Equipment, Weapons,
  and Traits reference catalogs with reverse links to units that use them.
- Displays curated rules-reference information where available, including
  summaries, classifications, special weapon data, and source citations.
- Supports centimetre/inch display preferences and a Developer mode for
  inspecting database IDs and other review information.
- Supports locally published army, unit, order, and characteristic SVG symbols.
  Corvus Belli graphical assets are acquired separately and are not bundled with
  InfinityDB source releases by default.
- Uses reproducible source snapshots for Army, wiki, and symbol acquisition.
  Normal database builds do not make network requests.
- Includes local development, validation, deployment, update, rollback, and
  server-migration workflows.

For the technical meaning of imported and InfinityDB-derived concepts, see the
[data model](docs/data-model.md). Architectural boundaries and design decisions
are documented in [architecture](docs/architecture.md).

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
Army snapshot:

```powershell
python tools/build_symbols.py --snapshot "data/raw/JSON 20260918-204434.zip"
```

Or intentionally fetch a fresh Army snapshot first:

```powershell
python tools/build_symbols.py --fetch-snapshot
```

Symbol processing requires the `symbols` Python extras. Compression additionally
requires SVGO v4+ and `resvg`; text conversion normally requires Inkscape.

The symbol pipeline is resumable and records detailed local logs, reports,
provenance, and publication state. See [architecture](docs/architecture.md) and
[data storage and provenance](data/README.md) for its full contract.

The wiki snapshot downloader is also available independently:

```powershell
python tools/download_wiki_snapshot.py
python tools/download_wiki_snapshot.py --language es
```

## Common commands

```powershell
# Run individual Army-data stages
infinity-db merge "data/raw/JSON 20260918-204434.zip" data/generated/master.json --compact
infinity-db normalize data/generated/master.json data/generated/normalized.json --compact
infinity-db export data/generated/normalized.json data/generated/infinity.db

# Use an alternate output directory or database/server port
infinity-db build --output-dir other-output --compact
infinity-db serve --database other-output/infinity.db --port 8001

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

The supported Docker Compose deployment packages the application and validated
runtime databases into an immutable image. Production has two explicit data paths:
`install-or-update.sh` rebuilds runtime databases from raw source already present on
the server, while `deploy-transferred.sh` deploys a commit-matched database/symbol
artifact set transferred from a development checkout without rebuilding it.

```sh
# Server-rebuild deployment
sh ./scripts/install-or-update.sh

# After tools/send_deployment_artifacts.py has transferred a matched artifact set
sh ./scripts/deploy-transferred.sh
```

For a deployment test on the server that must not be reachable from the LAN, use
`sh ./scripts/deploy-local-test.sh`. It runs as a separate Compose project on
`127.0.0.1:8080` by default and does not prune production rollback images.

Place the supplied production Caddy service behind a public TLS reverse proxy.
Deployment validation fails if required databases or graphical assets are missing or
inconsistent.

See the [Linux deployment guide](docs/deployment.md) for prerequisites, updates,
rollback, and operational commands. Use the
[server migration guide](docs/server-migration.md) when transferring an existing
installation to another host.

## Project layout

```text
docs/                       # Architecture, data model, deployment, testing, and project docs
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
  manifests/                # Generated provenance/build state, ignored by Git
  work/                     # Rebuildable processing work, ignored by Git
  reports/                  # Generated processing reports, ignored by Git
  logs/                     # Verbose pipeline logs, ignored by Git
  backups/                  # Local retained processing/publication history, ignored by Git
  generated/                # Databases and normalized build artifacts, ignored by Git
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
measured serial/parallel baseline.

Requested stages continue after a failure by default; add `--fail-fast` to stop
at the first failure. See [development checks](docs/testing.md) for stage and
profile definitions, asset modes, reports, and exit codes.

## Technical documentation

- [Architecture](docs/architecture.md) — engineering principles, subsystem
  boundaries, current architecture, and accepted design direction.
- [Data model](docs/data-model.md) — source semantics, canonical/application
  semantics, persistence, and data-model invariants.
- [Peripheral curated-data design](docs/peripheral-curated-data-design.md) —
  active Milestone 2B rules, identity, and relationship design.
- [Data storage and provenance](data/README.md) — raw, curated, generated, and
  local processing artifacts.
- [Development checks](docs/testing.md) — local and CI validation.
- [Release process](docs/releasing.md) — mandatory release checklist and project-wide
  documentation audit.
- [Linux deployment](docs/deployment.md) — production deployment and updates.
- [Server migration](docs/server-migration.md) — exact transfer and rebuild
  requirements.
- [Backlog](docs/TODO.md) — planned and unimplemented work.
- [Changelog](docs/CHANGELOG.md) — release history and upgrade-relevant changes.

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
see [third-party notices](THIRD_PARTY_NOTICES.md) before redistributing a build
that includes them.
