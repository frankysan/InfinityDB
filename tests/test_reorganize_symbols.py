import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    module_path = ROOT / "tools" / "reorganize_symbols.py"
    spec = importlib.util.spec_from_file_location("reorganize_symbols", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_slugify_matches_asset_sanitization() -> None:
    module = load_module()

    assert module.slugify("Special:Recent Changes?new=1*") == "special-recent-changes-new-1"
