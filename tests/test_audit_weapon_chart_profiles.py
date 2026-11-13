from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from tools.audit_weapon_chart_profiles import (
    _identity as chart_weapon_identity,
)
from tools.audit_weapon_chart_profiles import (
    _metadata as legacy_weapon_metadata,
)
from tools.audit_weapon_chart_profiles import (
    _mode_identity as chart_mode_identity,
)
from tools.audit_weapon_chart_profiles import (
    _printed_name_and_mode,
    _value,
    compare_rows,
    markdown_report,
    rows_from_words,
)
from tools.audit_weapon_chart_profiles import (
    _sha256 as chart_source_sha256,
)
from tools.audit_weapon_definition_gaps import (
    _identity as gap_weapon_identity,
)
from tools.audit_weapon_definition_gaps import (
    _sha256 as gap_source_sha256,
)
from tools.weapon_chart_source import (
    PDF_PAGES,
    WeaponChartAuditError,
    _chart_burst_anchors,
)
from tools.weapon_chart_source import (
    rows_from_words as source_rows_from_words,
)
from tools.weapon_source_common import (
    printed_name_and_mode,
    source_file_sha256,
    weapon_identity,
    weapon_mode_identity,
)
from tools.weapon_source_metadata import (
    _army_options,
    _metadata,
    _profile_attributes,
    _source_range_bands,
)


def test_source_weapon_identity_shared_across_research_audits() -> None:
    for value, expected in (
        ("MULTI Rifle", "multirifle"),
        ("ＭＵＬＴＩ　Ｒｉｆｌｅ", "multirifle"),
        ("E/M Mines", "emmines"),
        ("Tactical Bow", "tacticalbow"),
    ):
        assert weapon_identity(value) == expected
        assert chart_weapon_identity(value) == expected
        assert gap_weapon_identity(value) == expected

    variants = ("Anti-Material Mode", "Anti-Materiel Mode", "Antimaterial Mode")
    assert {weapon_mode_identity(value) for value in variants} == {"antimaterielmode"}
    assert chart_mode_identity(variants[0]) == weapon_mode_identity(variants[1])
    assert weapon_mode_identity("AP Mode") != weapon_mode_identity("DA Mode")
    assert weapon_identity("Anti-Material Mode") != weapon_identity("Anti-Materiel Mode")


def test_source_file_hash_preserves_exact_bytes(tmp_path: Path) -> None:
    path = tmp_path / "source.pdf"
    content = b"PDF\x00source\r\n"
    path.write_bytes(content)
    expected = hashlib.sha256(content).hexdigest()
    assert source_file_sha256(path) == expected
    assert chart_source_sha256(path) == gap_source_sha256(path) == expected
    path.write_bytes(content.replace(b"\r\n", b"\n"))
    assert source_file_sha256(path) != expected


def test_shared_chart_source_exports_preserve_row_geometry_and_mode_names() -> None:
    assert PDF_PAGES.start == 176 and PDF_PAGES.stop == 189
    assert source_rows_from_words is rows_from_words
    words = [
        (25.0, 210.0, "TACTICAL"), (63.0, 210.0, "BOW"),
        (275.0, 210.0, "8"), (301.0, 210.0, "1"),
        (330.0, 210.0, "DA"), (380.0, 210.0, "ARM"),
        (435.0, 210.0, "2"),
    ]
    assert _chart_burst_anchors(words) == [(210.0, "1")]
    assert source_rows_from_words(words, 176) == [_pdf_row("TACTICAL BOW")]
    for name, expected in (
        ("Feuerbach (Blast Mode)", ("Feuerbach", "Blast Mode")),
        ("E/M Mine", ("E/M Mine", "")),
    ):
        assert printed_name_and_mode(name) == _printed_name_and_mode(name) == expected


def test_shared_army_metadata_lookup_stays_read_only_and_fail_closed(tmp_path: Path) -> None:
    army_db = tmp_path / "army.db"
    with sqlite3.connect(army_db) as connection:
        connection.execute("CREATE TABLE metadata_ammunitions (id INTEGER, name TEXT)")
        connection.execute(
            "CREATE TABLE metadata_weapons (name TEXT, mode TEXT, ammunition INTEGER, "
            "burst INTEGER, damage TEXT, saving TEXT, savingNum INTEGER, "
            "distance TEXT, profile TEXT)"
        )
        connection.execute("INSERT INTO metadata_ammunitions VALUES (1, 'E/M')")
        connection.execute(
            "INSERT INTO metadata_weapons VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("E/M Mine", "", 1, 1, "8", "ARM", 1,
             '{"short":{"max":20,"mod":"+6"}}', "ARM=1 BTS=0 STR=1 S=0"),
        )
    data, count = _metadata(army_db)
    assert count == 1
    assert (data, count) == legacy_weapon_metadata(army_db)
    row = _army_options("E/M Mines", data)[0]
    assert row["name"] == "E/M Mine"
    assert row["ammunition"] == "E/M"
    assert row["rangeBands"] == _source_range_bands(
        '{"short":{"max":20,"mod":"+6"}}'
    ) == ["+6", None, None, None, None, None, None]
    assert _profile_attributes(row["profile"]) == {
        "ARM": 1, "BTS": 0, "STR": 1, "S": 0,
    }
    assert _army_options("E/M Mine (AP Mode)", data) == []

    with sqlite3.connect(army_db) as connection:
        connection.execute(
            "INSERT INTO metadata_weapons VALUES (X'ff', '', 1, 1, '8', 'ARM', 1, '', '')"
        )
    with pytest.raises(WeaponChartAuditError, match="invalid name"):
        _metadata(army_db)


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


def test_early_rows_share_profile_and_trait_anchors_without_mode_leaks(monkeypatch) -> None:
    from tools import audit_weapon_traits_prose

    words = [
        (297.0, 99.0, "9"),
        (24.0, 111.8, "SUPPRESSIVE"), (64.0, 111.8, "FIRE"),
        (24.0, 121.4, "MODE"), (48.0, 121.4, "WEAPON"),
        (297.0, 116.6, "1"), (470.0, 116.6, "FIRST"),
        (24.0, 143.0, "URAGAN"), (60.0, 143.0, "MRL"),
        (24.0, 152.6, "(Blast"), (50.0, 152.6, "Mode)"),
        (297.0, 147.8, "3"), (470.0, 143.0, "BLAST"),
        (470.0, 152.6, "TEMPLATE"),
        (24.0, 174.2, "URAGAN"), (60.0, 174.2, "MRL"),
        (24.0, 183.8, "(Hit"), (45.0, 183.8, "Mode)"),
        (297.0, 179.0, "3"), (470.0, 179.0, "HIT"),
        (297.0, 800.0, "9"),
    ]
    rows = rows_from_words(words, 188)
    names = [row["name"] for row in rows]
    assert names == [
        "SUPPRESSIVE FIRE MODE WEAPON",
        "URAGAN MRL (Blast Mode)",
        "URAGAN MRL (Hit Mode)",
    ]
    assert [row["burst"] for row in rows] == ["1", "3", "3"]
    assert [_printed_name_and_mode(name) for name in names[1:]] == [
        ("URAGAN MRL", "Blast Mode"), ("URAGAN MRL", "Hit Mode")
    ]

    class Page:
        def get_text(self, kind: str) -> list[tuple[float, float, float, float, str]]:
            assert kind == "words"
            return [(x, y, x + 1, y + 1, text) for x, y, text in words]

    class Document:
        def __getitem__(self, index: int) -> Page:
            assert index == 187
            return Page()

    monkeypatch.setattr(audit_weapon_traits_prose, "PDF_PAGES", (188,))
    traits = audit_weapon_traits_prose._source_traits_by_chart_row(Document())
    assert [traits[(188, name)] for name in names] == ["FIRST", "BLAST TEMPLATE", "HIT"]


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


def test_plasma_combined_save_is_reconstructed_from_two_baselines() -> None:
    words = [
        (24.0, 455.5, "PLASMA"), (50.0, 455.5, "CARBINE"),
        (28.0, 465.1, "(Blast"), (51.0, 465.1, "Mode)"),
        (277.0, 460.3, "7"), (297.0, 460.3, "2"),
        (333.0, 460.3, "N"),
        (374.0, 455.5, "ARM"), (392.0, 455.5, "and"),
        (382.0, 465.1, "BTS"),
        (426.0, 460.3, "1"), (432.0, 460.3, "and"),
        (447.0, 460.3, "1"),
    ]
    row = rows_from_words(words, 176)[0]
    assert row["name"] == "PLASMA CARBINE (Blast Mode)"
    assert row["savingAttribute"] == "ARM and BTS"
    assert row["savingRolls"] == "1 and 1"


def test_discover_row_does_not_absorb_disco_ball_object_profile() -> None:
    words = [
        (31.0, 557.5, "DISCO"), (54.2, 557.5, "BALL"),
        (126.6, 557.5, "ARM=0"), (158.0, 557.5, "BTS=0"),
        (186.0, 557.5, "STR=1"), (214.7, 557.5, "S=1"),
        (34.0, 574.2, "DISCOVER"), (298.0, 574.2, "--"),
        (277.0, 574.2, "--"),
    ]
    assert rows_from_words(words, 186)[0]["name"] == "DISCOVER"


def test_printed_range_mods_follow_vector_slots_not_color_meaning() -> None:
    from tools.audit_weapon_chart_profiles import (
        _printed_range_bands,
        _source_range_bands,
    )

    colors = [
        ((87.736, 300.0, 139.303, 319.0), (0.49, 0.66, 0.42)),
        ((139.303, 300.0, 164.268, 319.0), (0.85, 0.33, 0.33)),
        ((164.268, 300.0, 266.993, 319.0), (0.13, 0.12, 0.13)),
    ]
    words = [
        (97.0, 305.0, "+6"),
        (122.0, 305.0, "+3"),
        (148.0, 305.0, "-6"),
    ]
    assert _printed_range_bands(words, 305.0, colors) == [
        "+6", "+3", "-6", None, None, None, None,
    ]
    assert _source_range_bands('{"short":{"max":20,"mod":"+6"},'
                               '"med":{"max":40,"mod":"+3"},'
                               '"long":{"max":60,"mod":"-6"}}') == [
        "+6", "+3", "-6", None, None, None, None,
    ]


def test_bare_range_number_remains_different_from_signed_modifier() -> None:
    from tools.audit_weapon_chart_profiles import _printed_range_bands

    bands = _printed_range_bands(
        [(96.0, 305.0, "3")],
        305.0,
        [((87.736, 300.0, 113.663, 319.0), (0.49, 0.66, 0.42))],
    )
    assert bands == ["3", None, None, None, None, None, None]
    row = _pdf_row()
    row["rangeBands"] = bands
    army = {**_army_row(), "rangeBands": ["+3", None, None, None, None, None, None]}
    result = compare_rows([row], {"tacticalbow": [army]})
    assert result["rangeCandidates"] == 1
    assert result["candidateDiscrepancies"] == 0


def test_katyusha_range_notation_review_preserves_source_values() -> None:
    """A reviewed chart glyph is not a global signed-MOD normalization."""
    from tools.audit_weapon_chart_profiles import _metadata

    root = Path(__file__).resolve().parents[1]
    review = json.loads(
        (root / "config/validation/weapon-range-source-review.json").read_text(
            encoding="utf-8"
        )
    )
    trait_review = json.loads(
        (root / "config/validation/weapon-trait-wiki-review.json").read_text(
            encoding="utf-8"
        )
    )
    assert review["formatVersion"] == 1
    assert review["corePdfSha256"] == trait_review["corePdfSha256"]
    assert review["wikiRevisionId"] == trait_review["wikiRevisionId"]
    assert review["wikiMemberSha256"] == trait_review["wikiMemberSha256"]

    (candidate,) = review["candidates"]
    assert (candidate["weaponId"], candidate["name"], candidate["mode"]) == (
        49, "Katyusha MRL", "",
    )
    assert candidate["pdfPage"] == 187
    assert candidate["pdfUnsignedLabel"] == "3"
    assert candidate["classification"] == "confirmed-pdf-sign-omission"
    assert candidate["resolvedRangeMod"] == "+3"
    # Only zero may omit its sign; the PDF's nonzero bare integer is invalid.
    assert candidate["pdfUnsignedLabel"] != "0"
    assert not candidate["pdfUnsignedLabel"].startswith(("+", "-"))
    assert candidate["resolvedRangeMod"] == f"+{candidate['pdfUnsignedLabel']}"
    assert candidate["wikiRangeBands"] == candidate["armyRangeBands"]

    metadata, _ = _metadata(root / "data/generated/army.db")
    (army,) = metadata["katyushamrl"]
    with sqlite3.connect(root / "data/generated/army.db") as connection:
        assert connection.execute(
            "SELECT id FROM metadata_weapons WHERE name=? AND mode IS NULL",
            (candidate["name"],),
        ).fetchone() == (candidate["weaponId"],)
    assert army["mode"] == candidate["mode"]
    assert army["rangeBands"] == candidate["armyRangeBands"]
    assert army["rangeBands"] == ["-3", "+3", "+3", "0", "0", "-6", None]

    # Reproduce the PDF's unsigned middle-range label as read by the
    # pinned PDF audit.  The raw difference must remain visible in reports.
    printed = {
        **_pdf_row("Katyusha MRL"),
        "page": 187,
        **{field: army[field] for field in (
            "ps", "burst", "ammunition", "savingAttribute", "savingRolls"
        )},
        "rangeBands": ["-3", "3", "3", "0", "0", "-6", None],
    }
    comparison = compare_rows([printed], {"katyushamrl": [army]})
    assert comparison["candidateDiscrepancies"] == 0
    assert comparison["rangeCandidates"] == 1
    assert comparison["rangeMatches"] == 0
    assert comparison["compared"][0]["rangeComparison"] == {
        "pdf": printed["rangeBands"],
        "army": candidate["armyRangeBands"],
        "status": "candidate-discrepancy",
    }


def test_disco_ball_is_separate_auxiliary_mode_profile() -> None:
    from tools.audit_weapon_chart_profiles import (
        _printed_auxiliary_profiles,
        compare_auxiliary_profiles,
    )

    words = [
        (31.0, 557.5, "DISCO"), (31.0, 557.5, "DISCO"),
        (54.0, 557.5, "BALL"), (54.0, 557.5, "BALL"),
        (126.0, 557.5, "ARM=0"), (157.0, 557.5, "BTS=0"),
        (186.0, 557.5, "STR=1"), (214.0, 557.5, "S=1"),
    ]
    rows = _printed_auxiliary_profiles(words, 186)
    assert len(rows) == 1
    assert rows[0]["name"] == "DISCO BALL"
    matched = compare_auxiliary_profiles(rows, {
        "discoballer": [
            {**_army_row("Disco Baller"), "mode": "", "profile": ""},
            {**_army_row("Disco Baller"), "mode": "Disco Ball",
             "profile": "ARM=0, BTS=0, STR=1, S=1"},
        ]
    })
    assert len(matched) == 1
    assert matched[0]["status"] == "fields-match"

def test_auxiliary_extractor_preserves_wrapped_object_identities() -> None:
    from tools.audit_weapon_chart_profiles import _printed_auxiliary_profiles

    words = [
        (21.6, 545.6, "MONOFILAMENT"), (38.9, 555.2, "MINES"),
        (124.4, 550.4, "ARM=0"), (158.0, 550.4, "BTS=0"),
        (193.0, 550.4, "STR=1"), (232.0, 550.4, "S=0"),
        (28.8, 495.1, "DEPLOYABLE"), (33.1, 504.7, "REPEATER"),
        (125.9, 499.9, "ARM=0"), (159.0, 499.9, "BTS=0"),
        (194.0, 499.9, "STR=1"), (230.0, 499.9, "S=1"),
    ]
    rows = _printed_auxiliary_profiles(words, 181)
    assert [row["name"] for row in rows] == [
        "DEPLOYABLE REPEATER", "MONOFILAMENT MINES",
    ]
    assert rows[1]["profile"] == "ARM=0 BTS=0 STR=1 S=0"


def test_auxiliary_object_comparison_resolves_mines_modes_and_discrepancies() -> None:
    from tools.audit_weapon_chart_profiles import compare_auxiliary_profiles

    rows = [
        {"page": 181, "name": "AP MINES",
         "profile": "ARM=0 | BTS=0 | STR=1 | S=0"},
        {"page": 181, "name": "DROP BEARS (Deployable Mode)",
         "profile": "ARM=0 | BTS=0 | STR=1 | S=0"},
        {"page": 186, "name": "DAZER",
         "profile": "ARM=0 | BTS=0 | STR=1 | S=1"},
        {"page": 186, "name": "DISCO BALL",
         "profile": "ARM=0 | BTS=0 | STR=1 | S=1"},
        {"page": 186, "name": "UNKNOWN OBJECT",
         "profile": "ARM=0 | BTS=0 | STR=1 | S=1"},
    ]
    metadata = {
        "apmine": [{**_army_row("AP Mine"), "profile": "ARM=0, BTS=0, STR=1, S=1"}],
        "dropbears": [
            {**_army_row("Drop Bears"), "mode": "BS Mode", "profile": ""},
            {**_army_row("Drop Bears"), "mode": "Deployable Mode",
             "profile": "ARM=0, BTS=0, STR=1, S=0"},
        ],
        "dazer": [{**_army_row("Dazer"), "profile": "ARM=0, BTS=0, STR=1, S=0"}],
        "discoballer": [{**_army_row("Disco Baller"), "mode": "Disco Ball",
                         "profile": "ARM=0, BTS=0, STR=1, S=1"}],
    }
    compared = compare_auxiliary_profiles(rows, metadata)
    assert [row["status"] for row in compared] == [
        "candidate-discrepancy", "fields-match", "candidate-discrepancy",
        "fields-match", "unresolved-auxiliary-identity",
    ]
    assert compared[0]["armyName"] == "AP Mine"
    assert compared[0]["differences"] == [{"field": "S", "pdf": 0, "army": 1}]
    assert compared[1]["armyMode"] == "Deployable Mode"
    assert compared[2]["differences"] == [{"field": "S", "pdf": 1, "army": 0}]
    assert compared[3]["armyName"] == "Disco Baller"
    assert compared[4]["armyName"] is None
    assert compared[4]["printedAttributes"] == {
        "ARM": 0, "BTS": 0, "STR": 1, "S": 1,
    }


def test_auxiliary_markdown_report_includes_field_provenance() -> None:
    from tools.audit_weapon_chart_profiles import compare_auxiliary_profiles

    compared = compare_auxiliary_profiles(
        [{"page": 186, "name": "DAZER",
          "profile": "ARM=0 | BTS=0 | STR=1 | S=1"}],
        {"dazer": [{**_army_row("Dazer"),
                    "profile": "ARM=0, BTS=0, STR=1, S=0"}]},
    )
    report = {
        "corePdfSha256": "abc", "armyMetadataProfiles": 1,
        "comparison": compare_rows([], {}),
        "auxiliaryProfiles": compared,
        "notCompared": [],
    }
    markdown = markdown_report(report)
    assert "attribute discrepancies: **1**" in markdown
    assert "S: PDF 1 vs Army 0" in markdown


def test_pinned_n53_pdf_chart_source_differences(
    pinned_n53_core_pdf: Path,
) -> None:
    """Compare pinned N5.3 chart rows against Army without changing review dispositions."""
    from tools.audit_weapon_chart_profiles import audit_chart

    root = Path(__file__).resolve().parents[1]
    pytest.importorskip("fitz")
    report = audit_chart(pinned_n53_core_pdf, root / "data/generated/army.db")
    assert report["corePdfSha256"] == (
        "53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f"
    )
    rows = report["comparison"]
    assert (rows["chartRowsLocated"], rows["unambiguousRowsCompared"]) == (173, 173)
    assert (rows["candidateDiscrepancies"], rows["rangeCandidates"]) == (2, 1)
    assert rows["deferredRows"] == 0
    assert len(report["auxiliaryProfiles"]) == 14
    differences = [row for row in rows["compared"] if row["differences"]]
    assert [(row["name"], row["mode"]) for row in differences] == [
        ("Kobra Pistol", "CC Mode"), ("Suppressive Fire Mode Weapon", "")
    ]
    assert differences[0]["differences"] == [
        {"field": "savingRolls", "pdf": "1", "army": "2"}
    ]
    assert differences[1]["differences"] == [
        {"field": "ammunition", "pdf": "*", "army": ""}
    ]
    uragan = {
        row["mode"]: row for row in rows["compared"] if row["name"] == "Uragan MRL"
    }
    assert set(uragan) == {"Blast Mode", "Hit Mode"}
    assert all(row["page"] == 188 and row["status"] == "fields-match"
               for row in uragan.values())
    assert all(row["rangeComparison"]["status"] == "bands-match"
               for row in uragan.values())
    katyusha = next(row for row in rows["compared"] if row["name"] == "Katyusha MRL")
    assert katyusha["rangeComparison"]["pdf"][1:3] == ["3", "3"]
    assert katyusha["rangeComparison"]["army"][1:3] == ["+3", "+3"]
    silhouette_conflicts = [
        row for row in report["auxiliaryProfiles"]
        if row["status"] == "candidate-discrepancy"
    ]
    assert {row["armyName"] for row in silhouette_conflicts} == {
        "AP Mine", "E/M Mine", "Monofilament Mine", "PARA Mine",
        "Shock Mine", "Viral Mine", "Dazer",
    }
