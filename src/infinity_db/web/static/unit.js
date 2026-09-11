import { getUnit } from "./api.js";
import { armySymbolPath } from "./army-symbols.js";
import { unitSymbol } from "./unit-symbols.js";
import { distanceUnit, formatDistanceExtra, initializeDistanceUnitToggle } from "./preferences.js";

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
  const element = document.createElement("td");
  const structured = value && typeof value === "object";
  const highlighted = structured && "highlight" in value;
  element.textContent = text(structured && "value" in value ? value.value : value);
  if (value && typeof value === "object" && value.className) {
    element.classList.add(value.className);
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

function table(headers, rows, className = "") {
  const element = document.createElement("table");
  element.className = className;
  const head = document.createElement("thead");
  const headerRow = document.createElement("tr");
  for (const header of headers) { const th = document.createElement("th"); th.textContent = header; headerRow.append(th); }
  head.append(headerRow);
  const body = document.createElement("tbody");
  for (const row of rows) {
    const tr = document.createElement("tr");
    if (row.className) tr.className = row.className;
    row.forEach((value, index) => {
      const item = cell(value);
      item.dataset.label = headers[index];
      tr.append(item);
    });
    body.append(tr);
  }
  element.append(head, body);
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

function identicalStatline(left, right) {
  const rightStatline = generalStatline(right);
  return generalStatline(left).every((value, index) => value === rightStatline[index]);
}

function baseProfileName(profileName) {
  return String(profileName || "").replace(/^REINF:\s*/i, "");
}

function generalProfiles(profiles, loadouts) {
  const byName = new Map();
  for (const profile of profiles) {
    const profileName = baseProfileName(profile.name);
    if (!byName.has(profileName)) byName.set(profileName, []);
    byName.get(profileName).push(profile);
  }
  const rows = [];
  const generalByName = new Map();
  for (const [profileName, matchingProfiles] of byName) {
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
      type: mostCommon(matchingProfiles, "type"),
      classification: mostCommon(matchingProfiles, "classification"),
      occurrenceCount: matchingProfiles.length,
      reinforcement: matchingProfiles.every((profile) => isReinforcementArmy(profile.armyId)),
      sharedItems: {
        skills: commonProfileItems(matchingProfiles, "skills"),
        equipment: commonProfileItems(matchingProfiles, "equipment"),
        weapons: commonProfileItems(matchingLoadouts, "weapons"),
      },
    };
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

function profileItems(items, fallbackLabel) {
  if (!items.length) return "—";
  return items.map((item) => {
    const name = item.name || `${fallbackLabel} #${text(item.id)}`;
    const extras = (item.extras || []).map((extra) => {
      const extraName = extra.name || `Extra #${text(extra.id)}`;
      if (!extra.is_distance) return extraName;
      return formatDistanceExtra(extraName, {
        showPositiveSign: item.name !== "Super-Jump",
        forcePositiveSign: item.name === "Forward Deployment",
      });
    });
    const decoratedName = extras.length ? `${name} (${extras.join(", ")})` : name;
    return item.quantity != null && Number(item.quantity) !== 1
      ? `${decoratedName} ×${item.quantity}`
      : decoratedName;
  }).join(", ");
}

function generalProfileTableRows(profiles) {
  const rows = [];
  for (const profile of profiles) {
    const statline = [
      profile.profileName,
      profile.type,
      profile.classification,
      ...generalStatline(profile.stats).map(displayStatlineValue),
    ];
    statline.className = "profile-statline";
    rows.push(statline);
    for (const [label, property, fallbackLabel] of [
      ["Skills", "skills", "Skill"],
      ["Equipment", "equipment", "Equipment"],
      ["Weapons", "weapons", "Weapon"],
    ]) {
      if (!profile.sharedItems[property].length) continue;
      rows.push([
        { value: label, className: "general-item-label" },
        {
          value: profileItems(profile.sharedItems[property], fallbackLabel),
          className: "general-item-list",
          colSpan: statColumns.length,
        },
      ]);
    }
  }
  return rows;
}

function profileTableRows(profiles, generalByName) {
  return profiles.map((profile) => {
    const generalProfile = generalByName.get(profile.name || "");
    const generalStatsForProfile = generalProfile.stats;
    const sharedItems = generalProfile.sharedItems;
    const statline = [profile.name, ...statColumns.map(([label, read]) => ({
      value: displayStatlineValue(read(profile)),
      highlight: differsFromGeneral(profile, generalStatsForProfile, label),
    })),
    { value: profileItems(withoutSharedItems(profile.skills, sharedItems.skills), "Skill"), className: "profile-item-list" },
    { value: profileItems(withoutSharedItems(profile.equipment, sharedItems.equipment), "Equipment"), className: "profile-item-list" },
    { value: profileItems(withoutSharedItems(profile.weapons, sharedItems.weapons), "Weapon"), className: "profile-item-list" },
    displayStatlineValue(profile.ava)];
    statline.className = "profile-statline";
    return statline;
  });
}

function loadoutTable(loadouts, sharedItems) {
  return table(
    ["Name", "Points", "SWC", "Minis", "Skills", "Equipment", "Weapons"],
    loadouts.map((loadout) => [
      loadout.name, loadout.points, loadout.swc, loadout.minis,
      { value: profileItems(withoutSharedItems(loadout.skills, sharedItems.skills), "Skill"), className: "profile-item-list" },
      { value: profileItems(withoutSharedItems(loadout.equipment, sharedItems.equipment), "Equipment"), className: "profile-item-list" },
      { value: profileItems(withoutSharedItems(loadout.weapons, sharedItems.weapons), "Weapon"), className: "profile-item-list" },
    ]),
    "loadout-table",
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
};

function availabilityBadges(flags = []) {
  const badges = document.createElement("span");
  badges.className = "availability-badges";
  for (const flag of flags) {
    if (!availabilityLabels[flag]) continue;
    const badge = document.createElement("span");
    badge.className = `availability-badge availability-badge-${flag}`;
    badge.textContent = availabilityLabels[flag];
    badges.append(badge);
  }
  return badges;
}

function renderArmyProfile(army, generalByName) {
  const section = document.createElement("section");
  section.className = "explorer army-profile";
  const armyHeading = document.createElement("h3");
  armyHeading.className = "army-profile-title";
  armyHeading.textContent = army.name;
  const symbol = armySymbolPath(army.id);
  if (symbol) {
    const icon = document.createElement("img");
    icon.className = "army-symbol army-profile-symbol";
    icon.src = symbol;
    icon.alt = "";
    icon.title = army.name;
    armyHeading.prepend(icon);
  }
  armyHeading.append(availabilityBadges(army.availability_flags));
  section.append(armyHeading);
  for (const group of profileLoadoutGroups(army)) {
    if (group.profiles.length) {
      section.append(subheading("Profiles"));
      section.append(table(
        ["Name", ...statColumns.map(([label]) => label), "Skills", "Equipment", "Weapons", "AVA"],
        profileTableRows(group.profiles, generalByName),
        "statline",
      ));
    }
    if (group.loadouts.length) {
      section.append(subheading("Loadouts"));
      section.append(loadoutTable(
        group.loadouts,
        sharedItemsForProfileGroup(group.profiles, generalByName),
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
    mainIcon.title = "Main army";
    name.prepend(mainIcon);
  }
  meta.textContent = [
    unit.isc,
    unit.isc_abbr && `(${unit.isc_abbr})`,
    `Unit ${unit.source_ids.map((sourceId) => `#${sourceId}`).join(" / ")}`,
  ].filter(Boolean).join(" · ");
  status.hidden = true;
  const allProfiles = unit.armies.flatMap((army) => army.profiles.map((profile) => ({
    ...profile, armyId: army.id,
  })));
  const allLoadouts = unit.armies.flatMap((army) => army.loadouts.map((loadout) => ({
    ...loadout, armyId: army.id,
  })));
  const { rows: generalProfileRows, generalByName } = generalProfiles(allProfiles, allLoadouts);
  const general = document.createElement("section");
  general.className = "explorer general-profile";
  general.append(heading("General profile"));
  general.append(table(
    ["Name", "Type", "Classification", ...statColumns.map(([label]) => label)],
    generalProfileTableRows(visibleGeneralProfiles(generalProfileRows)),
    "statline",
  ));
  content.append(general);
  for (const group of groupArmiesByFaction(unit.armies)) {
    const section = document.createElement("section");
    section.className = "faction-profile-group";
    const groupHeading = heading(group.name);
    groupHeading.className = "faction-profile-group-title";
    section.append(groupHeading);
    const profiles = document.createElement("div");
    profiles.className = "faction-profile-grid";
    for (const army of group.armies) profiles.append(
      renderArmyProfile(army, generalByName),
    );
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
  }).catch((error) => {
    name.textContent = "Unit unavailable";
    status.textContent = error.message || "Could not load this unit.";
  });
}
