import { distanceUnit } from "./preferences.js";
import { shareStateHref } from "./share-state.js";
import { staticSymbolPath, unitSymbol } from "./unit-symbols.js";
import { formatMovement, formatProfileItem } from "./unit-presentation.js";

function displayArmies(armies) {
  return [...armies].sort((left, right) => left.id - right.id);
}

function text(value) {
  return value == null || value === "" ? "—" : String(value);
}

function unitArmyHref(unit, army) {
  const unitId = unit.public_slug || unit.id;
  const armyId = army.public_slug || army.slug || String(army.id);
  return shareStateHref(`/units/${unitId}`, "unit", { army_id: armyId });
}

function movement(profile) {
  return formatMovement(profile.move_1, profile.move_2, distanceUnit());
}

function statline(profile) {
  const attributes = profile.stats || {};
  const differences = new Set(profile.different_stat_labels || []);
  const stats = [
    ["MOV", movement(attributes)],
    ["CC", text(attributes.cc)],
    ["BS", text(attributes.bs)],
    ["PH", text(attributes.ph)],
    ["WIP", text(attributes.wip)],
    ["ARM", text(attributes.arm)],
    ["BTS", text(attributes.bts)],
    [attributes.is_structure ? "STR" : "VITA", text(attributes.vitality)],
    ["S", text(attributes.silhouette)],
  ];
  const list = document.createElement("dl");
  list.className = "unit-extended-statline";
  for (const [label, value] of stats) {
    const item = document.createElement("div");
    const term = document.createElement("dt");
    term.textContent = label;
    const description = document.createElement("dd");
    const varies = differences.has(label === "STR" ? "VITA" : label);
    description.textContent = value + (varies ? "*" : "");
    if (varies) description.title = "Varies between profile variants";
    item.append(term, description);
    list.append(item);
  }
  return list;
}

function profileAvailability(profile, armiesById) {
  const list = document.createElement("div");
  list.className = "unit-profile-availability";
  list.setAttribute("aria-label", "Army availability for this profile");
  for (const entry of profile.availability || []) {
    const army = armiesById.get(entry.army_id);
    if (!army) continue;
    const item = document.createElement("span");
    item.className = "unit-profile-availability-item";
    const symbol = staticSymbolPath(army.symbol_path);
    if (symbol) {
      const icon = document.createElement("img");
      icon.className = "army-symbol unit-profile-availability-symbol";
      icon.src = symbol;
      icon.alt = "";
      icon.width = 24;
      icon.height = 24;
      icon.loading = "lazy";
      icon.decoding = "async";
      item.append(icon);
    }
    const value = document.createElement("span");
    value.className = "unit-profile-availability-value";
    value.textContent = text(entry.ava).replace(/\btotal\b/g, "Total");
    const availability = entry.ava == null ? "attached profile" : `AVA ${value.textContent}`;
    item.title = `${army.name} — ${availability}`;
    item.append(value);
    list.append(item);
  }
  return list;
}

function capabilityLines(context) {
  const lines = document.createElement("div");
  lines.className = "unit-extended-capabilities";
  for (const [key, label, fallback] of [
    ["skills", "Skills", "Skill"],
    ["equipment", "Equipment", "Equipment"],
    ["weapons", "Weapons", "Weapon"],
  ]) {
    const items = context[key] || [];
    if (!items.length) continue;
    const line = document.createElement("div");
    const heading = document.createElement("strong");
    heading.textContent = label + ": ";
    line.append(heading, items.map((item) => formatProfileItem(item, fallback).label).join(", "));
    lines.append(line);
  }
  return lines;
}

function profileCapabilities(profile) {
  const section = document.createElement("div");
  section.className = "unit-extended-capability-section";
  const heading = document.createElement("strong");
  heading.textContent = "Shared by all variants of this profile";
  section.append(heading);
  const lines = capabilityLines(profile.shared_items || {});
  if (!lines.childElementCount) lines.textContent = "No shared Skills, Equipment or Weapons";
  section.append(lines);
  return section;
}

function extendedProfilesRow(unit, columnCount) {
  const row = document.createElement("tr");
  row.className = "unit-extended-row";
  const cell = document.createElement("td");
  cell.colSpan = columnCount;
  const surface = document.createElement("div");
  surface.className = "unit-extended-profiles";
  const armiesById = new Map((unit.armies || []).map((army) => [army.id, army]));

  for (const profile of unit.general_profiles || []) {
    const profileRow = document.createElement("section");
    profileRow.className = "unit-extended-profile";

    const heading = document.createElement("div");
    heading.className = "unit-extended-profile-heading";
    const title = document.createElement("strong");
    title.textContent = `General profile — ${profile.display_name || unit.name}`;
    const meta = document.createElement("span");
    meta.className = "unit-extended-profile-meta";
    if (profile.type) {
      const troopType = document.createElement("span");
      troopType.className = "unit-profile-troop-type";
      const longType = document.createElement("span");
      longType.className = "unit-profile-troop-type-long";
      longType.textContent = profile.type_label || profile.type;
      const shortType = document.createElement("span");
      shortType.className = "unit-profile-troop-type-short";
      shortType.textContent = profile.type;
      troopType.append(longType, shortType);
      meta.append(troopType);
    }
    if (profile.type && profile.classification) meta.append(" · ");
    if (profile.classification) meta.append(profile.classification);
    if (!meta.childNodes.length) meta.textContent = "—";
    heading.append(title, meta);

    const body = document.createElement("div");
    body.className = "unit-extended-profile-body";
    body.append(statline(profile));

    const characteristics = document.createElement("div");
    characteristics.className = "unit-profile-characteristics";
    characteristics.setAttribute("aria-label", "Characteristics");
    for (const descriptor of profile.symbol_descriptors || []) {
      const symbol = document.createElement("img");
      symbol.className = "unit-profile-characteristic-symbol";
      symbol.src = staticSymbolPath(descriptor.symbol_path);
      symbol.alt = descriptor.label;
      symbol.title = descriptor.label;
      symbol.width = 18;
      symbol.height = 18;
      characteristics.append(symbol);
    }
    body.append(characteristics, profileAvailability(profile, armiesById));
    profileRow.append(heading, body);
    if (profile.different_stat_labels?.length) {
      const note = document.createElement("div");
      note.className = "unit-extended-profile-meta";
      note.textContent = "* Attribute varies between profile variants";
      profileRow.append(note);
    }
    const capabilities = profileCapabilities(profile);
    if (capabilities.childElementCount) profileRow.append(capabilities);
    surface.append(profileRow);
  }

  cell.append(surface);
  row.append(cell);
  return row;
}

function matchDescription(context) {
  const profile = context.profile_name || "";
  const loadout = context.loadout_name || "";
  if (profile.toLocaleLowerCase() === loadout.toLocaleLowerCase()) return profile;
  return [profile, loadout].filter(Boolean).join(" · ");
}

function matchingContexts(unit) {
  const evidence = unit.matching_contexts;
  if (!evidence?.examples?.length) return null;
  const details = document.createElement("details");
  details.className = "unit-match-contexts";
  // The enclosing table row is navigable; this disclosure must remain independent.
  details.addEventListener("click", (event) => event.stopPropagation());
  const summary = document.createElement("summary");
  const sharedName = evidence.total === evidence.examples.length
    && evidence.examples.every((context) => (
      matchDescription(context) === matchDescription(evidence.examples[0])
    ));
  const count = `${evidence.total} `
    + (evidence.total === 1 ? "configuration" : "distinct configurations");
  summary.textContent = sharedName
    ? `Matched: ${matchDescription(evidence.examples[0])} · ${count}`
    : `Matched: ${count}`;
  details.append(summary);
  const list = document.createElement("ul");
  for (const context of evidence.examples) {
    const item = document.createElement("li");
    if (!sharedName) {
      const title = document.createElement("span");
      title.className = "unit-match-context-name";
      title.textContent = matchDescription(context);
      item.append(title);
    }
    const parts = [];
    if (context.points != null) parts.push(`${context.points} pts`);
    if (context.swc != null) parts.push(`${context.swc} SWC`);
    for (const category of ["weapons", "equipment", "skills"]) {
      const names = (context.highlights || [])
        .filter((entry) => entry.category === category)
        .map((entry) => entry.name);
      if (names.length) parts.push(`${category[0].toUpperCase() + category.slice(1)}: ${names.join(", ")}`);
    }
    if (parts.length) {
      const description = document.createElement("span");
      description.className = "unit-match-context-details";
      description.textContent = parts.join(" · ");
      item.append(description);
    }
    list.append(item);
  }
  const remainder = evidence.total - evidence.examples.length;
  if (remainder > 0) {
    const remaining = document.createElement("li");
    remaining.textContent = `${remainder} more matching configurations`;
    list.append(remaining);
  }
  details.append(list);
  return details;
}

/** Render catalog unit records with the shared Unit explorer presentation. */
export function renderUnitRows(container, units, { extended = false } = {}) {
  const fragment = document.createDocumentFragment();
  for (const unit of units) {
    const row = document.createElement("tr");
    row.className = "unit-row";
    const faction = unit.display_faction?.slug;
    if (faction) row.classList.add(`unit-row--faction-${faction}`);
    row.addEventListener("click", (event) => {
      if (!event.target.closest("a, .unit-match-contexts")) {
        const url = `/units/${unit.public_slug || unit.id}`;
        window.infinityNavigate ? window.infinityNavigate(url) : window.location.assign(url);
      }
    });
    const nameCell = document.createElement("th");
    nameCell.scope = "row";
    nameCell.className = "unit-name table-column--primary";
    const nameLink = document.createElement("a");
    nameLink.href = `/units/${unit.public_slug || unit.id}`;
    nameLink.textContent = unit.name;
    const nameContent = document.createElement("span");
    nameContent.className = "unit-name-content";
    const displayArmySymbol = staticSymbolPath(unit.display_army_symbol_path);
    if (!extended && displayArmySymbol) {
      const icon = document.createElement("img");
      icon.className = "army-symbol display-army-symbol";
      icon.src = displayArmySymbol;
      icon.alt = "";
      icon.width = 28;
      icon.height = 28;
      icon.loading = "lazy";
      icon.decoding = "async";
      icon.title = unit.display_army_name
        || unit.armies.find((army) => army.id === unit.display_army_id)?.name
        || "Army symbol";
      nameContent.append(icon);
    }
    nameContent.append(unitSymbol(unit.symbol_path), nameLink);
    nameCell.append(nameContent);
    const matches = matchingContexts(unit);
    if (matches) nameCell.append(matches);
    const armyCell = document.createElement("td");
    armyCell.className = "table-column--descriptor";
    const armyList = document.createElement("div");
    armyList.className = "army-tags";
    const armies = displayArmies(unit.armies);
    if (armies.length > 12) armyList.classList.add("army-tags-compact");
    for (const army of armies) {
      const symbol = staticSymbolPath(army.symbol_path);
      const link = document.createElement("a");
      link.className = "army-availability-link";
      link.href = unitArmyHref(unit, army);
      link.title = `${army.name} — open this Army profile`;
      if (symbol) {
        const icon = document.createElement("img");
        icon.className = "army-symbol";
        icon.src = symbol;
        icon.alt = army.name;
        icon.width = 30;
        icon.height = 30;
        icon.loading = "lazy";
        icon.decoding = "async";
        link.append(icon);
      } else {
        const tag = document.createElement("span");
        tag.className = "army-tag";
        tag.textContent = army.name;
        link.append(tag);
      }
      armyList.append(link);
    }
    if (!unit.armies.length) armyList.textContent = "—";
    armyCell.append(armyList);
    const idCell = document.createElement("td");
    idCell.className = "id-column table-column--technical";
    idCell.textContent = unit.source_ids.map((sourceId) => `#${sourceId}`).join(" / ");
    if (extended) {
      nameCell.colSpan = 2;
      row.append(nameCell, idCell);
    } else {
      row.append(nameCell, armyCell, idCell);
    }
    fragment.append(row);
    if (extended && unit.general_profiles?.length) fragment.append(extendedProfilesRow(unit, 3));
  }
  container.replaceChildren(fragment);
}
