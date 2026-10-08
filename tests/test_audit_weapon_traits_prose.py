from __future__ import annotations

from typing import Any

import pytest

from tools.audit_weapon_traits_prose import (
    _normalized_traits,
    _review_policy,
    _reviewed_tokens,
    _trait_cell,
    _traits,
    compare_traits,
    markdown_report,
)


def _compared(name: str = "Tactical Bow") -> list[dict[str, Any]]:
    return [{"page": 176, "printedName": name, "name": name, "mode": ""}]


def test_trait_tokens_preserve_parenthesized_options_and_order_independent_identity() -> None:
    assert _traits("BIOWEAPON (DA+SHOCK), SILENT (-6).") == [
        "BIOWEAPON (DA+SHOCK)", "SILENT (-6)"
    ]
    assert _normalized_traits(["Silent (-6)", "Bioweapon (DA+SHOCK)"]) == _normalized_traits(
        ["BIOWEAPON (DA+SHOCK)", "SILENT (-6)"]
    )


def test_traits_cell_keeps_multiline_text_without_absorbing_next_row() -> None:
    words = [
        (490.0, 320.0, "BIOWEAPON"), (534.0, 320.0, "(DA+SHOCK),"),
        (500.0, 329.6, "SILENT"), (540.0, 329.6, "(-6)."),
        (494.0, 340.0, "NON-LETHAL"),
    ]
    assert _trait_cell(words, 324.8, 299.0, 345.0) == (
        "BIOWEAPON (DA+SHOCK), SILENT (-6)."
    )



def test_tall_trait_cell_includes_both_extremes_without_next_row() -> None:
    # The N5 p.181 Cybermines cell extends beyond both Burst-anchor midpoints.
    words = [
        (475.0, 298.5, "COMMS"), (503.0, 298.5, "ATTACK,"),
        (534.0, 298.5, "INTUITIVE"), (484.0, 308.1, "ATTACK,"),
        (474.0, 327.3, "STUNNED/IMMOBILIZED-B,"),
        (492.0, 356.1, "DEPLOYABLE,"), (542.0, 356.1, "[*]."),
        (466.0, 372.9, "BS"), (478.0, 372.9, "WEAPON"),
    ]
    text = _trait_cell(words, 327.3, 267.3, 382.5)
    assert text.startswith("COMMS ATTACK, INTUITIVE ATTACK,")
    assert text.endswith("DEPLOYABLE, [*].")
    assert "BS WEAPON" not in text


def test_close_trait_rows_keep_the_original_midpoint_clipping() -> None:
    words = [(485.0, 320.0, "FIRST"), (486.0, 345.0, "NEXT")]
    assert _trait_cell(words, 320.0, 299.0, 347.0) == "FIRST"

def test_matching_traits_do_not_depend_on_presentation_order() -> None:
    comparison = compare_traits(
        _compared(), {(176, "Tactical Bow"): "ANTI-MATERIEL, SILENT (-6)."},
        {("Tactical Bow", ""): ["Silent (-6)", "Anti-materiel"]},
    )
    assert comparison[0]["status"] == "traits-match"


def test_missing_trait_is_candidate_not_silently_inferred() -> None:
    comparison = compare_traits(
        _compared(), {(176, "Tactical Bow"): "ANTI-MATERIEL, SILENT (-6)."},
        {("Tactical Bow", ""): ["Anti-materiel"]},
    )
    assert comparison[0]["status"] == "candidate-discrepancy"
    assert comparison[0]["printedTraits"] == ["ANTI-MATERIEL", "SILENT (-6)"]


def test_layout_contaminated_trait_cell_is_deferred() -> None:
    comparison = compare_traits(
        _compared("Deactivator"),
        {(176, "Deactivator"): "ZONE OF CONTROL. BS WEAPON (WIP), [***]"},
        {("Deactivator", ""): ["BS Weapon (WIP)", "[***]"]},
    )
    assert comparison[0]["status"] == "deferred-source-layout"


def test_missing_source_and_ambiguous_army_metadata_fail_closed() -> None:
    assert compare_traits(_compared(), {}, {})[0]["status"] == "deferred-source"
    assert compare_traits(
        _compared(), {(176, "Tactical Bow"): ""}, {}
    )[0]["status"] == "deferred-army"


def test_report_says_inventory_not_complete_definition() -> None:
    report = {
        "corePdfSha256": "a" * 64,
        "traitRows": 1, "traitMatches": 0, "traitCandidates": 1,
        "traitDeferred": 0,
        "traits": [{"name": "Kobra Pistol", "mode": "CC Mode", "page": 182,
                    "status": "candidate-discrepancy", "printedTraits": ["CC"],
                    "armyProperties": ["CC", "Anti-materiel"]}],
        "specialWeaponSections": [{"page": 70, "section": "Armed Turret",
                                  "status": "named-weapon-definition-present"}],
        "limitations": ["A profile match is not a complete rule."],
    }
    text = markdown_report(report)
    assert "not a completeness verdict" in text
    assert "Kobra Pistol" in text
    assert "Armed Turret" in text


def test_prose_inventory_tracks_source_and_named_curated_definition(tmp_path) -> None:
    import sqlite3

    from tools.audit_weapon_traits_prose import SPECIAL_SECTIONS, prose_inventory

    database = tmp_path / "rules.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE records (kind TEXT, name TEXT)")
        connection.execute(
            "INSERT INTO records (kind, name) VALUES ('weapon', 'Armed Turret')"
        )

    class Page:
        def __init__(self, printed_page: int) -> None:
            self.printed_page = printed_page

        def search_for(self, text: str) -> list[str]:
            if self.printed_page == 70 and text == "D-Charges":
                return []
            return [text]

    # This fake supplies the 196 pages but exposes only the search contract.
    pages = [Page(i + 1) for i in range(196)]
    report = prose_inventory(pages, database)
    assert len(report) == len(SPECIAL_SECTIONS)
    by_name = {row["section"]: row for row in report}
    assert by_name["Armed Turret"]["status"] == "named-weapon-definition-present"
    assert by_name["D-Charges"]["status"] == "source-heading-unverified"
    assert by_name["Pitcher"]["status"] == "no-named-curated-weapon-definition"



def test_prose_reference_coverage_does_not_infer_family_links(tmp_path) -> None:
    import sqlite3

    from tools.audit_weapon_traits_prose import prose_reference_coverage

    army = tmp_path / "army.db"
    rules = tmp_path / "rules.db"
    with sqlite3.connect(army) as connection:
        connection.execute("CREATE TABLE metadata_weapons(name TEXT, mode TEXT)")
        connection.executemany(
            "INSERT INTO metadata_weapons VALUES (?, ?)",
            [("Armed Turret", "AP Rifle"), ("AP Mine", None)],
        )
    with sqlite3.connect(rules) as connection:
        connection.execute(
            "CREATE TABLE records(collection_id TEXT, id TEXT, kind TEXT, name TEXT)"
        )
        connection.execute(
            "CREATE TABLE record_citations(collection_id TEXT, record_id TEXT, "
            "page INTEGER, section TEXT, source_id TEXT)"
        )
        connection.execute("CREATE TABLE record_relations(collection_id TEXT, record_id TEXT)")
        connection.execute("CREATE TABLE record_army_links(collection_id TEXT, record_id TEXT)")
        connection.executemany("INSERT INTO records VALUES (?, ?, ?, ?)", [
            ("n5", "weapon:armed", "weapon", "Armed Turret"),
            ("n5", "trait:mine", "trait", "Mine"),
        ])
        connection.executemany("INSERT INTO record_citations VALUES (?, ?, ?, ?, ?)", [
            ("n5", "weapon:armed", 70, "Armed Turret Profile", "n5-core-v5.3-pdf"),
            ("n5", "trait:mine", 72, "Mine", "n5-core-v5.3-pdf"),
        ])
        connection.execute("INSERT INTO record_relations VALUES ('n5', 'weapon:armed')")
        connection.execute("INSERT INTO record_army_links VALUES ('n5', 'weapon:armed')")
    sections = [
        {"page": 70, "section": "Armed Turret", "sourcePresent": True},
        {"page": 72, "section": "Mines", "sourcePresent": True},
    ]
    covered = prose_reference_coverage(sections, army, rules)
    assert covered[0]["exactArmyWeaponProfiles"] == [
        {"name": "Armed Turret", "mode": "AP Rifle"}
    ]
    assert len(covered[0]["exactCuratedRecords"]) == 1
    assert covered[0]["sectionCitedRecordIds"] == ["n5/weapon:armed"]
    assert covered[0]["exactRecordRelationCount"] == 1
    assert covered[0]["exactRecordArmyLinkCount"] == 1
    assert covered[1]["exactArmyWeaponProfiles"] == []
    assert covered[1]["exactCuratedRecords"] == []
    assert covered[1]["sectionCitedRecordIds"] == []

def test_reviewed_notation_equivalence_does_not_hide_missing_traits(tmp_path) -> None:
    import json

    base = {
        "formatVersion": 1, "corePdfSha256": "a" * 64,
        "traitAliases": {
            "Continous Damage": "Continuous Damage",
            "State: IMM-A": "State: IMMOBILIZED-A",
        },
        "combinedFootnotes": {"NON-LETHAL [**]": ["NON-LETHAL", "[**]"]},
        "verifiedSourceCells": {},
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(base), encoding="utf-8", newline="\n")
    review = _review_policy(path, "a" * 64)
    assert _reviewed_tokens(["CONTINUOUS DAMAGE"], review) == _reviewed_tokens(
        ["Continous Damage"], review
    )
    assert _reviewed_tokens(["NON-LETHAL [**]"], review) == _reviewed_tokens(
        ["Non-lethal", "[**]"], review
    )
    result = compare_traits(
        _compared(), {(176, "Tactical Bow"): "CONTINUOUS DAMAGE"},
        {("Tactical Bow", ""): ["Continous Damage"]}, review,
    )
    assert result[0]["status"] == "notation-equivalent"
    result = compare_traits(
        _compared(), {(176, "Tactical Bow"): "CONTINUOUS DAMAGE, NON-LETHAL"},
        {("Tactical Bow", ""): ["Continous Damage"]}, review,
    )
    assert result[0]["status"] == "candidate-discrepancy"
    assert result[0]["sourceOnlyTraits"] == ["non-lethal"]
    with pytest.raises(Exception, match="not pinned"):
        _review_policy(path, "b" * 64)


def test_verified_source_cell_is_exact_page_and_printed_identity() -> None:
    review = {
        "traitAliases": {}, "combinedFootnotes": {},
        "verifiedSourceCells": {
            "186:DEACTIVATOR": ["BS WEAPON (WIP)", "[***]"],
        },
    }
    rows = [{"page": 186, "name": "Deactivator", "mode": "",
             "printedName": "DEACTIVATOR"}]
    result = compare_traits(
        rows, {(186, "DEACTIVATOR"): "ZONE OF CONTROL. BS WEAPON (WIP)"},
        {("Deactivator", ""): ["BS Weapon (WIP)", "[***]"]}, review,
    )
    assert result[0]["status"] == "source-reviewed-match"
    assert result[0]["sourceCellReviewed"] is True
    rows[0]["printedName"] = "DIFFERENT SOURCE ROW"
    assert compare_traits(rows, {}, {("Deactivator", ""): ["BS Weapon (WIP)"]}, review)[
        0
    ]["status"] == "deferred-source"


def test_reviewed_real_pdf_policy_is_valid_and_bounded() -> None:
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / (
        "config/validation/weapon-trait-source-review.json"
    )
    import json

    raw = json.loads(path.read_text(encoding="utf-8"))
    review = _review_policy(path, raw["corePdfSha256"])
    assert len(review["verifiedSourceCells"]) == 2
    assert len(review["traitAliases"]) == 5
    assert len(review["combinedFootnotes"]) == 1
