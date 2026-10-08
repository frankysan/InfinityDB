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
def test_named_mine_pages_publish_shared_placement_rules(
    weaponry_app: Callable, slug: str
) -> None:
    payload = _weapon_detail(weaponry_app, slug)
    assert payload["slug"] == slug
    rules = _weapon_rules(payload)
    assert "weapon:mines" in rules
    assert "weapon:cybermine" not in rules
    assert "weapon:chest-mine" not in rules

    mines = rules["weapon:mines"]
    assert "ordinary Mines" not in mines["summary"]
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
        and relation["record"]["public_reference"] == {"href": "#rule-weapon-mines"}
        for relation in cybermine["display_relations"]
    )
    assert any(
        token["type"] == "reference"
        and token["target"] == "weapon:mines"
        and token["public_reference"] == {"href": "#rule-weapon-mines"}
        for token in cybermine["summary_tokens"]
    )


def test_chest_mine_page_does_not_inherit_shared_mines_rules(
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
    # No local Mines card exists on Chest Mine; land on the shared card elsewhere.
    assert next(
        token["public_reference"]
        for token in chest_mine["summary_tokens"]
        if token.get("target") == "weapon:mines"
    ) == {"href": "/weapons/ap-mine#rule-weapon-mines"}


def test_named_mine_page_can_host_shared_rule_link(weaponry_app: Callable) -> None:
    """The chosen cross-page target must actually publish the target card."""
    payload = _weapon_detail(weaponry_app, "ap-mine")
    assert "weapon:mines" in _weapon_rules(payload)


@pytest.mark.parametrize(
    ("slug", "ammunition", "damage", "saving", "rolls", "distinct_trait"),
    (
        ("ap-mine", "AP", "7", "ARM/2", "1", "Concealed"),
        ("e-m-mine", "E/M", "7", "BTS/2", "2", "Non-lethal"),
        ("monofilament-mine", "N", "8", "ARM=0", "1", "State: Dead"),
        ("para-mine", "PARA", "-", "PH-6", "1", "Non-lethal"),
        ("shock-mine", "Shock", "7", "ARM", "1", "Concealed"),
        ("viral-mine", "N", "7", "BTS", "1", "Bioweapon (DA+SHOCK)"),
        ("cybermine", 0, "5", "BTS", "2", "Comms. Attack"),
    ),
)
def test_named_mines_preserve_distinct_army_profiles(
    weaponry_app: Callable,
    slug: str,
    ammunition: str | int,
    damage: str,
    saving: str,
    rolls: str,
    distinct_trait: str,
) -> None:
    """Family rules must not flatten source-specific ammunition and effects."""
    payload = _weapon_detail(weaponry_app, slug)
    assert len(payload["profiles"]) == 1
    profile = payload["profiles"][0]
    assert (profile["ammunition"], profile["damage"], profile["saving"],
            profile["saving_num"]) == (ammunition, damage, saving, rolls)
    assert distinct_trait in profile["traits"]
    assert "weapon:mines" in _weapon_rules(payload)
    assert "ordinary Mines" not in _weapon_rules(payload)["weapon:mines"]["summary"]


def test_chest_mine_modes_are_not_a_default_mine_profile(
    weaponry_app: Callable,
) -> None:
    payload = _weapon_detail(weaponry_app, "chest-mine")
    assert {profile["mode"] for profile in payload["profiles"]} == {
        "BS Mode", "CC Mode"
    }
    assert "weapon:mines" not in _weapon_rules(payload)
    assert "ordinary Mines" not in _weapon_rules(payload)["weapon:chest-mine"]["summary"]


def test_wildparrot_rules_keep_perimeter_deployment_separate_from_boost(
    weaponry_app: Callable,
) -> None:
    """WildParrot follows E/M Mine effects, not Boost or CAMO placement."""
    payload = _weapon_detail(weaponry_app, "wildparrot")
    profile = payload["profiles"][0]
    assert profile["ammunition"] == "E/M"
    assert profile["saving"] == "BTS/2"
    assert profile["saving_num"] == "2"
    assert "Perimeter" in profile["traits"]
    assert "Boost" not in profile["traits"]
    # PDF v5.3 p. 74 and the Wiki include this Trait, but Army does not.
    assert "Non-lethal" not in profile["traits"]

    rules = _weapon_rules(payload)
    assert set(rules) == {"weapon:wildparrot"}
    record = rules["weapon:wildparrot"]
    assert "WildParrot Token or Model" in record["summary"]
    assert "source discrepancy" in record["summary"]
    assert record["summary_tokens"]
    assert any(
        citation["source_id"] == "n5-core-v5.3-pdf"
        and citation["source_version"] == "5.3"
        and citation["page"] == 74
        for citation in record["citations"]
    )
    assert {
        relation["record"]["id"]
        for relation in record["display_relations"]
        if relation["direction"] == "outbound"
    } >= {"trait:perimeter", "weapon:mines", "ammunition:em"}

    assert any(
        relation["type"] == "modifies-use-of"
        and relation["record"]["id"] == "weapon:mines"
        for relation in record["display_relations"]
    )

    references = profile["rule_references"]
    assert {reference["id"] for reference in references} == {
        "ammunition:em", "trait:non-lethal", "state:isolated",
        "state:immobilized-b",
    }
    for reference in references:
        target = reference["public_reference"]
        assert target.get("href") or (target.get("catalog") and target.get("id"))
    assert payload["weapon_variants"][0]["profiles"][0]["rule_references"] == references


@pytest.mark.parametrize("slug,ammunition,saving", (
    ("crazykoala", "Shock", "ARM"),
    ("madtraps", "PARA", "PH-6"),
))
def test_boost_perimeter_weapons_do_not_inherit_wildparrot_or_mines_rules(
    weaponry_app: Callable, slug: str, ammunition: str, saving: str
) -> None:
    payload = _weapon_detail(weaponry_app, slug)
    profile = payload["profiles"][0]
    assert "Boost" in profile["traits"]
    assert "Perimeter" in profile["traits"]
    assert profile["ammunition"] == ammunition
    assert profile["saving"] == saving
    assert {"weapon:wildparrot", "weapon:mines"}.isdisjoint(_weapon_rules(payload))
    assert "rule_references" not in profile


def test_pt_endgame_rules_apply_only_to_the_endgame_source_variant(
    weaponry_app: Callable,
) -> None:
    """A grouped PT catalog item must not grant Double Shot to other PTs."""
    payload = _weapon_detail(weaponry_app, "pt")
    assert payload["name"] == "PT"
    assert set(_weapon_rules(payload)) == {"weapon:pt"}

    variants = {variant["item_id"]: variant for variant in payload["variants"]}
    assert set(variants) == {203, 204, 205}
    endgame = variants[203]
    assert [rule["id"] for rule in endgame["rules"]] == ["weapon:pt-endgame"]
    assert endgame["source_variant"] == {"kind": "named", "label": "Endgame"}
    assert all(not variants[source_id].get("rules") for source_id in (204, 205))

    rule = endgame["rules"][0]
    assert "Double Shot" in rule["summary"]
    assert "source discrepancy" in rule["summary"]
    assert rule["facts"]["effects"]
    assert any(
        citation["source_id"] == "n5-core-v5.3-pdf"
        and citation["source_version"] == "5.3"
        and citation["page"] == 181
        for citation in rule["citations"]
    )
    assert any(
        token.get("target") == "trait:double-shot"
        and token["public_reference"] == {"catalog": "traits", "id": "double-shot"}
        for token in rule["summary_tokens"]
    )
    assert any(
        relation["record"]["id"] == "trait:double-shot"
        and relation["direction"] == "outbound"
        for relation in rule["display_relations"]
    )

    # Reviewed N5 additions are supplemental; never rewrite imported Army Traits.
    profiles = {profile["id"]: profile for profile in payload["profiles"]}
    assert set(profiles) == {203, 204, 205}
    assert all("Technical Weapon" in profile["traits"] for profile in profiles.values())
    assert all("Double Shot" not in profile["traits"] for profile in profiles.values())
    assert profiles[203]["burst"] == "1"
