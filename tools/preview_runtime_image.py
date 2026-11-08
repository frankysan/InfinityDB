"""Build and smoke-test an isolated v10 Docker image without deploying it.

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
from infinity_db.variant_usage_reference import load_variant_usage_publication
from infinity_db.weapon_profile_publication import load_weapon_profile_publication
from infinity_db.web import create_app
d = Path('/app/data')
expected = {'infinity.db','rules.db','variant-usage.json','weapon-profile-sources.json'}
assert {p.name for p in d.iterdir()} == expected, 'unexpected packaged files'
Database(d / 'infinity.db').validate()
r = RulesDatabase(d / 'rules.db')
r.validate()
assert sqlite3.connect(d / 'rules.db').execute('PRAGMA user_version').fetchone()[0] == 10
data = r.deployed_objects_payload(d / 'infinity.db')
assert data and len(data['objects']) == 17 and len(data['unresolvedDeliveries']) == 1
usage = load_variant_usage_publication(
    d / 'variant-usage.json', d / 'infinity.db', d / 'rules.db',
    d / 'deployed-objects.json',
)
assert usage and usage['formatVersion'] == 2 and len(usage['variants']) == 151
assert load_weapon_profile_publication(
    d / 'weapon-profile-sources.json', d / 'infinity.db', d / 'rules.db',
)
app = create_app(d / 'infinity.db', d / 'rules.db')
assert app.deployed_objects and len(app.deployed_objects['objects']) == 17
assert app.variant_usage is not None
print('v10 immutable image artifacts: PASS')
"""

_HTTP_VERIFY = r"""
import json
from urllib.request import urlopen
root = 'http://127.0.0.1:8000'
for path in (
    '/internal/health', '/api/deployed-objects',
    '/api/variant-usage?record_id=skill:camouflage', '/api/weapons/rifle',
):
    with urlopen(root + path, timeout=8) as response:
        assert response.status == 200, path
        payload = json.loads(response.read())
    if path == '/api/deployed-objects':
        assert len(payload['items']) == 17
print('v10 container HTTP smoke: PASS')
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
        _run("docker", "run", "-d", "--rm", "--network", "none",
             "--name", container, tag)
        running = True
        last_error: subprocess.CalledProcessError | None = None
        for _ in range(20):
            try:
                _run("docker", "exec", container, "python", "-c", _HTTP_VERIFY)
                break
            except subprocess.CalledProcessError as error:
                last_error = error
                time.sleep(1)
        else:
            raise ValueError(f"v10 HTTP smoke failed: {last_error}")
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
    parser.add_argument("--tag", default="infinity-db:v10-preview-local")
    args = parser.parse_args(argv)
    if not args.source_dir.resolve().is_relative_to((ROOT / "local").resolve()):
        parser.error("Preview inputs must live under ignored local/")
    if not args.tag.startswith("infinity-db:v10-preview-"):
        parser.error("Preview image tag must start with infinity-db:v10-preview-")
    preview_image(args.source_dir.resolve(), args.tag)
    print(json.dumps({"status": "passed", "image": args.tag, "deployed": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
