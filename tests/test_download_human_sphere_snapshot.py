from __future__ import annotations

import importlib.util
import json
import urllib.error
import urllib.parse
from datetime import datetime
from email.message import Message
from pathlib import Path
from typing import Any

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "download_wiki_snapshot.py"

spec = importlib.util.spec_from_file_location("download_human_sphere_snapshot", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _http_error(url: str, status: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url, status, "test error", hdrs=Message(), fp=None)


def test_human_sphere_site_contract_and_alias_canonicalization() -> None:
    site = module.HUMAN_SPHERE_SITE

    assert site.root_urls == {"en": "https://www.human-sphere.com/Main_Page"}
    assert module.canonical_crawl_url(
        "http://human-sphere.com/Main_Page#top",
        site=site,
    ) == "https://www.human-sphere.com/Main_Page"
    assert module.wiki_page_matches_language(
        "https://human-sphere.com/Stormbots",
        "en",
        site=site,
    )
    with pytest.raises(ValueError, match="English-only|expected one of: en"):
        module.wiki_page_matches_language(
            "https://www.human-sphere.com/Stormbots",
            "es",
            site=site,
        )




def test_human_sphere_ignores_noncontent_namespaces_and_service_endpoints() -> None:
    site = module.HUMAN_SPHERE_SITE

    assert module.ignored_url_reason(
        "https://www.human-sphere.com/Talk:PanOceania", site=site
    ) == "optional MediaWiki namespace"
    assert module.ignored_url_reason(
        "https://www.human-sphere.com/rest.php/v1/search", site=site
    ) == "optional site service endpoint"
    assert module.ignored_url_reason(
        "https://www.human-sphere.com/cdn-cgi/l/email-protection", site=site
    ) == "optional site service endpoint"
    assert module.ignored_url_reason(
        "https://www.human-sphere.com/Category:Units", site=site
    ) is None


def test_human_sphere_discovered_404s_are_ignored(
    tmp_path: Path,
    monkeypatch,
) -> None:
    site = module.HUMAN_SPHERE_SITE
    root = site.root_urls["en"]
    broken_page = "https://www.human-sphere.com/Copyright"
    broken_asset = "https://www.human-sphere.com/Wiki/HumanSphereLogo.png"
    fetched: list[str] = []

    monkeypatch.setattr(
        module,
        "fetch_all_page_titles",
        lambda *, language, site: ("Main Page",),
    )
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)

    def fake_fetch(url: str, *, language: str = "en") -> bytes:
        fetched.append(url)
        if url == root:
            return (
                b'<html><body><a href="/Copyright">Copyright</a>'
                b'<a href="/Talk:PanOceania">Talk</a>'
                b'<a href="/rest.php/v1/search">Search</a>'
                b'<a href="/cdn-cgi/l/email-protection">Email</a>'
                b'<img src="/Wiki/HumanSphereLogo.png"></body></html>'
            )
        if url in {broken_page, broken_asset}:
            raise _http_error(url, 404)
        raise AssertionError(f"unexpected network fetch: {url}")

    monkeypatch.setattr(module, "fetch_bytes", fake_fetch)

    result = module.download_wiki(root, tmp_path, language="en", site=site)

    assert result.failures == ()
    assert fetched == [root, broken_page, broken_asset]
    ignored = {item.url: item.reason for item in result.ignored}
    assert ignored[broken_page] == "discovered URL returned HTTP 404"
    assert ignored[broken_asset] == "discovered URL returned HTTP 404"
    assert ignored["https://www.human-sphere.com/Talk:PanOceania"] == (
        "optional MediaWiki namespace"
    )
    assert ignored["https://www.human-sphere.com/rest.php/v1/search"] == (
        "optional site service endpoint"
    )
    assert ignored["https://www.human-sphere.com/cdn-cgi/l/email-protection"] == (
        "optional site service endpoint"
    )


def test_human_sphere_enumerated_404_remains_required(
    tmp_path: Path,
    monkeypatch,
) -> None:
    site = module.HUMAN_SPHERE_SITE
    root = site.root_urls["en"]
    missing = "https://www.human-sphere.com/Missing_Page"

    monkeypatch.setattr(
        module,
        "fetch_all_page_titles",
        lambda *, language, site: ("Main Page", "Missing Page"),
    )
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)

    def fake_fetch(url: str, *, language: str = "en") -> bytes:
        if url == root:
            return b"<html><body>Main</body></html>"
        if url == missing:
            raise _http_error(url, 404)
        raise AssertionError(f"unexpected network fetch: {url}")

    monkeypatch.setattr(module, "fetch_bytes", fake_fetch)

    result = module.download_wiki(root, tmp_path, language="en", site=site)

    assert len(result.failures) == 1
    assert result.failures[0].url == missing
    assert result.ignored == ()


def test_human_sphere_allpages_enumeration_follows_continuation(monkeypatch) -> None:
    site = module.HUMAN_SPHERE_SITE
    requests: list[str] = []

    def fake_fetch(url: str, *, language: str, site: Any) -> bytes:
        requests.append(url)
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        if "apcontinue" not in query:
            document: dict[str, Any] = {
                "continue": {"continue": "-||", "apcontinue": "Orphan Page"},
                "query": {"allpages": [{"pageid": 1, "title": "Main Page"}]},
            }
        else:
            assert query["apcontinue"] == ["Orphan Page"]
            document = {
                "query": {"allpages": [{"pageid": 2, "title": "Orphan Page"}]}
            }
        return json.dumps(document).encode()

    monkeypatch.setattr(module, "fetch_site_bytes", fake_fetch)

    assert module.fetch_all_page_titles(language="en", site=site) == (
        "Main Page",
        "Orphan Page",
    )
    assert len(requests) == 2
    first = urllib.parse.parse_qs(urllib.parse.urlsplit(requests[0]).query)
    assert first["list"] == ["allpages"]
    assert first["apnamespace"] == ["0"]
    assert first["aplimit"] == ["max"]


def test_human_sphere_crawl_seeds_orphan_pages_and_follows_assets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    site = module.HUMAN_SPHERE_SITE
    root = site.root_urls["en"]
    orphan = "https://www.human-sphere.com/Orphan_Page"
    linked = "https://www.human-sphere.com/Linked_Page"
    image = "https://www.human-sphere.com/images/logo.png"
    pages = {
        root: (
            b'<html><body><a href="/Linked_Page">Linked</a>'
            b'<img src="/images/logo.png">'
            b'<a href="/index.php?title=Main_Page&amp;oldid=100">source</a>'
            b"</body></html>"
        ),
        orphan: b"<html><body>Orphan</body></html>",
        linked: b"<html><body>Linked</body></html>",
        image: b"PNG",
    }
    fetched: list[str] = []

    monkeypatch.setattr(
        module,
        "fetch_all_page_titles",
        lambda *, language, site: ("Main Page", "Orphan Page"),
    )
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)

    def fake_fetch(url: str, *, language: str = "en") -> bytes:
        assert language == "en"
        fetched.append(url)
        return pages[url]

    monkeypatch.setattr(module, "fetch_bytes", fake_fetch)

    result = module.download_wiki(root, tmp_path, language="en", site=site)

    assert result.failures == ()
    assert fetched == [root, orphan, linked, image]
    assert [path.relative_to(tmp_path).as_posix() for path in result.files] == [
        "Linked_Page.html",
        "Main_Page.html",
        "Orphan_Page.html",
        "images/logo.png",
    ]
    assert {page.title for page in result.pages} == {
        "Linked_Page",
        "Main_Page",
        "Orphan_Page",
    }


def test_human_sphere_page_paths_do_not_collide_with_descendant_assets() -> None:
    site = module.HUMAN_SPHERE_SITE

    page = module.local_relative_path(
        "https://www.human-sphere.com/Module:Infobox",
        site=site,
        os_name="Windows",
    )
    descendant = module.local_relative_path(
        "https://www.human-sphere.com/Module:Infobox/styles.css",
        asset=True,
        site=site,
        os_name="Windows",
    )

    assert page == "Module_Infobox.html"
    assert descendant == "Module_Infobox/styles.css"
    assert page != descendant.split("/", 1)[0]


def test_human_sphere_crawl_allows_page_and_descendant_asset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    site = module.HUMAN_SPHERE_SITE
    root = site.root_urls["en"]
    module_page = "https://www.human-sphere.com/Module:Infobox"
    module_asset = "https://www.human-sphere.com/Module:Infobox/styles.css"
    legacy_page = tmp_path / "Module_Infobox"
    legacy_page.write_bytes(b"legacy page")
    pages = {
        root: b'<html><body><a href="/Module:Infobox">Module</a></body></html>',
        module_page: (
            b'<html><head><link rel="stylesheet" href="/Module:Infobox/styles.css">'
            b"</head><body>Module</body></html>"
        ),
        module_asset: b".infobox {}",
    }
    monkeypatch.setattr(
        module,
        "fetch_all_page_titles",
        lambda *, language, site: ("Main Page", "Module:Infobox"),
    )
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        module,
        "fetch_bytes",
        lambda url, *, language="en": pages[url],
    )

    result = module.download_wiki(root, tmp_path, language="en", site=site)

    assert result.failures == ()
    assert legacy_page.is_dir()
    assert not legacy_page.is_file()
    assert [path.relative_to(tmp_path).as_posix() for path in result.files] == [
        "Main_Page.html",
        "Module_Infobox.html",
        "Module_Infobox/styles.css",
    ]


def test_human_sphere_resume_reuses_existing_assets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    site = module.HUMAN_SPHERE_SITE
    root = site.root_urls["en"]
    image = "https://www.human-sphere.com/images/logo.png"
    existing = tmp_path / "images" / "logo.png"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"existing PNG")
    monkeypatch.setattr(
        module,
        "fetch_all_page_titles",
        lambda *, language, site: ("Main Page",),
    )
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    fetched: list[str] = []

    def fake_fetch(url: str, *, language: str = "en") -> bytes:
        fetched.append(url)
        if url == root:
            return b'<html><body><img src="/images/logo.png"></body></html>'
        raise AssertionError(f"unexpected network fetch: {url}")

    monkeypatch.setattr(module, "fetch_bytes", fake_fetch)

    result = module.download_wiki(root, tmp_path, language="en", site=site)

    assert result.failures == ()
    assert fetched == [root]
    assert existing.read_bytes() == b"existing PNG"
    assert image not in fetched
    assert [path.relative_to(tmp_path).as_posix() for path in result.files] == [
        "Main_Page.html",
        "images/logo.png",
    ]


def test_human_sphere_link_rewriting_keeps_external_links_external() -> None:
    site = module.HUMAN_SPHERE_SITE
    html = (
        '<a href="http://human-sphere.com/Stormbots#Profile">Stormbots</a>'
        '<img src="https://www.human-sphere.com/images/unit.png">'
        '<a href="https://infinitythewiki.com/">Rules</a>'
    )

    rewritten = module.rewrite_html_links(
        html,
        site.root_urls["en"],
        language="en",
        site=site,
    )

    assert 'href="Stormbots.html#Profile"' in rewritten
    assert 'src="images/unit.png"' in rewritten
    assert 'href="https://infinitythewiki.com/"' in rewritten


def test_human_sphere_archive_and_work_names_are_source_specific(tmp_path: Path) -> None:
    site = module.HUMAN_SPHERE_SITE
    staging = tmp_path / "staging"
    staging.mkdir()
    page = staging / "Main_Page.html"
    page.write_text("Human Sphere", encoding="utf-8")
    timestamp = datetime(2026, 9, 30, 14, 30, 0)

    archive = module.archive_wiki(
        [page],
        tmp_path / "archives",
        root=staging,
        site=site,
        now=timestamp,
    )
    history_archive = module.archive_wiki(
        [page],
        tmp_path / "archives",
        root=staging,
        site=site,
        now=timestamp,
        include_history=True,
    )
    work = module.create_wiki_work_directory(
        tmp_path / "work",
        language="en",
        site=site,
        now=timestamp,
    )

    assert archive.name == "HUMAN-SPHERE 20260930-143000.zip"
    assert history_archive.name == "HUMAN-SPHERE-history 20260930-143000.zip"
    assert work.name == "HUMAN-SPHERE 20260930-143000.work"


def test_human_sphere_fetch_applies_courtesy_delay(monkeypatch) -> None:
    site = module.HUMAN_SPHERE_SITE
    sleeps: list[float] = []
    monkeypatch.setattr(module.time, "sleep", sleeps.append)
    monkeypatch.setattr(module, "fetch_bytes", lambda url, *, language="en": b"ok")

    assert module.fetch_site_bytes(site.root_urls["en"], language="en", site=site) == b"ok"
    assert sleeps == [site.request_delay_seconds]


def test_human_sphere_history_urls_use_its_mediawiki_install() -> None:
    site = module.HUMAN_SPHERE_SITE
    query = module.revision_query_url("Stormbots", language="en", site=site)
    oldid = module.oldid_url("Stormbots", 43097, language="en", site=site)

    assert query.startswith("https://www.human-sphere.com/api.php?")
    assert oldid.startswith("https://www.human-sphere.com/index.php?")


def test_main_human_sphere_snapshot_uses_distinct_provenance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    snapshot_root = tmp_path / "wiki"
    work_root = tmp_path / "work"
    manifest_directory = tmp_path / "manifests"
    site = module.HUMAN_SPHERE_SITE

    def fake_download(
        root_url: str,
        staging: Path,
        *,
        language: str = "en",
        site: Any = module.DEFAULT_SITE,
        progress=None,
    ) -> Any:
        assert root_url == module.HUMAN_SPHERE_SITE.root_urls["en"]
        assert site is module.HUMAN_SPHERE_SITE
        page = staging / "Main_Page.html"
        page.write_text("<html></html>", encoding="utf-8")
        return module.WikiDownloadResult(files=(page,), failures=())

    monkeypatch.setattr(module, "download_wiki", fake_download)

    assert (
        module.main(
            [
                "--site",
                "human-sphere",
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

    archives = list(snapshot_root.glob("HUMAN-SPHERE *.zip"))
    manifests = list(manifest_directory.glob("HUMAN-SPHERE *.json"))
    assert len(archives) == 1
    assert len(manifests) == 1
    assert list(work_root.glob("HUMAN-SPHERE *.work")) == []

    from infinity_db.snapshot_provenance import load_snapshot_manifest

    document = load_snapshot_manifest(manifests[0], archive=archives[0])
    assert document["snapshot"]["type"] == "wiki"
    assert document["source"] == {
        "url": site.root_urls["en"],
        "language": "en",
    }
