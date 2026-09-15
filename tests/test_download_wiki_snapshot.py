import importlib.util
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


def test_sanitize_windows_path_components() -> None:
    name = module.sanitize_path_component("Special:Recent Changes?new=1*", os_name="Windows")
    assert name == "Special_Recent Changes_new=1_"
    assert "<" not in name and ">" not in name and ":" not in name
    assert "?" not in name and "*" not in name


def test_sanitize_posix_path_components() -> None:
    name = module.sanitize_path_component("folder/name.txt", os_name="Linux")
    assert name == "folder_name.txt"
    assert "/" not in name
