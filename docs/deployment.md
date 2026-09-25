# Linux deployment

InfinityDB is deployed as an immutable Docker image: it contains the web
application, tracked static UI assets, and validated `infinity.db` and `rules.db`
snapshots. Caddy listens on HTTP and proxies traffic to the application, which is not exposed
directly on the host. Put Caddy behind an external TLS reverse proxy for public
HTTPS.

Corvus Belli has explicitly permitted InfinityDB to use and redistribute the
graphical assets used by this non-commercial community project, including
processed SVGs in public repositories and deployment/build packages. Those assets
remain Corvus Belli property and stay outside InfinityDB's MIT License. Raw Army,
wiki, PDF, and source-symbol archives remain separate local/provenance inputs by
project policy. Review [third-party notices](../THIRD_PARTY_NOTICES.md) for the
full permission and attribution boundary.

This guide documents the **current deployment workflows**. Army/wiki/symbol
acquisition and symbol processing/publication are explicit workflows separate
from deployment. Production has two intentionally separate data modes:

- `install-or-update.sh` rebuilds runtime databases from raw source already present
  on the server, then deploys them with the tracked symbol publication from the
  checked-out release plus the matching local terminal symbol manifest.
- `deploy-transferred.sh` consumes commit-matched runtime databases and terminal
  symbol provenance transferred from a development checkout; the processed symbol
  publication itself comes from the matching Git revision.

Do not mix those modes in one update: rebuilding after an artifact transfer can replace
the transferred database with one from a different Army snapshot, which the provenance
guard correctly rejects. For moving an existing installation to a new host, see the
[server migration guide](server-migration.md).

## Prerequisites

Install Docker Engine with the Compose plugin on the Linux server. Configure
the external reverse proxy to terminate TLS for the public hostname and forward
HTTP traffic to this deployment's port 80. The Compose configuration publishes
only TCP port 80; Caddy does not obtain or manage TLS certificates.

## Deploy or update

From a clone on the server, place the current source snapshot and its required
`metadata.json` in `data/raw/` (or ensure they are otherwise available to the
build). `metadata.json` is required: include it in the ZIP, place it beside the
source snapshot, or pass `--metadata PATH` to the build command. The build is
validated and replaces the local database only after a successful import.

```sh
sh ./scripts/install-or-update.sh
```

The interactive script fetches tags from `origin`, checks out the newest
version tag in detached-HEAD mode, asks for the public domain and image
retention count, builds both runtime databases, validates the tracked symbol
publication against terminal version-8 `data/manifests/army-symbol-build.json`,
and deploys only after the exact built image passes production startup and
installed-symbol validation. It can save the domain and retention settings to
the ignored `.infinity-db-deploy.env` file for subsequent runs. It stops before
changing tags when tracked local edits are present, but leaves untracked raw data,
generated manifests, generated databases, and the optional config file intact.

The image build deliberately requires both `data/generated/infinity.db` and
`data/generated/rules.db`. This makes an incomplete runtime-data build fail
before deployment. The Docker image explicitly configures both paths; an
explicitly configured invalid or missing rules database causes the WSGI workers
to fail at startup instead of silently serving the reduced no-rules feature set.
Both databases are baked into the image, so rolling back is simply deploying the
earlier image tag.

The application factory still treats an adjacent `rules.db` as optional when no
rules path is explicitly configured. This preserves local/development workflows;
the stricter requirement is part of the Docker production contract.

For an isolated local-access-only deployment test on the same server, use:

```sh
sh ./scripts/deploy-local-test.sh
```

This creates a separate `infinitydb-test` Compose project, binds Caddy only to
`127.0.0.1:8080`, uses the current matched runtime/symbol artifacts without
rebuilding them, and disables production image pruning. Pass another port as the
first argument when needed. From another machine, use an SSH tunnel such as
`ssh -L 8080:127.0.0.1:8080 <server>` and browse to `http://localhost:8080`.
Stop only this isolated stack with:

```sh
sh ./scripts/stop-local-test.sh
```

The stop helper always targets the `infinitydb-test` Compose project and leaves its
named volumes intact for the next test run. It does not target the production Compose
project or run the production image-pruning policy.

## Published graphical symbols

The deployment scripts do not acquire or regenerate Corvus Belli graphical assets.
The processed `armies/`, `characteristics/`, `orders/`, and `units/` SVG trees,
`src/infinity_db/web/static/symbol-inventory.json`, `army-symbols.js`, and
`unit-symbol-map.js` are tracked release content and therefore come from the exact
Git revision being deployed. Production additionally requires the local terminal
version-8 `data/manifests/army-symbol-build.json` that promoted that publication;
the manifest's SHA-bound inventory and browser maps must match the tracked files.

`deploy.sh` runs `tools/verify_deployment_assets.py` before Docker is allowed to
build. That guard verifies the v8 manifest bindings and the complete inventory by
path/hash rather than accepting merely non-empty directories. It then builds the
application image, runs `scripts/verify-container-image.sh --published-assets` to
revalidate the installed Python package and representative production symbol routes,
and only then starts Compose with `--no-build`. The image that passed validation is
therefore the image that is deployed. A missing manifest, partial publication,
stale browser map, package-data omission, or symbol hash mismatch fails before the
running service is replaced.

The runtime Army database must also carry the SHA-256 of the exact Army ZIP
snapshot used by the terminal symbol manifest. The deployment guard,
artifact-transfer helper, and installed-image check compare this generated
provenance directly; raw source archives are not needed on the server. A missing
or different identity fails closed. Rebuild the database from the symbol
publication's Army ZIP, or republish symbols from the database snapshot's source
before retrying.

On a validation checkout with the development dependencies installed,
`tools/run_checks.py --assets required` remains useful for full project testing;
the deployment guard is narrower and specifically binds deployment to one promoted
publication.

For routine deployment from a development checkout, `tools/send_deployment_artifacts.py`
transfers only the ignored runtime databases and terminal symbol manifest. The symbol
publication, inventory, and browser maps are already supplied by the exact matching Git
commit. The helper validates the local databases, database-to-symbol snapshot provenance,
and manifest-bound tracked publication first, requires the remote checkout to be at the
exact same commit with no tracked edits, stages the incoming files, and uses one SSH
session so password authentication prompts only once. Run a dry-run first to inspect
the exact transfer set:

```powershell
.\.venv\Scripts\python.exe tools\send_deployment_artifacts.py `
  root@docker-infinitydb --remote-root /srv/infinitydb --dry-run

.\.venv\Scripts\python.exe tools\send_deployment_artifacts.py `
  root@docker-infinitydb --remote-root /srv/infinitydb
```

SSH public-key authentication can be selected with `--identity-file` to make the same
transfer non-interactive. The helper deliberately excludes raw snapshots, work trees,
logs, reports, backups, caches, and other ignored development state. After transfer,
run the dedicated no-rebuild wrapper on the server:

```sh
sh ./scripts/deploy-transferred.sh
```

The wrapper installs the current checkout into the server virtual environment, derives
a versioned `app-v*` image tag, reads `DOMAIN` and `RETAIN_APP_IMAGES` from the
environment or `.infinity-db-deploy.env`, and delegates to the same guarded image
validation/deployment path. It deliberately does not call `infinity-db build` or
`build-rules`. `install-or-update.sh` remains the separate server-rebuild workflow and
requires its own raw Army snapshot.

For an exact server replacement, check out the same Git revision so the processed
publication is restored byte-for-byte, then transfer only the generated runtime and
local provenance state documented in [server migration](server-migration.md). Do not
regenerate SVGs merely to reproduce an existing release. The processed publication
may be redistributed with InfinityDB under Corvus Belli's permission; raw acquisition
archives remain separate from that distributable publication.

## Deployment smoke validation

The configured `Deployment smoke test` GitHub Actions workflow exercises the
distributable container path without committing or downloading real Army source data. It
builds `infinity.db` from the synthetic source under
`tests/fixtures/deployment-smoke/`, builds the tracked curated `rules.db`, then
builds an isolated temporary Docker context and runs `scripts/verify-container-image.sh`.
It never writes fixture data to `data/generated/`. A successful
hosted run is release evidence and remains a tracked release-validation task.

The verifier requires `/app/data/` to contain exactly `infinity.db` and
`rules.db`, validates both database formats, checks the configured runtime paths
and non-root image user, and starts Gunicorn with a read-only root filesystem,
`/tmp` tmpfs, and `no-new-privileges`. It waits for the image health check and
then exercises Army, rules-enriched Skill, and version API endpoints.
`--packaged-assets` requires the installed package to contain exactly the tracked
`symbol-inventory.json` publication, re-hashes every SVG, verifies the published byte
total, and requests one served symbol from each namespace. Production
`--published-assets` performs the same package checks and additionally binds the
runtime database to the ignored terminal symbol-build manifest, preserving the
snapshot-provenance deployment guard.

The same image verifier can be run manually after preparing the two generated
databases and building an image:

```sh
docker build -t infinity-db:smoke .
sh ./scripts/verify-container-image.sh infinity-db:smoke --packaged-assets
```

## Operations

```sh
docker compose ps
docker compose logs -f app caddy
docker compose pull caddy
# Production from server-side raw data:
sh ./scripts/install-or-update.sh
# Production from a commit-matched transferred artifact set:
sh ./scripts/deploy-transferred.sh
# Isolated loopback-only test stack (default port 8080):
sh ./scripts/deploy-local-test.sh
# Stop only the isolated test stack:
sh ./scripts/stop-local-test.sh
```

To update Army data, download or place the new raw snapshot and its required
`metadata.json` in `data/raw/`, then run `sh ./scripts/install-or-update.sh`.
The same deployment run rebuilds `rules.db` from the tracked collections under
`data/curated/rules/`. Do not edit either SQLite file inside a running container.

### Privacy and observability

InfinityDB's accepted monitoring direction is aggregate-only observability: normalized
route/request counts, status classes, latency distributions, response sizes, active
requests, version identity, and host/container resource use. Production monitoring must
not retain IP addresses, user agents/fingerprints, referrers, cookies/session or preference
values, query strings/search terms, persistent visitor identifiers, or per-user request
histories. See `docs/architecture.md` for the canonical policy.

The current Docker image still enables Gunicorn's standard access log on stdout. That
predates the aggregate-only policy and must not be treated as the intended monitoring
implementation. Until it is replaced or sanitized, operators should avoid exporting or
retaining that raw request stream beyond the minimum needed for immediate operations.
Error logs and host/container health data remain appropriate when they do not embed
request-identifying values.

`deploy.sh` retains the current build and the two newest rollback builds by
default. After Compose has successfully started and health-checked the new
application container, it removes only older `infinity-db:app-*` tags. It does
not prune dangling images or touch Caddy, Portainer, named volumes, or images
from other repositories. Set `RETAIN_APP_IMAGES=2` to keep the current build
plus one rollback build; use `RETAIN_APP_IMAGES=1` to keep only the current
build.

To apply the retention policy to images already on the server without
deploying, run `sh ./scripts/prune-app-images.sh` (or pass the desired count as
its first argument).

The application container runs as an unprivileged user with a read-only
filesystem. Caddy's named volumes are intentionally retained for its runtime
configuration state. Back them up if that state is needed when rebuilding the
server; TLS certificates belong to the external reverse proxy.
