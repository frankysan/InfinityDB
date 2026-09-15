import json
from pathlib import Path

import pytest

from infinity_db.curated import (
    discover_curated_documents,
    load_curated_directory,
    load_curated_document,
)


def valid_document() -> dict:
    return {
        "format": "InfinityDB curated reference",
        "formatVersion": 2,
        "collection": {
            "id": "n5-core-v5.3",
            "title": "N5 Core Rules v5.3",
            "domain": "core-rules",
            "status": "current",
            "effectiveFrom": "2026-08-10",
            "authority": "primary",
        },
        "vocabularySources": {
            "skillTypes": [
                {
                    "sourceId": "n5-core-v5.3",
                    "path": "Skills_and_Equipment_Module.html",
                    "snapshotDate": "2026-09-15",
                    "heading": "Skills",
                    "page": 76,
                }
            ],
            "labels": [
                {
                    "sourceId": "n5-core-v5.3",
                    "path": "Labels.html",
                    "snapshotDate": "2026-09-15",
                    "heading": "Labels",
                    "page": 174,
                }
            ],
        },
        "skillTypes": [
            {
                "id": "automatic",
                "name": "Automatic",
                "labels": ["Automatic Skill", "Automatic Skills"],
                "descriptions": {
                    "singular": (
                        "An Automatic Skill can be employed without expending an Order or ARO."
                    ),
                    "plural": "Automatic Skills can be employed without expending an Order or ARO.",
                },
            }
        ],
        "labels": [
            {
                "id": "example-label",
                "name": "Example",
                "description": "An example label.",
            }
        ],
        "sources": [
            {
                "id": "n5-core-v5.3",
                "kind": "pdf",
                "title": "N5 core rules",
                "version": "5.3",
                "publishedDate": "2026-08-10",
                "localPath": "data/pdf/rules/n5-rules-v5-3-en.pdf",
                "pageCount": 196,
                "authority": "primary",
            }
        ],
        "records": [
            {
                "id": "skill-example",
                "kind": "skill",
                "name": "Example skill",
                "summary": "A concise human-written summary.",
                "facts": {"typeId": "automatic"},
                "labelIds": ["example-label"],
                "citations": [{"sourceId": "n5-core-v5.3", "page": 12}],
            }
        ],
    }


def test_load_curated_document_requires_provenance(tmp_path: Path) -> None:
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(valid_document()), encoding="utf-8")

    assert load_curated_document(path)["records"][0]["citations"][0]["page"] == 12


def test_load_curated_document_rejects_unstructured_json(tmp_path: Path) -> None:
    path = tmp_path / "source.json"
    path.write_text(json.dumps({"units": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="must declare format"):
        load_curated_document(path)


def test_load_curated_document_accepts_wiki_citation(tmp_path: Path) -> None:
    document = valid_document()
    document["sources"] = [
        {
            "id": "wiki-20260915",
            "kind": "wiki",
            "title": "Infinity Wiki snapshot",
            "version": "20260915",
            "snapshotDate": "2026-09-15",
            "localPath": "data/wiki/20260915/",
            "authority": "secondary",
        }
    ]
    document["records"][0]["citations"] = [
        {
            "sourceId": "wiki-20260915",
            "path": "infinitythewiki.com/Example.html",
            "snapshotDate": "2026-09-15",
        }
    ]
    path = tmp_path / "wiki.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    assert load_curated_document(path)["sources"][0]["kind"] == "wiki"


def test_load_curated_document_rejects_v1(tmp_path: Path) -> None:
    document = valid_document()
    document["formatVersion"] = 1
    path = tmp_path / "v1.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported curated format version"):
        load_curated_document(path)


def test_load_curated_document_rejects_non_json_reference_file(tmp_path: Path) -> None:
    path = tmp_path / "rules.pdf"
    path.write_bytes(b"not an application input")

    with pytest.raises(ValueError, match="must be a .json file"):
        load_curated_document(path)


def test_curated_directory_ignores_example_template(tmp_path: Path) -> None:
    curated_dir = tmp_path / "curated"
    curated_dir.mkdir()
    (curated_dir / "example.json").write_text('{"not": "a collection"}', encoding="utf-8")
    collection_path = curated_dir / "rules.json"
    collection_path.write_text(json.dumps(valid_document()), encoding="utf-8")

    assert discover_curated_documents(curated_dir) == [collection_path]
    assert load_curated_directory(curated_dir)[0][0] == collection_path


def test_checked_in_n5_collection_is_valid() -> None:
    path = Path(__file__).parents[1] / "data" / "curated" / "rules" / "n5-core-v5.3.json"

    document = load_curated_document(path)

    assert document["collection"]["id"] == "n5-core-v5.3"
    assert document["vocabularySources"]["skillTypes"][0]["path"].endswith(
        "Skills_and_Equipment_Module.html"
    )
    assert document["vocabularySources"]["labels"][0]["path"] == ("infinitythewiki.com/Labels.html")
    assert document["vocabularySources"]["skillTypes"][0]["page"] == 76
    assert document["vocabularySources"]["labels"][0]["page"] == 174
    assert [skill_type["id"] for skill_type in document["skillTypes"]] == [
        "automatic",
        "deployment-skill",
        "basic-short-skill",
        "short-skill",
        "long-skill",
        "aro",
    ]
    assert {label["id"] for label in document["labels"]} == {
        "airborne-deployment",
        "assignable-transmutation",
        "attack",
        "bs-attack",
        "cc-attack",
        "cc-special-skill",
        "comms-attack",
        "comms-equipment",
        "hackable",
        "hostile",
        "marker",
        "movement",
        "negative-feedback",
        "no-lof",
        "non-reloadable",
        "no-roll",
        "null",
        "obligatory",
        "optional",
        "private-information",
        "states-phase",
        "superior-deployment",
        "supportware",
        "faqs",
    }
    records = {record["id"]: record for record in document["records"]}
    assert records["state:camouflaged"]["kind"] == "state"
    assert records["state:camouflaged"]["labelIds"] == ["marker"]
    assert records["state:camouflaged"]["facts"]["enteredBy"] == ["skill:camouflage"]
    assert records["skill:camouflage"]["kind"] == "skill"
    assert records["skill:camouflage"]["labelIds"] == ["optional"]
    assert records["skill:camouflage"]["facts"]["typeId"] == "automatic"
    assert records["skill:camouflage"]["armyLinks"] == [{"entity": "skill", "id": 29}]
    assert all(len(skill_type["labels"]) == 2 for skill_type in document["skillTypes"])
    assert all(
        set(skill_type["descriptions"]) == {"singular", "plural"}
        for skill_type in document["skillTypes"]
    )
