"""Reorganize bundled SVG symbols from an Army snapshot.

The snapshot supplies unit IDs, slugs, and canonical (main army) ownership.
Symbols no longer present in the snapshot are retained with a cleaned legacy
name and, where possible, their legacy army directory.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import unicodedata
import zipfile
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

SYMBOL_MAP = "unit-symbol-map.js"
ARMY_MAP = "army-symbols.js"
SOURCE_SUFFIX = re.compile(r"-(?:[0-9]+|null)-[0-9]+$")
ARMY_ENTRY = re.compile(r'\[(\d+), "([^"]+)"\]')
UNIT_ENTRY = re.compile(r'(\["[^"]+", )"([^"]+)"(\])')


def slugify(value: str) -> str:
    """Return an ASCII, lowercase, dash-separated filename component."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_value)).strip("-")


def unique_path(directory: Path, stem: str) -> Path:
    """Return an unused SVG path, adding a numeric suffix when needed."""
    candidate = directory / f"{stem}.svg"
    number = 1
    while candidate.exists():
        candidate = directory / f"{stem}-{number}.svg"
        number += 1
    return candidate


def load_snapshot(path: Path) -> tuple[dict[int, str], dict[str, list[tuple[int, str, str]]]]:
    """Load faction slugs and source-logo ownership from a raw snapshot ZIP."""
    with zipfile.ZipFile(path) as archive:
        metadata = json.loads(archive.read("metadata.json"))
        factions = {
            faction["id"]: slugify(faction.get("slug") or faction.get("name") or str(faction["id"]))
            for faction in metadata["factions"]
        }
        logos: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
        for name in archive.namelist():
            if name == "metadata.json" or not name.endswith(".json"):
                continue
            document = json.loads(archive.read(name))
            for unit in document.get("units", []):
                unit_id = unit.get("id")
                canonical = unit.get("canonical")
                slug = unit.get("slug") or unit.get("isc")
                if (
                    not isinstance(unit_id, int)
                    or not isinstance(canonical, int)
                    or not isinstance(slug, str)
                ):
                    continue
                record = (unit_id, factions.get(canonical, "unassigned"), slugify(slug))
                for group in unit.get("profileGroups", []):
                    for profile in group.get("profiles", []):
                        logo = profile.get("logo")
                        if isinstance(logo, str):
                            logos[Path(urlparse(logo).path).stem].append(record)
    return factions, logos


def unit_index(directory: Path) -> dict[str, Path]:
    """Match the web app's legacy first-symbol-wins lookup."""
    result: dict[str, Path] = {}
    for entry in directory.iterdir():
        if entry.is_dir():
            result.update(
                {key: value for key, value in unit_index(entry).items() if key not in result}
            )
        elif entry.suffix == ".svg":
            result.setdefault(entry.stem, entry)
    return result


def reorganize(snapshot: Path, static: Path) -> None:
    factions, logos = load_snapshot(snapshot)
    old_units = static / "unit-symbols"
    old_armies = static / "army-symbols"
    old_orders = static / "order-symbols"
    new_units = static / "units"
    new_armies = static / "armies"
    new_orders = static / "orders"
    old_unit_index = unit_index(old_units)
    destination_by_stem: dict[str, str] = {}

    for source in sorted(old_units.rglob("*.svg")):
        candidates = sorted(set(logos.get(source.stem, [])))
        if candidates:
            unit_id, army, slug = candidates[0]
            folder = new_units / army
            stem = f"{unit_id}-{slug}"
        else:
            relative = source.relative_to(old_units)
            army = slugify(relative.parts[0]) if len(relative.parts) > 1 else "unassigned"
            folder = new_units / army
            stem = slugify(SOURCE_SUFFIX.sub("", source.stem))
        folder.mkdir(parents=True, exist_ok=True)
        destination = unique_path(folder, stem)
        shutil.move(source, destination)
        if old_unit_index.get(source.stem) == source:
            destination_by_stem[source.stem] = (
                destination.relative_to(new_units).with_suffix("").as_posix()
            )

    army_text = (static / ARMY_MAP).read_text(encoding="utf-8")
    army_paths = {int(identifier): path for identifier, path in ARMY_ENTRY.findall(army_text)}
    for source in sorted(old_armies.rglob("*.svg")):
        relative = source.relative_to(old_armies).as_posix()
        army_id = next(
            (identifier for identifier, path in army_paths.items() if path == relative), None
        )
        folder = new_armies / slugify(source.relative_to(old_armies).parts[0])
        slug = factions.get(army_id, slugify(SOURCE_SUFFIX.sub("", source.stem)))
        stem = f"{army_id}-{slug}" if army_id is not None else slug
        folder.mkdir(parents=True, exist_ok=True)
        shutil.move(source, unique_path(folder, stem))

    for source in sorted(old_orders.rglob("*.svg")):
        new_orders.mkdir(parents=True, exist_ok=True)
        shutil.move(source, unique_path(new_orders, slugify(source.stem)))

    def army_replacement(match: re.Match[str]) -> str:
        identifier = int(match.group(1))
        old_path = match.group(2)
        folder = slugify(Path(old_path).parts[0])
        slug = factions.get(identifier, slugify(SOURCE_SUFFIX.sub("", Path(old_path).stem)))
        return f'[{identifier}, "{folder}/{identifier}-{slug}.svg"]'

    (static / ARMY_MAP).write_text(
        ARMY_ENTRY.sub(army_replacement, army_text), encoding="utf-8", newline="\n"
    )

    unit_text = (static / SYMBOL_MAP).read_text(encoding="utf-8")

    def unit_replacement(match: re.Match[str]) -> str:
        destination = destination_by_stem.get(match.group(2), match.group(2))
        return match.group(1) + json.dumps(destination) + match.group(3)

    (static / SYMBOL_MAP).write_text(
        UNIT_ENTRY.sub(unit_replacement, unit_text), encoding="utf-8", newline="\n"
    )

    for directory in (old_units, old_armies, old_orders):
        shutil.rmtree(directory)


def repair_unassigned(static: Path) -> None:
    """Move legacy faction-ID 1 symbols into the explicit unassigned folder."""
    legacy = static / "units" / "1"
    if not legacy.is_dir():
        return
    destination = static / "units" / "unassigned"
    destination.mkdir(parents=True, exist_ok=True)
    for source in sorted(legacy.glob("*.svg")):
        shutil.move(source, unique_path(destination, source.stem))
    legacy.rmdir()
    symbol_map = static / SYMBOL_MAP
    symbol_map.write_text(
        symbol_map.read_text(encoding="utf-8").replace('"1/', '"unassigned/'),
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, nargs="?", help="Raw Army snapshot ZIP")
    parser.add_argument("--static", type=Path, default=Path("src/infinity_db/web/static"))
    parser.add_argument("--repair-unassigned", action="store_true")
    args = parser.parse_args()
    if args.repair_unassigned:
        repair_unassigned(args.static)
        return 0
    if args.snapshot is None:
        parser.error("snapshot is required unless --repair-unassigned is used")
    reorganize(args.snapshot, args.static)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
