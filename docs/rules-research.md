# Rules research

This document holds verified rules findings that may become useful to InfinityDB
but do not yet have a confirmed processing, validation, query, presentation, or
data-model consumer.

It is deliberately not a speculation backlog. Every entry needs an authoritative
source and a concise statement of what is known. Once an application becomes
clear, promote the finding to `rules-semantics.md` and create normal TODO/code
work only if implementation is actually required.

An entry here is not a promise that InfinityDB will eventually model the rule.
The ruleset is useful semantic evidence, while InfinityDB's product model remains
centered on catalogs, structure, relationships, querying, and presentation.
Procedural mechanics and edge cases may remain permanently as contextual
research, or be removed during later review when they do not materially help
those responsibilities. The official rules remain authoritative for exact rules
wording and game resolution.

## Entry contract

Record:

- a stable local finding ID;
- rules scope and canonical term(s);
- concise verified fact;
- wiki URL and reviewed version;
- PDF/FAQ/ITS citation when available;
- why the fact may matter later;
- what is still missing before it becomes implementation-relevant.

Keep unresolved interpretations explicitly unresolved. Do not use this file to
turn an inference into a source-native rule.

## Basic Rules / Unit Profile

### RR-BR-UP-001 — Troop Type carries specific rule restrictions

**Scope:** core N5.

The current Unit Profile wiki associates concrete restrictions with several
Troop Types: TAG and VH cannot go Prone or declare Cautious Movement, while REM
may not declare Cautious Movement or be chosen as Lieutenant.

The completed Quick Reference pass confirms the full current Restrictions Chart
and promotes the static cross-domain relationship pattern to `RS-QR-REST-001`.
This entry remains as the provenance trail for why Troop Type restrictions were
initially held back rather than inferred from the Unit Profile page alone.

Sources:

- Wiki: <https://infinitythewiki.com/Unit_Profile#Trooper_Characteristics>, live
  N5.3 page
- PDF: Infinity N5 V5.3, printed page 194, Restrictions Chart

### RR-BR-UP-002 — Game-term thesaurus can span domains without creating entities

**Scope:** project research derived from source-native terminology.

The Unit Profile page already exposes cross-domain terms such as Unit, Unit
Profile, Trooper, Attribute, Characteristic, Training, Troop Type, Trooper
Classification, ISC, Peripheral, and Controller. These terms can form the first
seed of a game-term thesaurus even when no dedicated database domain is warranted
for a term.

The completed Game States and Glossary audit established the broader canonical
vocabulary and relationship boundaries. Any future thesaurus should reuse those
audited semantics rather than introduce a second competing glossary structure.

Sources:

- Wiki: <https://infinitythewiki.com/Unit_Profile>
- PDF: Infinity N5 V5.3, printed pages 8-9

## Basic Rules / Broader research

### RR-BR-BASE-001 — Game Modes define finite recommended game presets

**Scope:** core N5.

The Basic Rules publish named Game Modes with recommended table size, Deployment
Zone, Army Points, SWC, and expected duration. The current N5.3 set is Beginner,
Raid, Intermediate, Standard, Magnum/Reinforcements, and Large-scale.

This may later support scenario/setup reference pages or saved-list defaults, but
InfinityDB currently does not model game setup as a domain. Do not promote these
presets into Army identity or list legality; missions, scenarios, events, and
player agreement can establish their own list size and setup.

Sources:

- Wiki: <https://infinitythewiki.com/Basic_Rules#Game_Modes>
- PDF: Infinity N5 V5.3, printed page 6

### RR-BR-AL-001 — Combat Groups are list/session structure

**Scope:** core N5.

An Army List assigns Troopers to Combat Groups, normally capped at ten members,
and each Combat Group has its own Order Pool. Peripherals do not consume a
separate Combat Group slot, and Marker contents may be Private while their Combat
Group membership remains Open.

This is likely relevant to a future list-builder or game-session model but does
not describe canonical Unit identity. Revisit it if InfinityDB begins storing
user-created Army Lists or per-game state.

Sources:

- Wiki: <https://infinitythewiki.com/Army_List#Combat_Group>
- PDF: Infinity N5 V5.3, printed page 10

### RR-BR-SEQ-001 — Initiative, Deployment, and Player Turn form a procedural ontology

**Scope:** core N5.

The rules distinguish Initiative, Deployment, Game Rounds, Player Turns, the
Active/Reactive Player roles, Tactical/Impetuous/Orders/States phases, and End of
Turn. Deployment also has explicit reserve-order steps and can be modified by
Skills or scenarios.

These terms are strong thesaurus candidates and would support a future play aid
or game-session model. They currently do not improve interpretation of static
Army source rows enough to justify a dedicated InfinityDB domain.

Sources:

- Wiki: <https://infinitythewiki.com/Initiative_and_Deployment>
- Wiki: <https://infinitythewiki.com/Game_Sequence>
- PDF: Infinity N5 V5.3, printed pages 15-17

### RR-BR-OES-001 — Order Expenditure defines declaration and validation timing

**Scope:** core N5.

The Order Expenditure Sequence separates activation, first Skill declaration,
ARO checks/declarations, second Skill declaration, Resolution, Effects, and
Conclusion. Most Requirements are checked during Resolution, while some movement
and reaction cases are checked at declaration; an invalid declaration can become
Idle under the sequence rules.

This is useful for a future interactive rules assistant or play aid, but it is
procedural game state rather than static Unit/Profile data. Preserve it as
research until a consumer needs rule-step validation.

Sources:

- Wiki: <https://infinitythewiki.com/Order_Expenditure_Sequence>
- PDF: Infinity N5 V5.3, printed page 14

### RR-BR-GEO-001 — LoF, ZoC, zones, and replacement rules form a spatial vocabulary

**Scope:** core N5.

Basic Rules define distinct spatial concepts for Line of Fire, Zone of Control,
Silhouette contact, being inside versus totally inside a zone, Coherency, and
replacing Models/Markers/Tokens with different game elements. These concepts use
Silhouette geometry and are referenced throughout later Skills, States,
Fireteams, and scenarios.

They should become thesaurus/reference relationships if InfinityDB adds spatial
rules help, scenario maps, or tabletop tools. The current database does not need
to encode live positions or derive LoF/ZoC from static profile data.

Sources:

- Wiki: <https://infinitythewiki.com/Line_of_Fire>
- Wiki: <https://infinitythewiki.com/Zone_of_Control>
- Wiki: <https://infinitythewiki.com/Zones,_Bases_and_Silhouettes>
- Wiki: <https://infinitythewiki.com/Replacing_Game_Elements>
- PDF: Infinity N5 V5.3, printed pages 18-22

### RR-BR-ROLL-001 — Roll resolution is reusable rules-reference material

**Scope:** core N5.

The rules define Normal and Face to Face Rolls, Success Value, the overall MOD
cap, Criticals, special handling for Success Values below 1 or above 20, and tie/
cancellation behavior for Face to Face Rolls. These procedures are broadly
reused by later combat, Hacking, Skill, and Equipment rules.

They are useful future glossary/play-aid material, but InfinityDB should not try
to precompute them from static profiles without an actual game-action context.
The modifier *notation* that affects interpretation of imported profile extras is
instead promoted to `rules-semantics.md`.

Sources:

- Wiki: <https://infinitythewiki.com/Rolls>
- Wiki: <https://infinitythewiki.com/Face_to_Face_Rolls>
- PDF: Infinity N5 V5.3, printed pages 23-26

## Game States and Glossary / State research

### RR-GSG-STATE-001 — State effects form several reusable semantic families

**Scope:** core N5.

The 23 current States are not one uniform mechanic. The audit exposes recurring
families that may be useful as the State catalog expands or for a future thesaurus:

- representation/hidden-information States: Camouflaged, Decoy, Hidden
  Deployment, Holoecho, HoloMask, Impersonation;
- control/Order/alignment States: Dead, Disconnected, Isolated, Possessed,
  Retreat!, Sepsitorized, Unconscious;
- action/Attribute/profile overlays: Engaged, Foxhole, Immobilized-A,
  Immobilized-B, Normal, Prone, Stunned, Suppressive Fire, Targeted;
- item-availability state: Unloaded.

These are research groupings, not source-native State categories. If the State
catalog exposes such groupings, mark them as InfinityDB classification metadata
and keep the canonical State identities/rules primary.

Sources:

- Wiki: <https://infinitythewiki.com/States> and its 23 linked State pages
- PDF: Infinity N5 V5.3, printed pages 157-172

### RR-GSG-STATE-002 — Marker and disguise States separate visible representation from real identity

**Scope:** core N5.

Camouflaged, Decoy, Hidden Deployment, Holoecho, HoloMask, and Impersonation all
show that what is visible on the table may intentionally not identify the real
Trooper/profile. HoloMask is especially explicit: a Trooper can present another
appearance while continuing to use its real Unit Profile, while Hidden Deployment
can represent the Trooper with no Model/Marker on the table at all.

This is likely useful for a future rules glossary, game-session model, or privacy-
aware list sharing, but it should not be projected back into canonical Unit
identity. A reference database should describe the State without attempting to
infer the current hidden identity of an actual game piece.

Sources:

- Wiki: <https://infinitythewiki.com/Camouflaged_State>
- Wiki: <https://infinitythewiki.com/Decoy_State>
- Wiki: <https://infinitythewiki.com/Hidden_Deployment_State>
- Wiki: <https://infinitythewiki.com/Holoecho_State>
- Wiki: <https://infinitythewiki.com/HoloMask_State>
- Wiki: <https://infinitythewiki.com/Impersonation_State>
- PDF: Infinity N5 V5.3, printed pages 157 and 159-167

### RR-GSG-STATE-003 — State transitions can propagate across relationships

**Scope:** core N5.

State changes can have effects on related game elements rather than only on the
state-bearing element. Isolated can cause a Peripheral to enter Disconnected when
either the Peripheral or its Controller becomes Isolated; deployment and
operating-distance rules can also leave a Peripheral Disconnected. Other States
interact with Fireteam membership, Combat Groups, Lieutenant status, and
Coordinated Orders.

A future game/session model may therefore need transition rules over relationship
edges, not just independent state flags on entities. This reinforces the value of
keeping Peripheral/controller and future Fireteam relationships explicit.

Sources:

- Wiki: <https://infinitythewiki.com/Isolated_State>
- Wiki: <https://infinitythewiki.com/Disconnected_State>
- PDF: Infinity N5 V5.3, printed pages 160 and 168

### RR-GSG-STATE-004 — State cancellation has typed recovery actors and conditions

**Scope:** core N5.

State cancellation is not one generic “clear status” operation. Examples include
Dodge for Immobilized-A, Reset for Immobilized-B/Isolated/Targeted, Doctor versus
Engineer depending on VITA/STR for Stunned/Unconscious recovery, Command Tokens
or Total Control for Possessed, and Reload/Baggage for Unloaded. Some State
cancellation also has scenario-specific routes or explicit exceptions.

This could support future contextual cross-links such as “ways to cancel this
State,” but should be curated from explicit rule relationships rather than
inferred from shared wording.

Sources:

- Wiki: <https://infinitythewiki.com/States> and affected State pages
- PDF: Infinity N5 V5.3, printed pages 164-172

## Game States and Glossary / Vocabulary research

### RR-GSG-TERM-001 — Terminology is a strong seed for the cross-domain game-terms thesaurus

**Scope:** project research grounded in source-native terminology.

The source Glossary supplies an initial cross-domain concept set whose members do
not belong naturally to one Army-data domain: Attributes, Deployable Equipment,
Deployable Weapon, Marker, Model, Peripheral, Scenery Element, State Token,
Target, Token, Trooper, Unit Profile, Victory Points, plus the Alignment terms.

A future thesaurus can use these as source-backed concepts and link them to
existing domains where applicable without creating dedicated database entities
for every term. The new scoped-concept requirement in `rules-semantics.md`
should be treated as part of that design.

Sources:

- Wiki: <https://infinitythewiki.com/Terminology>
- Wiki: <https://infinitythewiki.com/Alignment>
- PDF: Infinity N5 V5.3, printed page 173

### RR-GSG-TERM-002 — Targetability and ownership form separate semantic axes

**Scope:** core N5.

Terminology and Alignment show that “what this game element is,” “which side it
belongs to,” and “whether/how it can be targeted” are separate questions. A
Scenery Element may or may not become a target; Deployable Equipment/Weapons can
be targets; Hostile elements belong to no player's Army List but are treated as
Enemy; Neutral elements also belong to neither Army List without the Hostile
attack semantics.

This distinction may later help scenario/scenery modeling and rules-aware search,
but current canonical Army entities do not require an alignment/targetability
schema.

Sources:

- Wiki: <https://infinitythewiki.com/Terminology>
- Wiki: <https://infinitythewiki.com/Alignment>
- PDF: Infinity N5 V5.3, printed page 173

### RR-GSG-TRAIT-001 — Trait-to-State links can seed future cross-domain references

**Scope:** core N5.

Several Traits explicitly connect Weapon/Equipment profiles to other rules
concepts: `State` names a Game State caused by the item; `Suppressive Fire (SF)`
links to Suppressive Fire State; `Concealed` invokes Camouflaged State effects;
`Disposable (X)` leads to Unloaded State when uses are exhausted; and
`Non-Reloadable` changes Unloaded cancellation.

These are useful candidates for a relationship graph between Traits, States,
Weapons, Equipment, Skills, and Ammunition. The reviewed Concealed-to-Camouflaged-State
edge is materialized as `uses-effects-of`, and Disposable-to-Unloaded-State is materialized
as `causes-state`; the later domain audits should validate the remaining edge set before it
is materialized.

Sources:

- Wiki: <https://infinitythewiki.com/Traits>
- PDF: Infinity N5 V5.3, printed pages 174-175

## Skills and Equipment / Broader research

### RR-SE-RULE-001 — Rule composition needs precedence, not simple effect union

**Scope:** core N5.

The module explicitly permits Skills/Equipment effects to combine while also
stating that NFB incompatibility and the most restrictive applicable option take
precedence. Requirements and Restrictions can additionally invalidate an
otherwise available action.

A future rule-assistant or compatibility view will therefore need more than a
set of tags/effects. Composition has precedence and exclusion semantics. Keep
this as research until InfinityDB has a consumer that evaluates combinations in
an actual game context.

Sources:

- Wiki: <https://infinitythewiki.com/Skills_and_Equipment_Module>
- PDF: Infinity N5 V5.3, printed page 76

### RR-SE-PROFILE-001 — Runtime/profile overlays form a reusable relationship family

**Scope:** core N5.

Several rules alter which effective profile or characteristics apply without
creating a new canonical Unit identity. Examples include Transmutation, AI
Motorcycle, Infinity Spec-Ops Initial/Enhanced profiles, Morpho-Scan, and
random/table-driven changes from Booty or MetaChemistry.

These mechanisms do not all work alike, so `profile overlay` is an InfinityDB
research grouping rather than a source-native category. If future comparison or
game-session features need them, model the specific transition source, duration,
copied/replaced fields, and persistence rules rather than a generic mutable
profile blob.

Sources:

- Wiki: Transmutation, AI Motorcycle, Infinity Spec-Ops, Morpho-Scan, Booty, and
  MetaChemistry pages
- PDF: Infinity N5 V5.3, printed pages 86, 98-103, 117, and 119

### RR-SE-REL-001 — Skills can modify relationships and group behavior

**Scope:** core N5.

FT Master, Strategic Deployment, TAGCom, G: Jumper, Peripheral, and similar
Special Skills show that Skill effects may be properties of relationships or
groups rather than only of the bearer. Examples affect Fireteam Training,
deployment of associated Troopers, Pilot/TAG relationships, Proxy activation,
Controller/Peripheral activation, or Combat Group counting.

This supports treating future relationship rules as first-class cited semantics
instead of materializing their effects into unrelated canonical Unit fields.
The detailed Fireteam and Command consequences remain deferred to their own
section audits.

Sources:

- Wiki: relevant Special Skill pages under the Skills and Equipment module
- PDF: Infinity N5 V5.3, printed pages 93-94, 106-109, and 112-115

### RR-SE-HACK-001 — Equipment/Skill identities seed a Hacking relationship graph

**Scope:** core N5; detailed semantics reconciled by the Combat audit.

Hacker, Hacking Device variants, Firewall, Repeater, TinBot, and related
Equipment establish cross-links between Troopers, devices, programs, Hacking
Area, MODs, and defensive effects. The Skills and Equipment chapter establishes
that those identities are related; the completed Combat audit records the actual
program/target/range semantics and implementation-relevant boundaries.

The original warning still applies: do not infer a complete Hacking graph from
Equipment names/source links alone. Use the reviewed Combat findings and future
curated relationships instead.

Sources:

- Wiki: <https://infinitythewiki.com/Hacking_Device>
- Wiki: Firewall, Repeater, TinBot, and Hacker pages
- PDF: Infinity N5 V5.3, printed pages 95 and 122-127

### RR-SE-REINF-001 — Live Special Skills navigation includes annex-scoped rules

**Scope:** Reinforcements annex, not core N5 Skills and Equipment.

The live Special Skills navigation lists `Commlink` and `Request Reinforcements`,
while the core N5 V5.3 Skills and Equipment PDF inventory does not. Those links
resolve into the Reinforcements rules.

This is a useful audit warning for future automated wiki discovery: page
navigation/parentage is not enough to assign rules scope. Preserve the explicit
annex source and defer the detailed rules semantics to the Reinforcements audit.

Sources:

- Wiki: live Special Skills navigation
- Wiki: Commlink and Request Reinforcements pages
- PDF: Infinity N5 V5.3, printed pages 75-127 (core inventory)

### RR-SE-COMMON-001 — Common Skills are rules-reference entities without Army occurrences

**Scope:** core N5.

Common Skills are available to every Trooper by the rules, so their usefulness to
InfinityDB does not depend on appearing as Army metadata records. They can still
be targets of Traits, declaration-category help, cross-links, and play-aid
content.

The rules-backed Skills catalog now carries all 18 core Common Skill identities
whether or not they have Army occurrences, and presents them above Special Skills.
This keeps rules identity separate from Army-profile occurrence and leaves distinct
Scenario Skills and ITS Scenario Skills categories available for later scoped work.

Sources:

- Wiki: Common Skills index under the Skills and Equipment module
- PDF: Infinity N5 V5.3, printed pages 76-85

## Combat Module / Broader research

### RR-CM-RES-001 — Guts and post-hit resolution are runtime procedure

**Scope:** core N5.

Wounds, Unconsciousness/Death, Guts Rolls, cover-seeking movement, and related
post-Attack consequences form a runtime resolution sequence. Static profiles can
provide VITA/STR and Skills that modify that procedure, but they do not describe
the Trooper's current Wounds, failed Saving Rolls, or Guts outcome.

This is useful future play-aid/reference material and should remain outside the
replaceable canonical Army snapshot unless a separate game-session model is
introduced.

Sources:

- Wiki: Wounds and Guts Roll pages under Combat Module
- PDF: Infinity N5 V5.3, printed pages 37-38

### RR-CM-TPL-001 — Template placement forms a reusable spatial-rules vocabulary

**Scope:** core N5.

Template attacks introduce Main Target, Area of Effect, Blast Focus, Circular/
Small Teardrop/Large Teardrop templates, Direct versus Impact placement, Total
Cover interactions, and secondary affected game elements.

These are strong thesaurus/reference concepts for a future tabletop/scenario
helper, but InfinityDB currently has no live geometry model. Record the concepts
without trying to compute template coverage from static Unit data.

Sources:

- Wiki: <https://infinitythewiki.com/Template_Weapons_and_Equipment>
- PDF: Infinity N5 V5.3, printed pages 43-50

### RR-CM-CC-001 — Engaged groups create situational combat relationships

**Scope:** core N5.

Close Combat can restrict what nearby Troopers may declare, change Burst through
allied participants, and interact with BS Attacks into the engagement. The
participants and eligible bonuses depend on current Silhouette contact, States,
and declarations.

A future game/session layer could represent an engagement graph, but canonical
Unit/Peripheral relationships alone are insufficient to determine it.

Sources:

- Wiki: <https://infinitythewiki.com/Close_Combat>
- PDF: Infinity N5 V5.3, printed pages 51-53

### RR-CM-HACK-001 — Supportware is a sustained runtime relationship

**Scope:** core N5.

Supportware Programs can apply continuing effects to Allied Troopers. A target
can benefit from only one Supportware Program at a time, each Hacker can sustain
only one, and later Programs or specific Hacker States can cancel the existing
relationship.

This is a useful reusable rules relationship but not a static Equipment fact. It
should become a rules-reference relationship before any future session layer
tries to track active Supportware.

Sources:

- Wiki: <https://infinitythewiki.com/Quantronic_Combat_%28Hacking%29>
- PDF: Infinity N5 V5.3, printed pages 54-55

### RR-CM-HACK-002 — Core Hacking Programs form a finite cross-domain vocabulary

**Scope:** core N5.

N5 V5.3 defines twelve core Programs: Assisted Fire, Carbonite, Controlled Jump,
Cybermask, Enhanced Reaction, Fairy Dust, Oblivion, Spotlight, Total Control,
Trinity, White Noise, and Zero Pain. Their effects connect to Troop Types,
Attributes, Ammunition, States, Labels, deployment, visibility, and Equipment.

The set is a strong candidate for the cross-domain rules thesaurus and a future
first-class Hacking Program catalog. Exact Device grants and Upgrade Programs
should be represented as cited relationships rather than embedded in prose.

Sources:

- Wiki: <https://infinitythewiki.com/Hacking_Programs_Chart>
- PDF: Infinity N5 V5.3, printed pages 57-62

### RR-CM-ACT-001 — Combat resolution exposes a reusable action ontology

**Scope:** core N5.

Attack declaration, Burst allocation, target selection, Range/Cover/other MODs,
Normal or Face-to-Face Roll, Saving Roll, Wounds/States, and post-hit effects form
a reusable procedural graph shared by BS, CC, and Hacking with domain-specific
branches.

This could support future rule-navigation or play-aid features, but it is not a
reason to encode executable game simulation into the current reference database.
Keep the concepts and relationships source-backed and consumer-driven.

Sources:

- Wiki: <https://infinitythewiki.com/Combat_Module>
- PDF: Infinity N5 V5.3, printed pages 36-62

## Ammunition and Weaponry / Broader research

### RR-AW-ZONE-001 — Smoke and Eclipse create transient visibility zones

**Scope:** core N5.

Smoke and Eclipse are Ammunition whose principal effect is to create a Zero
Visibility Zone rather than resolve ordinary Wounds. Eclipse additionally has
the Reflective interaction that blocks vision systems which can otherwise see
through Smoke.

The placement, duration, overlap, and Line-of-Fire consequences depend on the
current table state. These are useful future play-aid/spatial-reference concepts
but should not be materialized as static properties of a Unit carrying a Smoke
or Eclipse Weapon.

Sources:

- Wiki: <https://infinitythewiki.com/Smoke_Ammunition>
- Wiki: <https://infinitythewiki.com/Eclipse_Ammunition>
- PDF: Infinity N5 V5.3, printed pages 64 and 66

### RR-AW-DEP-001 — Perimeter/Mine activation is runtime spatial behavior

**Scope:** core N5.

Perimeter Weapons and Mines monitor a Trigger Area and can react to Enemy
activity according to current position, visibility/valid-target rules, States,
and declarations. The Weapon/Equipment identity and deployment profile are
reference data; whether it triggers or Boosts is game-session state.

A future tabletop helper could model this event/spatial relationship, but the
canonical Army snapshot should not attempt to infer active trigger areas.

Sources:

- Wiki: <https://infinitythewiki.com/Perimeter_Weapons>
- Wiki: <https://infinitythewiki.com/Mines>
- PDF: Infinity N5 V5.3, printed pages 69 and 72

### RR-AW-SYMBIO-001 — SymbioBomb separates owner, assigned user, and use-time effect

**Scope:** core N5.

A Unit Profile can list a SymbioBomb on its owner, while Deployment assigns the
single-use item to another eligible same-army Trooper who becomes its user.
During play that user can invoke one of the permitted Pheroware Tactics, after
which the SymbioBomb is removed.

This is a strong future example for a session/list relationship layer:
catalog/loadout ownership is static source data, assignment is deployment state,
and the selected use is action state. Those identities/scopes should not be
collapsed into one permanent Unit relationship.

Sources:

- Wiki: <https://infinitythewiki.com/SymbioBomb>
- PDF: Infinity N5 V5.3, printed page 74

### RR-AW-SCENERY-001 — Anti-materiel effects connect Weapon rules to scenery

**Scope:** core N5.

D-Charges and other Anti-materiel Weapons can interact with scenery/structures
through rules that are not ordinary Trooper damage resolution. This creates a
cross-domain relationship between Weapon/Ammunition/Traits and the later
Terrain/Scenery Structure rules.

Retain the relationship as a thesaurus/research edge until the Terrain and
Scenery Structures audit establishes the authoritative target/object vocabulary.

Sources:

- Wiki: <https://infinitythewiki.com/D-Charges>
- Wiki: <https://infinitythewiki.com/Traits#Anti-materiel>
- PDF: Infinity N5 V5.3, printed page 70

### RR-AW-OBJECT-001 — Delivery and deployed-object lifecycle is a reusable ontology

**Scope:** core N5.

Pitchers, Mine Dispensers, Drop Bears, Disco Ballers, WildParrots, and similar
rules distinguish the carried/delivery item, the placement action, the deployed
game element, its table representation, and later activation/removal. Different
rules use different subsets of that lifecycle.

This vocabulary is likely useful for a future game-term thesaurus and tabletop
helper. The implementation-relevant source/profile boundaries are recorded in
`rules-semantics.md`; exact placement/trigger/removal procedures remain
research-only until a consumer needs them.

Sources:

- Wiki: Ammunition and Weaponry named weapon pages
- PDF: Infinity N5 V5.3, printed pages 69-74

## Fireteams

### RR-FT-RUNTIME-001 — Fireteam activation and integrity are runtime procedures

**Scope:** core N5.

Fireteam Leader selection, Coherency checks, Active-Turn shared activation,
Reactive-Turn ARO coordination, member departure/rejoining, cancellation, and
bonus recalculation all depend on current game actions and state.

These rules explain why static chart eligibility must not be interpreted as
current membership or guaranteed bonuses. Beyond that boundary, InfinityDB does
not presently need to model the Fireteam procedure/state machine. Keep the
details as reference context unless a future game-session or play-aid consumer
requires them.

Sources:

- Wiki: <https://infinitythewiki.com/Fireteam_Integrity>
- Wiki: <https://infinitythewiki.com/Fireteams_in_the_Active_Turn>
- Wiki: <https://infinitythewiki.com/Fireteams_in_the_Reactive_Turn>
- PDF: Infinity N5 V5.3, printed pages 134-136

### RR-FT-INFO-001 — Fireteam bonuses have game-time disclosure semantics

**Scope:** core N5.

The rules treat a Fireteam's bonuses as Private Information until a Skill that
benefits from them is declared. This is disclosure state during a match, not a
reason for InfinityDB to hide the public rules describing Fireteam Level or the
Army chart itself.

Revisit the distinction only if InfinityDB gains privacy-aware saved-list or
game-session features.

Sources:

- Wiki: <https://infinitythewiki.com/Fireteam_Bonuses>
- Wiki: <https://infinitythewiki.com/Open_and_Private_Information>
- PDF: Infinity N5 V5.3, printed page 136

### RR-FT-TERM-001 — `Linkable` is historical official terminology and modern shorthand

**Scope:** terminology provenance; historical N3 plus current community usage.

`Linkable` was not merely fan terminology: official Human Sphere N3 profile
material used `Linkable` as a descriptor for Troopers participating in
Fireteams. Current N5 instead expresses eligibility through the Army Fireteams
Chart, with Fireteam-specific membership, FTO restrictions, Wildcards,
min/max/required conditions, and notes.

The word remains common and useful shorthand in player discussion, but
InfinityDB should not reintroduce it as a simple current-rule boolean. A
thesaurus/search layer can map `linkable` to current Fireteam-chart eligibility
while labeling the term's historical provenance.

Sources:

- Historical official PDF: Infinity Human Sphere N3, e.g.
  <https://assets.infinitythegame.net/downloads/hsn3rules/en/v3.2/hsn3rules.pdf>
  (`Linkable` in Unit/Profile material)
- Current rules: <https://infinitythewiki.com/Fireteams_Chart>

### RR-FT-TERM-002 — `pure Fireteam` is community shorthand rooted in N4 Composition Bonuses

**Scope:** terminology provenance; N4/community usage versus current N5.

N4 officially distinguished Fireteam Size Bonuses from **Fireteam Composition
Bonuses**, with the latter requiring a Fireteam made only from the same Unit
and/or chart entries identified as such. Contemporary player discourse widely
called a Fireteam satisfying that composition condition a **pure Fireteam**.

No current N5 rule term `pure Fireteam` was found in this audit. N5.3 instead
uses a single **Fireteam Level** that increases with the number of same-Unit /
bracket-equivalent members, so the old pure/impure binary is not a faithful
current model.

InfinityDB should retain `pure Fireteam` as a provenance-aware community alias
for search/help and explain its relationship to historical Composition Bonuses
and current Fireteam Level. It should not expose `Pure` as a current Fireteam
Type or authoritative boolean.

Sources:

- Historical official N4 Fireteams Annex:
  <https://downloads.corvusbelli.com/infinity/rules/rules-annex-eng.pdf>
  (`Fireteam Composition Bonuses`)
- Current N5: <https://infinitythewiki.com/Fireteam_Bonuses>
- Community provenance example: Corvus Belli forum archived N4 discussion,
  `Ridiculous Discovery Bonus for Pure Fireteams` (2022)

### RR-FT-TYPE-001 — Fireteam creation sizes are useful reference vocabulary, not identity derivation

**Scope:** core N5.

The general rules define Duo, Haris, and Core creation sizes, while individual
Army/Sectorial charts can modify Fireteam creation conditions and determine
which Types a named Fireteam supports.

Those defaults are useful glossary/help material. InfinityDB should nevertheless
take Type eligibility from the imported Army chart and retain the FAQ distinction
between Type and later member count, rather than deriving Type from count.

Sources:

- Wiki: <https://infinitythewiki.com/Fireteams:_Basic_Rules>
- Wiki: <https://infinitythewiki.com/Fireteams_Chart>
- PDF: Infinity N5 V5.3, printed pages 132-133

## Command

### RR-CMD-TOK-001 — Command Token use procedures are session/play-aid material

**Scope:** core N5.

Strategic, Executive, and Operational Use define a broad set of match-time
actions involving deployment, Order Pool disruption, Suppressive Fire,
Speedballs, Combat Group reassignment, Possessed cancellation, Guts Rolls,
Irregular-to-Regular Order conversion, Retreat!, Doctor/Engineer rerolls, and
Fireteam creation.

Those relationships are useful for navigation and concise contextual help, but
the exact timing, expenditure limits, current token balance, valid target, and
result belong to the state of a particular match. InfinityDB does not need a
Command Token execution engine to present the Units, Skills, States, Fireteams,
and other catalog concepts involved.

Sources:

- Wiki: <https://infinitythewiki.com/Command_Tokens>
- PDF: Infinity N5 V5.3, printed pages 128-129

### RR-CMD-CO-001 — Spearhead and Coordinated resolution are transient action roles

**Scope:** core N5.

A Coordinated Order creates temporary action-local structure: participating
Troopers, one Spearhead, a shared Skill sequence, target constraints, modified
Burst, restricted enemy reactions, and special handling for CC, States, Hacking,
Targetless/Deployable items, and failed participant Requirements. The Spearhead
Token is removed when the Order ends.

`Spearhead` is therefore useful thesaurus/reference vocabulary, but it is not a
Unit characteristic or persistent relationship. Detailed Coordinated Order
resolution should remain procedural research unless InfinityDB later gains an
explicit play-aid/session consumer.

Sources:

- Wiki: <https://infinitythewiki.com/Coordinated_Orders>
- PDF: Infinity N5 V5.3, printed pages 129-131

### RR-CMD-TERM-001 — Command use-mode terms are useful scoped glossary vocabulary

**Scope:** core N5 terminology.

`Strategic Use`, `Executive Use`, and `Operational Use` are named scopes for
spending Command Tokens. They are useful glossary/thesaurus terms because player
discussion and related Skills can reference one use mode specifically
(Counterintelligence, for example, targets Strategic Use).

A future thesaurus should link these terms beneath Command Token rather than
treat them as three token types or new application domains.

Sources:

- Wiki: <https://infinitythewiki.com/Command_Tokens>
- Wiki: <https://infinitythewiki.com/Counterintelligence>
- PDF: Infinity N5 V5.3, printed pages 90 and 128-129

## Movement

### RR-MOV-ROUTE-001 — Movement routes are action-local geometry

**Scope:** core N5.

The Movement rules require an exact route and final location, and LoF/ARO
interactions can depend on intermediate points along that route rather than only
on the starting and ending positions. General Movement also applies rules for
vaulting, base support, Silhouette contact, facing, and safe final placement.

These concepts are useful glossary/play-aid context but are not stable Unit or
profile relationships. InfinityDB does not need board coordinates, paths, or a
movement resolver to explain the static MOV Attribute and movement-related
Skills.

Sources:

- Wiki: <https://infinitythewiki.com/Moving_and_Measuring>
- Wiki: <https://infinitythewiki.com/General_Movement_Rules>
- PDF: Infinity N5 V5.3, printed pages 27-31

### RR-MOV-CAUT-001 — Cautious Movement is contextual ARO suppression, not static eligibility

**Scope:** core N5.

Cautious Movement avoids enemy AROs only when its current-position conditions
are satisfied. Its restrictions and checks reference LoF, ZoC, Hacking Area,
Hackable, several Troop Types, Motorcycle/Aerial, Targeted State, and Hidden
Deployment representation.

Those cross-links may be useful for rule help, but they should not be condensed
into a permanent `can_cautious_move` Unit flag. Actual availability depends on
current representation, State, enemies, and board position.

Sources:

- Wiki: <https://infinitythewiki.com/Cautious_Movement>
- PDF: Infinity N5 V5.3, printed pages 32-33

### RR-MOV-SURFACE-001 — Surface/scenery semantics belong with tabletop context

**Scope:** core N5 with a future Terrain/Scenery cross-section dependency.

Movement distinguishes ordinary surfaces, vertical surfaces, stairs/ladders,
vaultable obstacles, valid landing surfaces, and Silhouette-dependent height.
Stairs and ladders can make vertical/diagonal scenery behave as a horizontal
surface for Skills with the Movement Label, while Climb and Jump impose their
own surface and trajectory rules.

This vocabulary may later support terrain/scenery reference pages, but the
Movement audit does not make scenery geometry part of canonical Unit data. The
next Terrain and Scenery Structures pass should reuse these relationships rather
than introduce a separate movement-geometry model.

Sources:

- Wiki: <https://infinitythewiki.com/Moving_and_Measuring>
- Wiki: <https://infinitythewiki.com/General_Movement_Rules>
- Wiki: <https://infinitythewiki.com/Climb>
- Wiki: <https://infinitythewiki.com/Jump>
- PDF: Infinity N5 V5.3, printed pages 27-35

## Terrain and Scenery Structures

### RR-TS-DIFF-001 — Difficult Terrain is runtime movement context

**Scope:** core N5.

Difficult Terrain affects a movement action when the Trooper enters or is in
contact with the area. It can stop the current movement and impose a reduction
on subsequent movement through the area. The Terrain Special Skill and some
Equipment can alter whether those restrictions apply.

This is useful explanatory context for MOV and Terrain-related catalog entries,
but it should not be projected into a terrain-adjusted canonical MOV Attribute.
The applied value depends on current table position, selected terrain, Skill, and
Order.

Sources:

- Wiki: <https://infinitythewiki.com/Difficult_Terrain>
- Wiki: <https://infinitythewiki.com/Terrain>
- PDF: Infinity N5 V5.3, printed pages 116 and 144

### RR-TS-SAT-001 — Saturation is contextual Burst modification

**Scope:** core N5.

A Saturation Zone modifies Burst for a BS Attack that originates in, enters, or
passes through the zone. Its rules include timing relative to Burst allocation,
a floor, and non-stacking behavior between multiple Saturation Zones.

Those details are action-resolution context rather than a Weapon-profile
property. A reference view may explain that a Weapon's printed Burst can be
modified by Saturation without storing a second canonical Burst value.

Sources:

- Wiki: <https://infinitythewiki.com/Saturation>
- PDF: Infinity N5 V5.3, printed page 144

### RR-TS-ACCESS-001 — Access Width is scenery geometry, not static Trooper eligibility

**Scope:** core N5.

Scenery can have Narrow or Wide Access Widths. Whether a Trooper can pass a
Narrow access depends on the Silhouette used for that check, with an explicit
exception that Prone/SX uses the Silhouette value printed on the Unit Profile.

The terms are useful for a glossary or table/scenario reference, but InfinityDB
should not derive a permanent `can pass narrow access` property because current
State, scenery, and scenario rules participate in the decision.

Sources:

- Wiki: <https://infinitythewiki.com/Scenery_Structures>
- PDF: Infinity N5 V5.3, printed page 145

### RR-TS-TERM-001 — Difficult Movement is a historical/current-search alias for Difficult Terrain

**Scope:** N5 terminology history.

The N5.3 Terrain and Scenery Structures update replaces the parent-section term
`Difficult Movement` with `Difficult Terrain`. Older N5 material and community
discussion may therefore still use the former term for the same terrain
characteristic.

A future thesaurus/search layer should retain `Difficult Movement` as
historical terminology while presenting `Difficult Terrain` as the current N5.3
canonical term. This is provenance/search metadata, not a second rules concept.

Sources:

- Wiki: <https://infinitythewiki.com/Terrain_and_Scenery_Structures>, N5.3
  update annotation
- PDF: Infinity N5 V5.3, printed pages 143-144

## Triumph and Defeat

### RR-TD-STD-001 — Standard Game and Retreat! end conditions are play/session procedure

**Scope:** core N5.

A Standard Game normally lasts three Game Rounds and compares Victory Points at
the end. Retreat! adds additional end-game behavior and modifies the current
Player Turn while the army remains in that situation.

These procedures are useful for concise glossary/play-aid context, but
InfinityDB does not need to execute the end-game sequence to present Units,
Costs, States, or scenario references. The semantic distinctions that matter to
the data model—Victory Points, Null State, Retreat! situation, and Retreat!
State—are recorded separately in `rules-semantics.md`.

Sources:

- Wiki: <https://infinitythewiki.com/Triumph_and_Defeat_Module>
- PDF: Infinity N5 V5.3, printed page 146

### RR-TD-MODE-001 — Mission, scenario, and Free Game are session/setup vocabulary

**Scope:** core N5.

The rules use mission/scenario for games whose defined objectives award
Objective Points, while a Free Game is a game whose participants agree to
change one or more recommended Game Mode parameters.

These are strong thesaurus and future scenario/setup-reference terms, but they
do not imply that InfinityDB needs a complete game-session schema. Existing
planned scenario and ITS reference work can use the vocabulary if it improves
discovery or explanation.

Sources:

- Wiki: <https://infinitythewiki.com/Triumph_and_Defeat_Module>
- PDF: Infinity N5 V5.3, printed page 147

## Setting up the Gaming Table

### RR-TABLE-LAYOUT-001 — Terrain balance and accessibility are advisory design guidance

**Scope:** core N5 setup guidance.

The rules recommend arranging enough Cover to permit maneuver without eliminating
the value of long-range weapons, using large and small scenery to create useful
routes, keeping elevated areas reasonably accessible, and avoiding excessive
bottlenecks or blind alleys. They also suggest a less-than-10-inch spacing
between large terrain pieces as part of one example layout approach.

The section explicitly says this guidance is not mandatory. These ideas may be
useful in a future setup aid, but InfinityDB should not convert them into hard
validation thresholds or claim that a table is rules-valid/invalid based on
terrain density, sight lines, accessibility, or spacing.

Sources:

- Wiki: <https://infinitythewiki.com/Setting_up_the_Gaming_Table>
- PDF: Infinity N5 V5.3, printed pages 147-148

### RR-TABLE-SYM-001 — Deployment Zone symmetry describes terrain layout, not zone dimensions

**Scope:** core N5 setup vocabulary.

The rules distinguish symmetrical and asymmetrical Deployment Zones by whether
the terrain amount, size, and arrangement are comparable on both sides. An
asymmetrical zone may deliberately provide more Cover and/or higher terrain and
therefore a tactical advantage to the player who chooses that side.

This is useful glossary/map terminology for a future scenario or table reference.
It should not be conflated with the numeric dimensions of a Deployment Zone or
turned into an Army/Unit property. If represented later, terrain symmetry should
remain metadata about a specific table/layout.

Sources:

- Wiki: <https://infinitythewiki.com/Setting_up_the_Gaming_Table#Symmetrical_and_Asymmetrical_Deployment_Zones>
- PDF: Infinity N5 V5.3, printed page 148

## Scenarios

### RR-SCN-LIB-001 — The core rulebook scenarios are an introductory sample

**Scope:** core N5 source scope and future product planning.

The Scenarios overview describes the four included missions as a small set used
to introduce scenario play and points to additional official content elsewhere.
The core rulebook section is therefore not an authoritative inventory of all
Infinity scenarios.

A future scenario library can combine explicitly versioned core and seasonal
sources, but completing that library is not required for InfinityDB 1.0. The
current audit uses the four core scenarios primarily to discover scoped catalog
concepts and cross-domain relationships.

Sources:

- Wiki: <https://infinitythewiki.com/Scenarios>
- PDF: Infinity N5 V5.3, printed pages 149-156

### RR-SCN-RUNTIME-001 — Mission scoring and objective resolution are session procedure

**Scope:** core N5 scenario procedure.

Annihilation's Killed scoring, Domination's quadrant control, Supplies' end-game
Supply Box control, minimum-Victory-Point end conditions, and similar mission
procedures depend on the selected scenario plus current table/State/session
facts.

These mechanics may be useful later for scenario detail pages or play aids, but
they do not need to become a rules engine to support the 1.0 catalog/reference
scope. The named Skills, contextual roles, and cross-domain concepts those
procedures introduce can be curated independently.

Sources:

- Wiki: <https://infinitythewiki.com/Annihilation>
- Wiki: <https://infinitythewiki.com/Domination>
- Wiki: <https://infinitythewiki.com/Supplies>
- Wiki: <https://infinitythewiki.com/Firefight>
- PDF: Infinity N5 V5.3, printed pages 149-156

## Quick Reference Charts

### RR-QR-PROC-001 — Procedure charts are presentation aids, not additional state models

**Scope:** core N5 procedure/reference presentation.

Game Sequence, Order Expenditure, Impetuous activation, Retreat!/Loss of
Lieutenant summaries, and Fireteam bonus summaries compress procedures already
defined by their owning rules. Their chart form does not create new canonical
Unit/Profile facts or justify a parallel game-state engine.

These are good candidates for optional generated/cited play aids where they help
users navigate the rules, but the underlying facts should continue to live with
their owning semantic concepts.

Sources:

- PDF: Infinity N5 V5.3, printed pages 189-195
- Wiki: <https://infinitythewiki.com/Quick_Reference_Charts>

### RR-QR-RANDOM-001 — Random lookup results are structured overlays, not imported profile mutations

**Scope:** core N5 Skill lookup semantics.

Booty and MetaChemistry result tables are particularly well suited to generated
reference because Army metadata already carries their roll ranges and result
text. Some results grant catalog items, some replace Attributes, and some branch
on predicates such as TAG versus other Troop Types.

A future structured parser/cross-link layer could make those outcomes navigable,
but it should preserve the original result and condition and must not infer that
a Unit permanently possesses a randomly available result. This refines the
`profile overlay` research grouping in `RR-SE-PROFILE-001`.

Sources:

- Wiki: <https://infinitythewiki.com/Booty_Chart>
- Wiki: <https://infinitythewiki.com/MetaChemistry_Chart>
- PDF: Infinity N5 V5.3, printed page 192

### RR-QR-TRANS-001 — Translation charts are alias/localization evidence, not separate rule identities

**Scope:** current wiki reference tooling and future localization/search.

The live Quick Reference navigation includes Translation Charts. Their useful
architectural lesson is that localized names should resolve to the same scoped
semantic identity rather than create language-specific duplicate rules.

InfinityDB does not currently need a translation-chart product. Retain this as
research for a future multilingual thesaurus/search layer, where canonical
identity, language-specific display labels, historical aliases, and community
terms can remain distinct provenance dimensions.

Source:

- Wiki: <https://infinitythewiki.com/Quick_Reference_Charts>

### RR-QR-CONFLICT-001 — Summary charts can conflict with owning rules

**Scope:** source-quality and precedence research.

The V5.3 Quick Reference Deployable Profiles summary lists Armed Turret as S1,
while the detailed Armed Turret profile on printed page 70 and the current wiki
list S2. This is a concrete example of why Quick Reference must remain a
validation source rather than automatically override the owning rule.

Until Corvus Belli publishes a clarification/erratum or InfinityDB adopts a
reviewed source-precedence resolution for this exact conflict, preserve both
observations and present the detailed-rule S2 value currently used by the
curated Armed Turret record with provenance.

Sources:

- Wiki: <https://infinitythewiki.com/Armed_Turret>
- PDF: Infinity N5 V5.3, printed pages 70 and 195

## Reinforcements

### RR-RF-LIST-001 — Reinforcement point/SWC splits and list-size limits are list-building procedure

**Scope:** Reinforcements annex list construction.

The Extra reserves 100 Army Points and 2 SWC for the Reinforcement Section,
requires one Commlink Trooper in the Main Section, and counts Reinforcement
Troopers toward the normal 15-Trooper Army List maximum (subject to explicit
maximum-count bonuses such as `Commlink (+X)`). Its recommended 350-point game
therefore uses a 250/5 Main Section plus a 100/2 Reinforcement Section.

These constraints may matter to a future saved-list/list-validator feature, but
they are not canonical properties of a Unit, Army identity, or Reinforcement
pool. The current catalog/reference application only needs the section/parent and
Skill/parameter semantics recorded in `rules-semantics.md`.

Sources:

- Wiki: <https://infinitythewiki.com/index.php?title=Infinity_Reinforcements&oldid=3614>
- Official annex: <https://downloads.corvusbelli.com/infinity/rules/reinforcement-rules-en.pdf>

### RR-RF-DEP-001 — Request thresholds and DropPod deployment are runtime procedure

**Scope:** Reinforcements annex session/deployment behavior.

The Request Reinforcements step compares current Victory Points against a game-
size threshold (or becomes available in the third Game Round), then places a
DropPod Token and deploys the entire Reinforcement Section, Peripherals, and
Deployable Weapons/Equipment within the resulting deployment area subject to
current table/scenario restrictions.

This is potentially useful play-aid material but does not justify static Unit
fields or a Reinforcements state engine. The DropPod is a deployment Token/
scenery representation for the procedure, not Trooper Equipment to add to the
Equipment catalog.

Source:

- Wiki: <https://infinitythewiki.com/index.php?title=Infinity_Reinforcements&oldid=3614>

### RR-RF-CG-001 — Reinforcement Combat Group transfers are session state

**Scope:** Reinforcements annex Combat Group procedure.

Once deployed, Reinforcement Troopers form separate Combat Group(s), cannot move
into or out of those groups until the following Tactical Phase, and the Commlink
Trooper receives a special one-time transfer option when the Section deploys.

These facts explain why the Reinforcement Section is more than a second static
roster, but Combat Group membership and transfer timing remain live list/session
state. No canonical Unit/Profile relationship is required for current
InfinityDB catalog/reference responsibilities.

Source:

- Wiki: <https://infinitythewiki.com/index.php?title=Infinity_Reinforcements&oldid=3614>

## Baggage and Reload

### RR-BR-RELOAD-001 — N5.3 disagrees on which Trooper must be non-Null

**Scope:** core N5.3 Baggage / Reload interaction.

The current Baggage rule requires the *affected Allied Trooper* to be in a
non-Null State, while the current Reload rule requires the Allied Trooper or
game element *with Baggage* to be in a non-Null State. These are not equivalent
requirements. InfinityDB therefore preserves each rule's own source wording and
does not infer a shared prerequisite or choose one formulation as authoritative.

An official clarification or later rules revision is required before this can be
promoted to a normalized cross-rule semantic relationship.

Sources:

- Wiki: <https://infinitythewiki.com/Baggage>, live N5.3 page, reviewed 2026-09-23
- Wiki: <https://infinitythewiki.com/Reload>, live N5.3 page, reviewed 2026-09-23

## ITS FAQ

### RR-FAQ-RUNTIME-001 — Card use, timing, and tracking remain session procedure

**Scope:** ITS scenario runtime behavior.

The Akial Interference FAQ answers when an Emit Akial Interference card becomes
used, excludes Predator Kills that happened before the objective was drawn, and
allows players to track used cards by any convenient method.

Those rulings are important when explaining or adjudicating the scenario, but
they describe mutable match state and player procedure. Beyond cataloging the
scoped Skill/action identities and FAQ links needed by the general reference,
InfinityDB does not need persistent Unit/Profile fields or a card-state engine
for 1.0.

Sources:

- Wiki: <https://infinitythewiki.com/ITS_FAQ>
- Official FAQ v0.0 PDF, printed page 3:
  <https://downloads.corvusbelli.com/infinity/rules/infinity-faq-n5-en-v5.0.0.pdf>

### RR-FAQ-SPATIAL-001 — ITS movement/deployment clarifications depend on live table context

**Scope:** ITS scenario spatial procedure.

Neutral HVT movement blocking and Crossing Lines' nearest-enemy-Deployment-Zone
rule are resolved from the current table state; the Crossing Lines
Netrod/Imetron ruling is a scenario-local exception to that mission's deployment
rule. They may support contextual help or future play aids, but they do not
justify static Unit eligibility or geometry fields in the catalog model.

Source:

- Wiki: <https://infinitythewiki.com/ITS_FAQ>
