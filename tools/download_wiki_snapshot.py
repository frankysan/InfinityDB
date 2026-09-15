#!/usr/bin/env python3
"""Download a local mirror snapshot of the Infinity wiki.

This script is intentionally standalone like the other one-off downloaders in
``tools``. It keeps the important wget-style behavior:

- mirror a wiki subtree from the public site
- download linked local pages/assets
- rewrite local HTML links to point at the mirrored files
- skip special/index pages that are noisy or not useful for offline browsing
"""

from __future__ import annotations

import argparse
import html
import re
import shutil
import sys
import urllib.parse
import urllib.request
import zipfile
from collections import deque
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

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


def sanitize_path_component(value: str, *, os_name: str | None = None) -> str:
    """Normalize a path component so it is valid on the target OS."""
    os_name = (os_name or sys.platform).lower()

    cleaned = urllib.parse.unquote(value)
    cleaned = cleaned.strip().replace("\\", "/")

    if os_name.startswith("win"):
        cleaned = re.sub(r'[<>:"|?*]', "_", cleaned)
        cleaned = cleaned.rstrip(". ")
        if not cleaned:
            cleaned = "_"
    else:
        cleaned = re.sub(r"[\x00-\x1f]", "", cleaned)
        cleaned = cleaned.replace("/", "_")
        if not cleaned:
            cleaned = "_"

    return cleaned


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

    parts = [
        sanitize_path_component(part, os_name=os_name) for part in normalized.split("/") if part
    ]
    if not parts:
        return "index.html"
    return "/".join(parts)


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
            normalized = "/".join(
                sanitize_path_component(part, os_name=os_name) for part in a_path.split("/") if part
            )
            return f"{match.group('attr')}{normalized}{match.group('quote')}"

        if hostname == "infinitythewiki.com" or not hostname:
            relative = local_relative_path(candidate, os_name=os_name)
            return f"{match.group('attr')}{relative}{match.group('quote')}"

        return match.group(0)

    return pattern.sub(replace, html_text)


def fetch_text(url: str) -> str:
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
        body = response.read()
    return body.decode("utf-8", errors="replace")


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

        try:
            text = payload.decode("utf-8", errors="replace")
        except Exception:
            continue

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


def create_zip(snapshot_dir: Path, archive_path: Path) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(snapshot_dir.rglob("*")):
            if path.is_file():
                archive.write(path, arcname=path.relative_to(snapshot_dir).as_posix())


def ask_to_overwrite(snapshot_dir: Path, archive_path: Path) -> None:
    if not snapshot_dir.exists() and not archive_path.exists():
        return

    print("Existing snapshot found for this date:")
    if snapshot_dir.exists():
        print(f"  Mirror:  {snapshot_dir}")
    if archive_path.exists():
        print(f"  Archive: {archive_path}")

    answer = input("Overwrite and continue? [y/N]: ").strip().lower()
    if answer not in {"y", "yes"}:
        print("Aborting snapshot creation.")
        raise SystemExit(1)

    if snapshot_dir.exists():
        shutil.rmtree(snapshot_dir)
    if archive_path.exists():
        archive_path.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("data/wiki"),
        help="Parent folder used to store snapshot output (default: data/wiki)",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=datetime.utcnow().strftime("%Y%m%d"),
        help="Snapshot date in YYYYMMDD format (default: today)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing snapshot for the same date without prompting",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    snapshot_root = (Path.cwd() / args.root).resolve()
    snapshot_root.mkdir(parents=True, exist_ok=True)

    snapshot_dir = snapshot_root / args.date
    archive_path = snapshot_root / f"{args.date}.zip"

    if args.force:
        if snapshot_dir.exists():
            shutil.rmtree(snapshot_dir)
        if archive_path.exists():
            archive_path.unlink()
    else:
        ask_to_overwrite(snapshot_dir, archive_path)

    print(f"Creating wiki snapshot for {args.date}")
    print(f"Destination: {snapshot_dir}")
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    files = download_wiki(ROOT_URL, snapshot_dir)
    if not files:
        print("No wiki pages were downloaded.", file=sys.stderr)
        return 1

    create_zip(snapshot_dir, archive_path)
    print("Mirror completed.")
    print(f"Archive created: {archive_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
