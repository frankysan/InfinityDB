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
    assert SCHEMA_VERSION == 13
    assert DATABASE_COMPATIBILITY_VERSION == 18


def test_logical_unit_identity_is_frontend_derived_schema() -> None:
    assert "logical_units" not in TABLES
    assert "logical_unit_sources" not in TABLES
    assert {
        "logical_units",
        "logical_unit_sources",
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
    } == set(DERIVED_TABLES)
    assert set(DATABASE_TABLES) == set(TABLES) | set(DERIVED_TABLES)
    assert DERIVED_TABLES["logical_units"].key == ("id",)
    assert DERIVED_TABLES["logical_unit_sources"].key == ("source_unit_id",)
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
