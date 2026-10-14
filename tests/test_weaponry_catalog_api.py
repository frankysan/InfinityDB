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

from infinity_db.rules_database import RulesDatabase
from infinity_db.web import create_app


@pytest.fixture(scope="module")
def weaponry_app() -> Callable:
    root = Path(__file__).resolve().parents[1]
    return create_app(
        root / "data/generated/infinity.db",
        rules_database_path=root / "data/generated/rules.db",
    )


def _weapon_detail(
    app: Callable, slug: str, *, catalog: str = "weapons"
) -> dict[str, Any]:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=f"/api/{catalog}/{slug}", REQUEST_METHOD="GET")
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
    assert "source discrepancy" in record["facts"]["sourceNotes"][0]
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
    assert "source discrepancy" in rule["facts"]["sourceNotes"][0]
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
    for profile in profiles.values():
        alias = next(
            reference for reference in profile["trait_references"]
            if reference["label"] == "Technical Weapon"
        )
        assert alias == {
            "label": "Technical Weapon",
            "name": "BS Weapon (WIP)",
            "slug": "bs-weapon-wip",
            "source_alias": True,
        }
    assert profiles[203]["burst"] == "1"


@pytest.mark.parametrize(
    ("slug", "record_id", "pages", "phrases", "relations"),
    [
        (
            "d-charges",
            "weapon:d-charges",
            {70, 186},
            (
                "Demolition Mode",
                "[[trait:cc|CC]] Mode",
                "same three charges",
                "cannot be used",
                "detonates in the Resolution Step",
                "does not affect the user",
            ),
            {"skill:place-deployable", "trait:disposable-x", "trait:improvised"},
        ),
        (
            "disco-baller",
            "weapon:disco-baller",
            {71, 186},
            (
                "Conclusion Step",
                "States Phase",
                "Eclipse",
                "Activate Disco Ball",
                "enemy Ball",
                "Double Shot",
            ),
            {"ammunition:eclipse", "equipment:deactivator", "trait:double-shot"},
        ),
    ],
)
def test_reviewed_weapon_source_prose_has_separate_modes_and_sources(
    weaponry_app: Callable,
    slug: str,
    record_id: str,
    pages: set[int],
    phrases: tuple[str, ...],
    relations: set[str],
) -> None:
    payload = _weapon_detail(weaponry_app, slug)
    rules = _weapon_rules(payload)
    assert record_id in rules
    record = rules[record_id]
    assert all(phrase in record["summary"] for phrase in phrases)
    assert pages <= {
        citation["page"] for citation in record["citations"]
        if citation["source_id"] == "n5-core-v5.3-pdf"
    }
    assert relations <= {
        relation["record"]["id"]
        for relation in record["display_relations"]
        if relation["direction"] == "outbound"
    }
    assert any(
        citation["source_id"] == "wiki-en-20260926-200832"
        for citation in record["citations"]
    )


def test_d_charges_and_disco_baller_keep_army_modes_separate(
    weaponry_app: Callable,
) -> None:
    charges = _weapon_detail(weaponry_app, "d-charges")
    assert {profile["mode"] for profile in charges["profiles"]} == {
        "CC Mode", "Demolition Mode"
    }
    assert all(profile["ammunition"] == "AP+Exp" for profile in charges["profiles"])
    assert all(profile["saving_num"] == "3" for profile in charges["profiles"])
    assert all(profile["damage"] == "6" for profile in charges["profiles"])
    assert all("Disposable (3)" in profile["traits"] for profile in charges["profiles"])
    assert all(
        rule["id"] == "weapon:d-charges" for rule in charges.get("rules", [])
    )
    disco = _weapon_detail(weaponry_app, "disco-baller")
    launcher = next(profile for profile in disco["profiles"] if profile["mode"] is None)
    ball = next(profile for profile in disco["profiles"] if profile["mode"] == "Disco Ball")
    assert "Double Shot" in launcher["traits"]
    assert "Disposable (2)" in launcher["traits"]
    assert ball["profile"] == "ARM=0, BTS=0, STR=1, S=1"
    assert ball["ammunition"] == 0
    assert ball["saving_num"] == "-"


@pytest.mark.parametrize(
    ("slug", "page", "ammunition", "saving", "template", "linked_rules"),
    [
        ("chain-colt", 186, "N", "ARM", "Small Teardrop",
         {"ammunition:normal", "trait:direct-template", "skill:intuitive-attack"}),
        ("chain-rifle", 186, "N", "ARM", "Large Teardrop",
         {"ammunition:normal", "trait:direct-template", "skill:intuitive-attack"}),
        ("nanopulser", 187, "N", "BTS", "Small Teardrop",
         {"ammunition:normal", "trait:direct-template", "skill:intuitive-attack"}),
        ("pulzar", 187, "N", "BTS", "Large Teardrop",
         {"ammunition:normal", "trait:direct-template", "skill:intuitive-attack"}),
        ("e-mitter", 186, "E/M", "BTS/2", "two BTS/2 Saving Rolls",
         {"ammunition:em", "trait:non-lethal"}),
    ],
)
def test_first_weapon_batch_links_printed_profiles_and_applicable_effects(
    weaponry_app: Callable, slug: str, page: int, ammunition: str,
    saving: str, template: str, linked_rules: set[str],
) -> None:
    payload = _weapon_detail(weaponry_app, slug)
    assert len(payload["profiles"]) == 1
    assert payload["profiles"][0]["ammunition"] == ammunition
    assert payload["profiles"][0]["saving"] == saving
    record = _weapon_rules(payload)[f"weapon:{slug}"]
    assert template in record["summary"]
    assert {reference["record"]["id"] for reference in record["display_relations"]
            if reference["direction"] == "outbound"} >= linked_rules
    assert any(source["source_id"] == "n5-core-v5.3-pdf"
               and source["page"] == page for source in record["citations"])


def test_missile_launcher_preserves_distinct_hit_and_blast_mode_effects(
    weaponry_app: Callable,
) -> None:
    payload = _weapon_detail(weaponry_app, "missile-launcher")
    profiles = {profile["mode"]: profile for profile in payload["profiles"]}
    assert set(profiles) == {"Blast Mode", "Hit Mode"}
    assert profiles["Blast Mode"]["ammunition"] == "Exp"
    assert profiles["Blast Mode"]["saving"] == "ARM"
    assert profiles["Blast Mode"]["saving_num"] == "3"
    assert "Impact Template (Circular)" in profiles["Blast Mode"]["traits"]
    assert profiles["Hit Mode"]["ammunition"] == "AP+Exp"
    assert profiles["Hit Mode"]["saving"] == "ARM/2"
    assert profiles["Hit Mode"]["saving_num"] == "3"
    assert "Impact Template (Circular)" not in profiles["Hit Mode"]["traits"]
    record = _weapon_rules(payload)["weapon:missile-launcher"]
    assert "Blast Mode" in record["summary"] and "Hit Mode" in record["summary"]
    assert {r["record"]["id"] for r in record["display_relations"]
            if r["direction"] == "outbound"} >= {
                "ammunition:exp", "ammunition:ap",
                "trait:impact-template", "trait:anti-materiel",
            }


def test_activate_disco_ball_is_source_only_skill_with_working_weapon_link(
    weaponry_app: Callable,
) -> None:
    skill = _weapon_detail(weaponry_app, "activate-disco-ball", catalog="skills")
    assert skill["name"] == "Activate Disco Ball"
    assert skill["variants"] == []
    record = {r["id"]: r for r in skill["rules"]}["skill:activate-disco-ball"]
    assert "WIP +3" in record["summary"]
    assert "Enemy Disco Balls cannot be activated" in record["summary"]
    assert "Conclusion Step" in record["summary"]
    assert any(c["source_id"] == "n5-core-v5.3-pdf" and c["page"] == 71
               for c in record["citations"])
    assert any(c["source_id"] == "wiki-en-20260926-200832"
               and c["member"] == "Activate_Disco_Ball"
               for c in record["citations"])
    disco = _weapon_rules(_weapon_detail(weaponry_app, "disco-baller"))[
        "weapon:disco-baller"
    ]
    assert any(token["type"] == "reference"
               and token["target"] == "skill:activate-disco-ball"
               for token in disco["summary_tokens"])
    assert any(rel["record"]["id"] == "skill:activate-disco-ball"
               and rel["direction"] == "outbound"
               for rel in disco["display_relations"])


@pytest.mark.parametrize(
    ("slug", "ammo", "saving", "count", "ps"),
    [
        ("cc-weapon", "N", "ARM", "1", "8"),
        ("para-cc-weapon", "PARA", "PH-6", "1", "-"),
        ("da-cc-weapon", "DA", "ARM", "2", "8"),
        ("ap-cc-weapon", "AP", "ARM/2", "1", "8"),
        ("shock-cc-weapon", "Shock", "ARM", "1", "8"),
        ("e-m-cc-weapon", "N+E/M", "BTS/2", "2", "8"),
        ("exp-cc-weapon", "Exp", "ARM", "3", "8"),
        ("viral-cc-weapon", "N", "BTS", "1", "8"),
    ],
)
def test_cc_weapon_rules_have_pinned_chart_source(
    weaponry_app: Callable, slug: str, ammo: str, saving: str,
    count: str, ps: str,
) -> None:
    payload = _weapon_detail(weaponry_app, slug)
    assert len(payload["profiles"]) == 1
    profile = payload["profiles"][0]
    assert (
        profile["ammunition"], profile["saving"], profile["saving_num"],
        profile["damage"], profile["burst"],
    ) == (ammo, saving, count, ps, "1")
    record = _weapon_rules(payload)[f"weapon:{slug}"]
    assert any(
        c["page"] == 177 and c["source_id"] == "n5-core-v5.3-pdf"
        for c in record["citations"]
    )


def test_exp_and_viral_cc_weapons_preserve_profile_and_conditioned_effects(
    weaponry_app: Callable,
) -> None:
    exp = _weapon_detail(weaponry_app, "exp-cc-weapon")
    exp_profile = exp["profiles"][0]
    assert (exp_profile["ammunition"], exp_profile["saving"],
            exp_profile["saving_num"]) == ("Exp", "ARM", "3")
    assert "Anti-materiel" in exp_profile["traits"]
    exp_rule = _weapon_rules(exp)["weapon:exp-cc-weapon"]
    assert {"ammunition:exp", "trait:anti-materiel", "trait:cc"} <= {
        relation["record"]["id"]
        for relation in exp_rule["display_relations"]
        if relation["direction"] == "outbound"
    }
    assert "three ARM Saving Rolls" in exp_rule["summary"]

    viral = _weapon_detail(weaponry_app, "viral-cc-weapon")
    viral_profile = viral["profiles"][0]
    assert (viral_profile["ammunition"], viral_profile["saving"],
            viral_profile["saving_num"]) == ("N", "BTS", "1")
    assert "Bioweapon (DA+SHOCK)" in viral_profile["traits"]
    viral_rule = _weapon_rules(viral)["weapon:viral-cc-weapon"]
    assert {"ammunition:normal", "ammunition:da", "ammunition:shock",
            "trait:bioweapon", "trait:cc"} <= {
        relation["record"]["id"]
        for relation in viral_rule["display_relations"]
        if relation["direction"] == "outbound"
    }
    assert "against VITA" in viral_rule["summary"]
    assert "Against STR" in viral_rule["summary"]
    assert "(derived)" in viral_rule["summary"]
    assert "one-BTS-roll baseline" in viral_rule["summary"]
    assert any(
        citation["source_id"] == "wiki-traits-oldid-4110"
        and citation["heading"] == "BioWeapon"
        for citation in viral_rule["citations"]
    )


@pytest.mark.parametrize(
    ("slug", "modes", "linked_rules"),
    [
        ("pistol", [(None, "N", "ARM", "1", "9", "2", [])],
         {"ammunition:normal", "skill:bs-attack"}),
        ("heavy-pistol", [(None, "Shock", "ARM", "1", "6", "2", [])],
         {"ammunition:shock", "skill:bs-attack"}),
        ("boarding-pistol", [
            ("Blast Mode", "N", "ARM", "1", "7", "1",
             ["Intuitive Attack", "Direct Template (Small Teardrop)"]),
            ("Hit Mode", "N", "ARM", "1", "7", "2", []),
        ], {"ammunition:normal", "trait:direct-template",
            "skill:intuitive-attack", "skill:bs-attack"}),
        ("breaker-pistol", [(None, "AP", "BTS/2", "1", "8", "2", [])],
         {"ammunition:ap"}),
        ("assault-pistol", [(None, "N", "ARM", "1", "7", "4", [])],
         {"ammunition:normal", "skill:bs-attack"}),
        ("ap-heavy-pistol", [(None, "AP", "ARM/2", "1", "6", "2", [])],
         {"ammunition:ap"}),
        ("silenced-pistol", [
            (None, "AP+Shock", "BTS/2", "1", "8", "2", ["Silent (-6)"]),
        ], {"ammunition:ap", "ammunition:shock", "trait:silent-x",
            "skill:dodge"}),
        ("multi-pistol", [
            ("Anti-Material Mode", "DA", "ARM", "2", "7", "1",
             ["Anti-materiel"]),
            ("AP Mode", "AP", "ARM/2", "1", "7", "2", []),
            ("Shock Mode", "Shock", "ARM", "1", "7", "2", []),
        ], {"ammunition:ap", "ammunition:da", "ammunition:shock",
            "trait:anti-materiel"}),
    ],
)
def test_pistol_rules_match_exact_army_mode_profiles(
    weaponry_app: Callable,
    slug: str,
    modes: list[tuple],
    linked_rules: set[str],
) -> None:
    payload = _weapon_detail(weaponry_app, slug)
    actual_modes = [
        (p["mode"], p["ammunition"], p["saving"], p["saving_num"],
         p["damage"], p["burst"], p["traits"])
        for p in payload["profiles"]
    ]
    assert actual_modes == modes
    record = _weapon_rules(payload)[f"weapon:{slug}"]
    assert linked_rules <= {
        relation["record"]["id"]
        for relation in record["display_relations"]
        if relation["direction"] == "outbound"
    }
    assert any(
        citation["source_id"] == "n5-core-v5.3-pdf" and citation["page"] == 182
        for citation in record["citations"]
    )


def test_boarding_multi_and_silenced_pistol_mode_exceptions(
    weaponry_app: Callable,
) -> None:
    boarding = _weapon_detail(weaponry_app, "boarding-pistol")
    assert boarding["profiles"][0]["ranges"] == {}
    assert boarding["profiles"][1]["ranges"]
    summary = _weapon_rules(boarding)["weapon:boarding-pistol"]["summary"]
    assert "Blast Mode" in summary and "Hit Mode" in summary
    assert "not Hit Mode" in summary

    multi = _weapon_detail(weaponry_app, "multi-pistol")
    summary = _weapon_rules(multi)["weapon:multi-pistol"]["summary"]
    assert "effects are not combined" in summary
    assert "Anti-Materiel" in summary
    assert "two ARM Saving Rolls" in summary

    silenced = _weapon_detail(weaponry_app, "silenced-pistol")
    summary = _weapon_rules(silenced)["weapon:silenced-pistol"]["summary"]
    assert "one BTS/2 Saving Roll" in summary
    assert "outside their LoF" in summary
    assert "Face to Face" in summary
    assert "not a general -6" in summary
    assert {c["page"] for c in _weapon_rules(silenced)[
        "weapon:silenced-pistol"]["citations"]
        if c["source_id"] == "n5-core-v5.3-pdf"
    } == {67, 175, 182}


def test_symbiobomb_has_cited_weaponry_rules_without_fabricated_profile(
    weaponry_app: Callable,
) -> None:
    payload = _weapon_detail(weaponry_app, "symbiobomb")
    assert payload["name"] == "SymbioBomb"
    assert payload["profiles"] == []
    assert payload["weapon_variants"] == []
    assert set(_weapon_rules(payload)) == {"weapon:symbiobomb"}
    rule = _weapon_rules(payload)["weapon:symbiobomb"]
    assert "During Deployment" in rule["summary"]
    assert "Endgame, Eraser, or Mirrorball" in rule["summary"]
    assert "this MOD does not apply to Mirrorball" in rule["summary"]
    assert "at the end of the Order" in rule["summary"]
    assert "no separate attack profile" in rule["summary"]
    assert {
        (citation["source_id"], citation["page"])
        for citation in rule["citations"]
        if citation["source_id"] == "n5-core-v5.3-pdf"
    } == {("n5-core-v5.3-pdf", 74)}
    assert any(
        citation["source_id"] == "wiki-en-20260926-200832"
        and citation["member"] == "SymbioBomb"
        for citation in rule["citations"]
    )
    assert any(
        relation["record"]["id"] == "weapon:pt"
        and relation["direction"] == "outbound"
        for relation in rule["display_relations"]
    )
    assert any(
        token.get("target") == "weapon:pt"
        and token["type"] == "reference"
        for token in rule["summary_tokens"]
    )


def test_para_mine_has_own_reference_without_rewriting_source_marker(
    weaponry_app: Callable,
) -> None:
    para = _weapon_detail(weaponry_app, "para-mine")
    rules = _weapon_rules(para)
    assert {"weapon:mines", "weapon:para-mine"} <= rules.keys()
    assert "weapon:para-mine" not in _weapon_rules(
        _weapon_detail(weaponry_app, "ap-mine")
    )
    record = rules["weapon:para-mine"]
    assert "unresolved source-reference discrepancy" in record["facts"]["sourceNotes"][0]
    note = record["facts"]["sourceNotes"][0]
    assert "[*]" in note and "[**]" in note
    assert {72, 176, 181} <= {source["page"] for source in record["citations"]}
    assert {"weapon:mines", "ammunition:para", "state:immobilized-a"} <= {
        relation["record"]["id"]
        for relation in record["display_relations"]
        if relation["direction"] == "outbound"
    }
    assert {"weapon:mines", "ammunition:para", "state:immobilized-a"} <= {
        token["target"]
        for token in record["summary_tokens"]
        if token["type"] == "reference"
    }
    profile = para["profiles"][0]
    assert profile["ammunition"] == "PARA"
    assert profile["saving"] == "PH-6"
    assert "[**]" in profile["traits"]
    assert "[*]" not in profile["traits"]


def test_kobra_cc_mode_reference_preserves_anti_materiel_conflict(
    weaponry_app: Callable,
) -> None:
    payload = _weapon_detail(weaponry_app, "kobra-pistol")
    shared = _weapon_rules(payload)
    assert set(shared) == {"weapon:kobra-pistol"}
    assert "Shock Ammunition" in shared["weapon:kobra-pistol"]["summary"]

    profiles = {profile["mode"]: profile for profile in payload["profiles"]}
    assert "rules" not in profiles["BS Mode"]
    assert profiles["BS Mode"]["ammunition"] == "Shock"
    assert "Anti-materiel" not in profiles["BS Mode"]["traits"]

    cc = profiles["CC Mode"]
    assert cc["ammunition"] == "DA"
    assert cc["saving_num"] == "2"
    assert "Anti-materiel" in cc["traits"]  # The imported value is preserved.
    assert [rule["id"] for rule in cc["rules"]] == ["weapon:kobra-pistol-cc"]
    record = cc["rules"][0]
    assert record["variant_semantics"] == {
        "inheritance": "source", "source_mode": "CC Mode"
    }
    assert "unresolved source discrepancy" in record["facts"]["sourceNotes"][0]
    assert "two ARM Saving Rolls" in record["summary"]
    assert any(
        token["target"] == "trait:anti-materiel"
        for token in record["fact_tokens"]["sourceNotes"][0]
        if token["type"] == "reference"
    )
    assert {64, 68, 182} == {citation["page"] for citation in record["citations"]}
    assert {
        (relation["type"], relation["record"]["id"])
        for relation in record["display_relations"]
        if relation["direction"] == "outbound"
    } == {
        ("variant-of", "weapon:kobra-pistol"),
        ("uses-effects-of", "ammunition:da"),
    }
    for variant in payload["variants"]:
        assert "rules" not in variant  # No source-wide leak.
    for variant in payload["weapon_variants"]:
        by_mode = {p["mode"]: p for p in variant["profiles"]}
        assert "rules" not in by_mode["BS Mode"]
        assert [r["id"] for r in by_mode["CC Mode"]["rules"]] == [
            "weapon:kobra-pistol-cc"
        ]


def test_kobra_pistol_modes_share_source_id_but_not_effects(
    weaponry_app: Callable,
) -> None:
    item = _weapon_detail(weaponry_app, "kobra-pistol")
    profiles = {profile["mode"]: profile for profile in item["profiles"]}
    assert set(profiles) == {"BS Mode", "CC Mode"}
    assert profiles["BS Mode"]["id"] == profiles["CC Mode"]["id"] == 221
    assert profiles["BS Mode"]["ammunition"] == "Shock"
    assert profiles["CC Mode"]["ammunition"] == "DA"
    assert "Anti-materiel" not in profiles["BS Mode"]["traits"]
    assert "Anti-materiel" in profiles["CC Mode"]["traits"]


def test_drop_bears_keeps_two_modes_and_explains_n5_throwing_terminology(
    weaponry_app: Callable,
) -> None:
    payload = _weapon_detail(weaponry_app, "drop-bears")
    assert payload["id"] == 96
    assert set(_weapon_rules(payload)) == {"weapon:drop-bears"}

    profiles = {profile["mode"]: profile for profile in payload["profiles"]}
    assert set(profiles) == {"BS Mode", "Deployable Mode"}
    bs = profiles["BS Mode"]
    deployable = profiles["Deployable Mode"]
    # The Army snapshot really contains both labels; do not silently rewrite it.
    assert {"BS Weapon (PH)", "Throwing Weapon"} <= set(bs["traits"])
    bs_refs = {reference["label"]: reference for reference in bs["trait_references"]}
    assert bs_refs["Throwing Weapon"]["source_alias"] is True
    assert bs_refs["Throwing Weapon"]["name"] == "BS Weapon (PH)"
    assert bs_refs["BS Weapon (PH)"]["slug"] == "bs-weapon-ph"
    assert "source_alias" not in bs_refs["BS Weapon (PH)"]
    assert bs["ammunition"] == 0
    assert bs["ranges"]["short"] == {"max": 20, "mod": "+3"}
    assert deployable["ammunition"] == "Shock"
    assert deployable["saving"] == "ARM"
    assert "Throwing Weapon" not in deployable["traits"]

    card = _weapon_rules(payload)["weapon:drop-bears"]
    summary = card["summary"]
    for phrase in (
        "Deployable", "BS Mode", "Disposable (3)", "Mine Token",
        "Camouflage", "Conclusion step", "cannot detonate",
        "Trigger Area", "BS Weapon (PH)",
    ):
        assert phrase in summary
    assert summary.count("\n\n") == 3
    assert "**BS Mode:**" in summary
    assert "Throwing Weapon" not in summary
    assert len(card["facts"]["sourceNotes"]) == 1
    assert "Throwing Weapon" in card["facts"]["sourceNotes"][0]
    assert any(
        token.get("target") == "trait:bs-weapon-ph"
        for token in card["fact_tokens"]["sourceNotes"][0]
    )
    assert all(profile.get("rules", []) == [] for profile in profiles.values())
    assert any(
        citation["source_id"] == "n5-core-v5.3-pdf"
        and citation["source_version"] == "5.3"
        and citation["page"] == 71
        for citation in card["citations"]
    )
    assert any(
        relation["type"] == "modifies-use-of"
        and relation["record"]["id"] == "weapon:mines"
        for relation in card["display_relations"]
    )
    # Drop Bears are not eligible for the shared Mines card's marker placement.
    assert "weapon:mines" not in _weapon_rules(payload)
    assert card["summary_tokens"]


def test_monofilament_state_trait_links_to_dead_state(weaponry_app: Callable) -> None:
    profile = _weapon_detail(weaponry_app, "monofilament-mine")["profiles"][0]
    state = next(
        reference for reference in profile["trait_references"]
        if reference["label"] == "State: Dead"
    )
    assert state["public_reference"] == {"catalog": "states", "id": "dead"}
    assert state["slug"] is None  # States are not Traits.


@pytest.mark.parametrize(
    ("slug", "ps", "disposable", "rule_id"),
    (
        ("sepsitor", "4", True, "weapon:sepsitor"),
        ("sepsitor-plus", "3", False, "weapon:sepsitor-plus"),
    ),
)
def test_sepsitor_weaponry_rules_keep_distinct_army_profiles(
    weaponry_app: Callable, slug: str, ps: str, disposable: bool, rule_id: str
) -> None:
    payload = _weapon_detail(weaponry_app, slug)
    assert len(payload["profiles"]) == 1
    profile = payload["profiles"][0]
    assert (profile["damage"], profile["saving"], profile["saving_num"]) == (
        ps, "BTS", "1"
    )
    assert ("Disposable (2)" in profile["traits"]) is disposable
    assert ("[*]" in profile["traits"]) is disposable
    assert "State: Sepsitorized" in profile["traits"]
    references = {ref["label"]: ref for ref in profile["trait_references"]}
    assert references["State: Sepsitorized"] == {
        "label": "State: Sepsitorized",
        "name": "Sepsitorized State",
        "slug": None,
        "public_reference": {"catalog": "states", "id": "sepsitorized"},
    }

    rules = _weapon_rules(payload)
    assert set(rules) == {rule_id}
    rule = rules[rule_id]
    assert any(
        citation["source_id"] == "n5-core-v5.3-pdf"
        and citation["source_version"] == "5.3"
        and citation["page"] == 73
        for citation in rule["citations"]
    )
    assert rule["summary_tokens"]
    linked = {
        relation["record"]["id"]
        for relation in rule["display_relations"]
        if relation["record"] is not None
    }
    assert {"state:sepsitorized", "equipment:cube", "equipment:cube-2"} <= linked
    assert ("trait:disposable-x" in linked) is disposable


def test_cube_two_references_both_sepsitor_variants() -> None:
    db = RulesDatabase(Path(__file__).resolve().parents[1] / "data/generated/rules.db")
    record = db.composed_record("equipment:cube-2")
    assert record is not None
    links = {
        relation["record_id"]
        for relation in record["relations"]
        if relation["type"] == "modifies-rolls-for"
    }
    assert {"weapon:sepsitor", "weapon:sepsitor-plus"} <= links


def test_ammunition_metadata_links_are_reviewed_base_types(
    weaponry_app: Callable,
) -> None:
    # N, AP and DA are different source identities even when their weapon
    # profile stats or Saving Roll notations happen to look alike.
    cases = {
        "ap-heavy-machine-gun": ("AP", "ap", "ARM/2"),
        "da-cc-weapon": ("DA", "da", "ARM"),
    }
    for slug, (name, target, saving) in cases.items():
        payload = _weapon_detail(weaponry_app, slug)
        profile = payload["profiles"][0]
        assert profile["ammunition"] == name
        assert profile["saving"] == saving
        assert profile["ammunition_parts"] == [
            {
                "text": name,
                "public_reference": {"catalog": "ammunition", "id": target},
            }
        ]


def test_combined_ammunition_components_do_not_change_saving_rolls(
    weaponry_app: Callable,
) -> None:
    payload = _weapon_detail(weaponry_app, "feuerbach")
    profile = next(profile for profile in payload["profiles"] if profile["mode"] == "Burst Mode")
    assert profile["ammunition"] == "AP+DA"
    assert profile["ammunition_source_id"] == 10
    assert profile["ammunition_parts"] == [
        {"text": "AP", "public_reference": {"catalog": "ammunition", "id": "ap"}},
        {"text": "+"},
        {"text": "DA", "public_reference": {"catalog": "ammunition", "id": "da"}},
    ]
    assert profile["ammunition_composition"]["kind"] == "combined"
    assert [
        component["record_id"]
        for component in profile["ammunition_composition"]["components"]
    ] == ["ammunition:ap", "ammunition:da"]
    assert profile["saving"] == "ARM/2"
    assert str(profile["saving_num"]) == "2"


@pytest.mark.parametrize(
    ("slug", "source_id", "ammunition", "components", "saving", "rolls"),
    (
        ("missile-launcher", 13, "AP+Exp", ("ap", "exp"), "ARM/2", "3"),
        ("uragan-mrl", 30, "AP+Shock", ("ap", "shock"), "ARM/2", "1"),
        ("ap-t2-cc-weapon", 40, "AP+T2", ("ap", "t2"), "ARM/2", "1"),
    ),
)
def test_reviewed_combined_ammunition_exposes_typed_components(
    weaponry_app: Callable,
    slug: str,
    source_id: int,
    ammunition: str,
    components: tuple[str, str],
    saving: str,
    rolls: str,
) -> None:
    payload = _weapon_detail(weaponry_app, slug)
    profile = next(p for p in payload["profiles"] if p["ammunition_source_id"] == source_id)
    assert profile["ammunition"] == ammunition
    assert profile["ammunition_composition"] == {
        "kind": "combined",
        "components": [
            {
                "record_id": f"ammunition:{component}",
                "public_reference": {"catalog": "ammunition", "id": component},
            }
            for component in components
        ],
    }
    assert [segment["text"] for segment in profile["ammunition_parts"]] == [
        "AP", "+", ammunition.split("+", 1)[1],
    ]
    assert profile["saving"] == saving
    assert str(profile["saving_num"]) == rolls


def test_unreviewed_ammunition_identity_is_not_inferred_from_punctuation(
    weaponry_app: Callable,
) -> None:
    payload = _weapon_detail(weaponry_app, "missile-launcher")
    profile = next(profile for profile in payload["profiles"] if profile["mode"] == "Hit Mode")
    assert profile["ammunition_composition"]["kind"] == "combined"
    assert profile["saving"] == "ARM/2"
    # A matching Saving Roll expression is not an additional ammunition component.
    assert len(profile["ammunition_composition"]["components"]) == 2
