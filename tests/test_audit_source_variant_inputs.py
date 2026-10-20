"""Characterize pinned source-level Skill/Equipment parameters before usage indexing."""

from __future__ import annotations

import json
from pathlib import Path

from tools.audit_source_variant_inputs import inventory_source_variants

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
            "unresolved-occurrence-parameter": 41,
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
            "unresolved-occurrence-parameter",
        }


def test_known_ambiguous_extras_do_not_become_reviewed_variants() -> None:
    report = _inventory()["catalogs"]
    skills = {item["id"]: item for item in report["skills"]["items"]}
    equipment = {item["id"]: item for item in report["equipment"]["items"]}

    # The source type is TEXT, even for a numeral-looking MOD. It is
    # evidence, not reviewed +SD/Burst/Level semantics for an index.
    for source_id in (24, 25, 28, 40, 55, 74, 1000):
        item = skills[source_id]
        assert item["status"] == "unresolved-occurrence-parameter"
        assert "TEXT" in item["extraTypes"]
        assert item["extraSignatures"]
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
    assert mimetism["status"] == "unresolved-occurrence-parameter"

    berserk = skills[24]
    # N5.3 p. 86: bracketed positive MODs affect the owner's Berserk
    # CC Attack. They do not become a generic modifier on every CC roll.
    berserk_extras = _single_extra_counts(berserk)
    assert berserk_extras[(1, "TEXT", "+3")] == 243
    assert berserk_extras[(2, "TEXT", "+6")] == 3
    assert berserk["status"] == "unresolved-occurrence-parameter"

    dodge = skills[40]
    # N5.3 pp. 23, 79: a Dodge Skill's bracketed MOD is distinct from
    # situational -3 PH penalties; movement distances are another axis.
    dodge_extras = _single_extra_counts(dodge)
    assert dodge_extras[(1, "TEXT", "+3")] == 613
    assert dodge_extras[(2, "TEXT", "+6")] == 7
    assert dodge["extraTypes"] == ["DISTANCE", "TEXT"]
    assert dodge["status"] == "unresolved-occurrence-parameter"
    # The currently supported curated occurrence-parameter contract is
    # distance only: source TEXT values must not auto-promote to a typed MOD.


def test_source_inventory_is_deterministic() -> None:
    first = _inventory()
    assert json.dumps(first, sort_keys=True) == json.dumps(_inventory(), sort_keys=True)
