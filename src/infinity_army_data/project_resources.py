"""Locate maintained InfinityDB project resources in source and installed layouts."""

from __future__ import annotations

import sys
from pathlib import Path

_SOURCE_ROOT = Path(__file__).resolve().parents[2]
_INSTALLED_SHARE = Path(sys.prefix) / "share" / "infinity-db"


def maintained_config_path(
    *parts: str,
    source_root: Path | None = None,
    install_prefix: Path | None = None,
) -> Path:
    """Return one maintained config path for a source checkout or wheel install.

    A source checkout remains authoritative when the tracked ``config/`` file is
    present. Installed wheels place the same authored files under
    ``<sys.prefix>/share/infinity-db/config``.
    """
    relative = Path(*parts)
    source_base = source_root if source_root is not None else _SOURCE_ROOT
    source_path = source_base / "config" / relative
    if source_path.is_file():
        return source_path

    prefix = install_prefix if install_prefix is not None else Path(sys.prefix)
    return prefix / "share" / "infinity-db" / "config" / relative


def maintained_curated_path(
    *parts: str,
    source_root: Path | None = None,
    install_prefix: Path | None = None,
) -> Path:
    """Return one curated project-data path for a source checkout or wheel install."""
    relative = Path(*parts)
    source_base = source_root if source_root is not None else _SOURCE_ROOT
    source_path = source_base / "data" / "curated" / relative
    if source_path.is_file():
        return source_path

    prefix = install_prefix if install_prefix is not None else Path(sys.prefix)
    return prefix / "share" / "infinity-db" / "data" / "curated" / relative
