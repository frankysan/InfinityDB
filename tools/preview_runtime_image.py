"""Verify an isolated Docker image of one complete database set without deployment."""
from __future__ import annotations

import argparse
import base64
import json
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from infinity_db.database_set import COMPLETE_RUNTIME_FILES, validate_database_set
from tools.operations.receipt_output import require_new_receipt, write_new_json_receipt
from tools.performance.capacity_test import (
    _render_summary,
    capacity_test,
)
from tools.runtime_semantic_baseline import CURRENT_BASELINE, capture, check

ROOT = Path(__file__).resolve().parents[1]

_IMAGE_VERIFY = """
from pathlib import Path
from infinity_db.web import create_app_from_database_set
from infinity_db.database_set import validate_database_set
d = Path('/app/data')
report = validate_database_set(d, require_complete=True)
assert set(report['sha256']) == {'army.db', 'rules_n5.db', 'its_17.db', 'its_18.db'}
assert {p.name for p in d.iterdir()} == set(report['sha256'])
app = create_app_from_database_set(d)
assert len(app.deployed_objects['objects']) == 17
assert len(app.variant_usage['variants']) == 150
assert len(app.weapon_profile_citations) == 69
print('Runtime immutable image artifacts: PASS')
"""

_HTTP_FETCH = """
import base64,json,sys
from urllib.request import urlopen
from urllib.error import HTTPError
try:
    response = urlopen('http://127.0.0.1:8000' + sys.argv[1], timeout=15)
except HTTPError as error:
    response = error
with response:
    print(json.dumps([response.status, list(response.headers.items()),
                      base64.b64encode(response.read()).decode('ascii')]))
"""


def _copy_build_context(context: Path, selected: Path) -> None:
    """Copy current tracked source bytes, overriding only the explicitly selected set."""
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    for name in names:
        if not name or name.startswith("data/generated/"):
            continue
        source = ROOT / name
        if source.is_file():
            destination = context / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
    output = context / "data/generated"
    output.mkdir(parents=True, exist_ok=True)
    for name in sorted(COMPLETE_RUNTIME_FILES):
        shutil.copyfile(selected / name, output / name)


def _measure_capacity(container: str, output: Path) -> None:
    """Run the existing capacity workload through the private published port."""
    binding = subprocess.check_output(
        ["docker", "port", container, "8000/tcp"], text=True,
    ).strip()
    host, separator, port = binding.rpartition(":")
    if host != "127.0.0.1" or not separator or not port.isdecimal():
        raise ValueError("Preview capacity port is not bound to IPv4 loopback")
    base_url = f"http://127.0.0.1:{port}"
    print("Running Unit Explorer capacity workload (60s steady, 10s burst)", flush=True)
    report = capacity_test(
        base_url, timeout=10, warmup_passes=2, steady_seconds=60,
        steady_concurrency=8, burst_seconds=10, burst_concurrency=32,
        scenario="unit-explorer",
    )
    write_new_json_receipt(output, report)
    print(_render_summary(report))
    print(f"Report: {output}")
    if any(phase["errors"] for phase in report["phases"]):
        raise ValueError("Preview capacity workload reported HTTP errors")


def preview_image(
    selected: Path, tag: str, baseline: Path = CURRENT_BASELINE,
    *, capacity_output: Path | None = None,
) -> None:
    """Build/start/check/remove a private preview; never modify the serving directory."""
    if not shutil.which("docker"):
        raise ValueError("Docker CLI is unavailable")
    require_new_receipt(capacity_output)
    selected = selected.resolve()
    before = validate_database_set(selected, require_complete=True)["sha256"]
    subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], check=True)
    if subprocess.run(["docker", "image", "inspect", tag], capture_output=True).returncode == 0:
        raise ValueError("Preview tag already exists; choose a new disposable tag")
    container = "infinitydb-preview-" + uuid.uuid4().hex[:12]
    built = running = False
    local = ROOT / "local"
    local.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="image-preview-", dir=local) as directory:
        context = Path(directory).resolve()
        assert context.is_relative_to(local.resolve())
        _copy_build_context(context, selected)
        try:
            subprocess.run(["docker", "build", "--tag", tag, str(context)], check=True)
            built = True
            if capacity_output is None:
                subprocess.run([
                    "docker", "run", "--rm", "--entrypoint", "python", tag, "-c", _IMAGE_VERIFY,
                ], check=True)
            publish = ["--publish", "127.0.0.1::8000"] if capacity_output is not None else []
            subprocess.run([
                "docker", "run", "-d", "--rm", "--read-only", "--tmpfs", "/tmp",
                "--security-opt", "no-new-privileges", *publish, "--name", container, tag,
            ], check=True)
            running = True
            for _ in range(30):
                response = subprocess.run([
                    "docker", "exec", container, "python", "-c", _HTTP_FETCH, "/internal/health",
                ], capture_output=True, text=True)
                if response.returncode == 0 and json.loads(response.stdout)[0] == 200:
                    break
                time.sleep(1)
            else:
                subprocess.run(["docker", "logs", container], check=False)
                raise ValueError("Preview did not become healthy")

            if capacity_output is not None:
                _measure_capacity(container, capacity_output)
            else:
                _verify_semantic_preview(container, baseline)
        finally:
            if running:
                subprocess.run(["docker", "stop", container], check=False)
            if built:
                subprocess.run(["docker", "image", "rm", tag], check=False)
    if validate_database_set(selected, require_complete=True)["sha256"] != before:
        raise ValueError("Selected database files changed during preview")


def _verify_semantic_preview(container: str, baseline: Path) -> None:
    selected_its = subprocess.run([
        "docker", "exec", container, "python", "-c", _HTTP_FETCH,
        "/api/scenarios/battleground?"
        "army_points=300&collection=its-18",
    ], capture_output=True, text=True, check=True)
    its_status, _its_headers, its_body = json.loads(selected_its.stdout)
    its_payload = json.loads(base64.b64decode(its_body))
    if (
        its_status != 200
        or its_payload.get("publication", {}).get("collection_id") != "its-18"
        or its_payload.get("selected_army_points") != 300
    ):
        raise ValueError("Docker preview did not select ITS-owned Battleground")

    def transport(environ, start_response):
        path = environ["PATH_INFO"]
        if environ.get("QUERY_STRING"):
            path += "?" + environ["QUERY_STRING"]
        result = subprocess.run([
            "docker", "exec", container, "python", "-c", _HTTP_FETCH, path,
        ], capture_output=True, text=True, check=True)
        status, headers, body = json.loads(result.stdout)
        start_response(f"{status} Preview", headers)
        return [base64.b64decode(body)]

    expected = json.loads(baseline.read_text(encoding="utf-8"))
    observed = capture(
        transport, paths=tuple(probe["path"] for probe in expected["probes"]),
        route_aliases={"/static/restrictions-reference.json": "/api/restrictions/chart"},
    )
    print(f"Container semantic parity PASS: {check(expected, observed)} pinned paths")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "data/generated")
    parser.add_argument("--tag", default="infinity-db:preview-local")
    parser.add_argument("--baseline", type=Path, default=CURRENT_BASELINE)
    parser.add_argument(
        "--capacity-output", type=Path,
        help="Run the isolated Unit Explorer capacity workload instead of parity checks.",
    )
    args = parser.parse_args(argv)
    if not args.tag.startswith("infinity-db:preview-"):
        parser.error("Disposable preview tag must start with infinity-db:preview-")
    try:
        preview_image(
            args.source_dir, args.tag, args.baseline, capacity_output=args.capacity_output,
        )
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
