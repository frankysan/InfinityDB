# Data directories

**Project domains:** Acquisition, Data processing

InfinityDB separates external inputs, human-reviewed material, generated
provenance/state, and build outputs.

## Current paths and behavior

- `raw/` — immutable downloaded Corvus Belli Army snapshot archives. Army
  acquisition writes `JSON YYYYMMDD-HHMMSS.zip`; historical symbol archives
  may remain in `raw/symbols/`. Ignored by Git.
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
- `work/symbols/`, `reports/symbols/`, `logs/symbols/` and `backups/symbols/`
  may contain ignored historical in-tree processing evidence. The retired
  processor cannot resume it; accepted external promotions use a transaction
  under `local/`.
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
- `manifests/army-symbol-build.json` — ignored historical in-tree build evidence,
  not a current pipeline, publication, or deployment input.
- `curated/rules/` — source-controlled, human-reviewed rules-reference
  collections consumed by `infinity-db build-rules`.
- `curated/identities/` — source-controlled, reviewed source-derived identity and
  presentation relationships consumed by the relevant build/normalization stage.
- `curated/snapshot-notes/` — source-controlled, human-authored descriptions,
  comparison targets, and notable-change notes bound to immutable snapshots by
  SHA-256. Acquisition tools never modify this subtree.
- `generated/` — the three tracked runtime databases: `army.db`
  (Army v31/compatibility 40), `rules_n5.db` (Rules v17), and
  `its_18.db` (ITS v2). Exact variants, reviewed Weapon citations,
  deployed objects, Restrictions, and symbol mappings remain embedded in
  Army/Rules. The ITS database owns Season 18 Battleground and scoped
  tournament/Extra policies; it is selected by exact season and revision.
  See [ITS season database](../docs/its-season-database.md).
  The old filenames and required JSON publications are retired.

**Complete runtime build:** `infinity-db build --compact` uses the newest local
Army ZIP and selected API metadata plus maintained Rules/configuration inputs.
An explicit source ZIP pins another input; `--metadata` selects external
metadata. It never downloads data. Default output is `data/generated/`;
`--db-dir PATH` selects a complete alternate destination and is independent of
the serving-only `INFINITY_DB_DB_DIR` setting. The old `--output-dir` form is
retired from the integrated build. Lossless verification is mandatory.

Disposable files under ignored `data/work/build/` hold normalization, the
matched Army/raw pair, Rules and ITS construction. The builder validates all
three runtime databases, cross-domain references and source/build provenance,
checks that its inputs remain unchanged, then replaces the selected set and
discards intermediates.
Generation/validation failure before replacement preserves destination bytes.
Unrelated destination files are preserved. Stop serving before rebuilding; a
mid-replacement interruption leaves an invalid mixed set, recovered by rerun.

Normal serving opens only that completed directory. Precedence is explicit
`serve --db-dir PATH`, `INFINITY_DB_DB_DIR`, then `data/generated/` relative
to the working directory. WSGI requires the environment setting. The retired
individual-database variables are rejected. There is no automatic checkout
bundle selection or older-file fallback. Docker copies the same tracked
three-file set into its image. The cache revision hashes sorted active filenames and
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
`infinity_db.database_set` validator. Startup and directory health require `army.db`, `rules_n5.db`
and `its_18.db`, Army v31 / Rules v17 / ITS v2, with matched provenance
and compatible source and core revisions.
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

The standalone
[InfinityDB-army-acquisition](https://github.com/frankysan/InfinityDB-army-acquisition),
[InfinityDB-wiki-acquisition](https://github.com/frankysan/InfinityDB-wiki-acquisition)
and [InfinityDB-symbol-tools](https://github.com/frankysan/InfinityDB-symbol-tools)
producers write version-3 `InfinityDB snapshot provenance` documents under the
selected working directory's `manifests/snapshots/`. Producers hand off only immutable
source ZIPs and their matching manifests. InfinityDB's offline
`tools.army_snapshot_source` verifies acquired Army ZIPs; the normal build,
serve and Docker workflows never install or run the external producers. Version 3 retains the logical content and exact
archive identities introduced in version 2 and adds `source.dataChangedOn` for
Army snapshots. Version-1 and version-2 manifests remain valid historical
provenance.
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

Symbol snapshot provenance also records the hash of the Army source artifact.
The external producer records its stage inputs and outputs in SHA-bound receipts;
InfinityDB verifies their chain before preparing a candidate. The tracked
publication manifest owns each published SVG path/SHA-256, runtime Army,
Unit/profile and static mappings, and the compact Army source archive identity
used to bind the tracked database during deployment. Historical in-tree
`army-symbol-build.json` states are evidence, not resumable processing inputs.

The human annotation contract is documented in
[`curated/snapshot-notes/README.md`](curated/snapshot-notes/README.md). Snapshot
notes are not application/runtime inputs. Their version-1 contract uses the exact archive SHA-256;
logical-content identity in acquisition provenance does not change that maintained binding.

Army JSON `version` values are per-document Corvus Belli source revisions, not
InfinityDB snapshot versions. Their evidence-backed interpretation and the
required distinction between source revision and snapshot acquisition date are
documented in [`docs/data-model.md`](../docs/data-model.md#army-source-revision-interpretation).

### Cross-repository acquisition handoff (P5.3)

Optional acquisition may run from a different Git repository or machine.
Its supported handoff to InfinityDB is **a complete immutable ZIP plus
its version-3 snapshot provenance JSON**, not a Python module import
or an on-disk crawler work tree. The receiving checkout supplies both
paths explicitly and verifies the hashes with
`infinity_db.snapshot_provenance.load_snapshot_manifest(path, archive=zip_path)`.
The manifest's `archive.path` is an optional producer-relative locator,
not an instruction to read from the producer's directory. The exact
archive SHA-256 and logical `contentSha256` remain authoritative
after copying or renaming the ZIP. Incomplete acquisitions are not
handed off; changed bytes and missing or mismatched provenance fail
closed. The portable copy/rejection contract is tested for Army, Wiki
and symbol snapshot types in `tests/test_snapshot_provenance.py`.

The current producer contracts are:

- **Army:** `JSON YYYYMMDD-HHMMSS.zip` with one `metadata.json`
  and validated per-faction `<id>-<slug>.json` documents. Manifest
  type `army` includes source URL/language, acquired timestamp,
  document count and `source.dataChangedOn` derived from the contained
  source revisions. Two download passes must agree before publication.
  The offline importer remains in InfinityDB; external acquisition
  must not choose a rules interpretation or rebuild runtime databases.
- **Infinity Wiki / Human Sphere:** `WIKI-<language> ...zip` or
  `HUMAN-SPHERE ...zip` containing complete, portable relative
  HTML/asset paths and optional `_history` revision data. Manifest
  type `wiki` pins the source URL, language, acquired timestamp
  and file count. Required-page failures must not publish an archive.
  The archived pages remain research inputs, never an implicit
  runtime/source-authority update.
- **Symbols:** `SYMBOLS ...zip` plus type `symbols` provenance
  bound to its input Army artifact by `inputArtifact.sha256`.
  `InfinityDB-symbol-tools` owns raw acquisition, reviewed SVG overrides, font alias/substitution,
  text-to-path conversion, duplicate detection and compression.
  InfinityDB remains responsible for authoritative source selection,
  semantic/browser identity mappings, final static asset placement
  and `symbol-publication.json`. Browser UI font packaging
  (`prepare_web_fonts.py`) is separate from SVG font substitution.
  As preparation, `tools.export_symbol_source_plan` can explicitly
  generate a **read-only** v1 request plan from a verified Army ZIP,
  the pinned static declarations and legacy identity configuration.
  It records only sorted approved URLs, selected archive paths and
  the input Army file's name/SHA-256. The independent
  [InfinityDB-symbol-tools](https://github.com/frankysan/InfinityDB-symbol-tools)
  validator can check the plan and input bytes offline. An explicit
  `infinity-symbol-source --acquire` in the standalone repository now
  produces a deterministic raw `SYMBOLS ...zip`, its Army-bound v3
  snapshot provenance and a separate `.raw-report.json` of acquired
  and HTTP-404-unavailable source URLs. The request plan is **not**
  snapshot provenance and does not confer source authority by itself.
  Use `tools.verify_raw_symbol_handoff` in InfinityDB to verify the
  complete external ZIP/manifest/report against the pinned Army ZIP
  and source plan. The former in-tree acquisition, override and processing
  commands have been retired. Normal database builds do not acquire assets.
  For separate override processing, `tools.export_symbol_override_lookups`
  generates a SHA-pinned URL-to-override-path plan. The standalone
  `infinity-symbol-overrides` command can then create an intermediate
  `EFFECTIVE-SYMBOLS ...zip`, its v3 Army-bound provenance and a
  version-1 effective report recording raw/upstream, override and
  effective SVG identities. `tools.verify_effective_symbol_handoff`
  checks that chain independently, optionally against local reviewed
  override files. The standalone `infinity-symbol-preflight` and
  `infinity-symbol-font-audit` commands now produce matching legacy
  audit report formats plus immutable, hash-pinned stage receipts.
  These audit steps do not modify the effective SVG ZIP or promote it
  to publication-ready status. The standalone
  `infinity-symbol-duplicates` stage now consumes the passed font
  audit and produces canonical SVG mappings, the three existing
  exact/visual duplicate CSVs and a hash-pinned stage receipt
  containing renderer/version/settings. Render failures remain
  visible and fail the receipt instead of claiming visual coverage.
  `tools.verify_symbol_duplicate_handoff` verifies its byte, path,
  summary and receipt evidence independently, but cannot establish
  visual equivalence without rerendering. External text-to-path conversion
  and render-validated compression now provide immutable canonical ZIPs,
  reports and receipts. The [matched-input processor comparison](../docs/testing.md#p57-matched-input-symbol-processor-parity)
  passed; [candidate preparation](#external-processed-symbol-publication-candidates)
  consumes that handoff without running graphical processors. The
  [accepted cutover](../docs/testing.md#p57-accepted-symbol-publication-cutover)
  completed artwork, browser and hosting review.

The *format* and verification contract stay owned by InfinityDB's
snapshot-provenance module. An extracted producer must emit compatible
bytes/fields and pass consumer-side conformance tests without importing
InfinityDB at runtime. No source downloader, network access or external
Git checkout is required for `infinity-db build`, `serve` or Docker
packaging. Raw third-party files remain untracked and separately
licensed; this handoff does not grant redistribution permission.

## Symbol build lifecycle

This file owns the current acquisition/build-state and publication lifecycle for symbol artifacts.
[`docs/architecture.md`](../docs/architecture.md) defines only the subsystem boundary, while
[`docs/data-model.md`](../docs/data-model.md) defines runtime identity/persistence semantics.
Implementation details remain in the symbol tooling, and unfinished lifecycle work belongs in
[`docs/TODO.md`](../docs/TODO.md).

### External processed symbol publication candidates

**Project domain:** Data processing

`python -m tools.prepare_symbol_publication` prepares an offline candidate from
the external producer's v1 processing handoff. It uses InfinityDB's semantic mapper,
rederiving authoritative Army references and approved
source/override lookups from the selected Army snapshot and maintained inputs.
It requires neither the external Python package nor installed renderers,
converters or fonts.

```powershell
python -m tools.prepare_symbol_publication --source-plan SOURCE_PLAN.json --override-lookups LOOKUPS.json --army "JSON YYYYMMDD-HHMMSS.zip" --army-manifest ARMY_MANIFEST.json --raw-archive "SYMBOLS YYYYMMDD-HHMMSS.zip" --effective-archive "EFFECTIVE-SYMBOLS YYYYMMDD-HHMMSS.zip" --stage-reports STAGE_REPORTS --processed-root PROCESSED_OUTPUT --font-aliases font-aliases.json --output local/symbol-candidate
```

Select actual immutable paths. Each raw/effective ZIP's same-directory `.json`
manifest and `.raw-report.json` or `.effective-report.json` companion must be
present. `--stage-reports` selects the preflight/font/duplicate receipts and
reports, with duplicate CSVs under `duplicates/`. `--processed-root` selects
`CANONICAL.zip`, `COMPRESSED.zip`, both final stage receipts and their conversion
and compression CSV/JSON reports. `--font-aliases` must select the exact bytes
pinned by the producer, even when another JSON file has equivalent content.

For a standalone check of the processed handoff, select its seven actual files:

```powershell
.\.venv\Scripts\python.exe -m tools.verify_processed_symbol_handoff `
  --canonical-archive CANONICAL.zip --conversion-receipt CONVERSION-STATE.json `
  --compressed-archive COMPRESSED.zip --compression-receipt COMPRESSION-STATE.json `
  --compression-report COMPRESSION-REPORT.csv --candidates-report CANDIDATES.csv `
  --run-report COMPRESSION-RUN.json
```

This check does not rerender artwork or approve a publication. Candidate
preparation invokes it alongside the other source and stage checks.

The consumer independently verifies raw/effective provenance and override
decisions, passed preflight/font/duplicate evidence, source-to-canonical
identity, conversion input hashes and successful CSV coverage, and compressed
member hashes/structure. It joins each stage to the same immutable source and
checks that all selected inputs remain unchanged during preparation.
Canonical and publication paths use the existing Unit/Peripheral ownership,
profile identity and collision rules; raw source IDs never invent a new owner.

The destination must be new. It contains `static/`, the current v2
`symbol-publication.json` and `candidate-evidence.json` with input hashes and
the publication-manifest hash. Validation or mapping failure installs no
candidate; a failed installation rolls back its new directory. Existing output
is never replaced. Input archives, tracked static assets and runtime databases
remain unchanged.

A prepared candidate is available for artwork, URL/mapping, browser and hosting
review. It does not approve graphical changes against the tracked publication,
promote a release or rebuild embedded mappings.
The normal build/serve/Docker path continues using the tracked publication.

### Offline publication artwork review

**Project domains:** Data processing, Project infrastructure

`tools.build_symbol_artwork_review` compares explicitly selected current and
candidate publications without processing or promoting assets. First record
the expected SHA-256 values of the two selected v2 manifests from trusted
evidence. Computing a hash alone does not establish approval or provenance.
Replace the placeholders below with the selected paths and hashes; use a fresh
run directory under ignored `local/`:

```powershell
.\.venv\Scripts\python.exe -m tools.build_symbol_artwork_review --write-comparison `
  --comparison local\validation\symbols\publication\RUN-ID\comparison.json `
  --current-manifest CURRENT-MANIFEST.json --manifest CANDIDATE-MANIFEST.json `
  --expected-current-sha256 CURRENT_SHA256 --expected-candidate-sha256 CANDIDATE_SHA256

.\.venv\Scripts\python.exe -m tools.build_symbol_artwork_review `
  --comparison local\validation\symbols\publication\RUN-ID\comparison.json `
  --current CURRENT-STATIC --current-manifest CURRENT-MANIFEST.json `
  --candidate CANDIDATE-STATIC --manifest CANDIDATE-MANIFEST.json `
  --candidate-evidence CANDIDATE-EVIDENCE.json `
  --output local\validation\symbols\publication\RUN-ID\review.html
```

Comparison generation verifies both manifest formats and expected hashes and
writes a deterministic inventory of changed, added and removed paths. Review
generation checks that inventory against the same manifests, verifies each
embedded changed SVG and each removed SVG against its manifest, and rejects
unsafe paths, malformed SVGs, drift or existing output files. The optional
candidate evidence must bind to the selected candidate manifest; its recorded
input details are displayed, but the review does not rerun the handoff receipt
chain. `--provenance` may select a matching classification report; its pins
must include the same comparison, manifests and candidate evidence. The review
checks report format, coverage, asset hashes, cause values and summary; it does
not reopen or authenticate the attribution inputs. Establish the report's
provenance independently. The retired P5-specific audit is not a general
classifier for future external-only publications.

The self-contained page provides side-by-side/overlay views and filters for
changed artwork. Added paths are listed, not visually reviewed. Removed URLs
remain unresolved compatibility requirements even if their source identities
map elsewhere. Export decisions before closing: browser storage is not
automatic. Imports require the exact input fingerprint and replace the
decision set. Without independently verified provenance, classifications are
reviewer annotations, not established causes. The review does not accept
artwork, verify all unchanged/added asset bytes or approve semantic mappings;
use the candidate, compatibility and publication checks separately.
Retain the comparison, page, decision export and selected evidence for the
review's lifetime. The [P5 classification evidence](../docs/testing.md#p57-override-provenance-classification)
describes the older, legacy-input-specific audit and its limitations.

### Accepted external symbol publication promotion

**Project domains:** Data processing, Project infrastructure

`python -m tools.promote_symbol_publication` consumes an explicitly accepted
candidate and the same `SymbolPublicationHandoff` file selections used to prepare
it. The promotion input JSON uses
`format: "InfinityDB symbol publication promotion inputs"`, `formatVersion: 1`,
the eight handoff fields (`source_plan`, `override_lookups`, `army`,
`army_manifest`, `raw_archive`, `effective_archive`, `stage_reports`,
`processed_root`) and `font_aliases`, each holding a local path. Relative paths
resolve from the working directory. Expected current and candidate manifest
SHA-256 values pin the replacement base and approved input.

The operation verifies the complete candidate asset inventory, reruns the existing
raw/effective/processed receipt verification and semantic mapping without any
graphical processors, and requires byte-identical candidate manifest/evidence.
It then copies approved compressed artwork and applies
`config/symbols/publication-compatibility-aliases.json`. Alias paths must be new,
portable published SVG paths pointing directly to an existing canonical target.
Aliases copy its exact bytes and hash; source/canonical/browser mapping keys are
unchanged. The v2 manifest's `compatibilityAliases` records the alias-to-target
map, and its published inventory/byte totals include those files. Startup's
embedded asset inventory therefore verifies compatibility URLs too.

The accepted P5 publication has **807 canonical SVGs / 808 published URLs**:
807 are browser-referenced and one is the former Seed Soldier URL,
`units/combined-army/512-shasvastii-seed-soldiers--1-2.svg`, backed by
`units/combined-army/512-shasvastii-seed-soldiers.svg`. A compatibility URL is
an additional physical publication file, not a new source identity.

Stop checkout serving before promotion. The operation requires a fresh transaction
directory under ignored `local/`. It retains verified previous bytes, the incoming
publication and a persistent journal before replacing the generated category
directories and manifest. Caught installation/validation failures, including
keyboard interruption, restore the previous publication. For a killed process
or interrupted rollback, use `--recover --transaction <same-directory>` before
serving; recovery verifies backups and refuses unrelated destination drift.
Retain the transaction until acceptance is complete. It is private operational
evidence, not a runtime input. A completed transaction is not an implicit rollback
request.

```powershell
.\.venv\Scripts\python.exe -m tools.promote_symbol_publication `
  --candidate CANDIDATE-DIRECTORY --inputs PROMOTION-INPUTS.json `
  --transaction local\operations\symbols\RUN-ID `
  --expected-current-sha256 CURRENT_SHA256 --expected-candidate-sha256 CANDIDATE_SHA256
```

Promotion replaces graphical publication only. Rebuild the **complete three-file**
Army/Rules/ITS set using the accepted manifest, validate embedded hashes/mappings
and deployment assets, then resume serving. Do not patch only the Army SQLite
rows or serve a mixed database/publication set. The
[P5 cutover evidence](../docs/testing.md#p57-accepted-symbol-publication-cutover)
records the dated acceptance; hosted/release gates remain separate.
Acquisition, overrides, font conversion, duplicate detection and compression
are producer-owned; InfinityDB retains source planning, independent handoff
verification, semantic mapping and publication promotion.

Raw Army data, generated databases, PDF documents, wiki snapshots, and Corvus
Belli graphical assets are not covered by InfinityDB's MIT License. Corvus Belli
has explicitly permitted redistribution of the processed graphical publication used by this
non-commercial project. By project policy, the generated runtime databases are also distributed
only as part of the non-commercial InfinityDB application/release and remain outside the MIT
License. The tracked `data/generated/army.db` and `rules_n5.db` are therefore release artifacts,
while raw Army/wiki/PDF/source-symbol archives remain separate local provenance inputs. Review the
repository's
[third-party notices](../THIRD_PARTY_NOTICES.md) for the full boundary.
