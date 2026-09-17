from infinity_db.database.schema import (
    DATABASE_COMPATIBILITY_VERSION,
    SCHEMA_VERSION,
    TABLES,
)


def test_availability_semantics_are_explicit_schema_fields() -> None:
    assert "source_role" in TABLES["units"].fields
    assert "availability_kind" in TABLES["army_units"].fields
    assert SCHEMA_VERSION == 9
    assert DATABASE_COMPATIBILITY_VERSION == 11
