"""Reviewed Weapon Properties, separate from official Ammunition and Traits."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from infinity_army_data.project_resources import maintained_config_path
from infinity_db.domain_references import rule_record_public_reference
from infinity_db.rules_database import RulesDatabase

DEFAULT_PROPERTIES_PATH = maintained_config_path("catalogs", "weapon-properties.json")
_ORIGIN_KEYS = ({"domain", "role", "recordId"}, {"domain", "role", "sourceSection"})
_CANONICAL_DOMAINS = {
    "ammunition": "Ammunition",
    "trait": "Weapon Traits",
    "skill": "Skills",
    "rule": "General Rules",
    "weapon": "Weaponry",
    "state": "States",
}
_PROFILE_KEYS = {
    "weaponId", "weaponName", "mode", "ammunitionSourceId",
    "ammunition", "saving", "savingNum", "traits",
}
_PROFILE_FIELDS = (
    ("id", "weaponId"), ("name", "weaponName"),
    ("mode", "mode"), ("ammunition_source_id", "ammunitionSourceId"),
    ("ammunition", "ammunition"), ("saving", "saving"),
    ("saving_num", "savingNum"), ("traits", "traits"),
)


def load_weapon_properties(path: Path = DEFAULT_PROPERTIES_PATH) -> list[dict[str, Any]]:
    """Validate a closed source-profile mapping; never infer identity from prefixes."""
    document = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict)
        or set(document) != {"format", "version", "source", "properties"}
        or document["format"] != "InfinityDB reviewed weapon properties"
        or type(document["version"]) is not int
        or document["version"] != 1
        or document["source"] != "n5-core-v5.3"
        or not isinstance(document["properties"], list)
        or not document["properties"]
    ):
        raise ValueError("Invalid Weapon Properties configuration")
    ids: set[str] = set()
    profiles: set[tuple[str, int, str | None]] = set()
    for entry in document["properties"]:
        if (
            not isinstance(entry, dict)
            or set(entry) != {"id", "name", "summary", "origins", "profiles"}
            or not isinstance(entry["id"], str)
            or not entry["id"]
            or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in entry["id"])
            or entry["id"] in ids
            or any(not isinstance(entry[key], str) or not entry[key].strip()
                   for key in ("name", "summary"))
            or not isinstance(entry["origins"], list)
            or not entry["origins"]
            or not isinstance(entry["profiles"], list)
            or not entry["profiles"]
        ):
            raise ValueError("Invalid or duplicate Weapon Property definition")
        ids.add(entry["id"])
        origin_keys: set[tuple[str, str]] = set()
        for origin in entry["origins"]:
            if (
                not isinstance(origin, dict)
                or set(origin) not in _ORIGIN_KEYS
                or any(not isinstance(value, str) or not value.strip()
                       for value in origin.values())
            ):
                raise ValueError(f"Invalid Weapon Property origin in {entry['id']}")
            target = origin.get("recordId") or origin.get("sourceSection")
            if not isinstance(target, str):
                raise ValueError(f"Invalid Weapon Property origin in {entry['id']}")
            if "recordId" in origin and (
                ":" not in target
                or origin["domain"] != _CANONICAL_DOMAINS.get(target.split(":", 1)[0])
            ):
                raise ValueError(f"Invalid Weapon Property rules origin {target!r}")
            marker = (origin["role"], target)
            if marker in origin_keys:
                raise ValueError(f"Duplicate Weapon Property origin {marker!r}")
            origin_keys.add(marker)
        for profile in entry["profiles"]:
            if (
                not isinstance(profile, dict)
                or set(profile) != _PROFILE_KEYS
                or type(profile["weaponId"]) is not int
                or profile["weaponId"] <= 0
                or type(profile["ammunitionSourceId"]) is not int
                or profile["ammunitionSourceId"] <= 0
                or not isinstance(profile["weaponName"], str)
                or not profile["weaponName"].strip()
                or (profile["mode"] is not None
                    and (not isinstance(profile["mode"], str) or not profile["mode"].strip()))
                or any(profile[key] is not None and not isinstance(profile[key], str)
                       for key in ("ammunition", "saving", "savingNum"))
                or not isinstance(profile["traits"], list)
                or any(not isinstance(value, str) for value in profile["traits"])
            ):
                raise ValueError(f"Invalid Weapon Property profile in {entry['id']}")
            marker = (entry["id"], profile["weaponId"], profile["mode"])
            if marker in profiles:
                raise ValueError(f"Duplicate Weapon Property profile {marker!r}")
            profiles.add(marker)
    return document["properties"]


class WeaponProperties:
    """Project curated rules origins onto exact, reviewed Army source profiles."""

    def __init__(
        self, rules_database: RulesDatabase, path: Path = DEFAULT_PROPERTIES_PATH,
    ) -> None:
        self._entries: list[dict[str, Any]] = []
        self._profiles: dict[
            tuple[int, str | None], list[tuple[dict[str, Any], dict[str, Any]]]
        ] = {}
        for entry in load_weapon_properties(path):
            origins = []
            complete = True
            for origin in entry["origins"]:
                resolved = origin.copy()
                if record_id := origin.get("recordId"):
                    record = rules_database.composed_record(record_id)
                    if record is None:
                        # Synthetic/partial rules databases cannot publish broken links.
                        complete = False
                        break
                    reference = rule_record_public_reference(None, record)
                    resolved["name"] = record["name"]
                    if reference is not None:
                        resolved["public_reference"] = reference
                origins.append(resolved)
            if not complete:
                continue
            item = {
                "id": f"weapon-property:{entry['id']}",
                "name": entry["name"],
                "summary": entry["summary"],
                "origins": origins,
                "public_reference": {"href": f"/glossary#weapon-property-{entry['id']}"},
            }
            self._entries.append(item)
            for signature in entry["profiles"]:
                self._profiles.setdefault(
                    (signature["weaponId"], signature["mode"]), []
                ).append((signature, item))

    def entries(self) -> list[dict[str, Any]]:
        return deepcopy(self._entries)

    def for_profile(self, profile: dict[str, Any]) -> list[dict[str, Any]]:
        source_id = profile.get("id")
        mode = profile.get("mode")
        if type(source_id) is not int or (mode is not None and not isinstance(mode, str)):
            return []
        matches = []
        for signature, item in self._profiles.get((source_id, mode), []):
            if all(profile.get(field) == signature[expected]
                   for field, expected in _PROFILE_FIELDS):
                matches.append(item)
        return deepcopy(matches)
