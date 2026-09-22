# Peripheral curated-data design

## Status

This document is a Milestone 2B design direction. The rules-side foundation is now
implemented in the existing curated v3 rules pipeline: Doctor, Engineer, Cyberplug,
and Peripheral have reviewed Skill records, the five N5.3 Peripheral types have
reviewed rule records, and controller-eligibility/type facts are validated. The
Army-definition-to-canonical-Peripheral mapping and derived application relationship
layer remain unimplemented.

The research established that Peripheral type, Controller association,
controller eligibility, Peripheral identity, and (for Cyberplug) operating
profiles are distinct concepts. Army data and rules data describe different
parts of that model and must retain separate provenance.

The first implementation phase extends InfinityDB's existing
`data/curated/rules/` -> `rules.db` pipeline. It does **not** introduce a parallel
Peripheral rules loader or a second rules database. Source-to-Peripheral-entity
identity mappings are a separate curated concern and must remain outside both Army
source tables and the rules-reference contract.

## Evidence and authority

Peripheral modeling uses several sources with different responsibilities. They
must not be blended into one undifferentiated authority layer.

1. **Infinity Army snapshot** — primary authority for source-native Army facts:
   army-local Peripheral definitions, concrete profile/loadout attachments,
   quantities, ordering, `mercs`, and list-local availability context.
2. **N5 core rules v5.3 PDF** — primary authority for base Peripheral rules and
   stable rules concepts. The relevant material includes the general Peripheral
   rule and its five types on printed pages 106-108, plus the Doctor, Engineer,
   and Cyberplug Special Skills on printed pages 90-91.
3. **N5 FAQ v0.1** — a separate dated clarification layer. FAQ rulings may refine
   or clarify applicable core rules, but must not be flattened silently into the
   base-rule records.
4. **English Infinity Wiki snapshot** — secondary rules evidence and a discovery
   source for headings, aliases, cross-links, and candidate extraction. It does
   not override the applicable official PDF/FAQ or Army source data.

The reviewed Wiki snapshot is `data/wiki/WIKI-en 20260918-130233.zip`, English,
812 members, SHA-256
`aa407f1959fbaafce98058acf507640cc94bfc2690d4a7519a547caf1492f23a`.
Relevant members include `Peripheral`, `Cyberplug`, `Disconnected_State`, and
the linked Doctor, Engineer, Coherency, Place Deployable, Null, Isolated,
Fireteams, and Coordinated Order pages.

The current generated-DB audits provide independent Army-side evidence. The
relationship audit resolves all observed loadout includes without raw fallback
or cross-logical targets. The dedicated Peripheral audit reports 279 army-local
Peripheral definitions, 56 distinct names, 818 resolved loadout attachments,
no profile attachments in the audited snapshot, 41 names with multiple raw
identities, and three names whose `mercs` value varies by source context. These
are diagnostic observations, not proof that name alone is canonical identity.

## Concepts the model must keep separate

| Concept | Intended representation | Reason |
| --- | --- | --- |
| Peripheral base rule | Curated rules record | Defines common Controller/Peripheral behavior. |
| Peripheral type | Curated rules record | The five types have materially different behavior and restrictions. |
| Controller eligibility | Structured curated rule fact | Eligibility is a rules fact, not inferable from Army attachment tables. |
| Peripheral entity | Future canonical application abstraction | An Army-local name/ID does not by itself prove global identity. |
| Peripheral profile | Future canonical application abstraction plus curated semantics where needed | Connected/Autonomous and other profile distinctions must not be collapsed into entity identity. |
| Army Peripheral definition | Army source/context data | `(army_id, peripheral_id)` is source-local and list-contextual. |
| Explicit attachment | Army source relationship | A profile/loadout can explicitly bring a Peripheral. |
| Definition-only availability | Army source/context evidence | Presence without a normalized attachment is a distinct source mechanism, not proof of controller eligibility. |
| Controller--Peripheral eligibility | Curated-derived relationship | Produced only by joining source-observed Controller facts to curated rules predicates. |
| `mercs` | Army contextual data | It may vary for the same name and is not part of canonical Peripheral identity. |
| FAQ clarification | Separate curated `faq-ruling` | Dated clarification must remain distinguishable from the base rule. |

A concrete Controller--Peripheral association in an Army list and a rule saying
which Troopers *may* control a Peripheral are therefore different relationships.
InfinityDB should be able to represent both.

## Rules-side Peripheral inventory

The N5 v5.3 core rules define exactly five Peripheral types. “Not stated” below
means the reviewed base rule does not provide a generic Controller-eligibility
predicate; it must not be interpreted as “all Troopers are eligible.”

| Stable ID | Rules name | Controller eligibility | Useful structured facts |
| --- | --- | --- | --- |
| `rule:peripheral-type:servant` | Peripheral (Servant) | Doctor **or** Engineer | Unlimited operating distance; maximum 2; one activated at a time; Doctor/Engineer action can be performed through the Peripheral; one target per Order. |
| `rule:peripheral-type:synchronized` | Peripheral (Synchronized) | not stated | Controller Coherency; checks at start/end of Order/ARO; failed Coherency causes Disconnected; synchronized activation. |
| `rule:peripheral-type:control` | Peripheral (Control) | not stated | Unlimited operating distance; maximum 3; Control Unit and Spearhead; Coherency to Spearhead; target-requiring Skill performed only by Controller and Spearhead. |
| `rule:peripheral-type:ancillary` | Peripheral (Ancillary) | not stated | Unlimited operating distance; starts undeployed; Controller places it with Place Deployable; Fireteam/Coordinated-Order interaction depends on deployment/state. |
| `rule:peripheral-type:cyberplug` | Peripheral (Cyberplug) | Cyberplug skill | Unlimited operating distance; maximum 2; Connected/Autonomous Unit Profiles; at most one Connected; controller-state behavior differs from normal Disconnected handling; incompatible with Servant on the same Controller. |

The common rule also establishes Controller/Peripheral association, shared
activation behavior, Army-list/Combat-Group counting consequences, deployment
and AVA constraints, and the normal Disconnected interaction. Those are rules
facts, not Army availability calculations.

## Reuse the existing curated-rules architecture

### Do not create a parallel Peripheral rules format

The earlier draft proposed `data/curated/peripherals/n5-v5.3.json` with a new
loader. That direction is rejected. Peripheral rules are rules knowledge and
belong in the implemented curated v3 rules contract under
`data/curated/rules/`.

The current `rules.db` already persists generic typed records, structured
`facts`, citations, Army links, and record-to-record relations. The first
Peripheral phase should therefore prefer extending curated validation and
records over introducing a new database schema. A rules-database schema change
is justified only if the existing generic record representation proves
insufficient after implementation evidence.

### Add the missing skill identities first

Controller predicates should reference stable curated skill records, not Army
numeric IDs. The current Army snapshot exposes the following source links:

| Curated ID | Army skill ID | Rules source |
| --- | ---: | --- |
| `skill:doctor` | 53 | N5 v5.3 p. 90 |
| `skill:engineer` | 49 | N5 v5.3 p. 91 |
| `skill:cyberplug` | 277 | N5 v5.3 p. 90 |
| `skill:peripheral` | 243 | N5 v5.3 pp. 106-108 |

These numeric IDs remain useful source/provenance references, but maintained
`armyLinks` now prefer the corresponding application Skill slugs (`doctor`, `engineer`,
`cyberplug`, and `peripheral`). Numeric IDs remain accepted as compatibility or explicit
disambiguation references; neither form becomes the semantic identity of the curated
skill record itself.

The records should use the existing `skill` contract, existing skill-type/label
vocabulary, primary PDF citations, and optional Wiki citations where they add
useful cross-link or discovery provenance.

### Represent Peripheral types as rules records

The five Peripheral types should initially be ordinary rules records in the
existing N5 core collection, related to `skill:peripheral`. A dedicated new
record kind is not required for the first phase; `kind: "rule"` plus a validated
Peripheral-specific `facts` shape is sufficient unless implementation evidence
shows otherwise.

The implemented shape follows this pattern:

```json
{
  "id": "rule:peripheral-type:servant",
  "kind": "rule",
  "name": "Peripheral (Servant)",
  "summary": "Concise reviewed summary.",
  "facts": {
    "category": "peripheral-type",
    "controllerEligibility": {
      "anyOf": [
        {"hasSkill": "skill:doctor"},
        {"hasSkill": "skill:engineer"}
      ]
    },
    "maxPerController": 2,
    "operatingDistance": "unlimited"
  },
  "relatedRecords": ["skill:peripheral", "skill:doctor", "skill:engineer"],
  "citations": [
    {"sourceId": "n5-core-v5.3-pdf", "page": 106, "section": "Peripheral"}
  ]
}
```

The curated validator now checks the Peripheral-specific fact shape explicitly:
`category` is `peripheral-type`; controller eligibility is either `not-stated`, a
single `hasSkill` predicate, or an `anyOf` list of `hasSkill` predicates; finite
controller limits are positive integers; `operatingDistance` currently accepts the
reviewed `unlimited` value; and Cyberplug profile modes are restricted to
`connected`/`autonomous`. Eligibility skill references must resolve to Skill records
in the same collection.

For Synchronized, Control, and Ancillary, represent missing generic eligibility
as an explicit status such as `{"status": "not-stated"}`. Do not encode an
empty predicate that could be misread as universal eligibility.

## Controller-eligibility expressions

Keep the first expression grammar deliberately small. The currently established
Peripheral rules require only:

- `hasSkill`
- `anyOf`
- `allOf`

Do not pre-design `hasEquipment`, classification, characteristic, role, negation,
or explicit named-entity predicates until a reviewed rule actually requires
them. Extend the grammar when evidence appears.

Expression leaves reference stable curated rule IDs such as `skill:doctor`, not
Army IDs or display strings. The validator should reject dangling references and
unknown operators.

A future application-derived eligibility edge combines source-observed unit
skills with one of these curated predicates. It must retain enough provenance to
identify both the source occurrence and the curated rule record/citation used to
produce the result. Missing or ambiguous mappings remain unresolved; they are
never inferred false or true by name heuristics.

### Stable IDs and the domain-unique slug policy

Peripheral work follows the project-wide domain-identity layer rather than
introducing a one-off naming scheme. Schema version 17 materializes provisional
domain-local application slugs for the current Army/Unit/catalog domains, while
curated/application concepts use stable typed IDs such as `skill:doctor` and
`rule:peripheral-type:servant`. Source numeric IDs and source/display slugs remain
foreign/provenance/context references. A future public resource route may use the
resolved local domain slug, for example `/skills/doctor`, because the route itself
supplies the namespace.

Do not create a `peripherals` registry domain or assign `peripheral:*` /
`peripheral-profile:*` identities merely from an Army label. Those domains become
valid only after the reviewed source-to-entity mapping phase establishes the
corresponding canonical entity/profile boundary; collisions or ambiguous mappings
must remain unresolved rather than receiving generated suffixes.

## FAQ treatment

Peripheral FAQ rulings belong in the existing planned dated FAQ layer, for
example a future `data/curated/rules/n5-faq-v0.1.json` collection using
`kind: "faq-ruling"` records.

The FAQ clarification that a Peripheral may still declare the shared Skill when
the Controller cannot declare it is an example of a general Peripheral ruling.
It should link to the relevant Peripheral/base-rule records but remain visibly a
FAQ ruling with its own version/date and citation.

Scenario-specific rulings, such as whether an undeployed Peripheral (Ancillary)
counts as Killed for a scenario objective, must retain scenario/ITS scope. They
must not be promoted into universal core Peripheral facts, especially because
ITS content is outside the version-1.0 core-data requirement.

## Entity and profile identity remain a separate phase

Rules identity and source/entity identity are different problems.

Cyberplug establishes that a Peripheral (Cyberplug) can have Connected and
Autonomous Unit Profiles and switch operating profile during play. That supports
this conceptual relationship:

```text
Peripheral entity --uses type--> Peripheral type
Peripheral entity --has profile--> Peripheral profile
Peripheral profile --operates as--> Connected | Autonomous
```

It does **not** prove that an Army Peripheral label maps one-to-one to a canonical
entity or profile. Army-local IDs are contextual, repeated names are common, and
`mercs` can vary independently.

Do not place reviewed Army-definition-to-entity mappings in
`data/curated/rules/`. They resolve source objects rather than rules semantics and now
use the separate `data/curated/peripherals/army-identities.json` contract validated by
`infinity_db.peripheral_identities`. This does not overload the current
`identities/army-display.json` presentation-identity contract. The checked-in contract
is pinned to the audited Army snapshot and now resolves all 279 embedded Peripheral
definitions to 56 reviewed canonical entities. The first population pass deliberately
uses one canonical entity per exact source-definition name and does not merge distinct
source names into shared entities/profiles without separate evidence. No canonical
Peripheral profiles are created by this pass.

Candidate matching may normalize Unicode NFC, trim and collapse whitespace, and
case-fold for **reporting/review queues only**. Do not remove punctuation,
transliterate, expand abbreviations, or fuzzy-match. An automatic candidate is
not an accepted mapping. Ambiguous or changing source matches fail closed and
require an explicit reviewed mapping.

## Relationship and provenance boundary

The intended graph is:

```text
N5 core rule (curated) --defines--> Peripheral type
curated skill --satisfies--> controller-eligibility predicate
Peripheral type --requires--> controller-eligibility predicate
FAQ ruling (curated) --clarifies--> base rule/type

Army (source) --defines--> army-local Peripheral
Army profile/loadout (source) --explicitly attaches--> army-local Peripheral
reviewed identity mapping (future curated) --resolves--> canonical Peripheral entity
canonical Peripheral entity --uses--> Peripheral type
canonical Peripheral entity --has--> Peripheral profile

application derivation --joins source Controller facts + curated rules-->
    eligible Controller relationship
```

Source edges retain exact source identity and context, including
`(army_id, peripheral_id)`, position, quantity, `mercs`, raw fallback, and source
provenance. Curated rules retain official-document provenance. Future reviewed
identity mappings retain their own evidence. A derived application relationship
must not erase any of those layers.

## Validation strategy

### Curated rules phase

Extend existing v3 validation rather than create another validator family where
possible. The Peripheral rules work should validate at least:

- stable IDs are unique;
- Doctor, Engineer, Cyberplug, and Peripheral skill records have valid Army
  links and cited official-rule sources;
- all five Peripheral-type records exist exactly once;
- every Peripheral type relates to `skill:peripheral`;
- controller-eligibility expressions use only supported operators;
- every expression leaf resolves to a curated skill record;
- `not-stated` is distinct from a universally true predicate;
- finite limits are positive integers where present;
- Connected/Autonomous mode names are represented only where supported by cited
  rules;
- primary base-rule facts have a core-rule PDF citation;
- Wiki citations, when present, reference members in the pinned archive;
- FAQ facts are not stored as base core-rule facts.

Because all initial controller-eligibility skill references can live in the same
N5 core collection, first-phase referential validation need not solve arbitrary
cross-collection dependency resolution.

### Source/entity mapping phase

The separate mapping validator now fails closed for the authored contract itself,
including:

- duplicate mapping IDs;
- unknown canonical Peripheral entity/profile targets;
- duplicate explicit `(sourceId, armyId, peripheralId)` source mappings;
- unknown canonical entity/profile targets or profiles attached to the wrong entity;
- invalid canonical Peripheral-type references when a reviewed `typeId` is present;
- mappings without review/evidence metadata;
- attempts to treat `mercs` as intrinsic Peripheral identity;
- ambiguous Connected/Autonomous profile mapping.

Validation against the actual Army rows is now implemented as an optional snapshot-bound
coverage pass of `infinity-db validate-peripheral-identities`. With `--database`, the
validator matches the database `snapshotArchiveSha256` to exactly one declared curated
source, compares every explicit mapping against `(army_id, id, name)`, and reports:

- source definitions with no reviewed mapping;
- stale curated mappings whose source coordinates no longer exist;
- exact source-name drift on an otherwise matching coordinate;
- curated entities/profiles not referenced by the selected snapshot;
- repeated source-name groups and normalization-only review collisions; and
- a deterministic review queue grouped by the deliberately weak NFC/whitespace/case-fold
  candidate normalization.

Incomplete coverage is a normal `needs-review` state during population. Stale mappings or
source-name drift make the snapshot validation invalid. Name grouping remains review
evidence only and never creates or changes a canonical mapping.

The same coverage pass also audits the relationship graph in both directions when the
normalized controller tables are available:

- each Army Peripheral definition -> every profile/loadout occurrence that explicitly
  attaches it, including Controller Unit/profile/loadout identity and observed Skill slugs;
- each Controller occurrence -> every explicitly attached Army Peripheral definition; and
- the reviewed core `controllerEligibility` predicates -> a consistency check against each
  Controller's candidate effective Skill sets.

This typing evidence is deliberately asymmetric. `consistent` means the observed Controller
satisfies a rule-stated necessary eligibility condition; it does **not** prove that the
Peripheral has that type. `inconsistent` can rule out an evaluable type only when the
Controller Skill context is complete. Loadout-level evidence therefore evaluates every
profile Skill set in the same group together with loadout-local Skills and reports mixed
results as `ambiguous`. Synchronized, Control, and Ancillary remain unevaluated because the
reviewed core rules state no generic Controller-eligibility predicate for those types.

The coverage pass now distinguishes two separate Army source mechanisms instead of trying to
infer Cyberplug from same-name profile groups:

- the `peripherals` catalog plus explicit profile/loadout attachments and hidden disabled profile
  groups is the **embedded Peripheral mechanism**; and
- ordinary `army_units` occurrences whose profiles explicitly carry the Army `Peripheral` Skill
  are a separate **Unit-catalog Peripheral mechanism**. The Skill's source `extra` value is direct
  subtype evidence rather than display decoration.

The v3 coverage run on the 2026-09-18 snapshot proved why this separation is necessary: all 279
`peripherals` definitions matched disabled embedded groups and none matched an enabled group.
That same-name check therefore describes how embedded definitions are carried; it is not
Cyberplug evidence. Follow-up source review also disproved the initial Troop-Type hypothesis:
there is no Troop Type named `Peripheral` in the normalized catalog. Instead, source Skill 243
(`Peripheral`) carries subtype extras. Extra 41 is explicitly named `Servant`; extra 374 is
explicitly named `Cyberplug`. Slave Drones (unit 526) and Reinforcement Slave Drones (1617) carry
`Peripheral (Servant)`, while Sartroid Ranters/Puzzlers (1885/1886) carry
`Peripheral (Cyberplug)` and expose Connected/Autonomous profiles. Therefore selectable
Unit-backed Peripherals are not Cyberplug-exclusive.

The v5 audit inventories Unit-backed Peripheral occurrences from the explicit Skill, preserves
their source subtype extras, inventories every Controller occurrence whose effective Skill context
contains `cyberplug` even when it has no embedded Peripheral attachment, and surfaces same-Army
`Peripheral (Cyberplug)` Units plus raw `relations` / `relation_dependencies` adjacency as review
evidence. Neither candidate set is promoted into a semantic Controller mapping automatically.

Canonical entity identity and Peripheral type are therefore reviewed independently. A
`peripheral:<slug>` entity may exist without `typeId`; once type evidence is sufficient,
`typeId` may be added and must reference one of the five reviewed core Peripheral types. This
prevents an otherwise defensible cross-Army identity decision from forcing an unsupported
rules classification.

## Facts that should remain prose or interaction references initially

Do not over-structure temporal rules merely because they mention Peripherals.
Order/ARO sequencing, target-selection examples, Silhouette-contact procedures,
full Disconnected activation/cancellation, Fireteam transitions, and detailed
Connected/Autonomous switching behavior can remain concise cited summaries or
interaction records until a concrete query/UI need justifies a stricter model.

The static model should first capture identities, types, eligibility, finite
constraints, profile-mode existence, and durable relationships.

## Open questions requiring evidence

1. The rules do not map every Army Peripheral label to a Peripheral type/entity.
2. The dedicated Army audit confirms that repeated names alone are insufficient:
   all 279 definitions are attached somewhere, but 22 repeated canonical loadout
   payloads have different semantic attachment signatures across source contexts.
3. Synchronized, Control, and Ancillary do not state a generic Controller-
   eligibility predicate in the reviewed base rule.
4. Connected/Autonomous proves distinct operating profiles for Cyberplug but does
   not identify which Army payloads represent those profiles. The embedded `peripherals`
   mechanism cannot answer that question: all 279 current definitions resolve through hidden
   disabled groups. Cyberplug review must instead inspect ordinary Army Units carrying
   `Peripheral (Cyberplug)`, Cyberplug-skilled Controllers, and their same-Army/source-relationship
   evidence.
5. The identity-mapping curated category now has an explicit contract and repository
   location under `data/curated/peripherals/`; it remains independent of display identity.
   The unresolved work is evidence-backed population and coverage, not schema location.
6. Source precedence/effective-date behavior for later FAQ revisions must remain
   explicit rather than relying on collection load order.

## Revised implementation sequence

1. **Extend existing core curated skill coverage — complete.** Doctor, Engineer,
   Cyberplug, and Peripheral now have reviewed N5 v5.3 Skill records with current
   Army links and primary PDF citations.
2. **Define and validate the minimal Peripheral rules facts — complete.** The
   curated v3 validator now owns the small controller-eligibility expression grammar
   and Peripheral-type fact checks; no parallel rules schema/database was introduced.
3. **Curate the five Peripheral types — complete.** Servant, Synchronized, Control,
   Ancillary, and Cyberplug are reviewed records in the existing N5 core rules
   collection. Source/entity mappings remain deliberately separate.
4. **Keep FAQ clarifications separate.** When the dated FAQ layer is implemented,
   add relevant Peripheral rulings as `faq-ruling` records linked to the base
   rules; retain scenario scope on scenario-specific rulings.
5. **Review the dedicated Army Peripheral semantics audit — complete for the
   2026-09-18 snapshot.** The audit finds 279 army-local definitions / 56 names,
   818 resolved loadout attachments, no profile attachments, zero definition-only
   definitions, 41 names with multiple raw identities, three names with `mercs`
   variation, zero global-option Peripheral warnings, and 22 canonical loadout
   payloads with differing semantic attachment signatures. These are snapshot
   evidence, not permanent cardinalities or a canonical identity rule.
6. **Design the separate reviewed Peripheral identity/mapping contract — complete.**
   `data/curated/peripherals/army-identities.json` defines reviewed canonical entity/profile
   IDs and exact snapshot-local source mappings, with fail-closed validation and no
   automatic name promotion.
7. **Populate the reviewed embedded-definition mappings — complete for the current
   snapshot.** The v5 evidence resolves all 279 embedded definitions to 56 reviewed
   canonical entities. Each exact source-definition name is kept as its own entity boundary,
   and its rules type is taken from the matched Army profile's explicit `Peripheral` Skill
   subtype extra. Distinct source names are not merged into shared entities/profiles in this
   pass, even when they look like loadout variants.
8. **Complete the Unit-backed identity/controller relationship pass.** The audit now inventories
   ordinary Unit-backed Peripheral occurrences with direct subtype evidence, including standalone
   Servants and Cyberplugs, plus Cyberplug-skilled Controllers and same-Army subtype candidates.
   Resolve those source occurrences to canonical Peripheral identities and explicit Controller
   relationships without treating co-occurrence alone as proof.
9. **Materialize curated-derived application relationships.** Join source
   Controller facts, reviewed identity mappings, and curated eligibility rules;
   preserve all provenance and then decide the `infinity.db`/API/UI surface for
   cross-army Peripheral questions.

No runtime schema, compatibility revision, API, or UI change is required for
steps 1-5 unless validation work demonstrates a specific need.
