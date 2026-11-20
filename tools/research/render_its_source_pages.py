"""Render exact local ITS source-PDF pages for geometry and diagram review.

Keeps all source bytes and generated PNG previews under ignored local/.
This is a research aid, not a canonical scenario-map exporter.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SETS = {
    "current": ROOT / "local/data/pdf/its",
    "its17": ROOT / "local/data/pdf/legacy/its_17",
}
DEFAULT_OUTPUT = ROOT / "local/work/its/source-pages"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("filename", help="PDF basename in selected source set")
    parser.add_argument(
        "--source-set", choices=sorted(SOURCE_SETS), default="current",
        help="Select current ITS PDFs or archived ITS 17 revisions",
    )
    parser.add_argument("--pages", required=True, help="Comma-separated 1-based PDF pages")
    parser.add_argument("--dpi", type=int, default=120)
    parser.add_argument(
        "--crop", help="Optional page-relative crop: x0,y0,x1,y1 (fractions 0..1)"
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    crop = None
    if args.crop:
        try:
            crop = tuple(float(part) for part in args.crop.split(","))
        except ValueError:
            parser.error("--crop requires four decimal fractions")
        if len(crop) != 4 or not (0 <= crop[0] < crop[2] <= 1 and 0 <= crop[1] < crop[3] <= 1):
            parser.error("--crop must be x0,y0,x1,y1 inside 0..1")

    sources = SOURCE_SETS[args.source_set].resolve()
    source = (sources / args.filename).resolve()
    if source.parent != sources or source.suffix.lower() != ".pdf":
        parser.error(f"Source must be a PDF basename in {sources.relative_to(ROOT)}")
    if not source.is_file():
        parser.error(f"Missing source PDF: {source}")
    if args.dpi < 72 or args.dpi > 200:
        parser.error("DPI must be between 72 and 200")
    try:
        pages = [int(page) for page in args.pages.split(",")]
    except ValueError:
        parser.error("--pages requires a comma-separated list of integers")
    if not pages or any(page <= 0 for page in pages) or len(pages) > 12:
        parser.error("--pages requires 1 to 12 positive page numbers")

    output_dir = args.output_dir.resolve()
    if not output_dir.is_relative_to((ROOT / "local").resolve()):
        parser.error("Output must be in ignored local/")
    output_dir.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(source) as document:
        for page in pages:
            if page > len(document):
                parser.error(f"Page {page} exceeds document page count {len(document)}")
            suffix = "-crop" if crop else ""
            output = output_dir / f"{source.stem}-p{page:03d}{suffix}.png"
            source_page = document[page - 1]
            clip = None
            if crop:
                rect = source_page.rect
                clip = pymupdf.Rect(
                    rect.x0 + crop[0] * rect.width, rect.y0 + crop[1] * rect.height,
                    rect.x0 + crop[2] * rect.width, rect.y0 + crop[3] * rect.height,
                )
            source_page.get_pixmap(
                matrix=pymupdf.Matrix(args.dpi / 72, args.dpi / 72),
                alpha=False, clip=clip,
            ).save(output)
            print(output.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
