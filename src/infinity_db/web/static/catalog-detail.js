import { distanceUnit, initializeDistanceUnitToggle } from "./preferences.js";
import { getCatalogItem, visibleUnitIds } from "./api.js";
import { renderUnitRows } from "./unit-list.js";
import { rulesReferenceSection } from "./rules-reference.js";

const catalog = document.body.dataset.catalog;
const itemId = window.location.pathname.split("/").pop();
const name = document.getElementById("item-name");
const meta = document.getElementById("item-meta");
const status = document.getElementById("item-status");
const content = document.getElementById("item-content");
const rangeModifierClasses = {
  "0": "range-modifier-0",
  "+3": "range-modifier-plus-3",
  "-3": "range-modifier-minus-3",
  "-6": "range-modifier-minus-6",
};
let currentItem;

function displayWikiUrl(url) {
  try {
    return new URL(url).hostname.toLowerCase() === "infinitythewiki.com"
      ? url.split("?", 1)[0]
      : url;
  } catch {
    return url;
  }
}

function withVisibleUnits(item, ids) {
  return { ...item, variants: item.variants.map((variant) => ({
    ...variant, units: variant.units.filter((unit) => ids.has(unit.id)),
  })).filter((variant) => variant.units.length) };
}

function label(item, variant) {
  const variantName = variant.item_name || item.name;
  return variant.extras.length
    ? `${variantName} (${variant.extras.map((extra) => extra.name).join(", ")})`
    : variantName;
}

function text(value) {
  return value === null || value === undefined || value === "" ? "—" : String(value);
}

function weaponTraitLinks(traits) {
  const fragment = document.createDocumentFragment();
  for (const [index, trait] of traits.entries()) {
    if (index) fragment.append(" · ");
    const label = trait.label || trait.name || "";
    if (trait.slug) {
      const link = document.createElement("a");
      link.href = `/traits/${encodeURIComponent(trait.slug)}`;
      link.textContent = label;
      fragment.append(link);
    } else {
      fragment.append(label);
    }
  }
  return fragment;
}

function traitDescription(description) {
  const section = document.createElement("section");
  section.className = "explorer surface";
  const heading = document.createElement("h2");
  heading.className = "data-surface-header";
  heading.textContent = "Rules summary";
  const text = document.createElement("p");
  text.className = "weapon-profile-stats";
  text.textContent = description;
  section.append(heading, text);
  return section;
}

function rangeModifier(ranges, maximum) {
  const matchingRange = Object.values(ranges || {})
    .filter((range) => range && typeof range === "object" && Number.isFinite(Number(range.max)))
    .sort((left, right) => Number(left.max) - Number(right.max))
    .find((range) => Number(range.max) >= maximum);
  return matchingRange?.mod || "";
}

function weaponRangeBands(variants) {
  const maximums = new Set();
  for (const variant of variants || []) {
    for (const profile of variant.profiles || []) {
      for (const range of Object.values(profile.ranges || {})) {
        const maximum = Number(range?.max);
        if (Number.isFinite(maximum) && maximum > 0) maximums.add(maximum);
      }
    }
  }
  return [...maximums].sort((left, right) => left - right);
}

function rangeBandLabel(maximum) {
  return distanceUnit() === "in" ? `${maximum / 2.5}"` : `${maximum} cm`;
}

function specialWeaponProfile(profile) {
  const card = document.createElement("section");
  card.className = "explorer surface weapon-profile special-weapon-profile";
  const title = document.createElement("h4");
  title.className = "data-surface-header";
  title.textContent = "Armed Turret profile";
  card.append(title);

  const statTable = document.createElement("table");
  statTable.className = "data-table--compact weapon-statline special-weapon-statline";
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

function weaponVariants(variants) {
  const section = document.createElement("section");
  section.className = "weapon-variants";
  const rangeBands = weaponRangeBands(variants);

  for (const variant of variants) {
    const variantSection = document.createElement("section");
    variantSection.className = "detail-group weapon-variant";

    for (const profile of variant.profiles) {
      const card = document.createElement("section");
      card.className = "explorer surface weapon-profile";
      const profileTitle = profile.mode || profile.name || variant.name;
      const title = document.createElement("h4");
      title.className = "data-surface-header";
      title.textContent = profileTitle;
      card.append(title);

    const statTable = document.createElement("table");
    statTable.className = "data-table--compact weapon-statline";
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

    const modifiers = rangeBands.map((maximum) => rangeModifier(profile.ranges, maximum));
    if (modifiers.some(Boolean)) {
      const rangeTable = document.createElement("table");
      rangeTable.className = "data-table--compact weapon-ranges";
      const rangeHeader = document.createElement("thead");
      const headerRow = document.createElement("tr");
      for (const maximum of rangeBands) {
        const cell = document.createElement("th");
        cell.textContent = rangeBandLabel(maximum);
        headerRow.append(cell);
      }
      rangeHeader.append(headerRow);
      const rangeBody = document.createElement("tbody");
      const rangeRow = document.createElement("tr");
      for (const [index, maximum] of rangeBands.entries()) {
        const cell = document.createElement("td");
        cell.dataset.label = rangeBandLabel(maximum);
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
        const profileRow = document.createElement("div");
        profileRow.className = "weapon-data-row";
        const profileHeading = document.createElement("h5");
        profileHeading.className = "weapon-data-heading";
        profileHeading.textContent = "Profile";
        const profileStats = document.createElement("p");
        profileStats.className = "weapon-data-value";
        profileStats.textContent = profile.profile;
        profileRow.append(profileHeading, profileStats);
        card.append(profileRow);
      }

      const traitReferences = Array.isArray(profile.trait_references)
        ? profile.trait_references
        : [];
      if (traitReferences.length) {
        const traitsRow = document.createElement("div");
        traitsRow.className = "weapon-data-row";
        const traitsHeading = document.createElement("h5");
        traitsHeading.className = "weapon-data-heading";
        traitsHeading.textContent = "Traits";
        const traits = document.createElement("p");
        traits.className = "weapon-data-value";
        traits.append(weaponTraitLinks(traitReferences));
        traitsRow.append(traitsHeading, traits);
        card.append(traitsRow);
      }
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
      section.append(summary);
      section.addEventListener("toggle", () => {
        if (!section.open || section.dataset.loaded) return;
        const table = document.createElement("table");
        table.className = "data-table--compact";
        table.innerHTML = "<thead><tr><th>Unit</th><th>Armies</th><th class=\"id-column\">ID</th></tr></thead>";
        const body = document.createElement("tbody");
        renderUnitRows(body, variant.units);
        table.append(body);
        const container = document.createElement("div");
        container.className = "table-container";
        container.append(table);
        section.append(container);
        section.dataset.loaded = "true";
      });
      return section;
    });
}

function usageSectionGroup(sections) {
  const group = document.createElement("section");
  group.className = "detail-group usage-section-group";
  group.append(...sections);
  return group;
}

function traitUsageSectionGroup(item) {
  const group = document.createElement("section");
  group.className = "detail-group usage-section-group";
  const groups = new Map();
  for (const variant of item.variants) {
    const catalogName = variant.catalog || "other";
    if (!groups.has(catalogName)) groups.set(catalogName, []);
    groups.get(catalogName).push(variant);
  }
  for (const [catalogName, variants] of [...groups.entries()].sort(([left], [right]) => left.localeCompare(right))) {
    const title = document.createElement("h3");
    title.className = "trait-catalog-heading";
    title.textContent = catalogName[0].toUpperCase() + catalogName.slice(1);
    group.append(title, ...usageSections({ ...item, variants }));
  }
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
      link.textContent = displayWikiUrl(item.wiki);
      meta.replaceChildren(link);
    } else {
      meta.classList.add("developer-only");
      meta.textContent = `${catalog === "equipment" ? "Equipment" : catalog === "weapons" ? "Weapon" : "Weapon trait"} #${item.id}`;
    }
  }
  const sections = usageSections(item);
  content.replaceChildren(
    ...(item.rules?.length ? [rulesReferenceSection(item.rules)] : []),
    ...(catalog === "traits" && item.description && !item.rules?.length
      ? [traitDescription(item.description)] : []),
    ...(catalog === "weapons" && item.special_profile ? [specialWeaponProfile(item.special_profile)] : []),
    ...(catalog === "weapons" && item.weapon_variants?.length
      ? [weaponVariants(item.weapon_variants)] : []),
    ...(catalog === "equipment" && item.profiles?.length
      ? [weaponVariants([{ id: item.id, name: item.name, profiles: item.profiles }])] : []),
    ...(sections.length ? [catalog === "traits" ? traitUsageSectionGroup(item) : usageSectionGroup(sections)] : []),
  );
  content.hidden = false;
  status.hidden = true;
}

initializeDistanceUnitToggle();
window.addEventListener("distanceunitchange", () => {
  if (currentItem && catalog === "weapons") render(currentItem);
});
getCatalogItem(catalog, itemId).then((item) => {
  currentItem = item;
  render(item);
  return visibleUnitIds().then((ids) => render(withVisibleUnits(item, ids)));
}).catch((error) => {
  name.firstChild.textContent = "Item unavailable";
  status.textContent = error.message || "Could not load this item.";
});
window.addEventListener("optionalunitschange", () => {
  if (currentItem) visibleUnitIds().then((ids) => render(withVisibleUnits(currentItem, ids)));
});
