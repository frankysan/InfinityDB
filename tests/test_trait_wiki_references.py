"""Guard explicitly reviewed canonical Trait-to-Wiki destinations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_directory
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

    assert set(mapping) == {
        "trait:anti-materiel",
        "trait:aro",
        "trait:bioweapon",
        "trait:boost",
        "trait:cc",
        "trait:concealed",
        "trait:continuous-damage",
        "trait:deployable",
        "trait:direct-template",
        "trait:double-shot",
        "trait:impact-template",
        "trait:improvised",
        "trait:indiscriminate",
        "trait:intuitive-attack",
        "trait:non-lethal",
        "trait:non-reloadable",
        "trait:perimeter",
        "trait:prior-deployment",
        "trait:reflective",
        "trait:speculative-attack",
        "trait:state",
        "trait:targetless",
    }
    assert mapping["trait:continuous-damage"] == {
        "name": "Continuous Damage",
        "url": "https://infinitythewiki.com/Traits#Continuous_Damage",
    }


def test_reviewed_trait_wiki_links_match_current_canonical_records() -> None:
    root = Path(__file__).resolve().parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    traits = {
        record["id"]: record["name"]
        for _, document in documents
        for record in document["records"]
        if record["kind"] == "trait"
    }

    mapping = load_trait_wiki_references()
    assert len(traits) == 33
    assert {record_id: traits[record_id] for record_id in mapping} == {
        record_id: entry["name"] for record_id, entry in mapping.items()
    }
    # These official headings still need exact punctuation-sensitive URL verification.
    assert set(traits) - set(mapping) == {
        "trait:arm-0",
        "trait:bs-weapon-ph",
        "trait:bs-weapon-wip",
        "trait:bts-0",
        "trait:burst-b",
        "trait:burst-single-target",
        "trait:disposable-x",
        "trait:silent-x",
        "trait:suppressive-fire",
        "trait:target-attribute",
        "trait:zone-of-control-zc",
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
