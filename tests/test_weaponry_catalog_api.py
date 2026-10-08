"""Player-facing integration checks for reviewed N5 mine weapon references.

These checks deliberately exercise the published application snapshot, not just
the curated source records. A source clause being represented in a summary does
not prove that a player can reach the rule from the relevant weapon page.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.web import create_app


@pytest.fixture(scope="module")
def weaponry_app() -> Callable:
    root = Path(__file__).resolve().parents[1]
    return create_app(
        root / "data/generated/infinity.db",
        rules_database_path=root / "data/generated/rules.db",
    )


def _weapon_detail(app: Callable, slug: str) -> dict[str, Any]:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=f"/api/weapons/{slug}", REQUEST_METHOD="GET")
    observed: dict[str, Any] = {}

    def start_response(
        status: str, headers: list[tuple[str, str]], exc_info: Any = None
    ) -> None:
        observed["status"] = int(status.split()[0])
        observed["content_type"] = dict(headers).get("Content-Type", "")

    response: Iterator[bytes] = app(environ, start_response)
    try:
        body = b"".join(response)
    finally:
        close = getattr(response, "close", None)
        if close is not None:
            close()
    assert observed["status"] == 200, (slug, body[:300])
    assert observed["content_type"].startswith("application/json")
    return json.loads(body)


def _weapon_rules(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {record["id"]: record for record in payload.get("rules", [])}


@pytest.mark.parametrize(
    "slug",
    (
        "ap-mine",
        "e-m-mine",
        "monofilament-mine",
        "para-mine",
        "shock-mine",
        "viral-mine",
    ),
)
def test_ordinary_mine_pages_publish_the_shared_rules(
    weaponry_app: Callable, slug: str
) -> None:
    payload = _weapon_detail(weaponry_app, slug)
    assert payload["slug"] == slug
    rules = _weapon_rules(payload)
    assert "weapon:mines" in rules
    assert "weapon:cybermine" not in rules
    assert "weapon:chest-mine" not in rules

    mines = rules["weapon:mines"]
    assert any(
        source["source_id"] == "n5-core-v5.3-pdf"
        and source["source_version"] == "5.3"
        and source["page"] == 72
        for source in mines["citations"]
    )
    assert mines["summary_tokens"]
    assert any(
        relation["record"]["id"] == "trait:deployable"
        and relation["direction"] == "outbound"
        for relation in mines["display_relations"]
    )


def test_cybermine_page_retains_both_family_and_exception(
    weaponry_app: Callable,
) -> None:
    payload = _weapon_detail(weaponry_app, "cybermine")
    rules = _weapon_rules(payload)
    assert {"weapon:mines", "weapon:cybermine"} <= rules.keys()
    assert "weapon:chest-mine" not in rules
    cybermine = rules["weapon:cybermine"]
    assert any(
        relation["record"]["id"] == "weapon:mines"
        and relation["direction"] == "outbound"
        for relation in cybermine["display_relations"]
    )
    assert any(
        token["type"] == "reference"
        and token["target"] == "weapon:mines"
        and token["public_reference"]
        for token in cybermine["summary_tokens"]
    )


def test_chest_mine_page_does_not_inherit_ordinary_mine_rules(
    weaponry_app: Callable,
) -> None:
    payload = _weapon_detail(weaponry_app, "chest-mine")
    rules = _weapon_rules(payload)
    assert "weapon:chest-mine" in rules
    assert "weapon:mines" not in rules
    assert "weapon:cybermine" not in rules
    chest_mine = rules["weapon:chest-mine"]
    assert any(
        source["source_id"] == "n5-core-v5.3-pdf"
        and source["page"] == 72
        for source in chest_mine["citations"]
    )
    assert chest_mine["summary_tokens"]
