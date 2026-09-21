# Rules semantics audit

This document is the coverage ledger for InfinityDB's systematic audit of the
Infinity ruleset. The goal is not to reproduce the rules. The goal is to identify
source-authoritative semantics that improve data interpretation, normalization,
validation, relationships, querying, filtering, or presentation.

Infinity's rules use an unusually explicit and structured vocabulary, which
makes them valuable semantic evidence for this work. That structure is an input
property, not an application-model requirement. InfinityDB remains a catalog and
relationship reference: it does not need to mirror the rules ontology, encode
every procedure or edge case, or become an authoritative/infallible substitute
for the official rules. Audit completeness means that relevant rules material
has been examined for useful semantics, not that every rule must be represented
in the database, API, or UI.

Implementation-relevant findings move to `rules-semantics.md`. Verified findings
without a current consumer go to `rules-research.md`. Page-level coverage stays
here so `TODO.md` can remain a milestone-level backlog.

## Source baseline

The initial audit baseline is:

- Core rules: `data/pdf/rules/n5-rules-v5-3-en.pdf`, Infinity N5 V5.3. Use the
  printed page number for citations.
- FAQ: `data/pdf/faq/n5-faqs-v0-1-en.pdf`, N5 FAQ v0.1. FAQ findings remain
  separate from base-rule findings.
- Wiki: <https://infinitythewiki.com/>. Record the canonical page URL and the
  rules/FAQ version shown by the page when reviewed.
- Local wiki snapshot: `data/wiki/WIKI-en 20260918-130233.zip`, pinned by the
  curated rules source catalog as `wiki-en-20260918-130233`. Use its snapshot
  identity for stable local wiki provenance; cross-check the live wiki when a page
  carries a later N5.3/FAQ update or when the snapshot revision is uncertain.
- ITS material remains season-scoped and must not be silently merged into core
  rules semantics.

The live wiki currently reports N5.3 and FAQ v0.1 on current rules pages such as
`Unit_Profile` and `Basic_Rules`. The `Main_Sections` index has carried older
notice metadata, so it is used as navigation topology rather than as the version
authority for every linked page.

## Source and interpretation rules

- Prefer current official rules material when it supersedes an older local copy.
- Use the wiki for traversal, canonical page identity, cross-links, redirects, and
  current clarifications. Use the PDF for stable edition/version and printed-page
  citations.
- Keep core rules, FAQ/errata, Reinforcements, ITS season rules, and historical
  material explicitly scoped.
- Where sources appear to disagree, record the discrepancy and scope instead of
  silently combining them.
- Infinity Army remains authoritative for current unit availability and list
  legality. Rules sources explain semantics; they do not replace Army source data.
- Summarize and structure rules facts. Do not copy large portions of copyrighted
  rules text or artwork into tracked project files.

## Finding workflow

For every audited page or PDF section:

1. Record the page/section and source version.
2. Extract terms, finite value sets, relationships, invariants, notation, and
   scope rules that may affect InfinityDB.
3. Classify each concept as source-native, InfinityDB abstraction, or
   InfinityDB-derived interpretation.
4. Reconcile relevant findings against Army/API data and the current application
   model. Ask whether information is already preserved, flattened, ambiguous, or
   absent.
5. Record consequences for processing, validation, querying/filtering, or
   presentation.
6. Put immediately useful semantics in `rules-semantics.md`; put verified but
   currently unused findings in `rules-research.md`.
7. Do not implement schema/code/UI changes opportunistically during the audit.
   Feed confirmed gaps back into the normal project backlog.

Do not treat a precisely specified rule as a modeling requirement merely because
it is easy to structure. Procedural rules, timing details, and edge cases should
be retained only when they clarify terminology, prevent a likely data
misinterpretation, support a plausible reference/presentation need, or provide
necessary context for another finding. Otherwise the authoritative source link
is sufficient.

A normal finding records:

- a stable local finding ID;
- canonical term(s) and rules scope;
- concise semantic statement;
- wiki URL and reviewed rules/FAQ version;
- PDF document/version and printed page, when applicable;
- related Army/API fields or InfinityDB domains, when known;
- processing, validation, query/filter, and presentation implications;
- unresolved ambiguity or follow-up work.

## Audit order

The wiki Main Sections page is the traversal spine. `Game States and Glossary` is
intentionally audited immediately after Basic Rules because its terminology,
labels, traits, and states provide vocabulary reused by later sections. Quick
Reference Charts are primarily a validation/completeness pass after the prose
rules have been audited.

- [ ] Introduction
- [x] Basic Rules
  - [x] Basic Rules overview: game elements, terminology/alignment, labels/traits,
    armies, game states, and game modes
  - [x] Open and Private Information
  - [x] Unit Profile — initial semantic extraction and N5 V5.3 PDF cross-check
  - [x] Army List
  - [x] Orders and the Order Pool
  - [x] Trooper Activation
  - [x] ARO: Automatic Reaction Order
  - [x] Order Expenditure Sequence
  - [x] Initiative and Deployment
  - [x] Game Sequence
  - [x] Loss of Lieutenant
  - [x] Silhouettes
  - [x] Line of Fire
  - [x] Zone of Control
  - [x] Zones, Bases and Silhouettes
  - [x] Coherency
  - [x] Distances and Measurements
  - [x] Replacing Game Elements
  - [x] Rolls
  - [x] Face to Face Rolls
- [x] Game States and Glossary
  - [x] States overview and complete 23-State inventory
  - [x] Camouflaged State
  - [x] Dead State
  - [x] Decoy State
  - [x] Disconnected State
  - [x] Engaged State
  - [x] Foxhole State
  - [x] Hidden Deployment State
  - [x] Holoecho State
  - [x] HoloMask State
  - [x] Immobilized-A State
  - [x] Immobilized-B State
  - [x] Impersonation State
  - [x] Isolated State
  - [x] Normal State
  - [x] Possessed State
  - [x] Prone State
  - [x] Retreat! State
  - [x] Sepsitorized State
  - [x] Stunned State
  - [x] Suppressive Fire State
  - [x] Targeted State
  - [x] Unconscious State
  - [x] Unloaded State
  - [x] Terminology
  - [x] Alignment
  - [x] Labels
  - [x] Traits
- [x] Skills and Equipment
  - [x] Module framework: MODs, Levels, Labels, Traits, NFB, and Skill categories
  - [x] Common Skills: complete 18-skill core inventory and category semantics
  - [x] Special Skills: complete 76-skill N5 V5.3 core inventory and
    relationship/parameter/profile-impact semantics
  - [x] Equipment: complete 26-item N5 V5.3 core inventory and
    action/variant/profile semantics
  - [x] Live-wiki scope reconciliation, including Reinforcements annex links
  - [x] Curated rules/application-model reconciliation
- [x] Combat
  - [x] Combat overview: weapon types, Burst, MODs, Attack Rolls, PS/SR, Wounds,
    Unconsciousness/Death, and Guts
  - [x] Ballistic Skills, BS Attack, Cover/Range, and ranged weapon profiles
  - [x] Template Weapons and Equipment, Direct/Impact Templates, Intuitive Attack,
    and Speculative Attack
  - [x] Close Combat, CC Attack, multiple-Trooper interactions, and melee profiles
  - [x] Quantronic Combat: Hacker, Firewall, Hacking Area, Repeaters, Devices,
    program chart, and the 12 core Hacking Programs
  - [x] Curated/application-model reconciliation
- [x] Ammunition and Weaponry
  - [x] Ammunition framework and complete 11-type base Ammunition inventory
  - [x] Combined Ammunition and Combined Saving Roll semantics
  - [x] Weaponry and Mixed Weapons
  - [x] Deployable/special weapon rules: Perimeter Weapons, Armed Turret,
    Chest Mines, D-Charges, Disco Baller, Drop Bears, Mine Dispenser, Mines,
    Pitcher, Sepsitor, SymbioBomb, and WildParrot
  - [x] Army metadata/curated/application-model reconciliation
- [x] Fireteams
  - [x] Fireteams Module overview and Basic Rules
  - [x] Fireteams Chart
  - [x] Fireteam Integrity
  - [x] Fireteams in the Active Turn
  - [x] Fireteams in the Reactive Turn
  - [x] Fireteam Bonuses / Fireteam Level
  - [x] Fireteam Examples
  - [x] Army Fireteam-chart representation reconciliation
  - [x] Historical/community terminology: `Linkable` and `pure Fireteam`
- [x] Command
  - [x] Command Module overview and Command Token resource/use-mode semantics
  - [x] Coordinated Orders
  - [x] Cross-section interactions: Lieutenant, Counterintelligence, and NCO
  - [x] Application/session-boundary reconciliation
- [x] Movement
  - [x] Movement Module overview and MOV pair semantics
  - [x] Moving and Measuring
  - [x] Move
  - [x] General Movement Rules
  - [x] Cautious Movement
  - [x] Climb
  - [x] Jump
  - [x] Cross-section reconciliation: Movement Label, Prone, Super-Jump,
    Climbing Plus, source distance units, and application presentation
- [x] Terrain and Scenery Structures
  - [x] Special Terrain scope, area of effect, and characteristic composition
  - [x] Types of Terrain
  - [x] Difficult Terrain
  - [x] Saturation
  - [x] Visibility Conditions
  - [x] Scenery Structures / Access Width
  - [x] Cross-section reconciliation: Terrain Special Skill, Movement, Smoke/
    Eclipse, White Noise, Dazer, Silhouette, and application boundaries
- [x] Triumph and Defeat
  - [x] Standard Game and Victory Points
  - [x] Retreat! situation and its relationship to Retreat! State
  - [x] Mission or Scenario / Objective Points
  - [x] Free Game
  - [x] Cross-section reconciliation: Cost, Null States, Retreat! State,
    Game Modes, scenarios, and application/session boundaries
- [x] Setting up the Gaming Table
  - [x] Advisory scope and relationship to Game Modes/scenarios
  - [x] Terrain and Cover / recommended table-size guidance
  - [x] Terrain Layout and Accessibility
  - [x] Symmetrical and Asymmetrical Deployment Zones
  - [x] Cross-section reconciliation: Game Modes, Deployment Zones, Terrain/
    Scenery, Cover, scenarios, and application boundaries
- [x] Scenarios
  - [x] Section scope and relationship to the wider scenario corpus
  - [x] Annihilation
  - [x] Domination: quadrants, Consoles, Hack Consoles, and Specialist Troops
  - [x] Supplies: Supply Boxes, Pick Up Supply Boxes, and Specialist Troops
  - [x] Firefight: Killing, Reinforced Tactical Link, Designated Landing Area,
    and Specialist Troops
  - [x] Cross-section reconciliation: scenario-only catalog concepts, contextual
    roles/elements, scoped rule overlays, and the 1.0 scenario-library boundary
- [x] Quick Reference Charts
  - [x] Weapon and Alternative Weapon Charts; Ammunition summary
  - [x] Game sequence, Order expenditure, and Orders/AROs reference
  - [x] Impetuous activation; Martial Arts, Booty, and MetaChemistry charts
  - [x] Hacking Programs and Hacking Device/Program matrix
  - [x] Restrictions, Retreat!/Loss of Lieutenant, and Fireteam bonus summaries
  - [x] Deployable Profiles and cross-section completeness reconciliation
  - [x] Data-generated chart/table opportunities and source-conflict review
- [ ] Reinforcements
- [ ] ITS FAQ
- [ ] Final cross-section reconciliation and gap analysis

## Completed page notes

### Basic Rules — section complete

Status: core N5.3 wiki/PDF semantic extraction complete for the Basic Rules
section. Embedded FAQ material was observed but not promoted into core findings;
FAQ/errata semantics remain separately scoped under the source rules above.

Primary sources reviewed:

- Wiki: <https://infinitythewiki.com/Basic_Rules> and every Basic Rules page in
  its navigation sequence, reviewed against the live N5.3 / FAQ v0.1 wiki.
- PDF: Infinity N5 V5.3, printed pages 6-26.

The section produced implementation-relevant findings in
`rules-semantics.md` and future-facing findings in `rules-research.md`. The
reconciliation pass also confirmed several existing InfinityDB boundaries and
one presentation mismatch that should be handled later rather than fixed during
this documentation audit.

#### Basic Rules overview, information, and Army Lists

Sources reviewed:

- <https://infinitythewiki.com/Basic_Rules>
- <https://infinitythewiki.com/Open_and_Private_Information>
- <https://infinitythewiki.com/Unit_Profile>
- <https://infinitythewiki.com/Army_List>
- PDF: Infinity N5 V5.3, printed pages 6-11.

Promoted semantics cover the distinction between Labels and Traits, transient
Game States, Army-List disclosure/privacy context, army-specific list membership
and AVA, Cost/SWC context, and the Unit Profile findings already recorded by the
initial pass.

The rules reinforce the current application-model boundary: a Unit can occur in
multiple Army Lists with different list membership and AVA, while the logical
Unit remains a cross-Army InfinityDB identity. Points and SWC also belong to the
selectable option/occurrence context rather than the reusable loadout payload.

#### Orders, activation, AROs, and game sequence

Sources reviewed:

- <https://infinitythewiki.com/Orders_and_the_Order_Pool>
- <https://infinitythewiki.com/Trooper_Activation>
- <https://infinitythewiki.com/ARO>
- <https://infinitythewiki.com/Order_Expenditure_Sequence>
- <https://infinitythewiki.com/Initiative_and_Deployment>
- <https://infinitythewiki.com/Game_Sequence>
- <https://infinitythewiki.com/Loss_of_Lieutenant>
- PDF: Infinity N5 V5.3, printed pages 11-18.

Promoted semantics separate Training from the Orders a loadout generates,
distinguish static order-generation data from the runtime Order Pool, confirm
the Basic Short/Short/Long Skill declaration categories used by the curated
rules layer, and prevent dynamic Loss of Lieutenant effects from being mistaken
for permanent profile characteristics.

A concrete presentation mismatch was found during reconciliation:
`src/infinity_db/web/static/unit.js` currently labels the `tactical` order symbol
as `Tactical Awareness`. The rules define the symbol/profile fact as a
**Tactical Order**; **Tactical Awareness** is the Special Skill that grants an
additional Tactical Order. Keep the source order type and the granting Skill as
separate concepts. This audit records the gap but deliberately does not change
runtime code.

#### Spatial concepts and measurement

Sources reviewed:

- <https://infinitythewiki.com/Silhouette>
- <https://infinitythewiki.com/Line_of_Fire>
- <https://infinitythewiki.com/Zone_of_Control>
- <https://infinitythewiki.com/Zones,_Bases_and_Silhouettes>
- <https://infinitythewiki.com/Coherency>
- <https://infinitythewiki.com/Distances_and_Measurements>
- <https://infinitythewiki.com/Replacing_Game_Elements>
- PDF: Infinity N5 V5.3, printed pages 18-22.

Promoted semantics establish that the `S` value identifies a Silhouette Template
with defined geometry, that rules-table distances are expressed in inches, and
that Coherency is a relationship mechanic centered on a context-defined
Reference Trooper. Detailed LoF/ZoC/zone/replacement geometry remains research
material until InfinityDB has a consumer for tabletop spatial rules.

The measurement audit supports the existing separation between source units and
presentation units. Infinity Army range data may be stored in source-native
metric values while the rules describe tabletop measurements in inches; any
conversion must therefore retain explicit source/unit context rather than
reinterpreting a bare number.

#### Rolls and profile modifiers

Sources reviewed:

- <https://infinitythewiki.com/Rolls>
- <https://infinitythewiki.com/Face_to_Face_Rolls>
- PDF: Infinity N5 V5.3, printed pages 23-26.

Promoted semantics establish that parenthetical values beside a Skill, Weapon,
or Equipment item are scoped to use of that item and that notations such as a
plain MOD, `Attribute=value`, `PS=value`, Burst changes, ReRoll, Special Dice,
Ammunition, Traits, and Saving-Roll changes have different meanings. They must
not be normalized into one generic signed-modifier field. This directly supports
the existing curated parameter-semantics approach and the Skill Modifiers UI.

Normal/Face-to-Face resolution, Success Value limits, Criticals, and related
procedural roll rules are recorded in `rules-research.md` for future rules/help
features rather than modeled as static Army facts.

### Game States and Glossary — section complete

Status: core N5.3 wiki/PDF semantic extraction complete for the Game States and
Glossary module. The audit covers the state framework, all 23 listed States,
Terminology, Alignment, the complete Label vocabulary, and the complete Trait
vocabulary. Embedded FAQ material remains separately scoped and is not promoted
into core findings here.

Primary sources reviewed:

- Wiki: <https://infinitythewiki.com/Game_States_and_Glossary>,
  <https://infinitythewiki.com/States>, every State page linked by the States
  index, <https://infinitythewiki.com/Terminology>,
  <https://infinitythewiki.com/Alignment>,
  <https://infinitythewiki.com/Labels>, and
  <https://infinitythewiki.com/Traits>. The substantive pages reviewed report
  N5.3 / FAQ v0.1; the Main Section landing page can retain older notice metadata
  and is treated as navigation rather than version authority.
- PDF: Infinity N5 V5.3, printed pages 157-175. The printed index confirms the
  complete State sequence on pages 157-172, Terminology and Alignment on page
  173, and Labels/Traits from page 174.
- Curated-data reconciliation: `data/curated/rules/n5-core-v5.3.json`.

#### State framework and complete inventory

The rules define a State as a runtime condition of a Trooper or other game
element. States are cumulative, have explicit activation/cancellation rules, can
modify Attributes cumulatively, and are represented by State Tokens. The State
Token is a reminder/representation of the rule effect; it is not the State itself
and is not interchangeable with a Model, Marker, or deployable Token.

All 23 current N5.3 States were reviewed:

- Camouflaged (p.157): Marker representation, hidden identity, and restrictions
  around Discover, attacks, and Fireteam membership.
- Dead (p.159): Null State; removes the game element from normal play and from
  Order/Victory-Point contribution.
- Decoy (p.159): multiple representations with secret real/decoy identity.
- Disconnected (p.160): Null State used especially by Peripheral/controller
  relationships; disables ordinary activation while the disconnection persists.
- Engaged (p.160): relational/spatial State created by Silhouette contact with an
  Enemy and constraining legal actions/LoF.
- Foxhole (p.161): runtime overlay that changes effective Silhouette/movement and
  grants rule effects without changing the source Unit Profile.
- Hidden Deployment (p.161): off-table/private representation with special Order
  handling; absence of a Model/Marker is itself meaningful game state.
- Holoecho (p.162): multiple synchronized representations where apparent game
  elements are not independent canonical Troopers.
- HoloMask (p.164): visible identity/profile presentation may differ from the
  Trooper's real Unit Profile; disguise must not be mistaken for canonical
  identity.
- Immobilized-A (p.164): declaration restrictions centered on Dodge/PH and a -6
  MOD; still contributes Orders.
- Immobilized-B (p.165): distinct State centered on Reset/WIP and a -3 MOD; still
  contributes Orders. It must not be collapsed into Immobilized-A.
- Impersonation (p.166): Marker State with distinct IMP-1/IMP-2 levels and
  different discovery/interaction semantics.
- Isolated (p.168): runtime Order/Training, Comms/Hacking, Lieutenant, Peripheral,
  Fireteam, and Coordinated-Order effects. Temporary Irregular treatment is not a
  rewrite of source Training.
- Normal (p.168): default/non-Null runtime State, not a static catalog
  characteristic that needs to be stored on every profile.
- Possessed (p.169): Null State that changes effective alignment/control and uses
  a Possessed Trooper profile overlay while preserving the underlying Trooper.
- Prone (p.169): runtime Silhouette/movement overlay with Troop-Type restrictions.
- Retreat! (p.170): army/game-session condition propagated to affected Troopers;
  not a static profile fact.
- Sepsitorized (p.170): Null State with control/alignment and Order consequences.
- Stunned (p.170): temporary action/roll restrictions with VITA/STR-dependent
  recovery routes.
- Suppressive Fire (p.171): selected-weapon profile overlay; the normal weapon
  identity/profile is not replaced in canonical data.
- Targeted (p.171): transient modifiers/restrictions applied to interactions with
  the affected game element.
- Unconscious (p.172): Null State tied to VITA/STR Wound thresholds; removes Order
  and Victory-Point contribution while retaining Combat Group membership.
- Unloaded (p.172): state of relevant depleted Disposable weapon/Equipment usage;
  its effect is item-specific even though the State is tracked on the bearer/game
  element.

The current curated rules file contains one first-class `state` record,
`state:camouflaged`, so state identity coverage is **1/23**. This is a confirmed
rules-reference coverage gap, not an Army-import defect. The existing TODO item
for a Game States reference catalog already owns the implementation work; no
parallel backlog item is added here.

#### Terminology and Alignment

Terminology on printed page 173 defines Attributes, Deployable Equipment,
Deployable Weapon, Marker, Model, Peripheral, Scenery Element, State Token,
Target, Token, Trooper, Unit Profile, and Victory Points. These definitions give
InfinityDB a source-native object vocabulary that spans existing catalog domains
without requiring every term to become a database entity.

The representation terms are intentionally distinct: a **Model** is represented
by a miniature, a **Marker** is a game element with Attributes represented by a
Marker under a rule, a **Token** represents Deployable Equipment/Weapons, and a
**State Token** is a reminder of a rule/Skill/State effect. UI/help text and any
future thesaurus should preserve those distinctions.

Alignment defines Ally, Enemy, Hostile, and Neutral. Hostile and Neutral are not
synonyms: Hostile game elements are explicitly treated as Enemy by all players
and can declare/receive Attacks, while Neutral identifies elements belonging to
neither player's Army List without that additional Enemy rule. Alignment is
runtime/list context, not canonical faction ownership.

#### Labels and Traits

The live N5.3 Labels page and V5.3 glossary define 23 rules Labels. All 23 names
are already represented in the curated rules `labels` vocabulary. The curated
file contains one additional entry, `FAQs`; that entry is InfinityDB/wiki-support
metadata and must not be presented as a 24th source-native Infinity Label.

The live N5.3 Traits page defines 33 Traits, and the curated rules file contains
33 corresponding `kind: "trait"` records. Identity/name coverage is therefore
complete for the current Trait vocabulary. This does not imply every downstream
cross-link or structured effect is complete; later weapon/equipment audits must
still validate how each Trait is attached to Army/catalog data.

Several Traits encode typed semantics rather than being mere display tags:
`BS Weapon (PH/WIP)` substitutes the Attribute used by BS rules; `Deployable`
creates an independent battlefield element; `Disposable (X)` carries a use count
shared across modes; `Non-Lethal` takes precedence over added ammunition;
`State` points to a specific Game State; `Suppressive Fire (SF)` selects an SF
profile overlay; and `Target (Attribute)` restricts effect by VITA/STR. The
existing curated Trait identities and parameter-prefix facts are therefore the
correct semantic layer to extend rather than re-parsing these meanings in UI
code.

#### Thesaurus and model reconciliation

This section confirms that a future game-terms thesaurus cannot safely use a bare
term string as global identity. Source terminology intentionally reuses words in
multiple semantic roles: `Hackable` is a Trooper Characteristic and a Label;
`Hostile` is an Alignment term and a Label; `Marker` is a game-element term and a
Label; and `Null` is a Label used to classify a subset of States. A thesaurus
entry therefore needs concept kind/scope plus explicit relationships between
same-name concepts.

No schema/runtime changes are made by this audit. The confirmed implementation
gaps are already represented by the existing TODO work for broader curated rules
coverage, a glossary/profile-notation help layer, and a Game States reference
catalog.

### Skills and Equipment — section complete

Status: core N5 V5.3 semantic extraction complete for the Skills and Equipment
module. The core PDF section (printed pages 75-127) was used to establish scope
and the complete Common Skill, Special Skill, and Equipment inventories. The live
N5.3 wiki indexes and selected individual pages were then used to check current
classification, relationships, profile notation, and cross-module links.

The live Special Skills navigation currently also lists `Commlink` and `Request
Reinforcements`. Both resolve to the Reinforcements annex rather than the core
N5 V5.3 Skills and Equipment chapter. They are recorded as scoped research and
do **not** increase the core Special Skill inventory from 76 to 78. Wiki
navigation membership is therefore not sufficient evidence for rules scope.

Primary sources reviewed:

- Wiki: <https://infinitythewiki.com/Skills_and_Equipment_Module>
- Wiki indexes: Common Skills, Special Skills, and Equipment under that module
- PDF: Infinity N5 V5.3, printed pages 75-127
- Targeted validation: Infinity N5 V5.3, printed page 191, Orders and AROs
  Reference Chart. This targeted cross-check does not complete the later Quick
  Reference Charts audit.

#### Module framework and MOD semantics

Printed pages 75-76 and the current module overview define three independent
classification axes that InfinityDB must keep separate:

1. whether an action/rule is a Common Skill, Special Skill, or piece of Equipment;
2. declaration/timing categories such as Automatic, Deployment, Basic Short,
   Short, Long, and ARO;
3. Labels, Traits, Levels, Requirements, Effects, Restrictions, and
   parenthetical profile parameters.

A single rule may participate in several of these axes. For example, Sapper is a
Special Skill that is both a Deployment Skill and a Long Skill, while GizmoKit
and MediKit are pieces of Equipment whose use is a Short Skill. Declaration
category is therefore not equivalent to catalog/domain identity.

The MOD review extends the Basic Rules profile-notation finding. Parenthetical
values can modify the user, an opponent, an Attribute, a weapon value, Burst,
Saving Rolls, ammunition/Traits, or dice behavior. Positive/negative signs and
the target of the modifier have rule-defined meaning; `+1SD` is not a Burst
increase. These meanings must remain typed rather than being normalized to a
single signed number.

Levels are likewise distinct from arbitrary parenthetical parameters. When a
Skill or Equipment item has Levels, only the listed Level is available and Levels
are not cumulative; `Total` lets the player choose among Levels for each
Order/ARO. This is not the same concept as `Mimetism (-3)`, `Immunity (POS)`, or
a parameterized modifier.

NFB is a compatibility rule, not merely a display label: using one NFB rule can
exclude use of another NFB Skill, Equipment item, Hacking Program, or related
effect. This reinforces the earlier finding that Labels are structured semantic
selectors.

#### Common Skills inventory

The core N5 V5.3 chapter defines 18 Common Skills:

`Alert!`, `BS Attack`, `Cautious Movement`, `CC Attack`, `Climb`, `Discover`,
`Dodge`, `Idle`, `Intuitive Attack`, `Jump`, `Move`, `Look Out!`,
`Place Deployable`, `Reload`, `Request Speedball`, `Reset`,
`Speculative Attack`, and `Suppressive Fire`.

Common Skills are available by rule rather than because they are listed in a
Trooper's Unit Profile. Their absence from Army skill metadata is therefore not a
missing-source-data defect. Where InfinityDB needs them for reference,
declaration help, Traits, or relationship targets, they belong in the rules
reference layer.

The current declaration categories were checked against both the prose rules and
the page-191 Orders/AROs chart. The later completed Quick Reference Charts pass
confirms that this chart is best treated as a generated cross-domain projection
and a validation target for the declaration-category relationships.

#### Special Skills inventory

The core PDF chapter defines 76 Special Skills:

`Aerial`, `Berserk`, `Booty`, `Camouflage`, `Chain of Command`,
`Climbing Plus`, `Combat Instinct`, `Combat Jump`, `Courage`,
`Counterintelligence`, `Cyberplug`, `Decoy`, `Doctor`, `Dogged`, `Engineer`,
`Explode`, `Exrah`, `Forward Deployment`, `Forward Observer`, `Frenzy`,
`FT Master`, `G: Jumper`, `Guard`, `Hacker`, `Hidden Deployment`, `Immunity`,
`Impersonation`, `Impetuous`, `Infiltration`, `Infinity Spec-Ops`,
`Inspiring Leadership`, `Journalist`, `Lieutenant`, `Limited Cover`,
`Marksmanship`, `Martial Arts`, `MetaChemistry`, `Mimetism`, `Minelayer`,
`Mnemonica`, `Morpho-Scan`, `Natural Born Warrior`, `NCO`, `Neurocinetics`,
`No Cover`, `No Wound Incapacitation`, `Non-Hackable`, `Number 2`,
`Parachutist`, `Paramedic`, `Peripheral`, `Protheion`, `Regeneration`,
`Religious Troop`, `Remdriver`, `Remote Presence`, `Sapper`, `Sensor`,
`Shasvastii`, `Sixth Sense`, `Specialist Operative`, `Strategic Deployment`,
`Stealth`, `Strategos`, `Super-Jump`, `Surprise Attack`,
`Tactical Awareness`, `TAGCom`, `Tech-Recovery`, `Technorganic`, `Terrain`,
`Total Reaction`, `Transmutation`, `Triangulated Fire`, `Vulnerability`, and
`Warhorse`.

The audit does not attempt to reproduce all 76 rule texts. It instead records
the semantics that alter how InfinityDB should classify or relate source data.
Notable recurring structures are:

- levels/variants (`Martial Arts`, `Strategos`);
- parenthetical parameters that are not Levels (`Mimetism`, `Immunity`,
  `Forward Deployment`, `Vulnerability`, and others);
- relationships to other entities (`Cyberplug` to Peripheral (Cyberplug),
  `Hacker` to Hacking Devices/Programs, recovery Skills to States);
- alternate/profile-transition behavior (`Transmutation`, `Infinity Spec-Ops`);
- list/relationship/runtime effects (`FT Master`, `TAGCom`, `Strategic
  Deployment`, `Frenzy`, `G: Jumper`);
- dynamic or random profile overlays (`Booty`, `MetaChemistry`, `Morpho-Scan`);
- cross-domain exceptions (`Technorganic` changes normal VITA/STR recovery
  applicability).

These patterns belong in structured rules/reference relationships where a
consumer needs them. They should not be inferred from display names.

#### Equipment inventory

The N5 V5.3 chapter defines 26 Equipment entries:

`360° Visor`, `AI Motorcycle`, `Albedo`, `Baggage`, `Bangbomb`,
`Biometric Visor`, `Cube / Cube 2.0`, `Dazer`, `Deactivator`,
`Deployable Cover`, `Deployable Repeater`, `ECM`, `FastPanda`, `Firewall`,
`GizmoKit`, `Hacking Device`, `HoloMask`, `Holoprojector`, `MediKit`,
`Motorcycle`, `Multispectral Visor`, `Nanoscreen`, `Repeater`, `SymbioMate`,
`TinBot`, and `X-Visor`.

The rules ontology does not always match the source/asset presentation
classification. Most notably, Cube/Cube 2.0 are defined here as Automatic
Equipment even though Army/profile presentation and the symbol pipeline expose
Cube as a characteristic-style symbol. InfinityDB should preserve both facts:
source/presentation categorization does not redefine the rules-domain concept.

Equipment can also expose actions. GizmoKit and MediKit are Equipment but their
use is a **Short Skill**; Deactivator similarly appears as a Short Skill in the
current Orders/AROs chart. This exposes a current limitation in the curated
declaration-category data model, whose records and query path are restricted to
`armyLinks.entity == "skill"`.

Other Equipment entries demonstrate variant and relationship semantics:
Hacking Device types grant different Hacking Programs; TinBot suffixes grant
different benefits; AI Motorcycle changes between mounted and dismounted
profiles and can produce a Peripheral (Synchronized) representation; Firewall
carries a parameterized interaction rather than being a generic scalar
modifier.

#### Curated-data reconciliation

The six tracked `skillTypes` in
`data/curated/rules/n5-core-v5.3.json` correctly correspond to the current
Automatic, Deployment, Basic Short, Short, Long, and ARO rule categories.
However, the existing `skill-declaration-category` records predate the current
N5 V5.3 audit and cannot currently be treated as authoritative.

Confirmed examples include:

- `BS Attack`, `CC Attack`, `Dodge`, and `Forward Observer` are current Short
  Skill / ARO rules, not Basic Short Skill / ARO;
- `Doctor` and `Engineer` are Short Skills, not Basic Short Skill / ARO;
- `Cyberplug` and `Paramedic` are Automatic Skills, not Basic Short Skill / ARO;
- `Parachutist` is a Long Skill, not merely a Deployment Skill;
- `Triangulated Fire` is a Long Skill, not Basic Short Skill / ARO;
- `Berserk` uses the current Long Skill category; the tracked `Entire Order`
  category is not one of the six current `skillTypes`;
- the rules classify `Regular`/`Irregular` as Training. Army-derived data also
  exposes `Regular` through a skill-like source structure for its own
  compatibility/representation needs; InfinityDB must preserve that source fact
  without adopting the source container as the rules-domain classification;
- GizmoKit and MediKit are Equipment actions but are currently linked through
  the declaration-category contract as if they were Skills.

Several printed-page citations in those records are also stale. The problem is
therefore broader than renaming one category: both the curated facts and the
current Skill-only link/query contract need reconciliation against N5 V5.3.

This audit does not alter curated data or runtime code. A focused TODO item now
tracks that correction before declaration-category coverage is expanded.

#### Canonical identity and exact variants

The existing application catalog groups Martial Arts L1-L5, Strategos L1-L2, and
several TinBot source variants under canonical application identities. The rules
audit does not invalidate that identity design, provided source-specific
Level/variant information remains preserved and presentable.

A canonical family answers “which rule/equipment concept is this?”; a specific
Level, parameter, or source variant answers “which rules apply to this
occurrence?” Those are separate questions. A consumer must not infer the exact
rule effects from the family identity alone.

#### Cross-section follow-up

The detailed Hacking Device/Firewall/Repeater topology identified here has now
been reconciled by the completed Combat audit, and the Weapon/Ammunition
semantics have been cross-checked by the completed Ammunition and Weaponry audit.
Those later sections own the resulting findings rather than duplicating them
here.

`Commlink` and `Request Reinforcements` are visible in the live Special Skills
navigation but are Reinforcements annex rules, not core Skills and Equipment
entries in the N5 V5.3 PDF. Their detailed semantics remain deferred to the
Reinforcements audit.

### Combat — section complete

Status: core N5.3 wiki/PDF semantic extraction complete for the Combat Module.
FAQ callouts embedded on live wiki pages were observed but remain FAQ-scoped and
were not promoted into core findings.

Primary sources reviewed:

- Wiki: <https://infinitythewiki.com/Combat_Module> and the linked Combat pages,
  including the Quantronic Combat subtree, reviewed against the live N5.3 wiki.
- PDF: Infinity N5 V5.3, printed pages 36-62. The PDF index confirms that the
  Ammunition and Weaponry module begins on printed page 63; those
  ammunition-specific effects are covered by the completed section below.

The section produced implementation-relevant findings in `rules-semantics.md`
plus future-facing rules/reference material in `rules-research.md`. It also
confirmed one concrete presentation mismatch and one substantial missing rules
domain: the current web weapon profile presents the source `damage` field as
`DAM`, while N5 V5.3 calls the concept **Possibility of Survival (PS)**; and the
curated rules collection has no first-class Hacking Program catalog despite the
Combat rules defining twelve programs and explicit Device-to-Program mappings.
Both are tracked in `TODO.md`; runtime/curated data is unchanged by this audit.

#### Combat framework, PS, Saving Rolls, and Wounds

Printed pages 36-38 define BS, CC, and Hacking as the three combat/Attack
families. The item used to perform an Attack is a separate axis: Weapons, Skills,
and Equipment can all supply attack actions. This reinforces the Skills and
Equipment finding that catalog kind and action/declaration semantics must not be
collapsed.

Burst is action/profile context rather than an invariant count of attacks. The
Active Player normally uses the full current B value and declares its allocation;
Reactive-Turn B is normally 1 unless another rule changes it. Burst MODs and
Special Dice remain separate concepts, and the general B cap is 6.

Possibility of Survival (PS) is the rules-native lethality value. Counterintuitively
for consumers accustomed to a `damage` field, **lower PS is more lethal** because
it lowers the target's Saving-Roll Success Value. The normalized Army metadata
continues to preserve the upstream `damage` field name for provenance, but the
current browser's `DAM` heading is not N5.3 terminology. Presentation should map
the stored source field to PS without renaming or rewriting raw provenance.

Saving Rolls are also structurally richer than a single defense stat. A profile
can select ARM, BTS, another Attribute, a combination, an Attribute modifier, or
a fixed/substituted value; the number of Saving Rolls is a separate field. Some
Attacks have no PS at all and instead call for a direct Attribute Roll with a MOD.
The current metadata representation therefore correctly needs to preserve exact
`ammunition`, `saving`, `savingNum`, PS/source-`damage`, and Trait values rather
than deriving one generic damage formula.

Wounds and Unconscious/Dead transitions are runtime consequences. VITA/STR is
canonical profile data; accumulated Wounds and resulting States are not.

#### Ballistic Skills and ranged profiles

Sources reviewed include Ballistic Skills, BS Attack, Ranged Weapon Profile,
Template Weapons and Equipment, Direct Template Weapons, Impact Template
Weapons, Intuitive Attack, and Speculative Attack (printed pages 39-50).

A ranged profile has distinct semantic columns: range-band MODs, PS, Burst,
Ammunition, Saving Roll Attribute, number of Saving Rolls, and Traits. Modes of a
weapon may differ across any of these values. InfinityDB's existing decision to
retain detailed metadata modes/profiles as contextual data rather than flattening
them into the canonical Weapon identity is therefore rules-correct.

Range is not limited to the Weapon catalog. Any BS Weapon, Skill, or Equipment
capable of making a BS Attack can define Range MODs, and being beyond the maximum
range makes the Attack fail rather than merely applying another numeric MOD. This
matters for equipment such as MediKit and for future rules-reference composition.

Template semantics likewise cross catalog kinds. Direct Templates do not make a
BS Roll to hit, while Impact Templates do; both use template geometry and can be
provided by Weapons or Equipment. `Direct Template`/`Impact Template` should
therefore remain Traits that describe use semantics, not catalog-kind selectors.
Detailed template placement and secondary-target geometry remain research-only
until InfinityDB has a spatial/play-aid consumer.

#### Close Combat and melee profiles

Sources reviewed include Close Combat, CC Attack, and Melee Weapon Profile
(printed pages 51-53).

CC Attack, like BS Attack, can be supplied by a Weapon, Skill, or Equipment item.
Melee profiles use the same PS/Burst/Ammunition/Saving-Roll/Trait vocabulary as
ranged profiles but usually lack Range bands. The exact melee profile is therefore
a contextual rules profile, not a property that should be inferred from the
weapon's display name alone.

Multiple-Trooper Close Combat adds runtime Burst based on currently participating
allies/Peripherals and their States. That bonus describes the current engagement,
not a static weapon/profile Burst value, so it is retained in research rather than
materialized into source data.

#### Quantronic Combat (Hacking)

Sources reviewed include Quantronic Combat, Hacker, Firewall, Hacking Area,
Repeater, Deployable Repeater, Hacking Programs Chart, Hacking Device, and all
twelve core programs on printed pages 54-62:

`Assisted Fire`, `Carbonite`, `Controlled Jump`, `Cybermask`,
`Enhanced Reaction`, `Fairy Dust`, `Oblivion`, `Spotlight`, `Total Control`,
`Trinity`, `White Noise`, and `Zero Pain`.

The Combat rules resolve the relationship graph deferred from the Skills and
Equipment audit:

- `Hacker` is a Skill/role that permits Hacking Device/program use;
- each Hacking Device variant grants an explicit finite Program set;
- a Hacker may also receive Upgrade Programs independently of the Device;
- Hacking Area is a runtime area derived from the Hacker's ZoC plus allied
  Repeater/Deployable-Repeater ZoCs and special enemy-Repeater interactions;
- Firewall is a defensive relationship with a parameterized attack MOD and a
  normally fixed +3 Saving-Roll MOD, with only one Firewall applied at a time;
- Program profiles have their own typed schema: Attack MOD, Opponent MOD, PS,
  Burst, Target, Skill Type, and Special effects.

This is not safely reconstructible from Equipment names alone. Hacking Devices,
Programs, Upgrade Programs, Repeaters, Firewall, target predicates, States, and
Supportware duration are distinct concepts connected by rules-derived edges.
The existing rules-reference expansion backlog now explicitly includes Hacking
Program identities and Device/Upgrade relationships.

Supportware and Hacking Area also demonstrate why not every useful rule edge
belongs in the canonical imported snapshot. Both depend on current game state,
positions, active programs, and relationships. InfinityDB can document their
semantics without pretending to know a static Trooper's live Hacking Area or
Supportware state.

#### Curated/application reconciliation

The current curated rules collection already contains the relevant Labels and
Traits used by Combat, including Attack, BS Attack, CC Attack, Comms Attack,
Hackable, Supportware, Burst, Direct Template, Impact Template, and related
weapon Traits. It does **not** contain first-class Hacking Program records; only
the special Armed Turret weapon currently exists as a curated `kind: weapon`
record. This is a rules-reference coverage gap, not an Army-import defect.

The Army application database already preserves detailed Weapon metadata fields
(`ammunition`, `burst`, source `damage`, `saving`, `savingNum`, `properties`,
`distance`, `mode`, and profile data) and keeps those profile/mode facts contextual
to the source Weapon. That storage boundary is compatible with the Combat rules.
The main confirmed current presentation issue is terminology: the browser renders
source `damage` as `DAM` rather than N5.3 `PS`.

Detailed Ammunition interactions, combined Ammunition, Mixed Weapons, and named
weapon special rules are covered by the completed **Ammunition and Weaponry**
audit below.

### Ammunition and Weaponry — section complete

Status: core N5.3 wiki/PDF semantic extraction complete for Ammunition and
Weaponry. FAQ callouts embedded on live wiki pages were observed but remain
FAQ-scoped and were not promoted into core findings.

Primary sources reviewed:

- Wiki: the Ammunition and Weaponry navigation set, including all eleven base
  Ammunition pages, Combined Ammunition, Combined Saving Roll, Mixed Weapons,
  and the named special/deployable weapon pages.
- PDF: Infinity N5 V5.3, printed pages 63-74. The PDF index places Ammunition on
  pages 63-67 and Weaponry on pages 68-74.

The section produced implementation-relevant findings in `rules-semantics.md`
and future-facing runtime/spatial findings in `rules-research.md`. The existing
Army data model already preserves Ammunition IDs/names and detailed Weapon
profile fields; the main gap is rules identity/semantics rather than source-data
retention. The curated N5 V5.3 collection currently has no first-class
Ammunition records, so the rules-reference expansion backlog now explicitly
tracks base identities, combined composition, and Saving-Roll relationships.

#### Ammunition and Saving-Roll semantics

N5 V5.3 defines eleven base Ammunition types:

`N`, `AP`, `DA`, `Eclipse`, `E/M`, `EXP`, `PARA`, `Shock`, `Smoke`, `Stun`,
and `T2`.

They do not form a single "damage modifier" axis. Depending on Ammunition, the
rule may change the Saving Roll Attribute or its effective value, change the
number of Saving Rolls, change Wounds per failed Roll, apply or cancel States,
create a visibility zone without a Saving Roll, or impose target-eligibility
conditions. The Combat finding that Weapon profiles must preserve PS,
Ammunition, Saving Roll Attribute, Saving Roll count, and Traits independently
is therefore reinforced rather than simplified by this section.

`Combined Ammunition` and `Combined Saving Roll` also establish an important
parsing boundary. A plus sign in the Ammunition field (for example `AP+DA`)
means one composite Ammunition applying the component effects together. A plus
sign in a Saving Roll expression (for example `ARM+BTS`) instead means that the
weapon requires Saving Rolls against different Attributes. These operations are
not interchangeable and must be interpreted in field context.

Army source data already exposes global Ammunition identities and may include
combined names such as `AP+DA` as source catalog entries. InfinityDB should keep
those source IDs/labels for provenance while a curated rules layer can express
the semantic composition explicitly. It should not infer arbitrary composition
from punctuation alone when a reviewed source mapping is available.

#### Weapon modes and shared resources

Mixed Weapons confirm that one canonical Weapon can have materially different
BS and CC modes. A mode may change the Attribute used for the Attack, Range
bands, Burst, Ammunition, Saving Roll fields, and Traits. This reinforces the
existing application-model decision to keep exact Weapon mode/profile rows
contextual rather than promoting one mode to invariant canonical Weapon facts.

Disposable use counts can also be shared across modes. The rules explicitly
state this for multi-mode Disposable weapons, and Drop Bears/D-Charges provide
concrete examples. A consumer must therefore not model each mode as having an
independent ammunition/use counter merely because the modes have separate
profile rows.

#### Deployables, delivery weapons, and representation

Several named rules expose a reusable relationship pattern:

- Pitcher places a Deployable Repeater;
- Mine Dispenser and Drop Bears can deploy a Mine;
- Disco Baller places/activates a Disco Ball effect;
- Armed Turret, Mines, WildParrot, and other Deployables become independent
  table game elements with their own ARM/BTS/STR/S profile.

A delivery Weapon can therefore have no meaningful PS/Ammunition/Saving-Roll
payload of its own because its effect is to place another game element. Blank or
dash profile values in those cases are semantic, not necessarily incomplete
metadata.

Mines also demonstrate runtime representation separate from identity: they can
begin as a Camouflaged Marker and later be represented by a Mine Token while
remaining the same deployed rules object. This aligns with the earlier
Model/Marker/Token distinction and should not create duplicate canonical
entities merely because the table representation changes.

Perimeter Weapons cross catalog boundaries: the rule can apply to Weapons or
Equipment carrying the Perimeter Trait. Their trigger/Boost behavior depends on
current positions, enemy activity, and Trigger Area, so those runtime facts
belong in research/session semantics rather than the static Army snapshot.

#### Target predicates and State effects

Ammunition/weapon effects frequently depend on target properties rather than
only on a profile number. Examples include E/M applying additional
Immobilized-B effects to specific Troop Types, PARA having no effect when PH is
absent, Shock interacting with VITA 1 and Unconscious-related rules, and
Sepsitor requiring Cube or equivalent Equipment before it can cause
Sepsitorized State.

InfinityDB should represent such knowledge as cited rules relationships and
predicates if/when consumed. It must not turn those effects into unconditional
static properties of every Weapon occurrence.

SymbioBomb additionally introduces an owner-to-user assignment relationship
during Deployment. The Unit Profile identifies who owns the item; the current
game determines which eligible Trooper becomes its user. Those are different
relationship scopes.

#### Application reconciliation

The Army normalization/database layers already preserve Ammunition catalog IDs
and names plus Weapon mode/profile fields such as Ammunition, Burst, source
`damage`/PS, Saving Roll expression/count, Traits, Range, and mode. That is a
suitable lossless/source-context foundation for the rules semantics above.

The curated rules layer already has the generic `ammunition` kind available but
contains no current first-class Ammunition records. The implementation backlog
now calls for the eleven base identities plus reviewed composition/effect
relationships rather than hard-coding effects into Weapon names or browser
logic.

This audit does not change runtime data, curated rules records, or the web UI.
It only records the semantic contract and the resulting focused backlog work.

### Fireteams — section complete

Status: core N5.3 wiki/PDF semantic extraction complete for the Fireteams Module.
The audit intentionally focuses on chart structure, eligibility relationships,
bonus-equivalence semantics, and terminology useful to InfinityDB rather than
reproducing Fireteam activation and integrity procedures as a rules engine.

Primary sources reviewed:

- Wiki: <https://infinitythewiki.com/Infinity_Fireteams> and the linked Fireteams
  pages (`Fireteams:_Basic_Rules`, `Fireteams_Chart`, `Fireteam_Integrity`,
  Active/Reactive Turn, Bonuses, and Examples), reviewed against the live N5.3 /
  FAQ v0.1 wiki.
- PDF: Infinity N5 V5.3, printed pages 132-142.
- FAQ: N5 FAQ v0.1, printed page 3, for Fireteam Type persistence and
  formation-minimum clarification.
- Historical terminology cross-check:
  - Infinity Human Sphere N3, where `Linkable` appears as an official profile
    descriptor.
  - Infinity N4 Fireteams Annex / rules v2.1, where the official concept was
    `Fireteam Composition Bonuses`; contemporary community usage commonly called
    qualifying teams `pure Fireteams`.

The section confirms that Infinity Army's current Fireteams Chart is the
authoritative source for army/sectorial-specific composition. The rules explain
how to interpret that chart; they do not replace it with one universal
eligibility rule.

#### Fireteam identity, Type, and Level

N5 distinguishes at least three concepts that must not be collapsed:

1. the **Fireteam** itself, a runtime group created from eligible Troopers;
2. its **Type** (`Duo`, `Haris`, or `Core`), constrained by the Army's chart;
3. its **Fireteam Level**, which determines bonuses from the number of members
   treated as belonging to the same Unit for this purpose.

The Type is not another name for the current member count. FAQ v0.1 explicitly
clarifies that a Haris that loses a member remains a Haris rather than becoming
a Duo. Fireteam Level, by contrast, is recalculated as membership changes.
InfinityDB should therefore present Type and Level as separate concepts.

The general creation sizes (Duo 2, Haris 3, Core 3-5) are defaults interpreted
together with the Army's Fireteams Chart. They are formation semantics, not a
reason to reject a later runtime Fireteam merely because it has lost members.

#### Fireteams Chart as authoritative Army-local relationship data

The current rules explicitly identify the Infinity Army app as the source of the
official, up-to-date Fireteams Charts. The chart describes:

- maximum simultaneous Fireteams by Type;
- which Fireteam Types each named chart entry can create;
- per-entry minimum/maximum composition constraints;
- required-choice rows marked by an asterisk;
- additional chart notes that can override the general Fireteam rules;
- FTO restrictions to specific Unit Profile options;
- Wildcard participation and per-Fireteam maximums; and
- bracket/note terms used when determining Fireteam Level.

These are **Army-local relationship/configuration facts**. They must not be
promoted to universal properties of a logical Unit. The same Unit can have
different Fireteam eligibility or restrictions in another Army/Sectorial, and a
single Unit can expose only selected FTO options to a particular Fireteam.

This fits InfinityDB's broader scope: retain the concrete Army-chart occurrence,
then relate it to game-wide Unit/profile identities without erasing the
army-specific rule.

#### Formation constraints are not permanent membership invariants

FAQ v0.1 clarifies that the minimum/required conditions in the Fireteams Chart
apply when the Fireteam is created. Losing a Trooper that was required for
formation does not by itself cancel the Fireteam. Likewise, Type persists after
member loss.

That distinction is important for data naming. A chart `min`, maximum, or
required marker describes a **formation constraint**. It should not be exposed
as an invariant assertion that every later valid state of the Fireteam must
still contain that member/count.

Current Army source data also shows multiple rows in the same chart entry with
`required: true` and `min: 0`. This aligns with the official asterisk rule:
at least one Trooper from the marked set must be selected. The normalized
`required` boolean must therefore not be interpreted as "this individual row is
always mandatory".

#### FTO is option-level eligibility

The chart's `FTO` notation has explicit option semantics: when a Unit is listed
as FTO, only Unit Profile options whose option name carries FTO are eligible;
when a specific variant such as FTO-2 is named, only that variant qualifies.

InfinityDB currently resolves a normalized Fireteam member slug to a source Unit
when possible while preserving the chart's name/comment/min/max/required fields.
That is a useful provenance link but is not enough to prove option-level
eligibility. A future canonical Fireteam relationship layer should resolve FTO
against the applicable source option/loadout while keeping the original chart
wording for audit and presentation.

#### Wildcards and bracket terms are relationships, not Unit identity

A Wildcard may participate in any Fireteam allowed by the chart, subject to its
maximum. That is an Army-local eligibility relationship, not an intrinsic Unit
Characteristic.

Bracketed terms such as `(Morat)` or `(Fennec)` have a different purpose: for
Fireteam Level calculations, members with the same bracket term are treated as
belonging to the same Unit. This is **bonus-equivalence semantics only**. It does
not make the underlying Units one canonical Unit and must not feed logical-Unit
deduplication.

This is especially important for InfinityDB because the source already preserves
those bracket labels in Fireteam-member comments while logical Unit identity is
owned by a separate canonicalization layer.

#### Chart notes are rule-bearing data

The Fireteams Chart rules state that additional chart conditions can take
priority over the General Rules of Fireteams. Army `desc`/`obs` text is therefore
not necessarily decorative presentation metadata. It may encode an
army-specific eligibility or behavior exception.

InfinityDB should preserve those notes losslessly and display them with the
relevant Fireteam. Structured interpretation can be added only where a reviewed
consumer needs it; free-text rule notes should not be guessed into executable
logic.

#### Chart eligibility versus runtime eligibility

The chart answers which Troopers/options may be used to form a Fireteam, but the
general rules also impose runtime restrictions based on current state and role:
for example Marker, Isolated/Null, Suppressive Fire, Peripheral/Controller, and
Coherency interactions.

InfinityDB's catalog view should therefore describe **chart eligibility**, not
claim that a listed Trooper can always join or remain in a Fireteam in every
game state. The detailed runtime integrity/ARO/activation procedures remain
research context rather than application-schema requirements.

#### Terminology provenance: `Linkable` and `pure Fireteam`

The terminology investigation resolves the two community terms flagged before
this pass:

- **`Linkable` has historical official provenance.** Human Sphere N3 used
  `Linkable` directly in Unit/Profile material for Troopers able to participate
  in Fireteams. Current N5 does not use it as the canonical eligibility field;
  eligibility is expressed through the Army Fireteams Chart, including FTO,
  Wildcards, min/max constraints, and notes. Modern community use of "linkable"
  is therefore understandable shorthand, but a single `linkable=true` flag would
  lose important N5 context.
- **`pure Fireteam` is community shorthand rather than the current N5 term.**
  N4 officially defined `Fireteam Composition Bonuses` for Fireteams composed
  only of the same Unit (or chart-equivalent entries), and community discussion
  widely called teams satisfying that condition "pure". N5.3 instead uses one
  `Fireteam Level` based incrementally on the number of same-Unit/bracket-
  equivalent members. The phrase remains useful for search/help, but should map
  to current Fireteam-Level semantics rather than be presented as a current
  rules-defined Fireteam Type.

Both terms are retained in `rules-research.md` as provenance-aware thesaurus
candidates. This is a case where InfinityDB should support the vocabulary users
actually encounter without conflating historical/community language with the
current official ontology.

#### Application reconciliation

The normalization layer already preserves the important source shape:

- army-level Fireteam description and `fireteamChart.spec`;
- named Fireteam rows and observations;
- ordered Fireteam Type memberships;
- member slug/name/comment, min/max, and `required`;
- best-effort source Unit resolution plus explicit unresolved/ambiguous status.

That is a good lossless starting point, but several fields need semantic
interpretation before a first-class application Fireteam model is built:

- `fireteamChart.spec` corresponds to chart Type-quantity limits and should not
  remain an opaque presentation blob in the eventual application model;
- FTO restrictions require option-level resolution, not only Unit resolution;
- `required` may represent membership in a required-choice set rather than an
  individually mandatory row;
- bracket terms are Fireteam-Level equivalence labels, not canonical Unit aliases;
- Wildcards are Army-local membership relations; and
- descriptions/observations may carry rule overrides.

The existing Fireteam feature and Milestone 2 relationship backlog now records
those consequences. No runtime schema, normalization behavior, or UI was changed
by this audit.

### Command — section complete

Status: core N5.3 wiki/PDF semantic extraction complete for the Command Module.
The pass records the resource, catalog, and relationship semantics that help
InfinityDB interpret profile data and cross-link concepts. Detailed timing,
resource expenditure, ARO, and multi-Trooper resolution procedures remain
reference context rather than an application state machine.

Primary sources reviewed:

- Wiki: <https://infinitythewiki.com/Command_Module>,
  <https://infinitythewiki.com/Command_Tokens>, and
  <https://infinitythewiki.com/Coordinated_Orders>, reviewed against the live
  N5.3 / FAQ v0.1 wiki.
- PDF: Infinity N5 V5.3, printed pages 128-131.
- Cross-section rules used to classify static catalog interactions:
  <https://infinitythewiki.com/Lieutenant>,
  <https://infinitythewiki.com/Counterintelligence>, and
  <https://infinitythewiki.com/NCO> (PDF printed pages 99, 90, and 104).

Embedded FAQ material on the Coordinated Orders wiki page was observed but not
promoted into core findings; FAQ/errata remains a separately scoped audit source.

#### Command Tokens are match resources, not profile entities

A player normally starts a match with four Command Tokens. `Strategic`,
`Executive`, and `Operational` describe **ways the same resource can be used**,
not three different token identities.

This is useful for InfinityDB because profile/catalog facts can affect Command
Tokens without making the runtime token pool part of canonical Unit data. For
example, a Lieutenant option can provide `+1 Command Token`, while
Counterintelligence modifies particular Strategic Use effects. Those are
source/rules relationships from a Skill/profile option to a player/session
resource.

InfinityDB can expose those relationships and explanatory cross-links while
leaving the actual token count, expenditure, timing, and remaining resource to a
future list/game-session layer. There is no reason to materialize a current
Command Token balance in the imported application database.

#### Command Tokens and Orders are separate resource families

The Command Module repeatedly combines Command Tokens with Orders but does not
make them interchangeable. A normal Coordinated Order consumes one Command
Token and one Regular Order from the relevant Combat Group. Other Skills operate
on Orders without operating on Command Tokens: for example, NCO replaces Special
Lieutenant Orders with Tactical Orders.

This distinction reinforces the existing Order semantics audit. Static profile
data can describe Training, generated Order capabilities, and Skills such as
NCO/Tactical Awareness; Command Tokens remain a separate player/match resource.

#### Coordinated Orders are runtime activation, not a persistent relationship

A Coordinated Order temporarily activates up to four eligible Troopers together.
The participating set, chosen Spearhead, declared Skill sequence, targets, and
resolution exist for that Order only. This is not equivalent to Unit identity,
Fireteam membership, Peripheral/controller linkage, or another persistent
relationship that belongs in the canonical application model.

The rules nevertheless expose useful semantic predicates:

- all participants must be in the same Combat Group;
- all participants must have the same Training (`Regular`/`Irregular`);
- all declare the same sequence of Skills;
- one participant has the transient `Spearhead` role; and
- Peripherals/Controllers and Fireteam members are excluded by the applicable
  runtime rules.

The same-Training requirement independently confirms the rules-domain
classification established earlier: Regular/Irregular are Training categories.
Army-derived data may validly surface `Regular` through a skill-like source
structure for compatibility, but that source container does not redefine the
game concept.

#### Skill identity and implementing item are different

A Coordinated Order requires participants to declare the same Skill sequence,
but participants can perform that Skill with different Weapons or Equipment.
The rule example treats different weapons as implementations of the shared
`BS Attack` declaration.

This is useful catalog semantics. InfinityDB should keep the identity of an
action/Skill distinct from the Weapon or Equipment selected to perform it.
Cross-links can express that an item participates in or enables an action without
merging the item into the Skill catalog.

#### Command interactions do not change Fireteam chart authority

Operational Use of a Command Token can create a new Fireteam during play, but
the Trooper selected as Fireteam Leader still has to meet the Army's Fireteam
Chart Requirements. The Command rule is therefore a runtime creation mechanism;
it does not create new chart eligibility or modify the imported Army
Fireteams Chart.

This supports the Fireteams audit boundary: Army-local chart/configuration data
remains the static reference authority, while creation, current membership, and
Command Token expenditure are session state.

#### Application reconciliation

No new imported-data domain is required for Command Tokens or Coordinated Orders.
The current separation is appropriate:

- Army/profile data can preserve Skills and option annotations such as
  Lieutenant, NCO, Counterintelligence, and related extras;
- curated rules data can provide reviewed relationships from those catalog facts
  to Command/Order concepts;
- Fireteam chart eligibility remains imported Army context; and
- Command Token balance, Combat Group membership of a constructed list,
  Spearhead selection, participating Troopers, expenditure, and action resolution
  are runtime/list-session facts.

The broader rules-reference/play-aid backlog already provides a suitable future
home for concise Command Token and Coordinated Order guidance. This audit adds no
separate rules-engine or session-model implementation requirement.

### Movement — section complete

Status: core N5.3 Movement Module semantic extraction complete. The pass keeps
only movement semantics that help InfinityDB interpret profile Attributes,
Skill/Label relationships, parameterized distances, and presentation units.
Exact route geometry, ARO timing, and tabletop movement resolution remain
reference context rather than an application movement engine.

Primary sources reviewed:

- Wiki: <https://infinitythewiki.com/Movement_Module>,
  <https://infinitythewiki.com/Moving_and_Measuring>,
  <https://infinitythewiki.com/Move>,
  <https://infinitythewiki.com/General_Movement_Rules>,
  <https://infinitythewiki.com/Cautious_Movement>,
  <https://infinitythewiki.com/Climb>, and
  <https://infinitythewiki.com/Jump>.
- PDF: Infinity N5 V5.3, printed pages 27-35.
- Cross-section rules used to interpret profile movement modifiers:
  <https://infinitythewiki.com/Super-Jump>,
  <https://infinitythewiki.com/Climbing_Plus>,
  <https://infinitythewiki.com/Prone_State>, and
  <https://infinitythewiki.com/Labels>.

The live Movement Module, Moving and Measuring, Move, General Movement Rules,
Climb, and Jump pages identify the current N5.3 rules. The Cautious Movement page
currently carries an older N5.2 / FAQ v0.0.0 page notice; no N5.3-specific change
is shown there, so its content was treated as an unchanged current rule while the
N5 V5.3 PDF remains the edition baseline.

#### MOV is an ordered profile pair, not a generic speed score

The rules define the MOV Attribute as normally containing two values. The first
value is used the first time the Trooper moves in an Order, and the second value
is used for the second movement. `Move` makes that ordering explicit: the first
Move uses the first MOV value and a second Move uses the second value.

This confirms the semantic meaning of InfinityDB's existing `move_1` and
`move_2` profile fields. They are an ordered pair and must not be sorted,
averaged, or collapsed into one canonical movement number. A display such as
`4-4` is compact notation for two positionally meaningful values.

The rules express MOV in inches. Infinity Army source values retained by
InfinityDB use their source-native metric representation, and the browser already
converts those values using the project's shared 2.5 cm/inch convention. That is
presentation conversion around preserved source data, not a change in the
meaning of the MOV pair.

#### Movement is a Label, not a declaration category

`Movement` is a rules Label that can apply across Skills and AROs. Moving and
Measuring is invoked when a Skill with the Movement Label is declared, while the
declaration category (`Basic Short`, `Short`, `Long`, `ARO`, etc.) independently
determines how that action consumes an Order.

The distinction matters because different movement actions have different
categories: Move is a Basic Short Skill, while ordinary Jump and Climb are Long
Skills, and Special Skills such as Super-Jump and Climbing Plus can modify those
categories or how movement is performed.

InfinityDB's curated `movement` Label is therefore the correct kind of semantic
vocabulary, but label membership and declaration category must remain separate
relationships. Movement-like behavior should not be inferred merely from a
Skill name or its declaration category.

#### Parenthetical movement distances belong to the Skill occurrence

The N5.3 Jump and Climb rules use the first MOV value plus a rules-defined bonus.
For both ordinary Skills that bonus is normally 2 inches. If the relevant Skill
is listed in the Unit Profile with a distance in round brackets, that listed
distance replaces the normal 2-inch bonus; it is not a replacement for the
Trooper's MOV Attribute or the total movement distance.

Super-Jump further demonstrates why the exact relationship matters: the Special
Skill changes how Jump can be declared, gives a different Long-Skill bonus, and
can itself carry a profile distance affecting the Short-Skill Jump case.
Climbing Plus similarly changes declaration and surface semantics without
rewriting the underlying MOV values.

This supports InfinityDB's existing rule-derived parameter-semantics boundary.
A distance extra should remain attached to the Skill occurrence and be explained
according to that Skill's semantics rather than promoted to a generic MOV
modifier.

#### MOV does not completely describe mobility

A profile's MOV pair describes the base distance allowance used by movement
rules, but it is not a complete measure of how the Trooper can traverse the
table. Jump, Climb, Super-Jump, Climbing Plus, terrain/scenery geometry, States,
and other rules can change available routes, declaration categories, movement
distance, or usable surfaces without changing the stored MOV Attribute.

InfinityDB should therefore present MOV as a profile Attribute and relate it to
movement Skills where useful, rather than derive a universal `mobility` or
`speed` value from MOV alone.

#### Runtime geometry and Cautious Movement stay outside the catalog model

Movement paths are declared action-local geometry. LoF and ARO opportunities can
depend on points traversed along the route, and the general rules distinguish
horizontal surfaces, vertical surfaces, vaulting, ladders, base support, and
Silhouette-dependent obstacles.

Cautious Movement is likewise a contextual procedure for avoiding AROs when its
current-game requirements are met. Its restrictions reference otherwise useful
catalog concepts such as Troop Type, Motorcycle/Aerial, Hackable, Hacking Area,
and Targeted State, but those references do not establish an invariant
`can_cautious_move` property on a Unit.

Those procedural facts remain in `rules-research.md` for terminology and future
play-aid context. They do not require movement-path, board-position, or action
resolution tables in InfinityDB.

#### Application reconciliation

The existing application model already has the important static boundary:

- canonical profile payloads retain ordered `move_1` / `move_2` values;
- source metric values remain preserved while the browser can present inches;
- Skill extras retain source association instead of becoming global profile
  Attributes;
- the curated rules vocabulary already has a `Movement` Label; and
- States, table positions, movement routes, ARO opportunities, and terrain
  geometry are not stored as canonical Unit facts.

No schema or runtime change is required by this audit. Future rules-reference
coverage can add reviewed Movement-label and Skill-parameter relationships where
they improve profile help/search, without attempting to reproduce the Movement
Module as executable rules.

### Terrain and Scenery Structures — section complete

Status: core N5.3 Terrain and Scenery Structures semantic extraction complete.
The pass records the finite terrain vocabulary and the rules relationships that
help explain profile Skills and cross-domain effects, while keeping battlefield
layout, zone placement, and movement/combat resolution in table/session context.

Primary sources reviewed:

- Wiki: <https://infinitythewiki.com/Terrain_and_Scenery_Structures>,
  <https://infinitythewiki.com/Types_of_Terrain>,
  <https://infinitythewiki.com/Difficult_Terrain>,
  <https://infinitythewiki.com/Saturation>,
  <https://infinitythewiki.com/Visibility_Conditions>, and
  <https://infinitythewiki.com/Scenery_Structures>.
- PDF: Infinity N5 V5.3, printed pages 143-145.
- Cross-section rules used for reconciliation:
  <https://infinitythewiki.com/Terrain>,
  <https://infinitythewiki.com/Dazer>,
  <https://infinitythewiki.com/Smoke_Ammunition>,
  <https://infinitythewiki.com/Eclipse_Ammunition>, and
  <https://infinitythewiki.com/White_Noise>.

The live parent page is explicitly part of the N5.3 update. The principal N5.3
terminology change visible there is `Difficult Terrain` replacing the older
`Difficult Movement` wording. The N5 V5.3 PDF is the edition baseline for all
findings below.

#### Special Terrain is table configuration, not canonical Unit data

Special Terrain is optional and agreed by the players before the game. A zone is
defined by a Type of Terrain plus at least one other terrain characteristic from
Difficult Terrain, Saturation, and Visibility Conditions. Its effects apply by
table position/contact.

That is useful semantic evidence for interpreting Terrain-related Skills and
Equipment, but the selected zones are match/table configuration. They do not
belong in canonical Unit, profile, or Army-list identity. A future scenario or
table reference may describe them without turning InfinityDB into a board-state
engine.

#### Terrain Type is a finite vocabulary shared with the Terrain Special Skill

The current Type of Terrain vocabulary is:

- Aquatic;
- Desert;
- Mountain;
- Jungle; and
- Zero-G.

The Terrain Special Skill uses exactly this vocabulary as a profile parameter.
A profile that lists several Types requires a choice when the Trooper is placed
on the table; `Terrain (Total)` applies to all five current Types.

This makes a Terrain parenthetical value a typed parameter/relationship rather
than a generic text extra or numeric MOD. InfinityDB can eventually use the
finite vocabulary for explanation, filtering, and rules-reference links while
preserving the exact Army occurrence for provenance.

The existing curated declaration-category record for Terrain is already covered
by the previously recorded declaration-category reconciliation task; this pass
does not duplicate that backlog item.

#### Terrain characteristics are independent axes; examples are not identities

The rules' Beach, Swamp, Jungle, Engine Room, Generator Room, and similar rows
are explicitly suggestions/examples assembled from the independent
characteristics. They are not additional canonical Types of Terrain.

InfinityDB should therefore avoid constructing a terrain ontology from example
names. If scenario/table content is modeled later, a named area can retain its
scenario/display name while its mechanical characteristics remain separate,
typed relationships.

#### Visibility Conditions are reusable zone semantics across rules domains

Low, Poor, Zero Visibility, and White Noise are four current Visibility
Conditions. They are not Types of Terrain. Terrain can assign them to an area,
but other rules can create the same semantic zone effects: Smoke and Eclipse
create visibility zones, and the White Noise Hacking Program creates a White
Noise Zone.

This supports a shared glossary/rules-reference identity for visibility-zone
concepts rather than separate terrain-, ammunition-, and hacking-specific copies.
Actual active zones and their geometry remain runtime/table state.

#### Difficult Terrain and Saturation modify actions, not stored profile facts

Difficult Terrain can end movement on contact and applies a movement reduction
when the Trooper continues through the area. Saturation applies a contextual
Burst MOD to BS Attacks crossing the zone. Neither effect rewrites the
Trooper's stored MOV pair or a Weapon's printed Burst.

The same principle applies to Terrain Skill immunity/bonuses, Visibility MODs,
and Dazer-created Difficult Terrain: InfinityDB should describe the relationships
where useful, but keep source profile values canonical and treat the applied
effect as action/table context.

#### Scenery Access Width is a table property evaluated against Silhouette

Scenery Structures currently define Narrow and Wide Access Widths. Narrow admits
Troopers with the required Silhouette size, while Wide admits all Troopers.
The rule also demonstrates that the Silhouette used for an access check is
contextual: a Prone Trooper represented by SX uses the Silhouette value printed
on its Unit Profile for this restriction.

Access Width is therefore useful glossary/profile-help context around `S`, but it
does not justify a static `can pass narrow` Unit field. Scenery geometry,
current State, and scenario exceptions remain table context.

#### Application reconciliation

The current application boundary remains appropriate:

- profile MOV and Silhouette remain source/canonical facts;
- the Terrain Skill remains a Skill occurrence whose parameter can be given
  typed rules semantics;
- visibility, Saturation, Difficult Terrain, and Access Width can become
  glossary/reference concepts and cross-links;
- named example terrains are not promoted to canonical game entities; and
- actual terrain zones, scenery layout, active visibility templates, and applied
  movement/Burst MODs remain outside the canonical application model.

No new schema/runtime task is required by this audit. The existing broader
curated-rules/reference backlog can absorb Terrain parameters and cross-domain
zone links where they improve catalog interpretation.

### Triumph and Defeat — section complete

Status: core N5 V5.3 Triumph and Defeat semantic extraction complete. This
section primarily defines scoring and end-game/session concepts rather than
additional static Unit or catalog data, so only the distinctions that improve
InfinityDB's reference semantics are promoted.

Primary sources reviewed:

- Wiki: <https://infinitythewiki.com/Triumph_and_Defeat_Module>.
- PDF: Infinity N5 V5.3, printed pages 146-147.
- Cross-section rules used for reconciliation:
  <https://infinitythewiki.com/States>,
  <https://infinitythewiki.com/Normal_State>, and the Retreat! State on
  printed page 170.

The live Triumph and Defeat wiki page currently carries an N5.2 / FAQ 0.0.0
notice. Its Standard Game, Retreat!, Mission/Scenario, and Free Game material
was cross-checked against the N5 V5.3 PDF; no semantic discrepancy relevant to
this audit was found. The PDF remains the edition baseline.

#### Victory Points and Objective Points are different scoring concepts

The existing glossary finding `RS-GSG-TERM-003` already establishes that
Victory Points are a runtime aggregation of the Cost of a player's non-Null
Troopers. Triumph and Defeat adds the scoring context: Standard Games compare
Victory Points directly, while missions/scenarios award their own Objective
Points and use Victory Points as the tiebreaker when Objective Points are tied.

InfinityDB should therefore keep `Cost`, `Victory Points`, and `Objective
Points` semantically distinct. Cost is imported list-option data; Victory Points
require an Army List plus runtime State; Objective Points are defined by the
selected scenario. A future scenario reference can describe scoring without
turning either aggregate into an intrinsic Unit/Profile field.

#### Retreat! situation and Retreat! State have different scopes

Retreat! is first evaluated at the Army/player level during the Tactical Phase.
Under the core rule, an army enters the Retreat! situation when its current
Victory Points are at or below 25% of the Army Points available for list
construction. That army-level situation then causes surviving Troopers to enter
Retreat! State unless a rule protects them from it.

These concepts should not be collapsed. `Retreat! situation` is session-level
army state; `Retreat! State` is a Trooper State in the existing State vocabulary.
The State may also be cancelled for an individual Trooper by a Command Token
without ending the army's Retreat! situation.

The threshold is likewise not a canonical Army or Unit property. It depends on
the agreed/list-construction point budget and current runtime Victory Points.
Troopers not yet placed on the table are specifically treated as survivors for
the Retreat! check, which further demonstrates that it is a game-state
calculation rather than a simple database sum.

#### Mission/scenario and Free Game are game-context vocabulary

A mission/scenario defines objectives and their Objective Point awards. A Free
Game is one where players agree to change the recommended Game Mode parameters,
such as Army Points, table/deployment dimensions, Trooper limits, or Game
Rounds.

These terms are useful for the cross-domain thesaurus and future scenario/setup
reference features, but they are not canonical Army-data domains. The already
planned scenario/ITS reference work is the appropriate consumer; this audit
does not add a separate game-mode schema or rules engine.

#### Application reconciliation

The current application boundary remains appropriate:

- option Cost remains source/list-context data;
- the State vocabulary can represent Null and Retreat! State semantics;
- Victory Points and Retreat! require a selected Army List plus runtime State;
- Objective Points belong to scenario scoring rather than Unit/catalog data; and
- game-mode/free-game parameters belong to session/scenario setup.

No new schema/runtime task is required by this audit. The existing glossary,
Game States, scenario-reference, and future saved-list/session work already
provide appropriate homes for these concepts if and when InfinityDB needs to
present them.

### Setting up the Gaming Table — section complete

Status: core N5 V5.3 semantic extraction complete. This section is explicitly
presented as setup advice rather than mandatory rules, so the audit records the
scope distinctions and useful setup vocabulary without turning qualitative table
design guidance into an InfinityDB validation model.

Primary sources reviewed:

- Wiki: <https://infinitythewiki.com/Setting_up_the_Gaming_Table>, live N5.3
  page.
- PDF: Infinity N5 V5.3, printed pages 147-148.
- Cross-section rules used for reconciliation: Basic Rules / Game Modes,
  Initiative and Deployment, Terrain and Scenery Structures, Cover, and the
  scenario Forces and Deployment tables.

#### Generic table guidance is advisory, not scenario authority

The section explicitly says its advice is informative and not mandatory. It
recommends table sizes by Army Points, balancing Cover against long-range lines
of fire, terrain density/layout, accessibility, and Deployment Zone asymmetry.

Those recommendations are useful explanatory/setup-reference material, but they
are not universal list-legality constraints. Basic Rules Game Modes already
provide recommended table/deployment dimensions, while individual scenarios can
define their own Forces and Deployment parameters. If InfinityDB presents setup
information, it should label generic recommendations as such and preserve a
scenario's own setup values as scenario-scoped facts.

#### Terrain layout and accessibility are table-design guidance

The rules recommend enough terrain and Cover to allow maneuver without removing
the value of long-range weapons. They also recommend accessible elevated areas,
avoiding excessive bottlenecks/blind alleys, and arranging large/small terrain
so players have useful movement routes.

These are intentionally qualitative table-design principles. They should not be
converted into hard data validation such as a required scenery count, mandatory
maximum gap, or algorithmic `balanced table` result. A future table/scenario aid
may summarize the guidance, but InfinityDB remains a catalog/reference system
rather than a terrain-layout judge.

#### Symmetrical and asymmetrical Deployment Zones are setup vocabulary

The section distinguishes symmetrical and asymmetrical Deployment Zones by the
amount, size, and arrangement of terrain on each side. It explicitly presents an
asymmetrical zone with more Cover and/or elevated terrain as a possible tactical
advantage for the player choosing that side.

This is useful thesaurus/map vocabulary but not a characteristic of an Army,
Unit, or the Deployment Zone dimensions themselves. A future scenario/map
reference could annotate terrain symmetry separately from the numeric Deployment
Zone geometry if that helps explain a published layout.

#### Application reconciliation

No current application schema or runtime behavior needs to change:

- existing Game Mode research already captures recommended point/table/deployment
  presets;
- Terrain/Scenery and Cover semantics are already documented by their owning
  sections;
- Deployment Zone dimensions remain game/scenario setup context;
- table density, accessibility, sight lines, and symmetry are qualitative
  configuration of a particular physical/digital table; and
- scenario-specific setup data should remain scoped to the scenario rather than
  inferred from generic recommendations.

The section therefore adds only one implementation-relevant scope finding and
two research/reference findings. No new implementation backlog item is warranted.

### Scenarios — section complete

Status: core N5 V5.3 semantic extraction complete for the introductory scenario
section. The audit intentionally separates **scenario-defined catalog concepts**
from a **complete scenario library**: the former are in scope where they improve
InfinityDB's general reference coverage, while full scenario list/detail coverage
is not a version-1.0 requirement.

Primary sources reviewed:

- Wiki: <https://infinitythewiki.com/Scenarios>, live N5.3 page.
- Wiki: <https://infinitythewiki.com/Annihilation>, live N5.3 page.
- Wiki: <https://infinitythewiki.com/Domination>, live N5.3 page.
- Wiki: <https://infinitythewiki.com/Supplies>, currently carrying an N5.2 / FAQ
  0.0.0 notice.
- Wiki: <https://infinitythewiki.com/Firefight>, currently carrying an N5.2 / FAQ
  0.0.0 notice.
- PDF: Infinity N5 V5.3, printed pages 149-156.

The V5.3 PDF is the edition baseline for Supplies and Firefight. Their
implementation-relevant concepts were cross-checked against the current V5.3
PDF rather than promoting the older wiki notice to source authority.

#### The core Scenarios section is illustrative, not an exhaustive scenario corpus

The Scenarios overview says the rulebook contains a small introductory set and
points players to additional official content. The four core scenarios are
Annihilation, Domination, Supplies, and Firefight.

InfinityDB should therefore not treat this section as defining the complete
Infinity scenario catalog. Auditing these pages is necessary to discover
scenario-defined rules concepts and scope interactions, but completing a full
core/ITS scenario library is separate product work and does not block 1.0.

#### Scenario-defined Skills remain real reference concepts

Domination defines **Hack Consoles** as a Short Skill with the Attack Label.
Supplies defines **Pick Up Supply Boxes** as a Short Skill with the Attack Label.
Neither action is an Army-profile Skill: availability comes from the selected
scenario plus its requirements.

These are nevertheless useful rules-reference identities. InfinityDB's 1.0
catalog/reference completeness should be able to represent scenario-only Skills
(and scenario-only Equipment when encountered) with explicit scope/provenance.
They must not be inserted into a Trooper's static Army-derived Skill list merely
because that Trooper can declare them in a particular mission.

#### Specialist Troop is a scenario-scoped derived role

Domination, Supplies, and Firefight define Specialist Troops for their own
purposes using Doctors, Engineers, Forward Observers, Hackers, Paramedics,
Specialist Operatives, and Troopers with Chain of Command. The scenarios also
state that Doctors and Engineers cannot use Peripherals to perform tasks reserved
for Specialist Troops.

This makes **Specialist Troop** a contextual role derived from a scenario's rule
set and the Trooper's existing catalog facts, not another permanent Unit
Characteristic. The current core scenarios happen to share the same definition,
but InfinityDB should preserve the scenario scope so later mission/season rules
can differ without rewriting canonical Unit data.

#### Scenario elements are distinct from Equipment

Domination's Consoles and Supplies' Supply Boxes are mission objective/game
elements. The scenario-defined Skills target or manipulate them, and Supply Boxes
can be carried by Models, but those facts do not make the elements pieces of
Trooper Equipment.

A rules-reference implementation may need identities/relationships for such
scenario elements so scenario-only Skills can be explained coherently. It should
not force them into the Equipment catalog merely because they are interactive or
carried. No separate scenario-specific Equipment identity was found in these
four core scenarios; the 1.0 scope rule remains applicable when later sources do
define one.

#### Scenario special rules are scoped overlays, not canonical rewrites

Firefight demonstrates why mission rules need explicit scope. **Reinforced
Tactical Link** changes Lieutenant information/deployment behavior for that
mission, while **Designated Landing Area** modifies Combat Jump and Airborne
Deployment behavior on that table. These rules do not redefine Lieutenant,
Combat Jump, Airborne Deployment, or Open/Private Information globally.

The same principle applies to scenario scoring, Killed definitions, Domination
checks, Supply Box control, minimum-VP end conditions, and similar procedures:
they may be recorded for context or future mission pages, but they are session
rules rather than canonical Unit/Profile facts.

#### Application and version-1.0 reconciliation

The current architecture can preserve this boundary without adding a full
scenario model for 1.0:

- add scenario-defined Skills/Equipment and other named catalog concepts to the
  curated rules/reference layer when needed for general catalog completeness;
- preserve explicit scenario (and later season) scope/provenance on those facts;
- model Specialist Troop as a contextual relationship/derived role, not a static
  Unit characteristic;
- keep Consoles, Supply Boxes, and similar objective elements distinct from
  Trooper Equipment; and
- leave complete scenario identity, objectives/scoring, maps, deployment tables,
  and scenario list/detail pages as post-1.0 product/reference work.

This audit therefore creates a focused 1.0 catalog-coverage task rather than a
requirement to implement the four core scenarios as browsable missions.

### Quick Reference Charts — validation/completeness pass complete

Status: N5 V5.3 Quick Reference Charts reviewed as a cross-section validation pass,
with special attention to reference material that InfinityDB can generate from
Army data plus curated rule relationships rather than maintain as copied static
tables. The pass covers printed pages 176-195.

Primary sources reviewed:

- Wiki: <https://infinitythewiki.com/Quick_Reference_Charts> and the linked
  Weapon/Alternative Weapon, Ammunition, Orders/AROs, Martial Arts, Booty,
  MetaChemistry, Hacking Programs, Restrictions, Fireteam, and Retreat reference
  pages, reviewed against the live N5.3 wiki where available.
- PDF: Infinity N5 V5.3, printed pages 176-195.
- Current Army metadata shape as preserved by `src/infinity_army_data/metadata.py`
  and the normalized `metadata_*` tables, cross-checked against a recent source
  metadata snapshot for hacking programs, Martial Arts, Booty, MetaChemistry, Weapons,
  Equipment, and deployable profiles.

#### Quick-reference tables are projections, not a second rules ontology

The section mostly reorganizes concepts already defined by their owning rules:
Weapon profiles, Ammunition effects, declaration categories, Hacking Programs,
Skill levels/random tables, Fireteam bonuses, Retreat!/Loss of Lieutenant, and
static restrictions. InfinityDB should treat those charts as validation targets
and useful presentation patterns rather than author a second set of independent
chart facts.

Where the underlying facts already exist as Army metadata or curated semantic
relationships, a reference table should be generated from those sources. That
keeps detail pages, filters, cross-links, and quick-reference views consistent
and lets a source update propagate without hand-editing parallel tables.

#### Weapon and Ammunition reference is a natural generated view

The printed Weapon Chart occupies pages 176-188 and is primarily a denormalized
view of Weapon identity/mode, range MODs, PS, Burst, Ammunition, Saving Roll
Attribute/count, and Traits. The Alternative Weapon Chart is another presentation
of substantially the same underlying profile facts.

InfinityDB already preserves those exact source profile fields and reverse Unit/
loadout usage. Combined with curated Ammunition and Trait semantics, it can offer
a filterable/generated reference that is more useful than reproducing the fixed
chart: compare modes, filter by range/Ammunition/Trait, follow semantic links,
and see which Units/loadouts actually use the item. The existing weapon-and-
ammunition quick-reference backlog remains the correct implementation home.

#### Orders/AROs can validate and then consume declaration-category data

The page-191 Orders and AROs chart is a compact projection of declaration
categories across Common Skills, Special Skills, Hacking Programs, and Equipment
actions. It confirms that a generated declaration matrix is a useful consumer of
the existing declaration-category reconciliation work.

InfinityDB should not maintain a second hard-coded Orders/AROs table. Once current
N5 categories and cross-domain action links are corrected, the same structured
relationships can generate Basic Short/Short/Long/ARO reference views and expose
links back to the owning Skill, Equipment item, Hacking Program, or scoped
scenario action. This also provides an automated completeness check for missing
or contradictory declaration categories.

#### Army already carries several quick-reference datasets that the app does not expose

The Army metadata importer already preserves structured `hack`, `martialArts`,
`metachemistry`, and `booty` collections as normalized metadata tables. Current
source metadata includes Hacking Program profile fields and explicit Device IDs,
Martial Arts level MODs, and the complete Booty/MetaChemistry result rows.

These are strong candidates for generated rule-reference tables rather than
manually curated copies. Hacking Programs still need reviewed semantic identities
and Device/Upgrade relationships before presentation; Martial Arts can render its
level matrix from structured source rows; Booty and MetaChemistry can render their
random-result tables while cross-linking resolvable Skills, Equipment, Weapons,
and Attribute changes. The random results remain deployment/session outcomes, not
static Unit facts.

#### Restrictions Chart exposes a useful static relationship matrix

The V5.3 Restrictions Chart on printed page 194 confirms a finite set of static
profile/rule predicates: TAG, Motorcycle, Aerial, VH, REM, and Irregular each
restrict specific actions or Lieutenant eligibility. This closes the pending
Troop-Type cross-check from the initial Unit Profile research.

These restrictions are a good fit for a generated relationship/reference matrix
and contextual links from affected Troop Types/Training/Equipment/Skills. They do
**not** justify a general action-legality engine: the useful fact is the explicit
source-defined relationship, not an attempt to evaluate every declaration in a
live game.

#### Deployable Profiles reveal both a product gap and a source inconsistency

Printed page 195 gathers ARM/BTS/STR/S profiles for Armed Turret, CrazyKoala,
Cybermine, Dazer, Deployable Repeater, Disco Baller/Disco Ball, Drop Bears,
FastPanda, MadTraps, Mines, and WildParrot. Current Army Weapon/Equipment metadata
already carries structured `profile` values for many of these; InfinityDB also
supplies reviewed source corrections for omitted Mine profiles, while Armed
Turret has a richer curated special profile.

That makes a generated **Deployables** reference a genuine InfinityDB opportunity:
show the deployed object's defensive profile separately from the carrier/item,
link it back to the Weapon/Equipment rule and Unit/loadout uses, and avoid forcing
all deployables into a single catalog domain.

The validation pass also found a source conflict that must not be silently
normalized away: the V5.3 detailed Armed Turret profile on printed page 70 (and
the current wiki page) gives **S2**, while the page-195 Deployable Profiles
summary gives **S1**. InfinityDB's existing curated Armed Turret special profile
uses S2 from the owning rule. Keep the discrepancy documented and require an
official clarification/erratum or reviewed source-precedence decision before a
generated deployable table claims the summary value as authoritative.

#### Procedural summaries remain optional play aids

Game Sequence, Order Expenditure, Impetuous activation, Retreat!/Loss of
Lieutenant summaries, and similar charts mainly compress procedures already
audited in their owning sections. They remain useful optional play-aid material,
but do not become application schema merely because the rulebook presents them
as charts. Fireteam Bonuses similarly belong with the rule-aware Fireteams
feature, generated from curated general-rule semantics and kept separate from
Army-local composition charts.

#### Application reconciliation

This pass produces concrete reference/product work without changing the core
application model:

- retain the existing generated Weapon/Ammunition quick-reference direction;
- make a generated Orders/AROs matrix a consumer/validator of reconciled
  declaration-category relationships;
- expose structured Hacking Program/device, Martial Arts, Booty, and
  MetaChemistry reference tables from preserved source metadata plus curated
  semantics;
- add a narrow static Restrictions relationship matrix rather than an action
  legality engine;
- add a Deployables reference/profile surface that preserves carrier/item versus
  deployed-object identity and records the Armed Turret S1/S2 conflict; and
- keep procedural charts in the optional play-aid layer.

The Quick Reference Charts therefore serve their intended audit purpose: they
validate prior findings, expose a small number of missed cross-domain gaps, and
identify several places where InfinityDB's data-generated views can be more
maintainable and navigable than copied static charts.
