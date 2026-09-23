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

function variantSection(variant, parameterSemantics) {
  const section = document.createElement("details");
  section.className = "explorer army-profile";
  const heading = document.createElement("summary");
  heading.className = "data-surface-header army-profile-title";
  const title = document.createElement("h2");
  title.textContent = formatVariantName(variant, parameterSemantics);
  const count = document.createElement("span");
  count.className = "section-index";
  count.textContent = `${variant.units.length} ${variant.units.length === 1 ? "unit" : "units"}`;
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
    meta.classList.remove("developer-only");
    const link = document.createElement("a");
    link.href = skill.wiki;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = displayWikiUrl(skill.wiki);
    meta.replaceChildren(link);
    if (categories) meta.append(` · ${categories}`);
  } else {
    meta.classList.add("developer-only");
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
