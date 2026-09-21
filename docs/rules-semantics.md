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
