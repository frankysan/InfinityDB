#!/usr/bin/env python3
"""Build representative artifacts and record their SHA-256 identities.

The default v2 format measures application-only export, matching complete
runtime builds. Explicit --legacy-paired preserves the v1 artifact inventory
and hashes a disposable raw SQLite sibling for historical comparisons.
Neither format requires retaining development archives.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
import zlib
from contextlib import closing
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
FORMAT_VERSION = 2
LEGACY_FORMAT_VERSION = 1
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


def _canonical_fixture_copy(source: Path, destination: Path) -> Path:
    """Stabilize tracked JSON fixture newlines without touching the worktree.

    Git's LF attribute is the intended repository format. Existing Windows
    checkouts can nevertheless retain pre-attribute CRLF bytes; this disposable
    fixture must not treat such checkout differences as new Army source revisions.
    Real downloaded Army archives are not rewritten by this helper.
    """
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = path.read_bytes()
        if path.suffix.lower() == ".json":
            raw = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        target.write_bytes(raw)
    return destination


def _sqlite_diagnostics(path: Path) -> dict[str, Any]:
    """Record on-disk header and canonical relational content independently."""
    data = path.read_bytes()
    if not data.startswith(b"SQLite format 3\x00"):
        raise ValueError(f"Invalid SQLite diagnostic input: {path}")
    neutral_header = data[:96] + b"\x00" * 4 + data[100:]
    with closing(
        sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    ) as database:
        tables = [
            str(row[0])
            for row in database.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        fingerprints: dict[str, str] = {}
        for name in tables:
            escaped = name.replace('"', '""')
            serialized = []
            for row in database.execute(f'SELECT * FROM "{escaped}"'):
                fields = [
                    {"blob": value.hex()} if isinstance(value, bytes) else value
                    for value in row
                ]
                serialized.append(json.dumps(
                    fields, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":"), allow_nan=False,
                ))
            serialized.sort()
            fingerprints[name] = hashlib.sha256(
                ("\n".join(serialized)).encode("utf-8")
            ).hexdigest()
    return {
        "sqliteVersion": sqlite3.sqlite_version,
        "headerWriterVersion": int.from_bytes(data[96:100], "big"),
        "headerPageCount": int.from_bytes(data[28:32], "big"),
        "headerNeutralizedSha256": hashlib.sha256(neutral_header).hexdigest(),
        "tableDigests": fingerprints,
    }


def _zip_diagnostics(path: Path) -> dict[str, Any]:
    """Distinguish changed archive members from changed compressed bytes."""
    with zipfile.ZipFile(path) as archive:
        fingerprints = {}
        for item in archive.infolist():
            digest = hashlib.sha256()
            with archive.open(item) as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            fingerprints[item.filename] = {
                "sha256": digest.hexdigest(),
                "size": item.file_size,
                "crc": item.CRC,
                "compressSize": item.compress_size,
                "compression": item.compress_type,
            }
    return {"members": dict(sorted(fingerprints.items()))}


def build_manifest(
    project_root: Path, *, legacy_paired: bool = False,
    diagnostics_output: Path | None = None,
) -> dict[str, Any]:
    source_fixture = project_root / "tests" / "fixtures" / "deployment-smoke"
    with tempfile.TemporaryDirectory(prefix="infinitydb-determinism-") as temporary:
        root = Path(temporary)
        fixture = _canonical_fixture_copy(source_fixture, root / "fixture")
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
        _run(
            project_root, "-m", "infinity_db", "export",
            str(generated / "normalized.json"), str(generated / "army.db"),
            *(("--with-raw",) if legacy_paired else ()),
        )
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
                *(("army.raw.db",) if legacy_paired else ()),
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

        if diagnostics_output is not None:
            diagnostics = {
                "sqlite": {
                    name: _sqlite_diagnostics(generated / name)
                    for name in ("army.db", "rules_n5.db", "its_18.db")
                },
                "archives": {
                    "snapshot.zip": _zip_diagnostics(snapshot),
                    "work.zip": _zip_diagnostics(work_archive),
                },
            }
            write_json_lf(diagnostics_output, diagnostics, sort_keys=True)

        return {
            "format": FORMAT,
            "formatVersion": (
                LEGACY_FORMAT_VERSION if legacy_paired else FORMAT_VERSION
            ),
            "artifacts": dict(sorted(artifacts.items())),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--legacy-paired", action="store_true",
        help="Generate the original v1 manifest, including a disposable raw archive",
    )
    parser.add_argument(
        "--diagnostics-output", type=Path,
        help="Optional SQLite table/header and ZIP member diagnostics in local/",
    )
    args = parser.parse_args(argv)

    project_root = Path(__file__).resolve().parents[1]
    print(
        f"Determinism environment: Python {sys.version_info.major}."
        f"{sys.version_info.minor}.{sys.version_info.micro}, "
        f"SQLite {sqlite3.sqlite_version}, zlib {zlib.ZLIB_VERSION} "
        f"(runtime {zlib.ZLIB_RUNTIME_VERSION})"
    )
    manifest = build_manifest(
        project_root, legacy_paired=args.legacy_paired,
        diagnostics_output=args.diagnostics_output,
    )
    write_json_lf(args.output, manifest, sort_keys=True)
    print(f"Determinism manifest: {args.output}")
    for name, digest in manifest["artifacts"].items():
        print(f"{digest}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
