import importlib.util
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    module_path = ROOT / "tools" / "download_unit_symbols.py"
    spec = importlib.util.spec_from_file_location("download_unit_symbols", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_destination_name_preserves_svg_extension() -> None:
    module = load_module()

    name = module.destination_name(
        "https://assets.corvusbelli.net/army/img/logo/units/Special:Recent Changes?new=1*.svg"
    )
    assert name == "special-recent-changes-new-1.svg"


def test_archive_symbols_uses_timestamp_and_complete_staging_set(tmp_path: Path) -> None:
    module = load_module()
    staging = tmp_path / "staging"
    staging.mkdir()
    first = staging / "first.svg"
    second = staging / "second.svg"
    first.write_text("<svg id='first'/>", encoding="utf-8")
    second.write_text("<svg id='second'/>", encoding="utf-8")

    archive = module.archive_symbols(
        [second, first],
        tmp_path / "archives",
        root=staging,
        now=datetime(2026, 9, 16, 21, 30, 45),
    )

    assert archive.name == "SYMBOLS 20260916-213045.zip"
    with zipfile.ZipFile(archive) as output:
        assert output.namelist() == ["first.svg", "second.svg"]


def test_main_writes_snapshot_provenance_with_input_hash(tmp_path: Path, monkeypatch) -> None:
    module = load_module()
    source = tmp_path / "army.json"
    destination = tmp_path / "symbols"
    manifest_directory = tmp_path / "manifests"
    source.write_text(
        '{"army": {"units": [{"id": 1, "slug": "test-unit", "profileGroups": '
        '[{"profiles": [{"logo": '
        '"https://assets.corvusbelli.net/army/img/logo/units/test-unit.svg"}]}]}]}}',
        encoding="utf-8",
    )

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return b"<svg/>"

    monkeypatch.setattr(module, "urlopen", lambda *_args, **_kwargs: Response())

    assert (
        module.main(
            [
                str(source),
                str(destination),
                "--manifest-dir",
                str(manifest_directory),
                "--delay",
                "0",
            ]
        )
        == 0
    )

    archives = list(destination.glob("SYMBOLS *.zip"))
    manifests = list(manifest_directory.glob("*.json"))
    assert len(archives) == 1
    assert len(manifests) == 1

    from infinity_db.snapshot_provenance import load_snapshot_manifest, sha256_file

    document = load_snapshot_manifest(manifests[0], archive=archives[0])
    assert document["snapshot"]["type"] == "symbols"
    assert document["snapshot"]["documentCount"] == 1
    assert document["inputArtifact"]["sha256"] == sha256_file(source)
    assert document["source"] == {"url": module.ASSET_BASE_URL}
