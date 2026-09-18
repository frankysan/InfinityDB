#!/usr/bin/env python3
"""Download one timestamped local mirror snapshot of the Infinity wiki.

The downloader stages the mirror in a local work directory, rewrites local links,
then stores the complete result as a timestamped ZIP archive. Successful runs remove
their work directory; incomplete runs preserve it for inspection.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
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

ROOT_URL = "https://infinitythewiki.com/"
SUPPORTED_LANGUAGES = ("en", "es")
LANGUAGE_ROOT_URLS = {
    "en": ROOT_URL,
    "es": urllib.parse.urljoin(ROOT_URL, "es/"),
}
LANGUAGE_ACCEPT_HEADERS = {
    "en": "en-US,en;q=0.9",
    "es": "es-ES,es;q=0.9,en;q=0.5",
}
ALLOWED_HOSTS = {"infinitythewiki.com", "assets.corvusbelli.net"}
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
        ".svg",
        ".webp",
        ".woff",
        ".woff2",
    }
)


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


class WikiDownloadResult(NamedTuple):
    """Complete crawl result retained until snapshot publication."""

    files: tuple[Path, ...]
    failures: tuple[WikiDownloadFailure, ...]
    ignored: tuple[WikiIgnoredURL, ...] = ()


class WikiCrawlProgress(NamedTuple):
    """One progress update emitted before fetching an eligible URL."""

    attempted: int
    saved: int
    failed: int
    queued: int
    url: str
    ignored: int = 0


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


def ignored_url_reason(url: str) -> str | None:
    """Return why an optional site URL does not affect snapshot completeness."""
    parsed = urllib.parse.urlsplit(url)
    if (parsed.hostname or "").lower() != "infinitythewiki.com":
        return None

    path = urllib.parse.unquote(parsed.path or "/")
    if path.casefold() == "/favicon.ico":
        return "optional site favicon"

    segments = [segment for segment in path.split("/") if segment]
    if any(segment.casefold().startswith("infinity:") for segment in segments):
        return "MediaWiki project namespace"

    return None


def should_skip_url(url: str) -> bool:
    """Return True when a URL should never be mirrored."""
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if host and host not in ALLOWED_HOSTS:
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
    suffix = Path(path).suffix.casefold()
    return suffix in ASSET_EXTENSIONS or Path(path).name.casefold() == "load.php"


def wiki_page_matches_language(url: str, language: str) -> bool:
    """Return whether a wiki page URL belongs to the selected language tree."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported wiki language: {language}")

    parsed = urllib.parse.urlsplit(url)
    if (parsed.hostname or "").lower() != "infinitythewiki.com":
        return False

    path = urllib.parse.unquote(parsed.path or "/").casefold()
    is_spanish = path == "/es" or path.startswith("/es/")
    return is_spanish if language == "es" else not is_spanish


def canonical_crawl_url(url: str, *, asset: bool = False) -> str:
    """Return the fetch identity used for one mirrored page or asset.

    Wiki page query/fragment variants map to the same persisted page and are
    collapsed. Asset queries can select different resources, so their query
    strings remain part of the fetch identity. Fragments never affect fetching.
    """
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path or "/",
            parsed.query if asset else "",
            "",
        )
    )


def local_relative_path(
    url: str,
    *,
    asset: bool = False,
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

    return sanitize_relative_path(normalized, os_name=os_name)


def rewrite_html_links(
    html_text: str,
    base_url: str,
    *,
    language: str = "en",
    os_name: str | None = None,
) -> str:
    """Rewrite included pages/assets to local mirror paths for one language."""
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

        if ignored_url_reason(candidate) is not None:
            return f"{match.group('attr')}{candidate}{match.group('quote')}"

        attr = match.group("attr").lstrip().casefold()
        asset = attr.startswith("src") or is_asset_url(candidate)

        if hostname == "assets.corvusbelli.net":
            relative = local_relative_path(candidate, asset=True, os_name=os_name)
            if parsed.fragment:
                relative = f"{relative}#{parsed.fragment}"
            return f"{match.group('attr')}{relative}{match.group('quote')}"

        if hostname == "infinitythewiki.com" or not hostname:
            if not asset and not wiki_page_matches_language(candidate, language):
                return f"{match.group('attr')}{candidate}{match.group('quote')}"
            relative = local_relative_path(candidate, asset=asset, os_name=os_name)
            if parsed.fragment:
                relative = f"{relative}#{parsed.fragment}"
            return f"{match.group('attr')}{relative}{match.group('quote')}"

        return match.group(0)

    return pattern.sub(replace, html_text)


def fetch_bytes(url: str, *, language: str = "en") -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": LANGUAGE_ACCEPT_HEADERS[language],
            "Connection": "keep-alive",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".part")
    with temp_path.open("wb") as handle:
        handle.write(payload)
    temp_path.replace(path)


def mirror_path_sort_key(path: PurePath, destination: PurePath) -> str:
    """Return a platform-neutral sort key for persisted mirror paths."""
    return path.relative_to(destination).as_posix()


def download_wiki(
    base_url: str,
    destination: Path,
    *,
    language: str = "en",
    progress: Callable[[WikiCrawlProgress], None] | None = None,
) -> WikiDownloadResult:
    """Crawl one language-scoped mirror candidate without publishing partial data."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported wiki language: {language}")
    if not wiki_page_matches_language(base_url, language):
        raise ValueError(f"Wiki root {base_url!r} does not match language {language!r}")

    canonical_base_url = canonical_crawl_url(base_url)
    queue: deque[tuple[str, bool]] = deque([(canonical_base_url, False)])
    discovered: set[str] = {canonical_base_url}
    saved: set[Path] = set()
    failures: list[WikiDownloadFailure] = []
    ignored: dict[str, WikiIgnoredURL] = {}
    attempted = 0

    while queue:
        url, asset = queue.popleft()

        ignore_reason = ignored_url_reason(url)
        if ignore_reason is not None:
            ignored[url] = WikiIgnoredURL(url=url, reason=ignore_reason)
            continue
        if should_skip_url(url):
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
            payload = fetch_bytes(url, language=language)
        except Exception as exc:  # pragma: no cover - network failures are expected in real use.
            failures.append(
                WikiDownloadFailure(url=url, error=f"{type(exc).__name__}: {exc}")
            )
            continue

        relative = local_relative_path(url, asset=asset)
        target = destination / relative
        write_bytes(target, payload)
        saved.add(target)

        if asset:
            continue

        text = payload.decode("utf-8", errors="replace")
        if not any(token in text.lower() for token in ("<html", "<body", "href=", "src=")):
            continue

        rewritten_text = rewrite_html_links(text, url, language=language)
        write_bytes(target, rewritten_text.encode("utf-8"))

        parser = LinkExtractor()
        parser.feed(text)
        for link in parser.links:
            absolute = urllib.parse.urljoin(url, link.value)
            candidate = canonical_crawl_url(absolute, asset=link.asset)
            if candidate in discovered:
                continue
            discovered.add(candidate)

            ignore_reason = ignored_url_reason(candidate)
            if ignore_reason is not None:
                ignored[candidate] = WikiIgnoredURL(
                    url=candidate,
                    reason=ignore_reason,
                )
                continue
            if should_skip_url(candidate):
                continue
            if not link.asset and not wiki_page_matches_language(candidate, language):
                continue
            queue.append((candidate, link.asset))

    return WikiDownloadResult(
        files=tuple(
            sorted(saved, key=lambda path: mirror_path_sort_key(path, destination))
        ),
        failures=tuple(failures),
        ignored=tuple(ignored[url] for url in sorted(ignored)),
    )


def create_wiki_work_directory(
    root: Path,
    *,
    language: str,
    now: datetime | None = None,
) -> Path:
    """Create a collision-safe work directory retained when acquisition fails."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported wiki language: {language}")

    root.mkdir(parents=True, exist_ok=True)
    timestamp = (now or datetime.now().astimezone()).strftime("%Y%m%d-%H%M%S")
    candidate = root / f"WIKI-{language} {timestamp}.work"
    counter = 2
    while candidate.exists():
        candidate = root / f"WIKI-{language} {timestamp}-{counter}.work"
        counter += 1
    candidate.mkdir()
    return candidate


def archive_wiki(
    files: list[Path],
    destination: Path,
    *,
    root: Path,
    language: str = "en",
    now: datetime | None = None,
) -> Path:
    """Store one language-labeled wiki snapshot in a timestamped ZIP file."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported wiki language: {language}")
    return create_timestamped_archive(
        files,
        destination,
        prefix=f"WIKI-{language}",
        root=root,
        now=now,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
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
        help="Wiki language to mirror (default: en)",
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
    snapshot_root = (Path.cwd() / args.root).resolve()
    work_root = (Path.cwd() / args.work_root).resolve()
    snapshot_root.mkdir(parents=True, exist_ok=True)
    archive: Path | None = None
    manifest: Path | None = None
    staging_path: Path | None = None
    progress = ConsoleProgressReporter()
    root_url = LANGUAGE_ROOT_URLS[args.language]

    try:
        started_at = datetime.now().astimezone()
        staging_path = create_wiki_work_directory(
            work_root,
            language=args.language,
            now=started_at,
        )
        try:
            result = download_wiki(
                root_url,
                staging_path,
                language=args.language,
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

        acquired_at = datetime.now().astimezone()
        archive = archive_wiki(
            files,
            snapshot_root,
            root=staging_path,
            language=args.language,
            now=acquired_at,
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

    try:
        shutil.rmtree(staging_path)
    except OSError as exc:
        print(f"WARNING: could not remove wiki work directory {staging_path}: {exc}")

    print(f"Downloaded {len(files)} wiki files -> {archive}")
    if result.ignored:
        print(f"Ignored {len(result.ignored)} optional site URL(s).")
    print(f"Snapshot provenance -> {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
