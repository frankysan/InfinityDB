from __future__ import annotations

from pathlib import Path

from infinity_army_data.project_resources import (
    maintained_config_path,
    maintained_curated_path,
    maintained_documentation_path,
    maintained_manifest_path,
)


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

def test_maintained_manifest_prefers_source_checkout(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    prefix = tmp_path / "prefix"
    source = source_root / "data" / "manifests" / "symbol-publication.json"
    installed = (
        prefix
        / "share"
        / "infinity-db"
        / "data"
        / "manifests"
        / "symbol-publication.json"
    )
    source.parent.mkdir(parents=True)
    installed.parent.mkdir(parents=True)
    source.write_text("source", encoding="utf-8")
    installed.write_text("installed", encoding="utf-8")

    assert (
        maintained_manifest_path(
            "symbol-publication.json",
            source_root=source_root,
            install_prefix=prefix,
        )
        == source
    )


def test_maintained_manifest_falls_back_to_installed_share(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    prefix = tmp_path / "prefix"
    installed = (
        prefix
        / "share"
        / "infinity-db"
        / "data"
        / "manifests"
        / "symbol-publication.json"
    )
    installed.parent.mkdir(parents=True)
    installed.write_text("installed", encoding="utf-8")

    assert (
        maintained_manifest_path(
            "symbol-publication.json",
            source_root=source_root,
            install_prefix=prefix,
        )
        == installed
    )


def test_maintained_documentation_prefers_source_checkout(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    prefix = tmp_path / "prefix"
    source = source_root / "docs" / "CHANGELOG.md"
    installed = prefix / "share" / "infinity-db" / "docs" / "CHANGELOG.md"
    source.parent.mkdir(parents=True)
    installed.parent.mkdir(parents=True)
    source.write_text("source", encoding="utf-8")
    installed.write_text("installed", encoding="utf-8")

    assert (
        maintained_documentation_path(
            "CHANGELOG.md",
            source_root=source_root,
            install_prefix=prefix,
        )
        == source
    )


def test_maintained_documentation_falls_back_to_installed_share(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    prefix = tmp_path / "prefix"
    installed = prefix / "share" / "infinity-db" / "docs" / "CHANGELOG.md"
    installed.parent.mkdir(parents=True)
    installed.write_text("installed", encoding="utf-8")

    assert (
        maintained_documentation_path(
            "CHANGELOG.md",
            source_root=source_root,
            install_prefix=prefix,
        )
        == installed
    )


def test_readme_publishes_user_facing_privacy_policy() -> None:
    root = Path(__file__).resolve().parents[1]
    readme = (root / "README.md").read_text(encoding="utf-8")
    normalized = " ".join(readme.split())

    assert "## Privacy policy" in readme
    assert "without visitor-level tracking" in normalized
    assert "`sessionStorage` by default" in readme
    assert "does not use `localStorage`" in readme
    assert "Persistent cookies are opt-in" in readme
    assert "for up to one year" in readme
    assert "query or search terms" in readme
