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

## Identities

- `unit.id` is the stable source-unit identity. It is not necessarily the
  application logical-unit identity: multiple source unit IDs can resolve to one
  materialized logical unit while source rows retain their original IDs.
- Unit `profileGroups` and unit-level `filters` are army-list-specific variants.
- Profile group, profile and loadout option IDs are local to their army/unit
  hierarchy and use composite keys in normalized data.
- Skills, weapons, equipment, ammunition, characteristics, troop types,
  categories and extras use stable global lookup IDs.
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
  displays canonical-1 units with the 901 grouping identity.
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

Logical-unit identity is now materialized during frontend SQLite creation while
normalized/source records remain unchanged for provenance. The frontend relation
is:

```text
logical_units
  id                     application logical-unit ID
  representative_unit_id source unit used for canonical display/general data

logical_unit_sources
  source_unit_id          original source-defined unit ID; one row per source unit
  logical_unit_id         owning application logical unit
```

Since schema version 11, `logical_units.id` equals `representative_unit_id`,
preserving existing unit URLs and API identifiers. Keeping both fields explicit
allows a future application-owned logical ID without rewriting the source model.

Database creation resolves the relation from configured unit aliases in the
pinned identity policy, normalized `genericUnitMatches`, normalized
`mercenaryUnitMatches` / `unmatchedMercenaryUnitIds`, and the database-build
`reinforcementUnitMatches` audit. These remain evidence/provenance; the two
frontend tables are their resolved application identity. The resolver combines
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

### Canonical application model and semantic deduplication

The materialized logical-unit relation currently answers:

> Which source unit records belong to the same application-level unit?

It does not yet answer:

> Which facts carried by those source records are the same fact, and which
> differences are meaningful context?

Repository/API assembly therefore still reconstructs application objects from
repeated source-backed profile, loadout, option, occurrence, and army records.
This is correct and source-faithful, but it makes semantic completeness harder
to reason about and causes the application layer to repeatedly merge information
that is often identical.

InfinityDB will progressively introduce a canonical application model between
the normalized source model and repository/API presentation.

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

The first implementation stages must deduplicate only records whose complete
application-relevant payloads are exactly equal after contextual identity and
provenance fields have been deliberately excluded.

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
frontend database for provenance, validation, contextual relationships that have
not yet been canonicalized, and repository paths such as catalog reverse
lookups. `get_unit()` no longer uses those source payload rows to assemble its
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

#### First implementation targets

### 1. Profile payloads

Establish a canonical profile identity/payload independent of the source
occurrence that carries it.

The audit must determine which current profile fields are:

- invariant profile facts;
- army/context-specific values;
- profile-group relationships;
- presentation metadata;
- or source provenance.

Nested characteristics, skills, equipment, weapons, extras, includes, and
peripheral relationships must participate in equality testing where they affect
the profile's meaning.

A profile occurrence should ultimately be able to reference one canonical
profile payload plus any explicit contextual differences required by that
occurrence.

### 2. Loadout payloads

Apply the same model to loadouts after the profile model is understood.

Equality must account for the complete loadout meaning, including points, SWC,
minis, disabled state, skills, equipment, weapons, extras, orders,
characteristics, includes, peripherals, and any other modeled gameplay-bearing
fields.

Source `option_id`, army/group membership, source position, and similar
provenance/context fields must not automatically define a separate canonical
payload.

A loadout occurrence should ultimately reference one canonical loadout payload
plus explicit contextual differences.

### 3. Canonical unit payload

Once profile and loadout behavior is understood, audit the fields currently
repeated across the source units belonging to each `logical_unit`.

Promote only fields demonstrated to be invariant or governed by an explicit,
reviewed semantic rule. Army memberships, availability occurrences,
source-specific variants, and genuine differences remain separate.

### 4. Relationships

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

### 5. Catalog and metadata overlap

After unit/profile/loadout canonicalization, examine overlapping information
between Army catalogs, occurrence tables, and `metadata_*` collections.

Canonicalize only where the sources demonstrably describe the same application
concept. Preserve source-specific metadata and alternate modes where they carry
distinct gameplay meaning.

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

Frontend-only `logical_units` and `logical_unit_sources` tables are derived
application structure, not normalized source facts, and therefore do not replace
`units` or duplicate profile/loadout/occurrence tables. Repository unit queries
map a requested source or representative ID through `logical_unit_sources`, then
aggregate the associated original source rows. The normalized-input table
registry remains separate from these derived frontend tables so generated
application structure cannot be supplied as normalized source data.

`PRAGMA application_id` identifies an InfinityDB file and `PRAGMA user_version`
records its schema version. The current schema version is 12 and the application
compatibility revision is 17. Imports build temporary sibling files, check
database integrity, then replace the destinations. Incompatible schemas or
compatibility revisions require a rebuild from normalized JSON for now. The
frontend export runs `ANALYZE` after loading and indexing data, preserving SQLite
planner statistics in the immutable snapshot.

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
application ID, compatibility version, and replaceable snapshot lifecycle.

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

The unit browser queries `units`, `army_units`, and `army_lists`. It excludes
source-undefined placeholder units and uses actual army occurrences for
filtering, preserving the distinction between list membership and canonical
identity.

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
