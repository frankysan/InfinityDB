#!/usr/bin/env python3
"""Audit name-distinguished Army Peripheral variants against their source payloads."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from infinity_army_data.merge import load_sources

SUFFIX = re.compile(r"\s*\([^()]+\)\s*$")
LABEL = re.compile(r"\(([^()]+)\)\s*$")
PAYLOAD_FIELDS = ("skills", "equip", "weapons", "chars")


def summarize(archive: Path, *, unit_id: int, max_families: int) -> dict:
    sources, _ = load_sources(archive)
    definitions = []
    attached = []
    target_units = []
    named_loadouts = []
    equipment_catalog = {}
    source_count = 0
    for source in sources:
        army_id = source.faction_id
        data = source.data
        source_count += 1
        peripheral_by_id = {}
        for entry in data.get("filters", {}).get("equip", []):
            if isinstance(entry, dict):
                equipment_catalog[entry.get("id")] = entry.get("name")
        for definition in data.get("filters", {}).get("peripheral", []):
            if not isinstance(definition, dict):
                continue
            ident = definition.get("id")
            name = str(definition.get("name") or "")
            peripheral_by_id[ident] = name
            definitions.append({
                "armyId": army_id, "id": ident, "name": name,
                "extraFields": sorted(set(definition) - {"id", "name", "mercs"}),
                "payloadFields": [field for field in PAYLOAD_FIELDS if definition.get(field)],
            })
        for unit in data.get("units", []):
            seen = []
            for group in unit.get("profileGroups", []):
                for source_kind, rows in (("profile", group.get("profiles", [])),
                                          ("loadout", group.get("options", []))):
                    for item in rows:
                        linked = []
                        for entry in item.get("peripheral", []):
                            peripheral_id = entry.get("id") if isinstance(entry, dict) else None
                            name = peripheral_by_id.get(peripheral_id)
                            linked.append({
                                "id": peripheral_id, "name": name,
                                "raw": entry,
                            })
                            attached.append({
                                "armyId": army_id, "unitId": unit["id"],
                                "groupId": group.get("id"), "kind": source_kind,
                                "parentId": item.get("id"), "peripheralId": peripheral_id,
                                "name": name,
                            })
                        if linked:
                            seen.append({
                                "groupId": group.get("id"), "kind": source_kind,
                                "parentId": item.get("id"), "parentName": item.get("name"),
                                "attachments": linked,
                                "parentPayload": {field: item[field] for field in PAYLOAD_FIELDS
                                                  if item.get(field)},
                            })
            for group in unit.get("profileGroups", []):
                for option in group.get("options", []):
                    name = str(option.get("name") or "")
                    if not name:
                        continue
                    named_loadouts.append({
                        "armyId": army_id, "unitId": unit.get("id"),
                        "groupId": group.get("id"), "optionId": option.get("id"),
                        "name": name,
                        "base": SUFFIX.sub("", name).casefold().strip(),
                        "hasSuffix": bool(SUFFIX.search(name)),
                        "equipment": sorted(str(v.get("id")) for v in option.get("equip", [])
                                            if isinstance(v, dict)),
                        "skills": sorted(str(v.get("id")) for v in option.get("skills", [])
                                         if isinstance(v, dict)),
                    })
            if unit.get("id") == unit_id:
                target_units.append({
                    "armyId": army_id, "sourceFile": source.filename, "unitName": unit.get("name"),
                    "profilesAndLoadoutsWithPeripherals": seen,
                    "groups": [{
                        "groupId": group.get("id"),
                        "profiles": [{"id": p.get("id"), "name": p.get("name"),
                                      "peripherals": p.get("peripheral", []),
                                      "equipment": p.get("equip", []),
                                      "skills": p.get("skills", []),
                                      "weapons": p.get("weapons", [])}
                                     for p in group.get("profiles", [])],
                        "loadouts": [{"id": o.get("id"), "name": o.get("name"),
                                      "peripherals": o.get("peripheral", []),
                                      "equipment": o.get("equip", []),
                                      "includes": o.get("includes", [])}
                                     for o in group.get("options", [])],
                    } for group in unit.get("profileGroups", [])],
                })

    families = defaultdict(lambda: defaultdict(set))
    for record in definitions:
        base = SUFFIX.sub("", record["name"]).casefold().strip()
        families[base][record["name"]].add(record["armyId"])
    variants = []
    for base, names in sorted(families.items()):
        if len(names) < 2:
            continue
        related = [a for a in attached if
                   a["name"] in names]
        variants.append({
            "base": base,
            "names": sorted(names),
            "armies": len(set().union(*names.values())),
            "attachmentCount": len(related),
            "sourceUnitIds": sorted({a["unitId"] for a in related}),
        })
    variants.sort(key=lambda v: (-v["attachmentCount"], v["base"]))
    families_by_unit = defaultdict(list)
    for item in named_loadouts:
        families_by_unit[(item["armyId"], item["unitId"], item["groupId"],
                          item["base"])].append(item)
    name_distinguished_loadouts = []
    for group, entries in families_by_unit.items():
        if len({item["name"] for item in entries}) < 2:
            continue
        if not any(item["hasSuffix"] for item in entries):
            continue
        name_distinguished_loadouts.append({
            "armyId": group[0], "unitId": group[1], "groupId": group[2],
            "base": group[3],
            "variants": [{key: item[key] for key in ("optionId", "name", "equipment", "skills")}
                         for item in entries],
            "suffixWithEmptyEquipment": any(
                item["hasSuffix"] and not item["equipment"] for item in entries
            ),
        })
    name_distinguished_loadouts.sort(
        key=lambda v: (not v["suffixWithEmptyEquipment"], v["armyId"], v["unitId"])
    )
    catalog_by_name = defaultdict(set)
    for equipment_id, equipment_name in equipment_catalog.items():
        if equipment_name:
            catalog_by_name[str(equipment_name).casefold()].add(str(equipment_id))
    catalog_suffix_candidates = []
    for item in named_loadouts:
        label_match = LABEL.search(item["name"])
        if label_match is None:
            continue
        catalog_ids = catalog_by_name.get(label_match.group(1).strip().casefold(), set())
        if not catalog_ids or catalog_ids.intersection(item["equipment"]):
            continue
        catalog_suffix_candidates.append({
            key: item[key] for key in
            ("armyId", "unitId", "groupId", "optionId", "name", "equipment")
        } | {"namedEquipmentIdsAbsentFromLoadout": sorted(catalog_ids)})
    catalog_suffix_candidates.sort(
        key=lambda item: (item["armyId"], item["unitId"], item["groupId"])
    )
    return {
        "archive": str(archive),
        "sourceArmyCount": source_count,
        "peripheralDefinitionCount": len(definitions),
        "definitionsWithExplicitPayloadFields": [
            item for item in definitions if item["payloadFields"]
        ][:20],
        "definitionsWithExtraFields": [
            item for item in definitions if item["extraFields"]
        ][:20],
        "peripheralAttachmentCount": len(attached),
        "uniquePeripheralNames": len({record["name"] for record in definitions}),
        "variantFamiliesCount": len(variants),
        "variantFamilies": variants[:max_families],
        "nameDistinguishedLoadoutFamiliesCount": len(name_distinguished_loadouts),
        "nameDistinguishedLoadoutFamiliesWithEmptySuffixEquipment": sum(
            item["suffixWithEmptyEquipment"] for item in name_distinguished_loadouts
        ),
        "nameDistinguishedLoadoutFamilies": name_distinguished_loadouts[:max_families],
        "catalogSuffixCandidatesCount": len(catalog_suffix_candidates),
        "catalogSuffixCandidates": catalog_suffix_candidates[:max_families],
        "requestedUnitEquipmentCatalog": {str(key): value for key, value
                                         in equipment_catalog.items()
                                         if key in {111, 145, 100}
                                         or "repeater" in str(value).casefold()},
        "requestedUnitId": unit_id,
        "unitOccurrences": target_units,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument(
        "--unit", type=int, default=0, help="Include full source details for this Unit ID"
    )
    parser.add_argument("--max-families", type=int, default=40)
    args = parser.parse_args()
    print(json.dumps(
        summarize(args.archive, unit_id=args.unit, max_families=args.max_families),
        ensure_ascii=False, indent=2,
    ))


if __name__ == "__main__":
    main()
