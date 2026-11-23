# ITS Season 17 and 18 SQLite databases

**Project domain:** Data processing

Schema v2 participates in the complete four-file build and serving set:
Army, Rules, ITS Season 18 and ITS Season 17. This page owns the ITS
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
- **Public selection:** Choose ITS Season 18 or 17 by season in Scenarios.
  Their current authored revisions (2026.09.11 and 0.2, respectively) resolve
  automatically; explicit older revision links still fail closed without
  silently displaying replacement facts. Historical revision browsing remains deferred.
- **Event context:** All 36 published missions carry `eventContext` with separate
  English and Spanish Reinforcements declarations (`suitable`, `not-suitable`,
  or `not-declared`). ITS 17 also records `tacticalSupportOptions` per player
  (including explicit zeroes), distinct from Tactical Objectives. The ITS 17
  season-owned `rule:tactical-support` supplies the shared selection rules,
  restrictions and twelve effects/timings (EN pp. 27–29, ES pp. 28–30), linked
  from mission setup when options are used. Cancellation timing and the scope
  of the Specialist reroll differ between the languages and remain disclosed.
  ITS 18 has no Tactical Support count. Reinforcements discrepancies are retained
  for ITS 17 Area of Interest and Corporate Appropriation, and ITS 18 Provisioning;
  mission-header omission is not converted into an explicit prohibition.
- **Scenario Skills:** Mission rules with `skillTypeIds` and `skillFacts`
  project to standard Skill cards, `/skills` and Search. All 31 reviewed ITS 18
  and 22 ITS 17 actions have structured Requirements and Effects, with optional Restrictions,
  Clarifications and Source context. Original mission paragraphs and action
  titles remain available for provenance and compatibility. Public Skill names
  omit redundant terminal `(Short Skill)` and `(Long Skill)` labels because
  their typed badges convey that classification. Their public IDs include the
  season and scenario, so same-named actions are not conflated. Optional
  `skillCitations` now pin the exact English and Spanish action pages for
  all 31 ITS 18 actions, reviewed against the SHA-matched 2026.09.11 source
  PDFs. Double Bind's intact and destroyed Antenna actions are separate Skills;
  Provisioning pickup retains the season-specific Safe Area requirements.
  Source-specific `sourceLabels` are projected through the standard
  Skill badge row: all reviewed ITS 17/18 scenario actions show **Attack** and
  **Scenario**, while season-wide Skills retain their own printed qualifiers
  (such as Optional or Obligatory). Matching N5 Labels link to their canonical
  definitions; **Scenario** remains readable but unlinked because it is not a
  current N5 Label entry. No label is derived merely from a Skill category.
  Core N5 scenario Skills are resolved
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
says *from all other Infected*. The two versions now retain separate
reviewed placement rules. Both publications restrict CivEvac
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

**Real ITS 17 source-reviewed scenario authoring (2026-11-18):**
`data/curated/its/n5-its-season-17.json` is the registered
ITS 17 V0.2 curated season source. It has reviewed
`scenario:evacuation`, `scenario:hardlock`, `scenario:uplink-center`,
`scenario:battleground`, `scenario:annihilation`, `scenario:cutthroat`,
`scenario:superiority`, `scenario:provisioning`,
`scenario:area-of-interest`, `scenario:last-launch`,
`scenario:b-pong`, `scenario:crossing-lines`,
`scenario:corporate-appropriation`, `scenario:critical-intervention`,
`scenario:outbreak` and `scenario:akial-interference` memberships pinned to
`data/curated/its/shared/its17-scenarios-v1.json`, with the source
SHA-256 in `sharedScenarioLibrary`. The shared library owns the
complete historical scenario definitions (format version 1) and the
season document owns the source-specific memberships and citations.
The original V0.2 Evacuation English pp. **55–58** and Spanish pp. **50–53**
support its mission, six army sizes / three maps, two Extraction
Consoles and scoring. Per-language Classified scoring, opening
activation timing and cross-player Console reactivation ambiguities
retain historical page references rather than inheriting ITS 18's.
ITS 17's mission describes a Console A Token or matching-diameter
scenery; the separate ITS 17 V0.2 global token table (EN p. 13 /
ES p. 14) confirms its **40 mm** Console footprint.

Hardlock independently matches ITS 18's six-size scoring, three geometry
configurations, two scenario Skills, Specialist Troops and end conditions.
ITS 17 EN pp. **59–62** and ES pp. **54–57** supply eight season-local
citations. Its original map and text specify 6/8/12-inch offsets for
side Consoles and owner-specific Beacons at the Deployment Zone inner
edges. The mission refers to Console A and Beacon Tokens or
matching-diameter scenery; the ITS 17 V0.2 global table (EN p. 13 /
ES p. 14) specifies **40 mm Consoles** and **25 mm Beacons**.
Both editions preserve EN/ES differences concerning a Connected versus
Activated Console and the Normal State of a transferring Beacon carrier.
ITS 17's one Tactical Support Option belongs to historical play context,
not a current ITS 18 rule.

Uplink Center independently matches ITS 18's four scoring conditions,
12-/16-inch Deployment Zones, three geometry configurations, Communication
Antenna activation, Tech-Coffin Control, Operational Learning, Active
Lieutenant and end conditions. ITS 17 EN pp. **93–96** and ES pp. **99–102**
supply eight season-local citations. The 6/8/12-inch Antenna offsets and
central Tech-Coffin agree across the printed maps; ITS 17 permits the
named Tokens or matching-diameter scenery. Its V0.2 token table
(EN p. 13 / ES p. 14) specifies **40 mm** for both Transmission
Antenna and Tech-Coffin Tokens. ITS 17 ES p. 100 omits **350** from the
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
round-limit rules are carried across. The ITS 17 database is separately registered; the current ITS 18 record
remains unchanged.

Annihilation keeps the source-matched EN V0.2 scoring thresholds
(ITS 17 **pp. 81–82**, Spanish **pp. 85–87**), 150–400 Army Point
configurations, Killing, No Quarter and the three-round limit.
These match the current ITS 18 English definition, but the
historical source remains separately cited and versioned. The
ITS 17 **Spanish survival chart awards 3/4/4 OP**, contradicting
the **English 1/3/4 OP** for identical Victory Point bands.
The English scoring remains selected with the bilingual
discrepancy unresolved. Both original languages leave exactly
**275** at 350 points between the 3- and 4-OP bands, for both
Killed and surviving points. EN p. 82 also prints a mixed-unit
150-point Deployment Zone dimension (8 in × 32 cm), while its own
map and ES p. 86 show the normal full-width 8-inch-deep area.
The three original maps are retained without inventing a mixed-unit
deployment. The separate ITS 18 Spanish 400-point threshold
discrepancy is not retroactively assigned to ITS 17.

Cutthroat is versioned independently because ITS 17 EN pp. **86–88** and
ES pp. **91–93** include Key Ops designation and two Key Ops objectives
(1 OP to Kill the enemy Key Ops; 3 OP for more kills by one's Key Ops),
where ITS 18 awards 4 OP for more Lieutenant-led Trooper kills instead.
Both share the three 12-/16-inch Deployment Zone maps and Reinforced
Tactical Link. Original Key Ops Dodge (+3), Tactical Awareness, REM/VH
eligibility and Killing attribution remain in the ITS 17 definition;
the Spanish omission of VH, its minimum-one-Lieutenant condition for
the greater-Lieutenant-kills objective, and the omitted historical
Lieutenant-kill definition remain cited source differences.

Superiority uses the same source-verified four-Quadrant geometry and
Hack Consoles Short Skill, Specialist Troops, Operational Learning, and
three-round/Retreat! endings as ITS 18. ITS 17 EN pp. **89–92** and
ES pp. **94–98** instead cap Hacked Console scoring at **3 OP** (not 4)
and award **1 OP** for a Dominant Key Ops in a player-dominated Zone
of Operations at game end, with the Key Ops in a non-Null State.
This preserves the ten-point mission maximum (6 + 3 + 1). The historic
Key Ops selection, Dodge (+3), Tactical Awareness and English REM/VH
restriction are retained. Spanish omits VH, and the Shasvastii
Unconscious/non-Null versus Normal/Embryo formulations differ, so both
remain historical source issues. The mission uses Console A Tokens
and the ITS 17 V0.2 token table (EN p. 13 / ES p. 14) fixes their
**40 mm** diameter.

Provisioning has independently reviewed ITS 17 V0.2 EN pp. **72–76**
and ES pp. **70–74**. Its four-box scoring (4 + 3 + 2 + 1 OP),
three diagonal Tech-Coffins, corner quarter-circle deployments,
three game-size maps, Safe Areas, Specialist actions and endings
match the current definition. The original 8/12/16-inch coffin
spacing is confirmed by both language editions' diagrams. Its
Tech-Coffin Token scenery uses a matching diameter, which the
ITS 17 V0.2 chart (EN p. 13 / ES p. 14) fixes at **40 mm**. Both historical languages mark
an emptied coffin with a Player Token (ITS 18 English may instead
remove its Token), limit Specialist/WIP-3 recovery to the **enemy**
Safe Area (ITS 18 English says *a* Safe Area), and explicitly place
a deposited Box wholly inside the Safe Area. Historical EN p. 74
requires **base contact** to Extract, while ES p. 71 says
**Silhouette contact**; the source issue remains unresolved. The
separate ITS 18 bilingual issue set is not copied onto ITS 17.

Area of Interest is source-reviewed against ITS 17 V0.2 EN pp. **77–80**
and ES pp. **80–84**. The 3 + 3 + 3 + 1 OP scoring, corner
quarter-circle deployments (12/20/24-inch radii), one central
Antenna, three player-placed Circular Template Areas, INTELCOM
choice and three-round/Retreat! endings match ITS 18. Both
historical languages specify a Transmission Antenna Token or
matching-diameter scenery. The ITS 17 V0.2 chart (EN p. 13 /
ES p. 14) independently fixes **40 mm** for Transmission Antennas
and **25 mm** for the Player A/B activation Tokens.
The ITS 17 editions disagree on Reinforcements suitability
(**EN YES / ES NO**), enemy Hacker ARO optionality, and the
Shasvastii state wording (EN Unconscious/any non-Null versus
ES Normal/Unconscious). The Spanish Antenna text alternates
*Conectada* and *Activada*. As in ITS 18, English places
INTELCOM at the last Game Round while Spanish specifies the
third; this remains unresolved if Retreat! ends play earlier.
These are recorded with independent ITS 17 source citations.

Last Launch matches ITS 18 scoring (2 + 2 + up to 2 + 1 + 3 OP),
the three table configurations, 4/8-inch Scanner offsets, three ID actions,
8-inch central Launching Tower, four open Wide Gates, Baggage, No Quarter
and the third-round ending. ITS 17 V0.2 EN pp. **63–67** and ES pp.
**75–80** provide eleven historical citations. Both versions specify scenery
matching the ID Scanner/Checker Token diameter, confirmed as
**40 mm** for Tech-Coffin and Console Tokens by ITS 17's V0.2
chart (EN p. 13 / ES p. 14). ITS 17 EN names an 8-inch Tower versus ES 20 cm;
Spanish alone specifies gate access for any Silhouette; EN Shasvastii
non-Null wording differs from Spanish Normal/Unconscious; and EN says
removed Troopers' points while ES uses singular for Peripheral extraction.
Four independent source issues preserve these differences. The original
mission has two Tactical Support Options.

B-Pong V0.2 EN pp. **36–39** and ES pp. **38–41** agrees with ITS 18
on 2 + 3 + 3 + 2 OP scoring, six game sizes/three maps, center Beacon,
two Consoles at 6/8/12-inch offsets, exclusion zones, the two Short
Skills and the round limit. Unlike ITS 18, **both** ITS 17 languages
measure Beacon relocation from its **previous position** and specify
that Console Activation requires the Beacon not to touch a Trooper and
limits each successful Specialist Activation to once per round.
Both historical originals permit equal-diameter scenery. The ITS 17
V0.2 token chart (EN p. 13 / ES p. 14) specifies **25 mm Beacons**
and **40 mm Consoles**. Both editions agree on end-of-round Beacon Control. The
remaining bilingual source issues concern EN **up to 6 inches** versus
ES **15 cm** for Magnetize, and Spanish calling a successful Console
*Conectada* rather than *Activada*. These remain explicit and are not
inherited from ITS 18's distinct disagreements. ITS 17 specifies two
Tactical Support Options in both languages.

Crossing Lines V0.2 EN pp. **51–54** and ES pp. **42–45** confirms the
ITS 18 3 + 3 + 2 + 2 OP scoring, split-deployment geometry, central
75-point deployment cap, 6/8/12-inch Antenna offsets, Activate Antenna
Short Skill, and third-round/Retreat! endings. EN p. 53 specifies
Transmission Antenna Tokens while ES p. 44 says Console A Tokens.
Both are **40 mm** under the ITS 17 V0.2 chart (EN p. 13 / ES p. 14).
The bilingual representation disagreement remains unresolved.
The EN table gives an inconsistent longer central-strip length for
150/200/250 points; ES p. 42 supports the reused layout's actual table
widths. EN p. 53 counts Shasvastii-Embryo or other non-Null States whereas
ES p. 44 says Normal or Unconscious. EN/ES p. 54/45 exclude Secure HVT
and Secure Treasure, but do **not** expressly exclude HVT Model deployment
as ITS 18 does. The general compulsory deployment rule (EN pp. 26–27 /
ES pp. 27–28) therefore applies: one HVT per player. The missing explicit
mission exception remains a source note, not grounds for a zero count.
These four source issues are recorded with ITS 17 provenance.

Corporate Appropriation V0.2 EN pp. **40–44** and ES pp. **32–37**
confirms the 2 + 1 + (3 or 1) + 1 + 3 OP scoring, three deployment
configurations, two Prototypes and Panoplies, their fixed positions,
ADS defense, first-round protection, and three Classified Objectives.
Historical Panoplies permit Objective Tokens or matching-diameter
scenery; ITS 17 V0.2 EN p. 13 / ES p. 14 fixes the Objective Token
at **40 mm**. No unreviewed Prototype diameter is inferred.
Both ITS 17 languages expressly restrict Prototype-targeting Attacks
affecting other Troopers and forbid **all** CC Attribute MODs to the
attacker against ADS; unlike ITS 18, these are not bilingual disputes.
Pick Up Prototype and Use Panoply are both typed scenario Short Skills.
Three ITS 17-specific issues remain: **Reinforcements suitability**
(EN YES / ES NO), the enemy-contact condition for Captured Prototypes,
and Baggage's classification (EN Special Skill / ES Equipment). The
latter two are preserved in source-local prose rather than resolved.

Critical Intervention V0.2 EN pp. **45–50** and ES pp. **63–69**
confirms its asymmetric Attacker/Defender scoring, six Army Point
thresholds per role, one Classified Objective, the three maps, and the
Extract Data Pack / Use Inhibitor Antenna Short Skills. The Defender's
printed Main Objective awards total 11 OP plus 1 Classified OP;
they are retained instead of applying an unprinted 10-point cap.
Both historical languages print STR 1 for the Armed Turrets and say
the active Defense System reacts to **enemy Models**, not explicitly
Attacker Models. The Console and Inhibitor Antenna permit scenery
matching their **40 mm** Tokens under ITS 17 V0.2 EN p. 13 / ES p. 14. Six independent
source issues preserve the 8-inch/20-cm Server Room dimensions,
Spanish-only Silhouette access wording for the Gates, Shasvastii
states, Victory Points versus Army Points for INTELCOM, 4-inch/10-cm
exclusion half-width, and the printed Defender scoring maximum.

Outbreak V0.2 EN pp. **68–71** and ES pp. **46–49** has **different
objectives** from ITS 18: ITS 17 awards 1 OP for Stabilizing the Alpha
Infected and 1 OP for CivEvacing the Stabilized Alpha Infected; ITS 18
drops the former and awards 2 OP for the latter. Both still offer a
10-OP total. The six ITS 17 objectives have independent historical
fact text and provenance; no shared cross-season definition is claimed.
Both originals agree on five Infected, the central Alpha, three
opposite-corner deployment maps, player-placed Stabilization Zones,
CivEvac restrictions, Scan/Stabilize Short Skills and no Classified/HVT.
ITS 17 EN p. 69 / ES p. 47 require separation between each player's own
two Infected, not all five; EN p. 71 / ES p. 49 also explicitly exclude
Secure Treasure. One bilingual difference remains: placement distances of
4/8 inches versus 10/20 cm. ITS 18 scoring and placement remain unchanged.

Akial Interference V0.2 EN pp. **31–35** and ES pp. **58–62**
confirms the 6 + 1 + 1 + 2 OP scoring, 2 public Common Classified
Objectives per Round, 1 Private Classified Objective, 4 HVTs per
player and 3 deployment maps. Historical source explicitly disables
**both Secure HVT and Secure Treasure**, while retaining HVT Models.
The central Akial Antenna uses a Transmission Antenna Token or matching-
diameter scenery. The ITS 17 V0.2 chart (EN p. 13 / ES p. 14) specifies
**40 mm** for that Token, independently of ITS 18.
Emit Akial Interference and Filter the Signal remain typed Short Skills
with **ITS 17-local Skill citations**, not inherited ITS 18 citations.
Both originals allow repeated failed Emit Rolls but also limit each
Specialist to one Emission per Game Round; the attempts-versus-successes
ambiguity is recorded without inventing an interpretation.
Nested Skill citation `sourceId` validation accepts versioned source IDs with
revision dots (such as `v0.2`) without weakening identifier validation for
route slugs; malformed source IDs remain rejected by focused tests.

**ITS 17 V0.2 global token-diameter correction (2026-11-19):**
The independently pinned English **p. 13** and Spanish **p. 14**
each print the same season-wide Diameter of ITS Tokens table:
Transmission Antenna, Tech-Coffin, Console and Objective Tokens are
**40 mm**; Supply Box, Beacon, Player A/B, Data Pack, Defensive Turret
and CivEvac Tokens are **25 mm**. The scenario pages often give only
matching-diameter scenery, but that is not an absence of source-wide
dimensions. Twelve historically curated missions were reconciled
against the chart: Evacuation, Hardlock, Uplink Center, Superiority,
Provisioning, Area of Interest, Last Launch, B-Pong, Crossing Lines,
Corporate Appropriation, Critical Intervention and Akial Interference.
Each updated definition and season membership now has the two additional
source page citations. This does **not** prescribe the physical base
size of a Civilian Model or unlisted Prototype/Gate, nor resolve
Crossing Lines' genuine EN Transmission Antenna versus ES Console A
representation mismatch; both named Token types happen to be 40 mm.
Neither ITS 18 curation nor scenario scoring/geometry was changed.
The guarded one-time authoring migration was
`tools.research.reconcile_its17_token_chart`.

**ITS 17 season-wide Skills and State (2026-11-19):** Independent
review of pinned V0.2 EN pp. **17–21** and ES pp. **18–22**
adds `skill:civevac`, `skill:casevac` and `state:casevac` to the
historical season's own `records`, without modifying the 16-member
scenario library or registering ITS 17 for serving. Both English
Skills are declared **Short Movement Skills**; both Spanish Skills
are **Habilidades Cortas Básicas**. The original English classification
is retained in the historical typed facts, with the different Spanish
classification recorded rather than silently treated as equivalent
to ITS 18's distinct Basic Short / Short Skill types. EN p. 20 permits
Casevac State to continue for the specified Cautious Movement, Climb,
Dodge, Jump, Reset or **Short Movement Skill** declarations; ES p. 22
instead uses **Habilidad Corta Básica** for its general permitted class.
This difference affects possible cancellation and remains unresolved.
The Spanish CivEvac enemy-contact/Token condition on ES p. 18 is also
worded conjunctively where EN p. 17 lists two independent exclusions;
the historical English interpretation is retained, pending clarification.
The State retains the carrier/carried Order, ARO and movement rules,
single carried Trooper limit, all automatic cancellation triggers and
voluntary Short Skill cancellation. Each record has four bilingual page
pins and independent revision applicability. `its_18.db` and the
current ITS 18 facts remain unchanged.

**ITS 17 earlier-revision source comparison (2026-11-19):** The six
publisher-original V0.0/V0.1/V0.2 English/Spanish PDFs are SHA-256
pinned by `tools.research.acquire_its_pdf`, and the existing
`tools.research.audit_pdf_revision_deltas` now supports all four
adjacent ITS 17 comparisons with `--pairs its17-v0.0-v0.1-en
its17-v0.0-v0.1-es its17-v0.1-v0.2-en its17-v0.1-v0.2-es`.
This offline diagnostic writes a fresh ignored `local/audits/` report;
its nine-token window matches are **candidates**, not independently
accepted rules, especially across the V0.2 mobile-page reflow.
The first four-pair run found 34/38 V0.0→V0.1 candidate spans
(EN/ES) and 43/50 V0.1→V0.2 candidate spans (EN/ES).

The following concrete original-page differences were independently
checked, not simply inferred from the automated text diff:

- **Casevac declaration:** V0.0 EN p. **14** labels it *Short Skill*;
  V0.1 EN p. **14** changes to *Short Movement Skill*. Spanish
  V0.0 p. **14** labels it *Habilidad Corta*, while V0.1 p. **14**
  changes to *Habilidad Corta Básica*. These are independently
  published language-specific categories, not one interchangeable type.
- **Critical Intervention Reinforcements suitability:** V0.0 EN p.
  **30** prints **YES** and V0.1 EN p. **30** changes it to **NO**.
  Both V0.0 and V0.1 ES p. **37** already print **NO**. The English
  V0.1 changelog calls this out; the Spanish changelog does not.
- **Corporate Appropriation main scoring:** V0.0 ES p. **21** omits
  the 1-OP objective for acquiring more Panoply weapons/equipment than
  the opponent. V0.1 ES p. **21** includes it; the English V0.0 and
  V0.1 p. **27** already include it. The Spanish V0.1 changelog
  records this correction, but the English changelog does not.
  EN **YES** versus ES **NO** for Corporate Appropriation
  Reinforcements suitability is already present in both editions
  and remains unresolved in V0.2.
- **Crossing Lines:** V0.0 EN p. **36** does not contain the
  *Secure HVT or Secure Treasure Not Used* clause; V0.1 EN p.
  **36** adds it. Do not project that V0.1 restriction into V0.0.
- **Resilience Operations first reveal:** V0.0 EN p. **63** and
  V0.0/V0.1 ES p. **62** place it *after Deployment, before Game
  Round 1*. V0.1 EN p. **63** changes to *at the beginning
  of the first Game Round*. That version remains in V0.2 EN p.
  **97**, but V0.2 ES p. **104** retains the previous wording.
  The V0.1 English changelog describes a Tactical Objectives
  wording change, and the V0.2 bilingual conflict is preserved in
  `rule:resilience-operations` source notes.
- **V0.2 addition:** The EN/ES V0.2 changelogs on p. **2** state
  that **Outbreak / Estallido** was added. The original V0.0/V0.1
  contents each have 15 standard missions; the V0.2 contents have
  16. V0.2 also reflows the PDF from 68→105 EN and 67→112 ES
  pages, so printed-page offsets cannot be reused as citations.

**Earlier-revision evidence curation (2026-11-19):** The same
`data/curated/its/n5-its-season-17.json` now keeps an optional
`historicalEvidence` section with **23 reviewed fact aspects and 104
source observations**, each pinned to an original English/Spanish PDF
source ID, revision, page, SHA-256 and record identity. V0.0/V0.1
descriptors are stored once in the historical source inventory, while
V0.2 comparisons reuse the document's existing current PDF descriptors.
This includes the differences above and the source-reviewed V0.1
Use Inhibitor Antenna Attacker-only limit (EN p. **33** / ES p.
**40**), the replacement of Defender-placed Deployable Weapon
wording for Critical Intervention Armed Turrets with reaction to
active enemy Models and not Markers (EN p. **32** / ES p. **39**),
and the rewritten enemy-Hacker ARO / Face-to-Face WIP interaction
in Area of Interest (EN p. **49** / ES p. **48**). Akial
Interference's V0.0 texts exclude only Secure HVT explicitly
(EN p. **23** / ES p. **36**); V0.1 adds Secure Treasure to that
exclusion in both languages. The absence of a printed prohibition
is **not** curated as permission to perform the action.

Additional source-reviewed V0.0→V0.1 facts cover:

- **Tournament-wide:** A bye changes from **3 to 4 Tournament Points**
  in both English and Spanish (both p. **8**). In the 350-point
  Tournament Tier, English p. **9** changes **5 SWC → 7 SWC**;
  Spanish p. **9** already says **7 CAP** in V0.0 and V0.1.
  The V0.0 English general table is therefore not treated as
  proof that every 350-point mission used 5 SWC. These facts are
  explicitly bound to `seasonId: its-17` rather than incorrectly
  attributed to a particular scenario.
- **Akial Interference:** Simultaneously completing a shared Common
  Classified Objective changes from the same *Player Turn* to the
  same *Game Round* (EN p. **22**, ES p. **35**).
- **Corporate Appropriation:** V0.1 explicitly excepts *Pick Up
  Prototype* from the first-round attack restriction; V0.0 states
  the prohibition but not the exception (EN p. **28**, ES p.
  **22**). The accompanying *Controlling* → *Capturing* label
  correction is preserved as a terminology change, not assumed
  to change the physical possession requirements.
- **Crossing Lines:** V0.1 explicitly limits the 75-point Central
  Strip deployment allowance to the *Deployment Phase*; V0.0
  does not name the phase (EN p. **35**, ES p. **28**). The 75-point
  value and antenna placement distances are unchanged in these
  reviewed paragraphs; absence of the old phase wording is not
  treated as permission to deploy at other times.
- **Provisioning:** EN p. **46** changes *unaccompanied SUPPLY BOX
  Token* to *Supply Box that is not being carried*. ES p. **42**
  retains *SUPPLY BOX solitario* across both revisions. This is
  recorded as text revision, **not** a verified change in pickup
  eligibility.

**V0.1→V0.2 bilingual comparison (2026-11-19):** Two
source-confirmed written-rule changes and an independently reviewed
printed-map chronology are now part of the same review-only evidence:

- **Uplink Center, 150-point Communication Antennas:** The two
  centerline Antennas are placed **4 in** (ES **10 cm**) from their
  respective table edges in both V0.0 and V0.1 (EN p. **61**,
  ES p. **60**). V0.2 moves them to **6 in** (ES **15 cm**)
  from the edges (EN p. **94**, ES p. **100**). This is a
  written placement-rule revision, not simply V0.2's page reflow.
  However, visual inspection of the original 150-point maps shows
  **6 in / 15 cm in every edition**: V0.0/V0.1 EN p. **60**,
  ES p. **59**, and V0.2 EN p. **93**, ES p. **99**.
  Thus V0.0/V0.1 **written text contradicts its own map**; V0.2
  corrects the prose to match existing diagram placement, not the
  graphical antenna positions. The evidence keeps separate written-rule
  and printed-map aspects rather than inventing an unambiguous old rule.
  The current V0.2 shared scenario geometry and 150-point
  publication test already use **6 in**.
- **Corporate Appropriation Prototype targeting:** V0.0/V0.1
  allow selecting a Prototype as the target but do not state
  an explicit restriction for Attacks also affecting Troopers
  (EN p. **28**, ES p. **22**). V0.2 explicitly prohibits
  choosing the Prototype as a target if that Attack also
  affects an allied or enemy Trooper (EN p. **41**,
  ES p. **33**). The current V0.2 shared scenario rule
  already records the restriction. Lack of a printed V0.1
  clause is not curated as permission for collateral attacks.
- **Outbreak inventory:** Both V0.2 contents/changelogs
  on p. **2** explicitly add Outbreak / Estallido, completing
  the previously stored V0.0/V0.1 absence observations.

**Crossing Lines central-strip source conflict (2026-11-19):** Visual review
of its original 150-/200–250-point diagrams across all six PDFs confirms
full-table-width 4-inch strips: **4 × 24 in** and **4 × 32 in** in the
English maps (V0.0/V0.1 p. **34**, V0.2 p. **52**). Spanish maps show
**10 × 60 cm** and **10 × 80 cm** (V0.0/V0.1 p. **27**, V0.2 p. **43**).
However, the **English deployment tables** consistently print **4 × 32 in**
and **4 × 48 in** for these sizes (V0.0/V0.1 p. **34**, V0.2 p. **51**),
which exceed the corresponding 24-/32-inch game-table widths. Spanish
written tables match the maps (V0.0/V0.1 p. **27**, V0.2 p. **42**).
The mismatch persists through V0.2; it is not a revision-introduced change
or justification to widen the scenario geometry. The historical evidence
records separate map and written-table aspects, preserving the English
source contradiction and Spanish agreement without choosing a new rule.
Existing V0.2 geometry and ITS 18 publication remain unchanged.

Only Uplink Center and Crossing Lines have been reviewed visually across
all six ITS 17 editions in this pass; the other historical mission diagrams
still require independent review.

The section has `mode: review-only-not-projected`; validation rejects
out-of-range citations, unpinned or duplicate edition identifiers,
unknown record/season targets, double-bound observations, unreviewed
facts, and invalid current-publication PDF source identities. `project_its_source_family` validates then **excludes** it
from the current V0.2 projection, so it does not create older
scenario records, citations, sources, SQLite rows, API routes,
or selectable revisions. The historical section is retained in
the single curated source for later reconciliation. It is a
**reviewed subset**, not a claim of unchanged semantics for
unreviewed historical missions. More full-source review and
older-version field/geometry overrides are needed before a
complete `sourceFamily` history projection would be valid.

**ITS 17 SQLite ownership:** All reviewed ITS 17 mission, geometry, scoring and
season-specific citation records belong in an independent **`its_17.db`**,
not in `rules_n5.db` or `its_18.db`. The tracked runtime publication is
`data/generated/its_17.db` alongside the existing `its_18.db`, Army and Rules
files. It contains sixteen reviewed ITS 17 scenarios, CivEvac, Casevac,
Casevac State and the Resilience Operations tournament Extra; the old
`local/work/its/its_17.db` remains an optional development output.
No V0.0/V0.1 selectable revision or shared cross-season record identity is
inferred from the available historical observations.

Build or check the independent historical SQLite file without registering it:
`python -m tools.data.build_its_season --source data/curated/its/n5-its-season-17.json --shared-library data/curated/its/shared/its17-scenarios-v1.json --output local/work/its/its_17.db`
(add `--check` to validate the existing file). After each historical authoring
batch, rebuild this file from the pinned JSON and library inputs. The authoring
bootstrap `python -m tools.research.bootstrap_its17_evacuation`
**refuses to overwrite** these human-reviewed JSON files; the one-time
`tools.research.extend_its17_hardlock` and
`tools.research.extend_its17_uplink_center` and
`tools.research.extend_its17_battleground` and
`tools.research.extend_its17_annihilation` and
`tools.research.extend_its17_cutthroat` and
`tools.research.extend_its17_superiority` and
`tools.research.extend_its17_provisioning` and
`tools.research.extend_its17_area_of_interest` and
`tools.research.extend_its17_last_launch` and
`tools.research.extend_its17_b_pong` and
`tools.research.extend_its17_crossing_lines` and
`tools.research.extend_its17_corporate_appropriation` and
`tools.research.extend_its17_critical_intervention` and
`tools.research.extend_its17_outbreak` and
`tools.research.extend_its17_akial_interference` migrations are not build steps.
Exact source pins and independent SQLite reproducibility have focused
regression tests in `tests/test_its17_evacuation_publication.py` and
`tests/test_its17_hardlock_publication.py` and
`tests/test_its17_uplink_center_publication.py` and
`tests/test_its17_battleground_publication.py` and
`tests/test_its17_annihilation_publication.py` and
`tests/test_its17_cutthroat_publication.py` and
`tests/test_its17_superiority_publication.py` and
`tests/test_its17_provisioning_publication.py` and
`tests/test_its17_area_of_interest_publication.py` and
`tests/test_its17_last_launch_publication.py` and
`tests/test_its17_b_pong_publication.py` and
`tests/test_its17_crossing_lines_publication.py` and
`tests/test_its17_corporate_appropriation_publication.py` and
`tests/test_its17_critical_intervention_publication.py` and
`tests/test_its17_outbreak_publication.py` and
`tests/test_its17_akial_interference_publication.py`. Existing ITS 18
curated facts remain unchanged; this ITS 17 season is **not yet
registered for web publication**. A separate versioned shared
component extraction can follow after the rule-inclusion format is
reviewed: the existing typed v2 composer requires rule references,
not the inline narrative/Skill facts present in the reviewed
Evacuation, Hardlock, Uplink Center, Battleground, Annihilation,
Cutthroat, Superiority, Provisioning, Area of Interest, Last Launch,
B-Pong, Crossing Lines, Corporate Appropriation, Critical Intervention
Outbreak and Akial Interference missions.
The accepted migrations reuse complete v1 scenario definitions,
without claiming fine-grained component or Skill deduplication yet.

The ITS 17 V0.2 table of contents lists **exactly sixteen standard
scenarios**, and all sixteen have reviewed historical memberships;
there is no seventeenth standard mission. The separate
**Resilience Operations** section (EN pp. **96–104**, ES pp. **103–111**)
defines an optional tournament Extra using Tactical Objective
and Battle Condition decks *instead of* ordinary ITS scenarios and the
Classified Deck. It is not a scenario membership.

**Resilience Operations source-reviewed (2026-11-19):** The season-local
`rule:resilience-operations` record contains the original EN/ES source
pins (plus their shared Token charts EN p. 13 / ES p. 14) and typed
Extra-only facts. Tactical Objectives: draw four, discard one,
optional one-Command-Token redraw, reveal one each Round with Priority
Target first, maximum three OP *per card* awarded once, and one bonus
OP for completing more objectives than the opponent. Battle Conditions:
draw two, discard one, reveal in Initiative order after the Initiative
Roll and before Deployment, redraw duplicate cards for the second-turn
player, affect both players for the whole game, and apply at most one
Movement Bonus. Six standard deployment tiers (150–400 points), the
third-round/Retreat! end conditions, five Tactical Element categories
(Beacons, HVTs, Beepers, Objectives, conditional F-13 Turrets) and the
Capture/Control/Dominate/Killing/Subjugate glossary are preserved with
source-specific details. The two editions differ on the ordinary HVT
MOV value, exact wording of first-round reveal timing, Beacon failed
repair wording and Baggage's Skill/Equipment classification; these are
explicit source notes, not silently resolved claims. The *physical card
decks' contents* are not present in these rule pages and have not
been reconstructed.

This Extra is a **Rule**, not a `scenario`, in the existing
`records` table of `its_17.db`. The ITS builder fail-closed validates
season-local optional Extra records and their source revision, typed deck
selection, Tactical Elements, glossary, game sizes, and citation integrity.
No new SQLite schema or separate Extra-specific web route is introduced.
The ITS 18 database retains the existing report shape when no Extra
is present. Cross-season component/Skill equivalence, complete physical
deck card acquisition and earlier source revisions remain under review.

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

**Current registration:** ITS 18 remains source-local, while ITS 17 is
registered with its pinned `its17-scenarios-v1.json` shared authoring library.
Both compile to separate tracked SQLite files in the four-file runtime bundle;
source and library hashes, exact season/revision membership and independent
citations are checked during build, application startup and deployment validation.

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

### Release diagram acceptance

The independent bilingual diagram re-review for v1.2.0 compares the original
PDF images (not only extracted text) with curated table dimensions, zone
ownership and boundaries, fixed marker centers and all six game-size
bindings. All four local source PDFs match their registered SHA-256 pins.

Verified in ITS 17 V0.2 and ITS 18 2026.09.11, covering 69 distinct
layouts and 138 game-size setups (both seasons unless noted):

- **B-Pong:** ITS 17 EN p. 37 / ES p. 39; ITS 18 EN p. 59 / ES p. 59.
  Rear zones 12/16/16 inches, Exclusion half-widths 2/4/4 inches,
  central Beacon and quarter-width Consoles. The current diameter
  conflict remains separate from the confirmed center position.
- **Crossing Lines:** ITS 17 EN p. 52 / ES p. 43; ITS 18 EN/ES p. 64.
  Rear zones 8/12/12 inches, exchanged 4-inch forward zones,
  intervening Dead Zones, and centerline Antennas at 6/8/12 inches
  from the nearest lateral edge. The historical table-width typo
  remains disclosed; both diagrams support the maintained geometry.
- **Evacuation:** ITS 17 EN p. 55 / ES p. 51; ITS 18 EN/ES p. 88.
  Rear zones 8/12/12 inches; Civilians 6 inches from the lateral
  edges and 12/16/16 inches from the rear edges; centerline Consoles
  8/12/16 inches from the nearest lateral edge. The 25 mm Token
  option does not prescribe a Model base size.
- **Hardlock:** ITS 17 EN p. 60 / ES p. 55; ITS 18 EN p. 49 / ES p. 127.
  Rear zones 8/12/12 inches, owner Beacons centered on their front
  boundaries, three centerline Consoles with outer offsets 6/8/12 inches.

- **Critical Intervention:** ITS 17 EN p. 46 / ES p. 64; ITS 18 EN/ES p. 98.
  Rear zones 8/12/12 inches, central Attacker Exclusion half-width 4 inches,
  8-inch Server Room, four open Wide Gates, opposing interior corner Turrets,
  central Data Console and Inhibitor Antenna tangent to the southern wall.
  Turret clearances and gate widths remain schematic.
- **Last Launch:** ITS 17 EN p. 64 / ES p. 76; ITS 18 EN p. 115 / ES p. 116.
  Rear zones 8/12/12 inches, central 8-inch Launching Tower with four open
  Wide Gates and no deployment inside, central ID Checker and two centerline
  ID Scanners 4/8/8 inches from the nearest lateral edges.

- **Outbreak:** ITS 17 EN p. 69 / ES p. 47; ITS 18 EN/ES p. 84.
  Top-right A and bottom-left B quarter-circle zones (12/20/24-inch radii),
  central Alpha Infected; other Infected and Stabilization Zones player-placed.
- **Provisioning:** ITS 17 EN p. 73 / ES p. 71; ITS 18 EN/ES p. 110.
  Same corner deployments, three diagonal Tech-Coffins spaced 8/12/16 inches
  center-to-center, and player-placed Safe Areas.
- **Area of Interest:** ITS 17 EN p. 78 / ES p. 80; ITS 18 EN p. 121 / ES p. 122.
  Top-left A and bottom-right B quarter-circle zones (12/20/24-inch radii),
  central Communication Antenna; Areas of Interest are player-placed.

- **Corporate Appropriation:** ITS 17 EN p. 41 / ES p. 33; ITS 18 EN p. 54 /
  ES p. 52. Rear zones 8/12/12 inches, Exclusion half-width 4 inches,
  quarter-width Prototypes and central Panoplies on the front zone boundaries.
- **Neutralization (ITS 18 only):** EN/ES p. 105. Rear zones 8/12/12 inches,
  Exclusion half-width 4 inches, two centerline Tech Boxes each 4 inches
  from table center, and four Antennas on the front zone boundaries
  4 inches from the lateral edges. Existing 12 cm Circular Template
  footprints remain centered on their respective Antennas.
- **Akial Interference:** ITS 17 EN p. 32 / ES p. 59; ITS 18 EN/ES p. 92.
  Rear zones 8/12/12 inches and central Akial Antenna.

All twenty-three reviewed season-mission definitions have correct 150/200/250/
300/350/400-point configuration bindings and 3/4/5/6/7/8 SWC (ITS 18
EN p. 17; ITS 17 mission force tables). No geometry changes required in
these batches. Remaining diagram review: 13 season-mission definitions (78
setups); browser acceptance and runtime validation are separate steps.

All twenty missions are published for the current 2026.09.11 revision:

- **Crossing Lines:** Four deployment areas per map (two per player),
  two Dead Zones, two Antennas, scoring at the end of rounds and at game
  end, and the hotfix's explicit HVT/Classified exclusion (EN/ES pp. 63–66).
  Both languages on p. 64 disagree over Shasvastii eligibility for Domination:
  English counts Shasvastii-Embryo or any non-Null State; Spanish names
  Normal or Unconscious. The English-selected rule and source issue retain
  both formulations, also independently documented for ITS 17.
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
- **Evacuation:** Four fixed-position Civilians and two central 40 mm
  Extraction Consoles, on all six Army Point sizes, with 8-/12-inch opposing
  Deployment Zones. The 25 mm Player A/B Token option is rendered at scale;
  the Civilian Model alternative has no prescribed base diameter. Player-
  deployed enemy HVTs remain location-free. Score up to 4 OP for Extracted Civilians,
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
  Zone. The two Armed Turrets may use 25 mm Defensive Turret Tokens
  (ITS 18 EN p. 18) or S2 Models; the central 40 mm Data Console and
  Defender-side 40 mm Inhibitor Antenna are also source-sized. Its token sits
  tangent to the Server Room's bottom edge with its left edge aligned to
  the room's left edge in all three map sizes (ITS 17 and 18). The Defender may
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

**Circular Template Areas:** Every Circular Template defines an area
**12 cm in diameter** (the canonical physical template measurement, **not
an explicit numeric dimension in the reviewed scenario rule text**; see
[template semantics](rules-semantics.md)). This is now stated explicitly
in the relevant scenario rules for ITS 18 Double Bind (Antenna Zones of Influence),
Neutralization (four Antenna-centered Areas), Provisioning (Safe Areas),
Area of Interest, Data-Harvest (Designated Zones) and Outbreak
(Stabilization Zones), including the shared ITS 17 versions of
Provisioning, Area of Interest and Outbreak. Maps with fixed Circular
Template Areas repeat the size in their visible placement note. Their
fixed SVG footprints now use the exact physical **6 cm radius**
(60 / 25.4 inches in the canonical table coordinates), replacing the
former schematic 2.5-inch radius. Physical sizes use 25.4 mm per inch
as for tokens; distance labels continue to use Infinity's published
2.5 cm-per-inch game convention. Player-placed Areas retain the same
12 cm diameter but remain without invented map positions.

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

**ITS token footprint and ruler presentation:** ITS 17 V0.2 EN p. 13 and
ITS 18 2026.09.11 EN p. 18 (ES p. 19) provide the source-owned token
diameter chart. Every fixed-size token type used in scenario maps must
project that physical diameter in the SVG and player-facing marker list,
including the **25 mm Defensive Turret Token**. The S2 Model alternative
for a Defensive Turret remains a model. Civilian markers use the
**25 mm** Civilian/CivEvac footprint in Evacuation and Outbreak maps.
B-Pong's Tracking Beacon retains its unresolved EN/ES disagreement, rather than
borrowing the global 25 mm Beacon Token size.

Marker-placement ruler endpoints must describe the **actual measured
marker positions**. In-map rulers for centerline objectives normally
sit below the markers using a separate geometry `offset` (usually
2.5 inches); their distance labels also belong **below the visible
ruler**, not on top of those markers. Do not copy the official diagram's
external guide placement into the measured coordinates. Prefer
collision-free ruler, label, marker and region layouts in both inches
and centimeters. Place related guides together in unobstructed space:
Double Bind and B-Pong move their horizontal labels below the exclusion
area and keep vertical exclusion labels clear of Circular Templates;
Crossing Lines separates the two short central Deployment Zone depth
guides at 300–400 points and adds a 6-/8-/12-inch placement ruler from
the left table edge to the left Antenna. The right Antenna is its mirrored
counterpart at the same distance from the right edge; a duplicate right
ruler would collide with the nearby vertical Deployment Zone dimensions.
In Neutralization, the right Antenna's 4-inch
guide stays 3 inches **above** the marker with its caption above the
line, while the upper Deployment Zone depth guide moves to the left edge.
The player-facing maps now omit **edge-to-center placement rulers** for
objects fixed at the exact table center; their centered positions remain in
the geometry and source-backed setup rules. For **fully mirrored placement**
or equal upper/lower zone dimensions, show just one representative ruler
(e.g., Corporate Appropriation's left Prototype and B-Pong's upper half of
the Exclusion Zone). Keep off-center placement distances, measured
object-to-object spacing, quarter-circle deployment radii, and relevant
Deployment/Exclusion Zone dimensions. This affects both ITS 17 and 18
without changing any physical position, zone boundary, or source claim.
Ruler offsets remain presentation-only.

For central **8-inch square rooms** (Last Launch's Launching Tower and
Critical Intervention's Server Room), the 8-inch room-width helper is a
horizontal ruler **below** the room, with endpoints derived from the
room's left and right edges. Its placement leaves clearance for Critical
Intervention's physically sized Inhibitor Antenna. Both rooms have four
**Wide Gates** centered on their walls and open at game start; maps
depict them as four labeled breaks in the wall outline. The displayed
gate gaps are **schematic, not physical measurements**: neither source
gives a gate width. Their purpose is to admit Troopers regardless of
Silhouette (explicit in the Spanish text), so estimates such as
35 mm minimum clearance are not treated as official values. The
existing 8-inch EN / 20-cm ES room-size discrepancies remain preserved.

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
N5 core missions continue to use Rules. The complete-set factory registers both
`its-18` and `its-17` from their independent databases, validates the
four-file set, and resolves each ITS season to its sole published revision.
Both local `serve` and production WSGI/Docker use this same factory;
the runtime cache fingerprint includes all four exact file hashes.
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

**The release bundle contains four files:**
`army.db`, `rules_n5.db`, `its_18.db` and `its_17.db`. The selected set
does not autodiscover additional files. ITS 17's 16 source-reviewed scenarios
are explicitly registered at V0.2 using the pinned shared authoring library;
ITS 18 remains at its hotfix revision. The historical V0.0/V0.1 ITS 17
revisions remain internal evidence and are not selectable.

## Migration boundary

The Rules exporter excludes ITS-owned curated collections. Each ITS season
owns its own Battleground scenario membership and source citations in
`its_17.db` or `its_18.db`; the four-file runtime exposes each only under
its selected season. Earlier source-family revisions remain internal
historical facts, not independently selectable publications. N5 core
scenario facts, attribution and the shared renderer remain unchanged.

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
regenerate the four-file release set before source-bound deployment
checks or merge.

For the ownership and scope exceptions (Spec-Ops, TEAM-OPS,
Reinforcements, marker citations, FAQ), see
[season publication ownership](season-publication-ownership.md).
