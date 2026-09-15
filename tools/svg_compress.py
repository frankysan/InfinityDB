#!/usr/bin/env python3
"""
Display-aware SVG compression.

Profiles
--------
lossless
    Rendering/geometry-lossless SVG minification. Does not round coordinates.
    It does remove non-rendering cruft (comments, metadata/editor data, empty attrs)
    unless --lossless-minify-only is used.

balanced
    Production/default profile. Tries conservative SVGO numeric precisions in
    the requested order and stops at the first candidate that passes raster
    validation at all requested CSS sizes and DPRs. The default order is p2,p3:
    try the smaller p2 result first, then p3 only as a conservative rescue.

small
    Explicit aggressive profile. Tries a wider precision range. Optionally also
    tries Inkscape path simplification passes, and keeps the smallest candidate
    that passes the same visual validation.

all
    Produces all three profile trees. This is intentionally exhaustive and is
    slower than the default balanced profile.

Validation
----------
Reference and candidate SVGs are rasterized with the selected renderer
(Inkscape or resvg) at every combination of:
    --target-sizes  (CSS pixel widths)
    --dprs          (device-pixel ratios)

Each pair is compared after compositing onto BOTH black and white backgrounds,
which avoids treating invisible RGB values under transparent pixels as errors.

Requirements
------------
Python:
    pip install pillow

External:
    SVGO v4+:
        npm install -g svgo

    For visual validation, one of:
        resvg (default and recommended for speed)
        Inkscape

    Inkscape is still required only when --simplify-passes > 0.

Examples
--------
python svg_compress.py INPUT OUTPUT

# Exhaustive comparison of every profile (slower):
python svg_compress.py INPUT OUTPUT --profile all

python svg_compress.py INPUT OUTPUT ^
    --profile small ^
    --target-sizes 32,64,128 ^
    --dprs 1,2,3 ^
    --simplify-passes 1

The output path must be separate from the input path.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse
import csv
import gzip
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time

try:
    from PIL import Image, ImageChops, ImageStat
except ImportError:
    print(
        "Missing dependency: Pillow\n"
        "Install with: pip install pillow",
        file=sys.stderr,
    )
    sys.exit(2)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class VisualMetrics:
    worst_rms: float = 0.0
    worst_changed_fraction: float = 0.0
    worst_size: int = 0
    worst_dpr: float = 0.0
    worst_background: str = ""


@dataclass
class CandidateResult:
    file: str
    profile: str
    candidate: str
    precision: str
    simplify_passes: int
    bytes: int
    gzip_bytes: int
    passed: bool
    worst_rms: float
    worst_changed_fraction: float
    error: str = ""


@dataclass
class OutputResult:
    file: str
    profile: str
    status: str
    source_bytes: int
    output_bytes: int
    gzip_bytes: int
    reduction_percent: float
    chosen_candidate: str
    precision: str
    simplify_passes: int
    worst_rms: float
    worst_changed_fraction: float
    file_runtime_seconds: float = 0.0
    error: str = ""


@dataclass
class CandidateEvaluation:
    name: str
    precision: int | None
    simplify_passes: int
    path: Path | None
    passed: bool
    metrics: VisualMetrics
    error: str = ""
    renderer_failure: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_int_list(value: str) -> list[int]:
    result = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        number = int(part)
        if number <= 0:
            raise argparse.ArgumentTypeError("values must be > 0")
        result.append(number)
    if not result:
        raise argparse.ArgumentTypeError("at least one value is required")
    return sorted(set(result))


def parse_float_list(value: str) -> list[float]:
    result = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        number = float(part)
        if number <= 0:
            raise argparse.ArgumentTypeError("values must be > 0")
        result.append(number)
    if not result:
        raise argparse.ArgumentTypeError("at least one value is required")
    return sorted(set(result))


def parse_precision_list(value: str) -> list[int]:
    result = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        number = int(part)
        if not 0 <= number <= 20:
            raise argparse.ArgumentTypeError("precision must be between 0 and 20")
        result.append(number)
    if not result:
        raise argparse.ArgumentTypeError("at least one precision is required")
    # Preserve user order, because it is useful in reports.
    return list(dict.fromkeys(result))


def is_relative_to(path: Path, other: Path) -> bool:
    try:
        path.relative_to(other)
        return True
    except ValueError:
        return False


def run_command(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def file_gzip_size(path: Path) -> int:
    data = path.read_bytes()
    return len(gzip.compress(data, compresslevel=9, mtime=0))


def maybe_write_svgz(svg_path: Path):
    data = svg_path.read_bytes()
    svgz_path = svg_path.with_suffix(".svgz")
    svgz_path.write_bytes(gzip.compress(data, compresslevel=9, mtime=0))


def safe_reduction(source_bytes: int, output_bytes: int) -> float:
    if source_bytes <= 0:
        return 0.0
    return 100.0 * (1.0 - output_bytes / source_bytes)


def copy_if_smaller(source: Path, candidate: Path, destination: Path) -> tuple[Path, str]:
    """
    Write the smaller representation. Returns (chosen_source, label).
    """
    destination.parent.mkdir(parents=True, exist_ok=True)

    if candidate.exists() and candidate.stat().st_size < source.stat().st_size:
        shutil.copy2(candidate, destination)
        return candidate, "lossless-optimized"

    shutil.copy2(source, destination)
    return source, "original"


# ---------------------------------------------------------------------------
# Tool discovery
# ---------------------------------------------------------------------------

def find_inkscape(explicit: str | None) -> str | None:
    if explicit:
        p = Path(explicit)
        if p.exists():
            return str(p)
        found = shutil.which(explicit)
        if found:
            return found
        return None

    for name in ("inkscape.com", "inkscape"):
        found = shutil.which(name)
        if found:
            return found

    candidates = [
        Path(r"C:\Program Files\Inkscape\bin\inkscape.com"),
        Path(r"C:\Program Files\Inkscape\bin\inkscape.exe"),
        Path(r"C:\Program Files (x86)\Inkscape\bin\inkscape.com"),
        Path(r"C:\Program Files (x86)\Inkscape\bin\inkscape.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return None


def find_resvg(explicit: str | None) -> str | None:
    if explicit:
        p = Path(explicit)
        if p.exists():
            return str(p)
        found = shutil.which(explicit)
        if found:
            return found
        return None

    for name in ("resvg", "resvg.exe"):
        found = shutil.which(name)
        if found:
            return found

    return None


def find_svgo(explicit: str | None) -> str | None:
    if explicit:
        p = Path(explicit)
        if p.exists():
            return str(p)
        found = shutil.which(explicit)
        if found:
            return found
        return None

    for name in ("svgo", "svgo.cmd"):
        found = shutil.which(name)
        if found:
            return found

    return None


def get_tool_version(command: str) -> str:
    result = run_command([command, "--version"])
    text = (result.stdout or result.stderr).strip()
    return text.splitlines()[0] if text else "unknown"


# ---------------------------------------------------------------------------
# SVGO configuration and execution
# ---------------------------------------------------------------------------

LOSSLESS_CONFIG_MINIFY_ONLY = r"""
export default {
  multipass: true,
  js2svg: {
    pretty: false
  },
  plugins: []
};
""".strip()


LOSSLESS_CONFIG_CLEAN = r"""
export default {
  multipass: true,
  js2svg: {
    pretty: false
  },
  plugins: [
    "removeComments",
    "removeMetadata",
    "removeEditorsNSData",
    "removeEmptyAttrs",
    "sortAttrs"
  ]
};
""".strip()


LOSSY_CONFIG = r"""
export default {
  multipass: true,
  js2svg: {
    pretty: false
  },
  plugins: [
    {
      name: "preset-default",
      params: {
        overrides: {
          cleanupIds: false
        }
      }
    }
  ]
};
""".strip()


def write_config(directory: Path, name: str, text: str) -> Path:
    path = directory / name
    path.write_text(text + "\n", encoding="utf-8")
    return path


def run_svgo(
    svgo: str,
    source: Path,
    destination: Path,
    config: Path,
    precision: int | None = None,
) -> tuple[bool, str]:
    destination.parent.mkdir(parents=True, exist_ok=True)

    command = [
        svgo,
        "-i", str(source),
        "-o", str(destination),
        "--config", str(config),
        "--multipass",
        "--quiet",
    ]

    if precision is not None:
        command += ["--precision", str(precision)]

    result = run_command(command)

    if result.returncode != 0:
        return False, (result.stderr or result.stdout).strip()

    if not destination.exists():
        return False, "SVGO returned success but did not create output."

    return True, ""


# ---------------------------------------------------------------------------
# Inkscape rasterization and path simplification
# ---------------------------------------------------------------------------

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


def simplify_svg(
    inkscape: str,
    source: Path,
    destination: Path,
    passes: int,
) -> tuple[bool, str]:
    """
    Use Inkscape's path-simplify action. This is intentionally optional:
    path simplification changes geometry and must pass raster validation.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)

    actions = ["select-all:all"]
    actions.extend(["path-simplify"] * passes)
    actions.extend([
        f"export-filename:{destination}",
        "export-do",
        "file-close",
    ])

    command = [
        inkscape,
        "--batch-process",
        f"--actions={';'.join(actions)}",
        str(source),
    ]

    result = run_command(command)

    if result.returncode != 0:
        return False, (result.stderr or result.stdout).strip()

    if not destination.exists():
        return False, "Inkscape simplify pass did not create SVG."

    return True, ""


# ---------------------------------------------------------------------------
# Visual comparison
# ---------------------------------------------------------------------------

def composite_on_background(image: Image.Image, value: int) -> Image.Image:
    image = image.convert("RGBA")
    bg = Image.new("RGBA", image.size, (value, value, value, 255))
    return Image.alpha_composite(bg, image).convert("RGB")


def compare_rgb_images(
    reference: Image.Image,
    candidate: Image.Image,
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


# ---------------------------------------------------------------------------
# Profile processing
# ---------------------------------------------------------------------------

def build_lossless_candidate(
    svgo: str,
    source: Path,
    temp_dir: Path,
    lossless_config: Path,
) -> tuple[Path | None, str]:
    destination = temp_dir / "lossless.svg"

    ok, error = run_svgo(
        svgo,
        source,
        destination,
        lossless_config,
        precision=None,
    )

    if not ok:
        return None, error

    return destination, ""


def candidate_record(
    relative: Path,
    profile: str,
    name: str,
    precision: int | None,
    simplify_passes: int,
    path: Path,
    passed: bool,
    metrics: VisualMetrics,
    error: str = "",
) -> CandidateResult:
    return CandidateResult(
        file=str(relative),
        profile=profile,
        candidate=name,
        precision="" if precision is None else str(precision),
        simplify_passes=simplify_passes,
        bytes=path.stat().st_size if path.exists() else 0,
        gzip_bytes=file_gzip_size(path) if path.exists() else 0,
        passed=passed,
        worst_rms=metrics.worst_rms,
        worst_changed_fraction=metrics.worst_changed_fraction,
        error=error,
    )


def process_lossless(
    source: Path,
    relative: Path,
    profile_root: Path,
    svgo: str,
    temp_dir: Path,
    lossless_config: Path,
    write_svgz: bool,
) -> tuple[OutputResult, list[CandidateResult]]:
    destination = profile_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)

    source_bytes = source.stat().st_size

    candidate, error = build_lossless_candidate(
        svgo,
        source,
        temp_dir,
        lossless_config,
    )

    candidates = []

    if candidate is None:
        shutil.copy2(source, destination)

        result = OutputResult(
            file=str(relative),
            profile="lossless",
            status="COPIED_ORIGINAL_SVGO_FAILED",
            source_bytes=source_bytes,
            output_bytes=destination.stat().st_size,
            gzip_bytes=file_gzip_size(destination),
            reduction_percent=0.0,
            chosen_candidate="original",
            precision="",
            simplify_passes=0,
            worst_rms=0.0,
            worst_changed_fraction=0.0,
            error=error,
        )
        return result, candidates

    metrics = VisualMetrics()
    candidates.append(
        candidate_record(
            relative,
            "lossless",
            "lossless",
            None,
            0,
            candidate,
            True,
            metrics,
        )
    )

    chosen, chosen_label = copy_if_smaller(
        source,
        candidate,
        destination,
    )

    if write_svgz:
        maybe_write_svgz(destination)

    result = OutputResult(
        file=str(relative),
        profile="lossless",
        status="OK",
        source_bytes=source_bytes,
        output_bytes=destination.stat().st_size,
        gzip_bytes=file_gzip_size(destination),
        reduction_percent=safe_reduction(
            source_bytes,
            destination.stat().st_size,
        ),
        chosen_candidate=chosen_label,
        precision="",
        simplify_passes=0,
        worst_rms=0.0,
        worst_changed_fraction=0.0,
        error="",
    )

    return result, candidates


def evaluation_to_candidate_result(
    relative: Path,
    profile: str,
    evaluation: CandidateEvaluation,
) -> CandidateResult:
    path = evaluation.path
    return CandidateResult(
        file=str(relative),
        profile=profile,
        candidate=evaluation.name,
        precision=(
            "" if evaluation.precision is None else str(evaluation.precision)
        ),
        simplify_passes=evaluation.simplify_passes,
        bytes=path.stat().st_size if path is not None and path.exists() else 0,
        gzip_bytes=(
            file_gzip_size(path)
            if path is not None and path.exists()
            else 0
        ),
        passed=evaluation.passed,
        worst_rms=evaluation.metrics.worst_rms,
        worst_changed_fraction=evaluation.metrics.worst_changed_fraction,
        error=evaluation.error,
    )


def build_candidate_evaluation(
    source_base: Path,
    label: str,
    precision: int,
    simplify_passes: int,
    svgo: str,
    lossy_config: Path,
    validator: RasterValidator,
    temp_dir: Path,
) -> CandidateEvaluation:
    candidate = temp_dir / "svgo" / f"{label}.svg"

    ok, svgo_error = run_svgo(
        svgo,
        source_base,
        candidate,
        lossy_config,
        precision=precision,
    )

    if not ok:
        return CandidateEvaluation(
            name=label,
            precision=precision,
            simplify_passes=simplify_passes,
            path=None,
            passed=False,
            metrics=VisualMetrics(),
            error=svgo_error,
        )

    passed, metrics, validation_error = validator.validate(candidate, label)
    return CandidateEvaluation(
        name=label,
        precision=precision,
        simplify_passes=simplify_passes,
        path=candidate,
        passed=passed,
        metrics=metrics,
        error=validation_error,
        renderer_failure=bool(validation_error),
    )


def choose_lossy_output(
    profile: str,
    source: Path,
    relative: Path,
    profile_root: Path,
    evaluations: list[CandidateEvaluation],
    lossless_candidate: Path | None,
    lossless_error: str,
    write_svgz: bool,
) -> OutputResult:
    destination = profile_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_bytes = source.stat().st_size

    passing = [
        item
        for item in evaluations
        if item.passed and item.path is not None and item.path.exists()
    ]

    error = ""
    if passing:
        passing.sort(key=lambda item: item.path.stat().st_size)
        chosen = passing[0]

        if chosen.path.stat().st_size < source_bytes:
            shutil.copy2(chosen.path, destination)
            status = "OK"
            chosen_label = chosen.name
            precision = chosen.precision
            sim_passes = chosen.simplify_passes
            metrics = chosen.metrics
        else:
            shutil.copy2(source, destination)
            status = "NO_SMALLER_PASSING_CANDIDATE"
            chosen_label = "original"
            precision = None
            sim_passes = 0
            metrics = VisualMetrics()
    else:
        if lossless_candidate is not None:
            _, chosen_label = copy_if_smaller(
                source,
                lossless_candidate,
                destination,
            )
            status = "LOSSLESS_FALLBACK"
        else:
            shutil.copy2(source, destination)
            chosen_label = "original"
            status = "ORIGINAL_FALLBACK"
            error = lossless_error

        precision = None
        sim_passes = 0
        metrics = VisualMetrics()

    if write_svgz:
        maybe_write_svgz(destination)

    return OutputResult(
        file=str(relative),
        profile=profile,
        status=status,
        source_bytes=source_bytes,
        output_bytes=destination.stat().st_size,
        gzip_bytes=file_gzip_size(destination),
        reduction_percent=safe_reduction(
            source_bytes, destination.stat().st_size
        ),
        chosen_candidate=chosen_label,
        precision="" if precision is None else str(precision),
        simplify_passes=sim_passes,
        worst_rms=metrics.worst_rms,
        worst_changed_fraction=metrics.worst_changed_fraction,
        error=error,
    )


def process_file_profiles(
    source: Path,
    relative: Path,
    output_root: Path,
    profiles: list[str],
    svgo: str,
    renderer: str | None,
    renderer_executable: str | None,
    inkscape: str | None,
    temp_dir: Path,
    lossy_config: Path,
    lossless_config: Path,
    balanced_precisions: list[int],
    small_precisions: list[int],
    target_sizes: list[int],
    dprs: list[float],
    max_rms: float,
    max_changed_fraction: float,
    pixel_diff_threshold: int,
    simplify_passes: int,
    write_svgz: bool,
) -> tuple[list[OutputResult], list[CandidateResult], bool]:
    outputs: list[OutputResult] = []
    candidate_rows: list[CandidateResult] = []
    had_renderer_failure = False

    # Build the lossless candidate at most once. It is used both by the
    # lossless profile and as the safe fallback for lossy profiles.
    lossless_candidate: Path | None = None
    lossless_error = ""
    if "lossless" in profiles:
        lossless_candidate, lossless_error = build_lossless_candidate(
            svgo,
            source,
            temp_dir / "lossless",
            lossless_config,
        )

    if "lossless" in profiles:
        destination = output_root / "lossless" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        source_bytes = source.stat().st_size

        if lossless_candidate is None:
            shutil.copy2(source, destination)
            outputs.append(
                OutputResult(
                    file=str(relative),
                    profile="lossless",
                    status="COPIED_ORIGINAL_SVGO_FAILED",
                    source_bytes=source_bytes,
                    output_bytes=destination.stat().st_size,
                    gzip_bytes=file_gzip_size(destination),
                    reduction_percent=0.0,
                    chosen_candidate="original",
                    precision="",
                    simplify_passes=0,
                    worst_rms=0.0,
                    worst_changed_fraction=0.0,
                    error=lossless_error,
                )
            )
        else:
            candidate_rows.append(
                candidate_record(
                    relative,
                    "lossless",
                    "lossless",
                    None,
                    0,
                    lossless_candidate,
                    True,
                    VisualMetrics(),
                )
            )
            _, chosen_label = copy_if_smaller(
                source, lossless_candidate, destination
            )
            if write_svgz:
                maybe_write_svgz(destination)
            outputs.append(
                OutputResult(
                    file=str(relative),
                    profile="lossless",
                    status="OK",
                    source_bytes=source_bytes,
                    output_bytes=destination.stat().st_size,
                    gzip_bytes=file_gzip_size(destination),
                    reduction_percent=safe_reduction(
                        source_bytes, destination.stat().st_size
                    ),
                    chosen_candidate=chosen_label,
                    precision="",
                    simplify_passes=0,
                    worst_rms=0.0,
                    worst_changed_fraction=0.0,
                    error="",
                )
            )

    lossy_profiles = [p for p in profiles if p in {"balanced", "small"}]
    if not lossy_profiles:
        return outputs, candidate_rows, had_renderer_failure

    assert renderer is not None
    assert renderer_executable is not None

    # One reference raster set per SVG, shared by balanced and small.
    validator = RasterValidator(
        renderer=renderer,
        executable=renderer_executable,
        reference_svg=source,
        temp_root=temp_dir / "validation",
        target_sizes=target_sizes,
        dprs=dprs,
        max_rms=max_rms,
        max_changed_fraction=max_changed_fraction,
        pixel_diff_threshold=pixel_diff_threshold,
    )
    ok, reference_error = validator.prepare_reference()

    if not ok:
        had_renderer_failure = True
        source_bytes = source.stat().st_size
        for profile in lossy_profiles:
            destination = output_root / profile / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            if write_svgz:
                maybe_write_svgz(destination)
            outputs.append(
                OutputResult(
                    file=str(relative),
                    profile=profile,
                    status="REFERENCE_RENDER_FAILED",
                    source_bytes=source_bytes,
                    output_bytes=destination.stat().st_size,
                    gzip_bytes=file_gzip_size(destination),
                    reduction_percent=0.0,
                    chosen_candidate="original",
                    precision="",
                    simplify_passes=0,
                    worst_rms=0.0,
                    worst_changed_fraction=0.0,
                    error=reference_error,
                )
            )
        return outputs, candidate_rows, had_renderer_failure

    # Cache original-base precision candidates across profiles. Balanced is
    # intentionally short-circuiting: test candidates in the requested order
    # and stop at the first passing result. With the default [2, 3], p3 is only
    # rendered when p2 fails. Small remains exhaustive because its purpose is
    # to find the smallest visually acceptable candidate.
    original_eval: dict[int, CandidateEvaluation] = {}

    def get_original_evaluation(precision: int) -> CandidateEvaluation:
        nonlocal had_renderer_failure
        if precision not in original_eval:
            evaluation = build_candidate_evaluation(
                source_base=source,
                label=f"p{precision}",
                precision=precision,
                simplify_passes=0,
                svgo=svgo,
                lossy_config=lossy_config,
                validator=validator,
                temp_dir=temp_dir,
            )
            original_eval[precision] = evaluation
            had_renderer_failure |= evaluation.renderer_failure
        return original_eval[precision]

    profile_evaluations: dict[str, list[CandidateEvaluation]] = {}
    if "balanced" in profiles:
        balanced_evals: list[CandidateEvaluation] = []
        for precision in balanced_precisions:
            evaluation = get_original_evaluation(precision)
            balanced_evals.append(evaluation)
            if evaluation.passed:
                break
        profile_evaluations["balanced"] = balanced_evals

    if "small" in profiles:
        small_evals = [
            get_original_evaluation(p) for p in small_precisions
        ]

        current_base = source
        if simplify_passes > 0:
            assert inkscape is not None
        for pass_count in range(1, simplify_passes + 1):
            simplified = (
                temp_dir / "simplified" / f"pass-{pass_count}.svg"
            )
            ok, simplify_error = simplify_svg(
                inkscape, current_base, simplified, 1
            )

            if not ok:
                had_renderer_failure = True
                small_evals.append(
                    CandidateEvaluation(
                        name=f"simplify-{pass_count}",
                        precision=None,
                        simplify_passes=pass_count,
                        path=None,
                        passed=False,
                        metrics=VisualMetrics(),
                        error=simplify_error,
                        renderer_failure=True,
                    )
                )
                break

            for precision in small_precisions:
                evaluation = build_candidate_evaluation(
                    source_base=simplified,
                    label=f"s{pass_count}-p{precision}",
                    precision=precision,
                    simplify_passes=pass_count,
                    svgo=svgo,
                    lossy_config=lossy_config,
                    validator=validator,
                    temp_dir=temp_dir,
                )
                small_evals.append(evaluation)
                had_renderer_failure |= evaluation.renderer_failure

            current_base = simplified

        profile_evaluations["small"] = small_evals

    # A lossless fallback is only needed if a requested lossy profile has no
    # passing candidate. For balanced-only/small-only runs, build it lazily so
    # successful files avoid one unnecessary SVGO invocation.
    needs_lossless_fallback = any(
        not any(
            item.passed
            and item.path is not None
            and item.path.exists()
            for item in profile_evaluations[profile]
        )
        for profile in lossy_profiles
    )
    if needs_lossless_fallback and lossless_candidate is None:
        lossless_candidate, lossless_error = build_lossless_candidate(
            svgo,
            source,
            temp_dir / "lossless-fallback",
            lossless_config,
        )

    for profile in lossy_profiles:
        evaluations = profile_evaluations[profile]
        candidate_rows.extend(
            evaluation_to_candidate_result(relative, profile, item)
            for item in evaluations
        )
        outputs.append(
            choose_lossy_output(
                profile=profile,
                source=source,
                relative=relative,
                profile_root=output_root / profile,
                evaluations=evaluations,
                lossless_candidate=lossless_candidate,
                lossless_error=lossless_error,
                write_svgz=write_svgz,
            )
        )

    return outputs, candidate_rows, had_renderer_failure


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

def write_csv(path: Path, rows: list[dict], fieldnames: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_reports(
    reports_root: Path,
    outputs: list[OutputResult],
    candidates: list[CandidateResult],
    run_info: dict,
):
    output_fields = [
        "file",
        "profile",
        "status",
        "source_bytes",
        "output_bytes",
        "gzip_bytes",
        "reduction_percent",
        "chosen_candidate",
        "precision",
        "simplify_passes",
        "worst_rms",
        "worst_changed_fraction",
        "file_runtime_seconds",
        "error",
    ]

    candidate_fields = [
        "file",
        "profile",
        "candidate",
        "precision",
        "simplify_passes",
        "bytes",
        "gzip_bytes",
        "passed",
        "worst_rms",
        "worst_changed_fraction",
        "error",
    ]

    write_csv(
        reports_root / "compression-report.csv",
        [asdict(row) for row in outputs],
        output_fields,
    )

    write_csv(
        reports_root / "compression-candidates.csv",
        [asdict(row) for row in candidates],
        candidate_fields,
    )

    (reports_root / "compression-run.json").write_text(
        json.dumps(run_info, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Compress SVG files using rendering-lossless and "
            "display-aware lossy profiles."
        )
    )

    parser.add_argument(
        "input",
        help="Input SVG file or directory",
    )

    parser.add_argument(
        "output",
        help="Separate output directory",
    )

    parser.add_argument(
        "--profile",
        choices=["lossless", "balanced", "small", "all"],
        default="balanced",
        help="Compression profile (default: balanced)",
    )

    parser.add_argument(
        "--target-sizes",
        type=parse_int_list,
        default=parse_int_list("64"),
        help=(
            "Comma-separated CSS pixel widths used for validation "
            "(default: 64)"
        ),
    )

    parser.add_argument(
        "--dprs",
        type=parse_float_list,
        default=parse_float_list("1,3"),
        help=(
            "Comma-separated device-pixel ratios used for validation "
            "(default: 1,3)"
        ),
    )

    parser.add_argument(
        "--balanced-precisions",
        type=parse_precision_list,
        default=parse_precision_list("2,3"),
        help=(
            "Ordered SVGO precision candidates for balanced; stops at the "
            "first passing candidate (default: 2,3)"
        ),
    )

    parser.add_argument(
        "--small-precisions",
        type=parse_precision_list,
        default=parse_precision_list("3,2,1,0"),
        help="SVGO precision candidates for small (default: 3,2,1,0)",
    )

    parser.add_argument(
        "--simplify-passes",
        type=int,
        default=0,
        help=(
            "For small profile, also test 1..N Inkscape path-simplify "
            "passes (default: 0)"
        ),
    )

    parser.add_argument(
        "--max-rms",
        type=float,
        default=0.01,
        help=(
            "Maximum normalized RGB RMS difference for a lossy candidate "
            "(default: 0.01)"
        ),
    )

    parser.add_argument(
        "--max-changed",
        type=float,
        default=0.01,
        help=(
            "Maximum fraction of pixels differing above the per-channel "
            "threshold (default: 0.01 = 1%%)"
        ),
    )

    parser.add_argument(
        "--pixel-diff-threshold",
        type=int,
        default=8,
        help=(
            "A pixel counts as changed when any RGB channel differs by "
            "more than this 0..255 amount (default: 8)"
        ),
    )

    parser.add_argument(
        "--write-svgz",
        action="store_true",
        help="Also write gzip-compressed .svgz beside each .svg output",
    )

    parser.add_argument(
        "--lossless-minify-only",
        action="store_true",
        help=(
            "Lossless profile only reserializes/minifies XML; do not strip "
            "comments, metadata, editor data, or empty attributes"
        ),
    )

    parser.add_argument(
        "--jobs",
        type=int,
        default=2,
        help=(
            "Number of SVG files to process concurrently (default: 2). "
            "Renderer failures from parallel work are retried once "
            "sequentially."
        ),
    )

    parser.add_argument(
        "--svgo",
        help="Explicit SVGO executable/path",
    )

    parser.add_argument(
        "--renderer",
        choices=["inkscape", "resvg", "auto"],
        default="resvg",
        help=(
            "SVG rasterizer used for visual validation: inkscape, resvg, "
            "or auto (prefer resvg, fall back to Inkscape). "
            "Default: resvg"
        ),
    )

    parser.add_argument(
        "--resvg",
        help="Explicit resvg executable/path",
    )

    parser.add_argument(
        "--inkscape",
        help="Explicit Inkscape executable/path",
    )

    args = parser.parse_args()

    if args.simplify_passes < 0:
        parser.error("--simplify-passes cannot be negative")

    if args.jobs < 1:
        parser.error("--jobs must be at least 1")

    if not 0 <= args.pixel_diff_threshold <= 255:
        parser.error("--pixel-diff-threshold must be 0..255")

    if args.max_rms < 0 or args.max_changed < 0:
        parser.error("visual thresholds cannot be negative")

    input_path = Path(args.input).resolve()
    output_root = Path(args.output).resolve()

    if not input_path.exists():
        print(f"Input does not exist: {input_path}", file=sys.stderr)
        return 1

    # Keep source and output trees separate in both directions.
    input_tree_root = input_path if input_path.is_dir() else input_path.parent

    if output_root == input_tree_root or is_relative_to(output_root, input_tree_root):
        print(
            "Refusing to write output inside the input tree. "
            "Choose a separate output directory.",
            file=sys.stderr,
        )
        return 1

    if is_relative_to(input_tree_root, output_root):
        print(
            "Refusing to use an output directory that contains the input tree.",
            file=sys.stderr,
        )
        return 1

    svgo = find_svgo(args.svgo)

    if not svgo:
        print(
            "Could not find SVGO. Install it with:\n"
            "  npm install -g svgo",
            file=sys.stderr,
        )
        return 2

    profiles = (
        ["lossless", "balanced", "small"]
        if args.profile == "all"
        else [args.profile]
    )

    needs_visual_validation = any(
        p in {"balanced", "small"} for p in profiles
    )

    renderer = None
    renderer_executable = None
    resvg = None
    inkscape = None

    if needs_visual_validation:
        if args.renderer in {"resvg", "auto"}:
            resvg = find_resvg(args.resvg)
        if args.renderer in {"inkscape", "auto"}:
            inkscape = find_inkscape(args.inkscape)

        if args.renderer == "resvg":
            renderer = "resvg"
            renderer_executable = resvg
        elif args.renderer == "inkscape":
            renderer = "inkscape"
            renderer_executable = inkscape
        else:
            if resvg:
                renderer = "resvg"
                renderer_executable = resvg
            else:
                renderer = "inkscape"
                renderer_executable = inkscape

        if not renderer_executable:
            if args.renderer == "resvg":
                message = (
                    "Could not find resvg. Put resvg.exe in PATH or pass "
                    "--resvg PATH."
                )
            elif args.renderer == "inkscape":
                message = (
                    "Could not find Inkscape, which is required by the "
                    "selected renderer."
                )
            else:
                message = (
                    "Could not find either resvg or Inkscape for visual "
                    "validation."
                )
            print(message, file=sys.stderr)
            return 2

    # Inkscape remains necessary only for optional path simplification.
    needs_inkscape_simplify = (
        "small" in profiles and args.simplify_passes > 0
    )
    if needs_inkscape_simplify and not inkscape:
        inkscape = find_inkscape(args.inkscape)
        if not inkscape:
            print(
                "Could not find Inkscape, which is required when "
                "--simplify-passes > 0.",
                file=sys.stderr,
            )
            return 2

    if input_path.is_file():
        if input_path.suffix.casefold() != ".svg":
            print("Input file must have .svg extension.", file=sys.stderr)
            return 1
        files = [input_path]
        source_root = input_path.parent
    else:
        source_root = input_path
        files = sorted(input_path.rglob("*.svg"))

    if not files:
        print("No SVG files found.")
        return 0

    output_root.mkdir(parents=True, exist_ok=True)
    reports_root = output_root / "reports"
    reports_root.mkdir(parents=True, exist_ok=True)

    print(f"SVGO:     {svgo} ({get_tool_version(svgo)})")
    if renderer_executable:
        print(
            f"Renderer: {renderer} - {renderer_executable} "
            f"({get_tool_version(renderer_executable)})"
        )
    if needs_inkscape_simplify and inkscape:
        print(
            f"Simplifier: Inkscape - {inkscape} "
            f"({get_tool_version(inkscape)})"
        )
    print(f"Input:    {input_path}")
    print(f"Output:   {output_root}")
    print(f"Profiles: {', '.join(profiles)}")
    print(
        "Validation: "
        f"sizes={','.join(map(str, args.target_sizes))} CSS px; "
        f"DPR={','.join(f'{x:g}' for x in args.dprs)}"
    )
    print(
        "Thresholds: "
        f"RMS<={args.max_rms:g}, "
        f"changed<={args.max_changed:g}, "
        f"pixel-diff>{args.pixel_diff_threshold}"
    )
    print(f"SVG files: {len(files)}")
    print(f"Jobs:      {args.jobs}")
    print()

    all_outputs: list[OutputResult] = []
    all_candidates: list[CandidateResult] = []
    processing_started = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="svg-compress-run-") as run_temp_str:
        run_temp = Path(run_temp_str)

        lossless_config = write_config(
            run_temp,
            "lossless.config.mjs",
            LOSSLESS_CONFIG_MINIFY_ONLY
            if args.lossless_minify_only
            else LOSSLESS_CONFIG_CLEAN,
        )
        lossy_config = write_config(
            run_temp,
            "lossy.config.mjs",
            LOSSY_CONFIG,
        )

        def process_one(index: int, source: Path):
            file_started = time.perf_counter()
            relative = source.relative_to(source_root)
            temp_dir = run_temp / "files" / f"{index:06d}"
            temp_dir.mkdir(parents=True, exist_ok=True)
            outputs, candidates, renderer_failed = process_file_profiles(
                source=source,
                relative=relative,
                output_root=output_root,
                profiles=profiles,
                svgo=svgo,
                renderer=renderer,
                renderer_executable=renderer_executable,
                inkscape=inkscape,
                temp_dir=temp_dir,
                lossy_config=lossy_config,
                lossless_config=lossless_config,
                balanced_precisions=args.balanced_precisions,
                small_precisions=args.small_precisions,
                target_sizes=args.target_sizes,
                dprs=args.dprs,
                max_rms=args.max_rms,
                max_changed_fraction=args.max_changed,
                pixel_diff_threshold=args.pixel_diff_threshold,
                simplify_passes=args.simplify_passes,
                write_svgz=args.write_svgz,
            )
            file_runtime = time.perf_counter() - file_started
            for row in outputs:
                row.file_runtime_seconds = file_runtime
            return index, source, relative, outputs, candidates, renderer_failed

        completed: dict[int, tuple[Path, Path, list[OutputResult], list[CandidateResult], bool]] = {}

        if args.jobs == 1 or len(files) == 1:
            for index, source in enumerate(files, 1):
                result = process_one(index, source)
                _, src, relative, outputs, candidates, failed = result
                completed[index] = (src, relative, outputs, candidates, failed)
                print(
                    f"[{index}/{len(files)}] {relative} "
                    f"({source.stat().st_size:,} bytes)"
                )
                for row in outputs:
                    print(
                        f"    {row.profile:<8} "
                        f"{row.status:<28} "
                        f"{row.output_bytes:>10,} B "
                        f"({row.reduction_percent:6.1f}% smaller) "
                        f"[{row.chosen_candidate}]"
                    )
        else:
            print(f"Parallel jobs: {args.jobs}")
            print()
            with ThreadPoolExecutor(max_workers=args.jobs) as executor:
                futures = {
                    executor.submit(process_one, index, source): index
                    for index, source in enumerate(files, 1)
                }
                for future in as_completed(futures):
                    index, src, relative, outputs, candidates, failed = future.result()
                    completed[index] = (src, relative, outputs, candidates, failed)
                    print(
                        f"[{index}/{len(files)}] {relative} "
                        f"({src.stat().st_size:,} bytes)"
                    )
                    for row in outputs:
                        print(
                            f"    {row.profile:<8} "
                            f"{row.status:<28} "
                            f"{row.output_bytes:>10,} B "
                            f"({row.reduction_percent:6.1f}% smaller) "
                            f"[{row.chosen_candidate}]"
                        )

            retry_indices = [
                index
                for index in sorted(completed)
                if completed[index][4]
            ]

            if retry_indices:
                print()
                print(
                    f"Retrying {len(retry_indices)} file(s) with {renderer} "
                    "render failures sequentially..."
                )
                for retry_no, index in enumerate(retry_indices, 1):
                    source = files[index - 1]
                    retry_temp = run_temp / "retry" / f"{index:06d}"
                    if retry_temp.exists():
                        shutil.rmtree(retry_temp)
                    retry_temp.mkdir(parents=True, exist_ok=True)

                    relative = source.relative_to(source_root)
                    prior_outputs = completed[index][2]
                    prior_runtime = (
                        prior_outputs[0].file_runtime_seconds
                        if prior_outputs else 0.0
                    )
                    retry_started = time.perf_counter()
                    outputs, candidates, failed = process_file_profiles(
                        source=source,
                        relative=relative,
                        output_root=output_root,
                        profiles=profiles,
                        svgo=svgo,
                        renderer=renderer,
                        renderer_executable=renderer_executable,
                        inkscape=inkscape,
                        temp_dir=retry_temp,
                        lossy_config=lossy_config,
                        lossless_config=lossless_config,
                        balanced_precisions=args.balanced_precisions,
                        small_precisions=args.small_precisions,
                        target_sizes=args.target_sizes,
                        dprs=args.dprs,
                        max_rms=args.max_rms,
                        max_changed_fraction=args.max_changed,
                        pixel_diff_threshold=args.pixel_diff_threshold,
                        simplify_passes=args.simplify_passes,
                        write_svgz=args.write_svgz,
                    )
                    total_runtime = prior_runtime + (time.perf_counter() - retry_started)
                    for row in outputs:
                        row.file_runtime_seconds = total_runtime
                    completed[index] = (
                        source, relative, outputs, candidates, failed
                    )
                    status_text = (
                        f"still has {renderer} errors" if failed else "OK"
                    )
                    print(
                        f"[retry {retry_no}/{len(retry_indices)}] "
                        f"{relative}: {status_text}"
                    )

        # Deterministic report order regardless of worker completion order.
        profile_order = {name: i for i, name in enumerate(profiles)}
        for index in sorted(completed):
            _, _, outputs, candidates, _ = completed[index]
            outputs.sort(key=lambda row: profile_order.get(row.profile, 999))
            # Candidate rows are already generated in profile/requested precision
            # order. Keep that order while file order remains deterministic.
            all_outputs.extend(outputs)
            all_candidates.extend(candidates)

    elapsed_seconds = time.perf_counter() - processing_started

    run_info = {
        "input": str(input_path),
        "output": str(output_root),
        "profiles": profiles,
        "jobs": args.jobs,
        "elapsed_seconds": elapsed_seconds,
        "renderer": renderer,
        "renderer_version": (
            get_tool_version(renderer_executable)
            if renderer_executable else None
        ),
        "target_sizes_css_px": args.target_sizes,
        "dprs": args.dprs,
        "balanced_precisions": args.balanced_precisions,
        "small_precisions": args.small_precisions,
        "simplify_passes": args.simplify_passes,
        "max_rms": args.max_rms,
        "max_changed_fraction": args.max_changed,
        "pixel_diff_threshold": args.pixel_diff_threshold,
        "write_svgz": args.write_svgz,
        "lossless_minify_only": args.lossless_minify_only,
        "svgo_version": get_tool_version(svgo),
        "inkscape_version": (
            get_tool_version(inkscape) if inkscape else None
        ),
        "resvg_version": (
            get_tool_version(resvg) if resvg else None
        ),
    }

    write_reports(
        reports_root,
        all_outputs,
        all_candidates,
        run_info,
    )

    print()
    print("Summary")
    print("-------")

    for profile in profiles:
        rows = [r for r in all_outputs if r.profile == profile]
        source_total = sum(r.source_bytes for r in rows)
        output_total = sum(r.output_bytes for r in rows)
        gzip_total = sum(r.gzip_bytes for r in rows)

        reduction = safe_reduction(source_total, output_total)

        print(
            f"{profile:<8} "
            f"{source_total:>12,} -> {output_total:>12,} bytes "
            f"({reduction:5.1f}% smaller), "
            f"gzip estimate {gzip_total:,} bytes"
        )

    print()
    print(f"Elapsed: {elapsed_seconds:.2f} seconds")
    print(f"Reports: {reports_root}")
    print("  compression-report.csv")
    print("  compression-candidates.csv")
    print("  compression-run.json")

    return 0


if __name__ == "__main__":
    sys.exit(main())
