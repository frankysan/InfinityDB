#!/usr/bin/env python3
"""Download one timestamped local mirror snapshot of a configured Infinity MediaWiki site.

The downloader stages the mirror in a local work directory, rewrites local links,
then stores the complete result as a timestamped ZIP archive. Optional history mode
also retains every revision advertised by MediaWiki for each mirrored page. Successful
runs remove their work directory; incomplete runs preserve it for inspection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from collections.abc import Callable
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path, PurePath
from typing import NamedTuple, TextIO

from infinity_db.snapshot_provenance import write_snapshot_manifest

try:
    from tools.path_sanitization import (
        sanitize_path_component as _sanitize_path_component,
    )
    from tools.path_sanitization import (
        sanitize_relative_path,
    )
    from tools.snapshot_archive import create_timestamped_archive
except ImportError:  # pragma: no cover - direct script execution fallback
    from path_sanitization import (
        sanitize_path_component as _sanitize_path_component,
    )
    from path_sanitization import (
        sanitize_relative_path,
    )
    from snapshot_archive import create_timestamped_archive

sanitize_path_component = _sanitize_path_component

HISTORY_DIRECTORY = "_history"
HISTORY_INDEX_FORMAT = "InfinityDB wiki revision history"
HISTORY_INDEX_VERSION = 1
FETCH_ATTEMPTS = 5
FETCH_RETRY_DELAYS = (1.0, 2.0, 4.0, 8.0)
RETRYABLE_HTTP_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:155.0) Gecko/20100101 Firefox/155.0"
ASSET_EXTENSIONS = frozenset(
    {
        ".avif",
        ".css",
        ".gif",
        ".ico",
        ".jpeg",
        ".jpg",
        ".js",
        ".json",
        ".png",
        ".pdf",
        ".rar",
        ".svg",
        ".txt",
        ".webp",
        ".woff",
        ".woff2",
        ".zip",
    }
)


class WikiSite(NamedTuple):
    """Static acquisition contract for one MediaWiki installation."""

    key: str
    label: str
    languages: tuple[str, ...]
    root_urls: dict[str, str]
    api_urls: dict[str, str]
    index_urls: dict[str, str]
    page_hosts: frozenset[str]
    canonical_host: str
    asset_hosts: frozenset[str]
    archive_prefix: str
    archive_language: bool
    project_namespaces: frozenset[str]
    ignored_namespaces: frozenset[str] = frozenset()
    ignored_path_prefixes: tuple[str, ...] = ()
    ignored_discovered_http_statuses: frozenset[int] = frozenset()
    enumerate_pages: bool = False
    request_delay_seconds: float = 0.0
    page_path_suffix: str = ""
    windows_portable_paths: bool = False


INFINITY_WIKI_SITE = WikiSite(
    key="infinity-wiki",
    label="Infinity Wiki",
    languages=("en", "es"),
    root_urls={
        "en": "https://infinitythewiki.com/",
        "es": "https://infinitythewiki.com/es/",
    },
    api_urls={
        "en": "https://infinitythewiki.com/api.php",
        "es": "https://infinitythewiki.com/wiki-es/api.php",
    },
    index_urls={
        "en": "https://infinitythewiki.com/index.php",
        "es": "https://infinitythewiki.com/wiki-es/index.php",
    },
    page_hosts=frozenset({"infinitythewiki.com"}),
    canonical_host="infinitythewiki.com",
    asset_hosts=frozenset({"assets.corvusbelli.net"}),
    archive_prefix="WIKI",
    archive_language=True,
    project_namespaces=frozenset({"infinity"}),
)

HUMAN_SPHERE_SITE = WikiSite(
    key="human-sphere",
    label="Human Sphere",
    languages=("en",),
    root_urls={"en": "https://www.human-sphere.com/Main_Page"},
    api_urls={"en": "https://www.human-sphere.com/api.php"},
    index_urls={"en": "https://www.human-sphere.com/index.php"},
    page_hosts=frozenset({"human-sphere.com", "www.human-sphere.com"}),
    canonical_host="www.human-sphere.com",
    asset_hosts=frozenset(),
    archive_prefix="HUMAN-SPHERE",
    archive_language=False,
    project_namespaces=frozenset({"human sphere"}),
    ignored_namespaces=frozenset({"talk"}),
    ignored_path_prefixes=("/rest.php/", "/cdn-cgi/"),
    ignored_discovered_http_statuses=frozenset({404}),
    enumerate_pages=True,
    request_delay_seconds=0.5,
    page_path_suffix=".html",
    windows_portable_paths=True,
)

WIKI_SITES = {
    INFINITY_WIKI_SITE.key: INFINITY_WIKI_SITE,
    HUMAN_SPHERE_SITE.key: HUMAN_SPHERE_SITE,
}
DEFAULT_SITE = INFINITY_WIKI_SITE

# Backwards-compatible public constants used by existing callers/tests.
ROOT_URL = DEFAULT_SITE.root_urls["en"]
SUPPORTED_LANGUAGES = DEFAULT_SITE.languages
LANGUAGE_ROOT_URLS = DEFAULT_SITE.root_urls
LANGUAGE_API_URLS = DEFAULT_SITE.api_urls
LANGUAGE_INDEX_URLS = DEFAULT_SITE.index_urls
LANGUAGE_ACCEPT_HEADERS = {
    "en": "en-US,en;q=0.9",
    "es": "es-ES,es;q=0.9,en;q=0.5",
}
ALLOWED_HOSTS = set(DEFAULT_SITE.page_hosts | DEFAULT_SITE.asset_hosts)


class WikiLink(NamedTuple):
    """One link discovered in an included HTML page."""

    value: str
    asset: bool


class WikiDownloadFailure(NamedTuple):
    """One required mirror URL that could not be fetched."""

    url: str
    error: str


class WikiIgnoredURL(NamedTuple):
    """One optional site URL excluded from snapshot completeness."""

    url: str
    reason: str


class WikiPage(NamedTuple):
    """One mirrored wiki page with its source identity."""

    url: str
    path: str
    title: str


class WikiRevision(NamedTuple):
    """One MediaWiki revision advertised for a mirrored page."""

    oldid: int
    parentid: int
    timestamp: str


class WikiDownloadResult(NamedTuple):
    """Complete crawl result retained until snapshot publication."""

    files: tuple[Path, ...]
    failures: tuple[WikiDownloadFailure, ...]
    ignored: tuple[WikiIgnoredURL, ...] = ()
    pages: tuple[WikiPage, ...] = ()


class WikiHistoryResult(NamedTuple):
    """Optional historical revision acquisition retained until publication."""

    files: tuple[Path, ...]
    failures: tuple[WikiDownloadFailure, ...]
    revision_count: int


class WikiCrawlProgress(NamedTuple):
    """One progress update emitted before fetching an eligible URL."""

    attempted: int
    saved: int
    failed: int
    queued: int
    url: str
    ignored: int = 0


class WikiHistoryProgress(NamedTuple):
    """One progress update emitted before fetching an old revision."""

    page: int
    pages: int
    saved: int
    failed: int
    url: str


class ConsoleProgressReporter:
    """Render compact crawl progress without flooding interactive terminals."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self.stream = stream if stream is not None else sys.stdout
        self._last_length = 0

    def __call__(self, progress: WikiCrawlProgress) -> None:
        message = (
            f"Wiki crawl: fetching {progress.attempted} | saved {progress.saved} | "
            f"ignored {progress.ignored} | failed {progress.failed} | "
            f"queued {progress.queued} | {progress.url}"
        )
        if self.stream.isatty():
            width = max(1, shutil.get_terminal_size(fallback=(120, 24)).columns - 1)
            visible = message[:width]
            padding = " " * max(0, self._last_length - len(visible))
            print(f"\r{visible}{padding}", end="", file=self.stream, flush=True)
            self._last_length = len(visible)
            return

        if progress.attempted == 1 or progress.attempted % 25 == 0:
            print(message, file=self.stream, flush=True)

    def finish(self) -> None:
        """Terminate an interactive in-place progress line cleanly."""
        if self.stream.isatty() and self._last_length:
            print(file=self.stream, flush=True)
            self._last_length = 0


class ConsoleHistoryProgressReporter:
    """Render compact historical-revision progress."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self.stream = stream if stream is not None else sys.stdout
        self._last_length = 0

    def __call__(self, progress: WikiHistoryProgress) -> None:
        message = (
            f"Wiki history: page {progress.page}/{progress.pages} | "
            f"saved {progress.saved} | failed {progress.failed} | {progress.url}"
        )
        if self.stream.isatty():
            width = max(1, shutil.get_terminal_size(fallback=(120, 24)).columns - 1)
            visible = message[:width]
            padding = " " * max(0, self._last_length - len(visible))
            print(f"\r{visible}{padding}", end="", file=self.stream, flush=True)
            self._last_length = len(visible)
            return

        if progress.saved == 0 or progress.saved % 100 == 0:
            print(message, file=self.stream, flush=True)

    def finish(self) -> None:
        """Terminate an interactive in-place progress line cleanly."""
        if self.stream.isatty() and self._last_length:
            print(file=self.stream, flush=True)
            self._last_length = 0


class LinkExtractor(HTMLParser):
    """Collect page links and explicitly referenced assets from one HTML page."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[WikiLink] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name not in {"href", "src"} or not value:
                continue
            asset = name == "src" or tag.lower() == "link" or is_asset_url(value)
            self.links.append(WikiLink(value=value, asset=asset))


def _require_site_language(site: WikiSite, language: str) -> None:
    if language not in site.languages:
        choices = ", ".join(site.languages)
        raise ValueError(
            f"Unsupported {site.label} language {language!r}; expected one of: {choices}"
        )


def _site_accept_language(language: str) -> str:
    return LANGUAGE_ACCEPT_HEADERS.get(language, f"{language},en;q=0.5")


def _site_archive_prefix(
    site: WikiSite,
    *,
    language: str,
    include_history: bool,
) -> str:
    _require_site_language(site, language)
    prefix = site.archive_prefix
    if site.archive_language:
        prefix = f"{prefix}-{language}"
    if include_history:
        prefix = f"{prefix}-history"
    return prefix


def page_title_from_html(
    html_text: str,
    *,
    site: WikiSite = DEFAULT_SITE,
    language: str = "en",
) -> str | None:
    """Extract the MediaWiki source title from a rendered page footer link."""
    _require_site_language(site, language)
    parser = LinkExtractor()
    parser.feed(html_text)
    valid_path = urllib.parse.urlsplit(site.index_urls[language]).path
    for link in reversed(parser.links):
        candidate = urllib.parse.urljoin(site.root_urls[language], link.value)
        parsed = urllib.parse.urlsplit(candidate)
        if (parsed.hostname or "").lower() not in site.page_hosts:
            continue
        if parsed.path != valid_path:
            continue
        query = urllib.parse.parse_qs(parsed.query)
        if query.get("oldid") and query.get("title"):
            return query["title"][0]
    return None


def page_title_from_url(
    url: str,
    *,
    language: str,
    site: WikiSite = DEFAULT_SITE,
) -> str:
    """Derive a MediaWiki title from a language-scoped pretty URL."""
    _require_site_language(site, language)
    path = urllib.parse.unquote(urllib.parse.urlsplit(url).path).strip("/")
    if site is INFINITY_WIKI_SITE and language == "es" and path.casefold() == "es":
        return "Página principal"
    if (
        site is INFINITY_WIKI_SITE
        and language == "es"
        and path.casefold().startswith("es/")
    ):
        path = path[3:]
    if not path:
        return "Main Page" if language == "en" else "Página principal"
    return path


def revision_query_url(
    title: str,
    *,
    language: str,
    continuation: str | None = None,
    site: WikiSite = DEFAULT_SITE,
) -> str:
    """Build one MediaWiki API request that enumerates page revisions."""
    _require_site_language(site, language)
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "prop": "revisions",
        "titles": title,
        "rvprop": "ids|timestamp",
        "rvlimit": "max",
        "rvdir": "newer",
    }
    if continuation is not None:
        params["rvcontinue"] = continuation
    return f"{site.api_urls[language]}?{urllib.parse.urlencode(params)}"


def oldid_url(
    title: str,
    oldid: int,
    *,
    language: str,
    site: WikiSite = DEFAULT_SITE,
) -> str:
    """Build the rendered source URL for one exact MediaWiki revision."""
    _require_site_language(site, language)
    query = urllib.parse.urlencode(
        {"title": title, "oldid": str(oldid), "redirect": "no"}
    )
    return f"{site.index_urls[language]}?{query}"


def allpages_query_url(
    *,
    language: str,
    continuation: str | None = None,
    site: WikiSite = DEFAULT_SITE,
) -> str:
    """Build one MediaWiki request enumerating main-namespace content pages."""
    _require_site_language(site, language)
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "list": "allpages",
        "apnamespace": "0",
        "aplimit": "max",
    }
    if continuation is not None:
        params["apcontinue"] = continuation
    return f"{site.api_urls[language]}?{urllib.parse.urlencode(params)}"


def page_url_from_title(
    title: str,
    *,
    language: str,
    site: WikiSite = DEFAULT_SITE,
) -> str:
    """Return a same-site pretty URL for one main-namespace MediaWiki title."""
    _require_site_language(site, language)
    root = urllib.parse.urlsplit(site.root_urls[language])
    base_path = "/"
    if site is INFINITY_WIKI_SITE and language == "es":
        base_path = "/es/"
    title_path = urllib.parse.quote(title.replace(" ", "_"), safe="/:()")
    return urllib.parse.urlunsplit(
        (root.scheme, site.canonical_host, f"{base_path}{title_path}", "", "")
    )


def fetch_page_revisions(
    page: WikiPage,
    *,
    language: str,
    site: WikiSite = DEFAULT_SITE,
) -> tuple[str, tuple[WikiRevision, ...]]:
    """Return every public revision advertised for one mirrored page."""
    _require_site_language(site, language)
    continuation: str | None = None
    revisions: list[WikiRevision] = []
    canonical_title: str | None = None

    while True:
        url = revision_query_url(
            page.title,
            language=language,
            continuation=continuation,
            site=site,
        )
        payload = fetch_site_bytes(url, language=language, site=site)
        try:
            document = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid MediaWiki revision response for {page.url}: {exc}") from exc
        if not isinstance(document, dict):
            raise ValueError(f"Invalid MediaWiki revision response for {page.url}")
        query = document.get("query")
        page_records = query.get("pages") if isinstance(query, dict) else None
        if not isinstance(page_records, list) or len(page_records) != 1:
            raise ValueError(f"MediaWiki revision response did not identify {page.url}")
        page_record = page_records[0]
        if not isinstance(page_record, dict) or "missing" in page_record:
            raise ValueError(f"MediaWiki page not found while reading history: {page.url}")
        title = page_record.get("title")
        if not isinstance(title, str) or not title:
            raise ValueError(f"MediaWiki revision response has no title for {page.url}")
        if canonical_title is None:
            canonical_title = title
        elif canonical_title != title:
            raise ValueError(f"MediaWiki revision title changed while reading {page.url}")

        batch = page_record.get("revisions", [])
        if not isinstance(batch, list):
            raise ValueError(f"MediaWiki revision list is invalid for {page.url}")
        for record in batch:
            if not isinstance(record, dict):
                raise ValueError(f"MediaWiki revision entry is invalid for {page.url}")
            oldid = record.get("revid")
            parentid = record.get("parentid")
            timestamp = record.get("timestamp")
            if (
                type(oldid) is not int
                or type(parentid) is not int
                or not isinstance(timestamp, str)
                or not timestamp
            ):
                raise ValueError(f"MediaWiki revision entry is incomplete for {page.url}")
            revisions.append(
                WikiRevision(oldid=oldid, parentid=parentid, timestamp=timestamp)
            )

        continuation_record = document.get("continue")
        if not isinstance(continuation_record, dict):
            break
        next_continuation = continuation_record.get("rvcontinue")
        if not isinstance(next_continuation, str) or not next_continuation:
            raise ValueError(f"MediaWiki revision continuation is invalid for {page.url}")
        continuation = next_continuation

    if canonical_title is None or not revisions:
        raise ValueError(f"MediaWiki returned no revisions for {page.url}")
    return canonical_title, tuple(revisions)


def fetch_all_page_titles(
    *,
    language: str,
    site: WikiSite = DEFAULT_SITE,
) -> tuple[str, ...]:
    """Return all main-namespace MediaWiki page titles for a configured site."""
    _require_site_language(site, language)
    continuation: str | None = None
    titles: list[str] = []

    while True:
        url = allpages_query_url(
            language=language,
            continuation=continuation,
            site=site,
        )
        payload = fetch_site_bytes(url, language=language, site=site)
        try:
            document = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid MediaWiki allpages response for {site.label}: {exc}"
            ) from exc
        if not isinstance(document, dict):
            raise ValueError(f"Invalid MediaWiki allpages response for {site.label}")
        query = document.get("query")
        page_records = query.get("allpages") if isinstance(query, dict) else None
        if not isinstance(page_records, list):
            raise ValueError(f"MediaWiki allpages response is invalid for {site.label}")
        for record in page_records:
            if not isinstance(record, dict):
                raise ValueError(f"MediaWiki allpages entry is invalid for {site.label}")
            title = record.get("title")
            if not isinstance(title, str) or not title:
                raise ValueError(f"MediaWiki allpages entry has no title for {site.label}")
            titles.append(title)

        continuation_record = document.get("continue")
        if not isinstance(continuation_record, dict):
            break
        next_continuation = continuation_record.get("apcontinue")
        if not isinstance(next_continuation, str) or not next_continuation:
            raise ValueError(f"MediaWiki allpages continuation is invalid for {site.label}")
        continuation = next_continuation

    return tuple(titles)


def _history_index_payload(
    *,
    language: str,
    pages: list[dict[str, object]],
    revision_count: int,
    site: WikiSite = DEFAULT_SITE,
) -> bytes:
    _require_site_language(site, language)
    document = {
        "format": HISTORY_INDEX_FORMAT,
        "formatVersion": HISTORY_INDEX_VERSION,
        "language": language,
        "pages": pages,
        "revisionCount": revision_count,
        "source": {
            "apiUrl": site.api_urls[language],
            "indexUrl": site.index_urls[language],
        },
    }
    return (
        json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def download_wiki_history(
    pages: tuple[WikiPage, ...],
    destination: Path,
    *,
    language: str = "en",
    site: WikiSite = DEFAULT_SITE,
    progress: Callable[[WikiHistoryProgress], None] | None = None,
) -> WikiHistoryResult:
    """Download all rendered oldid revisions for the mirrored current pages."""
    _require_site_language(site, language)
    if not pages:
        raise ValueError("Historical wiki acquisition requires at least one mirrored page")

    files: set[Path] = set()
    failures: list[WikiDownloadFailure] = []
    history_pages: list[dict[str, object]] = []
    saved_oldids: set[int] = set()

    for page_number, page in enumerate(pages, start=1):
        try:
            canonical_title, revisions = fetch_page_revisions(
                page,
                language=language,
                site=site,
            )
        except Exception as exc:  # pragma: no cover - live network failure path.
            failures.append(
                WikiDownloadFailure(
                    url=revision_query_url(page.title, language=language, site=site),
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
            continue

        revision_records: list[dict[str, object]] = []
        for revision in revisions:
            source_url = oldid_url(
                canonical_title,
                revision.oldid,
                language=language,
                site=site,
            )
            if progress is not None:
                progress(
                    WikiHistoryProgress(
                        page=page_number,
                        pages=len(pages),
                        saved=len(saved_oldids),
                        failed=len(failures),
                        url=source_url,
                    )
                )

            relative = f"{HISTORY_DIRECTORY}/oldid/{revision.oldid}.html"
            target = destination / relative
            if revision.oldid not in saved_oldids:
                if target.is_file():
                    files.add(target)
                    saved_oldids.add(revision.oldid)
                else:
                    try:
                        payload = fetch_site_bytes(
                            source_url,
                            language=language,
                            site=site,
                        )
                    except Exception as exc:  # pragma: no cover - live network failure path.
                        failures.append(
                            WikiDownloadFailure(
                                url=source_url, error=f"{type(exc).__name__}: {exc}"
                            )
                        )
                        continue
                    write_bytes(target, payload)
                    files.add(target)
                    saved_oldids.add(revision.oldid)

            revision_records.append(
                {
                    "oldid": revision.oldid,
                    "parentid": revision.parentid,
                    "path": relative,
                    "timestamp": revision.timestamp,
                    "url": source_url,
                }
            )

        history_pages.append(
            {
                "currentPath": page.path,
                "currentUrl": page.url,
                "revisions": revision_records,
                "title": canonical_title,
            }
        )

    index_path = destination / HISTORY_DIRECTORY / "index.json"
    write_bytes(
        index_path,
        _history_index_payload(
            language=language,
            pages=history_pages,
            revision_count=len(saved_oldids),
            site=site,
        ),
    )
    files.add(index_path)
    return WikiHistoryResult(
        files=tuple(
            sorted(files, key=lambda path: mirror_path_sort_key(path, destination))
        ),
        failures=tuple(failures),
        revision_count=len(saved_oldids),
    )


def ignored_url_reason(url: str, *, site: WikiSite = DEFAULT_SITE) -> str | None:
    """Return why an optional site URL does not affect snapshot completeness."""
    parsed = urllib.parse.urlsplit(url)
    if (parsed.hostname or "").lower() not in site.page_hosts:
        return None

    path = urllib.parse.unquote(parsed.path or "/")
    folded_path = path.casefold()
    if folded_path == "/favicon.ico":
        return "optional site favicon"
    if any(folded_path.startswith(prefix.casefold()) for prefix in site.ignored_path_prefixes):
        return "optional site service endpoint"

    segments = [segment.replace("_", " ").casefold() for segment in path.split("/") if segment]
    if any(
        any(segment.startswith(f"{namespace}:") for namespace in site.project_namespaces)
        for segment in segments
    ):
        return "MediaWiki project namespace"
    if any(
        any(segment.startswith(f"{namespace}:") for namespace in site.ignored_namespaces)
        for segment in segments
    ):
        return "optional MediaWiki namespace"

    return None


def ignored_fetch_failure_reason(
    exc: BaseException,
    *,
    required: bool,
    site: WikiSite = DEFAULT_SITE,
) -> str | None:
    """Return why a failed discovered URL may be omitted from a complete snapshot."""
    if required or not isinstance(exc, urllib.error.HTTPError):
        return None
    if exc.code in site.ignored_discovered_http_statuses:
        return f"discovered URL returned HTTP {exc.code}"
    return None


def should_skip_url(url: str, *, site: WikiSite = DEFAULT_SITE) -> bool:
    """Return True when a URL should never be mirrored."""
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    allowed_hosts = site.page_hosts | site.asset_hosts
    if host and host not in allowed_hosts:
        return True

    path = urllib.parse.unquote(parsed.path).casefold()
    if "index.php" in path:
        return True
    segments = [segment for segment in path.split("/") if segment]
    if any(
        segment in {"special", "especial"}
        or segment.startswith("special:")
        or segment.startswith("especial:")
        for segment in segments
    ):
        return True
    if "javascript:" in url.lower() or "mailto:" in url.lower() or "data:" in url.lower():
        return True
    return False


def is_asset_url(url: str) -> bool:
    """Return whether a URL path is recognizably an asset resource."""
    path = urllib.parse.urlsplit(url).path
    decoded_path = urllib.parse.unquote(path).casefold()
    suffix = Path(path).suffix.casefold()
    return (
        decoded_path.startswith("/images/")
        or suffix in ASSET_EXTENSIONS
        or Path(path).name.casefold() == "load.php"
    )


def wiki_page_matches_language(
    url: str,
    language: str,
    *,
    site: WikiSite = DEFAULT_SITE,
) -> bool:
    """Return whether a wiki page URL belongs to the selected language tree."""
    _require_site_language(site, language)

    parsed = urllib.parse.urlsplit(url)
    if (parsed.hostname or "").lower() not in site.page_hosts:
        return False

    if site is not INFINITY_WIKI_SITE:
        return True

    path = urllib.parse.unquote(parsed.path or "/").casefold()
    is_spanish = path == "/es" or path.startswith("/es/")
    return is_spanish if language == "es" else not is_spanish


def canonical_crawl_url(
    url: str,
    *,
    asset: bool = False,
    site: WikiSite = DEFAULT_SITE,
) -> str:
    """Return the fetch identity used for one mirrored page or asset.

    Wiki page query/fragment variants map to the same persisted page and are
    collapsed. Asset queries can select different resources, so their query
    strings remain part of the fetch identity. Fragments never affect fetching.
    """
    parsed = urllib.parse.urlsplit(url)
    hostname = (parsed.hostname or "").lower()
    netloc = parsed.netloc.lower()
    scheme = parsed.scheme.lower()
    if hostname in site.page_hosts:
        netloc = site.canonical_host
        scheme = urllib.parse.urlsplit(site.root_urls[site.languages[0]]).scheme
    return urllib.parse.urlunsplit(
        (
            scheme,
            netloc,
            parsed.path or "/",
            parsed.query if asset else "",
            "",
        )
    )


def local_relative_path(
    url: str,
    *,
    asset: bool = False,
    site: WikiSite = DEFAULT_SITE,
    os_name: str | None = None,
) -> str:
    """Map a mirrored page or asset URL to a relative local filesystem path."""
    parsed = urllib.parse.urlparse(url)
    path = parsed.path or "/"
    if path == "/":
        normalized = "index.html"
    else:
        normalized = urllib.parse.unquote(path)
        if normalized.startswith("/"):
            normalized = normalized[1:]
        if not normalized or normalized.endswith("/"):
            normalized = f"{normalized}index.html" if normalized else "index.html"
        elif not asset and site.page_path_suffix:
            normalized = f"{normalized}{site.page_path_suffix}"

    if asset and parsed.query:
        query_hash = hashlib.sha256(parsed.query.encode("utf-8")).hexdigest()[:12]
        candidate = Path(normalized)
        if candidate.suffix:
            normalized = str(
                candidate.with_name(
                    f"{candidate.stem}__q_{query_hash}{candidate.suffix}"
                )
            )
        else:
            normalized = f"{normalized}__q_{query_hash}"

    path_os_name = os_name
    if path_os_name is None and site.windows_portable_paths:
        path_os_name = "Windows"
    return sanitize_relative_path(normalized, os_name=path_os_name)


def rewrite_html_links(
    html_text: str,
    base_url: str,
    *,
    language: str = "en",
    site: WikiSite = DEFAULT_SITE,
    os_name: str | None = None,
) -> str:
    """Rewrite included pages/assets to local mirror paths for one language."""
    _require_site_language(site, language)
    pattern = re.compile(
        r'(?P<attr>\b(?:href|src)\s*=\s*["\'])(?P<value>[^"\']+)(?P<quote>["\'])', re.I
    )

    def replace(match: re.Match[str]) -> str:
        value = match.group("value")
        if not value:
            return match.group(0)

        candidate = urllib.parse.urljoin(base_url, value)
        parsed = urllib.parse.urlparse(candidate)
        hostname = (parsed.hostname or "").lower()

        if value.lower().startswith(("javascript:", "mailto:", "data:")):
            return match.group(0)

        if ignored_url_reason(candidate, site=site) is not None:
            return f"{match.group('attr')}{candidate}{match.group('quote')}"

        attr = match.group("attr").lstrip().casefold()
        asset = attr.startswith("src") or is_asset_url(candidate)

        if hostname in site.asset_hosts:
            relative = local_relative_path(candidate, asset=True, site=site, os_name=os_name)
            if parsed.fragment:
                relative = f"{relative}#{parsed.fragment}"
            return f"{match.group('attr')}{relative}{match.group('quote')}"

        if hostname in site.page_hosts or not hostname:
            if not asset and not wiki_page_matches_language(
                candidate,
                language,
                site=site,
            ):
                return f"{match.group('attr')}{candidate}{match.group('quote')}"
            relative = local_relative_path(candidate, asset=asset, site=site, os_name=os_name)
            if parsed.fragment:
                relative = f"{relative}#{parsed.fragment}"
            return f"{match.group('attr')}{relative}{match.group('quote')}"

        return match.group(0)

    return pattern.sub(replace, html_text)


def _retryable_fetch_error(exc: BaseException) -> bool:
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in RETRYABLE_HTTP_STATUS
    return isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError))


def fetch_bytes(url: str, *, language: str = "en") -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": _site_accept_language(language),
            "Connection": "keep-alive",
        },
    )
    for attempt in range(FETCH_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except Exception as exc:
            if not _retryable_fetch_error(exc) or attempt >= FETCH_ATTEMPTS - 1:
                raise
            time.sleep(FETCH_RETRY_DELAYS[attempt])
    raise AssertionError("fetch retry loop exhausted unexpectedly")


def fetch_site_bytes(
    url: str,
    *,
    language: str,
    site: WikiSite = DEFAULT_SITE,
) -> bytes:
    """Fetch one site URL, applying any source-specific courtesy delay."""
    _require_site_language(site, language)
    if site.request_delay_seconds:
        time.sleep(site.request_delay_seconds)
    return fetch_bytes(url, language=language)


def write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".part")
    with temp_path.open("wb") as handle:
        handle.write(payload)
    temp_path.replace(path)


def mirror_path_sort_key(path: PurePath, destination: PurePath) -> str:
    """Return a platform-neutral sort key for persisted mirror paths."""
    return path.relative_to(destination).as_posix()


def _migrate_blocking_legacy_page_paths(
    target: Path,
    destination: Path,
    *,
    site: WikiSite,
) -> None:
    """Move legacy extensionless page files that block a new descendant path."""
    if not site.page_path_suffix:
        return

    parents: list[Path] = []
    candidate = target.parent
    while candidate != destination:
        parents.append(candidate)
        if candidate.parent == candidate:
            raise ValueError(f"Mirror target is outside destination: {target}")
        candidate = candidate.parent

    for blocker in reversed(parents):
        if not blocker.is_file():
            continue
        migrated = blocker.with_name(f"{blocker.name}{site.page_path_suffix}")
        if migrated.exists():
            blocker.unlink()
        else:
            blocker.replace(migrated)


def download_wiki(
    base_url: str,
    destination: Path,
    *,
    language: str = "en",
    site: WikiSite = DEFAULT_SITE,
    progress: Callable[[WikiCrawlProgress], None] | None = None,
) -> WikiDownloadResult:
    """Crawl one language-scoped mirror candidate without publishing partial data."""
    _require_site_language(site, language)
    if not wiki_page_matches_language(base_url, language, site=site):
        raise ValueError(f"Wiki root {base_url!r} does not match language {language!r}")

    canonical_base_url = canonical_crawl_url(base_url, site=site)
    initial_urls = [canonical_base_url]
    if site.enumerate_pages:
        try:
            titles = fetch_all_page_titles(language=language, site=site)
        except Exception as exc:  # pragma: no cover - live network failure path.
            return WikiDownloadResult(
                files=(),
                failures=(
                    WikiDownloadFailure(
                        url=allpages_query_url(language=language, site=site),
                        error=f"{type(exc).__name__}: {exc}",
                    ),
                ),
            )
        initial_urls.extend(
            canonical_crawl_url(
                page_url_from_title(title, language=language, site=site),
                site=site,
            )
            for title in titles
        )

    required_urls = set(initial_urls)
    discovered = set(initial_urls)
    queue: deque[tuple[str, bool]] = deque((url, False) for url in dict.fromkeys(initial_urls))
    saved: set[Path] = set()
    pages: dict[str, WikiPage] = {}
    failures: list[WikiDownloadFailure] = []
    ignored: dict[str, WikiIgnoredURL] = {}
    attempted = 0

    while queue:
        url, asset = queue.popleft()

        ignore_reason = ignored_url_reason(url, site=site)
        if ignore_reason is not None:
            ignored[url] = WikiIgnoredURL(url=url, reason=ignore_reason)
            continue
        if should_skip_url(url, site=site):
            continue

        relative = local_relative_path(url, asset=asset, site=site)
        target = destination / relative
        if asset and target.is_file():
            saved.add(target)
            continue

        attempted += 1
        if progress is not None:
            progress(
                WikiCrawlProgress(
                    attempted=attempted,
                    saved=len(saved),
                    failed=len(failures),
                    queued=len(queue),
                    url=url,
                    ignored=len(ignored),
                )
            )

        try:
            payload = fetch_site_bytes(url, language=language, site=site)
        except Exception as exc:  # pragma: no cover - network failures are expected in real use.
            failure_ignore_reason = ignored_fetch_failure_reason(
                exc,
                required=url in required_urls,
                site=site,
            )
            if failure_ignore_reason is not None:
                ignored[url] = WikiIgnoredURL(url=url, reason=failure_ignore_reason)
                continue
            failures.append(
                WikiDownloadFailure(url=url, error=f"{type(exc).__name__}: {exc}")
            )
            continue

        _migrate_blocking_legacy_page_paths(target, destination, site=site)
        write_bytes(target, payload)
        saved.add(target)

        if asset:
            continue

        if site.page_path_suffix:
            legacy_site = site._replace(page_path_suffix="")
            legacy_relative = local_relative_path(url, site=legacy_site)
            legacy_target = destination / legacy_relative
            if legacy_target != target and legacy_target.is_file():
                legacy_target.unlink()

        text = payload.decode("utf-8", errors="replace")
        if not any(token in text.lower() for token in ("<html", "<body", "href=", "src=")):
            continue

        pages[url] = WikiPage(
            url=url,
            path=relative,
            title=page_title_from_html(text, site=site, language=language)
            or page_title_from_url(url, language=language, site=site),
        )
        rewritten_text = rewrite_html_links(text, url, language=language, site=site)
        write_bytes(target, rewritten_text.encode("utf-8"))

        parser = LinkExtractor()
        parser.feed(text)
        for link in parser.links:
            absolute = urllib.parse.urljoin(url, link.value)
            candidate = canonical_crawl_url(absolute, asset=link.asset, site=site)
            if candidate in discovered:
                continue
            discovered.add(candidate)

            ignore_reason = ignored_url_reason(candidate, site=site)
            if ignore_reason is not None:
                ignored[candidate] = WikiIgnoredURL(
                    url=candidate,
                    reason=ignore_reason,
                )
                continue
            if should_skip_url(candidate, site=site):
                continue
            if not link.asset and not wiki_page_matches_language(
                candidate,
                language,
                site=site,
            ):
                continue
            queue.append((candidate, link.asset))

    return WikiDownloadResult(
        files=tuple(
            sorted(saved, key=lambda path: mirror_path_sort_key(path, destination))
        ),
        failures=tuple(failures),
        ignored=tuple(ignored[url] for url in sorted(ignored)),
        pages=tuple(sorted(pages.values(), key=lambda page: page.path)),
    )


def create_wiki_work_directory(
    root: Path,
    *,
    language: str,
    site: WikiSite = DEFAULT_SITE,
    now: datetime | None = None,
    include_history: bool = False,
) -> Path:
    """Create a collision-safe work directory retained when acquisition fails."""
    _require_site_language(site, language)

    root.mkdir(parents=True, exist_ok=True)
    timestamp = (now or datetime.now().astimezone()).strftime("%Y%m%d-%H%M%S")
    prefix = _site_archive_prefix(
        site,
        language=language,
        include_history=include_history,
    )
    candidate = root / f"{prefix} {timestamp}.work"
    counter = 2
    while candidate.exists():
        candidate = root / f"{prefix} {timestamp}-{counter}.work"
        counter += 1
    candidate.mkdir()
    return candidate


def archive_wiki(
    files: list[Path],
    destination: Path,
    *,
    root: Path,
    language: str = "en",
    site: WikiSite = DEFAULT_SITE,
    now: datetime | None = None,
    include_history: bool = False,
) -> Path:
    """Store one language-labeled wiki snapshot in a timestamped ZIP file."""
    _require_site_language(site, language)
    return create_timestamped_archive(
        files,
        destination,
        prefix=_site_archive_prefix(
            site,
            language=language,
            include_history=include_history,
        ),
        root=root,
        now=now,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--site",
        choices=tuple(WIKI_SITES),
        default=DEFAULT_SITE.key,
        help=(
            "MediaWiki site to mirror (default: infinity-wiki; "
            "human-sphere is currently English-only)"
        ),
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("data/wiki"),
        help="Directory used to store timestamped wiki ZIP snapshots (default: data/wiki)",
    )
    parser.add_argument(
        "--work-root",
        type=Path,
        default=Path("data/work/wiki"),
        help=(
            "Directory used for temporary wiki crawl work; incomplete runs are "
            "preserved here (default: data/work/wiki)"
        ),
    )
    parser.add_argument(
        "--language",
        choices=SUPPORTED_LANGUAGES,
        default="en",
        help="Wiki language to mirror where supported (default: en)",
    )
    parser.add_argument(
        "--include-history",
        action="store_true",
        help=(
            "Also archive every rendered MediaWiki oldid revision for each mirrored "
            "page; this can be substantially larger and slower than a normal snapshot"
        ),
    )
    parser.add_argument(
        "--resume-work",
        type=Path,
        help=(
            "Reuse a preserved wiki work directory from an incomplete run; existing "
            "oldid files are not downloaded again"
        ),
    )
    parser.add_argument(
        "--manifest-dir",
        type=Path,
        default=Path("data/manifests/snapshots"),
        help="Generated snapshot manifest directory (default: data/manifests/snapshots)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    site = WIKI_SITES[args.site]
    try:
        _require_site_language(site, args.language)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    snapshot_root = (Path.cwd() / args.root).resolve()
    work_root = (Path.cwd() / args.work_root).resolve()
    snapshot_root.mkdir(parents=True, exist_ok=True)
    archive: Path | None = None
    manifest: Path | None = None
    staging_path: Path | None = None
    history_result: WikiHistoryResult | None = None
    progress = ConsoleProgressReporter()
    root_url = site.root_urls[args.language]

    try:
        started_at = datetime.now().astimezone()
        if args.resume_work is not None:
            resume_path = (Path.cwd() / args.resume_work).resolve()
            if not resume_path.is_dir():
                raise ValueError(f"Wiki resume work directory does not exist: {resume_path}")
            staging_path = resume_path
        else:
            staging_path = create_wiki_work_directory(
                work_root,
                language=args.language,
                site=site,
                now=started_at,
                include_history=args.include_history,
            )
        assert staging_path is not None
        try:
            result = download_wiki(
                root_url,
                staging_path,
                language=args.language,
                site=site,
                progress=progress,
            )
        finally:
            progress.finish()

        if result.failures:
            print(
                f"Wiki snapshot incomplete: {len(result.failures)} required "
                "eligible URL(s) failed.",
                file=sys.stderr,
            )
            if result.ignored:
                print(
                    f"Ignored {len(result.ignored)} optional site URL(s).",
                    file=sys.stderr,
                )
            for failure in result.failures:
                print(f"  {failure.url}: {failure.error}", file=sys.stderr)
            print(f"Preserved wiki work -> {staging_path}", file=sys.stderr)
            return 1

        files = list(result.files)
        if not files:
            print("No wiki pages were downloaded.", file=sys.stderr)
            print(f"Preserved wiki work -> {staging_path}", file=sys.stderr)
            return 1

        if args.include_history:
            history_progress = ConsoleHistoryProgressReporter()
            try:
                history_result = download_wiki_history(
                    result.pages,
                    staging_path,
                    language=args.language,
                    site=site,
                    progress=history_progress,
                )
            finally:
                history_progress.finish()
            if history_result.failures:
                print(
                    f"Wiki history incomplete: {len(history_result.failures)} required "
                    "revision request(s) failed.",
                    file=sys.stderr,
                )
                for failure in history_result.failures:
                    print(f"  {failure.url}: {failure.error}", file=sys.stderr)
                print(f"Preserved wiki work -> {staging_path}", file=sys.stderr)
                return 1
            files.extend(history_result.files)

        acquired_at = datetime.now().astimezone()
        archive = archive_wiki(
            files,
            snapshot_root,
            root=staging_path,
            language=args.language,
            site=site,
            now=acquired_at,
            include_history=args.include_history,
        )
        manifest = write_snapshot_manifest(
            archive,
            args.manifest_dir,
            snapshot_type="wiki",
            acquired_at=acquired_at,
            source_url=root_url,
            document_count=len(files),
            project_root=Path.cwd(),
            language=args.language,
        )
    except (OSError, ValueError) as exc:
        if manifest is not None:
            manifest.unlink(missing_ok=True)
        if archive is not None:
            archive.unlink(missing_ok=True)
        print(f"ERROR: {exc}", file=sys.stderr)
        if staging_path is not None and staging_path.exists():
            print(f"Preserved wiki work -> {staging_path}", file=sys.stderr)
        return 1

    assert staging_path is not None
    try:
        shutil.rmtree(staging_path)
    except OSError as exc:
        print(f"WARNING: could not remove wiki work directory {staging_path}: {exc}")

    if history_result is not None:
        print(
            f"Downloaded {len(result.files)} current wiki files + "
            f"{history_result.revision_count} historical revisions -> {archive}"
        )
    else:
        print(f"Downloaded {len(files)} wiki files -> {archive}")
    if result.ignored:
        print(f"Ignored {len(result.ignored)} optional site URL(s).")
    print(f"Snapshot provenance -> {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
