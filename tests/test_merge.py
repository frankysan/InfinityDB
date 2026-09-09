from infinity_army_data.merge import parse_source_name


def test_parse_source_name() -> None:
    assert parse_source_name("201-yu_jing.json") == (201, "yu_jing")
    assert parse_source_name("1099-reinf.json") == (1099, "reinf")


def test_parse_source_name_rejects_non_army_json() -> None:
    assert parse_source_name("schema.json") is None
    assert parse_source_name("notes.txt") is None
