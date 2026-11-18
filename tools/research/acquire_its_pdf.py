"""Acquire an original official ITS PDF into ignored local source storage.

This is an explicit research operation, not part of builds, tests or deployment.
The downloaded bytes are never rewritten; the SHA-256 can be pinned in curation.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / "local/data/pdf/legacy/its_17"
# Locally supplied publisher originals; other revisions are verified offline only.
# Each value is (SHA-256, byte count, PDF page count).
PINNED_REVISIONS = {
    "v0.0-en": ("93de3ce8f9090edf86acf1db00e2d1dac6f2f44a9898e4bd8a98d991d308c812", 10384762, 68),
    "v0.0-es": ("5a8ef31491e9e22e4e9b8a8f8c526a3adafac5abf4ab11e999b730d3e5a67d38", 10499166, 67),
    "v0.1-en": ("1384eddb24affec3c16243d70d627d94c3bfe1250bec053647b08e30b837dd35", 11285980, 68),
    "v0.1-es": ("0edea2f3f1df41e6e341d188e7ab767faf236601c28b01b2469a534117c4ba89", 11330817, 67),
    "v0.2-en": ("73a184b80535f23499000bb81112d95168c12f970fa14a30050a95ec51cdfe71", 15286703, 105),
    "v0.2-es": ("d202d7e3373852204b848fa8eee3bbc19000695cec0296c9882e7d0f3a030457", 15690091, 112),
}
SOURCES = {
    "its-17-en-v1.0.2": (
        "https://downloads.corvusbelli.com/infinity/organized-play/"
        "its-rules-season-17-en-v1.0.2.pdf",
        "its-rules-season-17-v0.2-en.pdf",
        PINNED_REVISIONS["v0.2-en"][0],
    ),
}
MAX_BYTES = 30 * 1024 * 1024


def acquire(key: str) -> tuple[Path, str, int, int]:
    """Download once, validate PDF structure, return exact source identity."""
    url, filename, expected_sha256 = SOURCES[key]
    destination = DESTINATION / filename
    DESTINATION.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        payload = destination.read_bytes()
    else:
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix="its-download-", suffix=".part",
                dir=DESTINATION, delete=False,
            ) as handle:
                temporary = Path(handle.name)
                request = Request(url, headers={"User-Agent": "InfinityDB-source-acquisition"})
                with urlopen(request, timeout=90) as response:  # noqa: S310
                    final = urlparse(response.geturl())
                    if final.scheme != "https":
                        raise ValueError("Official source redirected to an insecure URL")
                    count = 0
                    while chunk := response.read(1024 * 1024):
                        count += len(chunk)
                        if count > MAX_BYTES:
                            raise ValueError("Official ITS PDF exceeds the 30 MiB limit")
                        handle.write(chunk)
            payload = temporary.read_bytes()
            _verify_pdf(payload)
            if hashlib.sha256(payload).hexdigest() != expected_sha256:
                raise ValueError("Official ITS PDF SHA-256 differs from its pinned original")
            os.replace(temporary, destination)
        except (HTTPError, URLError, OSError, ValueError) as exc:
            raise ValueError(f"Official ITS PDF acquisition failed: {exc}") from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    pages = _verify_pdf(payload)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256:
        raise ValueError("Local ITS PDF SHA-256 differs from its pinned original")
    return destination, digest, len(payload), pages


def verify_revision_set(directory: Path = DESTINATION) -> list[tuple[str, str, int, int]]:
    """Verify each locally supplied edition without downloading or changing sources."""
    verified = []
    for edition, (expected_hash, expected_size, expected_pages) in PINNED_REVISIONS.items():
        filename = f"its-rules-season-17-{edition}.pdf"
        source = directory / filename
        if not source.is_file():
            raise ValueError(f"Missing ITS 17 edition {filename}")
        if source.stat().st_size != expected_size:
            raise ValueError(f"ITS 17 edition has unexpected byte count: {filename}")
        payload = source.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if digest != expected_hash:
            raise ValueError(f"ITS 17 edition has unexpected SHA-256: {filename}")
        pages = _verify_pdf(payload)
        if pages != expected_pages:
            raise ValueError(f"ITS 17 edition has unexpected page count: {filename}")
        verified.append((filename, digest, len(payload), pages))
    return verified


def _verify_pdf(payload: bytes) -> int:
    if not payload.startswith(b"%PDF-") or len(payload) > MAX_BYTES:
        raise ValueError("Official ITS download is not a bounded PDF")
    try:
        with pymupdf.open(stream=payload, filetype="pdf") as pdf:
            if len(pdf) < 50:
                raise ValueError("Official ITS PDF has an implausible page count")
            return len(pdf)
    except (pymupdf.FileDataError, pymupdf.EmptyFileError) as exc:
        raise ValueError("Official ITS PDF is unreadable") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("key", nargs="?", choices=sorted(SOURCES))
    parser.add_argument(
        "--verify-set", action="store_true",
        help="Verify all six locally supplied ITS 17 editions without network access",
    )
    args = parser.parse_args(argv)
    if args.verify_set:
        if args.key:
            parser.error("Choose a download key or --verify-set, not both")
        for filename, digest, size, pages in verify_revision_set():
            print(f"{filename}: SHA-256={digest} bytes={size} pages={pages}")
        return 0
    if args.key is None:
        parser.error("Provide a download key or --verify-set")
    path, digest, size, pages = acquire(args.key)
    print(f"Source: {path.relative_to(ROOT)}")
    print(f"URL: {SOURCES[args.key][0]}")
    print(f"SHA-256: {digest}")
    print(f"Bytes: {size}")
    print(f"PDF pages: {pages}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
