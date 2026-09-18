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
    add_svg_preflight,
    artifact_record,
    load_symbol_manifest,
    write_symbol_manifest,
)

SVG_PREFLIGHT_FORMAT = "InfinityDB SVG preflight audit"
SVG_PREFLIGHT_VERSION = 1
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
