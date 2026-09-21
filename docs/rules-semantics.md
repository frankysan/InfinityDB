# Rules semantics

This document records source-authoritative Infinity rules semantics that already
have a known use in InfinityDB's data interpretation, normalization, validation,
relationships, querying/filtering, or presentation work.

It is not a replacement rules reference and must not become a copy of the
rulebook. Detailed audit coverage belongs in `rules-audit.md`; verified findings
that do not yet have a concrete InfinityDB consumer belong in
`rules-research.md`.

## Classification contract

Every finding should distinguish among:

- **Source-native concept:** explicitly defined by Infinity rules or official
  source data.
- **InfinityDB abstraction:** a project-owned concept used to organize or present
  source data and not claimed to exist in the source rules.
- **InfinityDB-derived interpretation:** a reproducible conclusion derived from
  source-native facts and documented assumptions.

Rules-derived semantics should retain source scope and citations even when later
materialized into curated data or `rules.db`.

## Basic Rules / Cross-cutting semantics

### RS-BR-BASE-001 — Labels and Traits are separate rules vocabularies

**Classification:** source-native.

Labels describe defining aspects of Skills, Special Skills, and Equipment for
quick reference. Traits instead describe special features of Weapons and
Equipment, often by referring to Skills or specific effects. They are related
classification systems but are not interchangeable.

InfinityDB should keep curated Labels and Traits as separate semantic concepts.
The existing Trait catalog should not become a catch-all for Skill/Equipment
Labels merely because both are reusable rules metadata.

Sources:

- Wiki: <https://infinitythewiki.com/Basic_Rules#Labels_and_Traits_in_Infinity>
- PDF: Infinity N5 V5.3, printed page 7

### RS-BR-BASE-002 — Game States are transient, cumulative game conditions

**Classification:** source-native with an InfinityDB data-boundary consequence.

A State is an altered condition that applies to a Trooper or other game element.
Each State defines its own effects and activation/cancellation rules, and
multiple States can apply cumulatively.

Static Army/Profile data can identify rules that interact with States, but it
must not be interpreted as the Trooper's current in-game State. A future Game
States catalog belongs in the rules/reference layer; actual per-game state would
belong to a separate session/game model.

Sources:

- Wiki: <https://infinitythewiki.com/Basic_Rules#Game_States>
- PDF: Infinity N5 V5.3, printed page 9

### RS-BR-INFO-001 — Open/Private status belongs to Army-List game context

**Classification:** source-native semantics with an InfinityDB presentation
consequence.

During a game, Army-List information is Open unless the rules explicitly make it
Private. The Private list includes Cost/SWC, several deployment/identity facts,
Marker contents, and Lieutenant identity; Private Information becomes Open when
the game ends.

This is a disclosure rule for a player's constructed Army List and current game,
not a rule that makes the corresponding catalog/profile facts globally secret.
InfinityDB may display source Cost, SWC, Skills, and similar static reference data.
Future saved-list/share or game-session features must apply privacy at the list/
session boundary rather than deleting or obscuring those facts in the canonical
reference model.

Sources:

- Wiki: <https://infinitythewiki.com/Open_and_Private_Information>
- PDF: Infinity N5 V5.3, printed page 7

## Basic Rules / Unit Profile

### RS-BR-UP-001 — Unit, Unit Profile, and Trooper options

**Classification:** source-native.

A Unit groups Troopers belonging to an Army. A Unit Profile supplies the data
needed to use those Troopers, while the profile can expose multiple Trooper
options with different combinations of Skills, Equipment, Weapons, and Cost.

This gives InfinityDB a source-native vocabulary for distinguishing the Unit
from the selectable/profile options represented beneath it. It should be used
when documenting canonical unit/profile/loadout relationships rather than
calling every source row a distinct game Unit.

Sources:

- Wiki: <https://infinitythewiki.com/Unit_Profile>
- PDF: Infinity N5 V5.3, printed page 8

### RS-BR-UP-002 — Common Unit data versus option-specific data

**Classification:** source-native semantics with an InfinityDB presentation
consequence.

The Unit Profile separates data common to all options from information attached
to one option. Common Attributes, Equipment, and Special Skills belong to the
Unit-level profile presentation; an individual option may add its own Skill,
Equipment, Weapons, Peripheral, SWC, and Cost information.

InfinityDB's existing **General profile** terminology remains an InfinityDB
abstraction. The rules explain the common-versus-option-specific source meaning,
but do not define an entity named "General profile". Documentation and UI text
should preserve that distinction.

Sources:

- Wiki: <https://infinitythewiki.com/Unit_Profile>
- PDF: Infinity N5 V5.3, printed page 8

### RS-BR-UP-003 — Trooper Characteristics taxonomy

**Classification:** source-native.

The Unit Profile groups several concepts under Trooper Characteristics:

- Training, expressed through Regular or Irregular Order contribution;
- Troop Type, including LI, MI, HI, REM, TAG, WB, SK, VH, and Peripheral;
- Trooper Classification, describing the Unit's function and operational role;
- ISC (International Standard Code);
- Hackable.

Cube/Cube 2.0, Tactical Order, and Impetuous can also appear as Unit Profile
icons, but they should not be collapsed into Training merely because they are
displayed alongside other profile symbols.

This taxonomy is useful for naming and grouping existing profile fields and
symbols, for filter/help text, and for keeping game semantics separate from
asset-storage categories.

Sources:

- Wiki: <https://infinitythewiki.com/Unit_Profile#Trooper_Characteristics>
- PDF: Infinity N5 V5.3, printed page 8

### RS-BR-UP-004 — Troop Type and Trooper Classification are different axes

**Classification:** source-native.

Troop Type identifies categories such as LI, REM, or TAG and participates in
rules restrictions. Trooper Classification instead describes the Unit's
function and operational role and can affect army composition in missions or
scenarios.

InfinityDB should therefore treat `type` and `classification` as semantically
different fields rather than interchangeable labels. Presentation and filtering
should preserve both concepts independently.

Sources:

- Wiki: <https://infinitythewiki.com/Unit_Profile#Trooper_Characteristics>
- PDF: Infinity N5 V5.3, printed page 8

### RS-BR-UP-005 — ISC is source nomenclature, not InfinityDB identity

**Classification:** source-native with an InfinityDB identity consequence.

ISC is the rules-defined International Standard Code: a language-independent
nomenclature used for O-12 intelligence reporting. InfinityDB can present and
search ISC/ISC abbreviations as source metadata, but it should not silently
replace established source IDs or domain slugs with ISC as an application
identity key without separate uniqueness/stability evidence.

Sources:

- Wiki: <https://infinitythewiki.com/Unit_Profile#Trooper_Characteristics>
- PDF: Infinity N5 V5.3, printed page 8

### RS-BR-UP-006 — Attribute `-` is semantic absence, not unknown data

**Classification:** source-native.

A dash in place of an Attribute value means that the game element does not have
that Attribute. It cannot use a Skill that requires the absent Attribute. For
MOV specifically, a dash means the Trooper is stationary and cannot move.

Normalization, database storage, validation, and API serialization must not
collapse this state into an ordinary unknown/missing value without retaining
the distinction.

Sources:

- Wiki: <https://infinitythewiki.com/Unit_Profile#Attributes>
- PDF: Infinity N5 V5.3, printed page 9

### RS-BR-UP-007 — VITA and STR are alternative durability Attributes

**Classification:** source-native.

STR is defined as the alternative to VITA used for mechanical Troopers and some
scenery structures. InfinityDB should present the appropriate durability
Attribute without implying that VITA and STR are simply two unrelated stats that
all Troopers are expected to possess.

Sources:

- Wiki: <https://infinitythewiki.com/Unit_Profile#Vitality_.28VITA.29>
- Wiki: <https://infinitythewiki.com/Unit_Profile#Structure_.28STR.29>
- PDF: Infinity N5 V5.3, printed page 9

### RS-BR-UP-008 — AVA is Army List context

**Classification:** source-native.

AVA is the number of Troopers from a Unit allowed in a single Army List. It is
therefore contextual list-construction information rather than an intrinsic
combat Attribute of a canonical Trooper payload.

This supports InfinityDB keeping availability/occurrence context separate from
reusable canonical profile payload facts. The Army List audit will refine how
army-specific AVA variation should be described and validated.

Sources:

- Wiki: <https://infinitythewiki.com/Unit_Profile#Availability_.28AVA.29>
- PDF: Infinity N5 V5.3, printed page 9

### RS-BR-UP-009 — Peripheral and Controller relationship

**Classification:** source-native.

A Peripheral is a special category of Trooper associated with a Controller. In
Unit Profile notation, Peripherals are distinct from ordinary Weapons and
Equipment, and the profile example explicitly identifies the Unit option as the
Controller of its Peripheral.

This is relationship semantics, not merely display text. It supports treating
Peripheral/controller identity and eligibility as a reviewed relationship layer
rather than flattening a Peripheral into a generic equipment or weapon value.

Sources:

- Wiki: <https://infinitythewiki.com/Unit_Profile>
- PDF: Infinity N5 V5.3, printed page 8

### RS-BR-UP-010 — Unit Profile notation carries domain meaning

**Classification:** source-native presentation semantics.

The rules distinguish common data, option-specific Skills/Equipment, BS
Weapons, Peripherals, and CC/special melee weapons through consistent profile
placement and separators. InfinityDB does not need to reproduce the Army layout,
but profile help, tooltips, imports from presentation-oriented sources, and any
notation-aware views should preserve those distinctions rather than treating the
profile as one undifferentiated equipment string.

Sources:

- Wiki: <https://infinitythewiki.com/Unit_Profile>
- PDF: Infinity N5 V5.3, printed page 8

## Basic Rules / Army List

### RS-BR-AL-001 — Army List membership and AVA are army-contextual

**Classification:** source-native with an InfinityDB canonicalization
consequence.

Generic and Sectorial Army Lists are distinct list-construction contexts. A
Sectorial may expose a different set of Units and different AVA values from its
parent generic faction; using one list does not grant the membership or AVA of
the other.

This supports InfinityDB's existing separation between cross-Army logical Unit
identity and army-specific occurrence/availability. A Unit's presence in one
Army List must not be generalized into universal faction membership, and AVA
must remain attached to the applicable Army/profile occurrence.

Sources:

- Wiki: <https://infinitythewiki.com/Army_List#Sectorial_Army_Lists>
- Wiki: <https://infinitythewiki.com/Army_List#Availability_.28AVA.29>
- PDF: Infinity N5 V5.3, printed pages 9-10

### RS-BR-AL-002 — Cost and SWC are option/list-construction values

**Classification:** source-native with an InfinityDB persistence consequence.

Army Points constrain the total Cost of the Troopers selected for an Army List.
SWC is specified per Unit Profile option according to its Weapons/Equipment and
is constrained by the list's available SWC. A positive `+SWC` value has a
special meaning: it adds SWC to the player's allowance and the option itself is
considered to cost zero SWC.

InfinityDB should preserve Cost/points and SWC on the selectable Army occurrence
rather than promoting them to invariant loadout payload facts. SWC also cannot be
blindly coerced to a non-negative scalar because its source notation can encode
this additional rule meaning.

Sources:

- Wiki: <https://infinitythewiki.com/Army_List#Army_Points_and_Value>
- Wiki: <https://infinitythewiki.com/Army_List#Support_Weapons_Cost_.28SWC.29>
- PDF: Infinity N5 V5.3, printed pages 9-11

## Basic Rules / Orders and activation

### RS-BR-ORD-001 — Training and generated Order types are related but distinct

**Classification:** source-native.

Regular and Irregular are Training characteristics that determine the ordinary
Order contributed by a Trooper. The rules additionally define Special Lieutenant
Orders and Tactical Orders, which are kept separately rather than becoming new
Training values. Tactical Awareness is a Special Skill that grants an extra
Tactical Order in addition to the Order provided by Training.

InfinityDB should therefore preserve `REGULAR`/`IRREGULAR`, `LIEUTENANT`, and
`TACTICAL` order-generation records as distinct facts and must not label a
Tactical Order itself as Tactical Awareness. Technical asset categories such as
`orders/` remain storage/presentation organization, not the rules ontology.

Sources:

- Wiki: <https://infinitythewiki.com/Orders_and_the_Order_Pool#Types_of_Orders>
- Wiki: <https://infinitythewiki.com/Unit_Profile#Trooper_Characteristics>
- Wiki: <https://infinitythewiki.com/Tactical_Awareness>
- PDF: Infinity N5 V5.3, printed page 11

### RS-BR-ORD-002 — Order generation is not the runtime Order Pool

**Classification:** source-native with an InfinityDB modeling consequence.

Each Combat Group has its own runtime Order Pool containing Regular Orders only.
Irregular, Special Lieutenant, and Tactical Orders remain separate. The pool is
recalculated during each Active Turn and depends on deployment and current game
State, so it is not an immutable property of the Unit or loadout.

InfinityDB's imported/generated order payload can describe what Orders an option
normally generates, but it must not be presented as a persisted live Order Pool.
A future game/session layer would have to derive runtime pools from the selected
list and current state.

Sources:

- Wiki: <https://infinitythewiki.com/Orders_and_the_Order_Pool#Order_Pool>
- PDF: Infinity N5 V5.3, printed pages 11-12

### RS-BR-ACT-001 — Basic Short, Short, and Long are declaration categories

**Classification:** source-native and already represented by curated rules data.

Trooper Activation defines three composition-relevant Skill categories. Basic
Short Skills may combine with another Basic Short Skill or with one Short Skill;
Short Skills require a Basic Short Skill partner; a Long Skill consumes the
whole Order. The two Skills of one Order are resolved as simultaneous actions
even though they are declared sequentially.

This confirms the semantic basis of InfinityDB's curated
`skill-declaration-category` records. Category labels are rule-derived metadata
about Skills and should remain in `rules.db`, not be inferred from Army usage or
hard-coded in browser code.

Sources:

- Wiki: <https://infinitythewiki.com/Trooper_Activation>
- PDF: Infinity N5 V5.3, printed page 13

## Basic Rules / Dynamic game state

### RS-BR-LOL-001 — Loss of Lieutenant does not rewrite static Training

**Classification:** source-native with an InfinityDB interpretation consequence.

During Loss of Lieutenant, all Troopers in the player's Army List are treated as
Irregular for that situation. The effect is temporary and the player appoints a
new Lieutenant at the end of the Turn; Unit Profiles that are intrinsically
Irregular and REM Troop Types are also restricted from being appointed.

A static Unit Profile's Regular/Irregular Training and imported Order-generation
payload therefore describe the source profile, not every possible runtime Order
state. InfinityDB must not mutate or canonicalize the source Training value based
on temporary game effects such as Loss of Lieutenant.

Sources:

- Wiki: <https://infinitythewiki.com/Loss_of_Lieutenant>
- PDF: Infinity N5 V5.3, printed page 18

## Basic Rules / Spatial semantics

### RS-BR-GEO-001 — Silhouette is a template identity with defined geometry

**Classification:** source-native.

The Silhouette (`S`) Attribute selects a fixed Silhouette Template that defines a
Trooper's rules volume. The value is therefore a categorical template identity,
not a free-standing measurement: S0-S8 (and SX) map to defined base widths and
heights.

InfinityDB may store/display the source `S` code compactly, but contextual help,
geometry-aware filtering, or future tabletop tools should resolve that code
through the rules-defined template mapping rather than treating `S=2` as a
literal dimension.

Sources:

- Wiki: <https://infinitythewiki.com/Silhouette>
- PDF: Infinity N5 V5.3, printed pages 18-19

### RS-BR-GEO-002 — Rules-table distances are measured in inches

**Classification:** source-native with a source/presentation-unit consequence.

The tabletop rules define distances in inches and measure Trooper-to-Trooper
distance between the closest parts of their Silhouettes. This unit convention is
separate from how a particular upstream API serializes movement or range data.

InfinityDB must therefore retain explicit unit/source semantics when converting
Army-derived metric values for display. A bare numeric value is insufficient to
establish rules meaning; centimetre source data and inch rules presentation are
representations of a distance, not interchangeable raw fields.

Sources:

- Wiki: <https://infinitythewiki.com/Distances_and_Measurements>
- PDF: Infinity N5 V5.3, printed page 21

### RS-BR-GEO-003 — Coherency is a relationship constraint around a Reference Trooper

**Classification:** source-native relationship semantics.

Coherency applies when linked Troopers act together and a rule requires them to
remain close. The applicable rule identifies a Reference Trooper, and the other
linked Troopers must remain inside that Trooper's Zone of Control. The Reference
Trooper is role/context dependent: examples include a Fireteam Team Leader and a
Peripheral's Controller.

This is useful semantic context for InfinityDB's Peripheral/controller and future
Fireteam relationship work. `Controller`, `Team Leader`, and `Reference Trooper`
should not be collapsed into one identity relation: the first two can supply the
reference role for particular rules, while Coherency describes the spatial
constraint applied to that relationship.

Sources:

- Wiki: <https://infinitythewiki.com/Coherency>
- PDF: Infinity N5 V5.3, printed page 21

## Basic Rules / Rolls and profile modifiers

### RS-BR-ROLL-001 — Parenthetical profile values are scoped to the item being used

**Classification:** source-native with a parsing/presentation consequence.

A MOD or value shown in round brackets beside a Special Skill, Weapon, or piece
of Equipment applies only when that Skill, Weapon, or Equipment is being used.
It is not a permanent modification of the Trooper's base Attribute or a generic
Unit-wide statistic.

InfinityDB should therefore retain modifier/extras association with the source
Skill/Weapon/Equipment occurrence. Presentation such as Skill Modifiers must not
promote an item-local annotation into an unconditional profile Attribute.

Sources:

- Wiki: <https://infinitythewiki.com/Rolls#Modifiers_.28MOD.29>
- PDF: Infinity N5 V5.3, printed pages 23-24

### RS-BR-ROLL-002 — Modifier notation encodes multiple semantic operations

**Classification:** source-native with a curated-data consequence.

Parenthetical profile notation is not one uniform signed-number system. The
Basic Rules distinguish, among other forms:

- ordinary positive/negative MODs;
- Attribute replacement such as `PH=10`;
- weapon-value replacement such as `PS=5`;
- Burst changes such as `+1B`;
- `ReRoll`;
- Special Dice (`+1SD`);
- added Ammunition or Traits;
- Saving-Roll modifiers.

These forms affect different targets and phases and sometimes have additional
constraints. InfinityDB should preserve the raw/exact source representation and
attach rule-derived parameter semantics where needed rather than flattening all
extras into a generic numeric modifier. This aligns with the existing curated
`facts.parameterSemantics` boundary.

Sources:

- Wiki: <https://infinitythewiki.com/Rolls#Modifiers_.28MOD.29>
- PDF: Infinity N5 V5.3, printed pages 23-24

## Game States and Glossary / State semantics

### RS-GSG-STATE-001 — States are runtime overlays, not canonical profile facts

**Classification:** source-native with an InfinityDB data-boundary consequence.

States represent positive or negative runtime conditions of Troopers or other
game elements. They are cumulative, have explicit activation and cancellation
procedures, and can modify the same Attribute cumulatively.

InfinityDB must therefore keep static Army/Profile facts separate from current
in-game State. A rules catalog may describe what a State does and which Skills,
Weapons, or Equipment interact with it, but a canonical Unit/Profile payload
must not be rewritten to reflect a temporary State. Actual active States would
belong to a future game/session layer.

Sources:

- Wiki: <https://infinitythewiki.com/States>
- PDF: Infinity N5 V5.3, printed page 157

### RS-GSG-STATE-002 — State Tokens are reminders, not the underlying State or identity

**Classification:** source-native presentation semantics.

The rules represent States using State Tokens, while Terminology defines a State
Token as a game element indicating the effect of a rule, Skill, or State as a
reminder. This is distinct from a Model, Marker, and deployable Token.

InfinityDB UI/help and any future game-state model should therefore distinguish
`state`, `state token`, `marker`, `token`, and `model` rather than treating every
tabletop indicator as one generic marker type. The underlying rules concept
should remain addressable even when its physical representation changes.

Sources:

- Wiki: <https://infinitythewiki.com/States>
- Wiki: <https://infinitythewiki.com/Terminology#State_Token>
- PDF: Infinity N5 V5.3, printed pages 157 and 173

### RS-GSG-STATE-003 — Null is a Label that classifies a finite subset of States

**Classification:** source-native with a curated-data consequence.

`Null` is a rules Label, not a separate kind of State. In N5.3 the Null States
are Dead, Disconnected, Possessed, Sepsitorized, and Unconscious. A Trooper in a
State carrying this Label does not provide an Order or Victory Points to its
player.

InfinityDB should model this as a relationship from State identities to the
`Null` Label rather than by duplicating `is_null` rules in consumers. The current
curated `null` Label is therefore a useful reusable vocabulary entry for the
planned State catalog.

Sources:

- Wiki: <https://infinitythewiki.com/Labels#Null>
- Wiki: <https://infinitythewiki.com/States>
- PDF: Infinity N5 V5.3, printed pages 157 and 174

### RS-GSG-STATE-004 — State effects can change effective Training, alignment, or profiles

**Classification:** source-native with an InfinityDB canonicalization consequence.

Several States demonstrate that runtime values can diverge materially from
static source data without changing canonical identity:

- Isolated can make a Trooper Irregular for a Turn and suppress its Order-Pool
  contribution while the State persists.
- Possessed changes which side treats the Trooper as Ally/Enemy and requires a
  Possessed Trooper profile overlay.
- Foxhole and Prone alter effective Silhouette/movement behavior.
- Suppressive Fire substitutes an SF Mode profile for the selected weapon.

These are runtime overlays. They must not mutate canonical Training, alignment,
Unit/Profile, or weapon-profile source facts. This reinforces the existing rule
that imported payload identity describes the source profile, while game-session
conditions would be modeled separately.

Sources:

- Wiki: <https://infinitythewiki.com/Isolated_State>
- Wiki: <https://infinitythewiki.com/Possessed_State>
- Wiki: <https://infinitythewiki.com/Foxhole_State>
- Wiki: <https://infinitythewiki.com/Prone_State>
- Wiki: <https://infinitythewiki.com/Suppressive_Fire_State>
- PDF: Infinity N5 V5.3, printed pages 161 and 168-171

### RS-GSG-STATE-005 — Similar State names can encode materially different mechanics

**Classification:** source-native with an identity consequence.

Immobilized-A and Immobilized-B are distinct State identities. IMM-A restricts
the affected Trooper to Dodge with a PH-6 MOD, while IMM-B uses Reset with a
WIP-3 MOD. Both still provide Orders. Impersonation similarly has meaningful
IMP-1 and IMP-2 levels with different interaction/reveal behavior.

State canonicalization must preserve these distinctions. A future State catalog
may expose family/group relationships such as `Immobilized` or `Impersonation`,
but a normalized family name must never erase the source State/level that
controls rules behavior.

Sources:

- Wiki: <https://infinitythewiki.com/Immobilized-A_State>
- Wiki: <https://infinitythewiki.com/Immobilized-B_State>
- Wiki: <https://infinitythewiki.com/Impersonation_State>
- PDF: Infinity N5 V5.3, printed pages 164-167

### RS-GSG-STATE-006 — Unloaded is item-specific runtime state

**Classification:** source-native with a future state-model consequence.

Unloaded State is activated when the ammunition/uses of a relevant Disposable
weapon or piece of Equipment are exhausted. Its effect is that the **relevant
weapon or Equipment** can no longer be used, and cancellation/reload semantics
operate on Disposable items. This means a State associated with a Trooper/game
element can have an item-specific target rather than describing the bearer as a
whole.

A future play/session model should therefore not assume every State is a simple
boolean attached only to a Trooper ID. State instances may need affected-item or
mode context. Static InfinityDB data should continue to model `Disposable (X)`
and `Non-Reloadable` as rules/catalog semantics, not current ammunition state.

Sources:

- Wiki: <https://infinitythewiki.com/Unloaded_State>
- Wiki: <https://infinitythewiki.com/Traits#Disposable_.28X.29>
- PDF: Infinity N5 V5.3, printed pages 172 and 174-175

## Game States and Glossary / Terminology and Alignment

### RS-GSG-TERM-001 — Model, Marker, Token, and State Token are distinct game-element concepts

**Classification:** source-native.

Terminology defines four different representation/object concepts:

- a Model is a game element with Attributes represented by a miniature;
- a Marker is a game element with Attributes represented by a Marker under a
  Skill/Weapon/Equipment rule;
- a Token represents Deployable Equipment or a Deployable Weapon;
- a State Token is a reminder indicating the effect of a rule, Skill, or State.

InfinityDB should use these terms precisely in reference/help text and future
tabletop/session features. In particular, a visible Marker is not merely a UI
icon and a State Token does not become the canonical identity of the affected
Trooper or item.

Sources:

- Wiki: <https://infinitythewiki.com/Terminology>
- PDF: Infinity N5 V5.3, printed page 173

### RS-GSG-TERM-002 — Deployable Weapons and Equipment become independent game elements

**Classification:** source-native relationship semantics.

Terminology and the Deployable Trait establish that deployed Weapons/Equipment
can become independent battlefield game elements with their own Attributes and
can be targeted. Deployable Equipment belongs to an Army List; a Deployable
Weapon may belong to one, depending on the rule.

This is stronger semantics than “an Equipment item carried by a Unit.” If
InfinityDB later exposes deployable profiles or relationships, carrier/catalog
identity and deployed-game-element identity must remain separate rather than
flattening the deployed profile into its carrier.

Sources:

- Wiki: <https://infinitythewiki.com/Terminology>
- Wiki: <https://infinitythewiki.com/Traits#Deployable>
- PDF: Infinity N5 V5.3, printed pages 173-175

### RS-GSG-TERM-003 — Victory Points are runtime Cost aggregation over non-Null Troopers

**Classification:** source-native with an InfinityDB context consequence.

Victory Points are defined as the combined Cost of a player's Troopers that are
in a non-Null State. They therefore combine static list Cost with current runtime
State rather than being a static Unit/Profile value.

InfinityDB may expose Cost as imported Army-list option data, but it must not
present a simple sum of canonical Costs as current Victory Points without a
specific Army List and game-state context.

Sources:

- Wiki: <https://infinitythewiki.com/Terminology#Victory_Points>
- Wiki: <https://infinitythewiki.com/Labels#Null>
- PDF: Infinity N5 V5.3, printed pages 173-174

### RS-GSG-ALIGN-001 — Alignment is contextual and Hostile is not Neutral

**Classification:** source-native.

Alignment classifies game elements relative to the players' Army Lists: Ally
belongs to the player's side, Enemy to the opposing side, Hostile belongs to no
player but is treated as Enemy by everyone and can declare/receive Attacks, and
Neutral belongs to neither player's Army List without the additional Hostile
Enemy rule.

These terms must not be inferred from canonical faction ownership alone. Future
scenario/game-session data should carry explicit alignment semantics where rules
create Hostile or Neutral game elements, and glossary/UI text must not use
`Hostile` and `Neutral` interchangeably.

Sources:

- Wiki: <https://infinitythewiki.com/Alignment>
- PDF: Infinity N5 V5.3, printed page 173

### RS-GSG-VOC-001 — Same surface terms require scoped thesaurus concepts

**Classification:** source-native vocabulary with an InfinityDB abstraction consequence.

The rules reuse the same surface terms in distinct but related semantic roles:

- `Hackable` is both a Trooper Characteristic and a Label;
- `Hostile` is both an Alignment term and a Label;
- `Marker` is both a Terminology game-element concept and a Label;
- `Null` is a Label used to classify States and is commonly referenced through
  the derived phrase “Null State”;
- `Non-Reloadable` exists as both a Label and a Trait.

A future InfinityDB game-terms thesaurus therefore cannot use normalized display
text alone as global identity. Terms need a concept kind/scope (for example
`characteristic`, `label`, `trait`, `alignment`, `game-element`, `state`) plus
explicit relationships between same-name or related concepts. This avoids accidental
merges while still allowing cross-links and aliases.

Sources:

- Wiki: <https://infinitythewiki.com/Unit_Profile#Trooper_Characteristics>
- Wiki: <https://infinitythewiki.com/Terminology>
- Wiki: <https://infinitythewiki.com/Alignment>
- Wiki: <https://infinitythewiki.com/Labels>
- PDF: Infinity N5 V5.3, printed pages 8 and 173-174

## Game States and Glossary / Labels and Traits

### RS-GSG-LABEL-001 — Labels are semantic selectors, not display-only badges

**Classification:** source-native and already represented by curated rules data.

Labels identify defining aspects shared by Skills, Weapons, and Equipment, and
rules may refer to a Label as a group. For example, a rule referring to Airborne
Deployment applies to all Skills carrying the AD Label, while `Hackable`,
`Movement`, `Comms Attack`, `Private Information`, and other Labels carry shared
interaction semantics.

InfinityDB should therefore preserve Label membership as structured rules data
where consumers need it. Label behavior belongs in the curated rules layer and
should not be reconstructed from names or duplicated as browser-only logic.

Sources:

- Wiki: <https://infinitythewiki.com/Labels>
- PDF: Infinity N5 V5.3, printed page 174

### RS-GSG-LABEL-002 — `FAQs` in curated labels is InfinityDB metadata, not an N5 Label

**Classification:** InfinityDB abstraction.

The N5.3 rules define 23 Labels, and all 23 are represented by name in
`data/curated/rules/n5-core-v5.3.json`. That curated vocabulary contains one
additional entry named `FAQs`, described as a category for FAQ-related rule
references. `FAQs` is not one of the source-native Labels listed by the N5.3
rules.

Consumers must therefore not present the complete curated `labels` array as if
it were a verbatim list of Infinity rules Labels. Either the project-specific
entry must remain explicitly typed/scoped as metadata, or future vocabulary
modeling should separate source Labels from project/navigation categories.

Sources:

- Wiki: <https://infinitythewiki.com/Labels>
- PDF: Infinity N5 V5.3, printed page 174
- Curated data: `data/curated/rules/n5-core-v5.3.json`

### RS-GSG-TRAIT-001 — Trait names have complete current curated identity coverage

**Classification:** source-native vocabulary with an existing curated-data mapping.

The current N5.3 Traits page defines 33 Traits. The curated N5 V5.3 rules file
contains 33 `kind: "trait"` records with matching canonical names. Current Trait
**identity/name coverage is therefore complete**.

This finding is about vocabulary coverage, not full rules coverage. Attachment
of Traits to every relevant Weapon/Equipment/Skill and all structured effect
relationships still need validation during the later domain audits.

Sources:

- Wiki: <https://infinitythewiki.com/Traits>
- PDF: Infinity N5 V5.3, printed pages 174-175
- Curated data: `data/curated/rules/n5-core-v5.3.json`

### RS-GSG-TRAIT-002 — Traits encode typed parameters and cross-domain relationships

**Classification:** source-native with a parsing/curated-data consequence.

Traits are not a uniform bag of booleans. Examples include:

- `BS Weapon (PH)` / `BS Weapon (WIP)`, which substitute the Attribute used for
  BS rules;
- `Disposable (X)` and `Silent (X)`, which carry parameters;
- `Direct Template (...)` / `Impact Template (...)`, which identify a template;
- `State`, which points to a Game State named by the profile;
- `Target (Attribute)`, which selects VITA or STR;
- `Suppressive Fire (SF)`, which links a weapon to Suppressive Fire State/profile
  behavior;
- `Deployable`, which changes the carrier/item relationship by creating an
  independent game element.

InfinityDB should continue using canonical Trait identities plus structured
parameter/source semantics rather than flattening Trait text or reparsing it in
each consumer. The existing `sourceIdentity.prefixes` pattern for parameterized
Traits is an appropriate foundation to extend.

Sources:

- Wiki: <https://infinitythewiki.com/Traits>
- PDF: Infinity N5 V5.3, printed pages 174-175
- Curated data: `data/curated/rules/n5-core-v5.3.json`
