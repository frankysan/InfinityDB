"""Historical source consumer regression tests using only synthetic ZIPs."""

import hashlib
import json
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import pytest

from infinity_db.army_history_characterization import (
    characterize,
    characterize_faction,
    compare_content,
    compare_identities,
)
from infinity_db.army_history_source import read_history, verify_receipt


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return json.dumps(value).encode()


def fixture(*, distinct_days=False):
    objects = {}
    evidence = {}

    def obj(value):
        raw = encode(value)
        sha = digest(raw)
        objects[sha] = raw
        return sha

    def report(name, value):
        raw = encode(value)
        evidence[f"evidence/{name}.json"] = raw
        return digest(raw)

    metadata = obj({"factions": [{"id": 101, "name": "PanO"}]})
    first = obj({"version": "7.26329.1", "units": [{"id": 1}]})
    second = obj({"version": "7.26330.2" if distinct_days else "7.26329.2",
                  "units": [{"id": 2}]})
    unknown = obj({"version": "7.26329.3", "units": []})
    backup = {"archiveSha256": "a" * 64}
    git = {"tipCommit": "b" * 40}
    snap = "c" * 64
    acquired = "2026-11-26T12:00:00+00:00" if distinct_days else "2026-11-25T12:00:00+00:00"
    rows = []
    inventory = []
    recovery = []
    assignments = []

    def blob_id(sha):
        raw = objects[sha]
        return hashlib.sha1(
            f"blob {len(raw)}\0".encode("ascii") + raw, usedforsecurity=False,
        ).hexdigest()

    def row(sha, kind="faction"):
        data: dict[str, Any] = {
            "edition": "n5", "kind": kind, "sha256": sha,
            "sizeBytes": len(objects[sha]),
        }
        if kind == "faction":
            data.update(
                sourceRevision=json.loads(objects[sha])["version"],
                encodedRevisionDate="2026-11-26" if distinct_days and sha == second
                else "2026-11-25", issues=[],
            )
        return data

    for sha, faction in ((first, 101), (second, 101), (unknown, None)):
        version = json.loads(objects[sha])["version"]
        path = f"n5/pan/{version}.json"
        blob = blob_id(sha)
        entry = {**row(sha), "member": f"backup/{path}"}
        identity = {
            "factionId": faction,
            "identityStatus": "inferred" if faction else "unresolved",
        }
        inventory.append(entry)
        assignments.append({**entry, **identity, "gitBlob": blob})
        rows.append({
            **entry, **identity, "sourceType": "backup-zip",
            "sourceArchiveSha256": backup["archiveSha256"],
        })
        appearance = {"metadataBlob": blob_id(metadata), "commitIndex": 1}
        entry = {**row(sha), "path": path, "blob": blob, "appearances": [appearance]}
        recovery.append(entry)
        rows.append({
            **entry, **identity, "sourceType": "backup-git",
            "sourceTipCommit": git["tipCommit"],
        })
    entry = {**row(metadata, "metadata"), "path": "n5/army.json", "blob": blob_id(metadata)}
    recovery.append(entry)
    rows.append({
        **entry, "sourceType": "backup-git", "sourceTipCommit": git["tipCommit"],
        "factionId": None,
    })
    for sha, kind, member in (
        (metadata, "metadata", "metadata.json"), (second, "faction", "101-pan.json"),
    ):
        entry = {
            **row(sha, kind), "sourceType": "direct-api", "sourceArchiveSha256": snap,
            "member": member, "acquiredAt": acquired,
            "factionId": 101 if kind == "faction" else None,
        }
        if kind == "faction":
            entry.update(identityStatus="direct-endpoint", metadataSha256=metadata)
        rows.append(entry)

    inv = report("inventory", {"source": backup, "documents": inventory})
    chrono = report("chronology", {"inventorySha256": inv})
    rec = report("git-recovery", {
        "source": git, "chronologySha256": chrono, "documents": recovery,
    })
    report("reconciled", {
        "chronologySha256": chrono, "gitRecoverySha256": rec, "documents": assignments,
        "sequences": [{
            "edition": "n5", "factionId": 101,
            "observations": ([
                {"encodedRevisionDate": "2026-11-25", "contents": [{"sha256": first}]},
                {"encodedRevisionDate": "2026-11-26", "contents": [{"sha256": second}]},
            ] if distinct_days else [{
                "encodedRevisionDate": "2026-11-25",
                "contents": [{"sha256": first}, {"sha256": second}],
            }]),
        }],
    })
    manifest = report(f"direct-{snap}", {"snapshot": {
        "archive": {"sha256": snap}, "acquiredAt": acquired,
        "type": "army", "documentCount": 2,
    }})
    index = {
        "format": "InfinityDB historical Army source archive", "formatVersion": 1,
        "completeForSelectedInputs": True, "missingObjects": {},
        "coverage": "incomplete-or-unknown",
        "sourceScope": {"backup": backup, "git": git, "directSnapshots": [{
            "archiveSha256": snap, "manifestSha256": manifest,
            "acquiredAt": acquired, "edition": "n5",
        }]},
        "objects": {sha: len(raw) for sha, raw in objects.items()},
        "evidence": {name: digest(raw) for name, raw in evidence.items()},
        "observations": rows,
        "summary": {
            "sourceObservations": 9, "observationsBySource": {
                "backup-zip": 3, "backup-git": 4, "direct-api": 2,
            },
            "uniqueObjects": 4, "missingObjects": 0,
            "uniqueObjectBytes": sum(map(len, objects.values())),
            "referencedObjectBytes": sum(r["sizeBytes"] for r in rows),
            "unresolvedFactionObservations": 2,
            "uniqueFactionObjects": 3, "uniqueMetadataObjects": 1,
        },
    }
    members = {f"objects/sha256/{sha}.json": raw for sha, raw in objects.items()}
    members.update(evidence)
    return index, members, metadata


def write_archive(path: Path, index, members):
    with ZipFile(path, "w") as archive:
        archive.writestr("index.json", encode(index))
        for name, raw in members.items():
            archive.writestr(name, raw)
    return digest(path.read_bytes())


def test_grouping_context_and_receipt(tmp_path):
    index, members, metadata = fixture()
    archive = tmp_path / "history.zip"
    sha = write_archive(archive, index, members)
    result = read_history(archive, sha)
    assert len(result.groups) == 2
    assert sorted(map(len, result.groups.values())) == [2, 3]
    assert result.unresolved == (4, 5)
    assert result.metadata_contexts[0] == ()
    assert result.metadata_contexts[1] == (metadata,)
    assert result.metadata_contexts[8] == (metadata,)
    assert result.read_object(metadata)["factions"][0]["id"] == 101
    assert result.summary == {
        **index["summary"], "editionFactionSequences": 1, "assignedFactionDateContents": 2,
        "assignedSameDayGroups": 1, "unresolvedEditionContents": 1,
        "metadataContexts": {"gitObservedContext": 3, "directSnapshotContext": 1},
    }
    receipt = tmp_path / "receipt.json"
    value = {
        "format": "InfinityDB historical Army handoff acceptance", "formatVersion": 1,
        "archive": {"sha256": sha, "sourceFormatVersion": 1},
        "sourceScope": index["sourceScope"], "evidence": index["evidence"],
        "summary": {**result.summary}, "coverage": index["coverage"],
    }
    receipt.write_bytes(encode(value))
    verify_receipt(result, receipt, digest(receipt.read_bytes()))
    value["summary"]["assignedSameDayGroups"] = 0
    receipt.write_bytes(encode(value))
    with pytest.raises(ValueError, match="differs"):
        verify_receipt(result, receipt, digest(receipt.read_bytes()))


@pytest.mark.parametrize("failure", [
    "hash", "version", "partial", "missing", "corrupt", "collision", "evidence",
    "assignment", "metadata", "summary", "unreferenced",
])
def test_invalid_source(tmp_path, failure):
    index, members, _ = fixture()
    member = next(iter(members))
    if failure == "version":
        index["formatVersion"] = 2
    elif failure == "partial":
        index["completeForSelectedInputs"] = False
    elif failure == "missing":
        del members[member]
    elif failure == "corrupt":
        members[member] = b"corrupt"
    elif failure == "collision":
        members[member.upper()] = members[member]
    elif failure == "evidence":
        members["evidence/chronology.json"] = b"{}"
    elif failure == "assignment":
        index["observations"][0]["factionId"] = 999
    elif failure == "metadata":
        index["observations"][-1]["metadataSha256"] = "0" * 64
    elif failure == "summary":
        index["summary"]["uniqueObjects"] = 99
    elif failure == "unreferenced":
        raw = b"{}"
        sha = digest(raw)
        index["objects"][sha] = len(raw)
        members[f"objects/sha256/{sha}.json"] = raw
    archive = tmp_path / "history.zip"
    sha = write_archive(archive, index, members)
    with pytest.raises(ValueError):
        read_history(archive, "0" * 64 if failure == "hash" else sha)


def test_characterization_preserves_array_order_and_types():
    first = characterize_faction({"version": "a", "units": [{"id": 1, "move": [10, 15]}]})
    reordered = characterize_faction({"units": [{"move": [10, 15], "id": 1}], "version": "a"})
    revised = characterize_faction({"version": "b", "units": [{"id": 1, "move": [10, 15]}]})
    different = characterize_faction({"version": "a", "units": [{"id": 1, "move": [15, 10]}]})
    typed = characterize_faction({"version": "a", "units": [{"id": 1, "move": [10.0, 15]}]})
    assert compare_content(first, reordered) == "parsedJsonEqual"
    assert compare_content(first, revised) == "revisionFieldOnly"
    assert compare_content(first, different) == "otherContentDifference"
    assert compare_content(first, typed) == "otherContentDifference"


def test_characterization_scopes_numeric_keys_and_flags_renumbering_candidates():
    def unit(identity, name, option_id, option_name):
        return {
            "id": identity, "name": name, "profileGroups": [{
                "id": 1, "profiles": [{"id": 1, "name": name}],
                "options": [{"id": option_id, "name": option_name, "skills": [{"id": 12}]}],
            }],
        }

    old = characterize_faction({"units": [unit(1, "A", 1, "X"), unit(2, "B", 1, "Y")]})
    new = characterize_faction({"units": [unit(1, "A", 3, "X"), unit(2, "C", 1, "Y")]})
    counts = compare_identities(old, new)
    assert not old.issues
    assert old.reference_ids == {"skills": {12}}
    assert counts["unit"]["sharedKeys"] == 2
    assert counts["unit"]["sharedKeyChangedLabel"] == 1
    assert counts["profile"]["sharedKeys"] == 2
    assert counts["loadout"]["uniqueSiblingLabelDifferentKey"] == 1
    assert counts["loadout"]["sharedKeys"] == 1


def test_characterization_does_not_match_duplicate_scoped_keys():
    duplicate = characterize_faction({"units": [{"id": 1}, {"id": 1}]})
    assert duplicate.issues["unit.duplicateScopedId"] == 1
    assert compare_identities(duplicate, duplicate)["unit"] == {"shapeIssueSkippedPairs": 1}


def test_characterization_keeps_same_day_alternatives_unordered(tmp_path):
    index, members, _ = fixture()
    archive = tmp_path / "history.zip"
    source = read_history(archive, write_archive(archive, index, members))
    report = characterize(source)
    n5 = report["editions"]["n5"]
    assert report["archiveSha256"] == source.sha256
    assert n5["uniqueFactionObjects"] == 3
    assert n5["uniqueMetadataObjects"] == 1
    assert n5["unresolvedContents"] == 1
    assert n5["metadataContexts"]["withContext"] == 2
    assert n5["metadataContexts"]["factionIdInEveryContext"] == 2
    assert n5["metadataCatalogs"]["factions"]["distinctIntegerIds"] == 1
    assert n5["unorderedSameDayPairs"] == {"otherContentDifference": 1}
    assert n5["adjacentObservedDateComparisons"] == {}
    assert n5["factionCoverage"][0]["sameDayAlternativeDates"] == 1
    assert n5["factionCoverage"][0]["maximumObservedDateGapDays"] == 0


def test_characterization_compares_distinct_observed_dates(tmp_path):
    index, members, _ = fixture(distinct_days=True)
    archive = tmp_path / "history.zip"
    source = read_history(archive, write_archive(archive, index, members))
    n5 = characterize(source)["editions"]["n5"]
    assert n5["unorderedSameDayPairs"] == {}
    assert n5["adjacentObservedDateComparisons"] == {"otherContentDifference": 1}
    counts = n5["scopedIdentityComparisons"]["unit"]
    assert counts["leftOnlyKeys"] == counts["rightOnlyKeys"] == 1
    assert counts["sharedKeys"] == 0
    assert n5["factionCoverage"][0]["maximumObservedDateGapDays"] == 1
    example = n5["comparisonExamples"]["otherContentDifference"][0]
    assert example["earlierDate"] == "2026-11-25"
    assert example["laterDate"] == "2026-11-26"
