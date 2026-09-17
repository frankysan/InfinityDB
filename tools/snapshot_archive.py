from __future__ import annotations

import zipfile
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path


def create_timestamped_archive(
    files: Iterable[Path],
    destination: Path,
    *,
    prefix: str,
    root: Path | None = None,
    now: datetime | None = None,
) -> Path:
    """Archive exactly ``files`` using the shared snapshot naming convention."""
    timestamp = (now or datetime.now().astimezone()).strftime("%Y%m%d-%H%M%S")
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / f"{prefix} {timestamp}.zip"
    sequence = 2
    while archive.exists():
        archive = destination / f"{prefix} {timestamp}-{sequence}.zip"
        sequence += 1

    items: list[tuple[str, Path]] = []
    seen_names: set[str] = set()
    for path in files:
        arcname = path.relative_to(root).as_posix() if root is not None else path.name
        if arcname in seen_names:
            raise ValueError(f"Duplicate archive path: {arcname}")
        seen_names.add(arcname)
        items.append((arcname, path))

    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as output:
        for arcname, path in sorted(items):
            output.write(path, arcname)
    return archive
