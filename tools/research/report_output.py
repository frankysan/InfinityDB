"""Fail closed on collisions for source-audit run receipts.

The audit's source files and reviewed tracked inputs are independent read-only
inputs, never destinations.  JSON and Markdown keep their existing serializers.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def require_new_audit_outputs(
    parser: argparse.ArgumentParser, *paths: Path | None,
) -> None:
    """Check all requested output paths before reading PDFs or saved Wiki inputs."""
    outputs = [path for path in paths if path is not None]
    seen: set[str] = set()
    for path in outputs:
        try:
            normalized = os.path.normcase(str(path.resolve(strict=False)))
        except OSError as exc:
            parser.exit(1, f"Audit report output: cannot resolve {path}: {exc}\n")
        if normalized in seen:
            parser.exit(1, f"Audit report output: duplicate destination: {path}\n")
        seen.add(normalized)
        if path.exists() or path.is_symlink():
            parser.exit(1, f"Audit report output: already exists: {path}\n")


def write_audit_text_or_exit(
    parser: argparse.ArgumentParser, path: Path, content: str,
) -> None:
    """Exclusively create an unchanged UTF-8/LF audit report or fail cleanly."""
    try:
        require_new_audit_outputs(parser, path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    except OSError as exc:
        parser.exit(1, f"Audit report output: {exc}\n")
