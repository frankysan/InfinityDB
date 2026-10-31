"""Load a prebuilt deployed-object reference publication without raw-source access."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def load_deployed_object_publication(
    path: Path,
    army_database: Path,
    rules_database: Path | None,
) -> dict[str, Any] | None:
    """Return a verified artifact or None for a not-yet-published legacy release.

    An artifact that *exists* but is invalid or belongs to different databases
    fails closed instead of silently serving stale object identities.
    """
    if not path.is_file():
        return None
    if rules_database is None:
        raise ValueError("Deployed-object publication requires a rules database")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid deployed-object publication JSON") from exc
    if (
        not isinstance(document, dict)
        or document.get("formatVersion") != 1
        or document.get("scope") != "reviewed-projection-not-complete-unit-usage"
        or not isinstance(document.get("objects"), list)
        or not isinstance(document.get("unresolvedDeliveries"), list)
    ):
        raise ValueError("Unsupported deployed-object publication")
    snapshot = document.get("sourceSnapshot")
    if not isinstance(snapshot, dict) or (
        snapshot.get("armyDatabaseSha256") != _sha256(army_database)
        or snapshot.get("rulesDatabaseSha256") != _sha256(rules_database)
    ):
        raise ValueError("Deployed-object publication does not match release databases")
    if not all(
        isinstance(snapshot.get(key), str) and len(snapshot[key]) == 64
        for key in ("curatedSourceSha256", "deliveryReviewSha256", "candidateReviewSha256")
    ):
        raise ValueError("Deployed-object publication has missing review provenance")
    identifiers: set[str] = set()
    source_keys: set[tuple[str, int, str | None]] = set()
    for entry in document["objects"]:
        if not isinstance(entry, dict):
            raise ValueError("Invalid deployed-object entry")
        identifier = entry.get("id")
        if (
            not isinstance(identifier, str) or not identifier
            or identifier in identifiers
            or not isinstance(entry.get("name"), str)
            or not isinstance(entry.get("deliverySources"), list)
        ):
            raise ValueError("Invalid/duplicate deployed-object identity")
        identifiers.add(identifier)
        source = entry.get("sourceProfile")
        if source is not None:
            if (
                not isinstance(source, dict)
                or source.get("catalog") not in {"weapon", "equipment"}
                or type(source.get("sourceId")) is not int
                or source["sourceId"] <= 0
                or (source.get("mode") is not None and not isinstance(source["mode"], str))
            ):
                raise ValueError("Invalid deployed-object Army source selector")
            key = (source["catalog"], source["sourceId"], source["mode"])
            if key in source_keys:
                raise ValueError("Duplicate deployed-object Army source selector")
            source_keys.add(key)
        attrs = entry.get("attributes")
        if not isinstance(attrs, dict) or set(attrs) != {"ARM", "BTS", "STR", "S"}:
            raise ValueError("Incomplete deployed-object attribute contract")
        for attribute in attrs.values():
            if not isinstance(attribute, dict):
                raise ValueError("Invalid deployed-object attribute")
            status = attribute.get("status")
            value = attribute.get("value")
            evidence = attribute.get("provenance")
            if (
                status not in {"known", "unreported", "disputed"}
                or not isinstance(evidence, list)
            ):
                raise ValueError("Invalid deployed-object attribute status")
            if status == "unreported":
                if value is not None or evidence:
                    raise ValueError("Unreported attribute cannot invent a value")
            elif (
                not isinstance(value, str)
                or len(evidence) != (2 if status == "disputed" else 1)
                or any(not isinstance(row, dict) or not row.get("source") for row in evidence)
            ):
                raise ValueError("Deployed-object attribute missing source provenance")
        reviewed_edges: set[tuple[str, str]] = set()
        for delivery in entry["deliverySources"]:
            if (
                not isinstance(delivery, dict)
                or not isinstance(delivery.get("recordId"), str)
                or not isinstance(delivery.get("method"), str)
                or not isinstance(delivery.get("sourcePages"), list)
            ):
                raise ValueError("Invalid reviewed delivery edge")
            reviewed_edges.add((delivery["recordId"], delivery["method"]))
        uses = entry.get("unitUses")
        if not isinstance(uses, list):
            raise ValueError("Missing or invalid deployed-object Unit usage collection")
        for use in uses:
            if (
                not isinstance(use, dict)
                or (use.get("originRecordId"), use.get("method")) not in reviewed_edges
                or use.get("kind") not in {
                    "profile", "loadout", "unit-option",
                    "profile-include", "loadout-include", "unit-option-include",
                }
                or any(type(use.get(key)) is not int for key in (
                    "unitId", "sourceItemId", "sourcePosition"
                ))
                or any(not isinstance(use.get(key), str) or not use[key]
                       for key in ("unitName", "unitSlug", "contextName"))
            ):
                raise ValueError("Invalid or unreviewed deployed-object Unit usage")
            if use["kind"] in {"unit-option", "unit-option-include"}:
                if (
                    use.get("armyId") is not None or use.get("armyName") is not None
                    or use.get("groupId") is not None
                    or use.get("profileId") is not None
                    or type(use.get("optionId")) is not int
                ):
                    raise ValueError("Unit-wide option cannot invent Army or group ownership")
                if use["kind"] == "unit-option-include" and (
                    type(use.get("includePosition")) is not int
                    or type(use.get("targetArmyId")) is not int
                    or not isinstance(use.get("targetArmyName"), str)
                    or not use["targetArmyName"]
                    or type(use.get("targetLoadoutPayloadId")) is not int
                    or not isinstance(use.get("targetName"), str)
                    or not use["targetName"]
                ):
                    raise ValueError("Invalid Unit-option Include target provenance")
            else:
                kind = use["kind"].removesuffix("-include")
                identity_key = "profileId" if kind == "profile" else "optionId"
                other_key = "optionId" if kind == "profile" else "profileId"
                if (
                    type(use.get("armyId")) is not int
                    or type(use.get("groupId")) is not int
                    or not isinstance(use.get("armyName"), str)
                    or not use["armyName"]
                    or type(use.get(identity_key)) is not int
                    or use.get(other_key) is not None
                ):
                    raise ValueError("Invalid deployed-object profile/loadout usage context")
                if use["kind"].endswith("-include") and (
                    type(use.get("includePosition")) is not int
                    or type(use.get("targetLoadoutPayloadId")) is not int
                    or not isinstance(use.get("targetName"), str)
                    or not use["targetName"]
                ):
                    raise ValueError("Invalid deployed-object Include provenance")
    return document
