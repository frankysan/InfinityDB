"""Shared source/API/ordinary-browser assertions for reference acceptance."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pymupdf

from infinity_db.curated import load_curated_document
from infinity_db.rules_database import RulesDatabase
from infinity_db.web import create_app
from tools.browser_wsgi_transport import route_browser_page, wsgi_response
from tools.research.source_paths import pinned_pdf_path

ROOT = Path(__file__).resolve().parents[1]
PDF_LABEL = "data/pdf/rules/n5-rules-v5.3-en.pdf"
PDF = ROOT / "local/data/pdf" / Path(PDF_LABEL).relative_to("data/pdf")
PIN = "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
FAQ_LABEL = "data/pdf/faq/n5-faq-v0.1-en.pdf"
FAQ_PIN = "7bf26b7d039db7826ef5500b1a2159fe54855b4e632133cab416becee65b85aa"
WIKI = ROOT / "local/data/wiki/WIKI-en 20260926-200832.zip"
WIKI_PIN = "c0fe18c165473e3f273efd58aa7ecb0ea0d94ee274189de9361aad175b3de987"
RULES = ROOT / "data/generated/rules_n5.db"
ORIGIN = "http://infinitydb-source-acceptance.test"


def app() -> Any:
    return create_app(ROOT / "data/generated/army.db", rules_database_path=RULES)


def records(name: str = "n5-core-v5.3.json") -> dict[str, Any]:
    document = load_curated_document(ROOT / "data/curated/rules" / name)
    return {r["id"]: r for r in document["records"]}


def selected_pdf(
    label: str, pin: str, *, layout: str = "local", root: Path = ROOT,
) -> Path | None:
    """Only the chosen pinned PDF; missing sources remain missing, never fall back."""
    return pinned_pdf_path(root, label, pin, layout=layout, missing_ok=True)


def pdf_pages(
    pages: tuple[int, ...], *, pdf_path: Path = PDF, pin: str = PIN,
) -> dict[int, str]:
    assert hashlib.sha256(pdf_path.read_bytes()).hexdigest() == pin
    with pymupdf.open(pdf_path) as document:
        return {n: " ".join(str(document[n - 1].get_text("text")).casefold().split())
                for n in pages}


def api(path: str) -> dict[str, Any]:
    status, _headers, body = wsgi_response(app(), ORIGIN + path)
    assert status == 200, path
    return json.loads(body)


def published(identity: str, path: str, authored: dict[str, Any]) -> dict[str, Any]:
    stored = RulesDatabase(RULES).composed_record(identity)
    assert stored is not None
    response = api(path)
    rule = next(r for r in response["rules"] if r["id"] == identity)
    for field in ("summary", "facts", "review"):
        assert stored[field] == authored[field], (identity, field)
    for field in ("summary", "facts"):
        assert rule[field] == authored[field], (identity, field)
    expected = [(c["sourceId"], c.get("page"), c.get("member"),
                 c.get("section"), c.get("heading")) for c in authored["citations"]]
    for value in (stored, rule):
        assert [(c["source_id"], c.get("page"), c.get("member"),
                 c.get("section"), c.get("heading")) for c in value["citations"]] == expected
    return rule


def browse(browser: Any, width: int, catalog: str, slug: str, identity: str,
           phrases: tuple[str, ...], links: tuple[str, ...]) -> None:
    page = browser.new_page(viewport={"width": width, "height": 900})
    page.add_init_script("localStorage.setItem('infinity-db-developer-mode', 'false')")
    route_browser_page(page, app(), ORIGIN)
    errors: list[str] = []
    failed: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("requestfailed", lambda request: failed.append(request.url))
    page.on("response", lambda response: failed.append(f"{response.status} {response.url}")
            if response.status >= 400 else None)
    route = f"/{catalog}/{slug}"
    try:
        response = page.goto(f"{ORIGIN}/{catalog}", wait_until="domcontentloaded")
        assert response is not None and response.status == 200
        link = page.locator(f'#catalog-list a[href="{route}"]').first
        link.wait_for(state="visible", timeout=30000)
        link.focus()
        link.press("Enter")
        page.wait_for_url(ORIGIN + route, timeout=30000)
        card = page.locator("#rule-" + identity.replace(":", "-"))
        card.wait_for(state="visible", timeout=30000)
        text = card.inner_text()
        for phrase in phrases:
            assert phrase in text, (width, route, phrase, text)
        payload = page.evaluate("async () => (await fetch('/api' + location.pathname)).json()")
        rule = next(r for r in payload["rules"] if r["id"] == identity)
        assert rule["facts"] and rule["citations"]
        assert page.evaluate("() => document.documentElement.dataset.developerMode") == "false"
        assert page.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1")
        for destination in links:
            assert card.locator(f'a[href="{destination}"]').count() > 0, destination
        if links:
            target = card.locator(f'a[href="{links[0]}"]').first
            target.focus()
            target.press("Enter")
            page.wait_for_url(ORIGIN + links[0], timeout=30000)
            assert page.evaluate("() => document.documentElement.scrollWidth <= innerWidth + 1")
        assert not errors and not failed, (width, route, errors, failed)
    finally:
        page.close()
