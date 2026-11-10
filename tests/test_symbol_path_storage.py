"""Army v31 symbol lookup, asset integrity and per-application cache identity."""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from storage_fixture_support import copy_base_army

from infinity_db.army_reference_storage import publish_army_reference_data
from infinity_db.database.health import database_health_report
from infinity_db.database.publication import validate_database_pair
from infinity_db.database.repository import Database
from infinity_db.equipment_presentation_storage import publish_equipment_encodings
from infinity_db.skill_classification_storage import publish_skill_classifications
from infinity_db.symbol_catalog import SymbolCatalog, SymbolCatalogError
from infinity_db.symbol_path_storage import MAPPING_FIELDS, publish_symbol_paths
from infinity_db.unit_filter_storage import publish_unit_filter_semantics
from infinity_db.web import create_app
from infinity_db.web.presentation import static_asset_revision
from tools.browser_wsgi_transport import route_browser_page, wsgi_response

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/generated"
MANIFEST = ROOT / "data/manifests/symbol-publication.json"
STATIC = ROOT / "src/infinity_db/web/static"


@pytest.fixture(scope="module")
def base_v30(tmp_path_factory) -> tuple[Path, Path]:
    directory = tmp_path_factory.mktemp("symbol-base")
    army, raw = directory / "army.db", directory / "army.raw.db"
    copy_base_army(army)
    copy_base_army(raw)
    publish_equipment_encodings(
        army, raw, ROOT / "config/catalogs/equipment-presentation-encodings.json",
    )
    publish_skill_classifications(
        army, raw, ROOT / "config/catalogs/skill-source-classifications.json",
    )
    publish_unit_filter_semantics(army, raw, ROOT / "config/catalogs/unit-filter-semantics.json")
    publish_army_reference_data(
        army, raw, ROOT / "data/curated/identities/army-overview.json",
        ROOT / "data/curated/identities/legacy-armies.json",
    )
    return army, raw


@pytest.fixture
def v30(base_v30, tmp_path: Path) -> tuple[Path, Path]:
    paths = tmp_path / "army.db", tmp_path / "army.raw.db"
    for source, target in zip(base_v30, paths, strict=True):
        shutil.copyfile(source, target)
    return paths


@pytest.fixture
def v31(v30) -> tuple[Path, Path]:
    army, raw = v30
    publish_symbol_paths(army, raw, MANIFEST, STATIC)
    return army, raw


def test_exact_mapping_roundtrip_and_paired_health(v31) -> None:
    army, raw = v31
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    actual = Database(army).symbol_publication()
    assert actual is not None
    assert {field: actual[field] for field in MAPPING_FIELDS} == {
        field: document[field] for field in MAPPING_FIELDS
    }
    assert actual["publishedSha256ByPath"] == document["publishedSha256ByPath"]
    assert sum(len(actual[field]) for field in MAPPING_FIELDS) == 2019
    assert len(actual["publishedSha256ByPath"]) == 808
    assert SymbolCatalog(publication=actual).revision == SymbolCatalog(MANIFEST).revision
    assert validate_database_pair(army, raw_path=raw) is not None
    health = database_health_report(army, require_raw=True)
    assert health["status"] == "healthy"
    assert health["application"]["schemaRevision"] == 31
    assert health["application"]["compatibilityRevision"] == 40
    assert Database(RELEASE / "army.db").symbol_publication() == actual


def test_http_symbol_parity_and_fresh_start_without_manifest(v31) -> None:
    paths = ("/api/armies", "/api/units?limit=200")
    previous, current = create_app(RELEASE / "army.db"), create_app(v31[0])
    for path in paths:
        before_status, _headers, before = wsgi_response(previous, "http://symbol.test" + path)
        status, _headers, after = wsgi_response(current, "http://symbol.test" + path)
        assert status == before_status
        assert json.loads(after) == json.loads(before)
    code = """
from pathlib import Path
import sys
original_text, original_bytes = Path.read_text, Path.read_bytes
def guard(method):
    def read(path, *args, **kwargs):
        if path.name == 'symbol-publication.json':
            raise AssertionError('Runtime attempted a manifest read')
        return method(path, *args, **kwargs)
    return read
Path.read_text, Path.read_bytes = guard(original_text), guard(original_bytes)
from infinity_db.web import create_app
app = create_app(Path(sys.argv[1]))
assert app.symbol_catalog.army_path(101)
assert app.presentation.static_revision
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(v31[0])], capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_selected_mappings_have_independent_cache_versions(v31, base_v30, tmp_path: Path) -> None:
    directory = tmp_path / "alternative"
    directory.mkdir()
    army, raw = directory / "army.db", directory / "army.raw.db"
    for source, target in zip(base_v30, (army, raw), strict=True):
        shutil.copyfile(source, target)
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    document[MAPPING_FIELDS[0]]["101"] = document[MAPPING_FIELDS[0]]["201"]
    source = directory / "alternative.json"
    source.write_text(json.dumps(document), encoding="utf-8")
    publish_symbol_paths(army, raw, source, STATIC)
    first, second = create_app(v31[0]), create_app(army)
    assert first.presentation.static_version != second.presentation.static_version
    for app in (first, second, first):
        version = app.presentation.static_version
        status, _headers, body = wsgi_response(app, "http://symbol.test/armies")
        assert status == 200 and f"?v={version}".encode() in body
        status, headers, body = wsgi_response(
            app, f"http://symbol.test/static/armies.js?v={version}",
        )
        assert status == 200 and "immutable" in dict(headers)["Cache-Control"]
        assert f"?v={version}".encode() in body
    assert first.symbol_catalog.army_path(101) != second.symbol_catalog.army_path(101)


@pytest.mark.parametrize("mutation", ("missing", "hash"))
def test_cache_revision_rejects_incorrect_packaged_assets(v31, monkeypatch, mutation: str) -> None:
    import infinity_db.web.presentation as presentation

    symbols = SymbolCatalog(publication=Database(v31[0]).symbol_publication())
    actual = dict(presentation._packaged_static_hashes())
    path = next(iter(symbols.asset_hashes))
    if mutation == "missing":
        actual.pop(path)
    else:
        actual[path] = "0" * 64
    monkeypatch.setattr(presentation, "_packaged_static_hashes", lambda: actual)
    with pytest.raises(SymbolCatalogError):
        static_asset_revision(symbols)


def test_legacy_asset_free_reference_serving_preserves_integrity(monkeypatch) -> None:
    import infinity_db.web.presentation as presentation

    symbols = SymbolCatalog(MANIFEST)
    actual = dict(presentation._packaged_static_hashes())
    path = next(iter(symbols.asset_hashes))
    actual.pop(path)
    monkeypatch.setattr(presentation, "_packaged_static_hashes", lambda: actual)
    assert static_asset_revision(symbols)
    actual[path] = "0" * 64
    with pytest.raises(SymbolCatalogError):
        static_asset_revision(symbols)


@pytest.mark.parametrize("mutation", (
    "archive", "unpublished", "hash", "traversal", "backslash", "unknown-assets",
))
def test_build_rejects_unbound_or_unsafe_inputs(v30, tmp_path: Path, mutation: str) -> None:
    army, raw = v30
    before = army.read_bytes(), raw.read_bytes()
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if mutation == "archive":
        document["sourceSnapshot"]["armyArtifact"]["sha256"] = "0" * 64
    elif mutation == "hash":
        document["publishedSha256ByPath"][next(iter(document["publishedSha256ByPath"]))] = "0" * 64
    elif mutation == "unknown-assets":
        document["publishedSha256ByPath"]["units/missing.svg"] = "0" * 64
    else:
        document[MAPPING_FIELDS[0]]["101"] = {
            "unpublished": "units/unpublished.svg", "traversal": "units/../outside.svg",
            "backslash": "units/bad\\outside.svg",
        }[mutation]
    source = tmp_path / "invalid.json"
    source.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError):
        publish_symbol_paths(army, raw, source, STATIC)
    assert (army.read_bytes(), raw.read_bytes()) == before


@pytest.mark.parametrize("sql", (
    "DELETE FROM published_symbol_paths WHERE kind='profileIdentityToPublishedPath'",
    "UPDATE published_symbol_paths SET path='units/unknown.svg' WHERE identity='101'",
    "UPDATE published_symbol_assets SET sha256=printf('%064d',0)",
    "UPDATE symbol_path_metadata SET army_archive_sha256=printf('%064d',0)",
    "UPDATE symbol_path_metadata SET content_sha256=printf('%064d',0)",
))
def test_corrupt_rows_fail_closed(v31, sql: str) -> None:
    army, _raw = v31
    with sqlite3.connect(army) as connection:
        connection.execute(sql)
    with pytest.raises(ValueError):
        Database(army).symbol_publication()
    with pytest.raises(ValueError):
        Database(army).validate()


@pytest.mark.parametrize("width", (390, 1280))
def test_v31_army_browser_loads_matching_modules_and_symbols(v31, width: int) -> None:
    sync = pytest.importorskip("playwright.sync_api")
    app = create_app(v31[0])
    origin = "http://symbol-browser.test"
    status, _headers, body = wsgi_response(app, origin + "/api/armies")
    assert status == 200
    expected = sum(
        item["playable"] is not False or item.get("legacy", False)
        for item in json.loads(body)["items"]
    )
    with sync.sync_playwright() as driver:
        try:
            browser = driver.chromium.launch(channel="chrome")
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or "not found" in str(exc):
                pytest.skip(f"Chromium unavailable: {exc}")
            raise
        page = browser.new_page(viewport={"width": width, "height": 900})
        errors: list[str] = []
        failed: list[str] = []
        http_errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("requestfailed", lambda request: failed.append(request.url))
        page.on("response", lambda response: http_errors.append(response.url)
                if response.status >= 400 else None)
        route_browser_page(page, app, origin)
        try:
            page.goto(origin + "/armies", wait_until="networkidle")
            sync.expect(page.locator(".army-overview-card")).to_have_count(expected)
            assert page.locator("html").get_attribute("data-static-version") == (
                app.presentation.static_version
            )
            assert page.evaluate("""() => [...document.querySelectorAll('.army-overview-symbol')]
                .every(image => image.complete && image.naturalWidth > 0)""")
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth + 1"
            )
            assert not errors, errors
            assert not failed, failed
            assert not http_errors, http_errors
        finally:
            browser.close()
