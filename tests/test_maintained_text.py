from pathlib import Path

import pytest

from infinity_db.curated import load_curated_directory, load_curated_document
from infinity_db.maintained_text import parse_maintained_text
from infinity_db.rules_database import export_rules_database


def test_maintained_text_parser_preserves_text_references_distances_and_escapes() -> None:
    tokens = parse_maintained_text(
        r"Use [[skill:jump]] or [[skill:dodge:plural|Dodge Skills]] within "
        r"[[distance:+2:inch]]; write \[[literal]] for documentation."
    )

    assert tokens == [
        {"type": "text", "text": "Use "},
        {"type": "reference", "target": "skill:jump"},
        {"type": "text", "text": " or "},
        {
            "type": "reference",
            "target": "skill:dodge",
            "display_form": "plural",
            "display_text": "Dodge Skills",
        },
        {"type": "text", "text": " within "},
        {"type": "distance", "centimeters": 5, "positive_sign": True},
        {"type": "text", "text": "; write [[literal]] for documentation."},
    ]


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("Broken [[skill:jump", "unclosed"),
        ("Broken ]] token", "unmatched"),
        ("[[unknown:thing]]", "unsupported maintained-text reference namespace"),
        ("[[distance:two:inch]]", "distance token must use"),
        ("[[distance:-2:inch]]", "distance values must be nonnegative"),
        ("[[skill:jump| ]]", "display text must not be empty"),
    ],
)
def test_maintained_text_parser_rejects_invalid_tokens(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_maintained_text(text)


def test_curated_rules_require_typed_distance_tokens(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    source = root / "data" / "curated" / "rules" / "n5-core-v5.3.json"
    document = source.read_text(encoding="utf-8")
    document = document.replace(
        "[[distance:2:inch]]",
        "2 inches",
        1,
    )
    path = tmp_path / source.name
    path.write_text(document, encoding="utf-8")

    with pytest.raises(ValueError, match="must use a .*distance"):
        load_curated_document(path)


def test_rules_database_rejects_unresolved_maintained_text_reference(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    document_path, document = documents[0]
    document = {**document, "records": [dict(record) for record in document["records"]]}
    document["records"][0]["summary"] += " [[skill:not-a-current-skill]]"
    documents[0] = (document_path, document)

    with pytest.raises(ValueError, match="does not resolve to a current semantic record"):
        export_rules_database(documents, tmp_path / "rules.db", finalize=False)
