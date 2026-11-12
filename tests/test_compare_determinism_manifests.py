from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import build_determinism_manifest as manifest_builder
from tools.compare_determinism_manifests import compare


def _write(
    path: Path, artifacts: dict[str, str], *, version: int = 1,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "format": "InfinityDB cross-platform determinism manifest",
                "formatVersion": version,
                "artifacts": artifacts,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def test_compare_accepts_identical_manifests(tmp_path: Path) -> None:
    first = _write(tmp_path / "linux.json", {"build/army.db": "a" * 64})
    second = _write(tmp_path / "windows.json", {"build/army.db": "a" * 64})
    assert compare([first, second]) == []


def test_compare_reports_missing_or_changed_artifacts(tmp_path: Path) -> None:
    first = _write(
        tmp_path / "linux.json",
        {"build/army.db": "a" * 64, "archives/work.zip": "b" * 64},
    )
    second = _write(tmp_path / "windows.json", {"build/army.db": "c" * 64})
    errors = compare([first, second])
    assert any("build/army.db" in error for error in errors)
    assert any("archives/work.zip" in error for error in errors)


def test_compare_accepts_matching_rawless_v2_manifests(tmp_path: Path) -> None:
    first = _write(tmp_path / "linux.json", {"build/army.db": "a" * 64}, version=2)
    second = _write(tmp_path / "windows.json", {"build/army.db": "a" * 64}, version=2)
    assert compare([first, second]) == []


def test_compare_refuses_mixed_v1_and_v2_without_dropping_raw_evidence(
    tmp_path: Path,
) -> None:
    legacy = _write(
        tmp_path / "legacy.json",
        {"build/army.db": "a" * 64, "build/army.raw.db": "b" * 64},
    )
    rawless = _write(
        tmp_path / "rawless.json", {"build/army.db": "a" * 64}, version=2,
    )
    with pytest.raises(ValueError, match="Cannot compare determinism manifest v1"):
        compare([legacy, rawless])


@pytest.mark.parametrize("version", [0, 3, True])
def test_compare_rejects_unknown_versions(tmp_path: Path, version: int) -> None:
    first = _write(tmp_path / "first.json", {"build/army.db": "a" * 64})
    second = _write(
        tmp_path / "second.json", {"build/army.db": "a" * 64}, version=version,
    )
    with pytest.raises(ValueError, match="Unexpected determinism manifest version"):
        compare([first, second])


@pytest.mark.parametrize("legacy, expected_version", [(False, 2), (True, 1)])
def test_manifest_cli_selects_explicit_legacy_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    legacy: bool, expected_version: int,
) -> None:
    calls: list[bool] = []

    def build(_root: Path, *, legacy_paired: bool = False) -> dict[str, object]:
        calls.append(legacy_paired)
        return {
            "format": manifest_builder.FORMAT,
            "formatVersion": 1 if legacy_paired else 2,
            "artifacts": {"build/army.db": "a" * 64},
        }

    monkeypatch.setattr(manifest_builder, "build_manifest", build)
    output = tmp_path / "manifest.json"
    args = ["--output", str(output)]
    if legacy:
        args.append("--legacy-paired")
    assert manifest_builder.main(args) == 0
    assert calls == [legacy]
    assert json.loads(output.read_text(encoding="utf-8"))["formatVersion"] == (
        expected_version
    )


def test_manifest_fixture_copy_normalizes_only_json_line_endings(
    tmp_path: Path,
) -> None:
    first = tmp_path / "windows-fixture"
    second = tmp_path / "linux-fixture"
    for root, newline in ((first, b"\r\n"), (second, b"\n")):
        root.mkdir()
        (root / "101-test-army.json").write_bytes(
            newline.join((b'{"version":"test",', b'"units":[]}')) + newline,
        )
        (root / "binary.dat").write_bytes(b"\x00\r\nkeep")
    windows_copy = manifest_builder._canonical_fixture_copy(
        first, tmp_path / "canonical-windows",
    )
    linux_copy = manifest_builder._canonical_fixture_copy(
        second, tmp_path / "canonical-linux",
    )
    assert (windows_copy / "101-test-army.json").read_bytes() == (
        linux_copy / "101-test-army.json"
    ).read_bytes()
    assert (windows_copy / "binary.dat").read_bytes() == b"\x00\r\nkeep"
    assert (first / "101-test-army.json").read_bytes() != (
        second / "101-test-army.json"
    ).read_bytes()


def test_compare_requires_multiple_manifests(tmp_path: Path) -> None:
    only = _write(tmp_path / "only.json", {"build/army.db": "a" * 64})
    with pytest.raises(ValueError, match="At least two"):
        compare([only])
