# Rules semantics audit

This document is the coverage ledger for InfinityDB's systematic audit of the
Infinity ruleset. The goal is not to reproduce the rules. The goal is to identify
source-authoritative semantics that improve data interpretation, normalization,
validation, relationships, querying, filtering, or presentation.

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
- [ ] Fireteams
- [ ] Command
- [ ] Movement
- [ ] Terrain and Scenery Structures
- [ ] Triumph and Defeat
- [ ] Setting up the Gaming Table
- [ ] Scenarios
- [ ] Quick Reference Charts
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
the page-191 Orders/AROs chart. The latter is used here only as a targeted
consistency check; the complete Quick Reference Charts section remains pending.

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
