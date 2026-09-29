# Application domains

**Project domains:** Data processing, Web backend, Web frontend

This document defines the planned **application-domain** structure used to organize InfinityDB's
player-facing game/reference information. Application domains are distinct from the engineering
ownership labels in `docs/project-domains.md`.

The goal is to give canonical concepts a stable home without forcing every concept type into the
same UI. Data identity, semantic ownership, search/glossary participation, and browser presentation
are related concerns, but they are not the same concern.

The capability registry described below is **Current** in
`src/infinity_db/application_domains.py`. Ammunition and Labels are published catalog domains,
Armies is a published overview domain, Fireteams follows the shared landing/scoped interaction
contract, and Attributes are a published embedded vocabulary projected through contextual help,
global search, and the federated Glossary. General Rules publication remains **Design direction**.
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

**Current.** Attributes are the first explicit example. Canonical identities such as
`attribute:mov`, `attribute:bs`, and `attribute:wip` own reviewed definitions and can participate in
semantic relationships without creating `/attributes` or individual Attribute pages. Their
player-facing presentation is contextual help/tooltips plus Glossary/search results.

Other finite vocabularies may use the same model when a player-facing catalog would add little
value.
Do not promote a vocabulary to a top-level domain merely because it has typed identities.

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

## Planned top-level domain set

The planned top-level domain set through 1.0 is:

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

This is a planned skeleton, not a requirement that every domain immediately be fully populated or
visible in primary navigation. Future evidence may justify another domain, but new top-level domains
should require a concrete player-facing browsing/use case rather than only a new data type.

## Domain capability registry

**Current.** `src/infinity_db/application_domains.py` is the canonical capability registry for the
planned domain skeleton. It separates semantic ownership from publication/presentation and is used
by public rules-reference routing so route ownership is not duplicated in a second kind-to-route
mapping. The registry expresses at least:

- stable public domain slug and singular/plural display names;
- the concept/record kinds owned or presented by the domain;
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
entries, with curated identities only for historical lists absent from current Army data. The
initial short descriptions are structural summaries derived from canonical Army role/group
relationships; they deliberately do not infer lore or play style from Unit composition. Richer
reviewed presentation copy can replace those summaries later without changing the domain contract.

Individual `/armies/<slug>` detail pages are not required unless a future player-facing use case
justifies them. The pre-filtered Unit Explorer URL is the shareable destination for browsing an
army's Units.

## Fireteams

**Current.** Fireteams are a top-level domain with an **overview landing state** and an
**army-scoped view**.

The intended behavior is:

```text
/fireteams
    domain heading
    army selector
    general Fireteam rules summary

/fireteams?army=<slug>
    domain heading
    army selector
    selected Army's Fireteam chart/reference content
```

The general Fireteam rules summary belongs to the Fireteams domain itself. It is shown on the
unscoped landing state and hidden when an Army is selected, rather than repeated above every Army
chart. Clearing the Army selection returns to the unscoped summary. The scoped API response likewise
contains only the Army chart projection; the domain-wide rules summary is returned by the unscoped
Fireteams API.

The selected Army must be URL-addressable/shareable. Loading a scoped URL should render the scoped
state directly without first depending on presentation of the general summary.

General Fireteam reference records remain globally searchable/linkable even when the landing summary
is hidden in an Army-scoped view. Stable record IDs need not be renamed merely because Fireteams is
now their canonical presentation domain.

## Ammunition and Labels

**Current.** Ammunition and Labels are the first new top-level domains published through the shared
domain framework. They intentionally exercise different existing data shapes.

### Ammunition

Ammunition is a first-class rules/reference domain with canonical `ammunition:*` identities, a
catalog, detail surfaces, global-search participation, and typed maintained-text links. The initial
0.9 population establishes the eleven N5.3 base Ammunition types and concise reviewed reference
text without requiring every Ammunition interaction to be exhaustively modeled.

The 1.0 completeness pass can then finish deeper semantics such as base/combined Ammunition
relationships, Saving Roll interactions, State effects, and other rules-reference links where they
serve the application model.

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
canonical top-level domain.

A concept belongs here because **General Rules is its best semantic owner**, not merely because the
concept is inconvenient to classify. If a later domain provides a natural home, presentation/domain
ownership should move there while preserving stable identities and relationships where practical.

General Rules should not absorb embedded vocabularies solely to give them pages. Concepts such as
Attributes can remain canonical and glossary/searchable without becoming generic rule-detail pages.

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
anchors. Additional terminology coverage remains tracked in `docs/TODO.md`.

## Population and publication strategy

The domain registry and route/navigation contracts should be established before exhaustive content
population. A scaffolded domain may exist internally without appearing in primary navigation until
its minimum useful player-facing content is ready.

The implementation sequence is:

1. **Current:** establish the application-domain registry/capability model and planned top-level
   skeleton;
2. **Current:** expose Labels and Ammunition as the first newly browsable domains;
3. **Current:** publish the Armies overview and normalize Fireteams to the landing/scoped
   interaction contract;
4. **Current:** publish Attributes as the first embedded vocabulary and Glossary as a federated
   projection over canonical domains plus embedded vocabularies;
5. continue filling semantic relationships and terminology coverage through the 1.0 completeness
   work.

This sequence deliberately creates the reusable structure first so later domains do not need to
invent independent navigation, catalog, glossary, or scoped-view conventions.
