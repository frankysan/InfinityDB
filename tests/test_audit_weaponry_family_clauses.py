from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools.audit_weaponry_family_clauses import (
    WeaponryFamilyAuditError,
    _read_policy,
    compare_family_clauses,
    markdown_report,
)


def _fixture() -> tuple[dict[str, Any], dict[int, str]]:
    family = {
        'name': 'Mines', 'page': 72, 'armyExamples': ['AP Mine', 'Cybermine'],
        'clauses': [{
            'id': 'mine-camo', 'anchor': 'place a Camouflaged Marker',
            'relatedCuratedIds': ['skill:place-deployable'],
        }],
    }
    return {'formatVersion': 1, 'families': [family]}, {
        72: 'MINES\nThe Trooper must place a Camouflaged\nMarker instead of a Token.'
    }


def test_compares_source_anchor_and_curated_concepts_without_claiming_coverage() -> None:
    policy, pages = _fixture()
    result = compare_family_clauses(
        policy, pages,
        [('n5-core-v5.3', 'skill:place-deployable', 'skill', 'Place Deployable')],
        [('AP Mine', ''), ('Cybermine', '')],
    )
    assert len(result) == 1
    assert not result[0]['namedCuratedFamilyPresent']
    assert all(row['found'] for row in result[0]['selectedArmyExamples'])
    clause = result[0]['clauses'][0]
    assert clause['missingCuratedConceptIds'] == []
    assert clause['semanticCoverage'] == 'not-adjudicated'


def test_missing_curated_concept_and_army_example_are_reported() -> None:
    policy, pages = _fixture()
    result = compare_family_clauses(policy, pages, [], [('AP Mine', '')])
    assert result[0]['clauses'][0]['missingCuratedConceptIds'] == ['skill:place-deployable']
    assert not result[0]['selectedArmyExamples'][1]['found']


def test_wrong_pdf_evidence_fails_closed() -> None:
    policy, pages = _fixture()
    with pytest.raises(WeaponryFamilyAuditError, match='anchor'):
        compare_family_clauses(policy, {72: 'MINES but without the reviewed clause'}, [], [])
    with pytest.raises(WeaponryFamilyAuditError, match='heading'):
        compare_family_clauses(policy, {72: 'place a Camouflaged Marker'}, [], [])


def test_hash_pin_and_duplicate_clause_ids_are_required(tmp_path: Path) -> None:
    policy, _ = _fixture()
    policy['corePdfSha256'] = 'a' * 64
    path = tmp_path / 'review.json'
    path.write_text(json.dumps(policy), encoding='utf-8', newline='\n')
    assert len(_read_policy(path, 'a' * 64)['families']) == 1
    with pytest.raises(WeaponryFamilyAuditError, match='SHA-256'):
        _read_policy(path, 'b' * 64)
    policy['families'][0]['clauses'].append(policy['families'][0]['clauses'][0])
    path.write_text(json.dumps(policy), encoding='utf-8', newline='\n')
    with pytest.raises(WeaponryFamilyAuditError, match='duplicate clause'):
        _read_policy(path, 'a' * 64)


def test_markdown_report_does_not_assert_semantic_completeness() -> None:
    policy, pages = _fixture()
    families = compare_family_clauses(policy, pages, [], [('AP Mine', '')])
    text = markdown_report({
        'pdfSha256': 'a', 'armyDbSha256': 'b', 'rulesDbSha256': 'c',
        'reviewSha256': 'd', 'reviewedClauseCount': 1, 'missingConceptCount': 1,
        'families': families, 'limitations': ['Not verified in the browser'],
    })
    assert 'not a completeness verdict' in text
    assert 'semantic implementation unverified' in text
    assert 'Not verified in the browser' in text


def test_checked_in_policy_has_21_distinct_reviewed_source_clauses() -> None:
    path = Path(__file__).resolve().parents[1] / (
        'config/validation/weaponry-family-clauses.json'
    )
    raw = json.loads(path.read_text(encoding='utf-8'))
    policy = _read_policy(path, raw['corePdfSha256'])
    assert [family['name'] for family in policy['families']] == [
        'Perimeter Weapons', 'Mines',
    ]
    assert [len(family['clauses']) for family in policy['families']] == [7, 14]
    assert len({clause['id'] for f in policy['families'] for clause in f['clauses']}) == 21
