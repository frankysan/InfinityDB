import { getUnit } from "./api.js";
import { armySymbolPath } from "./army-symbols.js";
import { unitSymbol } from "./unit-symbols.js";
import { distanceUnit, formatDistanceExtra, initializeDistanceUnitToggle, optionalUnitFilters } from "./preferences.js";

const name = document.getElementById("unit-name");
const meta = document.getElementById("unit-meta");
const status = document.getElementById("unit-status");
const content = document.getElementById("unit-content");
const unitId = /^\/units\/(\d+)$/.exec(window.location.pathname)?.[1];

function text(value) { return value == null || value === "" ? "—" : String(value); }

const factionGroups = new Map([
  [1, "PanOceania"],
  [2, "Yu Jing"],
  [3, "Ariadna"],
  [4, "Haqqislam"],
  [5, "Nomads"],
  [6, "Combined Army"],
  [7, "ALEPH"],
  [8, "Tohaa"],
  [9, "Non-Aligned Armies"],
  [10, "O-12"],
  [11, "JSA"],
]);
const factionSlugs = new Map([
  [1, "panoceania"], [2, "yu-jing"], [3, "ariadna"], [4, "haqqislam"],
  [5, "nomads"], [6, "combined-army"], [7, "aleph"], [8, "tohaa"],
  [9, "non-aligned-armies"], [10, "o-12"], [11, "jsa"],
]);

function factionSlug(armyId) {
  return factionSlugs.get(Math.floor(Number(armyId) / 100));
}

function factionGroup(armyId) {
  const key = Math.floor(Number(armyId) / 100);
  return {
    key,
    name: factionGroups.get(key) || "Other armies",
    order: key,
  };
}

function groupArmiesByFaction(armies) {
  const groups = new Map();
  for (const army of armies) {
    const group = factionGroup(army.id);
    if (!groups.has(group.key)) groups.set(group.key, { ...group, armies: [] });
    groups.get(group.key).armies.push(army);
  }
  return [...groups.values()]
    .sort((left, right) => left.order - right.order)
    .map((group) => ({
      ...group,
      armies: group.armies.sort((left, right) => (
        Number(left.id) - Number(right.id)
        || Number((left.availability_flags || []).includes("mercs"))
          - Number((right.availability_flags || []).includes("mercs"))
      )),
    }));
}

function cell(value) {
  const structured = value && typeof value === "object";
  const element = document.createElement(structured && value.header ? "th" : "td");
  const highlighted = structured && "highlight" in value;
  if (structured && value.content) element.append(value.content);
  else element.textContent = text(structured && "value" in value ? value.value : value);
  if (structured && value.header) element.scope = "row";
  if (value && typeof value === "object" && value.className) {
    element.classList.add(...value.className.split(/\s+/));
  }
  if (value && typeof value === "object" && value.colSpan) {
    element.colSpan = value.colSpan;
  }
  if (highlighted && value.highlight) {
    element.className = "stat-different";
    element.title = "Differs from the general profile";
  }
  return element;
}

function attributeStatline(stats, generalStats = null, includeAvailability = false) {
  const attributes = document.createElement("div");
  attributes.className = "attribute-statline";
  for (const [label, read] of statColumns) {
    const attribute = document.createElement("div");
    if (label === "MOV") attribute.classList.add("movement-attribute");
    const attributeLabel = document.createElement("span");
    attributeLabel.className = "attribute-label";
    const attributeValue = document.createElement("span");
    attributeValue.className = "attribute-value";
    const value = displayStatlineValue(read(stats));
    attributeLabel.textContent = label;
    attributeValue.textContent = text(value);
    attribute.append(attributeLabel, attributeValue);
    if (generalStats && differsFromGeneral(stats, generalStats, label)) {
      attribute.classList.add("stat-different");
      attribute.title = "Differs from the general profile";
    }
    attributes.append(attribute);
  }
  if (includeAvailability) {
    attributes.classList.add("attribute-statline-with-availability");
    const attribute = document.createElement("div");
    const attributeLabel = document.createElement("span");
    const attributeValue = document.createElement("span");
    attributeLabel.className = "attribute-label";
    attributeValue.className = "attribute-value";
    attributeLabel.textContent = "AVA";
    attributeValue.textContent = text(displayAvailability(stats.ava));
    attribute.append(attributeLabel, attributeValue);
    attributes.append(attribute);
  }
  return attributes;
}

function table(headers, rows, className = "") {
  const element = document.createElement("table");
  element.className = className;
  if (headers.length) {
    const head = document.createElement("thead");
    const headerRow = document.createElement("tr");
    for (const header of headers) { const th = document.createElement("th"); th.textContent = header; headerRow.append(th); }
    head.append(headerRow);
    element.append(head);
  }
  const body = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");
    if (row.className) tr.className = row.className;
    row.forEach((value, index) => {
      const item = cell(value);
      if (headers[index]) item.dataset.label = headers[index];
      tr.append(item);
    });
    body.append(tr);
  }
  element.append(body);
  return element;
}

function heading(label) { const value = document.createElement("h2"); value.textContent = label; return value; }

function subheading(label) { const value = document.createElement("h4"); value.textContent = label; return value; }

const statColumns = [
  ["MOV", (profile) => distanceUnit() === "in"
    ? `${inches(profile.move_1)}-${inches(profile.move_2)}`
    : `${text(profile.move_1)}-${text(profile.move_2)}`],
  ["CC", (profile) => profile.cc], ["BS", (profile) => profile.bs],
  ["PH", (profile) => profile.ph], ["WIP", (profile) => profile.wip],
  ["ARM", (profile) => profile.arm], ["BTS", (profile) => profile.bts],
  ["W", (profile) => profile.vitality], ["S", (profile) => profile.silhouette],
];

function isReinforcementArmy(armyId) {
  return [98, 99].includes(Number(armyId) % 100);
}
const statProperties = {
  CC: "cc", BS: "bs", PH: "ph", WIP: "wip", ARM: "arm", BTS: "bts",
  W: "vitality", S: "silhouette",
};

function mostCommon(profiles, property) {
  const counts = new Map();
  for (const profile of profiles) {
    const value = profile[property];
    if (value == null || value === "") continue;
    counts.set(value, (counts.get(value) || 0) + 1);
  }
  let selected = null;
  let highestCount = 0;
  for (const [value, count] of counts) {
    if (count > highestCount) {
      selected = value;
      highestCount = count;
    }
  }
  return selected;
}

function inches(centimeters) {
  if (centimeters == null || centimeters === "") return "—";
  const value = Number(centimeters) / 2.5;
  return Number.isFinite(value) ? String(value) : "—";
}

function generalStats(profiles) {
  return {
    move_1: mostCommon(profiles, "move_1"), move_2: mostCommon(profiles, "move_2"),
    ...Object.fromEntries(Object.values(statProperties).map((property) => [
      property, mostCommon(profiles, property),
    ])),
  };
}

function generalStatline(stats) {
  return statColumns.map(([, read]) => read(stats));
}

function displayStatlineValue(value) {
  return (typeof value === "number" && value < 0)
    || (typeof value === "string" && /^-\d+(?:\.\d+)?$/.test(value.trim()))
    ? "—"
    : value;
}

function displayAvailability(value) {
  return Number(value) >= 100 ? "Total" : displayStatlineValue(value);
}

function identicalStatline(left, right) {
  const rightStatline = generalStatline(right);
  return generalStatline(left).every((value, index) => value === rightStatline[index]);
}

function baseProfileName(profileName) {
  return String(profileName || "").replace(/^REINF(?:\.|:)?\s*/i, "").trim();
}

const profileIdentityWordAliases = {
  armoured: "armored",
  reconnaissance: "recon",
  reconaissance: "recon",
};
const profileIdentityIgnoredWords = new Set([
  "troops", "autonomous", "intervention", "unit",
]);

function profileIdentity(profileName) {
  const words = baseProfileName(profileName)
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .match(/[\p{L}\p{N}]+/gu) || [];
  return words.filter((word) => !profileIdentityIgnoredWords.has(word)).map((word) => {
    const singular = word.length > 3 && word.endsWith("s") && !word.endsWith("ss")
      ? word.slice(0, -1)
      : word;
    return profileIdentityWordAliases[singular] || singular;
  }).sort().join(" ");
}

const orderTypes = ["regular", "irregular"];
const symbolLabels = {
  regular: "Regular Order",
  irregular: "Irregular Order",
  peripheral: "Peripheral",
  impetuous: "Impetuous",
  tactical: "Tactical Awareness",
  lieutenant: "Lieutenant Order",
  hackable: "Hackable",
  cube: "Cube",
  "cube-2": "Cube 2.0",
};

function prominentOrderType(loadouts) {
  const counts = new Map(orderTypes.map((type) => [type, 0]));
  for (const loadout of loadouts) {
    for (const order of loadout.orders || []) {
      const type = String(order.type || "").toLowerCase();
      if (!counts.has(type)) continue;
      const count = Number(order.list) || Number(order.total) || 1;
      counts.set(type, counts.get(type) + count);
    }
  }
  const prominent = orderTypes.reduce((prominent, type) => (
    counts.get(type) > counts.get(prominent) ? type : prominent
  ), orderTypes[0]);
  return counts.get(prominent) ? prominent : null;
}

function hasSkill(items, skillName) {
  return items.some((item) => (
    (item.skills || []).some((skill) => String(skill.name || "").toLowerCase() === skillName)
  ));
}

function normalizedSkillName(value) {
  return String(value || "").toLowerCase().replace(/\s+/g, " ").trim();
}

function lieutenantSkills(items) {
  return items.flatMap((item) => (item.skills || []).filter((skill) => (
    normalizedSkillName(skill.name).startsWith("lieutenant")
  )));
}

function hasLieutenantPlusOne(items) {
  return lieutenantSkills(items).some((skill) => (
    normalizedSkillName(skill.name) === "lieutenant (+1 order)"
    || (normalizedSkillName(skill.name) === "lieutenant"
      && (skill.extras || []).some((extra) => normalizedSkillName(extra.name) === "+1 order"))
  ));
}

function lieutenantOrderCount(items) {
  const skills = lieutenantSkills(items);
  if (!skills.length) return 0;
  return hasLieutenantPlusOne(items) ? 2 : 1;
}

function characteristicSymbolTypes(profiles) {
  const names = new Set(profiles.flatMap((profile) => (
    (profile.characteristics || []).map((characteristic) => (
      String(characteristic.name || "").toLowerCase()
    ))
  )));
  return [
    ...(names.has("hackable") ? ["hackable"] : []),
    ...(names.has("cube") ? ["cube"] : []),
    ...(names.has("cube 2.0") ? ["cube-2"] : []),
  ];
}

function generalLieutenantOrderCount(profiles, loadouts) {
  if (hasLieutenantPlusOne(profiles)) return 2;
  if (lieutenantSkills(profiles).length) return 1;
  return loadouts.length && loadouts.every((loadout) => lieutenantSkills([loadout]).length)
    ? 1
    : 0;
}

function generalProfileOrderType(profiles, loadouts) {
  if (hasSkill(loadouts, "regular")) return "irregular";
  const orderType = prominentOrderType(loadouts);
  if (orderType) return orderType;
  return [...profiles, ...loadouts].some((item) => (
    (item.skills || []).some((skill) => (
      String(skill.name || "").toLowerCase().startsWith("peripheral")
    ))
  )) ? "peripheral" : null;
}

function nameWithOrderSymbols(nameText, symbolTypes) {
  if (!symbolTypes.length) return nameText;
  const name = document.createElement("span");
  name.className = "order-symbol-name";
  for (const symbolType of symbolTypes) {
    const symbol = document.createElement("img");
    symbol.className = "order-symbol";
    symbol.src = `/static/orders/${symbolType}.svg`;
    symbol.alt = symbolLabels[symbolType];
    symbol.title = symbolLabels[symbolType];
    name.append(symbol);
  }
  name.append(document.createTextNode(nameText));
  return name;
}

function generalProfileName(profile) {
  return nameWithOrderSymbols(profile.profileName, profile.symbolTypes);
}

function profileTitle(profile) {
  const title = document.createElement("h3");
  title.className = "profile-title";
  title.append(generalProfileName(profile));
  return title;
}

function generalProfiles(profiles, loadouts) {
  const byName = new Map();
  for (const profile of profiles) {
    const profileName = baseProfileName(profile.name);
    const profileKey = profileIdentity(profile.name);
    if (!byName.has(profileKey)) byName.set(profileKey, {
      profileName, profiles: [],
    });
    byName.get(profileKey).profiles.push(profile);
  }
  const rows = [];
  const generalByName = new Map();
  for (const { profileName, profiles: matchingProfiles } of byName.values()) {
    const stats = generalStats(matchingProfiles);
    const matchingGroupKeys = new Set(matchingProfiles.map(
      (profile) => `${profile.armyId}:${profile.group_id}`,
    ));
    const matchingLoadouts = loadouts.filter(
      (loadout) => matchingGroupKeys.has(`${loadout.armyId}:${loadout.group_id}`),
    );
    const row = {
      profileName,
      stats,
      orderType: generalProfileOrderType(matchingProfiles, matchingLoadouts),
      type: mostCommon(matchingProfiles, "type"),
      classification: mostCommon(matchingProfiles, "classification"),
      occurrenceCount: matchingProfiles.length,
      reinforcement: matchingProfiles.every((profile) => isReinforcementArmy(profile.armyId)),
      sharedItems: {
        skills: generalProfileSkills(matchingProfiles, matchingLoadouts),
        equipment: commonProfileItems(matchingProfiles, "equipment"),
        weapons: commonProfileItems(matchingLoadouts, "weapons"),
      },
    };
    row.symbolTypes = [
      row.orderType,
      ...(hasSkill([...matchingProfiles, ...matchingLoadouts], "impetuous") ? ["impetuous"] : []),
      ...(hasSkill([...matchingProfiles, ...matchingLoadouts], "tactical awareness") ? ["tactical"] : []),
      ...Array(generalLieutenantOrderCount(matchingProfiles, matchingLoadouts)).fill("lieutenant"),
      ...characteristicSymbolTypes(matchingProfiles),
    ].filter(Boolean);
    rows.push(row);
    for (const profile of matchingProfiles) {
      generalByName.set(profile.name || "", row);
    }
  }
  return { rows, generalByName };
}

function itemIdentity(item) {
  const quantity = item.quantity == null || Number(item.quantity) === 1
    ? null
    : item.quantity;
  return JSON.stringify([
    item.id,
    quantity,
    (item.extras || []).map((extra) => extra.id).sort(),
  ]);
}

function commonProfileItems(profiles, property) {
  if (!profiles.length) return [];
  const shared = new Set();
  return (profiles[0][property] || []).filter((item) => {
    const identity = itemIdentity(item);
    if (shared.has(identity)) return false;
    const appearsEverywhere = profiles.every((profile) => (
      (profile[property] || []).some((candidate) => itemIdentity(candidate) === identity)
    ));
    if (appearsEverywhere) shared.add(identity);
    return appearsEverywhere;
  });
}

function generalProfileSkills(profiles, loadouts) {
  const skills = commonProfileItems(profiles, "skills");
  if (loadouts.length !== 1) return skills;
  for (const skill of loadouts[0].skills || []) {
    if (!skills.some((candidate) => itemIdentity(candidate) === itemIdentity(skill))) {
      skills.push(skill);
    }
  }
  return skills;
}

function withoutSharedItems(items, sharedItems) {
  const sharedIdentities = new Set(sharedItems.map(itemIdentity));
  return items.filter((item) => !sharedIdentities.has(itemIdentity(item)));
}

function visibleGeneralProfiles(rows) {
  return rows.filter((profile) => !rows.some((candidate) => (
    candidate !== profile
    && candidate.profileName === profile.profileName
    && identicalStatline(profile.stats, candidate.stats)
    && (
      (profile.reinforcement && !candidate.reinforcement)
      || (profile.reinforcement === candidate.reinforcement
        && candidate.occurrenceCount > profile.occurrenceCount)
    )
  )));
}

function differsFromGeneral(profile, general, label) {
  if (label.startsWith("MOV")) {
    return profile.move_1 !== general.move_1 || profile.move_2 !== general.move_2;
  }
  return profile[statProperties[label]] !== general[statProperties[label]];
}

function profileItems(items, catalog, fallbackLabel) {
  if (!items.length) return "—";
  const result = document.createDocumentFragment();
  items.forEach((item, index) => {
    const name = item.name || fallbackLabel;
    const hiddenIds = [];
    if (!item.name) hiddenIds.push(`${fallbackLabel} #${text(item.id)}`);
    const extras = (item.extras || []).map((extra) => {
      const extraName = extra.name || "Extra";
      if (!extra.name) hiddenIds.push(`Extra #${text(extra.id)}`);
      if (!extra.is_distance) return extraName;
      return formatDistanceExtra(extraName, {
        showPositiveSign: item.name !== "Super-Jump",
        forcePositiveSign: item.name === "Forward Deployment",
      });
    });
    const decoratedName = extras.length ? `${name} (${extras.join(", ")})` : name;
    const label = item.quantity != null && Number(item.quantity) !== 1
      ? `${decoratedName} ×${item.quantity}`
      : decoratedName;
    const link = document.createElement("a");
    link.href = `/${catalog}/${encodeURIComponent(item.id)}`;
    link.textContent = label;
    if (hiddenIds.length) {
      const details = document.createElement("span");
      details.className = "developer-only";
      details.textContent = ` (${hiddenIds.join(", ")})`;
      link.append(details);
    }
    if (index) result.append(", ");
    result.append(link);
  });
  return result;
}

function generalProfileTableRows(profiles) {
  const rows = [];
  for (const profile of profiles) {
    rows.push(
      [
        { value: "Type", header: true, className: "data-label general-item-label" },
        { value: profile.type, className: "general-item-list" },
      ],
      [
        { value: "Classification", header: true, className: "data-label general-item-label" },
        { value: profile.classification, className: "general-item-list" },
      ],
    );
    rows.push([
      { value: "Attributes", header: true, className: "data-label profile-attributes-label" },
      { content: attributeStatline(profile.stats), className: "profile-attributes" },
    ]);
    for (const [label, property, fallbackLabel] of [
      ["Skills", "skills", "Skill"],
      ["Equipment", "equipment", "Equipment"],
      ["Weapons", "weapons", "Weapon"],
    ]) {
      if (!profile.sharedItems[property].length) continue;
      rows.push([
        { value: label, className: "data-label general-item-label" },
        {
          content: profileItems(profile.sharedItems[property], property, fallbackLabel),
          className: "general-item-list",
        },
      ]);
    }
  }
  return rows;
}

function profileTableRows(profiles, generalByName) {
  return profiles.flatMap((profile) => {
    const generalProfile = generalByName.get(profile.name || "");
    const generalStatsForProfile = generalProfile.stats;
    const sharedItems = generalProfile.sharedItems;
    const profileRow = [{ content: profileNameWithDivisionBadge(profile), header: true, colSpan: 2 }];
    profileRow.className = "profile-summary";
    const rows = [profileRow, [
      { value: "Attributes", header: true, className: "data-label profile-attributes-label" },
      {
        content: attributeStatline(profile, generalStatsForProfile, true),
        className: "profile-attributes",
      },
    ]];
    for (const [label, property, fallbackLabel] of [
      ["Skills", "skills", "Skill"],
      ["Equipment", "equipment", "Equipment"],
      ["Weapons", "weapons", "Weapon"],
    ]) {
      const items = withoutSharedItems(profile[property], sharedItems[property]);
      if (!items.length) continue;
      rows.push([
        { value: label, header: true, className: "data-label profile-item-label" },
        {
          content: profileItems(items, property, fallbackLabel),
          className: "profile-item-list",
        },
      ]);
    }
    return rows;
  });
}

function profileNameWithDivisionBadge(profile) {
  const title = document.createElement("span");
  title.className = "profile-name-with-division";
  title.append(document.createTextNode(text(profile.name)));
  const divisions = new Set((profile.characteristics || []).map((characteristic) => (
    String(characteristic.name || "").toLowerCase()
  )));
  for (const division of ["surface", "deepspace"]) {
    if (!divisions.has(division)) continue;
    const badge = document.createElement("span");
    badge.className = `badge division-badge division-badge-${division}`;
    badge.textContent = division === "surface" ? "Surface" : "Deepspace";
    title.append(badge);
  }
  return title;
}

function loadoutTable(loadouts, sharedItems, generalOrderType) {
  return table(
    ["Name", "Points", "SWC"],
    loadouts.flatMap((loadout, index) => {
      const loadoutOrderType = prominentOrderType([loadout]);
      const symbolTypes = [
        loadoutOrderType && loadoutOrderType !== generalOrderType ? loadoutOrderType : null,
        ...(hasSkill([loadout], "impetuous") ? ["impetuous"] : []),
        ...(hasSkill([loadout], "tactical awareness") ? ["tactical"] : []),
        ...Array(lieutenantOrderCount([loadout])).fill("lieutenant"),
      ].filter(Boolean);
      const loadoutName = nameWithOrderSymbols(loadout.name, symbolTypes);
      const loadoutRow = [{ content: loadoutName }, loadout.points, loadout.swc];
      loadoutRow.className = index ? "profile-summary loadout-start" : "profile-summary";
      const rows = [loadoutRow];
      for (const [label, property, fallbackLabel] of [
        ["Skills", "skills", "Skill"],
        ["Equipment", "equipment", "Equipment"],
        ["Weapons", "weapons", "Weapon"],
      ]) {
        const items = withoutSharedItems(loadout[property], sharedItems[property]);
        if (!items.length) continue;
        rows.push([
          { value: label, header: true, className: "data-label profile-item-label" },
          {
            content: profileItems(items, property, fallbackLabel),
            className: "profile-item-list",
            colSpan: 2,
          },
        ]);
      }
      return rows;
    }),
    "data-table--compact loadout-table",
  );
}

function sharedItemsForProfileGroup(profiles, generalByName) {
  const items = { skills: [], equipment: [], weapons: [] };
  for (const profile of profiles) {
    const sharedItems = generalByName.get(profile.name || "").sharedItems;
    for (const property of Object.keys(items)) {
      for (const item of sharedItems[property]) {
        if (!items[property].some((candidate) => itemIdentity(candidate) === itemIdentity(item))) {
          items[property].push(item);
        }
      }
    }
  }
  return items;
}

function profileLoadoutGroups(army) {
  const groups = new Map();
  for (const profile of army.profiles) {
    if (!groups.has(profile.group_id)) groups.set(profile.group_id, { profiles: [], loadouts: [] });
    groups.get(profile.group_id).profiles.push(profile);
  }
  for (const loadout of army.loadouts) {
    if (!groups.has(loadout.group_id)) groups.set(loadout.group_id, { profiles: [], loadouts: [] });
    groups.get(loadout.group_id).loadouts.push(loadout);
  }
  return [...groups.values()];
}

const availabilityLabels = {
  mercs: "Mercenary",
  specops: "Spec-Ops",
  teamops: "Team Operations",
  reinforcement: "Reinforcements",
};

function availabilityBadges(flags = []) {
  const badges = document.createElement("span");
  badges.className = "availability-badges";
  for (const flag of flags) {
    if (!availabilityLabels[flag]) continue;
    const badge = document.createElement("span");
    badge.className = `badge availability-badge availability-badge-${flag}`;
    badge.textContent = availabilityLabels[flag];
    badges.append(badge);
  }
  return badges;
}

function isStandardArmy(army) {
  const flags = army.availability_flags || [];
  return !flags.includes("mercs")
    && !flags.includes("reinforcement")
    && !isReinforcementArmy(army.id);
}

function isEnabledArmy(army) {
  const filters = optionalUnitFilters();
  return (army.availability_flags || []).every((flag) => filters[flag]);
}

function renderArmyProfile(army, generalByName, expanded) {
  const section = document.createElement("details");
  section.className = "explorer army-profile";
  section.open = expanded;
  const armyHeading = document.createElement("summary");
  armyHeading.className = "data-surface-header army-profile-title";
  armyHeading.textContent = army.name;
  const symbol = armySymbolPath(army.id);
  if (symbol) {
    const icon = document.createElement("img");
    icon.className = "army-symbol army-profile-symbol";
    icon.src = symbol;
    icon.alt = "";
    icon.width = 34;
    icon.height = 34;
    icon.loading = "lazy";
    icon.decoding = "async";
    icon.title = army.name;
    armyHeading.prepend(icon);
  }
  armyHeading.append(availabilityBadges(army.availability_flags));
  section.append(armyHeading);
  for (const group of profileLoadoutGroups(army)) {
    if (group.profiles.length) {
      const profilesHeading = subheading("Profiles");
      profilesHeading.className = "army-profiles-heading";
      section.append(profilesHeading);
      section.append(table(
        [],
        profileTableRows(group.profiles, generalByName),
        "data-table--compact profile-details-table",
      ));
    }
    if (group.loadouts.length) {
      section.append(subheading("Loadouts"));
      section.append(loadoutTable(
        group.loadouts,
        sharedItemsForProfileGroup(group.profiles, generalByName),
        generalByName.get(group.profiles[0]?.name || "")?.orderType,
      ));
    }
  }
  return section;
}

function render(unit) {
  content.replaceChildren();
  document.title = `${unit.name} · InfinityDB`;
  name.textContent = unit.name;
  const icon = unitSymbol(unit.slug || unit.isc || unit.name, "unit-symbol-detail");
  name.prepend(icon);
  const mainArmySymbol = armySymbolPath(unit.main_army_id);
  if (mainArmySymbol) {
    const mainIcon = document.createElement("img");
    mainIcon.className = "army-symbol main-army-symbol main-army-symbol-detail";
    mainIcon.src = mainArmySymbol;
    mainIcon.alt = "";
    mainIcon.width = 48;
    mainIcon.height = 48;
    mainIcon.decoding = "async";
    mainIcon.title = unit.main_army_name
      || unit.armies.find((army) => army.id === unit.main_army_id)?.name
      || "Main army";
    name.prepend(mainIcon);
  }
  const unitMetadata = [
    unit.isc,
    unit.isc_abbr && `(${unit.isc_abbr})`,
  ].filter(Boolean);
  meta.replaceChildren(document.createTextNode(unitMetadata.join(" · ")));
  const unitIds = document.createElement("span");
  unitIds.className = "developer-only";
  unitIds.textContent = `${unitMetadata.length ? " · " : ""}Unit ${unit.source_ids.map((sourceId) => `#${sourceId}`).join(" / ")}`;
  meta.append(unitIds);
  status.hidden = true;
  const armies = unit.armies.filter(isEnabledArmy);
  const allProfiles = armies.flatMap((army) => army.profiles.map((profile) => ({
    ...profile, armyId: army.id,
  })));
  const allLoadouts = armies.flatMap((army) => army.loadouts.map((loadout) => ({
    ...loadout, armyId: army.id,
  })));
  const { rows: generalProfileRows, generalByName } = generalProfiles(allProfiles, allLoadouts);
  const displayedGeneralProfiles = visibleGeneralProfiles(generalProfileRows);
  const generalProfilesSection = document.createElement("section");
  generalProfilesSection.className = "detail-group general-profile-group";
  const mainFaction = factionSlug(unit.main_army_id);
  if (mainFaction) generalProfilesSection.classList.add(`general-profile-group--faction-${mainFaction}`);
  const generalHeading = heading(
    displayedGeneralProfiles.length === 1 ? "General profile" : "General profiles",
  );
  generalHeading.className = "detail-section-title detail-section-title--rule";
  generalProfilesSection.append(generalHeading);
  for (const profile of displayedGeneralProfiles) {
    const generalProfile = document.createElement("section");
    generalProfile.className = "explorer general-profile";
    generalProfile.append(profileTitle(profile), table(
      [],
      generalProfileTableRows([profile]),
      "statline",
    ));
    generalProfilesSection.append(generalProfile);
  }
  content.append(generalProfilesSection);
  let standardArmyExpanded = false;
  for (const group of groupArmiesByFaction(armies)) {
    const section = document.createElement("section");
    section.className = "detail-group faction-profile-group";
    const groupHeading = heading(group.name);
    groupHeading.className = "detail-section-title detail-section-title--rule";
    section.append(groupHeading);
    const profiles = document.createElement("div");
    profiles.className = "detail-group faction-profile-grid";
    for (const army of group.armies) {
      const expanded = !standardArmyExpanded && isStandardArmy(army);
      if (expanded) standardArmyExpanded = true;
      profiles.append(renderArmyProfile(army, generalByName, expanded));
    }
    section.append(profiles);
    content.append(section);
  }
  content.hidden = false;
}

initializeDistanceUnitToggle();

if (!unitId) {
  status.textContent = "The requested unit address is invalid.";
} else {
  getUnit(unitId).then((unit) => {
    render(unit);
    window.addEventListener("distanceunitchange", () => render(unit));
    window.addEventListener("optionalunitschange", () => render(unit));
  }).catch((error) => {
    name.textContent = "Unit unavailable";
    status.textContent = error.message || "Could not load this unit.";
  });
}
