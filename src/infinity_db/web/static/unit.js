import { getUnit } from "./api.js";
import { armySymbolPath } from "./army-symbols.js";
import { unitProfileSymbolPath } from "./unit-symbols.js";
import { distanceUnit, formatSkillDistanceExtra, initializeDistanceUnitToggle, optionalUnitFilters } from "./preferences.js";

const name = document.getElementById("unit-name");
const meta = document.getElementById("unit-meta");
const status = document.getElementById("unit-status");
const content = document.getElementById("unit-content");
const unitIdentifier = /^\/units\/([a-z0-9]+(?:-[a-z0-9]+)*)$/.exec(window.location.pathname)?.[1];

function text(value) { return value == null || value === "" ? "—" : String(value); }

const troopTypeLabels = {
  LI: "Light Infantry",
  MI: "Medium Infantry",
  HI: "Heavy Infantry",
  REM: "Remote",
  TAG: "Tactical Armored Gear",
  WB: "Warband",
  SK: "Skirmisher",
  VH: "Vehicle",
};

function troopTypeLabel(value) {
  return troopTypeLabels[value] || value;
}

function groupArmiesByFaction(armies) {
  const groups = new Map();
  for (const army of armies) {
    const faction = army.faction;
    const key = faction?.id ?? "other";
    if (!groups.has(key)) groups.set(key, {
      key,
      name: faction?.name || "Other armies",
      order: faction?.id ?? Number.MAX_SAFE_INTEGER,
      armies: [],
    });
    groups.get(key).armies.push(army);
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
    attributeLabel.textContent = statLabel(label, stats);
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
  ["VITA", (profile) => profile.vitality], ["S", (profile) => profile.silhouette],
];

const statProperties = {
  CC: "cc", BS: "bs", PH: "ph", WIP: "wip", ARM: "arm", BTS: "bts",
  VITA: "vitality", S: "silhouette",
};

function isStructureProfile(profile) {
  return profile.is_structure === true || Number(profile.is_structure) === 1;
}

function statLabel(label, profile) {
  return label === "VITA" && isStructureProfile(profile) ? "STR" : label;
}

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
    is_structure: mostCommon(profiles, "is_structure"),
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
  if (isStructureProfile(left) !== isStructureProfile(right)) return false;
  const rightStatline = generalStatline(right);
  return generalStatline(left).every((value, index) => value === rightStatline[index]);
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

const symbolCategories = {
  regular: "orders",
  irregular: "orders",
  peripheral: "characteristics",
  impetuous: "orders",
  tactical: "orders",
  lieutenant: "orders",
  hackable: "characteristics",
  cube: "characteristics",
  "cube-2": "characteristics",
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
  const characteristics = new Map();
  for (const profile of profiles) {
    for (const characteristic of profile.characteristics || []) {
      const name = String(characteristic.name || "").toLowerCase();
      if (name && !characteristics.has(name)) characteristics.set(name, characteristic);
    }
  }
  const symbol = (name, type) => {
    const characteristic = characteristics.get(name);
    if (!characteristic) return null;
    const slug = characteristic.equipment_reference?.slug;
    return slug ? { type, href: `/equipment/${encodeURIComponent(slug)}` } : type;
  };
  return [
    symbol("hackable", "hackable"),
    symbol("cube", "cube"),
    symbol("cube 2.0", "cube-2"),
  ].filter(Boolean);
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
  for (const descriptor of symbolTypes) {
    const symbolType = typeof descriptor === "string" ? descriptor : descriptor.type;
    const symbol = document.createElement("img");
    symbol.className = "order-symbol";
    symbol.src = `/static/${symbolCategories[symbolType]}/${symbolType}.svg`;
    symbol.alt = descriptor.href ? "" : symbolLabels[symbolType];
    symbol.title = symbolLabels[symbolType];
    if (descriptor.href) {
      const link = document.createElement("a");
      link.className = "profile-symbol-link";
      link.href = descriptor.href;
      link.setAttribute("aria-label", `${symbolLabels[symbolType]} equipment`);
      link.append(symbol);
      name.append(link);
    } else {
      name.append(symbol);
    }
  }
  name.append(document.createTextNode(nameText));
  return name;
}

function generalProfileName(profile) {
  return nameWithOrderSymbols(profile.profileName, profile.symbolTypes);
}

function profileTitle(profile, profileSymbols = null) {
  const title = document.createElement("h3");
  title.className = "profile-title";
  const name = document.createElement("span");
  name.className = "profile-title-name";
  name.append(generalProfileName(profile));
  title.append(name);
  if (profileSymbols) title.append(profileSymbols);
  return title;
}

function generalProfileSymbols(profile, unitName) {
  const paths = new Set();
  const profileLogos = profile.logoUrls.length ? profile.logoUrls : [null];
  for (const profileLogo of profileLogos) {
    const path = unitProfileSymbolPath(profileLogo, unitName);
    if (path) paths.add(path);
  }
  if (!paths.size) return null;

  const symbols = document.createElement("div");
  symbols.className = "general-profile-symbols";
  symbols.setAttribute("aria-hidden", "true");
  for (const path of paths) {
    const icon = document.createElement("img");
    icon.className = "unit-symbol general-profile-unit-symbol";
    icon.src = path;
    icon.alt = "";
    icon.width = 56;
    icon.height = 56;
    icon.loading = "lazy";
    icon.decoding = "async";
    icon.addEventListener("error", () => icon.remove(), { once: true });
    symbols.append(icon);
  }
  return symbols;
}

function generalProfiles(profiles, loadouts) {
  const byName = new Map();
  for (const profile of profiles) {
    const profileName = String(profile.display_name || profile.name || "").trim();
    const profileKey = profile.profile_identity;
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
      reinforcement: matchingProfiles.every((profile) => profile.reinforcement),
      logoUrls: [...new Set(matchingProfiles.flatMap((profile) => profile.logo_urls || []))],
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
  if (label === "VITA" && isStructureProfile(profile) !== isStructureProfile(general)) {
    return true;
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
      return formatSkillDistanceExtra(extraName, item.parameter_semantics);
    });
    const decoratedName = extras.length ? `${name} (${extras.join(", ")})` : name;
    const label = item.quantity != null && Number(item.quantity) !== 1
      ? `${decoratedName} ×${item.quantity}`
      : decoratedName;
    const link = document.createElement("a");
    const routeId = item.slug || item.id;
    link.href = `/${catalog}/${encodeURIComponent(routeId)}`;
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

const peripheralTypeLabels = {
  "rule:peripheral-type:servant": "Servant",
  "rule:peripheral-type:synchronized": "Synchronized",
  "rule:peripheral-type:control": "Control",
  "rule:peripheral-type:ancillary": "Ancillary",
  "rule:peripheral-type:cyberplug": "Cyberplug",
};

function peripheralTypeLabel(typeId) {
  return peripheralTypeLabels[typeId] || String(typeId || "Peripheral").split(":").at(-1);
}

function unitLink(unit) {
  const link = document.createElement("a");
  const routeId = unit.slug || unit.id;
  link.href = `/units/${encodeURIComponent(routeId)}`;
  link.textContent = unit.name || `Unit #${text(unit.id)}`;
  return link;
}

function loadoutAnchorId(anchorScope, payloadId) {
  return `loadout-${anchorScope}-${payloadId}`;
}

function includeTargetLink(target, anchorScope) {
  const link = document.createElement("a");
  link.href = `#${loadoutAnchorId(anchorScope, target.loadout_payload_id)}`;
  const quantity = target.quantity != null && Number(target.quantity) !== 1
    ? ` ×${target.quantity}`
    : "";
  link.textContent = `${target.name || "Loadout"}${quantity}`;
  link.addEventListener("click", () => {
    const targetElement = document.getElementById(
      loadoutAnchorId(anchorScope, target.loadout_payload_id),
    );
    const details = targetElement?.closest("details");
    if (details) details.open = true;
  });
  return link;
}

function includeItems(items, anchorScope) {
  const result = document.createDocumentFragment();
  items.forEach((item, index) => {
    if (index) result.append(", ");
    result.append(includeTargetLink(item, anchorScope));
  });
  return result;
}

function appendIncludeRows(rows, item, anchorScope, colSpan = null) {
  if (!(item.includes || []).length) return;
  rows.push([
    { value: "Includes", header: true, className: "data-label profile-item-label" },
    {
      content: includeItems(item.includes, anchorScope),
      className: "profile-item-list",
      ...(colSpan ? { colSpan } : {}),
    },
  ]);
}

function peripheralItems(items) {
  const result = document.createDocumentFragment();
  items.forEach((item, index) => {
    const quantity = item.quantity != null && Number(item.quantity) !== 1
      ? ` ×${item.quantity}`
      : "";
    const label = `${item.name || "Peripheral"}${quantity} (${peripheralTypeLabel(item.type_id)})`;
    if (index) result.append(", ");
    result.append(document.createTextNode(label));
  });
  return result;
}

function peripheralAccessItems(accessItems) {
  const result = document.createDocumentFragment();
  accessItems.forEach((access, accessIndex) => {
    if (accessIndex) result.append("; ");
    const group = document.createElement("span");
    if (access.relationship === "access-pool") {
      group.title = "Access pool; this does not assign fixed Controller ownership.";
    }
    group.append(`${peripheralTypeLabel(access.type_id)}: `);
    (access.targets || []).forEach((target, targetIndex) => {
      if (targetIndex) group.append(", ");
      group.append(unitLink(target));
    });
    result.append(group);
  });
  return result;
}

function appendPeripheralRows(rows, item, colSpan = null) {
  if ((item.peripherals || []).length) {
    rows.push([
      { value: "Peripherals", header: true, className: "data-label profile-item-label" },
      {
        content: peripheralItems(item.peripherals),
        className: "profile-item-list",
        ...(colSpan ? { colSpan } : {}),
      },
    ]);
  }
  if ((item.peripheral_access || []).length) {
    rows.push([
      { value: "Controller access", header: true, className: "data-label profile-item-label" },
      {
        content: peripheralAccessItems(item.peripheral_access),
        className: "profile-item-list",
        ...(colSpan ? { colSpan } : {}),
      },
    ]);
  }
}

function profileGroupAnchorId(anchorScope, groupId) {
  return `profile-group-${anchorScope}-${groupId}`;
}

function profileGroupLabel(army, groupId) {
  const names = [];
  const addName = (value) => {
    if (value && !names.includes(value)) names.push(value);
  };
  for (const profile of army?.profiles || []) {
    if (Number(profile.group_id) === Number(groupId)) {
      addName(profile.display_name || profile.name);
    }
  }
  if (!names.length) {
    for (const loadout of army?.loadouts || []) {
      if (Number(loadout.group_id) === Number(groupId)) addName(loadout.name);
    }
  }
  return names.length ? names.join(" / ") : `Profile group ${groupId}`;
}

function openRelationshipTarget(link, targetId) {
  link.addEventListener("click", () => {
    const target = document.getElementById(targetId);
    const details = target?.closest("details");
    if (details) details.open = true;
  });
}

function profileGroupLink(army, groupId) {
  const label = profileGroupLabel(army, groupId);
  if (!army) return document.createTextNode(label);
  const anchorScope = [army.id, ...(army.availability_flags || [])].join("-");
  const targetId = profileGroupAnchorId(anchorScope, groupId);
  const link = document.createElement("a");
  link.href = `#${targetId}`;
  link.textContent = label;
  openRelationshipTarget(link, targetId);
  return link;
}

function dependencyOptionLinks(army, target) {
  const optionIds = new Set((target.options || []).map(Number));
  if (!army || !optionIds.size) return null;
  const loadouts = (army.loadouts || []).filter((loadout) => (
    Number(loadout.group_id) === Number(target.group_id)
      && optionIds.has(Number(loadout.option_id))
  ));
  if (!loadouts.length) return null;
  const result = document.createDocumentFragment();
  const anchorScope = [army.id, ...(army.availability_flags || [])].join("-");
  loadouts.forEach((loadout, index) => {
    if (index) result.append(", ");
    const payloadId = (loadout.loadout_payload_ids || [])[0];
    if (payloadId == null) {
      result.append(document.createTextNode(loadout.name || `Option ${loadout.option_id}`));
      return;
    }
    result.append(includeTargetLink({
      loadout_payload_id: payloadId,
      name: loadout.name || `Option ${loadout.option_id}`,
    }, anchorScope));
  });
  return result;
}

function selectionInstruction(minCount, maxCount) {
  const minimum = minCount == null ? null : Number(minCount);
  const maximum = maxCount == null ? null : Number(maxCount);
  if (minimum != null && maximum != null && minimum === maximum) {
    return `Select exactly ${minimum}`;
  }
  if (minimum != null && maximum != null) return `Select ${minimum}–${maximum}`;
  if (maximum != null) return `Select at most ${maximum}`;
  if (minimum != null && minimum > 0) return `Select at least ${minimum}`;
  return "Selection applies";
}

function uniqueConstraintMembers(members) {
  const unique = new Map();
  for (const member of members || []) {
    if (!unique.has(member.logical_unit_id)) unique.set(member.logical_unit_id, member);
  }
  return [...unique.values()];
}

function appendUnitLinks(parent, members) {
  members.forEach((member, index) => {
    if (index) parent.append(index === members.length - 1 ? " and " : ", ");
    parent.append(unitLink({
      id: member.logical_unit_id,
      slug: member.slug,
      name: member.name,
    }));
  });
}

function sourceDependencyParameters(relation, member, target) {
  const values = [];
  if (relation.min_count != null) values.push(`relation min ${relation.min_count}`);
  if (relation.max_count != null) values.push(`relation max ${relation.max_count}`);
  if (member.per_parent != null) values.push(`perParent ${text(member.per_parent)}`);
  if (target.source_group_selector != null) {
    values.push(`group selector ${target.source_group_selector}`);
  }
  if (target.min_count != null) values.push(`dependency min ${target.min_count}`);
  if (target.min_dependant != null) values.push(`minDependant ${target.min_dependant}`);
  return values;
}

function appendRelationProvenance(item, relation) {
  const provenance = document.createElement("span");
  provenance.className = "developer-only";
  provenance.textContent = ` · Army relation #${relation.relation_id}`;
  item.append(provenance);
}

function renderSelectionRelationships(unit, armies) {
  const visibleArmyIds = new Set(armies.map((army) => Number(army.id)));
  const constraints = (unit.selection_constraints || []).filter((relation) => (
    visibleArmyIds.has(Number(relation.army_id))
  ));
  const dependencies = (unit.group_dependencies || []).filter((relation) => (
    visibleArmyIds.has(Number(relation.army_id))
  ));
  if (!constraints.length && !dependencies.length) return null;

  const section = document.createElement("section");
  section.className = "detail-group selection-relationships";
  const title = heading("Selection relationships");
  title.className = "detail-section-title detail-section-title--rule";
  section.append(title);

  const surface = document.createElement("div");
  surface.className = "explorer connected-unit-surface selection-relationship-surface";
  const intro = document.createElement("p");
  intro.className = "selection-relationship-intro";
  intro.textContent = "These source-defined relationships explain linked choices only; "
    + "InfinityDB does not validate complete Army Lists.";
  surface.append(intro);

  if (constraints.length) {
    surface.append(subheading("Selection constraints"));
    const list = document.createElement("ul");
    list.className = "detail-list connected-unit-list";
    for (const relation of constraints) {
      const item = document.createElement("li");
      const army = armies.find((candidate) => Number(candidate.id) === Number(relation.army_id));
      const armyName = army?.name || `Army ${relation.army_id}`;
      const context = document.createElement("strong");
      context.textContent = `${armyName}: `;
      item.append(context);
      const members = uniqueConstraintMembers(relation.members);
      if (relation.family === "same-logical-cross-context-exclusive") {
        item.append("Select exactly 1 occurrence of ");
        appendUnitLinks(item, members);
        item.append(" across its linked selection contexts.");
      } else if (relation.family === "cross-logical-shared-cardinality") {
        item.append(`${selectionInstruction(relation.min_count, relation.max_count)} total from `);
        appendUnitLinks(item, members);
        item.append(".");
      } else if (relation.family === "single-logical-cardinality") {
        item.append(`${selectionInstruction(relation.min_count, relation.max_count)} of `);
        appendUnitLinks(item, members);
        item.append(".");
      } else {
        item.append(`${selectionInstruction(relation.min_count, relation.max_count)} across `);
        appendUnitLinks(item, members);
        item.append(".");
      }
      appendRelationProvenance(item, relation);
      list.append(item);
    }
    surface.append(list);
  }

  if (dependencies.length) {
    surface.append(subheading("Profile-group dependencies"));
    const explanation = document.createElement("p");
    explanation.className = "selection-relationship-note";
    explanation.textContent = "Dependency direction is normalized; source selector parameters are shown "
      + "verbatim where InfinityDB does not yet assign broader list-building semantics.";
    surface.append(explanation);
    const list = document.createElement("ul");
    list.className = "detail-list connected-unit-list";
    for (const relation of dependencies) {
      const army = armies.find((candidate) => Number(candidate.id) === Number(relation.army_id));
      const armyName = army?.name || `Army ${relation.army_id}`;
      for (const member of relation.members || []) {
        for (const target of member.dependencies || []) {
          const item = document.createElement("li");
          const context = document.createElement("strong");
          context.textContent = `${armyName}: `;
          item.append(context, profileGroupLink(army, member.group_id), " depends on ",
            profileGroupLink(army, target.group_id));
          const optionLinks = dependencyOptionLinks(army, target);
          if (optionLinks) item.append(" for ", optionLinks);
          item.append(".");
          const parameters = sourceDependencyParameters(relation, member, target);
          if (parameters.length) {
            const sourceParameters = document.createElement("span");
            sourceParameters.className = "selection-source-parameters";
            sourceParameters.textContent = ` Source parameters: ${parameters.join(" · ")}.`;
            item.append(sourceParameters);
          }
          appendRelationProvenance(item, relation);
          list.append(item);
        }
      }
    }
    surface.append(list);
  }

  section.append(surface);
  return section;
}

function renderPeripheralRelationships(unit) {
  const typeIds = unit.peripheral_type_ids || [];
  const controllers = unit.peripheral_controllers || [];
  if (!typeIds.length && !controllers.length) return null;

  const section = document.createElement("section");
  section.className = "detail-group peripheral-relationships";
  const title = heading("Peripheral relationships");
  title.className = "detail-section-title detail-section-title--rule";
  section.append(title);

  const surface = document.createElement("div");
  surface.className = "explorer connected-unit-surface";
  if (typeIds.length) {
    const type = document.createElement("p");
    type.className = "connected-unit-type";
    const label = typeIds.map(peripheralTypeLabel).join(", ");
    type.textContent = `Peripheral type: ${label}`;
    surface.append(type);
  }
  if (controllers.length) {
    surface.append(subheading("Controllers"));
    const list = document.createElement("ul");
    list.className = "detail-list connected-unit-list";
    for (const access of controllers) {
      const item = document.createElement("li");
      item.append(unitLink(access.controller));
      const context = [
        access.army?.name,
        access.controller_option_name
          ? `${access.controller_kind === "profile" ? "Profile" : "Loadout"}: ${access.controller_option_name}`
          : null,
      ].filter(Boolean);
      if (context.length) {
        const detail = document.createElement("span");
        detail.className = "connected-unit-context";
        detail.textContent = ` — ${context.join(" · ")}`;
        item.append(detail);
      }
      if (access.relationship === "access-pool") {
        item.title = "This Controller can select this Peripheral from its access pool; no fixed ownership is implied.";
      }
      list.append(item);
    }
    surface.append(list);
  }
  section.append(surface);
  return section;
}

function generalProfileTableRows(profiles) {
  const rows = [];
  for (const profile of profiles) {
    rows.push(
      [
        { value: "Type", header: true, className: "data-label general-item-label" },
        { value: troopTypeLabel(profile.type), className: "general-item-list" },
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

function profileTableRows(profiles, generalByName, anchorScope) {
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
    appendIncludeRows(rows, profile, anchorScope);
    appendPeripheralRows(rows, profile);
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

function loadoutTable(loadouts, sharedItems, generalOrderType, anchorScope, anchoredPayloads) {
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
      const loadoutName = document.createDocumentFragment();
      for (const payloadId of loadout.loadout_payload_ids || []) {
        if (anchoredPayloads.has(payloadId)) continue;
        anchoredPayloads.add(payloadId);
        const anchor = document.createElement("span");
        anchor.id = loadoutAnchorId(anchorScope, payloadId);
        anchor.className = "loadout-anchor";
        anchor.setAttribute("aria-hidden", "true");
        loadoutName.append(anchor);
      }
      loadoutName.append(nameWithOrderSymbols(loadout.name, symbolTypes));
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
      appendIncludeRows(rows, loadout, anchorScope, 2);
      appendPeripheralRows(rows, loadout, 2);
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
    if (!groups.has(profile.group_id)) {
      groups.set(profile.group_id, { id: profile.group_id, profiles: [], loadouts: [] });
    }
    groups.get(profile.group_id).profiles.push(profile);
  }
  for (const loadout of army.loadouts) {
    if (!groups.has(loadout.group_id)) {
      groups.set(loadout.group_id, { id: loadout.group_id, profiles: [], loadouts: [] });
    }
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
  return !flags.includes("mercs") && !flags.includes("reinforcement");
}

function isEnabledArmy(army) {
  const filters = optionalUnitFilters();
  return (army.availability_flags || []).every((flag) => filters[flag]);
}

function unitOptionIncludeTable(options, anchorScope) {
  return table(
    ["Option", "Includes"],
    options.map((option) => {
      const optionName = document.createDocumentFragment();
      optionName.append(document.createTextNode(text(option.name)));
      const sourceId = document.createElement("span");
      sourceId.className = "developer-only";
      sourceId.textContent = ` (Unit #${option.source_unit_id}, option #${option.option_id})`;
      optionName.append(sourceId);
      return [
        { content: optionName },
        {
          content: includeItems(option.includes || [], anchorScope),
          className: "profile-item-list",
        },
      ];
    }),
    "data-table--compact unit-option-includes-table",
  );
}

function renderArmyProfile(army, generalByName, expanded) {
  const section = document.createElement("details");
  const anchorScope = [army.id, ...(army.availability_flags || [])].join("-");
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
  if ((army.unit_option_includes || []).length) {
    section.append(subheading("Included loadouts"));
    section.append(unitOptionIncludeTable(army.unit_option_includes, anchorScope));
  }
  const anchoredPayloads = new Set();
  for (const group of profileLoadoutGroups(army)) {
    const groupAnchor = profileGroupAnchorId(anchorScope, group.id);
    let groupAnchored = false;
    if (group.profiles.length) {
      const profilesHeading = subheading("Profiles");
      profilesHeading.className = "army-profiles-heading";
      profilesHeading.id = groupAnchor;
      groupAnchored = true;
      section.append(profilesHeading);
      section.append(table(
        [],
        profileTableRows(group.profiles, generalByName, anchorScope),
        "data-table--compact profile-details-table",
      ));
    }
    if (group.loadouts.length) {
      const loadoutsHeading = subheading("Loadouts");
      if (!groupAnchored) loadoutsHeading.id = groupAnchor;
      section.append(loadoutsHeading);
      section.append(loadoutTable(
        group.loadouts,
        sharedItemsForProfileGroup(group.profiles, generalByName),
        generalByName.get(group.profiles[0]?.name || "")?.orderType,
        anchorScope,
        anchoredPayloads,
      ));
    }
  }
  return section;
}

function render(unit) {
  content.replaceChildren();
  document.title = `${unit.name} · InfinityDB`;
  name.textContent = unit.name;
  const displayArmySymbol = armySymbolPath(unit.display_army_id);
  if (displayArmySymbol) {
    const displayIcon = document.createElement("img");
    displayIcon.className = "army-symbol display-army-symbol display-army-symbol-detail";
    displayIcon.src = displayArmySymbol;
    displayIcon.alt = "";
    displayIcon.width = 48;
    displayIcon.height = 48;
    displayIcon.decoding = "async";
    displayIcon.title = unit.display_army_name
      || unit.armies.find((army) => army.id === unit.display_army_id)?.name
      || "Army symbol";
    name.prepend(displayIcon);
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
    ...profile,
    armyId: army.id,
    reinforcement: (army.availability_flags || []).includes("reinforcement"),
  })));
  const allLoadouts = armies.flatMap((army) => army.loadouts.map((loadout) => ({
    ...loadout, armyId: army.id,
  })));
  const { rows: generalProfileRows, generalByName } = generalProfiles(allProfiles, allLoadouts);
  const displayedGeneralProfiles = visibleGeneralProfiles(generalProfileRows);
  const generalProfilesSection = document.createElement("section");
  generalProfilesSection.className = "detail-group general-profile-group";
  const displayFaction = unit.display_faction?.slug;
  if (displayFaction) {
    generalProfilesSection.classList.add(`general-profile-group--faction-${displayFaction}`);
  }
  const generalHeading = heading(
    displayedGeneralProfiles.length === 1 ? "General profile" : "General profiles",
  );
  generalHeading.className = "detail-section-title detail-section-title--rule";
  generalProfilesSection.append(generalHeading);
  for (const profile of displayedGeneralProfiles) {
    const generalProfile = document.createElement("section");
    generalProfile.className = "explorer general-profile";
    const profileSymbols = generalProfileSymbols(
      profile, unit.slug || unit.isc || unit.name,
    );
    generalProfile.append(profileTitle(profile, profileSymbols), table(
      [],
      generalProfileTableRows([profile]),
      "statline",
    ));
    generalProfilesSection.append(generalProfile);
  }
  content.append(generalProfilesSection);
  const peripheralRelationships = renderPeripheralRelationships(unit);
  if (peripheralRelationships) content.append(peripheralRelationships);
  const selectionRelationships = renderSelectionRelationships(unit, armies);
  if (selectionRelationships) content.append(selectionRelationships);
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

if (!unitIdentifier) {
  status.textContent = "The requested unit address is invalid.";
} else {
  getUnit(unitIdentifier).then((unit) => {
    render(unit);
    window.addEventListener("distanceunitchange", () => render(unit));
    window.addEventListener("optionalunitschange", () => render(unit));
  }).catch((error) => {
    name.textContent = "Unit unavailable";
    status.textContent = error.message || "Could not load this unit.";
  });
}
