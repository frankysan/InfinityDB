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
            'semanticReview': {'status': 'component-only',
                               'reason': 'Only the generic placement Skill exists.'},
        }],
    }
    return {'formatVersion': 2, 'families': [family]}, {
        72: 'MINES\nThe Trooper must place a Camouflaged\nMarker instead of a Token.'
    }


def test_compares_source_anchor_and_curated_concepts_without_claiming_coverage() -> None:
    policy, pages = _fixture()
    result = compare_family_clauses(
        policy, pages,
        [('n5-core-v5.3', 'skill:place-deployable', 'skill', 'Place Deployable', 'Place item')],
        [('AP Mine', ''), ('Cybermine', '')],
    )
    assert len(result) == 1
    assert not result[0]['namedCuratedFamilyPresent']
    assert all(row['found'] for row in result[0]['selectedArmyExamples'])
    clause = result[0]['clauses'][0]
    assert clause['missingCuratedConceptIds'] == []
    assert clause['semanticCoverage'] == 'component-only'


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
        'semanticCoverageCounts': {'represented': 0, 'component-only': 1,
                                   'not-represented': 0},
    })
    assert 'not a completeness verdict' in text
    assert 'reviewed summary coverage **component-only**' in text
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


def test_represented_clause_requires_current_curated_summary_anchor() -> None:
    policy, pages = _fixture()
    review = policy['families'][0]['clauses'][0]['semanticReview']
    review.update({'status': 'represented', 'curatedId': 'skill:place-deployable',
                   'summaryAnchor': 'place Camouflaged Marker'})
    rules = [('n5-core-v5.3', 'skill:place-deployable', 'skill',
              'Place Deployable', 'Place Camouflaged Marker using this Skill')]
    result = compare_family_clauses(policy, pages, rules, [('AP Mine', '')])
    assert result[0]['clauses'][0]['semanticCoverage'] == 'represented'
    with pytest.raises(WeaponryFamilyAuditError, match='Curated summary evidence changed'):
        compare_family_clauses(policy, pages, [(*rules[0][:4], 'Place any item')], [])


def test_malformed_semantic_review_fails_closed(tmp_path: Path) -> None:
    policy, _ = _fixture()
    policy['corePdfSha256'] = 'a' * 64
    path = tmp_path / 'review.json'
    clause = policy['families'][0]['clauses'][0]
    clause['semanticReview'] = {'status': 'represented', 'reason': 'Missing evidence'}
    path.write_text(json.dumps(policy), encoding='utf-8', newline='\n')
    with pytest.raises(WeaponryFamilyAuditError, match='Invalid summary evidence'):
        _read_policy(path, 'a' * 64)


def test_checked_in_semantic_review_separates_full_and_partial_coverage() -> None:
    raw = json.loads(Path('config/validation/weaponry-family-clauses.json').read_text(
        encoding='utf-8'))
    statuses = [clause['semanticReview']['status']
                for family in raw['families'] for clause in family['clauses']]
    assert {status: statuses.count(status) for status in set(statuses)} == {
        'represented': 21,
    }


def test_curated_boost_rules_are_published_with_source_provenance() -> None:
    import sqlite3

    root = Path(__file__).resolve().parents[1]
    curated = json.loads((root / 'data/curated/rules/n5-core-v5.3.json').read_text(
        encoding='utf-8'))
    boost = next(r for r in curated['records'] if r['id'] == 'trait:boost')
    summary = boost['summary']
    for phrase in ('must trigger', 'Silhouette contact', '[[skill:dodge]]',
                   'obstacle or too-small gap', '[[state:camouflaged|CAMO]]',
                   '[[state:impersonation-1|IMP-1]]', 'cannot activate other'):
        assert phrase in summary
    assert {'sourceId': 'n5-core-v5.3-pdf', 'page': 69,
            'section': 'Perimeter Weapons and the Boost Trait'} in boost['citations']
    with sqlite3.connect(root / 'data/generated/rules.db') as db:
        assert db.execute(
            "SELECT summary FROM records WHERE id = 'trait:boost'"
        ).fetchone()[0] == summary
        assert db.execute(
            "SELECT COUNT(*) FROM record_citations "
            "WHERE record_id = 'trait:boost' AND source_id = 'n5-core-v5.3-pdf' "
            "AND page = 69"
        ).fetchone()[0] == 1


def test_mine_family_rules_apply_to_correct_army_weapon_profiles() -> None:
    import sqlite3

    from infinity_db.catalog_rules import CatalogRules
    from infinity_db.rules_database import RulesDatabase

    root = Path(__file__).resolve().parents[1]
    curated = json.loads((root / 'data/curated/rules/n5-core-v5.3.json').read_text(
        encoding='utf-8'))
    records = {r['id']: r for r in curated['records']}
    mine_slugs = {
        'ap-mine', 'e-m-mine', 'monofilament-mine', 'para-mine',
        'shock-mine', 'viral-mine', 'cybermine',
    }
    assert {link['id'] for link in records['weapon:mines']['armyLinks']} == mine_slugs
    assert records['weapon:cybermine']['armyLinks'] == [
        {'entity': 'weapon', 'id': 'cybermine'}]
    assert records['weapon:chest-mine']['armyLinks'] == [
        {'entity': 'weapon', 'id': 'chest-mine'}]
    for record_id in ('weapon:mines', 'weapon:cybermine', 'weapon:chest-mine'):
        record = records[record_id]
        assert record['variantSemantics'] == {'inheritance': 'family'}
        section = {'weapon:cybermine': 'Cybermines',
                   'weapon:chest-mine': 'Chest Mines'}.get(record_id, 'Mines')
        assert {'sourceId': 'n5-core-v5.3-pdf', 'page': 72,
                'section': section} in record['citations']

    with sqlite3.connect(root / 'data/generated/infinity.db') as db:
        slugs = {row[0] for row in db.execute(
            "SELECT slug FROM application_domain_slugs WHERE domain = 'weapons' "
            "AND status = 'resolved'")}
    assert mine_slugs | {'chest-mine'} <= slugs

    composed = CatalogRules(RulesDatabase(root / 'data/generated/rules.db'))
    for slug in sorted(mine_slugs | {'chest-mine', 'mine-dispenser', 'drop-bears'}):
        payload = composed.enrich_catalog_item(
            'weapons', {'id': slug, 'slug': slug, 'variants': []})
        actual = {r['id'] for r in payload.get('rules', [])}
        expected = ({'weapon:mines'} if slug in mine_slugs else set())
        if slug == 'cybermine':
            expected.add('weapon:cybermine')
        if slug == 'para-mine':
            expected.add('weapon:para-mine')
        if slug == 'chest-mine':
            expected.add('weapon:chest-mine')
        assert actual == expected, slug

    chest = composed.enrich_catalog_item('weapons', {
        'id': 'chest-mine', 'slug': 'chest-mine',
        'variants': [{'item_id': 147, 'mode': 'BS Mode'},
                     {'item_id': 147, 'mode': 'CC Mode'}],
    })
    assert {r['id'] for r in chest['rules']} == {'weapon:chest-mine'}
    assert all('rules' not in variant for variant in chest['variants'])


def test_mines_family_summaries_cover_general_and_exception_mechanics() -> None:
    root = Path(__file__).resolve().parents[1]
    curated = json.loads((root / 'data/curated/rules/n5-core-v5.3.json').read_text(
        encoding='utf-8'))
    records = {r['id']: r for r in curated['records']}
    general = records['weapon:mines']['summary']
    for text in ('360º LoF', 'Small Teardrop Template', 'Total Cover',
                 'without affecting any ally', '[[state:unconscious|Unconscious]]',
                 'must trigger', '-3 PH', '[[skill:mimetism]]',
                 '[[trait:intuitive-attack'):
        assert text in general
    cyber = records['weapon:cybermine']['summary']
    for text in ('[[skill:reset]] at -3 WIP', 'two BTS Saving Rolls',
                 '[[state:stunned]]', '[[state:immobilized-b|Immobilized-B]]'):
        assert text in cyber
    chest = records['weapon:chest-mine']['summary']
    for text in ('does not use the shared', '[[trait:direct-template]]',
                 '[[skill:cc-attack|CC attack]]', 'two uses',
                 'does not affect the bearer'):
        assert text in chest
