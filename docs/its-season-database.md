# ITS 18 SQLite database (P3.2–P3.3)

**Status:** Standalone offline schema/builder. P3.4 backend registry foundation exists, but ITS is not yet in the serving set.

The ITS season database is an independently validated, deterministic SQLite
artifact created from the existing reviewed curated ITS collection. The
implementation lives in `src/infinity_db/its_season_database.py`, with the
developer entry point in `tools/build_its_season.py`.

## Current source and scope

- **Input:** `data/curated/rules/n5-its-season-18-2026.09.01.json`
  (curated document SHA-256:
  `f002d279f711c5ac27e87cc3e91686beb85ec4e42aa7a740e2cebab1c4b2bbab`).
- **Collection:** `its-season-18-2026.09.01`; season set
  `its-18@2026.09.01`; effective 2026-09-01.
- **Official source:** `its-season-18-en-pdf`, SHA-256
  `9e16874924112e62d51acf78d622f5c0cf6196064cc36f003b515de9dc448baf`.
- **Required core revision:** N5 `5.3`, recorded as an explicit compatibility
  declaration. Cross-domain reference resolution remains P3.4 work, **not**
  something this standalone build claims to have verified.
- **Currently authored:** `scenario:battleground`, three source citations,
  three geometry configurations spanning 150, 200–250 and 300–400 Army Points;
  three ITS-owned season policies for Spec-Ops in official tournaments,
  TEAM-OPS applicability and the optional Reinforcements Extra (pp. 26–28).
  These are source-cited event policies, **not** new N5 core Rule definitions.
  There is no ITS-authored FAQ publication in the curated set.

## Schema v2 and read contract

The database has a distinct SQLite application ID (`0x49445331`) and
`user_version=2` (v1 was the unhosted P3.2 pilot, superseded by dedicated
season policy storage). It does **not** masquerade as a Rules database.

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
| `season_policies` | ITS-only event or Extra policy, exact typed N5 target, context and content digest |
| `season_policy_citations` | Ordered official ITS citations, bound to the policy and source collection |

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

P3.3 adds `seasonPolicies` to the **same** reviewed ITS curated document,
but keeps them outside `records`. The Rules exporter therefore does not
import event constraints as N5 rules or broaden its interaction-audit scope.
The ITS builder separately validates exact `(seasonId, revision, context)`,
typed `rules-n5` targets, source citations, review provenance and effect
kind. `select_its_policies` returns policies only for a supplied season,
exact revision and explicit play/Extra context; a missing or incorrect
context never causes the policy to apply by default. Cross-database target
resolution and overlay presentation belong to P3.4.

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

## P3.4 registry and explicitly registered HTTP candidate

`src/infinity_db/publication_registry.py` provides typed
`PublicationReference(domain, record_id, revision)` selection and
`PublicationRegistry` for registered season files. Registration validates
the ITS core revision and all cross-domain policy and scenario references
against current N5 definitions. `season_policies` returns resolved targets
only for an exact season, revision and explicit play context. The validated
manifest exposes publication identity and SHA, not physical paths.

`ScenarioCatalog` now accepts the registry and uses it for ITS publications,
while N5 core missions continue to use the Rules database. The internal
`create_app(..., season_databases={"its-18": path})` integration fixture
exercises the same public API collection/revision selectors and SVG renderer;
the explicit ITS database contributes to the runtime cache fingerprint.
The normal checkout `serve` and Docker factories still select the validated
**two-file** set. ITS is not auto-discovered, published in `data/generated`,
or deployed until the coordinated P3.4 three-file build/selection/packaging
cutover. Unknown seasons/revisions never fall back to core definitions.

## Migration boundary

The currently deployed `rules_n5.db` still owns its transitional
Battleground copy until the coordinated serving cutover. Both the standalone
P3.3 verifier and the registered three-file HTTP candidate compare the full
ITS Battleground API output across six point sizes and 24 byte-identical SVG
maps. The candidate resolves scenario content through the ITS owner, with
the same N5/Army maintained-text enrichment. The pilot ITS file remains an
**ignored inspection/build artifact**, not a third deployment input.

The existing N5 cards still carry transitional ITS season notes and the
shared Scenario catalog still attributes marker sizes to ITS 18 p. 17.
The new ITS-only policies are retained alongside those legacy presentations
until P3.4 can cut them over atomically without losing the player-visible
restrictions or caveats. Adding/modifying maintained `src/` or curated
files changes the complete build fingerprint; regenerate the tracked
Army/Rules pair before source-bound deployment checks or merge.

For the ownership and scope exceptions (Spec-Ops, TEAM-OPS,
Reinforcements, marker citations, FAQ), see
[season publication ownership](season-publication-ownership.md).
