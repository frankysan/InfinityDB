#!/usr/bin/env python3
"""Discover Corvus Belli store image URLs without downloading image assets.

This is an explicitly invoked acquisition/research command; normal builds and
tests never contact the store. Its JSON reports stay under ignored local/.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

STORE_HOST = "store.corvusbelli.com"
DEFAULT_URL = "https://store.corvusbelli.com/en/infinity/wargame/miniatures/myrmidons"
DEFAULT_OUTPUT_ROOT = Path("local/images/corvus-belli/store/discovery")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:155.0) "
    "Gecko/20100101 Firefox/155.0"
)
MAX_HTML_BYTES = 5 * 1024 * 1024
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif", ".svg", ".tif", ".tiff")
IMAGE_URL_RE = re.compile(
    r"""(?:(?:https?:)?//)[^\s"'<>\\]+?\.(?:png|jpe?g|webp|avif|gif|svg|tiff?)(?:\?[^\s"'<>\\]*)?""",
    re.IGNORECASE,
)
CSS_URL_RE = re.compile(r"""url\(\s*['"]?([^)'"]+)""", re.IGNORECASE)
SAFE_SLUG_RE = re.compile(r"[^a-z0-9-]+")


class StoreDiscoveryError(ValueError):
    """Store page cannot be safely fetched or analyzed."""


def validate_store_url(url: str) -> str:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != STORE_HOST
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
        or not parsed.path.startswith("/en/")
    ):
        raise StoreDiscoveryError("URL must be an HTTPS page on store.corvusbelli.com/en/")
    return url


def _image_like(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.path.lower().endswith(IMAGE_SUFFIXES)


def _absolute_image_url(value: str, base_url: str, *, explicit_image: bool) -> str | None:
    value = html.unescape(value.strip()).replace("\\/", "/")
    if not value or value.startswith(("#", "data:", "javascript:", "blob:")):
        return None
    absolute = urljoin(base_url, value)
    parsed = urlparse(absolute)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    if not explicit_image and not _image_like(absolute):
        return None
    return absolute


def _srcset_urls(value: str) -> list[str]:
    # Ordinary HTML srcset candidates are comma-delimited; density/width
    # descriptors follow the URL. Data URIs are intentionally not retained.
    return [part.strip().split()[0] for part in value.split(",") if part.strip()]


class ImageCollector:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.images: dict[str, set[str]] = {}

    def add(self, candidate: str, location: str, *, explicit_image: bool = False) -> None:
        url = _absolute_image_url(candidate, self.base_url, explicit_image=explicit_image)
        if url:
            self.images.setdefault(url, set()).add(location)

    def add_srcset(self, value: str, location: str) -> None:
        for candidate in _srcset_urls(value):
            self.add(candidate, location, explicit_image=True)

    def result(self) -> list[dict[str, Any]]:
        return [
            {"url": url, "discovered_via": sorted(locations)}
            for url, locations in sorted(self.images.items())
        ]


def _walk_product_data(value: Any, collector: ImageCollector, path: str = "json-ld") -> None:
    if isinstance(value, list):
        for index, item in enumerate(value):
            _walk_product_data(item, collector, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            field = str(key).lower()
            location = f"{path}.{key}"
            image_field = (
                field in {"image", "images", "thumbnail", "thumbnailurl", "contenturl"}
                or "gallery" in field
            )
            if image_field and isinstance(item, str):
                collector.add(item, location, explicit_image=True)
            elif image_field and isinstance(item, list):
                for entry in item:
                    if isinstance(entry, str):
                        collector.add(entry, location, explicit_image=True)
            _walk_product_data(item, collector, location)


class StorePageParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.base_url = page_url
        self.collector = ImageCollector(page_url)
        self.title_parts: list[str] = []
        self.skus: set[str] = set()
        self.script_urls: set[str] = set()
        self.has_app_root = False
        self._inside_title = False
        self._script_type: str | None = None
        self._script_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.lower(): val or "" for key, val in attrs}
        if tag == "base" and attributes.get("href"):
            self.base_url = urljoin(self.page_url, attributes["href"])
            self.collector.base_url = self.base_url
        if tag == "title":
            self._inside_title = True
        if tag == "app-root":
            self.has_app_root = True
        if tag == "script":
            self._script_type = attributes.get("type", "").lower()
            self._script_chunks = []
            if attributes.get("src"):
                self.script_urls.add(urljoin(self.base_url, attributes["src"]))

        for key, value in attributes.items():
            if not value:
                continue
            location = f"{tag}[{key}]"
            if key in {"srcset", "data-srcset", "imagesrcset", "data-lazy-srcset"}:
                if tag in {"img", "source", "link"}:
                    self.collector.add_srcset(value, location)
            elif key == "src" and tag in {"img", "source"}:
                self.collector.add(value, location, explicit_image=True)
            elif key in {
                "data-src", "data-lazy-src", "data-original", "data-image",
                "data-zoom-image", "data-large-image", "data-full-image",
                "data-full", "data-thumbnail", "data-large", "data-zoom",
            }:
                self.collector.add(value, location, explicit_image=True)
            elif key == "href" and tag in {"a", "link"}:
                self.collector.add(value, location)
            elif key == "poster" and tag == "video":
                self.collector.add(value, location, explicit_image=True)
            elif key == "style":
                for match in CSS_URL_RE.finditer(value):
                    self.collector.add(match.group(1), location)
            elif key == "content" and tag == "meta":
                meta_identity = (
                    attributes.get("property", "") or attributes.get("name", "")
                ).lower()
                if meta_identity in {
                    "og:image", "og:image:url", "og:image:secure_url",
                    "twitter:image", "twitter:image:src",
                }:
                    self.collector.add(value, f"meta[{meta_identity}]", explicit_image=True)
            elif "image" in key or "thumbnail" in key:
                # Storefront-specific lazy-loading attributes can vary.
                self.collector.add(value, location)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self._inside_title:
            self.title_parts.append(data)
        if self._script_type is not None:
            self._script_chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._inside_title = False
        if tag == "script" and self._script_type is not None:
            if "ld+json" in self._script_type:
                try:
                    structured = json.loads("".join(self._script_chunks))
                except json.JSONDecodeError:
                    pass
                else:
                    _walk_product_data(structured, self.collector)
                    self._collect_skus(structured)
            self._script_type = None
            self._script_chunks = []

    def _collect_skus(self, structured: Any) -> None:
        if isinstance(structured, list):
            for item in structured:
                self._collect_skus(item)
        elif isinstance(structured, dict):
            product_type = structured.get("@type", "")
            if isinstance(product_type, list):
                is_product = "Product" in product_type
            else:
                is_product = product_type == "Product"
            sku = structured.get("sku")
            if is_product and isinstance(sku, str) and sku.strip():
                self.skus.add(sku.strip())
            for child in structured.values():
                if isinstance(child, (dict, list)):
                    self._collect_skus(child)


def discover_from_html(raw: bytes, page_url: str) -> dict[str, Any]:
    parser = StorePageParser(page_url)
    text = raw.decode("utf-8-sig", errors="replace")
    parser.feed(text)
    parser.close()

    # A fallback for asset URLs embedded in JavaScript state instead of DOM
    # attributes. This does not execute scripts or request the referenced URLs.
    decoded = text.replace("\\/", "/").replace("\\u002F", "/").replace("\\u002f", "/")
    for match in IMAGE_URL_RE.finditer(decoded):
        parser.collector.add(match.group(), "embedded-source")
    images = parser.collector.result()
    is_spa_shell = parser.has_app_root and not images and not parser.skus
    return {
        "title": " ".join(" ".join(parser.title_parts).split()) or None,
        "skus": sorted(parser.skus),
        "images": images,
        "script_urls": sorted(parser.script_urls),
        "page_kind": "spa_shell" if is_spa_shell else "html_with_content",
    }


def probe_page(
    url: str,
    *,
    opener: Any = urlopen,
    timeout: int = 30,
    max_bytes: int = MAX_HTML_BYTES,
) -> tuple[dict[str, Any], bytes]:
    validate_store_url(url)
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://store.corvusbelli.com/en/",
        },
    )
    try:
        with opener(request, timeout=timeout) as response:
            resolved_url = response.geturl()
            validate_store_url(resolved_url)
            content_type = response.headers.get("Content-Type", "")
            if not content_type.lower().startswith(("text/html", "application/xhtml+xml")):
                raise StoreDiscoveryError(f"Unexpected Content-Type: {content_type!r}")
            body = response.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise StoreDiscoveryError(f"HTML response exceeds {max_bytes} bytes")
            status = response.status
    except (HTTPError, URLError, OSError) as exc:
        raise StoreDiscoveryError(f"Could not fetch store page: {exc}") from exc

    discovered = discover_from_html(body, resolved_url)
    report: dict[str, Any] = {
        "source": "corvus-belli-store",
        "requested_url": url,
        "resolved_url": resolved_url,
        "acquired_at": datetime.now(UTC).isoformat(),
        "http_status": status,
        "content_type": content_type,
        "html_sha256": hashlib.sha256(body).hexdigest(),
        "html_bytes": len(body),
        **discovered,
        "image_count": len(discovered["images"]),
        "note": "URL discovery only; no image assets downloaded or mappings verified",
    }
    return report, body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?", default=DEFAULT_URL, help="Store product page URL")
    parser.add_argument("--output", type=Path, help="JSON report path (defaults to ignored local/)")
    parser.add_argument("--save-html", action="store_true", help="Preserve raw HTML beside JSON")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    args = parser.parse_args(argv)
    if args.timeout < 1 or args.timeout > 120:
        parser.error("--timeout must be between 1 and 120 seconds")

    try:
        report, body = probe_page(args.url, timeout=args.timeout)
    except StoreDiscoveryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    filename = urlparse(report["resolved_url"]).path.rstrip("/").split("/")[-1].lower()
    slug = SAFE_SLUG_RE.sub("-", filename).strip("-") or "store-page"
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or DEFAULT_OUTPUT_ROOT / f"{slug}-{timestamp}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.save_html:
        output.with_suffix(".html").write_bytes(body)

    print(f"Page: {report['resolved_url']}")
    print(f"HTTP: {report['http_status']} ({report['html_bytes']} HTML bytes)")
    print(f"Images found: {report['image_count']}")
    if report["page_kind"] == "spa_shell":
        print("Note: JavaScript application shell; product assets are not in initial HTML.")
    print(f"Report: {output}")
    if args.save_html:
        print(f"HTML: {output.with_suffix('.html')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
