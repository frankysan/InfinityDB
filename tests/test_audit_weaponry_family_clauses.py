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


def test_checked_in_policy_has_83_distinct_reviewed_source_clauses() -> None:
    path = Path(__file__).resolve().parents[1] / (
        'config/validation/weaponry-family-clauses.json'
    )
    raw = json.loads(path.read_text(encoding='utf-8'))
    policy = _read_policy(path, raw['corePdfSha256'])
    assert [family['name'] for family in policy['families']] == [
        'Perimeter Weapons', 'Mines', 'Armed Turret', 'D-Charges',
        'Disco Baller', 'Drop Bears', 'Mine Dispenser',
         'Sepsitor', 'SymbioBomb', 'WildParrot', 'Pitcher', 'Mixed Weapons',
    ]
    assert [len(family['clauses']) for family in policy['families']] == [
        7, 14, 8, 9, 8, 6, 2, 5, 6, 3, 7, 8,
    ]
    assert len({clause['id'] for f in policy['families'] for clause in f['clauses']}) == 83
    assert sum(len(f.get('requiredRelations', [])) for f in policy['families']) == 16
    assert all(
        clause['semanticReview']['status'] == 'represented'
        for family in policy['families'] for clause in family['clauses']
    )


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
        'represented': 83,
    }


def test_curated_boost_rules_are_published_with_source_provenance(
    tmp_path: Path,
) -> None:
    import sqlite3

    from infinity_db.curated import load_curated_directory
    from infinity_db.rules_database import export_rules_database

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
    generated = tmp_path / "current_rules.db"
    export_rules_database(load_curated_directory(root / "data/curated"), generated)
    with sqlite3.connect(generated) as db:
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
        if slug == 'drop-bears':
            expected.add('weapon:drop-bears')
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


def test_turret_and_d_charges_clauses_are_pinned_to_distinct_family_records() -> None:
    root = Path(__file__).resolve().parents[1]
    policy = json.loads((root / 'config/validation/weaponry-family-clauses.json').read_text(
        encoding='utf-8'
    ))
    families = {f['name']: f for f in policy['families']}
    for name, record_id in (
        ('Armed Turret', 'weapon:armed-turret'),
        ('D-Charges', 'weapon:d-charges'),
    ):
        family = families[name]
        assert family['page'] == 70
        assert len(family['clauses']) >= 8
        assert all(record_id in clause['relatedCuratedIds'] for clause in family['clauses'])
        assert all(
            clause['semanticReview']['curatedId'] == record_id
            for clause in family['clauses']
        )
    ids = {c['id'] for c in families['Armed Turret']['clauses']}
    assert {'turret-deployable-traits', 'turret-place-in-zoc',
            'turret-model-not-marker', 'turret-stationary'} <= ids
    dc_ids = {c['id'] for c in families['D-Charges']['clauses']}
    assert {'dcharges-share-disposable', 'dcharges-resolution-no-roll',
            'dcharges-improvised-mod'} <= dc_ids


def test_selected_special_weapon_clauses_have_distinct_source_owners() -> None:
    """Do not conflate the six family mechanics or invent a SymbioBomb profile."""
    policy = json.loads(Path('config/validation/weaponry-family-clauses.json').read_text(
        encoding='utf-8'
    ))
    families = {f['name']: f for f in policy['families']}
    expected = {
        'Disco Baller': (71, 8),
        'Drop Bears': (71, 6),
        'Mine Dispenser': (72, 2),
        'Sepsitor': (73, 5),
        'SymbioBomb': (74, 6),
        'WildParrot': (74, 3),
    }
    for name, (page, count) in expected.items():
        family = families[name]
        assert family['page'] == page
        assert len(family['clauses']) == count
        assert all(clause['semanticReview']['status'] == 'represented'
                   for clause in family['clauses'])
    symbio = families['SymbioBomb']
    assert symbio['armyExamples'] == ['SymbioBomb']
    assert {c['semanticReview']['curatedId'] for c in symbio['clauses']} == {
        'weapon:symbiobomb',
    }
    disco = families['Disco Baller']['clauses']
    assert {c['semanticReview']['curatedId'] for c in disco} == {
        'weapon:disco-baller', 'skill:activate-disco-ball',
    }


def test_symbiobomb_printed_traits_have_cited_nonprofile_reference() -> None:
    root = Path(__file__).resolve().parents[1]
    curated = json.loads((root / 'data/curated/rules/n5-core-v5.3.json').read_text(
        encoding='utf-8'
    ))
    record = next(r for r in curated['records'] if r['id'] == 'weapon:symbiobomb')
    summary = record['summary']
    assert 'Assignable ([[skill:transmutation|Transmutation]])' in summary
    assert '**Comms Attack**' in summary
    assert '**Optional**' in summary
    assert 'no separate attack profile in the Weapon Chart' in summary
    # The link provides a stable detail page, not an imported attack profile.
    assert record['armyLinks'] == [{'entity': 'weapon', 'id': 'symbiobomb'}]
    assert any(
        c['sourceId'] == 'n5-core-v5.3-pdf' and c['page'] == 74
        for c in record['citations']
    )


def test_required_typed_relation_is_reported_when_missing() -> None:
    policy, pages = _fixture()
    policy['families'][0]['requiredRelations'] = [
        {'from': 'weapon:pitcher', 'type': 'uses-effects-of',
         'to': 'equipment:deployable-repeater'},
    ]
    with pytest.raises(WeaponryFamilyAuditError, match='typed-relation input'):
        compare_family_clauses(policy, pages, [], [])
    unrelated = [
        ('n5-core-v5.3', 'weapon:pitcher', 'uses-effects-of', 'equipment:repeater')
    ]
    result = compare_family_clauses(policy, pages, [], [], unrelated)
    assert result[0]['requiredRelationChecks'] == [
        {'from': 'weapon:pitcher', 'type': 'uses-effects-of',
         'to': 'equipment:deployable-repeater', 'present': False},
    ]
    present = [
        ('n5-core-v5.3', 'weapon:pitcher', 'uses-effects-of',
         'equipment:deployable-repeater'),
    ]
    assert compare_family_clauses(
        policy, pages, [], [], present
    )[0]['requiredRelationChecks'][0]['present']


def test_required_relation_schema_rejects_malformed_and_duplicate_edges(
    tmp_path: Path,
) -> None:
    policy, _ = _fixture()
    policy['corePdfSha256'] = 'a' * 64
    path = tmp_path / 'relation_policy.json'
    relation = {'from': 'weapon:pitcher', 'type': 'uses-effects-of',
                'to': 'equipment:deployable-repeater'}
    policy['families'][0]['requiredRelations'] = [relation, relation]
    path.write_text(json.dumps(policy), encoding='utf-8', newline='\n')
    with pytest.raises(WeaponryFamilyAuditError, match='Duplicate required relation'):
        _read_policy(path, 'a' * 64)
    policy['families'][0]['requiredRelations'] = [{'from': 'weapon:pitcher'}]
    path.write_text(json.dumps(policy), encoding='utf-8', newline='\n')
    with pytest.raises(WeaponryFamilyAuditError, match='Invalid relation evidence'):
        _read_policy(path, 'a' * 64)


def test_checked_in_required_relations_exist_in_current_curated_data() -> None:
    root = Path(__file__).resolve().parents[1]
    policy = json.loads((root / 'config/validation/weaponry-family-clauses.json').read_text(
        encoding='utf-8'
    ))
    curated = json.loads((root / 'data/curated/rules/n5-core-v5.3.json').read_text(
        encoding='utf-8'
    ))
    actual = {
        (record['id'], rel['type'], rel['recordId'])
        for record in curated['records'] for rel in record.get('relations', [])
    }
    required = {
        (r['from'], r['type'], r['to'])
        for family in policy['families'] for r in family.get('requiredRelations', [])
    }
    assert len(required) == 16
    assert required <= actual
    assert {
        ('weapon:pitcher', 'uses-effects-of', 'equipment:deployable-repeater'),
        ('weapon:mine-dispenser', 'modifies-use-of', 'weapon:drop-bears'),
        ('weapon:symbiobomb', 'uses-effects-of', 'weapon:pt'),
        ('weapon:sepsitor', 'causes-state', 'state:sepsitorized'),
    } <= required
    pitcher = next(f for f in policy['families'] if f['name'] == 'Pitcher')
    assert pitcher['page'] == 73 and len(pitcher['clauses']) == 7
    assert pitcher['armyExamples'] == ['Pitcher']
