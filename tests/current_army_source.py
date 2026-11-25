"""Select the exact Army archive bound to the current tracked publication."""

from __future__ import annotations

import hashlib
import json
import zipfile
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SOURCE = json.loads(
    (ROOT / "data/manifests/symbol-publication.json").read_text(encoding="utf-8")
)["sourceSnapshot"]["armyArtifact"]
CURRENT_ARMY_ZIP = ROOT / "local/data/raw/army" / _SOURCE["name"]


@lru_cache(maxsize=1)
def verify_current_army_archive() -> None:
    with CURRENT_ARMY_ZIP.open("rb") as handle:
        assert hashlib.file_digest(handle, "sha256").hexdigest() == _SOURCE["sha256"]


def open_current_army_archive() -> zipfile.ZipFile:
    verify_current_army_archive()
    return zipfile.ZipFile(CURRENT_ARMY_ZIP)
