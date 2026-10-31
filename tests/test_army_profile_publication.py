"""ARMY-02–20 current-source profiles, not historical deltas or list legality."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/JSON 20260929-114335.zip"
ARMY = ROOT / "data/generated/infinity.db"
SOURCE_CONTEXTS = {
    1912: {101, 102, 104, 105, 106, 107},
    1926: {101, 102, 104, 105, 106, 107},
    1913: {103},
    1927: {103},
    1914: {201, 202, 204, 205},
    1928: {201, 202, 204, 205},
    1915: {301, 302, 303, 304, 305, 306},
    1929: {301, 302, 303, 304, 305, 306},
    1916: {401, 402, 403, 404},
    1930: {401, 402, 403, 404},
    1917: {501, 502, 503, 504},
    1931: {501, 502, 503, 504},
    1918: {601, 604, 605},
    1932: {601, 604},
    1919: {601, 602},
    1933: {602},
    1920: {603},
    1934: {603},
    1921: {605},
    1935: {605},
    1922: {701, 702, 703},
    1936: {701, 702, 703},
    1923: {1001, 1002, 1003},
    1937: {1001, 1002, 1003},
    1924: {1101, 1102, 1103},
    1938: {1101, 1102, 1103},
    1908: {801},
    1909: {801},
    1925: {901, 902, 904, 905, 908, 909},
    1939: {902, 904, 905, 908, 909},
    1940: {305, 306, 605, 801, 1001, 1002, 1101, 1102},
    314: {401, 402, 403, 404, 908},
    1874: {107, 204, 304, 1003, 1102},
    1905: {101, 201, 401, 501},
}
SOURCE_IDS = tuple(SOURCE_CONTEXTS)
SOURCE_VERSION_OVERRIDES = {
    701: "7.26246.159", 702: "7.26246.159", 703: "7.26246.159",
    801: "7.26246.159", 901: "7.26246.159", 902: "7.26246.159",
    904: "7.26246.159", 905: "7.26246.159", 908: "7.26246.159", 909: "7.26246.159",
    1001: "7.26246.159", 1002: "7.26246.159", 1003: "7.26246.159",
    1101: "7.26246.159", 1102: "7.26246.159", 1103: "7.26246.159",
}


@pytest.fixture(scope="module")
def profile_app() -> Callable[..., Any]:
    return create_app(ARMY, rules_database_path=ROOT / "data/generated/rules.db")


@pytest.fixture(scope="module")
def source_documents() -> dict[int, dict[str, Any]]:
    if not SOURCE.exists():
        pytest.skip("Pinned Army ZIP unavailable; source parity is not verified")
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == (
        "f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75"
    )
    with sqlite3.connect(ARMY.as_uri() + "?mode=ro", uri=True) as connection:
        rows = connection.execute(
            "SELECT a.application_army_id, s.source_file, s.source_sha256 "
            "FROM application_army_sources AS a JOIN army_lists AS s "
            "ON s.id = a.source_army_id WHERE a.has_army_list = 1"
        ).fetchall()
    documents = {}
    with zipfile.ZipFile(SOURCE) as archive:
        for army_id, member, digest in rows:
            raw = archive.read(member)
            document = json.loads(raw)
            if not any(unit["id"] in SOURCE_IDS for unit in document["units"]):
                continue
            assert army_id not in documents
            assert hashlib.sha256(raw).hexdigest() == digest
            assert document["version"] == SOURCE_VERSION_OVERRIDES.get(army_id, "7.26246.158")
            documents[army_id] = {**document, "source_file": member}
    assert {
        source_id: {
            army_id for army_id, document in documents.items()
            if any(unit["id"] == source_id for unit in document["units"])
        }
        for source_id in SOURCE_IDS
    } == SOURCE_CONTEXTS
    return documents


def _references(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Discard only public names/links; retain identity, quantity and ordered extras."""
    return [
        {"id": item["id"], "q": item["quantity"],
         "extra": [extra["id"] for extra in item["extras"]]}
        for item in items
    ]


def _source_references(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Army uses both null and [] for no extras; neither names a modifier.
    return [
        {"id": item["id"], "q": item.get("q"), "extra": item.get("extra") or []}
        for item in items
    ]


def _assert_native_items(source: dict[str, Any], published: dict[str, Any]) -> None:
    for original_key, public_key in (
        ("skills", "skills"), ("equip", "equipment"), ("weapons", "weapons"),
    ):
        assert _references(published[public_key]) == _source_references(source[original_key])
    # These selected source occurrences contain neither relationship. Fail on
    # source drift rather than silently skipping a newly populated relationship.
    assert source["includes"] == source["peripheral"] == []
    assert not published.get("includes") and not published.get("peripherals")


@pytest.mark.parametrize("source_id", SOURCE_IDS)
def test_army_update_complete_native_profiles_and_loadouts_reach_api(
    profile_app: Callable[..., Any], source_documents: dict[int, dict[str, Any]],
    source_id: int,
) -> None:
    contexts = SOURCE_CONTEXTS[source_id]
    sources = {
        army_id: next(unit for unit in source_documents[army_id]["units"]
                      if unit["id"] == source_id)
        for army_id in contexts
    }
    slug = next(iter(sources.values()))["slug"]
    status, _, body = wsgi_response(profile_app, f"http://test/api/units/{slug}")
    assert status == 200
    unit = json.loads(body)
    assert unit["source_ids"] == [source_id]
    assert {army["id"] for army in unit["armies"]} == contexts
    if source_id in {1940, 314, 1874, 1905}:
        assert not any(source.get("spectables") for source in sources.values())
        assert unit["source_charts"] == []
    else:
        assert len(unit["source_charts"]) == 1
        chart = unit["source_charts"][0]
        assert chart["source_unit_id"] == source_id
        assert {(version["version"], version["source_file"])
                for version in chart["source_versions"]} == {
            (source_documents[army_id]["version"], source_documents[army_id]["source_file"])
            for army_id in contexts
        }
    for army in unit["armies"]:
        original = sources[army["id"]]
        filters = source_documents[army["id"]]["filters"]
        labels = {kind: {item["id"]: item["name"] for item in filters[kind]}
                  for kind in ("type", "category", "chars")}
        expected_profiles = [
            (group, profile) for group in original["profileGroups"]
            for profile in group["profiles"]
        ]
        assert [(profile["group_id"], profile["profile_id"])
                for profile in army["profiles"]] == [
            (group["id"], profile["id"]) for group, profile in expected_profiles
        ]
        for (group, source), published in zip(expected_profiles, army["profiles"], strict=True):
            for source_key, public_key in (
                ("name", "name"), ("cc", "cc"), ("bs", "bs"), ("ph", "ph"),
                ("wip", "wip"), ("arm", "arm"), ("bts", "bts"),
                ("w", "vitality"), ("s", "silhouette"), ("str", "is_structure"),
                ("ava", "ava"),
            ):
                assert published[public_key] == source[source_key], (
                    source_id, army["id"], group["id"], source["id"], source_key,
                )
            assert [published["move_1"], published["move_2"]] == source["move"]
            assert published["type"] == labels["type"][source["type"]]
            assert published["classification"] == labels["category"].get(group["category"])
            assert published["logo_urls"] == [source["logo"]]
            assert [item["name"] for item in published["characteristics"]] == [
                labels["chars"][item] for item in source["chars"]
            ]
            assert source["notes"] is None and group["notes"] is None
            _assert_native_items(source, published)
        expected_loadouts = [
            (group["id"], option) for group in original["profileGroups"]
            for option in group["options"]
        ]
        assert [(option["group_id"], option["option_id"]) for option in army["loadouts"]] == [
            (group_id, option["id"]) for group_id, option in expected_loadouts
        ]
        for (_, source), published in zip(expected_loadouts, army["loadouts"], strict=True):
            for field in ("name", "points", "swc", "minis", "disabled"):
                assert published[field] == source[field], (source_id, army["id"], field)
            assert [{key: order[key] for key in ("type", "list", "total")}
                    for order in published["orders"]] == [
                {**order, "type": order["type"].lower()} for order in source["orders"]
            ]
            for order in published["orders"]:
                assert order["training_reference"]["id"] == f"training:{order['type']}"
            assert source["chars"] == []
            _assert_native_items(source, published)
