@C:\Users\Franky\.codex\RTK.md

## Python environment

Use the project virtual environment for all Python tooling. Do not invoke bare
`python`, `pip`, `pytest`, or `ruff`.

Run commands through RTK with the virtual-environment interpreter, for example:

- `rtk .\.venv\Scripts\python.exe -m pytest`
- `rtk .\.venv\Scripts\python.exe -m ruff check src tests`
- `rtk .\.venv\Scripts\python.exe -m pip install ...`
