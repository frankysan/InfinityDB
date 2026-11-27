# Scenario data model

**Project domain:** Data processing

This document owns the shared Core/ITS scenario definition, configuration,
scoring and geometry model. [Season publication ownership](season-publication-ownership.md)
owns authority and selection; [ITS database](its-season-database.md)
owns season-specific schema, registered source libraries and reviewed
mission/diagram evidence. The [curated format](../data/curated/README.md)
owns authored fields and validation. None of these static definitions
evaluates live match state.

## Scenario model (implemented core and future extensions)

### Current scenario foundation

All four N5.3 Core scenarios use authoring definition v2. They compose explicit shared definitions
by typed identity inside the rules collection; display names never select or merge definitions.
`scenario_components.py` validates references, applicability, component kinds, override fields, and
cycles before the normal scenario/geometry validators check the resolved payload. Inline v1 payloads
remain readable for compatibility. Runtime export materializes the composed v1-shaped payload into
`rules_n5.db`; runtime queries never need the authoring library or working-tree curation.

Rules and Skills are separate normal semantic records. Scenario Rules use `facts.category:
scenario-rule`, ordered `effects`/`restrictions`, and optional `definesSkills` references. Hack
Consoles and Pick Up Supply Boxes are scoped Skill definitions with the same `typeIds`, `labelIds`,
Requirements, Effects, Restrictions, and citation contract used by other Skills. Including the owning
Rule derives the scenario Skill list. `scope.scenarios` explicitly limits applicability; these
definitions have no Army links and are excluded from default core composition. Contextual composition
selects them with an explicit scenario slug or typed ID. Same-name functions may have distinct IDs;
no name-based deduplication or implicit season/revision fallback occurs.

The collection's versioned `scenarioComponents` library owns reusable typed `setup`, `geometry`,
`objective`, and `end-condition` payloads with citations and explicit scenario applicability. Setup
inclusions may override named game-size `swc`/`minimumVictoryPoints` fields by exact Army Points.
The common deployment rows, standard Annihilation/Firefight geometry, three-round ending, all-Null
ending, and minimum-VP ending are shared. Domination retains its explicit 350-point 6 SWC override.
Objective definitions use the same reference mechanism; geometry titles come from the including
scenario as presentation metadata. Unsupported fields and mismatched component kinds fail closed.

Ordinary component references are collection-local. Explicit versioned
libraries may import shared scenarios, Skills and components at build time.
Each registered season materializes its own selected records; no
request-time authoring-library dependency is introduced.

### Accepted cross-season scenario and Skill reuse

The supported authoring contract is in the
[ITS database guide](its-season-database.md). Preserve one genuinely
shared definition with a stable typed identity and pinned version.
Selection, source citations, review, membership, season/revision and
scenario applicability remain independent. A changed mechanic needs an
explicit version or allowlisted scoped override; similar names alone do
not establish equivalence.

Scenario Skill catalog and Search publish one entry per reviewed identity,
retaining source names and scoped
URLs as aliases. The canonical `rules` card contains the shared definition
when identical, or reviewed common mechanics and exactly common clauses when
different. `scenarios` identifies applicable publications and
`context_variants` retains the exact source rules, facts, types, labels and
citations grouped by matching definition. Scenario cards and scoped URLs
continue to expose only their own definition. Explicit pinned shared Skill
identities use the same projection. Differing facts under the same unmodified
pinned version or conflicting origins still fail closed; a reviewed override
or distinct pinned version may differ. Similar names alone do not establish
equivalence. Core and season databases remain independently materialized.

`sharedSkillBindings.overrides` accepts exact `{scenarioId, ruleId, field, value}`
entries with complete replacements of Requirements, Effects or Restrictions
prose arrays. Missing bindings, duplicate/invalid fields and conflicting
origins fail. A shared component may be referenced by exact typed ID and
version; each membership retains its own `componentCitations` and
compiled `componentSources`. No citation leaks from a reused component
to a different mission automatically.

The reviewed `sharedSeasonSkillBindings` array supports exact
`{id, version, name, summary, category, applicability, citations, review}`
memberships without scenario IDs. The referenced `skills` library entry
supplies `skillTypeIds` and `skillFacts`; each season selects a pinned
definition version and retains its own citations, review, revision and
`season` or `team-ops-extra` applicability. Optional tournament Extras
do not make Team-Ops or Request a Tacball unconditional Skills.
Resolved standalone Skills live in each season's own SQLite `records`
table and are projected into catalog/Search; exact equivalent pinned Skills
across seasons consolidate into one canonical identity with independent
citations. Conflicting same-version facts fail closed. Explicit distinct
pinned versions of one identity, and the reviewed source-local CivEvac and
Casevac definitions, share the unqualified catalog route while retaining
season-qualified exact rule routes and contextual cards. Other independently
curated season Skills are not merged by name alone. Existing scenario-specific
Skill routes remain compatible.

Materialize the complete resolved payload in each season's SQLite artifact,
including the selected definition version and relevant provenance, so
publication validation, read APIs and deployment do not depend on another
season's database at runtime. Authoring should respect the existing
one-source-family-per-logical-source preference and revision-tagged facts;
sharing definitions does not combine independent official source histories.
Only current applicable versions remain player-facing by default.

The complete builder registers the source and any shared library explicitly;
ITS 17 uses its pinned authoring library, ITS 18 remains source-local.
Library, source and selected publication hashes are validated, and compiled
season databases remain independent. Current reviewed cross-context
Skill consolidation does not establish that all season mechanics are
equivalent. Generic component payload overrides and broader historical
replay remain future work in [TODO](TODO.md#its-scenarios-and-game-tools).

## Publication identity and selection

Current publications are `n5-core@5.3` (four Core missions),
`its-17@0.2` (sixteen missions) and `its-18@2026.09.11`
(twenty missions). Both ITS seasons cover 150/200/250/300/350/400
Army Points. Superseded versions remain in the authored source families.
The [publication registry](season-publication-ownership.md#stable-selection-and-identity-contract)
resolves the exact collection/revision/typed scenario identity. Normal
selection is latest-only per season; the unqualified catalog is Core.
Historical lookup is not a historical public scenario detail/map API.

Core relational tables retain `scenario_collections`,
`scenario_collection_revisions`, `scenario_publications` and
`scenario_memberships`, separating logical identity, source revision,
content fingerprint and ordered membership. ITS stores its own
materialized records and membership. Rebuild the matched complete set
after changing maintained inputs.

**Explicit published-set selection:** `ScenarioCatalog.list_scenarios(collection=...,
revision=...)` and `get_scenario(..., collection=..., revision=...)` filter current
composed scenario publications by the exact stable scenario-set ID and revision. The public
`GET /api/scenarios`, `GET /api/scenarios/:slug?army_points=...`, and
`GET /api/scenarios/:slug/map.svg?army_points=...` endpoints accept the same optional
`collection` and `revision` parameters **only as a pair**. Unknown pairs give an
empty list or HTTP 404 for detail/map; malformed/partial/repeated selectors give HTTP
400. Omitted selectors keep the legacy current-catalog behavior. This prevents an
explicit ITS season request from silently returning N5 Core information. The API
currently exposes only modeled **current** publications; a historical membership lookup is not
yet a historical compositional detail/map API.

Current scenarios can declare `facts.playRequirements` with non-negative
per-player counts for `classifiedObjectives`, `tacticalObjectives`, and
`hvts`. An optional `sharedClassifiedObjectivesPerRound` records the base
shared count. The detail API projects this as `setup.play_requirements` and
Forces and table displays zero as “Not used”. Older records without reviewed
counts omit the summary. Counts are mission facts independent of scoring, with
the standard ITS HVT and Tactical Objective scope sourced to ITS 18
2026.09.11 pp. 35–38 and mission-specific counts to their mission sections.

## Scenario detail, scoring and applicability

Specialist Troops uses one **unscoped, InfinityDB-owned General Rules
presentation** of the shared Rule `rule:specialist-troops:standard`, published
at `/rules/specialist-troops-standard` and in global search/Glossary.
Its source citations remain the scenario sections in N5.3, not a claim that
the official core rules define a universal Specialist Troop attribute.
`facts.specialists.anyOfSkills` is the standard qualifier list as complete
Skill IDs. Scenarios explicitly include the same Rule and author only
`addSkills` and `removeSkills` differences; only the selected scenario
determines whether a Trooper qualifies. General Rules details derive
**Used by** links from actual scenario inclusions, rather than maintaining a
second relationship list. Resolution rejects unknown, duplicate, conflicting,
or non-baseline removals and produces an effective qualifier list without changing the baseline.
Doctor/Engineer Peripheral restrictions and the Chain of Command (Non Specialist) qualification
exception are maintained once. That exception affects qualification through Chain of Command,
without disqualifying a Trooper that has another qualifying Skill. This is a reference list and
exception statement; the catalog does not evaluate game state or assign permanent profile roles.

The Unit Explorer's optional `specialist` filter selects either `standard`
(the InfinityDB general reference) or a named core scenario with a reviewed
Specialist inclusion (`domination`, `supplies`, `firefight`). The API
resolves the effective qualifier list from `rules_n5.db` (including any
scenario-specific add/remove overrides), then checks the current Army Skill
occurrences via the existing Skill catalog. Chain of Command occurrences
marked **Non Specialist** are excluded only as qualification through that
Skill; another qualifying Skill still counts. Filtering is at the logical
Unit level: a match means **at least one** profile, loadout, or Unit option
contains a qualifying Skill, not that every profile or Army list is a
Specialist, nor that currently selected Army contexts are all eligible.
This candidate-set filter intersects with other logical Unit filters,
respects existing availability flags, and does not persist new Unit facts.
Unsupported scenario names fail as invalid query selections; a missing
reviewed baseline or Skill identity fails closed instead of silently
inventing eligibility.

`ScenarioCatalog` builds list/detail read models from the selected
publication. Detail requires one exact supported Army Points value;
it includes only that game-size row, applicable awards, selected geometry,
scope-specific issues and composed Rule/Skill records, retaining
`componentSources`. Normal Core reference composition does not acquire
scenario-only actions. Orders/AROs keeps a core matrix and an optional
selected Core scenario extension; scenario-specific declarations are
not universal. Browser selection defaults to 300 and uses versioned
share-state; legacy explicit `army_points` remains readable.

The resolved mission owns ordered sides, all six Army Points/SWC rows, deployment references into
its geometry, objectives/awards, Rule inclusions, Skills, end conditions, and source issues. Every
geometry-supported Army Points value has exactly one game-size row, and every objective covers
those values. Deployment regions resolve in the selected geometry with multiple regions per side
supported; objective side applicability remains explicit.

Scoring awards may use inclusive integer `numeric-range` conditions (an unbounded upper limit is represented
by `maximum: null`) or `reviewed-prose` conditions with semantic maintained-text tokens. The initial
numeric metrics are killed enemy Army Points and surviving Victory Points. Each objective declares
its scoring timing, `exclusive` or `cumulative` aggregation, and Objective Point cap. This records
reference semantics without evaluating match state. Exclusive numeric ranges must not overlap unless
a `needs-verification` source issue names that objective and Army Points row. A `needs-verification`
issue preserves unresolved uncertainty; it does not select a winning band or authorize a rules
correction. A `reviewed-resolution` source note instead records an explicit maintained interpretation
of a known source discrepancy and cannot excuse overlapping ranges.

Scoring supports typed range, metric comparison, dominated-region
comparison, marker status count/comparison and reviewed-prose conditions.
Keep metric/side, timing, exclusive/cumulative semantics, per-round
and whole-mission caps, exact marker/region references and game-size
thresholds. Strict greater does not include a tie. A reviewed-prose clause
can describe a scoring requirement without implementing a calculator.
End conditions preserve check timing versus actual completion timing;
minimum-VP and all-Null conditions remain distinct.

Source notes/issues target exactly one `objectiveId`, `gameSizeField` (`swc` or
`minimumVictoryPoints`), or non-empty `geometryElementIds` list and name their applicable Army
Points. Geometry references must resolve in every applicable configuration. `needs-verification`
marks unresolved source uncertainty; `reviewed-resolution` records a maintained interpretation after
review. Only an objective-scoped `needs-verification` issue may acknowledge an otherwise-invalid
overlap, while game-size, geometry, and reviewed-resolution notes cannot excuse one. Domination
preserves the English N5.3 value of 6 SWC at 350 points from printed page 151,
with a game-size `needs-verification` note because Spanish N5.3 printed page 155
instead has 7 CAP/SWC for that same Domination row. This is an unresolved
official cross-language conflict, not merely a possible progression exception.
The ordinary 350-point Domination setup visibly flags the SWC cell as
source-disputed, with a keyboard-accessible in-page link to the full
`needs-verification` note under Source notes. This warning is sourced
from the existing game-size issue and is absent for other point values
and other scenarios. The issue stays unresolved pending a future official
clarification; neither edition is silently treated as an erratum.
Printed English pages 151–152 cite the mission rules.

Other exact Core source decisions (e.g. the Annihilation 350-point
reviewed survival-band correction, Supplies 8-inch outer markers,
and Firefight's mission-local deployment/Lieutenant overlays) remain
authored with reviewed notes and citations in the scenario definitions.
Use the [historical Core source decision evidence](https://github.com/frankysan/InfinityDB/blob/a7fc1900d73e4bc9b44561c20b04e58e73fbb8b6/docs/data-model.md#accepted-cross-season-scenario-and-skill-reuse)
for original reasoning. Do not substitute later publication facts or
generalize scenario-local Skills to Unit profiles.

## Geometry and physical markers

Geometry format 1 uses canonical inch table dimensions, ordered unique
element IDs and supported `rectangle`, `line`, `circle`,
`quarter-circle`, `marker` and `label` elements. Coordinates use
absolute inches or table-relative edge/center anchors with offsets.
Style and marker types are stable semantic identities. Annotations
`dimension`, `area-size`, `element-edge-distance` and `ruler`
reference/measure maintained semantic geometry, not alternative
gameplay coordinates. `scenario_geometry.py` owns validation; the
renderer projects the semantic coordinates without reading PDF artwork.

Rendered measurement text carries the canonical inch value in
`data-distance-inches` or `data-distance-size-inches`, separate from the user-facing display unit.
The map API accepts optional `distance_unit=in|cm`, using the Infinity distance convention
of 1 inch = 2.5 cm, and optional `theme=light|dark` (default Light). Its standalone SVG
embeds the selected theme's canonical map palette and resolves CSS variable references
in styles and hatch patterns to literal colors and font sizes for standalone viewers.
Measurement endcaps use a contrasting under-stroke at their original coordinates.
Browser pages retain it as a normal image element for Save Image As; theme and distance-unit preference events change the
image URL without altering the inch viewBox or stored geometry. Marker `data-diameter-mm`
remains unconverted physical metadata.
It also supports `element-edge-distance` annotations for markers and rectangles: the
displayed distance is derived from the target element's nearest physical boundary and selected table edge,
while an optional signed offset controls only where the dimension line is drawn. Scenario source language
such as “X inches from” is interpreted edge-to-edge unless the source explicitly names a center/reference
point. `marker` stores a semantic center point with a stable `markerType`. Known marker types
resolve to canonical marker metadata; an optional reviewed `diameterMm` records a source-specific
footprint when no common type diameter exists. Use an override only when its exact source supports the instance size;
unknown or disputed sizes stay unresolved. The same resolved diameter drives the SVG,
catalog metadata, boundary validation and marker clearances. Physical diameter is semantic when it defines the represented game object,
not merely SVG styling. N5.3 Domination requires each Console to be represented by a Console A Marker
or scenery of the same diameter, indirectly making that canonical footprint part of the scenario rules.
The ITS token-diameter table provides the explicit numeric dimensions used by the core fixtures:
**Console 40 mm** and **Supply Box 25 mm**. Validation rejects unsupported fields, invalid anchors,
duplicate IDs, non-finite values, unsupported element kinds, and geometry that resolves outside the
table. Geometry itself does not require symmetric regions or one Deployment Zone per side. The SVG
renderer owns its narrower presentation capability: it maps the current semantic style identities to
CSS, requires canonical physical metadata for markers it renders, and raises an explicit render error
for a valid future style or marker it cannot faithfully project instead of substituting a generic
appearance or size. It uses the inch dimensions directly as its `viewBox`; it does not infer rules or
geometry from diagrams.

**Scenario marker sizes** are a derived, read-only setup projection:
`placement.marker_dimensions` enumerates only marker types actually present
in the selected configuration's validated geometry, with occurrence count,
physical diameter in **millimeters**, and a source citation. The existing
`marker_diameter_mm()` registry owns physical sizes; neither table
dimensions (inches/centimeters) nor apparent SVG scale change the footprint.
The pinned N5.3 Core PDF pp. 151 and 153 identifies the Console A and
Supply Box markers. The separately pinned official ITS Season 18 document
(version 2026.09.01, printed p. 17, token diameter chart) supplies their
numerical sizes: Console 40 mm, Supply Box 25 mm. This ITS citation supplies
physical marker metadata only, **not** ITS-specific scenario rules. Domination
has four Consoles and Supplies three Supply Boxes for every supported Army
Points setting; Annihilation and Firefight have no placed scenario-marker
instances. The map's SVG circles retain the same fixed-mm metadata, and
the player-facing setup note keeps that physical measurement distinct from
scoring-area geometry, map drawing scale, and configurable game distances.
Do not invent dimensions for unreviewed marker types.

**Domination Console placement** is another derived *map-only* projection.
The pinned N5.3 English scenario map (printed p. 152) locates each Console
at the center of its scoring Quadrant. The renderer recognizes only the
complete four-Quadrant/four-Console arrangement and verifies that all four
centers coincide before drawing placement rulers. It measures directly
from each Console **center** to its nearest horizontal and vertical table
edges, not from the marker circumference. For the 24 × 32, 32 × 48 and
48 × 48 inch tables, the corresponding nearest horizontal/vertical
edge distances are **6/12**, **8/18**, and **12/18** inches. Measurements
use the normal in/cm game-distance conversion, independently of physical
40 mm Console diameters. The existing four scoring rectangles remain
intact: they define gameplay scoring regions, not small placement zones.
The renderer omits only their redundant dimension annotations in this
recognized setup, retaining all semantic source geometry, marker centers,
zone boundaries, and deployment-depth measurements. No curated data or
generated-database contract changes are required.

The [ITS geometry review](its-season-database.md#release-diagram-acceptance)
owns current season layouts, token footprints, zone styles, ruler
placement and bilingual conflicts. Multiple deployment regions per side,
asymmetric layouts, circles and quarter-circles are supported.
Classified Deck generation, selectable objective sets and live game
tracking remain separate capabilities; do not infer implementation
from the presence of source prose.

## Scenario publication model and remaining design direction

A logical Scenario may have several independently reviewed publications,
with versioned membership and typed applicability. Stable/queryable
facts use relational indexes; nested ordered components retain validated
payloads. Do not parse PDF prose, rendered HTML or SVG to recover
semantic facts. Keep side/role, game-size rows, optional features,
element interaction descriptions, objectives and end conditions in
their owning structured definitions. Extend the existing schema only
for a concrete unsupported mechanic; an unknown type must fail closed
rather than be rendered or scored approximately. Shared components and
references do not copy independent official source history.

## Proposed player-authored scenarios (design direction)

A scenario creator/editor should support **new blank scenarios** and **derivatives of
published scenarios** using the same validated, typed scenario components and
geometry/map projection as the curated catalog. Authors may select preset
Deployment Zone/table maps; assemble preset rule groups or individual Rules/Skills;
add or modify scenario elements, sides/roles, setup, objectives, scoring methods,
end conditions, and custom additions; or author their own components. Presets are
starting points, not frozen inherited behavior. A customized official scenario is
an explicitly labeled *player variant*, never a new official source revision.

The proposed portable scenario definition has explicit identity boundaries:

- A versioned, canonical serialization envelope, including required InfinityDB
  schema/codec version and reference-data or ruleset revision for reproducible
  interpretation. It contains the actual authored changes/content, not only a hash.
- Stable references to official scenario/rule/skill/element identities plus
  deterministic local overrides/additions. Missing or superseded referenced
  content must be surfaced, not rebound silently by title or current-version guess.
- Authored entities carry a local, scenario-scoped namespace; display text does
  not confer official provenance, canonical rule identity, or execution semantics.
- Composition records ordered components where order matters and uses canonical
  ordering for sets/other unordered fields. Avoid redundant copies of reference
  records when a stable reference and revision suffice.

**Custom typed rules are the difficult boundary.** Provide a small, explicitly
versioned and validated vocabulary for fields InfinityDB can honestly represent:
applicability/side, action or trigger, timing, target, scope, quantities/units,
conditions/comparisons, modifiers, scoring, and referenced States/Skills/Rules.
Typed components and custom scenario Skills may reuse existing schema concepts,
but a locally invented rule is not an official Skill or an executable program.
Author-defined prose remains first-class for rules outside the supported typed
vocabulary, marked **descriptive/not machine-evaluated** rather than mis-parsed
or falsely validated. No arbitrary code/evaluation, external URL execution, or
silent conversion of unsupported user clauses into executable behavior. Explicit
schema extensions and migration are needed before claiming support for novel
mechanics. The editor may check structural validity without adjudicating a game.

The authored definition should live in transient browser state and travel via a
self-contained share URL or user-initiated export/import file; no server storage,
user uploads, or automatically persisted authored scenarios. Reconstructing from
URL data and the packaged reference revision must work offline. See the
stateless-sharing decision in `docs/architecture.md`; this is deferred design, not a current publication or serving capability.
