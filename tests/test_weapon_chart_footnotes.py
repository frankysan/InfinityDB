"""N5.3 Weapon Chart markers: reviewed targets, combined labels and unresolved notation."""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.weapon_profile_publication import current_pdf_source
from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def app() -> Callable:
    return create_app(
        ROOT / "data/generated/army.db",
        rules_database_path=ROOT / "data/generated/rules_n5.db",
    )


def _request(app: Callable, path: str) -> tuple[str, dict[str, str], bytes]:
    environ: dict = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
    observed: dict = {}

    def respond(status: str, headers: list, _exc: object = None) -> None:
        observed["status"] = status
        observed["headers"] = dict(headers)

    body = b"".join(app(environ, respond))
    return observed["status"], observed["headers"], body


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
def test_weapon_footnotes_follow_exact_reviewed_source_context() -> None:
    script = """
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source = readFileSync('./src/infinity_db/web/static/weapon-footnotes.js');
const {
  isWeaponFootnote, weaponFootnoteMarkers, withoutWeaponFootnotes, weaponFootnotesForProfile,
} = await import('data:text/javascript;base64,' + source.toString('base64'));

assert.equal(isWeaponFootnote('[*]'), true);
assert.equal(isWeaponFootnote('Non-lethal [**]'), false);
assert.deepEqual(weaponFootnoteMarkers('NON-LETHAL [**] [***]'), ['[**]', '[***]']);
assert.deepEqual(weaponFootnoteMarkers('Other text'), []);
assert.equal(withoutWeaponFootnotes({label: '[*]'}), null);
assert.deepEqual(withoutWeaponFootnotes({
  label: 'NON-LETHAL [**]', name: 'NON-LETHAL [**]', slug: null,
}), {
  label: 'NON-LETHAL [**]', name: 'NON-LETHAL', slug: null, source_alias: true,
});

const mines = {id: 'weapon:mines', kind: 'weapon', name: 'Mines'};
const para = {id: 'weapon:para-mine', kind: 'weapon', name: 'PARA Mine'};
const paraRows = weaponFootnotesForProfile(
  {mode: null, traits: ['Non-lethal', '[**]'], ammunition_parts: [
    {text: 'PARA', public_reference: {catalog: 'ammunition', id: 'para'}},
  ]}, [mines, para], 'para-mine',
);
assert.deepEqual(paraRows.map(row => row.marker), ['[**]', '[*]']);
assert.equal(paraRows[0].source, 'Army');
assert.equal(paraRows[0].target, null);
assert.equal(paraRows[0].mismatch, true);
assert.equal(paraRows[1].source, 'N5.3 chart p. 181');
assert.equal(paraRows[1].issue, 'SRC-013');
assert.deepEqual(paraRows[1].target, {
  href: '#rule-weapon-mines', label: 'Mines',
});

const sepsitor = weaponFootnotesForProfile(
  {mode: null, traits: ['State: Sepsitorized']},
  [{id: 'weapon:sepsitor-plus', kind: 'weapon', name: 'Sepsitor Plus'}],
  'sepsitor-plus',
);
assert.equal(sepsitor.length, 1);
assert.equal(sepsitor[0].source, 'N5.3 chart p. 187');
assert.equal(sepsitor[0].issue, 'SRC-014');
assert.equal(sepsitor[0].mismatch, true);
assert.deepEqual(sepsitor[0].target, {
  href: '#rule-weapon-sepsitor-plus', label: 'Sepsitor Plus',
});

const emMine = weaponFootnotesForProfile(
  {mode: null, traits: ['[**]'], ammunition_parts: [
    {text: 'E/M', public_reference: {catalog: 'ammunition', id: 'em'}},
  ]}, [mines], 'e-m-mine',
);
assert.equal(emMine.length, 1);
assert.equal(emMine[0].source, 'Army and N5.3 chart p. 181');
assert.deepEqual(emMine[0].target, {label: 'E/M', href: '/ammunition/em'});
assert.equal(emMine[0].unresolved, false);

for (const slug of ['ap-mine', 'monofilament-mine', 'shock-mine', 'viral-mine']) {
  const rows = weaponFootnotesForProfile({mode: null, traits: ['[*]']}, [mines], slug);
  assert.equal(rows.length, 1, slug);
  assert.deepEqual(rows[0].target, {label: 'Mines', href: '#rule-weapon-mines'});
  assert.equal(rows[0].source, 'Army and N5.3 chart p. 181');
}
const cybermine = weaponFootnotesForProfile(
  {mode: null, traits: ['[*]']},
  [mines, {id: 'weapon:cybermine', kind: 'weapon', name: 'Cybermine'}],
  'cybermine',
);
assert.deepEqual(cybermine[0].target, {
  label: 'Cybermine', href: '#rule-weapon-cybermine',
});

// A uniquely related rule is not proof of the printed marker's target.
const unknown = weaponFootnotesForProfile(
  {traits: ['[*]', 'NON-LETHAL [**]', '[***]', '[****]']},
  [{id: 'weapon:unreviewed', kind: 'weapon', name: 'Unreviewed'}],
  'unreviewed',
);
assert.deepEqual(unknown.map(row => row.marker), ['[*]', '[**]', '[***]']);
assert(unknown.every(row => row.unresolved && row.target === null));
assert.deepEqual(weaponFootnotesForProfile(
  {mode: 'BS Mode', traits: ['[**]']}, [mines], 'para-mine',
).map(row => row.source), ['Army']);
assert.equal(weaponFootnotesForProfile(
  {mode: null, traits: ['[*]']}, [], 'ap-mine',
)[0].target, null);
"""
    result = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        cwd=ROOT, capture_output=True, text=True, check=False, timeout=20,
    )
    assert result.returncode == 0, result.stderr


def test_reviewed_chart_markers_match_pinned_evidence() -> None:
    mines = json.loads(
        (ROOT / "config/validation/mine-variant-effects.json").read_text(encoding="utf-8")
    )
    wiki = json.loads(
        (ROOT / "config/validation/weapon-trait-wiki-review.json").read_text(encoding="utf-8")
    )
    assert mines["sources"]["corePdfSha256"] == wiki["corePdfSha256"]
    selected = current_pdf_source(
        ROOT / "data/generated/rules_n5.db", "n5-core-v5.3", "n5-core-v5.3-pdf",
    )
    assert selected["sha256"] == mines["sources"]["corePdfSha256"]
    assert mines["sources"]["weaponChartPrintedPage"] == 181
    assert {row["slug"]: row["chartFootnote"] for row in mines["variants"]} == {
        "ap-mine": "[*]",
        "e-m-mine": "[**]",
        "monofilament-mine": "[*]",
        "para-mine": "[*]",
        "shock-mine": "[*]",
        "viral-mine": "[*]",
        "cybermine": "[*]",
    }
    sepsitor = next(
        item for item in wiki["candidates"] if item["name"] == "Sepsitor Plus"
    )
    assert sepsitor["mode"] == ""
    assert {176, 187} <= set(sepsitor["semanticReview"]["pdfPages"])
    assert "[*]" in sepsitor["semanticReview"]["finding"]


@pytest.mark.parametrize(("slug", "marker", "rule_id"), [
    ("ap-mine", "[*]", "weapon:mines"),
    ("e-m-mine", "[**]", "weapon:mines"),
    ("monofilament-mine", "[*]", "weapon:mines"),
    ("para-mine", "[**]", "weapon:mines"),
    ("shock-mine", "[*]", "weapon:mines"),
    ("viral-mine", "[*]", "weapon:mines"),
    ("cybermine", "[*]", "weapon:cybermine"),
    ("sepsitor-plus", None, "weapon:sepsitor-plus"),
])
def test_reviewed_profiles_remain_single_mode_and_source_native(
    app: Callable, slug: str, marker: str | None, rule_id: str,
) -> None:
    status, _headers, body = _request(app, f"/api/weapons/{slug}")
    assert status == "200 OK"
    payload = json.loads(body)
    assert payload["slug"] == slug
    assert len(payload["profiles"]) == 1
    profile = payload["profiles"][0]
    assert profile.get("mode") in (None, "")
    if marker:
        assert marker in profile["traits"]
    else:
        assert "[*]" not in profile["traits"]
    assert rule_id in {record["id"] for record in payload["rules"]}


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
def test_reviewed_chart_links_resolve_against_published_api(app: Callable) -> None:
    payloads = {}
    for slug in (
        "ap-mine", "e-m-mine", "monofilament-mine", "para-mine",
        "shock-mine", "viral-mine", "cybermine", "sepsitor-plus",
    ):
        status, _headers, body = _request(app, f"/api/weapons/{slug}")
        assert status == "200 OK"
        payloads[slug] = json.loads(body)

    script = """
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source = readFileSync('./src/infinity_db/web/static/weapon-footnotes.js');
const {weaponFootnotesForProfile} = await import(
  'data:text/javascript;base64,' + source.toString('base64')
);
const payloads = JSON.parse(readFileSync(0, 'utf8'));
for (const [slug, item] of Object.entries(payloads)) {
  const rows = weaponFootnotesForProfile(item.profiles[0], item.rules, item.slug);
  const reviewed = rows.find(row => row.source.includes('N5.3 chart'));
  assert(reviewed, slug);
  assert(reviewed.target, slug);
  if (reviewed.target.href.startsWith('#rule-')) {
    assert(item.rules.some(rule =>
      reviewed.target.href === '#rule-' + rule.id.replaceAll(':', '-')), slug);
  } else {
    assert(reviewed.target.href.startsWith('/ammunition/'), slug);
  }
  if (slug === 'para-mine') {
    assert.equal(rows.length, 2);
    assert.equal(rows[0].target, null);
  }
  if (slug === 'sepsitor-plus') assert.equal(rows.length, 1);
}
"""
    result = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        input=json.dumps(payloads), cwd=ROOT, capture_output=True, text=True,
        check=False, timeout=25,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(("slug", "ammunition_id"), [
    ("blitzen", "em"),
    ("smoke-grenades", "smoke"),
    ("e-m-grenades", "em"),
    ("eclipse-grenades", "eclipse"),
])
def test_more_reviewed_chart_footnotes_keep_exact_ammunition_owner(
    app: Callable, slug: str, ammunition_id: str,
) -> None:
    reviews = json.loads(
        (ROOT / "data/curated/weapon-shared-effect-reviews.json").read_text(
            encoding="utf-8"
        )
    )
    review = next(row for row in reviews["reviews"] if row["slug"] == slug)
    assert review["chartPage"] == 178
    assert "[**]" in review["reason"]
    status, _headers, body = _request(app, f"/api/weapons/{slug}")
    assert status == "200 OK"
    payload = json.loads(body)
    assert len(payload["profiles"]) == 1
    profile = payload["profiles"][0]
    assert not profile.get("mode")
    published_ammunition = {
        part.get("public_reference", {}).get("id")
        for part in profile.get("ammunition_parts", [])
    }
    published_ammunition.update(
        reference.get("public_reference", {}).get("id")
        for reference in profile.get("rule_references", [])
        if reference.get("kind") == "ammunition"
    )
    assert ammunition_id in published_ammunition


def test_chest_mine_cc_footnote_is_mode_scoped_to_reviewed_chart_cell(
    app: Callable,
) -> None:
    review = json.loads(
        (ROOT / "config/validation/weapon-trait-source-review.json").read_text(
            encoding="utf-8"
        )
    )
    assert "[*]" in review["verifiedSourceCells"]["181:CHEST MINES (CC Mode)"]
    status, _headers, body = _request(app, "/api/weapons/chest-mine")
    assert status == "200 OK"
    payload = json.loads(body)
    assert {profile["mode"] for profile in payload["profiles"]} == {
        "BS Mode", "CC Mode",
    }
    assert "weapon:chest-mine" in {rule["id"] for rule in payload["rules"]}
    assert "weapon:mines" not in {rule["id"] for rule in payload["rules"]}


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
def test_extra_reviewed_targets_are_routable_in_actual_api(app: Callable) -> None:
    payloads = {}
    for slug in (
        "blitzen", "smoke-grenades", "e-m-grenades", "eclipse-grenades", "chest-mine",
    ):
        status, _headers, body = _request(app, f"/api/weapons/{slug}")
        assert status == "200 OK"
        payloads[slug] = json.loads(body)
    script = """
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source = readFileSync('./src/infinity_db/web/static/weapon-footnotes.js');
const {weaponFootnotesForProfile} = await import(
  'data:text/javascript;base64,' + source.toString('base64')
);
const payloads = JSON.parse(readFileSync(0, 'utf8'));
const targets = {
  blitzen: '/ammunition/em',
  'smoke-grenades': '/ammunition/smoke',
  'e-m-grenades': '/ammunition/em',
  'eclipse-grenades': '/ammunition/eclipse',
  'chest-mine': '#rule-weapon-chest-mine',
};
for (const [slug, item] of Object.entries(payloads)) {
  const matched = [];
  for (const profile of item.profiles) {
    const rows = weaponFootnotesForProfile(profile, item.rules, slug);
    matched.push(...rows.filter(row => row.source.includes('N5.3 chart')));
    if (slug === 'chest-mine' && profile.mode === 'BS Mode') {
      assert.equal(matched.length, 0);
    }
  }
  assert.equal(matched.length, 1, slug);
  assert.equal(matched[0].marker, slug === 'chest-mine' ? '[*]' : '[**]');
  assert.equal(matched[0].target?.href, targets[slug], slug);
}
"""
    result = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        input=json.dumps(payloads), cwd=ROOT, capture_output=True, text=True,
        check=False, timeout=25,
    )
    assert result.returncode == 0, result.stderr



def test_weapon_profile_page_separates_source_markers_from_traits() -> None:
    page = (ROOT / "src/infinity_db/web/static/catalog-detail.js").read_text(
        encoding="utf-8"
    )
    assert "withoutWeaponFootnotes(reference)" in page
    assert "weaponFootnotesForProfile(profile, weaponRules, weaponSlug, catalog)" in page
    assert "footnote.source" in page
    assert 'node.setAttribute("aria-label",' in page
    assert 'value.append(" (exact target not verified)")' in page
    assert "source discrepancy" in page


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
def test_catalog_detail_script_is_valid_es_module() -> None:
    source = (ROOT / "src/infinity_db/web/static/catalog-detail.js").read_text(
        encoding="utf-8"
    )
    result = subprocess.run(
        ["node", "--input-type=module", "--check"],
        input=source, cwd=ROOT, capture_output=True, text=True, timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(("path", "expected"), [
    ("/static/weapon-footnotes.js", b"weaponFootnotesForProfile"),
    ("/static/catalog-detail.js", b'from "./weapon-footnotes.js"'),
])
def test_weapon_footnote_module_is_served_from_registered_assets(
    app: Callable, path: str, expected: bytes,
) -> None:
    status, headers, body = _request(app, path)
    assert status == "200 OK"
    assert headers["Content-Type"].startswith("text/javascript")
    assert expected in body


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
def test_deactivator_footnote_is_equipment_scoped_and_links_reviewed_rule(
    app: Callable,
) -> None:
    review = json.loads(
        (ROOT / "config/validation/weapon-trait-source-review.json").read_text(
            encoding="utf-8"
        )
    )
    assert review["verifiedSourceCells"]["186:DEACTIVATOR"] == [
        "BS WEAPON (WIP)", "[***]",
    ]
    status, _headers, body = _request(app, "/api/equipment/deactivator")
    assert status == "200 OK"
    item = json.loads(body)
    assert item["slug"] == "deactivator"
    assert len(item["profiles"]) == 1
    profile = item["profiles"][0]
    assert not profile.get("mode")
    assert "[***]" in profile["traits"]
    assert any(
        rule["id"] == "equipment:deactivator" and rule["kind"] == "equipment"
        for rule in item["rules"]
    )

    script = """
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source = readFileSync('./src/infinity_db/web/static/weapon-footnotes.js');
const {weaponFootnotesForProfile} = await import(
  'data:text/javascript;base64,' + source.toString('base64')
);
const item = JSON.parse(readFileSync(0, 'utf8'));
const profile = item.profiles[0];
const rows = weaponFootnotesForProfile(
  profile, item.rules, item.slug, 'equipment',
);
assert.equal(rows.length, 1);
assert.equal(rows[0].source, 'Army and N5.3 chart p. 186');
assert.equal(rows[0].marker, '[***]');
assert.equal(rows[0].category, 'Skills and Equipment');
assert.equal(rows[0].unresolved, false);
assert.deepEqual(rows[0].target, {
  label: 'Deactivator', href: '#rule-equipment-deactivator',
});
// Never resolve the Equipment rule from the Weapon catalog or another item.
assert.equal(weaponFootnotesForProfile(profile, item.rules, item.slug)[0].target, null);
assert.equal(weaponFootnotesForProfile(profile, item.rules, 'other', 'equipment')[0].target,
  null);
assert.equal(weaponFootnotesForProfile(profile, [], item.slug, 'equipment')[0].target, null);
"""
    result = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        input=json.dumps(item), cwd=ROOT, capture_output=True, text=True,
        check=False, timeout=25,
    )
    assert result.returncode == 0, result.stderr
