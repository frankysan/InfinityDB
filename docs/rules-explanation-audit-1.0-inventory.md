# Rules explanation audit 1.0: inventory and validation

**Project domains:** Data processing, Web backend, Web frontend

This appendix is a snapshot inventory for the [main audit](rules-explanation-audit-1.0.md),
examining commit `859823f8d2899405a40cf126883d2adf5763db7c` on 2026-10-09.
It is not generated runtime data or a replacement interaction ledger.

## Coverage totals

- 367 records screened: 217 **D** selected clause reviews and 150 **S** screening-only records.
- D means the cited material mechanics were compared, not that every source clause or browser path passed.
- S is reviewed inventory/text structure without independent source adjudication. No existing record was left unenumerated.
- 60 of the S records are declaration-category metadata; they are not 60 missing gameplay explanations.
- 24 Labels and 6 Skill Types were screened separately. Selected Label mechanics are discussed in the main findings.
- 20 scenario components were screened: selected clauses of the 12 objectives, 3 endings and 2 setup components were compared; 3 shared geometry components were structurally inventoried only.
- 12 scenario geometry configurations and 24 Army-Points selections were inventoried; no independent map visual acceptance.
- 314 authored relations were enumerated by owner; 113 deferred candidates screened (107 post-0.7.0, 6 targeting 1.0.0).
- The 307 ledger identities have 282 reviewed, 10 inherited and 15 pending statuses. These are not the D/S audit tiers.
- 18 interaction families investigated; no exhaustive denominator for all rule combinations established.
- 37 findings: 24 High, 12 Medium, 1 Low, 0 Critical.

| Kind | Records | D | S |
| --- | ---: | ---: | ---: |
| ammunition | 11 | 11 | 0 |
| attribute | 13 | 0 | 13 |
| declaration-category | 60 | 0 | 60 |
| equipment | 36 | 27 | 9 |
| hacking-program | 12 | 12 | 0 |
| rule | 34 | 16 | 18 |
| scenario | 4 | 4 | 0 |
| skill | 106 | 76 | 30 |
| state | 24 | 24 | 0 |
| term | 18 | 0 | 18 |
| training | 2 | 0 | 2 |
| trait | 33 | 33 | 0 |
| weapon | 14 | 14 | 0 |

## Finding index

| Finding | Severity | Priority | Title |
| --- | --- | --- | --- |
| [REA-001](rules-explanation-audit-1.0.md#rea-001---engineer-incorrectly-restricts-all-targets-to-str) | High | P0 | Engineer incorrectly restricts all targets to STR |
| [REA-002](rules-explanation-audit-1.0.md#rea-002---doctor-omits-its-ordinary-recovery-gate-and-lethal-failure) | High | P0 | Doctor omits its ordinary recovery gate and lethal failure |
| [REA-003](rules-explanation-audit-1.0.md#rea-003---intuitive-attack-appears-to-require-a-second-attack-roll) | High | P0 | Intuitive Attack appears to require a second attack roll |
| [REA-004](rules-explanation-audit-1.0.md#rea-004---continuous-damage-omits-the-extra-critical-roll-exception) | High | P0 | Continuous Damage omits the extra Critical roll exception |
| [REA-005](rules-explanation-audit-1.0.md#rea-005---bs-weapon-wip-omits-explicit-prohibited-combinations) | High | P0 | BS Weapon (WIP) omits explicit prohibited combinations |
| [REA-006](rules-explanation-audit-1.0.md#rea-006---controlled-jump-lacks-declaration-timing-and-opposing-cancellation) | High | P0 | Controlled Jump lacks declaration timing and opposing cancellation |
| [REA-007](rules-explanation-audit-1.0.md#rea-007---speedballs-reuse-of-combat-jump-needs-the-faq-exclusion) | Medium | P1 | Speedball's reuse of Combat Jump needs the FAQ exclusion |
| [REA-008](rules-explanation-audit-1.0.md#rea-008---protheion-needs-the-overkill-limit-and-profile-mod) | High | P1 | Protheion needs the overkill limit and profile MOD |
| [REA-009](rules-explanation-audit-1.0.md#rea-009---recovery-and-re-infliction-in-the-same-order-are-unexplained) | High | P1 | Recovery and re-infliction in the same Order are unexplained |
| [REA-010](rules-explanation-audit-1.0.md#rea-010---immunity-omits-the-ordinary-trait-protection-behind-its-exceptions) | High | P1 | Immunity omits the ordinary Trait protection behind its exceptions |
| [REA-011](rules-explanation-audit-1.0.md#rea-011---stored-immunity-cases-are-only-partly-presented) | Medium | P1 | Stored Immunity cases are only partly presented |
| [REA-012](rules-explanation-audit-1.0.md#rea-012---smoke-and-eclipse-describe-zones-without-sufficient-resolution) | High | P1 | Smoke and Eclipse describe zones without sufficient resolution |
| [REA-013](rules-explanation-audit-1.0.md#rea-013---ap-rounding-and-t2-die-identification-are-missing-player-actions) | Medium | P1 | AP rounding and T2 die identification are missing player actions |
| [REA-014](rules-explanation-audit-1.0.md#rea-014---dodge-and-reset-lack-multi-effect-conditions) | High | P1 | Dodge and Reset lack multi-effect conditions |
| [REA-015](rules-explanation-audit-1.0.md#rea-015---several-state-cards-lack-their-operative-cancellation-conditions) | High | P1 | Several State cards lack their operative cancellation conditions |
| [REA-016](rules-explanation-audit-1.0.md#rea-016---stealth-omits-deployables-and-multi-trooper-reaction-reasoning) | High | P1 | Stealth omits Deployables and multi-Trooper reaction reasoning |
| [REA-017](rules-explanation-audit-1.0.md#rea-017---peripheral-subtype-identities-do-not-explain-their-operation) | High | P1 | Peripheral subtype identities do not explain their operation |
| [REA-018](rules-explanation-audit-1.0.md#rea-018---firewall-hacking-area-and-supportware-have-no-adequate-baseline-owner) | High | P1 | Firewall, Hacking Area, and Supportware have no adequate baseline owner |
| [REA-019](rules-explanation-audit-1.0.md#rea-019---nfbs-label-does-not-explain-suppression-and-duration) | Medium | P1 | NFB's label does not explain suppression and duration |
| [REA-020](rules-explanation-audit-1.0.md#rea-020---fireteam-basics-omit-action-ownership-and-integrity-exceptions) | High | P1 | Fireteam basics omit action ownership and integrity exceptions |
| [REA-021](rules-explanation-audit-1.0.md#rea-021---fireteam-and-martial-arts-bonuses-need-special-dice-reasoning) | High | P1 | Fireteam and Martial Arts bonuses need Special Dice reasoning |
| [REA-022](rules-explanation-audit-1.0.md#rea-022---kit-recovery-and-disposable-spending-need-multi-roll-rules) | High | P1 | Kit recovery and Disposable spending need multi-roll rules |
| [REA-023](rules-explanation-audit-1.0.md#rea-023---placement-cards-defer-essential-geometry-and-deployment-restrictions) | High | P1 | Placement cards defer essential geometry and deployment restrictions |
| [REA-024](rules-explanation-audit-1.0.md#rea-024---bioweapon-needs-a-target-conditioned-explanation-alongside-the-chart) | Medium | P1 | BioWeapon needs a target-conditioned explanation alongside the chart |
| [REA-025](rules-explanation-audit-1.0.md#rea-025---nem-is-absent-from-the-reviewed-composition-map) | High | P1 | N+E/M is absent from the reviewed composition map |
| [REA-026](rules-explanation-audit-1.0.md#rea-026---useful-general-mechanics-remain-research-rather-than-linked-reference-content) | Medium | P1 | Useful general mechanics remain research rather than linked reference content |
| [REA-027](rules-explanation-audit-1.0.md#rea-027---flash-pulses-spanish-chart-disagrees-on-rolls-and-traits) | High | P1 | Flash Pulse's Spanish chart disagrees on rolls and Traits |
| [REA-028](rules-explanation-audit-1.0.md#rea-028---kobras-two-issues-require-separate-source-decisions) | High | P1 | Kobra's two issues require separate source decisions |
| [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | Medium | P1 | The collections' exact Wiki archive is unavailable locally |
| [REA-030](rules-explanation-audit-1.0.md#rea-030---faq-publication-and-scenario-applicability-remain-uncurated) | Medium | P1 | FAQ publication and scenario applicability remain uncurated |
| [REA-031](rules-explanation-audit-1.0.md#rea-031---kobras-cc-attribute-link-points-to-the-weapon-trait) | Low | P2 | Kobra's CC Attribute link points to the Weapon Trait |
| [REA-032](rules-explanation-audit-1.0.md#rea-032---profile-changing-and-assignable-families-lack-actionable-qualifiers) | Medium | P1 | Profile-changing and assignable families lack actionable qualifiers |
| [REA-033](rules-explanation-audit-1.0.md#rea-033---reviewed-graph-status-cannot-stand-in-for-explanation-acceptance) | Medium | P1 | Reviewed graph status cannot stand in for explanation acceptance |
| [REA-034](rules-explanation-audit-1.0.md#rea-034---the-printed-fireteam-level-3-example-includes-a-level-4-bonus) | Medium | P1 | The printed Fireteam Level 3 example includes a Level 4 bonus |
| [REA-035](rules-explanation-audit-1.0.md#rea-035---impersonation-2s-unmodified-discover-wording-overstates-the-exception) | High | P0 | Impersonation-2's "unmodified" Discover wording overstates the exception |
| [REA-036](rules-explanation-audit-1.0.md#rea-036---deployable-cover-names-a-cap-without-giving-its-value-or-conditions) | High | P1 | Deployable Cover names a cap without giving its value or conditions |
| [REA-037](rules-explanation-audit-1.0.md#rea-037---armed-turret-has-conflicting-silhouette-values-within-the-pdf) | Medium | P1 | Armed Turret has conflicting Silhouette values within the PDF |

## Record inventory

C = core collection; H = Hacking Program collection. Source locators in the last column
refer to the main report source register. For S records, the entry is the authored citation,
not a claim its source was verified. Finding links also include contextual participants;
being listed does not mean the individual record is factually wrong.

| Record identity | File | Tier | Outgoing relations | Related findings | Selected clause evidence / authored citation |
| --- | --- | --- | ---: | --- | --- |
| `attribute:mov` | C | S | 0 | - | n5-core-v5.3-pdf p. 9 |
| `attribute:cc` | C | S | 0 | - | n5-core-v5.3-pdf p. 9 |
| `attribute:bs` | C | S | 0 | - | n5-core-v5.3-pdf p. 9 |
| `attribute:ph` | C | S | 0 | - | n5-core-v5.3-pdf p. 9 |
| `attribute:wip` | C | S | 0 | - | n5-core-v5.3-pdf p. 9 |
| `attribute:arm` | C | S | 0 | - | n5-core-v5.3-pdf p. 9 |
| `attribute:bts` | C | S | 0 | - | n5-core-v5.3-pdf p. 9 |
| `attribute:vita` | C | S | 0 | [REA-008](rules-explanation-audit-1.0.md#rea-008---protheion-needs-the-overkill-limit-and-profile-mod) | n5-core-v5.3-pdf p. 9 |
| `attribute:str` | C | S | 0 | - | n5-core-v5.3-pdf p. 9 |
| `attribute:ava` | C | S | 0 | - | n5-core-v5.3-pdf p. 9 |
| `attribute:s` | C | S | 0 | - | n5-core-v5.3-pdf p. 9 |
| `attribute:swc` | C | S | 0 | - | n5-core-v5.3-pdf p. 9 |
| `attribute:c` | C | S | 0 | - | n5-core-v5.3-pdf p. 9 |
| `term:model` | C | S | 0 | - | n5-core-v5.3-pdf p. 173 |
| `term:marker` | C | S | 0 | - | n5-core-v5.3-pdf p. 173 |
| `term:token` | C | S | 0 | - | n5-core-v5.3-pdf p. 173 |
| `term:state-token` | C | S | 0 | - | n5-core-v5.3-pdf p. 173 |
| `term:deployable-equipment` | C | S | 0 | - | n5-core-v5.3-pdf p. 173 |
| `term:deployable-weapon` | C | S | 0 | - | n5-core-v5.3-pdf p. 173 |
| `term:peripheral` | C | S | 0 | - | n5-core-v5.3-pdf p. 173 |
| `term:scenery-element` | C | S | 0 | - | n5-core-v5.3-pdf p. 173 |
| `term:target` | C | S | 0 | - | n5-core-v5.3-pdf p. 173 |
| `term:trooper` | C | S | 0 | - | n5-core-v5.3-pdf p. 173 |
| `term:unit-profile` | C | S | 0 | - | n5-core-v5.3-pdf p. 173 |
| `term:fto` | C | S | 0 | - | wiki-fireteams-chart-oldid-4116 |
| `term:victory-points` | C | S | 0 | - | n5-core-v5.3-pdf p. 173 |
| `term:null-state` | C | S | 0 | - | n5-core-v5.3-pdf p. 174 |
| `term:ally` | C | S | 0 | - | n5-core-v5.3-pdf p. 173 |
| `term:enemy` | C | S | 0 | - | n5-core-v5.3-pdf p. 173 |
| `term:hostile` | C | S | 0 | - | n5-core-v5.3-pdf p. 173 |
| `term:neutral` | C | S | 0 | - | n5-core-v5.3-pdf p. 173 |
| `state:camouflaged` | C | D | 2 | [REA-015](rules-explanation-audit-1.0.md#rea-015---several-state-cards-lack-their-operative-cancellation-conditions), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 157-172 (State-specific heading) |
| `skill:camouflage` | C | D | 1 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 87, 157-158 |
| `skill:discover` | C | D | 5 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally), [REA-035](rules-explanation-audit-1.0.md#rea-035---impersonation-2s-unmodified-discover-wording-overstates-the-exception) | S1 pp. 77-78, 166-167 |
| `skill:super-jump` | C | D | 1 | [REA-032](rules-explanation-audit-1.0.md#rea-032---profile-changing-and-assignable-families-lack-actionable-qualifiers) | S1 pp. 113-114 |
| `skill:forward-deployment` | C | S | 0 | - | wiki-forward-deployment-oldid-3076 |
| `trait:anti-materiel` | C | D | 0 | [REA-028](rules-explanation-audit-1.0.md#rea-028---kobras-two-issues-require-separate-source-decisions) | S1 pp. 174-175 |
| `trait:arm-0` | C | D | 0 | [REA-010](rules-explanation-audit-1.0.md#rea-010---immunity-omits-the-ordinary-trait-protection-behind-its-exceptions) | S1 pp. 174-175 |
| `trait:aro` | C | D | 0 | - | S1 pp. 174-175 |
| `trait:bioweapon` | C | D | 0 | [REA-024](rules-explanation-audit-1.0.md#rea-024---bioweapon-needs-a-target-conditioned-explanation-alongside-the-chart) | S1 pp. 174-175 |
| `trait:boost` | C | D | 0 | [REA-016](rules-explanation-audit-1.0.md#rea-016---stealth-omits-deployables-and-multi-trooper-reaction-reasoning) | S1 pp. 69, 174-175 |
| `trait:bs-weapon-ph` | C | D | 1 | [REA-021](rules-explanation-audit-1.0.md#rea-021---fireteam-and-martial-arts-bonuses-need-special-dice-reasoning) | S1 pp. 174-175 |
| `trait:bs-weapon-wip` | C | D | 1 | [REA-005](rules-explanation-audit-1.0.md#rea-005---bs-weapon-wip-omits-explicit-prohibited-combinations), [REA-021](rules-explanation-audit-1.0.md#rea-021---fireteam-and-martial-arts-bonuses-need-special-dice-reasoning) | S1 pp. 174-175 |
| `trait:bts-0` | C | D | 0 | [REA-010](rules-explanation-audit-1.0.md#rea-010---immunity-omits-the-ordinary-trait-protection-behind-its-exceptions) | S1 pp. 174-175 |
| `trait:burst-b` | C | D | 0 | - | S1 pp. 174-175 |
| `trait:burst-single-target` | C | D | 0 | - | S1 pp. 174-175 |
| `trait:cc` | C | D | 1 | - | S1 pp. 174-175 |
| `trait:concealed` | C | D | 1 | - | S1 pp. 174-175 |
| `trait:continuous-damage` | C | D | 0 | [REA-004](rules-explanation-audit-1.0.md#rea-004---continuous-damage-omits-the-extra-critical-roll-exception), [REA-010](rules-explanation-audit-1.0.md#rea-010---immunity-omits-the-ordinary-trait-protection-behind-its-exceptions) | S1 pp. 174-175 |
| `trait:deployable` | C | D | 1 | [REA-023](rules-explanation-audit-1.0.md#rea-023---placement-cards-defer-essential-geometry-and-deployment-restrictions) | S1 pp. 174-175 |
| `trait:direct-template` | C | D | 0 | - | S1 pp. 174-175 |
| `trait:disposable-x` | C | D | 1 | [REA-021](rules-explanation-audit-1.0.md#rea-021---fireteam-and-martial-arts-bonuses-need-special-dice-reasoning), [REA-022](rules-explanation-audit-1.0.md#rea-022---kit-recovery-and-disposable-spending-need-multi-roll-rules) | S1 pp. 174-175 |
| `trait:double-shot` | C | D | 0 | [REA-022](rules-explanation-audit-1.0.md#rea-022---kit-recovery-and-disposable-spending-need-multi-roll-rules) | S1 pp. 174-175 |
| `trait:impact-template` | C | D | 0 | - | S1 pp. 174-175 |
| `trait:improvised` | C | D | 0 | - | S1 pp. 174-175 |
| `trait:indiscriminate` | C | D | 0 | - | S1 pp. 174-175 |
| `trait:intuitive-attack` | C | D | 1 | [REA-003](rules-explanation-audit-1.0.md#rea-003---intuitive-attack-appears-to-require-a-second-attack-roll) | S1 pp. 174-175 |
| `trait:non-lethal` | C | D | 1 | - | S1 pp. 174-175 |
| `trait:non-reloadable` | C | D | 1 | - | S1 pp. 174-175 |
| `trait:perimeter` | C | D | 1 | [REA-023](rules-explanation-audit-1.0.md#rea-023---placement-cards-defer-essential-geometry-and-deployment-restrictions) | S1 pp. 174-175 |
| `trait:prior-deployment` | C | D | 0 | - | S1 pp. 174-175 |
| `trait:reflective` | C | D | 2 | [REA-012](rules-explanation-audit-1.0.md#rea-012---smoke-and-eclipse-describe-zones-without-sufficient-resolution) | S1 pp. 174-175 |
| `trait:silent-x` | C | D | 1 | - | S1 pp. 174-175 |
| `trait:speculative-attack` | C | D | 1 | - | S1 pp. 174-175 |
| `trait:state` | C | D | 0 | [REA-010](rules-explanation-audit-1.0.md#rea-010---immunity-omits-the-ordinary-trait-protection-behind-its-exceptions) | S1 pp. 174-175 |
| `trait:suppressive-fire` | C | D | 1 | - | S1 pp. 174-175 |
| `trait:target-attribute` | C | D | 0 | - | S1 pp. 174-175 |
| `trait:targetless` | C | D | 0 | - | S1 pp. 174-175 |
| `trait:zone-of-control-zc` | C | D | 0 | - | S1 pp. 174-175 |
| `weapon:flash-pulse` | C | D | 5 | [REA-005](rules-explanation-audit-1.0.md#rea-005---bs-weapon-wip-omits-explicit-prohibited-combinations), [REA-010](rules-explanation-audit-1.0.md#rea-010---immunity-omits-the-ordinary-trait-protection-behind-its-exceptions), [REA-027](rules-explanation-audit-1.0.md#rea-027---flash-pulses-spanish-chart-disagrees-on-rolls-and-traits) | S1 pp. 95-96, 186 |
| `weapon:armed-turret` | C | D | 8 | [REA-023](rules-explanation-audit-1.0.md#rea-023---placement-cards-defer-essential-geometry-and-deployment-restrictions), [REA-037](rules-explanation-audit-1.0.md#rea-037---armed-turret-has-conflicting-silhouette-values-within-the-pdf) | S1 pp. 70, 74 |
| `weapon:sepsitor` | C | D | 5 | - | S1 pp. 73, 121, 187 |
| `weapon:sepsitor-plus` | C | D | 4 | - | S1 pp. 73, 121, 187 |
| `weapon:pt` | C | D | 1 | - | S1 pp. 182 |
| `weapon:pt-endgame` | C | D | 2 | [REA-022](rules-explanation-audit-1.0.md#rea-022---kit-recovery-and-disposable-spending-need-multi-roll-rules) | S1 pp. 175, 182 |
| `weapon:kobra-pistol` | C | D | 0 | [REA-028](rules-explanation-audit-1.0.md#rea-028---kobras-two-issues-require-separate-source-decisions), [REA-031](rules-explanation-audit-1.0.md#rea-031---kobras-cc-attribute-link-points-to-the-weapon-trait) | S1 pp. 68, 182 |
| `weapon:kobra-pistol-cc` | C | D | 2 | [REA-028](rules-explanation-audit-1.0.md#rea-028---kobras-two-issues-require-separate-source-decisions) | S1 pp. 64, 68, 182 |
| `weapon:drop-bears` | C | D | 7 | - | S1 pp. 71, 181 |
| `weapon:wildparrot` | C | D | 6 | [REA-023](rules-explanation-audit-1.0.md#rea-023---placement-cards-defer-essential-geometry-and-deployment-restrictions) | S1 pp. 74, 181 |
| `weapon:mines` | C | D | 4 | [REA-003](rules-explanation-audit-1.0.md#rea-003---intuitive-attack-appears-to-require-a-second-attack-roll), [REA-016](rules-explanation-audit-1.0.md#rea-016---stealth-omits-deployables-and-multi-trooper-reaction-reasoning), [REA-024](rules-explanation-audit-1.0.md#rea-024---bioweapon-needs-a-target-conditioned-explanation-alongside-the-chart) | S1 pp. 72-73, 181 |
| `weapon:para-mine` | C | D | 3 | - | S1 pp. 65, 72, 181 |
| `weapon:cybermine` | C | D | 4 | - | S1 pp. 72, 181 |
| `weapon:chest-mine` | C | D | 2 | - | S1 pp. 72, 181 |
| `declaration-category:automatic:p86` | C | S | 0 | - | n5-core-v5.3-pdf p. 86 |
| `declaration-category:automatic:p87` | C | S | 0 | - | n5-core-v5.3-pdf p. 87 |
| `declaration-category:automatic:p88` | C | S | 0 | - | n5-core-v5.3-pdf p. 88 |
| `declaration-category:automatic:p89` | C | S | 0 | - | n5-core-v5.3-pdf p. 89 |
| `declaration-category:automatic:p90` | C | S | 0 | - | n5-core-v5.3-pdf p. 90 |
| `declaration-category:automatic:p91` | C | S | 0 | - | n5-core-v5.3-pdf p. 91 |
| `declaration-category:automatic:p92` | C | S | 0 | - | n5-core-v5.3-pdf p. 92 |
| `declaration-category:automatic:p93` | C | S | 0 | - | n5-core-v5.3-pdf p. 93 |
| `declaration-category:automatic:p94` | C | S | 0 | - | n5-core-v5.3-pdf p. 94 |
| `declaration-category:automatic:p95` | C | S | 0 | - | n5-core-v5.3-pdf p. 95 |
| `declaration-category:automatic:p96` | C | S | 0 | - | n5-core-v5.3-pdf p. 96 |
| `declaration-category:automatic:p97` | C | S | 0 | - | n5-core-v5.3-pdf p. 97 |
| `declaration-category:automatic:p98` | C | S | 0 | - | n5-core-v5.3-pdf p. 98 |
| `declaration-category:automatic:p99` | C | S | 0 | - | n5-core-v5.3-pdf p. 99 |
| `declaration-category:automatic:p100` | C | S | 0 | - | n5-core-v5.3-pdf p. 100 |
| `declaration-category:automatic:p101` | C | S | 0 | - | n5-core-v5.3-pdf p. 101 |
| `declaration-category:automatic:p102` | C | S | 0 | - | n5-core-v5.3-pdf p. 102 |
| `declaration-category:automatic:p103` | C | S | 0 | - | n5-core-v5.3-pdf p. 103 |
| `declaration-category:automatic:p104` | C | S | 0 | - | n5-core-v5.3-pdf p. 104 |
| `declaration-category:automatic:p105` | C | S | 0 | - | n5-core-v5.3-pdf p. 105 |
| `declaration-category:automatic:p106` | C | S | 0 | - | n5-core-v5.3-pdf p. 106 |
| `declaration-category:automatic:p109` | C | S | 0 | - | n5-core-v5.3-pdf p. 109 |
| `declaration-category:automatic:p110` | C | S | 0 | - | n5-core-v5.3-pdf p. 110 |
| `declaration-category:automatic:p111` | C | S | 0 | - | n5-core-v5.3-pdf p. 111 |
| `declaration-category:automatic:p112` | C | S | 0 | - | n5-core-v5.3-pdf p. 112 |
| `declaration-category:automatic:p113` | C | S | 0 | - | n5-core-v5.3-pdf p. 113 |
| `declaration-category:automatic:p114` | C | S | 0 | - | n5-core-v5.3-pdf p. 114 |
| `declaration-category:automatic:p115` | C | S | 0 | - | n5-core-v5.3-pdf p. 115 |
| `declaration-category:automatic:p116` | C | S | 0 | - | n5-core-v5.3-pdf p. 116 |
| `declaration-category:automatic:p117` | C | S | 0 | - | n5-core-v5.3-pdf p. 117 |
| `declaration-category:automatic:p118` | C | S | 0 | - | n5-core-v5.3-pdf p. 118 |
| `declaration-category:deployment:p89` | C | S | 0 | - | n5-core-v5.3-pdf p. 89 |
| `declaration-category:deployment:p92` | C | S | 0 | - | n5-core-v5.3-pdf p. 92 |
| `declaration-category:deployment:p93` | C | S | 0 | - | n5-core-v5.3-pdf p. 93 |
| `declaration-category:deployment:p94` | C | S | 0 | - | n5-core-v5.3-pdf p. 94 |
| `declaration-category:deployment:p102` | C | S | 0 | - | n5-core-v5.3-pdf p. 102 |
| `declaration-category:deployment:p111` | C | S | 0 | - | n5-core-v5.3-pdf p. 111 |
| `declaration-category:short-skill:p40` | C | S | 0 | - | n5-core-v5.3-pdf p. 40 |
| `declaration-category:short-skill:p45` | C | S | 0 | - | n5-core-v5.3-pdf p. 45 |
| `declaration-category:basic-short-skill:p78` | C | S | 0 | - | n5-core-v5.3-pdf p. 78 |
| `declaration-category:short-skill:p79` | C | S | 0 | - | n5-core-v5.3-pdf p. 79 |
| `declaration-category:short-skill:p90` | C | S | 0 | - | n5-core-v5.3-pdf p. 90 |
| `declaration-category:short-skill:p91` | C | S | 0 | - | n5-core-v5.3-pdf p. 91 |
| `declaration-category:short-skill:p92` | C | S | 0 | - | n5-core-v5.3-pdf p. 92 |
| `declaration-category:basic-short-skill:p103` | C | S | 0 | - | n5-core-v5.3-pdf p. 103 |
| `declaration-category:short-skill:p112` | C | S | 0 | - | n5-core-v5.3-pdf p. 112 |
| `declaration-category:long-skill:p118` | C | S | 0 | - | n5-core-v5.3-pdf p. 118 |
| `declaration-category:short-skill:p121` | C | S | 0 | - | n5-core-v5.3-pdf p. 121 |
| `declaration-category:short-skill:p123` | C | S | 0 | - | n5-core-v5.3-pdf p. 123 |
| `declaration-category:short-skill:p124` | C | S | 0 | - | n5-core-v5.3-pdf p. 124 |
| `declaration-category:long-skill:p25` | C | S | 0 | - | n5-core-v5.3-pdf p. 25 |
| `declaration-category:long-skill:p89` | C | S | 0 | - | n5-core-v5.3-pdf p. 89 |
| `declaration-category:long-skill:p111` | C | S | 0 | - | n5-core-v5.3-pdf p. 111 |
| `declaration-category:long-skill:p86` | C | S | 0 | - | n5-core-v5.3-pdf p. 86 |
| `declaration-category:aro:p40` | C | S | 0 | - | n5-core-v5.3-pdf p. 40 |
| `declaration-category:aro:p45` | C | S | 0 | - | n5-core-v5.3-pdf p. 45 |
| `declaration-category:aro:p78` | C | S | 0 | - | n5-core-v5.3-pdf p. 78 |
| `declaration-category:aro:p79` | C | S | 0 | - | n5-core-v5.3-pdf p. 79 |
| `declaration-category:aro:p92` | C | S | 0 | - | n5-core-v5.3-pdf p. 92 |
| `declaration-category:aro:p103` | C | S | 0 | - | n5-core-v5.3-pdf p. 103 |
| `skill:doctor` | C | D | 3 | [REA-002](rules-explanation-audit-1.0.md#rea-002---doctor-omits-its-ordinary-recovery-gate-and-lethal-failure), [REA-009](rules-explanation-audit-1.0.md#rea-009---recovery-and-re-infliction-in-the-same-order-are-unexplained) | S1 pp. 90, 104, 170 |
| `skill:engineer` | C | D | 8 | [REA-001](rules-explanation-audit-1.0.md#rea-001---engineer-incorrectly-restricts-all-targets-to-str), [REA-009](rules-explanation-audit-1.0.md#rea-009---recovery-and-re-infliction-in-the-same-order-are-unexplained) | S1 pp. 91, 164-165, 168, 170-171 |
| `skill:cyberplug` | C | D | 1 | [REA-017](rules-explanation-audit-1.0.md#rea-017---peripheral-subtype-identities-do-not-explain-their-operation) | S1 pp. 90, 107-108 |
| `skill:peripheral` | C | D | 5 | [REA-017](rules-explanation-audit-1.0.md#rea-017---peripheral-subtype-identities-do-not-explain-their-operation) | S1 pp. 106-108 |
| `rule:peripheral-type:servant` | C | D | 0 | [REA-017](rules-explanation-audit-1.0.md#rea-017---peripheral-subtype-identities-do-not-explain-their-operation) | S1 pp. 106-108 |
| `rule:peripheral-type:synchronized` | C | D | 0 | [REA-017](rules-explanation-audit-1.0.md#rea-017---peripheral-subtype-identities-do-not-explain-their-operation) | S1 pp. 106-108 |
| `rule:peripheral-type:control` | C | D | 0 | [REA-017](rules-explanation-audit-1.0.md#rea-017---peripheral-subtype-identities-do-not-explain-their-operation) | S1 pp. 106-108 |
| `rule:peripheral-type:ancillary` | C | D | 1 | [REA-017](rules-explanation-audit-1.0.md#rea-017---peripheral-subtype-identities-do-not-explain-their-operation), [REA-030](rules-explanation-audit-1.0.md#rea-030---faq-publication-and-scenario-applicability-remain-uncurated) | S1 pp. 106-108 |
| `rule:peripheral-type:cyberplug` | C | D | 0 | [REA-017](rules-explanation-audit-1.0.md#rea-017---peripheral-subtype-identities-do-not-explain-their-operation) | S1 pp. 106-108 |
| `training:regular` | C | S | 0 | - | n5-core-v5.3-pdf p. 11 |
| `training:irregular` | C | S | 1 | - | n5-core-v5.3-pdf p. 11 |
| `skill:martial-arts` | C | D | 1 | [REA-021](rules-explanation-audit-1.0.md#rea-021---fireteam-and-martial-arts-bonuses-need-special-dice-reasoning) | S1 pp. 100-101 |
| `skill:martial-arts-l1` | C | D | 1 | [REA-021](rules-explanation-audit-1.0.md#rea-021---fireteam-and-martial-arts-bonuses-need-special-dice-reasoning) | S1 pp. 100 |
| `skill:martial-arts-l2` | C | D | 1 | [REA-021](rules-explanation-audit-1.0.md#rea-021---fireteam-and-martial-arts-bonuses-need-special-dice-reasoning) | S1 pp. 100 |
| `skill:martial-arts-l3` | C | D | 1 | [REA-021](rules-explanation-audit-1.0.md#rea-021---fireteam-and-martial-arts-bonuses-need-special-dice-reasoning) | S1 pp. 100 |
| `skill:martial-arts-l4` | C | D | 1 | [REA-021](rules-explanation-audit-1.0.md#rea-021---fireteam-and-martial-arts-bonuses-need-special-dice-reasoning) | S1 pp. 100 |
| `skill:martial-arts-l5` | C | D | 1 | [REA-021](rules-explanation-audit-1.0.md#rea-021---fireteam-and-martial-arts-bonuses-need-special-dice-reasoning) | S1 pp. 100 |
| `skill:strategos` | C | D | 0 | - | S1 pp. 113 |
| `skill:strategos-l1` | C | D | 1 | - | S1 pp. 113 |
| `skill:strategos-l2` | C | D | 1 | - | S1 pp. 113 |
| `skill:bs-attack` | C | D | 0 | [REA-005](rules-explanation-audit-1.0.md#rea-005---bs-weapon-wip-omits-explicit-prohibited-combinations), [REA-021](rules-explanation-audit-1.0.md#rea-021---fireteam-and-martial-arts-bonuses-need-special-dice-reasoning), [REA-026](rules-explanation-audit-1.0.md#rea-026---useful-general-mechanics-remain-research-rather-than-linked-reference-content) | S1 pp. 39-41, 75 |
| `skill:bs-12` | C | S | 1 | - | n5-core-v5.3-pdf p. 40 |
| `skill:bs-11` | C | S | 1 | - | n5-core-v5.3-pdf p. 40 |
| `skill:cc-attack` | C | D | 0 | [REA-026](rules-explanation-audit-1.0.md#rea-026---useful-general-mechanics-remain-research-rather-than-linked-reference-content) | S1 pp. 54, 95, 100, 103 (selected modifiers) |
| `skill:cc-21` | C | S | 1 | - | n5-core-v5.3-pdf p. 45 |
| `equipment:cube` | C | D | 1 | [REA-002](rules-explanation-audit-1.0.md#rea-002---doctor-omits-its-ordinary-recovery-gate-and-lethal-failure), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 121 |
| `equipment:cube-2` | C | D | 4 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 73, 121 |
| `equipment:tinbot` | C | S | 0 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | n5-core-v5.3-pdf p. 127 |
| `equipment:tinbot-firewall` | C | D | 1 | [REA-018](rules-explanation-audit-1.0.md#rea-018---firewall-hacking-area-and-supportware-have-no-adequate-baseline-owner), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 55-56 (Firewall baseline) |
| `equipment:tinbot-neurocinetics` | C | S | 2 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | n5-core-v5.3-pdf p. 127 |
| `equipment:tinbot-albedo` | C | S | 2 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | n5-core-v5.3-pdf p. 127 |
| `equipment:tinbot-discover` | C | S | 2 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | n5-core-v5.3-pdf p. 127 |
| `equipment:tinbot-ecm-guided` | C | S | 2 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | n5-core-v5.3-pdf p. 127 |
| `equipment:tinbot-repeater` | C | S | 2 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | n5-core-v5.3-pdf p. 127 |
| `skill:mimetism` | C | D | 2 | [REA-019](rules-explanation-audit-1.0.md#rea-019---nfbs-label-does-not-explain-suppression-and-duration) | S1 pp. 102, 125 |
| `equipment:multispectral-visor` | C | D | 1 | [REA-012](rules-explanation-audit-1.0.md#rea-012---smoke-and-eclipse-describe-zones-without-sufficient-resolution) | S1 pp. 64, 66, 125 |
| `skill:combat-instinct` | C | D | 2 | [REA-016](rules-explanation-audit-1.0.md#rea-016---stealth-omits-deployables-and-multi-trooper-reaction-reasoning) | S1 pp. 88 |
| `skill:sixth-sense` | C | D | 3 | [REA-014](rules-explanation-audit-1.0.md#rea-014---dodge-and-reset-lack-multi-effect-conditions), [REA-016](rules-explanation-audit-1.0.md#rea-016---stealth-omits-deployables-and-multi-trooper-reaction-reasoning) | S1 pp. 111-112 |
| `skill:stealth` | C | D | 1 | [REA-016](rules-explanation-audit-1.0.md#rea-016---stealth-omits-deployables-and-multi-trooper-reaction-reasoning) | S1 pp. 112 |
| `skill:surprise-attack` | C | S | 0 | - | wiki-surprise-attack-oldid-3943 |
| `state:hidden-deployment` | C | D | 1 | [REA-015](rules-explanation-audit-1.0.md#rea-015---several-state-cards-lack-their-operative-cancellation-conditions) | S1 pp. 157-172 (State-specific heading) |
| `skill:hidden-deployment` | C | D | 1 | - | S1 pp. 95, 161-162 |
| `skill:sensor` | C | S | 5 | - | n5-core-v5.3-pdf p. 112 |
| `skill:marksmanship` | C | D | 1 | - | S1 pp. 100, 125 |
| `equipment:baggage` | C | D | 2 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 83, 120, 172 |
| `equipment:albedo` | C | D | 2 | [REA-019](rules-explanation-audit-1.0.md#rea-019---nfbs-label-does-not-explain-suppression-and-duration) | S1 pp. 119 |
| `skill:natural-born-warrior` | C | D | 2 | - | S1 pp. 103 |
| `skill:limited-cover` | C | D | 0 | - | S1 pp. 100 |
| `skill:non-hackable` | C | S | 0 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | wiki-en-20260918-130233 / Non-Hackable |
| `skill:no-cover` | C | D | 1 | - | S1 pp. 104 |
| `skill:forward-observer` | C | S | 1 | - | wiki-forward-observer-oldid-3878 |
| `skill:dodge` | C | D | 2 | [REA-014](rules-explanation-audit-1.0.md#rea-014---dodge-and-reset-lack-multi-effect-conditions) | S1 pp. 79-80, 160 |
| `skill:reset` | C | D | 3 | [REA-014](rules-explanation-audit-1.0.md#rea-014---dodge-and-reset-lack-multi-effect-conditions) | S1 pp. 85, 165, 168, 171 |
| `skill:cautious-movement` | C | D | 0 | - | S1 pp. 32, 112 |
| `skill:alert` | C | D | 0 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 77 |
| `skill:climb` | C | D | 0 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 32-33, 88 |
| `skill:idle` | C | S | 0 | [REA-026](rules-explanation-audit-1.0.md#rea-026---useful-general-mechanics-remain-research-rather-than-linked-reference-content), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | wiki-en-20260918-130233 / Idle |
| `skill:intuitive-attack` | C | D | 0 | [REA-003](rules-explanation-audit-1.0.md#rea-003---intuitive-attack-appears-to-require-a-second-attack-roll), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 49 |
| `skill:jump` | C | D | 1 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 34, 113 |
| `skill:move` | C | D | 0 | [REA-026](rules-explanation-audit-1.0.md#rea-026---useful-general-mechanics-remain-research-rather-than-linked-reference-content), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 28-31 |
| `skill:look-out` | C | D | 1 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 81 |
| `skill:place-deployable` | C | D | 0 | [REA-023](rules-explanation-audit-1.0.md#rea-023---placement-cards-defer-essential-geometry-and-deployment-restrictions), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally), [REA-036](rules-explanation-audit-1.0.md#rea-036---deployable-cover-names-a-cap-without-giving-its-value-or-conditions) | S1 pp. 82-83 |
| `skill:reload` | C | D | 1 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 83, 120 |
| `skill:request-speedball` | C | D | 1 | [REA-007](rules-explanation-audit-1.0.md#rea-007---speedballs-reuse-of-combat-jump-needs-the-faq-exclusion), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S2 printed p. 1 (selected exclusion only) |
| `skill:speculative-attack` | C | S | 1 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | wiki-en-20260918-130233 / Speculative_Attack |
| `skill:suppressive-fire` | C | D | 1 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 85, 171 |
| `state:unconscious` | C | D | 2 | [REA-002](rules-explanation-audit-1.0.md#rea-002---doctor-omits-its-ordinary-recovery-gate-and-lethal-failure) | S1 pp. 157-172 (State-specific heading) |
| `state:disconnected` | C | D | 1 | [REA-015](rules-explanation-audit-1.0.md#rea-015---several-state-cards-lack-their-operative-cancellation-conditions), [REA-017](rules-explanation-audit-1.0.md#rea-017---peripheral-subtype-identities-do-not-explain-their-operation) | S1 pp. 157-172 (State-specific heading) |
| `state:immobilized-a` | C | D | 2 | [REA-001](rules-explanation-audit-1.0.md#rea-001---engineer-incorrectly-restricts-all-targets-to-str), [REA-009](rules-explanation-audit-1.0.md#rea-009---recovery-and-re-infliction-in-the-same-order-are-unexplained) | S1 pp. 157-172 (State-specific heading) |
| `state:immobilized-b` | C | D | 2 | [REA-001](rules-explanation-audit-1.0.md#rea-001---engineer-incorrectly-restricts-all-targets-to-str), [REA-014](rules-explanation-audit-1.0.md#rea-014---dodge-and-reset-lack-multi-effect-conditions) | S1 pp. 157-172 (State-specific heading) |
| `state:isolated` | C | D | 3 | [REA-001](rules-explanation-audit-1.0.md#rea-001---engineer-incorrectly-restricts-all-targets-to-str), [REA-014](rules-explanation-audit-1.0.md#rea-014---dodge-and-reset-lack-multi-effect-conditions) | S1 pp. 157-172 (State-specific heading) |
| `state:stunned` | C | D | 0 | [REA-002](rules-explanation-audit-1.0.md#rea-002---doctor-omits-its-ordinary-recovery-gate-and-lethal-failure) | S1 pp. 157-172 (State-specific heading) |
| `state:targeted` | C | D | 5 | [REA-001](rules-explanation-audit-1.0.md#rea-001---engineer-incorrectly-restricts-all-targets-to-str), [REA-014](rules-explanation-audit-1.0.md#rea-014---dodge-and-reset-lack-multi-effect-conditions) | S1 pp. 157-172 (State-specific heading) |
| `state:unloaded` | C | D | 0 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 157-172 (State-specific heading) |
| `equipment:360o-visor` | C | S | 0 | - | wiki-360-visor-oldid-3511 |
| `equipment:nanoscreen` | C | D | 1 | - | S1 pp. 100, 125 |
| `equipment:x-visor` | C | S | 3 | - | wiki-x-visor-oldid-3193 |
| `equipment:biometric-visor` | C | D | 3 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally), [REA-035](rules-explanation-audit-1.0.md#rea-035---impersonation-2s-unmodified-discover-wording-overstates-the-exception) | S1 pp. 120, 166-167 |
| `equipment:dazer` | C | D | 0 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 121 |
| `equipment:deactivator` | C | D | 1 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 121 |
| `equipment:deployable-cover` | C | D | 1 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally), [REA-036](rules-explanation-audit-1.0.md#rea-036---deployable-cover-names-a-cap-without-giving-its-value-or-conditions) | S1 pp. 82, 122 |
| `equipment:repeater` | C | D | 0 | [REA-018](rules-explanation-audit-1.0.md#rea-018---firewall-hacking-area-and-supportware-have-no-adequate-baseline-owner), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 55-56 |
| `equipment:deployable-repeater` | C | D | 1 | [REA-023](rules-explanation-audit-1.0.md#rea-023---placement-cards-defer-essential-geometry-and-deployment-restrictions), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 56, 82 |
| `equipment:fastpanda` | C | D | 1 | [REA-023](rules-explanation-audit-1.0.md#rea-023---placement-cards-defer-essential-geometry-and-deployment-restrictions), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 82-83, 122 |
| `equipment:ai-motorcycle` | C | D | 3 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally), [REA-032](rules-explanation-audit-1.0.md#rea-032---profile-changing-and-assignable-families-lack-actionable-qualifiers) | S1 pp. 107, 117, 119 |
| `equipment:bangbomb` | C | D | 1 | [REA-014](rules-explanation-audit-1.0.md#rea-014---dodge-and-reset-lack-multi-effect-conditions), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 79-80, 120 |
| `equipment:ecm` | C | S | 0 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | wiki-en-20260918-130233 / ECM |
| `equipment:escape-system` | C | D | 1 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally), [REA-032](rules-explanation-audit-1.0.md#rea-032---profile-changing-and-assignable-families-lack-actionable-qualifiers) | S1 pp. 117-118 |
| `equipment:evo-hacking-device` | C | D | 0 | [REA-018](rules-explanation-audit-1.0.md#rea-018---firewall-hacking-area-and-supportware-have-no-adequate-baseline-owner), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 58-61, 123 |
| `equipment:gizmokit` | C | D | 1 | [REA-021](rules-explanation-audit-1.0.md#rea-021---fireteam-and-martial-arts-bonuses-need-special-dice-reasoning), [REA-022](rules-explanation-audit-1.0.md#rea-022---kit-recovery-and-disposable-spending-need-multi-roll-rules), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 110, 123 |
| `equipment:hacking-device` | C | D | 0 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 58, 123 |
| `equipment:hacking-device-plus` | C | D | 0 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 58, 123 |
| `equipment:holomask` | C | D | 1 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 124, 164 |
| `equipment:holoprojector` | C | D | 1 | [REA-019](rules-explanation-audit-1.0.md#rea-019---nfbs-label-does-not-explain-suppression-and-duration), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 124, 162-163 |
| `equipment:killer-hacking-device` | C | D | 0 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 58, 123 |
| `equipment:medikit` | C | D | 2 | [REA-021](rules-explanation-audit-1.0.md#rea-021---fireteam-and-martial-arts-bonuses-need-special-dice-reasoning), [REA-022](rules-explanation-audit-1.0.md#rea-022---kit-recovery-and-disposable-spending-need-multi-roll-rules), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 124 |
| `equipment:motorcycle` | C | D | 4 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 125 |
| `equipment:symbiomate` | C | D | 1 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally), [REA-032](rules-explanation-audit-1.0.md#rea-032---profile-changing-and-assignable-families-lack-actionable-qualifiers) | S1 pp. 126, 174 |
| `skill:combat-jump` | C | D | 0 | [REA-006](rules-explanation-audit-1.0.md#rea-006---controlled-jump-lacks-declaration-timing-and-opposing-cancellation) | S1 pp. 59, 89, 155 |
| `skill:decoy` | C | S | 1 | - | wiki-decoy-oldid-3069 |
| `skill:impersonation` | C | D | 2 | - | S1 pp. 96, 166-167 |
| `skill:infiltration` | C | S | 0 | - | wiki-infiltration-oldid-3909 |
| `skill:minelayer` | C | D | 0 | [REA-023](rules-explanation-audit-1.0.md#rea-023---placement-cards-defer-essential-geometry-and-deployment-restrictions) | S1 pp. 102 |
| `skill:parachutist` | C | D | 0 | - | S1 pp. 105, 155 |
| `skill:sapper` | C | S | 1 | - | wiki-sapper-oldid-3286 |
| `skill:strategic-deployment` | C | D | 1 | - | S1 pp. 112 |
| `state:decoy` | C | D | 0 | - | S1 pp. 157-172 (State-specific heading) |
| `state:impersonation-1` | C | D | 1 | [REA-015](rules-explanation-audit-1.0.md#rea-015---several-state-cards-lack-their-operative-cancellation-conditions), [REA-035](rules-explanation-audit-1.0.md#rea-035---impersonation-2s-unmodified-discover-wording-overstates-the-exception) | S1 pp. 157-172 (State-specific heading) |
| `state:impersonation-2` | C | D | 1 | [REA-015](rules-explanation-audit-1.0.md#rea-015---several-state-cards-lack-their-operative-cancellation-conditions), [REA-035](rules-explanation-audit-1.0.md#rea-035---impersonation-2s-unmodified-discover-wording-overstates-the-exception) | S1 pp. 157-172 (State-specific heading) |
| `state:foxhole` | C | D | 2 | - | S1 pp. 157-172 (State-specific heading) |
| `skill:berserk` | C | S | 2 | - | wiki-berserk-oldid-3236 |
| `skill:guard` | C | D | 1 | - | S1 pp. 86, 95 |
| `skill:neurocinetics` | C | S | 1 | - | wiki-neurocinetics-oldid-3111 |
| `skill:total-reaction` | C | S | 1 | - | wiki-total-reaction-oldid-3147 |
| `skill:triangulated-fire` | C | D | 2 | - | S1 pp. 118 |
| `skill:aerial` | C | D | 5 | - | S1 pp. 86 |
| `skill:climbing-plus` | C | D | 3 | - | S1 pp. 88 |
| `skill:terrain` | C | D | 0 | - | S1 pp. 116 |
| `skill:warhorse` | C | D | 2 | - | S1 pp. 118 |
| `skill:courage` | C | D | 0 | - | S1 pp. 90 |
| `skill:frenzy` | C | D | 7 | - | S1 pp. 93 |
| `skill:impetuous` | C | S | 4 | - | wiki-impetuous-oldid-4039 |
| `skill:religious-troop` | C | D | 0 | - | S1 pp. 110 |
| `state:dead` | C | D | 1 | [REA-008](rules-explanation-audit-1.0.md#rea-008---protheion-needs-the-overkill-limit-and-profile-mod) | S1 pp. 157-172 (State-specific heading) |
| `state:engaged` | C | D | 1 | [REA-014](rules-explanation-audit-1.0.md#rea-014---dodge-and-reset-lack-multi-effect-conditions) | S1 pp. 157-172 (State-specific heading) |
| `state:holoecho` | C | D | 1 | [REA-015](rules-explanation-audit-1.0.md#rea-015---several-state-cards-lack-their-operative-cancellation-conditions) | S1 pp. 157-172 (State-specific heading) |
| `state:holomask` | C | D | 0 | [REA-015](rules-explanation-audit-1.0.md#rea-015---several-state-cards-lack-their-operative-cancellation-conditions) | S1 pp. 157-172 (State-specific heading) |
| `state:normal` | C | D | 0 | - | S1 pp. 157-172 (State-specific heading) |
| `state:prone` | C | D | 1 | [REA-015](rules-explanation-audit-1.0.md#rea-015---several-state-cards-lack-their-operative-cancellation-conditions) | S1 pp. 157-172 (State-specific heading) |
| `state:possessed` | C | D | 1 | - | S1 pp. 157-172 (State-specific heading) |
| `state:retreat` | C | D | 7 | [REA-015](rules-explanation-audit-1.0.md#rea-015---several-state-cards-lack-their-operative-cancellation-conditions) | S1 pp. 157-172 (State-specific heading) |
| `state:sepsitorized` | C | D | 1 | - | S1 pp. 157-172 (State-specific heading) |
| `state:suppressive-fire` | C | D | 0 | [REA-015](rules-explanation-audit-1.0.md#rea-015---several-state-cards-lack-their-operative-cancellation-conditions), [REA-020](rules-explanation-audit-1.0.md#rea-020---fireteam-basics-omit-action-ownership-and-integrity-exceptions) | S1 pp. 157-172 (State-specific heading) |
| `skill:dogged` | C | D | 5 | - | S1 pp. 91 |
| `skill:no-wound-incapacitation` | C | D | 4 | [REA-002](rules-explanation-audit-1.0.md#rea-002---doctor-omits-its-ordinary-recovery-gate-and-lethal-failure), [REA-022](rules-explanation-audit-1.0.md#rea-022---kit-recovery-and-disposable-spending-need-multi-roll-rules) | S1 pp. 104 |
| `skill:remote-presence` | C | D | 3 | [REA-022](rules-explanation-audit-1.0.md#rea-022---kit-recovery-and-disposable-spending-need-multi-roll-rules) | S1 pp. 110 |
| `skill:shasvastii` | C | D | 1 | - | S1 pp. 111, 151 |
| `skill:regeneration` | C | D | 1 | - | S1 pp. 109 |
| `skill:protheion` | C | D | 1 | [REA-008](rules-explanation-audit-1.0.md#rea-008---protheion-needs-the-overkill-limit-and-profile-mod) | S1 pp. 109 |
| `rule:loss-of-lieutenant` | C | S | 2 | - | wiki-loss-of-lieutenant-oldid-3508 |
| `rule:regular-order` | C | S | 0 | - | n5-core-v5.3-pdf p. 11 |
| `rule:irregular-order` | C | S | 0 | - | n5-core-v5.3-pdf p. 11 |
| `rule:special-lieutenant-order` | C | S | 0 | - | wiki-orders-order-pool-oldid-3589 |
| `rule:tactical-order` | C | S | 0 | - | wiki-orders-order-pool-oldid-3589 |
| `rule:command-token-strategic-use` | C | S | 2 | [REA-026](rules-explanation-audit-1.0.md#rea-026---useful-general-mechanics-remain-research-rather-than-linked-reference-content) | wiki-command-tokens-oldid-3959 |
| `skill:chain-of-command` | C | S | 2 | - | wiki-chain-of-command-oldid-3799 |
| `skill:counterintelligence` | C | S | 1 | - | wiki-counterintelligence-oldid-3991 |
| `skill:inspiring-leadership` | C | D | 3 | - | S1 pp. 99 |
| `skill:lieutenant` | C | D | 3 | - | S1 pp. 99 |
| `skill:mnemonica` | C | S | 2 | - | wiki-mnemonica-oldid-3105 |
| `skill:nco` | C | D | 2 | [REA-020](rules-explanation-audit-1.0.md#rea-020---fireteam-basics-omit-action-ownership-and-integrity-exceptions) | S1 pp. 104, 135 |
| `skill:tactical-awareness` | C | D | 1 | [REA-020](rules-explanation-audit-1.0.md#rea-020---fireteam-basics-omit-action-ownership-and-integrity-exceptions) | S1 pp. 115, 135 |
| `skill:paramedic` | C | D | 1 | - | S1 pp. 105 |
| `skill:tech-recovery` | C | D | 7 | - | S1 pp. 115 |
| `skill:technorganic` | C | D | 4 | [REA-022](rules-explanation-audit-1.0.md#rea-022---kit-recovery-and-disposable-spending-need-multi-roll-rules) | S1 pp. 116 |
| `skill:ft-master` | C | D | 0 | [REA-020](rules-explanation-audit-1.0.md#rea-020---fireteam-basics-omit-action-ownership-and-integrity-exceptions) | S1 pp. 93 |
| `skill:number-2` | C | D | 0 | [REA-020](rules-explanation-audit-1.0.md#rea-020---fireteam-basics-omit-action-ownership-and-integrity-exceptions) | S1 pp. 105 |
| `skill:specialist-operative` | C | S | 0 | - | wiki-specialist-operative-oldid-3136 |
| `skill:journalist` | C | S | 0 | - | wiki-journalist-oldid-4086 |
| `skill:tagcom` | C | S | 0 | - | wiki-tagcom-oldid-3144 |
| `skill:booty` | C | S | 0 | - | wiki-booty-oldid-3852 |
| `skill:metachemistry` | C | S | 0 | - | wiki-metachemistry-oldid-3855 |
| `skill:explode` | C | D | 2 | - | S1 pp. 92 |
| `skill:exrah` | C | D | 2 | - | S1 pp. 92 |
| `skill:immunity` | C | D | 0 | [REA-004](rules-explanation-audit-1.0.md#rea-004---continuous-damage-omits-the-extra-critical-roll-exception), [REA-010](rules-explanation-audit-1.0.md#rea-010---immunity-omits-the-ordinary-trait-protection-behind-its-exceptions), [REA-011](rules-explanation-audit-1.0.md#rea-011---stored-immunity-cases-are-only-partly-presented), [REA-025](rules-explanation-audit-1.0.md#rea-025---nem-is-absent-from-the-reviewed-composition-map), [REA-027](rules-explanation-audit-1.0.md#rea-027---flash-pulses-spanish-chart-disagrees-on-rolls-and-traits) | S1 pp. 95-96 |
| `skill:vulnerability` | C | D | 1 | [REA-024](rules-explanation-audit-1.0.md#rea-024---bioweapon-needs-a-target-conditioned-explanation-alongside-the-chart) | S1 pp. 118 |
| `skill:g-jumper` | C | S | 0 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | wiki-en-20260918-130233 / G:_Jumper |
| `skill:infinity-spec-ops` | C | S | 0 | - | wiki-infinity-spec-ops-oldid-4120 |
| `skill:morpho-scan` | C | S | 1 | - | wiki-morpho-scan-oldid-3106 |
| `skill:remdriver` | C | S | 0 | - | wiki-remdriver-oldid-3634 |
| `skill:transmutation` | C | D | 0 | [REA-032](rules-explanation-audit-1.0.md#rea-032---profile-changing-and-assignable-families-lack-actionable-qualifiers) | S1 pp. 117-118 |
| `skill:hacker` | C | S | 1 | [REA-018](rules-explanation-audit-1.0.md#rea-018---firewall-hacking-area-and-supportware-have-no-adequate-baseline-owner) | wiki-hacker-oldid-3646 |
| `rule:fireteam-general` | C | D | 0 | [REA-020](rules-explanation-audit-1.0.md#rea-020---fireteam-basics-omit-action-ownership-and-integrity-exceptions) | S1 pp. 132-136 |
| `rule:fireteam-level-bonuses` | C | D | 0 | [REA-021](rules-explanation-audit-1.0.md#rea-021---fireteam-and-martial-arts-bonuses-need-special-dice-reasoning), [REA-034](rules-explanation-audit-1.0.md#rea-034---the-printed-fireteam-level-3-example-includes-a-level-4-bonus) | S1 pp. 135-136 |
| `rule:profile-help:unit-profile` | C | S | 0 | - | n5-core-v5.3-pdf p. 8 |
| `rule:profile-help:attributes` | C | S | 0 | - | n5-core-v5.3-pdf p. 9 |
| `rule:profile-help:training-orders` | C | S | 0 | - | n5-core-v5.3-pdf p. 8 |
| `rule:profile-help:troop-type` | C | S | 0 | - | n5-core-v5.3-pdf p. 8 |
| `rule:profile-help:classification` | C | S | 0 | - | n5-core-v5.3-pdf p. 8 |
| `rule:profile-help:isc` | C | S | 0 | - | n5-core-v5.3-pdf p. 8 |
| `rule:profile-help:hackable` | C | S | 0 | - | n5-core-v5.3-pdf p. 8 |
| `rule:profile-help:peripheral` | C | S | 0 | - | n5-core-v5.3-pdf p. 8 |
| `rule:profile-help:skills` | C | S | 0 | - | n5-core-v5.3-pdf p. 8 |
| `rule:profile-help:equipment` | C | S | 0 | - | n5-core-v5.3-pdf p. 8 |
| `rule:profile-help:weapons` | C | S | 0 | - | n5-core-v5.3-pdf p. 8 |
| `rule:profile-help:profile-options` | C | S | 0 | - | n5-core-v5.3-pdf p. 8 |
| `ammunition:normal` | C | D | 0 | [REA-024](rules-explanation-audit-1.0.md#rea-024---bioweapon-needs-a-target-conditioned-explanation-alongside-the-chart), [REA-025](rules-explanation-audit-1.0.md#rea-025---nem-is-absent-from-the-reviewed-composition-map), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 63 |
| `ammunition:ap` | C | D | 0 | [REA-013](rules-explanation-audit-1.0.md#rea-013---ap-rounding-and-t2-die-identification-are-missing-player-actions), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 63 |
| `ammunition:da` | C | D | 0 | [REA-024](rules-explanation-audit-1.0.md#rea-024---bioweapon-needs-a-target-conditioned-explanation-alongside-the-chart), [REA-028](rules-explanation-audit-1.0.md#rea-028---kobras-two-issues-require-separate-source-decisions), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 64 |
| `ammunition:eclipse` | C | D | 0 | [REA-012](rules-explanation-audit-1.0.md#rea-012---smoke-and-eclipse-describe-zones-without-sufficient-resolution), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 64 |
| `ammunition:em` | C | D | 2 | [REA-013](rules-explanation-audit-1.0.md#rea-013---ap-rounding-and-t2-die-identification-are-missing-player-actions), [REA-025](rules-explanation-audit-1.0.md#rea-025---nem-is-absent-from-the-reviewed-composition-map), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 64 |
| `ammunition:exp` | C | D | 0 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 65 |
| `ammunition:para` | C | D | 1 | [REA-009](rules-explanation-audit-1.0.md#rea-009---recovery-and-re-infliction-in-the-same-order-are-unexplained), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 65 |
| `ammunition:shock` | C | D | 1 | [REA-024](rules-explanation-audit-1.0.md#rea-024---bioweapon-needs-a-target-conditioned-explanation-alongside-the-chart), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 65 |
| `ammunition:smoke` | C | D | 0 | [REA-012](rules-explanation-audit-1.0.md#rea-012---smoke-and-eclipse-describe-zones-without-sufficient-resolution), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 66 |
| `ammunition:stun` | C | D | 1 | [REA-027](rules-explanation-audit-1.0.md#rea-027---flash-pulses-spanish-chart-disagrees-on-rolls-and-traits), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 67 |
| `ammunition:t2` | C | D | 0 | [REA-013](rules-explanation-audit-1.0.md#rea-013---ap-rounding-and-t2-die-identification-are-missing-player-actions), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 67 |
| `scenario:domination` | C | D | 0 | - | S1 pp. 149-156 (mission rules/setup/scoring; geometry screened) |
| `scenario:supplies` | C | D | 0 | - | S1 pp. 149-156 (mission rules/setup/scoring; geometry screened) |
| `scenario:annihilation` | C | D | 0 | [REA-030](rules-explanation-audit-1.0.md#rea-030---faq-publication-and-scenario-applicability-remain-uncurated) | S1 pp. 149-156 (mission rules/setup/scoring; geometry screened) |
| `scenario:firefight` | C | D | 0 | [REA-030](rules-explanation-audit-1.0.md#rea-030---faq-publication-and-scenario-applicability-remain-uncurated) | S1 pp. 149-156 (mission rules/setup/scoring; geometry screened) |
| `rule:scenario:dominate-quadrants` | C | D | 0 | - | S1 pp. 150-155 (scoped rule heading) |
| `rule:scenario:consoles` | C | D | 0 | - | S1 pp. 150-155 (scoped rule heading) |
| `rule:specialist-troops:standard` | C | D | 0 | - | S1 pp. 150-155 (scoped rule heading) |
| `rule:scenario:supply-boxes` | C | D | 0 | - | S1 pp. 150-155 (scoped rule heading) |
| `rule:scenario:carrying-supply-boxes` | C | D | 0 | [REA-030](rules-explanation-audit-1.0.md#rea-030---faq-publication-and-scenario-applicability-remain-uncurated) | S1 pp. 150-155 (scoped rule heading) |
| `rule:scenario:controlling-supply-boxes` | C | D | 0 | - | S1 pp. 150-155 (scoped rule heading) |
| `rule:scenario:killing` | C | D | 0 | [REA-030](rules-explanation-audit-1.0.md#rea-030---faq-publication-and-scenario-applicability-remain-uncurated) | S1 pp. 150-155 (scoped rule heading) |
| `rule:scenario:reinforced-tactical-link` | C | D | 0 | - | S1 pp. 150-155 (scoped rule heading) |
| `rule:scenario:designated-landing-area` | C | D | 0 | [REA-006](rules-explanation-audit-1.0.md#rea-006---controlled-jump-lacks-declaration-timing-and-opposing-cancellation) | S1 pp. 150-155 (scoped rule heading) |
| `skill:hack-consoles` | C | D | 0 | - | S1 pp. 151-155 |
| `skill:pick-up-supply-boxes` | C | D | 0 | - | S1 pp. 151-155 |
| `hacking-program:assisted-fire` | H | D | 0 | [REA-018](rules-explanation-audit-1.0.md#rea-018---firewall-hacking-area-and-supportware-have-no-adequate-baseline-owner), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 55-61 (Program-specific heading) |
| `hacking-program:carbonite` | H | D | 1 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 55-61 (Program-specific heading) |
| `hacking-program:controlled-jump` | H | D | 1 | [REA-006](rules-explanation-audit-1.0.md#rea-006---controlled-jump-lacks-declaration-timing-and-opposing-cancellation), [REA-007](rules-explanation-audit-1.0.md#rea-007---speedballs-reuse-of-combat-jump-needs-the-faq-exclusion), [REA-018](rules-explanation-audit-1.0.md#rea-018---firewall-hacking-area-and-supportware-have-no-adequate-baseline-owner), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 55-61 (Program-specific heading) |
| `hacking-program:cybermask` | H | D | 1 | [REA-019](rules-explanation-audit-1.0.md#rea-019---nfbs-label-does-not-explain-suppression-and-duration), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 55-61 (Program-specific heading) |
| `hacking-program:enhanced-reaction` | H | D | 0 | [REA-018](rules-explanation-audit-1.0.md#rea-018---firewall-hacking-area-and-supportware-have-no-adequate-baseline-owner), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 55-61 (Program-specific heading) |
| `hacking-program:fairy-dust` | H | D | 0 | [REA-018](rules-explanation-audit-1.0.md#rea-018---firewall-hacking-area-and-supportware-have-no-adequate-baseline-owner), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 55-61 (Program-specific heading) |
| `hacking-program:oblivion` | H | D | 1 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 55-61 (Program-specific heading) |
| `hacking-program:spotlight` | H | D | 1 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 55-61 (Program-specific heading) |
| `hacking-program:total-control` | H | D | 2 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 55-61 (Program-specific heading) |
| `hacking-program:trinity` | H | D | 0 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 55-61 (Program-specific heading) |
| `hacking-program:white-noise` | H | D | 0 | [REA-019](rules-explanation-audit-1.0.md#rea-019---nfbs-label-does-not-explain-suppression-and-duration), [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 55-61 (Program-specific heading) |
| `hacking-program:zero-pain` | H | D | 0 | [REA-029](rules-explanation-audit-1.0.md#rea-029---the-collections-exact-wiki-archive-is-unavailable-locally) | S1 pp. 55-61 (Program-specific heading) |

## Scenario component inventory

D here also means selected clauses, not a complete scoring-engine acceptance.
All components belong to C. Geometry was inventoried for identity and references;
coordinate/footprint calculations and visual rendering were not independently accepted.

| Component identity | Kind | Tier | Clause evidence |
| --- | --- | --- | --- |
| `setup:standard-opposed` | setup | D | S1 pp. 150-155, Army-Points/SWC/table/deployment rows |
| `setup:minimum-vp` | setup | D | S1 pp. 151, 153, minimum VP; scenario-local Domination override preserved |
| `end-condition:round-limit` | end-condition | D | S1 pp. 150, 152, 154-155, third Game Round |
| `end-condition:all-troopers-null` | end-condition | D | S1 pp. 150, 155, Tactical check/end of Player Turn |
| `end-condition:minimum-victory-points` | end-condition | D | S1 pp. 152, 154, Tactical VP check/end of Player Turn |
| `geometry:standard-150-points` | geometry | S | Authored component/reference identity only |
| `geometry:standard-200-250-points` | geometry | S | Authored component/reference identity only |
| `geometry:standard-300-400-points` | geometry | S | Authored component/reference identity only |
| `objective:domination-dominate-quadrants` | objective | D | S1 p. 151, timing/comparison/at least one for equal award |
| `objective:domination-hacked-consoles` | objective | D | S1 p. 151, one point per Console at game end |
| `objective:supplies-controlled-boxes` | objective | D | S1 p. 153, two per controlled box |
| `objective:supplies-more-boxes` | objective | D | S1 p. 153, comparison bonus |
| `objective:supplies-all-boxes` | objective | D | S1 p. 153, additional all-boxes bonus |
| `objective:annihilation-destroy-forces` | objective | D | S1 p. 149, selected scoring-band comparison |
| `objective:annihilation-preserve-forces` | objective | D | S1 p. 149, selected bands and reviewed 350-point discrepancy |
| `objective:annihilation-eliminate-command` | objective | D | S1 p. 149, Lieutenant objective |
| `objective:firefight-surviving-specialists` | objective | D | S1 p. 155, comparative surviving Specialists |
| `objective:firefight-killed-specialists` | objective | D | S1 p. 155, comparative killed Specialists |
| `objective:firefight-killed-lieutenants` | objective | D | S1 p. 155, comparative killed Lieutenants |
| `objective:firefight-killed-army-points` | objective | D | S1 p. 155, comparative killed Army Points |

## Auxiliary curated collections

| Collection | Disposition |
| --- | --- |
| `maintained-text-link-reviews.json` | Review-exception contract consulted; no exceptions changed. A resolvable wrong-domain link still requires contextual review (REA-031). |
| `enrichment-coverage/classifications.json` | Coverage bookkeeping discovered; not proof of interaction explanation acceptance. |
| `peripherals/army-identities.json` | Identity layer distinguished from subtype gameplay explanations; no Unit mapping audit claimed. |
| `identities/*.json`, `relationships/historical-unit-endpoints.json` | Enumerated as other curated data; outside rules explanation adjudication. |
| `rules/example.json` | Reserved empty example; excluded from ingestion and the 367 denominator. |

## FAQ coverage disposition

All four numbered FAQ content pages were read. The table groups the questions by
mechanic instead of claiming an individual ruling migration. Source S2 is not registered
in C/H, and no FAQ data was authored. ITS headings retain ITS applicability.

| FAQ printed page | Mechanic | Audit disposition |
| --- | --- | --- |
| 1 | Deployment repositioning; Minelayer/Decoy/Holoecho private measurement; declaration details | Screened; useful deployment/timing baseline batch, not complete existing prose |
| 1 | Prone entry/exit; end-of-move Prone; vaulting in Climb/Jump | Compared to lifecycle/movement cards; REA-015; full geometry acceptance excluded |
| 1 | BS Attack labels and MODs; no shooting Direct Templates round corners | Screened; SD/Long Skill/label restrictions in REA-003/REA-021/REA-026 |
| 1 | Controlled Jump versus Speedball; Device Firewall disabled by States | Selected clause review; REA-007/REA-018 |
| 1-2 | Vertical Deployables; occupied intended placement | Selected clause review; REA-023 |
| 2 | Multiple Surprise Attacks; MSV1 plus Sixth Sense | Screened against relevant cards; no universal MOD cancellation inferred |
| 2 | Declare Stealth in Marker State; mixed activation ARO targeting | Selected clause review; REA-016 |
| 2 | Protheion overkill | Selected clause review; REA-008 |
| 2 | Camouflage (1 Use), failed Infiltration | Screened; deployment/variant follow-up, not a blanket new rule |
| 2 | Aerial versus Boost | Positive explicit exception verified |
| 2 | Controller unable to perform Skill; Peripheral can still act | Selected clause review; REA-017 |
| 2 | No placement/movement ending on Deployable Cover | Selected clause review; REA-036 |
| 2 | SD in Coordinated Orders | Baseline context screened; REA-021/REA-026 |
| 2-3 | Unconscious/Disconnected do not prevent Marker return/Cautious Movement; a revealed concealed element may still be in Total Cover | Screened; REA-015; complete Marker/geometry examples remain open |
| 3 | Fireteam SD/+1 BS not Discover; Type unchanged on loss; required member/minimum only at creation except FT Master | Selected clause review; REA-020/REA-021 |
| 3 | ITS: HVT movement; Spotlight Classified successes versus State entry | ITS-only context screened; no core Hacking mutation |
| 3 | ITS: scenario-element carrier cannot enter Marker State | Scope question retained; REA-030 |
| 3 | ITS: Oppose Activation, Netrod/Imetron deployment, Akial card timing/reuse/history/tracking | Screened as outside complete core curation; existing RR/RS research distinguished |
| 4 | ITS: nearest Deployment Zone during Impetuous; undeployed Ancillary not Killed | Scope question retained; REA-030; not silently applied to core missions |

## Validation results

Validation date: 2026-10-09. Commands used the project virtual environment.
No findings were implemented or data regenerated.

| Check | Exact result | Limits |
| --- | --- | --- |
| Documentation `git diff --check -- docs` | Exit 0; no output or diagnostics | Applies to modified tracked documentation |
| New report and inventory `git diff --no-index --check` against an empty temporary file | No whitespace diagnostics; each exits 1 because new files differ from empty | Both new files checked without staging them; earlier trailing spaces were corrected |
| Full `git diff --check` | Exit 0; stdout empty; 783 permission-denied diagnostics for pre-existing SVG paths | Does not establish complete readability of those unrelated assets; scoped documentation check above is clean |
| New documentation link/anchor check | 302 link occurrences valid, including the two integration links; 8 distinct external URLs syntactically valid | External reachability is the source-register research, not a blanket online link certification |
| Finding register | 37 unique contiguous IDs REA-001 through REA-037; all have classification, severity, priority, affected identities, current text/behavior, evidence, fix and dependencies | Source discrepancies remain explicitly Unresolved/Derived where indicated |
| Remediation plan | All 37 IDs included in batches A-G | Proposed work only |
| Record inventory | 367 IDs exactly match collection order; 217 D + 150 S; 314 outgoing relations; kind totals reconcile | Selected clauses, not every source clause or edge independently approved |
| Scenario component inventory | 20 unique IDs match C; 17 D + 3 S | Geometry excluded from visual reacceptance |
| Severity arithmetic | 24 High + 12 Medium + 1 Low + 0 Critical = 37 | No blanket correctness percentage |
| Protected JSON/database/configuration inputs | 35 SHA-256 comparisons unchanged | Includes curated JSON, maintained validation mappings and existing generated databases; not a claim to have rehashed every raw asset |
| Repository change boundary | Exactly four added/modified task paths, all Markdown under `docs/`; no pre-existing status entry removed or changed | Pre-existing asset deletions/inaccessibility preserved; no code/data/schema/test/runtime changes made |
| Existing interaction checklist check | Exit 0: primary 182/182; supporting 111/126, 15 pending; 314 relations; 113 future candidates | Historical review policy check, not a 1.0 explanation-completeness gate |

The four task paths are `docs/rules-explanation-audit-1.0.md`,
`docs/rules-explanation-audit-1.0-inventory.md`, `docs/README.md`, and `docs/TODO.md`.
The first two are new, non-ignored Markdown files, ready to add to a documentation
commit; no commit or staging operation was requested or performed.

No full pytest/Ruff/Pyright run, database build, checklist regeneration, real-browser
acceptance, live Army acquisition, or whole-project release audit was performed.
No dedicated Markdown/documentation validation stage was found in the standard
check runner; read-only link/anchor/identity/arithmetic checks supplied the relevant
lightweight verification. Semantic findings and unresolved research questions were
reviewed once more for overlap and inconsistent conclusions before finalizing.
