from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "infinity_db" / "web" / "static"
THEME_DIRECTORY = STATIC / "themes"
PRESENTATION_RULES = "".join(
    (STATIC / filename).read_text(encoding="utf-8")
    for filename in ("foundation.css", "components.css", "page-overrides.css")
)
THEME_STARTUP = (
    ROOT / "src" / "infinity_db" / "web" / "static" / "theme-startup.js"
).read_text(encoding="utf-8")

NORMAL_TEXT_MINIMUM = 4.5
NON_TEXT_MINIMUM = 3.0

DEFAULT_SURFACE_TEXT = (
    "color-text-primary",
    "color-text-heading",
    "color-data-group-emphasis",
    "color-data-emphasis",
    "color-text-control",
    "color-text-detail",
    "color-text-label",
    "color-text-data-label",
    "color-text-secondary",
    "color-text-tertiary",
    "color-text-technical",
    "color-control-text",
    "color-control-placeholder",
    "color-text-accent",
    "color-text-accent-strong",
    "color-text-action-subtle",
    "color-text-action-subtle-hover",
    "color-text-rule-heading",
    "color-text-index",
    "color-text-sort-label",
    "color-text-sort-direction",
    "color-text-footer",
    "color-text-footer-strong",
    "color-profile-attachment",
    "color-profile-stat-label",
    "color-profile-stat-value",
    "color-profile-characteristics",
    "color-profile-availability",
)

TEXT_CONTRAST_PAIRS = (
    ("table heading", "color-text-table-heading", "color-surface-data-header"),
    ("primary link", "color-action-primary", "color-surface-default"),
    ("hover link", "color-link-hover", "color-surface-default"),
    ("landing/about accent", "color-accent", "color-surface-page"),
    ("landing index", "color-text-accent-muted", "color-surface-raised"),
    ("landing action mark", "color-text-accent-subtle", "color-surface-raised"),
    ("inverse text", "color-text-on-inverse", "color-surface-inverse"),
    ("inverse muted text", "color-text-on-inverse-muted", "color-surface-inverse"),
    ("inverse accent text", "color-text-on-inverse-accent", "color-surface-inverse"),
    ("inverse strong text", "color-text-on-inverse-strong", "color-surface-inverse"),
    ("inverse detail text", "color-text-on-inverse-detail", "color-surface-inverse"),
    ("sidebar accent text", "color-inverse-accent", "color-nav-surface"),
    ("inverse accent action", "color-text-on-inverse-action", "color-inverse-accent"),
    ("navigation text", "color-nav-text", "color-nav-surface"),
    ("navigation muted text", "color-nav-text-muted", "color-nav-surface"),
    ("navigation active text", "color-nav-text-active", "color-nav-surface"),
    ("navigation detail text", "color-nav-text-detail", "color-nav-surface"),
    ("settings choice text", "color-nav-choice-muted", "color-nav-control-surface"),
    ("primary button", "color-text-on-action", "color-action-primary"),
    ("warning status", "color-status-warning-text", "color-status-warning-surface"),
    (
        "default availability badge",
        "color-availability-default-text",
        "color-availability-default-surface",
    ),
    (
        "mercenary availability badge",
        "color-availability-mercs-text",
        "color-availability-mercs-surface",
    ),
    (
        "Spec-Ops availability badge",
        "color-availability-specops-text",
        "color-availability-specops-surface",
    ),
    (
        "TeamPro availability badge",
        "color-availability-teamops-text",
        "color-availability-teamops-surface",
    ),
    (
        "Reinforcement availability badge",
        "color-availability-reinforcement-text",
        "color-availability-reinforcement-surface",
    ),
    (
        "profile characteristic fallback",
        "color-profile-fallback-text",
        "color-profile-fallback-surface",
    ),
    ("Army tag", "color-army-tag-text", "color-army-tag-surface"),
    ("neutral range modifier", "color-text-on-emphasis", "color-range-neutral"),
    ("positive range modifier", "color-text-on-emphasis", "color-range-positive"),
    ("caution range modifier", "color-text-on-caution", "color-range-caution"),
    ("negative range modifier", "color-text-on-emphasis", "color-range-negative"),
    ("Surface division badge", "color-text-on-emphasis", "color-division-surface"),
    ("Deep Space division badge", "color-text-on-emphasis", "color-division-deepspace"),
    ("unclassified Skill badge", "color-text-secondary", "color-surface-data-header"),
    ("Automatic Skill badge", "color-skill-category-on-dark", "color-skill-category-automatic"),
    (
        "Deployment Skill badge",
        "color-skill-category-on-dark",
        "color-skill-category-deployment",
    ),
    (
        "Basic Short Skill badge",
        "color-skill-category-on-dark",
        "color-skill-category-basic-short",
    ),
    ("Short Skill badge", "color-skill-category-on-dark", "color-skill-category-short"),
    ("Long Skill badge", "color-skill-category-on-dark", "color-skill-category-long"),
    ("ARO Skill badge", "color-skill-category-on-aro", "color-skill-category-aro"),
)

NON_TEXT_CONTRAST_PAIRS = (
    ("focus ring on page", "color-focus-ring", "color-surface-page"),
    ("focus ring on default surface", "color-focus-ring", "color-surface-default"),
    ("focus ring in navigation", "color-focus-ring", "color-nav-surface"),
    (
        "warning status indicator",
        "color-status-warning-indicator",
        "color-status-warning-surface",
    ),
    ("loading spinner", "color-spinner-active", "color-spinner-track"),
    ("extended profile accent", "color-profile-accent", "color-surface-default"),
    (
        "subordinate profile accent",
        "color-profile-accent-subordinate",
        "color-surface-default",
    ),
    ("state symbol", "color-state-symbol-text", "color-state-symbol-surface"),
)


def _registered_explicit_themes() -> tuple[str, ...]:
    values = re.findall(r'Object\.freeze\(\{ value: "([^"]+)", label:', THEME_STARTUP)
    assert values and values[0] == "system"
    return tuple(value for value in values if value != "system")


def _theme_source(theme: str) -> str:
    return (THEME_DIRECTORY / f"{theme}.css").read_text(encoding="utf-8")


def _theme_tokens(theme: str) -> dict[str, str]:
    source = _theme_source(theme)
    marker = f':root[data-theme="{theme}"]'
    marker_start = source.index(marker)
    opening = source.index("{", marker_start)
    depth = 1
    cursor = opening + 1
    while depth:
        if source[cursor] == "{":
            depth += 1
        elif source[cursor] == "}":
            depth -= 1
        cursor += 1
    body = source[opening + 1 : cursor - 1]
    return {
        name: value.strip()
        for name, value in re.findall(r"--([\w-]+):\s*([^;]+);", body)
    }


def _resolve_token(tokens: dict[str, str], name: str) -> str:
    value = tokens[name]
    seen = {name}
    while match := re.fullmatch(r"var\(--([\w-]+)\)", value):
        name = match.group(1)
        if name in seen:
            raise AssertionError(f"Theme token cycle includes --{name}")
        seen.add(name)
        value = tokens[name]
    return value


def _rgb(value: str) -> tuple[float, float, float]:
    match = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", value)
    assert match is not None, f"Audited theme color must resolve to opaque hex, got {value!r}"
    digits = match.group(1)
    if len(digits) == 3:
        digits = "".join(character * 2 for character in digits)
    return (
        int(digits[0:2], 16) / 255,
        int(digits[2:4], 16) / 255,
        int(digits[4:6], 16) / 255,
    )


def _relative_luminance(value: str) -> float:
    def linearize(channel: float) -> float:
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linearize(channel) for channel in _rgb(value))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast_ratio(tokens: dict[str, str], foreground: str, background: str) -> float:
    foreground_luminance = _relative_luminance(_resolve_token(tokens, foreground))
    background_luminance = _relative_luminance(_resolve_token(tokens, background))
    lighter = max(foreground_luminance, background_luminance)
    darker = min(foreground_luminance, background_luminance)
    return (lighter + 0.05) / (darker + 0.05)


def _assert_contrast_pairs(
    theme: str,
    tokens: dict[str, str],
    pairs: tuple[tuple[str, str, str], ...],
    minimum: float,
) -> None:
    failures: list[str] = []
    for label, foreground, background in pairs:
        ratio = _contrast_ratio(tokens, foreground, background)
        if ratio < minimum:
            failures.append(
                f"{label}: {ratio:.2f}:1 (--{foreground} on --{background}, needs {minimum:.1f}:1)"
            )
    assert not failures, f"{theme} theme contrast failures:\n" + "\n".join(failures)


def test_registered_explicit_themes_have_one_palette_file_each() -> None:
    registered = set(_registered_explicit_themes())
    palette_files = {path.stem for path in THEME_DIRECTORY.glob("*.css")}

    assert registered == palette_files


def test_every_explicit_theme_meets_compact_text_contrast_contract() -> None:
    for theme in _registered_explicit_themes():
        tokens = _theme_tokens(theme)
        default_pairs = tuple(
            (name, name, "color-surface-default") for name in DEFAULT_SURFACE_TEXT
        )
        _assert_contrast_pairs(
            theme,
            tokens,
            default_pairs + TEXT_CONTRAST_PAIRS,
            NORMAL_TEXT_MINIMUM,
        )


def test_every_explicit_theme_meets_non_text_contrast_contract() -> None:
    for theme in _registered_explicit_themes():
        _assert_contrast_pairs(
            theme,
            _theme_tokens(theme),
            NON_TEXT_CONTRAST_PAIRS,
            NON_TEXT_MINIMUM,
        )



def test_scenario_map_semantic_colors_meet_theme_contrast_contract() -> None:
    for theme in _registered_explicit_themes():
        tokens = _theme_tokens(theme)
        text_pairs = tuple(
            (
                f"scenario map text on {surface}",
                "color-scenario-map-text",
                f"color-scenario-map-{surface}",
            )
            for surface in ("table", "deployment-a", "deployment-b", "scoring", "marker")
        )
        edge_pairs = tuple(
            (
                f"scenario map {edge} on {surface}",
                f"color-scenario-map-{edge}",
                f"color-scenario-map-{surface}",
            )
            for edge, surface in (
                ("outline", "table"),
                ("deployment-a-edge", "deployment-a"),
                ("deployment-b-edge", "deployment-b"),
                ("scoring-edge", "scoring"),
                ("guide", "table"),
                ("measurement", "table"),
            )
        )
        _assert_contrast_pairs(theme, tokens, text_pairs, NORMAL_TEXT_MINIMUM)
        _assert_contrast_pairs(theme, tokens, edge_pairs, NON_TEXT_MINIMUM)


def test_faction_accents_remain_supplementary_in_every_explicit_theme() -> None:
    theme_sources = "".join(
        _theme_source(theme) for theme in _registered_explicit_themes()
    )
    faction_names = {
        match.group(1)
        for match in re.finditer(r"--color-faction-([\w-]+)-primary:", theme_sources)
    }
    assert faction_names
    assert "color: var(--color-faction-" not in PRESENTATION_RULES

    for theme in _registered_explicit_themes():
        tokens = _theme_tokens(theme)
        for faction in faction_names:
            primary = _resolve_token(tokens, f"color-faction-{faction}-primary")
            secondary = _resolve_token(tokens, f"color-faction-{faction}-secondary")
            assert primary != secondary, f"{theme} theme collapses {faction} faction accents"
