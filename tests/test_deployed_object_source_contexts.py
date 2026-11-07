"""Guard the source contexts eligible for reviewed deployed-object reverse uses.

This is a structural coverage check, not a claim that every Weapon or Equipment
record represents a deployed object or legal Army-list option. New catalog
references must be classified before they can silently bypass the raw-source
to publication parity checks.
"""

from __future__ import annotations

from infinity_db.database.schema import PUBLISHED_SOURCE_TABLES, TABLES


def test_all_source_weapon_and_equipment_foreign_keys_have_reviewed_roles() -> None:
    references = {
        (name, reference.table, reference.fields)
        for name, definition in TABLES.items()
        for reference in definition.references
        if reference.table in {"weapons", "equipment"}
    }
    assert references == {
        # Whole-Army catalogs express source availability, not a Unit carrier.
        ("army_weapons", "weapons", ("item_id",)),
        ("army_equipment", "equipment", ("item_id",)),
        # Source-wide Unit options have no parent Army/group ownership.
        ("unit_option_weapons", "weapons", ("item_id",)),
        ("unit_option_equipment", "equipment", ("item_id",)),
        # Army-local profiles are direct Unit/profile contexts.
        ("profile_weapons", "weapons", ("item_id",)),
        ("profile_equipment", "equipment", ("item_id",)),
        ("option_equipment", "equipment", ("item_id",)),
        # Army-local option Weapons use reusable source templates.
        ("option_weapon_templates", "weapons", ("item_id",)),
    }
    assert any(
        reference.table == "option_weapon_templates"
        and reference.fields == ("template_id",)
        for reference in TABLES["option_weapons"].references
    )
    # Direct raw-source parity tests cover these three Unit-owning routes,
    # including the template join for option_weapons.
    assert {"unit_option_weapons", "unit_option_equipment"} <= PUBLISHED_SOURCE_TABLES


def test_include_contexts_have_explicit_parent_and_target_selectors() -> None:
    for name, parent in (
        ("profile_includes", "profiles"),
        ("option_includes", "loadout_options"),
        ("unit_option_includes", "unit_options"),
    ):
        definition = TABLES[name]
        assert {"target_group_id", "target_option_id"} <= set(definition.fields)
        assert any(reference.table == parent for reference in definition.references)

    # Unit-wide Includes cannot have an explicit source Army foreign key:
    # resolving a target Army must not assign that Army to the parent option.
    assert not any(
        reference.table == "loadout_options"
        for reference in TABLES["unit_option_includes"].references
    )
    for name in ("profile_includes", "option_includes"):
        assert any(
            reference.table == "loadout_options"
            for reference in TABLES[name].references
        )

    # Weapon metadata can contain duplicate ID/mode rows and has no source
    # Unit ownership. Profile extraction is a separate object audit.
    assert {"id", "mode", "profile"} <= set(TABLES["metadata_weapons"].fields)
    assert TABLES["metadata_weapons"].references == ()
