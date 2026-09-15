import importlib.util
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
