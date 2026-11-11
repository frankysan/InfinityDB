# P5.7 — Symbol pipeline production parity runbook

Status: **accepted external publication promoted (2026-11-11)**. The user
approved all 118 changed artworks. The old Seed Soldier URL is retained,
embedded mappings are rebuilt, and checkout/browser/Docker acceptance passed.
The superseded in-tree processor has since been retired. Earlier sections are
dated acceptance evidence, not instructions to rerun retired commands; the
[data lifecycle](../data/README.md#external-processed-symbol-publication-candidates)
owns the current workflow.

## Readiness audit

The pinned baseline is `local/p5-production-symbol-baseline-audit-20261111.json`.
The legacy snapshot is `data/raw/symbols/SYMBOLS 20261004-184813.zip`
and its current work directory is
`data/work/symbols/SYMBOLS 20261004-184813--cda970bafe15`.
The now-retired read-only readiness audit was run before rendering.

The initial audit found 1,101 archived assets and 808 legacy
compressed canonical SVGs. **29 legacy overridden assets lacked
verified original upstream bytes** in that historical ZIP. A new
source-side acquisition was completed on 2026-11-11, producing
`SYMBOLS 20261111-202545.zip` and its provenance/report in the
symbol-tools checkout. The historical readiness audit still
describes the original baseline, not the new acquisition. It did not download,
reconstruct or silently substitute sources.

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

The historical matched-input run used the former InfinityDB symbol pipeline
against the same source snapshot and override set without modifying the deployed
site. Its `work_root/compressed` directory is retained as legacy evidence.
The in-tree processor is no longer available for new reference builds.

Record the real converter, renderer and SVGO versions. Use the same
renderer, sizes, DPRs and visual tolerances for both pipelines.
The new compressor receipt already pins these settings. This
comparison is not a substitute for validating override choices or
font resolution.

## Reconcile canonical paths

The new duplicate stage selected **807 canonical SVGs** from
1,101 effective sources (294 exact duplicates, zero render errors).
The historical in-tree work directory contains **808** compressed SVGs.
The matched-input rebuild produced the same 807-canonical mapping as the
external run. The later accepted publication verified both source identities;
a canonical count alone did not establish that result.

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
the external run. The historical matched-input rebuild used the now-retired
`tools.build_symbols` through compression with the same pinned source and
override tree, without changing application publication.

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
published SVG. The comparison recorded 118 changed SVG hashes and one removed
filename against the then-tracked publication. Those differences were later
approved and the old URL preserved. See the
[candidate acceptance evidence](testing.md#p57-external-semantic-publication-candidate).
Preparation does not promote assets or rebuild embedded SQLite mappings.

## Local artwork review

**Project domain:** Project infrastructure

The application owns comparison of its current publication with a prepared
candidate. Acquisition, overrides, font conversion and compression remain owned
by InfinityDB-symbol-tools. The offline review builder does not run those stages,
alter assets/manifests/databases, promote the candidate or change parity thresholds.
It can also review a future candidate with explicitly selected evidence.

From the repository root, use the project virtual environment and a **fresh**
output filename under ignored `local/`:

```powershell
.\.venv\Scripts\python.exe -m tools.build_symbol_artwork_review --candidate-evidence local/p5-external-symbol-publication-verified-20261111/candidate-evidence.json --output local/p5-symbol-artwork-review-20261111-v2.html
```

The other defaults select the dated comparison JSON, verified candidate's
`static/` and manifest, and current tracked publication. Use `--help` for
explicit input paths. The builder verifies both manifest hashes against the
comparison, recomputes its complete changed/added/removed inventory, and checks
every embedded SVG's bytes against the appropriate manifest. It rejects unsafe
paths, malformed SVGs, mismatched evidence and existing output files.
The default output without `--output` is `local/p5-symbol-artwork-review.html`.
Reports embed the SVGs and need no server, network or adjacent assets.

Open the HTML in a browser. Search filenames or source identities, filter by
category/decision, and use side-by-side or adjustable-opacity overlay views.
Expand input provenance for manifest/comparison hashes, snapshot identities and
optional candidate evidence; expand each card for both source/canonical mappings
and asset hashes. Candidate preparation evidence is displayed as recorded; the
review builder does not rerun its upstream receipt-chain verification.

Without a provenance report, differences begin **unclassified**. Neither changed hashes nor identical
appearance prove a source change or compression-only change. The publication
manifests do not contain paired per-asset source-byte histories. Record supporting
source/processing evidence identities in the notes when assigning a reviewer
classification; annotations are not automatically confirmed findings.
Matched-input processor parity does not classify historical publication changes.

Choose **Accept**, **Investigate** or **Reject** and add classification/notes.
Export JSON before closing or reloading: there is no automatic browser storage.
Save exports under ignored `local/`, then import to resume. Imports are bound
to the exact comparison/manifests/evidence fingerprint, validate every entry
before applying any changes, and replace the decision set (omitted paths reset
to unreviewed). Rejected imports preserve existing decisions. Keep exported
decisions with the report and pinned inputs; exporting does not approve cutover.

The validated production page is
`local/p5-symbol-artwork-review-20261111-v2.html`: **118 pairs** (4 Army,
1 characteristic, 2 Order, 11 Peripheral and 100 Unit assets).
Chrome validation at **1440/390/320 × 900** rendered all pairs in both views,
exercised search/category/decision filters, opacity, export/import after reload
and stale-import rejection, with no page/request/HTTP errors, external requests
or horizontal overflow. Private validation evidence is
`local/p5-symbol-artwork-browser-validation.json`; its test exports are browser
validation data, **not artwork approvals**. The generated report starts with all
118 decisions unreviewed.

At the time of this review, the removed
`units/combined-army/512-shasvastii-seed-soldiers--1-2.svg` remains an
**unresolved compatibility requirement** in the page and exports. Its source
identity's new destination did not establish compatibility for the old URL.
The later accepted cutover approved the artwork and preserved that URL.

Focused regression checks (including an optional real-Chrome fixture test when
Playwright/Chrome are installed):

```powershell
.\.venv\Scripts\python.exe tools/run_checks.py --stage test --assets off --test-workers 0 tests/test_build_symbol_artwork_review.py tests/test_test_sections.py
```

## Override provenance classification

**Project domains:** Data processing, Project infrastructure

Run the read-only audit with an explicit, SHA-pinned local input selection,
then embed its result in a fresh review page:

```powershell
.\.venv\Scripts\python.exe -m tools.classify_symbol_artwork_provenance --inputs local/p5-symbol-provenance-inputs-with-notes-20261111.json --output local/p5-symbol-provenance-final-20261111.json
.\.venv\Scripts\python.exe -m tools.build_symbol_artwork_review --candidate-evidence local/p5-external-symbol-publication-verified-20261111/candidate-evidence.json --provenance local/p5-symbol-provenance-final-20261111.json --output local/p5-symbol-artwork-review-classified-20261111.html
```

Those output files already contain the recorded run; use new filenames to repeat
it. No production SVGs are regenerated. The input JSON has
`format: "InfinityDB symbol provenance inputs"`, `formatVersion: 1`,
`overrideRoot`, and `files`. Each file selector is
`{"path": "relative/input/path", "sha256": "<exact SHA-256>"}`; relative paths
resolve from the working directory. Required roles are:

| Roles | Evidence |
| --- | --- |
| `comparison`, `current_manifest`, `candidate_manifest` | Publication inventory and source/canonical destinations |
| `historical_build`, `historical_archive`, `historical_compression` | Historical applied bytes, methods, canonical assignments and compressed output hashes |
| `baseline_audit`, `matched_inputs` | Pinned historical snapshot and corroborating matched-input evidence |
| `candidate_evidence` | Candidate manifest and input-file hash bindings |
| `effective_report`, `effective_archive`, `raw_archive` | Candidate applied and upstream bytes |
| `duplicate_receipt`, `override_lookups`, `candidate_compressed` | Exact duplicate assignments, override donors and published output bytes |

Optional `override_notes` and `legacy_tree_notes` selectors pin the present-day
`overrides.txt` copies. The audit retains repeated declarations and line numbers;
it joins candidate notes by the selected override path, including propagated
donors. Notes describe declared origins/intent, not verified historical content,
edit dates or visual equivalence. The two copies read on 2026-11-11 were
byte-identical. Original historical override filenames/edit histories are absent;
historical **applied override bytes** are recovered directly from the effective ZIP.
Do not substitute current override files for historical evidence.

Every selected artifact is hashed. The audit binds the historical build to the
current publication, verifies both effective archives against every source row,
checks current override files, raw hashes, exact duplicate groups, canonical
publication lineage, historical compression hashes and candidate output members.
The matched-input record is corroborated by identity; processor parity is not
rerun. Missing/disconnected inputs fail generation; unsupported or ambiguous
canonical attribution remains unresolved instead of being guessed.

The 2026-11-11 result covers **118 changed published assets / 154 source
identities**; 24 assets have multiple source identities:

| Confirmed canonical input cause | Assets | Meaning |
| --- | ---: | --- |
| Changed applied override content | 1 | Morat used different verified override bytes in both builds |
| Newly applied override | 56 | Historical upstream bytes were replaced by an override: 53 direct, 3 propagated canonical inputs |
| Processing only | 61 | Canonical effective bytes are identical: 57 upstream inputs and 4 unchanged overrides |
| Upstream source change | 0 | No changed publication attributed to changed upstream effective bytes |
| Removed override | 0 | No changed publication attributed to override removal |
| Unresolved canonical cause | 0 | All 118 canonical input comparisons are accounted for |

The four unchanged historical overrides are Onyx, Peripheral, Impetuous and
Lieutenant. The 56 newly applied overrides do **not** prove that those files
were edited after publication: their historical file content/existence is not
recorded because no override was applied. These are verified input transitions,
not sole-cause claims about output appearance. Processing-only is broader than
compression-only; conversion/configuration/toolchain effects are not waived.

The review's **Provenance cause** filter separates these queues, while
**Reviewer classification** remains an independent annotation. Expand
**Verified input provenance** for each canonical and related source trace.
The audit report's hash participates in review identity and JSON export/import,
so a different provenance report requires a fresh decision file. No assets are
automatically accepted. The Seed Soldier source membership change is retained
alongside its canonical input cause; the subsequent cutover resolved the old
filename and accepted artwork, mappings and browser/local/Docker behavior.

See [testing evidence](testing.md#p57-override-provenance-classification) for the
focused regression and real-page browser results. The dated findings are historical evidence for that accepted cutover.

## Accepted publication cutover

**Project domains:** Data processing, Project infrastructure, Deployment

**User decision, 2026-11-11:** all 118 changed artworks were approved. Artwork
review was not repeated. Promotion started from `e70195cdf84d46d1a1b4853948aa480eb7524f35`
and consumed `local/p5-external-symbol-publication-verified-20261111/`.
The [data lifecycle](../data/README.md#accepted-external-symbol-publication-promotion)
owns the operation and persistent recovery contract.

The actual command pinned the prior and approved candidate manifests:

```powershell
.\.venv\Scripts\python.exe -m tools.promote_symbol_publication --candidate local/p5-external-symbol-publication-verified-20261111 --inputs local/p5-accepted-cutover-20261111/promotion-inputs.json --transaction local/p5-accepted-cutover-20261111/publication --expected-current-sha256 92a27c349c6ac23d81de138ee7bff5d196f0f83caa5846417ebd1d89427a3eb5 --expected-candidate-sha256 acb3a2384fc985db59df429ce45daba413452cf1956534a0b1c24d5daebc3948
```

The transaction directory now contains the successful journal, reverified
candidate, and complete prior publication backup. For another accepted input,
select its hashes and a fresh transaction. Recover an **interrupted** promotion
before serving with:

```powershell
.\.venv\Scripts\python.exe -m tools.promote_symbol_publication --recover --transaction local/p5-accepted-cutover-20261111/publication
```

Recovery refuses a completed transaction and unrelated destination drift.
Installation/validation failures and keyboard interruption roll back automatically;
retained backups/journal permit recovery after process loss.

Promotion reverified the entire pinned raw/effective/stage/processed receipt
chain and reproduced the accepted candidate manifest/evidence byte-for-byte.
No SVG acquisition, conversion or compression ran. The only additional file
is the maintained compatibility alias:

`units/combined-army/512-shasvastii-seed-soldiers--1-2.svg`
copies `units/combined-army/512-shasvastii-seed-soldiers.svg`.
Both have SHA-256
`cdaca8ef8ee6494f7e1a539610d7ca1d8384e7b585d4e5d45a96935092961c74`.
The promoted manifest SHA-256 is
`a88c7ead46cb2b68c67deece21af1e2f0a072a3c7a44a8b319ae32f64fc10d17`.
It inventories **807 canonical assets / 808 published URLs**, **10,001,525 bytes**,
807 browser references and one compatibility-only URL. All candidate source and
browser mapping keys are retained. The tracked SVG diff is 118 approved
replacements plus the compatibility filename's replacement.

The complete offline build used the same pinned Army archive:

```powershell
.\.venv\Scripts\python.exe -m infinity_db build "data/raw/JSON 20260929-114335.zip" --compact --db-dir local/p5-accepted-cutover-20261111/runtime
.\.venv\Scripts\python.exe -m tools.verify_deployment_assets --database local/p5-accepted-cutover-20261111/runtime/army.db --rules-database local/p5-accepted-cutover-20261111/runtime/rules_n5.db
```

Only after full three-file integrity, source/build-pair and deployment
validation were the runtime files copied into `data/generated/`, with prior
bytes retained under `local/p5-accepted-cutover-20261111/previous-runtime/`.
Army v31 contains **2,019 mappings / 808 asset hashes**, including the old URL.
Rules v17 and ITS v2 remain required; the ITS bytes are unchanged.
See [exact hashes and validation](testing.md#p57-accepted-symbol-publication-cutover).

The focused cohort passed **97 tests, zero skips**. Actual checkout and Docker
HTTP checks verified all 808 hashes and the old URL's 200/SVG response. Chrome
rendered all 808 assets and normal Army/Seed Soldier pages at 1440/390/320 x 900
without page/request/HTTP errors or horizontal overflow. The final collector
used batches of 16 and no retries. An initial unbounded checkout-gallery probe
had a failed HTTP transfer in the private Windows test server; its diagnostic
is retained separately and is not counted as passing or as capacity evidence.
Both environments also passed the existing **41-route semantic baseline**.
Docker construction and non-root, read-only, three-database runtime checks passed;
the disposable container was stopped. No production deployment occurred.

Private logs, browser receipts, screenshots, prior bytes and transaction state
remain under ignored `local/p5-accepted-cutover-20261111/`. These local checks
accept the publication cutover, not a release tag or hosted CI. The in-tree
processor was subsequently retired; remaining P5 tooling hygiene and P6
integrated/release acceptance remain separate work.

## Original acceptance gates

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
5. These checks preceded retirement of the in-tree pipeline in a separate change.

**Current evidence:** matched-input production processor raster parity
passed, with zero pixel differences across all 807 canonical assets.
The independent artifact verifier and 16 hermetic handoff tests also passed.
The accepted external publication preserves every source/browser mapping key
and the removed URL as a compatibility alias. Artwork approval, candidate promotion,
rebuilt SQLite mappings and checkout/browser/Docker checks are complete for this
cutover. The in-tree processor is retired; final integrated/release acceptance remains open.
The failed historical-output comparison remains preserved separately.
