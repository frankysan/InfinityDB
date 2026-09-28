"""Validated pytest section configuration used by local development checks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "testing" / "test-sections.json"


@dataclass(frozen=True)
class TestSection:
    name: str
    description: str
    modules: frozenset[str]

    @property
    def marker(self) -> str:
        return f"section_{self.name}"


def load_test_sections(path: Path = DEFAULT_CONFIG_PATH) -> dict[str, TestSection]:
    """Load and validate the maintained test-section map."""

    document: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if document.get("version") != 1:
        raise ValueError(f"Unsupported test-section config version in {path}")
    raw_sections = document.get("sections")
    if not isinstance(raw_sections, dict) or not raw_sections:
        raise ValueError(f"Test-section config requires a non-empty sections object: {path}")

    sections: dict[str, TestSection] = {}
    assigned: dict[str, str] = {}
    for name, raw_section in raw_sections.items():
        if not isinstance(name, str) or not name.isidentifier():
            raise ValueError(f"Invalid test-section name {name!r} in {path}")
        if not isinstance(raw_section, dict):
            raise ValueError(f"Test section {name!r} must be an object in {path}")
        description = raw_section.get("description")
        modules = raw_section.get("modules")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"Test section {name!r} requires a description in {path}")
        if not isinstance(modules, list) or not modules:
            raise ValueError(f"Test section {name!r} requires modules in {path}")
        if not all(isinstance(module, str) and module.startswith("test_") for module in modules):
            raise ValueError(f"Test section {name!r} contains an invalid module name in {path}")
        if len(modules) != len(set(modules)):
            raise ValueError(f"Test section {name!r} contains duplicate modules in {path}")
        for module in modules:
            previous = assigned.get(module)
            if previous is not None:
                raise ValueError(
                    f"Test module {module!r} is assigned to both {previous!r} and {name!r}"
                )
            assigned[module] = name
        sections[name] = TestSection(
            name=name,
            description=description.strip(),
            modules=frozenset(modules),
        )
    return sections


def section_for_module(module_name: str, sections: dict[str, TestSection]) -> TestSection | None:
    """Return the configured section for one test module name."""

    for section in sections.values():
        if module_name in section.modules:
            return section
    return None
