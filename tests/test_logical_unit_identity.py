from __future__ import annotations

from infinity_db.database.unit_identity import resolve_logical_unit_identity
from infinity_db.identities import load_identity_config


def _unit(unit_id: int, *, role: str = "standard", label: str | None = None) -> dict:
    return {
        "id": unit_id,
        "name": label or f"Unit {unit_id}",
        "isc": label or f"Unit {unit_id}",
        "source_defined": True,
        "source_role": role,
    }


def test_resolver_materializes_transitive_identity_evidence() -> None:
    data = {
        "genericUnitMatches": [
            {
                "sourceUnitId": 1690,
                "representativeUnitId": 200,
                "method": "generic_duplicate_key",
            }
        ],
        "mercenaryUnitMatches": [
            {
                "mercenaryUnitId": 10200,
                "standardUnitId": 200,
                "method": "generic_duplicate_key",
            }
        ],
        "unmatchedMercenaryUnitIds": [],
        "tables": {
            "units": [
                _unit(200),
                _unit(300),
                _unit(1690),
                _unit(10200, role="mercenary_variant"),
                _unit(2200, label="Reinf. Unit 200"),
            ],
            "army_lists": [
                {"id": 101, "kind": "faction"},
                {"id": 199, "kind": "reinforcement"},
            ],
            "army_units": [
                {"army_id": 101, "unit_id": 200},
                {"army_id": 101, "unit_id": 300},
                {"army_id": 101, "unit_id": 1690},
                {"army_id": 101, "unit_id": 10200},
                {"army_id": 199, "unit_id": 2200},
            ],
        },
    }

    resolution = resolve_logical_unit_identity(
        data,
        load_identity_config(),
        reinforcement_matches={2200: 200},
    )

    assert resolution.logical_units == ({"id": 300, "representative_unit_id": 300},)
    assert resolution.logical_unit_sources == (
        {"source_unit_id": 200, "logical_unit_id": 300},
        {"source_unit_id": 300, "logical_unit_id": 300},
        {"source_unit_id": 1690, "logical_unit_id": 300},
        {"source_unit_id": 2200, "logical_unit_id": 300},
        {"source_unit_id": 10200, "logical_unit_id": 300},
    )


def test_resolver_keeps_explicitly_unmatched_special_variants_separate() -> None:
    data = {
        "genericUnitMatches": [],
        "mercenaryUnitMatches": [],
        "unmatchedMercenaryUnitIds": [10064],
        "tables": {
            "units": [
                _unit(64, label="Same"),
                _unit(10064, role="mercenary_variant", label="Same"),
                _unit(2064, label="Same"),
            ],
            "army_lists": [
                {"id": 101, "kind": "faction"},
                {"id": 199, "kind": "reinforcement"},
            ],
            "army_units": [
                {"army_id": 101, "unit_id": 64},
                {"army_id": 101, "unit_id": 10064},
                {"army_id": 199, "unit_id": 2064},
            ],
        },
    }

    resolution = resolve_logical_unit_identity(
        data,
        load_identity_config(),
        reinforcement_matches={},
    )

    assert resolution.logical_units == (
        {"id": 64, "representative_unit_id": 64},
        {"id": 2064, "representative_unit_id": 2064},
        {"id": 10064, "representative_unit_id": 10064},
    )
    assert resolution.logical_unit_sources == (
        {"source_unit_id": 64, "logical_unit_id": 64},
        {"source_unit_id": 2064, "logical_unit_id": 2064},
        {"source_unit_id": 10064, "logical_unit_id": 10064},
    )


def test_resolver_retains_legacy_duplicate_fallback_when_generic_audit_is_absent() -> None:
    data = {
        "tables": {
            "units": [
                _unit(64, label="Legacy duplicate"),
                _unit(10064, label="Legacy duplicate"),
            ],
            "army_lists": [{"id": 101, "kind": "faction"}],
            "army_units": [
                {"army_id": 101, "unit_id": 64},
                {"army_id": 101, "unit_id": 10064},
            ],
        }
    }

    resolution = resolve_logical_unit_identity(
        data,
        load_identity_config(),
        reinforcement_matches={},
    )

    assert resolution.logical_units == ({"id": 64, "representative_unit_id": 64},)
    assert resolution.logical_unit_sources == (
        {"source_unit_id": 64, "logical_unit_id": 64},
        {"source_unit_id": 10064, "logical_unit_id": 64},
    )
