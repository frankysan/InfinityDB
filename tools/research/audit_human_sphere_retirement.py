"""Compare immutable Human Sphere current-page snapshots before retiring an older ZIP.

Revision IDs establish whether old captured page revisions survive in the new
current-page capture. This does not prove identical HTML or source semantics;
changed revisions and missing assets require review. No files are removed.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from infinity_db.snapshot_provenance import load_snapshot_manifest

ROOT = Path(__file__).resolve().parents[2]
STEM = re.compile(r"HUMAN-SPHERE \d{8}-\d{6}\Z")
PAGE_NAME = re.compile(rb'"wgPageName"\s*:\s*"((?:\\.|[^"\\])*)"')
ARTICLE_ID = re.compile(rb'"wgArticleId"\s*:\s*(\d+)')
REVISION_ID = re.compile(rb'"wgRevisionId"\s*:\s*(\d+)')


def _page_record(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> dict[str, Any] | None:
    # Legacy MediaWiki file-description pages have names like File_Example.jpg
    # despite containing HTML. Only skip physical assets beneath images/.
    if info.filename.startswith("images/") or info.file_size == 0:
        return None
    with archive.open(info) as stream:
        header = stream.read(65536)
    if b"<html" not in header[:2048].lower():
        return None
    title_match = PAGE_NAME.search(header)
    if not title_match:
        return None
    title = json.loads(b'"' + title_match.group(1) + b'"')
    article = ARTICLE_ID.search(header)
    revision = REVISION_ID.search(header)
    return {
        "member": info.filename,
        "title": title,
        "articleId": int(article.group(1)) if article else None,
        "revisionId": int(revision.group(1)) if revision else None,
    }


def _pages(archive: zipfile.ZipFile) -> list[dict[str, Any]]:
    return [record for info in archive.infolist()
            if not info.is_dir() and (record := _page_record(archive, info)) is not None]


def compare(old_archive: Path, new_archive: Path) -> dict[str, Any]:
    """Compare page identity/revisions and exact member coverage; no writes."""
    with zipfile.ZipFile(old_archive) as old, zipfile.ZipFile(new_archive) as new:
        old_pages = _pages(old)
        new_pages = _pages(new)
        by_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
        by_title: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for page in new_pages:
            if page["articleId"] is not None and page["articleId"] > 0:
                by_id[page["articleId"]].append(page)
            by_title[page["title"].casefold()].append(page)

        counts: Counter[str] = Counter()
        unresolved = []
        for page in old_pages:
            identifier = page["articleId"]
            candidates = (
                by_id.get(identifier, [])
                if identifier is not None and identifier > 0 else []
            )
            if not candidates:
                candidates = [candidate for candidate in by_title[page["title"].casefold()]
                              if identifier is None or candidate["articleId"] in (None, identifier)]
            same_title = [candidate for candidate in candidates
                          if candidate["title"].casefold() == page["title"].casefold()]
            old_revision = page["revisionId"]
            if not candidates:
                status = "missing-page"
            elif not same_title:
                status = "title-changed"
            elif not old_revision or not any(candidate["revisionId"] for candidate in same_title):
                status = "unverified-revision"
            elif any(candidate["revisionId"] == old_revision for candidate in same_title):
                status = "revision-preserved"
            else:
                status = "revision-changed"
            counts[status] += 1
            if status != "revision-preserved":
                unresolved.append({
                    **page,
                    "status": status,
                    "candidateMembers": sorted(
                        candidate["member"] for candidate in candidates
                    )[:20],
                    "candidateRevisions": sorted({
                        candidate["revisionId"] for candidate in candidates
                        if candidate["revisionId"] is not None
                    }),
                    "candidateTitles": sorted({candidate["title"] for candidate in candidates}),
                })

        old_names = {info.filename for info in old.infolist() if not info.is_dir()}
        new_names = {info.filename for info in new.infolist() if not info.is_dir()}
        old_page_names = {page["member"] for page in old_pages}
        old_assets = old_names - old_page_names
        missing_assets = sorted(old_assets - new_names)
        complete = not unresolved and not missing_assets
        return {
            "oldArchive": old_archive.name,
            "newArchive": new_archive.name,
            "oldMemberCount": len(old_names),
            "newMemberCount": len(new_names),
            "oldPageCaptureCount": len(old_pages),
            "newPageCaptureCount": len(new_pages),
            "pageStatusCounts": dict(sorted(counts.items())),
            "unresolvedPages": unresolved,
            "oldNonPageMemberCount": len(old_assets),
            "missingNonPageMemberCount": len(missing_assets),
            "missingNonPageMembers": missing_assets,
            "strictCoverageComplete": complete,
            "note": (
                "Matching MediaWiki page/revision IDs do not prove identical HTML. "
                "Missing non-page paths may be renamed assets; review before retirement."
            ),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", required=True, help="September archive stem, without .zip")
    parser.add_argument("--new", required=True, help="New archive stem, without .zip")
    parser.add_argument("--json-output", type=Path, help="New report path below local/")
    args = parser.parse_args()
    if not all(STEM.fullmatch(value) for value in (args.old, args.new)) or args.old >= args.new:
        parser.error("Expected chronological HUMAN-SPHERE YYYYMMDD-HHMMSS archive stems")
    if args.json_output and (args.json_output.is_absolute() or ".." in args.json_output.parts
                             or not args.json_output.is_relative_to("local")):
        parser.error("Report must be a new relative path under local/")
    roots = [ROOT / "local/data/wiki" / f"{stem}.zip" for stem in (args.old, args.new)]
    manifests = [ROOT / "local/data/manifests/snapshots" / f"{stem}.json"
                 for stem in (args.old, args.new)]
    for archive, manifest in zip(roots, manifests, strict=True):
        print(f"Validating provenance and all content: {archive.name}", flush=True)
        document = load_snapshot_manifest(manifest, archive=archive)
        if document["snapshot"]["type"] != "wiki" or document["source"]["url"] != "https://www.human-sphere.com/Main_Page":
            raise ValueError(f"Not a Human Sphere Wiki provenance manifest: {manifest}")
    print("Comparing page revisions and member paths", flush=True)
    report = compare(*roots)
    print(json.dumps({key: value for key, value in report.items()
                      if key not in {"unresolvedPages", "missingNonPageMembers"}}, indent=2))
    for page in report["unresolvedPages"][:15]:
        print(
            f"  {page['status']}: {page['member']} "
            f"oldid={page['revisionId']} -> {page['candidateRevisions']}"
        )
    if args.json_output:
        target = ROOT / args.json_output
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        print(f"Full report: {args.json_output}")
    return 0 if report["strictCoverageComplete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
