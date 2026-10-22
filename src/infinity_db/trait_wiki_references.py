"""Explicitly reviewed official Wiki destinations for canonical Traits."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from infinity_army_data.project_resources import maintained_config_path

DEFAULT_MAPPING_PATH = maintained_config_path("catalogs", "trait-wiki-references.json")
_TRAIT_ID = re.compile(r"trait:[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def load_trait_wiki_references(
    path: Path = DEFAULT_MAPPING_PATH,
) -> dict[str, dict[str, str]]:
    """Validate exact curated identities and links without URL/slug inference."""
    document = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict)
        or set(document) != {"format", "version", "entries"}
        or document["format"] != "InfinityDB trait Wiki references"
        or document["version"] != 1
    ):
        raise ValueError("Unsupported trait Wiki reference config")
    entries = document["entries"]
    if not isinstance(entries, dict) or not entries:
        raise ValueError("Trait Wiki reference config requires entries")
    for record_id, entry in entries.items():
        if not isinstance(record_id, str) or _TRAIT_ID.fullmatch(record_id) is None:
            raise ValueError(f"Invalid trait Wiki reference ID {record_id!r}")
        if not isinstance(entry, dict) or set(entry) != {"name", "url"}:
            raise ValueError(f"Invalid trait Wiki entry {record_id!r}")
        name, url = entry["name"], entry["url"]
        if not isinstance(name, str) or not name.strip() or name != name.strip():
            raise ValueError(f"Invalid trait Wiki name for {record_id!r}")
        if not isinstance(url, str):
            raise ValueError(f"Invalid trait Wiki URL for {record_id!r}")
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or parts.netloc != "infinitythewiki.com"
            or parts.path != "/Traits"
            or not parts.fragment
            or parts.query
        ):
            raise ValueError(f"Unreviewed trait Wiki destination for {record_id!r}")
    return entries
