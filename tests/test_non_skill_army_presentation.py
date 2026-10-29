"""Permanent source-to-API/template checks for non-Skill Army source entries.

The separate local Chromium acceptance is historical evidence, not run by CI.
These checks use the tracked published Army and rules databases only.
"""

from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.database import Database
from infinity_db.web import create_app
from tools.verify_non_skill_army_browser import CASES, WIDTHS, projected_buckets

ROOT = Path(__file__).resolve().parents[1]
APPLICATION_DB = ROOT / "data/generated/infinity.db"
RULES_DB = ROOT / "data/generated/rules.db"
ARMY_ZIP = ROOT / "data/raw/JSON 20260929-114335.zip"

# Original Army Skill IDs deliberately published in other player-facing buckets.
SOURCE_BUCKETS = {
    254: ("gizmokit", "equipment"),
    273: ("medikit", "equipment"),
    266: ("bangbomb", "equipment"),
    258: ("regular", "training"),
    282: ("infinity-team-ops", "source_markers"),
    280: ("bts-3", "attribute_overrides"),
}

REPRESENTATIVE_UNITS = (
    ("dragoes", 254, "/equipment/gizmokit"),
    ("minutemen", 273, "/equipment/medikit"),
    ("racerbots", 266, "/equipment/bangbomb"),
    ("miyamoto-mushashi", 258, None),
    ("raoul-spector-mercenary-operative", 258, None),
    ("tohaa-team-ops", 282, None),
    ("corregidor-alguaciles", 280, None),
)


@pytest.fixture(scope="module")
def application() -> Any:
    assert APPLICATION_DB.is_file()
    assert RULES_DB.is_file()
    return create_app(APPLICATION_DB, rules_database_path=RULES_DB)


def _get(app: Any, path: str) -> tuple[int, bytes]:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
    statuses: list[int] = []

    def start_response(status: str, headers: list[tuple[str, str]], exc_info: Any = None) -> None:
        statuses.append(int(status.split()[0]))

    response = app(environ, start_response)
    try:
        body = b"".join(response)
    finally:
        close = getattr(response, "close", None)
        if close is not None:
            close()
    assert len(statuses) == 1
    return statuses[0], body


def _source_pairs() -> list[tuple[str, int]]:
    # Cross-check all directly used source identities, not just a shortlist
    # of representative Unit pages.
    with sqlite3.connect(f"{APPLICATION_DB.resolve().as_uri()}?mode=ro", uri=True) as connection:
        return [
            (str(slug), int(source_id))
            for slug, source_id in connection.execute(
                """
                SELECT DISTINCT logical.slug, source.id
                FROM logical_units AS logical
                JOIN (
                    SELECT p.logical_unit_id, s.item_id
                    FROM profile_payloads AS p
                    JOIN profile_payload_skills AS s ON s.profile_payload_id = p.id
                    UNION ALL
                    SELECT p.logical_unit_id, s.item_id
                    FROM loadout_payloads AS p
                    JOIN loadout_payload_skills AS s ON s.loadout_payload_id = p.id
                ) AS used ON used.logical_unit_id = logical.id
                JOIN skills AS source ON source.id = used.item_id
                WHERE source.id IN (254, 273, 266, 258, 282, 280)
                ORDER BY logical.slug, source.id
                """
            )
        ]


def _unit_items(unit: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []
    for general in unit["general_profiles"]:
        for bucket, items in general["shared_items"].items():
            found.extend((bucket, item) for item in items)
    for army in unit["armies"]:
        for kind in ("profiles", "loadouts"):
            for context in army[kind]:
                for bucket, items in context.get("specific_items", {}).items():
                    found.extend((bucket, item) for item in items)
    return found


def test_every_published_non_skill_army_source_has_a_correct_bucket(application: Any) -> None:
    pairs = _source_pairs()
    assert len(pairs) == 72  # Pinned published snapshot, not browser pass count.
    assert {source_id for _, source_id in pairs} == set(SOURCE_BUCKETS)
    for slug, source_id in pairs:
        source_slug, expected_bucket = SOURCE_BUCKETS[source_id]
        status, body = _get(application, f"/api/units/{slug}")
        assert status == 200, (slug, status)
        items = _unit_items(json.loads(body))
        matches = [(bucket, item) for bucket, item in items if item.get("slug") == source_slug]
        assert matches, (slug, source_slug)
        assert {bucket for bucket, _ in matches} == {expected_bucket}, (slug, source_slug)
        assert not any(bucket == "skills" for bucket, _ in matches)


@pytest.mark.parametrize(("slug", "source_id", "destination"), REPRESENTATIVE_UNITS)
def test_non_skill_sources_have_normal_unit_bootstrap_and_detail_api(
    application: Any, slug: str, source_id: int, destination: str | None,
) -> None:
    # Unit pages are client-rendered: the initial HTML provides the
    # bootstrap, not the .general-profile DOM nodes (Chromium checks those).
    status, body = _get(application, f"/units/{slug}")
    assert status == 200, slug
    html = body.decode("utf-8")
    assert 'id="unit-content"' in html, slug
    assert "/static/unit.js" in html, slug

    status, payload = _get(application, f"/api/units/{slug}")
    assert status == 200, slug
    unit = json.loads(payload)
    assert unit["general_profiles"], slug
    source_slug, expected_bucket = SOURCE_BUCKETS[source_id]
    assert any(
        bucket == expected_bucket and item.get("slug") == source_slug
        for bucket, item in _unit_items(unit)
    ), (slug, source_slug)
    if destination:
        assert _get(application, destination)[0] == 200


def test_browser_case_manifest_tracks_the_pinned_api_samples() -> None:
    assert WIDTHS == (1440, 390, 320)
    assert len(CASES) == len(REPRESENTATIVE_UNITS)
    for case, (slug, source_id, destination) in zip(CASES, REPRESENTATIVE_UNITS, strict=True):
        source_slug, category = SOURCE_BUCKETS[source_id]
        assert (case.slug, case.source_slug, case.category, case.href) == (
            slug, source_slug, category, destination,
        )
        assert case.minimum_rows >= 1


def _army_source(member: str) -> dict[str, Any]:
    with zipfile.ZipFile(ARMY_ZIP) as archive:
        return json.loads(archive.read(member))


def _published_unit(application: Any, slug: str) -> dict[str, Any]:
    status, data = _get(application, f"/api/units/{slug}")
    assert status == 200, slug
    return json.loads(data)


@pytest.mark.skipif(not ARMY_ZIP.exists(), reason="Pinned Army ZIP unavailable")
def test_army_17_ioann_source_membership_and_duo_chart_are_published(
    application: Any,
) -> None:
    database = Database(APPLICATION_DB)
    for source_file, army_id, expected_team in (
        ("1001-o-12.json", 1001, "O-12 Fireteams I"),
        ("1002-starmada.json", 1002, "Varangian Guards Fireteams"),
    ):
        source = _army_source(source_file)
        assert source["version"] == "7.26246.159"
        ioann = next(unit for unit in source["units"] if unit["id"] == 1940)
        assert ioann["slug"] == "ioann-bann-varangian-dog-warrior"
        profiles = ioann["profileGroups"][0]["profiles"]
        assert [(p["name"], p["ava"]) for p in profiles] == [
            ("DOGFACE FORM", 1), ("DOG-WARRIOR FORM", -1),
        ]
        source_team = next(team for team in source["fireteamChart"]["teams"]
                           if team["name"] == expected_team)
        source_member = next(member for member in source_team["units"]
                             if member["slug"] == ioann["slug"])
        assert source_member["max"] == 1
        assert source_member["required"] is False
        assert source_member["comment"] == "(Varangian)"
        assert "DUO" in source_team["type"]

        published_chart = database.get_fireteam_chart(army_id)
        assert published_chart is not None
        team = next(team for team in published_chart["teams"]
                    if team["name"] == expected_team)
        match = next(member for member in team["members"]
                     if member["slug"] == ioann["slug"])
        assert match["unit"]["slug"] == ioann["slug"]
        assert (match["max_count"], match["required"], match["comment"]) == (
            1, False, "(Varangian)",
        )
        assert "DUO" in team["types"]
    published = _published_unit(application, "ioann-bann-varangian-dog-warrior")
    assert 1940 in published["source_ids"]
    assert {"DOGFACE FORM", "DOG-WARRIOR FORM"} <= {
        profile["name"] for army in published["armies"] for profile in army["profiles"]
    }


@pytest.mark.skipif(not ARMY_ZIP.exists(), reason="Pinned Army ZIP unavailable")
def test_army_18_najjarun_shared_deactivator_survives_all_loadouts(
    application: Any,
) -> None:
    metadata = _army_source("metadata.json")
    assert next(item for item in metadata["equips"] if item["id"] == 238)["name"] == (
        "Deactivator"
    )
    sources = ("401-haqqislam.json", "402-hassassin-bahram.json",
               "403-qapu-khalqi.json")
    for member in sources:
        document = _army_source(member)
        assert document["version"] == "7.26246.158"
        unit = next(unit for unit in document["units"] if unit["id"] == 314)
        group = unit["profileGroups"][0]
        assert 238 in {entry["id"] for entry in group["profiles"][0]["equip"]}
        assert len(group["options"]) == 3
    unit = _published_unit(application, "najjarun-engineers")
    assert 314 in unit["source_ids"]
    assert any(item["slug"] == "deactivator"
               for profile in unit["general_profiles"]
               for item in profile["shared_items"]["equipment"])
    reviewed_armies = {
        army["id"]: army for army in unit["armies"] if army["id"] in (401, 402, 403)
    }
    assert set(reviewed_armies) == {401, 402, 403}
    for army in reviewed_armies.values():
        assert len(army["loadouts"]) == 3
        assert any(profile["ava"] in (1, 2) for profile in army["profiles"])
    assert _get(application, "/equipment/deactivator")[0] == 200


@pytest.mark.skipif(not ARMY_ZIP.exists(), reason="Pinned Army ZIP unavailable")
def test_army_19_sacha_ava_one_across_pinned_factions(
    application: Any,
) -> None:
    contexts = (
        ("1003-torchlight-brigade.json", "7.26246.159", 1003),
        ("107-kestrel-colonial-force.json", "7.26246.158", 107),
        ("204-invincible-army.json", "7.26246.158", 204),
        ("304-usariadna.json", "7.26246.158", 304),
    )
    for member, version, _ in contexts:
        document = _army_source(member)
        assert document["version"] == version
        unit = next(unit for unit in document["units"] if unit["id"] == 1874)
        assert unit["slug"] == "sacha-xenotech-hunters"
        assert [p["ava"] for group in unit["profileGroups"]
                for p in group["profiles"]] == [1]
    unit = _published_unit(application, "sacha-xenotech-hunters")
    assert 1874 in unit["source_ids"]
    for _, _, source_army in contexts:
        matching = [army for army in unit["armies"] if army["id"] == source_army]
        assert matching, source_army
        assert all(profile["ava"] == 1
                   for army in matching for profile in army["profiles"])


@pytest.mark.skipif(not ARMY_ZIP.exists(), reason="Pinned Army ZIP unavailable")
def test_army_20_racerbot_bangbomb_source_buckets_are_deduplicated(
    application: Any,
) -> None:
    meta = _army_source("metadata.json")
    assert next(item for item in meta["equips"] if item["id"] == 246)["name"] == "Bangbomb"
    assert next(item for item in meta["skills"] if item["id"] == 266)["name"] == "Bangbomb"
    for member in ("101-panoceania.json", "401-haqqislam.json"):
        source = _army_source(member)
        assert source["version"] == "7.26246.158"
        racer = next(unit for unit in source["units"] if unit["id"] == 1905)
        profile = racer["profileGroups"][0]["profiles"][0]
        for bucket, source_id in (("equip", 246), ("skills", 266)):
            assert any(item["id"] == source_id and item.get("extra") == [310]
                       for item in profile[bucket])
    published = _published_unit(application, "racerbots")
    assert 1905 in published["source_ids"]
    for general in published["general_profiles"]:
        bangbombs = [item for item in general["shared_items"]["equipment"]
                     if item.get("slug") == "bangbomb"]
        assert len(bangbombs) == 1
        assert [extra["id"] for extra in bangbombs[0]["extras"]] == [310]
        assert not any(item.get("slug") == "bangbomb"
                       for item in general["shared_items"]["skills"])
    assert _get(application, "/equipment/bangbomb")[0] == 200


def test_browser_verifier_collects_general_and_army_local_source_buckets() -> None:
    unit = {
        "general_profiles": [{"shared_items": {
            "equipment": [{"slug": "medikit"}],
        }}],
        "armies": [{"profiles": [{"specific_items": {
            "training": [{"slug": "regular"}],
        }}], "loadouts": [{"specific_items": {
            "equipment": [{"slug": "medikit"}],
        }}]}],
    }
    assert projected_buckets(unit, "medikit") == {"equipment"}
    assert projected_buckets(unit, "regular") == {"training"}
    assert projected_buckets(unit, "unpublished") == set()
