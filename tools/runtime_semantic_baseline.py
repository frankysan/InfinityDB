"""Snapshot-pinned, read-only API/browser contract baseline for the P1 data cutover.

This is a focused parity check, not a browser interaction or release acceptance gate.
Capture once from the reviewed DB pair, then compare candidate DB pairs offline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import quote

from infinity_db.web import create_app, create_app_from_database_set
from tools.browser_wsgi_transport import wsgi_response

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = ROOT / "tests/fixtures/runtime-semantic-baseline-v1.json"
FORMAT = "InfinityDB P1 runtime semantic baseline"
FORMAT_VERSION = 1
ORIGIN = "http://runtime-baseline.test"
# These are artifact-byte identities, not game semantics. Retain source archive,
# citation and source-PDF hashes when checking a rebuilt/renamed database set.
_ARTIFACT_KEYS = frozenset({
    "armyDatabaseSha256", "rulesDatabaseSha256", "exportPairSha256",
    "deployedObjectPublicationSha256",
})

# A compact, fixed surface spanning every public data ownership boundary.
API_PATHS = (
    "/api/armies",
    "/api/version",
    "/static/restrictions-reference.json",
    "/api/unit-filters",
    "/api/units?limit=5&extended=1",
    "/api/skills",
    "/api/equipment",
    "/api/weapons",
    "/api/traits",
    "/api/fireteams",
    "/api/orders-aros",
    "/api/restrictions",
    "/api/deployed-objects",
    "/api/glossary",
    "/api/scenarios",
    "/api/scenarios?collection=its-18&revision=2026.09.01",
    "/api/search?q=camouflage",
    "/api/faq-rulings?topic_id=skill%3Acamouflage&rules_revision=5.3&as_of=2026-10-15",
    "/api/scenarios/domination?army_points=300",
    "/api/scenarios/battleground?army_points=300&collection=its-18&revision=2026.09.01",
)
SVG_PATHS = (
    "/api/scenarios/battleground/map.svg?army_points=300&collection=its-18&revision=2026.09.01",
)
HTML_PATHS: dict[str, tuple[str, ...]] = {
    "/": ("<html",),
    "/armies": ("<html",),
    "/units": ("<html",),
    "/fireteams": ("<html",),
    "/rules": ("<html",),
    "/rules/restrictions": ("Restrictions chart", "/static/restrictions-page.js"),
    "/scenarios": ("<html",),
    "/scenarios/battleground": ("<html",),
    "/deployed-objects": ("<html",),
    "/changes": ("<html",),
}
SVG_MARKERS = (
    'id="sector-center"', 'id="sector-near-a"', 'id="sector-near-b"',
    'id="deployment-a"', 'id="deployment-b"',
)
BROWSER_ASSET_MARKERS: dict[str, tuple[str, ...]] = {
    "/static/restrictions-page.js": ("getRestrictionsReference(controller.signal)",),
    "/static/restrictions-reference.js": ("developer-only", "not a complete list of legal actions"),
    "/static/api.js": ('getJson("/api/restrictions/chart"',),
    "/static/styles.css": ('html:not([data-developer-mode="true"]) .developer-only',),
}


class BaselineError(ValueError):
    """The selected runtime does not meet the baseline or an observed parity check."""


def _sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                   allow_nan=False).encode("utf-8")
    ).hexdigest()


def semantic_payload(value: Any) -> Any:
    """Strip only database-byte binding from sourceSnapshot, not actual source identity."""
    if isinstance(value, list):
        return [semantic_payload(item) for item in value]
    if isinstance(value, dict):
        return {
            key: (
                {name: semantic_payload(entry) for name, entry in item.items()
                 if name not in _ARTIFACT_KEYS}
                if key == "sourceSnapshot" and isinstance(item, dict)
                else semantic_payload(item)
            )
            for key, item in value.items()
        }
    return value


def _get(app: Any, path: str, *, expected_type: str) -> bytes:
    status, headers, body = wsgi_response(app, ORIGIN + path)
    header = dict((name.lower(), value) for name, value in headers)
    content_type = header.get("content-type", "").split(";", 1)[0]
    if status != 200 or content_type != expected_type:
        raise BaselineError(
            f"{path}: expected 200 {expected_type}, received {status} {content_type}"
        )
    return body


def _json(app: Any, path: str) -> dict[str, Any]:
    body = _get(app, path, expected_type="application/json")
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise BaselineError(f"{path}: expected a JSON object")
    return payload


def _details(app: Any) -> tuple[str, ...]:
    """Pin exact public identities to the baseline; never rediscover on comparison."""
    result: list[str] = []
    for catalog in ("units", "skills", "equipment"):
        data = _json(app, f"/api/{catalog}")
        items = data.get("items")
        if not isinstance(items, list) or not items:
            raise BaselineError(f"Cannot discover a public {catalog} item")
        selected = next(
            (item for item in items if isinstance(item, dict)
             and isinstance(item.get("slug"), str)), None
        )
        if selected is None:
            raise BaselineError(f"Cannot discover a public {catalog} slug")
        result.append(f"/api/{catalog}/{quote(selected['slug'], safe='')}")
    # /api/weapons is a compact listing without profile objects. Select a
    # citation-bearing Weapon using the verified release profile publication.
    if not app.weapon_profile_citations:
        raise BaselineError("Selected release lacks reviewed Weapon-profile citations")
    weapon_id = min(key[0] for key in app.weapon_profile_citations)
    slug = app.database.application_slug("weapons", weapon_id)
    if not slug:
        raise BaselineError(f"Cannot resolve reviewed Weapon {weapon_id}")
    result.append(f"/api/weapons/{quote(slug, safe='')}")
    return tuple(result)


def _variants(app: Any) -> tuple[str, ...]:
    publication = app.variant_usage
    if publication is None or not publication.get("variants"):
        raise BaselineError("Selected release lacks exact variant publication")
    records = sorted({
        row["variant"]["recordId"] for row in publication["variants"]
        if row["variant"]["recordId"].startswith(("skill:", "equipment:"))
    })
    result = []
    for prefix in ("skill:", "equipment:"):
        selected = next((record for record in records if record.startswith(prefix)), None)
        if selected is None:
            raise BaselineError(f"Selected release lacks reviewed {prefix} variants")
        result.append(f"/api/variant-usage?record_id={quote(selected, safe='')}")
    return tuple(result)


def capture(
    app: Any, *, paths: tuple[str, ...] | None = None,
    artifacts: dict[str, str] | None = None,
    route_aliases: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Capture complete canonical API semantics, representative HTML and Battleground SVG."""
    selected = paths if paths is not None else (*API_PATHS, *_details(app), *_variants(app),
                                                *SVG_PATHS, *HTML_PATHS, *BROWSER_ASSET_MARKERS)
    if len(selected) != len(set(selected)):
        raise BaselineError("Duplicate runtime baseline request")
    aliases = route_aliases or {}
    if set(aliases) - set(selected):
        raise BaselineError("Route aliases must refer to a pinned baseline request")
    probes: list[dict[str, Any]] = []
    for path in selected:
        requested_path = aliases.get(path, path)
        if not requested_path.startswith("/") or requested_path.startswith("//"):
            raise BaselineError(f"Invalid local route alias for {path!r}")
        if path.endswith(".svg") or "/map.svg?" in path:
            body = _get(app, requested_path, expected_type="image/svg+xml")
            text = body.decode("utf-8")
            markers = SVG_MARKERS
            kind = "svg"
            digest = hashlib.sha256(body).hexdigest()
        elif path in HTML_PATHS:
            body = _get(app, requested_path, expected_type="text/html")
            text = body.decode("utf-8")
            markers = HTML_PATHS[path]
            kind = "html"
            digest = None  # Versioned asset URLs change independently of game semantics.
        elif path in BROWSER_ASSET_MARKERS:
            kind = "stylesheet" if path.endswith(".css") else "javascript"
            body = _get(
                app, requested_path, expected_type="text/css" if kind == "stylesheet"
                else "text/javascript",
            )
            text = body.decode("utf-8")
            markers = BROWSER_ASSET_MARKERS[path]
            digest = None
        else:
            payload = _json(app, requested_path)
            if path.startswith("/api/variant-usage?") or path.startswith("/api/faq-rulings?"):
                if not payload.get("items"):
                    raise BaselineError(f"{path}: expected reviewed source rows")
            if path == "/api/version":
                # Preserve the response schema; exact app/database revisions
                # are recorded separately as baseline artifact identities.
                payload = {"fields": sorted(payload)}
            markers = ()
            kind = "json"
            digest = _digest(semantic_payload(payload))
        for marker in markers:
            if marker not in text:
                raise BaselineError(f"{path}: missing browser/geometry marker {marker!r}")
        probe: dict[str, Any] = {"path": path, "kind": kind}
        if digest is not None:
            probe["semanticSha256" if kind == "json" else "bytesSha256"] = digest
        if markers:
            probe["markers"] = list(markers)
        probes.append(probe)
    return {
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
        "artifacts": artifacts or {},
        "probes": probes,
    }


def _artifact_identity(army: Path, rules: Path) -> dict[str, str]:
    if not army.is_file() or not rules.is_file():
        raise BaselineError("Both Army and Rules databases must exist")
    result = {"armyDbSha256": _sha256(army), "rulesDbSha256": _sha256(rules)}
    for name, path in (
        ("weaponProfilePublicationSha256", army.with_name("weapon-profile-sources.json")),
        ("symbolPublicationSha256", ROOT / "data/manifests/symbol-publication.json"),
    ):
        # Rebuilt database sets may intentionally no longer have a JSON sidecar.
        # Exact original-artifact mode still detects that omission.
        if path.is_file():
            result[name] = _sha256(path)
    return result


def check(expected: dict[str, Any], observed: dict[str, Any],
          *, identical_artifacts: bool = False) -> int:
    if (expected.get("format") != FORMAT or expected.get("formatVersion") != FORMAT_VERSION
            or not isinstance(expected.get("probes"), list) or not expected["probes"]):
        raise BaselineError("Invalid pinned runtime baseline format")
    if identical_artifacts and expected.get("artifacts") != observed.get("artifacts"):
        raise BaselineError("Runtime artifact hashes differ from the pinned baseline")
    by_path = {row["path"]: row for row in expected["probes"]}
    actual = {row["path"]: row for row in observed["probes"]}
    if len(by_path) != len(expected["probes"]) or len(actual) != len(observed["probes"]):
        raise BaselineError("Duplicate baseline paths")
    if by_path.keys() != actual.keys():
        raise BaselineError(
            f"Probe paths differ: missing={sorted(by_path.keys() - actual.keys())}, "
            f"extra={sorted(actual.keys() - by_path.keys())}"
        )
    # Approved browser data-source migration changes only one JS marker.
    # Even in identical-artifact mode the pinned DB/publication hashes remain
    # strict; this exact browser marker swap carries no game semantic change.
    historical_chart_marker = ['getJson("/static/restrictions-reference.json"']
    embedded_chart_marker = ['getJson("/api/restrictions/chart"']
    marker_path = "/static/api.js"
    old = by_path.get(marker_path)
    new = actual.get(marker_path)
    if (
        old is not None and new is not None
        and old.get("markers") == historical_chart_marker
        and new.get("markers") == embedded_chart_marker
    ):
        by_path[marker_path] = {**old, "markers": embedded_chart_marker}
    differences = [
        path for path, row in by_path.items()
        if {key: value for key, value in row.items() if key != "path"}
        != {key: value for key, value in actual[path].items() if key != "path"}
    ]
    if differences:
        raise BaselineError(
            f"{len(differences)} runtime responses differ: {', '.join(differences[:12])}"
        )
    return len(actual)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--capture", action="store_true",
                        help="write a new, reviewed source baseline (never overwrite)")
    action.add_argument("--check", action="store_true",
                        help="compare a candidate offline without changing either database")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--army-db", type=Path)
    parser.add_argument("--rules-db", type=Path)
    parser.add_argument("--db-dir", type=Path,
                        help="check one complete embedded set through shared application startup")
    parser.add_argument("--identical-artifacts", action="store_true",
                        help="also require exact source database and publication bytes")
    parser.add_argument(
        "--route-alias", action="append", default=[], metavar="PINNED=>ACTUAL",
        help="explicitly map a retired baseline URL to its migrated local API route",
    )
    args = parser.parse_args(argv)
    if args.db_dir is not None and (args.army_db is not None or args.rules_db is not None):
        parser.error("--db-dir cannot be combined with --army-db or --rules-db")
    if args.db_dir is not None and args.capture:
        parser.error("--db-dir checks candidates; initial capture uses the reviewed release pair")
    if args.capture and (args.identical_artifacts or args.route_alias):
        parser.error("--identical-artifacts and --route-alias apply to --check")
    aliases: dict[str, str] = {}
    for value in args.route_alias:
        pinned, separator, actual = value.partition("=>")
        if not separator or not pinned.startswith("/") or not actual.startswith("/"):
            parser.error("--route-alias requires /pinned/route=>/actual/local/route")
        if pinned in aliases:
            parser.error(f"Duplicate route alias: {pinned}")
        aliases[pinned] = actual
    if args.capture and args.baseline.exists():
        parser.error(f"Baseline already exists: {args.baseline}")
    try:
        if args.check:
            expected = json.loads(args.baseline.read_text(encoding="utf-8"))
            if (not isinstance(expected, dict)
                    or not isinstance(expected.get("probes"), list)
                    or not expected["probes"]):
                raise BaselineError("Invalid baseline fixture")
            paths = tuple(row["path"] for row in expected["probes"])
        else:
            expected = None
            paths = None
        if args.db_dir is not None:
            app = create_app_from_database_set(args.db_dir)
            assert app.rules_database is not None
            army, rules = app.database.path, app.rules_database.path
        else:
            army = args.army_db or ROOT / "data/generated/infinity.db"
            rules = args.rules_db or ROOT / "data/generated/rules.db"
            app = create_app(army, rules)
        identity = _artifact_identity(army, rules)
        if args.capture and len(identity) != 4:
            raise BaselineError("Initial baseline needs both sidecars and the symbol manifest")
        observed = capture(app, paths=paths, artifacts=identity, route_aliases=aliases)
        if args.capture:
            args.baseline.parent.mkdir(parents=True, exist_ok=True)
            with args.baseline.open("x", encoding="utf-8", newline="\n") as handle:
                json.dump(observed, handle, ensure_ascii=False, sort_keys=True, indent=2)
                handle.write("\n")
            print(f"Baseline CAPTURED: {len(observed['probes'])} paths -> {args.baseline}")
        else:
            assert expected is not None
            count = check(expected, observed, identical_artifacts=args.identical_artifacts)
            print(f"Runtime semantic parity PASS: {count} pinned paths"
                  + (" (exact artifacts)" if args.identical_artifacts else ""))
        return 0
    except (BaselineError, OSError, ValueError, KeyError, sqlite3.Error) as exc:
        parser.exit(1, f"Runtime baseline BLOCKED: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
