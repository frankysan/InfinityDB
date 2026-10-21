# Curated data

**Project domain:** Data processing

`data/curated/` contains source-controlled, human-reviewed information derived
from external sources. Curated material is distinct from immutable external
inputs under `data/raw/`, `data/wiki/`, and `data/pdf/`, and from generated
provenance under `data/manifests/`.

## Current curated data

- `rules/` contains validated rules-reference collections, including the
  source-verified `n5-faq-v0.1.json` FAQ pilot, consumed by
  `infinity-db build-rules`.
- `identities/` contains reviewed source-derived presentation and historical identity
  relationships consumed by the Army build/runtime surfaces that own them.
  `army-overview.json` contains short editorial gameplay summaries keyed by public Army slug;
  the copy is synthesized from current Army/rules data with external faction background used only
  as secondary context, and is kept separate from source-derived identity semantics.
- `peripherals/` contains the separate reviewed Army-Peripheral identity/mapping contract.
- `relationships/` contains snapshot-bound review evidence for source relationship
  endpoints that cannot be resolved from the current Army snapshot alone.
- `enrichment-coverage/` contains maintained release-scope classifications consumed by
  the rules-enrichment coverage audit; these decisions classify audit gaps without becoming
  runtime game semantics.
- `rules-interactions/` contains the long-lived outgoing-interaction review policy used to
  track current-release progress and known deferred/future relation candidates without
  becoming runtime game semantics.

These curated categories have separate schemas and loaders; no loader treats arbitrary JSON
from another curated category as valid input. Curated identifiers are stable project/domain
identities.

- `armyLinks` are cross-domain references rather than curated record identities: Skill,
  Equipment, and Weapon links may use either a positive numeric source ID or the owning
  application-domain slug, with slugs preferred in maintained rules data. Numeric references
  remain valid for compatibility, provenance, and explicit disambiguation.

Weapon Properties are a distinct, reviewed player-facing vocabulary maintained in
`config/catalogs/weapon-properties.json`, not additional Ammunition records or
source Army `properties` (Traits). Each explicitly associated source Weapon
profile is signature-matched, and its Property names their canonical rule
owners/source sections; see `docs/data-model.md` for the current projection
contract. Do not duplicate those source rules as new Property mechanics.

The sections below document the implemented `curated/rules/` contract.

### Maintained rules-text semantic-link policy

Maintained rules prose must use typed `[[kind:slug]]` references when it names an existing
supported Skill, Equipment item, Weapon, Ammunition type, Trait, State, Hacking Program,
General Rule (`rule:*`), Attribute, or reviewed Game term. `[[term:zero-visibility-zone]]` resolves to the corresponding
Glossary definition and the existing inline preview tooltip, including on keyboard focus and touch.
Visibility Zone variants are explicitly linked throughout current curated rules text.
The broad Game-term vocabulary also includes common nouns (e.g. Model and Token), so a full
term-name/plain-prose migration is not claimed; those cases must be curated deliberately.
The pre-token migration is complete: `maintained-text-link-reviews.json` records explicit
completed review coverage for the previously supported reference namespaces; new General Rule
references are supported, but are not claimed as a completed plain-text scan. The rules
build rejects any new plain semantic candidate in those fully reviewed namespaces directly.

Completed scopes receive a case-insensitive scan with conservative plural matching. A residual is an
error: link it when the meaning is clear, or replace it with `review-needed` when it is not. If a
colliding surface is confidently ordinary text rather than a reference to that namespace, record it
under that batch's `reviewedPlainSurfaces` with a reusable reason plus audit-derived occurrence
fingerprints. Each fingerprint binds the decision to an exact maintained-text passage, field, match
span, and semantic target set; changed or newly worded occurrences reopen review. Owner identity is
not part of the fingerprint, so an unchanged passage cloned into a synthetic/derived record inherits
the same reviewed meaning. A reviewed plain surface suppresses only that batch namespace, not
same-text candidates in another namespace.

Audit the current inventory with:

```powershell
python tools\audit_maintained_text_links.py
```

The audit prints unlinked candidates, reviewed-batch residuals, and explicit `review-needed` markers.
The first two inventories must remain zero. When a passage is ambiguous or its source meaning is not
clear enough to choose a semantic target, use
`[[review-needed:<reason>|<visible text>]]` rather than guessing.

Reason codes are lowercase kebab-case; prefer reusable codes such as
`ambiguous-target`, `unclear-source-meaning`, `source-conflict`, or
`scope-unclear`. `[[review-needed:<reason>]]` is valid for a standalone marker.

Rules summaries may separate paragraphs with blank lines (`\n\n`) and use
`**emphasis**` around mode labels; the browser renders both without breaking
maintained-text links. Editorial source discrepancies, legacy Army terminology,
and other non-gameplay notes belong in an optional `facts.sourceNotes` array of
non-empty maintained-text strings. These are shown beneath the primary rules in
smaller type and remain subject to reference auditing.

Curated rule records may add optional `facts.clarifications`, a non-empty
array of maintained-text strings for printed examples and explanations that
clarify rather than define core Effects. Render after Requirements, Effects,
and Restrictions, and before any reviewed interaction cases. Unlike
`facts.sourceNotes`, these are player-facing gameplay explanations at normal
body size, with semantic links, review coverage, and the record's citations
intact. Keep rule effects in `facts.effects`; do not move binding game
conditions into example prose.

The audit lists all review-needed markers separately so reviewed uncertainty remains easy to locate
and cannot disappear into ordinary prose. Resolve each marker to a typed semantic reference, or to
ordinary text when manual review proves it is not a reference.

For `ammunition:*` records, authored `causes-state` relations must contain
exactly the State identities in `facts.ammunitionResolution.stateEffects`.
The condition and target restrictions belong to the typed facts; a generic
related-rule edge is a navigational link, **not** an unconditional game effect.
The validator rejects an omitted, extra, or mismatched State relation so the
player-facing graph and source-cited facts cannot drift apart. Nine Saving-Roll-bearing Ammunition records additionally use the strictly
validated `facts.ammunitionResolution.criticalAdditionalSavingRolls: 1`.
This is one additional Saving Roll for a Critical with that Ammunition,
not one additional roll per component in a combined profile. T2's
`woundsPerFailedSave.criticalAdditionalRoll` separately describes the
Wounds inflicted on failure of that extra roll. Smoke/Eclipse use
`facts.visibilityZone` and no Saving Roll facts. Other
Ammunition effects remain independent of these State links.

The `skill:immunity` definition may also carry the closed
`facts.immunityInteraction` object. It records the reviewed N5.3 boundary for
covered Ammunition (treat as Normal and ignore its special effects, Saving
Roll Attribute MODs and Saving Roll-count MODs), the remaining single Critical
roll unless Immunity (Critical) applies, and the exceptions for Comms Attacks,
Non-Lethal and State: Stunned. Only `skill:immunity` may own this fact family.
The optional `reviewedCombinedCases` array records source-qualified, derived
examples for an Immunity (ARM) defender against an ARM-based, non-Comms combined
attack. Every case must specify the Army source Ammunition ID/name, two typed
component IDs, applicability, original and covered hit/Critical Saving Roll
counts, Normal treatment, and evidence class `derived-from-pinned-general-rules`.
The validator rejects unsupported conditions, duplicate IDs, and impossible
Critical counts. These examples cite Wiki Immunity `oldid=3643` together with
Combined Ammunition `oldid=3000`. The closed `reviewedVulnerabilityCases`
array records a **separate explicit Wiki example** (`Vulnerability` `oldid=3156`):
Immunity (Enhanced) cannot be used against weapons with `Viral` in their names
when the defender also has Vulnerability (Viral). Its predicate refers to a
weapon name, **not** the weapon's Ammunition components. Neither fact family is
executable or projected into Army profiles. The `reviewedWeaponCases` array
records the **explicit** N5.3 Wiki Immunity Example 4 (`oldid=3643`): against
Flash Pulse, Immunity (BTS) treats Stun Ammunition as Normal,
while Non-Lethal and the failed-Saving-Roll Stunned condition survive. The Weapon
Chart (`oldid=4083`) separately grounds Flash Pulse's printed profile. Do not
extrapolate these reviewed, non-executable examples to unreviewed combinations.

### Explaining rules interactions

**Accepted authoring and review standard, not a new JSON schema or a rules engine.**
A material interaction between rules is not adequately explained by stating the
correct outcome alone. A concise player-facing explanation should make the
reasoning traceable, using the existing curated `summary`, typed links, citations,
and `facts.sourceNotes` where appropriate:

1. **Scope and trigger:** identify the relevant weapon/Skill, target conditions,
   roll Attribute, and when the interaction applies. Do not imply that a
   conditional effect always occurs.
2. **General rule and modification:** explain the baseline mechanic and precisely
   what the interacting rule changes. Keep Ammunition effects, Saving Roll
   Attributes, and Weapon Traits distinct.
3. **Exception or precedence:** cite the *actual* clause that preserves,
   overrides, or limits an effect. A printed example establishes its own result,
   but does not prove an otherwise undocumented general mechanism.
4. **Gameplay result:** say what the player rolls or does, and what happens on
   success or failure, including Wounds and States where relevant. Make the
   difference between a hit and a failed Saving Roll explicit.
5. **Evidence and certainty:** cite the scoped official rule text and, when
   available, the matching example/FAQ and Army profile. Distinguish an
   **explicit ruling**, a **rule-derived interpretation**, and an **unresolved
   conflict**. Compare pinned English/Spanish versions and available historical
   editions when their wording or profiles materially differ; preserve source
   version/revision and do not silently choose a convenient reading.

Keep the explanation short enough to use during a game; link the relevant full
rules instead of reproducing them. Put historical/editorial differences in
`facts.sourceNotes`, but leave unresolved questions that change gameplay clearly
visible in ordinary rules text (using `review-needed` when appropriate). Do not
manufacture an explanation when the official material supports only an outcome;
label its evidence and scope instead. Relation-review status or a correct
conditional result alone does not establish explanatory completeness.

**Example — Immunity (BTS) and Flash Pulse:** Flash Pulse calls for a BTS Saving
Roll with Stun Ammunition. Immunity (BTS) treats that Ammunition as Normal but
does not turn the roll into ARM. The explicit *IMPORTANT* exception preserves
Non-Lethal and State: Stunned; a failed BTS Saving Roll therefore causes
Stunned but no Wounds. The English Weapon Chart includes the State: Stunned
Trait, whereas the Spanish N5.3 wiki chart omits it and reports a different
roll count. That discrepancy is a source note, not grounds for inventing a
general exception for other States or weapons. The pinned evidence and exact
scope are recorded in [RS-AW-IMM-001](../../docs/rules-semantics.md#rs-aw-imm-001--immunity-changes-covered-effects-not-the-attack-identity).

### Rules-enrichment coverage classifications

`enrichment-coverage/classifications.json` is the maintained release-scope policy for
`tools/audit_enrichment_coverage.py`. Every gap code known to the audit must have an explicit
default classification: `release-blocker`, `intentional-omission`, `supporting-identity`,
or `later-product-work`. The policy was introduced for the 0.7.0 enrichment gate and remains
deliberately conservative: detected user-facing coverage gaps require explicit review, while
rules-only relation targets that already support an exposed item are classified separately as
`supporting-identity`.

`catalogGapCodes` records reviewed release-scope decisions that apply to one gap kind across a
whole catalog. More-specific item or relation `overrides` record reviewed exceptions with a
reason and take precedence over catalog-level decisions. Item/relation overrides must match a gap
in the selected `infinity.db` + `rules.db` pair; stale or mistyped overrides fail the audit instead
of silently surviving after the underlying data changes.

The published 0.10.0 scope classified missing Weapon rule definitions as `later-product-work`
and deferred Commlink to its separately scoped Reinforcements Extra work. These retained
classifications describe that release's reviewed scope; they do not waive the 1.0 completeness
gate. Reassess them against the pinned 1.0 inputs as tracked in
[the backlog](../../docs/TODO.md#source-inventory-and-gap-batches).
Other defects in those catalogs, including stale citations, ambiguous mappings, unresolved links,
or unreviewed rules, retain their normal conservative classification and can still block the
release under review. The policy is release-planning metadata only; it must not be consumed as rules
ontology or application runtime behavior.

### Rules-interaction review policy

`rules-interactions/catalog-scope.json` is the maintained public-catalog denominator for
the interaction review. It lists every public Skill, Equipment item, and Trait targeted by
the release named in that scope file, including catalog identities that do not yet have a
curated rules definition. `rules-interactions/reviews.json` separately tracks every semantic
rules identity other than `declaration-category` projection records and
`faq-ruling` dated clarification overlays. FAQ records have separate source,
target, applicability and supersession validation and cannot introduce new
canonical outgoing rule mechanics through this ledger. Entries record the target
release whose outgoing interactions are being reviewed, whether that review is
pending/reviewed/inherited, and known future interactions that should survive beyond that
release. The top-level
`futureInteractions` queue can also retain a provisional source/target ID that is not yet a
current rules record, so future domain work does not lose already-reviewed interactions.

A primary catalog item is normally complete only when its canonical typed rules identity exists
and that identity's outgoing semantics are reviewed. `catalog-scope.json` may declare a
`releaseExceptions` entry when an item has been explicitly vetted but its authoritative rule
belongs to a different publication/domain that is deliberately outside the selected target release.
Such items remain visible in the denominator as deferred rather than being misclassified as missing
target-release rules. Unclassified missing definitions remain pending, and an exception becomes
stale and fails the audit if a current curated definition is later added. Exact source variants
and independently modeled supporting identities are reported separately.

The ledger deliberately does not duplicate authored `relations`: the current curated rules
graph remains authoritative for edges that exist now. `tools/audit_rules_interactions.py`
combines the graph with the ledger and generates `docs/rules-interaction-checklist.md`. A
source-specific variant may use `inherited` when its outgoing interaction semantics are
fully inherited from its family; this does not prevent adding a future exact-variant review
if a source exception is discovered. Deferred candidates may leave `relationType` null when
the current relation vocabulary cannot represent the interaction precisely.

Regenerate/check the maintained checklist with:

```powershell
python tools/audit_rules_interactions.py --output docs/rules-interaction-checklist.md
python tools/audit_rules_interactions.py --check-output docs/rules-interaction-checklist.md
```

When the Army/application catalog snapshot changes, validate or refresh the maintained catalog
scope against the generated databases:

```powershell
python tools/audit_rules_interactions.py --database data/generated/infinity.db --rules-database data/generated/rules.db
python tools/audit_rules_interactions.py --database data/generated/infinity.db --rules-database data/generated/rules.db --refresh-catalog-scope --output docs/rules-interaction-checklist.md
```

A release gate may be inspected explicitly with `--require-release <version>`. Pending
reviews make that command fail; future candidates targeting another release remain visible
without blocking the selected release.

### Curated Peripheral identities

`peripherals/army-identities.json` is the reviewed boundary between Army Peripheral
source encodings and canonical application identity. The contract is deliberately separate
from both rules records and the display-identity contract. It pins the Army snapshot used as
evidence and supports three source mechanisms:

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
Unknown fields fail closed; notably `mercs` is not accepted as identity data. Do not duplicate
current entity/mapping counts in this reference: the curated file plus
`infinity-db validate-peripheral-identities --database ...` are the authoritative current
inventory and coverage check.

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

The current reviewed identity/access contract is complete for the pinned snapshot. Army
database export materializes the validated identities, mappings, and Controller access pools
into the application database while retaining their source-context provenance and the curated
contract hash. Runtime repository/API/browser reads consume those materialized application
tables and never open the working-tree Peripheral JSON.

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

`identities/legacy-armies.json` separately records historical Army identities that
remain useful for player-facing reference but have no current N5 Army list. These
entries are not normalization aliases and are never promoted into selectable
`application_armies`. The Army overview loads them as explicit non-playable legacy
references, while symbol discovery uses their historical logo URLs so maintained
`image_overrides/factions` assets pass through the normal symbol processing and
publication pipeline.

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

### Current v23 contract

Place one collection per subject or release under `data/curated/rules/`, for
example `rules/n5-core-v5.3.json`. Each file contains:

- `format`: `InfinityDB curated reference`
- `formatVersion`: `23`
- `collection`: publication/source collection identity, scope, status, and authority
- optional `scenarioCollection`: stable scenario-set identity, exact set revision, and ordered members
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

Current Label IDs form one canonical vocabulary across current collections. A record may
therefore reuse a `labelIds` entry defined by another current collection rather than
duplicating that Label definition locally. If the same Label ID is carried by more than
one current collection, its name and description must agree exactly. Rules export rejects
unresolved current Label references and conflicting current Label definitions, while
historical collections remain self-contained.

Do not bulk-copy PDF or wiki text, images, or page markup. Keep core rules,
FAQs/errata, and ITS seasons in separate collections so versions cannot be
blended accidentally.

Every record declares `composition.role` as `definition` or `supplement`. Across
current collections, each semantic record ID has exactly one definition; supplements
retain their own scope, facts, citations, relations, and publication provenance rather
than being field-merged by load order. Related concepts use typed one-way `relations`;
reverse navigation is derived by `rules.db`.

### Dated FAQ ruling authoring contract (published subset)

`faq-ruling:<stable-slug>` is a canonical ruling identity, independent of
the page on which it first appeared. FAQ material lives in its own versioned
source collection rather than inside a core Rule summary. Validated
`faq-ruling` definitions have a required `facts` object:

- `question` and concise `answer`: non-empty authored text, distinct
  from the canonical topic's definition/Effects.
- `topicIds`: unique typed references to the affected rule, Skill,
  State, Hacking Program, scenario, or other supported topic.
- `applicability`: non-empty exact scope entries with `rulesRevision`,
  `effectiveFrom` (ISO date), optional `effectiveUntil` (not before the
  start), optional `season: {id, revision}`, and optional
  `scenarioIds`. Missing season/scenario restrictions mean the author
  deliberately chose general applicability **at the named Rules revision**,
  not applicability to every edition or future ITS season.
- `originalPublication`: `collectionId`, `sourceId`, `version`,
  `publishedDate` and positive printed `page`. The source must be a
  declared PDF and the original page must be in the record's citations;
  the version/date must match the source metadata.
- `selectedCitation: {sourceId, page}` and non-empty `selectionReason`:
  exact manually reviewed current official primary PDF evidence.
  `conflictingCitations` lists any other individually cited conflicting
  pages, rather than silently joining their answers or automatically
  preferring the newest upload.
- `supersedes`: unique stable `faq-ruling:*` IDs. Self-supersession
  and unknown predecessors are rejected at export. Historical predecessor
  definitions are allowed; every predecessor must have a potentially
  overlapping rules revision, time window and season/scenario scope.
  Cycles are rejected. A predecessor is superseded only within the
  verified overlap, not across its entire history.

**Precedence policy:** The source-native core definition remains intact.
An applicable official FAQ/erratum is a dated clarification layer, not a
field-wise overwrite. A source is eligible only after exact rules-revision
and effective-date matching, plus matching season revision and scenario
where declared. Cross-posting/carry-forward must preserve the same ruling
identity and original publication, with additional citations; creating a
new ruling ID merely because another PDF repeats the answer is prohibited.
An expressly superseding ruling can replace another only for its verified
overlapping scope; otherwise both remain evidence. Conflicting answers
without a reviewed selected citation and reason are **not** resolved by
document order, language, or publication recency.

**Implementation status:** `src/infinity_db/faq_rulings.py` validates this
authored contract during curated-document loading. Rules export additionally
checks that each current ruling's `topicIds` and `scenarioIds` resolve to
current canonical definitions (scenario IDs must reference actual Scenarios),
that predecessor IDs exist in retained current/historical definitions,
that original publication metadata does not drift across editions of one
ruling, and that supersession is acyclic and has an overlapping
rules-revision/season/scenario/date scope. Missing ITS scenarios are rejected
rather than silently accepted as published targets.

**Applicability-aware read model:** `RulesDatabase.faq_rulings_for_topic`
selects reviewed current FAQ definitions for an explicit typed `topic_id`,
exact `rules_revision`, and ISO `as_of` date. Optional season ID/revision
must be provided as a pair; optional scenario identity restricts
mission-specific rulings. A rule applies only when at least one authored
scope matches the supplied context, the selected official PDF source is
published, the original ruling has been published, and its current collection
is effective by the requested date. A season- or scenario-scoped ruling never
appears in an unspecified context. Only an applicable reviewed successor
for the same topic suppresses an applicable predecessor, never a newer
publication merely by date. Current selections retain question/answer,
matched scope, original publication, selected source version/date/page,
selection reason, conflicts, citations and `supersedes` references.
They do not rewrite a canonical Skill or Rule summary.

`GET /api/faq-rulings?topic_id=skill:camouflage&rules_revision=5.3&as_of=2026-10-15`
exposes that exact read model; optional `season_id`, `season_revision`,
`scenario_id`, and `cache_bust` are accepted. Unknown, repeated, missing
or invalid parameters receive HTTP 400. The API requires explicit context
and never assumes the newest rules, current season or today's date.
The default read model does not replay superseded historical collections;
historical publication selection and verification of ITS season revisions
not yet present in the corpus remain future work.

Twenty-eight source-reviewed rulings now live in `rules/n5-faq-v0.1.json`.
Nine were introduced in FAQ v0.1: Hacking Device Firewall, undeployed
Peripherals (Ancillary) counted as Killed (initially Annihilation only),
Skill declaration details, fired Deployables on vertical surfaces,
Peripheral declarations, Camouflaged Markers in Total Cover, Special Dice
in Coordinated Orders, Fireteam minimums after creation, and Fireteam Type
persistence after member loss.

Nineteen more were **first recorded in official English FAQ v0.0**
and carried into v0.1. The first eight cover: Prone entry restrictions; vaulting while Climbing or
Jumping; Direct Template line-of-fire limits; occupied Place Deployable
locations; multiple Surprise Attack MODs; Sixth Sense with MSV1 in Zero
Visibility; Protheion overkill; and Camouflage (1 Use) after Infiltration.
The additional ten cover private ZoC/Coherency deployment checks,
Prone movement distance, BS Attack MODs and Long Skill Special Dice,
Controlled Jump/Speedballs, Automatic Skills in Marker State,
Aerial/Boost restrictions, Stealth and simultaneous AROs,
Deployable Cover, Disconnected/Unconscious and Cautious Movement,
and Discover versus Fireteam bonuses. The nineteenth explains the
main Deployment Phase repositioning restriction and belongs to
`rule:deployment-phase`, a canonical N5.3 Basic Rules identity.
All nineteen v0.0 carry-forwards retain three citations **per ruling**:
original v0.0 English at its
own printed page, and current v0.1 English/Spanish at their
respective actual printed pages. `originalPublication` names v0.0,
while `selectedCitation` names reviewed current v0.1; no new identity
is created merely because a publication repeats a ruling. The v0.0
source date uses the 2025-10-15 version-associated official update
anchor, not an independently verified PDF upload/publication day.

The shared **FAQ clarifications** cards appear beside affected Equipment,
Scenario, Skill, Trait, State, General Rule, Hacking Program, and
Fireteam references.
The Fireteam quick-reference page owns Fireteam FAQs; there is no
parallel General Rules route for `rule:fireteam-general`.
The browser's explicit N5.3/v0.1 source snapshot uses
`as_of=2026-09-01`, not the viewer's clock. Source `publishedDate`
uses the documented official announcement-era date, not a separately
verified PDF publication day.

**Published source discrepancy:** The Fireteam *type after member loss*
ruling uses the consistent English HARIS three-to-two-member example.
The Spanish v0.1 example has inconsistent member counts; its cited conflict
is disclosed separately rather than changing the shared Type-persistence rule.
An official correction remains outstanding; publication does not settle it.
The main Deployment Phase question belongs to `rule:deployment-phase`,
not a specialized Skill. The ITS FAQ source audit confirms Area of
Interest, Crossing Lines and Akial Interference as Season 18 source
missions; these mission identities are not yet published in the
current N5 Core scenario catalog. Do not bypass the exporter's
current-scenario target validation or omit explicit ITS season context
to force those rulings into the browser. See the private audit in
`local/audits/faq-its-season18-source-scope-20261015.md`.
No general-rule cards are created from ITS-only answers without a
verified season context. Synthetic test rulings are never published.
FAQ records remain distinct from base definitions.

Collections that contain scenario definitions also require `scenarioCollection`. Its `id` is the
stable scenario-set identity (for example `n5-core`), `revision` is the exact revision within that
set (for example `5.3`), and ordered `members` must match the scenario definitions in that source
collection exactly. Rules export materializes collection/revision, membership, and publication rows
separately; each publication carries a deterministic SHA-256 of the fully composed scenario record.
The source `collection.id` remains the publication revision/provenance key, so a scenario identity,
its set membership, and the source publication revision are not interchangeable.

Weapon Ammunition source-identity navigation is maintained separately in
`config/catalogs/weapon-ammunition-references.json` (format version 2).
Each source row has an exact Army ID and name with ordered display/link segments.
Reviewed Combined Ammunition entries additionally require `components`, an ordered
list of typed base `ammunition:*` IDs matching the linked segments exactly, separated
only by `+`. This source projection is not a curated effect relationship, nor is
Saving Roll notation parsed to infer composition. See `docs/data-model.md` for the
current runtime boundary and remaining 1.0 work.

Authoring policy for Weapons: reuse canonical `ammunition:*` summaries
and their citations via exact profile mappings, rather than repeating
AP/DA/Shock/other generic mechanics in every Weapon summary. Keep curated
Weapon text for source-specific attack modes, applicable Saving Roll fields,
Traits, requirements, and genuinely conditional exceptions. The runtime
projects shared component summaries as `ammunition_effects`, but does not
adjudicate combinations or allow the lack of an individual Weapon definition
to certify complete behavior. The 1.0 Weapon triage keeps such cases pending
under shared-effects and exception review instead of treating every absent
Weapon paragraph as a confirmed gameplay fact gap.

`weapon-shared-effect-reviews.json` records explicit source-reviewed cases that
require **no separate Weapon-specific text**. Each decision identifies the
published Weapon, N5 Core Rules chart page, rationale, and a SHA-256 of its
complete Army source profiles. The v3 Weapon audit checks that the source
identity, chart page, profile fingerprint, absence of source discrepancies,
and full reviewed ammunition-link coverage still match. Any drift reopens
review rather than silently preserving acceptance. These approvals concern
Weapon-specific explanation needs, **not** gameplay resolution or release-wide
browser acceptance.

Ammunition definitions may additionally publish reviewed, **non-executable**
`facts.ammunitionResolution` operations. This is a bounded typed-effects pilot; the
source Ammunition map above does not own effects. Supported fields are:

- `defenseModifier: {"operation": "halve", "attributes": ["ARM", "BTS"]}`:
  halves the *applicable* Saving Roll Attribute, not necessarily both Attributes
  for one hit. A subset such as `["BTS"]` is allowed.
- `rollsPerHit`: a positive integer when the Ammunition itself specifies a
  multiplicity. It does **not** replace the Army Weapon's `saving_num` field.
- `stateEffects`: reviewed records with canonical `stateId`,
  `condition: "failed-saving-roll"`, and optional `targetTypes` (from
  `HI`, `TAG`, `REM`, `VH`). Shock additionally permits exactly
  `targetAttribute: {"name": "VITA", "equals": 1}` and
  `application: "bypass-unconscious"` together when linking to `state:dead`.
  Conditions and target restrictions are part of the fact; the State must not
  be presented as unconditional.
- `savingRoll: {"attribute": "PH", "modifier": -6, "missingAttribute": "no-effect"}`:
  a PH-based Saving Roll with an explicit negative MOD, with no roll or
  Ammunition effect if the target lacks PH. Currently validated only for PH
  rolls with a negative MOD and the `no-effect` missing-Attribute case.
- `woundsPerFailedSave: {"hit": 2, "criticalAdditionalRoll": 1}`:
  Wounds from failing a Saving Roll for a normal hit versus the *separately
  generated* additional roll for a Critical. The latter must not inherit
  the two-Wound result of a normal T2 hit. Normal and Shock each specify
  `{ "hit": 1, "criticalAdditionalRoll": 1 }`.
- `gutsEffect`: exactly a failed-Saving-Roll automatic Guts failure with a
  `courage-or-equivalent` exception (Stun). It is not a generic Guts evaluator.

`facts.visibilityZone` is a **separate** reviewed fact family for Smoke and
Eclipse: Circular Zero Visibility Zone, infinite height, expires at the start
of the States Phase. `multispectralVisor` distinguishes `can-draw-lof` (Smoke)
from `blocked` (Eclipse). No Saving Roll, automatic success, or generic Face to
Face outcome is implied. Visibility-zone data is validated only on Ammunition
records, and it cannot coexist with `ammunitionResolution` on one record.

The validator rejects unsupported operations, unknown Attributes, invalid
PH Saving Roll specifications, invalid Wound-count exceptions, invalid
State domains, duplicate States, invalid target restrictions, and ownership on
non-Ammunition records. It does not execute saving rolls or derive properties
of combined ammunition. Each record retains its existing N5/Wiki provenance;
Army data, combination component IDs, and profile Saving Roll notation stay
separate. All eleven published base identities have reviewed typed facts, but
critical interactions, target exceptions, visibility Face to Face cases, and
combined-effect precedence remain 1.0 audit work.

The current closed relation vocabulary is defined by `src/infinity_db/rule_relations.py`. It
distinguishes creation/enabling, State transitions, MOD/effect changes, cancellation/restriction,
and structural variant relationships rather than collapsing every connection into a generic
"related" edge. Curated loading fails closed on unsupported relation types. Add or change a relation
type in the canonical Python vocabulary and its validation/presentation tests before using it in
curated data.

Reviewed `training` definitions use `facts: {"orderType": "regular"}` or
`{"orderType": "irregular"}` and canonical IDs `training:regular` /
`training:irregular`. They do **not** have Army Skill links. Ordinary Army
loadout Order-generation entries reference these records in the Unit API and
browser, with citations; Lieutenant/Tactical Orders and source skill-like
compatibility rows must not be treated as further Training values. Training
supplements may add scoped facts but cannot redefine `orderType`.

A reviewed record whose fact schema permits it may use `facts.relatedCategories` to opt into cross-domain
reference navigation without changing its canonical kind or primary category.
Values are stable category slugs. This is intentionally weaker than a typed
record relation: it groups concepts for discovery only and must not be used to
claim that a concept belongs to that category. For example, Impetuous can be
surfaced next to Order types while remaining a Special Skill rather than an
Order.

### Document shape

The main collection structure is illustrated below. This is a schema example, not reviewed rules
content: sample summaries, dates, and citations must be replaced with verified authored evidence
before ingestion.

```json
{
    "format": "InfinityDB curated reference",
    "formatVersion": 23,
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
`equipment`, `weapon`, `ammunition`, `trait`, `state`, `attribute`, `term`, `training`,
`hacking-program`, `glossary`,
`interaction`, `fireteam`, `faq-ruling`, `erratum`, `scenario`, `objective`, `mission`, `deployment`, and
`unit-annotation`.

Acceptance by the generic record envelope does not imply a published application domain. Core
scenario authoring uses `facts.definitionVersion: 2` and composes explicit references from the same
collection. Inline v1 records remain supported; export resolves v2 into self-contained v1-shaped
runtime records. The canonical component/data contract is documented in
[the scenario model](../../docs/data-model.md#scenario-model-implemented-core-and-future-extensions).

An optional `scenarioComponents` object has `formatVersion: 1` and a `definitions` array. Each
definition has a typed `id`, `kind` (`setup`, `geometry`, `objective`, or `end-condition`), `payload`,
non-empty `citations`, and explicit `scenarios` IDs. Inclusions use `{ "ref": "<typed-id>" }`.
Setups can additionally specify `gameSizeOverrides` entries containing exact `armyPoints` and only
`swc`/`minimumVictoryPoints` changes. Shared setups can themselves reference another setup; cycles,
unknown references, unsupported kinds/fields, duplicate IDs, and scope mismatches are errors.
Geometry titles are projected from the including scenario without changing semantic coordinates.

Semantic scenario Rules and Skills are ordinary `rule`/`skill` records with optional
`scope.scenarios`. Scoped records cannot have Army links. Scenario Rules use
`facts.category: scenario-rule`, `effects`, `restrictions`, `definesSkills`, and optional
`specialists: { "anyOfSkills": ["skill:doctor", ...] }`. Rules include Skills by ID; Skill definitions
retain the ordinary declaration-type, Label, Requirements/Effects/Restrictions, review, and citation
contract. Same names with different behavior require distinct IDs, rather than collection load order.

A v2 mission has `setup`, `rules`, `objectives`, `endConditions`, and `sourceIssues`. Rule inclusions
have a local ordered `id` and semantic `ref`; Specialist inclusions may have `addSkills`/`removeSkills`
arrays of complete Skill IDs. Only actual differences belong in those arrays. The baseline and its
common restrictions are authored once, and rendering consumes the resolved qualifiers. Skill lists
are derived from the included Rules' `definesSkills`, rather than authored again on each mission.

The resolved mission uses ordered sides/game sizes, geometry-bound deployment regions, typed
objectives/conditions, included Rules and Skills, endings, and scoped source issues. Its existing
numeric range, per-round caps, geometry status/comparison, combat metric, and end-condition validators
still apply after expansion. Scenario source-note status is `needs-verification` for unresolved source
uncertainty or `reviewed-resolution` for an explicit maintained interpretation; only an objective-scoped
`needs-verification` issue may acknowledge an otherwise-overlapping exclusive scoring row. Annihilation
uses a reviewed resolution for its corrected 350-point surviving-VP boundaries, while Domination keeps
its 350-point SWC difference as needs-verification. Supplies no longer carries a placement issue: page 153 explicitly uses an 8-inch
offset, while re-review of page 154 shows the 12-inch mark as a guide ruler rather than the Supply Box
offset. Both definition and inclusion source provenance remain available; shared reuse does not
authorize correcting genuinely ambiguous source values.

Shared prose participates in the full semantic maintained-text syntax, target, and reviewed-link
audits, including objective/ending payloads in the component library. No plain-reference exception
is broadened for the new model. Rebuild `rules.db` with the current rules builder after migrating
to format v23; current rules schema/compatibility is 8/10.

Embedded `term` records own source-backed Game terminology that does not warrant a standalone
catalog/detail route. They require `facts.scope` with a stable slug such as `game-element`,
`alignment`, `profile`, `scoring`, or `state-classification`; the scope prevents same-name concepts
from being collapsed merely because their display text matches a Label, Trait, or another domain.

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
identities, and require exactly one PDF citation with a positive printed page. When an
Army Skill has both a full definition and fallback declaration records under the same
authored Army reference, their ordered category identities must agree; curated loading
fails closed on drift. During application composition, equivalent numeric source IDs and
canonical Skill slugs are cross-checked as the same identity as well, so category drift
cannot be hidden by authoring the two representations under different reference forms.
Skills without either a full definition or a curated declaration
fall back to `Unclassified`; Equipment receives no invented fallback category. Do not create uncited category
records to represent missing rules classification.

Army-linked Skill, Equipment, and Weapon definitions declare
`variantSemantics.inheritance` as `family` or `source`. Family semantics may be
presented for the canonical application family. Source semantics require exactly one
numeric Army source identity, a typed `variant-of` relation to a same-kind family
definition, and normally `variantSemantics.sourceVariant`. A numeric Level uses
`{"kind": "level", "value": 2}`; a reviewed named variant uses
`{"kind": "named", "label": "..."}`; and a reviewed numeric Attribute replacement uses
`{"kind": "attribute-replacement", "attribute": "BS", "value": 12}`. These apply only
to that exact source variant. Weapon definitions alone may instead use
`variantSemantics.sourceMode: "CC Mode"` to target an exact mode within one numeric
Army source identity. `sourceMode` is mutually exclusive with `sourceVariant`:
the former adds a rule to the matching Weapon **profile card**, not to its
source-wide variant or sibling modes. It must match the source profile's exact
`mode` string; an unknown mode attaches no rule rather than guessing.
An authored mode-specific definition still requires the usual numeric Army link,
`variant-of` relation and cited rule evidence. This does not authorize inferring
new gameplay effects from an unresolved source disagreement.
A Weapon family definition can additionally declare `facts.variantRuleReferences`,
a map of its linked canonical Army Weapon slugs to ordered, existing typed rules
IDs. These are reviewed **navigation associations**, not inherited statistics or
an executable rules engine. Only associated variants receive those links in
their profile API; links to Ammunition, Traits, Skills and States use the normal
published reference routes. Other source profiles and facts remain unchanged.

Supplements inherit Army routing from their definition and therefore do not declare
their own `armyLinks`.

Reviewed occurrence-parameter metadata lives under
`variantSemantics.occurrenceParameters`. A distance parameter uses
`{"source":"army-extra","kind":"distance","positiveSign":"preserve|omit|force"}`.
The imported `extras.type == "DISTANCE"` remains authoritative for distance
classification; display formatting continues to use the distance-only
`skill_parameter_semantics()` query.

An opt-in, source-bound numeric Skill modifier uses the following **non-executable**
contract (not a general parser for `TEXT` extras):

```json
{
  "source": "army-extra",
  "kind": "numeric-mod",
  "owner": "skill-holder",
  "target": "opponent",
  "appliesTo": ["bs-attack-requiring-lof", "discover"],
  "extraValues": [
    {"extraId": 6, "extraType": "TEXT", "rawValue": "-3", "modifier": -3}
  ]
}
```

Numeric modifiers currently require a family Skill Army link and a reviewed
mapping of every recognized `extraId`, exact `extraType` and `rawValue`.
Allowed targets are `skill-holder` and `opponent`; allowed applications
are `bs-attack-requiring-lof`, `discover`, `berserk-cc-attack`, and
`dodge-ph-roll`. An opponent-target modifier must apply to the two
Mimetism scopes; a skill-holder modifier may apply to a Berserk CC Attack
or Dodge PH Roll. Each mapped source modifier is a nonzero signed integer
within -12 to +12. Unknown extra signatures, other gameplay scopes and
unreviewed combinations stay unresolved. A single Skill family can specify
both numeric-MOD and distance entries; the index must verify every
co-occurring extra before calling a combined variant reviewed. Generic
situational Dodge penalties and Dodge (ARM+3) are **not** equivalent to a
Dodge PH-roll occurrence MOD. The new query
`RulesDatabase.skill_numeric_mod_semantics()` preserves the full curated
typed map without exposing it through the legacy distance-only browser
projection. Schema support alone does not certify any current Army
occurrence: the source-inventory audit must match the current reviewed
extra IDs, types and values, and reject unmapped co-occurring extras.
The N5.3 core collection reviews Mimetism (-3/-6), Berserk (+3/+6),
and Dodge PH-roll (+3/+6) as `numeric-mod` entries.

The **`reviewed-extra`** kind adds explicit, per-source-ID typed effects
without broadening numeric MODs or the distance-only browser projection.
Its first supported family is exactly `skill:dodge`. Each entry requires
`extraId`, `extraType`, `rawValue`, and a discriminated `effect`:

```json
{
  "source": "army-extra",
  "kind": "reviewed-extra",
  "extraValues": [
    {
      "extraId": 11,
      "extraType": "DISTANCE",
      "rawValue": "+2.5",
      "effect": {
        "kind": "movement-bonus",
        "appliesTo": "successful-dodge-movement",
        "centimeters": 2.5
      }
    }
  ]
}
```

The bounded Dodge effects are `opponent-roll-mod` (negative opponent
Face to Face MOD), `roll-attribute-replacement` (PH value for Dodge),
`movement-bonus` (positive centimeters, measured using 2.5 cm per
inch), `special-die` (one extra die on a Dodge Roll), and
`saving-attribute-mod` (+3 ARM to Saving Rolls after declaring Dodge).
The latter follows the English/Spanish N5.3 PDFs; their conflict
with the archived Wiki remains separately documented on the Dodge rule.
The source's exact spelling (`+1SD`, `ARM +3`, etc.) is retained.
Unknown IDs, mismatched raw types/values, invalid action scopes and
duplicate IDs across `numeric-mod` and `reviewed-extra` are rejected.
`RulesDatabase.skill_reviewed_extra_semantics()` exposes the typed
mapping to future index generation without creating a gameplay engine.
No unreviewed Army source extra becomes a specific variant merely
because its value resembles a known parameter.

Reviewed exact-source Attribute replacements are kept on
`sourceVariant`, not as generic occurrence parameters. Other MOD/value
forms remain opaque until their semantics are reviewed.

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
profile modes. Optional effects, restrictions, and clarifications are
non-empty arrays of maintained-text clauses rendered by the existing General
Rules reference cards. Keep the shared activation and Disconnected baseline
with the Peripheral Skill; subtype-local clauses explain Coherency, delegation,
and exceptions without adding inferred typed relations. Eligibility references
must resolve to Skill records in the same collection. These facts describe
rules semantics only; they do not map Army-local Peripheral definitions to
canonical Peripheral entities.

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
    "sourceId": "wiki-en-20260926-200832",
    "member": "Camouflaged_State",
    "heading": "Camouflaged State"
}
```

The checked-in N5 v5.3 collections are bound to
`data/wiki/WIKI-en 20260926-200832.zip` with SHA-256
`c0fe18c165473e3f273efd58aa7ecb0ea0d94ee274189de9361aad175b3de987`,
acquired 2026-09-26 at 20:08:32 +02:00 with 812 members. This replaces the
unavailable 2026-09-18 capture: all 74 archived citations and two vocabulary
references were checked against the newer archive; three citation members needed
path corrections. The original September 18 bytes are unavailable, so exact
content equivalence cannot be established. Individually pinned `oldid=`
revisions remain separate URL-backed source identities, even when archived
revision payloads can be verified against the history-enabled Wiki capture.

Generated acquisition provenance remains under `data/manifests/snapshots/`;
curated rules copy only the exact source identity required to reproduce what was
reviewed.

Curated-rule files older than format v23 are no longer accepted by the loader and must
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
