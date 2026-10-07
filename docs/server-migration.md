# Server migration

**Project domain:** Deployment

A released InfinityDB checkout is now self-contained for runtime deployment. The tracked Git
revision supplies the application, `infinity.db`, `rules.db`, processed SVG publication, and
`symbol-publication.json`. Raw Army/wiki/PDF/source-symbol archives and terminal symbol build state
are development/rebuild inputs, not server deployment requirements.

## Exact runtime migration

Record the deployed revision on the old host:

```sh
git rev-parse HEAD
git describe --tags --exact-match
```

Clone the repository on the replacement host and check out the same release tag, confirming that it
resolves to the recorded commit. No
runtime database or symbol files need to be copied separately: their exact bytes are part of that
Git revision.

Preserve the ignored deployment configuration when applicable:

```text
.infinity-db-deploy.env
```

That file may contain the public domain, image-retention setting, and optional LAN metrics bind
address/port. Update a stored metrics address if the replacement server uses a different LAN
address.

Caddy named volumes are operational state rather than InfinityDB release inputs. Back them up when
their state matters. Certificates/configuration owned by an external TLS reverse proxy must be
migrated through that system separately.

The `metrics_history` named volume is also persistent operational state. To preserve retained
history, take a consistent backup with the old collector stopped (or use SQLite's online backup
facility), and restore it into the replacement stack's history volume before starting its collector.
Keep the same Compose project name or explicitly map the restored volume so Compose does not create
an empty store under a different name. Preserve ownership for the image's unprivileged collector
user; do not migrate `.venv` or substitute the history database for a runtime game database.
The [history format and rollback contract](deployment.md#retained-metrics-history) remains applicable:
an older collector must not downgrade or delete a newer history store.

For an exact-version migration, prepare the virtual environment from the checked-out release and
invoke its low-level deployment script. For releases with the current deployment contract:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
release_tag="$(git describe --tags --exact-match)"
# Replace the example hostname and restore the recorded metrics/retention settings as needed.
DOMAIN=example.com IMAGE_TAG="app-$release_tag" RETAIN_APP_IMAGES=3 \
  METRICS_BIND_ADDRESS=127.0.0.1 METRICS_PORT=9090 sh ./scripts/deploy.sh
```

`deploy.sh` does not read `.infinity-db-deploy.env`; pass the restored values explicitly as above.
`install-or-update.sh` selects the newest available release tag, so use it only when an upgrade is
intended, not when preserving the recorded version. For an upgrade from 0.8.0, follow the one-time
bootstrap in [Linux deployment](deployment.md).

The deployment guard validates the tracked databases and complete processed symbol publication and
proves that `infinity.db` and `symbol-publication.json` name the same Army source ZIP SHA-256 before
building/activating the image.

## Reproducible development/build migration

A development workstation needs additional ignored source/provenance state only when it must
rebuild data or continue symbol processing.

For an Army database rebuild, preserve the exact immutable Army snapshot and its generated snapshot
manifest:

```text
data/raw/JSON YYYYMMDD-HHMMSS.zip
data/manifests/snapshots/JSON YYYYMMDD-HHMMSS.json
```

For symbol-source rebuild/cache continuity, also preserve:

```text
data/raw/symbols/SYMBOLS YYYYMMDD-HHMMSS.zip
data/manifests/snapshots/SYMBOLS YYYYMMDD-HHMMSS.json
data/manifests/army-symbol-build.json
image_overrides/
```

`army-symbol-build.json` remains local terminal/intermediate processing provenance. It binds pinned
Army/SYMBOLS artifacts, processing reports/settings, cache identities, and publication state, but
it is no longer needed to deploy an already released checkout.

For an interrupted symbol build, preserve the manifest-bound derived state as well:

```text
data/work/symbols/
data/reports/symbols/
```

Later-stage resume validates that work and its SHA-bound reports instead of silently regenerating
it. `data/logs/symbols/` is diagnostic history and `data/backups/symbols/` is optional removed-symbol
history; preserve either only when that history matters.

The current `rules.db` is reproducible from tracked curated data under `data/curated/rules/`.
Local PDF/wiki research collections are not runtime build inputs.

## Processing environment for regenerated symbols

Cross-machine symbol regeneration can vary when external rendering/conversion tools or fonts differ.
When rebuilding rather than consuming a tracked publication, recreate the prior processing
environment as closely as practical, including:

- installed fonts used by font audit/text conversion;
- Inkscape version/backend;
- `resvg` version;
- SVGO version;
- Python and symbol-processing dependency versions.

Do not commit or redistribute external system fonts used only by symbol text conversion
merely to make a rebuild portable. This is separate from InfinityDB's intentionally bundled
browser-font publication under `src/infinity_db/web/static/fonts/`, whose WOFF2 files and OFL
notices are tracked and redistributable under their SIL Open Font License terms.

## State that does not need to move

For a normal released-server migration, none of these local development/history directories are
required:

```text
data/raw/
data/wiki/
data/pdf/
data/work/
data/reports/
data/logs/
data/backups/
image_overrides/
reports/
.venv/
```

They matter only when preserving a development/research/rebuild environment.

## Verification after migration

Confirm that the replacement host runs the recorded release and has clean tracked state:

```sh
git rev-parse HEAD
git describe --tags --exact-match
git status --short
docker compose ps
```

Verify application version/snapshot and the collector's retained periods after restoration, using
[deployment guidance](deployment.md#retained-metrics-history). Check the application and relevant
browser paths before retiring the old host. If migrating a development candidate instead of a
released server, use the isolated local-test deployment described there.

For development-side validation before publishing a release, run the normal project checks with
required tracked assets and the deployment verifier as documented in
[testing](testing.md) and [deployment](deployment.md).
