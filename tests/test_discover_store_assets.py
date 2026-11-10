"""Offline contract tests for metadata-only Corvus Belli store discovery."""

import io
import json

import pytest

from tools import discover_store_assets as store

PAGE = store.DEFAULT_URL


class FakeResponse:
    def __init__(self, body: bytes, url: str = PAGE, mime: str = "text/html") -> None:
        self.body = io.BytesIO(body)
        self.url = url
        self.headers = {"Content-Type": mime}
        self.status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def geturl(self):
        return self.url

    def read(self, n=-1):
        return self.body.read(n)


def test_discover_html_product_image_variants_and_provenance() -> None:
    page = b"""
        <html><head><base href="/en/"><title>Myrmidons</title>
        <meta property="og:image" content="//assets.corvusbelli.net/og.jpg">
        <script type="application/ld+json">
        {"@type":"Product","sku":"280881-1060",
         "image":["https://assets.corvusbelli.net/one.png","/two.webp"]}
        </script></head><body>
        <img src="/mini.jpg" data-zoom-image="/mini-large.jpg"
             srcset="/mini-400.jpg 400w, /mini-800.jpg 800w">
        <picture><source srcset="/mini.avif 1x, /mini@2x.avif 2x"></picture>
        <a href="/full.jpeg"><img data-src="/lazy.webp"></a>
        <div style="background-image:url('/background.png')"></div>
        <script type="module" src="main.123.js"></script>
        <script>const x = "https://assets.corvusbelli.net/more.jpg";</script>
        </body></html>
    """
    parsed = store.discover_from_html(page, PAGE)
    url_to_method = {item["url"]: item["discovered_via"] for item in parsed["images"]}
    assert parsed["title"] == "Myrmidons"
    assert parsed["skus"] == ["280881-1060"]
    assert parsed["page_kind"] == "html_with_content"
    assert parsed["script_urls"] == ["https://store.corvusbelli.com/en/main.123.js"]
    assert "meta[og:image]" in url_to_method["https://assets.corvusbelli.net/og.jpg"]
    assert "json-ld.image" in url_to_method["https://assets.corvusbelli.net/one.png"]
    assert "img[data-zoom-image]" in url_to_method["https://store.corvusbelli.com/mini-large.jpg"]
    assert "img[srcset]" in url_to_method["https://store.corvusbelli.com/mini-800.jpg"]
    assert "source[srcset]" in url_to_method["https://store.corvusbelli.com/mini@2x.avif"]
    assert "a[href]" in url_to_method["https://store.corvusbelli.com/full.jpeg"]
    assert "div[style]" in url_to_method["https://store.corvusbelli.com/background.png"]
    assert "embedded-source" in url_to_method["https://assets.corvusbelli.net/more.jpg"]


def test_spa_shell_is_detected_and_scripts_are_recorded() -> None:
    parsed = store.discover_from_html(
        b'<base href="/en/"><app-root></app-root>'
        b'<script src="runtime.123.js"></script><script src="main.456.js"></script>',
        PAGE,
    )
    assert parsed["page_kind"] == "spa_shell"
    assert parsed["images"] == []
    assert parsed["script_urls"] == [
        "https://store.corvusbelli.com/en/main.456.js",
        "https://store.corvusbelli.com/en/runtime.123.js",
    ]


def test_probe_fetches_html_only_with_explicit_user_agent() -> None:
    requests = []

    def opener(request, *, timeout):
        requests.append((request, timeout))
        return FakeResponse(b"<html><img src='/mini.jpg'></html>")

    report, raw_html = store.probe_page(PAGE, opener=opener, timeout=9)
    assert requests[0][0].get_header("User-agent") == store.USER_AGENT
    assert requests[0][1] == 9
    assert report["http_status"] == 200
    assert report["image_count"] == 1
    assert raw_html.startswith(b"<html>")
    assert report["html_sha256"]
    assert "downloaded" in report["note"]


@pytest.mark.parametrize(
    "url",
    [
        "http://store.corvusbelli.com/en/product",
        "https://store.corvusbelli.com.evil.example/en/product",
        "https://attacker@store.corvusbelli.com/en/product",
        "https://store.corvusbelli.com:444/en/product",
        "https://store.corvusbelli.com/es/product",
    ],
)
def test_rejects_nonstore_and_insecure_urls_before_request(url) -> None:
    def opener(*_args, **_kwargs):
        raise AssertionError("request should not run")

    with pytest.raises(store.StoreDiscoveryError):
        store.probe_page(url, opener=opener)


def test_redirect_to_other_host_is_rejected() -> None:
    def opener(_request, **_kwargs):
        return FakeResponse(b"<html>test</html>", url="https://not-our-store.test/en/page")

    with pytest.raises(store.StoreDiscoveryError):
        store.probe_page(PAGE, opener=opener)


def test_rejects_non_html_and_oversized_response() -> None:
    def wrong_content_type(_request, **_kwargs):
        return FakeResponse(b"image bytes", mime="image/png")

    with pytest.raises(store.StoreDiscoveryError, match="Content-Type"):
        store.probe_page(PAGE, opener=wrong_content_type)

    def oversized(_request, **_kwargs):
        return FakeResponse(b"x" * 12)

    with pytest.raises(store.StoreDiscoveryError, match="exceeds"):
        store.probe_page(PAGE, opener=oversized, max_bytes=10)


def test_cli_writes_json_without_fetching_images(tmp_path, monkeypatch, capsys) -> None:
    def fake_probe(_url, **_kwargs):
        raw = b"<app-root></app-root>"
        return (
            {
                "resolved_url": PAGE,
                "http_status": 200,
                "html_bytes": len(raw),
                "image_count": 0,
                "page_kind": "spa_shell",
                "images": [],
            },
            raw,
        )

    monkeypatch.setattr(store, "probe_page", fake_probe)
    output = tmp_path / "results.json"
    assert store.main(["--output", str(output), "--save-html"]) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["image_count"] == 0
    assert output.with_suffix(".html").read_bytes() == b"<app-root></app-root>"
    assert "JavaScript application shell" in capsys.readouterr().out
