import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    module_path = ROOT / "tools" / "path_sanitization.py"
    spec = importlib.util.spec_from_file_location("path_sanitization", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_path_sanitization_keeps_windows_path_components_readable() -> None:
    module = load_module()

    component = module.sanitize_path_component("Special:Recent Changes?new=1*", os_name="Windows")
    assert component == "Special_Recent Changes_new=1_"


def test_path_sanitization_slugifies_asset_filenames() -> None:
    module = load_module()

    filename = module.sanitize_filename("Special:Recent Changes?new=1*.svg", os_name="Windows")
    assert filename == "special-recent-changes-new-1.svg"
