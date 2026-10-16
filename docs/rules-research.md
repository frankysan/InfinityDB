# Rules research

**Project domain:** Data processing

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

References to current N5 rules mean the reviewed N5 V5.3 baseline described in
[rules semantics](rules-semantics.md#audited-source-baseline), with FAQ, annex, ITS, and historical
sources kept separately scoped. They are not a claim that a live wiki page has been rechecked on
every documentation edit.

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

### RR-AW-IMM-002 — Component-specific Immunity: reviewed AP+DA case

**Scope:** N5.3 Immunity (AP) applied to an ARM-based AP+DA attack.

The pinned [Immunity](https://infinitythewiki.com/index.php?title=Immunity&oldid=3643)
rule treats its named Ammunition as Normal; the pinned
[Combined Ammunition](https://infinitythewiki.com/index.php?title=Combined_Ammunition&oldid=3000)
rule preserves the effects of each constituent type. Together, they support
**AP+DA → N+DA, effectively DA** when Immunity (AP) negates only AP: the
ARM-halving effect is removed, while DA still requires **two full-ARM Saving
Rolls**, or **three** on a Critical. This interpretation was clarified during
the 2026-10-09 project review and is **derived from the general rules**, not
an example explicitly printed on the cited pages. It is recorded as a reviewed,
non-executable case in `skill:immunity` and RS-AW-IMM-001.

This exact example does not settle other named-component Immunities or other
Combined Ammunition pairs, and should not be turned into a general calculation
or generalized from weapon-name-specific Vulnerability examples. Historical
N4/N3 interactions are not authoritative N5 precedents.

### RR-AW-IMM-003 — Printed Immunity (BTS) versus Flash Pulse example

**Scope:** N5.3 Wiki [Immunity Example 4](https://infinitythewiki.com/index.php?title=Immunity&oldid=3643), with the N5.3 [Weapon Chart](https://infinitythewiki.com/index.php?title=Weapon_Chart&oldid=4083) for Flash Pulse's STUN/BTS and Trait profile.

**Explicit printed example:** Immunity (BTS) treats a Flash Pulse hit as Normal Ammunition; **Non-Lethal still prevents Wounds**, and **State: Stunned still applies after a failed Saving Roll**. The example confirms that neutralizing covered Ammunition does not erase these exceptional weapon Traits. Its failed-roll condition is material: the example does not apply Stunned on every hit.

This is weapon-scoped, not a general Immunity (BTS) algorithm for all BTS weapons or for combined components. The curated `skill:immunity` reference records this exact example in `reviewedWeaponCases`, and `weapon:flash-pulse` links the same canonical Traits and State. Further weapon-specific interactions remain open.

## Official publication-change notices

See [N5 source and update history](n5-source-history.md) for the indexed official
change posts and the reproducible cross-source review policy. Individual findings
here must still cite the exact relevant publication and scope.

### RR-SRC-N53-001 — N5.3 release changelog helps adjudicate source differences

**Scope:** N5.3 core rules and Army changes; ITS Season 18 changes are separate.

Corvus Belli's dated N5.3 announcement records a rules change to **Kobra Pistol**:
Shock in BS Mode and DA in CC Mode. It also lists added weapons (Breaker Sniper
Rifle, AP Red Fury, AP Thunderbolt), the Thunderbolt category, and a Trench-Hammer
Disposable correction. Its Army changelog is a **separate** list, including a
Bangbomb classification correction.

This is useful as a change log and corroborating source for the ongoing Weapon
Chart/Army comparison, not as a replacement for the printed N5.3 Weapon Chart or
Army metadata. In particular, the announcement confirms the intended Kobra Pistol
**ammunition by mode** but does **not** state why its printed CC-mode Saving Rolls
cell differs from the Army value. Keep that mismatch open until the relevant rule
and profile semantics are reconciled explicitly.

Source: Corvus Belli, *ITS Season 18 + N5.3 Rules Update*, 2026-09-01,
<https://infinityuniverse.com/en/news/infinity-rules-update-5-3>,
sections "ARMY UPDATE CHANGELOG" and "N5.3 RULES CHANGELOG".
The page is a URL-backed publication notice, not a locally hashed source snapshot.

### RR-SRC-N53-002 — Kobra Pistol CC Mode: DA effect versus Trait attribution

The N5.3 PDF (printed pp. 68, 182) assigns DA ammunition to Kobra Pistol CC Mode but prints one Saving Roll; the explicit DA ammunition rule (p. 64) requires **two** Saving Rolls per hit. The imported Army data and archived Wiki `Weapon_Chart` revision `4083` both show two; this semantic resolution does not change the printed discrepancy.

The Wiki N5.3 updated `Mixed_Weapons` revision `4082` displays an explicit old/new comparison: the earlier CC Mode had Shock and CC Traits; the new version has DA and adds Anti-materiel. That records a Wiki editorial change, **not** an official explanation that the Trait should override the PDF. Current Army/Wiki show Anti-materiel, while the v5.3 PDF omits it. The September 1, 2026 official update names the ammunition change but does not mention Anti-materiel. Consequently the Trait remains disputed.

A `sourceMode: "CC Mode"` curated Weapon reference now explains the confirmed DA mechanics and the conflict on the CC profile alone; BS Mode continues to show its unmodified Shock source profile. No new Anti-materiel membership, gameplay override, or cross-profile inheritance is asserted.

Sources: [N5.3 release notice](https://infinityuniverse.com/en/news/infinity-rules-update-5-3); [N5.3 Wiki Mixed Weapons, oldid 4082](https://infinitythewiki.com/index.php?title=Mixed_Weapons&oldid=4082); [N5.3 Wiki Weapon Chart, oldid 4083](https://infinitythewiki.com/index.php?title=Weapon_Chart&oldid=4083). Official PDF v5.3 is locally pinned by the SHA-256 in `config/validation/weapon-trait-wiki-review.json`.

### RR-SRC-N53-003 — Katyusha MRL missing plus sign in N5.3 chart

**Scope:** Katyusha MRL range bands, N5 v5.3 core PDF (printed p. 187,
SHA-256 `53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f`),
September 2026 Army snapshot (`data/generated/infinity.db`, weapon source ID 49),
and N5.3 Wiki `Weapon_Chart` (reviewed revision 4083; pinned content hash in
`config/validation/weapon-trait-wiki-review.json`).

The PDF chart extraction reports an **unsigned `3`** for the positive
Katyusha range band, while Army encodes `+3`. The N5.3 English Wiki chart and
its Spanish chart both show `+3` for the two 20–60 cm bands. Army's complete
range-band sequence is `-3, +3, +3, 0, 0, -6, --` (20 cm increments).
Under the Weapon Chart's signed-MOD notation, **only `0` may appear as an
unsigned integer**; nonzero values must have an explicit `+` or `-`. The PDF's
bare `3` is therefore an invalid value, and its intended correction is **`+3`**:
Army and both language versions of the Wiki agree on this value. This is a
**confirmed PDF sign-omission typo, not an unresolved gameplay rule**. The cause
of the omission and whether an official erratum exists are unknown, but neither
changes the interpretation. Preserve the literal `3` in the pinned PDF audit
and the correct Army `+3`; do not silently normalize other chart values. The
machine-checkable evidence is in
`config/validation/weapon-range-source-review.json`.

Sources: [N5.3 English Weapon Chart](https://infinitythewiki.com/Weapon_Chart),
[Spanish Weapon Chart](https://infinitythewiki.com/es/Tabla_de_Armas);
locally reviewed N5.3 PDF p. 187 and imported Army snapshot. This closes the
**interpretation** of this specific discrepancy, not the larger Weapon Chart
source-provenance or 1.0 completeness review.

## Weaponry family prose (N5 v5.3)

### RR-WPN-FAMILY-001 — Mines and Perimeter Weapons are distinct rules families

**Scope:** current N5 core, Weaponry pp. 69 and 72; `rules.db` and Army snapshot
from `InfinityDB-work-021d3921c61f.zip` (with the reviewed Boost curation).

The Perimeter Weapons prose defines placement within the user's Zone of Control,
while its separate Boost subsection specifies triggering, movement/contact,
Dodge resolution, blocked paths, Marker exclusions and prevention of deployable
chain reactions. The Mines subsection instead specifies camouflage placement,
mandatory template triggering, friendly-model exclusion, a Dodge MOD, and
special handling for Cybermines and Chest Mines. These are **not** interchangeable
rules: Chest Mines explicitly exclude the shared Mines mechanics in both modes;
Cybermines require Reset instead of Dodge.

InfinityDB's current curated rules database now has three distinct N5 page-72
Weapon definitions: `weapon:mines` for shared Mines placement and triggering mechanics,
`weapon:cybermine` for the Comms Attack/Reset and Saving Roll exceptions, and
`weapon:chest-mine` for separate BS/CC use modes that **do not inherit** the
shared Mines mechanics. `trait:boost` continues to own Perimeter-specific
activation, Dodge, blocked-path and Marker restrictions with its page-69
citation; generic `trait:deployable` remains unchanged.

The independently reviewed `weapon:wildparrot` reference covers N5 v5.3
Weaponry p. 74: Perimeter/Deployable placement within ZoC followed by E/M Mine
behavior, except that it deploys as a visible WildParrot Token/Model rather than
a Camouflage Marker. It does **not** have Boost; sharing Perimeter with
Crazykoala and Madtraps does not grant their movement/contact/detonation mechanic.
Its own Army profile remains E/M, BTS/2, two Saving Rolls. The printed source's
Non-Lethal Trait is absent from the Army source Traits, and the curated card
explicitly identifies this unresolved source mismatch. Linked E/M, State, and
Non-Lethal references do not modify the imported source fields. This review
uses the pinned N5 v5.3 PDF p. 74 and the reviewed exact Wiki Trait discrepancy
in `config/validation/weapon-trait-wiki-review.json`; the live N5 Wiki
WildParrot page currently identifies revision 3610, but that live page is not
a substitute for the pinned PDF or historical source evidence.

The initial PDF-hash-pinned 21-clause inventory classified **all 21 selected clauses
as explicitly represented** in the curated summaries, rather than inferring
coverage from neighbouring generic concepts. Its scope remains bounded: the
inventory does not establish complete Weaponry prose coverage. Seven verified
named Mine Weapon slugs (`ap-mine`, `e-m-mine`, `monofilament-mine`,
`para-mine`, `shock-mine`, `viral-mine`, `cybermine`) link to the shared
Mines family;
Cybermine additionally exposes its exception record. `chest-mine` links only
to the Chest Mine exception record, with both Army modes sharing that
reference; Drop Bears and Mine Dispenser deliberately do not inherit it.
The catalog-enrichment regression checks these relationships against the
tracked Army and rules databases. Actual browser visual navigation remains
to be verified manually. The Weapon detail API now gives links to
rules already rendered on the same page stable local anchors. In particular,
Cybermine's shared Mines link leads to the adjacent Mines card, not to the
first unrelated Army weapon sharing that definition. Chest Mine does not show
shared Mines mechanics. Its comparison now links to the Mines card on the first
linked Army Weapon's detail page (`/weapons/ap-mine#rule-weapon-mines`), with
fragment navigation restored after the async API render. This is a temporary
host for the shared definition, **not** a claim that AP Mine owns the rules;
a dedicated canonical shared-family landing route remains an open design decision.

An additional **archived Wiki** cross-check identifies the corresponding
N5 pages `Perimeter_Weapons` (revision 3912), `Mines` (revision 4112), and
`Chest_Mines` (revision 3525) from the 2026-09-28 English history snapshot.
The Perimeter Weapons and general Mines sections support the same reviewed
clauses. In the Wiki, the Mine line-of-fire notation uses a different degree
symbol, and Chest Mine mode clauses live on their own page, rather than on the
Mines page. Thus simple page-local string searches are not a valid semantic
comparison for those four anchors; they are **not** confirmed rule conflicts.
Archive SHA-256:
`d49db0515420af297a7349201e8bb7750ecb422048d32bb494273ee1cea78a5d`;
page payload SHA-256 values: Perimeter Weapons
`7510cf3a66b8147c2070426d4b2255a81061add3b87d33a710b0cb699f90271a`,
Mines `5f1892817a145bb27a3b77f971829f745bce1757928904dbd6f16f2ad38d89d2`,
Chest Mines `6f4abda6bc62e1be694921cb4f8b658d98781e43f72820e5c3618aa7939f90f0`.
Wiki URLs: <https://infinitythewiki.com/Perimeter_Weapons>,
<https://infinitythewiki.com/Mines>, and
<https://infinitythewiki.com/Chest_Mines>. No live Wiki revisions have been
rechecked for this audit, and no older N5 snapshot delta is inferred.

The maintained read-only source anchors and concept associations are in
`config/validation/weaponry-family-clauses.json`. Reproduce the current
snapshot comparison using `tools/audit_weaponry_family_clauses.py`.
The current 75 reviewed anchors and twelve required typed relations
are **selected evidence**, not a complete clause or relationship
inventory of Weaponry pp. 68-74. See RR-WPN-FAMILY-004;
summary matches do not establish browser acceptance.

Sources: N5 v5.3 PDF, printed pp. 69 (Perimeter Weapons/Boost), 72 (Mines,
Cybermines, Chest Mines), PDF SHA-256
`53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f`;
`data/generated/infinity.db` and `data/generated/rules.db`, with their exact
hashes emitted by the audit. PDF and generated databases are external audit
inputs, not redistributed artifacts.

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

The 24 current States are not one uniform mechanic. The audit exposes recurring
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

The current State reference describes these rules. Representing a particular game's concealed
identity or privacy-aware list sharing remains a future session feature; it must not be projected
back into canonical Unit identity or inferred from the public reference profile.

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
keeping Peripheral/controller and Fireteam relationships explicit.

Sources:

- Wiki: <https://infinitythewiki.com/Isolated_State>
- Wiki: <https://infinitythewiki.com/Disconnected_State>
- PDF: Infinity N5 V5.3, printed pages 160 and 168

## Game States and Glossary / Vocabulary research

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

This supports treating relationship rules as first-class cited semantics instead of
materializing their effects into unrelated canonical Unit fields. Reviewed Fireteam,
Peripheral, and Command relationships now have concrete semantic records; this broader
grouping remains research only for relationship families that still lack a current
application consumer.

Sources:

- Wiki: relevant Special Skill pages under the Skills and Equipment module
- PDF: Infinity N5 V5.3, printed pages 93-94, 106-109, and 112-115

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

Current Hacking Program references retain Supportware restrictions as cited rules text and
reviewed effects. Tracking which Hacker sustains which active effect remains game/session state,
not a static Equipment fact or an implemented relationship between game instances.

Sources:

- Wiki: <https://infinitythewiki.com/Quantronic_Combat_%28Hacking%29>
- PDF: Infinity N5 V5.3, printed pages 54-55

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

### RR-WPN-FAMILY-002 - Armed Turret and D-Charges source clauses

**Project domain:** Weaponry. **Scope:** official N5.3 p. 70 and current
curated rules; ITS content excluded.

The PDF-hash-pinned clause review now covers **38 selected clauses**:
Perimeter Weapons (7), Mines (14), Armed Turret (8), D-Charges (9).
All have matched explicit source text and reviewed curated-summary
evidence, with zero missing curated concepts. This does not establish
complete N5.3 Weaponry prose or browser acceptance.

Armed Turret now explicitly names Disposable (1), Non-Reloadable,
and Perimeter placement entirely inside the deploying Trooper's
Zone of Control rather than in Silhouette contact. The typed
Place Deployable relationship supports discovery. Its S1/S2 source
contradiction and E/Mitter Saving Roll discrepancy remain unresolved.

D-Charges clauses cover legal targets and contact for both modes,
placement and no ARO in Demolition Mode, resolution without a Roll,
shared Disposable (3) uses, Improvised's CC penalty, and the fact
that detonation does not affect the user. Existing curated summaries
already represent these mechanics.

Four outdated Mines/Chest Mine evidence anchors were aligned with
the current equivalent curated wording. The checked-in policy and
read-only family audit generate a source-backed report under private
local/audits/. The 38 clauses are not an exhaustive inventory of
N5.3 pp. 68-74; see RR-WPN-FAMILY-003 for the subsequent extension.

### RR-WPN-FAMILY-003 - Additional special-weapon prose clauses

**Project domain:** Weaponry. **Scope:** pinned English N5.3 core rules
pp. 71-74; ITS mission content excluded.

At this checkpoint, the hash-pinned family review covered **68 selected clauses across
ten sections**. This pass adds 30 source-to-summary evidence anchors:

- Disco Baller: 8 clauses covering targetless deployment, the Eclipse
  template, deactivation/persistence, allied-only activation, WIP +3
  and Deactivator range MODs. The Activate Disco Ball Skill carries
  activation-specific clauses rather than repeating them as new rules.
- Drop Bears: 6 clauses covering two modes, visible Mine Token
  placement, Targetless BS use, delayed detonation, CAMO restrictions,
  and the shared Disposable (3) pool.
- Mine Dispenser: 2 clauses covering inherited Drop Bears BS placement
  and the unit-profile-specified Mine type.
- Sepsitor: 5 clauses covering eligible Cube targets, Direct Template
  behavior, Saving Rolls, Critical hits, and Sepsitorized State.
  Sepsitor Plus retains a separate Weapon Chart profile.
- SymbioBomb: 6 clauses covering single use, same-army assignment,
  printed Traits, Pheroware selection, the conditional -3 target MOD,
  and removal after use. Its curated reference now explicitly labels
  **Assignable (Transmutation)**, **Comms Attack**, and **Optional**.
  SymbioBomb has no standalone Army Weapon Chart attack profile, so
  none was synthesized.
- WildParrot: 3 clauses covering placement with Place Deployable or
  Intuitive Attack, Perimeter positioning in Zone of Control, and
  visible E/M Mine behavior instead of CAMO Marker placement.

All 68 clauses in this checkpoint matched their printed anchors and
the curated summaries, with zero unresolved referenced concept IDs. This
is a bounded source-to-summary review and **does not** certify complete
prose coverage, game-state interactions, source precedence, or visual
browser acceptance. A separate headless Chrome pass checked 132/132
rule-card, citation, profile-preservation, error and overflow
assertions on the seven relevant weapon pages (including Sepsitor
Plus), at 1440, 390 and 320 px. This confirms automated
presentation behavior, **not human visual review or exhaustive
interaction coverage**. No imported Army profiles changed.

Reproduce with the existing source-hash-pinned
`config/validation/weaponry-family-clauses.json` and
`tools/audit_weaponry_family_clauses.py`; generated evidence remains
private under `local/audits/`.

### RR-WPN-FAMILY-004 - Pitcher clauses and typed relationship checks

**Project domain:** Weaponry. **Scope:** pinned English N5.3 p. 73
and current curated rules; ITS content excluded.

The source-hash-pinned audit now checks **75 selected clauses across
eleven Weaponry sections**. Seven new Pitcher clauses cover Targetless
BS Attack, Deployable Repeater delivery, placement at impact, and
the printed Disposable (2), Indiscriminate, Non-Lethal and Speculative
Attack Traits. They already have explicit curated-summary evidence;
no duplicated mechanics or profile normalization was needed.

It now verifies **twelve selected typed relationships** in a freshly
built rules database, including Pitcher to Deployable Repeater,
Mine Dispenser to Drop Bears, Disco Baller to Activate Disco Ball,
SymbioBomb to Pheroware Tactics, and Sepsitor to Sepsitorized State.
This catches missing links that matching prose cannot detect.

Policy validation rejects malformed or duplicate required edges.
Missing relation input fails closed; absent actual edges are
reported as missing instead of treated as a pass. The pinned
audit reports 75 represented clauses, twelve present required
edges, and zero missing concept IDs.

This does not establish full relationship coverage or a new
source-precedence decision, and it is not a human visual review.
The Dodge and failed-Guts movement exemption for Deployable triggers
is curated under its canonical Skill/rule owners; the shared Mines
card now links those owners where their exceptions interact with
Mine triggering. The audit does not create a context-free typed
restriction edge. Generated evidence stays under ignored local/audits/.

### RR-WPN-DEPLOYABLE-EXCEPTIONS-001 - Trigger declarations versus exempt movement

**Scope:** official N5.3 EN pp. 38, 69, 72, 79-80, 82, 112.
Source PDF SHA-256:
`53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f`.

Confirmed distinction: declaring a Dodge ARO while inside a
Mine's legal Trigger Area can trigger it (Dodge example, p. 80).
A triggering Mine still needs a legal Small Teardrop Template
reaching the declared Model or Marker without affecting allies
(p. 72). Subsequent *Dodge movement* is exempt from triggering
Deployables or generating AROs (p. 79), as is movement arising
from a failed Guts Roll (p. 38; p. 72 reminder).

Stealth does not disable Deployable triggers (p. 112).
The Boost rules (p. 69) operate on eligible enemy Models,
with distinct exempt Markers and blocked-path checks; they
must not be collapsed into Mines' Model-or-Marker Trigger
Area rule. Place Deployable (p. 82) activates newly placed
items at the Conclusion of the Order, not during their own
placement.

The shared Mines reference now explains the declaration/movement
distinction with direct links to Dodge, Guts Roll and Stealth.
Their full mechanics remain on their canonical Skill/rule
entries. No context-free Dodge-to-Deployable typed edge was
added: such an edge would wrongly imply that a Dodge declaration
itself is exempt. This batch does not change imported Army
profiles or resolve any upstream object Silhouette conflict.

The pinned source extracts and current curated facts are
regression-tested in
`tests/test_deployable_trigger_cross_rules.py`, with separate
weapon-page API link/citation coverage. A headless Chrome
check passed 297/297 assertions on the seven Mine variants
and the separate Chest Mine page, at 1440, 390 and 320 px,
including the linked clarification and no horizontal overflow.
This automated evidence is not a human visual review or a
runtime spatial simulation.

### RR-WPN-DEPLOYABLE-EXCEPTIONS-002 - Boost placement and marker eligibility

**Scope:** pinned English N5.3 pp. 49, 69, 71-72 and 82.
Source PDF SHA-256:
`53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f`.

Three distinct conditions must not be merged into one rule:

- **Placement:** Ordinary Place Deployable forbids placing a
  Deployable Weapon with only an enemy CAMO Marker in its
  Trigger Area; the official CrazyKoala example explicitly
  permits placement where a valid non-Camouflaged enemy is
  also present (p. 69). The alternative Intuitive Attack
  exception on p. 82 requires a *legally available* Skill;
  the Boost Trait alone does not grant Intuitive Attack.
- **Later activation:** The item is placed at the Conclusion
  of its Order; it becomes available only for subsequent
  Orders/AROs (p. 82, CrazyKoala example p. 69). A legal
  placement does not cause a Boost trigger during that Order.
- **Targeting:** Boost reacts to eligible **enemy Models**,
  not CAMO, IMP-1, IMP-2, or other excluded Markers; it must
  be able to travel into Silhouette contact before
  detonating (p. 69). Mines instead test an enemy Model
  **or Marker** using their Small Teardrop Template and
  allied-safety restrictions (p. 72). This difference
  persists even when a non-Camouflaged enemy permits a
  Boost weapon to be placed near a CAMO Marker.

The Boost reference links to Place Deployable, Perimeter,
Intuitive Attack, Camouflaged State, and Mines. These are
source-backed context links, not a new typed relationship
that would make Boost and Mines inherit each other's
trigger mechanics. Drop Bears' BS placement and WildParrot
remain their own published exceptions.

PDF-hash-pinned and curated-data regressions are maintained
in `tests/test_deployable_trigger_cross_rules.py`; the Glossary
API regression checks destination links on `trait:boost`.
Automated headless Chrome validation passed **60/60
assertions** at 1440, 390 and 320 px on the Boost,
Place Deployable and AP Mine pages. This does not verify
live tabletop state or constitute a human visual review.

No Army data, weapon profiles, or upstream source rows changed.

### RR-WPN-PLACEMENT-001 ? Drop Bears mode resolution and Disposable timing

**Scope:** official N5.3 English pp. 49, 71, 82 and 175,
including the published Drop Bears Weapon Chart p. 181;
ITS content excluded.

The same item supports different deployment procedures:

- **Direct Deployable Mode:** A legal ordinary Place Deployable
  declaration places one Token without a Roll, with placement
  resolved at the Conclusion of the Order (p. 82).
- **Intuitive Attack placement:** If the enemy CAMO Marker is
  inside the prospective Trigger Area without another valid
  non-camouflaged enemy, the *eligible* Deployable Mode can use
  Intuitive Attack. This is an unmodified WIP Roll; failure
  places no Token but consumes a Disposable use (p. 49).
  Intuitive Attack must be legal; it is not a generic extra
  option conferred on every Deployable Weapon.
- **Thrown BS Mode:** The Targetless throw uses its own
  BS Weapon (PH) Roll, not the Intuitive Attack WIP Roll.
  A failed throw also consumes a use under the general
  Disposable (X) rule, even though no Token is deployed
  (pp. 71, 175). Modes share a total of three uses.
  Successful BS-mode deployment happens at the Conclusion
  and cannot detonate within that Order (p. 71).

The canonical Intuitive Attack, Place Deployable, Perimeter,
BS Weapon (PH) and Disposable rules remain authoritative.
Perimeter changes the permitted placement location and
passable-path requirements; it does not independently
grant a WIP Roll or the Intuitive Attack Skill.

The Drop Bears reference now links those already-curated
mechanics and explains how failure and consumption differ
between modes. No Attack profile, imported Army alias,
shared mine mechanics or source-order precedence changed.

Source-pinned direct tests and current rules-database/API
regressions verify roll/charge/timing semantics. A headless
Chrome pass checked the Drop Bears, Intuitive Attack,
Place Deployable and Perimeter pages at 1440, 390 and
320 px: **66/66 assertions passed**, with no page errors
or horizontal overflow. This is not a human visual review
or a simulation of live tabletop targeting.
The multi-mode rule is a **player-facing explanation**,
not a new official Weapon Property or game mechanic.

### RR-WPN-PLACEMENT-002 - Mine Dispenser inherits BS Mode only

**Scope:** pinned English N5.3 pp. 49, 71-72, 82 and 175,
Weapon Chart p. 181; ITS content excluded.

Mine Dispenser uses Drop Bears' **BS Mode placement procedure**
(N5.3 p. 72), not its Deployable Mode. The launcher makes
BS-based Targetless attacks, **not** the PH-based BS Weapon
profile of Drop Bears. Successful delivery places a visible
Mine Token of the bracketed Mine subtype from the unit
profile. Placement occurs at the Order's Conclusion;
the new Token cannot detonate during that Order. The same
CAMO Marker restriction and valid non-camouflaged enemy
exception govern placement (pp. 71-72).

A **failed individual BS Roll** places no Token for that Roll
but consumes the declared Disposable use, per the canonical
Disposable (X) Trait (p. 175). The Mine Dispenser's own
**Disposable (2)** and **Double Shot** apply: the optional
+1 Burst requires both remaining uses and spends both,
even when both attack Rolls fail. A failed Roll does not
retroactively cancel another successful Roll in the Burst.

The inherited BS Mode procedure does **not** grant the
ordinary no-Roll Place Deployable action, Drop Bears'
separate Deployable Mode, Intuitive Attack, PH-based
throws or its Shock Mine subtype. Neither an invented
extra attack profile nor additional source mechanics are
published. The non-operative imported savingNum=1
discrepancy remains preserved separately.

The reference links the existing Drop Bears, Mines,
Disposable, Double Shot, BS Attack and placement rules.
Source-pinned checks and the current weapon-detail API
test verify these distinctions; current Army profiles
are unchanged. Headless Chrome passed **57/57 checks**
at 1440, 390 and 320 px on Mine Dispenser and Drop
Bears, including profile counts, explained rules and
absence of horizontal overflow. This is automated
presentation evidence, not a human visual review.
The batch does not declare complete Weaponry
source coverage or override unresolved cross-source
profiles.

### RR-WPN-DELIVERY-001 - Fired delivery versus deployed object lifecycle

**Project domain:** Weaponry. **Scope:** pinned English N5.3
pp. 71, 73, 175, 186-187, and N5 FAQ v0.1 English pp. 2-3.
ITS scenario content excluded.

The core rules distinguish a *delivery BS Attack* from the
subsequently deployed game element:

- **Pitcher:** The launcher expends a Disposable (2) use on a
  declared attack, whether the BS Roll succeeds or fails.
  A successful Roll produces a separate Deployable Repeater
  Token at the impact location. The deployed object's
  ARM 0, BTS 0, STR 1 and S 1 are from the object
  profile (N5.3 p. 186), not the launcher's attack
  profile (p. 187). This is neither a damaging hit
  nor the user's Place Deployable Skill.
- **Disco Baller:** Failed delivery Rolls spend the declared
  launcher use but place no Disco Ball. Double Shot's
  optional +1 Burst expends both unspent Disposable (2)
  uses if selected (p. 175). Successful delivery places
  a Ball with independent ARM 0, BTS 0, STR 1 and S 1
  (pp. 71, 186) and centers an Eclipse Template on it.
  The Template deactivates at the States Phase; destroying
  the Ball removes it. Later allied reactivation instead
  uses the Deactivator and a WIP +3 Skill (p. 71),
  independently of the launcher's remaining shots.

**FAQ placement:** FAQ v0.1 p. 2 requires fired
Deployables to be fully supported, not on vertical
surfaces. FAQ p. 3 explicitly extends the Place
Deployable occupied-position correction to Pitcher,
Disco Baller and Drop Bears (BS Mode): after another
Trooper occupies the intended position before the
Conclusion step, select another legal location or
lose the item if none is legal. This is not permission
to invoke the Place Deployable Skill when firing.

The curated summaries now state these outcomes with
links to the existing Disposable, Double Shot,
Repeater, Eclipse, Deactivator and activation owners.
The older Pitcher FAQ p. 2 citation was labeled as
the occupancy ruling; its label is corrected, and
FAQ p. 3 is cited independently. Previously approved
plain-text mentions of "States Phase" retain their
review rationale; the two occurrence hashes were
updated for their changed passage context. No
imported Army profiles or upstream source facts
were normalized.

Source-pinned tests and live weapon-detail API
regressions distinguish launcher charge/profile
semantics from deployed objects. Headless Chrome
passed **75/75 assertions** across Pitcher, Disco Baller
and Activate Disco Ball at 1440, 390 and 320 px,
including distinct object profiles, absence of
JavaScript errors and horizontal overflow. This is
automated behavior evidence, **not** a human visual
review or a tabletop state-resolution simulation.

### RR-WPN-DEPLOYED-001 - Deployed Repeater and Disco Ball lifecycle

**Scope:** pinned English N5.3 pp. 55-56, 71, 73, 175,
186 and current curated rules. ITS mission material excluded.

**Deployable Repeater:** The equipment exists independently
of its carrier (ARM 0, BTS 0, STR 1, S 1). Its standard
Place Deployable action and successful Pitcher BS delivery
produce the same Token but use **different declaration
and placement rules** (pp. 56, 73). Neither route gives
the other weapon/Skill an extra action. While on the table,
the Token provides a Repeater, whose Zone of Control
extends allied Hacking Areas (pp. 55-56). Enemy use,
Hacker-only reach, Firewall MODs and AROs remain defined
on Repeater and Hacking Area, not reimplemented in this
object's data. A destroyed Deployable is removed per
the Deployable Trait (p. 175), so it can no longer extend
the Hacking Area. This is not the same as an enemy Hacker
using a Repeater and does not imply targeting the Token
with a Hacking Program.

**Disco Ball:** Delivery creates a separate ARM 0,
BTS 0, STR 1, S 1 object and Eclipse Template. The
States Phase removes only the Template; the Ball remains
available for allied Activate Disco Ball using Deactivator,
LoF or ZoC and WIP +3. Destruction removes the Template
and the Ball is no longer available for activation
(p. 71). Launcher Disposable charges do not fund
reactivation. Existing curated weapon and Skill records
already stated those rules, so this pass adds focused
cross-record regressions instead of repeated prose.

The Deployable Repeater card previously described only
the Place Deployable path. It now links Pitcher delivery
and canonical Hacking Area, Repeater, Firewall and
Deployable destruction semantics, backed by PDF citations.
No imported Army profile or rules authority was changed.

Source-pinned, curated-identity and API tests distinguish
the two delivery paths and the two Disco Ball outcomes.
Headless Chrome passed **78/78 assertions** across the
Deployable Repeater, Pitcher, Disco Baller, and Activate
Disco Ball pages at 1440, 390 and 320 px, with no
JavaScript errors or horizontal overflow. This is
automated page acceptance, not a human visual review.
The tests do not simulate Orders, Hacking Program
targeting, or destruction events on a live game state.

### RR-WPN-DEPLOYED-002 - FastPanda and WildParrot object lifecycle

**Scope:** pinned English N5.3 pp. 49, 56, 69, 74,
82, 175 and 186, archived English Wiki revisions
FastPanda 3437 and WildParrot 3610, and the pinned
Army snapshot. ITS mission content excluded.

**FastPanda:** Army and the archived Wiki agree on the
equipment profile: Disposable (1), Indiscriminate,
Perimeter, Deployable, Zone of Control, with ARM 0,
BTS 0, STR 1 and S 1. Place Deployable and Perimeter
permit a destination completely inside the user's
Zone of Control, but only if an S1-sized path is
passable (N5.3 p. 82). There is no Roll for ordinary
placement; the static equipment activates at
Conclusion. It contains a Repeater, which extends
allied Hacking Areas while present; removing the
object removes that extension. It does not gain
Boost movement/triggering or Intuitive Attack from
other Perimeter devices. Indiscriminate remains a
separate canonical Trait.

**WildParrot:** The N5.3 p. 74 and archived Wiki
identify a Disposable (1), S1 Perimeter weapon
deployed with Place Deployable or eligible Intuitive
Attack. The latter uses an unmodified WIP Roll;
failure consumes the use without placing a Token
(p. 49). Conclusion-step activation means the
new object cannot trigger in its own placement
Order (p. 82). The visible ARM 0/BTS 0/STR 1
Token uses its E/M, BTS/2, two-Saving-Roll profile
and the E/M Mines procedure, never Boost movement.
Destroying the object invokes Deployable removal
(p. 175). These facts must not be generalized to
FastPanda.

**Unresolved source conflict:** N5.3 p. 74 and Wiki
revision 3610 print the WildParrot Non-Lethal Trait;
Army's pinned profile omits it. The existing source
note and imported profile are preserved without an
inferred source-precedence decision.

The previously approved unlinked FastPanda
"Zone of Control" surface is now an explicit canonical
reference. Its obsolete maintained-text review hash
was retired; other review decisions remain unchanged.
The changes are explanatory curation and source
citations, not new mechanics or Army normalization.

Automated headless Chrome acceptance passed **60/60
assertions** across FastPanda and WildParrot at
1440, 390 and 320 px, including the linked summaries,
no JavaScript errors, and no horizontal overflow.
This is not a human visual review or runtime
simulation of Hacking or Mine detonation.

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

The 1.0 curated `weapon:symbiobomb` reference now describes the
source-backed assignment and action sequence on the Weapon detail page and
links to Pheroware Tactics. This does **not** implement a live session/list
assignment model: catalog/loadout ownership remains static, assignment is
deployment state, and use is action state. They must not be collapsed into
one permanent Unit relationship. The official rules do not give SymbioBomb
a standalone Weapon Chart attack profile.

Sources:

- Wiki: <https://infinitythewiki.com/SymbioBomb>
- PDF: Infinity N5 V5.3, printed page 74

### RR-AW-OBJECT-002 - Auxiliary Weapon Chart profiles preserve conflicting Silhouettes

**Project domain:** Data processing. **Scope:** core N5 v5.3 source
reconciliation; no ITS content or imported Army normalization.

The expanded read-only audit of 14 supplementary four-Attribute object
profiles (English N5.3 Weapon Chart pp. 181/186, including Disco Ball and
Drop Bears Deployable Mode) resolves all 14 to unique existing Army
Weapon/mode identities. Seven fully match; seven differ only on the
printed Silhouette. None is evidence of a missing attack profile.

**S0 is valid in N5.3, not an obsolete or impossible Silhouette.** The
Silhouette Templates table (English and Spanish N5.3 p. 18) explicitly
defines S0 as a 25 mm base with 3 mm height, distinct from S1
(25 mm base, 25 mm height) and SX (base-height template with
base width inherited from the Trooper). N5.1 and N5.2 English p. 18
also define S0; both printed Mine profile tables specify S0.
The S1-S8 *illustrations* do not exhaust the rules table.
The same six named Mine profiles print S0 in the English N5.1 p. 177,
N5.2 p. 180 and N5.3 p. 181. Dazer prints S1 in English N5.1
p. 182, N5.2 p. 185 and N5.3 p. 186. This repeated source history
makes an accidental carryover from a previous N5 edition unlikely,
though it does not explain why Army and the PDF tables disagree.
Therefore the seven differences are real published attribute mismatches,
not invalid S0 source rows or proof that old rules survived accidentally.

- **AP, E/M, Monofilament, PARA, Shock and Viral Mines:** English N5.3
  p. 181, Spanish N5.3 pp. 190-191, and both pinned Wiki Weapon Chart
  captures consistently specify S0; pinned Army specifies S1 for these
  six named Mine profiles. The archived dedicated Mines family pages
  also describe their common Mine object as S0.
- **Dazer:** English N5.3 p. 186 and both pinned Wiki Weapon Chart tables
  specify S1. Spanish N5.3 p. 195, the English dedicated Wiki Dazer page
  and Army specify S0. The *Spanish dedicated Wiki Dazer page* instead
  specifies S1. This is a **cross-publication conflict**, including
  disagreement between a Wiki chart and an equipment-specific Wiki page;
  it cannot be summarized as a bilingual PDF difference alone.
- **Cybermine and Drop Bears Deployable Mode:** English chart and Army
  specify S0.

- **WildParrot, Crazykoala, Deployable Repeater, Disco Ball and
  FastPanda:** English chart and Army specify S1.

**Do not conflate a concealed Marker with the Mine object.** N5.3
pp. 157 and 175 expressly make a Camouflaged Marker representing a
Weapon or Equipment **S2**. On Mine deployment that is the CAMO (-3)
Marker; the corresponding MINE (-3) Token replaces it upon discovery
(N5.3 p. 72). The S2 rule governs the marker representation, while
the printed Mine object profiles and imported Army data remain
separate, still-disputed source values. InfinityDB now explains this
on the shared Mines reference rather than treating S2 as a resolution
of S0 versus S1. Chest Mines do not inherit those shared rules.

The official N5.3 change announcement dated 2026-09-01 documents
several Weapon changes but lists no Mine or Dazer Silhouette
correction. Its silence is **not proof** of the intended active
profile or precedence. See:
<https://infinityuniverse.com/en/news/infinity-rules-update-5-3>.
The full 14-object comparison is reproducible with
tools/audit_weapon_chart_profiles.py. The seven disputed profiles now
also have a separate reproducible source-provenance matrix generated by
tools/audit_auxiliary_silhouette_provenance.py. This second audit pins
the input hashes and the English/Spanish N5.3 PDF page, archived Wiki
chart member, dedicated Dazer member and Army database for each quoted
value. The resulting evidence stays in ignored local/audits/.

None of the inputs were modified. The matrix does not decide which
disputed value governs gameplay or establish that Corvus Belli has
issued a correction. The printed PDF and Wiki chart agreement is
strong evidence for S0 as the published Mine object template, but
InfinityDB must still retain the conflicting Army source rather than
normalizing it silently. Dazer remains unresolved separately.

Sources: pinned N5 v5.3 English and Spanish core rules PDFs,
pinned English and Spanish Wiki snapshots (Weapon Chart, Mines and
Dazer pages), and pinned Army metadata, all held as separate versions
outside Git. This is a source/profile audit, not a gameplay ruling.

### RR-AW-WIKI-NAMES-001 — Wiki chart names are not missing Weapon profiles

**Project domain:** Data processing. **Scope:** N5 v5.3 Weaponry;
the pinned English Wiki Weapon Chart and imported Army snapshot.

The read-only identity audit identifies **208 Wiki Weapon-profile rows**,
including repeated alternative table sections, but only **174 unique
names/modes**. All 174 have an explicit classification: 162 exact Army
name/mode identities, ten name aliases, one mode-name alias, and one
editorial row that is not a Weapon profile. No unexplained chart-name
identity remains.

- **Plural names:** The nine Wiki Mine rows (including Chest Mine's
  two modes) and CrazyKoalas correspond to singular Army Weapon names.
  These are explicit *source-name aliases*, not separate weapon types.
- **Feuerbach (Blast Mode):** The archived Wiki name corresponds to
  Army/PDF **Feuerbach (Explosive Mode)**. Both source profiles use
  PS 6, B1, EXP, three ARM Saving Rolls. Do not invent another mode.
- **Suppressive Fire Mode:** The Wiki's asterisked generic firing-mode
  row is an editorial chart reference, not an independently cataloged
  Weapon with a fixed ammunition or damage value.
- **Repeated chart rows:** 34 additional occurrences are mostly
  identical duplicated alternative tables. Four repeated mode names
  actually have different values between tables: Trench-Hammer BS/CC
  and Kobra Pistol BS/CC. Their source differences remain tracked by
  the separate mode/profile audits; identity matching does not make
  their mechanics equivalent.
- **SymbioBomb:** The source provides an assignment and one-use
  Pheroware rule but no standalone Weapon Chart or Army attack profile.
  It already has a source-cited weapon:symbiobomb rule. A missing
  chart row is not a missing gameplay definition.

The reproducible tools/audit_wiki_weapon_chart_names.py report pins
the Wiki member, archive and Army database hashes, preserves alternate
table occurrences, and fails closed on unresolved identities. Its JSON
and Markdown outputs stay in ignored local/audits/ and do not
normalize upstream data. This **closes the name-identity inventory
only**; it does not assert complete special-weapon prose, browser
coverage or definitive source precedence.

Sources: pinned English Wiki Weapon_Chart and original Army metadata;
official N5.3 pp. 68?74 and 176?188 are independent profile/prose
references. No ITS mission content was considered.

### RR-AW-SCENERY-001 — Anti-materiel effects connect Weapon rules to scenery

**Scope:** core N5.

D-Charges and other Anti-materiel Weapons can interact with scenery/structures
through rules that are not ordinary Trooper damage resolution. This creates a
cross-domain relationship between Weapon/Ammunition/Traits and the later
Terrain/Scenery Structure rules.

The Terrain/Scenery semantics are now reviewed, but InfinityDB still has no canonical
scenery/object target identity for this edge. Retain it as research until a concrete
consumer establishes that application target rather than inventing one solely to
materialize the relationship.

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

The current General Rules reference already publishes Command Token: Strategic Use for its
Counterintelligence interaction. Broader coverage of Executive and Operational Use remains
research; any expansion should keep these as use modes of Command Tokens rather than separate
token types or application domains.

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

This vocabulary may later support terrain/scenery reference pages, but the Movement
audit does not make scenery geometry part of canonical Unit data. Terrain/Scenery
semantics are now recorded in `rules-semantics.md`; keep this geometry vocabulary as
research until a concrete tabletop/scenery consumer needs it rather than introducing
a parallel movement-geometry model.

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

### RR-WPN-MINE-002 — Named Mine profile and effect-owner review (N5.3)

**Scope:** N5 v5.3 Weapon Chart printed p. 181 and Mines prose p. 72;
Army catalog from `InfinityDB-work-368473cf9537.zip`; the pinned PDF SHA-256
and per-variant review coordinates are recorded in
`config/validation/mine-variant-effects.json`. The checked-in review reconciles
seven named Mine profiles with Army's published Weapon detail API and with the
curated ammunition, trait, state, and exceptional Weapon rule identities.
This is a **profile/owner mapping**, not proof that every interaction is
represented by a rule relation or evaluated by the browser.

The profile-specific effects are **not** inherited from `weapon:mines`:

- **AP Mine:** AP, ARM/2, one Saving Roll; see `ammunition:ap`.
- **E/M Mine:** E/M, BTS/2, two Saving Rolls; the ammunition may impose
  Isolated and (on particular target types) Immobilized-B. Non-Lethal does
  not cancel those rolls.
- **Monofilament Mine:** N, ARM=0, one Saving Roll and a separate State: Dead
  Trait. This is not AP Ammunition.
- **PARA Mine:** PARA, PH-6, one Saving Roll; applies its non-Wound
  Immobilized-A effect. Its PS field is inapplicable.
- **Shock Mine:** Shock, ARM, one Saving Roll; its special effect belongs
  to `ammunition:shock`.
- **Viral Mine:** N, BTS, one printed Saving Roll, plus BioWeapon (DA+Shock)
  against VITA-bearing targets. Do not silently change the printed roll count
  to two; the additional effects belong to `trait:bioweapon`.
- **Cybermine:** no Ammunition designation, PS 5, two BTS Saving Rolls;
  Comms Attack and the Reset / Stunned / Immobilized-B exceptions belong to
  `weapon:cybermine`.

The live N5.3 Wiki Weapon Chart and Mines rules corroborate these distinctions,
but those pages may advance independently of the pinned local sources. The
PARA Mine PDF/Wiki `[*]` versus Army `[**]` source-notation discrepancy remains
**unresolved** and the original Army field is preserved. Chest Mine's two
weapon modes remain outside this seven-variant family review.

The `trait:non-lethal` summary previously implied that all non-lethal attacks
skip Saving Rolls, contradicting the E/M, PARA, and Cybermine source profiles.
The corrected definition prohibits Wounds without suppressing the rolls used
to determine non-Wound effects. Citation: pinned `wiki-traits-oldid-4110`,
Non-Lethal heading; compare the N5.3 Weapon Chart p. 181.

### Sepsitor and Sepsitor Plus (N5.3; 2026-10-09)

**Project domain:** Data processing

The pinned N5 v5.3 Weaponry section (p. 73) governs both Sepsitor weapons.
The N5.3 Weapon Chart (p. 187) gives Sepsitor PS 4 and Disposable (2), and
Sepsitor Plus PS 3 without Disposable (2). Both require a BTS Saving Roll
against a Cube-bearing target (or equivalent Equipment); a failed roll causes
Sepsitorized State, and a Critical adds a Saving Roll. Cube 2.0's +2 MOD against
both weapons comes from p. 121.

Army weapon IDs **73** (Sepsitor) and **114** (Sepsitor Plus) preserve those
individual values. Army omits N5.3's `[*]` Weaponry marker on Sepsitor Plus;
the N5.3 PDF chart and Wiki include it. InfinityDB publishes distinct
`weapon:sepsitor` and `weapon:sepsitor-plus` references, linked to the shared
State and Cube 2.0 rules, without copying the Sepsitor Disposable Trait to
Sepsitor Plus. This resolves navigation coverage, **not** the unexplained
Army/PDF marker discrepancy; a proposed name-lookup explanation remains
hypothetical. The exact older Wiki revision and source comparison are retained
in `config/validation/weapon-trait-wiki-review.json`.
