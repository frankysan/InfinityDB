"""Shared content identity for the selected runtime SQLite database set."""

from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256


def database_set_snapshot_revision(fingerprints: Mapping[str, str]) -> str:
    """Bind cache identity to sorted active filenames and exact database bytes."""
    if not fingerprints:
        raise ValueError("Runtime database fingerprints are required")
    value = json.dumps(sorted(fingerprints.items()), separators=(",", ":"), ensure_ascii=True)
    return sha256(b"InfinityDB runtime database set v1\x00" + value.encode("ascii")).hexdigest()
