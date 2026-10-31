"""Hermetic discovery checks for optional Weapon fragment Chromium acceptance."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from tools.verify_rule_fragment_browser import (
    _assert_hosted,
    _check_fresh_deep_link,
    _direct_fragment,
    _record_failed_request,
    glossary_links,
    local_fragments,
    weapon_candidates,
)


class _Response:
    status = 200

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def json(self) -> dict[str, Any]:
        return self.payload


class _Request:
    def __init__(self, payloads: dict[str, dict[str, Any]]) -> None:
        self.payloads = payloads

    def get(self, url: str, *, timeout: int) -> _Response:
        assert timeout == 20000
        return _Response(self.payloads[url])


def test_local_fragments_selects_only_local_rule_hashes() -> None:
    payload = {
        "display_relations": [
            {"record": {"public_reference": {"href": "#rule-weapon-mines"}}},
            {"record": {"public_reference": {"href": "/skills/stealth"}}},
        ],
        "fact_tokens": {"effects": [[
            {"public_reference": {"href": "#rule-ammunition-ap"}},
            {"public_reference": {"href": "https://example.org/#rule-external"}},
        ]]},
        "variants": [{"source_variant": {"kind": "named", "label": "Example"}}],
    }
    assert local_fragments(payload) == {"#rule-weapon-mines", "#rule-ammunition-ap"}


def _weapon_payloads() -> dict[str, dict[str, Any]]:
    base = "http://localhost"
    slugs = ["ap-mine", *(f"weapon-{i}" for i in range(49))]
    payloads: dict[str, dict[str, Any]] = {
        f"{base}/api/weapons": {"items": [{"slug": slug} for slug in slugs]},
    }
    for slug in slugs:
        payloads[f"{base}/api/weapons/{slug}"] = {
            "rules": [{"public_reference": {"href": "#rule-weapon-mines"}}]
            if slug == "ap-mine" else [],
        }
    return payloads


def test_weapon_candidates_pin_known_link_without_inventing_other_links() -> None:
    candidates = weapon_candidates(_Request(_weapon_payloads()), "http://localhost")
    assert candidates == {"ap-mine": {"#rule-weapon-mines"}}


def test_weapon_candidates_reject_duplicate_source_slugs() -> None:
    payloads = _weapon_payloads()
    payloads["http://localhost/api/weapons"]["items"].append({"slug": "ap-mine"})
    with pytest.raises(AssertionError, match="duplicate"):
        weapon_candidates(_Request(payloads), "http://localhost")


def test_glossary_links_only_include_weapon_rule_fragments() -> None:
    payloads = {
        "http://localhost/api/glossary": {"items": [
            {"href": "/weapons/ap-mine#rule-weapon-mines"},
            {"href": "/weapons/ap-mine#rule-weapon-mines"},
            {"href": "/weapons/ap-mine"},
            {"href": "/skills/stealth#rule-skill-stealth"},
            {"href": "/weapons/combi-rifle#other"},
        ]}
    }
    assert glossary_links(_Request(payloads), "http://localhost") == [
        "/weapons/ap-mine#rule-weapon-mines",
    ]


def test_hosted_source_fragment_checks_card_atomically_without_self_link() -> None:
    page = MagicMock()
    page.wait_for_function.return_value.json_value.return_value = {"count": 1}

    _assert_hosted(page, "#rule-weapon-mines")

    page.locator.assert_not_called()
    page.wait_for_function.assert_called_once()
    expression = page.wait_for_function.call_args.args[0]
    assert "cards.length > 1" in expression
    assert "getClientRects()" in expression
    assert page.wait_for_function.call_args.kwargs == {
        "arg": "rule-weapon-mines", "timeout": 10000,
    }


def test_hosted_source_fragment_rejects_duplicate_cards() -> None:
    page = MagicMock()
    page.wait_for_function.return_value.json_value.return_value = {"count": 2}
    with pytest.raises(AssertionError, match="expected one rendered rule card, got 2"):
        _assert_hosted(page, "#rule-weapon-cybermine")


def test_hosted_source_fragment_reports_missing_card_state() -> None:
    page = MagicMock()
    page.wait_for_function.side_effect = TimeoutError("No matching card")
    page.evaluate.return_value = {
        "count": 0, "contentHidden": False, "status": "",
    }
    with pytest.raises(AssertionError, match="rendered rule card unavailable"):
        _assert_hosted(page, "#rule-weapon-kobra-pistol")
    page.evaluate.assert_called_once()


def test_failed_requests_ignore_expected_navigation_abort() -> None:
    errors: list[str] = []
    _record_failed_request(
        SimpleNamespace(
            url="http://localhost/api/units?filter=all",
            method="GET",
            failure="net::ERR_ABORTED",
        ),
        errors,
    )
    assert errors == []
    _record_failed_request(
        SimpleNamespace(
            url="http://localhost/api/weapons/para-mine",
            method="GET",
            failure="net::ERR_CONNECTION_RESET",
        ),
        errors,
    )
    assert errors == [
        "GET http://localhost/api/weapons/para-mine: net::ERR_CONNECTION_RESET"
    ]


def test_direct_link_falls_back_to_hosted_source_without_self_link() -> None:
    assert _direct_fragment({"#rule-weapon-mines"}, []) == "#rule-weapon-mines"
    assert _direct_fragment(
        {"#rule-weapon-mines", "#rule-weapon-ap-mine"},
        ["#rule-weapon-ap-mine"],
    ) == "#rule-weapon-ap-mine"


def test_direct_link_uses_fresh_page_and_closes_it() -> None:
    context = MagicMock()
    fresh_page = context.new_page.return_value
    fresh_page.goto.return_value.status = 200
    errors: list[str] = []
    network_errors: list[str] = []
    url = "http://localhost/weapons/para-mine#rule-weapon-mines"

    with (
        patch("tools.verify_rule_fragment_browser._ready") as ready,
        patch("tools.verify_rule_fragment_browser._assert_target") as target,
        patch("tools.verify_rule_fragment_browser._check_errors") as errors_check,
    ):
        _check_fresh_deep_link(
            context, url, "#rule-weapon-mines", errors, network_errors
        )

    context.new_page.assert_called_once_with()
    fresh_page.goto.assert_called_once_with(url, wait_until="domcontentloaded")
    ready.assert_called_once_with(fresh_page, errors, network_errors)
    target.assert_called_once_with(fresh_page, "#rule-weapon-mines")
    errors_check.assert_called_once_with(fresh_page, errors, network_errors)
    fresh_page.close.assert_called_once_with()


def test_direct_link_closes_fresh_page_on_render_failure() -> None:
    context = MagicMock()
    fresh_page = context.new_page.return_value
    fresh_page.goto.return_value.status = 200
    with patch(
        "tools.verify_rule_fragment_browser._ready",
        side_effect=AssertionError("Detail did not render"),
    ):
        with pytest.raises(AssertionError, match="Detail did not render"):
            _check_fresh_deep_link(
                context,
                "http://localhost/weapons/cybermine#rule-weapon-cybermine",
                "#rule-weapon-cybermine", [], [],
            )
    fresh_page.close.assert_called_once_with()
