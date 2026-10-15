"""N5.3 chart/Army source exactness and browser API for Marksman Rifles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import export_rules_database
from infinity_db.web import create_app

CHART_RANGES = {
    "short": {"max": 20, "mod": "-3"},
    "med": {"max": 60, "mod": "+3"},
    "long": {"max": 100, "mod": "-3"},
    "max": {"max": 120, "mod": "-6"},
}


@pytest.fixture(scope="module")
def app(tmp_path_factory: pytest.TempPathFactory) -> Any:
    root = Path(__file__).resolve().parents[1]
    output = tmp_path_factory.mktemp("marksman-rifle-reference") / "rules.db"
    export_rules_database(load_curated_directory(root / "data/curated"), output)
    return create_app(root / "data/generated/infinity.db", output)


def detail(app: Any, slug: str) -> dict[str, Any]:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=f"/api/weapons/{slug}", REQUEST_METHOD="GET")
    status: list[str] = []
    response = app(
        environ,
        lambda text, headers, exc_info=None: status.append(text),
    )
    try:
        body = b"".join(response)
    finally:
        close = getattr(response, "close", None)
        if close is not None:
            close()
    assert status == ["200 OK"], (slug, status, body[:200])
    return json.loads(body)


@pytest.mark.parametrize(
    ("slug", "source_id", "ammo", "saving", "traits", "refs", "property_id", "rules"),
    [
        ("ap-marksman-rifle", 85, "AP", "ARM/2", ["Suppressive Fire"],
         ["ammunition:ap", "trait:suppressive-fire"], None, ["weapon:marksman-rifles"]),
        ("breaker-marksman-rifle", 225, "AP", "BTS/2", ["Suppressive Fire"],
         [], "weapon-property:breaker", ["weapon:breaker-marksman-rifle"]),
        ("k1-marksman-rifle", 181, "N", "ARM=0", ["Anti-materiel", "Suppressive Fire"],
         ["ammunition:normal", "trait:anti-materiel", "trait:suppressive-fire"],
         "weapon-property:k1", ["weapon:marksman-rifles"]),
        ("marksman-rifle", 84, "N", "ARM", ["Suppressive Fire"],
         ["ammunition:normal", "trait:suppressive-fire"], None, ["weapon:marksman-rifles"]),
        ("shock-marksman-rifle", 155, "Shock", "ARM", ["Suppressive Fire"],
         ["ammunition:shock", "trait:suppressive-fire"], None, ["weapon:marksman-rifles"]),
        ("t2-marksman-rifle", 180, "T2", "ARM", ["Anti-materiel", "Suppressive Fire"],
         ["ammunition:t2", "trait:anti-materiel", "trait:suppressive-fire"],
         None, ["weapon:marksman-rifles"]),
        ("viral-marksman-rifle", 206, "N", "BTS",
         ["Bioweapon (DA+SHOCK)", "Suppressive Fire"],
         ["ammunition:normal", "trait:bioweapon", "trait:suppressive-fire"],
         "weapon-property:viral", ["weapon:marksman-rifles"]),
    ],
)
def test_single_mode_source_profiles_and_scoped_links(
    app: Any,
    slug: str,
    source_id: int,
    ammo: str,
    saving: str,
    traits: list[str],
    refs: list[str],
    property_id: str | None,
    rules: list[str],
) -> None:
    weapon = detail(app, slug)
    assert [rule["id"] for rule in weapon["rules"]] == rules
    assert len(weapon["profiles"]) == 1
    profile = weapon["profiles"][0]
    assert (profile["id"], profile["damage"], profile["burst"]) == (source_id, "7", "3")
    assert (profile["ammunition"], profile["saving"], profile["saving_num"]) == (
        ammo, saving, "1",
    )
    assert profile["ranges"] == CHART_RANGES
    assert profile["traits"] == traits
    assert [ref["id"] for ref in profile.get("rule_references", [])] == refs
    assert [prop["id"] for prop in profile.get("weapon_properties", [])] == (
        [property_id] if property_id else []
    )

    rule = weapon["rules"][0]
    assert any(
        citation["source_id"] == "n5-core-v5.3-pdf" and citation["page"] == 180
        for citation in rule["citations"]
    )
    if slug != "breaker-marksman-rifle":
        assert any(
            citation["source_id"] == "wiki-en-20260926-200832"
            and citation["heading"] == "MARKSMAN RIFLES"
            for citation in rule["citations"]
        )
        assert "weapon:multi-marksman-rifle" in {
            token["target"] for token in rule["summary_tokens"]
            if token["type"] == "reference"
        }


def test_multi_modes_have_exclusive_profile_facts_without_family_link(
    app: Any,
) -> None:
    weapon = detail(app, "multi-marksman-rifle")
    assert [rule["id"] for rule in weapon["rules"]] == ["weapon:multi-marksman-rifle"]
    profiles = {profile["mode"]: profile for profile in weapon["profiles"]}
    assert set(profiles) == {"Anti-Material Mode", "AP Mode", "Shock Mode"}
    expected = {
        "Anti-Material Mode": ("DA", "1", "ARM", "2", ["Anti-materiel"]),
        "AP Mode": ("AP", "3", "ARM/2", "1", ["Suppressive Fire"]),
        "Shock Mode": ("Shock", "3", "ARM", "1", ["Suppressive Fire"]),
    }
    for mode, (ammo, burst, saving, rolls, traits) in expected.items():
        profile = profiles[mode]
        assert (profile["id"], profile["damage"], profile["burst"]) == (
            169, "7", burst,
        )
        assert (profile["ammunition"], profile["saving"], profile["saving_num"]) == (
            ammo, saving, rolls,
        )
        assert profile["traits"] == traits
        assert profile["ranges"] == CHART_RANGES
        assert "rule_references" not in profile  # The API is not mode-scoped.
        assert [prop["id"] for prop in profile["weapon_properties"]] == [
            "weapon-property:multi"
        ]

    rule = weapon["rules"][0]
    assert "does **not** list" in rule["summary"]
    assert {"ammunition:da", "ammunition:ap", "ammunition:shock",
            "trait:anti-materiel", "trait:suppressive-fire"} == {
        relation["record_id"] for relation in rule["relations"]
    }
    assert "Anti-Material Mode" in " ".join(rule["facts"]["sourceNotes"])


def test_unrelated_weapons_do_not_inherit_marksman_rules(app: Any) -> None:
    for slug in ("sniper-rifle", "multi-rifle", "heavy-flamethrower"):
        assert not {
            "weapon:marksman-rifles",
            "weapon:multi-marksman-rifle",
        } & {rule["id"] for rule in detail(app, slug).get("rules", [])}
