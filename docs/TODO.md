# InfinityDB backlog

This is the working implementation backlog. Every unchecked item belongs to exactly
one release bucket: **0.9.0**, **0.10.0**, **1.0.0**, or **post-1.0**.
The buckets are planning commitments, not a promise that a minor release cannot move a
low-risk item earlier or defer a non-gating item when evidence changes.

This file does not define current application behavior. Current behavior belongs in
the relevant reference documentation; lasting design direction belongs in
`docs/architecture.md` or `docs/data-model.md`; durable release acceptance criteria
belong in `docs/releasing.md`.

Keep completed substeps while their parent task is still open because they clarify
progress and remaining scope. Once a standalone or parent task is complete, remove it
after any durable outcome is recorded in `CHANGELOG.md`, architecture/data-model
documentation, or another appropriate reference. Git history retains implementation
detail. New or materially revised work items use the canonical project-domain labels
defined in `docs/project-domains.md`; section-level domain declarations may be used
when all contained work shares the same owner.

## Current milestone

The current milestone is **0.9.0 — application completeness and discoverability**.
It follows the completed 0.8.0 connected-data milestone by closing the remaining
player-facing application-data gaps and making the resulting data searchable,
navigable, and understandable.

General performance/storage experiments, major pipeline refactors,
persistent-user-data features, ITS tooling, and native applications are explicitly
post-1.0 unless they become necessary to correct a release-blocking defect.

## Release roadmap through 1.0

- **0.8.x — Connected game structure.** Added Fireteams and exposed the structural
  relationships already present in the canonical application data.
- **0.9.x — Complete and make discoverable.** Close remaining player-facing
  application-data gaps and make the resulting data searchable, navigable, and
  understandable.
- **0.10.x — Audit, present, and harden.** Run the end-to-end consistency audit,
  finish the intended frontend/theme architecture, and harden CI/operations without
  adding another major game-data domain.
- **1.0.0 — Player data-complete.** Close the remaining current rules/reference gaps
  and pass the final source-to-storage-to-browser completeness gate. A full ITS
  scenario library, list builder, and other broader product tooling are not part of
  the 1.0 gate.
- **Post-1.0 — Expand and optimize.** Pursue optional product features, persistent
  user data, ITS/scenario tooling, native apps, historical-data features, pipeline
  refactors, and performance/storage experiments.

The concise public framing remains: **0.6 built the foundation → 0.7 added context →
0.8 connected the data → 0.9 closes application gaps → 0.10 hardens and polishes →
1.0 completes the reference.**

## 0.9.0 — application completeness and discoverability

0.9.0 completes discoverability and navigation around the player-facing application model
without absorbing the separate consistency, frontend-architecture, theme, and operations
hardening work reserved for 0.10.0. The maintained source-to-presentation inventory now has no
confirmed application-data presentation gap.

The Unit Explorer filtering/extended-results work, global search, structured rules-reference
cross-link pass, Profile notation foundation, maintained-text reference/token layer, application-
domain publication, and share-state work are complete. The original 0.9 application-completeness
and discoverability scope is closed, but the pre-release polish checklist below was added before
tagging the release and remains part of the 0.9 gate. Broader hardening still belongs to 0.10.
`docs/application-domains.md` defines the accepted domain skeleton and interaction model.

### Player-facing completeness and navigation

- [x] Complete the systematic semantic-link migration of all maintained rules prose. The legacy
  candidate baseline has been retired: all supported semantic-reference namespaces are now covered
  by completed review batches, and any new unlinked candidate fails the rules build directly. Any
  passage examined during review that remains ambiguous or unclear must use an explicit
  `review-needed` marker until manual review resolves it.
  - [x] Establish canonical-name/alias candidate auditing and make new unlinked candidates fail
    the rules build while grandfathering only the pre-migration corpus.
  - [x] Batch 1: replace unambiguous full State names such as `Unconscious State`,
    `Dead State`, and the reviewed `Retreat State` alias with typed `state:*` references.
  - [x] Batch 2: review and link all unambiguous Hacking Program names. The post-batch
    legacy inventory is 671 candidate occurrences across 183 semantic owners, with no remaining
    `hacking-program:*` candidates.
  - [x] Batch 3: review and link Equipment names. The post-batch legacy inventory was 625
    candidate occurrences across 178 semantic owners, with no remaining `equipment:*` candidates.
  - [x] Establish explicit `review-needed` markers for passages that have been examined but cannot
    yet be resolved safely.
  - [x] Retrospectively audit completed Batches 1-3 with a broader case-insensitive/plural residual
    scan and keep that scan as a build gate. It found one missed unambiguous `Holoecho States`
    reference, now linked, and a second ambiguous `HoloMask` passage, now explicitly flagged. The
    current inventory is 623 legacy candidates across 178 semantic owners plus two explicit
    `review-needed` markers.
  - [x] Batch 4: review Trait names, including the generic/colliding surfaces `State`, `CC`,
    `ARO`, `Zone of Control`, `Deployable`, and same-name Skill/State concepts. Confident non-Trait
    uses are fingerprinted as reviewed plain surfaces; unresolved Deployable/Direct Template/
    Perimeter scope and plural Deployables remain explicit `review-needed` markers. The broad pass
    classified all 332 Trait-name matches: 20 became semantic links, 293 were fingerprinted as
    reviewed non-Trait text, and 19 became new review markers. The post-batch legacy inventory is
    411 candidates across 141 semantic owners, with only Skill and State namespaces remaining and
    21 explicit review markers total including the two earlier HoloMask reviews.
  - [x] Batch 5: review Skill names. The broader case-insensitive/plural pass classified 401
    Skill-name matches: 324 became typed Skill links, 68 were confirmed as same-text game
    categories/states/modes or ordinary language and bound to reviewed passage fingerprints, and
    9 newly unclear source/collision uses became explicit `review-needed` markers. The post-batch
    legacy inventory is 66 candidates across 43 semantic owners, all in the State namespace, with
    30 explicit review markers total.
  - [x] Batch 6: review the remaining State aliases/collisions. The broad pass classified 87 State
    alias/name matches: 40 became typed State links and 47 ordinary/cross-domain uses of `Normal`,
    `targeted`, `Retreat`, and Decoy terminology were bound to reviewed passage fingerprints. The
    legacy candidate inventory is now zero. Weapon, Ammunition, and Attribute namespaces also
    received explicit case-insensitive/plural completeness audits with zero residuals, and the
    temporary legacy baseline has been removed.
  - [x] Resolve the 30 explicit `review-needed` passages by manual source/context review. Source-
    backed Deployable/Perimeter, Discover/Neurocinetics/Idle/Decoy/HoloMask, and Impersonation
    references are now typed links; the three Direct Template attack-rule passages and Infiltration's
    descriptive `forward deployment` phrase are confirmed ordinary/cross-domain text and bound to
    reviewed passage fingerprints. The maintained-text audit now reports zero unlinked candidates,
    zero reviewed-batch residuals, and zero explicit review markers.

- [x] **Data processing + Web backend + Web frontend:** Continue the application-domain framework
  established in `docs/application-domains.md` without adding one-off catalog/navigation structures.
  - [x] Add `/armies` as an overview surface with each Army's symbol, concise structural
    description, and a link to Unit Explorer pre-filtered by the canonical Army identity. Do not add
    per-Army detail pages without a separate player-facing use case.
  - [x] Normalize `/fireteams` to the shared landing/scoped contract: the unscoped page shows the
    Army selector plus general Fireteam rules summary; selecting an Army hides that summary and
    shows the Army-scoped chart/reference content; clearing the selection returns to the landing
    state; scoped state remains URL-addressable/shareable.
  - [x] Establish Attributes as an embedded canonical vocabulary for semantic links, tooltips,
    Glossary/search, and related metadata without adding an `/attributes` catalog or individual
    Attribute detail pages.
  - [x] Publish General Rules only as the explicit fallback for rules/reference concepts with no
    clearer top-level owner. The initial catalog publishes reviewed basic-rule, order-type,
    command-token-use, and Peripheral-type records; Fireteam rules and Unit-profile help stay with
    their clearer application owners, and embedded vocabularies still do not gain manufactured
    detail pages.

- [x] Complete deep-linkable, shareable search and filter state for catalog and
  Unit views.
  - [x] Unit Explorer Army, declared-faction, name, Skill, Equipment, Weapon,
    pagination, and sort state already participate in URL state. Global search uses
    its own shareable `q` parameter.
  - [x] Add the 0.9 Unit filters and extended-results mode to the URL contract so
    categorical/numeric filtering and the optional extended Unit presentation remain
    reproducible in shared links. Extended presentation uses `extended=1`.
  - [x] Make catalog-list search/filter state deep-linkable where it is still only
    local browser state. Searchable catalog landing pages now use the shared `q` query parameter,
    hydrate it before first render, and remove it when the search is cleared.
  - [x] Define how optional-unit preferences interact with reproducible shared Unit
    URLs. Unit Explorer now owns page-local optional-availability controls and records the effective
    `mercs`, `specops`, `teamops`, and `reinforcement` values explicitly as `0`/`1` URL state. A
    location with no optional flags is initialized from the user's Settings and immediately
    canonicalized to the full four-value URL; explicit shared state never overwrites saved Settings,
    and the page explains when the current result set came from preferences or overrides them.

### Pre-release polish

- [x] **Web backend + Web frontend:** Make structured Related rules links to Peripheral subtypes
  resolve to their General Rules detail pages, for example **Can control: Peripheral (Cyberplug)**.
- [x] **Web frontend:** Standardize rules-card badge ordering across domains: Labels first, then
  Skill/declaration category badges.
- [x] **Web frontend:** Make Unit Explorer Army-availability symbols deep-link to the Unit detail
  page with that Army profile expanded. Honor that explicit Army target even when the recipient's
  optional-unit Settings would otherwise hide it.
- [x] **Web frontend:** Retain the Unit Explorer Advanced filters disclosure state across reloads
  using the existing session/persistent Settings contract.
- [x] **Web frontend:** Make desktop sidebar vertical spacing responsive to viewport height so
  navigation/settings/footer content begins scrolling later on shorter displays.
- [x] **Web frontend:** Increase Army symbols on `/armies`.
- [x] **Web frontend:** Normalize `/armies` card heading geometry so symbols, Army-type labels, and
  Army names stay aligned when names wrap to multiple lines.
- [x] **Data processing + Web frontend:** Replace structural `/armies` descriptions with concise,
  mostly gameplay-focused summaries of what distinguishes each Army. The summaries are maintained
  as validated editorial copy keyed by public Army slug, informed by current Army/rules data and
  secondary faction background without becoming game semantics.
- [x] **Documentation + Web frontend:** Explain main armies versus Sectorials on `/armies`. The UI
  identifies main armies with the rules' **Generic Army List** terminology, summarizes the official
  roster/AVA distinction, and presents richer Sectorial Fireteam charts as an observation of the
  current N5 Army data rather than a universal rules guarantee.
- [x] **Web frontend + Web backend:** Replace verbose browser share-state query strings with one
  scoped, versioned `s=v1.<scope>.<payload>` token. The payload uses deterministic base64url over
  a compact field-indexed UTF-8 payload so links remain self-contained and synchronous to encode
  and decode. General compression was not justified for the small state payloads, and server-side
  hash/lookup state was rejected because it would make durable links depend on stored server data.
  Unit Explorer, Unit Army targeting, Fireteams, catalog search, global search, and Glossary search
  now use the shared
  token contract. Legacy explicit query parameters remain accepted and are canonicalized to the new
  form; API query parameters are unchanged.
- [x] **Documentation:** Rewrite the Unreleased changelog as concise, user/operator-facing release
  notes and retrospectively audit the recent release history for the same problem. The cleanup now
  covers 0.6.1 through 0.8.1; 0.6.0 and older entries were already concise and were left intact.

## 0.10.0 — consistency, presentation, and release hardening

0.10.0 is the stabilization pass before 1.0: audit the completed application model end
to end, finish the frontend/theme architecture, and harden release/operations workflows.
It should avoid introducing another major game-data domain; correctness fixes discovered
by the audit remain in scope.

### End-to-end application consistency

- [ ] Perform a systematic end-to-end consistency audit after the canonical-model
  groundwork above is sufficiently established. This remains an audit and bounded
  correctness-fix effort rather than a visual redesign or broad frontend
  restructuring project.
  - [ ] Establish one pinned production audit baseline before inspecting behavior:
    the Git commit, tracked `infinity.db` and `rules.db`, tracked release-matched symbol
    publication manifest, and the local raw/provenance evidence used to build them.
    Verify that the runtime database and symbol publication derive from the same Army
    snapshot. Keep raw/local evidence under
    the gitignored `docs/audits/` workspace, then promote durable conclusions and
    release-closeout decisions into a
    tracked audit document under `docs/`; do not mix production observations with
    synthetic test fixtures.
  - [ ] Create and maintain an explicit audit matrix for each concept, recording
    its semantic-provenance category, source meaning/evidence, storage
    representation, derivation or canonical/application interpretation, API
    representation, browser consumers, canonical documentation location, existing
    coverage, and audit result. Cover logical/source unit identity; army hierarchy, role,
    and playability; faction/display identity; optional availability;
    names/slugs; profiles and loadouts; catalog/rules enrichment; distance/range
    semantics; symbols; source/wiki/rules provenance;
    filtering/search/sorting/counts; and deep-link identifiers.
  - [ ] Begin with the army/unit identity and availability vertical slice. Trace
    `main_army_id` and `display_army_id`, faction grouping, role/playability,
    mercenary and reinforcement availability, logical identity, and their unit
    explorer/detail consumers from storage through the API to the browser.
  - [ ] Audit the backend and API contracts before browser presentation. Trace
    generated database rows through the canonical/application model, repository
    queries, and application-level composition (including `SkillCatalog`,
    `TraitCatalog`, and `CatalogRules`) to the JSON API. Add focused contract
    coverage wherever intentional behavior is not sufficiently pinned.
  - [ ] Audit browser semantic ownership. Inventory domain interpretation in
    browser modules, beginning with `unit.js`, the army selector, catalog detail
    modules, symbol lookup, rules links, and optional-unit filtering. Keep display
    formatting in JavaScript, but expose game/data semantics through the backend
    API when duplicate interpretation could disagree. Route JSON API access
    through `api.js` to match the documented boundary; static/HTML fetches are not
    part of that API-transport requirement.
  - [ ] Perform route-by-route parity checks for the Unit explorer and details;
    landing/About; Fireteams; Skill Modifiers; Skills, Equipment, Weapons, Traits,
    States, and Hacking Programs list/detail pages; shared navigation/settings; and
    version refresh. Compare API output with
    rendered behavior, including filtering, result counts, ordering, labels,
    deep-link state, cross-links, optional-unit behavior, source/rules links,
    catalog-item Unit usage where applicable, and symbol identity. Use a deliberate manual browser
    pass unless lightweight browser automation is added for a concrete audit need.
  - [x] Verify Fireteam source retention through the canonical application projection
    and first-class repository/API/browser chart surface. Keep the broader consistency
    audit responsible for route/API/render parity rather than reopening Fireteam domain
    modeling that is already tracked in the 0.8 connected-data workstream.
  - [ ] Exercise degraded states deliberately: rules database available versus
    unavailable; asset validation disabled versus required; complete tracked published
    assets versus an intentionally asset-free specialized package/test layout; unknown
    unit/catalog/trait IDs; empty search
    or filter results; invalid query parameters; missing catalog enrichment;
    stale version/snapshot detection; and database/symbol snapshot mismatch.
  - [ ] Verify the supported validation/runtime contexts independently: a normal
    source checkout with the tracked processed publication, a specialized package/test
    layout where the third-party SVG tree is deliberately absent and asset checks are
    disabled or allowed to fall back, local development with explicitly supplied
    generated runtime artifacts, and production deployment that fails closed for
    incomplete or mismatched databases/assets. Passing one context does not establish
    the others.
  - [ ] Fix discovered inconsistencies incrementally and add focused regression
    coverage where practical. Record intentional deferrals in the audit document
    and TODO rather than silently leaving them unresolved. Keep CI hardening,
    unrelated storage experiments, the Changes page, visual theming, and broader
    UI restructuring outside this audit unless required for a minimal correctness
    or 1.0-completeness fix.
  - [ ] Close with a second source-to-storage-to-browser matrix pass, complete
    normal project checks, and full-asset validation against the pinned production
    publication when it is available. Update canonical documentation, `TODO.md`,
    and `CHANGELOG.md` for material findings before closing the audit; feed any
    resulting corrections into the remaining frontend-architecture or theming work.

### Frontend architecture and theming

- [ ] **Web frontend + Project infrastructure:** Add a user-facing **Changes** page backed by
  `docs/CHANGELOG.md`, which remains the canonical release-history source. Present current and
  historical release notes in the browser without maintaining a second hand-edited copy of the
  same content.

- [ ] Refactor the web layer toward the documented backend/frontend responsibility
  boundary without changing the current same-origin deployment model.
  - [x] Split API handling, shared page-shell/static delivery, and top-level request
    dispatch into visibly separate Python concerns while preserving existing URLs. The WSGI
    composition/instrumentation layer now delegates browser/static delivery to
    `web/presentation.py` and JSON/domain handling to `web/api_handler.py`, with shared route
    identities and response values kept separate from both.
  - [ ] Organize browser code around explicit API transport, preferences/theme
    state, reusable view/components, and page modules; keep JSON API access routed
    through `api.js`.
  - [ ] Add focused contract/regression coverage as responsibilities move so domain
    interpretation cannot silently migrate back into browser code.
    - [x] Pin Python route ownership so presentation handling does not absorb `/api/*` and API
      handling does not absorb browser pages, and keep packaged-symbol tests coupled to the
      presentation concern rather than top-level WSGI dispatch.
    - [ ] Add browser/backend semantic-boundary coverage while moving remaining inferred domain
      labels/symbol roles out of page modules.

- [ ] Implement first-class theme selection using the semantic theme contract documented in
  `docs/architecture.md`, with Light and Dark as the initial themes rather than an architectural
  limit.
  - [ ] Separate semantic theme tokens from theme-neutral layout/component rules
    and remove remaining hard-coded light-theme assumptions.
  - [ ] Decide and document the default startup behavior (for example, operating-
    system preference versus a fixed project default); an explicit user choice wins.
  - [ ] Add a theme selector to Settings that is data-driven rather than hard-coded as a binary
    Light/Dark switch, resolve the selected theme before first meaningful paint, and keep
    persistence on the existing preference contract so additional themes can be added without new
    state logic.
  - [ ] Audit contrast and distinguishability for status/range colors, links, focus,
    muted text, tables, dialogs, menus, and faction accents in every shipped theme
    (initially Light and Dark).
  - [ ] Add regression coverage for initialization, switching, persistence, and
    representative core pages across every shipped theme.

- [ ] Add a project favicon derived from `infinitydb-logo.svg` and keep it legible
  in light and dark browser chrome where practical.

- [ ] Reorganize frontend design-system ownership after first-class themes are implemented:
  keep foundational tokens, per-theme values, shared components/layout, and page-specific
  exceptions visibly separate where that improves maintenance, without adding a CSS build step
  or reworking the shared visual primitives that are already established.

### Release hardening, CI, and operations

- [ ] Define a paired-export replacement policy. The application and raw archive
  are currently built as temporary siblings; document and test recovery when a
  process stops between replacing either output.

- [ ] Integrate curated snapshot-note validation into routine project checks so
  every checked-in file under `data/curated/snapshot-notes/` is validated even
  when no downloader or comparison workflow happens to load it.

- [ ] Retain release evidence for the configured hosted workflows. Before
  claiming a release has passed hosted CI, record successful `Source checks`,
  `Installed wheel smoke`, and `Deployment smoke test` runs for the release
  commit or tag.

- [ ] Complete optional/manual full-asset CI administration by adding authorized
  `FULL_ASSET_BUNDLE_URL` and `FULL_ASSET_BUNDLE_SHA256` secrets to the existing
  `full-assets` environment, then record one successful manual run.

- [ ] Establish privacy-preserving production monitoring and a repeatable capacity test
  for the Docker deployment.
  - [ ] Record host and container CPU, memory, swap, disk-space/inode, disk-I/O,
    and network utilization; retain Docker restart/OOM events and sanitized Caddy/Gunicorn
    error diagnostics. Alert on sustained CPU saturation, memory pressure or OOM kills,
    low disk space, elevated 5xx responses, and failed health checks.
  - [x] Publish aggregate request counters/histograms using normalized bounded route
    labels: request rate, status class, latency, response size, and active requests. Static
    assets and `/api/` requests remain separately identifiable for future dashboards.
  - [x] Do not collect IP/geolocation, user-agent/fingerprint, referrer, cookie/session/
    preference values, query/search terms, persistent visitor IDs, unique/returning-user
    analytics, or per-user navigation histories. Raw URLs and unbounded request values are
    excluded from metric labels.
  - [x] Disable the routine Gunicorn access-log stream while retaining stderr error logs.
    If raw request logging is temporarily required for a concrete incident, minimize/sanitize
    its fields, restrict access, and define short retention before enabling it.
  - [ ] Define a representative load-test scenario: browse the unit list, search,
    open unit/catalog details, and fetch API endpoints using a current
    production-like SQLite snapshot. Include a warm-cache steady-state run and
    a short burst run; do not benchmark only the health endpoint.
  - [ ] Establish a baseline at 2 Gunicorn workers x 4 threads, then test 4 x 4
    only with a matching 4-vCPU/4-GiB container allocation. Record p50/p95/p99
    latency, request/error rate, CPU, memory, and SQLite/disk behavior at each
    concurrency level.
  - [ ] Set an explicit scale trigger (for example, a sustained p95 latency or
    error-rate SLO breach while CPU is not otherwise constrained). Prefer
    multiple immutable app replicas behind Caddy over unbounded worker growth;
    re-run the test before changing worker counts or deployment resources.

- [ ] Add a benchmark/health-check command that validates the application database,
  confirms its expected raw archive when requested, and reports schema and
  compatibility revisions.

## 1.0.0 — current-reference completeness gate

1.0.0 is the final completeness release for the supported current reference data. It
should resolve remaining material source/rules gaps and validate the whole application;
it should not introduce a large new product surface.

### Rules and reference completeness

- [ ] **Data processing + Web backend + Web frontend:** Close the remaining versioned
  curated rules-reference gaps for N5 v5.3 using
  `data/pdf/rules/n5-rules-v5-3-en.pdf` (dated 2026-08-10) and other explicitly scoped
  current reference sources.
  - [ ] Expand remaining canonical rule identities across Skills, Equipment,
    Ammunition, Traits, States, Fireteam concepts, glossary terms, and other useful
    rule domains, retaining rulebook version and printed-page citation. Do not
    recreate Hacking Program facts already promoted by the 0.8 connected-data work.
  - [ ] Generate an Orders/AROs declaration matrix from the reconciled cross-domain
    relationships and use it as a completeness check for missing, invalid, or
    contradictory declaration categories rather than maintaining a second hard-coded
    chart. Make the projection source/scope-aware so scenario-only Skills/AROs can be
    represented without appearing in the core N5 matrix or being flagged as missing
    core categories.
  - [ ] Model Ammunition rules as first-class cited identities and relationships.
    Distinguish the eleven base Ammunition types from source-defined combined
    forms, preserve component relationships for combined Ammunition, and keep
    Ammunition composition separate from Combined Saving Roll notation. Link
    state/Attribute/Saving-Roll effects explicitly instead of deriving them from
    Ammunition display names.
  - [ ] Include scenario-defined catalog concepts needed for the general rules
    reference, including scenario-only Skills, Equipment when present, contextual
    roles such as Specialist Troop, and the scenario elements those concepts act
    on. Preserve scenario/season scope and keep temporary effects out of static
    Unit/Profile facts. Include the scoped action identities surfaced by the
    current ITS FAQ where their owning scenarios classify them as Skills/AROs,
    including `Activate Communication Antenna`, `Oppose Activation`, and `Emit
    Akial Interference`. Keep semantic identity, source publication provenance, and
    applicability separate so the same canonical concept can be cited or overlaid
    by core, scenario, FAQ, or season material without duplication or collection-
    load-order semantics. This catalog coverage is in scope for 1.0; a complete
    scenario library and scenario list/detail pages are not.
  - [ ] Add the official Reinforcements Extra as a separately versioned/scoped
    annex source rather than folding it into `n5-core-rules`. Curate `Commlink`
    and `Request Reinforcements`, link the capability they create to the annex
    scope, and retain the ordinary-Army -> Reinforcement Section/pool context.
    - [ ] Encode `Commlink (+X)` as a typed maximum-Trooper-count parameter, not a
      Skill Level or Attribute MOD.
    - [ ] Extend declaration-category validation so phase-scoped actions such as
      `Request Reinforcements` can be explicitly classified outside Basic Short/
      Short/Long/ARO instead of being treated as incomplete or assigned a false
      category.

- [ ] Add a dated FAQ/errata layer to the existing rules-reference system from
  current material under `data/pdf/faq/`.
  - [ ] Model each ruling as a question, concise answer, rule/topic links,
    applicable scope, document version/date, and source-page citation; do not
    flatten it into the base-rule summary. This preserves the distinction
    between a rule and a later clarification, and permits an answer to be
    superseded cleanly.
    - [ ] Give each ruling a canonical identity independent of wiki page
      placement. Store the original FAQ publication version/date separately from
      current rules/ITS-season/scenario applicability so cross-posted or
      carried-forward rulings are linked rather than duplicated.
  - [ ] Prioritize links to features already represented by the app: deployment
    and private-information handling; BS Attack/MOD and template behavior;
    hacking Firewall; Marker, Camouflage, Peripheral, and State interactions;
    Coordinated Orders; and Fireteam creation/bonuses/integrity. The FAQ also
    contains scenario-specific rulings, so scope them to the relevant ITS
    season and mission rather than presenting them as universal core rules.
  - [ ] Define an explicit source-precedence and effective-date policy. An on-screen
    answer must show its source date/version and never silently blend conflicting
    documents.

- [ ] **Data processing + Web backend + Web frontend:** Extend generated rules-reference
  projections that build on the enriched canonical data rather than duplicating its facts.
  - [ ] Add richer typed/cross-linked projections for the structured Martial Arts,
    Booty, and MetaChemistry reference rows now served in 0.7.0. Keep random outcomes
    as deployment/session overlays, preserve conditional branches (for example TAG
    versus other Troop Types), and cross-link resolvable outcomes to canonical Skills,
    Equipment, Weapons, and Attributes without rewriting Unit profiles.
  - [ ] Add a generated cross-army rule-variant usage index once exact variant
    semantics are reconciled: canonical Skill/Equipment -> Level/MOD/typed parameter
    variant -> Unit/profile/loadout occurrences. Derive it from canonical rules and
    Army occurrence relationships rather than maintaining a second classification.
  - [ ] Model the finite V5.3 Restrictions Chart as explicit cross-domain
    relationships (Troop Type/Training/Equipment/Skill -> restricted action or
    Lieutenant eligibility) and expose it as contextual help/generated reference.
    Do not generalize this into a full live-game action-legality engine.

- [ ] Extend the completed Game States reference catalog with any remaining contextual
  state links needed by later Fireteam, Hacking, weapon/ammunition, and scenario guidance;
  do not infer a Unit's current in-game State from its static Army profile.

- [ ] Add a weapon-and-ammunition quick-reference view built from existing
  weapon profiles plus curated rules data.
  - [ ] Normalize display of multi-mode/multi-ammunition profiles, link ammunition
    names and traits to their effects, and provide a unit-neutral
    comparison/filter view. Preserve the field-specific meaning of `+`: Ammunition
    composition and Combined Saving Rolls are separate rules operations. Validate
    the view against Army metadata; do not copy source charts wholesale into the
    application.
  - [ ] Add a generated Deployables profile reference from Weapon/Equipment
    metadata plus curated corrections: ARM/BTS/STR/S for the deployed object,
    originating item/rule, and reverse Unit/loadout uses. Keep deployed-object
    identity separate from the carrier and from catalog domain. Track the V5.3
    Armed Turret S2 detailed-profile versus S1 quick-reference conflict explicitly
    and do not silently choose the summary value without reviewed precedence.

- [ ] Add a curated Infinity Wiki URL mapping for traits when authoritative
  links are available.

### Final 1.0 acceptance

- [ ] **Data processing + Web backend + Web frontend + Project infrastructure:**
  Execute the final 1.0 source-to-storage-to-browser completeness gate defined by
  `docs/releasing.md` against pinned current Army, rules, wiki, database, and symbol
  inputs. Resolve every material in-scope gap or document an explicit exclusion with
  rationale, then complete normal project checks, hosted release checks, and
  full-asset validation before tagging 1.0.0.

## Post-1.0 — maintenance and product expansion

These items are intentionally outside the 1.0 completeness gate. They may move earlier
only when required to fix correctness, reproducibility, or release reliability.

### List and session configuration

- [ ] **Data processing + Web backend + Web frontend:** Model Spec-Ops/Team-Ops
  `spectables` as structured configurable list/session data, preserving the distinction
  between a Unit's base reference profile, a player's selected upgrades, and later
  in-game profile transitions. Do not attach selected choices to the replaceable Army
  snapshot or present the complete chart as immutable Unit detail.

- [ ] **Data processing + Web backend + Web frontend:** Revisit loadout `disabled` and
  `minis` only when a reviewed source contract or roster-builder use establishes their
  player-facing meaning. Until then retain the source values without inferring either
  current availability or a miniature-count rule.

### Routing and long-term compatibility

- [ ] Before retiring or redirecting numeric routes, define and implement the
  per-domain slug-freezing, reviewed-override, alias/redirect, and canonical-URL
  compatibility policy documented as future work in `docs/architecture.md`.

### Performance, storage, and build tooling

- [ ] Benchmark cold and warm requests per worker for unit lists, unit details,
  skills, equipment, and weapons. Record median and p95 timings against a
  representative snapshot before and after each performance change.

- [ ] Evaluate SQLite `immutable=1` for deployed snapshots. Enable it only when
  the process never observes an in-place database replacement.

- [ ] Compare otherwise equivalent deployment variants backed by SQLite and by
  `normalized.json`, with both variants exposing the same API and representative
  load scenario. Define the JSON variant's startup parsing, indexing, and caching
  semantics before interpreting performance results so the comparison measures
  runtime data models rather than repeated JSON parsing. Evaluate both request
  performance and deployment portability/multi-platform suitability before
  deciding whether a storage/query abstraction is justified.

- [ ] Establish a reproducible build/export performance baseline on CI or a
  fixed development host. A 2026-09-14 generated-snapshot smoke export measured
  8.45 seconds, 13.4 MB for the application DB, and 37.7 MB for the raw archive;
  treat those numbers as provisional until repeated in a controlled environment.

- [ ] Remove redundant whole-document work in the combined build/export path.
  Export validation serializes the complete normalized object to reject invalid
  JSON, while the raw archive serializes every row again and normalization has
  already run `validate_normalized`. Consider a hash-attested validation report
  or an in-memory hand-off that skips only the duplicate build-path pass; the
  standalone `export` command must retain full untrusted-input validation.

- [ ] Evaluate artifact-level deduplication for development builds. The raw
  archive contains 24.9 MB of row JSON, nearly the 25.2 MB normalized input,
  so retaining `normalized.json` and `infinity.raw.db` duplicates the same
  lossless data. Decide whether post-export development workflows need both,
  or document one as a regenerable/transient artifact.

- [ ] Provide a small development CLI for `infinity.raw.db`: inspect a raw row,
  list raw rows by normalized table, and verify that an archive matches its
  application sibling's metadata.

- [ ] Add database-size reporting to `infinity-db build` so snapshot growth is
  visible in build output and CI.

### Army snapshot and symbol-pipeline maintenance

Milestone 1 acceptance for the integrated pipeline is complete. The remaining work is
maintenance, refactoring, richer diagnostics, incremental performance, and broader
portability coverage rather than a prerequisite for the 1.0 application-data gate.

- [ ] Let future snapshot-comparison tooling write structured generated diff
  data/reports under manifest/report paths while curated snapshot notes remain
  the human interpretation of those results.

- [ ] Refactor stage scripts into thin CLIs over reusable Python functions and a
  small shared symbol-pipeline utility layer.
  - [ ] Make the symbol-downloader input contract match its CLI and tests. Prefer
    the immutable raw Army ZIP as the authoritative input; either fully support
    directory/current merged-master inputs end to end or stop advertising them.
    In particular, do not claim legacy/current `master.json` compatibility unless
    discovery can consume that schema without treating ordinary embedded SVG
    references as unknown fields.
  - [ ] `svg_processor.py`: keep font audit, alias normalization, complete-set
    duplicate detection, deterministic representative ranking, persistent
    Inkscape conversion, and reports. Duplicate/canonical and text-conversion
    state are integrated into the build manifest; multi-category processing
    beyond the current canonical flow remains.
  - [ ] `path_sanitization.py`: remain shared infrastructure for external/mirror
    naming; pipeline-generated asset names should use one host-independent
    policy.
  - [ ] Longer-term reusable modules may be split into `snapshot`, `discovery`,
    `manifest`, `downloader`, `audit`, `deduplicate`, `convert`, `compress`, and
    `publish` helpers when that reduces duplication rather than adding ceremony.

- [ ] Make every integrated symbol stage idempotent and traceable before adding
  sophisticated incremental caching.
  - [ ] Changes to an override SHA-256 invalidate downstream processing for that
    asset. Removing an override falls back to validated symbol archives/cache or
    network by the normal resolution rules.
  - [ ] After the integrated build is stable, consider cache keys based on snapshot
    SHA-256, source SVG SHA-256, processor/tool versions, font-alias config,
    duplicate renderer/settings, conversion backend/settings, and compression
    profile/settings.

- [ ] Standardize symbol-pipeline reports around detailed machine/human outputs
  plus one concise build summary.
  - [ ] Preserve/report discovery counts, unknown SVG references, font audit,
    missing fonts, unused font declarations, SVG parse errors, duplicate groups,
    duplicate-render errors/separation/summary, text-to-path results/summary,
    compression report/candidates/run metadata, overrides used/unused, raw-cache
    hits, network downloads, manual static assets, canonical counts, published
    asset counts, application-mapping counts, and per-stage/total runtime.
  - [ ] Existing report filenames from the plan may be retained where useful:
    `symbol-discovery.csv`, `unknown-svg-references.csv`, `svg-font-report.csv`,
    `missing-fonts.csv`, `unused-font-declarations.csv`, `svg-parse-errors.csv`,
    `duplicate-groups.csv`, `duplicate-render-errors.csv`,
    `duplicate-separation.csv`, `duplicate-summary.csv`,
    `svg-text-to-path-report.csv`, `text-conversion-summary.csv`,
    `compression-report.csv`, `compression-candidates.csv`, and
    `compression-run.json`.

- [ ] Add focused end-to-end and cross-platform regression coverage for the
  integrated Army/symbol pipeline.
  - [ ] Snapshot/discovery tests: metadata/faction validation, complete archive,
    snapshot identity/hash, all profile/faction logos, multiple logos for one
    unit, one logo shared by units, duplicate URLs, static declarations,
    override suppression of network, override over cache, invalid/unused
    overrides, filename collisions, unexpected SVG fields, and proof that
    `resume` is not required for complete discovery.
  - [ ] SVG fixtures: exact duplicate, XML-different visual duplicate, no-text,
    normal text, alias-font, missing-font, empty-text cleanup, and troublesome
    real-world conversion cases.
  - [ ] Run core portability coverage on Windows, Ubuntu/Linux, and macOS when CI
    permits: project-relative path generation, path sanitization, executable
    discovery including `.exe`/`.cmd`, subprocess argument construction without
    shell quoting, temp files, case-only collisions, snapshot ZIP handling,
    override lookup, static-symbol manifest loading, atomic replacement, and
    Windows `spawn` compatibility. External-tool integration tests may be
    conditional when Inkscape, `resvg`, or SVGO are unavailable.
  - [ ] Add a shared utility layer for executable discovery, native/project-relative
    path conversion, atomic writes, subprocess invocation, and platform-neutral
    generated filenames before orchestration otherwise duplicates those rules.

### ITS, scenarios, and game tools

- [ ] Build a versioned ITS reference library from material under
  `data/pdf/its/` and `data/pdf/legacy/`, keeping the current season distinct
  from archived seasons.
  - [ ] Keep season content isolated by season and effective date. A user choosing
    a prior event must see its matching scenario, objectives, extras, and FAQ
    rulings rather than a mixture of seasons. Retain a curated, human-reviewed
    change log/diff rather than relying on raw PDF text diffing.
  - [ ] Treat the official Army app/site as the authority for army-list legality.
    InfinityDB may provide read-only explanation and planning support, but must
    label its snapshot/date and avoid claiming tournament validation.

- [ ] Add ITS scenario list and detail pages backed by a curated seasonal data
  model, rather than PDF excerpts.
  - [ ] Capture structured, cited scenario facts: objectives and scoring, game
    rounds/end conditions, force/point/SWC/table/deployment configuration,
    deployment map or geometry, exclusion zones, token types/diameters,
    classified-objective setup, reinforcement suitability, tactical-support
    options, and scenario-specific rules/elements.
  - [ ] Scenario pages should expose the selected season prominently and link
    season-specific terms to the relevant rules/state references.

- [ ] **Data processing + Web frontend:** Add a deployment-map SVG
  generator for scenario maps. The first iteration should accept a validated JSON map
  definition and generate deterministic SVGs for the three officially supported table-size
  presets: **24×32 in, 32×48 in, and 48×48 in**. Treat inches as the canonical geometry unit
  in the schema rather than rounding dimensions to nominal feet. Keep the renderer itself
  dimension-agnostic so historical, future, and scenario-specific formats do not require
  renderer changes.
  - [ ] Define a flexible coordinate/geometry model with absolute and relative anchors to
    table edges, center lines, other objects, and repeated/mirrored placements; allow
    per-table-size overrides where geometry genuinely differs rather than scaling blindly.
  - [ ] Support layered map primitives for Deployment Zones, Exclusion/Hazard/Scoring areas,
    center or dividing lines, rectangular and circular regions, access/opening lines, objective
    markers and scenery elements, labels, measurements, player-side/Attacker/Defender context,
    legends, and scenario-specific icons. Styling should support fills, opacity, strokes, hatching,
    symbols, and reusable semantic styles without baking one ITS season's artwork into the schema.
  - [ ] Research current and archived ITS scenario maps before freezing the schema. Cover examples
    with changing Deployment Zone depths, central Exclusion Zones, hazardous areas such as
    Biotechvore regions, exact Console/Server placements, asymmetric roles, and maps containing
    special access lines or scenario-specific objective markers. Preserve season/scenario source
    provenance for any definitions derived from official material.
  - [ ] Validate generated geometry and metadata deterministically: table bounds, dimensions,
    required references/anchors, stable element order/IDs, reproducible SVG bytes where practical,
    and readable output at print and screen sizes. Keep the JSON schema versioned so map
    definitions can evolve without silently changing old output.
  - [ ] Later, build a web-based editor/preview UI over the same schema and rendering engine rather
    than creating a separate browser-only map format.

- [ ] **Web backend + Web frontend:** Add an interactive Fireteam builder within a
  selected Army context. Build compositions from the canonical Fireteam projection and general
  Fireteam-rule facts rather than duplicating chart logic in the client.
  - [ ] Enforce Fireteam-local requirements and limits while composing a team: chart type,
    minimum/maximum counts, required choices, FTO eligibility, Wildcards, equivalence/alias
    semantics, and any other reviewed Army-local constraints represented by the canonical model.
  - [ ] Resolve the resulting Fireteam type and Level, then show the applicable bonuses from the
    same canonical Fireteam Level data used by the reference UI. Explain incomplete or invalid
    compositions in terms of the specific local requirement that is not satisfied.
  - [ ] Keep the tool narrower than a full Army-list legality engine. Unit availability and
    Fireteam composition must come from InfinityDB's maintained snapshot, while the official Army
    app/site remains authoritative for complete list legality.

- [ ] Add mission-aware list capability guidance once saved-list support exists.
  - [ ] Derive a transparent checklist from the selected ITS scenario and the
    imported profile data: ITS Specialist Troops, relevant equipment/skills,
    Reinforcement or Team-Ops constraints, and scenario interactions. Explain
    missing capabilities without declaring a list illegal or strategically
    inadequate.
  - [ ] Keep temporary scenario-granted skills, designated Troopers, classified
    cards, tactical support, and private information out of static unit
    profiles. They belong to a per-game/session layer, which is not yet part of
    InfinityDB's replaceable imported snapshot.

- [ ] Provide an optional ITS organizer/event companion only after
  user-authored persistent storage and migrations are established.
  - [ ] Support season-aware event setup: published scenarios, allowed extras,
    player count/round guidance, pairings, byes, score entry, and a printable
    control-sheet checklist. Do not infer an official ranking submission or
    replace the Online Tournament Manager.
  - [ ] Include setup aids from ITS documents while keeping organizer choices and
    local participant data clearly separate from official records.

- [ ] Add optional play-aid pages for core procedures, distinct from the unit
  database: order expenditure/ARO sequence, modifiers, movement/combat
  resolution, command tokens, and Fireteam quick reference. Use concise cited
  checklists rather than source excerpts.

### Native applications

- [ ] **Project infrastructure + Web frontend:** Evaluate adapting InfinityDB into
  native stand-alone Android and iOS applications. Compare BeeWare/Toga, Kivy, and other suitable
  Python-capable or cross-platform frameworks before committing to an implementation.
  - [ ] Evaluate candidates against InfinityDB-specific requirements: reuse of Python domain/data
    logic, local/offline SQLite snapshots and rules data, UI/navigation reuse versus rewrite,
    performance and startup cost, accessibility, platform-native integration, persistent storage,
    snapshot/update delivery, package size, signing/store distribution, and CI/release burden.
  - [ ] Build a small read-only proof of concept for at least one representative workflow (for
    example Unit or Fireteam browsing) before choosing a framework, and record which existing web
    assumptions would need to be separated into shared application services.
  - [ ] If a native-client direction is accepted, keep the canonical data/rules artifacts and
    semantics shared with the web application rather than creating a second interpretation layer;
    revisit the project-domain taxonomy if a permanent native-frontend domain becomes warranted.

### Persistent user data and broader product features

- [ ] Establish a migration policy for future persistent user-authored data;
  imported snapshots are intentionally replaced wholesale today.

- [ ] When a saved army-list builder is introduced, use the rules reference to
  add game-mode and list-review guidance—not hidden-information disclosure.
  Keep any share/export view privacy-aware and treat the Army app/data as
  authoritative for list legality.

- [ ] Create a unit-model image repository.

- [ ] Add a per-user model-collection tracker.

- [ ] Saved army lists, favourites, and personal notes stored separately from
  the replaceable imported snapshot.

- [ ] Unit comparison view for profiles, loadouts, weapons, skills, and
  equipment across selected units or armies.

- [ ] Army-list builder/export integration once user-authored data storage and
  migrations are established.

- [ ] Data-review screens in Developer mode: normalization warnings, source
  record links through `infinity.raw.db`, and unresolved placeholder records.

- [ ] Low priority: provide access to prior imported-data versions when JSON
  source files change. Existing archived JSON ZIP files and Army snapshots are
  sufficient for recovery until this is needed.

- [ ] Low priority: add a JSON-snapshot comparison page showing added, removed,
  and updated data between two snapshots.

- [ ] Low priority: optionally highlight added, removed, and updated data
  elsewhere in the application when comparing snapshots.
