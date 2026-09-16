# Data directories

InfinityDB keeps external inputs, generated provenance, human-reviewed material,
and build outputs separate:

- `raw/` — immutable downloaded Corvus Belli Army snapshot archives. Army
  acquisition writes `JSON YYYYMMDD-HHMMSS.zip`; symbol acquisition uses the
  `raw/symbols/` subtree for `SYMBOLS YYYYMMDD-HHMMSS.zip`. Ignored by Git.
- `wiki/` — immutable local wiki mirror snapshots named
  `WIKI YYYYMMDD-HHMMSS.zip`. These are research inputs, not application data.
  Ignored by Git.
- `manifests/` — generated provenance and build state. Snapshot provenance
  belongs under `manifests/snapshots/` and identifies immutable Army, wiki, or
  symbol archives by SHA-256 together with acquisition/source metadata. These
  records are generated state rather than hand-authored project knowledge.
- `curated/` — source-controlled, human-reviewed information derived from
  external sources. `curated/rules/` contains the validated rules-reference
  collections consumed by `infinity-db build-rules`; other curated subtrees are
  not rules-database inputs. Human-written snapshot descriptions and notable
  changes belong under `curated/snapshot-notes/` and bind to the corresponding
  snapshot by SHA-256.
- `generated/` — generated `master.json`, normalized data, validation reports,
  the browser-facing `infinity.db`, development-only `infinity.raw.db`, and the
  separate curated-rules `rules.db`. The rules database has an independent
  update lifecycle and is built only from `data/curated/rules/`. Ignored by Git.

Keeping raw and generated data outside source control prevents large snapshots
from obscuring code changes. InfinityDB 0.5.1 treats generated database data as
replaceable: builds validate new frontend and raw-archive snapshots before
atomically replacing both generated database files.

PDFs and wiki snapshots are research sources, not Army-pipeline inputs. Facts
curated from PDFs must retain source version and printed-page provenance;
wiki-derived facts must retain exact snapshot identity and snapshot-local path
provenance. Do not merge either into Army JSON-derived artifacts.

Raw Army data, generated databases, PDF documents, wiki snapshots, and Corvus
Belli graphical assets are not automatically covered by InfinityDB's MIT
License. Review the repository's [third-party notices](../THIRD_PARTY_NOTICES.md)
before redistributing any snapshot or derived artifact that contains them.
