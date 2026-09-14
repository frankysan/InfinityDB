#!/usr/bin/env sh
# Interactively install or update the server checkout to its newest Git tag.
set -eu

config_file=".infinity-db-deploy.env"

fail() {
  echo "Error: $*" >&2
  exit 1
}

prompt() {
  label="$1"
  default="$2"
  printf '%s [%s]: ' "$label" "$default" >&2
  IFS= read -r answer || exit 1
  printf '%s' "${answer:-$default}"
}

config_value() {
  [ -f "$config_file" ] || return 0
  sed -n "s/^$1=//p" "$config_file" | sed -n '1p' | tr -d '\r'
}

git_root="$(git rev-parse --show-toplevel 2>/dev/null)" ||
  fail "run this script from an InfinityDB Git checkout."
cd "$git_root"

# A local tracked edit could be overwritten by changing tags. Untracked files,
# including the optional deployment config and raw source data, are preserved.
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  fail "the checkout has tracked changes; commit, stash, or discard them first."
fi

echo "Fetching release tags from origin..."
git fetch origin --tags --prune
release_tag="$(git tag --sort=-version:refname | sed -n '1p')"
[ -n "$release_tag" ] || fail "no Git tags are available from origin."

echo "Latest release tag: $release_tag"
printf 'Continue with this release? [Y/n]: '
IFS= read -r continue_answer || exit 1
case "${continue_answer:-Y}" in
  Y|y|yes|YES) ;;
  *) echo "No changes made."; exit 0 ;;
esac

domain_default="$(config_value DOMAIN)"
domain="$(prompt 'Public domain (or localhost)' "${domain_default:-localhost}")"
[ -n "$domain" ] || fail "a domain is required."

retain_default="$(config_value RETAIN_APP_IMAGES)"
retain="$(prompt 'Number of app images to retain' "${retain_default:-3}")"
case "$retain" in
  *[!0-9]* | '' | 0) fail "retention must be a positive integer." ;;
esac

printf 'Save these settings to %s for later runs? [Y/n]: ' "$config_file"
IFS= read -r save_answer || exit 1
case "${save_answer:-Y}" in
  Y|y|yes|YES)
    umask 077
    printf 'DOMAIN=%s\nRETAIN_APP_IMAGES=%s\n' "$domain" "$retain" > "$config_file"
    echo "Saved deployment settings to $config_file."
    ;;
esac

echo "Checking out $release_tag..."
git checkout --detach "$release_tag"

if [ ! -x .venv/bin/python ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv .venv
fi

echo "Installing application dependencies..."
.venv/bin/pip install -e .

echo "Building the validated database image input..."
.venv/bin/infinity-db build --compact

echo "Deploying image app-$release_tag..."
DOMAIN="$domain" IMAGE_TAG="app-$release_tag" RETAIN_APP_IMAGES="$retain" \
  sh ./scripts/deploy.sh
