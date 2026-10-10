"""Reviewed Combined Saving Roll profiles, separate from Ammunition composition.

The N5.3 rule gives a Critical one additional ARM Saving Roll. Only exact
source-profile signatures receive that fact; no weapon notation is parsed.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from infinity_army_data.project_resources import maintained_config_path

DEFAULT_MAPPING_PATH = maintained_config_path("catalogs", "weapon-combined-saving-rolls.json")


def load_combined_saving_roll_map(
    path: Path = DEFAULT_MAPPING_PATH,
) -> dict[tuple[int, str], dict[str, Any]]:
    """Validate source identities and the reviewed, non-executable Critical fact."""
    document = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict)
        or set(document) != {"format", "version", "source", "critical", "profiles"}
        or document["format"] != "InfinityDB reviewed combined saving rolls"
        or type(document["version"]) is not int
        or document["version"] != 1
        or document["source"] != {"sourceId": "n5-core-v5.3", "page": 67}
        or not isinstance(document["critical"], dict)
        or document["critical"] != {"additionalRolls": 1, "attribute": "ARM"}
        or type(document["critical"].get("additionalRolls")) is not int
        or not isinstance(document["profiles"], list)
        or not document["profiles"]
    ):
        raise ValueError("Invalid reviewed Combined Saving Roll configuration")

    result: dict[tuple[int, str], dict[str, Any]] = {}
    for entry in document["profiles"]:
        if (
            not isinstance(entry, dict)
            or set(entry) != {
                "weaponId", "weaponName", "modes", "ammunitionSourceId",
                "ammunition", "saving", "savingNum",
            }
            or type(entry["weaponId"]) is not int
            or entry["weaponId"] <= 0
            or not isinstance(entry["weaponName"], str)
            or not entry["weaponName"].strip()
            or not isinstance(entry["modes"], list)
            or not entry["modes"]
            or any(not isinstance(mode, str) or not mode.strip() for mode in entry["modes"])
            or len(entry["modes"]) != len(set(entry["modes"]))
            or type(entry["ammunitionSourceId"]) is not int
            or entry["ammunitionSourceId"] <= 0
            or entry["ammunition"] != "N"
            or entry["saving"] != "ARM and BTS"
            or entry["savingNum"] != "1 and 1"
        ):
            raise ValueError("Invalid reviewed Combined Saving Roll profile signature")
        for mode in entry["modes"]:
            key = (entry["weaponId"], mode)
            if key in result:
                raise ValueError(f"Duplicate Combined Saving Roll profile {key!r}")
            result[key] = {**entry, "source": document["source"]}
    return result


class WeaponCombinedSavingRolls:
    """Project only exact pinned Army profile signatures onto the Weapon API."""

    def __init__(self) -> None:
        self._mapping = load_combined_saving_roll_map()

    def for_profile(self, profile: dict[str, Any]) -> dict[str, Any] | None:
        source_id = profile.get("id")
        mode = profile.get("mode")
        if type(source_id) is not int or not isinstance(mode, str):
            return None
        entry = self._mapping.get((source_id, mode))
        if entry is None or any(
            profile.get(field) != entry[expected]
            for field, expected in (
                ("name", "weaponName"),
                ("ammunition_source_id", "ammunitionSourceId"),
                ("ammunition", "ammunition"),
                ("saving", "saving"),
                ("saving_num", "savingNum"),
            )
        ):
            return None
        return deepcopy({
            "kind": "combined-saving-roll",
            "rolls": [
                {"attribute": "ARM", "count": 1},
                {"attribute": "BTS", "count": 1},
            ],
            "critical": {"additionalRolls": 1, "attribute": "ARM"},
            "source": entry["source"],
        })
