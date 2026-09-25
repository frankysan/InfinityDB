#!/usr/bin/env python3
"""Build representative artifacts and record their SHA-256 identities."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from infinity_army_data.deterministic_io import write_json_lf

try:
    from tools.create_work_archive import create_work_archive
    from tools.snapshot_archive import create_timestamped_archive
except ImportError:  # pragma: no cover - direct script execution fallback
    from create_work_archive import create_work_archive
    from snapshot_archive import create_timestamped_archive

FORMAT = "InfinityDB cross-platform determinism manifest"
FORMAT_VERSION = 1
FIXED_ARCHIVE_TIME = datetime(2000, 1, 1, tzinfo=UTC)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(project_root: Path, *args: str) -> None:
    subprocess.run(
        [sys.executable, *args],
        cwd=project_root,
        check=True,
    )


def build_manifest(project_root: Path) -> dict[str, Any]:
    fixture = project_root / "tests" / "fixtures" / "deployment-smoke"
    with tempfile.TemporaryDirectory(prefix="infinitydb-determinism-") as temporary:
        root = Path(temporary)
        generated = root / "generated"
        generated.mkdir()

        _run(
            project_root,
            "-m",
            "infinity_db",
            "build",
            str(fixture),
            "--output-dir",
            str(generated),
            "--compact",
        )
        _run(
            project_root,
            "-m",
            "infinity_db",
            "build-rules",
            "--output",
            str(generated / "rules.db"),
        )

        fixture_files = sorted(path for path in fixture.rglob("*") if path.is_file())
        snapshot = create_timestamped_archive(
            fixture_files,
            root / "snapshots",
            prefix="FIXTURE",
            root=fixture,
            now=FIXED_ARCHIVE_TIME,
        )
        work_archive = create_work_archive(project_root, root / "work.zip")

        artifacts = {
            f"build/{name}": sha256_file(generated / name)
            for name in (
                "infinity.db",
                "infinity.raw.db",
                "master.json",
                "normalized-validation.json",
                "normalized.json",
                "rules.db",
            )
        }
        artifacts["archives/snapshot.zip"] = sha256_file(snapshot)
        artifacts["archives/work.zip"] = sha256_file(work_archive)

        static_root = project_root / "src" / "infinity_db" / "web" / "static"
        for name in ("symbol-inventory.json", "army-symbols.js", "unit-symbol-map.js"):
            artifacts[f"publication/{name}"] = sha256_file(static_root / name)

        return {
            "format": FORMAT,
            "formatVersion": FORMAT_VERSION,
            "artifacts": dict(sorted(artifacts.items())),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    project_root = Path(__file__).resolve().parents[1]
    manifest = build_manifest(project_root)
    write_json_lf(args.output, manifest, sort_keys=True)
    print(f"Determinism manifest: {args.output}")
    for name, digest in manifest["artifacts"].items():
        print(f"{digest}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
