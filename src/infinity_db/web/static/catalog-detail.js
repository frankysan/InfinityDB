import { distanceUnit, initializeDistanceUnitToggle } from "./preferences.js";
import { renderUnitRows } from "./unit-list.js";

const catalog = document.body.dataset.catalog;
const itemId = window.location.pathname.split("/").pop();
const name = document.getElementById("item-name");
const meta = document.getElementById("item-meta");
const status = document.getElementById("item-status");
const content = document.getElementById("item-content");
const rangeBands = [
  { label: '8"', maximum: 20 },
  { label: '16"', maximum: 40 },
  { label: '24"', maximum: 60 },
  { label: '32"', maximum: 80 },
  { label: '40"', maximum: 100 },
  { label: '48"', maximum: 120 },
  { label: '96"', maximum: 240 },
];
const rangeModifierClasses = {
  "0": "range-modifier-0",
  "+3": "range-modifier-plus-3",
  "-3": "range-modifier-minus-3",
  "-6": "range-modifier-minus-6",
};
let currentItem;

function label(item, variant) {
  const variantName = variant.item_name || item.name;
  return variant.extras.length
    ? `${variantName} (${variant.extras.map((extra) => extra.name).join(", ")})`
    : variantName;
}

function text(value) {
  return value === null || value === undefined || value === "" ? "—" : String(value);
}

function rangeModifier(ranges, maximum) {
  const matchingRange = Object.values(ranges || {})
    .filter((range) => range && typeof range === "object" && Number.isFinite(Number(range.max)))
    .sort((left, right) => Number(left.max) - Number(right.max))
    .find((range) => Number(range.max) >= maximum);
  return matchingRange?.mod || "";
}

function rangeBandLabel(band) {
  return distanceUnit() === "in" ? band.label : `${band.maximum} cm`;
}

function specialWeaponProfile(profile) {
  const card = document.createElement("section");
  card.className = "explorer weapon-profile special-weapon-profile";
  const title = document.createElement("h4");
  title.className = "data-surface-header";
  title.textContent = "Armed Turret profile";
  card.append(title);

  const statTable = document.createElement("table");
  statTable.className = "weapon-statline special-weapon-statline";
  const header = document.createElement("thead");
  const headerRow = document.createElement("tr");
  const valueRow = document.createElement("tr");
  for (const [statLabel, value] of profile.stats) {
    const heading = document.createElement("th");
    heading.textContent = statLabel;
    headerRow.append(heading);
    const cell = document.createElement("td");
    cell.dataset.label = statLabel;
    if (statLabel === "MOV") cell.classList.add("movement-value");
    cell.textContent = value;
    valueRow.append(cell);
  }
  header.append(headerRow);
  const body = document.createElement("tbody");
  body.append(valueRow);
  statTable.append(header, body);
  card.append(statTable);

  for (const [label, items] of [["Equipment", profile.equipment], ["Special Skills", profile.skills]]) {
    const row = document.createElement("p");
    row.className = "weapon-profile-stats";
    row.textContent = `${label}: ${items.join(" · ")}`;
    card.append(row);
  }
  const ccWeapon = document.createElement("p");
  ccWeapon.className = "weapon-profile-stats";
  ccWeapon.textContent = `CC Weapon: ${profile.cc_weapon}`;
  card.append(ccWeapon);
  return card;
}

function weaponVariants(variants, headingText = "Weapon variants") {
  const section = document.createElement("section");
  section.className = "weapon-variants";
  const heading = document.createElement("h2");
  heading.className = "detail-section-title";
  heading.textContent = headingText;
  section.append(heading);

  for (const variant of variants) {
    const variantSection = document.createElement("section");
    variantSection.className = "detail-group weapon-variant";
    const variantTitle = document.createElement("h3");
    variantTitle.className = "detail-section-title detail-section-title--variant";
    variantTitle.textContent = variant.name;
    variantSection.append(variantTitle);

    for (const profile of variant.profiles) {
      const card = document.createElement("section");
      card.className = "explorer weapon-profile";
      const profileTitle = profile.mode || (profile.name !== variant.name ? profile.name : "");
      if (profileTitle) {
        const title = document.createElement("h4");
        title.className = "data-surface-header";
        title.textContent = profileTitle;
        card.append(title);
      }

    const statTable = document.createElement("table");
    statTable.className = "weapon-statline";
    statTable.innerHTML = "<thead><tr><th>Ammunition</th><th>B</th><th>DAM</th><th>Saving</th></tr></thead>";
    const statRow = document.createElement("tr");
    const saving = [profile.saving, profile.saving_num].filter((value) => value !== null && value !== undefined && value !== "").join(" × ");
    for (const [statLabel, value] of [["Ammunition", profile.ammunition], ["B", profile.burst], ["DAM", profile.damage], ["Saving", saving]]) {
      const cell = document.createElement("td");
      cell.dataset.label = statLabel;
      cell.textContent = text(value);
      statRow.append(cell);
    }
    const statBody = document.createElement("tbody");
    statBody.append(statRow);
    statTable.append(statBody);
    card.append(statTable);

    const modifiers = rangeBands.map((band) => rangeModifier(profile.ranges, band.maximum));
    if (modifiers.some(Boolean)) {
      const rangeTable = document.createElement("table");
      rangeTable.className = "weapon-ranges";
      const rangeHeader = document.createElement("thead");
      const headerRow = document.createElement("tr");
      for (const band of rangeBands) {
        const cell = document.createElement("th");
        cell.textContent = rangeBandLabel(band);
        headerRow.append(cell);
      }
      rangeHeader.append(headerRow);
      const rangeBody = document.createElement("tbody");
      const rangeRow = document.createElement("tr");
      for (const [index, band] of rangeBands.entries()) {
        const cell = document.createElement("td");
        cell.dataset.label = rangeBandLabel(band);
        const modifier = modifiers[index];
        cell.textContent = modifier;
        if (rangeModifierClasses[modifier]) cell.classList.add(rangeModifierClasses[modifier]);
        rangeRow.append(cell);
      }
      rangeBody.append(rangeRow);
      rangeTable.append(rangeHeader, rangeBody);
      card.append(rangeTable);
    }

      if (profile.profile) {
        const profileStats = document.createElement("p");
        profileStats.className = "weapon-profile-stats";
        profileStats.textContent = `Profile: ${profile.profile}`;
        card.append(profileStats);
      }

      const traits = document.createElement("p");
    traits.className = "weapon-traits";
    const traitNames = Array.isArray(profile.traits) ? profile.traits : [profile.traits].filter(Boolean);
    traits.textContent = `Traits: ${traitNames.length ? traitNames.join(" · ") : "—"}`;
      card.append(traits);
      variantSection.append(card);
    }
    section.append(variantSection);
  }
  return section;
}

function usageSections(item) {
  return [...item.variants]
    .sort((a, b) => label(item, a).localeCompare(label(item, b), undefined, { numeric: true }))
    .map((variant) => {
      const section = document.createElement("details");
      section.className = "explorer army-profile";
      const summary = document.createElement("summary");
      summary.className = "data-surface-header army-profile-title";
      const title = document.createElement("h2");
      title.textContent = label(item, variant);
      const count = document.createElement("span");
      count.className = "section-index";
      count.textContent = `${variant.units.length} ${variant.units.length === 1 ? "unit" : "units"}`;
      summary.append(title, count);
      const table = document.createElement("table");
      table.innerHTML = "<thead><tr><th>Unit</th><th>Armies</th><th class=\"id-column\">ID</th></tr></thead>";
      const body = document.createElement("tbody");
      renderUnitRows(body, variant.units);
      table.append(body);
      const container = document.createElement("div");
      container.className = "table-container";
      container.append(table);
      section.append(summary, container);
      return section;
    });
}

function usageSectionGroup(sections) {
  const group = document.createElement("section");
  group.className = "detail-group usage-section-group";
  group.append(...sections);
  return group;
}

function render(item) {
  document.title = `${item.name} · InfinityDB`;
  name.firstChild.textContent = item.name;
  if (meta) {
    if (item.wiki) {
      meta.classList.remove("developer-only");
      const link = document.createElement("a");
      link.href = item.wiki;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = item.wiki;
      meta.replaceChildren(link);
    } else {
      meta.classList.add("developer-only");
      meta.textContent = `${catalog === "equipment" ? "Equipment" : "Weapon"} #${item.id}`;
    }
  }
  const sections = usageSections(item);
  content.replaceChildren(
    ...(catalog === "weapons" && item.special_profile ? [specialWeaponProfile(item.special_profile)] : []),
    ...(catalog === "weapons" && item.weapon_variants?.length
      ? [weaponVariants(item.weapon_variants)] : []),
    ...(catalog === "equipment" && item.profiles?.length
      ? [weaponVariants([{ id: item.id, name: item.name, profiles: item.profiles }], "Equipment profile")] : []),
    ...(sections.length ? [usageSectionGroup(sections)] : []),
  );
  content.hidden = false;
  status.hidden = true;
}

initializeDistanceUnitToggle();
window.addEventListener("distanceunitchange", () => {
  if (currentItem && catalog === "weapons") render(currentItem);
});
fetch(`/api/${catalog}/${encodeURIComponent(itemId)}`).then(async (response) => {
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Could not load this item.");
  return payload;
}).then((item) => {
  currentItem = item;
  render(item);
}).catch((error) => {
  name.firstChild.textContent = "Item unavailable";
  status.textContent = error.message || "Could not load this item.";
});
