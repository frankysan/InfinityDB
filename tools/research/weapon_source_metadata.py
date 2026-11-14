"""Read-only Army Weapon metadata for offline chart and provenance audits."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

if __package__:
    from .weapon_chart_source import WeaponChartAuditError
    from .weapon_source_common import weapon_identity as _identity
else:  # Support direct execution from tools/research/.
    from weapon_chart_source import WeaponChartAuditError
    from weapon_source_common import weapon_identity as _identity

_RANGE_EDGES_CM = (20, 40, 60, 80, 100, 120, 240)


def _source_range_bands(distance: str) -> list[str | None] | None:
    """Expand canonical Army breakpoints (2.5 cm per inch) into chart cells."""
    result: list[str | None] = [None] * 7
    if not distance:
        return result
    parsed = json.loads(distance)
    boundaries = sorted(
        (int(value["max"]), str(value["mod"]))
        for value in parsed.values() if isinstance(value, dict)
    )
    previous = 0
    for maximum, modifier in boundaries:
        if maximum not in _RANGE_EDGES_CM or maximum <= previous:
            return None
        for index, edge in enumerate(_RANGE_EDGES_CM):
            if previous < edge <= maximum:
                result[index] = modifier
        previous = maximum
    return result


def _profile_attributes(value: str) -> dict[str, int]:
    return {key: int(number) for key, number in re.findall(
        r"\b(ARM|BTS|STR|S)\s*=\s*(\d+)\b", value
    )}


def _army_options(
    name: str, metadata: dict[str, list[dict[str, Any]]]
) -> list[dict[str, Any]]:
    key = _identity(name)
    options = metadata.get(key, []) if key else []
    # The chart labels tokenized Mines in the plural; Army models the type
    # as a singular weapon. Limit this alias to a trailing "Mines" word.
    if not options and key.endswith("mines"):
        options = metadata.get(key[:-1], [])
    return options


def _metadata(db: Path) -> tuple[dict[str, list[dict[str, Any]]], int]:
    with sqlite3.connect(f"file:{db.resolve().as_posix()}?mode=ro", uri=True) as conn:
        ammunition = dict(conn.execute("SELECT id, name FROM metadata_ammunitions"))
        rows = conn.execute(
            "SELECT name, mode, ammunition, burst, damage, saving, savingNum, "
            "distance, profile FROM metadata_weapons"
        ).fetchall()
    indexed: dict[str, list[dict[str, Any]]] = {}
    for name, mode, ammo_id, burst, damage, saving, rolls, distance, profile in rows:
        if not isinstance(name, str):
            raise WeaponChartAuditError("Weapon metadata contains an invalid name")
        item = {
            "name": name,
            "mode": str(mode or ""),
            "ps": str(damage or ""),
            "burst": str(burst or ""),
            "ammunition": str(ammunition.get(ammo_id, "")),
            "savingAttribute": str(saving or ""),
            "savingRolls": str(rolls or ""),
            "rangeBands": _source_range_bands(str(distance or "")),
            "profile": str(profile or ""),
        }
        indexed.setdefault(_identity(name), []).append(item)
    return indexed, len(rows)
