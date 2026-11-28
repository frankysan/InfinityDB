# Rules and reference data model

**Project domain:** Data processing

This document owns typed N5 rules identities, composition, exact reviewed
source-variant use, restrictions, FAQ and Rules-derived read models.
The [curated format](../data/curated/README.md) owns authored fields and
validators; [rules semantics](rules-semantics.md) owns gameplay meaning;
the [official source clarification register](official-source-clarifications.md)
owns unresolved external questions. See [Weapons and deployed objects](data-model-weapons.md)
for source-profile and object projections, [scenario model](data-model-scenarios.md)
for scenario composition, and [season ownership](season-publication-ownership.md)
for N5/ITS publication boundaries.

## Rules/reference model

Curated rules collections are versioned and built into `rules_n5.db`. The rules layer is
semantic/reference data, not mutable game state. `data/curated/README.md` owns the current curated
format and validation contract.

Special Terrain's `facts.terrainExamples` retains the eighteen source-suggested
combinations as independent printed Type, difficulty, visibility and saturation
values. `rules_n5.db` stores these with the owning definition and p. 145 citation;
the General Rules API and ordinary detail card expose the same rows. Source
dashes, optional and conditional values remain text rather than inferred game
state. Narrow Gate and Wide Gate are aliases of the Access Width reference in
search and Glossary, without creating separate devices or canonical Terrain Types.
Simple rules-backed catalog lists expose their curated aliases; global search
matches those labels while retaining the canonical name, slug and destination.

A semantic record has a stable typed ID such as `skill:move`, `state:targeted`, or
`ammunition:shock`. Current composition is contribution-based:

- exactly one current `definition` contribution owns the canonical identity;
- optional supplements can add scoped reviewed facts/citations/relations;
- historical/superseded collections remain source evidence but are excluded from normal current
  composition; and
- applicability/review/source provenance remains explicit.

The current Label vocabulary retains the original Wiki citation and the reviewed
English N5.3 p. 174 citation in `vocabulary_sources`. Label descriptions are
stored once in `labels`; Label API/detail, Glossary and contextual help reuse
those definitions rather than creating `label:*` rule records. Label detail
responses expose the contributing current collections' ordered
`vocabulary_sources`, including source identity, locator and collection. They
are vocabulary-level references, not an assertion that each source covers
each Label; a definition with no available vocabulary source exposes an empty
list. The 23 printed gameplay Labels are distinct from the Wiki-only FAQs
category. The
[reviewed conditions](rules-semantics.md#rs-br-base-003--label-definitions-retain-their-conditions-and-exceptions)
include the visible Assignable bilingual timing caveat; no eligibility or effects
calculation follows from this reference vocabulary.

## Application catalog identities and slugs

Skills, Equipment, Weapons, and other application domains may group multiple source IDs/labels into
one canonical browsing identity. Source membership remains materialized so filters and usage queries
match every member of the application identity.

Where a domain has a stable slug:

- generated application-facing links and maintained references prefer the slug;
- numeric IDs remain accepted for compatibility/provenance;
- the domain's central resolver owns both forms; and
- consumers must not derive slugs independently from labels.

Rules/reference semantic IDs (`skill:...`, `equipment:...`, etc.) remain distinct from public route
slugs even when they correspond one-to-one. A numeric Army link is projected through the
current application catalog rather than treated as an absent string slug. If that source
identity is missing from the current Army snapshot, a reviewed Common/Special Skill
definition can still use its canonical semantic slug: the Skill catalog supports these
rules-only detail pages. This fallback does not apply to source-specific Skill variants
or unresolvable Equipment/Weapon links; those remain non-routable rather than receiving
invented source destinations.

## Typed relations

Rules relations are authored once in the semantic direction and validated against current semantic
IDs. Reverse navigation is derived for presentation. The relation vocabulary includes, among others,
state entry/cancellation, effect reuse/override/negation, modifier interactions, use restrictions,
enabling, triggers, Equipment grants, and Peripheral eligibility.

The edge states the relationship; exact numeric or conditional details remain in the owning rule
facts. Backend composition owns direction-aware labels/grouping for player presentation so browser
JavaScript does not maintain a second ontology.

## Maintained text

Maintained prose supports typed semantic reference tokens and typed distance values. Completed review
batches cover the supported namespaces and reject new plain semantic candidates. Ambiguous text uses
an explicit `review-needed` marker; confirmed ordinary-language collisions are stored as exact
passage fingerprints so changed wording reopens review.

The maintained policy is documented in `data/curated/README.md`.

## Declaration categories and exact source variants

Declaration/action categories are composition metadata rather than standalone public rule records.
Skills, action-like Equipment, and Hacking Programs reuse canonical declaration identities while
preserving source spelling in source storage.

Exact source variants may belong to a family through typed `variant-of` semantics while retaining
their own source-specific facts. Family grouping must not imply that every Level/named variant has
identical rules. When the authoritative rule is naturally level-based, a family definition may also
carry reviewed `facts.levels` entries so the browser can present the level differences as one
comparison surface instead of duplicating near-identical rule cards.

For Equipment families, the detail API also exposes current, source-specific
`variant-of` definitions that are not attached to any returned Army variant as
`reference_only_variants`. These are composed rules with their own citations,
not additions to `variants`, Unit usage, or standalone Equipment routes. The
browser labels them separately as references absent from that family's current
Army options, shows available citation sections, and notes that family sources
need not establish every named combination. Their membership is derived from maintained relations and the
unfiltered family response, not from browser filters or inferred roster legality.

Exact typed parameters must retain source owner, extra ID, type, raw value,
order and scope; levels, positive/negative MODs, replacement values,
distance, named recipients, conditional grants and complete combinations
remain distinct. Do not derive effects from display notation. An unresolved
parameter stays source evidence; a family match is not exact variant coverage.
Canonical reviewed definitions are the authority for the individual parameter
meanings, not the earlier snapshot inventories.

## Optional N4-origin annex

**Optional legacy-source annexes:** The `reinforcements-extra-n4-reference`
collection is deliberately separate from `n5-core-v5.3`. Its three
current-visibility records (`rule:reinforcements-extra`, `skill:commlink`,
`skill:request-reinforcements`) explain a **still-referenced optional
N5-era mode through N4-origin procedures**, with explicit source-edition
notices. They do not assert that the N4 annex has been reissued or adopted
unchanged for N5. Commlink retains the official Army Skill family link;
Request Reinforcements is a rules-only `tactical-phase-step`, with no Army
carrier and no core Orders/AROs declaration type. `Commlink (+X)` is
mapped in the **curated source** to two exact `reviewed-extra`
entries: Army Skill 260 extras `298/TEXT:+1` and `299/TEXT:+2`,
respectively `max-trooper-count-increase` by one or two, scoped
solely to `optional-reinforcements-extra-army-list`. The
validator rejects any other source signature or effect scope.

The current Rules publication retains those typed facts and the exact
optional-mode applicability. The separately qualified N4-origin reference
does not establish N5-native procedural authority or compute list legality.
The Reinforcements Extra page uses current source-backed Section and
parent memberships; it never assigns Section units to Main Sections.
See [season ownership](season-publication-ownership.md#ownership-decisions).

## Rule-variant usage index — implemented, release-artifact gated

The exact reviewed Skill/Equipment index is a read-only projection of
canonical rule identities, typed occurrence signatures, payloads and
source/application paths, not a second definition layer, roster builder
or game-state evaluator. Current complete builds embed it in
`rules_n5.db` (introduced in Rules v11).

**Rule identity and variant identity.** The primary grouping key is the
published canonical rules identity (for example `skill:martial-arts`),
resolved through reviewed source-to-application catalog membership and the
corresponding rules reference. A variant key additionally records explicitly
reviewed, typed differences: Level, MOD, named parameter, and any applicable
source-scoped restrictions. The typed signature is deterministic and
source-bound; distinct modifiers such as `+1 SD` and `+1B` cannot be merged.
A shared family does not imply that all of its variants are equivalent. Retain
the source catalog ID, raw variant/extras and rule citations as provenance.

### Source-parameter review and exclusions

Only an exact reviewed source variant and its supported occurrence
signature enter the index. Multi-extra signatures require independently
reviewed complete combinations, even when each single extra is understood.
Keep exact source buckets and IDs, distinguish source-native Skill,
Equipment and presentation encodings, and preserve occurrence modifiers
rather than translating them to unrelated permanent Unit attributes.

For example, source review distinguishes Lieutenant's extra match Command
Token from extra Special Lieutenant Order per Turn; a Doctor/Engineer or
MediKit PH value may target a particular Roll rather than rewrite a statline;
Hacking Device named program access differs from an Upgrade's scoped
modifier, and an unqualified Upgrade must not invent a program.
TAGCom/RemDriver modifiers belong to the reviewed recipient and scope,
not to the carrier's own stats. Review source-typed variants through the
curated rules `variantSemantics` metadata and validators. Do not generalize
one example to another source ID or accept an unknown combination.

Individual source decisions and examples in the
[dated source-variant reviews](https://github.com/frankysan/InfinityDB/blob/a7fc1900d73e4bc9b44561c20b04e58e73fbb8b6/docs/data-model.md#dated-source-variant-reviews-pre-publication-evidence)
are historical evidence; current exact signatures are in curated records,
pinned validation manifests and source audit tests. Unresolved questions
remain with the clarification register and backlog. Do not carry forward
old unresolved counts as current coverage. The
[raw/normalized source test contract](testing-data.md#full-army-source-archive-provenance-tests)
and source-variant audit are the reproducible coverage checks.

Do **not** parse a variant from a display string, strip punctuation, infer a
parameter from a shared family name, or count an unresolved variant as a
verified specific one. Missing/ambiguous variant semantics remain explicitly
unresolved and are excluded from **variant-specific** totals, while their
reviewed family membership may still be reported separately.

**Occurrence provenance.** Resolve an actual Army membership through
`application_army_sources`, `army_units`, and
`logical_unit_sources`; only a concrete list occurrence is evidence that the
Unit can be selected in that application Army. Keep the original
`(source_army_id, source_unit_id)` and `availability_kind`. For each
direct source Skill/Equipment relationship retain its owning layer and full
source key:

- profile: `(army_id, unit_id, group_id, profile_id)`;
- loadout: `(army_id, unit_id, group_id, option_id)`;
- Unit-wide option: `(unit_id, option_id)`, attributed to an application Army
  **only** where actual list membership and compatible context establish it.

Preserve the source relationship's `occurrence_id`, position, quantity,
extras and raw value for evidence, with the appropriate
`profile_payload_occurrences` or `loadout_payload_occurrences` join.
The reusable payload's item position identifies its relationship *within*
that payload. Neither the item position, numeric payload ID nor source
`occurrence_id` is a portable cross-snapshot semantic identifier. Use the
existing logical-Unit-scoped payload hash to identify equivalent payload
content **within the pinned source/build context**, while retaining distinct
Army/profile/group/option paths and contextual AVA, Points and SWC.

**Counting policy.** Publish clearly named measures rather than one
unspecified “occurrences” count:

- **Unique Units (global):** count distinct `logical_unit_id` for the exact
  reviewed rule/variant, across all eligible concrete Armies.
- **Unique Units per Army:** count distinct
  `(application_army_id, logical_unit_id)` for that rule/variant. A Unit
  legitimately available in two Armies counts once **in each Army**, but
  only once in the global count.
- **Distinct profile/loadout contexts:** count the corresponding
  `(application_army_id, logical_unit_id, owner_kind, payload_identity,
  exact_variant_signature)` once within each owner kind; report profile and
  loadout counts separately. Multiple rows/positions or source
  representations pointing to the same semantic payload do not inflate
  these totals. Each context still exposes *all* original source paths,
  group IDs and option-specific AVA/Points/SWC for drilldown.
- **Source relationship rows:** a separate provenance/debug measure, never
  the player-facing Unit denominator. Multiple same-variant rows may be
  preserved here even when they yield one Unit/context membership.

Variant membership is formed as a **set**, not a sum across profile Skills,
loadout Skills, Army-specific copies, or source IDs merged into one canonical
catalog family. Profile and loadout scopes remain distinct because a
loadout-only variant does not apply to every loadout, and Unit-wide options
are not implicitly assigned to every profile. Includes and Peripherals
require separately validated, explicitly labelled inheritance/relationship
paths; do not expand or multiply them into direct usage. Metadata-only
catalog definitions, chart outcomes available only after a Booty or
MetaChemistry roll, disabled/unavailable alternatives without concrete
membership, and broader declared faction membership alone are **not**
direct occurrences. An included target must not be silently promoted to a
selectable standalone option.

The generated index must retain pinned Army snapshot/build provenance and
rules-source/revision provenance. A source update, unresolved application
catalog mapping, contradictory variant parameter or unsupported relationship
shape must fail closed or remain flagged, not silently change totals. Public
links must resolve the canonical rule/variant and the actual Unit, Army and
compatible profile/loadout context; identifiers in this section describe
join semantics, not new public routes. Validate duplicate-source, reused
payload, repeated-row, cross-Army, shared-family/different-Level,
profile-versus-loadout and unresolved-variant fixtures before publishing.

### Build validation

The candidate builder (`tools.data.build_variant_usage`) validates direct source
rows and typed signatures against the matched selected Army/Rules publication.
`variant_usage_includes.py` also compares every retained raw Include with
its materialized edge, preserving multiplicity, quantity, raw fields and
the full source owner/target path. Include traversal uses source contexts,
not payload IDs: equivalent payloads never create cross-Army paths.
Missing or ambiguous owners/targets, duplicate source keys, materialized-row
drift and cycles fail closed. Repeated targets through different source
positions retain separate deterministic paths. A shared Unit option's target
Army identifies only its target, not compatible membership for its parent.

Peripheral validation reuses the reviewed identity validator against an
independent verified source rows and materialized
application relationships. Every source attachment must match its published
row and named source definition. Reviewed Controller access pools retain their
relationship/type/source identity and independently resolved Controller and
target profile contexts. Missing metadata, changed access pools, ambiguous
owners and cross-Army targets fail closed. An access pool describes eligibility,
not actual selection or possession of the Peripheral's Skills.

Shared Unit-option occurrences retain exact `compatible`, `disabled` and `raw`
source fields, with parity against their published parent. No reviewed
compatibility resolver currently establishes a concrete Army/profile context
for these options: the explicit status is `source-only-unverified`. They remain
source rows, excluded from Army, Unit and profile/loadout totals even when a
raw compatibility value is populated. Neither an available Unit nor an Include
target proves parent-option compatibility. Supporting a reviewed compatibility
shape later requires a separate validated mapping/contract; the current snapshot
has no direct Skill/Equipment rows on shared Unit options.

Candidate reports are ignored diagnostics; exact source generation and
Rule definition coordinates must agree. The old loose `variant-usage.json`
publication and its promotion/check switches are retired. See
[data validation](testing-data.md#research-receipts-and-publication-candidates)
for current candidate and inspection workflows.

### Rule-variant usage API

The current Rules database supplies the exact public read model
from SQLite. The API shape, canonical `variantKey`, set counts, source paths,
reviewed extras and Developer Mode presentation are unchanged. It never reads
or falls back to `variant-usage.json`; stale adjacent JSON is ignored. Low-level inspection also supports a selected Rules file outside the Army directory,
provided the embedded source fingerprint and export generation match.

`variant_usage_groups` stores the canonical identity, collection/record foreign
key, counts, and typed coordinates into that existing reviewed variant definition.
`variant_usage_source_rows` has globally unique `(catalog, owner_kind, occurrence_id)`,
ordered group membership, source/application Army and Unit identities, explicit
profile/loadout/shared-option paths, payload context and the exact reviewed
parameter/extra/combination coordinates. `variant_usage_extras` preserves each
row's ordered source positions, IDs, types and raw values. Shared Unit options
retain their unverified compatibility source and contribute zero direct Army,
Unit and profile/loadout totals. Includes and Peripheral context remain outside
direct usage; unresolved/family-only rows remain build diagnostics.

The variant-usage tables contain no opaque usage-payload/effect JSON. Meanings remain owned
by the existing canonical Rules definitions in `records.variant_json`, which
is pre-existing rule-model serialization debt rather than a second usage model.
Reads use the resolved coordinates, not a new source-interpretation pass; they
reconstruct and verify the canonical signature. Equivalent reviewed TAGCom
spellings can share a semantic group while keeping their distinct exact source
coordinates and extras. Missing, negative, out-of-range or mismatched references
fail validation instead of silently selecting another definition.

`variant_usage_metadata` records the Army archive/file/export-pair SHA-256 values,
logical content fingerprint and exact group/row inventory. It never stores the
Rules database's own final file hash. The API adds that hash after opening the
completed file, and variant/API cache validators change with Rules bytes. Startup
and database-set health check typed relationships, counts and fingerprints.

Unknown, stale or malformed embedded facts fail closed, and without a
valid read model `/api/variant-usage` returns `503`.

The API requires one canonical `record_id` such as
`skill:doctor` or `equipment:medikit`. It returns only that record's exact
variant groups in stable variant-key order, with the source-pair provenance,
set-based counts, and source-scoped occurrence contexts. Unknown query
parameters, repeated filters and non-Skill/Equipment record IDs return `400`.
When a matched publication is loaded, canonical Skill and Equipment detail APIs
expose `variant_usage_published: true`. Their ordinary pages then request every
reviewed canonical rule ID actually attached to the item's family and source
variants, deduplicate those IDs, and render the matching groups together in an
Developer Mode **Exact reviewed source occurrences** section alongside the existing
catalog-wide Unit-usage lists. If no curated rule IDs are attached, a verified
canonical catalog slug may be used as a single fallback identity. The UI never
guesses rule IDs from display names. Each exact group
retains its reviewed signature and source-row count; expanded rows link to the
logical Unit and selected application Army, with separate profile/loadout source
IDs and group anchors where the Army presentation has an unambiguous identity.
Repeated source rows in one published profile/loadout context have only one
browser link; `unit_option` rows without verified Army compatibility remain
unlinked, with an explicit notice. These are not source-inferred Army memberships.
When the publication is missing, the catalog detail flag is `false` and browsers
do not request the unavailable endpoint or present an empty index as proof of no
usage.

### Source-row identity and counting contract

Each source row is uniquely identified by `(catalog, owner_kind, occurrence_id)`.
The [occurrence and counting policy above](#rule-variant-usage-index--implemented-release-artifact-gated)
is authoritative: preserve raw extras and exact owners, count distinct
logical Unit/Army/context sets, and keep context-only Include/Peripheral
relationships and unverified Unit options out of direct totals.

## Structured Skill reference charts

**Current.** Martial Arts, Booty and MetaChemistry use generated Army tables,
projected through Skill detail `structured_reference`; curated Skill records
own their rules explanations and citations. Original Army row values remain
intact. Martial Arts hides the PS MOD column when every value is absent,
while retaining the separate Burst and Special Dice meanings.

Booty exposes typed `conditional_outcomes` for rolls 12, 16, 18 and 20,
separating TAG and other-Troop-Type results. MetaChemistry exposes typed
`outcome_components` for its five combined results (16–20), distinguishing
Attribute modifiers, MOV values, Skills and parameters. Unsupported compound
or conditional syntax fails closed instead of merging effects as free text.

Reviewed outcomes carry additive canonical `public_reference` links only when
the destination resolves uniquely. Booty's HMG uses the reviewed Heavy Machine
Gun alias; parameterized Skill/Equipment outcomes retain their printed variants
while linking to the owning family. MetaChemistry's six Skill occurrences link
to five families, preserving Immunity (ARM)/(Enhanced). Attribute modifiers
and MOV remain typed text. These are reference projections, not selected random
results, permanent Unit-profile changes or an executable effects engine.

Source/version, PDF pages, exact Wiki revisions and historical FAQ comparison
belong to [the reviewed chart provenance](n5-source-history.md#reviewed-10-structured-skill-chart-provenance).

## Restrictions Chart and typed constraints

The N5.3 p. 194 chart is authored in
`config/validation/restrictions-source-chart.json`. Its six subjects and
14 negative conditions are represented by two distinct models:
`restriction_constraints` and the chart display projection
(`restriction_chart_rows`, `restriction_chart_conditions`,
`restriction_chart_qualifiers`, `restriction_chart_metadata`).
Source identity, PDF SHA/page, row order, exact owner/target IDs, subject
kind, scope, action and typed qualifiers are retained. Build/read validation
checks chart-to-constraint correspondence and source/content fingerprints.

The separate typed model in
`src/infinity_db/restriction_conditions.py` compiles the reviewed
finite source chart into **14 negative constraints** with five
operation kinds: `state-entry`, `skill-declaration`,
`terrain-traversal`, `directional-skill-movement` and
`army-role-selection`. Each operation includes the reviewed target
record when available and only its valid qualifiers: ladders are
terrain traversal without a Skill target, Jump has `direction=upward`,
and Lieutenant is an Army `role=lieutenant` selection. Subjects have
source selectors or existing canonical owners; the three Troop Type
selectors have no canonical record IDs. The browser projection retains `subjectKind` and the typed
`operation` object for exact source semantics and future integration.

The additive **`GET /api/restrictions`** contract returns
`formatVersion: 1`, `available`, `source` (ID, printed page,
PDF SHA-256), `polarity: prohibition`, ordered `items`, and
`evaluationSupported: false`. Each item contains `subject`,
`subjectKind`, nullable `ownerRecordId`, `action`,
`operation: {kind, qualifier}`, nullable `targetRecordId`,
`scope` and `polarity`. Optional `subject` and `record_id`
filters are conjunctive and reject invalid identifiers.
The `/api/restrictions/chart` endpoint exposes the six-row display
reference, while `/api/restrictions` exposes typed prohibitions.
The standalone chart remains a public reference; relevant
Skill, Equipment and State reference links are Developer Mode details.
The historical static JSON is a checked input, not a current serving
fallback. Older explicit Rules fixtures retain their version-aware API
contract: missing historical typed constraints report unavailable rather
than manufacturing rules from generic edges.

**Legacy relationship consumer review:** the reviewed Motorcycle →
Jump and Irregular → Lieutenant graph edges are retained as
`restricts-use-of` for old API consumers, without adding or
removing any `record_relations` rows. Their shared player-facing
`display_relations[].presentation.label` strings are now
**source-scoped** in both directions: Motorcycle only prohibits
upward Jump while mounted (horizontal/downward Jump remain
unrestricted *by that rule*), and Irregular Training disqualifies
Lieutenant **selection** rather than all use of a Skill.
`src/infinity_db/rule_relations.py` owns the two exact
source-target presentation overrides; other uses of
`restricts-use-of` retain generic labels. The legacy API structure is preserved. The 14 typed source restrictions, not these generic
graph edges, remain the source of conditional semantics; the seven
source-only/unrepresentable generic edges are not manufactured.

Army Irregular Training remains scoped to matching Order occurrences,
not a generic profile-wide Skill. No missing negative edge establishes
permission. Neither projection evaluates action legality.
See [data validation](testing-data.md#focused-reference-regressions).

## Dated FAQ/errata layer (published reviewed subset)

FAQ rulings use independent `faq-ruling:*` semantic identities. The base
Rule/Skill/State definition is not rewritten when a later FAQ clarifies it.
The existing collection/definition boundary retains the source document's
identity, authority, effective date, citations and history; individual
rulings add a required validated `facts` contract (see
`data/curated/README.md`): question, answer, affected `topicIds`,
original publication identity/version/date/page, exact applicability by
rules revision plus effective date and optional ITS season revision/scenarios,
selected official citation with editorial selection reason, explicit
conflicting citations and predecessor `supersedes` IDs.

Known differences in FAQ question scope may also be explained on the owning
base reference through `facts.sourceNotes`, without changing the selected FAQ
answer or classifying consistent answers as conflicting. The Stealth and
Deployable references retain their respective English-selected contexts and
describe the narrower or broader Spanish question separately. The same source
context mechanism discloses unresolved Army qualifiers on Hacking Device Plus,
Journalist, Religious Troop, Doctor/Engineer, CC Attack and Infiltration.
These notes do not create typed effects or change source-owned occurrence
parameters. Engineer's bilingual contact note retains the English-backed
requirement while identifying the omission on Spanish N5.3 p. 98.

**Source precedence is applicability-first, not newest-first.** Core
definitions remain authoritative baseline material. Only a ruling explicitly
reviewed for the requested rules revision, effective date, and applicable
season/scenario may be considered as an additional clarification; newer
documents cannot retroactively or globally override unrelated source
contexts. Cross-posted/carried-forward answers preserve one identity and
original publication date, not duplicate FAQ entities. Disagreements are
separate evidence with a reviewed source choice and explanation. An explicit
supersession has effect only where applicability overlaps and the cited
predecessor has been verified; it must not delete historical evidence.

Currently `curated.py` validates this **authoring contract** for FAQ
definitions, and the rules exporter validates FAQ links across collections:
current canonical topic and scenario targets, retained historical FAQ
predecessor identities, consistent cross-posted original provenance,
acyclic supersession and overlapping revision/date/season/scenario scopes.
Supersession is explicit and limited to potentially overlapping contexts;
a later document date by itself still grants no precedence.

The **read-model and explicit-context API foundation** now selects only
reviewed, current FAQ identities matching topic ID, exact rules revision,
date, optional season ID/revision and optional scenario. It requires that
the chosen source, original publication and current collection already
exist on the requested date. An active scoped successor suppresses an
applicable predecessor only for the same topic; recency alone does not.
The result retains independently cited answer/provenance/conflict evidence
and matched applicability, separate from the unmodified base Rule/Skill.

`RulesDatabase.faq_rulings_for_topic` and `GET /api/faq-rulings` provide
that projection. The API requires `topic_id`, `rules_revision`, and
`as_of`, with optional paired `season_id`/`season_revision` and
`scenario_id`; it never defaults to the newest publication.
For matched scenario-scoped applicability, the backend also supplies
`applicability_note` from the reviewed source-selection explanation; general
FAQ matches return `null`. Normal browser cards show that note in secondary
source text even without conflicting citations. Conflicting-source cards
retain their existing discrepancy disclosure instead of duplicating the note.

Twenty-nine reviewed FAQ entries are now published from
`data/curated/rules/n5-faq-v0.1.json`: nine first recorded in v0.1 and
twenty **carried forward from v0.0**. Each carried ruling retains original
English v0.0 source/version/page separately from the currently selected
English v0.1 page, and a corroborating Spanish v0.1 citation. The
v0.0 record date 2025-10-15 is the associated official update anchor;
the exact PDF publication day is not independently verified. All
currently selected rulings require explicit N5.3 applicability, and
the stable ruling ID is reused across the cited publications.
The shared browser presentation now covers affected Equipment,
Scenario, Skills, Traits, States, General Rules and Hacking Programs,
with Fireteam FAQs appearing on the Fireteams page rather than a
competing rule route. A single topic may have multiple applicable
clarifications, and the same ruling may be discoverable from
several referenced topics without cloning its identity.
The N5.3 Basic Rules `rule:deployment-phase` is now a canonical
General Rules identity, cited to N5.3 printed p. 15. The v0.0-origin
FAQ about repositioning before Roll/measurement is attached to that
general rule, not to a specific Deployment Skill, and remains a
separate dated explanatory overlay. Existing Skill/Army data are unchanged.

The Annihilation-only Ancillary ruling is a conservative InfinityDB
applicability selection, not a claim that the ITS-section FAQ explicitly
names Annihilation. N5.3 uses the same Killing clause for Annihilation
(p. 150) and Firefight (p. 155), but FAQ v0.1 (English/Spanish printed
p. 4) does not name either Core mission. Shared Killing wording and the
FAQ's generic scenario-objective language do not justify adding
Firefight to the selected scope. Widening requires scenario-specific
source support and a reviewed applicability change. The source label
`2026-09-01` is the project-documented announcement-era anchor, not
a separately established document publication date. The Fireteam Type ruling
uses the consistent English HARIS three-to-two-member example. The contradictory
Spanish v0.1 count is published as separate conflict evidence; an official
correction remains open.

**Current applicability boundary:** The FAQ
read model remains a **current N5.3 reference**, not a historical
replay service. The 20 answers carried forward from v0.0 preserve
their earlier source identity but are selected from v0.1 and reviewed
only for N5.3 from the 2026-09-01 announcement-era reference anchor.
Nine answers first appear in v0.1. An older
`facts.originalPublication.publishedDate` is **not** an applicability
grant. The selector independently requires that the selected source
anchor, original source anchor, collection effective date and
ruling-specific applicability window all permit the requested date,
and that the rules revision, season and scenario match. A date supplied
to the explicit-context API is therefore a **filter over published,
reviewed current selections**, not a request to reconstruct the rules
and FAQ available at that historical instant.

Historical FAQ replay and user-selectable date/season controls in the
browser are deferred. They require separately authored and reviewed
v0.0 source selections and applicability for the actual historical N5
rules revision(s), compatible historical topic/Scenario identities,
source-specific effective-date evidence or clearly marked anchors,
and explicit version/season context for the reader. Historical
collections must remain independent of current canonical composition.
Do not backdate a v0.1 selected citation, copy N5.3 applicability
into N5.2, claim a source's PDF creation day is a publication day, or
derive historical supersession from recency. The same stable FAQ ID
may carry distinct reviewed historical contributions; duplicate
current definitions are not an acceptable replay mechanism.

The generic supplement mechanism must not auto-attach a ruling to a core
topic by name or by a newer collection date.

## Domain ownership and links

The [application-domain registry](application-domains.md) owns route-backed
domains and embedded vocabularies. Semantic identity does not guarantee a
dedicated detail route. Search, Glossary and reference links preserve the
canonical kind/namespace; same-name concepts and navigation-only
`facts.relatedCategories` do not change rule identity. The owning curated
record keeps its conditional effects; see [rules semantics](rules-semantics.md)
for exact movement, cover, geometry and State interpretations.

### Reviewed Trait Wiki links in Rules v14

`config/catalogs/trait-wiki-references.json` is editable maintained
source curation. The Rules v14/compatibility-16 schema first materialized
its reviewed exact canonical `trait:<slug>` identities into relational
`trait_source_links`: source collection ID and existing Trait record ID,
stable position, reviewed display name and the exact observed Wiki
`/Traits#fragment` URL. Composite foreign keys link each row to its
current Rules record. `trait_wiki_metadata` stores the maintained
format/version, complete row count and deterministic content fingerprint.

At build and read time, the complete link set must match **all current
canonical Traits**, names and valid HTTPS Wiki fragments. Missing,
ambiguous, mismatched and altered source links fail closed; a link is a
reviewed locator, not an independently authored Trait definition or a
claim about live upstream Wiki availability. The exact source JSON
and builder-input hash remain provenance; no runtime link inference
from slugs, names or unverified URL transformations is introduced.

`TraitCatalog` reads `RulesDatabase.trait_wiki_links_payload()`
from the current Rules database rather than packaged maintained JSON.
The public `/api/traits` listing and detail shape, `wiki` fields,
canonical identifiers and browser links remain unchanged. Historical
schema adapters are separate source/fixture compatibility paths.

## Embedded Rules projections

The complete Rules v24 publication retains the following current
build-time projections. Introductory schema numbers identify their
storage lineage, not standalone serving requirements. All scope-bound
projections are checked against selected Army/ITS fingerprints; older
explicit fixtures can use the canonical composers.

### Composed current records in Rules v18

Rules v18/compatibility 20 retains the authoritative relational tables and
all v17 publications. The final build derives `composed_rule_records` using
the existing composition and reverse-relation functions. Each row has a
semantic record ID, a scenario-context key (empty for the ordinary current
view), kind and serialized composed record, including source contributions,
citations, labels, resolved relation endpoints and Army links.

Only affected record IDs receive contextual rows, not a copy of every record
for each scenario. A contextual read prefers its exact selection, otherwise
uses the ordinary record; scenario-only records have no ordinary row.
Kind and reverse-lookup queries retain their ordinary current scope and
ordering. Army links remain opt-in on the public read model.

Validation checks the selection matrix against current source definitions
and scenario scopes and verifies its content fingerprint. The final build
binds the projection to the existing matched publication provenance.
Historical/standalone Rules v8–v17 retain canonical runtime composition.
ITS season databases remain separate; this projection does not change
their composition or ownership. Maintained-text token resolution that
depends on consumer-local routes, Army identities or ITS context remains
request-time work.

### Global search projection in Rules v19

The complete build publishes `search_index` and `search_index_terms` after the
Army and both ITS databases are finalized. Canonical catalog enumeration provides
ordered public result metadata and distinct normalized search terms, including
Unit aliases, profile/loadout names and scoped Scenario Skill identities. The
projection stores no full catalog/detail records. Queries normalize the input,
match substrings within individual terms and dynamically apply the existing
prefix/name/domain ranking, preserving canonical tie order.

Rules v19/compatibility 21 binds the projection content fingerprint to the Army
SHA-256 and ordered registered ITS publication keys and SHA-256 hashes, without
binding the Rules file to its own hash. Complete serving rejects missing, corrupt
or scope-mismatched projections; explicitly selected older or partial fixtures
retain the canonical composer. Normalized source tables remain authoritative.

### Catalog projections in Rules v20

Rules v20/compatibility 22 publishes `catalog_summaries` (raw Army and
composed public list/filter views), `catalog_details` (canonical raw Army
detail records, with ordered Unit IDs in each source-specific variant),
and `catalog_usage_units` (one all-availability display record per logical
Unit referenced by those variants). The canonical composers generate all
three; the same summary count semantics and source-specific extras are
retained. Details reconstruct the Unit lists using shared records rather than
storing repeated Unit payloads. Curated enrichment, contextual matching and
prospective counts continue to use their existing runtime paths.

The projection is fingerprinted against the same Army and ordered ITS scope
as global search. Complete serving requires it; explicitly selected older or
partial sets use canonical runtime composition. The projection does not
replace normalized occurrences or encode arbitrary filter combinations.

### Specialist candidate projection in Rules v21

Rules v21/compatibility 23 adds `specialist_candidates`, one sorted set
of logical Unit IDs per supported context (standard, domination, supplies,
firefight). The canonical Specialist composer derives candidates from the
reviewed Rules qualifiers and source-specific Army Skill occurrences,
excluding Chain of Command (Non Specialist) as a qualifying variant alone.
The fingerprint binds the same Army and ordered ITS publication scope as
global search. Older or partial explicitly selected sets use the canonical
composer. The Explorer still intersects candidates with contextual filters;
membership is not an assertion that every profile or loadout qualifies.

### Maintained-text target projection in Rules v22

Rules v22/compatibility 24 adds `maintained_reference_targets`, a compact
JSON document keyed by semantic record and composed scenario selection, plus
the reviewed Weapon Property vocabulary. Each target retains its label,
contextual-route restriction, canonical public route and parsed summary
tokens (or the plain Weapon Property preview). The build derives these from
the composed records and the existing public-route resolver; the fingerprint
binds the Army and ordered ITS scope. The complete selected application loads
the index once, without duplicating the composed rule records.

The consumer still selects the exact scenario override with ordinary fallback,
applies local rule anchors, explicit display labels and plural forms, and
resolves nested preview references without a second preview level. Scenario-
scoped definitions retain context-specific routing restrictions. Records owned by the selected
ITS publications retain the existing additional-record resolver fallback;
missing references still fail closed. Older or partial explicitly selected
sets use the canonical resolver. Returned tokens do not mutate shared inputs.

### Reference page projection in Rules v23

Rules v23/compatibility 25 adds `reference_pages`, containing the
canonical raw Glossary entry list, the core Orders/AROs declaration matrix
and a separate extension for each current core scenario. The builder uses
the existing catalog and declaration composers. The scope-bound fingerprint
and complete page-key coverage are validated alongside global search.
The Glossary attaches maintained-text tokens at runtime using the existing
reference target projection. Orders/AROs combines the base matrix with the
selected core scenario extension, after the existing query validation.
Explicitly selected older or partial sets retain the canonical composers.

### Catalog usage presentation in Rules v24

Rules v24/compatibility 26 extends `catalog_usage_units` with `presented_body`,
a second shared representation containing the canonical public Unit and Army
slugs and symbol paths. The same Army SHA-256 scope covers the embedded symbol
publication. The catalog fingerprint includes both bodies; raw consumers retain
`body`. Source-backed catalog API detail routes enrich their compact variant
records before expanding the ordered Unit IDs using the prepared presentation.
Rules-only and presentation-encoded items and explicit older schemas retain
the existing live enrichment path. Neither representation is retained in an
expanded catalog cache.
