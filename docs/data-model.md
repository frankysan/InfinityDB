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

- `unit.id` is the stable source-unit identity. It is not necessarily the
  application logical-unit identity: multiple source unit IDs can resolve to one
  materialized logical unit while source rows retain their original IDs.
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
  configuration. That policy also owns reinforcement-label prefixes used by
  unit/profile identity normalization and backend profile display names. Generic
  duplicate/name matching remains implementation
  behavior rather than authored alias data; normalization now persists the
  resulting generic unit matches for current snapshots.
- Weapon-family classification policy is maintained in validated
  `config/catalogs/weapon-categories.json`, while known Army weapon metadata
  corrections are maintained separately in `config/catalogs/weapon-overrides.json`.
  Those corrections include source name/profile fixes and exact metadata weapon
  rows that should not become display profiles. Normalization applies the authored
  build inputs before normalized catalog/metadata rows are materialized, while the
  original Army metadata envelope remains unchanged for provenance. The frontend
  database does not need the config files at runtime.
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
- Normalization warnings remain source-preservation diagnostics, not automatic
  corrections. InfinityDB tracks a reviewed warning-count baseline in
  `config/validation/source-anomalies.json` for the exact 2026-09-18 Army
  snapshot. For downloader-dated snapshots at or after that baseline,
  `infinity-db build` and `normalize` allow known warning counts to decrease but
  reject new categories or counts above the reviewed ceiling before database
  export. The standalone `infinity-army` pipeline does not impose this
  project-specific baseline.

## Army identities, grouping, playability, and mercenary availability

### Current

An `army_lists` record represents an Army source/list identity. Its presence does
not by itself prove that the identity is independently playable.

Current source identity `901`, Non-Aligned Armies, is both an imported Army list
and the metadata parent of its associated child armies, but it is not selectable
as an independent army in InfinityDB. In the investigated source shape, metadata
records `901.parent = 900`, while child lists such as `902`, `904`, `905`, `908`,
and `909` point to parent `901`. Runtime classification therefore treats source-list
existence, hierarchy role, roster semantics, and application playability as
separate dimensions rather than assuming that a grouping identity is metadata-only.

The merger's current `army_lists.kind` value is derived rather than supplied as
a source taxonomy: a source document with a top-level `reinforcements` field is
labeled `army`, while a source document without that field is labeled
`reinforcement`. It therefore distinguishes the current ordinary-list versus
reinforcement-file shape, but does not distinguish main armies, sectorials, or
Non-Aligned forces.

Army metadata provides a separate faction hierarchy. Standard main armies are
self-parented metadata factions that also exist as imported ordinary army lists,
while their sectorials point to that playable main-army parent. A referenced
parent that is itself an imported ordinary list but is **not** self-parented is
a grouping node; a referenced metadata parent that has no imported army list may
also be surfaced as a grouping node. Children of either grouping shape receive
the `non_aligned` role. Reinforcement lists are excluded from this derivation and
are instead identified through the explicit top-level `reinforcements`
relationship on their ordinary army/sectorial source document. These
relationships are source evidence and are stronger than numeric-ID conventions.

The analyzed 2026-09-10 snapshot shows why source roster semantics must remain
separate from application playability. Source list `901` contains one standard
unit (Rumbler Spec-Ops) plus the complete 49-variant optional-mercenary pool,
while each child list contains its own standard roster plus a subset of that
mercenary catalogue:

| Army | Standard source units | Mercenary variants | Standard units represented in 901 logical pool |
| --- | ---: | ---: | ---: |
| 901 Non-Aligned Armies | 1 | 49 | 1 |
| 902 Druze | 37 | 42 | 21 |
| 904 Ikari | 38 | 45 | 16 |
| 905 StarCo | 35 | 42 | 15 |
| 908 Dahshat | 41 | 43 | 16 |
| 909 White Company | 46 | 38 | 19 |

Only Rumbler Spec-Ops is directly present as the same standard source ID in all
six lists. The larger logical overlap comes from standard child units whose
optional-mercenary variant is present in `901`. InfinityDB therefore preserves
the `901` source roster and its occurrence provenance even though `901` is
non-playable in the army selector/API filter contract.

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

Normalization also persists `genericUnitMatches` for standard,
non-reinforcement source records whose 10,000-family ID and ISC/display-name
identity provide an unambiguous duplicate match. Presence of that metadata is
authoritative even when the list is empty: database creation consumes the
persisted matches and does not rediscover additional generic groups through ID
arithmetic. Older normalized inputs without `genericUnitMatches` retain the
legacy arithmetic fallback inside the builder.

Mercenary identity remains a separate source-semantic contract. Database
creation consumes persisted `mercenaryUnitMatches` /
`unmatchedMercenaryUnitIds`; matched mercenary records join through their
recorded standard source unit, while explicitly unmatched variants remain
separate. Configured alias groups still come from the pinned identity policy.
During database creation, reinforcement-only source rows are audited against
standard logical groups using the same pinned word-alias policy. Unambiguous
results are persisted as `reinforcementUnitMatches` and feed the same
materialized logical-unit relation; an explicitly empty result keeps those
reinforcement records separate.

Mercenary availability has now completed the same read-path migration for
current normalized snapshots. Repository source occurrences carry
`army_units.availability_kind`, and `mercenary` occurrences require the `mercs`
filter while `standard` occurrences do not. Canonical faction `1` and declared
faction membership are no longer the authority for mercenary filtering when
explicit availability provenance is present. A legacy fallback retains the
previous canonical/faction inference only for database rows where
`availability_kind` is absent.

Canonical ownership, source identity, army grouping, army-list kind, optional
availability category, playability, and application logical identity are separate
semantics. The current normalized/database model exposes mercenary source role,
availability category, and audited identity evidence explicitly. Database
creation resolves configured aliases plus generic, mercenary, and reinforcement
evidence into one materialized logical-unit relation while retaining every source
row for provenance. The repository derives army role/playability from imported
metadata parent relationships and explicit reinforcement links, exposes that
source-derived contract through `/api/armies`, and consumes the materialized
logical-unit relation for unit reads. Clients must not infer logical identity from
numeric ID patterns.

### Current logical-unit materialization

Source ID `1` and grouping identity `901` are now kept distinct in current
normalization. ID `1` remains source-side mercenary identity/provenance with no
application `main_army_id`, while Non-Aligned Army grouping is derived from the
metadata hierarchy generically; current source data happens to use metadata
identity `901` for that grouping node.

Logical-unit identity is now materialized during frontend SQLite creation while
normalized/source records remain unchanged for provenance. The frontend relation
is:

```text
logical_units
  id                     application logical-unit ID
  representative_unit_id source unit used for canonical display/general data

logical_unit_sources
  source_unit_id          original source-defined unit ID; one row per source unit
  logical_unit_id         owning application logical unit
```

For schema version 10, `logical_units.id` equals `representative_unit_id`,
preserving existing unit URLs and API identifiers. Keeping both fields explicit
allows a future application-owned logical ID without rewriting the source model.

Database creation resolves the relation from configured unit aliases in the
pinned identity policy, normalized `genericUnitMatches`, normalized
`mercenaryUnitMatches` / `unmatchedMercenaryUnitIds`, and the database-build
`reinforcementUnitMatches` audit. These remain evidence/provenance; the two
frontend tables are their resolved application identity. The resolver combines
transitive relationships as graph components, selects a deterministic
representative, rejects invalid or contradictory references, and places
explicitly unmatched mercenary/reinforcement variants in independent logical
units.

The enforced invariants are:

- every source-defined unit belongs to exactly one persisted logical unit;
- every logical unit has exactly one representative source unit;
- source rows are never physically merged or rewritten by logical identity;
- profiles, loadouts, unit options, army occurrences, and availability provenance
  continue to reference their original source unit IDs;
- `army_units.availability_kind` remains source-occurrence provenance even when
  standard and mercenary occurrences resolve to the same logical unit and army;
- repository reads consume the materialized relation and do not repeat generic,
  mercenary, reinforcement, or alias identity resolution.

### Design direction: canonical logical-unit payload and source deltas

The current materialized relation answers **which source rows belong to one
logical unit**, but repository/API assembly still reads shared data from source
rows. A later normalization/modeling pass should evaluate whether each logical
unit can have one canonical application payload for fields proven invariant
across its source rows, with army occurrences, profiles/loadouts, and other
source-specific records storing only meaningful differences.

That future deduplication must remain lossless: original source IDs, raw rows,
army membership, availability provenance, source/profile identity, and genuine
loadout/profile differences must remain recoverable. Fields should be promoted
to the canonical logical-unit payload only after an audit demonstrates that they
are invariant or that an explicit precedence rule is justified. This is a
design direction, not current behavior.

Legacy duplicate matching is now a build-compatibility concern. When older
normalized inputs lack the persisted generic or mercenary evidence, database
creation can use the retained legacy fallback before writing the materialized
relation. Every newly built frontend database therefore exposes the same
logical-unit contract regardless of which compatibility path produced it.

Normal availability derived from declared `factions` and optional mercenary
availability derived from mercenary source variants remain distinguishable even
when they occur for the same logical unit and army. The repository now consumes
that explicit normalized availability category. The legacy canonical/faction
inference remains only for compatibility with database rows that lack explicit
availability provenance and can be removed when that compatibility is no longer
required.

Army role/playability is now explicit at the repository/API boundary. Metadata
parent relationships provide main-army, sectorial, and Non-Aligned grouping;
explicit `reinforcements` links provide reinforcement parentage. Grouping
identity `901` is surfaced as non-playable when its imported child lists are
present, and the browser selector consumes `role`/`playable` instead of Army-ID
ranges. Its imported 50-unit source roster remains preserved but is not exposed
as a separate selectable/queryable roster; application unit availability comes
from the playable child NA2 occurrences. Logical-unit consolidation is now a
database-build concern rather than army playability or query-time generic/
reinforcement matching.

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

Frontend-only `logical_units` and `logical_unit_sources` tables are derived
application structure, not normalized source facts, and therefore do not replace
`units` or duplicate profile/loadout/occurrence tables. Repository unit queries
map a requested source or representative ID through `logical_unit_sources`, then
aggregate the associated original source rows. The normalized-input table
registry remains separate from these derived frontend tables so generated
application structure cannot be supplied as normalized source data.

`PRAGMA application_id` identifies an InfinityDB file and `PRAGMA user_version`
records its schema version. The current schema version is 10 and the application
compatibility revision is 15. Imports build temporary sibling files, check
database integrity, then replace the destinations. Incompatible schemas or
compatibility revisions require a rebuild from normalized JSON for now. The
frontend export runs `ANALYZE` after loading and indexing data, preserving SQLite
planner statistics in the immutable snapshot.

## Snapshot provenance and human annotations

### Current

Timestamped `JSON`, `WIKI`, and `SYMBOLS` ZIP files are immutable acquisition
artifacts. Each successful downloader run also writes one version-1 `InfinityDB
snapshot provenance` JSON record under `data/manifests/snapshots/`, labeled
from the archive filename and bound to the archive SHA-256.

The generated manifest has this logical shape:

```text
format / formatVersion
snapshot:
  type
  archive:
    name
    sha256
    path?          # project-relative POSIX form only
  acquiredAt       # timezone-aware ISO-8601
  documentCount
source:
  url
  language?        # Army snapshots
inputArtifact?     # current symbol acquisition input
  name
  sha256
  path?            # project-relative POSIX form only
```

The archive SHA-256 is authoritative snapshot identity. Archive filenames and
paths are labels/provenance and may change independently. Paths are omitted when
the corresponding file is outside the project root so generated provenance
never embeds machine-specific absolute paths. Loading a manifest can re-hash an
archive and reject mismatches.

Manifest JSON is serialized deterministically. A second write of identical
provenance for the same manifest label is idempotent; different provenance for
that label is rejected. Reacquiring identical bytes under a different archive
label may create another record with the same authoritative SHA-256. Generated
manifests are ignored by Git, excluded from Docker build context, and not
automatically pruned.

Corvus Belli's Army `metadata.json` remains source data. It is distinct from
InfinityDB-owned acquisition provenance.

### Army source revision interpretation

Army list and reinforcement JSON documents carry a top-level Corvus Belli
`version` string such as `7.26246.158`. InfinityDB preserves that value exactly
as source provenance. It is **not** the InfinityDB snapshot identity and must not
be treated as a snapshot-wide release number.

Historical Army captures strongly indicate that the middle numeric component
concatenates a two-digit year with a non-zero-padded ordinal day of year. For
example, `7.26246.158` and `7.26246.159` both encode 2026 day 246, which is
2026-09-03; older observed values such as `7.26147.195`, `7.2668.375`, and
`7.25288.295` line up with 2026 day 147, 2026 day 68, and 2025 day 288
respectively. The final component appears to distinguish source data
revisions/builds on that date. The exact Corvus Belli semantics are
undocumented, so this parsing is an evidence-backed InfinityDB interpretation
rather than an upstream contract.
Code must preserve and compare the raw string even if a parsed interpretation is
shown to humans.

A coherent Army snapshot may legitimately contain more than one source data
revision. The 2026-09-10 and 2026-09-18 acquisitions both contained 36 documents
at `7.26246.158` and 22 at `7.26246.159`; all 58 Army/reinforcement documents and
`metadata.json` were byte-identical between those acquisitions. The split is
stable by faction family rather than by sequential download position. Snapshot
coherence therefore cannot be established by requiring one `version` value
across every document.

The Army JSON downloader establishes acquisition coherence with two complete API
passes. The first pass validates metadata and every Army/reinforcement response
without publishing loose files. The second pass re-fetches the same metadata and
source endpoints and requires each response to be byte-identical to its first-pass
response. Any mismatch aborts the acquisition before the immutable archive or
provenance manifest is created and reports the changed filename together with the
first- and second-pass SHA-256 values. Successful runs report the observed raw
source-revision counts diagnostically; mixed revisions are not themselves an
error.

When dates or versions are reported, keep these concepts distinct:

- **snapshot acquisition date/time** — InfinityDB provenance from
  `snapshot.acquiredAt` and the immutable archive/hash;
- **Army source data revision** — the raw per-document Corvus Belli `version`,
  optionally interpreted as its apparent source date plus revision/build.

For example, describe the current material as an Army snapshot acquired on
2026-09-18 containing source revisions `7.26246.158` and `7.26246.159`, rather
than assigning either revision to the snapshot as a whole.

Human-authored snapshot annotations use a separate version-1 `InfinityDB
snapshot note` contract under `data/curated/snapshot-notes/`. Each note requires
`snapshotSha256`, a human description, and an ordered `notableChanges` array; an
optional `compareToSha256` may identify a different comparison snapshot.
Acquisition tools never create, rewrite, or delete these curated notes.

Snapshot notes are not rules-database inputs and do not become runtime
application data. The current contract is a source-controlled annotation format
and validation boundary only.

`army-symbol-build.json` is separate generated build state. Standalone raw symbol
acquisition writes version 2. The orchestrated structural SVG preflight promotes
that state to version 3 after verifying the exact `SYMBOLS` archive, its snapshot
provenance, and each member hash. Version 3 adds a preflight status/summary and a
SHA-256-bound report artifact. Installed-font audit then promotes the same state
to version 4 with available/missing/ambiguous/generic effective-font summaries,
its generated report identity, and the exact tracked font-alias configuration
identity. Detailed reports live under `data/reports/symbols/`. Loaders continue
to accept versions 2 and 3 so prior immutable symbol caches and completed
structural preflights remain valid inputs to their next stage.

### Design direction

Future snapshot-comparison tooling may emit generated diff/report data while
curated snapshot notes remain the human interpretation. The later
`army-symbol-build.json` processing manifest is a separate build-specific
contract and is not represented by acquisition manifests.

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

The current curated-v3 document has collection identity, source records, typed
fact records, maintained vocabularies, scope, Army links, related-record links,
review state, and source-specific citations. PDF sources record the local
reviewed file, Corvus Belli source URL, publication date, and page count; PDF
citations require positive printed page numbers. Archived wiki sources record
the exact timestamped ZIP path/hash, acquisition timestamp, language, document
count, and wiki base URL; citations use archive members. Exact pinned wiki
revisions remain URL-backed sources with a retrieval date.

`vocabularySources` uses the same source-specific locator rules, so wiki
vocabulary references no longer carry artificial printed-page values. The
checked-in v5.3 collection is bound to the English 2026-09-18 wiki snapshot
(`WIKI-en 20260918-130233.zip`, SHA-256
`aa407f1959fbaafce98058acf507640cc94bfc2690d4a7519a547caf1492f23a`).

`infinity-db build-rules` defaults to `data/curated/rules/` and stores those
curated facts in a separate SQLite database rather than either Army-derived
database. Directory ingestion skips `example.json`. Other curated subtrees are
not rules-database inputs. The rules database has an independent schema,
application ID, compatibility version, and replaceable snapshot lifecycle.

A curated rule fact may reference stable application-level identities, but
neither database is an import source for the other; any combined view is
assembled by application code.

Trait identity is one implemented example of that composition boundary. Army
metadata stores raw trait labels and usage, while current curated `trait` records
own canonical names, aliases/misspellings, parameterized source-label prefixes,
concise summaries, and citations. The application joins those sources at read
time; the Army database does not copy curated trait knowledge into its snapshot.

Skill declaration categories are another application-level composition. Army-derived
`skills` and their usage remain source data, while current curated
`skill-declaration-category` records carry the N5 declaration label, deterministic
display order, Army skill links, and printed-page citation. `SkillCatalog` joins
those records at read time and keeps uncited `Unclassified` as the fallback for
skills without a curated declaration. The Army database does not materialize these
rules facts.

Skill parameter interpretation follows the same source/curated split. The imported
Army `extras.type` field determines whether an extra is a distance; this source
semantic is preserved into the frontend database and drives `is_distance` in
repository responses. Curated `skill` records may additionally carry
`facts.parameterSemantics` for rule-derived display behavior such as whether a
positive sign is omitted or forced. `SkillCatalog` joins that hint at read time;
it is not copied into the Army database.

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

The rules schema stores collections, sources, vocabulary definitions,
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
