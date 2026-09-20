import { armySymbolPath } from "./army-symbols.js";
import { unitSymbol } from "./unit-symbols.js";

function displayArmies(armies) {
  return [...armies].sort((left, right) => left.id - right.id);
}

/** Render catalog unit records with the shared Unit explorer presentation. */
export function renderUnitRows(container, units) {
  const fragment = document.createDocumentFragment();
  for (const unit of units) {
    const row = document.createElement("tr");
    row.className = "unit-row";
    const faction = unit.display_faction?.slug;
    if (faction) row.classList.add(`unit-row--faction-${faction}`);
    row.addEventListener("click", (event) => {
      if (!event.target.closest("a")) {
        const url = `/units/${unit.id}`;
        window.infinityNavigate ? window.infinityNavigate(url) : window.location.assign(url);
      }
    });
    const nameCell = document.createElement("th");
    nameCell.scope = "row";
    nameCell.className = "unit-name";
    const nameLink = document.createElement("a");
    nameLink.href = `/units/${unit.id}`;
    nameLink.textContent = unit.name;
    const nameContent = document.createElement("span");
    nameContent.className = "unit-name-content";
    const displayArmySymbol = armySymbolPath(unit.display_army_id);
    if (displayArmySymbol) {
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
    nameContent.append(unitSymbol(unit.slug || unit.isc || unit.name), nameLink);
    nameCell.append(nameContent);
    const armyCell = document.createElement("td");
    const armyList = document.createElement("div");
    armyList.className = "army-tags";
    const armies = displayArmies(unit.armies);
    if (armies.length > 12) armyList.classList.add("army-tags-compact");
    for (const army of armies) {
      const symbol = armySymbolPath(army.id);
      if (symbol) {
        const icon = document.createElement("img");
        icon.className = "army-symbol";
        icon.src = symbol;
        icon.alt = army.name;
        icon.width = 30;
        icon.height = 30;
        icon.loading = "lazy";
        icon.decoding = "async";
        icon.title = army.name;
        armyList.append(icon);
      } else {
        const tag = document.createElement("span");
        tag.className = "army-tag";
        tag.title = army.name;
        tag.textContent = army.name;
        armyList.append(tag);
      }
    }
    if (!unit.armies.length) armyList.textContent = "—";
    armyCell.append(armyList);
    const idCell = document.createElement("td");
    idCell.className = "unit-id id-column";
    idCell.textContent = unit.source_ids.map((sourceId) => `#${sourceId}`).join(" / ");
    row.append(nameCell, armyCell, idCell);
    fragment.append(row);
  }
  container.replaceChildren(fragment);
}
