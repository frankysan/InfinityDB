"""Resolve Wiki archive members across legacy and portable snapshot names.

Legacy archives used extensionless wiki paths. Newer captures may append
`.html` or a portable Unicode suffix. Never silently choose between multiple
candidate pages; the caller must supply a reviewed exact member instead.
"""

from __future__ import annotations

import argparse
import re
import zipfile
from hashlib import sha256
from pathlib import Path


def resolve_page_member(archive: zipfile.ZipFile, member: str) -> str:
    names = set(archive.namelist())
    if member in names:
        return member
    if member + ".html" in names:
        return member + ".html"
    prefix = member.casefold() + "__u_"
    matches = sorted(
        name for name in names
        if name.casefold().startswith(prefix) and name.casefold().endswith(".html")
    )
    if len(matches) == 1:
        return matches[0]
    raise KeyError(
        f"Wiki page {member!r} has {len(matches)} portable candidates: {matches[:8]}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--search", required=True, help="Case-insensitive member substring")
    parser.add_argument("--digest", action="store_true", help="Show member hashes and revision IDs")
    args = parser.parse_args()
    with zipfile.ZipFile(args.archive) as archive:
        matches = [name for name in archive.namelist()
                   if args.search.casefold() in name.casefold()]
        for name in sorted(matches):
            if not args.digest:
                print(name)
                continue
            data = archive.read(name)
            revision = re.search(rb'"wgRevisionId"\s*:\s*(\d+)', data)
            rev = revision.group(1).decode("ascii") if revision else "unknown"
            print(f"{name}: sha256={sha256(data).hexdigest()} revision={rev}")
    print(f"Matches: {len(matches)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
