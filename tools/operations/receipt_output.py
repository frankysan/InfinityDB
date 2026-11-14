"""Preserve optional deployment and capacity report evidence.

An operator's chosen JSON receipt must never replace an earlier run or
a source report.  Operational status codes and summaries stay with callers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def require_new_receipt(output: Path | None) -> None:
    """Reject an occupied destination before network, subprocess or log work."""
    if output is not None and (output.exists() or output.is_symlink()):
        raise FileExistsError(f"Operational report already exists: {output}")


def write_new_json_receipt(output: Path, report: dict[str, Any]) -> None:
    """Create a new canonical JSON report exclusively; no existing bytes change."""
    require_new_receipt(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
