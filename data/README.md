# Data directories

**Project domains:** Acquisition, Data processing

InfinityDB separates external inputs, human-reviewed material, generated
provenance/state, and build outputs.

## Current paths and behavior

- `raw/` — immutable downloaded Corvus Belli Army snapshot archives. Army
  acquisition writes `JSON YYYYMMDD-HHMMSS.zip`; symbol acquisition uses the
  `raw/symbols/` subtree for `SYMBOLS YYYYMMDD-HHMMSS.zip`. Ignored by Git.
- `wiki/` — local wiki research material. The downloader persists immutable
  `WIKI-<language> YYYYMMDD-HHMMSS.zip` Infinity Wiki snapshots here; English (`en`)
  is the default and Spanish (`es`) is an explicit alternative. Human Sphere uses the
  distinct English-only `HUMAN-SPHERE YYYYMMDD-HHMMSS.zip` identity. History-enabled
  acquisitions add `-history` before the timestamp. Ignored by Git.
- `pdf/` — local rules/FAQ/ITS research documents. Ignored by Git.
- `work/wiki/` — local wiki crawl work. Successful acquisitions remove their
  work directory after publishing the immutable archive and provenance;
  incomplete/error runs preserve downloaded work here for inspection. Ignored
  by Git.
- `work/symbols/` — rebuildable loose symbol work trees keyed to the immutable
  `SYMBOLS ...zip` identity. The orchestrator verifies the raw archive and every
  member hash before replacing this derived work tree. Ignored by Git.
- `reports/symbols/` — generated, SHA-bound symbol-processing reports for
  structural preflight, installed-font audit, duplicate detection, text
  conversion, compression, and publication. Ignored by Git.
- `logs/symbols/` — complete verbose transcripts from `tools/build_symbols.py`.
  Interactive console output is intentionally compact; these timestamped logs
  retain detailed per-stage and per-asset diagnostics. Ignored by Git.
- `backups/symbols/` — timestamped backups of SVGs that existed in the previous
  publication but not in the incoming one. Publication creates these only as
  part of a successful replacement transaction. Ignored by Git.
- `manifests/snapshots/` — downloader-generated snapshot provenance. Each JSON
  record is labeled from the archive filename, records both the logical snapshot
  content SHA-256 and exact archive SHA-256, and records the snapshot type,
  archive label/path when project-relative, acquisition time, source URL,
  document count, optional language, and optional input-artifact provenance. Army
  manifests also record the latest source-data date encoded by the contained Army
  document versions.
  Ignored by Git, excluded from Docker build context, and outside Python package
  data.
- `manifests/symbol-publication.json` — tracked release manifest for the processed SVG
  publication. It owns the published path/SHA-256 inventory, browser mappings, summary,
  and compact Army source archive identity used to bind `army.db` during deployment.
- `manifests/army-symbol-build.json` — generated current symbol-build state from
  acquisition version 2 through terminal publication version 8. It binds the
  pinned Army/SYMBOLS artifacts, stage reports/settings, canonical mapping, and
  publication artifacts. Ignored by Git and not required for deployment.
- `curated/rules/` — source-controlled, human-reviewed rules-reference
  collections consumed by `infinity-db build-rules`.
- `curated/identities/` — source-controlled, reviewed source-derived identity and
  presentation relationships consumed by the relevant build/normalization stage.
- `curated/snapshot-notes/` — source-controlled, human-authored descriptions,
  comparison targets, and notable-change notes bound to immutable snapshots by
  SHA-256. Acquisition tools never modify this subtree.
- `generated/` — the two tracked, complete runtime databases: `army.db`
  (Army v31/compatibility 40) and `rules_n5.db` (Rules v17). Exact variants,
  reviewed Weapon citations, deployed objects, Restrictions, reviewed reference
  facts and symbol mappings are embedded. ITS Season 18 remains in Rules until P3.
  The old filenames and required JSON publications are retired.

**Complete runtime build:** `infinity-db build --compact` uses the newest local
Army ZIP and selected API metadata plus maintained Rules/configuration inputs.
An explicit source ZIP pins another input; `--metadata` selects external
metadata. It never downloads data. Default output is `data/generated/`;
`--db-dir PATH` selects a complete alternate destination and is independent of
the serving-only `INFINITY_DB_DB_DIR` setting. The old `--output-dir` form is
retired from the integrated build. Lossless verification is mandatory.

Disposable files under ignored `data/work/build/` hold normalization, the matched
Army/raw pair and Rules construction. The builder validates both final files,
embedded source relationships and shared build provenance, checks that its inputs
remain unchanged, then replaces the selected pair and discards intermediates.
Generation/validation failure before replacement preserves destination bytes.
Unrelated destination files are preserved. Stop serving before rebuilding; a
mid-replacement interruption leaves an invalid mixed set, recovered by rerun.

Normal serving opens only that completed directory. Precedence is explicit
`serve --db-dir PATH`, `INFINITY_DB_DB_DIR`, then `data/generated/` relative
to the working directory. WSGI requires the environment setting. The retired
individual-database variables are rejected. There is no automatic checkout
bundle selection or older-file fallback. Docker copies the same tracked pair
directly into its image. The cache revision hashes sorted active filenames and
their exact file hashes.

`infinity-army build --output-dir PATH` retains the source JSON pipeline;
`infinity-db export NORMALIZED.json OUTPUT.db` explicitly creates an Army/raw
development pair. Their work outputs are not complete serving sets.
`build-rules` retains a narrow standalone v10 export in ignored
`data/work/build/rules-standalone.db`, without runtime assembly or promotion.
Research tools receive an explicit raw archive path; normal serving never opens it.

Source/release verification compares the recorded build-input hashes against
maintained files and validates SVG bytes before image creation. Runtime startup
validates embedded provenance, schemas and contents without re-reading build
JSON, raw sources or working-tree policy. Installed build resources may still
exist for independent development commands; they are not serving dependencies.

**Selected runtime health:** `infinity-db database-health --db-dir PATH`
validates exactly the selected directory through the shared
`infinity_db.database_set` validator. Normal startup and directory health require the complete `army.db` and
`rules_n5.db` pair, Army v31 and Rules v17, with recorded matched provenance.
Low-level fixture APIs retain explicit older-model injection for semantic tests;
they do not establish an operator-facing alternate selection contract.

It checks schema/application compatibility, full SQLite integrity and foreign keys,
embedded deployed-object/Army pairing, embedded variant identities/extras/counts
in v11–v17, and current PDF, page, review and Army-profile bindings of the
embedded v12–v17 Weapon citations or older JSON publication. v13 onward also
checks six source-ordered Restrictions chart rows, fourteen exact conditions
against the separate normalized constraints, original labels/notes/links,
qualifiers, source identity and embedded content fingerprint. v14 checks
all current canonical Trait identities, their reviewed Wiki URLs and names,
and a complete link inventory with a deterministic content fingerprint.
v15 validates six source-reviewed Combined Saving Roll Weapon/mode
signatures against the selected Army, the current Rules PDF and the
relational source fingerprint. No calculation of saving-roll outcomes
or interpretation of Ammunition composition is added.
v16 verifies 16 reviewed Ammunition ID/name pairs against the
selected Army, the 11 base canonical N5 Ammunition records,
five separately authored ordered combined compositions, and the
content fingerprint. No component semantics are inferred from source text.
v17 validates the 12 authored Weapon Property definitions, ordered
origins, source-profile/mode and Trait lists against current canonical
N5 records and the selected Army. Their source-authority and content
fingerprints are checked without creating official rules records.
It reports final file SHA-256 hashes and returns a nonzero status for an
incomplete, corrupt or mismatched set. It never creates missing files,
selects another directory, rebuilds curation or reads the raw archive.
The strict check also verifies shared build-set identity, family roles and
required Army export generation. Other files are ignored and cannot repair a
missing projection. The builder, health CLI, direct server, WSGI and image checks
all apply this complete-set contract. The low-level validator can inspect
transitional fixtures when explicitly requested by development code.

`infinity_db.web.create_app_from_database_set(PATH)` validates and opens exactly
the selected pair, without selecting environment paths or discovering another
directory. The semantic-baseline tool's `--db-dir` exercises this factory.

The current two-file layout embeds Army v31 Equipment presentation
encodings, reviewed Skill source classifications, Unit filter semantics,
Army overview text, legacy identities and symbol mappings/hashes,
plus Rules v17 Weapon Properties, variant/Weapon/Restrictions, Trait Wiki, Combined Saving Roll
and Ammunition publications. P2.4 materialization is complete for the normal runtime.
Older v10–v16 Rules layouts
remain transitional compatibility. The browser
fetches `/api/restrictions/chart`; for a pre-v13 release the endpoint
returns its original packaged static publication. The v13+ chart
handler reads SQLite only. v14 Trait pages read reviewed Wiki links from
Rules SQLite without loading their packaged configuration; pre-v14
releases keep their existing JSON adapter. v15 Combined Saving Roll
profiles are read from Rules SQLite; pre-v15 releases retain the
maintained source JSON adapter. v16 Ammunition display links and
combined-component references are read from Rules SQLite; pre-v16
releases retain the reviewed JSON adapter. v17 Weapon Property origins
and exact source-profile references likewise read from Rules SQLite;
earlier schemas retain their validated JSON adapter. The v27
EquipmentCatalog reads Cube mappings from Army SQLite; v26
retains its validated JSON adapter. v28 Skill source classifications
are consumed by SkillCatalog and Unit-detail presentation from
Army SQLite, while older snapshots use the reviewed JSON adapter.
v29 Unit Explorer filtering and filter-choice presentation read their
overlays from Army SQLite; earlier schemas retain the JSON adapter.
v30 Army overview summaries and historical identities are read from Army
SQLite for `/api/armies` and legacy-aware search; earlier schemas and
explicit source tools retain their authored JSON adapters.
v31 symbol lookups and cache identity use embedded maps/hashes plus actual
packaged SVG/static bytes, without reading the publication manifest. The
builder and application startup verify published SVG hashes; selected-set
database health checks validate the stored projection without opening assets.
The separate Army/raw pair remains source-identical through shared export metadata and
each extended schema's checksum includes its relational rows.
It does not verify working-tree curation/config freshness or graphical
assets; release/source and graphical-publication checks still own those
obligations. `--db-dir` is explicit and cannot be combined with an individual
database argument or `--require-raw`. The existing individual Army/raw health
command remains available. The [data model](../docs/data-model.md#shared-metadata-and-integrity)
owns the embedded build-provenance fields. The P2.6 filename, default
selection and shared serving-directory contract are implemented; remaining
cleanup and integration acceptance are in the [restructuring plan](../docs/restructuring-plan.md).

Raw inputs, generated acquisition/build provenance, and intermediate outputs stay outside
source control so machine-local snapshot state does not obscure code changes.
For the private Linux worker, [Syncthing-staged development assets](../docs/syncthing-assets.md)
defines the separate source staging and explicit, verified checkout activation procedure.
The tracked `army.db` and `rules_n5.db` are release artifacts: a tagged
checkout includes exactly what production serves. Their embedded projections
bind reviewed source relationships and common build provenance; runtime JSON
sidecars are not release inputs. Rebuild the complete pair from pinned source
inputs when maintained code or curation changes, then validate its source
freshness and published symbols before commit or deployment. Never rebuild on
the deployment host or rewrite binary artifacts during packaging. Ignored
build/acquisition manifests remain local provenance records.

Generated Army database data is replaceable. Builds create temporary application
and raw-archive siblings, validate both before publication, and bind them with the
same deterministic `export_pair_sha256` metadata. That fingerprint covers the full
normalized source model plus the shared build metadata, including source-only rows
that do not appear in the application database.

The two destination files cannot be replaced as one filesystem transaction, so
publication has an explicit commit order and recovery policy:

1. replace `army.raw.db` first;
2. replace `army.db` last; the application replacement is the commit point.

If a process stops before the raw replacement, the previous pair remains. If it
stops between replacements, normal serving remains on the previous validated
`army.db`, while the newer raw archive is intentionally treated as unpaired.
Raw-dependent audit tooling must validate the pair metadata and fail closed rather
than combine generations. Rerunning the export rolls both siblings forward and is
the supported recovery operation; temporary files are not a rollback contract. On
a first-ever publication, the same interruption may leave only the raw sibling, and
a rerun completes the pair. If the process stops after the application replacement,
both destination siblings already belong to the new generation.

Older pairs created before `export_pair_sha256` remain acceptable when their full
shared metadata dictionaries match. New exports always carry the stronger pair
fingerprint. `infinity-db database-health data/generated/army.db --require-raw` is the
operator-facing validation command for this pair contract; omitting `--require-raw` validates only
the published application database.

For local source inspection, the read-only `tools.inspect_raw_archive` CLI
checks the application/raw sibling pairing *before* reading any lossless
source rows. It uses the imported table inventory from the paired metadata;
zero-row source tables remain visible, and table names are never accepted
outside the normalized source schema. From the repository root:

```powershell
.venv\Scripts\python.exe -m tools.inspect_raw_archive verify
.venv\Scripts\python.exe -m tools.inspect_raw_archive tables
.venv\Scripts\python.exe -m tools.inspect_raw_archive row skills 0
.venv\Scripts\python.exe -m tools.inspect_raw_archive rows skills --start 0 --limit 20
```

The `--application` and `--raw` flags select explicit sibling paths when
inspecting a different local build; a stale or mismatched pair fails closed.
Rows are exact source JSON, not application identities. Bounded listings
accept at most 100 entries per invocation. This tool does not change
imported, curated or published data, and it is not part of the runtime API.

PDFs and wiki snapshots are research sources, not Army-pipeline inputs. The
curated rules contract records the local reviewed artifact plus its upstream source URL;
`curated/README.md` owns the current format version and validation rules. PDF citations use
printed pages. Archived wiki sources bind to an
exact timestamped ZIP/hash and citations use archive members; exact pinned wiki
revisions remain URL-backed sources.

The [local PDF revision inventory](../docs/n5-source-history.md#local-pdf-revision-inventory-2026-11-06)
records available rules, FAQ and ITS revisions, their exact hashes and renamed
locators. Additional local revisions are research evidence until explicitly
reviewed and selected; they do not automatically replace cited publications.

Official Corvus Belli news posts can provide **dated, supplementary publication-change
and clarification evidence**, separate from the underlying rules, Army, FAQ, and ITS
sources. The relevant N5.3 release announcement is
<https://infinityuniverse.com/en/news/infinity-rules-update-5-3>, published **2026-09-01**.
It contains distinct Army and N5.3 rules changelogs, plus ITS Season 18 context.
Record the post URL/date and the applicable changelog scope when citing a change;
verify the actual rule or profile against the corresponding versioned primary source
before changing maintained gameplay data. This web URL is a reference, not a
byte-pinned local artifact or a new implicit build/network dependency.

Use [N5 source and update history](../docs/n5-source-history.md) for the indexed
official notices, the historical Army backup source, and the mandatory cross-source
research procedure. Current Army/PDF/FAQ/Wiki evidence and historical sources must
be versioned separately; neither a blog post nor a third-party Army backup
establishes current gameplay truth by itself.

## Snapshot provenance contract

Army, wiki, and symbol downloaders write version-3 `InfinityDB snapshot
provenance` documents under `manifests/snapshots/`. Version 3 retains the logical
content and exact archive identities introduced in version 2 and adds
`source.dataChangedOn` for Army snapshots. Version-1 and version-2 manifests remain
valid historical provenance.
Wiki acquisition is fail-closed for required content: if any required eligible URL or required
MediaWiki enumeration request cannot be fetched, the run reports the failed URLs, publishes no
archive or snapshot provenance, and preserves the partial crawl under `work/wiki/`. Optional site
chrome/project links that are not part of the mirrored content contract—such as `/favicon.ico`
and configured MediaWiki project namespaces—are reported as ignored rather than failures. Infinity
Wiki crawls are language-scoped: English is the default, Spanish is selected explicitly,
same-language pages are mirrored, and cross-language assets are included only when an included
page references them. Human Sphere is currently English-only; its MediaWiki-enumerated
main-namespace page inventory is the required content contract, so orphaned content pages remain
covered while stale link-discovered HTTP 404s do not block publication. Human Sphere Talk pages and
site-service endpoints are also ignored as non-content, while transient/server failures and any
failed API-enumerated page remain fatal. Requests use a source-specific courtesy delay. Only a
complete successful crawl becomes an immutable wiki snapshot.

The manifest filename mirrors the archive label with a `.json` suffix. Version 2
and later store two separate SHA-256 values:

- `snapshot.contentSha256` identifies the logical snapshot from normalized
  relative member paths plus member bytes. ZIP timestamps, permissions,
  compression method/level, entry order, comments, and other container metadata
  do not affect this identity.
- `snapshot.archive.sha256` identifies the exact ZIP byte stream and remains the
  integrity check for the physical artifact.

Snapshot ZIP creation also normalizes member ordering, timestamps, permissions,
comments, and extra fields and uses a fixed DEFLATE profile, so archives created
by the same implementation from identical files are byte-for-byte reproducible.
The logical content hash remains independent of compressor implementation details.
Generated JSON serialization is deterministic.

Persistent paths are stored only when the file is inside the project root, and
then use portable project-relative POSIX form. Machine-specific absolute paths
are never written. A repeated attempt to write identical provenance for the same
manifest label is idempotent; conflicting provenance for that label fails instead
of rewriting the record. Reacquiring the same logical content under a different
archive label may therefore produce another provenance record with the same
`contentSha256`, even if the exact archive SHA-256 differs.

Symbol snapshot provenance also records the hash of the Army source artifact
used by symbol acquisition. `tools/build_symbols.py` verifies the corresponding
Army snapshot provenance before discovery and keeps that exact archive pinned
through the complete symbol build. Acquisition writes version-2
`army-symbol-build.json`, persisting the Army archive identity together with
source URL, language, acquisition timestamp, source-document count, and observed
source revisions. Verified structural preflight promotes state to version 3;
installed-font audit promotes passed preflight to version 4; exact-first visual
deduplication promotes passed font-audit state to version 5; canonical text
conversion promotes version 5 to version 6; balanced compression promotes passed
version 6 to version 7; and final publication promotes passed version 7 to the
terminal version-8 state.

Each stage records the reports/settings needed by its successor. Version 7 binds
every compressed canonical SVG through the SHA-bound compression report. Version
8 binds the canonical `symbol-publication.json` plus the publication report and
final byte/count accounting. The publication manifest owns every published SVG
path/SHA-256 together with the runtime Army, Unit/profile, and static mappings plus the
compact Army source archive name/SHA-256 used to bind the tracked runtime database during
deployment. Stage promotion is
forward-only. Failed-stage retry is explicit where supported; later passed states
are not silently rolled back to rerun an earlier helper. Loaders still accept
versions 2 through 8 as valid historical/intermediate state for compatibility.

The human annotation contract is documented in
[`curated/snapshot-notes/README.md`](curated/snapshot-notes/README.md). Snapshot
notes are not application/runtime inputs. Their version-1 contract uses the exact archive SHA-256;
logical-content identity in acquisition provenance does not change that maintained binding.

Army JSON `version` values are per-document Corvus Belli source revisions, not
InfinityDB snapshot versions. Their evidence-backed interpretation and the
required distinction between source revision and snapshot acquisition date are
documented in [`docs/data-model.md`](../docs/data-model.md#army-source-revision-interpretation).

## Symbol build lifecycle

This file owns the current acquisition/build-state and publication lifecycle for symbol artifacts.
[`docs/architecture.md`](../docs/architecture.md) defines only the subsystem boundary, while
[`docs/data-model.md`](../docs/data-model.md) defines runtime identity/persistence semantics.
Implementation details remain in the symbol tooling, and unfinished lifecycle work belongs in
[`docs/TODO.md`](../docs/TODO.md).

Raw Army data, generated databases, PDF documents, wiki snapshots, and Corvus
Belli graphical assets are not covered by InfinityDB's MIT License. Corvus Belli
has explicitly permitted redistribution of the processed graphical publication used by this
non-commercial project. By project policy, the generated runtime databases are also distributed
only as part of the non-commercial InfinityDB application/release and remain outside the MIT
License. The tracked `data/generated/army.db` and `rules_n5.db` are therefore release artifacts,
while raw Army/wiki/PDF/source-symbol archives remain separate local provenance inputs. Review the
repository's
[third-party notices](../THIRD_PARTY_NOTICES.md) for the full boundary.
