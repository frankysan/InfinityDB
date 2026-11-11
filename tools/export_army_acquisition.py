"""Export a standalone Army API producer without fetching source data.

This one-time P5.4 migration tool never modifies the original downloader.
The output is a Git-ready source tree plus optional reproducible transfer ZIP.
"""

from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_PYPROJECT = """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "infinity-army-acquisition"
version = "0.1.0"
description = "Standalone Infinity Army JSON snapshot acquisition"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
test = ["pytest>=8"]

[project.scripts]
infinity-army-snapshot = "infinity_army_acquisition.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
"""

_README = """# Infinity Army acquisition

Standalone downloader for the official Infinity Army API. This
repository owns only source acquisition and source-format acceptance.
Army normalization, merging, rules and database publication remain
in the separate InfinityDB repository.

No downloaded source data or graphical assets are stored in this
repository. The MIT source-code license does not cover third-party
Army API data.

## Installation and offline tests

Python 3.11 or newer; no external runtime dependencies.

    python -m pip install -e ".[test]"
    python -m pytest -q

Tests use mock API responses and local temporary ZIPs only.

## Manual acquisition

    infinity-army-snapshot data/raw --language en --manifest-dir data/manifests/snapshots

The downloader validates each endpoint and repeats every request.
Different response bytes between passes fail closed; no torn snapshot
ZIP or manifest is published. It creates a timestamped JSON ZIP and
version-3 snapshot provenance with exact archive and logical-content
hashes. Unknown source-revision date formats are rejected.

For use by InfinityDB, transfer the immutable ZIP and its matching
manifest. InfinityDB validates the pair offline with
tools.army_snapshot_source.resolve_army_snapshot. The normal
InfinityDB build/serve/Docker workflows do not install this package.

Only source-facing acceptance is copied here; importing or running
InfinityDB's data model and normalization is not required.
"""

_GITIGNORE = """__pycache__/
.pytest_cache/
.venv/
*.egg-info/
build/
dist/
data/
local/
"""

_ATTRIBUTES = """# Canonical source and documentation line endings.
* text=auto
*.py text eol=lf
*.md text eol=lf
*.toml text eol=lf
*.yml text eol=lf
.gitignore text eol=lf
.gitattributes text eol=lf
LICENSE text eol=lf
"""

_WORKFLOW = """name: Offline tests

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  pytest:
    name: DOLLAR{{ matrix.os }} / Python 3.11
    runs-on: DOLLAR{{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install standalone acquisition
        run: python -m pip install -e ".[test]"
      - name: Check dependencies
        run: python -m pip check
      - name: Run offline producer tests
        run: python -m pytest -q
""".replace("DOLLAR", chr(36))


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a)
    if text.find(start, a + len(start)) >= 0:
        raise ValueError(f"Ambiguous extraction marker: {start}")
    return text[a:b]


def _replace(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"Source contract changed: {label}")
    return text.replace(old, new)


def _producer_cli() -> str:
    source = _read("tools/download_army_json.py")
    old_imports = _between(
        source, "from infinity_army_data.merge import decode_document",
        "API_BASE_URL = ",
    )
    new_imports = (
        "from infinity_army_acquisition.metadata import decode_metadata\n"
        "from infinity_army_acquisition.source_document import decode_document\n"
        "from infinity_army_acquisition.source_version import latest_army_source_change_date\n"
        "from infinity_army_acquisition.snapshot_archive import create_timestamped_archive\n"
        "from infinity_army_acquisition.snapshot_provenance import write_snapshot_manifest\n\n"
    )
    source = _replace(source, old_imports, new_imports, "Army imports")
    source = _replace(
        source, "from typing import Any\n", "from typing import Any, NamedTuple\n",
        "snapshot result type",
    )
    types = _between(
        _read("tools/army_snapshot_source.py"),
        "class ApiDownloadError(", "def snapshot_source_revision_counts(",
    )
    return _replace(
        source, "\ndef _request(", "\n" + types + "def _request(",
        "Army source result and error",
    )


def _source_metadata() -> str:
    source = _read("src/infinity_army_data/metadata.py")
    header = source[:source.index("def load_metadata(")].rstrip()
    validation = _between(
        source, "def validate_metadata_envelope(", "def normalize_metadata(",
    ).rstrip()
    # Strict source-facing decoder only: no normalization or table publication.
    return header + "\n\n\n" + validation + "\n"


def _source_document() -> str:
    decoder = _between(
        _read("src/infinity_army_data/merge.py"),
        "def decode_document(", "def make_source(",
    ).rstrip()
    return (
        '"""Source-document shape validation, without Army merging."""\n\n'
        "from __future__ import annotations\n\n"
        "import json\nfrom typing import Any\n\n\n" + decoder + "\n"
    )


def _api_tests() -> str:
    source = _replace(
        _read("tests/test_api.py"), "import runpy\n", "", "API test import",
    )
    header = _between(source, 'DOWNLOADER = runpy.run_path(', "\n\nclass Response:")
    replacement = (
        "from infinity_army_acquisition import cli as module\n\n"
        "ApiDownloadError = module.ApiDownloadError\n"
        "download_snapshot = module.download_snapshot\n"
        "archive_snapshot = module.archive_snapshot"
    )
    return _replace(source, header, replacement, "API downloader test setup")


def _downloader_tests() -> str:
    source = _read("tests/test_download_army_json.py")
    start = _between(
        source, "import importlib.util", "def test_filename_slugifies_bad_faction_names(",
    )
    replacement = (
        "import json\n\n"
        "from infinity_army_acquisition import cli as module\n\n\n"
        "def load_module():\n"
        "    return module\n\n\n"
    )
    source = _replace(source, start, replacement, "downloader fixture")
    return _replace(
        source,
        "from infinity_db.snapshot_provenance import load_snapshot_manifest",
        "from infinity_army_acquisition.snapshot_provenance import load_snapshot_manifest",
        "downloader provenance fixture",
    )


def _source_tests(name: str) -> str:
    source = _read("tests/" + name)
    if name == "test_snapshot_provenance.py":
        # This test validates maintained InfinityDB-only source-note files.
        source = _replace(
            source,
            "def test_checked_in_snapshot_notes_are_valid() -> None:\n"
            "    root = Path(__file__).parents[1]\n\n"
            '    validate_snapshot_note_directory(root / "data" / '
            '"curated" / "snapshot-notes")\n\n\n',
            "",
            "in-repository-only snapshot notes",
        )
    return (
        source.replace(
            "from infinity_db.snapshot_provenance import",
            "from infinity_army_acquisition.snapshot_provenance import",
        ).replace(
            "from tools.snapshot_archive import",
            "from infinity_army_acquisition.snapshot_archive import",
        ).replace(
            "from infinity_army_data.source_version import",
            "from infinity_army_acquisition.source_version import",
        )
    )


def export_producer(destination: Path) -> tuple[Path, ...]:
    """Write one new, isolated producer tree without overwriting anything."""
    destination = destination.resolve()
    staging = destination.with_name(destination.name + ".staging")
    if destination.exists() or staging.exists():
        raise FileExistsError(f"Destination or staging already exists: {destination}")

    files = {
        "src/infinity_army_acquisition/__init__.py":
            '"""Standalone Army source acquisition."""\n',
        "src/infinity_army_acquisition/cli.py": _producer_cli(),
        "src/infinity_army_acquisition/metadata.py": _source_metadata(),
        "src/infinity_army_acquisition/source_document.py": _source_document(),
        "src/infinity_army_acquisition/source_version.py":
            _read("src/infinity_army_data/source_version.py"),
        "src/infinity_army_acquisition/snapshot_archive.py":
            _read("tools/snapshot_archive.py"),
        "src/infinity_army_acquisition/snapshot_provenance.py":
            _read("src/infinity_db/snapshot_provenance.py"),
        "tests/test_api.py": _api_tests(),
        "tests/test_downloader.py": _downloader_tests(),
        "tests/test_snapshot_provenance.py":
            _source_tests("test_snapshot_provenance.py"),
        "tests/test_snapshot_archive.py":
            _source_tests("test_snapshot_archive.py"),
        "tests/test_source_version.py":
            _source_tests("test_source_version.py"),
        ".github/workflows/tests.yml": _WORKFLOW,
        ".gitattributes": _ATTRIBUTES,
        ".gitignore": _GITIGNORE,
        "README.md": _README,
        "LICENSE": _read("LICENSE"),
        "pyproject.toml": _PYPROJECT,
    }
    for name, source in files.items():
        if name.endswith(".py") and any(
            part in source for part in (
                "from infinity_db", "from infinity_army_data", "from tools.",
            )
        ):
            raise ValueError(f"An InfinityDB import escaped extraction: {name}")

    staging.parent.mkdir(parents=True, exist_ok=True)
    staging.mkdir()
    try:
        for name, source in sorted(files.items()):
            path = staging / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source, encoding="utf-8", newline="\n")
        staging.rename(destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return tuple(destination / name for name in sorted(files))


def archive_producer(destination: Path, archive: Path) -> Path:
    """Create a byte-reproducible source-only transfer ZIP."""
    destination = destination.resolve()
    if archive.exists():
        raise FileExistsError(f"Source transfer ZIP already exists: {archive}")
    if not (destination / "pyproject.toml").is_file():
        raise ValueError("Exported producer is missing pyproject.toml")
    archive.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(archive, "x") as output:
            for path in sorted(p for p in destination.rglob("*") if p.is_file()):
                info = zipfile.ZipInfo(
                    path.relative_to(destination).as_posix(),
                    date_time=(1980, 1, 1, 0, 0, 0),
                )
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                output.writestr(
                    info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED,
                )
    except BaseException:
        archive.unlink(missing_ok=True)
        raise
    return archive


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args(argv)
    paths = export_producer(args.output)
    if args.archive:
        print(f"Standalone source ZIP -> {archive_producer(args.output, args.archive)}")
    print(f"Standalone Army producer -> {args.output} ({len(paths)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
