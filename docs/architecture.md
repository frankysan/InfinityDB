# Architecture

## Project goals

1. **Database backend:** maintain validated, queryable Infinity data, including
   army-specific variants and the source metadata needed to trace it.
2. **Extensible web UI:** provide a unit explorer and rules-reference catalogs
   through focused API endpoints and views.

## Guiding principles

1. **Accuracy:** use official data sources and strive to represent those
   sources as accurately as possible. When source data is incomplete or
   ambiguous, preserve that uncertainty rather than presenting an unsupported
   conclusion as fact.
2. **Flexibility:** expand the ways users can browse and understand the data
   while keeping the experience simple, fast, and customizable.
3. **Transparency:** keep the project open source under the MIT License and
   clearly distinguish InfinityDB's work from outside data, quoted text, and
   image assets, which remain the property of their respective owners.

## Engineering principles

1. **Preserve the source.** Raw upstream data and assets are immutable inputs;
   transformations happen in separate stages.
2. **Never lose information silently.** Merging, normalization, deduplication,
   filtering, and cleanup must preserve provenance and report anything
   discarded, unresolved, or ambiguous.
3. **Code defines behavior; configuration defines maintained knowledge.**
   Domain-specific aliases, mappings, filters, overrides, exceptions, and other
   independently maintained project knowledge should live in validated
   configuration when they can change independently of implementation behavior.
   Generated manifests record provenance/build state rather than maintained
   policy.
4. **One source of truth per build.** Every stage of a build must use the same
   pinned inputs and explicit configuration so the result is reproducible.
5. **Prefer explicit relationships over assumptions.** Model what the source
   actually represents, including many-to-many and source-specific
   relationships, rather than flattening data for implementation convenience.
6. **Build conservatively.** When validation or interpretation is uncertain,
   preserve source or existing valid data rather than guessing or
   destructively correcting it.
7. **Separate stages and responsibilities.** Acquisition, validation,
   normalization, processing, publishing, and deployment should remain
   independently understandable and testable.
8. **Be deterministic and portable.** Given the same inputs and configuration,
   the project should produce the same logical result on Windows, Linux, and
   macOS.

These principles are the canonical engineering decision criteria for the
project. `AGENTS.md` contains immediate operational instructions, while
`docs/AI_CONTEXT.md` records durable invariants and non-obvious decisions.

Data tools are a subsystem of InfinityDB. They remain usable independently for
inspection, validation, and rebuilding snapshots. The standalone scripts in
`tools/` keep their own dedicated regression coverage under `tests/` so their
filesystem safety, URL handling, and cross-platform naming remain validated
independently from the core database and web pipeline.

## Documentation status

This document records both implemented architecture and accepted architectural
direction, but those are not interchangeable:

- **Current** describes implemented repository/application behavior.
- **Design direction** describes an accepted boundary or target shape that is
  not fully implemented yet.
- Concrete implementation work belongs in `docs/TODO.md`; this document should
  not maintain a second backlog.

Unless a paragraph is explicitly marked as design direction or future work,
architectural statements describe the current implementation.

## Configuration, curated data, manifests, and generated state

### Current

InfinityDB currently separates executable behavior, maintained project
knowledge, immutable source material, human-reviewed curated data, and
reproducible build output:

```text
code                         = behavior
config/                      = maintained project/domain knowledge
raw source data              = immutable external input
data/manifests/snapshots/    = generated acquisition provenance
data/curated/rules/          = source-controlled human-reviewed rules data
data/curated/snapshot-notes/ = source-controlled human snapshot annotations
data/generated/              = reproducible database/JSON build output
```

Aliases, mappings, filters, manual overrides, compatibility exceptions, static
asset declarations, and similar maintained domain knowledge belong in
validated, versioned configuration when they can change independently of the
code that interprets them.

`data/curated/` is different from configuration: it contains human-reviewed
information derived from identified external sources and retains source
provenance. `data/curated/rules/` is the only curated subtree currently consumed
by the rules-database build; `data/curated/snapshot-notes/` is a separate
human-annotation contract and is not an application input.

This is not a requirement to make every constant configurable. Values that
define implementation behavior remain in code. Configuration is for maintained
domain knowledge and policy; curated rules data is for human-reviewed
source-derived facts.

`config/validation/source-anomalies.json` records the reviewed normalization
warning ceiling for one exact Army snapshot, including its acquisition date,
archive SHA-256, source-revision counts, and per-warning counts. The comparison
policy remains code: downloader-dated snapshots at or after the baseline may
reduce known warning counts, but a new warning category or growth above a
recorded count is a build regression. Inputs without downloader snapshot
provenance are outside this production-source regression check so synthetic and
investigative normalization remain usable.

`config/identity/source-identities.json` is the first repository-wide example
of the code/config split. It owns maintained logical-identity exceptions for
source unit, army-list, skill, equipment, and weapon IDs plus identity-name
aliases. Generic matching and duplicate-detection algorithms remain code.
Current InfinityDB builds derive unit `main_army_id` from the imported Army
metadata faction-parent relationship, with maintained canonical-faction
overrides taking precedence. The former `xx01` arithmetic remains only as a
standalone/legacy normalization fallback when no usable metadata row exists for
the canonical faction.

Source canonical-faction ID `1` and Non-Aligned Armies grouping ID `901` are
now kept distinct in normalization. ID `1` remains mercenary source/origin
provenance with no application `main_army_id`; the generic whole-army `xx01`
derivation is explicitly suppressed for that source identity. ID `901` remains
the metadata grouping identity for Non-Aligned armies. The former legacy
`1` -> `901` identity-config override has been removed.

The authored identity configuration is a build input, not a deployed runtime
file. InfinityDB normalization validates it, supplies normalization-time
exceptions, and writes the exact document and its deterministic SHA-256 into
`normalized.json`. Database export revalidates that pinned provenance, rejects
incomplete or conflicting identity metadata, and propagates the same policy to
the frontend and raw database metadata. Repository queries revalidate and
consume the policy pinned into that immutable database snapshot. Unit-detail
queries also derive each profile's `profile_identity` from that pinned policy;
browser grouping consumes the backend-derived identity and backend-derived
`display_name`, so browser assets do not duplicate profile alias, reinforcement-
prefix, or ignored-word rules. The maintained reinforcement prefixes themselves
live in the pinned identity policy under `name_normalization`. This keeps deployments self-contained and prevents later working-tree
configuration changes from silently changing the meaning of an existing
normalized or SQLite snapshot.

Weapon catalog policy now follows the same code/config ownership rule without
becoming deployed runtime state. `config/catalogs/weapon-categories.json` owns
the ordered weapon-family taxonomy, regular-expression patterns, fallback
category, and explicit weapon-ID category decisions.
`config/catalogs/weapon-overrides.json` owns corrections for incomplete or
inconsistent Army weapon metadata, such as missing deployable profiles, known
source naming anomalies, and exact metadata-profile rows that should not become
display weapon modes. Normalization validates and consumes both files; those
corrections are applied before normalized metadata rows are materialized, while
the original Army metadata envelope remains preserved for source provenance.
Repository/runtime queries therefore do not read the working-tree configuration.
Classification mechanics,
validation, and fallback behavior remain Python code. Actual game-rule facts
such as special weapon statistics, skills, and equipment are not source
corrections and therefore do not belong in these config files. The Armed Turret
special profile is now a cited curated `weapon` record in `rules.db`; the Army
repository exposes only source catalog/profile data, and the application layer
composes the curated special profile when rules data is available.

Weapon range-table columns are also source-derived rather than maintained domain
policy. The browser builds one ordered set of range endpoints from the finite,
positive `max` values in the displayed weapon profiles' imported `distance`
metadata. Centimetre labels use those source endpoints directly and inch labels
use the shared 2.5 cm conversion, so a new source range endpoint is displayed
without updating a hard-coded global range table.

Skill declaration categories follow the same composition boundary. Army snapshots
identify skills and their usage but do not provide N5 declaration categories. The
curated N5 collection stores those rule-derived declarations as
`skill-declaration-category` records linked to Army skill IDs and cited by printed
rulebook page. The Army repository exposes raw skill catalog/usage data only;
`SkillCatalog` composes declaration categories and other curated skill records from
`rules.db`. Without a valid rules database, skills remain browsable and declaration
categories fall back to uncited `Unclassified` rather than hidden Python rules data.

Skill-extra distance semantics are split according to source authority. Army
`extras.type` is authoritative for whether an extra is a distance; the repository
therefore marks `DISTANCE` extras directly and does not infer distance meaning from
numeric text. Rule-derived presentation details live in curated skill records.
`Super-Jump` and `Forward Deployment` currently use
`facts.parameterSemantics` to state how a positive distance sign should be
displayed. `SkillCatalog` composes that semantic hint into skill, modifier, and
unit API payloads, and browser code formats distances without recognizing skill
names.

Army presentation and classification currently combine imported relationships
with merger-derived fields. Faction grouping, display names, and slugs come from
`metadata_factions.parent`, `name`, and `slug`; repository responses expose this
as `main_faction` for unit summaries/details and `faction` for each army
occurrence. The merger sets `army_lists.kind` to `army` for source documents
that contain a top-level `reinforcements` field and to `reinforcement` for those
that do not. That field therefore captures the current ordinary-list versus
reinforcement-file shape, but it is not an upstream main-army/sectorial
classification. Browser code consumes these backend fields and must not infer
faction or reinforcement semantics from Army ID prefixes or suffixes.

Mercenary units and Non-Aligned Armies are also separate source concepts.
Ordinary unit records declare their normal faction availability through
`factions`. The source additionally contains dedicated mercenary variants that
consistently use canonical faction `1`, an empty `factions` list, a `merc-...`
slug, and army-specific occurrences that supply optional mercenary
availability. Many also use 10,000-offset-style unit IDs, but that numeric
pattern is supporting evidence only. Normalization records mercenary source
roles, army-occurrence availability provenance, and audited mercenary-to-standard
source-unit matches. Generic standard duplicate matching is also audited during
normalization and persisted as `genericUnitMatches`. Database creation consumes
those audits plus configured aliases, performs the reinforcement-only identity
audit using the pinned name-normalization policy, and materializes one
logical-unit relation. The arithmetic duplicate fallback remains only inside the
builder for older normalized inputs that lack the persisted audits. Repository
queries consume the materialized identity and `army_units.availability_kind`;
the old canonical/faction availability inference remains only as a legacy-row
fallback.

### Current: manifests and snapshot notes

InfinityDB now separates generated snapshot provenance from human-reviewed
snapshot annotations:

```text
data/manifests/snapshots/    = generated acquisition provenance
data/curated/snapshot-notes/ = human-reviewed snapshot annotations
```

Generated manifests are not maintained project knowledge. Each Army, wiki, or
symbol acquisition writes a versioned `InfinityDB snapshot provenance` JSON
record labeled from the archive filename and bound to the immutable archive
SHA-256. The manifest stores the snapshot type, archive name and project-relative
path when available, acquisition
timestamp, source URL, document count, optional language, and optional
input-artifact provenance. Symbol acquisition currently records the exact Army
source artifact hash used by the downloader.

Manifest serialization is deterministic and validation can re-hash the archive.
Persistent paths are written only in project-relative POSIX form; external files
retain name/hash identity without embedding machine-specific absolute paths. An
archive-labeled record is immutable: identical regeneration is idempotent and
conflicting provenance for the same manifest label fails rather than rewriting
history. Reacquiring byte-identical content under a different archive label may
therefore produce another provenance record with the same authoritative SHA-256.

Generated snapshot manifests are ignored by Git, excluded from Docker build
context, and retained until explicitly removed. Acquisition tooling never
creates, rewrites, or deletes files under `data/curated/snapshot-notes/`.

Human notes use the separately versioned `InfinityDB snapshot note` contract and
bind to a snapshot by SHA-256. They may contain a description, an optional
comparison snapshot SHA-256, and ordered notable-change notes. Snapshot notes
are source-controlled human interpretation, not rules-database inputs or
runtime application data.

Symbol refresh orchestration is explicit and snapshot-pinned.
`tools/build_symbols.py` requires either `--snapshot` for an existing immutable
Army archive with generated provenance or `--fetch-snapshot` for an intentional
network refresh. It verifies the selected Army archive/provenance and keeps that
same artifact pinned through current raw symbol discovery and resolution;
normal application/database builds never invoke it or acquire network data.

Army-symbol acquisition also writes the version-2
`data/manifests/army-symbol-build.json`. This generated build-state document is
separate from immutable snapshot provenance: it binds the selected Army and
SYMBOLS artifacts and carries the verified Army acquisition pin (source URL,
language, acquisition timestamp, source-document count, and observed source
revisions). It also records every downloaded raw asset by URL/hash/archive path,
preserves every authoritative and audit-only source reference, and stores the
discovery audit counts. Raw assets are resolved in strict order: a matching
Git-ignored local override, an exact-URL entry from the prior validated immutable
symbol snapshot/cache, then upstream network access. The prior build manifest is
the cache index; its referenced symbol archive/provenance and the selected member
hash are validated before reuse. `--refresh-symbols` bypasses the archive cache
without bypassing local overrides. Invalid matching overrides fail rather than
falling through, and unused overrides plus URL/filename collisions are reported.
Its current contract is still raw-resolution only; later symbol processing
stages will extend the build state with their own validated fields rather than
making the downloader assign final application paths.

### Current: army roles and logical-unit identity

Army role/playability is derived in the backend from source relationships
rather than numeric ID patterns or known identity constants. Self-parented
imported ordinary lists that parent other lists remain main armies. An ordinary
imported list that itself parents ordinary lists but whose metadata parent is a
different identity is a grouping node; metadata-only referenced parents can
also be surfaced as grouping nodes. Their children receive the `non_aligned`
role. Current source data uses imported list `901` for the Non-Aligned Armies
grouping role even though `901` has a real source roster and metadata parent
`900`. Ordinary source documents identify their reinforcement list through the
explicit `reinforcements` field, and reinforcement lists do not participate in
grouping-node discovery. `/api/armies` exposes role and playability separately
from source-list existence; grouping identities are non-playable and cannot be
used as selectable `army_id` values, while their source rows remain preserved.
For current NA2 data, InfinityDB intentionally does not expose a separate roster
query for `901`: its roster remains provenance, and application availability is
consumed through the playable child army lists that share those units.

Mercenary source variants are classified during normalization from their
source-semantic contract (`canonical == 1`, empty declared `factions`,
`merc-...` slug), with schema drift reported instead of guessed. Audited
mercenary-to-standard source-unit matches and explicit army-occurrence
availability provenance are persisted and consumed by repository queries. The
10,000-ID offset is supporting matching evidence only, not the semantic rule.

The legacy `1` -> `901` canonical-faction override has now been removed. ID `1`
remains source provenance for mercenary identity and does not receive an
application `main_army_id`; 901 remains a separate Non-Aligned Army grouping
identity. Generic duplicate matching is persisted during normalization and
reinforcement-to-standard matching is audited during database creation; both
feed the materialized logical-unit identity consumed by repositories.

Logical-unit identity is materialized during frontend database creation. This
does **not** merge or rewrite source rows: source unit IDs, army occurrences,
profiles, loadouts, options, and availability provenance remain attached to
their original source unit. The exporter resolves configured unit aliases plus
persisted generic and mercenary matches and the database-build reinforcement
audit into frontend-only `logical_units` and `logical_unit_sources` tables.
Every source-defined unit maps to exactly one logical unit.

A later data-model refactor may materialize a canonical application payload per
logical unit and represent army/loadout/source-specific information as explicit
deltas. That work must be field-by-field and lossless: source IDs, raw rows,
availability, army membership, and genuine profile/loadout differences remain
provenance even if repeated invariant fields are promoted to the canonical
logical-unit payload.

The build-time resolver treats those inputs as identity evidence, combines their
transitive connected components, selects one deterministic representative,
validates missing/conflicting references, and persists the resolved mapping.
Explicitly unmatched mercenary or reinforcement records form their own logical
units. Older normalized inputs that lack the persisted generic/mercenary audits
retain the legacy duplicate fallback inside the builder; repository reads do
not rediscover logical identity.

For schema version 10, the logical-unit ID equals the representative source-unit
ID so existing API IDs and URLs remain stable. `representative_unit_id` is still
stored explicitly, leaving room to decouple application identity from source
identity later without changing provenance. Repository aggregation follows the
mapped source IDs when collecting profiles, loadouts, army occurrences, search
terms, and other source-backed data. It does not pre-aggregate those source
tables into logical copies, because normal and optional-mercenary occurrences
can belong to the same logical unit and army while retaining different
`availability_kind` semantics.

## Snapshot acquisition and provenance

### Current

Standalone Army, wiki, and symbol acquisition uses a common immutable snapshot
model. Downloaders stage loose files temporarily and persist complete timestamped
archives named `JSON YYYYMMDD-HHMMSS.zip`,
`WIKI-<language> YYYYMMDD-HHMMSS.zip`, or
`SYMBOLS YYYYMMDD-HHMMSS.zip`. A same-second collision receives `-2`, `-3`, and
so on rather than overwriting an existing archive.

The archive is the durable acquisition artifact. Wiki acquisition fails closed
for required content: every required eligible URL discovered by the crawl must
be fetched successfully before the downloader creates a
`WIKI-<language> ...zip` archive or provenance manifest. Optional site
chrome/project targets outside the content contract—currently `/favicon.ico`
and pages in the `Infinity:` MediaWiki project namespace—are ignored rather
than treated as acquisition failures. English is the default crawl language and
Spanish is an explicit alternative. Page links are restricted to the selected
language tree, while assets outside that tree may still be mirrored when an
included page directly references them. Failed runs report unresolved required
URLs, leave no incomplete immutable snapshot, and preserve partial crawl work
under `data/work/wiki/` for inspection; successful runs remove their work
directory after publication.

Corvus Belli's Army `metadata.json` remains source data contained in or supplied
alongside Army snapshots; it is not InfinityDB-owned snapshot metadata.

Curated-v3 rules provenance distinguishes local artifacts from upstream source
URLs. The checked-in N5 v5.3 collection binds archived wiki references to the
exact English `WIKI-en 20260918-130233.zip` snapshot/hash; exact `oldid=` wiki
revisions remain URL-backed sources because they are not members of that mirror.

The downloaders also write generated provenance outside the immutable archive
under `data/manifests/snapshots/`. Each version-1 record mirrors the archive
label in its filename, binds to the archive SHA-256, and can verify that hash
before use. Archive labels and portable project-relative paths are
descriptive; the SHA-256 is authoritative identity.
The manifest directory is generated local state and is not committed, included
in Python package data, or shipped in the application container.

Human interpretation has a separate lifecycle under
`data/curated/snapshot-notes/`. Those versioned notes bind to the same immutable
snapshot SHA-256 and are never modified by acquisition tooling.

### Design direction

Automated snapshot-comparison output may later be recorded in generated
manifests or reports while curated notes remain the human interpretation.
Exact timestamped archive identity/hash for wiki-derived curated rules is also a
design direction, not a current guarantee. Migrate the legacy wiki provenance
when the wiki downloader/packager and curated provenance contract are rewritten
together; do not fabricate that association in documentation alone.

## Data flow

The current application data flows are:

```text
Army directory / ZIP
    + required metadata.json
    -> merge + lossless verification
    -> master.json
       + validated identity configuration
    -> normalize + relationship validation
    -> normalized.json + validation report
       + pinned identity document / SHA-256
    -> SQLite importer
       + revalidated pinned identity provenance
    -> infinity.db + infinity.raw.db
    -> repository -> HTTP API -> browser UI

PDF / wiki research sources
    -> human-reviewed cited collections in data/curated/rules/
    -> `infinity-db build-rules`
    -> separate rules.db
    -> rules repository -> HTTP API -> browser UI
```

The two database flows are deliberately independent. `build-rules` consumes
only validated JSON collections under `data/curated/rules/` and skips the
reserved `example.json` template; it never reads PDFs, wiki snapshots, or other
curated subtrees directly. A rules-document update must not rebuild an Army
snapshot, and an Army import must not modify rules data. Where a screen needs
both, the application/service layer joins stable application-level identities
and returns a combined representation; the databases do not import from or
attach to one another.

Asset acquisition and processing is likewise a separate build concern. Current
Army-symbol acquisition is source-semantic and snapshot-pinned: every
`units[].profileGroups[].profiles[].logo` and `metadata.json -> factions[].logo`
reference is authoritative, maintained static declarations are included,
`resume[].logo` is audit-only, and a recursive scan fails closed on unknown
SVG-bearing source fields. URLs are resolved once while every reference is
preserved separately in `army-symbol-build.json`. Acquisition writes version-2
build state. The orchestrator then verifies the immutable `SYMBOLS` archive and
its snapshot provenance, re-hashes every listed member, and rebuilds a derived
`data/work/symbols/<artifact>/raw/` tree rather than modifying the raw archive.
It writes a deterministic structural SVG preflight under `data/reports/symbols/`
and promotes build state to version 3 with the report identity and summary.
Structural preflight covers parse validity, active text, empty text objects, and
font-family declarations. A following installed-font audit reuses the established
CSS/effective-font resolver, applies validated Infinity-specific aliases from
`config/symbols/font-aliases.json`, classifies active-text assets as
`fonts_available` or `fonts_missing`, reports alias normalization and unused
declarations, and promotes the build state to version 4 with both its report and
alias-config identities. Missing/ambiguous effective fonts stop orchestration
before expensive processing. The next integrated stage reuses the established
exact-first visual duplicate detector: byte-identical sets avoid redundant
renders, remaining candidates are compared through decoded RGBA output from the
selected renderer, and inconclusive render failures remain unique. Deterministic
representative ranking prefers `no_active_text`, then `fonts_available`, then
weaker classifications before filename/path tie-breakers. Version-5 build state
records duplicate reports, renderer settings, counts, and a complete portable
`archivePath -> canonical archivePath` mapping while retaining every acquisition
asset and source reference. The downloader does not generate browser mappings.

**Design direction:** later processing will consume that exact version-5 state
through text conversion, compression, and publication. Canonical processing may
collapse equivalent assets, but it must not discard their source references.
Only the publisher will assign final application paths and generated browser
mappings because only that stage knows the final canonical asset after subsequent
processing. Source resolution, validation, deduplication, conversion, compression,
and publishing remain distinct stages with provenance recorded rather than
inferred from final filenames.

## Module boundaries

| Layer | Responsibility | Extension point |
| --- | --- | --- |
| `infinity_army_data` | Interpret and validate source data | Source-format changes and additional normalization |
| `infinity_db.database.schema` | Table definitions, composite keys, references, schema version | New normalized entities and future migration policy |
| `infinity_db.database.importer` | Validate and store a complete snapshot | Alternative storage adapters, such as PostgreSQL |
| `infinity_db.database.repository` | Read-only application queries | Unit details, profile comparisons, catalog queries |
| `infinity_db.web.app` | Validate HTTP input and serialize query results | Additional routes and API resources |
| `infinity_db.web.static` | UI, shared page-shell components, URL state, loading and error handling | New screens, filters, and catalogs |
| standalone `tools/` | Explicit acquisition, validation, and asset-processing workflows | New independent build/input tools |
| deployment scripts | Package and deploy validated application output | Additional deployment targets |

Only the importer consumes normalized JSON. Read-only runtime imports must not
load the importer, Army normalizer, or maintained build-policy configuration as a
side effect; an installed application serving already-built databases is
independent of source-checkout-relative `config/` paths. HTTP routes query the
repository; browser code calls the API. Neither web layer parses raw Army files. Browser
requests live in `api.js`; shared unit-row rendering lives in `unit-list.js`;
page-specific state and rendering live in the corresponding module (for
example, `app.js` or `catalog-detail.js`). The current UI uses native modules
and requires no JavaScript build step. When Corvus Belli graphical symbols are
published into a local installation, army and unit symbols are addressed by
stable ID-and-slug paths while JavaScript maps source identities to those paths.
Those locally acquired graphical assets are not part of the InfinityDB source
distribution or redistributable release artifacts by default; see the
third-party notices for the current rights boundary.

Acquisition tools must not become hidden network dependencies of normal builds.
A normal build can consume explicit local snapshots. Network refreshes are
separate, intentional operations.

## Validation and CI policy

Local test execution now separates hermetic and full-asset coverage explicitly.
`run_checks.py --assets off|auto|required` validates the current published
army/unit/order symbol contract before enabling `full_assets` tests; direct
pytest excludes those tests by default. A detected partial/corrupt local asset
tree is an error in `auto`/`required`, while a completely absent tree is valid
for hermetic testing.

The `Source checks` GitHub Actions workflow now runs the hermetic project check
runner across clean Windows, Ubuntu/Linux, and macOS Python 3.11 checkouts, with
an additional Linux Python 3.14 compatibility leg. It uses the tracked synthetic
Army fixture for database construction and no live acquisition or third-party
graphical assets. `Installed wheel smoke` separately installs the built wheel in
a fresh virtual environment, verifies installed build CLIs and runtime startup,
and consumes maintained build configuration from
`<sys.prefix>/share/infinity-db/config/` rather than repository-relative paths.
`Full-asset checks` provides a dispatch-only GitHub layer restricted to `main`.
It stages a private checksum-pinned published-asset bundle through the
`full-assets` environment and validates it before running the normal checks with
`--assets required`; CI deliberately does not reconstruct publication paths from
raw symbols while the authoritative publisher remains unfinished. The graphical
asset tree is never uploaded as a workflow artifact. The existing container smoke
test continues to validate deployment packaging separately. See `docs/ci.md`.

## Portability and filesystem policy

Python tooling should support Windows, Linux, and macOS unless a component is
explicitly documented otherwise.

Core pipeline logic should use portable filesystem/process APIs rather than
shell-specific command strings or machine-specific paths. External executable
discovery should be centralized and allow explicit configuration before
platform-specific fallbacks.

Generated asset names and persistent generated-state paths should be
host-independent. Treat filenames as case-sensitive internally and detect
case-only collisions before publishing.

Raw inputs are immutable. Persistent generated files should be built and
validated separately and atomically replace prior output where practical.
Failure should leave the previous valid output usable.

## Browser design system

The WSGI page renderer composes every browser route from a page-specific
document, the shared navigation, and shared header/footer fragments. The page
header receives structured breadcrumb and catalog-tag data from the route; the
footer receives the application version. New pages should use the
`<!-- navigation -->`, `<!-- page-header -->`, and `<!-- page-footer -->`
markers so their shell stays synchronized with existing pages.

`static/styles.css` is the browser design-system entry point. Its root tokens
define shared color roles, surfaces, borders, spacing, radii, control height,
focus treatment, and shadows. Reuse these tokens and established components
such as `.main`, `.topbar`, `.explorer`, `.button`, and `.page-footer` rather
than introducing page-local visual values. Detail pages use `.main-detail` to
retain the common layout and responsive behavior. Detail renderers also reuse
`.detail-group`, `.detail-section-title`, `.data-surface-header`, `.data-label`,
and `.badge`; use their modifiers for semantic variants instead of duplicating
detail-table geometry or type treatments.

Surface hierarchy uses `.surface` with default, `--subtle`, or `--highlighted`
variants. Tables use the comfortable default or `.data-table--compact` for
detail and usage data; retain those variants instead of adding page-specific
cell padding or header type rules.

Unit-list and general-profile surfaces may use the unit's named main-army
colors as accents. Keep those accents within the shared token and gradient
system so catalog-specific styling remains legible and consistent.

Browser preferences are stored locally. The Settings sidebar section provides
distance units, a default-off Developer mode, and a developer-only cache-bypass
control; on compact screens it becomes a top-bar menu beside Navigation. New
sidebar or top-bar menus should use this same inline-sidebar and
compact-dropdown pattern. Developer mode sets `data-developer-mode` on the
document root; use `.developer-only` for inline technical details and
`.id-column` for table columns so they remain hidden in the player-facing view
by default.

## Required Army API metadata

The required API `metadata.json` is a supplemental source snapshot. Its records
are preserved separately and enrich display names for matching army IDs.
Faction records also provide explicit parent relationships, names, and slugs
used for unit presentation and grouping. Metadata never creates an army list or
changes unit membership, which continue to come solely from the army JSON
files. Database builds fail when no metadata snapshot is provided beside,
inside, or explicitly alongside the Army source.

Corvus Belli's `metadata.json` is source data. It is conceptually distinct from
the InfinityDB-generated acquisition provenance written under
`data/manifests/snapshots/`.

## SQLite persistence

SQLite is the initial backend because it runs locally without a separate
service. Schema definitions are separate from ingestion code. The current
schema has a schema version of 10 and database compatibility revision of 15; it
rejects incompatible databases with a rebuild instruction. The importer builds
a lean frontend database and a lossless sibling raw archive, creates read-path
indexes after loading, and persists SQLite planner statistics. Migration of
persistent user-authored data is future work; database rebuilds currently
replace a complete imported snapshot.

Rules-reference data uses a distinct SQLite database with its own schema,
compatibility/versioning, importer, and atomic replacement policy. This database
is not an extension of `infinity.db` or `infinity.raw.db`.

The source-controlled `data/curated/rules/` JSON layer is the only
application-facing representation of facts researched from PDFs or the wiki.
`data/pdf/` and `data/wiki/` remain local reference material and are not opened
by application code; `infinity_db.curated.load_curated_document` validates the
rules intermediary contract before the rules importer consumes it.

The current curated-v3 rules contract stores collection scope, source metadata,
typed records, maintained vocabularies, Army catalog links, related-rule links,
review state, and source-specific citations. PDF sources carry both the local
reviewed file and official upstream URL; PDF citations use printed pages.
Archived wiki sources carry exact ZIP/hash provenance and citations use archive
members, while pinned historical wiki revisions stay URL-backed.
`vocabularySources` follows the same locator rules.

No collection may silently combine current, historical, FAQ, and season rules.
Versions 1 and 2 curated-rule files must be migrated before ingestion.

## HTTP API

All routes are same-origin and read-only. `GET` returns JSON or a static asset;
`HEAD` returns the corresponding headers without a body.

HTML is revalidated on each request. API representations have
snapshot-specific ETags and short shared-cache lifetimes; fingerprinted static
assets are immutable for a release. Pages compare both the application version
and snapshot revision with the version endpoint, then reload through a fresh URL
after a deployment or data refresh.

### `GET /api/version`

Returns `{ "version": "0.5.1", "snapshot_revision": "..." }`. The browser uses
it to detect application or imported-snapshot changes.

### `GET /api/armies`

Returns `{ "items": [...] }`. Each item exposes `id`, `name`, `slug`,
legacy source-shape `kind`, explicit `role`, `playable`, `group_id`,
`group_name`, `group_slug`, `parent_army_ids`, and `unit_count`. Roles are
derived from imported source relationships rather than Army-ID ranges or known
identity constants. Self-parented metadata factions that are imported ordinary
army lists are `main`; metadata children of ordinary playable parents are
`sectorial`; children of grouping nodes are `non_aligned`; and lists referenced
by ordinary source `reinforcements` links are `reinforcement`. A referenced
parent is a grouping node when it is absent as an imported ordinary list, or
when it is an imported ordinary list whose own metadata parent is different from
itself. Current source data uses imported list `901` for the Non-Aligned Armies
group, with metadata parent `900` and its own source roster; runtime role
classification does not special-case that ID. Grouping items expose
`playable: false`, and unit counts still reflect preserved source-defined
`army_units`.

### `GET /api/units?army_id=101&search=fusilier&limit=50&offset=0`

Returns `{ "items": [...], "total": 0, "limit": 50, "offset": 0 }`, where each
item has `id`, `name`, `main_army_id`, `main_faction`, `army_ids`, and `armies`
(`id` and `name` per membership). `main_faction` is either null or an object
with `id`, `name`, and `slug`, derived from imported Army metadata. The zero
total above illustrates the response shape.

- Omit `army_id` to browse all source-defined units, deduplicated by global ID.
- Army membership comes from `army_units`, not canonical faction or declared
  faction references.
- `main_army_id` represents canonical whole-army/group ownership. Current
  InfinityDB builds derive it from imported metadata faction parents, with
  explicit maintained overrides taking precedence. The `xx01` derivation is
  retained only for standalone/legacy normalization without usable metadata.
  Canonical source ID `1` is explicitly excluded from application main-army
  ownership and remains mercenary source provenance; Non-Aligned grouping uses
  the separate metadata identity `901`.
- `main_faction` is derived from the matching metadata-faction parent record;
  browser code consumes it directly instead of deriving a faction from Army IDs.
- Search matches accent- and punctuation-insensitive, case-folded name
  substrings, including Unicode.
- Results sort by display name after case-folding, removing diacritics, and
  ignoring punctuation and other non-alphanumeric characters; unit ID breaks
  ties for stable pagination.
- Current normalized snapshots persist audited generic and mercenary unit
  matches. Database creation consumes those audits, configured aliases, and its
  reinforcement-to-standard audit to materialize the transitive logical-unit
  relation. The old 10,000-ID/ISC calculation is retained only as a build-time
  compatibility fallback for older normalized inputs. Configured identity
  aliases remain pinned project policy rather than normalized source facts;
  repository reads use the materialized mapping rather than reconstructing
  logical groups.
- `limit` defaults to 50 and must be between 1 and 200; `offset` defaults to 0
  and must be a nonnegative SQLite integer.
- `search` is limited to 200 characters. Invalid or repeated unit query
  parameters return HTTP 400 with `{ "error": "..." }`. Unknown army IDs return
  an empty list.
- Optional `skill_id`, `equipment_id`, and `weapon_id` parameters narrow
  results to units with matching catalog items in a profile, loadout, or unit
  option.
- Unknown resources return 404; unsupported methods return 405; database read
  failures return 503 without exposing internal exception details.

### `GET /api/units/{unit_id}`

Returns one logical unit, including its general data and the profiles,
loadouts, availability, skills, equipment, and weapons that apply to each army
where it occurs. The response includes the same `main_faction` object used by
unit summaries; each army occurrence also includes its derived `faction` object
or null. Profile records include a backend-derived `profile_identity` used by
the browser to group equivalent labels under the identity policy pinned into
the database. A reinforcement-only source variant is folded into a uniquely
matching standard unit. Current mercenary availability is evaluated from explicit normalized
`availability_kind` source-occurrence provenance at repository-query time. Unknown unit IDs return 404.

### `GET /api/skill-extras`

Returns `{ "items": [...] }` of distinct skill/extra combinations whose imported
Army extra has `type = DISTANCE`, together with the units using each combination.
When curated rules define skill parameter semantics, each item also carries the
corresponding `parameter_semantics` display hint. The Skill Modifiers browser
page consumes this endpoint.

### Rules-reference endpoints

`GET /api/skills`, `GET /api/equipment`, and `GET /api/weapons` return
`{ "items": [...] }` for their searchable catalogs. Catalog records combine
equivalent source labels where appropriate and include an ID, display name, and
reference link when the metadata snapshot provides one.

`GET /api/skills/{id}`, `GET /api/equipment/{id}`, and
`GET /api/weapons/{id}` return one catalog item and its distinct usage variants.
Each variant includes the relevant extras and logical units that use it. Weapon
details additionally include metadata weapon profiles, such as ammunition,
traits, and range data, when present in the supplied metadata snapshot.
Metadata weapon/equipment profiles retain the raw `traits` value. The application
composition layer also exposes `trait_references`: each reference preserves the
raw `label` and, when a matching curated trait record is available in `rules.db`,
adds that record's canonical `name` and stable trait-catalog `slug`. Exact source
aliases/misspellings and parameterized source-label prefixes are curated rule
data rather than Python tables. Without a valid `rules.db`, raw Army trait labels
remain browsable and linkable but no curated canonicalization or summary is
invented. Browser rendering consumes these backend-derived references and does
not canonicalize trait text or generate trait slugs independently.

Skill list/detail responses obtain declaration categories from current curated
`skill-declaration-category` records in `rules.db`. Category records themselves are
composition metadata and are not emitted as ordinary skill `rules`; other curated
skill records remain available through that field. If rules data is unavailable or
a skill has no curated declaration, the API reports an uncited `Unclassified`
category.

`GET /api/traits` returns the shared-traits catalog composed from raw Army usage
and optional current curated trait records. `GET /api/traits/{slug}` returns a
trait's usage grouped across skills, equipment, and weapons; when curated rules
are available it also includes the cited rule record and its concise summary.

Future implementation work is tracked in `docs/TODO.md`; this document records
current architecture and clearly labeled lasting design direction rather than
maintaining a second backlog.
