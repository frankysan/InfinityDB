"""Check whether local production symbol parity inputs are actually available.

Read-only. This does not synthesize upstream bytes from reviewed overrides.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def audit_parity_readiness(
    baseline: Path,
    source_plan: Path,
    symbol_manifest: Path,
    symbol_archive: Path,
    work_root: Path,
    external_root: Path,
) -> dict:
    audit = json.loads(baseline.read_text(encoding="utf-8"))
    plan = json.loads(source_plan.read_text(encoding="utf-8"))
    manifest = json.loads(symbol_manifest.read_text(encoding="utf-8"))
    if audit.get("format") != "InfinityDB symbol production-source baseline audit":
        raise ValueError("Unexpected baseline audit format")
    requests = plan.get("requests")
    if not isinstance(requests, list) or len(requests) != audit["counts"]["requestedUrls"]:
        raise ValueError("Source plan does not match recorded baseline URL count")
    if hashlib.sha256(symbol_archive.read_bytes()).hexdigest() != audit["inputs"]["symbolSha256"]:
        raise ValueError("Legacy symbol ZIP differs from audited baseline")
    with zipfile.ZipFile(symbol_archive) as archive:
        members = {item.filename for item in archive.infolist() if not item.is_dir()}
    if len(members) != audit["counts"]["verifiedArchiveMembers"]:
        raise ValueError("Legacy symbol archive member count differs from baseline")
    assets = manifest.get("assets", [])
    if len(assets) != len(members) or {row["archivePath"] for row in assets} != members:
        raise ValueError("Build manifest differs from legacy archive members")
    unproven = [
        row["archivePath"] for row in assets
        if row.get("upstreamSha256") != row["sha256"]
    ]
    if len(unproven) != audit["counts"]["upstreamRecoverability"]["upstream_not_proven"]:
        raise ValueError("Unproven source count differs from baseline")
    compressed = work_root / "compressed"
    legacy_count = len(list(compressed.rglob("*.svg"))) if compressed.is_dir() else 0
    external_files = {
        name: (external_root / name).is_file()
        for name in (
            "CANONICAL.zip", "text-conversion-state.json", "COMPRESSED.zip",
            "compression-state.json", "compression-report.csv",
            "compression-candidates.csv", "compression-run.json",
        )
    }
    blockers = []
    if unproven:
        blockers.append(
            f"{len(unproven)} overridden legacy SVGs are not verified upstream bytes"
        )
    if legacy_count == 0:
        blockers.append("Legacy canonical compressed tree not found")
    if not all(external_files.values()):
        blockers.append("External completed-stage artifacts not present at expected paths")
    return {
        "format": "InfinityDB production symbol parity readiness",
        "formatVersion": 1,
        "status": "ready" if not blockers else "blocked",
        "requestedUrls": len(requests),
        "legacyArchiveMembers": len(members),
        "upstreamUnproven": len(unproven),
        "upstreamUnprovenPaths": sorted(unproven),
        "legacyCompressedAssets": legacy_count,
        "externalStageFiles": external_files,
        "blockers": blockers,
        "note": (
            "Existing legacy compressed assets are reference outputs only; "
            "their presence does not prove a matching raw-source pipeline run."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline", type=Path,
        default=Path("local/p5-production-symbol-baseline-audit-20261111.json"),
    )
    parser.add_argument(
        "--source-plan", type=Path,
        default=Path("local/p5-production-symbol-source-plan-20260929.json"),
    )
    parser.add_argument(
        "--symbol-manifest", type=Path,
        default=Path("data/manifests/army-symbol-build.json"),
    )
    parser.add_argument(
        "--symbol-archive", type=Path,
        default=Path("data/raw/symbols/SYMBOLS 20261004-184813.zip"),
    )
    parser.add_argument(
        "--work-root", type=Path,
        default=Path("data/work/symbols/SYMBOLS 20261004-184813--cda970bafe15"),
    )
    parser.add_argument(
        "--external-root", type=Path, default=Path("local/p5-external-processing"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = audit_parity_readiness(
            args.baseline, args.source_plan, args.symbol_manifest,
            args.symbol_archive, args.work_root, args.external_root,
        )
        body = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            if args.output.exists():
                raise FileExistsError("Refusing to overwrite readiness evidence")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(body, encoding="utf-8")
        print(body)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    return 0 if result["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
