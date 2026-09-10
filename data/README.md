# Data directories

- `raw/` — downloaded Corvus Belli Army JSON files or ZIP archives, plus the optional
  Army API `metadata.json` snapshot. Ignored by Git.
- `generated/` — generated `master.json`, normalized data, validation reports, and `infinity.db`. Ignored by Git.

Keeping raw and generated data outside source control prevents large snapshots from obscuring code changes.
