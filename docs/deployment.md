# Linux deployment

InfinityDB is deployed as an immutable Docker image: it contains the web
application, static assets, and one validated `infinity.db` snapshot. Caddy
terminates HTTPS and proxies traffic to the application, which is not exposed
directly on the host.

## Prerequisites

Install Docker Engine with the Compose plugin on the Linux server. Point both
the domain's `A` (and, if used, `AAAA`) record at that server and allow inbound
TCP ports 80 and 443. Caddy uses port 80 for ACME validation and manages TLS
certificates automatically.

## Deploy or update

From a checked-out release on the server, prepare the database from a source
snapshot. The build is validated and replaces the local database only after a
successful import.

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/infinity-db build --compact

DOMAIN=infinity.example.com IMAGE_TAG=2026-09-10 docker compose up -d --build
```

The image build deliberately requires `data/generated/infinity.db`. This makes
an unbuilt or invalid data snapshot fail the deployment rather than serving an
unexpected database. The database is baked into the image, so rolling back is
simply deploying the earlier image tag.

For a local smoke test, use `DOMAIN=localhost`; Caddy will serve a local HTTPS
certificate. On a public domain, replace `infinity.example.com` with the real
hostname before running Compose.

## Operations

```sh
docker compose ps
docker compose logs -f app caddy
docker compose pull caddy
docker compose up -d --build
```

To update data, download or place the new raw snapshot in `data/raw/`, repeat
`infinity-db build --compact`, and run `docker compose up -d --build` with a new
`IMAGE_TAG`. Do not edit the SQLite file inside a running container.

The application container runs as an unprivileged user with a read-only
filesystem. Caddy's named volumes are intentionally retained: they hold its
TLS certificates and configuration state. Back them up if the server itself is
not otherwise backed up.
