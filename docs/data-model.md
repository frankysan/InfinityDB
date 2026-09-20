# Data model notes

This document distinguishes implemented data semantics from accepted but
unimplemented design direction. Unqualified descriptions are current; future
shape is labeled **Design direction** and concrete work remains in
`docs/TODO.md`.

## Pipeline

```text
raw Army JSON
    -> lossless merged master.json
       + validated identity configuration
    -> normalized relational-style JSON
       + pinned identity document / SHA-256
    -> validated SQLite database
    -> read-only repository / HTTP API / web UI
```

## Semantic provenance

`docs/architecture.md` defines four provenance categories that must remain
visible in this model: source-native facts, source-derived facts, InfinityDB
abstractions, and presentation conveniences. Provenance answers **where a
concept comes from**. It is independent of the canonicalization classification
below, which answers **how a fact behaves in the application model**.

Current examples are:

- source-native: source unit/profile/loadout records, Army-list occurrences,
  declared `factions`, metadata faction-parent relationships, and ordinary-list
  `reinforcements` links;
- source-derived: `army_lists.kind`, `units.source_role`,
  `army_units.availability_kind`, `main_army_id`, and backend army
  role/playability;
- InfinityDB abstractions: materialized logical units, canonical application
  payloads, and the browser's `General profile` summary; and
- presentation conveniences: `display_army_id` and `display_faction`.

A non-source-native concept must document its source inputs, derivation,
assumptions/fallbacks, and semantic limits. A singular representative field must
not replace a many-context relationship set unless the audit has independently
proved that the singular value is the correct game-wide fact.

## Identities

- `unit.id` is the stable source-unit identity. It is not necessarily the
  application logical-unit identity: multiple source unit IDs can resolve to one
  materialized logical unit while source rows retain their original IDs.
- Unit `profileGroups` and unit-level `filters` are army-list-specific variants.
- Profile group, profile and loadout option IDs are local to their army/unit
  hierarchy and use composite keys in normalized data.
- Skills, weapons, equipment, ammunition, characteristics, troop types,
  categories and extras use source-native numeric lookup IDs within their source
  catalogs. Those IDs remain source references; they are not the long-term public
  identity contract for InfinityDB resources.
- Skill, equipment, and weapon occurrences retain their owning profile,
  loadout, or unit option, display order, quantity, and linked extras. This
  supports both unit details and reverse lookup from the rules-reference
  catalogs.
- Explicit source-equivalent unit, army, skill, equipment, and weapon IDs are
  maintained in validated `config/identity/source-identities.json`
  configuration. That policy also owns reinforcement-label prefixes used by
  unit/profile identity normalization and backend profile display names. Generic
  duplicate/name matching remains implementation
  behavior rather than authored alias data; normalization now persists the
  resulting generic unit matches for current snapshots.
- Weapon-family classification policy is maintained in validated
  `config/catalogs/weapon-categories.json`, while known Army weapon metadata
  corrections are maintained separately in `config/catalogs/weapon-overrides.json`.
  Those corrections include source name/profile fixes and exact metadata weapon
  rows that should not become display profiles. Normalization applies the authored
  build inputs before normalized catalog/metadata rows are materialized, while the
  original Army metadata envelope remains unchanged for provenance. The frontend
  database does not need the config files at runtime.
- Current InfinityDB builds derive a unit's application `main_army_id` from
  the imported Army metadata parent for its canonical faction. Maintained
  canonical-faction overrides take precedence when explicitly configured. The
  old whole-army `xx01` calculation remains only as a standalone/legacy
  normalization fallback when no usable metadata row exists for that canonical
  faction. Source canonical-faction ID `1` remains mercenary source/origin
  provenance with `main_army_id = null`, while `901` remains the distinct
  Non-Aligned Armies grouping identity. Presentation is modeled separately:
  normalization derives `display_army_id` from reviewed relationships in
  `data/curated/identities/army-display.json`; the current curated relationship
  displays canonical-1 units with the 901 grouping identity. `main_army_id` is
  therefore a source-derived grouping/application field, not authority for a
  unit's complete game-wide membership, availability, or ownership.
- InfinityDB normalization pins the exact validated identity configuration and
  its canonical SHA-256 into `normalized.json`. Database export revalidates that
  provenance and propagates the same policy into both database siblings.
  Repository queries consume the database-pinned policy rather than reading the
  working tree's `config/` directory at runtime.
- Peripheral IDs are army-local.
- Referenced but undefined factions/units/categories are retained as explicit
  placeholder records rather than discarded.
- Normalization warnings remain source-preservation diagnostics, not automatic
  corrections. InfinityDB tracks a reviewed warning-count baseline in
  `config/validation/source-anomalies.json` for the exact 2026-09-18 Army
  snapshot. For downloader-dated snapshots at or after that baseline,
  `infinity-db build` and `normalize` allow known warning counts to decrease but
  reject new categories or counts above the reviewed ceiling before database
  export. The standalone `infinity-army` pipeline does not impose this
  project-specific baseline.

## Army identities, grouping, playability, and mercenary availability

### Current

An `army_lists` record represents an Army source/list identity. Its presence does
not by itself prove that the identity is independently playable.

Current source identity `901`, Non-Aligned Armies, is both an imported Army list
and the metadata parent of its associated child armies, but it is not selectable
as an independent army in InfinityDB. In the investigated source shape, metadata
records `901.parent = 900`, while child lists such as `902`, `904`, `905`, `908`,
and `909` point to parent `901`. Runtime classification therefore treats source-list
existence, hierarchy role, roster semantics, and application playability as
separate dimensions rather than assuming that a grouping identity is metadata-only.

The merger's current `army_lists.kind` value is derived rather than supplied as
a source taxonomy: a source document with a top-level `reinforcements` field is
labeled `army`, while a source document without that field is labeled
`reinforcement`. It therefore distinguishes the current ordinary-list versus
reinforcement-file shape, but does not distinguish main armies, sectorials, or
Non-Aligned forces.

Army metadata provides a separate faction hierarchy. Standard main armies are
self-parented metadata factions that also exist as imported ordinary army lists,
while their sectorials point to that playable main-army parent. A referenced
parent that is itself an imported ordinary list but is **not** self-parented is
a grouping node; a referenced metadata parent that has no imported army list may
also be surfaced as a grouping node. Children of either grouping shape receive
the `non_aligned` role. Reinforcement lists are excluded from this derivation and
are instead identified through the explicit top-level `reinforcements`
relationship on their ordinary army/sectorial source document. These
relationships are source evidence and are stronger than numeric-ID conventions.

The analyzed 2026-09-10 snapshot shows why source roster semantics must remain
separate from application playability. Source list `901` contains one standard
unit (Rumbler Spec-Ops) plus the complete 49-variant optional-mercenary pool,
while each child list contains its own standard roster plus a subset of that
mercenary catalogue:

| Army | Standard source units | Mercenary variants | Standard units represented in 901 logical pool |
| --- | ---: | ---: | ---: |
| 901 Non-Aligned Armies | 1 | 49 | 1 |
| 902 Druze | 37 | 42 | 21 |
| 904 Ikari | 38 | 45 | 16 |
| 905 StarCo | 35 | 42 | 15 |
| 908 Dahshat | 41 | 43 | 16 |
| 909 White Company | 46 | 38 | 19 |

Only Rumbler Spec-Ops is directly present as the same standard source ID in all
six lists. The larger logical overlap comes from standard child units whose
optional-mercenary variant is present in `901`. InfinityDB therefore preserves
the `901` source roster and its occurrence provenance even though `901` is
non-playable in the army selector/API filter contract.

Source canonical-faction ID `1` is materially different from 901. In the
investigated source snapshot, ID `1` has no army list, is used as the canonical
identity for mercenary-related unit records, and is not used as a normal unit
membership faction. InfinityDB does not map source ID `1` to `901` as ownership: normalization
preserves canonical source identity `1` while explicitly leaving its application
`main_army_id` unset. A separate curated display relationship derives
`display_army_id = 901` for presentation only.

Normal unit availability and optional mercenary availability are also distinct
source concepts. Ordinary unit records declare normal faction availability in
`factions`. The source additionally contains dedicated mercenary variants that
consistently use `canonical: 1`, an empty `factions` list, a `merc-...` slug, and
army-specific occurrences that supply optional mercenary availability. Many of
those records also use a 10,000-offset-style source ID, but that numeric pattern
is supporting evidence only and is not a semantic contract.

Normalization now validates that observed source contract and records it
explicitly. Source-defined units receive `units.source_role` with `standard` or
`mercenary_variant`; their army occurrences receive
`army_units.availability_kind` with `standard` or `mercenary`. A canonical-1
unit that still has declared ordinary faction memberships remains `standard`.
The classifier does not use the common 10,000-ID offset as its semantic rule,
and contradictory mercenary markers fail normalization rather than being
silently guessed.

Normalization also persists `genericUnitMatches` for standard,
non-reinforcement source records whose 10,000-family ID and ISC/display-name
identity provide an unambiguous duplicate match. Presence of that metadata is
authoritative even when the list is empty: database creation consumes the
persisted matches and does not rediscover additional generic groups through ID
arithmetic. Older normalized inputs without `genericUnitMatches` retain the
legacy arithmetic fallback inside the builder.

Mercenary identity remains a separate source-semantic contract. Database
creation consumes persisted `mercenaryUnitMatches` /
`unmatchedMercenaryUnitIds`; matched mercenary records join through their
recorded standard source unit, while explicitly unmatched variants remain
separate. Configured alias groups still come from the pinned identity policy.
During database creation, reinforcement-only source rows are audited against
standard logical groups using the same pinned word-alias policy. Unambiguous
results are persisted as `reinforcementUnitMatches` and feed the same
materialized logical-unit relation; an explicitly empty result keeps those
reinforcement records separate.

Mercenary availability has now completed the same read-path migration for
current normalized snapshots. Repository source occurrences carry
`army_units.availability_kind`, and `mercenary` occurrences require the `mercs`
filter while `standard` occurrences do not. Canonical faction `1` and declared
faction membership are no longer the authority for mercenary filtering when
explicit availability provenance is present. A legacy fallback retains the
previous canonical/faction inference only for database rows where
`availability_kind` is absent.

Canonical ownership, source identity, army grouping, army-list kind, optional
availability category, playability, and application logical identity are separate
semantics. The current normalized/database model exposes mercenary source role,
availability category, and audited identity evidence explicitly. Database
creation resolves configured aliases plus generic, mercenary, and reinforcement
evidence into one materialized logical-unit relation while retaining every source
row for provenance. The repository derives army role/playability from imported
metadata parent relationships and explicit reinforcement links, exposes that
source-derived contract through `/api/armies`, and consumes the materialized
logical-unit relation for unit reads. Clients must not infer logical identity from
numeric ID patterns.

### Current logical-unit materialization

Source ID `1` and grouping identity `901` are kept distinct in current
normalization. ID `1` remains source-side mercenary identity/provenance with no
application `main_army_id`, while Non-Aligned Army grouping is derived from the
metadata hierarchy generically; current source data happens to use metadata
identity `901` for that grouping node. The persisted `display_army_id` is a
separate presentation field derived from pinned curated display-identity data;
for the current reviewed relationship canonical source identity `1` displays as
army `901`.

The logical unit is an InfinityDB application abstraction rather than an Army
source object. Its identity is now materialized during frontend SQLite creation
while normalized/source records remain unchanged for provenance. The frontend
relation contains both identity and the first application-owned unit
payload/context layer:

```text
logical_units
  id                     application logical-unit ID
  representative_unit_id source unit used for canonical display/general data
  name
  isc
  isc_abbr
  slug
  canonical_faction_id
  main_army_id
  display_army_id

logical_unit_sources
  source_unit_id          original source-defined unit ID; one row per source unit
  logical_unit_id         owning application logical unit

logical_unit_aliases
  logical_unit_id
  source_unit_id
  field
  value

logical_unit_notes
  logical_unit_id
  source_unit_id
  note

logical_unit_spectables
  logical_unit_id
  source_unit_id
  spectables
```

Since schema version 11, `logical_units.id` equals `representative_unit_id`,
preserving existing unit URLs and API identifiers. Schema version 14 extends the
same row with representative-backed application fields and materializes the
source-attributed context tables above. The copied `canonical_faction_id`,
`main_army_id`, and `display_army_id` retain their relationship/context or
presentation semantics; residing on `logical_units` does not make them canonical
game-wide facts. Keeping the representative field explicit
allows a future application-owned logical ID without rewriting the source model.

Database creation resolves the relation from configured unit aliases in the
pinned identity policy, normalized `genericUnitMatches`, normalized
`mercenaryUnitMatches` / `unmatchedMercenaryUnitIds`, and the database-build
`reinforcementUnitMatches` audit. These remain evidence/provenance; the identity
rows are their resolved application mapping, while the canonical/context tables
materialize the accepted logical-unit payload boundary. The resolver combines
transitive relationships as graph components, selects a deterministic
representative, rejects invalid or contradictory references, and places
explicitly unmatched mercenary/reinforcement variants in independent logical
units.

The enforced invariants are:

- every source-defined unit belongs to exactly one persisted logical unit;
- every logical unit has exactly one representative source unit;
- source rows are never physically merged or rewritten by logical identity;
- profiles, loadouts, unit options, army occurrences, and availability provenance
  continue to reference their original source unit IDs;
- `army_units.availability_kind` remains source-occurrence provenance even when
  standard and mercenary occurrences resolve to the same logical unit and army;
- repository reads consume the materialized relation and do not repeat generic,
  mercenary, reinforcement, or alias identity resolution.

### Current `General profile` abstraction

`General profile` is an InfinityDB term; Infinity Army does not provide a
separate General-profile object. The current unit-detail browser synthesizes this
summary from source-backed profile/loadout data after optional army occurrences
have been enabled or disabled by the user's presentation settings.

The browser groups profiles by backend-derived `profile_identity`, selects the
most common stat, type, and classification values in each group, gathers shared
equipment and weapons, gathers profile-shared skills plus the skills of a single
matching loadout when exactly one exists, derives order/characteristic symbols,
and suppresses lower-priority duplicate-looking summaries. The result can
therefore change with the enabled army/availability contexts.

This makes `General profile` an InfinityDB abstraction implemented in the
presentation layer, not a source-native fact and not proof that any synthesized
value is invariant across the game. Before any `General profile` value is moved
into canonical storage or backend semantics, its supporting source facts and the
summary/presentation rule must be audited separately.

### Canonical application model and semantic deduplication

The materialized logical-unit relation answers:

> Which source unit records belong to the same application-level unit?

Canonical profile and loadout layers now additionally answer, conservatively:

> Which complete profile/loadout payloads can be reused within that logical unit,
> and which values must remain attached to a source/Army occurrence?

Unit-detail repository/API assembly consumes those canonical profile/loadout
payloads while retaining source occurrence context. Normal unit search,
skill/equipment/weapon filters, skill extras, and catalog reverse usage likewise
expand canonical payloads through their occurrence mappings. Source-local
relationships remain source-backed, while Army/faction identity/hierarchy and
skill/equipment/weapon catalog identity now serve through materialized
application layers. The application model remains progressively canonicalized,
but the normal-serving catalog/metadata overlap has been resolved.

InfinityDB is progressively introducing the remaining canonical application
model between the normalized source model and repository/API presentation.

```text
Infinity Army JSON
        |
        v
merged / normalized source model
  lossless, source-oriented, may be repetitive
        |
        v
canonical application model
  semantic identities + canonical facts + contextual deltas
        |
        v
repository / HTTP API
        |
        v
web presentation
```

#### Purpose

Canonicalization has two equal goals:

1. represent the same player-relevant fact once where equivalence can be proven;
2. make it possible to audit whether every distinct player-relevant fact reaches
   the application and web presentation.

Database-size reduction and query-performance improvements are useful possible
consequences, but are not the semantic criterion for performing a
deduplication.

#### Source structure is not application semantics

Normalized tables are intentionally derived from the structure of the Army JSON.
A normalized table, link row, occurrence row, position, or foreign key does not
by itself establish that Infinity Army contains an additional independent
player-facing datapoint.

For example, a nested source relationship may become a dedicated relational
table while the referenced model also appears through ordinary profile/loadout
records. The application-level audit must therefore trace the meaning of the
original source construct rather than count normalized tables or columns.

The relevant pipeline for completeness analysis is:

```text
original source construct
        |
        v
normalized representation
        |
        v
canonical application meaning
        |
        v
repository/API representation
        |
        v
web presentation
```

#### Semantic classification

During canonicalization, each source-backed value or relationship should be
classified according to its application meaning.

### Canonical fact

A fact that is invariant for the logical entity and can be stored once without
losing meaning. Examples may include invariant statistics, names,
classifications, or complete profile/loadout payloads proven identical across
source occurrences.

### Contextual fact or delta

A genuine variation that applies only in a particular army, sectorial,
availability mode, profile, loadout, or other context. Contextual differences
must remain explicit rather than being hidden by precedence rules or arbitrary
representative selection.

Examples may include army-specific AVA, points/SWC differences, availability
category, disabled status, or other source variations discovered during the
audit.

### Relationship

A meaningful association between canonical entities, such as an included model,
peripheral, dependency, Fireteam membership, or another gameplay relationship.
Normalization may represent the relationship separately from the entities it
connects. The relationship must be evaluated on its own player-facing meaning.

### Source/provenance fact

Information required to identify where a canonical fact or contextual delta
came from, but which is not itself normally player-facing. Examples include
source document identity, source row IDs, positions, hashes, and source
revisions.

### Normalization-only structure

Structure created because nested JSON was converted into relational data.
Normalization-only structure is not counted as an additional player-relevant
datapoint unless the original source relationship itself has independent
gameplay meaning.

These classifications are semantic rather than tied permanently to individual
columns. A field may prove canonical in one domain and contextual in another.

#### Invariants

Canonicalization must preserve all of the following:

- every source-defined record remains recoverable from the lossless source/raw
  layers;
- every canonical application record can be traced to one or more supporting
  source occurrences;
- no genuine source variation is discarded merely because most occurrences are
  identical;
- army membership and `army_units.availability_kind` remain explicit source
  provenance;
- canonicalization never depends solely on numeric-ID conventions;
- current curated identity rules remain pinned and reproducible;
- normalization warnings and source anomalies remain visible rather than being
  silently resolved by deduplication;
- application identity must not imply source ownership, playability, or
  availability unless those semantics are independently established;
- equivalent presentation does not prove equivalent source semantics;
- deduplication must not prevent reconstruction or auditing of the source
  evidence that produced the application record.

#### Exact equality before semantic equivalence

The initial profile/loadout implementation stages deduplicated only records whose
complete application-relevant payloads were exactly equal after contextual
identity and provenance fields had been deliberately excluded. Remaining
canonicalization work keeps the same evidence-first rule unless a broader
semantic equivalence is explicitly established.

This is intentionally conservative.

Records must not be merged merely because they have:

- the same or similar name;
- the same profile or option number;
- similar statistics;
- related source IDs;
- the same visible browser rendering;
- an apparent generic/mercenary/reinforcement relationship that has not already
  been established through maintained identity evidence.

When non-identical records appear to represent the same logical concept, the
difference must first be classified. It may be:

- a genuine contextual delta;
- provenance;
- a normalization artifact;
- redundant source representation;
- an upstream inconsistency;
- or evidence that the records should remain separate.

Only after that distinction is understood should a broader canonicalization
rule be introduced.

#### Initial empirical baseline

The frontend database built from the Army snapshot acquired on 2026-09-18
contains substantial exact repetition even under a conservative comparison of
complete profile/loadout payloads and their nested gameplay content.

Profiles:

- 5,020 stored profile occurrences;
- 1,479 distinct complete payloads when deduplicated only within each source
  unit;
- 3,541 repeated occurrences, approximately 70.5%;
- 1,430 distinct payloads when existing materialized logical-unit identity is
  also taken into account;
- 3,590 repeated occurrences, approximately 71.5%.

Loadouts:

- 12,993 stored loadout occurrences;
- 4,210 distinct complete payloads when deduplicated only within each source
  unit;
- 8,783 repeated occurrences, approximately 67.6%;
- 4,067 distinct payloads when existing materialized logical-unit identity is
  also taken into account;
- 8,926 repeated occurrences, approximately 68.7%.

These figures are investigative evidence, not database invariants. Snapshot
contents will change, and the canonical schema must not depend on these
particular counts.

They demonstrate that useful semantic deduplication can begin with exact
equality rather than heuristic matching.

#### Current baseline audit

`tools/audit_semantic_deduplication.py` is the read-only development audit for
this first exact-equality stage. It operates on an already-built frontend
`infinity.db`; it does not modify the database or participate in normal runtime
queries.

A normal summary can be generated with:

```text
python tools/audit_semantic_deduplication.py data/generated/infinity.db \
  --output reports/semantic-deduplication.json
```

Add `--details` when investigating duplicate groups. Detailed output adds every
repeated payload fingerprint and its source occurrence keys; the normal report
keeps the same deterministic summary and field contract without the much larger
group listing.

The baseline comparison deliberately defines its payload fields explicitly.
Schema drift in any audited table fails the audit until the new field is
classified rather than being silently ignored or silently changing equality.

For profile payloads, the top-level semantic fields are:

- `name`, `logo`, `type_id`;
- `move_1`, `move_2`, `cc`, `bs`, `ph`, `wip`, `arm`, `bts`, `vitality`,
  `silhouette`, `ava`, `is_structure`, and `notes`.

The profile payload also includes the ordered nested content from:

- `profile_characteristics`;
- `profile_skills` and `profile_skill_extras`;
- `profile_equipment` and `profile_equipment_extras`;
- `profile_weapons` and `profile_weapon_extras`;
- `profile_includes`;
- `profile_peripherals`.

For loadout payloads, the top-level semantic fields are `name`, `points`, `swc`,
`minis`, and `disabled`. The payload also includes the ordered nested content
from:

- `option_characteristics`;
- `option_orders`;
- `option_skills` and `option_skill_extras`;
- `option_equipment` and `option_equipment_extras`;
- `option_weapons`, resolved through `option_weapon_templates`, together with
  `option_weapon_extras`;
- `option_includes`;
- `option_peripherals`.

Parent identity and occurrence/provenance fields are not payload identity:
`army_id`, `unit_id`, `group_id`, `profile_id` / `option_id`, occurrence IDs,
template IDs, and literal `position` values are excluded. Nested rows and extras
are still read in `position` order, so changing their relative order changes the
payload even though the absolute position numbers do not.

Valid JSON in `raw` fields is parsed before hashing so whitespace and object-key
order do not manufacture false differences. Unknown/unmodeled `raw` content
remains part of the payload, preserving conservative equality.

The first pass intentionally retains referenced catalog IDs and
`target_group_id` / `target_option_id` values as semantic content. Those
relationships may later become canonical references, but the baseline does not
guess equivalence before the referenced identities are audited.

`profile_groups` and wider unit/army context are outside the profile/loadout
payload itself. They remain contextual data for subsequent classification rather
than being silently folded into this equality definition.

The audit reports both:

- distinct payloads within each source unit; and
- distinct payloads within each materialized logical unit.

The second view measures the additional exact repetition exposed by the existing
logical-unit identity relation. Both are diagnostics for the selected snapshot,
not compatibility requirements or expected constants.

#### Profile semantic classification audit

`tools/audit_profile_semantics.py` performs the next read-only evidence pass for
profile canonicalization. It compares repeated Army occurrences of the same
source profile key:

```text
(unit_id, group_id, profile_id)
```

That key is an **observational comparison key**, not a proposed canonical
application identity. It is useful because the source repeats the same
unit/group/profile identifiers across army lists, allowing the audit to isolate
which values actually change with army context before InfinityDB invents a new
profile identity.

The report is deterministic and can be written with:

```text
python tools/audit_profile_semantics.py data/generated/infinity.db \
  --output reports/profile-semantics.json
```

The 2026-09-18 frontend database contains:

- 5,020 profile occurrences;
- 1,137 distinct source profile keys;
- 698 source profile keys repeated in more than one army, covering 4,581
  occurrences;
- 306 repeated source profile keys whose complete baseline payload varies by
  army context.

The 306 varying keys separate into progressively clearer categories:

- excluding AVA reduces the count from 306 to 26, so AVA is the sole difference
  for 280 repeated source profile keys;
- excluding the three observed army-specific logo variations reduces 26 to 23;
- treating absolute `display_order` values as presentation context and treating
  omitted quantity versus explicit quantity `1` as equivalent **for diagnostic
  comparison only** reduces 23 to 16;
- the remaining 16 consist of one genuine WIP variation, 11 genuine
  characteristic-set variations, and four genuine skill-set variations.

The diagnostic quantity normalization is evidence of source-representation
duplication, not yet an application rule. InfinityDB still preserves the exact
source distinction until the canonical-profile design explicitly decides how
omitted and explicit default values are represented.

##### Profile fields

The current classification is:

| Field | Classification | Current evidence / treatment |
| --- | --- | --- |
| `army_id` | source/provenance | Identifies the owning Army occurrence; never canonical profile identity. |
| `unit_id` | source/provenance | Identifies the original source unit. |
| `group_id` | source/provenance | Source-local profile-group identity. |
| `profile_id` | source/provenance | Source-local profile identity. |
| `position` | normalization-only | Generated from source array order; preserve relative order where needed, not the literal ordinal as profile identity. |
| `name` | canonical fact candidate | No variation across repeated occurrences of the same source profile key. |
| `logo` | contextual delta | Three source profile keys have army-specific logo values; this is presentation context, not gameplay identity. |
| `type_id` | relationship | Relationship to the troop-type catalog; no same-source-key variation observed. |
| `move_1` | canonical fact candidate | No same-source-key variation observed. |
| `move_2` | canonical fact candidate | No same-source-key variation observed. |
| `cc` | canonical fact candidate | No same-source-key variation observed. |
| `bs` | canonical fact candidate | No same-source-key variation observed. |
| `ph` | canonical fact candidate | No same-source-key variation observed. |
| `wip` | contextual delta | One source profile key varies by army context, affecting four occurrences. |
| `arm` | canonical fact candidate | No same-source-key variation observed. |
| `bts` | canonical fact candidate | No same-source-key variation observed. |
| `vitality` | canonical fact candidate | No same-source-key variation observed. |
| `silhouette` | canonical fact candidate | No same-source-key variation observed. |
| `ava` | contextual delta | 297 source profile keys vary by army context, affecting 909 occurrences. |
| `is_structure` | canonical fact candidate | Determines Wounds-versus-Structure interpretation; no same-source-key variation observed. |
| `notes` | canonical fact candidate, unproven | Present in the source model but unpopulated in this snapshot; retain until populated evidence exists. |

“Canonical fact candidate” means the current snapshot supplies evidence that the
field can be shared for one source-profile concept. It does **not** mean the
schema may assume permanent invariance. A later snapshot may introduce a
contextual variation in any source-provided field, and canonicalization must
fail visibly or preserve a delta rather than discard it.

##### Profile groups

`profile_groups` remains context outside the profile payload. Across repeated
source group keys `(unit_id, group_id)`, the current snapshot shows no variation
in `position`, `category_id`, `isc`, or `notes`; `notes` is entirely unpopulated.

The fields are classified as follows:

- `army_id`, `unit_id`, and `group_id` are source/provenance;
- `position` is normalization-only array ordering;
- `category_id` is a relationship to the category/classification catalog;
- `isc` is a profile-group display fact;
- `notes` is a retained but currently unpopulated group fact.

This observed stability does not move profile-group context into canonical
profile identity. Group membership and grouping remain explicit occurrence
context until their own identity is designed.

##### Nested profile relationships

The normalized occurrence tables contain both meaningful relationships and
source/normalization mechanics. Common fields are treated as follows:

- parent `army_id` / `unit_id` / `group_id` / `profile_id` columns are
  source/provenance;
- `occurrence_id` is a normalization-only surrogate;
- `position` is a normalization-only ordinal preserving source array order;
- catalog `item_id`, `characteristic_id`, and `extra_id` values are semantic
  relationships;
- `display_order` is source presentation context. In the current profile data it
  never changes relative item ordering, although its absolute number can differ;
- `quantity` is a semantic relationship attribute. Current profile skill and
  equipment data only uses explicit quantity `1`; omission versus explicit `1`
  accounts for several otherwise-identical source representations;
- `raw` is source/provenance fallback for malformed or unmodeled content. It is
  currently null throughout the populated profile reference/include tables, but
  any future non-null value must block destructive canonicalization until the
  unmodeled content is understood;
- extra-row `position` is normalization-only ordering while `extra_id` is the
  semantic relationship.

Observed relationship behavior is:

| Relationship | Rows | Raw same-source variants | Variants after diagnostic representation normalization | Interpretation |
| --- | ---: | ---: | ---: | --- |
| characteristics | 15,011 | 11 | 11 | Genuine contextual relationship differences. |
| skills | 26,823 | 10 | 4 | Four genuine contextual skill-set differences; six are representation-only. |
| equipment | 2,629 | 1 | 0 | The only difference is representation-only. |
| weapons | 10 | 0 | 0 | No same-source-profile variation observed. |
| includes | 2 | 0 | 0 | Relationship is rare but must remain explicit. |
| peripherals | 0 | 0 | 0 | Supported by the model but absent from profile-level data in this snapshot. |

The diagnostic normalized relationship view removes absolute `display_order`
values and treats omitted quantity and explicit `1` as equivalent while
preserving relative row/extras ordering. It exists to identify source-encoding
duplication; it does not rewrite normalized data.

##### Design consequence

A canonical profile model must therefore separate at least three concerns:

1. a reusable profile payload containing invariant profile facts and stable
   relationships;
2. an occurrence/context layer retaining Army membership, source keys,
   profile-group membership, AVA, presentation context, and genuine contextual
   gameplay differences;
3. source provenance sufficient to reconstruct and audit every original
   occurrence.

The 16 residual contextual variants demonstrate why canonicalization cannot be
implemented as “pick one representative profile row and discard the rest.”
Conversely, the large AVA-only and representation-only populations demonstrate
that preserving every full source payload in the application model is also
unnecessary.

##### Current profile-payload materialization

Schema version 12 materializes reusable **profile payloads** as derived frontend
structure while retaining every normalized/source profile row unchanged. This
does not introduce a new global semantic profile identity. A payload remains
scoped to one existing `logical_unit`; two unrelated units are not merged merely
because their profile data happens to be identical.

The implementation deliberately stops at exact application-payload equality. It
does not factor every army-specific gameplay difference into fine-grained field
deltas. This keeps the first migration mechanically provable and leaves broader
semantic equivalence for later evidence-driven work.

For the 2026-09-18 database, the audited payload boundary gives:

- 5,020 source profile occurrences;
- 1,163 distinct candidate payloads when scoped by source unit;
- 1,108 distinct candidate payloads when scoped by materialized logical unit;
- 55 additional duplicate payloads exposed by existing logical-unit identity;
- 3,912 repeated occurrences represented by those 1,108 logical-unit payloads,
  approximately 77.93% of stored profile occurrences.

`tools/audit_profile_semantics.py` reports these values under `candidateModel`.
They remain snapshot diagnostics, not schema constants.

###### Payload boundary

The initial reusable payload contains the exact current values of:

- `name`, `type_id`, `move_1`, `move_2`, `cc`, `bs`, `ph`, `wip`, `arm`, `bts`,
  `vitality`, `silhouette`, `is_structure`, and `notes`;
- characteristics, preserving their relative order;
- skills plus extras;
- equipment plus extras;
- weapons plus extras.

Skill/equipment/weapon payloads initially preserve exact `display_order`,
`quantity`, `raw`, and relative ordering. The audit has shown some
`display_order` and omitted-versus-`1` quantity differences to be
representation-only in the current snapshot, but that diagnostic normalization
is **not** promoted into the first storage contract. Those records remain
separate payloads until application behavior and source meaning justify a
normalization rule explicitly.

The following stay outside the reusable payload:

- `army_id`, `unit_id`, `group_id`, and `profile_id` — source/provenance keys;
- profile `position` — occurrence ordering/context;
- `ava` — army-contextual gameplay data;
- `logo` — observed army-contextual presentation data;
- profile-group `category_id`, `isc`, `notes`, and group ordering — profile-group
  context;
- `profile_includes` — references to army/unit-local loadout identities;
- `profile_peripherals` — references to army-local peripheral identities.

Includes and peripherals are intentionally deferred because their numeric target
identities are contextual. They remain losslessly available through the current
source tables until the related entities have canonical identities of their own.
They must not be dropped merely because they are outside the first reusable
payload.

The 16 residual contextual variants identified by the classification audit are
therefore handled conservatively: WIP, characteristic, or skill differences
produce **different payloads**. Only AVA, logo, source identity, ordering, and
the deferred context-local relationships are separated from the payload in this
first model. A later layer may group multiple payload variants under a stronger
semantic profile identity, but that is not required for the first migration.

###### Derived application tables

The materialized application-side shape is:

```text
profile_payloads
  id                  internal deterministic payload row ID
  logical_unit_id     owning application logical unit
  payload_sha256      SHA-256 of versioned canonical payload serialization
  name
  type_id
  move_1 / move_2
  cc / bs / ph / wip / arm / bts
  vitality / silhouette / is_structure
  notes

profile_payload_occurrences
  army_id
  unit_id
  group_id
  profile_id
  profile_payload_id
  position
  ava
  logo

profile_payload_characteristics
profile_payload_skills
profile_payload_skill_extras
profile_payload_equipment
profile_payload_equipment_extras
profile_payload_weapons
profile_payload_weapon_extras
```

`profile_payload_occurrences` is one-to-one with the current source `profiles`
rows. Its composite source key remains `(army_id, unit_id, group_id,
profile_id)` and references exactly one reusable payload. The source `profiles`
and nested source tables remain unchanged for provenance and lossless auditing.

The nested payload tables use payload-relative ordering rather than copying the
source `occurrence_id` surrogate into the canonical layer. Extras remain linked
to the specific payload relationship occurrence. This keeps normalization-only
source identifiers out of application identity while preserving ordered
relationship meaning.

`payload_sha256` is a deterministic fingerprint of a versioned canonical JSON
serialization of the reusable payload. Payload equality is still scoped by
`logical_unit_id`; the hash does not authorize merging identical payload bytes
across unrelated logical units. Materialization compares the serialized payload
when coalescing rows and rejects an in-scope hash collision rather than treating
the hash as independent semantic evidence. Structured `raw` fallback JSON is
stored canonically in the derived layer; the source/raw layers retain its exact
original representation.

The integer `profile_payloads.id` is an internal database key, assigned
deterministically from the sorted `(logical_unit_id, payload_sha256)` set for a
build. It is not a public API identifier and is not promised stable across
snapshots when source payloads change.

###### Build and read-path invariants

The materializer and database validation enforce all of the following:

- every source profile occurrence maps to exactly one `profile_payload`;
- every payload has at least one supporting source occurrence;
- the occurrence's source unit maps to the same `logical_unit` that owns the
  payload;
- identical candidate payloads inside one logical unit reuse one payload row;
- WIP, characteristics, skills, equipment, weapons, extras, `raw`, and exact
  representation values remain distinct whenever they differ;
- AVA and logo retain their source occurrence values rather than being selected
  from a representative row;
- profile-group context remains attached through the source occurrence key;
- includes and peripherals remain available through their existing contextual
  source relationships until their own canonicalization stage;
- current source and raw tables are not rewritten or made lossy;
- non-null `raw` fallback content participates in payload equality and can never
  be silently discarded;
- canonical-profile IDs remain internal and must not leak into public URLs or
  API contracts during this migration.

Repository unit-detail profile assembly now consumes
`profile_payload_occurrences -> profile_payloads` and the nested payload tables
while retaining army/profile-group context from the occurrence/source side. The
public profile object shape, ordering, AVA handling, display-name normalization,
and merged logical-source behavior are intentionally unchanged.

The lossless `profiles` and nested `profile_*` source tables remain in the
frontend database for provenance, validation, and contextual relationships that
have not yet been canonicalized. Normal catalog reverse usage now expands the
canonical profile/loadout occurrence layers instead. `get_unit()` no longer uses
those source payload rows to assemble its
profile objects. This is a staged read-path migration rather than permission to
remove the source representation.

Behavioral regression coverage preserves the existing unit/API expectations and
also verifies that mutating the legacy source profile payload rows after
materialization does not change unit-detail profile output. The migration was
accepted only after representative and production-scale before/after comparison
showed identical serialized `get_unit()` results.

The remaining query-time profile merge is now explicitly an **occurrence merge**,
not payload deduplication. A logical unit can contain overlapping source records
for the same effective army occurrence and source-local group/profile coordinates
where one source contributes nested relationships that another omits. Canonical
`profile_payload_id` is therefore deliberately too strict to serve as that
occurrence identity.

`get_unit()` collapses such source occurrences only when their effective army
occurrence, group/profile IDs, scalar profile facts, troop type, and
profile-group classification agree. Nested skills, equipment, weapons, and
characteristics are then accumulated without repeated visible items. The only
direct source-context value merged after a match is AVA: when comparable
non-negative numeric values disagree, the more restrictive value is retained.
Different availability-category occurrences remain separate, and scalar
profile/stat/classification differences remain separate.

This source-occurrence merge remains necessary until InfinityDB has stronger
explicit identity evidence for those overlapping source profile occurrences. It
must not be replaced merely by canonical payload identity or by source-local
profile IDs.

#### Loadout semantic classification audit

`tools/audit_loadout_semantics.py` performs the corresponding read-only evidence
pass for loadout canonicalization. It compares repeated Army occurrences of the
same source loadout key:

```text
(unit_id, group_id, option_id)
```

As with the profile audit, that key is an **observational comparison key**, not
an application identity. It was used to inspect which values really change
between Army contexts before the canonical loadout boundary was selected, and
remains useful as a diagnostic comparison key for later snapshots.

Run the audit with:

```text
python tools/audit_loadout_semantics.py data/generated/infinity.db \
  --output reports/loadout-semantics.json
```

For the 2026-09-18 frontend database, the audit reports:

- 12,993 loadout occurrences;
- 3,593 distinct source loadout keys;
- 2,162 source loadout keys repeated in more than one Army, covering 11,562
  occurrences;
- 130 repeated keys whose complete conservative payload varies by Army context;
- 125 varying keys after diagnostic normalization of absolute `display_order`
  and omitted-versus-explicit quantity `1`;
- 26 varying keys when army-local peripheral IDs are compared through their
  referenced peripheral definition (`name` + `mercs`) instead of raw local IDs;
- 21 varying keys when both diagnostic normalizations are applied.

Those final 21 variations are disjoint in the current snapshot: two points
variations, one SWC variation, one order-generation variation, two skill
variations, eight weapon variations, and seven peripheral-context variations.
They were the evidence used to select the conservative materialization boundary
documented below; they are not permission to normalize the remaining
differences away.

The peripheral result is particularly important. Peripheral IDs are army-local,
so direct cross-army comparison exaggerates semantic variation: 111 repeated
source loadout keys differ when raw peripheral IDs are compared, but only seven
still differ after resolving each ID to the referenced peripheral definition.
The 104 collapsed cases are therefore local-identity/provenance differences,
not evidence of different peripheral names or roles. The remaining seven all
involve the same `TURTLEMEK` name with an Army-context difference in the
peripheral definition's `mercs` value. This was a diagnostic comparison, not an
identity rule. The later dedicated Peripheral audit separates `mercs` as source
context and treats name only as a grouping candidate pending reviewed entity
mapping.

##### Loadout fields

The current classification is:

| Field | Classification | Current evidence / treatment |
| --- | --- | --- |
| `army_id` | source/provenance | Identifies the owning Army occurrence. |
| `unit_id` | source/provenance | Identifies the original source unit. |
| `group_id` | source/provenance | Source-local profile-group identity. |
| `option_id` | source/provenance | Source-local loadout identity. |
| `position` | normalization-only | Generated from source option-array order; 67 repeated source keys change literal position. |
| `name` | canonical fact candidate | No variation across repeated source loadout keys. |
| `points` | contextual delta | Two repeated source keys vary by Army context, affecting 16 occurrences. |
| `swc` | contextual delta | One repeated source key varies by Army context, affecting two occurrences. |
| `minis` | canonical fact candidate | No same-source-key variation observed. |
| `disabled` | canonical fact candidate | No same-source-key variation observed. |

“Canonical fact candidate” has the same conservative meaning as in the profile
audit: the current snapshot supports reuse, but later source variation must fail
visibly or become explicit context rather than being discarded.

##### Nested loadout relationships

Normalized relationship rows mix gameplay meaning with source and
normalization mechanics. Their common field semantics are:

- parent `army_id` / `unit_id` / `group_id` / `option_id` columns are source
  provenance;
- `occurrence_id`, weapon `template_id`, and literal `position` values are
  normalization-only identities/order bookkeeping;
- catalog `item_id`, `characteristic_id`, and `extra_id` values are semantic
  relationships, except that peripheral `item_id` is only army-local;
- `display_order` is presentation context, not entity identity;
- `quantity` is a relationship attribute. The audit treats omitted quantity and
  explicit `1` as equivalent only in its diagnostic normalized view;
- `order_type`, `list_count`, and `total_count` are order-generation relationship
  attributes;
- `target_group_id` / `target_option_id` identify a source-local include
  relationship;
- `raw` is source/provenance fallback for malformed or unmodeled content and
  must continue to block destructive canonicalization until understood.

Observed relationship behavior is:

| Relationship | Rows | Extras | Raw same-source variants | After representation normalization | Interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
| characteristics | 0 | — | 0 | 0 | Supported by the model but absent from loadouts in this snapshot. |
| orders | 15,195 | — | 1 | 1 | One genuine Army-context order-generation difference. |
| skills | 6,330 | 1,594 | 2 | 2 | Two genuine contextual skill/extra differences. |
| equipment | 2,798 | 457 | 1 | 0 | The only same-source variation is representation-only. |
| weapons | 52,554 | 11,526 | 12 | 8 | Four differences are representation-only; eight retain source-shape/content differences for later classification. |
| includes | 949 | — | 0 | 0 | Stable for repeated source loadout keys, but the target remains source-local. |
| peripherals | 818 | — | 111 | 111 | Raw army-local IDs differ widely; resolving the target definition reduces this to seven contextual variants. |

The weapon source also contains one non-null raw fallback template (`{}`),
referenced by 95 normalized weapon occurrences. The conservative comparison
retains that fallback exactly; the loadout canonicalizer must not infer that an
anonymous/empty source object is safely discardable merely because nearby
weapon rows look redundant.

The classification audit itself intentionally stopped before selecting the
canonical loadout payload boundary. That separation keeps the evidence report
independent from the application rule chosen afterward. The implemented boundary
below keeps points/SWC and deferred source-local relationships outside the
payload while retaining exact order/skill/equipment/weapon representation inside
it; the audit's diagnostic normalizations still do not become application rules.

#### Canonical loadout payload materialization

The accepted first loadout migration boundary mirrors the conservative profile
model: deduplicate exact reusable application payloads **within an existing
`logical_unit`**, while keeping source/Army occurrence context explicit. It does
not introduce a new global semantic loadout identity, and identical payload
bytes from unrelated logical units do not authorize a merge.

The first model deliberately stops at exact payload equality. It does not turn
the diagnostic display-order or omitted-versus-`1` quantity normalization into
an application rule, and it does not attempt to factor every nested gameplay
difference into sparse deltas. Genuine or representational differences inside
the selected payload boundary therefore continue to produce separate payload
variants.

For the 2026-09-18 database, this boundary gives:

- 12,993 source loadout occurrences;
- 3,574 distinct candidate payloads when scoped by source unit;
- 3,448 distinct candidate payloads when scoped by materialized logical unit;
- 126 additional duplicate payloads exposed by existing logical-unit identity;
- 9,545 repeated occurrences represented by those 3,448 logical-unit payloads,
  approximately 73.46% of stored loadout occurrences;
- 16 repeated source-loadout identities still split into more than one candidate
  payload because their selected nested payload content differs exactly.

`tools/audit_loadout_semantics.py` reports these values under `candidateModel`.
They are snapshot diagnostics, not schema constants.

##### Payload boundary

The initial reusable loadout payload contains the exact current values of:

- `name`, `minis`, and `disabled`;
- characteristics, preserving their relative order;
- generated orders, including `order_type`, `list_count`, `total_count`, and
  retained `raw` fallback content;
- skills plus extras;
- equipment plus extras;
- weapons plus extras.

Skill/equipment/weapon payloads initially preserve exact `display_order`,
`quantity`, `raw`, and relative ordering. The classification audit has shown
some of those differences to be representation-only, but, as with canonical
profiles, that diagnostic normalization is **not** promoted into the first
storage contract. The one equipment representation variant and four weapon
representation variants therefore remain distinct payloads in this first model.

The following stay outside the reusable payload:

- `army_id`, `unit_id`, `group_id`, and `option_id` — source/provenance keys;
- loadout `position` — source occurrence ordering/context;
- `points` and `swc` — Army-contextual player-facing costs with observed
  same-source variation;
- profile-group membership/classification — context inherited from the source
  occurrence;
- `option_includes` — references to source-local loadout coordinates;
- `option_peripherals` — references to army-local peripheral identities.

Points and SWC are separated explicitly rather than forcing their three observed
Army-specific cost differences to create otherwise duplicate payloads. By
contrast, orders, skills, equipment, and weapons remain in the reusable payload:
when those gameplay relationships differ, the first canonical model represents
that as a distinct payload variant rather than inventing a finer-grained delta
system prematurely.

Includes and peripherals remain losslessly available through the source tables
until their target entities have stronger canonical identities. In particular,
the diagnostic peripheral comparison by `name + mercs` is evidence that raw
army-local IDs overstate variation; it is **not** yet sufficient to define a
canonical peripheral key. The seven remaining peripheral-context variations,
including `TURTLEMEK` `mercs` differences, must therefore remain explicit source
context.

The 16 candidate-payload variants among repeated source-loadout keys are retained
conservatively: one exact equipment representation variant, one order-generation
variant, two skill/extra variants, and twelve weapon variants. No one of those
is discarded or rewritten merely because most occurrences agree.

##### Derived application tables

The materialized application-side shape is:

```text
loadout_payloads
  id                  internal deterministic payload row ID
  logical_unit_id     owning application logical unit
  payload_sha256      SHA-256 of versioned canonical payload serialization
  name
  minis
  disabled

loadout_payload_occurrences
  army_id
  unit_id
  group_id
  option_id
  loadout_payload_id
  position
  points
  swc

loadout_payload_characteristics
loadout_payload_orders
loadout_payload_skills
loadout_payload_skill_extras
loadout_payload_equipment
loadout_payload_equipment_extras
loadout_payload_weapons
loadout_payload_weapon_extras
```

`loadout_payload_occurrences` is one-to-one with the current source
`loadout_options` rows. Its composite source key stays `(army_id, unit_id,
group_id, option_id)` and references exactly one reusable payload. The
source `loadout_options` and nested `option_*` tables remain unchanged for
provenance, lossless auditing, deferred relationships, and migration comparison.

Nested payload tables use payload-relative ordering instead of carrying
normalization-only source `occurrence_id` or weapon `template_id` identities into
the canonical application layer. Extras remain attached to their specific
payload relationship occurrence. The one currently non-null weapon raw fallback
(`{}`), referenced by 95 source occurrences, remains part of exact payload
equality and must not be silently inferred away.

As with profiles, `payload_sha256` fingerprints a versioned canonical JSON
serialization while equality remains scoped by `logical_unit_id`. Materialization
compares serialized payload content before coalescing hash matches and fails
visibly on an in-scope collision. Internal integer payload IDs are assigned
deterministically from the sorted logical-unit/fingerprint set and must not become
public API or URL identities.

##### Build and read-path invariants

The materializer and database validation enforce the storage/provenance portion
of the following contract. Repository unit-detail loadout assembly now consumes
the canonical payload/occurrence layer while preserving the existing visible
shape and logical-source merge behavior:

- every source loadout occurrence maps to exactly one reusable loadout payload;
- every payload has at least one supporting source occurrence;
- the source unit and payload belong to the same materialized logical unit;
- exact candidate payloads within one logical unit reuse one payload row;
- points and SWC remain attached to their exact source occurrence;
- order, skill, equipment, weapon, extra, `raw`, and exact representation
  differences continue to split payloads;
- profile-group context, includes, and peripherals remain recoverable from the
  occurrence/source side;
- source `loadout_options` and nested `option_*` rows remain lossless and
  reconstructable;
- no army-local peripheral ID is promoted to cross-Army canonical identity by
  this migration;
- `get_unit()` loadout assembly reads `loadout_payload_occurrences`,
  `loadout_payloads`, canonical orders, and canonical skill/equipment/weapon
  relationships rather than the corresponding source payload rows;
- logical-source occurrence merging remains separate from canonical payload
  identity, so overlapping source records with the same visible occurrence can
  still contribute complementary nested relationships;
- source `loadout_options` and `option_*` tables remain available for
  provenance, deferred relationships, and validation, but normal search/filter/
  catalog reverse usage now expands canonical payload occurrences instead.

The read-path migration preserves the existing public loadout object shape,
ordering, points/SWC context, order formatting, nested item accumulation, and
logical-source merge behavior. Regression coverage also mutates/removes the old
source loadout payload rows after materialization and verifies that unit-detail
output remains unchanged. The migration was accepted only after serialized
`get_unit()` output for all 920 source-defined unit IDs in the audited production
database was byte-for-byte identical before and after the read-path switch.

The remaining query-time loadout merge is an **occurrence reconciliation**, not
canonical payload deduplication. In the audited production database, 31 visible
loadout keys each reconcile exactly two logical-source occurrences (62 source
occurrences total). All 31 pairs already reference the same canonical
`loadout_payload_id`; no current merge combines distinct canonical payload
variants.

The merge nevertheless retains effective Army occurrence, source-local
`group_id`/`option_id`, name, points, SWC, minis, and disabled state in its key.
Distinct source options can legitimately reuse one canonical payload, so payload
identity alone is not occurrence identity. Nested items continue to be appended
uniquely when overlapping source occurrences reconcile, preserving the robust
source-overlap behavior without treating the merge itself as payload
canonicalization.

Secondary measurements on the same 2026-09-18 production snapshot confirm the
expected storage benefit while also exposing a read-path indexing requirement:

- the legacy lossless loadout tables plus their indexes occupy about 5.54 MiB;
- the canonical loadout payload/occurrence tables plus their indexes occupy about
  2.04 MiB, approximately 63.1% less for the corresponding application model;
- while both representations coexist during migration, this is not yet a net
  database-size saving; the physical benefit is realized only after source-only
  tables move to `infinity.raw.db`;
- before unit-oriented canonical-occurrence indexes were added, a diagnostic pass
  over all 920 source-unit `get_unit()` lookups took about 12.3-12.5 seconds on
  the acceptance environment, versus about 6.5-6.7 seconds for the preceding
  source-loadout read path;
- adding the loadout occurrence index restored approximately legacy performance
  (about 6.7-6.9 seconds), and indexing both canonical profile and loadout
  occurrence tables reduced the same diagnostic pass to about 3.0 seconds.

Those timings and byte counts are snapshot/environment diagnostics, not release
performance guarantees or schema invariants. Query-plan regression tests require
the canonical occurrence tables to use their unit-oriented indexes because unit
detail assembly filters them by source unit.

Canonical include/peripheral identities, representation normalization, and
eventual movement of lossless source-only tables to `infinity.raw.db` remain
separate evidence-driven decisions.

### Logical-unit payload semantic classification audit

The next canonicalization layer is the unit-level payload itself. A deterministic
read-only audit now compares every source-defined `units` row inside each
materialized `logical_unit`, together with unit-faction memberships, Army
occurrences, and top-level `unit_options`. Run it with:

```text
python tools/audit_unit_semantics.py path/to/infinity.db --output unit-semantics.json
```

On the production snapshot downloaded 2026-09-18, 920 source-defined units map
to 737 logical units. The source-count distribution is 570 singletons, 152
pairs, 14 triples, and one four-source logical unit. The 167 multi-source logical
units therefore account for 350 source-unit rows. Of the non-representative
source rows, 133 are reinforcement-only records, 49 are mercenary variants, and
one is another standard source representation.

The existing representative rule is strong enough to be considered explicit
semantic policy rather than an accidental implementation detail: all 737
representatives in the audited snapshot are ordinary `standard` source units,
and none is reinforcement-only or a mercenary variant. Canonical unit display
fields may therefore be based on the already-reviewed representative source
rule, but that rule does **not** authorize discarding differing source facts.

Field evidence across the 167 multi-source logical units is:

| Unit field | Classification | Repeated logical units with variation | Audit conclusion |
| --- | --- | ---: | --- |
| `id` | source/provenance | 167 | Original source identity; never a payload fact. |
| `id_army` | source/provenance | 166 | Source `idArmy` varies heavily and remains provenance. |
| `canonical_faction_id` | relationship/context | 136 | Source canonical-faction relationship varies across reinforcement/mercenary representations. |
| `main_army_id` | derived relationship/context | 124 | Every repeated logical unit with a non-null value varies; logical display may follow the representative rule. |
| `display_army_id` | presentation context | 136 | Source-specific display derivation varies; canonical display may follow the representative rule. |
| `isc` | representative-backed canonical fact | 132 | Canonical display value may come from the representative; alternate values remain search/provenance context. |
| `isc_abbr` | representative-backed canonical fact | 29 | Same rule as `isc`; only 36 repeated logical units contain any abbreviation. |
| `name` | representative-backed canonical fact | 131 | Canonical display value may come from the representative; alternate source names remain significant context. |
| `slug` | representative-backed canonical fact | 167 | Every multi-source logical unit has source slug variation. |
| `notes` | contextual delta | 6 | Genuine player-facing source-specific notes exist and must not be replaced by one representative value. |
| `spectables` | canonical candidate, unproven across variants | 0 | 30 source units contain data, but all belong to singleton logical units; cross-source invariance is not demonstrated. |
| `source_defined` | source/provenance | 0 | Distinguishes imported source rows from normalization placeholders. |
| `source_role` | source/provenance | 49 | Standard versus mercenary-variant representation is occurrence provenance. |
| `relation_reference_count` | relationship summary | 6 | Derived summary of source relations; underlying relationships are audited separately. |

The label differences are mostly source representation rather than evidence for
separate logical identity, but not universally so. Using only the database-pinned
identity normalization as a diagnostic, `name` variation falls from 131 logical
units to 38 after reinforcement-prefix removal and to 10 after full unit-identity
normalization. `isc` falls from 132 to 13 and then 7; `isc_abbr` falls from 29 to
12 and remains 12. These transformations are **matching evidence only**. They do
not rewrite canonical display strings or justify dropping alternate labels.

That distinction mattered directly to the read-path migration. Before the
canonical logical-unit layer became authoritative for display/search, the
repository used representative `name`/`isc`/`isc_abbr`/`slug` values while search
terms were the union of labels from every source row. All 167 multi-source logical units
contribute at least one alternate general label beyond the representative, 467
non-empty source labels in total in this snapshot. One additional source row has
no name and contributes the repository's derived `Unit 1662` fallback search
term. The canonical alias layer therefore preserves 468 distinct logical-unit
search values rather than relying on the source `units` rows at query time.

Notes provide a concrete losslessness/completeness case. Six logical units have
different source notes. Four of them (`657`, `659`, `1550`, and `1567`) have a
non-representative reinforcement note while the representative note is null. The
current `get_unit()` response exposes only the representative note, so these four
source note deltas are not currently reachable through unit detail. Canonical
unit design must preserve them explicitly and the later web-app completeness pass
must decide how to present them.

Unit relationships remain contextual rather than being folded into the canonical
unit row:

- source `unit_factions` membership sets differ in all 167 multi-source logical
  units; the logical-unit declared-faction view is an aggregate over those source
  relationships, not a replacement for them;
- `army_units` rows remain source/Army occurrences carrying position, filters,
  and `availability_kind`;
- top-level `unit_options` are also source-unit payload/context rather than simple
  unit facts. The snapshot contains 18 rows across nine source units / seven
  logical units. Two logical units have options on multiple source records: the
  SCARFACE pair is an exact repeat, while EQUIPE MIRAGE-5 has the same option and
  nested orders/includes but a genuine points difference (`60` versus `51`).
  The comparison uses `(logical_unit_id, option_id)` only as an observational key;
  `option_id` remains source-local and is not established canonical identity.

Thirty source units contain non-null `spectables`, but none belongs to a
multi-source logical unit and the repository currently does not consume this
field. It therefore remains a canonical-unit payload candidate with insufficient
variant evidence and a likely 1.0 presentation gap to resolve rather than data
that may be discarded. Top-level `unit_options` likewise require an explicit
overlap/presentation decision because their complete source meaning is not
currently returned by unit detail even though parts are used for search and
catalog reverse lookup.

The audit establishes the following design constraints for the next step:

- representative-backed general display values may be materialized under the
  existing deterministic representative rule, but source canonical-faction,
  `main_army_id`, and display-faction values remain contextual/derived or
  presentation semantics rather than canonical game-wide relationships;
- alternate source names/ISC/abbreviations/slugs must remain searchable and
  traceable;
- source-specific notes remain explicit deltas rather than being silently
  replaced by the representative note;
- source canonical-faction/main/display derivations, `unit_factions`, Army
  occurrences, availability, and top-level unit options remain contextual;
- `spectables` must be preserved while its canonical/presentation treatment is
  decided; and
- `relation_reference_count` is not a canonical fact; the underlying
  relationships, not the summary count, are the semantic object to audit.

### Canonical logical-unit payload/context design

**Current materialization.** Introduced in schema version 14, InfinityDB materializes one
application-owned row per existing logical unit without copying the complete
source `units` row. The canonical row is representative-backed, while source
labels and player-facing source deltas remain explicit context.

The materialized application boundary is:

```text
logical_units
  id
  representative_unit_id
  name
  isc
  isc_abbr
  slug
  canonical_faction_id
  main_army_id
  display_army_id

logical_unit_sources
  source_unit_id
  logical_unit_id

logical_unit_aliases
  logical_unit_id
  source_unit_id
  field                  name | isc | isc_abbr | slug
  value

logical_unit_notes
  logical_unit_id
  source_unit_id
  note

logical_unit_spectables
  logical_unit_id
  source_unit_id
  spectables
```

`logical_units` therefore owns the current representative-backed general
display/application values and carries compatibility copies of contextual or
presentation faction fields used by existing reads. Those copied fields do not
become canonical game-wide relationships merely because they reside on the
application-owned row. The representative source remains explicit provenance;
its selection does not turn the representative's entire source row into canonical
truth.

Alternate labels are stored when a non-representative search/display value
differs from the corresponding canonical field. For `name`, this includes the
existing derived `Unit <source id>` fallback when the source name is absent;
otherwise the alias value is the non-empty source field value. The source ID and
field name remain on the alias row rather than collapsing aliases into an
unattributed search-term set. On the audited production snapshot this produces
473 alias occurrences across all 167 multi-source logical units, representing
468 distinct `(logical_unit, value)` search terms.

Notes do not belong on the canonical logical-unit row. Every non-empty source
note remains attached to the source occurrence that supplied it. The production
snapshot contains 30 note occurrences across 28 logical units and 28 distinct
`(logical_unit, note)` facts. This preserves both exact duplicate source
evidence and the four currently hidden non-representative-only notes without
asserting that a source-specific restriction applies universally.

`spectables` is likewise kept off the canonical row for the first
implementation. The 30 current payloads are preserved exactly with
logical/source attribution. Because all 30 occur only on singleton logical
units, there is no evidence yet for either canonical promotion or cross-source
deduplication. Treat the payload as opaque until its schema and presentation
semantics are audited.

Top-level `unit_options` and their nested relationships also remain separate
source-context payloads. The first logical-unit materialization must not infer
cross-source option identity from `option_id`, and the observed `60` versus
`51` points difference for EQUIPE MIRAGE-5 must remain representable. A later
dedicated audit may canonicalize repeated option payloads if there is enough
evidence, but that is not part of the canonical logical-unit row.

Source-specific faction/main/display derivations, `unit_factions`, and
`army_units` remain deferred relationship context. The canonical row carries
the representative-backed values needed by current list/detail presentation,
while the subsequent relationship audit owns the lossless model for the
source-specific relationships.

The version-3 unit semantics audit emits this model directly. A clean schema-14
rebuild from the stored 2026-09-18 normalized source reproduces:

- 737 canonical logical-unit rows;
- 920 source links;
- 473 alternate-label occurrences / 468 distinct logical-unit alias values;
- 30 source-note occurrences across 28 logical units;
- 30 exact source-context `spectables` occurrences; and
- 18 top-level `unit_options` rows left as source-context payloads.

These counts are acceptance evidence for the audited snapshot, not permanent schema
cardinalities. Future source variation must be represented explicitly rather
than forced into the current counts. Database validation checks that canonical
fields still equal the representative source and that the alias, note, and
`spectables` context is complete relative to the retained source rows.

#### Next implementation targets

Canonical unit/profile/loadout payloads, their context mappings, application Army
identity/hierarchy, application catalog identity, and the audited runtime read
migrations were completed and released in 0.6.1 on 2026-09-20. The representative
runtime benchmark, local/hosted acceptance, release tag, deployment, and deployed
update verification are complete. Milestone 2B now covers broader relationships,
source-only structures, the eventual `infinity.raw.db` split, and 1.0 completeness.

### 0.6.1 runtime benchmark evidence

The release benchmark compares the 0.6.0 implementation with the 0.6.1 canonical
runtime pass on the same production-like Army snapshot, host, benchmark cases, and
iteration counts (20 cold / 200 warm per case). Across the 13 representative read
paths, the geometric mean of cold medians improved by **2.33%**. Army listing
improved by **43.94%**, Army-filtered unit listing by **11.68%**, plain unit listing
by **3.57%**, and Trait detail by **4.67%**. The geometric mean of cold p95 timings
was effectively flat at **+0.52%**. The small Traits-list path increased from a
1.92 ms to 2.87 ms cold median, so its large percentage change is not treated as a
standalone release blocker.

The same benchmark records `infinity.db` growing from **13,557,760 bytes** to
**18,108,416 bytes** (**+33.56%**). That is an accepted interim tradeoff for 0.6.1:
canonical application layers are now materialized while the source/context rows
required for provenance and still-unmigrated semantics are retained. The later
physical `infinity.raw.db` separation owns removal of source-only duplication; the
0.6.1 semantic acceptance criterion remains correctness and losslessness, not
storage reduction.

### 0.6.1 runtime serving-surface inventory

`tools/audit_runtime_database_surface.py` traces SQLite column reads with
SQLite's authorizer API while exercising every Army-database method called
directly by the web application, `SkillCatalog`, or `TraitCatalog`. Each probe
uses a fresh repository instance so method caches cannot hide dependencies.
`Database.validate()` is deliberately excluded: validation may inspect retained
lossless source tables without making them normal serving dependencies. The tool
also scans the runtime Python modules for direct `Database` calls and fails if a
new serving method is not represented by the probe plan.

The initial compatibility-21 trace of the reviewed 2026-09-18 snapshot covered
25 serving probes and read **62 tables / 230 distinct table-field pairs**. That
baseline identified 43 replaceable fields across 16 source tables in addition to
the genuine semantic-overlap work.

After migrating the replaceable source reads and moving Army/faction serving onto
the materialized application Army layer, the compatibility-23 trace covered
**49 tables / 192 distinct table-field pairs**. The subsequent catalog-identity
migration in compatibility revision 24 keeps the same 25 serving probes and 49
runtime tables while reading **196 distinct table-field pairs** because the
materialized catalog identity/provenance rows are now explicit runtime inputs. All
**43 replaceable source fields across 16 tables remain absent from normal serving**:
unit search labels come from the canonical logical-unit/profile/loadout layers;
skill/equipment/weapon filters and reverse catalog usage expand canonical payload
rows back through their occurrence maps; source-specific unit display names are
reconstructed from canonical logical-unit fields plus explicit name aliases.
Top-level `unit_option_*` occurrences stay source-contextual by design.

The current role totals are **111 canonical-application fields**, **62 explicit
contextual-application fields**, and **23 intentional-source fields**. The
application Army tables now provide canonical identity/hierarchy and reviewed
source mappings, while `application_catalog_items` /
`application_catalog_sources` provide canonical application catalog identity and
source-label provenance for Skills, Equipment, and Weapons.
`army_lists.id`/`kind` remain intentional source representation only for the
legacy API shape and reinforcement fallback. `metadata_factions`,
`metadata_skills`, and `metadata_equipment` are no longer read by normal
serving. **196 / 196 observed fields have no open semantic issue**.

`army_units`, `profile_groups`, profile/loadout occurrence maps, logical-unit
aliases/notes/source links, `metadata_ammunitions`, and `metadata_weapons` are
recorded as explicit contextual application data. `unit_factions` is classified in the same runtime
role because it remains source-backed relationship data, but semantically it is
the broader game-wide declared-membership relation rather than Army-local
availability. Top-level `unit_options` and their
skill/equipment/weapon occurrences remain intentional source-context data under
the previously accepted logical-unit design; they are not assumed redundant
with profile/loadout payloads.

The trace is equally useful for scope control. Normal serving currently does
**not** read Fireteam tables, relation/dependency tables, profile/loadout
includes or peripherals, `logical_unit_spectables`, or the other source-only
collections outside the traced surface. Those structures remain important to
Milestone 2B / 1.0 completeness, but they do not block 0.6.1 unless later work
introduces a runtime dependency on them.

The production counts above are evidence for this code/snapshot pair, not a
permanent table-count contract. The audit fails on an unclassified newly-read
table or an unprobed direct repository method so future runtime expansion becomes
an explicit semantic decision.

### Army/faction semantic boundary audit

The 0.6.1 army/faction audit treats Infinity Army and InfinityDB as different
scopes. Infinity Army exposes one concrete army/list at a time. InfinityDB must
retain those list-local occurrences while also representing identities and
relationships across the whole game. A source list is therefore not the same
thing as a game-wide faction identity, ownership relation, or declared unit
membership.

In semantic-provenance terms, the source list/metadata projections and their
membership/occurrence relationships are source-native evidence; current
role/playability and `main_army_id` are source-derived InfinityDB semantics; the
materialized canonical application army identity/hierarchy is an InfinityDB
abstraction; and display-army selection remains a presentation convenience.
Those categories must remain visible even when several concepts share IDs or
names.

On the reviewed 2026-09-18 snapshot, `army_lists` and `metadata_factions` each
contain 58 source IDs. Their ID sets are identical and every matching `name` /
`slug` pair is equal. That overlap is real, but the source constructs still carry
different semantics: `army_lists` owns roster/list context and the explicit
ordinary-list `reinforcement_id` relationship, while `metadata_factions` owns
hierarchy plus metadata such as `discontinued` and `logo`. The configured Army
alias `998 -> 999` reduces those 58 source list identities to **57 application
army identities**. The current derived application roles are **10 main, 30
sectorial, 5 non-aligned, 1 grouping, and 11 reinforcement** identities; 56 are
selectable and grouping identity 901 is not.

Reinforcement ownership must not be inferred from `metadata_factions.parent`.
All 12 reinforcement metadata rows point at parent IDs that are not themselves
metadata identities in this snapshot. By contrast, all 46 ordinary source lists
carry an explicit reinforcement link, resolving to 11 canonical reinforcement
identities after the 998/999 alias. The ordinary-list reinforcement relationship
is therefore the stronger source evidence for application semantics.

The normalized `factions` table is a broader game-wide identity registry than
the Army-list set. It contains 63 identities: the 58 list identities plus source
IDs `1`, `203`, `903`, `906`, and `907`, which are referenced by canonical-faction
or declared-membership data without a current Army list. This distinction is
material rather than theoretical. `unit_factions` contains 2,094 declared
memberships, while `army_units` contains 4,137 concrete list occurrences. For
89 source units, declared faction membership is a strict superset of current
standard Army-list availability: 99 extra membership references point to IDs
203, 903, 906, or 907, and there are **zero** standard Army occurrences missing
from the corresponding declared membership sets. Reducing `unit_factions` to
`army_units` would therefore erase cross-army/historical relationships that are
useful specifically because InfinityDB has a game-wide scope.

`army_units` remains explicit list-local availability context, including
`availability_kind`; current production data has no null availability-kind rows.
`unit_factions` remains a separate game-wide declared-membership relation. Source
`units.canonical_faction_id` is likewise separate: it represents source
canonical/origin context and can point to identities without an Army list (IDs 1
and 903 in this snapshot). It is not sufficient evidence for playability, Army
membership, or application ownership.

The reviewed application Army abstraction was introduced in schema version 15 /
compatibility revision 23 without rewriting either source projection:

```text
application_armies
  id                     canonical application Army ID
  name                   player-facing canonical name
  slug                   player-facing canonical slug
  role                   derived main/sectorial/non-aligned/grouping/reinforcement role
  playable               derived application selectability
  group_id               canonical application grouping/main parent where applicable
  preferred_source_id    source identity preferred for name/slug provenance

application_army_sources
  application_army_id    owning canonical application Army
  source_army_id         source identity reconciled into that Army
  has_army_list          whether the source identity has an `army_lists` projection
  has_metadata           whether it has a `metadata_factions` projection

application_army_reinforcement_parents
  reinforcement_army_id  canonical reinforcement Army
  parent_army_id         canonical ordinary Army that explicitly links to it
```

The layer is an InfinityDB abstraction, not a new upstream object. Name/slug
selection uses deterministic preferred-source provenance after reviewed Army
aliases are applied. Role, playability, grouping, and reinforcement-parent
relations are source-derived from the overlapping Army-list/metadata evidence
described above. Source list rows, metadata rows, `army_units`, `unit_factions`,
and source canonical-faction values remain unchanged and traceable; the broader
63-ID faction registry is not collapsed into application Army identities.

Normal Army/faction serving now consumes these materialized rows. `/api/armies`,
Army filtering, unit list/detail Army names and faction/group presentation, reviewed
source aliases, playability, and reinforcement-parent grouping all resolve through
the application layer. `army_units` still supplies concrete list availability and
`unit_factions` remains the broader game-wide declared-membership relation. The
legacy `army_lists.kind` source-shape field remains exposed for compatibility and
as a reinforcement fallback where an explicit parent relationship is unavailable.

### Relationship audit after entity canonicalization

Re-evaluate includes, peripherals, dependencies, relations, Fireteams, and
similar structures after the entities they reference have stable canonical
identities.

The audit must distinguish:

- the existence of a related entity;
- the relationship between entities;
- repeated presentation of that entity elsewhere;
- and normalization-only relational structure.

A relationship is not automatically redundant merely because both endpoint
entities are already visible in the UI.

#### Current Milestone 2B relationship evidence

The read-only audits against the 2026-09-18 Army snapshot establish a clean
starting point without yet changing runtime schema. Include targets resolve
completely through the canonical loadout/profile occurrence layer: 2/2 profile
includes, 949/949 loadout includes, and 35/35 shared unit-option includes resolve
with no missing targets, raw fallbacks, cross-logical-unit targets, or ambiguous
shared targets. The resolved profile/loadout includes point to 1 and 101 distinct
canonical target payloads respectively. This is sufficient evidence to design
canonical include relationships without inventing target identity.

Peripherals require a separate boundary. The same snapshot has 279 army-local
definitions / 56 names and 818 resolved loadout attachments, with no profile
attachments and no definition-only rows. All 279 definitions are referenced by at
least one loadout attachment. Forty-one names span multiple raw identities and
three names vary in source `mercs` context. Most importantly, 22 repeated
canonical loadout payloads have different semantic Peripheral attachment
signatures (32 differ when representation/context fields are included). Therefore
Peripheral attachment cannot yet be moved blindly onto the canonical loadout
payload, and name remains only a diagnostic grouping candidate until the separate
reviewed source-to-Peripheral identity/profile mapping is defined.

Controller eligibility is not represented by these Army relationships and must
enter through reviewed curated rules data. The current design for that rules side
is documented in `docs/peripheral-curated-data-design.md`.

### Application catalog identity and metadata context

`application_catalog_items` and `application_catalog_sources` are InfinityDB
abstractions. Infinity Army does not provide one upstream object that corresponds
to an InfinityDB application catalog item after reviewed aliases and equivalent
numeric/parameterized source labels have been combined.

The materializer currently uses these source inputs:

- normalized `skills`, `equipment`, and `weapons` catalog rows;
- `metadata_skills`, `metadata_equipment`, and `metadata_weapons` enrichment;
- reviewed catalog alias groups from `config/identity/source-identities.json`.

For each public catalog, explicit reviewed alias groups take precedence. Remaining
source rows are grouped only by the existing deterministic label rules used by the
application: numeric skill variants share the label with the numeric component
removed, while Equipment/Weapon labels additionally allow the text before a
colon to define the shared identity. The configured canonical ID is retained for
reviewed groups; otherwise the lowest source ID in the proven-equivalent group is
used as the current internal application key. The player-facing name is derived
from the representative source label using the corresponding merge rule.

This derivation creates application identity; it does **not** erase source
context. `application_catalog_sources` retains every contributing source ID and
source label plus whether matching metadata existed. Skill/Equipment wiki fields
and Weapon category are representative-backed application fields. Detailed
Weapon modes, ammunition, ranges, traits, Equipment-style weapon profiles, and
other mode-specific values remain in `metadata_weapons` and are joined as
contextual detail rather than flattened into catalog identity.

The abstraction is deliberately limited to Skills, Equipment, and Weapons used
by the current runtime. It does not claim that two source records are globally
identical outside the documented grouping rule, does not canonicalize curated
rules knowledge, and does not turn source metadata modes into one invariant fact.

#### Application domain slugs

Schema version 17 / compatibility revision 25 adds a derived
`application_domain_slugs` registry for `armies`, `units`, `skills`, `equipment`,
and `weapons`. Numeric application IDs remain implementation keys, while each
registry row records a normalized candidate and one of three states:

- `resolved`: the candidate is non-empty and unique within the domain, so `slug`
  receives that value;
- `collision`: two or more application identities normalize to the same candidate,
  so `slug` remains null and the conflict requires an explicit reviewed decision;
- `unavailable`: no usable candidate can be derived, so `slug` remains null.

Candidates are deterministic lowercase ASCII identifiers with single hyphen
separators. Collision handling is deliberately fail-closed: the application does not
generate positional `-2`/`-3` suffixes whose meaning could change with source order
or a later snapshot. The registry is application-owned derived data and therefore
does not replace Army/source slugs or provenance IDs. Source/application display
slugs may seed a candidate where useful, but they are not thereby promoted to a
permanent public identity.

Repository lookup can translate a `resolved` slug to/from the current numeric
application key. Existing public API/web routes remain numeric until a later
migration defines per-domain slug freezing, aliases/redirects, and compatibility
behavior. The current 2026-09-18 snapshot resolves all 1,042 initial identities
(57 Armies, 737 logical Units, 88 Skills, 28 Equipment items, and 132 Weapons)
without collision or unavailable candidates; these counts are evidence only.

Curated/application concepts that need an explicit namespace use typed IDs such as
`skill:doctor`. Curated v3 records now validate that the prefix matches the record
kind and that every colon-separated segment follows the same slug grammar. Source
numeric IDs remain provenance/foreign references rather than public identity.

#### Relationship to version 1.0.0 completeness

Semantic deduplication is an investigative path toward the 1.0.0 requirement,
not a requirement that every source table be physically minimized before 1.0.

For each source construct encountered during this work, record whether its
player-relevant meaning is:

- explicitly presented;
- implicitly represented by another presented structure;
- operationally consumed without direct presentation;
- redundant with another source representation;
- normalization-only structure;
- or currently unrepresented in the application.

An item becomes a 1.0 completeness gap when distinct player-relevant information
cannot be accessed through the web application. Repetition in the normalized
source model alone is not a completeness defect.

Conversely, the fact that an entity appears somewhere in the UI does not prove
that all useful relationships involving that entity are represented.

#### Non-goals

This work does not:

- rewrite the acquired Army JSON;
- make the normalized source model lossy;
- merge records based on superficial similarity;
- eliminate provenance to reduce database size;
- require every canonicalization opportunity to be completed before 1.0;
- require specialized final-form UI for every newly identified datapoint;
- include ITS-specific data in the 1.0 scope.

The work may change the frontend database schema, repository assembly, and API
contracts where that produces a clearer canonical application model. Such
changes must use the normal database compatibility/versioning process and carry
regression coverage proving that meaningful source variation is preserved.

Legacy duplicate matching is now a build-compatibility concern. When older
normalized inputs lack the persisted generic or mercenary evidence, database
creation can use the retained legacy fallback before writing the materialized
relation. Every newly built frontend database therefore exposes the same
logical-unit contract regardless of which compatibility path produced it.

Normal availability derived from declared `factions` and optional mercenary
availability derived from mercenary source variants remain distinguishable even
when they occur for the same logical unit and army. The repository now consumes
that explicit normalized availability category. The legacy canonical/faction
inference remains only for compatibility with database rows that lack explicit
availability provenance and can be removed when that compatibility is no longer
required.

Army role/playability is now explicit at the repository/API boundary. Metadata
parent relationships provide main-army, sectorial, and Non-Aligned grouping;
explicit `reinforcements` links provide reinforcement parentage. Grouping
identity `901` is surfaced as non-playable when its imported child lists are
present, and the browser selector consumes `role`/`playable` instead of Army-ID
ranges. Its imported 50-unit source roster remains preserved but is not exposed
as a separate selectable/queryable roster; application unit availability comes
from the playable child NA2 occurrences. Logical-unit consolidation is now a
database-build concern rather than army playability or query-time generic/
reinforcement matching.

## Principle

The merged master layer is lossless and source-oriented. The normalized layer
is query-oriented. Database-specific choices should live in exporters/adapters
rather than in source parsing.

## SQLite storage

`infinity_db.database` imports every normalized table with its original field
names, declared primary keys, and foreign keys. Nested arrays and objects use
JSON text. The frontend `infinity.db` contains only queryable columns. Its
sibling `infinity.raw.db` contains `__infinity_raw_rows`, preserving each exact
normalized record (including absent versus null fields) for development use.
Both databases retain `__infinity_metadata`; the schema defines empty frontend
tables so API queries do not depend on a particular snapshot containing every
kind of record. The metadata also stores the validated source-identity
configuration and its canonical hash copied from normalized provenance, making
the identity policy part of the immutable database snapshot and allowing
tampering, incomplete provenance, or conflicting explicit export policy to fail
validation.

When an Army database is built from a ZIP snapshot, normalized `_meta` and both
database siblings retain `snapshotArchiveSha256`: the SHA-256 of that exact ZIP.
Deployment compares it with the terminal symbol manifest's
`snapshot.armyArtifact.sha256`, binding the runtime data and symbol publication
without needing the raw archive at deployment time.

`units.source_role` and `army_units.availability_kind` are explicit frontend
schema fields rather than incidental dynamic columns. This makes the
normalization-time availability classification part of the generated database
contract; repository mercenary filtering consumes `availability_kind` directly
for current snapshots.

Frontend-only application-Army identity/provenance tables, `logical_units`,
`logical_unit_sources`, logical-unit alias/note/`spectables` context, and
canonical profile/loadout payload tables are derived application structure, not
normalized source facts, and therefore do not rewrite the source tables.
Repository unit queries map a requested source or representative ID through
`logical_unit_sources`; list/search/detail general
fields and unit-label search aliases come from the canonical logical-unit layer,
while source-backed Army/relationship context that has not yet been canonicalized
continues to use its reviewed source/context tables. The normal Army/faction and
Skill/Equipment/Weapon metadata-overlap boundaries were resolved by the 0.6.1 read
migrations. The normalized-input table registry remains separate from these
derived frontend tables so generated application structure cannot be supplied as normalized
source data.

`PRAGMA application_id` identifies an InfinityDB file and `PRAGMA user_version`
records its schema version. The current schema version is 17 and the application
compatibility revision is 25. Imports build temporary sibling files, check
database integrity, then replace the destinations. Incompatible schemas or
compatibility revisions require a rebuild from normalized JSON for now. The
frontend export runs `ANALYZE` after loading and indexing data, preserving SQLite
planner statistics in the immutable snapshot.

**Design direction:** while canonicalization is in progress, `infinity.db`
intentionally contains both derived application tables and lossless normalized
source tables needed by remaining runtime/provenance paths. After canonical unit,
relationship, and catalog coverage is complete, source/provenance-only normalized
tables should move exclusively to `infinity.raw.db`. Normal repository/API/web
serving should then require only the self-contained canonical `infinity.db`
(alongside `rules.db` and assets), with `infinity.raw.db` retained as a build and
audit artifact. The split must preserve canonical-to-source traceability and is
not justified by file-size reduction alone.

## Snapshot provenance and human annotations

### Current

Timestamped `JSON`, `WIKI`, and `SYMBOLS` ZIP files are immutable acquisition
artifacts. Each successful downloader run also writes one version-1 `InfinityDB
snapshot provenance` JSON record under `data/manifests/snapshots/`, labeled
from the archive filename and bound to the archive SHA-256.

The generated manifest has this logical shape:

```text
format / formatVersion
snapshot:
  type
  archive:
    name
    sha256
    path?          # project-relative POSIX form only
  acquiredAt       # timezone-aware ISO-8601
  documentCount
source:
  url
  language?        # Army snapshots
inputArtifact?     # current symbol acquisition input
  name
  sha256
  path?            # project-relative POSIX form only
```

The archive SHA-256 is authoritative snapshot identity. Archive filenames and
paths are labels/provenance and may change independently. Paths are omitted when
the corresponding file is outside the project root so generated provenance
never embeds machine-specific absolute paths. Loading a manifest can re-hash an
archive and reject mismatches.

Manifest JSON is serialized deterministically. A second write of identical
provenance for the same manifest label is idempotent; different provenance for
that label is rejected. Reacquiring identical bytes under a different archive
label may create another record with the same authoritative SHA-256. Generated
manifests are ignored by Git, excluded from Docker build context, and not
automatically pruned.

Corvus Belli's Army `metadata.json` remains source data. It is distinct from
InfinityDB-owned acquisition provenance.

### Army source revision interpretation

Army list and reinforcement JSON documents carry a top-level Corvus Belli
`version` string such as `7.26246.158`. InfinityDB preserves that value exactly
as source provenance. It is **not** the InfinityDB snapshot identity and must not
be treated as a snapshot-wide release number.

Historical Army captures strongly indicate that the middle numeric component
concatenates a two-digit year with a non-zero-padded ordinal day of year. For
example, `7.26246.158` and `7.26246.159` both encode 2026 day 246, which is
2026-09-03; older observed values such as `7.26147.195`, `7.2668.375`, and
`7.25288.295` line up with 2026 day 147, 2026 day 68, and 2025 day 288
respectively. The final component appears to distinguish source data
revisions/builds on that date. The exact Corvus Belli semantics are
undocumented, so this parsing is an evidence-backed InfinityDB interpretation
rather than an upstream contract.
Code must preserve and compare the raw string even if a parsed interpretation is
shown to humans.

A coherent Army snapshot may legitimately contain more than one source data
revision. The 2026-09-10 and 2026-09-18 acquisitions both contained 36 documents
at `7.26246.158` and 22 at `7.26246.159`; all 58 Army/reinforcement documents and
`metadata.json` were byte-identical between those acquisitions. The split is
stable by faction family rather than by sequential download position. Snapshot
coherence therefore cannot be established by requiring one `version` value
across every document.

The Army JSON downloader establishes acquisition coherence with two complete API
passes. The first pass validates metadata and every Army/reinforcement response
without publishing loose files. The second pass re-fetches the same metadata and
source endpoints and requires each response to be byte-identical to its first-pass
response. Any mismatch aborts the acquisition before the immutable archive or
provenance manifest is created and reports the changed filename together with the
first- and second-pass SHA-256 values. Successful runs report the observed raw
source-revision counts diagnostically; mixed revisions are not themselves an
error.

When dates or versions are reported, keep these concepts distinct:

- **snapshot acquisition date/time** — InfinityDB provenance from
  `snapshot.acquiredAt` and the immutable archive/hash;
- **Army source data revision** — the raw per-document Corvus Belli `version`,
  optionally interpreted as its apparent source date plus revision/build.

For example, describe the current material as an Army snapshot acquired on
2026-09-18 containing source revisions `7.26246.158` and `7.26246.159`, rather
than assigning either revision to the snapshot as a whole.

Human-authored snapshot annotations use a separate version-1 `InfinityDB
snapshot note` contract under `data/curated/snapshot-notes/`. Each note requires
`snapshotSha256`, a human description, and an ordered `notableChanges` array; an
optional `compareToSha256` may identify a different comparison snapshot.
Acquisition tools never create, rewrite, or delete these curated notes.

Snapshot notes are not rules-database inputs and do not become runtime
application data. The current contract is a source-controlled annotation format
and validation boundary only.

`army-symbol-build.json` is separate generated build state. Standalone raw symbol
acquisition writes version 2. The orchestrated structural SVG preflight promotes
that state to version 3 after verifying the exact `SYMBOLS` archive, its snapshot
provenance, and each member hash. Version 3 adds a preflight status/summary and a
SHA-256-bound report artifact. Installed-font audit then promotes the same state
to version 4 with available/missing/ambiguous/generic effective-font summaries,
its generated report identity, and the exact tracked font-alias configuration
identity. Exact-first visual duplicate detection then promotes the same state to
version 5. Version 5 records renderer settings, duplicate-report identities,
summary counts, total source/canonical loose-SVG byte sizes, reclaimed bytes, and
a complete portable `archivePath -> canonical archivePath` mapping while retaining
the original `assets` and `references` arrays unchanged. The SHA-bound duplicate
summary report additionally records percentage reduction. Canonical text
conversion promotes passed or failed conversion state to version 6 with
converter identity/jobs, conversion counts, and SHA-bound detailed/summary
reports. A passed conversion materializes one canonical work tree containing
converted active-text representatives plus unchanged no-text representatives;
failed conversion does not replace an existing canonical tree. Balanced
display-aware compression then promotes passed version-6 state to version 7.
Version 7 records canonical/compressed counts and byte totals, production
compression settings, and SHA-bound `compression-report.csv`,
`compression-candidates.csv`, and `compression-run.json` identities. The balanced
compression report also records the SHA-256 of every canonical output SVG. The derived
compressed work tree contains exactly the canonical asset set and is replaced only
after validation succeeds. Final publication verifies those per-file hashes before
promoting passed version-7 state to version 8. Version 8 records published/mapping
counts and byte totals and binds `publication-map.json`, the generated
`symbol-inventory.json`, `army-symbols.js`, and `unit-symbol-map.js`. The inventory
contains every published SVG path and SHA-256 and is the completeness contract for
local/full-asset validation; browser mappings intentionally describe only the
currently consumed subset. The report contains complete source-archive and
canonical-archive mappings to published paths, published SVG hashes, and a
comparison against the previous generated publication
covering added, removed, changed, and unchanged symbols. Removed prior symbols are
retained in a timestamped `data/backups/symbols/` backup whose manifest records their
original published paths and SHA-256 values. Detailed reports live under
`data/reports/symbols/`.
Loaders continue to accept versions 2 through 8 so prior immutable symbol caches
and completed intermediate processing states remain readable/valid; version-5
manifests produced before size accounting remain valid for compatibility. Stage
promotion itself is forward-only: each successful stage advances from its defined
source version, and failed-stage retry is handled explicitly instead of demoting
later passed state. Version 8 is terminal published state.

### Design direction

Future snapshot-comparison tooling may emit generated diff/report data while
curated snapshot notes remain the human interpretation. The later
`army-symbol-build.json` processing manifest is a separate build-specific
contract and is not represented by acquisition manifests.

## PDF- and wiki-derived rules storage

### Current

Curated facts from user-supplied rules PDFs and wiki research pass through the
source-controlled JSON contract in `data/curated/rules/`. Raw PDFs and wiki
snapshots are never accepted as application inputs.

The available source families include N5 core rules revisions, N5 FAQs, ITS
seasons, historical rules, and wiki research. Core rules yield reusable rule
identities and structured effects; FAQs yield dated rulings; ITS material is
isolated by season; wiki material supplies discovery, aliases, and cross-links.
Historical documents must not be silently merged into current rules.

The current curated-v3 document has collection identity, source records, typed
fact records, maintained vocabularies, scope, Army links, related-record links,
review state, and source-specific citations. PDF sources record the local
reviewed file, Corvus Belli source URL, publication date, and page count; PDF
citations require positive printed page numbers. Archived wiki sources record
the exact timestamped ZIP path/hash, acquisition timestamp, language, document
count, and wiki base URL; citations use archive members. Exact pinned wiki
revisions remain URL-backed sources with a retrieval date.

`vocabularySources` uses the same source-specific locator rules, so wiki
vocabulary references no longer carry artificial printed-page values. The
checked-in v5.3 collection is bound to the English 2026-09-18 wiki snapshot
(`WIKI-en 20260918-130233.zip`, SHA-256
`aa407f1959fbaafce98058acf507640cc94bfc2690d4a7519a547caf1492f23a`).

`infinity-db build-rules` defaults to `data/curated/rules/` and stores those
curated facts in a separate SQLite database rather than either Army-derived
database. Directory ingestion skips `example.json`. Other curated subtrees are
not rules-database inputs. The rules database has an independent schema,
application ID, compatibility version, and replaceable snapshot lifecycle; its
current schema and compatibility versions are both 2.

A curated rule fact may reference stable application-level identities, but
neither database is an import source for the other; any combined view is
assembled by application code.

Trait identity is one implemented example of that composition boundary. Army
metadata stores raw trait labels and usage, while current curated `trait` records
own canonical names, aliases/misspellings, parameterized source-label prefixes,
concise summaries, and citations. The application joins those sources at read
time; the Army database does not copy curated trait knowledge into its snapshot.

Skill declaration categories are another application-level composition. Army-derived
`skills` and their usage remain source data, while current curated
`skill-declaration-category` records carry the N5 declaration label, deterministic
display order, Army skill links, and printed-page citation. `SkillCatalog` joins
those records at read time and keeps uncited `Unclassified` as the fallback for
skills without a curated declaration. The Army database does not materialize these
rules facts.

Skill parameter interpretation follows the same source/curated split. The imported
Army `extras.type` field determines whether an extra is a distance; this source
semantic is preserved into the frontend database and drives `is_distance` in
repository responses. Curated `skill` records may additionally carry
`facts.parameterSemantics` for rule-derived display behavior such as whether a
positive sign is omitted or forced. `SkillCatalog` joins that hint at read time;
it is not copied into the Army database.

## Application query model

The unit browser queries canonical logical-unit data together with `army_units`,
`application_armies`, and `application_army_sources`. It excludes source-undefined
placeholder units and uses actual Army occurrences for filtering, preserving the
distinction between list availability and canonical application identity.
`army_lists.kind` remains a narrow source-context read for the legacy API field and
reinforcement fallback; `metadata_factions` is no longer required by normal unit
serving.

The rules-reference browsers query the global `skills`, `equipment`, and
`weapons` catalogs together with their `profile_*`, `option_*`, and
`unit_option_*` occurrence tables. Equivalent source labels can be merged for
display, but the underlying source IDs and individual occurrences remain
available for validation and detail rendering.

The rules schema stores collections, sources, vocabulary definitions,
records, citations, Army links, and related-record links. Curated records may
also link to `ammunition`, `extras`, `characteristics`, `troop_types`, `units`,
and profile occurrences. These are annotations and explanations only; Army JSON
remains authoritative for unit membership, availability, legality, and
source-derived statistics.

## Required Army API metadata

`metadata.json` is a required supplementary API snapshot for database builds.
When it is beside an Army directory or ZIP archive, `infinity-db build`
discovers it automatically; otherwise use `--metadata PATH`. It is copied
losslessly into `master.json` and `normalized.json`, and its nine collections
are available as `metadata_*` SQLite tables. Database export also rejects
normalized data that does not contain valid Army metadata.

Faction names enrich matching `army_lists` by numeric ID, while faction parent
relationships provide explicit grouping metadata for presentation. Army list
files remain authoritative for unit membership and source-derived availability,
but the presence of an army-list identity does not by itself make that identity
independently playable. Metadata-only factions never create army lists or unit
memberships. Metadata weapon IDs can repeat for different modes, so their table
uses source position as its key.
