# Rules research

This document holds verified rules findings that may become useful to InfinityDB
but do not yet have a confirmed processing, validation, query, presentation, or
data-model consumer.

It is deliberately not a speculation backlog. Every entry needs an authoritative
source and a concise statement of what is known. Once an application becomes
clear, promote the finding to `rules-semantics.md` and create normal TODO/code
work only if implementation is actually required.

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

This may eventually support contextual help, rule-aware filtering, or validation
of derived rule relationships. InfinityDB does not currently need these
restrictions to interpret the imported `type` field, so they remain research-only
until the Restrictions Chart and the affected rules are audited as a complete
set.

Source:

- Wiki: <https://infinitythewiki.com/Unit_Profile#Trooper_Characteristics>, live
  N5.3 page
- PDF cross-check: pending the Quick Reference / Restrictions Chart audit

### RR-BR-UP-002 — Game-term thesaurus can span domains without creating entities

**Scope:** project research derived from source-native terminology.

The Unit Profile page already exposes cross-domain terms such as Unit, Unit
Profile, Trooper, Attribute, Characteristic, Training, Troop Type, Trooper
Classification, ISC, Peripheral, and Controller. These terms can form the first
seed of a game-term thesaurus even when no dedicated database domain is warranted
for a term.

Before implementing a thesaurus, the Game States and Glossary audit should
establish the broader canonical vocabulary, aliases, relationships, and source
coverage so the project does not build a second competing glossary structure.

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
families that may be useful for a future State catalog or thesaurus:

- representation/hidden-information States: Camouflaged, Decoy, Hidden
  Deployment, Holoecho, HoloMask, Impersonation;
- control/Order/alignment States: Dead, Disconnected, Isolated, Possessed,
  Retreat!, Sepsitorized, Unconscious;
- action/Attribute/profile overlays: Engaged, Foxhole, Immobilized-A,
  Immobilized-B, Normal, Prone, Stunned, Suppressive Fire, Targeted;
- item-availability state: Unloaded.

These are research groupings, not source-native State categories. If a future
catalog exposes them, mark them as InfinityDB classification metadata and keep
the canonical State identities/rules primary.

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

These are useful candidates for a future relationship graph between Traits,
States, Weapons, Equipment, Skills, and Ammunition. The later domain audits should
validate the complete edge set before materializing such a graph.

Sources:

- Wiki: <https://infinitythewiki.com/Traits>
- PDF: Infinity N5 V5.3, printed pages 174-175
