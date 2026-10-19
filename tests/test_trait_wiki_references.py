"""Guard explicitly reviewed canonical Trait-to-Wiki destinations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from infinity_db.trait_wiki_references import load_trait_wiki_references


def _document(url: str, *, name: str = "Non-Lethal") -> dict:
    return {
        "format": "InfinityDB trait Wiki references",
        "version": 1,
        "entries": {
            "trait:non-lethal": {
                "name": name,
                "url": url,
            }
        },
    }


def test_reviewed_trait_wiki_destinations_are_explicit() -> None:
    mapping = load_trait_wiki_references()

    assert set(mapping) == {"trait:continuous-damage", "trait:non-lethal"}
    assert mapping["trait:continuous-damage"] == {
        "name": "Continuous Damage",
        "url": "https://infinitythewiki.com/Traits#Continuous_Damage",
    }


@pytest.mark.parametrize(
    "url",
    [
        "http://infinitythewiki.com/Traits#Non-Lethal",
        "https://evil.example/Traits#Non-Lethal",
        "https://infinitythewiki.com.evil.example/Traits#Non-Lethal",
        "https://infinitythewiki.com/Weapons_Chart#Non-Lethal",
        "https://infinitythewiki.com/Traits",
        "https://infinitythewiki.com/Traits?oldid=4110#Non-Lethal",
        "https://infinitythewiki.com:443/Traits#Non-Lethal",
    ],
)
def test_trait_wiki_mapping_rejects_unreviewed_destinations(
    tmp_path: Path, url: str
) -> None:
    path = tmp_path / "links.json"
    path.write_text(json.dumps(_document(url)), encoding="utf-8")

    with pytest.raises(ValueError, match="Unreviewed trait Wiki destination"):
        load_trait_wiki_references(path)


def test_trait_wiki_mapping_rejects_unreviewed_ids_and_shapes(tmp_path: Path) -> None:
    path = tmp_path / "links.json"
    document = _document("https://infinitythewiki.com/Traits#Non-Lethal")
    document["entries"]["trait:non-lethal"]["unknown"] = "ignored"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid trait Wiki entry"):
        load_trait_wiki_references(path)

    document["entries"] = {"equipment:non-lethal": document["entries"]["trait:non-lethal"]}
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid trait Wiki reference ID"):
        load_trait_wiki_references(path)
