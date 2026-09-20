# Server migration

This guide identifies the repository-local state that must be transferred when
moving an InfinityDB installation to another server. It distinguishes two goals:

1. **Exact runtime migration** — the new server initially serves the same
   generated databases and locally published graphical assets as the old one.
2. **Reproducible rebuild inputs** — the new server retains the same immutable
   source evidence and local-only inputs so future builds can start from the same
   data and symbol sources.

These goals overlap, but they are not identical. Copying already-generated
runtime artifacts is the strongest way to preserve the exact deployed result.
Reprocessing SVGs on another machine can legitimately produce different bytes if
its fonts or external processing tools differ.

## Record the source revision first

Record the exact Git revision before copying local state:

```sh
git rev-parse HEAD
```

Check out that same commit or release tag on the new server before restoring
ignored/local files. Tracked configuration, curated data, browser mapping files,
schemas, and application code are part of the Git revision and should not be
copied independently from another revision.

Do not run a new acquisition, database build, symbol publication, or deployment
while the migration copy is being taken.

## Exact runtime migration

To make the new server initially serve the same local application data, transfer
these ignored/generated artifacts in addition to checking out the same Git
revision:

```text
data/generated/infinity.db
data/generated/rules.db
data/manifests/army-symbol-build.json
```

If the installation uses locally published Corvus Belli graphical assets, also
transfer the complete published asset contract:

```text
src/infinity_db/web/static/armies/
src/infinity_db/web/static/characteristics/
src/infinity_db/web/static/orders/
src/infinity_db/web/static/units/
src/infinity_db/web/static/symbol-inventory.json
```

The terminal `army-symbol-build.json` and `symbol-inventory.json` are both
required for a guarded graphical deployment: the manifest binds the published set
to its Army snapshot and processing state, while the inventory records every
published SVG path and SHA-256. The tracked `army-symbols.js` and
`unit-symbol-map.js` files come from
the Git revision and must correspond to that publication. If those files contain
uncommitted local changes on the old server, preserve those changes explicitly
rather than assuming a clean checkout will reproduce them.

For the supported Compose deployment, also preserve local deployment state when
applicable:

```text
.infinity-db-deploy.env
```

The Caddy `caddy_data` and `caddy_config` named volumes are not InfinityDB build
inputs, but copy or back them up when their runtime state matters. Configuration,
accounts, or certificates owned by an external TLS reverse proxy are outside this
repository and must be migrated through that system separately.

After restoring the files, use the no-rebuild deployment path from the recorded
revision (`sh ./scripts/deploy-transferred.sh`). Do not run `install-or-update.sh`,
a fresh data build, or a symbol build first when the purpose of the migration is
to preserve the exact existing runtime artifacts.

## Reproducible database rebuild inputs

A future Army database rebuild needs the same tracked Git revision plus the exact
Army source snapshot. For downloader-created snapshots, preserve both the
immutable archive and its generated provenance manifest:

```text
data/raw/JSON YYYYMMDD-HHMMSS.zip
data/manifests/snapshots/JSON YYYYMMDD-HHMMSS.json
```

Downloader-created Army ZIPs contain `metadata.json`. For older/manual source
layouts where metadata is external, preserve the matching `metadata.json`
sidecar as well.

The current `rules.db` is built from tracked curated data under
`data/curated/rules/`; local PDF and wiki research files are not runtime build
inputs for that database.

## Reproducible symbol-source inputs

To preserve the same immutable symbol-source evidence and allow offline/cache
reuse on the new server, transfer:

```text
data/raw/JSON YYYYMMDD-HHMMSS.zip
data/manifests/snapshots/JSON YYYYMMDD-HHMMSS.json

data/raw/symbols/SYMBOLS YYYYMMDD-HHMMSS.zip
data/manifests/snapshots/SYMBOLS YYYYMMDD-HHMMSS.json

data/manifests/army-symbol-build.json
image_overrides/
```

The Army and SYMBOLS snapshot manifests bind the archives by SHA-256.
`army-symbol-build.json` binds the pinned Army/SYMBOLS relationship and records
raw asset provenance, processing state, reports, settings, and final publication
state. Local `image_overrides/` are authoritative build inputs and are ignored by
Git, so they must be copied separately when present.

A completed version-8 manifest is a terminal published state; the pipeline does
not roll it backward to rerun an earlier stage. For a fresh symbol build from the
same source evidence, use the same pinned Army snapshot and retain the prior
validated symbol snapshot/build state as the cache source rather than mutating
the completed manifest.

## Resuming an in-progress symbol build

If the goal is to continue an interrupted build rather than start a fresh one,
copy the manifest-bound derived state together:

```text
data/manifests/army-symbol-build.json
data/work/symbols/
data/reports/symbols/
```

and the pinned Army/SYMBOLS archives and snapshot manifests listed above.
Later-stage resume deliberately verifies existing work instead of silently
recreating it, and referenced reports are SHA-bound build artifacts. Moving only
the manifest is therefore not sufficient for a later-stage resume.

`data/logs/symbols/` is useful diagnostic history but is not a build input.
`data/backups/symbols/` is likewise not required to reproduce the current
publication, but should be transferred when historical copies of symbols removed
by later publications need to be retained.

## Processing environment for regenerated symbols

The symbol pipeline records important converter/renderer identities and settings,
but the repository does not currently pin the complete host processing
environment tightly enough to promise byte-for-byte identical SVG regeneration
on a different machine. When regenerating rather than copying published output,
recreate the same environment as closely as practical, including:

- installed fonts used by the font audit and text conversion;
- Inkscape version/backend used for text-to-path conversion;
- `resvg` version used for visual validation;
- SVGO version used for compression;
- Python version and installed symbol-processing dependency versions.

Do not commit or redistribute third-party font files merely to make a rebuild
portable. Preserve or reinstall them according to their own licensing terms.

For an exact runtime migration, copy the already-published SVGs and inventory
instead of relying on cross-machine SVG regeneration.

## State that does not need to move for a clean rebuild

The following are rebuildable or operational history and are not required for a
clean rebuild from the immutable inputs above:

```text
data/work/
data/reports/
data/logs/
data/backups/
reports/
.venv/
```

There are two exceptions:

- copy `data/work/symbols/` and `data/reports/symbols/` when continuing an
  in-progress symbol build rather than restarting it;
- copy `data/backups/symbols/` when removed-symbol history is intentionally being
  retained.

`data/wiki/` and `data/pdf/` are local research sources. Preserve them when that
research history matters, but they are not required to start the current Army
or rules runtime databases.

## Verification after migration

Before deploying, verify that the new checkout is on the intended revision. On
a validation checkout with `.[dev,symbols]` installed, run the normal project
checks. When a complete local symbol publication was transferred, require full
assets rather than allowing a hermetic fallback:

```text
python tools/run_checks.py --profile all --assets required --report
```

A complete asset check validates the full `symbol-inventory.json` publication,
including published variants that the browser does not yet reference. A partial
or hash-mismatched transferred symbol set fails rather than silently downgrading
to asset-free testing.

For an exact transferred-runtime migration, deploy with
`sh ./scripts/deploy-transferred.sh` after the validation above. For rebuild-mode
deployment, startup, and rollback operations, continue with the
[Linux deployment guide](deployment.md).
