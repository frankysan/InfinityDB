"""P3.4 domain-aware registry and cross-publication fail-closed boundaries."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from infinity_db.its_season_database import build_its_database
from infinity_db.publication_registry import PublicationReference, PublicationRegistry
from infinity_db.rules_database import RulesDatabase
from infinity_db.scenario_catalog import ScenarioCatalog
from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "data/generated/rules_n5.db"
ITS_SOURCE = ROOT / "data/curated/rules/n5-its-season-18-2026.09.01.json"
REVISION = "2026.09.01"


@pytest.fixture
def registry(tmp_path: Path) -> PublicationRegistry:
    path = tmp_path / "its_18.db"
    build_its_database(ITS_SOURCE, path)
    return PublicationRegistry(RulesDatabase(RULES_PATH), {"its-18": path})


def test_registry_resolves_same_scenario_id_by_owner_and_revision(
    registry: PublicationRegistry,
) -> None:
    assert registry.core_revision == "5.3"
    core = registry.resolve(PublicationReference("rules-n5", "scenario:battleground"))
    season = registry.resolve(PublicationReference(
        "its-18", "scenario:battleground", REVISION,
    ))
    assert core is None
    assert season is not None and season["record"]["id"] == "scenario:battleground"
    assert season["publication"]["collectionId"] == "its-18"
    assert season["publication"]["sourceCollectionId"] == "its-season-18-2026.09.01"
    manifest = registry.season_manifest()["its-18"]
    assert manifest["revision"] == REVISION
    assert manifest["requiredCoreRulesRevision"] == "5.3"
    assert len(manifest["sha256"]) == 64


def test_explicit_owner_revision_and_context_fail_closed(
    registry: PublicationRegistry,
) -> None:
    assert registry.resolve(PublicationReference(
        "its-18", "scenario:battleground", "2025.09.01",
    )) is None
    assert registry.resolve(PublicationReference(
        "its-17", "scenario:battleground", REVISION,
    )) is None
    assert registry.resolve(PublicationReference(
        "its-18", "scenario:missing", REVISION,
    )) is None
    assert registry.resolve(PublicationReference("rules-n5", "scenario:missing")) is None
    assert registry.season_policies(
        season_id="its-18", revision=REVISION, context="free-play",
    ) == []
    assert registry.season_policies(
        season_id="its-17", revision=REVISION, context="official-tournament",
    ) == []
    assert registry.season_policies(
        season_id="its-18", revision="2025.09.01", context="official-tournament",
    ) == []


def test_policy_targets_resolve_from_core_only_in_explicit_context(
    registry: PublicationRegistry,
) -> None:
    specs = registry.season_policies(
        season_id="its-18", revision=REVISION, context="official-tournament",
    )
    assert len(specs) == 1
    assert specs[0]["policy"]["id"] == "its18-spec-ops-tournament"
    assert specs[0]["policy"]["target"] == {
        "domain": "rules-n5", "recordId": "skill:infinity-spec-ops",
    }
    assert specs[0]["target"]["id"] == "skill:infinity-spec-ops"
    extra = registry.season_policies(
        season_id="its-18", revision=REVISION, context="reinforcements-extra",
    )
    assert len(extra) == 1
    assert extra[0]["target"]["id"] == "rule:reinforcements-extra"
    assert registry.season_policies(
        season_id="its-18", revision=REVISION, context="official-tournament",
        target_id="rule:reinforcements-extra",
    ) == []


def test_core_marker_provenance_is_resolved_from_its_source_metadata(
    registry: PublicationRegistry,
) -> None:
    citation = registry.source_citation(
        season_id="its-18", source_id="its-season-18-en-pdf", page=17,
    )
    assert citation == {
        "source_id": "its-season-18-en-pdf",
        "source_title": "ITS Season 18: Overheat (English)",
        "source_version": REVISION,
        "source_url": "https://experience.corvusbelli.com/en/infinity/its-rules",
        "page": 17,
    }
    catalog = ScenarioCatalog(registry.rules_database, registry)
    core = catalog.get_scenario("domination", army_points=300)
    assert core is not None
    assert core["placement"]["marker_dimensions"][0]["citation"] == citation
    # Attribution can originate in ITS without transferring core-mission ownership.
    assert core["publication"]["collection_id"] == "n5-core"
    assert registry.source_citation(
        season_id="its-17", source_id="its-season-18-en-pdf", page=17,
    ) is None
    assert registry.source_citation(
        season_id="its-18", source_id="unknown", page=17,
    ) is None


def test_registered_marker_provenance_missing_fails_closed(
    registry: PublicationRegistry, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(registry._season_sources["its-18"], "its-season-18-en-pdf")
    catalog = ScenarioCatalog(registry.rules_database, registry)
    with pytest.raises(ValueError, match="marker size source is unavailable"):
        catalog.get_scenario("domination", army_points=300)


def test_season_policy_contexts_are_discoverable_but_never_applied_by_default(
    registry: PublicationRegistry,
) -> None:
    assert registry.season_contexts(season_id="its-18", revision=REVISION) == [
        "official-tournament", "reinforcements-extra", "team-ops-extra",
    ]
    assert registry.season_contexts(season_id="its-18", revision="wrong") == []
    assert registry.season_contexts(season_id="its-17", revision=REVISION) == []


def test_registry_rejects_wrong_season_registration_and_core_revision(tmp_path: Path) -> None:
    its = tmp_path / "its_18.db"
    build_its_database(ITS_SOURCE, its)
    rules = RulesDatabase(RULES_PATH)
    with pytest.raises(ValueError, match="registration does not match"):
        PublicationRegistry(rules, {"its-17": its})

    class WrongCoreRevision(RulesDatabase):
        def current_core_scenario_revision(self) -> str:
            return "5.4"

    with pytest.raises(ValueError, match="different N5 core revision"):
        PublicationRegistry(WrongCoreRevision(RULES_PATH), {"its-18": its})


def test_registry_rejects_unknown_cross_domain_policy_target(tmp_path: Path) -> None:
    its = tmp_path / "its_18.db"
    build_its_database(ITS_SOURCE, its)

    class MissingReference(RulesDatabase):
        def composed_record(self, record_id: str, **kwargs):
            if record_id == "skill:infinity-spec-ops":
                return None
            return super().composed_record(record_id, **kwargs)

    with pytest.raises(ValueError, match="unknown N5 target"):
        PublicationRegistry(MissingReference(RULES_PATH), {"its-18": its})


@pytest.mark.parametrize(
    ("reference", "message"),
    [
        (("rules-n5", "scenario:battleground", REVISION), "do not take season"),
        (("its-18", "scenario:battleground", None), "require an exact season"),
        (("its-18", "skill:infinity-spec-ops", REVISION), "must identify a Scenario"),
        (("unknown", "scenario:battleground", None), "Unregistered publication"),
        (("rules-n5", "untyped", None), "typed record"),
    ],
)
def test_publication_reference_requires_explicit_typed_ownership(
    reference: tuple[str, str, str | None], message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        PublicationReference(*reference)


@pytest.fixture(scope="module")
def registered_http_apps(tmp_path_factory: pytest.TempPathFactory):
    path = tmp_path_factory.mktemp("p34-serving") / "its_18.db"
    build_its_database(ITS_SOURCE, path)
    army = ROOT / "data/generated/army.db"
    baseline = create_app(army, RULES_PATH)
    registered = create_app(
        army, RULES_PATH, season_databases={"its-18": path},
    )
    return baseline, registered


def test_registered_http_catalog_preserves_default_and_exact_season_selection(
    registered_http_apps,
) -> None:
    baseline, registered = registered_http_apps
    assert baseline.snapshot_revision != registered.snapshot_revision

    for query in ("", "?collection=n5-core&revision=5.3"):
        url = "http://registry.test/api/scenarios" + query
        old_status, _, old_body = wsgi_response(baseline, url)
        new_status, _, new_body = wsgi_response(registered, url)
        assert old_status == new_status == 200
        assert json.loads(new_body)["items"] == json.loads(old_body)["items"]

    its_url = f"http://registry.test/api/scenarios?collection=its-18&revision={REVISION}"
    assert json.loads(wsgi_response(baseline, its_url)[2])["items"] == []
    its_items = json.loads(wsgi_response(registered, its_url)[2])["items"]
    assert [item["slug"] for item in its_items] == ["battleground"]
    default = json.loads(wsgi_response(
        registered, "http://registry.test/api/scenarios",
    )[2])
    assert len(default["items"]) == 4
    assert all(item["publication"]["collection_id"] == "n5-core" for item in default["items"])

    for query in (
        "?collection=its-17&revision=2026.09.01",
        "?collection=its-18&revision=2025.09.01",
    ):
        status, _, body = wsgi_response(
            registered, "http://registry.test/api/scenarios" + query,
        )
        assert status == 200 and json.loads(body)["items"] == []


def test_its_scenario_is_unavailable_without_its_owner(registered_http_apps) -> None:
    core, registered = registered_http_apps
    url = (
        "http://registry.test/api/scenarios/battleground?"
        f"army_points=300&collection=its-18&revision={REVISION}"
    )
    assert wsgi_response(core, url)[0] == 404
    assert wsgi_response(registered, url)[0] == 200


def test_registered_http_core_default_and_cache_isolation(registered_http_apps) -> None:
    baseline, registered = registered_http_apps
    urls = (
        "http://registry.test/api/scenarios/battleground?army_points=300",
        "http://registry.test/api/scenarios/battleground?army_points=300"
        "&collection=its-17&revision=2026.09.01",
    )
    for url in urls:
        old_status, _, old_body = wsgi_response(baseline, url)
        new_status, _, new_body = wsgi_response(registered, url)
        assert (new_status, json.loads(new_body)) == (
            old_status, json.loads(old_body),
        )
    url = "http://registry.test/api/scenarios/annihilation?army_points=300"
    old_status, old_headers, _ = wsgi_response(baseline, url)
    new_status, new_headers, _ = wsgi_response(registered, url)
    assert old_status == new_status == 200
    assert dict(old_headers)["ETag"] != dict(new_headers)["ETag"]


def test_faq_api_requires_registered_season_and_mission_identity(
    registered_http_apps,
) -> None:
    _core, registered = registered_http_apps
    root = (
        "http://registry.test/api/faq-rulings?"
        "topic_id=equipment%3Ahacking-device&rules_revision=5.3&as_of=2026-09-01"
    )
    valid_season = "&season_id=its-18&season_revision=2026.09.01"
    invalid_season = "&season_id=its-17&season_revision=2025.09.01"
    assert json.loads(wsgi_response(registered, root)[2])["items"]
    # General N5 FAQ is still applicable to a registered season when not
    # scoped to a particular mission.
    assert json.loads(wsgi_response(registered, root + valid_season)[2])["items"]
    assert json.loads(wsgi_response(registered, root + invalid_season)[2])["items"] == []
    # A non-member mission cannot impersonate a season's namesake scenario.
    assert json.loads(wsgi_response(
        registered, root + valid_season + "&scenario_id=scenario%3Aannihilation",
    )[2])["items"] == []
    scoped = (
        "http://registry.test/api/faq-rulings?"
        "topic_id=scenario%3Asupplies&rules_revision=5.3&as_of=2026-09-01"
        "&scenario_id=scenario%3Asupplies"
    )
    assert json.loads(wsgi_response(registered, scoped)[2])["items"]
    assert json.loads(wsgi_response(
        registered, scoped + valid_season,
    )[2])["items"] == []


def test_published_season_policies_require_explicit_play_context(
    registered_http_apps,
) -> None:
    core, registered = registered_http_apps
    base = f"http://registry.test/api/season-policies?season_id=its-18&season_revision={REVISION}"
    status, _, data = wsgi_response(registered, base)
    assert status == 200
    initial = json.loads(data)
    assert initial["selection"]["context"] is None
    assert initial["items"] == []
    assert initial["contexts"] == [
        "official-tournament", "reinforcements-extra", "team-ops-extra",
    ]
    assert json.loads(wsgi_response(core, base)[2])["items"] == []
    cases = (
        ("official-tournament", "its18-spec-ops-tournament", "skill:infinity-spec-ops", 26),
        ("team-ops-extra", "its18-team-ops-spec-ops", "skill:infinity-spec-ops", 28),
        ("reinforcements-extra", "its18-reinforcements-availability",
         "rule:reinforcements-extra", 27),
    )
    for context, expected_id, target, page in cases:
        status, _, body = wsgi_response(registered, base + f"&context={context}")
        assert status == 200
        policy, = json.loads(body)["items"]
        assert policy["id"] == expected_id
        assert policy["target"]["recordId"] == target
        assert policy["target"]["name"]
        assert policy["citations"][0]["page"] == page
        assert policy["citations"][0]["sourceTitle"] == "ITS Season 18: Overheat (English)"
        assert policy["citations"][0]["sourceUrl"] == (
            "https://experience.corvusbelli.com/en/infinity/its-rules"
        )
        assert policy["applicability"]["context"] == context
        status, _, body = wsgi_response(
            registered, base + f"&context={context}&target_id={target}",
        )
        assert status == 200 and len(json.loads(body)["items"]) == 1
        status, _, body = wsgi_response(
            registered, base + f"&context={context}&target_id=rule:missing",
        )
        assert status == 200 and json.loads(body)["items"] == []
    for url in (
        base + "&context=free-play",
        base + "&context=official-tournament&target_id=rule:reinforcements-extra",
        "http://registry.test/api/season-policies?"
        "season_id=its-18&season_revision=wrong&context=official-tournament",
        "http://registry.test/api/season-policies?"
        f"season_id=its-17&season_revision={REVISION}&context=official-tournament",
    ):
        status, _, body = wsgi_response(registered, url)
        assert status == 200 and json.loads(body)["items"] == []


@pytest.mark.parametrize("query", [
    "",
    "season_id=its-18",
    "season_id=its-18&season_revision=",
    "season_id=ITS-18&season_revision=2026.09.01",
    "season_id=its-18&season_revision=2026.09.01&context=bad context",
    "season_id=its-18&season_revision=2026.09.01&target_id=skill:infinity-spec-ops",
    "season_id=its-18&season_revision=2026.09.01&context=official-tournament"
    "&target_id=scenario:battleground",
    "season_id=its-18&season_revision=2026.09.01&context=official-tournament"
    "&target_id=skill:CAPS",
    "season_id=its-18&season_revision=2026.09.01&season_id=its-18",
    "season_id=its-18&season_revision=2026.09.01&unexpected=1",
])
def test_season_policies_api_rejects_incomplete_or_malformed_selection(
    registered_http_apps, query: str,
) -> None:
    _, registered = registered_http_apps
    status, _, payload = wsgi_response(
        registered, "http://registry.test/api/season-policies?" + query,
    )
    assert status == 400
    assert "error" in json.loads(payload)


def test_registered_its_matches_pinned_pre_cutover_json_and_svg_bytes(
    registered_http_apps,
) -> None:
    import hashlib

    _core, registered = registered_http_apps
    combined = hashlib.sha256()
    for points in (150, 200, 250, 300, 350, 400):
        selector = f"army_points={points}&collection=its-18&revision={REVISION}"
        path = f"http://registry.test/api/scenarios/battleground?{selector}"
        status, _, body = wsgi_response(registered, path)
        assert status == 200
        canonical = json.dumps(
            json.loads(body), ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        combined.update(len(canonical).to_bytes(8, "big"))
        combined.update(canonical)
        for theme in ("light", "dark"):
            for unit in ("in", "cm"):
                path = (
                    "http://registry.test/api/scenarios/battleground/map.svg?"
                    f"{selector}&theme={theme}&distance_unit={unit}"
                )
                status, _, body = wsgi_response(registered, path)
                assert status == 200
                combined.update(len(body).to_bytes(8, "big"))
                combined.update(body)
    # Frozen from the pre-cutover Rules-owned Battleground HTTP responses.
    # Length-prefixed six canonical JSON payloads and 24 SVG byte streams.
    assert combined.hexdigest() == (
        "b631c0c677c0c8b1276a606b1367c4c6"
        "c0e5a9f61479506a7ceee608f33594b2"
    )
