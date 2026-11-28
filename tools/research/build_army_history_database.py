"""Build the private, queryable N5 historical Army research database."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from itertools import pairwise
from pathlib import Path
from typing import Any

from infinity_db.army_history_source import (
    Document,
    HistoricalArmySource,
    digest,
    document,
    read_history,
    require,
    verify_receipt,
)

# The accepted baseline in docs/n5-source-history.md. Selection is explicit;
# do not discover a newer report or substitute a summary for full evidence.
ARCHIVE_PIN = "08978b9bbf3fffa3184f6153fa4dd05a1931482742f08ee5de7a6df4f4a3c5c5"
RECEIPT_PIN = "da15fe82f910228ebd43b12eb74c47a365346fb9c4070b9768e0ed1cb59089d3"
REPORTS = {
    "characterization": ("characterization-v1.json", 1,
                         "4477dac7daa81f8b4580f8db3a9fedb9cb1bb27a7d9ced9c04296fa017ce5bfc"),
    "identityReview": ("n5-identity-review-v1.json", None,
                       "953d39efc8a1804803932f6845b4c0912e4a5f13ebeb31da15a583ef680d350b"),
    "pilot": ("n5-semantic-pilot-v3.json", 1,
              "168c4a06243b04a7097861464823150257344a6dafffd0eebbe377cd838cb8a3"),
    "consolidation": ("n5-consolidation-v3.json", 3,
                      "2694ab280e386558347cbf580ff553b426a750723efed0345a96f7010b4c0b74"),
    "membership": ("n5-membership-v2.json", 2,
                   "e740eec0460fd50747a18a467f46ab9efc88c8f607852769ebf05b829187ad10"),
    "loadouts": ("n5-loadouts-v2.json", 2,
                 "998ef8c5f82157d545cbf9446d6a316f8b0a7cbec1cb0f6e0f71cc40beb2f926"),
    "catalogs": ("n5-catalogs-v1.json", 1,
                 "d8ab56be3db436afaa7f40d344617c7c745b62828fe92d481e2fbac9ca875fb1"),
}
STREAMS = {
    "consolidation": {"candidates": "compositionCandidate"},
    "membership": {
        "nestedCandidateGroups": "nestedCandidate",
        "structuralOccurrences": "structuralOccurrence",
        "declaredMembershipClaims": "declaredMembershipClaim",
        "armyFieldOccurrences": "armyFieldOccurrence",
        "review": "membershipReview",
    },
    "loadouts": {
        "matches": "loadoutMatch",
        "unpaired": "loadoutUnpaired",
        "modificationReviewGroups": "loadoutModificationReview",
    },
    "catalogs": {
        "transitionGroups": "catalogTransition",
        "review": "catalogReview",
    },
}

SCHEMA = """
PRAGMA user_version=1;
CREATE TABLE metadata (key TEXT PRIMARY KEY, body TEXT NOT NULL);
CREATE TABLE source_report (
    report_id TEXT PRIMARY KEY, filename TEXT NOT NULL, sha256 TEXT NOT NULL,
    format_version INTEGER, body TEXT NOT NULL
);
CREATE TABLE source_observation (
    observation_index INTEGER PRIMARY KEY, edition TEXT, army_id INTEGER,
    source_sha256 TEXT NOT NULL, encoded_revision_date TEXT, body TEXT NOT NULL,
    metadata_contexts TEXT NOT NULL, unresolved INTEGER NOT NULL CHECK(unresolved IN (0,1))
);
CREATE TABLE unit_identity (
    unit_id INTEGER PRIMARY KEY, candidate_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL, body TEXT NOT NULL
);
CREATE TABLE comparison (
    comparison_index INTEGER PRIMARY KEY, army_id INTEGER NOT NULL,
    earlier_date TEXT NOT NULL, later_date TEXT NOT NULL,
    body TEXT NOT NULL, CHECK(earlier_date < later_date),
    UNIQUE(army_id, earlier_date, later_date)
);
CREATE TABLE comparison_change (
    comparison_index INTEGER NOT NULL REFERENCES comparison,
    change_index INTEGER NOT NULL, unit_id INTEGER, category TEXT NOT NULL,
    body TEXT NOT NULL, PRIMARY KEY(comparison_index, change_index)
);
CREATE INDEX comparison_change_unit ON comparison_change(unit_id, category);
CREATE TABLE coverage_gap (
    gap_index INTEGER PRIMARY KEY, army_id INTEGER NOT NULL,
    earlier_date TEXT NOT NULL, later_date TEXT NOT NULL, body TEXT NOT NULL,
    CHECK(earlier_date < later_date)
);
CREATE TABLE history_record (
    stream TEXT NOT NULL, position INTEGER NOT NULL,
    report_id TEXT NOT NULL REFERENCES source_report, section TEXT NOT NULL,
    record_key TEXT, body TEXT NOT NULL, PRIMARY KEY(stream, position),
    UNIQUE(stream, record_key)
);
CREATE TABLE history_record_unit (
    stream TEXT NOT NULL, position INTEGER NOT NULL,
    unit_id INTEGER NOT NULL REFERENCES unit_identity,
    PRIMARY KEY(stream, position, unit_id),
    FOREIGN KEY(stream, position) REFERENCES history_record
);
CREATE INDEX history_record_by_unit ON history_record_unit(unit_id, stream, position);
CREATE TABLE history_record_evidence (
    stream TEXT NOT NULL, position INTEGER NOT NULL, evidence_index INTEGER NOT NULL,
    role TEXT NOT NULL, comparison_index INTEGER NOT NULL REFERENCES comparison,
    change_index INTEGER, PRIMARY KEY(stream, position, evidence_index),
    FOREIGN KEY(stream, position) REFERENCES history_record,
    FOREIGN KEY(comparison_index, change_index) REFERENCES comparison_change
);
CREATE INDEX history_record_by_comparison ON history_record_evidence(comparison_index);
"""


def encode(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def unit_on_path(path: list[Any]) -> int | None:
    if len(path) >= 2 and path[0] == "units" and type(path[1]) is int:
        return path[1]
    return None


def record_links(stream: str, row: Document) -> tuple[set[int], list[tuple[str, Document]]]:
    """Link typed source paths; definition usage is not Unit composition."""
    evidence: list[tuple[str, Document]] = []
    units: set[int] = set()

    def add_path(value: Document, key: str = "path") -> None:
        if (unit := unit_on_path(value.get(key, []))) is not None:
            units.add(unit)

    def add_evidence(value: Document, role: str = "evidence") -> None:
        evidence.append((role, value))
        for usage in value.get("usages", []):
            add_path(usage)

    add_path(row)
    add_path(row, "parentPath")
    if type(row.get("unitId")) is int:
        units.add(row["unitId"])
    if stream == "loadoutMatch":
        for side in ("before", "after"):
            add_path(row[side])
            add_evidence(row[side]["evidence"], side)
    elif stream == "loadoutUnpaired":
        occurrence = row["occurrence"]
        add_path(occurrence)
        add_evidence(occurrence["evidence"])
    elif stream == "loadoutModificationReview":
        for pair in row["evidence"]:
            for side in ("before", "after"):
                add_evidence(pair[side], side)
    elif stream == "catalogReview":
        add_evidence(row)
    else:
        items = row["evidence"]
        for item in items if isinstance(items, list) else [items]:
            add_evidence(item)
        for item in row.get("listEvidence", []):
            add_evidence(item, "listEvidence")
    require(bool(units) and bool(evidence), f"Unlinked history record: {stream}")
    return units, evidence


def selected_reports(root: Path, source: HistoricalArmySource) -> dict[str, Document]:
    reports = {}
    for key, (name, version, pin) in REPORTS.items():
        raw = (root / "reports" / name).read_bytes()
        require(digest(raw) == pin, f"Historical report SHA-256 differs: {name}")
        row = document(raw)
        if version is not None:
            require(row.get("formatVersion") == version
                    and row.get("archiveSha256") == source.sha256,
                    f"Historical report scope differs: {name}")
        if key not in {"characterization", "identityReview"}:
            require(row.get("edition") == "n5", f"Historical report edition differs: {name}")
        if key in {"consolidation", "membership", "catalogs"}:
            require(row.get("pilotSha256") == REPORTS["pilot"][2], f"Pilot link differs: {name}")
        if key == "loadouts":
            require(row.get("membershipSha256") == REPORTS["membership"][2],
                    "Membership link differs")
        reports[key] = row
    return reports


def populate(db: sqlite3.Connection, source: HistoricalArmySource,
             reports: dict[str, Document]) -> dict[str, int]:
    """Persist exact accepted rows, with indexed evidence links and no promotion."""
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript(SCHEMA)
    db.executemany("INSERT INTO metadata VALUES (?,?)", [
        ("format", encode("InfinityDB private N5 Army history research")),
        ("publicationStatus", encode("privateResearchOnly")),
        ("archiveSha256", encode(source.sha256)),
        ("receiptSha256", encode(RECEIPT_PIN)),
        ("coverage", encode(source.index["coverage"])),
        ("archiveSummary", encode(source.summary)),
        ("sourceScope", encode(source.index["sourceScope"])),
        ("archiveEvidencePins", encode(source.index["evidence"])),
    ])
    unresolved = set(source.unresolved)
    db.executemany("INSERT INTO source_observation VALUES (?,?,?,?,?,?,?,?)", (
        (i, row["edition"], row["factionId"], row["sha256"], row.get("encodedRevisionDate"),
         encode(row), encode(source.metadata_contexts.get(i, ())), int(i in unresolved))
        for i, row in enumerate(source.index["observations"])
    ))

    for key, report in reports.items():
        name, version, pin = REPORTS[key]
        excluded = set(STREAMS.get(key, {}))
        if key == "pilot":
            excluded.update(("comparisons", "skipped"))
        if key == "consolidation":
            excluded.add("identityInventory")
        body = {k: v for k, v in report.items() if k not in excluded}
        if key == "consolidation":
            body["identityInventory"] = {
                k: v for k, v in report["identityInventory"].items() if k != "candidates"
            }
        db.execute("INSERT INTO source_report VALUES (?,?,?,?,?)",
                   (key, name, pin, version, encode(body)))

    inventory = reports["consolidation"]["identityInventory"]["candidates"]
    db.executemany("INSERT INTO unit_identity VALUES (?,?,?,?)", (
        (row["unitId"], row["candidateKey"], row["status"], encode(row))
        for row in inventory
    ))

    days: dict[int, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for edition, army, day, sha in source.groups:
        if edition == "n5":
            days[army][day].append(sha)
    expected = {(army, a, b) for army, sequence in days.items()
                for a, b in pairwise(sorted(sequence))}
    seen = set()

    def check_endpoint(army: int, endpoint: Document) -> str:
        day = endpoint["encodedRevisionDate"]
        key = ("n5", army, day, endpoint["sha256"])
        require(key in source.groups, "Unknown historical comparison endpoint")
        indices = source.groups[key]
        require(list(indices) == endpoint["observationIndices"], "Observation link differs")
        metadata = sorted({sha for i in indices for sha in source.metadata_contexts.get(i, ())
                           if sha is not None})
        require(metadata == endpoint["metadataSha256"], "Metadata link differs")
        return day

    pilot = reports["pilot"]
    comparisons = pilot["comparisons"]
    for ci, row in enumerate(comparisons):
        army = row["factionId"]
        a, b = (check_endpoint(army, row[side]) for side in ("earlier", "later"))
        key = (army, a, b)
        require(key in expected and key not in seen, "Unexpected comparison")
        require(len(days[army][a]) == len(days[army][b]) == 1, "Ambiguous comparison")
        seen.add(key)
        db.execute("INSERT INTO comparison VALUES (?,?,?,?,?)", (
            ci, army, a, b, encode({k: v for k, v in row.items() if k != "changes"}),
        ))
        db.executemany("INSERT INTO comparison_change VALUES (?,?,?,?,?)", (
            (ci, i, unit_on_path(change["path"]), change["category"], encode(change))
            for i, change in enumerate(row["changes"])
        ))

    for i, row in enumerate(pilot["skipped"]):
        army = row["factionId"]
        window = []
        for side in ("earlier", "later"):
            endpoints = row[side]
            dates = {check_endpoint(army, endpoint) for endpoint in endpoints}
            require(len(dates) == 1, "Ambiguous endpoint dates differ")
            day = next(iter(dates))
            require(sorted(e["sha256"] for e in endpoints) == sorted(days[army][day]),
                    "Incomplete same-day alternatives")
            window.append(day)
        a, b = window
        key = (army, a, b)
        require(key in expected and key not in seen, "Unexpected coverage gap")
        require(len(days[army][a]) > 1 or len(days[army][b]) > 1, "Gap is not ambiguous")
        seen.add(key)
        db.execute("INSERT INTO coverage_gap VALUES (?,?,?,?,?)", (i, army, a, b, encode(row)))
    require(seen == expected, "Historical comparison coverage differs")

    counts = Counter({"sourceObservations": len(source.index["observations"]),
                      "unitIdentities": len(inventory), "comparisons": len(comparisons),
                      "coverageGaps": len(pilot["skipped"]),
                      "rawChanges": sum(len(row["changes"]) for row in comparisons)})
    for report_id, sections in STREAMS.items():
        for section, stream in sections.items():
            for position, row in enumerate(reports[report_id][section]):
                key = next((row[k] for k in ("candidateId", "definitionTransitionId", "reviewId")
                            if k in row), None)
                db.execute("INSERT INTO history_record VALUES (?,?,?,?,?,?)",
                           (stream, position, report_id, section, key, encode(row)))
                units, evidence = record_links(stream, row)
                db.executemany("INSERT INTO history_record_unit VALUES (?,?,?)",
                               ((stream, position, unit) for unit in sorted(units)))
                for i, (role, ev) in enumerate(evidence):
                    ci = ev["comparisonIndex"]
                    require(type(ci) is int and 0 <= ci < len(comparisons),
                            "Unknown evidence comparison")
                    comparison = comparisons[ci]
                    require(all(ev[k] == comparison[k] for k in ("factionId", "earlier", "later")),
                            "Evidence comparison differs")
                    change = ev.get("changeIndex")
                    if change is not None:
                        require(type(change) is int and 0 <= change < len(comparison["changes"]),
                                "Unknown evidence change")
                        require(unit_on_path(comparison["changes"][change]["path"]) in units,
                                "Evidence Unit differs")
                    db.execute("INSERT INTO history_record_evidence VALUES (?,?,?,?,?,?)",
                               (stream, position, i, role, ci, change))
                    counts["recordEvidenceLinks"] += 1
                counts[stream] += 1
                counts["recordUnitLinks"] += len(units)
    require(db.execute("PRAGMA foreign_key_check").fetchone() is None,
            "Historical database foreign key violation")
    require(db.execute("PRAGMA integrity_check").fetchone() == ("ok",),
            "Historical database integrity check failed")
    return dict(counts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("local/data/history"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    require(output.is_relative_to(root / "generated"),
            "Use the private history generated directory")
    require(not output.exists(), "Historical database output already exists")
    source = read_history(root / "archive" / "army-history-v1.zip", ARCHIVE_PIN)
    verify_receipt(source, root / "archive" / "army-history-v1.acceptance.json", RECEIPT_PIN)
    reports = selected_reports(root, source)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb"):
        pass
    try:
        with closing(sqlite3.connect(output)) as db, db:
            counts = populate(db, source, reports)
    except BaseException:
        output.unlink()
        raise
    print(json.dumps(counts, indent=2, sort_keys=True))
    print(f"Private N5 history database: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
