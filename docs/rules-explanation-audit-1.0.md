# Rules explanation audit for InfinityDB 1.0

**Project domains:** Data processing, Web backend, Web frontend

**Audit date:** 2026-10-09

**Examined commit (follow-up):** `c5400ab1b950990fdacc509be91c110fe85431fb`

**Original audit commit:** `859823f8d2899405a40cf126883d2adf5763db7c`
**Status:** Assessment for review; no rules, code, schemas, tests, databases, or runtime configuration changed.

## Executive summary

The existing curation does **not yet meet the 1.0 rules interaction explanation
standard**. Its identities, source separation, and many recent explanations are
sound, but several older summaries omit conditions that change gameplay. A
relationship marked reviewed is often a navigation decision rather than a
complete explanation. Passing the existing interaction audit therefore does not
establish rules correctness or explanation completeness.

The most urgent examples are Engineer's incorrect STR-only requirement for
State cancellation (REA-001), Doctor's omitted recovery gate and failure result
(REA-002), Intuitive Attack's apparent second attack roll (REA-003), Continuous
Damage's missing extra-Critical-roll exception (REA-004), and the missing
BS Weapon (WIP) restrictions (REA-005). Controlled Jump omits immediate ARO
application and opposing-program cancellation (REA-006). These findings arise
from actual authored text compared with identified official clauses, rather than
from counting absent graph edges.

Other material gaps concern simultaneous recovery, cumulative State MODs,
Marker cancellation, Peripheral subtype exceptions, Fireteam integrity and
Special Dice, Supportware, and placement restrictions. Simple individually
correct cards do not always explain what happens when read together. Existing
Army tables already supply Martial Arts values and Hacking Program statlines;
their absence from curated facts is **not** reported as missing numeric data.

The Flash Pulse benchmark's outcome is verified against English N5.3 printed
pp. 95-96 and 186, exact archived English Wiki revisions, and Spanish Wiki
wording. It correctly retains BTS, Non-Lethal, and failed-roll Stunned. However,
the curated Immunity family omits the ordinary ARM/BTS protection against
State/Wound/Attribute Traits, leaving the reason for the exception incomplete
(REA-010). Spanish Weapon Chart revision 3987 still lists two rolls and omits
State: Stunned; the English chart and Army list one roll and the Trait. The
the official Spanish N5.3 PDF p. 196 agrees with English on one
Saving Roll and both Traits. The unresolved discrepancy is specifically the
Spanish Wiki chart versus the two published N5.3 PDFs (REA-027).

Kobra Pistol's DA/two-roll interpretation is supported while Anti-materiel
remains disputed (REA-028). Two additional internal PDF contradictions need
review: a Level 3 Fireteam example includes the Level 4 bonus (REA-034), and
Armed Turret's detailed profile and deployable table disagree on Silhouette
(REA-037). The supplied Spanish PDF reproduces both internal contradictions.
It also contains a conflicting six-dice Fireteam reminder (REA-041), even
though its general Special Dice rule agrees with English. Neither disagreement
authorizes silently rewriting source data.

Reproducibility is also limited: the exact September 18 Wiki ZIP named by both
collections is missing locally. Seventy-four record citations, across 72
records, depend on it. Later ZIPs and exact archived revisions were used as
**separate comparison evidence**, not replacements (REA-029). FAQ v0.1 is
available locally but has no curated publication; its ITS headings require
scope adjudication before applying rulings to core scenarios (REA-030).

All **367 records** were screened. The original **217 selected clause reviews**
and **150 screening-only records** reconcile exactly to the unchanged inputs.
Follow-up compares **87 additional records**, yielding **304 selected clause
reviews and 63 screening-only records**, alongside **24 Labels, 6 Skill Types, 20
scenario components, 314 authored relations, and 113 deferred interaction
candidates**. Selected clause reviews are identified individually in the
[inventory](rules-explanation-audit-1.0-inventory.md); screening is not a
source-by-source approval. This report investigates **18 interaction families**
and now registers **44 findings: 31 High, 12 Medium, 1 Low, and 0 Critical**.
The precise review-tier totals are recorded in the inventory. It does not certify every Weapon profile,
Spanish publication, Wiki member, or browser surface.

Start with a focused **recovery and Intuitive Attack correction batch**:
REA-001, REA-002, REA-003, REA-009, and REA-022. These have direct English PDF
evidence and can largely be addressed using existing prose fields and links.
Resolve source conflicts separately; retain the positive patterns below. The
remediation plan is a proposal, not accepted replacement semantics.

**Follow-up qualification:** REA-038 adds a source-decision gate for the friendly
target qualifier. No universal Allied-only restriction was established, but
absence of a prohibition is not treated as explicit permission for every
enemy/neutral case. Do not widen target allegiance while fixing independently
verified recovery mechanics. Counterintelligence's reversed Command Token actor
(REA-043) is a new confirmed P0 correction. TinBot sharing (REA-039), missing
SpecBall procedure (REA-040), Spanish PDF/Wiki conflicts (REA-041/042), and
the metadata-only Breaker Marksman reference (REA-044) add focused follow-ups.

Use the [source manifest](rules-explanation-audit-1.0-sources.md) for portable
provenance and the [complete notice reconciliation](rules-explanation-audit-1.0-n5.3-reconciliation.md)
for all 26 English rules bullets plus four additional Spanish subjects. Closing
findings does not close source verification: the inventory's
[completion gate](rules-explanation-audit-1.0-inventory.md#audit-completion-gate)
retains explicit pending dispositions.

## Methodology and scope

### Contracts and ownership

The review used [the curated explanation standard](../data/curated/README.md#explaining-rules-interactions),
[rules semantics](rules-semantics.md), [rules research](rules-research.md),
[N5 source history](n5-source-history.md), [web design guidelines](web-design-guidelines.md),
[the 1.0 release gate](releasing.md#version-10-data-completeness-gate),
[TODO](TODO.md), and [documentation ownership](README.md). Architecture,
data-model, AI context, testing guidance, AGENTS, and the local workflow
companion were consulted for boundaries. This is not release preparation and
does not claim to satisfy the mandatory whole-documentation release audit.

The main inputs are:

- **C:** [core curated collection](../data/curated/rules/n5-core-v5.3.json), 355 records.
- **H:** [Hacking Program collection](../data/curated/rules/n5-hacking-programs-v5.3.json), 12 records.
- [Interaction ledger](../data/curated/rules-interactions/reviews.json) and
  [catalog denominator](../data/curated/rules-interactions/catalog-scope.json).
- Relevant maintained mappings under `config/catalogs/` and source-review
  evidence under `config/validation/`; these were read, not rewritten.
- The current browser source paths `rules-reference.js`, `ammunition-facts.js`,
  `catalog-detail.js`, `skill.js`, and `fireteams.js`, plus the Skill and
  Hacking Program catalog composition paths. These establish code behavior,
  not real-browser acceptance.

### Review procedure

1. Enumerate every collection record, kind, citation, relation, variant, and
   scope. Separately enumerate Label/Skill-Type vocabularies and scenario components.
2. Read summaries, requirements, effects, restrictions, typed facts, links, and
   source notes. Identify candidate conflicts across cards and absent baseline owners.
3. Check selected mechanics against complete relevant English PDF pages,
   exact Wiki revision payloads where available, Army metadata, and FAQ clauses.
   Consult Spanish wording and older N5 publications for important discrepancies.
4. For each material case distinguish applicability, baseline, modifier,
   exception, outcome, and evidence. Retain multi-rule conditions rather than
   replacing them with an unconditional pairwise edge.
5. Inspect current data-to-browser paths before calling stored facts absent or
   visible. Record implementation inspection separately from browser verification.
6. Register distinct correction units, positive cases, unresolved scope decisions,
   and remaining coverage gaps. Do not treat a keyword match as an adjudicated defect.

Ad hoc analysis used the project virtual-environment Python, JSON parsing,
`zipfile`, `hashlib`, `pypdf`, read-only SQLite inspection, and searches. The
commands read sources directly; no analysis script or non-documentation artifact
is part of the deliverable. Full PDF text/artwork is not reproduced here.

Reproducible read-only inventory steps, using the virtual-environment interpreter:

```text
<venv-python> -B tools/audit_rules_interactions.py --check-output docs/rules-interaction-checklist.md
git rev-parse HEAD
git diff --check -- docs
git check-ignore docs/rules-explanation-audit-1.0.md docs/rules-explanation-audit-1.0-inventory.md
```

For an independent recount, load each `n5*.json` with `json.loads`, concatenate
its `records` array, count `kind`, and sum `len(record.get("relations", []))`.
Count ledger `records` and `futureInteractions` separately. For evidence
reproduction, hash source bytes with SHA-256, inspect ZIP members with `zipfile`,
and select printed PDF pages with `PdfReader(...).pages[printed_page - 1]`
for S1. The inventory's D list is an authored review disposition, not a value
that can be inferred from a `review.status` flag. Git check-ignore exits 1
with no output for non-ignored audit documentation, as expected.

### Coverage and denominators

The [record inventory](rules-explanation-audit-1.0-inventory.md) lists every ID,
its collection, selected source locator, relation count, review tier, and related
findings. **D** means selected material clauses compared with evidence, not a
pass for every clause of the record. **S** means authored-text/structure screening
only. No existing record was omitted from screening. Source evidence that was
inaccessible remains inaccessible even when the associated record has a D review
using another source. Scenario map geometry was structurally inventoried, not
visually reaccepted.

| Denominator | Observed scope | Meaning and limit |
| --- | --- | --- |
| Core records | 355/355 screened | Includes 60 declaration-category metadata records |
| Program records | 12/12 screened; selected clauses checked for all 12 | Army tables separately own numeric profiles |
| Authored relations | 314 enumerated/screened by owner | No claim that every edge received independent official-source adjudication |
| Deferred candidates | 113 screened | 107 target `post-0.7.0`, 6 target `1.0.0`; historical labels do not decide 1.0 scope |
| Ledger records | 307 | 282 reviewed, 10 inherited, 15 pending; excludes declaration-category metadata |
| Historical primary catalog | 182 | 95 Skills, 30 Equipment, 33 Traits, 24 States; this is a 0.7 denominator |
| Labels / Skill Types | 24 / 6 screened | Definitions, not additional semantic records |
| Scenario components | 20 screened | 12 objectives, 3 endings, 3 geometry, 2 setup components |
| Core scenarios | 4; 12 geometry configurations; 24 point-size selections | Scoring/setup/rules selected for source comparison; no new visual acceptance |
| Army metadata | 185 Weapon rows; 40 Ammunition rows | Selected names/modes inspected; not 185 independently adjudicated profiles |
| Interaction families | 18 investigated | No finite exhaustive denominator for all possible multi-rule combinations established |

Accuracy, completeness, clarity, consistency, source discrepancy, and
presentation are assessed separately. An explicit unresolved source note can be
good curation while the gameplay question remains unresolved. There is no
aggregate percentage of "rules correctness": the available evidence cannot
support one.

## Source register

The [portable provenance manifest](rules-explanation-audit-1.0-sources.md)
extends this original S1–S12 register with S13–S19 and derived S20. It is the
canonical follow-up owner for artifact availability, checksums, acquisition and
revision/member identity. Local evidence is an external reproduction requirement,
not a download included in a clean tracked checkout.

References to **S1 p. N** below mean the numbered printed page of the exact
English v5.3 file, not an arbitrary PDF viewer page. Its cover occupies file page
1 and the subsequent numbered pages align with file page numbers. FAQ printed
page 1 is file page 2. Acquisition time is not publication time.

| ID | Source and identity | Use and verification |
| --- | --- | --- |
| S1 | Local official English N5 rules v5.3 (external requirement S1), 196 pages; curated publication date 2026-08-10; PDF creation metadata 2026-08-10 | Direct clause/chart text comparison; SHA-256 below |
| S2 | Local official English FAQ v0.1 (external requirement S2), 5 file pages / 4 numbered content pages; PDF creation metadata 2026-08-25 | All content pages read; core and ITS sections kept distinct; metadata date is not a verified publication date |
| S3 | Local N5 v5.2 English (external requirement S3), 194 pages; PDF creation metadata 2025-10-15 | Original Kobra p. 68 comparison; follow-up selected change comparisons in appendix; not current authority |
| S4 | `data/wiki/WIKI-en-history 20260928-165727.zip`, 3592 members, `_history/index.json` | Exact revision payloads 3643, 4083, 3000, 3156 checked originally; 3979, 3980 and 4116 added in follow-up; later acquisition does not turn older revisions into N5.3 publications |
| S5 | `data/wiki/WIKI-en 20260926-200832.zip` | Available comparison archive; not the September 18 collection source; not a full member-by-member audit |
| S6 | Army snapshot manifest (ignored external evidence S6), archive `data/raw/JSON 20260929-114335.zip`, acquired 2026-09-29 11:43:35 +02:00; manifest source data-change date 2026-09-03 | Direct `metadata.json` profiles and `101-panoceania.json` version `7.26246.158`; not a fresh live Army acquisition |
| S7 | [Spanish Immunity](https://infinitythewiki.com/es/Inmunidad), footer revision 3677 | Live web response retrieved 2026-10-09; general clauses and Example 4 compared; exact oldid URL initially inaccessible |
| S8 | [Spanish Weapon Chart](https://infinitythewiki.com/es/Tabla_de_Armas), footer revision 3987 | Live web response retrieved 2026-10-09; Flash Pulse row compared; retained old/current table blocks must be distinguished |
| S9 | [Spanish Engineer](https://infinitythewiki.com/es/Ingeniero), footer revision 3823 | Live response retrieved 2026-10-09; separates STR repair from other State cancellation; shows historical reroll wording separately |
| S10 | [Spanish Intuitive Attack](https://infinitythewiki.com/es/Ataque_Intuitivo), footer revision 3882; response carried an N5.2 banner | Supporting language comparison only; its example opposes the WIP roll, without a second roll |
| S11 | [Official N5.3 announcement](https://infinityuniverse.com/en/news/infinity-rules-update-5-3), 2026-09-01 | Live checked; named changes include Kobra ammunition, Prone/Berserk, Aerial/Boost, Minelayer and Peripheral rules; no independent ruling on Kobra Anti-materiel |
| S12 | [English Engineer](https://infinitythewiki.com/Engineer), footer revision 3980; [Intuitive Attack](https://infinitythewiki.com/Intuitive_Attack), footer revision 3877 | Live supporting comparisons; underlying exact revisions are also discoverable in S4's history index |

Local hashes for reproducibility:

```text
S1 53921e91c2d3d62ad5f7125abcd4174b2cf937d45320233eed5b6d301b66af3f
S2 7bf26b7d039db7826ef5500b1a2159fe54855b4e632133cab416becee65b85aa
S3 643ab0b6d7c3e9e5ffbf668543723161f252367e7788af09ec008be19c17851b
S4 d49db0515420af297a7349201e8bb7750ecb422048d32bb494273ee1cea78a5d
S5 c0fe18c165473e3f273efd58aa7ecb0ea0d94ee274189de9361aad175b3de987
S6 f103a7afd02e68d845cc9ce38b1948f46914676bbc6a5e6b790d0a04148b6c75
S6 metadata.json bb46ff9c6039dde600108f6592be616cb7620d67240cd81c2e3587cad4fc8995
C  bb17f2013a1b8bc32961689789e4afff6fcc30f1476248d5d53d4b96587ab9a5
H  8b5a90cd036e048603d20d647139232e9fe7e27e1e43223cc68741387cd3143b
```

Exact S4 payload provenance:

| Revision | Revision timestamp from history index | Member / SHA-256 |
| --- | --- | --- |
| Immunity 3643 | 2025-04-28T09:04:03Z | `_history/oldid/3643.html` / `7014821db88a6725addd6e1c354952e5a2ac017a15a6d2ddb695a5de6333dfa8` |
| Weapon Chart 4083 | 2026-08-27T14:26:38Z | `_history/oldid/4083.html` / `b08f1eb349d4ed35055755fde6222f7461dbbf1a33a402cd8dc45c2cfbae7ba3` |
| Combined Ammunition 3000 | 2025-03-28T15:15:11Z | `_history/oldid/3000.html` / `1ad611ee7d66293387922c7755aa97dbab167cd44c8f1a76ee87518dc5bd7abd` |
| Vulnerability 3156 | 2025-04-08T10:35:35Z | `_history/oldid/3156.html` / `a92fddb42c092cb1cc67f64c613eafff01b64f7b3a0ed10e78c252bf23d3a2f7` |

These four revisions corroborate selected rules also printed in S1. The current
Wiki banner is not evidence that an unchanged April 2025 revision was authored
in September 2026. Spanish oldid revision timestamps and independently hashed historical bytes
are now recorded under S21 in the source manifest. Original URL evidence was not
hash-pinned; follow-up independently checked selected exact member bytes in S14,
including the original Spanish Immunity/Weapon Chart/Engineer revisions.

The original follow-up could not access the Spanish v5.3 PDF from its
candidate URL; **a separately supplied official Spanish v5.3 PDF has now been
hashed and inspected as S17**, without equating its creation timestamp to
publication time. GitHub, raw README, and public API
requests for [the unofficial Army backup](https://github.com/massayoshi/infinity-army-backup)
returned inaccessible/cache-miss responses. No historical backup commit or file
was verified. S3 and available local Army archives are the historical evidence
used here; the repository's prior backup research remains prior research.

Failed Spanish PDF endpoint:
`https://downloads.corvusbelli.com/infinity/rules/infinity-rules-n5-es-v5.3.pdf`.
This was an access attempt, not verification that the URL identifies the
current official Spanish download. That failed retrieval remains part of the research history; it no longer
means that Spanish N5.3 PDF evidence is unavailable.

## Findings register

Every ID below is a distinct follow-up unit. **High** means an incorrect,
misleading, or missing clause can materially change play; **Medium** means
missing explanatory context, evidence, or presentation that needs review;
**Low** means localized wording/link quality. **P0** means correct confirmed
misleading gameplay first; **P1** means required material 1.0 explanation or
source review; **P2** means usability improvement. No Critical severity was
assigned. Unless stated otherwise, affected identities live in **C**. Fix types
are recommendations only. Regression cases are specified in the remediation
plan, not implemented.

In evidence fields, **Observed** denotes a directly inspected repository or
filesystem fact. Gameplay conclusions remain **Explicit**, **Derived**, or
**Unresolved** as stated; an implementation observation is not an official ruling.

### REA-001 - Engineer incorrectly restricts all targets to STR

**Classification:** correctness, consistency. **Severity:** High. **Priority:** P0.
**Evidence:** Explicit; high confidence. **Affected:** `skill:engineer`,
`state:immobilized-a`, `state:immobilized-b`, `state:isolated`, `state:targeted`.

**Current:** Engineer's requirement says the target must be a friendly STR
Trooper, Equipment, or Scenery item. Its effect combines removing Structure and
canceling a State. The State cards independently offer Engineer cancellation.
This excludes VITA targets from the cancellation branch and confuses repair with
State recovery.

**Evidence/result:** S1 p. 91 requires contact; STR limits the Wound-removal
branch. Its alternative cancels all eligible non-Unconscious States and has no
failure penalty. S1 pp. 164-165, 168 and 171 refer affected Troopers to Engineer
without a STR gate. S9 revision 3823 distinguishes the same branches. Stunned
remains a separate VITA/STR-specific exception on p. 170.

**Action:** Separate repair, State cancellation, self-use, failure results, and
State-specific exceptions in requirements/effects/restrictions. Use linked
examples: a VITA Trooper's Targeted State can be canceled by Engineer; its
Stunned State requires Doctor. **Fix:** curated text and links; future validation.
**Dependencies:** REA-009 and REA-022 for broader recovery, not prerequisites.

**Follow-up evidence:** Allegiance follow-up: REA-038 is an independent source-decision gate. Correct
the STR-only State-cancellation error without making a universal claim about
enemy treatment. Allied examples remain supported, but do not prove an Allied-only
restriction. Full closure of eligibility requires the recorded allegiance decision.

### REA-002 - Doctor omits its ordinary recovery gate and lethal failure

**Classification:** correctness, completeness. **Severity:** High. **Priority:** P0.
**Evidence:** Explicit; high confidence. **Affected:** `skill:doctor`,
`state:unconscious`, `state:stunned`, `skill:no-wound-incapacitation`, `equipment:cube`.

**Current:** Any friendly VITA Trooper in contact appears eligible; success
"restores a lost Wound or cancels an applicable State." No ordinary Unconscious
requirement or failed-roll Dead consequence is supplied. This suggests routine
healing of an operational wounded VITA Trooper.

**Evidence/result:** S1 p. 90 limits ordinary recovery to a VITA target in
Unconscious State, removes one Wound on success, and sends it to Dead on failure.
Self-use cannot occur in a Null State. Stunned (p. 170), NWI (p. 104), and
Technorganic (p. 116) provide distinct applicable exceptions. Doctor (2W),
Doctor (ReRoll WIP=X), and the subsequent Command Token reroll have explicit
conditions; the replacement WIP does not apply to the Command Token reroll.

**Before/after proposal:** "Restores a lost Wound" becomes "For ordinary recovery,
the target has VITA, is Unconscious, and is in contact: pass WIP to remove one Wound; failure
causes Dead. Other States and Skills can allow treatment under their own rules."
Add those exception links rather than listing them as universally eligible.
**Fix:** text/links; variant facts only if needed. **Dependencies:** REA-001,
REA-009, REA-022, REA-038; preserve NWI and Technorganic qualifications.
Allegiance is intentionally omitted from this proposed baseline until REA-038
is adjudicated; this is not implicit permission to treat all enemies.

**Follow-up evidence:** Allegiance follow-up: S14 Médico 3822 and S4 Doctor 3979 corroborate the
ordinary recovery requirements but do not establish the universal friendly qualifier.
REA-038 separates direct treatment, delegated Allied use, self-use and Engaged
prohibitions; the neutral recovery proposal above deliberately leaves it open.

### REA-003 - Intuitive Attack appears to require a second attack roll

**Classification:** correctness, clarity, completeness. **Severity:** High.
**Priority:** P0. **Evidence:** Explicit; high confidence. **Affected:**
`skill:intuitive-attack`, `trait:intuitive-attack`, `weapon:mines`.

**Current:** The user makes WIP and "on success" performs a BS Attack Roll.
The restriction covers WIP MODs but not opposing reactions or Main Target
Criticals. It also describes only attacking, despite Mine placement using it.

**Evidence/result:** S1 p. 49 and its example resolve the attack using that WIP
roll: eligible Attack/Dodge reactions oppose it. A WIP Critical is Critical only
against the Main Target. The same page has the Deployable placement branch;
failed placement consumes a Disposable use. S10 revision 3882 corroborates the
single WIP resolution and avoids the English clause's possible two-roll reading.

**After proposal:** "Resolve this B1 attack with one unmodified WIP roll. An
eligible Attack or Dodge ARO opposes that roll; do not make another BS roll.
A Critical affects only the Main Target as a Critical." Explain placement as a
separate use. **Fix:** text, links, future regression. **Dependencies:** REA-023.

### REA-004 - Continuous Damage omits the extra Critical roll exception

**Classification:** completeness, correctness risk. **Severity:** High.
**Priority:** P0. **Evidence:** Explicit; high confidence.
**Affected:** `trait:continuous-damage`, `skill:immunity`.

**Current:** Every failed Saving Roll appears to start repeated rolls until
success or Dead; no distinction is made for the additional Critical roll.

**Evidence/result:** S1 p. 175 explicitly excludes Continuous Damage from the
additional roll caused by a Critical. A failed ordinary hit save starts the
continuation; failing only the extra Critical save does not start another chain.
Applicable Immunity can negate the Trait (pp. 95-96).

**Action:** State the ordinary failed-save Wound and continuation, then the
extra-roll exception, with a separate linked Immunity qualification. The ledger's
deferred indirect Dead edge does not supply this missing exception.
**Fix:** text/links; avoid a direct unconditional Dead transition.
**Dependencies:** REA-010 and REA-013 for shared Critical context.

### REA-005 - BS Weapon (WIP) omits explicit prohibited combinations

**Classification:** completeness, consistency. **Severity:** High. **Priority:** P0.
**Evidence:** Explicit; high confidence. **Affected:** `trait:bs-weapon-wip`,
`skill:bs-attack`, `weapon:flash-pulse`, Pheroware references.

**Current:** The Trait says all BS rules/MODs apply to WIP, with no exception.
The deferred ledger correctly remembers BS Attack (Shock) and Guided restrictions,
but normal Trait prose does not communicate them.

**Evidence/result:** S1 p. 175 prohibits BS Attack (Shock) with this Trait;
the Guided rules on p. 39 exclude PH/WIP weapons. General Attribute substitution
does not authorize those explicitly excluded combinations.

**Action:** Add the restrictions now as prose with existing relevant links;
defer a precise typed edge only if the exact variant has no identity. A missing
graph endpoint need not defer an intelligible warning on the owning card.
**Fix:** text/links; structured variant/edge work separately. **Dependencies:**
REA-033; no general ban on Shock Ammunition is inferred.

### REA-006 - Controlled Jump lacks declaration timing and opposing cancellation

**Classification:** completeness. **Severity:** High. **Priority:** P0.
**Evidence:** Explicit; high confidence. **Affected:** H `hacking-program:controlled-jump`,
C `skill:combat-jump`, `rule:scenario:designated-landing-area`.

**Current:** Only persistent +3/-3 and one-active-program-per-player are stated.
The player cannot determine whether a newly declared ARO modifies the jump in
progress or whether opposing Programs both remain modifiers.

**Evidence/result:** S1 p. 59 applies the effect immediately on declaration,
permits an ARO against Combat Jump anywhere on the table, and explicitly cancels
the effects when both players have Controlled Jump active. Firefight's separate
+3 remains separately sourced on p. 155; opposing Program cancellation does not
erase that scenario bonus.

**Action:** Explain immediate ARO application, optional declaration, table-wide
scope, and the exact opposing-program exception. **Fix:** H text and links;
timing facts only after a deliberate schema decision. **Dependencies:** REA-007,
REA-018; do not invent a general "opposing MODs cancel" rule.

### REA-007 - Speedball's reuse of Combat Jump needs the FAQ exclusion

**Classification:** completeness, clarity. **Severity:** Medium. **Priority:** P1.
**Evidence:** Explicit; high confidence. **Affected:** `skill:request-speedball`,
H `hacking-program:controlled-jump`.

**Current:** Request Speedball reuses Combat Jump with PH 15. Controlled Jump
correctly says Troopers, but no cross-reference explains why that reuse does not
include its MODs. Neither side states the FAQ exception.

**Evidence/result:** S2 printed p. 1, Quantronic Combat, explicitly says
Controlled Jump does not affect Speedballs and only applies to Troopers.
**Action:** Add a short cross-linked exclusion with its FAQ identity; keep PH 15.
**Fix:** text/links and versioned FAQ evidence. **Dependencies:** REA-006,
REA-030. This is missing explanation, not a confirmed existing numerical error.

### REA-008 - Protheion needs the overkill limit and profile MOD

**Classification:** completeness. **Severity:** High. **Priority:** P1.
**Evidence:** Explicit; high confidence. **Affected:** `skill:protheion`,
`state:dead`, `attribute:vita`.

**Current:** The per-Wound conversion, +2 cap, and positive-before-negative timing
are good. The card omits the profile-listed negative opponent MOD and does not
explain that further failed saves after Dead give no benefit.

**Evidence/result:** S1 p. 109 supplies the negative MOD to the opponent's
Face to Face Attribute. S2 printed p. 2, Protheion question, says additional
failed Saving Rolls beyond those needed for Dead have no effect or benefit.
Do not turn an overkill failed save into a recovered Wound or VITA increase.

**Action:** Preserve the existing sequence; add those two conditions and a
short example of attacking an Unconscious target. **Fix:** text/links and FAQ
citation. **Dependencies:** REA-009, REA-030.

### REA-009 - Recovery and re-infliction in the same Order are unexplained

**Classification:** completeness, consistency. **Severity:** High. **Priority:** P1.
**Evidence:** Explicit; high confidence. **Affected:** `skill:engineer`,
`skill:doctor`, `state:immobilized-a`, `ammunition:para`, recovery Equipment.

**Current:** Recovery cards and State cards present cancellation independently;
Protheion alone explains relevant positive-before-negative sequencing.
Readers may conclude that a successful cancellation erases the new State too.

**Evidence/result:** S1 p. 15 explicitly applies the positive effect before the
negative effect. Its Engineer/Riotstopper example first cancels IMM-A, then
resolves the new PARA save; failure can inflict IMM-A again. S9 revision 3823
repeats that example. This is sequencing, not mutual cancellation.

**Action:** Add one reusable, cited timing explanation and targeted recovery
links. **Fix:** prose/links; an optional canonical timing record is future work.
**Dependencies:** REA-001, REA-002, REA-026; preserve Protheion's already correct sequence.

### REA-010 - Immunity omits the ordinary Trait protection behind its exceptions

**Classification:** completeness, clarity. **Severity:** High. **Priority:** P1.
**Evidence:** Explicit; high confidence. **Affected:** `skill:immunity`,
`weapon:flash-pulse`, `trait:arm-0`, `trait:bts-0`, `trait:continuous-damage`, `trait:state`.

**Current:** ARM/BTS protection is summarized as Ammunition becoming Normal.
The facts do not state the additional protection against applicable Traits
causing States, Wounds, or Attribute reduction. The Flash Pulse explanation
names the exception without explaining what it overrides.

**Evidence/result:** S1 p. 95 states this Trait protection separately in the
ARM and BTS branches, followed by the IMPORTANT exceptions. Page 96 Example 2
negates Monofilament's ARM=0 and State: Dead; Example 4 preserves Non-Lethal and
Stunned. The extra Critical roll persists unless Immunity (Critical) applies.
S4 Immunity 3643 and S7 confirm the relevant clauses.

**Action:** Add the missing baseline to family prose, scoped to the appropriate
Saving Attribute and non-Comms attack. Then link the exceptions and examples.
**Fix:** text/links; broader typed Trait protection would require validation
design, not an invented generic algorithm. **Dependencies:** REA-004, REA-011,
REA-024, REA-027. Flash Pulse's current outcome is a positive finding.

### REA-011 - Stored Immunity cases are only partly presented

**Classification:** presentation, completeness. **Severity:** Medium. **Priority:** P1.
**Evidence:** Observed implementation; high confidence about the inspected path.
**Affected:** `skill:immunity` and `facts.immunityInteraction` in C.

**Current:** The facts store three combined cases, a Viral Vulnerability case,
and Flash Pulse. Ordinary `effects` expose Flash Pulse and the derived AP-only
case; they do not explain the two whole-ARM combined cases or the explicit
Plasma/Enhanced case. `appendRuleDetails` renders prose groups and Ammunition
facts, but has no Immunity-case renderer.

**Evidence/result:** S1 pp. 95-96 and 67 distinguish ammunition conversion from
the independent ARM+BTS profile. S4 revisions 3643 and 3000 support the stored
conditional cases. Against Plasma, Enhanced does not remove either base save.
The stored ARM combined cases are Derived, not separately printed examples.

**Action:** First add concise linked prose using existing fields; consider a
small dedicated display only if repeated cases justify it. Preserve conditions
and evidence classification. **Fix:** text/links or future browser presentation;
not a combat calculator. **Dependencies:** REA-010, REA-025. Real-browser
visibility was not tested in this audit.

### REA-012 - Smoke and Eclipse describe zones without sufficient resolution

**Classification:** completeness, clarity. **Severity:** High. **Priority:** P1.
**Evidence:** Explicit; high confidence. **Affected:** `ammunition:smoke`,
`ammunition:eclipse`, `equipment:multispectral-visor`, `trait:reflective`.

**Current:** Smoke mentions opposing attacks whose LoF crosses it, without the
roll-required condition, winning every relevant opposed roll, Normal Dodge, or
Critical limitation. Eclipse supplies zone blocking but not how its Reflective
exception changes the ordinary Smoke/MSV opposition.

**Evidence/result:** S1 p. 66 requires an enemy Attack with a roll and LoF
crossing the zone. Every relevant Face to Face roll must be won for the Template
to remain. An enemy Dodge against Smoke is Normal; a Smoke Critical creates no
extra effect. MSV attacks are not opposed by ordinary Smoke. Page 64 explicitly
allows opposition to qualifying MSV attacks with Eclipse; p. 125 provides Level
rules, and S2 p. 2 qualifies targeted Sixth Sense/MSV1.

**Action:** Give separate examples for an ordinary shooter, an MSV shooter, and
a non-opposed Template attack. Keep zone geometry/expiry facts distinct from
resolution. **Fix:** text/links; optional future fact expansion. **Dependencies:**
REA-019, REA-026; do not promise universal protection from attacks.

### REA-013 - AP rounding and T2 die identification are missing player actions

**Classification:** completeness, clarity. **Severity:** Medium. **Priority:** P1.
**Evidence:** Explicit; high confidence. **Affected:** `ammunition:ap`,
`ammunition:em`, `ammunition:t2`.

**Current:** Defense is halved without rounding instructions. T2 correctly
stores two Wounds for the ordinary failed save and one for the extra Critical
save, but never tells players to identify those dice before rolling.

**Evidence/result:** S1 pp. 63-64 round halved ARM/BTS upward. Page 37 adds PS
and applicable saving MODs separately. Page 67 requires identifying the T2 hit
die and extra Critical die before the saves. These are material execution
instructions even though the recorded values are correct.

**Action:** Add rounding and the T2 die-labeling instruction in existing prose;
retain the current differentiated typed Wound facts. **Fix:** text/links;
presentation enhancement optional. **Dependencies:** REA-026.

### REA-014 - Dodge and Reset lack multi-effect conditions

**Classification:** correctness risk, completeness. **Severity:** High. **Priority:** P1.
**Evidence:** Explicit clauses; arithmetic examples Derived. **Affected:**
`skill:dodge`, `skill:reset`, `state:engaged`, `state:isolated`,
`state:immobilized-b`, `state:targeted`, `skill:sixth-sense`, `equipment:bangbomb`.

**Current:** Dodge's summary suggests successful PH automatically cancels
Engaged; it omits the required valid move out of contact. The cards do not explain
cumulative Reset State penalties or differing Dodge success values for several
attacks. "Applying State-specific MODs" leaves the reasoning to the player.

**Evidence/result:** S1 p. 160 requires moving out of contact; without a valid
position the Trooper stays Engaged. Pages 157, 165, 168 and 171 make State MODs
cumulative: IMM-B plus Isolated means -12 to Reset, and Targeted adds its own -3
before applying the overall +/-12 MOD limit (p. 24). Sixth Sense p. 111 explicitly retains
IMM-A, IMM-B and Isolated penalties. Dodge p. 79 lists circumstances that impose
only one shared -3; p. 80 and Bangbomb p. 120 show a roll can evade one attack
but not another, preventing the Dodge move.

**Action:** Explain these as separate scoped cases; distinguish evasion,
movement, and State cancellation. **Fix:** text/links and future scenario
regressions. **Dependencies:** REA-015 and REA-026. No universal per-die
success evaluator or unconditional cancellation edge is recommended.

### REA-015 - Several State cards lack their operative cancellation conditions

**Classification:** completeness, consistency. **Severity:** High. **Priority:** P1.
**Evidence:** Explicit; high confidence. **Affected:** `state:camouflaged`,
`state:hidden-deployment`, `state:holoecho`, `state:holomask`,
`state:impersonation-1`, `state:impersonation-2`, `state:prone`,
`state:disconnected`, `state:retreat`, `state:suppressive-fire`.

**Current:** Hidden Deployment describes only Sensor cancellation; other cards
refer to "listed" revelation/cancellation conditions that are not listed in the
record. Prone omits automatic cancellation on Unconscious recovery. Disconnected
omits recovery via its Controller and Coherency. Retreat omits the Command Token
and army recovery routes. Suppressive Fire replaces concrete cancellation with
a broad reference to unnamed conditions.

**Evidence/result:** S1 pp. 157-172 give these procedures. Hidden Deployment
cancels on declaring an Order/ARO, not just being Discovered. Marker revelation
can apply to the entire Order (pp. 158, 163-164, 167). Controller recovery and
Coherency cancellation differ from Engineer treatment (p. 160). Suppressive
Fire cancels on joining a Fireteam and specified declarations (p. 171).

**Action:** Author short State-specific trigger/cancellation paragraphs with
links and named exceptions. Do not replace them with a universal Marker
cancellation rule: Impersonation and HoloMask have distinct restrictions.
**Fix:** text/links; conditional structured facts only if useful later.
**Dependencies:** REA-014, REA-017, REA-020, REA-035. REA-035 owns Discover
MOD wording rather than duplicating this lifecycle finding.

**Follow-up evidence:** Additional selected N5.3 comparisons: S1 p. 29 adds Berserk to Prone
transition restrictions, while p. 169's shorter list omits it. S1 p. 97 adds
Impetuous end-of-Order Prone wording that is not adequately explained by a
phase-only restriction. Camouflaged p. 157 restricts ARO declaration, not merely
execution, and requires the actual permitted-ARO list. These extend this finding;
do not infer that every movement/CC Skill or every Impetuous Order has the same
exception. The reconciliation records the previous/current clauses.

### REA-016 - Stealth omits Deployables and multi-Trooper reaction reasoning

**Classification:** completeness. **Severity:** High. **Priority:** P1.
**Evidence:** Explicit; high confidence. **Affected:** `skill:stealth`,
`weapon:mines`, `trait:boost`, `skill:sixth-sense`, `skill:combat-instinct`.

**Current:** The enemy-LoF exception and counter-Skill edges are present, but
Stealth does not state that it is ineffective against Deployable Weapons and
Equipment. Mixed activation and the need to declare Stealth while a Marker
remain unexplained.

**Evidence/result:** S1 p. 112 explicitly excludes Deployables. S2 p. 2 says
an ARO generated by another activated Trooper can target a Stealth user, but
becomes Idle if that user does not declare a Skill permitting the ARO. It also
requires announcing Automatic effects that restrict AROs, such as Stealth,
when used in Marker State. Mine triggering and ARO entitlement are independent.

**Action:** Add those conditions and one Controller/Peripheral or Fireteam
example, retaining Sixth Sense/Combat Instinct links. **Fix:** text/links,
future regressions. **Dependencies:** REA-015, REA-017, REA-020, REA-030.

### REA-017 - Peripheral subtype identities do not explain their operation

**Classification:** completeness, consistency. **Severity:** High. **Priority:** P1.
**Evidence:** Explicit; high confidence. **Affected:** `skill:peripheral`,
all five `rule:peripheral-type:*` records, `skill:cyberplug`, `state:disconnected`.

**Current:** The family says the type defines behavior; subtype facts largely
cover Controller eligibility, maximum count, distance, and Cyberplug profile
names. They omit the actions, cancellations, and exceptions those identities
need to explain. This is incomplete existing content, not absent identities.

**Evidence/result:** S1 pp. 106-108 distinguish shared activation/Idle behavior,
Servant contact delegation and single active Servant, Synchronized Coherency,
Control Spearhead roles, undeployed Ancillary/Fireteam exceptions, and Cyberplug
Autonomous behavior when its Controller becomes Isolated/Null. Cyberplug
Doctor/Engineer is an explicit exception to the Controller's usual Idle.
S2 p. 2 confirms one participant unable to perform a Skill Idles while others
can perform it. Generic Disconnected propagation cannot override Cyberplug.

**Action:** Add a concise common baseline plus subtype-local exceptions;
explain Controller/Peripheral roll ownership. **Fix:** text/links; subtype
facts/relations and browser support only where deliberately needed.
**Dependencies:** REA-001, REA-009, REA-015, REA-020, REA-030.

### REA-018 - Firewall, Hacking Area, and Supportware have no adequate baseline owner

**Classification:** completeness, clarity. **Severity:** High. **Priority:** P1.
**Evidence:** Explicit; high confidence. **Affected:** `equipment:repeater`,
`equipment:tinbot-firewall`, `equipment:evo-hacking-device`, `skill:hacker`,
H `hacking-program:assisted-fire`, `hacking-program:enhanced-reaction`,
`hacking-program:fairy-dust`, `hacking-program:controlled-jump`.

**Current:** Several Programs say "normal Supportware exclusivity and
cancellation rules apply," but no curated Supportware baseline supplies them.
Firewall cards refer to a Firewall without a corresponding definition.
Repeater describes enemy use but not the complete targeting/ARO distinction.
No authored `equipment:firewall` or `rule:hacking-area` exists in C/H.

**Evidence/result:** S1 pp. 55-56 specify one Supportware per benefitting Trooper
and one sustained Program per Hacker, replacement/cancellation, and loss on
Hacker Isolated/Null. Firewall applies its listed WIP penalty plus fixed +3 to
saves; only one Firewall is chosen. Enemy Repeaters reach enemy Hackers, not
arbitrary enemy non-Hackers; invalid requirements become Idle. Page 60's
example replaces the entire Fairy Dust Program on targeting one covered REM
with Enhanced Reaction. S2 p. 1 explains disabled Device Firewalls.

**Action:** Supply cited baseline reference prose and linked, Program-specific
exceptions. Preserve Army's Program tables and Device associations; no numeric
duplication is needed. **Fix:** new curated content/links, potential publication
work for new owners. **Dependencies:** REA-006, REA-019, REA-026, REA-030.

### REA-019 - NFB's label does not explain suppression and duration

**Classification:** completeness, clarity. **Severity:** Medium. **Priority:** P1.
**Evidence:** Explicit; high confidence. **Affected:** C Label
`negative-feedback`, `skill:mimetism`, `equipment:albedo`, `equipment:holoprojector`;
H `hacking-program:cybermask`, `hacking-program:white-noise`.

**Current:** The Label says only that another NFB element is incompatible.
Program facts do not explain which effects stop or when their restriction ends.
The player must reconstruct this from external rules.

**Evidence/result:** S1 pp. 59, 61, 76 and 174 make the new NFB effect override
other NFB effects for its duration. Cybermask's restriction persists while in
IMP-2; White Noise's applies to its Hacker while the Template is present.
That does not cancel every allied Trooper's Equipment or the whole army's effects.

**Action:** Expand the shared definition with duration/owner scope and link it
from affected Program prose. Separate Label definition from Program-specific
lifetimes. **Fix:** Label/curated text and links. **Dependencies:** REA-015,
REA-018; no pairwise universal negation edges.

### REA-020 - Fireteam basics omit action ownership and integrity exceptions

**Classification:** completeness. **Severity:** High. **Priority:** P1.
**Evidence:** Explicit; high confidence. **Affected:** `rule:fireteam-general`,
`skill:ft-master`, `skill:number-2`, `skill:nco`, `skill:tactical-awareness`,
`state:suppressive-fire`, Peripheral types.

**Current:** General facts cover chart authority, Coherency, group membership,
and activation, but not who performs an attack, differing AROs, leaving/rejoining,
or cancellation. Type badges show Haris 3 and Core 3-5 without creation-only
qualification. FT Master/Number 2 and Peripheral exceptions are not connected
to a readable common integrity baseline.

**Evidence/result:** S1 pp. 132-136 distinguish leader-only attacks from shared
Movement/Reset, majority ARO, member departure, whole-team cancellation, and
States Phase rejoining. S2 p. 3 says losing members does not change Type and
chart minimums apply to creation, with FT Master's exception. Ancillary
eligibility has its own conditions (p. 107); Number 2 can replace a disabled
leader (p. 105). The two forms of removal must not be conflated.

**Action:** Add a concise creation/activation/integrity reference and link the
exceptions. Qualify type counts as formation requirements. **Fix:** curated
text/facts/links; renderer changes if new fact groups are adopted.
**Dependencies:** REA-017, REA-021, REA-030, REA-034.

### REA-021 - Fireteam and Martial Arts bonuses need Special Dice reasoning

**Classification:** completeness, clarity. **Severity:** High. **Priority:** P1.
**Evidence:** Explicit; high confidence. **Affected:** `rule:fireteam-level-bonuses`,
`skill:martial-arts` and L1-L5, `skill:bs-attack`, `trait:disposable-x`,
`equipment:medikit`, `equipment:gizmokit`, `trait:bs-weapon-ph`, `trait:bs-weapon-wip`.

**Current:** Fireteam bonuses list +1 SD and +1 BS but do not explain allocation,
discard timing, Disposable uses, or no-roll/Long Skill limits. Martial Arts
numeric values already exist in the Army table and browser; the explanation is
missing, not the chart. The label +1 BS can obscure its WIP/PH weapon applicability.

**Evidence/result:** S1 pp. 75, 100 and 136 say SD adds a die to roll/discard
without increasing Burst or consuming uses, in both turns. Fireteam SD does not
apply to Long Skills or no-roll Direct Templates, does apply to ranged Kits,
and stacks with other BS Attack SD. Level 4 modifies the Attribute for the
BS Attack, including PH/WIP weapons. S2 p. 3 prohibits applying SD or +1 BS
Fireteam bonuses to Discover. Page 86 expressly permits SD for Berserk despite
the ordinary Long Skill restriction; this is not a general Long Skill permission.

**Action:** Link one Special Dice baseline and state the applicable Fireteam/
Martial Arts/Berserk exceptions. **Fix:** prose/links, possibly explanatory
table captions; retain imported tables. **Dependencies:** REA-005, REA-022,
REA-026, REA-034.

### REA-022 - Kit recovery and Disposable spending need multi-roll rules

**Classification:** completeness, consistency. **Severity:** High. **Priority:** P1.
**Evidence:** Explicit; high confidence. **Affected:** `equipment:medikit`,
`equipment:gizmokit`, `trait:disposable-x`, `trait:double-shot`, `weapon:pt-endgame`,
`skill:remote-presence`, `skill:technorganic`, `skill:no-wound-incapacitation`.

**Current:** Kits describe success and failure per PH roll, but omit the
same-Order multi-hit aggregation. Disposable describes each use, not how Burst
spends uses or is capped by remaining uses. Double Shot omits the requirement
that both Disposable (2) charges remain. These omissions become misleading
when bonuses produce several hits/rolls.

**Evidence/result:** S1 pp. 123-124 say any successful Kit PH roll means recovery
and still only one Wound is removed under the ordinary multi-hit rule; Remote
Presence separately removes enough to leave either Unconscious level (p. 110).
Pages 175 and 75 distinguish Burst spending from SD. Double Shot's +1B is
available with Disposable (2) only while both uses remain.

**Action:** Separate remote hit, target PH, same-Order aggregation, and special
recovery exceptions. Add remaining-use conditions and an SD-versus-B example.
**Fix:** text/links and future regression cases. **Dependencies:** REA-001,
REA-002, REA-021; do not infer success/failure aggregation for unrelated attacks.

### REA-023 - Placement cards defer essential geometry and deployment restrictions

**Classification:** completeness. **Severity:** High. **Priority:** P1.
**Evidence:** Explicit; high confidence. **Affected:** `skill:place-deployable`,
`trait:perimeter`, `skill:minelayer`, `weapon:wildparrot`, `weapon:armed-turret`,
`equipment:fastpanda`, `equipment:deployable-repeater`, `trait:deployable`.

**Current:** Place Deployable refers to unspecified active/reactive placement
restrictions. Perimeter supplies ZoC placement but not its required path.
Minelayer refers to enemy-presence restrictions without naming them. Armed
Turret says it reacts to enemy Orders, without the Model-not-Marker limit.
Deployable's card also omits immediate removal on reaching Unconscious.

**Evidence/result:** S1 p. 82 permits Active placement along the moved route,
requires contact in Reactive placement, a supported horizontal surface, and
placement at Conclusion; Perimeter additionally needs a passable path. Page
102 states Minelayer's enemy exclusion and deployable-position limits.
Indiscriminate (p. 175) and the item profile must be considered before applying
general exclusions. Page 70 limits Armed Turret reactions to an enemy Model.
Page 175 sends a Deployable entering Unconscious directly to Dead and excludes
Deployable-trigger chains. S2 p. 2 addresses an occupied intended position.

**Action:** Put short baseline restrictions on their owners and item exceptions
on their cards. Keep Mine trigger area distinct from Boost ZoC and Perimeter
placement. **Fix:** text/links, possible conditional facts. **Dependencies:**
REA-003, REA-017, REA-030, REA-037. The reviewed Mines/Drop Bears exceptions
are positive evidence, not proof that all Deployables are complete.

### REA-024 - BioWeapon needs a target-conditioned explanation alongside the chart

**Classification:** completeness, clarity. **Severity:** Medium. **Priority:** P1.
**Evidence:** Explicit baseline; conditional roll interpretation Derived.
**Affected:** `trait:bioweapon`, `weapon:mines`, `ammunition:normal`,
`ammunition:da`, `ammunition:shock`, `skill:vulnerability`.

**Current:** The Trait says DA+Shock applies to VITA, with no semantic component
links. Viral Mine's profile says N/BTS/one save; its related rules point to
BioWeapon but do not explain how the extra effect changes the VITA case.
This can be mistaken for one save universally or for Viral being its own
current Ammunition identity.

**Evidence/result:** S1 pp. 174 and 181 and S6 metadata weapon 63 distinguish
the profile from the target-conditioned Trait. DA supplies two saves against a
VITA target; Shock's direct-Dead rule additionally needs VITA 1 and a failed
save. Against STR, BioWeapon does not supply DA+Shock. The one-save chart field
is not automatically a typo: it is the baseline before applying that Trait.
Vulnerability (Viral) is separately weapon-name-scoped (S1 p. 118).

**Action:** Add a short VITA/STR comparison and component links, explicitly
marking the combined reasoning Derived. Keep source profile values.
**Fix:** prose/links and the already deferred reuse edges if appropriate.
**Dependencies:** REA-010, REA-013, REA-025. Broader partial Immunity cases
remain research, not a certified general algorithm.

### REA-025 - N+E/M is absent from the reviewed composition map

**Classification:** completeness, presentation. **Severity:** High. **Priority:** P1.
**Evidence:** Explicit; high confidence. **Affected:** `ammunition:normal`,
`ammunition:em`, `skill:immunity`; Army E/M CC Weapon, source weapon 7,
Ammunition source 5 `N+E/M`.

**Current:** The map covers AP+DA, AP+Exp, AP+Shock and AP+T2, not N+E/M.
The Army source is preserved, but its components and joint Wound/State result
are not explained by a reviewed shared example. E/M's standalone State-only
card cannot explain the Normal component's Wounds.

**Evidence/result:** S1 p. 67 explicitly gives two halved-BTS saves, Wounds
from the Normal component, and Isolated plus conditional IMM-B from E/M;
a Critical adds one save. S6 confirms source IDs and fields. This is an
explicit printed combined example, unlike the derived partial-Immunity case.
Non-Lethal, when actually present, has its own overriding rule (p. 175).

**Action:** Review source 5 and its actual profiles, link both components, and
provide the printed reasoning. Preserve the original Saving fields and do not
calculate arbitrary compositions in JavaScript. **Fix:** mapping/curated
content/links and future validation; no such edits made here.
**Dependencies:** REA-010, REA-011, REA-013, REA-026.

### REA-026 - Useful general mechanics remain research rather than linked reference content

**Classification:** completeness, clarity. **Severity:** Medium. **Priority:** P1.
**Evidence:** Explicit absence from C/H; official mechanics Explicit.
**Affected:** General Rules domain, `skill:bs-attack`, `skill:cc-attack`,
`skill:move`, `skill:idle`, `rule:command-token-strategic-use`, recovery references.

**Current:** No canonical baseline records cover Saving Roll/PS, Face to Face
resolution, Guts, ordinary declaration timing, or Coordinated Orders. The
34 `rule` records are peripheral types, orders, Fireteams, profile help, and
scenario rules. Maintained research describes many mechanics, but it is not
the normal player reference. Attribute definitions alone do not provide them.

**Evidence/result:** S1 pp. 14-15, 24-25, 37-38, 75-76 and 129-131 establish
these baselines. Useful examples include an unopposed save using PS plus
protection, capped cumulative MODs, simultaneous effects, illegal declarations
still spending Disposable uses, and Coordinated recovery's any-success rule.
This is absent curated content, distinct from incomplete existing Skill cards.

**Action:** Scope concise, source-cited General Rules to the explanations
needed by current catalogs. Link repeated baselines instead of copying whole
procedures into each Skill. **Fix:** new curated definitions and publication
integration; not a game engine. **Dependencies:** supports REA-009, REA-013,
REA-014, REA-018, REA-021, REA-025. Full procedural simulation is outside scope.

**Follow-up evidence:** Follow-up selects the parameter rules on S1 p. 75: Dodge (ARM+3) and
PARA CCW (-6) need a shared modifier baseline distinguishing the user's Attribute,
the opponent's Face-to-Face penalty and the separate PARA Saving Roll. REA-042
retains the bilingual condition conflict. S1 pp. 93-94 also requires the
G: Jumper shared-Cost, Loss of Lieutenant and Suppressive Fire qualifications;
these are linked-baseline work, not a request for an execution engine.

### REA-027 - Flash Pulse's Spanish chart disagrees on rolls and Traits

**Classification:** source discrepancy. **Severity:** High. **Priority:** P1.
**Evidence:** Profile baseline confirmed in both N5.3 PDFs; Wiki conflict Explicit.
**Affected:** `weapon:flash-pulse`, `skill:immunity`, `ammunition:stun`.

**Current:** C uses the English one-BTS-save profile and records the competing
Spanish Wiki numbers/Traits in its source notes. Its described gameplay outcome
is supported and should be preserved.

**Evidence/result:** S1 p. 186 and **S17 p. 196** both print Flash Pulse / Pulso
Flash with STUN/Aturdidora, **one BTS/PB Saving Roll**, and the separate
**Non-Lethal/No Letal** and **State: Stunned/Estado: Aturdido** Traits. The
English archived Weapon Chart 4083 and Army S6 weapon 72 agree. Spanish Wiki
revision 3987, timestamp **2026-08-27T14:20:08Z** from S21, instead prints two
PB rolls and omits the State Trait. S1 p. 96 and S17 p. 99 explicitly preserve
failed-save Stunned under Immunity (BTS/PB). Thus the *PDF-language* comparison
is resolved; the **Spanish Wiki publication discrepancy** is not. The Wiki
revision being later than the PDF's creation metadata does not establish a
superseding official rule or prove the reason for the difference.

**Action:** Preserve the verified one-BTS-save curated explanation and cite
both language PDFs plus the Immunity exception. Document the Spanish Wiki
conflict as a separate source issue and seek an official Wiki correction or
erratum where feasible. **Fix:** evidence/source-note maintenance only unless
later authoritative evidence changes the result. **Dependencies:** REA-010,
REA-029. Do not infer that every hit automatically Stuns.

### REA-028 - Kobra's two issues require separate source decisions

**Classification:** source discrepancy, clarity. **Severity:** High. **Priority:** P1.
**Evidence:** Two DA saves Explicit; Anti-materiel Unresolved.
**Affected:** `weapon:kobra-pistol`, `weapon:kobra-pistol-cc`,
`ammunition:da`, `trait:anti-materiel`.

**Current:** The CC-specific card already explains two saves while recording
the one-save PDF and missing Anti-materiel. Its source note correctly retains
the disagreement, but puts both the supported roll correction and uncertain
Trait into one secondary paragraph.

**Evidence/result:** S1 pp. 68/182 print DA with one save; DA p. 64 requires
two. S4 chart 4083 and S6 weapon 221 CC show two and Anti-materiel. S3 p. 68
had Shock CC and Normal BS with one save; S11 explicitly changes ammunition
to DA CC / Shock BS. This supports historical supersession and the DA roll
interpretation. Neither the announcement nor DA itself establishes Anti-materiel.

**Action:** Keep the supported two-save explanation; make Trait uncertainty
easy to identify alongside the CC profile and investigate its source history.
Do not change the BS sibling mode. **Fix:** source research/prose/presentation
review, not a guessed profile repair. **Dependencies:** REA-031.

**Follow-up evidence:** Follow-up visual check: S1 p. 182 actually prints CC DA, one save and no
Anti-materiel; extraction was not the cause. S6/S4 corroborate two DA saves;
that stronger mechanical interpretation does not adjudicate Anti-materiel.
The edition, mode and Trait decisions remain separate.

### REA-029 - The collections' exact Wiki archive is unavailable locally

**Classification:** source discrepancy, completeness of evidence. **Severity:** Medium.
**Priority:** P1. **Evidence:** Observed missing file; high confidence.
**Affected:** C/H source `wiki-en-20260918-130233` and 72 citing records.

**Current:** Both collections identify an 812-member ZIP acquired 2026-09-18
13:02:33 +02:00, expected SHA-256
`aa407f1959fbaafce98058acf507640cc94bfc2690d4a7519a547caf1492f23a`.
`data/wiki/WIKI-en 20260918-130233.zip` does not exist in this checkout.

**Evidence/result:** The JSON locators and filesystem enumeration establish
the mismatch. S4/S5 are real later archives with different hashes. S4 can
reproduce selected oldid content; it cannot prove all September 18 members.
Rules JSON validity or a database build does not establish archive availability.

**Action:** Recover the exact ZIP and verify hash/member identity, or conduct
a deliberate re-review against a new selected source. Never just rename or
replace the path. **Fix:** acquisition/evidence follow-up; curated provenance
only after review. **Dependencies:** limits H and Ammunition evidence, and
REA-027; it is an environment/evidence gap, not proof that 72 rules are wrong.

**Follow-up evidence:** Follow-up provenance: the ignored September 18 acquisition manifest was
located and its expected ZIP hash agrees with C/H. The ZIP itself is still absent.
No artifact mismatch or recovery was claimed; 72 records / 74 citations retain
their original dependency. S14 is separately identified Spanish evidence and
neither it nor S4/S5 repairs the missing English capture.

### REA-030 - FAQ publication and scenario applicability remain uncurated

**Classification:** completeness, source discrepancy. **Severity:** Medium.
**Priority:** P1. **Evidence:** Publication absence Observed; FAQ outcomes
Explicit within their scope; core applicability of ITS-only answers Unresolved.
**Affected:** C/H sources; `rule:scenario:killing`, `rule:scenario:carrying-supply-boxes`,
`rule:peripheral-type:ancillary`, `scenario:annihilation`, `scenario:firefight`.

**Current:** Neither collection registers S2 or FAQ-ruling records. Core Killing
counts undeployed Troopers as killed; Ancillary does not state an exception.
The core Supply Box rule says only Models carry boxes, without spelling out
the attempted Marker-State transition.

**Evidence/result:** S2 printed p. 4 exempts an undeployed Ancillary from Killed
objectives. Page 3 says a scenario-element carrier cannot enter Marker State.
Both are under the **ITS** heading. They are not automatically core amendments.
S1 pp. 150/155 establish core Killing; p. 153 forbids Marker carriers. The core
restriction is a useful baseline, but the FAQ's publication and applicable
mission/season need review before asserting its full scope.

**Action:** Register/pin the FAQ publication in a future batch, classify each
ruling, and decide applicability explicitly. Present the Ancillary question
as unresolved for core until that decision. **Fix:** source/collection/scoped
content and links. **Dependencies:** REA-007, REA-008, REA-016, REA-017,
REA-020, REA-023. No ITS-only wording was applied to core data here.

**Follow-up evidence:** Follow-up compared all English FAQ v0.0/v0.1 pages: 28 common Q&A blocks
and nine additions account for 37 current blocks (eight outside ITS, one ITS).
No material answer change in the common blocks was observed. The new Ancillary
scoring answer is under ITS; core-scenario applicability remains unresolved.
S16 Season 18 pp. 26/28 confirms the scoped ordinary Spec-Ops ban versus TEAM-OPS;
this does not establish all historical/core ITS applicability. Publication date
remains unverified despite PDF creation metadata and the notice's release context.

### REA-031 - Kobra's CC Attribute link points to the Weapon Trait

**Classification:** clarity, semantic-link consistency. **Severity:** Low.
**Priority:** P2. **Evidence:** Observed authored token; Explicit domain distinction.
**Affected:** `weapon:kobra-pistol`.

**Current:** Its phrase naming the Trooper's CC Attribute uses
`[[trait:cc|CC]]`, which resolves to the Weapon Trait rather than `attribute:cc`.
The token is resolvable but semantically wrong for that sentence.

**Evidence/result:** S1 pp. 9 and 68 distinguish the CC Attribute used by a
Trooper from the weapon's CC Trait. Token validation cannot infer author intent.
**Action:** Link the Attribute at that occurrence and retain Trait links where
they describe Weapon classification. **Fix:** semantic token change and a
contextual link check. **Dependencies:** REA-028; no reviewed-plain exception
needs to be broadened or weakened.

### REA-032 - Profile-changing and assignable families lack actionable qualifiers

**Classification:** completeness, clarity. **Severity:** Medium. **Priority:** P1.
**Evidence:** Explicit; high confidence. **Affected:** `skill:super-jump`,
`skill:transmutation`, `equipment:ai-motorcycle`, `equipment:escape-system`,
`equipment:symbiomate`, Label `assignable-transmutation`.

**Current:** Super-Jump omits Jet Propulsion's different trajectory permission;
Transmutation omits after-Guts timing for threshold changes; AI Motorcycle
omits the contact requirement to mount. Assignable's label omits deployment-only
assignment, Model form and one-per-type limits. Some broad summaries correctly
name the family without enough information to apply its particular variant.

**Evidence/result:** S1 pp. 113-114 define Jet Propulsion; pp. 117-118 put
threshold changes after Guts and retain applicable States. Page 119 requires
contact with the Peripheral to remount, separately from its State restrictions.
Page 174 defines assignment eligibility/timing. SymbioMate p. 126 confirms
ARM/BTS 9, Comms without Enhanced, single-Order duration and PARA's different
Attribute. Its simultaneous DA/Forward Observer example is an explicit
weapon-scoped outcome, not permission to invent universal no-save Immunity.

**Action:** Split modes/variants into linked paragraphs; add assignment and
transition qualifiers. **Fix:** text/links, variant data only after review.
**Dependencies:** REA-010, REA-017, REA-019, REA-023.

### REA-033 - Reviewed graph status cannot stand in for explanation acceptance

**Classification:** completeness of review, consistency. **Severity:** Medium.
**Priority:** P1. **Evidence:** Observed ledger/output; high confidence.
**Affected:** `rules-interactions/reviews.json`, `catalog-scope.json`,
the generated checklist, records covered by REA-001 through REA-026.

**Current:** Engineer, Doctor, Peripheral, Continuous Damage, BS Weapon (WIP),
and Fireteam General are reviewed under historical releases despite the
explanation gaps above. The audit reports 182/182 primary catalog complete;
supporting content still has 15 pending identities. No A-F explanation score
is implied by its validation contract.

**Evidence/result:** Read-only checklist verification passed with 314 relations
and 113 future candidates. The new explanation contract requires reasoning,
not merely graph membership. Source-native distinctions and deferred precise
edges remain useful; a deferred edge does not forbid an existing prose explanation.

**Action:** During implementation, record case/record-level explanation review
evidence and deliberately reconcile historical deferrals with the 1.0 gate.
Reuse existing fields/checklists where sufficient before proposing schema work.
**Fix:** future review policy/evidence/validation, not retroactive blanket
"reviewed" flags. **Dependencies:** all material content batches; this finding
is not counted as a second gameplay defect for each affected card.

### REA-034 - The printed Fireteam Level 3 example includes a Level 4 bonus

**Classification:** source discrepancy. **Severity:** Medium. **Priority:** P1.
**Evidence:** Internal contradiction Explicit in both language PDFs; intended
editorial correction Unresolved.
**Affected:** `rule:fireteam-level-bonuses`, source Fireteam examples.

**Current:** C follows the Fireteam Level table, which grants +1 BS at Level 4.

**Evidence/result:** English S1 p. 138 and Spanish S17 p. 142 both describe a
three-Morat/equivalent-members example as **Level 3**, then include **+1 BS/CD**
in its bonus list; each language's Fireteam tables place that modifier at
**Level 4** (S1 pp. 135-136; S17 pp. 139-140). The Spanish Wiki example 3443
also repeats the misleading example. Agreement between PDFs confirms the
publication contradiction, not entitlement to an extra bonus.

**Action:** Keep the table-based interpretation with a scoped explanation of
the conflicting examples; seek an official correction if practical.
**Fix:** citation/source note after acceptance; do not alter the derived
Fireteam Level for the example. **Dependencies:** REA-020/021. Not a confirmed
curated-level-table defect.

### REA-035 - Impersonation-2's "unmodified" Discover wording overstates the exception

**Classification:** correctness, clarity. **Severity:** High. **Priority:** P0.
**Evidence:** Explicit rules combined; high confidence.
**Affected:** `state:impersonation-2`, `state:impersonation-1`, `skill:discover`,
`equipment:biometric-visor`.

**Current:** IMP-2's summary calls its successful Discover roll unmodified.
The Discover card delegates MODs generally, without explaining its own Range
bands or the distinction between no IMP-1 penalty and no modifiers at all.

**Evidence/result:** S1 p. 77 applies Discover's Range/Cover/Mimetism rules.
Page 166 supplies IMP-1's -3 and no equivalent IMP-2 State penalty; it does not
erase ordinary Discover MODs. Page 167's multiple-success example changes IMP-1
only to IMP-2. Biometric Visor p. 120 explicitly bypasses that ordinary
two-stage transition.

**Action:** Say "without IMP-1's -3 State penalty" and explain ordinary MODs,
the failed-attempt limit, two-stage discovery and Biometric's exception.
**Fix:** text/links and future regression examples. **Dependencies:** REA-015,
REA-026; do not label every IMP-2 Discover roll as flat WIP.

### REA-036 - Deployable Cover names a cap without giving its value or conditions

**Classification:** completeness. **Severity:** High. **Priority:** P1.
**Evidence:** Explicit; high confidence. **Affected:** `equipment:deployable-cover`,
`skill:place-deployable`, Cover reference.

**Current:** Vitroferro provides +6 "subject to the documented cap," but the
record contains no cap, contact/obscuration condition, or non-stacking explanation.
The player cannot determine the save from the curated card.

**Evidence/result:** S1 p. 122 requires Silhouette contact and applicable
Partial Cover geometry. Cap ARM/BTS plus saving MODs at 12, **then** add PS.
The saving benefit does not stack with another scenery Partial Cover bonus.
Profile-listed variants constrain the choice. S2 p. 2 says nothing may be
placed on or end movement on the Cover; that restriction needs its FAQ scope.

**Action:** Give the exact cap order and conditions, with a short calculation
example, retaining ordinary Cover as a separate selectable benefit.
**Fix:** text/links and optionally reviewed facts. **Dependencies:** REA-023,
REA-026, REA-030; do not cap the final PS-inclusive Success Value at 12.

**Follow-up evidence:** S1 p. 122 also identifies Disposable (2) and Perimeter.
The authored Deployable Cover definition states ZoC placement but omits those
explicit properties; review their player-visible ownership with the cap and
placement baseline, rather than assuming a named metadata profile supplies them.

### REA-037 - Armed Turret has conflicting Silhouette values within the PDF

**Classification:** source discrepancy. **Severity:** Medium. **Priority:** P1.
**Evidence:** Both values Explicit in both N5.3 PDFs; precedence Unresolved.
**Affected:** `weapon:armed-turret`, `facts.specialProfile`.

**Current:** C's detailed profile uses S2, citing English S1 p. 70; it omits
the conflict with the summary tables.

**Evidence/result:** English S1 p. 70 and Spanish S17 p. 74 both give the
**detailed** Armed Turret/Torreta Artillada profile **S2**. Both languages'
**deployable summary** tables give **S1** (S1 pp. 74/195; S17 pp. 74/203).
The Spanish Wiki detailed Turret revision 3754 also gives S2. S1 p. 18 shows
S1 and S2 share a 25-mm base, but differ in height (25 versus 40 mm), affecting
LoF/clearance. Neither language's table resolves the disagreement.

**Action:** Preserve the S2 detailed-profile provenance and mark the conflict
rather than silently changing the stat. Seek an applicable official erratum;
**do not** assume either the detailed profile or summary always prevails.
**Fix:** source research and a visible note following review.
**Dependencies:** REA-023.

### REA-038 - Direct Doctor/Engineer target allegiance is not established

**Classification:** correctness risk, completeness of evidence. **Severity:** High.
**Priority:** P0 source decision. **Evidence:** Explicit scoped clauses;
universal direct non-Allied eligibility Unresolved. **Confidence:** High about
the unsupported qualifier, limited about unexamined scenario exceptions.
**Affected:** C `skill:doctor`, `skill:engineer`, `equipment:medikit`,
`equipment:gizmokit`, `skill:peripheral`, `state:engaged`, `state:stunned`.

**Current:** Both direct Skill requirements add a friendly target gate. REA-001
and REA-002 originally retained Allied wording in proposed examples without
separately proving it. This could preserve an unsupported restriction.

**Evidence and reasoning:** S1 pp. 90-91 and exact English Wiki Doctor 3979 /
Engineer 3980 specify contact and the relevant recovery conditions, without
a universal Allied-only requirement. Spanish S14 `es/Medico` 3822 and
`es/Ingeniero` 3823 have the same structural distinction. S1 pp. 123-124 explicitly
require Allied Models for Kits; pp. 106-107 explicitly require an Allied Model
for delegated Servant/Cyberplug treatment. These are local clauses, not a global
Doctor/Engineer prerequisite.

General target terminology/alignment (p. 173) defines ownership; it does not
make every Skill Allied-only. The Attack prohibition (p. 174) governs Attacks,
while Doctor/Engineer are Optional Short Skills without the Attack Label.
Declaration checks (pp. 14-15) enforce the selected Skill's requirements but do
not supply a general friendly gate. However, p. 51's **Interacting with a Close
Combat** expressly bars Doctor/Engineer on an Engaged target in that contact
situation; p. 160 separately restricts an acting Trooper's Engaged declarations.
Engaged activation on p. 160 requires neither contact participant to be
Immobilized or Null, except that Sepsitorized/Possessed still allow Engaged.
Thus ordinary enemy contact can prohibit the acting Doctor/Engineer, while
contact with an ordinary Unconscious or Immobilized enemy does not itself
activate Engaged. These are explicit State conditions supporting contextual
eligibility reasoning, not an explicit universal enemy-treatment ruling.

| Target/use category | Evidence disposition |
| --- | --- |
| Allied Kit target and Allied Peripheral-mediated treatment | Explicit local permissions when requirements are met; non-Allied use fails their express gate |
| Self-use outside Null with an applicable effect | Explicit on pp. 90-91; self-use in Null prohibited; NWI supplies its specific exception |
| Prohibited Engaged interaction | Explicit prohibition on pp. 51/160; allegiance does not remove it |
| Contact with an ordinary non-Null, non-Immobilized enemy Trooper | General Engaged activation supplies the declaration restriction; do not treat an absence of Allied wording as permission |
| Direct eligible Allied target | Supported by requirements and official Allied examples; State/Attribute/contact still apply |
| Direct non-Allied Unconscious/Immobilized/State target | No universal friendly prohibition found in checked general rules; permissive reading is Derived from their requirements, not an explicit universal ruling |
| Hostile/Neutral or scenario-specific target | Unresolved without the actual scenario/profile/target rules; not inferred from silence |

**Expected interpretation/action:** Treat the universal qualifier as unverified.
Find a scoped official ruling or explicitly accept a documented derived decision
before widening/removing it. Separate Wound removal from State cancellation,
direct from delegated use, and all of these from Engaged restrictions.
**Fix:** source review, then text/links/validation if accepted.
**Dependencies:** REA-001/002/009/017/022. No accepted rules semantics are changed
and not every enemy is declared a legal treatment target.
**1.0 relevance:** Adjudicate this qualifier before accepting the complete
target-eligibility explanation; confirmed recovery clauses can proceed separately.

### REA-039 - TinBot omits operational eligibility and Fireteam sharing

**Classification:** completeness, consistency. **Severity:** High. **Priority:** P1.
**Evidence:** Explicit; high confidence. **Affected:** C `equipment:tinbot`
and all six `equipment:tinbot-*` variants, `rule:fireteam-general`.

**Current:** Family/variant text covers only the listed benefit, omitting
owner Isolated/Null eligibility, Fireteam sharing, token nature and stacking.
Two correct variant identities do not explain who benefits or whether buffs stack.

**Evidence/result:** S1 p. 127 requires the owner not be Null or Isolated;
TinBot representations are State Tokens, do not block LoF/movement and cannot
be targeted. Every Fireteam member benefits when the owner belongs to it.
Identical advantages are used only once per Order/ARO; differing MODs to the
same advantage use the most advantageous one. Each listed benefit still comes
from the specific option/profile, not a universal union of variants.

**Action:** Add one family baseline and linked variant conditions; connect
Firewall without duplicating it. **Fix:** text/links and focused validation/
presentation if needed. **Dependencies:** REA-018/020. Future cases should cover
owner Isolation, membership loss, shared Firewall, identical buffs and different strengths.
**1.0 relevance:** TinBot is supported Equipment; its shared/disabled conditions
are material to gameplay, independently of optional exhaustive variant research.

### REA-040 - Infinity Spec-Ops links an absent SpecBall procedure

**Classification:** completeness, scope/provenance. **Severity:** High. **Priority:** P1.
**Evidence:** Explicit; high confidence about absence and printed mechanics.
**Affected:** C `skill:infinity-spec-ops`; absent `skill:request-specball` owner;
profile transitions and Marker cancellation.

**Current:** Customization and enhanced-profile collection are described,
but no definition explains Request SpecBall. The deferred ledger knows its
endpoint; a plain name is not an adequate explanation.

**Evidence/result:** S1 p. 98 requires a non-Null Spec-Ops Trooper, Active Turn
in Game Round 2 or 3, one use per game, a 55 mm token/PH 15 drop outside the
Order sequence, and two different items. Allied non-Null Spec-Ops pickup cancels
Marker State, applies the Enhanced Profile at the end of the Order, retains
Wounds/applicable States, and places a chosen SpecBot in contact. The effect
intro says Speedball within the SpecBall rule: retain this apparent copy error
as evidence rather than treating the two procedures as interchangeable.

S16 pp. 26/28 confirms that ordinary Spec-Ops is prohibited in Season 18
tournaments; TEAM-OPS is a separate optional Extra and does not permit this Skill.
That is scoped Season 18 evidence, not an eternal rule of the core edition.

**Action:** Supply the core procedure/reference and needed item links; pin the
ITS restriction separately. No full tournament tool is needed. **Fix:** curated
identity/text/links and publication after review. **Dependencies:** REA-015/023/
026/030/032. Future tests distinguish SpecBall, Speedball and TEAM-OPS Tacball,
and cover round, Null and once-per-game conditions.
**1.0 relevance:** Explain the supported new core procedure; complete ITS season
tools and all customization options are outside this focused requirement.

### REA-041 - Spanish Fireteam dice reminder conflicts with its general SD rule

**Classification:** source discrepancy. **Severity:** High. **Priority:** P1.
**Evidence:** Contradiction Explicit within official Spanish N5.3 PDF;
precedence/erratum Unresolved. **Confidence:** High about source contents.
**Affected:** `rule:fireteam-level-bonuses`, `skill:martial-arts`, SD baseline.

**Current:** English S1 pp. 75/136 and the current curated explanation separate
Burst from Special Dice and do not count +1 SD toward the six-Burst cap.

**Evidence/result:** Spanish S17 p. 75 explicitly excludes +1DE from the
maximum **Ráfaga 6** because extra Special Dice do not increase Burst. Yet
S17 p. 140, in the Fireteam section, says the maximum of six **dice** includes
extra dice from Skills, MODs, and bonuses. The contradiction is therefore
present **within the Spanish PDF itself**, not merely between a Spanish Wiki
page and English PDF. Spanish Wiki revision 4012 (2026-09-08) reflects the
exclusion and Fireteam bonuses revision 3918 (2025-11-28) retains the
inclusive reminder; these are separate publications with different dates.
English S1 consistently distinguishes Burst and SD, and FAQ S2 p. 2 confirms
SD does not change Burst for Coordinated Orders. Neither establishes why the
Spanish Fireteam reminder was retained.

**Action:** Keep the evidenced Burst-versus-SD baseline for now, visibly
register the Spanish PDF contradiction, and seek a scoped official erratum.
Do not invent a Fireteam-specific dice cap by inference. **Fix:** evidence and
reviewed source note after adjudication. **Dependencies:** REA-021/029/034.
**1.0 relevance:** Player explanations should be clear about the adopted
sourced interpretation and outstanding source contradiction.

### REA-042 - Dodge (ARM+3) has incompatible English/Spanish conditions

**Classification:** source discrepancy, completeness. **Severity:** High.
**Priority:** P1. **Evidence:** PDF/Wiki conflict Explicit; cause Unresolved.
**Confidence:** High about compared clauses. **Affected:** `skill:dodge`,
modifier baseline REA-026 and profile-listed Dodge (ARM+3).

**Current:** No complete curated explanation defines this parameter's effect.
A generic +3-to-Dodge-PH explanation or an undocumented conditional rule would
be misleading.

**Evidence/result:** **Both N5.3 PDFs agree:** English S1 p. 75 says Dodge
(ARM+3) always provides +3 ARM when Dodge is declared and the relevant Saving
Roll occurs; Spanish S17 p. 75 says Esquivar (BLI+3) *siempre* gives +3 BLI
when Esquivar is declared. Spanish Wiki revision 4012 (timestamp
2026-09-08T10:04:10Z in S21) instead uses a condition involving a failed PH
roll in a May-update paragraph. Thus this is no longer an unverified bilingual
PDF alignment; it is a **Spanish Wiki-versus-two-PDF** conflict. That Wiki
revision postdates the PDFs' creation metadata, but no explicit supersession
or erratum was verified.

**Action:** Preserve the common PDF-based interpretation as supported while
recording the Wiki conflict; seek a scoped correction/erratum. Future prose
must distinguish Dodge PH, ARM/BLI protection, failed rolls and simultaneous
Order resolution. **Fix:** evidence, then modifier text/links and focused
regressions. **Dependencies:** REA-014/026. Do not infer a universal ordinary
Dodge ARM bonus.
**1.0 relevance:** A sourced player-facing conditional explanation remains
necessary; the upstream discrepancy should be visible rather than hidden.

### REA-043 - Counterintelligence gives the relaxed limit to the wrong player

**Classification:** correctness, clarity. **Severity:** High. **Priority:** P0.
**Evidence:** Explicit clauses combined; high confidence. **Affected:** C
`skill:counterintelligence`, `rule:command-token-strategic-use`.

**Current:** Its alternative effect increases the Command Tokens the **adversary**
may use to two, reversing who benefits.

**Evidence/result:** S1 p. 128 lets the second-turn player limit the opponent's
first-turn Command Tokens to one. Counterintelligence p. 90 counteracts the
limit imposed by the adversary, allowing the affected player's allowance of two.
The other option separately reduces the adversary's Order removal from two to
one. Neither grants that adversary an extra allowance.

**Action:** Explain both options from the correct perspectives. Proposed text:
when your opponent limits your first-turn Command Tokens, Counterintelligence
lets you use two instead of one. Preserve timing and the separate Order-removal
option. **Fix:** text/links and a future actor/timing regression. **Dependencies:**
REA-026 for the shared Strategic Use baseline; no unresolved source conflict is needed.
**1.0 relevance:** Confirmed wrong beneficiary is a P0 gameplay correction and
can be the smallest independent first implementation slice.

### REA-044 - Breaker Marksman is metadata-only despite its current official profile

**Classification:** completeness, presentation; supplementary source terminology.
**Severity:** High. **Priority:** P1. **Evidence:** Official profile Explicit;
publication absence Observed; notice terminology reconciliation Derived.
**Confidence:** High about the examined runtime baseline. **Affected:** Army
Weapon source 225, public Weapons domain; no corresponding C definition.

**Current:** S6 preserves Breaker Marksman Rifle (AP, BTS/2, PS 7, B3, one save,
Suppressive Fire), but the application identity graph/getter does not publish
it. Numeric 225 and slug lookups return None. This is preserved-but-inaccessible
content, not a missing source profile.

**Evidence/result:** Rendered S1 p. 180 shows the new blue Marksman row; p. 185
has no distinct Breaker Sniper row. S14's matching profile is under FUSILES DE
PRECISIÓN, separate from Francotirador/Sniper. S13 names that Spanish weapon;
S11 calls it Breaker Sniper Rifle. Matched profiles and sections support a notice
translation interpretation, not inventing a second Sniper or aliasing by name
alone. S20's embedded metadata pins S6. Read-only central resolver, list and
getter confirm the publication gap; no browser was launched.

**Action:** Review a current metadata-only Weapon publication slice with explicit
profile/provenance and without requiring a referencing Army Unit. Keep unused
historical metadata separately scoped, instead of publishing every legacy row.
**Fix:** future processing/backend/reference publication and validation.
**Dependencies:** source completeness and REA-026. Do not fabricate raw Army
fields or an unsupported Sniper statline.
**1.0 relevance:** The current supported Weapon reference needs this preserved
official profile to be reachable; publishing every unused historical row is not required.

## Flash Pulse benchmark and positive findings

The benchmark is source-verified, with a remaining profile discrepancy:

1. S1 p. 186 / S4 chart 4083 / S6 weapon 72: Flash Pulse uses STUN, one BTS
   save per hit, Non-Lethal and State: Stunned.
2. S1 p. 95: matching Immunity (BTS) treats covered Ammunition as Normal;
   this is not an instruction to substitute ARM for the Weapon's BTS save.
3. That rule separately protects against applicable State/Wound/Attribute Traits.
4. Its IMPORTANT clause excludes Non-Lethal and State: Stunned from that protection.
5. S1 p. 96 Example 4: a failed save still Stuns, with no Wounds. A successful
   save does not Stun. S7 revision 3677 corroborates the result in Spanish.
6. Critical handling remains separately qualified by Immunity (Critical).

**Proposed concise explanation, for later curation:** Against Flash Pulse,
Immunity (BTS) leaves a BTS save; failure causes Stunned and no Wounds.
Flash Pulse's STUN becomes Normal, but its save Attribute does not change.
Although this Immunity ordinarily protects against applicable harmful Traits,
the IMPORTANT clause explicitly preserves Non-Lethal and State: Stunned.
The State still requires a failed save.

This proposal is not a data edit. REA-010 owns its missing ordinary-rule
sentence; REA-027 owns the Spanish chart investigation. Do not infer other
BTS weapon results or eliminate STUN's separate Guts rule by analogy without
checking whether that effect survives the particular Immunity.

| Preserve this pattern | Checked evidence | Why it helps |
| --- | --- | --- |
| Non-Lethal separates Wounds from non-Wound saves | C `trait:non-lethal`; S1 p. 175 plus Carbonite/PARA clauses | Avoids treating "non-lethal" as "no Saving Roll" universally |
| Partial AP Immunity keeps DA's multiplicity and labels the result Derived | C Immunity effects/case; S1 pp. 64, 67, 95; S4 3000/3643 | Correct reasoning without claiming a separately printed ruling |
| Vulnerability (Viral) is weapon-name-scoped | C `skill:vulnerability`; S1 p. 118; S4 3156 | Does not fabricate a Viral Ammunition component |
| E/M's failed-save and target-Type predicates | C `ammunition:em`; S1 p. 64 | Isolated versus additional IMM-B stays conditional |
| PARA explicitly handles absent PH | C `ammunition:para`; S1 p. 65 | Avoids forcing a meaningless roll on a target without that Attribute |
| T2 distinguishes ordinary and extra-Critical Wounds | C `ammunition:t2`; S1 p. 67 | Correct stored exception; add the die-identification instruction |
| Baggage and Reload state both participants' eligibility | C both records; S1 pp. 83, 120, 172 | Preserves Non-Null, range, Non-Reloadable, and already-deployed-item limits |
| Explode lists direct-Dead, Dogged/NWI, and allied-template exceptions | C `skill:explode`; S1 p. 92 | Explicit timing and exceptional outcomes, not just a Dead edge |
| Technorganic and Tech-Recovery keep Unconscious scope separate | C both records; S1 pp. 115-116 | Recovery cross-Attribute permission is not universal |
| Mines, Cybermines, Chest Mines and Drop Bears have distinct owners | C weapon family/exception records; S1 pp. 71-72/181 | Shared placement is not shared effect resolution; Cybermine uses Reset |
| WildParrot is an E/M Mine exception, not Boost | C `weapon:wildparrot`; S1 pp. 69/74/181 | Retains visible Token placement and its own trigger mechanics |
| Cube 2.0 links both Sepsitor variants | C Cube/Sepsitor records; S1 pp. 73/121/187 | +2 save protection remains distinct from target eligibility |
| Aerial states the Boost and Guard exceptions | C `skill:aerial`; S1 p. 86; S2 p. 2 | Contact prohibition is linked to actual specific outcomes |
| No Cover overrides Limited Cover, but Marksmanship only removes attack MODs | C those Skills; S1 pp. 100/104/41 | Does not erase unrelated saving protection |
| Scenario exceptions are explicitly scoped | C Specialist baseline, Domination/Firefight rules; S1 pp. 151-155 | Non Specialist Chain of Command does not exclude other qualifying Skills; Peripheral objective use stays restricted |
| Scenario source issues remain visible in maintained facts | C Domination 350-point SWC and Annihilation survival bands; S1 pp. 149/151 | Domination's printed 6 is preserved; Annihilation's correction is labeled a reviewed interpretation |

Positive cases are selected clause reviews, not certifications of every variant
or their real-browser rendering. In particular, preserving a source disagreement
is positive provenance behavior, not proof that the disagreement is settled.

## Interaction-family coverage

Each row records an investigation, not all mathematically possible rule pairs.
The families deliberately overlap when an outcome needs several rules.

| Family | Reviewed examples and ordinary/modifying/exception chain | Findings / residual scope |
| --- | --- | --- |
| 1. Immunity, Traits, States, Vulnerability | Flash Pulse; Monofilament; Plasma; Viral name exception; Comms exclusion | REA-004, REA-010, REA-011, REA-024, REA-027; other partial Immunities not generalized |
| 2. Combined Ammunition versus combined saves | AP+DA, AP+EXP, AP+T2 component handling; N+E/M; Plasma ARM+BTS | REA-011, REA-013, REA-025; arbitrary mixed-Attribute Immunity unresolved |
| 3. Criticals, multiplicity, persistent damage | DA 2+1; EXP 3+1; T2 2/1 Wounds; Continuous Damage extra-roll exclusion | REA-004, REA-013; all weapon-specific Critical interactions not exhaustively checked |
| 4. Recovery, prevention, incapacitation | Doctor/Engineer branches; Kits; NWI/Dogged; Remote Presence; Technorganic; Exrah/Explode | REA-001, REA-002, REA-009, REA-022; combined recovery methods/variants need focused follow-up |
| 5. Cumulative States and cancellation | IMM-B + Isolated + Targeted; successful Dodge/Reset; Engaged position; Prone recovery | REA-014, REA-015, REA-035; all scenario-created State sources not covered |
| 6. Hacking targets and defenses | Carbonite/Oblivion OR Hacker eligibility; Spotlight non-Hackable targeting; Total Control; Zero Pain; Repeater/Firewall | REA-005, REA-018, REA-026; Non-Hackable plus independent Hacker eligibility needs further scoped examples |
| 7. Sustained effects and NFB | Assisted Fire, Enhanced Reaction, Fairy Dust replacement; Cybermask; White Noise | REA-018, REA-019; Enhanced Reaction plus Total Reaction precedence not adjudicated |
| 8. Smoke, Eclipse, MSV, Sixth Sense | Rolled LoF attacks; MSV exception; Reflective Eclipse; White Noise; targeted MSV1/Sixth Sense FAQ | REA-012, REA-019; all scenery geometries not visually checked |
| 9. Cover, Attribute substitution, MOD precedence | Marksmanship/Nanoscreen; No/Limited Cover; PH/WIP weapons; Vitroferro cap | REA-005, REA-021, REA-036; Cover/Nanoscreen stacking combinations not fully adjudicated |
| 10. Declaration and simultaneous timing | Intuitive WIP; positive-before-negative recovery; Idle; Controlled Jump immediate ARO | REA-003, REA-006, REA-009, REA-026; no complete declaration matrix built |
| 11. Movement and contact restrictions | Dodge movement; Prone/Berserk; Aerial/Guard; Motorcycle; Climbing Plus; Jet Propulsion | REA-014, REA-032; movement geometry and complete mixed-Skill activation remain partially reviewed |
| 12. Deployment and item placement | Minelayer; superior-deployment failure; Perimeter path; Drop Bears; Firefight landing +3; Speedballs | REA-007, REA-023; deployment repositioning FAQ and all exclusion-zone cases need a dedicated batch |
| 13. Fireteam creation, action, integrity | Type/Level distinction; chart equivalence; FT Master; Number 2; NCO/Tactical Orders; Ancillary | REA-017, REA-020, REA-034; every Army chart's special notes not audited here |
| 14. Burst, SD, charges and multiple Kit hits | Martial Arts/Fireteam SD; ranged Kits; Double Shot; shared mode uses | REA-021, REA-022; no arbitrary Burst calculator inferred |
| 15. Peripherals and profile transitions | Five subtype baselines; Cyberplug exceptions; AI Motorcycle; Transmutation; SymbioMate | REA-017, REA-032; all Unit-backed Peripheral identity decisions outside this explanation audit |
| 16. Deployables and named Weapon families | Mines/Cybermine/Chest Mine; WildParrot; Armed Turret; delivery objects | REA-023, REA-024, REA-037; D-Charges, Disco Baller/activation, Mine Dispenser, Pitcher and SymbioBomb have no dedicated C definitions and need an owner/publication review |
| 17. Orders, command, morale and glossary | Regular/Irregular/Tactical/Lieutenant; Strategos/NCO; Courage/Religious/Warhorse; Protheion and Victory Points | REA-008, REA-026; full Strategic/Executive/Operational Command procedures, Retreat thresholds and list choices remain incomplete |
| 18. Scenarios and general-rule exceptions | Four core missions; Specialist restrictions; Shasvastii scoring; Killing; Supply Box carrier; Firefight deployment | REA-030; 20 components screened, map visuals not reaccepted, ITS library/reinforcement annex not certified |

**Relationships found beyond the existing queue:** the actual clauses expose
Continuous Damage's extra-Critical exception, Controlled Jump's same-declaration
timing/opposing-program cancellation, Speedball exclusion, Protheion overkill,
same-Order Kit aggregation, IMP-2's ordinary Discover MODs, Vitroferro's precise
cap, and the Armed Turret S discrepancy. These are more specific than a generic
relation endpoint. By contrast, BioWeapon's DA/Shock reuse and BS Weapon (WIP)'s
prohibited combinations were already deferred; this report discovers missing
**explanations**, not new knowledge of those queued relationships.

## Source discrepancies and dispositions

"Resolved" means the scoped interpretation is established by checked evidence,
not that every upstream file has been corrected. "Likely resolved" retains an
unverified inference. "Unresolved" preserves the actual competing claims.

| Case | Sources/values | Disposition and consequence |
| --- | --- | --- |
| Flash Pulse saves and State Trait | S1 p. 186 and S17 p. 196: one BTS/PB save, Non-Lethal and State: Stunned; Spanish Wiki S8/S21 3987: two PB saves without State Trait | **Current PDF baseline verified in both languages**; **Spanish Wiki publication conflict remains**, REA-027; Immunity example in both PDFs confirms failed-save Stunned |
| Kobra CC save count | S1 pp. 68/182: DA, one save; DA p. 64 / S4 4083 / S6: two | **Resolved interpretation**: DA requires two; preserve contradictory chart bytes. S3/S11 establish ammunition change, not an independently published chart correction |
| Kobra Anti-materiel | S1 omits; S4/S6 include | **Unresolved**, REA-028; DA is insufficient evidence for this Trait |
| Fireteam Level 3 example | S1 p. 138 and S17 p. 142 include Level 4 +1 BS/CD in a Level 3 example; both languages' tables place it at Level 4 | **Confirmed within-PDF contradiction in both languages; intended correction unresolved**, REA-034 |
| Armed Turret Silhouette | S1 detailed p. 70 / S17 detailed p. 74: S2; S1 summaries pp. 74/195 / S17 summaries pp. 74/203: S1 | **Confirmed within-PDF conflict in both languages; precedence unresolved**, REA-037; affects silhouette height |
| Direct Doctor/Engineer allegiance | S1/S4/S14 direct requirements lack a universal Allied gate; Kits/delegation explicitly impose it | **Unresolved universal interpretation**, REA-038; no general rule supplying the gate found, no universal enemy permission inferred |
| Spanish Fireteam dice reminder | S17 p. 75 excludes Special Dice from Burst-6; S17 p. 140 Fireteam reminder includes extra dice in six total; S14 Wiki mirrors split | **Confirmed internal contradiction in official Spanish PDF; ruling precedence unresolved**, REA-041; do not invent a separate Fireteam cap |
| Dodge (ARM+3) condition | S1 and S17 p. 75 agree on always +3 ARM/BLI for applicable Saving Rolls when declared; S14/S21 4012 conditions on failed PH | **PDF-language alignment verified; Spanish Wiki publication discrepancy remains**, REA-042; not +3 PH |
| Breaker notice weapon label | English S11 says Sniper; rendered S1 p. 180/S6 225/S14 Spanish section match Marksman | **Derived terminology reconciliation**, REA-044; profile-backed match, no separate Sniper invented; public reference still absent |
| Prone/Berserk | S1 general movement p. 29 excludes Berserk; Prone p. 169 repeats only Jump | **Resolved current exception** by p. 29 and S2 p. 1; record-level Prone prose still needs it in the lifecycle batch |
| Old Kobra ammunition | S3 p. 68: Normal BS / Shock CC; S1/S11: Shock BS / DA CC | **Resolved historical supersession**; do not use the old one-save CC row as current authority |
| Viral one-save profile versus DA+Shock | S1 pp. 174/181 and S6 weapon 63 | **Derived conditional reconciliation**, REA-024: Trait modifies VITA case; not a blanket typo or universal two-save profile |
| PARA Mine footnote | S1/S4 `[*]`; S6 `[**]`; S1 p. 176 defines distinct section meanings | **Unresolved Army reference intent**; existing dual-owner links and note are useful; no new gameplay conclusion |
| WildParrot Non-Lethal | S1 pp. 74/181 lists; S6 omits | **Unresolved source-property discrepancy**, with explicit printed non-Wound effect preserved; do not add Army properties silently |
| Endgame Double Shot | S1 p. 182 lists; S6 omits and retains Technical Weapon | **Printed behavior supported; source mismatch remains**. Existing CC-independent source-specific card preserves it; REA-022 adds remaining-use condition |
| Sepsitor Plus footnote | S1 p. 187 lists `[*]`; Army omits | **Unresolved reference-marker cause**; existing separate Sepsitor Plus card supplies rules without inventing the cause |
| Cybermine alleged missing Comms Attack | S1 pp. 72/181 and maintained source review agree | **Resolved prior extraction error**, not a new missing Trait; retain the corrected seven-line-cell evidence |
| September 18 Wiki archive | C/H require one exact hash/path; only later ZIPs available | **Unresolved local evidence availability**, REA-029; not rules supersession |
| FAQ Ancillary/scenario-element scope | S2 ITS section versus S1 core rules | **Unresolved core applicability**, REA-030; keep ITS rulings distinct |
| Annihilation 350-point survival bands | S1 p. 149 has gap/overlap; C uses contiguous reviewed ranges with an issue note | **Reviewed project resolution, Derived**; no official corrected Spanish/Wiki publication verified here. Preserve accepted decision and label |
| Domination 350-point SWC | S1 p. 151 says 6; other scenario tables say 7; C scenario override says 6 | **Unresolved source intent, faithfully retained**; positive provenance pattern, no normalization proposed |
| Katyusha unsigned range value | Prior maintained RR-SRC-N53-003 / validation mapping describes missing plus | **Previously resolved, not independently reverified here**; retained as prior research, not added to this audit's confirmed findings count |

The official announcement was checked only for its scoped change statements.
Neither an update post nor an unofficial backup is a substitute for the
versioned rule/FAQ/Army source. Spanish comparisons corroborate specific
mechanics; there was no complete bilingual clause audit.

## Current representation and future recommendations

Most urgent explanations fit the existing `summary`, `requirements`, `effects`,
`restrictions`, semantic tokens, relations, and citations. Use short mode/topic
paragraphs: result first, then baseline/modifier/exception and condition. A new
schema is not required merely because a typed graph relation is too coarse.

The closed relations correctly support navigation, not a complete conditional
calculus. For example, `causes-state` cannot carry all of the target-Type/save
conditions of E/M, and `cancels-state` cannot prove Engaged ends without a valid
Dodge move. Keep predicates in the explanation and existing typed facts.
Multi-rule cases need all material participants, not one overstated edge.

The current shared renderer displays requirements/effects/restrictions,
Ammunition mechanics, relation links, source notes, and citations. It does not
render every arbitrary structured fact (REA-011). Fireteam and Army tables have
separate consumers. A proposed structured interaction card with applicability,
before/after, exception and certainty is **future design**, requiring deliberate
schema/API/browser review. The app does not currently provide a universal such
card or resolve combat outcomes.

`facts.sourceNotes` is appropriate for editorial source history. A disagreement
that changes saves, Traits, targets or placement should remain understandable
beside the actionable explanation in normal mode. Do not hide it in Developer
Mode or use a secondary footnote as the only gameplay warning. Actual readability,
small-screen layout, link targets and disclosure require later live acceptance;
source-code inspection here does not prove them.

## Prioritized remediation plan

**Source preflight:** REA-038 must be explicitly adjudicated before accepting
changed direct-target allegiance. The confirmed STR/recovery/roll corrections
can proceed within supported Allied examples without widening eligibility;
their full eligibility closure remains dependent on that decision. REA-043 is
an independently confirmed first-batch actor correction. Recover S18 and adjudicate the **now verified bilingual PDF-versus-Wiki**
conflicts before closing dependent source claims, or accept an explicit scoped
uncertainty/migration disposition with fresh comparison.

These are independently reviewable proposed batches. Future code/JSON/schema
edits, generated outputs and regression tests belong to those tasks, not this
documentation-only audit.

| Batch | Finding IDs | Scope and dependencies | Suggested acceptance / future regression cases |
| --- | --- | --- | --- |
| A. Recovery and Intuitive Attack | REA-001, REA-002, REA-003, REA-009, REA-022, REA-038 | First batch; source-backed mechanics, with allegiance preflight; direct/delegated/self use and Kit ownership stay distinct | VITA Targeted versus Stunned Engineer eligibility; ordinary wounded VITA cannot receive ordinary Doctor healing; failed Doctor versus failed State cancellation; one Intuitive WIP roll/opposed ARO/Main Target Critical; cancellation then new PARA State; mixed Kit PH success/failure; SD does not consume charges; Engaged prohibition; explicit delegated Allied gate; unresolved direct allegiance must not become an accepted universal claim |
| B. Ammunition/Traits and Criticals | REA-004, REA-005, REA-010, REA-013, REA-024, REA-025 | Restore omitted exceptions; add N+E/M owner/map review; keep explicit and Derived examples separate | Ordinary versus extra Continuous Damage save; WIP+Shock prohibition versus ordinary WIP weapon; two whole-ARM cases versus partial AP; Normal+BTS is still BTS; odd defense rounds up; T2 dice designated before saves; N+E/M Wounds/States; Viral VITA/STR comparison |
| C. Hacking, NFB, visibility | REA-006, REA-007, REA-012, REA-018, REA-019 | Shared baseline content then Program-local timing; FAQ scope from F | Immediate Controlled Jump ARO; opposing Programs cancel each other's effects while Firefight +3 remains; Speedball no benefit; one Supportware/Hacker and beneficiary; replacement Fairy Dust example; one chosen Firewall; active versus disabled Device; MSV ordinary Smoke/Eclipse difference; White Noise owner NFB duration |
| D. States, declarations and general baselines | REA-008, REA-014, REA-015, REA-016, REA-026, REA-035 | Reusable baseline references before broad cross-links; preserve per-State differences | IMM-B+Isolated and Targeted/capped MODs; Sixth Sense retained penalties; valid/blocked Engaged exit; simultaneous Mine and gun Dodge; Prone/Berserk and recovery cancellation; Hidden Deployment Order/ARO; Marker full-Order revelation; Stealth mixed activation; IMP-2 Range MOD and IMP-1 multiple successes; Protheion overkill |
| E. Fireteams, Peripherals and placement | REA-017, REA-020, REA-021, REA-023, REA-032, REA-036, REA-039, REA-040 | Common action/placement baselines then subtype/variant exceptions; depends on D for lifecycle context | Controller/Peripheral mixed Idle; Servant and Cyberplug Doctor roll ownership; Ancillary eligibility/recovery; leader versus member departure and Number 2; Haris remains Haris at two members; original profile Training versus FT Master conversion; SD/BS bonuses versus Discover and WIP/PH; Perimeter blocked path; occupied placement fallback; Vitroferro cap before PS; AI remount contact; after-Guts Transmutation; TinBot owner disabled/sharing/identical versus different-strength benefits; SpecBall round/once/Null/Enhanced Profile and Marker conditions; TEAM-OPS scoped separately |
| F. Sources and scoped FAQ | REA-027, REA-028, REA-029, REA-030, REA-034, REA-037, REA-041, REA-042 | Recover S18; integrate verified Spanish PDF/oldid provenance, classify FAQ by scope; adjudicate remaining publication contradictions individually | Exact archive hash/member; verified PDF one-save Flash Pulse versus conflicting Spanish Wiki; Kobra DA separate from Anti-materiel; FAQ Ancillary applicability; bilingual Fireteam Level 3 example; bilingual Armed Turret S2/S1; Spanish PDF internal B6 versus B6+SD reminder; bilingual PDF Dodge modifier versus Spanish Wiki; document any official correction without overriding evidence |
| G. Presentation, links and acceptance evidence | REA-011, REA-031, REA-033 | Follow content decisions; current prose rendering first; optional structured display later | AP+DA before/after conditions visible; Derived versus Explicit labels; correct CC Attribute target; material uncertainty visible in normal mode; keyboard/narrow-screen links and citations; actual explanation review cannot pass solely on graph count |
| H. Command Token actor | REA-043 | Small independent P0 correction; share Strategic Use baseline from D | Opponent imposes limit on user's first turn; Counterintelligence allows user two; separate enemy Order-removal branch and >10 threshold |
| I. Current Weapon publication | REA-044 | Target current metadata-only profiles; source 225 does not require a referencing Unit; no blanket publication of historical rows | Numeric/slug public lookup, matched Marksman profile/ranges, name/source-note visibility; no fabricated Sniper or raw data mutation |

**Potential 1.0 blockers:** confirmed misleading eligibility/roll statements
(REA-001, REA-002, REA-003, REA-035, REA-043) and material omitted exceptions such as
REA-004 through REA-006. Other High findings are potential completeness blockers
when their mechanics belong to the supported player reference; assess them
against `releasing.md`, not their historical ledger target. REA-027/REA-028 need
an explicit supported-source disposition and usable uncertainty; an upstream
unresolved question need not force invented certainty. Archive availability and
FAQ scope need release evidence rather than assumed equivalence.

**Lower priority / post-1.0 candidates:** REA-031's localized token repair is
small but not itself a game-resolution blocker. A generalized interaction
schema, automatic evaluator, exhaustive historical ITS library, session-state
model, interactive editor and every possible combat combination are not
prerequisites for concise source-backed explanations. Do not defer an essential
sentence merely to wait for those larger features.

Closing a batch requires its conditions, normal case and explicit exceptions
to be accepted together. Common modifier, placement, recovery and Fireteam
baselines should own repeated reasoning; subtype/State cards link to and qualify
them. A corrected finding does not approve the rest of its record. The
[coverage gate](rules-explanation-audit-1.0-inventory.md#audit-completion-gate)
tracks all 63 remaining S records and pending material/source/presentation work
for all 367. None of the larger optional schemas or an automatic combat evaluator
is needed to write these concise explanations.

## Remaining audit gaps and limitations

- Every record was screened, but only the inventory's D subset received a
  selected official-clause comparison. There is no source-by-source approval
  of all 367 records or all 314 authored edges.
- The exact September 18 English Wiki archive, Spanish FAQ, separately
  versioned Reinforcements Extra/annex and a pinned historical Army backup
  commit were not verified. Later archives cannot repair that provenance by inference.
- The 185 Army Weapon rows and all Unit/profile variants were not individually
  audited. Named source properties and legacy aliases are not themselves proof
  of current explained gameplay. Source filtering retained absent definitions
  and references separately.
- All four core scenario rules/setup/objectives were screened against their
  clauses; 24 point-size selections and 12 geometry configurations were
  inventoried. Footprint-based Supply Box geometry, complete objective boundary
  matrices and visual map acceptance were not independently redone.
- Full Fireteam Army-chart exception review, all deployment/terrain combinations,
  combined healing methods, arbitrary partial Immunities, Enhanced Reaction
  versus Total Reaction, Smoke geometry, and Cover/Nanoscreen stacking remain open.
- Request Speedball's PH 15 and the Controlled Jump exclusion were checked;
  the pickup, item chart, token lifecycle and individual support-item interactions
  on S1 p. 84 were not fully adjudicated. The card's short deployment explanation
  must not be mistaken for complete Speedball support coverage. Review these
  with the useful baseline/reference scope proposed under REA-026.
- Source-note visibility and structured-case omissions were assessed through
  current code. No browser/server was launched and no visual, responsive,
  keyboard or end-to-end rendering acceptance is claimed.
- Original audit used `pypdf` text without a renderer. Follow-up used temporary
  `pypdfium2` 5.14.0 outside the repository to render and inspect eight S1 pages
  at scale 2: 70, 74, 138, 180, 182, 185, 186, 195. The disputed cells were visually
  verified; that confirms what is printed, not which conflicting source governs.
  No renderer dependency, PDF, screenshot or generated artifact was committed.
- Original live responses identified footer revisions without pinned Spanish
  bytes. Follow-up discovered and hash-checked selected S14 Spanish members;
  the supplementary review has now also pinned Spanish PDF S17 and oldid
  history S21; neither is the missing S18 English capture. Some direct oldid URLs and the GitHub backup
  failed; these failures were retained, not treated as evidence of absence.
- Prior research such as Katyusha range normalization was consulted for
  discovery but is not presented as independently reverified current evidence.

## Validation

Validation is documentation-focused and deliberately does not rebuild databases,
regenerate the interaction checklist, or alter data to make an audit pass.

The final exact results are recorded in the [inventory validation section](rules-explanation-audit-1.0-inventory.md#validation-results).
It includes Git whitespace, new links/anchors/paths, unique finding IDs,
remediation references, inventory arithmetic, protected-input hashes, and
comparison against pre-existing repository changes.

The existing read-only command
`python -B tools/audit_rules_interactions.py --check-output docs/rules-interaction-checklist.md`
passed: 182/182 primary catalog, 111/126 supporting identities, 15 pending,
314 authored relations, 113 future interactions. That is a historical graph
check, not a 1.0 explanation pass. The full code/data test suite, Ruff, Pyright,
database builds and release gates were not run because the deliverable changes
documentation only and the requested boundary prohibits implementing findings.
