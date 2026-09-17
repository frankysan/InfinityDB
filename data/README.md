# Data directories

InfinityDB separates external inputs, human-reviewed material, generated
provenance/state, and build outputs.

## Current paths and behavior

- `raw/` — immutable downloaded Corvus Belli Army snapshot archives. Army
  acquisition writes `JSON YYYYMMDD-HHMMSS.zip`; symbol acquisition uses the
  `raw/symbols/` subtree for `SYMBOLS YYYYMMDD-HHMMSS.zip`. Ignored by Git.
- `wiki/` — local wiki research material. The current downloader persists
  immutable `WIKI YYYYMMDD-HHMMSS.zip` snapshots here. Ignored by Git.
- `pdf/` — local rules/FAQ/ITS research documents. Ignored by Git.
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

PDFs and wiki snapshots are research sources, not Army-pipeline inputs. Current
curated-v2 PDF record citations retain source version and printed-page
provenance. Current wiki record citations retain a snapshot-local path and
snapshot date. The checked-in rules collection still contains legacy wiki
provenance from the earlier unpacked mirror; do not silently relabel it as an
exact timestamped ZIP snapshot.

## Snapshot provenance contract

Army, wiki, and symbol downloaders write version-1 `InfinityDB snapshot
provenance` documents under `manifests/snapshots/`. The manifest filename
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
used by the current symbol downloader. This is acquisition provenance only; it
is not the later planned `army-symbol-build.json` processing manifest.

The human annotation contract is documented in
[`curated/snapshot-notes/README.md`](curated/snapshot-notes/README.md). Snapshot
notes are keyed to the immutable snapshot SHA-256 rather than to an archive
filename and are not application/runtime inputs.

## Remaining design direction

Exact timestamped archive/hash provenance for legacy wiki-derived curated data
will be addressed when the wiki downloader/packager and curated provenance
contract are rewritten together. Other build-specific generated manifests, such
as the planned Army-symbol build manifest, may live under `manifests/` as those
pipelines are implemented.

Raw Army data, generated databases, PDF documents, wiki snapshots, and Corvus
Belli graphical assets are not automatically covered by InfinityDB's MIT
License. Review the repository's [third-party notices](../THIRD_PARTY_NOTICES.md)
before redistributing any snapshot or derived artifact that contains them.
