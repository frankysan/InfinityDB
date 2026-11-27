# Data and source validation

**Project domains:** Data processing, Project infrastructure

Use [development checks](testing.md) for the runner and host workflow.
The [data lifecycle](../data/README.md), [data model](data-model.md),
[curated authoring contract](../data/curated/README.md) and
[source clarification register](official-source-clarifications.md) own the
data and source semantics. This guide owns validation selection, not
an independent schema or source-authority contract.

## Selected runtime database-set validation

```powershell
infinity-db database-health --db-dir data/generated --json
.\.venv\Scripts\python.exe -m tools.verify_deployment_assets
```

Use an explicit directory containing the complete four-database set when
testing alternate artifacts. Directory health and serving share the
complete-set validator; missing, stale or mismatched data fails without
fallback. The current schema requirements are in the
[data lifecycle](../data/README.md#current-paths-and-behavior).

Select `tests/test_database_set.py`, `tests/test_database_set_builder.py`,
`tests/test_app_cli.py` and `tests/test_verify_deployment_assets.py` for
affected CLI, selected-set, integrity, provenance, interruption/recovery and
deployment-artifact contracts. Exercise the relevant storage/projection
and API tests when changing a materialized schema.

The asset verifier checks selected release inputs and published SVGs;
`--skip-svg` is narrower development evidence, not full-publication
acceptance. [Release gates](releasing.md#4-run-local-release-validation)
remain separate.

## P1 migration semantic baseline

```powershell
.\.venv\Scripts\python.exe -m tools.runtime_semantic_baseline --check --db-dir data/generated --baseline tests/fixtures/runtime-semantic-baseline-v1.3.0.json
```

Use the default or explicitly appropriate maintained fixture for the target
release. Preserve reviewed prior fixtures; capture changes with `--capture`
to a new path rather than overwriting them. `--identical-artifacts`
additionally requires matching artifact metadata. See
`tests/test_runtime_semantic_baseline.py` for guardrails and the
[historical fixture lineage](https://github.com/frankysan/InfinityDB/blob/4774abde079a0e91ea87c9ee417c4ca1e2429403/docs/testing.md#p1-migration-semantic-baseline)
for the pinned 41-route migration evidence.
A semantic baseline does not replace source, visual or Docker acceptance.

## Full Army source-archive provenance tests

Legacy source-row parity consumers still require the release-matched ignored
`local/work/build/army/army.raw.db` fixture. The normal build and installed
export CLI no longer create raw SQLite siblings. Before a full source-backed
release run, prepare the fixture using the supported tool:

```powershell
.\.venv\Scripts\python.exe -m tools.testing.prepare_source_audit
```

This uses the pinned Army ZIP and selected runtime build provenance. It
verifies the complete normalized generation and the final published Army
database; it preserves unrelated/mismatched prior audit directories. Do not
substitute a standalone export for a release-matched pair. The relevant
fixture prerequisite in `tests/conftest.py` skips missing source-only inputs;
malformed or mismatched supplied evidence must fail.

Focused source-variant tests include `tests/test_audit_source_variant_inputs.py`,
`tests/test_other_source_variant_provenance.py` and
`tests/test_martial_arts_variant_provenance.py`.
For current manual source inspection prefer explicitly verified normalized
JSON rather than generating raw SQLite:

```powershell
infinity-db database-health local/work/build/army/army.db --normalized local/work/build/army/normalized.json --json
.\.venv\Scripts\python.exe -m tools.data.audit_source_variant_inputs --application local/work/build/army/army.db --normalized local/work/build/army/normalized.json --catalog skills --source-id 74
```

These example files must come from the same export generation.
See the [data lifecycle](../data/README.md) for raw/normalized alternatives
and audit consumers. The [2026-11-27 CLI retirement evidence](https://github.com/frankysan/InfinityDB/blob/4774abde079a0e91ea87c9ee417c4ca1e2429403/docs/testing.md#raw-sqlite-cli-retirement--2026-11-27)
records the verified parity and focused tests.

## Snapshot provenance and research inputs

The [snapshot provenance contract](../data/README.md#snapshot-provenance-contract)
is exercised offline by `tests/test_snapshot_manifest_publication.py` and
`tests/test_snapshot_provenance.py`. The former covers byte-exact replay,
CRLF conflicts, exclusive staging, competing manifest publication,
transaction ownership, symlink refusal and unsupported hard links. The
latter also covers historical formats, content hashes and portable
producer/consumer copies. No external producer package or live acquisition
is required by InfinityDB's normal test suite.

`tests/test_army_snapshot_source.py` adds the stricter explicitly selected
Army ZIP/manifest identity checks. `tests/test_database_set_builder.py`
checks equivalent legacy/local input layouts through complete set generation
and rejects source/manifest drift before publication. Run these four modules
as a focused acquisition/build batch when changing that handoff.

Use `tests/test_activate_synced_assets.py` for explicit source-layout
selection and safe staging. Use `tests/test_research_source_paths.py`
for pinned PDF path/hash/unsafe-link rejection, missing-source behavior
and layout isolation.

Pytest's `--reference-pdf-layout legacy|local` defaults to **local**.
Canonical provenance labels remain unchanged; local PDF and Wiki archive
paths are documented in the [source lifecycle](../data/README.md) and
[curated PDF bindings](../data/curated/README.md#explicit-physical-pdf-bindings-for-research).
The reference-baseline, PDF-delta and Reinforcements CLI auditors also default
to `local`; specify `--source-layout legacy` for historical physical layouts.
Other tools may have their own explicit-input contracts; consult their help.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_template_reference.py::test_template_conditions_match_pinned_pdf_wiki_and_faq -q --reference-pdf-layout local
```

Only unavailable source-dependent assertions skip. Verify every supplied
member before reporting a missing bilingual or historical sibling; an
unavailable file cannot hide a supplied mismatched hash. The ordinary
semantic/API tests still run against synthetic or tracked fixtures.
No normal validation implicitly downloads private sources.

## SQLite finalization in tests

Release/default Army and rules exports perform canonical SQLite physical finalization so generated
files are byte-stable. Some semantic tests may explicitly use exporter APIs with physical
finalization disabled to avoid repeatedly paying for `VACUUM`/header canonicalization when the test
only asserts logical database contents.

That optimization skips only physical finalization. It must not bypass source validation, schema
creation, integrity checks, semantic materialization, or atomic destination replacement.
Army export tests also simulate interruption between raw-sibling replacement and the application
commit point: the previous application remains valid, the mismatched pair is rejected, and rerunning
export restores one matching generation. Determinism/release tests continue to exercise the
canonical finalized path.

## Curated source and publication checks

For maintained reference changes, choose a focused cross-layer set:

- Curated schema and maintained text (`tests/test_curated.py`,
  `tools.data.audit_maintained_text_links`), exact source and citation
  coverage (`tests/test_report_reference_baseline.py`).
- Affected Army/Rules/ITS storage, identity, usage and composition tests;
  verify exact variant scope, source conflicts, and source-native versus
  curated facts. Use `tools.data.audit_source_variant_inputs`,
  `tools.data.audit_enrichment_coverage` and related semantic audits as needed.
- Normal API and browser journeys for changed cards, links and source warnings;
  see [browser acceptance](testing-browser.md).
- Use `tools.data.audit_rules_interactions` for the maintained review ledger,
  not a count-based completeness claim. Use the runner's rules stage for
  curated rules/checklist validation; use the integrated build to publish
  all current runtime projections.

```powershell
.\.venv\Scripts\python.exe tools/run_checks.py --stage rules
.\.venv\Scripts\python.exe -m tools.research.report_reference_baseline --help
.\.venv\Scripts\python.exe -m tools.data.audit_source_presentation --help
.\.venv\Scripts\python.exe -m tools.data.verify_complete_database_build --help
```

The source evidence inventory does not by itself prove correct rules meaning,
completeness or source publication date. Use
[the source research contract](rules-research.md) and
[N5 source history](n5-source-history.md) for scope and current pins.
Earlier version-specific source evidence is preserved in the
[1.0 source baseline](https://github.com/frankysan/InfinityDB/blob/4774abde079a0e91ea87c9ee417c4ca1e2429403/docs/testing.md#10-source-evidence-baseline).

## Research receipts and publication candidates

Use unique ignored output paths under `local/validation/` or
`local/research/` for source and semantic audits. For example:

```powershell
.\.venv\Scripts\python.exe -m tools.research.audit_weapon_chart_profiles --core-pdf PINNED_N5_PDF --json-output local/research/weapon-source-audits/RUN_ID/chart.json --markdown-output local/research/weapon-source-audits/RUN_ID/chart.md
.\.venv\Scripts\python.exe -m tools.data.audit_unit_semantics data/generated/army.db --output local/validation/data-model/unit-semantics/RUN_ID/unit-semantics.json
```

Substitute real pinned inputs and a fresh run ID. The maintained report
helpers refuse occupied or symlink destinations and use exclusive creation;
multi-output reports are not a transaction. Inspect partial new output
after interruption. Failed checks retain their failure status even when
they write a report. See the relevant CLI for exact output flags and
source dependencies.

Distinguish evidence from deliberate outputs: generated interaction
checklists have a maintained refresh contract; variant usage candidates
are not published data; symbol source plans are immutable handoffs and
may reuse identical content. The [data lifecycle](../data/README.md) owns
candidate, source and promotion paths. Do not assume replaceable work
archives, build scratch or persistent database state are immutable receipts.

## Release-tracked FAQ parity

Normal FAQ API/browser tests build fresh Rules fixtures. They cannot prove
the checked-in `rules_n5.db` matches the current reviewed content.
After rebuilding and verifying the complete release set, enable the
release-only tracked-database cohort explicitly.

Windows PowerShell:

```powershell
$env:INFINITYDB_RELEASE_FAQ_PARITY = "1"
try {
    .\.venv\Scripts\python.exe -m pytest tests/test_faq_ruling_references.py::test_tracked_faq_database_matches_current_curated_release_projection tests/test_verify_scenario_faq_browser.py::test_release_faq_primary_entry_points_use_tracked_database tests/test_verify_scenario_faq_browser.py::test_release_faq_secondary_entry_points_use_tracked_database tests/test_verify_scenario_faq_browser.py::test_release_faq_haris_conflict_uses_tracked_database -q
} finally {
    Remove-Item Env:INFINITYDB_RELEASE_FAQ_PARITY -ErrorAction SilentlyContinue
}
```

Linux:

```sh
INFINITYDB_RELEASE_FAQ_PARITY=1 .venv/bin/python -m pytest tests/test_faq_ruling_references.py::test_tracked_faq_database_matches_current_curated_release_projection tests/test_verify_scenario_faq_browser.py::test_release_faq_primary_entry_points_use_tracked_database tests/test_verify_scenario_faq_browser.py::test_release_faq_secondary_entry_points_use_tracked_database tests/test_verify_scenario_faq_browser.py::test_release_faq_haris_conflict_uses_tracked_database -q
```

This is the 17-case opt-in gate (one source/API parity test plus
parameterized browser cases). Ensure Chromium is available and the
required cases actually run. It checks reviewed facts, citation metadata,
topic/scenario selection, date/revision exclusion and normal-browser
association/conflict presentation against tracked databases. It does not
rewrite the publication or establish live deployment/source authority.
The [release checklist](releasing.md#4-run-local-release-validation)
owns when this gate is mandatory.

## Focused reference regressions

- Structured charts (Martial Arts, Booty, MetaChemistry): use the current
  curated, Rules and structured-chart browser tests; historical
  [chart parity evidence](https://github.com/frankysan/InfinityDB/blob/4774abde079a0e91ea87c9ee417c4ca1e2429403/docs/testing.md#10-martial-arts-booty-and-metachemistry-structured-chart-parity).
- Restrictions: use current source-chart, storage and browser tests and
  `tools.research.audit_restrictions_source_chart --help`; historical
  [Restrictions review](https://github.com/frankysan/InfinityDB/blob/4774abde079a0e91ea87c9ee417c4ca1e2429403/docs/testing.md#n53-restrictions-chart-source-and-browser-reference).
- Fireteam source annotation: use current Fireteam semantics and API/browser
  tests; historical [annotation applicability evidence](https://github.com/frankysan/InfinityDB/blob/4774abde079a0e91ea87c9ee417c4ca1e2429403/docs/testing.md#fireteam-annotation-applicability).
- Core and ITS scenario composition: `tests/test_scenario_components.py`,
  `tests/test_scenario_catalog.py`, `tests/test_scenario_api.py`,
  applicable ITS publication and browser tests. The
  [ITS acceptance record](its-season-database.md#release-browser-acceptance)
  owns reviewed season coverage.

Source evidence and earlier release-specific procedures remain available in
the [historical record](https://github.com/frankysan/InfinityDB/blob/4774abde079a0e91ea87c9ee417c4ca1e2429403/docs/testing.md). Do not rerun retired staging or legacy
CLI commands merely because they were used on an older release.
