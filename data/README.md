# Data directories

- `raw/` — downloaded Corvus Belli Army JSON files or ZIP archives, plus the required
  Army API `metadata.json` snapshot. Ignored by Git.
- `generated/` — generated `master.json`, normalized data, validation reports,
  the browser-facing `infinity.db`, and development-only `infinity.raw.db`.
  Ignored by Git.

Keeping raw and generated data outside source control prevents large snapshots from obscuring code changes.
InfinityDB 0.4.0 treats generated data as replaceable: builds validate new
frontend and raw-archive snapshots before atomically replacing both generated
database files.
