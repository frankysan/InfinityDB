# Data directories

InfinityDB separates external inputs, human-reviewed material, generated
provenance/state, and build outputs. This document distinguishes paths that are
used today from accepted but unimplemented data-path design.

## Current paths and behavior

- `raw/` — immutable downloaded Corvus Belli Army snapshot archives. Army
  acquisition writes `JSON YYYYMMDD-HHMMSS.zip`; symbol acquisition uses the
  `raw/symbols/` subtree for `SYMBOLS YYYYMMDD-HHMMSS.zip`. Ignored by Git.
- `wiki/` — local wiki research material. The current downloader persists
  immutable `WIKI YYYYMMDD-HHMMSS.zip` snapshots here. Ignored by Git.
- `pdf/` — local rules/FAQ/ITS research documents. Ignored by Git.
- `curated/rules/` — source-controlled, human-reviewed rules-reference
  collections consumed by `infinity-db build-rules`.
- `generated/` — generated `master.json`, normalized data, validation reports,
  the browser-facing `infinity.db`, development-only `infinity.raw.db`, and the
  separate curated-rules `rules.db`. Ignored by Git.

Keeping raw and generated data outside source control prevents large snapshots
from obscuring code changes. InfinityDB 0.5.1 treats generated database data as
replaceable: builds validate new frontend and raw-archive snapshots before
atomically replacing both generated database files.

PDFs and wiki snapshots are research sources, not Army-pipeline inputs. Current
curated-v2 PDF record citations retain source version and printed-page
provenance. Current wiki record citations retain a snapshot-local path and
snapshot date. The checked-in rules collection still contains legacy wiki
provenance from the earlier unpacked mirror; do not silently relabel it as an
exact timestamped ZIP snapshot.

## Design direction — not yet implemented

- `manifests/snapshots/` will hold downloader-generated snapshot provenance and
  identify immutable Army, wiki, or symbol archives by SHA-256 together with
  acquisition/source metadata.
- `curated/snapshot-notes/` will hold source-controlled, human-written snapshot
  descriptions, comparison targets, and notable-change notes, also bound to the
  corresponding immutable snapshot by SHA-256. These notes will not be
  rules-database inputs.
- Other build-specific generated manifests may live under `manifests/` as
  manifest-backed pipelines are implemented.

No current downloader writes `data/manifests/snapshots/`, and no current build
or runtime consumes `data/curated/snapshot-notes/`. Version-control, ignore, and
packaging policy for generated manifests is therefore not yet an implemented
repository contract and will be finalized with the first manifest writer.

Exact timestamped archive/hash provenance for legacy wiki-derived curated data
will be addressed when the wiki downloader/packager and curated provenance
contract are rewritten together.

Raw Army data, generated databases, PDF documents, wiki snapshots, and Corvus
Belli graphical assets are not automatically covered by InfinityDB's MIT
License. Review the repository's [third-party notices](../THIRD_PARTY_NOTICES.md)
before redistributing any snapshot or derived artifact that contains them.
