from datetime import date

import pytest

from infinity_army_data.source_version import (
    army_source_version_date,
    latest_army_source_change_date,
)


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("7.26246.158", date(2026, 9, 3)),
        ("7.26147.195", date(2026, 5, 27)),
        ("7.2668.375", date(2026, 3, 9)),
        ("7.25288.295", date(2025, 10, 15)),
    ],
)
def test_army_source_version_date_decodes_observed_datecode(
    version: str, expected: date
) -> None:
    assert army_source_version_date(version) == expected


@pytest.mark.parametrize(
    "version",
    [None, "", "test", "7.260.1", "7.26367.1", "7.26366.1.extra"],
)
def test_army_source_version_date_rejects_unknown_or_invalid_codes(version: object) -> None:
    assert army_source_version_date(version) is None


def test_latest_army_source_change_date_uses_latest_observed_date() -> None:
    assert latest_army_source_change_date(
        {"7.26246.158": 36, "7.26247.160": 22}
    ) == date(2026, 9, 4)


def test_latest_army_source_change_date_fails_closed_for_mixed_unknown_format() -> None:
    assert latest_army_source_change_date(["7.26246.158", "future-format"]) is None
