"""Pitcher and Mine Dispenser N5.3 source profiles and published rule contracts."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import export_rules_database
from infinity_db.web import create_app


@pytest.fixture(scope="module")
def app(tmp_path_factory: pytest.TempPathFactory) -> Callable:
    root = Path(__file__).resolve().parents[1]
    rules_path = tmp_path_factory.mktemp("support-weapon-rules") / "rules.db"
    export_rules_database(load_curated_directory(root / "data/curated"), rules_path)
    return create_app(root / "data/generated/infinity.db", rules_path)


def weapon_detail(app: Callable, slug: str) -> dict[str, Any]:
    env: dict[str, Any] = {}
    setup_testing_defaults(env)
    env.update(PATH_INFO=f"/api/weapons/{slug}", REQUEST_METHOD="GET")
    statuses: list[str] = []
    response: Iterator[bytes] = app(
        env,
        lambda status, headers, exc_info=None: statuses.append(status),
    )
    try:
        payload = b"".join(response)
    finally:
        close = getattr(response, "close", None)
        if close:
            close()
    assert statuses == ["200 OK"], (slug, statuses, payload[:200])
    return json.loads(payload)


def rule_for(item: dict[str, Any], rule_id: str) -> dict[str, Any]:
    rules = {r["id"]: r for r in item.get("rules", [])}
    assert list(rules) == [rule_id]
    return rules[rule_id]


def citations(rule: dict[str, Any]) -> set[tuple[str, int]]:
    return {
        (citation["source_id"], citation["page"])
        for citation in rule["citations"] if citation.get("page")
    }


def test_pitcher_places_repeater_without_a_saving_roll(app: Callable) -> None:
    item = weapon_detail(app, "pitcher")
    profile, = item["profiles"]
    assert (profile["id"], profile["damage"], profile["burst"]) == (154, "-", "1")
    assert (profile["ammunition"], profile["saving"], profile["saving_num"]) == (
        0, "-", "-",
    )
    assert profile["ranges"] == {
        "short": {"max": 40, "mod": "0"},
        "long": {"max": 60, "mod": "-3"},
        "max": {"max": 120, "mod": "-6"},
    }
    assert profile["traits"] == [
        "Speculative Attack", "Disposable (2)", "Indiscriminate",
        "Non-lethal", "Targetless", "[*]",
    ]
    assert "ammunition_effects" not in profile

    rule = rule_for(item, "weapon:pitcher")
    text = rule["summary"]
    assert "successful BS Roll" in text
    assert "Deployable Repeater" in text
    assert "choose another legal position" in text
    assert "no PS, Ammunition or Saving Roll" in text
    assert "not the [[skill:place-deployable|Place Deployable]] Skill" in text
    assert {"equipment:deployable-repeater", "trait:indiscriminate", "trait:non-lethal",
            "trait:speculative-attack", "trait:targetless",
            "trait:disposable-x", "skill:speculative-attack"} == {
        relation["record_id"] for relation in rule["relations"]
    }
    assert {"n5-core-v5.3-pdf", "wiki-en-20260926-200832"} <= {
        c["source_id"] for c in rule["citations"]
    }
    assert {
        ("n5-core-v5.3-pdf", 73),
        ("n5-core-v5.3-pdf", 187),
        ("n5-faq-v0.1-en-pdf", 2),
    } <= citations(rule)
    targets = {
        token["target"] for token in rule["summary_tokens"]
        if token["type"] == "reference"
    }
    assert {
        "equipment:deployable-repeater", "equipment:repeater",
        "trait:targetless", "skill:place-deployable",
    } <= targets


def test_mine_dispenser_uses_drop_bears_bs_placement_not_damage(
    app: Callable,
) -> None:
    item = weapon_detail(app, "mine-dispenser")
    profile, = item["profiles"]
    assert (profile["id"], profile["damage"], profile["burst"]) == (176, "-", "1")
    # Imported savingNum=1 is source data, but has no operative Save Attribute.
    assert (profile["ammunition"], profile["saving"], profile["saving_num"]) == (
        0, "-", "1",
    )
    assert profile["ranges"] == {
        "short": {"max": 20, "mod": "0"},
        "med": {"max": 40, "mod": "+3"},
        "long": {"max": 60, "mod": "-3"},
        "max": {"max": 120, "mod": "-6"},
    }
    assert profile["traits"] == [
        "Double Shot", "Speculative Attack", "Disposable (2)",
        "Targetless", "[*]",
    ]
    assert "ammunition_effects" not in profile
    rule = rule_for(item, "weapon:mine-dispenser")
    summary = rule["summary"]
    for text in (
        "Trooper's Unit Profile", "BS Mode", "Conclusion step",
        "cannot detonate during the Order", "Camouflage",
        "Double Shot", "both remaining charges", "not",
    ):
        assert text in summary
    assert "not [[trait:bs-weapon-ph|BS Weapon (PH)]]" in summary
    assert {"weapon:drop-bears", "weapon:mines",
            "trait:double-shot", "trait:disposable-x",
            "trait:speculative-attack", "trait:targetless",
            "skill:speculative-attack"} == {
        relation["record_id"] for relation in rule["relations"]
    }
    assert {("n5-core-v5.3-pdf", page) for page in (71, 72, 181)} <= citations(rule)
    assert any(
        c["source_id"] == "wiki-en-20260926-200832"
        and c["member"] == "Mine_Dispenser" for c in rule["citations"]
    )
    assert "savingNum=1" in " ".join(rule["facts"]["sourceNotes"])
    assert "Shock Mine subtype" in " ".join(rule["facts"]["sourceNotes"])
    assert {
        "weapon:drop-bears", "weapon:mines", "trait:double-shot",
    } <= {
        token["target"] for token in rule["summary_tokens"]
        if token["type"] == "reference"
    }


def test_placement_rule_does_not_leak_into_related_weapons(app: Callable) -> None:
    for slug in ("drop-bears", "shock-mine", "heavy-flamethrower"):
        item = weapon_detail(app, slug)
        assert not {"weapon:pitcher", "weapon:mine-dispenser"} & {
            r["id"] for r in item.get("rules", [])
        }
