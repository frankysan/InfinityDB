# Application domains

**Project domains:** Data processing, Web backend, Web frontend

This document defines the **current application-domain structure** used to organize InfinityDB's
player-facing game/reference information. Application domains are distinct from the engineering
ownership labels in `docs/project-domains.md`.

The goal is to give canonical concepts a stable home without forcing every concept type into the
same UI. Data identity, semantic ownership, search/glossary participation, and browser presentation
are related concerns, but they are not the same concern.

The capability registry described below is **Current** in
`src/infinity_db/application_domains.py`. Ammunition, Labels, and General Rules are published
catalog domains, Armies is a published overview domain, Fireteams follows the shared landing/scoped
interaction contract, and Attributes plus scoped Game terms are published embedded vocabularies
projected through contextual help, global search, and the federated Glossary.
Concrete unfinished work remains in `docs/TODO.md`.

## Principles

1. **One canonical owner.** A concept should have one semantic home. Cross-links, glossary entries,
   tooltips, search results, and alternate views reuse that identity rather than duplicating the
   definition.
2. **Presentation follows usefulness.** A typed identity does not imply a catalog page or individual
   detail route. The UI exists only when it helps a player browse or understand the data.
3. **Domains expose capabilities, not one mandatory template.** A domain may provide a catalog,
   overview, scoped view, detail pages, glossary/search participation, navigation, or only embedded
   semantics.
4. **Cross-domain views do not become owners.** Glossary and global search index canonical concepts;
   they do not maintain competing definitions.
5. **Prefer a natural domain over the catch-all.** General Rules is the deliberate fallback for
   rules/reference concepts with no clearer owner. It must not become a miscellaneous bucket for
   concepts that already belong elsewhere.
6. **Stable identity is separate from domain placement.** Existing typed IDs may remain stable when
   presentation/ownership is clarified. Moving Fireteam reference material into the Fireteams
   domain, for example, does not require renaming a stable `rule:*` identity solely to
   match a route.
7. **Scaffold before exhaustive population.** InfinityDB may establish a domain and its contracts
   before every current rules item has been modeled. Missing coverage remains explicit backlog work
   rather than a reason to delay the shared structure.

## Domain presentation vocabulary

InfinityDB uses three primary presentation levels.

### Top-level domains

Top-level domains have a player-facing landing surface and appear in the application's navigational
or discovery model when sufficiently populated. They may use different presentation modes:

- **Catalog:** a browsable collection, usually with filters/search and optional item detail pages.
- **Overview:** a domain landing page that summarizes or routes to useful content without requiring
  one detail page per item.
- **Scoped view:** a stable domain surface whose content changes when a meaningful scope is
  selected.

A domain can combine these modes. Fireteams, for example, use an overview landing state and an
army-scoped view rather than a conventional item catalog.

### Embedded vocabularies

Embedded vocabularies contain canonical typed concepts that are useful for semantic links, tooltips,
glossary entries, filtering, or search, but do not warrant their own catalog/detail browser.

**Current.** Attributes and Game terms use this model. Canonical Attribute identities such as
`attribute:mov`, `attribute:bs`, and `attribute:wip` own reviewed definitions and can participate in
semantic relationships without creating `/attributes` or individual Attribute pages. Scoped
`term:*` identities cover source-native terminology such as Trooper, Marker, Token, Peripheral,
Victory Points, Null State, and Alignment terms. Each Game term carries a reviewed semantic scope
(for example `game-element`, `alignment`, or `scoring`) so a surface name such as Marker or Hostile
can coexist with a Label or Trait of the same name without merging identities. Neither vocabulary
has a standalone catalog/detail hierarchy; both project through Glossary/search, while Attributes
also participate in contextual Unit-profile help/tooltips.

Other finite vocabularies may use the same model when a player-facing catalog would add little
value. Do not promote a vocabulary to a top-level domain merely because it has typed identities.

### Cross-domain views

**Glossary** and **global search** are projections across canonical concepts rather than application
domains of their own.

- Search returns concepts from their owning domains and identifies that domain in the result.
- Glossary provides a terminology-oriented view across both top-level domains and embedded
  vocabularies.
- A glossary entry backed by a browsable concept links to that concept's normal detail surface.
- An embedded concept can present its definition/context directly in Glossary or a tooltip without
  inventing an otherwise-useless detail route.

This keeps the glossary useful without creating a second source of truth for rules text.

## Current top-level domain set

The current published top-level domain set is:

- **Armies** (`armies`) — overview/navigation domain.
- **Units** (`units`) — Unit Explorer plus Unit detail.
- **Skills** (`skills`) — catalog plus detail.
- **Equipment** (`equipment`) — catalog plus detail.
- **Weapons** (`weapons`) — catalog plus detail.
- **Ammunition** (`ammunition`) — rules/reference catalog plus detail.
- **Traits** (`traits`) — catalog plus detail.
- **States** (`states`) — catalog plus detail.
- **Hacking Programs** (`hacking-programs`) — catalog plus detail.
- **Fireteams** (`fireteams`) — overview plus army-scoped reference/chart view.
- **Labels** (`labels`) — rules/reference catalog plus detail.
- **General Rules** (`rules`) — catch-all rules/reference domain for concepts without a clearer
  top-level owner.

The registry is intentionally capability-based: publication, navigation, search, Glossary, landing,
catalog/detail, and scoped-view behavior are independent flags rather than consequences of being a
top-level domain. Future evidence may justify another domain, but a new top-level domain requires a
concrete player-facing browsing/use case rather than merely a new data type.

### Scenario domain

**Current bounded player-facing domain.** `scenarios` is a published top-level catalog/detail domain
owning `scenario:*` records. It participates in primary navigation and the landing page; global search
and Glossary participation are deliberately disabled for the bounded core set. Scenario slug
normalization remains the typed `scenario:<slug>` contract used by the maintained scenario layer.
Rules export keeps stable scenario collection identity, collection revision, ordered membership,
source publication revision, and deterministic content identity separate. `RulesDatabase` owns central
selection: default reads consider only `current` publications, historical revisions require an explicit
collection/revision pair, and unsupported selections never fall back silently. `ScenarioCatalog`
composes current publication list/detail read models in maintained collection order. Detail reads
require an explicit supported Army Points value and project setup, geometry, scoring, special
Rules/Skills, end conditions, source issues, and publication provenance for that selection.

The JSON API exposes those models at `/api/scenarios` and
`/api/scenarios/<slug>?army_points=...`; maintained text is resolved in the selected scenario context
so scoped concepts do not leak into ordinary core help. The browser publishes `/scenarios` and
`/scenarios/<slug>`, uses the shared versioned `s=` state token for Army Points selection, and requests
the canonical SVG from `/api/scenarios/<slug>/map.svg?army_points=...`. Browser code does not derive
scenario semantics or maintain separate geometry. Search/Glossary participation can be reconsidered
only if a larger scenario corpus creates a concrete discovery need.

## Domain capability registry

**Current.** `src/infinity_db/application_domains.py` is the canonical capability registry for the
application-domain set. It separates semantic ownership from publication/presentation and is used
by public rules-reference routing so route ownership is not duplicated in a second kind-to-route
mapping. The registry expresses at least:

- stable public domain slug and singular/plural display names;
- the concept/record kinds owned or presented by the domain, plus reviewed record-category
  filters where one kind is intentionally split across application owners;
- whether the domain participates in navigation, global search, and Glossary;
- whether it provides a landing/overview surface, catalog/list surface, scoped views, or detail
  pages;
- whether the surface is currently publishable/player-visible or only scaffolded for future use; and
- any cross-domain navigation target needed by the domain.

These capabilities must be independent. In particular, `identity: yes` must not imply
`detail page: yes`, and `top-level domain` must not imply `catalog`.

## Shared domain interaction contract

Player-facing domains should use the same high-level state vocabulary even when their content
differs.

### Landing state

The unscoped canonical domain URL presents the domain itself: heading, domain-level context where
useful, stable controls, and the natural overview or complete catalog.

### Scoped state

A meaningful selection/filter can produce a scoped view. Controls and domain identity stay in a
stable position while scoped content replaces or narrows landing content. Domain-wide explanatory
content may be landing-only when repeating it in every scoped state would add noise.

The scoped state must be reproducible in the URL when it materially changes what the user sees.

### Detail state

Domains with individually browsable records may expose detail pages. Detail surfaces reuse the same
canonical identities and link back to the relevant landing/scoped context rather than maintaining a
parallel definition.

### Reset state

Clearing a scope returns to the canonical landing state. It should not leave an ambiguous empty or
partially scoped page.

### Catalog search URL state

**Current.** Searchable catalog landing pages expose their client-side text search through the
shared versioned browser share-state token. Loading a tokenized catalog URL hydrates the search
control before the first result render, and clearing the search removes the token when no other
page state remains. Updating a text search replaces the current history entry rather than adding one
entry per debounce interval. Legacy `q` parameters remain accepted for backward compatibility and
are canonicalized to the token form. Future catalog filters that materially change visible results
should join the catalog share-state schema rather than remaining browser-local state.

This state model is shared vocabulary, not a requirement that every domain implement all four
states.

## Armies

**Current.** Armies are a top-level **overview** domain rather than a conventional catalog/detail
domain.

`/armies` presents concise entries for current playable armies plus explicitly curated historical
Army references. Current entries include:

- army symbol;
- canonical display name;
- a short maintained description;
- **Out of catalog** status when source `discontinued` metadata applies; and
- a link to Unit Explorer with the corresponding Army filter already applied.

Legacy entries such as Spiral Corps and Foreign Company are visibly marked **Legacy** / **Not
playable in N5** and do not offer a Unit Explorer link. Catalog status remains independent from
playability; Reinforcement entries inherit the display status only from their canonical main
overview group.

The overview reuses canonical Army identities/slugs and existing symbol relationships for current
entries, with curated identities only for historical lists absent from current Army data. The short
descriptions are maintained gameplay-oriented editorial copy in
`data/curated/identities/army-overview.json`. They may summarize broad force character and common
play patterns, but they are presentation guidance rather than rules, legality, identity, or
availability input.

Individual `/armies/<slug>` detail pages are not required unless a future player-facing use case
justifies them. The pre-filtered Unit Explorer URL is the shareable destination for browsing an
army's Units.

## Fireteams

**Current.** Fireteams are a top-level domain with an **overview landing state** and an
**army-scoped view**.

The current behavior is:

```text
/fireteams
    domain heading
    army selector
    general Fireteam rules summary

/fireteams?s=<versioned-share-state-token>
    domain heading
    army selector
    selected Army's Fireteam chart/reference content
```

The general Fireteam rules summary belongs to the Fireteams domain itself. It is shown on the
unscoped landing state and hidden when an Army is selected, rather than repeated above every Army
chart. Clearing the Army selection returns to the unscoped summary. The scoped API response likewise
contains only the Army chart projection; the domain-wide rules summary is returned by the unscoped
Fireteams API.

The selected Army must be URL-addressable/shareable. The current browser contract stores that scope
in the versioned share-state token while continuing to accept legacy `army=<slug>` URLs. Loading a
scoped URL should render the scoped state directly without first depending on presentation of the
general summary.

General Fireteam reference records remain globally searchable/linkable even when the landing summary
is hidden in an Army-scoped view. Stable record IDs need not be renamed merely because Fireteams is
now their canonical presentation domain.

## Ammunition and Labels

**Current.** Ammunition and Labels are published top-level domains using the shared domain
framework and intentionally exercise different data shapes.

### Ammunition

Ammunition is a first-class rules/reference domain with canonical `ammunition:*` identities, a
catalog, detail surfaces, global-search participation, and typed maintained-text links. The current
population contains the eleven N5.3 base Ammunition types and concise reviewed reference text.
Deeper relationships can be added within the same domain contract when they serve the application
model; incomplete work belongs in `docs/TODO.md`.

### Labels

Labels are a first-class rules/reference domain backed directly by the canonical current rules
Label vocabulary already used by Skills, States, Hacking Programs, and other references. The
browser exposes those existing identities through catalog/detail/search surfaces rather than copying
Label definitions into generic rule records.

Typed Label identity is important because surface terms can legitimately overlap other concept kinds
(for example a term can exist as both a Label and a Trait/Characteristic). Domain/kind information
must therefore remain part of semantic identity and linking.

## General Rules

`rules` is the generic top-level fallback for rules/reference concepts that do not have a clearer
canonical top-level domain. It is now published through `/rules` as a normal catalog/detail domain.
The current publication owns the `basic-rule`, `order-type`, `command-token-use`, and
`peripheral-type` categories from canonical `rule:*` records. The `order-type` category covers the
four N5 Order types: Regular, Irregular, Special Lieutenant, and Tactical. Impetuous remains owned
by the Skills domain because it grants a phase activation without spending an Order; General Rules
may surface it as a related cross-domain reference without changing that ownership. Qualified
internal identities such as `rule:peripheral-type:servant` keep that canonical identity while
projecting to a collision-checked public route slug such as `/rules/peripheral-type-servant`.

A concept belongs here because **General Rules is its best semantic owner**, not merely because the
concept is inconvenient to classify. Fireteam general/bonus records remain owned by the Fireteams
surface, and Unit-profile help remains contextual profile help rather than being duplicated into the
fallback catalog. If a later domain provides a natural home, presentation/domain ownership should
move there while preserving stable identities and relationships where practical.

General Rules does not absorb embedded vocabularies solely to give them pages. Concepts such as
Attributes and scoped Game terms remain canonical and glossary/searchable without becoming generic
rule-detail pages.

## Glossary usage

**Current.** `/glossary` answers “what does this term mean here?” across InfinityDB rather than
behaving as a separate rules catalog. It is a federated projection over canonical rules/reference
domains and embedded vocabularies.

The projection:

- derives entries from current canonical top-level domains and embedded vocabularies;
- preserves typed concept identity and owning domain so identical surface text is not merged;
- links browsable concepts to their owning detail surfaces;
- presents embedded-only definitions at stable Glossary anchors without inventing detail routes;
- keeps aliases on the canonical concept rather than creating duplicate entries; and
- renders maintained-text tokens through the same semantic-reference layer used by owning detail
  surfaces.

Profile notation help is a contextual consumer of this framework, not a competing glossary dataset.
Attribute labels on Unit details reuse the same canonical `attribute:*` definitions and Glossary
anchors. Source-backed `term:*` records provide the corresponding embedded terminology layer for
concepts that do not warrant dedicated pages; search and Glossary preserve their Game-term identity
separately from same-name Labels, Traits, or other concepts.

## Population and publication policy

The current registry is fully published for the domains listed above, but publication does not mean
semantic coverage is permanently complete. New records and deeper relationships can be added within
those domains without inventing new navigation or identity systems.

A future domain may be scaffolded internally before publication when that helps establish reusable
contracts, but unpublished capabilities must remain explicit in the registry and must not be
documented as player-visible behavior. Concrete completeness work is tracked in `docs/TODO.md`;
this document owns only the durable domain/presentation contract.
