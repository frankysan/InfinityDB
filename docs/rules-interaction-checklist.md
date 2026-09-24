# Rules interaction review checklist

This file is generated from the maintained public-catalog scope, interaction-review
policy, and current curated rules graph. Do not edit it by hand. Regenerate it with:

```powershell
python tools/audit_rules_interactions.py --output docs/rules-interaction-checklist.md
```

The **0.7.0 progress gate is catalog-based**: every public Skill, Equipment item, and
Trait is listed, including entries that do not yet have a curated rules definition.
A catalog item is complete only when its canonical rules identity exists and its
outgoing interaction semantics have been reviewed. Missing rules definitions therefore
remain visibly pending instead of disappearing from the denominator.

Exact source variants plus independently modeled Rule, State, Training, supporting
Trait, and curated Weapon identities are tracked separately as supporting semantics.
Ordinary Weapon catalog rows are covered through their Skill/Trait behavior rather than
audited one-by-one; a Weapon with its own curated rules definition remains in supporting
review. `declaration-category` projection records are excluded.

## Progress

- **0.7.0 primary catalog: 76/161 complete (47.2%), 85 pending.**
- Primary domains: Skill **39/100**; Equipment **28/28**; Trait **9/33**.
- Supporting semantic identities: **23/39** complete, **16** pending.
- Current authored outgoing relations: **109**.
- Explicitly tracked future/deferred interactions: **50**.

## 0.7.0 primary catalog review

### Skill (39/100)

- [ ] **Aerial** (`skill:aerial`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Alert** (`skill:alert`) — reviewed
  - outgoing: none
- [ ] **Bangbomb** (`skill:bangbomb`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Berserk** (`skill:berserk`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Booty** (`skill:booty`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **BS Attack** (`skill:bs-attack`) — reviewed
  - outgoing: none
- [ ] **BTS=3** (`skill:bts-3`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Camouflage** (`skill:camouflage`) — reviewed
  - `enters-state` → Camouflaged State (`state:camouflaged`)
- [x] **Cautious Movement** (`skill:cautious-movement`) — reviewed
  - outgoing: none
- [x] **CC Attack** (`skill:cc-attack`) — reviewed
  - outgoing: none
- [ ] **Chain of Command** (`skill:chain-of-command`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Climb** (`skill:climb`) — reviewed
  - outgoing: none
  - future [post-0.7.0; deferred]: `relation type TBD` → `rule:partial-cover` — Climb explicitly prevents the user from benefiting from Partial Cover MODs, but Partial Cover is not yet a canonical rules identity and the current relation vocabulary does not distinguish loss of beneficial MODs cleanly.
- [ ] **Climbing Plus** (`skill:climbing-plus`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Combat Instinct** (`skill:combat-instinct`) — reviewed
  - `ignores-modifiers-from` → Surprise Attack (`skill:surprise-attack`)
  - `negates-effects-of` → Stealth (`skill:stealth`)
- [ ] **Combat Jump** (`skill:combat-jump`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Commlink** (`skill:commlink`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Counterintelligence** (`skill:counterintelligence`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Courage** (`skill:courage`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Cyberplug** (`skill:cyberplug`) — reviewed
  - `controller-eligible-for` → Peripheral (Cyberplug) (`rule:peripheral-type:cyberplug`)
- [ ] **Decoy** (`skill:decoy`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Discover** (`skill:discover`) — reviewed
  - `reveals-state` → Camouflaged State (`state:camouflaged`)
- [x] **Doctor** (`skill:doctor`) — reviewed
  - `controller-eligible-for` → Peripheral (Servant) (`rule:peripheral-type:servant`)
  - `cancels-state` → Unconscious State (`state:unconscious`)
  - `cancels-state` → Stunned State (`state:stunned`)
- [x] **Dodge** (`skill:dodge`) — reviewed
  - `cancels-state` → Immobilized-A State (`state:immobilized-a`)
- [ ] **Dogged** (`skill:dogged`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Engineer** (`skill:engineer`) — reviewed
  - `controller-eligible-for` → Peripheral (Servant) (`rule:peripheral-type:servant`)
  - `cancels-state` → Disconnected State (`state:disconnected`)
  - `cancels-state` → Immobilized-A State (`state:immobilized-a`)
  - `cancels-state` → Immobilized-B State (`state:immobilized-b`)
  - `cancels-state` → Isolated State (`state:isolated`)
  - `cancels-state` → Stunned State (`state:stunned`)
  - `cancels-state` → Targeted State (`state:targeted`)
  - `cancels-state` → Unconscious State (`state:unconscious`)
- [ ] **Explode** (`skill:explode`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Exrah** (`skill:exrah`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Forward Deployment** (`skill:forward-deployment`) — reviewed
  - outgoing: none
- [x] **Forward Observer** (`skill:forward-observer`) — reviewed
  - `causes-state` → Targeted State (`state:targeted`)
- [ ] **Frenzy** (`skill:frenzy`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **FT Master** (`skill:ft-master`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **G: Jumper** (`skill:g-jumper`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Gizmokit** (`skill:gizmokit`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Guard** (`skill:guard`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Hacker** (`skill:hacker`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Hidden Deployment** (`skill:hidden-deployment`) — reviewed
  - `enters-state` → Hidden Deployment State (`state:hidden-deployment`)
- [x] **Idle** (`skill:idle`) — reviewed
  - outgoing: none
  - future [post-0.7.0; deferred]: `relation type TBD` → `rule:marker-form` — A failed declaration that resolves as Idle reveals a Trooper in Marker form; the graph needs a canonical Marker-form abstraction before this can be represented without enumerating only some Marker States.
- [ ] **Immunity** (`skill:immunity`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Impersonation** (`skill:impersonation`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Impetuous** (`skill:impetuous`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Infiltration** (`skill:infiltration`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Infinity Spec-Ops** (`skill:infinity-spec-ops`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Infinity Team-Ops** (`skill:infinity-team-ops`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Inspiring Leadership** (`skill:inspiring-leadership`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Intuitive Attack** (`skill:intuitive-attack`) — reviewed
  - outgoing: none
  - future [post-0.7.0; deferred]: `relation type TBD` → Camouflaged State (`state:camouflaged`) — Intuitive Attack can attack targets in States such as Camouflaged without first Discovering them, but the current relation vocabulary has no precise bypasses-targeting-protection edge.
- [ ] **Journalist** (`skill:journalist`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Jump** (`skill:jump`) — reviewed
  - outgoing: none
  - future [post-0.7.0; planned]: `cancels-state` → `state:prone` — Declaring Jump explicitly cancels Prone State; materialize this edge once Prone State is promoted to a canonical rules identity.
  - future [post-0.7.0; deferred]: `relation type TBD` → `rule:partial-cover` — A Trooper that declares Jump cannot benefit from Partial Cover MODs during that Order; Partial Cover and the appropriate benefit-suppression relation need canonical modeling first.
- [ ] **Lieutenant** (`skill:lieutenant`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Limited Cover** (`skill:limited-cover`) — reviewed
  - outgoing: none
  - future [post-0.7.0; deferred]: `relation type TBD` → `rule:partial-cover` — Limited Cover removes only the -3 BS MOD from Partial Cover while leaving its other effects intact; Partial Cover needs a canonical identity and the graph needs a relation more precise than globally negating the rule.
- [x] **Look Out** (`skill:look-out`) — reviewed
  - `modifies-rolls-for` → Dodge (`skill:dodge`)
- [x] **Marksmanship** (`skill:marksmanship`) — reviewed
  - `modifies-rolls-for` → BS Attack (`skill:bs-attack`)
- [x] **Martial Arts** (`skill:martial-arts`) — reviewed
  - `modifies-rolls-for` → CC Attack (`skill:cc-attack`)
- [ ] **MediKit** (`skill:medikit`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **MetaChemistry** (`skill:metachemistry`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Mimetism** (`skill:mimetism`) — reviewed
  - `imposes-modifiers-on` → BS Attack (`skill:bs-attack`)
  - `imposes-modifiers-on` → Discover (`skill:discover`)
- [ ] **Minelayer** (`skill:minelayer`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Mnemonica** (`skill:mnemonica`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Morpho-scan** (`skill:morpho-scan`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Move** (`skill:move`) — reviewed
  - outgoing: none
- [x] **Natural Born Warrior** (`skill:natural-born-warrior`) — reviewed
  - `ignores-modifiers-from` → Martial Arts (`skill:martial-arts`)
  - `ignores-modifiers-from` → Surprise Attack (`skill:surprise-attack`)
- [ ] **NCO** (`skill:nco`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Neurocinetics** (`skill:neurocinetics`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **No Cover** (`skill:no-cover`) — reviewed
  - `overrides-effects-of` → Limited Cover (`skill:limited-cover`)
- [ ] **No Wound Incapacitation** (`skill:no-wound-incapacitation`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Number 2** (`skill:number-2`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Parachutist** (`skill:parachutist`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Paramedic** (`skill:paramedic`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Peripheral** (`skill:peripheral`) — reviewed
  - `has-subtype` → Peripheral (Servant) (`rule:peripheral-type:servant`)
  - `has-subtype` → Peripheral (Synchronized) (`rule:peripheral-type:synchronized`)
  - `has-subtype` → Peripheral (Control) (`rule:peripheral-type:control`)
  - `has-subtype` → Peripheral (Ancillary) (`rule:peripheral-type:ancillary`)
  - `has-subtype` → Peripheral (Cyberplug) (`rule:peripheral-type:cyberplug`)
- [x] **Place Deployable** (`skill:place-deployable`) — reviewed
  - outgoing: none
  - future [post-0.7.0; deferred]: `relation type TBD` → Camouflaged State (`state:camouflaged`) — Enemy Camouflaged Markers can restrict legal Deployable placement through Trigger Area rules, but this is a placement constraint rather than a general restriction on declaring Place Deployable.
- [ ] **Protheion** (`skill:protheion`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Regeneration** (`skill:regeneration`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Regular** (`skill:regular`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Religious Troop** (`skill:religious-troop`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Reload** (`skill:reload`) — reviewed
  - `cancels-state` → Unloaded State (`state:unloaded`)
- [ ] **RemDriver** (`skill:remdriver`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Remote Presence** (`skill:remote-presence`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Request Speedball** (`skill:request-speedball`) — reviewed
  - outgoing: none
  - future [post-0.7.0; planned]: `uses-effects-of` → Combat Jump (`skill:combat-jump`) — Request Speedball explicitly places its Tokens by applying the Combat Jump Skill rules; materialize the edge once Combat Jump has a full canonical Skill definition.
- [x] **Reset** (`skill:reset`) — reviewed
  - `cancels-state` → Targeted State (`state:targeted`)
  - `cancels-state` → Immobilized-B State (`state:immobilized-b`)
  - `cancels-state` → Isolated State (`state:isolated`)
- [ ] **Sapper** (`skill:sapper`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Sensor** (`skill:sensor`) — reviewed
  - `ignores-modifiers-from` → Mimetism (`skill:mimetism`)
  - `modifies-rolls-for` → Discover (`skill:discover`)
  - `restricts-use-of` → Camouflage (`skill:camouflage`)
  - `reveals-state` → Camouflaged State (`state:camouflaged`)
  - `reveals-state` → Hidden Deployment State (`state:hidden-deployment`)
- [ ] **Shasvastii** (`skill:shasvastii`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Sixth Sense** (`skill:sixth-sense`) — reviewed
  - `negates-effects-of` → Stealth (`skill:stealth`)
  - `modifies-rolls-for` → Dodge (`skill:dodge`)
  - `modifies-rolls-for` → Reset (`skill:reset`)
- [ ] **Specialist Operative** (`skill:specialist-operative`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Speculative Attack** (`skill:speculative-attack`) — reviewed
  - `ignores-modifiers-from` → Mimetism (`skill:mimetism`)
- [x] **Stealth** (`skill:stealth`) — reviewed
  - `enables-use-of` → Cautious Movement (`skill:cautious-movement`)
  - future [post-0.7.0; deferred]: `relation type TBD` → Idle (`skill:idle`) — Stealth changes which enemies receive AROs when the user declares Idle, but the current relation vocabulary has no precise ARO-generation modifier edge.
  - future [post-0.7.0; deferred]: `relation type TBD` → Move (`skill:move`) — Stealth changes which enemies receive AROs for a Basic Short Skill with the Movement Label, including Move; the current relation vocabulary has no precise ARO-generation modifier edge.
- [ ] **Strategic Deployment** (`skill:strategic-deployment`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Strategos** (`skill:strategos`) — reviewed
  - outgoing: none
- [x] **Super-Jump** (`skill:super-jump`) — reviewed
  - outgoing: none
  - future [post-0.7.0; deferred]: `relation type TBD` → Jump (`skill:jump`) — Super-Jump changes how Jump is declared/executed; the current relation vocabulary has no precise transformation edge.
- [x] **Suppressive Fire** (`skill:suppressive-fire`) — reviewed
  - outgoing: none
  - future [post-0.7.0; planned]: `enters-state` → `state:suppressive-fire` — Suppressive Fire explicitly places the user in Suppressive Fire State; materialize the edge once that State is promoted to the canonical State catalog.
- [x] **Surprise Attack** (`skill:surprise-attack`) — reviewed
  - outgoing: none
  - future [post-0.7.0; planned]: `imposes-modifiers-on` → `rule:face-to-face-roll` — Surprise Attack applies its listed negative MOD to any Face to Face Roll made in ARO by a target of the Attack; model the generic Roll interaction once Face to Face Rolls have a canonical rules identity rather than incorrectly linking only selected Skills.
- [ ] **Tactical Awareness** (`skill:tactical-awareness`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **TAGCom** (`skill:tagcom`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Tech-recovery** (`skill:tech-recovery`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Technorganic** (`skill:technorganic`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Terrain** (`skill:terrain`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Total Reaction** (`skill:total-reaction`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Transmutation** (`skill:transmutation`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Triangulated Fire** (`skill:triangulated-fire`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Vulnerability** (`skill:vulnerability`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Warhorse** (`skill:warhorse`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable

### Equipment (28/28)

- [x] **360º Visor** (`equipment:360o-visor`) — reviewed
  - outgoing: none
- [x] **AI Motorcycle** (`equipment:ai-motorcycle`) — reviewed
  - `uses-effects-of` → Motorcycle (`equipment:motorcycle`)
  - `uses-effects-of` → Peripheral (Synchronized) (`rule:peripheral-type:synchronized`)
  - future [0.7.0; planned]: `uses-effects-of` → Transmutation (`skill:transmutation`) — AI Motorcycle explicitly applies Transmutation (Auto); materialize the edge once the canonical Transmutation Skill definition is added.
- [x] **Albedo** (`equipment:albedo`) — reviewed
  - `imposes-modifiers-on` → Multispectral Visor (`equipment:multispectral-visor`)
  - `imposes-modifiers-on` → Marksmanship (`skill:marksmanship`)
- [x] **Baggage** (`equipment:baggage`) — reviewed
  - `enables-use-of` → Reload (`skill:reload`)
  - `cancels-state` → Unloaded State (`state:unloaded`)
- [x] **Bangbomb** (`equipment:bangbomb`) — reviewed
  - `modifies-rolls-for` → Dodge (`skill:dodge`)
- [x] **Biometric Visor** (`equipment:biometric-visor`) — reviewed
  - `modifies-rolls-for` → Discover (`skill:discover`)
  - `ignores-modifiers-from` → Surprise Attack (`skill:surprise-attack`)
  - future [post-0.7.0; planned]: `cancels-state` → `state:impersonation-1` — A successful Discover Roll with Biometric Visor cancels Impersonation-1 State; materialize the State edge once Impersonation-1 has a canonical State identity.
- [x] **Dazer** (`equipment:dazer`) — reviewed
  - outgoing: none
  - future [post-0.7.0; deferred]: `relation type TBD` → `rule:difficult-terrain` — Dazer creates a Difficult Terrain area in its Zone of Control, but the current graph has neither a canonical Difficult Terrain identity nor a precise creates-area relation.
- [x] **Deactivator** (`equipment:deactivator`) — reviewed
  - `ignores-modifiers-from` → Mimetism (`skill:mimetism`)
  - future [post-0.7.0; deferred]: `relation type TBD` → Deployable (`trait:deployable`) — Deactivator targets and removes deployed enemy Weapons or Equipment with Deployable semantics; the current graph lacks a precise target-eligibility/removes-game-element relation.
  - future [post-0.7.0; planned]: `ignores-modifiers-from` → `rule:cover` — Deactivator explicitly ignores Cover MODs on its WIP Roll; materialize the edge once Cover has a canonical rules identity.
- [x] **Deployable Cover** (`equipment:deployable-cover`) — reviewed
  - `modifies-rolls-for` → BS Attack (`skill:bs-attack`)
  - future [post-0.7.0; planned]: `uses-effects-of` → `rule:partial-cover` — Deployable Cover explicitly applies Partial Cover with variant-specific changes; materialize the reuse edge once Partial Cover has a canonical rules identity.
- [x] **Deployable Repeater** (`equipment:deployable-repeater`) — reviewed
  - `uses-effects-of` → Repeater (`equipment:repeater`)
- [x] **ECM** (`equipment:ecm`) — reviewed
  - outgoing: none
- [x] **Escape System** (`equipment:escape-system`) — reviewed
  - outgoing: none
  - future [0.7.0; planned]: `uses-effects-of` → Transmutation (`skill:transmutation`) — Escape System is the Army Equipment identity for Transmutation (Escape System-X); materialize the reuse edge once Transmutation has a canonical Skill definition.
- [x] **EVO Hacking Device** (`equipment:evo-hacking-device`) — reviewed
  - outgoing: none
  - future [post-0.7.0; planned]: `enables-use-of` → `hacking-program:assisted-fire` — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
  - future [post-0.7.0; planned]: `enables-use-of` → `hacking-program:controlled-jump` — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
  - future [post-0.7.0; planned]: `enables-use-of` → `hacking-program:enhanced-reaction` — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
  - future [post-0.7.0; planned]: `enables-use-of` → `hacking-program:fairy-dust` — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
- [x] **FastPanda** (`equipment:fastpanda`) — reviewed
  - `uses-effects-of` → Repeater (`equipment:repeater`)
- [x] **GizmoKit** (`equipment:gizmokit`) — reviewed
  - `cancels-state` → Unconscious State (`state:unconscious`)
  - future [0.7.0; planned]: `enables-use-of` → Tech-recovery (`skill:tech-recovery`) — Tech-Recovery requires a successful allied GizmoKit use; materialize the prerequisite edge when Tech-Recovery gains its canonical Skill definition.
  - future [0.7.0; planned]: `relation type TBD` → Remote Presence (`skill:remote-presence`) — GizmoKit has a specific interaction with Remote Presence that changes how many Wounds are removed when Unconscious State is canceled; choose the precise relation after the Remote Presence rule definition is available.
- [x] **Hacking Device** (`equipment:hacking-device`) — reviewed
  - outgoing: none
  - future [post-0.7.0; planned]: `enables-use-of` → `hacking-program:carbonite` — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
  - future [post-0.7.0; planned]: `enables-use-of` → `hacking-program:oblivion` — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
  - future [post-0.7.0; planned]: `enables-use-of` → `hacking-program:spotlight` — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
  - future [post-0.7.0; planned]: `enables-use-of` → `hacking-program:total-control` — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
- [x] **Hacking Device Plus** (`equipment:hacking-device-plus`) — reviewed
  - outgoing: none
  - future [post-0.7.0; planned]: `enables-use-of` → `hacking-program:carbonite` — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
  - future [post-0.7.0; planned]: `enables-use-of` → `hacking-program:cybermask` — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
  - future [post-0.7.0; planned]: `enables-use-of` → `hacking-program:oblivion` — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
  - future [post-0.7.0; planned]: `enables-use-of` → `hacking-program:spotlight` — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
  - future [post-0.7.0; planned]: `enables-use-of` → `hacking-program:total-control` — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
  - future [post-0.7.0; planned]: `enables-use-of` → `hacking-program:white-noise` — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
- [x] **Holomask** (`equipment:holomask`) — reviewed
  - outgoing: none
  - future [post-0.7.0; planned]: `enters-state` → `state:holomask` — HoloMask explicitly lets its user deploy in or enter HoloMask State; materialize the State edge when that supporting State identity is added.
- [x] **Holoprojector** (`equipment:holoprojector`) — reviewed
  - outgoing: none
  - future [post-0.7.0; planned]: `enters-state` → `state:holoecho` — Holoprojector explicitly lets its user deploy in or enter Holoecho State; materialize the State edge when that supporting State identity is added.
- [x] **Killer Hacking Device** (`equipment:killer-hacking-device`) — reviewed
  - outgoing: none
  - future [post-0.7.0; planned]: `enables-use-of` → `hacking-program:cybermask` — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
  - future [post-0.7.0; planned]: `enables-use-of` → `hacking-program:trinity` — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
- [x] **MediKit** (`equipment:medikit`) — reviewed
  - `cancels-state` → Unconscious State (`state:unconscious`)
  - future [post-0.7.0; planned]: `causes-state` → `state:dead` — A failed MediKit target PH Roll makes the target enter Dead State; materialize the edge when Dead State has a canonical rules identity.
- [x] **Motorcycle** (`equipment:motorcycle`) — reviewed
  - `restricts-use-of` → Climb (`skill:climb`)
  - `restricts-use-of` → Jump (`skill:jump`)
  - `restricts-use-of` → Cautious Movement (`skill:cautious-movement`)
  - future [post-0.7.0; planned]: `relation type TBD` → `state:prone` — Motorcycle prevents its mounted user from entering Prone State; the current relation vocabulary has no precise state-entry restriction edge.
- [x] **Multispectral Visor** (`equipment:multispectral-visor`) — reviewed
  - `reduces-modifiers-from` → Mimetism (`skill:mimetism`)
- [x] **Nanoscreen** (`equipment:nanoscreen`) — reviewed
  - `imposes-modifiers-on` → BS Attack (`skill:bs-attack`)
- [x] **Repeater** (`equipment:repeater`) — reviewed
  - outgoing: none
  - future [post-0.7.0; deferred]: `relation type TBD` → `rule:hacking-area` — Repeater extends allied Hacking Areas and allows enemy Hackers in its Zone of Control to use that network; the current relation vocabulary has no precise Hacking-Area extension edge.
- [x] **SymbioMate** (`equipment:symbiomate`) — reviewed
  - outgoing: none
  - future [0.7.0; planned]: `uses-effects-of` → Immunity (`skill:immunity`) — SymbioMate grants Immunity (Enhanced) for eligible Saving Rolls; materialize the reuse edge when Immunity has its canonical Skill definition.
- [x] **TinBot** (`equipment:tinbot`) — reviewed: TinBot is a family container; exact source variants carry their own reviewed interaction semantics.
  - outgoing: none
- [x] **X Visor** (`equipment:x-visor`) — reviewed
  - `modifies-rolls-for` → BS Attack (`skill:bs-attack`)
  - `modifies-rolls-for` → Discover (`skill:discover`)
  - `modifies-rolls-for` → Suppressive Fire (`skill:suppressive-fire`)

### Trait (9/33)

- [ ] **Anti-materiel** (`trait:anti-materiel`) — pending
  - outgoing: none
- [ ] **BioWeapon** (`trait:bioweapon`) — pending
  - outgoing: none
- [ ] **Boost** (`trait:boost`) — pending
  - outgoing: none
- [ ] **BS Weapon (PH)** (`trait:bs-weapon-ph`) — pending
  - outgoing: none
- [ ] **BS Weapon (WIP)** (`trait:bs-weapon-wip`) — pending
  - outgoing: none
- [ ] **Burst: Single Target** (`trait:burst-single-target`) — pending
  - outgoing: none
- [ ] **CC** (`trait:cc`) — pending
  - outgoing: none
- [ ] **CC Attack (+3)** (`trait:cc-attack-3`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Comms. Attack** (`trait:comms-attack`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [x] **Concealed** (`trait:concealed`) — reviewed
  - `uses-effects-of` → Camouflaged State (`state:camouflaged`)
- [ ] **Continuous Damage** (`trait:continuous-damage`) — pending
  - outgoing: none
- [x] **Deployable** (`trait:deployable`) — reviewed
  - `enables-use-of` → Place Deployable (`skill:place-deployable`)
- [ ] **Direct Template** (`trait:direct-template`) — pending
  - outgoing: none
- [x] **Disposable (X)** (`trait:disposable-x`) — reviewed
  - `causes-state` → Unloaded State (`state:unloaded`)
- [ ] **Double Shot** (`trait:double-shot`) — pending
  - outgoing: none
- [ ] **Impact Template** (`trait:impact-template`) — pending
  - outgoing: none
- [ ] **Improvised** (`trait:improvised`) — pending
  - outgoing: none
- [ ] **Indiscriminate** (`trait:indiscriminate`) — pending
  - outgoing: none
- [x] **Intuitive Attack** (`trait:intuitive-attack`) — reviewed
  - `enables-use-of` → Intuitive Attack (`skill:intuitive-attack`)
- [ ] **No LoF** (`trait:no-lof`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Non-Lethal** (`trait:non-lethal`) — pending
  - outgoing: none
- [ ] **Non-Reloadable** (`trait:non-reloadable`) — pending
  - outgoing: none
- [x] **Perimeter** (`trait:perimeter`) — reviewed
  - outgoing: none
  - future [post-0.7.0; deferred]: `relation type TBD` → Place Deployable (`skill:place-deployable`) — Perimeter changes Place Deployable placement behavior rather than enabling the Skill; the current relation vocabulary has no precise modifier edge.
- [x] **Reflective** (`trait:reflective`) — reviewed
  - `applies-effects-to` → Multispectral Visor (`equipment:multispectral-visor`)
  - `applies-effects-to` → Marksmanship (`skill:marksmanship`)
- [x] **Silent (X)** (`trait:silent-x`) — reviewed
  - `imposes-modifiers-on` → Dodge (`skill:dodge`)
- [x] **Speculative Attack** (`trait:speculative-attack`) — reviewed
  - `enables-use-of` → Speculative Attack (`skill:speculative-attack`)
- [ ] **State** (`trait:state`) — pending
  - outgoing: none
- [x] **Suppressive Fire (SF)** (`trait:suppressive-fire`) — reviewed
  - `enables-use-of` → Suppressive Fire (`skill:suppressive-fire`)
- [ ] **Target (Attribute)** (`trait:target-attribute`) — pending
  - outgoing: none
- [ ] **Targetless** (`trait:targetless`) — pending
  - outgoing: none
- [ ] **Technical Weapon** (`trait:technical-weapon`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Throwing Weapon** (`trait:throwing-weapon`) — pending: No curated rules definition yet.
  - rules definition: missing; outgoing interactions not yet reviewable
- [ ] **Zone of Control (ZoC)** (`trait:zone-of-control-zc`) — pending
  - outgoing: none

## Supporting rules-identity review

### 0.7.0

#### Equipment (6/6)

- [x] **TinBot: Albedo** (`equipment:tinbot-albedo`) — reviewed
  - `variant-of` → TinBot (`equipment:tinbot`)
  - `uses-effects-of` → Albedo (`equipment:albedo`)
- [x] **TinBot: Discover** (`equipment:tinbot-discover`) — reviewed
  - `variant-of` → TinBot (`equipment:tinbot`)
  - `modifies-rolls-for` → Discover (`skill:discover`)
- [x] **TinBot: ECM Guided** (`equipment:tinbot-ecm-guided`) — reviewed
  - `variant-of` → TinBot (`equipment:tinbot`)
  - `uses-effects-of` → ECM (`equipment:ecm`)
- [x] **TinBot: Firewall** (`equipment:tinbot-firewall`) — reviewed
  - `variant-of` → TinBot (`equipment:tinbot`)
  - future [post-0.7.0; planned]: `uses-effects-of` → `equipment:firewall` — TinBot: Firewall grants the Firewall advantage; materialize the edge when Firewall is modeled as a standalone supporting Equipment rule.
- [x] **TinBot: Neurocinetics** (`equipment:tinbot-neurocinetics`) — reviewed
  - `variant-of` → TinBot (`equipment:tinbot`)
  - future [0.7.0; planned]: `uses-effects-of` → Neurocinetics (`skill:neurocinetics`) — TinBot: Neurocinetics grants that Special Skill; materialize the edge when Neurocinetics gains its canonical Skill definition.
- [x] **TinBot: Repeater** (`equipment:tinbot-repeater`) — reviewed
  - `variant-of` → TinBot (`equipment:tinbot`)
  - `uses-effects-of` → Repeater (`equipment:repeater`)

#### Rule (1/5)

- [x] **Peripheral (Ancillary)** (`rule:peripheral-type:ancillary`) — reviewed
  - `enables-use-of` → Place Deployable (`skill:place-deployable`)
- [ ] **Peripheral (Control)** (`rule:peripheral-type:control`) — pending
  - outgoing: none
- [ ] **Peripheral (Cyberplug)** (`rule:peripheral-type:cyberplug`) — pending
  - outgoing: none
- [ ] **Peripheral (Servant)** (`rule:peripheral-type:servant`) — pending
  - outgoing: none
- [ ] **Peripheral (Synchronized)** (`rule:peripheral-type:synchronized`) — pending
  - outgoing: none

#### Skill (10/10)

- [x] **BS=11** (`skill:bs-11`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → BS Attack (`skill:bs-attack`)
- [x] **BS=12** (`skill:bs-12`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → BS Attack (`skill:bs-attack`)
- [x] **CC=21** (`skill:cc-21`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → CC Attack (`skill:cc-attack`)
- [x] **Martial Arts L1** (`skill:martial-arts-l1`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → Martial Arts (`skill:martial-arts`)
- [x] **Martial Arts L2** (`skill:martial-arts-l2`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → Martial Arts (`skill:martial-arts`)
- [x] **Martial Arts L3** (`skill:martial-arts-l3`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → Martial Arts (`skill:martial-arts`)
- [x] **Martial Arts L4** (`skill:martial-arts-l4`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → Martial Arts (`skill:martial-arts`)
- [x] **Martial Arts L5** (`skill:martial-arts-l5`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → Martial Arts (`skill:martial-arts`)
- [x] **Strategos L1** (`skill:strategos-l1`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → Strategos (`skill:strategos`)
- [x] **Strategos L2** (`skill:strategos-l2`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → Strategos (`skill:strategos`)

#### State (6/10)

- [x] **Camouflaged State** (`state:camouflaged`) — reviewed
  - `enables-use-of` → Surprise Attack (`skill:surprise-attack`)
- [ ] **Disconnected State** (`state:disconnected`) — pending
  - outgoing: none
- [x] **Hidden Deployment State** (`state:hidden-deployment`) — reviewed
  - `enables-use-of` → Surprise Attack (`skill:surprise-attack`)
- [x] **Immobilized-A State** (`state:immobilized-a`) — reviewed
  - `modifies-rolls-for` → Dodge (`skill:dodge`)
- [x] **Immobilized-B State** (`state:immobilized-b`) — reviewed
  - `modifies-rolls-for` → Reset (`skill:reset`)
- [x] **Isolated State** (`state:isolated`) — reviewed
  - `modifies-rolls-for` → Reset (`skill:reset`)
- [ ] **Stunned State** (`state:stunned`) — pending
  - outgoing: none
- [x] **Targeted State** (`state:targeted`) — reviewed
  - `modifies-rolls-for` → BS Attack (`skill:bs-attack`)
  - `modifies-rolls-for` → Discover (`skill:discover`)
  - `modifies-rolls-for` → Reset (`skill:reset`)
  - `restricts-use-of` → Cautious Movement (`skill:cautious-movement`)
  - `restricts-use-of` → Stealth (`skill:stealth`)
- [ ] **Unconscious State** (`state:unconscious`) — pending
  - outgoing: none
- [ ] **Unloaded State** (`state:unloaded`) — pending
  - outgoing: none

#### Training (0/2)

- [ ] **Irregular** (`training:irregular`) — pending
  - outgoing: none
- [ ] **Regular** (`training:regular`) — pending
  - outgoing: none

#### Trait (0/5)

- [ ] **ARM = 0** (`trait:arm-0`) — pending
  - outgoing: none
- [ ] **ARO** (`trait:aro`) — pending
  - outgoing: none
- [ ] **BTS = 0** (`trait:bts-0`) — pending
  - outgoing: none
- [ ] **Burst (B)** (`trait:burst-b`) — pending
  - outgoing: none
- [ ] **Prior Deployment** (`trait:prior-deployment`) — pending
  - outgoing: none

#### Weapon (0/1)

- [ ] **Armed Turret** (`weapon:armed-turret`) — pending
  - outgoing: none

## Future interaction queue

- [ ] AI Motorcycle (`equipment:ai-motorcycle`) → Transmutation (`skill:transmutation`); `uses-effects-of`; **0.7.0 / planned** — AI Motorcycle explicitly applies Transmutation (Auto); materialize the edge once the canonical Transmutation Skill definition is added.
- [ ] Escape System (`equipment:escape-system`) → Transmutation (`skill:transmutation`); `uses-effects-of`; **0.7.0 / planned** — Escape System is the Army Equipment identity for Transmutation (Escape System-X); materialize the reuse edge once Transmutation has a canonical Skill definition.
- [ ] GizmoKit (`equipment:gizmokit`) → Remote Presence (`skill:remote-presence`); `relation type TBD`; **0.7.0 / planned** — GizmoKit has a specific interaction with Remote Presence that changes how many Wounds are removed when Unconscious State is canceled; choose the precise relation after the Remote Presence rule definition is available.
- [ ] GizmoKit (`equipment:gizmokit`) → Tech-recovery (`skill:tech-recovery`); `enables-use-of`; **0.7.0 / planned** — Tech-Recovery requires a successful allied GizmoKit use; materialize the prerequisite edge when Tech-Recovery gains its canonical Skill definition.
- [ ] SymbioMate (`equipment:symbiomate`) → Immunity (`skill:immunity`); `uses-effects-of`; **0.7.0 / planned** — SymbioMate grants Immunity (Enhanced) for eligible Saving Rolls; materialize the reuse edge when Immunity has its canonical Skill definition.
- [ ] TinBot: Neurocinetics (`equipment:tinbot-neurocinetics`) → Neurocinetics (`skill:neurocinetics`); `uses-effects-of`; **0.7.0 / planned** — TinBot: Neurocinetics grants that Special Skill; materialize the edge when Neurocinetics gains its canonical Skill definition.
- [ ] Biometric Visor (`equipment:biometric-visor`) → `state:impersonation-1`; `cancels-state`; **post-0.7.0 / planned** — A successful Discover Roll with Biometric Visor cancels Impersonation-1 State; materialize the State edge once Impersonation-1 has a canonical State identity.
- [ ] Dazer (`equipment:dazer`) → `rule:difficult-terrain`; `relation type TBD`; **post-0.7.0 / deferred** — Dazer creates a Difficult Terrain area in its Zone of Control, but the current graph has neither a canonical Difficult Terrain identity nor a precise creates-area relation.
- [ ] Deactivator (`equipment:deactivator`) → `rule:cover`; `ignores-modifiers-from`; **post-0.7.0 / planned** — Deactivator explicitly ignores Cover MODs on its WIP Roll; materialize the edge once Cover has a canonical rules identity.
- [ ] Deactivator (`equipment:deactivator`) → Deployable (`trait:deployable`); `relation type TBD`; **post-0.7.0 / deferred** — Deactivator targets and removes deployed enemy Weapons or Equipment with Deployable semantics; the current graph lacks a precise target-eligibility/removes-game-element relation.
- [ ] Deployable Cover (`equipment:deployable-cover`) → `rule:partial-cover`; `uses-effects-of`; **post-0.7.0 / planned** — Deployable Cover explicitly applies Partial Cover with variant-specific changes; materialize the reuse edge once Partial Cover has a canonical rules identity.
- [ ] EVO Hacking Device (`equipment:evo-hacking-device`) → `hacking-program:assisted-fire`; `enables-use-of`; **post-0.7.0 / planned** — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
- [ ] EVO Hacking Device (`equipment:evo-hacking-device`) → `hacking-program:controlled-jump`; `enables-use-of`; **post-0.7.0 / planned** — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
- [ ] EVO Hacking Device (`equipment:evo-hacking-device`) → `hacking-program:enhanced-reaction`; `enables-use-of`; **post-0.7.0 / planned** — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
- [ ] EVO Hacking Device (`equipment:evo-hacking-device`) → `hacking-program:fairy-dust`; `enables-use-of`; **post-0.7.0 / planned** — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
- [ ] Hacking Device (`equipment:hacking-device`) → `hacking-program:carbonite`; `enables-use-of`; **post-0.7.0 / planned** — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
- [ ] Hacking Device (`equipment:hacking-device`) → `hacking-program:oblivion`; `enables-use-of`; **post-0.7.0 / planned** — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
- [ ] Hacking Device (`equipment:hacking-device`) → `hacking-program:spotlight`; `enables-use-of`; **post-0.7.0 / planned** — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
- [ ] Hacking Device (`equipment:hacking-device`) → `hacking-program:total-control`; `enables-use-of`; **post-0.7.0 / planned** — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
- [ ] Hacking Device Plus (`equipment:hacking-device-plus`) → `hacking-program:carbonite`; `enables-use-of`; **post-0.7.0 / planned** — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
- [ ] Hacking Device Plus (`equipment:hacking-device-plus`) → `hacking-program:cybermask`; `enables-use-of`; **post-0.7.0 / planned** — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
- [ ] Hacking Device Plus (`equipment:hacking-device-plus`) → `hacking-program:oblivion`; `enables-use-of`; **post-0.7.0 / planned** — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
- [ ] Hacking Device Plus (`equipment:hacking-device-plus`) → `hacking-program:spotlight`; `enables-use-of`; **post-0.7.0 / planned** — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
- [ ] Hacking Device Plus (`equipment:hacking-device-plus`) → `hacking-program:total-control`; `enables-use-of`; **post-0.7.0 / planned** — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
- [ ] Hacking Device Plus (`equipment:hacking-device-plus`) → `hacking-program:white-noise`; `enables-use-of`; **post-0.7.0 / planned** — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
- [ ] Holomask (`equipment:holomask`) → `state:holomask`; `enters-state`; **post-0.7.0 / planned** — HoloMask explicitly lets its user deploy in or enter HoloMask State; materialize the State edge when that supporting State identity is added.
- [ ] Holoprojector (`equipment:holoprojector`) → `state:holoecho`; `enters-state`; **post-0.7.0 / planned** — Holoprojector explicitly lets its user deploy in or enter Holoecho State; materialize the State edge when that supporting State identity is added.
- [ ] Killer Hacking Device (`equipment:killer-hacking-device`) → `hacking-program:cybermask`; `enables-use-of`; **post-0.7.0 / planned** — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
- [ ] Killer Hacking Device (`equipment:killer-hacking-device`) → `hacking-program:trinity`; `enables-use-of`; **post-0.7.0 / planned** — The Hacking Device explicitly grants access to this Hacking Program; retain the interaction until the Hacking Program domain is materialized.
- [ ] MediKit (`equipment:medikit`) → `state:dead`; `causes-state`; **post-0.7.0 / planned** — A failed MediKit target PH Roll makes the target enter Dead State; materialize the edge when Dead State has a canonical rules identity.
- [ ] Motorcycle (`equipment:motorcycle`) → `state:prone`; `relation type TBD`; **post-0.7.0 / planned** — Motorcycle prevents its mounted user from entering Prone State; the current relation vocabulary has no precise state-entry restriction edge.
- [ ] Repeater (`equipment:repeater`) → `rule:hacking-area`; `relation type TBD`; **post-0.7.0 / deferred** — Repeater extends allied Hacking Areas and allows enemy Hackers in its Zone of Control to use that network; the current relation vocabulary has no precise Hacking-Area extension edge.
- [ ] TinBot: Firewall (`equipment:tinbot-firewall`) → `equipment:firewall`; `uses-effects-of`; **post-0.7.0 / planned** — TinBot: Firewall grants the Firewall advantage; materialize the edge when Firewall is modeled as a standalone supporting Equipment rule.
- [ ] `hacking-program:white-noise` → Multispectral Visor (`equipment:multispectral-visor`); `relation type TBD`; **post-0.7.0 / deferred** — White Noise is a documented Multispectral Visor counter-interaction, but Hacking Programs are outside the 0.7.0 catalog scope and need their own canonical domain first.
- [ ] `hacking-program:white-noise` → Marksmanship (`skill:marksmanship`); `relation type TBD`; **post-0.7.0 / deferred** — White Noise is a documented Marksmanship counter-interaction, but Hacking Programs are outside the 0.7.0 catalog scope and need their own canonical domain first.
- [ ] `rule:marker-form` → Surprise Attack (`skill:surprise-attack`); `enables-use-of`; **post-0.7.0 / planned** — Surprise Attack can begin from Marker form beyond the currently modeled Camouflaged example; add the generic prerequisite edge once Marker form is a canonical abstraction, while Hidden Deployment remains a separate enabling State.
- [ ] Climb (`skill:climb`) → `rule:partial-cover`; `relation type TBD`; **post-0.7.0 / deferred** — Climb explicitly prevents the user from benefiting from Partial Cover MODs, but Partial Cover is not yet a canonical rules identity and the current relation vocabulary does not distinguish loss of beneficial MODs cleanly.
- [ ] Idle (`skill:idle`) → `rule:marker-form`; `relation type TBD`; **post-0.7.0 / deferred** — A failed declaration that resolves as Idle reveals a Trooper in Marker form; the graph needs a canonical Marker-form abstraction before this can be represented without enumerating only some Marker States.
- [ ] Intuitive Attack (`skill:intuitive-attack`) → Camouflaged State (`state:camouflaged`); `relation type TBD`; **post-0.7.0 / deferred** — Intuitive Attack can attack targets in States such as Camouflaged without first Discovering them, but the current relation vocabulary has no precise bypasses-targeting-protection edge.
- [ ] Jump (`skill:jump`) → `rule:partial-cover`; `relation type TBD`; **post-0.7.0 / deferred** — A Trooper that declares Jump cannot benefit from Partial Cover MODs during that Order; Partial Cover and the appropriate benefit-suppression relation need canonical modeling first.
- [ ] Jump (`skill:jump`) → `state:prone`; `cancels-state`; **post-0.7.0 / planned** — Declaring Jump explicitly cancels Prone State; materialize this edge once Prone State is promoted to a canonical rules identity.
- [ ] Limited Cover (`skill:limited-cover`) → `rule:partial-cover`; `relation type TBD`; **post-0.7.0 / deferred** — Limited Cover removes only the -3 BS MOD from Partial Cover while leaving its other effects intact; Partial Cover needs a canonical identity and the graph needs a relation more precise than globally negating the rule.
- [ ] Place Deployable (`skill:place-deployable`) → Camouflaged State (`state:camouflaged`); `relation type TBD`; **post-0.7.0 / deferred** — Enemy Camouflaged Markers can restrict legal Deployable placement through Trigger Area rules, but this is a placement constraint rather than a general restriction on declaring Place Deployable.
- [ ] Request Speedball (`skill:request-speedball`) → Combat Jump (`skill:combat-jump`); `uses-effects-of`; **post-0.7.0 / planned** — Request Speedball explicitly places its Tokens by applying the Combat Jump Skill rules; materialize the edge once Combat Jump has a full canonical Skill definition.
- [ ] Stealth (`skill:stealth`) → Idle (`skill:idle`); `relation type TBD`; **post-0.7.0 / deferred** — Stealth changes which enemies receive AROs when the user declares Idle, but the current relation vocabulary has no precise ARO-generation modifier edge.
- [ ] Stealth (`skill:stealth`) → Move (`skill:move`); `relation type TBD`; **post-0.7.0 / deferred** — Stealth changes which enemies receive AROs for a Basic Short Skill with the Movement Label, including Move; the current relation vocabulary has no precise ARO-generation modifier edge.
- [ ] Super-Jump (`skill:super-jump`) → Jump (`skill:jump`); `relation type TBD`; **post-0.7.0 / deferred** — Super-Jump changes how Jump is declared/executed; the current relation vocabulary has no precise transformation edge.
- [ ] Suppressive Fire (`skill:suppressive-fire`) → `state:suppressive-fire`; `enters-state`; **post-0.7.0 / planned** — Suppressive Fire explicitly places the user in Suppressive Fire State; materialize the edge once that State is promoted to the canonical State catalog.
- [ ] Surprise Attack (`skill:surprise-attack`) → `rule:face-to-face-roll`; `imposes-modifiers-on`; **post-0.7.0 / planned** — Surprise Attack applies its listed negative MOD to any Face to Face Roll made in ARO by a target of the Attack; model the generic Roll interaction once Face to Face Rolls have a canonical rules identity rather than incorrectly linking only selected Skills.
- [ ] Perimeter (`trait:perimeter`) → Place Deployable (`skill:place-deployable`); `relation type TBD`; **post-0.7.0 / deferred** — Perimeter changes Place Deployable placement behavior rather than enabling the Skill; the current relation vocabulary has no precise modifier edge.
