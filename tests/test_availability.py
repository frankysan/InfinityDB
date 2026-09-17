from pathlib import Path

import pytest

import infinity_army_data.cli as cli
from infinity_army_data.availability import (
    GENERIC_MATCH_METHOD,
    MERCENARY_MATCH_METHOD,
    annotate_availability_semantics,
    audit_generic_logical_matches,
    audit_mercenary_logical_matches,
)
from infinity_army_data.merge import load_sources, merge_sources
from infinity_army_data.normalize import normalize_master

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "mercenary_source_roles"


def normalized_units(*units, memberships=(), occurrences=(), army_lists=()):
    return {
        "_meta": {
            "tableCounts": {
                "units": len(units),
                "unit_factions": len(memberships),
                "army_units": len(occurrences),
                "army_lists": len(army_lists),
            },
            "warningCount": 0,
        },
        "tables": {
            "units": [dict(unit) for unit in units],
            "unit_factions": [dict(row) for row in memberships],
            "army_units": [dict(row) for row in occurrences],
            "army_lists": [dict(row) for row in army_lists],
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


def test_generic_mapping_audit_persists_standard_duplicate_family() -> None:
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
            "canonical_faction_id": 202,
            "isc": "Alpha Unit",
            "name": "ALPHA UNIT",
            "slug": "alpha-unit-duplicate",
            "source_defined": True,
        },
        memberships=[
            {"unit_id": 64, "faction_id": 202},
            {"unit_id": 10064, "faction_id": 202},
        ],
        occurrences=[
            {"army_id": 202, "unit_id": 64},
            {"army_id": 202, "unit_id": 10064},
        ],
        army_lists=[{"id": 202, "kind": "sectorial"}],
    )

    annotate_availability_semantics(data)
    matches = audit_generic_logical_matches(data)

    assert matches == {10064: 64}
    assert data["genericUnitMatches"] == [
        {
            "sourceUnitId": 10064,
            "representativeUnitId": 64,
            "method": GENERIC_MATCH_METHOD,
        }
    ]


def test_generic_mapping_audit_excludes_reinforcement_only_units() -> None:
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
            "canonical_faction_id": 202,
            "isc": "Alpha Unit",
            "name": "ALPHA UNIT",
            "slug": "alpha-unit-reinforcement",
            "source_defined": True,
        },
        memberships=[
            {"unit_id": 64, "faction_id": 202},
            {"unit_id": 10064, "faction_id": 202},
        ],
        occurrences=[
            {"army_id": 202, "unit_id": 64},
            {"army_id": 998, "unit_id": 10064},
        ],
        army_lists=[
            {"id": 202, "kind": "sectorial"},
            {"id": 998, "kind": "reinforcement"},
        ],
    )

    annotate_availability_semantics(data)
    matches = audit_generic_logical_matches(data)

    assert matches == {}
    assert data["genericUnitMatches"] == []


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
    assert result["genericUnitMatches"] == []
    assert result["mercenaryUnitMatches"] == []
    assert result["unmatchedMercenaryUnitIds"] == [10464]


def test_source_shaped_mercenary_patterns_survive_merge_and_normalization() -> None:
    sources, skipped = load_sources(FIXTURE_DIR)
    assert skipped == []

    normalized = normalize_master(merge_sources(sources))
    annotate_availability_semantics(normalized)
    matches, unmatched = audit_mercenary_logical_matches(normalized)

    units = {row["id"]: row for row in normalized["tables"]["units"]}
    assert units[51]["source_role"] == "standard"
    assert units[51]["main_army_id"] is None
    assert units[10051]["source_role"] == "mercenary_variant"
    assert units[378]["source_role"] == "standard"
    assert units[378]["main_army_id"] is None
    assert units[10378]["source_role"] == "mercenary_variant"
    assert units[464]["source_role"] == "standard"
    assert units[10464]["source_role"] == "mercenary_variant"

    availability = {
        (row["army_id"], row["unit_id"]): row["availability_kind"]
        for row in normalized["tables"]["army_units"]
    }
    assert availability[(202, 51)] == "standard"
    assert availability[(101, 10051)] == "mercenary"
    assert availability[(401, 378)] == "standard"
    assert availability[(401, 10378)] == "mercenary"
    assert availability[(404, 464)] == "standard"
    assert availability[(101, 10464)] == "mercenary"

    assert matches == {10051: 51, 10378: 378, 10464: 464}
    assert unmatched == ()



@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("canonical", 2, "canonical faction"),
        ("factions", [101], "normal faction"),
        ("slug", "miranda-ashcroft-authorized", "source contract may have changed"),
    ],
)
def test_source_shaped_mercenary_contract_drift_fails_closed(
    field: str, value: object, message: str
) -> None:
    sources, _ = load_sources(FIXTURE_DIR)
    panoceania = next(source for source in sources if source.faction_id == 101)
    miranda = next(unit for unit in panoceania.data["units"] if unit["id"] == 10051)
    miranda[field] = value

    normalized = normalize_master(merge_sources(sources))
    with pytest.raises(ValueError, match=message):
        annotate_availability_semantics(normalized)

def test_source_shaped_overlap_preserves_standard_and_optional_availability() -> None:
    sources, _ = load_sources(FIXTURE_DIR)
    normalized = normalize_master(merge_sources(sources))
    annotate_availability_semantics(normalized)

    yuan_occurrences = [
        row
        for row in normalized["tables"]["army_units"]
        if row["army_id"] == 401 and row["unit_id"] in {378, 10378}
    ]

    assert [(row["unit_id"], row["availability_kind"]) for row in yuan_occurrences] == [
        (378, "standard"),
        (10378, "mercenary"),
    ]
