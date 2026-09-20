# Peripheral curated-data design

## Executive summary

This Milestone 2B research report proposes a curated-data boundary for Peripheral
rules. It makes no runtime-schema, compatibility, API, UI, or Army-normalization
change.

The local English Wiki establishes that Peripheral type, a Controller
association, controller eligibility, a Peripheral entity, and (for Cyberplug)
operating profiles are distinct concepts. Keep rule facts in curated data.
Keep Army-local definitions and explicit attachments as source facts. Do not
deduplicate Army `peripherals.id` or `name` into canonical entities.

Implement first a validated curated collection containing the five types and
their controller requirements, without joins or an SQLite/UI surface. The
existing TODO relationship audit already covers the later canonicalization work,
so this report adds no duplicate TODO item.

## Evidence and inventory

The evidence is the local ZIP `data/wiki/WIKI-en 20260918-130233.zip`:
English, 812 members, SHA-256
`aa407f1959fbaafce98058acf507640cc94bfc2690d4a7519a547caf1492f23a`.

| Archive member | Revision | Relevant content |
| --- | ---: | --- |
| `Peripheral` | 4118 | Definition, all five subtype headings, common behavior, list/AVA rules, and subtype-specific restrictions. |
| `Cyberplug` | 4085 | Cyberplug is an obligatory automatic skill whose holder may have Peripherals (Cyberplug). |
| `Disconnected_State` | 3930 | Disconnected activation, effects, and cancellation. |
| Linked terms from `Peripheral` | snapshot members | Doctor, Engineer, Coherency, Place Deployable, Null, Isolated, Fireteams, Coordinated Order, and related interactions. |

`Peripheral` is reliable for conservative extraction: it has a standard skill
box, explicit Effects/Restriction text, named subtype headings, numbered
contents, MediaWiki links, revision metadata, and visible N5.2/N5.3 updates.
The subtype definitions are headings on this page. `Peripheral_(Synchronized)`
is a redirect/search alias, not another type page.

The current generated-DB audit independently reports 279 army-local definitions,
56 distinct names, 818 resolved loadout attachments, no profile attachments, 41
names with multiple raw identities, and three names with `mercs` variants.
It explicitly classifies name grouping as diagnostic-only and refuses to infer
controller eligibility from Army data.

## Concepts the rules keep separate

| Concept | Curated/source representation | Reason |
| --- | --- | --- |
| Peripheral type | Curated `peripheralType` | Five types have different limits and behavior. |
| Peripheral entity | Future curated `peripheralEntity` | An Army label is neither a type nor proven identity. |
| Peripheral profile | Future curated `peripheralProfile` | A profile is a presentation/operating form of an entity. |
| Controller eligibility | Curated requirement expression | Servant and Cyberplug use different named-skill conditions. |
| Controller--Peripheral association | Source attachment; later curated-derived resolved edge | The rules require association but Army records the concrete occurrence. |
| Army availability | Army-source definition/attachment | Faction/list context, not a Wiki rule fact. |
| Connected/Autonomous mode | Curated profile-mode relation | Explicitly distinct Cyberplug Unit Profiles. |
| Disconnected and order behavior | Cited interaction rule | Gameplay state/sequence, not identity. |

## Type inventory and useful structured facts

`Peripheral` revision 4118 lists exactly these types. “Not stated” is not an
unrestricted predicate: the reviewed page supplies no generic eligibility rule.

| Stable ID | Rules name | Controller requirement | Structured facts |
| --- | --- | --- | --- |
| `peripheral-type:servant` | Peripheral (Servant) | `anyOf(skill:doctor, skill:engineer)` | Unlimited distance; maximum 2; one activated at a time; Doctor/Engineer action through Peripheral, one target per Order. |
| `peripheral-type:synchronized` | Peripheral (Synchronized) | not stated | Controller coherency; check start/end of Order/ARO; failure immediately causes Disconnected; all synchronize together. |
| `peripheral-type:control` | Peripheral (Control) | not stated | Unlimited distance; maximum 3; Control Unit and selected Spearhead; coherency to Spearhead; targeted Skill only Controller and Spearhead perform. |
| `peripheral-type:ancillary` | Peripheral (Ancillary) | not stated | Unlimited distance; starts undeployed and uses Place Deployable; N5.2 conditional Fireteam/Coordinated-Order exception. |
| `peripheral-type:cyberplug` | Peripheral (Cyberplug) | `allOf(skill:cyberplug)` | Unlimited distance; maximum 2; Connected/Autonomous Unit Profiles; one Connected at a time; incompatible with Servant for the same Controller. |

Common cited rules: Controller and Peripherals count as one Trooper for list and
Combat Group capacity, normally deploy together, share activation and Combat
Group, and have general Fireteam/Coordinated-Order restrictions. Controller
Null/Isolated or Peripheral Isolated normally produces Disconnected. Cyberplug
overrides the former response: its Peripherals switch Autonomous instead.
Peripherals in an Army List must be associated with a Controller, while both
respect the selected Army's general AVA. Store that as a base-rule constraint,
not as Army availability or calculated AVA.

## Controller eligibility

Use reusable declarative predicates rather than Python branches:

```json
{
  "id": "controller-requirement:doctor-or-engineer",
  "expression": {
    "anyOf": [
      {"hasSkill": "skill:doctor"},
      {"hasSkill": "skill:engineer"}
    ]
  }
}
```

Reserve this expression vocabulary: `allOf`, `anyOf`, `not`,
`hasSkill`, `hasEquipment`, `hasClassification`,
`hasCharacteristic`, `hasRole`, and `explicitEntity`. Leaves reference
stable curated vocabulary IDs, never Army numeric IDs. The initial records only
need `hasSkill`, `anyOf`, and `allOf`; do not invent Doctor/Engineer role
predicates or named exceptions.

A future derived edge combines source-observed skills/equipment with a curated
type requirement. It must retain the requirement ID and citation. Missing or
ambiguous vocabulary mapping is `unresolved`, never inferred true/false.

## Entity and profile identity

Cyberplug says that a Peripheral (Cyberplug) has two Unit Profiles—Connected
and Autonomous—chosen at Order/ARO start. Model this explicitly:

```text
peripheral entity --uses type--> peripheral type
peripheral entity --has profile--> peripheral profile --operates as--> connected | autonomous
```

Type governs controller rules; mode governs operation. Neither proves that an
Army label is one canonical entity. An Army peripheral name is initially only a
reviewed grouping candidate. Add a join only via an explicit curated mapping
with cardinality and evidence. The observed repeated raw IDs and `mercs`
variants make automatic canonicalization unsafe.

## Proposed curated collection

Start with one small collection:

```text
data/curated/peripherals/n5-v5.3.json
```

It intentionally sits outside `data/curated/rules/`, whose current loader is
the rules-DB contract. Reuse the established collection/source/citation shape,
but introduce a dedicated validator/loader with implementation. Keep the small
initial concepts in one reviewable file; split only when mappings grow.

```json
{
  "format": "InfinityDB curated peripherals",
  "formatVersion": 1,
  "collection": {"id": "n5-peripherals-v5.3", "rulesVersion": "N5.3", "status": "current"},
  "sources": [{"id": "wiki-en-20260918-130233", "kind": "wiki"}],
  "requirements": [],
  "peripheralTypes": [],
  "peripheralEntities": [],
  "peripheralProfiles": [],
  "armyDefinitionMappings": [],
  "notes": []
}
```

Representative records (illustrative, not added by this report):

```json
{
  "requirements": [{
    "id": "controller-requirement:doctor-or-engineer",
    "expression": {"anyOf": [{"hasSkill": "skill:doctor"}, {"hasSkill": "skill:engineer"}]},
    "citations": [{"sourceId": "wiki-en-20260918-130233", "member": "Peripheral", "heading": "Peripheral (Servant)", "revision": 4118}],
    "curation": {"method": "manual-review", "reviewStatus": "reviewed"}
  }],
  "peripheralTypes": [{
    "id": "peripheral-type:servant",
    "name": "Peripheral (Servant)",
    "controllerRequirementId": "controller-requirement:doctor-or-engineer",
    "constraints": {"maxPerController": 2, "operatingDistance": "unlimited", "activation": "one-at-a-time"},
    "citations": [{"sourceId": "wiki-en-20260918-130233", "member": "Peripheral", "heading": "Peripheral (Servant)", "revision": 4118}],
    "curation": {"method": "manual-review", "reviewStatus": "reviewed"}
  }]
}
```

Use namespaced lower-case ASCII IDs:
`peripheral-type:*`, `controller-requirement:*`, `peripheral:*`, and
`peripheral-profile:*`. Never embed Army IDs, snapshot dates, or display
spelling. Store aliases/source labels separately.

Every curated fact needs source ID, ZIP member, optional heading, observed
revision, curation method/status, and optional short review note. Reuse existing
archive provenance fields. Cite each fact/group precisely; do not bulk-copy Wiki
text.

## Relationship and join boundary

```text
curated skill --satisfies--> requirement --permits--> peripheral type
curated entity --uses type--> peripheral type
curated entity --has--> profile --operates as--> profile mode

Army (source) --defines--> army-local peripheral (army_id, id)
Army loadout (source) --explicitly attaches--> army-local peripheral
reviewed curated mapping --resolves--> source definition to curated entity
build/runtime join --derives--> eligible controller and cross-army availability
```

Source edges retain exact `(army_id, peripheral_id)`, position, quantity,
`mercs`, raw payload, and source provenance. The curated mapping is its own
edge, never source-table columns:

```json
{
  "id": "army-peripheral-map:panoceania:auxbot-3",
  "armySlug": "panoceania",
  "sourceDefinition": {"name": "AUXBOT_3", "normalization": "uppercase-ascii-token"},
  "peripheralEntityId": "peripheral:auxbot-3",
  "matchKind": "explicit-reviewed",
  "reviewNote": "Shape example only; a concrete mapping requires unit/profile review."
}
```

For candidate reports only, normalize Unicode NFC, trim, collapse whitespace,
and case-fold; preserve the display string. Do not remove punctuation,
transliterate, expand abbreviations, or fuzzy match. Exact normalized equality
can create a review queue only. Collisions, multiple candidates, and `mercs`
differences fail closed and require explicit override.

## Reliability and validation

| Fact class | Reliability | Workflow |
| --- | --- | --- |
| Type inventory/headings, member/revision/categories/links | Structurally extractable | Parse metadata/headings; review finite result. |
| Named skill eligibility, numeric limits, distance, mode names | Consistently phrase-extractable | Extract candidates from subtype blocks; human-review updates/scope. |
| Deployment, coherency, state exceptions | Curated/manual review | Wording is regular but scope and overrides matter. |
| Entity/profile-to-Army mapping | Curated/manual review | Require explicit evidence and mapping. |
| Semantic rules inferred from Army names/IDs | Unsuitable | Never infer type or eligibility from Army JSON. |

The future validator must fail closed for duplicate/invalid IDs; missing source,
ZIP member, or revision mismatch; unknown type/requirement/mode; invalid
expression leaf; invalid finite constraints; dangling entity/profile references;
mapping without review status; intended zero/multiple/changed source matches;
and ambiguous normalizations. It should report source-only definitions and
curated-only entities separately. It must also prove no source table receives
Wiki-derived columns.

Test fixtures should cover all five types, Doctor-or-Engineer OR, Cyberplug,
missing member, ambiguous mapping, and source-only `mercs` variation. A later
integration test must show a derived controller edge with source occurrence,
requirement ID, curated citation, and matching status.

## Prose-only rules and known questions

Keep order/ARO sequences, examples, target selection, Silhouette-contact
procedure, and full Disconnected activation/cancellation as cited rule prose.
They matter, but are temporal interactions rather than static entity facts.

Open review questions:

1. The Wiki does not map every Army peripheral label to a type/entity.
2. N5.2/N5.3 updates require effective-source/version preservation.
3. Synchronized, Control, and Ancillary eligibility is not generically stated;
   preserve `not-stated`, not an empty universally-eligible requirement.
4. Connected/Autonomous establishes modes but not which Army source payload
   represents either profile.

## Recommended implementation sequence

1. Add the validated standalone collection with five types, two requirements,
   common/base rule references, and complete archive citations.
2. Add a read-only exact normalized-name candidate report; write no mappings.
3. Curate entity/profile and Army-definition mappings, including ambiguous and
   grouping-only cases.
4. Add curated-derived build relationships, then decide the application
   database/API surface for game-wide questions.

