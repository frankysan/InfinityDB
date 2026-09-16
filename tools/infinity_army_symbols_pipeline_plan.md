# Infinity Army + Symbol Pipeline Plan

## Status

This document replaces the earlier symbol-only pipeline plan and treats Army snapshot acquisition and symbol processing as one coordinated, reproducible pipeline.

The design is based on the current project tools:

- `download_army_json.py`
- `download_unit_symbols.py`
- `reorganize_symbols.py`
- `path_sanitization.py`
- `svg_processor.py`
- `svg_compress.py`

The scripts should remain individually usable, but their reusable logic should gradually be exposed to a thin top-level orchestrator.

---

## 1. Verified source-data findings

The raw Army snapshot `JSON 20260910-204106.zip` contains **59 JSON files**: `metadata.json` plus **58 faction/unit documents**.

A recursive scan of every string value in the raw snapshot found:

| Source | SVG references | Unique SVG URLs |
| --- | ---: | ---: |
| `units[].profileGroups[].profiles[].logo` | 5,020 | 1,033 |
| `resume[].logo` | 4,137 | 862 |
| `metadata.json -> factions[].logo` | 58 | 57 |
| **Total raw references** | **9,215** | **1,090** |

The 1,090 unique URLs consist of:

- **1,033 unit/profile SVGs** under `/army/img/logo/units/`
- **57 faction SVGs** under `/army/img/logo/factions/`

No other SVG/image categories were found in the raw snapshot. In particular, the snapshot does not expose additional order, skill, equipment, weapon, PNG, JPEG, WebP, or GIF assets.

The normalized JSON preserves the same **1,090 unique SVG URLs**. Its higher raw reference count is caused by faction metadata being represented in more than one normalized location, not by additional source assets.

### Important downloader gap

The current unit-symbol downloader effectively chooses the first profile logo seen for each unit ID. Reproducing that behavior against the raw snapshot yields only **861 unique unit SVGs**.

The authoritative profile data contains **1,033 unique unit SVGs**, so the current logic can miss:

**172 distinct unit SVGs.**

There are **136 unit IDs** in this snapshot that reference more than one distinct profile logo.

Therefore:

> Symbol discovery must be keyed by asset URL/reference, not by unit ID.

A unit can reference several symbols, and several units/profiles can reference the same symbol.

---

## 2. Authoritative discovery sources

The new symbol discovery stage should use these semantic sources:

```text
metadata.json
  data.factions[].logo
      -> faction symbols

<faction>.json
  units[].profileGroups[].profiles[].logo
      -> unit/profile symbols
```

`resume[].logo` is useful as a validation source, but it is **not authoritative for complete symbol discovery** because it contains fewer unique unit symbols than the full profile tree.

### Recursive schema audit

In addition to semantic discovery, every build should recursively scan all strings in the snapshot for SVG references.

The recursive scan is an **audit**, not the primary downloader.

Expected result for the 2026-09-10 snapshot:

```text
Known semantic SVG URLs:  1,090
All recursive SVG URLs:   1,090
Unknown SVG locations:    0
```

If a later Army API version introduces a new SVG-bearing field, such as an order or marker icon, the build should report it rather than silently ignore it.

Unknown locations should fail validation by default or at minimum produce a prominent warning requiring review.

---

## 3. Core architectural rules

### 3.1 One immutable snapshot per build

Every downstream stage must consume the **same exact Army snapshot archive**.

Once a build starts, the snapshot is pinned by:

- archive path
- archive SHA-256
- language
- acquisition timestamp
- API base URL

For the inspected snapshot:

```text
archive: JSON 20260910-204106.zip
sha256: 504f8865c68d2e41108a11fc1acee670e372102e251645a32a3e767d017dfd18
```

No downstream stage may independently choose a newer snapshot.

### 3.2 Overrides supersede downloads

Local image overrides are authoritative.

Before any network request for an image asset, the resolver must check `image_overrides/`. If an override exists for that asset, the override is used and the upstream image is not downloaded.

This serves two purposes:

- avoid unnecessary repeated requests to Corvus Belli asset hosts
- allow known-bad upstream images to be locally corrected

Overrides remain separate from downloaded raw files so provenance is always clear.

### 3.3 Raw downloads are immutable

Downloaded Army JSON and downloaded SVGs are source material.

They must never be renamed, moved, rewritten, normalized, compressed, or deleted by later processing stages.

### 3.4 References and assets are different entities

The pipeline must distinguish:

- **reference**: a unit/profile/faction points at a source URL
- **source asset**: a unique downloaded SVG URL/file
- **canonical asset**: the surviving representative after duplicate detection
- **published asset**: the final project-facing SVG path

This distinction is essential because many references may point to one source asset, and several different source assets may later collapse to one visual canonical asset.

### 3.5 Deduplicate before expensive conversion

Duplicate detection runs across the full raw SVG set before text-to-path conversion.

### 3.6 Publishing is the only stage that defines final application paths

The downloader must not generate the final browser mapping. Only the publisher knows the final canonical output path after deduplication, conversion, compression, and organization.

---

## 4. End-to-end pipeline

```text
Corvus Belli Army API
        |
        v
0. Acquire + validate Army snapshot
        |
        v
Immutable timestamped snapshot ZIP
        |
        v
1. Discover symbol references
        |
        +---- profile logos
        |
        +---- faction logos
        |
        +---- manually declared characteristic/order assets
        |
        +---- recursive unknown-SVG audit
        |
        v
2. Resolve image source
        |
        +---- image_overrides (highest priority)
        |
        +---- existing raw cache
        |
        +---- network download (last resort)
        |
        v
3. SVG audit + font classification
        |
        v
4. Full-set duplicate detection
        |
        v
5. Canonical representative selection
        |
        v
6. Text -> path conversion of canonical targets only
        |
        v
7. Compress canonical path-only SVGs
        |
        v
8. Publish final project asset tree
        |
        v
9. Generate application mappings + build report
```

---

## 5. Proposed directory layout

```text
config/
  symbols/
    static-symbols.json
    override-notes.json        # optional metadata only; no SVG content

image_overrides/              # local only; gitignored
  units/
  factions/
  characteristics/
  orders/

data/
  raw/
    army/
      JSON YYYYMMDD-HHMMSS.zip

    symbols/
      units/
        <original downloaded unit SVGs>
      factions/
        <original downloaded faction SVGs>

  work/
    symbols/
      classified/
        fonts_available/
        fonts_missing/
        no_active_text/
        parse_errors/

      canonical/
      converted/
      compressed/
      duplicates/

  manifests/
    army-symbol-build.json

  reports/
    symbol-discovery.csv
    unknown-svg-references.csv
    svg-font-report.csv
    missing-fonts.csv
    unused-font-declarations.csv
    svg-parse-errors.csv
    duplicate-groups.csv
    duplicate-render-errors.csv
    duplicate-separation.csv
    duplicate-summary.csv
    svg-text-to-path-report.csv
    text-conversion-summary.csv
    compression-report.csv
    compression-candidates.csv
    compression-run.json

src/infinity_db/web/static/
  units/
    <army-slug>/
      <published canonical unit assets>

  armies/
    <published faction assets>

  characteristics/
    <published characteristic assets>

  orders/
    <published order assets>

  unit-symbol-map.js
  army-symbols.js
```

The exact roots should be configurable. The conceptual separation should not be.

---

## 6. Authoritative build manifest

Use one JSON manifest as the machine-readable state passed through the pipeline.

A better model than a filename-keyed object is to separate **assets** from **references**.

Example:

```json
{
  "schema_version": 1,
  "snapshot": {
    "archive": "JSON 20260910-204106.zip",
    "sha256": "504f8865c68d2e41108a11fc1acee670e372102e251645a32a3e767d017dfd18",
    "language": "en",
    "api_base_url": "https://api.corvusbelli.com/army"
  },
  "assets": {
    "https://assets.corvusbelli.net/army/img/logo/units/example-1-1.svg": {
      "kind": "unit",
      "source_filename": "example-1-1.svg",
      "source_sha256": "...",
      "classification": "fonts_available",
      "duplicate_group": "V0042",
      "canonical_url": "https://assets.corvusbelli.net/army/img/logo/units/example.svg",
      "is_canonical": false,
      "conversion": {
        "required": true,
        "status": "skipped_duplicate"
      },
      "compression": {
        "status": "inherited_from_canonical"
      },
      "published_asset": "units/panoceania/123-example.svg"
    }
  },
  "references": [
    {
      "kind": "unit-profile",
      "source_document": "101-panoceania.json",
      "json_path": "units[...].profileGroups[...].profiles[...].logo",
      "unit_id": 123,
      "unit_slug": "example",
      "army_id": 101,
      "asset_url": "https://assets.corvusbelli.net/army/img/logo/units/example-1-1.svg"
    },
    {
      "kind": "faction",
      "source_document": "metadata.json",
      "faction_id": 101,
      "faction_slug": "panoceania",
      "asset_url": "https://assets.corvusbelli.net/army/img/logo/factions/panoceania.svg"
    }
  ]
}
```

This structure naturally handles many-to-many relationships and duplicate canonicalization.

### Manifest information

The manifest should eventually carry:

**Snapshot**
- archive path/name
- archive hash
- language
- acquisition timestamp
- API version(s), if available
- source document count

**Asset**
- kind: `unit`, `faction`, or future category
- source URL
- source filename
- download state
- source SHA-256
- font classification
- alias-normalization information
- duplicate group
- canonical source URL/asset ID
- conversion state/backend
- compression state/profile
- final published path

**Reference**
- source document
- JSON path
- reference kind
- unit/faction IDs and slugs where applicable
- source asset URL

---

## 7. Stage 0 — Army snapshot acquisition

### Current tool

`download_army_json.py`

### Current behavior worth keeping

It already:

- downloads metadata
- validates metadata
- downloads every faction listed by metadata
- validates every faction document
- writes through temporary files
- archives one complete snapshot to a timestamped ZIP
- performs network access only when explicitly executed

### Planned changes

Keep its standalone CLI.

Expose reusable functions so the orchestrator can:

1. fetch a new snapshot explicitly
2. receive the resulting archive path
3. calculate/build snapshot identity metadata
4. continue the symbol pipeline using exactly that archive

Normal project builds must **not** silently contact the Army API.

Recommended modes:

```bat
REM Rebuild from a known snapshot
python tools/build_symbols.py --snapshot "data/raw/army/JSON 20260910-204106.zip"

REM Explicitly acquire a fresh snapshot, then build
python tools/build_symbols.py --fetch-snapshot
```

`--snapshot` and `--fetch-snapshot` should be mutually exclusive.

---

## 8. Stage 1 — Symbol discovery

### Replace the current first-logo-per-unit logic

The existing `download_unit_symbols.py` should no longer select one logo per unit.

Instead collect:

```text
all unique units[].profileGroups[].profiles[].logo URLs
all unique metadata factions[].logo URLs
```

Deduplicate **downloads** by URL, while preserving every reference to each URL.

### Rename

`download_unit_symbols.py` should likely become:

```text
download_army_symbols.py
```

because it will handle both unit and faction symbols.

### Discovery output

Before downloading, generate a discovery section/report containing:

```text
profile references
unique unit URLs
faction references
unique faction URLs
recursive SVG count
unknown SVG paths
```

For the inspected snapshot the baseline is:

```text
Unit/profile SVGs:  1,033
Faction SVGs:          57
Total unique SVGs:  1,090
Unknown SVG paths:      0
```

### `resume[].logo`

Do not use `resume` as the authoritative source.

It may be checked for consistency and included in reference metadata if useful, but it does not contain the complete unit-symbol set.

---

## 9. Manual static assets and image overrides

Some SVGs required by the web application are not referenced by the Army API but are available at stable static URLs.

These should be declared explicitly rather than inferred.

### Static asset manifest

Some SVGs required by the web application are not referenced by the Army API but are available at stable Corvus Belli URLs.

Maintain them explicitly in the committed project configuration:

```text
config/symbols/static-symbols.json
```

The currently known set is:

```text
Characteristics
---------------
cube.svg
cube2.svg
hackable.svg
peripheral.svg

Orders
------
regular.svg
irregular.svg
tactical.svg
lieutenant.svg
impetuous.svg
```

All nine currently share this base URL:

```text
https://assets.corvusbelli.net/army/img/icon/
```

Recommended manifest structure:

```json
{
  "schema_version": 1,
  "base_url": "https://assets.corvusbelli.net/army/img/icon/",
  "assets": {
    "characteristics": [
      "cube.svg",
      "cube2.svg",
      "hackable.svg",
      "peripheral.svg"
    ],
    "orders": [
      "regular.svg",
      "irregular.svg",
      "tactical.svg",
      "lieutenant.svg",
      "impetuous.svg"
    ]
  }
}
```

These declarations join API-discovered assets before source resolution, so downstream processing does not need to care whether an asset came from the Army JSON or from the manually maintained list.

Do not hardcode these URLs inside the downloader.

The manifest is project-owned and should be version-controlled.

`image_overrides/` is intentionally **not** version-controlled. Even when an override is recreated or repaired locally, it may remain derivative of Corvus Belli artwork, so the repository should not redistribute those SVGs unless redistribution rights are established separately.

### `image_overrides/`

Add a project-owned override tree:

```text
image_overrides/
  units/
  factions/
  characteristics/
  orders/
```

The preferred lookup key is the asset's stable URL-derived logical name/category, not a generated final publication filename.

For Corvus Belli logo URLs this maps naturally:

```text
.../army/img/logo/units/foo.svg
    -> image_overrides/units/foo.svg

.../army/img/logo/factions/bar.svg
    -> image_overrides/factions/bar.svg
```

Manually declared assets use their semantic category directly:

```text
image_overrides/characteristics/cube.svg
image_overrides/orders/regular.svg
```

If later asset classes need overrides, add another explicit category rather than putting unrelated files into one flat directory.

`cube.svg` is the first confirmed visual-correction override. The upstream Corvus Belli file contains embedded raster/mask content and renders with visible horizontal artifacts; the local override is a compact clean-vector reconstruction. The override must therefore be treated as authoritative and must suppress any upstream download for that asset.

### Resolution order

For every discovered or manually declared asset:

```text
1. matching image override
2. existing validated raw cached file
3. upstream network download
```

If step 1 succeeds, **no request is made for that asset**.

If step 2 succeeds, no request is made unless an explicit refresh mode is requested.

Only step 3 accesses the Corvus Belli host.

### Override processing

An override replaces the upstream **source image**, not the final processed image.

By default it still passes through:

```text
svg_processor.py
  -> deduplication
  -> text-to-path if needed
  -> svg_compress.py
  -> publisher
```

This keeps the final asset set subject to the same validation and optimization rules.

A future `publish_as_is` option could be added if a genuine use case appears, but it should not be the default.

### Provenance

The build manifest should distinguish:

```json
{
  "origin_url": "https://assets.corvusbelli.net/...",
  "resolved_source": "image_overrides/units/foo.svg",
  "source_method": "override",
  "override_sha256": "...",
  "upstream_downloaded": false
}
```

For a cached/downloaded asset:

```json
{
  "origin_url": "https://assets.corvusbelli.net/...",
  "resolved_source": "data/raw/symbols/units/foo.svg",
  "source_method": "cache",
  "source_sha256": "..."
}
```

or:

```json
{
  "source_method": "download"
}
```

This makes it possible to tell later whether a published image came from Corvus Belli unchanged or from a deliberate local correction.

### Override validation

Before accepting an override:

- it must exist as a regular file
- it must parse as SVG
- its category/key must resolve to a known asset declaration unless explicitly marked as a standalone manual asset
- duplicate override keys are an error

Unused overrides should be reported. They may indicate that an upstream filename changed or that a local fix is no longer referenced.

### Repository / redistribution policy

The repository should contain the pipeline logic and metadata, but not locally corrected Corvus Belli-derived SVGs by default.

Recommended Git policy:

```gitignore
/image_overrides/
/data/raw/
/data/work/
/data/manifests/
/data/reports/
```

Committed inputs:

```text
config/symbols/static-symbols.json
config/symbols/override-notes.json   # optional
```

Local/non-committed inputs:

```text
image_overrides/
```

Generated/non-committed content:

```text
data/raw/
data/work/
data/manifests/
data/reports/
```

A clean checkout therefore remains functional without overrides:

```text
override present      -> use local override
override absent       -> use validated raw cache if present
cache absent          -> download upstream asset
```

For overrides that exist to fix visual defects, a clean checkout may reproduce the upstream defect. To document this without redistributing the corrected SVG, an optional committed metadata file can record expected/recommended overrides:

```json
{
  "characteristics/cube.svg": {
    "override_recommended": true,
    "reason": "Upstream SVG renders with horizontal raster artifacts"
  }
}
```

This metadata is informational. It must not contain embedded SVG/raster content.

---

## 10. Stage 2 — Raw symbol acquisition

Resolve every discovered/manual asset using the override/cache/network priority defined above.

Network-downloaded SVGs are stored in immutable raw categories:

```text
data/raw/symbols/units/
data/raw/symbols/factions/
data/raw/symbols/characteristics/
data/raw/symbols/orders/
```

### Rules

- check `image_overrides` before any network access
- reuse an existing validated raw file before downloading
- derive safe local filenames from the URL
- validate asset host/path
- validate that a downloaded response is SVG
- do not overwrite existing raw files unless explicit refresh behavior is requested
- preserve source URL, resolved source path, resolution method, and SHA-256 in the build manifest

Future useful options:

```text
--refresh-symbols
--verify-existing
--download-delay
```

If the same local filename could map to two different URLs, treat that as a collision requiring deterministic disambiguation rather than silently overwriting.

---

## 11. Stage 3 — SVG audit and font classification

Run the unified SVG processor across the entire downloaded raw SVG collection.

Responsibilities:

- parse SVG
- detect active text
- identify referenced fonts
- classify:
  - `no_active_text`
  - `fonts_available`
  - `fonts_missing`
  - parse/error states
- resolve known font aliases
- normalize font declarations as needed for conversion
- preserve standard SVG namespaces
- emit human-readable reports
- update machine-readable asset records

Unit and faction symbols should both pass through this stage unless testing establishes that a class can safely bypass it.

---

## 12. Stage 4 — Full-set duplicate detection

Duplicate detection must include **all downloaded source SVGs before conversion**.

### Production backend

```text
renderer: resvg
jobs: 4
```

### Detection sequence

1. calculate SHA-256
2. group exact-byte duplicates
3. render one representative from each byte-unique set
4. compare rendered outputs
5. form visual duplicate groups
6. choose one canonical representative per group

### Canonical ranking

Current preferred deterministic ranking:

1. `no_active_text`
2. `fonts_available`
3. `fonts_missing`
4. parse error / unknown
5. shorter filename
6. alphabetical source path/name

This minimizes conversion work and prefers simpler names.

### Important rule

Removing a duplicate from active processing must **not remove its references**.

Every original source URL remains in the manifest and points to its canonical asset.

---

## 13. Stage 5 — Text-to-path conversion

Only canonical assets that still contain active text and have resolvable fonts should be converted.

### Production backend

```text
converter: inkscape-shell
jobs: 4
```

Persistent shell workers are the production choice because they retain Inkscape rendering fidelity while avoiding repeated Windows startup cost.

### Other backends

- one-shot `inkscape`: fallback/debugging
- `usvg`: experimental only; it produced visual differences in real symbol tests

### Validation

After conversion:

- SVG parses successfully
- meaningful active `<text>` no longer remains
- empty text placeholders may be removed
- namespaces remain standards-compliant

Conversion failure should not silently publish an unverified replacement.

---

## 14. Stage 6 — SVG compression

Keep `svg_compress.py` as a reusable standalone component, but make it callable by the orchestrator.

### Production defaults

```text
profile: balanced
renderer: resvg
precision: p2 first, p3 rescue
```

Current validation settings:

```text
target sizes: 32,64
DPRs: 1,2
max RMS: 0.01
max changed fraction: 0.01
pixel diff threshold: 8
```

Only canonical assets need compression.

If no lossy candidate passes visual validation, use the validated lossless output.

---

## 15. Stage 7 — Publishing / project organization

### Current problem

`reorganize_symbols.py` is currently migration-oriented: it moves source files, renames them, rewrites maps, and removes old directories.

That is inappropriate for a repeatable build.

### New responsibility

Refactor it into a **non-destructive publisher** that consumes:

- the pinned snapshot
- the authoritative build manifest
- the final canonical/compressed asset directory

It should:

- materialize the final project asset tree
- copy rather than move source/work files
- generate deterministic final names
- map multiple source references to one canonical physical file
- publish faction symbols as well as unit symbols
- generate application maps only after final paths are known
- leave the previous published tree untouched if publication fails

### Unit output convention

Retain the useful existing convention where possible:

```text
units/<army-slug>/<unit-id>-<unit-slug>.svg
```

But the filename belongs to the **canonical physical asset**, not necessarily every unit that references it.

Several units may map to the same final path.

### Faction output convention

Use:

```text
armies/<faction-id>-<faction-slug>.svg
```

or retain the currently expected application format if compatibility requires something different.

The exact naming format should be decided before refactoring browser mappings.

---

## 16. Application mappings

Browser/application mappings belong to the publisher, not the downloader.

The publisher knows:

- the original unit/faction reference
- the source SVG
- the canonical duplicate representative
- the final published path

Conceptually:

```javascript
const unitSymbols = new Map([
  ["unit-a", "nomads/123-unit-a"],
  ["unit-b", "nomads/123-unit-a"]
]);
```

One physical SVG may therefore serve several unit slugs.

Existing application APIs should be preserved where practical so this refactor does not unnecessarily affect frontend code.

---

## 17. Non-API/static symbols

The inspected raw Army snapshot contains **no authoritative order-symbol or other auxiliary SVG references**.

Assets required by the web application but absent from the API should therefore be maintained in `static-symbols.json` with their known stable source URLs.

The currently known non-API categories are:

- `characteristics`: `cube`, `cube2`, `hackable`, `peripheral`
- `orders`: `regular`, `irregular`, `tactical`, `lieutenant`, `impetuous`

These are normal pipeline assets after source resolution; they should pass through `svg_processor.py`, deduplication, text conversion if needed, compression, and publishing exactly like API-discovered unit and faction SVGs.

Those assets then use exactly the same source-resolution policy as API-discovered assets:

```text
override -> raw cache -> network
```

If the Army API later begins exposing one of these categories directly, discovery can migrate to the API source while preserving the same logical asset identity and override behavior.

---

## 18. Shared path sanitization

`path_sanitization.py` should remain shared infrastructure.

It already centralizes safe filename/path rules.

For long-term reproducibility, consider making generated project asset names follow one fixed policy independent of the host operating system, while still retaining OS-safe handling for mirrored external paths.

---

## 19. Top-level orchestrator

Add:

```text
tools/build_symbols.py
```

It should coordinate stages, not duplicate their implementation.

Recommended interface:

```bat
REM Offline/reproducible build
python tools/build_symbols.py --snapshot "data/raw/army/JSON 20260910-204106.zip"

REM Explicit online refresh + build
python tools/build_symbols.py --fetch-snapshot
```

Useful options:

```text
--snapshot PATH
--fetch-snapshot
--snapshot-only
--language en
--data-root PATH
--static-root PATH
--jobs 4
--image-overrides PATH
--static-symbols PATH        # default: config/symbols/static-symbols.json
--refresh-symbols
--skip-symbol-download
--skip-compression
--keep-work
--dry-run
```

### Orchestrator sequence

```text
0. acquire or select snapshot
1. validate + fingerprint snapshot
2. discover semantic SVG references
3. load manually declared static assets
4. recursively audit for unknown SVG locations
5. build/update manifest references and asset inventory
6. resolve every asset: override -> validated cache -> network
7. audit/classify resolved SVGs
8. detect duplicates
9. select canonical assets
10. convert canonical text assets
11. compress canonical assets
12. build temporary published asset tree
13. generate application mappings
14. validate publication
15. replace generated published tree
16. write final build report
```

---

## 20. Idempotency and incremental builds

Every stage should be safe to rerun.

### Snapshot

Never overwrite a timestamped snapshot.

### Overrides

Changes to an override's SHA-256 invalidate downstream processing for that asset.

Removing an override causes the resolver to fall back to the validated raw cache or network according to normal rules.

### Downloads

Reuse validated raw files.

### Processing

Eventually cache work using:

- snapshot SHA-256
- source SVG SHA-256
- processor/tool version
- font alias configuration version
- duplicate renderer/version/settings
- text converter/version/settings
- compression profile/settings

The first integrated version does not need sophisticated caching; correctness and traceability come first.

---

## 21. Failure policy

Fail conservatively.

### Snapshot acquisition/validation

- do not continue with a partial snapshot
- leave previous snapshots and published assets untouched

### Schema/SVG discovery audit

If recursively discovered SVG URLs are not covered by known semantic discovery:

- report their JSON paths and URLs
- do not silently ignore them
- require explicit handling or an intentional allowlist decision

### Override failure

- an invalid matching override is an error; do not silently fall back to the upstream file
- report unused overrides
- preserve the previous published tree

### Symbol download

- preserve existing raw files
- report failed URLs
- do not publish an incomplete replacement build

### SVG parse/font errors

- retain source
- report it
- do not silently discard it

### Duplicate rendering

If a comparison cannot be established, treat the asset as unique rather than removing it.

### Text conversion

Do not claim success or replace a canonical source with a failed conversion.

### Compression

Fall back to validated path-only/lossless canonical SVG.

### Publishing

Build into a temporary tree first. On failure, leave the previous published tree intact.

---

## 22. Reports

Keep detailed CSV/JSON reports for diagnosis, plus one concise build summary.

Example for the current source snapshot before SVG processing:

```text
Snapshot:                  JSON 20260910-204106.zip
Snapshot SHA-256:          504f8865c68d2e41108a11fc1acee670e372102e251645a32a3e767d017dfd18
Faction/unit documents:    58
Metadata documents:         1

Profile SVG references:  5,020
Unique unit SVGs:        1,033
Faction SVG references:     58
Unique faction SVGs:        57
Unique source SVGs:      1,090

resume SVG references:   4,137
Unique resume SVGs:        862

Current old downloader:     861
Unit SVGs previously missed:  172

Unknown SVG locations:       0
```

Later sections add:

- override assets used
- unused overrides
- assets satisfied from raw cache
- network downloads performed
- manually declared characteristic/order assets
- raw files present/downloaded
- exact/visual duplicate counts
- canonical asset count
- conversion targets/results
- compression results
- published unit/faction assets
- application mapping counts
- per-stage and total runtime

---

## 23. Script-by-script change plan

### `download_army_json.py`

Keep:
- API request behavior
- validation
- timestamped ZIP archive
- standalone explicit invocation

Change:
- expose snapshot identity/result to reusable callers
- optionally move reusable implementation into a package module later

### `download_unit_symbols.py`

Rename to `download_army_symbols.py`.

Replace:
- first logo per unit
- unit-ID deduplication
- early browser manifest generation

With:
- every profile logo
- every faction logo
- manually declared characteristic/order assets
- override-first source resolution
- URL-level asset deduplication
- full reference preservation
- recursive unknown-SVG audit
- structured manifest output/update

### `svg_processor.py`

Keep:
- font audit
- alias normalization
- complete-input duplicate detection
- deterministic representative ranking
- persistent Inkscape conversion
- CSV reports

Add:
- structured JSON manifest updates
- support unit + faction raw directories as one processing set

### `svg_compress.py`

Keep standalone CLI and current production defaults.

Add:
- importable entry point/result object for orchestration
- manifest status updates

### `reorganize_symbols.py`

Refactor into publisher.

Replace destructive moves/deletes with deterministic materialization from processed canonical assets.

Move final unit/faction JS map generation here.

### `path_sanitization.py`

Keep shared.

Only reconsider host-dependent behavior if cross-platform generated filenames prove unstable.

---

## 24. Recommended code organization

Longer term:

```text
config/
  symbols/
    static-symbols.json
    override-notes.json

image_overrides/              # local, gitignored

tools/
  build_symbols.py
  download_army_json.py
  download_army_symbols.py
  reorganize_symbols.py
  svg_processor.py
  svg_compress.py
  path_sanitization.py

  symbols/
    snapshot.py
    discovery.py
    manifest.py
    downloader.py
    audit.py
    deduplicate.py
    convert.py
    compress.py
    publish.py
```

CLI scripts become thin wrappers around reusable functions.

External executables remain subprocesses:

- Inkscape
- resvg
- SVGO

---

## 25. Testing strategy

### Snapshot/discovery tests

Test:

- metadata validation
- faction-document validation
- complete snapshot archive creation
- snapshot hash/identity
- discovery of all profile logos
- discovery of all faction logos
- several logos for one unit
- one logo referenced by several units
- duplicate URLs
- manually declared characteristic/order URLs
- matching override suppresses network access
- override supersedes an existing raw cached SVG
- invalid override fails instead of silently using upstream
- unused override reporting
- filename collisions
- recursive detection of an unexpected SVG field
- proof that `resume` is not required for complete discovery

### SVG processing fixture

Include:

- exact duplicate pair
- XML-different visual duplicate pair
- no-text SVG
- normal text SVG
- alias-font SVG
- missing-font SVG
- SVG requiring empty-text cleanup
- troublesome real-world conversion cases used during earlier testing

### Publishing tests

Test:

- several references -> one canonical asset
- faction publishing
- deterministic paths
- no destructive raw/work mutations
- failed build leaves previous static tree intact

---

## 26. Production defaults established so far

### Repository/source policy

```text
static symbol declarations: config/symbols/static-symbols.json
image overrides:            local + gitignored
downloaded raw assets:      local/generated + gitignored
build manifests/reports:    generated + gitignored
```

Overrides may be documented in committed metadata without committing the image content itself.


### Duplicate rendering

```text
renderer: resvg
jobs: 4
```

### Text-to-path

```text
converter: inkscape-shell
jobs: 4
```

One-shot Inkscape remains fallback/debugging.

`usvg` remains experimental because it produced visible differences in real font-heavy SVGs.

### Compression

```text
profile: balanced
renderer: resvg
precision order: p2, then p3 rescue
```

---

## 27. Recommended implementation order

1. Define the exact manifest schema, separating assets from references.
2. Define `config/symbols/static-symbols.json`, the local `image_overrides/` naming convention, and repository ignore policy.
3. Refactor snapshot handling just enough to expose snapshot identity to the orchestrator.
4. Replace symbol discovery with complete profile + faction discovery and load manual static declarations.
5. Add recursive unknown-SVG auditing.
6. Rename/refactor `download_unit_symbols.py` to `download_army_symbols.py`.
7. Implement override-first / cache-second / network-last source resolution.
8. Make raw downloaded symbol files immutable and manifest-backed.
9. Add JSON manifest updates to `svg_processor.py`.
10. Process all resolved symbol categories together for classification/deduplication.
11. Add compression manifest updates.
12. Refactor `reorganize_symbols.py` into a non-destructive publisher.
13. Move final JS mapping generation to the publisher.
14. Create `build_symbols.py`.
15. Add an end-to-end regression fixture including overrides.
16. Add hash/configuration-based incremental caching only after the integrated build is stable.

---

## 28. Intended normal workflow

### Rebuild from a known snapshot

```bat
python tools/build_symbols.py --snapshot "data/raw/army/JSON 20260910-204106.zip"
```

No Army API request is made.

### Fetch a new snapshot and rebuild

```bat
python tools/build_symbols.py --fetch-snapshot
```

The newly downloaded snapshot is pinned immediately and drives every downstream stage.

The complete process then becomes:

```text
snapshot
 -> discover all API-referenced symbols
 -> add manually declared characteristic/order symbols
 -> audit schema for unknown SVG sources
 -> resolve each image: override -> raw cache -> network
 -> classify fonts
 -> deduplicate full source set
 -> select canonical SVGs
 -> convert canonical text to paths
 -> compress
 -> publish unit/faction assets
 -> generate application mappings
 -> validate
 -> report
```

Individual stage tools remain directly runnable for debugging and targeted maintenance.

---

## Cross-platform compatibility requirements

Cross-platform support is a first-class requirement for the entire Army/SVG pipeline. All Python tools should support **Windows, Linux, and macOS**.

### Core rules

- Use `pathlib.Path` for filesystem paths.
- Use `subprocess.run()` / `subprocess.Popen()` with argument lists rather than shell command strings.
- Avoid `shell=True` unless there is no practical alternative.
- Do not rely on CMD, PowerShell, Bash, `^`, `&&`, or platform-specific quoting inside pipeline code.
- Use `shutil.which()` for executable discovery.
- Allow explicit executable paths through CLI/configuration.
- Use UTF-8 explicitly for generated text files.
- Use LF (`\n`) for generated project/config files unless an external format requires otherwise.
- Treat filenames as case-sensitive internally, even on case-insensitive filesystems.
- Do not assume symlink support.
- Do not assume executable extensions.
- Do not persist absolute machine-specific paths unless they are clearly transient build metadata.
- Generated project asset names should follow one deterministic, conservative naming policy that is valid on all three platforms.

### External tools

The current external executables are:

- Inkscape
- resvg
- SVGO

Executable discovery order should be:

```text
1. explicit CLI/config path
2. shutil.which(...)
3. small platform-specific fallback locations
4. clear installation error
```

The lookup layer should support common platform variants such as:

```text
inkscape / inkscape.exe
resvg / resvg.exe
svgo / svgo.cmd
```

Do not hardcode Windows paths such as:

```text
C:\Program Files\Inkscape\bin\inkscape.exe
```

into core pipeline logic.

If SVGO is later pinned through `package.json`, prefer the project-local executable over an arbitrary global installation.

### Inkscape shell backend

The persistent `inkscape --shell` backend should be launched directly through `subprocess.Popen()` using stdin/stdout pipes.

It must not depend on PowerShell, CMD, Bash, or terminal-specific syntax.

The slow Windows startup behavior is treated as an external Inkscape limitation; persistent workers remain the production design on every platform.

### Paths and persistent manifests

Persistent manifest paths should use project-relative POSIX-style strings:

```text
units/panoceania/123-example.svg
```

Convert those strings to native `Path` objects only when accessing the local filesystem.

This prevents manifests generated on one operating system from becoming unusable on another.

### Temporary files

Use Python's `tempfile` module for ephemeral work.

Use `data/work/` only when retained intermediate files are useful for diagnostics.

Do not assume either:

```text
C:\Temp
/tmp
```

### Filename policy

`path_sanitization.py` may retain OS-specific behavior for external mirroring tasks, but **pipeline-generated asset names should be host-independent**.

The common policy should be safe on Windows, Linux, and macOS:

- lowercase
- ASCII where required by existing project conventions
- dash-separated
- no Windows-reserved characters
- no trailing spaces or dots
- no Windows reserved device names
- conservative path-component length

The pipeline must detect case-only collisions such as:

```text
Foo.svg
foo.svg
```

before publishing.

### Atomic writes

Persistent generated files should be written to a temporary file and atomically replaced where practical.

This applies especially to:

- JSON manifests
- CSV reports
- generated JavaScript mappings
- snapshot metadata
- final build state

Interrupted execution should not leave partially written persistent files.

### Concurrency

Use Python concurrency primitives rather than shell job control.

Any process-based concurrency must be compatible with Windows' `spawn` model.

For subprocess-heavy stages such as Inkscape and resvg, threads remain preferable unless there is a clear reason to use multiprocessing.

### Cross-platform testing

The core test suite should eventually run in CI on:

```text
Windows
Ubuntu/Linux
macOS
```

At minimum test:

- path generation and sanitization
- project-relative manifest paths
- executable discovery
- `.exe` / `.cmd` handling
- subprocess argument construction without shell quoting
- temporary-file behavior
- case-only filename collision detection
- snapshot ZIP handling
- override lookup
- static-symbol manifest loading
- atomic file replacement
- any process-based concurrency under Windows `spawn`

External-tool integration tests may be conditional when Inkscape, resvg, or SVGO are not installed.

### Implementation impact

Before the individual pipeline stages are tied together, add a small shared utility layer for:

- executable discovery
- native/project-relative path conversion
- atomic writes
- subprocess invocation
- platform-neutral filename generation

This avoids duplicating OS-specific logic across:

```text
download_army_json.py
download_army_symbols.py
svg_processor.py
svg_compress.py
reorganize_symbols.py
build_symbols.py
```

Cross-platform behavior should therefore be designed once and reused throughout the pipeline.

