"""P5.4: prove a standalone Wiki producer can run without InfinityDB imports."""

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from infinity_db.snapshot_provenance import (
    load_snapshot_manifest,
    snapshot_content_sha256,
)
from tools.export_wiki_acquisition import archive_producer, export_producer


def _python_in_export(destination: Path, code: str) -> subprocess.CompletedProcess[str]:
    """Execute with isolated sys.path and no import of the InfinityDB checkout."""
    script = (
        "import sys\n"
        f"sys.path.insert(0, {str(destination / 'src')!r})\n"
        + code
    )
    return subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=destination,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def test_exported_wiki_producer_is_independent_and_contract_compatible(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "wiki-producer"
    paths = export_producer(destination)
    assert len(paths) == 12
    assert all(path.is_file() for path in paths)
    assert not (destination / "data").exists()

    source_root = destination / "src/infinity_wiki_acquisition"
    for file in source_root.glob("*.py"):
        text = file.read_text(encoding="utf-8")
        assert "from infinity_db" not in text
        assert "import infinity_db" not in text
        assert "from tools." not in text

    probe = _python_in_export(
        destination,
        "from infinity_wiki_acquisition import cli\n"
        "from infinity_wiki_acquisition import snapshot_provenance as provenance\n"
        "assert cli.WIKI_SITES['human-sphere'].archive_prefix == 'HUMAN-SPHERE'\n"
        "assert provenance.SNAPSHOT_MANIFEST_VERSION == 3\n"
        "assert 'infinity_db' not in sys.modules\n",
    )
    assert probe.returncode == 0, probe.stderr

    generated = _python_in_export(
        destination,
        "from datetime import UTC, datetime\n"
        "from pathlib import Path\n"
        "import zipfile\n"
        "from infinity_wiki_acquisition.snapshot_provenance import write_snapshot_manifest\n"
        "archive = Path('source.zip')\n"
        "with zipfile.ZipFile(archive, 'w') as out:\n"
        "    out.writestr('index.html', '<html>source</html>')\n"
        "write_snapshot_manifest(archive, Path('manifests'), snapshot_type='wiki',\n"
        "    acquired_at=datetime(2026, 11, 11, tzinfo=UTC),\n"
        "    source_url='https://infinitythewiki.com/', document_count=1,\n"
        "    project_root=Path.cwd(), language='en')\n",
    )
    assert generated.returncode == 0, generated.stderr

    archive = destination / "source.zip"
    manifest = destination / "manifests/source.json"
    verified = load_snapshot_manifest(manifest, archive=archive)
    assert verified["snapshot"]["contentSha256"] == snapshot_content_sha256(archive)
    assert verified["snapshot"]["archive"]["path"] == "source.zip"
    assert verified["source"]["language"] == "en"
    assert json.loads(manifest.read_text(encoding="utf-8")) == verified

    with pytest.raises(FileExistsError, match="already exists"):
        export_producer(destination)


def test_exported_downloader_tests_and_deterministic_bundle(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    export_producer(first)
    export_producer(second)
    one = archive_producer(first, tmp_path / "first.zip")
    two = archive_producer(second, tmp_path / "second.zip")
    assert one.read_bytes() == two.read_bytes()
    with zipfile.ZipFile(one) as source:
        assert "pyproject.toml" in source.namelist()
        assert "tests/test_downloader.py" in source.namelist()
        assert "tests/test_human_sphere.py" in source.namelist()
        assert "tests/test_wiki_history.py" in source.namelist()
        assert not any(name.startswith("data/") for name in source.namelist())

    check = _python_in_export(
        first,
        "import pytest\n"
        "raise SystemExit(pytest.main(['-q', 'tests']))\n",
    )
    assert check.returncode == 0, check.stdout + check.stderr
    assert "passed" in check.stdout
