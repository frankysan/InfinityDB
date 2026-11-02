"""Characterize pinned source-level Skill/Equipment parameters before usage indexing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import RulesDatabase, export_rules_database
from tools.audit_source_variant_inputs import (
    inventory_source_variants,
    reviewed_extra_signature,
    select_source_variants,
    source_extra_owner_context,
)

ROOT = Path(__file__).resolve().parents[1]


def test_source_variant_selection_preserves_full_summary_and_exact_ids() -> None:
    report = {"catalogs": {
        "skills": {"summary": {"publishedSourceIds": 2}, "items": [
            {"id": 28, "extraSignatures": [{"extras": [[6, "TEXT", "-3"]], "count": 5}]},
            {"id": 40, "extraSignatures": [{"extras": [[11, "DISTANCE", "+2.5"]], "count": 3}]},
        ]},
        "equipment": {"summary": {"publishedSourceIds": 1}, "items": [
            {"id": 169, "extraSignatures": [{"extras": [[7, "TEXT", "-6"]], "count": 2}]},
        ]},
    }}
    selected = select_source_variants(report, "equipment", [169, 169])
    assert selected == {
        "catalog": "equipment",
        "fullCatalogSummary": {"publishedSourceIds": 1},
        "selectedSourceIds": [169],
        "items": report["catalogs"]["equipment"]["items"],
    }
    selected = select_source_variants(report, "skills", [40])
    assert selected["fullCatalogSummary"] == {"publishedSourceIds": 2}
    assert selected["selectedSourceIds"] == [40]
    assert selected["items"] == report["catalogs"]["skills"]["items"][1:]
    assert select_source_variants(report, "skills")["selectedSourceIds"] == [28, 40]
    with pytest.raises(ValueError, match="source IDs absent from equipment: \\[28\\]"):
        select_source_variants(report, "equipment", [28, 169])
    with pytest.raises(ValueError, match="unsupported source catalog"):
        select_source_variants(report, "weapons", [169])


@pytest.mark.parametrize("brief", (False, True))
def test_audit_cli_unresolved_filter_preserves_full_summary(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], brief: bool,
) -> None:
    from tools import audit_source_variant_inputs as audit

    report = {"catalogs": {"skills": {
        "summary": {"publishedSourceIds": 2, "statuses": {
            "unresolved-occurrence-parameter": 1, "family-only": 1,
        }},
        "items": [
            {"id": 26, "name": "Chain of Command",
             "status": "unresolved-occurrence-parameter",
             "occurrences": 3,
             "extraSignatures": [{"extras": [[375, "TEXT", "Non Specialist"]],
                                  "reviewed": False, "count": 1}],
             "rawValueDistinctCount": 0},
            {"id": 28, "name": "Mimetism", "status": "family-only",
             "occurrences": 10, "extraSignatures": [], "rawValueDistinctCount": 0},
        ],
    }}}
    monkeypatch.setattr(audit, "inventory_source_variants", lambda *_args: report)
    argv = ["audit_source_variant_inputs", "--catalog", "skills", "--unresolved-only"]
    if brief:
        argv.append("--brief")
    monkeypatch.setattr("sys.argv", argv)
    audit.main()
    result = json.loads(capsys.readouterr().out)
    assert result["fullCatalogSummary"] == report["catalogs"]["skills"]["summary"]
    assert result["selectedSourceIds"] == [26]
    assert [item["id"] for item in result["items"]] == [26]
    if brief:
        assert result["items"][0] == {
            "id": 26, "name": "Chain of Command",
            "status": "unresolved-occurrence-parameter",
            "occurrences": 3, "extraSignatures": 1,
            "rawValueDistinctCount": 0,
        }
    else:
        assert result["items"][0]["extraSignatures"] == (
            report["catalogs"]["skills"]["items"][0]["extraSignatures"]
        )


def _inventory() -> dict:
    return inventory_source_variants(
        ROOT / "data/generated/infinity.db",
        ROOT / "data/generated/infinity.raw.db",
        ROOT / "data/generated/rules.db",
    )


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_infiltration_source_47_exact_ph_and_reroll_owners() -> None:
    """Preserve exact Army qualifiers before introducing typed Infiltration variants."""
    from collections import Counter

    # N5.3 p. 97 scopes bracketed PH replacements to the PH-3
    # Infiltration Roll; bare ReRoll is a distinct source signature.
    expected = {
        250: ("PH=12", {51187, 51194, 58587, 58594}, {"profile": 4}),
        277: ("ReRoll", {44546, 74177, 61511, 65105, 67248}, {"profile": 5}),
        317: ("PH=18", {86311, 90562}, {"profile": 2}),
        318: ("PH=19", {86574, 90140, 22696, 25017, 31744},
              {"profile": 5}),
        340: ("PH=16", {46149, 58240}, {"profile": 2}),
        353: ("PH=15", {82925, 63815, 65316, 82466},
              {"option": 1, "profile": 3}),
    }
    [item] = select_source_variants(_inventory(), "skills", [47])["items"]
    assert (item["name"], item["applicationId"], item["occurrences"]) == (
        "Infiltration", 47, 216,
    )
    assert item["status"] == "unresolved-occurrence-parameter"
    assert item["reviewedExtra"] is None
    assert item["rawValues"] == []
    assert item["extraSignatures"] == [
        {"extras": [[extra_id, "TEXT", raw]], "reviewed": False, "count": len(ids)}
        for extra_id, (raw, ids, _owners) in expected.items()
    ]
    assert sum(len(ids) for _raw, ids, _owners in expected.values()) == 22

    for extra_id, (raw, ids, owners) in expected.items():
        rows = source_extra_owner_context(
            ROOT / "data/generated/infinity.raw.db",
            catalog="skills", source_id=47, extra_id=extra_id,
        )
        assert {row["occurrence_id"] for row in rows} == ids
        assert Counter(row["owner"] for row in rows) == owners
        assert all(
            row["extra_position"] == 1
            and row["extra_id"] == extra_id
            and row["extra_type"] == "TEXT"
            and row["extra_raw"] == raw
            and row["source_raw"] is None
            and row["army_source_file"] is not None
            for row in rows
        )

    infiltration = next(
        record
        for _, document in load_curated_directory(ROOT / "data/curated/rules")
        for record in document["records"]
        if record["id"] == "skill:infiltration"
    )
    effects = " ".join(infiltration["facts"]["effects"])
    assert "normally PH-3" in effects
    assert "profile-specific PH replacement" in effects
    assert infiltration["variantSemantics"] == {"inheritance": "family"}


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_camouflage_one_use_source_29_signature_and_faq_scope() -> None:
    """Pin exact Army one-use qualifiers without treating them as a reviewed effect."""
    [item] = select_source_variants(_inventory(), "skills", [29])["items"]
    assert (item["name"], item["applicationId"], item["occurrences"]) == (
        "Camouflage", 29, 597,
    )
    assert item["status"] == "unresolved-occurrence-parameter"
    assert item["rawValues"] == []
    assert item["reviewedExtra"] is None
    assert item["extraSignatures"] == [{
        "extras": [[43, "TEXT", "1 Use"]], "reviewed": False, "count": 223,
    }]
    owners = source_extra_owner_context(
        ROOT / "data/generated/infinity.raw.db",
        catalog="skills", source_id=29, extra_id=43,
    )
    assert len(owners) == 223
    assert all(
        row["extra_id"] == 43
        and row["extra_type"] == "TEXT"
        and row["extra_raw"] == "1 Use"
        and row["extra_position"] == 1
        and row["source_raw"] is None
        for row in owners
    )

    faq = next(
        record
        for _, document in load_curated_directory(ROOT / "data/curated/rules")
        for record in document["records"]
        if record["id"] == "faq-ruling:camouflage-one-use-infiltration-failure"
    )
    answer = faq["facts"]["answer"]
    assert "Deploying as a Model preserves" in answer
    assert "failing an Infiltration Roll uses up the one use" in answer


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_religious_troop_total_source_83_is_unresolved_and_owner_pinned() -> None:
    """Pin the likely Army Terrain/Religious modifier swap without correcting input."""
    [item] = select_source_variants(_inventory(), "skills", [83])["items"]
    assert (item["name"], item["applicationId"], item["occurrences"]) == (
        "Religious Troop", 83, 498,
    )
    assert item["status"] == "unresolved-occurrence-parameter"
    assert item["rawValues"] == []
    assert item["reviewedExtra"] is None
    assert item["extraSignatures"] == [{
        "extras": [[33, "TEXT", "Total"]], "reviewed": False, "count": 1,
    }]
    owners = source_extra_owner_context(
        ROOT / "data/generated/infinity.raw.db",
        catalog="skills", source_id=83, extra_id=33,
    )
    assert len(owners) == 1
    owner = owners[0]
    assert {
        key: owner[key]
        for key in (
            "owner", "occurrence_id", "unit_id", "unit_slug",
            "army_id", "army_name", "army_source_file", "parent_id",
            "parent_name", "extra_position", "extra_id", "extra_type",
            "extra_raw", "source_raw",
        )
    } == {
        "owner": "profile",
        "occurrence_id": 5240,
        "unit_id": 1927,
        "unit_slug": "confessor-team-ops",
        "army_id": 103,
        "army_name": "Military Orders",
        "army_source_file": "103-military-orders.json",
        "parent_id": 1,
        "parent_name": "CONFESSOR HEAVY SPEC-OPS",
        "extra_position": 1,
        "extra_id": 33,
        "extra_type": "TEXT",
        "extra_raw": "Total",
        "source_raw": None,
    }

    # The same Team-Ops unit qualifies Terrain on its light/bot profiles,
    # but not on the Heavy profile where its sole Religious Troop extra occurs.
    terrain_owners = source_extra_owner_context(
        ROOT / "data/generated/infinity.raw.db",
        catalog="skills", source_id=58, extra_id=33,
    )
    assert {
        row["parent_name"] for row in terrain_owners
        if row["unit_id"] == 1927
    } == {"CONFESSOR-1 SPEC-OPS", "BLUEBERRY SPECBOTS"}
    # Both ordinary Confessor Spec-Ops profiles (and their SpecBot) also
    # qualify Terrain as Total; neither has a Religious Troop variant.
    assert {
        row["parent_name"] for row in terrain_owners
        if row["unit_id"] == 1913
    } == {"INITIAL PROFILE", "ENHANCED PROFILE", "BLUEBERRY SPECBOTS"}


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_parachutist_deployment_zone_source_33_exact_owners() -> None:
    """Pin source-only deployment-zone occurrences without implying a usage index."""
    from collections import Counter

    [item] = select_source_variants(_inventory(), "skills", [33])["items"]
    assert (item["name"], item["applicationId"], item["occurrences"]) == (
        "Parachutist", 33, 305,
    )
    assert item["rawValues"] == []
    assert item["status"] == "reviewed-extra-parameter"
    assert item["extraSignatures"] == [{
        "extras": [[48, "TEXT", "Dep. Zone"]], "reviewed": True, "count": 17,
    }]
    assert item["reviewedExtra"] == {
        "source": "army-extra", "kind": "reviewed-extra",
        "extra_values": [{
            "extra_id": 48, "extra_type": "TEXT", "raw_value": "Dep. Zone",
            "effect": {
                "kind": "parachutist-entry-zone-permission",
                "applies_to": "parachutist-table-edge-entry",
                "zone": "enemy-deployment-zone",
                "permitted": True,
            },
        }],
    }

    owners = source_extra_owner_context(
        ROOT / "data/generated/infinity.raw.db",
        catalog="skills", source_id=33, extra_id=48,
    )
    assert len(owners) == 17
    assert Counter(row["owner"] for row in owners) == {"option": 5, "profile": 12}
    assert {row["occurrence_id"] for row in owners} == {
        54851, 34224, 38292, 1450, 12013,
        22725, 27821, 22524, 22541, 26352, 26369,
        31334, 31351, 45157, 45177, 50392, 52988,
    }
    assert all(
        row["extra_position"] == 1
        and row["extra_id"] == 48
        and row["extra_type"] == "TEXT"
        and row["extra_raw"] == "Dep. Zone"
        and row["source_raw"] is None
        and row["army_id"] is not None
        for row in owners
    )


def test_parachutist_deployment_zone_export_is_source_scoped(tmp_path: Path) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    expected = {
        "source": "army-extra", "kind": "reviewed-extra",
        "extra_values": [{
            "extra_id": 48, "extra_type": "TEXT", "raw_value": "Dep. Zone",
            "effect": {
                "kind": "parachutist-entry-zone-permission",
                "applies_to": "parachutist-table-edge-entry",
                "zone": "enemy-deployment-zone",
                "permitted": True,
            },
        }],
    }
    for db_path in (fresh, ROOT / "data/generated/rules.db"):
        rules = RulesDatabase(db_path)
        assert rules.skill_reviewed_extra_semantics()["parachutist"] == expected
        record = rules.composed_record("skill:parachutist")
        assert record is not None
        assert record["variant_semantics"]["inheritance"] == "family"
        assert record["variant_semantics"]["occurrence_parameters"] == [expected]
        assert "Without the Deployment Zone variant" in " ".join(
            record["facts"]["restrictions"]
        )
        assert any(
            citation["source_id"] == "n5-core-v5.3-pdf"
            and citation["page"] == 105
            for citation in record["citations"]
        )


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_discover_131_exact_source_extras_and_owners() -> None:
    """All 43 Discover source occurrences have one independently reviewed extra."""
    from collections import Counter

    [item] = select_source_variants(_inventory(), "skills", [131])["items"]
    assert (item["name"], item["applicationId"], item["occurrences"]) == (
        "Discover", 131, 43,
    )
    assert item["status"] == "reviewed-extra-parameter"
    assert item["rawValues"] == []
    assert item["extraSignatures"] == [
        {"extras": [[1, "TEXT", "+3"]], "reviewed": True, "count": 24},
        {"extras": [[2, "TEXT", "+6"]], "reviewed": True, "count": 13},
        {"extras": [[277, "TEXT", "ReRoll"]], "reviewed": True, "count": 6},
    ]
    assert item["reviewedExtra"]["kind"] == "reviewed-extra"
    expected = {
        1: (
            {4278, 6423, 16516, 41502, 41515, 48170, 48183, 50841,
             50920, 53448, 54720, 56674, 56893, 58393, 58426, 58524,
             60806, 66106, 68389, 69537, 80498, 80650, 82705, 84912},
            {"option": 9, "profile": 15}, "+3",
        ),
        2: (
            {25171, 26785, 31511, 34673, 38006, 41626, 46537, 49175,
             58340, 71102, 76097, 80980, 82136},
            {"profile": 13}, "+6",
        ),
        277: (
            {1309, 6622, 16348, 16879, 54571, 78075},
            {"option": 1, "profile": 5}, "ReRoll",
        ),
    }
    for extra_id, (ids, owners, raw) in expected.items():
        rows = source_extra_owner_context(
            ROOT / "data/generated/infinity.raw.db",
            catalog="skills", source_id=131, extra_id=extra_id,
        )
        assert {row["occurrence_id"] for row in rows} == ids
        assert Counter(row["owner"] for row in rows) == owners
        assert all(
            row["extra_position"] == 1 and row["source_raw"] is None
            and row["extra_id"] == extra_id
            and row["extra_type"] == "TEXT" and row["extra_raw"] == raw
            and row["army_id"] is not None
            for row in rows
        )


def test_discover_131_exact_semantics_in_tracked_and_fresh_exports(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    expected = {
        "source": "army-extra", "kind": "reviewed-extra",
        "extra_values": [
            {
                "extra_id": extra_id, "extra_type": "TEXT",
                "raw_value": f"+{mod}",
                "effect": {
                    "kind": "discover-wip-roll-mod",
                    "applies_to": "discover-wip-roll", "modifier": mod,
                },
            }
            for extra_id, mod in ((1, 3), (2, 6))
        ] + [{
            "extra_id": 277, "extra_type": "TEXT", "raw_value": "ReRoll",
            "effect": {
                "kind": "reroll-one-die",
                "applies_to": "discover-wip-roll",
            },
        }],
    }
    for path in (fresh, ROOT / "data/generated/rules.db"):
        rules = RulesDatabase(path)
        assert rules.skill_reviewed_extra_semantics()["discover"] == expected
        record = rules.composed_record("skill:discover")
        assert record is not None
        assert record["variant_semantics"]["occurrence_parameters"] == [expected]
        assert "WIP Roll" in " ".join(record["facts"]["effects"])
        assert any(
            cite["source_id"] == "n5-core-v5.3-pdf" and cite["page"] == 77
            for cite in record["citations"]
        )


@pytest.mark.parametrize(
    ("catalog", "source_id", "extra_id"),
    [("weapons", 101, 344), ("equipment", 0, 344),
     ("equipment", 101, 0)],
)
def test_extra_owner_lookup_rejects_invalid_scope(
    tmp_path: Path, catalog: str, source_id: int, extra_id: int,
) -> None:
    with pytest.raises(ValueError, match="valid source catalog and positive IDs"):
        source_extra_owner_context(
            tmp_path / "absent.db", catalog=catalog,
            source_id=source_id, extra_id=extra_id,
        )


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_regeneration_62_exact_states_phase_ph_values_in_both_exports(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    expected = [
        {"extras": [[eid, "TEXT", f"PH={value}"]],
         "reviewed": True, "count": count}
        for eid, value, count in (
            (52, 13, 3), (244, 14, 3), (250, 12, 2), (353, 15, 8)
        )
    ]
    for path in (ROOT / "data/generated/rules.db", fresh):
        rules = RulesDatabase(path)
        params = rules.skill_reviewed_extra_semantics()["regeneration"]
        assert [(v["extra_id"], v["effect"]["value"])
                for v in params["extra_values"]] == [
            (52, 13), (244, 14), (250, 12), (353, 15),
        ]
        assert all(
            v["effect"]["kind"] == "regeneration-ph-replacement"
            and v["effect"]["applies_to"] == "regeneration-states-phase-ph-roll"
            and v["effect"]["attribute"] == "PH"
            for v in params["extra_values"]
        )
        report = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db", path,
        )
        [item] = select_source_variants(report, "skills", [62])["items"]
        assert (item["name"], item["applicationId"], item["occurrences"]) == (
            "Regeneration", 62, 82,
        )
        assert item["status"] == "reviewed-extra-parameter"
        assert item["extraSignatures"] == expected
        assert item["reviewedExtra"] == params
        assert item["reviewedCombinations"] is None
        assert item["rawValues"] == []
        assert report["catalogs"]["skills"]["summary"]["statuses"] == {
            "family-only": 44, "reviewed-distance-parameter": 3,
            "reviewed-exact-source": 10, "reviewed-numeric-parameter": 3,
            "reviewed-extra-parameter": 19, "reviewed-combination-parameter": 2,
            "unresolved-occurrence-parameter": 15,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_booty_metachemistry_exact_chart_rerolls_in_both_exports(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    for path in (ROOT / "data/generated/rules.db", fresh):
        rules = RulesDatabase(path)
        params = rules.skill_reviewed_extra_semantics()
        report = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db", path,
        )
        for source_id, skill, occurrence_count, signature_count in (
            (25, "booty", 482, 108), (55, "metachemistry", 117, 60),
        ):
            [item] = select_source_variants(report, "skills", [source_id])["items"]
            assert item["status"] == "reviewed-extra-parameter"
            assert item["occurrences"] == occurrence_count
            assert item["extraSignatures"] == [{
                "extras": [[277, "TEXT", "ReRoll"]],
                "reviewed": True, "count": signature_count,
            }]
            assert item["reviewedCombinations"] is None
            assert item["reviewedExtra"] == params[skill]
            assert params[skill] == {
                "source": "army-extra", "kind": "reviewed-extra",
                "extra_values": [{
                    "extra_id": 277, "extra_type": "TEXT", "raw_value": "ReRoll",
                    "effect": {
                        "kind": "reroll-one-die",
                        "applies_to": f"{skill}-deployment-chart-roll",
                    },
                }],
            }
        assert report["catalogs"]["skills"]["summary"]["statuses"] == {
            "family-only": 44, "reviewed-distance-parameter": 3,
            "reviewed-exact-source": 10, "reviewed-numeric-parameter": 3,
            "reviewed-extra-parameter": 19, "reviewed-combination-parameter": 2,
            "unresolved-occurrence-parameter": 15,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_hacker_skill_source_1000_exact_direct_programs_in_both_exports(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    signatures = [
        {"extras": [[265, "TEXT", "Zero Pain"]], "reviewed": True, "count": 4},
        {"extras": [[314, "TEXT", "UPGRADE: Total Control (SR-2)"]],
         "reviewed": True, "count": 3},
        {"extras": [[334, "TEXT", "UPGRADE: Firewall (-3)"]],
         "reviewed": True, "count": 2},
        {"extras": [[386, "TEXT", "Carbonite"], [387, "TEXT", "Spotlight"]],
         "reviewed": True, "count": 12},
    ]
    assert sum(row["count"] for row in signatures) == 21
    for path in (ROOT / "data/generated/rules.db", fresh):
        rules = RulesDatabase(path)
        params = rules.skill_reviewed_extra_semantics()["hacker"]
        combos = rules.skill_reviewed_combination_semantics()["hacker"]
        assert len(params["extra_values"]) == 3
        assert len(combos) == 1
        report = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db", path,
        )
        [item] = select_source_variants(report, "skills", [1000])["items"]
        assert (item["name"], item["applicationId"], item["occurrences"]) == (
            "Hacker", 1000, 1094,
        )
        assert item["status"] == "reviewed-extra-parameter"
        assert item["reviewedExtra"] == params
        assert item["reviewedCombinations"] == combos
        assert item["extraSignatures"] == signatures
        assert item["rawValues"] == []
        assert report["catalogs"]["skills"]["summary"]["statuses"] == {
            "family-only": 44, "reviewed-distance-parameter": 3,
            "reviewed-exact-source": 10, "reviewed-numeric-parameter": 3,
            "reviewed-extra-parameter": 19, "reviewed-combination-parameter": 2,
            "unresolved-occurrence-parameter": 15,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_journalist_plus_three_stays_unreviewed_pending_src_027() -> None:
    owners = source_extra_owner_context(
        ROOT / "data/generated/infinity.raw.db",
        catalog="skills", source_id=272, extra_id=1,
    )
    assert len(owners) == 1
    [owner] = owners
    assert (
        owner["owner"], owner["occurrence_id"], owner["unit_id"],
        owner["unit_slug"], owner["army_id"], owner["parent_id"],
        owner["extra_type"], owner["extra_raw"],
    ) == (
        "option", 68471, 658, "tohaa-diplomatic-delegates",
        801, 3, "TEXT", "+3",
    )
    row = select_source_variants(_inventory(), "skills", [272])["items"][0]
    assert (row["name"], row["occurrences"], row["status"]) == (
        "Journalist", 93, "unresolved-occurrence-parameter",
    )
    assert row["extraSignatures"] == [{
        "extras": [[1, "TEXT", "+3"]], "reviewed": False, "count": 1,
    }]
    assert row["reviewedExtra"] is None
    record = RulesDatabase(ROOT / "data/generated/rules.db").composed_record(
        "skill:journalist",
    )
    assert record is not None
    assert record["variant_semantics"] == {"inheritance": "family"}


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_charontid_unqualified_sr_owners_are_exact_source_loadouts() -> None:
    owners = source_extra_owner_context(
        ROOT / "data/generated/infinity.raw.db",
        catalog="equipment", source_id=101, extra_id=344,
    )
    assert len(owners) == 2
    assert source_extra_owner_context(
        ROOT / "data/generated/infinity.raw.db",
        catalog="equipment", source_id=100, extra_id=344,
    ) == []
    assert source_extra_owner_context(
        ROOT / "data/generated/infinity.raw.db",
        catalog="equipment", source_id=101, extra_id=9999,
    ) == []
    assert [(row["owner"], row["occurrence_id"], row["parent_id"])
            for row in owners] == [
        ("option", 51441, 4), ("option", 51461, 9),
    ]
    for row in owners:
        assert row["unit_id"] == 498
        assert row["unit_name"] == "THE CHARONTIDS"
        assert row["unit_slug"] == "the-charontids"
        assert row["army_id"] == 601
        assert row["army_name"] == "Combined Army"
        assert row["army_source_file"] == "601-combined-army.json"
        assert row["group_id"] == 1
        assert row["parent_name"] == "CHARONTID"
        assert row["source_raw"] is None
        assert row["extra_id"] == 344
        assert row["extra_type"] == "TEXT"
        assert row["extra_raw"] == "UPGRADE: SR-1"
    [device] = select_source_variants(
        _inventory(), "equipment", [101],
    )["items"]
    assert device["status"] == "unresolved-occurrence-parameter"
    assert [
        signature for signature in device["extraSignatures"]
        if not signature["reviewed"]
    ] == [{
        "extras": [[344, "TEXT", "UPGRADE: SR-1"]],
        "reviewed": False, "count": 2,
    }]


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_pinned_source_variant_inventory_is_complete_and_conservative() -> None:
    report = _inventory()
    skills = report["catalogs"]["skills"]
    equipment = report["catalogs"]["equipment"]
    assert skills["summary"] == {
        "publishedSourceIds": 96,
        "sourceIdsWithDirectRows": 96,
        "directSourceRows": 33153,
        "reviewedExactSourceIds": 10,
        "statuses": {
            "family-only": 44,
            "reviewed-distance-parameter": 3,
            "reviewed-exact-source": 10,
            "reviewed-numeric-parameter": 3,
            "reviewed-extra-parameter": 19,
            "reviewed-combination-parameter": 2,
            "unresolved-occurrence-parameter": 15,
        },
        "extraTypes": {"DISTANCE": 5, "TEXT": 39},
    }
    assert equipment["summary"] == {
        "publishedSourceIds": 34,
        "sourceIdsWithDirectRows": 34,
        "directSourceRows": 5427,
        "reviewedExactSourceIds": 6,
        "statuses": {
            "family-only": 19,
            "reviewed-exact-source": 1,
            "reviewed-extra-parameter": 13,
            "unresolved-occurrence-parameter": 1,
        },
        "extraTypes": {"TEXT": 14},
    }
    for catalog in (skills, equipment):
        rows = catalog["items"]
        assert rows == sorted(rows, key=lambda item: item["id"])
        assert all(item["occurrences"] > 0 for item in rows)
        assert all(item["applicationId"] is not None for item in rows)
        assert not any(item["rawValues"] for item in rows)
        assert set(item["status"] for item in rows) <= {
            "family-only",
            "reviewed-distance-parameter",
            "reviewed-exact-source",
            "reviewed-numeric-parameter",
            "reviewed-extra-parameter",
            "reviewed-combination-parameter",
            "unresolved-occurrence-parameter",
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_known_ambiguous_extras_do_not_become_reviewed_variants() -> None:
    report = _inventory()["catalogs"]
    skills = {item["id"]: item for item in report["skills"]["items"]}
    equipment = {item["id"]: item for item in report["equipment"]["items"]}

    # A TEXT extra is not automatically a reviewed modifier.
    # Booty/MetaChemistry and Hacker have exact source-specific review.
    # Commlink and Journalist still have unresolved source annotations.
    for source_id in (260, 272):
        item = skills[source_id]
        assert item["status"] == "unresolved-occurrence-parameter"
        assert "TEXT" in item["extraTypes"]
        assert item["extraSignatures"]
    assert skills[24]["status"] == "reviewed-numeric-parameter"
    assert skills[28]["status"] == "reviewed-numeric-parameter"
    assert skills[40]["status"] == "reviewed-extra-parameter"
    assert skills[74]["status"] == "reviewed-extra-parameter"
    for source_id in (24, 28, 40, 74):
        assert all(part["reviewed"] for part in skills[source_id]["extraSignatures"])
    assert equipment[100]["status"] == "reviewed-extra-parameter"
    assert all(part["reviewed"] for part in equipment[100]["extraSignatures"])
    assert equipment[101]["status"] == "unresolved-occurrence-parameter"
    assert equipment[101]["extraTypes"] == ["TEXT"]
    assert equipment[101]["extraSignatures"]
    for source_id in (106, 169, 182, 239, 241, 244, 246, 247):
        assert equipment[source_id]["status"] == "reviewed-extra-parameter"
        assert all(part["reviewed"] for part in equipment[source_id]["extraSignatures"])
    assert equipment[169]["reviewedVariant"] == {"kind": "named", "label": "Firewall"}
    assert equipment[169]["status"] == "reviewed-extra-parameter"
    assert all(part["reviewed"] for part in equipment[169]["extraSignatures"])
    assert skills[28]["reviewedVariant"] is None
    assert any(
        part[2] == "-3"
        for signature in skills[28]["extraSignatures"]
        for part in signature["extras"]
    )

    # Only family-linked, source-verified distance variants are certified.
    assert skills[161]["status"] == "reviewed-distance-parameter"
    assert skills[161]["extraTypes"] == ["DISTANCE"]
    for source_id in (263, 271):
        assert skills[source_id]["status"] == "reviewed-distance-parameter"
        assert skills[source_id]["extraTypes"] == ["DISTANCE"]
    assert skills[74]["extraTypes"] == ["DISTANCE", "TEXT"]

    # No direct source occurrence is manufactured from curated-only TinBot variants.
    assert 188 not in equipment and 193 not in equipment
    assert equipment[248]["status"] == "reviewed-exact-source"


@pytest.mark.parametrize(
    ("extras", "distance_allowed", "expected"),
    [
        ([], False, False),
        ([(0, 6, "TEXT", "-3")], False, True),
        ([(0, 11, "DISTANCE", "+2.5")], True, True),
        ([(0, 11, "DISTANCE", "+2.5")], False, False),
        ([(0, 99, "TEXT", "unreviewed")], False, False),
        ([(0, 6, "TEXT", "-3"), (1, 7, "TEXT", "-6")], False, False),
        ([(0, 6, "TEXT", "-3"), (1, 11, "DISTANCE", "+2.5")], True, False),
    ],
)
def test_reviewed_extra_signatures_require_explicit_combination_review(
    extras: list[tuple[int, int, str, str]],
    distance_allowed: bool,
    expected: bool,
) -> None:
    """Recognized individual extras cannot silently approve a new combination."""
    assert reviewed_extra_signature(
        extras,
        reviewed_values={(6, "TEXT", "-3"), (7, "TEXT", "-6")},
        distance_allowed=distance_allowed,
    ) is expected


def test_exact_compound_review_never_approves_components_or_permutations() -> None:
    allowed = {((25, "TEXT", "UPGRADE: Cybermask"),
                (12, "TEXT", "UPGRADE:\u00a0Trinity"))}
    exact = [(0, 25, "TEXT", "UPGRADE: Cybermask"),
             (1, 12, "TEXT", "UPGRADE:\u00a0Trinity")]
    for items, accepted in (
        (exact, True),
        (list(reversed(exact)), False),
        (exact[:1], False),
        (exact[1:], False),
        (exact + [(2, 287, "TEXT", "UPGRADE: Zero Pain")], False),
        ([(0, 25, "TEXT", "UPGRADE: Cybermask"),
          (1, 12, "TEXT", "UPGRADE: Trinity")], False),
    ):
        assert reviewed_extra_signature(
            items, reviewed_values=set(), distance_allowed=False,
            reviewed_combinations=allowed,
        ) is accepted


def test_single_compound_text_extra_is_exact_complete_signature_not_components() -> None:
    allowed = {
        ((369, "TEXT", "Dodge (PH+3), GizmoKit (PH+1)"),),
        ((312, "TEXT", "Dodge (PH+3)"),
         (313, "TEXT", "GizmoKit (PH+1)")),
    }
    for items, accepted in (
        ([(0, 369, "TEXT", "Dodge (PH+3), GizmoKit (PH+1)")], True),
        ([(0, 369, "TEXT", "Dodge (PH+3)")], False),
        ([(0, 312, "TEXT", "Dodge (PH+3)")], False),
        ([(0, 313, "TEXT", "GizmoKit (PH+1)")], False),
        ([(0, 313, "TEXT", "GizmoKit (PH+1)"),
          (1, 312, "TEXT", "Dodge (PH+3)")], False),
        ([(0, 312, "TEXT", "Dodge (PH+3)"),
          (1, 313, "TEXT", "GizmoKit (PH+1)")], True),
    ):
        assert reviewed_extra_signature(
            items, reviewed_values=set(), distance_allowed=False,
            reviewed_combinations=allowed,
        ) is accepted


def _single_extra_counts(item: dict) -> dict[tuple[int, str, str], int]:
    return {
        tuple(signature["extras"][0]): signature["count"]
        for signature in item["extraSignatures"]
        if len(signature["extras"]) == 1
    }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_n53_numeric_skill_modifiers_preserve_exact_source_meaning() -> None:
    """Pinned Army extras against N5.3 pp. 23, 79, 86, and 102."""
    skills = {
        item["id"]: item for item in _inventory()["catalogs"]["skills"]["items"]
    }
    mimetism = skills[28]
    # N5.3 p. 102: these target enemy LoF-dependent BS Attacks/Discover,
    # never the owner's roll or CC Attacks. TEXT is the upstream type.
    assert _single_extra_counts(mimetism) == {
        (6, "TEXT", "-3"): 1612,
        (7, "TEXT", "-6"): 392,
    }
    assert mimetism["occurrences"] == 2004
    assert mimetism["status"] == "reviewed-numeric-parameter"

    berserk = skills[24]
    # N5.3 p. 86: bracketed positive MODs affect the owner's Berserk
    # CC Attack. They do not become a generic modifier on every CC roll.
    berserk_extras = _single_extra_counts(berserk)
    assert berserk_extras[(1, "TEXT", "+3")] == 243
    assert berserk_extras[(2, "TEXT", "+6")] == 3
    assert berserk["status"] == "reviewed-numeric-parameter"

    dodge = skills[40]
    # N5.3 pp. 23, 79: a Dodge Skill's bracketed MOD is distinct from
    # situational -3 PH penalties; movement distances are another axis.
    dodge_extras = _single_extra_counts(dodge)
    assert dodge_extras[(1, "TEXT", "+3")] == 613
    assert dodge_extras[(2, "TEXT", "+6")] == 7
    assert dodge["extraTypes"] == ["DISTANCE", "TEXT"]
    assert dodge["status"] == "reviewed-extra-parameter"
    # Dodge has explicitly reviewed PH/MOV/extra signatures. Do not infer
    # generic MOD meaning from other source TEXT labels.


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_numeric_mod_signatures_require_exact_reviewed_ids_and_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only explicitly mapped source extras become countable variants."""
    monkeypatch.setattr(
        RulesDatabase, "skill_numeric_mod_semantics",
        lambda self: {
            "mimetism": {
                "kind": "numeric-mod", "owner": "skill-holder", "target": "opponent",
                "applies_to": ["bs-attack-requiring-lof", "discover"],
                "extra_values": [
                    {"extra_id": 6, "extra_type": "TEXT", "raw_value": "-3", "modifier": -3},
                    {"extra_id": 7, "extra_type": "TEXT", "raw_value": "-6", "modifier": -6},
                ],
            },
            "dodge": {
                "kind": "numeric-mod", "owner": "skill-holder", "target": "skill-holder",
                "applies_to": ["dodge-ph-roll"],
                "extra_values": [
                    {"extra_id": 1, "extra_type": "TEXT", "raw_value": "+3", "modifier": 3},
                    {"extra_id": 2, "extra_type": "TEXT", "raw_value": "+6", "modifier": 6},
                ],
            },
        },
    )
    # Deliberately withhold the reviewed typed-extra map: partial numeric
    # coverage must not certify Dodge's unrelated PH/MOV/SD/ARM signatures.
    monkeypatch.setattr(RulesDatabase, "skill_reviewed_extra_semantics", lambda self: {})
    skills = {item["id"]: item for item in _inventory()["catalogs"]["skills"]["items"]}
    mimetism = skills[28]
    assert mimetism["status"] == "reviewed-numeric-parameter"
    assert all(entry["reviewed"] for entry in mimetism["extraSignatures"])
    assert skills[24]["status"] == "unresolved-occurrence-parameter"
    assert skills[40]["status"] == "unresolved-occurrence-parameter"
    assert skills[40]["reviewedNumericMod"] is not None
    assert any(not entry["reviewed"] for entry in skills[40]["extraSignatures"])
    # The tested mapping cannot accidentally certify unrelated source extras.
    assert skills[25]["status"] == "unresolved-occurrence-parameter"


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_current_reviewed_numeric_mods_certify_only_exact_army_extras(
    tmp_path: Path,
) -> None:
    """The edited curated source, not stale generated rules.db, governs eligibility."""
    output = tmp_path / "rules.db"
    export_rules_database(
        load_curated_directory(ROOT / "data/curated"), output, finalize=False,
    )
    rules = RulesDatabase(output)
    parameters = rules.skill_numeric_mod_semantics()
    assert set(parameters) == {"mimetism", "berserk", "dodge", "surprise-attack"}
    assert {
        ref: {
            (value["extra_id"], value["extra_type"], value["raw_value"], value["modifier"])
            for value in parameters[ref]["extra_values"]
        }
        for ref in parameters
    } == {
        "mimetism": {(6, "TEXT", "-3", -3), (7, "TEXT", "-6", -6)},
        "berserk": {(1, "TEXT", "+3", 3), (2, "TEXT", "+6", 6)},
        "dodge": {(1, "TEXT", "+3", 3), (2, "TEXT", "+6", 6)},
        "surprise-attack": {(6, "TEXT", "-3", -3), (7, "TEXT", "-6", -6)},
    }
    assert parameters["mimetism"]["target"] == "opponent"
    assert parameters["mimetism"]["applies_to"] == [
        "bs-attack-requiring-lof", "discover",
    ]
    assert parameters["berserk"]["applies_to"] == ["berserk-cc-attack"]
    assert parameters["dodge"]["applies_to"] == ["dodge-ph-roll"]
    # Mimetism is fully resolved. Dodge has DISTANCE and other potential
    # extra signatures: reviewed PH MODs do not certify those combinations.
    report = inventory_source_variants(
        ROOT / "data/generated/infinity.db",
        ROOT / "data/generated/infinity.raw.db", output,
    )["catalogs"]["skills"]
    sources = {item["id"]: item for item in report["items"]}
    assert report["summary"]["statuses"] == {
        "family-only": 44,
        "reviewed-distance-parameter": 3,
        "reviewed-exact-source": 10,
        "reviewed-numeric-parameter": 3,
        "reviewed-extra-parameter": 19,
        "reviewed-combination-parameter": 2,
        "unresolved-occurrence-parameter": 15,
    }
    assert sources[28]["status"] == "reviewed-numeric-parameter"
    assert all(s["reviewed"] for s in sources[28]["extraSignatures"])
    assert sources[24]["reviewedNumericMod"] is not None
    assert sources[24]["status"] == "reviewed-numeric-parameter"
    assert sources[40]["status"] == "reviewed-extra-parameter"
    assert all(s["reviewed"] for s in sources[40]["extraSignatures"])
    assert sources[25]["status"] == "reviewed-extra-parameter"
    assert sources[55]["status"] == "reviewed-extra-parameter"
    # Existing distance-only projection remains independent of numeric MODs.
    assert rules.skill_parameter_semantics() == {
        "super-jump": {"kind": "distance", "positive_sign": "omit"},
        "forward-deployment": {"kind": "distance", "positive_sign": "force"},
        263: {"kind": "distance", "positive_sign": "omit"},
        271: {"kind": "distance", "positive_sign": "omit"},
    }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_vulnerability_viral_source_220_matches_both_rules_exports(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    for path in (ROOT / "data/generated/rules.db", fresh):
        rules = RulesDatabase(path)
        params = rules.skill_reviewed_extra_semantics()["vulnerability"]
        result = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db", path,
        )
        [row] = select_source_variants(result, "skills", [220])["items"]
        assert row["occurrences"] == 2
        assert row["status"] == "reviewed-extra-parameter"
        assert row["reviewedExtra"] == params
        assert row["extraSignatures"] == [
            {"extras": [[39, "TEXT", "Viral"]], "reviewed": True, "count": 2}
        ]
        assert row["rawValues"] == []


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_decoy_215_exact_deployment_replica_counts_in_both_exports(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    expected = [
        {"extras": [[44, "TEXT", "1"]], "reviewed": True, "count": 132},
        {"extras": [[267, "TEXT", "2"]], "reviewed": True, "count": 24},
    ]
    for path in (ROOT / "data/generated/rules.db", fresh):
        rules = RulesDatabase(path)
        params = rules.skill_reviewed_extra_semantics()["decoy"]
        assert params["source"] == "army-extra"
        assert params["kind"] == "reviewed-extra"
        assert params["extra_values"] == [
            {
                "extra_id": extra_id, "extra_type": "TEXT",
                "raw_value": str(count),
                "effect": {
                    "kind": "decoy-replica-marker-count",
                    "applies_to": "decoy-state-deployment",
                    "count": count,
                },
            }
            for extra_id, count in ((44, 1), (267, 2))
        ]
        result = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db", path,
        )
        [row] = select_source_variants(result, "skills", [215])["items"]
        assert (row["name"], row["applicationId"], row["occurrences"]) == (
            "Decoy", 215, 162,
        )
        assert row["status"] == "reviewed-extra-parameter"
        assert row["extraSignatures"] == expected
        assert row["reviewedExtra"] == params
        assert row["rawValues"] == []
        assert result["catalogs"]["skills"]["summary"]["statuses"] == {
            "family-only": 44, "reviewed-distance-parameter": 3,
            "reviewed-exact-source": 10, "reviewed-numeric-parameter": 3,
            "reviewed-extra-parameter": 19, "reviewed-combination-parameter": 2,
            "unresolved-occurrence-parameter": 15,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_ft_master_261_lists_exact_cancellation_trigger_units_in_both_exports(
    tmp_path: Path,
) -> None:
    from infinity_db.curated import FT_MASTER_UNIT_SIGNATURES

    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    expected = [
        {"extras": [[extra_id, "TEXT", raw]], "reviewed": True, "count": count}
        for (extra_id, raw, _names), count in zip(
            FT_MASTER_UNIT_SIGNATURES, (2, 47, 1, 2, 2, 2, 2, 1),
            strict=True,
        )
    ]
    assert sum(item["count"] for item in expected) == 59
    for path in (ROOT / "data/generated/rules.db", fresh):
        db = RulesDatabase(path)
        parameters = db.skill_reviewed_extra_semantics()["ft-master"]
        assert len(parameters["extra_values"]) == 8
        assert parameters["extra_values"][3]["effect"]["unitNames"] == [
            "Morlocks", "Zellenkriegers", "Connolly",
        ]
        report = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db", path,
        )
        [row] = select_source_variants(report, "skills", [261])["items"]
        assert (row["name"], row["applicationId"], row["occurrences"]) == (
            "FT Master", 261, 61,
        )
        assert row["status"] == "reviewed-extra-parameter"
        assert row["reviewedExtra"] == parameters
        assert row["extraSignatures"] == expected
        assert row["rawValues"] == []
        assert report["catalogs"]["skills"]["summary"]["statuses"] == {
            "family-only": 44, "reviewed-distance-parameter": 3,
            "reviewed-exact-source": 10, "reviewed-numeric-parameter": 3,
            "reviewed-extra-parameter": 19, "reviewed-combination-parameter": 2,
            "unresolved-occurrence-parameter": 15,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_tagcom_270_complete_recipient_mod_signatures_in_both_exports(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    expected = [
        {"extras": [[312, "TEXT", "Dodge (PH+3)"],
                    [313, "TEXT", "GizmoKit (PH+1)"]],
         "reviewed": True, "count": 2},
        {"extras": [[369, "TEXT", "Dodge (PH+3), GizmoKit (PH+1)"]],
         "reviewed": True, "count": 24},
        {"extras": [[370, "TEXT", "Dodge (PH+1), GizmoKit (PH+1)"]],
         "reviewed": True, "count": 2},
    ]
    from tools.audit_source_variant_inputs import reviewed_extra_signature
    assert not reviewed_extra_signature(
        [(1, 312, "TEXT", "Dodge (PH+3)")],
        reviewed_values=set(), distance_allowed=False,
        reviewed_combinations={
            tuple(tuple(e) for e in signature["extras"]) for signature in expected
        },
    )
    assert not reviewed_extra_signature(
        [(1, 313, "TEXT", "GizmoKit (PH+1)"),
         (2, 312, "TEXT", "Dodge (PH+3)")],
        reviewed_values=set(), distance_allowed=False,
        reviewed_combinations={
            tuple(tuple(e) for e in signature["extras"]) for signature in expected
        },
    )
    for path in (ROOT / "data/generated/rules.db", fresh):
        rules = RulesDatabase(path)
        combos = rules.skill_reviewed_combination_semantics()
        assert set(combos) == {"remdriver", "tagcom", "hacker"}
        assert "tagcom" not in rules.skill_reviewed_extra_semantics()
        report = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db", path,
        )
        [row] = select_source_variants(report, "skills", [270])["items"]
        assert (row["name"], row["applicationId"], row["occurrences"]) == (
            "TAGCom", 270, 28,
        )
        assert row["status"] == "reviewed-combination-parameter"
        assert row["extraSignatures"] == expected
        assert row["reviewedExtra"] is None
        assert row["reviewedCombinations"] == combos["tagcom"]
        assert row["rawValues"] == []
        assert report["catalogs"]["skills"]["summary"]["statuses"] == {
            "family-only": 44, "reviewed-distance-parameter": 3,
            "reviewed-exact-source": 10, "reviewed-numeric-parameter": 3,
            "reviewed-extra-parameter": 19, "reviewed-combination-parameter": 2,
            "unresolved-occurrence-parameter": 15,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_remdriver_255_only_exact_full_compounds_are_reviewed(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    expected = [
        {"extras": [[271, "TEXT", "+1 BS"], [300, "TEXT", "+5 CC"]],
         "reviewed": True, "count": 3},
        {"extras": [[280, "TEXT", "CC=15"], [281, "TEXT", "BS=13"],
                    [282, "TEXT", "WIP=14"]],
         "reviewed": True, "count": 5},
        {"extras": [[281, "TEXT", "BS=13"], [52, "TEXT", "PH=13"],
                    [384, "TEXT", "BTS=6"]],
         "reviewed": True, "count": 4},
    ]
    from tools.audit_source_variant_inputs import reviewed_extra_signature
    assert not reviewed_extra_signature(
        [(1, 281, "TEXT", "BS=13")],
        reviewed_values=set(), distance_allowed=False,
    )
    assert not reviewed_extra_signature(
        [(1, 281, "TEXT", "BS=13"), (2, 280, "TEXT", "CC=15"),
         (3, 282, "TEXT", "WIP=14")],
        reviewed_values=set(), distance_allowed=False,
        reviewed_combinations={
            tuple(tuple(x) for x in signature["extras"]) for signature in expected
        },
    )
    for path in (ROOT / "data/generated/rules.db", fresh):
        rules = RulesDatabase(path)
        combos = rules.skill_reviewed_combination_semantics()
        assert set(combos) == {"remdriver", "tagcom", "hacker"}
        result = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db", path,
        )
        [row] = select_source_variants(result, "skills", [255])["items"]
        assert (row["name"], row["applicationId"], row["occurrences"]) == (
            "RemDriver", 255, 12,
        )
        assert row["status"] == "reviewed-combination-parameter"
        assert row["extraSignatures"] == expected
        assert row["reviewedExtra"] is None
        assert row["reviewedCombinations"] == combos["remdriver"]
        assert row["rawValues"] == []
        assert result["catalogs"]["skills"]["summary"]["statuses"] == {
            "family-only": 44, "reviewed-distance-parameter": 3,
            "reviewed-exact-source": 10, "reviewed-numeric-parameter": 3,
            "reviewed-extra-parameter": 19, "reviewed-combination-parameter": 2,
            "unresolved-occurrence-parameter": 15,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_bangbomb_skill_266_reuses_equipment_scope_in_both_exports(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    expected = [{"extras": [[310, "TEXT", "+4"]], "reviewed": True, "count": 4}]
    for rules_path in (ROOT / "data/generated/rules.db", fresh):
        rules = RulesDatabase(rules_path)
        assert set(rules.skill_source_equipment_overrides()) == {254, 266, 273}
        assert "bangbomb" not in rules.skill_reviewed_extra_semantics()
        effect = rules.equipment_reviewed_extra_semantics()["bangbomb"]
        assert rules.skill_source_equipment_overrides()[266]["extra_values"] == (
            effect["extra_values"]
        )
        assert effect["extra_values"] == [{
            "extra_id": 310, "extra_type": "TEXT", "raw_value": "+4",
            "effect": {
                "kind": "dodge-roll-mod",
                "applies_to": "dodge-vs-enemy-in-lof-or-zoc-excluding-template-weapons",
                "modifier": 4,
            },
        }]
        report = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db", rules_path,
        )
        [row] = select_source_variants(report, "skills", [266])["items"]
        assert (row["name"], row["applicationId"], row["occurrences"]) == (
            "Bangbomb", 266, 4,
        )
        assert row["status"] == "reviewed-extra-parameter"
        assert row["extraSignatures"] == expected
        assert row["reviewedCombinations"] is None
        assert row["rawValues"] == []
        assert row["reviewedExtra"] == rules.skill_source_equipment_overrides()[266]
        assert report["catalogs"]["skills"]["summary"]["statuses"] == {
            "family-only": 44, "reviewed-distance-parameter": 3,
            "reviewed-exact-source": 10, "reviewed-numeric-parameter": 3,
            "reviewed-extra-parameter": 19, "reviewed-combination-parameter": 2,
            "unresolved-occurrence-parameter": 15,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_medikit_target_ph_skill_273_is_equipment_owned_in_both_exports(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    expected = [
        {"extras": [[extra_id, "TEXT", f"PH={value}"]],
         "reviewed": True, "count": count}
        for extra_id, value, count in (
            (52, 13, 2), (244, 14, 12), (250, 12, 1),
            (340, 16, 4), (353, 15, 6), (382, 17, 6),
        )
    ]
    assert sum(row["count"] for row in expected) == 31
    for rules_path in (ROOT / "data/generated/rules.db", fresh):
        db = RulesDatabase(rules_path)
        assert set(db.skill_source_equipment_overrides()) == {254, 266, 273}
        assert "medikit" not in db.skill_reviewed_extra_semantics()
        assert db.equipment_reviewed_extra_semantics()["medikit"]["extra_values"][0][
            "effect"
        ] == {
            "kind": "equipment-burst-mod",
            "applies_to": "ranged-medikit-bs-attack", "modifier": 1,
        }
        result = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db", rules_path,
        )
        [row] = select_source_variants(result, "skills", [273])["items"]
        assert (row["name"], row["applicationId"], row["occurrences"]) == (
            "MediKit", 273, 31,
        )
        assert row["status"] == "reviewed-extra-parameter"
        assert row["extraSignatures"] == expected
        assert row["reviewedCombinations"] is None
        assert row["rawValues"] == []
        assert row["reviewedExtra"] == db.skill_source_equipment_overrides()[273]
        assert result["catalogs"]["skills"]["summary"]["statuses"] == {
            "family-only": 44, "reviewed-distance-parameter": 3,
            "reviewed-exact-source": 10, "reviewed-numeric-parameter": 3,
            "reviewed-extra-parameter": 19, "reviewed-combination-parameter": 2,
            "unresolved-occurrence-parameter": 15,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_gizmokit_target_ph_skill_254_is_equipment_owned_in_both_exports(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    expected = [
        {"extras": [[extra_id, "TEXT", f"PH={value}"]],
         "reviewed": True, "count": count}
        for extra_id, value, count in (
            (27, 11, 131), (32, 10, 53), (46, 9, 57),
            (52, 13, 33), (244, 14, 4), (250, 12, 10),
        )
    ]
    assert sum(row["count"] for row in expected) == 288
    for rules_path in (ROOT / "data/generated/rules.db", fresh):
        db = RulesDatabase(rules_path)
        assert set(db.skill_source_equipment_overrides()) == {254, 266, 273}
        assert "gizmokit" not in db.skill_reviewed_extra_semantics()
        equipment = db.equipment_reviewed_extra_semantics()["gizmokit"]
        assert equipment["extra_values"][0]["effect"] == {
            "kind": "equipment-burst-mod",
            "applies_to": "ranged-gizmokit-bs-attack", "modifier": 1,
        }
        result = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db", rules_path,
        )
        [row] = select_source_variants(result, "skills", [254])["items"]
        assert (row["name"], row["applicationId"], row["occurrences"]) == (
            "Gizmokit", 254, 288,
        )
        assert row["status"] == "reviewed-extra-parameter"
        assert row["extraSignatures"] == expected
        assert row["reviewedCombinations"] is None
        assert row["rawValues"] == []
        assert row["reviewedExtra"] == db.skill_source_equipment_overrides()[254]
        assert result["catalogs"]["skills"]["summary"]["statuses"] == {
            "family-only": 44, "reviewed-distance-parameter": 3,
            "reviewed-exact-source": 10, "reviewed-numeric-parameter": 3,
            "reviewed-extra-parameter": 19, "reviewed-combination-parameter": 2,
            "unresolved-occurrence-parameter": 15,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_impersonation_imp2_matches_pinned_source_and_both_exports(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    for rules_path in (ROOT / "data/generated/rules.db", fresh):
        report = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db",
            rules_path,
        )
        [item] = select_source_variants(report, "skills", [249])["items"]
        assert (item["name"], item["applicationId"], item["occurrences"]) == (
            "Impersonation", 249, 14,
        )
        assert item["status"] == "reviewed-extra-parameter"
        assert item["rawValues"] == []
        assert item["reviewedCombinations"] is None
        assert item["extraSignatures"] == [{
            "extras": [[268, "TEXT", "IMP-2"]], "reviewed": True, "count": 9,
        }]
        reviewed = RulesDatabase(rules_path).skill_reviewed_extra_semantics()
        assert item["reviewedExtra"] == reviewed["impersonation"]
        assert reviewed["impersonation"] == {
            "source": "army-extra", "kind": "reviewed-extra",
            "extra_values": [{
                "extra_id": 268, "extra_type": "TEXT", "raw_value": "IMP-2",
                "effect": {
                    "kind": "impersonation-state-restriction",
                    "state": "state:impersonation-2",
                    "applies_to": "deployment-and-activation",
                    "only": True,
                },
            }],
        }
        assert report["catalogs"]["skills"]["summary"]["statuses"] == {
            "family-only": 44,
            "reviewed-distance-parameter": 3,
            "reviewed-exact-source": 10,
            "reviewed-numeric-parameter": 3,
            "reviewed-extra-parameter": 19,
            "reviewed-combination-parameter": 2,
            "unresolved-occurrence-parameter": 15,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_dodge_source_signatures_are_exact_and_independent(tmp_path: Path) -> None:
    """Pin every distinct Army Dodge extra; none may inherit another's semantics."""
    output = tmp_path / "rules.db"
    export_rules_database(
        load_curated_directory(ROOT / "data/curated"), output, finalize=False,
    )
    inventory = inventory_source_variants(
        ROOT / "data/generated/infinity.db",
        ROOT / "data/generated/infinity.raw.db",
        output,
    )["catalogs"]["skills"]["items"]
    dodge = next(item for item in inventory if item["id"] == 40)
    signatures = dodge["extraSignatures"]
    assert all(len(signature["extras"]) == 1 for signature in signatures)
    assert {
        tuple(signature["extras"][0]): signature["count"]
        for signature in signatures
    } == {
        (1, "TEXT", "+3"): 613,
        (2, "TEXT", "+6"): 7,
        (6, "TEXT", "-3"): 30,
        (7, "TEXT", "-6"): 1,
        (11, "DISTANCE", "+2.5"): 633,
        (23, "DISTANCE", "+5"): 808,
        (27, "TEXT", "PH=11"): 151,
        (32, "TEXT", "PH=10"): 3,
        (46, "TEXT", "PH=9"): 110,
        (52, "TEXT", "PH=13"): 5,
        (250, "TEXT", "PH=12"): 6,
        (260, "DISTANCE", "+7.5"): 4,
        (308, "TEXT", "+1SD"): 9,
        (379, "TEXT", "ARM +3"): 2,
    }
    assert dodge["occurrences"] == 2382
    # A source-ID-wide status must not promote the remaining exact signatures.
    assert dodge["status"] == "reviewed-extra-parameter"
    assert all(signature["reviewed"] for signature in signatures)


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_surprise_attack_signatures_preserve_conditional_target_mods(tmp_path: Path) -> None:
    output = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), output)
    for path in (output, ROOT / "data/generated/rules.db"):
        rules = RulesDatabase(path)
        parameters = rules.skill_numeric_mod_semantics()["surprise-attack"]
        assert parameters["owner"] == "skill-holder"
        assert parameters["target"] == "opponent"
        assert parameters["applies_to"] == ["surprise-attack-target-face-to-face-aro"]
        report = inventory_source_variants(
            ROOT / "data/generated/infinity.db", ROOT / "data/generated/infinity.raw.db", path,
        )
        source = next(row for row in report["catalogs"]["skills"]["items"] if row["id"] == 191)
        assert source["status"] == "reviewed-numeric-parameter"
        assert source["occurrences"] == 767
        assert {
            tuple(signature["extras"][0]): signature["count"]
            for signature in source["extraSignatures"]
        } == {(6, "TEXT", "-3"): 762, (7, "TEXT", "-6"): 5}
        assert all(len(s["extras"]) == 1 and s["reviewed"] for s in source["extraSignatures"])
        rule = rules.composed_record("skill:surprise-attack")
        assert rule is not None
        assert any(c["source_id"] == "n5-core-v5.3-pdf" and c["page"] == 114
                   for c in rule["citations"])
        assert rule["variant_semantics"]["inheritance"] == "family"
        assert "surprise-attack" not in rules.skill_parameter_semantics()


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_pinned_movement_and_tinbot_source_extra_signatures() -> None:
    """Separate N5.3 distance clauses, Jet Propulsion, and TinBot Firewall MODs."""
    report = _inventory()
    skills = select_source_variants(report, "skills", [74, 263, 271])["items"]
    assert [item["id"] for item in skills] == [74, 263, 271]
    assert [item["occurrences"] for item in skills] == [670, 26, 6]
    assert [item["status"] for item in skills] == [
        "reviewed-extra-parameter", "reviewed-distance-parameter",
        "reviewed-distance-parameter",
    ]
    assert {
        item["id"]: [
            (tuple(tuple(extra) for extra in signature["extras"]),
             signature["count"], signature["reviewed"])
            for signature in item["extraSignatures"]
        ]
        for item in skills
    } == {
        74: [
            (((260, "DISTANCE", "+7.5"),), 4, True),
            (((304, "TEXT", "Jet Propulsion"),), 198, True),
            (((372, "DISTANCE", "7.5"),), 43, True),
        ],
        263: [(((372, "DISTANCE", "7.5"),), 26, True)],
        271: [(((372, "DISTANCE", "7.5"),), 6, True)],
    }
    assert skills[0]["reviewedDistance"] == {"kind": "distance", "positive_sign": "omit"}
    assert skills[1]["reviewedDistance"] == {"kind": "distance", "positive_sign": "omit"}
    assert skills[2]["reviewedDistance"] == {"kind": "distance", "positive_sign": "omit"}

    [tinbot] = select_source_variants(report, "equipment", [169])["items"]
    assert tinbot["name"] == "TinBot: Firewall"
    assert tinbot["status"] == "reviewed-extra-parameter"
    assert tinbot["reviewedVariant"] == {"kind": "named", "label": "Firewall"}
    assert tinbot["reviewedExtra"] == RulesDatabase(
        ROOT / "data/generated/rules.db"
    ).equipment_reviewed_extra_semantics()[169]
    assert tinbot["occurrences"] == 147
    assert [
        (tuple(signature["extras"][0]), signature["count"], signature["reviewed"])
        for signature in tinbot["extraSignatures"]
    ] == [
        ((6, "TEXT", "-3"), 92, True),
        ((7, "TEXT", "-6"), 55, True),
    ]


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_evo_trinity_grant_and_sr_modifier_match_tracked_and_fresh_rules(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    expected = [{
        "extras": [[352, "TEXT", "UPGRADE: Trinity (SR-2)"]],
        "reviewed": True, "count": 2,
    }]
    for rules_path in (ROOT / "data/generated/rules.db", fresh):
        report = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db",
            rules_path,
        )
        [row] = select_source_variants(report, "equipment", [182])["items"]
        assert row["name"] == "EVO Hacking Device"
        assert row["applicationId"] == 182
        assert row["occurrences"] == 40
        assert row["status"] == "reviewed-extra-parameter"
        assert row["extraSignatures"] == expected
        assert row["reviewedCombinations"] is None
        reviewed = RulesDatabase(rules_path).equipment_reviewed_extra_semantics()
        assert row["reviewedExtra"] == reviewed["evo-hacking-device"]
        [extra] = reviewed["evo-hacking-device"]["extra_values"]
        assert extra["effect"] == {
            "kind": "hacking-program-upgrade",
            "program": "hacking-program:trinity",
            "grantsProgram": True,
            "applies_to": "target-saving-roll-against-program",
            "modifier": -2,
        }
        assert report["catalogs"]["equipment"]["summary"]["statuses"] == {
            "family-only": 19, "reviewed-exact-source": 1,
            "reviewed-extra-parameter": 13, "unresolved-occurrence-parameter": 1,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_albedo_183_modifiers_match_pinned_source_and_both_rules_exports(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    expected = [
        {"extras": [[6, "TEXT", "-3"]], "reviewed": True, "count": 55},
        {"extras": [[7, "TEXT", "-6"]], "reviewed": True, "count": 87},
    ]
    for rules_path in (ROOT / "data/generated/rules.db", fresh):
        report = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db",
            rules_path,
        )
        [item] = select_source_variants(report, "equipment", [183])["items"]
        assert (item["id"], item["name"], item["applicationId"]) == (
            183, "Albedo", 183,
        )
        assert item["occurrences"] == 142
        assert item["status"] == "reviewed-extra-parameter"
        assert item["rawValues"] == []
        assert item["reviewedCombinations"] is None
        assert item["extraSignatures"] == expected
        reviewed = RulesDatabase(rules_path).equipment_reviewed_extra_semantics()
        assert item["reviewedExtra"] == reviewed["albedo"]
        assert reviewed["albedo"] == {
            "source": "army-extra",
            "kind": "reviewed-extra",
            "extra_values": [
                {
                    "extra_id": extra_id,
                    "extra_type": "TEXT",
                    "raw_value": str(modifier),
                    "effect": {
                        "kind": "enemy-albedo-attribute-mod",
                        "applies_to": (
                            "msv-or-marksmanship-lof-bs-attack-or-discover-against-bearer"
                        ),
                        "modifier": modifier,
                    },
                }
                for extra_id, modifier in ((6, -3), (7, -6))
            ],
        }
        assert report["catalogs"]["equipment"]["summary"]["statuses"] == {
            "family-only": 19, "reviewed-exact-source": 1,
            "reviewed-extra-parameter": 13, "unresolved-occurrence-parameter": 1,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_medikit_source_106_burst_matches_tracked_and_fresh_rules(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    expected = [{
        "extras": [[8, "TEXT", "+1B"]], "reviewed": True, "count": 38,
    }]
    for rules_path in (ROOT / "data/generated/rules.db", fresh):
        report = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db",
            rules_path,
        )
        [row] = select_source_variants(report, "equipment", [106])["items"]
        assert row["name"] == "MediKit"
        assert row["applicationId"] == 106
        assert row["occurrences"] == 573
        assert row["status"] == "reviewed-extra-parameter"
        assert row["extraSignatures"] == expected
        assert row["reviewedCombinations"] is None
        assert row["reviewedExtra"] == (
            RulesDatabase(rules_path).equipment_reviewed_extra_semantics()["medikit"]
        )
        assert report["catalogs"]["equipment"]["summary"]["statuses"] == {
            "family-only": 19, "reviewed-exact-source": 1,
            "reviewed-extra-parameter": 13, "unresolved-occurrence-parameter": 1,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_gizmokit_source_237_burst_matches_tracked_and_fresh_rules(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    expected = [{
        "extras": [[8, "TEXT", "+1B"]], "reviewed": True, "count": 16,
    }]
    for rules_path in (ROOT / "data/generated/rules.db", fresh):
        report = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db",
            rules_path,
        )
        [row] = select_source_variants(report, "equipment", [237])["items"]
        assert row["name"] == "GizmoKit"
        assert row["applicationId"] == 237
        assert row["occurrences"] == 544
        assert row["status"] == "reviewed-extra-parameter"
        assert row["extraSignatures"] == expected
        assert row["reviewedCombinations"] is None
        assert row["reviewedExtra"] == (
            RulesDatabase(rules_path).equipment_reviewed_extra_semantics()["gizmokit"]
        )
        assert report["catalogs"]["equipment"]["summary"]["statuses"] == {
            "family-only": 19, "reviewed-exact-source": 1,
            "reviewed-extra-parameter": 13, "unresolved-occurrence-parameter": 1,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_deactivator_source_238_variants_match_tracked_and_fresh_rules(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    expected = [
        {"extras": [[8, "TEXT", "+1B"]], "reviewed": True, "count": 1},
        {"extras": [[277, "TEXT", "ReRoll"]], "reviewed": True, "count": 9},
    ]
    for rules_path in (ROOT / "data/generated/rules.db", fresh):
        report = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db",
            rules_path,
        )
        [row] = select_source_variants(report, "equipment", [238])["items"]
        assert (row["name"], row["applicationId"], row["occurrences"]) == (
            "Deactivator", 238, 416,
        )
        assert row["status"] == "reviewed-extra-parameter"
        assert row["extraSignatures"] == expected
        assert row["reviewedCombinations"] is None
        assert row["rawValues"] == []
        assert row["reviewedExtra"] == (
            RulesDatabase(rules_path).equipment_reviewed_extra_semantics()["deactivator"]
        )
        assert report["catalogs"]["equipment"]["summary"]["statuses"] == {
            "family-only": 19, "reviewed-exact-source": 1,
            "reviewed-extra-parameter": 13, "unresolved-occurrence-parameter": 1,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_bangbomb_source_246_matches_tracked_and_fresh_rules(tmp_path: Path) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    expected = [{
        "extras": [[310, "TEXT", "+4"]], "reviewed": True, "count": 125,
    }]
    for rules_path in (ROOT / "data/generated/rules.db", fresh):
        report = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db",
            rules_path,
        )
        [row] = select_source_variants(report, "equipment", [246])["items"]
        assert row["name"] == "Bangbomb"
        assert row["applicationId"] == 246
        assert row["occurrences"] == 125
        assert row["status"] == "reviewed-extra-parameter"
        assert row["extraSignatures"] == expected
        assert row["reviewedCombinations"] is None
        assert row["reviewedExtra"] == (
            RulesDatabase(rules_path).equipment_reviewed_extra_semantics()["bangbomb"]
        )
        assert report["catalogs"]["equipment"]["summary"]["statuses"] == {
            "family-only": 19, "reviewed-exact-source": 1,
            "reviewed-extra-parameter": 13, "unresolved-occurrence-parameter": 1,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_ecm_source_variants_match_tracked_and_fresh_rules(tmp_path: Path) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    expected = {
        239: ("Guided", 181, [
            (6, "-3", 2), (7, "-6", 176), (51, "-8", 1), (251, "-8", 2),
        ]),
        241: ("Hacker", 161, [(6, "-3", 158), (7, "-6", 3)]),
    }
    for rules_path in (ROOT / "data/generated/rules.db", fresh):
        report = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db",
            rules_path,
        )
        reviewed = RulesDatabase(rules_path).equipment_reviewed_extra_semantics()
        for source_id, (label, count, signatures) in expected.items():
            [item] = select_source_variants(report, "equipment", [source_id])["items"]
            assert item["applicationId"] == 239
            assert item["status"] == "reviewed-extra-parameter"
            assert item["reviewedVariant"] == {"kind": "named", "label": label}
            assert item["reviewedExtra"] == reviewed[source_id]
            assert item["occurrences"] == count
            assert item["extraSignatures"] == [
                {"extras": [[extra_id, "TEXT", raw]],
                 "reviewed": True, "count": number}
                for extra_id, raw, number in signatures
            ]
    raw = ROOT / "data/generated/infinity.raw.db"
    juggernauts = source_extra_owner_context(
        raw, catalog="equipment", source_id=239, extra_id=51,
    )
    zetas = source_extra_owner_context(
        raw, catalog="equipment", source_id=239, extra_id=251,
    )
    assert [(row["unit_id"], row["army_id"], row["extra_raw"])
            for row in juggernauts] == [(1882, 605, "-8")]
    assert {(row["unit_id"], row["army_id"], row["extra_raw"])
            for row in zetas} == {(1458, 1001, "-8"), (1458, 1002, "-8")}
    assert source_extra_owner_context(
        raw, catalog="equipment", source_id=241, extra_id=251,
    ) == []


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_tinbot_firewall_source_extras_match_fresh_export(tmp_path: Path) -> None:
    """An edited tracked rules artifact cannot alone certify Equipment MODs."""
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    for path in (ROOT / "data/generated/rules.db", fresh):
        rows = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db",
            path,
        )["catalogs"]["equipment"]["items"]
        item = next(row for row in rows if row["id"] == 169)
        assert item["status"] == "reviewed-extra-parameter"
        assert item["reviewedVariant"] == {"kind": "named", "label": "Firewall"}
        assert item["reviewedExtra"] == (
            RulesDatabase(path).equipment_reviewed_extra_semantics()[169]
        )
        assert item["occurrences"] == 147
        assert item["extraSignatures"] == [
            {"extras": [[6, "TEXT", "-3"]], "reviewed": True, "count": 92},
            {"extras": [[7, "TEXT", "-6"]], "reviewed": True, "count": 55},
        ]
        assert next(row for row in rows if row["id"] == 100)["status"] == (
            "reviewed-extra-parameter"
        )
        assert next(row for row in rows if row["id"] == 101)["status"] == (
            "unresolved-occurrence-parameter"
        )


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_tinbot_discover_ecm_extras_match_tracked_and_fresh_rules(tmp_path: Path) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    expected = {
        244: ("Discover", 2, [
            {"extras": [[277, "TEXT", "ReRoll"]], "reviewed": True, "count": 2},
        ]),
        247: ("ECM Guided", 4, [
            {"extras": [[7, "TEXT", "-6"]], "reviewed": True, "count": 2},
            {"extras": [[259, "TEXT", "-9"]], "reviewed": True, "count": 2},
        ]),
    }
    for rules_path in (ROOT / "data/generated/rules.db", fresh):
        report = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db",
            rules_path,
        )
        reviewed = RulesDatabase(rules_path).equipment_reviewed_extra_semantics()
        for source_id, (label, count, signatures) in expected.items():
            [row] = select_source_variants(report, "equipment", [source_id])["items"]
            assert row["reviewedVariant"] == {"kind": "named", "label": label}
            assert row["status"] == "reviewed-extra-parameter"
            assert row["reviewedExtra"] == reviewed[source_id]
            assert row["occurrences"] == count
            assert row["extraSignatures"] == signatures
        assert report["catalogs"]["equipment"]["summary"]["statuses"] == {
            "family-only": 19, "reviewed-exact-source": 1,
            "reviewed-extra-parameter": 13, "unresolved-occurrence-parameter": 1,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_killer_hacking_device_exact_source_variants_match_both_exports(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    signatures = (
        (13, "UPGRADE: Carbonite", 10),
        (14, "UPGRADE: Spotlight", 6),
        (20, "UPGRADE:\u00a0White Noise", 1),
        (21, "UPGRADE: Oblivion", 2),
        (270, "UPGRADE: Trinity (AP)", 2),
        (286, "UPGRADE: Trinity (-3)", 4),
        (334, "UPGRADE: Firewall (-3)", 14),
        (335, "UPGRADES: Carbonite, Firewall (-3)", 4),
        (339, "UPGRADE: Trinity (SR-1)", 1),
        (343, "UPGRADE: Trinity (PS=5)", 1),
    )
    expected = [
        {"extras": [[extra_id, "TEXT", raw]], "reviewed": True, "count": count}
        for extra_id, raw, count in signatures
    ]
    assert sum(count for _id, _raw, count in signatures) == 45
    for rules_path in (ROOT / "data/generated/rules.db", fresh):
        report = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db",
            rules_path,
        )
        [row] = select_source_variants(report, "equipment", [145])["items"]
        assert (row["name"], row["applicationId"], row["occurrences"]) == (
            "Killer Hacking Device", 145, 229,
        )
        assert row["status"] == "reviewed-extra-parameter"
        assert row["extraSignatures"] == expected
        assert row["reviewedCombinations"] is None
        assert row["rawValues"] == []
        assert row["reviewedExtra"] == (
            RulesDatabase(rules_path).equipment_reviewed_extra_semantics()[
                "killer-hacking-device"
            ]
        )
        assert report["catalogs"]["equipment"]["summary"]["statuses"] == {
            "family-only": 19, "reviewed-exact-source": 1,
            "reviewed-extra-parameter": 13, "unresolved-occurrence-parameter": 1,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_hacking_device_program_grants_preserve_unreviewed_overrides(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    expected = {
        100: {
            (12, "UPGRADE:\u00a0Trinity"): 17,
            (20, "UPGRADE:\u00a0White Noise"): 12,
            (25, "UPGRADE: Cybermask"): 1,
            (287, "UPGRADE: Zero Pain"): 120,
        },
        101: {(17, "UPGRADE:\u00a0Fairy Dust"): 46},
    }
    expected[100].update({
        (269, "UPGRADE: Oblivion (+1B)"): 7,
        (278, "UPGRADE: Total Control (+1B)"): 46,
        (285, "UPGRADE: Carbonite (+1 B)"): 7,
        (290, "UPGRADE: Trinity (+1B)"): 3,
        (363, "UPGRADE: Carbonite (PS=6)"): 8,
        (378, "UPGRADE: Trinity (+1SD)"): 1,
        (383, "UPGRADE: Carbonite (+1SD)"): 3,
    })
    expected[101].update({
        (269, "UPGRADE: Oblivion (+1B)"): 3,
        (378, "UPGRADE: Trinity (+1SD)"): 3,
    })
    expected[100].update({
        (331, "UPGRADE: Carbonite (SR-2)"): 1,
        (339, "UPGRADE: Trinity (SR-1)"): 2,
        (352, "UPGRADE: Trinity (SR-2)"): 4,
    })
    expected[101].update({
        (314, "UPGRADE: Total Control (SR-2)"): 46,
        (339, "UPGRADE: Trinity (SR-1)"): 2,
    })
    expected[100].update({
        (326, "Firewall -6"): 2,
        (334, "UPGRADE: Firewall (-3)"): 13,
        (376, "UPGRADE: Firewall (-6)"): 1,
    })
    for path in (ROOT / "data/generated/rules.db", fresh):
        report = inventory_source_variants(
            ROOT / "data/generated/infinity.db",
            ROOT / "data/generated/infinity.raw.db",
            path,
        )
        reviewed = RulesDatabase(path).equipment_reviewed_extra_semantics()
        for source_id, grants in expected.items():
            [item] = select_source_variants(report, "equipment", [source_id])["items"]
            slug = "hacking-device" if source_id == 100 else "hacking-device-plus"
            assert item["reviewedExtra"] == reviewed[slug]
            assert item["status"] == (
                "reviewed-extra-parameter" if source_id == 100
                else "unresolved-occurrence-parameter"
            )
            assert item["reviewedVariant"] is None
            checked = {
                (sig["extras"][0][0], sig["extras"][0][2]): sig["count"]
                for sig in item["extraSignatures"]
                if sig["reviewed"] and len(sig["extras"]) == 1
            }
            assert checked == grants
            assert all(
                sig["extras"][0][1] == "TEXT"
                for sig in item["extraSignatures"] if sig["reviewed"]
            )
            assert [
                sig for sig in item["extraSignatures"] if not sig["reviewed"]
            ] == ([] if source_id == 100 else [{
                "extras": [[344, "TEXT", "UPGRADE: SR-1"]],
                "reviewed": False, "count": 2,
            }])
            assert item["reviewedCombinations"] == (
                RulesDatabase(path).equipment_reviewed_combination_semantics()[slug]
            )
            trinity_ids = (
                {290: 3, 378: 1, 339: 2, 352: 4}
                if source_id == 100 else {378: 3, 339: 2}
            )
            trinity = [
                entry for entry in reviewed[slug]["extra_values"]
                if entry["extra_id"] in trinity_ids
            ]
            assert {entry["extra_id"] for entry in trinity} == set(trinity_ids)
            assert all(
                entry["effect"]["program"] == "hacking-program:trinity"
                and entry["effect"]["grantsProgram"] is True
                for entry in trinity
            )
            compound = next(
                pair for pair in item["reviewedCombinations"]
                if any(entry["extra_id"] == 343 for entry in pair["extras"])
            )
            trinity_index = next(
                i for i, entry in enumerate(compound["extras"])
                if entry["extra_id"] == 343
            )
            assert compound["effects"][trinity_index] == {
                "kind": "program-ps-replacement",
                "program": "hacking-program:trinity",
                "value": 5,
                "grantsProgram": True,
            }
            assert sum(trinity_ids.values()) + 2 == (
                12 if source_id == 100 else 7
            )
            assert all(
                "grantsProgram" not in effect
                for i, effect in enumerate(compound["effects"])
                if i != trinity_index
            )
        assert report["catalogs"]["equipment"]["summary"]["statuses"] == {
            "family-only": 19, "reviewed-exact-source": 1,
            "reviewed-extra-parameter": 13, "unresolved-occurrence-parameter": 1,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_neurocinetics_reactive_burst_extra_has_exact_source_owners() -> None:
    """Source-only review: +1B is not a generic Active Turn BS Attack bonus."""
    [item] = select_source_variants(_inventory(), "skills", [109])["items"]
    assert (item["name"], item["applicationId"], item["occurrences"]) == (
        "Neurocinetics", 109, 27,
    )
    assert item["extraSignatures"] == [{
        "extras": [[8, "TEXT", "+1B"]],
        "reviewed": True,
        "count": 4,
    }]
    assert item["status"] == "reviewed-extra-parameter"
    expected = {
        "source": "army-extra", "kind": "reviewed-extra",
        "extra_values": [{
            "extra_id": 8, "extra_type": "TEXT", "raw_value": "+1B",
            "effect": {
                "kind": "skill-burst-mod",
                "applies_to": "neurocinetics-reactive-turn-bs-weapon-single-target",
                "modifier": 1,
            },
        }],
    }
    assert item["reviewedExtra"] == expected
    assert RulesDatabase(ROOT / "data/generated/rules.db").skill_reviewed_extra_semantics()[
        "neurocinetics"
    ] == expected
    assert item["rawValues"] == []

    owners = source_extra_owner_context(
        ROOT / "data/generated/infinity.raw.db",
        catalog="skills", source_id=109, extra_id=8,
    )
    assert sorted((owner["army_id"], owner["unit_slug"]) for owner in owners) == [
        (201, "yan-hu-invincibles"),
        (204, "yan-hu-invincibles"),
        (401, "sunduqbut-covert-heavy-support-unit"),
        (402, "sunduqbut-covert-heavy-support-unit"),
    ]
    assert {owner["owner"] for owner in owners} == {"option"}
    assert all(
        owner["extra_position"] == 1
        and owner["extra_type"] == "TEXT"
        and owner["extra_raw"] == "+1B"
        for owner in owners
    )

    document = json.loads(
        (ROOT / "data/curated/rules/n5-core-v5.3.json").read_text(encoding="utf-8")
    )
    record = next(
        entry for entry in document["records"]
        if entry["id"] == "skill:neurocinetics"
    )
    assert any(
        citation["sourceId"] == "n5-core-v5.3-pdf" and citation["page"] == 104
        for citation in record["citations"]
    )
    assert any(
        "Reactive Turn" in effect and "MOD" in effect
        for effect in record["facts"]["effects"]
    )


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_neurocinetics_burst_is_identical_in_fresh_and_published_rules(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    for db_path in (ROOT / "data/generated/rules.db", fresh):
        [row] = select_source_variants(
            inventory_source_variants(
                ROOT / "data/generated/infinity.db",
                ROOT / "data/generated/infinity.raw.db", db_path,
            ),
            "skills", [109],
        )["items"]
        assert row["status"] == "reviewed-extra-parameter"
        assert row["extraSignatures"] == [{
            "extras": [[8, "TEXT", "+1B"]], "reviewed": True, "count": 4,
        }]
        assert row["reviewedExtra"]["extra_values"][0]["effect"] == {
            "kind": "skill-burst-mod",
            "applies_to": "neurocinetics-reactive-turn-bs-weapon-single-target",
            "modifier": 1,
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_minelayer_two_deployment_count_matches_pinned_source() -> None:
    """Source 56 permits two placed items, without extra Disposable uses."""
    [item] = select_source_variants(_inventory(), "skills", [56])["items"]
    assert (item["name"], item["occurrences"]) == ("Minelayer", 546)
    assert item["status"] == "reviewed-extra-parameter"
    assert item["extraSignatures"] == [{
        "extras": [[267, "TEXT", "2"]], "reviewed": True, "count": 15,
    }]
    assert item["reviewedCombinations"] is None
    assert item["rawValues"] == []
    expected = {
        "source": "army-extra", "kind": "reviewed-extra",
        "extra_values": [{
            "extra_id": 267, "extra_type": "TEXT", "raw_value": "2",
            "effect": {
                "kind": "minelayer-deployment-item-count",
                "applies_to": "minelayer-items-placed-during-deployment",
                "count": 2,
            },
        }],
    }
    assert item["reviewedExtra"] == expected
    assert RulesDatabase(ROOT / "data/generated/rules.db").skill_reviewed_extra_semantics()[
        "minelayer"
    ] == expected
    owners = source_extra_owner_context(
        ROOT / "data/generated/infinity.raw.db",
        catalog="skills", source_id=56, extra_id=267,
    )
    assert sorted((o["army_id"], o["unit_slug"], o["owner"]) for o in owners) == [
        (201, "zhencha", "option"),
        (204, "zhencha", "option"),
        (301, "scouts", "option"),
        (305, "scouts", "option"),
        (402, "hassassin-shujae", "option"),
        (402, "hassassin-shujae", "option"),
        (501, "tsyklon-sputniks", "option"),
        (504, "tsyklon-sputniks", "option"),
        (601, "victor-messer", "option"),
        (603, "victor-messer", "option"),
        (701, "dasyus", "option"),
        (703, "dasyus", "option"),
        (905, "tsyklon-sputniks", "option"),
        (908, "zhencha", "option"),
        (1002, "saladin-naval-liaison-officer", "profile"),
    ]
    assert all(o["extra_type"] == "TEXT" and o["extra_raw"] == "2"
               for o in owners)


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_minelayer_unparameterized_rows_do_not_inherit_two_items() -> None:
    """Only 15 exact occurrences, not all 546 Minelayer rows, carry (2)."""
    [row] = select_source_variants(_inventory(), "skills", [56])["items"]
    assert row["occurrences"] == 546
    assert row["extraSignatures"] == [
        {"extras": [[267, "TEXT", "2"]], "reviewed": True, "count": 15},
    ]
    assert row["occurrences"] - sum(
        signature["count"] for signature in row["extraSignatures"]
    ) == 531
    reviewed_values = {(267, "TEXT", "2")}
    assert reviewed_extra_signature(
        [(1, 267, "TEXT", "2")],
        reviewed_values=reviewed_values, distance_allowed=False,
    )
    assert not reviewed_extra_signature(
        [], reviewed_values=reviewed_values, distance_allowed=False,
    )
    assert not reviewed_extra_signature(
        [(1, 267, "TEXT", "3")],
        reviewed_values=reviewed_values, distance_allowed=False,
    )
    owners = source_extra_owner_context(
        ROOT / "data/generated/infinity.raw.db",
        catalog="skills", source_id=56, extra_id=267,
    )
    profile_owners = [owner for owner in owners if owner["owner"] == "profile"]
    assert [(owner["army_id"], owner["unit_slug"]) for owner in profile_owners] == [
        (1002, "saladin-naval-liaison-officer"),
    ]
    assert len(owners) == 15


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_chain_of_command_non_specialist_matches_exact_source_owners() -> None:
    """Non Specialist suppresses only CoC-derived scenario qualification."""
    [item] = select_source_variants(_inventory(), "skills", [26])["items"]
    assert (item["name"], item["applicationId"], item["occurrences"]) == (
        "Chain of Command", 26, 151,
    )
    assert item["status"] == "reviewed-extra-parameter"
    assert item["extraSignatures"] == [{
        "extras": [[375, "TEXT", "Non Specialist"]],
        "reviewed": True, "count": 11,
    }]
    assert item["reviewedCombinations"] is None
    assert item["rawValues"] == []
    expected = {
        "source": "army-extra", "kind": "reviewed-extra",
        "extra_values": [{
            "extra_id": 375, "extra_type": "TEXT",
            "raw_value": "Non Specialist",
            "effect": {
                "kind": "specialist-qualification-exclusion",
                "applies_to": "specialist-troop-qualification-from-chain-of-command",
                "excluded": True,
            },
        }],
    }
    assert item["reviewedExtra"] == expected
    assert RulesDatabase(ROOT / "data/generated/rules.db").skill_reviewed_extra_semantics()[
        "chain-of-command"
    ] == expected

    owners = source_extra_owner_context(
        ROOT / "data/generated/infinity.raw.db",
        catalog="skills", source_id=26, extra_id=375,
    )
    assert sorted((o["army_id"], o["unit_slug"]) for o in owners) == [
        (101, "jeanne-d-arc"),
        (101, "jeanne-d-arc"),
        (101, "jeanne-d-arc-v2-mobility-armor"),
        (101, "jeanne-d-arc-v2-mobility-armor"),
        (103, "jeanne-d-arc"),
        (103, "jeanne-d-arc"),
        (103, "jeanne-d-arc-v2-mobility-armor"),
        (103, "jeanne-d-arc-v2-mobility-armor"),
        (301, "william-wallace"),
        (302, "william-wallace"),
        (306, "william-wallace"),
    ]
    assert {o["owner"] for o in owners} == {"option"}
    assert all(o["extra_type"] == "TEXT" and o["extra_raw"] == "Non Specialist"
               for o in owners)


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_forward_observer_special_die_exact_profile_owners() -> None:
    """+1SD applies to Forward Observer rolls; it is not +1 Burst."""
    [item] = select_source_variants(_inventory(), "skills", [59])["items"]
    assert (item["name"], item["applicationId"], item["occurrences"]) == (
        "Forward Observer", 59, 609,
    )
    assert item["status"] == "reviewed-extra-parameter"
    assert item["extraSignatures"] == [{
        "extras": [[308, "TEXT", "+1SD"]], "reviewed": True, "count": 2,
    }]
    assert item["rawValues"] == []
    assert item["reviewedCombinations"] is None
    expected = {
        "source": "army-extra", "kind": "reviewed-extra",
        "extra_values": [{
            "extra_id": 308, "extra_type": "TEXT", "raw_value": "+1SD",
            "effect": {
                "kind": "special-die",
                "applies_to": "forward-observer-wip-attack-roll",
                "count": 1,
            },
        }],
    }
    assert item["reviewedExtra"] == expected
    assert RulesDatabase(ROOT / "data/generated/rules.db").skill_reviewed_extra_semantics()[
        "forward-observer"
    ] == expected
    owners = source_extra_owner_context(
        ROOT / "data/generated/infinity.raw.db",
        catalog="skills", source_id=59, extra_id=308,
    )
    assert sorted((o["army_id"], o["unit_slug"], o["owner"]) for o in owners) == [
        (701, "tarkshya-interception-wing", "profile"),
        (703, "tarkshya-interception-wing", "profile"),
    ]
    assert all(o["extra_type"] == "TEXT" and o["extra_raw"] == "+1SD"
               for o in owners)

    document = json.loads(
        (ROOT / "data/curated/rules/n5-core-v5.3.json").read_text(encoding="utf-8")
    )
    record = next(
        value for value in document["records"]
        if value["id"] == "skill:forward-observer"
    )
    assert {(c["sourceId"], c.get("page")) for c in record["citations"]} >= {
        ("n5-core-v5.3-pdf", 75), ("n5-core-v5.3-pdf", 92),
    }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_forward_observer_special_die_fresh_export_preserves_exact_scope(
    tmp_path: Path,
) -> None:
    """A family metadata entry never assigns +1SD to the other 607 rows."""
    fresh = tmp_path / "rules.db"
    export_rules_database(load_curated_directory(ROOT / "data/curated/rules"), fresh)
    published = ROOT / "data/generated/rules.db"
    expected = RulesDatabase(published).skill_reviewed_extra_semantics()[
        "forward-observer"
    ]
    reviewed_values = {(308, "TEXT", "+1SD")}
    assert reviewed_extra_signature(
        [(1, 308, "TEXT", "+1SD")],
        reviewed_values=reviewed_values, distance_allowed=False,
    )
    assert not reviewed_extra_signature(
        [], reviewed_values=reviewed_values, distance_allowed=False,
    )
    assert not reviewed_extra_signature(
        [(1, 308, "TEXT", "+1B")],
        reviewed_values=reviewed_values, distance_allowed=False,
    )
    for rules_path in (published, fresh):
        typed = RulesDatabase(rules_path).skill_reviewed_extra_semantics()
        assert typed["forward-observer"] == expected
        assert typed["forward-observer"]["extra_values"][0]["effect"] == {
            "kind": "special-die",
            "applies_to": "forward-observer-wip-attack-roll",
            "count": 1,
        }
        [row] = select_source_variants(
            inventory_source_variants(
                ROOT / "data/generated/infinity.db",
                ROOT / "data/generated/infinity.raw.db", rules_path,
            ),
            "skills", [59],
        )["items"]
        assert row["status"] == "reviewed-extra-parameter"
        assert row["reviewedExtra"] == expected
        assert row["extraSignatures"] == [
            {"extras": [[308, "TEXT", "+1SD"]], "reviewed": True, "count": 2},
        ]
        assert row["occurrences"] == 609
        assert row["occurrences"] - sum(
            signature["count"] for signature in row["extraSignatures"]
        ) == 607
        assert row["reviewedNumericMod"] is None
        assert "modifier" not in typed["forward-observer"]["extra_values"][0]["effect"]


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_source_inventory_is_deterministic() -> None:
    first = _inventory()
    assert json.dumps(first, sort_keys=True) == json.dumps(_inventory(), sort_keys=True)
