"""Build a private Unit-history preview against the exact current N5 Army snapshot."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from contextlib import closing
from functools import lru_cache
from pathlib import Path

from infinity_db.army_history_consolidation import record_at
from infinity_db.army_history_source import Document, file_digest, read_history, require
from infinity_db.build_provenance import BUILD_PROVENANCE_KEY, validate_build_record
from infinity_db.database.repository import Database
from tools.research.build_army_history_database import ARCHIVE_PIN, encode

ROOT = Path("local/data/history")
HISTORY = ROOT / "generated/army_history_n5.db"
ARMY = Path("data/generated/army.db")
MATCHABLE = frozenset({
    "consistentObservedIdAndSlug", "reviewedSeparateArmyIdentity", "reviewedSpellingAlias",
})


def resolve_identity(
    historical: Document, current: Document | None, direct_indices: set[int],
) -> Document:
    """Require direct source agreement before using the current logical mapping."""
    direct = [
        (slug["slug"], occurrence)
        for slug in historical["slugEvidence"]
        for occurrence in slug["occurrences"]
        if direct_indices.intersection(occurrence["observationIndices"])
    ]
    result: Document = {"sourceUnitId": historical["unitId"], "logicalUnitId": None}
    if historical["status"] not in MATCHABLE:
        return {**result, "status": "historicalIdentityReview"}
    if not direct:
        return {**result, "status": "historicalOnly" if current is None else "noDirectEvidence"}
    if current is None:
        return {**result, "status": "missingCurrentSource"}
    if any(
        (slug, occurrence["canonical"], occurrence["idArmy"]) !=
        (current["sourceSlug"], current["canonicalFactionId"], current["idArmy"])
        for slug, occurrence in direct
    ):
        return {**result, "status": "currentSourceConflict"}
    return {**result, "status": "matched", "logicalUnitId": current["logicalUnitId"],
            "directObservationIndices": sorted({
                i for _, occurrence in direct for i in occurrence["observationIndices"]
                if i in direct_indices
            })}


def composition_groups(records: list[Document]) -> list[Document]:
    """Group fields only for identical source target, window and comparison scope."""
    grouped: dict[str, Document] = {}
    for row in records:
        body = row["body"]
        evidence = body["evidence"]
        scope = sorted(
            (e["factionId"], e["comparisonIndex"]) for e in evidence
        )
        context = {
            "sourcePath": body["path"][:-1],
            "earlierObservedDate": body["earlierObservedDate"],
            "laterObservedDate": body["laterObservedDate"],
            "armyIds": sorted({e["factionId"] for e in evidence}),
            "comparisonIndices": sorted({e["comparisonIndex"] for e in evidence}),
            "historicalLabels": row["historicalLabels"],
            "status": "observedCandidate",
        }
        key = encode([context, scope])
        group = grouped.setdefault(key, {**context, "changes": []})
        group["changes"].append({
            "field": body["path"][-1], "before": body["before"], "after": body["after"],
            "evidenceRecord": row["ref"], "candidateId": body["candidateId"],
        })
    for group in grouped.values():
        group["changes"].sort(key=lambda c: (c["field"], c["candidateId"]))
    return sorted(grouped.values(), key=lambda g: (
        g["laterObservedDate"], g["earlierObservedDate"], encode(g["sourcePath"]),
        g["comparisonIndices"], encode(g["historicalLabels"]),
    ), reverse=True)


def current_units(db: sqlite3.Connection) -> dict[int, Document]:
    return {
        row[0]: {
            "sourceSlug": row[1], "canonicalFactionId": row[2], "idArmy": row[3],
            "logicalUnitId": row[4], "name": row[5], "slug": row[6],
        }
        for row in db.execute(
            "SELECT u.id,u.slug,u.canonical_faction_id,u.id_army,l.id,l.name,s.slug "
            "FROM units u JOIN logical_unit_sources m ON m.source_unit_id=u.id "
            "JOIN logical_units l ON l.id=m.logical_unit_id "
            "LEFT JOIN application_domain_slugs s ON s.application_id=l.id AND s.domain='units' "
            "WHERE u.source_defined=1 ORDER BY u.id"
        )
    }


def read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def build(history: sqlite3.Connection, army: sqlite3.Connection, archive: Path) -> Document:
    meta = {key: json.loads(value) for key, value in history.execute(
        "SELECT key,body FROM metadata"
    )}
    require(history.execute("PRAGMA user_version").fetchone() == (1,), "History schema differs")
    require(meta["publicationStatus"] == "privateResearchOnly"
            and meta["archiveSha256"] == ARCHIVE_PIN, "Unexpected history corpus")
    army_meta = {key: json.loads(value) for key, value in army.execute(
        "SELECT key,value FROM __infinity_metadata"
    )}
    provenance = validate_build_record(army_meta[BUILD_PROVENANCE_KEY], "army")
    snapshot = provenance["manifest"]["source"]["archiveSha256"]
    require(army_meta["_meta"]["snapshotArchiveSha256"] == snapshot, "Army snapshot differs")
    require(any(s["edition"] == "n5" and s["archiveSha256"] == snapshot
                for s in meta["sourceScope"]["directSnapshots"]),
            "Current Army is not an accepted direct N5 history endpoint")
    direct_indices = {
        i for i, body in history.execute(
            "SELECT observation_index,body FROM source_observation WHERE edition='n5'"
        )
        if (row := json.loads(body))["sourceType"] == "direct-api"
        and row["sourceArchiveSha256"] == snapshot and row["kind"] == "faction"
    }
    require(bool(direct_indices), "No current direct observations")
    current = current_units(army)
    identities = {
        i: resolve_identity(json.loads(body), current.get(i), direct_indices)
        for i, body in history.execute("SELECT unit_id,body FROM unit_identity ORDER BY unit_id")
    }
    for i in sorted(current.keys() - identities.keys()):
        identities[i] = {"sourceUnitId": i, "logicalUnitId": None, "status": "currentOnly"}

    source = read_history(archive, ARCHIVE_PIN)

    @lru_cache(maxsize=64)
    def historical_document(sha: str) -> Document:
        return source.read_object(sha)

    def labels(body: Document) -> list[list[Document]]:
        # Keep the actual endpoint labels, not present-day names assigned to old keys.
        results = {}
        for evidence in body["evidence"]:
            for side in ("earlier", "later"):
                data = historical_document(evidence[side]["sha256"])
                found = record_at(data, body["path"])
                if found is None:
                    raise ValueError("Historical target path no longer resolves")
                context = [
                    {k: row[k] for k in ("id", "name", "isc", "slug", "category") if k in row}
                    for row in found[1]
                ]
                results[encode(context)] = context
        return [results[k] for k in sorted(results)]

    by_logical: dict[int, Document] = {}
    for i, identity in sorted(identities.items()):
        logical = identity["logicalUnitId"]
        if logical is None:
            continue
        row = current[i]
        entry = by_logical.setdefault(logical, {
            "logicalUnitId": logical, "slug": row["slug"], "name": row["name"],
            "sourceIdentities": [], "composition": [], "armyObservations": [],
            "reviewEvidence": {}, "catalogEvidence": {}, "rawChangeCategories": {},
        })
        entry["sourceIdentities"].append(identity)

    for unit, category, count in history.execute(
        "SELECT unit_id,category,COUNT(*) FROM comparison_change "
        "WHERE unit_id IS NOT NULL GROUP BY unit_id,category ORDER BY unit_id,category"
    ):
        identity = identities.get(unit)
        if identity is not None and identity["status"] == "matched":
            categories = by_logical[identity["logicalUnitId"]]["rawChangeCategories"]
            categories.setdefault(str(unit), {})[category] = count

    counts: Counter[str] = Counter()
    for unit, stream, position, raw in history.execute(
        "SELECT u.unit_id,r.stream,r.position,r.body FROM history_record_unit u "
        "JOIN history_record r USING(stream,position) ORDER BY u.unit_id,r.stream,r.position"
    ):
        identity = identities[unit]
        if identity["status"] != "matched":
            counts["unresolvedRecordLinks"] += 1
            continue
        entry = by_logical[identity["logicalUnitId"]]
        body = json.loads(raw)
        ref = {"stream": stream, "position": position, "sourceUnitId": unit}
        if stream == "compositionCandidate":
            entry["composition"].append({
                "ref": ref, "body": body, "historicalLabels": labels(body),
            })
        elif (stream == "armyFieldOccurrence"
              or stream == "structuralOccurrence" and body["kind"] == "unitListMembership"
              and not body["possibleReplacementIds"]):
            ev = body["evidence"]
            entry["armyObservations"].append({
                "kind": body["kind"], "sourcePath": body["path"], "armyId": ev["factionId"],
                "earlierObservedDate": ev["earlier"]["encodedRevisionDate"],
                "laterObservedDate": ev["later"]["encodedRevisionDate"],
                "direction": body.get("direction"), "evidenceRecord": ref,
                "before": body["before"] if stream == "armyFieldOccurrence" else
                {"present": body["before"]["present"]},
                "after": body["after"] if stream == "armyFieldOccurrence" else
                {"present": body["after"]["present"]},
                "status": "observedCandidate",
            })
        else:
            key = "catalogEvidence" if stream.startswith("catalog") else "reviewEvidence"
            entry[key].setdefault(stream, []).append(ref)
        counts[stream] += 1
    for entry in by_logical.values():
        entry["composition"] = composition_groups(entry["composition"])
        entry["armyObservations"].sort(
            key=lambda r: (r["laterObservedDate"], r["earlierObservedDate"],
                           r["armyId"], encode(r["sourcePath"])), reverse=True
        )
    return {
        "formatVersion": 1, "publicationStatus": "privatePreviewOnly", "edition": "n5",
        "archiveSha256": ARCHIVE_PIN, "currentSnapshotSha256": snapshot,
        "currentBuildSetId": provenance["buildSetId"], "coverage": meta["coverage"],
        # Army-level observation gaps do not establish Unit-level absence or change.
        "ambiguousArmyWindows": [
            {"gapIndex": i, "armyId": army, "earlierObservedDate": earlier,
             "laterObservedDate": later}
            for i, army, earlier, later in history.execute(
                "SELECT gap_index,army_id,earlier_date,later_date FROM coverage_gap "
                "ORDER BY army_id,earlier_date,later_date"
            )
        ],
        "identityCounts": dict(Counter(row["status"] for row in identities.values())),
        "recordLinkCounts": dict(counts),
        "unresolvedIdentities": [row for _, row in sorted(identities.items())
                                 if row["status"] != "matched"],
        "units": [entry for _, entry in sorted(by_logical.items())],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to((ROOT / "generated").resolve()), "Use private history directory")
    require(not output.exists(), "Preview already exists")
    require(file_digest(HISTORY) == args.history_sha256, "History database SHA-256 differs")
    army_pin = file_digest(ARMY)
    Database(ARMY).validate()
    with closing(read_only(HISTORY)) as history, closing(read_only(ARMY)) as army:
        result = build(history, army, ROOT / "archive/army-history-v1.zip")
    require(file_digest(HISTORY) == args.history_sha256 and file_digest(ARMY) == army_pin,
            "Input databases changed during preview")
    result["historyDatabaseSha256"] = args.history_sha256
    result["armyDatabaseSha256"] = army_pin
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(encode(result) + "\n")
    print(json.dumps({
        "identityCounts": result["identityCounts"], "recordLinkCounts": result["recordLinkCounts"],
        "logicalUnits": len(result["units"]),
        "unitsWithComposition": sum(bool(u["composition"]) for u in result["units"]),
        "compositionGroups": sum(len(u["composition"]) for u in result["units"]),
        "armyObservations": sum(len(u["armyObservations"]) for u in result["units"]),
        "unresolvedIdentities": result["unresolvedIdentities"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
