# Data model

**Project domain:** Data processing

This document owns InfinityDB's **current semantic and persistence model**. It describes what the
source means to InfinityDB, which abstractions the project introduces, how those facts are stored,
and which invariants runtime queries rely on. Historical audit counts, release benchmarks, and
migration chronology belong in Git history or `docs/CHANGELOG.md`, not in this current-state
contract.

Unless explicitly marked otherwise, statements below describe the current repository model.

## Pipeline and persistent artifacts

Army-derived data flows through three conceptual layers:

```text
immutable Army snapshot
        ↓
lossless merged/master representation
        ↓
validated normalized source model
        ↓
SQLite export
        ├─ infinity.db      canonical application/runtime data
        └─ infinity.raw.db  lossless normalized source/audit archive
```

Curated rules data follows a separate path:

```text
reviewed data/curated/rules/*.json
        ↓
validation/composition
        ↓
rules.db
```

The two runtime databases are intentionally separate because Army data and reviewed rules knowledge
have different sources, provenance, and update cadence.

For weapon families such as Mines, a shared curated rule describes only the common
mechanics. The individual Army weapon profile identifies ammunition, PS, Saving Rolls,
and Traits; the corresponding ammunition, State, and Trait rules determine the
weapon-specific effects. Attaching `weapon:mines` to a weapon
does not create a generic "ordinary Mine" weapon or make the variants interchangeable.
Variant-specific effects require their own source-derived weapon profile and, where
necessary, curated exceptions or relationships. A reviewed family clause is not
evidence that every named weapon variant has complete rules coverage.
An Army Weapon source ID can also cover multiple modes (Kobra Pistol: source `221`,
BS Mode and CC Mode). Curated source rules may target an exact source ID *and*
mode, but must attach to that one profile only, not to the parent Weapon/source
variant or sibling modes. Mode qualifiers describe identity, not permission to
resolve a disputed Trait automatically.
Weapon Ammunition navigation is a reviewed *projection*, not executable Ammunition
composition. `config/catalogs/weapon-ammunition-references.json` pins exact Army
metadata Ammunition IDs and names to canonical published base Ammunition references.
The repository preserves the source metadata ID as `ammunition_source_id` in each
Weapon profile; the catalog API attaches ordered `ammunition_parts` only when both
that ID and its name match the reviewed map. A base type links to one reference;
source-defined `AP+DA`, `AP+Exp`, `AP+Shock`, and `AP+T2` link their reviewed
components separately. Version 2 of the maintained mapping also records those
ordered components as canonical `ammunition:*` IDs; the validator requires exact
agreement with the linked display segments and literal `+` separators. The
Weapon API exposes `ammunition_composition: {kind: "combined", components: [...]}`
only for an exact Army source ID/name pair with published reference targets.
Single Ammunition profiles do not receive a synthetic composition. Alternative
(`/`), absent, or mismatched values remain source text; they are not guessed
from punctuation. Saving Roll notation (`ARM/2`, `x2`, etc.) remains a distinct,
unchanged source field and is never interpreted as Ammunition composition.
The first reviewed Ammunition effect pilot now lives on canonical `ammunition:*`
records, not on Army mapping entries. The validated, non-executable
`facts.ammunitionResolution` object can describe halving the applicable ARM/BTS
Attribute (AP), two Saving Rolls per hit (DA/E/M), and E/M State outcomes with
failure conditions and eligible target categories. The EXP, PARA, and T2
extensions add three rolls per EXP hit; a PH-6 Saving Roll with no effect
against targets lacking PH and Immobilized-A on failure for PARA; and
separate T2 Wound counts for a failed hit roll versus a failed additional
Critical roll (2 versus 1). Normal and Shock record one Saving Roll and
one Wound per failed roll; Shock's direct-to-Dead outcome applies only to
failed rolls against targets with VITA 1. Stun records the Stunned State
and automatic Guts Roll failure on a failed Saving Roll, except with Courage
or equivalent rules. These facts flow through `rules.db` to Ammunition detail
APIs with the records' existing citations. Smoke and Eclipse instead use a
separate `facts.visibilityZone` shape recording the Circular Zero Visibility
Zone, infinite height, expiration, and the distinction between Smoke's MSV
exception and Eclipse's Reflective blocking of all MSV Levels. This is
visibility reference data, never a synthetic Saving Roll or a guarantee
that a Smoke Template succeeds against all attacks. The
Weapon API separately exposes source-authored profiles and reviewed combined
component IDs. It does **not** merge these facts into an inferred roll result:
Feuerbach's AP+DA source combination remains distinct from its `ARM/2` and `2`
fields, and Plasma Carbine's `ARM and BTS` / `1 and 1` remains a Combined Saving
Roll with Normal Ammunition, never a synthetic composition.

All eleven published base Ammunition identities now carry reviewed typed
facts, but the contract is deliberately non-executable: it does not model
critical attack resolution generally, Smoke/Eclipse Face to Face adjudication,
all conditional immunity/target interactions, or combined-Ammunition
precedence. This is not yet a complete curated Ammunition effect/relation model or a
general combined-Ammunition evaluator. Conditional State outcomes are also
published as authored `causes-state` rules-graph links for E/M, PARA, Shock,
and Stun. The curated validator requires the set of targets on these links to
match `facts.ammunitionResolution.stateEffects` exactly; target/attribute
restrictions and Saving Roll failure conditions remain in the typed facts,
not on the simple relation edge. Both directions of each link are available in
reference pages. Nine roll-bearing base Ammunition records now also carry
`criticalAdditionalSavingRolls: 1`. This represents the single extra Saving
Roll from a Critical, not a multiplicative roll count per combined component.
Smoke and Eclipse retain only visibility-zone facts and no Saving Roll facts.
For the four reviewed Combined Ammunition forms, the component mapping still
publishes identities only: it does not add, multiply, or adjudicate those rolls.
The additional roll retains applicable constituent effects; T2's
`woundsPerFailedSave.criticalAdditionalRoll` remains distinct from its regular
hit effect. Combined Saving Rolls (including Plasma's ARM/BTS case) have a
different extra-roll target rule and remain outside this fact pilot.
The other Ammunition effects, complete combined Critical interactions,
and broader semantic relationships still require source review.

The separate reviewed Combined Saving Roll projection now pins the six
Plasma Carbine, Plasma Rifle, and Plasma Sniper Rifle Hit/Blast source profiles
(including the source spelling of each name). Only exact source ID, mode,
Ammunition identity, and Saving Roll fields receive
`combined_saving_roll: {kind, rolls, critical}` in the Weapon API. The pinned
N5.3 rule specifies one additional **ARM** Saving Roll for a Critical, on top
of the ARM and BTS Saving Rolls from the hit. This is a reviewed source-profile
annotation, not a roll evaluator, an Ammunition effect, or an inferred
`ammunition_composition`. Other Weapon Saving Roll notations remain untouched.
Full cross-source Combined Saving Roll coverage and immunity interactions remain
open.

A bounded Immunity cross-reference now publishes `skill:immunity`'s validated
`facts.immunityInteraction` (N5.3 Wiki Immunity `oldid=3643`). It describes
covered Ammunition as Normal, the loss of special effects and Saving Roll
modifiers, the default additional Critical Saving Roll (unless the defender has
Immunity (Critical)), and the Comms Attack/Non-Lethal/Stunned exceptions. These
facts belong to Immunity, **not** to the ordered Combined Ammunition mapping:
checking whether a defender's particular Immunity covers an entire attack or
one or more constituent effects remains unimplemented. Three `reviewedCombinedCases`
now give **rule-derived, conditional** examples: Immunity (ARM) against source
IDs 10 (AP+DA) and 13 (AP+Exp), plus Immunity (AP) against AP+DA only.
The AP case records its ignored AP component and surviving DA effect, retaining
two full-ARM rolls (three on Critical), instead of collapsing to Normal.
Each example preserves before/after hit and Critical counts with source IDs,
components and explicit evidence status. They are stored on Immunity rather
than on the Ammunition navigation mapping. No roll counts, State outcomes, or
immunities are projected into individual Weapon profiles. A separate
`reviewedVulnerabilityCases` entry records the **explicit** Vulnerability (Viral)
versus Immunity (Enhanced) example (Wiki Vulnerability `oldid=3156`): the rule
matches a weapon whose *name* contains Viral, not an Ammunition component.
This example adds no weapon-name parsing at runtime. An independent, explicit
`reviewedWeaponCases` entry records the pinned Immunity (BTS) versus Flash Pulse
example (Wiki Immunity `oldid=3643`, Weapon Chart `oldid=4083`): Stun becomes
Normal, but Non-Lethal and Stunned on a failed Saving Roll remain. Flash Pulse
has its own cited Weapon reference and semantic links; none of these cases
executes a Weapon profile calculation. Other component Immunities, BTS
conditions and unreviewed combinations remain unresolved.

The Perimeter Trait likewise does not imply Boost. A WildParrot uses
Perimeter deployment followed by E/M Mine behavior with a visible Token/Model;
its specific rules are separately curated, and missing Army Trait notation is
not manufactured from the printed rulebook.

Current runtime database versions:

- Army application database schema: **25**;
- Army application compatibility revision: **34**;
- rules database schema: **8**;
- rules database compatibility revision: **10**.

`data/README.md` owns source/snapshot format versions, while `data/curated/README.md` owns the
curated-rules format version. Schema and compatibility validation is fail-closed. Incompatible
generated databases are rebuilt; there is no in-place migration contract for current generated
Army/rules databases.

## Semantic provenance

A field or relationship must be understood by provenance class before it is deduplicated or
presented.

### Source-native facts

These are represented directly by Army or another cited source: source IDs, names, profile values,
loadout costs, Army-list membership, source extras, notes, Fireteam rows, and similar material.
InfinityDB may normalize their representation but must preserve their source coordinates and meaning.

### Source-derived facts

These are deterministic interpretations of explicit source relationships, such as Army grouping or
role derived from metadata parents and reinforcement links. The derivation is application logic, but
the evidence remains source-owned.

### Curated/reviewed facts

These are human-reviewed project data derived from official sources where the application needs a
stable relationship the upstream data does not directly supply. Examples include identity aliases,
legacy Army presentation records, Peripheral mappings, historical relationship endpoint evidence,
maintained rules summaries, and typed rules relationships.

### InfinityDB abstractions

These are application concepts introduced to make multiple source views coherent. They must not be
presented as if they were source-native. Important examples are:

- logical Units spanning equivalent source representations;
- the General profile abstraction;
- canonical profile/loadout payload identities;
- application-domain slugs; and
- cross-domain composed reference projections.

### Presentation-only structure

Browser grouping, card/disclosure structure, responsive layout, visual labels, and other display
conveniences are not game-data semantics unless backed by a data-model contract.

## Identity model

InfinityDB keeps **source identity**, **application identity**, **relationship context**, and
**presentation identity** separate.

### Army identities and roles

`application_armies` is the canonical runtime Army projection. Army-list source records and metadata
factions are evidence used to build that projection; they are not interchangeable identities.

Current roles include main, sectorial, non-aligned/grouping, and reinforcement. Role/grouping is
derived from imported relationships and reviewed policy rather than ID ranges. In particular:

- source identity `1` remains mercenary source provenance;
- current Non-Aligned application grouping is represented separately (source grouping identity
  `901` in the current snapshot);
- reinforcement lists retain explicit parent relationships; and
- a grouping identity may exist in source metadata/source lists without being independently playable.

Playability, catalog/discontinued status, grouping, parentage, concrete roster availability, broader
faction membership, and browser display identity are separate facts.

`main_army_id` is a compatibility-named application grouping field, not authoritative roster
membership. `display_army_id` is the reviewed presentation identity used for faction symbol/styling
where it differs from source/main grouping. Browser code consumes these projections rather than
special-casing Army IDs.

### Logical Units

A logical Unit groups source Unit representations that reviewed/source-derived evidence says are the
same application Unit. Build-time identity processing materializes that mapping; runtime queries do
not recompute it from names or ID arithmetic.

The logical Unit layer owns game-wide Unit identity and aliases while preserving every source
occurrence needed for Army/profile/loadout context. A reinforcement or optional-mercenary source
representation can therefore belong to the same logical Unit without erasing its distinct
availability path.

Configured aliases remain maintained policy and are pinned into generated metadata; they are not
rewritten into source rows.

### General profile

The **General profile** is an InfinityDB abstraction for profile information that can safely be shown
once for a logical Unit rather than repeated for every Army occurrence. It is not an upstream Army
entity.

Only semantically compatible profile data may be consolidated. Materially different statlines,
profile identities, classifications, characteristics, or other contextual facts remain distinct.
Source profile IDs/names remain available as provenance even when multiple occurrences share one
application payload identity.

### Unit and General-profile symbols

Every published logical Unit has exactly one effective graphical symbol. A General profile inherits
that Unit symbol unless InfinityDB can resolve one distinct profile symbol for its normalized profile
identity. Raw Army `logo` values remain occurrence-level provenance and are not themselves the
semantic assignment. The tracked publication retains every authoritative profile-logo resolution as
evidence, including logos that are primary for one source Unit representation, because source Units
can later collapse into one logical Unit while their distinct General profiles remain meaningful.

Army profiles explicitly identified as Peripherals publish into a dedicated
`peripherals/<main-army>/<peripheral-name>.svg` namespace when that profile name is Peripheral-only,
including Units whose primary profile is itself a Peripheral. The Peripheral name comes from Army's
Peripheral metadata when it can be matched without guessing. Main-army folders follow the same
faction-parent hierarchy used by Unit symbol publication. Peripheral is contextual Army metadata,
not a global property of a profile name. When the same physical symbol is evidenced under the same
profile name in both Peripheral and normal Unit contexts, InfinityDB treats that name as mixed-role:
its artwork stays Unit-owned under `units/`, including any additional contextual variants of that
name. Byte-identical occurrences therefore resolve to one Unit-owned symbol, while genuinely
distinct artwork remains preserved as separate Unit-profile assets. Likewise, if Army reuses parent
Unit artwork for a Peripheral occurrence, the physical asset remains Unit-owned. Distinct physical
assets for Peripheral-only names remain preserved as context-suffixed Peripheral variants rather
than being silently discarded.

The tracked symbol publication may promote a cross-Unit profile-symbol consensus when one
published symbol is a strict majority across distinct parent Unit symbols for that profile identity
and is observed as a non-Unit override against at least two different parent Unit symbols. Repeated
Army occurrences of the same Unit count once. This permits
InfinityDB to repair repeated Army assignment errors without treating a single Army-specific
variant as a global graphical identity. Ambiguous contextual evidence falls back to the Unit
symbol rather than exposing multiple effective symbols for one General profile.

### Profile and loadout payloads

Profiles and loadouts are treated as structured semantic payloads rather than deduplicated by display
name alone.

- A **profile payload** owns profile statistics and profile-scoped categorical facts.
- A **loadout payload** owns shared loadout content such as weapons, equipment, skills, Orders,
  and includes. Points and SWC belong to `loadout_payload_occurrences`, so equivalent content can
  be shared without erasing Army-specific prices.
- Context tables connect those canonical payloads back to source Unit, Army, profile-group, and
  loadout occurrences.

Exact structural equality is useful evidence but does not by itself justify semantic identity when
source context says two records mean different things. Conversely, equivalent payloads may be shared
when the contextual relationships remain explicit.

### Application catalog identities and slugs

Skills, Equipment, Weapons, and other application domains may group multiple source IDs/labels into
one canonical browsing identity. Source membership remains materialized so filters and usage queries
match every member of the application identity.

Where a domain has a stable slug:

- generated application-facing links and maintained references prefer the slug;
- numeric IDs remain accepted for compatibility/provenance;
- the domain's central resolver owns both forms; and
- consumers must not derive slugs independently from labels.

Rules/reference semantic IDs (`skill:...`, `equipment:...`, etc.) remain distinct from public route
slugs even when they correspond one-to-one.

## Availability and membership

InfinityDB distinguishes several relationships that source data often places near each other:

- **Army-list availability** — the Unit/profile/loadout occurs in a concrete Army list;
- **optional availability kind** — standard, mercenary, Spec-Ops, Team Operations, reinforcement,
  or other explicitly normalized availability path;
- **broader declared faction membership** — source-declared game-wide faction relationship that may
  exist even without a current selectable Army list;
- **main/grouping identity** — application grouping context;
- **display identity** — browser presentation context.

`army_units.availability_kind` is persisted application data. Runtime optional-unit filtering consumes
that classification rather than reconstructing it from source IDs.

Unit-list counts and roster membership operate on logical Units with concrete application Army
availability, so duplicate source representations do not inflate player-facing totals.

## Context-coherent filtering

Profile/loadout-sensitive filters must be satisfied in one compatible occurrence context.

- AVA belongs to an Army/profile occurrence.
- Points and SWC belong to loadout occurrences.
- Troop Type, Classification, Characteristics, profile Skills/Equipment and other profile facts stay
  with their owning profile/profile group.
- Loadout-local Weapons/Equipment/Skills stay with the loadout.
- Unit-option facts remain Unit-wide when the source does not attach them to a profile group.

When AVA/Points/SWC participates in a query, another selected profile/loadout criterion cannot be
satisfied by an unrelated option elsewhere on the same logical Unit. This prevents semantically
impossible cross-option matches.

Unit Explorer filter vocabulary may also apply a maintained application overlay without rewriting
the source facts. A combined source Classification can participate in more than one public
Classification filter, while source Characteristics that duplicate a canonical current Skill can be
omitted from the picker as redundant. The original category/characteristic rows remain preserved
and direct identifiers remain queryable for compatibility and provenance.

AVA preserves `Total` as a first-class display/exact-filter value. Negative ancillary/source AVA
sentinels are not ordinary player-facing AVA values. SWC preserves ordinary costs separately from
bonus/non-cost source forms such as `+1`, `+1.5`, or `-`; numeric ranges apply only where numeric
ordering is meaningful.

## Source-specific Unit information

Some source material is useful but cannot safely be promoted to game-wide Unit facts.

### Source notes

Non-empty source Unit notes are retained with source Unit identity, representative/source status,
and applicable Army contexts. The application may present those notes on the logical Unit while
keeping attribution visible.

### Composite Unit options

Top-level source options that combine multiple loadouts remain source-context bundles. InfinityDB
preserves their cost, miniature count, Order contribution, included loadouts, and source/Army
context. Source-local option IDs are not canonical cross-Army identities unless separately reviewed.

### Selection and dependency constraints

Reviewed source selectors and same-Unit profile/loadout dependencies are materialized only when their
meaning can be represented without inventing list legality. Opaque source selector parameters remain
provenance rather than being treated as a complete list-builder rules engine.

## Peripherals and Controllers

Peripheral source encodings are normalized through a separate reviewed identity contract because
Army represents the concept through multiple shapes.

Current application semantics distinguish:

- embedded Peripheral entities/profiles;
- standalone Unit-backed Peripherals that reuse logical Unit identity;
- source mappings from Army coordinates to those canonical targets; and
- Controller access pools, which represent eligibility/selection rather than fixed ownership.

Peripheral subtype classification may link to canonical reviewed rules identities. A mapping that
cannot be supported by the pinned source evidence remains review work rather than being inferred by
name.

Runtime Unit detail consumes the materialized application relationships and never opens the curated
Peripheral JSON directly.

## Fireteams

Fireteam charts are Army-local structured source data. InfinityDB materializes one canonical
application chart per supported Army/source context while preserving:

- chart/type limits, including the raw Army value for provenance while projecting explicit
  `maximum`, `unavailable`, or `unlimited` application semantics before browser use;
- member requirements;
- Wildcards and equivalence context;
- source notes;
- resolved logical Unit targets;
- FTO-eligible loadout references; and
- source provenance.

Reinforcement parent limits remain separate through the application Army graph rather than being
silently merged into a child chart. General Fireteam rules/Level bonuses live in curated rules data
and are composed by the Fireteams application surface; they are not source Army chart rows.

## Relationship model

Application relationships should be materialized where their semantics are understood and useful.
Source storage links that exist only to express normalization shape are not automatically player
relationships.

Important current relationship families include:

- logical Unit ↔ source occurrence;
- Army grouping/parentage and Unit availability/membership;
- Profile/Loadout/Unit-option include relationships;
- selection/dependency constraints;
- Peripheral/Controller relationships;
- Fireteam membership/equivalence/Wildcard context; and
- typed rules/reference relations.

Historical source endpoints that no longer resolve in the current Army snapshot are handled by a
separate snapshot-bound review contract. That evidence can classify a source relation as stale; it
must not create a false alias to a current Unit.

## Rules/reference model

Curated rules collections are versioned and built into `rules.db`. The rules layer is
semantic/reference data, not mutable game state. `data/curated/README.md` owns the current curated
format and validation contract.

A semantic record has a stable typed ID such as `skill:move`, `state:targeted`, or
`ammunition:shock`. Current composition is contribution-based:

- exactly one current `definition` contribution owns the canonical identity;
- optional supplements can add scoped reviewed facts/citations/relations;
- historical/superseded collections remain source evidence but are excluded from normal current
  composition; and
- applicability/review/source provenance remains explicit.

### Domain ownership

The application-domain registry determines which semantic records receive player-facing routes.
Skills, Equipment, Weapons, Ammunition, Traits, States, Hacking Programs, Labels, and selected
General Rules are route-backed reference concepts. Attributes and scoped Game terms are embedded
vocabularies. Fireteam general rules remain owned by the Fireteams surface.

A semantic identity may exist without a dedicated detail route. Search/Glossary/presentation code
must preserve kind/domain and not merge same-name concepts from different namespaces.

Cross-domain discovery may additionally use reviewed `facts.relatedCategories` category slugs.
This adds navigation only: it does not change the record's canonical kind/domain, primary category,
or typed rules relationships.

### Declaration categories and exact source variants

Declaration/action categories are composition metadata rather than standalone public rule records.
Skills, action-like Equipment, and Hacking Programs reuse canonical declaration identities while
preserving source spelling in source storage.

Exact source variants may belong to a family through typed `variant-of` semantics while retaining
their own source-specific facts. Family grouping must not imply that every Level/named variant has
identical rules. When the authoritative rule is naturally level-based, a family definition may also
carry reviewed `facts.levels` entries so the browser can present the level differences as one
comparison surface instead of duplicating near-identical rule cards.

### Typed relations

Rules relations are authored once in the semantic direction and validated against current semantic
IDs. Reverse navigation is derived for presentation. The relation vocabulary includes, among others,
state entry/cancellation, effect reuse/override/negation, modifier interactions, use restrictions,
enabling, triggers, Equipment grants, and Peripheral eligibility.

The edge states the relationship; exact numeric or conditional details remain in the owning rule
facts. Backend composition owns direction-aware labels/grouping for player presentation so browser
JavaScript does not maintain a second ontology.

### Maintained text

Maintained prose supports typed semantic reference tokens and typed distance values. Completed review
batches cover the supported namespaces and reject new plain semantic candidates. Ambiguous text uses
an explicit `review-needed` marker; confirmed ordinary-language collisions are stored as exact
passage fingerprints so changed wording reopens review.

The maintained policy is documented in `data/curated/README.md`.

## Planned scenario model (1.0)

### Current scenario foundation

All four N5.3 core scenarios use authoring definition v2. They compose explicit shared definitions
by typed identity inside the rules collection; display names never select or merge definitions.
`scenario_components.py` validates references, applicability, component kinds, override fields, and
cycles before the normal scenario/geometry validators check the resolved payload. Inline v1 payloads
remain readable for compatibility. Runtime export materializes the composed v1-shaped payload into
`rules.db`; runtime queries never need the authoring library or working-tree curation.

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
References are collection-local; cross-collection historical/season selection remains future work.

Specialist Troops uses one shared Rule, `rule:specialist-troops:standard`, with
`facts.specialists.anyOfSkills` as a JSON array of complete Skill IDs. Scenario inclusions author
only `addSkills` and `removeSkills` differences. Resolution rejects unknown, duplicate, conflicting,
or non-baseline removals and produces an effective qualifier list without changing the baseline.
Doctor/Engineer Peripheral restrictions and the Chain of Command (Non Specialist) qualification
exception are maintained once. That exception affects qualification through Chain of Command,
without disqualifying a Trooper that has another qualifying Skill. This is a reference list and
exception statement; the catalog does not evaluate game state or assign permanent profile roles.

`RulesDatabase.scenario_reference()` reads the composed scenario, its included Rule records, and
its derived Skill records from `rules.db`. `ScenarioCatalog` builds the current player-facing backend
read models on that boundary: list entries retain maintained scenario-set order and publication/source
identity, while detail reads require one exact supported Army Points value. The selected detail projects
only that game-size row, its referenced geometry, applicable scoring awards and source issues, and the
composed scenario Rule/Skill records; it does not choose a default game size or evaluate match state.
Component IDs/citations are retained in `componentSources`.
Scoped Rule/Skill records include backend-resolved scenario names. The shared Skill-card renderer
presents their ordinary rule-detail fields and renders Specialist qualifier references as a list.
Normal browsing/search/glossary calls retain the default unscoped composition; scenario-only content
does not become universal core help. `/api/scenarios` exposes the current collection without choosing
a game size. `/api/scenarios/<slug>` requires one explicit `army_points` query value, rejects
unsupported values instead of substituting another configuration, and projects maintained-text
tokens/public references in the selected scenario context. Dedicated browser scenario pages remain
unimplemented.

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

The Annihilation 350-point surviving-Victory-Points column on page 149 prints inconsistent boundaries:
85–150 awards 1 Objective Point, 176–270 awards 3, and more than 250 awards 4. InfinityDB treats the
two boundaries as typographical errors because the surrounding game-size progression and corresponding
enemy-kills column both use contiguous bands. The maintained reviewed ranges are therefore 85–175,
176–270, and more than 270, with a `reviewed-resolution` source note preserving the printed discrepancy
and the reason for the correction. Its end conditions distinguish the third-Game-Round limit from the Tactical Phase all-Null check,
which finishes at the end of that Player Turn. Printed pages 149–150 cite the full pilot.

Domination adds geometry-referenced scoring conditions: `dominated-region-comparison` compares
each player's dominated-region count with the opponent (`equal` or `greater`), with an optional
minimum own count; `element-status-count` awards the declared points per matching marker element.
The current marker-status vocabulary is `hacked` or `controlled`. Referenced regions/markers must exist with the right
geometry kind in every Army Points configuration covered by the award. These conditions record
the reference rule; they do not evaluate ownership, control, or live game state.

An end-of-round objective may declare `maximumPointsPerRound` separately from its whole-mission
`maximumPoints` cap. Domination awards 1 point for a tie with at least one dominated Quadrant, or 2
for more Quadrants, capped at 2 per round and 6 over three rounds. It separately awards 1 point per
Hacked Console held at game end, capped at 4. All six game-size rows own literal
`minimumVictoryPoints` values (38, 50, 63, 75, 88, 100). The `minimum-victory-points` end condition
requires every row to have that field and distinguishes a Tactical Phase check from completion
at the end of that Player Turn. Its reviewed text preserves the strict below-threshold trigger
and non-Null Trooper basis.

Supplies adds `element-status-comparison`: `greater` compares the player's matching-marker count
with the opponent, while `all` requires every referenced marker to match for that player. Its
three end-of-game objectives remain additive: 2 points per controlled Supply Box (cap 6), 2 for
more than the opponent, and 2 extra for all boxes. Each condition references the same three
maintained Supply Box marker IDs. Carrying is insufficient on its own: control requires a Model
carrier that is non-Null and not in Silhouette contact with an enemy Model. Pickup alternatives,
one-box carrying capacity, Model-only carrying, persistent tokens, and deployment restrictions
remain cited ordered rules; live carriers and control are not stored or evaluated. Supplies
reuses the literal minimum-VP rows and typed end-condition contract, with 7 SWC at 350 points.

Firefight adds `metric-comparison` conditions, currently supporting strict `greater` comparisons
with the opponent for surviving Specialist Troops, killed enemy Specialist Troops, killed enemy
Lieutenants, and killed enemy Army Points. Its four end-of-game awards are 2, 1, 3, and 4 points
respectively; tied metrics do not satisfy a strict-greater condition. Metrics do not imply a
match-state evaluator or derive Specialist eligibility from static Unit/Profile flags.

Its Reinforced Tactical Link, Designated Landing Area, Specialist eligibility, and Killing
procedures remain ordered, semantically linked mission rules. Lieutenant identity is Open
Information; the first-round table requirement and Tactical Phase replacement procedure are
mission-local overlays. The Combat Jump +3 PH modifier and Airborne Deployment permission remain
mission-local too; neither canonical Skill definition is rewritten. Firefight retains the three-
round limit and all-Null ending, with no minimum-VP field on its game-size rows. Printed pages
155–156 cite the mission reference and maps.

Source notes/issues target exactly one `objectiveId`, `gameSizeField` (`swc` or
`minimumVictoryPoints`), or non-empty `geometryElementIds` list and name their applicable Army
Points. Geometry references must resolve in every applicable configuration. `needs-verification`
marks unresolved source uncertainty; `reviewed-resolution` records a maintained interpretation after
review. Only an objective-scoped `needs-verification` issue may acknowledge an otherwise-invalid
overlap, while game-size, geometry, and reviewed-resolution notes cannot excuse one. Domination
preserves the source-specific 6 SWC at 350 points from printed page 151, with a game-size
`needs-verification` note because the value differs from Annihilation's 7 SWC and the usual progression
but may be intentional. Printed pages 151–152 cite the mission rules.

Supplies uses the written placement consistently at every game size: printed page 153 places the
outer boxes `8 inches` from the table edges. Re-review of the 300–400-point illustration on page 154
shows that its `12 inches` mark belongs to a guide ruler; the Supply Box marker itself is visibly
closer to the edge and is consistent with the written 8-inch position. The maintained geometry
therefore keeps the outer markers 8 inches from their respective edges without a source issue.

Console setup, Hack Consoles, Specialist eligibility and the Peripheral restriction, base overlap,
and the Shasvastii exception remain ordered, semantically linked mission rules. Scenario Skills and the shared Specialist Rule now have distinct scoped identities; these rules
do not grant permanent
Unit/Profile capabilities.

Nested mission prose participates in the same syntax, target-resolution, and reviewed-link audits
as other maintained rules text. The existing rules record payload remains the canonical composed
scenario structure, while rules schema/compatibility **8/10** adds relational scenario publication
indexes. `scenario_collections` owns stable set identity, `scenario_collection_revisions` maps an
exact set revision to its source collection, `scenario_publications` stores deterministic composed
content identity, and `scenario_memberships` preserves ordered membership separately from scenario
identity. Source/citation provenance continues to use the existing collection/source/citation tables.
Rebuild `rules.db` after curation changes using the existing rules-build workflow.

`RulesDatabase.resolve_scenario_publication()` is the central selection boundary. A scenario may be
resolved by stable collection ID plus exact collection revision; omitting a revision considers only
publications backed by `current` source collections. Historical revisions require an explicit
collection/revision pair. Unknown selections return no match, malformed or ambiguous selections fail
explicitly, and no other season/revision is substituted. The player-facing `/scenarios` catalog and
detail pages consume `ScenarioCatalog` through the JSON API, require an explicit Army Points selection,
and render the selected maintained geometry through the deterministic SVG endpoint. Browser selection
state uses the common versioned share-state token; legacy explicit `army_points` input remains readable.
Element/feature vocabulary extensions and source-discrepancy resolution remain unfinished work in the
[1.0 backlog](TODO.md#rules-and-reference-completeness).

The implemented geometry v1 foundation is deliberately small and strict. A standalone document uses
`InfinityDB scenario geometry` format version 1, canonical inch table dimensions, ordered unique
element IDs, and `rectangle`, `line`, `marker`, or `label` elements. Coordinates may be absolute
inches or table-relative edge/center anchors with offsets. Element `style` and marker `markerType`
values are stable kebab-case semantic identities, not a closed list owned by the v1 SVG renderer.
An optional ordered `annotations` layer
references those semantic elements rather than restating their geometry. Geometry v1 currently supports
derived rectangle `dimension` annotations and `area-size` annotations; both calculate their displayed
measurement from the referenced rectangle, so a map cannot silently disagree with maintained zone
dimensions. Rendered measurement text carries the canonical inch value in
`data-distance-inches` or `data-distance-size-inches`, separate from the user-facing display unit.
The map API accepts optional `distance_unit=in|cm`, using the Infinity distance convention
of 1 inch = 2.5 cm. The browser updates inlined annotations when the existing unit preference
changes, without altering the inch viewBox or stored geometry. Marker `data-diameter-mm`
remains unconverted physical metadata.
It also supports `element-edge-distance` annotations for markers and rectangles: the
displayed distance is derived from the target element's nearest physical boundary and selected table edge,
while an optional signed offset controls only where the dimension line is drawn. Scenario source language
such as “X inches from” is interpreted edge-to-edge unless the source explicitly names a center/reference
point. `marker` stores a semantic center point with a stable `markerType`; per-instance radius is not
duplicated in geometry because known marker types resolve to canonical marker metadata. That footprint is
used when deriving marker clearances. Physical diameter is semantic when it defines the represented game object,
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

Domination exercises the rectangle annotation boundary: its Deployment Zones have derived depth
dimensions and its four Quadrants have derived width × height labels. Supplies exercises the point
boundary: the outer Supply Boxes are maintained at their semantic coordinates while the SVG derives
their `8″` distance to the left/right table edges. These annotations are map presentation metadata
referencing semantic geometry, not a second copy of scenario measurements.

The initial core-map acceptance corpus covered Annihilation, Domination, Supplies, and Firefight at
each distinct N5.3 table/deployment configuration (24×32 with 8-inch Deployment Zones, 32×48 with
12-inch Deployment Zones, and 48×48 with 12-inch Deployment Zones). It confirmed that v1 needs only
rectangular regions, dividing lines, semantic point markers, labels, and table-relative anchors for
the core maps. All four scenarios now own those configurations in maintained curated definitions,
and renderer acceptance tests consume that maintained geometry directly instead of keeping a second
fixture-only map corpus.

### Scenario publication model and remaining design direction

Scenarios are curated rules/reference data and will be published through the rules pipeline. Their
maintained representation is validated structured JSON; their runtime representation is a deliberate
hybrid in `rules.db`. High-stability/queryable facts are relational, while nested ordered structures
whose shape legitimately varies by scenario remain validated typed payloads. Runtime code must never
parse PDF prose, image geometry, or display HTML to recover scenario semantics.

The planned semantic model separates these identities and scopes:

- **Scenario identity:** stable InfinityDB slug/name for the conceptual mission. Reuse across seasons
  does not duplicate the identity.
- **Publication/revision:** authoritative source collection, source version/revision, language,
  reviewed citation, publication date when known, and deterministic content identity. A hotfix or
  revised mission document creates a new publication revision, not a new scenario identity.
- **Collection membership:** membership in a source set such as core N5.3 or an ITS season, including
  collection-local category/ordering and applicability. Membership may change between revisions of a
  season.
- **Scenario applicability/configuration:** supported Army Points/SWC, table dimensions, round count,
  minimum-VP/end thresholds, side configuration, and feature flags such as Reinforcements or
  collection-specific options. These values can vary by game-size row without changing identity.

Each published scenario revision then composes typed scenario components:

- **Sides and roles:** symmetric Side A/B by default, with named asymmetric roles and role-assignment
  procedure when required. Objectives/rules may be scoped to a side or role.
- **Geometry:** a table-local coordinate system plus typed points, lines, rectangles/strips, circles
  or radius regions, quadrants/sectors, and derived/side-relative regions. Dimensions, anchors,
  transforms, exclusion areas, and placement constraints remain numeric semantic data rather than
  pixels from a source diagram.
- **Elements and tokens:** objective/scenery element types and instances with placement, ownership or
  alignment, interaction/lifecycle capabilities, and representation metadata. Carrying, destruction,
  activation, control, and state-like markers are modeled only where the scenario definition needs
  them; live ownership/carrier/state during a match is not persisted by the scenario catalog.
- **Objectives and scoring:** ordered objective groups with side/applicability, timing such as
  immediate/end-of-round/end-of-game, Objective Points, caps, and typed condition/comparison forms.
  Game-size-dependent thresholds are data. Unusual resolution procedure may retain reviewed prose in
  addition to typed facts rather than forcing a universal executable scoring language.
- **Classified Objectives and reusable features:** optional configuration for counts, Common/Private
  use, points, exclusions, substitutions/alternate use, and scenario-specific interactions. HVTs,
  Specialists, carried objectives, control areas, selectable objective sets, and season extras follow
  the same optional-feature principle.
- **Scenario actions and rules:** local Skills/AROs/interactions, requirements, effects, roll/MOD
  metadata, timing hooks, and rule overrides where structurally useful. Existing Skills, Equipment,
  States, Traits, Labels, General Rules, and other canonical entities are referenced by typed ID
  rather than copied into scenario-local identities.
- **End conditions:** round/time limits, Retreat-related behavior, all-Null/minimum-VP conditions, and
  explicit scenario overrides. Definition data records the condition; match-state evaluation remains
  outside the 1.0 catalog/reference responsibility.

Publication should materialize relational indexes/foreign keys for identity, provenance, collection
membership, slugs, canonical entity references, and other cross-scenario query needs. The validated
component payload remains the canonical ordered scenario structure consumed by the backend. Browser
code receives composed presentation data and must not reinterpret score conditions, geometry, or
source-specific feature semantics.

The geometry component is also the sole semantic input for scenario-map generation. The 1.0 renderer
and geometry-schema v1 only need to cover the four N5.3 core scenarios: Annihilation, Domination,
Supplies, and Firefight. A renderer may project that geometry to SVG/other presentation formats, but
map-specific coordinates must not become an independent maintained source.

That v1 compatibility boundary must not be mistaken for a core-only architecture. The reviewed ITS
variation remains design evidence: geometry identities and primitives must not assume symmetric
roles, one Deployment Zone per side, rectangular-only regions, fixed marker vocabularies, or one
collection's styling. ITS-only constructs may remain unsupported by schema v1 and should fail
explicitly rather than be approximated; later versioned extensions should add those capabilities
without redefining the core semantic concepts. Likewise, future ITS support extends
publication/collection and optional-feature data rather than creating an ITS-only scenario schema.

### Post-1.0 player-authored scenarios (design direction)

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
stateless-sharing decision in `docs/architecture.md`; this is a post-1.0 goal,
not an extension of the 1.0 publication or database completeness gate.

## SQLite storage contract

Army export first loads normalized source data into validated relational staging, then writes two
permanent siblings:

### `infinity.db`

The self-contained application/runtime database. It contains the source/context rows still needed by
application behavior plus materialized canonical tables, mappings, provenance, and indexes. Source-
only normalized tables are physically absent.

Normal repository/API/web serving opens only this Army database plus `rules.db`.

### `infinity.raw.db`

The development/audit sibling. It contains all normalized source tables as queryable relational
structures plus exact normalized row JSON so absent-vs-null and source-only data remain recoverable.
It is not deployed.

### Shared metadata and integrity

Both Army siblings retain the generated metadata needed to bind them to the source/configuration
that produced them. Important metadata includes source snapshot identity, validated identity-policy
hashes, publication/raw table boundaries, deterministic application-content identity, and the
shared `export_pair_sha256` fingerprint for the complete application/raw export generation. The
pair fingerprint includes source-only normalized rows, so a partially published raw archive cannot
silently masquerade as the companion of an older application database.

When the Army database is built from a ZIP snapshot, `snapshotArchiveSha256` records that exact
archive identity. Deployment compares it with the Army source identity in the tracked symbol
publication manifest so Army data and graphical publication cannot silently come from different
snapshots.

`PRAGMA application_id`, `PRAGMA user_version`, and the InfinityDB compatibility revision are
validated before normal reads. Export validates integrity, writes planner statistics, and performs
canonical physical finalization for deterministic release bytes. Semantic tests may explicitly skip
only the physical finalization step; they do not bypass schema/input/integrity validation.

Builds publish generated database destinations only after temporary artifacts validate. The raw
archive is replaced first and the application database last, making the application replacement the
publication commit point. The exact interruption/recovery lifecycle is owned by `data/README.md`.

## Snapshot provenance

Army, wiki, and symbol acquisition uses generated snapshot provenance records described in
`data/README.md`.

The current provenance model distinguishes:

- logical snapshot content SHA-256 (normalized member paths + member bytes);
- exact archive SHA-256;
- acquisition timestamp;
- source URL/language/document count where applicable; and
- for Army snapshots, the latest source-data date encoded by supported Army source version strings.

`data/README.md` owns the current provenance-format version and compatibility rules.

Acquisition time answers when InfinityDB downloaded the snapshot. `source.dataChangedOn` answers when
the contained Army source data most recently reports changing. Those dates must not be substituted
for each other.

Human snapshot notes are separate curated annotations bound to immutable source identity. Acquisition
tools never rewrite them.

## Army source revision interpretation

Corvus Belli Army document `version` values are source revisions, not InfinityDB snapshot versions.
InfinityDB may derive a latest encoded source date only from version shapes it explicitly recognizes;
unsupported values must remain visible rather than guessed. A snapshot can be acquired long after
its newest source revision, so the provenance model stores both concepts.

The browser's normal freshness wording uses the source-data change date when available. Exact
acquisition/archive identity remains Developer/provenance information.

## Required Army metadata

Army database builds require the supplementary Army `metadata.json`. It is preserved through the
merge/normalized pipeline and exported to metadata tables.

Metadata provides, among other things, faction/grouping relationships and weapon/profile reference
information. Army list files remain authoritative for concrete Unit membership/availability; a
metadata identity does not create an Army roster by itself.

Current build validation rejects normalized Army data without valid required metadata.

## Application query model

Runtime repositories query canonical/materialized application structures and compose contextual
source detail as needed. They must not infer semantics from raw IDs or reach into `infinity.raw.db`.

Examples:

- Unit lists operate on logical Unit identity and materialized Army availability.
- Unit detail returns one logical Unit with source/Army/profile/loadout context preserved.
- catalog filters resolve canonical application identity and match all materialized source members.
- rules-backed States and other rules-only concepts are read from `rules.db`; their presence does
  not imply mutable in-game state in `infinity.db`.
- search and Glossary project canonical domain identities rather than creating another identity
  namespace.

The HTTP/browser layer may change presentation without changing these semantic ownership rules.

## Audit and validation tools

Current semantic contracts are executable through focused audit tools rather than copied as
historical inventories into this document. Important examples include:

- `tools/audit_database_separation.py` — application/raw table boundary;
- `tools/audit_runtime_database_surface.py` — runtime repository access boundary;
- `tools/audit_unit_semantics.py` — logical Unit/source semantics;
- `tools/audit_profile_semantics.py` and `tools/audit_loadout_semantics.py` — profile/loadout payload
  boundaries;
- `tools/audit_army_faction_semantics.py` — Army/grouping/faction semantics;
- `tools/audit_peripheral_semantics.py` — Peripheral mappings/access pools;
- `tools/audit_relationship_semantics.py` — source/application relationship interpretation;
- `tools/audit_fireteam_semantics.py` — Fireteam chart semantics;
- `tools/audit_source_presentation.py` — source-to-player-presentation coverage;
- `tools/audit_semantic_deduplication.py` — canonicalization evidence;
- `tools/audit_enrichment_coverage.py` and `tools/audit_rules_interactions.py` — rules/reference
  coverage and interaction review; and
- `tools/audit_maintained_text_links.py` — maintained-prose semantic-link completeness.

Generated reports and one-off audit measurements belong under ignored report/audit workspaces. Only
durable semantic conclusions belong in this document.
