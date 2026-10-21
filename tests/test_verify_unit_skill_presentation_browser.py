"""Hermetic DOM expectation tests for optional Unit Skill Chromium acceptance."""

from __future__ import annotations

import sqlite3
from copy import deepcopy
from pathlib import Path
from socketserver import ThreadingMixIn
from threading import Thread
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

import pytest

from infinity_db.web import create_app
from tools.verify_non_skill_army_browser import CASES, WIDTHS
from tools.verify_unit_skill_presentation_browser import (
    DEFAULT_SLUGS,
    DOM_SNAPSHOT,
    OPTIONAL_FLAGS,
    _distance_extra,
    _settings_script,
    _unit_api_url,
    assert_rendered_items,
    assert_unit_dom,
    expected_items,
    verify,
)


def _item(
    name: str, slug: str, *, quantity: int | None = None,
    extras: tuple[str, ...] = (),
) -> dict:
    return {
        "name": name, "slug": slug, "quantity": quantity,
        "extras": [{"name": extra} for extra in extras],
    }


def _row(
    label: str, item: str, *, href: str | None = None,
) -> dict:
    return {
        "heading": label, "text": label + " " + item,
        "links": [{"href": href, "text": item}] if href else [],
    }


def _unit() -> tuple[dict, dict]:
    unit = {
        "general_profiles": [
            {"presentation_visible": True, "shared_items": {
                "skills": [_item("Stealth", "stealth")],
                "training": [_item("Regular", "regular")],
                "source_markers": [_item("Marker", "source-only")],
            }},
            {"presentation_visible": False, "shared_items": {
                "skills": [_item("Hidden", "hidden")],
            }},
        ],
        "armies": [{
            "name": "Example Army", "availability_badges": [{"label": "Mercenary"}],
            "presentation_visible": True,
            "profiles": [{
                "specific_items": {
                    "equipment": [_item("MediKit", "medikit", quantity=2)],
                    "attribute_overrides": [_item("BTS=3", "bts-3")],
                },
            }],
            "loadouts": [{
                "specific_items": {
                    "weapons": [_item("Combi Rifle", "combi-rifle", extras=("AP",))],
                    "skills": [_item("Mimetism", "mimetism")],
                },
            }],
        }, {
            "name": "Hidden Army", "availability_badges": [],
            "presentation_visible": False, "profiles": [], "loadouts": [],
        }],
    }
    dom = {
        "general": [[
            _row("Skills", "Stealth", href="/skills/stealth"),
            _row("Training", "Regular"),
        ]],
        "armies": [{
            "name": "Example ArmyMercenary",
            "profiles": [[
                _row("Equipment", "MediKit ×2", href="/equipment/medikit"),
                _row("Attribute overrides", "BTS=3"),
            ]],
            "loadouts": [[
                _row("Weapons", "Combi Rifle (AP)", href="/weapons/combi-rifle"),
                _row("Skills", "Mimetism", href="/skills/mimetism"),
            ]],
        }],
        "skillHrefs": ["/skills/stealth", "/skills/mimetism"],
        "overflow": False,
    }
    return unit, dom


def test_live_chromium_unit_detail_matrix_when_available() -> None:
    """Run the complete seven-Unit, three-width matrix when Chrome is installed."""
    pytest.importorskip("playwright.sync_api")
    root = Path(__file__).resolve().parents[1]
    app = create_app(
        root / "data/generated/infinity.db",
        rules_database_path=root / "data/generated/rules.db",
    )

    class ThreadedServer(ThreadingMixIn, WSGIServer):
        daemon_threads = True

    class QuietHandler(WSGIRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            pass

    server = make_server(
        "127.0.0.1", 0, app, server_class=ThreadedServer,
        handler_class=QuietHandler,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        try:
            result = verify(
                f"http://127.0.0.1:{server.server_port}",
                slugs=DEFAULT_SLUGS, channel="chrome",
            )
        except Exception as exc:
            if "Executable doesn't exist" in str(exc) or (
                "chrome" in str(exc).lower() and "not found" in str(exc).lower()
            ):
                pytest.skip(f"Chromium browser unavailable: {exc}")
            raise
        assert result["passed"] == result["total"] == len(WIDTHS) * len(DEFAULT_SLUGS), (
            result
        )
        scenarios: tuple[tuple[tuple[str, ...], dict[str, bool]], ...] = (
            (("tohaa-team-ops",), {"teamops": False}),
            (
                ("raoul-spector-mercenary-operative", "tohaa-team-ops"),
                dict.fromkeys(OPTIONAL_FLAGS, False),
            ),
        )
        for filtered_slugs, flags in scenarios:
            filtered = verify(
                f"http://127.0.0.1:{server.server_port}",
                slugs=filtered_slugs, optional_filters=flags, channel="chrome",
            )
            assert filtered["passed"] == filtered["total"] == (
                len(WIDTHS) * len(filtered_slugs)
            ), filtered
            baseline_visibility = {
                (entry["unit"], entry["width"]): (
                    entry["visibleArmies"], entry["visibleGeneralProfiles"]
                )
                for entry in result["results"]
            }
            assert any(
                (
                    entry["visibleArmies"], entry["visibleGeneralProfiles"]
                ) != baseline_visibility[(entry["unit"], entry["width"])]
                for entry in filtered["results"]
            ), ("Optional filters did not change any visible content", filtered)

        with sqlite3.connect(root / "data/generated/infinity.db") as db:
            distance_slugs = tuple(row[0] for row in db.execute(
                "SELECT DISTINCT lu.slug FROM profile_payload_skill_extras AS x "
                "JOIN extras AS e ON e.id = x.extra_id AND e.type = 'DISTANCE' "
                "JOIN profile_payloads AS p ON p.id = x.profile_payload_id "
                "JOIN logical_units AS lu ON lu.id = p.logical_unit_id "
                "WHERE lu.slug IS NOT NULL "
                "UNION "
                "SELECT DISTINCT lu.slug FROM loadout_payload_skill_extras AS x "
                "JOIN extras AS e ON e.id = x.extra_id AND e.type = 'DISTANCE' "
                "JOIN loadout_payloads AS p ON p.id = x.loadout_payload_id "
                "JOIN logical_units AS lu ON lu.id = p.logical_unit_id "
                "WHERE lu.slug IS NOT NULL ORDER BY slug LIMIT 2"
            ))
        assert len(distance_slugs) == 2, distance_slugs
        for distance_unit in ("in", "cm"):
            distances = verify(
                f"http://127.0.0.1:{server.server_port}",
                slugs=distance_slugs, channel="chrome",
                distance_unit=distance_unit,
            )
            assert distances["passed"] == distances["total"] == (
                len(WIDTHS) * len(distance_slugs)
            ), distances
            assert sum(
                result.get("counts", {}).get("distanceExtras", 0)
                for result in distances["results"]
            ) > 0, distances
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_optional_filter_preferences_and_api_urls_are_consistent() -> None:
    script = _settings_script(
        {"mercs": False, "reinforcement": False}, "cm",
    )
    assert '"infinity-db-mercs": "false"' in script
    assert '"infinity-db-specops": "true"' in script
    assert '"infinity-db-reinforcement": "false"' in script
    assert '"infinity-db-distance-unit": "cm"' in script
    assert _unit_api_url(
        "http://127.0.0.1:8080", "test-unit",
        {"mercs": False, "reinforcement": False},
    ) == (
        "http://127.0.0.1:8080/api/units/test-unit?"
        "mercs=0&specops=1&teamops=1&reinforcement=0"
    )
    with pytest.raises(ValueError, match="Unknown optional"):
        _settings_script({"invalid": False}, "in")
    with pytest.raises(ValueError, match="Distance unit"):
        _settings_script({}, "feet")


def test_browser_manifest_is_pinned_and_covers_three_viewports() -> None:
    assert DEFAULT_SLUGS == tuple(case.slug for case in CASES)
    assert len(DEFAULT_SLUGS) == 7
    assert WIDTHS == (1440, 390, 320)
    assert ".general-profile" in DOM_SNAPSHOT
    assert ".army-profile" in DOM_SNAPSHOT
    assert ".profile-details-table" in DOM_SNAPSHOT
    assert ".loadout-table" in DOM_SNAPSHOT


def test_expected_items_omits_api_only_markers_and_distance_extra_text() -> None:
    projected = expected_items({
        "equipment": [_item("MediKit", "medikit", quantity=2)],
        "skills": [{
            **_item("Forward Observer", "forward-observer", extras=("8", "AP")),
            "extras": [{"name": "8", "is_distance": True}, {"name": "AP"}],
        }],
        "source_markers": [_item("Team marker", "team-marker")],
    })
    assert set(projected) == {"equipment", "skills"}
    assert projected["skills"][0].extras == ('3.2"', "AP")
    assert expected_items({
        "skills": [{
            **_item("Forward Observer", "forward-observer"),
            "extras": [{"name": "8", "is_distance": True}],
        }],
    }, "cm")["skills"][0].extras == ("8 cm",)
    assert projected["equipment"][0].href == "/equipment/medikit"
    assert projected["equipment"][0].quantity == 2


@pytest.mark.parametrize(
    ("source", "semantics", "unit", "expected"),
    [
        ("+7.5", None, "in", '+3"'),
        ("+7.5", {"positive_sign": "omit"}, "in", '3"'),
        ("7.5", {"positive_sign": "force"}, "in", '+3"'),
        ("-5", {"positive_sign": "force"}, "in", '-2"'),
        ("+7.5", {"positive_sign": "omit"}, "cm", "7.5 cm"),
        ("+7.5", {"positive_sign": "force"}, "cm", "+7.5 cm"),
    ],
)
def test_distance_extra_signed_formatting(
    source: str, semantics: dict | None, unit: str, expected: str,
) -> None:
    assert _distance_extra(source, semantics, unit) == expected


def test_rendered_row_requires_correct_bucket_link_quantity_and_extra() -> None:
    rows = [
        _row("Skills", "Mimetism (AP) ×2", href="/skills/mimetism"),
    ]
    expected = {
        "skills": [_item("Mimetism", "mimetism", quantity=2, extras=("AP",))],
    }
    assert assert_rendered_items(rows, expected, "example") == 1
    for bad_rows in (
        [_row("Equipment", "Mimetism (AP) ×2", href="/skills/mimetism")],
        [_row("Skills", "Mimetism (AP) ×2", href="/equipment/mimetism")],
        [_row("Skills", "Mimetism (AP)", href="/skills/mimetism")],
        [_row("Skills", "Mimetism ×2", href="/skills/mimetism")],
    ):
        with pytest.raises(AssertionError, match="missing skills item"):
            assert_rendered_items(bad_rows, expected, "example")


def test_rendered_distance_extra_must_match_selected_unit() -> None:
    items = {"skills": [{
        **_item("Super-Jump", "super-jump"),
        "extras": [{"name": "+7.5", "is_distance": True}],
        "parameter_semantics": {"positive_sign": "omit"},
    }]}
    assert assert_rendered_items(
        [_row("Skills", 'Super-Jump (3")', href="/skills/super-jump")],
        items, "inches",
    ) == 1
    assert assert_rendered_items(
        [_row("Skills", "Super-Jump (7.5 cm)", href="/skills/super-jump")],
        items, "centimeters", "cm",
    ) == 1
    with pytest.raises(AssertionError, match="missing skills item"):
        assert_rendered_items(
            [_row("Skills", 'Super-Jump (+3")', href="/skills/super-jump")],
            items, "wrong sign",
        )


def test_browser_dom_checks_scoped_shared_and_army_local_rows() -> None:
    unit, dom = _unit()
    assert assert_unit_dom(unit, dom, "unit") == {
        "shared": 2, "profiles": 2, "loadouts": 2, "distanceExtras": 0,
    }


@pytest.mark.parametrize(
    ("mutation", "error"),
    [
        ("shared_missing", "missing skills item"),
        ("wrong_local_bucket", "unexpected skills row"),
        ("missing_profile_segment", "profiles DOM count"),
        ("missing_army", "cannot uniquely match Army section"),
        ("bad_marker_link", "source marker gained Skill link"),
        ("extra_army", "cannot uniquely match Army section"),
        ("overflow", "document horizontal overflow"),
        ("unexpected_row", "unexpected equipment row"),
        ("classified_skill_link", "missing attribute_overrides item"),
    ],
)
def test_browser_dom_rejects_loss_and_cross_context_leakage(
    mutation: str, error: str,
) -> None:
    unit, dom = _unit()
    broken = deepcopy(dom)
    if mutation == "shared_missing":
        broken["general"][0][0]["links"] = []
    elif mutation == "wrong_local_bucket":
        broken["armies"][0]["profiles"][0][0]["heading"] = "Skills"
    elif mutation == "missing_profile_segment":
        broken["armies"][0]["profiles"] = []
    elif mutation == "missing_army":
        broken["armies"][0]["name"] = "Different Army"
    elif mutation == "bad_marker_link":
        broken["skillHrefs"].append("/skills/source-only")
    elif mutation == "extra_army":
        broken["armies"].append(deepcopy(broken["armies"][0]))
    elif mutation == "overflow":
        broken["overflow"] = True
    elif mutation == "unexpected_row":
        broken["general"][0].append(_row("Equipment", "Ghost Equipment"))
    elif mutation == "classified_skill_link":
        broken["armies"][0]["profiles"][0][1]["links"].append(
            {"href": "/skills/bts-3", "text": "BTS=3"}
        )
    with pytest.raises(AssertionError, match=error):
        assert_unit_dom(unit, broken, "unit")
