"""Read-only candidate audit for replacing older curated Wiki snapshots.

A matching page title or heading is locator evidence, never automatic semantic
acceptance. This bounded research tool does not edit curated rules or archives.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from infinity_db.snapshot_provenance import load_snapshot_manifest
from tools.research.audit_1_0_reference_inputs import (
    PAGE_NAME,
    REVISION_ID,
    _normalized,
    _WikiErrataLabels,
    _WikiHeadings,
    verify_wiki_revisions,
)

ROOT = Path(__file__).resolve().parents[2]
TARGETS = {
    "en": ("WIKI-en 20261116-075926", "WIKI-en-history 20261116-090844"),
    "es": ("WIKI-es 20261116-092640", "WIKI-es-history 20261116-101038"),
}


def _title(value: str) -> str:
    return unicodedata.normalize("NFKC", value).replace(" ", "_").casefold()


def _legacy_title(html: bytes) -> str | None:
    match = PAGE_NAME.search(html.decode("utf-8", "replace"))
    if not match:
        return None
    try:
        title = json.loads('"' + match.group(1) + '"')
    except ValueError:
        return None
    return title if isinstance(title, str) and title else None


def _walk(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for sub in value for item in _walk(sub)]
    if isinstance(value, dict):
        results = [value] if isinstance(value.get("sourceId"), str) else []
        return results + [item for sub in value.values() for item in _walk(sub)]
    return []


def _index_pages(inventory: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    by_title: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in inventory["members"]:
        if record["kind"] != "current-page":
            continue
        titles = {
            record["page"]["title"],
            record.get("sourceIdentity", {}).get("title") or record["page"]["title"],
        }
        for title in titles:
            by_title[_title(title)].append(record)
    return by_title


def _disambiguate_member(
    member: str, candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Require the captured page title AND its original URL path."""
    if len(candidates) <= 1:
        return candidates
    exact = [page for page in candidates if page["path"] == member]
    if exact:
        return exact
    matched = []
    for page in candidates:
        urls = {page["page"]["url"], *page.get("sourceUrls", [])}
        if any(unquote(urlsplit(url).path).lstrip("/") == member for url in urls):
            matched.append(page)
    return matched if matched else candidates


def _headings(html: bytes) -> set[str]:
    decoded = html.decode("utf-8", "replace")
    headings = _WikiHeadings()
    headings.feed(decoded)
    errata = _WikiErrataLabels()
    errata.feed(decoded)
    return headings.headings | errata.labels


def audit(
    root: Path = ROOT, *, archive_targets: dict[str, tuple[str, str]] = TARGETS,
) -> dict[str, Any]:
    curated = sorted((root / "data/curated/rules").glob("*.json"))
    target_pages: dict[str, dict[str, list[dict[str, Any]]]] = {}
    target_manifests: dict[str, dict[str, Any]] = {}
    new_archives: dict[str, zipfile.ZipFile] = {}
    histories: dict[str, zipfile.ZipFile] = {}
    old_archives: dict[str, zipfile.ZipFile] = {}
    results: list[dict[str, Any]] = []
    revisions: list[dict[str, Any]] = []
    try:
        for language, (current, history) in archive_targets.items():
            zip_path = root / "local/data/wiki" / f"{current}.zip"
            manifest = root / "local/data/manifests/snapshots" / f"{current}.json"
            inventory_path = (
                root / "local/data/manifests/snapshots/inventories"
                / f"{current}.inventory.json"
            )
            target_manifests[language] = load_snapshot_manifest(manifest, archive=zip_path)
            inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
            if inventory["snapshot"]["archiveName"] != zip_path.name:
                raise ValueError(f"Inventory/ZIP mismatch: {zip_path}")
            target_pages[language] = _index_pages(inventory)
            new_archives[language] = zipfile.ZipFile(zip_path)
            histories[language] = zipfile.ZipFile(
                root / "local/data/wiki" / f"{history}.zip"
            )

        old_sources: dict[str, dict[str, Any]] = {}
        refs: list[tuple[str, str, dict[str, Any]]] = []
        oldids: dict[str, dict[str, dict[str, str]]] = {"en": {}, "es": {}}
        for path in curated:
            document = json.loads(path.read_text(encoding="utf-8"))
            for source in document.get("sources", []):
                if source.get("kind") != "wiki":
                    continue
                source_id = source["id"]
                if isinstance(source.get("localPath"), str):
                    if source_id in old_sources and source != old_sources[source_id]:
                        raise ValueError(f"Conflicting source declaration: {source_id}")
                    old_sources[source_id] = source
                elif "oldid=" in source.get("url", ""):
                    lang = source.get("language") or (
                        "es" if "/wiki-es/" in source["url"] or "/es/" in source["url"] else "en"
                    )
                    oldids[lang][source_id] = {"id": source_id, "url": source["url"]}
            for item in _walk(document):
                if "member" in item:
                    refs.append((str(path.relative_to(root)), item["sourceId"], item))

        for source_id, source in old_sources.items():
            language = source.get("language")
            if language not in archive_targets:
                raise ValueError(f"Unsupported source language: {source_id}")
            old_path = root / "local/data/wiki" / Path(source["localPath"]).name
            # Snapshot identity must be verified before reading any old members.
            from hashlib import sha256
            if sha256(old_path.read_bytes()).hexdigest() != source["sha256"]:
                raise ValueError(f"Old snapshot is not the declared source: {source_id}")
            old_archives[source_id] = zipfile.ZipFile(old_path)

        cache: dict[tuple[str, str], tuple[str | None, list[dict[str, Any]]]] = {}
        heading_cache: dict[tuple[str, str], set[str]] = {}
        for filename, source_id, reference in refs:
            if source_id not in old_sources:
                continue
            old = old_sources[source_id]
            language = old["language"]
            member = reference["member"]
            key = (source_id, member)
            if key not in cache:
                old_zip = old_archives[source_id]
                title = (
                    _legacy_title(old_zip.read(member))
                    if member in old_zip.namelist() else None
                )
                candidates = target_pages[language].get(_title(title), []) if title else []
                unique = {candidate["path"]: candidate for candidate in candidates}
                cache[key] = (
                    title, _disambiguate_member(member, list(unique.values())),
                )
            title, candidates = cache[key]
            heading = reference.get("heading")
            status = "missing-old-page" if title is None else "unmapped-title"
            new_member = None
            if len(candidates) > 1:
                status = "ambiguous-title"
            elif len(candidates) == 1:
                new_member = candidates[0]["path"]
                if heading:
                    heading_key = (language, new_member)
                    if heading_key not in heading_cache:
                        heading_cache[heading_key] = _headings(
                            new_archives[language].read(new_member)
                        )
                    status = (
                        "heading-present"
                        if _normalized(heading) in heading_cache[heading_key]
                        else "heading-missing"
                    )
                else:
                    status = "member-resolved-no-heading"
            old_match = REVISION_ID.search(
                old_archives[source_id].read(member).decode("utf-8", "replace")
            )
            new_match = (
                REVISION_ID.search(
                    new_archives[language].read(new_member).decode("utf-8", "replace")
                ) if new_member else None
            )
            revision_status = (
                "unknown" if not old_match or not new_match
                else "same" if old_match.group(1) == new_match.group(1)
                else "changed"
            )
            results.append({
                "collection": filename,
                "sourceId": source_id,
                "oldMember": member,
                "sourceTitle": title,
                "newMember": new_member,
                "heading": heading,
                "status": status,
                "oldRevision": int(old_match.group(1)) if old_match else None,
                "newRevision": int(new_match.group(1)) if new_match else None,
                "revisionStatus": revision_status,
            })

        for language, sources in oldids.items():
            revisions.extend(
                {"language": language, **record}
                for record in verify_wiki_revisions(histories[language], list(sources.values()))
            )
    finally:
        for archive in (*new_archives.values(), *old_archives.values(), *histories.values()):
            archive.close()

    return {
        "snapshots": {
            lang: {
                "sourceId": "wiki-" + lang + "-" + archive_targets[lang][0].split(" ", 1)[1],
                "archiveSha256": doc["snapshot"]["archive"]["sha256"],
                "documentCount": doc["snapshot"]["documentCount"],
                "acquiredAt": doc["snapshot"]["acquiredAt"],
            }
            for lang, doc in target_manifests.items()
        },
        "sourceDeclarations": sorted(old_sources),
        "citationCounts": dict(sorted(Counter(item["status"] for item in results).items())),
        "currentRevisionCounts": dict(sorted(
            Counter(item["revisionStatus"] for item in results).items()
        )),
        "historicalRevisionCounts": dict(sorted(
            Counter(item["status"] for item in revisions).items()
        )),
        "citations": results,
        "historicalRevisions": revisions,
    }


def migration_patch(
    root: Path, report: dict[str, Any], *,
    archive_targets: dict[str, tuple[str, str]] = TARGETS,
) -> str:
    """Create a Git diff preserving exact curated JSON whitespace."""
    import difflib
    import re

    if any(item["status"] != "heading-present" or item["revisionStatus"] != "same"
           for item in report["citations"]):
        raise ValueError("Unresolved or changed Wiki citation")
    if any(item["status"] != "exact-revision-payload"
           for item in report["historicalRevisions"]):
        raise ValueError("Unverified historical oldid")
    targets = {
        old: report["snapshots"]["es" if old.startswith("wiki-es-") else "en"]
        for old in report["sourceDeclarations"]
    }
    members: dict[tuple[str, str], str] = {}
    for item in report["citations"]:
        key = item["sourceId"], item["oldMember"]
        if key in members and members[key] != item["newMember"]:
            raise ValueError(f"Conflicting new locator: {key}")
        members[key] = item["newMember"]

    def change_field(block: str, field: str, old: Any, new: Any) -> str:
        needle = f'"{field}": ' + json.dumps(old, ensure_ascii=False)
        replacement = f'"{field}": ' + json.dumps(new, ensure_ascii=False)
        if block.count(needle) != 1:
            raise ValueError(f"Unrecognized field layout: {field}={old!r}")
        return block.replace(needle, replacement, 1)

    source_count = 0
    citation_count = 0

    def change_object(match: Any) -> str:
        nonlocal source_count, citation_count
        original = match.group()
        try:
            obj = json.loads(original)
        except ValueError:
            return original
        if not isinstance(obj, dict):
            return original
        old_id = obj.get("sourceId")
        if isinstance(old_id, str) and old_id in targets:
            member = obj.get("member")
            if not isinstance(member, str):
                raise ValueError(f"Missing Wiki citation member: {old_id}")
            key = old_id, member
            if key not in members:
                raise ValueError(f"Unmapped Wiki reference: {key}")
            new = change_field(original, "sourceId", old_id, targets[old_id]["sourceId"])
            citation_count += 1
            return change_field(new, "member", member, members[key])
        old_id = obj.get("id")
        if old_id in targets and obj.get("kind") == "wiki":
            target = targets[old_id]
            name = archive_targets[obj["language"]][0]
            changed = original
            replacements = {
                "id": target["sourceId"],
                "version": name.split(" ", 1)[1],
                "acquiredAt": target["acquiredAt"],
                "localPath": "data/wiki/" + name + ".zip",
                "sha256": target["archiveSha256"],
                "documentCount": target["documentCount"],
            }
            for field, value in replacements.items():
                changed = change_field(changed, field, obj[field], value)
            source_count += 1
            return changed
        return original

    patches = []
    for path in sorted((root / "data/curated/rules").glob("*.json")):
        before = path.read_text(encoding="utf-8")
        if not any(old in before for old in targets):
            continue
        after = re.sub(r"\{[^{}]*\}", change_object, before, flags=re.DOTALL)
        if any(old in after for old in targets):
            leftovers = [
                (i + 1, line.strip()[:120])
                for i, line in enumerate(after.splitlines())
                if any(old in line for old in targets)
            ]
            raise ValueError(f"Unmigrated source ID in {path}: {len(leftovers)} {leftovers[:8]}")
        json.loads(after)
        relative = path.relative_to(root).as_posix()
        diff = "".join(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile="a/" + relative, tofile="b/" + relative,
        ))
        if not diff:
            raise ValueError(f"No resulting changes in {relative}")
        patches.append(f"diff --git a/{relative} b/{relative}\n" + diff)
    if citation_count != len(report["citations"]):
        raise ValueError(f"Mapped {citation_count} of {len(report['citations'])} citations")
    if source_count < len(targets) or not patches:
        raise ValueError(f"Incomplete curated Wiki source declarations: {source_count}")
    return "".join(patches)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for language in ("en", "es"):
        for kind, index in (("current", 0), ("history", 1)):
            parser.add_argument(
                f"--{language}-{kind}", default=TARGETS[language][index],
                help="Exact new archive stem without .zip",
            )
    parser.add_argument("--json-output", type=Path, help="New private report path; never overwrite")
    parser.add_argument("--patch-output", type=Path, help="New private Git diff; never overwrite")
    args = parser.parse_args()
    archive_targets = {}
    for language in ("en", "es"):
        current = getattr(args, f"{language}_current")
        history = getattr(args, f"{language}_history")
        for stem, label in ((current, language), (history, f"{language}-history")):
            if not re.fullmatch(r"WIKI-" + label + r" [0-9]{8}-[0-9]{6}", stem):
                parser.error(f"Invalid {label} Wiki archive stem: {stem}")
        archive_targets[language] = (current, history)
    result = audit(archive_targets=archive_targets)
    print(f"Old curated Wiki source declarations: {len(result['sourceDeclarations'])}")
    print(f"Curated Wiki citations: {len(result['citations'])}")
    print(f"Citation resolution: {result['citationCounts']}")
    print(f"Current-page revisions: {result['currentRevisionCounts']}")
    print(f"Historical oldid checks: {result['historicalRevisionCounts']}")
    unresolved = [
        item for item in result["citations"]
        if item["status"] not in {"heading-present", "member-resolved-no-heading"}
    ]
    for item in unresolved[:35]:
        print(
            f"  {item['status']}: {item['sourceId']} "
            f"{item['oldMember']} -> {item['newMember']} "
            f"(heading={item['heading']!r})"
        )
    if args.json_output:
        if not args.json_output.is_relative_to(Path("local/")):
            parser.error("Report path must be under local/")
        output = ROOT / args.json_output
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        print(f"Full candidate report: {args.json_output}")
    if args.patch_output:
        if not args.patch_output.is_relative_to(Path("local/")):
            parser.error("Patch path must be under local/")
        output = ROOT / args.patch_output
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            stream.write(migration_patch(ROOT, result, archive_targets=archive_targets))
        print(f"Reviewed-locator migration patch: {args.patch_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
