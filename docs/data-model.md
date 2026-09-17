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
  configuration. Generic duplicate/name rules remain implementation behavior
  rather than authored alias data.
- The ordinary whole-army `xx01` derivation remains current normalization
  behavior. The current identity configuration also contains a legacy
  canonical-faction override from source ID `1` to army/group ID `901`.
  Investigation of the source data now shows that this override conflates two
  different source concepts: ID `1` behaves as a mercenary source/origin
  identity, while `901` is the Non-Aligned Armies grouping identity. The mapping
  therefore remains current implementation behavior until migrated, but is not
  an accepted domain invariant.
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
membership faction. The current `1` -> `901` identity-config mapping therefore
should be understood as legacy InfinityDB interpretation policy, not evidence
that ID `1` means Non-Aligned Armies.

Normal unit availability and optional mercenary availability are also distinct
source concepts. Ordinary unit records declare normal faction availability in
`factions`. The source additionally contains dedicated mercenary variants that
consistently use `canonical: 1`, an empty `factions` list, a `merc-...` slug, and
army-specific occurrences that supply optional mercenary availability. Many of
those records also use a 10,000-offset-style source ID, but that numeric pattern
is supporting evidence only and is not a semantic contract.

Current repository queries reconstruct this distinction after database creation.
They union declared `unit_factions` as the unit's normal army set, then mark an
army occurrence as `mercs` when its source record has canonical faction `1` and
the army is outside that normal set. Logical-unit grouping also combines common
10,000-ID duplicate families and selected explicit aliases at query time. This
produces the intended UI behavior today but leaves source-semantic
classification and some deduplication later in the pipeline than necessary.

Canonical ownership, source identity, army grouping, army-list kind, optional
availability category, and playability are separate semantics. The current
normalized/database/API model does **not** yet expose a complete explicit
role/playability model, nor does normalized data explicitly classify a source
unit occurrence as normal versus optional mercenary availability. Clients must
not infer these semantics from numeric ID patterns.

### Design direction

Treat source ID `1` and grouping identity `901` as distinct concepts. Preserve
ID `1` as source-side mercenary identity/provenance and derive Non-Aligned Army
grouping from the actual 901 metadata hierarchy. Remove the legacy `1` -> `901`
override only as part of a coherent normalization/database/API migration so
existing behavior is not silently broken midway through the refactor.

Classify mercenary variants during normalization using source semantics rather
than repository-time inference. The observed contract to validate is
`canonical == 1`, empty declared `factions`, and a `merc-...` source slug.
Validation should report any future source record that violates or extends that
pattern. A 10,000-offset ID may help diagnose matching records but must not be
the rule that determines mercenary semantics.

Use that classification to improve logical-unit deduplication before runtime.
When a mercenary alternate record can be matched unambiguously to its ordinary
logical unit, normalization or database creation should combine their logical
identity while preserving every source unit ID, army occurrence, and
availability provenance needed for validation and the raw archive. The frontend
repository should consume the resulting explicit logical identity and
availability category instead of rediscovering them from canonical ID `1`,
`factions`, and numeric duplicate patterns on every read.

The exact normalized schema for this provenance is not fixed yet. The important
boundary is that deduplication may collapse several source records into one
logical application unit without discarding the source records or the reason an
army occurrence exists. Normal availability derived from declared `factions`
and optional mercenary availability derived from mercenary source variants must
remain distinguishable even when they occur for the same logical unit and army.

Model army role/playability explicitly as a related but separate concern. Prefer
metadata parent relationships for main-army/sectorial/Non-Aligned grouping and
the explicit `reinforcements` links for reinforcement relationships. Expose the
result from the backend so selectable armies are determined from modeled source
semantics and reviewed project policy rather than hard-coded IDs or list
presence.

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

`PRAGMA application_id` identifies an InfinityDB file and `PRAGMA user_version`
records its schema version. The current schema version is 8 and the application
compatibility revision is 10. Imports build temporary sibling files, check
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
