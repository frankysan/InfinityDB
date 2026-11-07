"""Run the portable cross-browser release cohort with an explicit browser engine.

Unlike the ordinary source suite, this opt-in runner requires Playwright and the
selected browser. A missing browser fails the job instead of being reported as a skip.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ENGINES = ("chromium", "firefox", "webkit", "msedge")
ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=ENGINES, required=True)
    args = parser.parse_args(argv)
    report = ROOT / "local/cross-browser-compatibility/junit.xml"
    report.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, INFINITYDB_CROSS_BROWSER_ENGINE=args.engine)
    print(f"Cross-browser release pilot: {args.engine}", flush=True)
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", "-q", "-s",
            "tests/test_cross_browser_compatibility.py",
            f"--junitxml={report.relative_to(ROOT).as_posix()}",
        ],
        cwd=ROOT, env=env, check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
