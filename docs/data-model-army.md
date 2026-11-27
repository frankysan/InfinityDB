# Army data model

**Project domain:** Data processing

This document owns application Army/Unit identity, context, availability,
filtering and persisted Army projections. See the [data model](data-model.md)
for common provenance/storage and [Army history](data-model-history.md)
for historical identity and observations.

## Identity model

InfinityDB keeps **source identity**, **application identity**, **relationship context**, and
**presentation identity** separate.

### Army identities and roles

`application_armies` is the canonical runtime Army projection. Army-list source records and metadata
factions are evidence used to build that projection; they are not interchangeable identities.

Current roles include main, sectorial, non-aligned/grouping, and reinforcement. Role/grouping is
derived from imported relationships and reviewed policy rather than ID ranges. In particular:

- source identity `1` remains mercenary source provenance;
- current Non-Aligned application grouping is represented separately (source grouping identity
  `901` in the current snapshot);
- reinforcement lists retain explicit parent relationships; and
- a grouping identity may exist in source metadata/source lists without being independently playable.

Playability, catalog/discontinued status, grouping, parentage, concrete roster availability, broader
faction membership, and browser display identity are separate facts.

`main_army_id` is a compatibility-named application grouping field, not authoritative roster
membership. `display_army_id` is the reviewed presentation identity used for faction symbol/styling
where it differs from source/main grouping. Browser code consumes these projections rather than
special-casing Army IDs.

### Logical Units

A logical Unit groups source Unit representations that reviewed/source-derived evidence says are the
same application Unit. Build-time identity processing materializes that mapping; runtime queries do
not recompute it from names or ID arithmetic.

The logical Unit layer owns game-wide Unit identity and aliases while preserving every source
occurrence needed for Army/profile/loadout context. A reinforcement or optional-mercenary source
representation can therefore belong to the same logical Unit without erasing its distinct
availability path.

Configured aliases remain maintained policy and are pinned into generated metadata; they are not
rewritten into source rows.

### Spec-Ops and TEAM-OPS source-choice charts

Army `spectables` is source-native *choice inventory*, not a configured roster or a Trooper's
selected upgrades. Each source Unit's chart is stored unchanged in `logical_unit_spectables`;
`Database.get_unit()` exposes it under `source_charts`, scoped by exact
`source_unit_id` and carrying source name and Army source-version/file provenance.
Source names resolve through the materialized logical-Unit/alias projection by exact
source Unit identity; normal chart serving does not read the raw `units.name` copy.
The projection retains the two independent `table` and `specball` collections,
source order, and every attribute in compound entries. Source catalog IDs are
resolved to available names and stable public routes; unresolved extras retain their
numeric source IDs and are not silently dropped. Raw `q` values and individual
MOV components are shown as source notation because the source payload alone does
not justify interpreting all of them as modifiers or final statline values.

The Unit detail page provides an ordinary read-only reference with relevant core
Skill links. It does not apply upgrades, validate a list, equate Spec-Ops to
ITS TEAM-OPS, or interpret the in-game Initial/Enhanced Profile transition.
The separate configurable-list/session feature remains deferred.

### General profile

The **General profile** is an InfinityDB abstraction for profile information that can safely be shown
once for a logical Unit rather than repeated for every Army occurrence. It is not an upstream Army
entity.

Only semantically compatible profile data may be consolidated. Materially different statlines,
profile identities, classifications, characteristics, or other contextual facts remain distinct.
Source profile IDs/names remain available as provenance even when multiple occurrences share one
application payload identity.

For presentation, when every loadout compatible with a General-profile identity
carries the same Skill, Equipment or Weapon with the same quantity but differing
extras, General displays its **base item without extras**. The base is a
display-only common denominator, not an assertion that the Army source publishes
a separate no-extra occurrence. Loadouts with only that base do not repeat it;
loadouts with actual extras retain their exact variants. An item absent from any
applicable loadout, or present with different quantities, is not promoted.
Existing identical-extra shared variants retain their own identity. Source
profile/loadout payloads, relationship semantics and filtering remain unchanged.

The [build-time materialization direction](architecture.md#design-direction-build-time-materialization)
changes when General profiles are composed, not their identity, semantics
or provenance. Army v33 stores the complete General-profile projection for
both Extended Explorer and Unit details. Explicit requested-Army selections
that change the effective set of occurrences retain contextual composition.

### Official Army Unit destinations

The Unit-detail API adds `official_army_links` to each Army occurrence group.
Each target contains `army_name`, `unit_name` and `href`. These are external
source destinations, not InfinityDB domain identities. The resolver uses the
selected snapshot's metadata faction slug and the exact source Unit ID's
`army_lists.resume` slug, joined to `army_units`. Logical aliases do not
replace either path segment. Reinforcement Units use each source parent
Army's slug and the reinforcement resume's Unit slug. Missing, malformed,
nonmember and ambiguous destinations are omitted, including slugs shared by
the main and reinforcement resumes. This read-only lookup is cached per
database instance; no new schema or live upstream dependency is required.
The links open the current official application, which may have newer data
than InfinityDB's pinned snapshot. They do not prove list legality.

### Unit and General-profile symbols

Every published logical Unit has exactly one effective graphical symbol. A General profile inherits
that Unit symbol unless InfinityDB can resolve one distinct profile symbol for its normalized profile
identity. Raw Army `logo` values remain occurrence-level provenance and are not themselves the
semantic assignment. The tracked publication retains every authoritative profile-logo resolution as
evidence, including logos that are primary for one source Unit representation, because source Units
can later collapse into one logical Unit while their distinct General profiles remain meaningful.

Army profiles explicitly identified as Peripherals publish into a dedicated
`peripherals/<main-army>/<peripheral-name>.svg` namespace when that profile name is Peripheral-only,
including Units whose primary profile is itself a Peripheral. The Peripheral name comes from Army's
Peripheral metadata when it can be matched without guessing. Main-army folders follow the same
faction-parent hierarchy used by Unit symbol publication. Peripheral is contextual Army metadata,
not a global property of a profile name. When the same physical symbol is evidenced under the same
profile name in both Peripheral and normal Unit contexts, InfinityDB treats that name as mixed-role:
its artwork stays Unit-owned under `units/`, including any additional contextual variants of that
name. Byte-identical occurrences therefore resolve to one Unit-owned symbol, while genuinely
distinct artwork remains preserved as separate Unit-profile assets. Likewise, if Army reuses parent
Unit artwork for a Peripheral occurrence, the physical asset remains Unit-owned. Distinct physical
assets for Peripheral-only names remain preserved as context-suffixed Peripheral variants rather
than being silently discarded.

The tracked symbol publication may promote a cross-Unit profile-symbol consensus when one
published symbol is a strict majority across distinct parent Unit symbols for that profile identity
and is observed as a non-Unit override against at least two different parent Unit symbols. Repeated
Army occurrences of the same Unit count once. This permits
InfinityDB to repair repeated Army assignment errors without treating a single Army-specific
variant as a global graphical identity. Ambiguous contextual evidence falls back to the Unit
symbol rather than exposing multiple effective symbols for one General profile.

### Profile and loadout payloads

Profiles and loadouts are treated as structured semantic payloads rather than deduplicated by display
name alone.

- A **profile payload** owns profile statistics and profile-scoped categorical facts.
- A **loadout payload** owns shared loadout content such as weapons, equipment, skills, Orders,
  and includes. Points and SWC belong to `loadout_payload_occurrences`, so equivalent content can
  be shared without erasing Army-specific prices.
- Context tables connect those canonical payloads back to source Unit, Army, profile-group, and
  loadout occurrences.

Exact structural equality is useful evidence but does not by itself justify semantic identity when
source context says two records mean different things. Conversely, equivalent payloads may be shared
when the contextual relationships remain explicit.

## Availability and membership

InfinityDB distinguishes several relationships that source data often places near each other:

- **Army-list availability** — the Unit/profile/loadout occurs in a concrete Army list;
- **optional availability kind** — standard, mercenary, Spec-Ops, Team Operations, reinforcement,
  or other explicitly normalized availability path;
- **broader declared faction membership** — source-declared game-wide faction relationship that may
  exist even without a current selectable Army list;
- **main/grouping identity** — application grouping context;
- **display identity** — browser presentation context.

`army_units.availability_kind` is persisted application data. Runtime optional-unit filtering consumes
that classification rather than reconstructing it from source IDs.

Unit-list counts and roster membership operate on logical Units with concrete application Army
availability, so duplicate source representations do not inflate player-facing totals.

## Context-coherent filtering

Legacy queries that omit `matching_scope` keep the previous profile-group/loadout coherence model.

- AVA belongs to an Army/profile occurrence.
- Points and SWC belong to loadout occurrences.
- Troop Type, Classification, Characteristics, profile Skills/Equipment and other profile facts stay
  with their owning profile/profile group.
- Loadout-local Weapons/Equipment/Skills stay with the loadout.
- Unit-option facts remain Unit-wide when the source does not attach them to a profile group.

With the legacy matcher, AVA/Points/SWC constrains an Army/profile-group/loadout context rather than
an unrelated alternative option. Explicit matching scopes are defined below.

An explicit `matching_scope` selects one of three nested source-backed
contexts, independently of each categorical AND/OR switch:

- `profile` (**Same profile**, fresh-view default): all AND criteria must occur
  on one exact Army/source-Unit/group/profile occurrence and its compatible
  selected loadout. Alternative profiles and unrelated models do not combine.
- `loadout` (**Same loadout**): criteria may occur on constituent source profiles
  and their one selected loadout, plus exact `profile_occurrence_includes` and
  `loadout_occurrence_includes` targets. Transmutation states in that loadout
  may collectively satisfy a reference query without implying simultaneous
  active-game-state abilities.
- `unit` (**Anywhere in Unit**): criteria may occur across alternative
  configurations and reviewed source representations of the same logical Unit.
  Source Unit-option properties and `unit_option_include_targets` contribute
  only at this broadest scope, and only from non-disabled Unit options.
  Another logical Unit never contributes.

An Include edge is resolved to a unique loadout occurrence in the same Army
and source Unit. Missing/ambiguous targets and cycles fail closed. Source
`profile_peripherals`/`option_peripherals` records establish attachments,
but embedded Peripheral identities alone do not publish property payloads;
their Skills cannot be inferred from names or eligible Controller targets.
`application_peripheral_controller_access` describes available choices, not
automatic inclusions. Aggregating properties never transfers ownership
from an included Peripheral to its Controller.

Disabled loadout occurrences remain available as unique Include targets, but
are not independently selectable root contexts in the explicit matching scopes. A group with only
disabled loadouts does not generate a synthetic root; a profile-only group
with no loadouts retains its normal profile context. Such Units remain
visible without filters, without inventing selectable configurations.

In the reviewed 2026-11-25 Army snapshot, Unit #965 KISS! (Repeater) has a
source omission: loadout option 3 has no Equipment entry for
Repeater (source Equipment 63), despite its explicit name. In Combined
Army and Onyx, the alternate KISS! loadout carries Deployable Repeater
(111); Next Wave has no alternate KISS! loadout. The three occurrences
were revalidated against the November archive before publication.
The authored, snapshot-hash-bound additions in
`data/curated/relationships/loadout-capabilities.json` are checked
against exact Army/source-Unit/group/option coordinates, loadout name,
catalog name and absence from source payload at build time. Only the
three KISS! (Repeater) occurrences in Combined Army, Onyx and Next Wave
are currently reviewed. Complete builds project validated facts into
`__infinity_metadata.reviewedLoadoutCapabilities`, with a curated
content SHA-256 and count, leaving immutable Army source payloads
untouched. Runtime Unit detail and the explicit scope evaluator read
only this database projection; the facts stay owned by KISS's selected
loadout and may contribute to Bit only through its exact Includes edge.
Other snapshot hashes do not inherit the correction. No arbitrary
source-name substring creates a Skill or Equipment fact.

With explicit scopes, numeric restrictions are applied to eligible contexts
before evaluating categorical requirements. Under `unit`, a qualifying
numeric occurrence can coexist with other categorical alternatives of
that same logical Unit, but cannot make a different Unit eligible.

Fresh Unit Explorer views default to `matching_scope=profile` and **AND within
each categorical filter** and **AND between filters**. Each of six categorical
filters has its own independent AND/OR switch. AND requires all selected
choices in one evaluated context at the chosen scope; OR requires any of its
choices, without double-counting Units. Different categories still combine
with AND. Shared URLs without `matching_scope` retain the legacy matcher and
show a compatibility selector until an explicit scope is chosen. Historical
links without `and_filters` retain legacy OR-within-category selection. Sorting,
pagination and extended presentation do not affect matching.

When an explicit `profile` or `loadout` scope is filtered, returned page
items can include `matching_contexts: {total, source_matches, examples}`.
The disclosure groups matching source occurrences with the same profile/loadout
names, cost and named Skills/Equipment/Weapons. `source_matches` preserves
the original occurrence count; `total` counts the grouped summaries.
Up to five examples show Points, SWC and at most three distinguishing catalog
items, preferring one each of Weapons, Equipment and Skills. Capabilities
shared by all matching summaries are omitted unless only one summary exists.
Names are resolved through the published catalog, not inferred from loadout
text or unreviewed extras. This is a concise comparison, not an exhaustive
loadout inventory or a claim that alternate profiles are simultaneously usable.
Broad `unit` scope and legacy requests omit the field rather than assigning
one configuration to a match assembled across alternatives.

The `/api/units` parameters `skill_id`, `equipment_id`, `weapon_id`,
`troop_type`, `classification` and `characteristic` accept one legacy
slug/numeric ID or up to 16 comma-separated selections. The API normalizes
and deduplicates identifiers in deterministic order and rejects repeated
query keys and malformed identifiers. Unknown values continue to fail closed.
The optional `and_filters` parameter accepts comma-separated category names:
`skill`, `equipment`, `weapon`, `troop_type`, `classification`, and
`characteristic`; omitted categories use OR. The `matching_scope` parameter
accepts `profile`, `loadout`, or `unit`; omission preserves legacy behavior.
Share-state v1 appends the new field after `and_filters`, keeping all historical
field indices and tokens valid without a version bump. An application catalog
choice may match through any of its valid source IDs, but distinct AND
choices must share the selected matching scope. NOT/exclusion is unsupported.

Presentation-encoded Equipment selections resolve through their source
Characteristics and respect the same profile-group/loadout context in combined
queries. **Cube and Cube 2.0 are not selectable from the Equipment filter menu**;
their choices remain in Characteristics, and their existing catalog routes and
historical filter URLs remain compatible. Unknown mixed identifiers fail closed.

The optional `/api/units?counts=1` response retains `usage_counts` and
`baseline_usage_counts`. When `matching_scope` is explicit it also exposes
`prospective_counts`; all maps contain `skills`, `equipment`, `weapons`,
`troop_types`, `classifications`, and `characteristics`, keyed by application
item ID, vocabulary ID, or encoded-Equipment slug. Every count represents
**distinct logical Units**, not profiles, loadouts or included models.

`usage_counts` retains its legacy **source-usage within the currently matching
population** interpretation, including the prior context-specific and raw
Unit-wide behavior. It is not the number of results after selecting an option;
existing API callers remain compatible. `prospective_counts` drives the scoped
player-facing menus. An **unselected** option has exactly the result `total`
after selecting it under current AND/OR and matching scope; a **selected**
option displays the current `total`. Both result membership and prospective
counts use one shared scope evaluator and an indexed source occurrence graph,
not separate database queries for each menu option. Explicit scoped browser
requests use `counts=prospective`, which returns the same prospective, baseline
and Army counts without calculating the unused legacy `usage_counts` map.
Existing `counts=1` clients retain the full response and legacy unscoped browser
links continue to use that mode. The immutable Unit graph precomputes optional
availability requirements per source occurrence. The scoped evaluator reuses
selection outcomes for identical property sets within a query, retaining all
matching occurrence identities; prospective counts deduplicate logical Units.
Catalog option IDs come from the same application identity graph as the
public catalogs, without calculating catalog usage statistics.

`/api/unit-filters?catalogs=1` adds a `catalogs` object containing the
Skills, Equipment and Weapons filter choices (IDs, names, public slugs
and source aliases) in the same order as the public catalogs. The default
response shape is unchanged. This projection skips catalog use counts
and unused rules presentation metadata. The browser overlaps initial Unit
results with filter initialization unless saved Army or categorical
selections require normalization. Public slug reads reuse a resolved
ID-to-slug index scoped to the immutable snapshot; unresolved identities
still return no slug.

`baseline_usage_counts` ignores discovery filters, Army selection and search,
but retains the optional-unit Settings flags (Mercenaries, Spec-Ops, Team
Operations, Reinforcements). With an explicit matching scope, the baseline is
computed using that scope's prospective counts, including source-backed
Includes. Without a scope, the legacy raw usage baseline is unchanged.
Options absent from the baseline are hidden unless already selected; baseline
options with zero current prospective matches remain selectable and dimmed.
Unlisted count keys mean zero. Count extensions are opt-in; API clients without
`counts=1` retain their previous response shape. The separate `army_usage_counts`
map counts distinct matching logical Units per visible application Army ID, using
the same memberships as the availability symbols across all result pages.
The Matching armies summary compares the number of visible Army IDs with
all playable or source-backed availability identities from `/api/armies`,
including Reinforcement sections and non-selectable grouping identities with
Unit memberships, but excluding historical-only identities. The collapsed
Currently shown breakdown groups visible identities by application role.
These are usage counts within the filtered population, not prospective Army
replacement counts. Optional-unit flags apply to both symbols and shown counts.

The Specialist Troops selector exposes `Standard set` as the single currently
distinct candidate set. Reviewed Domination, Supplies and Firefight candidate
sets are identical on the current snapshot; a regression test guards this
assumption. The API still accepts their context keys, and older UI URLs
normalize these equivalent choices to Standard set. Actual Specialist status
remains determined by the chosen scenario and profile.

The opt-in `extended=1` Unit list exposes the visible General profiles
from the same detail presentation pipeline, using the selected optional-unit
flags. Extended results render only these General profiles, with shared Skills,
Equipment and Weapons as plain text, including quantities and extras as on
the Unit page. Attribute differences are marked, and Army availability is
aggregated by General profile identity without conflating distinct AVA values.
Distinct General profile identities (such as a trooper and its peripheral)
remain separate. Army-specific profiles and loadouts are not rendered in
the Explorer. The existing compact `profiles` response is retained for
compatibility; the ordinary list response is unchanged.

Unit Explorer filter vocabulary may also apply a maintained application overlay without rewriting
the source facts. A combined source Classification can participate in more than one public
Classification filter, while source Characteristics that duplicate a canonical current Skill can be
omitted from the picker as redundant. The original category/characteristic rows remain preserved
and direct identifiers remain queryable for compatibility and provenance.

AVA preserves `Total` as a first-class display/exact-filter value. Negative ancillary/source AVA
sentinels are not ordinary player-facing AVA values. SWC preserves ordinary costs separately from
bonus/non-cost source forms such as `+1`, `+1.5`, or `-`; numeric ranges apply only where numeric
ordering is meaningful.

## Source-specific Unit information

Some source material is useful but cannot safely be promoted to game-wide Unit facts.

### Source notes

Non-empty source Unit notes are retained with source Unit identity, representative/source status,
and applicable Army contexts. The application may present those notes on the logical Unit while
keeping attribution visible.

### Composite Unit options

Top-level source options that combine multiple loadouts remain source-context bundles. InfinityDB
preserves their cost, miniature count, Order contribution, included loadouts, and source/Army
context. Source-local option IDs are not canonical cross-Army identities unless separately reviewed.

Verified normalized source rows (or their explicit legacy raw export) preserve fields not yet published
through these bundles (for example, direct Unit-option Skills/Equipment/Weapons,
and profile/group notes). The source-to-presentation audit keeps such fields
classified as potential presentation gaps even when empty in the selected source
snapshot, and separately reports **how many source values are actually populated**.
Newly populated fields must be reviewed before a data-completeness claim; absence
in one pinned snapshot does not justify permanently excluding their semantics.

### Source-field occupancy and publication limits

The [source-to-presentation audit](../tools/data/audit_source_presentation.py)
assigns a semantic/presentation policy to every normalized field and checks
actual source occupancy. Direct Unit-option item rows and profile/group notes
must remain losslessly available for future review even when absent from a
particular snapshot. Composite Unit options and source Unit notes have their
own current projections; empty direct item tables do not imply no options.

Spec-Ops/Team-Ops source choice charts are published as read-only reference;
configuration and chosen upgrades remain outside the immutable model.
The `minis` and `disabled` source-client flags are preserved without
guessing additional gameplay meaning. Explicit disabled-state handling in
context filtering is a selection rule, not a universal game legality verdict.

Use the [source occupancy gate](testing-data.md#curated-source-and-publication-checks)
with the matching normalized generation or legacy audit evidence as
supported by the current CLI. An occupied unrepresented field requires
review, not blanket suppression. Clean CI alone cannot establish source-byte
coverage; see [full source validation](testing-data.md#full-army-source-archive-provenance-tests).

### Selection and dependency constraints

Reviewed source selectors and same-Unit profile/loadout dependencies are materialized only when their
meaning can be represented without inventing list legality. Opaque source selector parameters remain
provenance rather than being treated as a complete list-builder rules engine.

## Peripherals and Controllers

Peripheral source encodings are normalized through a separate reviewed identity contract because
Army represents the concept through multiple shapes.

Current application semantics distinguish:

- embedded Peripheral entities/profiles;
- standalone Unit-backed Peripherals that reuse logical Unit identity;
- source mappings from Army coordinates to those canonical targets; and
- Controller access pools, which represent eligibility/selection rather than fixed ownership.

Peripheral subtype classification may link to canonical reviewed rules identities. A mapping that
cannot be supported by the pinned source evidence remains review work rather than being inferred by
name.

Runtime Unit detail consumes the materialized application relationships and never opens the curated
Peripheral JSON directly.

In Unit-detail presentation, a unique exact name-and-quantity match between a
source `Includes` target and an attached Peripheral is displayed only once as
**Included peripherals**, linked to that target loadout (for example, KISS!
(Repeater) on Bit). Other Include targets remain under **Includes**; Peripheral
attachments without an unambiguous Include target remain under **Attached
peripherals**. Controller eligibility appears separately as **Selectable
peripherals — available to select, not automatically included**. No
attachment, subtype, selected loadout, or requirement is inferred from an
access pool or a partial name match. The separate profile group of an
included Peripheral remains visible because its stats and loadouts belong
to that Trooper. Original source occurrences and API relationship collections
remain unchanged.

## Fireteams

Fireteam charts are Army-local structured source data. InfinityDB materializes one canonical
application chart per supported Army/source context while preserving:

- chart/type limits, including the raw Army value for provenance while projecting explicit
  `maximum`, `unavailable`, or `unlimited` application semantics before browser use;
- member requirements;
- Wildcards and parenthetical source terms;
- source notes;
- resolved logical Unit targets;
- FTO-eligible loadout references; and
- source provenance.

Reinforcement parent limits remain separate through the application Army graph rather than being
silently merged into a child chart. General Fireteam rules/Level bonuses live in curated rules data
and are composed by the Fireteams application surface; they are not source Army chart rows.
Fireteam Level curated facts allow an optional `sourceNotes` list for
provenance and rules-publication conflicts. These notes are displayed as
secondary text without affecting Level requirements or bonuses.

The chart read model exposes `wildcards_excluded` for the reviewed complete
observations `No Wildcards` and `No Wildcards Special Fireteam` (ignoring case,
whitespace and a terminal full stop or exclamation mark). The backend decodes
these explicit exclusions from the preserved observation; it does not infer
restrictions from arbitrary prose. `false` means no recognized exclusion,
not approval of Wildcard eligibility. The browser omits combined Wildcard rows
from excluded teams and retains a separate Wildcard card when no team can
display the pool. The source-separated view preserves every original chart row.

Each member also exposes `reference_issues` with stable codes and player-readable
messages derived from the persisted resolution and Army-local FTO loadout links.
An unresolved or ambiguous Unit, a global-only match, and a missing Army-local
FTO option remain distinct. A global Unit link is reference navigation, not
proof of Army-local eligibility. These issues are visible in ordinary member
rows, including combined Wildcards, alongside the original `comment` as a chart
annotation. Technical resolution/ID columns remain developer-only. Original
annotations supplement the legacy `equivalence_labels` projection; they do not
create new aliases or automatically interpret additional conditions. That field
and its persisted table retain their names for compatibility, but contain ordered
parenthetical source terms, not independently verified equivalence rules. Normal
charts label them **Chart terms**, alongside the exact original **Chart note**.
Parentheses alone do not establish a counts-as rule, profile eligibility or Skill
entitlement. In the pinned Shindenbutai source, Shizoku's `(Strategic Deployment)`
note matches the option carrying Skill 251, distinct from its two FTO options.
The Varuna Div names match Army-local ORC/Machinist loadouts; Triad/Triada terms
retain their chart context, including Reinforcement-only source rows. These
descriptive correspondences do not add generic eligibility relations or a rules
engine. See [annotation validation](https://github.com/frankysan/InfinityDB/blob/4774abde079a0e91ea87c9ee417c4ca1e2429403/docs/testing.md#fireteam-annotation-applicability).

`parent_charts` retains each Reinforcement Section's source-backed parent Army
reference, selected chart source and independent type-limit projection. A
`selectable` flag reuses the ordinary Fireteam Army picker eligibility; grouping
parents remain represented without a chart link. Normal Reinforcement pages show
these parent limits, including zero/unavailable values, separately from Section
members. An absent chart and an existing chart with no limits are distinct; neither
becomes a zero limit. Parent links use canonical public slugs and shared Fireteam
state. This is contextual reference information, not combined roster validation.

## Embedded Army projections

The following stages are retained in the current complete Army v34/v35
storage. Build validation pins source identity and checksum coverage;
explicit older fixture/source-only readers retain their own adapters.
Normal requests consume embedded projections, not the authored JSON.

### Equipment presentation encodings in Army v27

The editable `config/catalogs/equipment-presentation-encodings.json`
retains two reviewed Cube/Cube 2.0 characteristic mappings.
Introduced in Army v27/compatibility 36; retained in the current runtime.
`equipment_presentation_encodings` stores the exact canonical
Equipment slug, ordered position, source characteristic ID/name
and authored reason. Each characteristic ID is a local foreign
key to the selected Army's `characteristics` catalog and the
name must resolve uniquely, case-insensitively.
`equipment_presentation_metadata` records the maintained source
digest, source format/version, exact export-generation identity,
row count and full content fingerprint.

The published Army database includes these rows in its content checksum.
Optional standalone paired exports retain matching raw/application
generation metadata; the normal complete build emits no raw sibling.
Archived v26/compatibility-35 Army fixtures remain independently
readable under their version contract.

`EquipmentCatalog` reads v27 encodings from the selected Army
SQLite file without a runtime JSON lookup. On legacy v26 it
retains the validated source adapter. Equipment pages and canonical rules references retain their source
identities. Cube and Cube 2.0 appear under the Characteristics filter,
not in the Equipment filter menu; historical Equipment-encoded filter URLs
retain compatibility. No Equipment identity is synthesized from characteristic
spelling, and source-review mismatches fail closed.

### Reviewed Army Skill source classifications in Army v28

The editable `config/catalogs/skill-source-classifications.json`
retains six reviewed exceptions for Army's skill-like source bucket:
Bangbomb, BTS=3, GizmoKit, Infinity Team-Ops, MediKit and
Regular. These are source classifications, **not** newly created
N5 canonical Skills. The Army v28/compatibility 37 schema first embedded these
classifications; the current runtime retains them.
`skill_source_classifications` stores each exact numeric or
slug source reference, explicit reference kind, ordered position,
resolved application Skill identity, reviewed classification
(`equipment`, `attribute-override`, `source-marker`, or
`training`) and author reason. A composite foreign key targets
`application_catalog_items` with catalog `skills`; the
read-time resolver checks the original source reference still
resolves uniquely without inferring an N5 rule definition.

`skill_source_classification_metadata` binds the reviewed
configuration digest, format/version, six-row count, content
fingerprint and paired Army export generation. The published-content checksum includes these relational rows;
explicit standalone raw-pair exports retain matching generation metadata.
Older importer/fixture schemas have their own compatibility contract.

`SkillCatalog` reads v28 classifications from Army SQLite.
The Unit-detail presentation backend receives the same selected
database projection instead of re-opening maintained JSON; direct
source-only tools and older v26/v27 snapshots retain the
validated JSON adapter. The API continues to show the original
training/equipment/attribute/source-marker classifications and
preserves exact source Skill identity semantics.

### Unit Explorer filter semantics in Army v29

The Army v29/compatibility 38 schema introduced the selected
filter metadata used by the current runtime, built from the editable
`config/catalogs/unit-filter-semantics.json` build input.
`hidden_unit_characteristics` retains the two normalized slugs,
source characteristic IDs, authored reasons and source ordering.
`source_classification_memberships` retains the combined source
classification, category ID, order and reason; ordered child rows
in `source_classification_matches` retain each component filter
slug and category ID. Foreign keys and the shared filter-vocabulary
slug resolver reject missing, ambiguous or drifted source identities.
These overlays do not rewrite source characteristics or categories.

`unit_filter_metadata` binds source digest, format/version,
Army export generation, row counts and full content fingerprint.
The published-content checksum covers all four tables; optional paired
raw exports retain matching generation and compatibility metadata.
Repository classification filtering and `/api/unit-filters`
presentation use the selected SQLite projection. Numeric/slug
compatibility, hidden choices, combined membership and contextual
numeric filtering retain their existing results. Corrupt v29 data
fails closed; earlier schemas and source-only presentation tools
retain the validated maintained-JSON adapter.

### Army overview and historical identities in Army v30

Introduced in Army v30/compatibility 39. The current runtime embeds summaries from
`data/curated/identities/army-overview.json` and reviewed historical identities from
`data/curated/identities/legacy-armies.json`. The JSON files remain editable
build inputs; the summaries are InfinityDB editorial copy rather than official
rules or newly inferred Army identities.

`army_overview_text` is keyed by public Army slug and text role (`summary`),
retaining authored order and exact text. Each row references either the
existing current `application_armies` identity or an explicit historical
identity through foreign keys. Current slugs resolve through the central
application registry; all non-grouping current Armies and the authored legacy
identities must be covered exactly once.

`legacy_army_identities` is keyed by source context and explicit historical ID,
with unique API ID/slug, original position, name, role, group ID/name/slug,
logo locator and review reason. The context references
`army_reference_metadata`, which names the authored legacy format/version
and exact source digest. This identifies the curated evidence, not an
unverified historical Army archive or edition. Parent information must match
an existing current identity in all three fields; no parent is inferred from
ID ranges or names. Historical IDs/slugs cannot collide with current Armies,
and the historical records do not enter the playable application catalog.
No aliases or current-identity replacement links are invented.

`army_reference_metadata` also binds overview format/version/digest, Army
export generation, both row counts and a full ordered content fingerprint.
The published checksum covers all three tables; optional raw-pair
exports retain matching generation metadata. `/api/armies` and legacy-aware
search consume the database projection without reading either authored JSON
file. Existing summary text, grouping, non-playability and search links remain
unchanged. Corrupt or mismatched data fails closed; earlier schemas and
source-review tools retain the validated JSON adapters.

### Published symbol mappings in Army v31

`published_symbol_paths` stores exact mapping keys, unique by mapping kind
and identity: faction/source IDs, Unit slugs, source profile-logo URLs and
semantic profile identities. These retain the lookup namespaces; they are
not inferred canonical Army/Unit identities. Their foreign keys reference
`published_symbol_assets`, which retains paths and hashes for every
published SVG, including assets not selected by those maps.

`symbol_path_metadata` binds publication format/version, exact manifest
digest, Army archive SHA, paired export generation, row counts and the full
mapping/asset fingerprint. Build-time checks require the publication's named
Army archive to match the selected database and verify every published SVG's
actual bytes. Paths must be canonical relative SVG paths in the supported
asset namespaces; traversal, Windows separators and unpublished targets fail
closed. The published checksum includes all three tables; the optional raw
export retains matching compatibility/checksum metadata when explicitly requested.

`SymbolCatalog` consumes this projection from the embedded tables; earlier schemas and explicit
source tools retain the manifest adapter. Unit/Army/profile symbol selection,
semantic-profile precedence, contextual ambiguity and existing API fields are
unchanged. Other manifest fields remain build/graphical-publication evidence.
The manifest is no longer read when importing or starting a current application.

Browser HTML, version responses, module imports and cache headers share one
per-application static revision derived from the selected mapping fingerprint
and actual packaged static/SVG bytes. Published SVG hashes are verified against
that immutable package inventory, cached once per process. Different selected
mapping projections receive different versions without changing an existing
application's responses. The optional legacy static JSON route uses a short
cache lifetime and does not participate in the asset fingerprint. Release
candidate checks compute the same revision from the candidate's selected Army
database rather than a process-global default publication.

### General-profile projection in Army v33

Army v33/compatibility 42 retains the v32 relational layout, but publishes
all General profiles, including presentation-hidden identities, with
pre-classification shared-item buckets and availability. The
`general_profile_payloads` table stores deduplicated canonical JSON arrays;
`general_profile_selections` maps each logical Unit ID and availability mask
to exactly one payload via foreign keys. Mask bits 0–3 represent Mercenaries,
Spec-Ops, Team Operations and Reinforcements respectively. Each Unit has
all 16 combinations, including empty results. Both tables participate in
the published content checksum; validation checks coverage and references.

The shared Unit composer uses embedded Army identities, classifications,
catalogs and symbol mappings plus a temporary core Rules model constructed
from the same pinned curated inputs as the final Rules database. Materialize
before building Army-bound Rules publications, so their exact Army file
fingerprints remain valid without circular byte-hash dependencies.
The final paired Rules model is the reference for full-snapshot parity.
The projection does not incorporate ITS-only rules or requested-Army context.

Extended Explorer classifies shared items and projects visible rows with
availability. Unit details reuse the same stored General rows to derive
specific-item differences before source-bucket classification, without
exposing the Explorer-only availability field. A requested Army that adds
otherwise excluded occurrences uses the canonical composer instead.
v32 remains readable for Extended Explorer only; earlier schemas and
fixtures without matching embedded Rules retain runtime composition.
Source occurrences remain authoritative.

### Scoped filter context projection in Army v34

Army v34/compatibility 43 adds `unit_filter_contexts`, a single
checksum-covered JSON document with interned property sets, exact
source-occurrence contexts (including numeric AVA, points and SWC), and
ordered context references for each of the profile, loadout and logical
Unit matching scopes. The build calls the canonical context composer;
identical property sets and identical contexts share storage without
merging different source occurrence identities. The reader restores immutable
property sets and the existing MatchContext instances. Older schemas retain
the canonical runtime composer.

The projection does not precompute user selections, eligibility, prospective
counts or matching results. Availability, Army selection, search, numeric
filters, AND/OR combinations and pagination retain their dynamic behavior.

History-enabled builds append `unit_history_payloads` to these projections;
see [Army history model](data-model-history.md#published-unit-history).
