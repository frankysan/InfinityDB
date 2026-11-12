"""Trace publication differences to hash-verified effective inputs, offline.

This audit consumes existing receipts and archives; it never processes or publishes SVGs.
An explained input change does not prove visual equivalence or grant artwork approval.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

FORMAT = "InfinityDB symbol artwork provenance"
CAUSES = {
    "override-content-changed": "Changed applied override content",
    "override-newly-applied": "Newly applied override",
    "override-removed": "Removed override",
    "upstream-source-changed": "Changed upstream source",
    "processing-only": "Processing only (same effective input)",
    "unresolved": "Unresolved",
}
ROOT = Path(__file__).resolve().parents[1]


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _object(value: Any) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Expected JSON object")
    return value


def _path(value: str) -> str:
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"[a-z0-9][a-z0-9._/-]*\.svg", value)
        or any(p in {"", ".", ".."} for p in value.split("/"))
    ):
        raise ValueError(f"Unsafe SVG member: {value!r}")
    return value


def _rows(values: list[dict]) -> dict[str, dict]:
    result = {}
    for row in values:
        name = _path(row["archivePath"])
        if name in result:
            raise ValueError(f"Duplicate source identity: {name}")
        result[name] = row
    return result


def _zip(content: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        result = {}
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = _path(info.filename)
            if name in result:
                raise ValueError(f"Duplicate ZIP member: {name}")
            result[name] = archive.read(info)
    return result


def _equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise ValueError(f"Disconnected evidence: {label}")


def _archive_rows(rows: dict[str, dict], members: dict[str, bytes]) -> None:
    _equal(set(members), set(rows), "archive source inventory")
    for name, row in rows.items():
        _equal(digest(members[name]), row["sha256"], f"effective bytes {name}")


def parse_override_notes(content: bytes) -> dict[str, list[dict]]:
    """Retain every declaration, including repeated keys; do not adjudicate its claims."""
    section = None
    notes: dict[str, list[dict]] = {}
    for number, raw in enumerate(content.decode("utf-8-sig").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.endswith(":") and ":" not in line[:-1]:
            section = line[:-1]
            continue
        if section is None or ":" not in line:
            raise ValueError(f"Unrecognized override note at line {number}")
        key, text = line.split(":", 1)
        relative = _path(section + "/" + key.strip() + ".svg")
        notes.setdefault(relative, []).append({"line": number, "text": text.strip()})
    return notes


def source_cause(old: dict | None, new: dict | None) -> tuple[str, str]:
    """Describe verified effective inputs, not file edit dates or visual causality."""
    if old is None or new is None:
        return "unresolved", "Source identity is absent from one build."
    if old["sha256"] == new["sha256"]:
        return "processing-only", "Effective source bytes are identical."
    before_override = old["sourceMethod"] == "override"
    after_override = new["sourceMethod"] == "override"
    if before_override and after_override:
        return "override-content-changed", "Both builds applied different verified override bytes."
    upstream_same = old.get("upstreamSha256") is not None and old.get("upstreamSha256") == new.get(
        "upstreamSha256"
    )
    if after_override and upstream_same:
        return "override-newly-applied", (
            "Historical upstream bytes replaced by a verified override; "
            "file creation/edit date unknown."
        )
    if before_override and upstream_same:
        return (
            "override-removed",
            "A historical override was replaced by matching upstream identity.",
        )
    if not before_override and not after_override:
        return "upstream-source-changed", "Different verified upstream effective bytes."
    return "unresolved", "Override application and upstream identity both changed or lack evidence."


def classify(inputs: Path) -> dict:
    """Read an explicit pinned input selection; return a deterministic classification report."""
    selection_bytes = inputs.read_bytes()
    selection = _object(json.loads(selection_bytes))
    _equal(selection.get("format"), "InfinityDB symbol provenance inputs", "input selection format")
    _equal(selection.get("formatVersion"), 1, "input selection version")
    contents, pins = {}, {}
    for role, entry in _object(selection["files"]).items():
        path = Path(entry["path"])
        content = path.read_bytes()
        _equal(digest(content), entry["sha256"], f"selected {role}")
        contents[role] = content
        pins[role] = {"name": path.name, "sha256": digest(content)}

    def js(role):
        return _object(json.loads(contents[role]))

    comparison, before, after = (
        js(k) for k in ("comparison", "current_manifest", "candidate_manifest")
    )
    build, baseline, matched, evidence = (
        js(k)
        for k in ("historical_build", "baseline_audit", "matched_inputs", "candidate_evidence")
    )
    effective, duplicate, lookup = (
        js(k) for k in ("effective_report", "duplicate_receipt", "override_lookups")
    )
    expected_formats = {
        "comparison": ("InfinityDB external symbol candidate publication comparison", 1),
        "current_manifest": ("InfinityDB symbol publication mapping", 2),
        "candidate_manifest": ("InfinityDB symbol publication mapping", 2),
        "historical_build": ("InfinityDB army symbol build", 8),
        "baseline_audit": ("InfinityDB symbol production-source baseline audit", 1),
        "matched_inputs": ("InfinityDB matched symbol parity input evidence", 1),
        "candidate_evidence": ("InfinityDB symbol publication candidate", 1),
        "effective_report": ("InfinityDB effective symbol processing report", 1),
        "duplicate_receipt": ("InfinityDB symbol processing stage receipt", 1),
        "override_lookups": ("InfinityDB symbol override lookup plan", 1),
    }
    for role, (format_name, version) in expected_formats.items():
        doc = js(role)
        _equal((doc.get("format"), doc.get("formatVersion")), (format_name, version), role)
    _equal(
        comparison["baselineManifestSha256"], pins["current_manifest"]["sha256"], "old publication"
    )
    _equal(
        comparison["candidateManifestSha256"],
        pins["candidate_manifest"]["sha256"],
        "new publication",
    )
    _equal(
        build["processing"]["publication"]["publicationManifest"]["sha256"],
        pins["current_manifest"]["sha256"],
        "historical publication owner",
    )
    for owner in (build["snapshot"]["symbolArtifact"],):
        _equal(owner["sha256"], pins["historical_archive"]["sha256"], "historical archive")
    _equal(baseline["inputs"]["symbolSha256"], pins["historical_archive"]["sha256"], "baseline ZIP")
    _equal(
        baseline["inputs"]["armySha256"],
        before["sourceSnapshot"]["armyArtifact"]["sha256"],
        "baseline Army",
    )
    _equal(before["sourceSnapshot"], after["sourceSnapshot"], "publication Army snapshots")
    _equal(
        build["snapshot"]["armyArtifact"]["sha256"],
        before["sourceSnapshot"]["armyArtifact"]["sha256"],
        "historical Army",
    )
    _equal(evidence["publicationManifestSha256"], pins["candidate_manifest"]["sha256"], "candidate")
    _equal(evidence["status"], "prepared", "candidate status")
    for role, key in {
        "effective_report": "effective_report",
        "effective_archive": "effective_archive",
        "raw_archive": "raw_archive",
        "duplicate_receipt": "duplicate_receipt",
        "override_lookups": "override_lookups",
        "candidate_compressed": "compressed_archive",
    }.items():
        _equal(pins[role]["sha256"], evidence["inputFiles"][key]["sha256"], f"candidate {role}")
    _equal(effective["snapshot"]["sha256"], pins["effective_archive"]["sha256"], "effective ZIP")
    _equal(effective["rawSnapshot"]["sha256"], pins["raw_archive"]["sha256"], "raw ZIP")
    _equal(
        effective["overrideLookupPlanSha256"], pins["override_lookups"]["sha256"], "override plan"
    )
    _equal(effective["inputArtifact"], before["sourceSnapshot"]["armyArtifact"], "effective Army")
    _equal(
        duplicate["inputArtifact"]["sha256"], pins["effective_archive"]["sha256"], "duplicate input"
    )
    _equal(
        (duplicate["stage"], duplicate["status"]), ("duplicateDetection", "passed"), "duplicates"
    )
    _equal(matched["status"], "passed", "matched-input evidence")
    _equal(
        matched["externalInputArtifacts"]["compressedSha256"],
        pins["candidate_compressed"]["sha256"],
        "matched candidate",
    )
    # Check the effective report/duplicate receipt cited by the matched-input evidence, without
    # interpreting the platform-specific selector paths or claiming a new processor parity run.
    for role in ("effective_report", "duplicate_receipt"):
        if pins[role]["sha256"] not in matched["inputs"].values():
            raise ValueError(f"Matched evidence does not cite {role}")

    old_rows, new_rows = _rows(build["assets"]), _rows(effective["assets"])
    old_zip, new_zip, raw_zip, compressed = (
        _zip(contents[k])
        for k in ("historical_archive", "effective_archive", "raw_archive", "candidate_compressed")
    )
    _archive_rows(old_rows, old_zip)
    _archive_rows(new_rows, new_zip)
    _equal(len(old_rows), baseline["counts"]["verifiedArchiveMembers"], "baseline members")
    _equal(
        dict(Counter(r["sourceMethod"] for r in old_rows.values())),
        baseline["counts"]["effectiveMethods"],
        "baseline methods",
    )
    _equal(set(old_rows), set(new_rows), "source identity inventory")
    _equal(len(new_rows), matched["matchedSourceIdentities"], "matched source count")
    lookups = {row["url"]: _path(row["overridePath"]) for row in lookup["lookups"]}
    _equal(len(lookups), len(lookup["lookups"]), "unique override lookup URLs")
    override_root = Path(selection["overrideRoot"]).resolve()
    override_notes = (
        parse_override_notes(contents["override_notes"]) if "override_notes" in contents else {}
    )
    source_records = {}
    for source in sorted(old_rows):
        old, new = old_rows[source], new_rows[source]
        _equal(old["url"], new["url"], f"source URL {source}")
        if old["sourceMethod"] not in {"override", "cache", "network"}:
            raise ValueError(f"Unknown historical source method: {source}")
        if old["sourceMethod"] != "override":
            _equal(old["sha256"], old.get("upstreamSha256"), f"historical upstream {source}")
        raw_sha = digest(raw_zip[source]) if source in raw_zip else None
        _equal(new.get("upstreamSha256"), raw_sha, f"candidate raw bytes {source}")
        donor_sources = []
        if new["sourceMethod"] == "override":
            relative = _path(new["overridePath"])
            override_file = (override_root / relative).resolve()
            if not override_file.is_relative_to(override_root):
                raise ValueError("Override escapes selected root")
            override_sha = digest(override_file.read_bytes())
            _equal(override_sha, new["sha256"], f"current override bytes {source}")
            _equal(override_sha, new["overrideSha256"], f"override receipt {source}")
            direct = lookups[new["url"]] == relative
            if not direct:
                _equal(Path(relative).parent, Path(lookups[new["url"]]).parent,
                       f"override propagation category {source}")
            donor_sources = sorted(
                p
                for p, row in new_rows.items()
                if lookups[row["url"]] == relative
                and row["sourceMethod"] == "override"
                and row["sha256"] == override_sha
                and (direct or row.get("upstreamSha256") == raw_sha)
            )
            if not donor_sources or (not direct and raw_sha is None):
                raise ValueError(f"Unverified override donor: {source}")
            application = "direct" if direct else "propagated"
            pins["override:" + relative] = {"name": relative, "sha256": override_sha}
        else:
            _equal(new["sourceMethod"], "network", f"candidate method {source}")
            _equal(new["sha256"], raw_sha, f"candidate upstream {source}")
            application = "none"
        cause, reason = source_cause(old, new)
        source_records[source] = {
            "archivePath": source,
            "url": old["url"],
            "cause": cause,
            "reason": reason,
            "historical": {
                "sourceMethod": old["sourceMethod"],
                "effectiveSha256": old["sha256"],
                "recordedUpstreamSha256": old.get("upstreamSha256"),
                "upstreamBytesAvailable": old["sha256"] == old.get("upstreamSha256"),
                "overrideSha256": old["sha256"] if old["sourceMethod"] == "override" else None,
                "overrideEvidence": (
                    "Applied bytes recovered from historical effective ZIP; "
                    "original override filename/file history not recorded."
                    if old["sourceMethod"] == "override"
                    else "No override applied in the historical build; file history unknown."
                ),
            },
            "candidate": {
                "sourceMethod": new["sourceMethod"],
                "effectiveSha256": new["sha256"],
                "upstreamSha256": raw_sha,
                "overridePath": new.get("overridePath"),
                "overrideSha256": new.get("overrideSha256"),
                "overrideApplication": application,
                "overrideDonorSources": donor_sources,
                "declaredOverrideNotes": override_notes.get(new.get("overridePath") or "", []),
            },
        }

    old_map = build["processing"]["duplicateDetection"]["canonicalByArchivePath"]
    new_map = duplicate["canonicalByArchivePath"]
    for mapping, rows, publication in ((old_map, old_rows, before), (new_map, new_rows, after)):
        _equal(set(mapping), set(rows), "complete canonical mapping")
        for source, canonical in mapping.items():
            _equal(rows[source]["sha256"], rows[canonical]["sha256"], f"exact duplicate {source}")
            _equal(
                publication["sourceArchivePathToPublishedPath"][source],
                publication["canonicalArchivePathToPublishedPath"][canonical],
                "publication lineage",
            )
    compression = build["processing"]["compression"]["report"]
    _equal(compression["sha256"], pins["historical_compression"]["sha256"], "historical compressor")
    csv_rows = {
        row["file"]: row
        for row in csv.DictReader(
            io.StringIO(contents["historical_compression"].decode("utf-8-sig"))
        )
    }
    _equal(set(compressed), set(after["canonicalArchivePathToPublishedPath"]),
           "compressed canonical inventory")
    old_hashes, new_hashes = before["publishedSha256ByPath"], after["publishedSha256ByPath"]
    changed = sorted(
        p for p in old_hashes.keys() & new_hashes.keys() if old_hashes[p] != new_hashes[p]
    )
    for key, value in {
        "changed": changed,
        "missing": sorted(old_hashes.keys() - new_hashes.keys()),
        "added": sorted(new_hashes.keys() - old_hashes.keys()),
        "before": len(old_hashes),
        "after": len(new_hashes),
    }.items():
        _equal(comparison["assetComparison"][key], value, f"comparison inventory {key}")
    assets = []
    for published in changed:
        old_canon = sorted(
            s for s, p in before["canonicalArchivePathToPublishedPath"].items() if p == published
        )
        new_canon = sorted(
            s for s, p in after["canonicalArchivePathToPublishedPath"].items() if p == published
        )
        for canonical in old_canon:
            _equal(csv_rows[canonical]["output_sha256"], old_hashes[published], "historical output")
        for canonical in new_canon:
            _equal(digest(compressed[canonical]), new_hashes[published], "candidate output")
        old_sources = {
            s for s, p in before["sourceArchivePathToPublishedPath"].items() if p == published
        }
        new_sources = {
            s for s, p in after["sourceArchivePathToPublishedPath"].items() if p == published
        }
        cause, reason = "unresolved", "Canonical selection changed or has multiple representatives."
        if old_canon == new_canon and len(old_canon) == 1:
            cause, reason = source_cause(old_rows[old_canon[0]], new_rows[new_canon[0]])
        related = []
        for source in sorted(old_sources | new_sources):
            related.append(
                {
                    **source_records[source],
                    "historicalCanonical": old_map[source],
                    "candidateCanonical": new_map[source],
                    "historicalPublishedPath": before["sourceArchivePathToPublishedPath"][source],
                    "candidatePublishedPath": after["sourceArchivePathToPublishedPath"][source],
                }
            )
        assets.append(
            {
                "path": published,
                "currentSha256": old_hashes[published],
                "candidateSha256": new_hashes[published],
                "cause": cause,
                "reason": reason,
                "historicalCanonicals": old_canon,
                "candidateCanonicals": new_canon,
                "sourceMappingChanged": old_sources != new_sources,
                "sources": related,
            }
        )
    return {
        "format": FORMAT,
        "formatVersion": 1,
        "classifierSha256": digest(Path(__file__).read_bytes()),
        "selectionSha256": digest(selection_bytes),
        "publicationPins": {
            "comparisonSha256": pins["comparison"]["sha256"],
            "currentManifestSha256": pins["current_manifest"]["sha256"],
            "candidateManifestSha256": pins["candidate_manifest"]["sha256"],
            "candidateEvidenceSha256": pins["candidate_evidence"]["sha256"],
        },
        "inputs": pins,
        "overrideNotesEvidence": {
            "documents": {k: pins[k] for k in ("override_notes", "legacy_tree_notes") if k in pins},
            "scope": "Present-day declarations only; "
                     "not historical file content or edit-date evidence.",
            "notes": override_notes,
        },
        "summary": {cause: sum(a["cause"] == cause for a in assets) for cause in CAUSES},
        "comparedAssets": len(assets),
        "assets": assets,
        "unresolvedCompatibility": comparison["assetComparison"]["missing"],
        "limits": [
            "Causes describe canonical effective-input evidence, "
            "not sole visual causality or approval.",
            "Newly applied overrides do not prove that an existing override file "
            "changed after publication.",
            "Historical override filenames and edit histories are not recorded; "
            "applied bytes are preserved.",
            "Processing-only does not mean compression-only or visually equivalent.",
            "Related aliases are traced separately; "
            "they do not replace the published canonical input.",
            "Matched processor evidence is corroborated by identity, not rerun by this audit.",
        ],
    }


def load_classifications(path: Path, pins: dict, pairs: list[dict]) -> tuple[dict, str]:
    """Reject stale/partial classification reports before embedding them in a review."""
    content = path.read_bytes()
    report = _object(json.loads(content))
    _equal((report.get("format"), report.get("formatVersion")), (FORMAT, 1), "provenance format")
    _equal(report["publicationPins"], pins, "provenance publication inputs")
    assets = report["assets"]
    if not isinstance(assets, list) or len({a["path"] for a in assets}) != len(assets):
        raise ValueError("Duplicate or invalid provenance assets")
    indexed = {a["path"]: a for a in assets}
    _equal(set(indexed), {p["path"] for p in pairs}, "provenance coverage")
    for pair in pairs:
        asset = indexed[pair["path"]]
        for key in ("currentSha256", "candidateSha256"):
            _equal(asset[key], pair[key], f"provenance pair {key}")
        if asset["cause"] not in CAUSES:
            raise ValueError("Unknown provenance cause")
    _equal(report["summary"],
           {cause: sum(a["cause"] == cause for a in assets) for cause in CAUSES},
           "provenance summary")
    _equal(report["comparedAssets"], len(pairs), "provenance count")
    return report, digest(content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inputs",
        required=True,
        type=Path,
        help="Pinned role-to-file selectors; relative paths use the working directory",
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        output = args.output.resolve()
        if not output.is_relative_to((ROOT / "local").resolve()) or output.suffix != ".json":
            raise ValueError("Output must be JSON under ignored local/")
        if output.exists():
            raise FileExistsError("Refusing to overwrite existing provenance evidence")
        report = classify(args.inputs)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(report, stream, indent=2, sort_keys=True)
            stream.write("\n")
        print(
            json.dumps({"comparedAssets": report["comparedAssets"], "summary": report["summary"]})
        )
        return 0
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        parser.exit(1, f"Provenance classification failed: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
