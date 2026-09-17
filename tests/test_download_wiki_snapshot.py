import importlib.util
import zipfile
from datetime import datetime
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "download_wiki_snapshot.py"

spec = importlib.util.spec_from_file_location("download_wiki_snapshot", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(module)


def test_should_skip_special_pages() -> None:
    assert module.should_skip_url("https://infinitythewiki.com/index.php?title=Main_Page")
    assert module.should_skip_url("https://infinitythewiki.com/wiki/Special:RecentChanges")
    assert module.should_skip_url("https://example.com/other-page")


def test_rewrite_relative_links_to_local_paths() -> None:
    html = """
    <html><body>
      <a href="/wiki/Main_Page">Main</a>
      <img src="/assets/logo.png" />
      <script src="https://assets.corvusbelli.net/js/app.js"></script>
    </body></html>
    """
    rewritten = module.rewrite_html_links(html, "https://infinitythewiki.com/", os_name="Windows")
    assert 'href="wiki/Main_Page"' in rewritten
    assert 'src="assets/logo.png"' in rewritten
    assert 'src="js/app.js"' in rewritten


def test_archive_wiki_uses_timestamp_and_relative_paths(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    page = staging / "Electromagnetic_(E_M)_Ammunition"
    asset = staging / "assets" / "logo.svg"
    page.parent.mkdir(parents=True)
    asset.parent.mkdir(parents=True)
    page.write_text("wiki", encoding="utf-8")
    asset.write_text("<svg/>", encoding="utf-8")

    archive = module.archive_wiki(
        [page, asset],
        tmp_path / "archives",
        root=staging,
        now=datetime(2026, 9, 16, 21, 30, 45),
    )

    assert archive.name == "WIKI 20260916-213045.zip"
    with zipfile.ZipFile(archive) as output:
        assert output.namelist() == [
            "Electromagnetic_(E_M)_Ammunition",
            "assets/logo.svg",
        ]


def test_sanitize_windows_path_components() -> None:
    name = module.sanitize_path_component("Special:Recent Changes?new=1*", os_name="Windows")
    assert name == "Special_Recent Changes_new=1_"
    assert "<" not in name and ">" not in name and ":" not in name
    assert "?" not in name and "*" not in name


def test_sanitize_posix_path_components() -> None:
    name = module.sanitize_path_component("folder/name.txt", os_name="Linux")
    assert name == "folder_name.txt"
    assert "/" not in name


def test_download_unit_symbols_sanitizes_windows_invalid_names() -> None:
    import importlib.util
    from pathlib import Path

    module_path = Path(__file__).resolve().parents[1] / "tools" / "download_unit_symbols.py"
    spec = importlib.util.spec_from_file_location("download_unit_symbols", module_path)
    assert spec is not None and spec.loader is not None
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)

    name = tool.destination_name(
        "https://assets.corvusbelli.net/army/img/logo/units/Special:Recent Changes?new=1*.svg"
    )
    assert name.endswith(".svg")
    assert "<" not in name and ">" not in name and ":" not in name
    assert "?" not in name and "*" not in name and '"' not in name


def test_reorganize_symbols_slugifies_windows_invalid_names() -> None:
    import importlib.util
    from pathlib import Path

    module_path = Path(__file__).resolve().parents[1] / "tools" / "reorganize_symbols.py"
    spec = importlib.util.spec_from_file_location("reorganize_symbols", module_path)
    assert spec is not None and spec.loader is not None
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)

    assert tool.slugify("Special:Recent Changes?new=1*") == "special-recent-changes-new-1"
