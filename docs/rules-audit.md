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
- [ ] Skills and Equipment
- [ ] Combat
- [ ] Ammunition and Weaponry
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
