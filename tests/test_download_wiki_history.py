from __future__ import annotations

import importlib.util
import json
import urllib.error
import urllib.parse
import zipfile
from datetime import datetime
from email.message import Message
from pathlib import Path
from typing import Any

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "download_wiki_snapshot.py"

spec = importlib.util.spec_from_file_location("download_wiki_snapshot_history", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_fetch_bytes_retries_transient_http_errors(monkeypatch) -> None:
    attempts = 0
    sleeps: list[float] = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def read(self) -> bytes:
            return b"ok"

    def fake_urlopen(request, timeout=30):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise urllib.error.HTTPError(
                request.full_url, 502, "Bad Gateway", hdrs=Message(), fp=None
            )
        return Response()

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(module.time, "sleep", sleeps.append)

    assert module.fetch_bytes(module.ROOT_URL) == b"ok"
    assert attempts == 3
    assert sleeps == [1.0, 2.0]


def test_fetch_bytes_does_not_retry_non_transient_http_error(monkeypatch) -> None:
    attempts = 0

    def fake_urlopen(request, timeout=30):
        nonlocal attempts
        attempts += 1
        raise urllib.error.HTTPError(
            request.full_url, 404, "Not Found", hdrs=Message(), fp=None
        )

    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    try:
        module.fetch_bytes(module.ROOT_URL)
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
    else:
        raise AssertionError("expected HTTPError")
    assert attempts == 1


def test_history_is_opt_in() -> None:
    assert module.parse_args([]).include_history is False
    assert module.parse_args(["--include-history"]).include_history is True
    resume = module.parse_args(["--resume-work", "preserved.work"])
    assert resume.resume_work == Path("preserved.work")


def test_current_crawl_records_mediawiki_page_identity(
    tmp_path: Path, monkeypatch
) -> None:
    page_url = "https://infinitythewiki.com/BS_Attack"
    pages = {
        module.ROOT_URL: (
            b'<html><body><a href="/BS_Attack">BS Attack</a>'
            b'<a href="/index.php?title=Main_Page&amp;oldid=4000">source</a>'
            b"</body></html>"
        ),
        page_url: (
            b'<html><body><a href="/index.php?title=BS_Attack&amp;oldid=4100">'
            b"source</a></body></html>"
        ),
    }
    monkeypatch.setattr(
        module,
        "fetch_bytes",
        lambda url, *, language="en": pages[url],
    )

    result = module.download_wiki(module.ROOT_URL, tmp_path)

    assert result.pages == (
        module.WikiPage(
            url=page_url,
            path="BS_Attack",
            title="BS_Attack",
        ),
        module.WikiPage(
            url=module.ROOT_URL,
            path="index.html",
            title="Main_Page",
        ),
    )


def test_fetch_page_revisions_follows_mediawiki_continuation(monkeypatch) -> None:
    page = module.WikiPage(
        url="https://infinitythewiki.com/BS_Attack",
        path="BS_Attack",
        title="BS_Attack",
    )
    requests: list[str] = []

    def fake_fetch(url: str, *, language: str = "en") -> bytes:
        assert language == "en"
        requests.append(url)
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        if "rvcontinue" not in query:
            document: dict[str, Any] = {
                "continue": {"continue": "||", "rvcontinue": "20250101000000|10"},
                "query": {
                    "pages": [
                        {
                            "pageid": 1,
                            "title": "BS Attack",
                            "revisions": [
                                {
                                    "revid": 10,
                                    "parentid": 0,
                                    "timestamp": "2024-12-01T00:00:00Z",
                                }
                            ],
                        }
                    ]
                },
            }
        else:
            assert query["rvcontinue"] == ["20250101000000|10"]
            document = {
                "query": {
                    "pages": [
                        {
                            "pageid": 1,
                            "title": "BS Attack",
                            "revisions": [
                                {
                                    "revid": 20,
                                    "parentid": 10,
                                    "timestamp": "2025-01-01T00:00:00Z",
                                }
                            ],
                        }
                    ]
                }
            }
        return json.dumps(document).encode()

    monkeypatch.setattr(module, "fetch_bytes", fake_fetch)

    title, revisions = module.fetch_page_revisions(page, language="en")

    assert title == "BS Attack"
    assert revisions == (
        module.WikiRevision(10, 0, "2024-12-01T00:00:00Z"),
        module.WikiRevision(20, 10, "2025-01-01T00:00:00Z"),
    )
    assert len(requests) == 2
    first_query = urllib.parse.parse_qs(urllib.parse.urlsplit(requests[0]).query)
    assert first_query["rvprop"] == ["ids|timestamp"]
    assert first_query["rvdir"] == ["newer"]
    assert first_query["rvlimit"] == ["max"]


def test_download_history_keeps_raw_oldid_pages_and_writes_index(
    tmp_path: Path, monkeypatch
) -> None:
    page = module.WikiPage(
        url="https://infinitythewiki.com/BS_Attack",
        path="BS_Attack",
        title="BS_Attack",
    )
    revisions = (
        module.WikiRevision(10, 0, "2024-12-01T00:00:00Z"),
        module.WikiRevision(20, 10, "2025-01-01T00:00:00Z"),
    )
    monkeypatch.setattr(
        module,
        "fetch_page_revisions",
        lambda _page, *, language="en", site=module.DEFAULT_SITE: ("BS Attack", revisions),
    )
    fetched: list[str] = []

    def fake_fetch(url: str, *, language: str = "en") -> bytes:
        fetched.append(url)
        oldid = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["oldid"][0]
        return f'<html><a href="/Other">revision {oldid}</a></html>'.encode()

    monkeypatch.setattr(module, "fetch_bytes", fake_fetch)

    result = module.download_wiki_history((page,), tmp_path)

    assert result.failures == ()
    assert result.revision_count == 2
    assert [path.relative_to(tmp_path).as_posix() for path in result.files] == [
        "_history/index.json",
        "_history/oldid/10.html",
        "_history/oldid/20.html",
    ]
    assert (tmp_path / "_history/oldid/10.html").read_bytes() == (
        b'<html><a href="/Other">revision 10</a></html>'
    )
    index = json.loads((tmp_path / "_history/index.json").read_text(encoding="utf-8"))
    assert index["format"] == module.HISTORY_INDEX_FORMAT
    assert index["revisionCount"] == 2
    assert index["pages"][0]["currentPath"] == "BS_Attack"
    assert [item["oldid"] for item in index["pages"][0]["revisions"]] == [10, 20]
    assert fetched == [
        module.oldid_url("BS Attack", 10, language="en"),
        module.oldid_url("BS Attack", 20, language="en"),
    ]


def test_download_history_reuses_existing_oldid_file(
    tmp_path: Path, monkeypatch
) -> None:
    page = module.WikiPage(
        url="https://infinitythewiki.com/BS_Attack",
        path="BS_Attack",
        title="BS_Attack",
    )
    revisions = (
        module.WikiRevision(10, 0, "2024-12-01T00:00:00Z"),
        module.WikiRevision(20, 10, "2025-01-01T00:00:00Z"),
    )
    monkeypatch.setattr(
        module,
        "fetch_page_revisions",
        lambda _page, *, language="en", site=module.DEFAULT_SITE: ("BS Attack", revisions),
    )
    existing = tmp_path / "_history" / "oldid" / "10.html"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"already downloaded")
    fetched: list[str] = []

    def fake_fetch(url: str, *, language: str = "en") -> bytes:
        fetched.append(url)
        return b"new revision"

    monkeypatch.setattr(module, "fetch_bytes", fake_fetch)

    result = module.download_wiki_history((page,), tmp_path)

    assert result.failures == ()
    assert result.revision_count == 2
    assert existing.read_bytes() == b"already downloaded"
    assert fetched == [module.oldid_url("BS Attack", 20, language="en")]


def test_history_archive_has_distinct_identity(tmp_path: Path) -> None:
    staging = tmp_path / "staging"
    page = staging / "index.html"
    staging.mkdir()
    page.write_text("wiki", encoding="utf-8")

    current_archive = module.archive_wiki(
        [page],
        tmp_path / "archives",
        root=staging,
        language="en",
        now=datetime(2026, 9, 28, 14, 30, 0),
    )
    history_archive = module.archive_wiki(
        [page],
        tmp_path / "archives",
        root=staging,
        language="en",
        now=datetime(2026, 9, 28, 14, 30, 0),
        include_history=True,
    )

    assert current_archive.name == "WIKI-en 20260928-143000.zip"
    assert history_archive.name == "WIKI-en-history 20260928-143000.zip"
    with zipfile.ZipFile(history_archive) as output:
        assert output.namelist() == ["index.html"]


def test_history_uses_separate_spanish_mediawiki_install() -> None:
    query = module.revision_query_url("Teniente", language="es")
    oldid = module.oldid_url("Teniente", 3687, language="es")

    assert query.startswith("https://infinitythewiki.com/wiki-es/api.php?")
    assert oldid.startswith("https://infinitythewiki.com/wiki-es/index.php?")


def test_main_history_failure_preserves_work_without_publishing(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    snapshot_root = tmp_path / "wiki"
    work_root = tmp_path / "work"
    manifest_directory = tmp_path / "manifests"

    def fake_download(
        root_url: str,
        staging: Path,
        *,
        language: str = "en",
        site=module.DEFAULT_SITE,
        progress=None,
    ) -> Any:
        assert root_url == module.ROOT_URL
        page = staging / "index.html"
        page.write_text("<html></html>", encoding="utf-8")
        return module.WikiDownloadResult(
            files=(page,),
            failures=(),
            pages=(module.WikiPage(module.ROOT_URL, "index.html", "Main Page"),),
        )

    def fake_history(
        pages: tuple[Any, ...],
        staging: Path,
        *,
        language: str = "en",
        site=module.DEFAULT_SITE,
        progress=None,
    ) -> Any:
        assert len(pages) == 1
        assert staging.is_dir()
        return module.WikiHistoryResult(
            files=(),
            failures=(
                module.WikiDownloadFailure(
                    url=module.oldid_url("Main Page", 1, language="en"),
                    error="OSError: unavailable",
                ),
            ),
            revision_count=0,
        )

    monkeypatch.setattr(module, "download_wiki", fake_download)
    monkeypatch.setattr(module, "download_wiki_history", fake_history)

    assert (
        module.main(
            [
                "--include-history",
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

    assert list(snapshot_root.glob("*.zip")) == []
    assert list(manifest_directory.glob("*.json")) == []
    work_directories = list(work_root.glob("WIKI-en-history *.work"))
    assert len(work_directories) == 1
    assert (work_directories[0] / "index.html").is_file()
    assert "Wiki history incomplete: 1 required revision request(s) failed." in (
        capsys.readouterr().err
    )
