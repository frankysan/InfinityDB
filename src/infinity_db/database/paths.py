"""Dependency-light paths shared by database build and runtime entry points."""

from pathlib import Path


def raw_database_path(path: Path) -> Path:
    """Return the development archive path associated with a frontend database."""
    path = Path(path)
    return path.with_name(f"{path.stem}.raw{path.suffix}")
