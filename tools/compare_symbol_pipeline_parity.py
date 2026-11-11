"""Compare a verified external canonical ZIP with legacy compressed SVGs.

This is an opt-in production parity gate. It does not change publication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from infinity_db.snapshot_provenance import sha256_file
from tools.symbol_raster_validation import (
    RasterValidator,
    get_tool_version,
)
from tools.verify_processed_symbol_handoff import verify_processed_symbol_handoff


def compare_symbol_pipeline_parity(
    canonical_archive: Path,
    conversion_receipt: Path,
    compressed_archive: Path,
    compression_receipt: Path,
    compression_report: Path,
    candidates_report: Path,
    run_report: Path,
    legacy_root: Path,
    *,
    renderer: str,
    executable: str,
    target_sizes: tuple[int, ...] = (32, 64),
    dprs: tuple[float, ...] = (1.0, 2.0),
    max_rms: float = 0.01,
    max_changed_fraction: float = 0.01,
    pixel_diff_threshold: int = 8,
) -> dict[str, Any]:
    """Compare all canonical paths and their rasterized output at selected sizes."""
    evidence = verify_processed_symbol_handoff(
        canonical_archive, conversion_receipt, compressed_archive,
        compression_receipt, compression_report, candidates_report, run_report,
    )
    if renderer not in {"resvg", "inkscape"} or not executable:
        raise ValueError("A concrete renderer executable is required")
    version = get_tool_version(executable)
    if not version or version == "unknown":
        raise ValueError("Renderer version cannot be established")
    if not target_sizes or not dprs or any(x <= 0 for x in (*target_sizes, *dprs)):
        raise ValueError("Invalid raster sizes or DPRs")
    with zipfile.ZipFile(compressed_archive) as archive:
        paths = sorted(archive.namelist())
        legacy_files = {
            file.relative_to(legacy_root).as_posix()
            for file in legacy_root.rglob("*.svg") if file.is_file()
        }
        if set(paths) != legacy_files:
            missing = sorted(set(paths) - legacy_files)
            extra = sorted(legacy_files - set(paths))
            raise ValueError(
                f"Legacy/external canonical path mismatch: missing={missing[:5]}, "
                f"extra={extra[:5]}"
            )
        rows: list[dict[str, Any]] = []
        with tempfile.TemporaryDirectory(prefix="symbol-parity-") as directory:
            root = Path(directory)
            for index, path in enumerate(paths):
                candidate = root / "candidate.svg"
                candidate.write_bytes(archive.read(path))
                legacy = legacy_root / path
                validator = RasterValidator(
                    renderer=renderer, executable=executable,
                    reference_svg=legacy, temp_root=root / f"render-{index}",
                    target_sizes=list(target_sizes), dprs=list(dprs),
                    max_rms=max_rms,
                    max_changed_fraction=max_changed_fraction,
                    pixel_diff_threshold=pixel_diff_threshold,
                )
                ready, error = validator.prepare_reference()
                if ready:
                    passed, metrics, error = validator.validate(candidate, "external")
                    worst_rms = metrics.worst_rms
                    worst_changed = metrics.worst_changed_fraction
                else:
                    passed = False
                    error = f"Legacy rendering failed: {error}"
                    worst_rms = None
                    worst_changed = None
                rows.append({
                    "archivePath": path,
                    "legacySha256": hashlib.sha256(legacy.read_bytes()).hexdigest(),
                    "externalSha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
                    "passed": passed,
                    "worstRms": worst_rms,
                    "worstChangedFraction": worst_changed,
                    "error": error,
                })
    failed = [row["archivePath"] for row in rows if not row["passed"]]
    return {
        "format": "InfinityDB symbol pipeline raster parity",
        "formatVersion": 1,
        "status": "passed" if not failed else "failed",
        "renderer": renderer,
        "rendererVersion": version,
        "parameters": {
            "targetSizes": list(target_sizes), "dprs": list(dprs),
            "maxRms": max_rms, "maxChangedFraction": max_changed_fraction,
            "pixelDiffThreshold": pixel_diff_threshold,
        },
        "inputArtifacts": {
            "canonicalSha256": sha256_file(canonical_archive),
            "conversionReceiptSha256": sha256_file(conversion_receipt),
            "compressedSha256": sha256_file(compressed_archive),
            "compressionReceiptSha256": sha256_file(compression_receipt),
        },
        "verifiedAssets": evidence["canonicalAssets"],
        "failedAssets": len(failed),
        "assets": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "canonical-archive", "conversion-receipt", "compressed-archive",
        "compression-receipt", "compression-report", "candidates-report",
        "run-report", "legacy-root",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--renderer", choices=["resvg", "inkscape"], default="resvg")
    parser.add_argument("--executable", required=True)
    parser.add_argument("--target-sizes", default="32,64")
    parser.add_argument("--dprs", default="1,2")
    parser.add_argument("--max-rms", type=float, default=0.01)
    parser.add_argument("--max-changed", type=float, default=0.01)
    parser.add_argument("--pixel-diff-threshold", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = compare_symbol_pipeline_parity(
            args.canonical_archive, args.conversion_receipt,
            args.compressed_archive, args.compression_receipt,
            args.compression_report, args.candidates_report, args.run_report,
            args.legacy_root, renderer=args.renderer, executable=args.executable,
            target_sizes=tuple(int(x) for x in args.target_sizes.split(",")),
            dprs=tuple(float(x) for x in args.dprs.split(",")),
            max_rms=args.max_rms, max_changed_fraction=args.max_changed,
            pixel_diff_threshold=args.pixel_diff_threshold,
        )
        if args.output.exists():
            raise FileExistsError("Parity report must not overwrite existing evidence")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(f"Symbol pipeline parity {result['status']}: "
          f"{result['verifiedAssets']} assets; {result['failedAssets']} failures")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
