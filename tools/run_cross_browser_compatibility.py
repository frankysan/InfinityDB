"""Run the portable cross-browser release cohort with an explicit browser engine.

Unlike the ordinary source suite, this opt-in runner requires Playwright and the
selected browser. A missing browser fails the job instead of being reported as a skip.
JUnit, screenshots and traces belong to one new, revision-pinned local/ run.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ENGINES = ("chromium", "firefox", "webkit", "msedge")
ROOT = Path(__file__).resolve().parents[1]
REPORT_BASE = Path("local/validation/project-infrastructure/cross-browser")


def _checkout_revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=ROOT, capture_output=True, text=True, check=False, timeout=10,
    )
    revision = result.stdout.strip().lower()
    if result.returncode or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Cannot identify the exact Git revision for browser evidence")
    return revision[:12]


def _reserve_output_dir(engine: str, requested: Path | None = None) -> Path:
    if requested is None:
        run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        requested = REPORT_BASE / f"{run_id}-{_checkout_revision()}" / engine
    target = ROOT / requested
    # Only project-owned ignored validation output may be created. Reject
    # symlink escapes and reuse, rather than truncating earlier JUnit/traces.
    allowed = ROOT.resolve() / "local" / "validation"
    if not target.resolve().is_relative_to(allowed):
        raise ValueError("Cross-browser output must be beneath repository local/validation/")
    target.mkdir(parents=True, exist_ok=False)
    return target.resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=ENGINES, required=True)
    parser.add_argument(
        "--output-dir", type=Path,
        help="fresh report directory beneath local/validation/ (default: UTC run and Git SHA)",
    )
    args = parser.parse_args(argv)
    try:
        report_dir = _reserve_output_dir(args.engine, args.output_dir)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        parser.error(f"Cannot reserve cross-browser evidence directory: {exc}")
    report = report_dir / "junit.xml"
    relative_dir = report_dir.relative_to(ROOT.resolve()).as_posix()
    env = dict(
        os.environ,
        INFINITYDB_CROSS_BROWSER_ENGINE=args.engine,
        INFINITYDB_CROSS_BROWSER_ARTIFACT_DIR=relative_dir,
    )
    print(
        f"Cross-browser release pilot: {args.engine}; evidence: {relative_dir}",
        flush=True,
    )
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", "-q", "-s",
            "tests/test_cross_browser_compatibility.py",
            f"--junitxml={report.relative_to(ROOT.resolve()).as_posix()}",
        ],
        cwd=ROOT, env=env, check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
