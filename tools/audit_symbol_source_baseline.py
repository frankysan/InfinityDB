"""Audit a real symbol snapshot against current pinned raw-source discovery.

Read-only production acceptance evidence. A processed/overridden SVG is never
misrepresented as an original upstream SVG. No network calls are performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from infinity_db.snapshot_provenance import load_snapshot_manifest, sha256_file
from infinity_db.symbol_manifest import load_symbol_manifest
from tools.army_snapshot_source import resolve_army_snapshot
from tools.export_symbol_source_plan import build_source_plan


def audit_symbol_baseline(
    *,
    army_archive: Path,
    army_manifest: Path,
    plan_path: Path,
    symbol_archive: Path,
    symbol_manifest: Path,
    build_manifest: Path,
) -> dict[str, Any]:
    """Validate and classify observed upstream availability without changing artifacts."""
    pinned = resolve_army_snapshot(
        army_archive, manifest_directory=army_manifest.parent, manifest=army_manifest,
    )
    expected_plan = build_source_plan(army_archive, army_manifest)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan != expected_plan:
        raise ValueError("Production raw-source plan differs from current Army discovery")
    provenance = load_snapshot_manifest(symbol_manifest, archive=symbol_archive)
    if provenance["snapshot"]["type"] != "symbols":
        raise ValueError("Baseline symbol provenance does not describe a symbol archive")
    input_record = provenance.get("inputArtifact", {})
    if (
        input_record.get("name") != pinned.archive.name
        or input_record.get("sha256") != sha256_file(pinned.archive)
    ):
        raise ValueError("Baseline symbol provenance is not bound to the pinned Army")

    document = load_symbol_manifest(build_manifest)
    base = document["snapshot"]
    army_record = base["armyArtifact"]
    symbol_record = base["symbolArtifact"]
    if (
        army_record["name"] != pinned.archive.name
        or army_record["sha256"] != sha256_file(pinned.archive)
        or symbol_record["name"] != symbol_archive.name
        or symbol_record["sha256"] != sha256_file(symbol_archive)
    ):
        raise ValueError("Baseline build manifest artifact identity mismatch")

    requests = {row["url"]: row["archivePath"] for row in plan["requests"]}
    assets = document["assets"]
    missing = document["unavailableAssets"]
    actual: dict[str, str] = {}
    for row in [*assets, *missing]:
        url = row["url"]
        if url in actual:
            raise ValueError(f"Duplicate asset/unavailable URL in build manifest: {url}")
        actual[url] = row["archivePath"]

    added_urls = sorted(set(requests) - set(actual))
    removed_urls = sorted(set(actual) - set(requests))
    changed_paths = sorted(
        url for url in set(requests) & set(actual)
        if requests[url] != actual[url]
    )
    if added_urls or removed_urls or changed_paths:
        raise ValueError(
            "Production source discovery and existing symbol snapshot differ: "
            f"{len(added_urls)} missing acquired URLs, "
            f"{len(removed_urls)} no-longer-declared URLs, "
            f"{len(changed_paths)} path changes; "
            f"sample missing={added_urls[:3]}, extra={removed_urls[:3]}, "
            f"changed={changed_paths[:3]}"
        )
    if provenance["snapshot"]["documentCount"] != len(assets):
        raise ValueError("Baseline symbol provenance asset count mismatch")

    methods: Counter[str] = Counter()
    recoverable: Counter[str] = Counter()
    non_upstream: list[dict[str, str]] = []
    observed_archive: set[str] = set()
    with zipfile.ZipFile(symbol_archive) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
        if len(members) != len(set(members)):
            raise ValueError("Duplicate symbol ZIP member name")
        if set(members) != {row["archivePath"] for row in assets}:
            raise ValueError("Symbol ZIP members differ from build-manifest assets")
        for row in assets:
            name = row["archivePath"]
            body = archive.read(name)
            digest = hashlib.sha256(body).hexdigest()
            if digest != row["sha256"]:
                raise ValueError(f"Effective SVG SHA-256 mismatch: {name}")
            if name in observed_archive:
                raise ValueError(f"Repeated effective SVG member: {name}")
            observed_archive.add(name)
            method = row["sourceMethod"]
            methods[method] += 1
            upstream = row.get("upstreamSha256")
            if upstream == digest:
                recoverable["upstream_byte_identical"] += 1
            elif method != "override" and upstream is None:
                # Old manifest versions may omit explicit upstream hash.
                recoverable["upstream_implicit"] += 1
            else:
                recoverable["upstream_not_proven"] += 1
                non_upstream.append({
                    "url": row["url"],
                    "archivePath": name,
                    "sourceMethod": method,
                })

    unavailable_methods = Counter(row["sourceMethod"] for row in missing)
    return {
        "format": "InfinityDB symbol production-source baseline audit",
        "formatVersion": 1,
        "inputs": {
            "army": pinned.archive.name,
            "armySha256": sha256_file(pinned.archive),
            "symbolArchive": symbol_archive.name,
            "symbolSha256": sha256_file(symbol_archive),
            "buildManifestVersion": document["formatVersion"],
        },
        "counts": {
            "sourceDocuments": pinned.document_count,
            "requestedUrls": len(requests),
            "effectiveAssets": len(assets),
            "unavailableUrls": len(missing),
            "verifiedArchiveMembers": len(observed_archive),
            "effectiveMethods": dict(sorted(methods.items())),
            "upstreamRecoverability": dict(sorted(recoverable.items())),
            "unavailableMethods": dict(sorted(unavailable_methods.items())),
        },
        "unrecoverableUpstreamExamples": non_upstream[:20],
        "conclusion": (
            "Source discovery and effective artifact identities match; "
            "upstream bytes must be reacquired for any assets whose effective "
            "hash differs from the recorded upstream hash."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--army", required=True, type=Path)
    parser.add_argument("--army-manifest", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--symbol-archive", required=True, type=Path)
    parser.add_argument("--symbol-manifest", required=True, type=Path)
    parser.add_argument("--build-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = audit_symbol_baseline(
            army_archive=args.army,
            army_manifest=args.army_manifest,
            plan_path=args.plan,
            symbol_archive=args.symbol_archive,
            symbol_manifest=args.symbol_manifest,
            build_manifest=args.build_manifest,
        )
        output = args.output
        if output.exists():
            raise ValueError(f"Refusing to overwrite audit report: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print("Production symbol baseline: " + json.dumps(result["counts"], sort_keys=True))
    print(f"Report -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
