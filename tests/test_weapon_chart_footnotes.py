"""N5.3 source-marker resolution: exact published targets or visible ambiguity."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from wsgiref.util import setup_testing_defaults

import pytest

from infinity_db.web import create_app

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
def test_weapon_footnote_targets_follow_current_source_context() -> None:
    script = """
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const source = readFileSync('./src/infinity_db/web/static/weapon-footnotes.js');
const {
  isWeaponFootnote, weaponFootnotesForProfile,
} = await import('data:text/javascript;base64,' + source.toString('base64'));

assert.equal(isWeaponFootnote('[*]'), true);
assert.equal(isWeaponFootnote('[**]'), true);
assert.equal(isWeaponFootnote('[***]'), true);
assert.equal(isWeaponFootnote('Non-lethal'), false);
const references = [
  { id: 'ammunition:para', name: 'PARA', kind: 'ammunition',
    public_reference: { catalog: 'ammunition', id: 'para' } },
  { id: 'skill:deactivate', name: 'Deactivate', kind: 'skill',
    public_reference: { catalog: 'skills', id: 'deactivate' } },
];
const profile = {
  traits: ['Non-lethal', '[*]', '[**]', '[***]', '[**]'],
  ammunition_parts: [
    { text: 'PARA', public_reference: { catalog: 'ammunition', id: 'para' } },
  ],
  rule_references: references,
  rules: [{ id: 'weapon:para-mine', kind: 'weapon', name: 'PARA Mine' }],
};
const rows = weaponFootnotesForProfile(profile, []);
assert.deepEqual(rows.map(row => row.marker), ['[*]', '[**]', '[***]']);
assert.equal(rows[0].category, 'Weaponry');
assert.deepEqual(rows[0].target, {
  label: 'PARA Mine', href: '#rule-weapon-para-mine',
});
assert.deepEqual(rows[1].target, { label: 'PARA', href: '/ammunition/para' });
assert.deepEqual(rows[2].target, { label: 'Deactivate', href: '/skills/deactivate' });
assert(rows.every(row => !row.unresolved));

const ambiguous = weaponFootnotesForProfile(
  { traits: ['[*]', '[**]', '[***]'], ammunition_parts: [
    { text: 'AP', public_reference: { catalog: 'ammunition', id: 'ap' } },
    { text: 'DA', public_reference: { catalog: 'ammunition', id: 'da' } },
  ] },
  [
    { id: 'weapon:mines', name: 'Mines', kind: 'weapon' },
    { id: 'weapon:para-mine', name: 'PARA Mine', kind: 'weapon' },
  ],
);
assert.equal(ambiguous.length, 3);
assert(ambiguous.every(row => row.target === null && row.unresolved));
// Neither an unknown footnote nor a recognized type with no exact published
// source becomes a guessed rule link.
assert.deepEqual(weaponFootnotesForProfile({ traits: ['[****]', 'Regular'] }), []);
const item = { traits: ['[*]'] };
assert.deepEqual(weaponFootnotesForProfile(item, [
  { id: 'weapon:pitcher', kind: 'weapon', name: 'Pitcher' },
])[0].target, { href: '#rule-weapon-pitcher', label: 'Pitcher' });
"""
    result = subprocess.run(
        ["node", "--input-type=module",
         "--eval", script],
        cwd=ROOT, capture_output=True, text=True, check=False, timeout=20,
    )
    assert result.returncode == 0, result.stderr


def test_weapon_profile_page_uses_source_markers_as_footnotes() -> None:
    page = (ROOT / "src/infinity_db/web/static/catalog-detail.js").read_text(
        encoding="utf-8",
    )
    assert 'import { isWeaponFootnote, weaponFootnotesForProfile }' in page
    assert 'if (isWeaponFootnote(reference.label)) continue;' in page
    assert 'const footnotes = weaponFootnoteRow(profile, weaponRules);' in page
    assert 'node.setAttribute("aria-label",' in page
    assert 'value.append(" (exact target not verified)")' in page


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
def test_catalog_detail_script_is_valid_es_module() -> None:
    source = (ROOT / "src/infinity_db/web/static/catalog-detail.js").read_text(
        encoding="utf-8",
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
    path: str, expected: bytes,
) -> None:
    app = create_app(
        ROOT / "data/generated/army.db",
        rules_database_path=ROOT / "data/generated/rules_n5.db",
    )
    environ: dict = {}
    setup_testing_defaults(environ)
    environ.update(PATH_INFO=path, REQUEST_METHOD="GET")
    observed: dict = {}

    def respond(status: str, headers: list, _exc: object = None) -> None:
        observed["status"] = status
        observed["headers"] = dict(headers)

    body = b"".join(app(environ, respond))
    assert observed["status"] == "200 OK"
    assert observed["headers"]["Content-Type"].startswith("text/javascript")
    assert expected in body
