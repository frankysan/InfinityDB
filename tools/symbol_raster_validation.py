"""Raster comparison for optional read-only symbol parity verification."""

from __future__ import annotations

import math
import subprocess
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

try:
    Image: Any = import_module("PIL.Image")
    ImageChops: Any = import_module("PIL.ImageChops")
    ImageStat: Any = import_module("PIL.ImageStat")
except ModuleNotFoundError:
    Image = None
    ImageChops = None
    ImageStat = None


def require_pillow() -> None:
    if Image is None or ImageChops is None or ImageStat is None:
        raise RuntimeError(
            "Missing dependency: Pillow. Install InfinityDB with the 'symbols' extra."
        )


@dataclass
class VisualMetrics:
    worst_rms: float = 0.0
    worst_changed_fraction: float = 0.0
    worst_size: int = 0
    worst_dpr: float = 0.0
    worst_background: str = ""


def run_command(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
    )


def get_tool_version(command: str) -> str:
    result = run_command([command, "--version"])
    text = (result.stdout or result.stderr).strip()
    return text.splitlines()[0] if text else "unknown"


def render_png(
    renderer: str,
    executable: str,
    source: Path,
    destination: Path,
    width_px: int,
) -> tuple[bool, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)

    if renderer == "resvg":
        command = [
            executable,
            "--quiet",
            "--width", str(width_px),
            str(source),
            str(destination),
        ]
    elif renderer == "inkscape":
        command = [
            executable,
            str(source),
            "--export-type=png",
            f"--export-filename={destination}",
            f"--export-width={width_px}",
            "--export-background-opacity=0",
            "--export-overwrite",
        ]
    else:
        return False, f"Unknown renderer: {renderer}"

    result = run_command(command)

    if result.returncode != 0:
        return False, (result.stderr or result.stdout).strip()

    if not destination.exists():
        return False, f"{renderer} returned success but did not create PNG."

    return True, ""


def composite_on_background(image: Any, value: int) -> Any:
    image = image.convert("RGBA")
    bg = Image.new("RGBA", image.size, (value, value, value, 255))
    return Image.alpha_composite(bg, image).convert("RGB")


def compare_rgb_images(
    reference: Any,
    candidate: Any,
    pixel_diff_threshold: int,
) -> tuple[float, float]:
    if reference.size != candidate.size:
        return 1.0, 1.0

    diff = ImageChops.difference(reference, candidate)

    stat = ImageStat.Stat(diff)
    # RMS across RGB channels, normalized to [0,1].
    channel_rms = stat.rms[:3]
    rms = math.sqrt(sum(v * v for v in channel_rms) / 3.0) / 255.0

    changed = 0
    total = reference.width * reference.height

    pixels = (
        diff.get_flattened_data()
        if hasattr(diff, "get_flattened_data")
        else diff.getdata()
    )
    for pixel in pixels:
        if max(pixel) > pixel_diff_threshold:
            changed += 1

    changed_fraction = changed / total if total else 0.0
    return rms, changed_fraction


def compare_pngs(
    reference_png: Path,
    candidate_png: Path,
    pixel_diff_threshold: int,
) -> tuple[float, float, str]:
    require_pillow()
    with Image.open(reference_png) as rimg, Image.open(candidate_png) as cimg:
        worst_rms = 0.0
        worst_changed = 0.0
        worst_bg = ""

        for name, value in (("black", 0), ("white", 255)):
            ref = composite_on_background(rimg, value)
            cand = composite_on_background(cimg, value)

            rms, changed = compare_rgb_images(
                ref,
                cand,
                pixel_diff_threshold,
            )

            # Track the background producing the stronger normalized error.
            score = max(rms, changed)
            old_score = max(worst_rms, worst_changed)

            if score >= old_score:
                worst_rms = max(worst_rms, rms)
                worst_changed = max(worst_changed, changed)
                worst_bg = name
            else:
                worst_rms = max(worst_rms, rms)
                worst_changed = max(worst_changed, changed)

        return worst_rms, worst_changed, worst_bg


class RasterValidator:
    def __init__(
        self,
        renderer: str,
        executable: str,
        reference_svg: Path,
        temp_root: Path,
        target_sizes: list[int],
        dprs: list[float],
        max_rms: float,
        max_changed_fraction: float,
        pixel_diff_threshold: int,
    ):
        self.renderer = renderer
        self.executable = executable
        self.reference_svg = reference_svg
        self.temp_root = temp_root
        self.target_sizes = target_sizes
        self.dprs = dprs
        self.max_rms = max_rms
        self.max_changed_fraction = max_changed_fraction
        self.pixel_diff_threshold = pixel_diff_threshold

        self.reference_pngs: dict[tuple[int, float], Path] = {}

    def prepare_reference(self) -> tuple[bool, str]:
        for css_size in self.target_sizes:
            for dpr in self.dprs:
                width_px = max(1, round(css_size * dpr))
                key = (css_size, dpr)

                png = self.temp_root / "reference" / f"{css_size}px-{dpr:g}x.png"

                ok, error = render_png(
                    self.renderer,
                    self.executable,
                    self.reference_svg,
                    png,
                    width_px,
                )

                if not ok:
                    return False, (
                        f"Could not render reference at "
                        f"{css_size}px/{dpr:g}x: {error}"
                    )

                self.reference_pngs[key] = png

        return True, ""

    def validate(self, candidate_svg: Path, candidate_name: str) -> tuple[bool, VisualMetrics, str]:
        metrics = VisualMetrics()

        for css_size in self.target_sizes:
            for dpr in self.dprs:
                width_px = max(1, round(css_size * dpr))
                key = (css_size, dpr)

                candidate_png = (
                    self.temp_root
                    / "candidates"
                    / candidate_name
                    / f"{css_size}px-{dpr:g}x.png"
                )

                ok, error = render_png(
                    self.renderer,
                    self.executable,
                    candidate_svg,
                    candidate_png,
                    width_px,
                )

                if not ok:
                    return False, metrics, (
                        f"Could not render candidate at "
                        f"{css_size}px/{dpr:g}x: {error}"
                    )

                rms, changed, bg = compare_pngs(
                    self.reference_pngs[key],
                    candidate_png,
                    self.pixel_diff_threshold,
                )

                if (
                    rms > metrics.worst_rms
                    or changed > metrics.worst_changed_fraction
                ):
                    metrics.worst_rms = max(metrics.worst_rms, rms)
                    metrics.worst_changed_fraction = max(
                        metrics.worst_changed_fraction,
                        changed,
                    )
                    metrics.worst_size = css_size
                    metrics.worst_dpr = dpr
                    metrics.worst_background = bg

                if (
                    rms > self.max_rms
                    or changed > self.max_changed_fraction
                ):
                    return False, metrics, ""

        return True, metrics, ""
