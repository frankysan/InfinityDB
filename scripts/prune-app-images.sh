#!/usr/bin/env sh
# Remove old InfinityDB deployment image tags without affecting other repositories.
set -eu

retain="${1:-3}"
case "$retain" in
  *[!0-9]* | '')
    echo "Retention count must be a positive integer." >&2
    exit 2
    ;;
esac

if [ "$retain" -lt 1 ]; then
  echo "Retention count must be at least 1." >&2
  exit 2
fi

prune_repository() {
  repository="$1"
  service="$2"
  description="$3"

  # Always protect the image used by the running Compose service, even if it
  # is not one of the most recently-created local images. If the service is
  # not running, retain the newest images instead.
  current_image="$(docker compose ps -q "$service" | sed -n '1p')"
  if [ -n "$current_image" ]; then
    current_image="$(docker inspect --format '{{.Image}}' "$current_image")"
  fi

  # Tags are newest first. Restrict discovery/deletion to this one InfinityDB
  # repository; Caddy, Portainer, dangling images, and unrelated repositories
  # are deliberately untouched.
  docker image ls --no-trunc --filter "reference=$repository:app-*" --format '{{.Tag}} {{.ID}}' |
  awk -v current="$current_image" -v retain="$retain" -v repository="$repository" '
    BEGIN {
      if (current != "") {
        seen[current] = 1
        builds = 1
      }
    }
    $2 == current { next }
    !seen[$2]++ { builds++ }
    builds > retain { print repository ":" $1 }
  ' |
  while IFS= read -r image; do
    [ -n "$image" ] || continue
    echo "Removing old $description image tag: $image"
    docker image rm "$image"
  done
}

prune_repository infinity-db app application
prune_repository infinity-db-metrics-history metrics-history metrics-history
