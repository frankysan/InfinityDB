# Linux deployment

**Project domain:** Deployment

For public internet serving, InfinityDB deploys an immutable Docker image
containing the application, processed graphical assets and the complete tracked
`army.db` / `rules_n5.db` / `its_17.db` / `its_18.db` set. Structured runtime facts are
embedded; no JSON publication or raw source archive is required at startup.
Rollback uses a matching retained image for the older release's data format.

Caddy listens on HTTP and proxies traffic to the application, which is not exposed
directly on the host. Put Caddy behind an external TLS reverse proxy for public HTTPS.

Corvus Belli has explicitly permitted InfinityDB to use and redistribute the graphical
assets used by this non-commercial community project. By project policy, the generated runtime
databases are likewise distributed only as part of the non-commercial InfinityDB
application/release and remain outside the MIT License. Raw Army/wiki/PDF/source-symbol archives
stay outside the public repository; the processed SVG publication and four runtime databases are
tracked release artifacts. See
[third-party notices](../THIRD_PARTY_NOTICES.md).

**Docker deployment** is intentionally **release-only**; the independently
supported direct-checkout runtime is described below. Database and symbol
generation happen in a development/release checkout. A tagged Docker server
checkout consumes the exact tracked databases and
symbols reviewed for that release. It verifies recorded build-input freshness
and published graphics before image creation, without acquiring raw data or
rebuilding the databases. Runtime validates the built set independently of those
source files.

For moving an installation to a new host, see the
[server migration guide](server-migration.md).

## Direct checkout hosting (without Docker)

This is the separate local/LAN or self-hosted checkout target, not the public
Docker release workflow. From the repository root, after acquiring a local
Army snapshot and installing the project:

```sh
infinity-db build --compact
infinity-db serve
```

The build validates and replaces the complete `data/generated/` set:
`army.db`, `rules_n5.db`, `its_17.db` and `its_18.db`.
Stop the service before rebuilding its selected directory. `serve --db-dir PATH`
selects another complete set; otherwise `INFINITY_DB_DB_DIR` precedes the default
`data/generated/` relative to the working directory. Invalid sets fail startup.

For a longer-lived checkout service, install the optional `server` dependencies,
set the service working directory and `INFINITY_DB_DB_DIR` to the absolute
complete-set directory, then start
`gunicorn --bind 127.0.0.1:8000 infinity_db.web.wsgi:app`.
WSGI requires the setting. The individual database variables are retired.
Local builds do not publish a Docker release.

## Prerequisites

Install Git, Python 3.11 or newer with `venv`/pip support, and Docker Engine with a Compose plugin
that supports `up --wait` on the Linux server. Host Python runs the installer and artifact verifier;
the application itself runs in the container. Configure the external
reverse proxy to terminate TLS for the public hostname and forward HTTP traffic to this
deployment's HTTP port (80 by default). Compose also publishes the separate metrics listener on
loopback port 9090 by default; it can bind to a specific trusted LAN interface. The application
container has no host-published port. Caddy does not obtain or manage TLS certificates.

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
data/generated/army.db
data/generated/rules_n5.db
data/generated/its_17.db
data/generated/its_18.db
data/manifests/symbol-publication.json
src/infinity_db/web/static/{armies,characteristics,orders,peripherals,units}/...
```

`deploy.sh` runs `tools/verify_deployment_assets.py` before Docker builds. This
validates the strict complete set, recorded source/build-input freshness, embedded
Weapon citations against maintained reviews, and the graphical publication's
paths, hashes and Army source identity. Raw Army/PDF inputs are not needed on the
server. The image copies the four databases directly into `/app/data/`; no
`data/runtime/` copy or candidate promotion is required.

The image uses `INFINITY_DB_DB_DIR=/app/data`. Missing, invalid or incompatible
databases fail before activation. `scripts/verify-container-image.sh --published-assets`
checks embedded provenance, static bytes, package contents, representative API
citations and production startup. Compose starts with `--no-build` after image
verification. The immutable container never regenerates databases.

For a production `app-v<version>` image, the deploy script requires HEAD at the
matching exact Git tag and a matching installed package version. It embeds
the release version independently of ignored/untracked server artifacts;
the image verifier rejects a mismatched tag, package or baked footer version.
Development/test image tags retain the `+dev` display behavior. After the
application is healthy, old image pruning is best-effort: image tags referenced
by any container (including stopped test containers) are retained, and
cleanup errors do not change the successful application deployment result.

For an isolated image build and all pinned semantic-baseline probes, run:

```sh
python -m tools.preview_runtime_image
# Or select an already-built complete alternate set:
python -m tools.preview_runtime_image --source-dir local/alternate-dbs
```

The preview creates a private build context, runs a disposable read-only container
without published ports and removes its owned container/image. It preserves the
selected files and requires an active Docker Linux engine. Deployment and release
remain separately authorized.

## Release-artifact generation

The tracked runtime databases are generated during development/release preparation, not on the
server. Raw archives and intermediate build products remain ignored. Rebuild the complete
Army/Rules/ITS set from the pinned Army snapshot and tracked curated inputs, run the normal
validation gates, then commit all three `data/generated/` databases with the code/data
changes that require them.

Historical `data/manifests/army-symbol-build.json` is not part of the deployment
contract and cannot resume the retired in-tree processor. The tracked
`symbol-publication.json` carries the compact Army archive name/SHA-256 needed by deployment
plus the published SVG hashes/mappings. Current symbol publication writes that provenance
automatically. A legacy publication without `sourceSnapshot.armyArtifact`
is not a valid release input: prepare and promote a verified external handoff
for the pinned Army archive rather than modifying the manifest in place.
Deployment validation compares its SHA-256 with `army.db`.

## Isolated local deployment test

Before every release merge, the
[release checklist](releasing.md#mandatory-pre-merge-release-sign-off)
requires a **running Docker test deployment**, independent of hosted image
smoke. Use a Docker Linux host with the synchronized candidate SHA and
tracked runtime files; a separate development/test host is preferable.
Run the isolated loopback-only deployment, then check public-page routing,
runtime identity, metrics and health through their correct listeners:

```sh
sh ./scripts/deploy-local-test.sh
.venv/bin/python -m tools.ci.verify_running_deployment
```

The probe defaults to `http://localhost:8080` for the Caddy public host
and `http://127.0.0.1:8081` for the metrics listener. Use
`--public-base` and `--metrics-base` for custom test ports. For production,
use the public HTTPS URL and configured metrics listener, plus
`--expected-version <version>` to reject an accidental `+dev` footer.

To verify production directly through Caddy when the external TLS proxy
rejects the probe, use its loopback HTTP listener and the configured
public hostname as an explicit Host header:

```sh
.venv/bin/python -m tools.ci.verify_running_deployment --public-base http://127.0.0.1 --public-host YOUR-HOST --metrics-base http://127.0.0.1:9090 --expected-version <version>
```

Adjust the listener addresses/ports to the deployment configuration.
`--public-host` applies to every public probe request, never to metrics.
This verifies the running Caddy/application path, not external TLS or
reverse-proxy availability; check public browser access separately.

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

The verifier requires `/app/data/` to contain exactly `army.db`, `rules_n5.db`, `its_17.db` and `its_18.db`, checks the
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
infinity-db database-health --db-dir data/generated
```

The directory check validates both databases, embedded source pairing and full
SQLite integrity. Raw build archives are outside the serving contract.

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

### Voluntary error reports

The shared form sends reports to a fixed maintainer email address using
an authenticated or otherwise authorized SMTP relay. Reporting is disabled
by default, without affecting reference browsing. Set these values in the
deployment checkout's private, Git-ignored `.env` file (mode 600):

```dotenv
INFINITYDB_FEEDBACK_SMTP_HOST=smtp.example.invalid
INFINITYDB_FEEDBACK_SMTP_PORT=587
INFINITYDB_FEEDBACK_SMTP_SECURITY=starttls
INFINITYDB_FEEDBACK_SMTP_FROM=sender@example.invalid
INFINITYDB_FEEDBACK_SMTP_TO=maintainer@example.invalid
INFINITYDB_FEEDBACK_SMTP_USERNAME=sender@example.invalid
INFINITYDB_FEEDBACK_SMTP_PASSWORD='replace-with-mail-app-password'
```

Use the relay's authorized sender address and the intended maintainer
recipient. For implicit TLS use `ssl` and port 465; the port defaults
to 587 for STARTTLS and 465 for SSL. Username and password may both be
omitted for a relay that authorizes the application without credentials.
Plaintext SMTP is not supported. The installer preserves the separate
`.env` file across updates; Compose passes the values only to the app.
Keep credentials private and do not include them in diagnostics or Git.

The app does not retain report bodies or retry failed deliveries. Review
email in the configured mailbox, retain it only as needed to resolve the
issue, and transfer only actionable non-personal findings to the normal
project issue/backlog workflow. SMTP acceptance is not a guarantee of
inbox delivery. An actual submission after configuring the relay is part of
operator acceptance. The isolated local-test deployment explicitly disables
mail delivery to avoid accidental real submissions.

The [architecture privacy contract](architecture.md#privacy-preserving-observability)
describes the submitted fields and abuse limits.

### Retained metrics history

Retained history does not make the web-facing application container writable. The implemented
topology uses a separate `metrics-history` operational service on the private Compose network.
The standalone collection/aggregation/reporting engine is implemented in `tools/operations/metrics_history.py`
and runs through the dedicated Compose service. The service scrapes
`http://app:8000/internal/metrics` directly, exposes no public/LAN port, runs with an immutable root
filesystem, and owns one dedicated writable SQLite
volume. It must not receive the Docker socket, host filesystem mounts, or writable mounts into `app`.
The existing loopback/trusted-LAN `/metrics` endpoint remains the interactive/current-state surface.

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

The reviewed vocabulary includes the fixed `/api/variant-usage` route label;
its catalog, variant and Army query values are never retained as labels.

The engine can also be exercised manually from a checkout against the trusted LAN metrics listener:

```powershell
python tools/operations/metrics_history.py --database local/reports/metrics-history.db collect --url http://127.0.0.1:9090/metrics
python tools/operations/metrics_history.py --database local/reports/metrics-history.db status
```

Retained history is queryable without exposing another HTTP endpoint. `periods` lists the exact
week/version/snapshot identities present in the SQLite store. `report` defaults to the latest exact
period; `--week`, `--version`, and `--snapshot` may be combined, and broader selectors intentionally
aggregate all matching retained periods. `compare` defaults to the latest two exact periods or accepts
independent `--from-*` and `--to-*` selectors. For example:

```powershell
python tools/operations/metrics_history.py --database local/reports/metrics-history.db periods
python tools/operations/metrics_history.py --database local/reports/metrics-history.db report
python tools/operations/metrics_history.py --database local/reports/metrics-history.db report --week 2026-10-05
python tools/operations/metrics_history.py --database local/reports/metrics-history.db compare --from-version 0.9.1 --to-version 0.10.0
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
versioned separately from the application. `tools/operations/metrics_history.py` owns an explicit
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
python -m tools.operations.report_metrics
```

The report shows application/snapshot identity, metrics-generation start/latest-request timestamps
and observed span, active and completed requests, status-class counts, average and approximate p95
latency, average response size, and the busiest normalized routes. It consumes only the bounded
aggregate Prometheus surface and therefore cannot reconstruct visitor histories. Use
`python -m tools.operations.report_metrics --raw` when the raw Prometheus exposition is needed for another local
monitoring tool.

Raw request logging is not enabled in normal operation. If it is temporarily required for a
concrete incident, minimize and sanitize the fields, restrict access, and define short
retention before enabling it. Error logs and host/container health data remain appropriate
when they do not embed request-identifying values.

For routine retained diagnostics, do not archive raw Docker logs. Instead collect a bounded,
sanitized warning/error report from the existing Caddy/Gunicorn streams. For each
example below, replace `RUN_ID` with a **new** UTC run timestamp plus short
checkout SHA (and keep the same run ID for paired evidence). All four operational
report commands reject an existing output file *before* reading logs, gathering
resources, sending load-test traffic or starting alert sampling, and use
exclusive creation to guard against later collisions. Old explicit paths still
work if unoccupied; do not reuse a previous report filename.

```sh
.venv/bin/python -m tools.operations.deployment_diagnostics --output local/operations/deployment/diagnostics/RUN_ID/diagnostics.json
```

The extractor ignores routine informational lines, discards Caddy structured request fields,
redacts request targets/URLs/IP addresses and other identity-like key/value fields, redacts Python
exception messages, groups repeated sanitized events by fingerprint, and caps retained groups. It
does not enable Caddy or Gunicorn access logging. To align diagnostics exactly with a capacity/resource
run, reuse the resource report's capture window:

```sh
.venv/bin/python -m tools.operations.deployment_diagnostics --resource-report local/performance/http-capacity/RUN_ID/resources.json --output local/operations/deployment/diagnostics/RUN_ID/capacity-diagnostics.json
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
python -m tools.performance.capacity_test http://localhost:8080 --output local/performance/http-capacity/RUN_ID/capacity.json
```

The defaults run a 60-second steady phase at concurrency 8 followed by a 10-second burst at
concurrency 32. Override those values explicitly when reproducing a recorded baseline. The report
contains the target version/snapshot identity, aggregate and per-route p50/p95/p99 latency,
request/error rate, status classes, and response sizes. The generated search term is synthetic and
redacted from retained report paths. A non-zero load-phase error count makes the command fail.

For the current Unit Explorer, use the separate `--scenario unit-explorer`
workload. It discovers positive-count Skill and Equipment identities and
exercises 15 routes/query shapes: page and filter initialization, scoped
prospective counts, pagination, sorting, search, individual and combined
filters (profile/loadout/unit), Extended pages and optional availability.
It reports per-case timings and redacts the synthetic Unit search value.
The general scenario remains the default; do not compare aggregate throughput
across the two workloads. This is a warmed, repeatedly sampled HTTP workload,
not a measurement of cold worker initialization or browser rendering.

For first-access diagnostics, restart the **isolated** application workers
before each invocation, wait for health only, and send no other application
traffic. Select one fixed API case rather than discovering identities:

```bash
.venv/bin/python -m tools.performance.capacity_test http://localhost:8080 --first-access-case unit-detail --steady-seconds 10 --burst-seconds 5 --output local/performance/http-capacity/RUN_ID/unit-detail.json
```

The initial batch sends one request per steady-concurrency slot (default 8)
before any discovery or warm-up; the subsequent steady and burst phases use
the same route after normal warm-up. A failed initial batch is reported
without proceeding to the warmed phases. Use `--help` for the fixed Explorer,
Unit, catalog/detail and Search cases. Repeat on independently restarted
workers for each case and retain separate receipts. This measures deployment
first-access latency, not per-worker cache misses or cold filesystem caches:
HTTP dispatch does not establish worker identity, and simultaneous requests
can share initialization work. Small initial batches have limited percentile
resolution. Compare repeated fresh starts with warmed per-route p50/p95 and
record the resource configuration. Do not run this diagnostic against live
production traffic or infer browser rendering time from the HTTP samples.

On the Linux development checkout, use the isolated test stack and collect a
fresh resource and capacity report with the normal 2x4 worker configuration:

```bash
sh scripts/deploy-local-test.sh 8080
```

```bash
COMPOSE_PROJECT_NAME=infinitydb-test .venv/bin/python -m tools.operations.deployment_resources --output local/performance/http-capacity/RUN_ID/resources.json -- .venv/bin/python -m tools.performance.capacity_test http://localhost:8080 --scenario unit-explorer --output local/performance/http-capacity/RUN_ID/capacity.json
```

For an app-only capacity check without a Compose deployment, the disposable
runtime image preview also supports `--capacity-output`:

```bash
.venv/bin/python -m tools.preview_runtime_image --tag infinity-db:preview-capacity --capacity-output local/performance/http-capacity/RUN_ID/capacity.json
```

It builds the normal Dockerfile, starts a read-only preview with an ephemeral
IPv4 loopback port, waits for health, runs the same Unit Explorer workload,
retains the JSON receipt and removes the owned container/image. This mode
does not run semantic parity checks or Caddy. Select another workload with
`--capacity-case general` or a fixed first-access case, and on Linux add
`--capacity-resources` with a separate new JSON path to sample the host and
the owned app container during the same run. Each invocation starts a new
container, without application traffic before the selected workload. The
default 60/10-second phases are configurable with `--steady-seconds` and
`--burst-seconds`. App-only evidence excludes Caddy; use the full isolated
stack for deployment-level resource evidence.

The same preview tool can run the complete disposable Compose stack on Linux
without disturbing an existing deployment. For example:

```bash
.venv/bin/python -m tools.preview_runtime_image --compose-capacity --capacity-case general --capacity-output local/performance/http-capacity/RUN_ID/general.json --capacity-resources local/performance/http-capacity/RUN_ID/general-resources.json
```

Compose mode uses a unique project, ephemeral IPv4 loopback ports, the tracked
Caddy configuration, and separate temporary metrics-history storage. It
requires both receipt paths and collects resources from all three services.
Each invocation starts fresh and removes its own containers, volumes and
image tags afterward. Use `--capacity-case unit-explorer` for the separate
Explorer workload; fixed first-access cases are also supported.

The HTTP report is only one half of a capacity result. On the Linux deployment host, wrap the
capacity command with the resource sampler so both ignored JSON reports cover the same interval:

```bash
COMPOSE_PROJECT_NAME=infinitydb-test .venv/bin/python -m tools.operations.deployment_resources --output local/performance/http-capacity/RUN_ID/resources.json -- .venv/bin/python -m tools.performance.capacity_test http://localhost:8080 --output local/performance/http-capacity/RUN_ID/capacity.json
```

The resource report records host CPU, memory/swap, filesystem space/inodes, aggregate network rates,
backing-device I/O when the Linux mount exposes a corresponding `/proc/diskstats` device, and Docker
CPU/memory/network/block-I/O data for the `app` and `caddy` services. It also records container
restart-count changes plus Docker `restart`/`oom` events during the capture. For capacity evidence,
each container summary also records only the bounded runtime configuration needed to interpret the
result: an explicit Docker CPU limit in cores, an explicit Docker memory limit in bytes, and, when the
container command is Gunicorn, its configured worker/thread counts. A missing CPU or memory limit is
reported as `null` rather than inferred from host capacity. Some LXC/storage layouts do not expose a
directly attributable host block device; in that case host disk-I/O rates are `null` while Docker
block-I/O deltas remain available.

The retained report deliberately omits hostnames, IP addresses, request URLs, arbitrary Docker event
attributes, arbitrary container environment/command values, and the wrapped command line. Record any
resource boundary outside Docker (for example an LXC/VM allocation) with the baseline notes. Do not
compare 2-worker and 4-worker results unless the relevant allocation is recorded and controlled; the
recorded matched comparison requires both app-container reports to show the same
4-core/4-GiB limit.

For the controlled worker-count comparison, keep resource allocation and workload identical. The
retained 2x4 baseline was uncapped at the Docker layer, so it remains useful reference evidence
but is not by itself a matched control for a capped 4x4 run. Two capacity-only Compose overrides keep
the experimental variables separate:

- `compose.capacity-4cpu-4g.yaml` applies only the 4-CPU / 4-GiB app-container limit;
- `compose.capacity-4x4.yaml` changes only Gunicorn from the image default 2x4 to 4x4.

First deploy and measure the matched **2x4 control** under the resource cap:

```bash
COMPOSE_FILE=compose.yaml:compose.capacity-4cpu-4g.yaml sh scripts/deploy-local-test.sh 8080
```

```bash
COMPOSE_PROJECT_NAME=infinitydb-test COMPOSE_FILE=compose.yaml:compose.capacity-4cpu-4g.yaml .venv/bin/python -m tools.operations.deployment_resources --output local/performance/http-capacity/RUN_ID-2x4/resources.json -- .venv/bin/python -m tools.performance.capacity_test http://localhost:8080 --output local/performance/http-capacity/RUN_ID-2x4/capacity.json
```

Then deploy and measure the **4x4 experiment** with the same resource cap:

```bash
COMPOSE_FILE=compose.yaml:compose.capacity-4cpu-4g.yaml:compose.capacity-4x4.yaml sh scripts/deploy-local-test.sh 8080
```

```bash
COMPOSE_PROJECT_NAME=infinitydb-test COMPOSE_FILE=compose.yaml:compose.capacity-4cpu-4g.yaml:compose.capacity-4x4.yaml .venv/bin/python -m tools.operations.deployment_resources --output local/performance/http-capacity/RUN_ID-4x4/resources.json -- .venv/bin/python -m tools.performance.capacity_test http://localhost:8080 --output local/performance/http-capacity/RUN_ID-4x4/capacity.json
```

Both valid reports must record `cpuLimitCores: 4.0` and `memoryLimitBytes: 4294967296`. The control
must additionally report `workers: 2`, `threads: 4`; the experiment must report `workers: 4`,
`threads: 4`. If any value differs, discard that run as non-comparable. Compare the matched pair first;
use the original uncapped 2x4 result as supporting context rather than attributing resource-boundary
differences to worker count.

After the experiment, restore the ordinary isolated 2x4 stack simply by redeploying without
`COMPOSE_FILE`:

```bash
sh scripts/deploy-local-test.sh 8080
```

#### Full-stack v1.3.0 development capacity (2026-11-27)

The Linux-dev disposable Compose preview at `e8f7035e` used the tracked
Caddy, Gunicorn (2 workers × 4 threads) and metrics-history services. The
snapshot was `3457c90e15f84b17ce2cf44e8402726f8fa1fb71ab0b39a507024c21c3efb37b`;
the development package reported 1.2.2. The host exposed 16 logical CPUs and
approximately 31.3 GiB RAM, without explicit Docker CPU or memory limits.
The two workloads ran sequentially in fresh isolated stacks with discovery
and warmup before the 60-second concurrency-8 steady phase and 10-second
concurrency-32 burst.

| Workload | Steady req/s | Steady p50/p95/p99 (ms) | Burst req/s | Burst p50/p95/p99 (ms) |
| --- | ---: | ---: | ---: | ---: |
| General (18 cases) | 495.7 | 10.5/48.3/74.6 | 487.1 | 59.8/114.9/139.1 |
| Unit Explorer (15 cases) | 103.4 | 75.3/178.7/257.4 | 106.2 | 255.3/558.4/620.1 |

Both runs had zero HTTP errors, restarts or OOM events, exited 0, and removed
their temporary containers, volumes, networks and image tags. The sampled
resource results were:

| Workload | App peak MiB | Caddy peak MiB | Metrics peak MiB | Sum of peaks MiB | Host CPU avg/max | Host memory peak |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| General | 205.4 | 25.4 | 21.5 | 252.3 | 28.9%/34.2% | 6.7% |
| Unit Explorer | 332.3 | 22.6 | 21.1 | 375.9 | 15.7%/19.1% | 7.0% |

The sum of individual sampled container peaks is an upper bound on their
simultaneous sampled total, not a simultaneous peak measurement. App memory
is container usage across workers, not summed process RSS. The app averaged
305.3% CPU during general traffic and 200.0% during Explorer traffic.

General steady API p50/p95 (ms): Unit detail 24.5/40.6, Skill detail
35.2/56.0, Equipment detail 49.6/84.7, Weapon detail 35.5/58.2, search
9.9/18.4 and Unit list 10.0/15.4. These use discovered identities rather
than the fixed high-usage catalog detail cases. Explorer steady p50/p95:
initial 114.8/155.1, Extended 152.9/283.6, Extended next 137.8/250.9,
profile/loadout/Unit matching 62.3/92.6, 75.0/103.9 and 76.4/105.2.
Explorer burst p95 was 619.0 ms for Extended and 573.4 ms for Extended next.

HTTP and resource receipts are retained under
`local/performance/http-capacity/20261127-e8f7035e/` on Linux-dev.
The earlier [fixed-route first-access measurements](testing.md#pre-fork-runtime-index-initialization-pilot)
were app-only, while these full-stack workloads measure warmed representative
HTTP traffic. They are complementary, not a paired Caddy overhead experiment.
The older baseline differs in revision, snapshot and/or resource boundary.
These results support retaining the default 2x4 configuration and closing
the development capacity investigation. They do not establish a production
SLO, measure browser rendering or validate production traffic; revisit
first-visit, exact-variant or asynchronous costs when new evidence warrants it.

#### Unit Explorer app-only 2x4 measurement (2026-11-25)

The disposable Docker preview on the Linux development worker ran the
15-case Unit Explorer capacity scenario at commit `a1ad31c4` using the
normal Dockerfile (Gunicorn 2x4, Python 3.11). The preview did not supply a
development display-version override, so the API reported 1.2.1; the Git
commit identifies the tested development code. Snapshot revision:
`55375a32f200506ec03943c627f1d4face5b0a4fc17b4bd8ebb368bcd9c8ff13`.

- Steady, concurrency 8 / 60 seconds: 112.2 requests/s, p50/p95/p99
  23.2/193.9/289.0 ms, 6,745 requests, zero errors.
- Burst, concurrency 32 / 10 seconds: 109.8 requests/s, p50/p95/p99
  192.2/730.1/841.3 ms, 1,166 requests, zero errors.
- Steady per-case p95: initial results 179.2 ms, filter initialization
  96.8 ms, profile/loadout/unit matching 155.6/171.1/176.8 ms,
  Extended first/next page 222.8/225.6 ms.
- Burst Extended first/next page p95: 737.1/837.2 ms.

The preview passed health, completed both phases and removed its disposable
container and image. The JSON receipt is retained on the Linux worker under
`local/performance/http-capacity/20261125-a1ad31c4/capacity.json`.
This was a warmed repeated-query workload directly against Gunicorn; Caddy,
matched production resource boundaries, concurrent host/container resource
sampling and cold-worker latency were not measured. The similar throughput
and higher burst latency suggest saturation under this synthetic workload,
not a measured CPU or worker-count bottleneck. Do not compare the aggregate
rates with the older general capacity scenario or infer a production SLO.

#### Recorded 2x4 baseline (2026-10-06)

The first retained baseline used the isolated `infinitydb-test` deployment with Gunicorn configured
for 2 workers x 4 threads. The enclosing Proxmox LXC was limited to 8 CPUs and 8 GiB RAM. The app
container itself had no explicit Docker CPU or memory limit, so the LXC allocation is the effective
outer resource boundary for this result. The target was InfinityDB 0.9.1 with snapshot revision
`49a316155f34d386a5acda02c7bce1615976a46c7955fccff23961a0f9077769`.

Using the default capacity scenario after warm-up:

- steady phase, concurrency 8 for 60 seconds: 271.1 requests/s, 0 errors, p50 8.5 ms,
  p95 113.6 ms, p99 160.5 ms;
- burst phase, concurrency 32 for 10 seconds: 264.8 requests/s, 0 errors, p50 107.9 ms,
  p95 219.8 ms, p99 262.3 ms.

During the wrapped run, app CPU averaged 265.9% and peaked at 338.3%; host CPU averaged 41.6% and
peaked at 45.6% on 8 logical CPUs. App memory peaked at about 149 MB, host memory peaked at about
8.2% used, and no restart/OOM event occurred. Disk activity was negligible: the app container
reported no block-I/O delta, while host disk I/O averaged about 2.4 kB/s read and 11.6 kB/s write.

The result is intentionally treated as a baseline, not a production SLO. Increasing concurrency from
8 to 32 did not increase throughput and instead raised median and tail latency substantially, while
host CPU, memory, and disk remained well below their resource ceilings. For this synthetic scenario,
that is evidence that the 2x4 Gunicorn configuration is application-concurrency-bound before the
8-CPU/8-GiB LXC is host-resource-bound.

#### Matched 2x4 versus 4x4 result (2026-10-06)

A follow-up matched experiment applied the same explicit 4-vCPU/4-GiB app-container boundary to both
worker configurations. The control report confirmed Gunicorn 2x4 with `cpuLimitCores: 4.0` and
`memoryLimitBytes: 4294967296`; the experiment confirmed Gunicorn 4x4 under the identical limits.
Both runs completed with zero HTTP errors and no container restart/OOM events. The capped 2x4
control was also consistent with the earlier uncapped reference: steady p95 stayed effectively the
same (114.2 ms versus 113.6 ms) and steady throughput was within 7.2%, so the 4-CPU boundary was
not itself the dominant 2x4 bottleneck.

Under the 60-second concurrency-8 steady phase:

- 2x4: 251.6 requests/s; p50/p95/p99 8.5/114.2/164.9 ms;
- 4x4: 432.1 requests/s; p50/p95/p99 5.8/87.9/141.5 ms.

That is a 71.8% throughput increase. Mean latency fell 41.8%, p50 32.3%, p95 23.0%, and p99 14.2%.
The 4x4 app averaged 368.5% CPU versus 277.3% for 2x4; host CPU averaged 57.2% versus 40.2%. App
memory remained small in both cases, peaking around 238 MB for 4x4 and 212 MB for 2x4, while disk
activity remained negligible relative to the workload.

Under the concurrency-32 burst, 4x4 delivered 366.7 requests/s versus 260.5 requests/s for 2x4
(+40.8%). Mean and median latency improved by about 29.1% and 37.6%, but p95/p99 were 241.4/304.3 ms
versus 226.9/268.5 ms for 2x4. The result therefore validates 4x4 as a substantially higher-capacity
configuration under the controlled resource boundary, but also shows that heavier overload still
produces tail-latency pressure rather than unlimited scaling.

Production remains 2x4 by default. Use the matched result as a bounded scale step rather than an
unconditional worker-count increase. Start a 4x4 scale review when representative production traffic
sustains aggregate p95 latency of at least 120 ms for about 15 minutes while request rate is at least
200 requests/s, or when overload-attributable 5xx exceeds 1% for at least 5 minutes. Before changing
workers, collect fresh resource evidence and require host/LXC CPU below 70% average, memory below 80%,
and no storage/OOM/restart pressure; otherwise address the actual resource bottleneck instead. Re-run
the representative capacity scenario against the candidate configuration before production rollout.
If the same trigger is later reached on 4x4, prefer multiple immutable app replicas behind Caddy over
continuing to grow Gunicorn worker count in one container.

When the Proxmox/LXC CPU allocation changes, restart Docker inside the LXC before relying on Docker CPU
limits or cpusets. Docker can retain the CPU topology observed when the daemon started even though
existing unconstrained containers see newly added CPUs. Verify with `docker info --format 'Docker CPUs: {{.NCPU}}'`
and a small cpuset probe before running controlled capacity experiments.

### Operational alert evaluation

After collecting a fresh resource report, evaluate the deployment alert policy against that evidence
and a bounded aggregate-metrics/health sampling interval:

```bash
.venv/bin/python -m tools.operations.deployment_alerts --resource-report local/performance/http-capacity/RUN_ID/resources.json --output local/operations/deployment/alerts/RUN_ID/alerts.json
```

When evaluating a matched 2x4 or 4x4 capacity experiment, select its
corresponding `RUN_ID-2x4` or `RUN_ID-4x4` resource report instead.
Keep the alert receipt separate from the input resource file. Alert
statuses remain OK=0, warning=1, critical=2, unknown=3;
report-file errors return **3 (unknown)**, never a synthetic critical
status. Resource/diagnostic report failures return 2; capacity-report
errors return 2, distinct from ordinary load-phase failure (1).
Do not interpret an output error as a completed diagnostic.

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
production/capacity evidence. The scale-review trigger defined in the matched worker-count
comparison above uses measured latency, error, and resource behavior rather than copying these
alert thresholds.

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
