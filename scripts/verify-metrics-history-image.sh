#!/usr/bin/env sh
# Verify the immutable metrics-history image before it is allowed into deployment.
set -eu

image="${1:-}"
if [ -z "$image" ]; then
  echo "Usage: sh scripts/verify-metrics-history-image.sh <image>" >&2
  exit 2
fi

echo "Verifying metrics-history image $image..."
docker run --rm \
  --read-only \
  --tmpfs /tmp \
  -e INFINITYDB_METRICS_HISTORY_DATABASE=/tmp/history.db \
  "$image" status >/dev/null

echo "Metrics-history image verified."
