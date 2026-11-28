# Performance and test capacity

**Project domains:** Project infrastructure, Web backend, Web frontend, Deployment

Use [development checks](testing.md) for correctness and local validation;
the [architecture](architecture.md#design-direction-build-time-materialization)
owns accepted runtime design, and [deployment](deployment.md#repeatable-http-capacity-scenario)
owns full-stack capacity and operational decisions. This guide owns
repeatable benchmark methods and the bounded evidence behind current choices.
Do not treat short local or fixed-route samples as production guarantees.

## Benchmark tooling

Compare the same pinned commit/inputs, database identity, host, toolchain,
worker/browser configuration and workload. Record wall time, relevant
percentiles, success/failure/skip counts, throughput and resource usage as
appropriate. Alternate repeated A/B runs on an idle host when making a
capacity decision. Keep raw logs and reports under ignored `local/`.

```powershell
.\.venv\Scripts\python.exe -m tools.performance.benchmark_runtime --help
.\.venv\Scripts\python.exe -m tools.performance.compare_runtime_benchmarks --help
.\.venv\Scripts\python.exe -m tools.performance.benchmark_test_workers --help
.\.venv\Scripts\python.exe -m tools.performance.benchmark_test_workers --workers 0 4 --repeat 2 --report local/performance/test-workers/RUN_ID/worker-comparison.json
```

Use the actual selected runtime set. The runtime benchmark distinguishes
cold repository initialization, warm requests, profiling and real-browser
journeys; do not add browser launch or fixture wait to request latency.
For Explorer browser performance, with Chrome installed:

```powershell
.\.venv\Scripts\python.exe -m tools.performance.benchmark_runtime data/generated/army.db --browser --cold-iterations 3
```

Use the current `tools/performance/benchmark_*.py` modules for a measured
specific projection/build phase. Use fresh ignored paths for reports;
the worker benchmark checks its selected output before starting expensive
runs and preserves earlier receipts even on failure. Use
[deployment's HTTP workload](deployment.md#repeatable-http-capacity-scenario)
rather than duplicating production capacity instructions here.

## Bounded live-search prefix benchmark

The published index matches normalized substrings, ranks all matches, and
applies the requested limit at the API boundary. To compare that path with
SQL-side limiting using the same Unicode ranking and stable tie order:

```powershell
.\.venv\Scripts\python.exe -m tools.performance.benchmark_search_index --prefixes --iterations 100
```

On Windows at `334a5793` (2026-11-28), the seven sampled two-character
queries matched 64–399 entries. Current index medians were 1.93–3.77 ms;
bounded WSGI API medians were 2.06–3.92 ms. SQL-side top-eight selection
saved at most 0.31 ms for these queries and slightly increased narrow-query
costs. The single-character stress query `a` matched 1,148 entries with a
7.60 ms API median; navigation suggestions require two characters and use
a 180 ms debounce. All 1,100 paired candidate and API comparisons matched
the existing ranked results. Retain the existing ranking and API slicing:
the observed absolute savings do not justify another ranking path or a
publication change. This sequential local benchmark is not a capacity test.

## Chromium concurrency under pytest-xdist

Default Windows capacity remains two Chromium slots. On the dedicated
Linux worker use the validated eight-worker, four-slot, four-lane
Scenario FAQ split profile. Enable, inspect or disable the ignored
host-local profile explicitly on Linux:

```sh
.venv/bin/python -m tools.performance.browser_test_host_profile enable
.venv/bin/python -m tools.performance.browser_test_host_profile status
.venv/bin/python -m tools.performance.browser_test_host_profile disable
```

The profile is applied to the ordinary runner test stage only when no
scheduling/capacity override was explicitly supplied. It does not alter
Windows, direct pytest, clean CI or isolated preflight defaults.
For a broad explicit Linux run:

```sh
.venv/bin/python tools/run_checks.py --stage test --assets required --test-workers 8 --test-dist browserlanes --browser-slot-count 4 --browser-lane-count 4 --split-scenario-faq --report
```

`browserlanes` maps maintained browser groups onto xdist loadgroup.
The runner supports 2/3/4 slots and lanes; non-default lane selection
requires browserlanes. Scenario FAQ splitting requires four lanes and
parallel workers. `--reuse-browser` is opt-in and requires four slots
and lanes. Inspect actual one-worker-per-lane assignments rather than
assuming a grouping marker proves correct scheduling. Use the declared
pytest/xdist dependency constraints; the known pytest 9.2/xdist 3.8
loadgroup incompatibility is guarded by the startup profiler.

## Controlled Chromium concurrency and browser-reuse benchmark

For a controlled same-host comparison, hold all non-capacity inputs fixed
and run sequentially with `--browser-metrics`. For example:

```powershell
.\.venv\Scripts\python.exe tools/run_checks.py --stage test --test-section browser --test-workers 8 --test-dist browserlanes --browser-slot-count 2 --browser-lane-count 4 --split-scenario-faq --browser-metrics
.\.venv\Scripts\python.exe tools/run_checks.py --stage test --test-section browser --test-workers 8 --test-dist browserlanes --browser-slot-count 4 --browser-lane-count 4 --split-scenario-faq --browser-metrics
```

Compare unchanged selected tests, asset state, expected skips and lifecycle
isolation; repeat in alternating order with CPU/RAM observations.
Retain host-specific settings if instability or material resource regression
remains. A Windows four-slot test that times out is not an accepted speedup.

Pytest's native `setup` duration includes time blocked acquiring a Chromium
slot. This is **waiting**, not active fixture initialization; the two numbers
must not be added. The `tools.testing.pytest_startup_profile` plugin
records Chromium-slot acquisition waits during setup and transfers their
durations through pytest's `user_properties` to the xdist controller. For
significant waits (at least 50 ms), the final console report displays:

- **Measured resource waiting**: time blocked before acquiring a Chromium
  slot, summed across worker processes (not wall-clock elapsed time).
- **Remaining setup**: the original pytest setup duration minus the measured
  wait. This is *not* guaranteed active CPU work: other waits remain
  uninstrumented.
- **Original pytest setup**: unchanged, for comparison with historical results.

The displayed largest-wait examples are individual test setup events; a
module-scoped fixture's slot wait is charged to the first test executing that
fixture on each worker, not distributed across all cases in the module.
Tests blocked in a slot admission timeout also report their measured waiting.

The runner prints the ignored `local/benchmarks/chromium-*/` metrics
directory. Slot metrics describe completed admission/hold records and
monotonic timestamps within one host/run, not a complete process timeline.
Analyze them with:

```powershell
.\.venv\Scripts\python.exe -m tools.performance.analyze_chromium_timeline local/benchmarks/chromium-RUN --slots 4
.\.venv\Scripts\python.exe -m tools.performance.sample_test_host_resources --help
.\.venv\Scripts\python.exe -m tools.performance.analyze_test_host_resources --help
```

The timeline analyzer refuses old duration-only records. Align native CPU/RAM
samples to the test window; host-wide usage does not attribute CPU to a
specific test. Failure-only API/DOM diagnostics on Glossary and Spec-Ops
help investigate timeouts without increasing production waits.

**Decision evidence:** at `5ac29416` on 2026-11-03, the same 616-case
browser selection passed on Windows and Linux with both two and four slots.
Linux improved from 636.13 s to 396.22 s and repeated at 395.29 s.
Windows improved from 481.83 s to 402.56 s, but its reverse-order four-slot
run failed the Spec-Ops visibility assertion. Linux four slots and Windows
two slots were retained. The enabled Linux profile subsequently passed
5,001 tests with 29 skips at `47122aa5`, all four lanes correctly owned.
See the [controlled comparisons and instrumentation](https://github.com/frankysan/InfinityDB/blob/4774abde079a0e91ea87c9ee417c4ca1e2429403/docs/testing.md#controlled-chromium-concurrency-and-browser-reuse-benchmark)
for complete historical trials. Remaining test-performance research is
tracked in [TODO](TODO.md#performance-storage-and-build-tooling).

## Runtime materialization and first access — November 2026

The earlier [materialization measurements](https://github.com/frankysan/InfinityDB/blob/4774abde079a0e91ea87c9ee417c4ca1e2429403/docs/testing.md#unit-explorer-filter-performance--2026-11-25)
and [cross-platform baseline](https://github.com/frankysan/InfinityDB/blob/4774abde079a0e91ea87c9ee417c4ca1e2429403/docs/testing.md#cross-platform-materialization-baseline--2026-11-26)
cover General profiles, composed Rules, search, catalogs, filter inputs,
Specialist candidates and reference projections. These incremental
development measurements are preserved for comparisons with their exact
original revisions. The following experiments underpin the current
architecture's catalog and first-access decisions.

## Docker first-access and catalog detail baseline — 2026-11-27

Linux-dev at `94e56857`, snapshot
`e8060a35f1664ddb6b46475ab69ea42aceeb1b83e21352a0ac4d1c3d47cd2a89`.
The development checkout still reports package version 1.2.2. Each case used
a fresh disposable app-only image/container, Gunicorn 2 workers × 4 threads,
no explicit resource limits, health checks only before the initial batch,
8 first-access requests, 10 seconds steady at concurrency 8 and 5 seconds
burst at concurrency 32. Both HTTP and resource receipts are retained under
`local/performance/http-capacity/20261127-94e56857/` on Linux-dev.

| Case | First p50/p95 (ms) | Steady p50/p95 (ms) | Burst p50/p95 (ms) | Steady req/s | Peak app MiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| Minutemen | 3506.7/3534.4 | 28.7/53.7 | 124.9/222.0 | 261.5 | 231 |
| Minutemen repeat | 3580.6/3600.7 | 30.1/54.9 | 122.1/236.5 | 250.9 | 244 |
| Explorer initial | 3672.4/3792.2 | 12.6/193.8 | 394.0/675.7 | 116.9 | 339 |
| Mimetism | 3044.6/3453.5 | 274.3/1327.7 | 1789.0/3975.5 | 15.0 | 244 |
| MediKit | 2856.4/3162.7 | 159.6/580.5 | 576.4/2354.1 | 34.6 | 235 |
| Combi Rifle | 2928.2/3430.1 | 198.6/1029.9 | 2060.9/2727.7 | 17.7 | 231 |

All six runs exited successfully without HTTP errors, restarts or OOM events.
Peak app memory is sampled container usage, not summed process RSS. The
first-access figures are small concurrent batches, not per-worker cold
percentiles. The short fixed-route stress workloads are not mixed traffic or
browser rendering measurements; the Caddy/Compose release baseline remains
outstanding.

A separate Windows single-browser profile on the same revision showed the
initial Minutemen API taking 240 ms under profiling, including 110 ms building
the Unit graph and 41 ms constructing official Army links; the repeated API
took 18 ms. The existing instance LRU releases its lock during computation,
allowing concurrent misses to duplicate work. The contribution of duplicate
initialization to the Docker latency has not yet been isolated.

Mimetism's initial/repeated API profiles took 528/229 ms; the response was
approximately 490 KB. The repeated profile still executed 583,615 function
calls, dominated by recursive Army/Unit slug and symbol enrichment, deep
copying, maintained-text references and relation enrichment. Materialized
catalog usage already deduplicates underlying Unit records. The next pilot
should reuse enriched shared Unit display data and avoid unnecessary copies
and repeated traversal, or compare a compact immutable final-response
representation if justified by storage/memory measurements. Do not restore
the retired expanded-object caches without a measured tradeoff. Separately
test preloading the shared Unit graph and other measured immutable indexes
before Gunicorn forks, or coalescing concurrent initialization; neither
strategy has yet been validated against the Docker baseline.

## Catalog presentation materialization pilot — 2026-11-27

Rules schema v24 adds a presentation-enriched JSON record alongside each shared
raw catalog usage Unit record. Catalog API handlers process compact Unit IDs and
expand them only after catalog-specific enrichment. The history-enabled integrated
Windows build completed in 238.7 s. The Rules database grew from 10,481,664 to
11,636,736 bytes (+1,155,072 bytes); Army and ITS database sizes were unchanged.
The focused catalog projection, database-set, database-set builder and real
ITS17 publication suites passed all 89 tests in 501.13 s, including v23 fallback
and repeated fixture-build determinism.
Deployment database and reference-publication verification passed with
`python -m tools.verify_deployment_assets --skip-svg`.

Linux-dev at `fe22fa55`, snapshot
`3457c90e15f84b17ce2cf44e8402726f8fa1fb71ab0b39a507024c21c3efb37b`.
The three catalog cases ran sequentially using fresh disposable app-only
containers under the same workload and server configuration as the baseline
above. HTTP and resource receipts are retained under
`local/performance/http-capacity/20261127-fe22fa55/` on Linux-dev.

| Case | First p50/p95 (ms) | Steady p50/p95 (ms) | Burst p50/p95 (ms) | Steady req/s | Peak app MiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| Mimetism | 362.4/437.9 | 134.2/235.5 | 499.5/831.2 | 57.6 | 188 |
| MediKit | 247.7/364.2 | 70.1/119.2 | 233.9/520.3 | 109.5 | 165 |
| Combi Rifle | 336.8/390.7 | 80.8/135.5 | 331.3/493.3 | 96.8 | 171 |

All three runs exited 0 without HTTP errors, restarts or OOM events. Relative
to the original baseline, first-access p95 fell 87–89%, steady p95 fell
79–87%, steady throughput rose 3.16–5.47 times, and peak sampled container
memory fell approximately 23–30%. Retain the shared presentation projection:
its 1.1 MiB additional Rules storage is justified by the measured savings.
The earlier history-enabled build took 232.07 s, but the two builds are not a
controlled before/after timing comparison. Do not attribute their difference
to this projection alone. These short fixed-route samples are not a mixed
traffic capacity claim. Further serialized-response materialization is not
currently justified; revisit only if later profiling identifies a meaningful
residual cost.

The additional Minutemen control on the same revision and snapshot used the
same workload and completed with exit 0, no HTTP errors, restarts or OOM
events. First-access p50/p95 was 3313.3/3327.4 ms; steady 28.7/52.6 ms,
burst 102.8/232.6 ms, steady throughput 264.0 req/s, peak app memory 247 MiB.
The Unit-detail first-access cost persists despite the catalog improvement;
use this control for the separate pre-fork initialization experiment.

## Pre-fork runtime index initialization pilot

A Linux-dev cold repository profile at `fe22fa55` (Python 3.14, numeric
Unit detail selected by `tools.performance.benchmark_runtime --profile`)
took 247 ms, including 189 ms in the Unit graph and 46 ms in the official
Army link index. These are the measured warmup candidates, not a profile
of the concurrent Docker workload.

The WSGI pilot warms those existing snapshot caches after complete-set
validation. Both loaders close their read-only connections before returning.
The direct development application factory stays lazy; request-specific
results remain lazy everywhere. Gunicorn already uses `--preload`.
The seven focused Windows tests passed in 20.42 s on the corrected
implementation (reference response parity, WSGI startup and opt-out, cache
reuse without opening SQLite, and preview lifecycle); Ruff, Pyright and
documentation checks passed. The orchestration belongs in the web application
rather than the fingerprinted database repository; it does not change generated
content. The original `078c1df7` deployment provenance check failed because
it modified a build input. The correction restored that source and passed
`tools.verify_deployment_assets --skip-svg` and hosted deployment smoke.

For a controlled comparison, use `tools.preview_runtime_image` with the
same capacity case and distinct receipts/tags, with and without `--lazy-indexes`
(sets `INFINITY_DB_PRELOAD_INDEXES=0` in the disposable container).
Both runs print elapsed Docker launch-to-health readiness, including container
setup and the coarse health polling interval.

Linux-dev at `e04535d0`, snapshot
`3457c90e15f84b17ce2cf44e8402726f8fa1fb71ab0b39a507024c21c3efb37b`,
Minutemen, sequential fresh containers with the same application image and
baseline workload. Receipts: `local/performance/http-capacity/20261127-e04535d0/`.

| Index mode | Readiness (s) | First p50/p95 (ms) | Steady p50/p95 (ms) | Burst p50/p95 (ms) | Steady req/s | Peak app MiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Lazy | 11.884 | 3348.7/3384.6 | 29.1/54.6 | 121.5/221.7 | 258.0 | 257 |
| Preloaded | 11.756 | 184.1/209.9 | 28.9/54.8 | 120.0/200.6 | 257.7 | 176 |

Both runs exited 0 without HTTP errors, restarts or OOM events. First-access
p95 fell 93.8% in the paired comparison, 94.1% versus the original baseline
and 93.7% versus the catalog-optimized control. Peak sampled container memory
fell about 32% in the paired comparison; warmed throughput was equivalent
within the short samples. Readiness showed no discernible penalty at this
polling granularity. An additional lazy control at `078c1df7` gave readiness
11.800 s and first-access p95 3381.6 ms. The database snapshot and storage
are unchanged by the warmup.

The remaining cross-route comparison used the same pinned revision, snapshot,
application image and workload, with sequential fresh containers. Explorer
also received a same-image lazy-index control because there was no separate
catalog-optimized Explorer baseline. Receipts are in the same directory.

| Case | Readiness (s) | First p50/p95 (ms) | Steady p50/p95 (ms) | Burst p50/p95 (ms) | Steady req/s | Peak app MiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Explorer lazy | 11.925 | 3627.3/3714.9 | 14.2/191.1 | 15.0/836.2 | 110.1 | 357 |
| Explorer preloaded | 11.936 | 2172.6/2251.1 | 12.7/190.0 | 36.3/800.5 | 118.6 | 397 |
| Mimetism preloaded | 11.899 | 382.4/415.0 | 132.7/255.4 | 581.6/733.2 | 56.6 | 214 |
| MediKit preloaded | 11.908 | 233.1/269.7 | 70.3/125.9 | 280.0/499.3 | 108.5 | 190 |
| Combi Rifle preloaded | 11.913 | 229.5/277.8 | 79.5/151.4 | 336.5/455.7 | 94.6 | 191 |

All five additional runs exited 0 with no HTTP errors, restarts or OOM events.
Explorer first-access p95 fell 39.4% versus the paired lazy control, with
comparable steady throughput and an approximately 11% increase in peak sampled
container memory. Its burst p95 improved against the paired control but was
higher than the original baseline. The catalog cases retain the materialization
gains: first-access p95 is 88–92% below the original baseline, and steady
throughput is approximately 3.1–5.3 times the original. Compared with the
catalog-optimized controls, first-access p95 fell a further 5–29%, steady
throughput was within 3%, steady p95 was 6–12% higher, and sampled peak memory
increased approximately 12–15%, while remaining below the original catalog
baseline. The short samples do not establish statistical significance for
small timing differences. No readiness penalty was discernible.

Retain selective pre-fork initialization: the substantial Unit-detail and
Explorer first-access improvements justify the measured route-dependent memory
tradeoff. Do not infer a general reduction in memory from the Unit-detail
result or add serialized catalog caches without a new measured need. The
build-time materialization and initialization experiments are complete.
The [full-stack capacity investigation](deployment.md#full-stack-v130-development-capacity-2026-11-27)
subsequently completed on Linux-dev.

## SQLite immutable mode pilot — 2026-11-27

Compared ordinary `mode=ro` against `mode=ro&immutable=1` on the complete
runtime set at `31984f479deeda52d6643a5edd6b62a6764f380f` (Windows run
used the equivalent benchmark implementation before the loop-binding lint
correction). The standalone benchmark intercepts only read-only SQLite
connections to the selected four files; it rejects WAL mode and existing
sidecars. Run against a stable set with no concurrent rebuild:

```sh
python -m tools.performance.benchmark_runtime data/generated/army.db --sqlite-immutable --cold-iterations 3 --warm-iterations 10
```

Each host completed three alternating pairs of application startups with
index preload and 13 API routes, each with one first and ten repeated
requests per app. All 858 responses per host were HTTP 200 and
byte-identical by route across both modes. Windows (SQLite 3.50.4):
startup 6219/5890 ms, first Explorer 277/232 ms, first Skill detail
61/46 ms, repeat Search 1.81/1.57 ms (ordinary/immutable median).
Linux-dev (SQLite 3.46.1): startup 9510/9312 ms, first Explorer
277/305 ms, first Skill detail 53/50 ms, repeat Search 1.66/1.58 ms.
Linux repeated-request differences ranged from a 4.5% reduction to
a 1.1% increase; first-access results varied, including Glossary
45/53 ms. These are single-threaded in-process WSGI measurements,
not Docker throughput or concurrent load measurements. Retain ordinary
read-only mode: see the [architecture decision](architecture.md#design-direction-build-time-materialization).

The full-stack capacity results are maintained in
[deployment](deployment.md#full-stack-v130-development-capacity-2026-11-27).
No further runtime materialization or immutable-SQLite adoption is implied
by these completed investigations. Revisit when measured workloads or
runtime constraints materially change.
