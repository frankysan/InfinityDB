"""Compare explicitly selected local Army snapshots with the accepted history corpus.

Read-only intake assessment; not a producer-side acceptance gate.
Legacy manifests are allowed for comparison, not publication.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from infinity_army_data.source_version import army_source_version_date
from infinity_db.army_history_source import digest, document, read_history, require, verify_receipt
from infinity_db.army_snapshot_source import resolve_army_snapshot
from infinity_db.snapshot_provenance import load_snapshot_manifest
from tools.research.build_army_history_database import ARCHIVE_PIN, RECEIPT_PIN


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", nargs="+", type=Path)
    args = parser.parse_args()
    root = Path("local/data")
    source = read_history(root / "history/archive/army-history-v1.zip", ARCHIVE_PIN)
    verify_receipt(source, root / "history/archive/army-history-v1.acceptance.json", RECEIPT_PIN)
    by_day: dict[tuple[str, int, str], set[str]] = defaultdict(set)
    for edition, army, day, sha in source.groups:
        by_day[edition, army, day].add(sha)
    direct = {row["archiveSha256"] for row in source.index["sourceScope"]["directSnapshots"]}
    metadata = {
        sha: source.read_object(sha) for sha in sorted({
            row["sha256"] for row in source.index["observations"] if row["kind"] == "metadata"
        })
    }
    reports = []
    seen: set[str] = set()
    for archive in args.archives:
        manifest = root / "manifests/snapshots" / (archive.stem + ".json")
        pinned = resolve_army_snapshot(
            archive, manifest_directory=manifest.parent, manifest=manifest,
            expected_language="en",
        )
        provenance = load_snapshot_manifest(manifest, archive=archive)
        require(pinned.source_url.rstrip("/") == "https://api.corvusbelli.com/army",
                "Unexpected direct Army source URL")
        sha = provenance["snapshot"]["archive"]["sha256"]
        report: dict[str, Any] = {
            "archive": archive.name, "archiveSha256": sha,
            "manifestVersion": provenance["formatVersion"],
            "alreadyDirect": sha in direct,
            "duplicateSelectedArchive": sha in seen,
            "revisions": pinned.source_revisions,
        }
        seen.add(sha)
        counts: Counter[str] = Counter()
        novel = []
        with ZipFile(archive) as z:
            names = z.namelist()
            require(len(names) == len({name.casefold() for name in names}),
                    "Colliding snapshot members")
            meta_raw = z.read("metadata.json")
            meta_sha = digest(meta_raw)
            meta = document(meta_raw)
            factions = {row["id"] for row in meta["factions"]}
            members: set[int] = set()
            report["metadataAlreadyPresent"] = meta_sha in source.index["objects"]
            report["metadataParsedEquivalent"] = [
                sha for sha, prior in metadata.items() if prior == meta
            ]
            context_counts: Counter[str] = Counter()
            for name in names:
                if name == "metadata.json":
                    continue
                match = re.fullmatch(r"(\d+)-[^/\\]+\.json", name)
                require(match is not None, f"Unexpected member {name}")
                assert match is not None
                army = int(match.group(1))
                require(army not in members, "Duplicate source Army")
                members.add(army)
                raw = z.read(name)
                body = document(raw)
                day = army_source_version_date(body.get("version"))
                require(day is not None, "Unknown encoded revision date")
                assert day is not None
                key = ("n5", army, day.isoformat())
                obj = digest(raw)
                if obj in by_day[key]:
                    status = "exactExistingComparisonInput"
                    refs = {
                        sha for i in source.groups[(*key, obj)]
                        for sha in source.metadata_contexts.get(i, ()) if sha is not None
                    }
                    if not refs:
                        context_counts["noMetadataContext"] += 1
                    elif any(metadata[ref] == meta for ref in refs):
                        context_counts["equivalentContext"] += 1
                    else:
                        context_counts["differentContext"] += 1
                elif not by_day[key]:
                    status = "newArmyDate"
                elif any(source.read_object(prior) == body for prior in by_day[key]):
                    status = "sameDayParsedEquivalent"
                else:
                    status = "distinctSameDayAlternative"
                counts[status] += 1
                if status != "exactExistingComparisonInput":
                    novel.append({"army": army, "date": day.isoformat(), "status": status})
            require(members == factions, "Snapshot faction set differs from metadata")
        report["contextCounts"] = dict(context_counts)
        report["counts"] = dict(counts)
        report["novel"] = novel
        reports.append(report)
    print(json.dumps(reports, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
