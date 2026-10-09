import { DISTANCE_CENTIMETERS_PER_INCH } from "./distance.js";
import { distanceUnit, optionalUnitFilters } from "./preferences.js";
import { getCatalogItem, visibleUnitIds } from "./api.js";
import { renderUnitRows } from "./unit-list.js";
import { tableViewport } from "./view-components.js";
import {
  gameplayVariantRules,
  levelEffectsSection,
  rulesReferenceSection,
} from "./rules-reference.js";

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
const pageController = new AbortController();

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
  return { ...item, variants: (item.variants || []).map((variant) => ({
    ...variant, units: variant.units.filter((unit) => ids.has(unit.id)),
  })).filter((variant) => variant.units.length) };
}

function label(item, variant) {
  const variantName = variant.item_name || item.name;
  return variant.extras.length
    ? `${variantName} (${variant.extras.map((extra) => extra.name).join(", ")})`
    : variantName;
}

function sourceVariantLabel(variant) {
  const semantics = variant.source_variant;
  if (!semantics) return null;
  if (semantics.kind === "level") return `Level ${semantics.value}`;
  if (semantics.kind === "named") return semantics.label;
  if (semantics.kind === "attribute-replacement") {
    return `${semantics.attribute} = ${semantics.value}`;
  }
  return null;
}

function text(value) {
  return value === null || value === undefined || value === "" ? "—" : String(value);
}

function weaponSavingDisplay(profile) {
  const saving = profile.saving;
  if (saving == null || ["", "-", "--"].includes(String(saving).trim())) return "--";
  return [saving, profile.saving_num]
    .filter((value) => value !== null && value !== undefined && value !== "")
    .join(" × ");
}

function ruleReferenceHref(reference) {
  if (reference?.href) return reference.href;
  if (reference?.catalog && reference?.id) {
    return `/${reference.catalog}/${encodeURIComponent(reference.id)}`;
  }
  return null;
}

function weaponTraitLinks(traits) {
  const fragment = document.createDocumentFragment();
  const canonicalSlugs = new Set(traits
    .filter((trait) => trait.slug && !trait.source_alias)
    .map((trait) => trait.slug));
  const duplicateAliases = new Map();
  for (const trait of traits) {
    if (!trait.source_alias || !canonicalSlugs.has(trait.slug)) continue;
    const aliases = duplicateAliases.get(trait.slug) || [];
    aliases.push(trait.label);
    duplicateAliases.set(trait.slug, aliases);
  }
  const visibleTraits = traits.filter((trait) => !(
    trait.source_alias && canonicalSlugs.has(trait.slug)
  ));
  for (const [index, trait] of visibleTraits.entries()) {
    if (index) fragment.append(" · ");
    const label = (trait.source_alias ? trait.name : trait.label) || trait.name || "";
    let href = ruleReferenceHref(trait.public_reference);
    if (!href && trait.slug && !label.startsWith("State:")) {
      href = `/traits/${encodeURIComponent(trait.slug)}`;
    }
    if (href) {
      const link = document.createElement("a");
      link.href = href;
      link.textContent = label;
      fragment.append(link);
    } else {
      fragment.append(label);
    }
    const sourceLabels = trait.source_alias
      ? [trait.label] : (duplicateAliases.get(trait.slug) || []);
    if (sourceLabels.length) {
      const sourceAlias = document.createElement("span");
      sourceAlias.className = "developer-only weapon-trait-source-alias";
      sourceAlias.textContent = ` (Army: ${sourceLabels.join(", ")})`;
      fragment.append(sourceAlias);
    }
  }
  return fragment;
}

function traitDescription(description) {
  const section = document.createElement("section");
  section.className = "surface surface--clipped content-frame";
  const heading = document.createElement("h2");
  heading.className = "surface-titlebar surface-titlebar--subtle";
  heading.textContent = "Rules summary";
  const text = document.createElement("p");
  text.className = "weapon-profile-stats";
  text.textContent = description;
  section.append(heading, text);
  return section;
}

function rangeModifier(ranges, maximum) {
  const orderedRanges = Object.values(ranges || {})
    .filter((range) => range && typeof range === "object" && Number.isFinite(Number(range.max)))
    .sort((left, right) => Number(left.max) - Number(right.max));
  if (!orderedRanges.length) return "";
  const matchingRange = orderedRanges.find((range) => Number(range.max) >= maximum);
  if (!matchingRange) return "--";
  const modifier = matchingRange.mod;
  return modifier === null || modifier === undefined ? "" : String(modifier);
}

const canonicalWeaponRangeBands = [20, 40, 60, 80, 100, 120, 240];

function rangeBandLabel(maximum) {
  return distanceUnit() === "in"
    ? `${maximum / DISTANCE_CENTIMETERS_PER_INCH}"`
    : `${maximum} cm`;
}

function specialWeaponProfile(profile) {
  const card = document.createElement("section");
  card.className = "surface surface--clipped content-frame weapon-profile special-weapon-profile";
  const title = document.createElement("h4");
  title.className = "surface-titlebar surface-titlebar--subtle";
  title.textContent = "Armed Turret profile";
  card.append(title);

  const statTable = document.createElement("table");
  statTable.className =
    "data-table--compact data-table--profile weapon-statline special-weapon-statline";
  const caption = document.createElement("caption");
  caption.className = "sr-only";
  caption.textContent = "Armed Turret profile attributes";
  const header = document.createElement("thead");
  const headerRow = document.createElement("tr");
  const valueRow = document.createElement("tr");
  for (const [statLabel, value] of profile.stats) {
    const heading = document.createElement("th");
    heading.scope = "col";
    heading.className = "table-column--metric";
    heading.textContent = statLabel;
    headerRow.append(heading);
    const cell = document.createElement("td");
    cell.className = "table-column--metric";
    cell.dataset.label = statLabel;
    if (statLabel === "MOV") cell.classList.add("movement-value");
    cell.textContent = value;
    valueRow.append(cell);
  }
  header.append(headerRow);
  const body = document.createElement("tbody");
  body.append(valueRow);
  statTable.append(caption, header, body);
  card.append(tableViewport(statTable));

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
  const rangeBands = canonicalWeaponRangeBands;

  for (const variant of variants) {
    const variantSection = document.createElement("section");
    variantSection.className = "detail-group weapon-variant";

    for (const profile of variant.profiles) {
      const card = document.createElement("section");
      card.className = "surface surface--clipped content-frame weapon-profile";
      const profileTitle = profile.mode || profile.name || variant.name;
      const title = document.createElement("h4");
      title.className = "surface-titlebar surface-titlebar--subtle";
      title.textContent = profileTitle;
      card.append(title);

      const statTable = document.createElement("table");
      statTable.className = "data-table--compact data-table--profile weapon-statline";
      const statCaption = document.createElement("caption");
      statCaption.className = "sr-only";
      statCaption.textContent = `${profileTitle} statistics`;
      statTable.innerHTML = "<thead><tr><th class=\"table-column--descriptor\" scope=\"col\">Ammunition</th><th class=\"table-column--metric\" scope=\"col\">B</th><th class=\"table-column--metric\" scope=\"col\">PS</th><th class=\"table-column--metric\" scope=\"col\">Saving</th></tr></thead>";
      statTable.prepend(statCaption);
      const statRow = document.createElement("tr");
      const ruleReferences = Array.isArray(profile.rule_references)
        ? profile.rule_references : [];
      const ammunitionRule = ruleReferences.find((reference) => (
        reference.kind === "ammunition" && ruleReferenceHref(reference.public_reference)
      ));
      const saving = weaponSavingDisplay(profile);
      for (const [statLabel, value, role] of [
        ["Ammunition", profile.ammunition, "descriptor"],
        ["B", profile.burst, "metric"],
        ["PS", profile.damage, "metric"],
        ["Saving", saving, "metric"],
      ]) {
        const cell = document.createElement("td");
        cell.className = `table-column--${role}`;
        cell.dataset.label = statLabel;
        if (statLabel === "Ammunition" && ammunitionRule) {
          const link = document.createElement("a");
          link.href = ruleReferenceHref(ammunitionRule.public_reference);
          link.textContent = text(value);
          cell.append(link);
        } else {
          cell.textContent = text(value);
        }
        statRow.append(cell);
      }
      const statBody = document.createElement("tbody");
      statBody.append(statRow);
      statTable.append(statBody);
      card.append(tableViewport(statTable));

      const modifiers = rangeBands.map((maximum) => rangeModifier(profile.ranges, maximum));
      if (modifiers.some(Boolean)) {
        const rangeTable = document.createElement("table");
        rangeTable.className = "data-table--compact weapon-ranges";
        const rangeCaption = document.createElement("caption");
        rangeCaption.className = "sr-only";
        rangeCaption.textContent = `${profileTitle} range modifiers`;
        const rangeHeader = document.createElement("thead");
        const headerRow = document.createElement("tr");
        for (const maximum of rangeBands) {
          const cell = document.createElement("th");
          cell.scope = "col";
          cell.className = "table-column--metric";
          cell.textContent = rangeBandLabel(maximum);
          headerRow.append(cell);
        }
        rangeHeader.append(headerRow);
        const rangeBody = document.createElement("tbody");
        const rangeRow = document.createElement("tr");
        for (const [index, maximum] of rangeBands.entries()) {
          const cell = document.createElement("td");
          cell.className = "table-column--metric";
          cell.dataset.label = rangeBandLabel(maximum);
          const modifier = modifiers[index];
          cell.textContent = modifier;
          if (rangeModifierClasses[modifier]) cell.classList.add(rangeModifierClasses[modifier]);
          rangeRow.append(cell);
        }
        rangeBody.append(rangeRow);
        rangeTable.append(rangeCaption, rangeHeader, rangeBody);
        card.append(tableViewport(rangeTable));
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
      if (profile.rules?.length) {
        card.append(rulesReferenceSection(profile.rules, "Mode rules"));
      }
      const sourceTraitSlugs = new Set(traitReferences.map((trait) => trait.slug));
      const relatedRules = ruleReferences.filter((reference) => (
        reference.kind !== "ammunition"
        && !(reference.kind === "trait" && sourceTraitSlugs.has(reference.id.slice(6)))
      ));
      if (relatedRules.length) {
        const row = document.createElement("div");
        row.className = "weapon-data-row";
        const heading = document.createElement("h5");
        heading.className = "weapon-data-heading";
        heading.textContent = "Related rules";
        const links = document.createElement("p");
        links.className = "weapon-data-value";
        for (const [index, reference] of relatedRules.entries()) {
          if (index) links.append(" · ");
          const link = document.createElement("a");
          link.href = ruleReferenceHref(reference.public_reference);
          link.textContent = reference.name;
          links.append(link);
        }
        row.append(heading, links);
        card.append(row);
      }
      variantSection.append(card);
    }
    section.append(variantSection);
  }
  return section;
}

function usageSections(item) {
  return [...(item.variants || [])]
    .sort((a, b) => label(item, a).localeCompare(label(item, b), undefined, { numeric: true }))
    .map((variant) => {
      const section = document.createElement("details");
      section.className = "surface surface--clipped content-frame army-profile";
      const summary = document.createElement("summary");
      summary.className = "surface-titlebar surface-titlebar--subtle army-profile-title";
      const title = document.createElement("h2");
      title.textContent = label(item, variant);
      const count = document.createElement("span");
      count.className = "section-index";
      const semanticLabel = sourceVariantLabel(variant);
      const unitCount = `${variant.units.length} ${variant.units.length === 1 ? "unit" : "units"}`;
      const summaryParts = [semanticLabel, unitCount].filter(Boolean);
      count.textContent = summaryParts.join(" · ");
      summary.append(title, count);
      section.append(summary);
      section.addEventListener("toggle", () => {
        if (!section.open || section.dataset.loaded) return;
        const table = document.createElement("table");
        table.className = "data-table--compact data-table--listing data-table--unit-list data-table--unit-usage data-table--interactive";
        table.innerHTML = "<caption class=\"sr-only\">Units using this variant</caption><thead><tr><th class=\"table-column--primary\" scope=\"col\">Unit</th><th class=\"table-column--descriptor\" scope=\"col\">Armies</th><th class=\"id-column table-column--technical\" scope=\"col\">ID</th></tr></thead>";
        const body = document.createElement("tbody");
        renderUnitRows(body, variant.units);
        table.append(body);
        section.append(tableViewport(table));
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


function hackingProgramsSection(programs) {
  const section = document.createElement("section");
  section.className = "detail-group";
  const heading = document.createElement("h2");
  heading.className = "detail-heading";
  heading.textContent = "Baseline Hacking Programs";
  const list = document.createElement("ul");
  list.className = "detail-list";
  for (const program of programs) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = `/hacking-programs/${encodeURIComponent(program.slug || program.id)}`;
    link.textContent = program.name;
    item.append(link);
    list.append(item);
  }
  section.append(heading, list);
  return section;
}

function render(item) {
  document.title = `${item.name} · InfinityDB`;
  name.firstChild.textContent = item.name;
  if (meta) {
    const categories = (item.categories || []).map((category) => category.name).join(", ");
    if (item.wiki) {
      const link = document.createElement("a");
      link.href = item.wiki;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = displayWikiUrl(item.wiki);
      meta.replaceChildren(link);
      if (categories) meta.append(` · ${categories}`);
    } else {
      const domain = catalog === "equipment"
        ? "Equipment"
        : catalog === "weapons"
          ? "Weapon"
          : "Weapon trait";
      meta.textContent = `${domain} #${item.id}${categories ? ` · ${categories}` : ""}`;
    }
  }
  const sections = usageSections(item);
  const variantRules = gameplayVariantRules(item.variants);
  const levelEffects = levelEffectsSection(item.rules);
  content.replaceChildren(
    ...(item.rules?.length ? [rulesReferenceSection(item.rules)] : []),
    ...(levelEffects ? [levelEffects] : []),
    ...(variantRules.length ? [rulesReferenceSection(variantRules, "Variant rules")] : []),
    ...(catalog === "traits" && item.description && !item.rules?.length
      ? [traitDescription(item.description)] : []),
    ...(catalog === "weapons" && item.special_profile ? [specialWeaponProfile(item.special_profile)] : []),
    ...(catalog === "weapons" && item.weapon_variants?.length
      ? [weaponVariants(item.weapon_variants)] : []),
    ...(catalog === "equipment" && item.profiles?.length
      ? [weaponVariants([{ id: item.id, name: item.name, profiles: item.profiles }])] : []),
    ...(catalog === "equipment" && item.hacking_programs?.length
      ? [hackingProgramsSection(item.hacking_programs)] : []),
    ...(sections.length ? [catalog === "traits" ? traitUsageSectionGroup(item) : usageSectionGroup(sections)] : []),
  );
  content.hidden = false;
  status.hidden = true;
}

// Rule cards arrive after the initial document fragment navigation. Restore
// that target once the catalog API response has rendered the card.
function revealHashTarget() {
  if (!window.location.hash) return;
  let targetId;
  try {
    targetId = decodeURIComponent(window.location.hash.slice(1));
  } catch {
    return;
  }
  const target = document.getElementById(targetId);
  if (!target || !content.contains(target)) return;
  target.scrollIntoView({ block: "start" });
}

document.addEventListener(
  "infinity:beforenavigation",
  () => pageController.abort(),
  { once: true },
);
window.addEventListener("hashchange", revealHashTarget, { signal: pageController.signal });
window.addEventListener("distanceunitchange", () => {
  if (currentItem && catalog === "weapons") render(currentItem);
}, { signal: pageController.signal });
getCatalogItem(catalog, itemId, pageController.signal).then((item) => {
  currentItem = item;
  render(item);
  requestAnimationFrame(revealHashTarget);
  if (catalog === "states") return null;
  return visibleUnitIds(optionalUnitFilters(), pageController.signal).then((ids) => render(withVisibleUnits(item, ids)));
}).catch((error) => {
  if (error.name === "AbortError") return;
  name.firstChild.textContent = "Item unavailable";
  status.textContent = error.message || "Could not load this item.";
});
window.addEventListener("optionalunitschange", () => {
  if (!currentItem) return;
  visibleUnitIds(optionalUnitFilters(), pageController.signal)
    .then((ids) => render(withVisibleUnits(currentItem, ids)))
    .catch((error) => {
      if (error.name !== "AbortError") throw error;
    });
}, { signal: pageController.signal });
