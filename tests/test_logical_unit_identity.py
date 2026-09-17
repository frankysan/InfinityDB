from __future__ import annotations

import pytest

from infinity_db.database.unit_identity import (
    reinforcement_unit_matches,
    resolve_logical_unit_identity,
)
from infinity_db.identities import load_identity_config


def _unit(unit_id: int, *, role: str = "standard", label: str | None = None) -> dict:
    return {
        "id": unit_id,
        "name": label or f"Unit {unit_id}",
        "isc": label or f"Unit {unit_id}",
        "source_defined": True,
        "source_role": role,
    }


def _identity_data(
    units: list[dict],
    memberships: dict[int, list[tuple[int, str]]],
    **metadata: object,
) -> dict:
    army_kinds: dict[int, str] = {}
    army_units: list[dict[str, int]] = []
    for unit_id, armies in memberships.items():
        for army_id, kind in armies:
            previous = army_kinds.setdefault(army_id, kind)
            assert previous == kind
            army_units.append({"army_id": army_id, "unit_id": unit_id})
    return {
        **metadata,
        "tables": {
            "units": units,
            "army_lists": [
                {"id": army_id, "kind": kind}
                for army_id, kind in sorted(army_kinds.items())
            ],
            "army_units": army_units,
        },
    }


def _source_mapping(data: dict, *, reinforcement_matches: dict[int, int]) -> dict[int, int]:
    resolution = resolve_logical_unit_identity(
        data,
        load_identity_config(),
        reinforcement_matches=reinforcement_matches,
    )
    return {
        row["source_unit_id"]: row["logical_unit_id"]
        for row in resolution.logical_unit_sources
    }


def _reinforcement_match_data(standard: dict, *reinforcements: dict) -> dict:
    units = [standard, *reinforcements]
    memberships = {standard["id"]: [(101, "faction")]}
    memberships.update(
        {reinforcement["id"]: [(199, "reinforcement")] for reinforcement in reinforcements}
    )
    return _identity_data(units, memberships, genericUnitMatches=[])


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
                _unit(2200, label="Completely unrelated reinforcement label"),
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


def test_empty_generic_audit_disables_legacy_duplicate_fallback() -> None:
    data = _identity_data(
        [_unit(64, label="Same"), _unit(10064, label="Same")],
        {64: [(101, "faction")], 10064: [(101, "faction")]},
        genericUnitMatches=[],
    )

    assert _source_mapping(data, reinforcement_matches={}) == {64: 64, 10064: 10064}


@pytest.mark.parametrize(
    ("canonical_id", "source_ids"),
    [
        (300, (300, 1690, 10300)),
        (1345, (1345, 1875, 11345)),
    ],
)
def test_configured_alias_group_uses_declared_canonical_representative(
    canonical_id: int, source_ids: tuple[int, ...]
) -> None:
    data = _identity_data(
        [_unit(source_id, label=f"Distinct {source_id}") for source_id in source_ids],
        {source_id: [(101, "faction")] for source_id in source_ids},
        genericUnitMatches=[],
    )

    mapping = _source_mapping(data, reinforcement_matches={})

    assert mapping == {source_id: canonical_id for source_id in source_ids}


def test_explicit_empty_reinforcement_audit_disables_name_matching() -> None:
    data = _reinforcement_match_data(
        _unit(35, label="Armbots: Bulleteer"),
        _unit(1649, label="Reinf. Bulleteers Armbots"),
    )

    assert _source_mapping(data, reinforcement_matches={}) == {35: 35, 1649: 1649}


def test_reinforcement_audit_matches_multiple_variants_to_standard_unit() -> None:
    data = _reinforcement_match_data(
        _unit(265, label="Wardrivers, Mercenary Hackers"),
        _unit(1635, label="Reinf. Wardrivers, Mercenary Hackers"),
        _unit(1691, label="Reinf. Wardrivers, Mercenary Hackers"),
        _unit(2691, label="Reinf. Wardrivers, Mercenary Hackers"),
    )

    assert reinforcement_unit_matches(data, load_identity_config()) == {
        1635: 265,
        1691: 265,
        2691: 265,
    }


def test_reinforcement_audit_matches_reordered_pluralized_identity() -> None:
    standard = {
        **_unit(35),
        "isc": "Armbots: Bulleteer",
        "name": "BULLETEER ARMBOTS",
    }
    reinforcement = {
        **_unit(1649),
        "isc": "Reinf. Bulleteers Armbots",
        "name": "REINF: ARMBOTS BULLETEERS",
    }
    data = _reinforcement_match_data(standard, reinforcement)

    assert reinforcement_unit_matches(data, load_identity_config()) == {1649: 35}


def test_reinforcement_audit_uses_display_name_when_isc_is_abbreviated() -> None:
    standard = {
        **_unit(1751),
        "isc": "Blade-Ops, Neoterran Unified Commando Regiment",
        "name": "BLADE-OPS, Neoterran Unified Commando Regiment",
    }
    reinforcement = {
        **_unit(1642),
        "isc": "Reinf. Blade-Ops",
        "name": "REINF: BLADE-OPS, Unified Neoterran Commando Regiment",
    }
    data = _reinforcement_match_data(standard, reinforcement)

    assert reinforcement_unit_matches(data, load_identity_config()) == {1642: 1751}


@pytest.mark.parametrize(
    ("standard", "reinforcement"),
    [
        (
            {
                **_unit(1624),
                "isc": "Caskuda WCD Armored Jump Operator",
                "name": "CASKUDA",
            },
            {
                **_unit(1618),
                "isc": "Reinf. Caskuda WCD Armoured Jump Operator",
                "name": "REINF. CASKUDA",
            },
        ),
        (
            {
                **_unit(1610),
                "isc": "Ŝarko, Naval Reconaissance Special Unit",
                "name": "ŜARKO",
            },
            {
                **_unit(1700),
                "isc": "Reinf. Ŝarko, Naval Recon Special Unit",
                "name": "REINF: ŜARKO",
            },
        ),
    ],
)
def test_reinforcement_audit_matches_known_spelling_aliases(
    standard: dict, reinforcement: dict
) -> None:
    data = _reinforcement_match_data(standard, reinforcement)

    assert reinforcement_unit_matches(data, load_identity_config()) == {
        reinforcement["id"]: standard["id"]
    }
