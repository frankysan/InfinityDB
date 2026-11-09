"""Build and smoke-test an isolated runtime Docker image without deploying it.

The preview uses an ignored, source-matched staging bundle, never replaces
production containers, and restores the tracked release's Docker build inputs.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path

from tools.prepare_runtime_bundle import DEFAULT_OUTPUT, DEFAULT_SOURCE, prepare_bundle

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE = ROOT / "local/v10-candidate"

_IMAGE_VERIFY = r"""
import json
import sqlite3
from pathlib import Path
from infinity_db.database import Database
from infinity_db.rules_database import RulesDatabase
from infinity_db.database_set import validate_database_set
from infinity_db.variant_usage_reference import load_runtime_variant_usage
from infinity_db.weapon_profile_publication import load_weapon_profile_publication
from infinity_db.web import create_app
d = Path('/app/data')
expected = set(validate_database_set(d)['sha256'])
assert {p.name for p in d.iterdir()} == expected, 'unexpected packaged files'
Database(d / 'infinity.db').validate()
r = RulesDatabase(d / 'rules.db')
r.validate()
assert sqlite3.connect(d / 'rules.db').execute('PRAGMA user_version').fetchone()[0] in (10,11)
data = r.deployed_objects_payload(d / 'infinity.db')
assert data and len(data['objects']) == 17 and len(data['unresolvedDeliveries']) == 1
usage, _ = load_runtime_variant_usage(d / 'infinity.db', d / 'rules.db')
assert usage and usage['formatVersion'] == 2 and len(usage['variants']) == 151
assert load_weapon_profile_publication(
    d / 'weapon-profile-sources.json', d / 'infinity.db', d / 'rules.db',
)
app = create_app(d / 'infinity.db', d / 'rules.db')
assert app.deployed_objects and len(app.deployed_objects['objects']) == 17
assert app.variant_usage is not None
print('Runtime immutable image artifacts: PASS')
"""

_HEALTH_PROBE = r"""
from urllib.request import urlopen
with urlopen('http://127.0.0.1:8000/internal/health', timeout=5) as response:
    assert response.status == 200 and response.read() == b'ok\n'
"""

_HTTP_VERIFY = r"""
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

root = 'http://127.0.0.1:8000'


def get_json(path):
    with urlopen(root + path, timeout=8) as response:
        assert response.status == 200, path
        return json.load(response)


deployed = get_json('/api/deployed-objects')
assert len(deployed['items']) == 17
assert len(deployed['unresolved_deliveries']) == 1

from infinity_db.variant_usage_reference import load_runtime_variant_usage
directory = Path('/app/data')
publication, _ = load_runtime_variant_usage(directory / 'infinity.db', directory / 'rules.db')
assert publication is not None
record_id = publication['variants'][0]['variant']['recordId']
usage = get_json('/api/variant-usage?record_id=' + quote(record_id))
assert usage['recordId'] == record_id and usage['items']
assert usage['sourceSnapshot'] == publication['sourceSnapshot']

rifle = get_json('/api/weapons/rifle')
assert rifle['profile_citations_available']
assert any(
    citation['source_id'] == 'n5-core-v5.3-pdf' and citation['page'] == 183
    for citation in rifle['profiles'][0]['profile_citations']
)
print('Runtime container HTTP smoke: PASS')
"""


def _run(*arguments: str) -> None:
    subprocess.run(arguments, cwd=ROOT, check=True)


def preview_image(stage: Path, tag: str) -> None:
    """Run a disposable Docker image and clean up; never touch deployed services."""
    if not shutil.which("docker"):
        raise ValueError("Docker CLI is not available on this worker")
    if not stage.is_dir():
        raise ValueError(f"Missing prevalidated candidate: {stage}")
    container = "infinitydb-v10-preview-check"
    if subprocess.run(
        ["docker", "info", "--format", "{{.ServerVersion}}"],
        cwd=ROOT, capture_output=True, check=False,
    ).returncode != 0:
        raise ValueError("Docker Desktop Linux engine is unavailable")
    built = False
    running = False
    try:
        prepare_bundle(stage, DEFAULT_OUTPUT)
        _run("docker", "build", "--tag", tag, ".")
        built = True
        _run("docker", "run", "--rm", "--entrypoint", "python", tag, "-c", _IMAGE_VERIFY)
        # No host ports are published. Use Docker's private bridge network:
        # --network none leaves loopback unavailable for in-container HTTP probes.
        _run("docker", "run", "-d", "--rm", "--read-only",
             "--tmpfs", "/tmp", "--security-opt", "no-new-privileges",
             "--name", container, tag)
        running = True
        for _ in range(20):
            probe = subprocess.run(
                ["docker", "exec", container, "python", "-c", _HEALTH_PROBE],
                cwd=ROOT, capture_output=True, check=False,
            )
            if probe.returncode == 0:
                break
            time.sleep(1)
        else:
            subprocess.run(["docker", "logs", container], cwd=ROOT, check=False)
            raise ValueError("v10 container did not become HTTP-healthy")
        # Run the substantive API assertions once after readiness.
        _run("docker", "exec", container, "python", "-c", _HTTP_VERIFY)
    finally:
        if running:
            subprocess.run(["docker", "stop", container], cwd=ROOT, check=False)
        if built:
            subprocess.run(["docker", "image", "rm", tag], cwd=ROOT, check=False)
        # Any subsequent ordinary docker build must use the tracked release pair.
        prepare_bundle(DEFAULT_SOURCE, DEFAULT_OUTPUT)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument(
        "--tracked-release", action="store_true",
        help="Preview the exact promoted data/generated/ release instead of ignored staging",
    )
    parser.add_argument("--tag", default="infinity-db:v10-preview-local")
    args = parser.parse_args(argv)
    if args.tracked_release:
        if args.source_dir != DEFAULT_CANDIDATE:
            parser.error("--tracked-release cannot be combined with --source-dir")
        source = DEFAULT_SOURCE
    else:
        source = args.source_dir.resolve()
        if not source.is_relative_to((ROOT / "local").resolve()):
            parser.error("Preview inputs must live under ignored local/")
    if not args.tag.startswith("infinity-db:v10-preview-"):
        parser.error("Preview image tag must start with infinity-db:v10-preview-")
    preview_image(source, args.tag)
    print(json.dumps({"status": "passed", "image": args.tag, "deployed": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
