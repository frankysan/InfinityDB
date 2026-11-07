"""Pure, source-backed deployed-object reference projection for the N5.3 pilot.

This is a *read model*, not a Unit/loadout ownership model. It consumes only the
validated audit output. No user-generated content, server storage or IDs derived
from a Unit are introduced. Do not publish this projection as exhaustive.
"""

from __future__ import annotations

import re
from typing import Any

ATTRIBUTES = ("ARM", "BTS", "STR", "S")

# Source conflicts already documented and reconciled in the pinned N5.3
# auxiliary/silhouette audits. Values here are source alternatives, not rulings.
_MINE_DISPUTES = frozenset({
    "AP Mine", "E/M Mine", "Monofilament Mine",
    "PARA Mine", "Shock Mine", "Viral Mine",
})
_SOURCE_CONFLICTS: dict[str, tuple[int, int]] = {
    **{name: (0, 181) for name in _MINE_DISPUTES},
    "Dazer": (1, 186),
    "Armed Turret": (1, 74),
}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _source_key(row: dict[str, Any]) -> tuple[str, str, str | None]:
    return (row["catalog"], row["name"], row["mode"])


def _attribute(
    value: int | str | None,
    *,
    source: dict[str, Any] | None,
    alternative: tuple[int, int] | None = None,
) -> dict[str, Any]:
    if value is None:
        return {"status": "unreported", "value": None, "provenance": []}
    if source is None:
        raise ValueError("Known attribute without provenance")
    values = [{"value": str(value), "source": source}]
    if alternative is not None:
        other, page = alternative
        if str(other) == str(value):
            raise ValueError("Identical values cannot establish a dispute")
        values.append({
            "value": str(other),
            "source": {"kind": "printed", "id": "n5-core-v5.3-pdf", "page": page},
        })
    return {
        "status": "disputed" if alternative else "known",
        "value": str(value),
        "provenance": values,
    }


def _profile_reference(row: dict[str, Any]) -> dict[str, Any]:
    source_id = row["sourceId"]
    if type(source_id) is not int or source_id <= 0:
        raise ValueError("Deployed-object profile requires an exact Army ID")
    mode = row["mode"]
    if mode is not None and not isinstance(mode, str):
        raise ValueError("Invalid deployed-object source mode")
    catalog = row["catalog"]
    if catalog not in {"weapon", "equipment"}:
        raise ValueError("Invalid deployed-object catalog")
    name = row["name"]
    suffix = f"-{_slug(mode)}" if mode else ""
    identifier = f"army-{catalog}-{source_id}{suffix}"
    values = row["attributes"]
    if not isinstance(values, dict) or set(values) != set(ATTRIBUTES):
        raise ValueError(f"Missing complete Army profile evidence: {identifier}")
    source = {
        "kind": "army", "catalog": catalog, "id": source_id,
        "mode": mode,
    }
    conflict = _SOURCE_CONFLICTS.get(name)
    if conflict and name == "Dazer" and catalog != "equipment":
        raise ValueError("Dazer conflict applied to wrong catalog")
    attrs = {
        key: _attribute(
            values[key], source=source,
            alternative=conflict if conflict and key == "S" else None,
        )
        for key in ATTRIBUTES
    }
    return {
        "id": identifier,
        "name": mode if name == "Disco Baller" and mode == "Disco Ball" else name,
        "type": "model-or-token",
        "sourceProfile": {
            "catalog": catalog, "sourceId": source_id,
            "name": name, "mode": mode, "raw": row["sourceProfile"],
        },
        "attributes": attrs,
        "originRuleId": None,
        "deliverySources": [],
    }


def _reviewed_reference(decision: dict[str, Any]) -> dict[str, Any]:
    record_id = decision["recordId"]
    name = record_id.split(":", 1)[1].replace("-", " ").title()
    category = decision["classification"]
    if category not in {
        "deployed-object-curated-trooper-profile", "deployed-scenery-s-only"
    }:
        raise ValueError(f"Not a curated deployed object: {record_id}")
    provenance = {
        "kind": "curated", "recordId": record_id,
        "sourceId": "n5-core-v5.3-pdf", "pages": decision["sourcePages"],
    }
    values = decision["knownAttributes"]
    unexpected = set(values) | set(decision["unreportedAttributes"])
    if unexpected != set(ATTRIBUTES):
        raise ValueError(f"Incomplete curated attribute states: {record_id}")
    attrs = {
        key: _attribute(
            values.get(key), source=provenance,
            alternative=(
                _SOURCE_CONFLICTS["Armed Turret"]
                if record_id == "weapon:armed-turret" and key == "S"
                else None
            ),
        )
        for key in ATTRIBUTES
    }
    if category == "deployed-scenery-s-only" and set(values) != {"S"}:
        raise ValueError("Scenery is S-only; other attributes are unreported")
    return {
        "id": f"reviewed-{_slug(record_id)}",
        "name": name,
        "type": "scenery" if category == "deployed-scenery-s-only" else "trooper-profile",
        "sourceProfile": None,
        "attributes": attrs,
        "originRuleId": record_id,
        "deliverySources": [],
    }


def project_deployed_references(report: dict[str, Any]) -> dict[str, Any]:
    """Separate reference identity, imported values and reviewed delivery paths.

    The result includes no Unit carriers. Reviewed delivery edges can be used to
    show originating catalog items, but do not establish Unit/loadout legality.
    """
    if report.get("scope") != "candidate-inventory-not-canonical-object-model":
        raise ValueError("Input is not a reviewed deployed-object inventory")
    refs = [
        _profile_reference(row)
        for row in (report["chartProfiles"] + report["additionalSourceProfiles"])
    ]
    for decision in report["reviewedCandidateDecisions"]:
        if decision["classification"] in {
            "deployed-object-curated-trooper-profile", "deployed-scenery-s-only"
        }:
            refs.append(_reviewed_reference(decision))
    by_id = {row["id"]: row for row in refs}
    if len(by_id) != len(refs):
        raise ValueError("Duplicate deployed-object identity")
    by_source = {
        (
            row["sourceProfile"]["catalog"],
            row["sourceProfile"]["name"],
            row["sourceProfile"]["mode"],
        ): row
        for row in refs if row["sourceProfile"] is not None
    }
    if len(by_source) != sum(row["sourceProfile"] is not None for row in refs):
        raise ValueError("Source modes must not merge independently")
    by_rule = {
        row["originRuleId"]: row for row in refs if row["originRuleId"] is not None
    }
    unresolved = []
    for delivery in report["reviewedDeliveryPaths"]:
        source = delivery["sourceProfileEvidence"]
        if source is None:
            # A reviewed-only object (e.g. Armed Turret) has no Army
            # four-attribute source selector. Its exact reviewed rule owner
            # can identify it; unreviewed or unspecified targets stay unresolved.
            owner = delivery["objectRulesRecordId"]
            if owner is None:
                unresolved.append({
                    "originRecordId": delivery["originRecordId"],
                    "delivery": delivery["delivery"],
                    "reason": "source-object-not-resolved",
                })
                continue
            target = by_rule.get(owner)
            if target is None:
                raise ValueError("Reviewed delivery lacks a reviewed-only object target")
        else:
            target = by_source.get(_source_key(source))
            if target is None or target["sourceProfile"]["sourceId"] != source["sourceId"]:
                raise ValueError("Reviewed delivery does not match a unique source object")
        edge = {
            "recordId": delivery["originRecordId"],
            "method": delivery["delivery"],
            "sourcePages": delivery["sourcePages"],
        }
        if edge in target["deliverySources"]:
            raise ValueError("Duplicate deployed-object delivery edge")
        target["deliverySources"].append(edge)
    return {
        "formatVersion": 1,
        "scope": "reviewed-projection-not-complete-unit-usage",
        "sourceSnapshot": {
            "armyDatabaseSha256": report["armyDatabaseSha256"],
            "curatedSourceSha256": report["curatedSourceSha256"],
        },
        "objects": sorted(refs, key=lambda row: row["id"]),
        "unresolvedDeliveries": unresolved,
    }
