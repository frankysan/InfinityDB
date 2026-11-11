# P5.7 — Symbol pipeline production parity runbook

Status: **not executed**. This is an opt-in acceptance exercise, not a
replacement for the current symbol publication path.

## Readiness audit

The pinned baseline is `local/p5-production-symbol-baseline-audit-20261111.json`.
The legacy snapshot is `data/raw/symbols/SYMBOLS 20261004-184813.zip`
and its current work directory is
`data/work/symbols/SYMBOLS 20261004-184813--cda970bafe15`.
Run the read-only readiness check before spending time on rendering:

```powershell
python -m tools.audit_symbol_parity_readiness --output "local/p5-symbol-parity-readiness.json"
```

The initial audit found 1,101 archived assets and 808 legacy
compressed canonical SVGs. **29 legacy overridden assets lack
verified original upstream bytes**, and no completed external
conversion/compression artifacts exist at
`local/p5-external-processing`. The command exits with status 2
for this expected blocked state, and 1 for invalid input evidence.
It does not download, reconstruct or silently substitute sources.

## Required inputs

Use the **same pinned Army snapshot and source URL plan** for both
pipelines. Keep the actual upstream SVG bytes separate from reviewed
overrides. Do not use already-overridden legacy SVGs as a substitute
for upstream acquisition evidence.

The external run must complete, with passed receipts, in this order:
raw acquisition → reviewed override application → SVG preflight →
font audit → duplicate detection → text-to-path conversion →
canonical compression. Preserve the input ZIPs, stage receipts,
reports, alias policy and resolved font-file hashes.

Run the existing InfinityDB symbol pipeline against the same source
snapshot and override set without modifying the deployed site.
Retain its `work_root/compressed` directory as the legacy reference.
Both outputs must have the same canonical path set; the comparison
will reject missing or extra paths rather than silently filtering.

Record the real converter, renderer and SVGO versions. Use the same
renderer, sizes, DPRs and visual tolerances for both pipelines.
The new compressor receipt already pins these settings. This
comparison is not a substitute for validating override choices or
font resolution.

## Verify and compare

From the InfinityDB repository root, substitute the actual immutable
paths below. The `--legacy-root` directory must contain the
in-tree pipeline's canonical compressed SVGs, not browser-published
renamed assets.

```powershell
python -m tools.verify_processed_symbol_handoff --canonical-archive "PATH_TO_CANONICAL.zip" --conversion-receipt "PATH_TO_TEXT_CONVERSION_STATE.json" --compressed-archive "PATH_TO_COMPRESSED.zip" --compression-receipt "PATH_TO_COMPRESSION_STATE.json" --compression-report "PATH_TO_COMPRESSION_REPORT.csv" --candidates-report "PATH_TO_CANDIDATES_REPORT.csv" --run-report "PATH_TO_COMPRESSION_RUN.json"
python -m tools.compare_symbol_pipeline_parity --canonical-archive "PATH_TO_CANONICAL.zip" --conversion-receipt "PATH_TO_TEXT_CONVERSION_STATE.json" --compressed-archive "PATH_TO_COMPRESSED.zip" --compression-receipt "PATH_TO_COMPRESSION_STATE.json" --compression-report "PATH_TO_COMPRESSION_REPORT.csv" --candidates-report "PATH_TO_CANDIDATES_REPORT.csv" --run-report "PATH_TO_COMPRESSION_RUN.json" --legacy-root "PATH_TO_LEGACY_COMPRESSED_DIRECTORY" --renderer resvg --executable "PATH_TO_RESVG_EXECUTABLE" --target-sizes 32,64 --dprs 1,2 --max-rms 0.01 --max-changed 0.01 --pixel-diff-threshold 8 --output "local/p5-symbol-parity.json"
```

The comparison verifies the external receipt chain before rendering.
It writes one report with both artifact hashes, each canonical
asset's legacy/external SVG hash, the worst raster metrics, and
per-asset errors. Renderer failures are recorded as failed assets
where possible, not counted as passing comparisons. A failed
comparison exits nonzero. Use a fresh output path for every run;
reports must not be overwritten.

## Acceptance gates

1. The real-source inventory must account for every reviewed
   override (29 in the recorded baseline), missing upstream
   source and canonical representative, with provenance to the
   original source bytes.
2. All external stage receipts must pass, with no unresolved font,
   conversion, duplicate-render or compression errors.
3. The independent artifact verifier must pass, and the raster
   parity report must show zero failed assets at the approved
   sizes/DPRs and thresholds.
4. Compare the final semantic browser mapping and packaged assets
   against the current publication output. Confirm actual browser
   rendering, attribution and local/Docker build behavior.
5. Only after these checks should the in-tree pipeline be retired
   in a separate, reviewed change.

**Current evidence:** hermetic verifier/parity tests and cross-platform
symbol-tools CI only. No actual production snapshot parity or
browser publication acceptance has been recorded.
