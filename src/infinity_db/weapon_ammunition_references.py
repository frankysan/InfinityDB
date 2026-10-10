"""Reviewed Army ammunition identities projected as player-facing rules links.

This is a navigation projection, not an ammunition-effects or Saving Roll parser.
Only exact source metadata IDs/names in the maintained map receive links.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from infinity_army_data.project_resources import maintained_config_path
from infinity_db.domain_references import rule_record_public_reference
from infinity_db.rules_database import RulesDatabase

DEFAULT_MAPPING_PATH = maintained_config_path("catalogs", "weapon-ammunition-references.json")


def load_ammunition_reference_map(
    path: Path = DEFAULT_MAPPING_PATH,
) -> dict[int, dict[str, Any]]:
    """Validate a closed, explicit map without parsing source ammunition notation."""
    document = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict)
        or document.get("format") != "InfinityDB weapon ammunition references"
        or document.get("version") != 2
        or set(document) != {"format", "version", "sourceEntries"}
    ):
        raise ValueError("Unsupported weapon ammunition reference config")
    entries = document["sourceEntries"]
    if not isinstance(entries, dict) or not entries:
        raise ValueError("Weapon ammunition reference config requires sourceEntries")
    mapping: dict[int, dict[str, Any]] = {}
    for source_id, entry in entries.items():
        if (
            not isinstance(source_id, str)
            or not source_id.isdecimal()
            or str(int(source_id)) != source_id
        ):
            raise ValueError(f"Invalid source ammunition ID {source_id!r}")
        if not isinstance(entry, dict) or set(entry) not in (
            {"name", "segments"}, {"name", "segments", "components"}
        ):
            raise ValueError(f"Invalid source ammunition entry {source_id}")
        name, segments = entry["name"], entry["segments"]
        if not isinstance(name, str) or not name.strip() or not isinstance(segments, list):
            raise ValueError(f"Invalid ammunition name/segments at {source_id}")
        if not segments:
            raise ValueError(f"Missing ammunition segments at {source_id}")
        collected: list[str] = []
        link_count = 0
        for segment in segments:
            if not isinstance(segment, dict) or set(segment) not in (
                {"text"}, {"text", "ruleId"}
            ):
                raise ValueError(f"Invalid ammunition segment at {source_id}")
            segment_text = segment["text"]
            if not isinstance(segment_text, str) or not segment_text:
                raise ValueError(f"Empty ammunition segment at {source_id}")
            collected.append(segment_text)
            if "ruleId" in segment:
                rule_id = segment["ruleId"]
                if (
                    not isinstance(rule_id, str)
                    or not rule_id.startswith("ammunition:")
                    or len(rule_id) <= len("ammunition:")
                ):
                    raise ValueError(f"Invalid ammunition target at {source_id}")
                link_count += 1
        if "".join(collected) != name or not link_count:
            raise ValueError(f"Ammunition segments must reproduce source name {name!r}")
        components = entry.get("components")
        if components is not None:
            if (
                not isinstance(components, list)
                or len(components) < 2
                or any(not isinstance(rule_id, str) for rule_id in components)
                or len(set(components)) != len(components)
                or len(segments) != 2 * len(components) - 1
                or any(
                    segments[index] != {"text": "+"}
                    for index in range(1, len(segments), 2)
                )
                or [segment.get("ruleId") for segment in segments[::2]] != components
            ):
                raise ValueError(
                    f"Combined ammunition {name!r} needs ordered, linked components"
                )
        elif link_count != 1 or len(segments) != 1:
            raise ValueError(
                f"Ammunition {name!r} needs an explicit combined components list"
            )
        mapping[int(source_id)] = entry
    return mapping


class WeaponAmmunitionReferences:
    """Resolve approved metadata ammunition references against the published rules DB."""

    def __init__(self, rules_database: RulesDatabase) -> None:
        self._mapping = load_ammunition_reference_map()
        self._resolved: dict[int, list[dict[str, Any]]] = {}
        self._compositions: dict[int, dict[str, Any]] = {}
        for source_id, entry in self._mapping.items():
            segments = []
            for segment in entry["segments"]:
                result: dict[str, Any] = {"text": segment["text"]}
                if rule_id := segment.get("ruleId"):
                    record = rules_database.composed_record(rule_id)
                    if record is None:
                        # Synthetic/partial rules databases may not publish every
                        # base type. Do not create dangling links in that case.
                        segments = []
                        break
                    if record["kind"] != "ammunition":
                        raise ValueError(f"Invalid curated Ammunition target {rule_id!r}")
                    reference = rule_record_public_reference(None, record)
                    if reference is None:
                        raise ValueError(f"Ammunition target lacks public route {rule_id!r}")
                    result["public_reference"] = reference
                segments.append(result)
            if segments:
                self._resolved[source_id] = segments
                if "components" in entry:
                    component_segments = segments[::2]
                    self._compositions[source_id] = {
                        "kind": "combined",
                        "components": [
                            {
                                "record_id": rule_id,
                                "public_reference": segment["public_reference"],
                            }
                            for rule_id, segment in zip(
                                entry["components"], component_segments, strict=True
                            )
                        ],
                    }

    def _matched_id(self, profile: dict[str, Any]) -> int | None:
        """Only reviewed Army ID/name pairs can carry semantic references."""
        source_id = profile.get("ammunition_source_id")
        if type(source_id) is not int:
            return None
        entry = self._mapping.get(source_id)
        if (
            entry is None
            or source_id not in self._resolved
            or profile.get("ammunition") != entry["name"]
        ):
            return None
        return source_id

    def for_profile(self, profile: dict[str, Any]) -> list[dict[str, Any]] | None:
        """Return player-facing reference spans for an exact source identity."""
        source_id = self._matched_id(profile)
        if source_id is None:
            return None
        return [segment.copy() for segment in self._resolved[source_id]]

    def composition_for_profile(self, profile: dict[str, Any]) -> dict[str, Any] | None:
        """Return explicitly reviewed composition, never derived from display syntax."""
        source_id = self._matched_id(profile)
        if source_id is None:
            return None
        composition = self._compositions.get(source_id)
        if composition is None:
            return None
        return deepcopy(composition)
