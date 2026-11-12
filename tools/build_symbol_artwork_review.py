"""Prepare pinned comparisons and offline reviews without publishing symbol assets."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Any

from tools.classify_symbol_artwork_provenance import CAUSES, load_classifications

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_ROOT = REPO_ROOT / "local"
COMPARISON_FORMAT = "InfinityDB external symbol candidate publication comparison"
TEMPLATE = Path(__file__).with_name("templates") / "symbol_artwork_review.html"


def _sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _json(path: Path) -> tuple[dict[str, Any], str]:
    content = path.read_bytes()
    value = json.loads(content)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path.name}")
    return value, _sha(content)


def _asset_path(value: str) -> str:
    if (not isinstance(value, str) or not value or "\\" in value or ":" in value
            or any(ord(c) < 32 for c in value)
            or PurePosixPath(value).is_absolute()
            or any(part in {"", ".", ".."} for part in value.split("/"))
            or not value.endswith(".svg")):
        raise ValueError(f"Unsafe asset path: {value!r}")
    return value


def _manifest(path: Path, expected_sha: str | None) -> tuple[dict[str, Any], str]:
    manifest, digest = _json(path)
    if digest != expected_sha:
        raise ValueError(f"Manifest hash mismatch: {path.name}")
    if (manifest.get("format") != "InfinityDB symbol publication mapping"
            or manifest.get("formatVersion") != 2):
        raise ValueError("Unsupported publication manifest")
    hashes = manifest.get("publishedSha256ByPath")
    if not isinstance(hashes, dict):
        raise ValueError("Missing published asset hashes")
    for name, sha in hashes.items():
        _asset_path(name)
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
            raise ValueError(f"Invalid asset hash: {name}")
    for key in ("sourceArchivePathToPublishedPath", "canonicalArchivePathToPublishedPath"):
        mapping = manifest.get(key)
        if not isinstance(mapping, dict):
            raise ValueError(f"Missing source mapping: {key}")
        for source, destination in mapping.items():
            _asset_path(source)
            if _asset_path(destination) not in hashes:
                raise ValueError(f"Unpublished source destination: {source}")
    return manifest, digest


def _svg(root: Path, name: str, expected_sha: str) -> str:
    """Embed verified SVG bytes as an isolated image, never as active HTML."""
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Asset escapes root: {name}")
    content = path.read_bytes()
    if _sha(content) != expected_sha:
        raise ValueError(f"Asset hash mismatch: {name}")
    if re.search(br"<!\s*(?:DOCTYPE|ENTITY)", content, re.I):
        raise ValueError(f"Unsupported SVG declarations: {name}")
    try:
        svg = ET.fromstring(content)
    except ET.ParseError as error:
        raise ValueError(f"Invalid SVG: {name}") from error
    if svg.tag != "{http://www.w3.org/2000/svg}svg":
        raise ValueError(f"Expected SVG root: {name}")
    return "data:image/svg+xml;base64," + base64.b64encode(content).decode("ascii")


def _sources(manifest: dict[str, Any], path: str) -> dict[str, list[str]]:
    return {
        key: sorted(source for source, published in manifest[key].items() if published == path)
        for key in ("sourceArchivePathToPublishedPath", "canonicalArchivePathToPublishedPath")
    }


def _comparison_inventory(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    old, new = before["publishedSha256ByPath"], after["publishedSha256ByPath"]
    return {
        "before": len(old),
        "after": len(new),
        "changed": sorted(p for p in old.keys() & new.keys() if old[p] != new[p]),
        "missing": sorted(old.keys() - new.keys()),
        "added": sorted(new.keys() - old.keys()),
    }


def write_comparison(current_manifest: Path, candidate_manifest: Path, output: Path, *,
                     expected_current_sha256: str, expected_candidate_sha256: str) -> int:
    """Exclusively create a comparison from two explicitly pinned manifests."""
    output = output.resolve()
    if not output.is_relative_to(LOCAL_ROOT.resolve()) or output.suffix != ".json":
        raise ValueError("Comparison output must be a JSON file under ignored local/")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing comparison: {output}")
    for label, digest in (("current", expected_current_sha256),
                          ("candidate", expected_candidate_sha256)):
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"Invalid expected {label} manifest SHA-256")
    before, before_sha = _manifest(current_manifest, expected_current_sha256)
    after, after_sha = _manifest(candidate_manifest, expected_candidate_sha256)
    record = {
        "format": COMPARISON_FORMAT,
        "formatVersion": 1,
        "baselineManifestSha256": before_sha,
        "candidateManifestSha256": after_sha,
        "assetComparison": _comparison_inventory(before, after),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(f"Created {output} from the selected publication manifests")
    return 0


def build_report(comparison: Path, current: Path, candidate: Path, output: Path,
                 candidate_manifest: Path, current_manifest: Path,
                 candidate_evidence: Path | None = None,
                 provenance: Path | None = None) -> int:
    """Validate inventory and hashes before exclusively creating a local review."""
    output = output.resolve()
    if not output.is_relative_to(LOCAL_ROOT.resolve()) or output.suffix != ".html":
        raise ValueError("Review output must be an HTML file under ignored local/")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing review: {output}")
    record, comparison_sha = _json(comparison)
    if (record.get("format") != COMPARISON_FORMAT
            or record.get("formatVersion") != 1):
        raise ValueError("Unsupported comparison format")
    before, before_sha = _manifest(current_manifest, record.get("baselineManifestSha256"))
    after, after_sha = _manifest(candidate_manifest, record.get("candidateManifestSha256"))
    old, new = before["publishedSha256ByPath"], after["publishedSha256ByPath"]
    expected = _comparison_inventory(before, after)
    inventory = record.get("assetComparison", {})
    if not isinstance(inventory, dict):
        raise ValueError("Comparison asset inventory must be an object")
    for key in ("changed", "missing", "added"):
        supplied = inventory.get(key)
        if not isinstance(supplied, list) or supplied != expected[key]:
            raise ValueError(f"Comparison {key} inventory does not match manifests")
    if inventory.get("before") != expected["before"] or inventory.get("after") != expected["after"]:
        raise ValueError("Comparison asset counts do not match manifests")
    evidence = None
    evidence_sha = None
    if candidate_evidence is not None:
        evidence, evidence_sha = _json(candidate_evidence)
        if (evidence.get("format") != "InfinityDB symbol publication candidate"
                or evidence.get("formatVersion") != 1 or evidence.get("status") != "prepared"
                or evidence.get("publicationManifestSha256") != after_sha):
            raise ValueError("Candidate evidence does not match publication")

    items = []
    for path in expected["changed"]:
        items.append({
            "path": path, "category": path.split("/", 1)[0],
            "currentSha256": old[path], "candidateSha256": new[path],
            "currentSources": _sources(before, path), "candidateSources": _sources(after, path),
            "current": _svg(current, path, old[path]),
            "candidate": _svg(candidate, path, new[path]),
        })
    # Validate and retain removed URLs independently of the artwork decisions.
    removed = []
    for path in expected["missing"]:
        _svg(current, path, old[path])
        sources = _sources(before, path)
        replacements = sorted({after["sourceArchivePathToPublishedPath"][source]
                               for source in sources["sourceArchivePathToPublishedPath"]
                               if source in after["sourceArchivePathToPublishedPath"]})
        removed.append({"path": path, "currentSha256": old[path], "sources": sources,
                        "candidateDestinations": replacements,
                        "status": "unresolved compatibility requirement"})
    pins = {"comparisonSha256": comparison_sha, "currentManifestSha256": before_sha,
            "candidateManifestSha256": after_sha, "candidateEvidenceSha256": evidence_sha}
    classification_report = None
    if provenance is not None:
        classification_report, provenance_sha = load_classifications(provenance, pins, items)
        pins["provenanceSha256"] = provenance_sha
        classifications = {row["path"]: row for row in classification_report["assets"]}
        for item in items:
            item["provenance"] = classifications[item["path"]]
    report = {
        "reviewId": _sha(json.dumps(pins, sort_keys=True).encode()), "pins": pins,
        "currentSnapshot": before.get("sourceSnapshot"),
        "candidateSnapshot": after.get("sourceSnapshot"),
        "candidateEvidence": evidence, "removed": removed, "added": expected["added"],
        "provenance": classification_report, "causeLabels": CAUSES,
        "items": items,
    }
    payload = json.dumps(report, ensure_ascii=True).replace("<", "\\u003c")
    page = TEMPLATE.read_text(encoding="utf-8").replace("__PAYLOAD__", payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(page)
    print(f"Created {output} with {len(items)} embedded SVG pairs; "
          f"{len(removed)} unresolved removed URLs")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-comparison", action="store_true",
                        help="Create the comparison instead of rendering a review")
    parser.add_argument("--comparison", required=True, type=Path,
                        help="Comparison input, or new local JSON output with --write-comparison")
    parser.add_argument("--current", type=Path, help="Current publication static directory")
    parser.add_argument("--candidate", type=Path, help="Candidate publication static directory")
    parser.add_argument("--manifest", required=True, type=Path,
                        help="Candidate publication manifest")
    parser.add_argument("--current-manifest", required=True, type=Path,
                        help="Current publication manifest")
    parser.add_argument("--expected-current-sha256",
                        help="Selected current manifest SHA-256 when writing a comparison")
    parser.add_argument("--expected-candidate-sha256",
                        help="Selected candidate manifest SHA-256 when writing a comparison")
    parser.add_argument("--candidate-evidence", type=Path,
                        help="Optional candidate-evidence.json bound to the candidate manifest")
    parser.add_argument("--output", type=Path, help="New local HTML output for a review")
    parser.add_argument("--provenance", type=Path,
                        help="Optional exact-publication provenance classification report")
    args = parser.parse_args(argv)
    if args.write_comparison:
        required = {"--expected-current-sha256": args.expected_current_sha256,
                    "--expected-candidate-sha256": args.expected_candidate_sha256}
        incompatible = {"--current": args.current, "--candidate": args.candidate,
                        "--output": args.output, "--candidate-evidence": args.candidate_evidence,
                        "--provenance": args.provenance}
    else:
        required = {"--current": args.current, "--candidate": args.candidate,
                    "--output": args.output}
        incompatible = {"--expected-current-sha256": args.expected_current_sha256,
                        "--expected-candidate-sha256": args.expected_candidate_sha256}
    missing = [flag for flag, value in required.items() if value is None]
    if missing:
        parser.error(f"Required for this mode: {', '.join(missing)}")
    unexpected = [flag for flag, value in incompatible.items() if value is not None]
    if unexpected:
        parser.error(f"Not supported in this mode: {', '.join(unexpected)}")
    try:
        if args.write_comparison:
            return write_comparison(
                args.current_manifest, args.manifest, args.comparison,
                expected_current_sha256=args.expected_current_sha256,
                expected_candidate_sha256=args.expected_candidate_sha256,
            )
        return build_report(args.comparison, args.current, args.candidate, args.output,
                            args.manifest, args.current_manifest, args.candidate_evidence,
                            args.provenance)
    except (OSError, ValueError, KeyError, TypeError) as error:
        kind = "Comparison" if args.write_comparison else "Review"
        parser.exit(1, f"{kind} generation failed: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
