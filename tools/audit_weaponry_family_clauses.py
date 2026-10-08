#!/usr/bin/env python3
"""Validate reviewed N5 Weaponry family evidence and inventory linked concepts.

Source anchors establish printed facts, not that a curated entry implements them.
Requires the N5 v5.3 PDF only when explicitly invoked. Never alters data.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from tools.audit_weapon_chart_profiles import _identity, _sha256

DEFAULT_REVIEW = Path('config/validation/weaponry-family-clauses.json')
DEFAULT_ARMY = Path('data/generated/infinity.db')
DEFAULT_RULES = Path('data/generated/rules.db')


class WeaponryFamilyAuditError(ValueError):
    """Source pin, evidence anchor or reviewed identity failed validation."""


def _normalized_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip().casefold()


def _read_policy(path: Path, pdf_hash: str) -> dict[str, Any]:
    policy = json.loads(path.read_text(encoding='utf-8'))
    if policy.get('formatVersion') != 1 or policy.get('corePdfSha256') != pdf_hash:
        raise WeaponryFamilyAuditError('Weaponry family review does not match PDF SHA-256')
    families = policy.get('families')
    if not isinstance(families, list) or not families:
        raise WeaponryFamilyAuditError('Missing reviewed Weaponry families')
    family_ids: set[str] = set()
    clause_ids: set[str] = set()
    for family in families:
        if not isinstance(family, dict):
            raise WeaponryFamilyAuditError('Invalid family review entry')
        name, page = family.get('name'), family.get('page')
        if (not isinstance(name, str) or not name or name in family_ids
                or type(page) is not int or not 1 <= page <= 196):
            raise WeaponryFamilyAuditError('Invalid or duplicate Weaponry family')
        family_ids.add(name)
        examples, clauses = family.get('armyExamples'), family.get('clauses')
        if (not isinstance(examples, list) or not examples
                or not all(isinstance(x, str) and x for x in examples)
                or len(examples) != len(set(examples))
                or not isinstance(clauses, list) or not clauses):
            raise WeaponryFamilyAuditError(f'Invalid Weaponry family contents: {name}')
        for clause in clauses:
            if not isinstance(clause, dict):
                raise WeaponryFamilyAuditError('Invalid Weaponry clause')
            clause_id, anchor = clause.get('id'), clause.get('anchor')
            refs = clause.get('relatedCuratedIds')
            if (not isinstance(clause_id, str) or not clause_id
                    or clause_id in clause_ids or not isinstance(anchor, str)
                    or len(anchor.split()) < 3 or not isinstance(refs, list) or not refs
                    or not all(isinstance(ref, str) and ref for ref in refs)
                    or len(refs) != len(set(refs))):
                raise WeaponryFamilyAuditError(f'Invalid or duplicate clause: {clause_id}')
            clause_ids.add(clause_id)
    return policy


def compare_family_clauses(
    policy: dict[str, Any], pages: dict[int, str],
    rules: list[tuple[str, str, str, str]],
    army: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Check PDF clauses, curated concept identities and selected Army examples.

    Curated concept existence is NOT clause implementation or browser coverage.
    """
    ids = {(collection, record_id) for collection, record_id, _, _ in rules}
    names = {(collection, _identity(name)) for collection, _, _, name in rules}
    army_names: dict[str, list[str]] = {}
    for name, mode in army:
        army_names.setdefault(_identity(name), []).append(mode)
    result: list[dict[str, Any]] = []
    for family in policy['families']:
        page = family['page']
        content = pages.get(page)
        if content is None or _normalized_text(family['name']) not in _normalized_text(content):
            raise WeaponryFamilyAuditError(f'Missing printed family heading: {family["name"]}')
        family_rows: list[dict[str, Any]] = []
        for clause in family['clauses']:
            if _normalized_text(clause['anchor']) not in _normalized_text(content):
                raise WeaponryFamilyAuditError(
                    f'PDF clause anchor not found on p. {page}: {clause["id"]}'
                )
            missing = [ref for ref in clause['relatedCuratedIds']
                       if ('n5-core-v5.3', ref) not in ids]
            family_rows.append({
                'id': clause['id'], 'page': page,
                'sourceAnchor': clause['anchor'],
                'relatedCuratedIds': clause['relatedCuratedIds'],
                'missingCuratedConceptIds': missing,
                'semanticCoverage': 'not-adjudicated',
            })
        examples = [
            {'name': name, 'modes': sorted(army_names.get(_identity(name), [])),
             'found': _identity(name) in army_names}
            for name in family['armyExamples']
        ]
        result.append({
            'name': family['name'], 'page': page,
            'namedCuratedFamilyPresent': ('n5-core-v5.3', _identity(family['name'])) in names,
            'selectedArmyExamples': examples, 'clauses': family_rows,
            'caveat': 'Source and concept identities only; not clause or UI completeness',
        })
    return result


def audit_family_clauses(
    pdf: Path, army_db: Path = DEFAULT_ARMY, rules_db: Path = DEFAULT_RULES,
    review_path: Path = DEFAULT_REVIEW,
) -> dict[str, Any]:
    try:
        import fitz  # type: ignore[import-untyped]
    except ImportError as exc:
        raise WeaponryFamilyAuditError('PDF audit requires PyMuPDF') from exc
    pdf_hash = _sha256(pdf)
    policy = _read_policy(review_path, pdf_hash)
    with fitz.open(pdf) as doc:
        pages = {f['page']: doc[f['page'] - 1].get_text() for f in policy['families']}
    with sqlite3.connect(f'file:{rules_db.resolve().as_posix()}?mode=ro', uri=True) as db:
        rules = db.execute('SELECT collection_id, id, kind, name FROM records').fetchall()
    with sqlite3.connect(f'file:{army_db.resolve().as_posix()}?mode=ro', uri=True) as db:
        army = db.execute("SELECT name, COALESCE(mode, '') FROM metadata_weapons").fetchall()
    families = compare_family_clauses(policy, pages, rules, army)
    return {
        'format': 'InfinityDB N5 Weaponry family source-to-reference review',
        'formatVersion': 1, 'status': 'partial-family-evidence-not-rule-completeness',
        'pdfSha256': pdf_hash, 'armyDbSha256': _sha256(army_db),
        'rulesDbSha256': _sha256(rules_db), 'reviewSha256': _sha256(review_path),
        'families': families, 'familyCount': len(families),
        'reviewedClauseCount': sum(len(f['clauses']) for f in families),
        'missingConceptCount': sum(len(c['missingCuratedConceptIds'])
                                   for f in families for c in f['clauses']),
        'limitations': [
            'Reviewed source anchors cover selected Mines and Perimeter Weapons clauses only.',
            'Family variants, exceptions and additional sections require separate review.',
            'Existing concept records do not prove the specific source clause is encoded.',
            'A missing named family record does not imply the rules are absent elsewhere.',
            'Army identities are explicitly selected examples, not an exhaustive family census.',
            'Relationships and browser behavior have not been adjudicated.',
        ],
    }


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        '# N5 Weaponry family clause evidence', '',
        '**Partial source-to-reference inventory, not a completeness verdict.**', '',
        f"- Core PDF SHA-256: `{report['pdfSha256']}`",
        f"- Army database SHA-256: `{report['armyDbSha256']}`",
        f"- Rules database SHA-256: `{report['rulesDbSha256']}`",
        f"- Review policy SHA-256: `{report['reviewSha256']}`",
        f"- Source clauses checked: **{report['reviewedClauseCount']}**.",
        f"- Unresolved curated concept identities: **{report['missingConceptCount']}**.",
    ]
    for family in report['families']:
        lines.extend([
            '', f"## {family['name']} (p. {family['page']})", '',
            f"- Named curated family record: **{family['namedCuratedFamilyPresent']}**.",
            '- Selected Army names: ' + ', '.join(
                f"{row['name']} ({'found' if row['found'] else 'unmatched'})"
                for row in family['selectedArmyExamples']
            ) + '.',
        ])
        for clause in family['clauses']:
            lines.append(
                f"- `{clause['id']}`: source anchor `{clause['sourceAnchor']}`; "
                f"related concepts {clause['relatedCuratedIds']}; "
                f"absent concepts {clause['missingCuratedConceptIds']}; "
                '**semantic implementation unverified**.'
            )
    lines.extend(['', '## Limits', ''])
    lines.extend(f'- {limit}' for limit in report['limitations'])
    return '\n'.join(lines) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core-pdf', type=Path, required=True)
    parser.add_argument('--army-db', type=Path, default=DEFAULT_ARMY)
    parser.add_argument('--rules-db', type=Path, default=DEFAULT_RULES)
    parser.add_argument('--review', type=Path, default=DEFAULT_REVIEW)
    parser.add_argument('--json-output', type=Path)
    parser.add_argument('--markdown-output', type=Path)
    args = parser.parse_args()
    try:
        report = audit_family_clauses(args.core_pdf, args.army_db, args.rules_db, args.review)
    except (OSError, sqlite3.Error, ValueError) as exc:
        parser.error(str(exc))
    output = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + '\n'
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(output, encoding='utf-8', newline='\n')
    else:
        print(output, end='')
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown_report(report), encoding='utf-8', newline='\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
