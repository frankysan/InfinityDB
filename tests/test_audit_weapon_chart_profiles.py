from __future__ import annotations

from tools.audit_weapon_chart_profiles import (
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


def test_detects_source_discrepancy_without_rewriting_either_value() -> None:
    pdf = _pdf_row("Mine Dispenser")
    pdf["savingRolls"] = "--"
    army = _army_row("Mine Dispenser")
    army["savingRolls"] = "1"
    result = compare_rows([pdf], {"minedispenser": [army]})
    assert result["candidateDiscrepancies"] == 1
    assert result["compared"][0]["differences"] == [
        {"field": "savingRolls", "pdf": "--", "army": "1"}
    ]
    report = {
        "corePdfSha256": "abc", "armyMetadataProfiles": 1,
        "comparison": result, "notCompared": ["range bands"],
    }
    assert "Mine Dispenser" in markdown_report(report)
    assert army["savingRolls"] == "1"


def test_absent_values_are_equivalent_but_a_number_is_not() -> None:
    assert _value("--") == _value("-") == _value("")
    assert _value("ARM/2") == _value("arm / 2")
    assert _value(" 1 ") != _value("--")


def test_multimode_and_wrapped_names_are_deferred_not_guessed() -> None:
    first = _pdf_row("")
    second = _pdf_row("MULTI Red Fury")
    result = compare_rows(
        [first, second],
        {"multiredfury": [
            _army_row("MULTI Red Fury"),
            {**_army_row("MULTI Red Fury"), "mode": "Shock Mode"},
        ]},
    )
    assert result["unambiguousRowsCompared"] == 0
    assert result["deferredRows"] == 2
    assert result["deferredReasons"] == {
        "multiple-army-modes": 1,
        "no-exact-single-line-name": 1,
    }
