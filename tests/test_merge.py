import json

from infinity_army_data.merge import make_source, merge_sources, parse_source_name


def test_parse_source_name() -> None:
    assert parse_source_name("201-yu_jing.json") == (201, "yu_jing")
    assert parse_source_name("1099-reinf.json") == (1099, "reinf")


def test_parse_source_name_rejects_non_army_json() -> None:
    assert parse_source_name("schema.json") is None
    assert parse_source_name("notes.txt") is None


def test_merge_records_latest_army_source_change_date() -> None:
    sources = []
    for filename, version in (
        ("101-first.json", "7.26246.158"),
        ("102-second.json", "7.26247.160"),
    ):
        source = make_source(
            filename,
            json.dumps({"version": version, "units": [], "reinforcements": None}).encode(),
        )
        assert source is not None
        sources.append(source)

    merged = merge_sources(sources)

    assert merged["_meta"]["sourceDataChangedOn"] == "2026-09-04"
