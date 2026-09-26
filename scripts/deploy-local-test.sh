#!/usr/bin/env sh
# Deploy the current matched artifacts to an isolated loopback-only test stack.
set -eu

fail() {
  echo "Error: $*" >&2
  exit 1
}

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" ||
  fail "run this script from an InfinityDB Git checkout."
cd "$repo_root"

port="${1:-8080}"
case "$port" in
  *[!0-9]* | '' | 0) fail "test port must be an integer between 1 and 65535." ;;
esac
if [ "$port" -gt 65535 ]; then
  fail "test port must be an integer between 1 and 65535."
fi

metrics_port="${2:-$((port + 1))}"
case "$metrics_port" in
  *[!0-9]* | '' | 0) fail "metrics test port must be an integer between 1 and 65535." ;;
esac
if [ "$metrics_port" -gt 65535 ]; then
  fail "metrics test port must be an integer between 1 and 65535."
fi

short_commit="$(git rev-parse --short=12 HEAD)"
image_tag="app-test-$short_commit"

echo "Starting loopback-only test deployment on http://localhost:$port ..."
COMPOSE_PROJECT_NAME=infinitydb-test \
DOMAIN=localhost \
BIND_ADDRESS=127.0.0.1 \
HTTP_PORT="$port" \
METRICS_BIND_ADDRESS=127.0.0.1 \
METRICS_PORT="$metrics_port" \
IMAGE_TAG="$image_tag" \
RETAIN_APP_IMAGES=1 \
PRUNE_APP_IMAGES=0 \
  sh ./scripts/deploy-transferred.sh

printf 'Local test deployment ready: http://localhost:%s\n' "$port"
printf 'Local test metrics: http://localhost:%s/metrics\n' "$metrics_port"
printf 'Remote access: ssh -L %s:127.0.0.1:%s <server>\n' "$port" "$port"
