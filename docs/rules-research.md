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
