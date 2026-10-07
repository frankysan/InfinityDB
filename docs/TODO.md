# InfinityDB backlog

This is the working implementation backlog. Every unchecked item belongs to exactly
one release bucket: **1.0.0** or **post-1.0**.
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

**Project domain:** Project infrastructure

Version **0.10.0** is released and deployed. The current implementation milestone is
**1.0.0 — current-reference completeness**, with implementation planning below.

General performance/storage experiments, major pipeline refactors,
persistent-user-data features, ITS season/tournament tooling, and native applications are explicitly
post-1.0 unless they become necessary to correct a release-blocking defect. Core-rules scenarios are
part of the 1.0 completeness target; their accepted architecture guides the 1.0 implementation.

The public roadmap summary lives in `README.md`; the durable 1.0 acceptance
definition lives in `docs/releasing.md`. The sections below contain the remaining implementation
and release work for 1.0 and later milestones. Completed substeps are retained only under an
open parent item.

## 1.0.0 — current-reference completeness gate

1.0.0 is the final completeness release for the supported current reference data. It
should resolve remaining material source/rules gaps, add the bounded core-scenario reference
surface, and validate the whole application without expanding into broader ITS/tournament tooling.

### Development sequence

**Project domains:** Data processing, Web backend, Web frontend, Project infrastructure

This is a proposed implementation sequence within the existing release scope, not a new
completeness definition. Use [the release gate](releasing.md#version-10-data-completeness-gate)
to decide whether a gap blocks 1.0. Do not wait until release preparation to discover missing
information or browser surfaces.

| Stage | Reviewable output | Dependencies |
| --- | --- | --- |
| 1. Inventory and scope | Pinned inputs, source-to-browser coverage inventory, prioritized gap batches | Existing Army/rules databases and audit tools |
| 2. Shared semantics | Scoped identity/clarification contracts, typed Ammunition and annex facts, scenario validation/export pilot | Inventory; reuse current contribution and relation contracts |
| 3. Complete vertical slices | Reviewed catalog batches, FAQ presentation, all four core scenarios | Relevant Stage 2 contract; each slice includes storage, API, and usable browser access |
| 4. Derived references | Declaration matrix, enriched lookup rows, variant usage, Restrictions, weapons and Deployables | Reviewed owning facts and exact variant/scope semantics |
| 5. Closeout | Reconciled completeness evidence and final release acceptance | Every in-scope gap resolved; canonical release checklist |

Stages may overlap where dependencies are satisfied. In particular, ordinary catalog curation can
continue while the scenario model is implemented, and projections need only their owning facts to
be ready. Keep model/export, curation, backend, and browser substeps visible under each open parent;
a populated JSON collection alone does not complete a player-facing task.

For each implementation slice, record the source/version being covered, remaining decisions,
affected canonical documents, and evidence needed to close it. Extend existing validators and
audit tools before introducing another coverage system. Keep generated evidence in ignored
`reports/` or `docs/audits/`; keep maintained semantic decisions in validated curated data or
configuration. Use [the standard checks](testing.md) for the affected contracts, and add manual
browser acceptance for new visual/interaction surfaces. Promote durable contracts to their
canonical owners as implementation lands; the planned scenario model must remain labelled as
unimplemented until its corresponding behavior exists.

### Source inventory and gap batches

- [ ] **Data processing + Project infrastructure:** Establish the 1.0 completeness baseline
  before expanding curation.
  - [ ] Pin the intended Army snapshot, rules/FAQ/annex PDF versions, and supported wiki evidence.
    Record archive/content hashes as appropriate, publication dates separately from acquisition
    dates, and the generated database/publication identities. A later source refresh reopens the
    affected coverage review; normal checks must not acquire newer inputs implicitly.
  - [ ] Inventory player-relevant information by source section/category, including the four core
    scenarios. For each category record its canonical identity/model, maintained input, generated
    storage, API/read path, ordinary browser entry point, rules context, and outstanding gap or
    justified exclusion. Distinguish missing facts, missing relationships, and missing presentation.
  - [ ] Reuse `audit_source_presentation.py`, `audit_enrichment_coverage.py`, and
    `audit_rules_interactions.py` as baseline evidence. Their existing Army/catalog coverage does
    not establish PDF, FAQ, or scenario completeness or prove browser usability; add the missing
    source review and presentation checks explicitly.
  - [ ] Reconcile `data/curated/rules-interactions/reviews.json` and `catalog-scope.json` with the
    pinned input set. Historical review/defer release labels are evidence, not the active roadmap:
    reassess pending items against the 1.0 gate and record explicit scope decisions rather than
    treating every deferred candidate as either automatically required or automatically excluded.
  - [ ] Turn confirmed gaps into bounded batches under the owning tasks below. Each batch names
    the concepts/source sections, dependency, missing contract or content, and completion evidence;
    material source conflicts need a reviewed decision before dependent presentation is closed.
  - **Completion:** every supported source/category has an explicit coverage disposition and every
    material in-scope gap has an owning open task. This establishes the baseline, not final acceptance.

### Rules and reference completeness

- [ ] **Data processing + Web backend + Web frontend:** Close the remaining versioned
  curated rules-reference gaps for N5 v5.3 using
  `data/pdf/rules/n5-rules-v5-3-en.pdf` (dated 2026-08-10) and other explicitly scoped
  current reference sources.
  - [ ] Plan curation batches from the inventory by missing semantic family or source section.
    Separate already-reviewed content from absent definitions, unresolved variants, missing typed
    relations, and facts that exist but cannot yet be reached in the normal browser experience.
    Reuse the current [curated contract](../data/curated/README.md#curated-rules-reference-data);
    extend closed fact/relation vocabularies with validation and presentation support before use.
  - [ ] Expand remaining canonical rule identities across Skills, Equipment,
    Ammunition, Traits, States, Fireteam concepts, glossary terms, and other useful
    rule domains, retaining rulebook version and printed-page citation. Do not
    duplicate Hacking Program facts already owned by the current Hacking Program
    domain.
  - [ ] Generate an Orders/AROs declaration matrix from the reconciled cross-domain
    relationships and use it as a completeness check for missing, invalid, or
    contradictory declaration categories rather than maintaining a second hard-coded
    chart. Make the projection source/scope-aware so scenario-only Skills/AROs can be
    represented without appearing in the core N5 matrix or being flagged as missing
    core categories.
    - [ ] Define projection rows and declaration/scope columns from the existing canonical
      declaration metadata; expose the owning rule links and cited exceptions. Choose a normal
      reference entry point rather than leaving the matrix as an audit-only output.
    - [ ] Validate the pinned core chart against the generated projection. Cover action-like
      Equipment and Hacking Programs, missing/contradictory categories, scenario-only actions,
      and phase-scoped exclusions without interpreting absence as permission or prohibition.
  - [ ] Deepen the existing first-class Ammunition model with explicit typed
    relationships. Preserve the eleven published base Ammunition identities, distinguish
    source-defined combined forms, preserve component relationships for Combined
    Ammunition, and keep Ammunition composition separate from Combined Saving Roll
    notation. Link State, Attribute, and Saving-Roll effects explicitly instead of
    deriving them from display names.
    - [ ] Review the fact/relation schema before curation: components, affected saving Attribute,
      roll/effect conditions, and State interactions need explicit ownership. Cover a base type,
      a combined form, and Combined Saving Roll notation in an end-to-end pilot.
    - [ ] Validate every published base identity and reviewed combined form against the pinned
      source; prove that weapon links, Ammunition detail, and later comparison views consume the
      same facts without conflating composition with roll notation.
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
    load-order semantics. This catalog coverage is in scope for 1.0 and should share
    identities/scope with the core-scenario model rather than becoming a parallel representation.
    - [ ] Reuse current scoped definitions/supplements, then identify any missing applicability
      validation or presentation contract using one concept shared by core and scenario material.
      Prove that scope is visible and unrelated scenario/season overlays do not leak into core help.
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
    - [ ] Deliver the annex as a bounded slice: validated collection/citations, typed parameter
      and declaration support, generated rules facts, and linked annex/Skill help from the existing
      Reinforcement Army context. Reuse reviewed Army parent/pool relationships.
    - [ ] Test ordinary versus Reinforcement context, exact `Commlink (+X)` variants, and explicit
      phase classification; do not infer roster legality or mutate the core declaration chart.
  - **Completion:** each covered batch builds into `rules.db`, passes maintained-text and
    interaction review, and is navigable with citations in normal mode. Use semantic maintained-text
    tokens; preserve genuine ambiguity with `review-needed` rather than weakening plain-text review.

- [ ] **Data processing + Web backend + Web frontend:** Add the current core-rules
  scenarios as a first-class, browsable scenario domain for 1.0, using the model derived
  from the 0.10.0 core/ITS comparison.
  - [ ] Implement a model/export pilot from
    [the accepted scenario model](data-model.md#planned-scenario-model-10). Start with one core
    scenario selected from the inventory, while checking the schema against the reviewed ITS
    variation evidence; do not require ITS content publication to validate extensibility.
    - [ ] Define versioned validated structures for identity, publication revision, collection
      membership, game-size configuration, sides, geometry, elements, scoring, scoped actions,
      optional features, and end conditions. Preserve ordered prose where a universal executable
      condition language would invent semantics.
    - [ ] Export relational identities/provenance/membership/reference indexes and validated
      component payloads to `rules.db`. Cover broken references, invalid dimensions/placements,
      distinct revisions of one identity, deterministic output, and unsupported formats. Update
      documented rules schema/compatibility and rebuild guidance if those contracts change.
  - [ ] Maintain structured, cited scenario data sufficient to understand setup, objectives,
    scoring, deployment, special rules/elements, and end conditions without relying on an
    unstructured PDF excerpt as the application model.
    - [ ] Curate **Annihilation, Domination, Supplies, and Firefight**, using N5 v5.3 printed
      pages 149–156 and the retained [scenario findings](rules-semantics.md#scenarios).
      Review every supported game-size row, objective/cap/timing, placement rule, special rule,
      and end condition. Link shared concepts to canonical catalog identities; retain source
      discrepancies and reviewed resolution instead of copying the nearest chart value.
  - [ ] Keep the model source/scope-aware and extensible to versioned ITS seasons, but do
    not make ITS scenario content, tournament/event tooling, or a deployment-map editor a
    1.0 requirement.
  - [ ] **Data processing + Web frontend:** Add the first version of the scenario-map SVG
    generator as part of the core-scenario 1.0 work. Its v1 schema only needs to represent the
    geometry required by **Annihilation, Domination, Supplies, and Firefight**; ITS scenario
    definitions and ITS-only geometry remain post-1.0.
    - [ ] Consume the same validated scenario geometry that backs scenario detail data. Do not
      maintain a second map-specific definition or recover geometry from source diagrams.
      - [x] Pilot this ownership boundary with **Domination**: its three N5.3 map configurations now
        live in the maintained `scenario:domination` curated record, validate through the typed
        scenario-definition layer, and can be rendered directly with `render-scenario-map` by
        scenario identity + Army Points. Remove the duplicate Domination geometry from test fixtures.
      - [x] Migrate **Supplies** to the same maintained-definition path. Its Supply Box placements
        and Deployment Zones now render from `scenario:supplies`; remove duplicate Supplies geometry
        from the acceptance fixture.
    - [x] Accept a versioned validated JSON geometry definition and generate deterministic SVG.
      Treat inches as the canonical geometry unit. Support the current **24×32 in, 32×48 in,
      and 48×48 in** table-size configurations while keeping the renderer dimension-agnostic.
    - [x] Implement the semantic primitives required by the four core scenarios: table-relative
      anchors, Deployment Zones and scoring/control rectangles, center/dividing lines, fixed
      objective/scenery point markers, labels, and reusable semantic styles. Keep semantic marker
      identity in geometry and resolve known marker types through canonical marker metadata rather
      than duplicating a radius on every element. Console is canonically 40 mm: N5.3 Domination
      indirectly makes that footprint rules-relevant by requiring a Console A Marker or scenery of
      the same diameter, while the ITS token table supplies the explicit numeric value. Supply Box is
      canonically 25 mm from the same token table. Prefer typed primitives over a general arbitrary
      SVG-path escape hatch.
    - [ ] Keep the schema deliberately extensible using the reviewed ITS evidence: do not bake in
      symmetric sides, one Deployment Zone per side, rectangular-only regions, fixed marker kinds,
      or one season's visual styling. Future schema versions must be able to add repeated/mirrored
      placements, circles/radius regions, Exclusion/Hazard areas, asymmetric roles, access lines,
      custom markers/icons, and per-configuration overrides without redefining the core concepts.
      Unsupported ITS-only constructs should fail explicitly rather than be approximated in v1.
    - [x] Add reference-based map measurements before freezing geometry v1. Keep annotations separate
      from semantic shapes: rectangle depth/width dimensions and area-size labels resolve their values
      from a target geometry element instead of duplicating numbers. Domination pilots rectangle
      dimensions and derived Quadrant sizes; Supplies adds point-to-table-edge distances derived from
      Supply Box coordinates, so its canonical 8-inch placements are never restated in annotation data.
    - [x] Validate table bounds, dimensions, stable element order/IDs, and reproducible SVG bytes.
      The maintained Domination and Supplies definitions plus deterministic acceptance fixtures for
      the remaining two core scenarios cover every distinct supported core table/deployment
      configuration. Replace each remaining fixture-only definition with curated geometry as that
      scenario is implemented.
    - [x] Provide a small development CLI for JSON -> SVG rendering so schema/renderer behavior can
      be tested independently of scenario-page presentation. A browser editor/preview remains
      post-1.0 and must use this same schema/rendering engine when added.
  - [ ] Provide usable scenario list/detail presentation and links to existing canonical
    rule/catalog entities where identities overlap.
    - [ ] Register scenario capabilities through the application-domain registry and define
      central slug/revision/collection resolution before adding API/browser consumers. Unknown
      identities or unsupported selections must have explicit not-found/invalid-input behavior;
      never silently substitute another season or revision.
    - [ ] Publish composed list/detail read models with clear source and selected configuration.
      Render setup, placement, objectives/scoring, special rules, and end conditions using shared
      browser structures. Decide discovery/search/Glossary participation explicitly in
      `docs/application-domains.md`; do not require every capability just to register the domain.
    - [ ] Make geometry understandable through structured placement descriptions/measurements and
      the core-scenario SVG renderer where useful. Generated diagrams must consume the scenario
      geometry rather than a second map definition. Reuse the common distance presentation contract;
      the interactive map editor and ITS-only rendering extensions remain post-1.0.
  - **Completion:** all four scenarios can be found and understood in normal mode for every
    supported configuration. Review scoring and placement against citations, follow related-rule
    links, and check keyboard/touch, narrow widths, Light/Dark themes, loading/empty/error behavior,
    direct navigation, and soft-navigation cleanup. No session state or live scoring engine is required.

- [ ] **Data processing + Web backend + Web frontend:** Add a dated FAQ/errata layer to the
  existing rules-reference system from current material under `data/pdf/faq/`.
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
    - [ ] Reuse the current definition/supplement boundary. Define the additional ruling identity,
      applicability, supersession, and source-selection fields needed by FAQ data before authoring
      batches; publication recency alone must not imply universal applicability. Record accepted
      semantics in the canonical data model and curated contract.
  - [ ] Deliver one core clarification and one scenario/season-scoped ruling through validation,
    export, repository/API composition, and browser presentation before curating the remaining
    inventory. Show linked questions/answers with dates and affected concepts alongside the base
    rule; choose a discoverable reference entry point without requiring a new top-level FAQ domain.
  - **Completion:** cover carried-forward/cross-posted rulings, supersession, conflicting sources,
    missing targets, and out-of-scope seasons. Every in-scope ruling is discoverable from its topic
    or scenario, and the reader can distinguish base rules from applicable clarifications.

- [ ] **Data processing + Web backend + Web frontend:** Extend generated rules-reference
  projections that build on the enriched canonical data rather than duplicating its facts.
  - [ ] Add richer typed/cross-linked projections for the existing structured Martial Arts,
    Booty, and MetaChemistry reference rows. Keep random outcomes
    as deployment/session overlays, preserve conditional branches (for example TAG
    versus other Troop Types), and cross-link resolvable outcomes to canonical Skills,
    Equipment, Weapons, and Attributes without rewriting Unit profiles.
    - [ ] Validate every published lookup row/range and conditional outcome against its cited
      source. Extend typed outcome support first, then render canonical links from the same rows;
      no random-result selection or persistent session overlay is required for 1.0.
  - [ ] Add a generated cross-army rule-variant usage index once exact variant
    semantics are reconciled: canonical Skill/Equipment -> Level/MOD/typed parameter
    variant -> Unit/profile/loadout occurrences. Derive it from canonical rules and
    Army occurrence relationships rather than maintaining a second classification.
    - [ ] Define the occurrence key and counting policy before aggregation so shared payloads,
      duplicate source Unit representations, and Army-specific variants do not inflate totals or
      lose context. Link results to the applicable Unit/profile/loadout and exact rule variant.
  - [ ] Model the finite V5.3 Restrictions Chart as explicit cross-domain
    relationships (Troop Type/Training/Equipment/Skill -> restricted action or
    Lieutenant eligibility) and expose it as contextual help/generated reference.
    Do not generalize this into a full live-game action-legality engine.
    - [ ] Reconcile every chart row and footnote with its owning fact/typed relationship, then
      test conditional restrictions, positive/negative cases, and scope. Present the condition and
      source; an absent restriction edge must not be presented as an affirmative legality result.
  - **Completion:** each projection has a normal browser entry point, source reconciliation, and
    regression coverage for its exceptional rows. Exact variant reconciliation gates the usage
    index; it need not block independently ready lookup or Restrictions views.

- [ ] **Data processing + Web backend + Web frontend:** Extend the completed Game States reference
  catalog with any remaining contextual state links needed by later Fireteam, Hacking,
  weapon/ammunition, and scenario guidance;
  do not infer a Unit's current in-game State from its static Army profile.
  - [ ] Drive additions from the coverage inventory and new typed Ammunition/scenario/FAQ facts.
    Author each relation once and verify derived navigation in both directions; distinguish entry,
    cancellation, immunity/override, and objective completion from the resulting State.
  - **Completion:** relevant context is linked from the owning rule and State help with applicable
    conditions/scope; no duplicate definitions or static assertions of a Trooper's live State.

- [ ] **Data processing + Web backend + Web frontend:** Add a weapon-and-ammunition quick-reference
  view built from existing weapon profiles plus curated rules data.
  - [ ] Normalize display of multi-mode/multi-ammunition profiles, link ammunition
    names and traits to their effects, and provide a unit-neutral
    comparison/filter view. Preserve the field-specific meaning of `+`: Ammunition
    composition and Combined Saving Rolls are separate rules operations. Validate
    the view against Army metadata; do not copy source charts wholesale into the
    application.
    - [ ] Define a unit-neutral read model and minimal comparison/filter controls using existing
      weapon identities/profiles and the enriched Ammunition model. Keep mode/profile identity,
      conditional values, range bands, damage/saving notation, Traits, and unavailable values
      explicit. Browser code renders these semantics rather than parsing display strings.
    - [ ] Reconcile representative single/multi-mode, combined-ammunition, Combined Saving Roll,
      and conditional/sentinel profiles through storage, API, and browser output. Verify the
      complete published profile set against the inventory, not only representative examples.
  - [ ] Add a generated Deployables profile reference from Weapon/Equipment
    metadata plus curated corrections: ARM/BTS/STR/S for the deployed object,
    originating item/rule, and reverse Unit/loadout uses. Keep deployed-object
    identity separate from the carrier and from catalog domain. Track the V5.3
    Armed Turret S2 detailed-profile versus S1 quick-reference conflict explicitly
    and do not silently choose the summary value without reviewed precedence.
    - [ ] Inventory deployed objects independently of their carriers. Reuse existing
      `facts.specialProfile` support where it fits; extend validated metadata/corrections only for
      confirmed gaps. Resolve or visibly retain the Armed Turret discrepancy with both citations.
    - [ ] Expose deployed-object profiles and reverse uses through a usable reference entry point.
      Test objects supplied through Weapons and Equipment, shared objects/multiple carriers,
      missing/not-applicable values, and carrier-to-object navigation without inventing Unit identity.
  - **Completion:** players can compare weapon profiles and reach Ammunition/Traits and deployed
    object statistics without selecting a carrier first; reverse uses preserve Army/loadout context.

- [ ] **Data processing + Web backend + Web frontend:** Add a curated Infinity Wiki URL mapping
  for traits when authoritative links are available.
  - [ ] Inventory Traits with missing or ambiguous official targets and author validated maintained
    mappings, reusing existing source-link resolution where applicable. Keep renamed/alias labels
    separate from destination identity; do not generate URLs from display names or invent a page
    when only a heading exists.
  - **Completion:** mapped links reach the reviewed official page/heading from normal Trait help;
    unavailable mappings remain deliberate. Source-link checking is explicit research activity,
    while automated mapping/resolution tests remain offline.

### Final 1.0 acceptance

- [ ] **Data processing + Web backend + Web frontend + Project infrastructure:**
  Execute the final 1.0 source-to-storage-to-browser completeness gate defined by
  `docs/releasing.md` against pinned current Army, rules, wiki, database, and symbol
  inputs. Resolve every material in-scope gap or document an explicit exclusion with
  rationale, then complete normal project checks, hosted release checks, and
  full-asset validation before tagging 1.0.0.
  - [ ] Re-run the baseline inventory against the final pinned input set. Follow every in-scope
    category from source citation through maintained representation and generated storage to a
    usable normal browser surface; schema coverage, passing validators, and an API route alone
    are insufficient evidence. Re-review exclusions against the canonical completeness definition.
  - [ ] Close the 1.0 interaction-review target in the maintained ledger, regenerate the checklist,
    and require the following check to pass. Never edit the generated checklist manually:

    ```text
    python tools/audit_rules_interactions.py --check-output docs/rules-interaction-checklist.md --require-release 1.0.0
    ```

  - [ ] Reconcile cross-source conflicts and empty/unavailable/not-applicable values; retain cited
    uncertainty where appropriate and fix every defect that materially misrepresents in-scope data.
    Record evidence by category and source identity in ignored reports/audits rather than keeping
    completed release narrative in this backlog.
  - [ ] Run [the complete release checklist](releasing.md), including the mandatory whole-corpus
    documentation audit, rebuilt release-matched artifacts where needed, local/hosted checks for
    the final candidate, annotated-tag evidence, and deployed smoke/rollback acceptance where
    applicable. Capture new scenario/reference browser acceptance in `docs/testing.md` as those
    surfaces are implemented.

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

- [ ] Evaluate a v2 short share-link registry that assigns one compact identifier to each
  unique canonical share state, rather than trying to make every shared URL fully
  self-contained. Keep existing v1 links decodable for long-term compatibility.
  - [ ] Define canonicalization before identity assignment so semantically equivalent states
    deduplicate regardless of parameter order, explicit defaults, or other serialization
    differences. Store the canonical state/schema version behind the identifier rather than
    treating the literal incoming query string as identity.
  - [ ] Compare compact identifier strategies against expected scale and operational needs.
    Prefer a sequential integer encoded in a URL-safe high radix when minimum URL length is
    the primary goal; evaluate a collision-checked random 64-bit identifier if enumeration is
    undesirable, and a truncated content-derived hash only if deterministic decentralized
    identity provides a concrete benefit. Do not use conventional UUID text when a shorter
    representation provides the same required semantics.
  - [ ] Define the resolver route and lifecycle contract (for example `/s/<id>`), including
    lookup/not-found behavior, immutability, backup/restore, migrations, retention, abuse
    controls, and the persistence boundary outside replaceable application snapshots/containers.
    Existing published short links must remain stable across application and data upgrades.
  - [ ] Keep the registry representation independent of the public identifier. It may store a
    compact typed v2 payload rather than JSON if that reduces storage and also supports a
    self-contained v2 encoding; measure both approaches before committing to one.
  - [ ] Benchmark complete URL length for representative simple and complex Unit Explorer,
    catalog, and global-search states against v1, a compact self-contained v2 codec, and the
    registry design. Treat generic compression as an optional optimization only where it
    produces a measured win.

- [ ] Before retiring or redirecting numeric routes, define and implement a
  per-domain slug-freezing, reviewed-override, alias/redirect, and canonical-URL
  compatibility policy. Until then, preserve the current contract: canonical generated
  links prefer stable domain slugs while numeric routes remain accepted compatibility forms.

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
  fixed development host. Record the exact source snapshot, toolchain, generated artifact
  sizes, and timing methodology with each result instead of carrying provisional benchmark
  numbers in the backlog.

- [ ] Remove redundant whole-document work in the combined build/export path.
  Export validation serializes the complete normalized object to reject invalid
  JSON, while the raw archive serializes every row again and normalization has
  already run `validate_normalized`. Consider a hash-attested validation report
  or an in-memory hand-off that skips only the duplicate build-path pass; the
  standalone `export` command must retain full untrusted-input validation.

- [ ] Evaluate artifact-level deduplication for development builds. `normalized.json` and
  `infinity.raw.db` intentionally retain overlapping lossless source structure today; measure
  the duplication on a controlled build, then decide whether post-export workflows need both
  or whether one should be documented as a regenerable/transient artifact.

- [ ] Provide a small development CLI for `infinity.raw.db`: inspect a raw row,
  list raw rows by normalized table, and verify that an archive matches its
  application sibling's metadata.

- [ ] Add database-size reporting to `infinity-db build` so snapshot growth is
  visible in build output and CI.

### Army snapshot and symbol-pipeline maintenance

Remaining pipeline work covers maintenance, selective refactoring, richer diagnostics/performance
work, and external-tool portability. It is outside the 1.0 application-data gate. The implemented
pipeline and artifact lifecycle are described in [data guidance](../data/README.md).

- [ ] Let future snapshot-comparison tooling write structured generated diff
  data/reports under manifest/report paths while curated snapshot notes remain
  the human interpretation of those results.

- [ ] Refactor legacy/standalone stage CLIs around the integrated pipeline only where doing so
  removes duplicated contracts or platform handling.
  - [ ] Resolve the standalone symbol-downloader input mismatch. The maintained integrated build
    requires an immutable raw Army ZIP, while the downloader help still advertises discovery-only
    directory/master inputs that are not supported consistently end to end. Either implement that
    discovery-only contract deliberately or remove it from the CLI/documentation.
  - [ ] Consolidate shared executable discovery, native/project-relative path conversion, atomic
    writes, and subprocess invocation where conversion/compression/orchestration still duplicate
    those rules.
  - [ ] Split additional `snapshot`, `discovery`, `manifest`, `downloader`, `audit`, `deduplicate`,
    `convert`, `compress`, or `publish` helpers only when the split reduces duplication rather than
    adding ceremony.

- [ ] Evaluate content-addressed incremental reuse only after measuring the current full rebuild.
  If worthwhile, derive cache keys from the pinned snapshot/source SVG hashes plus processor/tool
  versions, font-alias configuration, duplicate-render settings, conversion settings, and
  compression profile/settings. Do not weaken the current manifest/hash validation or immutable
  raw-symbol snapshot boundary to gain incremental speed.

- [ ] Finish symbol-pipeline reporting for machine-to-machine comparison.
  - [x] Persist the detailed acquisition/source counts, SVG preflight, font audit, duplicate
    detection, text-conversion, compression, publication mapping/change data, override usage, and
    cache/network provenance while keeping the interactive console concise and the verbose build
    log complete.
  - [ ] Add one compact machine-readable build-summary artifact with per-stage and total runtime so
    repeated builds can be compared without scraping the verbose log or individual reports.
  - [ ] Add separate discovery/unknown-reference CSV outputs only if future audit tooling needs
    row-oriented data beyond the build manifest and current JSON/CSV stage reports.

- [ ] Extend the remaining regression and portability coverage for the integrated Army/symbol
  pipeline.
  - [x] Cover pinned snapshot/provenance validation, complete Unit/profile/faction discovery,
    multiple/shared/duplicate URLs, static declarations, category-safe filename collisions,
    override precedence and upstream-equivalent propagation, conflicting/invalid/unused overrides,
    validated cache reuse, refresh behavior, and unavailable-source handling.
  - [x] Cover verified materialization/resume behavior, persisted failed audits, exact-first visual
    deduplication and deterministic representative ranking, text-conversion failure preservation,
    compression/report binding, publication collision detection, removed-symbol backups, and
    transactional publication rollback.
  - [x] Cover semantic publication cases for Unit/Profile fallback, distinct General-profile
    artwork, Reinforcement aliases, Peripheral-only and mixed-role identities, contextual
    Peripheral variants, parent-Unit artwork reuse, and cross-Unit profile-symbol consensus.
  - [ ] Add explicit fixtures for empty-text cleanup and a small set of troublesome real-world SVG
    conversion cases that should remain stable across tool upgrades.
  - [ ] **Acquisition:** Extend native external-tool integration coverage across Windows, Ubuntu/Linux, and macOS,
    especially executable discovery (`.exe`/`.cmd`), subprocess arguments, and real
    Inkscape/`resvg`/SVGO invocation. Hermetic source/pipeline coverage already runs across all three
    operating systems in required CI; external-tool tests may remain conditional when those
    executables are unavailable.

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

- [ ] Extend the 1.0 scenario domain with ITS scenario list/detail coverage backed by
  curated seasonal data, rather than creating a separate ITS-only model or using PDF excerpts.
  - [ ] Capture structured, cited scenario facts: objectives and scoring, game
    rounds/end conditions, force/point/SWC/table/deployment configuration,
    deployment map or geometry, exclusion zones, token types/diameters,
    classified-objective setup, reinforcement suitability, tactical-support
    options, and scenario-specific rules/elements.
  - [ ] Scenario pages should expose the selected season prominently and link
    season-specific terms to the relevant rules/state references.

- [ ] **Data processing + Web frontend:** Extend the 1.0 core-scenario SVG renderer for ITS
  geometry after the seasonal scenario data is curated. Reuse the same versioned geometry model and
  rendering engine rather than creating an ITS-only map format.
  - [ ] Add ITS-required geometry only when supported by curated scenario evidence, including
    repeated/mirrored placements, circular/radius regions, Exclusion/Hazard/Scoring areas,
    asymmetric roles, access/opening lines, scenario-specific markers/icons, and genuine
    per-table-size overrides rather than blind scaling.
  - [ ] Preserve season/scenario source provenance and add compatibility fixtures from current and
    archived ITS material before promoting new geometry features into the schema contract.
  - [ ] Build a web-based editor/preview UI over the same schema and rendering engine rather than
    creating a separate browser-only map format.

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
