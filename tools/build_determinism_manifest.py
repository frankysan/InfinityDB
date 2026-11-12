#!/usr/bin/env python3
"""Build representative artifacts and record their SHA-256 identities.

The raw SQLite hash deliberately measures the *standalone paired export*
contract, using a disposable temporary directory. It is not a retained
development input or an artifact produced by complete runtime builds.
"""

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
            "infinity_army_data",
            "build",
            str(fixture),
            "--output-dir",
            str(generated),
            "--compact",
        )
        _run(project_root, "-m", "infinity_db", "export",
             str(generated / "normalized.json"), str(generated / "army.db"))
        from infinity_db.curated import load_curated_directory
        from infinity_db.rules_database import export_rules_database

        export_rules_database(
            load_curated_directory(project_root / "data/curated/rules"),
            generated / "rules_n5.db",
        )
        from infinity_db.its_season_database import build_its_database

        build_its_database(
            project_root / "data/curated/rules/n5-its-season-18-2026.09.01.json",
            generated / "its_18.db",
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
                "army.db",
                "army.raw.db",
                "master.json",
                "normalized-validation.json",
                "normalized.json",
                "rules_n5.db",
                "its_18.db",
            )
        }
        artifacts["archives/snapshot.zip"] = sha256_file(snapshot)
        artifacts["archives/work.zip"] = sha256_file(work_archive)

        artifacts["publication/symbol-publication.json"] = sha256_file(
            project_root / "data" / "manifests" / "symbol-publication.json"
        )
        # Hash reviewed, source-derived citation meaning without producing
        # the retired loose JSON release artifact.
        from infinity_db.build_provenance import canonical_bytes
        from infinity_db.weapon_profile_builder import build_publication

        reviewed = build_publication(
            project_root / "data/generated/army.db",
            project_root / "data/generated/rules_n5.db",
            project_root / "data/curated/weapon-shared-effect-reviews.json",
        )
        artifacts["reviewed/weapon-profile-citations"] = hashlib.sha256(
            canonical_bytes(reviewed)
        ).hexdigest()

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
