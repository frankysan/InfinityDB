"""Opt-in repeatable source-ZIP acceptance for the complete SQLite runtime set.

This is a maintained development/release diagnostic. Outputs are isolated under
ignored local/ and discarded; tracked release files are never modified.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from infinity_db.build_provenance import file_sha256
from infinity_db.cli import _build_army, build_parser
from infinity_db.database_set import validate_database_set
from infinity_db.database_set_builder import build_database_set
from infinity_db.rules_database import RulesDatabase
from infinity_db.weapon_profile_publication import load_weapon_profile_publication
from infinity_db.web import create_app
from tools.browser_wsgi_transport import wsgi_response
from tools.runtime_semantic_baseline import DEFAULT_BASELINE, capture, check

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://database-set-acceptance.test"


def _api(app: Callable[..., Any], route: str) -> dict:
    status, _headers, body = wsgi_response(app, ORIGIN + route)
    if status != 200:
        raise ValueError(f"Source-build HTTP acceptance failed: {route} ({status})")
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError(f"Source-build HTTP response is not an object: {route}")
    return payload


def verify(source: Path, expected_sha256: str) -> dict:
    """Rebuild twice, verify byte determinism and public citation semantics."""
    source = source.resolve()
    if not source.is_file() or file_sha256(source) != expected_sha256:
        raise ValueError("Selected source ZIP does not match its expected SHA-256")
    expected = load_weapon_profile_publication(
        ROOT / "data/generated/weapon-profile-sources.json",
        ROOT / "data/generated/infinity.db",
        ROOT / "data/generated/rules.db",
    )
    if expected is None:
        raise ValueError("Tracked release lacks reviewed Weapon citation baseline")

    scratch = ROOT / "local"
    scratch.mkdir(exist_ok=True)
    reports = []
    with tempfile.TemporaryDirectory(prefix="complete-build-acceptance-", dir=scratch) as temp:
        for attempt in (1, 2):
            destination = Path(temp) / f"attempt-{attempt}"
            args = build_parser().parse_args(
                ["build", str(source), "--db-dir", str(destination), "--compact"]
            )
            result = build_database_set(args, _build_army)
            report = validate_database_set(destination)
            if report != result or report["layout"] != "v13-two-file":
                raise ValueError("Complete-build database health disagrees with publication")
            if set(report["sha256"]) != {"infinity.db", "rules.db"}:
                raise ValueError("Complete build produced an unexpected runtime file set")
            inventory = (
                report["variantGroups"], report["reviewedWeapons"], report["restrictionChartRows"],
            )
            if inventory != (151, 62, 6):
                raise ValueError("Complete build changed the reviewed source inventory")

            citations = RulesDatabase(
                destination / "rules.db"
            ).weapon_profile_citations_payload(destination / "infinity.db")
            if citations != expected:
                raise ValueError("Complete build changed reviewed Weapon citation semantics")
            app = create_app(
                destination / "infinity.db", rules_database_path=destination / "rules.db",
            )
            weapon = _api(app, "/api/weapons/uragan-mrl")
            if not weapon["profile_citations_available"] or not all(
                profile["profile_citations"] for profile in weapon["profiles"]
            ):
                raise ValueError("Reviewed Weapon chart locators are absent from the HTTP API")
            variant = _api(app, "/api/variant-usage?record_id=skill:tagcom")
            if not variant.get("items"):
                raise ValueError("Embedded exact variant usage is absent from the HTTP API")
            chart = _api(app, "/api/restrictions/chart")
            expected_chart = json.loads(
                (ROOT / "src/infinity_db/web/static/restrictions-reference.json").read_text(
                    encoding="utf-8"
                )
            )
            if chart != expected_chart:
                raise ValueError("Embedded Restrictions chart differs from source publication")
            baseline = json.loads(DEFAULT_BASELINE.read_text(encoding="utf-8"))
            observed = capture(
                app, paths=tuple(item["path"] for item in baseline["probes"]),
            )
            if check(baseline, observed) != len(baseline["probes"]):
                raise ValueError("Runtime semantic baseline is incomplete")
            reports.append(report)
            print(
                f"Complete build {attempt}: v13 healthy, 62 Weapons, "
                f"69 citation rows, 6 chart rows, 41 baseline routes; "
                f"hashes {json.dumps(report['sha256'], sort_keys=True)}",
                flush=True,
            )
        if reports[0]["sha256"] != reports[1]["sha256"]:
            raise ValueError("Repeated complete builds differ at the SQLite byte level")
        if reports[0]["buildProvenance"] != reports[1]["buildProvenance"]:
            raise ValueError("Repeated complete builds differ in source provenance")

    return {
        "status": "pass",
        "sourceSha256": expected_sha256,
        "buildSetId": reports[0]["buildProvenance"]["buildSetId"],
        "layout": reports[0]["layout"],
        "sha256": reports[0]["sha256"],
        "reviewedWeapons": reports[0]["reviewedWeapons"],
        "variantGroups": reports[0]["variantGroups"],
        "restrictionChartRows": reports[0]["restrictionChartRows"],
        "rebuilds": 2,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Pinned local immutable Army ZIP")
    parser.add_argument(
        "--sha256", required=True, help="Expected exact source archive SHA-256",
    )
    args = parser.parse_args(argv)
    if len(args.sha256) != 64 or any(char not in "0123456789abcdef" for char in args.sha256):
        parser.error("--sha256 must be 64 lowercase hexadecimal characters")
    try:
        print(json.dumps(verify(args.source, args.sha256), sort_keys=True, indent=2))
    except (OSError, ValueError) as exc:
        print(f"Complete-build acceptance: FAIL: {exc}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
