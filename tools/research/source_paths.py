"""Resolve an explicitly selected physical PDF without changing its source label.

Maintained research-only path policy; no source discovery, writes or runtime
dependency. Source owners retain their original labels and SHA-256 pins.
"""
from __future__ import annotations

import hashlib
import json
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any

POLICY = Path(__file__).resolve().parents[2] / "config/operations/research-source-layouts.json"


class SourcePathError(ValueError):
    """Unsafe binding, unsupported policy, unavailable source or hash mismatch."""


def _relative(value: Any) -> PurePosixPath:
    if (
        not isinstance(value, str) or not value or "\\" in value or ":" in value
        or any(part in {"", ".", "..", ".stfolder", ".stversions", ".stignore"}
               for part in value.split("/"))
    ):
        raise SourcePathError("Source binding requires a normalized relative POSIX path")
    return PurePosixPath(value)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise SourcePathError(f"Duplicate source policy key: {key}")
        result[key] = value
    return result


def _selected_prefix(layout: str, policy: Path) -> PurePosixPath:
    try:
        record = json.loads(policy.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, ValueError) as exc:
        raise SourcePathError("Cannot load research source layout policy") from exc
    if (
        not isinstance(record, dict)
        or set(record) != {"format", "formatVersion", "scope", "sourceLabelPrefix", "layouts"}
        or record["format"] != "InfinityDB research source layouts"
        or type(record["formatVersion"]) is not int or record["formatVersion"] != 1
        or record["scope"] != "explicit-read-only-pdf-binding-no-source-migration"
        or record["sourceLabelPrefix"] != "data/pdf"
        or not isinstance(record["layouts"], dict)
        or set(record["layouts"]) != {"legacy", "local"}
    ):
        raise SourcePathError("Unsupported research source layout policy")
    for name, value in record["layouts"].items():
        prefix = _relative(value)
        permitted = PurePosixPath("data/pdf" if name == "legacy" else "local/data/pdf")
        if prefix != permitted:
            raise SourcePathError("Research source layout is outside its permitted PDF family")
    if not isinstance(layout, str) or layout not in record["layouts"]:
        raise SourcePathError(f"Unknown research source layout: {layout}")
    return _relative(record["layouts"][layout])


def pinned_pdf_path(
    root: Path, source_label: str, sha256: str, *,
    layout: str = "legacy", policy: Path = POLICY, missing_ok: bool = False,
) -> Path | None:
    """Read only the selected layout; never fall back to another existing root.

    ``source_label`` is unchanged provenance, not a physical-path suggestion.
    Missing historical inputs may remain explicitly not supplied, while unsafe
    or mismatched supplied inputs always fail. No directories are created.
    """
    label = _relative(source_label)
    if (
        label.parts[:2] != ("data", "pdf") or len(label.parts) < 3
        or label.suffix != ".pdf" or not isinstance(sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", sha256) is None
    ):
        raise SourcePathError("Expected a canonical PDF source label and lowercase SHA-256")
    selected = _selected_prefix(layout, policy) / label.relative_to("data/pdf")
    try:
        if root.is_symlink() or not root.is_dir():
            raise SourcePathError("Research source root is missing or a symlink")
        if getattr(root.lstat(), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise SourcePathError("Research source root is a reparse point")
    except OSError as exc:
        raise SourcePathError("Cannot inspect research source root") from exc
    path = root
    for index, segment in enumerate(selected.parts):
        path /= segment
        try:
            if path.is_symlink():
                raise SourcePathError(f"Source binding contains a symlink: {source_label}")
            info = path.lstat()
        except FileNotFoundError as exc:
            if missing_ok:
                return None
            raise SourcePathError(f"Source unavailable in selected layout: {source_label}") from exc
        except OSError as exc:
            raise SourcePathError(f"Cannot inspect selected PDF: {source_label}") from exc
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            raise SourcePathError(f"Source binding contains a link/reparse point: {source_label}")
        if index < len(selected.parts) - 1 and not stat.S_ISDIR(info.st_mode):
            raise SourcePathError(f"Source binding parent is not a directory: {source_label}")
    if not stat.S_ISREG(info.st_mode):
        raise SourcePathError(f"Selected PDF is not a regular file: {source_label}")
    try:
        with path.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError as exc:
        raise SourcePathError(f"Cannot read selected PDF: {source_label}") from exc
    if actual != sha256:
        raise SourcePathError(f"Source hash mismatch: {source_label}")
    return path
