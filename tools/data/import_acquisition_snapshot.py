"""Import one immutable snapshot pair from a sibling acquisition repository.

The producer and InfinityDB remain separate Git repositories; only ignored
source bytes are copied. No source acquisition, fallback search or deletion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

from infinity_db.snapshot_provenance import validate_snapshot_manifest

ROOT = Path(__file__).resolve().parents[2]
SOURCE_FAMILIES = {
    "army": ("InfinityDB-army-acquisition", "raw/army", "raw/army", "JSON "),
    "wiki": ("InfinityDB-wiki-acquisition", "wiki", "wiki", ("WIKI-", "HUMAN-SPHERE ")),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _regular(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Source must be a regular file: {path}")


def import_snapshot(root: Path, family: str, name: str, *, apply: bool) -> str:
    if family not in SOURCE_FAMILIES:
        raise ValueError(f"Unknown source family: {family}")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]{1,130}", name):
        raise ValueError("Expected an unqualified snapshot archive stem")
    repository, incoming, destination, prefix = SOURCE_FAMILIES[family]
    if not name.startswith(prefix):
        raise ValueError(f"Unexpected {family} snapshot name: {name}")
    producer = root.parent / repository / "local/data"
    archive = producer / incoming / f"{name}.zip"
    manifest = producer / "manifests/snapshots" / f"{name}.json"
    for source in (archive, manifest):
        _regular(source)
    document = json.loads(manifest.read_text(encoding="utf-8"))
    if document.get("formatVersion") != 3 or document.get("snapshot", {}).get("type") != family:
        raise ValueError("Snapshot provenance must be version 3 and match its family")
    if document["snapshot"]["archive"]["name"] != archive.name:
        raise ValueError("Snapshot archive and manifest names differ")
    validate_snapshot_manifest(document, archive=archive)

    targets = (
        (archive, root / "local/data" / destination / archive.name),
        (manifest, root / "local/data/manifests/snapshots" / manifest.name),
    )
    for source, target in targets:
        if target.is_symlink() or (target.exists() and (
            not target.is_file() or _sha256(target) != _sha256(source)
        )):
            raise ValueError(f"Existing destination conflicts: {target}")
    pending = 0
    for source, target in targets:
        if target.exists():
            continue
        pending += 1
        if not apply:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(prefix=".acquisition-transfer-", dir=target.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(fd, "wb") as output, source.open("rb") as input_stream:
                shutil.copyfileobj(input_stream, output, length=1024 * 1024)
            if _sha256(temporary) != _sha256(source):
                raise ValueError(f"Source changed during transfer: {source}")
            os.link(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    return f"{family}: {name}: {'copied' if apply else 'would copy'} {pending} files"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=tuple(SOURCE_FAMILIES), required=True)
    parser.add_argument("--snapshot", required=True, help="Exact ZIP stem, without extension")
    parser.add_argument("--apply", action="store_true", help="Copy only absent destination files")
    args = parser.parse_args(argv)
    try:
        print(import_snapshot(ROOT, args.family, args.snapshot, apply=args.apply))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Snapshot import refused: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
