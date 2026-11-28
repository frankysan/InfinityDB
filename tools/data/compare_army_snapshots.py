"""Generate an offline, source-pinned comparison of two Army snapshots."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

from infinity_army_data.merge import decode_document, parse_source_name
from infinity_db.army_history_catalogs import catalog_rows, classify
from infinity_db.army_history_pilot import (
    MISSING,
    catalog_index,
    collect_references,
    compare_catalog_contexts,
    compare_faction,
    recorded,
    same,
)
from infinity_db.army_history_references import CATALOGS
from infinity_db.army_history_source import Document, digest, document
from infinity_db.army_snapshot_source import resolve_army_snapshot
from infinity_db.snapshot_provenance import load_snapshot_manifest, sha256_file
from tools.research.summarize_army_history import (
    comparable_relationships,
    effective,
    effective_delta,
    same_labels,
    stable_context,
)

REPORT_DIRECTORY = Path("local/data/reports/army-snapshot-diffs")
REPRESENTATION = frozenset({
    "sourceRevisionField", "referenceDisplayOrderOnly", "sharedChildOrderChanged",
    "peripheralDefinitionEquivalentRekey",
})


def read_snapshot(archive: Path, manifest: Path) -> tuple[Document, dict[str, Document]]:
    """Verify provenance before decoding the exact selected ZIP members."""
    result = resolve_army_snapshot(
        archive, manifest_directory=manifest.parent, manifest=manifest,
    )
    manifest_sha = sha256_file(manifest)
    provenance = load_snapshot_manifest(manifest, archive=archive)
    documents = {}
    members = {}
    faction_ids: set[int] = set()
    with ZipFile(archive) as source:
        for name in sorted(source.namelist()):
            if name.endswith("/") or not name.lower().endswith(".json"):
                continue
            if name in documents:
                raise ValueError(f"Duplicate Army snapshot member: {name}")
            raw = source.read(name)
            data = document(raw) if name == "metadata.json" else decode_document(raw, name)
            documents[name] = data
            member: Document = {"sha256": digest(raw), "sourceRevision": data.get("version")}
            if name != "metadata.json":
                identity = parse_source_name(name)
                if identity is None or identity[0] in faction_ids:
                    raise ValueError(f"Invalid or duplicate Army list identity: {name}")
                faction_ids.add(identity[0])
                member.update({"factionId": identity[0], "slug": identity[1]})
            members[name] = member
    # Recheck the archive after reading, rather than publishing mixed evidence.
    if (load_snapshot_manifest(manifest, archive=archive) != provenance
            or sha256_file(manifest) != manifest_sha):
        raise ValueError("Snapshot provenance changed during comparison")
    snapshot = provenance["snapshot"]
    return {
        "manifestFormatVersion": provenance["formatVersion"],
        "manifestSha256": manifest_sha,
        "archiveName": snapshot["archive"]["name"],
        "archiveSha256": snapshot["archive"]["sha256"],
        "contentSha256": snapshot.get("contentSha256"),
        "acquiredAt": snapshot["acquiredAt"],
        "source": provenance["source"],
        "sourceRevisions": result.source_revisions,
        "members": members,
    }, documents


def metadata_changes(old: Document, new: Document) -> list[Document]:
    """Use the historical catalog classifier without guessing weapon-mode pairing."""
    changes = []
    for field in sorted(old.keys() | new.keys()):
        a, b = old.get(field, MISSING), new.get(field, MISSING)
        if same(a, b):
            continue
        if all(
            isinstance(value, list) and all(
                isinstance(row, dict) and type(row.get("id")) is int for row in value
            )
            for value in (a, b)
        ):
            left = catalog_rows(old, field, local=False)
            right = catalog_rows(new, field, local=False)
            for identity in sorted(left.keys() | right.keys()):
                before, after = left.get(identity, MISSING), right.get(identity, MISSING)
                if same(before, after):
                    continue
                if identity not in left:
                    category = "observedKeyAppearance"
                elif identity not in right:
                    category = "observedKeyDisappearance"
                else:
                    category = classify(field, "metadata", left[identity], right[identity])
                changes.append({
                    "path": [field, identity], "category": category,
                    "before": recorded(before), "after": recorded(after),
                })
            if same(left, right):
                changes.append({
                    "path": [field], "category": "catalogRecordOrderOnly",
                    "before": recorded(a), "after": recorded(b),
                })
        else:
            changes.append({
                "path": [field], "category": "metadataFieldReview",
                "before": recorded(a), "after": recorded(b),
            })
    for change in changes:
        category = change["category"]
        change["classification"] = (
            "representation" if category == "catalogRecordOrderOnly" else
            "gameplayCandidate" if category == "weaponMechanicsCandidate" else "review"
        )
    return changes


def effective_changes(
    old: Document, new: Document, changes: list[Document],
    left_context: list[dict[str, dict[int, tuple[str, ...]]]],
    right_context: list[dict[str, dict[int, tuple[str, ...]]]],
) -> list[Document]:
    """Compare effective reference occurrences in stable single-profile groups.

    Source differences remain separate, including changes to catalog definitions.
    Missing, rekeyed, disabled and ambiguous owners are never silently paired.
    """
    targets = {
        (path[1], path[3], path[-1])
        for change in changes
        for path in [change["path"]]
        if len(path) == 7 and path[0] == "units" and path[2] == "profileGroups"
        and path[4] in {"profiles", "options"} and path[-1] in CATALOGS
    }
    results: list[Document] = []
    for unit, group, field in sorted(targets):
        scope = {"unitId": unit, "groupId": group, "field": field}
        context, reason = stable_context(
            old, new, unit, group, allow_stable_relationships=True,
        )
        if context is None:
            results.append({**scope, "category": "effectiveReview", "reason": reason})
            continue
        pa, oa, pb, ob = context
        if oa.keys() != ob.keys():
            results.append({
                **scope, "category": "effectiveReview", "reason": "changedLoadoutKeys",
                "beforeLoadoutIds": sorted(oa), "afterLoadoutIds": sorted(ob),
            })
        for identity in sorted(oa.keys() & ob.keys()):
            owner = {**scope, "profileId": pa["id"], "loadoutId": identity}
            a, b = oa[identity], ob[identity]
            if (a.get("disabled") or b.get("disabled") or not same_labels(a, b)
                    or not comparable_relationships(a, b, old, new, unit, True)):
                results.append({
                    **owner, "category": "effectiveReview", "reason": "unstableLoadout",
                })
                continue
            before, status_a = effective(pa, a, field, old, left_context)
            after, status_b = effective(pb, b, field, new, right_context)
            if before is None or after is None:
                results.append({
                    **owner, "category": "effectiveReview",
                    "reason": status_a if before is None else status_b,
                })
                continue
            delta = effective_delta(before, after)
            results.append({
                **owner,
                "category": (
                    "effectiveOccurrenceChange" if delta["lost"] or delta["gained"]
                    else "effectiveOccurrenceEquivalent"
                ),
                **delta,
            })
    return results


def compare_documents(
    before: dict[str, Document], after: dict[str, Document],
) -> Document:
    """Compare explicit endpoints, retaining source-member and record coordinates."""
    old_meta, new_meta = before["metadata.json"], after["metadata.json"]
    old_context, new_context = [catalog_index(old_meta)], [catalog_index(new_meta)]
    metadata = metadata_changes(old_meta, new_meta)
    counts: Counter[str] = Counter(c["category"] for c in metadata)
    effective_counts: Counter[str] = Counter()
    comparisons = []
    for member in sorted((before.keys() | after.keys()) - {"metadata.json"}):
        if member not in before or member not in after:
            category = "observedMemberAppearance" if member not in before else (
                "observedMemberDisappearance"
            )
            counts[category] += 1
            comparisons.append({"member": member, "category": category})
            continue
        old, new = before[member], after[member]
        changes = compare_faction(old, new)
        for change in changes:
            category = change["category"]
            change["classification"] = (
                "representation" if category in REPRESENTATION else
                "gameplayCandidate" if category == "gameplayFieldCandidate"
                and not change["ancestorOrRecordLabelChanged"] else "review"
            )
        old_refs, old_issues = collect_references(old)
        new_refs, new_issues = collect_references(new)
        findings, _ = compare_catalog_contexts(
            old_refs, new_refs, old_context, new_context,
        )
        effects = effective_changes(old, new, changes, old_context, new_context)
        counts.update(c["category"] for c in changes)
        effective_counts.update(c["category"] for c in effects)
        if changes or findings or old_issues != new_issues:
            comparisons.append({
                "member": member, "category": "compared",
                "changes": changes, "effectiveReferences": effects,
                "sharedReferenceMetadataFindings": findings,
                "beforeReferenceShapeIssues": dict(old_issues),
                "afterReferenceShapeIssues": dict(new_issues),
            })
    return {
        "sharedMemberCount": len((before.keys() & after.keys()) - {"metadata.json"}),
        "changeCounts": dict(counts), "effectiveReferenceCounts": dict(effective_counts),
        "metadataChanges": metadata, "comparisons": comparisons,
    }


def compare_snapshots(
    before_archive: Path, before_manifest: Path, after_archive: Path, after_manifest: Path,
) -> Document:
    before, old = read_snapshot(before_archive, before_manifest)
    after, new = read_snapshot(after_archive, after_manifest)
    if before["source"]["language"] != after["source"]["language"]:
        raise ValueError("Army snapshot languages differ")
    return {
        "format": "InfinityDB Army snapshot diff", "formatVersion": 1,
        "scope": "explicitEndpoints",
        "limitations": [
            "Endpoint observations do not establish intermediate changes or publication dates.",
            "Member names and numeric record keys are source coordinates, "
            "not canonical identities.",
            "Gameplay field candidates require review; effective occurrence differences cover "
            "changed reference fields in stable single-profile loadouts only, "
            "not attached entities or catalog mechanics.",
            "Equal occurrence identities do not establish equivalent catalog definitions.",
            "Unresolved identities, definitions and changes of membership remain review evidence.",
        ],
        "before": before, "after": after, **compare_documents(old, new),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--before-manifest", type=Path, required=True)
    parser.add_argument("--after-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = compare_snapshots(args.before, args.before_manifest, args.after, args.after_manifest)
    output = args.output or REPORT_DIRECTORY / (
        f'{report["before"]["archiveSha256"]}-{report["after"]["archiveSha256"]}.json'
    )
    if not output.resolve().is_relative_to(REPORT_DIRECTORY.resolve()):
        parser.error(f"Output must be beneath {REPORT_DIRECTORY}")
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(payload + "\n")
    print(json.dumps({
        "output": output.as_posix(), "sharedMemberCount": report["sharedMemberCount"],
        "changeCounts": report["changeCounts"],
        "effectiveReferenceCounts": report["effectiveReferenceCounts"],
        "sha256": digest((payload + "\n").encode("utf-8")),
    }, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
