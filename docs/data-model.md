# Data model

**Project domain:** Data processing

This document owns InfinityDB's **current semantic and persistence model**. It describes what the
source means to InfinityDB, which abstractions the project introduces, how those facts are stored,
and which invariants runtime queries rely on. Historical audit counts, release benchmarks, and
migration chronology belong in Git history or `docs/CHANGELOG.md`, not in this current-state
contract.

Unless explicitly marked otherwise, statements below describe the current repository model.

## Pipeline and persistent artifacts

Army-derived data flows through three conceptual layers:

```text
immutable Army snapshot
        ↓
lossless merged/master representation
        ↓
validated normalized source model
        ↓
SQLite export
        ├─ infinity.db      canonical application/runtime data
        └─ infinity.raw.db  lossless normalized source/audit archive
```

Curated rules data follows a separate path:

```text
reviewed data/curated/rules/*.json
        ↓
validation/composition
        ↓
rules.db
```

The two runtime databases are intentionally separate because Army data and reviewed rules knowledge
have different sources, provenance, and update cadence.

Current runtime database versions:

- Army application database schema: **25**;
- Army application compatibility revision: **34**;
- rules database schema: **7**;
- rules database compatibility revision: **8**.

`data/README.md` owns source/snapshot format versions, while `data/curated/README.md` owns the
curated-rules format version. Schema and compatibility validation is fail-closed. Incompatible
generated databases are rebuilt; there is no in-place migration contract for current generated
Army/rules databases.

## Semantic provenance

A field or relationship must be understood by provenance class before it is deduplicated or
presented.

### Source-native facts

These are represented directly by Army or another cited source: source IDs, names, profile values,
loadout costs, Army-list membership, source extras, notes, Fireteam rows, and similar material.
InfinityDB may normalize their representation but must preserve their source coordinates and meaning.

### Source-derived facts

These are deterministic interpretations of explicit source relationships, such as Army grouping or
role derived from metadata parents and reinforcement links. The derivation is application logic, but
the evidence remains source-owned.

### Curated/reviewed facts

These are human-reviewed project data derived from official sources where the application needs a
stable relationship the upstream data does not directly supply. Examples include identity aliases,
legacy Army presentation records, Peripheral mappings, historical relationship endpoint evidence,
maintained rules summaries, and typed rules relationships.

### InfinityDB abstractions

These are application concepts introduced to make multiple source views coherent. They must not be
presented as if they were source-native. Important examples are:

- logical Units spanning equivalent source representations;
- the General profile abstraction;
- canonical profile/loadout payload identities;
- application-domain slugs; and
- cross-domain composed reference projections.

### Presentation-only structure

Browser grouping, card/disclosure structure, responsive layout, visual labels, and other display
conveniences are not game-data semantics unless backed by a data-model contract.

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

### General profile

The **General profile** is an InfinityDB abstraction for profile information that can safely be shown
once for a logical Unit rather than repeated for every Army occurrence. It is not an upstream Army
entity.

Only semantically compatible profile data may be consolidated. Materially different statlines,
profile identities, classifications, characteristics, or other contextual facts remain distinct.
Source profile IDs/names remain available as provenance even when multiple occurrences share one
application payload identity.

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
- A **loadout payload** owns loadout costs, weapons/equipment/skills/options and other loadout-local
  facts.
- Context tables connect those canonical payloads back to source Unit, Army, profile-group, and
  loadout occurrences.

Exact structural equality is useful evidence but does not by itself justify semantic identity when
source context says two records mean different things. Conversely, equivalent payloads may be shared
when the contextual relationships remain explicit.

### Application catalog identities and slugs

Skills, Equipment, Weapons, and other application domains may group multiple source IDs/labels into
one canonical browsing identity. Source membership remains materialized so filters and usage queries
match every member of the application identity.

Where a domain has a stable slug:

- generated application-facing links and maintained references prefer the slug;
- numeric IDs remain accepted for compatibility/provenance;
- the domain's central resolver owns both forms; and
- consumers must not derive slugs independently from labels.

Rules/reference semantic IDs (`skill:...`, `equipment:...`, etc.) remain distinct from public route
slugs even when they correspond one-to-one.

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

Profile/loadout-sensitive filters must be satisfied in one compatible occurrence context.

- AVA belongs to an Army/profile occurrence.
- Points and SWC belong to loadout occurrences.
- Troop Type, Classification, Characteristics, profile Skills/Equipment and other profile facts stay
  with their owning profile/profile group.
- Loadout-local Weapons/Equipment/Skills stay with the loadout.
- Unit-option facts remain Unit-wide when the source does not attach them to a profile group.

When AVA/Points/SWC participates in a query, another selected profile/loadout criterion cannot be
satisfied by an unrelated option elsewhere on the same logical Unit. This prevents semantically
impossible cross-option matches.

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

## Fireteams

Fireteam charts are Army-local structured source data. InfinityDB materializes one canonical
application chart per supported Army/source context while preserving:

- chart/type limits, including the raw Army value for provenance while projecting explicit
  `maximum`, `unavailable`, or `unlimited` application semantics before browser use;
- member requirements;
- Wildcards and equivalence context;
- source notes;
- resolved logical Unit targets;
- FTO-eligible loadout references; and
- source provenance.

Reinforcement parent limits remain separate through the application Army graph rather than being
silently merged into a child chart. General Fireteam rules/Level bonuses live in curated rules data
and are composed by the Fireteams application surface; they are not source Army chart rows.

## Relationship model

Application relationships should be materialized where their semantics are understood and useful.
Source storage links that exist only to express normalization shape are not automatically player
relationships.

Important current relationship families include:

- logical Unit ↔ source occurrence;
- Army grouping/parentage and Unit availability/membership;
- Profile/Loadout/Unit-option include relationships;
- selection/dependency constraints;
- Peripheral/Controller relationships;
- Fireteam membership/equivalence/Wildcard context; and
- typed rules/reference relations.

Historical source endpoints that no longer resolve in the current Army snapshot are handled by a
separate snapshot-bound review contract. That evidence can classify a source relation as stale; it
must not create a false alias to a current Unit.

## Rules/reference model

Curated rules collections are versioned and built into `rules.db`. The rules layer is
semantic/reference data, not mutable game state. `data/curated/README.md` owns the current curated
format and validation contract.

A semantic record has a stable typed ID such as `skill:move`, `state:targeted`, or
`ammunition:shock`. Current composition is contribution-based:

- exactly one current `definition` contribution owns the canonical identity;
- optional supplements can add scoped reviewed facts/citations/relations;
- historical/superseded collections remain source evidence but are excluded from normal current
  composition; and
- applicability/review/source provenance remains explicit.

### Domain ownership

The application-domain registry determines which semantic records receive player-facing routes.
Skills, Equipment, Weapons, Ammunition, Traits, States, Hacking Programs, Labels, and selected
General Rules are route-backed reference concepts. Attributes and scoped Game terms are embedded
vocabularies. Fireteam general rules remain owned by the Fireteams surface.

A semantic identity may exist without a dedicated detail route. Search/Glossary/presentation code
must preserve kind/domain and not merge same-name concepts from different namespaces.

Cross-domain discovery may additionally use reviewed `facts.relatedCategories` category slugs.
This adds navigation only: it does not change the record's canonical kind/domain, primary category,
or typed rules relationships.

### Declaration categories and exact source variants

Declaration/action categories are composition metadata rather than standalone public rule records.
Skills, action-like Equipment, and Hacking Programs reuse canonical declaration identities while
preserving source spelling in source storage.

Exact source variants may belong to a family through typed `variant-of` semantics while retaining
their own source-specific facts. Family grouping must not imply that every Level/named variant has
identical rules. When the authoritative rule is naturally level-based, a family definition may also
carry reviewed `facts.levels` entries so the browser can present the level differences as one
comparison surface instead of duplicating near-identical rule cards.

### Typed relations

Rules relations are authored once in the semantic direction and validated against current semantic
IDs. Reverse navigation is derived for presentation. The relation vocabulary includes, among others,
state entry/cancellation, effect reuse/override/negation, modifier interactions, use restrictions,
enabling, triggers, Equipment grants, and Peripheral eligibility.

The edge states the relationship; exact numeric or conditional details remain in the owning rule
facts. Backend composition owns direction-aware labels/grouping for player presentation so browser
JavaScript does not maintain a second ontology.

### Maintained text

Maintained prose supports typed semantic reference tokens and typed distance values. Completed review
batches cover the supported namespaces and reject new plain semantic candidates. Ambiguous text uses
an explicit `review-needed` marker; confirmed ordinary-language collisions are stored as exact
passage fingerprints so changed wording reopens review.

The maintained policy is documented in `data/curated/README.md`.

## SQLite storage contract

Army export first loads normalized source data into validated relational staging, then writes two
permanent siblings:

### `infinity.db`

The self-contained application/runtime database. It contains the source/context rows still needed by
application behavior plus materialized canonical tables, mappings, provenance, and indexes. Source-
only normalized tables are physically absent.

Normal repository/API/web serving opens only this Army database plus `rules.db`.

### `infinity.raw.db`

The development/audit sibling. It contains all normalized source tables as queryable relational
structures plus exact normalized row JSON so absent-vs-null and source-only data remain recoverable.
It is not deployed.

### Shared metadata and integrity

Both Army siblings retain the generated metadata needed to bind them to the source/configuration
that produced them. Important metadata includes source snapshot identity, validated identity-policy
hashes, publication/raw table boundaries, and deterministic content identity.

When the Army database is built from a ZIP snapshot, `snapshotArchiveSha256` records that exact
archive identity. Deployment compares it with the Army source identity in the tracked symbol
publication manifest so Army data and graphical publication cannot silently come from different
snapshots.

`PRAGMA application_id`, `PRAGMA user_version`, and the InfinityDB compatibility revision are
validated before normal reads. Export validates integrity, writes planner statistics, and performs
canonical physical finalization for deterministic release bytes. Semantic tests may explicitly skip
only the physical finalization step; they do not bypass schema/input/integrity validation.

Builds publish generated database destinations only after temporary artifacts validate. The exact
publication/recovery lifecycle is owned by `data/README.md`.

## Snapshot provenance

Army, wiki, and symbol acquisition uses generated snapshot provenance records described in
`data/README.md`.

The current provenance model distinguishes:

- logical snapshot content SHA-256 (normalized member paths + member bytes);
- exact archive SHA-256;
- acquisition timestamp;
- source URL/language/document count where applicable; and
- for Army snapshots, the latest source-data date encoded by supported Army source version strings.

`data/README.md` owns the current provenance-format version and compatibility rules.

Acquisition time answers when InfinityDB downloaded the snapshot. `source.dataChangedOn` answers when
the contained Army source data most recently reports changing. Those dates must not be substituted
for each other.

Human snapshot notes are separate curated annotations bound to immutable source identity. Acquisition
tools never rewrite them.

## Army source revision interpretation

Corvus Belli Army document `version` values are source revisions, not InfinityDB snapshot versions.
InfinityDB may derive a latest encoded source date only from version shapes it explicitly recognizes;
unsupported values must remain visible rather than guessed. A snapshot can be acquired long after
its newest source revision, so the provenance model stores both concepts.

The browser's normal freshness wording uses the source-data change date when available. Exact
acquisition/archive identity remains Developer/provenance information.

## Required Army metadata

Army database builds require the supplementary Army `metadata.json`. It is preserved through the
merge/normalized pipeline and exported to metadata tables.

Metadata provides, among other things, faction/grouping relationships and weapon/profile reference
information. Army list files remain authoritative for concrete Unit membership/availability; a
metadata identity does not create an Army roster by itself.

Current build validation rejects normalized Army data without valid required metadata.

## Application query model

Runtime repositories query canonical/materialized application structures and compose contextual
source detail as needed. They must not infer semantics from raw IDs or reach into `infinity.raw.db`.

Examples:

- Unit lists operate on logical Unit identity and materialized Army availability.
- Unit detail returns one logical Unit with source/Army/profile/loadout context preserved.
- catalog filters resolve canonical application identity and match all materialized source members.
- rules-backed States and other rules-only concepts are read from `rules.db`; their presence does
  not imply mutable in-game state in `infinity.db`.
- search and Glossary project canonical domain identities rather than creating another identity
  namespace.

The HTTP/browser layer may change presentation without changing these semantic ownership rules.

## Audit and validation tools

Current semantic contracts are executable through focused audit tools rather than copied as
historical inventories into this document. Important examples include:

- `tools/audit_database_separation.py` — application/raw table boundary;
- `tools/audit_runtime_database_surface.py` — runtime repository access boundary;
- `tools/audit_unit_semantics.py` — logical Unit/source semantics;
- `tools/audit_profile_semantics.py` and `tools/audit_loadout_semantics.py` — profile/loadout payload
  boundaries;
- `tools/audit_army_faction_semantics.py` — Army/grouping/faction semantics;
- `tools/audit_peripheral_semantics.py` — Peripheral mappings/access pools;
- `tools/audit_relationship_semantics.py` — source/application relationship interpretation;
- `tools/audit_fireteam_semantics.py` — Fireteam chart semantics;
- `tools/audit_source_presentation.py` — source-to-player-presentation coverage;
- `tools/audit_semantic_deduplication.py` — canonicalization evidence;
- `tools/audit_enrichment_coverage.py` and `tools/audit_rules_interactions.py` — rules/reference
  coverage and interaction review; and
- `tools/audit_maintained_text_links.py` — maintained-prose semantic-link completeness.

Generated reports and one-off audit measurements belong under ignored report/audit workspaces. Only
durable semantic conclusions belong in this document.
