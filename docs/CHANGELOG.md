# Changelog

All notable user- or operator-relevant changes to InfinityDB are documented here.
Each release with entries begins with a concise **Player summary** containing only changes visible
or useful to players; an empty `Unreleased` heading is omitted from the browser page. The remaining
sections preserve fuller user/operator release detail. Entries describe
meaningful release outcomes rather than detailed implementation history. New or materially revised
entries use the project-domain labels defined in `docs/project-domains.md`; historical release notes
are not retroactively relabeled.

## [Unreleased]

### Player summary

- Continuous Damage and Non-Lethal Trait pages now link directly to
  their reviewed official Infinity Wiki headings.
- Army source items now appear in their proper Unit categories:
  Equipment, Training and loadout Attribute overrides.
  Source-only markers no longer generate non-existent Skill links.
- Hacking Area now cites the correct N5.3 page and explains
  when a Hacker, a Comms Attack target, or a delayed
  Camouflaged Marker can generate separate ARO opportunities.
- Suppressive Fire now distinguishes its Long Skill declaration
  from the State's B3 ARO and explains the G: Jumper exception
  when a different Proxy is activated.
- Speculative Attack now explains the Circular Template ARO
  sequence and why an out-of-LoF target can Dodge the
  incoming template before the attack Roll is resolved.
- Peripheral (Cyberplug) now explains why a Connected Controller
  may be attacked while performing Idle and how its own ARO
  changes Connected/Autonomous reactions.
- Alert! now correctly explains its automatic eligibility
  and after-Saving-Rolls facing adjustment, rather than
  treating it as a declared ARO.
- Cautious Movement now explains when it suppresses AROs,
  including Hackable Troopers, Stealth, Hidden Deployment,
  and the importance of both movement endpoints.
- Discover now makes its LoF requirement and same-Marker
  retry restriction explicit, including how a revealing ARO
  affects a combined Discover + Attack Order.
- Reload and Place Deployable explanations now distinguish
  reactive declaration requirements from Baggage's automatic
  recovery and deployable activation in subsequent Orders.
- Look Out! now explains its special allied Dodge (PH-3)
  ARO, ally selection, roll opposition and scope, with
  a direct citation to N5.3.
- Combat Instinct and Sixth Sense now distinguish their separate
  Stealth counters: only Sixth Sense grants an attack-only
  outside-LoF response, not a general ARO against movement.
- Guard and Aerial now explain their targeting exception: active
  Aerial targets prohibit Guard, whereas Unconscious targets
  remain eligible subject to Guard's LoF and ZoC requirements.
- Guard and Neurocinetics now link directly to their N5.3 definitions,
  alongside their historical Wiki citations.
- Climbing Plus and Super-Jump now explain conditional Short Skill
  declarations, trajectory and 360-degree LoF, Impetuous use,
  and the Jet Propulsion limitation.
- Sensor now cites its actual N5.3 Short Skill definition (p. 111).
  The named BS=11, BS=12 and CC=21 Army variants retain their exact
  numerical replacements and links to BS Attack and CC Attack.
- Automatic Skill categories now cite their correct N5.3 headings,
  including Hacker, Super-Jump and Surprise Attack. Regular is
  no longer incorrectly linked as an Automatic Skill.
- Booty, Decoy, MetaChemistry, Remdriver and Strategic Deployment now
  display their correct Deployment Skill category instead of Automatic,
  with direct N5.3 source citations.
- Deployment and Long Skill declarations now cite their correct N5.3
  definition pages. Jump and Climb, and Combat Jump and Parachutist,
  each retain their own source provenance rather than sharing a
  citation from a different Skill.
- BS Attack, CC Attack and Discover now cite their actual N5.3
  definition pages; Morpho-Scan is classified only as a Short Skill,
  not as a Basic Short Skill or ARO. Profile-specific numeric Skill
  values remain sourced separately from their action rules.
- Glossary deep links now keep headings visible below the compact
  navigation bar; reference previews no longer reopen detached
  tooltips when moving between pages.
- Visibility Zone help now distinguishes additive Range, Cover, Skill and
  Equipment MODs from the non-stacking, most-restrictive Zone MOD.
- Mines now explicitly measure their Trigger Area from the edge of
  the Mine's base and exclude Total Cover from the template's Blast Focus.
- Modifiers Explained now covers bracketed-only-on-use MODs,
  positive/negative recipients and one-die ReRoll, with a
  link to existing Special Dice rules. Mixed Weapons also
  links Vorpal CC Weapon and its PH-based BS Mode without
  changing imported profiles.
- Mixed Weapons now have one shared N5.3 source-backed rule
  linked from Trench-Hammer and Kobra Pistol. The reference
  explains distinct BS/CC modes and Trench-Hammer's PH-based
  BS exception; existing Kobra source disputes remain visible.
- Mine pages now show the weapon-specific profile before the long
  shared Mines rules; Cybermine and PARA Mine-specific cards
  also precede the family text. Cybermine displays absent
  ammunition as "--" rather than the imported numeric 0.
  Chest Mine BS/CC modes and source profiles are unchanged.
- Deactivator now distinguishes same-Order Mine and
  Cybermine triggers, Boost contact attacks and Armed
  Turret reactions, including concealed Marker
  ineligibility and each item's existing conditions.
- Deactivator now explains eligible enemy deployed targets,
  Range-only WIP removal, the same-Order trigger exception,
  and how removal ends persistent Dazer, Repeater and
  Deployable Cover effects. Allied Disco Ball activation
  remains a separate Skill.
- Dazer now distinguishes ordinary placement from the
  persistent Difficult Terrain area it generates, including
  Conclusion activation and destruction/deactivation.
  The published S0/S1 Silhouette disagreement remains visible.
- FastPanda and WildParrot now distinguish Perimeter placement
  from later Repeater or E/M Mine effects, with visible object
  Attributes and Conclusion-step timing. WildParrot explains
  failed Intuitive Attack consumption; its Non-Lethal source
  discrepancy remains explicitly unresolved.
- Deployable Repeater now distinguishes ordinary Place Deployable
  placement from Pitcher delivery, explains the resulting Token's
  Hacking Area effects, and links canonical Repeater targeting
  and removal rules. Disco Ball lifecycle tests confirm that
  deactivation preserves the Ball while destruction removes it.
- Pitcher and Disco Baller now explain launcher charge consumption,
  deployed-object Attributes, legal landing locations and
  occupied-position corrections. Disco Ball reactivation remains
  a separate Deactivator action, not another launcher shot.
- Mine Dispenser now explains inherited Drop Bears BS Mode
  restrictions, the shared CAMO placement exception, and
  failed-roll Disposable consumption without granting Drop
  Bears' separate Deployable or Intuitive Attack options.
- Drop Bears now explain why direct placement requires no Roll,
  Intuitive Attack placement uses WIP and consumes a charge on
  failure, and throwing uses a PH-based Roll with the same
  shared Disposable pool. Activation remains at the Order's
  Conclusion; imported weapon profiles are unchanged.
- Boost now distinguishes placing a device near a CAMO Marker from
  triggering it later. The clarification covers the non-Camouflaged
  enemy placement exception, legal Intuitive Attack eligibility,
  activation timing and the different Mine trigger rules.
- Mines now explain why a qualifying Dodge declaration may trigger
  them, while subsequent Dodge or failed-Guts movement cannot;
  canonical Dodge, Guts Roll and Stealth references remain linked.
- SymbioBomb now explicitly identifies its three printed Traits:
  Assignable (Transmutation), Comms Attack and Optional. Its published
  Pheroware behavior is unchanged.
- Armed Turret now explains Disposable (1), Non-Reloadable, and
  Perimeter placement inside the deploying Trooper's Zone of Control,
  with a direct Place Deployable reference. Source disputes remain.
- Mines now distinguish a concealing CAMO Marker (S2) from the revealed
  Mine object, whose S0/S1 values conflict across published sources.
  The distinction does not change any Weapon profile or Chest Mine rules.
- Silhouette help now explains the valid S0 and SX templates alongside
  the existing S1-S8 comparison diagrams, without treating their absence
  from the illustrations as a missing rule.
- AP Thunderbolt, AP+EXP CC Weapon and Stun Pistol now disclose conflicting
  Wiki chart values beside the current N5.3/Army weapon rules; the imported
  profiles and gameplay effects remain unchanged.
- The Scenario browser now offers a collection selector for N5 Core and
  published ITS missions. Season 18 starts with Battleground, including
  its end-of-game Sectors, size-dependent map, 2/3/5-point scoring and
  special rules. Shared scenario links retain the exact season and game size.
- Pitcher and Mine Dispenser now explain what their successful shots
  place on the table, how those deployed objects behave, and how launcher
  Traits and charge counts differ from the resulting Equipment or Mines.
- Marksman Rifle profiles now explain their shared range/PS baseline, with
  direct links to each variant's Ammunition and Traits. MULTI modes stay
  separate, and Breaker keeps its own BTS-based AP explanation.
- Light and Heavy Flamethrowers now share linked Direct Template,
  Intuitive Attack and Continuous Damage help, while clearly distinguishing
  their Small/Large Teardrop areas and PS values.
- Fireteam Type now has a separate FAQ clarification: a surviving HARIS
  does not become a DUO when it loses a member. The Spanish FAQ's
  inconsistent example count remains visible as a source discrepancy.
- Dated FAQ v0.1 clarifications appear alongside Hacking Device,
  Annihilation, Skill, Trait, State, General Rule and Fireteam references.
  New entries explain Skill declaration, fired Deployables, Peripheral
  restrictions, Camouflaged Markers in Total Cover, Special Dice in
  Coordinated Orders, and Fireteam creation minimums. Eight additional
  carried-forward v0.0 clarifications cover Prone, Climb/Jump, template
  LoF, Deployables, Surprise Attack, Sixth Sense/MSV1, Protheion and
  Camouflage (1 Use). Another ten carried-forward clarifications
  cover Deployment private checks, Prone distance, BS MODs, Controlled
  Jump, automatic Marker State declarations, Aerial/Boost, Stealth
  AROs, Deployable Cover, inactive States and Discover bonuses.
  The final general Deployment Phase repositioning clarification now
  lives on its own General Rules page, separate from particular
  deployment Skills. All show their earlier source version beside
  the selected v0.1 citation.
- Domination's 350-point SWC displays the English-source 6, with an explicit
  discrepancy: official Spanish N5.3 says 7. The Annihilation 350-point
  survival bands are now corroborated by official Spanish N5.3 rather than
  inferred solely from English table continuity.
- PARA clarifies its missing-PH exception and re-infliction after recovery.
  Shock explains when its VITA 1 effect bypasses Unconscious protections;
  Stun explains Guts Rolls and the specific Flash Pulse Immunity exception.
- EXP now explains its mandatory three Saving Rolls and fourth Critical roll,
  including AP+EXP. T2 distinguishes its two-Wound hit from its one-Wound
  additional Critical roll and retains a source-language discrepancy.
- AP Ammunition now explains its Saving Rolls and conditional Immunity cases;
  E/M explains when a failed save causes Isolated/Immobilized-B and why
  some affected troops cannot make the ordinary Guts Roll.
- DA Ammunition now explains why its second Saving Roll is still required after
  the first fails or causes Unconscious. Smoke now explains how scenery blocks
  portions of its otherwise infinite-height Template; Eclipse links to the
  shared Smoke rules while retaining its visor exceptions.
- Dense Unit profiles and loadouts remain readable on narrow screens: Attributes,
  Skills, Equipment and Includes no longer crowd adjacent content, and long
  loadout names can wrap without losing Points or SWC.
- Narrow rules-reference pages no longer clip the breadcrumb's
  "Rules reference" tag on 320 px screens.
- Shared Weapon rules such as Mines are now discoverable in the Glossary,
  with links that open the existing rule card on an actual Army Weapon page.
- Stealth now gives concrete examples of how Deployables still trigger,
  when a mixed-activation ARO targeting a Stealth user becomes Idle, and
  why Stealth must be announced when used in Marker form.
- Immunity (ARM/BTS) now highlights its separate protection against
  applicable weapon Traits, with linked examples; the printed Monofilament
  Critical case and Flash Pulse's Non-Lethal/Stunned exceptions are clearer.
- Recovery and re-infliction in the same Order are now explained with
  the Engineer/Riotstopper example: cancel IMM-A first, then resolve a
  new PARA Saving Roll, which can inflict IMM-A again.
- Request Speedball now explicitly shows why its PH 15 Token Rolls
  cannot receive Controlled Jump +3/-3, even when either player's
  Program is active. The FAQ exemption does not remove other modifiers.
- Controlled Jump now illustrates how its optional ARO affects the
  current Combat Jump immediately, why two active Programs cancel
  each other without removing Firefight's +3 landing bonus, and why
  non-Hackable Troopers but not Speedball Tokens are affected.
- BS Weapon (WIP) now explains why normal WIP-based attacks work,
  while BS Attack (Shock) and Guided are prohibited; Shock Ammunition
  itself is not universally prohibited.
- Continuous Damage now includes an example showing that a failed ordinary
  hit Saving Roll repeats, while an additional Critical Saving Roll does not.
  Applicable Immunity is explained separately without changing the rules.
- Intuitive Attack now includes worked examples of its single unmodified
  WIP attack, opposing AROs and Main Target Critical, plus the separate
  Deployable placement condition and failed-use cost.
- Doctor now includes concrete explanations of ordinary Unconscious
  recovery and its lethal failure, Stunned, NWI self-treatment and
  Technorganic STR exceptions without granting routine healing to
  conscious wounded Troopers.
- Engineer now includes practical examples distinguishing STR Wound
  repair from canceling Targeted on a VITA Trooper, including why a failed
  cancellation does not cause a Wound and why Stunned uses Doctor for VITA.
- The Fireteam Level reference now gives a concrete five-member Morat
  CORE example that earns Level 3 bonuses only. Its source note discloses
  why both N5.3 printed examples incorrectly add Level 4's +1 BS/CD;
  the actual Fireteam bonuses have not changed.
- Armed Turret's disputed E/Mitter mode now explains the one-versus-two
  BTS/2 Saving Roll source conflict in a separate note with links to
  E/Mitter and E/M Ammunition. Its imported profile remains unchanged
  pending an official ruling.
- Armed Turret now identifies its contradictory Silhouette sources:
  detailed profiles list S2 while summary charts list S1. The visible
  profile remains S2 pending an official clarification, and the size
  difference is explained for Line of Fire and clearance.
- Doctor and Engineer now distinguish direct contact from delegated
  Servant/Cyberplug treatment and the separate Allied-only Kit rules.
  Their Engaged restrictions are clearer; non-Allied direct treatment
  remains an unresolved rules interpretation rather than an assumed right.
- Dodge (ARM+3) now explains when its profile-listed ARM protection
  applies, without changing the Dodge PH Roll. The reference also
  distinguishes the two N5.3 PDF descriptions from both language Wiki
  versions that require a failed PH Roll.
- Special Dice and Fireteam reference pages now disclose the Spanish
  N5.3 contradiction over six dice versus B6 plus extra Special Dice.
  The sourced B6/SD distinction remains unchanged; an official correction
  is still outstanding.
- Infinity Spec-Ops now links to the complete Request SpecBall procedure:
  when a drop can be requested, how the token is placed and collected,
  and when the Enhanced Profile takes effect. The separate Request Speedball
  and Season 18 TEAM-OPS rules remain distinct.
- TinBot references now explain when their benefits are shared by a Fireteam,
  why matching bonuses do not stack, and how owner isolation, departure or death affects them.
- Sixth Sense and Multispectral Visor now explain the FAQ's joint
  Level 1 exception for a target attacked through a Zero Visibility Zone.
  ITS Spotlight and Ancillary scoring clarifications remain explicitly
  mission-scoped rather than changing core scenario rules.
- Kobra Pistol's CC reference now separates the two Saving Rolls required
  by DA Ammunition from the disputed Anti-materiel Trait, preserving the
  imported weapon profile and keeping BS Mode independent.
- BioWeapon now links its VITA-only DA+Shock effects to the underlying
  Ammunition rules. Viral Mine explains why its printed one-BTS-roll
  profile remains the baseline while the shared Viral Property describes
  target-dependent Saving Rolls and Shock exceptions.
- Weapon profiles now link named **Weapon Properties** such as Plasma, Viral,
  Breaker, K1, MULTI, Monofilament, Silenced and combined Ammunition, including
  N+E/M, to searchable Glossary explanations and their originating rules. Links provide the same preview
  interaction as other rules references; shared Viral and Plasma explanations
  no longer need to be repeated in individual weapon summaries.
- Fireteam help now distinguishes actions performed only by the Team
  Leader from shared movement and reactive AROs. It explains when members
  leave, when the entire team cancels, how rejoining works and why the
  DUO/HARIS/CORE counts apply to formation rather than ongoing membership.
- Discover and Impersonation references now distinguish normal modifiers
  from IMP-1's penalty and explain when a failed attempt may be retried.
  Deployable Cover now identifies all of its listed properties alongside the
  Vitroferro Saving Roll cap.
- **What's changed** now includes upcoming-release notes alongside past releases when there are new changes to show.
- Breaker Marksman Rifle is now directly searchable and viewable even when
  no Army Unit currently references it; its rules reference preserves the
  official profile and distinguishes the conflicting update-notice name.
- Weapon profiles now offer expandable, linked explanations of shared Ammunition
  effects. New Weapon references clarify CC and Pistol variants, MULTI and K1
  Rifles, D-Charges, Disco Baller, and SymbioBomb while preserving their
  different modes and Saving Rolls, including Feuerbach's Burst/Explosive
  options, the Hyper-Rapid Magnetic Cannon's three firing modes, and
  MULTI Heavy Machine Gun's EXP, AP and Shock modes, MULTI Spitfire's
  DA, AP and Shock modes, and Flammenspeer's Blast versus Hit effects.
  Sniper Rifles now distinguish the MULTI's DA/AP/Shock modes, K1's ARM=0
  Saving Roll, Viral's conditional BioWeapon and Plasma's separate ARM and
  BTS Saving Rolls; standard, AP and T2 variants reuse canonical effects.
  Armed Turret now warns where Army's E/Mitter mode disagrees with the
  N5.3 weapon charts about the number of Saving Rolls.
- Peripheral and its five subtype references now explain activation,
  Coherency, Doctor/Engineer delegation, Controller and Peripheral rolls,
  and Cyberplug Connected/Autonomous exceptions.
- Coordinated Orders now have a linked reference covering Spearhead, shared
  declarations, Burst, reactive targets, recovery and Hacking exceptions.
- The Order Expenditure Sequence now explains declaration choices, both ARO
  checks, Resolution timing, invalid declarations and simultaneous effects.
- A new Guts Roll reference explains when to roll, the order of withdrawal
  options, the revised Line of Fire check, and Courage, Religious Troop and
  Stun Ammunition exceptions.
- Face to Face Rolls and Saving Rolls now have linked explanations of opposing
  results, Criticals, ties, defense values and special Saving Roll exceptions.
- Deployable placement references now explain Active/Reactive contact,
  passable Perimeter paths, Minelayer exclusions, occupied-position
  alternatives and the timing of activation. Armed Turret identifies its
  enemy-Model-only reaction without changing unresolved source profiles.
- Recovery Kit references now explain why one successful target PH Roll
  is enough among multiple hits in the same Order, with only one Wound
  removed under the ordinary rule; GizmoKit retains Remote Presence's
  exception. Disposable and Double Shot now distinguish additional Burst
  charges from Special Dice with concrete remaining-use examples.
- Special Dice now have a linked reference explaining extra-die allocation and
  discard timing, Fireteam and Martial Arts bonuses, and exceptions. Fireteam
  Level 2's +1 SD bonus now links directly to that explanation.
- Hacking Area, Firewall and Supportware now have their own linked references, with
  enemy Repeater restrictions, Firewall Saving Roll bonuses and Supportware replacement
  explained alongside Hacking Programs.
- Negative Feedback (NFB) now explains which effects it overrides on a Trooper and
  how long Cybermask and White Noise restrict other NFB effects.

### Added

- **Data processing + Web backend + Web frontend:** Add source-reviewed
  Pitcher and Mine Dispenser references. Pitcher deploys Repeaters without
  a damaging Saving Roll; Mine Dispenser inherits Drop Bears BS-mode
  placement, not Drop Bears' PH or Shock Mine profile. Link canonical
  targetless, ammunition/Equipment, Disposable and Double Shot rules,
  with cited placement and source-profile qualifications.
- **Data processing + Web backend + Web frontend:** Publish shared N5.3
  Marksman Rifle guidance for six single-mode source identities and one
  separate MULTI three-mode reference. Use exact source profiles and
  mode-specific canonical Ammunition/Trait links; retain the existing
  Breaker definition, source spelling of MULTI Anti-Material Mode, and
  explicit non-stacking/anti-materiel exceptions.
- **Data processing + Web backend + Web frontend:** Add one source-reviewed
  rules reference shared by Light and Heavy Flamethrowers, linking their
  Direct Template, Intuitive Attack, Continuous Damage and Normal Ammunition
  rules. Each keeps its original Army Weapon profile; no attack or Saving Roll
  semantics are duplicated or changed.
- **Data processing + Web backend + Web frontend:** Publish Request SpecBall
  as its own linked N5.3 Skill, including round and eligibility restrictions,
  PH 15 drop, token placement, two different support items, profile transfer,
  and SpecBot handling. Preserve the English/Spanish wording discrepancy
  and Season 18 ITS tournament restriction as source-specific notes.
  Imported Army data and roster customization remain unchanged.
- **Data processing + Web backend + Web frontend:** Introduce searchable,
  rules-linked Weapon Properties as a Glossary vocabulary. Reviewed weapon
  profiles link to their Property and its original Ammunition, Trait or
  other rules sections, with hover, keyboard and touch previews. Shared
  Viral and Plasma rules explanations now support shorter individual
  weapon summaries; relevant reference prose also links directly to shared
  Properties. E/M CC Weapon now explains how its N+E/M Ammunition can cause
  Wounds and conditional disabling States without implying extra Saving Rolls.
  Imported profiles and conditional gameplay behavior are unchanged.
- **Data processing + Web backend:** Add source-cited Weapon explanations for
  common CC Weapons and Pistols, D-Charges, Disco Baller and SymbioBomb,
  distinguishing mode-specific requirements and exceptions without changing
  published Army profiles. Explain MULTI Rifle's alternative firing modes and
  K1 Combi Rifle's printed Normal Ammunition with ARM=0; other reviewed Rifles
  reuse existing Ammunition and Trait rules.
- **Data processing + Web backend:** Explain Feuerbach's AP+DA Burst Mode
  versus EXP Explosive Mode and the Hyper-Rapid Magnetic Cannon's three
  mode-specific Burst, Saving Roll and Trait combinations, plus the
  MULTI Heavy Machine Gun's EXP Anti-materiel versus AP/Shock modes,
  and MULTI Spitfire's DA Anti-materiel versus AP/Shock modes. The
  official Spitfire mode label is distinguished from Army's source
  spelling without changing the imported profile. Flammenspeer's
  Normal circular Blast and AP Hit Modes retain shared Continuous
  Damage and Disposable (2) charges.
  MULTI, K1, Viral and Plasma Sniper Rifles now distinguish alternative
  firing modes, conditional target effects and Combined Saving Rolls using
  source-linked definitions. Other reviewed Weapons continue to reuse
  source-backed Ammunition and Trait references.

### Changed

- **Data processing:** Verify Katyusha MRL and Jammer as shared-effects-only
  Weapon references. Katyusha's `+3` range modifier is already established
  by RR-SRC-N53-003; preserve the PDF omission. Jammer's Comms Attack,
  No LoF and Isolated references resolve as Labels/State rather than
  Trait slugs. Pending source reviews decrease to 11 without changing
  Army profiles or adding duplicate mechanics.
- **Data processing:** Review four Grenade Launchers and Portable
  Autocannon as hash-pinned shared-effects-only cases. Canonical
  Ammunition, Impact Template, Speculative Attack and AP+EXP rules
  already explain their effects. Preserve Eclipse's non-operative
  imported Saving Roll number. Pending Weapon reviews fall to 13.
- **Data processing:** Review E/M Carbine, AP+T2 CC Weapon,
  Monofilament CC Weapon, and Light/Heavy Riotstoppers as
  profile-hash-pinned shared-effects-only references. Existing
  Ammunition, Trait and Weapon Property rules describe their effects,
  without introducing duplicate Weapon cards. Retain source
  discrepancies for AP+EXP CC Weapon and Stun Pistol: archived
  Spanish Wiki Saving Roll counts differ from official N5.3/Army.
  Remaining source reviews decrease to 18.
- **Data processing:** Accept five additional source-verified,
  profile-hash-pinned shared-only Weapons: Tactical Bow, Ohotnik,
  T2 CC Weapon, AP+DA CC Weapon and AP+Shock CC Weapon. Reuse
  canonical Ammunition, Trait and Weapon Property explanations,
  preserving one-versus-two Saving Roll differences. Pending Weapon
  source reviews fall to 23 without adding duplicate rule cards.
- **Data processing:** Review Red Fury, AP Red Fury and Thunderbolt as
  source-pinned shared-effect profiles, using existing Shock, AP, Normal
  Ammunition and Suppressive Fire references. Retain AP Thunderbolt as
  a pending source discrepancy: official N5.3 and Army print AP,
  while archived English and Spanish Wiki charts print N. Remaining
  Weapon source reviews decrease to 28 with no gameplay-data changes.
- **Data processing:** Reconcile Weapon definition gaps against a freshly built
  rules database and N5.3 source-chart evidence. Explicitly accept Breaker Rifle,
  Viral Combi Rifle, Viral Rifle, Viral Pistol and Viral Tactical Bow as
  hash-pinned, shared-effects-only references: current AP/Normal Ammunition,
  BioWeapon, Silent, Suppressive Fire and Weapon Properties already cover their
  mechanics. Remaining source reviews decrease to 31; Weapon profiles and
  player-facing behavior are unchanged.
- **Data processing:** Introduce validated dated FAQ ruling authoring fields
  for exact applicability, original provenance, reviewed source selection,
  conflicts and explicit supersession references. Rules export now rejects
  missing topic/scenario/predecessor targets, cycles, non-overlapping
  supersession and inconsistent carried-forward origins. Add an
  applicability-aware read model and explicit-context FAQ API, retaining
  reviewed source provenance and conditional supersession. Twenty-eight
  reviewed FAQ entries now reach their owning Equipment, Scenario, Skill,
  Trait, State, General Rule, Hacking Program and Fireteam browser surfaces
  through shared dated clarification cards. Nineteen entries retain v0.0
  original source citations and current EN/ES v0.1 evidence, without
  duplicating rulings. The newly modeled Deployment Phase uses its
  official N5.3 source; its FAQ remains a separate dated overlay.
  The Fireteam detail stays on the Fireteams page rather than inventing
  a rule route. A separate Fireteam Type ruling preserves the English
  three-to-two-member HARIS example; a disclosure links the Spanish FAQ's
  contradictory count without overriding the shared rule. Base rules remain unchanged.
- **Data processing + Web backend + Web frontend:** Add strict current
  scenario collection/revision selection to catalog and list/detail/map
  APIs and a browser collection picker generated from published missions.
  Preserve the default N5.3 Core catalog and reject unknown revisions
  without substituting another season. Publish the first real ITS Season 18
  scenario, Battleground, with sourced scoring, geometry and special rules;
  season-aware share URLs survive changes of Army Points and reloads.
  Other ITS missions and scenario-specific FAQ applicability remain open.
- **Data processing + Web backend:** Verify all 24 core-scenario Army Points
  selections against the N5.3 source charts, composed database and public API.
  The Spanish N5.3 Annihilation table confirms the corrected 350-point survival
  bands; Domination's Spanish/English 350-point SWC conflict remains visible,
  without overriding the existing English-source value.
- **Web frontend:** Wrap narrow shared detail breadcrumbs without hiding
  the reference tag; verified Visibility Zone and Ammunition/Immunity
  cross-reference navigation with pointer, keyboard and touch.
- **Project infrastructure:** Add a lockfile-pinned Markdownlint documentation stage to the
  project check runner and required `--all` CI workflows. Documentation validation runs without
  automatic dependency downloads; Node.js tooling remains development-only.
- **Web backend + Web frontend:** Include curated Weapon definitions in
  Glossary using opt-in Army links for canonical family/variant destinations.
  Preserve standalone Army Weapon routes and omit source-mode-specific
  subrecords from independent Glossary identities.
- **Data processing + Web frontend:** Add source-backed Stealth
  examples and English/Spanish N5.3/FAQ citations for independent
  Deployable triggers, mixed Controller/Peripheral activation, and
  Marker announcements. Keep existing ARO and counter-Skill mechanics.
- **Data processing + Web frontend:** Complete REA-010 Immunity reference
  acceptance with linked Trait-protection examples, Monofilament
  one-/two-roll wording, and bilingual N5.3 source verification.
  Preserve conditional Immunity cases, evidence labels, imported weapons,
  and the existing Flash Pulse source-conflict disclosure.
- **Data processing + Web frontend:** Complete REA-009 State/recovery
  timing reference acceptance with bilingual N5.3 p. 15 sources,
  an explicit positive-before-negative resolution example, and links
  from Doctor, Engineer and IMM-A to the shared Order rules. Preserve
  existing State transitions, source data and game mechanics.
- **Data processing + Web frontend:** Complete REA-007 Request
  Speedball reference acceptance with a source-backed PH 15 worked
  example and regression coverage for the reciprocal Controlled Jump
  FAQ exception. Preserve the original PH values, placement rules,
  Combat Jump relation, and versioned provenance.
- **Data processing + Web frontend:** Complete REA-006 Controlled Jump
  reference acceptance with three worked timing, opposing-Program and
  Token-scope examples, bilingual N5.3 source citations, and linked
  Combat Jump/Speedball references. Retain all existing Supportware,
  scenario modifier and FAQ mechanics.
- **Data processing + Web frontend:** Complete REA-005 BS Weapon (WIP)
  reference acceptance with source-linked ordinary attack, Shock Skill
  versus Ammunition, and Guided examples, including Spanish N5.3 p. 39.
  Preserve source profiles, canonical attack relationships, and deferred
  exact-variant restriction edges.
- **Data processing + Web frontend:** Complete REA-004 Continuous Damage
  reference acceptance with ordinary-hit/Critical-only roll examples,
  conditional Immunity variants, and English/Spanish N5.3 citations.
  Preserve the underlying Trait, weapon data, and deferred graph edges.
- **Data processing + Web frontend:** Complete REA-003 Intuitive Attack
  reference acceptance with three source-linked examples and bilingual
  N5.3 citations. Preserve B1/WIP Attack resolution and existing placement
  mechanics without adding a second BS Roll or changing imported data.
- **Data processing + Web frontend:** Complete REA-002 Doctor
  reference acceptance with N5.3-cited examples for ordinary VITA
  recovery, Stunned, No Wound Incapacitation, and Technorganic.
  Preserve Doctor variant mechanics and pending non-Allied eligibility
  review; no recovery engine or imported Army profiles changed.
- **Data processing + Web frontend:** Complete REA-001 Engineer
  reference acceptance with source-backed VITA Targeted and
  VITA/STR Stunned examples, plus linked N5.3 source citations. Preserve
  existing recovery, failure, self-use and delegated target rules;
  non-Allied direct use remains separately unresolved under REA-038.
- **Data processing + Web frontend:** Publish a checked Level 3 Morat
  Fireteam example alongside the cumulative bonus table, with separate
  bilingual source notes for the contradictory Level 4 bonus in the
  printed examples. Preserve level requirements and the existing
  unrelated Special Dice source discrepancy.
- **Data processing + Web frontend:** Separate the Armed Turret E/Mitter
  Army/PDF Saving Roll discrepancy from normal weapon mechanics and its
  independent Silhouette discrepancy. Preserve the imported one-roll
  Turret mode, standalone two-roll E/Mitter, and cited bilingual sources;
  no new E/M ammunition exception is introduced.
- **Data processing + Web backend + Web frontend:** Add the bilingual
  Armed Turret Silhouette discrepancy to the weapon's secondary source
  notes, with PDF/Wiki citations and the different S1/S2 heights.
  Retain the detailed S2 curated profile; do not override Army data or
  treat either conflicting source cell as an official erratum.
- **Data processing + Web backend:** Clarify source-scoped Doctor and
  Engineer eligibility, including Engaged and close-combat restrictions,
  while preserving the independent Allied requirements for MediKit,
  GizmoKit and Peripheral delegation. The direct Skills do not gain a
  new allegiance gate or universal permission for non-Allied targets;
  source uncertainty remains explicit and tracked.
- **Data processing + Web backend + Web frontend:** Expand the Dodge
  Skill reference with source-cited (ARM+3) conditions, relevant Saving
  Roll links, and simultaneous-Attack interactions. Preserve the
  conflicting English/Spanish Wiki failed-PH prerequisite as reviewed
  secondary notes, not an unannounced override of the N5.3 PDF wording.
  No imported Army profiles or Dodge mechanics were changed.
- **Data processing + Web frontend:** Show the bilingual N5.3 Fireteam
  six-dice contradiction as source notes on the Special Dice reference and
  Fireteam quick reference. Explain B6 plus one SD without introducing an
  inferred Fireteam cap. Fireteam Level facts now permit optional curated
  source notes, rendered with the existing secondary-source styling.
- **Data processing + Web backend + Web frontend:** Show canonical Ammunition
  effects and source citations in an expandable section on Weapon profiles.
  Shared descriptions now also render inline rules links correctly (including
  Smoke and Eclipse visibility-zone references) instead of raw link notation.
  Shared effects use the normal reference links and touch previews, while each
  Weapon retains its own Saving Rolls, Traits and modes.
- **Data processing + Web backend:** Expand the shared Peripheral baseline
  and five subtype cards with source-cited operation, disconnection,
  recovery and exception rules, linked to Doctor, Engineer and Cyberplug.
- **Data processing + Web backend:** Publish a Coordinated Orders reference
  explaining shared Skill choices, reactive targeting, Burst adjustments and
  recovery and Special Dice exceptions, linked from relevant references.
- **Data processing + Web backend:** Publish a shared Order Expenditure Sequence
  reference and link it from commonly declared Skills, Guts Rolls and Disposable
  uses, including declaration-time exceptions and simultaneous recovery timing.
- **Data processing + Web backend:** Link the Guts Roll reference to relevant
  Skills, States and Stun Ammunition, including the N5.3 attacker-position
  clarification and compulsory failed-roll movement priorities.
- **Data processing + Web backend:** Add linked Face to Face and Saving Roll
  references for ordinary contest outcomes, Criticals, defense calculations and
  Attribute-based exceptions; connect BS and CC Attack cards to these shared rules.
- **Data processing + Web backend:** Explain how Special Dice differ from Burst
  increases and Disposable charges, including Fireteam bonuses, Martial Arts,
  ranged Kits, Berserk, and the Coordinated Orders FAQ; link the published
  reference from those rules without changing Army profiles.
- **Data processing + Web backend:** Publish linked N5.3 Hacking Area and Supportware
  General Rules and a Firewall Equipment reference, including the FAQ for disabled
  Hacking Devices. Connect existing Hacker, Repeater, TinBot and Hacking Programs to
  the shared mechanics without changing Army source values.
- **Data processing:** Clarify the one-active-NFB-effect rule and the separate
  Cybermask/White Noise lifetimes in the linked Label and Hacking Program references.
  Other Troopers' NFB effects remain independent.

### Fixed

- **Data processing:** Complete the 1.0 maintained rules-interaction review
  ledger, including Supplies' box placement, pickup/transfer, control scoring,
  Specialist restrictions, and mission endings. The source-backed checklist
  now has no pending supporting identities; the separate 1.0 release gate
  remains open.
- **Data processing:** Verify Firefight's four comparative end-game objectives,
  Lieutenant replacement/Open Information, cumulative Combat Jump landing MOD,
  Airborne Deployment zone exception, Specialist criteria, and early-ending
  conditions in source-backed mission and API regression tests.
- **Data processing:** Verify Domination's round-end Quadrant scoring,
  Shasvastii exception, last-hacked Console ownership, Specialist eligibility,
  and Tactical Phase minimum-VP ending with regression tests. Retain the
  scenario-specific 6 SWC at 350 points with corroborating versioned sources.
- **Data processing:** Add Annihilation mission acceptance checks covering
  six scored game sizes, source-identified 350-point survival-band correction,
  shared Killing criteria, Lieutenant scoring and both mission-ending triggers.
- **Data processing + Web frontend:** Clarify PARA's PH-6/no-PH and
  conditional IMM-A outcomes, Shock's VITA 1 Dead transition and related
  Special Skills, and Stun's Courage/Guts effect and the narrow Flash Pulse
  Immunity (BTS) exception. Preserve canonical conditional State facts.
- **Data processing + Web frontend:** Clarify EXP's mandatory Saving Rolls
  and combined AP+EXP example; record T2's distinct Critical roll and explicit
  English/Spanish/Wiki Saving Attribute discrepancy without overriding Weapon data.
- **Data processing + Web frontend:** Clarify AP's Critical and conditional
  Immunity interactions, and E/M's BTS/2 Critical rolls, troop-specific States,
  and Guts Roll exceptions. Preserve the existing typed Ammunition mechanics.
- **Data processing + Web frontend:** Clarify DA's mandatory second Saving Roll
  and Smoke's scenery-blocked volume in the player-facing reference. Eclipse
  now links to its inherited Smoke mechanics without losing its distinct
  Multispectral Visor behavior.
- **Web frontend:** Give narrow Unit profile attributes and loadout details
  full-width rows; preserve wrapping names and the Points/SWC labels in
  320–400 px cards, with less cramped mobile labels up to 600 px.
- **Web frontend:** Wrap long composite Unit-option names within narrow Unit
  detail cards instead of clipping their order symbols or displayed names.
- **Data processing:** Repeater now cites the current reviewed Hacking Area
  Wiki snapshot rather than an older revision on its rules-reference card.
- **Web backend:** Show upcoming-release notes on **What's changed** when the changelog uses its bracketed `Unreleased` heading, but omit that section when it contains no actual changes.

## [0.10.1] - 2026-10-10

### Player summary

- Browse the four core scenarios: Annihilation, Domination, Supplies and Firefight,
  with game-size-specific setup, objectives, scoring and deployment maps. Maps follow
  your theme and distance preference.
- Ammunition pages now show compact mechanics and linked State effects. Weapon profiles link
  reviewed Ammunition components and separate Traits, Labels and States for easier lookup.
- Rules references explain more of the conditions and exceptions that matter during play,
  including Immunity, Dodge, Reset, State cancellation, Smoke/Eclipse and Critical Saving Rolls.
- Corrected explanations cover IMP-2 Discover modifiers, Stealth against Deployables,
  Deployable Cover, TinBot sharing and Fireteam formation requirements. Special Weapon
  references explain their distinct modes and keep unresolved source disagreements visible.
- Visibility Zones are easier to find through search, the Glossary and linked rules tooltips;
  longer rules cards use clearer sections and separate source notes.

### Added

- **Data processing + Web backend + Web frontend:** Add the four current core scenarios,
  with a default 300-point selection, point-dependent setup/scoring, linked scenario Rules
  and Skills, source notes and deployment maps generated from the maintained geometry.
  Scenario selection is shareable; maps support Light/Dark themes and inches/centimeters.
- **Data processing + Web backend + Web frontend:** Add compact, source-cited mechanics for
  all eleven base Ammunition references, including conditional State effects and Critical
  exceptions. Weapon profiles link base Ammunition and the reviewed AP+DA, AP+Exp,
  AP+Shock and AP+T2 components while retaining imported Saving Rolls.
- **Data processing + Web backend:** Add distinct rules references for Drop Bears,
  Flash Pulse, Kobra Pistol CC Mode, PARA Mine, Mines, Cybermine, Chest Mine, PT: Endgame,
  Sepsitor, Sepsitor Plus and WildParrot. Explain mode-specific behavior and preserve disagreements
  with Army or other cited sources without silently changing imported profiles.
- **Data processing + Web backend:** Identify Combined Saving Rolls on the six Plasma
  Hit/Blast profiles in the Weapon API, including the additional ARM Saving Roll for a
  Critical. Keep these distinct from Combined Ammunition and retain source profile values.
- **Web backend + Web frontend:** Make Visibility Zone and its Low, Poor, Zero and White
  Noise variants discoverable in search and the Glossary, with linked explanation tooltips
  in rules text.

### Changed

- **Data processing:** Reduce database rebuild time, especially on Windows, while preserving
  generated contents, validation and deterministic release artifacts.
- **Data processing + Web frontend:** Present long rules references in topic-based paragraphs
  with separate source notes. Immunity keeps Requirements, Effects and Restrictions in order,
  followed by clarifications, examples and five reviewed interactions with conditional outcomes
  and evidence labels. Explain AP+DA protection and the Flash Pulse exception without implying
  that unreviewed combinations have been resolved.
- **Web backend + Web frontend:** Group Weapon properties under Traits, Labels or States,
  linking each to its owning reference. Use reviewed N5 names for legacy Army labels;
  original wording remains available in Developer Mode and unknown properties remain visible.

### Fixed

- **Data processing:** Correct IMP-2 Discover modifiers and Stealth's Deployable exception.
  Discover now explains its Range MODs and the retry limit after a failed attempt against an
  Impersonation Marker. Deployable Cover explains Vitroferro's pre-PS cap,
  eligibility and printed S3, Disposable (2), Indiscriminate and Perimeter properties.
  TinBot retains owner requirements, Fireteam sharing and non-stacking benefits.
  Kobra Pistol links the correct CC Attribute.
- **Data processing + Web frontend:** Identify Fireteam Type counts as formation requirements,
  distinguish ongoing integrity and type persistence, and preserve the existing count data.
- **Data processing:** Clarify Dodge and Reset roll/movement conditions, cumulative State
  penalties and cancellation exceptions; explain Smoke/Eclipse opposition and Visor limits,
  AP/E/M rounding, T2 Critical Wounds and Continuous Damage's extra-roll exception.
- **Data processing:** Correct Counterintelligence's Command Token effects, Protheion's
  Attribute penalty and post-death limits, Controlled Jump timing/cancellation and its Speedball
  exclusion. Clarify Doctor, Engineer, MediKit, GizmoKit, Intuitive Attack, Disposable,
  Double Shot, Non-Lethal and Boost exceptions, and BS Weapon (WIP)'s Skill restrictions.
- **Web frontend:** Display no Saving Rolls for Weapon profiles without a Saving Attribute.
- **Data processing + Web frontend:** Correct Annihilation's 350-point surviving-force scoring
  boundaries and Supplies' edge-to-edge Supply Box placement at every game size. Preserve
  Domination's printed 350-point 6 SWC and explain the unresolved source inconsistency.

### Upgrade notes

- **Deployment:** Deploy the release-matched application and both tracked runtime databases
  together. Older rules databases are incompatible with the new scenario references; local
  installations maintaining their own generated data must rebuild the rules database from
  this release's curated inputs. Tagged production deployment uses the bundled databases
  and must not rebuild them on the server.

## [0.10.0] - 2026-10-07

### Player summary

- You can now choose a Light or Dark theme, or let InfinityDB follow your device's settings.
- Silhouette diagrams in the Glossary and Unit previews show templates at the same scale,
  making their sizes easier to compare.
- The new **What's changed** page collects release notes in one place, and the privacy policy
  explains what InfinityDB stores.
- Rules descriptions and Unit help are clearer, artwork has been corrected, and Unit and Fireteam
  pages are easier to read on small screens.

### Added

- **Web frontend:** Add System, Light, and Dark theme selection in Settings. System follows the
  operating-system preference; explicit choices use existing Settings persistence and apply before
  first paint. Add a project favicon that stays legible in light and dark browser chrome.
- **Web frontend:** Add scale-preserving S1–S8 Silhouette diagrams to the Glossary and Unit
  statline previews. Other supported Silhouettes include a faded S2 reference at the same scale;
  S2 appears alone and the normal statline stays compact.
- **Web frontend + Project infrastructure:** Add a **What's changed** page with concise player
  summaries and expandable release details, plus a public privacy policy linked from cookie
  consent. Explain aggregate-only monitoring, session settings, opt-in preference cookies, and
  shareable URL state.
- **Data processing + Web frontend:** Add **FTO (Fireteam Option)** to the Glossary, explaining
  option-name identifiers and chart requirements for specific variants such as FTO-2.
- **Deployment:** Add bounded aggregate metrics history and operator reports by week, version,
  and snapshot. A separate private collector retains request/status/error summaries and latency
  estimates without visitor identities. Updates capture outgoing and incoming generations without
  blocking a healthy application; history survives restarts and rollback, and format upgrades are
  transactional with older collectors refusing newer stores.
- **Deployment:** Add privacy-preserving resource capture, sanitized warning/error diagnostics,
  and configurable operational alerts for CPU, memory, storage, errors, and health failures.
- **Deployment:** Add repeatable HTTP capacity testing and controlled worker/resource comparisons.
  The matched 2x4 versus 4x4 experiment establishes 4x4 as the first bounded scale step, with an
  explicit latency/error/resource trigger for review. Production continues to default to 2x4;
  measured results and comparison commands are retained in deployment guidance.
- **Deployment:** Add `infinity-db database-health` to validate Army databases and optionally
  verify their application/raw export pair, with revision, timing, and JSON output.
- **Acquisition:** Add English-only Human Sphere wiki research snapshots, including orphaned
  content pages, deterministic archive identities, and resumable downloads. Missing required pages
  block publication; unrelated Talk/service pages and stale discovered 404s remain diagnostics.

### Changed

- **Web frontend:** Use clearer game/reference language throughout navigation, page introductions,
  Unit notes, profile notation, rules help, and empty/error/loading states. Unresolved reference
  information appears as **Needs verification** with an **uncertain** marker and readable reasons.
- **Data processing:** Publish validated application/raw exports as one matching generation.
  Interrupted publication preserves the previous serving database, rejects mismatched raw-dependent
  audits, and recovers by rerunning the export.
- **Web backend + Web frontend:** Interpret Fireteam limit sentinels explicitly and include legacy
  Armies in global search, linking to their entries on the Armies overview.
- **Data processing + Web frontend:** Refresh processed faction, Order, Characteristic, Peripheral,
  and Unit artwork. Preserve distinct contextual variants, publish Peripheral-only artwork in its
  own namespace, and keep mixed-role artwork with its Unit identity.

### Fixed

- **Web frontend:** Give Unit Profile row headers maintained help and Glossary links, keep
  Fireteam columns and cm-mode statlines readable at narrow widths, and improve text, status,
  link, and focus contrast in both themes. Army links now scroll to and highlight the matching card.
- **Web backend + Web frontend:** Explain when optional-unit Settings hide all Unit profiles,
  remove redundant one-Unit Characteristics from filter choices, and match the combined
  Headquarters/Mechanized classification through either component filter.
- **Web backend:** Reject unknown or duplicate semantic parameters on Fireteam and Unit-detail
  APIs while preserving the Developer-mode cache-bust parameter.
- **Web frontend:** Display stationary MOV as an em dash rather than a negative distance, and
  keep cm/in conversion consistent across profiles, rules help, and Weapon ranges.
- **Data processing:** Update Armed Turret to current N5 v5.3 citations while preserving the
  documented conflict between sources for its deployable-profile Silhouette.
- **Acquisition:** Apply symbol overrides to all same-category upstream-identical artwork;
  conflicting overrides fail explicitly rather than producing ambiguous results.
- **Data processing + Web backend + Web frontend:** Correct Unit and General-profile symbol
  assignments, preserve genuine profile-specific artwork, and repair repeated upstream
  misassignments such as Crabbots on Cutters and Dragões while retaining source provenance.
- **Deployment:** Include published Peripheral artwork in installed packages and release images.

### Upgrade notes

- **Deployment:** Deploy the release-matched tracked Army database, rules database, and complete
  processed SVG publication together. Normal server upgrades consume these artifacts without
  rebuilding databases in production.
- **Deployment:** Preserve the metrics-history volume during updates and rollback. Older
  collectors refuse newer history formats; rollback must not downgrade or delete retained history.

## [0.9.1] - 2026-09-30

### Player summary

- Shared Unit Explorer links show when their optional-unit choices differ from your Settings,
  without changing your saved preferences.
- Order references are more complete, and Strategos and Multispectral Visor levels are easier
  to compare.
- Army symbols wrap more neatly when a Unit is available to many Armies.

### Changed

- **Web frontend:** Replace the Unit Explorer's duplicate optional-unit controls with a compact
  status showing whether the URL-owned view matches Settings and, when it does not, which optional
  unit categories differ. Clearing filters returns the view to the current Settings baseline, while
  shared views remain reproducible without overwriting the recipient's saved Settings.

### Fixed

- **Data processing + Web backend + Web frontend:** Publish Regular Order and Irregular Order as
  General Rules alongside Special Lieutenant Order and Tactical Order, so all four Order types
  cross-link through the `order-type` category. Impetuous remains a Skill and is surfaced as a
  related reference rather than being misclassified as an Order.
- **Data processing + Web frontend:** Publish the concrete Strategos L1/L2 effects from the core
  rules and surface gameplay-bearing source variants before collapsed Unit-usage sections while
  keeping identity-only variants out of the player-facing rule view.
- **Data processing + Web frontend:** Present level-based reference data such as Multispectral
  Visor in a compact level-effects table between the family rules and Unit-usage sections.
- **Web frontend:** Keep Army-availability symbols bounded and horizontally wrapping in both the
  Unit Explorer and reverse Unit-usage tables, preventing dense Army sets from clipping or
  collapsing into one-symbol-wide columns.

### Upgrade notes

- Deploy the release-matched tracked `data/generated/rules.db` shipped with 0.9.1; it contains the
  new Order references and reviewed Strategos/Multispectral Visor level content.
- No Army database rebuild is required solely for 0.9.1.

## [0.9.0] - 2026-09-29

### Player summary

- New **Ammunition**, **Labels**, and **General Rules** pages, a **Glossary**, and site-wide search
  make rules easier to find.
- Unit Explorer has more filters and an optional view of profile stats. The Armies page covers
  both current and legacy forces.
- Rules text links to related references, and shared links preserve search, filter, and Army
  selections. Pages are easier to use on small screens.

### Added

- **Data processing + Web backend + Web frontend:** Expand the rules/reference surface with
  first-class **Ammunition**, **Labels**, and **General Rules** catalogs. General Rules is the
  fallback home for reviewed concepts without a clearer domain owner, while Fireteam rules,
  profile help, Attributes, and scoped terminology stay with their more specific surfaces.
- **Data processing + Web backend + Web frontend:** Add canonical **Attributes** and scoped
  **Game terms** as embedded vocabularies plus a federated **Glossary** across the reference
  domains. Same-name concepts remain distinct by semantic kind, and browsable entries link back
  to their owning detail surfaces instead of creating duplicate catalogs.
- **Web backend + Web frontend:** Add global search across the player-facing reference, including
  Armies, Units, rules catalogs, Hacking Programs, and Fireteam charts, with results routed to the
  corresponding application surface.
- **Data processing + Web backend + Web frontend:** Add rules-backed **Profile notation** help to
  Unit details for Attributes, Orders, Troop Type, Classification, ISC, Hackable, Peripheral,
  Equipment/Weapon domains, and profile/loadout structure without making the profile tables denser.
- **Web backend + Web frontend:** Expand Unit Explorer with Troop Type, Classification,
  Characteristics, AVA, Points, and SWC filters plus an optional extended result mode showing
  profile statlines and Army-specific AVA. The complete filter and presentation state is shareable.
- **Data processing + Web backend + Web frontend:** Add an **Armies** overview for current and
  legacy forces with symbols, catalog status, gameplay-focused summaries, and direct Unit Explorer
  links. The page also explains the practical distinction between Generic Army Lists and
  Sectorials and identifies playable forces that are out of catalog.
- **Web backend + Web frontend:** Present source-specific Unit notes and composite Unit options with
  their applicable Army/source context, including costs, miniature count, Orders, and linked
  constituent loadouts where that structure is available.

### Changed

- **Data processing + Web backend + Web frontend:** Make maintained rules prose navigable through
  semantic references. Reviewed Skill, Equipment, Weapon, Trait, State, and Hacking Program links
  can preview definitions and open canonical detail pages, Label badges and Related rules links
  open their canonical references, and typed gameplay distances follow the user's cm/in preference.
  The maintained corpus is now fully reviewed with no unresolved semantic-link migration debt.
- **Web backend + Web frontend:** Make shared browser state compact and reproducible across Unit
  Explorer, Unit Army targeting, Fireteams, catalog search, global search, and Glossary search.
  Optional Unit availability is carried with shared Unit views without overwriting the recipient's
  saved Settings, Army-availability symbols open Units in the selected Army context, and existing
  explicit-parameter links remain compatible.
- **Web backend + Web frontend:** Normalize Fireteams around the shared landing/scoped interaction:
  the unscoped page shows the Army selector and general rules, while selecting an Army switches to
  the shareable Army chart. Wildcard handling and ordinary-player layouts stay compact while
  Developer mode retains the additional source detail.
- **Web frontend:** Standardize responsive behavior across Unit Explorer, catalogs, reference
  details, Hacking Programs, Weapons, Fireteams, navigation, and Settings. Army symbols/headings,
  rules-card badge ordering, narrow-screen tables, short-viewport sidebar spacing, and Advanced
  filter disclosure state now follow the shared presentation rules.

### Fixed

- **Web backend:** Keep compound Unit filters coherent when AVA, Points, or SWC is involved, so
  profile/loadout-sensitive criteria must be satisfied within one compatible context rather than
  assembled from unrelated options on the same Unit.
- **Data processing + Web backend + Web frontend:** Restore missing canonical rule links and labels,
  including Peripheral subtype links into General Rules and Supportware, No Roll, Comms Attack,
  and Negative Feedback (NFB) on Hacking Programs.
- **Web backend:** Merge Skill-detail variants whose distance extras differ only by source spelling,
  preventing duplicate converted values while preserving the original source forms.
- **Web frontend:** Correct narrow-screen and soft-navigation regressions affecting active
  navigation, Unit Explorer introductory wrapping, and Fireteam member tables.

### Upgrade notes

- Deploy the release-matched tracked `data/generated/infinity.db` and
  `data/generated/rules.db` shipped with 0.9.0. They include the additional Unit-option source
  data and reviewed rules/reference content required by the release.
- Normal server upgrades from 0.8.1 onward do **not** rebuild databases in production. Raw
  Army/wiki/PDF inputs remain development and release-preparation inputs only.

## [0.8.1] - 2026-09-27

### Player summary

- Hacking Programs use the same action labels and page layout as Skills.
- Fonts are more consistent across the site, and the sidebar shows when Army data last changed.

### Changed

- **Web backend + Web frontend:** Present Hacking Programs with the same declaration language and
  detail-card structure as Skills, including canonical **Long Skill** presentation for Army's
  legacy `entire order` source value.
- **Web frontend + Project infrastructure:** Adopt bundled redistributable browser fonts and a
  shared typography scale so headings, body text, compact tables, and diagnostic text remain
  consistent and responsive across the application.
- **Acquisition + Data processing + Web backend + Web frontend:** Distinguish when the contained
  Army data last changed from when a snapshot was downloaded. The player-facing sidebar now shows
  the Army-data change date while acquisition time remains Developer-mode provenance, and older
  snapshot manifests remain readable.
- **Deployment + Project infrastructure:** Make release tags self-contained for deployment by
  tracking the exact runtime Army/rules databases and the publication metadata that binds them to
  the processed symbol set. Production no longer needs raw source archives or symbol-build state.

### Upgrade notes

- No Army or rules database rebuild is required solely for 0.8.1; deploy the tracked runtime
  databases shipped with the release.
- The first upgrade from 0.8.0 must bootstrap the 0.8.1 installer as documented in
  `docs/deployment.md`. From 0.8.1 onward, updates hand off to the target release's installer before
  checkout-side effects occur.
- Snapshot manifest versions 1 and 2 remain supported, and production servers do not need the raw
  Army/wiki/PDF/source-symbol archives used during release preparation.

## [0.8.0] - 2026-09-26

### Player summary

- Hacking Programs have their own reference pages, and Fireteam charts can be browsed by Army,
  with rules, limits, Wildcards, and FTO options.
- Unit pages show linked profiles, Peripherals, Controllers, and selection requirements more
  clearly. Profile artwork and Fireteam layouts have also been improved.

### Added

- **Data processing + Web backend + Web frontend:** Promote Hacking Programs to a first-class
  reference surface with program statlines, targets, declaration types, effects, related rules,
  baseline Hacking Device associations, and reverse links from Hacking Devices.
- **Data processing + Web backend + Web frontend:** Add first-class Army-scoped Fireteam browsing
  with current chart limits, membership requirements, FTO-eligible loadouts, Wildcards,
  equivalence labels, notes, Unit links, and reviewed general Fireteam rules/Level bonuses.
- **Web backend + Web frontend:** Expand Unit details with Reinforcement relationships,
  source-declared faction membership, reviewed selection constraints, profile/loadout includes,
  same-Unit dependencies, and canonical Peripheral/Controller relationships while keeping
  source-oriented diagnostics in Developer mode where appropriate.
- **Deployment:** Add an optional trusted-LAN listener and workstation reporting path for the
  aggregate request metrics introduced in 0.7.2, without exposing the application's internal
  metrics endpoint publicly.

### Changed

- **Acquisition + Web backend + Web frontend:** Improve Unit artwork placement and profile-specific
  symbol resolution so General profiles show the correct Army/contextual artwork and the complete
  processed symbol publication is addressable by the browser.
- **Web backend + Web frontend:** Refine the shared shell, reference navigation, and Fireteam
  presentation, including compact ordinary-player cards, a Unit-Explorer-style Army hierarchy,
  clearer unlimited type allowances, and a persistent setting that folds a single Wildcard set
  into each ordinary Fireteam table.
- **Data processing + Web backend + Deployment:** Use one tracked symbol-publication contract for
  browser lookup, completeness validation, packaging, and deployment instead of separate generated
  lookup inventories.

### Upgrade notes

- Rebuild the generated Army database and `rules.db` before deploying 0.8.0 so the Fireteam and
  Hacking Program application/reference data is present.
- Deploy the application, rebuilt databases, and processed SVG publication from the same release
  revision.
- The trusted-LAN metrics listener is optional; configure its bind address only when remote
  workstation reporting is needed.

## [0.7.2] - 2026-09-26

### Player summary

- On first use, distances are shown in inches and all optional Unit types are included.
  Troop Type names are clearer, and profiles show **VITA** or **STR** as appropriate.
- Settings can be collapsed on desktop, and text and layouts are easier to read.

### Changed

- **Deployment + Web backend:** Replace routine per-request production access logging with bounded,
  privacy-preserving aggregate request metrics while retaining Gunicorn error logging for
  diagnostics.
- **Web backend + Web frontend:** Improve presentation defaults and readability: Settings can
  collapse in the desktop sidebar, first-use preferences use inches and include all optional Unit
  types, troop types use rules-facing names, Unit health shows `VITA` or `STR` from profile
  semantics, detail metadata is Developer-mode only, and catalog/rules layouts use a clearer
  shared type scale.
- **Web backend + Web frontend:** Apply an explicit same-origin Content Security Policy so browser
  scripts remain external modules without permitting inline executable code.

### Upgrade notes

- Redeploy the application image for 0.7.2 so the production web/metrics configuration moves as one
  release.
- No Army or rules database rebuild is required solely for 0.7.2; 0.7.1-compatible generated
  databases remain usable.

## [0.7.1] - 2026-09-25

### Player summary

- Equipment such as MediKit, GizmoKit, and Deactivator uses the same action presentation as Skills.
- Paramedic links correctly to MediKit, and reference pages refresh correctly after an app update.

### Changed

- Make generated archives, reports, symbol metadata, and SQLite databases reproducible at the byte
  level across supported operating systems.
- Present declaration-bearing Equipment such as MediKit, GizmoKit, and Deactivator with the same
  action-card and declaration-category language used for Skills.

### Fixed

- Model Paramedic as equipping its user with MediKit and keep MediKit/GizmoKit relationships routed
  to the Equipment reference.
- Prevent immutable frontend assets from remaining stale when browser resources are rebuilt under
  the same application version.
- Prevent platform line-ending conversion from invalidating checksum-bound symbol publication
  metadata.

### Upgrade notes

- Rebuild `rules.db` before deployment so the Paramedic → MediKit equipment relationship is
  available.
- No Army database rebuild is required solely for 0.7.1.

## [0.7.0] - 2026-09-25

### Player summary

- Skills, Equipment, Traits, and States have fuller rules explanations and more links to related
  rules, including a complete State reference.
- Skill pages include Hacking Program, Martial Arts, Booty, and MetaChemistry tables.
  Cube and Cube 2.0 pages list the Units that use them.
- Unit pages are easier to read on very small screens.

### Added

- Complete the rules-backed Skill, Equipment, Trait, and State reference for the 0.7 milestone,
  including reviewed N5.3 relationships for requirements, effects, restrictions, recovery,
  deployment, mobility, morale, combat, and Peripheral interactions.
- Add the complete current State reference, including distinct IMP-1 and IMP-2 concepts with
  reviewed entry, cancellation, recovery, restriction, modifier, and reverse relationships.
- Surface Army's structured Hacking Program, Martial Arts, Booty, and MetaChemistry data on Skill
  details, and make Cube/Cube 2.0 profile-symbol usage available through the canonical Equipment
  reference.

### Changed

- Make rules presentation come from the maintained application/rules data rather than parallel
  browser assumptions, with clearer Skill categories, Requirements/Effects/Restrictions, related
  rules, exact variants, and source/applicability context.
- Present Army weapon-profile `damage` as N5 Possibility of Survival (`PS`) while preserving the
  upstream field in stored data.
- Update the landing/About presentation for the rules-enriched scope, roadmap, open-source and
  non-commercial status, non-affiliation, and Corvus Belli graphical-asset permission.
- Track the validated processed Corvus Belli SVG publication as release content while keeping raw
  Army/wiki/PDF/source-symbol archives as local provenance inputs.

### Fixed

- Keep very narrow Unit details readable by allowing long titles to wrap and stacking General
  profile labels above their values instead of compressing the Attribute statline.

### Upgrade notes

- Rebuild the generated Army database before deploying 0.7.0 so the structured Hacking Program,
  Martial Arts, Booty, and MetaChemistry data is available.
- Rebuild `rules.db` so the complete 0.7 Skill, Equipment, Trait, State, and interaction reference
  is deployed.
- Deploy the tracked processed SVG publication with the matching release revision; raw source
  archives remain local build/provenance inputs.

## [0.6.3] - 2026-09-22

### Player summary

- Doctor, Engineer, Cyberplug, and Peripheral references explain which Controllers can use
  each type of Peripheral.
- Unit pages show which profiles and loadouts are linked and explain requirements that affect
  those choices.

### Added

- Add reviewed N5.3 Doctor, Engineer, Cyberplug, Peripheral, and Peripheral-type reference data,
  including Controller eligibility and Connected/Autonomous profile-mode semantics.
- Add canonical Peripheral attachments, Controller access pools, Unit/Profile/Loadout include
  relationships, reviewed Unit selection constraints, and same-Unit profile-group dependencies
  without guessing unresolved Army selector semantics.

### Changed

- Split generated Army storage into a self-contained runtime `infinity.db` and a separate
  `infinity.raw.db` containing the complete normalized source representation. The deployed
  application database becomes substantially smaller while source/audit detail remains available
  to development tooling.

### Upgrade notes

- Rebuild generated Army databases before deploying 0.6.3; there is no in-place migration from the
  earlier combined storage layout.

## [0.6.2] - 2026-09-21

### Player summary

- Browser links use readable names instead of numbers.
- Unit Explorer shows how many Units match your filters and breaks down their availability.
  Skill, Equipment, and Weapon filters also include related variants more consistently.

### Added

- Add deterministic readable public slugs for Armies, Units, Skills, Equipment, and Weapons while
  continuing to accept numeric identifiers for compatibility and provenance.

### Changed

- Use readable slugs throughout browser links, catalog/detail APIs, Unit Explorer filters, and
  canonical cross-domain references where a stable application identity exists.
- Show the Unit Explorer's visible unique-Unit count alongside the total available under the same
  filters, with an expandable availability breakdown.

### Fixed

- Resolve grouped Skill, Equipment, and Weapon filters across all source variants and canonicalize
  accepted legacy numeric references to readable slugs when available.
- Keep session-only Settings, Team Operations-only Skill usage, merged Skill identities, and
  reviewed catalog naming consistent across browser and API surfaces.

### Upgrade notes

- Rebuild generated Army databases before deploying 0.6.2; older generated `infinity.db` files are
  not compatible with this release.

## [0.6.1] - 2026-09-20

### Player summary

- Units, Skills, Equipment, and Weapons are shown consistently across Army views.
- Army totals count each Unit once, even when it appears in several related Army Lists.

### Changed

- Move Unit, Army, profile/loadout, Skill, Equipment, and Weapon browsing onto canonical
  application data while preserving source-specific context and improving Army-oriented query
  performance.
- Preserve richer source projections behind canonical identities so cross-Army relationships and
  profile metadata remain available without treating one Army view as the complete game model.

### Fixed

- Count Army totals by logical Units rather than duplicate source representations.
- Protect deployment artifacts from synthetic development/test data and reject deployments whose
  runtime database and processed graphical assets come from different Army snapshots.

### Upgrade notes

- Rebuild generated Army databases before deploying 0.6.1; there is no in-place migration from the
  previous application-data layout.

## [0.6.0] - 2026-09-19

### Player summary

- Unit availability, Army labels, symbols, and Weapon ranges are more accurate and consistent.

### Added

- Add a separately versioned rules database for cited N5 rules knowledge, including
  skill declaration categories, parameter semantics, trait summaries, and exceptional
  weapon profiles.
- Add reliable logical-unit identities and explicit availability for standard,
  mercenary, and reinforcement units.
- Add verifiable, reproducible source snapshots for Army, wiki, and symbol data.
- Add a resumable symbol build and publication workflow that produces complete local
  graphical assets with source provenance.
- Add a unified validation workflow for local development and CI, including data,
  code, package, deployment, and full-asset checks.
- Add deployment checks and tooling for safely publishing validated local graphical
  assets.

### Changed

- Use authoritative imported relationships and reviewed policy to determine army
  roles, faction presentation, unit identity, and optional-unit availability.
- Move maintained game knowledge into validated configuration and cited rules data,
  rather than duplicating it in application code.
- Treat third-party graphical symbols as locally generated deployment artifacts rather
  than source-distributed assets.
- Require production deployments to include validated Army and rules databases.
- Derive browser-facing faction, profile, army-role, and weapon-range information
  from backend data contracts.

### Upgrade notes

- Rebuild existing generated databases before deploying 0.6.0.

### Fixed

- Preserve distinct graphical-symbol variants and their provenance through publication,
  including explicitly unavailable upstream assets.
- Make symbol publication recoverable and reproducible after interrupted or failed
  builds.
- Keep installed-package validation and symbol processing reliable across the supported
  development workflow.

## [0.5.1a] - 2026-09-15

### Player summary

- No player-facing changes.

### Added

- Add the foundation for cited curated rules data and archived wiki sources.
- Clarify licensing boundaries for InfinityDB code, external game data, and graphical
  assets.

### Changed

- Stop distributing third-party graphical symbols in the source tree by default.
- Improve cross-platform handling of wiki-mirror paths and local asset URLs.

## [0.5.1] - 2026-09-14

### Player summary

- No player-facing changes.

### Fixed

- Mark the deployment, install/update, and application-image pruning scripts executable so the
  documented server maintenance commands work directly from a release checkout.

## [0.5.0] - 2026-09-14

### Player summary

- Unit lists can be filtered by Skills, Equipment, and Weapons.
- The new **Traits** pages explain their effects and link to the Weapons, Skills, and Equipment
  that use them.

### Added

- Add advanced unit-catalog filters for skills, equipment, and weapons.
- Add a Traits catalog and detail pages covering traits used by weapons, Skills, and Equipment,
  with concise summaries and usage grouped by catalog type.
- Add server deployment, install/update, and application-image pruning scripts with documented
  image-retention behavior.
- Add a Developer-mode control for bypassing cached API responses while reviewing a local
  deployment.

### Changed

- Document the release deployment workflow and refresh immutable static-asset URLs so linked
  browser modules load their matching release versions after deployment.

### Fixed

- Remove incompatible browser theme metadata from static pages.

## [0.4.2] - 2026-09-14

### Player summary

- Mercenary and Reinforcement results now follow your optional-unit settings without leaving
  outdated results on screen.

### Fixed

- Apply optional-unit settings consistently to unit availability, including
  mercenary and reinforcement armies, without stale browser results.

## [0.4.1] - 2026-09-13

### Player summary

- Support and feedback links now take you to the project's GitHub page.

### Changed

- Direct support questions, suggestions, and feedback to the project GitHub page.

## [0.4.0] - 2026-09-13

### Player summary

- Unit and reference pages respond faster, and it is clearer when a page is still loading.
- The browser refreshes automatically after an app update or a change to Army data.

### Added

- Add a raw database archive for development and data review alongside the lean
  deployed database.
- Add snapshot-aware API caching and automatic browser refresh when release or source
  data changes.
- Add a maintained backlog for future performance, pipeline, operational, and product
  work.

### Changed

- Improve responsiveness of high-volume unit and catalog queries.
- Improve browser navigation feedback while page data is loading.
- Clarify InfinityDB's data-driven reference scope and future direction.

## [0.3.3] - 2026-09-13

### Player summary

- Reference lists and detail pages no longer get stuck loading after an app update.

### Fixed

- Prevent cached browser modules from mixing releases and leaving catalog or detail
  pages in a loading state.

## [0.3.2] - 2026-09-13

### Player summary

- Settings let you include mercenaries, Spec-Ops, Team Operations, and Reinforcements,
  and remember your preferences on this device.
- The browser detects app updates more reliably, and optional-unit settings and wiki-link labels
  are consistent across pages.

### Added

- Add global controls for including mercenaries, Spec-Ops, Team Operations, and
  reinforcements across relevant unit lists.
- Add an opt-in cookie consent flow for saving display and browsing preferences on the
  current device.
- Add release-aware browser updates and clear startup guidance when a server port is
  already in use.

### Changed

- Improve responsiveness of the web reference and update project release metadata.

### Fixed

- Apply global optional-unit settings and external wiki-link labels consistently on
  catalog detail pages.

## [0.3.1] - 2026-09-13

### Player summary

- Settings adapt to different screen sizes, and Army colours make Unit and reference pages
  easier to scan.
- Movement values are displayed correctly, and mobile navigation works more reliably.

### Added

- Add a reusable responsive Settings menu.

### Changed

- Improve unit search and catalog presentation, including army-color accents.
- Make the browser footer accurately identify unreleased checkouts.
- Use the newest available local source archive for default builds and debugging.

### Fixed

- Correct movement-value presentation and mobile navigation behavior.

## [0.3.0] - 2026-09-12

### Player summary

- A new home page, simpler navigation, and division badges make the site easier to browse.
  Pages also adapt more consistently to smaller screens.

### Added

- Add an opt-in Developer mode for database IDs and data-review columns.
- Add a landing page, compact navigation, and division badges for applicable unit
  profiles.

### Changed

- Establish a consistent responsive visual system and shared page shell across browser
  routes.
- Require validated Army metadata when building a database.

### Upgrade notes

- Rebuild existing databases before deploying 0.3.0.

## [0.2.1] - 2026-09-12

### Player summary

- The About page explains what InfinityDB offers, where its data comes from, and that it's
  an independent community project.

### Changed

- Expand the About page with InfinityDB's purpose, local data flow, current reference
  features, future direction, and independent-project disclosures.

## [0.2.0] - 2026-09-11

### Player summary

- Skills, Equipment, and Weapons have searchable pages with links to the Units and loadouts
  that use them.
- Weapon profiles show Ammunition, Traits, ranges, icons, and special rules, and Unit pages show
  more complete profile and loadout details.
- AVA values display correctly, searches handle punctuation, and symbol display is more reliable.

### Added

- Add searchable Skills, Equipment, and Weapons catalogs with detail pages that link
  rule items to the unit profiles and loadouts that use them.
- Add weapon profiles, ammunition, traits, range modifiers, special-weapon details,
  and relevant order and characteristic icons to unit references.
- Add maintenance support for organizing Army symbol assets.

### Changed

- Improve unit-detail presentation of shared, army-specific, profile, and loadout
  information.
- Preserve catalog-item usage and associated details throughout database and browser
  views.
- Use stable static paths for graphical symbols.

### Upgrade notes

- Rebuild existing databases before deploying 0.2.0.

### Fixed

- Correct displayed AVA, literal punctuation searches, missing-asset responses, and
  packaged symbol availability.

## [0.1.2] - 2026-09-11

### Player summary

- Unit rows open their detail pages, and search ignores differences in case, accents, and
  punctuation. The browser also shows when Army data was downloaded.
- Reinforcements and related profiles are grouped more reliably when their names differ between
  Army Lists.

### Added

- Add an About page, snapshot download dates in the browser, and clickable unit
  catalog rows.

### Changed

- Make unit search insensitive to case, accents, and punctuation.
- Improve reinforcement matching and profile grouping despite source naming variants.

### Upgrade notes

- Rebuild existing databases before deploying 0.1.2.

## [0.1.1] - 2026-09-11

### Player summary

- You can switch between centimetres and inches, look up Skill Modifiers, and choose whether
  to include Reinforcements.
- General profiles show Troop Type and Classification. Equivalent Army Lists are grouped together
  in filters, and profile and loadout tables are easier to read on small screens.

### Added

- Add a persistent centimetre/inch preference, Skill Modifiers reference, and
  reinforcement filtering and availability in unit views.
- Add profile type and classification to general unit profiles.

### Changed

- Present equivalent army lists as one filterable army and improve profile and
  loadout grouping.

### Fixed

- Correct distance-modifier display and keep profile and loadout rows usable on
  narrow screens.

## [0.1.0] - 2026-09-10

### Player summary

- The first release lets you browse Units across Armies and look up their profiles, loadouts,
  Skills, Equipment, Weapons, and availability.
- Unit pages bring shared and Army-specific details together, with symbols and mercenary
  availability.

### Added

- Add a validated SQLite-backed Infinity data pipeline, command-line workflows, and
  local browser and JSON API.
- Add unit catalog and detail views for armies, profiles, loadouts, skills,
  equipment, weapons, AVA, and optional-unit availability.
- Add imported faction and catalog metadata, graphical symbols, source-acquisition
  tools, developer documentation, automated coverage, and repeatable Linux
  deployment.

### Changed

- Validate source reconstruction, normalized relationships, and database integrity
  before replacing an existing database.
- Improve army labels, faction grouping, mercenary availability, and presentation of
  shared and army-specific unit details.

### Fixed

- Correct mercenary main-army designations, source-symbol resolution, and profile and
  loadout rendering.
