"""Guard explicitly reviewed canonical Trait-to-Wiki destinations."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.curated import load_curated_directory
from infinity_db.database.repository import Database
from infinity_db.trait_wiki_references import load_trait_wiki_references
from infinity_db.web import create_app
from tools.audit_trait_wiki_anchors import audit_html
from tools.audit_trait_wiki_anchors import main as audit_anchors_main
from tools.verify_ammunition_browser import WIDTHS
from tools.verify_ammunition_browser import verify as verify_catalog_browser
from tools.verify_trait_wiki_browser import _browser_html, _validate_trait_page_response
from tools.verify_traits_catalog_browser import source_traits


def _document(url: str, *, name: str = "Non-Lethal") -> dict:
    return {
        "format": "InfinityDB trait Wiki references",
        "version": 1,
        "entries": {
            "trait:non-lethal": {
                "name": name,
                "url": url,
            }
        },
    }


def test_reviewed_trait_wiki_destinations_are_explicit() -> None:
    mapping = load_trait_wiki_references()

    assert set(mapping) == {
        "trait:anti-materiel",
        "trait:arm-0",
        "trait:aro",
        "trait:bioweapon",
        "trait:boost",
        "trait:bs-weapon-ph",
        "trait:bs-weapon-wip",
        "trait:bts-0",
        "trait:burst-b",
        "trait:burst-single-target",
        "trait:cc",
        "trait:concealed",
        "trait:continuous-damage",
        "trait:deployable",
        "trait:direct-template",
        "trait:disposable-x",
        "trait:double-shot",
        "trait:impact-template",
        "trait:improvised",
        "trait:indiscriminate",
        "trait:intuitive-attack",
        "trait:non-lethal",
        "trait:non-reloadable",
        "trait:perimeter",
        "trait:prior-deployment",
        "trait:reflective",
        "trait:silent-x",
        "trait:speculative-attack",
        "trait:state",
        "trait:suppressive-fire",
        "trait:target-attribute",
        "trait:targetless",
        "trait:zone-of-control-zc",
    }
    assert mapping["trait:continuous-damage"] == {
        "name": "Continuous Damage",
        "url": "https://infinitythewiki.com/Traits#Continuous_Damage",
    }


def test_reviewed_trait_wiki_links_match_current_canonical_records() -> None:
    root = Path(__file__).resolve().parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    traits = {
        record["id"]: record["name"]
        for _, document in documents
        for record in document["records"]
        if record["kind"] == "trait"
    }

    mapping = load_trait_wiki_references()
    assert len(traits) == 33
    assert {record_id: traits[record_id] for record_id in mapping} == {
        record_id: entry["name"] for record_id, entry in mapping.items()
    }
    # All 33 curated Traits now have source-observed fragment mappings.
    assert set(traits) == set(mapping)


def test_punctuation_sensitive_trait_fragments_match_reviewed_html_inventory() -> None:
    # Exact heading IDs from a saved official /Traits HTML audit (35 headings).
    # These are source-observed fragments, not display-name transformations.
    observed = {
        "trait:arm-0": "ARM_.3D_0",
        "trait:bs-weapon-ph": "BS_Weapon_.28PH.29",
        "trait:bs-weapon-wip": "BS_Weapon_.28WIP.29",
        "trait:bts-0": "BTS_.3D_0",
        "trait:burst-b": "Burst_.28B.29",
        "trait:burst-single-target": "Burst:_Single_Target",
        "trait:disposable-x": "Disposable_.28X.29",
        "trait:silent-x": "Silent_.28X.29",
        "trait:suppressive-fire": "Suppressive_Fire_.28SF.29",
        "trait:target-attribute": "Target_.28Attribute.29",
        "trait:zone-of-control-zc": "Zone_of_Control_.28ZoC.29",
    }
    mapping = load_trait_wiki_references()
    assert {
        record_id: mapping[record_id]["url"].split("#", 1)[1]
        for record_id in observed
    } == observed


@pytest.mark.parametrize(
    "url",
    [
        "http://infinitythewiki.com/Traits#Non-Lethal",
        "https://evil.example/Traits#Non-Lethal",
        "https://infinitythewiki.com.evil.example/Traits#Non-Lethal",
        "https://infinitythewiki.com/Weapons_Chart#Non-Lethal",
        "https://infinitythewiki.com/Traits",
        "https://infinitythewiki.com/Traits?oldid=4110#Non-Lethal",
        "https://infinitythewiki.com:443/Traits#Non-Lethal",
    ],
)
def test_trait_wiki_mapping_rejects_unreviewed_destinations(
    tmp_path: Path, url: str
) -> None:
    path = tmp_path / "links.json"
    path.write_text(json.dumps(_document(url)), encoding="utf-8")

    with pytest.raises(ValueError, match="Unreviewed trait Wiki destination"):
        load_trait_wiki_references(path)


def test_trait_wiki_anchor_audit_matches_exact_heading_ids() -> None:
    html = """
        <h3><span class="mw-headline" id="Continuous_Damage">
          Continuous <a href="/Category">Damage</a></span></h3>
        <h3 id="Non-Lethal">Non-Lethal</h3>
    """
    refs = {
        "trait:continuous-damage": {
            "name": "Continuous Damage",
            "url": "https://infinitythewiki.com/Traits#Continuous_Damage",
        },
        "trait:non-lethal": {
            "name": "Non-Lethal",
            "url": "https://infinitythewiki.com/Traits#Non-Lethal",
        },
    }
    result = audit_html(html, refs)
    assert result["matchedCount"] == 2
    assert result["headingCount"] == 2
    assert result["failures"] == []

    refs["trait:non-lethal"]["url"] += "_incorrect"
    refs["trait:continuous-damage"]["name"] = "Unrelated"
    result = audit_html(html, refs)
    assert result["matchedCount"] == 0
    assert {failure["status"] for failure in result["failures"]} == {
        "missing-fragment", "wrong-heading"
    }


def test_trait_wiki_anchor_audit_accepts_legacy_escaped_fragment() -> None:
    html = (
        '<h3><span class="mw-headline" id="Suppressive_Fire_.28SF.29">'
        'Suppressive Fire (SF)</span></h3>'
    )
    result = audit_html(html, {
        "trait:suppressive-fire": {
            "name": "Suppressive Fire (SF)",
            "url": "https://infinitythewiki.com/Traits#Suppressive_Fire_.28SF.29",
        }
    })
    assert result["matchedCount"] == 1
    assert not result["failures"]


def test_trait_wiki_anchor_audit_ignores_edit_controls_and_void_tags() -> None:
    html = (
        '<h3 id="Suppressive_Fire_.28SF.29">'
        '<span class="mw-headline" id="Suppressive_Fire_.28SF.29">'
        'Suppressive <img src="symbol.svg">Fire (SF)</span>'
        '<span class="mw-editsection">[<a href="/edit">edit</a>]</span></h3>'
    )
    report = audit_html(html, {
        "trait:suppressive-fire": {
            "name": "Suppressive Fire (SF)",
            "url": "https://infinitythewiki.com/Traits#Suppressive_Fire_.28SF.29",
        }
    })
    assert report["matchedCount"] == 1
    assert report["failures"] == []


def test_unmapped_trait_candidates_use_exact_html_ids_without_guessing() -> None:
    html = (
        '<h3 id="Boost">Boost</h3>'
        '<h3 id="ARM_.3D_0">ARM = 0</h3>'
        '<h3 id="Duplicate_A">Duplicate</h3>'
        '<h3 id="Duplicate_B">Duplicate</h3>'
    )
    report = audit_html(html, {
        "trait:boost": {
            "name": "Boost", "url": "https://infinitythewiki.com/Traits#Boost",
        }
    }, {
        "trait:boost": "Boost",
        "trait:arm-0": "ARM = 0",
        "trait:duplicate": "Duplicate",
        "trait:missing": "Missing",
    })
    assert report["matchedCount"] == 1
    assert report["unmappedReview"] == [
        {
            "traitId": "trait:arm-0", "name": "ARM = 0",
            "headingIds": ["ARM_.3D_0"], "status": "review-candidate",
        },
        {
            "traitId": "trait:duplicate", "name": "Duplicate",
            "headingIds": ["Duplicate_A", "Duplicate_B"], "status": "ambiguous-heading",
        },
        {
            "traitId": "trait:missing", "name": "Missing",
            "headingIds": [], "status": "missing-heading",
        },
    ]


def test_trait_wiki_anchor_audit_fails_closed_with_json_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from tools import audit_trait_wiki_anchors as audit

    html_path = tmp_path / "traits.html"
    output = tmp_path / "anchors.json"
    html_path.write_text('<h3 id="Other">Other</h3>', encoding="utf-8")
    monkeypatch.setattr(audit, "load_trait_wiki_references", lambda: {
        "trait:non-lethal": {
            "name": "Non-Lethal",
            "url": "https://infinitythewiki.com/Traits#Non-Lethal",
        }
    })
    assert audit_anchors_main([str(html_path), "--output", str(output)]) == 1
    assert "0/1 matched" in capsys.readouterr().out
    assert json.loads(output.read_text(encoding="utf-8"))["failures"][0][
        "status"
    ] == "missing-fragment"


def test_trait_wiki_anchor_cli_inventories_unmapped_without_publishing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import hashlib

    from infinity_db import curated
    from tools import audit_trait_wiki_anchors as audit

    html = '<h3 id="Boost">Boost</h3><h3 id="ARM_.3D_0">ARM = 0</h3>'
    path = tmp_path / "wiki.html"
    path.write_text(html, encoding="utf-8")
    output = tmp_path / "report.json"
    monkeypatch.setattr(audit, "load_trait_wiki_references", lambda: {
        "trait:boost": {
            "name": "Boost",
            "url": "https://infinitythewiki.com/Traits#Boost",
        }
    })
    monkeypatch.setattr(curated, "load_curated_directory", lambda _: [(
        Path("test.json"),
        {"records": [
            {"kind": "trait", "id": "trait:boost", "name": "Boost"},
            {"kind": "trait", "id": "trait:arm-0", "name": "ARM = 0"},
        ]},
    )])
    assert audit_anchors_main([
        str(path), "--inventory-unmapped", "--output", str(output)
    ]) == 0
    assert "trait:arm-0: review-candidate" in capsys.readouterr().out
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["sourceSha256"] == hashlib.sha256(html.encode("utf-8")).hexdigest()
    assert report["unmappedReview"] == [{
        "traitId": "trait:arm-0",
        "name": "ARM = 0",
        "headingIds": ["ARM_.3D_0"],
        "status": "review-candidate",
    }]


def test_trait_page_exposes_a_player_visible_source_link() -> None:
    root = Path(__file__).resolve().parents[1]
    template = (root / "src/infinity_db/web/static/traits-detail.html").read_text(
        encoding="utf-8"
    )
    javascript = (root / "src/infinity_db/web/static/catalog-detail.js").read_text(
        encoding="utf-8"
    )
    assert 'id="trait-wiki-link"' in template
    assert 'target="_blank" rel="noopener noreferrer" hidden' in template
    assert '<p class="intro-copy"><a id="trait-wiki-link"' in template
    assert 'const traitWikiLink = document.getElementById("trait-wiki-link");' in javascript
    assert 'traitWikiLink.hidden = !item.wiki;' in javascript
    assert 'if (item.wiki) traitWikiLink.href = item.wiki;' in javascript


def test_trait_browser_verifier_rejects_wrong_or_stale_target() -> None:
    with pytest.raises(RuntimeError, match="HTTP 404 for /traits/boost"):
        _validate_trait_page_response(404, "not found", "http://localhost:8080")

    with pytest.raises(RuntimeError, match="does not serve the current Trait detail template"):
        _validate_trait_page_response(
            200,
            '<body data-catalog="traits"><p id="item-meta"></p></body>',
            "http://localhost:8080",
        )

    _validate_trait_page_response(
        200,
        '<body data-catalog="traits"><a id="trait-wiki-link"></a></body>',
        "http://localhost:8080",
    )


def test_published_traits_reconcile_curated_rules_army_usage_and_public_api() -> None:
    """Audit all canonical Traits without misclassifying raw Army properties."""

    root = Path(__file__).resolve().parents[1]
    army_db = root / "data/generated/infinity.db"
    rules_db = root / "data/generated/rules.db"
    curated = {
        record["id"]: (document["collection"]["id"], record)
        for _, document in load_curated_directory(root / "data/curated")
        if document["collection"]["status"] == "current"
        for record in document["records"]
        if record["kind"] == "trait"
    }
    mapping = load_trait_wiki_references()
    assert len(curated) == 33
    assert set(mapping) == set(curated)
    assert source_traits(root) == {
        identity.removeprefix("trait:"): source["name"]
        for identity, (_, source) in curated.items()
    }
    assert WIDTHS == (1440, 390, 320)
    with pytest.raises(ValueError, match="Traits require a complete reviewed Wiki"):
        verify_catalog_browser(
            "http://127.0.0.1:8000",
            catalog="traits",
            expected_names=source_traits(root),
        )

    with sqlite3.connect(rules_db) as connection:
        published = list(connection.execute(
            "SELECT r.collection_id, r.id, r.name, r.summary, r.facts_json "
            "FROM records AS r JOIN collections AS c ON c.id = r.collection_id "
            "WHERE c.status = 'current' AND r.kind = 'trait'"
        ))
    assert {record_id for _, record_id, *_ in published} == set(curated)
    for collection_id, record_id, name, summary, facts in published:
        expected_collection, source = curated[record_id]
        assert (collection_id, name, summary, json.loads(facts or "{}")) == (
            expected_collection, source["name"], source["summary"], source.get("facts", {})
        ), record_id

    app = create_app(army_db, rules_database_path=rules_db)

    def get(path: str) -> tuple[str, bytes]:
        environ: dict[str, Any] = {}
        setup_testing_defaults(environ)
        environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
        statuses: list[str] = []

        def respond(status: str, _headers: list, _exc_info: object = None) -> None:
            statuses.append(status)

        response = app(environ, respond)
        try:
            content = b"".join(response)
        finally:
            close = getattr(response, "close", None)
            if close is not None:
                close()
        assert len(statuses) == 1, path
        return statuses[0], content

    status, body = get("/api/traits")
    assert status == "200 OK"
    items = json.loads(body)["items"]
    by_slug = {item["slug"]: item for item in items}
    assert len(by_slug) == len(items)
    canonical_slugs = {record_id.removeprefix("trait:") for record_id in curated}
    assert canonical_slugs <= set(by_slug)

    # Any noncanonical entry must be a real unresolved Army property.
    raw_slugs = {item["slug"] for item in Database(army_db).list_traits()}
    assert set(by_slug) - canonical_slugs <= raw_slugs

    status, body = get("/traits")
    assert status == "200 OK"
    assert b'data-catalog="traits"' in body
    assert b"/static/catalog-list.js" in body

    for record_id, (_, source) in sorted(curated.items()):
        slug = record_id.removeprefix("trait:")
        item = by_slug[slug]
        assert (item["id"], item["name"], item["description"]) == (
            slug, source["name"], source["summary"]
        ), record_id
        assert isinstance(item["use_count"], int) and item["use_count"] >= 0

        status, body = get(f"/api/traits/{slug}")
        assert status == "200 OK", record_id
        detail = json.loads(body)
        assert (detail["id"], detail["slug"], detail["name"], detail["description"]) == (
            slug, slug, source["name"], source["summary"]
        ), record_id
        assert detail["use_count"] == item["use_count"], record_id
        assert detail["wiki"] == mapping[record_id]["url"], record_id
        assert len(detail["rules"]) == 1, record_id
        rule = detail["rules"][0]
        assert (rule["id"], rule["summary"], rule.get("facts") or {}) == (
            record_id, source["summary"], source.get("facts") or {}
        ), record_id
        assert rule["citations"], record_id
        assert {citation["source_id"] for citation in rule["citations"]} >= {
            citation["sourceId"] for citation in source["citations"]
        }, record_id
        assert all(
            variant["catalog"] in {"skills", "equipment", "weapons"}
            and isinstance(variant["units"], list)
            for variant in detail["variants"]
        ), record_id
        usage_keys = [(variant["catalog"], variant["item_id"]) for variant in detail["variants"]]
        assert len(usage_keys) == len(set(usage_keys)), record_id

        status, body = get(f"/traits/{slug}")
        assert status == "200 OK", record_id
        assert b'data-catalog="traits"' in body
        assert b"/static/catalog-detail.js" in body
        assert b'id="trait-wiki-link"' in body
        assert b'id="item-content"' in body


def test_current_trait_routes_are_served_by_presentation_handler() -> None:
    from infinity_db.web.presentation import PresentationHandler

    presentation = PresentationHandler(
        source_data_changed_on=None,
        snapshot_downloaded_on=None,
        snapshot_revision="test",
    )
    for trait_id in load_trait_wiki_references():
        slug = trait_id.removeprefix("trait:")
        response = presentation.handle(f"/traits/{slug}", "")
        assert response is not None, slug
        assert response.status.value == 200, slug
        assert b'id="trait-wiki-link"' in response.body, slug


def test_browser_fixture_adds_scroll_space_without_changing_headings() -> None:
    original = '<html><body><h3 id="ARM_.3D_0">ARM = 0</h3></body></html>'
    instrumented = _browser_html(original)
    assert instrumented.count('<h3 id="ARM_.3D_0">ARM = 0</h3>') == 1
    assert instrumented.index('height:2000px') < instrumented.index("</body>")
    assert instrumented.endswith("</html>")


def test_trait_wiki_mapping_rejects_unreviewed_ids_and_shapes(tmp_path: Path) -> None:
    path = tmp_path / "links.json"
    document = _document("https://infinitythewiki.com/Traits#Non-Lethal")
    document["entries"]["trait:non-lethal"]["unknown"] = "ignored"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid trait Wiki entry"):
        load_trait_wiki_references(path)

    document["entries"] = {"equipment:non-lethal": document["entries"]["trait:non-lethal"]}
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid trait Wiki reference ID"):
        load_trait_wiki_references(path)
