"""Stage the existing Wiki/Human Sphere acquisition code as a standalone producer.

This is a one-time P5.4 extraction aid. It leaves the current downloader in
place and writes only to a new destination. No network access is performed.
"""

from __future__ import annotations

import argparse
import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_OLD_IMPORTS = """from infinity_db.snapshot_provenance import write_snapshot_manifest

try:
    from tools.path_sanitization import (
        sanitize_path_component as _sanitize_path_component,
    )
    from tools.path_sanitization import (
        sanitize_relative_path,
    )
    from tools.snapshot_archive import create_timestamped_archive
except ImportError:  # pragma: no cover - direct script execution fallback
    from path_sanitization import (
        sanitize_path_component as _sanitize_path_component,
    )
    from path_sanitization import (
        sanitize_relative_path,
    )
    from snapshot_archive import create_timestamped_archive
"""

_NEW_IMPORTS = """from infinity_wiki_acquisition.path_sanitization import (
    sanitize_path_component as _sanitize_path_component,
)
from infinity_wiki_acquisition.path_sanitization import sanitize_relative_path
from infinity_wiki_acquisition.snapshot_archive import create_timestamped_archive
from infinity_wiki_acquisition.snapshot_provenance import write_snapshot_manifest
"""

_OLD_TEST_SETUP = """import importlib.util
import io
import os
import zipfile
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import Any

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "download_wiki_snapshot.py"

spec = importlib.util.spec_from_file_location("download_wiki_snapshot", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
"""

_NEW_TEST_SETUP = """import io
import os
import zipfile
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import Any

from infinity_wiki_acquisition import cli as module
"""

_PYPROJECT = """[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "infinity-wiki-acquisition"
version = "0.1.0"
description = "Standalone Infinity Wiki and Human Sphere snapshot acquisition"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
test = ["pytest>=8"]

[project.scripts]
infinity-wiki-snapshot = "infinity_wiki_acquisition.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
"""

_README = """# Infinity Wiki / Human Sphere acquisition

Standalone **source acquisition** for InfinityDB research. This repository
contains no downloaded source documents, game data or graphical assets.
Raw third-party materials remain outside its source license.

## Offline development

The code requires Python 3.11 or newer and uses only the standard library.
Install locally with `python -m pip install -e ".[test]"`, then run
`python -m pytest -q`. The tests mock network fetches and require no
local Wiki/Army/PDF archives.

## Explicit acquisition

Run from the desired working directory:

```powershell
infinity-wiki-snapshot --site infinity-wiki --language en
infinity-wiki-snapshot --site infinity-wiki --language es
infinity-wiki-snapshot --site human-sphere --language en
```

`--include-history` additionally archives MediaWiki revisions; `--resume-work`
uses a preserved incomplete crawl. Partial/failed crawls never publish a ZIP
or manifest. Archive acquisition is optional and never runs during an
InfinityDB build, serve or Docker deployment.

## Consumer contract

A complete acquisition exports an immutable `WIKI-en ...zip`,
`WIKI-es ...zip` or `HUMAN-SPHERE ...zip` and a matching v3
`InfinityDB snapshot provenance` JSON manifest. Copy the ZIP and JSON
to the consumer machine. Exact archive SHA-256 and logical
`snapshot.contentSha256` must match; the producer-relative path in the
manifest is informational. InfinityDB's snapshot-provenance reader verifies
the pair offline. Source ZIP members remain source evidence, not
authoritative current gameplay rules.

The Python provenance contract is copied from InfinityDB's current
`snapshot_provenance` implementation at extraction time, so conformance
is established against the consuming InfinityDB version rather than
requiring an `infinity_db` runtime import.

This standalone export is staged by the original InfinityDB repository's
P5.4 extraction tool; create a dedicated Git repository only after the
producer tests and consumer conformance checks are green.
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


def _replace_once(source: str, old: str, new: str, label: str) -> str:
    if source.count(old) != 1:
        raise ValueError(f"Cannot export {label}: source contract changed")
    return source.replace(old, new)


def _download_test_source() -> str:
    source = (ROOT / "tests/test_download_wiki_snapshot.py").read_text(
        encoding="utf-8",
    )
    source = _replace_once(source, _OLD_TEST_SETUP, _NEW_TEST_SETUP, "test setup")
    source = source.replace(
        "from infinity_db.snapshot_provenance import load_snapshot_manifest",
        "from infinity_wiki_acquisition.snapshot_provenance import load_snapshot_manifest",
    )
    for name in (
        "test_download_army_symbols_sanitizes_windows_invalid_names",
        "test_reorganize_symbols_slugifies_windows_invalid_names",
    ):
        pattern = rf"(?ms)^def {name}\(.*?(?=^def test_|\Z)"
        source, count = re.subn(pattern, "", source)
        if count != 1:
            raise ValueError(f"Cannot isolate Wiki-only test: {name}")
    return source


def _independent_test_source(filename: str) -> str:
    """Convert the existing Human Sphere/history fixtures to package imports."""
    source = (ROOT / "tests" / filename).read_text(encoding="utf-8")
    source = _replace_once(
        source, "import importlib.util\n", "", f"{filename} import",
    )
    start = source.index("MODULE_PATH = Path(__file__)")
    end = source.index("spec.loader.exec_module(module)", start)
    end += len("spec.loader.exec_module(module)")
    source = source[:start] + (
        "from infinity_wiki_acquisition import cli as module"
    ) + source[end:]
    return source.replace(
        "from infinity_db.snapshot_provenance import load_snapshot_manifest",
        "from infinity_wiki_acquisition.snapshot_provenance import load_snapshot_manifest",
    )


def export_producer(destination: Path) -> tuple[Path, ...]:
    """Create the isolated producer tree; never overwrite an existing path."""
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(f"Standalone producer destination already exists: {destination}")
    staging = destination.with_name(destination.name + ".staging")
    if staging.exists():
        raise FileExistsError(f"Standalone producer staging path already exists: {staging}")

    downloader = (ROOT / "tools/download_wiki_snapshot.py").read_text(
        encoding="utf-8",
    )
    downloader = _replace_once(
        downloader, _OLD_IMPORTS, _NEW_IMPORTS, "Wiki acquisition imports",
    )
    files: dict[str, str] = {
        "src/infinity_wiki_acquisition/__init__.py":
            '"""Offline-source-preserving Wiki snapshot acquisition."""\n',
        "src/infinity_wiki_acquisition/cli.py": downloader,
        "src/infinity_wiki_acquisition/path_sanitization.py":
            (ROOT / "tools/path_sanitization.py").read_text(encoding="utf-8"),
        "src/infinity_wiki_acquisition/snapshot_archive.py":
            (ROOT / "tools/snapshot_archive.py").read_text(encoding="utf-8"),
        "src/infinity_wiki_acquisition/snapshot_provenance.py":
            (ROOT / "src/infinity_db/snapshot_provenance.py").read_text(encoding="utf-8"),
        "tests/test_downloader.py": _download_test_source(),
        "tests/test_human_sphere.py": _independent_test_source(
            "test_download_human_sphere_snapshot.py",
        ),
        "tests/test_wiki_history.py": _independent_test_source(
            "test_download_wiki_history.py",
        ),
        "pyproject.toml": _PYPROJECT,
        "README.md": _README,
        ".gitignore": _GITIGNORE,
        "LICENSE": (ROOT / "LICENSE").read_text(encoding="utf-8"),
    }
    staging.parent.mkdir(parents=True, exist_ok=True)
    staging.mkdir()
    try:
        for name, content in sorted(files.items()):
            path = staging / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
        staging.rename(destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return tuple(destination / name for name in sorted(files))


def archive_producer(destination: Path, archive: Path) -> Path:
    """Create a reproducible transfer ZIP, without changing the source tree."""
    if archive.exists():
        raise FileExistsError(f"Standalone producer archive already exists: {archive}")
    destination = destination.resolve()
    if not (destination / "pyproject.toml").is_file():
        raise ValueError("Standalone producer has no pyproject.toml")
    archive.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(archive, "x") as output:
            for path in sorted(item for item in destination.rglob("*") if item.is_file()):
                name = path.relative_to(destination).as_posix()
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                output.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
    except BaseException:
        archive.unlink(missing_ok=True)
        raise
    return archive


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args(argv)
    paths = export_producer(args.output)
    if args.archive is not None:
        archive = archive_producer(args.output, args.archive)
        print(f"Standalone producer archive: {archive}")
    print(f"Standalone Wiki/Human Sphere producer: {args.output} ({len(paths)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
