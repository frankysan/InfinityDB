"""Report source-backed N5 Unit identity exceptions for manual disposition."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from infinity_db.army_history_characterization import fingerprint
from infinity_db.army_history_pilot import indexed
from infinity_db.army_history_source import read_history, verify_receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--receipt-sha256", required=True)
    parser.add_argument("--unit-ids", type=int, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = read_history(args.archive, args.sha256)
    verify_receipt(source, args.receipt, args.receipt_sha256)
    wanted = set(args.unit_ids)
    variants = defaultdict(dict)
    by_id = defaultdict(list)
    coexistence = []
    for edition, army, day, sha in sorted(source.groups):
        if edition != "n5":
            continue
        data = source.read_object(sha)
        units = indexed(data.get("units"))
        if units is None:
            raise ValueError(f"Invalid unit array: {sha}")
        found = sorted(wanted & units.keys())
        evidence = {
            "factionId": army, "date": day, "sha256": sha,
            "observationIndices": list(source.groups[(edition, army, day, sha)]),
        }
        if len(found) > 1:
            coexistence.append({**evidence, "unitIds": found})
        for identity in found:
            unit = units[identity]
            signature = {k: unit.get(k) for k in (
                "slug", "isc", "name", "canonical", "idArmy", "factions",
            )}
            key = fingerprint(signature)
            row = variants[identity].setdefault(key, {
                "identityFields": signature, "occurrences": [], "example": unit,
            })
            row["occurrences"].append(evidence)
            by_id[identity].append(evidence)
    report = {
        "archiveSha256": source.sha256,
        "units": {identity: list(variants[identity].values()) for identity in sorted(wanted)},
        "coexistence": coexistence,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
    for identity, rows in report["units"].items():
        print(json.dumps({
            "id": identity, "occurrences": len(by_id[identity]),
            "variants": [{
                "identityFields": row["identityFields"],
                "count": len(row["occurrences"]),
                "armies": sorted({e["factionId"] for e in row["occurrences"]}),
                "first": min(e["date"] for e in row["occurrences"]),
                "last": max(e["date"] for e in row["occurrences"]),
                "profileGroups": [{
                    "id": g.get("id"), "isc": g.get("isc"),
                    "profiles": [p.get("name") for p in g.get("profiles", [])],
                    "options": len(g.get("options", [])),
                } for g in row["example"].get("profileGroups", [])],
            } for row in rows],
        }, ensure_ascii=False, sort_keys=True))
    print(json.dumps({"coexistenceCount": len(coexistence), "examples": coexistence[:3]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
