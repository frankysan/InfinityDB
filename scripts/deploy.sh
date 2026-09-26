#!/usr/bin/env sh
# Deploy a versioned InfinityDB image, then retain a small rollback window.
set -eu

: "${IMAGE_TAG:?Set IMAGE_TAG to an app-* version, for example app-0.4.2}"
case "$IMAGE_TAG" in
  app-*) ;;
  *)
    echo "IMAGE_TAG must begin with app-; refusing to deploy an unversioned image." >&2
    exit 2
    ;;
esac

# The deployed image plus two rollback builds. Set RETAIN_APP_IMAGES=2 to keep
# the deployed image and one rollback build, for example.
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

echo "Validating manifest-bound published symbol set..."
"$python" tools/verify_deployment_assets.py

display_version="$("$python" -c 'import infinity_db; print(infinity_db.__display_version__)')"
echo "Building application image infinity-db:$IMAGE_TAG (display $display_version)..."
docker compose build --build-arg "INFINITY_DB_DISPLAY_VERSION=$display_version" app

# Verify the exact image that Compose will deploy. The published-assets mode
# checks that the locally validated symbol publication survived Docker/package
# installation and that production routes can serve representative assets.
sh ./scripts/verify-container-image.sh "infinity-db:$IMAGE_TAG" --published-assets

docker compose up -d --no-build --wait
if [ "$PRUNE_APP_IMAGES" = "1" ]; then
  exec sh "$(dirname "$0")/prune-app-images.sh" "$RETAIN_APP_IMAGES"
fi
echo "Application image pruning skipped for this deployment."
