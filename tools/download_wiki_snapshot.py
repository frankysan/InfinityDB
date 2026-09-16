#!/usr/bin/env python3
"""Download one timestamped local mirror snapshot of the Infinity wiki.

The downloader stages the mirror in a temporary directory, rewrites local links,
then stores the complete result as a timestamped ZIP archive. Loose downloaded
files are not retained after a successful run.
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

try:
    from tools.path_sanitization import sanitize_path_component, sanitize_relative_path
    from tools.snapshot_archive import create_timestamped_archive
except ImportError:  # pragma: no cover - direct script execution fallback
    from path_sanitization import sanitize_path_component, sanitize_relative_path
    from snapshot_archive import create_timestamped_archive

ROOT_URL = "https://infinitythewiki.com/"
ALLOWED_HOSTS = {"infinitythewiki.com", "assets.corvusbelli.net"}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:155.0) Gecko/20100101 Firefox/155.0"


class LinkExtractor(HTMLParser):
    """Collect href/src URLs from a page."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src"} and value:
                self.links.append(value)


def should_skip_url(url: str) -> bool:
    """Return True when a URL should not be mirrored."""
    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if host and host not in ALLOWED_HOSTS:
        return True

    path = parsed.path.lower()
    if "index.php" in path:
        return True
    if "/special" in path:
        return True
    if "/special:" in path:
        return True
    if "javascript:" in url.lower() or "mailto:" in url.lower() or "data:" in url.lower():
        return True
    return False


def local_relative_path(url: str, *, os_name: str | None = None) -> str:
    """Map a wiki URL to a relative local filesystem path."""
    parsed = urllib.parse.urlparse(url)
    path = parsed.path or "/"
    if path == "/":
        return "index.html"

    normalized = urllib.parse.unquote(path)
    if normalized.startswith("/"):
        normalized = normalized[1:]
    if not normalized or normalized.endswith("/"):
        normalized = f"{normalized}index.html" if normalized else "index.html"

    return sanitize_relative_path(normalized, os_name=os_name)


def rewrite_html_links(html_text: str, base_url: str, *, os_name: str | None = None) -> str:
    """Rewrite local wiki links to relative file paths used in the mirrored tree."""
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

        if hostname in {"assets.corvusbelli.net"}:
            a_path = urllib.parse.unquote(parsed.path)
            if a_path.startswith("/"):
                a_path = a_path[1:]
            if not a_path:
                return f"{match.group('attr')}{candidate}{match.group('quote')}"
            normalized = sanitize_relative_path(a_path, os_name=os_name)
            return f"{match.group('attr')}{normalized}{match.group('quote')}"

        if hostname == "infinitythewiki.com" or not hostname:
            relative = local_relative_path(candidate, os_name=os_name)
            return f"{match.group('attr')}{relative}{match.group('quote')}"

        return match.group(0)

    return pattern.sub(replace, html_text)


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
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


def download_wiki(base_url: str, destination: Path) -> list[Path]:
    queue: deque[str] = deque([base_url])
    seen: set[str] = set()
    saved: set[Path] = set()

    while queue:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)

        if should_skip_url(url):
            continue

        try:
            payload = fetch_bytes(url)
        except Exception as exc:  # pragma: no cover - network failures are expected in real use.
            print(f"Skipping {url}: {exc}", file=sys.stderr)
            continue

        relative = local_relative_path(url)
        target = destination / relative
        write_bytes(target, payload)
        saved.add(target)

        text = payload.decode("utf-8", errors="replace")
        if not any(token in text.lower() for token in ("<html", "<body", "href=", "src=")):
            continue

        rewritten_text = rewrite_html_links(text, url)
        write_bytes(target, rewritten_text.encode("utf-8"))

        parser = LinkExtractor()
        parser.feed(text)
        for value in parser.links:
            candidate = urllib.parse.urljoin(url, value)
            if should_skip_url(candidate):
                continue
            if candidate not in seen:
                queue.append(candidate)

    return sorted(saved)


def archive_wiki(
    files: list[Path],
    destination: Path,
    *,
    root: Path,
    now: datetime | None = None,
) -> Path:
    """Store exactly one mirrored wiki snapshot in a timestamped ZIP file."""
    return create_timestamped_archive(
        files,
        destination,
        prefix="WIKI",
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    snapshot_root = (Path.cwd() / args.root).resolve()
    snapshot_root.mkdir(parents=True, exist_ok=True)

    try:
        with tempfile.TemporaryDirectory(prefix="infinity-wiki-", dir=snapshot_root) as staging:
            staging_path = Path(staging)
            files = download_wiki(ROOT_URL, staging_path)
            if not files:
                print("No wiki pages were downloaded.", file=sys.stderr)
                return 1
            archive = archive_wiki(files, snapshot_root, root=staging_path)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Downloaded {len(files)} wiki files -> {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
