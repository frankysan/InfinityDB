# ITS 18 SQLite database (P3.2)

**Status:** Standalone offline schema/builder; not part of the serving set before P3.4.

The ITS season database is an independently validated, deterministic SQLite
artifact created from the existing reviewed curated ITS collection. The
implementation lives in `src/infinity_db/its_season_database.py`, with the
developer entry point in `tools/build_its_season.py`.

## Current source and scope

- **Input:** `data/curated/rules/n5-its-season-18-2026.09.01.json`
  (curated document SHA-256:
  `e06df90f134587db2fd2f6af239e19ae8d2b3cce8dc85965f94cf73698e1fb42`).
- **Collection:** `its-season-18-2026.09.01`; season set
  `its-18@2026.09.01`; effective 2026-09-01.
- **Official source:** `its-season-18-en-pdf`, SHA-256
  `9e16874924112e62d51acf78d622f5c0cf6196064cc36f003b515de9dc448baf`.
- **Required core revision:** N5 `5.3`, recorded as an explicit compatibility
  declaration. Cross-domain reference resolution remains P3.4 work, **not**
  something this standalone build claims to have verified.
- **Currently authored:** `scenario:battleground`, three source citations,
  three geometry configurations spanning 150, 200–250 and 300–400 Army Points.
  ITS tournament constraints, Extras and season-published FAQ are not yet
  curated as independent ITS-owned records. P3.3 will deal with existing
  season-specific caveats currently embedded in N5/annex records.

## Schema v1 and read contract

The database has a distinct SQLite application ID (`0x49445331`) and
`user_version=1`; it does **not** masquerade as a Rules database.

| Table | Ownership |
| --- | --- |
| `__its_metadata` | Build ID, exact source/builder fingerprints, required core revision, scenario count |
| `collections` | Source collection authority, status and effective date |
| `sources` | Complete authored source descriptors, including printed provenance |
| `records` | Composed season-owned records with canonical content hashes |
| `record_citations` | Ordered citations associated with the exact published record |
| `scenario_sets` | Collection ID, exact revision, title and originating collection |
| `scenario_memberships` | Ordered scenario IDs within the exact season revision |
| `scenario_configurations` | Configuration ID, Army Points and original validated geometry |

All relational links are foreign-key constrained. The shared
`load_curated_document`, `compose_scenario_document` and
`parse_scenario_definition_record` code is reused. There is **no second**
mission parser, geometry model or renderer. Configuration JSON is a
lossless projection of the authored, validated record; the entire record is
also available for future integration without reinterpreting source prose.

`inspect_its_database` validates format, relational integrity, source
fingerprints, stored builder identity, scenario content hashes, citations,
configurations and geometry without writing. Its optional
`require_current_builder=True` separately enforces freshness against the
current builder; a compatible archived snapshot is not invalidated solely
because the exporter source code has changed. The CLI's `--check` enables
this freshness gate. `select_its_scenario` requires
`(season_id, revision, scenario_id)`; missing or unknown selections cannot
fall back to core missions or another season. It returns the composed
record and the selected publication's precise source identity.

## Local commands

From the repository root, with the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m tools.build_its_season
.\.venv\Scripts\python.exe -m tools.build_its_season --check
.\.venv\Scripts\python.exe -m tools.build_its_season --output local/its_18.db
```

The default output is the ignored `data/work/its/its_18.db`. The tool rejects
output under `data/generated/` before P3.4 and does not modify either
tracked release database. Builders create a temporary sibling, validate
it, and replace the destination only after success; a changed or invalid
source leaves a prior output intact. A second identical build produces
byte-identical SQLite data (normalized page settings and transaction
header).

The test module is `tests/test_its_season_database.py`, assigned to the
model test section. It covers byte determinism, matched P2 Battleground
publication content, full configuration/citation preservation, exact
selection, source drift, core compatibility, corruption, and safe
replacement.

## Migration boundary

The currently served `rules_n5.db` still owns its copy of Battleground
until P3.3 migration and P3.4 coordinated serving cutover. The first
standalone ITS database is an **ignored inspection/build artifact**, not a
third deployment input or an independently selected runtime source.
Adding the `src/` implementation changes the current complete build
fingerprint, so the tracked Army/Rules pair must be regenerated with the
normal `infinity-db build` before merging/releasing this source change.

For the ownership and scope exceptions (Spec-Ops, TEAM-OPS,
Reinforcements, marker citations, FAQ), see
[season publication ownership](season-publication-ownership.md).
