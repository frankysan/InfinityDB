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


def _inventory() -> dict:
    return inventory_source_variants(
        ROOT / "data/generated/infinity.db",
        ROOT / "data/generated/infinity.raw.db",
        ROOT / "data/generated/rules.db",
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
            "reviewed-extra-parameter": 2,
            "unresolved-occurrence-parameter": 34,
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
            "unresolved-occurrence-parameter",
        }


@pytest.mark.usefixtures("requires_pinned_raw_army_archive")
def test_known_ambiguous_extras_do_not_become_reviewed_variants() -> None:
    report = _inventory()["catalogs"]
    skills = {item["id"]: item for item in report["skills"]["items"]}
    equipment = {item["id"]: item for item in report["equipment"]["items"]}

    # A TEXT extra is not automatically a reviewed modifier. Three
    # source IDs now have exact typed mappings; the others remain open.
    for source_id in (25, 55, 1000):
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
        "reviewed-extra-parameter": 2,
        "unresolved-occurrence-parameter": 34,
    }
    assert sources[28]["status"] == "reviewed-numeric-parameter"
    assert all(s["reviewed"] for s in sources[28]["extraSignatures"])
    assert sources[24]["reviewedNumericMod"] is not None
    assert sources[24]["status"] == "reviewed-numeric-parameter"
    assert sources[40]["status"] == "reviewed-extra-parameter"
    assert all(s["reviewed"] for s in sources[40]["extraSignatures"])
    assert sources[25]["status"] == "unresolved-occurrence-parameter"
    # Existing distance-only projection remains independent of numeric MODs.
    assert rules.skill_parameter_semantics() == {
        "super-jump": {"kind": "distance", "positive_sign": "omit"},
        "forward-deployment": {"kind": "distance", "positive_sign": "force"},
        263: {"kind": "distance", "positive_sign": "omit"},
        271: {"kind": "distance", "positive_sign": "omit"},
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
def test_source_inventory_is_deterministic() -> None:
    first = _inventory()
    assert json.dumps(first, sort_keys=True) == json.dumps(_inventory(), sort_keys=True)
