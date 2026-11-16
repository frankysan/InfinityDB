# ITS Season 18 SQLite database

**Project domain:** Data processing

Schema v2 participates in the complete four-file build and serving set: Army,
Rules, and two separately selected ITS Season 18 revisions.
This page owns the ITS database format, selection and build contract;
release acceptance belongs in [releasing](releasing.md).

The ITS season database is an independently validated, deterministic SQLite
artifact created from the existing reviewed curated ITS collection. The
implementation lives in `src/infinity_db/its_season_database.py`, with the
developer entry point in `tools/data/build_its_season.py`.

## Current source and scope

- **Input:** `data/curated/rules/n5-its-season-18-2026.09.01.json`
  (curated document SHA-256:
  `f002d279f711c5ac27e87cc3e91686beb85ec4e42aa7a740e2cebab1c4b2bbab`).
- **Collection:** `its-season-18-2026.09.01`; season set
  `its-18@2026.09.01`; effective 2026-09-01.
- **Official source:** `its-season-18-en-pdf`, SHA-256
  `9e16874924112e62d51acf78d622f5c0cf6196064cc36f003b515de9dc448baf`.
- **Required core revision:** N5 `5.3`, recorded as an explicit compatibility
  declaration. Complete-set validation resolves ITS dependencies against the
  selected Rules database and checks source identity against the Army/Rules
  build manifest.
- **Currently authored:** `scenario:battleground`, three source citations,
  three geometry configurations spanning 150, 200–250 and 300–400 Army Points;
  three ITS-owned season policies for Spec-Ops in official tournaments,
  TEAM-OPS applicability and the optional Reinforcements Extra (pp. 26–28).
  These are source-cited event policies, **not** new N5 core Rule definitions.
  There is no ITS-authored FAQ publication in the curated set.

### Published 2026.09.11 hotfix curation

The independent curated input
`data/curated/its/n5-its-season-18-2026.09.11.json` is published
into `its_18_2026.09.11.db`. The original `2026.09.01` input and
`its_18.db` remain unchanged in mission semantics and independently selectable.
The Rules exporter imports neither ITS-owned source. The public scenario selector
lists `its-18@2026.09.01` (historical Battleground) and
`its-18@2026.09.11` (twelve reviewed hotfix missions).

The selected hotfix source binds English 2026.09.11 (142 pages,
`d1700f7f7ebb6c6bd8c2fbfad927c9eee864d170108941032a37f7673c82597f`)
and Spanish 2026.09.11 (147 pages,
`df7398f8bc99927dc30c86cf5625cb08f8f38db9f3bbba685223c9c4981fa94d`).
The source files identify revision **2026.09.11**; September 24, 2026 is
the documented hotfix announcement/availability date used for this collection,
not a claim that every clause took effect individually on September 11.

Twelve missions are published with independent revision selection:

- **Crossing Lines:** Four deployment areas per map (two per player),
  two Dead Zones, two Antennas, scoring at the end of rounds and at game
  end, and the hotfix's explicit HVT/Classified exclusion (EN/ES pp. 63–66).
- **Double Bind:** Three Antennas, their Circular Template Zones of
  Influence, 4-inch central Exclusion Zone and typed, mutually exclusive
  Main Objective sets (Encryption, Sabotage and Secure Vector). The
  hotfix's selection timing, Antenna damage ceiling and Engineer/GizmoKit
  permission are preserved (EN/ES pp. 72–77). The player-facing viewer
  separates the alternative sets from Secondary and Classified scoring.
- **The Dig:** Opposite corner quarter-circle Deployment Zones, three
  diagonal Consoles, six player-placed Hyperthermal Tech Tokens, typed
  scoring, Operational Learning and classified context. The 150-point
  4-inch placement spacing, opponent's choice of analyzed Tech, ownership
  Tokens and Analyze/Neutralize restrictions match the hotfix
  (EN/ES pp. 78–82).
- **Annihilation:** Six Army-Points scoring configurations, three
  deployment geometries, enemy-kill/survival/Lieutenant scoring, No Quarter,
  HVT/Classified exclusion and the three-round end condition (EN
  pp. 125–128 and ES pp. 131–133).
- **Battleground:** Preserves the existing three scoring and geometry
  configurations with citations rebased to hotfix pp. 129–131.
- **Cutthroat:** Six-size, Lieutenant-focused Direct Action scoring, Open
  Information Lieutenants, no Loss of Lieutenant, compulsory on-table
  replacements, No Quarter and the three-round limit. Source-backed 12-inch
  (150-point) and 16-inch (200–400-point) deployment depths; EN pp. 132–134
  and ES pp. 137–139. The missing Spanish former-Lieutenant Killing
  clarification and an undefined Key Ops reference in both languages are
  preserved as source issues rather than inferred mechanics.
- **Superiority:** Four central scoring Quadrants, four Consoles, two
  end-of-round Objective Points for dominating more Quadrants (up to six),
  and one end-of-game Objective Point per Hacked Console (up to four).
  Both players can Hack and score the same Console. The mission includes
  its own Specialist Troops and Operational Learning rules, HVT/Classified
  exclusion, the three-round limit and Retreat! ending. Reuses the reviewed
  symmetric 8-/12-inch deployment depths and quarter-centered Consoles from
  core Domination without borrowing core scoring; EN pp. 135–138,
  ES pp. 140–143. The English/Spanish Shasvastii ZO-status wording
  discrepancy remains explicitly flagged.
- **Uplink Center:** Two Communication Antennas at one-quarter and
  three-quarters width and a central Tech-Coffin, each using a 40 mm physical
  Token; 12-inch (150-point) and 16-inch (200–400-point) deployment depths.
  The 10-point end-game scoring separates reversible Antenna Activation
  (2 OP each), uncontested Model-only Control of each Antenna (1 OP each),
  Control of the Tech-Coffin (3 OP) and an Active Lieutenant (1 OP).
  Covers Specialist Troops, Operational Learning, deployment contact restriction,
  HVT/Classified exclusion, three rounds and Retreat! ending. Source-pinned
  English pp. 139–142 and Spanish pp. 144–147.
- **Hardlock:** Two owner-specific Beacons at the Deployment Zone inner edges,
  three reversible-activation Consoles on the centerline and one Classified
  Objective per player. Three end-of-round Beacon Control points, seven
  end-of-game points and exact six-size SWC/deployment setup are captured.
  The source does not state a physical Beacon diameter, so those two markers
  are schematic; Consoles remain 40 mm. Differences in the Spanish/English
  pickup wording are recorded, not inferred away (EN pp. 49–52, ES pp. 127–130).
- **B-Pong:** A mobile Tracking Beacon initially at table center, two Consoles
  at quarter-width positions, symmetric 2-/4-inch Exclusion half-widths and
  12-/16-inch Deployment Zones. The mission scores Beacon Control and Control
  of at least one Console at each round end (3 OP maximum each), getting the
  Beacon entirely into the opponent's half (2 OP), and two Classified
  Objectives (2 OP). Shared typed `element-status-any` represents the
  one-point-per-round minimum-one condition without rewarding both Consoles.
  The map's schematic Tracking Beacon carries no asserted physical diameter:
  English p. 60 prints 40 mm while Spanish p. 59 prints 25 mm. Repositioning
  origins, activation restrictions, scoring timing and Magnetize wording are
  preserved as five explicit bilingual source issues (EN pp. 59–62,
  ES pp. 58–62). No Quarter removes Retreat! without changing other missions.
- **Akial Interference:** One 40 mm Akial Antenna on the table centerline,
  source-matched 8-/12-inch opposite-edge Deployment Zones and center-placement
  rulers for all six game sizes. Score up to six Common Classified Objectives,
  one point for completing more Classified Objectives at game end, one total
  point for completing at least one in each of the three Game Rounds (even if
  subsequently canceled), and two points for one Private Classified Objective.
  Rules capture round-by-round public Common cards, private selection, matching
  card redundancy, four HVTs per player, Secure HVT exclusion, Emits/Filters,
  Specialist Troops, three-round ending and Retreat! termination. The competing
  p. 95 clauses about one Emit per Trooper per round and retrying failed WIP
  Rolls are recorded as a source issue, not reconciled by inference. Sources:
  EN pp. 92–96 and ES pp. 92–96. The original publication is unchanged.
- **Evacuation:** Four schematic, fixed-position Civilians and two central 40 mm
  Extraction Consoles, on all six Army Point sizes, with 8-/12-inch opposing
  Deployment Zones. Civilians have no published physical base diameter;
  the map displays center positions without asserting one. Player-deployed
  enemy HVTs remain location-free. Score up to 4 OP for Extracted Civilians,
  2 OP for Extracted enemy HVTs, and 4 OP for two Classified Objectives.
  The mission includes the one-subject-per-successful-console-action procedure,
  Specialist Troops, Operational Learning, the three-round/Retreat! endings,
  and three recorded bilingual differences (Classified awards, first-round
  restriction and reactivation language). Sources: EN/ES pp. 88–91.

All twelve missions share the existing geometry parser, model and SVG
renderer. Source-backed circles, corner-quarter-circles and unit-convertible
placement rulers are reusable geometry primitives, not mission-specific markup.
The hotfix maps distinguish striped Exclusion Zones, violet Antenna Zones of
Influence and olive Battleground Sectors. Crossing Lines' four Deployment Zone
labels are centered, while The Dig uses two-line labels in its corner zones.
Double Bind's Antenna ruler intervals and The Dig's Console interval, centerline
and deployment-radius measurements follow the printed diagrams. Hyperthermal
Tech Tokens remain player-placed, so the map does not invent their coordinates;
their 4-inch/8-inch clearance is retained in mission rules.

The Annihilation source-issues array explicitly retains the **350-point**
gap printed in both languages: 3 OP for 176–274 and 4 OP for greater than
275 leaves 275 unassigned. The English 400-point surviving-VP threshold
is greater than **300**, while Spanish p. 132 prints greater than **30**.
This bilingual discrepancy is also recorded without treating the overlapping
Spanish threshold as a valid second scoring rule.

The three event policies remain explicitly selected, with hotfix page
references 27 (Spec-Ops), 28 (Reinforcements), and 29 (TEAM-OPS).
`tests/test_its_hotfix_scenarios.py` exercises both source revisions,
the staged database, scenario geometry, scoring bands, issue retention,
source citations and policy rebasing. The additional mission definitions
also have focused source-version, geometry and semantic tests. The published
revision-aware registry, exact selectors, and Double Bind set selection have
separate API/browser tests. Source page comparisons and local light/dark previews are supported by
`python -m tools.research.render_its_map_previews --config 300-400-points`,
which writes only under ignored `local/work/its/map-previews/`. The PNG
rasterization tool approximates Exclusion hatching because MuPDF does not
support its SVG pattern; the shipped SVG retains that pattern. Final in-browser
visual review at relevant breakpoints remains a release-acceptance check;
no historical or tournament context is silently replaced.

## Schema v2 and read contract

The database has a distinct SQLite application ID (`0x49445331`) and
`user_version=2` (v1 was an unhosted pilot, superseded by dedicated
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

The reviewed ITS curated document stores `seasonPolicies`
outside `records`. The Rules exporter therefore does not
import event constraints as N5 rules or broaden its interaction-audit scope.
The ITS builder separately validates exact `(seasonId, revision, context)`,
typed `rules-n5` targets, source citations, review provenance and effect
kind. `select_its_policies` returns policies only for a supplied season,
exact revision and explicit play/Extra context; a missing or incorrect
context never causes the policy to apply by default. Cross-database target resolution and overlay presentation use the
publication registry and the selected N5 Rules database.

## Local commands

From the repository root, with the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m tools.data.build_its_season
.\.venv\Scripts\python.exe -m tools.data.build_its_season --check
.\.venv\Scripts\python.exe -m tools.data.build_its_season --output local/its_18.db
```

The standalone developer tool still defaults to the ignored
`local/work/its/its_18.db` and cannot overwrite the tracked runtime artifact.
Use `infinity-db build --compact` to regenerate the complete
`army.db` / `rules_n5.db` / `its_18.db` /
`its_18_2026.09.11.db` set. The builder first validates
all three outputs and their cross-publication references, then replaces the
selected files. A changed or invalid source before replacement preserves
the previous outputs. Identical builds produce byte-identical SQLite data.

The test module `tests/test_its_season_database.py` covers the
production ITS 18 schema, deterministic bytes, citation and geometry
preservation, exact selection, drift, core compatibility, corruption
and safe replacement. The `tests/test_its_multiseason.py` module uses
a temporary, explicitly **synthetic** ITS 17 document and SQLite file
to prove multiple independent seasons with the *same* Battleground
slug, different publication content, isolated policy/citation sources,
FAQ selection, cache fingerprints, ETags and invalid registration
behavior. It is not an assertion about actual Season 17 rules.

## Publication registry and selected runtime

`src/infinity_db/publication_registry.py` provides typed
`PublicationReference(domain, record_id, revision)` selection and
`PublicationRegistry` for registered season files. Registration validates
the ITS core revision and all cross-domain policy and scenario references
against current N5 definitions. `season_policies` returns resolved targets
only for an exact season, revision and explicit play context. The validated
manifest exposes publication identity and SHA, not physical paths.

`ScenarioCatalog` uses the registry for ITS-owned publications, while
N5 core missions continue to use Rules. The complete-set factory registers
`its-18` from `its_18.db` and `its-18@2026.09.11` from
`its_18_2026.09.11.db`, validates the four-file set, and resolves
both through exact `(season, revision)` selection. The version-qualified
internal registration key never leaks into public collection identifiers. Both local `serve` and production WSGI/Docker use this same factory;
the runtime cache fingerprint includes all three exact file hashes.
The HTTP API retains its existing collection/revision selectors; unknown
seasons/revisions never fall back to core. The internal explicit
`create_app(..., season_databases={"its-18": path})` remains useful for
isolated parity tests.

## Multi-season isolation and growth

The isolated ITS builder/inspector derives the owner from the validated
`scenarioCollection.id` and requires a matching
`its-season-<season-number>-` source collection and exact record/policy
scope. A second season can be built and registered independently without
modifying N5/Army storage, overriding another season or creating
alternate renderers. Reused `scenario:battleground` identities are resolved
by their registered season and revision, not by slug alone. An absent or
mismatched owner, missing N5 target, stale revision, unregistered source
or altered source/geometry fails closed.

**The production release intentionally uses four files:**
`army.db`, `rules_n5.db`, `its_18.db` and
`its_18_2026.09.11.db`. The selected set does not autodiscover
additional files. Adding another season or revision requires its own
reviewed source, explicit registration, recorded build input and packaging;
the synthetic ITS 17 test database is never published.

## Migration boundary

The Rules exporter excludes ITS-owned curated collections, so Battleground
and its scenario membership now exist in `its_18.db` only. The selected
four-file runtime resolves both season revisions through the registry. A pinned
pre-cutover digest independently guards six Battleground JSON payloads and
24 SVG maps; the isolated ITS reader remains comparable to the real HTTP
response without retaining a second Rules-owned record. N5 scenario facts,
source attribution and shared renderer behavior remain unchanged.

The N5 Spec-Ops and Request SpecBall cards no longer duplicate ITS 18
tournament and TEAM-OPS restrictions. The season database remains the sole
authority for those reviewed policies, including the optional
Reinforcements Extra availability. `GET /api/season-policies` requires
`season_id` and `season_revision`; without an explicit `context` it
returns only the authored available context names and **no applied policies**.
Selecting an exact play context returns the season-owned effects, target and
citations, optionally filtered by typed `target_id`. Unknown contexts,
seasons and revisions return no policies; malformed selectors return 400.
The ITS scenario page offers a context selector with no selection by default.
It does not add tournament restrictions to core/free play automatically.

The N5/Spanish SpecBall printing discrepancy stays in the core card, and
the Reinforcements annex preserves its N4-origin procedural caution.
Core Scenario marker dimensions remain unchanged; their external ITS 18
p. 17 citation is resolved against the selected season source descriptor in
the complete runtime. The N5 FAQ remains N5-owned: source- and
scenario-scoped rulings cannot leak into an unrelated ITS mission with a
reused scenario ID, while rules-wide N5 FAQ applies to a valid selected
season. Exact season/revision/mission selection fails closed when unregistered.
No ITS-authored FAQ is inferred. Changing maintained `src/` or curated files
changes the complete build fingerprint;
regenerate the four-file release set before source-bound deployment
checks or merge.

For the ownership and scope exceptions (Spec-Ops, TEAM-OPS,
Reinforcements, marker citations, FAQ), see
[season publication ownership](season-publication-ownership.md).
