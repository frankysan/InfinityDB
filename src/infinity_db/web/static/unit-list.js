import { armySymbolPath } from "./army-symbols.js";
import { unitSymbol } from "./unit-symbols.js";

const factionSlugs = new Map([
  [1, "panoceania"], [2, "yu-jing"], [3, "ariadna"], [4, "haqqislam"],
  [5, "nomads"], [6, "combined-army"], [7, "aleph"], [8, "tohaa"],
  [9, "non-aligned-armies"], [10, "o-12"], [11, "jsa"],
]);

function factionSlug(armyId) {
  return factionSlugs.get(Math.floor(Number(armyId) / 100));
}

function displayArmies(armies) {
  const regularArmies = armies.filter((army) => ![98, 99].includes(army.id % 100));
  return [...(regularArmies.length ? regularArmies : armies)].sort((left, right) => left.id - right.id);
}

/** Render catalog unit records with the shared Unit explorer presentation. */
export function renderUnitRows(container, units) {
  const fragment = document.createDocumentFragment();
  for (const unit of units) {
    const row = document.createElement("tr");
    row.className = "unit-row";
    const faction = factionSlug(unit.main_army_id);
    if (faction) row.classList.add(`unit-row--faction-${faction}`);
    row.addEventListener("click", (event) => {
      if (!event.target.closest("a")) window.location.href = `/units/${unit.id}`;
    });
    const nameCell = document.createElement("th");
    nameCell.scope = "row";
    nameCell.className = "unit-name";
    const nameLink = document.createElement("a");
    nameLink.href = `/units/${unit.id}`;
    nameLink.textContent = unit.name;
    const nameContent = document.createElement("span");
    nameContent.className = "unit-name-content";
    const mainArmySymbol = armySymbolPath(unit.main_army_id);
    if (mainArmySymbol) {
      const icon = document.createElement("img");
      icon.className = "army-symbol main-army-symbol";
      icon.src = mainArmySymbol;
      icon.alt = "";
      icon.title = unit.main_army_name
        || unit.armies.find((army) => army.id === unit.main_army_id)?.name
        || "Main army";
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
