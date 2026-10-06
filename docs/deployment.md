# Linux deployment

**Project domain:** Deployment

InfinityDB is deployed as an immutable Docker image containing the web application,
tracked processed graphical assets, and the release-matched `infinity.db` and `rules.db`
snapshots. Caddy listens on HTTP and proxies traffic to the application, which is not
exposed directly on the host. Put Caddy behind an external TLS reverse proxy for public
HTTPS.

Corvus Belli has explicitly permitted InfinityDB to use and redistribute the graphical
assets used by this non-commercial community project. By project policy, the generated runtime
databases are likewise distributed only as part of the non-commercial InfinityDB
application/release and remain outside the MIT License. Raw Army/wiki/PDF/source-symbol archives
stay outside the public repository; the processed SVG publication and two runtime databases are
tracked release artifacts. See
[third-party notices](../THIRD_PARTY_NOTICES.md).

Deployment is intentionally **release-only**. Database and symbol generation happen in a
development/release checkout. A tagged server checkout consumes the exact artifacts already
reviewed and committed for that release; it does not acquire raw data or rebuild databases.
For moving an installation to a new host, see the
[server migration guide](server-migration.md).

## Prerequisites

Install Docker Engine with the Compose plugin on the Linux server. Configure the external
reverse proxy to terminate TLS for the public hostname and forward HTTP traffic to this
deployment's port 80. The Compose configuration publishes only TCP port 80; Caddy does not
obtain or manage TLS certificates.

## Deploy or update

### One-time 0.8.0 to 0.8.1 transition

The 0.8.0 installer predates tracked runtime databases and continues executing its old logic
after it checks out a newer tag. Do **not** start the 0.8.0-to-0.8.1 upgrade by invoking that
old checkout's `scripts/install-or-update.sh` directly: it can rebuild `infinity.db` from local
server source material and replace the release-matched database before the new deployment guard
runs.

For a server still starting from a 0.8.0 checkout, bootstrap the installer from the 0.8.1 tag instead:

```sh
tmp="$(mktemp)" && git fetch origin --tags --prune && git show v0.8.1:scripts/install-or-update.sh > "$tmp" && sh "$tmp"; status=$?; rm -f "$tmp"; [ "$status" -eq 0 ]
```

The 0.8.1 installer removes the legacy untracked database copies only when the target release
owns tracked files at those paths, then checks out and deploys the exact release artifacts.

### Normal updates from 0.8.1 onward

From the server checkout:

```sh
sh ./scripts/install-or-update.sh
```

The interactive installer fetches release tags from `origin`, loads the installer shipped by the
newest release tag before any prompts or checkout-side effects, then checks out that tag in
detached-HEAD mode. This handoff prevents obsolete updater behavior from continuing after a
release checkout. The release installer asks for the public domain, image-retention policy, and
optional LAN metrics binding, installs the application into the local virtual environment, then
deploys the tracked release artifacts without rebuilding them. It can save deployment settings
in the ignored `.infinity-db-deploy.env` file. The script refuses to change tags while tracked
local edits are present.

Every deploy requires these release-controlled files to be present in the checkout:

```text
data/generated/infinity.db
data/generated/rules.db
data/manifests/symbol-publication.json
src/infinity_db/web/static/{armies,characteristics,orders,units}/...
```

`deploy.sh` runs `tools/verify_deployment_assets.py` before Docker is allowed to build. The
guard validates both SQLite databases, verifies the complete symbol publication by path and
SHA-256, and compares `infinity.db`'s embedded `snapshotArchiveSha256` with
`symbol-publication.json`'s `sourceSnapshot.armyArtifact.sha256`. This binds the runtime Army
data and graphical publication to the same exact source ZIP without requiring that raw archive
or the terminal `army-symbol-build.json` on the server.

The Docker image explicitly configures both runtime database paths. Missing, invalid, or
incompatible tracked databases fail before activation. After building the image,
`scripts/verify-container-image.sh --published-assets` revalidates the installed publication,
the embedded database/publication provenance, package contents, representative symbol routes,
and production startup. Compose is started with `--no-build` only after that exact image has
passed verification.

## Release-artifact generation

The tracked runtime databases are generated during development/release preparation, not on the
server. Raw archives and intermediate build products remain ignored. Rebuild the application
database from the pinned Army snapshot and the rules database from tracked curated rules, run
the normal validation gates, then commit the resulting `data/generated/infinity.db` and
`data/generated/rules.db` with the code/data changes that require them.

The terminal `data/manifests/army-symbol-build.json` remains ignored local build provenance. It
is useful for symbol processing/resume but is not part of the deployment contract. The tracked
`symbol-publication.json` carries only the compact Army archive name/SHA-256 needed by deployment
plus the published SVG hashes/mappings. Current symbol publication writes that provenance
automatically. Only when preparing a legacy publication created before this provenance
field was tracked, run the one-time migration in the development checkout:

```powershell
python tools/migrate_symbol_publication_provenance.py
```

That command copies the Army archive identity from the local terminal build manifest into the
tracked publication manifest and refreshes the ignored local binding. It does not rebuild or
modify any SVG.

## Isolated local deployment test

For an isolated local-access-only deployment test on the same server, use:

```sh
sh ./scripts/deploy-local-test.sh
```

This creates a separate `infinitydb-test` Compose project, binds Caddy only to
`127.0.0.1:8080`, deploys the current tracked runtime/symbol artifacts, and disables production
image pruning. Pass another port as the first argument when needed. From another machine, use an
SSH tunnel such as `ssh -L 8080:127.0.0.1:8080 <server>` and browse to
`http://localhost:8080`. Stop only this isolated stack with:

```sh
sh ./scripts/stop-local-test.sh
```

The stop helper always targets the `infinitydb-test` Compose project and leaves its named
volumes intact for the next test run. The local deployment runs the same `metrics-history`
collector/update lifecycle as production, so its history database is automatically isolated in the
`infinitydb-test` Compose project's `metrics_history` volume. Normal stop/start and update tests
preserve that synthetic history. For a deliberate clean-slate run, use:

```sh
sh ./scripts/stop-local-test.sh --purge
```

The purge path still targets only `COMPOSE_PROJECT_NAME=infinitydb-test`; it removes that project's
named volumes (including metrics history and local Caddy state) without targeting production.

## Published graphical symbols

The deployment scripts do not acquire or regenerate Corvus Belli graphical assets. The
processed `armies/`, `characteristics/`, `orders/`, and `units/` SVG trees, plus the
`peripherals/<main-army>/` tree when present, are tracked release content together with
`data/manifests/symbol-publication.json`, supplied by the exact Git revision being deployed. Browser static code consumes paths derived from that canonical manifest;
no generated lookup metadata or terminal build manifest is required at runtime.

`tools/run_checks.py --assets required` remains the full project-level asset gate in a
development checkout. `tools/verify_deployment_assets.py` is narrower and release-oriented: it
checks the committed runtime databases and publication that the Docker image will actually use.

## Deployment smoke validation

The configured `Deployment smoke test` GitHub Actions workflow builds the Docker image directly
from the tracked runtime databases and processed publication in the checkout. It then runs
`scripts/verify-container-image.sh --published-assets`, so a stale or missing committed database,
publication/database snapshot mismatch, packaging omission, corrupted SQLite file, symbol hash
mismatch, or startup failure is caught against the same artifact model used in production.

The verifier requires `/app/data/` to contain exactly `infinity.db` and `rules.db`, checks the
configured runtime paths and non-root image user, and starts Gunicorn with a read-only root
filesystem, `/tmp` tmpfs, and `no-new-privileges`. It waits for the image health check and then
exercises Army, rules-enriched Skill, and version API endpoints.

The same verifier can be run manually after building an image:

```sh
docker build -t infinity-db:smoke .
sh ./scripts/verify-container-image.sh infinity-db:smoke --published-assets
```

## Operations

```sh
docker compose ps
docker compose logs -f app caddy
docker compose pull caddy
# Fetch/check out the latest release and deploy its tracked runtime artifacts:
sh ./scripts/install-or-update.sh
# Isolated loopback-only test stack (default port 8080):
sh ./scripts/deploy-local-test.sh
# Stop only the isolated test stack:
sh ./scripts/stop-local-test.sh
```

To update Army data, perform acquisition/build/publication in the development environment,
validate and commit the updated runtime databases/publication, then release a new tag. Production
servers update by checking out that tag; they do not need the underlying raw archive. Do not edit
either SQLite file inside a running container. Before publication, the development pair can be
checked explicitly with:

```powershell
infinity-db database-health data/generated/infinity.db --require-raw
```

For a tracked/deployed application database where the development-only raw sibling is intentionally
absent, omit `--require-raw`. The command reports actual/expected schema and compatibility revisions
and fails if the application database is not valid for the running InfinityDB code.

### Privacy and observability

`docs/architecture.md` owns the canonical aggregate-only privacy/observability policy. The
deployment layer enforces that policy by disabling Gunicorn's routine access log, retaining stderr
error logging for diagnostics, and using the preloaded application's fixed-cardinality shared
request registry for bounded route/status/latency/response-size/activity/build metrics.

The aggregate registry is exposed as Prometheus text at `/internal/metrics` on the app
container's port 8000. `/internal/health` provides the container liveness/readiness probe and
is excluded from usage metrics. The public Caddy site still returns 404 for `/internal/*`. A
second Caddy listener exposes only `/metrics` and `/health`; Compose publishes that listener on
`METRICS_BIND_ADDRESS` / `METRICS_PORT`, defaulting to `127.0.0.1:9090`. The application
container itself remains unpublished. Deployment tooling rejects wildcard metrics binds such as
`0.0.0.0` or `::`, so LAN access must name a specific trusted server interface address. The
metrics are process-lifetime operational state and intentionally reset when the application
container restarts.

### Retained metrics history

Retained history must not make the web-facing application container writable. The accepted target
topology remains a separate `metrics-history` operational service on the private Compose network.
The standalone collection/aggregation/reporting engine is implemented in `tools/metrics_history.py`
and runs through the dedicated Compose service. The service scrapes
`http://app:8000/internal/metrics` directly, exposes no public/LAN port, runs with an immutable root
filesystem, and owns one dedicated writable SQLite
volume. It must not receive the Docker socket, host filesystem mounts, or writable mounts into `app`.
The existing LAN-only `/metrics` endpoint remains the interactive/current-state scrape surface.

The collector treats each application metrics generation explicitly. Live metrics expose the
generation-start and latest completed-request timestamps needed to distinguish restarts even when
version and snapshot revision are unchanged. The SQLite store keeps only one previous scrape state
needed to compute deltas, then folds deltas into weekly summaries keyed by ISO week, InfinityDB
version, and snapshot revision. The first scrape of a new generation is safely treated as a delta
from zero; later scrapes subtract only the matching generation state. An unexplained counter decrease
inside one generation is not retained as a delta: rolling state is reset so history cannot inflate.
Multiple process generations may therefore contribute to the same weekly/version/snapshot summary
without confusing counter resets with request activity.

The retention contract is intentionally bounded: continuous collection defaults to every 5 minutes,
keeps the current week plus 52 completed weeks, prunes after successful collection, and enforces a
64-MiB SQLite safety ceiling by deleting the oldest completed weeks first. Collector status exposes
earliest/latest retained observations, retained-week count, database size, and whether the size
ceiling is still exceeded because only the current week remains. No raw request URL, search/query
value, IP address, user agent, cookie/preference value, visitor ID, or per-user history may enter the
history database. The collector also fails closed on an unreviewed route label rather than silently
persisting a new high-cardinality dimension. Latency and response-size histogram boundaries are also
allowlisted so a future metrics-layout change cannot silently mix incompatible bucket schemas in one
historical store.

The engine can also be exercised manually from a checkout against the trusted LAN metrics listener:

```powershell
python tools/metrics_history.py --database reports/metrics-history.db collect --url http://127.0.0.1:9090/metrics
python tools/metrics_history.py --database reports/metrics-history.db status
```

Retained history is queryable without exposing another HTTP endpoint. `periods` lists the exact
week/version/snapshot identities present in the SQLite store. `report` defaults to the latest exact
period; `--week`, `--version`, and `--snapshot` may be combined, and broader selectors intentionally
aggregate all matching retained periods. `compare` defaults to the latest two exact periods or accepts
independent `--from-*` and `--to-*` selectors. For example:

```powershell
python tools/metrics_history.py --database reports/metrics-history.db periods
python tools/metrics_history.py --database reports/metrics-history.db report
python tools/metrics_history.py --database reports/metrics-history.db report --week 2026-10-05
python tools/metrics_history.py --database reports/metrics-history.db compare --from-version 0.9.1 --to-version 0.10.0
```

Human-readable reports include request/status counts, 4xx+5xx and 5xx rates, normalized-route
activity, average latency/response size, cumulative histograms, and bounded p50/p95/p99 estimates.
Percentiles are histogram upper-bound estimates, not reconstructed raw request timings; if a
percentile falls in `+Inf`, the report states that it is greater than the largest finite bucket.
Append `--json` to `periods`, `report`, or `compare` for machine-readable aggregate output. Reporting
reads only the retained bounded dimensions already present in the history store and does not add
request-level persistence.

For the deployed persistent history volume, run the reporting commands inside the collector service
so they use its configured `/var/lib/infinitydb-metrics/history.db` directly:

```sh
docker compose exec metrics-history python /app/metrics_history.py periods
docker compose exec metrics-history python /app/metrics_history.py report
docker compose exec metrics-history python /app/metrics_history.py compare
```

Use `COMPOSE_PROJECT_NAME=infinitydb-test` with the same commands when inspecting the isolated local
test history.

Deployment keeps application availability and history persistence deliberately separate. Before
changing the running stack, `deploy.sh` builds and verifies both the new application image and the
separate `metrics-history` image. It then stops only an existing continuous collector so it cannot
race the transition samples. If an application is already running, the new collector image runs once
against the old `app:8000/internal/metrics` endpoint and writes a closing sample into the persistent
history volume. The app/Caddy replacement and `--wait` health gate then remain the availability-
critical deployment step. After the new application passes health checks, the collector image runs
once again for the opening sample, and only then is the continuous collector service started/updated.
The closing one-shot may use a transition-only legacy generation fallback, allowing the first
collector-enabled release to retain aggregate counters from an older deployment that predates the
live generation-timestamp gauges. Continuous collection never uses that fallback.

Closing/opening scrape failures or failure to start the continuous collector are operational warnings,
not reasons to roll back or block an otherwise healthy application/security update. A collector image
that cannot be built or verified fails before application replacement begins. The historical
`RETAIN_APP_IMAGES` deployment setting is retained for configuration compatibility but now applies
to both `infinity-db:app-*` and `infinity-db-metrics-history:app-*`, so repeated releases do not
silently accumulate collector images. Periodic collection handles normal operation; after an
unexpected restart, generation detection prevents reset counters from being interpreted as deltas.

The persistent history database is independent forward-moving operational state. Its on-disk format is
versioned separately from the application. `tools/metrics_history.py` owns an explicit
one-version-at-a-time forward-migration registry: every persisted format increment must add the
previous -> next migration before `FORMAT_VERSION` is raised. Each migration and its `format_version`
update run in one SQLite transaction. A failed migration therefore leaves the previous committed format
intact and can be retried;
a non-empty unversioned store is refused rather than guessed. A collector that encounters a history
format newer than it supports refuses to open it without downgrading, deleting, or rewriting retained
history.

An application rollback does not imply a history-database downgrade. Before rolling back to a release
that predates the `metrics-history` service, stop the currently deployed collector from the current
checkout with `docker compose stop metrics-history`, then perform the application rollback without
`docker compose down -v` or any explicit removal of the `metrics_history` volume. The stopped collector
container may be removed as an orphan if needed; the named volume must remain. If a rollback target has
an older collector that cannot read a newer history format, leave that collector stopped/failed and keep
the volume for a later compatible release rather than attempting a downgrade. Collector health/status
is separate from app/Caddy health and must not participate in the deployment success gate.

The isolated local test deployment uses the same transition sequence under
`COMPOSE_PROJECT_NAME=infinitydb-test`, giving it a separate history volume automatically. Normal local
shutdown preserves that volume so restart/update continuity can be tested; `stop-local-test.sh --purge`
removes only the isolated test project's volumes for a deliberate clean slate. `/metrics` itself
remains volatile process-lifetime state; retained history lives only in the collector volume.

### LAN metrics access and workstation report

For direct access from a trusted workstation on the local network, bind the metrics listener to
the **server's LAN address**, not the workstation address. `install-or-update.sh` prompts for the
setting and stores it in the ignored `.infinity-db-deploy.env`. Subsequent tagged-release deployments reuse the same values. For example:

```text
METRICS_BIND_ADDRESS=192.168.1.20
METRICS_PORT=9090
```

Do not use a wildcard address. If the server firewall filters LAN traffic, allow the selected TCP
port only from the trusted local network/workstation. The public InfinityDB host remains separate
and continues to reject `/internal/*`.

From a Windows development checkout, set the metrics URL once for the PowerShell session and use
the dependency-free report tool:

```powershell
$env:INFINITYDB_METRICS_URL = "http://192.168.1.20:9090/metrics"
python tools/report_metrics.py
```

The report shows application/snapshot identity, metrics-generation start/latest-request timestamps
and observed span, active and completed requests, status-class counts, average and approximate p95
latency, average response size, and the busiest normalized routes. It consumes only the bounded
aggregate Prometheus surface and therefore cannot reconstruct visitor histories. Use
`python tools/report_metrics.py --raw` when the raw Prometheus exposition is needed for another local
monitoring tool.

Raw request logging is not enabled in normal operation. If it is temporarily required for a
concrete incident, minimize and sanitize the fields, restrict access, and define short
retention before enabling it. Error logs and host/container health data remain appropriate
when they do not embed request-identifying values.

For routine retained diagnostics, do not archive raw Docker logs. Instead collect a bounded,
sanitized warning/error report from the existing Caddy/Gunicorn streams:

```sh
.venv/bin/python tools/deployment_diagnostics.py --output reports/deployment-diagnostics.json
```

The extractor ignores routine informational lines, discards Caddy structured request fields,
redacts request targets/URLs/IP addresses and other identity-like key/value fields, redacts Python
exception messages, groups repeated sanitized events by fingerprint, and caps retained groups. It
does not enable Caddy or Gunicorn access logging. To align diagnostics exactly with a capacity/resource
run, reuse the resource report's capture window:

```sh
.venv/bin/python tools/deployment_diagnostics.py --resource-report reports/capacity-resources.json --output reports/capacity-diagnostics.json
```

Treat the generated JSON as short-lived operational evidence. If a concrete incident requires the
raw log stream, inspect it interactively with restricted access rather than adding it to retained
capacity/release evidence.

### Repeatable HTTP capacity scenario

Use the dependency-free capacity runner against the HTTP entry point being evaluated, preferably an
isolated deployment first. The scenario discovers current public identities from the target and
exercises Unit browsing, global search, Unit/catalog details, and matching JSON APIs after a warm-up;
it does not benchmark only the health endpoint. For example, after starting the loopback test stack:

```powershell
python tools\capacity_test.py http://127.0.0.1:8080 --output reports\capacity-local.json
```

The defaults run a 60-second steady phase at concurrency 8 followed by a 10-second burst at
concurrency 32. Override those values explicitly when reproducing a recorded baseline. The report
contains the target version/snapshot identity, aggregate and per-route p50/p95/p99 latency,
request/error rate, status classes, and response sizes. The generated search term is synthetic and
redacted from retained report paths. A non-zero load-phase error count makes the command fail.

The HTTP report is only one half of a capacity result. On the Linux deployment host, wrap the
capacity command with the resource sampler so both ignored JSON reports cover the same interval:

```bash
.venv/bin/python tools/deployment_resources.py --output reports/capacity-resources.json -- .venv/bin/python tools/capacity_test.py http://127.0.0.1:8080 --output reports/capacity.json
```

The resource report records host CPU, memory/swap, filesystem space/inodes, aggregate network rates,
backing-device I/O when the Linux mount exposes a corresponding `/proc/diskstats` device, and Docker
CPU/memory/network/block-I/O data for the `app` and `caddy` services. It also records container
restart-count changes plus Docker `restart`/`oom` events during the capture. Some LXC/storage layouts
do not expose a directly attributable host block device; in that case host disk-I/O rates are `null`
while Docker block-I/O deltas remain available.

The retained report deliberately omits hostnames, IP addresses, request URLs, arbitrary Docker event
attributes, and the wrapped command line. Capture the exact Gunicorn/container allocation separately
with the baseline notes. Do not compare 2-worker and 4-worker results unless the resource allocation
is recorded and controlled.

### Operational alert evaluation

After collecting a fresh resource report, evaluate the deployment alert policy against that evidence
and a bounded aggregate-metrics/health sampling interval:

```bash
.venv/bin/python tools/deployment_alerts.py --resource-report reports/capacity-resources.json --output reports/deployment-alerts.json
```

By default the evaluator samples metrics for 60 seconds and checks `/health` at both ends of that
interval. `INFINITYDB_METRICS_URL` can select the trusted metrics listener; unless
`INFINITYDB_HEALTH_URL` or `--health-url` is set explicitly, the health URL is derived as `/health`
beside the metrics URL. Retained JSON does not include either URL.

The initial operational thresholds are deliberately explicit and conservative rather than claimed
as final SLOs:

- sustained host CPU: warning at 85% average, critical at 95% average, requiring at least a
  60-second resource window;
- host/container memory: warning at 85% maximum used, critical at 95%; any observed container OOM
  kill is immediately critical, while a restart/restarting container is warning-level evidence;
- filesystem free space and free inodes: warning at 15% remaining, critical at 5%;
- 5xx responses: warning requires at least 5 errors and 1% of requests during the sampled counter
  delta; critical requires at least 10 errors and 5%;
- any failed health probe is critical.

All thresholds can be overridden explicitly on the command line. A stale resource report, a resource
window too short to establish sustained CPU behavior, unavailable metrics, or metrics counters that
reset during sampling produces `unknown` evidence rather than a false OK. Exit codes are `0` OK,
`1` warning, `2` critical, and `3` unknown, making the command suitable for cron/systemd or an
external notification service without coupling InfinityDB to one alert-delivery provider.

These defaults are an initial operational safety net. Tune them only after retaining representative
2x4 production/capacity evidence; the separate scale-trigger task should be based on measured latency,
error, and resource behavior rather than simply copying these alert thresholds.

`deploy.sh` retains the current build and the two newest rollback builds by
default. After the application health gate and metrics-history transition/start
steps, it removes only older `infinity-db:app-*` and
`infinity-db-metrics-history:app-*` tags. It does not prune dangling images or
touch Caddy, Portainer, named volumes, or images from other repositories. The
historical `RETAIN_APP_IMAGES` setting controls both InfinityDB image
repositories: set it to `2` to keep the current build plus one rollback build,
or `1` to keep only the current build.

To apply the retention policy to images already on the server without
deploying, run `sh ./scripts/prune-app-images.sh` (or pass the desired count as
its first argument).

The application container runs as an unprivileged user with a read-only
filesystem. Caddy's named volumes are intentionally retained for its runtime
configuration state. Back them up if that state is needed when rebuilding the
server; TLS certificates belong to the external reverse proxy.
