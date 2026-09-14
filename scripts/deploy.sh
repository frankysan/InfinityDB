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

docker compose up -d --build --wait
exec sh "$(dirname "$0")/prune-app-images.sh" "$RETAIN_APP_IMAGES"
