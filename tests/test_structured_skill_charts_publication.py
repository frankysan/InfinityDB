"""Release-contract parity for Army Martial Arts, Booty, and MetaChemistry charts."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.database.repository import Database
from infinity_db.structured_chart_outcomes import (
    link_booty_family_outcomes,
    link_booty_weapon_outcomes,
    link_metachemistry_skill_components,
    project_booty_rows,
    project_metachemistry_rows,
)
from infinity_db.web import create_app
from tools.verify_structured_skill_charts_browser import (
    CHARTS,
    source_charts,
    source_only_chart,
)

ROOT = Path(__file__).resolve().parents[1]
ARMY_DB = ROOT / "data/generated/infinity.db"
RULES_DB = ROOT / "data/generated/rules.db"


def _get(app: Any, path: str) -> tuple[str, bytes]:
    environ: dict[str, Any] = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
    statuses: list[str] = []

    def start_response(status: str, _headers: list, _exc_info: object = None) -> None:
        statuses.append(status)

    response = app(environ, start_response)
    try:
        body = b"".join(response)
    finally:
        close = getattr(response, "close", None)
        if close is not None:
            close()
    assert len(statuses) == 1, path
    return statuses[0], body


def _roll_positions(rows: list[dict[str, Any]], chart: str) -> list[int]:
    """Expand source roll ranges without inferring random result semantics."""
    result: list[int] = []
    for row in rows:
        notation = str(row["roll"])
        match = re.fullmatch(r"(\d+)(?:\s*-\s*(\d+))?", notation)
        assert match is not None, (chart, notation)
        low = int(match.group(1))
        high = int(match.group(2) or low)
        assert 1 <= low <= high <= 20, (chart, notation)
        result.extend(range(low, high + 1))
    return result


def test_all_published_structured_skill_charts_preserve_army_rows_and_api() -> None:
    database = Database(ARMY_DB)
    expected = source_charts(database)
    assert set(expected) == {"martial-arts", "booty", "metachemistry"}
    assert set(expected) == set(CHARTS)

    with sqlite3.connect(ARMY_DB) as connection:
        for slug, chart in CHARTS.items():
            rows = expected[slug]["rows"]
            assert rows, slug
            source_columns = ", ".join(chart["columns"])
            stored = [
                dict(zip(chart["columns"], item, strict=True))
                for item in connection.execute(
                    f"SELECT {source_columns} FROM {chart['table']} ORDER BY {chart['order']}"
                )
            ]
            assert [
                {
                    key: value for key, value in row.items()
                    if key not in {"conditional_outcomes", "outcome_components"}
                }
                for row in rows
            ] == stored, slug
            if slug == "martial-arts":
                assert [str(row["level"]) for row in rows] == [
                    "1", "2", "3", "4", "5"
                ]
                assert [int(row["position"]) for row in rows] == list(range(1, 6))
            else:
                covered = _roll_positions(rows, slug)
                assert covered == list(range(1, 21)), (slug, covered)
                assert len({row["id"] for row in rows}) == len(rows), slug

    app = create_app(ARMY_DB, rules_database_path=RULES_DB)
    status, body = _get(app, "/api/skills")
    assert status == "200 OK"
    published = json.loads(body)["items"]
    by_slug = {row["slug"]: row for row in published}
    assert set(CHARTS) <= set(by_slug)

    status, body = _get(app, "/skills")
    assert status == "200 OK"
    assert b'data-catalog="skills"' in body
    assert b"/static/catalog-list.js" in body

    for slug, chart in CHARTS.items():
        status, body = _get(app, f"/api/skills/{slug}")
        assert status == "200 OK", slug
        detail = json.loads(body)
        assert detail["slug"] == slug
        assert detail["name"] == by_slug[slug]["name"]
        structured = detail["structured_reference"]
        assert source_only_chart(structured) == expected[slug], slug
        assert structured["kind"] == chart["kind"], slug
        assert structured["title"] == chart["title"], slug

        status, body = _get(app, f"/skills/{slug}")
        assert status == "200 OK", slug
        assert b"/static/skill.js" in body
        assert b'id="skill-content"' in body

    javascript = (ROOT / "src/infinity_db/web/static/skill.js").read_text(
        encoding="utf-8"
    )
    assert "structuredReferenceSection(skill.structured_reference)" in javascript
    assert 'if (reference.kind === "martial-arts")' in javascript
    assert 'if (reference.kind === "random-chart")' in javascript
    assert "randomChartOutcome(row)" in javascript
    assert "row.conditional_outcomes" in javascript
    assert "chartOutcomeLink(row.result, row.public_reference)" in javascript
    assert "chartOutcomeLink(branch.result, branch.public_reference)" in javascript
    assert 'className = "chart-outcome-branches"' in javascript
    assert 'const hasPsMod = reference.rows.some(' in javascript
    assert '{ label: "Burst MOD", role: "metric" }' in javascript
    stylesheet = (ROOT / "src/infinity_db/web/static/components.css").read_text(
        encoding="utf-8"
    )
    assert ".chart-outcome-branches {\n  white-space: pre-line;" in stylesheet
    assert 'row.outcome_components' in javascript
    assert 'className = "chart-outcome-component"' in javascript
    assert ".chart-outcome-component {\n  display: inline-block;" in stylesheet


def test_current_army_charts_match_reviewed_n5_wiki_reference_rows() -> None:
    """Independently pin entire N5.3 Wiki chart rows, not just source occupancy.

    Reference pages: infinitythewiki.com/{Booty,MetaChemistry,Martial_Arts}.
    Source notation is pinned exactly: Army prints +1SD and +1B
    without the spaces shown in the official Wiki. These represent the
    same named modifiers, not alternate gameplay mechanics.
    """

    database = Database(ARMY_DB)
    booty = {str(row["roll"]): row["result"] for row in database.list_booty_results()}
    expected_booty = {
        "1-2": "+1 ARM",
        "3-4": "Light Flamethrower",
        "5-6": "Grenades",
        "7-8": "DA CC Weapon",
        "9": "Multispectral Visor L1",
        "10": "EXP CC Weapon",
        "11": "Adhesive Launcher Rifle",
        "12": "TAG: Immunity (AP) / Other Troop Types: + 2 ARM",
        "13": "Panzerfaust",
        "14": "Monofilament CC Weapon",
        "15": "MOV 8-4",
        "16": "TAG: BS Attack (Shock) / Other Troop Types: MULTI Rifle",
        "17": "MULTI Sniper Rifle",
        "18": "TAG: Immunity (ARM) / Other Troop Types: +4 ARM",
        "19": "Mimetism (-6)",
        "20": "TAG: BS Attack (+1B) / Other Troop Types: HMG",
    }
    assert booty == expected_booty

    metachemistry = {
        str(row["roll"]): row["result"]
        for row in database.list_metachemistry_results()
    }
    assert metachemistry == {
        "1-3": "+3 PH",
        "4-5": "Super-Jump",
        "6-7": "Regeneration",
        "8-10": "Climbing Plus",
        "11-12": "MOV: 8-4",
        "13-14": "+6 BTS",
        "15": "No Wound Incapacitation",
        "16": "+1 ARM + Immunity (ARM)",
        "17": "Dogged + Immunity (Enhanced)",
        "18": "MOV: 6-4 + Super-Jump",
        "19": "MOV: 8-4 + Climbing Plus",
        "20": "+3 PH + Regeneration",
    }

    martial = {
        str(row["level"]): (
            row["attack_mod"], row["opponent_mod"], row["burst_mod"]
        )
        for row in database.list_martial_arts_levels()
    }
    assert martial == {
        "1": ("0", "-3", "0"),
        "2": ("+3", "-3", "0"),
        "3": ("+3", "-3", "+1SD"),
        "4": ("+3", "-3", "+1B"),
        "5": ("+3", "-3", "+1B, +1SD"),
    }


def test_structured_charts_publish_cited_canonical_skill_rules() -> None:
    """Chart pages must expose the reviewed rules, not only imported Army rows."""

    app = create_app(ARMY_DB, rules_database_path=RULES_DB)
    for slug in ("booty", "metachemistry", "martial-arts"):
        status, body = _get(app, f"/api/skills/{slug}")
        assert status == "200 OK", slug
        detail = json.loads(body)
        owners = [
            item for item in detail["rules"] if item["id"] == f"skill:{slug}"
        ]
        assert len(owners) == 1, slug
        assert owners[0]["citations"], slug
        assert all(
            citation["source_id"] for citation in owners[0]["citations"]
        ), slug


def test_army_chart_source_fields_preserve_n5_reference_distinctions() -> None:
    """Guard reviewed N5 chart distinctions without inventing new game effects."""

    database = Database(ARMY_DB)
    martial_arts = database.list_martial_arts_levels()
    # The N5 Martial Arts chart has Attack, Opponent, and Burst modifiers.
    # The source's extra PS MOD column is not a current rules benefit.
    assert all(row["ps_mod"] in (None, "", "-") for row in martial_arts), martial_arts

    booty = database.list_booty_results()
    conditional = {
        str(row["roll"]): str(row["result"])
        for row in booty
        if "TAG:" in str(row["result"])
    }
    # These four results have different effects for TAGs and other
    # Troop Types; flattening them would change the game outcome.
    assert set(conditional) == {"12", "16", "18", "20"}, conditional
    assert all("Other Troop Types:" in result for result in conditional.values())
    assert all(
        " / Other Troop Types: " in result for result in conditional.values()
    ), conditional

    projected = project_booty_rows(booty)
    assert all("conditional_outcomes" not in row for row in booty)
    assert {row["roll"] for row in projected if "conditional_outcomes" in row} == {
        "12", "16", "18", "20"
    }
    for row in projected:
        if "conditional_outcomes" not in row:
            continue
        branches = row["conditional_outcomes"]
        assert [branch["scope"] for branch in branches] == [
            "tag", "other-troop-types"
        ]
        assert [branch["label"] for branch in branches] == ["TAG", "Other Troop Types"]
        assert " / ".join(
            f"{branch['label']}: {branch['result']}" for branch in branches
        ) == row["result"]


def test_conditional_booty_parser_fails_closed_for_unreviewed_source_syntax() -> None:
    for malformed in (
        "TAG: Immunity (AP)",
        "Other Troop Types: +2 ARM",
        "TAG: / Other Troop Types: +2 ARM",
        "TAG: Immunity (AP) / Other Troop Types: ",
        "TAG: Immunity (AP) / Other Troop Types: +2 ARM / Unknown: X",
    ):
        with pytest.raises(ValueError):
            project_booty_rows([{"id": 12, "roll": "12", "result": malformed}])


def test_metachemistry_compound_source_outcomes_match_reviewed_n5_chart() -> None:
    expected = {
        "16": "+1 ARM + Immunity (ARM)",
        "17": "Dogged + Immunity (Enhanced)",
        "18": "MOV: 6-4 + Super-Jump",
        "19": "MOV: 8-4 + Climbing Plus",
        "20": "+3 PH + Regeneration",
    }
    rows = Database(ARMY_DB).list_metachemistry_results()
    assert {row["roll"]: row["result"] for row in rows if row["roll"] in expected} == expected


def test_metachemistry_compounds_are_typed_and_source_preserving() -> None:
    raw = Database(ARMY_DB).list_metachemistry_results()
    projected = project_metachemistry_rows(raw)
    assert all("outcome_components" not in row for row in raw)
    components = {
        row["roll"]: row["outcome_components"]
        for row in projected
        if "outcome_components" in row
    }
    assert set(components) == {"16", "17", "18", "19", "20"}
    assert {
        roll: [part["kind"] for part in parts]
        for roll, parts in components.items()
    } == {
        "16": ["attribute-modifier", "special-skill"],
        "17": ["special-skill", "special-skill"],
        "18": ["movement-value", "special-skill"],
        "19": ["movement-value", "special-skill"],
        "20": ["attribute-modifier", "special-skill"],
    }
    assert components["16"][0]["attribute"] == "ARM"
    assert components["16"][0]["modifier"] == 1
    assert components["16"][1]["name"] == "Immunity"
    assert components["16"][1]["parameter"] == "ARM"
    assert components["17"][1]["parameter"] == "Enhanced"
    assert components["18"][0]["value"] == "6-4"
    assert components["19"][0]["value"] == "8-4"
    assert components["20"][0]["attribute"] == "PH"
    assert components["20"][0]["modifier"] == 3
    for row in projected:
        parts = row.get("outcome_components")
        if parts is None:
            continue
        assert " + ".join(part["text"] for part in parts) == row["result"]


def test_booty_remaining_catalog_families_are_exact_and_routable() -> None:
    """Verify HMG's expansion and parameterized outcome owner identities."""

    app = create_app(ARMY_DB, rules_database_path=RULES_DB)
    expected = {
        "weapons": {"Heavy Machine Gun": "heavy-machine-gun"},
        "equipment": {"Multispectral Visor": "multispectral-visor"},
        "skills": {"Mimetism": "mimetism", "BS Attack": "bs-attack"},
    }
    source = " / ".join(
        row["result"] for row in Database(ARMY_DB).list_booty_results()
    )
    for literal in (
        "HMG", "Multispectral Visor L1", "Mimetism (-6)",
        "BS Attack (Shock)", "BS Attack (+1B)",
    ):
        assert literal in source
    for catalog, names in expected.items():
        status, body = _get(app, f"/api/{catalog}")
        assert status == "200 OK"
        items = json.loads(body)["items"]
        for name, slug in names.items():
            matches = [
                item for item in items
                if item["name"].casefold() == name.casefold()
            ]
            assert len(matches) == 1, (catalog, name, matches)
            assert matches[0]["slug"] == slug, (catalog, name)
            status, detail_body = _get(app, f"/api/{catalog}/{slug}")
            assert status == "200 OK", (catalog, name)
            detail = json.loads(detail_body)
            assert (detail["slug"], detail["name"]) == (slug, name)
            if catalog == "skills":
                assert any(
                    rule["id"] == f"skill:{slug}"
                    for rule in detail.get("rules", [])
                ), slug


def test_booty_reviewed_family_links_preserve_source_variants() -> None:
    """Assert all reviewed Booty aliases/variants resolve to canonical families."""

    app = create_app(ARMY_DB, rules_database_path=RULES_DB)
    status, body = _get(app, "/api/skills/booty")
    assert status == "200 OK"
    reference = json.loads(body)["structured_reference"]
    source = source_charts(Database(ARMY_DB))["booty"]
    assert source_only_chart(reference) == source

    outcomes = [
        branch
        for row in reference["rows"]
        for branch in (row.get("conditional_outcomes") or [row])
    ]
    expected = {
        "HMG": ("weapons", "heavy-machine-gun", None),
        "Multispectral Visor L1": ("equipment", "multispectral-visor", ("level", "1")),
        "Mimetism (-6)": ("skills", "mimetism", ("modifier", "-6")),
        "BS Attack (Shock)": ("skills", "bs-attack", ("named", "Shock")),
        "BS Attack (+1B)": ("skills", "bs-attack", ("burst-modifier", "+1B")),
        "Immunity (AP)": ("skills", "immunity", ("named", "AP")),
        "Immunity (ARM)": ("skills", "immunity", ("named", "ARM")),
    }
    for printed, (catalog, slug, variant) in expected.items():
        matches = [item for item in outcomes if item["result"] == printed]
        assert len(matches) == 1, printed
        item = matches[0]
        assert item["public_reference"] == {"catalog": catalog, "id": slug}, printed
        if variant is None:
            assert item["reference_name"] == "Heavy Machine Gun"
            assert "outcome_variant" not in item
        else:
            assert item["outcome_variant"] == {
                "kind": variant[0], "value": variant[1]
            }, printed
            assert "reference_name" not in item
    assert sum(item.get("reference_name") == "Heavy Machine Gun" for item in outcomes) == 1
    assert sum("outcome_variant" in item for item in outcomes) == 6


def test_booty_family_links_fail_closed_on_ambiguous_publication() -> None:
    """Reject unresolved or multiply claimed targets without mutating source."""

    original = [
        {"roll": "20", "result": "HMG"},
        {"roll": "9", "result": "Multispectral Visor L1"},
        {"roll": "19", "result": "Mimetism (-6)"},
    ]
    catalogs = {
        "weapons": [{"name": "Heavy Machine Gun", "slug": "heavy-machine-gun"}],
        "equipment": [{"name": "Multispectral Visor", "slug": "multispectral-visor"}],
        "skills": [{"name": "Mimetism", "slug": "mimetism"}],
    }
    reviewed = [
        {"kind": "equipment", "id": "equipment:multispectral-visor",
         "name": "Multispectral Visor"},
        {"kind": "skill", "id": "skill:mimetism", "name": "Mimetism",
         "facts": {"category": "special-skill"}},
    ]
    linked = link_booty_family_outcomes(
        original, public_catalogs=catalogs, reviewed_records=reviewed
    )
    assert all("public_reference" in item for item in linked)
    assert all("public_reference" not in item for item in original)
    for name in ("weapons", "equipment", "skills"):
        duplicate = {key: list(value) for key, value in catalogs.items()}
        duplicate[name] = duplicate[name] * 2
        unresolved = link_booty_family_outcomes(
            original, public_catalogs=duplicate, reviewed_records=reviewed
        )
        index = {"weapons": 0, "equipment": 1, "skills": 2}[name]
        assert "public_reference" not in unresolved[index], name
    for removed in ("equipment", "skill"):
        unresolved = link_booty_family_outcomes(
            original,
            public_catalogs=catalogs,
            reviewed_records=[item for item in reviewed if item["kind"] != removed],
        )
        index = 1 if removed == "equipment" else 2
        assert "public_reference" not in unresolved[index], removed


def test_booty_weapon_names_have_exact_published_catalog_destinations() -> None:
    """Discover only exact Weapon names printed on the N5 Booty chart."""

    chart = Database(ARMY_DB).list_booty_results()
    outcomes = {str(row["result"]) for row in chart}
    expected = {
        "Light Flamethrower",
        "Grenades",
        "DA CC Weapon",
        "EXP CC Weapon",
        "Adhesive Launcher Rifle",
        "Panzerfaust",
        "Monofilament CC Weapon",
        "MULTI Rifle",
        "MULTI Sniper Rifle",
        "HMG",
    }
    source_text = " / ".join(sorted(outcomes))
    assert all(name in source_text for name in expected)

    app = create_app(ARMY_DB, rules_database_path=RULES_DB)
    status, body = _get(app, "/api/weapons")
    assert status == "200 OK"
    items = json.loads(body)["items"]
    missing: set[str] = set()
    for weapon in sorted(expected):
        matches = [
            item for item in items
            if item["name"].casefold() == weapon.casefold()
        ]
        if not matches:
            missing.add(weapon)
            continue
        assert len(matches) == 1, (weapon, matches)
        slug = matches[0]["slug"]
        status, detail_body = _get(app, f"/api/weapons/{slug}")
        assert status == "200 OK", (weapon, slug)
        assert json.loads(detail_body)["slug"] == slug
    # Source chart spells this "HMG"; the published Weapon catalog does not.
    # Keep it unresolved rather than assuming a different catalog name is identical.
    assert missing == {"HMG"}, sorted(missing)

    status, body = _get(app, "/api/skills/booty")
    assert status == "200 OK"
    rows = json.loads(body)["structured_reference"]["rows"]
    linked: dict[str, dict[str, str]] = {}
    for row in rows:
        if "conditional_outcomes" in row:
            for branch in row["conditional_outcomes"]:
                name = branch["result"]
                if name in expected - missing:
                    linked[name] = branch["public_reference"]
        else:
            name = row["result"]
            if name in expected - missing:
                linked[name] = row["public_reference"]
    assert set(linked) == expected - missing
    weapon_by_name = {item["name"].casefold(): item for item in items}
    for name, reference in linked.items():
        assert reference == {
            "catalog": "weapons",
            "id": weapon_by_name[name.casefold()]["slug"],
        }, name


def test_booty_weapon_links_fail_closed_on_unknown_or_duplicate_names() -> None:
    original = [{
        "roll": "3-4", "result": "Light Flamethrower",
    }, {
        "roll": "20",
        "result": "TAG: BS Attack (+1 B) / Other Troop Types: HMG",
        "conditional_outcomes": [
            {"scope": "tag", "label": "TAG", "result": "BS Attack (+1 B)"},
            {"scope": "other-troop-types", "label": "Other Troop Types", "result": "HMG"},
        ],
    }]
    published = [{"name": "Light Flamethrower", "slug": "light-flamethrower"}]
    linked = link_booty_weapon_outcomes(original, public_weapons=published)
    assert linked[0]["public_reference"] == {
        "catalog": "weapons", "id": "light-flamethrower"
    }
    assert "public_reference" not in linked[1]["conditional_outcomes"][0]
    assert "public_reference" not in linked[1]["conditional_outcomes"][1]
    assert "public_reference" not in original[0]
    assert "public_reference" not in original[1]["conditional_outcomes"][1]
    for weapons in ([], published * 2):
        unresolved = link_booty_weapon_outcomes(original, public_weapons=weapons)
        assert "public_reference" not in unresolved[0]


def test_metachemistry_skill_components_have_unambiguous_public_definitions() -> None:
    """Link only canonical Skill families present in the current public catalog."""

    app = create_app(ARMY_DB, rules_database_path=RULES_DB)
    status, body = _get(app, "/api/skills")
    assert status == "200 OK"
    expected = {
        "Immunity": "immunity",
        "Dogged": "dogged",
        "Super-Jump": "super-jump",
        "Climbing Plus": "climbing-plus",
        "Regeneration": "regeneration",
    }
    items = json.loads(body)["items"]
    for name, slug in expected.items():
        candidates = [
            item for item in items
            if item["name"].casefold() == name.casefold()
        ]
        assert len(candidates) == 1, (name, candidates)
        assert candidates[0]["slug"] == slug, name
        status, body = _get(app, f"/api/skills/{slug}")
        assert status == "200 OK", slug
        detail = json.loads(body)
        assert detail["slug"] == slug
        assert detail["name"].casefold() == name.casefold()
        assert any(
            rule["id"] == f"skill:{slug}"
            for rule in detail.get("rules", [])
        ), slug

    status, body = _get(app, "/api/skills/metachemistry")
    assert status == "200 OK"
    rows = json.loads(body)["structured_reference"]["rows"]
    linked_names: set[str] = set()
    for row in rows:
        for component in row.get("outcome_components", []):
            if component["kind"] != "special-skill":
                assert "public_reference" not in component
                continue
            name = component["name"]
            assert component["public_reference"] == {
                "catalog": "skills", "id": expected[name]
            }, (row["roll"], name)
            linked_names.add(name)
    assert linked_names == set(expected)
    assert next(row for row in rows if row["roll"] == "16")[
        "outcome_components"
    ][1]["parameter"] == "ARM"
    assert next(row for row in rows if row["roll"] == "17")[
        "outcome_components"
    ][1]["parameter"] == "Enhanced"


def test_metachemistry_skill_links_fail_closed_on_ambiguous_definitions() -> None:
    original = [{
        "roll": "18",
        "result": "MOV: 6-4 + Super-Jump",
        "outcome_components": [
            {"kind": "movement-value", "text": "MOV: 6-4", "value": "6-4"},
            {"kind": "special-skill", "text": "Super-Jump", "name": "Super-Jump"},
        ],
    }]
    reviewed = [{
        "kind": "skill",
        "id": "skill:super-jump",
        "name": "Super-Jump",
        "facts": {"category": "special-skill"},
    }]
    published = [{"name": "Super-Jump", "slug": "super-jump"}]
    linked = link_metachemistry_skill_components(
        original, reviewed_records=reviewed, public_skills=published
    )
    assert linked[0]["outcome_components"][1]["public_reference"] == {
        "catalog": "skills", "id": "super-jump"
    }
    assert "public_reference" not in original[0]["outcome_components"][1]
    assert "public_reference" not in linked[0]["outcome_components"][0]

    for records, skills in (
        ([], published),
        (reviewed, []),
        (reviewed * 2, published),
        (reviewed, published * 2),
        (reviewed, [{"name": "Super-Jump", "slug": "wrong-route"}]),
    ):
        unresolved = link_metachemistry_skill_components(
            original, reviewed_records=records, public_skills=skills
        )
        assert "public_reference" not in unresolved[0]["outcome_components"][1]


def test_metachemistry_compound_parser_rejects_unreviewed_formats() -> None:
    rows = Database(ARMY_DB).list_metachemistry_results()
    for malformed in (
        "MOV: 6-4 + Mystery",
        "MOV: 6-4",
        "MOV: 6-4 + Super-Jump + Regeneration",
        "MOV: 6-4 + ",
        "Dogged + Immunity",
    ):
        modified = [
            {**row, "result": malformed} if row["roll"] == "18" else row
            for row in rows
        ]
        with pytest.raises(ValueError):
            project_metachemistry_rows(modified)
    # Partial fixture charts are supported; the full publication test
    # separately requires the exact five source-owned compound rolls.
    partial = [row for row in rows if row["roll"] not in {"16", "17", "18", "19", "20"}]
    assert project_metachemistry_rows(partial) == partial
    with pytest.raises(ValueError, match="Duplicate MetaChemistry compound"):
        project_metachemistry_rows([*rows, next(row for row in rows if row["roll"] == "20")])


def test_roll_range_audit_detects_gaps_overlaps_and_invalid_notation() -> None:
    assert _roll_positions([
        {"roll": "1-3"}, {"roll": "4"}, {"roll": "5-20"},
    ], "test") == list(range(1, 21))
    for rows in (
        [{"roll": "1-3"}, {"roll": "3-20"}],
        [{"roll": "1-3"}, {"roll": "5-20"}],
    ):
        assert _roll_positions(rows, "test") != list(range(1, 21))
    for invalid in ("0", "21", "10-9", "1;20", "special"):
        with pytest.raises(AssertionError):
            _roll_positions([{"roll": invalid}], "test")
