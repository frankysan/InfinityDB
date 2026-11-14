"""Exclusive, canonical JSON receipts for optional browser verification commands.

Existing explicit output paths remain accepted, but prior runs are never
overwritten. The acceptance result is owned by each caller, not this helper.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def require_new_browser_report(parser: argparse.ArgumentParser, output: Path | None) -> None:
    """Refuse occupied report names before browser startup."""
    if output is not None and (output.exists() or output.is_symlink()):
        parser.exit(1, f"Browser report already exists: {output}\n")


def write_browser_report(
    parser: argparse.ArgumentParser, output: Path | None, report: dict[str, Any],
) -> None:
    """Write the unchanged sorted, indented JSON format using exclusive creation."""
    if output is None:
        return
    require_new_browser_report(parser, output)
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(report, sort_keys=True, indent=2) + "\n")
    except OSError as exc:
        parser.exit(1, f"Browser report could not be created: {output}: {exc}\n")
