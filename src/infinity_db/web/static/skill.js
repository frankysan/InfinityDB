import { formatSkillDistanceExtra } from "./distance.js";
import { optionalUnitFilters } from "./preferences.js";
import { getCatalogItem, visibleUnitIds } from "./api.js";
import { renderUnitRows } from "./unit-list.js";
import { gameplayVariantRules, rulesReferenceSection } from "./rules-reference.js";
import { skillCategoryBadge } from "./skill-categories.js";
import { tableViewport } from "./view-components.js";

const skillId = new URLSearchParams(window.location.search).get("id")
  || window.location.pathname.split("/").pop();
const name = document.getElementById("skill-name");
const meta = document.getElementById("skill-meta");
const status = document.getElementById("skill-status");
const content = document.getElementById("skill-content");
let currentSkill;
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

function withVisibleUnits(skill, ids) {
  return {
    ...skill, variants: skill.variants.map((variant) => ({
      ...variant, units: variant.units.filter((unit) => ids.has(unit.id)),
    })).filter((variant) => variant.units.length)
  };
}

function formatVariantName(variant, parameterSemantics = null) {
  const extras = variant.extras.map((extra) => {
    if (!extra.is_distance) return extra.name;
    return formatSkillDistanceExtra(extra.name, parameterSemantics);
  });
  return extras.length ? `${variant.skill_name} (${extras.join(", ")})` : variant.skill_name;
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

function referenceCell(value, role) {
  const cell = document.createElement("td");
  cell.className = `table-column--${role}`;
  if (value instanceof Node) cell.append(value);
  else cell.textContent = value === null || value === undefined || value === "" ? "—" : String(value);
  return cell;
}

function structuredTable(titleText, columns, rows) {
  const section = document.createElement("section");
  section.className = "detail-group";
  const title = document.createElement("h2");
  title.className = "detail-heading";
  title.textContent = titleText;
  const table = document.createElement("table");
  table.className = "data-table--compact data-table--reference";
  const caption = document.createElement("caption");
  caption.className = "sr-only";
  caption.textContent = titleText;
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const column of columns) {
    const header = document.createElement("th");
    header.scope = "col";
    header.className = `table-column--${column.role}`;
    header.textContent = column.label;
    headRow.append(header);
  }
  head.append(headRow);
  const body = document.createElement("tbody");
  for (const values of rows) {
    const row = document.createElement("tr");
    row.append(...values.map((value, index) => referenceCell(value, columns[index].role)));
    body.append(row);
  }
  table.append(caption, head, body);
  section.append(title, tableViewport(table));
  return section;
}

function hackingProgramLink(row) {
  const link = document.createElement("a");
  link.href = `/hacking-programs/${encodeURIComponent(row.slug || row.id || row.position)}`;
  link.textContent = row.name;
  return link;
}

function hackingDeviceLinks(devices) {
  if (!devices?.length) return "Granted separately / Upgrade";
  const fragment = document.createDocumentFragment();
  for (const [index, device] of devices.entries()) {
    if (index) fragment.append(", ");
    if (device.slug) {
      const link = document.createElement("a");
      link.href = `/equipment/${encodeURIComponent(device.slug)}`;
      link.textContent = device.name;
      fragment.append(link);
    } else {
      fragment.append(device.name);
    }
  }
  return fragment;
}

function declarationCategoryBadges(categories) {
  if (!categories?.length) return "—";
  const badges = document.createElement("span");
  badges.className = "detail-badges";
  for (const category of categories) {
    badges.append(skillCategoryBadge(category));
  }
  return badges;
}
function structuredReferenceSection(reference) {
  if (!reference?.rows?.length) return null;
  if (reference.kind === "hacking-programs") {
    return structuredTable(
      reference.title,
      [
        { label: "Program", role: "primary" },
        { label: "Attack MOD", role: "metric" },
        { label: "Opponent MOD", role: "metric" },
        { label: "PS", role: "metric" },
        { label: "B", role: "metric" },
        { label: "Target", role: "descriptor" },
        { label: "Type(s)", role: "descriptor" },
        { label: "Device", role: "descriptor" },
        { label: "Special", role: "descriptor" },
      ],
      reference.rows.map((row) => [
        hackingProgramLink(row),
        row.attack_mod,
        row.opponent_mod,
        row.ps,
        row.burst,
        row.targets?.length ? row.targets.join(", ") : "—",
        declarationCategoryBadges(row.declaration_categories),
        hackingDeviceLinks(row.devices),
        row.special,
      ]),
    );
  }
  if (reference.kind === "martial-arts") {
    return structuredTable(
      reference.title,
      [
        { label: "Level", role: "metric" },
        { label: "Attack MOD", role: "metric" },
        { label: "Opponent MOD", role: "metric" },
        { label: "PS MOD", role: "metric" },
        { label: "B MOD", role: "metric" },
      ],
      reference.rows.map((row) => [
        row.level, row.attack_mod, row.opponent_mod, row.ps_mod, row.burst_mod,
      ]),
    );
  }
  if (reference.kind === "random-chart") {
    return structuredTable(
      reference.title,
      [
        { label: "Roll", role: "metric" },
        { label: "Result", role: "descriptor" },
      ],
      reference.rows.map((row) => [row.roll, row.result]),
    );
  }
  return null;
}

function variantSection(variant, parameterSemantics) {
  const section = document.createElement("details");
  section.className = "surface surface--clipped content-frame army-profile";
  const heading = document.createElement("summary");
  heading.className = "surface-titlebar surface-titlebar--subtle army-profile-title";
  const title = document.createElement("h2");
  title.textContent = formatVariantName(variant, parameterSemantics);
  const count = document.createElement("span");
  count.className = "section-index";
  const semanticLabel = sourceVariantLabel(variant);
  const unitCount = `${variant.units.length} ${variant.units.length === 1 ? "unit" : "units"}`;
  const summaryParts = [semanticLabel, unitCount].filter(Boolean);
  count.textContent = summaryParts.join(" · ");
  heading.append(title, count);
  section.append(heading);
  section.addEventListener("toggle", () => {
    if (!section.open || section.dataset.loaded) return;
    const table = document.createElement("table");
    table.className = "data-table--compact data-table--listing data-table--unit-list data-table--unit-usage data-table--interactive";
    table.innerHTML = "<caption class=\"sr-only\">Units using this skill variant</caption><thead><tr><th class=\"table-column--primary\" scope=\"col\">Unit</th><th class=\"table-column--descriptor\" scope=\"col\">Armies</th><th class=\"id-column table-column--technical\" scope=\"col\">ID</th></tr></thead>";
    const body = document.createElement("tbody");
    renderUnitRows(body, variant.units);
    table.append(body);
    section.append(tableViewport(table));
    section.dataset.loaded = "true";
  });
  return section;
}

function render(skill) {
  document.title = `${skill.name} · InfinityDB`;
  name.firstChild.textContent = skill.name;
  const categories = (skill.categories || []).map((category) => category.name).join(", ");
  if (skill.wiki) {
    const link = document.createElement("a");
    link.href = skill.wiki;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = displayWikiUrl(skill.wiki);
    meta.replaceChildren(link);
    if (categories) meta.append(` · ${categories}`);
  } else {
    meta.textContent = `Skill #${skill.id}${categories ? ` · ${categories}` : ""}`;
  }
  const variants = [...skill.variants].sort((left, right) => (
    formatVariantName(left, skill.parameter_semantics).localeCompare(
      formatVariantName(right, skill.parameter_semantics),
      undefined,
      { sensitivity: "base", numeric: true },
    )
  ));
  const sections = document.createElement("section");
  sections.className = "detail-group usage-section-group";
  const children = [];
  if (skill.rules?.length) children.push(rulesReferenceSection(skill.rules));
  const variantRules = gameplayVariantRules(variants);
  if (variantRules.length) children.push(rulesReferenceSection(variantRules, "Variant rules"));
  const structuredReference = structuredReferenceSection(skill.structured_reference);
  if (structuredReference) children.push(structuredReference);
  children.push(sections);
  sections.append(...variants.map((variant) => variantSection(variant, skill.parameter_semantics)));
  content.replaceChildren(...children);
  status.hidden = true;
  content.hidden = false;
}

document.addEventListener(
  "infinity:beforenavigation",
  () => pageController.abort(),
  { once: true },
);
window.addEventListener("distanceunitchange", () => {
  if (currentSkill) render(currentSkill);
}, { signal: pageController.signal });
if (!skillId) {
  name.firstChild.textContent = "Skill unavailable";
  status.textContent = "The requested skill address is invalid.";
} else {
  getCatalogItem("skills", skillId, pageController.signal).then((skill) => {
    currentSkill = skill;
    render(skill);
    return visibleUnitIds(optionalUnitFilters(), pageController.signal)
      .then((ids) => render(withVisibleUnits(skill, ids)));
  }).catch((error) => {
    if (error.name === "AbortError") return;
    name.firstChild.textContent = "Skill unavailable";
    status.textContent = error.message || "Could not load this skill.";
  });
}
window.addEventListener("optionalunitschange", () => {
  if (!currentSkill) return;
  visibleUnitIds(optionalUnitFilters(), pageController.signal)
    .then((ids) => render(withVisibleUnits(currentSkill, ids)))
    .catch((error) => {
      if (error.name !== "AbortError") throw error;
    });
}, { signal: pageController.signal });
