@C:\Users\Franky\.codex\RTK.md

## Python environment

Use the project virtual environment for all Python tooling. Do not invoke bare
`python`, `pip`, `pytest`, or `ruff`.

Run commands through RTK with the virtual-environment interpreter, for example:

- `rtk .\.venv\Scripts\python.exe -m pytest`
- `rtk .\.venv\Scripts\python.exe -m ruff check src tests`
- `rtk .\.venv\Scripts\python.exe -m pip install ...`

## Local rules reference

User-supplied PDFs in `data/` are potential research sources for rules-aware
features, data review, and TODO discovery. They are not build inputs and are
ignored by Git:

- `eng-n5-update-5-3.pdf` — N5 core rules v5.3
- `eng-faqs-n5-v0-1.pdf` — N5 FAQ v0.1
- `its-18-en.pdf` — current ITS Season 18 rules
- `its-rules-season-17-en-v1.0.2.pdf` — archived ITS Season 17 rules

Keep facts derived from these documents versioned and cited by printed page.
Do not bulk-extract or serve their copyrighted text/artwork. Treat official
Infinity Army data and live official publications as authoritative where they
conflict with an archived local document.
