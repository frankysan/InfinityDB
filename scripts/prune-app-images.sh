#!/usr/bin/env sh
# Remove old InfinityDB application image tags without affecting other images.
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

# Always protect the image used by the running Compose app container, even if
# it is not one of the most recently-created local images. If the app is not
# running (for example, when this script is invoked manually), retain the
# newest images instead.
current_image="$(docker compose ps -q app | sed -n '1p')"
if [ -n "$current_image" ]; then
  current_image="$(docker inspect --format '{{.Image}}' "$current_image")"
fi

# `docker image ls` returns images newest first. Restrict both discovery and
# deletion to this repository's versioned application tags; Caddy, Portainer,
# dangling images, and all other repositories are deliberately untouched.
docker image ls --no-trunc --filter 'reference=infinity-db:app-*' --format '{{.Tag}} {{.ID}}' |
awk -v current="$current_image" -v retain="$retain" '
  BEGIN {
    if (current != "") {
      seen[current] = 1
      builds = 1
    }
  }
  $2 == current { next }
  !seen[$2]++ { builds++ }
  builds > retain { print "infinity-db:" $1 }
' |
while IFS= read -r image; do
  [ -n "$image" ] || continue
  echo "Removing old application image tag: $image"
  docker image rm "$image"
done
