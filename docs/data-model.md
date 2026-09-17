# Data model notes

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
- Profile group, profile and loadout option IDs are local to their army/unit hierarchy and use composite keys in normalized data.
- Skills, weapons, equipment, ammunition, characteristics, troop types, categories and extras use stable global lookup IDs.
- Skill, equipment, and weapon occurrences retain their owning profile,
  loadout, or unit option, display order, quantity, and linked extras. This
  supports both unit details and reverse lookup from the rules-reference
  catalogs.
- Explicit source-equivalent unit, army, skill, equipment, and weapon IDs are
  maintained in the validated `config/identity/source-identities.json`
  manifest. Generic duplicate/name rules remain implementation behavior rather
  than authored alias data.
- The ordinary whole-army `xx01` derivation remains normalization behavior.
  Exceptional canonical-faction interpretation, including the legacy
  canonical-faction source ID `1` -> `901` mapping, is maintained in the
  identity manifest and supplied explicitly to the normalizer.
- InfinityDB normalization pins the exact validated identity manifest and its
  canonical SHA-256 into `normalized.json`. Database export revalidates that
  provenance and propagates the same policy into both database siblings.
  Repository queries consume the database-pinned policy rather than reading the
  working tree's `config/` directory at runtime.
- Peripheral IDs are army-local.
- Referenced but undefined factions/units/categories are retained as explicit placeholder records rather than discarded.

## Army identities, grouping, and playability

An `army_lists` record represents an Army source/list identity. Its presence does
not by itself imply that the identity is independently playable.

Faction 901, Non-Aligned Armies, is a grouping identity for the associated 9xx
armies rather than a playable army of its own. Its child armies remain distinct
playable army identities.

The source canonical-faction ID `1` is a legacy mercenary designation and maps
to grouping identity `901` for canonical ownership through the validated
identity manifest. That identity mapping is separate from playability: resolving
canonical faction `1` to `901` must not make 901 a selectable army.

Canonical ownership, source-identity mapping, grouping, list kind, and
playability are separate semantics. The current normalizer still uses the
ordinary `xx01` derivation for canonical ownership where no exceptional mapping
applies; grouping and presentation also use imported metadata faction
relationships. Playability must be modeled separately rather than inferred from
list presence or numeric ID patterns such as `9xx`.

Army-list occurrences remain authoritative for unit membership and availability,
while the set of user-selectable armies is determined separately from the
modeled army/faction semantics.

## Principle

The merged master layer is lossless and source-oriented. The normalized layer is query-oriented. Database-specific choices should live in exporters/adapters rather than in source parsing.

## SQLite storage

`infinity_db.database` imports every normalized table with its original field names,
declared primary keys, and foreign keys. Nested arrays and objects use JSON text.
The frontend `infinity.db` contains only queryable columns. Its sibling
`infinity.raw.db` contains `__infinity_raw_rows`, preserving each exact normalized
record (including absent versus null fields) for development use. Both databases
retain `__infinity_metadata`; the schema defines empty frontend tables so API
queries do not depend on a particular snapshot containing every kind of record.
The metadata also stores the validated source-identity manifest and its
canonical hash copied from normalized provenance, making the identity policy
part of the immutable database snapshot and allowing tampering, incomplete
provenance, or conflicting explicit export policy to fail validation.

`PRAGMA application_id` identifies an InfinityDB file and `PRAGMA user_version`
records its schema version. The current schema version is 8 and the application
compatibility revision is 10. Imports build temporary sibling files, check
database integrity, then replace the destinations. Incompatible schemas or
compatibility revisions require a rebuild from normalized JSON for now.
The frontend export runs `ANALYZE` after loading and indexing data, preserving
SQLite planner statistics in the immutable snapshot.

## PDF-derived rules storage

Curated facts from user-supplied rules PDFs and wiki research first pass through
the source-controlled JSON contract in `data/curated/`. The loader validates
that every record has a stable identity, concise summary, and source reference
with a printed page. Raw PDFs and wiki snapshots are never accepted as
application inputs.

The available source families are N5 core rules v5.1-v5.3, N5 FAQs v0.0-v0.1,
ITS Seasons 6-18, and the 20260915 wiki snapshot. Core rules yield reusable
rule identities and structured effects; FAQs yield dated rulings; ITS material
is isolated by season; wiki material supplies discovery, aliases, and
cross-links. Historical documents remain selectable references and must not be
silently merged into current rules.

The current curated v2 document has a collection identity, source records,
typed fact records, scope, Army links, related-record links, review state, and
citations. PDF citations require printed page numbers. Wiki citations require
the local page path and snapshot date instead. Version 1 files are no longer
accepted and must be migrated before ingestion.

`infinity-db build-rules data/curated --output data/generated/rules.db` stores
those curated facts in a separate SQLite database, rather than in either Army
JSON-derived database. Directory ingestion skips `example.json`. The rules
database has an independent schema, application ID, compatibility version, and
replaceable snapshot lifecycle.
Every fact must retain document identity, edition/version or date, and a
printed-page citation. It may reference stable application-level rule
identities, but neither database is an import source for the other; any combined
view is assembled by application code.

The unit browser queries `units`, `army_units`, and `army_lists`. It excludes
source-undefined placeholder units and uses actual army occurrences for filtering,
preserving the distinction between list membership and canonical identity.

The rules-reference browsers query the global `skills`, `equipment`, and
`weapons` catalogs together with their `profile_*`, `option_*`, and
`unit_option_*` occurrence tables. Equivalent source labels can be merged for
display, but the underlying source IDs and individual occurrences remain
available for validation and detail rendering.

The first rules schema stores collections, sources, vocabulary definitions,
records, citations, Army links, and related-record links. Curated records may
also link to `ammunition`, `extras`, `characteristics`,
`troop_types`, `units`, and profile occurrences. These are annotations and
explanations only; Army JSON remains authoritative for unit membership,
availability, legality, and source-derived statistics.

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