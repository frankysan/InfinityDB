from __future__ import annotations

import json
import sqlite3
from decimal import Decimal, InvalidOperation
from pathlib import Path

from infinity_db.maintained_text import DISTANCE_CENTIMETERS_PER_INCH

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DATABASE = ROOT / "data" / "generated" / "infinity.db"


def _is_game_distance(value: object) -> bool:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return False
    return number >= 0 and number % DISTANCE_CENTIMETERS_PER_INCH == 0


def test_tracked_runtime_distance_storage_matches_game_conversion_contract() -> None:
    with sqlite3.connect(RUNTIME_DATABASE) as connection:
        movement_rows = connection.execute(
            "SELECT move_1, move_2 FROM profile_payloads"
        ).fetchall()
        distance_extras = connection.execute(
            "SELECT name FROM extras WHERE type = 'DISTANCE'"
        ).fetchall()
        weapon_ranges = connection.execute(
            "SELECT distance FROM metadata_weapons "
            "WHERE distance IS NOT NULL AND distance != ''"
        ).fetchall()

    assert movement_rows
    assert distance_extras
    assert weapon_ranges

    for move_1, move_2 in movement_rows:
        values = (move_1, move_2)
        if any(number < 0 for number in values):
            assert values == (-1, -1)
        else:
            assert all(_is_game_distance(value) for value in values)

    assert all(_is_game_distance(name) for (name,) in distance_extras)

    maxima: list[object] = []
    for (raw_ranges,) in weapon_ranges:
        ranges = json.loads(raw_ranges)
        for band in ranges.values():
            if isinstance(band, dict) and band.get("max") is not None:
                maxima.append(band["max"])
    assert maxima
    assert all(_is_game_distance(value) for value in maxima)
