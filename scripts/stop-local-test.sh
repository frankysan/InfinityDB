#!/usr/bin/env sh
# Stop the isolated loopback-only InfinityDB test deployment.
set -eu

fail() {
  echo "Error: $*" >&2
  exit 1
}

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" ||
  fail "run this script from an InfinityDB Git checkout."
cd "$repo_root"

echo "Stopping isolated infinitydb-test deployment..."
COMPOSE_PROJECT_NAME=infinitydb-test docker compose down

echo "Local test deployment stopped. Production deployment was not targeted."
