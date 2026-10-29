from __future__ import annotations

from pathlib import Path

from tools.test_sections import load_test_sections, section_for_module


def test_test_section_config_covers_every_test_module_exactly_once() -> None:
    root = Path(__file__).resolve().parents[1]
    sections = load_test_sections()
    configured = {module for section in sections.values() for module in section.modules}
    discovered = {path.stem for path in (root / "tests").glob("test_*.py")}

    assert configured == discovered
    assert sum(len(section.modules) for section in sections.values()) == len(configured)


def test_test_section_markers_are_stable_and_named_from_sections() -> None:
    sections = load_test_sections()

    assert tuple(sections) == ("model", "web", "browser", "build", "ops", "assets")
    assert sections["browser"].marker == "section_browser"
    assert "test_verify_scenario_faq_browser" in sections["browser"].modules
    assert "test_verify_weapon_source_cards_browser" in sections["browser"].modules
    assert "test_verify_scenario_faq_browser" not in sections["web"].modules
    assert sections["model"].marker == "section_model"
    assert sections["web"].marker == "section_web"
    assert section_for_module("test_database", sections) == sections["model"]
    assert section_for_module("test_web", sections) == sections["web"]
    assert section_for_module("test_symbol_manifest", sections) == sections["assets"]
