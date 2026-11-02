"""Explicit, non-destructive activation of Syncthing-staged InfinityDB inputs.

Syncthing stages files outside the checkout. This tool never synchronizes Git,
and it does not modify a checkout unless activate --apply is supplied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parents[1]
STAGING_ROOT = Path.home() / "syncthing" / "infinitydb"
MAPPINGS = {
    "data/raw": "raw",
    "data/wiki": "wiki",
    "data/pdf": "pdf",
    "data/manifests/snapshots": "snapshots",
    "image_overrides": "image_overrides",
}
UNPINNED_PREFIXES = ("data/pdf", "image_overrides")
SHA256_RE = re.compile(r"[a-f0-9]{64}\Z")


class ActivationError(ValueError):
    """Unsafe input, missing asset, hash mismatch, or destination conflict."""


def _relative(value: str) -> PurePosixPath:
    if (
        not value
        or "\\" in value
        or ":" in value
        or value.startswith("/")
        or "//" in value
    ):
        raise ActivationError(f"Invalid relative path: {value!r}")
    parts = value.split("/")
    if any(part in ("", ".", "..", ".stfolder", ".stversions", ".stignore") for part in parts):
        raise ActivationError(f"Invalid relative path: {value!r}")
    return PurePosixPath(*parts)


def _source_for(root: Path, relative: str) -> Path:
    rel = _relative(relative)
    for destination_prefix, staging_prefix in MAPPINGS.items():
        base = PurePosixPath(destination_prefix)
        if rel.parts[: len(base.parts)] == base.parts and len(rel.parts) > len(base.parts):
            return root / staging_prefix / Path(*rel.parts[len(base.parts) :])
    raise ActivationError(f"Not a supported synchronized path: {relative}")


def _file_without_links(path: Path, root: Path) -> Path:
    """Reject symlinks anywhere between the staging root and selected file."""
    if root.is_symlink() or not root.is_dir():
        raise ActivationError(f"Staging root missing or a symlink: {root}")
    try:
        parts = path.relative_to(root).parts
    except ValueError as exc:
        raise ActivationError("Source is outside staging root") from exc
    current = root
    for part in parts:
        current /= part
        if current.is_symlink():
            raise ActivationError(f"Staged symlink not permitted: {current}")
    if not path.is_file():
        raise ActivationError(f"Staged file missing: {path}")
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _snapshot(
    name: str, staging_root: Path
) -> list[tuple[str, Path, str]]:
    if name.endswith(".json"):
        name = name[:-5]
    if not name or "/" in name or "\\" in name:
        raise ActivationError("Snapshot name must be a manifest basename")
    manifest_rel = f"data/manifests/snapshots/{name}.json"
    manifest_file = _file_without_links(
        _source_for(staging_root, manifest_rel), staging_root
    )
    raw = manifest_file.read_bytes()
    try:
        manifest = json.loads(raw)
        archive = manifest["snapshot"]["archive"]
        archive_rel = archive["path"]
        digest = archive["sha256"]
    except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
        raise ActivationError(f"Invalid snapshot manifest: {name}") from exc
    if manifest.get("format") != "InfinityDB snapshot provenance":
        raise ActivationError(f"Unrecognized snapshot provenance: {name}")
    if not isinstance(archive_rel, str) or not isinstance(digest, str):
        raise ActivationError(f"Invalid archive identity: {name}")
    archive_path = _relative(archive_rel)
    if archive_path.parts[0:2] not in (("data", "raw"), ("data", "wiki")):
        raise ActivationError(f"Unexpected archive location: {archive_rel}")
    if archive_path.suffix != ".zip" or archive.get("name") != archive_path.name:
        raise ActivationError(f"Invalid archive filename: {archive_rel}")
    if SHA256_RE.fullmatch(digest) is None:
        raise ActivationError(f"Invalid archive SHA-256: {name}")
    staged_archive = _file_without_links(
        _source_for(staging_root, archive_rel), staging_root
    )
    actual = _sha256(staged_archive)
    if actual != digest:
        raise ActivationError(
            f"Archive hash mismatch: {archive_rel} (expected {digest}, got {actual})"
        )
    return [
        (archive_rel, staged_archive, digest),
        (manifest_rel, manifest_file, hashlib.sha256(raw).hexdigest()),
    ]


def _destination(repo_root: Path, relative: str, *, apply: bool) -> Path:
    dest = repo_root
    for segment in _relative(relative).parts[:-1]:
        dest /= segment
        if dest.is_symlink() or (dest.exists() and not dest.is_dir()):
            raise ActivationError(f"Unsafe destination directory: {dest}")
        if apply:
            dest.mkdir(exist_ok=True)
    return dest / _relative(relative).name


def _activate_one(
    repo_root: Path,
    relative: str,
    source: Path,
    digest: str,
    *,
    mode: str,
    apply: bool,
) -> str:
    dest = _destination(repo_root, relative, apply=apply)
    if dest.is_symlink():
        if mode == "symlink" and dest.readlink() == source.absolute():
            return "unchanged"
        raise ActivationError(f"Existing destination symlink differs: {relative}")
    if dest.exists():
        if not dest.is_file() or _sha256(dest) != digest:
            raise ActivationError(f"Existing destination differs: {relative}")
        return "unchanged"
    if not apply:
        return "planned"
    if mode == "symlink":
        try:
            dest.symlink_to(source.absolute())
        except FileExistsError as exc:
            raise ActivationError(f"Destination appeared during activation: {relative}") from exc
    else:
        fd, temp_name = tempfile.mkstemp(prefix=".syncthing-activate-", dir=dest.parent)
        temporary = Path(temp_name)
        try:
            with os.fdopen(fd, "wb") as output, source.open("rb") as input_file:
                shutil.copyfileobj(input_file, output, length=1024 * 1024)
            if _sha256(temporary) != digest:
                raise ActivationError(f"Source changed while copying: {relative}")
            try:
                os.link(temporary, dest)  # Atomic, fails rather than overwriting.
            except FileExistsError as exc:
                raise ActivationError(
                    f"Destination appeared during activation: {relative}"
                ) from exc
        finally:
            temporary.unlink(missing_ok=True)
    return "activated"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="action", required=True)
    subs.add_parser("list", help="List snapshot provenance available in staging.")
    verify = subs.add_parser("verify", help="Verify pinned snapshot archive SHA-256.")
    verify.add_argument("--snapshot", action="append", help="Snapshot manifest basename.")
    activate = subs.add_parser("activate", help="Preview or activate selected assets.")
    choice = activate.add_mutually_exclusive_group(required=True)
    choice.add_argument(
        "--snapshot", help="Snapshot manifest basename (activates archive and manifest)."
    )
    choice.add_argument(
        "--file",
        help="Repository-relative path under data/pdf/ or image_overrides/ (unpinned).",
    )
    activate.add_argument("--mode", choices=("copy", "symlink"), default="copy")
    activate.add_argument("--apply", action="store_true", help="Perform checkout writes.")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    staging_root: Path = STAGING_ROOT,
    repo_root: Path = REPO_ROOT,
) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.action == "list":
            folder = staging_root / "snapshots"
            if folder.is_symlink() or not folder.is_dir():
                raise ActivationError(f"Snapshot staging directory missing: {folder}")
            for path in sorted(folder.glob("*.json")):
                _file_without_links(path, staging_root)
                print(path.stem)
            return 0
        if args.action == "verify":
            folder = staging_root / "snapshots"
            if args.snapshot:
                names = args.snapshot
            else:
                if not folder.is_dir() or folder.is_symlink():
                    raise ActivationError(f"Snapshot staging directory missing: {folder}")
                names = [file.stem for file in sorted(folder.glob("*.json"))]
            if not names:
                raise ActivationError("No snapshot manifests available")
            for name in names:
                items = _snapshot(name, staging_root)
                print(f"verified {items[0][0]} SHA-256={items[0][2]}")
            return 0
        if args.snapshot:
            items = _snapshot(args.snapshot, staging_root)
        else:
            rel = _relative(args.file)
            is_pdf = rel.parts[:2] == ("data", "pdf") and len(rel.parts) > 2
            is_override = len(rel.parts) > 1 and rel.parts[0] == "image_overrides"
            if not (is_pdf or is_override):
                raise ActivationError(
                    "Direct file activation is limited to PDFs and image overrides"
                )
            source = _file_without_links(_source_for(staging_root, args.file), staging_root)
            items = [(args.file, source, _sha256(source))]
            print("Note: this file has no snapshot provenance pin; SHA-256 measured only.")
        # Preflight the entire selection before modifying the checkout.
        for relative, source, digest in items:
            _activate_one(repo_root, relative, source, digest, mode=args.mode, apply=False)
        for relative, source, digest in items:
            status = _activate_one(
                repo_root, relative, source, digest, mode=args.mode, apply=args.apply
            )
            print(f"{status}: {relative} ({args.mode})")
        return 0
    except (ActivationError, OSError) as exc:
        print(f"Activation refused: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
