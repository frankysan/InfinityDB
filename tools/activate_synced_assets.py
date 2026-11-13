"""Explicit, non-destructive activation of Syncthing-staged InfinityDB inputs.

Syncthing stages files outside the checkout. This tool never synchronizes Git,
and it does not modify a checkout unless activate --apply is supplied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from infinity_db.snapshot_provenance import (
    SnapshotProvenanceError,
    validate_snapshot_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
STAGING_ROOT = Path.home() / "syncthing" / "infinitydb"
LAYOUT_CONFIG = REPO_ROOT / "config/operations/synced-asset-layouts.json"


class ActivationError(ValueError):
    """Unsafe input, missing asset, hash mismatch, or destination conflict."""


@dataclass(frozen=True)
class Route:
    staging: PurePosixPath
    destination: PurePosixPath


@dataclass(frozen=True)
class Layout:
    manifest: Route
    archives: dict[str, Route]
    files: dict[str, str]


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


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ActivationError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _object(value: Any, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ActivationError(f"Expected configuration object with keys: {sorted(keys)}")
    return value


def _under(path: PurePosixPath, prefix: PurePosixPath) -> bool:
    return path.parts[:len(prefix.parts)] == prefix.parts


def _route(value: Any, *, source: str, destinations: tuple[str, ...]) -> Route:
    record = _object(value, {"staging", "destination"})
    if not all(isinstance(record[key], str) for key in record):
        raise ActivationError("Layout paths must be strings")
    staged, destination = _relative(record["staging"]), _relative(record["destination"])
    if not _under(staged, PurePosixPath(source)) or not any(
        _under(destination, PurePosixPath(prefix)) for prefix in destinations
    ):
        raise ActivationError("Layout route is outside its permitted source/destination family")
    return Route(staged, destination)


def _layouts(path: Path) -> dict[str, Layout]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, ValueError) as exc:
        raise ActivationError(f"Cannot load asset layouts: {exc}") from exc
    root = _object(document, {"format", "formatVersion", "layouts"})
    if (
        root["format"] != "InfinityDB staged asset layouts"
        or type(root["formatVersion"]) is not int or root["formatVersion"] != 1
    ):
        raise ActivationError("Unsupported asset layout format/version")
    definitions = _object(root["layouts"], {"legacy", "local"})
    layouts = {}
    for name, value in definitions.items():
        record = _object(value, {"manifest", "archives", "files"})
        archives = _object(record["archives"], {"army", "wiki", "symbols"})
        manifest = _route(
            record["manifest"], source="snapshots",
            destinations=("data/manifests/snapshots", "local/data/manifests/snapshots"),
        )
        files = _object(record["files"], {"data/pdf", "image_overrides"})
        for destination, staged in files.items():
            if not isinstance(staged, str):
                raise ActivationError("Layout paths must be strings")
            _route(
                {"staging": staged, "destination": destination},
                source="pdf" if destination == "data/pdf" else "image-overrides",
                destinations=(destination,),
            )
        layouts[name] = Layout(
            manifest,
            {kind: _route(
                route, source="wiki" if kind == "wiki" else "raw",
                destinations=("data/wiki", "local/data/wiki") if kind == "wiki"
                else ("data/raw", "local/data/raw"),
            ) for kind, route in archives.items()},
            files,
        )
    return layouts


def _source_for(root: Path, relative: str, mappings: dict[str, str]) -> Path:
    rel = _relative(relative)
    for destination_prefix, staging_prefix in mappings.items():
        base = PurePosixPath(destination_prefix)
        if rel.parts[: len(base.parts)] == base.parts and len(rel.parts) > len(base.parts):
            return root / staging_prefix / Path(*rel.parts[len(base.parts) :])
    raise ActivationError(f"Not a supported synchronized path: {relative}")


def _without_links(path: Path, root: Path) -> Path:
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
    return path


def _file_without_links(path: Path, root: Path) -> Path:
    _without_links(path, root)
    if not path.is_file():
        raise ActivationError(f"Staged file missing: {path}")
    return path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _snapshot_name(name: str) -> str:
    if name.endswith(".json"):
        name = name[:-5]
    if len(_relative(name).parts) != 1:
        raise ActivationError("Snapshot name must be a manifest basename")
    return name


def _snapshot_names(names: list[str]) -> list[str]:
    normalized = [_snapshot_name(name) for name in names]
    if len({name.casefold() for name in normalized}) != len(normalized):
        raise ActivationError("Duplicate or case-colliding snapshot names")
    return normalized


def _available(staging_root: Path, layout: Layout) -> list[str]:
    folder = _without_links(staging_root / layout.manifest.staging, staging_root)
    if not folder.is_dir():
        raise ActivationError(f"Snapshot staging directory missing: {folder}")
    paths = sorted(path for path in folder.iterdir() if path.suffix.casefold() == ".json")
    if any(path.suffix != ".json" for path in paths):
        raise ActivationError("Snapshot manifests must use the lowercase .json suffix")
    for path in paths:
        _file_without_links(path, staging_root)
    return _snapshot_names([path.stem for path in paths])


def _snapshot(
    name: str, staging_root: Path, layout: Layout, *, legacy: bool,
) -> list[tuple[str, Path, str]]:
    name = _snapshot_name(name)
    manifest_rel = (layout.manifest.destination / f"{name}.json").as_posix()
    manifest_file = _file_without_links(
        staging_root / layout.manifest.staging / f"{name}.json", staging_root
    )
    raw = manifest_file.read_bytes()
    try:
        manifest = json.loads(raw, object_pairs_hook=_unique_object)
        validate_snapshot_manifest(manifest)
        archive = manifest["snapshot"]["archive"]
        route = layout.archives[manifest["snapshot"]["type"]]
    except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
        raise ActivationError(f"Invalid snapshot manifest: {name}") from exc
    basename = _relative(archive["name"])
    if len(basename.parts) != 1 or basename.suffix != ".zip" or basename.stem != name:
        raise ActivationError(f"Invalid archive filename: {archive['name']}")
    if legacy:
        archive_path = _relative(archive.get("path", ""))
        if not _under(archive_path, route.destination) or archive_path.name != basename.name:
            raise ActivationError(f"Unexpected legacy archive location: {archive_path}")
        tail = archive_path.relative_to(route.destination)
    else:
        # Producer-relative paths are informational in the explicitly selected layout.
        if "path" in archive:
            _relative(archive["path"])
        tail = basename
    archive_rel = (route.destination / tail).as_posix()
    staged_archive = _file_without_links(
        staging_root / route.staging / tail, staging_root
    )
    validate_snapshot_manifest(manifest, archive=staged_archive)
    if manifest_file.read_bytes() != raw:
        raise ActivationError(f"Snapshot manifest changed during verification: {name}")
    digest = archive["sha256"]
    return [
        (archive_rel, staged_archive, digest),
        (manifest_rel, manifest_file, hashlib.sha256(raw).hexdigest()),
    ]


def _destination(repo_root: Path, relative: str, *, apply: bool) -> Path:
    if repo_root.is_symlink() or not repo_root.is_dir():
        raise ActivationError(f"Checkout root missing or a symlink: {repo_root}")
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
    staging_root: Path,
    mode: str,
    apply: bool,
) -> str:
    _file_without_links(source, staging_root)
    if _sha256(source) != digest:
        raise ActivationError(f"Source changed before activation: {relative}")
    dest = _destination(repo_root, relative, apply=apply)
    if dest.is_symlink():
        # Windows may expose a stored absolute target with a different path spelling
        # (for example, a device prefix). Compare canonical targets, not link text.
        if mode == "symlink" and dest.resolve(strict=True) == source.resolve(strict=True):
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
    for subparser in subs.choices.values():
        subparser.add_argument(
            "--layout", choices=("legacy", "local"), default="legacy",
            help="Explicit snapshot layout; legacy remains the default.",
        )
    return parser


def main(
    argv: list[str] | None = None,
    *,
    staging_root: Path | None = None,
    repo_root: Path = REPO_ROOT,
    layout_config: Path = LAYOUT_CONFIG,
) -> int:
    args = _parser().parse_args(argv)
    if staging_root is None:
        configured_root = os.environ.get("INFINITYDB_SYNC_STAGING_ROOT")
        staging_root = Path(configured_root) if configured_root else STAGING_ROOT
    try:
        layout = _layouts(layout_config)[args.layout]
        if args.action == "list":
            for name in _available(staging_root, layout):
                print(name)
            return 0
        if args.action == "verify":
            if args.snapshot:
                names = _snapshot_names(args.snapshot)
            else:
                names = _available(staging_root, layout)
            if not names:
                raise ActivationError("No snapshot manifests available")
            for name in names:
                items = _snapshot(name, staging_root, layout, legacy=args.layout == "legacy")
                print(f"verified {items[0][0]} SHA-256={items[0][2]}")
            return 0
        if args.snapshot:
            items = _snapshot(args.snapshot, staging_root, layout, legacy=args.layout == "legacy")
        else:
            rel = _relative(args.file)
            is_pdf = rel.parts[:2] == ("data", "pdf") and len(rel.parts) > 2
            is_override = len(rel.parts) > 1 and rel.parts[0] == "image_overrides"
            if not (is_pdf or is_override):
                raise ActivationError(
                    "Direct file activation is limited to PDFs and image overrides"
                )
            source = _file_without_links(
                _source_for(staging_root, args.file, layout.files), staging_root
            )
            items = [(args.file, source, _sha256(source))]
            print("Note: this file has no snapshot provenance pin; SHA-256 measured only.")
        # Preflight the entire selection before modifying the checkout.
        for relative, source, digest in items:
            _activate_one(
                repo_root, relative, source, digest, staging_root=staging_root,
                mode=args.mode, apply=False,
            )
        for relative, source, digest in items:
            status = _activate_one(
                repo_root, relative, source, digest, staging_root=staging_root,
                mode=args.mode, apply=args.apply,
            )
            print(f"{status}: {relative} ({args.mode})")
        return 0
    except (ActivationError, OSError, SnapshotProvenanceError, zipfile.BadZipFile) as exc:
        print(f"Activation refused: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
