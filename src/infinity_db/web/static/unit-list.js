import { distanceUnit } from "./preferences.js";
import { shareStateHref } from "./share-state.js";
import { staticSymbolPath, unitSymbol } from "./unit-symbols.js";
import {
  characteristicSymbol,
  developerOnlyCharacteristic,
  formatMovement,
  troopTypeLabel,
} from "./unit-presentation.js";

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
  const stats = [
    ["MOV", movement(profile)],
    ["CC", text(profile.cc)],
    ["BS", text(profile.bs)],
    ["PH", text(profile.ph)],
    ["WIP", text(profile.wip)],
    ["ARM", text(profile.arm)],
    ["BTS", text(profile.bts)],
    [profile.is_structure ? "STR" : "VITA", text(profile.vitality)],
    ["S", text(profile.silhouette)],
  ];
  const list = document.createElement("dl");
  list.className = "unit-extended-statline";
  for (const [label, value] of stats) {
    const item = document.createElement("div");
    const term = document.createElement("dt");
    term.textContent = label;
    const description = document.createElement("dd");
    description.textContent = value;
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
    value.textContent = entry.ava === "total" ? "Total" : text(entry.ava);
    const availability = entry.ava == null ? "attached profile" : `AVA ${value.textContent}`;
    item.title = `${army.name} — ${availability}`;
    item.append(value);
    list.append(item);
  }
  return list;
}

function extendedProfilesRow(unit, columnCount) {
  const row = document.createElement("tr");
  row.className = "unit-extended-row";
  const cell = document.createElement("td");
  cell.colSpan = columnCount;
  const surface = document.createElement("div");
  surface.className = "unit-extended-profiles";
  const armiesById = new Map((unit.armies || []).map((army) => [army.id, army]));

  for (const [index, profile] of (unit.profiles || []).entries()) {
    const profileRow = document.createElement("section");
    profileRow.className = "unit-extended-profile";
    if (index > 0) profileRow.classList.add("unit-extended-profile-subordinate");

    const heading = document.createElement("div");
    heading.className = "unit-extended-profile-heading";
    if (index > 0) {
      const attachment = document.createElement("span");
      attachment.className = "unit-profile-attachment";
      attachment.setAttribute("aria-hidden", "true");
      attachment.textContent = "↳";
      heading.append(attachment);
    }
    const title = document.createElement("strong");
    title.textContent = profile.name || unit.name;
    const meta = document.createElement("span");
    meta.className = "unit-extended-profile-meta";
    if (profile.type) {
      const troopType = document.createElement("span");
      troopType.className = "unit-profile-troop-type";
      const longType = document.createElement("span");
      longType.className = "unit-profile-troop-type-long";
      longType.textContent = troopTypeLabel(profile.type);
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
    for (const characteristic of profile.characteristics || []) {
      const descriptor = characteristicSymbol(characteristic);
      if (descriptor) {
        const symbol = document.createElement("img");
        symbol.className = "unit-profile-characteristic-symbol";
        if (developerOnlyCharacteristic(characteristic)) symbol.classList.add("developer-only");
        symbol.src = `/static/${descriptor.category}/${descriptor.type}.svg`;
        symbol.alt = descriptor.label;
        symbol.title = descriptor.label;
        symbol.width = 18;
        symbol.height = 18;
        characteristics.append(symbol);
        continue;
      }
      const fallback = document.createElement("span");
      fallback.className = "unit-profile-characteristic-fallback";
      if (developerOnlyCharacteristic(characteristic)) fallback.classList.add("developer-only");
      fallback.textContent = characteristic;
      characteristics.append(fallback);
    }
    if (!characteristics.childElementCount) characteristics.textContent = "No characteristics";
    body.append(characteristics, profileAvailability(profile, armiesById));
    profileRow.append(heading, body);
    surface.append(profileRow);
  }

  cell.append(surface);
  row.append(cell);
  return row;
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
      if (!event.target.closest("a")) {
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
    if (extended && unit.profiles?.length) fragment.append(extendedProfilesRow(unit, 3));
  }
  container.replaceChildren(fragment);
}
