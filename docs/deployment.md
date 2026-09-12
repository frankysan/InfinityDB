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

From a checked-out release on the server, prepare the database from a source
snapshot. `metadata.json` is required: include it in the ZIP, place it beside
the source snapshot, or pass `--metadata PATH` to the build command. The build
is validated and replaces the local database only after a successful import.

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/infinity-db build --compact

DOMAIN=infinity.example.com IMAGE_TAG=0.3.0 docker compose up -d --build
```

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
`metadata.json` in `data/raw/`, repeat `infinity-db build --compact`, and run
`docker compose up -d --build` with a new `IMAGE_TAG`. Do not edit the SQLite
file inside a running container.

The application container runs as an unprivileged user with a read-only
filesystem. Caddy's named volumes are intentionally retained for its runtime
configuration state. Back them up if that state is needed when rebuilding the
server; TLS certificates belong to the external reverse proxy.
