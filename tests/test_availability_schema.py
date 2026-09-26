from infinity_db.database.schema import (
    DATABASE_COMPATIBILITY_VERSION,
    DATABASE_TABLES,
    DERIVED_TABLES,
    SCHEMA_VERSION,
    TABLES,
)


def test_availability_semantics_are_explicit_schema_fields() -> None:
    assert "source_role" in TABLES["units"].fields
    assert "display_army_id" in TABLES["units"].fields
    assert "availability_kind" in TABLES["army_units"].fields
    assert SCHEMA_VERSION == 25
    assert DATABASE_COMPATIBILITY_VERSION == 33


def test_logical_unit_identity_is_frontend_derived_schema() -> None:
    assert "logical_units" not in TABLES
    assert "logical_unit_sources" not in TABLES
    assert {
        "application_armies",
        "application_army_sources",
        "application_army_reinforcement_parents",
        "application_fireteam_charts",
        "application_fireteam_chart_limits",
        "application_fireteams",
        "application_fireteam_types",
        "application_fireteam_members",
        "application_fireteam_member_loadouts",
        "application_fireteam_member_equivalence_labels",
        "application_catalog_items",
        "application_catalog_sources",
        "application_domain_slugs",
        "application_hacking_programs",
        "application_hacking_program_devices",
        "application_hacking_program_targets",
        "application_hacking_program_skill_types",
        "application_martial_arts_levels",
        "application_metachemistry_results",
        "application_booty_results",
        "application_peripheral_entities",
        "application_peripheral_profiles",
        "application_peripheral_sources",
        "application_peripheral_unit_sources",
        "application_peripheral_controller_access",
        "application_peripheral_controller_targets",
        "application_unit_constraints",
        "application_unit_constraint_members",
        "application_unit_group_dependency_constraints",
        "application_unit_group_dependency_members",
        "application_unit_group_dependency_targets",
        "logical_units",
        "logical_unit_sources",
        "logical_unit_aliases",
        "logical_unit_notes",
        "logical_unit_spectables",
        "profile_payloads",
        "profile_payload_occurrences",
        "profile_payload_characteristics",
        "profile_payload_skills",
        "profile_payload_skill_extras",
        "profile_payload_equipment",
        "profile_payload_equipment_extras",
        "profile_payload_weapons",
        "profile_payload_weapon_extras",
        "loadout_payloads",
        "loadout_payload_occurrences",
        "loadout_payload_characteristics",
        "loadout_payload_orders",
        "loadout_payload_skills",
        "loadout_payload_skill_extras",
        "loadout_payload_equipment",
        "loadout_payload_equipment_extras",
        "loadout_payload_weapons",
        "loadout_payload_weapon_extras",
        "profile_occurrence_includes",
        "loadout_occurrence_includes",
        "unit_option_include_targets",
    } == set(DERIVED_TABLES)
    assert set(DATABASE_TABLES) == set(TABLES) | set(DERIVED_TABLES)
    assert DERIVED_TABLES["application_armies"].key == ("id",)
    assert DERIVED_TABLES["application_army_sources"].key == (
        "application_army_id",
        "source_army_id",
    )
    assert DERIVED_TABLES["application_army_reinforcement_parents"].key == (
        "reinforcement_army_id",
        "parent_army_id",
    )
    assert DERIVED_TABLES["application_fireteam_charts"].key == ("application_army_id",)
    assert DERIVED_TABLES["application_fireteam_chart_limits"].key == (
        "application_army_id",
        "fireteam_type",
    )
    assert DERIVED_TABLES["application_fireteams"].key == (
        "application_army_id",
        "fireteam_id",
    )
    assert DERIVED_TABLES["application_fireteam_members"].key == (
        "application_army_id",
        "fireteam_id",
        "member_id",
    )
    assert DERIVED_TABLES["application_catalog_items"].key == ("catalog", "id")
    assert DERIVED_TABLES["application_catalog_sources"].key == (
        "catalog",
        "application_item_id",
        "source_item_id",
    )
    assert DERIVED_TABLES["application_domain_slugs"].key == (
        "domain",
        "application_id",
    )
    assert DERIVED_TABLES["logical_units"].key == ("id",)
    assert DERIVED_TABLES["logical_unit_sources"].key == ("source_unit_id",)
    assert DERIVED_TABLES["logical_unit_aliases"].key == (
        "logical_unit_id",
        "source_unit_id",
        "field",
    )
    assert DERIVED_TABLES["logical_unit_notes"].key == (
        "logical_unit_id",
        "source_unit_id",
    )
    assert DERIVED_TABLES["logical_unit_spectables"].key == (
        "logical_unit_id",
        "source_unit_id",
    )
    assert DERIVED_TABLES["profile_payloads"].key == ("id",)
    assert DERIVED_TABLES["profile_payload_occurrences"].key == (
        "army_id",
        "unit_id",
        "group_id",
        "profile_id",
    )
    assert DERIVED_TABLES["loadout_payloads"].key == ("id",)
    assert DERIVED_TABLES["loadout_payload_occurrences"].key == (
        "army_id",
        "unit_id",
        "group_id",
        "option_id",
    )


def test_include_relationships_are_frontend_derived_schema() -> None:
    assert DERIVED_TABLES["profile_occurrence_includes"].key == (
        "army_id",
        "unit_id",
        "group_id",
        "profile_id",
        "position",
    )
    assert DERIVED_TABLES["loadout_occurrence_includes"].key == (
        "army_id",
        "unit_id",
        "group_id",
        "option_id",
        "position",
    )
    assert DERIVED_TABLES["unit_option_include_targets"].key == (
        "unit_id",
        "option_id",
        "position",
        "target_army_id",
    )
