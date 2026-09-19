from __future__ import annotations

from pathlib import Path

from infinity_army_data.project_resources import maintained_config_path, maintained_curated_path


def test_maintained_config_prefers_source_checkout(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    prefix = tmp_path / "prefix"
    source = source_root / "config" / "catalogs" / "example.json"
    installed = prefix / "share" / "infinity-db" / "config" / "catalogs" / "example.json"
    source.parent.mkdir(parents=True)
    installed.parent.mkdir(parents=True)
    source.write_text("source", encoding="utf-8")
    installed.write_text("installed", encoding="utf-8")

    assert (
        maintained_config_path(
            "catalogs",
            "example.json",
            source_root=source_root,
            install_prefix=prefix,
        )
        == source
    )


def test_maintained_config_falls_back_to_installed_share(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    prefix = tmp_path / "prefix"
    installed = prefix / "share" / "infinity-db" / "config" / "identity" / "example.json"
    installed.parent.mkdir(parents=True)
    installed.write_text("installed", encoding="utf-8")

    assert (
        maintained_config_path(
            "identity",
            "example.json",
            source_root=source_root,
            install_prefix=prefix,
        )
        == installed
    )


def test_maintained_curated_prefers_source_checkout(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    prefix = tmp_path / "prefix"
    source = source_root / "data" / "curated" / "identities" / "example.json"
    installed = (
        prefix
        / "share"
        / "infinity-db"
        / "data"
        / "curated"
        / "identities"
        / "example.json"
    )
    source.parent.mkdir(parents=True)
    installed.parent.mkdir(parents=True)
    source.write_text("source", encoding="utf-8")
    installed.write_text("installed", encoding="utf-8")

    assert (
        maintained_curated_path(
            "identities",
            "example.json",
            source_root=source_root,
            install_prefix=prefix,
        )
        == source
    )


def test_maintained_curated_falls_back_to_installed_share(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    prefix = tmp_path / "prefix"
    installed = (
        prefix
        / "share"
        / "infinity-db"
        / "data"
        / "curated"
        / "identities"
        / "example.json"
    )
    installed.parent.mkdir(parents=True)
    installed.write_text("installed", encoding="utf-8")

    assert (
        maintained_curated_path(
            "identities",
            "example.json",
            source_root=source_root,
            install_prefix=prefix,
        )
        == installed
    )
