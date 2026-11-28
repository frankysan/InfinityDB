"""Contrast-aware faction palettes inspired by Army, emblems and studio paint schemes."""

from __future__ import annotations

import itertools
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

ThemeMode = Literal["light", "dark"]
DEFAULT_PALETTE = "infinitydb"

# Numerical Army IDs, canonical source slugs and player-facing labels.
# Army identity colors and separately authored appearance seeds are owned by
# themes/light.css; only the latter determine the optional theme appearance.
ARMY_THEMES = (
    (101, "panoceania", "PanOceania"),
    (201, "yu-jing", "Yu Jing"),
    (301, "ariadna", "Ariadna"),
    (401, "haqqislam", "Haqqislam"),
    (501, "nomads", "Nomads"),
    (601, "combined-army", "Combined Army"),
    (701, "aleph", "ALEPH"),
    (801, "tohaa", "Tohaa"),
    (901, "non-aligned-armies", "Non-Aligned Armies"),
    (1001, "o-12", "O-12"),
    (1101, "jsa", "JSA"),
)
PALETTE_IDS = frozenset((DEFAULT_PALETTE, *(slug for _, slug, _ in ARMY_THEMES)))

_THEME_DIRECTORY = Path(__file__).resolve().parent / "web" / "static" / "themes"
_TOKEN_RE = re.compile(r"--([\w-]+):\s*([^;]+);")
_HEX_RE = re.compile(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?")
_WEIGHTS = (0.2126, 0.7152, 0.0722)
_RGB = tuple[float, float, float]

# These roles encode game meaning, not the user's visual identity. Map table
# and measurement roles may be tinted; deployment and scoring roles must not.
_SEMANTIC_PREFIXES = (
    "color-faction-",
    "color-skill-category-",
    "color-status-",
    "color-range-",
    "color-division-",
    "color-availability-",
    "color-scenario-map-deployment-",
    "color-scenario-map-scoring",
)
_SEMANTIC_ROLES = {"color-text-on-emphasis", "color-text-on-caution"}
_PRIMARY_ROLES = (
    "color-action-",
    "color-link-",
    "color-accent",
    "color-text-accent",
    "color-text-action-",
    "color-focus-",
    "color-inverse-accent",
    "color-nav-indicator",
    "color-nav-text-active",
    "color-nav-status-",
    "color-switch-checked-",
    "color-switch-choice-checked-",
    "color-spinner-active",
    "color-profile-accent",
    "color-logo-ribbon-",
    "color-logo-rim-",
    "color-text-on-inverse-accent",
    "color-text-rule-heading",
)
_CHROME_ROLES = ("color-nav-", "color-switch-", "color-brand-border", "color-surface-inverse")

# Keep light content cards nearly white, but give the larger page surface
# a visible hue. Dark cards also need separation from the page background.
_SURFACE_LUMINANCE = {
    "light": {"color-surface-page": 0.82, "color-surface-data-header": 0.89,
              "color-surface-toolbar": 0.89},
    "dark": {
        "color-surface-page": 0.012, "color-surface-default": 0.026,
        "color-surface-subtle": 0.033, "color-surface-raised": 0.031,
        "color-surface-data-header": 0.035, "color-surface-toolbar": 0.035,
        "color-surface-accent": 0.044, "color-surface-control-hover": 0.042,
        "color-surface-interactive-hover": 0.039,
    },
}


def palette_options() -> list[dict[str, str]]:
    """Ordered, public selector options shared by first paint and the backend."""
    return [
        {"value": DEFAULT_PALETTE, "label": "InfinityDB"},
        *({"value": slug, "label": label} for _, slug, label in ARMY_THEMES),
    ]


@lru_cache(maxsize=2)
def _base_tokens(mode: ThemeMode) -> dict[str, str]:
    return dict(_TOKEN_RE.findall((_THEME_DIRECTORY / f"{mode}.css").read_text(encoding="utf-8")))


def _linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def _srgb(channel: float) -> float:
    return 12.92 * channel if channel <= 0.0031308 else 1.055 * channel ** (1 / 2.4) - 0.055


def _rgb(value: str) -> _RGB:
    digits = value.removeprefix("#")
    if len(digits) == 3:
        digits = "".join(character * 2 for character in digits)
    return (
        _linear(int(digits[0:2], 16) / 255),
        _linear(int(digits[2:4], 16) / 255),
        _linear(int(digits[4:6], 16) / 255),
    )


def _luminance(rgb: _RGB) -> float:
    return sum(channel * weight for channel, weight in zip(rgb, _WEIGHTS, strict=True))


def _seed_at_luminance(seed: _RGB, target: float) -> _RGB:
    """Mix a source color toward black/white in linear RGB at a target luminance."""
    current = _luminance(seed)
    if current > target:
        amount = target / current
        return (seed[0] * amount, seed[1] * amount, seed[2] * amount)
    if current < target:
        amount = (target - current) / (1 - current)
        return (
            seed[0] + (1 - seed[0]) * amount,
            seed[1] + (1 - seed[1]) * amount,
            seed[2] + (1 - seed[2]) * amount,
        )
    return seed


def _quantize(rgb: _RGB, luminance: float) -> str:
    """Choose the nearest 8-bit neighbors that best preserve relative luminance."""
    channels = tuple(max(0.0, min(255.0, _srgb(channel) * 255)) for channel in rgb)
    neighbors = tuple((math.floor(channel), math.ceil(channel)) for channel in channels)

    def score(candidate: tuple[int, ...]) -> tuple[float, float]:
        red, green, blue = candidate
        actual = _luminance((_linear(red / 255), _linear(green / 255), _linear(blue / 255)))
        return abs(actual - luminance), sum(
            (value - channel) ** 2 for value, channel in zip(candidate, channels, strict=True)
        )

    closest = min(itertools.product(*neighbors), key=score)
    return "#" + "".join(f"{channel:02x}" for channel in closest)


def _tint(value: str, seed: _RGB, strength: float, *, target: float | None = None) -> str:
    if target is None:
        target = _luminance(_rgb(value))
    red, green, blue = _seed_at_luminance(seed, target)
    rgb = (
        target + strength * (red - target),
        target + strength * (green - target),
        target + strength * (blue - target),
    )
    return _quantize(rgb, target)


@lru_cache(maxsize=2 * len(PALETTE_IDS))
def theme_tokens(mode: ThemeMode, palette: str = DEFAULT_PALETTE) -> dict[str, str]:
    """Resolve the same semantic palette for browser CSS and standalone maps."""
    if mode not in {"light", "dark"}:
        raise ValueError("theme must be light or dark")
    if palette not in PALETTE_IDS:
        raise ValueError("unknown theme palette")
    base = _base_tokens(mode)
    if palette == DEFAULT_PALETTE:
        return dict(base)
    seeds = _base_tokens("light")
    accent, surface, chrome = (
        _rgb(seeds[f"appearance-{palette}-{role}"])
        for role in ("accent", "surface", "chrome")
    )
    result = dict(base)
    for name, value in base.items():
        if (
            not name.startswith("color-")
            or name.startswith(_SEMANTIC_PREFIXES)
            or name in _SEMANTIC_ROLES
            or not _HEX_RE.fullmatch(value)
        ):
            continue
        target = None
        if name.startswith(_PRIMARY_ROLES):
            seed, strength = accent, 1.0
            if mode == "light" and name == "color-accent":
                target = 0.135  # readable on the stronger page tint
        elif name.startswith(_CHROME_ROLES):
            seed, strength = chrome, 1.0
            if name.startswith("color-nav-surface") or name == "color-nav-control-surface":
                # A more visible faction-colored frame, including in dark mode.
                target = _luminance(_rgb(value))
                if palette == "nomads":
                    # Nomads use near-black chrome rather than a prominent faction tint.
                    if name == "color-nav-surface":
                        target = 0.014 if mode == "light" else 0.008
                    else:
                        target = max(target * 0.8, 0.024 if mode == "light" else 0.016)
                else:
                    target += 0.018 if mode == "light" else 0.012
            elif name == "color-nav-choice-muted":
                target = 0.44 if mode == "light" else 0.36
        else:
            seed, strength = surface, 0.35
            if ("surface" in name or "border" in name) and not name.startswith("color-text-"):
                strength = 1.0
            target = _SURFACE_LUMINANCE[mode].get(name)
        if (mode == "light" and name.startswith("color-text-")
                and not name.startswith("color-text-on-")
                and name != "color-text-separator"):
            # Normal page text, including muted labels, must remain readable
            # even outside the nearly white content cards.
            target = min(0.135, _luminance(_rgb(value))) if target is None else target
        result[name] = _tint(value, seed, strength, target=target)
    result["color-surface-translucent"] = result["color-surface-default"] + (
        "9e" if mode == "light" else "d1"
    )
    return result


@lru_cache(maxsize=1)
def army_palette_stylesheet() -> bytes:
    """Generate only palette overrides, leaving all component geometry shared."""
    blocks: list[str] = []
    for army_id, palette, label in ARMY_THEMES:
        blocks.append(f"/* Army {army_id}: {label} */\n")
        for mode in ("light", "dark"):
            base = theme_tokens(mode)
            tokens = theme_tokens(mode, palette)
            declarations = "".join(
                f"  --{name}: {value};\n" for name, value in tokens.items() if value != base[name]
            )
            blocks.append(
                f':root[data-theme="{mode}"][data-theme-palette="{palette}"] {{\n'
                + declarations + "}\n"
            )
    return "".join(blocks).encode("utf-8")
