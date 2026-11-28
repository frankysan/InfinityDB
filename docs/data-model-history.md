# Army history data model

**Project domain:** Data processing

This document owns historical source evidence, identity continuity, observed
change semantics, and the embedded player-facing Unit history.
[Army model](data-model-army.md) owns present-day identity/context;
the [data lifecycle](../data/README.md) owns history input paths and commands.
The [Unit history presentation](web-design-guidelines.md#unit-history-presentation)
owns the layout. This is a partial, source-backed reference, not a
complete release log or a replay of all historic Army lists.

## Private Army history research database

The explicit offline N5 history builder produces a separate, ignored SQLite
research artifact, not a fifth serving database. Its source report registry
pins the accepted full reports and archive/receipt identities. The
`source_observation`, `unit_identity`, `comparison`, `comparison_change`
and `coverage_gap` tables preserve source evidence and provisional identity
without equating observation dates with publication dates. The
`history_record` table retains separate evidence streams for composition,
structural occurrences, membership, loadout reconciliation and catalog
transitions/review. Unit and comparison links are indexed; catalog usage
links do not imply changes to Unit composition. The original research record
bodies remain available as JSON. No record is promoted to a confirmed change
or selected for public exposure by this builder. See the
[data lifecycle](../data/README.md) for the explicit build command.

The private Unit-history preview binds this research index to a current
Army database whose recorded source archive matches an accepted direct N5
observation. Require the historical identity disposition, direct source ID,
slug, canonical faction and `idArmy` to agree before following the current
`logical_unit_sources` mapping. Historical-only and conflicting identities
remain explicit and are not assigned to a present-day Unit by name alone.
A logical Unit can contain several historical source identities; keep their
source paths and Army contexts distinct. Composition candidates group fields
only for the same source target, observed window, endpoint comparison scope
and historical labels. They retain before/after values and evidence record
references, not inferred exact release dates. Army list and AVA observations
are separate from composition. Unresolved structural, membership and loadout
records and catalog evidence remain separate drilldown references; raw
comparison categories and ambiguous Army windows retain coverage context.
The preview is not a published history API or a verified event log.
The offline HTML review renders attributes and costs as source before/after
values, and compares resolved Skill, Equipment and Weapon multisets by exact
signatures. Retain duplicates and modifiers; distinguish changed definitions
with unchanged occurrence multisets from changed occurrences. Do not pair
unrelated IDs by name. Army list appearances and disappearances describe
observed list presence, not necessarily playable availability. Current Army
labels are explicitly marked as such. Evidence references and raw values
remain expandable; unresolved and catalog evidence are separate from the
main timeline, with coverage gaps visible at report level.

## Effective composition and identity continuity

The public history is a concise semantic summary, not the layout of
the private review. Effective-loadout comparison matches individual profiles
in Groups by surviving Loadout keys and uniquely reconciled rekeys. A
profile-owned Skill applies to every associated loadout; a relocation is
unchanged only for a particular loadout whose effective occurrences remain
unchanged. Normalize default quantity and empty extras, preserve occurrence
multiplicity, and leave overlaps across owners unresolved. Definition-only
changes are not composition changes. Identical cost deltas and effective
reference changes are grouped across loadouts, then across exact matching
Army windows and payloads. Compare supported surviving pairs even when
siblings are unresolved, disabled, newly observed or no longer observed.
Record the paired, unpaired and excluded keys and per-pair dispositions.
All-loadout scope requires complete comparison of both endpoints; it means
all loadouts in the compared Group, not all loadouts in the logical Unit or
all Armies. Multi-profile comparisons retain affected profile identities and
scope; shared loadout costs are counted once. All-group scope additionally
requires complete coverage of the profiles.

Direct-owner comparisons may proceed when Include edges resolve to the same
Army-local Unit/Group/Loadout targets with stable labels, profile identities
and multiplicity, and Peripheral attachments have equivalent unique local
definitions. Mark this limited scope explicitly; never attribute attached
entities' capabilities to a Controller or flatten the Include graph. Changed
or unresolved relationships and lifecycle composition remain review evidence,
as do unresolved rekeys, disabled options and non-pilot fields. Preserve
original comparison and candidate links. Use observation ranges
until independently established update dates exist. Technical evidence
belongs in developer review, not normal player copy.

The separate private player-history renderer combines the four semantic
summary streams with supported profile characteristic candidates. It resolves
historical Group and owner labels against the pinned comparison endpoints,
consolidates changes by exact observation window and Army scope, and combines
equal group-wide effects even where the affected loadout definitions differ
between Armies. The player-facing timeline groups entries by the later endpoint's encoded
JSON revision date, not the backup acquisition date or an inferred public
publication date. Preserve each complete observation window in technical evidence. Within a date, display
equivalent effects once across disjoint Army scopes even if their earlier
observation dates differ. Retain distinct cost pairs, partial scopes, source
identities, overlapping Army observations and underlying evidence. Pair one-sided
cross-catalog reference changes as an observed classification transition only when
exact target names, rule links, occurrence modifiers, scope, loadout coverage and
comparison evidence agree uniquely. Retain both source observations; do not infer
mechanical equivalence or a gameplay change from classification alone. Display
source-list membership as observed presence, not playable availability. The offline preview exposes unresolved outcomes
and provenance through optional technical controls; it is not a public API
or publication approval.

Direct attachment history additionally compares observed changes to Include
and Peripheral fields on surviving source owners. Resolve Include targets
within the endpoint Army and Unit, and resolve Peripheral references through
unique exact local definitions. Ignore equivalent Peripheral rekeys and
reference display ordering, normalize default quantities, and retain
multiplicity. Summarize supported one-sided changes and quantity changes
with the owner and target context; do not infer a replacement between
different target identities. Preserve raw comparison links and unresolved
outcomes. Attachment changes are source-scoped candidates, not evidence of
playable availability or a rules-derived Controller relationship.

Loadout lifecycle summaries use the structural occurrence and reconciliation
evidence separately from effective changes on surviving loadouts. A supported
one-sided key appearance or disappearance with no replacement evidence becomes
an observed addition or removal candidate scoped to that Army and Group.
Resolve its endpoint profile-owned and loadout-owned references and costs.
Known composition-equivalent rekeys are not additions or removals; ambiguous
modifications and unsupported composition remain review outcomes. Consolidate
only identical payloads and observation windows across Armies.

A second continuity pass permits exact normalized composition equivalence:
resolve references and retain metadata and unknown fields, normalize default
quantities and empty extras, and resolve stable Include and unique Peripheral
targets. Require stable parent and loadout labels and uniqueness among all
siblings at both endpoints, including survivors. Retain both unpaired source
records as evidence for each reconciled pair. Verified rekeys may normalize
Include target identity in attachment comparisons. Do not promote distinctive
reference modification hints into accepted continuity without stronger evidence.

Contextual availability retains profile-scoped AVA and explicit disabled-state
changes separately from observed Army-list presence. Format AVA using the
current display convention, including Total for values of 100 or greater.
Missing or ambiguous values remain review outcomes. A list appearance is
not proof of playable availability. Preserve declared membership claims
and link corroborating list evidence without treating the claims as additional
timeline changes. Keep the Army scope and observation window explicit.

## General-profile and Army-context projection

Project
historical changes onto the same application-facing General-profile and
Army-specific profile/loadout boundaries used by current Unit details. A
General-profile event must describe an observed change to that profile's
shared presentation, not merely a source-level profile change or a change
repeated in several Armies. Compare the shared facts at the relevant
historical endpoints using the canonical General-profile composition and
compatible profile identities, including the applicable occurrence selection.
Do not apply today's common-item intersection retrospectively. Incomplete
coverage, ambiguous continuity and asynchronous observations must not be
treated as proof of a change shared by all applicable loadouts or Armies.
A confirmed shared change appears once in the relevant General profile;
retain any additional Army-specific effects in the relevant Army cards.
Points, SWC, contextual AVA, Army-list presence and loadout lifecycle belong
to the Army context. Preserve unmatched historical identities and removed
Army contexts separately rather than assigning them to an unrelated current
profile or losing their history. Source-only classification changes do not
become changes to the General profile unless its projected facts changed.
The [Unit history presentation](web-design-guidelines.md#unit-history-presentation)
owns disclosure and layout.

The contextual projection uses the current materialized General profiles
with all optional Unit categories enabled and current Army cards. General
history covers seven scalar fields (CC, BS, PH, WIP, ARM, BTS and S) and
supported shared Skill, Equipment and Weapon occurrence changes. It requires
one stable source Unit identity, every known Army context with a unique
comparison ending on the same encoded JSON revision date, complete declared
Army coverage, and one uniquely identified profile occurrence at each endpoint.
Scalar endpoint values must agree across those contexts and with the canonical
General-stat composition. Earlier revision dates may differ. In that case,
shared-item promotion additionally requires the same occurrence transition to
be independently supported in every Army's own comparison. Preserve every
individual comparison window; do not merge changes with different later dates.

For shared items, compare both historical endpoint projections using the
canonical shared-item functions, including the loadouts present at each
endpoint. Promote only exact occurrence changes supported by accepted semantic
summaries. Remove the promoted occurrences from the Army display rows, retaining
all residual effects and original evidence. Do not promote synthetic common
bases with varying extras, unresolved references, catalog aliases requiring
identity reconciliation, cross-catalog transitions, or Units with snapshot-bound
reviewed loadout capabilities. Source-classified Equipment can be presented
under Equipment when the historical source ID and name match the reviewed
current classification and neither endpoint contains a possible native
counterpart. Preserve the source bucket in the evidence; this is presentation
policy, not a historical rules classification claim. Other source-classified
Skills remain excluded. The item projection allows stable, uniquely resolved direct
attachments, without flattening their capabilities into the Controller. In a
multi-profile Group, promote a Skill or Equipment change only when accepted
summaries explicitly identify a single profile, all sibling profile IDs and
labels remain stable, and the exact occurrence is owned by the target profile
rather than a loadout. Do not promote overlapping multi-target summaries or
group-owned loadout changes to one profile. Changed or unresolved attachments
and disabled loadouts remain excluded. Ambiguous or removed Army cards retain
a separate historical context. This is a conservative projection. The maintainer confirmed on 2026-11-26
that the existing Army data permission covers historical use.

## Published Unit history

Army schema v35 (compatibility 44) embeds the contextual player history
projection in `unit_history_payloads`, keyed by logical Unit ID. The payload
contains date, scope, category and typed display rows, keyed internally by
General profile identity and Army card ID plus sorted availability flags;
unmatched historical contexts remain separate. Raw research evidence stays
offline. The default `infinity-db build` validates the
accepted archive and historical research database hashes and recomputes the
projection against the staged v34 Army database before publishing Rules.
Its build provenance includes the corpus hashes and history builder sources.
The embedded table is covered by the Army published-content checksum and the
final database-set fingerprint. Unit details automatically read the selected
Unit's history; the normal revision-aware API cache applies. Older v34 sets
remain supported without history; new history-free development builds require
`--no-unit-history`. The explicit `serve --unit-history PATH`
preview override remains available and rejects mismatched database hashes;
override responses are not cached. General history describes the
all-optional-categories profile scope, regardless of current browser filters,
which is stated in the disclosure.
Action rows retain their text fallback alongside optional typed distance and
MOV parts. Historical source extra types determine which values are distances;
reviewed Skill conventions determine positive-sign formatting. Historical
references remain independent of the current Army's available Skills.

Historical snapshots support observed changes, not guaranteed complete
intervening events or publication dates. Extend the pinned input corpus
deliberately and revalidate projection identity and coverage; do not
silently change the accepted hashes to accommodate unknown evidence.
