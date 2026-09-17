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

- `unit.id` is treated as the global unit identity.
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
  configuration. Generic duplicate/name matching remains implementation
  behavior rather than authored alias data; normalization now persists the
  resulting generic unit matches for current snapshots.
- Current InfinityDB builds derive a unit's application `main_army_id` from
  the imported Army metadata parent for its canonical faction. Maintained
  canonical-faction overrides take precedence when explicitly configured. The
  old whole-army `xx01` calculation remains only as a standalone/legacy
  normalization fallback when no usable metadata row exists for that canonical
  faction. Source canonical-faction ID `1` remains mercenary source/origin
  provenance with `main_army_id = null`, while `901` remains the distinct
  Non-Aligned Armies grouping identity.
- InfinityDB normalization pins the exact validated identity configuration and
  its canonical SHA-256 into `normalized.json`. Database export revalidates that
  provenance and propagates the same policy into both database siblings.
  Repository queries consume the database-pinned policy rather than reading the
  working tree's `config/` directory at runtime.
- Peripheral IDs are army-local.
- Referenced but undefined factions/units/categories are retained as explicit
  placeholder records rather than discarded.

## Army identities, grouping, playability, and mercenary availability

### Current

An `army_lists` record represents an Army source/list identity. Its presence does
not by itself prove that the identity is independently playable.

Faction 901, Non-Aligned Armies, is a known grouping identity for the associated
9xx armies rather than a playable army of its own. Its child armies remain
distinct force/list identities.

The merger's current `army_lists.kind` value is derived rather than supplied as
a source taxonomy: a source document with a top-level `reinforcements` field is
labeled `army`, while a source document without that field is labeled
`reinforcement`. It therefore distinguishes the current ordinary-list versus
reinforcement-file shape, but does not distinguish main armies, sectorials, or
Non-Aligned forces.

Army metadata provides a separate faction hierarchy. Standard main armies are
self-parented metadata factions, while their sectorials point to that main-army
parent. Non-Aligned army lists such as the 9xx forces point to metadata grouping
identity 901. Reinforcement lists are also explicitly referenced from their
ordinary army/sectorial source documents through the top-level
`reinforcements` relationship. These relationships are source evidence and are
stronger than numeric-ID conventions.

Source canonical-faction ID `1` is materially different from 901. In the
investigated source snapshot, ID `1` has no army list, is used as the canonical
identity for mercenary-related unit records, and is not used as a normal unit
membership faction. InfinityDB no longer maps source ID `1` to `901`: normalization preserves
canonical source identity `1` while explicitly leaving its application
`main_army_id` unset.

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

Normalization now also persists `genericUnitMatches` for standard,
non-reinforcement source records whose 10,000-family ID and ISC/display-name
identity provide an unambiguous duplicate match. Presence of that metadata is
authoritative even when the list is empty: repository grouping consumes the
persisted matches and does not rediscover additional generic groups through ID
arithmetic. Databases built before `genericUnitMatches` was persisted remain
readable through the legacy arithmetic fallback.

Mercenary identity remains a separate source-semantic contract. Repository
logical-unit grouping consumes persisted `mercenaryUnitMatches` /
`unmatchedMercenaryUnitIds`; matched mercenary records join through their
recorded standard source unit, while explicitly unmatched variants remain
separate. Configured alias groups still come from the pinned identity policy. During
database creation, reinforcement-only source rows are audited against those
standard logical groups using the same pinned word-alias policy. Unambiguous
results are persisted as `reinforcementUnitMatches`; current repositories treat
that metadata as authoritative, while databases without it retain the legacy
query-time label matcher. An explicitly empty persisted result disables runtime
reinforcement rediscovery.

Mercenary availability has now completed the same read-path migration for
current normalized snapshots. Repository source occurrences carry
`army_units.availability_kind`, and `mercenary` occurrences require the `mercs`
filter while `standard` occurrences do not. Canonical faction `1` and declared
faction membership are no longer the authority for mercenary filtering when
explicit availability provenance is present. A legacy fallback retains the
previous canonical/faction inference only for database rows where
`availability_kind` is absent.

Canonical ownership, source identity, army grouping, army-list kind, optional
availability category, and playability are separate semantics. The current
normalized/database model exposes mercenary source role, availability category,
and the audited mercenary-to-standard source relationship explicitly. The
repository additionally derives army role/playability from imported metadata
parent relationships and explicit reinforcement links, and `/api/armies`
exposes that source-derived contract. It still does **not** expose one complete
pre-runtime logical-unit identity that physically consolidates every configured
alias and source variant. The generic, mercenary, and reinforcement match
decisions are now persisted before repository queries, but source rows remain
separate for provenance. Clients must not infer logical identity from numeric ID
patterns.

### Design direction

Source ID `1` and grouping identity `901` are now kept distinct in current
normalization. ID `1` remains source-side mercenary identity/provenance with no
application `main_army_id`, while Non-Aligned Army grouping is derived from the
actual 901 metadata hierarchy.

Continue moving logical-unit identity earlier in the pipeline. The current
normalizer persists generic duplicate and mercenary-to-standard matches, while
database creation persists unambiguous reinforcement-to-standard matches using
the pinned identity policy. The repository honors all three decisions directly.
Configured aliases and these persisted match sets are still not represented by
one materialized logical-unit identity.

The accepted next step is to materialize that identity during frontend SQLite
creation, while leaving normalized/source records unchanged for provenance. The
planned frontend relation is conceptually:

```text
logical_units
  id                     application logical-unit ID
  representative_unit_id source unit used for canonical display/general data

logical_unit_sources
  source_unit_id          original source-defined unit ID; one row per source unit
  logical_unit_id         owning application logical unit
```

Initially `logical_units.id` should equal `representative_unit_id`, preserving
existing unit URLs and API identifiers. Keeping both fields explicit allows a
future application-owned logical ID without rewriting the source model.

Database creation should resolve the relation from four inputs: configured unit
aliases in the pinned identity policy, normalized `genericUnitMatches`, normalized
`mercenaryUnitMatches` / `unmatchedMercenaryUnitIds`, and database-build
`reinforcementUnitMatches`. These are evidence and provenance; the materialized
relation is their resolved application identity. The resolver should combine
transitive relationships as graph components rather than depend on matching
order. It must choose a deterministic representative, reject references to
missing source rows or contradictory mappings, and place explicitly unmatched
mercenary/reinforcement variants in independent logical units.

The central invariants are:

- every source-defined unit belongs to exactly one persisted logical unit;
- every logical unit has exactly one deterministic representative source unit;
- source rows are never physically merged or rewritten by logical identity;
- profiles, loadouts, unit options, army occurrences, and availability provenance
  continue to reference their original source unit IDs;
- `army_units.availability_kind` remains source-occurrence provenance even when
  standard and mercenary occurrences resolve to the same logical unit and army;
- current repository reads consume the materialized relation and do not repeat
  generic, mercenary, reinforcement, or alias identity resolution.

Legacy matching remains a build-compatibility concern rather than a repository
concern. When older normalized inputs lack persisted generic, mercenary, or
reinforcement evidence, database creation may run the existing legacy fallback
to obtain the mapping before writing `logical_units` and `logical_unit_sources`.
Every newly built frontend database then exposes the same materialized contract
regardless of which compatibility path produced it. Once old input support is no
longer required, those fallbacks can be removed without changing repository
queries.

Normal availability derived from declared `factions` and optional mercenary
availability derived from mercenary source variants remain distinguishable even
when they occur for the same logical unit and army. The repository now consumes
that explicit normalized availability category. The remaining migration work is
to remove the legacy canonical/faction fallback once databases without explicit
availability provenance no longer need to be supported.

Army role/playability is now explicit at the repository/API boundary. Metadata
parent relationships provide main-army, sectorial, and Non-Aligned grouping;
explicit `reinforcements` links provide reinforcement parentage. Grouping
identity `901` is surfaced as non-playable when its imported child lists are
present, and the browser selector consumes `role`/`playable` instead of Army-ID
ranges. The remaining identity work concerns complete logical-unit consolidation
rather than army playability or query-time generic/reinforcement matching.

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

`units.source_role` and `army_units.availability_kind` are explicit frontend
schema fields rather than incidental dynamic columns. This makes the
normalization-time availability classification part of the generated database
contract; repository mercenary filtering consumes `availability_kind` directly
for current snapshots.

The planned logical-unit materialization adds frontend-only `logical_units` and
`logical_unit_sources` tables during database export. These tables are derived
application structure, not normalized source facts, and therefore do not replace
`units` or duplicate profile/loadout/occurrence tables. Repository unit queries
will map a requested source or representative ID through `logical_unit_sources`,
then aggregate the associated original source rows. This keeps source provenance
lossless while making the logical identity itself an explicit database contract.

`PRAGMA application_id` identifies an InfinityDB file and `PRAGMA user_version`
records its schema version. The current schema version is 9 and the application
compatibility revision is 13. Imports build temporary sibling files, check
database integrity, then replace the destinations. Incompatible schemas or
compatibility revisions require a rebuild from normalized JSON for now. The
frontend export runs `ANALYZE` after loading and indexing data, preserving SQLite
planner statistics in the immutable snapshot.

## Snapshot provenance and human annotations

### Current

Timestamped `JSON`, `WIKI`, and `SYMBOLS` ZIP files are immutable acquisition
artifacts. Current downloaders create those archives and do not create separate
InfinityDB snapshot-provenance manifests or curated snapshot-note files.

Corvus Belli's Army `metadata.json` is source data. It is distinct from any
future InfinityDB-owned acquisition provenance.

### Design direction

Downloader-known provenance will live in generated records under
`data/manifests/snapshots/`, outside the immutable ZIP and separate from Corvus
Belli's source `metadata.json`. A snapshot manifest will identify its archive by
SHA-256 and may retain archive path/name, snapshot type, acquisition timestamp,
language, source/base URL, document counts, and other reproducibility facts.

Human-authored descriptions, comparison targets, and notable-change notes will
live separately under `data/curated/snapshot-notes/` and reference the
corresponding immutable snapshot by SHA-256. Editing those notes must not alter
the raw archive or generated provenance. Snapshot notes are not rules-database
inputs and do not become runtime application data unless a future feature
explicitly defines such an ingestion path.

No current code writes or consumes either of these planned snapshot-metadata
paths. Their generated-file persistence/ignore/package policy is therefore not
yet part of the implemented data model.

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

The current curated-v2 document has collection identity, source records, typed
fact records, maintained vocabularies, scope, Army links, related-record links,
review state, and citations. Record citations are source-specific: PDF citations
require positive printed page numbers; wiki record citations require a
snapshot-local path and `snapshotDate`.

`vocabularySources` is a current legacy exception to that cleaner model. The
loader requires every vocabulary-source entry to contain `sourceId`, `path`,
`snapshotDate`, `heading`, and a positive `page`, and the checked-in v5.3
collection therefore carries wiki path/date information together with page
numbers. That shape is current behavior, not a statement that wiki citations
should generally use printed pages.

The checked-in wiki source record also retains the earlier unpacked local mirror
identity (`data/wiki/20260915/`). It predates the timestamped-ZIP downloader
lifecycle and should be preserved as recorded provenance until a real migration
can establish the exact replacement source identity.

`infinity-db build-rules` defaults to `data/curated/rules/` and stores those
curated facts in a separate SQLite database rather than either Army-derived
database. Directory ingestion skips `example.json`. Other curated subtrees are
not rules-database inputs. The rules database has an independent schema,
application ID, compatibility version, and replaceable snapshot lifecycle.

A curated rule fact may reference stable application-level identities, but
neither database is an import source for the other; any combined view is
assembled by application code.

### Design direction

When the wiki downloader/packager and curated provenance contract are rewritten,
migrate wiki sources from legacy unpacked/date-only identity to an exact
recorded timestamped archive identity/hash and replace the mixed
`vocabularySources` locator shape with source-appropriate provenance. Do not
invent an archive/hash association before that migration has authoritative
input to bind.

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

The first rules schema stores collections, sources, vocabulary definitions,
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
