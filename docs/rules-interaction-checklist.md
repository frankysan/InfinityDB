# Rules interaction review checklist

This file is generated from the maintained interaction-review policy and the current
curated rules graph. Do not edit it by hand. Regenerate it with:

```powershell
python tools/audit_rules_interactions.py --output docs/rules-interaction-checklist.md
```

A checked entity means its **outgoing** interaction semantics have been reviewed for
its target release. `inherited` means an exact source variant uses the reviewed family
semantics unless a variant-specific exception is later identified. A checked entity may
still have explicitly tracked future interactions; those stay in the future queue until
their target release/model is ready.

`declaration-category` projection records are excluded because they classify Skills/
Equipment rather than representing independently reviewable gameplay identities.

## Progress

- **0.7.0: 70/110 complete (63.6%), 40 pending.**
- Current authored outgoing relations: **87**.
- Explicitly tracked future/deferred interactions: **14**.

## 0.7.0 entity review

### Equipment (9/10)

- [x] **Albedo** (`equipment:albedo`) — reviewed
  - `imposes-modifiers-on` → Multispectral Visor (`equipment:multispectral-visor`)
  - `imposes-modifiers-on` → Marksmanship (`skill:marksmanship`)
- [x] **Baggage** (`equipment:baggage`) — reviewed
  - `enables-use-of` → Reload (`skill:reload`)
  - `cancels-state` → Unloaded State (`state:unloaded`)
- [x] **Multispectral Visor** (`equipment:multispectral-visor`) — reviewed
  - `reduces-modifiers-from` → Mimetism (`skill:mimetism`)
- [ ] **TinBot** (`equipment:tinbot`) — pending
  - outgoing: none
- [x] **TinBot: Albedo** (`equipment:tinbot-albedo`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → TinBot (`equipment:tinbot`)
- [x] **TinBot: Discover** (`equipment:tinbot-discover`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → TinBot (`equipment:tinbot`)
- [x] **TinBot: ECM Guided** (`equipment:tinbot-ecm-guided`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → TinBot (`equipment:tinbot`)
- [x] **TinBot: Firewall** (`equipment:tinbot-firewall`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → TinBot (`equipment:tinbot`)
- [x] **TinBot: Neurocinetics** (`equipment:tinbot-neurocinetics`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → TinBot (`equipment:tinbot`)
- [x] **TinBot: Repeater** (`equipment:tinbot-repeater`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → TinBot (`equipment:tinbot`)

### Rule (1/5)

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

### Skill (45/49)

- [x] **Alert** (`skill:alert`) — reviewed
  - outgoing: none
- [x] **BS Attack** (`skill:bs-attack`) — reviewed
  - outgoing: none
- [x] **BS=11** (`skill:bs-11`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → BS Attack (`skill:bs-attack`)
- [x] **BS=12** (`skill:bs-12`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → BS Attack (`skill:bs-attack`)
- [x] **Camouflage** (`skill:camouflage`) — reviewed
  - `enters-state` → Camouflaged State (`state:camouflaged`)
- [x] **Cautious Movement** (`skill:cautious-movement`) — reviewed
  - outgoing: none
- [x] **CC Attack** (`skill:cc-attack`) — reviewed
  - outgoing: none
- [x] **CC=21** (`skill:cc-21`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → CC Attack (`skill:cc-attack`)
- [x] **Climb** (`skill:climb`) — reviewed
  - outgoing: none
  - future [post-0.7.0; deferred]: `relation type TBD` → `rule:partial-cover` — Climb explicitly prevents the user from benefiting from Partial Cover MODs, but Partial Cover is not yet a canonical rules identity and the current relation vocabulary does not distinguish loss of beneficial MODs cleanly.
- [x] **Combat Instinct** (`skill:combat-instinct`) — reviewed
  - `ignores-modifiers-from` → Surprise Attack (`skill:surprise-attack`)
  - `negates-effects-of` → Stealth (`skill:stealth`)
- [x] **Cyberplug** (`skill:cyberplug`) — reviewed
  - `controller-eligible-for` → Peripheral (Cyberplug) (`rule:peripheral-type:cyberplug`)
- [x] **Discover** (`skill:discover`) — reviewed
  - `reveals-state` → Camouflaged State (`state:camouflaged`)
- [x] **Doctor** (`skill:doctor`) — reviewed
  - `controller-eligible-for` → Peripheral (Servant) (`rule:peripheral-type:servant`)
  - `cancels-state` → Unconscious State (`state:unconscious`)
  - `cancels-state` → Stunned State (`state:stunned`)
- [x] **Dodge** (`skill:dodge`) — reviewed
  - `cancels-state` → Immobilized-A State (`state:immobilized-a`)
- [x] **Engineer** (`skill:engineer`) — reviewed
  - `controller-eligible-for` → Peripheral (Servant) (`rule:peripheral-type:servant`)
  - `cancels-state` → Disconnected State (`state:disconnected`)
  - `cancels-state` → Immobilized-A State (`state:immobilized-a`)
  - `cancels-state` → Immobilized-B State (`state:immobilized-b`)
  - `cancels-state` → Isolated State (`state:isolated`)
  - `cancels-state` → Stunned State (`state:stunned`)
  - `cancels-state` → Targeted State (`state:targeted`)
  - `cancels-state` → Unconscious State (`state:unconscious`)
- [ ] **Forward Deployment** (`skill:forward-deployment`) — pending
  - outgoing: none
- [x] **Forward Observer** (`skill:forward-observer`) — reviewed
  - `causes-state` → Targeted State (`state:targeted`)
- [x] **Hidden Deployment** (`skill:hidden-deployment`) — reviewed
  - `enters-state` → Hidden Deployment State (`state:hidden-deployment`)
- [x] **Idle** (`skill:idle`) — reviewed
  - outgoing: none
  - future [post-0.7.0; deferred]: `relation type TBD` → `rule:marker-form` — A failed declaration that resolves as Idle reveals a Trooper in Marker form; the graph needs a canonical Marker-form abstraction before this can be represented without enumerating only some Marker States.
- [x] **Intuitive Attack** (`skill:intuitive-attack`) — reviewed
  - outgoing: none
  - future [post-0.7.0; deferred]: `relation type TBD` → Camouflaged State (`state:camouflaged`) — Intuitive Attack can attack targets in States such as Camouflaged without first Discovering them, but the current relation vocabulary has no precise bypasses-targeting-protection edge.
- [x] **Jump** (`skill:jump`) — reviewed
  - outgoing: none
  - future [post-0.7.0; planned]: `cancels-state` → `state:prone` — Declaring Jump explicitly cancels Prone State; materialize this edge once Prone State is promoted to a canonical rules identity.
  - future [post-0.7.0; deferred]: `relation type TBD` → `rule:partial-cover` — A Trooper that declares Jump cannot benefit from Partial Cover MODs during that Order; Partial Cover and the appropriate benefit-suppression relation need canonical modeling first.
- [ ] **Limited Cover** (`skill:limited-cover`) — pending
  - outgoing: none
- [x] **Look Out** (`skill:look-out`) — reviewed
  - `modifies-rolls-for` → Dodge (`skill:dodge`)
- [x] **Marksmanship** (`skill:marksmanship`) — reviewed
  - `modifies-rolls-for` → BS Attack (`skill:bs-attack`)
- [x] **Martial Arts** (`skill:martial-arts`) — reviewed
  - `modifies-rolls-for` → CC Attack (`skill:cc-attack`)
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
- [x] **Mimetism** (`skill:mimetism`) — reviewed
  - `imposes-modifiers-on` → BS Attack (`skill:bs-attack`)
  - `imposes-modifiers-on` → Discover (`skill:discover`)
- [x] **Move** (`skill:move`) — reviewed
  - outgoing: none
- [x] **Natural Born Warrior** (`skill:natural-born-warrior`) — reviewed
  - `ignores-modifiers-from` → Martial Arts (`skill:martial-arts`)
  - `ignores-modifiers-from` → Surprise Attack (`skill:surprise-attack`)
- [x] **No Cover** (`skill:no-cover`) — reviewed
  - `overrides-effects-of` → Limited Cover (`skill:limited-cover`)
- [x] **Peripheral** (`skill:peripheral`) — reviewed
  - `has-subtype` → Peripheral (Servant) (`rule:peripheral-type:servant`)
  - `has-subtype` → Peripheral (Synchronized) (`rule:peripheral-type:synchronized`)
  - `has-subtype` → Peripheral (Control) (`rule:peripheral-type:control`)
  - `has-subtype` → Peripheral (Ancillary) (`rule:peripheral-type:ancillary`)
  - `has-subtype` → Peripheral (Cyberplug) (`rule:peripheral-type:cyberplug`)
- [x] **Place Deployable** (`skill:place-deployable`) — reviewed
  - outgoing: none
  - future [post-0.7.0; deferred]: `relation type TBD` → Camouflaged State (`state:camouflaged`) — Enemy Camouflaged Markers can restrict legal Deployable placement through Trigger Area rules, but this is a placement constraint rather than a general restriction on declaring Place Deployable.
- [x] **Reload** (`skill:reload`) — reviewed
  - `cancels-state` → Unloaded State (`state:unloaded`)
- [x] **Request Speedball** (`skill:request-speedball`) — reviewed
  - outgoing: none
  - future [post-0.7.0; planned]: `uses-effects-of` → `skill:combat-jump` — Request Speedball explicitly places its Tokens by applying the Combat Jump Skill rules; materialize the edge once Combat Jump has a full canonical Skill definition.
- [x] **Reset** (`skill:reset`) — reviewed
  - `cancels-state` → Targeted State (`state:targeted`)
  - `cancels-state` → Immobilized-B State (`state:immobilized-b`)
  - `cancels-state` → Isolated State (`state:isolated`)
- [x] **Sensor** (`skill:sensor`) — reviewed
  - `ignores-modifiers-from` → Mimetism (`skill:mimetism`)
  - `modifies-rolls-for` → Discover (`skill:discover`)
  - `restricts-use-of` → Camouflage (`skill:camouflage`)
  - `reveals-state` → Camouflaged State (`state:camouflaged`)
  - `reveals-state` → Hidden Deployment State (`state:hidden-deployment`)
- [x] **Sixth Sense** (`skill:sixth-sense`) — reviewed
  - `negates-effects-of` → Stealth (`skill:stealth`)
  - `modifies-rolls-for` → Dodge (`skill:dodge`)
  - `modifies-rolls-for` → Reset (`skill:reset`)
- [x] **Speculative Attack** (`skill:speculative-attack`) — reviewed
  - `ignores-modifiers-from` → Mimetism (`skill:mimetism`)
- [x] **Stealth** (`skill:stealth`) — reviewed
  - `enables-use-of` → Cautious Movement (`skill:cautious-movement`)
  - future [post-0.7.0; deferred]: `relation type TBD` → Idle (`skill:idle`) — Stealth changes which enemies receive AROs when the user declares Idle, but the current relation vocabulary has no precise ARO-generation modifier edge.
  - future [post-0.7.0; deferred]: `relation type TBD` → Move (`skill:move`) — Stealth changes which enemies receive AROs for a Basic Short Skill with the Movement Label, including Move; the current relation vocabulary has no precise ARO-generation modifier edge.
- [ ] **Strategos** (`skill:strategos`) — pending
  - outgoing: none
- [x] **Strategos L1** (`skill:strategos-l1`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → Strategos (`skill:strategos`)
- [x] **Strategos L2** (`skill:strategos-l2`) — inherited: Exact source variant inherits family interaction semantics; variant-of remains structural.
  - `variant-of` → Strategos (`skill:strategos`)
- [x] **Super-Jump** (`skill:super-jump`) — reviewed
  - outgoing: none
  - future [post-0.7.0; deferred]: `relation type TBD` → Jump (`skill:jump`) — Super-Jump changes how Jump is declared/executed; the current relation vocabulary has no precise transformation edge.
- [x] **Suppressive Fire** (`skill:suppressive-fire`) — reviewed
  - outgoing: none
  - future [post-0.7.0; planned]: `enters-state` → `state:suppressive-fire` — Suppressive Fire explicitly places the user in Suppressive Fire State; materialize the edge once that State is promoted to the canonical State catalog.
- [ ] **Surprise Attack** (`skill:surprise-attack`) — pending
  - outgoing: none

### State (6/10)

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

### Training (0/2)

- [ ] **Irregular** (`training:irregular`) — pending
  - outgoing: none
- [ ] **Regular** (`training:regular`) — pending
  - outgoing: none

### Trait (9/33)

- [ ] **Anti-materiel** (`trait:anti-materiel`) — pending
  - outgoing: none
- [ ] **ARM = 0** (`trait:arm-0`) — pending
  - outgoing: none
- [ ] **ARO** (`trait:aro`) — pending
  - outgoing: none
- [ ] **BioWeapon** (`trait:bioweapon`) — pending
  - outgoing: none
- [ ] **Boost** (`trait:boost`) — pending
  - outgoing: none
- [ ] **BS Weapon (PH)** (`trait:bs-weapon-ph`) — pending
  - outgoing: none
- [ ] **BS Weapon (WIP)** (`trait:bs-weapon-wip`) — pending
  - outgoing: none
- [ ] **BTS = 0** (`trait:bts-0`) — pending
  - outgoing: none
- [ ] **Burst (B)** (`trait:burst-b`) — pending
  - outgoing: none
- [ ] **Burst: Single Target** (`trait:burst-single-target`) — pending
  - outgoing: none
- [ ] **CC** (`trait:cc`) — pending
  - outgoing: none
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
- [ ] **Non-Lethal** (`trait:non-lethal`) — pending
  - outgoing: none
- [ ] **Non-Reloadable** (`trait:non-reloadable`) — pending
  - outgoing: none
- [x] **Perimeter** (`trait:perimeter`) — reviewed
  - outgoing: none
  - future [post-0.7.0; deferred]: `relation type TBD` → Place Deployable (`skill:place-deployable`) — Perimeter changes Place Deployable placement behavior rather than enabling the Skill; the current relation vocabulary has no precise modifier edge.
- [ ] **Prior Deployment** (`trait:prior-deployment`) — pending
  - outgoing: none
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
- [ ] **Zone of Control (ZoC)** (`trait:zone-of-control-zc`) — pending
  - outgoing: none

### Weapon (0/1)

- [ ] **Armed Turret** (`weapon:armed-turret`) — pending
  - outgoing: none

## Future interaction queue

- [ ] `hacking-program:white-noise` → Multispectral Visor (`equipment:multispectral-visor`); `relation type TBD`; **post-0.7.0 / deferred** — White Noise is a documented Multispectral Visor counter-interaction, but Hacking Programs are outside the 0.7.0 catalog scope and need their own canonical domain first.
- [ ] `hacking-program:white-noise` → Marksmanship (`skill:marksmanship`); `relation type TBD`; **post-0.7.0 / deferred** — White Noise is a documented Marksmanship counter-interaction, but Hacking Programs are outside the 0.7.0 catalog scope and need their own canonical domain first.
- [ ] Climb (`skill:climb`) → `rule:partial-cover`; `relation type TBD`; **post-0.7.0 / deferred** — Climb explicitly prevents the user from benefiting from Partial Cover MODs, but Partial Cover is not yet a canonical rules identity and the current relation vocabulary does not distinguish loss of beneficial MODs cleanly.
- [ ] Idle (`skill:idle`) → `rule:marker-form`; `relation type TBD`; **post-0.7.0 / deferred** — A failed declaration that resolves as Idle reveals a Trooper in Marker form; the graph needs a canonical Marker-form abstraction before this can be represented without enumerating only some Marker States.
- [ ] Intuitive Attack (`skill:intuitive-attack`) → Camouflaged State (`state:camouflaged`); `relation type TBD`; **post-0.7.0 / deferred** — Intuitive Attack can attack targets in States such as Camouflaged without first Discovering them, but the current relation vocabulary has no precise bypasses-targeting-protection edge.
- [ ] Jump (`skill:jump`) → `rule:partial-cover`; `relation type TBD`; **post-0.7.0 / deferred** — A Trooper that declares Jump cannot benefit from Partial Cover MODs during that Order; Partial Cover and the appropriate benefit-suppression relation need canonical modeling first.
- [ ] Jump (`skill:jump`) → `state:prone`; `cancels-state`; **post-0.7.0 / planned** — Declaring Jump explicitly cancels Prone State; materialize this edge once Prone State is promoted to a canonical rules identity.
- [ ] Place Deployable (`skill:place-deployable`) → Camouflaged State (`state:camouflaged`); `relation type TBD`; **post-0.7.0 / deferred** — Enemy Camouflaged Markers can restrict legal Deployable placement through Trigger Area rules, but this is a placement constraint rather than a general restriction on declaring Place Deployable.
- [ ] Request Speedball (`skill:request-speedball`) → `skill:combat-jump`; `uses-effects-of`; **post-0.7.0 / planned** — Request Speedball explicitly places its Tokens by applying the Combat Jump Skill rules; materialize the edge once Combat Jump has a full canonical Skill definition.
- [ ] Stealth (`skill:stealth`) → Idle (`skill:idle`); `relation type TBD`; **post-0.7.0 / deferred** — Stealth changes which enemies receive AROs when the user declares Idle, but the current relation vocabulary has no precise ARO-generation modifier edge.
- [ ] Stealth (`skill:stealth`) → Move (`skill:move`); `relation type TBD`; **post-0.7.0 / deferred** — Stealth changes which enemies receive AROs for a Basic Short Skill with the Movement Label, including Move; the current relation vocabulary has no precise ARO-generation modifier edge.
- [ ] Super-Jump (`skill:super-jump`) → Jump (`skill:jump`); `relation type TBD`; **post-0.7.0 / deferred** — Super-Jump changes how Jump is declared/executed; the current relation vocabulary has no precise transformation edge.
- [ ] Suppressive Fire (`skill:suppressive-fire`) → `state:suppressive-fire`; `enters-state`; **post-0.7.0 / planned** — Suppressive Fire explicitly places the user in Suppressive Fire State; materialize the edge once that State is promoted to the canonical State catalog.
- [ ] Perimeter (`trait:perimeter`) → Place Deployable (`skill:place-deployable`); `relation type TBD`; **post-0.7.0 / deferred** — Perimeter changes Place Deployable placement behavior rather than enabling the Skill; the current relation vocabulary has no precise modifier edge.
