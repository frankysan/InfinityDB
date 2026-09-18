"""Materialize and structurally audit immutable raw symbol snapshots."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, NamedTuple

from infinity_db.snapshot_provenance import load_snapshot_manifest, sha256_file
from infinity_db.symbol_manifest import (
    SYMBOL_BUILD_FONT_AUDIT_VERSION,
    add_duplicate_detection,
    add_font_audit,
    add_svg_preflight,
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
    preflight = manifest.get("processing", {}).get("svgPreflight", {})
    if manifest.get("formatVersion") != 3 or preflight.get("status") != "passed":
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
    }
    if summary["sourceAssetCount"] != materialized.asset_count:
        raise ValueError(
            "Duplicate detector source count does not match materialized symbols: "
            f"{summary['sourceAssetCount']} != {materialized.asset_count}"
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
