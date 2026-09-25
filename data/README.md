# Data directories

**Project domains:** Acquisition, Data processing

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
  document count, optional language, and optional input-artifact provenance.
  Ignored by Git, excluded from Docker build context, and outside Python package
  data.
- `manifests/army-symbol-build.json` — generated current symbol-build state from
  acquisition version 2 through terminal publication version 8. It binds the
  pinned Army/SYMBOLS artifacts, stage reports/settings, canonical mapping, and
  publication artifacts. Ignored by Git.
- `curated/rules/` — source-controlled, human-reviewed rules-reference
  collections consumed by `infinity-db build-rules`.
- `curated/identities/` — source-controlled, reviewed source-derived identity and
  presentation relationships consumed by the relevant build/normalization stage.
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

Generated Army database data is replaceable. Builds create temporary frontend
and raw-archive siblings, validate both before publication, and replace each
destination atomically. The pair is not yet one atomic transaction: recovery
from interruption between the two replacements remains an explicit backlog item.

PDFs and wiki snapshots are research sources, not Army-pipeline inputs. The
curated-v3 rules contract records the local reviewed artifact plus its upstream
source URL. PDF citations use printed pages. Archived wiki sources bind to an
exact timestamped ZIP/hash and citations use archive members; exact pinned wiki
revisions remain URL-backed sources.

## Snapshot provenance contract

Army, wiki, and symbol downloaders write version-2 `InfinityDB snapshot
provenance` documents under `manifests/snapshots/`. Version-1 manifests remain
valid historical provenance and continue to verify their exact archive SHA-256.
Wiki acquisition is fail-closed for required content: if any required eligible
URL discovered during the crawl cannot be fetched, the run reports the failed
URLs, publishes neither a `WIKI-<language> ...zip` archive nor snapshot
provenance, and preserves the partial crawl under `work/wiki/`. Optional site
chrome/project links that are not part of the mirrored content contract—currently
`/favicon.ico` and pages in the `Infinity:` MediaWiki project namespace—are
reported as ignored rather than failures. Wiki crawls are language-scoped:
English is the default, Spanish is selected explicitly, same-language pages are
mirrored, and cross-language assets are included only when an included page
references them. Only a complete successful crawl becomes an immutable wiki
snapshot.

The manifest filename mirrors the archive label with a `.json` suffix. Version 2
stores two separate SHA-256 values:

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
8 binds the complete `symbol-inventory.json`, browser maps, publication report,
and final byte/count accounting; the inventory covers all published SVGs, not
only the subset currently referenced by the browser. Stage promotion is
forward-only. Failed-stage retry is explicit where supported; later passed states
are not silently rolled back to rerun an earlier helper. Loaders still accept
versions 2 through 8 as valid historical/intermediate state for compatibility.

The human annotation contract is documented in
[`curated/snapshot-notes/README.md`](curated/snapshot-notes/README.md). Snapshot
notes are not application/runtime inputs. Their current version-1 contract still
uses the exact archive SHA-256; migrating that separate curated contract to the
logical content identity can be done independently once the new snapshot identity
has been exercised on real acquisitions.

Army JSON `version` values are per-document Corvus Belli source revisions, not
InfinityDB snapshot versions. Their evidence-backed interpretation and the
required distinction between source revision and snapshot acquisition date are
documented in [`docs/data-model.md`](../docs/data-model.md#army-source-revision-interpretation).

## Symbol build lifecycle

The complete current symbol lifecycle, stage invariants, and publication contract
are documented in [`docs/architecture.md`](../docs/architecture.md) and
[`docs/data-model.md`](../docs/data-model.md). This file remains authoritative for
where local data classes live; it does not duplicate the complete processing
algorithm or backlog.

Raw Army data, generated databases, PDF documents, wiki snapshots, and Corvus
Belli graphical assets are not covered by InfinityDB's MIT License. Corvus Belli
has explicitly permitted InfinityDB to redistribute the processed graphical
publication used by this non-commercial project; raw Army/wiki/PDF/source-symbol
archives remain separate local/provenance inputs by project policy. Review the
repository's [third-party notices](../THIRD_PARTY_NOTICES.md) for the full boundary.
