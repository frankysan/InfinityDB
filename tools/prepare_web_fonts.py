"""Build InfinityDB's canonical browser-font publication from Google Fonts TTFs."""

from __future__ import annotations

import argparse
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from fontTools.ttLib import TTFont

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "src" / "infinity_db" / "web" / "static" / "fonts"


class _OS2Table(Protocol):
    usWeightClass: int


@dataclass(frozen=True)
class FontFace:
    source: str
    destination: str
    family_prefix: str
    weight: int
    variable_axes: tuple[tuple[str, float, float], ...] = ()


FACES = (
    FontFace(
        "Audiowide/Audiowide-Regular.ttf",
        "Audiowide/Audiowide-Regular.woff2",
        "Audiowide",
        400,
    ),
    FontFace(
        "Oxanium/Oxanium-VariableFont_wght.ttf",
        "Oxanium/Oxanium-Variable.woff2",
        "Oxanium",
        200,
        (("wght", 200.0, 800.0),),
    ),
    FontFace(
        "IBM_Plex_Sans/IBMPlexSans-VariableFont_wdth,wght.ttf",
        "IBM_Plex_Sans/IBMPlexSans-Variable.woff2",
        "IBM Plex Sans",
        400,
        (("wght", 100.0, 700.0), ("wdth", 75.0, 100.0)),
    ),
    FontFace(
        "IBM_Plex_Sans/IBMPlexSans-Italic-VariableFont_wdth,wght.ttf",
        "IBM_Plex_Sans/IBMPlexSans-Italic-Variable.woff2",
        "IBM Plex Sans",
        400,
        (("wght", 100.0, 700.0), ("wdth", 75.0, 100.0)),
    ),
    FontFace(
        "IBM_Plex_Sans_Condensed/IBMPlexSansCondensed-Regular.ttf",
        "IBM_Plex_Sans_Condensed/IBMPlexSansCondensed-Regular.woff2",
        "IBM Plex Sans Condensed",
        400,
    ),
    FontFace(
        "IBM_Plex_Sans_Condensed/IBMPlexSansCondensed-Medium.ttf",
        "IBM_Plex_Sans_Condensed/IBMPlexSansCondensed-Medium.woff2",
        "IBM Plex Sans Condensed",
        500,
    ),
    FontFace(
        "IBM_Plex_Sans_Condensed/IBMPlexSansCondensed-SemiBold.ttf",
        "IBM_Plex_Sans_Condensed/IBMPlexSansCondensed-SemiBold.woff2",
        "IBM Plex Sans Condensed",
        600,
    ),
    FontFace(
        "IBM_Plex_Sans_Condensed/IBMPlexSansCondensed-Bold.ttf",
        "IBM_Plex_Sans_Condensed/IBMPlexSansCondensed-Bold.woff2",
        "IBM Plex Sans Condensed",
        700,
    ),
    FontFace(
        "IBM_Plex_Mono/IBMPlexMono-Regular.ttf",
        "IBM_Plex_Mono/IBMPlexMono-Regular.woff2",
        "IBM Plex Mono",
        400,
    ),
)

LICENSES = (
    ("Audiowide/OFL.txt", "Audiowide/OFL.txt"),
    ("Oxanium/OFL.txt", "Oxanium/OFL.txt"),
    ("IBM_Plex_Sans/OFL.txt", "IBM_Plex_Sans/OFL.txt"),
    ("IBM_Plex_Sans_Condensed/OFL.txt", "IBM_Plex_Sans_Condensed/OFL.txt"),
    ("IBM_Plex_Mono/OFL.txt", "IBM_Plex_Mono/OFL.txt"),
)

README = """# Browser fonts

This directory is the canonical browser-font publication for InfinityDB.

The WOFF2 files are generated from upstream Google Fonts TTF downloads with
`tools/prepare_web_fonts.py`. Source TTFs may be staged in these family directories for
regeneration, but they are gitignored and excluded from wheels/runtime packages. An unpacked
Google Fonts download containing the expected family directories may also be supplied from
any external directory. The helper requires the project's `symbols` optional dependencies.

Runtime roles:

- Audiowide: InfinityDB wordmark/brand text.
- Oxanium: display headings and titles.
- IBM Plex Sans: running text and normal controls.
- IBM Plex Sans Condensed: dense tables and compact structured data.
- IBM Plex Mono: identifiers and developer/diagnostic text.

Each family remains licensed under the SIL Open Font License 1.1. The corresponding
`OFL.txt` is stored beside its published font files and the copyright holders are also
listed in the repository-level `THIRD_PARTY_NOTICES.md`.
"""


def _font_family(font: TTFont) -> str:
    for record in font["name"].names:
        if record.nameID == 1 and record.platformID == 3:
            return record.toUnicode()
    for record in font["name"].names:
        if record.nameID == 1:
            return record.toUnicode()
    raise ValueError("Font has no family name")


def _validate_face(font: TTFont, spec: FontFace, source: Path) -> None:
    family = _font_family(font)
    if not family.startswith(spec.family_prefix):
        raise ValueError(
            f"Unexpected family for {source}: {family!r}; expected {spec.family_prefix!r}"
        )
    actual_weight = cast(_OS2Table, font["OS/2"]).usWeightClass
    if actual_weight != spec.weight:
        raise ValueError(
            f"Unexpected weight for {source}: {actual_weight}; expected {spec.weight}"
        )
    if spec.variable_axes:
        if "fvar" not in font:
            raise ValueError(f"Expected variable font axes in {source}")
        axes = {axis.axisTag: axis for axis in font["fvar"].axes}
        for tag, minimum, maximum in spec.variable_axes:
            axis = axes.get(tag)
            if axis is None or axis.minValue != minimum or axis.maxValue != maximum:
                raise ValueError(
                    f"Unexpected {tag!r} axis for {source}: "
                    f"{None if axis is None else (axis.minValue, axis.maxValue)!r}"
                )


def _convert_face(source_root: Path, staging_root: Path, spec: FontFace) -> None:
    source = source_root / spec.source
    if not source.is_file():
        raise FileNotFoundError(f"Required source font is missing: {source}")
    destination = staging_root / spec.destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    font = TTFont(source, recalcTimestamp=False)
    try:
        _validate_face(font, spec, source)
        font.flavor = "woff2"
        font.save(destination, reorderTables=True)
    finally:
        font.close()
    if destination.read_bytes()[:4] != b"wOF2":
        raise ValueError(f"FontTools did not produce a WOFF2 file: {destination}")


def _copy_license(source_root: Path, staging_root: Path, source_name: str, target: str) -> None:
    source = source_root / source_name
    if not source.is_file():
        raise FileNotFoundError(f"Required font license is missing: {source}")
    content = source.read_bytes()
    text = content.decode("utf-8")
    if "SIL Open Font License" not in text or "Version 1.1" not in text:
        raise ValueError(f"Unexpected font license text: {source}")
    destination = staging_root / target
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)


def prepare_web_fonts(source_root: Path, output_root: Path = DEFAULT_OUTPUT_ROOT) -> None:
    """Build the canonical WOFF2 files without retaining upstream TTFs in the package."""

    source_root = source_root.resolve()
    output_root = output_root.resolve()
    if not source_root.is_dir():
        raise FileNotFoundError(f"Font source directory does not exist: {source_root}")

    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="infinitydb-web-fonts-") as temp_name:
        staging_root = Path(temp_name) / "fonts"
        staging_root.mkdir()
        for spec in FACES:
            _convert_face(source_root, staging_root, spec)
        for source_name, target in LICENSES:
            _copy_license(source_root, staging_root, source_name, target)
        (staging_root / "README.md").write_text(README, encoding="utf-8", newline="\n")

        expected_woff2 = {Path(spec.destination) for spec in FACES}
        for existing in output_root.rglob("*.woff2"):
            relative = existing.relative_to(output_root)
            if relative not in expected_woff2:
                existing.unlink()
        for relative in sorted(expected_woff2):
            source = staging_root / relative
            destination = output_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        for _, target in LICENSES:
            source = staging_root / target
            destination = output_root / target
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        shutil.copyfile(staging_root / "README.md", output_root / "README.md")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert the selected Google Fonts TTFs into InfinityDB's WOFF2 publication."
    )
    parser.add_argument(
        "source_root",
        type=Path,
        help="Directory containing Audiowide, Oxanium, IBM_Plex_Sans, and related downloads",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Destination browser-font directory",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    prepare_web_fonts(args.source_root, args.output_root)
    print(f"Published {len(FACES)} WOFF2 faces to {args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
