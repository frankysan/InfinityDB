# Browser acceptance

**Project domains:** Web frontend, Project infrastructure

Use the [testing guide](testing.md) for local execution, the
[design guidelines](web-design-guidelines.md) for the visual/interaction
contract, and [releasing](releasing.md) for required release gates.
Run affected automated browser tests and inspect rendered output when the
change involves visual hierarchy, clipping, spacing or interaction.
Source/API verification, DOM assertions, screenshots and actual manual
keyboard/touch/assistive-technology review are distinct evidence.

## Focused browser execution

```powershell
.\.venv\Scripts\python.exe tools/run_checks.py --stage test --test-section browser --test-workers 2
.\.venv\Scripts\python.exe tools/run_checks.py --stage test tests/test_verify_scenario_faq_browser.py --test-workers 2
```

Check real Chromium availability; missing browser dependencies may cause
optional browser cases to skip. Use the existing environment's Playwright
and matching browser installation. The controlled cross-browser cohort
below owns its explicit engine setup. On Linux use the
[host profile](testing-performance.md#chromium-concurrency-under-pytest-xdist)
for broad runs, not as a prerequisite for small focused checks.

Use Developer Mode off first; then check intentionally exposed technical
details. Select affected desktop and narrow viewports (typically 1440,
390 and 320 CSS px), modes/palettes, loading/error states, keyboard/touch,
soft navigation and deep/shared links. Check page/console errors, failed
requests, semantic destinations and unwanted horizontal overflow as relevant.
Prefer an existing test fixture or verifier over a new standalone harness.

The browser module registry is in
[config/testing/test-sections.json](../config/testing/test-sections.json).
The connected MCP browser may provide exploratory visual diagnostics where
origin policy permits; see the
[workspace skill](../.agents/skills/infinity-mcp-workspace/SKILL.md).
It does not replace the tracked regression or release acceptance.

## Complete-set release-candidate browser verifier

`tools.verify_release_candidate_browser` compares an explicit release version,
the static fingerprint and the **complete Army/Rules/ITS database identity**
against the selected server before and after representative Unit-detail browser
cases. It validates the selected directory through the same complete-set
validator as serving, including embedded publications, schemas, integrity and
matched build/source provenance. A missing or invalid ITS database blocks the
gate before network/browser work. Changes to the local selected set or static
fingerprint during the check also block acceptance.

Use one `--db-dir` containing the four runtime databases; its default is the
checkout's `data/generated/`. The former individual `--army-db`/`--rules-db`
selectors and two-path Python API are retired for this gate. Other research
tools and explicit low-level fixture APIs retain their independently documented
contracts. An alternate directory never falls back to the checkout's databases.

For an already-running candidate, replace the version, origin and `RUN_ID`
with its pinned values:

```powershell
.\.venv\Scripts\python.exe -m tools.verify_release_candidate_browser --db-dir data/generated --base-url http://127.0.0.1:8000 --expected-version VERSION --channel chrome --json-output local/validation/project-infrastructure/release-candidate/RUN_ID/acceptance.json
```

The optional JSON receipt is written only on success. Its selected file must
be new: the verifier rejects an existing file or symlink **before** runtime
and browser work, and uses exclusive creation after postflight checks to
prevent an intervening writer from truncating earlier evidence. Select a
fresh `local/validation/` run-ID directory for every attempt, keeping
accepted receipts and failed/incomplete diagnostics separate. If filesystem
writing fails, CLI acceptance is blocked; any partially created **new**
receipt requires inspection rather than reuse. Omitting `--json-output`
still runs the verification without writing a receipt. Existing explicit
legacy output paths are not migrated or deleted.

Retain successful receipts with the pinned candidate evidence while
acceptance is open. This command starts no server,
build, acquisition or deployment. Complete-set identity plus selected Unit
cases does not establish whole-reference completeness, all browser surfaces or
post-deployment acceptance. The nested preflight and postflight `status` values
are `exact-runtime-revision-match-not-source-completeness`; they describe the
selected complete runtime revision, not a two-database pair.

Focused regressions live in `tests/test_verify_release_candidate_browser.py`,
including missing/invalid/mismatched ITS inputs, ITS-only byte changes, local
drift and real loopback Chromium preflight/DOM/postflight acceptance.

## Optional browser verifiers and receipts

The maintained modules under [tools/browser](../tools/browser) provide
bounded checks for catalog navigation (Ammunition, General Rules, Labels,
States, Traits), Hacking Programs, non-Skill Army data, Unit Skill
presentation/history, structured Skill charts, Trait Wiki anchors and
rule fragments. Use the applicable module's `--help` for source inputs,
`--self-host` or `--base-url` support and report flags.

```powershell
.\.venv\Scripts\python.exe -m tools.browser.verify_labels_browser --base-url http://127.0.0.1:8000 --output local/validation/browser/catalog-navigation/RUN_ID/labels.json
.\.venv\Scripts\python.exe -m tools.browser.verify_hacking_programs_browser --self-host --output local/validation/browser/hacking-programs/RUN_ID/hacking-programs.json
.\.venv\Scripts\python.exe -m tools.browser.verify_rule_fragment_browser --self-host --output local/validation/browser/rule-fragments/RUN_ID/fragments.json
```

Use a fresh ignored output location; the shared receipt helper refuses
occupied paths/symlinks and creates files exclusively. Some verifiers
retain failed observations with a nonzero exit; report contents and
terminal status must both be inspected. A partial new receipt is not
acceptance. For historical source/browser matrix evidence use the
[pre-split record](https://github.com/frankysan/InfinityDB/blob/4774abde079a0e91ea87c9ee417c4ca1e2429403/docs/testing.md), not its superseded commands.

## Portable cross-browser critical-journey cohort

**Project domains:** Web frontend, Project infrastructure

Use `python -m tools.browser.run_cross_browser_compatibility --engine chromium` for
an explicitly selected local engine; `firefox`, `webkit` and `msedge` are
also supported. Install `playwright==1.64.1` and that engine using
`python -m playwright install <engine>` first (on Linux CI the matching OS
libraries are installed with `--with-deps`). The helper runs the dedicated
`tests/test_cross_browser_compatibility.py` cohort with one engine, exits
nonzero on failed/missing browser setup and stores its JUnit report and
failure screenshot/Playwright trace files together under a fresh
`local/validation/project-infrastructure/cross-browser/<UTC-run-id>-<short-SHA>/<engine>/`
directory. The output directory is created exclusively before pytest starts;
an existing directory fails without modifying previous evidence. Use
`--output-dir local/validation/project-infrastructure/cross-browser/<RUN_ID>/<engine>`
to select another fresh directory under `local/validation/`. The runner
requires a resolvable checkout Git HEAD SHA for its automatic directory
and passes the same output directory to its test module. The HEAD label does
not certify that a local worktree is clean; only separately verified
exact-SHA acceptance can do that. Run the module via this runner rather
than setting only the browser engine environment variable.
Hosted CI uploads the `local/validation/project-infrastructure/cross-browser/`
tree, preserving the same JUnit and failure traces on both successful and
failed runs. Previously retained `local/cross-browser-compatibility/`
artifacts remain unchanged and are not treated as current run output.

The ordinary source suite does not require Playwright and skips this
opt-in module without an engine. The hosted matrix is
[optional for v1.1+, mandatory for v1.0.x](ci.md#cross-browser-release-compatibility-gate).
A successful local cohort cannot replace any selected hosted gate, and the
81-page Unit matrix is not multiplied across browser engines.

## Theme and scenario regression coverage

Use `tests/test_theme_contrast.py`, the theme/preference startup and
web presentation regressions, and representative actual Chromium pages.
The selected palette and Auto/Light/Dark mode must resolve before first
paint; preference ownership, navigation lifecycle and the stable stylesheet
contract are in [architecture](architecture.md#browser-theming).
For source/citation hierarchy check the normal rule body, reviewed examples,
interpretations, FAQ conflicts and source uncertainty across affected palettes.

```powershell
.\.venv\Scripts\python.exe -m tools.browser.review_reference_palettes --output local/validation/browser/palette-review/RUN_ID
```

Scenario API/lifecycle tests check aborted or late requests, distance
preference listeners, game-size switching and the canonical map response.
Use the current scenario and ITS browser cohorts for setup, citations,
scoring and linked rules. The [ITS guide](its-season-database.md)
owns full season geometry and browser acceptance.

```powershell
.\.venv\Scripts\python.exe -m tools.research.render_its_map_previews --standalone --theme dark --distance-unit cm --width-px 360
```

Standalone SVG previews must match the published API bytes and retain
the selected palette, unit labels, scale and geometry. Check selected
large/narrow maps and actual native image saving when relevant.

## Silhouette manual browser acceptance

The scale-preserving Silhouette renderer has automated structural coverage, but the release gate
retains a small real-browser review because clipping, touch behavior, and theme rendering are visual
interaction concerns. Use the current generated database and check these representative Unit pages:

- `/units/cadin-firststrike-donn` — S2, shown without a duplicate reference;
- `/units/ajax-the-great-myrmidon-officer` — S5 plus the faded S2 reference;
- `/units/gator-squadron` — S7 plus the faded S2 reference;
- `/units/maghariba-guard` — S8 plus the faded S2 reference.

Also check `/glossary#attribute-s`. In both Light and Dark themes, confirm the Glossary S1–S8 set
keeps one common relative scale, wraps into equal-width rows without horizontal clipping, and does
not widen the normal Glossary content column. On the Unit examples, confirm the `S` value opens the
preview with mouse hover, keyboard focus, and touch/click; the popup must remain on-screen at narrow
widths, preserve the selected-template/S2 relative scale, and close normally when focus/pointer
moves away or the touch/click interaction is dismissed. Record actual review evidence with the applicable release/task; do not
replace this acceptance check with screenshot-only or DOM-only evidence.

## Official Army deep-link acceptance

Use `tests/test_official_army_links.py` for exact source-native destinations,
ambiguous/unsupported values and reinforcement-parent routing.
For changed link semantics verify representative live destinations in an
approved isolated browser. Do not infer the external app's current behavior
from a historical route or source bundle.

The [2026-11-26 route review](https://github.com/frankysan/InfinityDB/blob/4774abde079a0e91ea87c9ee417c4ca1e2429403/docs/testing.md#official-army-deep-link-acceptance)
verified Zeros in Nomads/Bakunin and reinforcement Prowlers. This is
representative external-app evidence, not an exhaustive live audit.

## Faction palette and rules-content visual acceptance

The [2026-11-26 visual review](https://github.com/frankysan/InfinityDB/blob/4774abde079a0e91ea87c9ee417c4ca1e2429403/docs/testing.md#faction-palette-and-rules-content-visual-acceptance)
passed 7 contrast, 2 hierarchy and 4 scenario-map regression tests and
192 representative page/viewport/theme combinations. It identified and
corrected primary gameplay-text contrast. This dated result does not
establish current release acceptance; use the reproducible review above.

## Scenario SVG standalone visual acceptance

The [2026-11-26 standalone review](https://github.com/frankysan/InfinityDB/blob/4774abde079a0e91ea87c9ee417c4ca1e2429403/docs/testing.md#scenario-svg-standalone-visual-acceptance--2026-11-26)
covered 20 Chromium previews; the subsequent
[edge-adjacent ruler correction](https://github.com/frankysan/InfinityDB/blob/4774abde079a0e91ea87c9ee417c4ca1e2429403/docs/testing.md#edge-adjacent-placement-ruler-labels--2026-11-27)
passed 183 focused tests and six representative standalone Chromium
previews. Firefox was unavailable in the first Windows review. Neither
result establishes compatibility with every standalone SVG viewer.
