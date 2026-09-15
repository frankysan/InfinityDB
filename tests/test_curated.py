import json
from pathlib import Path

import pytest

from infinity_db.curated import load_curated_document


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