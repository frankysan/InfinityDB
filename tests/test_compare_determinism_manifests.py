from __future__ import annotations

import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from tools import build_determinism_manifest as manifest_builder
from tools.compare_determinism_manifests import compare
from tools.compare_determinism_manifests import main as compare_main


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

    def build(
        _root: Path, *, legacy_paired: bool = False,
        diagnostics_output: Path | None = None,
    ) -> dict[str, object]:
        assert diagnostics_output is None
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


@pytest.mark.parametrize("occupied", ("manifest", "diagnostics"))
def test_manifest_cli_rejects_existing_evidence_before_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str], occupied: str,
) -> None:
    manifest_path = tmp_path / "manifest.json"
    diagnostic_path = tmp_path / "diagnostics.json"
    occupied_path = manifest_path if occupied == "manifest" else diagnostic_path
    original = b'{"previous": "accepted evidence"}\n'
    occupied_path.write_bytes(original)

    def unexpected_build(*args: object, **kwargs: object) -> object:
        pytest.fail("Preflight should reject occupied output before building")

    monkeypatch.setattr(manifest_builder, "build_manifest", unexpected_build)
    with pytest.raises(SystemExit) as error:
        manifest_builder.main([
            "--output", str(manifest_path),
            "--diagnostics-output", str(diagnostic_path),
        ])
    assert error.value.code == 1
    assert "already exists" in capsys.readouterr().err
    assert occupied_path.read_bytes() == original
    other = diagnostic_path if occupied == "manifest" else manifest_path
    assert not other.exists()


def test_manifest_cli_rejects_same_normalized_output_before_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def unexpected_build(*args: object, **kwargs: object) -> object:
        pytest.fail("Same path selected for two outputs must fail before building")

    monkeypatch.setattr(manifest_builder, "build_manifest", unexpected_build)
    output = tmp_path / "manifest.json"
    with pytest.raises(SystemExit) as error:
        manifest_builder.main([
            "--output", str(output),
            "--diagnostics-output", str(tmp_path / "subdir" / ".." / "manifest.json"),
        ])
    assert error.value.code == 1
    assert "different files" in capsys.readouterr().err
    assert not output.exists()


def test_manifest_cli_rejects_dangling_symlink_before_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "manifest.json"
    # Creating symlinks may require additional privileges on Windows.
    monkeypatch.setattr(type(output), "is_symlink", lambda path: path == output)

    def unexpected_build(*args: object, **kwargs: object) -> object:
        pytest.fail("Symlink output must fail before building")

    monkeypatch.setattr(manifest_builder, "build_manifest", unexpected_build)
    with pytest.raises(SystemExit) as error:
        manifest_builder.main(["--output", str(output)])
    assert error.value.code == 1
    assert "already exists" in capsys.readouterr().err
    assert not output.exists()


def test_direct_manifest_builder_rejects_existing_diagnostics_before_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    diagnostics = tmp_path / "diagnostics.json"
    original = b"prior detailed diagnostics\n"
    diagnostics.write_bytes(original)

    def unexpected_run(*args: object, **kwargs: object) -> None:
        pytest.fail("Existing diagnostics must fail before the expensive build")

    monkeypatch.setattr(manifest_builder, "_run", unexpected_run)
    with pytest.raises(FileExistsError, match="already exists"):
        manifest_builder.build_manifest(tmp_path, diagnostics_output=diagnostics)
    assert diagnostics.read_bytes() == original


def test_manifest_cli_does_not_replace_output_created_during_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "manifest.json"
    original = b"another writer's output\n"

    def build(*args: object, **kwargs: object) -> dict[str, object]:
        output.write_bytes(original)
        return {
            "format": manifest_builder.FORMAT,
            "formatVersion": 2,
            "artifacts": {"build/army.db": "a" * 64},
        }

    monkeypatch.setattr(manifest_builder, "build_manifest", build)
    with pytest.raises(SystemExit) as error:
        manifest_builder.main(["--output", str(output)])
    assert error.value.code == 1
    captured = capsys.readouterr()
    assert "already exists" in captured.err
    assert "Determinism manifest:" not in captured.out
    assert output.read_bytes() == original


def test_manifest_output_uses_canonical_json_and_exclusive_creation(
    tmp_path: Path,
) -> None:
    output = tmp_path / "nested" / "manifest.json"
    document = {"z": "Å", "a": {"value": 1}}
    manifest_builder._write_new_json(output, document)
    from infinity_army_data.deterministic_io import json_text

    original = json_text(document, sort_keys=True).encode("utf-8")
    assert output.read_bytes() == original
    with pytest.raises(FileExistsError, match="already exists"):
        manifest_builder._write_new_json(output, {"replacement": True})
    assert output.read_bytes() == original


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


def test_sqlite_diagnostics_separate_writer_header_from_relational_content(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "data.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, name TEXT)")
        connection.executemany(
            "INSERT INTO records (id, name) VALUES (?, ?)",
            [(1, "first"), (2, "second")],
        )
    reference = manifest_builder._sqlite_diagnostics(database_path)
    changed = tmp_path / "writer-version.db"
    original = database_path.read_bytes()
    changed.write_bytes(original[:96] + (3099999).to_bytes(4, "big") + original[100:])
    diagnostic = manifest_builder._sqlite_diagnostics(changed)
    assert reference["tableDigests"] == diagnostic["tableDigests"]
    assert reference["headerNeutralizedSha256"] == (
        diagnostic["headerNeutralizedSha256"]
    )
    assert reference["headerWriterVersion"] != diagnostic["headerWriterVersion"]


def test_zip_diagnostics_separate_member_contents_from_deflate_bytes(
    tmp_path: Path,
) -> None:
    plain, compressed = tmp_path / "stored.zip", tmp_path / "compressed.zip"
    for path, method in (
        (plain, zipfile.ZIP_STORED), (compressed, zipfile.ZIP_DEFLATED),
    ):
        with zipfile.ZipFile(path, "w", compression=method) as archive:
            archive.writestr("member.txt", b"Same source bytes! " * 50)
    first = manifest_builder._zip_diagnostics(plain)["members"]["member.txt"]
    second = manifest_builder._zip_diagnostics(compressed)["members"]["member.txt"]
    assert first["sha256"] == second["sha256"]
    assert first["crc"] == second["crc"]
    assert first["compressSize"] != second["compressSize"]


def test_comparator_cli_accepts_explicit_manifest_paths(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    windows = _write(
        tmp_path / "windows.json", {"build/army.db": "a" * 64}, version=2,
    )
    linux = _write(
        tmp_path / "linux.json", {"build/army.db": "b" * 64}, version=2,
    )
    assert compare_main([str(windows), str(linux)]) == 1
    output = capsys.readouterr().out
    assert "Cross-platform deterministic output mismatch" in output
    assert "build/army.db" in output


def test_comparator_cli_preserves_directory_discovery(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    _write(
        tmp_path / "windows" / "determinism-manifest.json",
        {"build/army.db": "a" * 64}, version=2,
    )
    _write(
        tmp_path / "linux" / "determinism-manifest.json",
        {"build/army.db": "a" * 64}, version=2,
    )
    assert compare_main([str(tmp_path)]) == 0
    assert "verified across 2 manifests" in capsys.readouterr().out


def test_compare_requires_multiple_manifests(tmp_path: Path) -> None:
    only = _write(tmp_path / "only.json", {"build/army.db": "a" * 64})
    with pytest.raises(ValueError, match="At least two"):
        compare([only])
