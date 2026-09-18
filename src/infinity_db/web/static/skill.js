import { cacheBustedUrl, formatSkillDistanceExtra, initializeDistanceUnitToggle } from "./preferences.js";
import { visibleUnitIds } from "./api.js";
import { renderUnitRows } from "./unit-list.js";

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

function rulesReferenceSection(rules) {
  const section = document.createElement("section");
  section.className = "detail-group rules-reference";
  const heading = document.createElement("h2");
  heading.className = "detail-section-title";
  heading.textContent = "Rules reference";
  section.append(heading);
  for (const rule of rules) {
    const article = document.createElement("article");
    article.className = "detail-section";
    const title = document.createElement("h3");
    title.textContent = rule.name;
    article.append(title);
    const summary = document.createElement("p");
    summary.className = "detail-copy";
    summary.textContent = rule.summary;
    article.append(summary);
    const badges = [];
    if (rule.skill_type?.name) badges.push(rule.skill_type.name);
    for (const label of rule.labels || []) badges.push(label.name);
    if (badges.length) {
      const badgeRow = document.createElement("p");
      badgeRow.className = "detail-badges";
      for (const badge of badges) {
        const element = document.createElement("span");
        element.className = "badge";
        element.textContent = badge;
        badgeRow.append(element);
      }
      article.append(badgeRow);
    }
    const facts = rule.facts || {};
    for (const key of ["effects", "requirements", "restrictions"]) {
      if (!Array.isArray(facts[key]) || !facts[key].length) continue;
      const list = document.createElement("ul");
      list.className = "detail-list";
      for (const fact of facts[key]) {
        const item = document.createElement("li");
        item.textContent = fact;
        list.append(item);
      }
      article.append(list);
    }
    if (rule.citations?.length) {
      const citations = document.createElement("p");
      citations.className = "detail-source";
      citations.textContent = rule.citations.map((citation) => {
        const location = citation.page ? `p. ${citation.page}` : citation.heading || citation.member;
        return `${citation.source_title || citation.source_id}, ${location}`;
      }).join(" · ");
      article.append(citations);
    }
    section.append(article);
  }
  return section;
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
    section.append(container);
    section.dataset.loaded = "true";
  });
  return section;
}

function render(skill) {
  document.title = `${skill.name} · InfinityDB`;
  name.firstChild.textContent = skill.name;
  if (skill.wiki) {
    meta.classList.remove("developer-only");
    const link = document.createElement("a");
    link.href = skill.wiki;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = displayWikiUrl(skill.wiki);
    meta.replaceChildren(link);
  } else {
    meta.classList.add("developer-only");
    const categories = (skill.categories || []).map((category) => category.name).join(", ");
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
if (!/^\d+$/.test(skillId || "")) {
  name.firstChild.textContent = "Skill unavailable";
  status.textContent = "The requested skill address is invalid.";
} else {
  fetch(cacheBustedUrl(`/api/skills/${encodeURIComponent(skillId)}`), { cache: "no-store" }).then(async (response) => {
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Could not load this skill.");
    return payload;
  }).then((skill) => {
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
