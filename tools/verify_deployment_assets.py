#!/usr/bin/env python3
"""Verify tracked runtime databases and the published symbol set for deployment."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from infinity_db.deployment_provenance import (
    DeploymentProvenanceError,
    validate_database_symbol_provenance,
)
from infinity_db.rules_database import RulesDatabase
from infinity_db.variant_usage_reference import load_variant_usage_publication

try:
    from tools.asset_validation import (
        AssetSetValidation,
        AssetValidationError,
        validate_asset_set,
    )
except ImportError:  # pragma: no cover - direct script execution fallback
    from asset_validation import (  # type: ignore[no-redef]
        AssetSetValidation,
        AssetValidationError,
        validate_asset_set,
    )

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATIC_ROOT = PROJECT_ROOT / "src" / "infinity_db" / "web" / "static"
DEFAULT_DATABASE = PROJECT_ROOT / "data" / "generated" / "infinity.db"
DEFAULT_RULES_DATABASE = PROJECT_ROOT / "data" / "generated" / "rules.db"
DEFAULT_PUBLICATION_MANIFEST = PROJECT_ROOT / "data" / "manifests" / "symbol-publication.json"


class DeploymentAssetError(ValueError):
    """Raised when tracked deployment data or published symbols are incomplete."""


def _require_complete_asset_set(validation: AssetSetValidation) -> None:
    if validation.complete:
        return
    details: list[str] = [validation.state]
    if validation.missing:
        details.append(f"missing {len(validation.missing)}")
    if validation.browser_missing:
        details.append(f"browser-missing {len(validation.browser_missing)}")
    if validation.unexpected:
        details.append(f"unexpected {len(validation.unexpected)}")
    if validation.invalid:
        details.append(f"invalid {len(validation.invalid)}")
    raise DeploymentAssetError(
        "Published symbol set does not satisfy its publication/browser contract ("
        + ", ".join(details)
        + ")"
    )


def verify_deployment_assets(
    static_root: Path = DEFAULT_STATIC_ROOT,
    *,
    database_path: Path = DEFAULT_DATABASE,
    rules_database_path: Path = DEFAULT_RULES_DATABASE,
    publication_manifest_path: Path = DEFAULT_PUBLICATION_MANIFEST,
) -> AssetSetValidation:
    """Validate the release databases and symbols using tracked repository artifacts only."""

    validation = validate_asset_set(
        static_root, publication_manifest=publication_manifest_path
    )
    _require_complete_asset_set(validation)

    verify_runtime_artifacts(database_path, rules_database_path, publication_manifest_path)
    verify_variant_release_publication(database_path, rules_database_path)
    return validation


def verify_runtime_artifacts(
    database_path: Path,
    rules_database_path: Path,
    publication_manifest_path: Path,
) -> None:
    """Validate database schemas and source binding independently of SVG availability."""
    validate_database_symbol_provenance(database_path, publication_manifest_path)
    RulesDatabase(rules_database_path).validate()


def verify_variant_release_publication(
    database_path: Path, rules_database_path: Path,
) -> None:
    """Require the tracked, release-paired exact-variant publication before packaging."""
    directory = database_path.parent
    publication = load_variant_usage_publication(
        directory / "variant-usage.json",
        database_path,
        rules_database_path,
        directory / "deployed-objects.json",
    )
    if publication is None or not publication["variants"]:
        raise DeploymentAssetError("Release-matched variant-usage.json is missing or empty")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-svg", action="store_true",
        help="check database schemas and snapshot binding without requiring SVG files",
    )
    parser.add_argument(
        "--static-root",
        type=Path,
        default=DEFAULT_STATIC_ROOT,
        help="Published browser static root (default: repository web/static directory)",
    )
    parser.add_argument(
        "--database", type=Path, default=DEFAULT_DATABASE, help="Tracked runtime infinity.db"
    )
    parser.add_argument(
        "--rules-database",
        type=Path,
        default=DEFAULT_RULES_DATABASE,
        help="Tracked runtime rules.db",
    )
    parser.add_argument(
        "--publication-manifest",
        type=Path,
        default=DEFAULT_PUBLICATION_MANIFEST,
        help="Tracked canonical symbol publication manifest",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.skip_svg:
            verify_runtime_artifacts(
                args.database, args.rules_database, args.publication_manifest,
            )
            verify_variant_release_publication(args.database, args.rules_database)
            print("Runtime databases and variant publication valid; SVG validation skipped")
            return 0
        validation = verify_deployment_assets(
            args.static_root,
            database_path=args.database,
            rules_database_path=args.rules_database,
            publication_manifest_path=args.publication_manifest,
        )
    except (
        DeploymentAssetError,
        DeploymentProvenanceError,
        AssetValidationError,
        sqlite3.Error,
        ValueError,
    ) as exc:
        print(f"ERROR: {exc}")
        return 1

    print(
        "Deployment release artifacts verified: "
        f"{validation.present_count}/{validation.expected_count} published SVGs; "
        f"{validation.browser_present_count}/{validation.browser_expected_count} "
        "browser-referenced; runtime databases and variant publication source-matched"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
