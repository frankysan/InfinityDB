#!/usr/bin/env sh
# Validate a built InfinityDB application image and exercise production startup.
set -eu

usage() {
  echo "Usage: $0 IMAGE [--redistributable|--published-assets]" >&2
  exit 2
}

[ "$#" -ge 1 ] && [ "$#" -le 2 ] || usage
image="$1"
redistributable=0
published_assets=0
if [ "$#" -eq 2 ]; then
  case "$2" in
    --redistributable)
      redistributable=1
      ;;
    --published-assets)
      published_assets=1
      ;;
    *)
      usage
      ;;
  esac
fi

docker image inspect "$image" >/dev/null

# Validate the immutable runtime-data contract without starting the service.
docker run --rm --entrypoint python "$image" -c '
import os
from pathlib import Path

from infinity_db.database import Database
from infinity_db.rules_database import RulesDatabase

expected_environment = {
    "INFINITY_DB_DATABASE": "/app/data/infinity.db",
    "INFINITY_DB_RULES_DATABASE": "/app/data/rules.db",
}
for name, expected in expected_environment.items():
    actual = os.environ.get(name)
    if actual != expected:
        raise SystemExit(f"{name}={actual!r}; expected {expected!r}")

if hasattr(os, "geteuid") and os.geteuid() == 0:
    raise SystemExit("Application image must not run as root")

data_dir = Path("/app/data")
expected_files = {"infinity.db", "rules.db"}
actual_files = {path.name for path in data_dir.iterdir()}
if actual_files != expected_files:
    raise SystemExit(
        f"Unexpected /app/data contents: {sorted(actual_files)!r}; "
        f"expected {sorted(expected_files)!r}"
    )

Database(data_dir / "infinity.db").validate()
RulesDatabase(data_dir / "rules.db").validate()
'

if [ "$redistributable" -eq 1 ]; then
  # A redistributable CI/release image must not accidentally pick up ignored,
  # locally acquired Corvus Belli graphical assets from the build context.
  docker run --rm --entrypoint python "$image" -c '
from importlib.resources import files
from pathlib import Path

blocked = ("armies", "characteristics", "orders", "units")
roots = [
    Path("/app/src/infinity_db/web/static"),
    files("infinity_db.web").joinpath("static"),
]
for root in roots:
    for name in blocked:
        candidate = root.joinpath(name)
        if candidate.is_dir():
            raise SystemExit(f"Redistributable image contains third-party asset tree: {candidate}")
'
fi

if [ "$published_assets" -eq 1 ]; then
  # Deployment images with local third-party symbols must contain the complete
  # publication that was validated before the Docker build. Revalidate the
  # installed package so package-data omissions cannot reach production.
  docker run --rm --entrypoint python "$image" -c '
import hashlib
import json
from importlib.resources import files
from pathlib import Path, PurePosixPath

root = Path(files("infinity_db.web").joinpath("static"))
inventory_path = root / "symbol-inventory.json"
try:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"Installed published symbol inventory is unavailable: {exc}") from exc

if inventory.get("format") != "InfinityDB published symbol inventory":
    raise SystemExit("Installed published symbol inventory has an unexpected format")
if inventory.get("formatVersion") != 1:
    raise SystemExit("Installed published symbol inventory has an unsupported formatVersion")
expected = inventory.get("publishedSha256ByPath")
summary = inventory.get("summary")
if not isinstance(expected, dict) or not expected or not isinstance(summary, dict):
    raise SystemExit("Installed published symbol inventory is incomplete")
if summary.get("publishedAssetCount") != len(expected):
    raise SystemExit("Installed published symbol inventory count does not match its paths")

categories = {"armies", "characteristics", "orders", "units"}
actual = set()
for category in categories:
    category_root = root / category
    if category_root.is_dir():
        actual.update(
            path.relative_to(root).as_posix()
            for path in category_root.rglob("*.svg")
            if path.is_file()
        )
if actual != set(expected):
    missing = sorted(set(expected) - actual)
    unexpected = sorted(actual - set(expected))
    raise SystemExit(
        f"Installed symbol set does not match inventory: missing={missing[:5]!r} "
        f"unexpected={unexpected[:5]!r}"
    )

published_bytes = 0
for relative, digest in sorted(expected.items()):
    portable = PurePosixPath(relative)
    if (
        portable.is_absolute()
        or ".." in portable.parts
        or len(portable.parts) < 2
        or portable.parts[0] not in categories
        or portable.suffix != ".svg"
    ):
        raise SystemExit(f"Invalid installed symbol inventory path: {relative!r}")
    path = root.joinpath(*portable.parts)
    data = path.read_bytes()
    published_bytes += len(data)
    actual_digest = hashlib.sha256(data).hexdigest()
    if actual_digest != digest:
        raise SystemExit(f"Installed symbol SHA-256 mismatch: {relative}")
if summary.get("publishedBytes") != published_bytes:
    raise SystemExit("Installed symbol inventory byte total does not match installed files")
'
  # The manifest is an ignored deployment artifact, not image content. Bind it
  # while validating the exact image so its embedded database is proven to be
  # from the same Army ZIP as the published symbols.
  docker run --rm \
    -v "$(pwd)/data/manifests/army-symbol-build.json:/tmp/army-symbol-build.json:ro" \
    --entrypoint python "$image" -c '
from pathlib import Path

from infinity_db.deployment_provenance import validate_database_symbol_provenance
from infinity_db.symbol_manifest import load_symbol_manifest

manifest = load_symbol_manifest(Path("/tmp/army-symbol-build.json"))
validate_database_symbol_provenance(Path("/app/data/infinity.db"), manifest)
'
fi

container="infinitydb-deployment-smoke-$$"
cleanup() {
  docker rm -f "$container" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

# Match the important Compose runtime constraints while shortening the health
# interval so CI does not wait for the production 30-second cadence.
docker run -d \
  --name "$container" \
  --read-only \
  --tmpfs /tmp \
  --security-opt no-new-privileges:true \
  --health-interval 1s \
  --health-timeout 3s \
  --health-start-period 1s \
  --health-retries 20 \
  "$image" >/dev/null

attempt=0
while [ "$attempt" -lt 30 ]; do
  status="$(
    docker inspect \
      --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' \
      "$container"
  )"
  case "$status" in
    healthy)
      break
      ;;
    unhealthy|exited|dead)
      echo "Container entered state: $status" >&2
      docker logs "$container" >&2 || true
      exit 1
      ;;
  esac
  attempt=$((attempt + 1))
  sleep 1
done

if [ "$status" != "healthy" ]; then
  echo "Container did not become healthy; final state: $status" >&2
  docker logs "$container" >&2 || true
  exit 1
fi

# Exercise ordinary Army data plus a rules-backed endpoint. The synthetic Army
# fixture deliberately includes Super-Jump so its detail response can prove that
# the production process opened and composed both runtime databases.
docker exec "$container" python -c '
import json
from urllib.request import urlopen

with urlopen("http://127.0.0.1:8000/api/armies", timeout=3) as response:
    armies = {item["id"]: item for item in json.load(response)["items"]}
if not armies:
    raise SystemExit("/api/armies returned no deployment-fixture armies")

main = armies.get(101)
sectorial = armies.get(102)
if main is None or main.get("role") != "main" or main.get("group_id") is not None:
    raise SystemExit(f"Army 101 hierarchy mismatch: {main!r}")
if sectorial is None or sectorial.get("role") != "sectorial" or sectorial.get("group_id") != 101:
    raise SystemExit(f"Army 102 hierarchy mismatch: {sectorial!r}")

with urlopen("http://127.0.0.1:8000/api/skills/74", timeout=3) as response:
    skill = json.load(response)
if not skill.get("rules"):
    raise SystemExit("/api/skills/74 did not include curated rules data")

with urlopen("http://127.0.0.1:8000/api/version", timeout=3) as response:
    version = json.load(response)
if not version.get("version") or not version.get("snapshot_revision"):
    raise SystemExit("/api/version returned incomplete runtime identity")
'

if [ "$published_assets" -eq 1 ]; then
  docker exec "$container" python -c '
import json
from importlib.resources import files
from pathlib import Path
from urllib.request import urlopen

root = Path(files("infinity_db.web").joinpath("static"))
inventory = json.loads((root / "symbol-inventory.json").read_text(encoding="utf-8"))
paths = sorted(inventory["publishedSha256ByPath"])
for category in ("armies", "characteristics", "orders", "units"):
    try:
        relative = next(path for path in paths if path.startswith(category + "/"))
    except StopIteration as exc:
        raise SystemExit(f"Installed symbol inventory has no {category} asset") from exc
    with urlopen(f"http://127.0.0.1:8000/static/{relative}", timeout=3) as response:
        if response.status != 200:
            raise SystemExit(f"Published symbol route returned {response.status}: {relative}")
        if response.headers.get_content_type() != "image/svg+xml":
            raise SystemExit(f"Published symbol route has wrong content type: {relative}")
'
fi

printf 'Validated image %s and healthy production startup.\n' "$image"
