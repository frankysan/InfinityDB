# Linux deployment

InfinityDB is deployed as an immutable Docker image: it contains the web
application, tracked static UI assets, and validated `infinity.db` and `rules.db`
snapshots. Caddy listens on HTTP and proxies traffic to the application, which is not exposed
directly on the host. Put Caddy behind an external TLS reverse proxy for public
HTTPS.

Corvus Belli graphical assets are not bundled with the InfinityDB source or a
redistributable release by default. A local installation may acquire and process
those assets separately for local browser use, but that does not grant
redistribution rights. Review [third-party notices](../THIRD_PARTY_NOTICES.md)
before distributing any image or database that contains external data or assets.

This guide documents the **current deployment workflow**. Army/wiki/symbol
acquisition and symbol processing/publication are explicit workflows separate
from deployment; `install-or-update.sh` does not perform network acquisition or
rebuild the local symbol publication. For moving an existing installation to a
new host, see the [server migration guide](server-migration.md).

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
retention count, builds both runtime databases, and deploys them. It can save
those two settings to the ignored `.infinity-db-deploy.env` file for subsequent runs.
It stops before changing tags when tracked local edits are present, but leaves
untracked raw data and the optional config file intact.

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

For a local smoke test, use `DOMAIN=localhost` and open
`http://localhost`. On a public domain, replace `infinity.example.com` with
the real hostname before running Compose and configure the external TLS proxy
to forward that host to Caddy.


## Local graphical symbols

The deployment scripts do not acquire Corvus Belli graphical assets. When a local
installation should serve symbols, prepare the complete published asset set
separately before building the Docker image. A complete local publication consists
of the ignored `armies/`, `characteristics/`, `orders/`, and `units/` trees plus
`src/infinity_db/web/static/symbol-inventory.json`; the tracked browser maps must
come from the same repository revision/publication. On a validation checkout with
the development dependencies installed, `tools/run_checks.py --assets required`
validates that publication before deployment.

For an exact server replacement, copy the already-published local asset set rather
than relying on cross-machine SVG regeneration. See
[server migration](server-migration.md) for the full transfer checklist and the
current reproducibility limits. Local publication does not change the third-party
redistribution boundary described above.

## Deployment smoke validation

The `Deployment smoke test` GitHub Actions workflow exercises the distributable
container path without committing or downloading real Army source data. It
builds `infinity.db` from the synthetic source under
`tests/fixtures/deployment-smoke/`, builds the tracked curated `rules.db`, then
builds the Docker image and runs `scripts/verify-container-image.sh`.

The verifier requires `/app/data/` to contain exactly `infinity.db` and
`rules.db`, validates both database formats, checks the configured runtime paths
and non-root image user, and starts Gunicorn with a read-only root filesystem,
`/tmp` tmpfs, and `no-new-privileges`. It waits for the image health check and
then exercises Army, rules-enriched Skill, and version API endpoints. In
`--redistributable` mode it also rejects the ignored `armies/`,
`characteristics/`, `orders/`, and `units/` Corvus Belli graphical-asset trees if
they appear in either the copied
source tree or the installed Python package. This keeps CI/release validation
separate from local asset publication.

The same image verifier can be run manually after preparing the two generated
databases and building an image:

```sh
docker build -t infinity-db:smoke .
sh ./scripts/verify-container-image.sh infinity-db:smoke --redistributable
```

## Operations

```sh
docker compose ps
docker compose logs -f app caddy
docker compose pull caddy
docker compose up -d --build
```

To update Army data, download or place the new raw snapshot and its required
`metadata.json` in `data/raw/`, then run `sh ./scripts/install-or-update.sh`.
The same deployment run rebuilds `rules.db` from the tracked collections under
`data/curated/rules/`. Do not edit either SQLite file inside a running container.

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
