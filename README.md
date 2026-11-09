# InfinityDB

InfinityDB is a read-only Infinity reference for exploring Units, profiles,
Equipment, Skills, Weapons, core Scenarios, and relationships across Armies. It combines
Infinity Army data with reviewed rules references, bringing information from
individual Army Lists into one game-wide browser.

Current release: **1.0.1** (2026-11-09). See the
[release notes](docs/CHANGELOG.md#101---2026-11-09) for changes and upgrade
considerations, and the [deployment guide](docs/deployment.md) for updates.

## Guiding principles

InfinityDB prioritizes official-source accuracy, transparent provenance,
privacy, and flexible reference lookup. The authoritative principles and
subsystem boundaries are in the [architecture](docs/architecture.md#guiding-principles).

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
  catalogs, including reviewed current weapons not yet used by an Army Unit,
  with reverse Unit usage links where that relationship applies. Search and filter state
  uses compact self-contained share links while legacy explicit query parameters remain readable.
- Includes global search and a federated Glossary across player-facing reference domains, with
  canonical Equipment, embedded Attributes, scoped Game terms and searchable Weapon Properties
  (such as Viral, Plasma and combined Ammunition). Weapon Properties link to their underlying
  canonical rules and reviewed, source-cited Weapon examples instead of redefining the effects.
  Embedded Attribute, Game-term and Unit Profile help entries show their source citations in the
  Glossary; Unit Profile notation help also shows them in context.
- Label definitions include deployment, targeting, modifier and fixed-result
  qualifications, with Assignable's English/Spanish timing difference disclosed.
  Detail pages show the vocabulary's source locators and their scope.
- Trait help explains Disposable exhaustion, Non-Reloadable cancellation,
  attribute-specific target effects and Silent's conditional Dodge modifiers.
- Links to **Orders and AROs** from the home page and navigation, with searchable
  declarations by Order type and links to their rules and scenario context.
- Shows eighteen suggested terrain combinations on Special Terrain, preserving
  optional and conditional values; Narrow Gate and Wide Gate searches lead to Access Width.
- Includes linked N5.3 movement and geometry references for routes, supporting
  surfaces, visibility, Cover, zones, Coherency and replacement positioning, with
  Move's declaration requirements and Silhouette diagrams.
- Presents dated N5 FAQ clarifications alongside the affected rules and scenarios,
  with concise citations and disclosed source disagreements. The **Deployed objects**
  reference presents 17 reviewed objects in individual cards, retaining disputed
  or unknown attributes and verified delivery/Unit-use context.
- Includes a browsable **Scenarios** reference with four N5.3 Core missions
  and a separately selectable ITS Season 18 Battleground pilot. Explicit
  Army Points selection, structured setup/objectives/scoring, scenario Rules
  and Skills, source-verification notes and deterministic maps all derive
  from maintained scenario definitions. Maps can be saved as standalone SVGs
  using the browser's image context menu, with the selected theme and units.
  The wider ITS library remains
  outside the 1.0 completeness requirement.
- Shows S1–S8 Silhouette templates at a shared scale in the Glossary and Unit statline previews,
  with an S2 reference alongside other supported Silhouettes.
- Supports System, Light, and Dark themes from Settings; System follows the operating-system
  preference, while an explicit choice can be remembered with the other browser settings.
- Uses `/fireteams` as a general Fireteam-rules landing page and switches to Army-scoped charts when
  an Army is selected, with limits, member requirements, Wildcards, FTO loadouts, parenthetical
  chart terms, original chart notes, and N5 rules/bonus context. Parentheses alone do not imply
  a counts-as rule or profile eligibility. Unverified Unit/FTO references are flagged;
  Reinforcement charts show parent Army limits separately. The combined view respects reviewed
  explicit Wildcard exclusions. General Fireteam rules remain available without Army chart entries.
- Presents connected Unit relationships for Peripherals/Controllers, Includes,
  selection/dependency constraints, Reinforcement parentage, and broader
  source-declared faction membership.
- Displays curated rules-reference information where available, including
  summaries, classifications, special weapon data, and source citations.
  Normal rules cards disclose known source disagreements and unresolved Army
  qualifiers without assigning unverified effects.
  Equipment families distinguish reference-only variants from options in
  the current Army data and identify family-source citation scope. Reviewed
  Weapon profiles without a separate rules
  card show their corresponding N5 Weapon Chart page when the matching
  source publication is available.
- Supports centimetre/inch display preferences and a Developer mode for
  inspecting database IDs, exact reviewed Skill/Equipment source occurrences,
  and source-scoped Restrictions links. The complete Restrictions chart has
  its own public reference page at `/rules/restrictions`.
- Supports published Army, Unit, Peripheral, Order, and Characteristic SVG symbols. Corvus
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

Engineering changes are classified by the six ownership areas defined in
[project domains](docs/project-domains.md). This is separate from player-facing
[application domains](docs/application-domains.md).

## Release progression

InfinityDB **1.0.0** is the N5.3 current-reference release, following the
0.6–0.10 series. It includes current-source rules citations, four core
scenarios, reviewed FAQ and deployed objects, and exact-variant usage
references. See the [changelog](docs/CHANGELOG.md) for the complete version
history and the [post-1.0 backlog](docs/TODO.md#post-10--maintenance-and-product-expansion)
for work outside this baseline.

Version **1.0.1** is being prepared with improved scenario maps, reference-page
spacing, version-specific release notes and safer local-build/deployment workflows.
Its Rules database embeds reviewed deployed objects while retaining the reference baseline.

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

InfinityDB supports two independent runtime targets: **serving directly from a
checkout** (local development or a trusted hosted checkout), and **immutable
Docker deployment** for internet serving. See
[architecture](docs/architecture.md#runtime-targets) and
[deployment](docs/deployment.md) for the separate contracts.

A clean checkout includes tracked runtime databases and processed graphics. Without
a local rebuild, the development server uses the tracked database pair:

```powershell
infinity-db serve
```

To use the latest Army and curated Rules changes, the original development
workflow remains supported:

```powershell
infinity-db build --compact
infinity-db build-rules
infinity-db serve
```

The Rules build publishes a complete, ignored `local/checkout-runtime/` with
co-located Army and v10 Rules databases, exact-variant usage and reviewed Weapon
citations. `serve` automatically selects that **verified local build** over
the tracked release pair; a stale/mismatched local build fails with instructions
to rebuild instead of silently falling back. Explicit `serve --database PATH`
bypasses automatic selection. Docker never reads this directory.

Open <http://127.0.0.1:8000> on the development machine. The development server
listens on local network interfaces by default; use the machine's LAN address
from another device, or bind only to localhost with
`infinity-db serve --host 127.0.0.1`. Stop with `Ctrl+C`.

### Download a fresh Army snapshot

Acquisition is explicit and separate from normal builds:

```powershell
python tools/download_army_json.py data/raw
infinity-db build --compact
infinity-db build-rules
infinity-db serve
```

The downloader publishes an immutable timestamped ZIP only after validating a
coherent source acquisition. Generated snapshot provenance is kept separately
from the source archive. See [data storage and provenance](data/README.md) for
the detailed snapshot contract.

### Build the rules reference

The current rules build combines curated rule definitions with reviewed Army-derived
deployed-object evidence, while keeping its complete reference model in rules.db:

```powershell
infinity-db build-rules
```

The default command writes v10 Rules to `local/rules-standalone.db`
and assembles the matching `local/checkout-runtime/` for checkout-based
serving. It requires the paired raw Army database produced by
`infinity-db build --compact` to publish reviewed exact-variant usage.
Use `--output` for a **standalone Rules-only** build with no checkout
publication, or `--legacy-v8`/`--legacy-v9` for compatibility work.
For an independently staged, source-matched v10 candidate, run
`python -m tools.build_v10_runtime_candidate` and repeat with `--check`.
Use `--promote-release` to explicitly verify v9→v10 semantic parity and
promote the three matched v10 tracked files (Rules, variant usage and Weapon
citations). The development branch now contains this promoted v10 set;
the previous tagged production release remains v9 until separate acceptance
and deployment.

Reference PDFs and wiki snapshots are research inputs rather than direct runtime
inputs. Human-reviewed rules collections live under `data/curated/rules/`.

### Acquire and publish graphical symbols

The processed graphical publication is already tracked in a normal checkout. Regeneration
is optional for source development and requires separate raw inputs and external tools.
Use the symbol orchestrator only when preparing a new publication, with an existing pinned
Army snapshot (replace the timestamp with the immutable local snapshot you intend to use):

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

# Validate a complete current runtime directory (without raw build inputs)
infinity-db database-health --db-dir data/generated --json

# Validate a curated rules file
infinity-db validate-curated data/curated/rules/n5-core-v5.3.json

# Build the complete v10 rules-reference candidate
infinity-db build-rules
```

`build-rules` reads `data/curated/rules/` and the reviewed Army-source
inputs, writing a v10 candidate to `local/rules-standalone.db` by default.
The Restrictions chart and deployed-object reviews are applied automatically.
Use `--legacy-v8` or `--legacy-v9` for older standalone formats.
Direct writes to the tracked release `rules.db` are disallowed.

The prepared 1.0.1 release uses v10 with deployed objects embedded in `rules.db`;
the tagged 1.0.0 release used v9 with `deployed-objects.json`. See the
[versioned storage contract](docs/data-model.md#restriction-persistence-and-version-aware-api-v9-locally-promoted)
and its release work in [TODO](docs/TODO.md#performance-storage-and-build-tooling).
A tagged immutable Docker image must receive a validated matching set of
artifacts rather than rebuilding data at container startup.

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

The supported Docker Compose deployment packages the application, matched
tracked runtime databases and processed graphical assets into an immutable
release image; no raw Army/wiki/PDF archives are needed on the server.

```sh
sh ./scripts/install-or-update.sh
```

The installer selects a published release tag and validates its bundled
artifacts before activation. For prerequisites, rollback, the special
0.8.0-to-0.8.1 transition, metrics and isolated testing, see
[Linux deployment](docs/deployment.md). Host migration is documented in the
[server migration guide](docs/server-migration.md).

## Project layout

```text
docs/                       # Tracked project documentation
local/                      # Private untracked workspace, excluded from Docker builds
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

Use the project virtual environment and the canonical
[testing guide](docs/testing.md) for profiles, test selection, asset modes,
preflight and worker instructions. Common checks from the repository root:

```powershell
.\.venv\Scripts\python.exe tools/run_checks.py --profile code
.\.venv\Scripts\python.exe tools/run_checks.py --stage docs
.\.venv\Scripts\python.exe tools/run_checks.py --all
```

The documentation stage requires pinned npm dependencies installed via
`npm ci --ignore-scripts --no-audit --no-fund`. See
[CI](docs/ci.md) for hosted acceptance and [releasing](docs/releasing.md)
for release gates.

## Technical documentation

The [documentation map](docs/README.md) identifies the authoritative owners
for architecture, data models, application domains, UI conventions, source
provenance, tests, CI, release operations, deployment and research evidence.
For work planning use the [post-1.0 backlog](docs/TODO.md); for published
outcomes use the [changelog](docs/CHANGELOG.md).

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
