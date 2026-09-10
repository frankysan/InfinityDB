import { getUnit } from "./api.js";
import { armySymbolPath } from "./army-symbols.js";
import { unitSymbol } from "./unit-symbols.js";

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
      armies: group.armies.sort((left, right) => Number(left.id) - Number(right.id)),
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
  for (const row of rows) { const tr = document.createElement("tr"); row.forEach((value) => tr.append(cell(value))); body.append(tr); }
  element.append(head, body);
  return element;
}

function heading(label) { const value = document.createElement("h2"); value.textContent = label; return value; }

function subheading(label) { const value = document.createElement("h4"); value.textContent = label; return value; }

const statColumns = [
  ["MOV (cm)", (profile) => `${text(profile.move_1)}-${text(profile.move_2)}`],
  ["MOV (in)", (profile) => `${inches(profile.move_1)}-${inches(profile.move_2)}`],
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

function identicalStatline(left, right) {
  const rightStatline = generalStatline(right);
  return generalStatline(left).every((value, index) => value === rightStatline[index]);
}

function generalProfiles(profiles) {
  const byName = new Map();
  for (const profile of profiles) {
    const profileName = profile.name || "";
    if (!byName.has(profileName)) byName.set(profileName, []);
    byName.get(profileName).push(profile);
  }
  const rows = [];
  const generalByName = new Map();
  for (const [profileName, matchingProfiles] of byName) {
    const stats = generalStats(matchingProfiles);
    rows.push({
      profileName,
      stats,
      skills: commonProfileItems(matchingProfiles, "skills"),
      equipment: commonProfileItems(matchingProfiles, "equipment"),
      weapons: commonProfileItems(matchingProfiles, "weapons"),
      occurrenceCount: matchingProfiles.length,
      reinforcement: matchingProfiles.every((profile) => isReinforcementArmy(profile.armyId)),
    });
    generalByName.set(profileName, stats);
  }
  return { rows, generalByName };
}

function commonProfileItems(profiles, property) {
  if (!profiles.length) return [];
  return (profiles[0][property] || []).flatMap((item) => {
    const matches = profiles.map((profile) => (
      (profile[property] || []).find((candidate) => candidate.id === item.id)
    ));
    if (matches.some((match) => !match)) return [];
    const quantities = matches.map((match) => match.quantity);
    return [{
      ...item,
      quantity: quantities.every((quantity) => quantity === quantities[0])
        ? quantities[0]
        : null,
    }];
  });
}

function visibleGeneralProfiles(rows) {
  return rows.filter((profile) => !rows.some((candidate) => (
    candidate !== profile
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
    return item.quantity != null && Number(item.quantity) !== 1
      ? `${name} ×${item.quantity}`
      : name;
  }).join(", ");
}

function generalProfileTableRows(profiles) {
  return profiles.flatMap((profile) => {
    const rows = [[profile.profileName, ...generalStatline(profile.stats)]];
    for (const [label, property, fallbackLabel] of [
      ["Skills", "skills", "Skill"],
      ["Equipment", "equipment", "Equipment"],
      ["Weapons", "weapons", "Weapon"],
    ]) {
      if (profile[property].length) {
        rows.push([
          { value: label, className: "general-item-label" },
          {
            value: profileItems(profile[property], fallbackLabel),
            className: "general-item-list",
            colSpan: statColumns.length,
          },
        ]);
      }
    }
    return rows;
  });
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
  section.append(armyHeading);
  section.append(subheading("Profiles"));
  section.append(table(["Name", ...statColumns.map(([label]) => label), "Skills", "Equipment", "Weapons", "AVA"], army.profiles.map((p) => {
    const generalStatsForProfile = generalByName.get(p.name || "");
    return [p.name, ...statColumns.map(([label, read]) => ({
      value: read(p), highlight: differsFromGeneral(p, generalStatsForProfile, label),
    })),
    { value: profileItems(p.skills, "Skill"), className: "profile-item-list" },
    { value: profileItems(p.equipment, "Equipment"), className: "profile-item-list" },
    { value: profileItems(p.weapons, "Weapon"), className: "profile-item-list" },
    p.ava];
  }), "statline"));
  section.append(subheading("Loadouts"));
  section.append(table(
    ["Name", "Points", "SWC", "Minis", "Skills", "Equipment", "Weapons"],
    army.loadouts.map((o) => [
      o.name, o.points, o.swc, o.minis,
      { value: profileItems(o.skills, "Skill"), className: "profile-item-list" },
      { value: profileItems(o.equipment, "Equipment"), className: "profile-item-list" },
      { value: profileItems(o.weapons, "Weapon"), className: "profile-item-list" },
    ]),
  ));
  return section;
}

function render(unit) {
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
  const { rows: generalProfileRows, generalByName } = generalProfiles(allProfiles);
  const general = document.createElement("section");
  general.className = "explorer general-profile";
  general.append(heading("General profile"));
  general.append(table(
    ["Name", ...statColumns.map(([label]) => label)],
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
    for (const army of group.armies) profiles.append(renderArmyProfile(army, generalByName));
    section.append(profiles);
    content.append(section);
  }
  content.hidden = false;
}

if (!unitId) {
  status.textContent = "The requested unit address is invalid.";
} else {
  getUnit(unitId).then(render).catch((error) => {
    name.textContent = "Unit unavailable";
    status.textContent = error.message || "Could not load this unit.";
  });
}
