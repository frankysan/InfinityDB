# Data directories

- `raw/` — downloaded Corvus Belli Army JSON files or ZIP archives. Ignored by Git.
- `generated/` — generated `master.json`, normalized data, validation reports, and later database files. Ignored by Git.

Keeping raw and generated data outside source control prevents large snapshots from obscuring code changes.
