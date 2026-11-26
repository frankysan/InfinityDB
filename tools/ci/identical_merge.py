"""Plan a main-push CI reuse from the actual merged PR, or run full checks."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from tools.ci.prepare_release_ci_evidence import (
    ReleaseEvidenceError,
    collect_identical_merge_evidence,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--github-output", required=True, type=Path)
    args = parser.parse_args(argv)
    reuse = False
    try:
        evidence = collect_identical_merge_evidence(
            args.repository, args.commit, token=os.environ.get("GH_TOKEN"),
        )
    except (ReleaseEvidenceError, OSError, ValueError) as exc:
        print(f"Identical-tree reuse unavailable; run fresh validation: {exc}")
    else:
        merge = evidence["identical_merge"]
        print(f"Verified identical merge: {merge}")
        for run in evidence["workflows"]:
            print(f"{run['workflow']}: {run['head_sha']} {run['url']}")
        reuse = True
    with args.github_output.open("a", encoding="utf-8") as output:
        output.write(f"reuse={str(reuse).lower()}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
