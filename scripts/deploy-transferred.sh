#!/usr/bin/env sh
# Deploy a commit-matched artifact set transferred from a development checkout.
set -eu

config_file=".infinity-db-deploy.env"

fail() {
  echo "Error: $*" >&2
  exit 1
}

config_value() {
  [ -f "$config_file" ] || return 0
  sed -n "s/^$1=//p" "$config_file" | sed -n '1p' | tr -d '\r'
}

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" ||
  fail "run this script from an InfinityDB Git checkout."
cd "$repo_root"

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  fail "the checkout has tracked changes; commit, stash, or discard them first."
fi

if [ ! -x .venv/bin/python ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv .venv
fi

echo "Installing application dependencies..."
.venv/bin/pip install -e .

version="$(.venv/bin/python -c 'import infinity_db; print(infinity_db.__version__)')"
image_tag="${IMAGE_TAG:-app-v$version}"
domain="${DOMAIN:-$(config_value DOMAIN)}"
retain="${RETAIN_APP_IMAGES:-$(config_value RETAIN_APP_IMAGES)}"
retain="${retain:-3}"
metrics_bind="${METRICS_BIND_ADDRESS:-$(config_value METRICS_BIND_ADDRESS)}"
metrics_bind="${metrics_bind:-127.0.0.1}"
metrics_port="${METRICS_PORT:-$(config_value METRICS_PORT)}"
metrics_port="${metrics_port:-9090}"

[ -n "$domain" ] || fail \
  "DOMAIN is not configured; set DOMAIN or save it in $config_file before deployment."
case "$retain" in
  *[!0-9]* | '' | 0) fail "RETAIN_APP_IMAGES must be a positive integer." ;;
esac

echo "Deploying transferred artifacts as $image_tag without rebuilding runtime data..."
DOMAIN="$domain" IMAGE_TAG="$image_tag" RETAIN_APP_IMAGES="$retain" \
METRICS_BIND_ADDRESS="$metrics_bind" METRICS_PORT="$metrics_port" \
  sh ./scripts/deploy.sh
