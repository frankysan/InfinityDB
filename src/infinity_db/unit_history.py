"""Snapshot-bound, precomputed Unit history presentation for the web app."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def army_history_key(army: dict[str, Any]) -> str:
    """Identify an Army card independently of its presentation order."""
    return ":".join([str(army["id"]), *sorted(army.get("availability_flags", []))])


def load_unit_history(path: Path, army_sha256: str) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if (document.get("formatVersion") != 1
            or document.get("armyDatabaseSha256") != army_sha256
            or not isinstance(document.get("units"), dict)):
        raise ValueError("Unit history projection does not match the selected Army database")
    return document["units"]


def attach_unit_history(unit: dict[str, Any], histories: dict[str, Any]) -> None:
    """Attach only to matching current cards, keeping removed contexts separate."""
    history = histories.get(str(unit["id"]))
    if history is None:
        return
    for profile in unit.get("general_profiles", []):
        key = profile["profile_identity"]
        if key in history["general"]:
            profile["history"] = history["general"][key]
    for army in unit.get("armies", []):
        key = army_history_key(army)
        if key in history["armies"]:
            army["history"] = history["armies"][key]
    unit["historical_contexts"] = history["unmatched"]
