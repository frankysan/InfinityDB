"""Coverage checks for reviewed Army-local Peripheral identity mappings."""

from __future__ import annotations

import json
import sqlite3
import unicodedata
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .peripheral_identities import PeripheralIdentityCurated, PeripheralIdentityError

COVERAGE_FORMAT = "InfinityDB Peripheral identity coverage"
COVERAGE_FORMAT_VERSION = 3

_CONTROLLER_GRAPH_TABLES = frozenset(
    {
        "units",
        "profiles",
        "loadout_options",
        "profile_peripherals",
        "option_peripherals",
        "profile_skills",
        "option_skills",
        "skills",
        "application_catalog_sources",
        "application_domain_slugs",
    }
)


def _normalized_review_name(value: str) -> str:
    """Normalize names only for deterministic review grouping, never identity."""
    return " ".join(unicodedata.normalize("NFC", value).split()).casefold()


def _table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }


def _require_peripheral_schema(connection: sqlite3.Connection) -> None:
    tables = _table_names(connection)
    for table in ("__infinity_metadata", "peripherals"):
        if table not in tables:
            raise PeripheralIdentityError(
                f"Peripheral identity coverage requires table {table!r}"
            )
    columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(peripherals)").fetchall()
    }
    required = {"army_id", "id", "name", "mercs"}
    missing = sorted(required - columns)
    if missing:
        raise PeripheralIdentityError(
            "Peripheral identity coverage peripherals table is missing column(s): "
            + ", ".join(missing)
        )


def _database_snapshot_sha256(connection: sqlite3.Connection) -> str:
    row = connection.execute(
        'SELECT value FROM "__infinity_metadata" WHERE key = ?', ("_meta",)
    ).fetchone()
    try:
        metadata = json.loads(row[0]) if row is not None else None
    except (json.JSONDecodeError, TypeError) as exc:
        raise PeripheralIdentityError(
            f"Could not read Peripheral identity coverage database provenance: {exc}"
        ) from exc
    value = metadata.get("snapshotArchiveSha256") if isinstance(metadata, dict) else None
    if not isinstance(value, str) or len(value) != 64:
        raise PeripheralIdentityError(
            "Peripheral identity coverage database has no valid snapshotArchiveSha256"
        )
    return value.lower()


def _source_for_snapshot(document: dict[str, Any], snapshot_sha256: str) -> dict[str, Any]:
    sources = document.get("sources")
    if not isinstance(sources, list):
        raise PeripheralIdentityError("Peripheral identity curated sources are unavailable")
    matches = [
        source
        for source in sources
        if isinstance(source, dict)
        and isinstance(source.get("sha256"), str)
        and source["sha256"].lower() == snapshot_sha256
    ]
    if len(matches) != 1:
        raise PeripheralIdentityError(
            "Peripheral identity curated data must declare exactly one source matching "
            f"database snapshot {snapshot_sha256}"
        )
    return matches[0]


def _army_skill_slug_by_rule_id(
    rules_documents: Iterable[tuple[Path, dict[str, Any]]] | None,
) -> tuple[dict[str, str], dict[str, Any]]:
    if rules_documents is None:
        return {}, {}
    records: dict[str, dict[str, Any]] = {}
    for _path, document in rules_documents:
        for record in document.get("records", []):
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                records[record["id"]] = record

    skill_slugs: dict[str, str] = {}
    for record_id, record in records.items():
        if record.get("kind") != "skill":
            continue
        links = record.get("armyLinks")
        if not isinstance(links, list):
            continue
        slugs = {
            link.get("id")
            for link in links
            if isinstance(link, dict)
            and link.get("entity") == "skill"
            and isinstance(link.get("id"), str)
        }
        if len(slugs) == 1:
            skill_slugs[record_id] = str(next(iter(slugs)))

    predicates: dict[str, Any] = {}
    for record_id, record in records.items():
        facts = record.get("facts")
        if not isinstance(facts, dict) or facts.get("category") != "peripheral-type":
            continue
        eligibility = facts.get("controllerEligibility")
        if isinstance(eligibility, dict) and eligibility.get("status") != "not-stated":
            predicates[record_id] = eligibility
    return skill_slugs, predicates


def _evaluate_rule_eligibility(
    expression: Any,
    skill_slugs: set[str],
    army_skill_slug_by_rule_id: Mapping[str, str],
) -> bool | None:
    if not isinstance(expression, dict):
        return None
    if "hasSkill" in expression:
        required = army_skill_slug_by_rule_id.get(str(expression["hasSkill"]))
        return required in skill_slugs if required is not None else None
    if "anyOf" in expression:
        children = expression["anyOf"]
        if not isinstance(children, list):
            return None
        values = [
            _evaluate_rule_eligibility(child, skill_slugs, army_skill_slug_by_rule_id)
            for child in children
        ]
        if any(value is True for value in values):
            return True
        if all(value is False for value in values):
            return False
        return None
    if "allOf" in expression:
        children = expression["allOf"]
        if not isinstance(children, list):
            return None
        values = [
            _evaluate_rule_eligibility(child, skill_slugs, army_skill_slug_by_rule_id)
            for child in children
        ]
        if any(value is False for value in values):
            return False
        if all(value is True for value in values):
            return True
        return None
    return None


def _army_list_presentation_by_definition(
    connection: sqlite3.Connection,
    definitions: Mapping[tuple[int, int], dict[str, Any]],
    *,
    include_details: bool,
) -> dict[tuple[int, int], dict[str, Any]]:
    """Report same-Army profile-group exposure without treating names as identity.

    A selectable matching profile/loadout is positive review evidence for Cyberplug
    because Cyberplug Peripherals can be exposed alongside ordinary Army-list units.
    Disabled-only embedded groups are deliberately kept separate because Army also
    uses those to carry otherwise non-selectable Peripheral profiles.
    """
    groups: dict[tuple[int, int, int], dict[str, Any]] = {}
    unit_names = {
        int(row["id"]): str(row["name"])
        for row in connection.execute("SELECT id, name FROM units")
    }

    for row in connection.execute(
        "SELECT army_id, unit_id, group_id, profile_id, name FROM profiles "
        "ORDER BY army_id, unit_id, group_id, profile_id"
    ):
        key = (int(row["army_id"]), int(row["unit_id"]), int(row["group_id"]))
        group = groups.setdefault(
            key,
            {
                "armyId": key[0],
                "unitId": key[1],
                "unitName": unit_names.get(key[1]),
                "groupId": key[2],
                "profileNames": [],
                "loadoutOptions": [],
            },
        )
        name = str(row["name"] or "")
        if name:
            group["profileNames"].append(name)

    for row in connection.execute(
        "SELECT army_id, unit_id, group_id, option_id, name, disabled "
        "FROM loadout_options ORDER BY army_id, unit_id, group_id, option_id"
    ):
        key = (int(row["army_id"]), int(row["unit_id"]), int(row["group_id"]))
        group = groups.setdefault(
            key,
            {
                "armyId": key[0],
                "unitId": key[1],
                "unitName": unit_names.get(key[1]),
                "groupId": key[2],
                "profileNames": [],
                "loadoutOptions": [],
            },
        )
        group["loadoutOptions"].append(
            {
                "optionId": int(row["option_id"]),
                "name": str(row["name"] or ""),
                "disabled": bool(row["disabled"]),
            }
        )

    by_army: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for group in groups.values():
        by_army[int(group["armyId"])].append(group)

    result: dict[tuple[int, int], dict[str, Any]] = {}
    for key, definition in sorted(definitions.items()):
        target = _normalized_review_name(str(definition["sourceName"]))
        matches: list[dict[str, Any]] = []
        for group in by_army.get(key[0], []):
            profile_matches = sorted(
                name
                for name in group["profileNames"]
                if _normalized_review_name(name) == target
            )
            option_matches = [
                option
                for option in group["loadoutOptions"]
                if option["name"] and _normalized_review_name(option["name"]) == target
            ]
            if not profile_matches and not option_matches:
                continue
            selectable = any(
                not option["disabled"] for option in group["loadoutOptions"]
            )
            match = {
                "unitId": group["unitId"],
                "unitName": group["unitName"],
                "groupId": group["groupId"],
                "selectable": selectable,
                "profileNameMatch": bool(profile_matches),
                "loadoutNameMatch": bool(option_matches),
            }
            if include_details:
                match["matchingProfileNames"] = profile_matches
                match["matchingLoadoutOptions"] = option_matches
                match["groupSelectableOptionCount"] = sum(
                    1 for option in group["loadoutOptions"] if not option["disabled"]
                )
            matches.append(match)

        if any(match["selectable"] for match in matches):
            status = "selectable"
        elif matches:
            status = "embedded-disabled"
        else:
            status = "not-matched"
        result[key] = {
            "status": status,
            "matchingGroupCount": len(matches),
            "selectableGroupCount": sum(1 for match in matches if match["selectable"]),
        }
        if include_details:
            result[key]["matches"] = matches
    return result


def _controller_skill_maps(connection: sqlite3.Connection) -> tuple[
    dict[tuple[int, int, int, int], set[str]],
    dict[tuple[int, int, int, int], set[str]],
    dict[tuple[int, int, int], list[set[str]]],
    dict[int, str],
]:
    source_skill_slug = {
        int(row["source_item_id"]): str(row["slug"])
        for row in connection.execute(
            "SELECT acs.source_item_id, ads.slug "
            "FROM application_catalog_sources AS acs "
            "JOIN application_domain_slugs AS ads "
            "ON ads.domain = 'skills' AND ads.application_id = acs.application_item_id "
            "WHERE acs.catalog = 'skills' AND ads.status = 'resolved' AND ads.slug IS NOT NULL"
        )
    }
    skill_names = {
        int(row["id"]): str(row["name"])
        for row in connection.execute("SELECT id, name FROM skills")
    }

    profile_skills: dict[tuple[int, int, int, int], set[str]] = defaultdict(set)
    for row in connection.execute(
        "SELECT army_id, unit_id, group_id, profile_id, item_id FROM profile_skills"
    ):
        slug = source_skill_slug.get(int(row["item_id"]))
        if slug is not None:
            profile_key = (
                int(row["army_id"]),
                int(row["unit_id"]),
                int(row["group_id"]),
                int(row["profile_id"]),
            )
            profile_skills[profile_key].add(slug)

    option_skills: dict[tuple[int, int, int, int], set[str]] = defaultdict(set)
    for row in connection.execute(
        "SELECT army_id, unit_id, group_id, option_id, item_id FROM option_skills"
    ):
        slug = source_skill_slug.get(int(row["item_id"]))
        if slug is not None:
            option_key = (
                int(row["army_id"]),
                int(row["unit_id"]),
                int(row["group_id"]),
                int(row["option_id"]),
            )
            option_skills[option_key].add(slug)

    group_profile_skill_sets: dict[tuple[int, int, int], list[set[str]]] = defaultdict(list)
    profile_rows = connection.execute(
        "SELECT army_id, unit_id, group_id, profile_id FROM profiles "
        "ORDER BY army_id, unit_id, group_id, profile_id"
    )
    for row in profile_rows:
        key = (int(row["army_id"]), int(row["unit_id"]), int(row["group_id"]))
        profile_key = (*key, int(row["profile_id"]))
        group_profile_skill_sets[key].append(set(profile_skills.get(profile_key, set())))

    return profile_skills, option_skills, group_profile_skill_sets, skill_names


def _audit_controller_graph(
    connection: sqlite3.Connection,
    definitions: Mapping[tuple[int, int], dict[str, Any]],
    *,
    rules_documents: Iterable[tuple[Path, dict[str, Any]]] | None,
    include_details: bool,
) -> tuple[dict[str, Any], dict[tuple[int, int], dict[str, Any]]]:
    missing_tables = sorted(_CONTROLLER_GRAPH_TABLES - _table_names(connection))
    if missing_tables:
        return (
            {
                "status": "unavailable",
                "missingTables": missing_tables,
                "reason": (
                    "Controller evidence requires the normalized relationship/catalog tables."
                ),
            },
            {},
        )

    rule_skill_slugs, type_predicates = _army_skill_slug_by_rule_id(rules_documents)
    profile_skills, option_skills, group_profile_skill_sets, _skill_names = _controller_skill_maps(
        connection
    )
    unit_names = {
        int(row["id"]): str(row["name"])
        for row in connection.execute("SELECT id, name FROM units")
    }
    profile_names = {
        (
            int(row["army_id"]),
            int(row["unit_id"]),
            int(row["group_id"]),
            int(row["profile_id"]),
        ): str(row["name"] or "")
        for row in connection.execute(
            "SELECT army_id, unit_id, group_id, profile_id, name FROM profiles"
        )
    }
    option_names = {
        (
            int(row["army_id"]),
            int(row["unit_id"]),
            int(row["group_id"]),
            int(row["option_id"]),
        ): str(row["name"] or "")
        for row in connection.execute(
            "SELECT army_id, unit_id, group_id, option_id, name FROM loadout_options"
        )
    }

    army_list_presentation = _army_list_presentation_by_definition(
        connection, definitions, include_details=include_details
    )

    attachment_evidence: list[dict[str, Any]] = []
    controllers: dict[tuple[str, int, int, int, int], dict[str, Any]] = {}
    definition_attachments: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)

    def add_attachment(kind: str, row: sqlite3.Row) -> None:
        army_id = int(row["army_id"])
        unit_id = int(row["unit_id"])
        group_id = int(row["group_id"])
        parent_field = "profile_id" if kind == "profile" else "option_id"
        parent_id = int(row[parent_field])
        definition_key = (army_id, int(row["item_id"]))
        definition = definitions.get(definition_key)
        parent_key = (army_id, unit_id, group_id, parent_id)
        if kind == "profile":
            candidate_skill_sets = [set(profile_skills.get(parent_key, set()))]
            direct_skill_slugs = sorted(candidate_skill_sets[0])
            controller_name = profile_names.get(parent_key, "")
        else:
            direct = set(option_skills.get(parent_key, set()))
            profile_sets = group_profile_skill_sets.get((army_id, unit_id, group_id), [])
            candidate_skill_sets = [
                direct | profile_set for profile_set in profile_sets
            ] or [direct]
            direct_skill_slugs = sorted(direct)
            controller_name = option_names.get(parent_key, "")

        type_evidence: dict[str, str] = {}
        for type_id, predicate in sorted(type_predicates.items()):
            values = [
                _evaluate_rule_eligibility(predicate, skills, rule_skill_slugs)
                for skills in candidate_skill_sets
            ]
            known = [value for value in values if value is not None]
            if not known:
                status = "unknown"
            elif all(value is True for value in known) and len(known) == len(values):
                status = "consistent"
            elif all(value is False for value in known) and len(known) == len(values):
                status = "inconsistent"
            else:
                status = "ambiguous"
            type_evidence[type_id] = status

        evidence = {
            "controllerKind": kind,
            "armyId": army_id,
            "unitId": unit_id,
            "unitName": unit_names.get(unit_id),
            "groupId": group_id,
            "parentId": parent_id,
            "controllerName": controller_name,
            "peripheralId": int(row["item_id"]),
            "peripheralName": definition.get("sourceName") if definition is not None else None,
            "quantity": row["quantity"],
            "directSkillSlugs": direct_skill_slugs,
            "candidateEffectiveSkillSets": [sorted(skills) for skills in candidate_skill_sets],
            "typeEligibility": type_evidence,
        }
        attachment_evidence.append(evidence)
        definition_attachments[definition_key].append(evidence)
        controller_key = (kind, army_id, unit_id, group_id, parent_id)
        controller = controllers.setdefault(
            controller_key,
            {
                "controllerKind": kind,
                "armyId": army_id,
                "unitId": unit_id,
                "unitName": unit_names.get(unit_id),
                "groupId": group_id,
                "parentId": parent_id,
                "controllerName": controller_name,
                "directSkillSlugs": direct_skill_slugs,
                "candidateEffectiveSkillSets": [sorted(skills) for skills in candidate_skill_sets],
                "peripherals": [],
            },
        )
        controller["peripherals"].append(
            {
                "peripheralId": int(row["item_id"]),
                "peripheralName": definition.get("sourceName") if definition is not None else None,
                "quantity": row["quantity"],
            }
        )

    for row in connection.execute(
        "SELECT army_id, unit_id, group_id, profile_id, item_id, quantity "
        "FROM profile_peripherals ORDER BY army_id, unit_id, group_id, profile_id, position"
    ):
        add_attachment("profile", row)
    for row in connection.execute(
        "SELECT army_id, unit_id, group_id, option_id, item_id, quantity "
        "FROM option_peripherals ORDER BY army_id, unit_id, group_id, option_id, position"
    ):
        add_attachment("loadout", row)

    definition_evidence: dict[tuple[int, int], dict[str, Any]] = {}
    for key, definition in sorted(definitions.items()):
        attachments = definition_attachments.get(key, [])
        type_summary: dict[str, dict[str, int]] = {}
        for type_id in sorted(type_predicates):
            counts = {"consistent": 0, "inconsistent": 0, "ambiguous": 0, "unknown": 0}
            for evidence in attachments:
                counts[evidence["typeEligibility"].get(type_id, "unknown")] += 1
            type_summary[type_id] = counts
        definition_evidence[key] = {
            "armyId": key[0],
            "peripheralId": key[1],
            "sourceName": definition["sourceName"],
            "attachmentCount": len(attachments),
            "controllerCount": len(
                {
                    (
                        item["controllerKind"],
                        item["armyId"],
                        item["unitId"],
                        item["groupId"],
                        item["parentId"],
                    )
                    for item in attachments
                }
            ),
            "typeEligibility": type_summary,
            "armyListPresentation": army_list_presentation.get(
                key,
                {"status": "not-matched", "matchingGroupCount": 0, "selectableGroupCount": 0},
            ),
        }
        if include_details:
            definition_evidence[key]["controllers"] = attachments

    report: dict[str, Any] = {
        "status": "available",
        "attachmentCount": len(attachment_evidence),
        "controllerCount": len(controllers),
        "attachedDefinitionCount": sum(
            1 for value in definition_evidence.values() if value["attachmentCount"]
        ),
        "definitionOnlyCount": sum(
            1 for value in definition_evidence.values() if not value["attachmentCount"]
        ),
        "evaluableTypeIds": sorted(type_predicates),
        "armyListPresentation": {
            "selectableDefinitionCount": sum(
                1
                for value in army_list_presentation.values()
                if value["status"] == "selectable"
            ),
            "embeddedDisabledDefinitionCount": sum(
                1
                for value in army_list_presentation.values()
                if value["status"] == "embedded-disabled"
            ),
            "notMatchedDefinitionCount": sum(
                1
                for value in army_list_presentation.values()
                if value["status"] == "not-matched"
            ),
            "interpretation": (
                "A same-Army matching profile group with at least one enabled/selectable loadout "
                "is strong structural evidence to review the definition as Peripheral (Cyberplug). "
                "Disabled-only embedded profile groups are used for other Peripheral types too and "
                "are not Cyberplug evidence. Absence of selectable exposure does not rule "
                "Cyberplug out."
            ),
        },
        "interpretation": (
            "Controller eligibility is a necessary-condition check only. A 'consistent' result "
            "supports review for that type but does not establish Peripheral type identity. "
            "Core types whose controller eligibility is not stated are intentionally not evaluated."
        ),
        "definitionEvidence": [definition_evidence[key] for key in sorted(definition_evidence)],
    }
    if include_details:
        report["controllerToPeripherals"] = [
            {
                **controllers[key],
                "peripherals": sorted(
                    controllers[key]["peripherals"],
                    key=lambda item: (item["peripheralName"] or "", item["peripheralId"]),
                ),
            }
            for key in sorted(controllers)
        ]
    return report, definition_evidence


def _aggregate_group_controller_evidence(
    group_rows: list[dict[str, Any]],
    definition_evidence: Mapping[tuple[int, int], dict[str, Any]],
) -> dict[str, Any]:
    evidence = [
        definition_evidence.get((int(row["armyId"]), int(row["peripheralId"])))
        for row in group_rows
    ]
    evidence = [item for item in evidence if item is not None]
    type_ids = sorted(
        {
            type_id
            for item in evidence
            for type_id in item.get("typeEligibility", {})
        }
    )
    type_summary: dict[str, dict[str, int]] = {}
    for type_id in type_ids:
        counts = {"consistent": 0, "inconsistent": 0, "ambiguous": 0, "unknown": 0}
        for item in evidence:
            type_counts = item.get("typeEligibility", {}).get(type_id, {})
            for status in counts:
                counts[status] += int(type_counts.get(status, 0))
        type_summary[type_id] = counts
    presentation_statuses = [
        item.get("armyListPresentation", {}).get("status", "not-matched") for item in evidence
    ]
    return {
        "attachedDefinitionCount": sum(1 for item in evidence if item.get("attachmentCount", 0)),
        "definitionOnlyCount": sum(1 for item in evidence if not item.get("attachmentCount", 0)),
        "attachmentCount": sum(int(item.get("attachmentCount", 0)) for item in evidence),
        "typeEligibility": type_summary,
        "armyListPresentation": {
            "selectableDefinitionCount": presentation_statuses.count("selectable"),
            "embeddedDisabledDefinitionCount": presentation_statuses.count("embedded-disabled"),
            "notMatchedDefinitionCount": presentation_statuses.count("not-matched"),
        },
    }


def audit_peripheral_identity_coverage(
    curated: PeripheralIdentityCurated,
    database: Path,
    *,
    include_details: bool = True,
    rules_documents: Iterable[tuple[Path, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Compare reviewed mappings with one exact Army database snapshot."""
    database = Path(database)
    try:
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        try:
            _require_peripheral_schema(connection)
            snapshot_sha256 = _database_snapshot_sha256(connection)
            schema_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            rows = [
                {
                    "armyId": int(row["army_id"]),
                    "peripheralId": int(row["id"]),
                    "sourceName": str(row["name"]),
                    "mercs": row["mercs"],
                }
                for row in connection.execute(
                    "SELECT army_id, id, name, mercs FROM peripherals ORDER BY army_id, id"
                )
            ]
            controller_graph, definition_controller_evidence = _audit_controller_graph(
                connection,
                {(row["armyId"], row["peripheralId"]): row for row in rows},
                rules_documents=rules_documents,
                include_details=include_details,
            )
        finally:
            connection.close()
    except (OSError, sqlite3.Error, TypeError, ValueError) as exc:
        raise PeripheralIdentityError(
            f"Could not audit Peripheral identity coverage from {database}: {exc}"
        ) from exc

    document = curated.document
    source = _source_for_snapshot(document, snapshot_sha256)
    source_id = source.get("id")
    if not isinstance(source_id, str):
        raise PeripheralIdentityError("Matched Peripheral identity source has no valid id")

    definitions = {(row["armyId"], row["peripheralId"]): row for row in rows}
    mappings_value = document.get("mappings")
    mappings = mappings_value if isinstance(mappings_value, list) else []
    current_mappings = [
        mapping
        for mapping in mappings
        if isinstance(mapping, dict) and mapping.get("sourceId") == source_id
    ]
    mapping_by_key = {
        (int(mapping["armyId"]), int(mapping["peripheralId"])): mapping
        for mapping in current_mappings
    }

    stale_mappings: list[dict[str, Any]] = []
    source_name_drift: list[dict[str, Any]] = []
    for key, mapping in sorted(mapping_by_key.items()):
        definition = definitions.get(key)
        if definition is None:
            stale_mappings.append(
                {
                    "mappingId": mapping.get("id"),
                    "armyId": key[0],
                    "peripheralId": key[1],
                    "sourceName": mapping.get("sourceName"),
                }
            )
            continue
        if mapping.get("sourceName") != definition["sourceName"]:
            source_name_drift.append(
                {
                    "mappingId": mapping.get("id"),
                    "armyId": key[0],
                    "peripheralId": key[1],
                    "expectedSourceName": mapping.get("sourceName"),
                    "actualSourceName": definition["sourceName"],
                }
            )

    mapped_keys = set(mapping_by_key) & set(definitions)
    unmapped_rows = [row for key, row in definitions.items() if key not in mapped_keys]

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[_normalized_review_name(row["sourceName"])].append(row)

    review_queue: list[dict[str, Any]] = []
    repeated_name_group_count = 0
    normalized_name_collision_count = 0
    for normalized_name, group_rows in sorted(groups.items()):
        if len(group_rows) > 1:
            repeated_name_group_count += 1
        source_names = sorted({row["sourceName"] for row in group_rows})
        if len(source_names) > 1:
            normalized_name_collision_count += 1
        unmapped = [
            row
            for row in group_rows
            if (row["armyId"], row["peripheralId"]) not in mapped_keys
        ]
        if not unmapped:
            continue
        reviewed_targets = sorted(
            {
                (
                    str(mapping_by_key[(row["armyId"], row["peripheralId"])].get("entityId")),
                    str(
                        mapping_by_key[(row["armyId"], row["peripheralId"])].get(
                            "profileId", ""
                        )
                    ),
                )
                for row in group_rows
                if (row["armyId"], row["peripheralId"]) in mapping_by_key
            }
        )
        entry: dict[str, Any] = {
            "normalizedName": normalized_name,
            "sourceNames": source_names,
            "definitionCount": len(group_rows),
            "unmappedDefinitionCount": len(unmapped),
            "mercsValues": sorted(
                {row["mercs"] for row in group_rows}, key=lambda value: str(value)
            ),
            "nameCollision": len(source_names) > 1,
            "reviewedTargets": [
                {
                    "entityId": entity_id,
                    **({"profileId": profile_id} if profile_id else {}),
                }
                for entity_id, profile_id in reviewed_targets
            ],
        }
        if definition_controller_evidence:
            entry["controllerEvidence"] = _aggregate_group_controller_evidence(
                group_rows, definition_controller_evidence
            )
        if include_details:
            entry["unmappedDefinitions"] = unmapped
        review_queue.append(entry)

    entities_value = document.get("entities")
    entities = entities_value if isinstance(entities_value, list) else []
    profiles_value = document.get("profiles")
    profiles = profiles_value if isinstance(profiles_value, list) else []
    mapped_entity_ids = {
        str(mapping.get("entityId"))
        for mapping in current_mappings
        if (int(mapping["armyId"]), int(mapping["peripheralId"])) in definitions
    }
    mapped_profile_ids = {
        str(mapping.get("profileId"))
        for mapping in current_mappings
        if "profileId" in mapping
        and (int(mapping["armyId"]), int(mapping["peripheralId"])) in definitions
    }
    curated_only_entities = sorted(
        str(entity.get("id"))
        for entity in entities
        if isinstance(entity, dict) and str(entity.get("id")) not in mapped_entity_ids
    )
    curated_only_profiles = sorted(
        str(profile.get("id"))
        for profile in profiles
        if isinstance(profile, dict) and str(profile.get("id")) not in mapped_profile_ids
    )

    invalid_count = len(stale_mappings) + len(source_name_drift)
    unmapped_count = len(unmapped_rows)
    definition_count = len(rows)
    status = "invalid" if invalid_count else ("complete" if unmapped_count == 0 else "needs-review")
    coverage_percent = 100.0 if definition_count == 0 else round(
        (len(mapped_keys) / definition_count) * 100.0, 2
    )

    report: dict[str, Any] = {
        "format": COVERAGE_FORMAT,
        "formatVersion": COVERAGE_FORMAT_VERSION,
        "status": status,
        "database": {
            "path": str(database),
            "schemaVersion": schema_version,
            "snapshotArchiveSha256": snapshot_sha256,
            "sourceId": source_id,
        },
        "definitions": {
            "definitionCount": definition_count,
            "mappedDefinitionCount": len(mapped_keys),
            "unmappedDefinitionCount": unmapped_count,
            "coveragePercent": coverage_percent,
            "reviewGroupCount": len(groups),
            "unmappedReviewGroupCount": len(review_queue),
            "repeatedNameGroupCount": repeated_name_group_count,
            "normalizedNameCollisionCount": normalized_name_collision_count,
        },
        "controllerGraph": controller_graph,
        "curated": {
            "entityCount": curated.entity_count,
            "profileCount": curated.profile_count,
            "mappingCount": curated.mapping_count,
            "currentSnapshotMappingCount": len(current_mappings),
            "curatedOnlyEntityCount": len(curated_only_entities),
            "curatedOnlyProfileCount": len(curated_only_profiles),
        },
        "validation": {
            "staleMappingCount": len(stale_mappings),
            "sourceNameDriftCount": len(source_name_drift),
            "status": "valid" if invalid_count == 0 else "invalid",
        },
        "reviewQueue": review_queue,
    }
    if include_details:
        report["validation"]["staleMappings"] = stale_mappings
        report["validation"]["sourceNameDrift"] = source_name_drift
        report["curated"]["curatedOnlyEntities"] = curated_only_entities
        report["curated"]["curatedOnlyProfiles"] = curated_only_profiles
    return report
