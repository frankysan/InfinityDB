import importlib.util
import io
import os
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
    assert module.should_skip_url("https://infinitythewiki.com/es/Especial:CambiosRecientes")
    assert module.should_skip_url("https://example.com/other-page")


def test_optional_site_urls_are_ignored_semantically() -> None:
    assert (
        module.ignored_url_reason("https://infinitythewiki.com/favicon.ico")
        == "optional site favicon"
    )
    assert (
        module.ignored_url_reason(
            "https://infinitythewiki.com/Infinity:Privacy_policy"
        )
        == "MediaWiki project namespace"
    )
    assert (
        module.ignored_url_reason("https://infinitythewiki.com/es/Infinity:About")
        == "MediaWiki project namespace"
    )
    assert module.ignored_url_reason("https://infinitythewiki.com/BS_Attack") is None


def test_wiki_page_language_scope() -> None:
    assert module.wiki_page_matches_language("https://infinitythewiki.com/Super-Jump", "en")
    assert not module.wiki_page_matches_language(
        "https://infinitythewiki.com/es/Super-Salto", "en"
    )
    assert module.wiki_page_matches_language(
        "https://infinitythewiki.com/es/Super-Salto", "es"
    )
    assert not module.wiki_page_matches_language(
        "https://infinitythewiki.com/Super-Jump", "es"
    )


def test_rewrite_relative_links_to_local_paths() -> None:
    html = """
    <html><body>
      <a href="/wiki/Main_Page">Main</a>
      <a href="/wiki/Main_Page#Contents">Contents</a>
      <img src="/assets/logo.png" />
      <script src="https://assets.corvusbelli.net/js/app.js"></script>
    </body></html>
    """
    rewritten = module.rewrite_html_links(
        html,
        "https://infinitythewiki.com/",
        language="en",
        os_name="Windows",
    )
    assert 'href="wiki/Main_Page"' in rewritten
    assert 'href="wiki/Main_Page#Contents"' in rewritten
    assert 'src="assets/logo.png"' in rewritten
    assert 'src="js/app.js"' in rewritten


def test_rewrite_ignored_site_links_stays_external() -> None:
    html = (
        '<html><head><link rel="icon" href="/favicon.ico"></head><body>'
        '<a href="/Infinity:About">About</a></body></html>'
    )
    rewritten = module.rewrite_html_links(
        html,
        module.ROOT_URL,
        language="en",
    )
    assert 'href="https://infinitythewiki.com/favicon.ico"' in rewritten
    assert 'href="https://infinitythewiki.com/Infinity:About"' in rewritten


def test_canonical_crawl_url_collapses_query_fragment_variants() -> None:
    assert (
        module.canonical_crawl_url(
            "https://InfinityTheWiki.com/Super-Jump?version=n4#Requirements"
        )
        == "https://infinitythewiki.com/Super-Jump"
    )


def test_download_wiki_fetches_each_canonical_url_once(
    tmp_path: Path, monkeypatch
) -> None:
    page_url = "https://infinitythewiki.com/Super-Jump"
    pages = {
        module.ROOT_URL: (
            b'<html><body><a href="/Super-Jump">One</a>'
            b'<a href="/Super-Jump">Duplicate</a>'
            b'<a href="/Super-Jump#Requirements">Fragment</a>'
            b'<a href="/Super-Jump?version=n4">Query</a></body></html>'
        ),
        page_url: b"<html><body>Done</body></html>",
    }
    fetched: list[str] = []

    def fake_fetch(url: str, *, language: str = "en") -> bytes:
        assert language == "en"
        fetched.append(url)
        return pages[url]

    monkeypatch.setattr(module, "fetch_bytes", fake_fetch)

    result = module.download_wiki(module.ROOT_URL, tmp_path)

    assert fetched == [module.ROOT_URL, page_url]
    assert [path.relative_to(tmp_path).as_posix() for path in result.files] == [
        "Super-Jump",
        "index.html",
    ]


def test_download_wiki_ignores_optional_site_links_without_fetching(
    tmp_path: Path, monkeypatch
) -> None:
    optional_urls = {
        "https://infinitythewiki.com/favicon.ico",
        "https://infinitythewiki.com/Infinity:Privacy_policy",
        "https://infinitythewiki.com/Infinity:About",
        "https://infinitythewiki.com/Infinity:General_disclaimer",
    }
    pages = {
        module.ROOT_URL: (
            b'<html><head><link rel="icon" href="/favicon.ico"></head><body>'
            b'<a href="/Infinity:Privacy_policy">Privacy</a>'
            b'<a href="/Infinity:About">About</a>'
            b'<a href="/Infinity:General_disclaimer">Disclaimer</a>'
            b'<a href="/BS_Attack">BS Attack</a></body></html>'
        ),
        "https://infinitythewiki.com/BS_Attack": b"<html><body>Rule</body></html>",
    }
    fetched: list[str] = []

    def fake_fetch(url: str, *, language: str = "en") -> bytes:
        fetched.append(url)
        return pages[url]

    monkeypatch.setattr(module, "fetch_bytes", fake_fetch)

    result = module.download_wiki(module.ROOT_URL, tmp_path)

    assert fetched == [
        module.ROOT_URL,
        "https://infinitythewiki.com/BS_Attack",
    ]
    assert result.failures == ()
    assert {item.url for item in result.ignored} == optional_urls


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

    assert archive.name == "WIKI-en 20260916-213045.zip"
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


def test_download_army_symbols_sanitizes_windows_invalid_names() -> None:
    import importlib.util
    from pathlib import Path

    module_path = Path(__file__).resolve().parents[1] / "tools" / "download_army_symbols.py"
    spec = importlib.util.spec_from_file_location("download_army_symbols", module_path)
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



def test_download_wiki_collects_failures_without_hiding_partial_crawl(
    tmp_path: Path, monkeypatch
) -> None:
    pages = {
        module.ROOT_URL: (
            b'<html><body><a href="/good">Good</a>'
            b'<a href="/missing">Missing</a></body></html>'
        ),
        "https://infinitythewiki.com/good": b"<html><body>Good</body></html>",
    }

    def fake_fetch(url: str, *, language: str = "en") -> bytes:
        assert language == "en"
        if url not in pages:
            raise OSError("not found")
        return pages[url]

    monkeypatch.setattr(module, "fetch_bytes", fake_fetch)

    result = module.download_wiki(module.ROOT_URL, tmp_path)

    assert [path.relative_to(tmp_path).as_posix() for path in result.files] == [
        "good",
        "index.html",
    ]
    assert len(result.failures) == 1
    assert result.failures[0].url == "https://infinitythewiki.com/missing"
    assert result.failures[0].error == "OSError: not found"


def test_main_rejects_incomplete_snapshot_before_archive_creation(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    snapshot_root = tmp_path / "wiki"
    work_root = tmp_path / "work"
    manifest_directory = tmp_path / "manifests"

    def fake_download(
        _root_url: str,
        staging: Path,
        *,
        language: str = "en",
        progress=None,
    ) -> module.WikiDownloadResult:
        assert language == "en"
        page = staging / "index.html"
        page.write_text("<html></html>", encoding="utf-8")
        return module.WikiDownloadResult(
            files=(page,),
            failures=(
                module.WikiDownloadFailure(
                    url="https://infinitythewiki.com/missing",
                    error="OSError: not found",
                ),
            ),
        )

    monkeypatch.setattr(module, "download_wiki", fake_download)

    assert (
        module.main(
            [
                "--root",
                str(snapshot_root),
                "--work-root",
                str(work_root),
                "--manifest-dir",
                str(manifest_directory),
            ]
        )
        == 1
    )

    assert list(snapshot_root.glob("WIKI-*.zip")) == []
    assert list(manifest_directory.glob("*.json")) == []
    work_directories = list(work_root.glob("WIKI-en *.work"))
    assert len(work_directories) == 1
    assert (work_directories[0] / "index.html").is_file()

    stderr = capsys.readouterr().err
    assert "Wiki snapshot incomplete: 1 required eligible URL(s) failed." in stderr
    assert "https://infinitythewiki.com/missing: OSError: not found" in stderr
    assert f"Preserved wiki work -> {work_directories[0]}" in stderr

def test_main_writes_snapshot_provenance(tmp_path: Path, monkeypatch) -> None:
    snapshot_root = tmp_path / "wiki"
    work_root = tmp_path / "work"
    manifest_directory = tmp_path / "manifests"

    def fake_download(
        _root_url: str,
        staging: Path,
        *,
        language: str = "en",
        progress=None,
    ) -> module.WikiDownloadResult:
        assert language == "en"
        page = staging / "index.html"
        page.write_text("<html></html>", encoding="utf-8")
        return module.WikiDownloadResult(files=(page,), failures=())

    monkeypatch.setattr(module, "download_wiki", fake_download)

    assert (
        module.main(
            [
                "--root",
                str(snapshot_root),
                "--work-root",
                str(work_root),
                "--manifest-dir",
                str(manifest_directory),
            ]
        )
        == 0
    )

    archives = list(snapshot_root.glob("WIKI-*.zip"))
    manifests = list(manifest_directory.glob("*.json"))
    assert len(archives) == 1
    assert len(manifests) == 1
    assert list(work_root.glob("WIKI-en *.work")) == []

    from infinity_db.snapshot_provenance import load_snapshot_manifest

    document = load_snapshot_manifest(manifests[0], archive=archives[0])
    assert document["snapshot"]["type"] == "wiki"
    assert document["snapshot"]["documentCount"] == 1
    assert document["source"] == {"url": module.ROOT_URL, "language": "en"}


def test_download_wiki_reports_progress_before_fetching(
    tmp_path: Path, monkeypatch
) -> None:
    pages = {
        module.ROOT_URL: b'<html><body><a href="/next">Next</a></body></html>',
        "https://infinitythewiki.com/next": b"<html><body>Done</body></html>",
    }

    monkeypatch.setattr(module, "fetch_bytes", lambda url, *, language="en": pages[url])
    updates: list[module.WikiCrawlProgress] = []

    result = module.download_wiki(module.ROOT_URL, tmp_path, progress=updates.append)

    assert len(result.files) == 2
    assert [update.url for update in updates] == [
        module.ROOT_URL,
        "https://infinitythewiki.com/next",
    ]
    assert updates[0] == module.WikiCrawlProgress(
        attempted=1,
        saved=0,
        failed=0,
        queued=0,
        url=module.ROOT_URL,
    )
    assert updates[1].attempted == 2
    assert updates[1].saved == 1


def test_console_progress_reporter_updates_one_interactive_line(monkeypatch) -> None:
    class TtyBuffer(io.StringIO):
        def isatty(self) -> bool:
            return True

    stream = TtyBuffer()
    monkeypatch.setattr(
        module.shutil,
        "get_terminal_size",
        lambda fallback: os.terminal_size((120, 24)),
    )
    reporter = module.ConsoleProgressReporter(stream)

    reporter(
        module.WikiCrawlProgress(
            attempted=7,
            saved=6,
            failed=0,
            queued=19,
            url="https://infinitythewiki.com/Super-Jump",
        )
    )
    reporter.finish()

    output = stream.getvalue()
    assert output.startswith(
        "\rWiki crawl: fetching 7 | saved 6 | ignored 0 | failed 0 | queued 19 | "
    )
    assert "https://infinitythewiki.com/Super-Jump" in output
    assert output.endswith("\n")

def test_english_crawl_skips_spanish_pages_but_keeps_referenced_assets(
    tmp_path: Path, monkeypatch
) -> None:
    spanish_page = "https://infinitythewiki.com/es/Reglas"
    spanish_asset = "https://infinitythewiki.com/es/images/shared.png"
    english_page = "https://infinitythewiki.com/Rules"
    pages = {
        module.ROOT_URL: (
            b'<html><body><a href="/Rules">Rules</a>'
            b'<a href="/es/Reglas">Reglas</a>'
            b'<img src="/es/images/shared.png" /></body></html>'
        ),
        english_page: b"<html><body>Rules</body></html>",
        spanish_asset: b"PNG",
    }
    fetched: list[str] = []

    def fake_fetch(url: str, *, language: str = "en") -> bytes:
        assert language == "en"
        fetched.append(url)
        return pages[url]

    monkeypatch.setattr(module, "fetch_bytes", fake_fetch)

    result = module.download_wiki(module.ROOT_URL, tmp_path, language="en")

    assert spanish_page not in fetched
    assert fetched == [module.ROOT_URL, english_page, spanish_asset]
    assert [path.relative_to(tmp_path).as_posix() for path in result.files] == [
        "Rules",
        "es/images/shared.png",
        "index.html",
    ]
    mirrored = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert 'href="https://infinitythewiki.com/es/Reglas"' in mirrored
    assert 'src="es/images/shared.png"' in mirrored


def test_spanish_crawl_skips_english_pages_but_keeps_referenced_assets(
    tmp_path: Path, monkeypatch
) -> None:
    root = module.LANGUAGE_ROOT_URLS["es"]
    spanish_page = "https://infinitythewiki.com/es/Reglas"
    english_page = "https://infinitythewiki.com/Rules"
    english_asset = "https://infinitythewiki.com/images/shared.png"
    pages = {
        root: (
            b'<html><body><a href="/es/Reglas">Reglas</a>'
            b'<a href="/Rules">Rules</a>'
            b'<img src="/images/shared.png" /></body></html>'
        ),
        spanish_page: b"<html><body>Reglas</body></html>",
        english_asset: b"PNG",
    }
    fetched: list[str] = []

    def fake_fetch(url: str, *, language: str = "es") -> bytes:
        assert language == "es"
        fetched.append(url)
        return pages[url]

    monkeypatch.setattr(module, "fetch_bytes", fake_fetch)

    result = module.download_wiki(root, tmp_path, language="es")

    assert english_page not in fetched
    assert fetched == [root, spanish_page, english_asset]
    assert [path.relative_to(tmp_path).as_posix() for path in result.files] == [
        "es/Reglas",
        "es/index.html",
        "images/shared.png",
    ]


def test_asset_query_variants_keep_distinct_fetch_and_local_paths() -> None:
    first = "https://infinitythewiki.com/load.php?modules=site.styles"
    second = "https://infinitythewiki.com/load.php?modules=skins.vector"

    assert module.canonical_crawl_url(first, asset=True) != module.canonical_crawl_url(
        second, asset=True
    )
    assert module.local_relative_path(first, asset=True) != module.local_relative_path(
        second, asset=True
    )


def test_archive_wiki_language_is_part_of_archive_identity(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    page = staging / "index.html"
    staging.mkdir()
    page.write_text("wiki", encoding="utf-8")

    archive = module.archive_wiki(
        [page],
        tmp_path / "archives",
        root=staging,
        language="es",
        now=datetime(2026, 9, 18, 12, 0, 0),
    )

    assert archive.name == "WIKI-es 20260918-120000.zip"


def test_main_spanish_snapshot_records_language_and_root(
    tmp_path: Path, monkeypatch
) -> None:
    snapshot_root = tmp_path / "wiki"
    work_root = tmp_path / "work"
    manifest_directory = tmp_path / "manifests"

    def fake_download(
        root_url: str,
        staging: Path,
        *,
        language: str = "en",
        progress=None,
    ) -> module.WikiDownloadResult:
        assert root_url == module.LANGUAGE_ROOT_URLS["es"]
        assert language == "es"
        page = staging / "es" / "index.html"
        page.parent.mkdir(parents=True)
        page.write_text("<html></html>", encoding="utf-8")
        return module.WikiDownloadResult(files=(page,), failures=())

    monkeypatch.setattr(module, "download_wiki", fake_download)

    assert (
        module.main(
            [
                "--language",
                "es",
                "--root",
                str(snapshot_root),
                "--work-root",
                str(work_root),
                "--manifest-dir",
                str(manifest_directory),
            ]
        )
        == 0
    )

    archives = list(snapshot_root.glob("WIKI-es *.zip"))
    manifests = list(manifest_directory.glob("WIKI-es *.json"))
    assert len(archives) == 1
    assert len(manifests) == 1
    assert list(work_root.glob("WIKI-es *.work")) == []

    from infinity_db.snapshot_provenance import load_snapshot_manifest

    document = load_snapshot_manifest(manifests[0], archive=archives[0])
    assert document["source"] == {
        "url": module.LANGUAGE_ROOT_URLS["es"],
        "language": "es",
    }
