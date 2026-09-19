#!/usr/bin/env sh
# Validate a built InfinityDB application image and exercise production startup.
set -eu

usage() {
  echo "Usage: $0 IMAGE [--redistributable]" >&2
  exit 2
}

[ "$#" -ge 1 ] && [ "$#" -le 2 ] || usage
image="$1"
redistributable=0
if [ "$#" -eq 2 ]; then
  [ "$2" = "--redistributable" ] || usage
  redistributable=1
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

printf 'Validated image %s and healthy production startup.\n' "$image"
