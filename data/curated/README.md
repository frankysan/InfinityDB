# Curated data

`data/curated/` contains source-controlled, human-reviewed information derived
from external sources. Curated material is distinct from immutable external
inputs under `data/raw/`, `data/wiki/`, and `data/pdf/`, and from generated
provenance under `data/manifests/`.

## Current curated data

- `rules/` contains validated rules-reference collections consumed by `infinity-db build-rules`.
- `identities/` contains reviewed source-derived presentation relationships consumed
  during Army normalization.
- `peripherals/` contains the separate reviewed Army-Peripheral identity/mapping contract.
- `relationships/` contains snapshot-bound review evidence for source relationship
  endpoints that cannot be resolved from the current Army snapshot alone.
- `enrichment-coverage/` contains maintained release-scope classifications consumed by
  the rules-enrichment coverage audit; these decisions classify audit gaps without becoming
  runtime game semantics. These categories
  have separate schemas and loaders; no loader treats arbitrary JSON from another
  curated category as valid input. Curated identifiers are stable project/domain identities.
- `armyLinks` are cross-domain references rather than curated record identities: Skill,
  Equipment, and Weapon links may use either a positive numeric source ID or the owning
  application-domain slug, with slugs preferred in maintained rules data. Numeric references
  remain valid for compatibility, provenance, and explicit disambiguation.

The sections below document the implemented `curated/rules/` contract.

## Other curated categories

`data/curated/snapshot-notes/` defines the current versioned contract for
human-maintained snapshot descriptions, comparison targets, and notable-change
notes associated with immutable snapshots by SHA-256. Those notes remain
separate from generated snapshot provenance and are not rules-database inputs.
Acquisition tooling never writes or consumes this subtree; see
[`snapshot-notes/README.md`](snapshot-notes/README.md).


### Rules-enrichment coverage classifications

`enrichment-coverage/classifications.json` is the maintained release-scope policy for
`tools/audit_enrichment_coverage.py`. Every gap code known to the audit must have an explicit
default classification: `release-blocker`, `intentional-omission`, `supporting-identity`,
or `later-product-work`. The checked-in defaults are deliberately conservative: detected
user-facing coverage gaps block 0.7.0 until reviewed otherwise, while rules-only relation
targets that already support an exposed item are classified separately as
`supporting-identity`.

Item- or relation-specific `overrides` record reviewed exceptions with a reason. Overrides
must match a gap in the selected `infinity.db` + `rules.db` pair; stale or mistyped overrides
fail the audit instead of silently surviving after the underlying data changes. The policy is
release-planning metadata only. It must not be consumed as rules ontology or application
runtime behavior.

### Curated Peripheral identities

`peripherals/army-identities.json` is the reviewed boundary between Army Peripheral
source encodings and canonical application identity. The contract is deliberately separate
from both rules records and the display-identity contract. It pins the Army snapshot used as
evidence and supports two source mechanisms:

- embedded `peripherals` rows resolve through reviewed `peripheral:<slug>` entities, optional
  `peripheral-profile:<slug>` profiles, and `peripheral-mapping:<slug>` mappings keyed by
  `(sourceId, armyId, peripheralId)`;
- standalone Unit-backed Peripherals resolve through `peripheral-unit-mapping:<slug>` records
  keyed by source-global Unit ID and reuse the existing `logical_units` identity instead of
  creating duplicate `peripheral:*` entities;
- reviewed Controller access pools resolve through
  `peripheral-controller-access:<slug>` records keyed to an exact source Controller
  profile/loadout occurrence and point to canonical logical Unit IDs. `access-pool` means
  eligibility/selection, not fixed ownership of one Peripheral by one Controller.

Canonical entities may reference one of the five curated N5.3 Peripheral-type rule
IDs once type classification is independently reviewed. `typeId` is intentionally optional so
source identity can be established before the rules type is known; when present it must be one
of those five IDs. Profiles may declare only the reviewed `connected` or `autonomous` Cyberplug
modes. Every accepted source mapping requires review date and reason, and an optional
profile must belong to the mapped entity. Unit-backed mappings additionally pin the expected
logical Unit and reviewed Peripheral type so source-name, logical-identity, or subtype drift
fails closed. Controller access additionally pins source occurrence name, reviewed Peripheral
type, and the complete canonical target pool so source/controller/target drift fails closed.
Unknown fields fail closed; notably `mercs` is not accepted as identity data. The checked-in
current-snapshot contract contains 56 embedded entities, 279 embedded mappings, 17 Unit-backed
source mappings resolving to 10 logical Units, and four reviewed Cyberplug Controller access
pools targeting two canonical logical Units.

Validate the authored contract with:

```powershell
infinity-db validate-peripheral-identities
```

During mapping review, validate it against the exact generated Army snapshot and write the
deterministic coverage/review queue with:

```powershell
infinity-db validate-peripheral-identities --database data/generated/infinity.db --output "reports/PERIPHERAL IDENTITY COVERAGE.json"
```

The snapshot-bound pass requires the database SHA-256 provenance to match exactly one
declared curated source. Incomplete mapping coverage is reported as review work rather than
a validation failure; stale coordinates or exact source-name drift are invalid. Candidate
name normalization (Unicode NFC, collapsed whitespace, and case-folding) is used only to
group the review queue and never creates identity automatically.

The current reviewed identity/access contract is complete for the pinned snapshot. The next
Milestone 2B step is to materialize these curated-derived relationships into the application
database/API without collapsing their source-context provenance.

### Reviewed historical relation endpoints

`relationships/historical-unit-endpoints.json` records independent historical evidence for
relation-referenced Army Unit IDs that are placeholders in the current snapshot. It is an audit
review contract, not a logical-Unit alias file and not a runtime application input. The current
contract identifies retired Unit IDs 165, 613, 749, 1503, and 1509 and pins the review to the
2026-09-18 Army snapshot SHA-256.

`tools/audit_relationship_semantics.py` uses the file only when one of those IDs is referenced by
a relation. Before classifying the relation as `reviewed-stale-source-relation`, the audit verifies
that the pinned snapshot matches and that the endpoint remains a source placeholder with no
logical-Unit mapping, Army roster row, profile, loadout, or payload occurrence. Any drift fails
closed for renewed review. Historical names provide provenance for the stale endpoint; they never
imply equivalence with a current Unit or cause a current application constraint to be materialized.

### Curated display identities

`identities/army-display.json` records source-derived presentation relationships
that must remain distinct from ownership and playability. Each mapping relates a
source canonical faction identity to the army/grouping identity whose symbol and
faction styling should represent that unit in the UI. The current reviewed
relationship maps canonical source identity `1` to display army `901`.

`infinity-db normalize` and `infinity-db build` validate this document, derive
`display_army_id`, and pin the exact document plus canonical SHA-256 into
`normalized.json`. Database export revalidates that pinned relationship. Runtime
code consumes the persisted field and does not reload this curated file.

## Curated rules reference data

This directory is the handoff from local wiki/PDF research to rules-data
ingestion. Developers and agents may read reference material in `data/wiki/`
and `data/pdf/`, then write concise, human-reviewed facts under
`data/curated/rules/`. The application and its build pipeline never read those
raw reference trees directly.

### Available reference families

The local reference corpus may include:

- N5 core rules revisions under `data/pdf/rules/`.
- N5 FAQ revisions under `data/pdf/faq/`.
- ITS seasons under `data/pdf/its/` and `data/pdf/legacy/`.
- Wiki research snapshots under `data/wiki/`; the current downloader writes
  `WIKI-<language> YYYYMMDD-HHMMSS.zip` archives.

Core rules can provide curated skills, equipment, weapons, ammunition, traits,
states, attributes, timing, modifiers, deployment, hacking, fireteams, and
interactions. FAQ records represent dated clarifications or rulings. ITS records
remain season-scoped and can represent scenarios, objectives, scoring,
deployment, and mission constraints. Wiki pages are useful for discovery,
aliases, cross-links, and concise explanations, but do not override applicable
official rules or Army data.

### Current v19 contract

Place one collection per subject or release under `data/curated/rules/`, for
example `rules/n5-core-v5.3.json`. Each file contains:

- `format`: `InfinityDB curated reference`
- `formatVersion`: `19`
- `collection`: collection identity/scope/authority
- `sources`: source-specific PDF or wiki provenance
- `vocabularySources`: source references for maintained vocabularies
- `skillTypes`, `labels`, and typed `records`

Source provenance is explicit and source-specific. PDF sources require the local
reviewed file, official upstream `url`, publication date, and page count; PDF
citations use positive **printed** page numbers. Archived wiki sources require
the exact timestamped ZIP path, SHA-256, acquisition timestamp, language,
document count, and wiki base URL; citations use archive `member` names and may
add a heading. Exact pinned wiki revisions remain URL-backed sources with a
`retrievedDate`; their citations use the source URL directly and may add a
heading.

`vocabularySources` follows the same locator rules instead of forcing wiki
references to carry PDF page numbers.

Do not bulk-copy PDF or wiki text, images, or page markup. Keep core rules,
FAQs/errata, and ITS seasons in separate collections so versions cannot be
blended accidentally.

Every record declares `composition.role` as `definition` or `supplement`. Across
current collections, each semantic record ID has exactly one definition; supplements
retain their own scope, facts, citations, relations, and publication provenance rather
than being field-merged by load order. Related concepts use typed one-way `relations`;
reverse navigation is derived by `rules.db`. Format v10 introduced the gameplay-
interaction edge `reduces-modifiers-from`; format v11 extends that closed vocabulary
with `ignores-modifiers-from` and `negates-effects-of` so counter-rules can describe
ignored MODs separately from effects that become ineffective. Format v12 adds
`modifies-rolls-for` and `restricts-use-of` for rules such as Sensor that alter another
Skill's Roll or constrain one specific use without implying that the whole target rule
is negated. Format v13 adds `applies-effects-to` and `imposes-modifiers-on` so rules such
as Reflective and Albedo can expose who they affect without collapsing those different
mechanics into a generic related-item edge. Format v14 adds `overrides-effects-of` for explicit precedence such as No Cover taking priority over Limited Cover when both restrictions apply. Format v15 adds `cancels-state` for reviewed recovery/removal rules such as Doctor and Engineer; State definitions remain rules/reference identities rather than runtime game-session state. Format v16 adds `causes-state` for explicit activation paths such as Forward Observer causing Targeted State and Disposable (X) causing the item-specific Unloaded State, while existing roll/restriction relations make the affected State useful from both directions. Format v17 adds `enables-use-of` when a reviewed rule or State satisfies a documented prerequisite for another rule without claiming that all of the target rule's requirements are met. Format v18 adds `uses-effects-of` when a rule reuses another rule's effects without claiming that it enters the target State; Concealed uses Camouflaged State effects while retaining its distinct Marker behavior. Format v19 replaces the singular Skill-definition `facts.typeId` with ordered `facts.typeIds`, allowing every full Skill definition to own one or more declaration categories directly.

Reviewed `training` definitions use `facts: {"orderType": "regular"}` or
`{"orderType": "irregular"}` and canonical IDs `training:regular` /
`training:irregular`. They do **not** have Army Skill links. Ordinary Army
loadout Order-generation entries reference these records in the Unit API and
browser, with citations; Lieutenant/Tactical Orders and source skill-like
compatibility rows must not be treated as further Training values. Training
supplements may add scoped facts but cannot redefine `orderType`. This is an
additive v7 record-kind contract; it does not alter the `rules.db` schema.

### Document shape

The main collection structure is:

```json
{
    "format": "InfinityDB curated reference",
    "formatVersion": 19,
    "collection": {
        "id": "n5-core-v5.3",
        "title": "N5 Core Rules v5.3",
        "domain": "core-rules",
        "status": "current",
        "effectiveFrom": "2026-08-10",
        "authority": "primary"
    },
    "vocabularySources": {
        "skillTypes": [],
        "labels": []
    },
    "skillTypes": [
        {
            "id": "automatic",
            "name": "Automatic Skills",
            "labels": ["Automatic Skill", "Automatic Skills"],
            "descriptions": {
                "singular": "Automatic Skill description.",
                "plural": "Automatic Skills description."
            }
        }
    ],
    "labels": [
        {"id": "optional", "name": "Optional", "description": "Optional label."}
    ],
    "sources": [
        {
            "id": "n5-core-v5.3-pdf",
            "kind": "pdf",
            "title": "N5 Core Rules",
            "version": "5.3",
            "publishedDate": "2026-08-10",
            "localPath": "data/pdf/rules/n5-rules-v5-3-en.pdf",
            "url": "https://experience.corvusbelli.com/en/infinity/resources",
            "pageCount": 196,
            "authority": "primary"
        }
    ],
    "records": [
        {
            "id": "skill:camouflage",
            "kind": "skill",
            "name": "Camouflage",
            "summary": "Concise human-written summary.",
            "scope": {"game": "N5", "seasons": ["current"]},
            "facts": {"typeIds": ["automatic"]},
            "labelIds": ["optional"],
            "armyLinks": [{"entity": "skill", "id": "camouflage"}],
            "variantSemantics": {"inheritance": "family"},
            "relations": [],
            "citations": [
                {"sourceId": "n5-core-v5.3-pdf", "page": 113, "section": "States"}
            ],
            "review": {"status": "reviewed", "reviewedOn": "2026-09-15"},
            "composition": {"role": "definition"}
        }
    ]
}
```

Supported record kinds include `rule`, `skill`, `declaration-category`,
`equipment`, `weapon`, `ammunition`, `trait`, `state`, `glossary`, `interaction`, `fireteam`,
`faq-ruling`, `erratum`, `scenario`, `objective`, `mission`, `deployment`, and
`unit-annotation`.

Weapon records may use `facts.specialProfile` for rulebook-defined deployable
profiles that are not fully represented by Army weapon metadata. The special
profile stores ordered stat name/value pairs, equipment, skills, and a CC weapon;
the application composes it into the existing weapon-reference API only when a
validated `rules.db` is available.

Full Skill definitions own their declaration/action categories directly through an
ordered, non-empty `facts.typeIds` array referencing the canonical `skillTypes`
vocabulary. Multiple values are first-class semantics; the first value is the primary
category only for compatibility projections that still expose singular `skill_type`.

`declaration-category` records remain the partial-curation mechanism for Army Skills
that do not yet have a full Skill definition, and for Equipment action categories. They
use singular `facts.typeId` plus `facts.order`, may link to Army `skill` or `equipment`
identities, and require exactly one PDF citation with a positive printed page. Skills
without either a full definition or a curated declaration fall back to `Unclassified`;
Equipment receives no invented fallback category. Do not create uncited category
records to represent missing rules classification.

Army-linked Skill, Equipment, and Weapon definitions declare
`variantSemantics.inheritance` as `family` or `source`. Family semantics may be
presented for the canonical application family. Source semantics require exactly one
numeric Army source identity, a typed `variant-of` relation to a same-kind family
definition, and `variantSemantics.sourceVariant`. A numeric Level uses
`{"kind": "level", "value": 2}`; a reviewed named variant uses
`{"kind": "named", "label": "..."}`; and a reviewed numeric Attribute replacement uses
`{"kind": "attribute-replacement", "attribute": "BS", "value": 12}`. These apply only
to that exact source variant.
Supplements inherit Army routing from their definition and therefore do not declare
their own `armyLinks`.

Rule-derived occurrence-parameter display behavior lives under
`variantSemantics.occurrenceParameters`. The currently standardized parameter is an
Army extra with `kind: "distance"` and `positiveSign: "preserve|omit|force"`. This
does not decide whether an Army extra is a distance: imported
`extras.type == "DISTANCE"` remains authoritative for that source semantic. Reviewed
exact-source Attribute replacements are kept on `sourceVariant`, not as generic
occurrence parameters. Other MOD/value forms remain opaque until their semantics are
reviewed.

Skill and State records always carry a `labelIds` array, but it may be empty when the reviewed
rule does not assign any maintained rules Label. Do not invent a Label merely to satisfy
serialization.

Peripheral types remain ordinary `rule` records in this same collection. A Peripheral
type uses `facts.category = "peripheral-type"` and a validated
`controllerEligibility` object. The supported first-phase grammar is an explicit
`{"status": "not-stated"}`, one `{"hasSkill": "skill:<id>"}` predicate, or an
`{"anyOf": [...]}` list containing two or more `hasSkill` predicates. Optional
structured facts currently cover positive `maxPerController`, reviewed
`operatingDistance: "unlimited"`, and the Cyberplug `connected` / `autonomous`
profile modes. Eligibility references must resolve to Skill records in the same
collection. These facts describe rules semantics only; they do not map Army-local
Peripheral definitions to canonical Peripheral entities.

Trait records may use `facts.sourceIdentity.prefixes` for source labels whose
parameter value is part of the Army text, for example `Disposable (2)` mapping
to the canonical `Disposable (X)` record. Exact alternate spellings and
misspellings belong in the normal `aliases` array. This is source-identity data;
the matching algorithm remains application code.

Army links may target existing `skills`, `equipment`, `weapons`, `ammunition`,
`extras`, `characteristics`, `troop_types`, `units`, or profile occurrences. For
`skill`, `equipment`, and `weapon`, an `id` may be either a positive numeric source ID
or a lowercase application-domain slug. The checked-in N5 collection uses slugs for
those catalog domains; numeric IDs remain accepted for compatibility/provenance. A
numeric-looking string is not a slug and must instead be written as a JSON integer.
The independent rules database stores the authored reference as text; application
composition matches slugs to the current Army application identity without making
either database an import source for the other. Army links annotate Army data; they do
not establish list legality or replace Army-derived statistics.

An archived wiki citation uses an archive member plus an optional heading, for
example:

```json
{
    "sourceId": "wiki-en-20260918-130233",
    "member": "Camouflaged_State",
    "heading": "Camouflaged State"
}
```

The checked-in N5 v5.3 collection is bound to
`data/wiki/WIKI-en 20260918-130233.zip` with SHA-256
`aa407f1959fbaafce98058acf507640cc94bfc2690d4a7519a547caf1492f23a`,
acquired 2026-09-18 at 13:02:33 +02:00 with 812 members. Pinned `oldid=` wiki
sources remain URL-backed because the current mirror intentionally does not
preserve query-selected historical revisions as separate archive members.

Generated acquisition provenance remains under `data/manifests/snapshots/`;
curated rules copy only the exact source identity required to reproduce what was
reviewed.

Curated-rule files older than format v19 are no longer accepted by the loader and must
be migrated to the current source/citation, composition, variant, declaration, and
Training contracts before ingestion.

The starter file `rules/example.json` is intentionally empty and is never an
ingestion input. Directory ingestion skips that reserved filename. Validate all
rules collections with:

```powershell
infinity-db validate-curated data/curated/rules
```

To validate one collection directly, provide its path instead. Build the rules
database with:

```powershell
infinity-db build-rules
```

Curated rules files are source-controlled project data. Raw PDFs and wiki
snapshots remain ignored, local-only research material, and are never packaged
or served.
