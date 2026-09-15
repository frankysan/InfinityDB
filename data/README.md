# Data directories

- `raw/` — downloaded Corvus Belli Army JSON files or ZIP archives, plus the required
  Army API `metadata.json` snapshot. Ignored by Git.
- `curated/` — source-controlled, human-reviewed JSON intermediaries derived from
  developer-only PDF and wiki research. The application may ingest these files,
  but must never read `pdf/` or `wiki/` directly.
- `generated/` — generated `master.json`, normalized data, validation reports,
  the browser-facing `infinity.db`, development-only `infinity.raw.db`, and
  the separate curated-rules `rules.db`. The rules database has an independent
  update lifecycle and is built only from `data/curated/`. Ignored by Git.

Keeping raw and generated data outside source control prevents large snapshots from obscuring code changes.
InfinityDB 0.5.1 treats generated data as replaceable: builds validate new
frontend and raw-archive snapshots before atomically replacing both generated
database files.

PDFs and wiki snapshots in this directory are research sources, not Army-pipeline
inputs. Their curated facts must retain document version and printed-page
provenance in `curated/` and, later, in the separate rules database; do not merge
them into Army JSON-derived artifacts.

Raw Army data, generated databases, PDF documents, and wiki snapshots are not
automatically covered by InfinityDB's MIT License. Review the repository's
[third-party notices](../THIRD_PARTY_NOTICES.md) before redistributing any
snapshot or derived artifact that contains them.
