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
