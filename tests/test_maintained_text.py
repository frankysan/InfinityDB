from pathlib import Path

import pytest

from infinity_db.curated import load_curated_directory, load_curated_document
from infinity_db.maintained_text import parse_maintained_text
from infinity_db.maintained_text_policy import (
    collect_review_needed_markers,
    collect_reviewed_batch_residuals,
    collect_unlinked_reference_candidates,
    validate_maintained_text_link_baseline,
    validate_reviewed_batch_coverage,
)
from infinity_db.rules_database import export_rules_database


def test_maintained_text_parser_preserves_text_references_distances_and_escapes() -> None:
    tokens = parse_maintained_text(
        r"Use [[skill:jump]] or [[skill:dodge:plural|Dodge Skills]] with "
        r"[[attribute:mov|MOV]] within [[distance:+2:inch]]; write \[[literal]] "
        r"for documentation."
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
        {"type": "text", "text": " with "},
        {
            "type": "reference",
            "target": "attribute:mov",
            "display_text": "MOV",
        },
        {"type": "text", "text": " within "},
        {"type": "distance", "centimeters": 5, "positive_sign": True},
        {"type": "text", "text": "; write [[literal]] for documentation."},
    ]


def test_maintained_text_parser_preserves_explicit_review_markers() -> None:
    tokens = parse_maintained_text(
        "Check [[review-needed:ambiguous-target|HoloMask]] and "
        "[[review-needed:source-meaning-unclear]]."
    )

    assert tokens == [
        {"type": "text", "text": "Check "},
        {
            "type": "review-needed",
            "reason": "ambiguous-target",
            "text": "HoloMask",
        },
        {"type": "text", "text": " and "},
        {"type": "review-needed", "reason": "source-meaning-unclear"},
        {"type": "text", "text": "."},
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
        ("[[review-needed:]]", "must include a reason"),
        ("[[review-needed:Ambiguous]]", "lowercase kebab-case"),
        ("[[review-needed:ambiguous-target| ]]", "display text must not be empty"),
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


def test_project_maintained_text_link_baseline_is_current() -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    baseline = root / "data" / "curated" / "maintained-text-link-baseline.json"

    validate_maintained_text_link_baseline(documents, baseline)


def test_project_completed_maintained_text_batches_have_no_plain_residuals() -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    review_policy = root / "data" / "curated" / "maintained-text-link-reviews.json"

    assert collect_reviewed_batch_residuals(documents, review_policy) == {}
    validate_reviewed_batch_coverage(documents, review_policy)


def test_rules_database_rejects_new_unlinked_semantic_reference(tmp_path: Path) -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    document_path, document = documents[0]
    document = {**document, "records": [dict(record) for record in document["records"]]}
    document["records"][0]["summary"] += " Jump."
    documents[0] = (document_path, document)

    with pytest.raises(ValueError, match="semantic-link coverage changed"):
        export_rules_database(documents, tmp_path / "rules.db", finalize=False)


def test_canonical_state_names_are_semantic_links() -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    candidates = collect_unlinked_reference_candidates(documents)

    remaining = [
        (text, targets)
        for values in candidates.values()
        for (_, text, targets), count in values.items()
        for _ in range(count)
        if text.endswith(" State") and any(target.startswith("state:") for target in targets)
    ]
    assert remaining == []


def test_hacking_program_names_are_semantic_links() -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    candidates = collect_unlinked_reference_candidates(documents)

    remaining = [
        (text, targets)
        for values in candidates.values()
        for (_, text, targets), count in values.items()
        for _ in range(count)
        if any(target.startswith("hacking-program:") for target in targets)
    ]
    assert remaining == []


def test_equipment_names_are_semantic_links() -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    candidates = collect_unlinked_reference_candidates(documents)

    remaining = [
        (text, targets)
        for values in candidates.values()
        for (_, text, targets), count in values.items()
        for _ in range(count)
        if any(target.startswith("equipment:") for target in targets)
    ]
    assert remaining == []


def test_unlinked_reference_candidates_use_aliases_longest_match_and_ignore_tokens() -> None:
    document = {
        "collection": {"id": "test", "status": "current"},
        "skillTypes": [],
        "labels": [],
        "records": [
            {
                "id": "skill:jump",
                "kind": "skill",
                "name": "Jump",
                "summary": "Jump definition.",
            },
            {
                "id": "skill:suppressive-fire",
                "kind": "skill",
                "name": "Suppressive Fire",
                "summary": "Suppressive Fire definition.",
            },
            {
                "id": "state:suppressive-fire",
                "kind": "state",
                "name": "Suppressive Fire State",
                "aliases": ["Suppressive Fire"],
                "summary": "Suppressive Fire State definition.",
            },
            {
                "id": "state:unconscious",
                "kind": "state",
                "name": "Unconscious State",
                "aliases": ["Unconscious"],
                "summary": "Unconscious State definition.",
            },
            {
                "id": "rule:test",
                "kind": "rule",
                "name": "Test",
                "summary": (
                    "Jump, Suppressive Fire, [[skill:jump|Jump]], and Unconscious State."
                ),
            },
        ],
    }

    candidates = collect_unlinked_reference_candidates([(Path("test.json"), document)])
    values = candidates["test|rule:test"]

    assert values[("summary", "Jump", ("skill:jump",))] == 1
    assert values[
        (
            "summary",
            "Suppressive Fire",
            ("skill:suppressive-fire", "state:suppressive-fire"),
        )
    ] == 1
    assert values[("summary", "Unconscious State", ("state:unconscious",))] == 1
    assert sum(values.values()) == 3


def test_reviewed_batch_audit_catches_case_and_plural_omissions(
    tmp_path: Path,
) -> None:
    policy = tmp_path / "maintained-text-link-reviews.json"
    policy.write_text(
        """{
  "formatVersion": 1,
  "policy": "reviewed-maintained-text-link-batches",
  "batches": [
    {
      "id": "equipment",
      "namespace": "equipment",
      "includeAliases": true,
      "includeSimplePlurals": true,
      "caseInsensitive": true,
      "reviewedOn": "2026-09-29"
    }
  ]
}
""",
        encoding="utf-8",
    )
    document = {
        "collection": {"id": "test", "status": "current"},
        "skillTypes": [],
        "labels": [],
        "records": [
            {
                "id": "equipment:multispectral-visor",
                "kind": "equipment",
                "name": "Multispectral Visor",
                "summary": "Definition.",
            },
            {
                "id": "rule:test",
                "kind": "rule",
                "name": "Test",
                "summary": "MULTISPECTRAL VISORS are visible here.",
            },
        ],
    }
    documents = [(Path("test.json"), document)]

    residuals = collect_reviewed_batch_residuals(documents, policy)
    assert residuals["test|rule:test"][
        (
            "equipment",
            "summary",
            "MULTISPECTRAL VISORS",
            ("equipment:multispectral-visor",),
        )
    ] == 1

    document["records"][1]["summary"] = (
        "[[review-needed:ambiguous-target|MULTISPECTRAL VISORS]] are visible here."
    )
    assert collect_reviewed_batch_residuals(documents, policy) == {}


def test_review_needed_markers_are_explicit_and_excluded_from_unlinked_candidates() -> None:
    root = Path(__file__).parents[1]
    documents = load_curated_directory(root / "data" / "curated")
    candidates = collect_unlinked_reference_candidates(documents)
    review_needed = collect_review_needed_markers(documents)

    remaining_holomask = [
        (owner, field, text, targets)
        for owner, values in candidates.items()
        for (field, text, targets), count in values.items()
        for _ in range(count)
        if text == "HoloMask"
    ]
    assert remaining_holomask == []

    assert review_needed["n5-core-v5.3|state:retreat"][
        ("facts.effects[]", "ambiguous-target", "HoloMask")
    ] == 1
    assert review_needed["n5-core-v5.3|state:holomask"][
        ("facts.restrictions[]", "ambiguous-target", "HoloMask")
    ] == 1
