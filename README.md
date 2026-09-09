# Infinity Army Data

Python tooling for building a consistent dataset from Corvus Belli Infinity Army JSON files.

The project deliberately separates three concerns:

1. **Merge** — combine the raw faction/sectorial JSON files into a lossless `master.json`.
2. **Normalize** — turn the nested master data into relational-style tables while preserving army-specific rules.
3. **Export** — write the normalized tables to SQLite/PostgreSQL. This is the next development stage.

## Project layout

```text
infinity-army-data/
├─ src/infinity_army_data/
│  ├─ cli.py
│  ├─ merge.py
│  └─ normalize.py
├─ tests/
├─ data/
│  ├─ raw/          # ignored by Git
│  └─ generated/    # ignored by Git
├─ docs/
└─ .vscode/
```

## Setup on Windows / VS Code

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Then select `.venv` as the Python interpreter in VS Code if it is not selected automatically.

## Put the Army data in place

For example:

```text
data/raw/JSON 20260909.zip
```

Raw data is intentionally ignored by Git.

## Full pipeline

```powershell
infinity-army build "data/raw/JSON 20260909.zip" --compact
```

This creates:

```text
data/generated/master.json
data/generated/normalized.json
data/generated/normalized-validation.json
```

The build command performs both validation stages:

- reconstruct every source Army JSON object from `master.json` to prove the merge is lossless;
- validate normalized uniqueness and foreign-key relationships.

## Individual stages

```powershell
infinity-army merge "data/raw/JSON 20260909.zip" data/generated/master.json --compact
infinity-army normalize data/generated/master.json data/generated/normalized.json --compact
```

The package can also be run without installing the console entry point:

```powershell
python -m infinity_army_data build "data/raw/JSON 20260909.zip" --compact
```

## VS Code

The workspace includes:

- a default **Infinity: Build dataset** build task (`Ctrl+Shift+B`);
- a pytest task;
- a Ruff lint task;
- a debug configuration for the full build pipeline.

## Tests

```powershell
pytest
ruff check src tests
```

## Next stage

Add a `database/` or `export/` module implementing SQLite first, with SQL schema/migrations kept separate from the source parsing and normalization code.
