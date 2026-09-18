import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    module_path = ROOT / "tools" / "download_army_json.py"
    spec = importlib.util.spec_from_file_location("download_army_json", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_filename_slugifies_bad_faction_names() -> None:
    module = load_module()

    name = module._filename({"id": 42, "slug": "Special: Recent/Changes?*"})
    assert name == "42-special-recent-changes.json"


def test_main_writes_snapshot_provenance_and_reports_revisions(
    tmp_path, monkeypatch, capsys
) -> None:
    module = load_module()
    destination = tmp_path / "raw"
    manifest_directory = tmp_path / "manifests"

    def fake_download(staging, *, language):
        metadata = staging / "metadata.json"
        army = staging / "101-panoceania.json"
        sectorial = staging / "102-sectorial.json"
        metadata.write_text("{}", encoding="utf-8")
        army.write_text(
            json.dumps({"version": "7.26246.158", "units": []}),
            encoding="utf-8",
        )
        sectorial.write_text(
            json.dumps({"version": "7.26246.159", "units": []}),
            encoding="utf-8",
        )
        return [metadata, army, sectorial]

    monkeypatch.setattr(module, "download_snapshot", fake_download)

    assert (
        module.main(
            [
                str(destination),
                "--manifest-dir",
                str(manifest_directory),
            ]
        )
        == 0
    )

    archives = list(destination.glob("JSON *.zip"))
    manifests = list(manifest_directory.glob("*.json"))
    assert len(archives) == 1
    assert len(manifests) == 1

    from infinity_db.snapshot_provenance import load_snapshot_manifest

    document = load_snapshot_manifest(manifests[0], archive=archives[0])
    assert document["snapshot"]["type"] == "army"
    assert document["snapshot"]["documentCount"] == 3
    assert document["source"] == {"language": "en", "url": module.API_BASE_URL}

    output = capsys.readouterr().out
    assert "Downloaded 2 army lists and metadata" in output
    assert "Army source revisions -> 7.26246.158: 1, 7.26246.159: 1" in output
