"""Verify the Army producer export is independent and byte-compatible."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from infinity_db.snapshot_provenance import load_snapshot_manifest
from tools.army_snapshot_source import resolve_army_snapshot
from tools.download_army_json import acquire_army_snapshot
from tools.export_army_acquisition import archive_producer, export_producer

STAMP = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
METADATA = b'{"factions":[{"id":101,"name":"PanOceania"}]}'
ARMY = b'{"version":"7.26246.158","units":[]}'


class _Response:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _opener(request, **_kwargs):
    body = METADATA if request.full_url.endswith("/metadata") else ARMY
    return _Response(body)


def _isolated(project: Path, code: str) -> subprocess.CompletedProcess[str]:
    script = (
        "import sys\n"
        f"sys.path.insert(0, {str(project / 'src')!r})\n"
        + code
    )
    return subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def test_standalone_army_producer_export_and_offline_tests(tmp_path: Path) -> None:
    root = tmp_path / "external"
    paths = export_producer(root)
    assert len(paths) == 18
    assert not (root / "data").exists()
    for path in (root / "src/infinity_army_acquisition").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "from infinity_db" not in source
        assert "from infinity_army_data" not in source
        assert "from tools." not in source

    check = _isolated(
        root,
        "from infinity_army_acquisition import cli\n"
        "from infinity_army_acquisition.snapshot_provenance import SNAPSHOT_MANIFEST_VERSION\n"
        "assert SNAPSHOT_MANIFEST_VERSION == 3\n"
        "assert cli.API_BASE_URL == 'https://api.corvusbelli.com/army'\n"
        "assert 'infinity_db' not in sys.modules\n"
        "assert 'infinity_army_data' not in sys.modules\n"
        "import pytest\n"
        "raise SystemExit(pytest.main(['-q', 'tests']))\n",
    )
    assert check.returncode == 0, check.stdout + check.stderr
    assert "passed" in check.stdout


def test_standalone_army_producer_matches_infinitydb_zip_and_manifest(
    tmp_path: Path,
) -> None:
    root = tmp_path / "external"
    export_producer(root)
    code = (
        "from datetime import UTC, datetime\n"
        "from pathlib import Path\n"
        "from infinity_army_acquisition.cli import acquire_army_snapshot\n"
        f"metadata = {METADATA!r}\n"
        f"army = {ARMY!r}\n"
        "class Response:\n"
        "    def __init__(self, body): self.body = body\n"
        "    def __enter__(self): return self\n"
        "    def __exit__(self, *args): return None\n"
        "    def read(self): return self.body\n"
        "def opener(req, **kwargs):\n"
        "    return Response(metadata if req.full_url.endswith('/metadata') else army)\n"
        "result = acquire_army_snapshot(\n"
        "    Path('raw'), Path('manifests'), opener=opener,\n"
        "    project_root=Path.cwd(),\n"
        "    acquired_at=datetime(2026, 9, 17, 12, 0, tzinfo=UTC),\n"
        ")\n"
        "assert result.document_count == 2\n"
    )
    check = _isolated(root, code)
    assert check.returncode == 0, check.stdout + check.stderr

    current = tmp_path / "current"
    current.mkdir()
    original = acquire_army_snapshot(
        current / "raw",
        current / "manifests",
        opener=_opener,
        project_root=current,
        acquired_at=STAMP,
    )
    external_archive = next((root / "raw").glob("JSON *.zip"))
    external_manifest = next((root / "manifests").glob("JSON *.json"))
    assert external_archive.read_bytes() == original.archive.read_bytes()
    assert external_manifest.read_bytes() == original.manifest.read_bytes()
    validated = load_snapshot_manifest(external_manifest, archive=external_archive)
    resolved = resolve_army_snapshot(
        external_archive, manifest_directory=external_manifest.parent,
    )
    assert validated["snapshot"]["documentCount"] == 2
    assert resolved.source_revisions == {"7.26246.158": 1}
    assert resolved.document_count == original.document_count


def test_producer_export_is_reproducible_and_never_overwrites(
    tmp_path: Path,
) -> None:
    one = tmp_path / "one"
    two = tmp_path / "two"
    export_producer(one)
    export_producer(two)
    first = archive_producer(one, tmp_path / "one.zip")
    second = archive_producer(two, tmp_path / "two.zip")
    assert first.read_bytes() == second.read_bytes()
    with __import__("zipfile").ZipFile(first) as archive:
        paths = archive.namelist()
    assert "src/infinity_army_acquisition/cli.py" in paths
    assert "tests/test_downloader.py" in paths
    assert "README.md" in paths
    assert not any(name.startswith("data/") for name in paths)

    import pytest

    with pytest.raises(FileExistsError, match="already exists"):
        export_producer(one)
    with pytest.raises(FileExistsError, match="already exists"):
        archive_producer(one, first)


def test_standalone_source_decoder_matches_infinitydb_acceptance(
    tmp_path: Path,
) -> None:
    from infinity_army_data.merge import decode_document
    from infinity_army_data.metadata import decode_metadata
    from infinity_army_data.source_version import latest_army_source_change_date

    root = tmp_path / "producer"
    export_producer(root)
    samples = [
        {"kind": "metadata", "value": {"factions": [{"id": 1, "name": "Good"}]}},
        {"kind": "metadata", "value": {"factions": "not-a-list"}},
        {"kind": "metadata", "value": {"factions": [{"id": 1, "name": ""}]}},
        {"kind": "metadata", "value": {"factions": [{"id": 1, "name": "A", "parent": "x"}]}},
        {"kind": "document", "value": {"version": "7.26246.158", "units": []}},
        {"kind": "document", "value": {"version": "7.26246.158", "units": {}}},
        {"kind": "document", "value": []},
    ]

    def status(kind: str, value: object) -> str:
        raw = json.dumps(value).encode()
        func = decode_metadata if kind == "metadata" else decode_document
        try:
            func(raw, "test.json")
        except ValueError as exc:
            return type(exc).__name__ + ": " + str(exc)
        return "ok"

    expected = [status(s["kind"], s["value"]) for s in samples]
    program = (
        "import json\n"
        "from infinity_army_acquisition.metadata import decode_metadata\n"
        "from infinity_army_acquisition.source_document import decode_document\n"
        "from infinity_army_acquisition.source_version import latest_army_source_change_date\n"
        f"samples = json.loads({json.dumps(samples)!r})\n"
        "def status(kind, value):\n"
        "    raw = json.dumps(value).encode()\n"
        "    fn = decode_metadata if kind == 'metadata' else decode_document\n"
        "    try: fn(raw, 'test.json')\n"
        "    except ValueError as exc: return type(exc).__name__ + ': ' + str(exc)\n"
        "    return 'ok'\n"
        "print(json.dumps([status(item['kind'], item['value']) for item in samples]))\n"
    )
    check = _isolated(root, program)
    assert check.returncode == 0, check.stderr
    assert json.loads(check.stdout) == expected
    changed_on = latest_army_source_change_date(["7.26246.158"])
    assert changed_on is not None
    assert changed_on.isoformat() == "2026-09-03"
