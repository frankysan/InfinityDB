import { formatSkillDistanceExtra, initializeDistanceUnitToggle } from "./preferences.js";
import { getCatalogItem, visibleUnitIds } from "./api.js";
import { renderUnitRows } from "./unit-list.js";
import { rulesReferenceSection } from "./rules-reference.js";

const skillId = new URLSearchParams(window.location.search).get("id")
  || window.location.pathname.split("/").pop();
const name = document.getElementById("skill-name");
const meta = document.getElementById("skill-meta");
const status = document.getElementById("skill-status");
const content = document.getElementById("skill-content");
let currentSkill;

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

function referenceCell(value) {
  const cell = document.createElement("td");
  if (value instanceof Node) cell.append(value);
  else cell.textContent = value === null || value === undefined || value === "" ? "—" : String(value);
  return cell;
}

function structuredTable(titleText, headers, rows) {
  const section = document.createElement("section");
  section.className = "detail-group";
  const title = document.createElement("h2");
  title.className = "detail-section-title";
  title.textContent = titleText;
  const container = document.createElement("div");
  container.className = "table-container";
  const table = document.createElement("table");
  table.className = "data-table--compact";
  const head = document.createElement("thead");
  const headRow = document.createElement("tr");
  for (const label of headers) {
    const header = document.createElement("th");
    header.scope = "col";
    header.textContent = label;
    headRow.append(header);
  }
  head.append(headRow);
  const body = document.createElement("tbody");
  for (const values of rows) {
    const row = document.createElement("tr");
    row.append(...values.map(referenceCell));
    body.append(row);
  }
  table.append(head, body);
  container.append(table);
  section.append(title, container);
  return section;
}

function hackingDeviceLinks(devices) {
  if (!devices?.length) return "Upgrade / source-specific";
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

function skillTypeLabel(value) {
  const labels = {
    "entire order": "Entire Order",
    short: "Short Skill",
    aro: "ARO",
  };
  return labels[value] || value;
}

function structuredReferenceSection(reference) {
  if (!reference?.rows?.length) return null;
  if (reference.kind === "hacking-programs") {
    return structuredTable(
      reference.title,
      ["Program", "Attack MOD", "Opponent MOD", "PS", "B", "Target", "Skill type", "Device", "Special"],
      reference.rows.map((row) => [
        row.name,
        row.attack_mod,
        row.opponent_mod,
        row.ps,
        row.burst,
        row.targets?.length ? row.targets.join(", ") : "—",
        row.skill_types?.length ? row.skill_types.map(skillTypeLabel).join(", ") : "—",
        hackingDeviceLinks(row.devices),
        row.special,
      ]),
    );
  }
  if (reference.kind === "martial-arts") {
    return structuredTable(
      reference.title,
      ["Level", "Attack MOD", "Opponent MOD", "PS MOD", "B MOD"],
      reference.rows.map((row) => [
        row.level, row.attack_mod, row.opponent_mod, row.ps_mod, row.burst_mod,
      ]),
    );
  }
  if (reference.kind === "random-chart") {
    return structuredTable(
      reference.title,
      ["Roll", "Result"],
      reference.rows.map((row) => [row.roll, row.result]),
    );
  }
  return null;
}

function variantSection(variant, parameterSemantics) {
  const section = document.createElement("details");
  section.className = "explorer army-profile";
  const heading = document.createElement("summary");
  heading.className = "data-surface-header army-profile-title";
  const title = document.createElement("h2");
  title.textContent = formatVariantName(variant, parameterSemantics);
  const count = document.createElement("span");
  count.className = "section-index";
  const semanticLabel = sourceVariantLabel(variant);
  const unitCount = `${variant.units.length} ${variant.units.length === 1 ? "unit" : "units"}`;
  const summaryParts = [semanticLabel, variant.rules?.length ? "Variant rules" : null, unitCount]
    .filter(Boolean);
  count.textContent = summaryParts.join(" · ");
  heading.append(title, count);
  section.append(heading);
  section.addEventListener("toggle", () => {
    if (!section.open || section.dataset.loaded) return;
    const table = document.createElement("table");
    table.className = "data-table--compact";
    table.innerHTML = "<caption class=\"sr-only\">Units using this skill variant</caption><thead><tr><th scope=\"col\">Unit</th><th scope=\"col\">Armies</th><th class=\"id-column\" scope=\"col\">ID</th></tr></thead>";
    const body = document.createElement("tbody");
    renderUnitRows(body, variant.units);
    table.append(body);
    const container = document.createElement("div");
    container.className = "table-container";
    container.append(table);
    if (variant.rules?.length) {
      section.append(rulesReferenceSection(variant.rules, "Variant rules"));
    }
    section.append(container);
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
  const structuredReference = structuredReferenceSection(skill.structured_reference);
  if (structuredReference) children.push(structuredReference);
  children.push(sections);
  sections.append(...variants.map((variant) => variantSection(variant, skill.parameter_semantics)));
  content.replaceChildren(...children);
  status.hidden = true;
  content.hidden = false;
}

initializeDistanceUnitToggle();
window.addEventListener("distanceunitchange", () => {
  if (currentSkill) render(currentSkill);
});
if (!skillId) {
  name.firstChild.textContent = "Skill unavailable";
  status.textContent = "The requested skill address is invalid.";
} else {
  getCatalogItem("skills", skillId).then((skill) => {
    currentSkill = skill;
    render(skill);
    return visibleUnitIds().then((ids) => render(withVisibleUnits(skill, ids)));
  }).catch((error) => {
    name.firstChild.textContent = "Skill unavailable";
    status.textContent = error.message || "Could not load this skill.";
  });
}
window.addEventListener("optionalunitschange", () => {
  if (currentSkill) visibleUnitIds().then((ids) => render(withVisibleUnits(currentSkill, ids)));
});
