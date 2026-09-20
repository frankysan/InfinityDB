# Peripheral curated-data design

## Status

This document is a Milestone 2B design direction. It does not describe a fully
implemented Peripheral application model yet and does not authorize source-
normalization, runtime-schema, API, or UI changes by itself.

The research established that Peripheral type, Controller association,
controller eligibility, Peripheral identity, and (for Cyberplug) operating
profiles are distinct concepts. Army data and rules data describe different
parts of that model and must retain separate provenance.

The first implementation phase should extend InfinityDB's existing
`data/curated/rules/` -> `rules.db` pipeline. Do **not** introduce a parallel
Peripheral rules loader or a second rules database. Source-to-Peripheral-entity
identity mappings are a later curated concern and must remain outside both Army
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

These numeric IDs remain snapshot/source links in `armyLinks`; they are not the
semantic identity of the curated skills.

The records should use the existing `skill` contract, existing skill-type/label
vocabulary, primary PDF citations, and optional Wiki citations where they add
useful cross-link or discovery provenance.

### Represent Peripheral types as rules records

The five Peripheral types should initially be ordinary rules records in the
existing N5 core collection, related to `skill:peripheral`. A dedicated new
record kind is not required for the first phase; `kind: "rule"` plus a validated
Peripheral-specific `facts` shape is sufficient unless implementation evidence
shows otherwise.

A representative shape is:

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

This example is design direction, not yet an accepted serialized schema. Before
adding records, extend the curated validator so the chosen Peripheral facts are
validated explicitly rather than being arbitrary unchecked JSON.

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
`data/curated/rules/`. They require a separate curated identity/mapping contract
because they resolve source objects rather than rules semantics. The exact
subtree and loader should be chosen during that phase; do not overload the
current `identities/army-display.json` presentation-identity contract
implicitly.

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

### Future source/entity mapping phase

A separate mapping validator should eventually fail closed for:

- duplicate mapping IDs;
- unknown canonical Peripheral entity/profile targets;
- intended source definitions resolving to zero or multiple current source rows;
- source-name normalization collisions;
- changed source identity after a new snapshot;
- mappings without review/evidence metadata;
- attempts to treat `mercs` as intrinsic Peripheral identity;
- ambiguous Connected/Autonomous profile mapping.

It should report source-only definitions and curated-only entities separately
instead of silently discarding either side.

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
2. The dedicated Army audit still needs to drive the source/entity mapping phase;
   repeated names alone are insufficient.
3. Synchronized, Control, and Ancillary do not state a generic Controller-
   eligibility predicate in the reviewed base rule.
4. Connected/Autonomous proves distinct operating profiles for Cyberplug but does
   not identify which Army payloads, if any, represent those profiles.
5. The future identity-mapping curated category needs an explicit contract and
   repository location; the existing display-identity contract must not be
   broadened accidentally.
6. Source precedence/effective-date behavior for later FAQ revisions must remain
   explicit rather than relying on collection load order.

## Revised implementation sequence

1. **Extend existing core curated skill coverage.** Add reviewed N5 v5.3 records
   for Doctor, Engineer, Cyberplug, and Peripheral with current Army links and
   primary PDF citations.
2. **Define and validate the minimal Peripheral rules facts.** Add explicit
   validation for the small controller-eligibility expression grammar and the
   Peripheral-type facts needed by the five core type records. Avoid speculative
   operators and avoid a new rules database schema unless required by evidence.
3. **Curate the five Peripheral types in the existing N5 core rules collection.**
   Use the N5 v5.3 PDF as primary evidence and the pinned Wiki snapshot as
   optional secondary discovery/cross-link provenance. Do not add source/entity
   mappings yet.
4. **Keep FAQ clarifications separate.** When the dated FAQ layer is implemented,
   add relevant Peripheral rulings as `faq-ruling` records linked to the base
   rules; retain scenario scope on scenario-specific rulings.
5. **Run and review the dedicated Army Peripheral semantics audit on the current
   generated database.** Use definition-only availability, attachment stability,
   name repetition, `mercs` variation, and unresolved global-option warnings as
   evidence for the identity/mapping design.
6. **Design the separate reviewed Peripheral identity/mapping contract.** Decide
   canonical entity/profile boundaries and explicit source mappings only after
   combining the Army audit evidence with the curated rules vocabulary.
7. **Materialize curated-derived application relationships.** Join source
   Controller facts, reviewed identity mappings, and curated eligibility rules;
   preserve all provenance and then decide the `infinity.db`/API/UI surface for
   cross-army Peripheral questions.

No runtime schema, compatibility revision, API, or UI change is required for
steps 1-5 unless validation work demonstrates a specific need.
