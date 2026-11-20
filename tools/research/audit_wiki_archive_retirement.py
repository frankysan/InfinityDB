"""Compare old/new Wiki archives before retiring an older acquisition.

Checks revision identities, not byte equality (new crawl packaging can differ).
Reports any old historical or current-page revision missing from the new pair.
Read-only; never removes archives or changes curated references.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

REVISION = re.compile(rb'"wgRevisionId"\s*:\s*(\d+)')
PAGE_NAME = re.compile(rb'"wgPageName":"([^"]+)"')
OLDID_PATH = re.compile(r"^_history/oldid/(\d+)\.html$")


def _page_revisions(archive: zipfile.ZipFile) -> set[int]:
    result = set()
    for name in archive.namelist():
        if name.startswith("_history/"):
            continue
        match = REVISION.search(archive.read(name))
        if match:
            result.add(int(match.group(1)))
    return result


def _history_revisions(archive: zipfile.ZipFile) -> dict[int, str]:
    paths = {}
    for name in archive.namelist():
        match = OLDID_PATH.fullmatch(name)
        if match:
            oldid = int(match.group(1))
            if oldid in paths:
                raise ValueError(f"Duplicate oldid {oldid} in {archive.filename}")
            payload = archive.read(name)
            identity = REVISION.search(payload)
            if not identity or int(identity.group(1)) != oldid:
                raise ValueError(f"Invalid historical revision payload: {name}")
            paths[oldid] = name
    if not paths:
        raise ValueError(f"Missing oldid history in {archive.filename}")
    return paths


def compare(old_current: Path, new_current: Path, old_history: Path, new_history: Path) -> dict:
    with (
        zipfile.ZipFile(old_current) as oc,
        zipfile.ZipFile(new_current) as nc,
        zipfile.ZipFile(old_history) as oh,
        zipfile.ZipFile(new_history) as nh,
    ):
        old_pages = _page_revisions(oc)
        new_pages = _page_revisions(nc)
        old_ids = _history_revisions(oh)
        new_ids = _history_revisions(nh)
        missing_history = sorted(old_ids.keys() - new_ids.keys())
        missing_current = sorted(old_pages - (new_pages | new_ids.keys()))
        identity_mismatch = []
        for oldid in old_ids.keys() & new_ids.keys():
            old_title = PAGE_NAME.search(oh.read(old_ids[oldid]))
            new_title = PAGE_NAME.search(nh.read(new_ids[oldid]))
            if not old_title or not new_title or old_title.group(1) != new_title.group(1):
                identity_mismatch.append(oldid)
        identity_mismatch.sort()
    return {
        "oldCurrentRevisions": len(old_pages),
        "newCurrentRevisions": len(new_pages),
        "oldHistoryRevisions": len(old_ids),
        "newHistoryRevisions": len(new_ids),
        "missingHistoryCount": len(missing_history),
        "missingHistoryOldids": missing_history,
        "missingCurrentRevisionCount": len(missing_current),
        "missingCurrentRevisionIds": missing_current,
        "historyIdentityMismatchCount": len(identity_mismatch),
        "historyIdentityMismatchOldids": identity_mismatch,
        "revisionCoverageComplete": not (
            missing_history or missing_current or identity_mismatch
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("old-current", "new-current", "old-history", "new-history"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    report = compare(args.old_current, args.new_current, args.old_history, args.new_history)
    print(json.dumps(report, indent=2))
    if args.json_output:
        if not args.json_output.is_relative_to("local"):
            parser.error("Output must be under local/")
        path = args.json_output
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
    return 0 if report["revisionCoverageComplete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
