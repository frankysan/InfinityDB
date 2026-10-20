"""Characterize pinned source-level Skill/Equipment parameters before usage indexing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_directory
from infinity_db.rules_database import RulesDatabase, export_rules_database
from tools.audit_source_variant_inputs import inventory_source_variants

pytestmark = pytest.mark.usefixtures("requires_pinned_raw_army_archive")

ROOT = Path(__file__).resolve().parents[1]


def _inventory() -> dict:
    return inventory_source_variants(
        ROOT / "data/generated/infinity.db",
        ROOT / "data/generated/infinity.raw.db",
        ROOT / "data/generated/rules.db",
    )


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
            "reviewed-distance-parameter": 1,
            "reviewed-exact-source": 10,
            "reviewed-numeric-parameter": 2,
            "reviewed-extra-parameter": 1,
            "unresolved-occurrence-parameter": 38,
        },
        "extraTypes": {"DISTANCE": 5, "TEXT": 39},
    }
    assert equipment["summary"] == {
        "publishedSourceIds": 34,
        "sourceIdsWithDirectRows": 34,
        "directSourceRows": 5427,
        "reviewedExactSourceIds": 4,
        "statuses": {
            "family-only": 19,
            "reviewed-exact-source": 1,
            "unresolved-occurrence-parameter": 14,
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


def test_known_ambiguous_extras_do_not_become_reviewed_variants() -> None:
    report = _inventory()["catalogs"]
    skills = {item["id"]: item for item in report["skills"]["items"]}
    equipment = {item["id"]: item for item in report["equipment"]["items"]}

    # A TEXT extra is not automatically a reviewed modifier. Three
    # source IDs now have exact typed mappings; the others remain open.
    for source_id in (25, 55, 74, 1000):
        item = skills[source_id]
        assert item["status"] == "unresolved-occurrence-parameter"
        assert "TEXT" in item["extraTypes"]
        assert item["extraSignatures"]
    assert skills[24]["status"] == "reviewed-numeric-parameter"
    assert skills[28]["status"] == "reviewed-numeric-parameter"
    assert skills[40]["status"] == "reviewed-extra-parameter"
    for source_id in (24, 28, 40):
        assert all(part["reviewed"] for part in skills[source_id]["extraSignatures"])
    for source_id in (100, 101, 169, 244, 247):
        item = equipment[source_id]
        assert item["status"] == "unresolved-occurrence-parameter"
        assert item["extraTypes"] == ["TEXT"]
        assert item["extraSignatures"]
    assert equipment[169]["reviewedVariant"] == {"kind": "named", "label": "Firewall"}
    assert skills[28]["reviewedVariant"] is None
    assert any(
        part[2] == "-3"
        for signature in skills[28]["extraSignatures"]
        for part in signature["extras"]
    )

    # Source-typed DISTANCE is not sufficient by itself. Forward Deployment
    # has reviewed distance semantics, but Jump and Climb are not certified.
    assert skills[161]["status"] == "reviewed-distance-parameter"
    assert skills[161]["extraTypes"] == ["DISTANCE"]
    for source_id in (263, 271):
        assert skills[source_id]["status"] == "unresolved-occurrence-parameter"
        assert skills[source_id]["extraTypes"] == ["DISTANCE"]
    assert skills[74]["extraTypes"] == ["DISTANCE", "TEXT"]

    # No direct source occurrence is manufactured from curated-only TinBot variants.
    assert 188 not in equipment and 193 not in equipment
    assert equipment[248]["status"] == "reviewed-exact-source"


def _single_extra_counts(item: dict) -> dict[tuple[int, str, str], int]:
    return {
        tuple(signature["extras"][0]): signature["count"]
        for signature in item["extraSignatures"]
        if len(signature["extras"]) == 1
    }


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
    assert set(parameters) == {"mimetism", "berserk", "dodge"}
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
        "reviewed-distance-parameter": 1,
        "reviewed-exact-source": 10,
        "reviewed-numeric-parameter": 2,
        "reviewed-extra-parameter": 1,
        "unresolved-occurrence-parameter": 38,
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
    }


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


def test_source_inventory_is_deterministic() -> None:
    first = _inventory()
    assert json.dumps(first, sort_keys=True) == json.dumps(_inventory(), sort_keys=True)
