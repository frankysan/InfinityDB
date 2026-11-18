# ITS Season 18 SQLite database

**Project domain:** Data processing

Schema v2 participates in the complete three-file build and serving set:
Army, Rules and the current ITS Season 18 publication. This page owns the ITS
database format, selection and build contract; release acceptance belongs in
[releasing](releasing.md).

The ITS season database is an independently validated, deterministic SQLite
artifact created from reviewed curated ITS facts. The implementation lives in
`src/infinity_db/its_season_database.py` and the revision projector in
`src/infinity_db/its_source_family.py`, with the developer entry point in
`tools/data/build_its_season.py`.

## Current source and scope

- **Input:** `data/curated/its/n5-its-season-18.json`, one maintained
  source-family file with explicit per-fact revision tags and field-level
  historical overrides. The original 2026.09.01 source-file hash
  (`f002d279f711c5ac27e87cc3e91686beb85ec4e42aa7a740e2cebab1c4b2bbab`)
  and its reviewed Battleground/policy facts are preserved inside this file.
- **Current publication:** `its-season-18-2026.09.11`, season `its-18`,
  effective 2026-09-24 and published in `its_18.db`. **No historical ITS
  database or player-facing revision selection is maintained.**
- **Required core revision:** N5 `5.3`, recorded as an explicit compatibility
  declaration. Complete-set validation resolves ITS dependencies against the
  selected Rules database and verifies the source identity against the
  Army/Rules build manifest.
- **Currently authored:** Twenty reviewed source-cited hotfix missions,
  six Army Points configurations per mission, and three ITS-owned event policies
  for Spec-Ops, TEAM-OPS and optional Reinforcements. These policies are
  **not** new N5 core Rule definitions. There is no ITS-authored FAQ publication.
- **Public selection:** Choose ITS Season 18; the current 2026.09.11 revision
  resolves automatically. Older explicit revision links fail closed without
  silently displaying replacement facts. Historical browsing remains deferred.
- **Scenario Skills:** Mission rules with `skillTypeIds` and `skillFacts`
  project to standard Skill cards, `/skills` and Search. All 26 reviewed ITS 18
  actions have structured Requirements and Effects, with optional Restrictions,
  Clarifications and Source context. Original mission paragraphs and action
  titles remain available for provenance and compatibility. Public Skill names
  omit redundant terminal `(Short Skill)` and `(Long Skill)` labels because
  their typed badges convey that classification. Their public IDs include the
  season and scenario, so same-named actions are not conflated. Optional
  `skillCitations` identify exact source pages only where already supported
  by reviewed action evidence (currently three actions); the others retain
  explicitly mission-wide page ranges. Core N5 scenario Skills are resolved
  independently from their scoped Rules definitions, not imported into ITS.

**Implemented optional authoring slice (no deployed migration):** The ITS
builder accepts a `shared_library` path; the standalone developer command
accepts `--shared-library`. A source declares `sharedScenarioLibrary` with
exact `id` and `sha256`. A membership with `sharedDefinition` supplies
`version`, season-local `citations`, `review`, `componentCitations` keyed
by typed component IDs, and an `overrides` array. Each override has an exact
`target` scenario ID, allowlisted `field` and `value`. Only the scenario
summary and individual `facts.playRequirements` counts are currently allowed.
The referenced library declares format `InfinityDB shared scenario library`,
formatVersion 1, its matching `id`, and versioned `definitions`; each
contains an exact typed `id`, `version`, originating collection/season/revision
and source IDs, original `record`, and optional versioned `components`.
All imported components must have publication-owned citations and pinned
`version` references in their definitions. The resulting standard records
are fully validated and materialized into **unchanged schema v2**, with
origin metadata separately preserved in the scenario payload. The selected
library hash joins the build identity. No runtime database or external source
file lookup is required when serving the result.

**Cross-scenario components (synthetic acceptance):** That library may
add a top-level `components` array containing one canonical pinned
`{id, kind, version, payload, citations, scenarios}` definition for
each reusable setup, geometry, objective or end condition. Multiple
scenario definitions reference it with `{ref, version}` entries in
their `components` lists. Unknown/unused versions, unsupported scopes,
conflicting same-ID payloads, and same-season local ID collisions fail
closed. Each season's `sharedDefinition.componentCitations` binds
its own exact source pages per scenario. Compilation creates one
season-local component definition with explicit scope but emits
`componentSources` using only the citing scenario's pages, avoiding
source leakage between neighboring scenarios. The compiled SQLite
schema and public mission payloads are unchanged. This capability
does not by itself establish that any ITS 17/18 components are
semantically identical; actual reuse awaits source review.

An optional `skills` array in that same pinned library holds canonical
`{id, version, origin, payload, citations, review}` entries. Each Skill
`payload` contains `skillTypeIds` and `skillFacts`. The season-owned
`sharedSkillBindings` entries specify `{id, version, scenarios, citations,
review}`; the corresponding scenario rules use `skillDefinition: {ref,
version}`. Skill citations and review are independently pinned to the selected
season, rather than inherited from the originating source. The existing
`ScenarioComponents` composer materializes them before validation, preserving
the legacy scenario action IDs and typed `sharedSkill` metadata. Repeated,
semantically identical Skill definitions project to one canonical Skill in
catalog and Search, with explicit scenario/season applicability; legacy
season/scenario Skill routes and cards continue to work. Conflicting facts or
versions are rejected rather than silently merged.

**Season-wide ITS Skills (implemented):** ITS 18 2026.09.11 publishes
CivEvac (Common Basic Short Skill, pp. 22–23), Casevac (Common Short
Skill, p. 25), Team-Ops (Automatic Special Skill, p. 30) and Request a
Tacball (Attack Short Skill, pp. 30–31). All four are independent,
reviewed `kind: skill` records without scenario IDs, stored in the
existing ITS SQLite `records` table (schema v2). They have explicit
`facts.applicability: {context, revision}` values and version-tagged
historical citations for 2026.09.01. The current ITS database validation
checks record types, counts, citations, content hashes, and season/revision
applicability; the Skill catalog and Search expose their standard cards.
The Team-Ops tournament Extra (p. 29) remains distinct from the Special
Skill, and both Team-Ops and Request a Tacball are scoped to that Extra.
Casevac State (pp. 25–26) is a separate `kind: state` ITS record, with
source-cited activation/effects/cancellation conditions and an independent
`/states/casevac` card. `/skills/casevac` links to that State and the State
links back to the Skill. Historical 2026.09.01 citations use pp. 24–25.
The State catalog merges registered ITS States for presentation but never
writes them into or infers them from the core Rules database. It rejects
ambiguous route identities; cross-season State deduplication needs separately
reviewed evidence before a second season reuses the same typed ID.

**Reusable season-level memberships (synthetic cross-season acceptance):**
A pinned shared library can additionally declare a top-level
`sharedSeasonSkillBindings` array with exact `{id, version, name, summary,
category, applicability, citations, review}` objects. Unlike
`sharedSkillBindings.scenarios`, this requires no scenario action. The
definition's Skill types and structured facts are materialized into a
season-owned, source-cited Skill record; same-identity equivalence across
seasons consolidates in catalog/Search only when exact pinned origin and
facts match. Each season's compiled SQLite still serves independently.
No published ITS 18 Skill has yet been migrated into a shared library;
real ITS 17 reuse requires independently reviewed source equivalence.

**Initial ITS 17/18 source comparison (2026-11-18; not an ITS 17 import):**
The official [ITS 17 English PDF v1.0.2](https://downloads.corvusbelli.com/infinity/organized-play/its-rules-season-17-en-v1.0.2.pdf)
(labels itself V0.2 and includes Outbreak in its changelog) calls CivEvac
and Casevac **Short Movement Skills** in the season-wide rules.
The pinned ITS 18 2026.09.11 English PDF calls CivEvac a **Basic Short
Skill** (p. 23) and Casevac a **Short Skill** (p. 25). Matching
Requirements/Effects prose is therefore insufficient for one shared
Skill definition/version; the declared type is part of its semantics.
The ITS season Skill validator and catalog now support the historical
`short-movement-skill` designation, displaying "Short Movement Skill"
without adding it to the current N5 core declaration matrix. Synthetic
cross-season tests verify its independent API presentation. When one
canonical Skill has distinct, explicitly pinned definition versions from
the same reviewed library origin, the newest season retains the established
unqualified `/skills/<slug>` route and older versions get season-qualified
`/skills/its-17-<slug>` routes, with their own typed facts, applicability
and citations. Registration order does not change route choice. Equivalent
same-version facts still consolidate; changes under the same pinned
version or unpinned identity collisions fail closed. No real ITS 17
publication or historical revision browsing is activated.

ITS 17 Outbreak awards 1 point for Stabilizing the Alpha Infected and
1 point for CivEvacing the Stabilized Alpha. ITS 18 Outbreak (p. 83)
omits the standalone Stabilized-Alpha objective and awards 2 points
for CivEvacing the Stabilized Alpha. This is a changed objective set,
not merely a point-value override: **do not reuse an identical version**
of the entire Outbreak scenario. ITS 17 also requires player-placed
Infected to be 8 inches apart *from each other*, while ITS 18 p. 84
says *from all other Infected*; this changed placement scope needs its
own reviewed rule/component version. Both publications restrict CivEvac
to **one Infected** in Outbreak (ITS 18 p. 84), whereas the general
ITS 18 CivEvac rule permits **two Civilians** (p. 23). Evacuation
(ITS 18 pp. 88–90) applies the general CivEvac rule but requires a
separate successful Extraction Console action for extraction. These
contextual rules must not be moved into the globally shared Skill.
The ITS 18 optional Team-Ops Extra and its two Skills must not be
assumed applicable to ITS 17. The comparison is partial: full scenario/geometry/effect parity
remains outstanding.

**ITS 17 source revisions and verified overlap (2026-11-18):**
The canonical ignored archive is now
`local/data/pdf/legacy/its_17/`, containing the original English and
Spanish PDFs at **V0.0, V0.1 and V0.2** (six distinct source files).
`tools.research.acquire_its_pdf.PINNED_REVISIONS` records each exact
SHA-256, size and PDF page count; run
`python -m tools.research.acquire_its_pdf --verify-set` to check all
six locally without network access. PDF pages per edition are
V0.0 EN 68 / ES 67, V0.1 EN 68 / ES 67, and V0.2 EN 105 / ES 112.
To inspect a historical diagram, run
`python -m tools.research.render_its_source_pages its-rules-season-17-v0.2-en.pdf --source-set its17 --pages 55`.
The older download URL ending `v1.0.2.pdf` resolves to exactly the
same **V0.2 English** bytes (SHA-256
`73a184b80535f23499000bb81112d95168c12f970fa14a30050a95ec51cdfe71`)
as the renamed `its-rules-season-17-v0.2-en.pdf`; this is **not**
an additional rules revision. The existing acquisition key
`its-17-en-v1.0.2` remains compatible but now uses this canonical
destination. No source PDFs are tracked or required by CI.

**Revision-specific scope:** V0.1's English and Spanish changelogs
explicitly change the Casevac Skill type; on p. 14, English changes
from **Short Skill** (V0.0) to **Short Movement Skill** (V0.1),
while Spanish changes from **Habilidad Corta** (V0.0) to
**Habilidad Corta Básica** (V0.1). V0.2 retains these respective
labels (EN p. 19 / ES p. 20); the English/Spanish classifications
are **not literal equivalents** and their intended rule
equivalence requires review. These type changes must be tagged by
revision if V0.0/V0.1 facts are ever curated; the existing ITS 17/18
comparison below applies specifically to **V0.2**, not all ITS 17.
V0.1 also renames Zone of Interest to Area of Interest and records
several mission corrections in its changelog. V0.2's changelog
introduces **Outbreak**, absent from V0.0/V0.1; its mobile layout
changes PDF pagination and should not be used to backfill older
source-page citations. No older source revision is separately
selectable in the application.

The V0.2 ITS 17 table of contents (PDF p. 2) has **16 scenario names
also present** among ITS 18's 20 published missions. The four
ITS 18-only names are Double Bind, The Dig, Neutralization and
Data Harvest. Shared titles establish availability candidates,
**not** semantic equivalence.

Focused reviewed comparisons against the pinned ITS 18 English
2026.09.11 original:

- **Evacuation** (ITS 17 pp. 55–58; ITS 18 pp. 88–91):
  both have 1 OP per Extracted Civilian/enemy HVT and two Classified
  Objectives worth 2 OP each. Visual review confirms matching
  150/200–250/300–400-point deployment maps, four fixed Civilians,
  two Extraction Consoles, and their dimensions/positions. The
  English Activate Extraction Console action has the same
  first-Game-Round restriction. **Geometry, setup and mission-action
  reuse are candidates**, but the season-wide CivEvac Skill must
  keep its separate historical declaration type and source pins.
  `tests/test_its_cross_season_source_review.py` locks the reviewed
  ITS 18 scoring and positions without requiring the local ITS 17
  PDF in CI.
- **Battleground** (ITS 17 pp. 83–85; ITS 18 pp. 129–131):
  ITS 17 awards 1/3/4 OP for near/central/far Sectors and adds
  Key Ops killing (2 OP) or threatening (1 OP); ITS 18 awards
  2/3/5 and removes the Key Ops objectives. The 4-/8-inch
  sector depths and 2-/4-inch center offsets match, making
  **sector geometry** a candidate, **not** the complete scenario
  or objective definitions.
- **Superiority** (ITS 17 pp. 89–92; ITS 18 pp. 135–138):
  ITS 17 caps Hacked Console scoring at 3 and grants 1 bonus OP
  for a Dominant Key Ops. ITS 18 contains four Consoles and
  omits that Key Ops objective. Preserve distinct scoring versions;
  Quadrant geometry and generic ZO rules are candidates only.
- **Cutthroat** (ITS 17 pp. 86–88; ITS 18 pp. 132–134):
  ITS 17 has two Key Ops scoring conditions. ITS 18 instead
  awards 4 OP for Lieutenant-caused kills and drops those
  objectives. The remaining Key Ops wording in ITS 18's Killing
  paragraph is an **existing recorded source issue**, not grounds
  to restore the historical Key Ops mechanics.
- **Outbreak** (ITS 17 pp. 68–71; ITS 18 pp. 83–87):
  the separately reviewed Alpha scoring and Infected spacing
  changes above require separate objective/rule versions.

**Real ITS 17 Evacuation, Hardlock, Uplink Center and Battleground (2026-11-18):**
`data/curated/its/n5-its-season-17.json` is a standalone, **unregistered**
ITS 17 V0.2 curated season source. It has reviewed
`scenario:evacuation`, `scenario:hardlock`, `scenario:uplink-center`
and `scenario:battleground` memberships pinned to
`data/curated/its/shared/its17-scenarios-v1.json`, with the source
SHA-256 in `sharedScenarioLibrary`. The shared library owns the
complete historical scenario definitions (format version 1) and the
season document owns the source-specific memberships and citations.
The original V0.2 Evacuation English pp. **55–58** and Spanish pp. **50–53**
support its mission, six army sizes / three maps, two Extraction
Consoles and scoring. Per-language Classified scoring, opening
activation timing and cross-player Console reactivation ambiguities
retain historical page references rather than inheriting ITS 18's.
ITS 17's Console description says to use a Console A Token or
scenery of the same diameter; it does **not** independently specify
a 40 mm diameter in this mission's text, so the separate ITS 18
40 mm assertion is not carried into the historical rule prose.

Hardlock independently matches ITS 18's six-size scoring, three geometry
configurations, two scenario Skills, Specialist Troops and end conditions.
ITS 17 EN pp. **59–62** and ES pp. **54–57** supply eight season-local
citations. Its original map and text specify 6/8/12-inch offsets for
side Consoles and owner-specific Beacons at the Deployment Zone inner
edges. The ITS 17 mission refers to a Console A Token or equal-diameter
scenery but does not itself assert ITS 18's explicit 40 mm scenery size.
Both editions preserve EN/ES differences concerning a Connected versus
Activated Console and the Normal State of a transferring Beacon carrier.
ITS 17's one Tactical Support Option belongs to historical play context,
not a current ITS 18 rule.

Uplink Center independently matches ITS 18's four scoring conditions,
12-/16-inch Deployment Zones, three geometry configurations, Communication
Antenna activation, Tech-Coffin Control, Operational Learning, Active
Lieutenant and end conditions. ITS 17 EN pp. **93–96** and ES pp. **99–102**
supply eight season-local citations. The 6/8/12-inch Antenna offsets and
central Tech-Coffin agree across the printed maps; the original ITS 17 text
requires Tokens or scenery of matching diameter, without separately
specifying ITS 18's 40 mm. ITS 17 ES p. 100 omits **350** from the
300/350/400-point Antenna placement grouping; both source maps and EN p. 94
include 350. The discrepancy remains source-local rather than inventing a
fourth configuration. ITS 17's zero Tactical Support Options likewise belong
to historical play context.

Battleground is **not the same scenario definition across seasons**.
Reviewed ITS 17 V0.2 EN pp. **83–85** / ES pp. **88–90** award
**1/3/4 OP** for near/central/far Sectors rather than ITS 18's
**2/3/5 OP**, plus one mutually exclusive Key Ops award: **2 OP** for
Killing, or **1 OP** for Threatening the opposing Key Ops. One
`enemy-key-ops` objective with `aggregation=exclusive`,
`maximumPoints=2` and distinct 2-/1-OP reviewed-prose award
conditions represents these alternatives without treating them as
additive or inventing an automatic Key Ops scoring engine. Both
season maps use identical 4-/8-inch Sector geometry, but the shared
historical definition substitutes the correct **1/4 OP** map labels
for each side. ITS 17 adds Key Ops designation (eligible deployed
Models, no Irregular or REM; English also excludes VH), Dodge (+3),
Tactical Awareness and Threaten criteria that do not appear in ITS 18.
The EN/ES **VH exclusion** difference and distinct **Shasvastii
Unconscious/non-Null versus Normal/Embryo** wording remain explicit
source issues. Only matching Sector, Domination, Baggage, Killing and
round-limit rules are carried across. The archived database is still
unregistered and the current ITS 18 record is unchanged.

Build and check the independent SQLite output without registering it:
`python -m tools.data.build_its_season --source data/curated/its/n5-its-season-17.json --shared-library data/curated/its/shared/its17-scenarios-v1.json --output local/work/its/its_17_reviewed.db`
(and add `--check` to inspect the existing result). The authoring
bootstrap `python -m tools.research.bootstrap_its17_evacuation`
**refuses to overwrite** these human-reviewed JSON files; the one-time
`tools.research.extend_its17_hardlock` and
`tools.research.extend_its17_uplink_center` and
`tools.research.extend_its17_battleground` migrations are not build steps.
Exact source pins and independent SQLite reproducibility have focused
regression tests in `tests/test_its17_evacuation_publication.py` and
`tests/test_its17_hardlock_publication.py` and
`tests/test_its17_uplink_center_publication.py` and
`tests/test_its17_battleground_publication.py`. Existing ITS 18
curated facts remain unchanged; this ITS 17 season is **not yet
registered for web publication**. A separate versioned shared
component extraction can follow after the rule-inclusion format is
reviewed: the existing typed v2 composer requires rule references,
not the inline narrative/Skill facts present in the reviewed
Evacuation, Hardlock, Uplink Center and Battleground missions.
The accepted migrations therefore reuse complete v1 scenario definitions, without claiming fine-grained
component or Skill deduplication yet.

The remaining shared-name missions and cross-language parity
still need targeted review before adding their historical memberships
or promoting additional shared definitions.

Optional `sharedSkillBindings.overrides` entries use exact
`{scenarioId, ruleId, field, value}` objects. Only complete prose-array
replacement of one Skill's Requirements, Effects or Restrictions is supported.
Each override is constrained to a declared season/scenario Skill binding and
inherits that binding's reviewed season-local evidence. The materialized
`sharedSkill.overriddenFields` identifies intentional variants; these remain
distinct in catalog and Search rather than being merged with the shared base
definition. Unchanged actions still consolidate by exact identity.

A source-family file can replace one local scenario record with a shared
membership while retaining that scenario's exact `factRevisions.records` tag
and historical field overrides. A synthetic ITS 18 test confirms that both
2026.09.11 and 2026.09.01 projections preserve the corresponding facts and
membership ordering.

**Complete-set registration (implemented; opt-in):**
`SEASON_DATABASE_SOURCES` continues to register each shipped season and its
curated source. A season that imports shared definitions also explicitly
registers a library under `SEASON_SHARED_LIBRARY_SOURCES` in
`src/infinity_db/database_set.py`, using a repository-relative
`data/curated/its/shared/*.json` path. The complete-set builder passes
the library to the existing standalone ITS builder. The shared library is
included in the curated JSON input manifest; complete-set validation verifies
that the selected season database has the registered library SHA-256 recorded
in the matched Army/Rules build inputs. Unregistered libraries and missing or
mismatched pins fail closed. The deployment asset check verifies the actual
library file and current ITS builder revision. The compiled database still
serves independently without an on-disk authoring library. New libraries must
retain byte-stable LF source text across systems, matching the repository
`.gitattributes` policy and exact library SHA-256 pins.

The current registration is empty: **ITS 18 remains source-local and the only
registered production season**. A synthetic ITS 17 fixture verifies the
complete-set builder's registration path, rejection of missing/modified library
bytes, and independent SQLite output. No current content migration or runtime
schema change is implied.

This is proven on synthetic single-season, two-season and revision-tagged
fixtures, **not** reviewed ITS 17 data. Generic component overrides and
real migrations remain [unfinished](TODO.md#its-scenarios-and-game-tools); see the
[canonical data model](data-model.md#accepted-cross-season-scenario-and-skill-reuse).

### Published 2026.09.11 hotfix curation

The Rules exporter does not import ITS-owned sources. The unified ITS curation
tracks English/Spanish 2026.09.11 hotfix facts as current, while keeping
2026.09.01 Battleground and policy evidence internally for possible future
historical replay. The player-facing list contains only one ITS Season 18
collection with all twenty current reviewed missions.

The selected hotfix source binds English 2026.09.11 (142 pages,
`d1700f7f7ebb6c6bd8c2fbfad927c9eee864d170108941032a37f7673c82597f`)
and Spanish 2026.09.11 (147 pages,
`df7398f8bc99927dc30c86cf5625cb08f8f38db9f3bbba685223c9c4981fa94d`).
The source files identify revision **2026.09.11**; September 24, 2026 is
the documented hotfix announcement/availability date used for this collection,
not a claim that every clause took effect individually on September 11.

All twenty missions are published for the current 2026.09.11 revision:

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
  The shared ITS token diameter chart specifies 25 mm Beacons (EN p. 18).
  Consoles are 40 mm. Differences in the Spanish/English
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
- **Neutralization:** Two central 40 mm Tech-Coffin Hyperthermal Tech Boxes,
  four 40 mm Neutralizing Antennas and four Circular Template Neutralization
  Areas (radius 2.5 inches), each centered on an Antenna on the near edge of
  a Deployment Zone. Six Army Point sizes share three geometry configurations,
  with 8-/12-inch Deployment Zones and a central 4-inch half-width Exclusion
  Zone. Scoring: 1 OP per Neutralized Hyperthermal Tech (up to 4 OP), 1 OP
  for Neutralizing more Techs, 3 OP for Controlling more Antennas, and 2 OP for
  one Classified Objective. Rules cover extraction, Stun Ammunition on pickup,
  carrying/dropping, Neutralization at the end of an Order or ARO, and Model-only
  Antenna Control. The source does not define the number of Techs extractable
  per Box; the Spanish rules also omit an English Marker State prohibition.
  Both remain explicit source issues (EN/ES pp. 105–109).
- **Provisioning:** Three 40 mm Tech-Coffins on the table diagonal, at
  source-backed 8-/12-/16-inch center spacing for three game-size maps,
  with corner quarter-circle Deployment Zones. The central Coffin holds two
  Supply Boxes and the other two hold one each. Players place two Circular
  Template Safe Areas outside Deployment Zones, so those positions are not
  invented on the map. Game-end scoring awards up to 4 OP for controlled Boxes,
  3 OP for the greater Safe Area count (or 1 OP for a nonzero tie), 2 OP if the
  opponent controls no Boxes in their Safe Area, and 1 Classified OP.
  Five bilingual discrepancies about emptied Coffins, pickup scope,
  fully-inside deposition, extraction contact and Reinforcements suitability
  are retained (EN pp. 110–114; ES pp. 110–115).
- **Area of Interest:** One 40 mm Communication Antenna at the table
  center and corner quarter-circle Deployment Zones for all six game
  sizes. Three player-placed Circular Template Areas of Interest, including
  one Special Area, must lie entirely outside Deployment Zones and must not
  overlap; the map does not invent their positions. Score up to 3 OP for
  Dominating Areas at game end, 3 OP for Dominating the Special Area at
  round ends, 3 OP for holding the Activated Antenna at round ends and
  1 Classified OP. The mission defines opposing enemy-Hacker AROs,
  domination rules for Shasvastii and Baggage, and INTELCOM Support and
  Control. Three bilingual issues preserve differences concerning Hacker
  ARO obligation, INTELCOM timing and the antenna's physical diameter
  (EN pp. 121–124; ES pp. 122–126).
- **Data-Harvest:** Three fixed 40 mm Tech-Coffins on the centerline,
  centered or 4 inches from each table edge, contain six 25 mm
  Data-Harvesters total. Players place four Circular Template Designated
  Zones: each side's one Zone is fully within the enemy Deployment Zone,
  and the other is outside that Zone but within the enemy half. Their
  exact placements are not invented in geometry. Source-backed opposite
  Deployment Zones are 8 inches deep at 150 points and 12 inches at
  200–400 points. The mission awards 2 OP for a Data-Harvester Active
  inside the enemy Deployment Zone, up to 3 OP for activation in an
  enemy-half Zone at each round end, 2 OP for denying all enemy active
  Harvesters at game end, 1 OP for activating both own Zones while denying
  the opponent, and 2 Classified OP. It defines extraction, carrying,
  activation, neutralization, specialist restrictions and Retreat! ending.
  Two bilingual source issues preserve base-versus-Silhouette contact
  for extraction and neutralization (EN/ES pp. 67–71).
- **Last Launch:** Two 40 mm ID Scanners along the centerline, one central
  40 mm ID Checker and an 8-inch-square Launching Tower shown as a distinct
  No Deployment Zone, with open Wide Gates described in the mission rules.
  Three source-backed map configurations cover all six Army Point sizes;
  the tower is central, its Scanners have exact lateral placements, and
  the Deployment Zones use 8-/12-inch depths. Scoring compares extracted
  Army Points (2 OP), extracted Specialists (2 OP), killed Specialists
  (2 OP for more, or 1 OP for a tie), Tower Domination (1 OP), and three
  Classified Objectives (3 OP). Downloading/transferring ID Tokens,
  extracting Troopers and eligible Peripherals, Victory Points,
  Baggage/Shasvastii, Loss of Lieutenant, No Quarter and the three-round
  end condition are documented. Three source discrepancies preserve the
  English/Spanish tower-size, gate-access and Peripheral-point wording
  (EN pp. 115–120; ES pp. 116–121).
- **Corporate Appropriation:** Two fixed 40 mm Prototypes at quarter-width
  centerline positions, two 40 mm Panoplies at the Deployment Zone inner
  edges, and a central striped 4-inch-per-side Exclusion Zone. All six
  game sizes use the 8-/12-inch Deployment Zone depths and three source
  map configurations. Opponents capture each other's Prototypes or
  destroy their own; the 3 OP Destroyed-own-Prototype outcome is
  mutually exclusive with the 1 OP intact-and-uncaptured outcome. Other
  awards cover capturing the enemy Prototype (2 OP, plus 1 OP if home),
  more Panoply acquisitions (1 OP), and three Classified Objectives
  (3 OP). The curation includes the ARM/BTS/STR/ADS defense Profile,
  Anti-materiel/D-Charge restrictions, carrying and dropping, the
  complete D20 Panoply Chart, and both three-round/Retreat! endings.
  Three bilingual differences remain explicit: targeting restrictions,
  ADS CC MODs, and capture disqualification when contacting enemy
  Models (EN pp. 53–58; ES pp. 52–57).
- **Outbreak:** Five Infected Civilians, including one fixed Alpha Infected
  at table center. Each player places two other Infected in the opposing
  half before deployment and one Circular Template Stabilization Zone
  inside their own Deployment Zone. Their exact player-selected
  positions are not invented on the map. Three corner-quarter-circle
  configurations cover all six game sizes; Side A is top-right, Side B
  bottom-left, with radii of 12, 20 or 24 inches. Scoring: up to 3 OP
  from Scans, 2 OP for Stabilizing more Infected, 2 OP for CivEvacing
  more Stabilized Infected, 2 OP for CivEvacing the Stabilized Alpha,
  and 1 OP for Securing an Infected. There are no Classified Objectives.
  The rules include ownership of Stabilization, per-player Scan limits,
  end-of-turn zones, the Doctor/Paramedic +1SD bonus, CivEvac, HVT
  exclusion and both mission endings. English 4-/8-inch versus Spanish
  10-/20-cm minimum placement distances are preserved as a bilingual
  source issue (EN/ES pp. 83–87).
- **Critical Intervention:** Fixed Attacker (first Turn, Side A) and
  Defender (second Turn, Side B) roles have different Main Objectives;
  this is not a Double Bind-style selection. Both sides use 8-/12-inch
  deployment depths, a central 4-inch-per-side Attacker Exclusion Zone
  and an 8-inch square Server Room, which is normally a No Deployment
  Zone. Its schematic two Armed Turrets have no published physical
  diameter; the central 40 mm Data Console and Defender-side 40 mm
  Inhibitor Antenna have physical marker dimensions. The Defender may
  spend one additional pre-deployment Command Token to activate the
  Defense System or deploy up to 65 Army Points in the room. Attacker
  scoring covers unlocking and extracting the Data Pack, extractor
  survival and return, Server Room Domination and size-dependent kills;
  Defender scoring covers preventing both actions, killing the
  extractor, Domination and a different set of kill thresholds. Both
  may score one Classified Objective or select an INTELCOM card.
  **The published Defender awards total 12 OP** while the Attacker
  awards total 10; both languages agree, and the data does not impose
  an invented 10-OP cap. The mission includes Turret Profile and
  reactions, WIP-6 extraction (no -6 when Unlocked), Inhibitor
  activation, INTELCOM Support and Control, Shasvastii/Baggage,
  Specialist restrictions and mission endings. Six source issues
  disclose bilingual room size, Exclusion width, Shasvastii status,
  STR, INTELCOM point terminology and the 12-OP anomaly
  (EN/ES pp. 97–104).

All twenty missions share the existing geometry parser, model and SVG
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
`army.db` / `rules_n5.db` / `its_18.db` set. The builder validates
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
`its-18` from the current `its_18.db`, validates the three-file set,
and resolves an ITS season selection to its sole published revision.
Both local `serve` and production WSGI/Docker use this same factory;
the runtime cache fingerprint includes all three exact file hashes.
The HTTP API accepts season-only selection by default and may validate an
explicit revision in an older link; unregistered revisions never fall back
to core or silently show current facts. The internal explicit
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

**The production release intentionally uses three files:**
`army.db`, `rules_n5.db` and `its_18.db`. The selected set does not
autodiscover additional files. Adding another season requires its own
reviewed source, explicit registration, recorded build input and packaging;
a new revision of ITS 18 updates its curated source family and current build.
The synthetic ITS 17 test database is never published.

## Migration boundary

The Rules exporter excludes ITS-owned curated collections, so current
Battleground and its scenario membership exist in `its_18.db` only. The
three-file runtime publishes the hotfix revision. Historical Battleground
facts, original citations and source identity remain in the curated family
but are not served. N5 scenario facts, source attribution and shared renderer
behavior remain unchanged.

The N5 Spec-Ops and Request SpecBall cards no longer duplicate ITS 18
tournament and TEAM-OPS restrictions. The season database remains the sole
authority for those reviewed policies, including the optional
Reinforcements Extra availability. `GET /api/season-policies` requires
`season_id` and `season_revision`; without an explicit `context` it
returns only the authored available context names and **no applied policies**.
Selecting an exact play context returns the season-owned effects, target and
citations, optionally filtered by typed `target_id`. Unknown contexts,
seasons and revisions return no policies; malformed selectors return 400.
The ITS scenario page displays the current publication's policies in separate
cards for official tournaments and each Extra, with each card scoped to its
own play context. Core scenario pages do not display these cards.

The N5/Spanish SpecBall printing discrepancy stays in the core card, and
the Reinforcements annex preserves its N4-origin procedural caution.
Core Scenario marker dimensions remain unchanged; their external ITS 18
p. 18 citation is resolved against the selected season source descriptor in
the complete runtime. The N5 FAQ remains N5-owned: source- and
scenario-scoped rulings cannot leak into an unrelated ITS mission with a
reused scenario ID, while rules-wide N5 FAQ applies to a valid selected
season. Exact season/revision/mission selection fails closed when unregistered.
No ITS-authored FAQ is inferred. Changing maintained `src/` or curated files
changes the complete build fingerprint;
regenerate the three-file release set before source-bound deployment
checks or merge.

For the ownership and scope exceptions (Spec-Ops, TEAM-OPS,
Reinforcements, marker citations, FAQ), see
[season publication ownership](season-publication-ownership.md).
