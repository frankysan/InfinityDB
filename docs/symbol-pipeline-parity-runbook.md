# P5.7 — Symbol pipeline production parity runbook

Status: **matched-input processor parity passed and semantic candidate
prepared (2026-11-11)**. Artwork/URL review against the tracked release,
promotion and actual browser/local/Docker acceptance remain open. See the [dated evidence and acceptance
boundary](testing.md#p57-matched-input-symbol-processor-parity).

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
compressed canonical SVGs. **29 legacy overridden assets lacked
verified original upstream bytes** in that historical ZIP. A new
source-side acquisition was completed on 2026-11-11, producing
`SYMBOLS 20261111-202545.zip` and its provenance/report in the
symbol-tools checkout. The historical readiness audit still
describes the original baseline, not the new acquisition. The command exits with status 2
for this expected blocked state, and 1 for invalid input evidence.
It does not download, reconstruct or silently substitute sources.

## Reacquire upstream bytes

The pinned source plan already exists at
`InfinityDB/local/p5-production-symbol-source-plan-20260929.json`.
The authoritative override lookup plan was exported and verified
against current Army discovery at
`InfinityDB/local/p5-production-symbol-override-lookups-20261111.json`
(1,101 URLs). The reviewed override tree already exists in the
symbol-tools checkout at `local/image_overrides`.

**Run these commands in PowerShell**, starting from the InfinityDB
repository root. Adjust only the sibling repository path if needed:

```powershell
$symbols = (Resolve-Path ..\InfinityDB-symbol-tools).Path
$handoff = Join-Path $symbols 'local/p5-production-input'
New-Item -ItemType Directory -Force -Path $handoff | Out-Null
Copy-Item 'data/raw/JSON 20260929-114335.zip' (Join-Path $handoff 'JSON 20260929-114335.zip')
Copy-Item 'local/p5-production-symbol-source-plan-20260929.json' (Join-Path $handoff 'source-plan.json')
Copy-Item 'local/p5-production-symbol-override-lookups-20261111.json' (Join-Path $handoff 'override-lookups.json')
Set-Location $symbols
if (-not (Test-Path '.venv/Scripts/python.exe')) { py -3 -m venv .venv }
.\.venv\Scripts\python.exe -m pip install -e '.[test,processing]'
.\.venv\Scripts\python.exe -m infinity_symbol_tools.cli --plan local/p5-production-input/source-plan.json --army 'local/p5-production-input/JSON 20260929-114335.zip'
.\.venv\Scripts\python.exe -m infinity_symbol_tools.cli --plan local/p5-production-input/source-plan.json --army 'local/p5-production-input/JSON 20260929-114335.zip' --acquire --destination local/p5-production-raw --manifest-dir local/p5-production-raw
```

The last command performs **1,101 network requests** (default
0.2-second delay between requests) and may take several minutes.
It is an explicit, source-side operation; no application artifact is
published. It may record HTTP 404 as unavailable, but unexpected
HTTP errors or redirects fail closed. Retain the raw ZIP, provenance
manifest and raw report together. Never substitute the old
override-containing legacy ZIP for this acquisition.

The explicit source-side acquisition and subsequent processing completed
on 2026-11-11. For a new run, pass its actual generated filenames to
`infinity-symbol-overrides` using the pinned lookup plan and
`local/image_overrides`, then continue through preflight, font audit,
duplicate detection, conversion and compression. Preserve all receipts
and reports; the completed matched-input comparison requires no new
acquisition.

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

## Reconcile canonical paths

The new duplicate stage selected **807 canonical SVGs** from
1,101 effective sources (294 exact duplicates, zero render errors).
The historical in-tree work directory contains **808** compressed SVGs.
The matched-input rebuild now produces the same 807-canonical mapping
as the external run. Semantic publication of both source identities
still needs verification; a canonical count alone does not establish it.

Copy the external `duplicate-state.json` receipt into an
ignored local location in the InfinityDB checkout and
compare canonical paths before running expensive raster
parity:

```powershell
Copy-Item '..\InfinityDB-symbol-tools\local\p5-production-reports\EFFECTIVE-SYMBOLS 20261111-204139\duplicate-state.json' 'local/p5-production-duplicate-state.json'
python -m tools.compare_symbol_canonical_paths --legacy-root 'data/work/symbols/SYMBOLS 20261004-184813--cda970bafe15/compressed' --duplicate-receipt 'local/p5-production-duplicate-state.json'
```

The actual 2026-11-11 comparison passed independent
artifact verification (**807** canonical assets, **1,101**
source identities) and reported exactly one legacy-only
path, `units/shasvastii-seed-soldiers-1-2.svg`. The new
duplicate receipt maps it to
`units/shasvastii-seed-soldiers-1-1.svg` as an exact
duplicate. This explains the count difference but is
**not** sufficient to pass browser publication acceptance. The path
comparison against that historical directory continues to report its
count difference. For processor parity, use the isolated matched-input
rebuild described below; preserve the separate semantic publication gate.

## Matched-input reference build

The initial historical-output raster comparison failed on 73 assets.
Its effective override inputs and compression renderer differed from
the external run. Preserve that failure rather than relaxing thresholds.
Use `tools.build_symbols` with an isolated `--data-root`, the pinned
Army archive/provenance, all four `--raw-symbol-*` handoff arguments
and the same override tree as the external run. Stop after compression
with `--stop-after compression`; keep the application publication unchanged.

The completed reference is under `local/p5-matched-legacy-20261111`,
with compressed SVGs at
`work/symbols/SYMBOLS 20261111-210655--13474b43eb16/compressed`.
Use that directory as `--legacy-root` below. Both effective byte inventories
and complete canonical mappings were checked before comparing. The strict
comparison passed all 807 assets without path exceptions. See
[testing](testing.md#p57-matched-input-symbol-processor-parity) for the
input hashes, tool versions, measurements and remaining acceptance.

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

## Prepare and compare semantic publication

Use the offline `tools.prepare_symbol_publication` consumer with the exact
raw/effective ZIPs, producer font-alias bytes and stage/processed report
directories. The [candidate lifecycle](../data/README.md#external-processed-symbol-publication-candidates)
owns the full input and output contract. Always select a fresh output directory.
No processing package or graphical tool installation is needed.

The production-derived candidate under
`local/p5-external-symbol-publication-verified-20261111` preserves every source
and browser mapping key. Both Seed Soldier source identities resolve to one
published SVG. The comparison records 118 changed SVG hashes and one removed
filename against the tracked publication; those artwork and URL differences
remain subject to review. See the [candidate acceptance evidence](testing.md#p57-external-semantic-publication-candidate).
Preparation does not promote assets or rebuild embedded SQLite mappings.

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

**Current evidence:** matched-input production processor raster parity
passed, with zero pixel differences across all 807 canonical assets.
The independent artifact verifier and 16 hermetic handoff tests also passed.
The external semantic publication candidate preserves every source/browser
mapping key. Artwork/URL review, candidate promotion, rebuilt SQLite mappings,
actual browser/local/Docker acceptance and in-tree processor retirement remain
open.
The failed historical-output comparison remains preserved separately.
