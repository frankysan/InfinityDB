"""Export explicit, pinned raw-symbol requests without network access.

InfinityDB owns which Army, static and legacy sources are authoritative.
The standalone symbol producer may download only this reviewed URL/path set.
The normal application build does not depend on this optional export.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from infinity_db.snapshot_provenance import sha256_file
from tools.army_snapshot_source import resolve_army_snapshot
from tools.symbol_source import (
    DEFAULT_LEGACY_ARMIES,
    DEFAULT_STATIC_CONFIG,
    archive_paths,
    discover_symbol_source,
)

FORMAT = "InfinityDB raw symbol acquisition requests"
VERSION = 1
_SHA256 = re.compile(r"[0-9a-f]{64}")


def build_source_plan(
    army_archive: Path,
    army_manifest: Path,
    *,
    static_symbols_path: Path = DEFAULT_STATIC_CONFIG,
    legacy_armies_path: Path | None = DEFAULT_LEGACY_ARMIES,
    project_root: Path | None = None,
) -> dict[str, Any]:
    """Pin a read-only source request set to one verified Army ZIP."""
    project_root = project_root or Path.cwd()
    pinned = resolve_army_snapshot(
        army_archive,
        manifest_directory=army_manifest.parent,
        manifest=army_manifest,
    )
    discovery = discover_symbol_source(
        pinned.archive,
        static_symbols_path=static_symbols_path,
        legacy_armies_path=legacy_armies_path,
        project_root=project_root,
    )
    if discovery.source_document_count != pinned.document_count:
        raise ValueError(
            "Source-discovery document count does not match Army provenance: "
            f"{discovery.source_document_count} != {pinned.document_count}"
        )

    paths = archive_paths(discovery)
    requests = [
        {"url": url, "archivePath": paths[url]}
        for url in sorted(discovery.authoritative_urls)
    ]
    if len(requests) != len(paths):
        raise ValueError("Symbol source request paths are incomplete")

    digest = sha256_file(army_archive)
    assert _SHA256.fullmatch(digest)
    return {
        "format": FORMAT,
        "formatVersion": VERSION,
        "inputArtifact": {
            "name": army_archive.name,
            "sha256": digest,
        },
        "sourceDocumentCount": pinned.document_count,
        "requests": requests,
    }


def write_source_plan(path: Path, plan: dict[str, Any]) -> Path:
    """Write immutable deterministic JSON; matching bytes are idempotent."""
    payload = (json.dumps(
        plan, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False,
    ) + "\n").encode("utf-8")
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"Existing raw-symbol source plan differs: {path}")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    created = False
    try:
        with temporary.open("xb") as stream:
            created = True
            stream.write(payload)
        temporary.replace(path)
    except BaseException:
        if created:
            temporary.unlink(missing_ok=True)
        raise
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--static-symbols", type=Path, default=DEFAULT_STATIC_CONFIG)
    parser.add_argument("--legacy-armies", type=Path, default=DEFAULT_LEGACY_ARMIES)
    args = parser.parse_args(argv)
    try:
        plan = build_source_plan(
            args.snapshot,
            args.manifest,
            static_symbols_path=args.static_symbols,
            legacy_armies_path=args.legacy_armies,
        )
        output = write_source_plan(args.output, plan)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(
        f"Symbol source request plan -> {output} "
        f"({len(plan['requests'])} authoritative URLs)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
