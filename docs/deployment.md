# Linux deployment

InfinityDB is deployed as an immutable Docker image: it contains the web
application, static assets, and one validated `infinity.db` snapshot. Caddy
listens on HTTP and proxies traffic to the application, which is not exposed
directly on the host. Put Caddy behind an external TLS reverse proxy for public
HTTPS.

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
retention count, builds the database, and deploys it. It can save those two
settings to the ignored `.infinity-db-deploy.env` file for subsequent runs.
It stops before changing tags when tracked local edits are present, but leaves
untracked raw data and the optional config file intact.

The image build deliberately requires `data/generated/infinity.db`. This makes
an unbuilt or invalid data snapshot fail the deployment rather than serving an
unexpected database. The database is baked into the image, so rolling back is
simply deploying the earlier image tag.

For a local smoke test, use `DOMAIN=localhost` and open
`http://localhost`. On a public domain, replace `infinity.example.com` with
the real hostname before running Compose and configure the external TLS proxy
to forward that host to Caddy.

## Operations

```sh
docker compose ps
docker compose logs -f app caddy
docker compose pull caddy
docker compose up -d --build
```

To update data, download or place the new raw snapshot and its required
`metadata.json` in `data/raw/`, then run `sh ./scripts/install-or-update.sh`.
Do not edit the SQLite file inside a running container.

`deploy.sh` retains the current build and the two newest rollback builds by
default. After Compose has successfully started and health-checked the new application container,
it removes only older `infinity-db:app-*` tags. It does not prune dangling
images or touch Caddy, Portainer, named volumes, or images from other
repositories. Set `RETAIN_APP_IMAGES=2` to keep the current build plus one
rollback build; use `RETAIN_APP_IMAGES=1` to keep only the current build.

To apply the retention policy to images already on the server without
deploying, run `sh ./scripts/prune-app-images.sh` (or pass the desired count as
its first argument).

The application container runs as an unprivileged user with a read-only
filesystem. Caddy's named volumes are intentionally retained for its runtime
configuration state. Back them up if that state is needed when rebuilding the
server; TLS certificates belong to the external reverse proxy.
