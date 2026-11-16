"""P3.5 synthetic two-season isolation; no extra season is shipped or registered for release."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_document
from infinity_db.database_set import validate_database_set
from infinity_db.its_season_database import build_its_database, inspect_its_database
from infinity_db.publication_registry import PublicationReference, PublicationRegistry
from infinity_db.rules_database import RulesDatabase
from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "data/generated"
SOURCE_18 = ROOT / "data/curated/rules/n5-its-season-18-2026.09.01.json"
REVISION_18 = "2026.09.01"
REVISION_17 = "2025.09.01"
ORIGIN = "http://seasons.test"


def _synthetic_source(tmp_path: Path, *, unknown_target: bool = False) -> Path:
    """Clone the maintained *shape*, never assert this is historical ITS 17 content."""
    document = load_curated_document(SOURCE_18)
    document["collection"].update(
        id="its-season-17-synthetic", title="Synthetic ITS 17 fixture",
        effectiveFrom="2025-09-01",
    )
    document["scenarioCollection"].update(
        id="its-17", title="Synthetic ITS 17", revision=REVISION_17,
    )
    old_source, new_source = "its-season-18-en-pdf", "synthetic-its-17-pdf"

    def rewrite_citations(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "sourceId" and item == old_source:
                    value[key] = new_source
                else:
                    rewrite_citations(item)
        elif isinstance(value, list):
            for item in value:
                rewrite_citations(item)

    rewrite_citations(document)
    document["sources"][0].update(
        id=new_source, title="Synthetic ITS 17 test document",
        version=REVISION_17, publishedDate="2025-09-01",
        localPath="tests/fixtures/nonexistent-its17.pdf",
        sha256="ab" * 32, url="https://example.invalid/synthetic-its17",
    )
    assert len(document["records"]) == 1
    scenario = document["records"][0]
    assert scenario["id"] == "scenario:battleground"
    # Both seasons intentionally keep the same title and slug; only authored
    # content and owner differ. Geometry titles must match the scenario name.
    scenario["summary"] = "Synthetic alternate-season mission for duplicate-slug acceptance."
    scenario["scope"]["seasons"] = ["its-17"]

    # Only one synthetic policy, distinct from the three real Season 18 policies.
    policy = document["seasonPolicies"][0]
    policy["id"] = "synthetic-its17-restriction"
    policy["title"] = "Synthetic season-only restriction"
    policy["effect"]["text"] = "Synthetic fixture restriction; never publish."
    policy["applicability"].update(seasonId="its-17", revision=REVISION_17)
    if unknown_target:
        policy["target"]["recordId"] = "skill:missing-synthetic-target"
    document["seasonPolicies"] = [policy]
    path = tmp_path / ("invalid" if unknown_target else "synthetic")
    path = path.with_suffix(".json")
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def two_seasons(tmp_path_factory: pytest.TempPathFactory):
    temp = tmp_path_factory.mktemp("p35-synthetic-seasons")
    source = _synthetic_source(temp)
    second = temp / "its_17.db"
    result = build_its_database(source, second)
    assert result == inspect_its_database(second, source=source, core_revision="5.3")
    assert result["inputIdentity"]["seasonId"] == "its-17"
    assert result["inputIdentity"]["seasonRevision"] == REVISION_17
    assert result["scenarios"][0]["id"] == "scenario:battleground"
    rules = RulesDatabase(RELEASE / "rules_n5.db")
    season_paths = {
        "its-18": RELEASE / "its_18.db",
        "its-17": second,
    }
    registry = PublicationRegistry(rules, season_paths)
    app = create_app(RELEASE / "army.db", RELEASE / "rules_n5.db", season_databases=season_paths)
    single = create_app(
        RELEASE / "army.db", RELEASE / "rules_n5.db",
        season_databases={"its-18": RELEASE / "its_18.db"},
    )
    return source, second, registry, app, single


def _get(app, url: str) -> tuple[int, dict, bytes]:
    status, headers, body = wsgi_response(app, ORIGIN + url)
    return status, dict(headers), body


def test_duplicate_scenario_slug_is_selected_only_by_owner_and_revision(two_seasons) -> None:
    _source, _second, registry, app, single = two_seasons
    assert set(registry.season_manifest()) == {"its-17", "its-18"}
    for season, revision in (
        ("its-17", REVISION_17), ("its-18", REVISION_18),
    ):
        selected = registry.resolve(PublicationReference(
            season, "scenario:battleground", revision,
        ))
        assert selected is not None
        assert selected["record"]["name"] == "Battleground"
        status, _, data = _get(
            app, f"/api/scenarios?collection={season}&revision={revision}",
        )
        assert status == 200
        summaries = json.loads(data)["items"]
        assert [entry["slug"] for entry in summaries] == ["battleground"]
        for points in (150, 300, 400):
            path = (
                f"/api/scenarios/battleground?army_points={points}"
                f"&collection={season}&revision={revision}"
            )
            status, _, data = _get(app, path)
            assert status == 200
            detail = json.loads(data)
            assert detail["name"] == "Battleground"
            assert detail["description"].startswith(
                "Synthetic alternate-season" if season == "its-17" else "Season 18"
            )
            assert detail["publication"]["collection_id"] == season
            assert detail["publication"]["revision"] == revision
            assert detail["publication"]["sources"][0]["id"] == (
                "synthetic-its-17-pdf" if season == "its-17" else "its-season-18-en-pdf"
            )
            status, headers, svg = _get(app, path.replace(
                "/api/scenarios/battleground?", "/api/scenarios/battleground/map.svg?",
            ))
            assert status == 200 and "image/svg+xml" in headers["Content-Type"]
            assert b'<svg xmlns="http://www.w3.org/2000/svg"' in svg
            if season == "its-18":
                assert _get(single, path.replace(
                    "/api/scenarios/battleground?", "/api/scenarios/battleground/map.svg?",
                ))[2] == svg

    assert [item["slug"] for item in json.loads(_get(app, "/api/scenarios")[2])["items"]] == [
        "annihilation", "domination", "supplies", "firefight",
    ]
    assert _get(app, "/api/scenarios/battleground?army_points=300")[0] == 404
    for season, revision in (("its-17", REVISION_18), ("its-18", REVISION_17)):
        assert json.loads(_get(
            app, f"/api/scenarios?collection={season}&revision={revision}",
        )[2])["items"] == []
        assert _get(
            app, f"/api/scenarios/battleground?army_points=300"
            f"&collection={season}&revision={revision}",
        )[0] == 404
    assert registry.resolve(PublicationReference(
        "its-17", "scenario:annihilation", REVISION_17,
    )) is None


def test_season_policy_and_faq_scope_are_independent(two_seasons) -> None:
    _source, _second, registry, app, _single = two_seasons
    base = "/api/season-policies?season_id={}&season_revision={}"
    for season, revision, expected_contexts, expected_id in (
        ("its-17", REVISION_17, ["official-tournament"], "synthetic-its17-restriction"),
        ("its-18", REVISION_18, [
            "official-tournament", "reinforcements-extra", "team-ops-extra",
        ], "its18-spec-ops-tournament"),
    ):
        query = base.format(season, revision)
        unselected = json.loads(_get(app, query)[2])
        assert unselected["items"] == []
        assert unselected["contexts"] == expected_contexts
        policy, = json.loads(_get(app, query + "&context=official-tournament")[2])["items"]
        assert policy["id"] == expected_id
        assert policy["applicability"]["seasonId"] == season
        assert policy["citations"][0]["sourceTitle"].startswith(
            "Synthetic" if season == "its-17" else "ITS Season 18"
        )
        assert json.loads(_get(app, query + "&context=free-play")[2])["items"] == []
        assert json.loads(_get(
            app, query + "&context=official-tournament&target_id=rule:reinforcements-extra",
        )[2])["items"] == []
    assert registry.season_policies(
        season_id="its-17", revision=REVISION_18, context="official-tournament",
    ) == []

    faq = (
        "/api/faq-rulings?topic_id=equipment%3Ahacking-device"
        "&rules_revision=5.3&as_of=2026-09-01"
    )
    for season, revision in (("its-17", REVISION_17), ("its-18", REVISION_18)):
        scope = f"&season_id={season}&season_revision={revision}"
        assert json.loads(_get(app, faq + scope)[2])["items"]  # global N5 ruling
        assert json.loads(_get(
            app, faq + scope + "&scenario_id=scenario%3Aannihilation",
        )[2])["items"] == []  # not a member of either ITS publication
    assert json.loads(_get(app, faq + "&season_id=its-17&season_revision=wrong")[2])[
        "items"
    ] == []
    core_faq = (
        "/api/faq-rulings?topic_id=scenario%3Asupplies"
        "&rules_revision=5.3&as_of=2026-09-01&scenario_id=scenario%3Asupplies"
    )
    assert json.loads(_get(app, core_faq)[2])["items"]
    assert json.loads(_get(
        app, core_faq + "&season_id=its-17&season_revision=" + REVISION_17,
    )[2])["items"] == []


def test_second_season_changes_cache_identity_without_rewriting_first(two_seasons) -> None:
    _source, second, _registry, app, single = two_seasons
    assert app.snapshot_revision != single.snapshot_revision
    assert app.snapshot_revision
    assert (RELEASE / "its_18.db").is_file() and second.is_file()
    path = "/api/scenarios/annihilation?army_points=300"
    status, headers, body = _get(app, path)
    assert status == 200
    _, alone_headers, alone_body = _get(single, path)
    assert json.loads(body) == json.loads(alone_body)
    assert headers["ETag"] != alone_headers["ETag"]
    assert wsgi_response(
        app, ORIGIN + path, headers={"If-None-Match": alone_headers["ETag"]},
    )[0] == 200
    assert wsgi_response(
        app, ORIGIN + path, headers={"If-None-Match": headers["ETag"]},
    )[0] == 304
    selectors = [
        f"/api/scenarios/battleground?army_points=300&collection={season}&revision={revision}"
        for season, revision in (("its-17", REVISION_17), ("its-18", REVISION_18))
    ]
    first = _get(app, selectors[0])
    second_response = _get(app, selectors[1])
    assert first[1]["ETag"] != second_response[1]["ETag"]
    assert json.loads(first[2])["description"] != json.loads(second_response[2])["description"]
    assert wsgi_response(
        app, ORIGIN + selectors[1], headers={"If-None-Match": first[1]["ETag"]},
    )[0] == 200


def test_registration_rejects_unknown_core_dependency_and_mixed_owner(
    tmp_path: Path, two_seasons,
) -> None:
    _, second, _, _, _ = two_seasons
    rules = RulesDatabase(RELEASE / "rules_n5.db")
    with pytest.raises(ValueError, match="registration does not match"):
        PublicationRegistry(rules, {"its-18": second})
    bad_source = _synthetic_source(tmp_path, unknown_target=True)
    bad_database = tmp_path / "invalid.db"
    build_its_database(bad_source, bad_database)
    with pytest.raises(ValueError, match="unknown N5 target"):
        PublicationRegistry(rules, {"its-17": bad_database})
    with pytest.raises(ValueError, match="different N5 core revision"):
        inspect_its_database(second, core_revision="4.0")


def test_unregistered_extra_season_does_not_extend_release_implicitly(
    tmp_path: Path, two_seasons,
) -> None:
    _, second, _, _, _ = two_seasons
    from infinity_db import database_set

    selected = tmp_path / "selected"
    selected.mkdir()
    for name in ("army.db", "rules_n5.db", "its_18.db"):
        shutil.copyfile(RELEASE / name, selected / name)
    shutil.copyfile(second, selected / "its_17.db")
    # An extra file is not a registration. The shipped runtime keeps its
    # explicit three-file allowlist; adding a second season requires a new
    # build manifest and explicit registration, not an opportunistic scan.
    report = validate_database_set(selected, require_complete=True)
    assert set(report["sha256"]) == {"army.db", "rules_n5.db", "its_18.db"}
    assert set(report["seasons"]) == {"its-18"}
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setitem(database_set.SEASON_DATABASE_SOURCES, "its-17", (
            "its_17.db", "synthetic-fixture-not-in-release-manifest.json",
        ))
        with pytest.raises(ValueError, match="lacks input identity"):
            validate_database_set(selected, require_complete=True)
    finally:
        monkeypatch.undo()
