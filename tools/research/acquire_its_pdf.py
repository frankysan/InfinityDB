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
DESTINATION = ROOT / "local/data/pdf/its"
SOURCES = {
    "its-17-en-v1.0.2": (
        "https://downloads.corvusbelli.com/infinity/organized-play/"
        "its-rules-season-17-en-v1.0.2.pdf",
        "its-17-rules-v1.0.2-en.pdf",
        "73a184b80535f23499000bb81112d95168c12f970fa14a30050a95ec51cdfe71",
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
    parser.add_argument("key", choices=sorted(SOURCES))
    args = parser.parse_args(argv)
    path, digest, size, pages = acquire(args.key)
    print(f"Source: {path.relative_to(ROOT)}")
    print(f"URL: {SOURCES[args.key][0]}")
    print(f"SHA-256: {digest}")
    print(f"Bytes: {size}")
    print(f"PDF pages: {pages}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
