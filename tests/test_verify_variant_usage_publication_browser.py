"""Pinned cross-Army exact-variant publication and normal-browser acceptance.

Requires the ignored raw Army export and an explicitly built local publication.
The release gate must run without skips on the matching release pair.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest

from infinity_db.variant_usage import build_variant_usage_projection
from infinity_db.variant_usage_reference import (
    load_variant_usage_publication,
    publication_from_candidate,
)
from infinity_db.web import create_app
from tools.browser_wsgi_transport import route_browser_page, wsgi_response

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/generated"
ORIGIN = "http://variant-publication-acceptance.test"


def _get_json(app: Any, path: str) -> dict[str, Any]:
    status, _, body = wsgi_response(app, ORIGIN + path)
    assert status == 200, (path, status, body[:500])
    result: dict[str, Any] = json.loads(body)
    return result


@pytest.fixture(scope="module")
def published_pair(requires_pinned_raw_army_archive: None) -> dict[str, Any]:
    """Full pinned source parity: never silently rebuild a stale publication."""
    army = DATA / "infinity.db"
    raw = DATA / "infinity.raw.db"
    rules = DATA / "rules.db"
    publication = DATA / "variant-usage.json"
    assert publication.is_file(), (
        "V1S-066 requires an explicit tools.build_variant_usage --publish before acceptance"
    )
    candidate = build_variant_usage_projection(army, raw, rules)
    expected = publication_from_candidate(candidate)
    expected_bytes = (
        json.dumps(expected, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    assert publication.read_bytes() == expected_bytes, (
        "Published exact-variant bytes are stale or differ from source-pair regeneration"
    )
    loaded = load_variant_usage_publication(publication, army, rules)
    assert loaded == expected
    app = create_app(army, rules_database_path=rules)
    assert app.variant_usage == expected
    return {"app": app, "candidate": candidate, "publication": expected}


def _rule_ids(item: dict[str, Any]) -> set[str]:
    result = {rule["id"] for rule in item.get("rules", [])}
    for variant in item.get("variants", []):
        result.update(rule["id"] for rule in variant.get("rules", []))
    return result


def test_variant_usage_full_source_rows_and_canonical_api_parity(
    published_pair: dict[str, Any],
) -> None:
    app = published_pair["app"]
    candidate = published_pair["candidate"]
    publication = published_pair["publication"]
    groups = publication["variants"]
    assert groups and {row["catalog"] for group in groups
                       for row in group["sourceRows"]} == {"skills", "equipment"}

    resolved = {
        tuple(row["sourceKey"]) for group in groups for row in group["sourceRows"]
    }
    unresolved = {
        (row["catalog"], row["ownerKind"], row["occurrenceId"])
        for row in candidate["unresolvedSourceRows"]
    }
    assert len(resolved) == sum(group["sourceRelationshipRows"] for group in groups)
    assert resolved.isdisjoint(unresolved)
    assert len(unresolved) == len(candidate["unresolvedSourceRows"])

    by_record: dict[str, list[dict[str, Any]]] = {}
    for group in groups:
        record_id = group["variant"]["recordId"]
        by_record.setdefault(record_id, []).append(group)
        contexts = [
            row["context"] for row in group["sourceRows"]
            if row["context"]["applicationArmyId"] is not None
        ]
        assert group["uniqueUnits"] == len({
            ctx["logicalUnitId"] for ctx in contexts
        })
        assert group["uniqueArmyUnits"] == len({
            (ctx["applicationArmyId"], ctx["logicalUnitId"]) for ctx in contexts
        })
        assert group["uniqueUnits"] <= group["uniqueArmyUnits"]
        assert group["sourceRelationshipRows"] >= group["uniqueArmyUnits"]

    for record_id, expected in by_record.items():
        payload = _get_json(
            app, f"/api/variant-usage?record_id={quote(record_id, safe='')}"
        )
        assert payload["scope"] == "exact-reviewed-source-variants"
        assert payload["sourceSnapshot"] == publication["sourceSnapshot"]
        assert payload["items"] == expected
    assert sum(len(items) for items in by_record.values()) == len(groups)


def test_variant_usage_every_group_has_a_canonical_owner(
    published_pair: dict[str, Any],
) -> None:
    """Any published group must be discoverable from a canonical catalog detail."""
    app = published_pair["app"]
    publication = published_pair["publication"]
    cache: dict[tuple[str, int], dict[str, Any]] = {}
    missing: list[tuple[str, str, int]] = []
    for group in publication["variants"]:
        record_id = group["variant"]["recordId"]
        catalog = "skills" if record_id.startswith("skill:") else "equipment"
        application_ids = {
            row["applicationItemId"] for row in group["sourceRows"]
        }
        assert application_ids
        matches = False
        for application_id in sorted(application_ids):
            key = (catalog, application_id)
            if key not in cache:
                cache[key] = _get_json(app, f"/api/{catalog}/{application_id}")
            if record_id in _rule_ids(cache[key]):
                matches = True
                break
        if not matches:
            missing.append((catalog, record_id, len(application_ids)))
    assert not missing, (
        f"{len(missing)} exact rule groups have no canonical owning page: {missing[:18]}"
    )


def test_variant_usage_stale_release_pair_fails_closed(
    published_pair: dict[str, Any], tmp_path: Path,
) -> None:
    """Reusing real publication bytes with a changed rules pair cannot be accepted."""
    publication = DATA / "variant-usage.json"
    army = tmp_path / "infinity.db"
    rules = tmp_path / "rules.db"
    objects = tmp_path / "deployed-objects.json"
    shutil.copyfile(DATA / "infinity.db", army)
    shutil.copyfile(DATA / "rules.db", rules)
    assert not objects.exists()
    assert load_variant_usage_publication(publication, army, rules)
    with rules.open("ab") as output:
        output.write(b"\nintentionally stale pairing\n")
    with pytest.raises(ValueError, match="does not match release artifacts"):
        load_variant_usage_publication(publication, army, rules)


def _browser_catalog_case(
    published_pair: dict[str, Any], catalog: str,
) -> tuple[str, int]:
    """Pick a real page with an exact group, preferring source-specific variants."""
    app = published_pair["app"]
    by_record: dict[str, list[dict[str, Any]]] = {}
    for group in published_pair["publication"]["variants"]:
        if group["variant"]["recordId"].startswith(
            "skill:" if catalog == "skills" else "equipment:"
        ):
            for row in group["sourceRows"]:
                by_record.setdefault(str(row["applicationItemId"]), []).append(group)
    candidates = []
    for item_id, groups in by_record.items():
        detail = _get_json(app, f"/api/{catalog}/{item_id}")
        ids = _rule_ids(detail)
        expected = {group["variantKey"] for group in groups
                    if group["variant"]["recordId"] in ids}
        if expected:
            family_ids = {rule["id"] for rule in detail.get("rules", [])}
            source_specific = any(
                group["variant"]["recordId"] not in family_ids
                for group in groups if group["variantKey"] in expected
            )
            candidates.append((source_specific, len(expected), item_id, detail))
    assert candidates, f"No published {catalog} page has exact reviewed variants"
    candidates.sort(key=lambda case: (-int(case[0]), -case[1], int(case[2])))
    _, expected_count, item_id, detail = candidates[0]
    return str(detail.get("slug") or item_id), expected_count


@pytest.mark.parametrize("catalog", ("skills", "equipment"))
@pytest.mark.parametrize("width", (1440, 390, 320))
def test_variant_usage_developer_browser_matches_real_source_groups(
    published_pair: dict[str, Any], catalog: str, width: int,
) -> None:
    """Normal routes expose exact source groups only through Developer Mode."""
    sync_api = pytest.importorskip("playwright.sync_api")
    app = published_pair["app"]
    slug, expected_count = _browser_catalog_case(published_pair, catalog)
    with sync_api.sync_playwright() as driver:
        try:
            browser = driver.chromium.launch(channel="chrome")
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or "not found" in str(exc):
                pytest.skip(f"Chromium unavailable: {exc}")
            raise
        try:
            page = browser.new_page(viewport={"width": width, "height": 900})
            route_browser_page(page, app, ORIGIN)
            errors: list[str] = []
            failed: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("requestfailed", lambda request: failed.append(request.url))
            try:
                response = page.goto(
                    f"{ORIGIN}/{catalog}/{slug}", wait_until="domcontentloaded"
                )
                assert response and response.status == 200
                page.locator("#skill-content" if catalog == "skills"
                             else "#item-content").wait_for(state="visible")
                page.wait_for_function(
                    "expected => document.querySelectorAll("
                    "'.exact-variant-group').length >= expected",
                    arg=expected_count, timeout=15000,
                )
                groups = page.locator(".exact-variant-group")
                assert groups.count() == expected_count, (
                    catalog, slug, width, expected_count, groups.count()
                )
                usage = page.locator(".exact-variant-usage")
                assert usage.is_hidden(), (catalog, slug, width)
                settings = page.locator('button[aria-controls="settings-menu"]')
                settings.click()
                toggle = page.locator("#developer-mode-toggle")
                toggle.set_checked(True)
                settings.click()
                usage.wait_for(state="visible")
                summary = groups.first.locator("summary")
                summary.focus()
                summary.press("Enter")
                links = groups.first.locator('a[href^="/units/"]')
                links.first.wait_for(state="visible", timeout=15000)
                href = links.first.get_attribute("href")
                assert href and "/units/" in href and "s=" in href
                settings.click()
                toggle.set_checked(False)
                settings.click()
                assert usage.is_hidden(), (catalog, slug, width)
                settings.click()
                toggle.set_checked(True)
                settings.click()
                links.first.wait_for(state="visible", timeout=15000)
                links.first.click()
                page.wait_for_url(re.compile(r".*/units/[a-z0-9-]+.*"))
                page.locator("#unit-content").wait_for(state="visible", timeout=15000)
                assert page.evaluate(
                    "() => document.documentElement.scrollWidth <= innerWidth + 1"
                )
                assert not errors and not failed, (errors, failed)
            finally:
                page.close()
        finally:
            browser.close()
