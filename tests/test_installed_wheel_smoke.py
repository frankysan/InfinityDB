"""Isolation and destructive-operation boundaries of installed-wheel acceptance."""

from pathlib import Path

import pytest

from tools.installed_wheel_smoke import (
    SYMBOL_DIRECTORIES,
    clean_environment,
    remove_symbol_assets,
    smoke_wheel,
    verify_runtime,
)


def test_smoke_rejects_workspaces_inside_source_checkout(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="separate from the source checkout"):
        smoke_wheel(tmp_path / "demo.whl", tmp_path, tmp_path / "smoke", require_assets=True)


def test_smoke_does_not_reuse_or_overwrite_existing_environment(tmp_path: Path) -> None:
    source = tmp_path / "source"
    work = tmp_path / "smoke"
    work.mkdir()
    sentinel = work / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError, match="must be empty"):
        smoke_wheel(tmp_path / "demo.whl", source, work, require_assets=True)
    assert sentinel.read_text() == "keep"


def test_installed_runtime_verification_rejects_editable_application_imports(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="outside the installed environment"):
        verify_runtime(tmp_path, asset_free=False, require_assets=True)


def test_smoke_removes_developer_and_pip_redirect_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("PYTHONPATH", "PYTHONHOME", "PIP_TARGET", "GIT_INDEX_FILE", "VIRTUAL_ENV"):
        monkeypatch.setenv(name, "developer-only")
    env = clean_environment()
    assert not (
        {"PYTHONPATH", "PYTHONHOME", "PIP_TARGET", "GIT_INDEX_FILE", "VIRTUAL_ENV"} & env.keys()
    )
    assert env["PYTHONNOUSERSITE"] == "1"


def test_asset_free_smoke_refuses_removal_outside_disposable_environment(tmp_path: Path) -> None:
    outside = tmp_path / "real-source"
    target = outside / "armies"
    target.mkdir(parents=True)
    with pytest.raises(ValueError, match="outside the wheel environment"):
        remove_symbol_assets(outside, tmp_path / "venv", require_assets=False)
    assert target.is_dir()


def test_asset_free_smoke_requires_packaged_symbols_when_requested(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="symbol directory missing"):
        remove_symbol_assets(tmp_path / "static", tmp_path, require_assets=True)
    remove_symbol_assets(tmp_path / "static", tmp_path, require_assets=False)


def test_asset_free_smoke_removes_only_installed_symbol_directories(tmp_path: Path) -> None:
    static = tmp_path / "site-packages/static"
    for category in SYMBOL_DIRECTORIES:
        (static / category).mkdir(parents=True)
    script = static / "unit-symbols.js"
    script.write_text("keep", encoding="utf-8")
    remove_symbol_assets(static, tmp_path, require_assets=True)
    assert not any((static / category).exists() for category in SYMBOL_DIRECTORIES)
    assert script.read_text() == "keep"
