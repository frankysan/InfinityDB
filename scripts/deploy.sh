#!/usr/bin/env sh
# Deploy versioned InfinityDB application/metrics images, then retain a small rollback window.
set -eu

: "${IMAGE_TAG:?Set IMAGE_TAG to an app-* version, for example app-0.4.2}"
case "$IMAGE_TAG" in
  app-*) ;;
  *)
    echo "IMAGE_TAG must begin with app-; refusing to deploy an unversioned image." >&2
    exit 2
    ;;
esac

: "${METRICS_HISTORY_IMAGE_TAG:=$IMAGE_TAG}"
export IMAGE_TAG METRICS_HISTORY_IMAGE_TAG
case "$METRICS_HISTORY_IMAGE_TAG" in
  app-*) ;;
  *)
    echo "METRICS_HISTORY_IMAGE_TAG must begin with app-." >&2
    exit 2
    ;;
esac

# The deployed images plus two rollback builds. Set RETAIN_APP_IMAGES=2 to keep
# each deployed image and one rollback build, for example. The historical name
# remains for deployment-config compatibility and applies to both repositories.
: "${RETAIN_APP_IMAGES:=3}"
case "$RETAIN_APP_IMAGES" in
  *[!0-9]* | '')
    echo "RETAIN_APP_IMAGES must be a positive integer." >&2
    exit 2
    ;;
esac

if [ "$RETAIN_APP_IMAGES" -lt 1 ]; then
  echo "RETAIN_APP_IMAGES must be at least 1." >&2
  exit 2
fi

: "${METRICS_BIND_ADDRESS:=127.0.0.1}"
: "${METRICS_PORT:=9090}"
case "$METRICS_BIND_ADDRESS" in
  0.0.0.0|::|\[::\])
    echo "METRICS_BIND_ADDRESS must be loopback or a specific trusted interface address; wildcard binds are refused." >&2
    exit 2
    ;;
esac
case "$METRICS_PORT" in
  *[!0-9]* | '' | 0)
    echo "METRICS_PORT must be an integer between 1 and 65535." >&2
    exit 2
    ;;
esac
if [ "$METRICS_PORT" -gt 65535 ]; then
  echo "METRICS_PORT must be an integer between 1 and 65535." >&2
  exit 2
fi

: "${PRUNE_APP_IMAGES:=1}"
case "$PRUNE_APP_IMAGES" in
  0|1) ;;
  *)
    echo "PRUNE_APP_IMAGES must be 0 or 1." >&2
    exit 2
    ;;
esac

repo_root="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

python=".venv/bin/python"
if [ ! -x "$python" ]; then
  echo "Deployment requires $python; run scripts/install-or-update.sh or prepare the project virtual environment first." >&2
  exit 2
fi

warn() {
  echo "WARNING: $*" >&2
}

metrics_history_running() {
  [ -n "$(docker compose ps -q metrics-history | sed -n '1p')" ]
}

application_running() {
  [ -n "$(docker compose ps -q app | sed -n '1p')" ]
}

stop_metrics_history() {
  if metrics_history_running; then
    echo "Stopping continuous metrics-history collector for deployment transition..."
    if ! docker compose stop metrics-history; then
      warn "could not stop metrics-history cleanly; continuing with application deployment."
    fi
  fi
}

collect_metrics_history() {
  phase="$1"
  echo "Collecting metrics-history $phase sample..."
  if [ "$phase" = "closing" ]; then
    if docker compose run --rm --no-deps metrics-history collect \
      --legacy-generation-at-collection; then
      status=0
    else
      status=$?
    fi
  elif docker compose run --rm --no-deps metrics-history collect; then
    status=0
  else
    status=$?
  fi

  if [ "$status" -eq 0 ]; then
    echo "Metrics-history $phase sample complete."
  else
    warn "metrics-history $phase sample failed (exit $status); continuing with application deployment."
  fi
}

start_metrics_history() {
  echo "Starting continuous metrics-history collector..."
  if docker compose up -d --no-build metrics-history; then
    echo "Metrics-history collector started."
  else
    status=$?
    warn "metrics-history collector failed to start (exit $status); application deployment remains active."
  fi
}

echo "Validating tracked runtime databases and published symbol set..."
"$python" tools/verify_deployment_assets.py

display_version="$("$python" -c 'import infinity_db; print(infinity_db.__display_version__)')"
echo "Building application image infinity-db:$IMAGE_TAG (display $display_version)..."
docker compose build --build-arg "INFINITY_DB_DISPLAY_VERSION=$display_version" app

echo "Building metrics-history image infinity-db-metrics-history:$METRICS_HISTORY_IMAGE_TAG..."
docker compose build metrics-history

# Verify both exact images before changing the running deployment. A collector
# build/verification failure is caught here; later scrape/runtime failures are
# operational warnings and do not make the application availability-critical.
sh ./scripts/verify-container-image.sh "infinity-db:$IMAGE_TAG" --published-assets
sh ./scripts/verify-metrics-history-image.sh \
  "infinity-db-metrics-history:$METRICS_HISTORY_IMAGE_TAG"

had_running_app=0
if application_running; then
  had_running_app=1
fi
stop_metrics_history
if [ "$had_running_app" = "1" ]; then
  collect_metrics_history "closing"
else
  echo "No running application found; skipping metrics-history closing sample."
fi

# Keep application availability independent of the collector. Only app/Caddy
# participate in the deployment health gate.
docker compose up -d --no-build --wait app caddy

collect_metrics_history "opening"
start_metrics_history

if [ "$PRUNE_APP_IMAGES" = "1" ]; then
  exec sh "$(dirname "$0")/prune-app-images.sh" "$RETAIN_APP_IMAGES"
fi
echo "Deployment image pruning skipped for this deployment."
