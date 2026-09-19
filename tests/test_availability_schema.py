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
    assert SCHEMA_VERSION == 11
    assert DATABASE_COMPATIBILITY_VERSION == 16


def test_logical_unit_identity_is_frontend_derived_schema() -> None:
    assert "logical_units" not in TABLES
    assert "logical_unit_sources" not in TABLES
    assert set(DERIVED_TABLES) == {"logical_units", "logical_unit_sources"}
    assert set(DATABASE_TABLES) == set(TABLES) | set(DERIVED_TABLES)
    assert DERIVED_TABLES["logical_units"].key == ("id",)
    assert DERIVED_TABLES["logical_unit_sources"].key == ("source_unit_id",)
