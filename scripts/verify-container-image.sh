#!/usr/bin/env sh
# Validate a built InfinityDB application image and exercise production startup.
set -eu

usage() {
  echo "Usage: $0 IMAGE [--packaged-assets|--published-assets]" >&2
  exit 2
}

[ "$#" -ge 1 ] && [ "$#" -le 2 ] || usage
image="$1"
packaged_assets=0
published_assets=0
if [ "$#" -eq 2 ]; then
  case "$2" in
    --packaged-assets)
      packaged_assets=1
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
from infinity_db.database_set import validate_database_set
from infinity_db.rules_database import RulesDatabase
from infinity_db.variant_usage_reference import load_runtime_variant_usage
from infinity_db.weapon_profile_publication import load_runtime_weapon_profile_publication

expected_environment = {
    "INFINITY_DB_DB_DIR": "/app/data",
}
for name, expected in expected_environment.items():
    actual = os.environ.get(name)
    if actual != expected:
        raise SystemExit(f"{name}={actual!r}; expected {expected!r}")

if hasattr(os, "geteuid") and os.geteuid() == 0:
    raise SystemExit("Application image must not run as root")

data_dir = Path("/app/data")
report = validate_database_set(data_dir, require_complete=True)
rules = RulesDatabase(data_dir / "rules_n5.db")
rules.validate()
restrictions = rules.restrictions_payload()
expected_files = set(report["sha256"])
actual_files = {path.name for path in data_dir.iterdir()}
if actual_files != expected_files:
    raise SystemExit(
        f"Unexpected /app/data contents: {sorted(actual_files)!r}; "
        f"expected {sorted(expected_files)!r}"
    )

if (
    not restrictions["available"]
    or restrictions["source"]["id"] != "n5-core-v5.3-pdf"
    or restrictions["source"]["page"] != 194
    or len(restrictions["items"]) != 14
    or restrictions["evaluationSupported"] is not False
):
    raise SystemExit("Release image has incomplete reviewed Restrictions data")
publication = rules.deployed_objects_payload(data_dir / "army.db")
if publication is None or len(publication["objects"]) != 17:
    raise SystemExit("Release image has no complete reviewed deployed-object publication")
if len(publication["unresolvedDeliveries"]) != 1:
    raise SystemExit("Release image lost the unresolved deployed-object delivery")
usage, _ = load_runtime_variant_usage(data_dir / "army.db", data_dir / "rules_n5.db")
if usage is None or not usage["variants"]:
    raise SystemExit("Release image is missing the reviewed exact-variant publication")
weapon_sources, _ = load_runtime_weapon_profile_publication(
    data_dir / "army.db", data_dir / "rules_n5.db",
)
rifle = Database(data_dir / "army.db").get_catalog_item("weapons", "rifle")
if not weapon_sources or rifle is None:
    raise SystemExit("Release image is missing reviewed Weapon Chart citations")
profile = rifle["profiles"][0]
citation = weapon_sources.get((rifle["id"], profile["id"], profile["mode"]))
if not citation or citation["source_id"] != "n5-core-v5.3-pdf" or citation["page"] != 183:
    raise SystemExit("Release image has no matching Rifle Weapon Chart citation")
'

if [ "$published_assets" -eq 1 ]; then
  packaged_assets=1
fi

if [ "$packaged_assets" -eq 1 ]; then
  # Images that package the tracked third-party symbols must contain the complete
  # publication that was validated before the Docker build. Revalidate the
  # installed package so package-data omissions cannot reach production.
  docker run --rm --entrypoint python "$image" -c '
import hashlib
import json
from importlib.resources import files
from pathlib import Path, PurePosixPath

from infinity_db.database import Database

root = Path(files("infinity_db.web").joinpath("static"))
publication = Database(Path("/app/data/army.db")).symbol_publication()
if publication is None:
    raise SystemExit("Embedded symbol publication is missing")
expected = publication.get("publishedSha256ByPath")
if not isinstance(expected, dict) or not expected:
    raise SystemExit("Embedded symbol hashes are missing")

categories = {"armies", "characteristics", "orders", "peripherals", "units"}
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
        f"Installed symbol set does not match publication manifest: missing={missing[:5]!r} "
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
        raise SystemExit(f"Invalid installed symbol publication path: {relative!r}")
    path = root.joinpath(*portable.parts)
    data = path.read_bytes()
    published_bytes += len(data)
    actual_digest = hashlib.sha256(data).hexdigest()
    if actual_digest != digest:
        raise SystemExit(f"Installed symbol SHA-256 mismatch: {relative}")
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
import os
from urllib.request import urlopen

from infinity_db.web.release_notes import render_current_release_notes_html

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

with urlopen("http://127.0.0.1:8000/api/deployed-objects", timeout=3) as response:
    deployed = json.load(response)
if len(deployed.get("items", [])) != 17 or len(deployed.get("unresolved_deliveries", [])) != 1:
    raise SystemExit("/api/deployed-objects did not publish the reviewed release objects")
with urlopen("http://127.0.0.1:8000/deployed-objects", timeout=3) as response:
    if b"deployed" not in response.read().lower():
        raise SystemExit("/deployed-objects browser entry point unavailable")

with urlopen("http://127.0.0.1:8000/api/restrictions", timeout=3) as response:
    restrictions = json.load(response)
if restrictions.get("evaluationSupported") is not False:
    raise SystemExit("/api/restrictions incorrectly claims legality evaluation")
if not restrictions.get("available") or len(restrictions.get("items", [])) != 14:
    raise SystemExit("/api/restrictions has incomplete reviewed source conditions")
jump = next(
    (row for row in restrictions["items"] if
     row["subject"] == "Motorcycle" and row["action"] == "upward-jump"),
    None,
)
if (
    jump is None
    or jump["scope"] != "while-mounted-upwards-only"
    or jump["operation"] != {
        "kind": "directional-skill-movement", "qualifier": {"direction": "upward"}
    }
):
    raise SystemExit("/api/restrictions lost the mounted upward-Jump condition")
chosen = [
    row for row in restrictions["items"]
    if row["action"] == "lieutenant-selection"
]
if len(chosen) != 2 or any(
    row["operation"] != {
        "kind": "army-role-selection", "qualifier": {"role": "lieutenant"}
    }
    for row in chosen
):
    raise SystemExit("/api/restrictions lost Lieutenant selection-only scope")

with urlopen("http://127.0.0.1:8000/api/weapons/rifle", timeout=3) as response:
    rifle = json.load(response)
if rifle.get("profile_citations_available") is not True:
    raise SystemExit("/api/weapons/rifle has the wrong Weapon Chart publication status")
profile_sources = rifle["profiles"][0].get("profile_citations", [])
if not any(
    citation.get("source_id") == "n5-core-v5.3-pdf" and citation.get("page") == 183
    for citation in profile_sources
):
    raise SystemExit("/api/weapons/rifle lost its reviewed Weapon Chart citation")

with urlopen("http://127.0.0.1:8000/api/version", timeout=3) as response:
    version = json.load(response)
if not version.get("version") or not version.get("snapshot_revision"):
    raise SystemExit("/api/version returned incomplete runtime identity")

expected_display_version = os.environ.get("INFINITY_DB_DISPLAY_VERSION", "").strip()
if expected_display_version:
    with urlopen("http://127.0.0.1:8000/", timeout=3) as response:
        page = response.read().decode("utf-8")
    if f"Version {expected_display_version}" not in page:
        raise SystemExit(
            f"Browser footer does not show built display version {expected_display_version!r}"
        )

with urlopen("http://127.0.0.1:8000/changes", timeout=3) as response:
    changes = response.read().decode("utf-8")
expected_release_notes = render_current_release_notes_html()
if not expected_release_notes or expected_release_notes not in changes:
    raise SystemExit("/changes did not render the installed canonical changelog")
'

# Current releases must expose a real reviewed source group through the installed API.
docker exec "$container" python -c '
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

from infinity_db.variant_usage_reference import load_runtime_variant_usage

directory = Path("/app/data")
publication, _ = load_runtime_variant_usage(directory / "army.db", directory / "rules_n5.db")
if publication is None or not publication["variants"]:
    raise SystemExit("Release image has no reviewed exact-variant publication")
record_id = publication["variants"][0]["variant"]["recordId"]
url = "http://127.0.0.1:8000/api/variant-usage?record_id=" + quote(record_id)
with urlopen(url, timeout=3) as response:
    result = json.load(response)
if result.get("recordId") != record_id or not result.get("items"):
    raise SystemExit("Exact-variant usage API is missing the installed publication")
if result.get("sourceSnapshot") != publication["sourceSnapshot"]:
    raise SystemExit("Exact-variant usage API returned unexpected source provenance")
'

if [ "$packaged_assets" -eq 1 ]; then
  docker exec "$container" python -c '
from pathlib import Path
from urllib.request import urlopen

from infinity_db.database import Database

# The runtime publishes source identity in the Army database. Standalone
# build manifests are intentionally absent from the immutable container.
publication = Database(Path("/app/data/army.db")).symbol_publication()
if publication is None:
    raise SystemExit("Embedded symbol publication is missing")
paths = sorted(publication["publishedSha256ByPath"])
present_categories = {path.split("/", 1)[0] for path in paths}
required_categories = {"armies", "characteristics", "orders", "units"}
if not required_categories <= present_categories:
    missing = sorted(required_categories - present_categories)
    raise SystemExit(f"Installed symbol publication is missing categories: {missing!r}")
for category in sorted(present_categories):
    relative = next(path for path in paths if path.startswith(category + "/"))
    with urlopen(f"http://127.0.0.1:8000/static/{relative}", timeout=3) as response:
        if response.status != 200:
            raise SystemExit(f"Published symbol route returned {response.status}: {relative}")
        if response.headers.get_content_type() != "image/svg+xml":
            raise SystemExit(f"Published symbol route has wrong content type: {relative}")
'
fi

printf 'Validated image %s and healthy production startup.\n' "$image"
