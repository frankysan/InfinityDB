# Data directories

InfinityDB separates external inputs, human-reviewed material, generated
provenance/state, and build outputs.

## Current paths and behavior

- `raw/` — immutable downloaded Corvus Belli Army snapshot archives. Army
  acquisition writes `JSON YYYYMMDD-HHMMSS.zip`; symbol acquisition uses the
  `raw/symbols/` subtree for `SYMBOLS YYYYMMDD-HHMMSS.zip`. Ignored by Git.
- `wiki/` — local wiki research material. The current downloader persists
  immutable `WIKI-<language> YYYYMMDD-HHMMSS.zip` snapshots here. English (`en`)
  is the downloader default; Spanish (`es`) is an explicit alternative. Ignored
  by Git.
- `pdf/` — local rules/FAQ/ITS research documents. Ignored by Git.
- `work/wiki/` — local wiki crawl work. Successful acquisitions remove their
  work directory after publishing the immutable archive and provenance;
  incomplete/error runs preserve downloaded work here for inspection. Ignored
  by Git.
- `work/symbols/` — rebuildable loose symbol work trees keyed to the immutable
  `SYMBOLS ...zip` identity. The orchestrator verifies the raw archive and every
  member hash before replacing this derived work tree. Ignored by Git.
- `reports/symbols/` — generated symbol-processing reports. The current
  `svg-preflight.json` records parse/text/font-declaration findings and is bound
  back into `army-symbol-build.json` by SHA-256. Ignored by Git.
- `manifests/snapshots/` — downloader-generated snapshot provenance. Each JSON
  record is labeled from the archive filename, bound to its immutable SHA-256,
  and records the snapshot type, archive label/path when project-relative,
  acquisition time, source URL,
  document count, optional language, and optional input-artifact provenance.
  Ignored by Git, excluded from Docker build context, and outside Python package
  data.
- `curated/rules/` — source-controlled, human-reviewed rules-reference
  collections consumed by `infinity-db build-rules`.
- `curated/snapshot-notes/` — source-controlled, human-authored descriptions,
  comparison targets, and notable-change notes bound to immutable snapshots by
  SHA-256. Acquisition tools never modify this subtree.
- `generated/` — generated `master.json`, normalized data, validation reports,
  the browser-facing `infinity.db`, development-only `infinity.raw.db`, and the
  separate curated-rules `rules.db`. Ignored by Git.

Keeping raw inputs, generated provenance, and generated databases outside source
control prevents large or machine-local snapshot state from obscuring code
changes. Generated snapshot manifests are local provenance records rather than
maintained project knowledge. They are retained until explicitly removed; the
acquisition tools do not automatically prune either archives or manifests.

InfinityDB 0.5.1 treats generated database data as replaceable: builds validate
new frontend and raw-archive snapshots before atomically replacing both
generated database files.

PDFs and wiki snapshots are research sources, not Army-pipeline inputs. The
curated-v3 rules contract records the local reviewed artifact plus its upstream
source URL. PDF citations use printed pages. Archived wiki sources bind to an
exact timestamped ZIP/hash and citations use archive members; exact pinned wiki
revisions remain URL-backed sources.

## Snapshot provenance contract

Army, wiki, and symbol downloaders write version-1 `InfinityDB snapshot
provenance` documents under `manifests/snapshots/`. Wiki acquisition is
fail-closed for required content: if any required eligible URL discovered during
the crawl cannot be fetched, the run reports the failed URLs, publishes neither
a `WIKI-<language> ...zip` archive nor snapshot provenance, and preserves the
partial crawl under `work/wiki/`. Optional site chrome/project links that are not
part of the mirrored content contract—currently `/favicon.ico` and pages in the
`Infinity:` MediaWiki project namespace—are reported as ignored rather than
failures. Wiki crawls are language-scoped: English is the default, Spanish is
selected explicitly, same-language pages are mirrored, and cross-language
assets are included only when an included page references them. Only a complete
successful crawl becomes an immutable wiki snapshot.

The manifest filename
mirrors the archive label with a `.json` suffix, while the archive's lowercase
SHA-256 digest is stored inside the document and is the authoritative identity
that can be revalidated against the archive. Generated JSON serialization is
deterministic.

Persistent paths are stored only when the file is inside the project root, and
then use portable project-relative POSIX form. Machine-specific absolute paths
are never written. A repeated attempt to write identical provenance for the same manifest label
is idempotent; conflicting provenance for that label fails instead of rewriting
the record. Byte-identical archives acquired under different labels may have
separate manifests with the same authoritative SHA-256.

Symbol snapshot provenance also records the hash of the Army source artifact
used by symbol acquisition. `tools/build_symbols.py` verifies the corresponding
Army snapshot provenance before discovery and keeps that exact archive pinned
through raw symbol acquisition. Acquisition writes version-2
`army-symbol-build.json`, persisting the Army archive identity together with
source URL, language, acquisition timestamp, source-document count, and observed
source revisions. After verified extraction and SVG structural preflight, the
orchestrator promotes the same build state to version 3 and records the preflight
status, summary, and exact generated report artifact. Installed-font audit then
promotes the state to version 4 and records its environment-specific report plus
the exact tracked `config/symbols/font-aliases.json` artifact. Version-2 state
remains valid for standalone acquisition/prior symbol caches, and version-3 state
remains valid as completed structural preflight awaiting font audit.

The human annotation contract is documented in
[`curated/snapshot-notes/README.md`](curated/snapshot-notes/README.md). Snapshot
notes are keyed to the immutable snapshot SHA-256 rather than to an archive
filename and are not application/runtime inputs.

Army JSON `version` values are per-document Corvus Belli source revisions, not
InfinityDB snapshot versions. Their evidence-backed interpretation and the
required distinction between source revision and snapshot acquisition date are
documented in [`docs/data-model.md`](../docs/data-model.md#army-source-revision-interpretation).

## Remaining design direction

The symbol orchestrator currently stops after verified raw extraction, structural
SVG preflight, and installed-font audit. Later stages will consume the same
pinned Army/SYMBOLS
build state for installed-font/alias resolution, deduplication, text conversion,
compression, publication, generated browser mappings, and final validation.

Raw Army data, generated databases, PDF documents, wiki snapshots, and Corvus
Belli graphical assets are not automatically covered by InfinityDB's MIT
License. Review the repository's [third-party notices](../THIRD_PARTY_NOTICES.md)
before redistributing any snapshot or derived artifact that contains them.
