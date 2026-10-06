#!/usr/bin/env sh
# Stop or explicitly purge the isolated loopback-only InfinityDB test deployment.
set -eu

fail() {
  echo "Error: $*" >&2
  exit 1
}

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" ||
  fail "run this script from an InfinityDB Git checkout."
cd "$repo_root"

purge=0
case "${1:-}" in
  '') ;;
  --purge) purge=1 ;;
  *) fail "usage: sh scripts/stop-local-test.sh [--purge]" ;;
esac
if [ "$#" -gt 1 ]; then
  fail "usage: sh scripts/stop-local-test.sh [--purge]"
fi

if [ "$purge" = "1" ]; then
  echo "Stopping isolated infinitydb-test deployment and removing its volumes..."
  COMPOSE_PROJECT_NAME=infinitydb-test docker compose down -v
  echo "Local test deployment stopped and purged. Production deployment was not targeted."
else
  echo "Stopping isolated infinitydb-test deployment; preserving its volumes..."
  COMPOSE_PROJECT_NAME=infinitydb-test docker compose down
  echo "Local test deployment stopped. Its volumes were preserved; production deployment was not targeted."
fi
