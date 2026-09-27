from infinity_db.hacking_program_catalog import hacking_program_declaration_categories


def test_hacking_program_declarations_use_canonical_skill_categories() -> None:
    assert hacking_program_declaration_categories(["short", "aro"]) == [
        {"id": "short-skill", "name": "Short Skill"},
        {"id": "aro", "name": "ARO"},
    ]
    assert hacking_program_declaration_categories(["entire order"]) == [
        {"id": "long-skill", "name": "Long Skill"}
    ]


def test_unknown_hacking_program_declaration_remains_visible() -> None:
    assert hacking_program_declaration_categories(["Future Action"]) == [
        {"id": "unclassified", "name": "Future Action"}
    ]
