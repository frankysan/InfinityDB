from __future__ import annotations

from tools.audit_weapon_chart_profiles import (
    _printed_name_and_mode,
    _value,
    compare_rows,
    markdown_report,
    rows_from_words,
)


def _pdf_row(name: str = "Tactical Bow") -> dict[str, object]:
    return {
        "page": 176,
        "name": name,
        "ps": "8",
        "burst": "1",
        "ammunition": "DA",
        "savingAttribute": "ARM",
        "savingRolls": "2",
    }


def _army_row(name: str = "Tactical Bow") -> dict[str, str]:
    return {
        "name": name,
        "mode": "",
        "ps": "8",
        "burst": "1",
        "ammunition": "DA",
        "savingAttribute": "ARM",
        "savingRolls": "2",
    }


def test_single_baseline_weapon_extracts_all_five_cells() -> None:
    words = [
        (24.0, 304.4, "TACTICAL"),
        (63.0, 304.4, "BOW"),
        (276.0, 304.4, "8"),
        (297.0, 304.4, "1"),
        (330.0, 304.4, "DA"),
        (377.0, 304.4, "ARM"),
        (435.0, 304.4, "2"),
        (510.0, 304.4, "SILENT"),
        (25.0, 250.0, "NAME"),
    ]
    assert rows_from_words(words, 176) == [_pdf_row("TACTICAL BOW")]


def test_compares_matching_metadata_without_claiming_completeness() -> None:
    result = compare_rows([_pdf_row()], {"tacticalbow": [_army_row()]})
    assert result["chartRowsLocated"] == 1
    assert result["unambiguousRowsCompared"] == 1
    assert result["matchingRows"] == 1
    assert result["candidateDiscrepancies"] == 0


def test_nonoperative_saving_roll_multiplier_matches_no_rolls() -> None:
    pdf = _pdf_row("Mine Dispenser")
    pdf["savingAttribute"] = "--"
    pdf["savingRolls"] = "--"
    army = _army_row("Mine Dispenser")
    army["savingAttribute"] = "-"
    army["savingRolls"] = "1"
    result = compare_rows([pdf], {"minedispenser": [army]})
    assert result["matchingRows"] == 1
    assert result["candidateDiscrepancies"] == 0
    assert result["compared"][0]["differences"] == []
    assert result["compared"][0]["army"]["savingRolls"] == "1"
    assert result["compared"][0]["pdf"]["savingRolls"] == "--"
    report = {
        "corePdfSha256": "abc", "armyMetadataProfiles": 1,
        "comparison": result, "notCompared": ["range bands"],
    }
    assert "Candidate discrepancies: **0**" in markdown_report(report)


def test_detects_saving_roll_mismatch_when_attribute_exists() -> None:
    pdf = _pdf_row()
    army = _army_row()
    army["savingRolls"] = "1"
    result = compare_rows([pdf], {"tacticalbow": [army]})
    assert result["candidateDiscrepancies"] == 1
    assert result["compared"][0]["differences"] == [
        {"field": "savingRolls", "pdf": "2", "army": "1"}
    ]


def test_missing_saving_attribute_is_still_a_discrepancy() -> None:
    pdf = _pdf_row()
    army = _army_row()
    army["savingAttribute"] = "-"
    result = compare_rows([pdf], {"tacticalbow": [army]})
    assert result["candidateDiscrepancies"] == 1
    assert result["compared"][0]["differences"] == [
        {"field": "savingAttribute", "pdf": "ARM", "army": "-"},
    ]


def test_absent_values_are_equivalent_but_a_number_is_not() -> None:
    assert _value("--") == _value("-") == _value("")
    assert _value("ARM/2") == _value("arm / 2")
    assert _value(" 1 ") != _value("--")


def test_wrapped_name_is_reconstructed_within_row_boundaries() -> None:
    words = [
        (34.0, 197.8, "AP+DA"),
        (60.0, 197.8, "CC"),
        (38.0, 207.4, "WEAPON"),
        (274.0, 202.6, "8"),
        (297.0, 202.6, "1"),
        (329.0, 202.6, "AP+DA"),
        (376.0, 202.6, "ARM/2"),
        (430.0, 202.6, "2"),
        (24.0, 224.2, "AP+EXP"),
        (40.0, 233.8, "WEAPON"),
        (274.0, 229.0, "8"),
        (297.0, 229.0, "1"),
    ]
    rows = rows_from_words(words, 177)
    assert [row["name"] for row in rows] == ["AP+DA CC WEAPON", "AP+EXP WEAPON"]
    assert rows[0]["ammunition"] == "AP+DA"


def test_explicit_mode_disambiguates_repeated_weapon_name() -> None:
    source = _pdf_row("MULTI Red Fury (Anti-Materiel Mode)")
    primary = {**_army_row("MULTI Red Fury"), "mode": "Antimaterial Mode"}
    secondary = {**_army_row("MULTI Red Fury"), "mode": "Shock Mode",
                 "ammunition": "SHOCK"}
    result = compare_rows([source], {"multiredfury": [primary, secondary]})
    assert result["matchingRows"] == 1
    assert result["compared"][0]["mode"] == "Antimaterial Mode"
    assert result["compared"][0]["printedName"] == source["name"]
    assert _printed_name_and_mode("Kobra Pistol (CC Mode)") == (
        "Kobra Pistol", "CC Mode"
    )


def test_mine_plural_is_a_narrow_source_name_alias() -> None:
    result = compare_rows([_pdf_row("AP MINES")], {"apmine": [_army_row("AP Mine")]})
    assert result["matchingRows"] == 1


def test_missing_or_unknown_mode_stays_deferred() -> None:
    rows = [
        _pdf_row("MULTI Red Fury"),
        _pdf_row("MULTI Red Fury (Blast Mode)"),
    ]
    options = [
        {**_army_row("MULTI Red Fury"), "mode": "AP Mode"},
        {**_army_row("MULTI Red Fury"), "mode": "Shock Mode"},
    ]
    result = compare_rows(rows, {"multiredfury": options})
    assert result["deferredReasons"] == {
        "missing-mode-disambiguation": 1,
        "unresolved-army-mode": 1,
    }


def test_incomplete_multiline_profile_cell_is_deferred_not_mismatch() -> None:
    row = _pdf_row("Plasma Carbine (Blast Mode)")
    row["savingAttribute"] = ""
    result = compare_rows(
        [row], {"plasmacarbine": [
            {**_army_row("Plasma Carbine"), "mode": "Blast Mode"},
            {**_army_row("Plasma Carbine"), "mode": "Hit Mode"},
        ]}
    )
    assert result["candidateDiscrepancies"] == 0
    assert result["deferredReasons"] == {"incomplete-pdf-cells": 1}


def test_resolved_multimode_profile_can_report_real_field_discrepancy() -> None:
    row = _pdf_row("Kobra Pistol (CC Mode)")
    row["savingRolls"] = "1"
    army = {**_army_row("Kobra Pistol"), "mode": "CC Mode", "savingRolls": "1"}
    result = compare_rows(
        [row], {"kobrapistol": [
            {**army, "mode": "BS Mode"},
            {**army, "mode": "CC Mode", "savingRolls": "2"},
        ]}
    )
    assert result["candidateDiscrepancies"] == 1
    assert result["compared"][0]["differences"] == [
        {"field": "savingRolls", "pdf": "1", "army": "2"}
    ]
