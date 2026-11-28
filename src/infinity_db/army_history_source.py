"""Independent, offline consumer for pinned historical Army source archives."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

from infinity_army_data.source_version import army_source_version_date

FORMAT = "InfinityDB historical Army source archive"
HEX = re.compile(r"[0-9a-f]{64}")
Document = dict[str, Any]
GroupKey = tuple[str, int, str, str]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def file_digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def object_member(sha: str) -> str:
    require(isinstance(sha, str) and HEX.fullmatch(sha) is not None, "Invalid object identity")
    return f"objects/sha256/{sha}.json"


def document(raw: bytes) -> Document:
    data = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object")
    return data


@dataclass
class HistoricalArmySource:
    """Groups contain observation indices, not inferred logical Unit identities.

    Metadata references align with Git appearances or a direct observation.
    Empty tuples mean no contextual link; None means a missing Git context.
    Same-day keys are sorted for reproducibility, not publication order.
    """

    archive: Path
    sha256: str
    index: Document
    evidence: dict[str, Document]
    groups: dict[GroupKey, tuple[int, ...]]
    unresolved: tuple[int, ...]
    metadata_contexts: dict[int, tuple[str | None, ...]]
    summary: Document

    def read_object(self, sha: str) -> Document:
        require(sha in self.index["objects"], "Unknown historical object")
        with ZipFile(self.archive) as archive:
            raw = archive.read(object_member(sha))
        require(
            len(raw) == self.index["objects"][sha] and digest(raw) == sha,
            "Historical object changed",
        )
        return document(raw)


def _evidence(
    archive: ZipFile, index: Document, names: set[str],
) -> dict[str, Document]:
    scope = index["sourceScope"]
    direct = {s["archiveSha256"]: s for s in scope["directSnapshots"]}
    require(len(direct) == len(scope["directSnapshots"]), "Duplicate direct source")
    required = {f"evidence/{name}.json" for name in (
        "inventory", "chronology", "git-recovery", "reconciled",
    )}
    required.update(f"evidence/direct-{sha}.json" for sha in direct)
    hashes = index["evidence"]
    require(set(hashes) == required, "Unexpected evidence set")
    require(
        names == {"index.json"} | required | {object_member(s) for s in index["objects"]},
        "Unexpected archive member set",
    )
    evidence = {}
    for name, sha in hashes.items():
        raw = archive.read(name)
        require(digest(raw) == sha, f"Evidence hash mismatch: {name}")
        evidence[name] = document(raw)
    inventory = evidence["evidence/inventory.json"]
    chronology = evidence["evidence/chronology.json"]
    recovery = evidence["evidence/git-recovery.json"]
    reconciled = evidence["evidence/reconciled.json"]
    require(
        chronology["inventorySha256"] == hashes["evidence/inventory.json"]
        and recovery["chronologySha256"] == hashes["evidence/chronology.json"]
        and reconciled["chronologySha256"] == hashes["evidence/chronology.json"]
        and reconciled["gitRecoverySha256"] == hashes["evidence/git-recovery.json"]
        and scope["backup"] == inventory["source"]
        and scope["git"] == recovery["source"],
        "Historical evidence linkage mismatch",
    )
    for sha, snapshot in direct.items():
        object_member(sha)
        name = f"evidence/direct-{sha}.json"
        manifest = evidence[name]["snapshot"]
        require(
            hashes[name] == snapshot["manifestSha256"]
            and manifest["archive"]["sha256"] == sha
            and manifest["acquiredAt"] == snapshot["acquiredAt"]
            and manifest["type"] == "army",
            "Direct snapshot evidence mismatch",
        )
    return evidence


def _relative_member(row: Document) -> str:
    parts = row["member"].split("/")
    return "/".join(parts if parts[0] == row["edition"] else parts[1:])


def _assignment(row: Document) -> tuple[Any, ...]:
    return row["sha256"], row["factionId"], row["identityStatus"]


def _inventory(
    archive: Path, sha: str, index: Document, evidence: dict[str, Document],
    revisions: dict[str, str | None],
) -> HistoricalArmySource:
    rows = index["observations"]
    objects = index["objects"]
    scope = index["sourceScope"]
    inventory = {r["member"]: r for r in evidence["evidence/inventory.json"]["documents"]}
    recovery = {
        (r["path"], r["blob"]): r
        for r in evidence["evidence/git-recovery.json"]["documents"]
    }
    reconciled = evidence["evidence/reconciled.json"]
    by_member = {r["member"]: r for r in reconciled["documents"]}
    by_git = {
        (_relative_member(r), r["sha256"], r["edition"]): r
        for r in reconciled["documents"] if r.get("gitBlob")
    }
    snapshots = {r["archiveSha256"]: r for r in scope["directSnapshots"]}
    seen_zip: set[str] = set()
    seen_git: set[tuple[str, str]] = set()
    seen_direct: dict[str, set[str]] = defaultdict(set)
    metadata_git: dict[tuple[str, str], set[str]] = defaultdict(set)
    metadata_direct: dict[str, set[str]] = defaultdict(set)
    groups: dict[GroupKey, list[int]] = defaultdict(list)
    unresolved: list[int] = []
    kinds: dict[str, set[str]] = defaultdict(set)
    sources: Counter[str] = Counter()
    for i, row in enumerate(rows):
        edition, kind, obj = row["edition"], row["kind"], row["sha256"]
        source = row["sourceType"]
        require(
            edition in {"n4", "n5", "codeone"} and kind in {"faction", "metadata"},
            "Invalid observation kind or edition",
        )
        require(obj in objects and row["sizeBytes"] == objects[obj], "Invalid object reference")
        kinds[kind].add(obj)
        sources[source] += 1
        assignment = None
        if source == "backup-zip":
            member = row["member"]
            original = inventory[member]
            require(
                member not in seen_zip
                and row["sourceArchiveSha256"] == scope["backup"]["archiveSha256"]
                and all(row.get(k) == v for k, v in original.items()),
                "Backup ZIP reference mismatch",
            )
            seen_zip.add(member)
            assignment = by_member.get(member)
        elif source == "backup-git":
            key = (row["path"], row["blob"])
            original = recovery[key]
            require(
                key not in seen_git and row["sourceTipCommit"] == scope["git"]["tipCommit"]
                and all(row.get(k) == v for k, v in original.items() if k != "factions"),
                "Git reference mismatch",
            )
            seen_git.add(key)
            assignment = by_git.get((row["path"], obj, edition))
            if kind == "metadata":
                metadata_git[(edition, row["blob"])].add(obj)
        elif source == "direct-api":
            snapshot = row["sourceArchiveSha256"]
            require(
                snapshot in snapshots and edition == snapshots[snapshot]["edition"]
                and row["acquiredAt"] == snapshots[snapshot]["acquiredAt"]
                and row["member"] not in seen_direct[snapshot],
                "Direct observation reference mismatch",
            )
            seen_direct[snapshot].add(row["member"])
            if kind == "metadata":
                require(row["member"] == "metadata.json", "Invalid direct metadata member")
                metadata_direct[snapshot].add(obj)
        else:
            raise ValueError("Unknown historical source type")
        if kind == "metadata":
            require(row["factionId"] is None and revisions[obj] is None, "Invalid metadata")
            continue
        day = army_source_version_date(revisions[obj])
        if day is None or row["sourceRevision"] != revisions[obj]:
            raise ValueError("Invalid historical faction revision")
        require(row["encodedRevisionDate"] == day.isoformat(), "Invalid revision date")
        require(not row.get("issues"), "Invalid source faction document")
        faction = row["factionId"]
        require(faction is None or type(faction) is int, "Invalid source faction ID")
        if source == "direct-api":
            require(
                faction is not None and row["identityStatus"] == "direct-endpoint",
                "Invalid direct faction identity",
            )
        elif assignment is not None:
            require(
                _assignment(row) == _assignment(assignment)
                and (source != "backup-git" or row["blob"] == assignment["gitBlob"]),
                "Historical faction assignment mismatch",
            )
        else:
            require(source == "backup-git" and faction is None, "Unreviewed faction identity")
        if faction is None:
            unresolved.append(i)
        else:
            groups[(edition, faction, day.isoformat(), obj)].append(i)

    require(seen_zip == set(inventory) and seen_git == set(recovery), "Missing source observations")
    require(
        set(seen_direct) == set(snapshots) and set(objects) == kinds["faction"] | kinds["metadata"]
        and not (kinds["faction"] & kinds["metadata"]),
        "Incomplete object or snapshot references",
    )
    for snapshot, members in seen_direct.items():
        manifest = evidence[f"evidence/direct-{snapshot}.json"]["snapshot"]
        require(len(members) == manifest["documentCount"], "Direct document count mismatch")

    contexts: dict[int, tuple[str | None, ...]] = {}
    counts: Counter[str] = Counter()
    for i, row in enumerate(rows):
        if row["kind"] != "faction":
            continue
        if row["sourceType"] == "backup-git":
            refs: list[str | None] = []
            for appearance in row["appearances"]:
                blob = appearance["metadataBlob"]
                if blob is None:
                    refs.append(None)
                    counts["gitMissingContext"] += 1
                else:
                    candidates = metadata_git[(row["edition"], blob)]
                    require(len(candidates) == 1, "Missing or ambiguous Git metadata")
                    refs.append(next(iter(candidates)))
                    counts["gitObservedContext"] += 1
            contexts[i] = tuple(refs)
        elif row["sourceType"] == "direct-api":
            obj = row["metadataSha256"]
            require(
                metadata_direct[row["sourceArchiveSha256"]] == {obj},
                "Direct metadata reference mismatch",
            )
            contexts[i] = (obj,)
            counts["directSnapshotContext"] += 1
        else:
            contexts[i] = ()

    for sequence in reconciled["sequences"]:
        for occurrence in sequence["observations"]:
            for content in occurrence["contents"]:
                require(
                    (sequence["edition"], sequence["factionId"],
                     occurrence["encodedRevisionDate"], content["sha256"]) in groups,
                    "Unknown reconciled sequence content",
                )
    summary = {
        "sourceObservations": len(rows), "observationsBySource": dict(sources),
        "uniqueObjects": len(objects), "missingObjects": 0,
        "uniqueObjectBytes": sum(objects.values()),
        "referencedObjectBytes": sum(r["sizeBytes"] for r in rows),
        "unresolvedFactionObservations": len(unresolved),
        "uniqueFactionObjects": len(kinds["faction"]),
        "uniqueMetadataObjects": len(kinds["metadata"]),
    }
    require(summary == index["summary"], "Archive summary mismatch")
    days = Counter(key[:3] for key in groups)
    summary.update(
        editionFactionSequences=len({key[:2] for key in groups}),
        assignedFactionDateContents=len(groups),
        assignedSameDayGroups=sum(n > 1 for n in days.values()),
        unresolvedEditionContents=len({
            (rows[i]["edition"], rows[i]["sha256"]) for i in unresolved
        }),
        metadataContexts=dict(counts),
    )
    return HistoricalArmySource(
        archive, sha, index, evidence, {key: tuple(groups[key]) for key in sorted(groups)},
        tuple(unresolved), contexts, summary,
    )


def read_history(archive: Path, expected_sha256: str) -> HistoricalArmySource:
    """Verify selected bytes and evidence independently of current Army snapshots."""
    require(
        HEX.fullmatch(expected_sha256) is not None and file_digest(archive) == expected_sha256,
        "Historical archive SHA-256 mismatch",
    )
    try:
        with ZipFile(archive) as source:
            names = source.namelist()
            require(len(names) == len({n.casefold() for n in names}), "Colliding archive members")
            index = document(source.read("index.json"))
            require(
                index.get("format") == FORMAT and type(index.get("formatVersion")) is int
                and index["formatVersion"] == 1,
                "Unsupported historical archive format",
            )
            require(
                index["completeForSelectedInputs"] is True and index["missingObjects"] == {},
                "Incomplete historical archive",
            )
            evidence = _evidence(source, index, set(names))
            revisions: dict[str, str | None] = {}
            git_blobs: dict[str, set[str]] = defaultdict(set)
            for observation in index["observations"]:
                if observation["sourceType"] == "backup-git":
                    git_blobs[observation["sha256"]].add(observation["blob"])
            for sha, size in index["objects"].items():
                raw = source.read(object_member(sha))
                require(
                    type(size) is int and len(raw) == size and digest(raw) == sha,
                    f"Invalid archived object: {sha}",
                )
                for blob in git_blobs[sha]:
                    require(
                        re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", blob) is not None,
                        "Invalid Git blob identity",
                    )
                    algorithm = "sha1" if len(blob) == 40 else "sha256"
                    framed = f"blob {len(raw)}\0".encode("ascii") + raw
                    require(
                        hashlib.new(algorithm, framed, usedforsecurity=False).hexdigest() == blob,
                        "Git blob identity mismatch",
                    )
                data = document(raw)
                if isinstance(data.get("units"), list):
                    version = data.get("version")
                    if not isinstance(version, str):
                        raise ValueError("Missing faction source revision")
                    revisions[sha] = version
                elif isinstance(data.get("factions"), list):
                    revisions[sha] = None
                else:
                    raise ValueError("Invalid historical document shape")
            result = _inventory(archive, expected_sha256, index, evidence, revisions)
    except (KeyError, TypeError, AttributeError, BadZipFile) as exc:
        raise ValueError(f"Malformed historical archive: {exc}") from exc
    require(file_digest(archive) == expected_sha256, "Archive changed during verification")
    return result


def verify_receipt(source: HistoricalArmySource, receipt: Path, expected_sha256: str) -> None:
    raw = receipt.read_bytes()
    require(digest(raw) == expected_sha256, "Producer receipt SHA-256 mismatch")
    value = document(raw)
    require(
        value.get("format") == "InfinityDB historical Army handoff acceptance"
        and value.get("formatVersion") == 1
        and value["archive"]["sha256"] == source.sha256
        and value["archive"]["sourceFormatVersion"] == 1
        and value["sourceScope"] == source.index["sourceScope"]
        and value["evidence"] == source.index["evidence"]
        and value["summary"] == source.summary
        and value["coverage"] == source.index["coverage"],
        "Producer receipt differs from independent consumer results",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--receipt-sha256", required=True)
    args = parser.parse_args()
    try:
        source = read_history(args.archive, args.sha256)
        verify_receipt(source, args.receipt, args.receipt_sha256)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Historical consumer acceptance: FAIL: {exc}\n")
    print(json.dumps(source.summary, indent=2, sort_keys=True))
    print("Historical consumer acceptance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
