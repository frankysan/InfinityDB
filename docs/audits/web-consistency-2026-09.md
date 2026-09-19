# Web-app consistency audit — 2026-09

## Status

In progress. This document records evidence from one pinned local production
artifact set and the results of the Milestone 2 audit matrix. Synthetic fixtures
are used only for regression coverage, never as production-audit evidence.

## Baseline

| Item | Pinned value | Verification status |
| --- | --- | --- |
| Checkout | `main` at `512bf28b8b6633600ce9fb7bc78c23c6ffcc330c` | Recorded; this audit document and the Milestone 2 TODO are uncommitted audit work. |
| Army snapshot | `JSON 20260918-204434.zip`, SHA-256 `858309ea44b6a07f0aadb7bf2856d6c0dfdcb75dbe587b85997ed46c4780e3a3` | Recorded from terminal `army-symbol-build.json` v8. |
| Army source provenance | Acquired `2026-09-18T20:44:34+02:00`; 59 documents; revisions `7.26246.158` (36) and `7.26246.159` (22) | Recorded from terminal symbol-build manifest. |
| Symbol snapshot | `SYMBOLS 20260919-131535.zip`, SHA-256 `dea1ae983f72388eec5e4700d40d8070befea94ec1dff09302b03025b8880208` | Recorded from terminal symbol-build manifest. |
| Runtime Army database | `data/generated/infinity.db`; schema `11`, compatibility revision `16` | **Fails deployment provenance validation:** it has no validated `snapshotArchiveSha256`, so it cannot be bound to the promoted symbol publication. Rebuild from the pinned Army ZIP. |
| Runtime rules database | `data/generated/rules.db`; schema `2` | Present. Rules enrichment remains a separately audited composition boundary. |
| Published symbols | Static inventory and four generated SVG trees are present locally | Readable outside the workspace sandbox. The deployment validator reaches database provenance validation; rerun it after rebuilding `infinity.db` from the pinned Army ZIP. |
| Browser module maps | `static/army-symbols.js` and `static/unit-symbol-map.js` are generated browser modules | Imported by the Unit explorer through `unit-symbols.js` | Live browser route inspection | **Blocked:** the local development server receives `PermissionError` reading both modules, leaving `/units` permanently in its loading state. |

The terminal manifest is format version 8 and identifies the intended Army and
symbol source artifacts. It is not by itself evidence that the generated
database and published assets are mutually valid. The validator can read the
local publication outside the sandbox, but currently reports that the runtime
database lacks a validated `snapshotArchiveSha256`.

## Audit matrix

| Concept | Storage / backend contract | Browser consumers | Existing coverage | Result |
| --- | --- | --- | --- | --- |
| Logical/source unit identity | `logical_units` and `logical_unit_sources`; repository maps source and representative IDs | Unit explorer and detail | Repository/API coverage plus pinned live API samples | API verified; live browser pass pending |
| Army hierarchy, role, and playability | Army lists plus metadata parent relationships; `/api/armies` role/playability contract | Army selector and unit filtering | Repository/API coverage plus pinned live API samples | API and selector source contract verified; live browser pass pending |
| Faction/display identity | Backend-derived `main_army_id`, `display_army_id`, faction data, and display names | Unit list/detail grouping and labels | Repository/API coverage plus pinned live API samples | API verified; live browser pass pending |
| Optional availability | `army_units.availability_kind` and occurrence provenance | Unit filtering and availability labels | Repository/API coverage plus pinned live API samples | API verified; browser preference behavior reviewed |
| Profiles and loadouts | Source-keyed profile/loadout/option records | Unit detail | To audit | Not started |
| Skills, Equipment, Weapons, Traits | Army catalog/usage plus application-level rules composition | Catalog list/detail and unit detail | To audit | Not started |
| Distance/range semantics | Imported source values plus curated display semantics where applicable | Skill and weapon detail | To audit | Not started |
| Symbols | Terminal symbol manifest, inventory, and static mappings | Unit and army symbol views | To audit | Blocked pending publication read access |
| Source, wiki, and rules provenance | Army metadata and curated rules citations | Catalog and detail links | To audit | Not started |
| Filtering, sorting, counts, and deep links | Validated query/API behavior | List/detail route state | To audit | Not started |
| Fireteams | Imported `fireteams`, types, and members are retained | No repository/API/browser surface | To audit | Deferred UI; preservation audit pending |

## First vertical-slice results

- `/api/armies` returned 57 entries. It identifies `901` as the non-playable
  `grouping` identity and `902` as a playable `non_aligned` army in that group.
  `/api/units?army_id=901` correctly returns HTTP 400, while the corresponding
  query for 902 succeeds.
- Source unit ID `10051` resolves through `/api/units/10051` to logical unit 51
  with source IDs 51, 1693, and 10051. It retains no ownership
  `main_army_id` and reports display army 901. The separate 255/1633 source pair
  resolves to logical unit 255. These are expected examples of source identity
  consolidation and display identity remaining separate from ownership.
- The four optional-unit switches are persistent browser preferences, initialized
  by `preferences.js`, rather than shareable URL filters. The Unit explorer
  deliberately removes optional-filter query parameters from its URL and obtains
  their state from those preferences. This is not a deep-link inconsistency.

## Transport-boundary result

- The documented JSON API transport boundary has drifted: `catalog-list.js`,
  `catalog-detail.js`, `skill.js`, `skill-extras.js`, and `version-check.js`
  called `fetch()` for JSON API routes directly. `app.js` and `unit.js` already
  used `api.js`. Static/HTML loading is outside this finding.
- **Resolved:** those page modules now use typed helpers in `api.js`; API error
  payloads are preserved for their existing page-level error states. The focused
  static contract test prevents these modules from reintroducing direct JSON
  transport calls.

## Browser-runtime result

- Chrome rendered `/units`, but its module dependency chain could not complete:
  the server returned HTTP 500 for the generated `army-symbols.js` and
  `unit-symbol-map.js` files because the current process lacks read access. The
  page consequently remains in its loading state with a disabled army selector.
  This is a local artifact-access/deployment issue, not a browser UI result.

## Pending work

- A live browser pass remains pending because this audit environment has no
  usable rendered Unit explorer until read access to the generated symbol modules
  is restored. The local development server and live HTTP checks do not substitute
  for route-level rendering verification.
- Continue with profile/loadout and unit-detail semantic ownership after the
  browser pass or a browser-capable audit environment becomes available.

## Closure criteria

- Complete every matrix result or record an explicit, justified deferral.
- Rebuild `infinity.db` from the pinned Army ZIP, then re-run the deployment
  asset validator against the published inventory and SVG trees.
- Run the normal project checks and full-asset validation against this pinned
  publication when it is available.
- Perform a second storage-to-browser pass after fixes and update canonical
  documentation, this record, and release notes for material outcomes.
