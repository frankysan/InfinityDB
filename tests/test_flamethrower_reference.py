"""N5.3 chart -> rules database -> public Weapon API regression for Flamethrowers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import export_rules_database
from infinity_db.web import create_app


@pytest.fixture(scope="module")
def app(tmp_path_factory: pytest.TempPathFactory) -> Any:
    root = Path(__file__).resolve().parents[1]
    rules = tmp_path_factory.mktemp("flamethrower-reference") / "rules.db"
    export_rules_database(load_curated_directory(root / "data/curated"), rules)
    return create_app(root / "data/generated/infinity.db", rules)


def weapon_detail(app: Any, slug: str) -> dict[str, Any]:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=f"/api/weapons/{slug}", REQUEST_METHOD="GET")
    status: list[str] = []
    body = b"".join(app(
        environ, lambda response_status, headers, exc_info=None: status.append(response_status),
    ))
    assert status == ["200 OK"], (slug, status, body[:150])
    return json.loads(body)


# Official N5.3 English Weapon Chart p. 178; match the imported Army profile.
@pytest.mark.parametrize(
    ("slug", "source_id", "ps", "template"),
    [
        ("heavy-flamethrower", 57, "6", "Large Teardrop"),
        ("light-flamethrower", 56, "7", "Small Teardrop"),
    ],
)
def test_flamethrower_family_rules_and_profile_remain_source_exact(
    app: Any, slug: str, source_id: int, ps: str, template: str,
) -> None:
    item = weapon_detail(app, slug)
    assert [rule["id"] for rule in item["rules"]] == ["weapon:flamethrowers"]
    assert len(item["profiles"]) == 1
    profile = item["profiles"][0]
    assert (profile["id"], profile["damage"], profile["burst"]) == (source_id, ps, "1")
    assert (profile["ammunition"], profile["saving"], profile["saving_num"]) == ("N", "ARM", "1")
    assert profile["ranges"] == {}
    assert f"Direct Template ({template})" in profile["traits"]
    assert {"Intuitive Attack", "Continous Damage"} <= set(profile["traits"])

    rule = item["rules"][0]
    assert "PS 6" in rule["summary"] and "PS 7" in rule["summary"]
    assert "Large Teardrop" in rule["summary"] and "Small Teardrop" in rule["summary"]
    assert {"trait:direct-template", "trait:intuitive-attack",
            "trait:continuous-damage", "ammunition:normal", "skill:intuitive-attack"} <= {
        rel["record_id"] for rel in rule["relations"]
    }
    assert {"trait:direct-template", "trait:continuous-damage",
            "ammunition:normal", "skill:intuitive-attack"} <= {
        token["target"] for token in rule["summary_tokens"]
        if token["type"] == "reference"
    }
    assert any(
        citation["source_id"] == "n5-core-v5.3-pdf" and citation["page"] == 178
        for citation in rule["citations"]
    )
    assert any(
        citation["source_id"] == "wiki-en-20260926-200832"
        and citation["heading"] == "FLAMETHROWERS"
        for citation in rule["citations"]
    )


def test_flamethrower_family_does_not_leak_to_other_weapon(app: Any) -> None:
    rules = [rule["id"] for rule in weapon_detail(app, "flammenspeer")["rules"]]
    assert "weapon:flammenspeer" in rules
    assert "weapon:flamethrowers" not in rules
