from __future__ import annotations

from typing import Any

from tools.audit_weapon_traits_prose import (
    _normalized_traits,
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
