"""Copy selected ignored legacy source families to local/data without deleting originals."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _regular_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Not a regular source file: {path}")


def candidates(root: Path, family: str) -> tuple[list[tuple[Path, Path, str]], int]:
    """Enumerate only the reviewed legacy immutable inputs for one family."""
    if family == "army":
        source_dir, destination_dir = root / "data/raw", root / "local/data/raw/army"
        archives = sorted(source_dir.glob("JSON *.zip"))
    elif family == "wiki":
        source_dir, destination_dir = root / "data/wiki", root / "local/data/wiki"
        archives = sorted(
            item for item in source_dir.glob("*.zip")
            if item.name.startswith(("WIKI-", "HUMAN-SPHERE "))
        )
    elif family == "symbols":
        source_dir = root / "data/raw/symbols"
        destination_dir = root / "local/data/raw/symbols"
        archives = sorted(source_dir.glob("SYMBOLS *.zip"))
    elif family == "pdf":
        source_dir, destination_dir = root / "data/pdf", root / "local/data/pdf"
        archives = sorted(source_dir.rglob("*.pdf"))
    else:
        raise ValueError(f"Unknown source family: {family}")
    if not archives:
        raise ValueError(f"No sources found for {family}")

    entries: list[tuple[Path, Path, str]] = []
    missing_manifests = 0
    for archive in archives:
        _regular_file(archive)
        relative = archive.relative_to(source_dir)
        digest = sha256_file(archive)
        entries.append((archive, destination_dir / relative, digest))
        if family == "pdf":
            continue
        manifest = root / "data/manifests/snapshots" / f"{archive.stem}.json"
        if not manifest.exists() and not manifest.is_symlink():
            missing_manifests += 1
            continue
        _regular_file(manifest)
        record = json.loads(manifest.read_text(encoding="utf-8"))
        snapshot = record["snapshot"]
        archive_info = snapshot["archive"]
        expected_type = "wiki" if family == "wiki" else family
        if (
            snapshot["type"] != expected_type
            or archive_info["name"] != archive.name
            or archive_info["sha256"] != digest
        ):
            raise ValueError(f"Archive and provenance disagree: {archive.name}")
        entries.append((
            manifest,
            root / "local/data/manifests/snapshots" / manifest.name,
            sha256_file(manifest),
        ))
    return entries, missing_manifests


def copy_family(root: Path, family: str, *, apply: bool) -> tuple[int, int, int]:
    entries, missing = candidates(root, family)
    for _, destination, digest in entries:
        if destination.is_symlink() or (
            destination.exists() and (
                not destination.is_file() or sha256_file(destination) != digest
            )
        ):
            raise ValueError(f"Conflicting destination: {destination}")

    copied = 0
    for source, destination, digest in entries:
        if destination.exists() or not apply:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(prefix=".local-source-", dir=destination.parent)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(fd, "wb") as output, source.open("rb") as input_stream:
                shutil.copyfileobj(input_stream, output, length=1024 * 1024)
            if sha256_file(temporary) != digest or sha256_file(source) != digest:
                raise ValueError(f"Source changed during copy: {source}")
            os.link(temporary, destination)
            copied += 1
        finally:
            temporary.unlink(missing_ok=True)
    pending = sum(not destination.exists() for _, destination, _ in entries)
    action = "copied" if apply else "would copy"
    print(
        f"{family}: {len(entries)} hash-checked files; "
        f"{action} {copied if apply else pending}; "
        f"{missing} archive(s) without a matching manifest"
    )
    return len(entries), copied, missing


def retire_family(root: Path, family: str, *, apply: bool) -> int:
    """Remove legacy duplicates only when every selected local copy matches."""
    if family == "pdf":
        raise ValueError("PDF retirement requires separate physical-reader cutover")
    entries, missing = candidates(root, family)
    for source, destination, digest in entries:
        _regular_file(source)
        if (
            destination.is_symlink()
            or not destination.is_file()
            or sha256_file(destination) != digest
            or sha256_file(source) != digest
        ):
            raise ValueError(f"Unverified destination; original retained: {source}")
    if apply:
        for source, _, _ in entries:
            source.unlink()
    print(
        f"{family}: {len(entries)} verified duplicate files; "
        f"{'retired' if apply else 'would retire'} {len(entries)}; "
        f"{missing} archive(s) without a matching manifest"
    )
    return len(entries)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", required=True, choices=("army", "wiki", "symbols", "pdf"))
    parser.add_argument(
        "--apply", action="store_true", help="Perform the selected copy or duplicate retirement"
    )
    parser.add_argument(
        "--retire-duplicates", action="store_true",
        help="Retire already-copied legacy Army/Wiki/symbol ZIP and manifest files",
    )
    args = parser.parse_args(argv)
    try:
        if args.retire_duplicates:
            retire_family(ROOT, args.family, apply=args.apply)
        else:
            copy_family(ROOT, args.family, apply=args.apply)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Source copy refused: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
