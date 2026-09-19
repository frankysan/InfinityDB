"""Materialize and structurally audit immutable raw symbol snapshots."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from importlib import import_module
from pathlib import Path, PurePosixPath
from typing import Any, NamedTuple

from infinity_db.snapshot_provenance import load_snapshot_manifest, sha256_file
from infinity_db.symbol_manifest import (
    SYMBOL_BUILD_DUPLICATE_VERSION,
    SYMBOL_BUILD_FONT_AUDIT_VERSION,
    SYMBOL_BUILD_PREFLIGHT_VERSION,
    SYMBOL_BUILD_TEXT_CONVERSION_VERSION,
    add_compression,
    add_duplicate_detection,
    add_font_audit,
    add_svg_preflight,
    add_text_conversion,
    artifact_record,
    load_symbol_manifest,
    write_symbol_manifest,
)

SVG_PREFLIGHT_FORMAT = "InfinityDB SVG preflight audit"
SVG_PREFLIGHT_VERSION = 1
FONT_AUDIT_FORMAT = "InfinityDB SVG font audit"
FONT_AUDIT_VERSION = 1
DEFAULT_FONT_ALIAS_CONFIG = (
    Path(__file__).resolve().parents[1] / "config" / "symbols" / "font-aliases.json"
)
_TEXT_ROOT_TAGS = {"text", "flowRoot"}
_FONT_FAMILY_RE = re.compile(r"(?:^|[;{])\s*font-family\s*:\s*([^;}]+)", re.I)


class MaterializedSymbols(NamedTuple):
    work_root: Path
    raw_root: Path
    asset_count: int
    build_manifest: dict[str, Any]


class SvgPreflightResult(NamedTuple):
    report: Path
    summary: dict[str, int]
    status: str


class FontAuditResult(NamedTuple):
    report: Path
    summary: dict[str, int]
    status: str


class DuplicateDetectionResult(NamedTuple):
    groups_report: Path
    errors_report: Path
    summary_report: Path
    summary: dict[str, int]
    canonical_by_archive_path: dict[str, str]
    renderer: str
    renderer_version: str
    status: str


class TextConversionResult(NamedTuple):
    canonical_root: Path
    report: Path
    summary_report: Path
    summary: dict[str, int]
    converter: str
    converter_version: str
    status: str


class CompressionResult(NamedTuple):
    compressed_root: Path
    report: Path
    candidates_report: Path
    run_report: Path
    summary: dict[str, int]
    renderer: str
    renderer_version: str
    status: str


def _portable_member(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or path.is_absolute()
        or ".." in path.parts
        or any(part in {"", "."} for part in path.parts)
    ):
        raise ValueError(f"Symbol archive member is not a portable relative path: {value!r}")
    return path


def _work_name(archive: Path, digest: str) -> str:
    return f"{archive.stem}--{digest[:12]}"


def load_materialized_symbol_work(
    archive: Path,
    snapshot_manifest_path: Path,
    build_manifest_path: Path,
    work_base: Path,
) -> MaterializedSymbols:
    """Load and verify an existing loose work tree without replacing derived output."""
    manifest = load_symbol_manifest(build_manifest_path)
    artifact = manifest["snapshot"]["symbolArtifact"]
    if archive.name != artifact["name"]:
        raise ValueError(
            "Pinned symbol archive name does not match army-symbol-build.json: "
            f"{archive.name} != {artifact['name']}"
        )
    archive_sha = sha256_file(archive)
    if archive_sha != artifact["sha256"]:
        raise ValueError(
            "Pinned symbol archive SHA-256 mismatch: "
            f"expected {artifact['sha256']}, got {archive_sha}"
        )
    provenance = load_snapshot_manifest(snapshot_manifest_path, archive=archive)
    snapshot = provenance["snapshot"]
    if snapshot["type"] != "symbols":
        raise ValueError(
            f"Pinned symbol provenance is not a symbol snapshot: {snapshot_manifest_path}"
        )
    if snapshot["archive"]["name"] != archive.name:
        raise ValueError(
            "Pinned symbol provenance names a different archive: "
            f"{snapshot['archive']['name']} != {archive.name}"
        )
    input_artifact = provenance.get("inputArtifact")
    army_artifact = manifest["snapshot"]["armyArtifact"]
    if not isinstance(input_artifact, dict) or (
        input_artifact.get("name") != army_artifact["name"]
        or input_artifact.get("sha256") != army_artifact["sha256"]
    ):
        raise ValueError(
            "Pinned symbol provenance Army input does not match army-symbol-build.json"
        )

    destination = work_base / _work_name(archive, archive_sha)
    raw_root = destination / "raw"
    if not raw_root.is_dir():
        raise ValueError(f"Materialized symbol work tree is missing: {raw_root}")

    expected = {asset["archivePath"]: asset for asset in manifest["assets"]}
    if snapshot["documentCount"] != len(expected):
        raise ValueError(
            "Pinned symbol snapshot document count does not match army-symbol-build.json: "
            f"{snapshot['documentCount']} != {len(expected)}"
        )
    actual = {
        path.relative_to(raw_root).as_posix()
        for path in raw_root.rglob("*")
        if path.is_file()
    }
    if actual != set(expected):
        missing = sorted(set(expected) - actual)
        unexpected = sorted(actual - set(expected))
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if unexpected:
            details.append("unexpected: " + ", ".join(unexpected))
        raise ValueError(
            "Materialized symbol work tree does not match army-symbol-build.json ("
            + "; ".join(details)
            + ")"
        )
    for archive_path, asset in expected.items():
        path = raw_root.joinpath(*_portable_member(archive_path).parts)
        actual_sha = sha256_file(path)
        if actual_sha != asset["sha256"]:
            raise ValueError(
                f"Materialized symbol SHA-256 mismatch for {archive_path}: "
                f"expected {asset['sha256']}, got {actual_sha}"
            )

    return MaterializedSymbols(
        work_root=destination,
        raw_root=raw_root,
        asset_count=len(expected),
        build_manifest=manifest,
    )


def materialize_symbol_archive(
    archive: Path,
    snapshot_manifest_path: Path,
    build_manifest_path: Path,
    work_base: Path,
) -> MaterializedSymbols:
    """Rebuild a verified loose work tree from one immutable SYMBOLS archive."""
    manifest = load_symbol_manifest(build_manifest_path)
    artifact = manifest["snapshot"]["symbolArtifact"]
    if archive.name != artifact["name"]:
        raise ValueError(
            "Pinned symbol archive name does not match army-symbol-build.json: "
            f"{archive.name} != {artifact['name']}"
        )

    archive_sha = sha256_file(archive)
    if archive_sha != artifact["sha256"]:
        raise ValueError(
            "Pinned symbol archive SHA-256 mismatch: "
            f"expected {artifact['sha256']}, got {archive_sha}"
        )

    provenance = load_snapshot_manifest(snapshot_manifest_path, archive=archive)
    snapshot = provenance["snapshot"]
    if snapshot["type"] != "symbols":
        raise ValueError(
            f"Pinned symbol provenance is not a symbol snapshot: {snapshot_manifest_path}"
        )
    if snapshot["archive"]["name"] != archive.name:
        raise ValueError(
            "Pinned symbol provenance names a different archive: "
            f"{snapshot['archive']['name']} != {archive.name}"
        )

    input_artifact = provenance.get("inputArtifact")
    army_artifact = manifest["snapshot"]["armyArtifact"]
    if not isinstance(input_artifact, dict):
        raise ValueError(
            "Pinned symbol provenance is missing the Army input artifact: "
            f"{snapshot_manifest_path}"
        )
    if (
        input_artifact.get("name") != army_artifact["name"]
        or input_artifact.get("sha256") != army_artifact["sha256"]
    ):
        raise ValueError(
            "Pinned symbol provenance Army input does not match army-symbol-build.json"
        )

    expected = {asset["archivePath"]: asset for asset in manifest["assets"]}
    if snapshot["documentCount"] != len(expected):
        raise ValueError(
            "Pinned symbol snapshot document count does not match army-symbol-build.json: "
            f"{snapshot['documentCount']} != {len(expected)}"
        )

    work_base.mkdir(parents=True, exist_ok=True)
    destination = work_base / _work_name(archive, archive_sha)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=work_base))
    raw_root = staging / "raw"
    raw_root.mkdir()
    try:
        with zipfile.ZipFile(archive) as source:
            members = [info for info in source.infolist() if not info.is_dir()]
            names = [info.filename for info in members]
            if len(names) != len(set(names)):
                raise ValueError(f"Symbol archive contains duplicate members: {archive}")
            folded = [name.casefold() for name in names]
            if len(folded) != len(set(folded)):
                raise ValueError(
                    f"Symbol archive contains case-insensitive member collisions: {archive}"
                )
            for name in names:
                _portable_member(name)

            actual_names = set(names)
            expected_names = set(expected)
            missing = sorted(expected_names - actual_names)
            unexpected = sorted(actual_names - expected_names)
            if missing or unexpected:
                details = []
                if missing:
                    details.append("missing: " + ", ".join(missing))
                if unexpected:
                    details.append("unexpected: " + ", ".join(unexpected))
                raise ValueError(
                    "Symbol archive members do not match army-symbol-build.json ("
                    + "; ".join(details)
                    + ")"
                )

            for name in sorted(expected):
                body = source.read(name)
                actual_sha = hashlib.sha256(body).hexdigest()
                wanted_sha = expected[name]["sha256"]
                if actual_sha != wanted_sha:
                    raise ValueError(
                        f"Symbol archive member SHA-256 mismatch for {name}: "
                        f"expected {wanted_sha}, got {actual_sha}"
                    )
                relative = _portable_member(name)
                target = raw_root.joinpath(*relative.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(body)

        if destination.exists():
            shutil.rmtree(destination)
        staging.replace(destination)
    except zipfile.BadZipFile as exc:
        shutil.rmtree(staging, ignore_errors=True)
        raise ValueError(f"Invalid symbol archive {archive}: {exc}") from exc
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    return MaterializedSymbols(
        work_root=destination,
        raw_root=destination / "raw",
        asset_count=len(expected),
        build_manifest=manifest,
    )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _split_font_family_list(value: str) -> list[str]:
    result: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escaped = False
    for char in value:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif quote:
            if char == quote:
                quote = None
            else:
                current.append(char)
        elif char in {"'", '"'}:
            quote = char
        elif char == ",":
            name = "".join(current).strip()
            if name:
                result.append(name)
            current = []
        else:
            current.append(char)
    name = "".join(current).strip()
    if name:
        result.append(name)
    return result


def _font_families(root: ET.Element) -> list[str]:
    families: set[str] = set()
    for element in root.iter():
        direct = element.attrib.get("font-family")
        if direct:
            families.update(_split_font_family_list(direct))
        style = element.attrib.get("style")
        if style:
            for match in _FONT_FAMILY_RE.finditer(";" + style):
                families.update(_split_font_family_list(match.group(1)))
        if _local_name(element.tag) == "style":
            css = "".join(element.itertext())
            for match in _FONT_FAMILY_RE.finditer("{" + css):
                families.update(_split_font_family_list(match.group(1)))
    return sorted(families, key=str.casefold)


def _text_state(root: ET.Element) -> tuple[bool, int, int]:
    active = False
    text_runs = 0
    empty_objects = 0
    for element in root.iter():
        if _local_name(element.tag) not in _TEXT_ROOT_TAGS:
            continue
        text = "".join(element.itertext())
        if text.strip():
            active = True
            text_runs += sum(1 for part in element.itertext() if part.strip())
        else:
            empty_objects += 1
    return active, text_runs, empty_objects


def _write_json(document: dict[str, Any], path: Path) -> Path:
    payload = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    ) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8", newline="\n")
    temporary.replace(path)
    return path


def audit_symbol_work(
    materialized: MaterializedSymbols,
    *,
    archive: Path,
    build_manifest_path: Path,
    reports_base: Path,
    project_root: Path,
) -> SvgPreflightResult:
    """Write a deterministic structural SVG/font-declaration audit and persist its state."""
    rows: list[dict[str, Any]] = []
    font_assets: Counter[str] = Counter()
    parse_errors = 0
    active_text_assets = 0

    for asset in materialized.build_manifest["assets"]:
        archive_path = asset["archivePath"]
        path = materialized.raw_root.joinpath(*_portable_member(archive_path).parts)
        row: dict[str, Any] = {"archivePath": archive_path}
        try:
            root = ET.parse(path).getroot()
            if _local_name(root.tag) != "svg":
                raise ValueError(f"root element is {_local_name(root.tag)!r}, expected 'svg'")
            active_text, text_runs, empty_text_objects = _text_state(root)
            fonts = _font_families(root)
            row.update(
                {
                    "parseStatus": "ok",
                    "activeText": active_text,
                    "textRunCount": text_runs,
                    "emptyTextObjectCount": empty_text_objects,
                    "fontFamilies": fonts,
                }
            )
            if active_text:
                active_text_assets += 1
            for family in fonts:
                font_assets[family] += 1
        except (ET.ParseError, OSError, ValueError) as exc:
            parse_errors += 1
            row.update({"parseStatus": "error", "error": str(exc)})
        rows.append(row)

    summary = {
        "svgCount": len(rows),
        "parseErrorCount": parse_errors,
        "activeTextAssetCount": active_text_assets,
        "noActiveTextAssetCount": len(rows) - active_text_assets - parse_errors,
        "fontDeclaredAssetCount": sum(1 for row in rows if row.get("fontFamilies")),
        "uniqueDeclaredFontCount": len(font_assets),
    }
    if summary["svgCount"] != materialized.asset_count:
        raise ValueError(
            "SVG preflight count does not match materialized symbols: "
            f"{summary['svgCount']} != {materialized.asset_count}"
        )

    symbol_sha = materialized.build_manifest["snapshot"]["symbolArtifact"]["sha256"]
    report_root = reports_base / _work_name(archive, symbol_sha)
    report = report_root / "svg-preflight.json"
    document = {
        "format": SVG_PREFLIGHT_FORMAT,
        "formatVersion": SVG_PREFLIGHT_VERSION,
        "symbolArtifact": {
            "name": archive.name,
            "sha256": symbol_sha,
        },
        "summary": dict(sorted(summary.items())),
        "fonts": [
            {"family": family, "assetCount": count}
            for family, count in sorted(font_assets.items(), key=lambda item: item[0].casefold())
        ],
        "assets": sorted(rows, key=lambda row: row["archivePath"]),
    }
    _write_json(document, report)

    status = "passed" if parse_errors == 0 else "failed"
    updated = add_svg_preflight(
        materialized.build_manifest,
        status=status,
        summary=summary,
        report=report,
        project_root=project_root,
    )
    write_symbol_manifest(updated, build_manifest_path)
    return SvgPreflightResult(report=report, summary=summary, status=status)


def _font_tools():
    try:
        from tools import svg_processor
    except ImportError:  # pragma: no cover - direct script execution fallback
        import svg_processor
    return svg_processor


def _compression_tools() -> Any:
    try:
        return import_module("tools.svg_compress")
    except ModuleNotFoundError:
        try:
            return import_module("svg_compress")
        except ModuleNotFoundError as exc:  # pragma: no cover - packaging failure
            raise RuntimeError("Could not import svg_compress") from exc


def _font_result_record(result: dict[str, str]) -> dict[str, str]:
    font_file = result.get("font_file", "")
    return {
        "status": result.get("status", ""),
        "matchType": result.get("match_type", ""),
        "matchedName": result.get("matched_name", ""),
        "family": result.get("family", ""),
        "subfamily": result.get("subfamily", ""),
        "fullName": result.get("full_name", ""),
        "postscript": result.get("postscript", ""),
        "normalize": result.get("normalize", ""),
        "weight": result.get("weight", ""),
        "style": result.get("style", ""),
        "stretch": result.get("stretch", ""),
        "fontFile": Path(font_file).name if font_file else "",
    }


def audit_symbol_fonts(
    materialized: MaterializedSymbols,
    *,
    archive: Path,
    build_manifest_path: Path,
    reports_base: Path,
    project_root: Path,
    alias_config: Path = DEFAULT_FONT_ALIAS_CONFIG,
) -> FontAuditResult:
    """Resolve effective SVG fonts against the installed font environment."""
    manifest = load_symbol_manifest(build_manifest_path)
    font_audit_state = manifest.get("processing", {}).get("fontAudit")
    if manifest.get("formatVersion") == SYMBOL_BUILD_FONT_AUDIT_VERSION:
        if (
            not isinstance(font_audit_state, dict)
            or font_audit_state.get("status") != "failed"
        ):
            raise ValueError(
                "Font audit rerun requires a failed version-4 font audit state"
            )
        manifest = json.loads(json.dumps(manifest))
        manifest["formatVersion"] = SYMBOL_BUILD_PREFLIGHT_VERSION
        del manifest["processing"]["fontAudit"]
    preflight = manifest.get("processing", {}).get("svgPreflight", {})
    if (
        manifest.get("formatVersion") != SYMBOL_BUILD_PREFLIGHT_VERSION
        or preflight.get("status") != "passed"
    ):
        raise ValueError("Font audit requires passed version-3 SVG preflight state")

    tools = _font_tools()
    try:
        overrides = tools.load_font_reference_overrides(alias_config)
        exact_index, compact_index, font_file_count, face_count = tools.load_font_index()
    except RuntimeError as exc:
        raise ValueError(str(exc)) from exc

    rows: list[dict[str, Any]] = []
    references: dict[str, dict[str, Any]] = {}
    available_assets = 0
    missing_assets = 0
    no_text_assets = 0
    implicit_default_assets = 0
    unused_declarations = 0

    for asset in manifest["assets"]:
        archive_path = asset["archivePath"]
        path = materialized.raw_root.joinpath(*_portable_member(archive_path).parts)
        scan, error = tools.scan_svg(path)
        if scan is None:
            raise ValueError(
                f"Font audit could not parse {archive_path} after passed preflight: {error}"
            )

        used_fonts = scan["used_fonts"]
        declared_fonts = scan["declared_fonts"]
        active_text = scan["found_active_text"]
        used_keys = {tools.normal_key(value) for value in used_fonts}
        unused = sorted(
            (value for value in declared_fonts if tools.normal_key(value) not in used_keys),
            key=str.casefold,
        )
        unused_declarations += len(unused)
        resolved: list[dict[str, Any]] = []
        has_unresolved = False

        for reference in sorted(used_fonts, key=str.casefold):
            result = tools.find_font(
                reference,
                exact_index,
                compact_index,
                overrides=overrides,
            )
            if result["status"] in {"MISSING", "AMBIGUOUS"}:
                has_unresolved = True
            detail = {
                "reference": reference,
                "textRuns": used_fonts[reference],
                **_font_result_record(result),
            }
            resolved.append(detail)

            aggregate = references.setdefault(
                reference,
                {
                    "reference": reference,
                    "assetCount": 0,
                    "textRuns": 0,
                    **_font_result_record(result),
                },
            )
            current = _font_result_record(result)
            comparable = {
                key: value
                for key, value in aggregate.items()
                if key not in {"reference", "assetCount", "textRuns"}
            }
            if comparable != current:
                raise ValueError(
                    f"Font reference {reference!r} resolved inconsistently within one audit"
                )
            aggregate["assetCount"] += 1
            aggregate["textRuns"] += used_fonts[reference]

        if not active_text:
            category = "no_active_text"
            no_text_assets += 1
        elif not used_fonts:
            category = "fonts_available"
            available_assets += 1
            implicit_default_assets += 1
        elif has_unresolved:
            category = "fonts_missing"
            missing_assets += 1
        else:
            category = "fonts_available"
            available_assets += 1

        rows.append(
            {
                "archivePath": archive_path,
                "category": category,
                "activeText": active_text,
                "textRunCount": scan["text_runs"],
                "emptyTextObjectCount": scan["empty_text_objects"],
                "effectiveFonts": resolved,
                "unusedFontDeclarations": unused,
            }
        )

    reference_rows = sorted(references.values(), key=lambda row: row["reference"].casefold())
    summary = {
        "svgCount": len(rows),
        "fontAvailableAssetCount": available_assets,
        "fontMissingAssetCount": missing_assets,
        "noActiveTextAssetCount": no_text_assets,
        "implicitDefaultAssetCount": implicit_default_assets,
        "effectiveFontReferenceCount": len(reference_rows),
        "availableFontReferenceCount": sum(
            row["status"] == "FOUND" for row in reference_rows
        ),
        "missingFontReferenceCount": sum(
            row["status"] == "MISSING" for row in reference_rows
        ),
        "ambiguousFontReferenceCount": sum(
            row["status"] == "AMBIGUOUS" for row in reference_rows
        ),
        "genericFontReferenceCount": sum(
            row["status"] == "GENERIC" for row in reference_rows
        ),
        "normalizedAliasReferenceCount": sum(
            row["status"] == "FOUND" and row["normalize"] == "YES"
            for row in reference_rows
        ),
        "unusedDeclarationCount": unused_declarations,
    }
    if summary["svgCount"] != materialized.asset_count:
        raise ValueError(
            "Font audit count does not match materialized symbols: "
            f"{summary['svgCount']} != {materialized.asset_count}"
        )

    symbol_sha = manifest["snapshot"]["symbolArtifact"]["sha256"]
    report_root = reports_base / _work_name(archive, symbol_sha)
    report = report_root / "font-audit.json"
    document = {
        "format": FONT_AUDIT_FORMAT,
        "formatVersion": FONT_AUDIT_VERSION,
        "symbolArtifact": {"name": archive.name, "sha256": symbol_sha},
        "fontAliases": artifact_record(alias_config, project_root=project_root),
        "fontIndex": {
            "fontFileCount": font_file_count,
            "fontFaceCount": face_count,
        },
        "summary": dict(sorted(summary.items())),
        "fonts": reference_rows,
        "assets": sorted(rows, key=lambda row: row["archivePath"]),
    }
    _write_json(document, report)

    status = "passed" if missing_assets == 0 else "failed"
    updated = add_font_audit(
        manifest,
        status=status,
        summary=summary,
        report=report,
        aliases=alias_config,
        project_root=project_root,
    )
    write_symbol_manifest(updated, build_manifest_path)
    return FontAuditResult(report=report, summary=summary, status=status)


def detect_symbol_duplicates(
    materialized: MaterializedSymbols,
    *,
    archive: Path,
    build_manifest_path: Path,
    font_report: Path,
    reports_base: Path,
    project_root: Path,
    render_size: int = 512,
    jobs: int = 4,
    renderer: str = "resvg",
) -> DuplicateDetectionResult:
    """Detect exact/visual duplicates and persist canonical raw-asset mapping."""
    manifest = load_symbol_manifest(build_manifest_path)
    font_audit = manifest.get("processing", {}).get("fontAudit", {})
    if (
        manifest.get("formatVersion") != SYMBOL_BUILD_FONT_AUDIT_VERSION
        or font_audit.get("status") != "passed"
    ):
        raise ValueError(
            "Duplicate detection requires passed "
            f"version-{SYMBOL_BUILD_FONT_AUDIT_VERSION} font audit state"
        )
    if sha256_file(font_report) != font_audit["report"]["sha256"]:
        raise ValueError("Font audit report SHA-256 does not match army-symbol-build.json")

    try:
        font_document = json.loads(font_report.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not load font audit report {font_report}: {exc}") from exc
    if font_document.get("symbolArtifact") != {
        "name": archive.name,
        "sha256": manifest["snapshot"]["symbolArtifact"]["sha256"],
    }:
        raise ValueError("Font audit report is bound to a different symbol artifact")

    rows = font_document.get("assets")
    if not isinstance(rows, list):
        raise ValueError("Font audit report assets must be an array")
    file_categories: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Font audit report asset rows must be objects")
        archive_path = row.get("archivePath")
        category = row.get("category")
        if not isinstance(archive_path, str) or not isinstance(category, str):
            raise ValueError("Font audit report asset rows require archivePath/category")
        if archive_path in file_categories:
            raise ValueError(f"Font audit report repeats asset {archive_path}")
        file_categories[archive_path] = category

    asset_paths = {asset["archivePath"] for asset in manifest["assets"]}
    if set(file_categories) != asset_paths:
        raise ValueError("Font audit report asset set does not match army-symbol-build.json")

    symbol_sha = manifest["snapshot"]["symbolArtifact"]["sha256"]
    report_root = reports_base / _work_name(archive, symbol_sha)
    tools = _font_tools()
    try:
        result = tools.find_duplicate_svgs(
            materialized.raw_root,
            materialized.work_root,
            file_categories,
            render_size=render_size,
            jobs=jobs,
            renderer=renderer,
            reports_root=report_root,
        )
    except RuntimeError as exc:
        raise ValueError(str(exc)) from exc

    redundant = result["duplicate_representatives"]
    if not isinstance(redundant, dict):
        raise ValueError("Duplicate detector returned an invalid representative mapping")
    canonical = {path: redundant.get(path, path) for path in sorted(asset_paths)}
    for source, target in canonical.items():
        if target not in asset_paths:
            raise ValueError(
                f"Duplicate detector selected unknown representative {target} for {source}"
            )
        if canonical.get(target) != target:
            raise ValueError(
                f"Duplicate detector returned chained representative {source} -> {target}"
            )

    summary = {
        "sourceAssetCount": result["source_svg_files"],
        "uniqueByteSetCount": result["unique_byte_sets"],
        "rendersAvoidedExactCount": result["renders_avoided_exact"],
        "exactGroupCount": result["exact_groups"],
        "visualGroupCount": result["visual_groups"],
        "redundantAssetCount": result["redundant_files"],
        "canonicalAssetCount": len(set(canonical.values())),
        "renderErrorCount": result["render_errors"],
        "sourceAssetBytes": result["source_size_bytes"],
        "canonicalAssetBytes": result["canonical_size_bytes"],
        "reclaimedAssetBytes": result["reclaimed_size_bytes"],
    }
    if summary["sourceAssetCount"] != materialized.asset_count:
        raise ValueError(
            "Duplicate detector source count does not match materialized symbols: "
            f"{summary['sourceAssetCount']} != {materialized.asset_count}"
        )
    if result["canonical_svg_files"] != summary["canonicalAssetCount"]:
        raise ValueError(
            "Duplicate detector canonical count does not match canonical mapping: "
            f"{result['canonical_svg_files']} != {summary['canonicalAssetCount']}"
        )

    updated = add_duplicate_detection(
        manifest,
        summary=summary,
        canonical_by_archive_path=canonical,
        groups_report=result["report_path"],
        errors_report=result["error_path"],
        summary_report=result["summary_path"],
        renderer=result["renderer"],
        renderer_version=result["renderer_version"],
        render_size=result["render_size"],
        jobs=result["jobs"],
        project_root=project_root,
    )
    write_symbol_manifest(updated, build_manifest_path)
    return DuplicateDetectionResult(
        groups_report=result["report_path"],
        errors_report=result["error_path"],
        summary_report=result["summary_path"],
        summary=summary,
        canonical_by_archive_path=canonical,
        renderer=result["renderer"],
        renderer_version=result["renderer_version"],
        status="passed",
    )


def convert_symbol_text(
    materialized: MaterializedSymbols,
    *,
    archive: Path,
    build_manifest_path: Path,
    font_report: Path,
    reports_base: Path,
    project_root: Path,
    jobs: int = 4,
    text_converter: str = "inkscape-shell",
) -> TextConversionResult:
    """Convert active text on canonical assets and build the canonical work tree."""
    manifest = load_symbol_manifest(build_manifest_path)
    processing = manifest.get("processing", {})
    conversion_state = processing.get("textConversion")
    if manifest.get("formatVersion") == SYMBOL_BUILD_TEXT_CONVERSION_VERSION:
        if (
            not isinstance(conversion_state, dict)
            or conversion_state.get("status") != "failed"
        ):
            raise ValueError(
                "Text conversion rerun requires a failed "
                f"version-{SYMBOL_BUILD_TEXT_CONVERSION_VERSION} text conversion state"
            )
        manifest = json.loads(json.dumps(manifest))
        manifest["formatVersion"] = SYMBOL_BUILD_DUPLICATE_VERSION
        del manifest["processing"]["textConversion"]
        processing = manifest["processing"]

    duplicate = processing.get("duplicateDetection", {})
    if (
        manifest.get("formatVersion") != SYMBOL_BUILD_DUPLICATE_VERSION
        or duplicate.get("status") != "passed"
    ):
        raise ValueError(
            "Text conversion requires passed "
            f"version-{SYMBOL_BUILD_DUPLICATE_VERSION} duplicate-detection state"
        )

    font_audit = processing.get("fontAudit", {})
    if sha256_file(font_report) != font_audit["report"]["sha256"]:
        raise ValueError("Font audit report SHA-256 does not match army-symbol-build.json")
    try:
        font_document = json.loads(font_report.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not load font audit report {font_report}: {exc}") from exc

    if font_document.get("symbolArtifact") != {
        "name": archive.name,
        "sha256": manifest["snapshot"]["symbolArtifact"]["sha256"],
    }:
        raise ValueError("Font audit report is bound to a different symbol artifact")

    rows = font_document.get("assets")
    if not isinstance(rows, list):
        raise ValueError("Font audit report assets must be an array")
    categories: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Font audit report asset rows must be objects")
        archive_path = row.get("archivePath")
        category = row.get("category")
        if not isinstance(archive_path, str) or not isinstance(category, str):
            raise ValueError("Font audit report asset rows require archivePath/category")
        if archive_path in categories:
            raise ValueError(f"Font audit report repeats asset {archive_path}")
        categories[archive_path] = category

    canonical_map = duplicate.get("canonicalByArchivePath")
    if not isinstance(canonical_map, dict):
        raise ValueError("Duplicate-detection canonical mapping is invalid")
    canonical_paths = sorted({str(value) for value in canonical_map.values()})
    if set(categories) != {asset["archivePath"] for asset in manifest["assets"]}:
        raise ValueError("Font audit report asset set does not match army-symbol-build.json")

    conversion_root = materialized.work_root / "text-conversion"
    if conversion_root.exists():
        shutil.rmtree(conversion_root)
    available_root = conversion_root / "fonts_available"
    available_root.mkdir(parents=True)

    carried_forward: list[str] = []
    candidates: list[str] = []
    for archive_path in canonical_paths:
        category = categories.get(archive_path)
        source = materialized.raw_root.joinpath(*_portable_member(archive_path).parts)
        if category == "fonts_available":
            destination = available_root.joinpath(*_portable_member(archive_path).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            candidates.append(archive_path)
        elif category == "no_active_text":
            carried_forward.append(archive_path)
        else:
            raise ValueError(
                f"Canonical asset {archive_path} has unsupported conversion category {category!r}"
            )

    tools = _font_tools()
    try:
        exact_index, compact_index, _, _ = tools.load_font_index()
        result = tools.convert_available_svgs(
            conversion_root,
            exact_index,
            compact_index,
            overwrite=True,
            keep_failed=True,
            jobs=jobs,
            text_converter=text_converter,
        )
    except RuntimeError as exc:
        raise ValueError(str(exc)) from exc

    symbol_sha = manifest["snapshot"]["symbolArtifact"]["sha256"]
    report_root = reports_base / _work_name(archive, symbol_sha)
    report_root.mkdir(parents=True, exist_ok=True)
    report = report_root / "svg-text-to-path-report.csv"
    summary_report = report_root / "text-conversion-summary.csv"
    shutil.copy2(result["report_path"], report)
    shutil.copy2(result["summary_path"], summary_report)

    converted = int(result["converted"])
    failed = int(result["failed"])
    summary = {
        "canonicalAssetCount": len(canonical_paths),
        "conversionCandidateCount": len(candidates),
        "convertedAssetCount": converted,
        "carriedForwardAssetCount": len(carried_forward),
        "failedAssetCount": failed,
    }
    if converted + failed != len(candidates):
        raise ValueError(
            "Text converter result count does not match canonical conversion candidates"
        )

    status = "passed" if failed == 0 else "failed"
    canonical_root = materialized.work_root / "canonical"
    if status == "passed":
        staging = Path(
            tempfile.mkdtemp(prefix=".canonical-", dir=materialized.work_root)
        )
        try:
            for archive_path in carried_forward:
                source = materialized.raw_root.joinpath(*_portable_member(archive_path).parts)
                destination = staging.joinpath(*_portable_member(archive_path).parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            converted_root = conversion_root / "text_as_paths"
            for archive_path in candidates:
                source = converted_root.joinpath(*_portable_member(archive_path).parts)
                if not source.is_file():
                    raise ValueError(
                        f"Verified text conversion did not produce {archive_path}"
                    )
                destination = staging.joinpath(*_portable_member(archive_path).parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            actual = {
                path.relative_to(staging).as_posix()
                for path in staging.rglob("*.svg")
                if path.is_file()
            }
            if actual != set(canonical_paths):
                raise ValueError(
                    "Canonical conversion output does not contain exactly the canonical asset set"
                )
            if canonical_root.exists():
                shutil.rmtree(canonical_root)
            staging.replace(canonical_root)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    updated = add_text_conversion(
        manifest,
        status=status,
        summary=summary,
        report=report,
        summary_report=summary_report,
        converter=str(result["converter"]),
        converter_version=str(result.get("converter_version", "")),
        jobs=jobs,
        project_root=project_root,
    )
    write_symbol_manifest(updated, build_manifest_path)
    return TextConversionResult(
        canonical_root=canonical_root,
        report=report,
        summary_report=summary_report,
        summary=summary,
        converter=str(result["converter"]),
        converter_version=str(result.get("converter_version", "")),
        status=status,
    )


def _bind_compression_output_hashes(
    report: Path,
    *,
    profile_root: Path,
    canonical_paths: list[str],
) -> None:
    """Bind each balanced compression-report row to its exact output bytes."""
    try:
        with report.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)
    except OSError as exc:
        raise ValueError(f"Could not load compression report {report}: {exc}") from exc
    if "file" not in fieldnames or "profile" not in fieldnames:
        raise ValueError("Compression report requires file/profile columns")
    if "output_sha256" not in fieldnames:
        fieldnames.append("output_sha256")

    expected = set(canonical_paths)
    seen: set[str] = set()
    for row in rows:
        if row.get("profile") != "balanced":
            continue
        relative = row.get("file")
        if not isinstance(relative, str) or relative not in expected:
            raise ValueError(f"Compression report contains unexpected balanced asset: {relative}")
        if relative in seen:
            raise ValueError(f"Compression report repeats balanced asset: {relative}")
        seen.add(relative)
        output = profile_root.joinpath(*_portable_member(relative).parts)
        row["output_sha256"] = sha256_file(output)
    if seen != expected:
        raise ValueError("Compression report does not cover exactly the canonical asset set")

    with report.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def compress_symbol_work(
    materialized: MaterializedSymbols,
    *,
    archive: Path,
    build_manifest_path: Path,
    reports_base: Path,
    project_root: Path,
    jobs: int = 4,
    renderer: str = "resvg",
) -> CompressionResult:
    """Compress the complete version-6 canonical tree with production settings."""
    manifest = load_symbol_manifest(build_manifest_path)
    processing = manifest.get("processing", {})
    conversion = processing.get("textConversion", {})
    if (
        manifest.get("formatVersion") != SYMBOL_BUILD_TEXT_CONVERSION_VERSION
        or conversion.get("status") != "passed"
    ):
        raise ValueError(
            "Compression requires passed "
            f"version-{SYMBOL_BUILD_TEXT_CONVERSION_VERSION} text-conversion state"
        )

    duplicate = processing.get("duplicateDetection", {})
    canonical_map = duplicate.get("canonicalByArchivePath")
    if not isinstance(canonical_map, dict):
        raise ValueError("Duplicate-detection canonical mapping is invalid")
    canonical_paths = sorted({str(value) for value in canonical_map.values()})
    canonical_root = materialized.work_root / "canonical"
    if not canonical_root.is_dir():
        raise ValueError(f"Canonical symbol work tree is missing: {canonical_root}")
    actual_input = {
        path.relative_to(canonical_root).as_posix()
        for path in canonical_root.rglob("*.svg")
        if path.is_file()
    }
    if actual_input != set(canonical_paths):
        raise ValueError(
            "Canonical symbol work tree does not contain exactly the manifest canonical set"
        )

    target_sizes = [32, 64]
    dprs = [1.0, 2.0]
    balanced_precisions = [2, 3]
    max_rms = 0.01
    max_changed_fraction = 0.01
    pixel_diff_threshold = 8

    staging = Path(
        tempfile.mkdtemp(prefix=".compression-", dir=materialized.work_root)
    )
    try:
        tools = _compression_tools()
        try:
            result = tools.compress_svg_tree(
                canonical_root,
                staging / "run",
                profile="balanced",
                target_sizes=tuple(target_sizes),
                dprs=tuple(dprs),
                balanced_precisions=tuple(balanced_precisions),
                max_rms=max_rms,
                max_changed_fraction=max_changed_fraction,
                pixel_diff_threshold=pixel_diff_threshold,
                jobs=jobs,
                renderer=renderer,
            )
        except RuntimeError as exc:
            raise ValueError(str(exc)) from exc

        symbol_sha = manifest["snapshot"]["symbolArtifact"]["sha256"]
        report_root = reports_base / _work_name(archive, symbol_sha)
        report_root.mkdir(parents=True, exist_ok=True)
        report = report_root / "compression-report.csv"
        candidates_report = report_root / "compression-candidates.csv"
        run_report = report_root / "compression-run.json"

        actual_output = {
            path.relative_to(result.profile_root).as_posix()
            for path in result.profile_root.rglob("*.svg")
            if path.is_file()
        }
        if actual_output != set(canonical_paths):
            raise ValueError(
                "Compression output does not contain exactly the canonical asset set"
            )
        for relative in canonical_paths:
            output = result.profile_root.joinpath(*_portable_member(relative).parts)
            try:
                root = ET.parse(output).getroot()
            except (ET.ParseError, OSError) as exc:
                raise ValueError(
                    f"Compressed SVG is not parseable for {relative}: {exc}"
                ) from exc
            has_active_text, _, _ = _text_state(root)
            if has_active_text:
                raise ValueError(
                    f"Compressed SVG unexpectedly contains active text: {relative}"
                )

        _bind_compression_output_hashes(
            result.report,
            profile_root=result.profile_root,
            canonical_paths=canonical_paths,
        )

        source_bytes = int(result.summary["sourceBytes"])
        output_bytes = int(result.summary["outputBytes"])
        reclaimed_bytes = int(result.summary["reclaimedBytes"])
        summary = {
            "assetCount": int(result.summary["assetCount"]),
            "compressedAssetCount": int(result.summary["compressedAssetCount"]),
            "retainedAssetCount": int(result.summary["retainedAssetCount"]),
            "sourceBytes": source_bytes,
            "outputBytes": output_bytes,
            "reclaimedBytes": reclaimed_bytes,
        }
        if summary["assetCount"] != len(canonical_paths):
            raise ValueError(
                "Compression result count does not match canonical asset count"
            )

        report_sources = {
            report: result.report,
            candidates_report: result.candidates_report,
            run_report: result.run_report,
        }
        report_backups = staging / "report-backups"
        report_backups.mkdir()
        report_had_previous: dict[Path, bool] = {}
        report_replacements: dict[Path, Path] = {}
        for destination, source in report_sources.items():
            report_had_previous[destination] = destination.exists()
            if destination.exists():
                shutil.copy2(destination, report_backups / destination.name)
            replacement = destination.with_name(f".{destination.name}.compression-new")
            replacement.unlink(missing_ok=True)
            shutil.copy2(source, replacement)
            report_replacements[destination] = replacement

        compressed_root = materialized.work_root / "compressed"
        prepared = staging / "prepared"
        backup = materialized.work_root / ".compressed-previous"
        installed_reports: list[Path] = []
        had_previous = compressed_root.exists()
        tree_swapped = False
        try:
            for destination, replacement in report_replacements.items():
                replacement.replace(destination)
                installed_reports.append(destination)

            run_info = result.run_info
            renderer_version = str(run_info.get("renderer_version") or "")
            updated = add_compression(
                manifest,
                status="passed",
                summary=summary,
                report=report,
                candidates_report=candidates_report,
                run_report=run_report,
                profile="balanced",
                renderer=str(run_info.get("renderer") or renderer),
                target_sizes=target_sizes,
                dprs=dprs,
                balanced_precisions=balanced_precisions,
                max_rms=max_rms,
                max_changed_fraction=max_changed_fraction,
                pixel_diff_threshold=pixel_diff_threshold,
                jobs=jobs,
                project_root=project_root,
            )

            result.profile_root.replace(prepared)
            if backup.exists():
                shutil.rmtree(backup)
            if had_previous:
                compressed_root.replace(backup)
            prepared.replace(compressed_root)
            tree_swapped = True
            write_symbol_manifest(updated, build_manifest_path)
        except Exception:
            if tree_swapped and compressed_root.exists():
                shutil.rmtree(compressed_root)
            if had_previous and backup.exists() and not compressed_root.exists():
                backup.replace(compressed_root)
            for destination in installed_reports:
                previous = report_backups / destination.name
                if report_had_previous[destination]:
                    shutil.copy2(previous, destination)
                else:
                    destination.unlink(missing_ok=True)
            for replacement in report_replacements.values():
                replacement.unlink(missing_ok=True)
            raise
        else:
            shutil.rmtree(backup, ignore_errors=True)
        return CompressionResult(
            compressed_root=compressed_root,
            report=report,
            candidates_report=candidates_report,
            run_report=run_report,
            summary=summary,
            renderer=str(run_info.get("renderer") or renderer),
            renderer_version=renderer_version,
            status="passed",
        )
    finally:
        shutil.rmtree(staging, ignore_errors=True)
