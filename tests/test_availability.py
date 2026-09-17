from pathlib import Path

import pytest

import infinity_army_data.cli as cli
from infinity_army_data.availability import (
    MERCENARY_MATCH_METHOD,
    annotate_availability_semantics,
    audit_mercenary_logical_matches,
)


def normalized_units(*units, memberships=(), occurrences=()):
    return {
        "_meta": {
            "tableCounts": {
                "units": len(units),
                "unit_factions": len(memberships),
                "army_units": len(occurrences),
            },
            "warningCount": 0,
        },
        "tables": {
            "units": [dict(unit) for unit in units],
            "unit_factions": [dict(row) for row in memberships],
            "army_units": [dict(row) for row in occurrences],
        },
        "warnings": [],
    }


def test_canonical_mercenary_source_with_declared_factions_is_standard() -> None:
    data = normalized_units(
        {
            "id": 51,
            "canonical_faction_id": 1,
            "main_army_id": 901,
            "slug": "miranda-ashcroft",
            "source_defined": True,
        },
        memberships=[{"unit_id": 51, "faction_id": 202}],
        occurrences=[{"army_id": 202, "unit_id": 51}],
    )

    annotate_availability_semantics(data)

    assert data["tables"]["units"][0]["source_role"] == "standard"
    assert data["tables"]["units"][0]["main_army_id"] is None
    assert data["tables"]["army_units"][0]["availability_kind"] == "standard"


def test_mercenary_variant_uses_source_markers_not_unit_id_pattern() -> None:
    data = normalized_units(
        {
            "id": 50_123,
            "canonical_faction_id": 1,
            "main_army_id": 901,
            "slug": "merc-example-authorized",
            "source_defined": True,
        },
        occurrences=[{"army_id": 101, "unit_id": 50_123}],
    )

    annotate_availability_semantics(data)

    assert data["tables"]["units"][0]["source_role"] == "mercenary_variant"
    assert data["tables"]["units"][0]["main_army_id"] is None
    assert data["tables"]["army_units"][0]["availability_kind"] == "mercenary"


def test_mercenary_mapping_audit_matches_standard_duplicate_family() -> None:
    data = normalized_units(
        {
            "id": 51,
            "canonical_faction_id": 1,
            "isc": "Miranda Ashcroft",
            "name": "MIRANDA ASHCROFT",
            "slug": "miranda-ashcroft",
            "source_defined": True,
        },
        {
            "id": 10051,
            "canonical_faction_id": 1,
            "isc": "Miranda Ashcroft",
            "name": "MIRANDA ASHCROFT",
            "slug": "merc-miranda-ashcroft-authorized",
            "source_defined": True,
        },
        memberships=[{"unit_id": 51, "faction_id": 202}],
    )

    annotate_availability_semantics(data)
    matches, unmatched = audit_mercenary_logical_matches(data)

    assert matches == {10051: 51}
    assert unmatched == ()
    assert data["mercenaryUnitMatches"] == [
        {
            "mercenaryUnitId": 10051,
            "standardUnitId": 51,
            "method": MERCENARY_MATCH_METHOD,
        }
    ]
    assert data["unmatchedMercenaryUnitIds"] == []


def test_mercenary_mapping_audit_does_not_match_numeric_family_alone() -> None:
    data = normalized_units(
        {
            "id": 64,
            "canonical_faction_id": 202,
            "isc": "Alpha Unit",
            "name": "ALPHA UNIT",
            "slug": "alpha-unit",
            "source_defined": True,
        },
        {
            "id": 10064,
            "canonical_faction_id": 1,
            "isc": "Beta Unit",
            "name": "BETA UNIT",
            "slug": "merc-beta-unit",
            "source_defined": True,
        },
        memberships=[{"unit_id": 64, "faction_id": 202}],
    )

    annotate_availability_semantics(data)
    matches, unmatched = audit_mercenary_logical_matches(data)

    assert matches == {}
    assert unmatched == (10064,)
    assert data["mercenaryUnitMatches"] == []
    assert data["unmatchedMercenaryUnitIds"] == [10064]


@pytest.mark.parametrize(
    ("canonical_faction_id", "slug", "memberships", "message"),
    [
        (2, "merc-example", [], "canonical faction"),
        (1, "merc-example", [{"unit_id": 10001, "faction_id": 202}], "normal faction"),
        (1, "example", [], "source contract may have changed"),
    ],
)
def test_inconsistent_mercenary_source_markers_fail_normalization(
    canonical_faction_id: int,
    slug: str,
    memberships: list[dict],
    message: str,
) -> None:
    data = normalized_units(
        {
            "id": 10001,
            "canonical_faction_id": canonical_faction_id,
            "slug": slug,
            "source_defined": True,
        },
        memberships=memberships,
        occurrences=[{"army_id": 101, "unit_id": 10001}],
    )

    with pytest.raises(ValueError, match=message):
        annotate_availability_semantics(data)


def test_normalize_pipeline_applies_availability_annotation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    normalized = normalized_units(
        {
            "id": 10464,
            "canonical_faction_id": 1,
            "slug": "merc-valerya-gromoz",
            "source_defined": True,
        },
        occurrences=[{"army_id": 101, "unit_id": 10464}],
    )
    monkeypatch.setattr(cli, "normalize_master", lambda *args, **kwargs: normalized)
    monkeypatch.setattr(cli, "validate_normalized", lambda data: {"checkCount": 1})
    monkeypatch.setattr(cli, "write_normalized", lambda *args, **kwargs: None)

    result = cli._normalize(
        {},
        tmp_path / "normalized.json",
        tmp_path / "validation.json",
        compact=True,
    )

    assert result["tables"]["units"][0]["source_role"] == "mercenary_variant"
    assert result["tables"]["army_units"][0]["availability_kind"] == "mercenary"
    assert result["mercenaryUnitMatches"] == []
    assert result["unmatchedMercenaryUnitIds"] == [10464]
