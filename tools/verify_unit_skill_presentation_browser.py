#!/usr/bin/env python3
"""Optional Chromium acceptance for Unit detail shared and specific item rows.

The normal Unit API is the expected source. This checks client-rendered DOM
placement and links, not semantic source correctness or every possible Unit.
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
from contextlib import nullcontext
from dataclasses import dataclass
from decimal import Decimal
from functools import partial
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

from tools.browser_wsgi_transport import route_browser_page
from tools.verify_non_skill_army_browser import CASES, WIDTHS

DEFAULT_SLUGS = tuple(case.slug for case in CASES)
OPTIONAL_FLAGS = ("mercs", "specops", "teamops", "reinforcement")
_DISTANCE_NUMBER = re.compile(r"[+-]?\d+(?:\.\d+)?")
BUCKETS = (
    ("skills", "Skills", "skills"),
    ("equipment", "Equipment", "equipment"),
    ("weapons", "Weapons", "weapons"),
    ("training", "Training", None),
    ("attribute_overrides", "Attribute overrides", None),
)


@dataclass(frozen=True)
class ItemExpectation:
    label: str
    name: str
    href: str | None
    quantity: int | None
    extras: tuple[str, ...]


def _distance_extra(name: str, semantics: dict[str, Any] | None, unit: str) -> str:
    """Independently expect JS's fixed 2.5 cm/in conversion and positive-sign policy."""
    positive_sign = (semantics or {}).get("positive_sign", "preserve")

    def convert(match: re.Match[str]) -> str:
        number = match.group(0)
        value = Decimal(number)
        if unit == "in":
            value /= Decimal("2.5")
        explicit_plus = positive_sign == "force" or (
            positive_sign != "omit" and number.startswith("+")
        )
        sign = "+" if explicit_plus and value >= 0 else ""
        number_text = format(value, "f")
        formatted = (
            number_text.rstrip("0").rstrip(".")
            if "." in number_text else number_text
        )
        return f'{sign}{formatted}{chr(34) if unit == "in" else " cm"}'

    return _DISTANCE_NUMBER.sub(convert, name)


def expected_items(
    items: dict[str, Any], distance_unit: str = "in",
) -> dict[str, list[ItemExpectation]]:
    """Project API shared/specific items onto rows visible in the chosen units."""
    result: dict[str, list[ItemExpectation]] = {}
    for bucket, label, catalog in BUCKETS:
        expected: list[ItemExpectation] = []
        for item in items.get(bucket) or []:
            route_id = item.get("slug") or item.get("id")
            href = f"/{catalog}/{quote(str(route_id), safe='')}" if catalog else None
            expected.append(
                ItemExpectation(
                    label=label,
                    name=str(item.get("name") or bucket.removesuffix("s").title()),
                    href=href,
                    quantity=item.get("quantity"),
                    extras=tuple(
                        _distance_extra(
                            str(extra.get("name") or "Extra"),
                            item.get("parameter_semantics"),
                            distance_unit,
                        )
                        if extra.get("is_distance")
                        else str(extra.get("name") or "Extra")
                        for extra in item.get("extras") or []
                    ),
                )
            )
        if expected:
            result[bucket] = expected
    return result


def _matches_row(row: dict[str, Any], item: ItemExpectation) -> bool:
    if not str(row["heading"]).strip().startswith(item.label):
        return False
    if item.href is not None:
        matching = [
            link["text"] for link in row["links"] if link["href"] == item.href
        ]
    else:
        # Classified non-Skills are deliberately unlinked text/spans.
        # Header help anchors may exist, but not Skill catalog links.
        matching = (
            [] if any(
                str(link["href"]).startswith("/skills/") for link in row["links"]
            ) else [row["text"]]
        )
    decorated = item.name
    if item.extras:
        decorated += f" ({', '.join(item.extras)})"
    if item.quantity is not None and int(item.quantity) != 1:
        decorated += f" ×{item.quantity}"
    for rendered in matching:
        label = str(rendered).strip()
        if item.href is not None:
            # Developer-only source annotations can follow the player label.
            if label == decorated or label.startswith(f"{decorated} ("):
                return True
        elif decorated.casefold() in label.casefold():
            return True
    return False


def assert_rendered_items(
    rows: list[dict[str, Any]], items: dict[str, Any], context: str,
    distance_unit: str = "in",
) -> int:
    """Require the right row header and rendered item for every visible API entry."""
    matches = 0
    projected = expected_items(items, distance_unit)
    for bucket, label, _ in BUCKETS:
        expected = projected.get(bucket, [])
        if not expected and any(
            str(row["heading"]).strip().startswith(label) for row in rows
        ):
            raise AssertionError(f"{context}: unexpected {bucket} row")
        for item in expected:
            if not any(_matches_row(row, item) for row in rows):
                raise AssertionError(
                    f"{context}: missing {bucket} item {item.name!r} "
                    f"({item.href or 'unlinked'}) in its labeled row"
                )
            matches += 1
    return matches


# Segment by actual profile/loadout summary rows, not document-wide text.
DOM_SNAPSHOT = """() => {
  const rows = (root) => [...root.querySelectorAll('tr')].map((tr) => ({
    heading: tr.cells[0]?.textContent?.trim() || '',
    text: tr.textContent?.trim() || '',
    links: [...tr.querySelectorAll('a[href]')].map((a) => ({
      href: a.getAttribute('href'), text: a.textContent?.trim() || '',
    })),
    summary: tr.classList.contains('profile-summary'),
  }));
  const segments = (root, selector) => {
    const result = [];
    for (const table of root.querySelectorAll(selector)) {
      let active = null;
      for (const row of rows(table)) {
        if (row.summary) {
          active = [];
          result.push(active);
        } else if (active) {
          active.push(row);
        }
      }
    }
    return result;
  };
  return {
    general: [...document.querySelectorAll('.general-profile')].map(rows),
    armies: [...document.querySelectorAll('.army-profile')].map((section) => ({
      name: section.querySelector('summary')?.textContent?.trim() || '',
      profiles: segments(section, '.profile-details-table'),
      loadouts: segments(section, '.loadout-table'),
      composite: segments(section, '.composite-option-table'),
      anchors: [...section.querySelectorAll('.loadout-anchor[id]')].map(
        (item) => item.id
      ),
    })),
    skillHrefs: [...document.querySelectorAll('a[href^="/skills/"]')].map(
      (a) => a.getAttribute('href')
    ),
    overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
  };
}"""


def _visible_distance_extras(unit: dict[str, Any]) -> int:
    """Count parameterized Extras only in player-visible API item buckets."""
    contexts = [
        entry["shared_items"] for entry in unit["general_profiles"]
        if entry.get("presentation_visible") is not False
    ]
    contexts.extend(
        entry.get("specific_items") or {}
        for army in unit["armies"] if army.get("presentation_visible")
        for kind in ("profiles", "loadouts")
        for entry in army[kind]
    )
    return sum(
        bool(extra.get("is_distance"))
        for context in contexts
        for bucket, _, _ in BUCKETS
        for item in context.get(bucket) or []
        for extra in item.get("extras") or []
    )


def assert_relationship_rows(
    rows: list[dict[str, Any]], source: dict[str, Any],
    anchor_scope: str, anchors: set[str], context: str,
) -> dict[str, int]:
    """Validate contextual relations in the correct row and Army, not page-wide."""
    result = {"includes": 0, "peripherals": 0, "controllerTargets": 0}
    expected_includes = source.get("includes") or []
    expected_peripherals = source.get("peripherals") or []
    expected_access = source.get("peripheral_access") or []
    for label, has_items in (
        ("Includes", bool(expected_includes)),
        ("Peripherals", bool(expected_peripherals)),
        ("Controller access", bool(expected_access)),
    ):
        matching = [row for row in rows if row["heading"].strip().startswith(label)]
        if bool(matching) != has_items:
            raise AssertionError(f"{context}: unexpected or missing {label} row")
        if has_items and len(matching) != 1:
            raise AssertionError(f"{context}: duplicate {label} row")
    if expected_includes:
        row = next(row for row in rows if row["heading"].strip().startswith("Includes"))
        for item in expected_includes:
            anchor = f"loadout-{anchor_scope}-{item['loadout_payload_id']}"
            href = f"#{anchor}"
            qty = item.get("quantity")
            suffix = f" ×{qty}" if qty is not None and int(qty) != 1 else ""
            title = f"{item.get('name') or 'Loadout'}{suffix}"
            if not any(
                link["href"] == href and link["text"] == title
                for link in row["links"]
            ):
                raise AssertionError(f"{context}: missing Include link {href} ({title})")
            if anchor not in anchors:
                raise AssertionError(f"{context}: Include target missing {anchor}")
            result["includes"] += 1
    if expected_peripherals:
        row = next(row for row in rows if row["heading"].strip().startswith("Peripherals"))
        for item in expected_peripherals:
            qty = item.get("quantity")
            suffix = f" ×{qty}" if qty is not None and int(qty) != 1 else ""
            label = item.get("type_label") or item.get("type_id")
            type_suffix = f" ({label})" if label else ""
            title = f"{item.get('name') or 'Peripheral'}{suffix}{type_suffix}"
            if title not in row["text"]:
                raise AssertionError(f"{context}: missing Peripheral {title}")
            if item.get("source_only") and not label and f"{title} (" in row["text"]:
                raise AssertionError(
                    f"{context}: source-only Peripheral gained an unreviewed type"
                )
            result["peripherals"] += 1
    if expected_access:
        row = next(
            row for row in rows if row["heading"].strip().startswith("Controller access")
        )
        for access in expected_access:
            label = access.get("type_label") or str(access.get("type_id"))
            if f"{label}:" not in row["text"]:
                raise AssertionError(f"{context}: missing Controller access type {label}")
            for target in access.get("targets") or []:
                route = quote(str(target.get("slug") or target["id"]), safe="")
                name = target.get("name") or f"Unit #{target['id']}"
                if not any(
                    link["href"] == f"/units/{route}" and link["text"] == name
                    for link in row["links"]
                ):
                    raise AssertionError(
                        f"{context}: missing Controller target link /units/{route}"
                    )
                result["controllerTargets"] += 1
    return result


def assert_unit_dom(
    unit: dict[str, Any], dom: dict[str, Any], slug: str,
    distance_unit: str = "in",
) -> dict[str, int]:
    """Compare visible General and Army-local API projections with scoped DOM rows."""
    general = [
        entry for entry in unit["general_profiles"]
        if entry.get("presentation_visible") is not False
    ]
    if len(dom["general"]) != len(general):
        raise AssertionError(
            f"{slug}: General Profile DOM count {len(dom['general'])} != {len(general)}"
        )
    counts = {
        "shared": 0, "profiles": 0, "loadouts": 0,
        "distanceExtras": _visible_distance_extras(unit),
        "includes": 0, "peripherals": 0, "controllerTargets": 0,
    }
    for index, entry in enumerate(general):
        counts["shared"] += assert_rendered_items(
            dom["general"][index], entry["shared_items"], f"{slug}/general#{index}",
            distance_unit,
        )
    rendered_armies = dom["armies"]
    consumed: set[int] = set()
    for army in unit["armies"]:
        if not army.get("presentation_visible"):
            continue
        expected_heading = army["name"] + "".join(
            badge["label"] for badge in army.get("availability_badges") or []
        )
        candidates = [
            (i, value) for i, value in enumerate(rendered_armies)
            if i not in consumed and value["name"] == expected_heading
        ]
        if len(candidates) != 1:
            raise AssertionError(
                f"{slug}: cannot uniquely match Army section {army['name']!r}, "
                f"found {len(candidates)}"
            )
        index, rendered = candidates[0]
        consumed.add(index)
        anchor_scope = "-".join([
            str(army["id"]), *(str(flag) for flag in army.get("availability_flags") or [])
        ])
        anchors = set(rendered.get("anchors") or [])
        for kind in ("profiles", "loadouts"):
            if len(rendered[kind]) != len(army[kind]):
                raise AssertionError(
                    f"{slug}/{army['name']}: {kind} DOM count "
                    f"{len(rendered[kind])} != API {len(army[kind])}"
                )
            for offset, context in enumerate(army[kind]):
                context_label = f"{slug}/{army['name']}/{kind}#{offset}"
                counts[kind] += assert_rendered_items(
                    rendered[kind][offset],
                    context.get("specific_items") or {},
                    context_label, distance_unit,
                )
                relations = assert_relationship_rows(
                    rendered[kind][offset], context, anchor_scope,
                    anchors, context_label,
                )
                for key, value in relations.items():
                    counts[key] += value
        options = army.get("composite_options") or []
        composite = rendered.get("composite") or []
        if len(composite) != len(options):
            raise AssertionError(
                f"{slug}/{army['name']}: composite option DOM count "
                f"{len(composite)} != API {len(options)}"
            )
        for offset, (rows, option) in enumerate(zip(composite, options, strict=True)):
            label = f"{slug}/{army['name']}/composite#{offset}"
            relations = assert_relationship_rows(
                rows, option, anchor_scope, anchors, label,
            )
            for key, value in relations.items():
                counts[key] += value
    if len(consumed) != len(rendered_armies):
        raise AssertionError(f"{slug}: unexpected Army sections in DOM")
    for general_or_army in [
        *(general_item["shared_items"] for general_item in general),
        *(
            context.get("specific_items") or {}
            for army in unit["armies"] if army.get("presentation_visible")
            for kind in ("profiles", "loadouts")
            for context in army[kind]
        ),
    ]:
        for source_marker in general_or_army.get("source_markers") or []:
            marker_slug = source_marker.get("slug") or source_marker.get("id")
            if f"/skills/{quote(str(marker_slug), safe='')}" in dom["skillHrefs"]:
                raise AssertionError(f"{slug}: source marker gained Skill link")
    if dom["overflow"]:
        raise AssertionError(f"{slug}: document horizontal overflow")
    return counts


def _settings_script(optional_filters: dict[str, bool], distance_unit: str) -> str:
    """Set isolated session preferences before the client imports preferences.js."""
    if set(optional_filters) - set(OPTIONAL_FLAGS):
        raise ValueError("Unknown optional Unit filter")
    if distance_unit not in ("in", "cm"):
        raise ValueError("Distance unit must be 'in' or 'cm'")
    settings = {
        f"infinity-db-{flag}": str(optional_filters.get(flag, True)).lower()
        for flag in OPTIONAL_FLAGS
    }
    settings["infinity-db-distance-unit"] = distance_unit
    return (
        "for (const [key, value] of Object.entries("
        + json.dumps(settings, sort_keys=True)
        + ")) window.sessionStorage.setItem(key, value);"
    )


def _unit_api_url(base: str, slug: str, optional_filters: dict[str, bool]) -> str:
    params = urlencode({
        flag: "1" if optional_filters.get(flag, True) else "0"
        for flag in OPTIONAL_FLAGS
    })
    return f"{base}/api/units/{quote(slug, safe='')}?{params}"


def _page_error(errors: list[str], error: Any) -> None:
    errors.append(str(error))


def verify(
    base_url: str, *, slugs: tuple[str, ...] = DEFAULT_SLUGS, headed: bool = False,
    channel: str | None = None, optional_filters: dict[str, bool] | None = None,
    distance_unit: str = "in", widths: tuple[int, ...] = WIDTHS,
    browser: Any | None = None,
    browser_wsgi_app: Any | None = None,
) -> dict[str, Any]:
    if not widths or any(width < 240 or width > 3840 for width in widths):
        raise ValueError("Viewport widths must be between 240 and 3840 px")
    try:
        playwright = importlib.import_module("playwright.sync_api")
    except ImportError as exc:
        raise RuntimeError("Install Playwright and Chromium for browser acceptance") from exc
    base = base_url.rstrip("/")
    filters = optional_filters or {}
    init_script = _settings_script(filters, distance_unit)
    results: list[dict[str, Any]] = []
    # Test callers may reuse one launched Chromium instance across scenarios.
    # The CLI continues to own and close its own browser as before.
    driver_context = playwright.sync_playwright() if browser is None else nullcontext(None)
    with driver_context as driver:
        if browser is None:
            assert driver is not None
            active_browser = driver.chromium.launch(
                headless=not headed,
                **({"channel": channel} if channel else {}),
            )
        else:
            active_browser = browser
        try:
            for width in widths:
                context = active_browser.new_context(viewport={"width": width, "height": 900})
                context.add_init_script(script=init_script)
                try:
                    for slug in slugs:
                        outcome: dict[str, Any] = {
                            "unit": slug, "width": width, "status": "failed",
                        }
                        page = context.new_page()
                        if browser_wsgi_app is not None:
                            route_browser_page(page, browser_wsgi_app, base)
                        errors: list[str] = []
                        failed_requests: list[str] = []
                        bad_responses: list[str] = []
                        page.on("pageerror", partial(_page_error, errors))
                        page.on(
                            "requestfailed",
                            lambda request, failures=failed_requests: failures.append(
                                f"{request.url}: {request.failure}"
                            ),
                        )
                        page.on(
                            "response",
                            lambda response, failures=bad_responses: failures.append(
                                f"{response.status} {response.url}"
                            ) if response.status >= 400 else None,
                        )
                        try:
                            response = page.goto(
                                f"{base}/units/{slug}", wait_until="domcontentloaded",
                                timeout=20000,
                            )
                            if response is None or response.status != 200:
                                raise AssertionError("Unit page HTTP response not 200")
                            try:
                                page.locator("#unit-content").wait_for(
                                    state="visible", timeout=60000,
                                )
                            except Exception as exc:
                                status = page.locator("#unit-status").text_content()
                                raise AssertionError(
                                    f"Unit content not visible: status={status!r}, "
                                    f"JavaScript errors={errors!r}, "
                                    f"failed requests={failed_requests!r}, "
                                    f"HTTP errors={bad_responses!r}"
                                ) from exc
                            api = context.request.get(
                                _unit_api_url(base, slug, filters), timeout=15000,
                            )
                            if api.status != 200:
                                raise AssertionError(f"Unit API HTTP {api.status}")
                            if any(
                                entry.get("presentation_visible") is not False
                                for entry in api.json()["general_profiles"]
                            ):
                                page.locator(".general-profile").first.wait_for(
                                    state="attached", timeout=10000,
                                )
                            page.locator(".army-profile").evaluate_all(
                                "(elements) => elements.forEach(el => el.open = true)"
                            )
                            unit = api.json()
                            outcome["visibleArmies"] = sum(
                                bool(army.get("presentation_visible"))
                                for army in unit["armies"]
                            )
                            outcome["visibleGeneralProfiles"] = sum(
                                general.get("presentation_visible") is not False
                                for general in unit["general_profiles"]
                            )
                            outcome["counts"] = assert_unit_dom(
                                unit, page.evaluate(DOM_SNAPSHOT), slug,
                                distance_unit,
                            )
                            if errors:
                                raise AssertionError(f"Browser JS errors: {errors!r}")
                            outcome["status"] = "passed"
                        except Exception as exc:
                            outcome["error"] = str(exc)
                        finally:
                            results.append(outcome)
                            page.close()
                finally:
                    context.close()
        finally:
            if browser is None:
                active_browser.close()
    return {
        "format": "InfinityDB Unit Skill presentation browser acceptance",
        "baseUrl": base,
        "optionalFilters": {flag: filters.get(flag, True) for flag in OPTIONAL_FLAGS},
        "distanceUnit": distance_unit,
        "passed": sum(r["status"] == "passed" for r in results),
        "total": len(slugs) * len(widths),
        "widths": list(widths),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--slug", action="append", dest="slugs")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--channel", help="Installed Chromium channel, e.g. chrome")
    parser.add_argument(
        "--exclude-optional", choices=OPTIONAL_FLAGS, action="append",
        help="Exclude an optional availability category; repeat to combine",
    )
    parser.add_argument("--distance-unit", choices=("in", "cm"), default="in")
    parser.add_argument(
        "--width", type=int, action="append",
        help="Viewport width in px; repeat for multiple widths",
    )
    args = parser.parse_args(argv)
    report = verify(
        args.base_url, slugs=tuple(args.slugs) if args.slugs else DEFAULT_SLUGS,
        headed=args.headed, channel=args.channel,
        optional_filters={flag: False for flag in args.exclude_optional or []},
        distance_unit=args.distance_unit,
        widths=tuple(args.width) if args.width else WIDTHS,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8", newline="\n",
        )
    print(f"Unit Skill browser acceptance: {report['passed']}/{report['total']} passed")
    for entry in report["results"]:
        if entry["status"] != "passed":
            print(f"  {entry['width']}px {entry['unit']}: {entry['error']}")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
