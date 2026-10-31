"""Published cross-domain rule-relation destinations must resolve in normal APIs."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.database import Database
from infinity_db.domain_references import enrich_rule_relation_references
from infinity_db.rules_database import RulesDatabase
from infinity_db.web import create_app


def _get(app: Any, path: str) -> tuple[str, bytes]:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
    statuses: list[str] = []

    def start_response(
        status: str, headers: list[tuple[str, str]], exc_info: Any = None,
    ) -> None:
        statuses.append(status)

    response = app(environ, start_response)
    try:
        body = b"".join(response)
    finally:
        close = getattr(response, "close", None)
        if close is not None:
            close()
    assert len(statuses) == 1
    return statuses[0], body


RELATION_SOURCE_KINDS = (
    "ammunition", "equipment", "hacking-program", "rule",
    "skill", "state", "trait", "weapon",
)
RELATION_ROUTE_CATALOGS = (
    "ammunition", "equipment", "hacking-programs", "rules",
    "skills", "states", "traits", "weapons",
)


@pytest.fixture(scope="module")
def relation_destinations() -> tuple[Any, dict[tuple[str, str], set[str]]]:
    """Collect the full published relation inventory once per pytest worker."""
    root = Path(__file__).resolve().parents[1]
    army_path = root / "data/generated/infinity.db"
    rules_path = root / "data/generated/rules.db"
    database = Database(army_path)
    rules = RulesDatabase(rules_path)
    app = create_app(army_path, rules_database_path=rules_path)
    records = [
        record
        for kind in RELATION_SOURCE_KINDS
        for record in rules.composed_records_by_kind(kind)
    ]
    enriched = enrich_rule_relation_references(database, {"records": records})
    targets: dict[tuple[str, str], set[str]] = defaultdict(set)
    for owner in enriched["records"]:
        for relation in owner.get("display_relations", []):
            if "presentation" not in relation:
                continue  # Structural variants are not rendered as links.
            reference = relation["record"].get("public_reference", {})
            if "catalog" not in reference:
                continue  # Embedded or deliberately unlinked source variants.
            targets[(reference["catalog"], reference["id"])].add(owner["id"])
    assert len(targets) >= 40, len(targets)
    assert {catalog for catalog, _ in targets} <= set(RELATION_ROUTE_CATALOGS)
    return app, targets


@pytest.mark.parametrize("catalog", RELATION_ROUTE_CATALOGS)
def test_published_cross_domain_relation_catalog_destinations_resolve(
    relation_destinations: tuple[Any, dict[tuple[str, str], set[str]]], catalog: str,
) -> None:
    app, targets = relation_destinations
    failures: dict[str, list[str]] = {}
    for (target_catalog, slug), owners in sorted(targets.items()):
        if target_catalog != catalog:
            continue
        api_path = f"/api/{catalog}/{slug}"
        detail_path = f"/{catalog}/{slug}"
        status, _ = _get(app, api_path)
        if status != "200 OK":
            failures[api_path] = sorted(owners)
        # A valid JSON endpoint alone does not make a player-facing link
        # usable; the normal detail route must serve the matching catalog.
        page_status, page = _get(app, detail_path)
        # Skills and Hacking Programs have dedicated detail renderers;
        # other domains bind their generic renderer via body data-catalog.
        dedicated_scripts = {
            "skills": b"/static/skill.js",
            "hacking-programs": b"/static/hacking-program-detail.js",
        }
        marker = dedicated_scripts.get(
            catalog, f'data-catalog="{catalog}"'.encode()
        )
        if page_status != "200 OK" or marker not in page:
            failures[detail_path] = sorted(owners)
    assert not failures, failures


def test_embedded_glossary_entries_target_their_client_generated_anchors() -> None:
    root = Path(__file__).resolve().parents[1]
    army_path = root / "data/generated/infinity.db"
    rules_path = root / "data/generated/rules.db"
    app = create_app(army_path, rules_database_path=rules_path)
    status, body = _get(app, "/api/glossary")
    assert status == "200 OK"
    entries = [
        entry for entry in json.loads(body)["items"]
        if entry.get("embedded")
    ]
    assert len(entries) >= 10, len(entries)
    assert len({entry["id"] for entry in entries}) == len(entries)
    for entry in entries:
        assert entry["href"] == "/glossary#" + entry["id"].replace(":", "-"), entry

    status, page = _get(app, "/glossary")
    assert status == "200 OK"
    assert b"glossary.js" in page
    status, script = _get(app, "/static/glossary.js")
    assert status == "200 OK"
    assert b'item.id.replaceAll(":", "-")' in script
    assert b"article.id = anchorId(item)" in script


def test_glossary_weapon_family_fragments_have_a_real_host_rule_card() -> None:
    root = Path(__file__).resolve().parents[1]
    army_path = root / "data/generated/infinity.db"
    rules_path = root / "data/generated/rules.db"
    app = create_app(army_path, rules_database_path=rules_path)
    status, body = _get(app, "/api/glossary")
    assert status == "200 OK"
    anchored = [
        item for item in json.loads(body)["items"]
        if item["href"].startswith("/weapons/") and "#rule-" in item["href"]
    ]
    assert anchored, "No hosted Weapon family rule cards found"
    for item in anchored:
        url = urlsplit(item["href"])
        status, body = _get(app, "/api" + url.path)
        assert status == "200 OK", item["href"]
        hosted = json.loads(body)
        target = url.fragment
        anchors = {
            "rule-" + record["id"].replace(":", "-")
            for record in hosted["rules"]
        }
        assert target in anchors, (item["id"], item["href"], sorted(anchors))
        assert _get(app, url.path)[0] == "200 OK"

    status, script = _get(app, "/static/rules-reference.js")
    assert status == "200 OK"
    assert b'if (rule.id) article.id = `rule-${rule.id.replaceAll(":", "-")}`' in script


def _local_rule_fragments(value: Any) -> list[str]:
    """Collect local rule-card links from API relation and text tokens."""
    if isinstance(value, dict):
        reference = value.get("public_reference")
        found = (
            [reference["href"]]
            if isinstance(reference, dict)
            and isinstance(reference.get("href"), str)
            and reference["href"].startswith("#rule-")
            else []
        )
        return found + [
            href for child in value.values()
            for href in _local_rule_fragments(child)
        ]
    if isinstance(value, list):
        return [href for child in value for href in _local_rule_fragments(child)]
    return []


def test_all_published_weapon_local_fragments_match_hosted_cards() -> None:
    root = Path(__file__).resolve().parents[1]
    app = create_app(
        root / "data/generated/infinity.db",
        rules_database_path=root / "data/generated/rules.db",
    )
    status, body = _get(app, "/api/weapons")
    assert status == "200 OK"
    items = json.loads(body)["items"]
    slugs = {item["slug"] for item in items}
    assert len(slugs) == len(items), "Public Weapon catalog has duplicate slugs"
    assert len(slugs) >= 50, "Public Weapon catalog unexpectedly sparse"

    observed: set[str] = set()
    linked_pages: set[str] = set()
    for slug in sorted(slugs):
        status, body = _get(app, f"/api/weapons/{slug}")
        assert status == "200 OK", slug
        payload = json.loads(body)
        rules = payload.get("rules", [])
        hosted = {"#rule-" + rule["id"].replace(":", "-") for rule in rules}
        assert len(hosted) == len(rules), slug
        links = set(_local_rule_fragments(payload))
        assert links <= hosted, (slug, sorted(links - hosted))
        if links:
            linked_pages.add(slug)
            assert _get(app, f"/weapons/{slug}")[0] == "200 OK"
        observed.update(links)

    assert "ap-mine" in linked_pages, sorted(linked_pages)
    assert "#rule-weapon-mines" in observed, sorted(observed)

