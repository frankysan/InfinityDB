"""Shared filename/path sanitization for tool scripts.

The goal is to produce filesystem-safe names across Windows, macOS, and Linux
without losing too much readability. The rules are intentionally conservative so
we can still mirror real wiki/site names while avoiding invalid or dangerous
characters on the host OS.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote

_WINDOWS_RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    "com1",
    "com2",
    "com3",
    "com4",
    "com5",
    "com6",
    "com7",
    "com8",
    "com9",
    "lpt1",
    "lpt2",
    "lpt3",
    "lpt4",
    "lpt5",
    "lpt6",
    "lpt7",
    "lpt8",
    "lpt9",
}


def sanitize_path_component(value: str, *, os_name: str | None = None) -> str:
    """Normalize a path component so it is valid on the target OS."""
    os_name = (os_name or sys.platform).lower()
    cleaned = unquote(value).strip().replace("\\", "/")
    cleaned = unicodedata.normalize("NFKD", cleaned)
    cleaned = cleaned.encode("ascii", "ignore").decode("ascii")

    if os_name.startswith("win"):
        cleaned = re.sub(r'[<>:"|?*]+', "_", cleaned)
        cleaned = cleaned.replace("/", "_")
        cleaned = cleaned.rstrip(". ")
        if not cleaned:
            cleaned = "_"
        if cleaned.lower() in _WINDOWS_RESERVED:
            cleaned = f"_{cleaned}"
        if len(cleaned) > 240:
            cleaned = cleaned[:240].rstrip(". ")
    else:
        cleaned = re.sub(r"[\x00-\x1f]", "", cleaned)
        cleaned = cleaned.replace("/", "_")
        cleaned = cleaned.rstrip(".")
        if not cleaned:
            cleaned = "_"

    return cleaned


def sanitize_filename(name: str, *, os_name: str | None = None) -> str:
    """Return a safe filename while preserving the final extension."""
    path = Path(name)
    stem, suffix = path.stem, path.suffix.lower()
    if not suffix:
        suffix = "." + path.name.split(".")[-1] if "." in path.name else ""

    cleaned = unicodedata.normalize("NFKD", stem)
    cleaned = cleaned.encode("ascii", "ignore").decode("ascii")
    cleaned = cleaned.lower()
    cleaned = re.sub(r"[^a-z0-9._ -]+", "-", cleaned)
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned)
    cleaned = cleaned.strip("-. ")
    if not cleaned:
        cleaned = "file"

    if (os_name or sys.platform).lower().startswith("win"):
        cleaned = re.sub(r'[<>:"|?*]+', "-", cleaned)
        cleaned = re.sub(r"\s+", "-", cleaned)
        cleaned = re.sub(r"-+", "-", cleaned)
        cleaned = cleaned.strip("-. ")
        if cleaned.lower() in _WINDOWS_RESERVED:
            cleaned = f"_{cleaned}"
        if len(cleaned) > 240:
            cleaned = cleaned[:240].rstrip("-. ")
    else:
        cleaned = re.sub(r"[\x00-\x1f]", "", cleaned)
        cleaned = re.sub(r"\s+", "-", cleaned)
        cleaned = re.sub(r"-+", "-", cleaned)
        cleaned = cleaned.strip("-. ")

    if not cleaned:
        cleaned = "file"
    return f"{cleaned}{suffix}"


def sanitize_relative_path(path: str, *, os_name: str | None = None) -> str:
    """Normalize a relative path by sanitizing each component."""
    normalized = unquote(path).replace("\\", "/")
    if normalized.startswith("/"):
        normalized = normalized[1:]
    if not normalized:
        return "index.html"
    parts = [
        sanitize_path_component(part, os_name=os_name) for part in normalized.split("/") if part
    ]
    return "/".join(parts) if parts else "index.html"
