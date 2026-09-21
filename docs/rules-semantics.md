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

## Skills and Equipment / Module semantics

### RS-SE-SCOPE-001 — Navigation membership does not determine rules scope

**Classification:** source-native scope with an audit/provenance consequence.

The core N5 V5.3 Skills and Equipment chapter occupies printed pages 75-127 and
contains 18 Common Skills, 76 Special Skills, and 26 Equipment entries. The live
Special Skills navigation additionally links `Commlink` and `Request
Reinforcements`, but those rules belong to the Reinforcements annex rather than
the core chapter.

InfinityDB must therefore retain source scope alongside a rule identity.
Discovering a term under a wiki navigation list is not sufficient evidence that
it belongs to core N5. Annex, FAQ, ITS, and core material may cross-link through
the same live wiki.

Sources:

- Wiki: <https://infinitythewiki.com/Skills_and_Equipment_Module>
- Wiki: Reinforcements-linked `Commlink` and `Request Reinforcements` pages
- PDF: Infinity N5 V5.3, printed pages 75-127

### RS-SE-KIND-001 — Common Skills, Special Skills, and Equipment are distinct rule kinds

**Classification:** source-native with a catalog-model consequence.

Common Skills can be declared by any Trooper and do not need to appear in its
Unit Profile. Special Skills are available because the Unit Profile lists them.
Equipment is a separate kind of game object that can grant passive effects and,
in some cases, actions.

InfinityDB must not interpret the absence of a Common Skill from Army metadata as
missing Unit data. Rules-reference identity and Army-profile occurrence are
different concerns. Equipment likewise must not be coerced into the Skill domain
merely because using a piece of Equipment can declare a Skill-like action.

Sources:

- Wiki: <https://infinitythewiki.com/Skills_and_Equipment_Module>
- PDF: Infinity N5 V5.3, printed pages 76 and 119

### RS-SE-CAT-001 — Declaration category is independent of rule/catalog kind

**Classification:** source-native with a curated-data modeling consequence.

Automatic, Deployment, Basic Short, Short, Long, and ARO describe when or how an
action/rule is used. They are not synonyms for Common Skill, Special Skill, or
Equipment. One rule can also carry more than one declaration category; for
example, Sapper is both a Deployment Skill and a Long Skill.

Equipment can participate in the same action vocabulary. GizmoKit and MediKit
are Equipment whose use is a Short Skill, and Deactivator also appears as a
Short Skill in the current Orders/AROs reference.

A reusable declaration-category relation therefore needs at least:

- the referenced rules/catalog domain;
- the canonical entity identity within that domain;
- one or more current declaration categories;
- source scope/version and citation.

It must not be structurally restricted to `entity == "skill"`.

Sources:

- Wiki: <https://infinitythewiki.com/Skills_and_Equipment_Module>
- PDF: Infinity N5 V5.3, printed pages 76, 111, 121, 123-124, and 191

### RS-SE-CAT-002 — Existing declaration-category facts require N5 V5.3 reconciliation

**Classification:** confirmed InfinityDB curated-data correctness gap.

The tracked `skillTypes` vocabulary correctly defines the six current categories:
Automatic, Deployment, Basic Short, Short, Long, and ARO. The existing
`skill-declaration-category` records do not consistently match those rules.

Confirmed mismatches include current Short Skill / ARO rules stored as Basic
Short Skill / ARO (`BS Attack`, `CC Attack`, `Dodge`, `Forward Observer`);
current Short Skills stored as Basic Short Skill / ARO (`Doctor`, `Engineer`);
Automatic Skills stored as Basic Short Skill / ARO (`Cyberplug`, `Paramedic`);
`Parachutist` stored as Deployment rather than Long; and `Triangulated Fire`
stored as Basic Short Skill / ARO rather than Long. The tracked `Entire Order`
record for Berserk also uses a category name absent from the current six-category
vocabulary.

`Regular` requires a different interpretation. The rules classify
Regular/Irregular as Training, but Army-derived data also exposes `Regular`
through a skill-like source structure. That source representation is valid
provenance and may be retained for compatibility; it must not be treated as
evidence that the rules-domain concept itself is a Skill. InfinityDB can preserve
the Army occurrence while classifying/presenting the semantic concept as
Training.

The Equipment cases expose an additional schema issue:
`skill-declaration-category` validation and query code currently require
`armyLinks.entity == "skill"`, so Short Skill actions supplied by GizmoKit,
MediKit, or Deactivator cannot be represented in their actual Equipment domain.

Consumers must not treat the current declaration-category dataset as fully
audited N5 V5.3 truth until the focused backlog reconciliation is complete.

Sources:

- PDF: Infinity N5 V5.3, printed pages 76, 77-85, 86-118, 123-124, and 191
- Curated data: `data/curated/rules/n5-core-v5.3.json`
- Validation/query ownership: `src/infinity_db/curated.py` and
  `src/infinity_db/rules_database.py`

### RS-SE-MOD-001 — MOD notation encodes direction, target, timing, and operation

**Classification:** source-native with a parsing/presentation consequence.

The Skills and Equipment module makes parenthetical MOD semantics more specific
than a generic signed number:

- positive MODs apply to the user;
- negative MODs apply to enemies, with different timing for Automatic versus
  declared Skills/Weapons/Equipment;
- Burst MODs normally apply only in the Active Turn;
- `ReRoll` changes dice handling rather than an Attribute;
- `+1SD` adds/selects a die without increasing Burst;
- `Attribute=value` and `PS=value` replace the relevant value;
- ammunition, Trait, Saving-Roll, and other annotations modify different parts of
  resolution.

These rules refine `RS-BR-ROLL-001/002`. InfinityDB should preserve the exact
source annotation and use typed parameter semantics for interpretation. A value
such as `-3` is insufficient without the owning rule and semantic target.

Sources:

- Wiki: <https://infinitythewiki.com/Skills_and_Equipment_Module#Modifiers_Explained_.28MODs.29>
- PDF: Infinity N5 V5.3, printed page 75

### RS-SE-LEVEL-001 — Levels are not generic parameters, and `Total` is a selector

**Classification:** source-native with an identity/presentation consequence.

For a Special Skill or piece of Equipment with actual Levels, a Trooper may use
only the listed Level; Levels are not cumulative. `Total` instead permits the
player to select the applicable Level for each Order or ARO.

This concept must remain distinct from parenthetical variants or parameters such
as `Mimetism (-3)`, `Immunity (POS)`, or `Forward Deployment (+4")`. Application
identity may group source records into a rule family, but the exact Level/variant
attached to the profile occurrence determines which rules apply.

The existing canonical grouping of Martial Arts L1-L5 and Strategos L1-L2 is
therefore compatible with the rules only while the source Level remains
preserved and presentable.

Sources:

- Wiki: <https://infinitythewiki.com/Skills_and_Equipment_Module#Levels.2C_Labels_and_Traits>
- PDF: Infinity N5 V5.3, printed page 76
- Identity configuration: `config/identity/source-identities.json`

### RS-SE-NFB-001 — NFB is a cross-domain compatibility constraint

**Classification:** source-native.

Negative Feedback (NFB) is not simply descriptive metadata. Use of a Special
Skill, Equipment item, Hacking Program, or other relevant rule carrying NFB is
incompatible with other NFB rules as specified by the Label/Trait interaction.

InfinityDB should model NFB as semantic rules metadata where compatibility
guidance is exposed. It should not infer compatibility merely because two effects
belong to different catalog domains.

Sources:

- Wiki: <https://infinitythewiki.com/Skills_and_Equipment_Module#Levels.2C_Labels_and_Traits>
- PDF: Infinity N5 V5.3, printed page 76

### RS-SE-RULE-001 — Requirements, Effects, Restrictions, Labels, and applicability are separate facts

**Classification:** source-native with a curated-reference consequence.

Skill and Equipment rules repeatedly separate declaration category, Labels,
Optional/Obligatory applicability, Requirements, Effects, and Restrictions.
These fields answer different questions and can change independently.

The existing direction of keeping concise structured rule facts in `rules.db` is
therefore preferable to flattening a rule into one prose summary. In particular,
`Optional` and `Obligatory` describe whether an available rule is applied, while
Requirements determine whether an attempted use is valid and Restrictions limit
otherwise permitted behavior.

Sources:

- Wiki: <https://infinitythewiki.com/Skills_and_Equipment_Module>
- PDF: Infinity N5 V5.3, printed pages 75-127

## Skills and Equipment / Profile and relationship semantics

### RS-SE-PROFILE-001 — Alternate Unit Profiles can be rule-driven states of one Trooper

**Classification:** source-native with a canonicalization consequence.

Some Skills and Equipment explicitly switch a Trooper between different Unit
Profiles instead of describing separate canonical Troopers. Transmutation uses a
rule/trigger to move to another profile. AI Motorcycle similarly has Mounted and
Dismounted profiles, with different weapon sets and representation behavior.

Canonicalization must therefore distinguish:

- logical Trooper/Unit identity;
- available profile variants;
- the rule-driven transition between those variants;
- the currently active profile in a game/session.

Two differing profiles under such a rule are meaningful alternatives, not
duplicate source rows to collapse simply because they share a Unit identity.

Sources:

- Wiki: <https://infinitythewiki.com/Seed-Embryo> (Transmutation)
- Wiki: <https://infinitythewiki.com/AI_Motorcycle>
- PDF: Infinity N5 V5.3, printed pages 117 and 119

### RS-SE-EQUIP-001 — Cube/Cube 2.0 are Equipment in the rules ontology

**Classification:** source-native with a source/presentation-classification consequence.

The Skills and Equipment chapter defines Cube and Cube 2.0 as Automatic
Equipment. Army/Profile source data and the symbol publication layer may expose
Cube through a characteristic-style icon/category, but that is a different
classification purpose.

InfinityDB should preserve both pieces of information without treating the asset
or upstream presentation category as the rules ontology. This is analogous to
the earlier distinction between Training semantics and technical order-symbol
organization.

Sources:

- Wiki: <https://infinitythewiki.com/Cube>
- PDF: Infinity N5 V5.3, printed page 121

### RS-SE-VARIANT-001 — Canonical equipment families do not erase exact source variants

**Classification:** source-native semantics with an InfinityDB identity consequence.

Some Equipment concepts have named variants whose rules differ. Hacking Device
types grant different program sets. TinBot source variants grant different
Equipment, Skills, or MODs. Firewall values also encode specific interaction
parameters.

InfinityDB may group such source records under a canonical application identity
for browsing, but the exact source variant remains contextual player-relevant
information. Family identity alone is insufficient to determine the applicable
rules.

This supports the current application/catalog policy of retaining
`application_catalog_sources` and source labels alongside canonical identities.

Sources:

- Wiki: <https://infinitythewiki.com/Hacking_Device>
- Wiki: <https://infinitythewiki.com/TinBot>
- Wiki: <https://infinitythewiki.com/Firewall>
- PDF: Infinity N5 V5.3, printed pages 123 and 127
- Identity configuration: `config/identity/source-identities.json`

### RS-SE-RECOVERY-001 — VITA/STR recovery domains have explicit rule exceptions

**Classification:** source-native cross-domain relationship semantics.

The normal recovery split aligns Doctor/MediKit with VITA-bearing targets and
Engineer/GizmoKit with STR-bearing targets. The Skills and Equipment rules also
define exceptions rather than making that split an immutable type rule:
Technorganic can allow either recovery route while the Trooper is Unconscious,
regardless of whether the profile uses VITA or STR.

Future contextual help or relationship data should therefore encode explicit
rule edges and exceptions, not derive all recovery applicability from VITA/STR
alone.

Sources:

- Wiki: Doctor, Engineer, GizmoKit, and MediKit pages
- PDF: Infinity N5 V5.3, printed pages 90-91, 116, and 123-124

### RS-SE-PERIPHERAL-001 — Cyberplug is an explicit Skill-to-Peripheral relationship

**Classification:** source-native relationship semantics.

Cyberplug is an Automatic Special Skill that grants access to Peripherals
(Cyberplug). Those Peripherals have Controller relationships and Connected/
Autonomous profile behavior defined by the Peripheral rules.

This supports the current Peripheral design direction: controller eligibility
and Peripheral type are reviewed rules relationships, not strings that should be
inferred from similar names in Army data. The Skill and the Peripheral remain
separate concepts connected by a rules-derived edge.

Sources:

- Wiki: <https://infinitythewiki.com/Cyberplug>
- Wiki: <https://infinitythewiki.com/Peripheral>
- PDF: Infinity N5 V5.3, printed pages 90 and 106-109

### RS-SE-SPECOPS-001 — Spec-Ops customization is list/session context, not immutable Unit data

**Classification:** source-native with a persistence-boundary consequence.

Infinity Spec-Ops allows a player to customize a Trooper while constructing an
Army List and provides Initial/Enhanced Unit Profiles that can transition during
play. The selected options are therefore user/list configuration applied to a
rules-defined base concept, not immutable canonical source facts for every
instance of that Unit.

A future saved-list/game model should keep those selections outside the
replaceable imported Army snapshot. Tournament legality remains a separately
scoped ITS concern rather than being inferred from the existence of the core
rule.

Sources:

- Wiki: <https://infinitythewiki.com/Infinity_Spec-Ops>
- PDF: Infinity N5 V5.3, printed pages 98-99


## Combat Module

### RS-CM-BASE-001 — Attack family and catalog kind are independent axes

**Classification:** source-native with an InfinityDB modeling consequence.

The Combat Module defines three combat families: Ballistic Skills (BS), Close
Combat (CC), and Quantronic Combat (Hacking). A BS or CC Attack can be performed
using a Weapon, Special Skill, or piece of Equipment that authorizes that action;
Hacking Programs likewise form rules actions reached through Hacker/Device
semantics.

InfinityDB must therefore avoid equating `weapon`, `equipment`, or `skill` catalog
identity with one combat/action type. Rules-derived action relationships should be
modeled separately from source catalog kind.

Sources:

- Wiki: <https://infinitythewiki.com/Combat_Module>
- Wiki: <https://infinitythewiki.com/BS_Attack>
- Wiki: <https://infinitythewiki.com/CC_Attack>
- PDF: Infinity N5 V5.3, printed pages 36, 39, and 51

### RS-CM-BURST-001 — Burst is contextual action data, not a universal attack count

**Classification:** source-native.

Burst (`B`) is the number of dice used for the declared Attack in its current
context. The Active Player normally uses the full current Burst and declares how
it is allocated. In ARO, Burst is normally reduced to 1 unless another rule
modifies it. Burst-changing MODs, optional bonuses, and Special Dice are distinct;
the general maximum Burst of an Attack is 6, while `+1SD` does not increase B.

Stored Weapon/Program B is therefore a base profile fact. Runtime ARO Burst,
Fireteam bonuses, multiple-Trooper CC bonuses, and similar effects must not be
written back into canonical source profiles.

Sources:

- Wiki: <https://infinitythewiki.com/Combat_Module#Burst_.28B.29>
- PDF: Infinity N5 V5.3, printed page 36

### RS-CM-PS-001 — N5 uses Possibility of Survival, not Damage, as the profile value

**Classification:** source-native with a source/presentation-boundary consequence.

N5 V5.3 defines **Possibility of Survival (PS)** as the value used when resolving
harm/effects. Lower PS is more lethal because PS is added to the target's
protection when determining the Saving-Roll Success Value.

Infinity Army metadata currently reaches InfinityDB through a source field named
`damage`; preserving that source key is provenance, not permission to present the
N5 concept as `Damage`/`DAM`. The current Weapon detail UI labels the field `DAM`;
rules-facing presentation should expose **PS** while retaining the upstream field
name internally where required for compatibility.

Sources:

- Wiki: <https://infinitythewiki.com/Possibility_of_Survival_%28PS%29>
- Wiki: <https://infinitythewiki.com/Ranged_Weapon_Profile>
- PDF: Infinity N5 V5.3, printed pages 37 and 46
- Current presentation: `src/infinity_db/web/static/catalog-detail.js`

### RS-CM-SR-001 — Saving-Roll profile fields encode typed expressions

**Classification:** source-native with a persistence/presentation consequence.

A combat profile separately specifies PS, the Saving Roll Attribute/expression,
and the number of Saving Rolls. The Saving expression may identify ARM, BTS,
PH or another Attribute; combine Attributes; halve/substitute a value; or apply
a MOD. Some effects have no PS and instead require a direct Attribute Roll with
a listed MOD.

InfinityDB should therefore preserve the exact source fields and their typed
meaning rather than deriving a single generic `damage-versus-defense` scalar.
`saving` and `savingNum` are independent facts, and rules summaries should not
assume every hit resolves against unmodified ARM or BTS.

Sources:

- Wiki: <https://infinitythewiki.com/Saving_Roll_%28SR%29>
- Wiki: <https://infinitythewiki.com/Ranged_Weapon_Profile>
- PDF: Infinity N5 V5.3, printed pages 37 and 46-47

### RS-CM-WPN-001 — Canonical Weapon identity does not replace exact mode/profile semantics

**Classification:** source-native semantics with an InfinityDB identity
consequence.

Ranged Weapon profiles independently define Range MODs, PS, Burst, Ammunition,
Saving Roll Attribute, number of Saving Rolls, and Traits. A Weapon may expose
multiple modes whose values differ across those fields. Melee profiles use the
same combat-profile vocabulary but normally omit Range bands.

This confirms the current application-catalog boundary: canonical Weapon identity
can group equivalent source identities for browsing, while `metadata_weapons`
modes/profiles remain contextual player-relevant data. Consumers must not infer a
specific mode's combat values from the canonical family identity alone.

Sources:

- Wiki: <https://infinitythewiki.com/Ranged_Weapon_Profile>
- Wiki: <https://infinitythewiki.com/Melee_Weapon_Profile>
- PDF: Infinity N5 V5.3, printed pages 46-47 and 53
- Model contract: `docs/data-model.md`, application catalog identity and metadata context

### RS-CM-RANGE-001 — Range profiles belong to attack-capable rules, not only Weapons

**Classification:** source-native.

BS Weapons, pieces of Equipment, and Special Skills capable of making BS Attacks
can define Range MODs. If the target is beyond the applicable maximum Range, the
Attack fails; this is different from merely receiving another numeric Range MOD.

Rules-reference composition should therefore be able to associate a range profile
with an action supplied by Equipment or a Skill as well as by a Weapon. The
current Weapon metadata range table remains valid for Weapon profiles, but it is
not a complete ontology of every ranged action in the game.

Sources:

- Wiki: <https://infinitythewiki.com/Ballistic_Skills#Range>
- Wiki: <https://infinitythewiki.com/Ranged_Weapon_Profile>
- PDF: Infinity N5 V5.3, printed pages 42 and 46-47

### RS-CM-TPL-001 — Template type is attack semantics, not catalog identity

**Classification:** source-native cross-domain semantics.

Template Weapons and Equipment use area-of-effect geometry. Direct Templates and
Impact Templates are distinct use modes: Direct Templates normally make no BS
Roll to hit, while Impact Templates require an Attack Roll. Either behavior may
be supplied by a Weapon or Equipment item.

`Direct Template` and `Impact Template` should therefore remain Traits/rules
semantics attached to the relevant profile rather than being used to decide that
the source item belongs in the Weapon catalog.

Sources:

- Wiki: <https://infinitythewiki.com/Template_Weapons_and_Equipment>
- Wiki: <https://infinitythewiki.com/Direct_Template_Weapons>
- Wiki: <https://infinitythewiki.com/Impact_Template_Weapons>
- PDF: Infinity N5 V5.3, printed pages 43-50

### RS-CM-CC-001 — Close Combat bonuses are runtime relationship effects

**Classification:** source-native with a canonicalization consequence.

CC Attack uses the attacker's applicable CC profile, but Close Combat with
multiple Troopers can add Burst according to which allied Troopers/Peripherals are
currently in Silhouette contact and eligible under the current States. That bonus
is produced by the live engagement relationship, not by the Weapon's static B.

InfinityDB should preserve base melee profile Burst and treat multi-Trooper CC
bonuses as runtime rules context. Peripheral/controller identity can inform the
relationship graph without turning the situational bonus into a canonical loadout
fact.

Sources:

- Wiki: <https://infinitythewiki.com/Close_Combat>
- Wiki: <https://infinitythewiki.com/CC_Attack>
- PDF: Infinity N5 V5.3, printed pages 51-53

### RS-CM-HACK-001 — Hacking Device variants grant explicit Program sets

**Classification:** source-native relationship semantics.

`Hacker` identifies Troopers capable of using Hacking Devices/Programs. Each
Hacking Device variant grants an explicit Program set, while Hackers may also
receive Upgrade Programs separately. In N5 V5.3 the standard Device families map
to finite sets of the twelve core Hacking Programs.

This is a reviewed rules relationship, not a naming convention. InfinityDB should
model Hacking Program identity and Device-to-Program/Upgrade links in the rules
reference layer rather than infer them from Equipment labels or flatten them into
the canonical Hacking Device family.

Sources:

- Wiki: <https://infinitythewiki.com/Hacker>
- Wiki: <https://infinitythewiki.com/Hacking_Device>
- PDF: Infinity N5 V5.3, printed pages 54 and 58-62

### RS-CM-HACK-002 — Hacking Area is a derived runtime relationship graph

**Classification:** source-native relationship semantics.

A Hacker's Hacking Area includes the Hacker's own ZoC plus the ZoCs of allied
Repeaters and Deployable Repeaters, with additional rules for interacting through
enemy Repeaters. It can create ARO/target relationships without LoF and outside
the Hacker's own ZoC.

Hacking Area is therefore not a fixed range value that belongs on a Hacker's
canonical Unit Profile. InfinityDB may document which entities extend or use the
area, but an actual live Hacking Area requires game positions, Repeater state,
Army-list alignment, and current States.

Sources:

- Wiki: <https://infinitythewiki.com/Hacking_Area>
- Wiki: <https://infinitythewiki.com/Repeater>
- PDF: Infinity N5 V5.3, printed pages 55-57

### RS-CM-HACK-003 — Firewall is a two-sided, non-stacking defensive modifier

**Classification:** source-native parameter and relationship semantics.

Firewall applies a parameterized negative MOD to an enemy's Comms Attack WIP
Roll and normally gives the protected Trooper +3 to Saving Rolls against that
Comms Attack. A Trooper benefits from only one Firewall at a time even when
multiple sources are available. The parenthetical value in `Firewall (-3)` or
`Firewall (-6)` therefore does not describe the whole effect.

InfinityDB should not flatten Firewall to a single scalar modifier. The attack
MOD, Saving-Roll MOD, applicability to Comms Attacks, source relationship, and
non-stacking rule are separate facts.

Sources:

- Wiki: <https://infinitythewiki.com/Firewall>
- Wiki: <https://infinitythewiki.com/Repeater>
- PDF: Infinity N5 V5.3, printed pages 55-56

### RS-CM-HACK-004 — Hacking Programs have a dedicated typed profile schema

**Classification:** source-native rules-domain semantics.

The Hacking Programs chart defines Program profiles using **Attack MOD, Opponent
MOD, PS, Burst, Target, Skill Type, and Special**. Targets may be Troop Types,
Hackers, broader game elements, or effectively unrestricted depending on the
Program. Program effects can invoke Ammunition, States, Supportware, profile
changes, MODs, or non-damaging effects.

Hacking Programs should therefore become a rules-reference domain rather than be
encoded as pseudo-Weapons or pseudo-Skills solely to reuse an existing schema.
Shared concepts such as PS, Burst, Ammunition, Labels, and States can be related
across domains while preserving the Program-specific profile fields.

Sources:

- Wiki: <https://infinitythewiki.com/Hacking_Programs_Chart>
- Wiki: <https://infinitythewiki.com/Quantronic_Combat_%28Hacking%29>
- PDF: Infinity N5 V5.3, printed pages 57-62

## Ammunition and Weaponry

### RS-AW-AMMO-001 — Ammunition is a typed rules-effect vocabulary

**Classification:** source-native with a curated-data consequence.

N5 V5.3 defines eleven base Ammunition types: Normal (N), Armor Piercing (AP),
Double Action (DA), Eclipse, Electromagnetic (E/M), Explosive (EXP), Paralysis
(PARA), Shock, Smoke, Stun, and T2.

These identities describe different rule operations rather than variants of one
numeric damage scalar. Depending on the type, Ammunition can change the
effective Saving Roll Attribute, number of Saving Rolls, Wounds caused, State
effects, visibility effects, or whether a target can be affected at all.

InfinityDB should therefore model reviewed Ammunition identities/effects in the
rules layer and link Weapon profiles to them. Source Ammunition IDs/names remain
provenance; effects should not be inferred from Weapon display names.

Sources:

- Wiki: <https://infinitythewiki.com/Ammunition>
- Wiki: <https://infinitythewiki.com/Ammunition_Summary_Chart>
- PDF: Infinity N5 V5.3, printed pages 63-67

### RS-AW-AMMO-002 — Ammunition effects are orthogonal to PS and profile fields

**Classification:** source-native with a Weapon-profile interpretation
consequence.

The same Weapon-profile schema separates PS, Ammunition, Saving Roll Attribute,
number of Saving Rolls, and Traits because Ammunition can modify different parts
of resolution. AP halves the applicable ARM/BTS value; DA and EXP increase the
number of Saving Rolls; T2 changes Wounds per failed Roll; E/M/PARA/Stun can
cause States; Smoke/Eclipse create visibility effects without ordinary damaging
Saving Rolls.

InfinityDB must preserve those fields independently. A rules-aware view may
explain how they combine, but normalization must not replace them with one
derived "damage" value.

Sources:

- Wiki: <https://infinitythewiki.com/Ammunition_Summary_Chart>
- PDF: Infinity N5 V5.3, printed pages 63-67

### RS-AW-AMMO-003 — Combined Ammunition is explicit composition

**Classification:** source-native relationship semantics.

When Ammunition types are joined with `+`, the rules treat them as one Combined
Ammunition whose component effects apply together. Criticals add one additional
Saving Roll applying the relevant combined effects; the component rules still
determine effects such as defense halving, Saving Roll count, Wounds, and States.

Army may expose a combined expression such as `AP+DA` as its own source
Ammunition row. InfinityDB should preserve that source identity while a curated
rules layer records reviewed component relationships. Canonical composition must
not depend solely on parsing punctuation from a display label when source IDs
and reviewed mappings are available.

Sources:

- Wiki: <https://infinitythewiki.com/Combined_Ammunition>
- PDF: Infinity N5 V5.3, printed page 67

### RS-AW-SAVE-001 — Combined Saving Roll is not Combined Ammunition

**Classification:** source-native with a parsing/presentation consequence.

A Weapon may require Saving Rolls against more than one Attribute, represented
by a combined Saving Roll expression such as `ARM+BTS`. This is a different
operation from an Ammunition expression such as `AP+DA`: the former identifies
multiple defense Attributes/Rolls; the latter composes Ammunition effects.

The `+` token is therefore field-scoped syntax. InfinityDB must retain typed
field context when parsing, normalizing, validating, or presenting Weapon
profiles instead of assigning a universal meaning to the character.

Sources:

- Wiki: <https://infinitythewiki.com/Combined_Saving_Roll>
- PDF: Infinity N5 V5.3, printed page 67

### RS-AW-WPN-001 — Canonical Weapon identity and mode profile are separate

**Classification:** source-native with an InfinityDB canonicalization
consequence.

Mixed Weapons can operate as both BS and CC Weapons, and each mode can carry
different Attack Attribute semantics, Range, Burst, Ammunition, Saving Roll
fields, and Traits. Other multi-mode Weapons likewise change profile facts
without becoming unrelated canonical items.

This confirms the current application boundary: canonical Weapon identity may
group reviewed variants/modes, while exact metadata mode/profile rows remain
contextual data. A consumer must select the applicable mode rather than merge
mode fields into one synthetic profile.

Sources:

- Wiki: <https://infinitythewiki.com/Mixed_Weapons>
- PDF: Infinity N5 V5.3, printed pages 68-69

### RS-AW-WPN-002 — Disposable use pools can be shared across Weapon modes

**Classification:** source-native with a future session-model consequence.

For a Disposable Weapon with multiple modes, the Disposable use count is shared
between those modes. Drop Bears and D-Charges are explicit examples: using one
mode consumes from the same limited resource available to the other mode.

Static Weapon profiles should therefore preserve the shared-resource semantic
relationship. A future game/session model must not create an independent use
counter for every metadata mode row.

Sources:

- Wiki: <https://infinitythewiki.com/Traits#Disposable>
- Wiki: <https://infinitythewiki.com/Drop_Bears>
- Wiki: <https://infinitythewiki.com/D-Charges>
- PDF: Infinity N5 V5.3, printed pages 70-71

### RS-AW-DEP-001 — Deployables become independent game elements with profiles

**Classification:** source-native relationship semantics.

Deployable Weapons and Equipment can be placed on the table as game elements
separate from their bearer. Several have their own ARM, BTS, STR, and S values,
and some have their own Weapons, Equipment, Skills, trigger rules, or
representation.

InfinityDB should distinguish ownership/source loadout from the rules identity
and profile of the deployed object. A Deployable is not automatically a
Peripheral, and its table profile must not be flattened into the bearer's Unit
Profile.

Sources:

- Wiki: <https://infinitythewiki.com/Perimeter_Weapons>
- Wiki: <https://infinitythewiki.com/Armed_Turret>
- Wiki: <https://infinitythewiki.com/Mines>
- PDF: Infinity N5 V5.3, printed pages 69-74

### RS-AW-DEP-002 — Delivery Weapons can place another rules object

**Classification:** source-native relationship semantics with a
missing-value/presentation consequence.

Some Weapon profiles primarily deliver or place another game element: Pitcher
places a Deployable Repeater; Mine Dispenser and Drop Bears can place Mines;
Disco Baller places a Disco Ball effect. Their delivery profile can therefore
legitimately have no PS, Ammunition, or Saving Roll value of its own.

Blank/dash attack-effect fields on such a profile are semantic absence, not
automatically incomplete source data. A rules-aware model should express the
`delivers/places` relationship instead of fabricating damage values.

Sources:

- Wiki: <https://infinitythewiki.com/Pitcher>
- Wiki: <https://infinitythewiki.com/Mine_Dispenser>
- Wiki: <https://infinitythewiki.com/Drop_Bears>
- Wiki: <https://infinitythewiki.com/Disco_Baller>
- PDF: Infinity N5 V5.3, printed pages 71-73

### RS-AW-MINE-001 — Runtime representation does not change deployable identity

**Classification:** source-native with an InfinityDB identity consequence.

A Mine may initially be represented by a Camouflaged Marker and later by a Mine
Token when its identity is revealed. That is a runtime representation/state
transition of the same deployed rules object, not evidence for separate
canonical Mine entities.

This follows the glossary distinction between Model, Marker, Token, and the
underlying game element. InfinityDB rules/reference identity should remain
separate from table representation.

Sources:

- Wiki: <https://infinitythewiki.com/Mines>
- Wiki: <https://infinitythewiki.com/Camouflaged>
- PDF: Infinity N5 V5.3, printed page 72

### RS-AW-EFFECT-001 — Weapon/Ammunition effects can depend on target predicates

**Classification:** source-native with a rules-relationship consequence.

Several effects are conditional on target data rather than merely on a hit and a
numeric profile. E/M can impose additional State effects on specified Troop
Types; PARA has no effect on targets without PH; Shock has specific interaction
with VITA 1 and Unconscious-related rules; Sepsitor can affect only eligible
Troopers with Cube or equivalent Equipment.

If InfinityDB exposes these interactions, they should be represented as cited
target/effect predicates tied to rules identities. They must not be promoted to
unconditional static properties of every Weapon occurrence.

Sources:

- Wiki: <https://infinitythewiki.com/Electromagnetic_(E/M)_Ammunition>
- Wiki: <https://infinitythewiki.com/Paralysis_(PARA)_Ammunition>
- Wiki: <https://infinitythewiki.com/Shock_Ammunition>
- Wiki: <https://infinitythewiki.com/Sepsitor>
- PDF: Infinity N5 V5.3, printed pages 64-65 and 73

### RS-AW-DATA-001 — Army Ammunition identity and rules identity are separate layers

**Classification:** source-native data plus InfinityDB rules-reference
interpretation.

Army-derived data already carries Ammunition lookup identities and Weapon
profiles reference those source values. The N5 rules independently define the
semantic identities/effects of the eleven base Ammunition types and the
composition rules for combined forms.

InfinityDB should preserve the Army IDs/labels and map them to reviewed
rules-reference identities rather than rewriting source rows. This follows the
same source-versus-semantic boundary used elsewhere: the shape chosen by Army is
valid provenance but does not force InfinityDB's rules ontology.

Sources:

- PDF: Infinity N5 V5.3, printed pages 63-67
- Source model: normalized/metadata Ammunition tables and Weapon profile
  Ammunition references


## Fireteams

### RS-FT-CHART-001 — Infinity Army Fireteams Charts are the current composition authority

**Classification:** source-native with an InfinityDB source-authority consequence.

The N5 Fireteams rules explicitly state that the official, current Fireteams
Charts are those shown in Infinity Army. The core rules define how to read and
apply a chart, while the chart supplies army/sectorial-specific Fireteam
composition.

InfinityDB should therefore preserve and present imported Army Fireteam-chart
data as the authority for current Unit/profile eligibility. Curated rules data
may explain Fireteam concepts, but must not replace Army chart membership with
a separately reconstructed eligibility list.

Sources:

- Wiki: <https://infinitythewiki.com/Fireteams_Chart>
- PDF: Infinity N5 V5.3, printed page 133

### RS-FT-BASE-001 — Fireteam Type and Fireteam Level are independent concepts

**Classification:** source-native.

`Duo`, `Haris`, and `Core` are Fireteam Types. Fireteam Level is a separate
bonus tier determined from same-Unit / chart-equivalent membership. FAQ v0.1
also clarifies that a Fireteam does not change Type merely because it loses
members.

InfinityDB must keep `type` and level/bonus composition separate. A current
member count can contribute to Level and integrity, but it is not a replacement
identity for the Fireteam Type.

Sources:

- Wiki: <https://infinitythewiki.com/Fireteams:_Basic_Rules>
- Wiki: <https://infinitythewiki.com/Fireteams_Chart>, N5 FAQ v0.1
- PDF: Infinity N5 V5.3, printed pages 132-135
- FAQ: N5 FAQ v0.1, printed page 3

### RS-FT-CHART-002 — Fireteam chart composition is Army-local contextual data

**Classification:** source-native with an InfinityDB canonicalization consequence.

A Fireteams Chart belongs to an Army or Sectorial and defines its permitted
Fireteams, Types, composition limits, and exceptions. Fireteam eligibility is
therefore contextual to that Army chart rather than an invariant property of a
game-wide logical Unit.

InfinityDB should attach canonical Unit/profile identities to the source chart
occurrence without promoting that occurrence into universal Unit membership.
This follows the same source-context boundary already used for army-specific AVA
and other list-local facts.

Sources:

- Wiki: <https://infinitythewiki.com/Fireteams_Chart>
- PDF: Infinity N5 V5.3, printed page 133
- Source model: Army `fireteamChart`

### RS-FT-CHART-003 — Fireteam min/required values are formation constraints

**Classification:** source-native plus source-data interpretation.

Fireteams Chart minimums, maximums, and required entries govern creation.
FAQ v0.1 explicitly confirms that losing a Trooper required to form the
Fireteam does not itself cancel the Fireteam; the minimum applies when the team
is created.

Observed Army chart data can mark several rows `required: true` while each has
`min: 0`. This corresponds to the chart's asterisk rule requiring at least one
member from the marked set, not every marked row individually.

InfinityDB should model these as creation/formation constraints and required-
choice membership rather than as permanent invariants or one-row mandatory
flags.

Sources:

- Wiki: <https://infinitythewiki.com/Fireteams_Chart>, N5 FAQ v0.1
- PDF: Infinity N5 V5.3, printed page 133
- FAQ: N5 FAQ v0.1, printed page 3
- Source model: Army Fireteam member `min`, `max`, and `required`

### RS-FT-FTO-001 — FTO eligibility belongs to Unit Profile options

**Classification:** source-native with an InfinityDB relationship consequence.

When a Fireteams Chart lists a Unit as `FTO`, only Unit Profile options carrying
FTO in the option name can join that Fireteam. A more specific chart term such
as `FTO-2` restricts eligibility to that specific option.

A Fireteam member relation resolved only to a Unit identity is therefore
insufficient to express all N5 eligibility. InfinityDB should preserve the
source chart wording and, when materializing Fireteam relationships, resolve
FTO restrictions against applicable source option/loadout identities.

Sources:

- Wiki: <https://infinitythewiki.com/Fireteams_Chart>
- PDF: Infinity N5 V5.3, printed page 133

### RS-FT-WILD-001 — Wildcard is an Army-local Fireteam eligibility relationship

**Classification:** source-native relationship semantics.

A Wildcard can join any Fireteam permitted by the applicable Army's chart,
subject to the maximum shown for that Wildcard entry. `Wildcard` therefore
describes a relationship between an Army chart entry and its Fireteams, not an
intrinsic cross-Army Characteristic of the Unit.

InfinityDB should keep Wildcard eligibility scoped to the source Army/chart and
must not infer universal Fireteam eligibility from a Unit being a Wildcard in
one context.

Sources:

- Wiki: <https://infinitythewiki.com/Fireteams_Chart>
- PDF: Infinity N5 V5.3, printed pages 133 and 137

### RS-FT-LEVEL-001 — Bracket terms define Fireteam-Level equivalence, not Unit identity

**Classification:** source-native with an InfinityDB identity consequence.

Fireteam Level is based on the number of members considered to belong to the
same Unit. For this calculation, the rules also treat Troopers with the same
term in brackets (or equivalent chart note) as belonging to the same Unit.

This equivalence is scoped to Fireteam bonus calculation. A chart label such as
`(Morat)` or `(Fennec)` must not merge the underlying Units in InfinityDB's
logical-Unit layer or become a generic Unit alias. It is a Fireteam-context
equivalence relationship.

Sources:

- Wiki: <https://infinitythewiki.com/Fireteam_Bonuses>
- Wiki: <https://infinitythewiki.com/Fireteam_Examples>
- PDF: Infinity N5 V5.3, printed pages 135 and 138

### RS-FT-NOTE-001 — Fireteam chart notes can override general Fireteam rules

**Classification:** source-native with a source-preservation consequence.

The Fireteams Chart rules explicitly allow additional conditions for creation or
operation, and state that these notes take priority over the General Rules of
Fireteams.

Army Fireteam descriptions/observations are therefore potentially rule-bearing
context rather than disposable display text. InfinityDB should preserve and
surface them with the relevant chart entry. Structured interpretation should be
reviewed and use-driven rather than inferred automatically from arbitrary note
text.

Sources:

- Wiki: <https://infinitythewiki.com/Fireteams_Chart>
- PDF: Infinity N5 V5.3, printed page 133
- Source model: Army Fireteam chart `desc` / team `obs`

### RS-FT-ELIG-001 — Chart eligibility and current runtime eligibility are different scopes

**Classification:** source-native with an InfinityDB presentation consequence.

A Fireteams Chart states which Troopers/options may form a Fireteam, while the
general Fireteam rules can prevent otherwise chart-eligible Troopers from
joining or remaining in one because of current State, representation, role, or
other runtime conditions.

InfinityDB should describe static/reference information as **Fireteam chart
eligibility**. It should not claim that a listed Trooper is unconditionally
"able to Fireteam" in every game state, nor should it try to derive current
runtime membership from static Army data.

Sources:

- Wiki: <https://infinitythewiki.com/Fireteams:_Basic_Rules>
- Wiki: <https://infinitythewiki.com/Fireteam_Integrity>
- PDF: Infinity N5 V5.3, printed pages 132-134

## Command

### RS-CMD-TOK-001 — Command Tokens are player/match resources

**Classification:** source-native with an InfinityDB data-boundary consequence.

Command Tokens represent command-and-control resources available to a player.
The core Command rules normally give each player four for the match. Strategic,
Executive, and Operational are use modes for that same resource rather than
different token identities.

InfinityDB may explain and cross-link Command Token interactions, but a current
token balance is not an invariant Unit/Profile/catalog fact. Actual availability
and expenditure belong to a constructed-list/game-session context.

Sources:

- Wiki: <https://infinitythewiki.com/Command_Tokens>
- PDF: Infinity N5 V5.3, printed pages 128-129

### RS-CMD-TOK-002 — Static catalog facts can modify a session resource conditionally

**Classification:** source-native relationship semantics.

Some static profile/catalog facts interact with Command Tokens only when their
game/list conditions apply. A Lieutenant option can provide `+1 Command Token`
when that Trooper is selected as the Lieutenant. Counterintelligence modifies
specific effects of the opponent's Strategic Use of a Command Token.

InfinityDB should preserve the source Skill/profile facts and may curate these
relationships for explanation or search. It should not materialize their
resulting match resource as an unconditional property of the logical Unit.

Sources:

- Wiki: <https://infinitythewiki.com/Command_Tokens>
- Wiki: <https://infinitythewiki.com/Lieutenant>
- Wiki: <https://infinitythewiki.com/Counterintelligence>
- PDF: Infinity N5 V5.3, printed pages 90, 99, and 128-129

### RS-CMD-RES-001 — Command Tokens and Orders are distinct resource domains

**Classification:** source-native.

Command Tokens can be spent together with or act upon Orders, but they are not
Order types. A normal Coordinated Order spends one Command Token plus one Regular
Order. Separately, NCO operates on Special Lieutenant Orders by replacing them
with Tactical Orders; it does not turn them into Command Tokens.

InfinityDB should therefore keep Command-resource semantics separate from
Training and generated Order semantics. Cross-links may describe interactions,
but one resource vocabulary must not be used as the storage/type system for the
other.

Sources:

- Wiki: <https://infinitythewiki.com/Command_Tokens>
- Wiki: <https://infinitythewiki.com/Coordinated_Orders>
- Wiki: <https://infinitythewiki.com/NCO>
- PDF: Infinity N5 V5.3, printed pages 104 and 128-131

### RS-CMD-CO-001 — Coordinated Order participation is runtime/session context

**Classification:** source-native with an InfinityDB relationship-boundary
consequence.

A Coordinated Order temporarily activates a selected set of up to four Troopers.
The set exists for that Order and is constrained by current list/game context:
participants must share a Combat Group and Training, and runtime rules exclude
such cases as Peripherals/Controllers and Fireteam members.

InfinityDB should not materialize "coordinated with" as a persistent Unit or
profile relationship. Combat Group membership of a constructed list and actual
Coordinated Order participation belong to a future list/session layer.

Sources:

- Wiki: <https://infinitythewiki.com/Coordinated_Orders>
- PDF: Infinity N5 V5.3, printed pages 129-131

### RS-CMD-CO-002 — Coordinated Order eligibility reinforces Training semantics

**Classification:** source-native with a source-representation consequence.

Participants in one Coordinated Order must have the same Training
(`Regular`/`Irregular`). This is a rules-domain predicate over Training, not over
membership in a Skill catalog.

Army-derived data can validly expose `Regular` through a skill-like compatibility
structure. InfinityDB should preserve that source occurrence for provenance while
resolving the semantic concept to Training when interpreting rules relationships
such as Coordinated Order eligibility.

Sources:

- Wiki: <https://infinitythewiki.com/Coordinated_Orders>
- PDF: Infinity N5 V5.3, printed page 129

### RS-CMD-CO-003 — Shared Skill identity does not require a shared implementing item

**Classification:** source-native with a catalog-model consequence.

Coordinated Order participants declare the same sequence of Skills, but they can
perform the same Skill in different ways. In a coordinated BS Attack, for
example, different Troopers may use different Weapons or Equipment while still
sharing the `BS Attack` declaration.

InfinityDB should therefore keep action/Skill identity separate from the
Weapon/Equipment used to perform that action. Reviewed relationships may connect
those domains without collapsing their canonical identities.

Sources:

- Wiki: <https://infinitythewiki.com/Coordinated_Orders#Coordinating_Skills>
- PDF: Infinity N5 V5.3, printed pages 129-130

### RS-CMD-FT-001 — Command-based Fireteam creation does not redefine chart eligibility

**Classification:** source-native cross-domain relationship semantics.

Operational Use of a Command Token can create a Fireteam, but the selected
Trooper must meet the Army Fireteam Chart Requirements. The Command rule is a
runtime creation mechanism; it does not add chart eligibility or alter the
Army-local composition authority.

InfinityDB should keep imported Fireteam chart eligibility independent from
Command Token/session state. A future play aid can cross-link the creation
mechanism to Fireteam rules without merging the domains.

Sources:

- Wiki: <https://infinitythewiki.com/Command_Tokens#Command_Tokens:_Operational_Use>
- Wiki: <https://infinitythewiki.com/Fireteams_Chart>
- PDF: Infinity N5 V5.3, printed page 129

## Movement

### RS-MOV-ATTR-001 — MOV is an ordered two-part movement allowance

**Classification:** source-native with an InfinityDB persistence/presentation
consequence.

The MOV Attribute normally contains two positionally meaningful values. The
first value is used the first time the Trooper moves in an Order; a second Move
uses the second value. The rules express those values in inches.

InfinityDB should preserve `move_1` and `move_2` as an ordered pair rather than
collapse them into a single speed value. The current source-native metric
storage and optional browser conversion to inches are representation choices
around those facts; conversion must not change which value is first or second.

Sources:

- Wiki: <https://infinitythewiki.com/Movement_Module>
- Wiki: <https://infinitythewiki.com/Move>
- PDF: Infinity N5 V5.3, printed pages 27-29

### RS-MOV-LABEL-001 — Movement is a cross-domain Label, not a declaration category

**Classification:** source-native with a curated-data consequence.

`Movement` classifies Skills/AROs whose use is movement. It is independent from
the declaration category that determines Order expenditure. Move is a Basic
Short Skill, ordinary Jump and Climb are Long Skills, and other rules can modify
those categories while the action remains Movement.

InfinityDB should keep the curated `movement` Label separate from
`skill-declaration-category` facts. Label membership should be reviewed/cited
rather than inferred from a Skill name or from Basic Short/Short/Long/ARO
classification.

Sources:

- Wiki: <https://infinitythewiki.com/Moving_and_Measuring>
- Wiki: <https://infinitythewiki.com/General_Movement_Rules>
- Wiki: <https://infinitythewiki.com/Labels>
- PDF: Infinity N5 V5.3, printed pages 27-31

### RS-MOV-PARAM-001 — Parenthetical movement distances modify a Skill, not MOV itself

**Classification:** source-native with a parsing/curated-parameter consequence.

Ordinary Jump and Climb use the first MOV value plus a rules-defined bonus. In
N5.3 that bonus is normally 2 inches. When the applicable Skill is listed in the
Unit Profile with a distance in round brackets, the listed distance replaces
that normal bonus; it is not the total movement distance and does not replace
`move_1` or `move_2`.

Super-Jump and Climbing Plus further modify how Jump/Climb can be declared and
performed without rewriting the base MOV Attribute. InfinityDB should therefore
keep a movement-distance extra attached to its Skill occurrence and describe it
with Skill-specific parameter semantics rather than treating it as a generic
profile-stat modifier.

Sources:

- Wiki: <https://infinitythewiki.com/Jump>
- Wiki: <https://infinitythewiki.com/Climb>
- Wiki: <https://infinitythewiki.com/Super-Jump>
- Wiki: <https://infinitythewiki.com/Climbing_Plus>
- PDF: Infinity N5 V5.3, printed pages 32-35

### RS-MOV-CAP-001 — MOV is not a complete mobility classification

**Classification:** InfinityDB-derived interpretation from source-native movement
semantics.

MOV provides the base movement allowances used by the rules, while Skills,
States, and table geometry can change which routes/surfaces are available, how a
movement action is declared, or how far a particular Jump/Climb can travel.
Consequently two Troopers with the same MOV pair can have materially different
movement capabilities.

InfinityDB should present MOV as the source profile Attribute and relate relevant
Skills/Equipment/States where useful. It should not infer a single authoritative
`mobility` or `speed` score from MOV alone.

Sources:

- Wiki: <https://infinitythewiki.com/General_Movement_Rules>
- Wiki: <https://infinitythewiki.com/Jump>
- Wiki: <https://infinitythewiki.com/Climb>
- Wiki: <https://infinitythewiki.com/Super-Jump>
- Wiki: <https://infinitythewiki.com/Climbing_Plus>
- PDF: Infinity N5 V5.3, printed pages 27-35

## Terrain and Scenery Structures

### RS-TS-SCOPE-001 — Special Terrain is optional table context

**Classification:** source-native with an InfinityDB data-boundary consequence.

Special Terrain is optional battlefield configuration agreed before play. Each
Special Terrain area has a Type of Terrain and at least one additional
characteristic from Difficult Terrain, Saturation, or Visibility Conditions;
its effects depend on the Trooper's relationship to that area on the table.

InfinityDB may use these rules to explain profile Skills, Equipment, and
cross-domain relationships, but a selected Special Terrain zone is not an
intrinsic Unit/Profile/Army fact. Actual zone placement and current effects
belong to scenario/table/session context.

Sources:

- Wiki: <https://infinitythewiki.com/Terrain_and_Scenery_Structures>
- PDF: Infinity N5 V5.3, printed page 143

### RS-TS-TYPE-001 — Type of Terrain is a finite parameter vocabulary

**Classification:** source-native with a profile-parameter consequence.

The current Types of Terrain are Aquatic, Desert, Mountain, Jungle, and Zero-G.
The Terrain Special Skill uses those same identities as its profile parameter.
When several Types are listed, one is chosen when the Trooper is placed on the
table; `Terrain (Total)` covers all current Types.

A Terrain parenthetical value should therefore be interpreted as a typed terrain
scope/choice, not as a Level or generic text/numeric modifier. InfinityDB can
retain the exact source extra while rules-reference data supplies the finite
vocabulary and relationships.

Sources:

- Wiki: <https://infinitythewiki.com/Types_of_Terrain>
- Wiki: <https://infinitythewiki.com/Terrain>
- PDF: Infinity N5 V5.3, printed pages 116 and 143

### RS-TS-CHAR-001 — Named terrain examples compose independent characteristics

**Classification:** source-native structure with an InfinityDB modeling
consequence.

The rules define Special Terrain using independent characteristics: Type of
Terrain, Difficult Terrain, Saturation, and Visibility Conditions. Named examples
such as Beach, Swamp, Woods, Jungle, Engine Room, or Generator Room are suggested
combinations of those characteristics, not additional canonical Types of
Terrain.

InfinityDB should not infer a permanent terrain taxonomy from the examples. A
future scenario/table record may preserve a named area's display identity while
representing its mechanical characteristics separately.

Sources:

- Wiki: <https://infinitythewiki.com/Terrain_and_Scenery_Structures>
- PDF: Infinity N5 V5.3, printed pages 143-145

### RS-TS-VIS-001 — Visibility Conditions are reusable zone concepts across domains

**Classification:** source-native cross-domain relationship semantics.

The current Visibility Conditions are Low Visibility, Poor Visibility, Zero
Visibility, and White Noise. They can be assigned to Special Terrain, but the
same zone semantics also arise outside terrain: Smoke/Eclipse create visibility
zones and the White Noise Hacking Program creates a White Noise Zone.

InfinityDB should therefore treat these as reusable rules-reference/glossary
concepts rather than creating independent terrain-, ammunition-, and
Hacking-specific identities for the same zone meaning. Whether a zone currently
exists and affects an action remains table/session state.

Sources:

- Wiki: <https://infinitythewiki.com/Visibility_Conditions>
- Wiki: <https://infinitythewiki.com/Smoke_Ammunition>
- Wiki: <https://infinitythewiki.com/Eclipse_Ammunition>
- Wiki: <https://infinitythewiki.com/White_Noise>
- PDF: Infinity N5 V5.3, printed pages 66 and 144-145

## Triumph and Defeat

### RS-TD-SCORE-001 — Objective Points and Victory Points are distinct scoring domains

**Classification:** source-native with an InfinityDB scenario-model consequence.

Victory Points are derived from the Cost of a player's Troopers that are not in
a Null State. Missions and scenarios instead define objectives that award
Objective Points. If both players finish a scenario with the same Objective
Points, Victory Points are used as the tiebreaker.

InfinityDB should therefore keep Cost, Victory Points, and Objective Points as
separate semantic concepts. A scenario reference can relate objectives to their
Objective Point awards, while current Victory Points require Army-list and
runtime-State context and must not be stored as a canonical Unit/Profile value.

Sources:

- Wiki: <https://infinitythewiki.com/Triumph_and_Defeat_Module>
- Wiki: <https://infinitythewiki.com/Terminology#Victory_Points>
- PDF: Infinity N5 V5.3, printed pages 146-147

### RS-TD-RET-001 — Retreat! situation and Retreat! State have different scopes

**Classification:** source-native with an InfinityDB state-model consequence.

The core Retreat! check applies to the player's army as a whole. When the army
enters the Retreat! situation, surviving Troopers normally enter Retreat! State.
The two concepts are not interchangeable: the situation is army/session state,
while Retreat! State is a Trooper State with its own effects and cancellation
rules.

InfinityDB should preserve that distinction in glossary/state relationships.
For example, spending a Command Token can cancel Retreat! State for one Trooper
without cancelling the army's Retreat! situation.

Sources:

- Wiki: <https://infinitythewiki.com/Triumph_and_Defeat_Module>
- PDF: Infinity N5 V5.3, printed pages 146 and 170

### RS-TD-RET-002 — The Retreat! threshold is session/list context, not static army data

**Classification:** source-native with an InfinityDB data-boundary consequence.

Under the core Retreat! rule, the threshold is 25% of the Army Points available
for building the Army List and is compared with the army's current Victory
Points. Troopers not yet placed on the table are treated as survivors for this
check.

The threshold therefore depends on game/list setup plus runtime State. InfinityDB
must not derive a permanent `retreat threshold` from a faction, Unit, or
canonical profile, nor assume that summing imported option Costs alone yields
the current Retreat! status.

Sources:

- Wiki: <https://infinitythewiki.com/Triumph_and_Defeat_Module>
- PDF: Infinity N5 V5.3, printed page 146
