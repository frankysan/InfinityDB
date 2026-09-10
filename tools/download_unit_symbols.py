"""Download the primary unit symbols referenced by an Army master-list snapshot."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

ASSET_HOST = "assets.corvusbelli.net"
ASSET_PATH = "/army/img/logo/units/"
SVG_NAME = re.compile(r"[a-z0-9-]+\.svg$")


def primary_logos(master_list: dict) -> set[str]:
    """Return one deterministic profile-logo URL for every referenced unit ID."""
    by_unit: dict[int, str] = {}
    for army in master_list.values():
        for unit in army.get("units", []):
            unit_id = unit.get("id")
            if not isinstance(unit_id, int) or unit_id in by_unit:
                continue
            logo = next(
                (
                    profile["logo"]
                    for group in unit.get("profileGroups", [])
                    for profile in group.get("profiles", [])
                    if isinstance(profile.get("logo"), str)
                ),
                None,
            )
            if logo is not None:
                by_unit[unit_id] = logo
    return set(by_unit.values())


def destination_name(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != ASSET_HOST:
        raise ValueError(f"Unsupported symbol host: {url}")
    if not parsed.path.startswith(ASSET_PATH):
        raise ValueError(f"Unsupported symbol path: {url}")
    name = Path(parsed.path).name
    if not SVG_NAME.fullmatch(name):
        raise ValueError(f"Unsupported symbol filename: {url}")
    return name


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master_list", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    master_list = json.loads(args.master_list.read_text(encoding="utf-8"))
    if not isinstance(master_list, dict):
        raise ValueError("master list must be an object keyed by Army source filename")
    urls = sorted(primary_logos(master_list))
    existing = {path.name for path in args.destination.rglob("*.svg")}
    pending = []
    for url in urls:
        name = destination_name(url)
        if name not in existing:
            pending.append((url, name))
    print(f"Primary symbols: {len(urls)}; already present: {len(urls) - len(pending)}")
    if args.dry_run:
        print(f"Would download: {len(pending)}")
        return 0

    args.destination.mkdir(parents=True, exist_ok=True)
    for index, (url, name) in enumerate(pending, start=1):
        with urlopen(url, timeout=30) as response:
            body = response.read()
        if b"<svg" not in body[:1024]:
            raise ValueError(f"Expected an SVG response: {url}")
        (args.destination / name).write_bytes(body)
        print(f"[{index}/{len(pending)}] {name}")
    print(f"Downloaded: {len(pending)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
